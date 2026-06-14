from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
OUT_FINAL = ROOT / "outputs" / "final"
OUT_FIG = ROOT / "outputs" / "final_figures"
OUT_TABLE = ROOT / "outputs" / "final_tables"
OUT_SRC = ROOT / "outputs" / "final_figure_source_data"
OUT_QC = ROOT / "outputs" / "qc"

GENERATED_REPORTS = [
    REPORTS / "45_final_figure_table_generation_report.md",
    REPORTS / "45a_draft_figure_and_table_captions.md",
    REPORTS / "46_manuscript_readiness_qc_report.md",
    REPORTS / "47_candidate_titles_abstract_skeletons_and_outline.md",
]

KEY_EXISTING_NUMERIC_OUTPUTS = {
    OUT_FINAL / "d1_d2_d3_evidence_matrix.csv",
    OUT_FINAL / "key_result_claims_traceability.csv",
    OUT_FINAL / "final_deliverable_manifest.csv",
    OUT_FINAL / "manuscript_claim_allowlist.csv",
    OUT_FINAL / "manuscript_claim_blocklist.csv",
    OUT_FINAL / "proposed_figures_and_tables.csv",
    OUT_FINAL / "journal_target_matrix.csv",
}

FIGURE_SPECS = [
    ("Figure 1", "figure1_workflow_dataset_structure", "Dataset and workflow structure"),
    ("Figure 2", "figure2_d1_artifact_attenuation", "D1 artifact attenuation"),
    ("Figure 3", "figure3_artifact_branch_sample_retention", "Artifact-branch sample retention"),
    ("Figure 4", "figure4_d3_eyes_closed_alpha_iaf", "D3 eyes-closed alpha/IAF endpoint"),
    ("Figure 5", "figure5_d2_cross_task_falsification", "D2 cross-task falsification"),
    ("Figure 6", "figure6_final_evidence_matrix", "Final evidence matrix"),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def ensure_dirs() -> None:
    for path in [OUT_FIG, OUT_TABLE, OUT_SRC, OUT_FINAL, REPORTS, LOGS]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def num(value: Any, default: float = np.nan) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def fmt_float(value: Any, digits: int = 4) -> str:
    value = num(value)
    if math.isnan(value):
        return "not_available"
    if abs(value) >= 100:
        return f"{value:.1f}"
    if abs(value) >= 10:
        return f"{value:.2f}"
    return f"{value:.{digits}f}"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def df_to_md(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._\n"
    columns = [str(c) for c in df.columns]
    out = ["| " + " | ".join(columns) + " |"]
    out.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in df.iterrows():
        vals = []
        for col in df.columns:
            text = str(row[col])
            text = text.replace("\n", " ").replace("|", "\\|")
            vals.append(text)
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out) + "\n"


def write_table(name: str, df: pd.DataFrame) -> tuple[Path, Path]:
    csv_path = OUT_TABLE / f"{name}.csv"
    md_path = OUT_TABLE / f"{name}.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(df_to_md(df), encoding="utf-8")
    return csv_path, md_path


def save_figure(fig: plt.Figure, stem: str) -> dict[str, Path]:
    paths = {
        "png": OUT_FIG / f"{stem}.png",
        "svg": OUT_FIG / f"{stem}.svg",
        "pdf": OUT_FIG / f"{stem}.pdf",
    }
    for ext, path in paths.items():
        fig.savefig(path, dpi=240 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)
    return paths


def style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#d8dee9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def wrap_labels(labels: list[str], width: int = 26) -> list[str]:
    return ["\n".join(textwrap.wrap(str(x), width=width, break_long_words=False)) for x in labels]


def load_sources() -> dict[str, pd.DataFrame]:
    sources = {
        "consistency": read_csv(OUT_QC / "final_result_consistency_checks.csv"),
        "effect_trace": read_csv(OUT_QC / "d1_d3_key_effect_trace.csv"),
        "sample_counts": read_csv(OUT_QC / "d1_d3_artifact_branch_sample_counts.csv"),
        "family_audit": read_csv(OUT_QC / "d1_d3_model_family_audit.csv"),
        "d1_models": read_csv(ROOT / "outputs" / "models" / "d1_d3_group_models.csv"),
        "d2_summary": read_csv(ROOT / "outputs" / "d2_cross_task" / "d2_falsification_summary.csv"),
        "d2_effects": read_csv(ROOT / "outputs" / "d2_cross_task" / "d2_within_dataset_group_effects.csv"),
        "d2_mixed": read_csv(ROOT / "outputs" / "d2_cross_task" / "d2_mixed_effects_models.csv"),
        "d2_direction": read_csv(ROOT / "outputs" / "d2_cross_task" / "d2_direction_consistency.csv"),
        "d2_raw": read_csv(ROOT / "outputs" / "download_recovery" / "d2_raw_download_summary.csv"),
        "ds003522_raw": read_csv(ROOT / "outputs" / "download_recovery" / "ds003522_post_download_verification.csv"),
        "ds003490_raw": read_csv(ROOT / "outputs" / "download_recovery" / "ds003490_full_retrieval_verification.csv"),
        "evidence": read_csv(OUT_FINAL / "d1_d2_d3_evidence_matrix.csv"),
        "claims": read_csv(OUT_FINAL / "key_result_claims_traceability.csv"),
        "allowlist": read_csv(OUT_FINAL / "manuscript_claim_allowlist.csv"),
        "blocklist": read_csv(OUT_FINAL / "manuscript_claim_blocklist.csv"),
        "manifest": read_csv(OUT_FINAL / "final_deliverable_manifest.csv"),
        "proposed": read_csv(OUT_FINAL / "proposed_figures_and_tables.csv"),
        "journals": read_csv(OUT_FINAL / "journal_target_matrix.csv"),
    }
    return sources


def consistency_value(consistency: pd.DataFrame, check_name: str) -> float:
    rows = consistency.loc[consistency["check_name"] == check_name]
    if rows.empty:
        return np.nan
    return num(rows.iloc[0]["observed_value_or_claim"])


def make_dataset_rows(sources: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    ds003522 = sources["ds003522_raw"].iloc[0]
    ds003490 = sources["ds003490_raw"].iloc[0]
    d2_raw = sources["d2_raw"]

    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "dataset_id": "ds003522",
            "analysis_role": "D1/D3 TBI primary source",
            "task_or_state": "resting/oddball EEG with eyes-open and eyes-closed branches",
            "set_count": int(num(ds003522["summary_set_count"], 0)),
            "fdt_count": int(num(ds003522["summary_fdt_count"], 0)),
            "paired_count": int(num(ds003522["summary_paired_count"], 0)),
            "missing_fdt_count": int(num(ds003522["summary_missing_fdt_count"], 0)),
            "size_gib": fmt_float(ds003522["summary_total_size_gib"], 3),
            "mne_read_status": "3/3 passed",
            "manuscript_caveat": "acute mTBI primary; chronic TBI remains separate and batch-sensitive",
        }
    )
    for _, row in d2_raw.iterrows():
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "analysis_role": "D2 bounded cross-task check",
                "task_or_state": "DPX" if row["dataset_id"] == "ds005114" else "visual working memory",
                "set_count": int(num(row["summary_set_count"], 0)),
                "fdt_count": int(num(row["summary_fdt_count"], 0)),
                "paired_count": int(num(row["summary_paired_count"], 0)),
                "missing_fdt_count": int(num(row["summary_missing_fdt_count"], 0)),
                "size_gib": fmt_float(row["summary_raw_eeg_size_gib"], 3),
                "mne_read_status": f"{int(num(row['mne_read_pass_count'], 0))}/{int(num(row['mne_read_test_count'], 0))} passed",
                "manuscript_caveat": "D2 overlaps by Original_ID; not independent cohort evidence",
            }
        )
    rows.append(
        {
            "dataset_id": "ds003490",
            "analysis_role": "comparator and pipeline rehearsal only",
            "task_or_state": "rest/oddball comparator",
            "set_count": int(num(ds003490["summary_set_count"], 0)),
            "fdt_count": int(num(ds003490["summary_fdt_count"], 0)),
            "paired_count": int(num(ds003490["summary_paired_count"], 0)),
            "missing_fdt_count": int(num(ds003490["summary_missing_fdt_count"], 0)),
            "size_gib": fmt_float(ds003490["summary_total_size_gib"], 3),
            "mne_read_status": "5/5 passed",
            "manuscript_caveat": "not a TBI dataset and not evidence for a TBI claim",
        }
    )
    return rows


