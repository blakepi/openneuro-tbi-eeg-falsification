from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import markdown_table, project_path, read_rows_csv, script_finish, script_start, write_text
from scripts.utils.reporting_utils import csv_summary, file_status, write_report


SCRIPT = "16_write_reports.py"


def main() -> None:
    start = script_start(SCRIPT)
    outputs = []
    warnings = []

    report_specs = [
        ("04_d1_rest_aperiodic_report.md", "D1 Rest Aperiodic/Spectral Report", d1_report_sections()),
        ("05_d3_ec_alpha_iaf_report.md", "D3 Eyes-Closed Alpha/IAF Report", d3_report_sections()),
        ("06_d2_cross_task_convergence_report.md", "D2 Cross-Task Convergence Report", d2_report_sections()),
        ("09_limitations_and_risk_assessment.md", "Limitations and Risk Assessment", limitations_sections()),
        ("10_final_analysis_report.md", "Final Analysis Report", final_report_sections()),
        ("analysis_reproduction_instructions.md", "Analysis Reproduction Instructions", reproduction_sections()),
    ]
    for filename, title, sections in report_specs:
        path = project_path("reports", filename)
        write_report(path, title, sections)
        outputs.append(str(path))

    script_finish(SCRIPT, start, outputs=outputs, warnings=warnings)


def d1_report_sections() -> list[tuple[str, str]]:
    feature_path = project_path("outputs/features/d1_rest_features.csv")
    model_path = project_path("outputs/models/d1_d3_group_models.csv")
    rows = [row for row in read_rows_csv(model_path) if row.get("analysis_family") == "d1_rest_aperiodic_spectral"]
    return [
        ("Question", "Does resting EEG in TBI show an artifact-controlled aperiodic/spectral alteration?"),
        ("Feature Status", csv_summary(feature_path)),
        ("Primary Group Results", markdown_table(rows, max_rows=25) if rows else "No D1 group model rows are available yet."),
        ("Artifact Interpretation", "Eyes-open slope/entropy findings must be treated as artifact-sensitive until EMG metrics, high-EMG exclusions, temporal/frontal exclusions, and eyes-closed sensitivity branches are complete."),
        ("Verdict", verdict_from_rows(rows)),
    ]


def d3_report_sections() -> list[tuple[str, str]]:
    feature_path = project_path("outputs/features/d3_ec_alpha_iaf_features.csv")
    model_path = project_path("outputs/models/d1_d3_group_models.csv")
    rows = [row for row in read_rows_csv(model_path) if row.get("analysis_family") == "d3_ec_alpha_iaf"]
    return [
        ("Question", "Do eyes-closed alpha power or IAF provide less EMG-prone convergence with the D1 resting signature?"),
        ("Feature Status", csv_summary(feature_path)),
        ("Group Results", markdown_table(rows, max_rows=25) if rows else "No D3 group model rows are available yet."),
        ("Verdict", verdict_from_rows(rows)),
    ]


def d2_report_sections() -> list[tuple[str, str]]:
    corr_path = project_path("outputs/models/d2_cross_task_correlations.csv")
    return [
        ("Question", "Are harmonized EEG features stable across tasks or paradigms within overlapping subjects?"),
        ("Cross-Task Results", csv_summary(corr_path)),
        ("Interpretation", "D2 can support convergence but not independent validation because the core TBI datasets may contain overlapping people."),
    ]


def limitations_sections() -> list[tuple[str, str]]:
    return [
        ("Key Risks", "\n".join([
            "- EMG/muscle artifact risk is central for eyes-open frontal/temporal slope and entropy effects.",
            "- Chronic TBI comparisons may be batch or recruitment confounded.",
            "- Stable person-level IDs are required to prevent leakage across ds003522/ds005114/ds003523.",
            "- Multiple comparisons are exploratory; FDR and robustness must be reported.",
            "- ds003490 is a methodological comparator, not TBI validation.",
            "- Missing covariates and clinical/behavioral tables limit adjusted and secondary models.",
        ])),
        ("Confirmatory Need", "Any promising signal requires external validation in an independent cohort with pre-registered preprocessing, artifact-control, and modeling choices."),
    ]


def final_report_sections() -> list[tuple[str, str]]:
    key_files = [
        project_path("outputs/metadata/dataset_inventory.csv"),
        project_path("outputs/metadata/subject_crosswalk.csv"),
        project_path("outputs/qc/eeg_file_manifest.csv"),
        project_path("outputs/features/d1_rest_features.csv"),
        project_path("outputs/features/d3_ec_alpha_iaf_features.csv"),
        project_path("outputs/models/d1_d3_group_models.csv"),
        project_path("outputs/models/d2_cross_task_correlations.csv"),
        project_path("outputs/robustness/top_signal_robustness_summary.csv"),
    ]
    inventory = read_rows_csv(project_path("outputs/metadata/dataset_inventory.csv"))
    robustness = read_rows_csv(project_path("outputs/robustness/top_signal_robustness_summary.csv"))
    completion = completion_status()
    return [
        ("Executive Summary", completion),
        ("What Was Analyzed", markdown_table(inventory, max_rows=25) if inventory else "Dataset inventory has not been populated."),
        ("Subject Identity and Overlap", csv_summary(project_path("outputs/metadata/subject_overlap_matrix.csv"))),
        ("EEG QC", csv_summary(project_path("outputs/qc/artifact_qc_metrics.csv"))),
        ("D1 Results", csv_summary(project_path("outputs/models/d1_d3_group_models.csv"))),
        ("D3 Results", csv_summary(project_path("outputs/features/d3_ec_alpha_iaf_features.csv"))),
        ("D2 Results", csv_summary(project_path("outputs/models/d2_cross_task_correlations.csv"))),
        ("Secondary Results", "Secondary clinical/cognitive models are reported in `reports/07_secondary_clinical_cognitive_report.md`."),
        ("Robustness Summary", markdown_table(robustness, max_rows=25) if robustness else "Robustness tables are empty until model rows exist."),
        ("Publishability Assessment", publishability_assessment(robustness)),
        ("What Not To Claim", "Do not claim validation, diagnostic utility, prediction, recovery prognosis, or causal interpretation from these exploratory public-data analyses."),
        ("File Manifest", file_status(key_files)),
    ]


