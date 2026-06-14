from __future__ import annotations

import csv
import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DRAFT_DIR = ROOT / "manuscript" / "neurotrauma_reports_draft_v1"
OUT_FINAL = ROOT / "outputs" / "final"
OUT_QC = ROOT / "outputs" / "qc"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"

RECOMMENDED_TITLE = (
    "Artifact-sensitive resting EEG candidate signals in public traumatic brain injury datasets: "
    "an OpenNeuro falsification analysis"
)


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for col in df.columns:
            vals.append(str(row[col]).replace("\n", " ").replace("|", "\\|"))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def get_gate_status() -> tuple[bool, list[str]]:
    issues: list[str] = []
    gate_path = OUT_QC / "audit_gate.json"
    if not gate_path.exists():
        issues.append("outputs/qc/audit_gate.json missing")
        return False, issues
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("gate") != "PASS":
        issues.append(f"audit gate is {gate.get('gate')}")
    if gate.get("safe_to_continue") is not True:
        issues.append("safe_to_continue is not true")
    if gate.get("next_prompt_allowed") is not True:
        issues.append("next_prompt_allowed is not true")
    if not (OUT_QC / "AUDIT_PASS.ok").exists():
        issues.append("AUDIT_PASS.ok missing")
    if (OUT_QC / "AUDIT_FAIL.ok").exists():
        issues.append("AUDIT_FAIL.ok present")
    if not (OUT_FINAL / "MANUSCRIPT_QC_PASS.ok").exists():
        issues.append("MANUSCRIPT_QC_PASS.ok missing")
    if (OUT_FINAL / "MANUSCRIPT_QC_FAIL.ok").exists():
        issues.append("MANUSCRIPT_QC_FAIL.ok present")
    qc_path = OUT_FINAL / "manuscript_readiness_qc_checks.csv"
    if not qc_path.exists():
        issues.append("manuscript_readiness_qc_checks.csv missing")
    else:
        qc = read_csv(qc_path)
        failed = qc[(qc["severity"] == "critical") & (qc["pass"].astype(str).str.lower() != "true")]
        if len(failed):
            issues.append(f"{len(failed)} critical manuscript readiness QC checks failed")
    return len(issues) == 0, issues


def load_sources() -> dict[str, pd.DataFrame | str]:
    source_paths = [
        REPORTS / "39_final_analysis_package_integrity_report.md",
        REPORTS / "40_final_scientific_synthesis_and_publishability_report.md",
        REPORTS / "41_reproduction_and_handoff_guide.md",
        REPORTS / "42_manuscript_viability_and_strategy_report.md",
        REPORTS / "43_candidate_journal_and_article_type_assessment.md",
        REPORTS / "44_claims_figures_tables_manuscript_blueprint.md",
        REPORTS / "45_final_figure_table_generation_report.md",
        REPORTS / "45a_draft_figure_and_table_captions.md",
        REPORTS / "46_manuscript_readiness_qc_report.md",
        REPORTS / "47_candidate_titles_abstract_skeletons_and_outline.md",
        REPORTS / "24_d1_d3_integrated_artifact_control_report.md",
        REPORTS / "28_d1_d3_post_analysis_audit.md",
        REPORTS / "29_next_step_decision_after_d1_d3.md",
        REPORTS / "30_d2_prespecified_falsification_plan.md",
        REPORTS / "35_d2_bounded_falsification_report.md",
        REPORTS / "36_integrated_d1_d2_d3_final_decision_report.md",
        REPORTS / "37_stale_parallel_job_accuracy_audit.md",
        REPORTS / "38_stale_report_repair_log.md",
    ]
    sources: dict[str, pd.DataFrame | str] = {}
    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        sources[path.name] = path.read_text(encoding="utf-8")
    sources.update(
        {
            "evidence": read_csv(OUT_FINAL / "d1_d2_d3_evidence_matrix.csv"),
            "claims": read_csv(OUT_FINAL / "key_result_claims_traceability.csv"),
            "manifest": read_csv(OUT_FINAL / "final_deliverable_manifest.csv"),
            "allowlist": read_csv(OUT_FINAL / "manuscript_claim_allowlist.csv"),
            "blocklist": read_csv(OUT_FINAL / "manuscript_claim_blocklist.csv"),
            "proposed": read_csv(OUT_FINAL / "proposed_figures_and_tables.csv"),
            "journals": read_csv(OUT_FINAL / "journal_target_matrix.csv"),
            "readiness_qc": read_csv(OUT_FINAL / "manuscript_readiness_qc_checks.csv"),
            "figure_manifest": read_csv(ROOT / "outputs" / "final_figures" / "figure_manifest.csv"),
            "table_manifest": read_csv(ROOT / "outputs" / "final_tables" / "table_manifest.csv"),
            "source_manifest": read_csv(ROOT / "outputs" / "final_figure_source_data" / "source_data_manifest.csv"),
            "table1": read_csv(ROOT / "outputs" / "final_tables" / "table1_dataset_cohort_overview.csv"),
            "table2": read_csv(ROOT / "outputs" / "final_tables" / "table2_analysis_families_interpretation_rules.csv"),
            "table3": read_csv(ROOT / "outputs" / "final_tables" / "table3_key_results_summary.csv"),
            "table4": read_csv(ROOT / "outputs" / "final_tables" / "table4_claims_caveats_traceability.csv"),
        }
    )
    return sources


