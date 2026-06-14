from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
REPORTS = PROJECT / "reports"
FINAL = PROJECT / "outputs" / "final"
QC = PROJECT / "outputs" / "qc"


REQUIRED_SOURCES = [
    "reports/39_final_analysis_package_integrity_report.md",
    "reports/40_final_scientific_synthesis_and_publishability_report.md",
    "reports/41_reproduction_and_handoff_guide.md",
    "outputs/final/d1_d2_d3_evidence_matrix.csv",
    "outputs/final/key_result_claims_traceability.csv",
    "outputs/final/final_deliverable_manifest.csv",
    "reports/36_integrated_d1_d2_d3_final_decision_report.md",
    "reports/35_d2_bounded_falsification_report.md",
    "reports/28_d1_d3_post_analysis_audit.md",
    "reports/37_stale_parallel_job_accuracy_audit.md",
    "reports/38_stale_report_repair_log.md",
]


JOURNAL_SOURCES = [
    {
        "journal": "Neurotrauma Reports",
        "url": "https://journals.sagepub.com/author-instructions/ntr",
        "basis": "Author instructions list Regular Manuscript, Short Communications, and Null Hypothesis article types.",
    },
    {
        "journal": "Frontiers in Neurology - Neurotrauma",
        "url": "https://www.frontiersin.org/journals/neurology/sections/neurotrauma/about",
        "basis": "Section scope includes traumatic injuries to the nervous system and biomarkers for injury, with clinical/translational linkage.",
    },
    {
        "journal": "Brain Injury",
        "url": "https://www.internationalbrain.org/publications/official-journal-brain-injury",
        "basis": "IBIA describes Brain Injury as multidisciplinary and focused on empirical studies, reviews, and case studies across brain-injury care and outcomes.",
    },
    {
        "journal": "Clinical Neurophysiology",
        "url": "https://www.ifcn.info/publications/clinical-neurophysiology-journal",
        "basis": "IFCN scope emphasizes pathophysiology of peripheral and central nervous-system disease and substantial contribution; negative studies need knowledge advance.",
    },
    {
        "journal": "NeuroImage: Clinical",
        "url": "https://shop.elsevier.com/journals/neuroimage/1053-8119",
        "basis": "Elsevier describes NeuroImage: Clinical as focused on pathology, abnormal development, and biomarker usage; NeuroImage: Reports is noted as more tolerant of null/replication work.",
    },
    {
        "journal": "Scientific Reports",
        "url": "https://www.nature.com/srep/about",
        "basis": "Scientific Reports publishes original research across natural sciences, medicine, psychology, and engineering.",
    },
    {
        "journal": "PLOS ONE",
        "url": "https://journals.plos.org/plosone/s/what-we-publish",
        "basis": "PLOS ONE considers rigorous research articles across science and medicine and explicitly considers negative and null results.",
    },
    {
        "journal": "Data in Brief",
        "url": "https://www.elsevier.support/publishing/answer/cosubmission-to-data-in-brief-and-methodsx",
        "basis": "Elsevier describes Data in Brief/MethodsX co-submissions for research data, methods, and protocols that support open science and reproducibility.",
    },
    {
        "journal": "F1000Research",
        "url": "https://f1000research.com/for-authors/article-guidelines",
        "basis": "F1000Research encourages null/negative findings and reanalyses, and offers Research Articles, Brief Reports, and Data Notes.",
    },
]


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def require_gate() -> dict:
    gate_path = QC / "audit_gate.json"
    pass_marker = QC / "AUDIT_PASS.ok"
    fail_marker = QC / "AUDIT_FAIL.ok"
    if not gate_path.exists():
        raise SystemExit("Missing outputs/qc/audit_gate.json.")
    if not pass_marker.exists():
        raise SystemExit("Missing outputs/qc/AUDIT_PASS.ok.")
    if fail_marker.exists():
        raise SystemExit("outputs/qc/AUDIT_FAIL.ok exists.")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("gate") != "PASS" or gate.get("safe_to_continue") is not True or gate.get("next_prompt_allowed") is not True:
        raise SystemExit(f"Audit gate is not clean PASS: {gate}")
    return gate


def require_sources() -> None:
    missing = [p for p in REQUIRED_SOURCES if not (PROJECT / p).exists()]
    if missing:
        raise SystemExit("Missing required source files: " + ", ".join(missing))


def read_values() -> dict[str, str]:
    checks = pd.read_csv(PROJECT / "outputs/qc/final_result_consistency_checks.csv")
    return {
        row["check_name"]: str(row["observed_value_or_claim"])
        for _, row in checks.iterrows()
    }


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


def f4(value: str) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return value


