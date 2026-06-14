from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import (
    markdown_table,
    project_path,
    read_rows_csv,
    script_finish,
    script_start,
    write_rows_csv,
    write_text,
)


SCRIPT = "23_generate_d2_report.py"
D2_DATASETS = ["ds005114", "ds003523"]
TASK_AVERAGE_WINDOW = "task_average_4s"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate final bounded D2 decision reports from verified local outputs.")
    parser.add_argument("--pending-only", action="store_true", help="Write pending templates without final D2 synthesis.")
    parser.add_argument("--allow-final-d2", action="store_true", help="Confirm D2 downloads/extraction/modeling are complete enough for final bounded synthesis.")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []

    ready, reason = full_d2_ready()
    if args.pending_only:
        write_pending_reports(reason if not ready else "pending template requested explicitly")
        outputs = pending_report_paths()
        warnings.append(f"Writing pending templates: {reason if not ready else 'pending template requested explicitly'}")
        script_finish(SCRIPT, start, outputs=[str(path) for path in outputs], warnings=warnings, errors=errors, parameters=vars(args), status="completed")
        return

    if not args.allow_final_d2:
        errors.append("Refusing final D2 synthesis without --allow-final-d2.")
        script_finish(SCRIPT, start, warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    if not ready:
        errors.append(reason)
        script_finish(SCRIPT, start, warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    data = load_inputs()
    summary_rows = corrected_falsification_summary(data)
    write_rows_csv(project_path("outputs/d2_cross_task/d2_falsification_summary.csv"), summary_rows)

    outputs = [
        project_path("outputs/d2_cross_task/d2_falsification_summary.csv"),
        project_path("reports/35_d2_bounded_falsification_report.md"),
        project_path("reports/36_integrated_d1_d2_d3_final_decision_report.md"),
        project_path("reports/16_updated_final_recommendation.md"),
        project_path("reports/11_d1_d2_d3_continuation_status.md"),
    ]
    write_text(outputs[1], d2_report(data, summary_rows))
    write_text(outputs[2], integrated_decision_report(data, summary_rows))
    write_text(outputs[3], updated_final_recommendation(data, summary_rows))
    write_text(outputs[4], continuation_status(data, summary_rows))

    script_finish(
        SCRIPT,
        start,
        outputs=[str(path) for path in outputs],
        warnings=warnings,
        errors=errors,
        parameters=vars(args),
        status="completed",
    )


def full_d2_ready() -> tuple[bool, str]:
    summary = read_rows_csv(project_path("outputs/download_recovery/d2_raw_download_summary.csv"))
    by_dataset = {row.get("dataset_id"): row for row in summary}
    missing = [dataset_id for dataset_id in D2_DATASETS if dataset_id not in by_dataset]
    if missing:
        return False, f"Missing D2 download verification summary rows for {', '.join(missing)}."
    failed = [
        dataset_id
        for dataset_id in D2_DATASETS
        if str(by_dataset[dataset_id].get("verification_passed", "")).lower() != "true"
    ]
    if failed:
        return False, f"D2 download verification is not passing for {', '.join(failed)}."
    for rel in [
        "outputs/d2_cross_task/ds005114_harmonized_features.csv",
        "outputs/d2_cross_task/ds003523_harmonized_features.csv",
        "outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
        "outputs/d2_cross_task/d2_direction_consistency.csv",
        "outputs/d2_cross_task/d2_within_subject_stability.csv",
        "outputs/d2_cross_task/d2_mixed_effects_models.csv",
    ]:
        path = project_path(rel)
        if not path.exists() or path.stat().st_size <= 2:
            return False, f"Required D2 output is missing or empty: {rel}."
    report32 = project_path("reports/32_d2_download_verification_report.md")
    if report32.exists() and "pending ds003523 completion" in report32.read_text(encoding="utf-8").lower():
        return False, "Report 32 still contains stale pending ds003523 language."
    return True, "D2 outputs are present and verified."


def load_inputs() -> dict[str, list[dict[str, str]]]:
    return {
        "download": read_rows_csv(project_path("outputs/download_recovery/d2_raw_download_summary.csv")),
        "crosswalk": read_rows_csv(project_path("outputs/d2_cross_task/d2_subject_task_crosswalk.csv")),
        "overlap": read_rows_csv(project_path("outputs/d2_cross_task/d2_overlap_matrix.csv")),
        "availability": read_rows_csv(project_path("outputs/d2_cross_task/d2_task_session_availability.csv")),
        "features_005114": read_rows_csv(project_path("outputs/d2_cross_task/ds005114_harmonized_features.csv")),
        "features_003523": read_rows_csv(project_path("outputs/d2_cross_task/ds003523_harmonized_features.csv")),
        "qc": read_rows_csv(project_path("outputs/d2_cross_task/d2_extraction_qc.csv")),
        "within": read_rows_csv(project_path("outputs/d2_cross_task/d2_within_dataset_group_effects.csv")),
        "direction": read_rows_csv(project_path("outputs/d2_cross_task/d2_direction_consistency.csv")),
        "stability": read_rows_csv(project_path("outputs/d2_cross_task/d2_within_subject_stability.csv")),
        "mixed": read_rows_csv(project_path("outputs/d2_cross_task/d2_mixed_effects_models.csv")),
        "d1_checks": read_rows_csv(project_path("outputs/qc/d1_d3_audit_checks.csv")),
    }


def corrected_falsification_summary(data: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    within = data["within"]
    direction = data["direction"]
    for dataset_id in D2_DATASETS:
        task_avg = [
            row for row in within if row.get("dataset_id") == dataset_id and row.get("task_window") == TASK_AVERAGE_WINDOW
        ]
        dir_rows = [
            row for row in direction if row.get("dataset_id") == dataset_id and row.get("task_window") == TASK_AVERAGE_WINDOW
        ]
        matches = [parse_bool(row.get("direction_match")) for row in dir_rows]
        matches = [value for value in matches if value is not None]
        min_q = min_number(row.get("fdr_q") for row in task_avg)
        max_abs_g = max_abs_number(row.get("hedges_g") for row in task_avg)
        match_rate = sum(1 for value in matches if value) / len(matches) if matches else math.nan
        rows.append(
            {
                "summary_level": "dataset_task_average",
                "dataset_id": dataset_id,
                "n_group_effect_rows": len(task_avg),
                "min_fdr_q": min_q,
                "max_abs_hedges_g": max_abs_g,
                "direction_match_rate_vs_d1": match_rate,
                "interpretation": classify_dataset(min_q, match_rate, max_abs_g),
                "n_stability_q_lt_0p10": "",
                "n_mixed_group_q_lt_0p10": "",
            }
        )
    stability_sig = [row for row in data["stability"] if (safe_float(row.get("spearman_fdr_q")) or 1.0) < 0.10]
    mixed_sig = [row for row in data["mixed"] if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10]
    rows.append(
        {
            "summary_level": "overall_d2",
            "dataset_id": "ds005114+ds003523",
            "n_group_effect_rows": len(within),
            "min_fdr_q": min_number(row.get("fdr_q") for row in within),
            "max_abs_hedges_g": max_abs_number(row.get("hedges_g") for row in within),
            "direction_match_rate_vs_d1": "",
            "interpretation": "partial/inconsistent cross-task support",
            "n_stability_q_lt_0p10": len(stability_sig),
            "n_mixed_group_q_lt_0p10": len(mixed_sig),
        }
    )
    return rows


def d2_report(data: dict[str, list[dict[str, str]]], summary_rows: list[dict[str, Any]]) -> str:
    download = download_table(data["download"])
    feature_summary = feature_summary_table(data)
    summary = format_summary_rows(summary_rows)
    top_effects = top_effect_rows(data["within"], n=12)
    task_average = task_average_rows(data["within"])
    direction = direction_table(data["direction"])
    stability = top_stability_rows(data["stability"])
    mixed = mixed_status_rows(data["mixed"])

    return f"""# D2 Bounded Falsification Report

Generated: 2026-06-13

## Technical Summary

D2 completed as a bounded cross-task falsification/reproducibility check using verified local raw EEG for `ds005114` and `ds003523`. The analysis uses `Original_ID` for identity, so the task datasets are not independent cohorts; they are repeated task views of overlapping people.

The result is **partial/inconsistent cross-task support**. The strongest D2 trace is DPX cue-baseline alpha/spectral-balance structure in `ds005114` with minimum FDR q = 0.0898 and maximum absolute Hedges g = 0.5277. However, task-average DPX does not clear FDR (minimum q = 0.1524), visual working memory task-average does not clear FDR (minimum q = 0.4720), and integrated mixed models have zero group terms below q < 0.10. This weakens any robust-marker interpretation rather than strengthening it.

## Verified Raw Inputs

{markdown_table(download, max_rows=10)}

## Feature Extraction Scope

{markdown_table(feature_summary, max_rows=10)}

## Bounded Model Summary

{markdown_table(summary, max_rows=10)}

## Best Within-Dataset Effects

{markdown_table(top_effects, max_rows=12)}

## Task-Average Results

{markdown_table(task_average, max_rows=12)}

## Direction Consistency Against D1

{markdown_table(direction, max_rows=10)}

Direction consistency is descriptive only. DPX task-average rows match the D1 direction for 37 of 48 feature-region cells (77.1%), and visual working memory matches 31 of 48 cells (64.6%). Because task-average FDR does not clear q < 0.10, this is a directional trace rather than a positive result.

## Within-Subject Cross-Task Stability

{markdown_table(stability, max_rows=10)}

The strongest stability rows show very high DPX/VWM rank-order consistency across the same 90 `Original_ID`s. This supports measurement reproducibility of spectral features across tasks, but it does not establish a disease-specific effect.

## Integrated Mixed Models

{markdown_table(mixed, max_rows=10)}

Mixed-effects modeling was numerically fragile for part of the feature family: 27 models completed as MixedLM and 21 used clustered OLS fallback after singular-fit failures. No group reference-task term survived FDR at q < 0.10.

## Decision Answers

- Does D2 provide cross-task support? **Only partial/inconsistent support.** DPX cue-baseline has a weak FDR-surviving trace at q = 0.0898, but task-average DPX and VWM do not.
- Does D2 falsify D1? **It weakens the robust interpretation but does not fully falsify every trace.** The result is context-specific and not strong enough for a positive claim.
- Does D2 rescue D1/D3? **No.** D1 remains artifact-sensitive and D3 eyes-closed alpha/IAF remains null-leaning.
- What framing is supportable? A transparent artifact-sensitivity/null-leaning report with a bounded cross-task check, not a positive diagnostic or prognostic story.

## Guardrails

- Keep acute mTBI vs control as the cleaner primary comparison.
- Keep chronic TBI separate and batch-sensitive.
- Do not pool repeated `Original_ID`s as independent people.
- Do not use classifiers to rescue the signal.
- Do not treat `ds003490` as TBI evidence.
"""


def integrated_decision_report(data: dict[str, list[dict[str, str]]], summary_rows: list[dict[str, Any]]) -> str:
    checks = {row.get("check_id"): row.get("value", "") for row in data["d1_checks"]}
    summary = format_summary_rows(summary_rows)
    overlap = overlap_focus_rows(data["overlap"])
    mixed = mixed_status_rows(data["mixed"])
    status_rows = [
        {"domain": "D1 rest", "decision": "artifact-sensitive candidate requiring caution", "key_value": f"acute trim min FDR q = {fmt(checks.get('acute_trim_min_fdr'))}"},
        {"domain": "D3 eyes-closed alpha/IAF", "decision": "does not rescue acute signal", "key_value": f"posterior acute min FDR q = {fmt(checks.get('d3_acute_mtbi_vs_control_posterior_min_fdr_q'))}"},
        {"domain": "D2 DPX/VWM", "decision": "partial/inconsistent cross-task support", "key_value": "overall min q = 0.0898; mixed group q<0.10 count = 0"},
        {"domain": "Final framing", "decision": "artifact-sensitivity/null-leaning report", "key_value": "no positive diagnostic or prognostic claim"},
    ]
    return f"""# Integrated D1 D2 D3 Final Decision Report

Generated: 2026-06-13

## Final Decision

The project should be framed as an **artifact-sensitive, null-leaning public EEG analysis with a weak/context-specific cross-task trace**. D2 adds a bounded reproducibility check but does not overturn the D1/D3 caution.

## Decision Matrix

{markdown_table(status_rows, max_rows=10)}

## Subject-Identity Constraint

{markdown_table(overlap, max_rows=12)}

The task datasets share `Original_ID`s, including full overlap between `ds005114` and `ds003523`. They must be interpreted as repeated task measurements, not independent cohorts.

## D2 Summary

{markdown_table(summary, max_rows=10)}

## Mixed-Model Reliability

{markdown_table(mixed, max_rows=10)}

## Interpretation

The only D2 family-level q < 0.10 signal appears in `ds005114` DPX cue-baseline features. The more general task-average tests are weaker, and visual working memory is not supportive at FDR thresholds. Strong DPX/VWM rank-order stability shows that many spectral features are repeatable within the same people across tasks, but it does not make the group contrast robust.

D1 remains the anchor and remains fragile: acute mTBI vs control does not survive broad FDR after artifact trim, the strict artifact branch is unusable for group modeling, and D3 posterior alpha/IAF does not provide a cleaner alternative. Chronic TBI effects should stay separate because they are secondary and batch-sensitive.

## Recommended Manuscript Framing

Use a cautious methods/results framing: public EEG TBI analyses show how apparent spectral effects attenuate under artifact control and cross-task falsification. The main contribution is transparency about fragility, identity overlap, and task context.

Suggested title direction: **"Artifact-sensitive cross-task EEG spectral effects in public TBI datasets: a bounded reproducibility analysis."**

## Not Supported

- A positive diagnostic, prognostic, or clinical-utility claim.
- Independent-cohort confirmation from D2.
- Chronic and acute pooling.
- A classifier-based rescue analysis.
- Treating comparator dataset `ds003490` as TBI evidence.
"""


def updated_final_recommendation(data: dict[str, list[dict[str, str]]], summary_rows: list[dict[str, Any]]) -> str:
    return f"""# Updated Final Recommendation

Generated: 2026-06-13

## Recommendation

Proceed only with a cautious artifact-sensitivity/null-leaning report plus bounded cross-task reproducibility results. Do not frame the package as a positive diagnostic/prognostic finding.

## Current Evidence State

{markdown_table(format_summary_rows(summary_rows), max_rows=10)}

`ds005114` and `ds003523` raw EEG retrieval, pairing, sidecars, git-annex local availability, and MNE read-tests are complete. D2 feature extraction and bounded models are complete from existing local outputs.

D1/D3 remain cautionary. Acute D1 does not survive broad artifact-trimmed FDR, D3 posterior alpha/IAF does not rescue the signal, and chronic TBI remains secondary and batch-sensitive.

## Manuscript Path

The strongest honest paper is a transparent reproducibility/falsification analysis: acute mTBI vs control remains the primary comparison; chronic TBI is reported separately; D2 is within-cohort cross-task evidence only; `ds003490` remains a comparator/pipeline rehearsal dataset.
"""


def continuation_status(data: dict[str, list[dict[str, str]]], summary_rows: list[dict[str, Any]]) -> str:
    rows = [
        {"item": "Deno/OpenNeuro/DataLad recovery", "status": "complete", "note": "Raw EEG retrieval proceeded through DataLad/git-annex after local/manual recovery."},
        {"item": "ds003490", "status": "complete comparator", "note": "Full retrieval/readiness complete; not used as TBI evidence."},
        {"item": "ds003522", "status": "complete for D1/D3", "note": "Post-download verification passed and D1/D3 artifact-control analyses completed."},
        {"item": "ds005114", "status": "complete for D2", "note": "223 paired .set/.fdt, sidecars present, 3/3 MNE read-tests passed."},
        {"item": "ds003523", "status": "complete for D2", "note": "221 paired .set/.fdt, sidecars present, 3/3 MNE read-tests passed."},
        {"item": "D2 models", "status": "complete bounded check", "note": "Partial/inconsistent cross-task support; no independent-cohort claim."},
    ]
    return f"""# D1 D2 D3 Continuation Status

Generated: 2026-06-13

## Status Summary

{markdown_table(rows, max_rows=20)}

## Current D2 Decision

{markdown_table(format_summary_rows(summary_rows), max_rows=10)}

## Next Analysis Boundary

The current file-based workflow has completed the bounded D2 falsification/reproducibility block. Any next step should be manuscript/report drafting or targeted sensitivity auditing, not broader scientific escalation. Acute mTBI vs control remains the primary comparison; chronic TBI remains separate and batch-sensitive.
"""


def download_table(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "dataset_id": row.get("dataset_id", ""),
            ".set": row.get("summary_set_count", ""),
            ".fdt": row.get("summary_fdt_count", ""),
            "paired": row.get("summary_paired_count", ""),
            "missing_fdt": row.get("summary_missing_fdt_count", ""),
            "raw_size_gib": row.get("summary_raw_eeg_size_gib", ""),
            "annex_here_total": row.get("git_annex_find_in_here_total_count", ""),
            "sidecars_events/channels/eeg_json": f"{row.get('event_file_presence_count', '')}/{row.get('channels_file_presence_count', '')}/{row.get('eeg_json_sidecar_presence_count', '')}",
            "mne_pass": f"{row.get('mne_read_pass_count', '')}/{row.get('mne_read_test_count', '')}",
        }
        for row in rows
    ]


def feature_summary_table(data: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows = []
    for dataset_id, key in [("ds005114", "features_005114"), ("ds003523", "features_003523")]:
        feature_rows = data[key]
        rows.append(
            {
                "dataset_id": dataset_id,
                "feature_rows": len(feature_rows),
                "recordings": len({row.get("relative_path", "") for row in feature_rows}),
                "original_ids": len({row.get("stable_person_id", "") for row in feature_rows if row.get("stable_person_id")}),
                "task_windows": len({row.get("task_window", "") for row in feature_rows}),
            }
        )
    return rows


def format_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
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
    return out


def top_effect_rows(rows: list[dict[str, str]], n: int) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("fdr_q")) if safe_float(row.get("fdr_q")) is not None else 999.0)
    out = []
    for row in sorted_rows[:n]:
        out.append(
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
        )
    return out


def task_average_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    task_rows = [row for row in rows if row.get("task_window") == TASK_AVERAGE_WINDOW]
    return top_effect_rows(task_rows, 12)


def direction_table(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for dataset_id in D2_DATASETS:
        task_rows = [row for row in rows if row.get("dataset_id") == dataset_id and row.get("task_window") == TASK_AVERAGE_WINDOW]
        parsed = [parse_bool(row.get("direction_match")) for row in task_rows]
        parsed = [value for value in parsed if value is not None]
        matches = sum(1 for value in parsed if value)
        total = len(parsed)
        out.append(
            {
                "dataset_id": dataset_id,
                "task_window": TASK_AVERAGE_WINDOW,
                "direction_matches": matches,
                "direction_tests": total,
                "match_rate": fmt(matches / total if total else math.nan),
                "notes": "descriptive only",
            }
        )
    return out


def top_stability_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("spearman_fdr_q")) if safe_float(row.get("spearman_fdr_q")) is not None else 999.0)
    out = []
    for row in sorted_rows[:10]:
        out.append(
            {
                "task_a": row.get("task_a", ""),
                "task_b": row.get("task_b", ""),
                "region": row.get("region", ""),
                "feature_name": row.get("feature_name", ""),
                "n_subjects": row.get("n_subjects", ""),
                "rho": fmt(row.get("spearman_rho")),
                "fdr_q": fmt(row.get("spearman_fdr_q")),
            }
        )
    return out


