import json
from pathlib import Path

from ffrepro.bundles import verify_official_bundles


def test_detects_rubric_category_count_mismatch(tmp_path: Path) -> None:
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "query_id": "q1",
                "query": "x",
                "query_date": "2025-01-01",
                "use_cases": ["company_research"],
                "capabilities": [],
                "rubrics": [
                    {
                        "rubric_id": 1,
                        "rubric_text": "x",
                        "must_have": True,
                        "rubric_type": "Forward-Looking Information",
                        "data_source_type": "na",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance = tmp_path / "performance.json"
    performance.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "id": "run",
                        "num_records": 1,
                        "cost_per_query": 0.1,
                        "total_cost": 0.1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    breakdowns = tmp_path / "breakdowns.json"
    breakdowns.write_text(
        json.dumps(
            {
                "run": {
                    "rubric_type_scores": [
                        {
                            "type": "Forward-Looking Information",
                            "n_criteria": 2,
                            "score": 0.5,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    report = verify_official_bundles(
        dataset_path=dataset,
        performance_path=performance,
        breakdowns_path=breakdowns,
    )
    assert report["anomalies"] == [
        {
            "type": "rubric_type_count_mismatch",
            "rubric_type": "Forward-Looking Information",
            "bundle": 2,
            "dataset": 1,
            "delta": 1,
        }
    ]