def journal_rows() -> list[dict]:
    return [
        {
            "journal": "Neurotrauma Reports",
            "article_type": "Null Hypothesis or Regular Manuscript",
            "fit_rating": "realistic_best_fit",
            "likely_reviewer_reaction": "Likely receptive if framed as neurotrauma-focused null/reproducibility work with clear translational humility.",
            "strengths": "TBI fit; explicit Null Hypothesis option; compact format suits a focused falsification report.",
            "risks": "Must avoid sounding like a biomarker-discovery paper; space limits require tight figures and tables.",
            "required_framing": "Artifact-sensitive public EEG reproducibility/falsification report in acute mTBI, with chronic branch separate.",
            "recommendation": "Top target after one figure/QC pass.",
        },
        {
            "journal": "Frontiers in Neurology - Neurotrauma",
            "article_type": "Original Research",
            "fit_rating": "realistic_good_fit",
            "likely_reviewer_reaction": "Receptive to neurotrauma scope, but reviewers may want clearer clinical or mechanistic implications.",
            "strengths": "Section scope covers TBI, biomarkers for injury, and translational neurotrauma questions.",
            "risks": "Open-ended article format could tempt overclaiming; negative result needs strong open-science rationale.",
            "required_framing": "Transparent neurotrauma signal-discovery and falsification analysis, not marker validation.",
            "recommendation": "Strong second target.",
        },
        {
            "journal": "Brain Injury",
            "article_type": "Original empirical study",
            "fit_rating": "conditional_fit",
            "likely_reviewer_reaction": "Interested in brain-injury relevance, but may question EEG-methods depth and practical clinical payoff.",
            "strengths": "Brain-injury readership; multidisciplinary and clinically adjacent.",
            "risks": "Null/methods-heavy paper may feel less compelling without clear clinical translation.",
            "required_framing": "Clinical caution: public EEG candidate did not support robust acute mTBI signal after artifact control.",
            "recommendation": "Reasonable if the Discussion is clinically accessible.",
        },
        {
            "journal": "Clinical Neurophysiology",
            "article_type": "Original Research or Short Communication",
            "fit_rating": "stretch",
            "likely_reviewer_reaction": "Methodologically demanding reviewers may ask for stronger EEG preprocessing, aperiodic modeling, and larger contribution.",
            "strengths": "EEG/neurophysiology technical audience; artifact-control story is relevant.",
            "risks": "Journal has lower priority for negative studies unless they clearly advance knowledge; current signal may be too modest.",
            "required_framing": "EEG-methods rigor and artifact sensitivity as the main contribution, with no clinical marker claim.",
            "recommendation": "Stretch target only after figure/methods polish.",
        },
        {
            "journal": "NeuroImage: Clinical",
            "article_type": "Original Research",
            "fit_rating": "poor_to_stretch",
            "likely_reviewer_reaction": "May see the current package as insufficiently strong for clinical neuroimaging impact.",
            "strengths": "Open clinical neuroimaging venue; public-data and methods angle may interest some reviewers.",
            "risks": "EEG-only, null-leaning result and lack of robust marker effect are a hard sell.",
            "required_framing": "Robust neuroimaging reproducibility/methods paper, not TBI biomarker discovery.",
            "recommendation": "Not recommended as first submission.",
        },
        {
            "journal": "Scientific Reports",
            "article_type": "Article",
            "fit_rating": "realistic_broad_fit",
            "likely_reviewer_reaction": "Likely to focus on methodological validity and reproducibility rather than novelty alone.",
            "strengths": "Broad biomedical scope; accepts original research across medicine and engineering.",
            "risks": "Reviewer expertise may be broad; TBI-specific contribution must be made plain.",
            "required_framing": "Scientifically valid open-data EEG reproducibility study with negative/mixed results.",
            "recommendation": "Good broad fallback if neurotrauma targets are not preferred.",
        },
        {
            "journal": "PLOS ONE",
            "article_type": "Research Article",
            "fit_rating": "realistic_good_fallback",
            "likely_reviewer_reaction": "Receptive if methods are rigorous, data/code availability is strong, and conclusions are conservative.",
            "strengths": "Explicitly considers negative and null results; broad scope; strong fit for reproducibility.",
            "risks": "Needs a clearly defined research question and robust methods transparency.",
            "required_framing": "Methodologically rigorous public-data falsification analysis.",
            "recommendation": "Excellent fallback or co-top target for null/reproducibility framing.",
        },
        {
            "journal": "Data in Brief",
            "article_type": "Data Article or co-submission",
            "fit_rating": "poor_as_standalone_conditional_as_companion",
            "likely_reviewer_reaction": "Not suitable for the interpretive analysis as-is; possible companion if packaged as reusable derived data/methods object.",
            "strengths": "Supports open science and reusable data objects.",
            "risks": "Data articles should not carry the main interpretive conclusions.",
            "required_framing": "Derived feature/QC dataset description only, paired with a separate research article.",
            "recommendation": "Do not target as the main manuscript.",
        },
        {
            "journal": "F1000Research",
            "article_type": "Research Article or Brief Report",
            "fit_rating": "realistic_open_reproducibility_fit",
            "likely_reviewer_reaction": "Likely receptive to transparent null/reanalysis framing; post-publication review requires strong source openness.",
            "strengths": "Welcomes null/negative findings and reanalyses; good transparency/reproducibility culture.",
            "risks": "Less conventional prestige path; open peer-review format requires comfort with visible revisions.",
            "required_framing": "Open, source-backed reanalysis and falsification of public TBI EEG candidate.",
            "recommendation": "Good alternative if speed/transparency are prioritized.",
        },
    ]


