# Reproduction And Handoff Guide

Generated: 2026-06-13T19:20:47-04:00

## Project Directory

`<LOCAL_PROJECT_ROOT>`

## Environment Setup

Use the project virtual environment:

```powershell
cd "<LOCAL_PROJECT_ROOT>"
.\.venv\Scripts\python.exe --version
```

The package also used DataLad/git-annex for OpenNeuro retrieval and Deno/OpenNeuro CLI as supporting tooling. Deno/OpenNeuro CLI helped with authentication and metadata/tooling checks, but DataLad/git-annex was required for successful raw EEG retrieval.

## Required Tools

- Python virtual environment: `.\.venv\Scripts\python.exe`
- DataLad: `.\.venv\Scripts\datalad.exe`
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
.\.venv\Scripts\python.exe scripts\13_verify_ds003522_after_download.py
.\.venv\Scripts\python.exe scripts\14_d1_artifact_control_analysis.py
.\.venv\Scripts\python.exe scripts\15_d3_eyes_closed_alpha_iaf_analysis.py
.\.venv\Scripts\python.exe scripts\16_d1_d3_integrated_report.py
.\.venv\Scripts\python.exe scripts\19_d1_d3_post_analysis_audit.py
.\.venv\Scripts\python.exe scripts\20_verify_d2_downloads.py
.\.venv\Scripts\python.exe scripts\21_extract_d2_harmonized_features.py
.\.venv\Scripts\python.exe scripts\22_run_d2_falsification_models.py
.\.venv\Scripts\python.exe scripts\23_generate_d2_report.py
.\.venv\Scripts\python.exe scripts\24_stale_parallel_job_accuracy_audit.py
.\.venv\Scripts\python.exe scripts\26_final_analysis_package_consolidation.py
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
.\.venv\Scripts\python.exe scripts\24_stale_parallel_job_accuracy_audit.py
```

Continue only if `outputs/qc/audit_gate.json` reports `PASS`, `outputs/qc/AUDIT_PASS.ok` exists, and `outputs/qc/AUDIT_FAIL.ok` is absent.

## Rerun Final Consolidation

```powershell
.\.venv\Scripts\python.exe scripts\26_final_analysis_package_consolidation.py
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