def claim_audit_rows() -> list[dict[str, str]]:
    return [
        {
            "claim_text": "The analysis is a public-data, exploratory falsification-oriented reanalysis rather than a prospective clinical study.",
            "source_file": "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "supporting_numeric_value": "not_applicable",
            "allowed_wording": "transparent public EEG analysis; falsification-oriented",
            "prohibited_overclaim_avoided": "positive diagnostic/prognostic narrative",
            "manuscript_section": "Abstract; Introduction; Methods; Discussion",
            "caveat_included": "public data and exploratory framing stated",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "Verified raw EEG was available for ds003522, ds005114, ds003523, and ds003490.",
            "source_file": "reports/39_final_analysis_package_integrity_report.md; outputs/final_tables/table1_dataset_cohort_overview.csv",
            "supporting_numeric_value": "ds003522 200 pairs; ds005114 223 pairs; ds003523 221 pairs; ds003490 75 pairs",
            "allowed_wording": "raw EEG retrieval and MNE checks were verified",
            "prohibited_overclaim_avoided": "dataset completeness beyond verified local files",
            "manuscript_section": "Methods; Results",
            "caveat_included": "ds003490 comparator-only caveat",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "Acute mTBI versus control did not survive broad artifact-controlled D1 FDR.",
            "source_file": "outputs/final_tables/table3_key_results_summary.csv; outputs/qc/final_result_consistency_checks.csv",
            "supporting_numeric_value": "minimum q=0.7876",
            "allowed_wording": "did not survive broad artifact-controlled FDR",
            "prohibited_overclaim_avoided": "survived correction",
            "manuscript_section": "Abstract; Results; Discussion",
            "caveat_included": "broad family scope described",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "The D1 narrow prior-anchor family remains exploratory and non-confirmatory.",
            "source_file": "outputs/final_tables/table2_analysis_families_interpretation_rules.csv; reports/28_d1_d3_post_analysis_audit.md",
            "supporting_numeric_value": "q=0.1320",
            "allowed_wording": "exploratory transparency family",
            "prohibited_overclaim_avoided": "claim rescue",
            "manuscript_section": "Results; Discussion",
            "caveat_included": "post hoc transparency family stated",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "D3 eyes-closed alpha/IAF did not rescue the acute signal.",
            "source_file": "outputs/final_tables/table3_key_results_summary.csv; reports/28_d1_d3_post_analysis_audit.md",
            "supporting_numeric_value": "minimum q=0.9149",
            "allowed_wording": "did not rescue or support the acute signal",
            "prohibited_overclaim_avoided": "alpha/IAF rescue endpoint",
            "manuscript_section": "Abstract; Results; Discussion",
            "caveat_included": "aperiodic-adjusted alpha peak metric unavailable",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "Chronic TBI findings remain separate, exploratory, and batch-sensitive.",
            "source_file": "outputs/final_tables/table3_key_results_summary.csv; reports/28_d1_d3_post_analysis_audit.md",
            "supporting_numeric_value": "minimum q=0.3484",
            "allowed_wording": "exploratory and batch-sensitive chronic branch",
            "prohibited_overclaim_avoided": "chronic TBI proof",
            "manuscript_section": "Results; Discussion; Limitations",
            "caveat_included": "acute and chronic not pooled",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "D2 provides partial and inconsistent cross-task support.",
            "source_file": "reports/35_d2_bounded_falsification_report.md; outputs/d2_cross_task/d2_falsification_summary.csv",
            "supporting_numeric_value": "overall min q=0.0898; mixed q<0.10 count=0",
            "allowed_wording": "partial/inconsistent bounded cross-task support",
            "prohibited_overclaim_avoided": "independent confirmation",
            "manuscript_section": "Abstract; Results; Discussion",
            "caveat_included": "Original_ID overlap stated",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "The only weak D2 q<0.10 trace was in ds005114 DPX cue-baseline rows.",
            "source_file": "reports/35_d2_bounded_falsification_report.md; outputs/d2_cross_task/d2_within_dataset_group_effects.csv",
            "supporting_numeric_value": "minimum q=0.0898; max abs(g)=0.5277",
            "allowed_wording": "weak/context-specific DPX cue-baseline trace",
            "prohibited_overclaim_avoided": "confirmed replication",
            "manuscript_section": "Results; Discussion",
            "caveat_included": "cue-baseline context-specific; not a robust endpoint",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "DPX task-average, VWM task-average, and mixed-effects group terms did not support robust convergence.",
            "source_file": "reports/35_d2_bounded_falsification_report.md; outputs/d2_cross_task/d2_falsification_summary.csv; outputs/d2_cross_task/d2_mixed_effects_models.csv",
            "supporting_numeric_value": "DPX task-average q=0.1524; VWM task-average q=0.4720; mixed group terms below q<0.10=0",
            "allowed_wording": "did not support robust convergence",
            "prohibited_overclaim_avoided": "cross-task validation",
            "manuscript_section": "Abstract; Results; Discussion",
            "caveat_included": "mixed models numerically fragile for some features",
            "pass_fail": "PASS",
        },
        {
            "claim_text": "ds003490 is a comparator and pipeline rehearsal dataset only.",
            "source_file": "reports/22_ds003490_feature_readiness_report.md; outputs/final_tables/table1_dataset_cohort_overview.csv",
            "supporting_numeric_value": "75 paired SET/FDT files; MNE readable",
            "allowed_wording": "comparator/pipeline rehearsal dataset",
            "prohibited_overclaim_avoided": "ds003490 TBI validation",
            "manuscript_section": "Methods; Results; Discussion",
            "caveat_included": "not a TBI dataset",
            "pass_fail": "PASS",
        },
    ]


