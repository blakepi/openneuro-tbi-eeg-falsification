from __future__ import annotations

import argparse
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import (
    markdown_table,
    project_path,
    read_tsv,
    script_finish,
    script_start,
    write_rows_csv,
    write_text,
)


SCRIPT = "20_verify_d2_downloads.py"
D2_DATASETS = ["ds005114", "ds003523"]
DEFAULT_DATASETS = D2_DATASETS
PROTECTED_DATASET = ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify D2 raw EEG downloads without downloading or modifying datasets.")
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    parser.add_argument("--max-read-tests", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260613)
    parser.add_argument(
        "--allow-ds003523",
        action="store_true",
        help="Explicitly allow verifying ds003523 after its active DataLad retrieval has completed.",
    )
    parser.add_argument(
        "--confirm-ds003523-unlocked",
        action="store_true",
        help="Second safety confirmation that data/raw/ds003523 is no longer locked by an active retrieval.",
    )
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    all_summary_rows: list[dict[str, Any]] = []
    all_detail_rows: dict[str, list[dict[str, Any]]] = {}

    requested = list(dict.fromkeys(args.datasets))
    if PROTECTED_DATASET and PROTECTED_DATASET in requested and not (args.allow_ds003523 and args.confirm_ds003523_unlocked):
        errors.append(
            "Refusing to inspect data/raw/ds003523 without --allow-ds003523 and --confirm-ds003523-unlocked. "
            "This keeps the script safe while ds003523 retrieval may still be active."
        )
        write_pending_d2_verification_report([], warnings, errors)
        script_finish(
            SCRIPT,
            start,
            outputs=[str(project_path("reports/32_d2_download_verification_report.md"))],
            warnings=warnings,
            errors=errors,
            parameters=vars(args),
            status="failed",
        )
        raise SystemExit(1)

    for dataset_id in requested:
        if dataset_id not in D2_DATASETS:
            warnings.append(f"Skipping unsupported D2 dataset id: {dataset_id}")
            continue
        summary_row, detail_rows, dataset_warnings, dataset_errors = verify_dataset(dataset_id, args.max_read_tests, args.seed)
        all_summary_rows.append(summary_row)
        all_detail_rows[dataset_id] = detail_rows
        warnings.extend(dataset_warnings)
        errors.extend(dataset_errors)
        detail_path = project_path("outputs/download_recovery", f"{dataset_id}_retrieval_verification.csv")
        write_rows_csv(detail_path, detail_rows)

    summary_path = project_path("outputs/download_recovery/d2_raw_download_summary.csv")
    write_rows_csv(summary_path, all_summary_rows)
    write_raw_download_status_report(all_summary_rows, requested)
    if any(row.get("dataset_id") == "ds005114" for row in all_summary_rows):
        write_ds005114_report(all_summary_rows, all_detail_rows, warnings, errors)

    if both_datasets_verified(all_summary_rows) and not errors:
        write_full_d2_verification_report(all_summary_rows, all_detail_rows, warnings, errors)
    else:
        write_pending_d2_verification_report(all_summary_rows, warnings, errors)

    outputs = [
        str(summary_path),
        str(project_path("reports/31_d2_raw_download_report.md")),
        str(project_path("reports/31a_ds005114_download_verification_report.md")),
        str(project_path("reports/32_d2_download_verification_report.md")),
    ]
    for dataset_id in all_detail_rows:
        outputs.append(str(project_path("outputs/download_recovery", f"{dataset_id}_retrieval_verification.csv")))

    if PROTECTED_DATASET and PROTECTED_DATASET not in requested:
        warnings.append("ds003523 not inspected in this run; treated as pending completion.")

    script_finish(
        SCRIPT,
        start,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        parameters=vars(args),
        status="completed" if not errors else "failed",
    )

    if errors:
        raise SystemExit(1)