def allowlist_rows() -> list[dict]:
    return [
        {
            "claim_id": "A01",
            "claim_text": "Artifact-controlled analyses did not support a robust acute mTBI resting EEG marker in this public OpenNeuro cohort.",
            "why_allowed_or_blocked": "Directly reflects D1 broad artifact-controlled FDR failure.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md; outputs/qc/final_result_consistency_checks.csv",
            "caveat": "Use marker only as a negated claim; do not imply clinical validation was achieved.",
            "acceptable_wording": "did not support a robust acute mTBI resting EEG marker",
            "unacceptable_wording": "identified a robust acute mTBI EEG marker",
        },
        {
            "claim_id": "A02",
            "claim_text": "The initially promising aperiodic/spectral signal attenuated under artifact-control and cross-task testing.",
            "why_allowed_or_blocked": "Supported by D1 attenuation against prior anchor and D2 mixed task results.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md; reports/35_d2_bounded_falsification_report.md",
            "caveat": "Original exact row-level model outputs were not locally available.",
            "acceptable_wording": "attenuated under artifact-control and cross-task testing",
            "unacceptable_wording": "was confirmed after artifact-control and cross-task testing",
        },
        {
            "claim_id": "A03",
            "claim_text": "Acute mTBI vs control did not survive broad artifact-controlled FDR.",
            "why_allowed_or_blocked": "Final consistency checks report D1 acute broad minimum q around 0.7876.",
            "source_evidence": "outputs/qc/final_result_consistency_checks.csv; reports/36_integrated_d1_d2_d3_final_decision_report.md",
            "caveat": "Narrow prior-anchor result is exploratory and not confirmatory.",
            "acceptable_wording": "did not survive broad artifact-controlled FDR",
            "unacceptable_wording": "survived artifact-controlled correction",
        },
        {
            "claim_id": "A04",
            "claim_text": "D3 eyes-closed alpha/IAF did not rescue the acute signal.",
            "why_allowed_or_blocked": "D3 posterior acute minimum q around 0.9149.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md; outputs/final/key_result_claims_traceability.csv",
            "caveat": "Generated D3 table lacks aperiodic-adjusted alpha peak metrics.",
            "acceptable_wording": "did not rescue or support the acute signal",
            "unacceptable_wording": "provided confirmatory alpha evidence",
        },
        {
            "claim_id": "A05",
            "claim_text": "Cross-task D2 analyses provided partial/inconsistent support rather than standalone cohort confirmation.",
            "why_allowed_or_blocked": "D2 has only one weak q<0.10 cue-baseline trace and no mixed-model group terms below q<0.10.",
            "source_evidence": "reports/35_d2_bounded_falsification_report.md; outputs/d2_cross_task/d2_falsification_summary.csv",
            "caveat": "D2 overlaps by Original_ID and is not an independent cohort.",
            "acceptable_wording": "partial/inconsistent bounded cross-task support",
            "unacceptable_wording": "independently confirmed in D2",
        },
        {
            "claim_id": "A06",
            "claim_text": "DPX cue-baseline showed a weak exploratory trace, but task-average DPX, VWM, and mixed models did not support robust convergence.",
            "why_allowed_or_blocked": "Preserves the only weak D2 trace while foregrounding non-convergence.",
            "source_evidence": "reports/35_d2_bounded_falsification_report.md; outputs/qc/final_result_consistency_checks.csv",
            "caveat": "Cue-baseline q<0.10 is exploratory and context-specific.",
            "acceptable_wording": "weak exploratory DPX cue-baseline trace",
            "unacceptable_wording": "DPX validated the resting EEG signal",
        },
        {
            "claim_id": "A07",
            "claim_text": "Chronic TBI findings should be reported separately as exploratory and batch-sensitive.",
            "why_allowed_or_blocked": "Chronic branch has q around 0.3484 and recruitment/batch caveats.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md; outputs/final/d1_d2_d3_evidence_matrix.csv",
            "caveat": "Do not use chronic results to prove acute mTBI effects.",
            "acceptable_wording": "exploratory and batch-sensitive chronic branch",
            "unacceptable_wording": "chronic TBI proves the acute signal",
        },
        {
            "claim_id": "A08",
            "claim_text": "These findings motivate preregistered artifact-controlled confirmatory work.",
            "why_allowed_or_blocked": "Final package recommends a prospective, preregistered confirmatory study rather than current validation.",
            "source_evidence": "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "caveat": "The current manuscript should not imply the confirmatory study has already been done.",
            "acceptable_wording": "motivate preregistered artifact-controlled confirmatory work",
            "unacceptable_wording": "are ready for clinical deployment",
        },
    ]


