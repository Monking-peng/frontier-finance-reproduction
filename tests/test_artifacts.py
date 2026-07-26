from pathlib import Path

from ffrepro.io import hash_artifacts, verify_artifact_manifest, write_json


def test_artifact_manifest_detects_changes(tmp_path: Path) -> None:
    artifact = tmp_path / "answer.txt"
    artifact.write_text("original", encoding="utf-8")
    manifest = tmp_path / "artifact_hashes.json"
    write_json(
        manifest,
        {"algorithm": "sha256", "artifacts": hash_artifacts(tmp_path)},
    )
    assert verify_artifact_manifest(tmp_path, manifest)["valid"] is True
    artifact.write_text("changed", encoding="utf-8")
    report = verify_artifact_manifest(tmp_path, manifest)
    assert report["valid"] is False
    assert report["failures"][0]["path"] == "answer.txt"
