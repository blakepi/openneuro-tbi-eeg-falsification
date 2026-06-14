# D1/D3 Post-Analysis Audit

Generated: 2026-06-13

## Technical Summary

The D1/D3 analysis is best classified as **artifact-sensitive candidate requiring caution**. The acute mTBI vs control signal remains coherent enough to audit, but it does not survive the broad preplanned FDR families after artifact control. The strongest artifact-trimmed acute effects are mostly eyes-open spectral-balance or entropy-type effects, with minimum broad FDR q = 0.7876. This is not a biomarker result and not validation.

The prior Phase 5 lead signal did not numerically survive in its original reported magnitude. The only locally available original evidence is an execution-prompt anchor, not exact per-feature model rows: Original Phase 5 numeric per-feature rows were not available locally. The audit uses the execution-prompt anchor: acute mTBI vs control roughly abs(g)=0.80-0.96 with broad-screen FDR<0.10, chronic up to about abs(g)=1.11 with some FDR<0.05, centered on eyes-open temporal/frontal/global aperiodic/spectral features. Against that anchor, the new acute artifact-trimmed effects attenuate to absolute g values mostly below 0.65 and fail FDR.

Artifact control changes the interpretation. The strict 250 microvolt branch is unusable for group modeling because it retains too few recording-condition rows. The ptp95 branch keeps recording coverage but trims high-amplitude epochs. Artifact-sensitivity rows are mostly direction-stable (449 stable, 31 changed/unavailable), yet the reliance on eyes-open frontal/temporal/global features keeps the candidate artifact-sensitive.

D3 eyes-closed alpha/IAF does not rescue the acute finding. The posterior D3 acute minimum FDR q is 0.9149, and no aperiodic-adjusted alpha peak metric is available in the generated D3 table. Chronic TBI effects remain larger in places, but chronic is secondary and batch-sensitive; after artifact trim its minimum broad q is 0.3484.

## Original Lead Signal Vs Artifact-Controlled Results

The original Phase 5 signal is available only as a prose anchor, so the audit traces nearest-equivalent features rather than pretending exact original rows exist. The key pattern was eyes-open temporal/frontal/global aperiodic/spectral differences with acute mTBI absolute g around 0.80-0.96 and FDR below 0.10 in a broad screen.

| feature_name          | region   | new_effect_direction | new_hedges_g | raw_p   | fdr_q  | direction_persisted | effect_attenuated_vs_original_anchor | artifact_sensitivity_label       |
| --------------------- | -------- | -------------------- | ------------ | ------- | ------ | ------------------- | ------------------------------------ | -------------------------------- |
| aperiodic_exponent    | global   | lower_in_group1_tbi  | -0.1657      | 0.4722  | 0.8414 | true                | true                                 | direction_stable                 |
| aperiodic_exponent    | frontal  | lower_in_group1_tbi  | -0.3217      | 0.2253  | 0.7876 | true                | true                                 | direction_stable                 |
| aperiodic_exponent    | temporal | lower_in_group1_tbi  | -0.2407      | 0.351   | 0.801  | true                | true                                 | direction_stable                 |
| aperiodic_offset      | global   | higher_in_group1_tbi | 0.2048       | 0.4435  | 0.8224 | false               | true                                 | direction_stable                 |
| aperiodic_offset      | frontal  | lower_in_group1_tbi  | -0.5399      | 0.04607 | 0.7876 | true                | true                                 | direction_stable                 |
| aperiodic_offset      | temporal | lower_in_group1_tbi  | -0.2771      | 0.2822  | 0.7876 | true                | true                                 | direction_stable                 |
| spectral_entropy_1_45 | global   | higher_in_group1_tbi | 0.4811       | 0.03554 | 0.7876 | true                | true                                 | direction_stable                 |
| spectral_entropy_1_45 | frontal  | higher_in_group1_tbi | 0.1563       | 0.5502  | 0.8877 | true                | true                                 | direction_stable                 |
| spectral_entropy_1_45 | temporal | lower_in_group1_tbi  | -0.1238      | 0.608   | 0.9041 | false               | true                                 | direction_changed_or_unavailable |
| relative_delta_power  | global   | lower_in_group1_tbi  | -0.5538      | 0.01258 | 0.7876 |                     | true                                 | direction_stable                 |
| relative_delta_power  | frontal  | lower_in_group1_tbi  | -0.2057      | 0.4089  | 0.8224 |                     | true                                 | direction_stable                 |
| relative_delta_power  | temporal | higher_in_group1_tbi | 0.001882     | 0.9939  | 0.9939 |                     | true                                 | direction_stable                 |
| relative_alpha_power  | global   | higher_in_group1_tbi | 0.5629       | 0.01036 | 0.7876 |                     | true                                 | direction_stable                 |
| relative_alpha_power  | frontal  | higher_in_group1_tbi | 0.1539       | 0.5078  | 0.8492 |                     | true                                 | direction_stable                 |