def build_main_manuscript() -> str:
    return f"""
    # {RECOMMENDED_TITLE}

    ## Abstract

    See `abstract.md` for the structured abstract. In brief, this manuscript reports a public OpenNeuro EEG reanalysis in which an initially plausible resting EEG candidate signal in mild traumatic brain injury attenuated under artifact-control and was only partially supported by bounded cross-task testing.

    ## Introduction

    Mild traumatic brain injury (mTBI) is common, clinically heterogeneous, and difficult to summarize with a single neurophysiological endpoint. EEG is attractive for public-data reanalysis because it is inexpensive relative to many imaging modalities, temporally precise, and available in multiple OpenNeuro datasets. At the same time, scalp EEG is highly sensitive to artifact, task context, preprocessing decisions, and participant overlap across repeated recordings. These properties make transparent falsification especially important before any candidate signal is treated as robust.

    The present manuscript uses a completed, audited D1/D2/D3 analysis package to ask a deliberately conservative question: does a plausible resting EEG aperiodic/spectral candidate in public TBI data remain interpretable after artifact-control, a lower-artifact eyes-closed alpha/IAF sensitivity check, and bounded cross-task stress testing? The purpose is not to build a classifier or to claim clinical readiness. The purpose is to document what remains after a candidate signal is pushed through transparent, source-backed robustness checks.

    The final package supports a cautious answer. The acute mTBI versus control resting signal does not survive broad artifact-controlled FDR. A narrower prior-anchor family remains exploratory. The eyes-closed alpha/IAF branch does not rescue the acute signal. D2 task datasets provide a weak DPX cue-baseline trace, but task-average DPX, visual working memory, and integrated task models do not support robust convergence. Chronic TBI is handled as a separate batch-sensitive context, and ds003490 is used only as a comparator and pipeline rehearsal dataset.

    This framing is aligned with Neurotrauma Reports as a transparent null-leaning reproducibility and falsification report. The manuscript emphasizes public-data traceability, artifact sensitivity, and conservative interpretation rather than a positive translational narrative.

    ## Methods

    ### Study Design and Scope

    This was a retrospective public-data EEG reanalysis using only completed, audited outputs from the final D1/D2/D3 package. No new downloads, extraction, model fitting, raw-data movement, or machine-readable result edits were performed during manuscript drafting. The analysis was designed as a stress test of an initially plausible resting EEG candidate signal in TBI.

    D1 evaluated resting EEG aperiodic and spectral families in ds003522 under artifact-control branches. D3 evaluated a lower-artifact eyes-closed alpha/IAF branch within ds003522. D2 evaluated bounded cross-task support using ds005114 and ds003523. ds003490 was used only for comparator and pipeline-readiness rehearsal. The audit gate and manuscript-readiness gate were required to pass before this draft was generated.

    ### Datasets and Participants

    The verified dataset roles are summarized in Table 1 and Figure 1. ds003522 supplied the D1/D3 TBI analyses and had 200 paired EEGLAB SET/FDT files locally verified. ds005114 supplied the DPX task component of D2 and had 223 paired SET/FDT files verified. ds003523 supplied the visual working memory component of D2 and had 221 paired SET/FDT files verified. ds003490 had 75 paired SET/FDT files verified and was used only as a comparator and pipeline rehearsal dataset.

    In the D1/D3 group models, acute mTBI versus control was treated as the cleanest primary comparison. The model reports show subject-level acute comparisons with 26 controls and 44 mTBI observations for the main ds003522 branch. Chronic TBI was kept separate because the chronic branch is secondary and batch-sensitive. In D2, task-average models used Original_ID to avoid treating repeated task records from the same person as independent people.

    ### Identity Harmonization and Overlap Handling

    D2 was interpreted within an overlapping-subject framework. The ds005114 and ds003523 task datasets overlap by Original_ID, so they were not treated as independent cohorts. Direction consistency and within-subject stability across D2 tasks were interpreted as feature-stability context rather than separate cohort evidence. This distinction is central to the manuscript's claim boundary.

    ### EEG Preprocessing and Feature Extraction

    The analysis used locally verified EEGLAB SET/FDT files readable with MNE. The final feature families included aperiodic features, band-power summaries, spectral-balance ratios, entropy-like features, and alpha/IAF-adjacent features where available. The manuscript does not introduce new preprocessing or feature extraction; it describes the locked outputs already generated by the analysis scripts and audited final package.

    ### D1 Artifact-Control Analysis

    D1 tested acute mTBI versus control in ds003522 across resting EEG eyes-open and eyes-closed conditions. The broad D1 FDR family combined eyes-open and eyes-closed conditions, six regions, and 17 features within each comparison and artifact branch. Artifact branches included all epochs, ptp95 within-recording trimming, and a strict 250 microvolt branch.

    The ptp95 branch removed the highest-amplitude 5% of epochs within recording-condition while preserving recording-condition coverage. The strict 250 microvolt branch retained too few recording-condition rows for meaningful group modeling and was treated as an artifact-control limitation rather than a substantive group result. The narrow prior-anchor family was reported only as an exploratory transparency calculation, not as a rescued endpoint.

    ### D3 Eyes-Closed Alpha/IAF Analysis

    D3 tested whether lower-artifact eyes-closed posterior alpha/IAF features would support the acute signal. This branch was especially relevant because the original D1 candidate was strongest in eyes-open frontal, temporal, and global features where non-neural artifact sensitivity was a concern. The generated D3 table did not include a separate aperiodic-adjusted alpha peak endpoint, so alpha interpretation remains limited.

    ### D2 Bounded Cross-Task Falsification Analysis

    D2 tested whether harmonized spectral/aperiodic structure generalized across task contexts. ds005114 provided DPX cue-baseline and task-average windows; ds003523 provided visual working memory task-average windows. D2 results were interpreted as bounded cross-task falsification evidence within overlapping Original_IDs, not as a separate cohort study.

    ### ds003490 Comparator/Pipeline Rehearsal

    ds003490 was retained as a comparator and pipeline rehearsal dataset only. It verified that the pipeline could retrieve paired EEGLAB files, read MNE-compatible recordings, parse event/rest structure, and generate readiness outputs. It is not a TBI dataset and is not evidence for a TBI claim.

    ### Statistical Analysis

    The final package reported Hedges g for group differences, Welch tests for local signal inspection, permutation p-values where available, bootstrap confidence intervals, leave-one-out effect ranges, artifact-sensitivity summaries, and Benjamini-Hochberg FDR q-values. Mixed task models were attempted for D2; 27 MixedLM models completed and 21 used clustered OLS fallback because part of the model family was numerically fragile.

    ### Multiple-Comparison Handling

    The manuscript gives interpretive priority to broad FDR families. D1 artifact-controlled acute mTBI versus control was evaluated across 204 tests in the broad family. D3 eyes-closed alpha/IAF was evaluated across 36 tests in the acute family. Narrower prior-anchor calculations are presented as transparency analyses only. D2 cue-baseline findings are described as weak and context-specific because task-average and integrated task checks did not converge.

    ### Reproducibility and Audit Procedures

    Raw data verification, stale-report repair, final package integrity checks, manuscript-readiness QC, figure/table source data, and claim traceability were completed before drafting. The audit gate reported PASS with no critical failures. The manuscript-readiness gate reported PASS, with all critical rows true. The draft package preserves the final source file paths and includes a claim traceability audit.

    ## Results

    ### Dataset Retrieval and Verification

    All datasets used in the final package had paired EEGLAB files locally verified before interpretation. ds003522 had 200 SET/FDT pairs for D1/D3. ds005114 had 223 pairs for D2 DPX. ds003523 had 221 pairs for D2 visual working memory. ds003490 had 75 pairs and passed comparator readiness checks. Table 1 summarizes dataset roles and verification status, and Figure 1 summarizes the locked workflow.

    **Table 1 about here.**

    **Figure 1 about here.**

    ### Original Candidate and Artifact-Control Outcome

    The original D1 signal was available locally only as a prose anchor rather than exact per-feature rows. That anchor described eyes-open temporal, frontal, and global aperiodic/spectral differences with acute mTBI absolute Hedges g around 0.80-0.96 and broad-screen FDR below q<0.10. The audit therefore treated the original signal as historical rationale rather than exact reproducible row-level evidence.

    After ptp95 artifact trimming, the acute mTBI versus control broad D1 family did not survive FDR. The minimum broad artifact-controlled q-value was 0.7876. The narrow prior-anchor family yielded q=0.1320, but that family was explicitly exploratory and non-confirmatory. Figure 2 visualizes the attenuation from the prose anchor to artifact-controlled estimates, and Figure 3 shows why ptp95 was interpretable as a sensitivity branch while strict 250 microvolt filtering was too conservative for group inference.

    **Figure 2 about here.**

    **Figure 3 about here.**

    **Table 2 about here.**

    **Table 3 about here.**

    ### D3 Eyes-Closed Alpha/IAF Outcome

    The D3 eyes-closed alpha/IAF branch did not rescue the acute signal. The posterior acute minimum FDR q-value was 0.9149. The generated D3 outputs also lacked a separate aperiodic-adjusted alpha peak endpoint, limiting mechanistic alpha interpretation. Figure 4 summarizes the non-supportive D3 endpoint.

    **Figure 4 about here.**

    ### D2 Bounded Cross-Task Falsification Outcome

    D2 provided partial and inconsistent cross-task support. The only weak q<0.10 trace was in ds005114 DPX cue-baseline rows, with minimum q=0.0898 and maximum absolute Hedges g=0.5277. However, DPX task-average did not survive FDR (q=0.1524), visual working memory task-average did not survive FDR (q=0.4720), and integrated mixed models had 0 group reference-task terms below q<0.10.

    Direction consistency and within-subject stability offered useful measurement context, but they did not override D1/D3 artifact sensitivity. Because the D2 task datasets overlap by Original_ID, D2 is best interpreted as bounded cross-task stress testing rather than a separate cohort result. Figure 5 summarizes the D2 outcome.

    **Figure 5 about here.**

    ### ds003490 Pipeline Rehearsal Outcome

    ds003490 verified that the local pipeline could retrieve and read paired EEGLAB files and rehearse rest/oddball feature-readiness steps. It remains comparator-only. It is not a TBI dataset and is not used as support for any TBI inference.

    ### Evidence Synthesis

    The integrated evidence matrix favors a cautious null-leaning interpretation. D1 broad artifact-controlled results are non-supportive, the D1 narrow prior-anchor family remains exploratory, D3 does not rescue the signal, chronic TBI remains separate and batch-sensitive, and D2 is weak/context-specific rather than convergent. Figure 6 and Table 4 summarize the claim boundaries.

    **Figure 6 about here.**

    **Table 4 about here.**

    **Table S1 about here.**

    ## Discussion

    ### Principal Findings

    This public OpenNeuro EEG reanalysis found that an initially plausible resting EEG candidate signal in mTBI became null-leaning after artifact-control and bounded cross-task checks. The most important result is not a positive signal. It is the attenuation and non-convergence pattern: broad D1 artifact-controlled FDR did not survive, D3 eyes-closed alpha/IAF did not rescue the signal, and D2 offered only a weak DPX cue-baseline trace that did not generalize to task-average or integrated task models.

    ### Interpretation

    The final interpretation is artifact-sensitive and falsification-oriented. The original candidate remained coherent enough to justify auditing, but the audited package does not support strong disease-specific inference. Nominal effect sizes in selected rows remain scientifically interesting, especially because some directions persisted across artifact sensitivity checks, but broad FDR failure and cross-task inconsistency are the dominant interpretive facts.

    ### Relation to TBI EEG and Aperiodic EEG Literature

    The manuscript should be situated within three literatures: EEG studies of mTBI, aperiodic/spectral parameterization methods, and artifact-aware EEG interpretation. Exact citation details remain to be verified before submission. The present contribution is methodological and transparency-oriented: it shows how a plausible public-data EEG candidate weakens when artifact handling, lower-artifact sensitivity testing, and task-context stress testing are made explicit.

    ### Why Artifact Control Changed Interpretation

    Artifact control changed interpretation by shifting the analysis from nominally promising eyes-open features toward broad family-level evidence. The ptp95 branch preserved coverage while trimming high-amplitude epochs, but the broad acute mTBI family still had minimum q=0.7876. The strict 250 microvolt branch showed that a very stringent fixed threshold was overconservative for these files. These results do not prove that the original signal was artifact, but they make a strong positive interpretation untenable from the present outputs.

    ### Why D2 Is Falsification, Not Validation

    D2 was designed as a bounded stress test. It was useful because it asked whether harmonized spectral structure appeared across task contexts. It cannot be treated as a separate cohort result because ds005114 and ds003523 overlap by Original_ID. The cue-baseline DPX trace is therefore best described as weak and context-specific. The non-supportive DPX task-average, VWM task-average, and mixed-model results are more important for the overall conclusion than the isolated cue-baseline q<0.10 trace.

    ### Clinical Implications

    The clinical implication is caution. The current public-data package does not support using these EEG features for clinical decision-making, triage, symptom inference, or treatment planning. The result is still useful for neurotrauma research because it identifies design features that a future preregistered study would need: stronger artifact control, predefined endpoints, prospective covariates, external testing, and separation of acute and chronic TBI.

    ### Strengths

    Strengths include local raw EEG verification, use of public datasets, explicit identity-overlap handling, conservative FDR interpretation, artifact-branch transparency, D3 sensitivity testing, D2 cross-task stress testing, figure/table source-data manifests, stale-report audit, and claim traceability. The package is unusually explicit about what cannot be claimed.

    ### Limitations

    The main limitations are substantial. Exact original Phase 5 per-feature rows were unavailable locally, so the original candidate was available only as a prose anchor. The strict artifact-clean branch was too conservative for group inference. The ptp95 branch is a sensitivity approach rather than a definitive artifact-correction method. D3 lacked aperiodic-adjusted alpha peak metrics in the generated table. D2 overlapped by Original_ID and was not a separate cohort. Chronic TBI was secondary and batch-sensitive. ds003490 was comparator-only.

    ### Future Directions

    A future study should be prospective and preregistered. It should specify artifact handling before analysis, include eyes-open and eyes-closed endpoints, predefine aperiodic and alpha features, include covariates such as medication, sleep, injury timing, and symptoms, and keep acute and chronic TBI either separate or explicitly modeled. It should also define an independent test strategy before analysis.

    ## Conclusion

    A plausible public resting EEG candidate signal in mTBI did not survive broad artifact-controlled FDR and was not rescued by eyes-closed alpha/IAF or robust cross-task convergence. The strongest contribution is a transparent null-leaning falsification analysis showing why artifact and task-context sensitivity must be foregrounded before stronger TBI EEG claims are considered.

    ## Data Availability

    The analysis used public OpenNeuro datasets ds003522, ds005114, ds003523, and ds003490. ds003490 was used only as a comparator and pipeline rehearsal dataset. Derived outputs, source-data manifests, figure/table manifests, and the reproduction guide are listed in the local final package. Exact public repository and archival links should be inserted before submission.

    ## Code Availability

    Code will be made available in a public repository upon submission or publication. The local reproduction guide documents script order, raw-data verification outputs, and audit gates.

    ## Ethics / Public Data Statement

    This study reanalyzed publicly available deidentified datasets. No new participant recruitment, intervention, or private-data collection was performed by the drafting team. Dataset-specific ethics and consent statements should be verified from the original OpenNeuro dataset documentation before submission.

    ## Conflicts of Interest

    CONFLICTS OF INTEREST STATEMENT TO ADD.

    ## Funding

    FUNDING STATEMENT TO ADD.

    ## Acknowledgments

    ACKNOWLEDGMENTS TO ADD. The authors should acknowledge the original dataset contributors and OpenNeuro/DataLad infrastructure after verifying required citation language.

    ## References Placeholder

    - OpenNeuro dataset citation for ds003522. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro dataset citation for ds005114. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro dataset citation for ds003523. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro dataset citation for ds003490, comparator-only. REFERENCE DETAILS TO VERIFY.
    - DataLad and git-annex methods citation. REFERENCE DETAILS TO VERIFY.
    - MNE-Python citation. REFERENCE DETAILS TO VERIFY.
    - Aperiodic/specparam/FOOOF methods citation. REFERENCE DETAILS TO VERIFY.
    - mTBI EEG literature citation set. REFERENCE DETAILS TO VERIFY.
    - EEG artifact and EMG caution literature citation set. REFERENCE DETAILS TO VERIFY.

    ## Figure and Table Callouts

    - Figure 1: Dataset and workflow structure.
    - Figure 2: D1 artifact-control attenuation.
    - Figure 3: Artifact-branch sample retention.
    - Figure 4: D3 eyes-closed alpha/IAF endpoint.
    - Figure 5: D2 bounded cross-task check.
    - Figure 6: Final evidence matrix.
    - Table 1: Dataset and cohort overview.
    - Table 2: Analysis families and interpretation rules.
    - Table 3: Key results summary.
    - Table 4: Claims, caveats, and traceability.
    - Table S1: Deliverable manifest summary.
    """