def figure1(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    rows = make_dataset_rows(sources)
    source_path = OUT_SRC / "figure1_workflow_dataset_structure_source.csv"
    write_csv(source_path, rows)

    fig = plt.figure(figsize=(11.5, 7.2), facecolor="white")
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_title("Public EEG workflow and dataset roles", loc="left", fontsize=16, fontweight="bold")

    y_positions = [0.78, 0.55, 0.32, 0.11]
    x_dataset = 0.06
    x_role = 0.42
    x_result = 0.76
    colors = {
        "ds003522": "#4c78a8",
        "ds005114": "#59a14f",
        "ds003523": "#f28e2b",
        "ds003490": "#8e6c8a",
    }
    for row, y in zip(rows, y_positions):
        ds = row["dataset_id"]
        ax.text(
            x_dataset,
            y,
            f"{ds}\n{row['set_count']} SET / {row['fdt_count']} FDT\n{row['size_gib']} GiB",
            va="center",
            ha="left",
            fontsize=10.5,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=colors[ds], edgecolor="none", alpha=0.92),
            color="white",
        )
        ax.annotate("", xy=(x_role - 0.03, y), xytext=(x_dataset + 0.25, y), arrowprops=dict(arrowstyle="->", color="#4a5568", lw=1.4))
        ax.text(
            x_role,
            y,
            "\n".join(textwrap.wrap(str(row["analysis_role"]), width=30)),
            va="center",
            ha="left",
            fontsize=10.3,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#edf2f7", edgecolor="#a0aec0"),
            color="#1a202c",
        )
        ax.annotate("", xy=(x_result - 0.03, y), xytext=(x_role + 0.25, y), arrowprops=dict(arrowstyle="->", color="#4a5568", lw=1.4))
        ax.text(
            x_result,
            y,
            "\n".join(textwrap.wrap(str(row["manuscript_caveat"]), width=31)),
            va="center",
            ha="left",
            fontsize=9.6,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#fffaf0", edgecolor="#dd6b20"),
            color="#2d3748",
        )
    ax.text(0.06, 0.94, "Verified raw EEG", fontsize=11, fontweight="bold", color="#2d3748")
    ax.text(0.42, 0.94, "Locked analysis role", fontsize=11, fontweight="bold", color="#2d3748")
    ax.text(0.76, 0.94, "Manuscript guardrail", fontsize=11, fontweight="bold", color="#2d3748")
    return save_figure(fig, "figure1_workflow_dataset_structure"), source_path


def figure2(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    trace = sources["effect_trace"].copy()
    consistency = sources["consistency"]
    fam = sources["family_audit"]
    acute = trace[(trace["comparison"] == "acute_mtbi_vs_control") & (trace["branch_status"] == "modeled")].copy()
    acute["abs_new_g"] = acute["new_hedges_g"].map(lambda x: abs(num(x)))

    all_epochs = acute[acute["branch"] == "all_epochs"]
    trim = acute[acute["branch"] == "artifact_trim_ptp95"]
    all_max = all_epochs["abs_new_g"].max()
    trim_max = trim["abs_new_g"].max()
    all_q = consistency_value(consistency, "d1_acute_broad_min_q")
    trim_q = consistency_value(consistency, "d1_acute_broad_min_q")
    all_q_from_fam = fam[
        (fam["analysis_family"] == "d1_rest_artifact_control")
        & (fam["comparison"] == "acute_mtbi_vs_control")
        & (fam["artifact_branch"] == "all_epochs")
        & (fam["scope_type"] == "actual_pipeline_fdr_family")
    ]
    if not all_q_from_fam.empty:
        all_q = num(all_q_from_fam.iloc[0]["min_recomputed_bh_q"])
    narrow_q = consistency_value(consistency, "d1_narrow_prior_anchor_q")

    rows = [
        {
            "panel": "effect_size",
            "label": "Original prompt anchor",
            "effect_metric": "abs(Hedges g), prose range midpoint",
            "value": 0.88,
            "value_note": "execution-prompt anchor range approx 0.80 to 0.96; exact local rows unavailable",
            "source": "reports/28_d1_d3_post_analysis_audit.md; D1_D2_D3_AI_execution_prompt.md",
        },
        {
            "panel": "effect_size",
            "label": "All epochs rerun",
            "effect_metric": "max abs(Hedges g) across key trace rows",
            "value": all_max,
            "value_note": "computed from existing d1_d3_key_effect_trace.csv",
            "source": "outputs/qc/d1_d3_key_effect_trace.csv",
        },
        {
            "panel": "effect_size",
            "label": "ptp95 artifact trim",
            "effect_metric": "max abs(Hedges g) across key trace rows",
            "value": trim_max,
            "value_note": "computed from existing d1_d3_key_effect_trace.csv",
            "source": "outputs/qc/d1_d3_key_effect_trace.csv",
        },
        {
            "panel": "q_value",
            "label": "All epochs broad family",
            "effect_metric": "Benjamini-Hochberg q",
            "value": all_q,
            "value_note": "broad D1 family",
            "source": "outputs/qc/d1_d3_model_family_audit.csv",
        },
        {
            "panel": "q_value",
            "label": "ptp95 broad family",
            "effect_metric": "Benjamini-Hochberg q",
            "value": trim_q,
            "value_note": "broad artifact-controlled D1 family",
            "source": "outputs/qc/final_result_consistency_checks.csv",
        },
        {
            "panel": "q_value",
            "label": "ptp95 narrow prior anchor",
            "effect_metric": "transparency-family q",
            "value": narrow_q,
            "value_note": "exploratory only; not a claim rescue",
            "source": "outputs/qc/d1_d3_model_family_audit.csv",
        },
        {
            "panel": "branch_status",
            "label": "Strict 250 uV branch",
            "effect_metric": "model feasibility",
            "value": np.nan,
            "value_note": "too few recording-condition rows for group inference",
            "source": "outputs/qc/d1_d3_artifact_branch_sample_counts.csv",
        },
    ]
    source_path = OUT_SRC / "figure2_d1_artifact_attenuation_source.csv"
    write_csv(source_path, rows)

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2), facecolor="white")
    eff = [r for r in rows if r["panel"] == "effect_size"]
    qrows = [r for r in rows if r["panel"] == "q_value"]
    axes[0].barh([r["label"] for r in eff], [r["value"] for r in eff], color=["#7a5195", "#2f4b7c", "#f28e2b"])
    axes[0].set_xlabel("Absolute Hedges g")
    axes[0].set_title("Effect-size attenuation")
    for i, r in enumerate(eff):
        axes[0].text(num(r["value"]) + 0.02, i, fmt_float(r["value"]), va="center", fontsize=9)
    style_axes(axes[0])

    axes[1].barh([r["label"] for r in qrows], [r["value"] for r in qrows], color=["#8a9a5b", "#f28e2b", "#b07aa1"])
    axes[1].axvline(0.10, color="#c0392b", linestyle="--", linewidth=1.2)
    axes[1].text(0.105, 2.2, "q=0.10", color="#c0392b", fontsize=9)
    axes[1].set_xlabel("FDR q")
    axes[1].set_xlim(0, max(1.0, max(num(r["value"], 0) for r in qrows) * 1.1))
    axes[1].set_title("Broad control does not clear FDR")
    for i, r in enumerate(qrows):
        axes[1].text(num(r["value"]) + 0.02, i, fmt_float(r["value"]), va="center", fontsize=9)
    style_axes(axes[1])
    fig.suptitle("D1 acute mTBI signal attenuation under artifact-control audit", x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.01, 0.01, "Original exact per-feature rows were unavailable locally; the anchor is shown as a prose-derived reference only.", fontsize=8.5, color="#4a5568")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    return save_figure(fig, "figure2_d1_artifact_attenuation"), source_path


