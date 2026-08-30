#!/usr/bin/env python3
"""Regression tests for schema-capture progress summary."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_save_capture_to_manifest import build_schema_verified_manifest
from prepare_probe_save_handoff import build_handoff as build_save_handoff
from build_probe_save_runbook import build_runbook as build_save_runbook
from summarize_schema_capture_progress import summarize
from test_apply_save_capture_to_manifest import draft_manifest, save_capture, base_run_evidence
from test_schema_capture_handoff import prepare_binding
from build_schema_capture_handoff import build_handoff as build_schema_handoff


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def base_args(root: Path, handoff_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        schema_capture_handoff=str(handoff_path),
        create_evidence=[],
        save_handoff=[],
        save_runbook=[],
        save_capture=[],
        base_run_evidence=[],
        schema_manifest=[],
        output=str(root / "schema-capture-progress.json"),
        fail_on_incomplete=False,
        json=False,
    )


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


def create_evidence() -> dict:
    return {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "editUrl": "https://workspace.laicms.com/demo123/products/fake-product-probe/update",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {"exists": True},
    }


def test_progress_starts_at_create_probe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = prepare_schema_handoff(root)
        report = summarize(base_args(root, handoff_path))
        product = next(item for item in report["results"] if item["contentType"] == "products")
        assert product["status"] == "ready_for_create_probe"
        assert "authorizationRecordCommand" in product


def test_progress_reaches_save_capture_after_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = prepare_schema_handoff(root)
        create_path = Path(write_json(root / "products-create-evidence.json", create_evidence()))
        save_handoff = build_save_handoff(
            create_evidence=create_evidence(),
            create_evidence_path=str(create_path),
            preflight_path="/tmp/products-preflight.json",
            edit_url="https://workspace.laicms.com/demo123/products/fake-product-probe/update",
            authorization_output=str(root / "products-save-authorization.json"),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        save_handoff_path = Path(write_json(root / "products-save-handoff.json", save_handoff))
        save_runbook = build_save_runbook(save_handoff, handoff_path=str(save_handoff_path), generated_at="2026-07-01T00:00:00+00:00")
        save_runbook_path = Path(write_json(root / "products-save-runbook.json", save_runbook))
        args = base_args(root, handoff_path)
        args.create_evidence = [f"products={create_path}"]
        args.save_handoff = [f"products={save_handoff_path}"]
        args.save_runbook = [f"products={save_runbook_path}"]
        report = summarize(args)
        product = next(item for item in report["results"] if item["contentType"] == "products")
        assert product["status"] == "ready_for_save_capture"
        assert product["saveRunbook"] == str(save_runbook_path)


def test_progress_reaches_schema_manifest_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = prepare_schema_handoff(root)
        create_path = Path(write_json(root / "products-create-evidence.json", create_evidence()))
        save_handoff = build_save_handoff(
            create_evidence=create_evidence(),
            create_evidence_path=str(create_path),
            preflight_path="/tmp/products-preflight.json",
            edit_url="https://workspace.laicms.com/demo123/products/fake-product-probe/update",
            authorization_output=str(root / "products-save-authorization.json"),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        save_handoff_path = Path(write_json(root / "products-save-handoff.json", save_handoff))
        save_runbook = build_save_runbook(save_handoff, handoff_path=str(save_handoff_path), generated_at="2026-07-01T00:00:00+00:00")
        save_runbook_path = Path(write_json(root / "products-save-runbook.json", save_runbook))
        capture = save_capture("products")
        capture_path = Path(write_json(root / "products-save-capture.json", capture))
        base_path = Path(write_json(root / "products-base-run-evidence.json", base_run_evidence("products")))
        schema_manifest = build_schema_verified_manifest(
            manifest=draft_manifest("products"),
            capture=capture,
            capture_path=str(capture_path),
            base_run_evidence=base_run_evidence("products"),
            base_run_evidence_path=str(base_path),
        )
        schema_manifest_path = Path(write_json(root / "products-schema-manifest.json", schema_manifest))
        args = base_args(root, handoff_path)
        args.create_evidence = [f"products={create_path}"]
        args.save_handoff = [f"products={save_handoff_path}"]
        args.save_runbook = [f"products={save_runbook_path}"]
        args.save_capture = [f"products={capture_path}"]
        args.base_run_evidence = [f"products={base_path}"]
        args.schema_manifest = [f"products={schema_manifest_path}"]
        report = summarize(args)
        product = next(item for item in report["results"] if item["contentType"] == "products")
        assert product["status"] == "schema_manifest_ready"
        assert product["schemaManifest"] == str(schema_manifest_path)


if __name__ == "__main__":
    test_progress_starts_at_create_probe()
    test_progress_reaches_save_capture_after_runbook()
    test_progress_reaches_schema_manifest_ready()
    print("schema-capture progress regression tests passed.")
