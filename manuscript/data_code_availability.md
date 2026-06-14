# Data and Code Availability

This manuscript uses public OpenNeuro EEG datasets ds003522, ds005114, ds003523, and ds003490. ds003522 supplied the D1/D3 traumatic brain injury analyses. ds005114 and ds003523 supplied the bounded D2 cross-task analyses. ds003490 was used only as a comparator and pipeline rehearsal dataset and should not be cited as TBI evidence.

Dataset accessions and provisional dataset DOIs:

- ds003522: https://openneuro.org/datasets/ds003522, doi:10.18112/openneuro.ds003522.v1.1.0
- ds005114: https://openneuro.org/datasets/ds005114, doi:10.18112/openneuro.ds005114.v1.0.0
- ds003523: https://openneuro.org/datasets/ds003523, doi:10.18112/openneuro.ds003523.v1.1.0
- ds003490: https://openneuro.org/datasets/ds003490, doi:10.18112/openneuro.ds003490.v1.1.0

Local analysis outputs include raw-data verification reports, D1/D3 artifact-control outputs, D3 eyes-closed alpha/IAF outputs, D2 bounded cross-task outputs, final evidence matrices, figure/table source data, and manuscript claim traceability files. The reproduction guide is `reports/41_reproduction_and_handoff_guide.md`.

Subject identity overlap in D2 was handled using `Original_ID`. ds005114 and ds003523 were not pooled or interpreted as independent cohorts. Direction consistency and within-subject stability are treated as descriptive feature-stability context.

Sanitized public code and selected derived manuscript artifacts are available at:

https://github.com/blakepi/openneuro-tbi-eeg-falsification

The public repository excludes raw EEG files, DataLad annex contents, local paths, virtual environments, credential material, and administrative logs. A Zenodo DOI has not yet been minted. If the GitHub-Zenodo integration is enabled after final reference verification, a GitHub release can be archived and the resulting DOI should be inserted here.