Interpretation: the nearest-equivalent acute rows are mostly attenuated relative to the reported original cluster. Some directions are coherent with the prior anchor, especially offset and entropy-like rows, but broad FDR failure and artifact sensitivity prevent a positive claim.

## Branch-By-Branch Result Summary

`all_epochs` and `artifact_trim_ptp95` both model acute mTBI vs control with n=70 subject-level observations for the main comparison. The strict fixed-threshold branch does not produce group model rows.

| artifact_branch         | group_normalized | condition   | possible_recording_conditions | included_recording_conditions | excluded_recording_conditions | median_usable_epoch_fraction | exclusion_reasons                                        |
| ----------------------- | ---------------- | ----------- | ----------------------------- | ----------------------------- | ----------------------------- | ---------------------------- | -------------------------------------------------------- |
| artifact_clean_ptp250uv | chronic_tbi      | eyes_closed | 25.000                        | 0                             | 25.000                        | 0                            | {"no_epochs_after_artifact_filter": 25}                  |
| artifact_clean_ptp250uv | chronic_tbi      | eyes_open   | 25.000                        | 0                             | 25.000                        | 0                            | {"no_epochs_after_artifact_filter": 25}                  |
| artifact_clean_ptp250uv | control          | eyes_closed | 73.000                        | 1.000                         | 72.000                        | 0                            | {"no_epochs_after_artifact_filter": 72, "processed": 1}  |
| artifact_clean_ptp250uv | control          | eyes_open   | 73.000                        | 1.000                         | 72.000                        | 0                            | {"no_epochs_after_artifact_filter": 72, "processed": 1}  |
| artifact_clean_ptp250uv | mtbi             | eyes_closed | 101.0                         | 1.000                         | 100.0                         | 0                            | {"no_epochs_after_artifact_filter": 100, "processed": 1} |
| artifact_clean_ptp250uv | mtbi             | eyes_open   | 101.0                         | 1.000                         | 100.0                         | 0                            | {"no_epochs_after_artifact_filter": 100, "processed": 1} |
| artifact_trim_ptp95     | chronic_tbi      | eyes_closed | 25.000                        | 25.000                        | 0                             | 0.9333                       | {"processed": 25}                                        |
| artifact_trim_ptp95     | chronic_tbi      | eyes_open   | 25.000                        | 25.000                        | 0                             | 0.9333                       | {"processed": 25}                                        |
| artifact_trim_ptp95     | control          | eyes_closed | 73.000                        | 73.000                        | 0                             | 0.9333                       | {"processed": 73}                                        |
| artifact_trim_ptp95     | control          | eyes_open   | 73.000                        | 73.000                        | 0                             | 0.9333                       | {"processed": 73}                                        |
| artifact_trim_ptp95     | mtbi             | eyes_closed | 101.0                         | 101.0                         | 0                             | 0.9333                       | {"processed": 101}                                       |
| artifact_trim_ptp95     | mtbi             | eyes_open   | 101.0                         | 101.0                         | 0                             | 0.9333                       | {"processed": 101}                                       |

The ptp95 branch is not a subject-exclusion branch; it removes the highest-amplitude epochs within recording-condition and keeps all modeled recording-condition rows. The strict branch is too conservative and would bias inference by leaving almost no usable data.

## FDR Family Audit

FDR was applied separately by analysis family, comparison, and artifact branch. Acute and chronic comparisons were not mixed, and artifact branches were not mixed. However, within each D1 family, eyes-open and eyes-closed, six regions, and 17 features are corrected together. That broad scope explains why the minimum acute trimmed q is high even when nominal p-values exist.

