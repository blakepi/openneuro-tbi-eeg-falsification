from __future__ import annotations

import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.signal import welch

from scripts.utils.common import project_path, read_rows_csv, read_tsv, script_finish, script_start, write_rows_csv


SCRIPT = "14_d1_artifact_control_analysis.py"
BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "low_gamma_or_emg": (30.0, 45.0),
}
REGIONS = {
    "global": [],
    "frontal": ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "Fz", "AF3", "AF4"],
    "central": ["C3", "C4", "Cz", "FC1", "FC2", "FC5", "FC6"],
    "parietal": ["P3", "P4", "Pz", "CP1", "CP2", "CP5", "CP6"],
    "occipital": ["O1", "O2", "Oz", "PO3", "PO4", "POz"],
    "temporal": ["T7", "T8", "TP7", "TP8", "P7", "P8", "FT7", "FT8"],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gated ds003522 D1 cropped-rest artifact-control extraction.")
    parser.add_argument("--dataset", default="ds003522")
    parser.add_argument("--verification-csv", default="outputs/download_recovery/ds003522_post_download_verification.csv")
    parser.add_argument("--ptp-threshold-uv", type=float, default=250.0)
    parser.add_argument("--ptp-trim-quantile", type=float, default=0.95)
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    out_dir = project_path("outputs/d1_artifact_control")
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "ds003522_d1_artifact_control_status.csv"

    try:
        require_verified_ds003522(project_path(args.verification_csv))
    except RuntimeError as exc:
        errors.append(str(exc))
        write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "refused", "reason": str(exc)}])
        script_finish(SCRIPT, start, outputs=[str(status_path)], errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(str(exc))

    try:
        import mne
    except Exception as exc:
        raise SystemExit(f"MNE is required for D1 extraction: {exc}") from exc
    patch_mne_eeglab_chaninfo_array()

    root = project_path("data/raw", args.dataset)
    set_files = sorted(path for path in root.rglob("*.set") if is_bids_set(path))
    people = load_crosswalk(args.dataset)
    qc_rows: list[dict[str, Any]] = []
    feature_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []

    for idx, set_path in enumerate(set_files, 1):
        relative = rel(root, set_path)
        entities = parse_entities(relative)
        person = people.get(entities["bids_subject"], {})
        event_path = set_path.with_name(set_path.name.replace("_eeg.set", "_events.tsv"))
        segments = rest_segments_from_events(read_tsv(event_path))
        if not segments:
            warnings.append(f"No eyes-open/eyes-closed rest blocks identified: {relative}")
            continue
        try:
            raw = mne.io.read_raw_eeglab(set_path, preload=True, verbose="ERROR")
            picks = mne.pick_types(raw.info, eeg=True, eog=False, ecg=False, emg=False, misc=False)
            if len(picks) == 0:
                picks = np.arange(len(raw.ch_names))
            ch_names = [raw.ch_names[int(pick)] for pick in picks]
            sfreq = float(raw.info["sfreq"])
            for condition, blocks in sorted(segments.items()):
                data = concatenate_blocks(raw, picks, blocks)
                if data.shape[1] < int(8 * sfreq):
                    warnings.append(f"Short condition skipped: {relative} {condition}")
                    continue
                epoch_data = make_epochs(data, sfreq, duration_sec=4.0)
                ptp_uv = np.ptp(epoch_data, axis=2).max(axis=1) * 1e6 if epoch_data.size else np.array([])
                keep = np.isfinite(ptp_uv) & (ptp_uv <= args.ptp_threshold_uv)
                common = {
                    "dataset_id": args.dataset,
                    "relative_path": relative,
                    "bids_subject": entities["bids_subject"],
                    "stable_person_id": person.get("stable_person_id", ""),
                    "session": entities["session"],
                    "task": entities["task"],
                    "group": person.get("group", ""),
                    "group_normalized": person.get("group_normalized", ""),
                    "condition": condition,
                    "n_channels_total": len(ch_names),
                    "sfreq_hz": sfreq,
                    "segment_duration_sec": round(data.shape[1] / sfreq, 6),
                    "n_epochs_total": int(len(epoch_data)),
                    "ptp_threshold_uv": args.ptp_threshold_uv,
                    "ptp_trim_quantile": args.ptp_trim_quantile,
                }
                trim_threshold_uv = float(np.nanquantile(ptp_uv, args.ptp_trim_quantile)) if len(ptp_uv) else float("nan")
                trim_keep = np.isfinite(ptp_uv) & (ptp_uv <= trim_threshold_uv)
                branches = [
                    ("all_epochs", epoch_data, np.ones(len(epoch_data), dtype=bool), ""),
                    ("artifact_clean_ptp250uv", epoch_data[keep], keep, args.ptp_threshold_uv),
                    ("artifact_trim_ptp95", epoch_data[trim_keep], trim_keep, trim_threshold_uv),
                ]
                for branch, branch_epochs, branch_keep, branch_threshold_uv in branches:
                    qc = qc_row(common, branch, branch_epochs, branch_keep, ptp_uv, branch_threshold_uv)
                    qc_rows.append(qc)
                    if len(branch_epochs) == 0:
                        continue
                    freqs, psd_by_channel = compute_psd(branch_epochs, sfreq)
                    for region, indices in region_indices(ch_names).items():
                        if not indices:
                            continue
                        psd = np.nanmean(psd_by_channel[indices, :], axis=0)
                        feature_rows.extend(feature_rows_for_region(common, branch, region, len(indices), freqs, psd, qc))
            status_rows.append({"dataset_id": args.dataset, "relative_path": relative, "status": "processed", "notes": ""})
        except Exception as exc:
            errors.append(f"{relative}: {exc}")
            status_rows.append({"dataset_id": args.dataset, "relative_path": relative, "status": "failed", "notes": str(exc)})
        if idx % 20 == 0:
            print(f"processed {idx}/{len(set_files)} ds003522 recordings", flush=True)

    outputs = [
        project_path("outputs/qc/artifact_qc_metrics.csv"),
        project_path("outputs/features/d1_rest_features.csv"),
        status_path,
    ]
    write_rows_csv(outputs[0], qc_rows)
    write_rows_csv(outputs[1], feature_rows)
    write_rows_csv(status_path, status_rows)
    if not feature_rows:
        errors.append("No D1 feature rows were extracted.")
    script_finish(SCRIPT, start, outputs=[str(path) for path in outputs], warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
    if errors:
        raise SystemExit("D1 extraction completed with errors; see logs/run_log.jsonl and status CSV.")


def require_verified_ds003522(verification_csv: Path) -> None:
    if not verification_csv.exists():
        raise RuntimeError(f"Refusing to run: missing verification CSV {verification_csv}.")
    rows = read_rows_csv(verification_csv)
    if not rows:
        raise RuntimeError(f"Refusing to run: verification CSV has no rows: {verification_csv}.")
    first = rows[0]
    for column, expected in {"summary_set_count": 200, "summary_fdt_count": 200, "summary_paired_count": 200, "summary_missing_fdt_count": 0}.items():
        try:
            observed = int(float(first.get(column, "")))
        except Exception as exc:
            raise RuntimeError(f"Refusing to run: verification column {column} is not numeric.") from exc
        if observed != expected:
            raise RuntimeError(f"Refusing to run: verification {column}={observed}, expected {expected}.")
    if sum(1 for row in rows if row.get("mne_read_test_status") == "passed") < 3:
        raise RuntimeError("Refusing to run: fewer than 3 MNE read-tests passed.")


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
    }


def load_crosswalk(dataset: str) -> dict[str, dict[str, str]]:
    rows = [row for row in read_rows_csv(project_path("outputs/metadata/subject_crosswalk.csv")) if row.get("dataset_id") == dataset]
    return {row.get("bids_subject", ""): row for row in rows}


def patch_mne_eeglab_chaninfo_array() -> None:
    import mne.io.eeglab.eeglab as eeglab_mod

    original = getattr(eeglab_mod, "_codex_original_get_montage_information", None)
    if original is None:
        original = eeglab_mod._get_montage_information
        eeglab_mod._codex_original_get_montage_information = original

    def compat_get_montage_information(eeg: Any, get_pos: bool, *, montage_units: str) -> Any:
        chaninfo = getattr(eeg, "chaninfo", None)
        if chaninfo is not None and not hasattr(chaninfo, "get"):
            eeg.chaninfo = {}
        return original(eeg, get_pos, montage_units=montage_units)

    eeglab_mod._get_montage_information = compat_get_montage_information


def rest_segments_from_events(rows: list[dict[str, str]]) -> dict[str, list[tuple[float, float]]]:
    onsets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        label = (row.get("trial_type") or row.get("value") or "").lower()
        condition = ""
        if "eyes closed" in label:
            condition = "eyes_closed"
        elif "eyes open" in label:
            condition = "eyes_open"
        if not condition:
            continue
        try:
            onset = float(row.get("onset", ""))
        except Exception:
            continue
        onsets[condition].append(onset)
    return {condition: onset_blocks(sorted(values)) for condition, values in onsets.items() if values}


def onset_blocks(onsets: list[float]) -> list[tuple[float, float]]:
    blocks = []
    start = onsets[0]
    last = onsets[0]
    gaps = []
    for onset in onsets[1:]:
        gap = onset - last
        if 0 < gap <= 3.0:
            gaps.append(gap)
            last = onset
            continue
        step = median(gaps) if gaps else 1.0
        blocks.append((start, last + step))
        start = onset
        last = onset
        gaps = []
    step = median(gaps) if gaps else 1.0
    blocks.append((start, last + step))
    return [(max(0.0, start), max(start, stop)) for start, stop in blocks if stop > start]


def median(values: list[float]) -> float:
    if not values:
        return 1.0
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def concatenate_blocks(raw: Any, picks: np.ndarray, blocks: list[tuple[float, float]]) -> np.ndarray:
    sfreq = float(raw.info["sfreq"])
    pieces = []
    for start, stop in blocks:
        start_idx = max(0, int(round(start * sfreq)))
        stop_idx = min(raw.n_times, int(round(stop * sfreq)))
        if stop_idx > start_idx:
            pieces.append(raw.get_data(picks=picks, start=start_idx, stop=stop_idx))
    return np.concatenate(pieces, axis=1) if pieces else np.empty((len(picks), 0))


def make_epochs(data: np.ndarray, sfreq: float, duration_sec: float = 4.0) -> np.ndarray:
    samples = int(round(duration_sec * sfreq))
    n_epochs = data.shape[1] // samples
    if n_epochs <= 0:
        return np.empty((0, data.shape[0], samples))
    trimmed = data[:, : n_epochs * samples]
    return trimmed.reshape(data.shape[0], n_epochs, samples).transpose(1, 0, 2)


def compute_psd(epoch_data: np.ndarray, sfreq: float) -> tuple[np.ndarray, np.ndarray]:
    nperseg = int(min(max(128, round(4 * sfreq)), epoch_data.shape[2]))
    freqs, psd = welch(epoch_data, fs=sfreq, nperseg=nperseg, noverlap=nperseg // 2, axis=2)
    return freqs, np.nanmean(psd, axis=0)


def region_indices(ch_names: list[str]) -> dict[str, list[int]]:
    lower = [name.lower() for name in ch_names]
    out = {"global": list(range(len(ch_names)))}
    for region, labels in REGIONS.items():
        if region == "global":
            continue
        targets = {label.lower() for label in labels}
        out[region] = [idx for idx, name in enumerate(lower) if name in targets]
    return out


def qc_row(common: dict[str, Any], branch: str, epochs: np.ndarray, keep: np.ndarray, ptp_uv: np.ndarray, branch_threshold_uv: Any) -> dict[str, Any]:
    usable = int(len(epochs))
    total = int(common["n_epochs_total"])
    return {
        **common,
        "artifact_branch": branch,
        "branch_ptp_threshold_uv": branch_threshold_uv,
        "n_epochs_used": usable,
        "usable_epoch_fraction": usable / total if total else "",
        "ptp_uv_median": float(np.nanmedian(ptp_uv)) if len(ptp_uv) else "",
        "ptp_uv_p95": float(np.nanpercentile(ptp_uv, 95)) if len(ptp_uv) else "",
        "qc_status": "processed" if usable else "no_epochs_after_artifact_filter",
        "notes": "",
    }


def feature_rows_for_region(common: dict[str, Any], branch: str, region: str, n_channels_region: int, freqs: np.ndarray, psd: np.ndarray, qc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    denom = integrate_power(freqs, psd, 1.0, 45.0)
    powers = {name: integrate_power(freqs, psd, low, high) for name, (low, high) in BANDS.items()}
    base = {
        **common,
        "artifact_branch": branch,
        "region": region,
        "n_channels_region": n_channels_region,
        "n_epochs_used": qc["n_epochs_used"],
        "usable_epoch_fraction": qc["usable_epoch_fraction"],
        "emg_index_region": powers["low_gamma_or_emg"] / denom if denom and math.isfinite(denom) and denom > 0 else np.nan,
        "line_noise_index_region": integrate_power(freqs, psd, 58.0, 62.0) / integrate_power(freqs, psd, 1.0, 90.0) if integrate_power(freqs, psd, 1.0, 90.0) > 0 else np.nan,
    }
    for band, value in powers.items():
        rows.append({**base, "feature_family": "band_power", "feature_name": f"absolute_{band}_power", "feature_value": value, "unit": "power"})
        rows.append({**base, "feature_family": "relative_band_power", "feature_name": f"relative_{band}_power", "feature_value": value / denom if denom and math.isfinite(denom) and denom > 0 else np.nan, "unit": "proportion_1_45Hz"})
    theta = powers["theta"]
    alpha = powers["alpha"]
    rows.append({**base, "feature_family": "ratio", "feature_name": "theta_alpha_ratio", "feature_value": theta / alpha if alpha > 0 else np.nan, "unit": "ratio"})
    rows.append({**base, "feature_family": "ratio", "feature_name": "alpha_theta_ratio", "feature_value": alpha / theta if theta > 0 else np.nan, "unit": "ratio"})
    rows.append({**base, "feature_family": "distribution", "feature_name": "spectral_entropy_1_45", "feature_value": spectral_entropy(freqs, psd), "unit": "unitless"})
    iaf, alpha_peak_power = alpha_peak(freqs, psd)
    rows.append({**base, "feature_family": "alpha", "feature_name": "iaf_peak_frequency", "feature_value": iaf, "unit": "Hz"})
    rows.append({**base, "feature_family": "alpha", "feature_name": "alpha_peak_power", "feature_value": alpha_peak_power, "unit": "power"})
    slope, offset = loglog_slope(freqs, psd)
    rows.append({**base, "feature_family": "aperiodic_loglog", "feature_name": "aperiodic_exponent", "feature_value": -slope if math.isfinite(slope) else np.nan, "unit": "unitless"})
    rows.append({**base, "feature_family": "aperiodic_loglog", "feature_name": "aperiodic_offset", "feature_value": offset, "unit": "log10_power"})
    return rows


def integrate_power(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high) & np.isfinite(psd)
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(psd[mask], freqs[mask]))


def spectral_entropy(freqs: np.ndarray, psd: np.ndarray) -> float:
    mask = (freqs >= 1.0) & (freqs <= 45.0) & np.isfinite(psd)
    values = np.maximum(np.asarray(psd[mask], dtype=float), 0)
    total = float(np.sum(values))
    if total <= 0 or len(values) <= 1:
        return float("nan")
    probs = values / total
    probs = probs[probs > 0]
    return float(-(probs * np.log(probs)).sum() / np.log(len(values)))


def alpha_peak(freqs: np.ndarray, psd: np.ndarray) -> tuple[float, float]:
    mask = (freqs >= 7.0) & (freqs <= 13.0) & np.isfinite(psd)
    if np.count_nonzero(mask) < 2:
        return float("nan"), float("nan")
    idx = int(np.argmax(psd[mask]))
    return float(freqs[mask][idx]), float(psd[mask][idx])


def loglog_slope(freqs: np.ndarray, psd: np.ndarray) -> tuple[float, float]:
    mask = (freqs >= 1.0) & (freqs <= 40.0) & np.isfinite(psd) & (psd > 0)
    if np.count_nonzero(mask) < 3:
        return float("nan"), float("nan")
    slope, offset = np.polyfit(np.log10(freqs[mask]), np.log10(psd[mask]), 1)
    return float(slope), float(offset)


if __name__ == "__main__":
    main()
