from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ffrepro.io import sha256_file

OFFICIAL_DATASET_SHA256 = "a82874d7a587baf6f1ebe79b95fa1c3090260d3661c544f4496056d338e313c4"


def inspect_dataset(path: Path) -> dict[str, Any]:
    rows = 0
    rubrics = 0
    must_have = 0
    use_cases: Counter[str] = Counter()
    capabilities: Counter[str] = Counter()
    rubric_types: Counter[str] = Counter()
    source_types: Counter[str] = Counter()
    rubric_counts: list[int] = []
    query_ids: set[str] = set()

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            query_id = str(row["query_id"])
            if query_id in query_ids:
                raise ValueError(f"Duplicate query_id at line {line_number}: {query_id}")
            query_ids.add(query_id)
            rows += 1
            row_rubrics = row.get("rubrics", [])
            rubric_counts.append(len(row_rubrics))
            rubrics += len(row_rubrics)
            use_cases.update(row.get("use_cases", []))
            capabilities.update(row.get("capabilities", []))
            for rubric in row_rubrics:
                must_have += int(bool(rubric.get("must_have")))
                rubric_types[rubric.get("rubric_type", "(unspecified)")] += 1
                source_types[rubric.get("data_source_type", "(unspecified)")] += 1

    sorted_counts = sorted(rubric_counts)
    median = sorted_counts[len(sorted_counts) // 2] if sorted_counts else 0
    digest = sha256_file(path)
    return {
        "path": str(path),
        "sha256": digest,
        "matches_pinned_official_snapshot": digest == OFFICIAL_DATASET_SHA256,
        "queries": rows,
        "rubrics": rubrics,
        "must_have_rubrics": must_have,
        "nice_to_have_rubrics": rubrics - must_have,
        "rubrics_per_query": {
            "min": min(rubric_counts, default=0),
            "median": median,
            "max": max(rubric_counts, default=0),
            "mean": rubrics / rows if rows else 0,
        },
        "use_cases": dict(sorted(use_cases.items())),
        "capabilities": dict(sorted(capabilities.items())),
        "rubric_types": dict(sorted(rubric_types.items())),
        "data_source_types": dict(sorted(source_types.items())),
    }
