# D2 Bounded Falsification Report

Generated: 2026-06-13

## Technical Summary

D2 completed as a bounded cross-task falsification/reproducibility check using verified local raw EEG for `ds005114` and `ds003523`. Because the task datasets overlap by `Original_ID`, D2 is not independent confirmation.

The restored result is **partial/inconsistent cross-task support**. The strongest D2 trace is `ds005114` DPX cue-baseline alpha/spectral-balance structure with minimum FDR q = 0.0898 and maximum absolute Hedges g = 0.5277. However, DPX task-average does not clear FDR (minimum q = 0.1524), visual working memory task-average does not clear FDR (minimum q = 0.4720), and mixed models have 0 group reference-task terms below q < 0.10.

## Bounded Model Summary

| summary_level | dataset_id | n_group_effect_rows | min_fdr_q | max_abs_g | direction_match_rate | n_stability_q_lt_0p10 | n_mixed_group_q_lt_0p10 | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dataset_task_average | ds005114 | 48 | 0.1524 | 0.4955 | 0.7708 |  |  | directional but non-FDR-supportive |
| dataset_task_average | ds003523 | 48 | 0.4720 | 0.3669 | 0.6458 |  |  | directional but non-FDR-supportive |
| overall_d2 | ds005114+ds003523 | 576 | 0.0898 | 0.5277 |  | 76 | 0 | partial/inconsistent cross-task support |

## Best Within-Dataset Effects

| dataset_id | task_window | region | feature_name | n | hedges_g | welch_p | fdr_q | permutation_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds005114 | cue_locked_baseline_2s | central | alpha_theta_ratio | 90 | 0.4843 | 0.0182 | 0.0898 | 0.0255 |
| ds005114 | cue_locked_baseline_2s | central | relative_alpha_power | 90 | 0.4907 | 0.0172 | 0.0898 | 0.0225 |
| ds005114 | cue_locked_baseline_2s | central | relative_delta_power | 90 | -0.4717 | 0.0275 | 0.0898 | 0.0270 |
| ds005114 | cue_locked_baseline_2s | global | alpha_theta_ratio | 90 | 0.4701 | 0.0225 | 0.0898 | 0.0295 |
| ds005114 | cue_locked_baseline_2s | global | relative_alpha_power | 90 | 0.4855 | 0.0200 | 0.0898 | 0.0265 |
| ds005114 | cue_locked_baseline_2s | global | relative_delta_power | 90 | -0.4920 | 0.0225 | 0.0898 | 0.0205 |
| ds005114 | cue_locked_baseline_2s | occipital | alpha_theta_ratio | 90 | 0.5183 | 0.0113 | 0.0898 | 0.0210 |
| ds005114 | cue_locked_baseline_2s | occipital | relative_alpha_power | 90 | 0.5277 | 0.0110 | 0.0898 | 0.0160 |
| ds005114 | cue_locked_baseline_2s | occipital | relative_delta_power | 90 | -0.5136 | 0.0173 | 0.0898 | 0.0155 |
| ds005114 | cue_locked_baseline_2s | occipital | spectral_entropy_1_45 | 90 | 0.4968 | 0.0266 | 0.0898 | 0.0180 |
| ds005114 | cue_locked_baseline_2s | parietal | alpha_theta_ratio | 90 | 0.5048 | 0.0142 | 0.0898 | 0.0220 |
| ds005114 | cue_locked_baseline_2s | parietal | relative_alpha_power | 90 | 0.4934 | 0.0170 | 0.0898 | 0.0235 |

## Task-Average Results

