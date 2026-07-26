from pathlib import Path

from ffrepro.dataset import inspect_dataset


def test_demo_fixture_is_valid_jsonl() -> None:
    root = Path(__file__).resolve().parents[1]
    stats = inspect_dataset(root / "data" / "demo" / "frontier_finance_tsla_q4_2024.jsonl")
    assert stats["queries"] == 1
    assert stats["rubrics"] == 16
    assert stats["must_have_rubrics"] == 5
