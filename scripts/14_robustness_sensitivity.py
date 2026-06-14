from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, read_rows_csv, safe_float, script_finish, script_start, write_rows_csv
from scripts.utils.reporting_utils import write_report


SCRIPT = "14_robustness_sensitivity.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", default="all")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    warnings = []
    model_rows = read_rows_csv(project_path("outputs/models/d1_d3_group_models.csv"))
    if not model_rows:
        warnings.append("No D1/D3 model rows available; robustness tables are empty.")

    robustness_rows = []
    for row in model_rows:
        effect = safe_float(row.get("hedges_g"))
        q = safe_float(row.get("fdr_q"))
        perm = safe_float(row.get("permutation_p"))
        label = label_signal(effect, q, perm, row)
        out = row.copy()
        out["robustness_label"] = label
        out["robustness_score"] = str(score_signal(effect, q, perm))
        out["artifact_sensitivity_status"] = "not_fully_tested" if "eyes_open" in row.get("condition", "") else "pending_emg_sensitivity"
        robustness_rows.append(out)

    output_files = [
        "top_signal_robustness_summary.csv",
        "bootstrap_results.csv",
        "permutation_results.csv",
        "leave_one_out_results.csv",
        "specparam_sensitivity_results.csv",
        "emg_sensitivity_results.csv",
        "iaf_sensitivity_results.csv",
        "d2_sensitivity_results.csv",
    ]
    outputs = []
    for filename in output_files:
        path = project_path("outputs/robustness", filename)
        if filename == "top_signal_robustness_summary.csv":
            write_rows_csv(path, robustness_rows)
        else:
            write_rows_csv(path, [])
        outputs.append(str(path))

    report_path = project_path("reports/08_robustness_sensitivity_report.md")
    write_report(
        report_path,
        "Robustness and Sensitivity",
        [
            ("Status", f"Robustness rows generated: {len(robustness_rows)}. Empty sensitivity branch files indicate raw-data-dependent analyses still need to be run." if robustness_rows else "No top signals were available for robustness testing."),
            ("Required Branches Still To Confirm", "EMG exclusion/covariate, frontal-temporal exclusion, specparam range sensitivity, IRASA, permutation, bootstrap, and leave-one-out branches must be interpreted from completed outputs before scientific claims are made."),
        ],
    )
    outputs.append(str(report_path))
    script_finish(SCRIPT, start, outputs=outputs, warnings=warnings, parameters=vars(args))


def label_signal(effect: float | None, q: float | None, perm: float | None, row: dict[str, str]) -> str:
    if effect is None or not math.isfinite(effect):
        return "underpowered"
    if q is not None and math.isfinite(q) and q < 0.05 and abs(effect) >= 0.8:
        return "moderate"
    if q is not None and math.isfinite(q) and q < 0.10 and abs(effect) >= 0.5:
        return "moderate"
    if perm is not None and math.isfinite(perm) and perm < 0.05 and abs(effect) >= 0.5:
        return "fragile"
    return "underpowered"


def score_signal(effect: float | None, q: float | None, perm: float | None) -> float:
    if effect is None or not math.isfinite(effect):
        return 0.0
    effect_score = min(abs(effect) / 1.2, 1.0)
    q_score = 0.0 if q is None or not math.isfinite(q) else max(0.0, min(1.0, 1.0 - q / 0.10))
    perm_score = 0.0 if perm is None or not math.isfinite(perm) else max(0.0, min(1.0, 1.0 - perm / 0.10))
    return round(0.45 * effect_score + 0.35 * q_score + 0.20 * perm_score, 3)


if __name__ == "__main__":
    main()
