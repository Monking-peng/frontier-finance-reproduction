from __future__ import annotations

from pathlib import Path
from typing import Any

from ffrepro.dataset import inspect_dataset
from ffrepro.io import read_json, sha256_file


def verify_official_bundles(
    *, dataset_path: Path, performance_path: Path, breakdowns_path: Path
) -> dict[str, Any]:
    dataset = inspect_dataset(dataset_path)
    performance = read_json(performance_path)
    breakdowns = read_json(breakdowns_path)

    anomalies: list[dict[str, Any]] = []
    runs = performance.get("runs", [])
    for run in runs:
        if run.get("num_records") != dataset["queries"]:
            anomalies.append(
                {
                    "type": "record_count_mismatch",
                    "run_id": run.get("id"),
                    "bundle": run.get("num_records"),
                    "dataset": dataset["queries"],
                }
            )
        expected_total = round(run["cost_per_query"] * run["num_records"], 2)
        if abs(expected_total - run["total_cost"]) > 0.02:
            anomalies.append(
                {
                    "type": "total_cost_mismatch",
                    "run_id": run.get("id"),
                    "bundle": run["total_cost"],
                    "computed_from_rounded_average": expected_total,
                }
            )

    first_breakdown = next(iter(breakdowns.values()), {})
    displayed_counts = {
        row["type"]: row["n_criteria"] for row in first_breakdown.get("rubric_type_scores", [])
    }
    dataset_counts = dataset["rubric_types"]
    for rubric_type in sorted(set(displayed_counts) | set(dataset_counts)):
        if rubric_type not in displayed_counts:
            continue  # The public radar intentionally omits two small categories.
        if displayed_counts[rubric_type] != dataset_counts.get(rubric_type):
            anomalies.append(
                {
                    "type": "rubric_type_count_mismatch",
                    "rubric_type": rubric_type,
                    "bundle": displayed_counts[rubric_type],
                    "dataset": dataset_counts.get(rubric_type, 0),
                    "delta": displayed_counts[rubric_type] - dataset_counts.get(rubric_type, 0),
                }
            )

    return {
        "dataset": {
            "path": str(dataset_path),
            "sha256": dataset["sha256"],
            "queries": dataset["queries"],
            "rubrics": dataset["rubrics"],
        },
        "bundles": {
            "system_performance_sha256": sha256_file(performance_path),
            "run_breakdowns_sha256": sha256_file(breakdowns_path),
            "systems": len(runs),
        },
        "anomalies": anomalies,
    }
