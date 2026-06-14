from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy import stats

from scripts.utils.common import append_run_log, project_path


SCRIPT = "19_d1_d3_post_analysis_audit.py"


KEY_FEATURES = {
    "aperiodic_exponent": {
        "original_direction": "lower_in_tbi",
        "expected_sign": -1,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "aperiodic_offset": {
        "original_direction": "lower_in_tbi",
        "expected_sign": -1,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "spectral_entropy_1_45": {
        "original_direction": "higher_in_tbi",
        "expected_sign": 1,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "relative_delta_power": {
        "original_direction": "altered_direction_not_feature_specific",
        "expected_sign": 0,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "relative_alpha_power": {
        "original_direction": "altered_direction_not_feature_specific",
        "expected_sign": 0,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "theta_alpha_ratio": {
        "original_direction": "derived_from_theta_alpha_balance_not_feature_specific",
        "expected_sign": 0,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "alpha_theta_ratio": {
        "original_direction": "derived_from_theta_alpha_balance_not_feature_specific",
        "expected_sign": 0,
        "original_g": "acute_cluster_abs_g_0.80_to_0.96",
    },
    "iaf_peak_frequency": {
        "original_direction": "d3_secondary_no_prior_direction",
        "expected_sign": 0,
        "original_g": "not_reported",
    },
}

PRIOR_ANCHOR_NOTE = (
    "Original Phase 5 numeric per-feature rows were not available locally. "
    "The audit uses the execution-prompt anchor: acute mTBI vs control roughly abs(g)=0.80-0.96 "
    "with broad-screen FDR<0.10, chronic up to about abs(g)=1.11 with some FDR<0.05, "
    "centered on eyes-open temporal/frontal/global aperiodic/spectral features."
)


def main() -> None:
    model = read_csv("outputs/models/d1_d3_group_models.csv")
    sensitivity = read_csv("outputs/d1_artifact_control/ds003522_artifact_sensitivity.csv")
    qc = read_csv("outputs/qc/artifact_qc_metrics.csv")
    d1 = read_csv("outputs/features/d1_rest_features.csv")
    d3 = read_csv("outputs/features/d3_ec_alpha_iaf_features.csv")

    audit_checks = build_audit_checks(model, sensitivity, qc, d1, d3)
    family_audit = build_model_family_audit(model)
    key_trace = build_key_effect_trace(model, sensitivity)
    sample_counts = build_sample_counts(qc)

    out_qc = project_path("outputs/qc")
    out_qc.mkdir(parents=True, exist_ok=True)
    paths = {
        "checks": out_qc / "d1_d3_audit_checks.csv",
        "families": out_qc / "d1_d3_model_family_audit.csv",
        "trace": out_qc / "d1_d3_key_effect_trace.csv",
        "samples": out_qc / "d1_d3_artifact_branch_sample_counts.csv",
    }
    audit_checks.to_csv(paths["checks"], index=False)
    family_audit.to_csv(paths["families"], index=False)
    key_trace.to_csv(paths["trace"], index=False)
    sample_counts.to_csv(paths["samples"], index=False)

    reports = {
        "audit": project_path("reports/28_d1_d3_post_analysis_audit.md"),
        "decision": project_path("reports/29_next_step_decision_after_d1_d3.md"),
    }
    reports["audit"].write_text(
        build_audit_report(model, sensitivity, qc, d1, d3, audit_checks, family_audit, key_trace, sample_counts),
        encoding="utf-8",
        newline="\n",
    )
    reports["decision"].write_text(
        build_decision_report(model, audit_checks, family_audit),
        encoding="utf-8",
        newline="\n",
    )

    append_run_log(
        script=SCRIPT,
        status="completed",
        inputs=[
            "outputs/models/d1_d3_group_models.csv",
            "outputs/d1_artifact_control/ds003522_artifact_sensitivity.csv",
            "outputs/qc/artifact_qc_metrics.csv",
            "outputs/features/d1_rest_features.csv",
            "outputs/features/d3_ec_alpha_iaf_features.csv",
            "reports/24_d1_d3_integrated_artifact_control_report.md",
        ],
        outputs=[str(path) for path in [*paths.values(), *reports.values()]],
        parameters={
            "no_downloads_started": True,
            "d2_convergence_started": False,
            "prior_anchor_source": "C:/Users/gbp34/Downloads/D1_D2_D3_AI_execution_prompt.md",
        },
        warnings=[PRIOR_ANCHOR_NOTE],
    )

    print(json.dumps({key: str(value) for key, value in {**paths, **reports}.items()}, indent=2))


def read_csv(relative: str) -> pd.DataFrame:
    path = project_path(relative)
    if not path.exists() or path.stat().st_size <= 2:
        return pd.DataFrame()
    return pd.read_csv(path)


def build_key_effect_trace(model: pd.DataFrame, sensitivity: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    wanted_regions = ["global", "frontal", "temporal"]
    wanted_conditions = ["eyes_open", "eyes_closed"]
    wanted_branches = ["all_epochs", "artifact_trim_ptp95", "artifact_clean_ptp250uv"]
    sens_lookup = {}
    for _, row in sensitivity.iterrows():
        key = (
            row.get("analysis_family"),
            row.get("comparison"),
            row.get("condition"),
            row.get("region"),
            row.get("feature_name"),
            row.get("artifact_branch_compared"),
        )
        sens_lookup[key] = row

    for feature, meta in KEY_FEATURES.items():
        for condition in wanted_conditions:
            for region in wanted_regions:
                for branch in wanted_branches:
                    hit = model[
                        (model["analysis_family"] == "d1_rest_artifact_control")
                        & (model["comparison"] == "acute_mtbi_vs_control")
                        & (model["condition"] == condition)
                        & (model["region"] == region)
                        & (model["feature_name"] == feature)
                        & (model["artifact_branch"] == branch)
                    ]
                    if hit.empty:
                        rows.append(
                            {
                                "comparison": "acute_mtbi_vs_control",
                                "analysis_family": "d1_rest_artifact_control",
                                "condition": condition,
                                "region": region,
                                "feature_name": feature,
                                "branch": branch,
                                "branch_status": "not_modeled_or_unusable",
                                "original_effect_direction": meta["original_direction"],
                                "original_hedges_g": meta["original_g"],
                                "new_effect_direction": "",
                                "new_hedges_g": "",
                                "raw_p": "",
                                "fdr_q": "",
                                "n_total": "",
                                "direction_persisted": "",
                                "effect_attenuated_vs_original_anchor": "",
                                "fdr_failed": "",
                                "artifact_sensitivity_label": "",
                                "artifact_sensitivity_likely": branch == "artifact_clean_ptp250uv",
                                "notes": "Strict branch produced too few group-model rows." if branch == "artifact_clean_ptp250uv" else "",
                            }
                        )
                        continue
                    r = hit.iloc[0]
                    g = finite_float(r.get("hedges_g"))
                    expected = int(meta["expected_sign"])
                    direction_persisted = "" if expected == 0 or not math.isfinite(g) else sign(g) == expected
                    sens_key = (
                        r.get("analysis_family"),
                        r.get("comparison"),
                        r.get("condition"),
                        r.get("region"),
                        r.get("feature_name"),
                        branch,
                    )
                    sens = sens_lookup.get(sens_key)
                    sens_label = "" if sens is None else sens.get("artifact_sensitivity_label", "")
                    rows.append(
                        {
                            "comparison": r.get("comparison"),
                            "analysis_family": r.get("analysis_family"),
                            "condition": condition,
                            "region": region,
                            "feature_name": feature,
                            "branch": branch,
                            "branch_status": "modeled",
                            "original_effect_direction": meta["original_direction"],
                            "original_hedges_g": meta["original_g"],
                            "new_effect_direction": effect_direction(g),
                            "new_hedges_g": g,
                            "raw_p": finite_float(r.get("welch_p")),
                            "fdr_q": finite_float(r.get("fdr_q")),
                            "n_total": r.get("n_total"),
                            "direction_persisted": direction_persisted,
                            "effect_attenuated_vs_original_anchor": abs(g) < 0.80 if math.isfinite(g) and meta["original_g"].startswith("acute_cluster") else "",
                            "fdr_failed": finite_float(r.get("fdr_q")) >= 0.10,
                            "artifact_sensitivity_label": sens_label,
                            "artifact_sensitivity_likely": sens_label == "direction_changed_or_unavailable",
                            "notes": PRIOR_ANCHOR_NOTE,
                        }
                    )
    return pd.DataFrame(rows)


def build_model_family_audit(model: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, sub in model.groupby(["analysis_family", "comparison", "artifact_branch"], dropna=False):
        family, comparison, branch = key
        rows.append(
            {
                "family_name": f"actual_fdr_family::{family}::{comparison}::{branch}",
                "analysis_family": family,
                "comparison": comparison,
                "artifact_branch": branch,
                "scope_type": "actual_pipeline_fdr_family",
                "n_tests": len(sub),
                "n_conditions": sub["condition"].nunique(),
                "conditions": join_sorted(sub["condition"]),
                "n_regions": sub["region"].nunique(),
                "regions": join_sorted(sub["region"]),
                "n_features": sub["feature_name"].nunique(),
                "mixes_acute_and_chronic": False,
                "mixes_artifact_branches": False,
                "mixes_eo_ec": sub["condition"].nunique() > 1,
                "mixes_regions": sub["region"].nunique() > 1,
                "mixes_features": sub["feature_name"].nunique() > 1,
                "min_welch_p": min_finite(sub["welch_p"]),
                "min_pipeline_fdr_q": min_finite(sub["fdr_q"]),
                "min_recomputed_bh_q": min_bh(sub["welch_p"]),
                "interpretation": actual_family_interpretation(family, comparison, branch, len(sub)),
            }
        )

    definitions = [
        (
            "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal",
            "d1_rest_artifact_control",
            "acute_mtbi_vs_control",
            "artifact_trim_ptp95",
            {"eyes_open"},
            {"global", "frontal", "temporal"},
            {
                "aperiodic_exponent",
                "aperiodic_offset",
                "spectral_entropy_1_45",
                "relative_delta_power",
                "relative_alpha_power",
                "theta_alpha_ratio",
                "alpha_theta_ratio",
            },
        ),
        (
            "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal_all_epochs",
            "d1_rest_artifact_control",
            "acute_mtbi_vs_control",
            "all_epochs",
            {"eyes_open"},
            {"global", "frontal", "temporal"},
            {
                "aperiodic_exponent",
                "aperiodic_offset",
                "spectral_entropy_1_45",
                "relative_delta_power",
                "relative_alpha_power",
                "theta_alpha_ratio",
                "alpha_theta_ratio",
            },
        ),
        (
            "narrow_d3_posterior_alpha_iaf_trim",
            "d3_eyes_closed_alpha_iaf",
            "acute_mtbi_vs_control",
            "artifact_trim_ptp95",
            {"eyes_closed"},
            {"parietal", "occipital"},
            {
                "absolute_alpha_power",
                "relative_alpha_power",
                "theta_alpha_ratio",
                "alpha_theta_ratio",
                "iaf_peak_frequency",
                "alpha_peak_power",
            },
        ),
        (
            "d1_trim_no_temporal_frontal",
            "d1_rest_artifact_control",
            "acute_mtbi_vs_control",
            "artifact_trim_ptp95",
            {"eyes_open", "eyes_closed"},
            {"central", "parietal", "occipital"},
            set(KEY_FEATURES.keys()) - {"iaf_peak_frequency"},
        ),
    ]
    for name, family, comparison, branch, conditions, regions, features in definitions:
        sub = model[
            (model["analysis_family"] == family)
            & (model["comparison"] == comparison)
            & (model["artifact_branch"] == branch)
            & (model["condition"].isin(conditions))
            & (model["region"].isin(regions))
            & (model["feature_name"].isin(features))
        ].copy()
        rows.append(
            {
                "family_name": name,
                "analysis_family": family,
                "comparison": comparison,
                "artifact_branch": branch,
                "scope_type": "post_hoc_transparency_family_not_claim_rescue",
                "n_tests": len(sub),
                "n_conditions": sub["condition"].nunique() if not sub.empty else 0,
                "conditions": join_sorted(sub["condition"]) if not sub.empty else "",
                "n_regions": sub["region"].nunique() if not sub.empty else 0,
                "regions": join_sorted(sub["region"]) if not sub.empty else "",
                "n_features": sub["feature_name"].nunique() if not sub.empty else 0,
                "mixes_acute_and_chronic": False,
                "mixes_artifact_branches": False,
                "mixes_eo_ec": len(conditions) > 1,
                "mixes_regions": len(regions) > 1,
                "mixes_features": len(features) > 1,
                "min_welch_p": min_finite(sub["welch_p"]) if not sub.empty else "",
                "min_pipeline_fdr_q": min_finite(sub["fdr_q"]) if not sub.empty else "",
                "min_recomputed_bh_q": min_bh(sub["welch_p"]) if not sub.empty else "",
                "interpretation": "Exploratory narrower-family audit only; not a rescued confirmatory endpoint.",
            }
        )
    return pd.DataFrame(rows)


def build_sample_counts(qc: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    possible = (
        qc[qc["artifact_branch"] == "all_epochs"]
        .groupby(["group_normalized", "condition"], dropna=False)
        .size()
        .rename("possible_recording_conditions")
        .reset_index()
    )
    possible_lookup = {
        (row["group_normalized"], row["condition"]): int(row["possible_recording_conditions"])
        for _, row in possible.iterrows()
    }
    for key, sub in qc.groupby(["artifact_branch", "group_normalized", "condition"], dropna=False):
        branch, group, condition = key
        included = int(((sub["qc_status"] == "processed") & (pd.to_numeric(sub["n_epochs_used"], errors="coerce") > 0)).sum())
        possible_n = possible_lookup.get((group, condition), len(sub))
        excluded = max(0, possible_n - included)
        reasons = sub["qc_status"].value_counts(dropna=False).to_dict()
        rows.append(
            {
                "artifact_branch": branch,
                "group_normalized": group,
                "condition": condition,
                "possible_recording_conditions": possible_n,
                "included_recording_conditions": included,
                "excluded_recording_conditions": excluded,
                "included_subjects": sub.loc[sub["qc_status"] == "processed", "stable_person_id"].nunique(),
                "excluded_fraction": excluded / possible_n if possible_n else "",
                "median_usable_epoch_fraction": finite_median(sub["usable_epoch_fraction"]),
                "mean_usable_epoch_fraction": finite_mean(sub["usable_epoch_fraction"]),
                "median_ptp_uv": finite_median(sub["ptp_uv_median"]),
                "median_ptp_p95_uv": finite_median(sub["ptp_uv_p95"]),
                "exclusion_reasons": json.dumps(reasons, sort_keys=True),
                "interpretation": sample_count_interpretation(branch, excluded, possible_n),
            }
        )
    return pd.DataFrame(rows)


def build_audit_checks(model: pd.DataFrame, sensitivity: pd.DataFrame, qc: pd.DataFrame, d1: pd.DataFrame, d3: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    add = rows.append

    def subset_min_q(**filters: str) -> float:
        sub = model.copy()
        for key, value in filters.items():
            sub = sub[sub[key] == value]
        return min_finite(sub["fdr_q"]) if not sub.empty else float("nan")

    add(check_row("acute_trim_min_fdr", "fdr_audit", subset_min_q(comparison="acute_mtbi_vs_control", artifact_branch="artifact_trim_ptp95"), "Acute mTBI vs control did not survive broad FDR after artifact trim."))
    add(check_row("acute_all_epochs_min_fdr", "fdr_audit", subset_min_q(comparison="acute_mtbi_vs_control", artifact_branch="all_epochs"), "Untrimmed acute mTBI also did not survive broad FDR."))
    add(check_row("chronic_trim_min_fdr", "fdr_audit", subset_min_q(comparison="chronic_tbi_vs_control", artifact_branch="artifact_trim_ptp95"), "Chronic trim effects are still large in places but do not survive broad FDR."))
    add(check_row("chronic_all_epochs_min_fdr", "fdr_audit", subset_min_q(comparison="chronic_tbi_vs_control", artifact_branch="all_epochs"), "Chronic all-epochs branch has suggestive q<0.10 but is not the artifact-trimmed result."))

    strict_qc = qc[qc["artifact_branch"] == "artifact_clean_ptp250uv"]
    strict_included = int(((strict_qc["qc_status"] == "processed") & (pd.to_numeric(strict_qc["n_epochs_used"], errors="coerce") > 0)).sum())
    add(check_row("strict_branch_usability", "artifact_branch", strict_included, "Strict 250 microvolt branch retained only 4 recording-condition rows and produced 0 group model rows."))

    trim_qc = qc[qc["artifact_branch"] == "artifact_trim_ptp95"]
    trim_excluded = int((trim_qc["qc_status"] != "processed").sum())
    add(check_row("trim_branch_exclusions", "artifact_branch", trim_excluded, "The ptp95 trim branch retained all modeled recording-condition rows; it trims epochs, not subjects/recordings."))

    sens_changed = int((sensitivity["artifact_sensitivity_label"] == "direction_changed_or_unavailable").sum())
    add(check_row("artifact_sensitivity_direction_changes", "artifact_sensitivity", sens_changed, "Most modeled all-vs-trim comparisons kept direction, but direction changes/unavailable rows remain a fragility warning."))

    proxy_summary = artifact_proxy_summary(d1)
    for item in proxy_summary:
        add(item)

    cov_summary = covariate_attenuation_summary(d1, model)
    for item in cov_summary:
        add(item)

    regional_summary = region_exclusion_summary(model)
    for item in regional_summary:
        add(item)

    d3_summary = d3_evidence_summary(model)
    for item in d3_summary:
        add(item)

    add(check_row("project_classification", "decision", "artifact-sensitive candidate requiring caution", "Most conservative classification: acute D1 is coherent but non-FDR-surviving and artifact-sensitive; D3 does not rescue it."))
    add(check_row("d2_decision", "decision", "proceed_only_as_bounded_falsification", "D2 downloads are justified only as a falsification/reproducibility check of a fragile candidate, not as validation."))
    return pd.DataFrame(rows)


def artifact_proxy_summary(d1: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    proxy = dedup_proxy_rows(d1, branch="artifact_trim_ptp95")
    if proxy.empty:
        return [check_row("artifact_proxy_available", "artifact_proxy", False, "No proxy rows available.")]
    for condition in ["eyes_open", "eyes_closed"]:
        for region in ["global", "frontal", "temporal"]:
            sub = proxy[(proxy["condition"] == condition) & (proxy["region"] == region)]
            if sub.empty:
                continue
            for metric in ["emg_index_region", "line_noise_index_region"]:
                control = sub.loc[sub["group_normalized"] == "control", metric]
                mtbi = sub.loc[sub["group_normalized"] == "mtbi", metric]
                chronic = sub.loc[sub["group_normalized"] == "chronic_tbi", metric]
                for group_name, values in [("control", control), ("mtbi", mtbi), ("chronic_tbi", chronic)]:
                    out.append(
                        check_row(
                            f"proxy_{metric}_{condition}_{region}_{group_name}_mean",
                            "artifact_proxy_distribution",
                            finite_mean(values),
                            f"Mean {metric} for {group_name} in {condition} {region}.",
                        )
                    )
                out.append(
                    check_row(
                        f"proxy_{metric}_{condition}_{region}_acute_g",
                        "artifact_proxy",
                        hedges_g(mtbi, control),
                        "Positive means higher proxy in mTBI than control; large values would support artifact concern.",
                    )
                )
                out.append(
                    check_row(
                        f"proxy_{metric}_{condition}_{region}_chronic_g",
                        "artifact_proxy",
                        hedges_g(chronic, control),
                        "Positive means higher proxy in chronic TBI than control; large values would support artifact concern.",
                    )
                )
    return out


def covariate_attenuation_summary(d1: pd.DataFrame, model: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    candidates = model[
        (model["analysis_family"] == "d1_rest_artifact_control")
        & (model["comparison"] == "acute_mtbi_vs_control")
        & (model["artifact_branch"] == "artifact_trim_ptp95")
    ].copy()
    candidates["abs_g"] = pd.to_numeric(candidates["hedges_g"], errors="coerce").abs()
    candidates = candidates.sort_values("abs_g", ascending=False).head(12)
    attenuations = []
    for _, row in candidates.iterrows():
        sub = subject_feature_proxy(d1, row)
        if sub.empty or sub["group_indicator"].nunique() < 2:
            continue
        base = ols_group_coef(sub, covariates=[])
        adjusted = ols_group_coef(sub, covariates=["emg_index_region", "line_noise_index_region"])
        if math.isfinite(base) and math.isfinite(adjusted) and base != 0:
            attenuations.append(1 - abs(adjusted) / abs(base))
    out.append(
        check_row(
            "artifact_proxy_covariate_median_attenuation_top12",
            "artifact_proxy_covariate",
            finite_median(attenuations),
            "Approximate OLS group-coefficient attenuation after adding EMG and line-noise proxies for the top acute trim effects.",
        )
    )
    out.append(
        check_row(
            "artifact_proxy_covariate_n_models",
            "artifact_proxy_covariate",
            len(attenuations),
            "Number of top acute trim models where proxy-adjusted attenuation was estimable.",
        )
    )
    return out


def region_exclusion_summary(model: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sub = model[
        (model["analysis_family"] == "d1_rest_artifact_control")
        & (model["comparison"] == "acute_mtbi_vs_control")
        & (model["artifact_branch"] == "artifact_trim_ptp95")
    ].copy()
    for name, regions in {
        "temporal_frontal_global": {"temporal", "frontal", "global"},
        "central_parietal_occipital_only": {"central", "parietal", "occipital"},
        "eyes_open_only": set(sub.loc[sub["condition"] == "eyes_open", "region"].unique()),
        "eyes_closed_only": set(sub.loc[sub["condition"] == "eyes_closed", "region"].unique()),
    }.items():
        s = sub[sub["region"].isin(regions)]
        if name == "eyes_open_only":
            s = sub[sub["condition"] == "eyes_open"]
        if name == "eyes_closed_only":
            s = sub[sub["condition"] == "eyes_closed"]
        out.append(check_row(f"{name}_min_fdr_q", "regional_condition_sensitivity", min_finite(s["fdr_q"]), "Minimum FDR q in this sensitivity slice."))
        out.append(check_row(f"{name}_max_abs_g", "regional_condition_sensitivity", max_abs(s["hedges_g"]), "Largest absolute Hedges g in this sensitivity slice."))
    return out


def d3_evidence_summary(model: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    d3 = model[(model["analysis_family"] == "d3_eyes_closed_alpha_iaf") & (model["artifact_branch"] == "artifact_trim_ptp95")]
    for comparison in ["acute_mtbi_vs_control", "chronic_tbi_vs_control"]:
        sub = d3[d3["comparison"] == comparison]
        post = sub[sub["region"].isin(["parietal", "occipital"])]
        out.append(check_row(f"d3_{comparison}_all_regions_min_fdr_q", "d3_alpha_iaf", min_finite(sub["fdr_q"]), "D3 branch-wide minimum FDR q."))
        out.append(check_row(f"d3_{comparison}_posterior_min_fdr_q", "d3_alpha_iaf", min_finite(post["fdr_q"]), "Posterior parietal/occipital D3 minimum FDR q."))
        out.append(check_row(f"d3_{comparison}_posterior_max_abs_g", "d3_alpha_iaf", max_abs(post["hedges_g"]), "Posterior D3 strongest absolute effect size."))
    out.append(check_row("d3_aperiodic_adjusted_alpha_available", "d3_alpha_iaf", False, "No aperiodic-adjusted alpha peak metric is present in the D3 table."))
    return out


def build_audit_report(
    model: pd.DataFrame,
    sensitivity: pd.DataFrame,
    qc: pd.DataFrame,
    d1: pd.DataFrame,
    d3: pd.DataFrame,
    checks: pd.DataFrame,
    family: pd.DataFrame,
    trace: pd.DataFrame,
    samples: pd.DataFrame,
) -> str:
    acute_trim = model[(model["comparison"] == "acute_mtbi_vs_control") & (model["artifact_branch"] == "artifact_trim_ptp95")]
    chronic_trim = model[(model["comparison"] == "chronic_tbi_vs_control") & (model["artifact_branch"] == "artifact_trim_ptp95")]
    d3_trim = acute_trim[acute_trim["analysis_family"] == "d3_eyes_closed_alpha_iaf"]
    top_acute = top_rows(acute_trim, 8)
    top_chronic = top_rows(chronic_trim, 8)
    top_d3 = top_rows(d3_trim, 6)
    family_focus = family[
        family["family_name"].isin(
            [
                "actual_fdr_family::d1_rest_artifact_control::acute_mtbi_vs_control::artifact_trim_ptp95",
                "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal",
                "narrow_d3_posterior_alpha_iaf_trim",
                "d1_trim_no_temporal_frontal",
            ]
        )
    ]
    sample_focus = samples[samples["artifact_branch"].isin(["artifact_trim_ptp95", "artifact_clean_ptp250uv"])]
    direction_changed = int((sensitivity["artifact_sensitivity_label"] == "direction_changed_or_unavailable").sum())
    direction_stable = int((sensitivity["artifact_sensitivity_label"] == "direction_stable").sum())
    proxy_att = checks.loc[checks["check_id"] == "artifact_proxy_covariate_median_attenuation_top12", "value"].iloc[0]
    proxy_distribution = checks[
        (checks["category"] == "artifact_proxy_distribution")
        & (checks["check_id"].str.contains("eyes_open"))
        & (checks["check_id"].str.contains("global|frontal|temporal", regex=True))
    ].copy()
    proxy_group_diffs = checks[
        (checks["category"] == "artifact_proxy")
        & (checks["check_id"].str.contains("eyes_open"))
        & (checks["check_id"].str.contains("global|frontal|temporal", regex=True))
    ].copy()
    classification = checks.loc[checks["check_id"] == "project_classification", "value"].iloc[0]

    return f"""# D1/D3 Post-Analysis Audit

Generated: 2026-06-13

## Technical Summary

The D1/D3 analysis is best classified as **{classification}**. The acute mTBI vs control signal remains coherent enough to audit, but it does not survive the broad preplanned FDR families after artifact control. The strongest artifact-trimmed acute effects are mostly eyes-open spectral-balance or entropy-type effects, with minimum broad FDR q = {fmt(check_value(checks, "acute_trim_min_fdr"))}. This is not a biomarker result and not validation.

The prior Phase 5 lead signal did not numerically survive in its original reported magnitude. The only locally available original evidence is an execution-prompt anchor, not exact per-feature model rows: {PRIOR_ANCHOR_NOTE} Against that anchor, the new acute artifact-trimmed effects attenuate to absolute g values mostly below 0.65 and fail FDR.

Artifact control changes the interpretation. The strict 250 microvolt branch is unusable for group modeling because it retains too few recording-condition rows. The ptp95 branch keeps recording coverage but trims high-amplitude epochs. Artifact-sensitivity rows are mostly direction-stable ({direction_stable} stable, {direction_changed} changed/unavailable), yet the reliance on eyes-open frontal/temporal/global features keeps the candidate artifact-sensitive.

D3 eyes-closed alpha/IAF does not rescue the acute finding. The posterior D3 acute minimum FDR q is {fmt(check_value(checks, "d3_acute_mtbi_vs_control_posterior_min_fdr_q"))}, and no aperiodic-adjusted alpha peak metric is available in the generated D3 table. Chronic TBI effects remain larger in places, but chronic is secondary and batch-sensitive; after artifact trim its minimum broad q is {fmt(check_value(checks, "chronic_trim_min_fdr"))}.

## Original Lead Signal Vs Artifact-Controlled Results

The original Phase 5 signal is available only as a prose anchor, so the audit traces nearest-equivalent features rather than pretending exact original rows exist. The key pattern was eyes-open temporal/frontal/global aperiodic/spectral differences with acute mTBI absolute g around 0.80-0.96 and FDR below 0.10 in a broad screen.

{md_table(trace[(trace["branch"] == "artifact_trim_ptp95") & (trace["condition"] == "eyes_open") & (trace["region"].isin(["global", "frontal", "temporal"]))].head(14), ["feature_name", "region", "new_effect_direction", "new_hedges_g", "raw_p", "fdr_q", "direction_persisted", "effect_attenuated_vs_original_anchor", "artifact_sensitivity_label"])}

Interpretation: the nearest-equivalent acute rows are mostly attenuated relative to the reported original cluster. Some directions are coherent with the prior anchor, especially offset and entropy-like rows, but broad FDR failure and artifact sensitivity prevent a positive claim.

## Branch-By-Branch Result Summary

`all_epochs` and `artifact_trim_ptp95` both model acute mTBI vs control with n=70 subject-level observations for the main comparison. The strict fixed-threshold branch does not produce group model rows.

{md_table(sample_focus, ["artifact_branch", "group_normalized", "condition", "possible_recording_conditions", "included_recording_conditions", "excluded_recording_conditions", "median_usable_epoch_fraction", "exclusion_reasons"])}

The ptp95 branch is not a subject-exclusion branch; it removes the highest-amplitude epochs within recording-condition and keeps all modeled recording-condition rows. The strict branch is too conservative and would bias inference by leaving almost no usable data.

## FDR Family Audit

FDR was applied separately by analysis family, comparison, and artifact branch. Acute and chronic comparisons were not mixed, and artifact branches were not mixed. However, within each D1 family, eyes-open and eyes-closed, six regions, and 17 features are corrected together. That broad scope explains why the minimum acute trimmed q is high even when nominal p-values exist.

{md_table(family_focus, ["family_name", "scope_type", "n_tests", "conditions", "regions", "n_features", "min_welch_p", "min_pipeline_fdr_q", "min_recomputed_bh_q", "interpretation"])}

The q around 0.788 is not a single-row artifact: it is the minimum broad FDR q for the acute artifact-trimmed D1 family. A narrower prior-anchor family changes the q-value, but it remains an exploratory post hoc transparency calculation, not a rescued confirmatory endpoint.

## Artifact Proxy Audit

High-frequency proxy fields were available (`emg_index_region`, `line_noise_index_region`) and were summarized from the D1 feature rows. For the strongest acute trimmed effects, adding these proxies as covariates produced a median approximate group-coefficient attenuation of {fmt(proxy_att)} across estimable top models. This supports caution but is not a definitive artifact explanation.

Proxy distributions show that group differences are not one-sided across every region/metric, but eyes-open frontal/temporal/global proxies are still central enough to keep the lead D1 pattern artifact-sensitive.

{md_table(proxy_distribution, ["check_id", "value", "interpretation"], max_rows=18)}

Group-difference effect sizes for the same proxy rows:

{md_table(proxy_group_diffs, ["check_id", "value", "interpretation"], max_rows=12)}

Temporal/frontal/global effects remain the most visually coherent part of the acute candidate. When temporal/frontal regions are excluded, effect sizes remain present in some central/parietal/occipital rows, but broad FDR still fails.

{md_table(checks[checks["category"].isin(["artifact_proxy_covariate", "regional_condition_sensitivity"])], ["check_id", "value", "interpretation"])}

## Sample-Composition Audit

The strict branch changed sample composition severely because almost all recording-condition rows failed its fixed peak-to-peak threshold. The ptp95 branch did not exclude subjects or recording-condition rows; it changed epoch composition within each recording-condition. That makes ptp95 better suited for sensitivity than strict thresholding, but it remains an artifact-control sensitivity branch rather than a clean validation branch.

Full sample counts are saved to `outputs/qc/d1_d3_artifact_branch_sample_counts.csv`.

## D3 Alpha/IAF Audit

D3 is cleaner in the sense that it is eyes-closed and posterior regions can be inspected directly. It does not provide a strong supportive acute signal in the current outputs.

{md_table(top_d3, ["comparison", "artifact_branch", "region", "feature_name", "n_group0", "n_group1", "hedges_g", "welch_p", "fdr_q", "permutation_p"])}

For acute mTBI vs control, D3 supports at most a weak exploratory check. It does not become the lead. It also lacks aperiodic-adjusted alpha peak metrics in the generated D3 table, so any alpha interpretation should remain preliminary.

## Chronic TBI Interpretation

Chronic effects remain larger than acute effects in several eyes-open aperiodic/spectral rows, but they do not survive broad FDR after artifact trim and remain batch/recruitment sensitive.

{md_table(top_chronic, ["analysis_family", "comparison", "artifact_branch", "condition", "region", "feature_name", "n_group0", "n_group1", "hedges_g", "welch_p", "fdr_q", "permutation_p"])}

Chronic TBI can be discussed only as exploratory supporting context. It should not be combined with acute mTBI and should not be used as proof.

## Limitations And Robustness

- Original Phase 5 exact model rows were not present locally; the original comparison uses the documented prior-anchor prose, not feature-specific original estimates.
- The strict 250 microvolt branch is overconservative and unusable for group inference.
- The ptp95 branch preserves recording coverage but is still a sensitivity branch, not a gold-standard artifact correction.
- D1 features use log-log fallback aperiodic estimates rather than a full specparam/IRASA re-estimation branch for ds003522.
- No D2 convergence analysis has been started.
- `ds003490` remains comparator/pipeline rehearsal only and is not TBI validation.

## Recommended Next Step

Proceed to D2 downloads only if the next phase is explicitly framed as a bounded falsification/reproducibility check of a fragile D1 candidate. Do not proceed as if D1/D3 found a validated or robust biomarker. The current project value is a rigorous artifact-sensitivity/null-leaning report plus a transparent cross-task check.
"""


def build_decision_report(model: pd.DataFrame, checks: pd.DataFrame, family: pd.DataFrame) -> str:
    return f"""# Next-Step Decision After D1/D3

Generated: 2026-06-13

## Decision Summary

The project should **not** proceed as a positive D1/D3 biomarker story. The honest current classification is **{check_value(checks, "project_classification")}**.

## 1. Should We Proceed To ds005114/ds003523 D2 Downloads?

Yes, but only under a narrowed purpose: D2 should be a **cross-task falsification/reproducibility check of a fragile candidate**, not a validation phase. The rationale is that the acute D1 pattern is coherent enough to try to falsify across tasks, but not strong enough to claim.

Do not download D2 data until this bounded D2 scope is accepted:

- test a small, prespecified feature family derived from the D1 audit
- preserve subject-level overlap controls
- treat failure to reproduce as an informative null
- do not use D2 to chase nominal p-values

## 2. Should D1 Remain The Lead?

D1 can remain the lead only as an **artifact-sensitive exploratory candidate**. It should not be the lead as a robust positive result. The acute artifact-trimmed broad FDR minimum is {fmt(check_value(checks, "acute_trim_min_fdr"))}, so D1 cannot carry a positive manuscript claim alone.

## 3. Should D3 Become The Lead?

No. D3 is cleaner and useful as a control/sensitivity domain, but the generated posterior alpha/IAF rows do not show a strong acute FDR-surviving signal. D3 should remain a secondary check.

## 4. Should The Project Pivot To An Artifact-Sensitivity/Null Report?

Yes, unless D2 later provides coherent cross-task support. The most defensible current story is a transparent artifact-control audit showing that the prior acute signal attenuates and fails broad FDR after stricter handling.

## 5. What Analyses Are Worth Doing Next?

Worth doing next:

1. Download and verify `ds005114` and `ds003523` only for a bounded D2 falsification check.
2. Prespecify the D2 feature family from D1 before downloading: eyes-open/global-frontal-temporal aperiodic offset/exponent, spectral entropy, relative delta/alpha, theta-alpha balance, plus a posterior eyes-closed alpha/IAF check.
3. Add a ds003522 specparam/IRASA sensitivity branch only if runtime is acceptable and it is framed as method sensitivity, not rescue.
4. Produce a subject-overlap-safe D2 table with stable person IDs and no file/session leakage.

## 6. What Should Be Avoided?

- Do not claim a biomarker.
- Do not claim validation.
- Do not use chronic TBI as proof.
- Do not merge chronic with acute mTBI.
- Do not treat `ds003490` as TBI validation.
- Do not redefine the FDR family post hoc to rescue significance.
- Do not start broad D2 feature mining without a prespecified falsification scope.

## 7. Revised Publishability Assessment

Current publishability is **not positive-result ready**. It may become publishable as one of two narrower products:

1. a rigorous null/artifact-sensitivity technical report showing why an initially plausible public EEG signal does not survive artifact-aware scrutiny; or
2. a cautious cross-task reproducibility paper only if D2 shows coherent support under the prespecified bounded family.

The current D1/D3 package alone supports feasibility, reproducibility, and methodological caution more than it supports a scientific disease signal.
"""


def top_rows(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["abs_g"] = pd.to_numeric(out["hedges_g"], errors="coerce").abs()
    return out.sort_values("abs_g", ascending=False).head(n).drop(columns=["abs_g"])


def dedup_proxy_rows(d1: pd.DataFrame, branch: str) -> pd.DataFrame:
    cols = [
        "relative_path",
        "stable_person_id",
        "group_normalized",
        "condition",
        "artifact_branch",
        "region",
        "emg_index_region",
        "line_noise_index_region",
    ]
    keep = d1[(d1["artifact_branch"] == branch)][cols].drop_duplicates()
    for col in ["emg_index_region", "line_noise_index_region"]:
        keep[col] = pd.to_numeric(keep[col], errors="coerce")
    return keep


def subject_feature_proxy(d1: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    sub = d1[
        (d1["artifact_branch"] == row["artifact_branch"])
        & (d1["condition"] == row["condition"])
        & (d1["region"] == row["region"])
        & (d1["feature_name"] == row["feature_name"])
        & (d1["group_normalized"].isin(["control", "mtbi"]))
    ].copy()
    if sub.empty:
        return pd.DataFrame()
    for col in ["feature_value", "emg_index_region", "line_noise_index_region"]:
        sub[col] = pd.to_numeric(sub[col], errors="coerce")
    agg = (
        sub.groupby(["stable_person_id", "group_normalized"], dropna=False)[
            ["feature_value", "emg_index_region", "line_noise_index_region"]
        ]
        .mean()
        .reset_index()
        .dropna()
    )
    agg["group_indicator"] = (agg["group_normalized"] == "mtbi").astype(float)
    return agg


def ols_group_coef(df: pd.DataFrame, covariates: list[str]) -> float:
    try:
        y = df["feature_value"].to_numpy(dtype=float)
        x_cols = [np.ones(len(df)), df["group_indicator"].to_numpy(dtype=float)]
        for cov in covariates:
            z = df[cov].to_numpy(dtype=float)
            z = (z - np.nanmean(z)) / np.nanstd(z) if np.nanstd(z) > 0 else z * 0
            x_cols.append(z)
        x = np.column_stack(x_cols)
        coef = np.linalg.lstsq(x, y, rcond=None)[0]
        return float(coef[1])
    except Exception:
        return float("nan")


def check_row(check_id: str, category: str, value: Any, interpretation: str) -> dict[str, Any]:
    return {"check_id": check_id, "category": category, "value": value, "interpretation": interpretation}


def check_value(checks: pd.DataFrame, check_id: str) -> Any:
    hit = checks.loc[checks["check_id"] == check_id, "value"]
    return "" if hit.empty else hit.iloc[0]


def actual_family_interpretation(family: str, comparison: str, branch: str, n_tests: int) -> str:
    bits = [f"{n_tests} tests corrected together"]
    if family == "d1_rest_artifact_control":
        bits.append("D1 combines EO/EC, six regions, and all D1 features within this comparison/branch")
    if family == "d3_eyes_closed_alpha_iaf":
        bits.append("D3 family is narrower but still combines regions/features")
    bits.append("acute/chronic and artifact branches are separate")
    return "; ".join(bits)


def sample_count_interpretation(branch: str, excluded: int, possible_n: int) -> str:
    if branch == "artifact_clean_ptp250uv":
        return "Strict fixed threshold is overconservative; too few rows remain for group inference."
    if branch == "artifact_trim_ptp95":
        return "Within-recording epoch trimming retains recording-condition coverage."
    return "Reference all-epochs branch."


def finite_float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else float("nan")
    except Exception:
        return float("nan")


def clean(values: Iterable[Any]) -> np.ndarray:
    arr = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna().to_numpy(dtype=float)
    return arr[np.isfinite(arr)]


def hedges_g(x: Iterable[Any], y: Iterable[Any]) -> float:
    a = clean(x)
    b = clean(y)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled = ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1)) / (len(a) + len(b) - 2)
    if pooled <= 0:
        return float("nan")
    d = (np.mean(a) - np.mean(b)) / math.sqrt(pooled)
    correction = 1 - (3 / (4 * (len(a) + len(b)) - 9))
    return float(d * correction)


def min_finite(values: Iterable[Any]) -> float:
    arr = clean(values)
    return float(np.min(arr)) if len(arr) else float("nan")


def max_abs(values: Iterable[Any]) -> float:
    arr = clean(values)
    return float(np.max(np.abs(arr))) if len(arr) else float("nan")


def finite_median(values: Iterable[Any]) -> float:
    arr = clean(values)
    return float(np.median(arr)) if len(arr) else float("nan")


def finite_mean(values: Iterable[Any]) -> float:
    arr = clean(values)
    return float(np.mean(arr)) if len(arr) else float("nan")


def bh_q(p_values: Iterable[Any]) -> np.ndarray:
    p = clean(p_values)
    if len(p) == 0:
        return np.asarray([])
    order = np.argsort(p)
    ranked = p[order]
    q_sorted = np.empty(len(ranked), dtype=float)
    running = 1.0
    m = len(ranked)
    for i in range(m - 1, -1, -1):
        rank = i + 1
        running = min(running, ranked[i] * m / rank)
        q_sorted[i] = min(running, 1.0)
    q = np.empty(len(ranked), dtype=float)
    q[order] = q_sorted
    return q


def min_bh(p_values: Iterable[Any]) -> float:
    q = bh_q(p_values)
    return float(np.min(q)) if len(q) else float("nan")


def sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def effect_direction(value: float) -> str:
    if not math.isfinite(value):
        return ""
    return "higher_in_group1_tbi" if value > 0 else "lower_in_group1_tbi" if value < 0 else "zero"


def join_sorted(values: Iterable[Any]) -> str:
    return ";".join(sorted(str(v) for v in set(values) if str(v) != "nan"))


def fmt(value: Any) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    try:
        f = float(value)
        if not math.isfinite(f):
            return "NA"
        if abs(f) >= 100:
            return f"{f:.1f}"
        if abs(f) >= 1:
            return f"{f:.3f}"
        return f"{f:.4g}"
    except Exception:
        return str(value)


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int = 14) -> str:
    if df.empty:
        return "_No rows available._"
    use = df.loc[:, [col for col in columns if col in df.columns]].head(max_rows).copy()
    for col in use.columns:
        use[col] = use[col].map(fmt)
    widths = {col: max(len(str(col)), *(len(str(v)) for v in use[col].tolist())) for col in use.columns}
    header = "| " + " | ".join(str(col).ljust(widths[col]) for col in use.columns) + " |"
    sep = "| " + " | ".join("-" * widths[col] for col in use.columns) + " |"
    lines = [header, sep]
    for _, row in use.iterrows():
        lines.append("| " + " | ".join(str(row[col]).ljust(widths[col]) for col in use.columns) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