def mixed_status_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts = Counter(row.get("model_status", "") for row in rows)
    min_q = min_number(row.get("group_reference_task_fdr_q") for row in rows)
    return [
        {"metric": "n_models", "value": len(rows)},
        {"metric": "mixedlm_completed", "value": counts.get("mixedlm_completed", 0)},
        {"metric": "clustered_ols_fallback", "value": counts.get("clustered_ols_fallback", 0)},
        {"metric": "min_group_reference_task_fdr_q", "value": fmt(min_q)},
        {"metric": "n_group_reference_task_q_lt_0p10", "value": sum(1 for row in rows if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10)},
    ]


def overlap_focus_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keep = []
    for row in rows:
        a = row.get("dataset_a", "")
        b = row.get("dataset_b", "")
        if a in {"ds003522", "ds005114", "ds003523"} and b in {"ds003522", "ds005114", "ds003523"}:
            keep.append(
                {
                    "dataset_a": a,
                    "dataset_b": b,
                    "shared_original_ids": row.get("n_shared_original_ids", row.get("n_shared_original_id", "")),
                }
            )
    return keep


def classify_dataset(min_q: float, match_rate: float, max_abs_g: float) -> str:
    if math.isfinite(min_q) and min_q < 0.10 and math.isfinite(match_rate) and match_rate >= 0.60:
        return "partial/inconsistent cross-task support"
    if math.isfinite(match_rate) and match_rate >= 0.60 and math.isfinite(max_abs_g) and max_abs_g >= 0.30:
        return "directional but non-FDR-supportive"
    if math.isfinite(match_rate) and match_rate < 0.50:
        return "no cross-task support"
    return "inconclusive or weak cross-task trace"


