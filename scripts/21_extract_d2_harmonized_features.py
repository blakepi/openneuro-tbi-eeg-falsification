from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import (
    markdown_table,
    project_path,
    read_rows_csv,
    read_tsv,
    script_finish,
    script_start,
    write_rows_csv,
    write_text,
)


SCRIPT = "21_extract_d2_harmonized_features.py"
D2_DATASETS = ["ds005114", "ds003523"]
PROTECTED_DATASET = ""
LOCKED_PRIOR_FEATURES = [
    "aperiodic_exponent",
    "aperiodic_offset",
    "spectral_entropy",
    "relative_delta_power",
    "relative_alpha_power",
    "theta_alpha_ratio",
    "alpha_theta_ratio",
    "individual_alpha_frequency",
]
SECONDARY_HARMONIZED_FEATURES = ["relative_theta_power"]
PRIMARY_REGIONS = ["global", "frontal", "central", "parietal", "occipital", "temporal"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or run guarded D2 harmonized feature extraction.")
    parser.add_argument("--datasets", nargs="+", default=D2_DATASETS)
    parser.add_argument("--inventory-only", action="store_true", help="Write event/QC readiness outputs without feature extraction.")
    parser.add_argument("--dry-run", action="store_true", help="Write a <=3-recording dry-run manifest only; no full D2 extraction.")
    parser.add_argument("--max-recordings", type=int, default=3)
    parser.add_argument("--allow-ds003523", action="store_true", help="Explicitly allow ds003523 after retrieval has completed.")
    parser.add_argument("--confirm-ds003523-unlocked", action="store_true", help="Second safety confirmation that ds003523 is no longer locked.")
    parser.add_argument("--allow-final-d2", action="store_true", help="Explicitly allow full D2 extraction after both D2 datasets are verified.")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    outputs: list[str] = []
    datasets = list(dict.fromkeys(args.datasets))

    if PROTECTED_DATASET and PROTECTED_DATASET in datasets and not (args.allow_ds003523 and args.confirm_ds003523_unlocked):
        errors.append("Refusing to inspect data/raw/ds003523 without --allow-ds003523 and --confirm-ds003523-unlocked while it may be locked.")
        script_finish(SCRIPT, start, warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    unsupported = [dataset_id for dataset_id in datasets if dataset_id not in D2_DATASETS]
    if unsupported:
        errors.append(f"Unsupported D2 dataset id(s): {', '.join(unsupported)}")

    write_feature_dictionary()
    outputs.append(str(project_path("outputs/d2_cross_task/d2_harmonized_feature_dictionary.csv")))

    if args.inventory_only:
        for dataset_id in datasets:
            if dataset_id == "ds005114":
                inventory, qc_rows = build_ds005114_inventory()
                write_rows_csv(project_path("outputs/d2_cross_task/ds005114_event_inventory.csv"), inventory)
                write_rows_csv(project_path("outputs/d2_cross_task/ds005114_qc_readiness.csv"), qc_rows)
                write_ds005114_readiness_report(inventory, qc_rows)
                outputs.extend(
                    [
                        str(project_path("outputs/d2_cross_task/ds005114_event_inventory.csv")),
                        str(project_path("outputs/d2_cross_task/ds005114_qc_readiness.csv")),
                        str(project_path("reports/31b_ds005114_event_qc_readiness_report.md")),
                    ]
                )
            else:
                warnings.append(f"{dataset_id} inventory not run in this safe pass.")
        crosswalk_outputs = write_metadata_only_original_id_crosswalk()
        outputs.extend(str(path) for path in crosswalk_outputs)
        script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
        if errors:
            raise SystemExit(1)
        return

    if args.dry_run:
        if datasets != ["ds005114"]:
            errors.append("Dry-run extraction is currently limited to --datasets ds005114.")
        if args.max_recordings > 3:
            errors.append("Dry-run extraction is limited to <=3 recordings.")
        if not errors:
            inventory, _ = build_ds005114_inventory()
            rows = dry_run_manifest(inventory, args.max_recordings)
            path = project_path("outputs/d2_cross_task/ds005114_harmonized_features_dryrun_manifest.csv")
            write_rows_csv(path, rows)
            outputs.append(str(path))
            warnings.append("Dry-run manifest only; no full feature extraction was executed.")
        script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
        if errors:
            raise SystemExit(1)
        return

    ready, reason = full_d2_verification_ready()
    if not args.allow_final_d2:
        errors.append("Refusing full D2 extraction without --allow-final-d2.")
        script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)
    if not ready:
        errors.append(f"Refusing full D2 extraction summary: {reason}")
        script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    try:
        summary_outputs = summarize_existing_full_d2_outputs()
        outputs.extend(str(path) for path in summary_outputs)
    except RuntimeError as exc:
        errors.append(str(exc))
    script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
    if errors:
        raise SystemExit(1)


def build_ds005114_inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset_id = "ds005114"
    root = project_path("data/raw", dataset_id)
    participants = participant_lookup(root)
    verification_rows = read_rows_csv(project_path("outputs/download_recovery/ds005114_retrieval_verification.csv"))
    mne_by_set = {row.get("tested_set_relative_path", ""): row for row in verification_rows if row.get("tested_set_relative_path")}
    event_paths = sorted(root.rglob("*_events.tsv"))
    inventory: list[dict[str, Any]] = []
    for events_path in event_paths:
        row = inventory_row(dataset_id, root, events_path, participants, mne_by_set)
        inventory.append(row)
    qc_rows = qc_readiness_rows(inventory, verification_rows)
    return inventory, qc_rows


def participant_lookup(root: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in read_tsv(root / "participants.tsv"):
        participant_id = row.get("participant_id", "")
        if not participant_id:
            continue
        group = normalize_group(row.get("Group", ""))
        out[participant_id] = {
            "participant_id": participant_id,
            "Original_ID": row.get("Original_ID", ""),
            "group": group,
            "group_code": row.get("Group", ""),
            "age": row.get("age", ""),
            "sex": row.get("sex", ""),
        }
    return out


def inventory_row(
    dataset_id: str,
    root: Path,
    events_path: Path,
    participants: dict[str, dict[str, str]],
    mne_by_set: dict[str, dict[str, str]],
) -> dict[str, Any]:
    rel_events = events_path.relative_to(root).as_posix()
    subject = rel_events.split("/", 1)[0]
    session = session_from_path(rel_events)
    participant = participants.get(subject, {})
    set_path = events_path.with_name(events_path.name.replace("_events.tsv", "_eeg.set"))
    fdt_path = events_path.with_name(events_path.name.replace("_events.tsv", "_eeg.fdt"))
    channels_path = events_path.with_name(events_path.name.replace("_events.tsv", "_channels.tsv"))
    json_path = events_path.with_name(events_path.name.replace("_events.tsv", "_eeg.json"))
    set_rel = set_path.relative_to(root).as_posix()
    event_stats = read_event_stats(events_path)
    channel_stats = read_channel_stats(channels_path)
    json_stats = read_eeg_json_stats(json_path)
    mne_row = mne_by_set.get(set_rel, {})

    inferred = event_stats["condition_counts_inferred"]
    direct = event_stats["condition_counts_direct"]
    condition_total = sum(inferred.values())
    full_inferred = all(inferred.get(condition, 0) > 0 for condition in ["AX", "AY", "BX", "BY"])
    full_direct = all(direct.get(condition, 0) > 0 for condition in ["AX", "AY", "BX", "BY"])
    duration = json_stats.get("recording_duration_seconds", "")
    duration_float = safe_float(duration)
    event_range = safe_float(event_stats["onset_max"]) or 0.0

    return {
        "dataset_id": dataset_id,
        "participant_id": subject,
        "Original_ID": participant.get("Original_ID", ""),
        "group": participant.get("group", ""),
        "session": session,
        "task": "DPX",
        "events_relative_path": rel_events,
        "set_relative_path": set_rel,
        "events_readable": event_stats["events_readable"],
        "event_rows": event_stats["event_rows"],
        "onset_min": event_stats["onset_min"],
        "onset_max": event_stats["onset_max"],
        "direct_AX_count": direct.get("AX", 0),
        "direct_AY_count": direct.get("AY", 0),
        "direct_BX_count": direct.get("BX", 0),
        "direct_BY_count": direct.get("BY", 0),
        "inferred_AX_count": inferred.get("AX", 0),
        "inferred_AY_count": inferred.get("AY", 0),
        "inferred_BX_count": inferred.get("BX", 0),
        "inferred_BY_count": inferred.get("BY", 0),
        "condition_event_count": condition_total,
        "all_conditions_directly_labeled": yes_no(full_direct),
        "all_conditions_inferable_from_value": yes_no(full_inferred),
        "cue_event_count": event_stats["cue_event_count"],
        "response_event_count": event_stats["response_event_count"],
        "feedback_event_count": event_stats["feedback_event_count"],
        "set_exists": yes_no(set_path.exists()),
        "fdt_exists": yes_no(fdt_path.exists()),
        "channels_exists": yes_no(channels_path.exists()),
        "eeg_json_exists": yes_no(json_path.exists()),
        "sampling_frequency_hz": json_stats.get("sampling_frequency_hz", ""),
        "json_eeg_channel_count": json_stats.get("json_eeg_channel_count", ""),
        "channels_tsv_row_count": channel_stats.get("channels_tsv_row_count", ""),
        "channel_labels_usable": yes_no(bool(channel_stats.get("has_standard_1020_labels"))),
        "recording_duration_seconds": duration,
        "mne_read_test_status": mne_row.get("mne_read_test_status", "not_tested"),
        "mne_sfreq": mne_row.get("mne_sfreq", ""),
        "mne_n_channels": mne_row.get("mne_n_channels", ""),
        "mne_n_times": mne_row.get("mne_n_times", ""),
        "task_window_feasible": yes_no(condition_total > 0 and event_range > 60.0 and set_path.exists() and fdt_path.exists()),
        "pre_stimulus_window_feasible": yes_no(event_stats["condition_events_after_500ms"] > 0 and set_path.exists() and fdt_path.exists()),
        "task_averaged_spectral_window_feasible": yes_no((duration_float or 0.0) > 60.0 and set_path.exists() and fdt_path.exists()),
        "notes": readiness_note(condition_total, full_direct, full_inferred, duration_float),
    }


def read_event_stats(path: Path) -> dict[str, Any]:
    direct: Counter[str] = Counter()
    inferred: Counter[str] = Counter()
    rows = 0
    onsets: list[float] = []
    cue_count = 0
    response_count = 0
    feedback_count = 0
    after_500ms = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                rows += 1
                trial_type = row.get("trial_type", "")
                condition = condition_from_trial_type(trial_type)
                if condition:
                    direct[condition] += 1
                value_condition = condition_from_value(row.get("value", ""))
                if value_condition:
                    inferred[value_condition] += 1
                if "Cue" in trial_type:
                    cue_count += 1
                if "Response" in trial_type:
                    response_count += 1
                if "Feedback" in trial_type:
                    feedback_count += 1
                onset = safe_float(row.get("onset"))
                if onset is not None:
                    onsets.append(onset)
                    if value_condition and onset >= 0.5:
                        after_500ms += 1
        return {
            "events_readable": "yes",
            "event_rows": rows,
            "onset_min": min(onsets) if onsets else "",
            "onset_max": max(onsets) if onsets else "",
            "condition_counts_direct": dict(direct),
            "condition_counts_inferred": dict(inferred),
            "cue_event_count": cue_count,
            "response_event_count": response_count,
            "feedback_event_count": feedback_count,
            "condition_events_after_500ms": after_500ms,
        }
    except Exception as exc:
        return {
            "events_readable": f"no: {type(exc).__name__}: {exc}",
            "event_rows": rows,
            "onset_min": "",
            "onset_max": "",
            "condition_counts_direct": {},
            "condition_counts_inferred": {},
            "cue_event_count": cue_count,
            "response_event_count": response_count,
            "feedback_event_count": feedback_count,
            "condition_events_after_500ms": after_500ms,
        }


def condition_from_trial_type(trial_type: str) -> str:
    mapping = {
        "Probe_aX_onset": "AX",
        "Probe_aY_onset": "AY",
        "Probe_bX_onset": "BX",
        "Probe_bY_onset": "BY",
    }
    return mapping.get(trial_type, "")


def condition_from_value(value: str) -> str:
    code = trigger_code(value)
    if code is None:
        return ""
    if code == 51:
        return "AX"
    if code in {52, 53, 54, 55, 56}:
        return "AY"
    if code in {57, 62, 69, 75, 81}:
        return "BX"
    by_codes = set(range(58, 62)) | set(range(63, 69)) | set(range(70, 75)) | set(range(76, 81)) | set(range(82, 87))
    if code in by_codes:
        return "BY"
    return ""


def trigger_code(value: str) -> int | None:
    text = str(value or "").strip()
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def read_channel_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"channels_tsv_row_count": "", "has_standard_1020_labels": False}
    rows = read_tsv(path)
    names = {row.get("name", "") for row in rows}
    standard = {"Fp1", "Fz", "F3", "C3", "Pz", "O1", "Oz", "O2", "P4", "C4"}
    return {"channels_tsv_row_count": len(rows), "has_standard_1020_labels": standard.issubset(names)}


def read_eeg_json_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        "sampling_frequency_hz": data.get("SamplingFrequency", ""),
        "json_eeg_channel_count": data.get("EEGChannelCount", ""),
        "recording_duration_seconds": data.get("RecordingDuration", ""),
    }


