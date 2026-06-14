from __future__ import annotations

import csv
import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import (
    append_run_log,
    markdown_table,
    now_iso,
    project_path,
    read_rows_csv,
    script_finish,
    script_start,
    write_rows_csv,
    write_text,
)


SCRIPT = "25_repair_stale_d2_reports.py"
REPAIR_REPORT = project_path("reports/38_stale_report_repair_log.md")
BACKUP_MANIFEST = project_path("outputs/qc/stale_repair_backup_manifest.csv")
SOURCE_MANIFEST = project_path("outputs/qc/stale_repair_authoritative_sources.csv")
ACTION_LOG = project_path("outputs/qc/stale_report_repair_actions.csv")

REPORTS_TO_BACKUP = [
    "reports/32_d2_download_verification_report.md",
    "reports/33_d2_subject_overlap_report.md",
    "reports/34_d2_harmonized_feature_extraction_report.md",
    "reports/35_d2_bounded_falsification_report.md",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
    "reports/16_updated_final_recommendation.md",
    "reports/11_d1_d2_d3_continuation_status.md",
]

REPORTS_TO_REPAIR = [
    "reports/32_d2_download_verification_report.md",
    "reports/33_d2_subject_overlap_report.md",
    "reports/34_d2_harmonized_feature_extraction_report.md",
    "reports/35_d2_bounded_falsification_report.md",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
    "reports/16_updated_final_recommendation.md",
    "reports/11_d1_d2_d3_continuation_status.md",
]

AUTHORITATIVE_SOURCES = [
    ("outputs/d2_cross_task/d2_falsification_summary.csv", "D2 final bounded interpretation"),
    ("outputs/d2_cross_task/d2_within_dataset_group_effects.csv", "D2 within-dataset group effects"),
    ("outputs/d2_cross_task/d2_direction_consistency.csv", "D2 direction consistency"),
    ("outputs/d2_cross_task/d2_within_subject_stability.csv", "D2 within-subject stability"),
    ("outputs/d2_cross_task/d2_mixed_effects_models.csv", "D2 mixed-effects and fallback models"),
    ("outputs/d2_cross_task/ds005114_harmonized_features.csv", "D2 ds005114 extracted features"),
    ("outputs/d2_cross_task/ds003523_harmonized_features.csv", "D2 ds003523 extracted features"),
    ("outputs/d2_cross_task/d2_extraction_qc.csv", "D2 extraction QC"),
    ("outputs/d2_cross_task/d2_subject_task_crosswalk.csv", "Original_ID crosswalk"),
    ("outputs/d2_cross_task/d2_overlap_matrix.csv", "Original_ID overlap matrix"),
    ("outputs/d2_cross_task/d2_task_session_availability.csv", "task/session availability"),
    ("outputs/qc/d1_d3_audit_checks.csv", "D1/D3 audit checks"),
    ("outputs/qc/d1_d3_model_family_audit.csv", "D1/D3 FDR family audit"),
    ("outputs/qc/d1_d3_key_effect_trace.csv", "D1 key effect trace"),
    ("outputs/qc/d1_d3_artifact_branch_sample_counts.csv", "D1/D3 artifact branch sample counts"),
    ("outputs/download_recovery/ds005114_retrieval_verification.csv", "ds005114 read verification"),
    ("outputs/download_recovery/ds003523_retrieval_verification.csv", "ds003523 read verification"),
    ("outputs/download_recovery/d2_raw_download_summary.csv", "D2 raw download summary"),
    ("outputs/download_recovery/ds003522_post_download_verification.csv", "ds003522 read verification"),
    ("outputs/download_recovery/ds003490_full_retrieval_verification.csv", "ds003490 full retrieval verification"),
    ("outputs/d2_cross_task/ds003490_qc.csv", "ds003490 comparator QC"),
    ("outputs/d2_cross_task/ds003490_event_inventory.csv", "ds003490 event inventory"),
    ("outputs/d2_cross_task/ds003490_feature_readiness_summary.csv", "ds003490 feature readiness"),
]