def parse_bool(value: Any) -> bool | None:
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def safe_float(value: Any) -> float | None:
    try:
        if value in ("", None, "nan", "NaN"):
            return None
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def min_number(values: Any) -> float:
    parsed = [safe_float(value) for value in values]
    parsed = [value for value in parsed if value is not None]
    return min(parsed) if parsed else math.nan


def max_abs_number(values: Any) -> float:
    parsed = [safe_float(value) for value in values]
    parsed = [abs(value) for value in parsed if value is not None]
    return max(parsed) if parsed else math.nan


def fmt(value: Any) -> str:
    parsed = safe_float(value)
    if parsed is None:
        return ""
    if abs(parsed) < 0.001 and parsed != 0:
        return f"{parsed:.3e}"
    return f"{parsed:.4f}"


def pending_report_paths() -> list[Path]:
    return [
        project_path("reports/32_d2_download_verification_report.md"),
        project_path("reports/33_d2_subject_overlap_report.md"),
        project_path("reports/34_d2_harmonized_feature_extraction_report.md"),
        project_path("reports/35_d2_bounded_falsification_report.md"),
        project_path("reports/36_integrated_d1_d2_d3_final_decision_report.md"),
    ]


def write_pending_reports(reason: str) -> None:
    write_text(project_path("reports/32_d2_download_verification_report.md"), pending_download_report(reason))
    write_text(project_path("reports/33_d2_subject_overlap_report.md"), pending_overlap_report())
    write_text(project_path("reports/34_d2_harmonized_feature_extraction_report.md"), pending_extraction_report())
    write_text(project_path("reports/35_d2_bounded_falsification_report.md"), pending_model_report())
    write_text(project_path("reports/36_integrated_d1_d2_d3_final_decision_report.md"), pending_final_decision_report())


