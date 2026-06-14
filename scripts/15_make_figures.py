from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, read_rows_csv, script_finish, script_start
from scripts.utils.plotting_utils import save_simple_bar


SCRIPT = "15_make_figures.py"


def main() -> None:
    start = script_start(SCRIPT)
    warnings = []
    outputs = []
    inventory = read_rows_csv(project_path("outputs/metadata/dataset_inventory.csv"))
    if not inventory:
        warnings.append("No dataset inventory available for figures.")
    else:
        try:
            labels = [row.get("dataset_id", "") for row in inventory]
            values = [float(row.get("n_eeg_data_files", "0") or 0) for row in inventory]
            path = project_path("outputs/figures/fig01_dataset_task_overview.png")
            save_simple_bar(path, "Candidate EEG files by dataset", labels, values, "EEG file count")
            outputs.append(str(path))
        except Exception as exc:
            warnings.append(f"Could not create dataset overview figure: {exc}")

    crosswalk = read_rows_csv(project_path("outputs/metadata/subject_crosswalk.csv"))
    if crosswalk:
        try:
            counts: dict[str, int] = {}
            for row in crosswalk:
                counts[row.get("dataset_id", "")] = counts.get(row.get("dataset_id", ""), 0) + 1
            path = project_path("outputs/figures/fig02_subject_overlap_upset_or_matrix.png")
            save_simple_bar(path, "Subject IDs indexed by dataset", list(counts), [float(v) for v in counts.values()], "Indexed subject IDs")
            outputs.append(str(path))
        except Exception as exc:
            warnings.append(f"Could not create subject overview figure: {exc}")
    else:
        warnings.append("No subject crosswalk available for overlap figure.")

    script_finish(SCRIPT, start, outputs=outputs, warnings=warnings)


if __name__ == "__main__":
    main()
