#!/usr/bin/env python3
"""Regression tests for manifest sample evidence bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from build_manifest_sample_upload_runbook import build_runbook
from prepare_manifest_sample_evidence_bundle import build_bundle, validate_bundle
from test_manifest_sample_upload import (
    content_goal_overages,
    created_site_submitted_values,
    overage_quality,
    schema_manifest,
    wiki_review,
)
from test_summarize_source_execution_status import content_goal_coverage
from test_apply_save_capture_to_manifest import confirmation_decision_matrix


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def sample_runbook(root: Path) -> tuple[dict, str]:
    manifest = schema_manifest()
    manifest_path = write_json(root / "products-schema-verified-manifest.json", manifest)
    runbook = build_runbook(
        manifest=manifest,
        manifest_path=manifest_path,
        target="https://workspace.laicms.com/demo123/products",
        authorization_output=str(root / "sample-authorization.json"),
    )
    runbook_path = write_json(root / "products-manifest-sample-runbook.json", runbook)
    return runbook, runbook_path


def source_context_sample_runbook(root: Path) -> tuple[dict, str, dict]:
    manifest = schema_manifest()
    manifest["contentGoalCoverage"] = content_goal_coverage()
    manifest["contentQualityReview"] = overage_quality()
    manifest["contentGoalOverages"] = content_goal_overages()
    manifest["wikiReview"] = wiki_review()
    manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
    manifest_path = write_json(root / "products-schema-verified-manifest.json", manifest)
    runbook = build_runbook(
        manifest=manifest,
        manifest_path=manifest_path,
        target="https://workspace.laicms.com/demo123/products",
        authorization_output=str(root / "sample-authorization.json"),
    )
    runbook_path = write_json(root / "products-manifest-sample-runbook.json", runbook)
    return runbook, runbook_path, manifest


def test_manifest_sample_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path = sample_runbook(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            output_dir=root / "sample-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["browserStepsExecutable"] is False
        assert bundle["manifest"] == runbook["manifest"]
        assert bundle["sampleSlug"] == runbook["sampleSlug"]
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidencePath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_manifest_sample_upload_evidence"
        assert template["sampleSlug"] == runbook["sampleSlug"]
        assert template["schemaGatePass"] is False
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert "validate_manifest_sample_upload_evidence.py" in Path(bundle["validationCommand"]).read_text(encoding="utf-8")
        assert "apply_manifest_sample_upload.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")


def test_manifest_sample_evidence_bundle_preserves_source_context_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, manifest = source_context_sample_runbook(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            output_dir=root / "sample-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert bundle[key] == manifest[key]
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert template[key] == manifest[key]

        drifted = json.loads(json.dumps(bundle))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_bundle(drifted)
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues


def test_manifest_sample_evidence_bundle_rejects_mutating_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path = sample_runbook(root)
        runbook["remoteMutationsPerformed"] = True
        try:
            build_bundle(
                runbook=runbook,
                runbook_path=runbook_path,
                output_dir=root / "bundle",
            )
        except ValueError as exc:
            assert "local-only/no remote mutation" in str(exc)
        else:
            raise AssertionError("bundle should reject a mutating runbook")


if __name__ == "__main__":
    test_manifest_sample_evidence_bundle_builds()
    test_manifest_sample_evidence_bundle_preserves_source_context_when_present()
    test_manifest_sample_evidence_bundle_rejects_mutating_runbook()
    print("manifest sample evidence bundle regression tests passed.")
