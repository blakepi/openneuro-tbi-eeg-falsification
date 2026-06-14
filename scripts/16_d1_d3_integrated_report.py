from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from scripts.utils.common import project_path, read_rows_csv, script_finish, script_start, write_rows_csv
from scripts.utils.stats_utils import benjamini_hochberg, bootstrap_ci_effect, hedges_g, leave_one_out_effect_range, permutation_p_mean_diff, welch_t_test


SCRIPT = "16_d1_d3_integrated_report.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write gated D1/D3 integrated report after verified ds003522 extraction.")
    parser.add_argument("--dataset", default="ds003522")
    parser.add_argument("--verification-csv", default="outputs/download_recovery/ds003522_post_download_verification.csv")
    parser.add_argument("--report", default="reports/24_d1_d3_integrated_artifact_control_report.md")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []
    status_path = project_path("outputs/d1_artifact_control/ds003522_d1_d3_integrated_report_status.csv")

    try:
        require_verified_ds003522(project_path(args.verification_csv))
    except RuntimeError as exc:
        errors.append(str(exc))
        write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "refused", "reason": str(exc)}])
        script_finish(SCRIPT, start, outputs=[str(status_path)], errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(str(exc))

    d1_rows = [row for row in read_rows_csv(project_path("outputs/features/d1_rest_features.csv")) if row.get("dataset_id") == args.dataset]
    d3_rows = [row for row in read_rows_csv(project_path("outputs/features/d3_ec_alpha_iaf_features.csv")) if row.get("dataset_id") == args.dataset]
    if not d1_rows:
        errors.append("No D1 feature rows for ds003522.")
    if not d3_rows:
        warnings.append("No D3 eyes-closed alpha/IAF rows for ds003522.")
    if errors:
        write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "failed", "reason": "; ".join(errors)}])
        script_finish(SCRIPT, start, outputs=[str(status_path)], warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit("; ".join(errors))

    model_rows = run_models(d1_rows, "d1_rest_artifact_control") + run_models(d3_rows, "d3_eyes_closed_alpha_iaf")
    apply_fdr(model_rows)
    sensitivity_rows = artifact_sensitivity(model_rows)

    model_path = project_path("outputs/models/d1_d3_group_models.csv")
    sensitivity_path = project_path("outputs/d1_artifact_control/ds003522_artifact_sensitivity.csv")
    report_path = project_path(args.report)
    write_rows_csv(model_path, model_rows)
    write_rows_csv(sensitivity_path, sensitivity_rows)
    report_path.write_text(build_report(args.dataset, d1_rows, d3_rows, model_rows, sensitivity_rows, warnings), encoding="utf-8", newline="\n")
    write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "completed", "report": str(report_path), "model_rows": len(model_rows), "artifact_sensitivity_rows": len(sensitivity_rows)}])
    script_finish(
        SCRIPT,
        start,
        outputs=[str(report_path), str(status_path), str(model_path), str(sensitivity_path)],
        warnings=warnings,
        errors=errors,
        parameters=vars(args),
        status="completed",
    )


def require_verified_ds003522(verification_csv: Path) -> None:
    if not verification_csv.exists():
        raise RuntimeError(f"Refusing to run: missing verification CSV {verification_csv}.")
    rows = read_rows_csv(verification_csv)
    if not rows:
        raise RuntimeError(f"Refusing to run: verification CSV has no rows: {verification_csv}.")
    first = rows[0]
    for column, expected in {"summary_set_count": 200, "summary_fdt_count": 200, "summary_paired_count": 200, "summary_missing_fdt_count": 0}.items():
        observed = int(float(first.get(column, "")))
        if observed != expected:
            raise RuntimeError(f"Refusing to run: verification {column}={observed}, expected {expected}.")
    if sum(1 for row in rows if row.get("mne_read_test_status") == "passed") < 3:
        raise RuntimeError("Refusing to run: fewer than 3 MNE read-tests passed.")