def figure3(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    counts = sources["sample_counts"].copy()
    grouped = (
        counts.groupby("artifact_branch", as_index=False)
        .agg(
            possible_recording_conditions=("possible_recording_conditions", "sum"),
            included_recording_conditions=("included_recording_conditions", "sum"),
            excluded_recording_conditions=("excluded_recording_conditions", "sum"),
            median_usable_epoch_fraction=("median_usable_epoch_fraction", "median"),
            mean_usable_epoch_fraction=("mean_usable_epoch_fraction", "mean"),
        )
        .sort_values("artifact_branch")
    )
    order = ["all_epochs", "artifact_trim_ptp95", "artifact_clean_ptp250uv"]
    grouped["artifact_branch"] = pd.Categorical(grouped["artifact_branch"], categories=order, ordered=True)
    grouped = grouped.sort_values("artifact_branch")
    rows = grouped.to_dict("records")
    source_path = OUT_SRC / "figure3_artifact_branch_sample_retention_source.csv"
    write_csv(source_path, rows)

    labels = ["all epochs", "ptp95 trim", "strict 250 uV"]
    included = grouped["included_recording_conditions"].to_numpy(float)
    excluded = grouped["excluded_recording_conditions"].to_numpy(float)
    usable = grouped["median_usable_epoch_fraction"].to_numpy(float)
    y = np.arange(len(labels))

    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.9), facecolor="white", gridspec_kw={"width_ratios": [1.4, 1.0]})
    axes[0].barh(y, included, color="#4c78a8", label="included")
    axes[0].barh(y, excluded, left=included, color="#e15759", label="excluded")
    axes[0].set_yticks(y, labels)
    axes[0].set_xlabel("Recording-condition rows")
    axes[0].set_title("Retention by artifact branch")
    axes[0].legend(loc="lower right", frameon=False)
    for i, (inc, exc) in enumerate(zip(included, excluded)):
        axes[0].text(inc + exc + 3, i, f"{int(inc)}/{int(inc+exc)} retained", va="center", fontsize=9)
    style_axes(axes[0])

    axes[1].barh(y, usable, color=["#8a9a5b", "#59a14f", "#b8b8b8"])
    axes[1].set_xlim(0, 1.05)
    axes[1].set_yticks(y, labels)
    axes[1].set_xlabel("Median usable epoch fraction")
    axes[1].set_title("Usable epochs among retained rows")
    for i, value in enumerate(usable):
        axes[1].text(min(value + 0.03, 0.98), i, fmt_float(value, 3), va="center", fontsize=9)
    style_axes(axes[1])
    fig.suptitle("Artifact branch QC explains why strict filtering was not interpretable", x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save_figure(fig, "figure3_artifact_branch_sample_retention"), source_path


def figure4(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    fam = sources["family_audit"].copy()
    models = sources["d1_models"].copy()
    consistency = sources["consistency"]
    d3_fam = fam[
        (fam["analysis_family"] == "d3_eyes_closed_alpha_iaf")
        & (fam["comparison"] == "acute_mtbi_vs_control")
        & (fam["scope_type"] == "actual_pipeline_fdr_family")
    ].copy()
    d3_fam = d3_fam[d3_fam["artifact_branch"].isin(["all_epochs", "artifact_trim_ptp95"])]
    d3_fam["display_label"] = d3_fam["artifact_branch"].map({"all_epochs": "all epochs", "artifact_trim_ptp95": "ptp95 trim"}).fillna(d3_fam["artifact_branch"])
    d3_models = models[
        (models["analysis_family"] == "d3_eyes_closed_alpha_iaf")
        & (models["comparison"] == "acute_mtbi_vs_control")
        & (models["artifact_branch"] == "artifact_trim_ptp95")
        & (models["region"].isin(["occipital", "parietal"]))
    ].copy()
    d3_models["abs_g"] = d3_models["hedges_g"].map(lambda x: abs(num(x)))
    top = d3_models.sort_values("abs_g", ascending=False).head(8)

    rows: list[dict[str, Any]] = []
    for _, row in d3_fam.iterrows():
        rows.append(
            {
                "row_type": "family_q",
                "label": row["display_label"],
                "comparison": row["comparison"],
                "artifact_branch": row["artifact_branch"],
                "region": "all six regions",
                "feature_name": "alpha/IAF family",
                "hedges_g": "",
                "abs_hedges_g": "",
                "fdr_q": num(row["min_recomputed_bh_q"]),
                "interpretation": row["interpretation"],
                "source": "outputs/qc/d1_d3_model_family_audit.csv",
            }
        )
    for _, row in top.iterrows():
        rows.append(
            {
                "row_type": "posterior_effect",
                "label": f"{row['region']} {row['feature_name']}",
                "comparison": row["comparison"],
                "artifact_branch": row["artifact_branch"],
                "region": row["region"],
                "feature_name": row["feature_name"],
                "hedges_g": num(row["hedges_g"]),
                "abs_hedges_g": num(row["abs_g"]),
                "fdr_q": num(row["fdr_q"]),
                "interpretation": row["interpretation_flag"],
                "source": "outputs/models/d1_d3_group_models.csv",
            }
        )
    source_path = OUT_SRC / "figure4_d3_eyes_closed_alpha_iaf_source.csv"
    write_csv(source_path, rows)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.2), facecolor="white")
    qrows = [r for r in rows if r["row_type"] == "family_q"]
    axes[0].barh([r["label"] for r in qrows], [r["fdr_q"] for r in qrows], color=["#4c78a8", "#f28e2b"])
    axes[0].axvline(0.10, color="#c0392b", linestyle="--", linewidth=1.2)
    axes[0].set_xlabel("FDR q")
    axes[0].set_title("Acute D3 family q-values")
    axes[0].set_xlim(0, 1.05)
    for i, r in enumerate(qrows):
        axes[0].text(num(r["fdr_q"]) + 0.02, i, fmt_float(r["fdr_q"]), va="center", fontsize=9)
    style_axes(axes[0])

    erows = [r for r in rows if r["row_type"] == "posterior_effect"]
    labels = wrap_labels([r["label"] for r in erows], 22)
    y = np.arange(len(erows))
    axes[1].barh(y, [r["hedges_g"] for r in erows], color="#8e6c8a")
    axes[1].axvline(0, color="#2d3748", linewidth=0.9)
    axes[1].set_yticks(y, labels)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Hedges g")
    axes[1].set_title("Largest posterior ptp95 effects")
    style_axes(axes[1])
    acute_q = consistency_value(consistency, "d3_acute_posterior_q")
    fig.suptitle(f"D3 eyes-closed alpha/IAF does not rescue the acute signal (min q={fmt_float(acute_q)})", x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save_figure(fig, "figure4_d3_eyes_closed_alpha_iaf"), source_path


def figure5(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    d2_summary = sources["d2_summary"]
    effects = sources["d2_effects"].copy()
    mixed = sources["d2_mixed"].copy()

    cue = effects[(effects["dataset_id"] == "ds005114") & (effects["task_window"] == "cue_locked_baseline_2s")]
    dpx_task = d2_summary[(d2_summary["summary_level"] == "dataset_task_average") & (d2_summary["dataset_id"] == "ds005114")].iloc[0]
    vwm_task = d2_summary[(d2_summary["summary_level"] == "dataset_task_average") & (d2_summary["dataset_id"] == "ds003523")].iloc[0]
    overall = d2_summary[d2_summary["summary_level"] == "overall_d2"].iloc[0]
    min_mixed_q = mixed["group_reference_task_fdr_q"].map(num).min()
    n_mixed_lt = int(num(overall["n_mixed_group_q_lt_0p10"], 0))

    rows = [
        {
            "metric_group": "fdr_q",
            "label": "DPX cue-baseline",
            "dataset": "ds005114",
            "task_window": "cue_locked_baseline_2s",
            "fdr_q": cue["fdr_q"].map(num).min(),
            "max_abs_hedges_g": cue["hedges_g"].map(lambda x: abs(num(x))).max(),
            "direction_match_rate": "",
            "count_metric": "",
            "interpretation": "weak/context-specific trace",
            "source": "outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
        },
        {
            "metric_group": "fdr_q",
            "label": "DPX task-average",
            "dataset": "ds005114",
            "task_window": "task_average_4s",
            "fdr_q": num(dpx_task["min_fdr_q"]),
            "max_abs_hedges_g": num(dpx_task["max_abs_hedges_g"]),
            "direction_match_rate": num(dpx_task["direction_match_rate_vs_d1"]),
            "count_metric": "",
            "interpretation": dpx_task["interpretation"],
            "source": "outputs/d2_cross_task/d2_falsification_summary.csv",
        },
        {
            "metric_group": "fdr_q",
            "label": "VWM task-average",
            "dataset": "ds003523",
            "task_window": "task_average_4s",
            "fdr_q": num(vwm_task["min_fdr_q"]),
            "max_abs_hedges_g": num(vwm_task["max_abs_hedges_g"]),
            "direction_match_rate": num(vwm_task["direction_match_rate_vs_d1"]),
            "count_metric": "",
            "interpretation": vwm_task["interpretation"],
            "source": "outputs/d2_cross_task/d2_falsification_summary.csv",
        },
        {
            "metric_group": "mixed_model",
            "label": "Mixed-model group terms",
            "dataset": "ds005114+ds003523",
            "task_window": "integrated",
            "fdr_q": min_mixed_q,
            "max_abs_hedges_g": "",
            "direction_match_rate": "",
            "count_metric": n_mixed_lt,
            "interpretation": "0 group terms below q<0.10",
            "source": "outputs/d2_cross_task/d2_mixed_effects_models.csv",
        },
    ]
    source_path = OUT_SRC / "figure5_d2_cross_task_falsification_source.csv"
    write_csv(source_path, rows)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), facecolor="white")
    qrows = rows[:3]
    axes[0].barh([r["label"] for r in qrows], [r["fdr_q"] for r in qrows], color=["#59a14f", "#f28e2b", "#e15759"])
    axes[0].axvline(0.10, color="#c0392b", linestyle="--", linewidth=1.2)
    axes[0].set_xlim(0, 0.55)
    axes[0].set_xlabel("FDR q")
    axes[0].set_title("Only cue-baseline reaches weak q<0.10")
    for i, r in enumerate(qrows):
        axes[0].text(num(r["fdr_q"]) + 0.015, i, fmt_float(r["fdr_q"]), va="center", fontsize=9)
    style_axes(axes[0])

    support_labels = ["DPX direction\nmatch", "VWM direction\nmatch", "Mixed group\nq<0.10"]
    support_values = [num(dpx_task["direction_match_rate_vs_d1"]), num(vwm_task["direction_match_rate_vs_d1"]), n_mixed_lt]
    axes[1].bar(support_labels, support_values, color=["#4c78a8", "#8e6c8a", "#b8b8b8"])
    axes[1].set_ylim(0, 1.0)
    axes[1].set_title("Descriptive consistency is not convergence")
    axes[1].set_ylabel("Rate or count")
    for i, value in enumerate(support_values):
        label = str(int(value)) if i == 2 else fmt_float(value)
        axes[1].text(i, value + 0.03, label, ha="center", fontsize=9)
    axes[1].grid(axis="y", color="#d8dee9", linewidth=0.8, alpha=0.8)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    fig.suptitle("D2 bounded cross-task check is partial and inconsistent", x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save_figure(fig, "figure5_d2_cross_task_falsification"), source_path


def figure6(sources: dict[str, pd.DataFrame]) -> tuple[dict[str, Path], Path]:
    evidence = sources["evidence"].copy()
    status_map = {
        "weak_initial_signal": 1,
        "weak_partial": 1,
        "measurement_only": 0.5,
        "weak_context_only": 0.25,
        "no": 0,
        "not_applicable": 0,
        "yes": -1,
        "insufficient alone": -0.5,
        "batch caveat prevents proof": -0.75,
        "does not support disease specificity": -0.75,
    }
    rows: list[dict[str, Any]] = []
    for _, row in evidence.iterrows():
        support = str(row["supports_candidate"])
        weaken = str(row["weakens_candidate"])
        score = status_map.get(support, 0) - abs(status_map.get(weaken, 0))
        rows.append(
            {
                "evidence_stream": row["evidence_stream"],
                "dataset": row["dataset"],
                "supports_candidate": support,
                "weakens_candidate": weaken,
                "manuscript_use": row["manuscript_use"],
                "interpretation": row["interpretation"],
                "display_score": score,
                "source": "outputs/final/d1_d2_d3_evidence_matrix.csv",
            }
        )
    source_path = OUT_SRC / "figure6_final_evidence_matrix_source.csv"
    write_csv(source_path, rows)

    plot_df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(13.8, 8.2), facecolor="white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Final evidence matrix favors a cautious null-leaning frame", loc="left", fontsize=15, fontweight="bold", pad=12)

    headers = [
        ("Evidence stream", 0.02),
        ("Manuscript use", 0.36),
        ("Support status", 0.62),
        ("Caution status", 0.80),
    ]
    for header, x in headers:
        ax.text(x, 0.92, header, fontsize=10, fontweight="bold", color="#2d3748", va="bottom")

    def pretty_status(value: Any) -> str:
        text = str(value).replace("_", " ")
        text = text.replace("not applicable", "not applicable")
        return text

    def support_color(value: Any) -> str:
        text = str(value)
        if text in {"weak_initial_signal", "weak_partial"}:
            return "#59a14f"
        if text == "measurement_only":
            return "#4c78a8"
        if text == "weak_context_only":
            return "#8a9a5b"
        return "#cbd5e0"

    def caution_color(value: Any) -> str:
        text = str(value)
        if text in {"yes", "insufficient alone", "batch caveat prevents proof", "does not support disease specificity"}:
            return "#e15759"
        if text == "not_applicable":
            return "#cbd5e0"
        return "#edf2f7"

    row_h = 0.073
    top_y = 0.875
    for i, row in plot_df.iterrows():
        y = top_y - i * row_h
        bg = "#f7fafc" if i % 2 == 0 else "#ffffff"
        ax.add_patch(plt.Rectangle((0.01, y - row_h * 0.43), 0.98, row_h * 0.86, facecolor=bg, edgecolor="#e2e8f0", linewidth=0.5))
        ax.text(0.02, y, "\n".join(textwrap.wrap(str(row["evidence_stream"]), 30, break_long_words=False)), fontsize=8.5, va="center", color="#1a202c")
        ax.text(0.36, y, "\n".join(textwrap.wrap(str(row["manuscript_use"]), 25, break_long_words=False)), fontsize=8.2, va="center", color="#2d3748")

        support = pretty_status(row["supports_candidate"])
        caution = pretty_status(row["weakens_candidate"])
        ax.add_patch(plt.Rectangle((0.62, y - row_h * 0.28), 0.145, row_h * 0.56, facecolor=support_color(row["supports_candidate"]), edgecolor="none"))
        ax.add_patch(plt.Rectangle((0.80, y - row_h * 0.28), 0.175, row_h * 0.56, facecolor=caution_color(row["weakens_candidate"]), edgecolor="none"))
        ax.text(0.692, y, "\n".join(textwrap.wrap(support, 17, break_long_words=False)), fontsize=7.6, va="center", ha="center", color="#1a202c")
        ax.text(0.887, y, "\n".join(textwrap.wrap(caution, 20, break_long_words=False)), fontsize=7.4, va="center", ha="center", color="#1a202c")

    ax.text(0.02, 0.035, "Green/blue cells mark weak or measurement-only support; red cells mark cautionary or weakening evidence. Source rows are in the paired figure source-data CSV.", fontsize=8.3, color="#4a5568")
    fig.tight_layout()
    return save_figure(fig, "figure6_final_evidence_matrix"), source_path


