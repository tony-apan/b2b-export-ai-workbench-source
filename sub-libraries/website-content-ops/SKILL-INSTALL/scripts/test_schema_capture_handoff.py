#!/usr/bin/env python3
"""Regression tests for created-site to schema-capture handoff."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from bind_created_site_to_artifacts import build_binding
from build_schema_capture_handoff import build_handoff, validate_handoff
from export_confirmed_site_artifacts import build_artifacts
from merge_content_type_preflight import merge_content_preflight
from test_bind_created_site_to_artifacts import created_site_evidence
from test_export_confirmed_site_artifacts import prepare_confirmed_plan
from test_validate_run_evidence import existing_site_selected_evidence
from test_merge_content_type_preflight import retarget_refresh_to_created_site


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_binding(root: Path) -> tuple[Path, Path]:
    package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
    readiness = build_artifacts(
        argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            execution_plan=str(plan_path),
            site_key="",
            frontend_base_url="",
            output_dir=str(root / "artifacts"),
            json=False,
        )
    )
    readiness_path = root / "artifacts" / "artifact-readiness.json"
    write_json(readiness_path, readiness)
    evidence_path = created_site_evidence(root)
    binding = build_binding(
        argparse.Namespace(
            artifact_readiness=str(readiness_path),
            created_site_evidence=str(evidence_path),
            output_dir=str(root / "bound-artifacts"),
            output=str(root / "created-site-artifact-binding.json"),
            json=False,
        )
    )
    binding_path = root / "created-site-artifact-binding.json"
    write_json(binding_path, binding)
    return binding_path, evidence_path


def test_schema_capture_handoff_products_ready_posts_need_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        handoff = build_handoff(
            argparse.Namespace(
                created_site_binding=str(binding_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "schema-capture"),
                authorization_dir="",
                output=str(root / "schema-capture-handoff.json"),
                json=False,
            )
        )
        assert not validate_handoff(handoff)
        stages = {stage["contentType"]: stage for stage in handoff["stages"]}
        assert stages["products"]["status"] == "ready_for_create_probe_authorization"
        assert stages["posts"]["status"] == "needs_readonly_content_preflight"
        assert "create_product_probe" in stages["products"]["createProbe"]["authorizationRecordCommand"]
        assert "apply_save_capture_to_manifest.py" in stages["products"]["afterSaveCapture"]["applySaveCaptureCommand"]
        assert handoff["remoteMutationsPerformed"] is False
        assert handoff["contentQualityReview"]["warnings"] == []
        assert handoff["contentQualityReview"]["reviewRequired"] is False
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        assert handoff["wikiReview"] == binding["wikiReview"]
        assert handoff["confirmationDecisionMatrix"] == binding["confirmationDecisionMatrix"]
        assert handoff["createdSiteSubmittedValues"] == binding["createdSiteSubmittedValues"]
        assert Path(handoff["wikiReview"]["sourceWikiMarkdownIndex"]).exists()


def test_schema_capture_handoff_skips_empty_posts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        posts_manifest_path = Path(binding["boundArtifacts"]["postsManifest"])
        posts_manifest = json.loads(posts_manifest_path.read_text(encoding="utf-8"))
        posts_manifest["items"] = []
        write_json(posts_manifest_path, posts_manifest)
        handoff = build_handoff(
            argparse.Namespace(
                created_site_binding=str(binding_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "schema-capture"),
                authorization_dir="",
                output=str(root / "schema-capture-handoff.json"),
                json=False,
            )
        )
        stages = {stage["contentType"]: stage for stage in handoff["stages"]}
        assert stages["posts"]["status"] == "skipped_no_manifest_items"
        assert handoff["skippedCount"] == 1


def test_schema_capture_handoff_uses_merged_posts_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        created = json.loads(evidence_path.read_text(encoding="utf-8"))
        refresh = existing_site_selected_evidence()
        retarget_refresh_to_created_site(refresh, created)
        refresh["contentInspection"] = {
            "contentType": "posts",
            "listColumns": ["标题", "Slug", "摘要", "状态"],
            "editFields": ["标题", "Slug", "摘要", "正文编辑器", "更新", "发布"],
        }
        refresh_path = root / "posts-readonly-refresh.json"
        write_json(refresh_path, refresh)
        merged_path = root / "created-site-with-posts-preflight.json"
        merged = merge_content_preflight(
            created,
            refresh,
            refresh_path=refresh_path,
            content_type="posts",
            output_path=merged_path,
        )
        write_json(merged_path, merged)
        handoff = build_handoff(
            argparse.Namespace(
                created_site_binding=str(binding_path),
                created_site_evidence=str(merged_path),
                output_dir=str(root / "schema-capture"),
                authorization_dir="",
                output=str(root / "schema-capture-handoff.json"),
                json=False,
            )
        )
        stages = {stage["contentType"]: stage for stage in handoff["stages"]}
        assert stages["posts"]["status"] == "ready_for_create_probe_authorization"
        assert str(merged_path) in stages["posts"]["createProbe"]["preMutationGateCommand"]
        assert stages["posts"]["contentPreflight"]["fromContentTypePreflights"] is True


def test_schema_capture_handoff_preserves_content_quality_warning_from_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        warning_quality = {
            "readyShape": False,
            "warnings": ["posts_present_without_post_categories"],
            "reviewRequired": True,
            "contentCounts": {"pages": 1, "products": 1, "posts": 1},
        }
        binding["contentQualityReview"] = warning_quality
        bound_readiness = Path(binding["boundArtifacts"]["artifactReadiness"])
        readiness = json.loads(bound_readiness.read_text(encoding="utf-8"))
        readiness["contentQualityReview"] = warning_quality
        write_json(bound_readiness, readiness)
        write_json(binding_path, binding)
        handoff = build_handoff(
            argparse.Namespace(
                created_site_binding=str(binding_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "schema-capture"),
                authorization_dir="",
                output=str(root / "schema-capture-handoff.json"),
                json=False,
            )
        )
        assert not validate_handoff(handoff)
        assert handoff["contentQualityReview"] == warning_quality
        assert "posts_present_without_post_categories" in handoff["contentQualityReview"]["warnings"]


def test_schema_capture_handoff_rejects_missing_wiki_index() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        Path(binding["wikiReview"]["sourceWikiMarkdownIndex"]).unlink()
        write_json(binding_path, binding)
        try:
            build_handoff(
                argparse.Namespace(
                    created_site_binding=str(binding_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "schema-capture"),
                    authorization_dir="",
                    output=str(root / "schema-capture-handoff.json"),
                    json=False,
                )
            )
        except ValueError as exc:
            assert "wikiReview" in str(exc)
        else:
            raise AssertionError("missing readable wiki index should block schema-capture handoff")


def test_schema_capture_handoff_rejects_schema_verified_draft() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binding_path, evidence_path = prepare_binding(root)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        products_manifest_path = Path(binding["boundArtifacts"]["productsManifest"])
        products_manifest = json.loads(products_manifest_path.read_text(encoding="utf-8"))
        products_manifest["schemaVerified"] = True
        products_manifest["fieldMapping"] = {"nameField": "name"}
        products_manifest["payloadTemplate"] = {"mode": "update"}
        write_json(products_manifest_path, products_manifest)
        try:
            build_handoff(
                argparse.Namespace(
                    created_site_binding=str(binding_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "schema-capture"),
                    authorization_dir="",
                    output=str(root / "schema-capture-handoff.json"),
                    json=False,
                )
            )
        except ValueError as exc:
            assert "schemaVerified=false" in str(exc)
        else:
            raise AssertionError("expected schemaVerified draft rejection")


if __name__ == "__main__":
    test_schema_capture_handoff_products_ready_posts_need_preflight()
    test_schema_capture_handoff_skips_empty_posts()
    test_schema_capture_handoff_uses_merged_posts_preflight()
    test_schema_capture_handoff_preserves_content_quality_warning_from_binding()
    test_schema_capture_handoff_rejects_missing_wiki_index()
    test_schema_capture_handoff_rejects_schema_verified_draft()
    print("schema capture handoff regression tests passed.")