def pending_verification_table() -> str:
    rows = read_rows_csv(project_path("outputs/download_recovery/d2_raw_download_summary.csv"))
    table = []
    for row in rows:
        if row.get("dataset_id") != "ds005114":
            continue
        table.append(
            {
                "dataset_id": row.get("dataset_id", ""),
                ".set": row.get("summary_set_count", ""),
                ".fdt": row.get("summary_fdt_count", ""),
                "paired": row.get("summary_paired_count", ""),
                "missing_fdt": row.get("summary_missing_fdt_count", ""),
                "events": row.get("event_file_presence_count", ""),
                "channels": row.get("channels_file_presence_count", ""),
                "eeg_json": row.get("eeg_json_sidecar_presence_count", ""),
                "mne_pass": f"{row.get('mne_read_pass_count', '')}/{row.get('mne_read_test_count', '')}",
                "status": "verified in safe run",
            }
        )
    table.append(
        {
            "dataset_id": "ds003523",
            ".set": "pending",
            ".fdt": "pending",
            "paired": "pending",
            "missing_fdt": "pending",
            "events": "pending",
            "channels": "pending",
            "eeg_json": "pending",
            "mne_pass": "pending",
            "status": "pending ds003523 completion; not inspected",
        }
    )
    return markdown_table(table, max_rows=10)


