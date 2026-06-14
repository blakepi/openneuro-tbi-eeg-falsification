# Artifact-sensitive resting EEG candidate signals in public traumatic brain injury datasets: an OpenNeuro falsification analysis

## Abstract

See `abstract.md` for the structured abstract. In brief, this manuscript reports a public OpenNeuro EEG reanalysis in which an initially plausible resting EEG candidate signal in mild traumatic brain injury attenuated under artifact-control and was only partially supported by bounded cross-task testing.

## Introduction

Mild traumatic brain injury (mTBI) is common, clinically heterogeneous, and difficult to summarize with a single neurophysiological endpoint. EEG is attractive for public-data reanalysis because it is inexpensive relative to many imaging modalities, temporally precise, and available in multiple OpenNeuro datasets.<sup>1</sup> At the same time, scalp EEG is highly sensitive to artifact, task context, preprocessing decisions, and participant overlap across repeated recordings.<sup>13,14</sup> These properties make transparent falsification especially important before any candidate signal is treated as robust.

The present manuscript uses a completed, audited D1/D2/D3 analysis package to ask a deliberately conservative question: does a plausible resting EEG aperiodic/spectral candidate in public TBI data remain interpretable after artifact-control, a lower-artifact eyes-closed alpha/IAF sensitivity check, and bounded cross-task stress testing? The purpose is not to build a classifier or to claim clinical readiness. The purpose is to document what remains after a candidate signal is pushed through transparent, source-backed robustness checks.

The final package supports a cautious answer. The acute mTBI versus control resting signal does not survive broad artifact-controlled FDR. A narrower prior-anchor family remains exploratory. The eyes-closed alpha/IAF branch does not rescue the acute signal. D2 task datasets provide a weak DPX cue-baseline trace, but task-average DPX, visual working memory, and integrated task models do not support robust convergence. Chronic TBI is handled as a separate batch-sensitive context, and ds003490 is used only as a comparator and pipeline rehearsal dataset.

This framing is aligned with Neurotrauma Reports as a transparent null-leaning reproducibility and falsification report. The manuscript emphasizes public-data traceability, artifact sensitivity, and conservative interpretation rather than a positive translational narrative.

## Methods

### Study Design and Scope

This was a retrospective public-data EEG reanalysis using only completed, audited outputs from the final D1/D2/D3 package. No new downloads, extraction, model fitting, raw-data movement, or machine-readable result edits were performed during manuscript drafting. The analysis was designed as a stress test of an initially plausible resting EEG candidate signal in TBI.

D1 evaluated resting EEG aperiodic and spectral families in ds003522 under artifact-control branches.<sup>2,6</sup> D3 evaluated a lower-artifact eyes-closed alpha/IAF branch within ds003522.<sup>2</sup> D2 evaluated bounded cross-task support using ds005114 and ds003523.<sup>3,4,7</sup> ds003490 was used only for comparator and pipeline-readiness rehearsal.<sup>5,8</sup> The audit gate and manuscript-readiness gate were required to pass before this draft was generated.

### Datasets and Participants

The verified dataset roles are summarized in Table 1 and Figure 1. ds003522 supplied the D1/D3 TBI analyses and had 200 paired EEGLAB SET/FDT files locally verified.<sup>2</sup> ds005114 supplied the DPX task component of D2 and had 223 paired SET/FDT files verified.<sup>3</sup> ds003523 supplied the visual working memory component of D2 and had 221 paired SET/FDT files verified.<sup>4</sup> ds003490 had 75 paired SET/FDT files verified and was used only as a comparator and pipeline rehearsal dataset.<sup>5</sup>

In the D1/D3 group models, acute mTBI versus control was treated as the cleanest primary comparison. The model reports show subject-level acute comparisons with 26 controls and 44 mTBI observations for the main ds003522 branch. Chronic TBI was kept separate because the chronic branch is secondary and batch-sensitive. In D2, task-average models used Original_ID to avoid treating repeated task records from the same person as independent people.

### Identity Harmonization and Overlap Handling

D2 was interpreted within an overlapping-subject framework. The ds005114 and ds003523 task datasets overlap by Original_ID, so they were not treated as independent cohorts. Direction consistency and within-subject stability across D2 tasks were interpreted as feature-stability context rather than separate cohort evidence. This distinction is central to the manuscript's claim boundary.

### EEG Preprocessing and Feature Extraction

