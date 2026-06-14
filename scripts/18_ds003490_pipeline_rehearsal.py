from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.signal import welch

from scripts.utils.common import project_path, read_tsv, script_finish, script_start, write_rows_csv
from scripts.utils.feature_extraction import region_indices


SCRIPT = "18_ds003490_pipeline_rehearsal.py"
DATASET = "ds003490"
BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
}
REGIONS = ["global", "frontal", "central", "parietal", "occipital", "temporal"]
ERP_CONDITIONS = {
    "standard": ["standard tone", "s201"],
    "target": ["target tone", "s200"],
    "novel": ["novel tone", "s202"],
}
SENSITIVITY_CONFIGS = [
    ("1_40_fixed", 1.0, 40.0, "fixed", False),
    ("2_40_fixed", 2.0, 40.0, "fixed", False),
    ("2_30_fixed", 2.0, 30.0, "fixed", False),
    ("2_40_knee", 2.0, 40.0, "knee", False),
    ("2_40_fixed_line_noise_exclusion", 2.0, 40.0, "fixed", True),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ds003490 pipeline rehearsal outputs without TBI claims.")
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--specparam-sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260612)
    args = parser.parse_args()
    if args.dataset != DATASET:
        raise SystemExit("This rehearsal script is intentionally restricted to ds003490.")

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    root = project_path("data/raw", DATASET)
    out_dir = project_path("outputs/d2_cross_task")
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import mne
    except Exception as exc:
        raise SystemExit(f"MNE is required for ds003490 pipeline rehearsal: {exc}") from exc

    set_files = sorted(path for path in root.rglob("*.set") if is_bids_set(path))
    if not set_files:
        raise SystemExit(f"No BIDS .set files found under {root}")
    participants = participant_map(root)
    sensitivity_sample = set(random.Random(args.seed).sample(set_files, min(args.specparam_sample_size, len(set_files))))

    rest_rows: list[dict[str, Any]] = []
    aperiodic_rows: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    erp_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []

    for index, set_path in enumerate(set_files, 1):
        relative = rel(root, set_path)
        entities = parse_entities(relative)
        event_path = set_path.with_name(set_path.name.replace("_eeg.set", "_events.tsv"))
        event_rows = read_tsv(event_path)
        try:
            raw = mne.io.read_raw_eeglab(set_path, preload=True, verbose="ERROR")
            picks = mne.pick_types(raw.info, eeg=True, eog=False, ecg=False, emg=False, misc=False)
            if len(picks) == 0:
                picks = np.arange(len(raw.ch_names))
            channel_names = [raw.ch_names[int(idx)] for idx in picks]
            sfreq = float(raw.info["sfreq"])
            duration = float(raw.n_times / sfreq)
            segments = rest_segments_from_events(event_rows, duration)
            if not segments:
                segments = [{"condition": "rest_unspecified", "blocks": [(0.0, duration)], "duration_sec": duration, "event_count": 0}]
            erp_rows.extend(erp_readiness_rows(root, set_path, event_rows, entities, participants, duration))
            for segment in segments:
                data = concatenate_blocks(raw, picks, segment["blocks"])
                if data.shape[1] < max(10, int(sfreq * 2)):
                    warnings.append(f"Skipping short segment {relative} {segment['condition']} duration={segment['duration_sec']:.3f}s")
                    continue
                freqs, psd_by_channel = compute_psd(data, sfreq)
                for region in REGIONS:
                    indices = list(range(len(channel_names))) if region == "global" else region_indices(channel_names, region)
                    if not indices:
                        continue
                    psd = np.nanmean(psd_by_channel[indices, :], axis=0)
                    common = common_columns(root, set_path, entities, participants, segment, region, channel_names, sfreq, data)
                    rest_rows.extend(rest_feature_rows(common, freqs, psd))
                    fit = fit_spectral_model(freqs, psd, 1.0, 40.0, "fixed", False)
                    aperiodic_rows.append(aperiodic_row(common, fit))
                    alpha_rows.append(alpha_row(common, freqs, psd, fit))
                    if set_path in sensitivity_sample:
                        for config_name, fmin, fmax, mode, exclude_line_noise in SENSITIVITY_CONFIGS:
                            sensitivity_rows.append(
                                sensitivity_row(
                                    common,
                                    freqs,
                                    psd,
                                    config_name,
                                    fmin,
                                    fmax,
                                    mode,
                                    exclude_line_noise,
                                )
                            )
        except Exception as exc:
            errors.append(f"{relative}: {exc}")
        finally:
            if index % 10 == 0:
                print(f"processed {index}/{len(set_files)} ds003490 recordings", flush=True)

    write_outputs(out_dir, rest_rows, aperiodic_rows, alpha_rows, erp_rows, sensitivity_rows)
    write_feature_dictionary(out_dir)
    write_reports(rest_rows, aperiodic_rows, alpha_rows, erp_rows, sensitivity_rows, len(set_files), len(sensitivity_sample))
    script_finish(
        SCRIPT,
        start,
        outputs=[
            str(out_dir / "ds003490_rest_features.csv"),
            str(out_dir / "ds003490_aperiodic_features.csv"),
            str(out_dir / "ds003490_alpha_iaf_features.csv"),
            str(out_dir / "ds003490_erp_readiness.csv"),
            str(out_dir / "ds003490_feature_dictionary.csv"),
            str(out_dir / "ds003490_specparam_sensitivity.csv"),
            str(project_path("reports/24_ds003490_pipeline_rehearsal_report.md")),
            str(project_path("reports/25_ds003490_specparam_rehearsal_report.md")),
        ],
        warnings=warnings + ["ds003490 is comparator-only; no TBI validation claim was made."],
        errors=errors,
        parameters=vars(args),
        status="completed" if not errors else "completed_with_errors",
    )