def blocklist_rows() -> list[dict]:
    return [
        {
            "claim_id": "B01",
            "claim_text": "validated biomarker",
            "why_allowed_or_blocked": "Blocked because no D1/D3/D2 pattern supports marker validation.",
            "source_evidence": "reports/36_integrated_d1_d2_d3_final_decision_report.md; outputs/final/key_result_claims_traceability.csv",
            "caveat": "Future prospective validation could change this, but current outputs cannot.",
            "acceptable_wording": "no marker-validation claim is supported",
            "unacceptable_wording": "validated biomarker",
        },
        {
            "claim_id": "B02",
            "claim_text": "diagnostic biomarker",
            "why_allowed_or_blocked": "Blocked because no diagnostic model or clinically validated threshold exists.",
            "source_evidence": "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "caveat": "The package is not a diagnostic accuracy study.",
            "acceptable_wording": "candidate signal did not support diagnostic use",
            "unacceptable_wording": "diagnostic biomarker",
        },
        {
            "claim_id": "B03",
            "claim_text": "predictive biomarker",
            "why_allowed_or_blocked": "Blocked because no prospective prediction or outcome model was run.",
            "source_evidence": "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "caveat": "No symptom or outcome prediction endpoint is supported.",
            "acceptable_wording": "not evaluated as a predictive endpoint",
            "unacceptable_wording": "predictive biomarker",
        },
        {
            "claim_id": "B04",
            "claim_text": "confirmed EEG signature",
            "why_allowed_or_blocked": "Blocked because broad FDR and cross-task convergence did not hold.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md; reports/35_d2_bounded_falsification_report.md",
            "caveat": "A weak/context-specific trace is not confirmation.",
            "acceptable_wording": "initially promising EEG candidate attenuated",
            "unacceptable_wording": "confirmed EEG signature",
        },
        {
            "claim_id": "B05",
            "claim_text": "independently replicated signal",
            "why_allowed_or_blocked": "Blocked because D2 overlaps by Original_ID and did not provide robust convergence.",
            "source_evidence": "reports/35_d2_bounded_falsification_report.md; reports/33_d2_subject_overlap_report.md",
            "caveat": "Within-subject stability is not independent replication.",
            "acceptable_wording": "bounded cross-task check with overlapping identities",
            "unacceptable_wording": "independently replicated signal",
        },
        {
            "claim_id": "B06",
            "claim_text": "D2 validation",
            "why_allowed_or_blocked": "Blocked because D2 is partial/inconsistent and not independent.",
            "source_evidence": "outputs/d2_cross_task/d2_falsification_summary.csv; reports/35_d2_bounded_falsification_report.md",
            "caveat": "DPX cue-baseline is a weak exploratory trace only.",
            "acceptable_wording": "D2 bounded falsification/reproducibility check",
            "unacceptable_wording": "D2 validation",
        },
        {
            "claim_id": "B07",
            "claim_text": "chronic TBI proof",
            "why_allowed_or_blocked": "Blocked because chronic branch is batch-sensitive and secondary.",
            "source_evidence": "reports/28_d1_d3_post_analysis_audit.md",
            "caveat": "Chronic and acute must remain separate.",
            "acceptable_wording": "chronic branch remains exploratory and batch-sensitive",
            "unacceptable_wording": "chronic TBI proof",
        },
        {
            "claim_id": "B08",
            "claim_text": "ds003490 TBI validation",
            "why_allowed_or_blocked": "Blocked because ds003490 is a comparator/pipeline rehearsal dataset, not TBI evidence.",
            "source_evidence": "reports/22_ds003490_feature_readiness_report.md; outputs/final/d1_d2_d3_evidence_matrix.csv",
            "caveat": "It may support methods readiness only.",
            "acceptable_wording": "ds003490 comparator/pipeline rehearsal",
            "unacceptable_wording": "ds003490 TBI validation",
        },
        {
            "claim_id": "B09",
            "claim_text": "symptom prediction",
            "why_allowed_or_blocked": "Blocked because clinical symptom/cognitive prediction was not established in the final package.",
            "source_evidence": "reports/40_final_scientific_synthesis_and_publishability_report.md",
            "caveat": "No supported symptom endpoint belongs in the main claim set.",
            "acceptable_wording": "future studies should collect symptom covariates",
            "unacceptable_wording": "predicts symptoms",
        },
        {
            "claim_id": "B10",
            "claim_text": "clinical deployment",
            "why_allowed_or_blocked": "Blocked because the current work is exploratory/falsification-oriented and not clinically validated.",
            "source_evidence": "reports/36_integrated_d1_d2_d3_final_decision_report.md",
            "caveat": "Clinical deployment requires prospective validation, thresholds, and utility evidence.",
            "acceptable_wording": "not ready for clinical use",
            "unacceptable_wording": "ready for clinical deployment",
        },
        {
            "claim_id": "B11",
            "claim_text": "black-box classifier rescue",
            "why_allowed_or_blocked": "Blocked because the final package explicitly rejects classifier-based significance rescue.",
            "source_evidence": "reports/36_integrated_d1_d2_d3_final_decision_report.md; reports/41_reproduction_and_handoff_guide.md",
            "caveat": "A new preregistered predictive design would be a different study.",
            "acceptable_wording": "no classifier rescue was attempted",
            "unacceptable_wording": "classification rescues the signal",
        },
    ]


