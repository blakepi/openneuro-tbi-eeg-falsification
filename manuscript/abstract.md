# Structured Abstract

## Background

Public EEG datasets make it possible to test whether candidate traumatic brain injury (TBI) signals remain interpretable when artifact sensitivity, task context, and reproducibility are handled explicitly.

## Objective

To evaluate whether a plausible resting EEG spectral/aperiodic candidate signal in public mild TBI data survived artifact-control, lower-artifact eyes-closed alpha/individual-alpha-frequency sensitivity testing, and bounded cross-task falsification.

## Methods

This manuscript used the locked, audited D1/D2/D3 analysis package without rerunning extraction or models. D1 evaluated resting EEG features in OpenNeuro ds003522. D3 tested eyes-closed posterior alpha/IAF-adjacent features in ds003522. D2 evaluated bounded cross-task support using ds005114 and ds003523 while preserving subject-overlap constraints. ds003490 was used only as a comparator and pipeline rehearsal dataset.

## Results

All interpreted datasets had locally verified paired EEGLAB SET/FDT files. The acute mTBI versus control D1 broad artifact-controlled family did not survive FDR (minimum q=0.7876). A narrow prior-anchor family was exploratory only (q=0.1320). D3 did not rescue the signal (posterior acute minimum q=0.9149). D2 showed only a weak DPX cue-baseline trace (minimum q=0.0898, maximum absolute Hedges g=0.5277), while DPX task-average, visual working memory task-average, and integrated task models did not converge.

## Conclusions

The audited public-data package supports a cautious null-leaning interpretation. The strongest contribution is not a positive clinical signal, but a reproducibility-oriented demonstration that artifact handling, lower-artifact sensitivity checks, and task-context stress testing materially constrain TBI EEG claims.

## Keywords

mild traumatic brain injury; EEG; OpenNeuro; artifact sensitivity; reproducibility; falsification; aperiodic EEG; alpha rhythm