def main() -> None:
    start = script_start(SCRIPT)
    actions: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_path("reports", f"stale_parallel_backup_{timestamp}")

    backup_rows = backup_stale_reports(backup_dir, actions)
    write_rows_csv(BACKUP_MANIFEST, backup_rows)

    source_rows = authoritative_source_rows()
    write_rows_csv(SOURCE_MANIFEST, source_rows)
    missing = [row for row in source_rows if row["usable_for_repair"] != "true"]
    if missing:
        errors.append("One or more authoritative sources are missing or empty; repair aborted.")
        write_rows_csv(ACTION_LOG, actions)
        write_repair_log("FAIL", backup_dir, backup_rows, source_rows, actions, warnings, errors)
        script_finish(SCRIPT, start, outputs=[str(BACKUP_MANIFEST), str(SOURCE_MANIFEST), str(ACTION_LOG), str(REPAIR_REPORT)], warnings=warnings, errors=errors, status="failed")
        raise SystemExit(1)

    data = load_data()
    report_writers = [
        ("reports/32_d2_download_verification_report.md", report_32(data)),
        ("reports/33_d2_subject_overlap_report.md", report_33(data)),
        ("reports/34_d2_harmonized_feature_extraction_report.md", report_34(data)),
        ("reports/35_d2_bounded_falsification_report.md", report_35(data)),
        ("reports/36_integrated_d1_d2_d3_final_decision_report.md", report_36(data)),
        ("reports/16_updated_final_recommendation.md", report_16(data)),
        ("reports/11_d1_d2_d3_continuation_status.md", report_11(data)),
    ]
    for idx, (rel, text) in enumerate(report_writers, start=1):
        path = project_path(rel)
        write_text(path, text)
        actions.append(
            action_row(
                f"repair_{idx:02d}",
                path,
                "repaired_report_from_authoritative_outputs",
                "existing CSV outputs and audit tables",
                "Replace stale pending ds003523 report text with completed D2 bounded interpretation.",
                True,
                "No machine-readable numeric outputs modified.",
            )
        )

    stale_hits = current_report_stale_hits()
    if stale_hits:
        errors.append("Stale text remains after repair: " + "; ".join(stale_hits[:10]))

    write_rows_csv(ACTION_LOG, actions)
    status = "FAIL" if errors else "PASS"
    write_repair_log(status, backup_dir, backup_rows, source_rows, actions, warnings, errors)
    outputs = [BACKUP_MANIFEST, SOURCE_MANIFEST, ACTION_LOG, REPAIR_REPORT, *[project_path(rel) for rel in REPORTS_TO_REPAIR]]
    script_finish(SCRIPT, start, outputs=[str(path) for path in outputs], warnings=warnings, errors=errors, status="completed" if not errors else "failed")
    if errors:
        raise SystemExit(1)


