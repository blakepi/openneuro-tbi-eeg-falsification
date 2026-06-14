from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils.common import project_path, read_rows_csv, script_finish, script_start, write_rows_csv


SCRIPT = "15_d3_eyes_closed_alpha_iaf_analysis.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gated D3 eyes-closed alpha/IAF extraction from D1 features.")
    parser.add_argument("--dataset", default="ds003522")
    parser.add_argument("--verification-csv", default="outputs/download_recovery/ds003522_post_download_verification.csv")
    args = parser.parse_args()

    start = script_start(SCRIPT, parameters=vars(args))
    errors: list[str] = []
    warnings: list[str] = []
    out_dir = project_path("outputs/d3_eyes_closed_alpha")
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "ds003522_d3_alpha_iaf_status.csv"

    try:
        require_verified_ds003522(project_path(args.verification_csv))
    except RuntimeError as exc:
        errors.append(str(exc))
        write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "refused", "reason": str(exc)}])
        script_finish(SCRIPT, start, outputs=[str(status_path)], warnings=warnings, errors=errors, parameters=vars(args), status="failed")
        raise SystemExit(str(exc))

    d1_rows = [row for row in read_rows_csv(project_path("outputs/features/d1_rest_features.csv")) if row.get("dataset_id") == args.dataset]
    keep_features = {"iaf_peak_frequency", "alpha_peak_power", "absolute_alpha_power", "relative_alpha_power", "theta_alpha_ratio", "alpha_theta_ratio"}
    rows = []
    for row in d1_rows:
        if row.get("condition") != "eyes_closed":
            continue
        if row.get("feature_name") not in keep_features:
            continue
        out = row.copy()
        out["analysis_family"] = "d3_eyes_closed_alpha_iaf"
        rows.append(out)
    if not rows:
        errors.append("No eyes-closed alpha/IAF rows found. Run D1 extraction first.")
    out_path = project_path("outputs/features/d3_ec_alpha_iaf_features.csv")
    write_rows_csv(out_path, rows)
    write_rows_csv(status_path, [{"dataset_id": args.dataset, "status": "completed" if rows else "failed", "rows": len(rows), "notes": "" if rows else "; ".join(errors)}])
    script_finish(SCRIPT, start, outputs=[str(out_path), str(status_path)], warnings=warnings, errors=errors, parameters=vars(args), status="completed" if not errors else "failed")
    if errors:
        raise SystemExit("; ".join(errors))


def require_verified_ds003522(verification_csv: Path) -> None:
    if not verification_csv.exists():
        raise RuntimeError(f"Refusing to run: missing verification CSV {verification_csv}.")
    rows = read_rows_csv(verification_csv)
    if not rows:
        raise RuntimeError(f"Refusing to run: verification CSV has no rows: {verification_csv}.")
    first = rows[0]
    for column, expected in {"summary_set_count": 200, "summary_fdt_count": 200, "summary_paired_count": 200, "summary_missing_fdt_count": 0}.items():
        observed = int(float(first.get(column, "")))
        if observed != expected:
            raise RuntimeError(f"Refusing to run: verification {column}={observed}, expected {expected}.")
    if sum(1 for row in rows if row.get("mne_read_test_status") == "passed") < 3:
        raise RuntimeError("Refusing to run: fewer than 3 MNE read-tests passed.")


if __name__ == "__main__":
    main()