def figure_table_rows() -> list[dict]:
    return [
        {
            "item_id": "Figure 1",
            "item_type": "figure",
            "title": "Dataset and workflow schematic",
            "purpose": "Orient readers to ds003522, ds005114, ds003523, ds003490, and the D1/D2/D3 audit flow.",
            "source_files": "outputs/figures/fig01_dataset_task_overview.png; outputs/final/final_deliverable_manifest.csv",
            "required_panels_or_columns": "Dataset roles; retrieval verification; D1/D3/D2 flow; ds003490 comparator label",
            "claim_supported": "The analysis is a traceable public-data falsification workflow.",
            "caveats_shown": "ds003490 is comparator only; D2 overlaps by identity.",
            "already_available_or_needs_generation": "partly_available_needs_manuscript_polish",
            "priority_level": "high",
        },
        {
            "item_id": "Figure 2",
            "item_type": "figure",
            "title": "D1 original-anchor versus artifact-controlled attenuation",
            "purpose": "Show how the promising D1 anchor attenuates under artifact-trimmed broad FDR.",
            "source_files": "reports/28_d1_d3_post_analysis_audit.md; outputs/qc/d1_d3_key_effect_trace.csv; outputs/qc/final_result_consistency_checks.csv",
            "required_panels_or_columns": "Original anchor summary; artifact-trimmed effect sizes; FDR q annotations; prior-anchor caveat",
            "claim_supported": "The initially promising signal attenuated and did not survive broad artifact-controlled FDR.",
            "caveats_shown": "Original exact per-feature rows unavailable; prior anchor is prose-based.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "highest",
        },
        {
            "item_id": "Figure 3",
            "item_type": "figure",
            "title": "Artifact-branch sample retention and QC",
            "purpose": "Explain why ptp95 is interpretable as a sensitivity branch and strict 250 uV is not.",
            "source_files": "outputs/qc/d1_d3_artifact_branch_sample_counts.csv; reports/28_d1_d3_post_analysis_audit.md",
            "required_panels_or_columns": "Branch by group/state retention; usable epoch fraction; exclusion reasons",
            "claim_supported": "Strict artifact-clean filtering was overconservative; ptp95 preserves coverage while trimming epochs.",
            "caveats_shown": "ptp95 is not gold-standard artifact correction.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "high",
        },
        {
            "item_id": "Figure 4",
            "item_type": "figure",
            "title": "D3 eyes-closed alpha/IAF non-supportive endpoint",
            "purpose": "Show that the lower-artifact eyes-closed alpha/IAF branch does not rescue the D1 signal.",
            "source_files": "outputs/features/d3_ec_alpha_iaf_features.csv; outputs/models/d1_d3_group_models.csv; outputs/qc/final_result_consistency_checks.csv",
            "required_panels_or_columns": "Posterior alpha/IAF rows; q=0.9149 callout; missing aperiodic-adjusted alpha metric note",
            "claim_supported": "D3 does not rescue the acute signal.",
            "caveats_shown": "Aperiodic-adjusted alpha peak unavailable in generated D3 table.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "medium",
        },
        {
            "item_id": "Figure 5",
            "item_type": "figure",
            "title": "D2 bounded cross-task falsification",
            "purpose": "Display DPX cue-baseline weak trace beside non-supportive DPX task-average, VWM, and mixed-model results.",
            "source_files": "outputs/d2_cross_task/d2_falsification_summary.csv; outputs/d2_cross_task/d2_within_dataset_group_effects.csv; outputs/d2_cross_task/d2_mixed_effects_models.csv",
            "required_panels_or_columns": "Cue-baseline q and abs(g); task-average q values; mixed q<0.10 count; identity-overlap caveat",
            "claim_supported": "D2 is partial/inconsistent, not validation.",
            "caveats_shown": "D2 overlaps by Original_ID and is not independent confirmation.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "highest",
        },
        {
            "item_id": "Figure 6",
            "item_type": "figure",
            "title": "Evidence matrix and final decision",
            "purpose": "Summarize D1, D3, chronic, D2, and ds003490 roles in one decision graphic.",
            "source_files": "outputs/final/d1_d2_d3_evidence_matrix.csv; outputs/final/key_result_claims_traceability.csv",
            "required_panels_or_columns": "Evidence stream; support/weakening; manuscript use; forbidden overclaim markers",
            "claim_supported": "The only defensible framing is null-leaning reproducibility/falsification.",
            "caveats_shown": "No marker-validation claim; chronic and ds003490 guardrails.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "medium",
        },
        {
            "item_id": "Table 1",
            "item_type": "table",
            "title": "Dataset and cohort table",
            "purpose": "Document dataset roles, raw EEG counts, task/state, and TBI relevance.",
            "source_files": "reports/39_final_analysis_package_integrity_report.md; outputs/download_recovery/*.csv",
            "required_panels_or_columns": "Dataset; role; .set/.fdt counts; MNE checks; task/state; TBI role",
            "claim_supported": "Raw data were verified before interpretation.",
            "caveats_shown": "ds003490 comparator only.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "high",
        },
        {
            "item_id": "Table 2",
            "item_type": "table",
            "title": "Locked feature and analysis families",
            "purpose": "Preempt concerns about post hoc flexibility by showing planned families and exploratory transparency families.",
            "source_files": "outputs/qc/d1_d3_model_family_audit.csv; outputs/d2_cross_task/d2_harmonized_feature_dictionary.csv",
            "required_panels_or_columns": "Family; comparison; branch/window; n tests; exploratory vs primary status",
            "claim_supported": "The analysis distinguishes broad FDR families from exploratory slices.",
            "caveats_shown": "Narrow prior-anchor family is not confirmatory.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "high",
        },
        {
            "item_id": "Table 3",
            "item_type": "table",
            "title": "Key D1/D3/D2 results",
            "purpose": "Give exact q-values, effect summaries, and interpretation in one manuscript table.",
            "source_files": "outputs/qc/final_result_consistency_checks.csv; outputs/final/d1_d2_d3_evidence_matrix.csv",
            "required_panels_or_columns": "Domain; metric; q value; effect summary; interpretation; manuscript use",
            "claim_supported": "The overall pattern is null-leaning with a weak D2 trace only.",
            "caveats_shown": "No validation or clinical marker claim.",
            "already_available_or_needs_generation": "needs_generation_from_existing_outputs",
            "priority_level": "highest",
        },
        {
            "item_id": "Table 4",
            "item_type": "table",
            "title": "Claims and caveats traceability",
            "purpose": "Make manuscript claims auditable against final source files.",
            "source_files": "outputs/final/key_result_claims_traceability.csv; outputs/final/manuscript_claim_allowlist.csv; outputs/final/manuscript_claim_blocklist.csv",
            "required_panels_or_columns": "Claim; allowed wording; source; caveat; forbidden overclaim",
            "claim_supported": "Claims are traceable and conservative.",
            "caveats_shown": "Blocked claims are explicit.",
            "already_available_or_needs_generation": "partly_available_needs_formatting",
            "priority_level": "medium",
        },
        {
            "item_id": "Table 5",
            "item_type": "table",
            "title": "Limitations and mitigations",
            "purpose": "Turn reviewer concerns into transparent limitations with mitigation language.",
            "source_files": "reports/40_final_scientific_synthesis_and_publishability_report.md; reports/42_manuscript_viability_and_strategy_report.md",
            "required_panels_or_columns": "Concern; why it matters; mitigation; residual risk",
            "claim_supported": "The manuscript foregrounds limitations rather than hiding them.",
            "caveats_shown": "Original rows unavailable; artifact branch caveats; D2 identity overlap.",
            "already_available_or_needs_generation": "needs_generation_from_current_reports",
            "priority_level": "medium",
        },
    ]


