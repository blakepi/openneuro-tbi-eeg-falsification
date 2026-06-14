# Integrated D1 D2 D3 Final Decision Report

Generated: 2026-06-13

## Final Decision

The project should be framed as an **artifact-sensitive, null-leaning public EEG analysis with a weak/context-specific cross-task trace**. D2 adds a bounded reproducibility/falsification check but does not overturn the D1/D3 caution.

## Decision Matrix

| domain | decision | key_value |
| --- | --- | --- |
| D1 rest | artifact-sensitive/null-leaning | acute artifact-controlled broad min q = 0.7876 |
| D1 narrow prior-anchor | exploratory only | narrow q = 0.1320 |
| D3 eyes-closed alpha/IAF | does not rescue acute signal | posterior acute min q = 0.9149 |
| chronic TBI | separate and batch-sensitive | artifact-trimmed chronic min q = 0.3484 |
| D2 DPX/VWM | partial/inconsistent cross-task support | overall min q = 0.0898; mixed q<0.10 count = 0 |
| Final framing | artifact-sensitivity/null-leaning reproducibility report | no positive diagnostic, prognostic, or biomarker claim |

## D2 Interpretation

The only D2 q < 0.10 trace is in `ds005114` DPX cue-baseline features (minimum q = 0.0898, max |g| = 0.5277). The more general task-average tests are weaker: DPX task-average minimum q = 0.1524, and VWM task-average minimum q = 0.4720. Mixed-effects models have 0 group terms below q < 0.10.

## D1/D3 Interpretation

D1 remains fragile after artifact control: acute mTBI vs control does not survive broad artifact-controlled FDR (minimum q = 0.7876). The narrower prior-anchor family remains exploratory and non-confirmatory (q = 0.1320). D3 posterior alpha/IAF does not rescue the signal (minimum q = 0.9149). Chronic TBI effects remain separate and batch-sensitive (minimum q = 0.3484).

## ds003490 Role

`ds003490` remains a comparator/pipeline rehearsal dataset only. It is not TBI validation and is not evidence for a TBI claim.

## Recommended Scientific Framing

Use a cautious methods/results framing: public EEG TBI analyses show how apparent spectral effects attenuate under artifact control and cross-task falsification. The main contribution is transparency about fragility, identity overlap, and task context.

## Not Supported

- A positive diagnostic, prognostic, predictive, or clinical-utility claim.
- No validated biomarker or confirmed-marker claim.
- Independent-cohort confirmation from D2.
- Chronic and acute pooling.
- A classifier-based rescue analysis.
- Treating comparator dataset `ds003490` as TBI evidence.