| family_name                                                                             | scope_type                                    | n_tests | conditions            | regions                                            | n_features | min_welch_p | min_pipeline_fdr_q | min_recomputed_bh_q | interpretation                                                                                                                                                    |
| --------------------------------------------------------------------------------------- | --------------------------------------------- | ------- | --------------------- | -------------------------------------------------- | ---------- | ----------- | ------------------ | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| actual_fdr_family::d1_rest_artifact_control::acute_mtbi_vs_control::artifact_trim_ptp95 | actual_pipeline_fdr_family                    | 204.0   | eyes_closed;eyes_open | central;frontal;global;occipital;parietal;temporal | 17.000     | 0.01036     | 0.7876             | 0.7876              | 204 tests corrected together; D1 combines EO/EC, six regions, and all D1 features within this comparison/branch; acute/chronic and artifact branches are separate |
| narrow_prior_anchor_d1_eyes_open_global_frontal_temporal                                | post_hoc_transparency_family_not_claim_rescue | 21.000  | eyes_open             | frontal;global;temporal                            | 7.000      | 0.01036     | 0.7876             | 0.132               | Exploratory narrower-family audit only; not a rescued confirmatory endpoint.                                                                                      |
| narrow_d3_posterior_alpha_iaf_trim                                                      | post_hoc_transparency_family_not_claim_rescue | 12.000  | eyes_closed           | occipital;parietal                                 | 6.000      | 0.3613      | 0.9149             | 0.9226              | Exploratory narrower-family audit only; not a rescued confirmatory endpoint.                                                                                      |
| d1_trim_no_temporal_frontal                                                             | post_hoc_transparency_family_not_claim_rescue | 42.000  | eyes_closed;eyes_open | central;occipital;parietal                         | 7.000      | 0.06947     | 0.7876             | 0.9708              | Exploratory narrower-family audit only; not a rescued confirmatory endpoint.                                                                                      |

The q around 0.788 is not a single-row artifact: it is the minimum broad FDR q for the acute artifact-trimmed D1 family. A narrower prior-anchor family changes the q-value, but it remains an exploratory post hoc transparency calculation, not a rescued confirmatory endpoint.

## Artifact Proxy Audit

High-frequency proxy fields were available (`emg_index_region`, `line_noise_index_region`) and were summarized from the D1 feature rows. For the strongest acute trimmed effects, adding these proxies as covariates produced a median approximate group-coefficient attenuation of 0.09681 across estimable top models. This supports caution but is not a definitive artifact explanation.

Proxy distributions show that group differences are not one-sided across every region/metric, but eyes-open frontal/temporal/global proxies are still central enough to keep the lead D1 pattern artifact-sensitive.

| check_id                                                          | value   | interpretation                                                      |
| ----------------------------------------------------------------- | ------- | ------------------------------------------------------------------- |
| proxy_emg_index_region_eyes_open_global_control_mean              | 0.01652 | Mean emg_index_region for control in eyes_open global.              |
| proxy_emg_index_region_eyes_open_global_mtbi_mean                 | 0.0162  | Mean emg_index_region for mtbi in eyes_open global.                 |
| proxy_emg_index_region_eyes_open_global_chronic_tbi_mean          | 0.01572 | Mean emg_index_region for chronic_tbi in eyes_open global.          |
| proxy_line_noise_index_region_eyes_open_global_control_mean       | 0.2302  | Mean line_noise_index_region for control in eyes_open global.       |
| proxy_line_noise_index_region_eyes_open_global_mtbi_mean          | 0.2205  | Mean line_noise_index_region for mtbi in eyes_open global.          |
| proxy_line_noise_index_region_eyes_open_global_chronic_tbi_mean   | 0.2834  | Mean line_noise_index_region for chronic_tbi in eyes_open global.   |
| proxy_emg_index_region_eyes_open_frontal_control_mean             | 0.03547 | Mean emg_index_region for control in eyes_open frontal.             |
| proxy_emg_index_region_eyes_open_frontal_mtbi_mean                | 0.03678 | Mean emg_index_region for mtbi in eyes_open frontal.                |
| proxy_emg_index_region_eyes_open_frontal_chronic_tbi_mean         | 0.04788 | Mean emg_index_region for chronic_tbi in eyes_open frontal.         |
| proxy_line_noise_index_region_eyes_open_frontal_control_mean      | 0.02623 | Mean line_noise_index_region for control in eyes_open frontal.      |
| proxy_line_noise_index_region_eyes_open_frontal_mtbi_mean         | 0.01667 | Mean line_noise_index_region for mtbi in eyes_open frontal.         |
| proxy_line_noise_index_region_eyes_open_frontal_chronic_tbi_mean  | 0.01138 | Mean line_noise_index_region for chronic_tbi in eyes_open frontal.  |
| proxy_emg_index_region_eyes_open_temporal_control_mean            | 0.08473 | Mean emg_index_region for control in eyes_open temporal.            |
| proxy_emg_index_region_eyes_open_temporal_mtbi_mean               | 0.08819 | Mean emg_index_region for mtbi in eyes_open temporal.               |
| proxy_emg_index_region_eyes_open_temporal_chronic_tbi_mean        | 0.1303  | Mean emg_index_region for chronic_tbi in eyes_open temporal.        |
| proxy_line_noise_index_region_eyes_open_temporal_control_mean     | 0.09236 | Mean line_noise_index_region for control in eyes_open temporal.     |
| proxy_line_noise_index_region_eyes_open_temporal_mtbi_mean        | 0.02419 | Mean line_noise_index_region for mtbi in eyes_open temporal.        |
| proxy_line_noise_index_region_eyes_open_temporal_chronic_tbi_mean | 0.066   | Mean line_noise_index_region for chronic_tbi in eyes_open temporal. |