def is_bids_set(path: Path) -> bool:
    text = path.as_posix()
    return path.suffix.lower() == ".set" and "/.git/annex/objects/" not in text and bool(re.search(r"/sub-[^/]+/ses-[^/]+/eeg/", text))


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def parse_entities(relative_path: str) -> dict[str, str]:
    name = Path(relative_path).name

    def search(pattern: str, text: str) -> str:
        match = re.search(pattern, text)
        return match.group(1) if match else ""

    return {
        "bids_subject": search(r"(?:^|/)sub-([^/_]+)", relative_path),
        "session": search(r"(?:^|/)ses-([^/_]+)", relative_path),
        "task": search(r"_task-([^_./]+)", name),
        "run": search(r"_run-([^_./]+)", name),
    }


def participant_map(root: Path) -> dict[str, dict[str, str]]:
    rows = read_tsv(root / "participants.tsv")
    return {row.get("participant_id", ""): row for row in rows}


def rest_segments_from_events(rows: list[dict[str, str]], raw_duration: float) -> list[dict[str, Any]]:
    by_condition: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        label = (row.get("trial_type") or row.get("value") or "").strip().lower()
        condition = ""
        if "eyes closed" in label or "eyes_closed" in label:
            condition = "eyes_closed"
        elif "eyes open" in label or "eyes_open" in label:
            condition = "eyes_open"
        elif "rest" in label:
            condition = "rest_unspecified"
        if not condition:
            continue
        try:
            onset = float(row.get("onset", ""))
        except Exception:
            continue
        if math.isfinite(onset):
            by_condition[condition].append(onset)

    segments: list[dict[str, Any]] = []
    for condition, onsets in sorted(by_condition.items()):
        onsets = sorted(onsets)
        if not onsets:
            continue
        blocks = []
        block_start = onsets[0]
        last = onsets[0]
        gaps = []
        for onset in onsets[1:]:
            gap = onset - last
            if 0 < gap <= 3.0:
                gaps.append(gap)
                last = onset
                continue
            step = median(gaps) if gaps else 1.0
            blocks.append((max(0.0, block_start), min(raw_duration, last + step)))
            block_start = onset
            last = onset
            gaps = []
        step = median(gaps) if gaps else 1.0
        blocks.append((max(0.0, block_start), min(raw_duration, last + step)))
        duration = sum(max(0.0, stop - start) for start, stop in blocks)
        if duration > 0:
            segments.append({"condition": condition, "blocks": blocks, "duration_sec": duration, "event_count": len(onsets)})
    return segments