The analysis used locally verified EEGLAB SET/FDT files readable with MNE.<sup>10</sup> The final feature families included aperiodic features,<sup>11</sup> band-power summaries, spectral-balance ratios, entropy-like features, and alpha/IAF-adjacent features where available. The manuscript does not introduce new preprocessing or feature extraction; it describes the locked outputs already generated by the analysis scripts and audited final package.

### D1 Artifact-Control Analysis

D1 tested acute mTBI versus control in ds003522 across resting EEG eyes-open and eyes-closed conditions. The broad D1 FDR family combined eyes-open and eyes-closed conditions, six regions, and 17 features within each comparison and artifact branch. Artifact branches included all epochs, ptp95 within-recording trimming, and a strict 250 microvolt branch.

The ptp95 branch removed the highest-amplitude 5% of epochs within recording-condition while preserving recording-condition coverage. The strict 250 microvolt branch retained too few recording-condition rows for meaningful group modeling and was treated as an artifact-control limitation rather than a substantive group result. The narrow prior-anchor family was reported only as an exploratory transparency calculation, not as a rescued endpoint.

### D3 Eyes-Closed Alpha/IAF Analysis

D3 tested whether lower-artifact eyes-closed posterior alpha/IAF features would support the acute signal. This branch was especially relevant because the original D1 candidate was strongest in eyes-open frontal, temporal, and global features where non-neural artifact sensitivity was a concern. The generated D3 table did not include a separate aperiodic-adjusted alpha peak endpoint, so alpha interpretation remains limited.

### D2 Bounded Cross-Task Falsification Analysis

D2 tested whether harmonized spectral/aperiodic structure generalized across task contexts. ds005114 provided DPX cue-baseline and task-average windows; ds003523 provided visual working memory task-average windows. D2 results were interpreted as bounded cross-task falsification evidence within overlapping Original_IDs, not as a separate cohort study.

### ds003490 Comparator/Pipeline Rehearsal

ds003490 was retained as a comparator and pipeline rehearsal dataset only. It verified that the pipeline could retrieve paired EEGLAB files, read MNE-compatible recordings, parse event/rest structure, and generate readiness outputs. It is not a TBI dataset and is not evidence for a TBI claim.<sup>5,8</sup>

### Statistical Analysis

The final package reported Hedges g for group differences, Welch tests for local signal inspection, permutation p-values where available, bootstrap confidence intervals, leave-one-out effect ranges, artifact-sensitivity summaries, and Benjamini-Hochberg FDR q-values.<sup>12</sup> Mixed task models were attempted for D2; 27 MixedLM models completed and 21 used clustered OLS fallback because part of the model family was numerically fragile.

### Multiple-Comparison Handling

The manuscript gives interpretive priority to broad FDR families. D1 artifact-controlled acute mTBI versus control was evaluated across 204 tests in the broad family. D3 eyes-closed alpha/IAF was evaluated across 36 tests in the acute family. Narrower prior-anchor calculations are presented as transparency analyses only. D2 cue-baseline findings are described as weak and context-specific because task-average and integrated task checks did not converge.

### Reproducibility and Audit Procedures

Raw data verification, stale-report repair, final package integrity checks, manuscript-readiness QC, figure/table source data, and claim traceability were completed before drafting. Data retrieval and provenance used OpenNeuro and DataLad where applicable.<sup>1,9</sup> The audit gate reported PASS with no critical failures. The manuscript-readiness gate reported PASS, with all critical rows true. The draft package preserves the final source file paths and includes a claim traceability audit.

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

The manuscript should be situated within three literatures: EEG studies of mTBI, aperiodic/spectral parameterization methods, and artifact-aware EEG interpretation.<sup>6,7,11,13,14</sup> The present contribution is methodological and transparency-oriented: it shows how a plausible public-data EEG candidate weakens when artifact handling, lower-artifact sensitivity testing, and task-context stress testing are made explicit.

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

The analysis used public OpenNeuro datasets ds003522, ds005114, ds003523, and ds003490.<sup>1-5</sup> ds003490 was used only as a comparator and pipeline rehearsal dataset. Derived manuscript artifacts, source-data manifests, figure/table manifests, and reproduction materials are listed in the local final package. A sanitized public repository for code and selected derived manuscript artifacts is listed at: https://github.com/blakepi/openneuro-tbi-eeg-falsification.

## Code Availability