Group-difference effect sizes for the same proxy rows:

| check_id                                                   | value    | interpretation                                                                                        |
| ---------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------- |
| proxy_emg_index_region_eyes_open_global_acute_g            | -0.02331 | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_emg_index_region_eyes_open_global_chronic_g          | -0.06214 | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |
| proxy_line_noise_index_region_eyes_open_global_acute_g     | -0.03272 | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_line_noise_index_region_eyes_open_global_chronic_g   | 0.1731   | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |
| proxy_emg_index_region_eyes_open_frontal_acute_g           | 0.02662  | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_emg_index_region_eyes_open_frontal_chronic_g         | 0.2254   | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |
| proxy_line_noise_index_region_eyes_open_frontal_acute_g    | -0.1354  | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_line_noise_index_region_eyes_open_frontal_chronic_g  | -0.1784  | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |
| proxy_emg_index_region_eyes_open_temporal_acute_g          | 0.04802  | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_emg_index_region_eyes_open_temporal_chronic_g        | 0.5142   | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |
| proxy_line_noise_index_region_eyes_open_temporal_acute_g   | -0.432   | Positive means higher proxy in mTBI than control; large values would support artifact concern.        |
| proxy_line_noise_index_region_eyes_open_temporal_chronic_g | -0.1184  | Positive means higher proxy in chronic TBI than control; large values would support artifact concern. |

Temporal/frontal/global effects remain the most visually coherent part of the acute candidate. When temporal/frontal regions are excluded, effect sizes remain present in some central/parietal/occipital rows, but broad FDR still fails.

| check_id                                          | value   | interpretation                                                                                                        |
| ------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| artifact_proxy_covariate_median_attenuation_top12 | 0.09681 | Approximate OLS group-coefficient attenuation after adding EMG and line-noise proxies for the top acute trim effects. |
| artifact_proxy_covariate_n_models                 | 12.000  | Number of top acute trim models where proxy-adjusted attenuation was estimable.                                       |
| temporal_frontal_global_min_fdr_q                 | 0.7876  | Minimum FDR q in this sensitivity slice.                                                                              |
| temporal_frontal_global_max_abs_g                 | 0.6127  | Largest absolute Hedges g in this sensitivity slice.                                                                  |
| central_parietal_occipital_only_min_fdr_q         | 0.7876  | Minimum FDR q in this sensitivity slice.                                                                              |
| central_parietal_occipital_only_max_abs_g         | 0.4929  | Largest absolute Hedges g in this sensitivity slice.                                                                  |
| eyes_open_only_min_fdr_q                          | 0.7876  | Minimum FDR q in this sensitivity slice.                                                                              |
| eyes_open_only_max_abs_g                          | 0.6127  | Largest absolute Hedges g in this sensitivity slice.                                                                  |
| eyes_closed_only_min_fdr_q                        | 0.7876  | Minimum FDR q in this sensitivity slice.                                                                              |
| eyes_closed_only_max_abs_g                        | 0.4866  | Largest absolute Hedges g in this sensitivity slice.                                                                  |

## Sample-Composition Audit

The strict branch changed sample composition severely because almost all recording-condition rows failed its fixed peak-to-peak threshold. The ptp95 branch did not exclude subjects or recording-condition rows; it changed epoch composition within each recording-condition. That makes ptp95 better suited for sensitivity than strict thresholding, but it remains an artifact-control sensitivity branch rather than a clean validation branch.

Full sample counts are saved to `outputs/qc/d1_d3_artifact_branch_sample_counts.csv`.

## D3 Alpha/IAF Audit

D3 is cleaner in the sense that it is eyes-closed and posterior regions can be inspected directly. It does not provide a strong supportive acute signal in the current outputs.

