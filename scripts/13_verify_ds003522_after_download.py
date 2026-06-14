from __future__ import annotations

import argparse
import csv
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, read_tsv, script_finish, script_start, write_rows_csv


SCRIPT = "13_verify_ds003522_after_download.py"
EXPECTED_SET_COUNT = 200
EXPECTED_FDT_COUNT = 200


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify ds003522 after manual DataLad retrieval without downloading.")
    parser.add_argument("--dataset", default="ds003522")
    parser.add_argument("--max-read-tests", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260612)
    parser.add_argument("--output", default="outputs/download_recovery/ds003522_post_download_verification.csv")
    args = parser.parse_args()

    if args.dataset != "ds003522":
        raise SystemExit("This verifier is intentionally restricted to ds003522.")

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    root = project_path("data/raw/ds003522")
    output = project_path(args.output)

    set_files = sorted(path for path in root.rglob("*.set") if is_bids_eeg_path(path, ".set"))
    fdt_files = sorted(path for path in root.rglob("*.fdt") if is_bids_eeg_path(path, ".fdt"))
    paired = []
    missing_fdt = []
    for set_path in set_files:
        fdt = paired_fdt(set_path)
        if fdt.exists() and is_bids_eeg_path(fdt, ".fdt"):
            paired.append((set_path, fdt))
        else:
            missing_fdt.append(set_path)

    annex = git_annex_find_in_here(root)
    if annex["error"]:
        warnings.append(annex["error"])

    rows = []
    read_tests = select_read_tests(root, set_files, args.max_read_tests, args.seed)
    for set_path in read_tests:
        rows.append(
            {
                **summary_columns(set_files, fdt_files, paired, missing_fdt, annex),
                **mne_read_test_row(root, set_path),
                "random_seed": args.seed,
            }
        )

    if not rows:
        rows.append(
            {
                **summary_columns(set_files, fdt_files, paired, missing_fdt, annex),
                "tested_set_path": "",
                "tested_set_relative_path": "",
                "tested_set_size": "",
                "tested_fdt_path": "",
                "tested_fdt_size": "",
                "mne_read_test_status": "not_run",
                "mne_sfreq": "",
                "mne_n_channels": "",
                "mne_n_times": "",
                "mne_error": "No BIDS-path .set files available for MNE read-test.",
                "random_seed": args.seed,
            }
        )
        errors.append("No BIDS-path .set files available for MNE read-test.")

    if len(set_files) != EXPECTED_SET_COUNT:
        warnings.append(f"Expected {EXPECTED_SET_COUNT} .set files, found {len(set_files)}.")
    if len(fdt_files) != EXPECTED_FDT_COUNT:
        warnings.append(f"Expected {EXPECTED_FDT_COUNT} .fdt files, found {len(fdt_files)}.")
    if missing_fdt:
        errors.append(f"Missing paired .fdt for {len(missing_fdt)} .set files.")

    write_rows_csv(output, rows)
    script_finish(
        SCRIPT,
        start,
        outputs=[str(output)],
        warnings=warnings,
        errors=errors,
        parameters=vars(args),
        status="completed" if not errors else "failed",
    )


def is_bids_eeg_path(path: Path, suffix: str) -> bool:
    text = path.as_posix()
    if "/.git/annex/objects/" in text:
        return False
    if path.suffix.lower() != suffix:
        return False
    return bool(re.search(r"/sub-[^/]+/ses-[^/]+/eeg/", text))


def paired_fdt(set_path: Path) -> Path:
    return set_path.with_name(set_path.name.replace("_eeg.set", "_eeg.fdt"))


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def git_annex_find_in_here(root: Path) -> dict[str, object]:
    result = {
        "set_count": "",
        "fdt_count": "",
        "exit_code": "",
        "error": "",
    }
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
            timeout=300,
        )
    except Exception as exc:
        result["error"] = f"git annex find --in=here failed: {exc}"
        return result
    paths = [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]
    result["set_count"] = sum(1 for line in paths if line.endswith(".set") and "/eeg/" in line)
    result["fdt_count"] = sum(1 for line in paths if line.endswith(".fdt") and "/eeg/" in line)
    result["exit_code"] = proc.returncode
    if proc.returncode != 0:
        result["error"] = (proc.stderr or "git annex find --in=here returned non-zero exit code.").strip()
    return result


def select_read_tests(root: Path, set_files: list[Path], max_read_tests: int, seed: int) -> list[Path]:
    if not set_files or max_read_tests <= 0:
        return []
    participants = {row.get("participant_id", ""): row.get("Group", "") for row in read_tsv(root / "participants.tsv")}
    by_group: dict[str, list[Path]] = {}
    for path in set_files:
        subject = "sub-" + relative(root, path).split("/", 1)[0].replace("sub-", "")
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


def summary_columns(
    set_files: list[Path],
    fdt_files: list[Path],
    paired: list[tuple[Path, Path]],
    missing_fdt: list[Path],
    annex: dict[str, object],
) -> dict[str, object]:
    total_bytes = sum(path.stat().st_size for path in set_files + fdt_files)
    return {
        "dataset_id": "ds003522",
        "summary_set_count": len(set_files),
        "summary_fdt_count": len(fdt_files),
        "summary_paired_count": len(paired),
        "summary_missing_fdt_count": len(missing_fdt),
        "summary_total_size_bytes": total_bytes,
        "summary_total_size_gib": round(total_bytes / (1024**3), 3),
        "git_annex_find_in_here_set_count": annex["set_count"],
        "git_annex_find_in_here_fdt_count": annex["fdt_count"],
        "git_annex_find_exit_code": annex["exit_code"],
        "verification_expected_set_count": EXPECTED_SET_COUNT,
        "verification_expected_fdt_count": EXPECTED_FDT_COUNT,
    }


def mne_read_test_row(root: Path, set_path: Path) -> dict[str, object]:
    fdt = paired_fdt(set_path)
    row = {
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
    }
    try:
        import mne

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
        row["mne_error"] = str(exc)
    return row


if __name__ == "__main__":
    main()