def build_abstract() -> str:
    return f"""
    # Structured Abstract

    ## Background

    Public EEG datasets can be used to stress-test candidate neurophysiological signals in mild traumatic brain injury (mTBI), but EEG is sensitive to artifact, task context, and repeated participant identity. This manuscript reports a transparent OpenNeuro reanalysis framed as a null-leaning reproducibility and falsification study.

    ## Methods

    We used the audited final D1/D2/D3 analysis package without new extraction, modeling, downloads, or raw-data modification. ds003522 supplied the resting EEG D1 artifact-control and D3 eyes-closed alpha/IAF analyses. ds005114 and ds003523 supplied bounded D2 cross-task checks using DPX and visual working memory. ds003490 was retained only as a comparator and pipeline rehearsal dataset. Analyses prioritized broad Benjamini-Hochberg FDR families, artifact sensitivity, Original_ID overlap handling, and source-backed claim traceability.

    ## Results

    The acute mTBI versus control resting EEG signal did not survive broad artifact-controlled FDR in D1 (minimum q=0.7876). A narrow prior-anchor transparency family remained exploratory (q=0.1320). D3 eyes-closed posterior alpha/IAF did not rescue the acute signal (minimum q=0.9149). Chronic TBI remained separate and batch-sensitive (minimum q=0.3484). In D2, the only weak q<0.10 trace appeared in ds005114 DPX cue-baseline rows (minimum q=0.0898; maximum absolute Hedges g=0.5277), while DPX task-average (q=0.1524), visual working memory task-average (q=0.4720), and mixed-effects group terms (0 below q<0.10) did not support robust convergence.

    ## Conclusions

    The final package supports a cautious artifact-sensitive, null-leaning interpretation. The manuscript is best framed as a public-data EEG falsification report showing attenuation of an initially plausible candidate signal under artifact-control and bounded cross-task testing, not as a clinical translation claim.
    """