| dataset_id | task_window | region | feature_name | n | hedges_g | welch_p | fdr_q | permutation_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds005114 | task_average_4s | central | alpha_theta_ratio | 90 | 0.4096 | 0.0443 | 0.1524 | 0.0595 |
| ds005114 | task_average_4s | central | relative_alpha_power | 90 | 0.4438 | 0.0306 | 0.1524 | 0.0405 |
| ds005114 | task_average_4s | central | relative_delta_power | 90 | -0.4121 | 0.0581 | 0.1524 | 0.0560 |
| ds005114 | task_average_4s | central | theta_alpha_ratio | 90 | -0.4532 | 0.0401 | 0.1524 | 0.0335 |
| ds005114 | task_average_4s | global | alpha_theta_ratio | 90 | 0.3903 | 0.0603 | 0.1524 | 0.0705 |
| ds005114 | task_average_4s | global | relative_alpha_power | 90 | 0.4382 | 0.0370 | 0.1524 | 0.0410 |
| ds005114 | task_average_4s | global | relative_delta_power | 90 | -0.4277 | 0.0511 | 0.1524 | 0.0490 |
| ds005114 | task_average_4s | global | theta_alpha_ratio | 90 | -0.4249 | 0.0540 | 0.1524 | 0.0490 |
| ds005114 | task_average_4s | occipital | alpha_theta_ratio | 90 | 0.4086 | 0.0389 | 0.1524 | 0.0575 |
| ds005114 | task_average_4s | occipital | relative_alpha_power | 90 | 0.4698 | 0.0226 | 0.1524 | 0.0305 |
| ds005114 | task_average_4s | occipital | relative_delta_power | 90 | -0.4525 | 0.0385 | 0.1524 | 0.0370 |
| ds005114 | task_average_4s | occipital | spectral_entropy_1_45 | 90 | 0.4293 | 0.0540 | 0.1524 | 0.0500 |

## Direction Consistency Against D1

| dataset_id | task_window | direction_matches | direction_tests | match_rate | notes |
| --- | --- | --- | --- | --- | --- |
| ds005114 | task_average_4s | 37 | 48 | 0.7708 | descriptive only |
| ds003523 | task_average_4s | 31 | 48 | 0.6458 | descriptive only |

Direction consistency is descriptive only. DPX task-average rows match the D1 direction for 37 of 48 feature-region cells, and visual working memory matches 31 of 48 cells. Because task-average FDR does not clear q < 0.10, this is a directional trace rather than a positive result.

## Within-Subject Cross-Task Stability

| task_a | task_b | region | feature_name | n_subjects | rho | fdr_q |
| --- | --- | --- | --- | --- | --- | --- |
| ds005114_task_average | ds003523_task_average | global | alpha_theta_ratio | 90 | 0.9538 | 7.823e-46 |
| ds005114_task_average | ds003523_task_average | occipital | alpha_theta_ratio | 90 | 0.9537 | 7.823e-46 |
| ds005114_task_average | ds003523_task_average | frontal | alpha_theta_ratio | 90 | 0.9531 | 9.286e-46 |
| ds005114_task_average | ds003523_task_average | central | alpha_theta_ratio | 90 | 0.9518 | 2.126e-45 |
| ds005114_task_average | ds003523_task_average | temporal | alpha_theta_ratio | 90 | 0.9515 | 2.312e-45 |
| ds005114_task_average | ds003523_task_average | occipital | relative_alpha_power | 90 | 0.9477 | 4.782e-44 |
| ds005114_task_average | ds003523_task_average | temporal | relative_alpha_power | 90 | 0.9452 | 2.961e-43 |
| ds005114_task_average | ds003523_task_average | central | relative_alpha_power | 90 | 0.9448 | 3.524e-43 |
| ds005114_task_average | ds003523_task_average | global | relative_alpha_power | 90 | 0.9435 | 8.818e-43 |
| ds005114_task_average | ds003523_task_average | temporal | relative_delta_power | 90 | 0.9225 | 5.573e-37 |

The strongest stability rows show high DPX/VWM rank-order consistency across the same 90 `Original_ID`s. This supports measurement reproducibility of spectral features across tasks, but it does not establish disease-specific convergence.

## Integrated Mixed Models

| metric | value |
| --- | --- |
| n_models | 48 |
| mixedlm_completed | 27 |
| clustered_ols_fallback | 21 |
| min_group_reference_task_fdr_q | 0.4665 |
| n_group_reference_task_q_lt_0p10 | 0 |

Mixed-effects modeling was numerically fragile for part of the feature family: 27 models completed as MixedLM and 21 used clustered OLS fallback. No group reference-task term survived FDR at q < 0.10.

## Decision Answers

- D2 provides only partial/inconsistent cross-task support.
- D2 weakens a robust-marker interpretation but does not fully falsify every directional trace.
- D2 does not rescue D1/D3.
- Supportable framing is an artifact-sensitivity/null-leaning report with a bounded cross-task check, not a positive diagnostic or prognostic story.

## Guardrails

- Keep acute mTBI vs control as the cleaner primary comparison.
- Keep chronic TBI separate and batch-sensitive.
- Do not pool repeated `Original_ID`s as independent people.
- Do not use classifiers to rescue the signal.
- Do not treat `ds003490` as TBI evidence.
- No validated biomarker, diagnostic biomarker, predictive biomarker, or independent validation claim is supported.