def run_models(rows: list[dict[str, str]], family: str) -> list[dict[str, Any]]:
    subject_rows = aggregate_to_subject(rows)
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in subject_rows:
        grouped[
            (
                row.get("artifact_branch", ""),
                row.get("condition", ""),
                row.get("region", ""),
                row.get("feature_name", ""),
            )
        ].append(row)
    out: list[dict[str, Any]] = []
    for key, values in grouped.items():
        artifact_branch, condition, region, feature_name = key
        for comparison, group0, group1, interpretation in [
            ("acute_mtbi_vs_control", "control", "mtbi", "primary_cleaner_comparison"),
            ("chronic_tbi_vs_control", "control", "chronic_tbi", "secondary_batch_sensitive"),
        ]:
            y = [row["feature_value"] for row in values if row["group_normalized"] == group0]
            x = [row["feature_value"] for row in values if row["group_normalized"] == group1]
            if len(x) < 2 or len(y) < 2:
                continue
            t, p = welch_t_test(x, y)
            g = hedges_g(x, y)
            ci_low, ci_high = bootstrap_ci_effect(x, y, iterations=2000)
            perm_p = permutation_p_mean_diff(x, y, iterations=5000)
            loo_values = [(row["stable_person_id"], row["feature_value"], row["group_normalized"]) for row in values if row["group_normalized"] in {group0, group1}]
            loo_low, loo_high = leave_one_out_effect_range(loo_values, group0, group1)
            out.append(
                {
                    "analysis_family": family,
                    "comparison": comparison,
                    "dataset_id": "ds003522",
                    "artifact_branch": artifact_branch,
                    "condition": condition,
                    "region": region,
                    "feature_name": feature_name,
                    "n_total": len(x) + len(y),
                    "n_group0": len(y),
                    "n_group1": len(x),
                    "group0_label": group0,
                    "group1_label": group1,
                    "group0_mean": float(np.mean(y)),
                    "group1_mean": float(np.mean(x)),
                    "hedges_g": g,
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "welch_t": t,
                    "welch_p": p,
                    "permutation_p": perm_p,
                    "fdr_q": "",
                    "loo_min_effect": loo_low,
                    "loo_max_effect": loo_high,
                    "interpretation_flag": interpretation,
                    "notes": "Subject-level mean across sessions. Chronic TBI comparison kept separate and batch-sensitive.",
                }
            )
    return out


def aggregate_to_subject(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[float]] = defaultdict(list)
    meta: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        try:
            value = float(row.get("feature_value", ""))
        except Exception:
            continue
        if not math.isfinite(value):
            continue
        group = row.get("group_normalized", "")
        if group not in {"control", "mtbi", "chronic_tbi"}:
            continue
        key = (
            row.get("stable_person_id") or row.get("bids_subject", ""),
            group,
            row.get("artifact_branch", ""),
            row.get("condition", ""),
            row.get("region", ""),
            row.get("feature_name", ""),
        )
        grouped[key].append(value)
        meta[key] = row
    out = []
    for key, values in grouped.items():
        stable_person_id, group, artifact_branch, condition, region, feature_name = key
        ref = meta[key]
        out.append(
            {
                "stable_person_id": stable_person_id,
                "bids_subject": ref.get("bids_subject", ""),
                "group_normalized": group,
                "artifact_branch": artifact_branch,
                "condition": condition,
                "region": region,
                "feature_name": feature_name,
                "feature_value": float(np.mean(values)),
                "n_recording_rows": len(values),
            }
        )
    return out


def apply_fdr(rows: list[dict[str, Any]]) -> None:
    families: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        families[(row["analysis_family"], row["comparison"], row["artifact_branch"])].append(idx)
    for indices in families.values():
        q_values = benjamini_hochberg([rows[idx].get("welch_p") for idx in indices])
        for idx, q in zip(indices, q_values):
            rows[idx]["fdr_q"] = "" if not math.isfinite(q) else q


