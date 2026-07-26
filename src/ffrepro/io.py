from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_artifacts(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = exclude or set()
    records: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def verify_artifact_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    failures: list[dict[str, Any]] = []
    for record in manifest.get("artifacts", []):
        path = root / record["path"]
        if not path.is_file():
            failures.append({"path": record["path"], "error": "missing"})
            continue
        actual_bytes = path.stat().st_size
        actual_sha256 = sha256_file(path)
        if actual_bytes != record["bytes"] or actual_sha256 != record["sha256"]:
            failures.append(
                {
                    "path": record["path"],
                    "error": "mismatch",
                    "expected_bytes": record["bytes"],
                    "actual_bytes": actual_bytes,
                    "expected_sha256": record["sha256"],
                    "actual_sha256": actual_sha256,
                }
            )
    return {
        "algorithm": manifest.get("algorithm"),
        "checked": len(manifest.get("artifacts", [])),
        "failures": failures,
        "valid": not failures,
    }
