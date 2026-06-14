from __future__ import annotations

import csv
import json
import math
import os
import py_compile
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import markdown_table, now_iso, project_path, read_rows_csv, write_json, write_rows_csv, write_text


SCRIPT = "24_stale_parallel_job_accuracy_audit.py"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = project_path("outputs/qc")
REPORT_PATH = project_path("reports/37_stale_parallel_job_accuracy_audit.md")
AUDIT_CSV = OUTPUT_DIR / "stale_parallel_job_accuracy_audit.csv"
TIMESTAMP_CSV = OUTPUT_DIR / "stale_parallel_job_file_timestamps.csv"
TEXT_SCAN_CSV = OUTPUT_DIR / "stale_parallel_job_text_scan.csv"
CONSISTENCY_CSV = OUTPUT_DIR / "final_result_consistency_checks.csv"
GATE_JSON = OUTPUT_DIR / "audit_gate.json"
PASS_OK = OUTPUT_DIR / "AUDIT_PASS.ok"
FAIL_OK = OUTPUT_DIR / "AUDIT_FAIL.ok"

FINAL_CURRENT_REPORTS = {
    "reports/11_d1_d2_d3_continuation_status.md",
    "reports/16_updated_final_recommendation.md",
    "reports/31_d2_raw_download_report.md",
    "reports/32_d2_download_verification_report.md",
    "reports/33_d2_subject_overlap_report.md",
    "reports/34_d2_harmonized_feature_extraction_report.md",
    "reports/35_d2_bounded_falsification_report.md",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
}

IMPORTANT_FILES = [
    "reports/35_d2_bounded_falsification_report.md",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
    "reports/16_updated_final_recommendation.md",
    "reports/11_d1_d2_d3_continuation_status.md",
    "reports/28_d1_d3_post_analysis_audit.md",
    "reports/29_next_step_decision_after_d1_d3.md",
    "outputs/d2_cross_task/d2_falsification_summary.csv",
    "outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
    "outputs/d2_cross_task/d2_direction_consistency.csv",
    "outputs/d2_cross_task/d2_within_subject_stability.csv",
    "outputs/d2_cross_task/d2_mixed_effects_models.csv",
    "outputs/download_recovery/ds005114_retrieval_verification.csv",
    "outputs/download_recovery/ds003523_retrieval_verification.csv",
    "outputs/download_recovery/d2_raw_download_summary.csv",
    "logs/run_log.jsonl",
]

SUPPORT_OUTPUTS = [
    "outputs/d2_cross_task/ds003490_qc.csv",
    "outputs/d2_cross_task/ds003490_event_inventory.csv",
    "outputs/d2_cross_task/ds003490_feature_readiness_summary.csv",
    "outputs/d2_cross_task/ds003490_rest_features.csv",
    "outputs/features/d1_rest_features.csv",
    "outputs/models/d1_d3_group_models.csv",
    "outputs/features/d3_ec_alpha_iaf_features.csv",
    "outputs/d2_cross_task/ds005114_harmonized_features.csv",
    "outputs/d2_cross_task/ds003523_harmonized_features.csv",
    "outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
    "outputs/d2_cross_task/d2_mixed_effects_models.csv",
    "reports/35_d2_bounded_falsification_report.md",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
]

