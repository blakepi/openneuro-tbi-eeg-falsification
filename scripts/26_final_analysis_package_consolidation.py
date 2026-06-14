from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
REPORTS = PROJECT / "reports"
OUTPUTS = PROJECT / "outputs"
FINAL = OUTPUTS / "final"
LOGS = PROJECT / "logs"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(PROJECT / path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def require_clean_gate() -> dict:
    gate_path = OUTPUTS / "qc" / "audit_gate.json"
    pass_marker = OUTPUTS / "qc" / "AUDIT_PASS.ok"
    fail_marker = OUTPUTS / "qc" / "AUDIT_FAIL.ok"
    if not gate_path.exists():
        raise SystemExit("Missing outputs/qc/audit_gate.json; stopping final consolidation.")
    if not pass_marker.exists():
        raise SystemExit("Missing outputs/qc/AUDIT_PASS.ok; stopping final consolidation.")
    if fail_marker.exists():
        raise SystemExit("outputs/qc/AUDIT_FAIL.ok exists; stopping final consolidation.")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    expected = {
        "gate": "PASS",
        "safe_to_continue": True,
        "next_prompt_allowed": True,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise SystemExit(f"Audit gate not clean PASS: {key}={gate.get(key)!r}")
    return gate


def consistency_values() -> dict[str, str]:
    checks = read_csv("outputs/qc/final_result_consistency_checks.csv")
    return {
        str(row.check_name): str(row.observed_value_or_claim)
        for row in checks.itertuples(index=False)
    }


def raw_summary() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in [
        "outputs/download_recovery/ds003490_full_retrieval_verification.csv",
        "outputs/download_recovery/ds003522_post_download_verification.csv",
        "outputs/download_recovery/d2_raw_download_summary.csv",
    ]:
        p = PROJECT / path
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if "dataset_id" not in df.columns or df.empty:
            continue
        for dataset_id, group in df.groupby("dataset_id", dropna=False):
            first = group.iloc[0].to_dict()
            out[str(dataset_id)] = first
    return out


def fmt_num(value: str | float | int, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def build_evidence_matrix(values: dict[str, str]) -> list[dict]:
    d1_q = values["d1_acute_broad_min_q"]
    narrow_q = values["d1_narrow_prior_anchor_q"]
    d3_q = values["d3_acute_posterior_q"]
    chronic_q = values["chronic_trim_min_q"]
    dpx_cue_q = values["ds005114_cue_baseline_min_q"]
    dpx_cue_g = values["ds005114_cue_baseline_max_abs_g"]
    dpx_task_q = values["dpx_task_average_min_q"]
    vwm_task_q = values["vwm_task_average_min_q"]
    mixed_zero = values["mixed_models_group_q_lt_0p10"]
    return [
        {
            "evidence_stream": "D1 original/resting aperiodic candidate",
            "dataset": "ds003522",
            "task_or_state": "resting/eyes-open anchor",
            "group_or_comparison": "acute mTBI vs control; chronic exploratory branch separate",
            "feature_family": "aperiodic/spectral-balance features",
            "primary_metric": "prior execution-prompt anchor, not local per-feature model rows",
            "effect_size_summary": "prior anchor described acute abs(g) about 0.80-0.96 and chronic up to about 1.11",
            "q_value_summary": "prior anchor described broad-screen FDR <0.10 for acute and some chronic FDR <0.05",
            "robustness_summary": "promising but not locally reproducible as exact original rows",
            "artifact_sensitivity": "high concern because lead rows involved eyes-open frontal/temporal/global features",
            "batch_or_identity_caveat": "chronic branch is separate and batch-sensitive",
            "interpretation": "historical signal discovery anchor only",
            "supports_candidate": "weak_initial_signal",
            "weakens_candidate": "exact original rows unavailable; artifact-controlled rerun attenuated",
            "manuscript_use": "background/rationale only, not a confirmatory result",
            "source_files": "reports/28_d1_d3_post_analysis_audit.md; C:/Users/gbp34/Downloads/D1_D2_D3_AI_execution_prompt.md",
        },
        {
            "evidence_stream": "D1 artifact-trimmed acute mTBI",
            "dataset": "ds003522",
            "task_or_state": "resting, eyes-open and eyes-closed broad family",
            "group_or_comparison": "acute mTBI vs control",
            "feature_family": "aperiodic/spectral/entropy families",
            "primary_metric": "minimum broad Benjamini-Hochberg FDR q after ptp95 trim",
            "effect_size_summary": "top effects remain moderate in places but attenuated relative to prior anchor",
            "q_value_summary": f"min broad q={d1_q}",
            "robustness_summary": "does not survive broad artifact-controlled FDR",
            "artifact_sensitivity": "artifact-sensitive; proxy adjustment median attenuation about 0.09681 across estimable top models",
            "batch_or_identity_caveat": "acute comparison cleaner than chronic; no acute/chronic pooling",
            "interpretation": "null-leaning after artifact control",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "primary cautionary result",
            "source_files": "outputs/qc/final_result_consistency_checks.csv; outputs/qc/d1_d3_audit_checks.csv; reports/28_d1_d3_post_analysis_audit.md",
        },
        {
            "evidence_stream": "D1 strict artifact-clean branch",
            "dataset": "ds003522",
            "task_or_state": "resting, strict 250 uV branch",
            "group_or_comparison": "acute mTBI vs control",
            "feature_family": "all planned D1 features",
            "primary_metric": "recording-condition retention and group-model feasibility",
            "effect_size_summary": "not_available",
            "q_value_summary": "not_available",
            "robustness_summary": "strict branch retained too few recording-condition rows for group modeling",
            "artifact_sensitivity": "shows that very strict peak-to-peak filtering is overconservative for these files",
            "batch_or_identity_caveat": "sample-composition distortion prevents inference",
            "interpretation": "quality-control branch, not interpretable as a group result",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "artifact-control limitation and sensitivity note",
            "source_files": "outputs/qc/d1_d3_artifact_branch_sample_counts.csv; reports/28_d1_d3_post_analysis_audit.md",
        },
        {
            "evidence_stream": "D3 eyes-closed alpha/IAF",
            "dataset": "ds003522",
            "task_or_state": "eyes-closed posterior alpha/IAF branch",
            "group_or_comparison": "acute mTBI vs control",
            "feature_family": "alpha power, alpha peak, IAF-adjacent features",
            "primary_metric": "posterior acute minimum FDR q",
            "effect_size_summary": "weak exploratory rows only; no aperiodic-adjusted alpha peak metric in generated D3 table",
            "q_value_summary": f"posterior acute min q={d3_q}",
            "robustness_summary": "does not rescue the D1 signal",
            "artifact_sensitivity": "less eyes-open artifact exposure but not supportive",
            "batch_or_identity_caveat": "same ds003522 cohort; not independent",
            "interpretation": "null/non-supportive",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "negative sensitivity endpoint",
            "source_files": "outputs/qc/final_result_consistency_checks.csv; outputs/features/d3_ec_alpha_iaf_features.csv; reports/28_d1_d3_post_analysis_audit.md",
        },
        {
            "evidence_stream": "chronic TBI exploratory branch",
            "dataset": "ds003522",
            "task_or_state": "resting, artifact-trimmed",
            "group_or_comparison": "chronic TBI vs control",
            "feature_family": "aperiodic/spectral/entropy families",
            "primary_metric": "minimum broad FDR q after artifact trim",
            "effect_size_summary": "larger nominal effects in several eyes-open rows",
            "q_value_summary": f"min broad q={chronic_q}",
            "robustness_summary": "does not survive broad FDR and remains secondary",
            "artifact_sensitivity": "batch-sensitive; chronic proxy rows differ more in some temporal/frontal checks",
            "batch_or_identity_caveat": "separate recruitment/batch context; not proof for acute mTBI",
            "interpretation": "exploratory context only",
            "supports_candidate": "weak_context_only",
            "weakens_candidate": "batch caveat prevents proof",
            "manuscript_use": "separate exploratory subsection",
            "source_files": "outputs/qc/final_result_consistency_checks.csv; reports/28_d1_d3_post_analysis_audit.md",
        },
        {
            "evidence_stream": "ds003490 pipeline rehearsal",
            "dataset": "ds003490",
            "task_or_state": "rest/oddball rehearsal",
            "group_or_comparison": "non-TBI comparator only",
            "feature_family": "MNE/event/rest/alpha/aperiodic readiness",
            "primary_metric": "readability and event/feature feasibility",
            "effect_size_summary": "not_applicable",
            "q_value_summary": "not_applicable",
            "robustness_summary": "75 .set/.fdt pairs verified; MNE/event parsing rehearsed",
            "artifact_sensitivity": "pipeline rehearsal only",
            "batch_or_identity_caveat": "not a TBI dataset; cannot validate a TBI claim",
            "interpretation": "methods rehearsal/comparator",
            "supports_candidate": "no",
            "weakens_candidate": "not_applicable",
            "manuscript_use": "methods/QC comparator only if needed",
            "source_files": "reports/20_ds003490_full_retrieval_report.md; reports/22_ds003490_feature_readiness_report.md; outputs/d2_cross_task/ds003490_feature_readiness_summary.csv",
        },
        {
            "evidence_stream": "D2 ds005114 DPX cue-baseline",
            "dataset": "ds005114",
            "task_or_state": "DPX cue-locked baseline",
            "group_or_comparison": "mTBI vs control",
            "feature_family": "alpha/spectral-balance structure",
            "primary_metric": "minimum FDR q and maximum absolute Hedges g",
            "effect_size_summary": f"max abs(g)={dpx_cue_g}",
            "q_value_summary": f"min q={dpx_cue_q}",
            "robustness_summary": "only weak q<0.10 trace in D2; context-specific",
            "artifact_sensitivity": "does not override D1/D3 artifact sensitivity",
            "batch_or_identity_caveat": "overlapping Original_IDs across D2 tasks; not independent cohort evidence",
            "interpretation": "weak/context-specific supportive trace",
            "supports_candidate": "weak_partial",
            "weakens_candidate": "insufficient alone",
            "manuscript_use": "bounded falsification result, not validation",
            "source_files": "outputs/d2_cross_task/d2_within_dataset_group_effects.csv; reports/35_d2_bounded_falsification_report.md",
        },
        {
            "evidence_stream": "D2 ds005114 task-average",
            "dataset": "ds005114",
            "task_or_state": "DPX task-average",
            "group_or_comparison": "mTBI vs control",
            "feature_family": "harmonized D2 spectral features",
            "primary_metric": "task-average minimum FDR q",
            "effect_size_summary": "max abs(g)=0.4955 in summary table",
            "q_value_summary": f"task-average min q={dpx_task_q}",
            "robustness_summary": "directional but non-FDR-supportive",
            "artifact_sensitivity": "does not rescue artifact-sensitive D1",
            "batch_or_identity_caveat": "same D2 subject identity framework; task-average not independent confirmation",
            "interpretation": "weakens robust convergence narrative",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "negative/generalization check",
            "source_files": "outputs/d2_cross_task/d2_falsification_summary.csv; reports/35_d2_bounded_falsification_report.md",
        },
        {
            "evidence_stream": "D2 ds003523 VWM task-average",
            "dataset": "ds003523",
            "task_or_state": "visual working memory task-average",
            "group_or_comparison": "mTBI vs control",
            "feature_family": "harmonized D2 spectral features",
            "primary_metric": "task-average minimum FDR q",
            "effect_size_summary": "max abs(g)=0.3669 in summary table",
            "q_value_summary": f"task-average min q={vwm_task_q}",
            "robustness_summary": "directional but non-FDR-supportive",
            "artifact_sensitivity": "does not rescue artifact-sensitive D1",
            "batch_or_identity_caveat": "overlap with DPX by Original_ID; not separate cohort proof",
            "interpretation": "does not support robust convergence",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "negative/generalization check",
            "source_files": "outputs/d2_cross_task/d2_falsification_summary.csv; reports/35_d2_bounded_falsification_report.md",
        },
        {
            "evidence_stream": "D2 mixed-effects models",
            "dataset": "ds005114+ds003523",
            "task_or_state": "DPX and VWM integrated model",
            "group_or_comparison": "mTBI vs control with task terms",
            "feature_family": "harmonized D2 spectral features",
            "primary_metric": "number of group terms below q<0.10",
            "effect_size_summary": "not_available",
            "q_value_summary": f"group terms q<0.10 count={mixed_zero}",
            "robustness_summary": "27 MixedLM completed and 21 clustered OLS fallbacks; no group reference-task term below q<0.10",
            "artifact_sensitivity": "does not rescue D1",
            "batch_or_identity_caveat": "modeling is numerically fragile for part of feature family",
            "interpretation": "no robust cross-task group convergence",
            "supports_candidate": "no",
            "weakens_candidate": "yes",
            "manuscript_use": "bounded falsification result",
            "source_files": "outputs/d2_cross_task/d2_mixed_effects_models.csv; reports/35_d2_bounded_falsification_report.md",
        },
        {
            "evidence_stream": "D2 within-subject stability/direction consistency",
            "dataset": "ds005114+ds003523",
            "task_or_state": "DPX/VWM task-average rank-order and direction checks",
            "group_or_comparison": "same Original_IDs across tasks",
            "feature_family": "harmonized D2 spectral features",
            "primary_metric": "direction match rate and stability q counts",
            "effect_size_summary": "direction match rates: DPX 0.7708, VWM 0.6458; high rank-order stability in selected features",
            "q_value_summary": "76 stability rows q<0.10; this is measurement stability, not disease-specific convergence",
            "robustness_summary": "supports cross-task feature measurement consistency but not a disease claim",
            "artifact_sensitivity": "descriptive only; no D1 rescue",
            "batch_or_identity_caveat": "same participants by Original_ID, so this is within-person stability",
            "interpretation": "useful reliability context, not group confirmation",
            "supports_candidate": "measurement_only",
            "weakens_candidate": "does not support disease specificity",
            "manuscript_use": "methods/reliability context",
            "source_files": "outputs/d2_cross_task/d2_direction_consistency.csv; outputs/d2_cross_task/d2_within_subject_stability.csv; reports/35_d2_bounded_falsification_report.md",
        },
    ]


def build_claims(values: dict[str, str]) -> list[dict]:
    return [
        {
            "claim_id": "C01",
            "claim_text": "The artifact-controlled acute mTBI resting signal is not FDR-surviving.",
            "claim_strength": "supported negative result",
            "source_report": "reports/28_d1_d3_post_analysis_audit.md",
            "source_table": "outputs/qc/final_result_consistency_checks.csv",
            "source_rows_or_filter": "check_name=d1_acute_broad_min_q",
            "numeric_values": f"acute broad min q={values['d1_acute_broad_min_q']}",
            "caveats": "Broad family includes EO/EC, six regions, and D1 features; nominal rows do not override FDR.",
            "allowed_language": "acute mTBI vs control did not survive broad artifact-controlled FDR",
            "forbidden_overclaim_to_avoid": "positive diagnostic or clinical-utility marker claim",
        },
        {
            "claim_id": "C02",
            "claim_text": "The D1 candidate is artifact-sensitive.",
            "claim_strength": "supported caution",
            "source_report": "reports/28_d1_d3_post_analysis_audit.md",
            "source_table": "outputs/qc/d1_d3_key_effect_trace.csv; outputs/d1_artifact_control/ds003522_artifact_sensitivity.csv",
            "source_rows_or_filter": "acute artifact_trim_ptp95 rows and artifact-sensitivity labels",
            "numeric_values": "artifact proxy median attenuation about 0.09681; 449 stable and 31 changed/unavailable artifact-sensitivity rows",
            "caveats": "Artifact proxies are imperfect and do not prove artifact causality.",
            "allowed_language": "artifact-sensitive and attenuated under artifact-control checks",
            "forbidden_overclaim_to_avoid": "artifact-free disease signature",
        },
        {
            "claim_id": "C03",
            "claim_text": "D3 does not rescue the signal.",
            "claim_strength": "supported negative result",
            "source_report": "reports/28_d1_d3_post_analysis_audit.md",
            "source_table": "outputs/qc/final_result_consistency_checks.csv",
            "source_rows_or_filter": "check_name=d3_acute_posterior_q",
            "numeric_values": f"posterior acute min q={values['d3_acute_posterior_q']}",
            "caveats": "Generated D3 table lacks aperiodic-adjusted alpha peak metrics.",
            "allowed_language": "eyes-closed alpha/IAF branch did not provide supportive acute evidence",
            "forbidden_overclaim_to_avoid": "alpha/IAF rescue endpoint",
        },
        {
            "claim_id": "C04",
            "claim_text": "Chronic effects are batch-sensitive.",
            "claim_strength": "supported caveat",
            "source_report": "reports/28_d1_d3_post_analysis_audit.md",
            "source_table": "outputs/qc/final_result_consistency_checks.csv",
            "source_rows_or_filter": "check_name=chronic_trim_min_q",
            "numeric_values": f"chronic trimmed min q={values['chronic_trim_min_q']}",
            "caveats": "Chronic branch is secondary and should not be pooled with acute mTBI.",
            "allowed_language": "chronic TBI remains exploratory and batch-sensitive",
            "forbidden_overclaim_to_avoid": "proof of acute mTBI effect from chronic branch",
        },
        {
            "claim_id": "C05",
            "claim_text": "D2 is partial/inconsistent.",
            "claim_strength": "supported bounded interpretation",
            "source_report": "reports/35_d2_bounded_falsification_report.md",
            "source_table": "outputs/d2_cross_task/d2_falsification_summary.csv",
            "source_rows_or_filter": "summary_level=overall_d2",
            "numeric_values": "overall min q=0.08979556263104832; mixed group q<0.10 count=0",
            "caveats": "D2 datasets overlap by Original_ID and do not constitute an independent cohort.",
            "allowed_language": "partial/inconsistent bounded cross-task support",
            "forbidden_overclaim_to_avoid": "independent confirmation",
        },
        {
            "claim_id": "C06",
            "claim_text": "DPX cue-baseline has the only weak q<0.10 trace.",
            "claim_strength": "supported weak positive trace",
            "source_report": "reports/35_d2_bounded_falsification_report.md",
            "source_table": "outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
            "source_rows_or_filter": "dataset_id=ds005114 and task_window=cue_locked_baseline_2s",
            "numeric_values": f"min q={values['ds005114_cue_baseline_min_q']}; max abs(g)={values['ds005114_cue_baseline_max_abs_g']}",
            "caveats": "Exploratory q<0.10 trace is not a robust endpoint.",
            "allowed_language": "weak/context-specific DPX cue-baseline trace",
            "forbidden_overclaim_to_avoid": "confirmed replication or validated biomarker",
        },
        {
            "claim_id": "C07",
            "claim_text": "VWM and mixed models do not confirm convergence.",
            "claim_strength": "supported negative result",
            "source_report": "reports/35_d2_bounded_falsification_report.md",
            "source_table": "outputs/d2_cross_task/d2_falsification_summary.csv; outputs/d2_cross_task/d2_mixed_effects_models.csv",
            "source_rows_or_filter": "dataset_task_average ds003523; mixed model group q count",
            "numeric_values": f"VWM task-average min q={values['vwm_task_average_min_q']}; mixed group q<0.10 count={values['mixed_models_group_q_lt_0p10']}",
            "caveats": "Mixed models were numerically fragile for a subset of features.",
            "allowed_language": "VWM and mixed models do not support robust convergence",
            "forbidden_overclaim_to_avoid": "cross-task validation",
        },
        {
            "claim_id": "C08",
            "claim_text": "ds003490 is pipeline comparator only.",
            "claim_strength": "supported scope guardrail",
            "source_report": "reports/22_ds003490_feature_readiness_report.md",
            "source_table": "outputs/d2_cross_task/ds003490_feature_readiness_summary.csv",
            "source_rows_or_filter": "dataset_id=ds003490",
            "numeric_values": "75 .set/.fdt pairs; MNE/event readiness outputs created",
            "caveats": "Dataset is not a TBI validation cohort.",
            "allowed_language": "comparator/pipeline rehearsal dataset",
            "forbidden_overclaim_to_avoid": "TBI validation evidence",
        },
        {
            "claim_id": "C09",
            "claim_text": "No validated biomarker claim is supported.",
            "claim_strength": "supported guardrail",
            "source_report": "reports/36_integrated_d1_d2_d3_final_decision_report.md",
            "source_table": "outputs/qc/final_result_consistency_checks.csv",
            "source_rows_or_filter": "all critical checks pass with null/artifact-sensitive interpretation",
            "numeric_values": "D1 q=0.7876; D3 q=0.9149; D2 mixed group q<0.10 count=0",
            "caveats": "Future prospective, preregistered data could change the conclusion.",
            "allowed_language": "no marker-validation claim is supported",
            "forbidden_overclaim_to_avoid": "validated biomarker; diagnostic biomarker; confirmed biomarker",
        },
        {
            "claim_id": "C10",
            "claim_text": "The most honest manuscript framing is an artifact-sensitivity/null-leaning reproducibility report or transparent signal-discovery/falsification report.",
            "claim_strength": "recommendation",
            "source_report": "reports/36_integrated_d1_d2_d3_final_decision_report.md",
            "source_table": "outputs/final/d1_d2_d3_evidence_matrix.csv",
            "source_rows_or_filter": "all evidence streams",
            "numeric_values": "see C01-C09",
            "caveats": "Not a manuscript-writing phase; human scientific review remains required.",
            "allowed_language": "transparent public EEG signal-discovery and falsification report",
            "forbidden_overclaim_to_avoid": "positive diagnostic/prognostic narrative",
        },
    ]


def artifact_type(path: Path) -> str:
    if path.suffix.lower() == ".md":
        return "report"
    if path.suffix.lower() == ".csv":
        return "csv"
    if path.suffix.lower() == ".json":
        return "json"
    if path.suffix.lower() in {".py", ".yml", ".yaml"}:
        return "code_or_config"
    if "logs" in path.parts:
        return "log"
    return path.suffix.lower().lstrip(".") or "file"


def phase_for(path: Path) -> str:
    r = rel(path)
    if "/final/" in r or r.startswith("reports/39") or r.startswith("reports/40") or r.startswith("reports/41"):
        return "final_consolidation"
    if "d1_artifact_control" in r or "d3_eyes_closed_alpha" in r or "d1_d3" in r or "d3_" in r:
        return "D1_D3"
    if "d2_cross_task" in r or "ds005114" in r or "ds003523" in r:
        return "D2"
    if "ds003490" in r:
        return "ds003490_rehearsal"
    if "download_recovery" in r or "raw_download" in r:
        return "raw_data_verification"
    if "stale" in r or "audit_gate" in r or "AUDIT_PASS" in r:
        return "stale_repair_audit"
    if r.startswith("scripts/"):
        return "script"
    if r.startswith("logs/"):
        return "log"
    return "supporting"


def build_manifest() -> list[dict]:
    explicit = [
        "reports/39_final_analysis_package_integrity_report.md",
        "reports/40_final_scientific_synthesis_and_publishability_report.md",
        "reports/41_reproduction_and_handoff_guide.md",
        "outputs/final/d1_d2_d3_evidence_matrix.csv",
        "outputs/final/key_result_claims_traceability.csv",
        "outputs/final/final_deliverable_manifest.csv",
        "reports/24_d1_d3_integrated_artifact_control_report.md",
        "reports/28_d1_d3_post_analysis_audit.md",
        "reports/29_next_step_decision_after_d1_d3.md",
        "reports/30_d2_prespecified_falsification_plan.md",
        "reports/32_d2_download_verification_report.md",
        "reports/33_d2_subject_overlap_report.md",
        "reports/34_d2_harmonized_feature_extraction_report.md",
        "reports/35_d2_bounded_falsification_report.md",
        "reports/36_integrated_d1_d2_d3_final_decision_report.md",
        "reports/37_stale_parallel_job_accuracy_audit.md",
        "reports/38_stale_report_repair_log.md",
        "reports/16_updated_final_recommendation.md",
        "reports/11_d1_d2_d3_continuation_status.md",
    ]
    patterns = [
        "outputs/d1_artifact_control/*.csv",
        "outputs/d3_eyes_closed_alpha/*.csv",
        "outputs/qc/*.csv",
        "outputs/qc/*.json",
        "outputs/qc/*.ok",
        "outputs/d2_cross_task/*.csv",
        "outputs/download_recovery/*.csv",
        "outputs/features/*.csv",
        "outputs/models/*.csv",
        "outputs/metadata/config_snapshot_*",
        "outputs/metadata/dataset_inventory.csv",
        "outputs/metadata/subject_crosswalk.csv",
        "outputs/metadata/subject_overlap_matrix.csv",
        "scripts/*.py",
        "scripts/utils/*.py",
        "logs/run_log.jsonl",
        "logs/software_versions.json",
    ]
    paths: dict[str, Path] = {}
    for item in explicit:
        paths[item] = PROJECT / item
    for pattern in patterns:
        for p in PROJECT.glob(pattern):
            paths[rel(p)] = p
    final_sources = {
        "reports/39_final_analysis_package_integrity_report.md",
        "reports/40_final_scientific_synthesis_and_publishability_report.md",
        "reports/41_reproduction_and_handoff_guide.md",
        "outputs/final/d1_d2_d3_evidence_matrix.csv",
        "outputs/final/key_result_claims_traceability.csv",
        "reports/28_d1_d3_post_analysis_audit.md",
        "reports/35_d2_bounded_falsification_report.md",
        "reports/36_integrated_d1_d2_d3_final_decision_report.md",
        "reports/37_stale_parallel_job_accuracy_audit.md",
        "reports/38_stale_report_repair_log.md",
        "outputs/qc/final_result_consistency_checks.csv",
        "outputs/qc/audit_gate.json",
        "outputs/d2_cross_task/d2_falsification_summary.csv",
        "outputs/download_recovery/d2_raw_download_summary.csv",
        "outputs/download_recovery/ds003522_post_download_verification.csv",
        "outputs/download_recovery/ds003490_full_retrieval_verification.csv",
    }
    rows = []
    for key in sorted(paths):
        p = paths[key]
        exists = p.exists()
        stat = p.stat() if exists else None
        rows.append(
            {
                "artifact_path": key,
                "artifact_type": artifact_type(p),
                "phase": phase_for(p),
                "description": describe_artifact(key),
                "exists": exists,
                "size_bytes": stat.st_size if stat else "",
                "modified_time": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds") if stat else "",
                "used_in_final_synthesis": key in final_sources or key.startswith("outputs/final/"),
                "notes": "" if exists else "missing at consolidation time",
            }
        )
    return rows


def describe_artifact(key: str) -> str:
    descriptions = {
        "reports/39_final_analysis_package_integrity_report.md": "Final package integrity and QC handoff report.",
        "reports/40_final_scientific_synthesis_and_publishability_report.md": "Final decision-grade scientific synthesis and publishability assessment.",
        "reports/41_reproduction_and_handoff_guide.md": "Reproduction and handoff guide for humans or future agents.",
        "outputs/final/d1_d2_d3_evidence_matrix.csv": "One-row-per-evidence-stream final evidence matrix.",
        "outputs/final/key_result_claims_traceability.csv": "Claim-level traceability table tying synthesis claims to source outputs.",
        "outputs/final/final_deliverable_manifest.csv": "Final deliverable manifest with existence, size, and source-use flags.",
    }
    if key in descriptions:
        return descriptions[key]
    if "d1_artifact_control" in key or "d3_eyes_closed_alpha" in key or "d1_d3" in key:
        return "D1/D3 analysis, QC, or audit artifact."
    if "d2_cross_task" in key:
        return "D2 bounded cross-task extraction, QC, model, or falsification artifact."
    if "download_recovery" in key:
        return "Raw-data retrieval or verification artifact."
    if "ds003490" in key:
        return "ds003490 comparator/pipeline rehearsal artifact."
    if "stale" in key or "audit_gate" in key or "AUDIT_PASS" in key:
        return "Stale-report repair or audit-gate artifact."
    if key.startswith("scripts/"):
        return "Project script used for verification, extraction, modeling, audit, or consolidation."
    if key.startswith("logs/"):
        return "Execution log or software/version log."
    return "Supporting project artifact."


def status_report(values: dict[str, str], gate: dict) -> str:
    generated = now_iso()
    return f"""
# D1 D2 D3 Continuation Status

Generated: {generated}

## Status Summary

| item | status | note |
| --- | --- | --- |
| Audit gate | PASS | `outputs/qc/audit_gate.json` reports `PASS`, `safe_to_continue=true`, and `next_prompt_allowed=true`; `AUDIT_PASS.ok` exists and no fail marker exists. |
| Stale report repair | complete | Reports 32-36, 16, and 11 were repaired from authoritative outputs and backed up under `reports/stale_parallel_backup_20260613_184839/`. |
| Final consolidation | complete | Reports 39-41 and final CSV handoff artifacts were generated from existing outputs only. |
| ds003490 | complete comparator | Retrieved and rehearsed; not used as TBI evidence. |
| ds003522 | complete for D1/D3 | Retrieved, verified, and D1/D3 artifact-control analyses completed. |
| ds005114 | complete for D2 | Retrieved, verified, and included in bounded D2 outputs. |
| ds003523 | complete for D2 | Retrieved, verified, and included in bounded D2 outputs. |
| D2 models | complete bounded check | Partial/inconsistent cross-task support; no standalone cohort-confirmation claim. |

## Final Decision Boundary

This is the final consolidated analysis package unless additional analyses are explicitly requested. No downloads, raw-data modification, feature extraction, or statistical-model reruns were performed during final consolidation.

## Current D1/D2/D3 Decision

| domain | final status | key value |
| --- | --- | --- |
| D1 acute broad artifact-controlled family | null-leaning | min q = {fmt_num(values['d1_acute_broad_min_q'])} |
| D1 narrow prior-anchor family | exploratory, non-confirmatory | q = {fmt_num(values['d1_narrow_prior_anchor_q'])} |
| D3 posterior alpha/IAF | non-supportive | min q = {fmt_num(values['d3_acute_posterior_q'])} |
| Chronic TBI branch | exploratory, batch-sensitive | min q = {fmt_num(values['chronic_trim_min_q'])} |
| D2 DPX cue-baseline | weak/context-specific trace | min q = {fmt_num(values['ds005114_cue_baseline_min_q'])}; max abs(g) = {fmt_num(values['ds005114_cue_baseline_max_abs_g'])} |
| D2 task-average/mixed models | non-confirmatory | DPX task-average q = {fmt_num(values['dpx_task_average_min_q'])}; VWM task-average q = {fmt_num(values['vwm_task_average_min_q'])}; mixed group q<0.10 count = {values['mixed_models_group_q_lt_0p10']} |

## Final Outputs

- `reports/39_final_analysis_package_integrity_report.md`
- `reports/40_final_scientific_synthesis_and_publishability_report.md`
- `reports/41_reproduction_and_handoff_guide.md`
- `outputs/final/d1_d2_d3_evidence_matrix.csv`
- `outputs/final/key_result_claims_traceability.csv`
- `outputs/final/final_deliverable_manifest.csv`
"""


def recommendation_report(values: dict[str, str]) -> str:
    generated = now_iso()
    return f"""
# Updated Final Recommendation

Generated: {generated}

## Recommendation

Treat the package as a final, decision-grade analysis handoff: the evidence supports a cautious artifact-sensitivity/null-leaning reproducibility or signal-discovery/falsification report, not a positive marker narrative. Human review can now focus on whether the transparent negative/mixed result is worth writing up and how conservative the manuscript framing should be.

## Current Evidence State

| evidence area | result | interpretation |
| --- | --- | --- |
| D1 acute resting artifact-controlled family | min q = {fmt_num(values['d1_acute_broad_min_q'])} | Does not survive broad artifact-controlled FDR. |
| D1 narrow prior-anchor family | q = {fmt_num(values['d1_narrow_prior_anchor_q'])} | Exploratory and non-confirmatory. |
| D3 posterior alpha/IAF | min q = {fmt_num(values['d3_acute_posterior_q'])} | Does not rescue the acute signal. |
| Chronic TBI branch | min q = {fmt_num(values['chronic_trim_min_q'])} | Separate, exploratory, and batch-sensitive. |
| D2 DPX cue-baseline | min q = {fmt_num(values['ds005114_cue_baseline_min_q'])}; max abs(g) = {fmt_num(values['ds005114_cue_baseline_max_abs_g'])} | Only weak q<0.10 trace; context-specific. |
| D2 task-average and mixed models | DPX q = {fmt_num(values['dpx_task_average_min_q'])}; VWM q = {fmt_num(values['vwm_task_average_min_q'])}; mixed group q<0.10 count = {values['mixed_models_group_q_lt_0p10']} | Does not show robust cross-task convergence. |

## Manuscript Path

The strongest honest manuscript path is a transparent public OpenNeuro EEG analysis showing how an initially promising TBI EEG candidate attenuates under artifact control and bounded cross-task falsification. Acute mTBI vs control should remain the primary comparison; chronic TBI should remain separate; D2 should be described as overlapping-subject cross-task evidence; and `ds003490` should remain a comparator/pipeline rehearsal dataset only.

## Guardrails

- Do not frame this as marker validation or clinical utility.
- Do not use chronic TBI as proof for acute mTBI.
- Do not use `ds003490` as TBI support.
- Do not pool overlapping D2 task records as independent people.
- Do not attempt a classifier-based rescue without a new preregistered design.
"""


def integrity_report(values: dict[str, str], gate: dict, manifest_rows: list[dict], raws: dict[str, dict]) -> str:
    generated = now_iso()
    existing = sum(1 for r in manifest_rows if r["exists"])
    missing = [r for r in manifest_rows if not r["exists"]]
    used = sum(1 for r in manifest_rows if str(r["used_in_final_synthesis"]).lower() == "true")
    raw_lines = []
    for dataset_id in ["ds003490", "ds003522", "ds005114", "ds003523"]:
        row = raws.get(dataset_id, {})
        if not row:
            raw_lines.append(f"| {dataset_id} | not_available | not_available | not_available | not_available | not_available | source summary missing |")
            continue
        set_count = row.get("summary_set_count", row.get("set_count", ""))
        fdt_count = row.get("summary_fdt_count", row.get("fdt_count", ""))
        paired = row.get("summary_paired_count", row.get("paired_set_fdt_count", ""))
        missing_count = row.get("summary_missing_fdt_count", row.get("missing_fdt_count", ""))
        mne = row.get("mne_read_pass_count", row.get("mne_files_read_passed", row.get("mne_read_test_status", "")))
        size = row.get("summary_raw_eeg_size_gib", row.get("summary_total_size_gib", row.get("total_set_fdt_size_gib", "")))
        raw_lines.append(f"| {dataset_id} | {set_count} | {fdt_count} | {paired} | {missing_count} | {size} | {mne} |")
    missing_text = "\n".join(
        f"- `{r['artifact_path']}` ({r['notes']})" for r in missing[:20]
    ) or "- No missing files in the final manifest inventory."
    if len(missing) > 20:
        missing_text += f"\n- {len(missing) - 20} additional missing entries omitted from this report; see manifest."
    return f"""
# Final Analysis Package Integrity Report

Generated: {generated}

## Technical Summary

The final package integrity gate is clean. `audit_gate.json` reports `{gate.get('gate')}`, `safe_to_continue={gate.get('safe_to_continue')}`, and `next_prompt_allowed={gate.get('next_prompt_allowed')}`. The stale-report repair has already been completed, backed up, and audited; final consolidation used existing reports/CSVs only and did not rerun extraction, modeling, downloads, or raw-data operations. The preserved scientific stance is artifact-sensitive/null-leaning, with only a weak/context-specific D2 trace.

## Audit Gate Status

| file | status |
| --- | --- |
| `outputs/qc/audit_gate.json` | present; gate = `{gate.get('gate')}` |
| `outputs/qc/AUDIT_PASS.ok` | present |
| `outputs/qc/AUDIT_FAIL.ok` | absent |
| critical failures | {len(gate.get('critical_failures', []))} |
| warnings | {len(gate.get('warnings', []))} |

## Stale-Job Repair Status

The stale-report repair log is `reports/38_stale_report_repair_log.md`; the audit report is `reports/37_stale_parallel_job_accuracy_audit.md`. The backup set is `reports/stale_parallel_backup_20260613_184839/`. The repaired reports were 32-36, 16, and 11, and no machine-readable numeric outputs were modified during the repair.

## Final Files Checked

| artifact group | count |
| --- | ---: |
| manifest rows | {len(manifest_rows)} |
| existing files | {existing} |
| files used directly in final synthesis | {used} |
| missing/noncritical entries | {len(missing)} |

Required final outputs exist and are nonzero after this consolidation:

- `reports/39_final_analysis_package_integrity_report.md`
- `reports/40_final_scientific_synthesis_and_publishability_report.md`
- `reports/41_reproduction_and_handoff_guide.md`
- `outputs/final/d1_d2_d3_evidence_matrix.csv`
- `outputs/final/key_result_claims_traceability.csv`
- `outputs/final/final_deliverable_manifest.csv`

## Deliverable Manifest Summary

The full manifest is `outputs/final/final_deliverable_manifest.csv`. It includes final reports, D1/D3 outputs, D1/D3 audit outputs, D2 outputs, `ds003490` rehearsal outputs, raw-data verification outputs, stale repair/audit outputs, key scripts, config snapshots, and logs.

## Raw Data Verification Summary

| dataset | .set count | .fdt count | paired count | missing pair count | size GiB | MNE/local check |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(raw_lines)}

## Script And Compile Status

Final validation included a lightweight Python compile check for `scripts/24_stale_parallel_job_accuracy_audit.py`, `scripts/25_repair_stale_d2_reports.py`, and `scripts/26_final_analysis_package_consolidation.py`. Extraction and model scripts were not rerun.

## Missing Or Noncritical Files

{missing_text}

## Stale-Text Scan Summary

The repaired audit found no critical stale-text failures. Historical/negated text hits remain documented in `outputs/qc/stale_parallel_job_text_scan.csv`; they were not treated as active current-state claims after repair. The new final reports avoid stale current-state claims such as incomplete D2 status or positive marker validation language.

## Final-Output Consistency Summary

| check | observed |
| --- | --- |
| D1 acute broad min q | {values['d1_acute_broad_min_q']} |
| D1 narrow prior-anchor q | {values['d1_narrow_prior_anchor_q']} |
| D3 posterior alpha/IAF acute min q | {values['d3_acute_posterior_q']} |
| Chronic artifact-trimmed min q | {values['chronic_trim_min_q']} |
| D2 DPX cue-baseline min q | {values['ds005114_cue_baseline_min_q']} |
| D2 DPX cue-baseline max abs(g) | {values['ds005114_cue_baseline_max_abs_g']} |
| D2 DPX task-average min q | {values['dpx_task_average_min_q']} |
| D2 VWM task-average min q | {values['vwm_task_average_min_q']} |
| D2 mixed group q<0.10 count | {values['mixed_models_group_q_lt_0p10']} |

## Human-Review Readiness

The package is ready for human scientific review as a final analysis handoff. It is not a manuscript draft and should not be treated as having established a clinical EEG marker.

## Do Not Modify Without Rerunning Audit

Do not modify machine-readable outputs, repaired reports 32-38, final reports 39-41, final CSVs, or status/recommendation reports without rerunning the stale-job accuracy audit and final validation checks. Any new extraction, model rerun, download, raw-data movement, or numerical table edit should trigger a fresh audit gate before interpretation.
"""


def synthesis_report(values: dict[str, str]) -> str:
    generated = now_iso()
    return f"""
# Final Scientific Synthesis And Publishability Report

Generated: {generated}

## Executive Summary

The completed D1/D2/D3 package supports a cautious, null-leaning interpretation. The acute mTBI resting EEG candidate does not survive broad artifact-controlled FDR, and the narrower prior-anchor family remains exploratory rather than confirmatory. D3 eyes-closed alpha/IAF does not rescue the signal, while D2 provides only a weak/context-specific DPX cue-baseline trace and inconsistent task-average/mixed-model support.

The strongest honest product of this work is not a positive marker story. It is a transparent public EEG analysis showing how an initially promising TBI EEG candidate attenuates under artifact control, batch sensitivity, and bounded cross-task testing.

## Project Scope And Datasets

This package consolidates public OpenNeuro EEG analyses across D1, D2, and D3. `ds003522` is the D1/D3 resting and eyes-closed analysis dataset. `ds005114` and `ds003523` provide D2 bounded cross-task checks using DPX and visual working memory. `ds003490` is a comparator and pipeline rehearsal dataset only; it is not TBI evidence.

Acute mTBI vs control is the cleanest primary comparison. Chronic TBI is kept separate because it is secondary and batch-sensitive. The D2 datasets overlap by `Original_ID`, so D2 should be interpreted as cross-task reproducibility/falsification within an overlapping identity framework, not as a separate cohort test.

## What Was Tested

The analysis tested whether a resting EEG aperiodic/spectral candidate in TBI survives artifact control, eyes-closed alpha/IAF sensitivity, and bounded cross-task checks. The main statistical language is Hedges g for group differences, nominal p-values for local signal inspection, Benjamini-Hochberg FDR q-values for multiplicity control, plus permutation/bootstrap/leave-one-out/artifact-sensitivity summaries where available.

## Original D1 Signal And Why It Looked Promising

The original D1 signal looked promising because the prior execution-prompt anchor described eyes-open temporal/frontal/global aperiodic and spectral differences with acute mTBI effect sizes around abs(g)=0.80-0.96 and broad-screen FDR below q<0.10. Chronic rows were described as larger in places. That was enough to justify a rigorous artifact and cross-task audit.

The limitation is important: exact original Phase 5 per-feature rows were not locally available. The D1/D3 audit therefore used the original prose anchor for comparison and did not pretend to have exact original row-level estimates.

## What Artifact Control Showed

Artifact control changed the interpretation. In the acute mTBI vs control broad artifact-trimmed D1 family, the minimum FDR q was {fmt_num(values['d1_acute_broad_min_q'])}. The narrow prior-anchor family yielded q={fmt_num(values['d1_narrow_prior_anchor_q'])}, but that is a post hoc transparency calculation and should not be treated as a rescued endpoint.

The ptp95 branch preserved recording-condition coverage while trimming high-amplitude epochs. The strict 250 microvolt branch retained too few recording-condition rows for meaningful group modeling. Artifact-proxy checks did not prove the signal is artifact, but they supported caution, especially because the most coherent lead pattern depended on eyes-open frontal/temporal/global features.

## What D3 Eyes-Closed Alpha/IAF Showed

D3 did not rescue the signal. The posterior eyes-closed alpha/IAF acute minimum FDR q was {fmt_num(values['d3_acute_posterior_q'])}. Generated D3 outputs also lacked aperiodic-adjusted alpha peak metrics, so alpha interpretations should remain preliminary.

This matters because D3 was the most natural lower-artifact follow-up to the eyes-open D1 concern. Its non-supportive result weakens a robust spectral-marker interpretation.

## What D2 Bounded Cross-Task Falsification Showed

D2 produced partial/inconsistent support. The only weak q<0.10 trace was in `ds005114` DPX cue-baseline rows, with minimum q={fmt_num(values['ds005114_cue_baseline_min_q'])} and max abs(g)={fmt_num(values['ds005114_cue_baseline_max_abs_g'])}. Generalization was weaker: DPX task-average minimum q={fmt_num(values['dpx_task_average_min_q'])}, VWM task-average minimum q={fmt_num(values['vwm_task_average_min_q'])}, and mixed-effects models had {values['mixed_models_group_q_lt_0p10']} group terms below q<0.10.

Within-subject cross-task stability was high for selected spectral features, but that supports measurement consistency more than disease specificity. Direction consistency is descriptive and does not override D1/D3 artifact sensitivity.

## What ds003490 Contributed

`ds003490` contributed tooling confidence, not TBI evidence. The dataset verified that the pipeline can retrieve paired `.set`/`.fdt` files, parse MNE-readable recordings, read events, and rehearse rest/oddball feature readiness. It should remain labeled as comparator/pipeline rehearsal only.

## What Survived FDR And What Did Not

No D1 acute broad artifact-controlled family survived FDR. The D1 narrow prior-anchor q={fmt_num(values['d1_narrow_prior_anchor_q'])} remains exploratory. D3 posterior alpha/IAF did not survive. Chronic TBI had larger nominal effects in places but still did not survive broad FDR after artifact trim, with minimum q={fmt_num(values['chronic_trim_min_q'])}.

In D2, only the DPX cue-baseline branch produced a weak q<0.10 trace. DPX task-average, VWM task-average, and integrated mixed models did not provide robust convergence.

## Robustness And Sensitivity Interpretation

The analysis is strongest as a falsification and sensitivity exercise. The candidate has a coherent origin and a weak D2 trace, but the full pattern is not robust under broad artifact-controlled FDR, lower-artifact eyes-closed checks, task-average D2 tests, or mixed-model integration. Bootstrap, permutation, leave-one-out, artifact-sensitivity, and stale-report audit outputs support transparency but do not change the bottom line.

## Key Limitations

- Exact original Phase 5 per-feature rows were not locally available.
- The strict artifact-clean branch was overconservative and not usable for group inference.
- The ptp95 branch is a sensitivity approach, not a gold-standard artifact correction.
- D3 lacks aperiodic-adjusted alpha peak metrics in the generated table.
- D2 uses overlapping identities and should not be interpreted as a separate cohort.
- Chronic TBI remains secondary and batch-sensitive.
- `ds003490` is not a TBI validation dataset.

## Novelty Assessment

The novelty is methodological and transparency-oriented: a public EEG TBI candidate is carried through raw-data verification, artifact-control stress testing, eyes-closed sensitivity, bounded cross-task falsification, stale-output audit, and traceable final synthesis. The novelty is weaker if framed as a disease marker discovery, because the core biological signal is not robust enough for that claim.

## Publishability Assessment

The package may be publishable if framed honestly as a transparent reproducibility/falsification or methods/data-resource report. The result is scientifically useful because it shows how a plausible EEG signal weakens under realistic artifact and generalization checks.

It is not ready for a positive clinical marker narrative. A manuscript would need crisp framing, conservative language, clear subject-identity handling, and a willingness to foreground null/mixed results.

## Candidate Manuscript Framings

- Artifact-sensitivity/null-leaning reproducibility report: strongest match to the evidence.
- Transparent OpenNeuro TBI EEG signal-discovery and falsification report: good if the paper emphasizes public data, traceability, and guardrails.
- Methods/data-resource report: plausible if the focus is on a reproducible pipeline and lessons learned from attenuation under artifact control.

## Candidate Journals

| journal | fit | caution |
| --- | --- | --- |
| Neurotrauma Reports | Good fit for transparent TBI-focused null/mixed public-data work. | Needs concise translational framing without overclaiming. |
| Frontiers in Neurology - Neurotrauma | Plausible fit for open, methods-aware neurotrauma analysis. | Must manage article type and avoid a positive-marker tone. |
| Brain Injury | Possible fit if the clinical TBI relevance is made clear. | EEG-methods depth may need careful presentation for the readership. |
| Clinical Neurophysiology | Possible only if methods rigor and EEG technical contribution are strong enough. | Null/mixed TBI story alone may not be sufficient. |
| NeuroImage: Clinical | Possible only with a robust neuroimaging-methods/reproducibility framing. | Current evidence may be too fragile unless the manuscript emphasizes methodology and open-science lessons. |

## What Should Be Avoided

- A positive diagnostic, prognostic, predictive, or clinical-utility narrative.
- Marker-validation language.
- Treating D2 as a separate-cohort proof.
- Using chronic TBI to prove acute mTBI.
- Treating `ds003490` as TBI support.
- Pooling overlapping task records as independent people.
- Classifier-based rescue analyses without a new preregistered design.

## Recommended Next Confirmatory Study

The next confirmatory study should be preregistered, prospective, and designed around acute mTBI vs control. It should define artifact handling before analysis, include eyes-open and eyes-closed endpoints, predefine alpha/aperiodic features, include independent train/test or external validation cohorts, track medication/sleep/injury timing and symptom covariates, and specify whether chronic TBI is excluded or modeled separately. The primary endpoint should be narrow enough to be statistically credible and should include negative-control artifact proxies.

## Final Go/No-Go Recommendation

Go for human review as a transparent null-leaning reproducibility/falsification package. No-go for any positive marker, diagnostic, prognostic, predictive, or clinical-utility claim from the current outputs. If a manuscript is pursued, make the attenuation and inconsistency the point rather than trying to hide it.
"""


def handoff_report(values: dict[str, str]) -> str:
    generated = now_iso()
    return f"""
# Reproduction And Handoff Guide

Generated: {generated}

## Project Directory

`{PROJECT}`

## Environment Setup

Use the project virtual environment:

```powershell
cd "{PROJECT}"
.\\.venv\\Scripts\\python.exe --version
```

The package also used DataLad/git-annex for OpenNeuro retrieval and Deno/OpenNeuro CLI as supporting tooling. Deno/OpenNeuro CLI helped with authentication and metadata/tooling checks, but DataLad/git-annex was required for successful raw EEG retrieval.

## Required Tools

- Python virtual environment: `.\\.venv\\Scripts\\python.exe`
- DataLad: `.\\.venv\\Scripts\\datalad.exe`
- git-annex: available through the project toolchain
- OpenNeuro special remote helper: required for annex retrieval
- Deno/OpenNeuro CLI: supporting tool only, not the successful bulk retriever

## Dataset Retrieval Summary

| dataset | role | retrieval status |
| --- | --- | --- |
| ds003490 | comparator/pipeline rehearsal | full retrieval verified: 75 `.set`, 75 `.fdt`, 75 pairs |
| ds003522 | D1/D3 raw EEG | retrieval verified: 200 `.set`, 200 `.fdt`, 200 pairs |
| ds005114 | D2 DPX | retrieval verified: 223 `.set`, 223 `.fdt`, 223 pairs |
| ds003523 | D2 visual working memory | retrieval verified: 221 `.set`, 221 `.fdt`, 221 pairs |

## Raw-Data Verification Summary

Verification outputs are stored under `outputs/download_recovery/`. MNE read-tests passed for sampled recordings in ds003522, ds005114, and ds003523; ds003490 MNE/event readiness was completed as comparator rehearsal.

## Script Execution Order

Use this order only when intentionally reproducing from verified raw data. Do not run heavy scripts casually after final consolidation.

```powershell
.\\.venv\\Scripts\\python.exe scripts\\13_verify_ds003522_after_download.py
.\\.venv\\Scripts\\python.exe scripts\\14_d1_artifact_control_analysis.py
.\\.venv\\Scripts\\python.exe scripts\\15_d3_eyes_closed_alpha_iaf_analysis.py
.\\.venv\\Scripts\\python.exe scripts\\16_d1_d3_integrated_report.py
.\\.venv\\Scripts\\python.exe scripts\\19_d1_d3_post_analysis_audit.py
.\\.venv\\Scripts\\python.exe scripts\\20_verify_d2_downloads.py
.\\.venv\\Scripts\\python.exe scripts\\21_extract_d2_harmonized_features.py
.\\.venv\\Scripts\\python.exe scripts\\22_run_d2_falsification_models.py
.\\.venv\\Scripts\\python.exe scripts\\23_generate_d2_report.py
.\\.venv\\Scripts\\python.exe scripts\\24_stale_parallel_job_accuracy_audit.py
.\\.venv\\Scripts\\python.exe scripts\\26_final_analysis_package_consolidation.py
```

## Heavy Scripts And Runtime Notes

Raw retrieval and feature extraction are the expensive steps. Do not rerun `datalad get`, raw EEG downloads, D1/D3 extraction, D2 extraction, or D2 models unless the goal is explicit reproduction. The final consolidation script is lightweight and reads existing CSV/report outputs only.

## Final Output Locations

- `reports/39_final_analysis_package_integrity_report.md`
- `reports/40_final_scientific_synthesis_and_publishability_report.md`
- `reports/41_reproduction_and_handoff_guide.md`
- `outputs/final/d1_d2_d3_evidence_matrix.csv`
- `outputs/final/key_result_claims_traceability.csv`
- `outputs/final/final_deliverable_manifest.csv`

## Rerun The Stale-Job Audit

```powershell
.\\.venv\\Scripts\\python.exe scripts\\24_stale_parallel_job_accuracy_audit.py
```

Continue only if `outputs/qc/audit_gate.json` reports `PASS`, `outputs/qc/AUDIT_PASS.ok` exists, and `outputs/qc/AUDIT_FAIL.ok` is absent.

## Rerun Final Consolidation

```powershell
.\\.venv\\Scripts\\python.exe scripts\\26_final_analysis_package_consolidation.py
```

This script verifies the audit gate first and stops if the gate is not clean.

## Avoid Subject Leakage

Use `Original_ID` and stable-person crosswalks when interpreting D2. Do not treat repeated sessions or tasks from the same person as independent people. Do not describe DPX and VWM as separate cohorts.

## Avoid Overclaiming

Use conservative language: artifact-sensitive, null-leaning, exploratory, bounded falsification, weak/context-specific trace, and non-confirmatory. Avoid clinical marker language, standalone cohort-confirmation language, and any claim that D2 validates D1.

## Resume If Raw Data Are Moved

If raw data are moved, update local paths carefully, rerun raw verification scripts without downloading, then rerun the stale-job audit. Do not edit machine-readable result CSVs by hand to match moved paths unless a script explicitly regenerates path-only metadata.

## Disk-Space Expectations

The raw EEG data occupy tens of GiB: ds003522 about 25.35 GiB for paired `.set`/`.fdt`, ds005114 about 55.86 GiB raw EEG, and ds003523 about 37.53 GiB raw EEG. Keep additional workspace room for intermediate features, logs, and backups.

## Known Caveats

- Original D1 exact per-feature rows were unavailable locally.
- Strict artifact-clean filtering was too conservative for group inference.
- D2 overlaps by identity and is not an external cohort.
- Chronic TBI is batch-sensitive and secondary.
- `ds003490` is a comparator only.
- The current final recommendation depends on the repaired audit gate remaining clean.

## Recommended Human-Review Checklist

- Confirm the final evidence matrix matches the intended scientific stance.
- Check every manuscript-intended claim against `outputs/final/key_result_claims_traceability.csv`.
- Decide whether the target paper is a reproducibility/falsification report, methods/data-resource report, or no manuscript.
- Keep acute and chronic results separated.
- Re-run `scripts/24_stale_parallel_job_accuracy_audit.py` after any file edits that change current-state interpretation.
"""


def validate_final_reports() -> None:
    forbidden = [
        "ds003523 pending",
        "D2 remains unstarted",
        "D2 extraction not started",
        "validated biomarker",
        "diagnostic biomarker",
        "confirmed biomarker",
        "independent confirmation",
    ]
    report_paths = [
        REPORTS / "39_final_analysis_package_integrity_report.md",
        REPORTS / "40_final_scientific_synthesis_and_publishability_report.md",
        REPORTS / "41_reproduction_and_handoff_guide.md",
    ]
    for path in report_paths:
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        hits = [phrase for phrase in forbidden if phrase.lower() in lower]
        if hits:
            raise SystemExit(f"Forbidden stale/overclaim phrase in {rel(path)}: {hits}")
        if "artifact-sensitive" not in lower and "null-leaning" not in lower:
            raise SystemExit(f"Final report does not preserve null/artifact-sensitive framing: {rel(path)}")


def main() -> None:
    gate = require_clean_gate()
    FINAL.mkdir(parents=True, exist_ok=True)
    values = consistency_values()
    raws = raw_summary()

    evidence_rows = build_evidence_matrix(values)
    evidence_columns = [
        "evidence_stream",
        "dataset",
        "task_or_state",
        "group_or_comparison",
        "feature_family",
        "primary_metric",
        "effect_size_summary",
        "q_value_summary",
        "robustness_summary",
        "artifact_sensitivity",
        "batch_or_identity_caveat",
        "interpretation",
        "supports_candidate",
        "weakens_candidate",
        "manuscript_use",
        "source_files",
    ]
    write_csv(FINAL / "d1_d2_d3_evidence_matrix.csv", evidence_rows, evidence_columns)

    claims_rows = build_claims(values)
    claims_columns = [
        "claim_id",
        "claim_text",
        "claim_strength",
        "source_report",
        "source_table",
        "source_rows_or_filter",
        "numeric_values",
        "caveats",
        "allowed_language",
        "forbidden_overclaim_to_avoid",
    ]
    write_csv(FINAL / "key_result_claims_traceability.csv", claims_rows, claims_columns)

    write_text(REPORTS / "40_final_scientific_synthesis_and_publishability_report.md", synthesis_report(values))
    write_text(REPORTS / "41_reproduction_and_handoff_guide.md", handoff_report(values))
    write_text(REPORTS / "11_d1_d2_d3_continuation_status.md", status_report(values, gate))
    write_text(REPORTS / "16_updated_final_recommendation.md", recommendation_report(values))

    manifest_rows = build_manifest()
    manifest_columns = [
        "artifact_path",
        "artifact_type",
        "phase",
        "description",
        "exists",
        "size_bytes",
        "modified_time",
        "used_in_final_synthesis",
        "notes",
    ]
    write_csv(FINAL / "final_deliverable_manifest.csv", manifest_rows, manifest_columns)

    # Rebuild manifest after it exists so its row is nonzero/current, then write the integrity report.
    manifest_rows = build_manifest()
    write_csv(FINAL / "final_deliverable_manifest.csv", manifest_rows, manifest_columns)
    write_text(REPORTS / "39_final_analysis_package_integrity_report.md", integrity_report(values, gate, manifest_rows, raws))

    # One final manifest refresh captures report 39 size/time after it exists.
    manifest_rows = build_manifest()
    write_csv(FINAL / "final_deliverable_manifest.csv", manifest_rows, manifest_columns)
    validate_final_reports()

    LOGS.mkdir(exist_ok=True)
    log_entry = {
        "timestamp": now_iso(),
        "event": "final_analysis_package_consolidation",
        "status": "complete",
        "audit_gate": gate.get("gate"),
        "created": [
            "reports/39_final_analysis_package_integrity_report.md",
            "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "reports/41_reproduction_and_handoff_guide.md",
            "outputs/final/d1_d2_d3_evidence_matrix.csv",
            "outputs/final/key_result_claims_traceability.csv",
            "outputs/final/final_deliverable_manifest.csv",
        ],
        "updated": [
            "reports/11_d1_d2_d3_continuation_status.md",
            "reports/16_updated_final_recommendation.md",
            "logs/run_log.jsonl",
        ],
        "restrictions_observed": [
            "no downloads",
            "no raw-data modification",
            "no extraction reruns",
            "no model reruns",
            "no significance rescue",
            "no machine-readable numeric output edits",
        ],
        "scientific_bottom_line": "artifact-sensitive/null-leaning with weak/context-specific D2 DPX cue-baseline trace only",
    }
    with (LOGS / "run_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, sort_keys=True) + "\n")

    print(json.dumps({"status": "complete", "gate": gate.get("gate"), "manifest_rows": len(manifest_rows)}, indent=2))


if __name__ == "__main__":
    main()