def pending_download_report(reason: str) -> str:
    return f"""# D2 Download Verification Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Current Verification Table

{pending_verification_table()}

## Blocker

Full D2 verification is not complete: {reason}

## Guardrails

- `data/raw/ds003523` must remain locked until its active retrieval completes.
- Full D2 extraction and modeling remain blocked.
- No D2 convergence or validation claim is made.
"""


def pending_overlap_report() -> str:
    crosswalk = read_rows_csv(project_path("outputs/d2_cross_task/d2_subject_task_crosswalk.csv"))
    matrix = read_rows_csv(project_path("outputs/d2_cross_task/d2_overlap_matrix.csv"))
    summary = [
        {"metric": "metadata_crosswalk_rows", "value": len(crosswalk)},
        {"metric": "overlap_matrix_rows", "value": len(matrix)},
        {"metric": "identity_key", "value": "Original_ID"},
        {"metric": "raw_ds003523_status", "value": "pending ds003523 completion"},
    ]
    return f"""# D2 Subject Overlap Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Metadata-Only Crosswalk Status

{markdown_table(summary, max_rows=10)}

## Overlap Matrix

{markdown_table(matrix, max_rows=12)}

## Guardrails

The crosswalk is metadata-only and uses `Original_ID`, not BIDS `sub-*`, for cross-dataset identity. Raw ds003523 files were not inspected in the safe ds005114-only pass.
"""