def median(values: list[float]) -> float:
    if not values:
        return 1.0
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def concatenate_blocks(raw: Any, picks: np.ndarray, blocks: list[tuple[float, float]]) -> np.ndarray:
    sfreq = float(raw.info["sfreq"])
    pieces = []
    for start, stop in blocks:
        start_idx = max(0, int(round(start * sfreq)))
        stop_idx = min(raw.n_times, int(round(stop * sfreq)))
        if stop_idx > start_idx:
            pieces.append(raw.get_data(picks=picks, start=start_idx, stop=stop_idx))
    if not pieces:
        return np.empty((len(picks), 0))
    return np.concatenate(pieces, axis=1)


def compute_psd(data: np.ndarray, sfreq: float) -> tuple[np.ndarray, np.ndarray]:
    nperseg = int(min(max(128, round(4 * sfreq)), data.shape[1]))
    noverlap = nperseg // 2 if nperseg >= 4 else 0
    freqs, psd = welch(data, fs=sfreq, nperseg=nperseg, noverlap=noverlap, axis=1)
    return freqs, psd


def common_columns(
    root: Path,
    set_path: Path,
    entities: dict[str, str],
    participants: dict[str, dict[str, str]],
    segment: dict[str, Any],
    region: str,
    channel_names: list[str],
    sfreq: float,
    data: np.ndarray,
) -> dict[str, Any]:
    subject = f"sub-{entities.get('bids_subject', '')}"
    person = participants.get(subject, {})
    return {
        "dataset_id": DATASET,
        "relative_path": rel(root, set_path),
        "bids_subject": entities.get("bids_subject", ""),
        "session": entities.get("session", ""),
        "task": entities.get("task", ""),
        "group": person.get("Group", ""),
        "condition": segment["condition"],
        "condition_event_count": segment["event_count"],
        "segment_duration_sec": round(float(segment["duration_sec"]), 6),
        "region": region,
        "n_channels_region": data.shape[0] if region == "global" else "",
        "n_channels_total": len(channel_names),
        "sfreq_hz": sfreq,
        "n_samples_condition": data.shape[1],
        "pipeline_scope": "ds003490_pipeline_rehearsal_only",
    }


def rest_feature_rows(common: dict[str, Any], freqs: np.ndarray, psd: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    denom = integrate_power(freqs, psd, 1.0, 40.0)
    powers = {name: integrate_power(freqs, psd, low, high) for name, (low, high) in BANDS.items()}
    for band, value in powers.items():
        rows.append({**common, "feature_family": "band_power", "feature_name": f"absolute_{band}_power", "feature_value": value, "unit": "V^2/Hz_integral"})
        rows.append(
            {
                **common,
                "feature_family": "relative_band_power",
                "feature_name": f"relative_{band}_power",
                "feature_value": value / denom if denom and math.isfinite(denom) and denom > 0 else np.nan,
                "unit": "proportion_1_40Hz",
            }
        )
    theta = powers["theta"]
    alpha = powers["alpha"]
    rows.append({**common, "feature_family": "ratio", "feature_name": "theta_alpha_ratio", "feature_value": theta / alpha if alpha > 0 else np.nan, "unit": "ratio"})
    rows.append({**common, "feature_family": "ratio", "feature_name": "alpha_theta_ratio", "feature_value": alpha / theta if theta > 0 else np.nan, "unit": "ratio"})
    rows.append({**common, "feature_family": "distribution", "feature_name": "spectral_entropy_1_40", "feature_value": spectral_entropy(freqs, psd), "unit": "unitless"})
    return rows


def integrate_power(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high) & np.isfinite(psd)
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(psd[mask], freqs[mask]))


def spectral_entropy(freqs: np.ndarray, psd: np.ndarray) -> float:
    mask = (freqs >= 1.0) & (freqs <= 40.0) & np.isfinite(psd)
    values = np.maximum(np.asarray(psd[mask], dtype=float), 0.0)
    total = float(np.sum(values))
    if total <= 0 or len(values) <= 1:
        return float("nan")
    probs = values / total
    probs = probs[probs > 0]
    return float(-(probs * np.log(probs)).sum() / np.log(len(values)))