def source_links_md() -> str:
    return "\n".join(f"- [{s['journal']}]({s['url']}): {s['basis']}" for s in JOURNAL_SOURCES)


def viability_report(values: dict[str, str]) -> str:
    return f"""
# Manuscript Viability And Strategy Report

Generated: {now()}

## Technical Summary

**Recommendation: conditional go.** There is a publishable manuscript here if it is framed as a transparent artifact-sensitivity, reproducibility, and falsification report. The manuscript should not be framed as a positive EEG marker discovery. The central contribution is that an initially promising public EEG TBI signal becomes artifact-sensitive/null-leaning after broad artifact-controlled FDR, D3 eyes-closed checks, and bounded D2 cross-task testing.

## Is There A Publishable Manuscript Here?

Yes, but the publishable unit is modest and must be written with unusual honesty. The current package is strongest as a reproducibility/falsification paper using public OpenNeuro EEG data. It is not strong enough for a biomarker-discovery manuscript, a diagnostic claim, a predictive claim, or a clinical-deployment narrative.

The result is still valuable because negative and mixed findings are informative when the pipeline is traceable: raw EEG retrieval was verified, stale outputs were audited, claims are traceable, and the interpretation is explicitly bounded.

## Honest Central Contribution

The manuscript contribution is: **a transparent public-data EEG analysis showing how a plausible resting TBI spectral/aperiodic candidate attenuates under artifact control and only partially/inconsistently generalizes across task contexts.**

Key values that define the contribution:

| evidence area | key result | manuscript implication |
| --- | --- | --- |
| D1 acute broad artifact-controlled family | min q = {f4(values['d1_acute_broad_min_q'])} | No robust acute mTBI resting signal after broad FDR. |
| D1 narrow prior-anchor family | q = {f4(values['d1_narrow_prior_anchor_q'])} | Exploratory only, not a rescued endpoint. |
| D3 eyes-closed alpha/IAF | min q = {f4(values['d3_acute_posterior_q'])} | Does not rescue the acute signal. |
| Chronic TBI | min q = {f4(values['chronic_trim_min_q'])} | Exploratory and batch-sensitive. |
| D2 DPX cue-baseline | min q = {f4(values['ds005114_cue_baseline_min_q'])}; max abs(g) = {f4(values['ds005114_cue_baseline_max_abs_g'])} | Only weak/context-specific q<0.10 trace. |
| D2 task-average and mixed models | DPX q = {f4(values['dpx_task_average_min_q'])}; VWM q = {f4(values['vwm_task_average_min_q'])}; mixed group q<0.10 count = {values['mixed_models_group_q_lt_0p10']} | No robust cross-task convergence. |

## If Not Publishable, What Would Be Needed?

For a stronger clinical-neurophysiology or clinical-neuroimaging submission, the minimum would be a prospective or externally independent validation cohort, preregistered artifact handling, exact primary endpoints, aperiodic-adjusted alpha/IAF metrics, and no identity overlap between discovery and validation samples.

For the current package, no new scientific analysis is required before drafting, but one manuscript-specific QC and figure-generation pass is recommended. That pass should generate manuscript figures from existing outputs only, verify figure captions against the claim allowlist, and freeze the claim/blocklist before text drafting.

## Strongest Framing

The strongest framing is **artifact-sensitivity/null-leaning reproducibility report**. The second strongest is **transparent OpenNeuro TBI EEG signal-discovery and falsification report**. A methods/data-resource framing is viable if the paper emphasizes raw-data recovery, traceability, and reusable analysis outputs.

The paper can also be described as a cautionary EEG marker story, but that should be a discussion angle rather than the title-level claim.

## Framing To Avoid

- Positive marker discovery.
- Diagnostic, predictive, prognostic, or clinical-utility framing.
- Independent replication or D2 validation.
- Chronic TBI as proof of acute mTBI effects.
- `ds003490` as TBI evidence.
- Black-box classification rescue.

## Likely Reviewer Concerns And Mitigations

| concern | why it matters | mitigation |
| --- | --- | --- |
| Original D1 exact per-feature rows unavailable | Reviewers may worry the original signal is not fully reproducible. | State this explicitly and treat the original as a documented prior anchor, not a result being confirmed. |
| Artifact correction is imperfect | ptp95 is a sensitivity branch, not gold-standard artifact removal. | Present strict-branch failure and ptp95 retention transparently; avoid artifact-free language. |
| Negative/mixed findings may seem low novelty | Some journals prioritize positive discoveries. | Emphasize traceable public-data falsification and how apparent EEG signals attenuate under realistic controls. |
| D2 is not independent | D2 overlaps by Original_ID. | Make D2 a bounded cross-task check, not a validation cohort. |
| Chronic TBI effects look larger | Reviewers may ask why not foreground chronic findings. | Keep chronic separate as exploratory and batch-sensitive. |
| ds003490 is not TBI | Reviewers may object if it is used as disease evidence. | Label it comparator/pipeline rehearsal only or omit from main Results. |

## Framing Decision

| framing option | recommendation | reason |
| --- | --- | --- |
| artifact-sensitivity/reproducibility report | strongest | Directly matches final evidence and reviewer-proof caveats. |
| transparent null/falsification report | strong | Works well for PLOS ONE, F1000Research, and possibly Neurotrauma Reports Null Hypothesis. |
| OpenNeuro methods/data-resource report | conditional | Strong if figure/data packaging is polished and source traceability is central. |
| EEG marker cautionary tale | secondary angle | Useful in Discussion, but too rhetorical as the main submission strategy. |
| not manuscript-ready | not selected | The final package is coherent enough for a conservative manuscript after figure/QC pass. |

## Minimum Additional Work Before Drafting

1. Generate manuscript figures/tables from existing outputs only.
2. Freeze the allowlist/blocklist and require every Results sentence to map to one allowed claim.
3. Decide first submission target and article type.
4. Run a manuscript-specific stale/overclaim phrase scan after the draft exists.
5. Prepare a concise source/data/code availability statement.

## Candidate Titles

1. Artifact-sensitive resting EEG signals in public traumatic brain injury datasets.
2. A transparent falsification analysis of resting EEG candidate signals in traumatic brain injury.
3. When exploratory EEG signatures attenuate under artifact control: a public TBI data analysis.
4. Artifact control and cross-task testing weaken a candidate resting EEG signal in mild traumatic brain injury.
5. Null-leaning reproducibility analysis of aperiodic and spectral EEG features in public TBI data.
6. Public EEG reanalysis of traumatic brain injury candidate signals under artifact-control stress testing.
7. From promising EEG candidate to bounded falsification: an OpenNeuro TBI reproducibility analysis.
8. Artifact-sensitive aperiodic and spectral EEG findings in public mild TBI data.
9. Cross-task checks do not confirm a resting EEG candidate signal in public TBI datasets.
10. A cautionary public-data study of resting EEG candidate signals in traumatic brain injury.

## Preliminary Structured Abstract Skeleton

This is a skeleton only, not a manuscript draft.

**Background:** Public EEG datasets can support transparent tests of candidate neurophysiological signals in traumatic brain injury, but artifact sensitivity and cross-task reproducibility remain major concerns.

**Methods:** Briefly describe verified OpenNeuro retrieval, D1 resting artifact-control analyses, D3 eyes-closed alpha/IAF sensitivity, and bounded D2 cross-task falsification using prespecified feature families and FDR control.

**Results:** State the negative/mixed results with exact key q-values: D1 broad q={f4(values['d1_acute_broad_min_q'])}, D3 q={f4(values['d3_acute_posterior_q'])}, D2 cue-baseline q={f4(values['ds005114_cue_baseline_min_q'])}, task-average/mixed non-convergence.

**Conclusions:** A candidate resting EEG signal was artifact-sensitive and not robustly supported after artifact control and cross-task testing; findings motivate preregistered confirmatory work rather than clinical marker claims.

## Final Strategy Recommendation

Draft after one figure-generation and manuscript-QC pass. The next prompt should be:

```text
Using the manuscript strategy package, generate manuscript-ready figures and tables from existing outputs only. Do not rerun analyses. Produce figure/table files, captions, and a caption-to-claim traceability table before drafting text.
```
"""