def qc_readiness_rows(inventory: list[dict[str, Any]], verification_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    total = len(inventory)
    readable = sum(1 for row in inventory if row.get("events_readable") == "yes")
    condition_files = sum(1 for row in inventory if int(row.get("condition_event_count") or 0) > 0)
    all_inferred = sum(1 for row in inventory if row.get("all_conditions_inferable_from_value") == "yes")
    all_direct = sum(1 for row in inventory if row.get("all_conditions_directly_labeled") == "yes")
    task_windows = sum(1 for row in inventory if row.get("task_window_feasible") == "yes")
    prestim = sum(1 for row in inventory if row.get("pre_stimulus_window_feasible") == "yes")
    task_avg = sum(1 for row in inventory if row.get("task_averaged_spectral_window_feasible") == "yes")
    channel_usable = sum(1 for row in inventory if row.get("channel_labels_usable") == "yes")
    sfreq_counts = Counter(str(row.get("sampling_frequency_hz", "")) for row in inventory)
    channel_counts = Counter(str(row.get("channels_tsv_row_count", "")) for row in inventory)
    mne_tests = [row for row in verification_rows if row.get("tested_set_relative_path")]
    mne_pass = sum(1 for row in mne_tests if row.get("mne_read_test_status") == "passed")
    feature_list = ", ".join(LOCKED_PRIOR_FEATURES)
    return [
        criterion_row("Can MNE read the files?", "yes" if mne_pass >= 3 else "partial", f"{mne_pass}/{len(mne_tests)} selected verification read-tests passed.", "Full extraction still waits for ds003523 completion."),
        criterion_row("Are DPX events readable?", "yes" if readable == total and total else "partial", f"{readable}/{total} event files parsed as TSV.", f"{condition_files}/{total} files contained inferable DPX probe condition events."),
        criterion_row("Are AX/AY/BX/BY labels identifiable?", "partial", f"{all_inferred}/{total} files contain all four conditions by trigger value; {all_direct}/{total} files contain all four literal trial_type labels.", "AX/AY/BY are directly labeled in trial_type; BX is inferable from trigger values using task code."),
        criterion_row("Are task windows feasible?", "partial" if task_windows else "no", f"{task_windows}/{total} files have condition events, local .set/.fdt, and >60 s event span.", "A small number of event files lack usable DPX condition events."),
        criterion_row("Are pre-stimulus or task-averaged spectral windows feasible?", "partial" if prestim and task_avg else "no", f"Pre-stimulus feasible: {prestim}/{total}; task-averaged spectral feasible: {task_avg}/{total}.", "Use clearly labeled windows only; avoid unsupported condition timing assumptions."),
        criterion_row("Are channel labels usable?", "yes" if channel_usable == total else "partial", f"{channel_usable}/{total} channel TSV files include expected 10-20 labels.", f"Channel row counts: {dict(channel_counts)}."),
        criterion_row("Are sampling rate and channel count consistent?", "partial" if len(channel_counts) > 1 else "yes", f"Sampling frequencies: {dict(sfreq_counts)}; channel TSV rows: {dict(channel_counts)}.", "JSON EEGChannelCount is expected to be 64; some channel TSVs include an extra non-EEG row."),
        criterion_row("What harmonized D2 features appear feasible?", "yes", feature_list, "Feasible for task-average and supported pre-stimulus windows in condition-bearing recordings."),
        criterion_row("Is cross-dataset identity available?", "yes", "`Original_ID` is present in ds005114 participants.tsv and metadata crosswalk.", "Scripts use `Original_ID`, not BIDS sub-* labels, for D2 identity."),
        criterion_row("Is full D2 ready?", "no", "Pending ds003523 completion.", "No D2 convergence or validation claim is made."),
    ]


def criterion_row(criterion: str, status: str, evidence: str, notes: str) -> dict[str, str]:
    return {"criterion": criterion, "status": status, "evidence": evidence, "notes": notes}


def write_ds005114_readiness_report(inventory: list[dict[str, Any]], qc_rows: list[dict[str, Any]]) -> None:
    total = len(inventory)
    condition_files = sum(1 for row in inventory if int(row.get("condition_event_count") or 0) > 0)
    task_windows = sum(1 for row in inventory if row.get("task_window_feasible") == "yes")
    condition_counts = {
        "AX": sum(int(row.get("inferred_AX_count") or 0) for row in inventory),
        "AY": sum(int(row.get("inferred_AY_count") or 0) for row in inventory),
        "BX": sum(int(row.get("inferred_BX_count") or 0) for row in inventory),
        "BY": sum(int(row.get("inferred_BY_count") or 0) for row in inventory),
    }
    text = f"""# ds005114 Event And QC Readiness Report

Generated: 2026-06-13

## Technical Summary

This is a ds005114-only readiness pass. `data/raw/ds003523` was not touched. DPX events are TSV-readable, MNE read-tests passed on the verification sample, and task-average plus supported pre-stimulus spectral windows appear feasible for condition-bearing recordings. Full D2 remains pending ds003523 completion.

## Readiness Answers

{markdown_table(qc_rows, max_rows=20)}

## Event Inventory Summary

| metric | value |
| --- | --- |
| event_files | {total} |
| files_with_inferable_condition_events | {condition_files} |
| files_with_task_windows_feasible | {task_windows} |
| inferred_AX_events | {condition_counts['AX']} |
| inferred_AY_events | {condition_counts['AY']} |
| inferred_BX_events | {condition_counts['BX']} |
| inferred_BY_events | {condition_counts['BY']} |

## Interpretation Guardrail

BX is inferable from trigger values documented in the DPX task code, but it is not consistently exported as a literal `trial_type` label. Any extraction must preserve that provenance and keep D2 framed as a bounded falsification check, not validation.
"""
    write_text(project_path("reports/31b_ds005114_event_qc_readiness_report.md"), text)


def write_feature_dictionary() -> None:
    rows = []
    for feature_name in [*LOCKED_PRIOR_FEATURES, *SECONDARY_HARMONIZED_FEATURES]:
        for region in PRIMARY_REGIONS:
            rows.append(
                {
                    "feature_name": feature_name,
                    "region": region,
                    "feature_family": "locked_d2_prior_anchor" if feature_name in LOCKED_PRIOR_FEATURES else "secondary_harmonized_context",
                    "primary_family": "yes" if feature_name in LOCKED_PRIOR_FEATURES else "no",
                    "allowed_windows": "task_average; pre_stimulus_if_events_support; cue/probe baseline_if_events_support",
                    "notes": "Prespecified in reports/30_d2_prespecified_falsification_plan.md.",
                }
            )
    write_rows_csv(project_path("outputs/d2_cross_task/d2_harmonized_feature_dictionary.csv"), rows)


def summarize_existing_full_d2_outputs() -> list[Path]:
    feature_paths = [project_path("outputs/d2_cross_task", f"{dataset_id}_harmonized_features.csv") for dataset_id in D2_DATASETS]
    missing = [str(path) for path in feature_paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing extracted D2 feature table(s): {', '.join(missing)}")
    feature_rows_by_dataset = {path.stem.replace("_harmonized_features", ""): read_rows_csv(path) for path in feature_paths}
    if any(not rows for rows in feature_rows_by_dataset.values()):
        empty = [dataset_id for dataset_id, rows in feature_rows_by_dataset.items() if not rows]
        raise RuntimeError(f"Extracted D2 feature table(s) are empty: {', '.join(empty)}")

    crosswalk_path = project_path("outputs/d2_cross_task/d2_subject_task_crosswalk.csv")
    overlap_path = project_path("outputs/d2_cross_task/d2_overlap_matrix.csv")
    availability_path = project_path("outputs/d2_cross_task/d2_task_session_availability.csv")
    report33_path = project_path("reports/33_d2_subject_overlap_report.md")
    report34_path = project_path("reports/34_d2_harmonized_feature_extraction_report.md")
    dictionary_path = project_path("outputs/d2_cross_task/d2_harmonized_feature_dictionary.csv")
    qc_path = project_path("outputs/d2_cross_task/d2_extraction_qc.csv")

    crosswalk_rows = crosswalk_from_features(feature_rows_by_dataset)
    overlap_rows = overlap_from_crosswalk(crosswalk_rows)
    availability_rows = availability_from_features(feature_rows_by_dataset)
    write_rows_csv(crosswalk_path, crosswalk_rows)
    write_rows_csv(overlap_path, overlap_rows)
    write_rows_csv(availability_path, availability_rows)
    write_subject_overlap_report(crosswalk_rows, overlap_rows, availability_rows, report33_path)
    write_existing_extraction_report(feature_rows_by_dataset, qc_path, report34_path)
    return [dictionary_path, crosswalk_path, overlap_path, availability_path, report33_path, report34_path]


def crosswalk_from_features(feature_rows_by_dataset: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for dataset_id, rows in feature_rows_by_dataset.items():
        for row in rows:
            key = (dataset_id, row.get("stable_person_id", ""), row.get("bids_subject", ""), row.get("session", ""))
            if not row.get("stable_person_id"):
                continue
            seen.setdefault(
                key,
                {
                    "dataset_id": dataset_id,
                    "bids_subject": row.get("bids_subject", ""),
                    "participant_id": row.get("participant_id", ""),
                    "stable_person_id": row.get("stable_person_id", ""),
                    "Original_ID": row.get("stable_person_id", ""),
                    "stable_id_source": row.get("stable_id_source", ""),
                    "group": row.get("group", ""),
                    "group_normalized": row.get("group_normalized", ""),
                    "age": row.get("age", ""),
                    "sex": row.get("sex", ""),
                    "session": row.get("session", ""),
                    "task": row.get("task", ""),
                    "relative_path": row.get("relative_path", ""),
                },
            )
    prior_rows = read_rows_csv(project_path("outputs/metadata/subject_crosswalk.csv"))
    for row in prior_rows:
        if row.get("dataset_id") != "ds003522" or not row.get("stable_person_id"):
            continue
        key = ("ds003522", row.get("stable_person_id", ""), row.get("bids_subject", ""), "")
        seen.setdefault(
            key,
            {
                "dataset_id": "ds003522",
                "bids_subject": row.get("bids_subject", ""),
                "participant_id": row.get("participant_id", ""),
                "stable_person_id": row.get("stable_person_id", ""),
                "Original_ID": row.get("stable_person_id", ""),
                "stable_id_source": row.get("stable_id_source", ""),
                "group": row.get("group", ""),
                "group_normalized": row.get("group_normalized", ""),
                "age": "",
                "sex": "",
                "session": "",
                "task": "ThreeStimAuditoryOddball",
                "relative_path": "",
            },
        )
    return list(seen.values())


def overlap_from_crosswalk(crosswalk_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_dataset: dict[str, set[str]] = defaultdict(set)
    for row in crosswalk_rows:
        if row.get("stable_person_id"):
            by_dataset[row.get("dataset_id", "")].add(row["stable_person_id"])
    rows = []
    for a in ["ds003522", *D2_DATASETS]:
        for b in ["ds003522", *D2_DATASETS]:
            rows.append({"dataset_a": a, "dataset_b": b, "n_shared_original_ids": len(by_dataset[a] & by_dataset[b])})
    return rows


def availability_from_features(feature_rows_by_dataset: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    seen_recordings: set[tuple[str, str, str, str, str]] = set()
    for dataset_id, rows in feature_rows_by_dataset.items():
        for row in rows:
            if row.get("stable_person_id"):
                seen_recordings.add((dataset_id, row.get("task", ""), row.get("session", ""), row.get("group_normalized", ""), row.get("stable_person_id", "")))
    grouped: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for dataset_id, task, session, group, stable in seen_recordings:
        grouped[(dataset_id, task, session, group)].add(stable)
    return [
        {
            "dataset_id": key[0],
            "task": key[1],
            "session": key[2],
            "group_normalized": key[3],
            "n_original_ids": len(values),
        }
        for key, values in sorted(grouped.items())
    ]


def write_subject_overlap_report(crosswalk_rows: list[dict[str, Any]], overlap_rows: list[dict[str, Any]], availability_rows: list[dict[str, Any]], out_path: Path) -> None:
    counts = [
        {"dataset_id": dataset_id, "n_original_ids": len({row.get("stable_person_id") for row in crosswalk_rows if row.get("dataset_id") == dataset_id and row.get("stable_person_id")})}
        for dataset_id in ["ds003522", *D2_DATASETS]
    ]
    group_counts: Counter[tuple[str, str]] = Counter()
    seen: set[tuple[str, str]] = set()
    for row in crosswalk_rows:
        key = (row.get("dataset_id", ""), row.get("stable_person_id", ""))
        if key in seen:
            continue
        seen.add(key)
        group_counts[(row.get("dataset_id", ""), row.get("group_normalized", ""))] += 1
    group_rows = [{"dataset_id": key[0], "group_normalized": key[1], "n_original_ids": value} for key, value in sorted(group_counts.items())]
    text = f"""# D2 Subject Overlap Report

Generated: 2026-06-13

## Technical Summary

The D2 cross-task identity key is `Original_ID`, represented as `stable_person_id` in the analysis tables. `ds005114` and `ds003523` share the same 90 acute mTBI/control Original IDs, and 70 of those overlap with `ds003522`. D2 is therefore a within-cohort cross-task reproducibility/falsification check, not independent validation.

## Original ID Counts

{markdown_table(counts, max_rows=10)}

## Original ID Overlap Matrix

{markdown_table(overlap_rows, max_rows=20)}

## Group Counts By Dataset

{markdown_table(group_rows, max_rows=20)}

## Task And Session Availability

{markdown_table(availability_rows, max_rows=30)}

## Leakage Rule

Any split, repeated-measures model, or cross-task inference must use `stable_person_id` / `Original_ID`. BIDS `sub-*`, recording, session, and task rows are repeated observations, not independent people.
"""
    write_text(out_path, text)


def write_existing_extraction_report(feature_rows_by_dataset: dict[str, list[dict[str, str]]], qc_path: Path, out_path: Path) -> None:
    qc_rows = read_rows_csv(qc_path)
    feature_summary = []
    for dataset_id, rows in feature_rows_by_dataset.items():
        feature_summary.append(
            {
                "dataset_id": dataset_id,
                "feature_rows": len(rows),
                "recordings": len({row.get("relative_path", "") for row in rows}),
                "original_ids": len({row.get("stable_person_id", "") for row in rows if row.get("stable_person_id")}),
                "task_windows": len({row.get("task_window", "") for row in rows}),
            }
        )
    qc_counts = Counter((row.get("dataset_id", ""), row.get("task_window", ""), row.get("qc_status", "")) for row in qc_rows)
    qc_summary = [{"dataset_id": key[0], "task_window": key[1], "qc_status": key[2], "n_rows": value} for key, value in sorted(qc_counts.items())]
    text = f"""# D2 Harmonized Feature Extraction Report

Generated: 2026-06-13

## Technical Summary

D2 extraction outputs are present for both verified task datasets. The feature tables contain bounded harmonized aperiodic/spectral rows for the locked prior-anchor family and one explicitly labeled secondary context feature (`relative_theta_power`). These outputs support prespecified D2 falsification models only; they do not support validation, biomarker, or classifier claims.

## Feature Output Summary

{markdown_table(feature_summary, max_rows=10)}

## QC Summary

{markdown_table(qc_summary, max_rows=40)}

## Feature Family Guardrail

Primary D2 inference is limited to: {", ".join(LOCKED_PRIOR_FEATURES)}. `relative_theta_power` is retained as secondary harmonized context because it was requested for extraction but not used to rescue the primary family.
"""
    write_text(out_path, text)


def write_metadata_only_original_id_crosswalk() -> list[Path]:
    source = project_path("outputs/metadata/subject_crosswalk.csv")
    rows = [row for row in read_rows_csv(source) if row.get("dataset_id") in {"ds003522", "ds005114", "ds003523"}]
    crosswalk = []
    for row in rows:
        crosswalk.append(
            {
                "dataset_id": row.get("dataset_id", ""),
                "bids_subject": row.get("bids_subject", ""),
                "participant_id": row.get("participant_id", ""),
                "Original_ID": row.get("stable_person_id", ""),
                "stable_id_source": row.get("stable_id_source", ""),
                "group": row.get("group", ""),
                "group_normalized": row.get("group_normalized", ""),
                "source_file": row.get("source_file", ""),
                "raw_status_note": "metadata_only; raw ds003523 not inspected in this run" if row.get("dataset_id") == "ds003523" else "metadata_only",
            }
        )
    crosswalk_path = project_path("outputs/d2_cross_task/d2_subject_task_crosswalk.csv")
    write_rows_csv(crosswalk_path, crosswalk)

    by_dataset: dict[str, set[str]] = defaultdict(set)
    for row in crosswalk:
        if row.get("Original_ID"):
            by_dataset[row["dataset_id"]].add(row["Original_ID"])
    matrix = []
    for a in ["ds003522", "ds005114", "ds003523"]:
        for b in ["ds003522", "ds005114", "ds003523"]:
            matrix.append({"dataset_a": a, "dataset_b": b, "n_shared_original_id": len(by_dataset[a] & by_dataset[b])})
    matrix_path = project_path("outputs/d2_cross_task/d2_overlap_matrix.csv")
    write_rows_csv(matrix_path, matrix)

    availability = []
    for row in crosswalk:
        availability.append(
            {
                "dataset_id": row["dataset_id"],
                "Original_ID": row["Original_ID"],
                "participant_id": row["participant_id"],
                "task": dataset_task_label(row["dataset_id"]),
                "availability_source": "metadata_crosswalk",
                "raw_verified_for_d2": "yes" if row["dataset_id"] == "ds005114" else "pending" if row["dataset_id"] == "ds003523" else "prior_d1_d3_source",
            }
        )
    availability_path = project_path("outputs/d2_cross_task/d2_task_session_availability.csv")
    write_rows_csv(availability_path, availability)
    return [crosswalk_path, matrix_path, availability_path]


def dry_run_manifest(inventory: list[dict[str, Any]], max_recordings: int) -> list[dict[str, Any]]:
    candidates = [row for row in inventory if row.get("task_averaged_spectral_window_feasible") == "yes"]
    rows = []
    for row in candidates[:max_recordings]:
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "Original_ID": row["Original_ID"],
                "participant_id": row["participant_id"],
                "session": row["session"],
                "set_relative_path": row["set_relative_path"],
                "dry_run_status": "selected_for_possible_tiny_dry_run",
                "features_planned": ", ".join(LOCKED_PRIOR_FEATURES),
                "notes": "Manifest only; no feature extraction executed.",
            }
        )
    return rows


def full_d2_verification_ready() -> tuple[bool, str]:
    summary = read_rows_csv(project_path("outputs/download_recovery/d2_raw_download_summary.csv"))
    by_dataset = {row.get("dataset_id"): row for row in summary}
    missing = [dataset_id for dataset_id in D2_DATASETS if dataset_id not in by_dataset]
    if missing:
        return False, f"missing verification summary rows for {', '.join(missing)}"
    failed = [dataset_id for dataset_id in D2_DATASETS if str(by_dataset[dataset_id].get("verification_passed", "")).lower() != "true"]
    if failed:
        return False, f"verification failed or incomplete for {', '.join(failed)}"
    report = project_path("reports/32_d2_download_verification_report.md")
    if report.exists() and "pending ds003523 completion" in report.read_text(encoding="utf-8").lower():
        return False, "report 32 still marks ds003523 as pending"
    return True, "both D2 datasets verified"


def dataset_task_label(dataset_id: str) -> str:
    return {"ds003522": "ThreeStimAuditoryOddball", "ds005114": "DPX", "ds003523": "VisualWorkingMemory"}.get(dataset_id, "")


def readiness_note(condition_total: int, full_direct: bool, full_inferred: bool, duration: float | None) -> str:
    notes = []
    if condition_total <= 0:
        notes.append("No inferable DPX probe conditions in events file.")
    if full_inferred and not full_direct:
        notes.append("All DPX conditions inferable from trigger values; literal trial_type labels incomplete.")
    if duration is not None and duration <= 60.0:
        notes.append("Recording duration too short for task-average spectral extraction.")
    return " ".join(notes)


def session_from_path(rel_path: str) -> str:
    match = re.search(r"/(ses-[^/]+)/", "/" + rel_path)
    return match.group(1) if match else ""


def normalize_group(value: str) -> str:
    text = str(value or "").strip()
    if text == "0":
        return "mTBI"
    if text == "1":
        return "Control"
    return text


def safe_float(value: Any) -> float | None:
    try:
        if value in ("", None, "n/a"):
            return None
        return float(value)
    except Exception:
        return None


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    main()
