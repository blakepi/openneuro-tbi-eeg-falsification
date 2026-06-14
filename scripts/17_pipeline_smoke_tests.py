from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, read_rows_csv, script_finish, script_start, write_rows_csv


SCRIPT = "17_pipeline_smoke_tests.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate ds003490 rehearsal outputs and later-use script gates.")
    parser.add_argument("--skip-refusal-exec", action="store_true", help="Only scan scripts; do not execute refusal checks.")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    rows.extend(required_directory_checks())
    rows.extend(required_output_checks())
    rows.extend(column_checks())
    rows.extend(duplicate_key_checks())
    rows.extend(value_range_checks())
    rows.extend(specparam_finite_checks())
    rows.extend(script_download_scan_checks())
    if not args.skip_refusal_exec:
        rows.extend(refusal_execution_checks())

    for row in rows:
        if row["status"] == "failed":
            errors.append(f"{row['check_id']}: {row['detail']}")
        elif row["status"] == "warning":
            warnings.append(f"{row['check_id']}: {row['detail']}")

    out_csv = project_path("outputs/qc/pipeline_smoke_tests.csv")
    write_rows_csv(out_csv, rows)
    report_path = project_path("reports/27_pipeline_smoke_test_report.md")
    report_path.write_text(build_report(rows), encoding="utf-8", newline="\n")
    script_finish(
        SCRIPT,
        start,
        outputs=[str(out_csv), str(report_path)],
        warnings=warnings,
        errors=errors,
        parameters=vars(args),
        status="completed" if not errors else "failed",
    )
    if errors:
        raise SystemExit("Pipeline smoke tests failed; see outputs/qc/pipeline_smoke_tests.csv")


def check_row(check_id: str, status: str, detail: str, artifact: str = "") -> dict[str, Any]:
    return {"check_id": check_id, "status": status, "detail": detail, "artifact": artifact}


def required_directory_checks() -> list[dict[str, Any]]:
    rows = []
    for rel in ["outputs/d2_cross_task", "outputs/qc", "reports", "scripts", "logs"]:
        path = project_path(rel)
        rows.append(check_row(f"dir_exists_{rel.replace('/', '_')}", "passed" if path.is_dir() else "failed", str(path), rel))
    return rows


def required_output_checks() -> list[dict[str, Any]]:
    rows = []
    for rel in [
        "outputs/d2_cross_task/ds003490_rest_features.csv",
        "outputs/d2_cross_task/ds003490_aperiodic_features.csv",
        "outputs/d2_cross_task/ds003490_alpha_iaf_features.csv",
        "outputs/d2_cross_task/ds003490_erp_readiness.csv",
        "outputs/d2_cross_task/ds003490_feature_dictionary.csv",
        "outputs/d2_cross_task/ds003490_specparam_sensitivity.csv",
        "reports/24_ds003490_pipeline_rehearsal_report.md",
        "reports/25_ds003490_specparam_rehearsal_report.md",
        "reports/26_ds003522_post_download_handoff_plan.md",
    ]:
        path = project_path(rel)
        status = "passed" if path.exists() and path.stat().st_size > 0 else "failed"
        detail = f"{path} size={path.stat().st_size if path.exists() else 'missing'}"
        rows.append(check_row(f"output_exists_{Path(rel).stem}", status, detail, rel))
    return rows