STALE_PHRASES = [
    "ds003523 pending",
    "pending ds003523",
    "ds003523 remains in progress",
    "ds003523 download is still running",
    "ds003523 retrieval is currently active",
    "D2 remains unstarted",
    "D2 extraction not started",
    "D2 convergence pending",
    "ds005114 only",
    "validation",
    "validated biomarker",
    "diagnostic biomarker",
    "confirmed biomarker",
    "independent confirmation",
    "proof",
    "robust positive biomarker",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_rows: list[dict[str, Any]] = []
    critical_failures: list[str] = []
    warnings: list[str] = []

    processes = active_process_audit()
    suspicious_processes = [row for row in processes if row["actively_writing_project_outputs"]]
    add_check(
        audit_rows,
        "active_stale_writing_processes",
        "process",
        "no active project-writing stale processes",
        "PASS" if not suspicious_processes else "FAIL",
        "critical",
        f"{len(suspicious_processes)} suspicious process(es) detected.",
    )
    if suspicious_processes:
        critical_failures.append("Active process appears to be writing project outputs.")
        finish_gate("FAIL", critical_failures, warnings, audit_rows, [], [], [], processes, [], [])
        return

    final_completion = latest_completed_run("23_generate_d2_report.py")
    timestamp_rows = timestamp_audit(final_completion)
    text_rows = text_scan()
    consistency_rows = numeric_consistency_checks()
    raw_rows = raw_data_audit()
    support_rows = support_output_audit()
    compile_rows = compile_check()

    for row in timestamp_rows:
        if row.get("suspected_stale_overwrite") == "true":
            critical_failures.append(f"Suspicious timestamp/content issue: {row['file_path']} - {row['reason']}")
    for row in text_rows:
        if row.get("critical_failure") == "true":
            critical_failures.append(f"Critical stale/overclaim text: {row['file_path']}:{row['line_number']} {row['phrase']}")
    for row in consistency_rows:
        if row.get("pass") != "true" and row.get("severity") == "critical":
            critical_failures.append(f"Numeric consistency failed: {row['check_name']} observed {row['observed_value_or_claim']}")
    for row in raw_rows:
        if row.get("critical_failure") == "true":
            critical_failures.append(f"Raw data audit failed: {row['dataset_id']} {row['notes']}")
    for row in support_rows:
        if row.get("critical_failure") == "true":
            critical_failures.append(f"Supporting output missing/empty: {row['file_path']}")
    for row in compile_rows:
        if row.get("pass") != "true":
            critical_failures.append(f"Compile check failed: {row['file_path']} {row['notes']}")

    add_check(
        audit_rows,
        "timestamp_and_file_presence",
        "files",
        "all critical files exist, nonzero, and no content-confirmed stale overwrite",
        "PASS" if not any(row.get("suspected_stale_overwrite") == "true" for row in timestamp_rows) else "FAIL",
        "critical",
        "Timestamp findings are content-confirmed, not timestamp-only.",
    )
    add_check(
        audit_rows,
        "stale_text_scan",
        "reports",
        "no stale pending or overclaim text in final/current reports",
        "PASS" if not any(row.get("critical_failure") == "true" for row in text_rows) else "FAIL",
        "critical",
        f"{len(text_rows)} phrase hit(s) recorded with context.",
    )
    add_check(
        audit_rows,
        "numeric_consistency",
        "csv_outputs",
        "final claims trace to machine-readable outputs",
        "PASS" if not any(row.get("pass") != "true" and row.get("severity") == "critical" for row in consistency_rows) else "FAIL",
        "critical",
        "Rounded values tolerated.",
    )
    add_check(
        audit_rows,
        "raw_data_and_support_outputs",
        "files",
        "raw data and high-level outputs exist without recomputation",
        "PASS"
        if not any(row.get("critical_failure") == "true" for row in raw_rows + support_rows)
        else "FAIL",
        "critical",
        "Counts were collected from local files only.",
    )
    add_check(
        audit_rows,
        "python_compile",
        "scripts",
        "core scripts compile",
        "PASS" if not any(row.get("pass") != "true" for row in compile_rows) else "FAIL",
        "critical",
        f"{len(compile_rows)} script file(s) checked.",
    )

    gate = "FAIL" if critical_failures else "PASS"
    finish_gate(gate, critical_failures, warnings, audit_rows, timestamp_rows, text_rows, consistency_rows, processes, raw_rows, compile_rows)


def active_process_audit() -> list[dict[str, Any]]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Depth 4"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        payload = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception as exc:
        return [
            {
                "pid": "",
                "name": "",
                "command_line": "",
                "match_reason": "process audit failed",
                "actively_writing_project_outputs": True,
                "notes": f"{type(exc).__name__}: {exc}",
            }
        ]
    if isinstance(payload, dict):
        payload = [payload]

    rows: list[dict[str, Any]] = []
    patterns = [
        ("datalad", re.compile(r"\bdatalad(\.exe)?\b", re.I)),
        ("git-annex", re.compile(r"\bgit-annex(\.exe)?\b", re.I)),
        ("git", re.compile(r"\bgit(\.exe)?\b", re.I)),
        ("d2_or_report_script", re.compile(r"22_run_d2|21_extract_d2|23_generate_d2|20_verify_d2|14_d1_artifact|15_d3_eyes|16_d1_d3|19_d1_d3|24_stale_parallel", re.I)),
    ]
    current_pid = os.getpid()
    for proc in payload:
        pid = int(proc.get("ProcessId") or 0)
        cmd = str(proc.get("CommandLine") or "")
        name = str(proc.get("Name") or "")
        matches = [label for label, pattern in patterns if pattern.search(cmd) or pattern.search(name)]
        if not matches:
            continue
        is_self = pid == current_pid or SCRIPT in cmd
        is_readonly_audit_shell = "24_stale_parallel_job_accuracy_audit.py" in cmd or "Get-CimInstance Win32_Process" in cmd
        actively_writing = process_appears_to_write_project_outputs(name, cmd, matches) and not is_self and not is_readonly_audit_shell
        if not actively_writing and "git" in matches and not cmd:
            note = "ambiguous git process with unavailable command line; no project-writing action visible"
        elif not actively_writing:
            note = "ignored audit/read-only process"
        else:
            note = "potential stale writer"
        rows.append(
            {
                "pid": pid,
                "name": name,
                "command_line": cmd,
                "match_reason": ";".join(matches),
                "actively_writing_project_outputs": actively_writing,
                "notes": note,
            }
        )
    return rows


def process_appears_to_write_project_outputs(name: str, cmd: str, matches: list[str]) -> bool:
    lower_cmd = (cmd or "").lower()
    lower_name = (name or "").lower()
    project_fragment = "openneuro_tbi_eeg_d1_d2_d3_analysis".lower()
    if "datalad" in matches:
        return any(token in lower_cmd for token in [" get ", " clone ", " install ", " save ", " push ", " update "]) or project_fragment in lower_cmd
    if "git-annex" in matches:
        return any(token in lower_cmd for token in [" get ", " copy ", " move ", " drop ", " add ", " sync "]) or project_fragment in lower_cmd
    if "d2_or_report_script" in matches:
        return project_fragment in lower_cmd
    if "git" in matches or "git.exe" in lower_name:
        read_only_git = [
            " config ",
            " status",
            " rev-parse",
            " ls-files",
            " diff",
            " show",
            " log",
            " branch",
        ]
        write_like_git = [
            " checkout ",
            " reset ",
            " clean ",
            " add ",
            " mv ",
            " rm ",
            " commit ",
            " pull ",
            " fetch ",
            " merge ",
            " rebase ",
            " restore ",
            " annex ",
        ]
        if any(token in lower_cmd for token in write_like_git):
            return project_fragment in lower_cmd or "data/raw" in lower_cmd or "outputs" in lower_cmd or "reports" in lower_cmd
        if any(token in lower_cmd for token in read_only_git):
            return False
        return False
    return False


def timestamp_audit(final_completion: datetime | None) -> list[dict[str, Any]]:
    paths = [project_path(rel) for rel in IMPORTANT_FILES]
    paths.extend(sorted(project_path("logs").glob("d2_*")))
    rows = []
    for path in paths:
        rel = rel_path(path)
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        modified_dt = datetime.fromtimestamp(path.stat().st_mtime).astimezone() if exists else None
        modified = modified_dt.isoformat(timespec="seconds") if modified_dt else ""
        reason_parts: list[str] = []
        suspicious = False
        is_required_output = rel in set(IMPORTANT_FILES)
        is_log = rel.startswith("logs/")
        if not exists:
            suspicious = True
            reason_parts.append("missing required file")
        elif size == 0 and is_required_output and not is_log:
            suspicious = True
            reason_parts.append("zero-byte required file")
        elif size == 0 and is_log:
            reason_parts.append("zero-byte log file; inspected but not a critical output")
        if exists and rel in FINAL_CURRENT_REPORTS and current_report_has_stale_failure(path):
            suspicious = True
            reason_parts.append("current/final report contains stale or overclaim text")
        if exists and final_completion and modified_dt and modified_dt > final_completion and rel not in {"logs/run_log.jsonl"}:
            if rel.startswith("reports/3") or rel.startswith("outputs/d2_cross_task/"):
                if current_report_has_stale_failure(path):
                    suspicious = True
                    reason_parts.append("modified after final D2 completion and content is stale")
                else:
                    reason_parts.append("modified after final D2 completion but content check passed")
        if rel == "logs/run_log.jsonl":
            reason_parts.append("run log may update during this audit; not stale by itself")
        rows.append(
            {
                "file_path": str(path),
                "exists": str(exists).lower(),
                "size_bytes": size,
                "modified_time": modified,
                "suspected_stale_overwrite": str(suspicious).lower(),
                "reason": "; ".join(reason_parts) if reason_parts else "present; no stale content detected",
            }
        )
    write_rows_csv(TIMESTAMP_CSV, rows)
    return rows


def text_scan() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(project_path("reports").glob("*.md")):
        rel = rel_path(path)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as exc:
            rows.append(
                {
                    "file_path": str(path),
                    "phrase": "read_error",
                    "line_number": "",
                    "context": f"{type(exc).__name__}: {exc}",
                    "acceptable_historical_context": "false",
                    "critical_failure": "true",
                }
            )
            continue
        for idx, line in enumerate(lines, start=1):
            lower = line.lower()
            for phrase in STALE_PHRASES:
                if phrase.lower() not in lower:
                    continue
                current = rel in FINAL_CURRENT_REPORTS
                acceptable = (not current) or is_negated_or_guardrail(line, phrase)
                critical = current and not acceptable
                rows.append(
                    {
                        "file_path": str(path),
                        "phrase": phrase,
                        "line_number": idx,
                        "context": line.strip()[:500],
                        "acceptable_historical_context": str(acceptable).lower(),
                        "critical_failure": str(critical).lower(),
                    }
                )
    write_rows_csv(TEXT_SCAN_CSV, rows)
    return rows


def numeric_consistency_checks() -> list[dict[str, Any]]:
    within = read_rows_csv(project_path("outputs/d2_cross_task/d2_within_dataset_group_effects.csv"))
    summary = read_rows_csv(project_path("outputs/d2_cross_task/d2_falsification_summary.csv"))
    mixed = read_rows_csv(project_path("outputs/d2_cross_task/d2_mixed_effects_models.csv"))
    checks = {row.get("check_id"): row.get("value") for row in read_rows_csv(project_path("outputs/qc/d1_d3_audit_checks.csv"))}
    family = read_rows_csv(project_path("outputs/qc/d1_d3_model_family_audit.csv"))

    rows: list[dict[str, Any]] = []
    cue_rows = [row for row in within if row.get("dataset_id") == "ds005114" and row.get("task_window") == "cue_locked_baseline_2s"]
    dpx_task_rows = [row for row in within if row.get("dataset_id") == "ds005114" and row.get("task_window") == "task_average_4s"]
    vwm_task_rows = [row for row in within if row.get("dataset_id") == "ds003523" and row.get("task_window") == "task_average_4s"]
    dpx_summary = next((row for row in summary if row.get("summary_level") == "dataset_task_average" and row.get("dataset_id") == "ds005114"), {})
    vwm_summary = next((row for row in summary if row.get("summary_level") == "dataset_task_average" and row.get("dataset_id") == "ds003523"), {})
    overall_summary = next((row for row in summary if row.get("summary_level") == "overall_d2"), {})
    narrow = next((row for row in family if row.get("family_name") == "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal"), {})

    add_numeric(rows, "ds005114_cue_baseline_min_q", "outputs/d2_cross_task/d2_within_dataset_group_effects.csv", 0.0898, min_value(cue_rows, "fdr_q"), 0.002)
    add_numeric(rows, "ds005114_cue_baseline_max_abs_g", "outputs/d2_cross_task/d2_within_dataset_group_effects.csv", 0.5277, max_abs_value(cue_rows, "hedges_g"), 0.002)
    add_numeric(rows, "dpx_task_average_min_q", "outputs/d2_cross_task/d2_within_dataset_group_effects.csv", 0.1524, min_value(dpx_task_rows, "fdr_q"), 0.002)
    add_numeric(rows, "vwm_task_average_min_q", "outputs/d2_cross_task/d2_within_dataset_group_effects.csv", 0.4720, min_value(vwm_task_rows, "fdr_q"), 0.002)
    add_numeric(rows, "mixed_models_group_q_lt_0p10", "outputs/d2_cross_task/d2_mixed_effects_models.csv", 0, sum(1 for row in mixed if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10), 0)
    add_numeric(rows, "d1_acute_broad_min_q", "outputs/qc/d1_d3_audit_checks.csv", 0.7876, safe_float(checks.get("acute_trim_min_fdr")), 0.002)
    add_numeric(rows, "d1_narrow_prior_anchor_q", "outputs/qc/d1_d3_model_family_audit.csv", 0.132, safe_float(narrow.get("min_recomputed_bh_q")), 0.003)
    add_numeric(rows, "d3_acute_posterior_q", "outputs/qc/d1_d3_audit_checks.csv", 0.9149, safe_float(checks.get("d3_acute_mtbi_vs_control_posterior_min_fdr_q")), 0.002)
    add_numeric(rows, "chronic_trim_min_q", "outputs/qc/d1_d3_audit_checks.csv", 0.3484, safe_float(checks.get("chronic_trim_min_fdr")), 0.002)
    add_claim(rows, "d2_overall_interpretation", "outputs/d2_cross_task/d2_falsification_summary.csv", "partial/inconsistent cross-task support", overall_summary.get("interpretation", ""))
    add_claim(rows, "dpx_summary_interpretation", "outputs/d2_cross_task/d2_falsification_summary.csv", "directional but non-FDR-supportive", dpx_summary.get("interpretation", ""))
    add_claim(rows, "vwm_summary_interpretation", "outputs/d2_cross_task/d2_falsification_summary.csv", "directional but non-FDR-supportive", vwm_summary.get("interpretation", ""))

    write_rows_csv(CONSISTENCY_CSV, rows)
    return rows


def raw_data_audit() -> list[dict[str, Any]]:
    rows = []
    for dataset_id in ["ds003490", "ds003522", "ds005114", "ds003523"]:
        root = project_path("data/raw", dataset_id)
        set_files = sorted(path for path in root.rglob("*.set") if is_bids_eeg_file(path)) if root.exists() else []
        fdt_files = sorted(path for path in root.rglob("*.fdt") if is_bids_eeg_file(path)) if root.exists() else []
        fdt_stems = {path.with_suffix("").as_posix().lower() for path in fdt_files}
        paired = sum(1 for path in set_files if path.with_suffix("").as_posix().lower() in fdt_stems)
        missing = len(set_files) - paired
        total_size = sum(path.stat().st_size for path in set_files + fdt_files if path.exists())
        expected_raw = dataset_id in {"ds003490", "ds003522", "ds005114", "ds003523"}
        critical = expected_raw and (not root.exists() or not set_files or not fdt_files or missing > 0)
        rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_root": str(root),
                "exists": str(root.exists()).lower(),
                "set_count": len(set_files),
                "fdt_count": len(fdt_files),
                "paired_count": paired,
                "missing_pair_count": missing,
                "raw_eeg_size_bytes": total_size,
                "raw_eeg_size_gib": round(total_size / (1024**3), 3),
                "datalad_dataset_exists": str((root / ".git").exists() or (root / ".datalad").exists()).lower(),
                "critical_failure": str(critical).lower(),
                "notes": "local file count only; no datalad get called",
            }
        )
    return rows