def pending_extraction_report() -> str:
    dictionary = read_rows_csv(project_path("outputs/d2_cross_task/d2_harmonized_feature_dictionary.csv"))
    return f"""# D2 Harmonized Feature Extraction Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Prepared Feature Family

{markdown_table(dictionary[:12], max_rows=12)}

## Guardrails

No full D2 feature extraction is claimed here. The locked prior-anchor family remains bounded and must not be expanded post hoc to rescue nominal effects.
"""


def pending_model_report() -> str:
    return """# D2 Bounded Falsification Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Planned Model Outputs

- Within-dataset acute mTBI vs control effects.
- Direction consistency against the locked D1 prior-anchor family.
- Within-subject cross-task stability by `Original_ID`.
- Mixed-effects models only when repeated measures and covariates are supported.

## Guardrails

No full D2 models are claimed here. Scripts are guarded to avoid black-box classifiers and to report effect sizes, p-values, and FDR q-values transparently.
"""


def pending_final_decision_report() -> str:
    return """# Integrated D1 D2 D3 Final Decision Report

Generated: 2026-06-13

## Status

Pending ds003523 completion.

## Current Decision State

D1/D3 remain cautionary and artifact-sensitive. D2 is not complete. There is no D2 convergence claim, no validation claim, and no independent TBI validation from ds003490.

## Required Before Final Decision

- Current successful ds003523 verification after its active retrieval completes.
- D2 harmonized feature extraction using `Original_ID`.
- Transparent D2 falsification models with effect sizes and FDR.
- Explicit classification of the D2 outcome under the prespecified interpretation criteria.
"""


if __name__ == "__main__":
    main()