def alpha_peak_from_psd(freqs: np.ndarray, psd: np.ndarray) -> tuple[float, float]:
    mask = (freqs >= 7.0) & (freqs <= 13.0) & np.isfinite(psd)
    if np.count_nonzero(mask) < 2:
        return float("nan"), float("nan")
    local_freqs = freqs[mask]
    local_psd = psd[mask]
    idx = int(np.argmax(local_psd))
    return float(local_freqs[idx]), float(local_psd[idx])


def fit_spectral_model(
    freqs: np.ndarray,
    psd: np.ndarray,
    fmin: float,
    fmax: float,
    mode: str,
    exclude_line_noise: bool,
) -> dict[str, Any]:
    mask = (freqs >= fmin) & (freqs <= fmax) & np.isfinite(psd) & (psd > 0)
    line_noise_bins_excluded = 0
    if exclude_line_noise:
        line_mask = (freqs >= 57.0) & (freqs <= 63.0)
        line_noise_bins_excluded = int(np.count_nonzero(mask & line_mask))
        mask = mask & ~line_mask
    fit_freqs = freqs[mask]
    fit_psd = psd[mask]
    if len(fit_freqs) < 12:
        return failed_fit("insufficient_frequency_bins", line_noise_bins_excluded)
    specparam_error = ""
    try:
        from specparam import SpectralModel

        model = SpectralModel(
            peak_width_limits=[1, 12],
            max_n_peaks=6,
            min_peak_height=0.0,
            peak_threshold=2.0,
            aperiodic_mode=mode,
            verbose=False,
        )
        model.fit(fit_freqs, fit_psd)
        ap = np.asarray(model.results.get_params("aperiodic"), dtype=float)
        peaks = np.asarray(model.results.get_params("peak"), dtype=float)
        if ap.ndim == 0 or ap.size < 2:
            raise ValueError("specparam returned incomplete aperiodic parameters")
        offset = float(ap[0])
        knee = float(ap[1]) if mode == "knee" and ap.size >= 3 else ""
        exponent = float(ap[-1])
        rsq = to_float(model.results.get_metrics("rsquared"))
        error = to_float(model.results.get_metrics("mae"))
        return {
            "fit_status": "passed",
            "fit_method": "specparam",
            "aperiodic_mode": mode,
            "aperiodic_offset": offset,
            "aperiodic_knee": knee,
            "aperiodic_exponent": exponent,
            "r_squared": rsq,
            "fit_error": error,
            "n_peaks": peak_count(peaks),
            **alpha_peak_from_model(peaks),
            "line_noise_bins_excluded": line_noise_bins_excluded,
            "fit_notes": "",
        }
    except Exception as exc:
        specparam_error = str(exc)
    try:
        from fooof import FOOOF

        fm = FOOOF(
            peak_width_limits=[1, 12],
            max_n_peaks=6,
            min_peak_height=0.0,
            peak_threshold=2.0,
            aperiodic_mode=mode,
            verbose=False,
        )
        fm.fit(fit_freqs, fit_psd)
        ap = np.asarray(fm.aperiodic_params_, dtype=float)
        offset = float(ap[0])
        knee = float(ap[1]) if mode == "knee" and ap.size >= 3 else ""
        exponent = float(ap[-1])
        peaks = np.asarray(fm.peak_params_, dtype=float)
        return {
            "fit_status": "passed",
            "fit_method": "fooof",
            "aperiodic_mode": mode,
            "aperiodic_offset": offset,
            "aperiodic_knee": knee,
            "aperiodic_exponent": exponent,
            "r_squared": to_float(fm.r_squared_),
            "fit_error": to_float(fm.error_),
            "n_peaks": peak_count(peaks),
            **alpha_peak_from_model(peaks),
            "line_noise_bins_excluded": line_noise_bins_excluded,
            "fit_notes": f"FOOOF fallback used after specparam failed: {specparam_error}",
        }
    except Exception as exc:
        return failed_fit(f"specparam error: {specparam_error}; fooof error: {exc}", line_noise_bins_excluded)


def failed_fit(notes: str, line_noise_bins_excluded: int) -> dict[str, Any]:
    return {
        "fit_status": "failed",
        "fit_method": "",
        "aperiodic_mode": "",
        "aperiodic_offset": "",
        "aperiodic_knee": "",
        "aperiodic_exponent": "",
        "r_squared": "",
        "fit_error": "",
        "n_peaks": "",
        "alpha_peak_cf_hz": "",
        "alpha_peak_power": "",
        "alpha_peak_bandwidth_hz": "",
        "line_noise_bins_excluded": line_noise_bins_excluded,
        "fit_notes": notes,
    }


