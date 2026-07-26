from decimal import Decimal

from ffrepro.audit import evaluate_rubric, parse_report_tables

REPORT = """## Q4 2024

| Metric | USD millions |
|---|---:|
| Automotive sales | 18,659 |
| Total automotive revenue | 19,798 |
| Energy generation and storage | 3,061 |
| Services and other | 2,848 |
| Total revenue | 25,707 |

## FY 2024 source context

| Metric | USD millions |
|---|---:|
| Automotive sales | 72,480 |
| Total revenue | 97,690 |
"""


def test_report_table_parser() -> None:
    facts = parse_report_tables(REPORT)
    assert facts["q4"]["automotive_sales"] == Decimal("18659")
    assert facts["fy"]["total_revenue"] == Decimal("97690")


def test_accepts_coarser_correct_rounding() -> None:
    facts = parse_report_tables(REPORT)
    label, _, comparison = evaluate_rubric(
        "States that Tesla reported total revenue of USD 25.7 billion in Q4 2024.",
        REPORT,
        facts,
    )
    assert label is True
    assert comparison is not None
    assert comparison["rounded_actual_usd_millions"] == "25700.0"


def test_flags_published_q4_automotive_sales_mismatch() -> None:
    facts = parse_report_tables(REPORT)
    label, _, comparison = evaluate_rubric(
        "States that Tesla reported automotive sales revenue of USD 18.83 billion "
        "under the Automotive segment in Q4 2024.",
        REPORT,
        facts,
    )
    assert label is False
    assert comparison is not None
    assert comparison["actual_usd_millions"] == "18659"
    assert comparison["rubric_target_usd_millions"] == "18830.00"