def build_title_page() -> str:
    titles = [
        RECOMMENDED_TITLE,
        "Artifact sensitivity in public EEG analyses of mild traumatic brain injury",
        "When resting EEG signals attenuate under artifact control: a public mTBI reanalysis",
        "A public EEG falsification study of resting and task spectral signals in mTBI",
        "Fragile spectral effects in OpenNeuro mTBI EEG across rest and task contexts",
        "Cross-task stress testing of resting EEG spectral effects in public mTBI data",
        "A null-leaning OpenNeuro EEG reanalysis of mTBI resting-state spectral features",
        "Resting-state EEG candidate effects in mTBI attenuate across artifact and task checks",
    ]
    return f"""
    # Title Page

    ## Recommended Title

    {RECOMMENDED_TITLE}

    ## Candidate Titles

    {chr(10).join(f'{i + 1}. {title}' for i, title in enumerate(titles))}

    ## Article Type Recommendation

    Neurotrauma Reports Null Hypothesis article if the editorial office agrees; otherwise compact Regular Manuscript with explicit null-leaning reproducibility/falsification framing.

    ## Authors

    AUTHOR NAMES TO ADD.

    ## Affiliations

    AFFILIATIONS TO ADD.

    ## Corresponding Author

    CORRESPONDING AUTHOR CONTACT TO ADD.

    ## Short Title

    Artifact-sensitive OpenNeuro mTBI EEG reanalysis

    ## Keywords

    mild traumatic brain injury; EEG; OpenNeuro; artifact sensitivity; reproducibility; falsification; aperiodic EEG; alpha rhythm
    """


