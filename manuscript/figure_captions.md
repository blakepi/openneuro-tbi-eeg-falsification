# Figure Captions

**Figure 1. Dataset and workflow structure.** Public EEG datasets were assigned locked roles before manuscript-facing visualization. ds003522 supplied the D1/D3 TBI analyses, ds005114 and ds003523 supplied the bounded D2 cross-task check, and ds003490 remained a comparator and pipeline rehearsal dataset only. Counts show verified paired EEGLAB SET/FDT files.

**Figure 2. D1 artifact-control attenuation.** The historical prompt-level D1 anchor is shown only as a prose-derived reference because exact local per-feature rows were unavailable. Existing audit outputs show that acute mTBI versus control does not survive broad artifact-controlled FDR after ptp95 trimming, while the narrow prior-anchor family remains exploratory.

**Figure 3. Artifact-branch sample retention.** The all-epochs branch preserves all recording-condition rows, ptp95 trimming preserves coverage while trimming epochs within recordings, and the strict 250 uV branch leaves too few rows for group inference. This supports interpreting ptp95 as a sensitivity branch rather than definitive artifact correction.

**Figure 4. D3 eyes-closed alpha/IAF endpoint.** The lower-artifact eyes-closed alpha/IAF branch does not rescue the acute D1 signal. Posterior acute rows remain non-supportive after FDR, and generated D3 tables do not include a separate aperiodic-adjusted alpha peak endpoint.

**Figure 5. D2 bounded cross-task check.** The DPX cue-baseline window shows a weak q<0.10 trace, but DPX task-average, visual working memory task-average, and integrated task models do not support robust convergence. Direction consistency is descriptive because D2 task datasets overlap by Original_ID.

**Figure 6. Final evidence matrix.** The integrated evidence favors a cautious null-leaning reproducibility and falsification frame. D1/D3 broad artifact-controlled results are non-supportive, chronic TBI remains separate and batch-sensitive, D2 is partial and context-specific, and ds003490 is comparator-only.