def journal_report() -> str:
    rows = journal_rows()
    table = "\n".join(
        f"| {r['journal']} | {r['article_type']} | {r['fit_rating']} | {r['recommendation']} |"
        for r in rows
    )
    details = "\n\n".join(
        f"### {r['journal']}\n"
        f"- Fit: {r['fit_rating']}.\n"
        f"- Likely article type: {r['article_type']}.\n"
        f"- Likely reviewer reaction: {r['likely_reviewer_reaction']}\n"
        f"- Strengths: {r['strengths']}\n"
        f"- Risks: {r['risks']}\n"
        f"- Required emphasis: {r['required_framing']}\n"
        f"- Recommendation: {r['recommendation']}"
        for r in rows
    )
    return f"""
# Candidate Journal And Article Type Assessment

Generated: {now()}

## Technical Summary

The strongest first target is **Neurotrauma Reports**, ideally as a Null Hypothesis or compact Regular Manuscript, because the paper is TBI-focused and null/reproducibility-forward. **Frontiers in Neurology - Neurotrauma** is a strong second target if the framing emphasizes public neurotrauma signal falsification. **PLOS ONE** and **F1000Research** are the best broad/open reproducibility fallback venues.

## Source Basis

Journal fit was checked against current official or publisher/official-society pages where accessible:

{source_links_md()}

## Target Matrix Summary

| journal | likely article type | fit rating | recommendation |
| --- | --- | --- | --- |
{table}

## Journal-Level Assessment

{details}

## Practical Submission Order

1. Neurotrauma Reports: strongest alignment if the Null Hypothesis format can accommodate the full story.
2. Frontiers in Neurology - Neurotrauma: strong if the manuscript foregrounds neurotrauma relevance and open-science falsification.
3. PLOS ONE: strong broad fallback for methodologically rigorous null/mixed findings.
4. F1000Research: good transparency-forward option if open peer review is desirable.
5. Brain Injury: conditional clinical audience option.
6. Scientific Reports: broad fallback, but likely less targeted than the neurotrauma venues.
7. Clinical Neurophysiology and NeuroImage: Clinical: stretch or poor first targets unless the methods contribution is strengthened.
8. Data in Brief: companion or derived-data article only, not the main interpretive manuscript.
"""


