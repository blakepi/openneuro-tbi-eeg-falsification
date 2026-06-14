from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy import stats

from scripts.utils.common import project_path, read_rows_csv, script_finish, script_start, write_rows_csv
from scripts.utils.stats_utils import benjamini_hochberg, bootstrap_ci_effect, hedges_g, permutation_p_mean_diff, welch_t_test


SCRIPT = "22_run_d2_falsification_models.py"
PRIMARY_FEATURES = [
    "aperiodic_exponent",
    "aperiodic_offset",
    "spectral_entropy",
    "relative_delta_power",
    "relative_alpha_power",
    "theta_alpha_ratio",
    "alpha_theta_ratio",
    "individual_alpha_frequency",
]
PRIMARY_REGIONS = ["global", "frontal", "central", "parietal", "occipital", "temporal"]
D2_DATASETS = ["ds005114", "ds003523"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded D2 falsification/reproducibility models.")
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--permutation-iterations", type=int, default=2000)
    parser.add_argument("--allow-final-d2", action="store_true", help="Explicitly allow full D2 modeling after ds003523 is unlocked and verified.")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings: list[str] = []
    errors: list[str] = []

    if not args.allow_final_d2:
        errors.append("Refusing full D2 modeling without --allow-final-d2.")
        script_finish(SCRIPT, start, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    ready, reason = full_d2_verification_ready()
    if not ready:
        errors.append(f"Refusing full D2 modeling: {reason}")
        script_finish(SCRIPT, start, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(1)

    try:
        d2 = load_d2_features()
        d1_features = load_d1_subject_features()
        d1_effects = load_d1_reference_effects()
    except RuntimeError as exc:
        errors.append(str(exc))
        script_finish(SCRIPT, start, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(str(exc))

    subject_d2 = aggregate_d2_subject_features(d2)
    within_rows = within_dataset_group_effects(subject_d2, args.bootstrap_iterations, args.permutation_iterations)
    add_fdr(within_rows)
    direction_rows = direction_consistency(within_rows, d1_effects)
    stability_rows = within_subject_stability(d1_features, subject_d2)
    mixed_rows, mixed_warnings = mixed_effects_models(d1_features, subject_d2)
    warnings.extend(mixed_warnings)
    summary_rows = falsification_summary(within_rows, direction_rows, stability_rows, mixed_rows)

    out_dir = project_path("outputs/d2_cross_task")
    outputs = {
        "within": out_dir / "d2_within_dataset_group_effects.csv",
        "direction": out_dir / "d2_direction_consistency.csv",
        "stability": out_dir / "d2_within_subject_stability.csv",
        "mixed": out_dir / "d2_mixed_effects_models.csv",
        "summary": out_dir / "d2_falsification_summary.csv",
    }
    write_rows_csv(outputs["within"], within_rows)
    write_rows_csv(outputs["direction"], direction_rows)
    write_rows_csv(outputs["stability"], stability_rows)
    write_rows_csv(outputs["mixed"], mixed_rows)
    write_rows_csv(outputs["summary"], summary_rows)
    script_finish(SCRIPT, start, outputs=[str(path) for path in outputs.values()], warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
    if errors:
        raise SystemExit(1)


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


def require_original_id(df: pd.DataFrame, label: str) -> None:
    if "Original_ID" not in df.columns and "stable_person_id" in df.columns:
        df["Original_ID"] = df["stable_person_id"]
    if "Original_ID" not in df.columns:
        raise RuntimeError(f"{label} is missing Original_ID.")
    if df["Original_ID"].fillna("").astype(str).str.strip().eq("").any():
        raise RuntimeError(f"{label} contains blank Original_ID values.")


def load_d2_features() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for dataset_id in D2_DATASETS:
        path = project_path("outputs/d2_cross_task", f"{dataset_id}_harmonized_features.csv")
        if not path.exists():
            raise RuntimeError(f"Missing D2 feature table: {path}")
        rows.extend(read_rows_csv(path))
    if not rows:
        raise RuntimeError("D2 feature tables are empty.")
    df = pd.DataFrame(rows)
    require_original_id(df, "D2 feature table")
    df = df[df["feature_name"].isin(PRIMARY_FEATURES)].copy()
    df = df[df["region"].isin(PRIMARY_REGIONS)].copy()
    df["feature_value"] = pd.to_numeric(df["feature_value"], errors="coerce")
    df["age"] = pd.to_numeric(df.get("age", ""), errors="coerce")
    df["emg_index_region"] = pd.to_numeric(df.get("emg_index_region", ""), errors="coerce")
    df["line_noise_index_region"] = pd.to_numeric(df.get("line_noise_index_region", ""), errors="coerce")
    df = df[np.isfinite(df["feature_value"])]
    df = df[df["group_normalized"].isin(["control", "mtbi"])]
    return df


def load_d1_subject_features() -> pd.DataFrame:
    path = project_path("outputs/features/d1_rest_features.csv")
    if not path.exists():
        raise RuntimeError(f"Missing D1 feature table: {path}")
    df = pd.DataFrame(read_rows_csv(path))
    require_original_id(df, "D1 feature table")
    df = df[
        (df.get("artifact_branch", "") == "artifact_trim_ptp95")
        & (df.get("condition", "") == "eyes_open")
        & (df.get("feature_name", "").isin(PRIMARY_FEATURES))
        & (df.get("region", "").isin(PRIMARY_REGIONS))
        & (df.get("group_normalized", "").isin(["control", "mtbi"]))
    ].copy()
    if df.empty:
        raise RuntimeError("No D1 artifact-trimmed eyes-open primary feature rows available.")
    df["feature_value"] = pd.to_numeric(df["feature_value"], errors="coerce")
    df["emg_index_region"] = pd.to_numeric(df.get("emg_index_region", ""), errors="coerce")
    df = df[np.isfinite(df["feature_value"])]
    grouped = (
        df.groupby(["Original_ID", "group_normalized", "region", "feature_name"], dropna=False)
        .agg(feature_value=("feature_value", "mean"), emg_index_region=("emg_index_region", "mean"))
        .reset_index()
    )
    grouped["dataset_id"] = "ds003522"
    grouped["task_label"] = "ds003522_eyes_open_rest"
    return grouped


def load_d1_reference_effects() -> dict[tuple[str, str], dict[str, Any]]:
    path = project_path("outputs/models/d1_d3_group_models.csv")
    rows = [
        row
        for row in read_rows_csv(path)
        if row.get("analysis_family") == "d1_rest_artifact_control"
        and row.get("comparison") == "acute_mtbi_vs_control"
        and row.get("artifact_branch") == "artifact_trim_ptp95"
        and row.get("feature_name") in PRIMARY_FEATURES
        and row.get("region") in PRIMARY_REGIONS
    ]
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_key[(row.get("region", ""), row.get("feature_name", ""))].append(row)
    selected = {}
    for key, candidates in by_key.items():
        eyes_open = [row for row in candidates if row.get("condition") == "eyes_open"]
        pool = eyes_open or candidates
        selected[key] = max(pool, key=lambda row: abs(safe_float(row.get("hedges_g")) or 0.0))
    return selected


def aggregate_d2_subject_features(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "dataset_id",
        "Original_ID",
        "group_normalized",
        "task",
        "task_window",
        "condition",
        "region",
        "feature_name",
    ]
    agg = (
        df.groupby(group_cols, dropna=False)
        .agg(
            feature_value=("feature_value", "mean"),
            n_recording_rows=("feature_value", "size"),
            age=("age", "mean"),
            emg_index_region=("emg_index_region", "mean"),
            line_noise_index_region=("line_noise_index_region", "mean"),
        )
        .reset_index()
    )
    return agg


def within_dataset_group_effects(df: pd.DataFrame, bootstrap_iterations: int, permutation_iterations: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group_cols = ["dataset_id", "task", "task_window", "condition", "region", "feature_name"]
    for key, sub in df.groupby(group_cols, dropna=False):
        controls = sub[sub["group_normalized"] == "control"]["feature_value"].dropna().to_numpy(dtype=float)
        mtbi = sub[sub["group_normalized"] == "mtbi"]["feature_value"].dropna().to_numpy(dtype=float)
        if len(controls) < 3 or len(mtbi) < 3:
            continue
        t_stat, p_value = welch_t_test(mtbi, controls)
        g = hedges_g(mtbi, controls)
        ci_low, ci_high = bootstrap_ci_effect(mtbi, controls, iterations=bootstrap_iterations)
        perm_p = permutation_p_mean_diff(mtbi, controls, iterations=permutation_iterations)
        rows.append(
            {
                "analysis_family": "d2_locked_prior_anchor",
                "comparison": "acute_mtbi_vs_control",
                "dataset_id": key[0],
                "task": key[1],
                "task_window": key[2],
                "condition": key[3],
                "region": key[4],
                "feature_name": key[5],
                "n_total": len(controls) + len(mtbi),
                "n_group0": len(controls),
                "n_group1": len(mtbi),
                "group0_label": "control",
                "group1_label": "mtbi",
                "group0_mean": float(np.mean(controls)),
                "group1_mean": float(np.mean(mtbi)),
                "hedges_g": g,
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "welch_t": t_stat,
                "welch_p": p_value,
                "permutation_p": perm_p,
                "fdr_family": f"d2_locked_prior_anchor::{key[0]}::{key[2]}",
                "fdr_q": "",
                "notes": "Subject-level mean across recordings/sessions by Original_ID.",
            }
        )
    return rows


def add_fdr(rows: list[dict[str, Any]]) -> None:
    by_family: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        by_family[str(row["fdr_family"])].append(idx)
    for indices in by_family.values():
        q_values = benjamini_hochberg([rows[idx]["welch_p"] for idx in indices])
        for idx, q in zip(indices, q_values):
            rows[idx]["fdr_q"] = q


def direction_consistency(within_rows: list[dict[str, Any]], d1_effects: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in within_rows:
        ref = d1_effects.get((row["region"], row["feature_name"]), {})
        d1_g = safe_float(ref.get("hedges_g"))
        d2_g = safe_float(row.get("hedges_g"))
        if d1_g is None or d2_g is None or d1_g == 0 or d2_g == 0:
            match = ""
        else:
            match = bool(np.sign(d1_g) == np.sign(d2_g))
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "task": row["task"],
                "task_window": row["task_window"],
                "condition": row["condition"],
                "region": row["region"],
                "feature_name": row["feature_name"],
                "d1_reference_condition": ref.get("condition", ""),
                "d1_hedges_g": d1_g if d1_g is not None else "",
                "d1_fdr_q": ref.get("fdr_q", ""),
                "d2_hedges_g": d2_g if d2_g is not None else "",
                "d2_fdr_q": row.get("fdr_q", ""),
                "direction_match": match,
                "d2_effect_abs_ge_0p2": abs(d2_g) >= 0.2 if d2_g is not None else "",
                "notes": "Direction only; this is not validation and does not override D1 artifact sensitivity.",
            }
        )
    return rows


def within_subject_stability(d1: pd.DataFrame, d2: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    d2_task_average = d2[d2["task_window"] == "task_average_4s"].copy()
    d2_task_average["task_label"] = d2_task_average["dataset_id"] + "_task_average"
    d2_agg = (
        d2_task_average.groupby(["Original_ID", "task_label", "region", "feature_name"], dropna=False)["feature_value"]
        .mean()
        .reset_index()
    )
    d1_values = d1[["Original_ID", "task_label", "region", "feature_name", "feature_value"]].copy()
    combined = pd.concat([d1_values, d2_agg], ignore_index=True)
    task_pairs = [
        ("ds003522_eyes_open_rest", "ds005114_task_average"),
        ("ds003522_eyes_open_rest", "ds003523_task_average"),
        ("ds005114_task_average", "ds003523_task_average"),
    ]
    for feature in PRIMARY_FEATURES:
        for region in PRIMARY_REGIONS:
            sub = combined[(combined["feature_name"] == feature) & (combined["region"] == region)]
            wide = sub.pivot_table(index="Original_ID", columns="task_label", values="feature_value", aggfunc="mean")
            for a, b in task_pairs:
                if a not in wide or b not in wide:
                    continue
                paired = wide[[a, b]].dropna()
                if len(paired) < 5:
                    continue
                rho, p_value = stats.spearmanr(paired[a], paired[b], nan_policy="omit")
                rows.append(
                    {
                        "feature_name": feature,
                        "region": region,
                        "task_a": a,
                        "task_b": b,
                        "n_subjects": len(paired),
                        "spearman_rho": float(rho),
                        "spearman_p": float(p_value),
                        "notes": "Subject-level rank-order stability by Original_ID.",
                    }
                )
    q_values = benjamini_hochberg([row["spearman_p"] for row in rows])
    for row, q in zip(rows, q_values):
        row["spearman_fdr_q"] = q
    return rows


def mixed_effects_models(d1: pd.DataFrame, d2: pd.DataFrame) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    d1_model = d1.rename(columns={"feature_value": "value"}).copy()
    d1_model["task_label"] = "ds003522"
    d2_task = d2[d2["task_window"] == "task_average_4s"].copy()
    d2_model = d2_task.rename(columns={"feature_value": "value"}).copy()
    d2_model["task_label"] = d2_model["dataset_id"]
    keep_cols = ["Original_ID", "group_normalized", "task_label", "region", "feature_name", "value", "emg_index_region"]
    combined = pd.concat([d1_model[keep_cols], d2_model[keep_cols]], ignore_index=True)
    combined = combined[combined["group_normalized"].isin(["control", "mtbi"])].copy()
    combined["group_binary"] = (combined["group_normalized"] == "mtbi").astype(float)
    for feature in PRIMARY_FEATURES:
        for region in PRIMARY_REGIONS:
            sub = combined[(combined["feature_name"] == feature) & (combined["region"] == region)].copy()
            sub = sub[np.isfinite(pd.to_numeric(sub["value"], errors="coerce"))].copy()
            sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
            if sub["Original_ID"].nunique() < 10 or sub["task_label"].nunique() < 2:
                continue
            result_row = {
                "feature_name": feature,
                "region": region,
                "n_rows": len(sub),
                "n_subjects": sub["Original_ID"].nunique(),
                "tasks": ";".join(sorted(sub["task_label"].unique())),
                "model_formula": "value ~ group_binary * C(task_label) + (1 | Original_ID)",
                "model_status": "",
                "group_beta_reference_task": "",
                "group_p_reference_task": "",
                "max_abs_group_task_interaction_beta": "",
                "min_group_task_interaction_p": "",
                "covariates_included": "none; age/artifact covariate completeness differs across D1/D2 tables",
                "notes": "",
            }
            try:
                import statsmodels.formula.api as smf

                model = smf.mixedlm("value ~ group_binary * C(task_label)", data=sub, groups=sub["Original_ID"])
                fit = model.fit(reml=False, method="lbfgs", maxiter=200, disp=False)
                params = fit.params
                pvalues = fit.pvalues
                interactions = [name for name in params.index if "group_binary:C(task_label)" in name]
                result_row.update(
                    {
                        "model_status": "mixedlm_completed",
                        "group_beta_reference_task": float(params.get("group_binary", np.nan)),
                        "group_p_reference_task": float(pvalues.get("group_binary", np.nan)),
                        "max_abs_group_task_interaction_beta": float(max([abs(params[name]) for name in interactions], default=np.nan)),
                        "min_group_task_interaction_p": float(min([pvalues[name] for name in interactions], default=np.nan)),
                    }
                )
            except Exception as exc:
                warnings.append(f"MixedLM fallback for {feature}/{region}: {type(exc).__name__}: {exc}")
                try:
                    import statsmodels.formula.api as smf

                    ols = smf.ols("value ~ group_binary * C(task_label)", data=sub).fit(
                        cov_type="cluster", cov_kwds={"groups": sub["Original_ID"]}
                    )
                    params = ols.params
                    pvalues = ols.pvalues
                    interactions = [name for name in params.index if "group_binary:C(task_label)" in name]
                    result_row.update(
                        {
                            "model_status": "clustered_ols_fallback",
                            "group_beta_reference_task": float(params.get("group_binary", np.nan)),
                            "group_p_reference_task": float(pvalues.get("group_binary", np.nan)),
                            "max_abs_group_task_interaction_beta": float(max([abs(params[name]) for name in interactions], default=np.nan)),
                            "min_group_task_interaction_p": float(min([pvalues[name] for name in interactions], default=np.nan)),
                            "notes": f"MixedLM failed; clustered OLS fallback used: {type(exc).__name__}.",
                        }
                    )
                except Exception as fallback_exc:
                    result_row.update({"model_status": "failed", "notes": f"{type(exc).__name__}: {exc}; fallback {type(fallback_exc).__name__}: {fallback_exc}"})
            rows.append(result_row)
    q_values = benjamini_hochberg([row.get("group_p_reference_task") for row in rows])
    for row, q in zip(rows, q_values):
        row["group_reference_task_fdr_q"] = q
    return rows, warnings


def falsification_summary(
    within_rows: list[dict[str, Any]],
    direction_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    mixed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for dataset_id in D2_DATASETS:
        task_avg = [row for row in within_rows if row["dataset_id"] == dataset_id and row["task_window"] == "task_average_4s"]
        dir_rows = [row for row in direction_rows if row["dataset_id"] == dataset_id and row["task_window"] == "task_average_4s"]
        match_values = [row for row in dir_rows if isinstance(row.get("direction_match"), bool)]
        min_q = min([safe_float(row.get("fdr_q")) for row in task_avg if safe_float(row.get("fdr_q")) is not None], default=float("nan"))
        max_abs_g = max([abs(safe_float(row.get("hedges_g")) or 0.0) for row in task_avg], default=float("nan"))
        match_rate = sum(1 for row in match_values if row["direction_match"]) / len(match_values) if match_values else float("nan")
        summary.append(
            {
                "summary_level": "dataset_task_average",
                "dataset_id": dataset_id,
                "n_group_effect_rows": len(task_avg),
                "min_fdr_q": min_q,
                "max_abs_hedges_g": max_abs_g,
                "direction_match_rate_vs_d1": match_rate,
                "interpretation": classify_dataset(min_q, match_rate, max_abs_g),
            }
        )
    stability_sig = [row for row in stability_rows if (safe_float(row.get("spearman_fdr_q")) or 1.0) < 0.10]
    mixed_sig = [row for row in mixed_rows if (safe_float(row.get("group_reference_task_fdr_q")) or 1.0) < 0.10]
    overall = classify_overall(summary, stability_sig, mixed_sig)
    summary.append(
        {
            "summary_level": "overall_d2",
            "dataset_id": "ds005114+ds003523",
            "n_group_effect_rows": len(within_rows),
            "min_fdr_q": min([safe_float(row.get("fdr_q")) for row in within_rows if safe_float(row.get("fdr_q")) is not None], default=float("nan")),
            "max_abs_hedges_g": max([abs(safe_float(row.get("hedges_g")) or 0.0) for row in within_rows], default=float("nan")),
            "direction_match_rate_vs_d1": "",
            "n_stability_q_lt_0p10": len(stability_sig),
            "n_mixed_group_q_lt_0p10": len(mixed_sig),
            "interpretation": overall,
        }
    )
    return summary


def classify_dataset(min_q: float, match_rate: float, max_abs_g: float) -> str:
    if math.isfinite(min_q) and min_q < 0.10 and math.isfinite(match_rate) and match_rate >= 0.60:
        return "partial/inconsistent cross-task support"
    if math.isfinite(match_rate) and match_rate >= 0.60 and max_abs_g >= 0.30:
        return "directional but non-FDR-supportive"
    if math.isfinite(match_rate) and match_rate < 0.50:
        return "no cross-task support"
    return "inconclusive or weak cross-task trace"


def classify_overall(dataset_summary: list[dict[str, Any]], stability_sig: list[dict[str, Any]], mixed_sig: list[dict[str, Any]]) -> str:
    interpretations = " ".join(str(row.get("interpretation", "")) for row in dataset_summary)
    if "partial/inconsistent" in interpretations and stability_sig:
        return "partial/inconsistent cross-task support"
    if all("no cross-task support" in str(row.get("interpretation", "")) for row in dataset_summary):
        return "no cross-task support"
    if not stability_sig and not mixed_sig:
        return "evidence favors weak or context-specific signal"
    return "partial/inconsistent cross-task support"


def safe_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


if __name__ == "__main__":
    main()