def to_float(value: Any) -> float:
    try:
        arr = np.asarray(value, dtype=float)
        if arr.size == 0:
            return float("nan")
        return float(arr.flat[0])
    except Exception:
        return float("nan")


def peak_count(peaks: np.ndarray) -> int:
    if peaks.size == 0:
        return 0
    if peaks.ndim == 1:
        return 1 if peaks.size >= 3 else 0
    return int(peaks.shape[0])


def alpha_peak_from_model(peaks: np.ndarray) -> dict[str, Any]:
    if peaks.size == 0:
        return {"alpha_peak_cf_hz": "", "alpha_peak_power": "", "alpha_peak_bandwidth_hz": ""}
    peaks = np.atleast_2d(peaks)
    alpha = peaks[(peaks[:, 0] >= 7.0) & (peaks[:, 0] <= 13.0)]
    if alpha.size == 0:
        return {"alpha_peak_cf_hz": "", "alpha_peak_power": "", "alpha_peak_bandwidth_hz": ""}
    idx = int(np.argmax(alpha[:, 1]))
    return {"alpha_peak_cf_hz": float(alpha[idx, 0]), "alpha_peak_power": float(alpha[idx, 1]), "alpha_peak_bandwidth_hz": float(alpha[idx, 2])}


def aperiodic_row(common: dict[str, Any], fit: dict[str, Any]) -> dict[str, Any]:
    return {
        **common,
        "frequency_range_hz": "1-40",
        "line_noise_exclusion": False,
        "fit_status": fit["fit_status"],
        "fit_method": fit["fit_method"],
        "aperiodic_mode": fit["aperiodic_mode"],
        "aperiodic_exponent": fit["aperiodic_exponent"],
        "aperiodic_offset": fit["aperiodic_offset"],
        "aperiodic_knee": fit["aperiodic_knee"],
        "r_squared": fit["r_squared"],
        "fit_error": fit["fit_error"],
        "n_peaks": fit["n_peaks"],
        "fit_notes": fit["fit_notes"],
    }


def alpha_row(common: dict[str, Any], freqs: np.ndarray, psd: np.ndarray, fit: dict[str, Any]) -> dict[str, Any]:
    iaf, alpha_power = alpha_peak_from_psd(freqs, psd)
    alpha_abs = integrate_power(freqs, psd, 8.0, 13.0)
    total = integrate_power(freqs, psd, 1.0, 40.0)
    return {
        **common,
        "iaf_peak_frequency_hz": iaf,
        "iaf_peak_power": alpha_power,
        "absolute_alpha_power": alpha_abs,
        "relative_alpha_power": alpha_abs / total if total and math.isfinite(total) and total > 0 else np.nan,
        "specparam_alpha_peak_cf_hz": fit["alpha_peak_cf_hz"],
        "specparam_alpha_peak_power": fit["alpha_peak_power"],
        "specparam_alpha_peak_bandwidth_hz": fit["alpha_peak_bandwidth_hz"],
        "specparam_fit_status": fit["fit_status"],
        "specparam_fit_method": fit["fit_method"],
    }


def sensitivity_row(
    common: dict[str, Any],
    freqs: np.ndarray,
    psd: np.ndarray,
    config_name: str,
    fmin: float,
    fmax: float,
    mode: str,
    exclude_line_noise: bool,
) -> dict[str, Any]:
    fit = fit_spectral_model(freqs, psd, fmin, fmax, mode, exclude_line_noise)
    exponent = finite_or_nan(fit.get("aperiodic_exponent"))
    offset = finite_or_nan(fit.get("aperiodic_offset"))
    rsq = finite_or_nan(fit.get("r_squared"))
    err = finite_or_nan(fit.get("fit_error"))
    unstable = (
        fit.get("fit_status") != "passed"
        or not math.isfinite(exponent)
        or not math.isfinite(offset)
        or abs(exponent) > 5
        or (math.isfinite(rsq) and rsq < 0.90)
        or (math.isfinite(err) and err > 0.25)
    )
    return {
        **common,
        "sensitivity_config": config_name,
        "fmin_hz": fmin,
        "fmax_hz": fmax,
        "line_noise_exclusion": exclude_line_noise,
        "unstable_fit_flag": unstable,
        **fit,
    }


