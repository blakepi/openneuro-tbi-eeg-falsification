# Structured Abstract

## Background

Public EEG datasets can test whether proposed traumatic brain injury (TBI) EEG findings remain interpretable when artifact sensitivity, task context, and reproducibility constraints are made explicit.

## Objective

To evaluate whether an initially plausible resting EEG spectral/aperiodic pattern in public mild TBI data remained supported after artifact-control, lower-artifact eyes-closed alpha/individual-alpha-frequency sensitivity testing, and bounded cross-task falsification.

## Methods

This manuscript used the locked, audited D1/D2/D3 analysis package without rerunning extraction or models. D1 evaluated resting EEG features in OpenNeuro ds003522. D3 tested eyes-closed posterior alpha/IAF-adjacent features in ds003522. D2 evaluated bounded cross-task support using ds005114 and ds003523 while preserving subject-overlap constraints. ds003490 was used only as a comparator and pipeline rehearsal dataset.

## Results

All interpreted datasets had locally verified paired EEGLAB SET/FDT files. The acute mTBI versus control D1 broad artifact-controlled family did not survive FDR (minimum q=0.7876). A narrow prior-anchor family remained exploratory (q=0.1320). D3 did not rescue the signal (posterior acute minimum q=0.9149). D2 showed only a weak DPX cue-baseline trace (minimum q=0.0898, maximum absolute Hedges g=0.5277), while DPX task-average, visual working memory task-average, and integrated task models did not converge.

## Conclusions

The audited public-data package supports a cautious null-leaning interpretation. Its contribution is a reproducibility-oriented stress test showing how artifact handling, lower-artifact rest sensitivity checks, and task-context analyses constrain TBI EEG claims before clinical or biomarker interpretations are considered.

## Keywords

mild traumatic brain injury; EEG; OpenNeuro; artifact sensitivity; reproducibility; falsification; aperiodic EEG; alpha rhythm
