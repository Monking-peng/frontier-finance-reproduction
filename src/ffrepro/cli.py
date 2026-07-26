from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ffrepro.bundles import verify_official_bundles
from ffrepro.dataset import inspect_dataset
from ffrepro.io import verify_artifact_manifest
from ffrepro.pipeline import run_demo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ffrepro",
        description="Auditable FrontierFinance reproduction harness.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the SEC-only TSLA end-to-end demo.")
    demo.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (normally auto-detected).",
    )
    demo.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory that receives a timestamped run (default: <repo>/runs).",
    )
    demo.add_argument(
        "--offline-source-dir",
        type=Path,
        help="Reuse tsla-2024-10k.htm and tsla-2024-q3-10q.htm from a prior run.",
    )

    dataset = subparsers.add_parser(
        "dataset-verify", help="Inspect a FrontierFinance JSONL file and verify its hash."
    )
    dataset.add_argument("path", type=Path)

    bundles = subparsers.add_parser(
        "bundle-verify", help="Cross-check official website bundles against the dataset."
    )
    bundles.add_argument("--dataset", required=True, type=Path)
    bundles.add_argument("--performance", required=True, type=Path)
    bundles.add_argument("--breakdowns", required=True, type=Path)

    artifacts = subparsers.add_parser(
        "artifact-verify", help="Recompute every SHA-256 entry in a run manifest."
    )
    artifacts.add_argument("run_dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "demo":
            repo_root = args.repo_root.resolve()
            output_root = (args.output_root or repo_root / "runs").resolve()
            run_dir = run_demo(
                repo_root=repo_root,
                output_root=output_root,
                offline_source_dir=(
                    args.offline_source_dir.resolve() if args.offline_source_dir else None
                ),
            )
            metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            print(f"run_dir={run_dir}")
            print(
                "demo_qualification_rate="
                f"{metrics['macro_avg_qualification_rate_on_all_queries']:.4f}"
            )
            print("officially_comparable=false")
            return 0
        if args.command == "dataset-verify":
            print(json.dumps(inspect_dataset(args.path.resolve()), indent=2, ensure_ascii=False))
            return 0
        if args.command == "bundle-verify":
            report = verify_official_bundles(
                dataset_path=args.dataset.resolve(),
                performance_path=args.performance.resolve(),
                breakdowns_path=args.breakdowns.resolve(),
            )
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        if args.command == "artifact-verify":
            run_dir = args.run_dir.resolve()
            report = verify_artifact_manifest(run_dir, run_dir / "artifact_hashes.json")
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["valid"] else 1
    except Exception as error:
        print(f"ffrepro failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