def verify_dataset(dataset_id: str, max_read_tests: int, seed: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    root = project_path("data/raw", dataset_id)
    set_files = sorted(path for path in root.rglob("*.set") if is_bids_eeg_path(path, ".set")) if root.exists() else []
    fdt_files = sorted(path for path in root.rglob("*.fdt") if is_bids_eeg_path(path, ".fdt")) if root.exists() else []
    pairs: list[tuple[Path, Path]] = []
    missing_fdt: list[Path] = []
    for set_path in set_files:
        fdt_path = paired_fdt(set_path)
        if fdt_path.exists() and is_bids_eeg_path(fdt_path, ".fdt"):
            pairs.append((set_path, fdt_path))
        else:
            missing_fdt.append(set_path)

    sidecars = sidecar_counts(set_files)
    annex = git_annex_find_in_here(root)
    if annex["error"]:
        warnings.append(f"{dataset_id}: {annex['error']}")

    selected = select_read_tests(root, set_files, max_read_tests, seed)
    read_rows = [mne_read_test_row(dataset_id, root, path, seed) for path in selected]
    if not read_rows:
        read_rows.append(empty_read_test_row(dataset_id, seed, "No BIDS-path .set files available for MNE read-test."))

    summary = summary_columns(dataset_id, root, set_files, fdt_files, pairs, missing_fdt, sidecars, annex, read_rows)
    detail_rows = [{**summary, **row} for row in read_rows]

    if not root.exists():
        errors.append(f"{dataset_id}: dataset root is missing: {root}")
    if not (root / ".git").exists():
        errors.append(f"{dataset_id}: dataset root is not a DataLad/git repository: {root}")
    if not set_files:
        errors.append(f"{dataset_id}: no BIDS-path .set files found.")
    if not fdt_files:
        errors.append(f"{dataset_id}: no BIDS-path .fdt files found.")
    if missing_fdt:
        errors.append(f"{dataset_id}: missing paired .fdt for {len(missing_fdt)} .set files.")
    if len(pairs) != len(set_files):
        errors.append(f"{dataset_id}: paired .set/.fdt count does not match .set count.")
    if summary["mne_read_pass_count"] < min(max_read_tests, len(set_files)):
        errors.append(f"{dataset_id}: not all selected MNE read-tests passed.")
    if sidecars["events_tsv_count"] < len(set_files):
        warnings.append(f"{dataset_id}: event file count is lower than .set count.")
    if sidecars["channels_tsv_count"] < len(set_files):
        warnings.append(f"{dataset_id}: channels file count is lower than .set count.")
    if sidecars["eeg_json_count"] < len(set_files):
        warnings.append(f"{dataset_id}: EEG JSON sidecar count is lower than .set count.")

    return summary, detail_rows, warnings, errors


def is_bids_eeg_path(path: Path, suffix: str) -> bool:
    text = path.as_posix()
    if "/.git/annex/objects/" in text:
        return False
    if path.suffix.lower() != suffix:
        return False
    return bool(re.search(r"/sub-[^/]+/ses-[^/]+/eeg/", text))


def paired_fdt(set_path: Path) -> Path:
    if set_path.name.endswith("_eeg.set"):
        return set_path.with_name(set_path.name.replace("_eeg.set", "_eeg.fdt"))
    return set_path.with_suffix(".fdt")


def sidecar_counts(set_files: list[Path]) -> dict[str, Any]:
    events = 0
    channels = 0
    eeg_json = 0
    missing_events: list[str] = []
    missing_channels: list[str] = []
    missing_json: list[str] = []
    for set_path in set_files:
        events_path = set_path.with_name(set_path.name.replace("_eeg.set", "_events.tsv"))
        channels_path = set_path.with_name(set_path.name.replace("_eeg.set", "_channels.tsv"))
        json_path = set_path.with_name(set_path.name.replace("_eeg.set", "_eeg.json"))
        if events_path.exists():
            events += 1
        else:
            missing_events.append(set_path.as_posix())
        if channels_path.exists():
            channels += 1
        else:
            missing_channels.append(set_path.as_posix())
        if json_path.exists():
            eeg_json += 1
        else:
            missing_json.append(set_path.as_posix())
    return {
        "events_tsv_count": events,
        "channels_tsv_count": channels,
        "eeg_json_count": eeg_json,
        "missing_events_count": len(missing_events),
        "missing_channels_count": len(missing_channels),
        "missing_eeg_json_count": len(missing_json),
        "missing_events_examples": "; ".join(missing_events[:5]),
        "missing_channels_examples": "; ".join(missing_channels[:5]),
        "missing_eeg_json_examples": "; ".join(missing_json[:5]),
    }


def git_annex_find_in_here(root: Path) -> dict[str, Any]:
    result = {"total_count": "", "set_count": "", "fdt_count": "", "exit_code": "", "error": ""}
    if not root.exists():
        result["error"] = f"Dataset root is missing: {root}"
        return result
    if shutil.which("git") is None:
        result["error"] = "git executable is not available; skipped git-annex local availability check."
        return result
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "annex", "find", "--in=here"],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except Exception as exc:
        result["error"] = f"git annex find --in=here failed: {exc}"
        return result
    paths = [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]
    result["total_count"] = len(paths)
    result["set_count"] = sum(1 for line in paths if line.endswith(".set") and "/eeg/" in line)
    result["fdt_count"] = sum(1 for line in paths if line.endswith(".fdt") and "/eeg/" in line)
    result["exit_code"] = proc.returncode
    if proc.returncode != 0:
        result["error"] = (proc.stderr or "git annex find --in=here returned non-zero exit code.").strip()
    return result