def artifact_sensitivity(model_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in model_rows:
        key = (
            row["analysis_family"],
            row["comparison"],
            row["condition"],
            row["region"],
            row["feature_name"],
        )
        by_key[key][row["artifact_branch"]] = row
    out = []
    for key, branches in by_key.items():
        all_row = branches.get("all_epochs")
        if not all_row:
            continue
        for artifact_branch, clean_row in sorted(branches.items()):
            if artifact_branch == "all_epochs":
                continue
            g_all = float_or_nan(all_row.get("hedges_g"))
            g_clean = float_or_nan(clean_row.get("hedges_g"))
            same_direction = math.isfinite(g_all) and math.isfinite(g_clean) and (g_all == 0 or g_clean == 0 or math.copysign(1, g_all) == math.copysign(1, g_clean))
            out.append(
                {
                    "analysis_family": key[0],
                    "comparison": key[1],
                    "condition": key[2],
                    "region": key[3],
                    "feature_name": key[4],
                    "artifact_branch_compared": artifact_branch,
                    "hedges_g_all_epochs": g_all,
                    "hedges_g_artifact_branch": g_clean,
                    "delta_artifact_minus_all": g_clean - g_all if math.isfinite(g_all) and math.isfinite(g_clean) else "",
                    "same_direction": same_direction,
                    "artifact_sensitivity_label": "direction_stable" if same_direction else "direction_changed_or_unavailable",
                }
            )
    return out


def float_or_nan(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else float("nan")
    except Exception:
        return float("nan")


def top_rows(rows: list[dict[str, Any]], comparison: str, artifact_branch: str, limit: int = 10) -> list[dict[str, Any]]:
    filtered = [row for row in rows if row.get("comparison") == comparison and row.get("artifact_branch") == artifact_branch]
    filtered = [row for row in filtered if math.isfinite(float_or_nan(row.get("hedges_g")))]
    return sorted(filtered, key=lambda row: abs(float(row["hedges_g"])), reverse=True)[:limit]


def preferred_artifact_branch(rows: list[dict[str, Any]]) -> str:
    counts = defaultdict(int)
    for row in rows:
        counts[row.get("artifact_branch", "")] += 1
    for branch in ["artifact_trim_ptp95", "artifact_clean_ptp250uv", "all_epochs"]:
        if counts.get(branch, 0):
            return branch
    return ""


def md_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows available._"
    columns = ["analysis_family", "comparison", "artifact_branch", "condition", "region", "feature_name", "n_group0", "n_group1", "hedges_g", "welch_p", "fdr_q", "permutation_p", "bootstrap_ci_low", "bootstrap_ci_high", "loo_min_effect", "loo_max_effect"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        values = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                value = f"{value:.6g}"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(dataset: str, d1_rows: list[dict[str, str]], d3_rows: list[dict[str, str]], model_rows: list[dict[str, Any]], sensitivity_rows: list[dict[str, Any]], warnings: list[str]) -> str:
    preferred_branch = preferred_artifact_branch(model_rows)
    strict_branch_rows = sum(1 for row in model_rows if row.get("artifact_branch") == "artifact_clean_ptp250uv")
    primary = top_rows(model_rows, "acute_mtbi_vs_control", preferred_branch)
    chronic = top_rows(model_rows, "chronic_tbi_vs_control", preferred_branch)
    direction_stable = sum(1 for row in sensitivity_rows if row.get("artifact_sensitivity_label") == "direction_stable")
    return f"""# D1/D3 Integrated Artifact-Control Report

Generated: 2026-06-12

## Scope

Dataset: `{dataset}`

The raw ds003522 EEG retrieval passed local verification before this report was generated. This report is exploratory, not diagnostic or clinically validated. It keeps acute mTBI vs control as the cleaner primary comparison and keeps chronic TBI separate because chronic status is potentially batch/session sensitive.

`ds003490` remains a Parkinson's/control comparator and is not used as TBI validation here. D2 cross-task convergence is not claimed.

## Available Rows

| Output | Rows |
| --- | ---: |
| D1 feature rows | {len(d1_rows)} |
| D3 eyes-closed alpha/IAF rows | {len(d3_rows)} |
| Group model rows | {len(model_rows)} |
| Artifact sensitivity rows | {len(sensitivity_rows)} |
| Direction-stable artifact sensitivity rows | {direction_stable} |
| Preferred artifact branch for top tables | {preferred_branch} |
| Strict 250 microvolt branch model rows | {strict_branch_rows} |

## Primary: Acute mTBI Vs Control

Rows below are the largest absolute Hedges g values for `{preferred_branch}` branch models after subject-level aggregation. Reported fields include Welch p, FDR q, permutation p, bootstrap CI, and leave-one-out effect range.

{md_table(primary)}

## Secondary: Chronic TBI Vs Control

Chronic TBI is kept separate and labeled secondary/batch-sensitive.

{md_table(chronic)}

## Artifact Sensitivity

Artifact sensitivity compares the Hedges g estimate from all epochs with each available non-all artifact branch. `artifact_clean_ptp250uv` is a strict fixed-threshold branch; `artifact_trim_ptp95` removes the highest-amplitude 5% of epochs within each recording-condition. Direction changes or unavailable estimates should be treated as fragile, not as confirmed effects.

## Warnings

{chr(10).join('- ' + warning for warning in warnings) if warnings else '- None'}

## Interpretation Guardrail

Effect sizes are exploratory and unadjusted for clinical covariates. FDR, permutation, bootstrap, leave-one-out, and artifact-sensitivity outputs are included to make fragility visible rather than to validate a biomarker.
"""


if __name__ == "__main__":
    main()
