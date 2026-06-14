# Data and Code Availability

This manuscript uses public OpenNeuro EEG datasets ds003522, ds005114, ds003523, and ds003490. ds003522 supplied the D1/D3 traumatic brain injury analyses. ds005114 and ds003523 supplied the bounded D2 cross-task analyses. ds003490 was used only as a comparator and pipeline rehearsal dataset and should not be cited as TBI evidence.

Dataset accessions and verified/provisional dataset DOI metadata:

- ds003522: EEG: Three-Stim Auditory Oddball and Rest in Acute and Chronic TBI; OpenNeuro version 1.1.0; issued 2021; https://openneuro.org/datasets/ds003522/versions/1.1.0; doi:10.18112/openneuro.ds003522.v1.1.0. Final wording remains human-verification-needed because DataCite and local title fields differ.
- ds005114: EEG: DPX Cog Ctl Task in Acute Mild TBI; OpenNeuro version 1.0.0; issued 2024; https://openneuro.org/datasets/ds005114/versions/1.0.0; doi:10.18112/openneuro.ds005114.v1.0.0.
- ds003523: EEG: Visual Working Memory in Acute TBI; OpenNeuro version 1.1.0; issued 2021; https://openneuro.org/datasets/ds003523/versions/1.1.0; doi:10.18112/openneuro.ds003523.v1.1.0.
- ds003490: EEG: 3-Stim Auditory Oddball and Rest in Parkinson's; OpenNeuro version 1.1.0; issued 2021; https://openneuro.org/datasets/ds003490/versions/1.1.0; doi:10.18112/openneuro.ds003490.v1.1.0. Final author formatting remains human-verification-needed because the source creator field includes an email string.

Local analysis outputs include raw-data verification reports, D1/D3 artifact-control outputs, D3 eyes-closed alpha/IAF outputs, D2 bounded cross-task outputs, final evidence matrices, figure/table source data, and manuscript claim traceability files. The reproduction guide is `reports/41_reproduction_and_handoff_guide.md`.

Subject identity overlap in D2 was handled using `Original_ID`. ds005114 and ds003523 were not pooled or interpreted as independent cohorts. Direction consistency and within-subject stability are treated as descriptive feature-stability context.

Code and selected derived manuscript artifacts are publicly available at:

https://github.com/blakepi/openneuro-tbi-eeg-falsification

The public repository excludes raw EEG files, DataLad annex contents, local paths, virtual environments, credential material, and administrative logs. A Zenodo DOI has not yet been minted. The prepared Zenodo metadata should be used only after final reference verification and a deliberate GitHub release/archive step.