def reproduction_sections() -> list[tuple[str, str]]:
    commands = """```powershell
cd "<LOCAL_PROJECT_ROOT>"
uv venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe scripts\\00_setup_project.py
.\\.venv\\Scripts\\python.exe scripts\\01_download_metadata.py
.\\.venv\\Scripts\\python.exe scripts\\02_inventory_datasets.py
.\\.venv\\Scripts\\python.exe scripts\\03_build_subject_crosswalk.py
.\\.venv\\Scripts\\python.exe scripts\\04_eeg_manifest_and_qc_dryrun.py
.\\.venv\\Scripts\\python.exe scripts\\05_download_priority_eeg.py --dataset ds003522 --execute
.\\.venv\\Scripts\\python.exe scripts\\06_extract_rest_segments.py --dataset ds003522
.\\.venv\\Scripts\\python.exe scripts\\07_preprocess_and_artifact_qc.py --dataset ds003522
.\\.venv\\Scripts\\python.exe scripts\\08_extract_d1_rest_aperiodic_features.py --dataset ds003522
.\\.venv\\Scripts\\python.exe scripts\\09_extract_d3_ec_alpha_iaf_features.py --dataset ds003522
.\\.venv\\Scripts\\python.exe scripts\\11_statistical_models_d1_d3.py --dataset ds003522
.\\.venv\\Scripts\\python.exe scripts\\14_robustness_sensitivity.py --scope d1_d3
.\\.venv\\Scripts\\python.exe scripts\\10_extract_d2_harmonized_cross_task_features.py --dataset ds003490
.\\.venv\\Scripts\\python.exe scripts\\10_extract_d2_harmonized_cross_task_features.py --dataset ds005114
.\\.venv\\Scripts\\python.exe scripts\\10_extract_d2_harmonized_cross_task_features.py --dataset ds003523
.\\.venv\\Scripts\\python.exe scripts\\12_statistical_models_d2.py
.\\.venv\\Scripts\\python.exe scripts\\13_secondary_clinical_cognitive_models.py
.\\.venv\\Scripts\\python.exe scripts\\14_robustness_sensitivity.py --scope all
.\\.venv\\Scripts\\python.exe scripts\\15_make_figures.py
.\\.venv\\Scripts\\python.exe scripts\\16_write_reports.py
```"""
    return [
        ("Environment", "Use `uv` or Conda to install the packages in `requirements.txt` or `environment.yml`. The bundled Codex Python may not include the full EEG stack."),
        ("Command Order", commands),
        ("Raw Data Placement", "If OpenNeuro CLI download is unavailable, place datasets under `data/raw/<dataset_id>/` with their BIDS directory structure intact, then rerun scripts 02 onward."),
    ]


def verdict_from_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "Not yet assessable: no completed model rows."
    q_values = []
    for row in rows:
        try:
            q_values.append(float(row.get("fdr_q", "nan")))
        except Exception:
            pass
    if any(q < 0.05 for q in q_values):
        return "Potential candidate signal, pending artifact-control and robustness confirmation."
    if any(q < 0.10 for q in q_values):
        return "Suggestive exploratory signal, pending artifact-control and robustness confirmation."
    return "Weak or not yet robust based on available model rows."


def completion_status() -> str:
    feature_rows = read_rows_csv(project_path("outputs/features/d1_rest_features.csv"))
    if feature_rows:
        return "The analysis package has run through feature extraction/modeling outputs currently present on disk. Interpret all findings as exploratory and check missing sensitivity branches before manuscript decisions."
    return "The reproducible analysis package is scaffolded and early metadata/QC scripts can run, but the full EEG analysis is not complete until dependencies and raw OpenNeuro data are available and all numbered scripts run successfully."


def publishability_assessment(robustness_rows: list[dict[str, str]]) -> str:
    if not robustness_rows:
        return "\n".join([
            "scientific_strength: not_yet_assessable",
            "artifact_control_strength: not_yet_assessable",
            "novelty: moderate",
            "clinical_relevance: not_yet_assessable",
            "statistical_robustness: not_yet_assessable",
            "replication_or_convergence: not_yet_assessable",
            "publishability: not_yet_assessable",
            "recommended_next_step: install dependencies, download raw EEG, and complete D1/D3 before assessing publishability.",
        ])
    return "\n".join([
        "scientific_strength: exploratory",
        "artifact_control_strength: pending_full_sensitivity",
        "novelty: moderate",
        "clinical_relevance: exploratory",
        "statistical_robustness: see robustness table",
        "replication_or_convergence: see D2 report",
        "publishability: depends_on_artifact_control",
        "recommended_next_step: prioritize EMG and eyes-closed sensitivity before manuscript framing.",
    ])


if __name__ == "__main__":
    main()