Code and selected derived manuscript artifacts are available or being prepared at: https://github.com/blakepi/openneuro-tbi-eeg-falsification. The public repository excludes raw EEG files and local administrative logs. The local reproduction guide documents script order, raw-data verification outputs, and audit gates.

## Ethics / Public Data Statement

This study used publicly available, deidentified OpenNeuro data and did not constitute human-subjects research for the present analysis.

## Author Contributions

Gregory Pierpoint: Conceptualization; Methodology; Software; Formal analysis; Investigation; Data curation; Writing - original draft; Writing - review and editing; Visualization; Project administration.

## Conflicts of Interest

The author declares no competing interests.

## Funding

No external funding.

## Acknowledgments

The author acknowledges the original OpenNeuro dataset contributors and the OpenNeuro/DataLad infrastructure that enabled transparent public-data reanalysis. Dataset-specific acknowledgments and citation wording should be verified against the original dataset records before submission.

## References

1. Markiewicz CJ, Gorgolewski KJ, Feingold F, Blair R, Halchenko YO, Miller E, et al. The OpenNeuro resource for sharing of neuroscience data. eLife. 2021;10:e71774. doi:10.7554/eLife.71774.
2. Cavanagh JF, Quinn D. EEG: Three-Stim Auditory Oddball and Rest in Acute and Chronic TBI [dataset]. OpenNeuro; version 1.1.0. doi:10.18112/openneuro.ds003522.v1.1.0.
3. Cavanagh JF. EEG: DPX Cog Ctl Task in Acute Mild TBI [dataset]. OpenNeuro; version 1.0.0. doi:10.18112/openneuro.ds005114.v1.0.0.
4. Cavanagh JF. EEG: Visual Working Memory in Acute TBI [dataset]. OpenNeuro; version 1.1.0. doi:10.18112/openneuro.ds003523.v1.1.0.
5. Cavanagh JF. EEG: 3-Stim Auditory Oddball and Rest in Parkinson's [dataset]. OpenNeuro; version 1.1.0. doi:10.18112/openneuro.ds003490.v1.1.0.
6. Cavanagh JF, Wilson JK, Rieger RE, Gill D, Broadway JM, Story Remer JH, et al. ERPs predict symptomatic distress and recovery in sub-acute mild traumatic brain injury. Neuropsychologia. 2019;132:107125. doi:10.1016/j.neuropsychologia.2019.107125.
7. Cavanagh JF, Rieger RE, Wilson JK, Gill D, Fullerton L, Brandt E, et al. Joint analysis of frontal theta synchrony and white matter following mild traumatic brain injury. Brain Imaging Behav. 2020;14(6):2210-2223. doi:10.1007/s11682-019-00171-y.
8. Cavanagh JF, Kumar P, Mueller AA, Richardson SP, Mueen A. Diminished EEG habituation to novel events effectively classifies Parkinson's patients. Clin Neurophysiol. 2018;129(2):409-418. doi:10.1016/j.clinph.2017.11.023.
9. Halchenko YO, Meyer K, Poldrack B, Solanky DS, Wagner AS, Gors J, et al. DataLad: distributed system for joint management of code, data, and their relationship. J Open Source Softw. 2021;6(63):3262. doi:10.21105/joss.03262.
10. Gramfort A, Luessi M, Larson E, Engemann DA, Strohmeier D, Brodbeck C, et al. MNE software for processing MEG and EEG data. Neuroimage. 2014;86:446-460. doi:10.1016/j.neuroimage.2013.10.027.
11. Donoghue T, Haller M, Peterson EJ, Varma P, Sebastian P, Gao R, et al. Parameterizing neural power spectra into periodic and aperiodic components. Nat Neurosci. 2020;23(12):1655-1665. doi:10.1038/s41593-020-00744-x.
12. Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. J R Stat Soc Series B Stat Methodol. 1995;57(1):289-300. doi:10.1111/j.2517-6161.1995.tb02031.x.
13. Whitham EM, Pope KJ, Fitzgibbon SP, Lewis T, Clark CR, Loveless S, et al. Scalp electrical recording during paralysis: quantitative evidence that EEG frequencies above 20 Hz are contaminated by EMG. Clin Neurophysiol. 2007;118(8):1877-1888. doi:10.1016/j.clinph.2007.04.027.
14. Goncharova II, McFarland DJ, Vaughan TM, Wolpaw JR. EMG contamination of EEG: spectral and topographical characteristics. Clin Neurophysiol. 2003;114(9):1580-1593. doi:10.1016/S1388-2457(03)00093-2.

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
