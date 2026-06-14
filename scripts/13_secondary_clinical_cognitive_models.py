from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, script_finish, script_start, write_rows_csv
from scripts.utils.reporting_utils import write_report


SCRIPT = "13_secondary_clinical_cognitive_models.py"


def main() -> None:
    start = script_start(SCRIPT)
    warnings = []
    clinical_sources = list(project_path("data/raw").rglob("*clinical*")) + list(project_path("data/raw").rglob("*behavior*")) + list(project_path("data/raw").rglob("*phenotype*"))
    outputs = []
    if not clinical_sources:
        warnings.append("No local clinical/cognitive source files were found under data/raw. Secondary models were not run.")

    output_specs = [
        "secondary_clinical_cross_sectional.csv",
        "secondary_cognitive_cross_sectional.csv",
        "secondary_longitudinal_models.csv",
    ]
    for name in output_specs:
        path = project_path("outputs/models", name)
        write_rows_csv(path, [])
        outputs.append(str(path))

    report_path = project_path("reports/07_secondary_clinical_cognitive_report.md")
    write_report(
        report_path,
        "Secondary Clinical and Cognitive Models",
        [
            ("Status", "Secondary models require downloaded local clinical/cognitive tables and matched stable person IDs. None were detected in this run." if warnings else "Secondary source files were detected; implement variable-specific models after variable inventory."),
            ("Interpretation Rule", "Clinical/cognitive associations are exploratory and should not be primary manuscript claims unless they survive multiplicity control and converge with D1/D3."),
        ],
    )
    outputs.append(str(report_path))
    script_finish(SCRIPT, start, outputs=outputs, warnings=warnings)


if __name__ == "__main__":
    main()
