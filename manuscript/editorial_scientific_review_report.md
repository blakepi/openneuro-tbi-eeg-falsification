# Editorial and Scientific Review Report

## Readiness Classification

needs minor editorial revision

## Summary Judgment

The draft is manuscript-ready in concept and source discipline, but it should receive minor editorial revision before DOCX conversion. The strongest version is a rigorous public-data falsification report, not a failed biomarker paper. Its contribution is useful because it explains why an initially plausible TBI EEG candidate signal weakened under artifact-aware and task-context stress tests.

## Scientific Honesty

The manuscript is appropriately conservative. It foregrounds the broad D1 artifact-controlled FDR failure, the non-rescuing D3 eyes-closed alpha/IAF branch, and the partial/inconsistent D2 result. The manuscript avoids clinical readiness claims and correctly keeps chronic TBI separate from acute mTBI.

## Null/Artifact-Sensitive Framing

The null-leaning framing is scientifically defensible. Artifact sensitivity is not treated as a nuisance footnote; it is the organizing logic of the paper. This should appeal to reviewers who value reproducibility and public-data transparency.

## Compelling Despite Negative or Partial Results

The paper is compelling if the introduction and discussion continue to emphasize falsification value. The draft should not apologize for negative findings. It should frame negative and partial results as information about endpoint fragility, artifact handling, and task generalization.

## Introduction and Motivation

The introduction motivates the design adequately, but it can be tightened before DOCX conversion. Recommended revision: state earlier that the analysis tests claim durability across three constraints: artifact control, lower-artifact rest sensitivity, and bounded task-context stress testing.

## Methods Reproducibility

Methods are reproducible at the manuscript level because raw verification, audit gates, figure/table source data, and claim traceability are all referenced. Before submission, the public repository should include the relevant scripts and selected derived outputs, while excluding raw EEG and local logs.

## Results Tone

The results are slightly defensive in places but generally appropriate. Keep the numerical results direct: D1 broad q=0.7876, D1 narrow q=0.1320, D3 q=0.9149, D2 cue-baseline q=0.0898, and integrated task models with 0 group reference-task terms below q<0.10.

## Discussion Contribution

The discussion makes a useful contribution by showing why artifact-aware public-data analyses can prevent overinterpretation. The future-directions section is strong because it turns a null-leaning result into design guidance for prospective work.

## Candidate Signal Language

The manuscript uses "candidate signal" often but not excessively. Keep "candidate" paired with "exploratory," "artifact-sensitive," or "not sufficient for clinical translation" when the phrase appears in interpretive sections.

## Likely Reviewer Concerns

- The original D1 signal was available only as a prose anchor, not exact per-feature rows.
- The ptp95 artifact branch is a sensitivity method, not definitive artifact correction.
- D3 did not include a separate aperiodic-adjusted alpha peak endpoint.
- D2 datasets overlap by Original_ID and are not independent cohorts.
- OpenNeuro dataset citation details and journal reference style require final verification.
- The public repository and archival DOI need completion before submission.

## Recommended Revisions Before DOCX Conversion

1. Verify all OpenNeuro dataset citations and release dates.
2. Tighten the Introduction to present the three stress tests more explicitly.
3. Keep the Results concise and numeric.
4. Add one final sentence to the Discussion distinguishing endpoint falsification from disease absence.
5. Confirm the target article type with Neurotrauma Reports.
6. Add a Zenodo DOI only after a real archive DOI is minted.
