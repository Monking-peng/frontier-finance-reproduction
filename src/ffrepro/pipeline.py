from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from frontier_finance.grading import Grader
from frontier_finance.metrics import MetricsReport
from frontier_finance.models import EvalItem, Rubric

from ffrepro import __version__
from ffrepro.audit import DeterministicAuditJudge
from ffrepro.io import hash_artifacts, read_json, sha256_file, write_json
from ffrepro.trace import TraceRecorder, utc_now
from ffrepro.xbrl import InlineXbrlDocument

OFFICIAL_GRADER_COMMIT = "7d2d9c2a54816e94fb9e2e6a1cb033cc9dfcb589"
FINANCE_AGENT_COMMIT = "e2a0446969a9b77c7613012744c15affe14a88d0"
DATASET_COMMIT = "21da0514a15c51774ff836c46f290681c0ad91ee"
REVENUE_CONCEPT = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
MEMBERS = {
    "automotive_sales": "AutomotiveSalesMember",
    "regulatory_credits": "AutomotiveRegulatoryCreditsMember",
    "automotive_leasing": "AutomotiveLeasingMember",
    "total_automotive": "AutomotiveRevenuesMember",
    "energy": "EnergyGenerationAndStorageMember",
    "services_other": "ServicesAndOtherMember",
    "total_revenue": None,
}
LABELS = {
    "automotive_sales": "Automotive sales",
    "regulatory_credits": "Automotive regulatory credits",
    "automotive_leasing": "Automotive leasing",
    "total_automotive": "Total automotive revenue",
    "energy": "Energy generation and storage",
    "services_other": "Services and other",
    "total_revenue": "Total revenue",
}


def _git_state(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        return completed.stdout.strip() if completed.returncode == 0 else "unavailable"

    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "status_porcelain": run("status", "--short"),
    }


def _download(url: str, destination: Path) -> tuple[int, int]:
    user_agent = os.environ.get("SEC_USER_AGENT", "frontier-finance-repro/0.1 contact@example.com")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "identity",
        },
    )
    # A direct connection avoids accidental SDK/tool failures caused by a
    # machine-wide SOCKS proxy. Users can pre-populate --offline-source-dir when
    # their network requires an authenticated proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=90) as response:
        content = response.read()
        status = getattr(response, "status", 200)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return status, len(content)