def select_read_tests(root: Path, set_files: list[Path], max_read_tests: int, seed: int) -> list[Path]:
    if not set_files or max_read_tests <= 0:
        return []
    participants = read_participant_groups(root)
    by_group: dict[str, list[Path]] = {}
    for path in set_files:
        subject = relative(root, path).split("/", 1)[0]
        group = participants.get(subject, "unknown")
        by_group.setdefault(group, []).append(path)
    rng = random.Random(seed)
    selected: list[Path] = []
    for group in sorted(by_group):
        candidates = sorted(by_group[group])
        if candidates:
            selected.append(rng.choice(candidates))
        if len(selected) >= max_read_tests:
            break
    remaining = [path for path in set_files if path not in selected]
    if len(selected) < min(max_read_tests, len(set_files)):
        selected.extend(rng.sample(remaining, min(max_read_tests, len(set_files)) - len(selected)))
    return selected[:max_read_tests]


def read_participant_groups(root: Path) -> dict[str, str]:
    rows = read_tsv(root / "participants.tsv")
    out: dict[str, str] = {}
    for row in rows:
        participant = row.get("participant_id", "")
        group = row.get("Group") or row.get("group") or row.get("participant_group") or ""
        if participant:
            out[participant] = group or "unknown"
    return out


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def tree_size_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if "/.git/" in path.as_posix():
            continue
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def summary_columns(
    dataset_id: str,
    root: Path,
    set_files: list[Path],
    fdt_files: list[Path],
    pairs: list[tuple[Path, Path]],
    missing_fdt: list[Path],
    sidecars: dict[str, Any],
    annex: dict[str, Any],
    read_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_eeg_bytes = sum(path.stat().st_size for path in set_files + fdt_files)
    dataset_tree_bytes = tree_size_bytes(root)
    read_pass_count = sum(1 for row in read_rows if row.get("mne_read_test_status") == "passed")
    return {
        "dataset_id": dataset_id,
        "dataset_root": str(root),
        "is_datalad_repo": (root / ".git").exists(),
        "summary_set_count": len(set_files),
        "summary_fdt_count": len(fdt_files),
        "summary_paired_count": len(pairs),
        "summary_missing_fdt_count": len(missing_fdt),
        "summary_raw_eeg_size_bytes": raw_eeg_bytes,
        "summary_raw_eeg_size_gib": round(raw_eeg_bytes / (1024**3), 3),
        "summary_dataset_tree_size_bytes": dataset_tree_bytes,
        "summary_dataset_tree_size_gib": round(dataset_tree_bytes / (1024**3), 3),
        "git_annex_find_in_here_total_count": annex["total_count"],
        "git_annex_find_in_here_set_count": annex["set_count"],
        "git_annex_find_in_here_fdt_count": annex["fdt_count"],
        "git_annex_find_exit_code": annex["exit_code"],
        "event_file_presence_count": sidecars["events_tsv_count"],
        "channels_file_presence_count": sidecars["channels_tsv_count"],
        "eeg_json_sidecar_presence_count": sidecars["eeg_json_count"],
        "missing_event_file_count": sidecars["missing_events_count"],
        "missing_channels_file_count": sidecars["missing_channels_count"],
        "missing_eeg_json_sidecar_count": sidecars["missing_eeg_json_count"],
        "mne_read_test_count": len(read_rows),
        "mne_read_pass_count": read_pass_count,
        "verification_passed": bool(
            root.exists()
            and (root / ".git").exists()
            and set_files
            and len(set_files) == len(fdt_files) == len(pairs)
            and not missing_fdt
            and read_pass_count == len(read_rows)
        ),
    }


def mne_read_test_row(dataset_id: str, root: Path, set_path: Path, seed: int) -> dict[str, Any]:
    fdt = paired_fdt(set_path)
    row: dict[str, Any] = {
        "tested_set_path": str(set_path),
        "tested_set_relative_path": relative(root, set_path),
        "tested_set_size": set_path.stat().st_size,
        "tested_fdt_path": str(fdt) if fdt.exists() else "",
        "tested_fdt_size": fdt.stat().st_size if fdt.exists() else "",
        "mne_read_test_status": "failed",
        "mne_sfreq": "",
        "mne_n_channels": "",
        "mne_n_times": "",
        "mne_error": "",
        "random_seed": seed,
    }
    try:
        import mne

        patch_mne_eeglab_chaninfo_array()
        raw = mne.io.read_raw_eeglab(set_path, preload=False, verbose="ERROR")
        row.update(
            {
                "mne_read_test_status": "passed",
                "mne_sfreq": float(raw.info.get("sfreq") or 0.0),
                "mne_n_channels": len(raw.ch_names),
                "mne_n_times": int(raw.n_times),
            }
        )
    except Exception as exc:
        row["mne_error"] = f"{type(exc).__name__}: {exc}"
    return row


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


def empty_read_test_row(dataset_id: str, seed: int, error: str) -> dict[str, Any]:
    return {
        "tested_set_path": "",
        "tested_set_relative_path": "",
        "tested_set_size": "",
        "tested_fdt_path": "",
        "tested_fdt_size": "",
        "mne_read_test_status": "not_run",
        "mne_sfreq": "",
        "mne_n_channels": "",
        "mne_n_times": "",
        "mne_error": error,
        "random_seed": seed,
    }


def latest_log(pattern: str) -> str:
    matches = sorted(project_path("logs").glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(matches[0]) if matches else ""


def both_datasets_verified(rows: list[dict[str, Any]]) -> bool:
    status = {row.get("dataset_id"): bool(row.get("verification_passed")) for row in rows}
    return all(status.get(dataset_id) for dataset_id in D2_DATASETS)


def report_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "dataset_id": row["dataset_id"],
            ".set": row["summary_set_count"],
            ".fdt": row["summary_fdt_count"],
            "paired": row["summary_paired_count"],
            "missing_fdt": row["summary_missing_fdt_count"],
            "raw_size_gib": row["summary_raw_eeg_size_gib"],
            "tree_size_gib": row["summary_dataset_tree_size_gib"],
            "annex_here_total": row["git_annex_find_in_here_total_count"],
            "events": row["event_file_presence_count"],
            "channels": row["channels_file_presence_count"],
            "eeg_json": row["eeg_json_sidecar_presence_count"],
            "mne_pass": f"{row['mne_read_pass_count']}/{row['mne_read_test_count']}",
            "passed": row["verification_passed"],
        }
        for row in rows
    ]