| comparison            | artifact_branch     | region   | feature_name         | n_group0 | n_group1 | hedges_g | welch_p | fdr_q  | permutation_p |
| --------------------- | ------------------- | -------- | -------------------- | -------- | -------- | -------- | ------- | ------ | ------------- |
| acute_mtbi_vs_control | artifact_trim_ptp95 | frontal  | absolute_alpha_power | 26.000   | 44.000   | -0.4206  | 0.1986  | 0.9149 | 0.05259       |
| acute_mtbi_vs_control | artifact_trim_ptp95 | global   | relative_alpha_power | 26.000   | 44.000   | 0.4181   | 0.06347 | 0.9149 | 0.08538       |
| acute_mtbi_vs_control | artifact_trim_ptp95 | temporal | absolute_alpha_power | 26.000   | 44.000   | -0.4149  | 0.2061  | 0.9149 | 0.0194        |
| acute_mtbi_vs_control | artifact_trim_ptp95 | central  | absolute_alpha_power | 26.000   | 44.000   | -0.4107  | 0.2033  | 0.9149 | 0.09198       |
| acute_mtbi_vs_control | artifact_trim_ptp95 | temporal | alpha_peak_power     | 26.000   | 44.000   | -0.3804  | 0.2452  | 0.9149 | 0.0232        |
| acute_mtbi_vs_control | artifact_trim_ptp95 | frontal  | alpha_peak_power     | 26.000   | 44.000   | -0.3798  | 0.2444  | 0.9149 | 0.07139       |

For acute mTBI vs control, D3 supports at most a weak exploratory check. It does not become the lead. It also lacks aperiodic-adjusted alpha peak metrics in the generated D3 table, so any alpha interpretation should remain preliminary.

## Chronic TBI Interpretation

Chronic effects remain larger than acute effects in several eyes-open aperiodic/spectral rows, but they do not survive broad FDR after artifact trim and remain batch/recruitment sensitive.

| analysis_family          | comparison             | artifact_branch     | condition | region   | feature_name                    | n_group0 | n_group1 | hedges_g | welch_p  | fdr_q  | permutation_p |
| ------------------------ | ---------------------- | ------------------- | --------- | -------- | ------------------------------- | -------- | -------- | -------- | -------- | ------ | ------------- |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | central  | aperiodic_exponent              | 26.000   | 25.000   | -0.8694  | 0.003175 | 0.3484 | 0.0016        |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | temporal | aperiodic_offset                | 26.000   | 25.000   | -0.7867  | 0.006193 | 0.3484 | 0.005199      |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | parietal | aperiodic_exponent              | 26.000   | 25.000   | -0.7829  | 0.006832 | 0.3484 | 0.003799      |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | central  | aperiodic_offset                | 26.000   | 25.000   | -0.7768  | 0.006822 | 0.3484 | 0.003399      |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | central  | relative_low_gamma_or_emg_power | 26.000   | 25.000   | 0.7593   | 0.01036  | 0.388  | 0.005799      |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | central  | spectral_entropy_1_45           | 26.000   | 25.000   | 0.7272   | 0.01208  | 0.388  | 0.0116        |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | parietal | aperiodic_offset                | 26.000   | 25.000   | -0.6963  | 0.01481  | 0.388  | 0.005599      |
| d1_rest_artifact_control | chronic_tbi_vs_control | artifact_trim_ptp95 | eyes_open | parietal | relative_low_gamma_or_emg_power | 26.000   | 25.000   | 0.6848   | 0.02016  | 0.388  | 0.0126        |

Chronic TBI can be discussed only as exploratory supporting context. It should not be combined with acute mTBI and should not be used as proof.

## Limitations And Robustness

- Original Phase 5 exact model rows were not present locally; the original comparison uses the documented prior-anchor prose, not feature-specific original estimates.
- The strict 250 microvolt branch is overconservative and unusable for group inference.
- The ptp95 branch preserves recording coverage but is still a sensitivity branch, not a gold-standard artifact correction.
- D1 features use log-log fallback aperiodic estimates rather than a full specparam/IRASA re-estimation branch for ds003522.
- No D2 convergence analysis has been started.
- `ds003490` remains comparator/pipeline rehearsal only and is not TBI validation.

## Recommended Next Step

Proceed to D2 downloads only if the next phase is explicitly framed as a bounded falsification/reproducibility check of a fragile D1 candidate. Do not proceed as if D1/D3 found a validated or robust biomarker. The current project value is a rigorous artifact-sensitivity/null-leaning report plus a transparent cross-task check.