def _materialize_sources(
    *,
    source_specs: list[dict[str, Any]],
    query_date: str,
    source_dir: Path,
    trace: TraceRecorder,
    offline_source_dir: Path | None,
) -> list[dict[str, Any]]:
    query_day = date.fromisoformat(query_date)
    records: list[dict[str, Any]] = []
    for spec in source_specs:
        filed = date.fromisoformat(spec["filed"])
        if filed > query_day:
            raise ValueError(
                f"Source {spec['id']} was filed after the query date: {filed} > {query_day}"
            )
        destination = source_dir / f"{spec['id']}.htm"
        started = utc_now()
        trace.record(
            "tool_call_started",
            tool="sec_filing_fetch",
            source_id=spec["id"],
            url=spec["url"],
            offline=offline_source_dir is not None,
        )
        if offline_source_dir:
            cached = offline_source_dir / destination.name
            if not cached.exists():
                raise FileNotFoundError(f"Offline source is missing: {cached}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached, destination)
            status, byte_count = 0, destination.stat().st_size
        else:
            status, byte_count = _download(spec["url"], destination)
        record = {
            **spec,
            "fetched_at": utc_now(),
            "fetch_started_at": started,
            "http_status": status,
            "bytes": byte_count,
            "sha256": sha256_file(destination),
            "local_path": destination.name,
            "cutoff_check": "pass",
        }
        records.append(record)
        trace.record(
            "tool_call_completed",
            tool="sec_filing_fetch",
            source_id=spec["id"],
            http_status=status,
            bytes=byte_count,
            sha256=record["sha256"],
        )
    return records


def _extract_period(
    document: InlineXbrlDocument, *, start_date: str, end_date: str
) -> dict[str, Decimal]:
    return {
        metric: document.usd_millions(
            concept=REVENUE_CONCEPT,
            start_date=start_date,
            end_date=end_date,
            member_suffix=member,
        )
        for metric, member in MEMBERS.items()
    }


def _validate_revenue(period: str, facts: dict[str, Decimal]) -> None:
    auto_sum = facts["automotive_sales"] + facts["regulatory_credits"] + facts["automotive_leasing"]
    if auto_sum != facts["total_automotive"]:
        raise ValueError(
            f"{period} automotive reconciliation failed: {auto_sum} != {facts['total_automotive']}"
        )
    total_sum = facts["total_automotive"] + facts["energy"] + facts["services_other"]
    if total_sum != facts["total_revenue"]:
        raise ValueError(
            f"{period} total revenue reconciliation failed: {total_sum} != {facts['total_revenue']}"
        )


def extract_revenue_facts(source_dir: Path) -> dict[str, dict[str, Decimal]]:
    annual_doc = InlineXbrlDocument.from_path(source_dir / "tsla-2024-10k.htm")
    nine_month_doc = InlineXbrlDocument.from_path(source_dir / "tsla-2024-q3-10q.htm")
    annual = _extract_period(annual_doc, start_date="2024-01-01", end_date="2024-12-31")
    nine_month = _extract_period(nine_month_doc, start_date="2024-01-01", end_date="2024-09-30")
    q4 = {metric: annual[metric] - nine_month[metric] for metric in MEMBERS}
    _validate_revenue("FY 2024", annual)
    _validate_revenue("9M 2024", nine_month)
    _validate_revenue("Q4 2024", q4)
    return {"q4": q4, "fy": annual, "nine_month": nine_month}


def _plain_facts(facts: dict[str, dict[str, Decimal]]) -> dict[str, dict[str, str]]:
    return {
        period: {metric: str(value) for metric, value in values.items()}
        for period, values in facts.items()
    }


def _table(values: dict[str, Decimal]) -> str:
    rows = ["| Metric | USD millions |", "|---|---:|"]
    for metric in MEMBERS:
        rows.append(f"| {LABELS[metric]} | {values[metric]:,.0f} |")
    return "\n".join(rows)


def render_response(facts: dict[str, dict[str, Decimal]], sources: list[dict[str, Any]]) -> str:
    source_links = "\n".join(
        f"{index}. [{source['form']} filed {source['filed']}]({source['url']})"
        for index, source in enumerate(sources, start=1)
    )
    return f"""# Tesla revenue breakdown

As of the query date (February 4, 2025), Tesla's most recent reported quarter was
**Q4 2024, ending December 31, 2024**. Values below are USD millions.

## Q4 2024

{_table(facts["q4"])}

The Q4 figures are derived mechanically as FY 2024 less the first nine months of
2024. Both source statements reconcile: automotive sales + regulatory credits +
leasing = total automotive revenue, and total automotive + energy + services =
total revenue.

## FY 2024 source context

{_table(facts["fy"])}

## Sources

{source_links}
"""


def _load_item(fixture: Path, response: str) -> tuple[EvalItem, dict[str, Any]]:
    raw = json.loads(fixture.read_text(encoding="utf-8").strip())
    rubrics = [Rubric.from_dict(row) for row in raw["rubrics"]]
    item = EvalItem(
        query_id=raw["query_id"],
        query=raw["query"],
        query_date=raw["query_date"],
        rubrics=rubrics,
        system_response=response,
    )
    return item, raw


def _per_item(result: Any, judge_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audit_by_index = {record["batch_index"]: record for record in judge_records}
    return [
        {
            "query_id": result.query_id,
            "failed": result.failed,
            "failure_reason": result.failure_reason,
            "failed_checks_by_judge": result.failed_checks_by_judge,
            "num_rubrics": result.num_rubrics,
            "num_qualified": result.num_qualified,
            "judgements": [
                {
                    "rubric_id": rubric.rubric_id,
                    "must_have": rubric.must_have,
                    "rubric_type": rubric.rubric_type,
                    "data_source_type": rubric.data_source_type,
                    "qualified": label,
                    "audit_reason": audit_by_index[index]["reason"],
                    "comparison": audit_by_index[index]["comparison"],
                }
                for index, (rubric, label) in enumerate(
                    zip(result.rubrics, result.labels, strict=True)
                )
            ],
        }
    ]


def _findings(result: Any, judge_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rubric, label, record in zip(result.rubrics, result.labels, judge_records, strict=True):
        if label or not record["comparison"]:
            continue
        comparison = record["comparison"]
        findings.append(
            {
                "finding_id": f"rubric-reference-{rubric.rubric_id}",
                "category": "scoring_anomaly",
                "status": "confirmed_in_demo_sources",
                "rubric_id": rubric.rubric_id,
                "rubric_text": rubric.rubric_text,
                "source_derived_value_usd_millions": comparison["actual_usd_millions"],
                "rubric_target_usd_millions": comparison["rubric_target_usd_millions"],
                "explanation": record["reason"],
                "score_treatment": "failed under the published rubric; not silently corrected",
            }
        )
    return findings


def _failure_category(error: Exception) -> str:
    if isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return "environment_anomaly"
    if isinstance(error, (LookupError, ValueError)):
        return "agent_failure"
    if isinstance(error, OSError):
        return "environment_anomaly"
    return "unclassified_failure"


def run_demo(
    *,
    repo_root: Path,
    output_root: Path,
    offline_source_dir: Path | None = None,
) -> Path:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-tsla-q4-2024")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    trace = TraceRecorder(run_dir / "trace.jsonl")
    trace.record("run_started", run_id=run_id, scoring_mode="deterministic_audit")

    config_path = repo_root / "configs" / "demo.tsla-q4-2024.json"
    fixture_path = repo_root / "data" / "demo" / "frontier_finance_tsla_q4_2024.jsonl"
    config = read_json(config_path)
    source_dir = run_dir / "sources"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "project_version": __version__,
        "command": " ".join(sys.argv),
        "query_id": config["query_id"],
        "query_date": config["query_date"],
        "scoring": {
            "mode": "deterministic-audit-v1",
            "official_panel_run": False,
            "officially_comparable": False,
            "note": (
                "The official Grader/Grader majority-vote and MetricsReport code run, "
                "but the judge is a transparent deterministic checker because no provider "
                "API keys were present."
            ),
        },
        "upstreams": {
            "official_grader_commit": OFFICIAL_GRADER_COMMIT,
            "finance_agent_v2_commit": FINANCE_AGENT_COMMIT,
            "dataset_commit": DATASET_COMMIT,
        },
        "inputs": {
            "config": {
                "path": config_path.relative_to(repo_root).as_posix(),
                "sha256": sha256_file(config_path),
            },
            "rubric_fixture": {
                "path": fixture_path.relative_to(repo_root).as_posix(),
                "sha256": sha256_file(fixture_path),
            },
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "api_keys_present": {
                name: bool(os.environ.get(name))
                for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
            },
        },
        "git": _git_state(repo_root),
    }
    write_json(run_dir / "run_manifest.json", manifest)
    (run_dir / "command.txt").write_text(manifest["command"] + "\n", encoding="utf-8")

    try:
        sources = _materialize_sources(
            source_specs=config["sources"],
            query_date=config["query_date"],
            source_dir=source_dir,
            trace=trace,
            offline_source_dir=offline_source_dir,
        )
        write_json(run_dir / "source_manifest.json", sources)

        trace.record("agent_step_started", step="parse_and_derive_xbrl_revenue")
        facts = extract_revenue_facts(source_dir)
        trace.record(
            "agent_step_completed",
            step="parse_and_derive_xbrl_revenue",
            reconciliation="pass",
        )
        write_json(run_dir / "facts.json", _plain_facts(facts))
        write_json(
            run_dir / "calculations.json",
            {
                "formula": "Q4 2024 = FY 2024 - nine months ended 2024-09-30",
                "unit": "USD millions",
                "calculations": [
                    {
                        "metric": metric,
                        "fy_2024": str(facts["fy"][metric]),
                        "nine_month_2024": str(facts["nine_month"][metric]),
                        "q4_2024": str(facts["q4"][metric]),
                    }
                    for metric in MEMBERS
                ],
                "reconciliations": [
                    "automotive components equal total automotive revenue",
                    "total automotive + energy + services equal total revenue",
                ],
            },
        )

        response = render_response(facts, sources)
        (run_dir / "answer.md").write_text(response, encoding="utf-8")
        item, raw_item = _load_item(fixture_path, response)
        write_json(
            run_dir / "system_summaries.json",
            [{"query_id": item.query_id, "system_summary": response}],
        )

        trace.record(
            "scoring_started",
            grader="samaya-ai/frontier-finance.Grader",
            judge="deterministic-audit-v1",
        )
        judge = DeterministicAuditJudge()
        grader = Grader([judge], max_rubrics_per_call=30, max_json_parse_retries=1)
        result = grader.grade(item)
        metrics = MetricsReport([result]).compute()
        trace.record(
            "scoring_completed",
            num_rubrics=result.num_rubrics,
            num_qualified=result.num_qualified,
        )
        per_item = _per_item(result, judge.records)
        findings = _findings(result, judge.records)
        write_json(run_dir / "metrics.json", metrics)
        write_json(run_dir / "per_item.json", per_item)
        write_json(run_dir / "rubric_audit.json", findings)

        manifest.update(
            {
                "status": "completed_with_findings" if findings else "completed",
                "completed_at": utc_now(),
                "source_manifest": "source_manifest.json",
                "outputs": {
                    "answer": "answer.md",
                    "responses": "system_summaries.json",
                    "metrics": "metrics.json",
                    "per_item": "per_item.json",
                    "trace": "trace.jsonl",
                    "rubric_audit": "rubric_audit.json",
                },
                "result": {
                    "qualified": result.num_qualified,
                    "rubrics": result.num_rubrics,
                    "qualification_rate": metrics["macro_avg_qualification_rate_on_all_queries"],
                    "must_have_rate": metrics[
                        "macro_avg_qualification_rate_must_have_on_all_queries"
                    ],
                    "confirmed_scoring_anomalies": len(findings),
                    "query": raw_item["query"],
                },
            }
        )
        write_json(run_dir / "run_manifest.json", manifest)
        trace.record("run_completed", status=manifest["status"])
    except Exception as error:
        category = _failure_category(error)
        failure = {
            "timestamp": utc_now(),
            "category": category,
            "exception_type": type(error).__name__,
            "message": str(error),
        }
        write_json(run_dir / "failure.json", failure)
        manifest.update({"status": "failed", "completed_at": utc_now(), "failure": failure})
        write_json(run_dir / "run_manifest.json", manifest)
        trace.record("run_failed", **failure)
        raise
    finally:
        write_json(
            run_dir / "artifact_hashes.json",
            {
                "algorithm": "sha256",
                "generated_at": utc_now(),
                "artifacts": hash_artifacts(run_dir, exclude={"artifact_hashes.json"}),
            },
        )
    return run_dir
