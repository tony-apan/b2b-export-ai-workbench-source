#!/usr/bin/env python3
"""Regression tests for schema save-capture preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_schema_capture_handoff import build_handoff as build_schema_handoff
from prepare_schema_save_capture import build
from test_schema_capture_handoff import prepare_binding
from test_summarize_schema_capture_progress import create_evidence, write_json


def prepare_schema_handoff(root: Path) -> Path:
    binding_path, evidence_path = prepare_binding(root)
    handoff = build_schema_handoff(
        argparse.Namespace(
            created_site_binding=str(binding_path),
            created_site_evidence=str(evidence_path),
            output_dir=str(root / "schema-capture"),
            authorization_dir="",
            output=str(root / "schema-capture-handoff.json"),
            json=False,
        )
    )
    return Path(write_json(root / "schema-capture-handoff.json", handoff))


def test_prepare_schema_save_capture_builds_handoff_runbook_and_progress() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = prepare_schema_handoff(root)
        create_path = Path(write_json(root / "products-create-evidence.json", create_evidence()))
        summary = build(
            argparse.Namespace(
                schema_capture_handoff=str(handoff_path),
                content_type="products",
                create_evidence=str(create_path),
                output_dir=str(root / "save-capture"),
                preflight="",
                edit_url="",
                authorization_output="",
                existing_create_evidence=[],
                existing_save_handoff=[],
                existing_save_runbook=[],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                json=False,
            )
        )
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["contentType"] == "products"
        assert summary["progressStatus"] == "ready_for_save_capture"
        save_handoff = json.loads(Path(summary["artifacts"]["saveHandoff"]).read_text(encoding="utf-8"))
        save_runbook = json.loads(Path(summary["artifacts"]["saveRunbook"]).read_text(encoding="utf-8"))
        progress = json.loads(Path(summary["artifacts"]["schemaCaptureProgress"]).read_text(encoding="utf-8"))
        assert save_handoff["kind"] == "allincms_probe_save_handoff"
        assert save_handoff["isUserAuthorization"] is False
        assert "<paste current user authorization text here>" in save_handoff["authorizationRecordCommand"]
        assert save_runbook["kind"] == "allincms_probe_save_browser_runbook"
        assert save_runbook["browserStepsExecutable"] is False
        products = next(item for item in progress["results"] if item["contentType"] == "products")
        assert products["status"] == "ready_for_save_capture"


if __name__ == "__main__":
    test_prepare_schema_save_capture_builds_handoff_runbook_and_progress()
    print("schema save-capture preparation regression tests passed.")