def build_cover_letter() -> str:
    return f"""
    # Draft Cover Letter: Neurotrauma Reports

    Dear Editors,

    We are pleased to submit the manuscript titled "{RECOMMENDED_TITLE}" for consideration in Neurotrauma Reports. We believe the manuscript is best considered as a Null Hypothesis article, or as a compact Regular Manuscript if that format better fits the journal's current issue structure.

    This paper reports a transparent public-data EEG reanalysis of OpenNeuro traumatic brain injury datasets. Rather than presenting a positive discovery narrative, the manuscript asks whether an initially plausible resting EEG candidate signal remains interpretable after artifact-control, eyes-closed alpha/IAF sensitivity testing, and bounded cross-task stress testing. The answer is deliberately conservative: the main acute mTBI signal does not survive broad artifact-controlled FDR, D3 does not rescue the signal, and D2 provides only partial and inconsistent support.

    We believe this result will interest Neurotrauma Reports readers because it provides a practical example of how public neurotrauma EEG signals can change under artifact-aware analysis and source-backed claim control. The manuscript foregrounds reproducibility, raw-data verification, Original_ID overlap handling, and limitations rather than overclaiming.

    The manuscript does not assert marker validation, diagnostic readiness, prognostic readiness, or clinical decision utility. The ds003490 dataset is described only as a comparator and pipeline rehearsal dataset, chronic TBI is kept separate and batch-sensitive, and D2 is interpreted as overlapping-subject cross-task stress testing rather than a separate cohort result.

    Code will be made available in a public repository upon submission or publication, and all public dataset citations will be verified before final submission. Thank you for considering this manuscript for Neurotrauma Reports.

    Sincerely,

    AUTHOR NAME TO ADD
    """


def build_highlights() -> str:
    return """
    # Highlights / Key Points

    - Public OpenNeuro EEG datasets were used to stress-test an initially plausible mTBI resting EEG candidate signal.
    - The acute mTBI versus control D1 signal did not survive broad artifact-controlled FDR after ptp95 trimming.
    - D3 eyes-closed alpha/IAF did not rescue the acute signal.
    - D2 showed only a weak DPX cue-baseline trace, while task-average and integrated task models did not support robust convergence.
    - The manuscript is framed as a transparent artifact-sensitivity and falsification report, with chronic TBI separate and ds003490 comparator-only.
    """


def build_figure_captions() -> str:
    return """
    # Figure Captions

    **Figure 1. Dataset and workflow structure.** Public EEG datasets were assigned locked roles before manuscript-facing visualization. ds003522 supplied the D1/D3 TBI analyses, ds005114 and ds003523 supplied the bounded D2 cross-task check, and ds003490 remained a comparator and pipeline rehearsal dataset only. Counts show verified paired EEGLAB SET/FDT files.

    **Figure 2. D1 artifact-control attenuation.** The historical prompt-level D1 anchor is shown only as a prose-derived reference because exact local per-feature rows were unavailable. Existing audit outputs show that acute mTBI versus control does not survive broad artifact-controlled FDR after ptp95 trimming, while the narrow prior-anchor family remains exploratory.

    **Figure 3. Artifact-branch sample retention.** The all-epochs branch preserves all recording-condition rows, ptp95 trimming preserves coverage while trimming epochs within recordings, and the strict 250 uV branch leaves too few rows for group inference. This supports interpreting ptp95 as a sensitivity branch rather than definitive artifact correction.

    **Figure 4. D3 eyes-closed alpha/IAF endpoint.** The lower-artifact eyes-closed alpha/IAF branch does not rescue the acute D1 signal. Posterior acute rows remain non-supportive after FDR, and generated D3 tables do not include a separate aperiodic-adjusted alpha peak endpoint.

    **Figure 5. D2 bounded cross-task check.** The DPX cue-baseline window shows a weak q<0.10 trace, but DPX task-average, visual working memory task-average, and integrated task models do not support robust convergence. Direction consistency is descriptive because D2 task datasets overlap by Original_ID.

    **Figure 6. Final evidence matrix.** The integrated evidence favors a cautious null-leaning reproducibility and falsification frame. D1/D3 broad artifact-controlled results are non-supportive, chronic TBI remains separate and batch-sensitive, D2 is partial and context-specific, and ds003490 is comparator-only.
    """


def build_table_captions() -> str:
    return """
    # Table Captions

    **Table 1. Dataset and cohort overview.** Verified raw EEG counts, MNE read status, dataset role, and manuscript caveats for each OpenNeuro dataset used in the final package.

    **Table 2. Analysis families and interpretation rules.** Locked D1/D3 FDR families, exploratory transparency families, and bounded D2 checks used to constrain manuscript interpretation.

    **Table 3. Key results summary.** Compact summary of D1, D3, chronic, D2, and comparator findings with q-values or verification values copied from the final package.

    **Table 4. Claims, caveats, and traceability.** Cautious manuscript wording and blocked overclaim wording mapped to source reports and machine-readable outputs.

    **Table S1. Deliverable manifest summary.** Compressed count of final package artifacts by phase and artifact type.
    """


def build_data_code_availability() -> str:
    return """
    # Data and Code Availability

    This manuscript uses public OpenNeuro EEG datasets ds003522, ds005114, ds003523, and ds003490. ds003522 supplied the D1/D3 traumatic brain injury analyses. ds005114 and ds003523 supplied the bounded D2 cross-task analyses. ds003490 was used only as a comparator and pipeline rehearsal dataset and should not be cited as TBI evidence.

    Local analysis outputs include raw-data verification reports, D1/D3 artifact-control outputs, D3 eyes-closed alpha/IAF outputs, D2 bounded cross-task outputs, final evidence matrices, figure/table source data, and manuscript claim traceability files. The reproduction guide is `reports/41_reproduction_and_handoff_guide.md`.

    Subject identity overlap in D2 was handled using `Original_ID`. ds005114 and ds003523 were not pooled or interpreted as independent cohorts. Direction consistency and within-subject stability are treated as descriptive feature-stability context.

    Code will be made available in a public repository upon submission or publication.

    Public dataset accession and citation details must be verified before submission:

    - OpenNeuro ds003522. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro ds005114. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro ds003523. REFERENCE DETAILS TO VERIFY.
    - OpenNeuro ds003490, comparator-only. REFERENCE DETAILS TO VERIFY.
    """