def blueprint_report() -> str:
    rows = figure_table_rows()
    table = "\n".join(
        f"| {r['item_id']} | {r['item_type']} | {r['title']} | {r['priority_level']} | {r['already_available_or_needs_generation']} |"
        for r in rows
    )
    details = "\n\n".join(
        f"### {r['item_id']}: {r['title']}\n"
        f"- Purpose: {r['purpose']}\n"
        f"- Source files: `{r['source_files']}`\n"
        f"- Required panels/columns: {r['required_panels_or_columns']}\n"
        f"- Claim supported: {r['claim_supported']}\n"
        f"- Caveats shown: {r['caveats_shown']}\n"
        f"- Availability: {r['already_available_or_needs_generation']}\n"
        f"- Priority: {r['priority_level']}"
        for r in rows
    )
    return f"""
# Claims Figures Tables Manuscript Blueprint

Generated: {now()}

## Technical Summary

The manuscript should be built around a small, defensive figure/table set that makes the negative and mixed findings impossible to miss. The highest-priority visuals are the D1 attenuation figure, the D2 falsification figure, and a key-results table. These should be generated from existing outputs only before full manuscript drafting.

## Proposed Figure And Table Set

| item | type | title | priority | status |
| --- | --- | --- | --- | --- |
{table}

## Figure And Table Details

{details}

## Claims-To-Display Map

| claim | primary display |
| --- | --- |
| D1 attenuated and did not survive broad FDR | Figure 2; Table 3 |
| Strict artifact branch is not interpretable for group inference | Figure 3; Table 5 |
| D3 does not rescue signal | Figure 4; Table 3 |
| D2 is partial/inconsistent | Figure 5; Table 3 |
| ds003490 is comparator only | Figure 1; Table 1 |
| No marker-validation claim is supported | Figure 6; Table 4 |

## Caption Guardrails

Captions should use the allowlist wording and should not introduce claims absent from `outputs/final/manuscript_claim_allowlist.csv`. Captions should explicitly say "exploratory" for the D1 narrow prior-anchor and DPX cue-baseline trace, and should label D2 as overlapping-subject cross-task evidence rather than independent validation.

## Recommended Pre-Drafting Figure Pass

Before writing the manuscript, generate the figure/table assets and a caption-to-claim traceability table. That pass should not run new analyses; it should only format and visualize existing outputs.
"""


def main() -> None:
    gate = require_gate()
    require_sources()
    values = read_values()

    write_csv(
        FINAL / "journal_target_matrix.csv",
        journal_rows(),
        [
            "journal",
            "article_type",
            "fit_rating",
            "likely_reviewer_reaction",
            "strengths",
            "risks",
            "required_framing",
            "recommendation",
        ],
    )
    write_csv(
        FINAL / "manuscript_claim_allowlist.csv",
        allowlist_rows(),
        [
            "claim_id",
            "claim_text",
            "why_allowed_or_blocked",
            "source_evidence",
            "caveat",
            "acceptable_wording",
            "unacceptable_wording",
        ],
    )
    write_csv(
        FINAL / "manuscript_claim_blocklist.csv",
        blocklist_rows(),
        [
            "claim_id",
            "claim_text",
            "why_allowed_or_blocked",
            "source_evidence",
            "caveat",
            "acceptable_wording",
            "unacceptable_wording",
        ],
    )
    write_csv(
        FINAL / "proposed_figures_and_tables.csv",
        figure_table_rows(),
        [
            "item_id",
            "item_type",
            "title",
            "purpose",
            "source_files",
            "required_panels_or_columns",
            "claim_supported",
            "caveats_shown",
            "already_available_or_needs_generation",
            "priority_level",
        ],
    )

    write_text(REPORTS / "42_manuscript_viability_and_strategy_report.md", viability_report(values))
    write_text(REPORTS / "43_candidate_journal_and_article_type_assessment.md", journal_report())
    write_text(REPORTS / "44_claims_figures_tables_manuscript_blueprint.md", blueprint_report())

    print(
        json.dumps(
            {
                "status": "complete",
                "gate": gate.get("gate"),
                "reports": 3,
                "csvs": 4,
                "recommendation": "conditional_go_after_figure_qc_pass",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
