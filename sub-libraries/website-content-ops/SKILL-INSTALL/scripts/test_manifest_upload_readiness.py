#!/usr/bin/env python3
"""Regression tests for manifest upload readiness taxonomy gates."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from make_manifest_upload_readiness import build_report
from test_manifest_sample_upload import schema_manifest


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def taxonomy_validation() -> dict:
    return {
        "kind": "allincms_taxonomy_execution_evidence_validation",
        "valid": True,
        "siteKey": "demo123",
        "taxonomyPrerequisiteSatisfied": True,
        "issues": [],
    }


def test_readiness_passes_without_taxonomy_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest_path = Path(write_json(root / "manifest.json", schema_manifest()))
        report = build_report([manifest_path])
        assert report["overallStatus"] == "ready_for_sample_upload", report
        assert report["manifests"][0]["taxonomyRequired"] is False
        assert report["manifests"][0]["taxonomyGate"]["ok"] is True


def test_readiness_blocks_taxonomy_fields_without_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["tags"] = ["example-tag"]
        manifest_path = Path(write_json(root / "manifest.json", manifest))
        report = build_report([manifest_path])
        assert report["overallStatus"] == "blocked", report
        assert report["manifests"][0]["taxonomyRequired"] is True
        assert "taxonomy_gate_not_passed" in report["manifests"][0]["blockers"]


def test_readiness_accepts_valid_taxonomy_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["categoryIds"] = ["redacted-category-id"]
        manifest_path = Path(write_json(root / "manifest.json", manifest))
        report = build_report([manifest_path], taxonomy_validation())
        assert report["overallStatus"] == "ready_for_sample_upload", report
        assert report["manifests"][0]["taxonomyGate"]["ok"] is True


if __name__ == "__main__":
    test_readiness_passes_without_taxonomy_fields()
    test_readiness_blocks_taxonomy_fields_without_validation()
    test_readiness_accepts_valid_taxonomy_validation()
    print("manifest upload readiness regression tests passed.")
