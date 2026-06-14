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

    | claim_id | acceptable_wording | caveat | source_evidence |
| --- | --- | --- | --- |
| A01 | did not support a robust acute mTBI resting EEG marker | Use marker only as a negated claim; do not imply clinical validation was achieved. | reports/28_d1_d3_post_analysis_audit.md; outputs/qc/final_result_consistency_checks.csv |
| A02 | attenuated under artifact-control and cross-task testing | Original exact row-level model outputs were not locally available. | reports/28_d1_d3_post_analysis_audit.md; reports/35_d2_bounded_falsification_report.md |
| A03 | did not survive broad artifact-controlled FDR | Narrow prior-anchor result is exploratory and not confirmatory. | outputs/qc/final_result_consistency_checks.csv; reports/36_integrated_d1_d2_d3_final_decision_report.md |
| A04 | did not rescue or support the acute signal | Generated D3 table lacks aperiodic-adjusted alpha peak metrics. | reports/28_d1_d3_post_analysis_audit.md; outputs/final/key_result_claims_traceability.csv |
| A05 | partial/inconsistent bounded cross-task support | D2 overlaps by Original_ID and is not an independent cohort. | reports/35_d2_bounded_falsification_report.md; outputs/d2_cross_task/d2_falsification_summary.csv |
| A06 | weak exploratory DPX cue-baseline trace | Cue-baseline q<0.10 is exploratory and context-specific. | reports/35_d2_bounded_falsification_report.md; outputs/qc/final_result_consistency_checks.csv |
| A07 | exploratory and batch-sensitive chronic branch | Do not use chronic results to prove acute mTBI effects. | reports/28_d1_d3_post_analysis_audit.md; outputs/final/d1_d2_d3_evidence_matrix.csv |
| A08 | motivate preregistered artifact-controlled confirmatory work | The current manuscript should not imply the confirmatory study has already been done. | reports/40_final_scientific_synthesis_and_publishability_report.md |

    ## Blocked Claims

    | claim_id | claim_text | acceptable_wording | unacceptable_wording | caveat |
| --- | --- | --- | --- | --- |
| B01 | validated biomarker | no marker-validation claim is supported | validated biomarker | Future prospective validation could change this, but current outputs cannot. |
| B02 | diagnostic biomarker | candidate signal did not support diagnostic use | diagnostic biomarker | The package is not a diagnostic accuracy study. |
| B03 | predictive biomarker | not evaluated as a predictive endpoint | predictive biomarker | No symptom or outcome prediction endpoint is supported. |
| B04 | confirmed EEG signature | initially promising EEG candidate attenuated | confirmed EEG signature | A weak/context-specific trace is not confirmation. |
| B05 | independently replicated signal | bounded cross-task check with overlapping identities | independently replicated signal | Within-subject stability is not independent replication. |
| B06 | D2 validation | D2 bounded falsification/reproducibility check | D2 validation | DPX cue-baseline is a weak exploratory trace only. |
| B07 | chronic TBI proof | chronic branch remains exploratory and batch-sensitive | chronic TBI proof | Chronic and acute must remain separate. |
| B08 | ds003490 TBI validation | ds003490 comparator/pipeline rehearsal | ds003490 TBI validation | It may support methods readiness only. |
| B09 | symptom prediction | future studies should collect symptom covariates | predicts symptoms | No supported symptom endpoint belongs in the main claim set. |
| B10 | clinical deployment | not ready for clinical use | ready for clinical deployment | Clinical deployment requires prospective validation, thresholds, and utility evidence. |
| B11 | black-box classifier rescue | no classifier rescue was attempted | classification rescues the signal | A new preregistered predictive design would be a different study. |

    ## Language Substitutions

    - Use "artifact-sensitive/null-leaning" instead of "robust positive signal."
    - Use "weak/context-specific DPX cue-baseline trace" instead of "confirmed cross-task effect."
    - Use "bounded cross-task stress test" instead of "D2 validation."
    - Use "comparator/pipeline rehearsal" instead of "ds003490 TBI validation."
    - Use "future preregistered follow-up is needed" instead of "ready for clinical deployment."


## Metadata and Reference Update Guardrail

Author metadata, affiliation wording, funding, competing interests, ethics/public-data wording, and provisional references were inserted on 2026-06-14T12:55:45-04:00. The affiliation spelling uses the ODU public spelling "Macon & Joan Brock Virginia Health Sciences." Dataset citations for OpenNeuro accessions remain flagged for final human verification of preferred dataset citation style and release dates.

The manuscript must continue to avoid claims of validated biomarker, diagnostic biomarker, clinical deployment, independent validation, confirmed replication, proven EEG signature, or robust positive marker. The public repository URL may be cited only after the GitHub repository exists.

## Editorial Revision v2 Guardrail

The v2 revision improved flow and public-repository integration without changing scientific conclusions. The manuscript remains a public-data, artifact-sensitive, null-leaning reproducibility/falsification report. It should not be reframed as a positive marker paper. The GitHub repository is public at https://github.com/blakepi/openneuro-tbi-eeg-falsification; Zenodo DOI wording must wait until an actual archived release DOI exists.
