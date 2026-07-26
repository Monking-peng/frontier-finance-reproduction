from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from frontier_finance.judges import Judge

_RUBRIC_RE = re.compile(r"(?ms)^(?P<index>\d+)\.\s+(?P<text>.*?)(?=\n\n\d+\.\s+|\Z)")
_AMOUNT_RE = re.compile(r"USD\s+(?P<amount>[\d,.]+)\s+(?P<unit>billion|million)", re.IGNORECASE)


def _extract_tag(prompt: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", prompt, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Judge prompt is missing <{tag}> block")
    return match.group(1)


def _normalize_metric(label: str) -> str | None:
    label = re.sub(r"[^a-z ]", " ", label.lower())
    label = re.sub(r"\s+", " ", label).strip()
    mapping = {
        "automotive sales": "automotive_sales",
        "automotive regulatory credits": "regulatory_credits",
        "automotive leasing": "automotive_leasing",
        "total automotive revenue": "total_automotive",
        "energy generation and storage": "energy",
        "services and other": "services_other",
        "total revenue": "total_revenue",
    }
    return mapping.get(label)


def parse_report_tables(report: str) -> dict[str, dict[str, Decimal]]:
    period: str | None = None
    facts: dict[str, dict[str, Decimal]] = {"q4": {}, "fy": {}}
    for raw_line in report.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if lowered.startswith("## q4 2024"):
            period = "q4"
            continue
        if lowered.startswith("## fy 2024"):
            period = "fy"
            continue
        if period is None or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        metric = _normalize_metric(cells[0])
        if metric is None:
            continue
        number = re.sub(r"[^0-9.\-]", "", cells[1].replace(",", ""))
        if number:
            facts[period][metric] = Decimal(number)
    return facts


def _metric_from_rubric(rubric: str) -> str | None:
    text = rubric.lower()
    if "automotive segment revenue" in text or "total automotive revenue" in text:
        return "total_automotive"
    if "automotive sales revenue" in text:
        return "automotive_sales"
    if "automotive regulatory credits revenue" in text:
        return "regulatory_credits"
    if "automotive leasing revenue" in text:
        return "automotive_leasing"
    if "energy generation and storage" in text:
        return "energy"
    if "services and other" in text:
        return "services_other"
    if "total revenue" in text:
        return "total_revenue"
    return None


def _period_from_rubric(rubric: str) -> str | None:
    text = rubric.lower()
    if "q4 2024" in text:
        return "q4"
    if "full year 2024" in text or "full-year 2024" in text:
        return "fy"
    return None


def _target_millions(match: re.Match[str]) -> tuple[Decimal, Decimal]:
    amount_text = match.group("amount").replace(",", "")
    amount = Decimal(amount_text)
    decimals = len(amount_text.partition(".")[2])
    multiplier = Decimal(1000) if match.group("unit").lower() == "billion" else Decimal(1)
    target = amount * multiplier
    step = multiplier * (Decimal(10) ** -decimals)
    return target, step


def evaluate_rubric(
    rubric: str, report: str, facts: dict[str, dict[str, Decimal]]
) -> tuple[bool, str, dict[str, Any] | None]:
    lowered = rubric.lower()
    if "table format" in lowered:
        passed = report.count("| Metric | USD millions |") >= 2
        reason = (
            "The response contains separate Q4 and FY revenue tables."
            if passed
            else ("The response does not contain both expected Markdown revenue tables.")
        )
        return passed, reason, None

    if "most recent quarter" in lowered and "ending on december 31, 2024" in lowered:
        passed = "Q4 2024" in report and "December 31, 2024" in report
        reason = (
            "The response identifies Q4 2024 and the December 31, 2024 period end."
            if passed
            else ("The response does not state the expected quarter and period end.")
        )
        return passed, reason, None

    amount_match = _AMOUNT_RE.search(rubric)
    metric = _metric_from_rubric(rubric)
    period = _period_from_rubric(rubric)
    if not amount_match or not metric or not period:
        return False, "The deterministic demo auditor cannot map this rubric.", None

    actual = facts.get(period, {}).get(metric)
    target, step = _target_millions(amount_match)
    if actual is None:
        return False, f"The response table has no {period}/{metric} value.", None
    rounded_actual = (actual / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step
    passed = rounded_actual == target
    reason = (
        f"Source-derived response value {actual} USDm rounds to {rounded_actual} USDm "
        f"at the rubric precision; target is {target} USDm."
    )
    comparison = {
        "period": period,
        "metric": metric,
        "actual_usd_millions": str(actual),
        "rubric_target_usd_millions": str(target),
        "rubric_precision_step_usd_millions": str(step),
        "rounded_actual_usd_millions": str(rounded_actual),
        "match": passed,
    }
    return passed, reason, comparison


class DeterministicAuditJudge(Judge):
    """Transparent, demo-only rubric checker.

    This is intentionally not represented as an LLM judge and its output is not
    comparable to Samaya's official three-model panel. It exists so the no-key
    path still executes the official batching, voting, and metric code.
    """

    def __init__(self) -> None:
        super().__init__(
            "deterministic-audit-v1",
            max_tokens=0,
            timeout=0,
            max_retries=0,
        )
        self.records: list[dict[str, Any]] = []

    def complete(self, system: str, user: str) -> str:  # noqa: ARG002
        report = _extract_tag(user, "report")
        rubric_block = _extract_tag(user, "rubrics")
        facts = parse_report_tables(report)
        judgements: dict[str, dict[str, Any]] = {}
        for match in _RUBRIC_RE.finditer(rubric_block):
            index = match.group("index")
            rubric = match.group("text").strip()
            label, reason, comparison = evaluate_rubric(rubric, report, facts)
            judgements[index] = {"reason": reason, "label": label}
            self.records.append(
                {
                    "batch_index": int(index),
                    "rubric_text": rubric,
                    "label": label,
                    "reason": reason,
                    "comparison": comparison,
                }
            )
        return json.dumps(judgements, ensure_ascii=False)