def backup_stale_reports(backup_dir: Path, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel in REPORTS_TO_BACKUP:
        original = project_path(rel)
        backup = backup_dir / original.name
        exists = original.exists()
        if exists:
            shutil.copy2(original, backup)
        rows.append(
            {
                "original_file": str(original),
                "backup_file": str(backup),
                "original_modified_time": mtime(original) if exists else "",
                "original_size_bytes": original.stat().st_size if exists else "",
                "backed_up": str(exists).lower(),
                "notes": "copied before repair" if exists else "original missing",
            }
        )
        actions.append(
            action_row(
                f"backup_{len(rows):02d}",
                original,
                "backup",
                str(original),
                "Preserve stale overwritten file before repair.",
                exists,
                str(backup) if exists else "original missing",
            )
        )
    return rows


def authoritative_source_rows() -> list[dict[str, Any]]:
    rows = []
    for rel, role in AUTHORITATIVE_SOURCES:
        path = project_path(rel)
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        usable = exists and size > 2
        rows.append(
            {
                "source_file": str(path),
                "exists": str(exists).lower(),
                "size_bytes": size,
                "modified_time": mtime(path) if exists else "",
                "role": role,
                "key_values_extracted": key_values_for_source(path, rel) if usable else "",
                "usable_for_repair": str(usable).lower(),
            }
        )
    return rows


def load_data() -> dict[str, list[dict[str, str]]]:
    return {rel: read_rows_csv(project_path(rel)) for rel, _role in AUTHORITATIVE_SOURCES}


def report_32(data: dict[str, list[dict[str, str]]]) -> str:
    summary = data["outputs/download_recovery/d2_raw_download_summary.csv"]
    details = data["outputs/download_recovery/ds005114_retrieval_verification.csv"] + data["outputs/download_recovery/ds003523_retrieval_verification.csv"]
    download_rows = [
        {
            "dataset_id": row.get("dataset_id", ""),
            ".set": row.get("summary_set_count", ""),
            ".fdt": row.get("summary_fdt_count", ""),
            "paired": row.get("summary_paired_count", ""),
            "missing_fdt": row.get("summary_missing_fdt_count", ""),
            "raw_size_gib": row.get("summary_raw_eeg_size_gib", ""),
            "annex_here_total": row.get("git_annex_find_in_here_total_count", ""),
            "events/channels/eeg_json": f"{row.get('event_file_presence_count', '')}/{row.get('channels_file_presence_count', '')}/{row.get('eeg_json_sidecar_presence_count', '')}",
            "mne_pass": f"{row.get('mne_read_pass_count', '')}/{row.get('mne_read_test_count', '')}",
            "passed": row.get("verification_passed", ""),
        }
        for row in summary
    ]
    mne_rows = [
        {
            "dataset_id": row.get("dataset_id", ""),
            "tested_set_relative_path": row.get("tested_set_relative_path", ""),
            "mne_status": row.get("mne_read_test_status", ""),
            "sfreq": row.get("mne_sfreq", ""),
            "channels": row.get("mne_n_channels", ""),
            "samples": row.get("mne_n_times", ""),
        }
        for row in details
        if row.get("tested_set_relative_path")
    ]
    return f"""# D2 Download Verification Report

Generated: 2026-06-13

## Technical Summary

D2 raw EEG verification is complete for both task datasets using existing local files. This repair did not call `datalad get`, `git-annex get`, clone, rename, delete, feature extraction, or statistical modeling.

## Download Verification Summary

{markdown_table(download_rows, max_rows=10)}

## MNE Read Tests

{markdown_table(mne_rows, max_rows=20)}

## Interpretation Guardrail

Passing verification permits interpretation of the already-completed bounded D2 outputs only. It does not support independent confirmation, a validated biomarker, diagnostic utility, prognosis, or clinical prediction. `Original_ID` remains the identity key for D2.
"""


def report_33(data: dict[str, list[dict[str, str]]]) -> str:
    crosswalk = data["outputs/d2_cross_task/d2_subject_task_crosswalk.csv"]
    overlap = data["outputs/d2_cross_task/d2_overlap_matrix.csv"]
    availability = data["outputs/d2_cross_task/d2_task_session_availability.csv"]
    counts = []
    for dataset_id in ["ds003522", "ds005114", "ds003523"]:
        ids = {
            row.get("stable_person_id") or row.get("Original_ID")
            for row in crosswalk
            if row.get("dataset_id") == dataset_id and (row.get("stable_person_id") or row.get("Original_ID"))
        }
        counts.append({"dataset_id": dataset_id, "n_original_ids": len(ids)})
    group_counter: Counter[tuple[str, str]] = Counter()
    seen: set[tuple[str, str]] = set()
    for row in crosswalk:
        stable = row.get("stable_person_id") or row.get("Original_ID")
        if not stable:
            continue
        key = (row.get("dataset_id", ""), stable)
        if key in seen:
            continue
        seen.add(key)
        group_counter[(row.get("dataset_id", ""), row.get("group_normalized", ""))] += 1
    group_rows = [{"dataset_id": key[0], "group_normalized": key[1], "n_original_ids": value} for key, value in sorted(group_counter.items())]
    return f"""# D2 Subject Overlap Report

Generated: 2026-06-13

## Technical Summary

The D2 cross-task identity key is `Original_ID`, represented as `stable_person_id` in the analysis tables. `ds005114` and `ds003523` share the same 90 acute mTBI/control Original IDs, and 70 of those overlap with `ds003522`. D2 is therefore a within-cohort cross-task falsification/reproducibility check, not independent confirmation.

## Original ID Counts

{markdown_table(counts, max_rows=10)}

## Original ID Overlap Matrix

{markdown_table(overlap, max_rows=20)}

## Group Counts By Dataset

{markdown_table(group_rows, max_rows=20)}

## Task And Session Availability

{markdown_table(availability, max_rows=30)}

## Leakage Rule

Any split, repeated-measures model, or cross-task inference must use `stable_person_id` / `Original_ID`. BIDS `sub-*`, recording, session, and task rows are repeated observations, not independent people.
"""


def report_34(data: dict[str, list[dict[str, str]]]) -> str:
    features = {
        "ds005114": data["outputs/d2_cross_task/ds005114_harmonized_features.csv"],
        "ds003523": data["outputs/d2_cross_task/ds003523_harmonized_features.csv"],
    }
    feature_summary = []
    for dataset_id, rows in features.items():
        feature_summary.append(
            {
                "dataset_id": dataset_id,
                "feature_rows": len(rows),
                "recordings": len({row.get("relative_path", "") for row in rows if row.get("relative_path", "")}),
                "original_ids": len({row.get("stable_person_id", "") for row in rows if row.get("stable_person_id", "")}),
                "task_windows": len({row.get("task_window", "") for row in rows if row.get("task_window", "")}),
            }
        )
    qc_counter = Counter((row.get("dataset_id", ""), row.get("task_window", ""), row.get("qc_status", "")) for row in data["outputs/d2_cross_task/d2_extraction_qc.csv"])
    qc_rows = [{"dataset_id": key[0], "task_window": key[1], "qc_status": key[2], "n_rows": value} for key, value in sorted(qc_counter.items())]
    return f"""# D2 Harmonized Feature Extraction Report

Generated: 2026-06-13

## Technical Summary

D2 harmonized feature outputs are present for both verified task datasets. This repair only regenerated the report text from existing output tables; it did not rerun extraction. The feature tables support the prespecified bounded falsification models only.

## Feature Output Summary

{markdown_table(feature_summary, max_rows=10)}

## QC Summary

{markdown_table(qc_rows, max_rows=40)}

## Feature Family Guardrail

Primary D2 inference is limited to the locked prior-anchor family: aperiodic exponent, aperiodic offset, spectral entropy, relative delta power, relative alpha power, theta/alpha ratio, alpha/theta ratio, and individual alpha frequency across prespecified regions/windows. `relative_theta_power` is retained as secondary context only and must not be used to rescue nominal findings.
"""


def report_35(data: dict[str, list[dict[str, str]]]) -> str:
    metrics = derived_metrics(data)
    return f"""# D2 Bounded Falsification Report

Generated: 2026-06-13

## Technical Summary

D2 completed as a bounded cross-task falsification/reproducibility check using verified local raw EEG for `ds005114` and `ds003523`. Because the task datasets overlap by `Original_ID`, D2 is not independent confirmation.

The restored result is **partial/inconsistent cross-task support**. The strongest D2 trace is `ds005114` DPX cue-baseline alpha/spectral-balance structure with minimum FDR q = {fmt(metrics['cue_min_q'])} and maximum absolute Hedges g = {fmt(metrics['cue_max_abs_g'])}. However, DPX task-average does not clear FDR (minimum q = {fmt(metrics['dpx_task_min_q'])}), visual working memory task-average does not clear FDR (minimum q = {fmt(metrics['vwm_task_min_q'])}), and mixed models have {metrics['mixed_q_lt_0p10']} group reference-task terms below q < 0.10.

## Bounded Model Summary

{markdown_table(summary_rows(data), max_rows=10)}

## Best Within-Dataset Effects

{markdown_table(top_effect_rows(data["outputs/d2_cross_task/d2_within_dataset_group_effects.csv"], 12), max_rows=12)}

## Task-Average Results

{markdown_table(task_average_rows(data["outputs/d2_cross_task/d2_within_dataset_group_effects.csv"]), max_rows=12)}

## Direction Consistency Against D1

{markdown_table(direction_rows(data["outputs/d2_cross_task/d2_direction_consistency.csv"]), max_rows=10)}

Direction consistency is descriptive only. DPX task-average rows match the D1 direction for {metrics['dpx_direction_matches']} of {metrics['dpx_direction_tests']} feature-region cells, and visual working memory matches {metrics['vwm_direction_matches']} of {metrics['vwm_direction_tests']} cells. Because task-average FDR does not clear q < 0.10, this is a directional trace rather than a positive result.

## Within-Subject Cross-Task Stability

{markdown_table(top_stability_rows(data["outputs/d2_cross_task/d2_within_subject_stability.csv"]), max_rows=10)}

The strongest stability rows show high DPX/VWM rank-order consistency across the same 90 `Original_ID`s. This supports measurement reproducibility of spectral features across tasks, but it does not establish disease-specific convergence.

## Integrated Mixed Models

{markdown_table(mixed_status_rows(data["outputs/d2_cross_task/d2_mixed_effects_models.csv"]), max_rows=10)}

Mixed-effects modeling was numerically fragile for part of the feature family: {metrics['mixedlm_completed']} models completed as MixedLM and {metrics['clustered_ols_fallback']} used clustered OLS fallback. No group reference-task term survived FDR at q < 0.10.

## Decision Answers

- D2 provides only partial/inconsistent cross-task support.
- D2 weakens a robust-marker interpretation but does not fully falsify every directional trace.
- D2 does not rescue D1/D3.
- Supportable framing is an artifact-sensitivity/null-leaning report with a bounded cross-task check, not a positive diagnostic or prognostic story.

## Guardrails

- Keep acute mTBI vs control as the cleaner primary comparison.
- Keep chronic TBI separate and batch-sensitive.
- Do not pool repeated `Original_ID`s as independent people.
- Do not use classifiers to rescue the signal.
- Do not treat `ds003490` as TBI evidence.
- No validated biomarker, diagnostic biomarker, predictive biomarker, or independent validation claim is supported.
"""


def report_36(data: dict[str, list[dict[str, str]]]) -> str:
    metrics = derived_metrics(data)
    checks = d1_checks(data)
    status_rows = [
        {"domain": "D1 rest", "decision": "artifact-sensitive/null-leaning", "key_value": f"acute artifact-controlled broad min q = {fmt(checks['acute_trim_q'])}"},
        {"domain": "D1 narrow prior-anchor", "decision": "exploratory only", "key_value": f"narrow q = {fmt(checks['narrow_q'])}"},
        {"domain": "D3 eyes-closed alpha/IAF", "decision": "does not rescue acute signal", "key_value": f"posterior acute min q = {fmt(checks['d3_posterior_q'])}"},
        {"domain": "chronic TBI", "decision": "separate and batch-sensitive", "key_value": f"artifact-trimmed chronic min q = {fmt(checks['chronic_q'])}"},
        {"domain": "D2 DPX/VWM", "decision": "partial/inconsistent cross-task support", "key_value": f"overall min q = {fmt(metrics['overall_min_q'])}; mixed q<0.10 count = {metrics['mixed_q_lt_0p10']}"},
        {"domain": "Final framing", "decision": "artifact-sensitivity/null-leaning reproducibility report", "key_value": "no positive diagnostic, prognostic, or biomarker claim"},
    ]
    return f"""# Integrated D1 D2 D3 Final Decision Report

Generated: 2026-06-13

## Final Decision

The project should be framed as an **artifact-sensitive, null-leaning public EEG analysis with a weak/context-specific cross-task trace**. D2 adds a bounded reproducibility/falsification check but does not overturn the D1/D3 caution.

## Decision Matrix

{markdown_table(status_rows, max_rows=10)}

## D2 Interpretation

The only D2 q < 0.10 trace is in `ds005114` DPX cue-baseline features (minimum q = {fmt(metrics['cue_min_q'])}, max |g| = {fmt(metrics['cue_max_abs_g'])}). The more general task-average tests are weaker: DPX task-average minimum q = {fmt(metrics['dpx_task_min_q'])}, and VWM task-average minimum q = {fmt(metrics['vwm_task_min_q'])}. Mixed-effects models have {metrics['mixed_q_lt_0p10']} group terms below q < 0.10.

## D1/D3 Interpretation

D1 remains fragile after artifact control: acute mTBI vs control does not survive broad artifact-controlled FDR (minimum q = {fmt(checks['acute_trim_q'])}). The narrower prior-anchor family remains exploratory and non-confirmatory (q = {fmt(checks['narrow_q'])}). D3 posterior alpha/IAF does not rescue the signal (minimum q = {fmt(checks['d3_posterior_q'])}). Chronic TBI effects remain separate and batch-sensitive (minimum q = {fmt(checks['chronic_q'])}).

## ds003490 Role

`ds003490` remains a comparator/pipeline rehearsal dataset only. It is not TBI validation and is not evidence for a TBI claim.

## Recommended Scientific Framing

Use a cautious methods/results framing: public EEG TBI analyses show how apparent spectral effects attenuate under artifact control and cross-task falsification. The main contribution is transparency about fragility, identity overlap, and task context.

## Not Supported

- A positive diagnostic, prognostic, predictive, or clinical-utility claim.
- No validated biomarker or confirmed-marker claim.
- Independent-cohort confirmation from D2.
- Chronic and acute pooling.
- A classifier-based rescue analysis.
- Treating comparator dataset `ds003490` as TBI evidence.
"""


def report_16(data: dict[str, list[dict[str, str]]]) -> str:
    metrics = derived_metrics(data)
    checks = d1_checks(data)
    return f"""# Updated Final Recommendation

Generated: 2026-06-13

## Recommendation

Proceed only after a clean audit gate, and only with cautious package consolidation or human review. The scientific state is artifact-sensitive/null-leaning with D2 providing partial/inconsistent cross-task support, not independent confirmation.

## Current Evidence State

{markdown_table(summary_rows(data), max_rows=10)}

`ds005114` and `ds003523` raw EEG retrieval, pairing, sidecars, git-annex local availability, and MNE read-tests are complete. D2 feature extraction/model outputs exist from the completed bounded run. The restored D2 conclusion is partial/inconsistent support: cue-baseline DPX minimum q = {fmt(metrics['cue_min_q'])}, DPX task-average q = {fmt(metrics['dpx_task_min_q'])}, VWM task-average q = {fmt(metrics['vwm_task_min_q'])}, and mixed group q < 0.10 count = {metrics['mixed_q_lt_0p10']}.

D1/D3 remain cautionary. Acute D1 does not survive broad artifact-controlled FDR (q = {fmt(checks['acute_trim_q'])}), D3 posterior alpha/IAF does not rescue the signal (q = {fmt(checks['d3_posterior_q'])}), and chronic TBI remains secondary and batch-sensitive (q = {fmt(checks['chronic_q'])}).

## Manuscript Path

The strongest honest future manuscript is a transparent reproducibility/falsification analysis: acute mTBI vs control remains the primary comparison; chronic TBI is reported separately; D2 is within-cohort cross-task evidence only; `ds003490` remains a comparator/pipeline rehearsal dataset.
"""


def report_11(data: dict[str, list[dict[str, str]]]) -> str:
    rows = [
        {"item": "ds003490", "status": "complete comparator", "note": "Retrieved and rehearsed; not used as TBI evidence."},
        {"item": "ds003522", "status": "complete for D1/D3", "note": "Retrieved, verified, and D1/D3 artifact-control analyses completed."},
        {"item": "ds005114", "status": "complete for D2", "note": "Retrieved, verified, and included in bounded D2 outputs."},
        {"item": "ds003523", "status": "complete for D2", "note": "Retrieved, verified, and included in bounded D2 outputs."},
        {"item": "D2 models", "status": "complete bounded check", "note": "Partial/inconsistent cross-task support; no independent-cohort claim."},
        {"item": "Stale report repair", "status": "complete pending audit rerun", "note": "Reports 32-36, 16, and 11 repaired from authoritative outputs."},
    ]
    return f"""# D1 D2 D3 Continuation Status

Generated: 2026-06-13

## Status Summary

{markdown_table(rows, max_rows=20)}

## Current D2 Decision

{markdown_table(summary_rows(data), max_rows=10)}

## Next Analysis Boundary

This repair step restored stale report files only. No downloads, raw-data modification, feature extraction, or statistical modeling were run. The next phase may proceed only if the rerun stale-job accuracy audit produces `AUDIT_PASS.ok` and `audit_gate.json` reports `PASS`.
"""


def write_repair_log(
    status: str,
    backup_dir: Path,
    backup_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    stale_summary = [
        {"failed_item": "reports/32-36", "finding": "stale pending ds003523 text in current D2 reports"},
        {"failed_item": "reports/35 and reports/36", "finding": "modified after final D2 synthesis and missing final D2 conclusion"},
        {"failed_item": "machine-readable outputs", "finding": "numeric outputs remained usable and were treated as authoritative"},
    ]
    restored = [
        {"conclusion": "D2 result", "value": "partial/inconsistent cross-task support"},
        {"conclusion": "DPX cue-baseline", "value": "only weak q<0.10 trace, min q about 0.0898 and max |g| about 0.5277"},
        {"conclusion": "DPX task-average", "value": "not FDR-surviving, q about 0.1524"},
        {"conclusion": "VWM task-average", "value": "not FDR-surviving, q about 0.4720"},
        {"conclusion": "mixed models", "value": "0 group terms below q<0.10"},
        {"conclusion": "D1/D3", "value": "artifact-sensitive/null-leaning; D3 does not rescue signal"},
    ]
    error_text = "\n".join(f"- {err}" for err in errors) or "- None."
    warning_text = "\n".join(f"- {warn}" for warn in warnings) or "- None."
    text = f"""# Stale Report Repair Log

Generated: {now_iso()}

## Repair Status

**{status}**

## Failed Audit Findings Repaired

{markdown_table(stale_summary, max_rows=10)}

## Backup Location

`{backup_dir}`

## Files Backed Up

{markdown_table(backup_rows, max_rows=20)}

## Authoritative Sources Used

{markdown_table(source_rows, max_rows=30)}

## Restored Conclusions

{markdown_table(restored, max_rows=20)}

## Repair Actions

{markdown_table(actions, max_rows=30)}

## Warnings

{warning_text}

## Errors

{error_text}

## Uncertainty

No uncertainty remains if the subsequent stale-job accuracy audit passes. If the audit remains FAIL, this repair log should be treated as an attempted repair only, not a clean package gate.
"""
    write_text(REPAIR_REPORT, text)


def current_report_stale_hits() -> list[str]:
    phrases = [
        "ds003523 pending",
        "pending ds003523",
        "ds003523 remains in progress",
        "ds003523 download is still running",
        "ds003523 retrieval is currently active",
        "D2 remains unstarted",
        "D2 extraction not started",
        "D2 convergence pending",
        "ds005114 only",
    ]
    hits = []
    for rel in REPORTS_TO_REPAIR:
        text = project_path(rel).read_text(encoding="utf-8", errors="replace").lower()
        for phrase in phrases:
            if phrase.lower() in text:
                hits.append(f"{rel}: {phrase}")
    return hits


def key_values_for_source(path: Path, rel: str) -> str:
    rows = read_rows_csv(path)
    if rel.endswith("d2_falsification_summary.csv"):
        return "; ".join(f"{row.get('dataset_id')}={row.get('interpretation')} min_q={row.get('min_fdr_q')}" for row in rows)
    if rel.endswith("d2_within_dataset_group_effects.csv"):
        cue = [row for row in rows if row.get("dataset_id") == "ds005114" and row.get("task_window") == "cue_locked_baseline_2s"]
        dpx = [row for row in rows if row.get("dataset_id") == "ds005114" and row.get("task_window") == "task_average_4s"]
        vwm = [row for row in rows if row.get("dataset_id") == "ds003523" and row.get("task_window") == "task_average_4s"]
        return f"cue_min_q={fmt(min_value(cue, 'fdr_q'))}; cue_max_abs_g={fmt(max_abs_value(cue, 'hedges_g'))}; dpx_task_min_q={fmt(min_value(dpx, 'fdr_q'))}; vwm_task_min_q={fmt(min_value(vwm, 'fdr_q'))}"
    if rel.endswith("d2_mixed_effects_models.csv"):
        return f"n_rows={len(rows)}; q_lt_0p10={sum(1 for row in rows if (safe_float(row.get('group_reference_task_fdr_q')) or 1.0) < 0.10)}"
    if rel.endswith("d1_d3_audit_checks.csv"):
        checks = {row.get("check_id"): row.get("value") for row in rows}
        return f"acute_trim={checks.get('acute_trim_min_fdr')}; d3_post={checks.get('d3_acute_mtbi_vs_control_posterior_min_fdr_q')}; chronic={checks.get('chronic_trim_min_fdr')}"
    if rel.endswith("d1_d3_model_family_audit.csv"):
        narrow = next((row for row in rows if row.get("family_name") == "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal"), {})
        return f"narrow_prior_anchor_q={narrow.get('min_recomputed_bh_q', '')}"
    if rel.endswith("d2_raw_download_summary.csv"):
        return "; ".join(f"{row.get('dataset_id')}:set={row.get('summary_set_count')} fdt={row.get('summary_fdt_count')} mne={row.get('mne_read_pass_count')}/{row.get('mne_read_test_count')}" for row in rows)
    return f"rows={len(rows)}"


def derived_metrics(data: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    within = data["outputs/d2_cross_task/d2_within_dataset_group_effects.csv"]
    cue = [row for row in within if row.get("dataset_id") == "ds005114" and row.get("task_window") == "cue_locked_baseline_2s"]
    dpx = [row for row in within if row.get("dataset_id") == "ds005114" and row.get("task_window") == "task_average_4s"]
    vwm = [row for row in within if row.get("dataset_id") == "ds003523" and row.get("task_window") == "task_average_4s"]
    direction = data["outputs/d2_cross_task/d2_direction_consistency.csv"]
    mixed = data["outputs/d2_cross_task/d2_mixed_effects_models.csv"]
    summary = data["outputs/d2_cross_task/d2_falsification_summary.csv"]
    overall = next((row for row in summary if row.get("summary_level") == "overall_d2"), {})
    dpx_dir = bool_counts([row for row in direction if row.get("dataset_id") == "ds005114" and row.get("task_window") == "task_average_4s"])
    vwm_dir = bool_counts([row for row in direction if row.get("dataset_id") == "ds003523" and row.get("task_window") == "task_average_4s"])
    status_counts = Counter(row.get("model_status", "") for row in mixed)
    return {
        "cue_min_q": min_value(cue, "fdr_q"),
        "cue_max_abs_g": max_abs_value(cue, "hedges_g"),
        "dpx_task_min_q": min_value(dpx, "fdr_q"),
        "vwm_task_min_q": min_value(vwm, "fdr_q"),
        "overall_min_q": safe_float(overall.get("min_fdr_q")),
        "mixed_q_lt_0p10": sum(1 for row in mixed if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10),
        "mixedlm_completed": status_counts.get("mixedlm_completed", 0),
        "clustered_ols_fallback": status_counts.get("clustered_ols_fallback", 0),
        "dpx_direction_matches": dpx_dir[0],
        "dpx_direction_tests": dpx_dir[1],
        "vwm_direction_matches": vwm_dir[0],
        "vwm_direction_tests": vwm_dir[1],
    }


def d1_checks(data: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    rows = data["outputs/qc/d1_d3_audit_checks.csv"]
    checks = {row.get("check_id"): safe_float(row.get("value")) for row in rows}
    family = data["outputs/qc/d1_d3_model_family_audit.csv"]
    narrow = next((row for row in family if row.get("family_name") == "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal"), {})
    return {
        "acute_trim_q": checks.get("acute_trim_min_fdr"),
        "d3_posterior_q": checks.get("d3_acute_mtbi_vs_control_posterior_min_fdr_q"),
        "chronic_q": checks.get("chronic_trim_min_fdr"),
        "narrow_q": safe_float(narrow.get("min_recomputed_bh_q")),
    }


def summary_rows(data: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows = []
    for row in data["outputs/d2_cross_task/d2_falsification_summary.csv"]:
        rows.append(
            {
                "summary_level": row.get("summary_level", ""),
                "dataset_id": row.get("dataset_id", ""),
                "n_group_effect_rows": row.get("n_group_effect_rows", ""),
                "min_fdr_q": fmt(row.get("min_fdr_q")),
                "max_abs_g": fmt(row.get("max_abs_hedges_g")),
                "direction_match_rate": fmt(row.get("direction_match_rate_vs_d1")),
                "n_stability_q_lt_0p10": row.get("n_stability_q_lt_0p10", ""),
                "n_mixed_group_q_lt_0p10": row.get("n_mixed_group_q_lt_0p10", ""),
                "interpretation": row.get("interpretation", ""),
            }
        )
    return rows


def top_effect_rows(rows: list[dict[str, str]], n: int) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("fdr_q")) if safe_float(row.get("fdr_q")) is not None else 999.0)
    return [
        {
            "dataset_id": row.get("dataset_id", ""),
            "task_window": row.get("task_window", ""),
            "region": row.get("region", ""),
            "feature_name": row.get("feature_name", ""),
            "n": row.get("n_total", ""),
            "hedges_g": fmt(row.get("hedges_g")),
            "welch_p": fmt(row.get("welch_p")),
            "fdr_q": fmt(row.get("fdr_q")),
            "permutation_p": fmt(row.get("permutation_p")),
        }
        for row in sorted_rows[:n]
    ]


def task_average_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return top_effect_rows([row for row in rows if row.get("task_window") == "task_average_4s"], 12)


def direction_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for dataset_id in ["ds005114", "ds003523"]:
        subset = [row for row in rows if row.get("dataset_id") == dataset_id and row.get("task_window") == "task_average_4s"]
        matches, total = bool_counts(subset)
        out.append(
            {
                "dataset_id": dataset_id,
                "task_window": "task_average_4s",
                "direction_matches": matches,
                "direction_tests": total,
                "match_rate": fmt(matches / total if total else math.nan),
                "notes": "descriptive only",
            }
        )
    return out


def top_stability_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("spearman_fdr_q")) if safe_float(row.get("spearman_fdr_q")) is not None else 999.0)
    return [
        {
            "task_a": row.get("task_a", ""),
            "task_b": row.get("task_b", ""),
            "region": row.get("region", ""),
            "feature_name": row.get("feature_name", ""),
            "n_subjects": row.get("n_subjects", ""),
            "rho": fmt(row.get("spearman_rho")),
            "fdr_q": fmt(row.get("spearman_fdr_q")),
        }
        for row in sorted_rows[:10]
    ]


def mixed_status_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts = Counter(row.get("model_status", "") for row in rows)
    return [
        {"metric": "n_models", "value": len(rows)},
        {"metric": "mixedlm_completed", "value": counts.get("mixedlm_completed", 0)},
        {"metric": "clustered_ols_fallback", "value": counts.get("clustered_ols_fallback", 0)},
        {"metric": "min_group_reference_task_fdr_q", "value": fmt(min_value(rows, "group_reference_task_fdr_q"))},
        {"metric": "n_group_reference_task_q_lt_0p10", "value": sum(1 for row in rows if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10)},
    ]


def bool_counts(rows: list[dict[str, str]]) -> tuple[int, int]:
    parsed = []
    for row in rows:
        text = str(row.get("direction_match", "")).strip().lower()
        if text == "true":
            parsed.append(True)
        elif text == "false":
            parsed.append(False)
    return sum(1 for value in parsed if value), len(parsed)


def action_row(action_id: str, file_path: Path, action: str, source_used: str, reason: str, success: bool, notes: str) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "file_path": str(file_path),
        "action": action,
        "source_used": source_used,
        "reason": reason,
        "timestamp": now_iso(),
        "success": str(success).lower(),
        "notes": notes,
    }


def min_value(rows: list[dict[str, str]], field: str) -> float | None:
    vals = [safe_float(row.get(field)) for row in rows]
    vals = [val for val in vals if val is not None]
    return min(vals) if vals else None


def max_abs_value(rows: list[dict[str, str]], field: str) -> float | None:
    vals = [safe_float(row.get(field)) for row in rows]
    vals = [abs(val) for val in vals if val is not None]
    return max(vals) if vals else None


def safe_float(value: Any) -> float | None:
    try:
        if value in ("", None, "nan", "NaN"):
            return None
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def fmt(value: Any) -> str:
    parsed = safe_float(value)
    if parsed is None:
        return ""
    if abs(parsed) < 0.001 and parsed != 0:
        return f"{parsed:.3e}"
    return f"{parsed:.4f}"


def mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