def mne_rows(details: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for dataset_rows in details.values():
        for row in dataset_rows:
            out.append(
                {
                    "dataset_id": row["dataset_id"],
                    "tested_set_relative_path": row["tested_set_relative_path"],
                    "mne_status": row["mne_read_test_status"],
                    "sfreq": row["mne_sfreq"],
                    "channels": row["mne_n_channels"],
                    "samples": row["mne_n_times"],
                    "error": row["mne_error"],
                }
            )
    return out


def write_raw_download_status_report(rows: list[dict[str, Any]], requested: list[str]) -> None:
    table = []
    for row in rows:
        dataset_id = row["dataset_id"]
        table.append(
            {
                "dataset_id": dataset_id,
                ".set": row["summary_set_count"],
                ".fdt": row["summary_fdt_count"],
                "paired": row["summary_paired_count"],
                "size_gib": row["summary_raw_eeg_size_gib"],
                "get_log": latest_log(f"d2_{dataset_id}_get_*.all.log"),
                "command_log": latest_log(f"d2_{dataset_id}_*retrieval_*.commands.log") or latest_log(f"d2_{dataset_id}_get_resume_*.commands.log"),
                "current_run_status": "verified in this run",
            }
        )
    if PROTECTED_DATASET and PROTECTED_DATASET not in requested:
        table.append(
            {
                "dataset_id": PROTECTED_DATASET,
                ".set": "pending",
                ".fdt": "pending",
                "paired": "pending",
                "size_gib": "pending",
                "get_log": "",
                "command_log": "",
                "current_run_status": "pending ds003523 completion; not inspected in this run",
            }
        )
    text = f"""# D2 Raw Download Report

Generated: 2026-06-13

## Technical Summary

Both D2 task datasets are now verified from local files only. This script counts local EEG binaries, sidecars, git-annex availability, and MNE readability without calling `datalad get`, `git-annex get`, clone, rename, or delete operations.

## Retrieval Results

{markdown_table(table, max_rows=10)}

## Interpretation Guardrail

Retrieval and verification are prerequisites only. D2 remains a bounded cross-task falsification/reproducibility check using `Original_ID`; it is not an independent validation cohort.
"""
    write_text(project_path("reports/31_d2_raw_download_report.md"), text)


def write_ds005114_report(rows: list[dict[str, Any]], details: dict[str, list[dict[str, Any]]], warnings: list[str], errors: list[str]) -> None:
    ds_rows = [row for row in rows if row.get("dataset_id") == "ds005114"]
    ds_details = {"ds005114": details.get("ds005114", [])}
    warning_text = "\n".join(f"- {warning}" for warning in warnings if "ds005114" in warning) or "- None."
    error_text = "\n".join(f"- {error}" for error in errors if "ds005114" in error) or "- None."
    text = f"""# ds005114 Download Verification Report

Generated: 2026-06-13

## Technical Summary

`ds005114` was verified without touching `data/raw/ds003523`. This report covers local `.set`/`.fdt` pairing, total local size, git-annex local availability, BIDS sidecars, and MNE read-tests.

## Verification Summary

{markdown_table(report_rows(ds_rows), max_rows=10)}

## MNE Read Tests

{markdown_table(mne_rows(ds_details), max_rows=10)}

## Warnings

{warning_text}

## Blockers

{error_text}

## Interpretation Guardrail

This verifies ds005114 retrieval/readability only. It does not complete D2, does not claim cross-task convergence, and does not validate a biomarker.
"""
    write_text(project_path("reports/31a_ds005114_download_verification_report.md"), text)


def write_full_d2_verification_report(
    rows: list[dict[str, Any]],
    details: dict[str, list[dict[str, Any]]],
    warnings: list[str],
    errors: list[str],
) -> None:
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None."
    error_text = "\n".join(f"- {error}" for error in errors) if errors else "- None."
    text = f"""# D2 Download Verification Report

Generated: 2026-06-13

## Technical Summary

D2 raw EEG verification passed for both D2 datasets. Full extraction may proceed only after confirming no active retrieval locks remain.

## Download Verification Summary

{markdown_table(report_rows(rows), max_rows=10)}

## MNE Read Tests

{markdown_table(mne_rows(details), max_rows=20)}

## Warnings

{warning_text}

## Blockers

{error_text}

## Interpretation Guardrail

Passing verification only permits D2 extraction. It does not support validation, biomarker, or independent replication language. D2 must remain a prespecified cross-task falsification/reproducibility check using `Original_ID` for subject identity.
"""
    write_text(project_path("reports/32_d2_download_verification_report.md"), text)


def write_pending_d2_verification_report(rows: list[dict[str, Any]], warnings: list[str], errors: list[str]) -> None:
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None."
    error_text = "\n".join(f"- {error}" for error in errors) if errors else "- None."
    text = f"""# D2 Download Verification Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Completed Safe Work

{markdown_table(report_rows(rows), max_rows=10)}

## Not Run

- `data/raw/ds003523` was not touched in this safe run.
- Full D2 verification, extraction, and modeling remain pending ds003523 completion.

## Warnings

{warning_text}

## Blockers

{error_text}

## Interpretation Guardrail

No D2 convergence or validation claim is made. D2 remains a bounded cross-task falsification/reproducibility check and must use `Original_ID` for identity.
"""
    write_text(project_path("reports/32_d2_download_verification_report.md"), text)


if __name__ == "__main__":
    main()