def finite_or_nan(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else float("nan")
    except Exception:
        return float("nan")


def classify_event(label: str) -> str:
    text = normalize_label(label)
    for condition, tokens in ERP_CONDITIONS.items():
        if any(token in text for token in tokens):
            return condition
    if "eyes closed" in text:
        return "eyes_closed"
    if "eyes open" in text:
        return "eyes_open"
    if "boundary" in text or "status" in text:
        return "boundary"
    return "other"


def normalize_label(label: str) -> str:
    return str(label or "").strip().lower().replace("  ", " ")


def erp_readiness_rows(
    root: Path,
    set_path: Path,
    rows: list[dict[str, str]],
    entities: dict[str, str],
    participants: dict[str, dict[str, str]],
    raw_duration: float,
) -> list[dict[str, Any]]:
    by_condition: dict[str, list[float]] = defaultdict(list)
    labels_by_condition: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        label = row.get("trial_type") or row.get("value") or ""
        condition = classify_event(label)
        try:
            onset = float(row.get("onset", ""))
        except Exception:
            continue
        by_condition[condition].append(onset)
        labels_by_condition[condition][label] += 1
    subject = f"sub-{entities.get('bids_subject', '')}"
    person = participants.get(subject, {})
    out = []
    for condition in ["standard", "target", "novel"]:
        onsets = by_condition.get(condition, [])
        valid_epoch_count = sum(1 for onset in onsets if onset >= 0.2 and onset + 0.8 <= raw_duration)
        epoch_feasible = valid_epoch_count >= 20
        p3_window = "250-450ms" if condition == "novel" else "300-600ms"
        p3_component = "P3a" if condition == "novel" else "P3b" if condition == "target" else "standard_control_ERP"
        out.append(
            {
                "dataset_id": DATASET,
                "relative_path": rel(root, set_path),
                "bids_subject": entities.get("bids_subject", ""),
                "session": entities.get("session", ""),
                "task": entities.get("task", ""),
                "group": person.get("Group", ""),
                "condition": condition,
                "labels_observed": "; ".join(f"{label}:{count}" for label, count in labels_by_condition[condition].most_common()),
                "event_count": len(onsets),
                "valid_epoch_count_minus200_to_800ms": valid_epoch_count,
                "epoch_feasible": epoch_feasible,
                "p3_component_candidate": p3_component,
                "basic_erp_window": p3_window,
                "p3_extraction_feasible": epoch_feasible and condition in {"target", "novel"},
                "notes": "ERP readiness only; no Parkinson-specific or TBI-specific analysis was run.",
            }
        )
    return out


def write_outputs(
    out_dir: Path,
    rest_rows: list[dict[str, Any]],
    aperiodic_rows: list[dict[str, Any]],
    alpha_rows: list[dict[str, Any]],
    erp_rows: list[dict[str, Any]],
    sensitivity_rows: list[dict[str, Any]],
) -> None:
    write_rows_csv(out_dir / "ds003490_rest_features.csv", rest_rows)
    write_rows_csv(out_dir / "ds003490_aperiodic_features.csv", aperiodic_rows)
    write_rows_csv(out_dir / "ds003490_alpha_iaf_features.csv", alpha_rows)
    write_rows_csv(out_dir / "ds003490_erp_readiness.csv", erp_rows)
    write_rows_csv(out_dir / "ds003490_specparam_sensitivity.csv", sensitivity_rows)


def write_feature_dictionary(out_dir: Path) -> None:
    rows = [
        {"output_file": "ds003490_rest_features.csv", "feature_name": "absolute_delta/theta/alpha/beta_power", "description": "Regional Welch PSD band-power integrals.", "unit": "V^2/Hz_integral", "notes": "Comparator pipeline rehearsal only."},
        {"output_file": "ds003490_rest_features.csv", "feature_name": "relative_delta/theta/alpha/beta_power", "description": "Band power divided by total 1-40 Hz power.", "unit": "proportion_1_40Hz", "notes": "Comparator pipeline rehearsal only."},
        {"output_file": "ds003490_rest_features.csv", "feature_name": "theta_alpha_ratio", "description": "Absolute theta power divided by absolute alpha power.", "unit": "ratio", "notes": "Comparator pipeline rehearsal only."},
        {"output_file": "ds003490_rest_features.csv", "feature_name": "alpha_theta_ratio", "description": "Absolute alpha power divided by absolute theta power.", "unit": "ratio", "notes": "Comparator pipeline rehearsal only."},
        {"output_file": "ds003490_rest_features.csv", "feature_name": "spectral_entropy_1_40", "description": "Normalized entropy of regional PSD values from 1-40 Hz.", "unit": "unitless", "notes": "Comparator pipeline rehearsal only."},
        {"output_file": "ds003490_aperiodic_features.csv", "feature_name": "aperiodic_exponent", "description": "Specparam/FOOOF fixed-mode aperiodic exponent over 1-40 Hz.", "unit": "unitless", "notes": "Preferred method is specparam; FOOOF is fallback."},
        {"output_file": "ds003490_aperiodic_features.csv", "feature_name": "aperiodic_offset", "description": "Specparam/FOOOF fixed-mode aperiodic offset over 1-40 Hz.", "unit": "log10_power", "notes": "Preferred method is specparam; FOOOF is fallback."},
        {"output_file": "ds003490_alpha_iaf_features.csv", "feature_name": "iaf_peak_frequency_hz", "description": "Peak PSD frequency in the 7-13 Hz alpha search band.", "unit": "Hz", "notes": "Simple PSD peak for rehearsal."},
        {"output_file": "ds003490_alpha_iaf_features.csv", "feature_name": "specparam_alpha_peak_*", "description": "Model-derived alpha peak center frequency, power, and bandwidth when available.", "unit": "mixed", "notes": "Blank when no alpha peak is identified."},
        {"output_file": "ds003490_erp_readiness.csv", "feature_name": "event_count", "description": "Standard/target/novel event counts derived from explicit labels.", "unit": "count", "notes": "Readiness only; no ERP amplitude claim."},
        {"output_file": "ds003490_specparam_sensitivity.csv", "feature_name": "unstable_fit_flag", "description": "True for failed, non-finite, low R2, high-error, or extreme-exponent fits.", "unit": "boolean", "notes": "Thresholds are QC heuristics for pipeline rehearsal."},
    ]
    write_rows_csv(out_dir / "ds003490_feature_dictionary.csv", rows)


def write_reports(
    rest_rows: list[dict[str, Any]],
    aperiodic_rows: list[dict[str, Any]],
    alpha_rows: list[dict[str, Any]],
    erp_rows: list[dict[str, Any]],
    sensitivity_rows: list[dict[str, Any]],
    n_files: int,
    n_sensitivity_files: int,
) -> None:
    reports = project_path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    conditions = sorted({row.get("condition", "") for row in rest_rows})
    regions = sorted({row.get("region", "") for row in rest_rows})
    erp_feasible = Counter(str(row.get("p3_extraction_feasible", "")) for row in erp_rows if row.get("condition") in {"target", "novel"})
    report24 = f"""# ds003490 Pipeline Rehearsal Report

Generated: 2026-06-12

## Scope

`ds003490` is a Parkinson's/control comparator dataset, not a TBI dataset. This run is pipeline/paradigm rehearsal only. No D1, D2, D3, TBI-validation, diagnostic, prognostic, or clinical claim is made from these outputs.

## Outputs

| Output | Rows |
| --- | ---: |
| `outputs/d2_cross_task/ds003490_rest_features.csv` | {len(rest_rows)} |
| `outputs/d2_cross_task/ds003490_aperiodic_features.csv` | {len(aperiodic_rows)} |
| `outputs/d2_cross_task/ds003490_alpha_iaf_features.csv` | {len(alpha_rows)} |
| `outputs/d2_cross_task/ds003490_erp_readiness.csv` | {len(erp_rows)} |
| `outputs/d2_cross_task/ds003490_feature_dictionary.csv` | 11 |

## Rehearsal Coverage

| Check | Result |
| --- | --- |
| Recordings processed | {n_files} |
| Rest/state conditions | {', '.join(conditions)} |
| Regional aggregations | {', '.join(regions)} |
| Band/ratio/entropy features | delta, theta, alpha, beta, theta/alpha, alpha/theta, entropy |
| Aperiodic features | exponent and offset via specparam with FOOOF fallback |
| Alpha/IAF features | PSD alpha peak plus model-derived alpha peak fields when available |
| ERP readiness | standard/target/novel counts, epoch feasibility, P3a/P3b feasibility flags |

## ERP Readiness Summary

Target/novel P3 feasibility flags across recording-condition rows:

| Feasible | Rows |
| --- | ---: |
{counter_table_rows(erp_feasible)}

## Decision

These outputs prepare the later D2 paradigm reproducibility section and the later ds003522 comparison workflow. They do not establish TBI effects and should not be merged into D1/D3 scientific interpretation.
"""
    (reports / "24_ds003490_pipeline_rehearsal_report.md").write_text(report24, encoding="utf-8", newline="\n")

    sens_counter = Counter(row.get("fit_status", "") for row in sensitivity_rows)
    unstable = sum(1 for row in sensitivity_rows if str(row.get("unstable_fit_flag", "")).lower() == "true")
    alpha_identified = sum(1 for row in sensitivity_rows if str(row.get("alpha_peak_cf_hz", "")).strip())
    config_summary = summarize_sensitivity_by_config(sensitivity_rows)
    report25 = f"""# ds003490 Specparam Rehearsal Report

Generated: 2026-06-12

## Scope

This stress-test uses `ds003490` only to rehearse aperiodic estimation before ds003522 is verified. `ds003490` is not TBI validation.

## Run Summary

| Check | Result |
| --- | ---: |
| Recordings sampled for sensitivity | {n_sensitivity_files} |
| Sensitivity fit rows | {len(sensitivity_rows)} |
| Passed fits | {sens_counter.get('passed', 0)} |
| Failed fits | {sens_counter.get('failed', 0)} |
| Unstable fit flags | {unstable} |
| Rows with model alpha peak | {alpha_identified} |

## Frequency-Range And Mode Summary

{config_summary}

Line-noise exclusion was included as a pipeline flag. Because all requested sensitivity ranges ended at 40 Hz or 30 Hz, no 57-63 Hz bins were present to exclude in this rehearsal.

## Interpretation For Later Use

The sensitivity output records range, aperiodic mode, line-noise exclusion, fit success, fit error, R-squared, exponent/offset, and model alpha-peak fields. It is ready to compare against ds003522 later only after ds003522 raw EEG is verified locally. Any frequency-range dependence should be treated as pipeline sensitivity, not as a disease result.
"""
    (reports / "25_ds003490_specparam_rehearsal_report.md").write_text(report25, encoding="utf-8", newline="\n")


def counter_table_rows(counter: Counter[str]) -> str:
    if not counter:
        return "| none | 0 |"
    return "\n".join(f"| {key} | {value} |" for key, value in sorted(counter.items()))


def summarize_sensitivity_by_config(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No sensitivity rows available._"
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("sensitivity_config", ""))].append(row)
    lines = [
        "| Config | Rows | Passed | Failed | Unstable | Mean Exponent | Mean R2 | Alpha Peak Rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for config, config_rows in sorted(grouped.items()):
        exponents = [finite_or_nan(row.get("aperiodic_exponent")) for row in config_rows]
        r2s = [finite_or_nan(row.get("r_squared")) for row in config_rows]
        exponents = [x for x in exponents if math.isfinite(x)]
        r2s = [x for x in r2s if math.isfinite(x)]
        mean_exponent = f"{np.mean(exponents):.4f}" if exponents else "NA"
        mean_r2 = f"{np.mean(r2s):.4f}" if r2s else "NA"
        lines.append(
            f"| `{config}` | {len(config_rows)} | {sum(row.get('fit_status') == 'passed' for row in config_rows)} | "
            f"{sum(row.get('fit_status') == 'failed' for row in config_rows)} | "
            f"{sum(str(row.get('unstable_fit_flag', '')).lower() == 'true' for row in config_rows)} | "
            f"{mean_exponent} | {mean_r2} | "
            f"{sum(bool(str(row.get('alpha_peak_cf_hz', '')).strip()) for row in config_rows)} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