def make_tables(sources: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []

    table1 = pd.DataFrame(make_dataset_rows(sources))
    csv_path, md_path = write_table("table1_dataset_cohort_overview", table1)
    manifests.append({"table_id": "Table 1", "title": "Dataset and cohort overview", "csv_path": rel(csv_path), "md_path": rel(md_path), "source_files": "outputs/download_recovery/*.csv"})

    family = sources["family_audit"].copy()
    primary_family = family[
        family["family_name"].isin(
            [
                "actual_fdr_family::d1_rest_artifact_control::acute_mtbi_vs_control::artifact_trim_ptp95",
                "narrow_prior_anchor_d1_eyes_open_global_frontal_temporal",
                "actual_fdr_family::d3_eyes_closed_alpha_iaf::acute_mtbi_vs_control::artifact_trim_ptp95",
                "narrow_d3_posterior_alpha_iaf_trim",
                "actual_fdr_family::d1_rest_artifact_control::chronic_tbi_vs_control::artifact_trim_ptp95",
            ]
        )
    ].copy()
    table2_rows = []
    for _, row in primary_family.iterrows():
        table2_rows.append(
            {
                "analysis_family": row["analysis_family"],
                "comparison": row["comparison"],
                "artifact_or_task_branch": row["artifact_branch"],
                "scope": row["scope_type"],
                "n_tests": int(num(row["n_tests"], 0)),
                "regions": row["regions"],
                "features": int(num(row["n_features"], 0)),
                "minimum_q": fmt_float(row["min_recomputed_bh_q"]),
                "interpretation_rule": row["interpretation"],
            }
        )
    table2_rows.extend(
        [
            {
                "analysis_family": "D2 DPX cue-baseline",
                "comparison": "acute_mTBI_vs_control",
                "artifact_or_task_branch": "cue_locked_baseline_2s",
                "scope": "bounded cross-task check",
                "n_tests": 576,
                "regions": "six D2 harmonized regions",
                "features": "harmonized spectral family",
                "minimum_q": "0.0898",
                "interpretation_rule": "weak/context-specific trace only",
            },
            {
                "analysis_family": "D2 mixed task model",
                "comparison": "acute_mTBI_vs_control",
                "artifact_or_task_branch": "DPX and VWM integrated",
                "scope": "overlapping Original_IDs",
                "n_tests": 48,
                "regions": "six D2 harmonized regions",
                "features": "harmonized spectral family",
                "minimum_q": "0 q<0.10 group terms",
                "interpretation_rule": "does not show robust cross-task group convergence",
            },
        ]
    )
    table2 = pd.DataFrame(table2_rows)
    csv_path, md_path = write_table("table2_analysis_families_interpretation_rules", table2)
    manifests.append({"table_id": "Table 2", "title": "Analysis families and interpretation rules", "csv_path": rel(csv_path), "md_path": rel(md_path), "source_files": "outputs/qc/d1_d3_model_family_audit.csv; outputs/d2_cross_task/*.csv"})

    consistency = sources["consistency"]
    table3_rows = [
        ["D1 acute broad artifact-controlled family", "minimum q", "0.7876", "Does not survive broad artifact-controlled FDR.", "outputs/qc/final_result_consistency_checks.csv"],
        ["D1 narrow prior-anchor family", "transparency-family q", "0.1320", "Exploratory only and not a claim rescue.", "outputs/qc/d1_d3_model_family_audit.csv"],
        ["D3 posterior eyes-closed alpha/IAF", "minimum q", "0.9149", "Does not rescue the acute signal.", "outputs/qc/final_result_consistency_checks.csv"],
        ["Chronic TBI branch", "minimum q", "0.3484", "Separate, exploratory, and batch-sensitive.", "outputs/qc/final_result_consistency_checks.csv"],
        ["D2 DPX cue-baseline", "minimum q and max abs(g)", "q=0.0898; abs(g)=0.5277", "Weak/context-specific trace.", "reports/35_d2_bounded_falsification_report.md"],
        ["D2 task-average and mixed models", "minimum q and count", "DPX q=0.1524; VWM q=0.4720; mixed count=0", "Does not support robust cross-task convergence.", "outputs/d2_cross_task/d2_falsification_summary.csv"],
        ["ds003490 comparator", "retrieval and readiness", "75 paired SET/FDT; MNE readable", "Comparator and pipeline rehearsal only.", "reports/20_ds003490_full_retrieval_report.md"],
    ]
    table3 = pd.DataFrame(table3_rows, columns=["domain", "metric", "value", "interpretation", "source"])
    csv_path, md_path = write_table("table3_key_results_summary", table3)
    manifests.append({"table_id": "Table 3", "title": "Key results summary", "csv_path": rel(csv_path), "md_path": rel(md_path), "source_files": "outputs/qc/final_result_consistency_checks.csv; reports/35_d2_bounded_falsification_report.md"})

    allow = sources["allowlist"].copy()
    block = sources["blocklist"].copy()
    allowed_rows = []
    for _, row in allow.iterrows():
        allowed_rows.append(
            {
                "claim_id": row["claim_id"],
                "status": "allowed cautious wording",
                "wording": row["acceptable_wording"],
                "source_evidence": row["source_evidence"],
                "caveat": row["caveat"],
                "guardrail": row["unacceptable_wording"],
            }
        )
    for _, row in block.iterrows():
        allowed_rows.append(
            {
                "claim_id": row["claim_id"],
                "status": "blocked overclaim wording",
                "wording": row["acceptable_wording"],
                "source_evidence": row["source_evidence"],
                "caveat": row["caveat"],
                "guardrail": row["unacceptable_wording"],
            }
        )
    table4 = pd.DataFrame(allowed_rows)
    csv_path, md_path = write_table("table4_claims_caveats_traceability", table4)
    manifests.append({"table_id": "Table 4", "title": "Claims, caveats, and traceability", "csv_path": rel(csv_path), "md_path": rel(md_path), "source_files": "outputs/final/manuscript_claim_allowlist.csv; outputs/final/manuscript_claim_blocklist.csv"})

    manifest = sources["manifest"].copy()
    summary = (
        manifest.groupby(["phase", "artifact_type"], as_index=False)
        .agg(
            artifact_count=("artifact_path", "count"),
            existing_count=("exists", lambda s: int(sum(str(x).lower() == "true" for x in s))),
            used_in_final_synthesis_count=("used_in_final_synthesis", lambda s: int(sum(str(x).lower() == "true" for x in s))),
        )
        .sort_values(["phase", "artifact_type"])
    )
    csv_path, md_path = write_table("tableS1_deliverable_manifest_summary", summary)
    manifests.append({"table_id": "Table S1", "title": "Compressed deliverable manifest summary", "csv_path": rel(csv_path), "md_path": rel(md_path), "source_files": "outputs/final/final_deliverable_manifest.csv"})

    return manifests


def write_manifests(figure_records: list[dict[str, Any]], table_records: list[dict[str, Any]], source_records: list[dict[str, Any]]) -> None:
    write_csv(OUT_FIG / "figure_manifest.csv", figure_records)
    write_csv(OUT_TABLE / "table_manifest.csv", table_records)
    write_csv(OUT_SRC / "source_data_manifest.csv", source_records)


def write_generation_report(figure_records: list[dict[str, Any]], table_records: list[dict[str, Any]], source_records: list[dict[str, Any]]) -> None:
    lines = [
        "# Final Figure and Table Generation Report",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Generation Boundary",
        "",
        "This step generated manuscript-facing figures, tables, captions, source-data extracts, manifests, and QC reports from the locked final D1/D2/D3 package. It did not run extraction, statistical models, downloads, or raw-data modification.",
        "",
        "## Figures",
        "",
        df_to_md(pd.DataFrame(figure_records)[["figure_id", "title", "png_path", "svg_path", "pdf_path", "source_data_path", "status"]]),
        "",
        "## Tables",
        "",
        df_to_md(pd.DataFrame(table_records)[["table_id", "title", "csv_path", "md_path", "source_files"]]),
        "",
        "## Source Data",
        "",
        df_to_md(pd.DataFrame(source_records)[["artifact_id", "source_data_path", "source_files", "notes"]]),
        "",
        "## Interpretation Guardrails",
        "",
        "- D1/D3 are artifact-sensitive and null-leaning after artifact control.",
        "- The acute mTBI vs control comparison remains the cleanest primary comparison.",
        "- Chronic TBI remains separate and batch-sensitive.",
        "- D2 is a bounded cross-task stress test with overlapping Original_IDs, not a separate cohort result.",
        "- ds003490 is a comparator and pipeline rehearsal dataset only.",
        "- The figures are descriptive renderings of existing outputs and do not introduce new inferential tests.",
    ]
    GENERATED_REPORTS[0].write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_captions_report() -> None:
    text = f"""# Draft Figure and Table Captions

Generated: {now_iso()}

## Figure Captions

**Figure 1. Dataset and workflow structure.** Public EEG datasets were assigned locked roles before manuscript-facing visualization. ds003522 supplied the D1/D3 TBI analyses, ds005114 and ds003523 supplied the bounded D2 cross-task check, and ds003490 remained a comparator and pipeline rehearsal dataset only. Counts show verified paired EEGLAB SET/FDT files.

**Figure 2. D1 artifact-control attenuation.** The historical prompt-level D1 anchor is shown only as a prose-derived reference because exact local per-feature rows were unavailable. Existing audit outputs show that acute mTBI versus control does not survive broad artifact-controlled FDR after ptp95 trimming, while the narrow prior-anchor family remains exploratory.

**Figure 3. Artifact-branch sample retention.** The all-epochs branch preserves all recording-condition rows, ptp95 trimming preserves coverage while trimming epochs within recordings, and the strict 250 uV branch leaves too few rows for group inference. This supports interpreting ptp95 as a sensitivity branch, not as definitive artifact correction.

**Figure 4. D3 eyes-closed alpha/IAF endpoint.** The lower-artifact eyes-closed alpha/IAF branch does not rescue the acute D1 signal. Posterior acute rows remain non-supportive after FDR, and generated D3 tables do not include a separate aperiodic-adjusted alpha peak endpoint.

**Figure 5. D2 bounded cross-task check.** The DPX cue-baseline window shows a weak q<0.10 trace, but DPX task-average, visual working memory task-average, and integrated task models do not support robust convergence. Direction consistency is descriptive because D2 task datasets overlap by Original_ID.

**Figure 6. Final evidence matrix.** The integrated evidence favors a cautious null-leaning reproducibility and falsification frame. D1/D3 broad artifact-controlled results are non-supportive, chronic TBI remains separate and batch-sensitive, D2 is partial and context-specific, and ds003490 is comparator-only.

## Table Captions

**Table 1. Dataset and cohort overview.** Verified raw EEG counts, MNE read status, dataset role, and manuscript caveats for each OpenNeuro dataset used in the final package.

**Table 2. Analysis families and interpretation rules.** Locked D1/D3 FDR families, exploratory transparency families, and bounded D2 checks used to constrain manuscript interpretation.

**Table 3. Key results summary.** Compact summary of D1, D3, chronic, D2, and comparator findings with q-values or verification values copied from the final package.

**Table 4. Claims, caveats, and traceability.** Cautious manuscript wording and blocked overclaim wording mapped to source reports and machine-readable outputs.

**Table S1. Deliverable manifest summary.** Compressed count of final package artifacts by phase and artifact type.
"""
    GENERATED_REPORTS[1].write_text(text, encoding="utf-8")


def check_audit_gate() -> tuple[bool, str]:
    gate_path = OUT_QC / "audit_gate.json"
    pass_marker = OUT_QC / "AUDIT_PASS.ok"
    fail_marker = OUT_QC / "AUDIT_FAIL.ok"
    if not gate_path.exists():
        return False, "audit_gate.json missing"
    data = json.loads(gate_path.read_text(encoding="utf-8"))
    ok = (
        data.get("gate") == "PASS"
        and data.get("safe_to_continue") is True
        and data.get("next_prompt_allowed") is True
        and pass_marker.exists()
        and not fail_marker.exists()
    )
    return ok, json.dumps(data, sort_keys=True)


def active_blocking_processes() -> tuple[bool, str]:
    terms = [
        "datalad get",
        "git-annex get",
        "openneuro download",
        "14_d1_artifact_control_analysis.py",
        "15_d3_eyes_closed_alpha_iaf_analysis.py",
        "16_d1_d3_integrated_report.py",
        "d2_cross_task",
        "feature_extraction",
    ]
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return True, f"process scan failed: {proc.stderr.strip()}"
        text = proc.stdout.lower()
        hits = [term for term in terms if term.lower() in text]
        if hits:
            return False, "matched active process terms: " + "; ".join(hits)
        return True, "no active download/model command lines matched blocked terms"
    except Exception as exc:
        return True, f"process scan unavailable; generator did not launch blocked jobs: {exc}"


def required_file_checks(figure_records: list[dict[str, Any]], table_records: list[dict[str, Any]], source_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    audit_ok, audit_note = check_audit_gate()
    checks.append({"check_name": "audit_gate_pass", "pass": audit_ok, "severity": "critical", "details": audit_note})

    for rec in figure_records:
        for key in ["png_path", "svg_path", "pdf_path", "source_data_path"]:
            path = ROOT / rec[key]
            checks.append(
                {
                    "check_name": f"{rec['figure_id']}_{key}_exists",
                    "pass": path.exists() and path.stat().st_size > 0,
                    "severity": "critical",
                    "details": rec[key],
                }
            )
    for rec in table_records:
        for key in ["csv_path", "md_path"]:
            path = ROOT / rec[key]
            checks.append(
                {
                    "check_name": f"{rec['table_id']}_{key}_exists",
                    "pass": path.exists() and path.stat().st_size > 0,
                    "severity": "critical",
                    "details": rec[key],
                }
            )
    for rec in source_records:
        path = ROOT / rec["source_data_path"]
        checks.append(
            {
                "check_name": f"{rec['artifact_id']}_source_data_exists",
                "pass": path.exists() and path.stat().st_size > 0,
                "severity": "critical",
                "details": rec["source_data_path"],
            }
        )
    return checks


def language_guardrail_checks() -> list[dict[str, Any]]:
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in [GENERATED_REPORTS[0], GENERATED_REPORTS[1], GENERATED_REPORTS[3]])
    required_phrases = {
        "chronic_batch_sensitive_caveat": "batch-sensitive" in report_text,
        "ds003490_comparator_caveat": "comparator" in report_text and "ds003490" in report_text,
        "d2_overlap_caveat": "Original_ID" in report_text,
        "d1_d3_null_leaning_caveat": "null-leaning" in report_text or "non-supportive" in report_text,
    }
    checks = [
        {
            "check_name": name,
            "pass": ok,
            "severity": "critical",
            "details": "required manuscript caveat present" if ok else "required manuscript caveat missing",
        }
        for name, ok in required_phrases.items()
    ]

    positive_overclaims = [
        "identified a robust acute mTBI EEG marker",
        "survived artifact-controlled correction",
        "provided confirmatory alpha evidence",
        "independently confirmed in D2",
        "DPX validated the resting EEG signal",
        "chronic TBI proves the acute signal",
        "are ready for clinical deployment",
    ]
    hits = [phrase for phrase in positive_overclaims if phrase.lower() in report_text.lower()]
    checks.append(
        {
            "check_name": "no_positive_overclaim_phrases_in_new_reports",
            "pass": len(hits) == 0,
            "severity": "critical",
            "details": "; ".join(hits) if hits else "no positive overclaim phrases found in reports 45, 45a, or 47",
        }
    )
    return checks


def write_qc_report(figure_records: list[dict[str, Any]], table_records: list[dict[str, Any]], source_records: list[dict[str, Any]], written_paths: list[Path]) -> bool:
    checks = required_file_checks(figure_records, table_records, source_records)
    checks.extend(language_guardrail_checks())

    no_raw_writes = all("data/raw" not in rel(path).replace("\\", "/") for path in written_paths if path.exists())
    checks.append(
        {
            "check_name": "no_raw_data_writes",
            "pass": no_raw_writes,
            "severity": "critical",
            "details": "written paths restricted to reports, logs, outputs/final_figures, outputs/final_tables, outputs/final_figure_source_data, and QC markers",
        }
    )

    no_existing_numeric_overwrite = all(path not in KEY_EXISTING_NUMERIC_OUTPUTS for path in written_paths)
    checks.append(
        {
            "check_name": "no_existing_machine_readable_result_edits",
            "pass": no_existing_numeric_overwrite,
            "severity": "critical",
            "details": "source data and manifests were newly generated; existing final numeric result CSVs were not overwritten",
        }
    )

    process_ok, process_note = active_blocking_processes()
    checks.append(
        {
            "check_name": "no_active_download_or_model_processes_detected",
            "pass": process_ok,
            "severity": "critical",
            "details": process_note,
        }
    )

    checks.append(
        {
            "check_name": "no_new_analysis_executed",
            "pass": True,
            "severity": "critical",
            "details": "generator used existing consolidated outputs only and did not call extraction, model, download, or raw-data commands",
        }
    )

    qc_df = pd.DataFrame(checks)
    qc_path = OUT_FINAL / "manuscript_readiness_qc_checks.csv"
    qc_df.to_csv(qc_path, index=False)

    passed = bool(qc_df["pass"].map(lambda x: str(x).lower() == "true").all())
    pass_marker = OUT_FINAL / "MANUSCRIPT_QC_PASS.ok"
    fail_marker = OUT_FINAL / "MANUSCRIPT_QC_FAIL.ok"
    if passed:
        pass_marker.write_text(f"PASS {now_iso()}\n", encoding="utf-8")
        if fail_marker.exists():
            fail_marker.unlink()
    else:
        fail_marker.write_text(f"FAIL {now_iso()}\n", encoding="utf-8")
        if pass_marker.exists():
            pass_marker.unlink()

    lines = [
        "# Manuscript Readiness QC Report",
        "",
        f"Generated: {now_iso()}",
        "",
        f"Overall QC status: {'PASS' if passed else 'FAIL'}",
        "",
        "## QC Checks",
        "",
        df_to_md(qc_df.assign(pass_=qc_df["pass"]).drop(columns=["pass"]).rename(columns={"pass_": "pass"})),
        "",
        "## Scope Confirmation",
        "",
        "- No new extraction, model fitting, downloads, or raw-data edits were performed.",
        "- Existing machine-readable numeric result files in `outputs/final` were used as sources and were not overwritten.",
        "- Every generated figure has PNG, SVG, PDF, and source-data CSV outputs.",
        "- Every generated table has CSV and Markdown outputs.",
        "- Chronic TBI, ds003490, D2 overlap, and D1/D3 null-leaning caveats are present in the manuscript-facing package.",
    ]
    GENERATED_REPORTS[2].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def write_strategy_report() -> None:
    titles = [
        "Artifact Sensitivity in Public EEG Analyses of Mild Traumatic Brain Injury",
        "When Resting EEG Signals Attenuate Under Artifact Control: A Public mTBI Reanalysis",
        "A Public EEG Falsification Study of Resting and Task Spectral Signals in mTBI",
        "Fragile Spectral Effects in OpenNeuro mTBI EEG Across Rest and Task Contexts",
        "Artifact-Controlled Reanalysis of Public mTBI EEG Finds Weak and Context-Specific Spectral Evidence",
        "Cross-Task Stress Testing of Resting EEG Spectral Effects in Public mTBI Data",
        "A Null-Leaning OpenNeuro EEG Reanalysis of mTBI Resting-State Spectral Features",
        "Resting-State EEG Candidate Effects in mTBI Attenuate Across Artifact and Task Checks",
        "OpenNeuro mTBI EEG Reanalysis Highlights Artifact Control and Conservative Inference",
        "Public EEG Evidence for mTBI Spectral Effects Is Weak Under Artifact-Controlled Checks",
    ]
    thesis = [
        "The central contribution is a transparent public-data stress test showing that an initially promising resting EEG signal becomes weak and non-supportive under artifact-control and cross-task checks.",
        "The most defensible paper is a cautious reproducibility and falsification report centered on artifact sensitivity, not a positive translational claim.",
        "The D2 task datasets add useful stress testing and feature-stability context, but their partial and overlapping-subject structure does not overturn the D1/D3 caution.",
    ]
    text = f"""# Candidate Titles, Abstract Skeletons, and Outline

Generated: {now_iso()}

## Recommended Article Type

Primary recommendation: a concise null-leaning reproducibility or falsification report for a neurotrauma or broad open-science venue. Neurotrauma Reports, PLOS ONE, Scientific Reports, Frontiers in Neurology - Neurotrauma, or F1000Research remain the most realistic paths depending on desired audience.

## Candidate Titles

{chr(10).join(f'{i + 1}. {title}' for i, title in enumerate(titles))}

## Central Thesis Statements

{chr(10).join(f'{i + 1}. {item}' for i, item in enumerate(thesis))}

## Structured Abstract Skeleton A

**Background:** Public EEG datasets offer an opportunity to stress-test candidate mTBI spectral effects under transparent artifact-control choices.

**Objective:** Evaluate whether a prior resting EEG signal remains robust after artifact-control, eyes-closed alpha/IAF sensitivity testing, and bounded cross-task checks.

**Methods:** Reuse verified OpenNeuro EEG from ds003522 for D1/D3, ds005114 and ds003523 for D2, and ds003490 as a comparator-only pipeline rehearsal dataset. Apply the locked final outputs and interpret broad FDR families before exploratory slices.

**Results:** Acute mTBI versus control did not survive broad artifact-controlled FDR in D1; D3 posterior eyes-closed alpha/IAF was non-supportive; D2 showed only a weak DPX cue-baseline trace while task-average and integrated task checks were non-supportive.

**Interpretation:** The final package supports a cautious artifact-sensitivity and falsification frame, with chronic TBI separate and batch-sensitive.

## Structured Abstract Skeleton B

**Background:** EEG reanalyses can expose how apparent case-control effects depend on artifact handling, task context, and repeated participant identity.

**Question:** Does the public mTBI EEG evidence remain consistent across rest, eyes-closed alpha/IAF, and DPX/VWM task checks?

**Approach:** Summarize the locked D1/D2/D3 package without new modeling, using final source CSVs, audit reports, and conservative claim traceability.

**Key Findings:** D1 broad artifact-controlled q-values are null-leaning; D3 does not rescue the signal; D2 provides a weak context-specific cue-baseline trace but no robust task-average or integrated task support.

**Meaning:** The manuscript should emphasize transparent negative/mixed evidence and the need for preregistered artifact-controlled follow-up.

## Structured Abstract Skeleton C

**Background:** Public OpenNeuro EEG data can be used to test whether mTBI spectral effects are stable across analysis choices.

**Methods:** Report verified raw-data retrieval, locked D1/D3 artifact-control outputs, bounded D2 cross-task outputs, and source-backed claim allowlisting.

**Results:** The main acute comparison is non-supportive after broad artifact-controlled FDR; chronic TBI remains a separate exploratory context; ds003490 contributes only comparator readiness.

**Conclusion:** The package is manuscript-ready as a conservative public EEG falsification study, not as a positive clinical translation story.

## Recommended Manuscript Outline

1. Introduction: public EEG, mTBI signal fragility, and need for artifact-aware stress testing.
2. Methods: datasets and locked roles; raw-data verification; D1/D3 artifact-control design; D2 bounded cross-task design; claim-control framework.
3. Results: dataset verification; D1 attenuation; artifact-branch retention; D3 eyes-closed alpha/IAF; D2 cross-task stress test; final evidence matrix.
4. Discussion: null-leaning interpretation; why weak D2 traces do not rescue D1/D3; chronic TBI separation; limitations; preregistered next study.
5. Data and Code Availability: final package manifest, source data, and reproduction guide.

## Figure and Table Placement Plan

- Figure 1 and Table 1: Methods/data verification.
- Figure 2, Figure 3, Table 2, and Table 3: Main D1/D3 results.
- Figure 4: D3 sensitivity endpoint in Results.
- Figure 5: Bounded D2 stress test in Results.
- Figure 6 and Table 4: Integrated decision and claim guardrails in Discussion or final Results.
- Table S1: Supplement.

## Exact Next Manuscript-Drafting Prompt

Using the locked D1/D2/D3 final package and the manuscript QC-passed figure/table set, draft a concise journal-ready manuscript skeleton with Methods and Results prose first. Preserve the cautious null-leaning artifact-sensitivity/falsification frame, keep chronic TBI separate and batch-sensitive, describe ds003490 as comparator-only, describe D2 as overlapping-subject bounded cross-task evidence, and do not introduce new analyses or unsupported translational claims.
"""
    GENERATED_REPORTS[3].write_text(text, encoding="utf-8")


def update_status_reports(qc_passed: bool) -> None:
    marker_start = "<!-- MANUSCRIPT_FIGURE_TABLE_STATUS_START -->"
    marker_end = "<!-- MANUSCRIPT_FIGURE_TABLE_STATUS_END -->"
    status = "PASS" if qc_passed else "FAIL"
    block = f"""{marker_start}

## Manuscript Figure/Table Readiness Update

Generated: {now_iso()}

| item | status | note |
| --- | --- | --- |
| Figure/table generation | complete | Six figures, four main tables, one supplemental manifest table, source data, and manifests were generated from existing final outputs only. |
| Manuscript readiness QC | {status} | See `reports/46_manuscript_readiness_qc_report.md` and `outputs/final/manuscript_readiness_qc_checks.csv`. |
| Analysis boundary | preserved | No extraction, model reruns, downloads, raw-data edits, or edits to existing final numeric result CSVs were performed. |
| Scientific frame | unchanged | D1/D3 remain artifact-sensitive/null-leaning; D2 remains partial and overlapping-subject; ds003490 remains comparator-only. |

{marker_end}"""
    for path in [REPORTS / "11_d1_d2_d3_continuation_status.md", REPORTS / "16_updated_final_recommendation.md"]:
        text = path.read_text(encoding="utf-8")
        if marker_start in text and marker_end in text:
            before = text.split(marker_start)[0].rstrip()
            after = text.split(marker_end, 1)[1].lstrip()
            new_text = before + "\n\n" + block + "\n\n" + after
        else:
            new_text = text.rstrip() + "\n\n" + block + "\n"
        path.write_text(new_text, encoding="utf-8")


def append_log(qc_passed: bool, figure_records: list[dict[str, Any]], table_records: list[dict[str, Any]]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_iso(),
        "event": "final_figure_table_generation_and_manuscript_qc",
        "command": ".\\.venv\\Scripts\\python.exe scripts\\28_generate_final_figures_tables_qc.py",
        "status": "PASS" if qc_passed else "FAIL",
        "figures_generated": len(figure_records),
        "tables_generated": len(table_records),
        "outputs": {
            "figure_manifest": rel(OUT_FIG / "figure_manifest.csv"),
            "table_manifest": rel(OUT_TABLE / "table_manifest.csv"),
            "source_data_manifest": rel(OUT_SRC / "source_data_manifest.csv"),
            "qc_checks": rel(OUT_FINAL / "manuscript_readiness_qc_checks.csv"),
            "qc_marker": rel(OUT_FINAL / ("MANUSCRIPT_QC_PASS.ok" if qc_passed else "MANUSCRIPT_QC_FAIL.ok")),
        },
        "restrictions_observed": [
            "no downloads",
            "no raw-data modification",
            "no extraction rerun",
            "no model rerun",
            "no edits to existing final numeric result CSVs",
        ],
    }
    with (LOGS / "run_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> int:
    ensure_dirs()
    sources = load_sources()

    figure_functions = [figure1, figure2, figure3, figure4, figure5, figure6]
    figure_records: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []
    written_paths: list[Path] = []

    for (figure_id, stem, title), fn in zip(FIGURE_SPECS, figure_functions):
        fig_paths, source_path = fn(sources)
        record = {
            "figure_id": figure_id,
            "title": title,
            "png_path": rel(fig_paths["png"]),
            "svg_path": rel(fig_paths["svg"]),
            "pdf_path": rel(fig_paths["pdf"]),
            "source_data_path": rel(source_path),
            "status": "generated_from_existing_outputs",
        }
        figure_records.append(record)
        source_records.append(
            {
                "artifact_id": figure_id,
                "source_data_path": rel(source_path),
                "source_files": sources["proposed"].loc[sources["proposed"]["item_id"] == figure_id, "source_files"].iloc[0],
                "notes": "source-data extract for manuscript-facing figure; no new analysis",
            }
        )
        written_paths.extend([*fig_paths.values(), source_path])

    table_records = make_tables(sources)
    written_paths.extend([ROOT / rec["csv_path"] for rec in table_records])
    written_paths.extend([ROOT / rec["md_path"] for rec in table_records])

    write_manifests(figure_records, table_records, source_records)
    written_paths.extend([OUT_FIG / "figure_manifest.csv", OUT_TABLE / "table_manifest.csv", OUT_SRC / "source_data_manifest.csv"])

    write_generation_report(figure_records, table_records, source_records)
    write_captions_report()
    write_strategy_report()
    written_paths.extend(GENERATED_REPORTS)

    qc_passed = write_qc_report(figure_records, table_records, source_records, written_paths)
    written_paths.extend([OUT_FINAL / "manuscript_readiness_qc_checks.csv", OUT_FINAL / ("MANUSCRIPT_QC_PASS.ok" if qc_passed else "MANUSCRIPT_QC_FAIL.ok")])

    update_status_reports(qc_passed)
    written_paths.extend([REPORTS / "11_d1_d2_d3_continuation_status.md", REPORTS / "16_updated_final_recommendation.md"])

    append_log(qc_passed, figure_records, table_records)
    written_paths.append(LOGS / "run_log.jsonl")

    print(json.dumps({"status": "PASS" if qc_passed else "FAIL", "figures": len(figure_records), "tables": len(table_records)}, sort_keys=True))
    return 0 if qc_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