def column_checks() -> list[dict[str, Any]]:
    expected = {
        "outputs/d2_cross_task/ds003490_rest_features.csv": ["dataset_id", "relative_path", "bids_subject", "session", "condition", "region", "feature_name", "feature_value"],
        "outputs/d2_cross_task/ds003490_aperiodic_features.csv": ["dataset_id", "relative_path", "condition", "region", "fit_status", "aperiodic_exponent", "aperiodic_offset"],
        "outputs/d2_cross_task/ds003490_alpha_iaf_features.csv": ["dataset_id", "relative_path", "condition", "region", "iaf_peak_frequency_hz", "absolute_alpha_power", "relative_alpha_power"],
        "outputs/d2_cross_task/ds003490_erp_readiness.csv": ["dataset_id", "relative_path", "condition", "event_count", "epoch_feasible", "p3_extraction_feasible"],
        "outputs/d2_cross_task/ds003490_specparam_sensitivity.csv": ["dataset_id", "relative_path", "condition", "region", "sensitivity_config", "fit_status", "aperiodic_exponent", "aperiodic_offset", "unstable_fit_flag"],
    }
    rows = []
    for rel, columns in expected.items():
        path = project_path(rel)
        observed = csv_header(path)
        missing = [col for col in columns if col not in observed]
        status = "passed" if not missing else "failed"
        rows.append(check_row(f"columns_{Path(rel).stem}", status, f"missing={missing}", rel))
    return rows


def csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        return next(reader, [])


def duplicate_key_checks() -> list[dict[str, Any]]:
    checks = [
        (
            "outputs/d2_cross_task/ds003490_rest_features.csv",
            ["relative_path", "condition", "region", "feature_name"],
        ),
        (
            "outputs/d2_cross_task/ds003490_aperiodic_features.csv",
            ["relative_path", "condition", "region", "frequency_range_hz", "aperiodic_mode"],
        ),
        (
            "outputs/d2_cross_task/ds003490_alpha_iaf_features.csv",
            ["relative_path", "condition", "region"],
        ),
        (
            "outputs/d2_cross_task/ds003490_specparam_sensitivity.csv",
            ["relative_path", "condition", "region", "sensitivity_config"],
        ),
    ]
    rows = []
    for rel, keys in checks:
        records = read_rows_csv(project_path(rel))
        seen = set()
        dupes = 0
        for record in records:
            key = tuple(record.get(k, "") for k in keys)
            if key in seen:
                dupes += 1
            seen.add(key)
        rows.append(check_row(f"duplicates_{Path(rel).stem}", "passed" if dupes == 0 else "failed", f"duplicate_keys={dupes}", rel))
    return rows


def value_range_checks() -> list[dict[str, Any]]:
    rows = []
    rest = read_rows_csv(project_path("outputs/d2_cross_task/ds003490_rest_features.csv"))
    alpha = read_rows_csv(project_path("outputs/d2_cross_task/ds003490_alpha_iaf_features.csv"))
    bad_relative = [
        row
        for row in rest
        if row.get("feature_name", "").startswith("relative_")
        and (not is_between(row.get("feature_value"), 0.0, 1.05))
    ]
    bad_entropy = [
        row
        for row in rest
        if row.get("feature_name") == "spectral_entropy_1_40"
        and (not is_between(row.get("feature_value"), 0.0, 1.0))
    ]
    bad_ratios = [
        row
        for row in rest
        if row.get("feature_name") in {"theta_alpha_ratio", "alpha_theta_ratio"}
        and (not is_nonnegative_finite(row.get("feature_value")))
    ]
    bad_iaf = [row for row in alpha if not is_between(row.get("iaf_peak_frequency_hz"), 7.0, 13.0)]
    rows.append(check_row("range_relative_power", "passed" if not bad_relative else "failed", f"bad_rows={len(bad_relative)}", "ds003490_rest_features.csv"))
    rows.append(check_row("range_spectral_entropy", "passed" if not bad_entropy else "failed", f"bad_rows={len(bad_entropy)}", "ds003490_rest_features.csv"))
    rows.append(check_row("range_ratios_nonnegative", "passed" if not bad_ratios else "failed", f"bad_rows={len(bad_ratios)}", "ds003490_rest_features.csv"))
    rows.append(check_row("range_iaf_7_13", "passed" if not bad_iaf else "failed", f"bad_rows={len(bad_iaf)}", "ds003490_alpha_iaf_features.csv"))
    return rows