def support_output_audit() -> list[dict[str, Any]]:
    rows = []
    for rel in SUPPORT_OUTPUTS:
        path = project_path(rel)
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        critical = not exists or size == 0
        rows.append(
            {
                "file_path": str(path),
                "exists": str(exists).lower(),
                "size_bytes": size,
                "critical_failure": str(critical).lower(),
                "notes": "expected high-level supporting output",
            }
        )
    return rows


def compile_check() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(project_path("scripts").glob("*.py")) + sorted(project_path("scripts/utils").glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
            passed = True
            notes = "compiled"
        except Exception as exc:
            passed = False
            notes = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "file_path": str(path),
                "pass": str(passed).lower(),
                "severity": "critical",
                "notes": notes,
            }
        )
    return rows


def is_bids_eeg_file(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if ".git" in parts or ".datalad" in parts:
        return False
    if "eeg" not in parts:
        return False
    return path.name.startswith("sub-")


def finish_gate(
    gate: str,
    critical_failures: list[str],
    warnings: list[str],
    audit_rows: list[dict[str, Any]],
    timestamp_rows: list[dict[str, Any]],
    text_rows: list[dict[str, Any]],
    consistency_rows: list[dict[str, Any]],
    process_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    compile_rows: list[dict[str, Any]],
) -> None:
    gate_payload = {
        "gate": gate,
        "timestamp": now_iso(),
        "critical_failures": critical_failures,
        "warnings": warnings,
        "final_files_checked": [str(project_path(rel)) for rel in IMPORTANT_FILES],
        "safe_to_continue": gate == "PASS",
        "next_prompt_allowed": gate == "PASS",
    }
    write_json(GATE_JSON, gate_payload)
    write_rows_csv(AUDIT_CSV, audit_rows)
    write_rows_csv(TIMESTAMP_CSV, timestamp_rows)
    write_rows_csv(TEXT_SCAN_CSV, text_rows)
    write_rows_csv(CONSISTENCY_CSV, consistency_rows)
    write_gate_marker(gate)
    write_report(gate_payload, audit_rows, timestamp_rows, text_rows, consistency_rows, process_rows, raw_rows, compile_rows)


def write_report(
    gate_payload: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    timestamp_rows: list[dict[str, Any]],
    text_rows: list[dict[str, Any]],
    consistency_rows: list[dict[str, Any]],
    process_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    compile_rows: list[dict[str, Any]],
) -> None:
    critical_text = "\n".join(f"- {item}" for item in gate_payload["critical_failures"]) or "- None."
    warning_text = "\n".join(f"- {item}" for item in gate_payload["warnings"]) or "- None."
    process_summary = process_rows if process_rows else [{"pid": "", "name": "", "match_reason": "none", "actively_writing_project_outputs": "false", "notes": "No matching stale writer process detected."}]
    text_failures = [row for row in text_rows if row.get("critical_failure") == "true"]
    timestamp_failures = [row for row in timestamp_rows if row.get("suspected_stale_overwrite") == "true"]
    consistency_failures = [row for row in consistency_rows if row.get("pass") != "true" and row.get("severity") == "critical"]
    compile_failures = [row for row in compile_rows if row.get("pass") != "true"]
    text = f"""# Stale Parallel Job Accuracy Audit

Generated: {gate_payload["timestamp"]}

## Gate

**{gate_payload["gate"]}**

Safe to continue: `{str(gate_payload["safe_to_continue"]).lower()}`

Next prompt allowed: `{str(gate_payload["next_prompt_allowed"]).lower()}`

## Critical Failures

{critical_text}

## Warnings

{warning_text}

## Process Audit

{markdown_table(process_summary, max_rows=20)}

## Audit Checks

{markdown_table(audit_rows, max_rows=20)}

## Timestamp/File Findings

{markdown_table(timestamp_failures or timestamp_rows[:12], max_rows=20)}

Full timestamp audit: `outputs/qc/stale_parallel_job_file_timestamps.csv`

## Text Scan Findings

{markdown_table(text_failures or text_rows[:20], max_rows=20)}

Full text scan: `outputs/qc/stale_parallel_job_text_scan.csv`

## Numeric Consistency Findings

{markdown_table(consistency_failures or consistency_rows, max_rows=20)}

Full consistency table: `outputs/qc/final_result_consistency_checks.csv`

## Raw Data Audit

{markdown_table(raw_rows, max_rows=10)}

## Compile Audit

{markdown_table(compile_failures or [{"status": "PASS", "scripts_checked": len(compile_rows)}], max_rows=20)}

## Files Written

- `reports/37_stale_parallel_job_accuracy_audit.md`
- `outputs/qc/stale_parallel_job_accuracy_audit.csv`
- `outputs/qc/stale_parallel_job_file_timestamps.csv`
- `outputs/qc/stale_parallel_job_text_scan.csv`
- `outputs/qc/final_result_consistency_checks.csv`
- `outputs/qc/audit_gate.json`
"""
    write_text(REPORT_PATH, text)


def write_gate_marker(gate: str) -> None:
    if gate == "PASS":
        if FAIL_OK.exists():
            FAIL_OK.unlink()
        PASS_OK.write_text(f"PASS {now_iso()}\n", encoding="utf-8")
    else:
        if PASS_OK.exists():
            PASS_OK.unlink()
        FAIL_OK.write_text(f"FAIL {now_iso()}\n", encoding="utf-8")


def latest_completed_run(script_name: str) -> datetime | None:
    path = project_path("logs/run_log.jsonl")
    latest: datetime | None = None
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("script") != script_name or row.get("status") != "completed":
            continue
        try:
            ts = datetime.fromisoformat(row["timestamp"])
        except Exception:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def current_report_has_stale_failure(path: Path) -> bool:
    if rel_path(path) not in FINAL_CURRENT_REPORTS:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return True
    for line in text.splitlines():
        lower = line.lower()
        for phrase in STALE_PHRASES:
            if phrase.lower() in lower and not is_negated_or_guardrail(line, phrase):
                return True
    return False


def is_negated_or_guardrail(line: str, phrase: str) -> bool:
    lower = line.lower()
    if phrase.lower() in {
        "pending ds003523",
        "ds003523 pending",
        "ds003523 remains in progress",
        "ds003523 download is still running",
        "ds003523 retrieval is currently active",
        "d2 remains unstarted",
        "d2 extraction not started",
        "d2 convergence pending",
        "ds005114 only",
    }:
        return False
    negators = [
        "not ",
        "no ",
        "without ",
        "does not ",
        "do not ",
        "cannot ",
        "must not ",
        "not supported",
        "guardrail",
        "forbidden",
        "avoid",
    ]
    return any(token in lower for token in negators)


def add_check(rows: list[dict[str, Any]], check_name: str, source: str, expected: str, observed: str, severity: str, notes: str) -> None:
    rows.append(
        {
            "check_name": check_name,
            "source": source,
            "expected": expected,
            "observed": observed,
            "severity": severity,
            "notes": notes,
        }
    )


def add_numeric(
    rows: list[dict[str, Any]],
    check_name: str,
    source_file: str,
    expected: float,
    observed: float | None,
    tolerance: float,
) -> None:
    passed = observed is not None and abs(float(observed) - float(expected)) <= tolerance
    rows.append(
        {
            "check_name": check_name,
            "source_file": source_file,
            "expected_value_or_claim": expected,
            "observed_value_or_claim": observed if observed is not None else "",
            "tolerance": tolerance,
            "pass": str(passed).lower(),
            "severity": "critical",
            "notes": "within tolerance" if passed else "outside tolerance or missing",
        }
    )


def add_claim(rows: list[dict[str, Any]], check_name: str, source_file: str, expected: str, observed: str) -> None:
    passed = str(expected).strip().lower() == str(observed).strip().lower()
    rows.append(
        {
            "check_name": check_name,
            "source_file": source_file,
            "expected_value_or_claim": expected,
            "observed_value_or_claim": observed,
            "tolerance": "exact string",
            "pass": str(passed).lower(),
            "severity": "critical",
            "notes": "matches" if passed else "claim mismatch",
        }
    )


def min_value(rows: list[dict[str, str]], field: str) -> float | None:
    values = [safe_float(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return min(values) if values else None


def max_abs_value(rows: list[dict[str, str]], field: str) -> float | None:
    values = [safe_float(row.get(field)) for row in rows]
    values = [abs(value) for value in values if value is not None]
    return max(values) if values else None


def safe_float(value: Any) -> float | None:
    try:
        if value in ("", None, "nan", "NaN"):
            return None
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


if __name__ == "__main__":
    main()