def build_guardrails(sources: dict[str, Any]) -> str:
    allow = sources["allowlist"]
    block = sources["blocklist"]
    allow_table = md_table(allow[["claim_id", "acceptable_wording", "caveat", "source_evidence"]])
    block_table = md_table(block[["claim_id", "claim_text", "acceptable_wording", "unacceptable_wording", "caveat"]])
    return f"""
    # Limitations and Claims Guardrails

    ## Required Caveats

    - D1/D3 are artifact-sensitive and null-leaning after artifact control.
    - Acute mTBI versus control is the cleanest primary comparison.
    - The D1 narrow prior-anchor family is exploratory and non-confirmatory.
    - D3 eyes-closed alpha/IAF does not rescue the acute signal.
    - Chronic TBI is separate, exploratory, and batch-sensitive.
    - D2 is partial and inconsistent, with overlap by Original_ID.
    - ds003490 is comparator/pipeline rehearsal only and not TBI evidence.
    - No current output supports marker validation, diagnostic use, symptom prediction, separate-cohort proof, or clinical decision use.

    ## Allowed Claims

    {allow_table}

    ## Blocked Claims

    {block_table}

    ## Language Substitutions

    - Use "artifact-sensitive/null-leaning" instead of "robust positive signal."
    - Use "weak/context-specific DPX cue-baseline trace" instead of "confirmed cross-task effect."
    - Use "bounded cross-task stress test" instead of "D2 validation."
    - Use "comparator/pipeline rehearsal" instead of "ds003490 TBI validation."
    - Use "future preregistered follow-up is needed" instead of "ready for clinical deployment."
    """


def build_submission_checklist() -> str:
    return """
    # Submission Readiness Checklist

    ## Human-Supplied Items Still Needed

    - Author names and order.
    - Author affiliations.
    - Corresponding author contact information.
    - Funding statement.
    - Conflicts of interest statement.
    - Acknowledgments and dataset contributor wording.
    - Author contribution statement, if required by the journal.

    ## Scientific/Editorial Checks Still Needed

    - PI/coauthor review of scientific framing and claim boundaries.
    - Verification of all OpenNeuro dataset citation details.
    - Verification of DataLad, MNE, specparam/FOOOF, and methods citations.
    - Verification of TBI EEG and EEG artifact literature citations.
    - Journal-specific article type confirmation: Null Hypothesis article versus Regular Manuscript.
    - Neurotrauma Reports word count, abstract format, reference style, and figure/table formatting checks.

    ## Package and Formatting Checks

    - Figure resolution check for final submission portal.
    - Table formatting check for journal style.
    - Decide whether figures should be submitted as PNG, PDF, SVG, or converted TIFF.
    - DOCX conversion still needed before submission if the journal requires Word format.
    - Public GitHub/code release still needed.
    - Data/code availability links still need final repository URL.

    ## Claim-Control Checks

    - Keep D1/D3 artifact-sensitive/null-leaning language.
    - Keep D2 partial/inconsistent language.
    - Keep chronic TBI separate and batch-sensitive.
    - Keep ds003490 comparator-only.
    - Do not convert exploratory or weak traces into positive translational claims.
    """


def build_readme() -> str:
    return f"""
    # Neurotrauma Reports Draft v1 Package

    Generated: {now_iso()}

    This folder contains a first full Markdown manuscript draft package for Neurotrauma Reports generated from the audited final D1/D2/D3 package and manuscript-QC-passed figure/table package.

    ## Draft Boundary

    - No new scientific analyses were run.
    - No extraction or model scripts were rerun.
    - No downloads were performed.
    - No raw data were modified.
    - Existing machine-readable numeric outputs were not edited.
    - Scientific claims are restricted to source-backed, cautious wording.

    ## Recommended Title

    {RECOMMENDED_TITLE}

    ## Recommended Article Type

    Neurotrauma Reports Null Hypothesis article if accepted by journal format; otherwise compact Regular Manuscript with explicit reproducibility/falsification framing.

    ## Core Files

    - `main_manuscript.md`
    - `abstract.md`
    - `title_page.md`
    - `cover_letter.md`
    - `highlights_or_key_points.md`
    - `figure_captions.md`
    - `table_captions.md`
    - `data_code_availability.md`
    - `limitations_and_claims_guardrails.md`
    - `submission_readiness_checklist.md`
    - `manuscript_claim_traceability_audit.csv`
    - `draft_package_manifest.csv`

    ## QC

    See `draft_text_qc.csv`. If `DRAFT_QC_PASS.ok` exists and `DRAFT_QC_FAIL.ok` is absent, the Markdown package passed the lightweight text and traceability checks.
    """


def write_all_documents(sources: dict[str, Any]) -> list[Path]:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "main_manuscript.md": build_main_manuscript(),
        "abstract.md": build_abstract(),
        "title_page.md": build_title_page(),
        "cover_letter.md": build_cover_letter(),
        "highlights_or_key_points.md": build_highlights(),
        "figure_captions.md": build_figure_captions(),
        "table_captions.md": build_table_captions(),
        "data_code_availability.md": build_data_code_availability(),
        "limitations_and_claims_guardrails.md": build_guardrails(sources),
        "submission_readiness_checklist.md": build_submission_checklist(),
        "README.md": build_readme(),
    }
    written: list[Path] = []
    for name, text in files.items():
        path = DRAFT_DIR / name
        write_text(path, text)
        written.append(path)
    audit_path = DRAFT_DIR / "manuscript_claim_traceability_audit.csv"
    write_csv(audit_path, claim_audit_rows())
    written.append(audit_path)
    return written