def specparam_finite_checks() -> list[dict[str, Any]]:
    rows = []
    for rel in ["outputs/d2_cross_task/ds003490_aperiodic_features.csv", "outputs/d2_cross_task/ds003490_specparam_sensitivity.csv"]:
        records = read_rows_csv(project_path(rel))
        succeeded = [row for row in records if row.get("fit_status") == "passed"]
        bad = [
            row
            for row in succeeded
            if not (is_finite(row.get("aperiodic_exponent")) and is_finite(row.get("aperiodic_offset")))
        ]
        rows.append(check_row(f"finite_aperiodic_{Path(rel).stem}", "passed" if not bad else "failed", f"passed_fits={len(succeeded)} bad_rows={len(bad)}", rel))
    return rows


def script_download_scan_checks() -> list[dict[str, Any]]:
    rows = []
    forbidden = re.compile(r"\b(datalad\s+get|git\s+annex\s+get|git-annex\s+get|datalad\s+clone|git\s+clone|clone\s+https|Rename-Item|Remove-Item|shutil\.rmtree|os\.remove|rmdir)\b", re.IGNORECASE)
    for rel in [
        "scripts/13_verify_ds003522_after_download.py",
        "scripts/14_d1_artifact_control_analysis.py",
        "scripts/15_d3_eyes_closed_alpha_iaf_analysis.py",
        "scripts/16_d1_d3_integrated_report.py",
    ]:
        path = project_path(rel)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        matches = [match.group(0) for match in forbidden.finditer(text)]
        rows.append(check_row(f"no_download_or_reclone_{Path(rel).stem}", "passed" if not matches else "failed", f"matches={matches}", rel))
    return rows


def refusal_execution_checks() -> list[dict[str, Any]]:
    rows = []
    fake_verification = "outputs/qc/nonexistent_ds003522_verification_for_smoke.csv"
    for rel in [
        "scripts/14_d1_artifact_control_analysis.py",
        "scripts/15_d3_eyes_closed_alpha_iaf_analysis.py",
        "scripts/16_d1_d3_integrated_report.py",
    ]:
        command = [sys.executable, str(project_path(rel)), "--verification-csv", fake_verification]
        proc = subprocess.run(command, cwd=project_path(), capture_output=True, text=True, check=False, timeout=120)
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        refused = proc.returncode != 0 and "Refusing to run" in combined
        rows.append(
            check_row(
                f"refusal_without_verification_{Path(rel).stem}",
                "passed" if refused else "failed",
                f"return_code={proc.returncode}; refused={refused}; tail={combined[-500:].replace(chr(10), ' ')}",
                rel,
            )
        )
    return rows


def is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def is_between(value: Any, low: float, high: float) -> bool:
    try:
        number = float(value)
        return math.isfinite(number) and low <= number <= high
    except Exception:
        return False


def is_nonnegative_finite(value: Any) -> bool:
    try:
        number = float(value)
        return math.isfinite(number) and number >= 0
    except Exception:
        return False


def build_report(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    failed = [row for row in rows if row["status"] == "failed"]
    warnings = [row for row in rows if row["status"] == "warning"]
    failed_text = "\n".join(f"- `{row['check_id']}`: {row['detail']}" for row in failed) if failed else "- None"
    warning_text = "\n".join(f"- `{row['check_id']}`: {row['detail']}" for row in warnings) if warnings else "- None"
    return f"""# Pipeline Smoke Test Report

Generated: 2026-06-12

## Scope

This smoke test validates ds003490 pipeline-rehearsal outputs and checks that later-use ds003522 scripts remain gated. It does not inspect `data/raw/ds003522`, does not download data, and does not make D1/D2/D3 scientific claims.

## Summary

| Status | Checks |
| --- | ---: |
| passed | {counts.get('passed', 0)} |
| warning | {counts.get('warning', 0)} |
| failed | {counts.get('failed', 0)} |

## Failures

{failed_text}

## Warnings

{warning_text}

## Decision

Smoke tests pass only if required ds003490 outputs exist, expected columns are present, duplicate feature keys are absent, simple value ranges are plausible, specparam outputs are finite for passed fits, D1/D3 scripts refuse to run without ds003522 verification, and later-use scripts contain no download/reclone command patterns.
"""


if __name__ == "__main__":
    main()