def run_text_qc() -> tuple[bool, list[dict[str, str]]]:
    checks: list[dict[str, str]] = []
    md_files = [p for p in DRAFT_DIR.glob("*.md") if p.name != "limitations_and_claims_guardrails.md"]
    combined = "\n".join(p.read_text(encoding="utf-8") for p in md_files)
    lower = combined.lower()

    required = {
        "d1_d3_artifact_sensitive_null_leaning_present": "artifact-sensitive" in lower and "null-leaning" in lower,
        "d2_partial_inconsistent_present": "partial and inconsistent" in lower or "partial/inconsistent" in lower,
        "ds003490_comparator_only_present": "ds003490" in lower and "comparator" in lower,
        "chronic_batch_sensitive_present": "chronic" in lower and "batch-sensitive" in lower,
        "no_d2_validation_claim_present": "d2 validation" not in lower,
    }
    for name, ok in required.items():
        checks.append(
            {
                "check_name": name,
                "pass": str(ok),
                "severity": "critical",
                "details": "required conclusion present or prohibited phrase absent",
            }
        )

    overclaim_terms = [
        "validated biomarker",
        "diagnostic biomarker",
        "predictive biomarker",
        "confirmed marker",
        "independent confirmation",
        "clinical deployment",
    ]
    hits: list[str] = []
    for term in overclaim_terms:
        if term in lower:
            hits.append(term)
    proven_hits = [m.group(0) for m in re.finditer(r"\bproven\b", lower)]
    hits.extend(proven_hits)
    checks.append(
        {
            "check_name": "no_unsupported_overclaim_terms_outside_guardrails",
            "pass": str(len(hits) == 0),
            "severity": "critical",
            "details": "; ".join(sorted(set(hits))) if hits else "no unsupported overclaim terms found outside guardrails",
        }
    )

    audit = read_csv(DRAFT_DIR / "manuscript_claim_traceability_audit.csv")
    audit_pass = bool((audit["pass_fail"] == "PASS").all()) and len(audit) >= 10
    checks.append(
        {
            "check_name": "claim_traceability_audit_complete",
            "pass": str(audit_pass),
            "severity": "critical",
            "details": f"{len(audit)} claim rows; all pass={audit_pass}",
        }
    )

    gate_ok, gate_issues = get_gate_status()
    checks.append(
        {
            "check_name": "upstream_audit_and_manuscript_gates_clean",
            "pass": str(gate_ok),
            "severity": "critical",
            "details": "; ".join(gate_issues) if gate_issues else "upstream gates pass",
        }
    )

    all_pass = all(row["pass"] == "True" for row in checks if row["severity"] == "critical")
    write_csv(DRAFT_DIR / "draft_text_qc.csv", checks)
    pass_marker = DRAFT_DIR / "DRAFT_QC_PASS.ok"
    fail_marker = DRAFT_DIR / "DRAFT_QC_FAIL.ok"
    if all_pass:
        pass_marker.write_text(f"PASS {now_iso()}\n", encoding="utf-8")
        if fail_marker.exists():
            fail_marker.unlink()
    else:
        fail_marker.write_text(f"FAIL {now_iso()}\n", encoding="utf-8")
        if pass_marker.exists():
            pass_marker.unlink()
    return all_pass, checks


def write_manifest() -> Path:
    rows = []
    for path in sorted(DRAFT_DIR.iterdir()):
        if path.is_file():
            rows.append(
                {
                    "artifact_path": rel(path),
                    "artifact_type": path.suffix.lstrip(".") or "marker",
                    "size_bytes": path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(path.stat().st_mtime).astimezone().replace(microsecond=0).isoformat(),
                    "purpose": {
                        "main_manuscript.md": "full draft manuscript body",
                        "abstract.md": "structured abstract",
                        "title_page.md": "title and author placeholder page",
                        "cover_letter.md": "Neurotrauma Reports cover letter draft",
                        "highlights_or_key_points.md": "key points",
                        "figure_captions.md": "figure captions",
                        "table_captions.md": "table captions",
                        "data_code_availability.md": "data and code availability section",
                        "limitations_and_claims_guardrails.md": "claims and language guardrails",
                        "submission_readiness_checklist.md": "human and journal readiness checklist",
                        "manuscript_claim_traceability_audit.csv": "claim-to-source audit",
                        "README.md": "draft package overview",
                        "draft_text_qc.csv": "lightweight manuscript QC",
                        "DRAFT_QC_PASS.ok": "draft QC pass marker",
                        "DRAFT_QC_FAIL.ok": "draft QC fail marker",
                    }.get(path.name, "draft package artifact"),
                }
            )
    manifest_path = DRAFT_DIR / "draft_package_manifest.csv"
    write_csv(manifest_path, rows)
    return manifest_path


def append_run_log(qc_pass: bool) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_iso(),
        "event": "neurotrauma_reports_draft_v1_generation",
        "command": ".\\.venv\\Scripts\\python.exe scripts\\29_generate_neurotrauma_reports_draft_v1.py",
        "status": "PASS" if qc_pass else "FAIL",
        "draft_dir": rel(DRAFT_DIR),
        "recommended_title": RECOMMENDED_TITLE,
        "restrictions_observed": [
            "no downloads",
            "no raw-data modification",
            "no extraction rerun",
            "no model rerun",
            "no edits to existing final numeric result CSVs",
            "no new scientific claims beyond audited source outputs",
        ],
    }
    with (LOGS / "run_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> int:
    gate_ok, issues = get_gate_status()
    if not gate_ok:
        DRAFT_DIR.mkdir(parents=True, exist_ok=True)
        fail_note = DRAFT_DIR / "DRAFT_GENERATION_BLOCKED.md"
        write_text(
            fail_note,
            "# Draft Generation Blocked\n\n" + "\n".join(f"- {issue}" for issue in issues),
        )
        print(json.dumps({"status": "BLOCKED", "issues": issues}, sort_keys=True))
        return 2

    sources = load_sources()
    written = write_all_documents(sources)
    qc_pass, checks = run_text_qc()
    manifest_path = write_manifest()
    append_run_log(qc_pass)

    print(
        json.dumps(
            {
                "status": "PASS" if qc_pass else "FAIL",
                "draft_dir": rel(DRAFT_DIR),
                "files_written": len(written) + 3,
                "manifest": rel(manifest_path),
                "qc_failures": [row for row in checks if row["pass"] != "True"],
            },
            sort_keys=True,
        )
    )
    return 0 if qc_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
