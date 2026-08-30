#!/usr/bin/env python3
"""Regression tests for batch upload/publish evidence bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from build_batch_upload_publish_runbook import build_runbook
from prepare_batch_upload_publish_evidence_bundle import build_bundle, validate_bundle
from test_manifest_sample_upload import (
    base_run_evidence,
    content_goal_overages,
    content_counts,
    created_site_submitted_values,
    overage_quality,
    sample_evidence,
    schema_manifest,
    warning_quality,
)
from test_summarize_source_execution_status import content_goal_coverage, confirmation_decision_matrix, wiki_review


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def batch_runbook(root: Path) -> tuple[dict, str]:
    run_evidence = base_run_evidence()
    manifest = schema_manifest()
    sample = sample_evidence()
    run_evidence_path = write_json(root / "run-evidence.json", run_evidence)
    manifest_path = write_json(root / "manifest.json", manifest)
    sample_path = write_json(root / "sample-evidence.json", sample)
    runbook = build_runbook(
        run_evidence=run_evidence,
        run_evidence_path=run_evidence_path,
        manifest=manifest,
        manifest_path=manifest_path,
        sample_evidence=sample,
        sample_evidence_path=sample_path,
        authorization_output=str(root / "batch-authorization.json"),
        target="https://workspace.laicms.com/demo123/products",
        target_identifier="products manifest batch",
    )
    runbook_path = write_json(root / "batch-runbook.json", runbook)
    return runbook, runbook_path


def source_context_batch_runbook(root: Path) -> tuple[dict, str, dict]:
    context = {
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "wikiReview": wiki_review(root),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
    }
    run_evidence = {**base_run_evidence(), **context}
    manifest = {**schema_manifest(), **context}
    sample = {**sample_evidence(), **context}
    run_evidence_path = write_json(root / "run-evidence.json", run_evidence)
    manifest_path = write_json(root / "manifest.json", manifest)
    sample_path = write_json(root / "sample-evidence.json", sample)
    runbook = build_runbook(
        run_evidence=run_evidence,
        run_evidence_path=run_evidence_path,
        manifest=manifest,
        manifest_path=manifest_path,
        sample_evidence=sample,
        sample_evidence_path=sample_path,
        authorization_output=str(root / "batch-authorization.json"),
        target="https://workspace.laicms.com/demo123/products",
        target_identifier="products manifest batch",
    )
    runbook_path = write_json(root / "batch-runbook.json", runbook)
    return runbook, runbook_path, context


def test_batch_upload_publish_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path = batch_runbook(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            output_dir=root / "batch-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["browserStepsExecutable"] is False
        assert bundle["manifest"] == runbook["sourceManifest"]
        assert bundle["sourceSampleEvidence"] == runbook["sourceSampleEvidence"]
        assert bundle["manifestItemCount"] == runbook["manifestItemCount"]
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidencePath"]).exists()
        assert Path(bundle["progressLogPath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["finalAuditInputsCommand"]).exists()
        assert Path(bundle["frontendAuditCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_batch_upload_publish_evidence"
        assert template["progressLogComplete"] is False
        assert template["frontendDetailAudit"]["detailRouteCount"] == runbook["manifestItemCount"]
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert "validate_batch_upload_publish_evidence.py" in Path(bundle["validationCommand"]).read_text(encoding="utf-8")
        assert "make_final_frontend_audit_inputs.py" in Path(bundle["finalAuditInputsCommand"]).read_text(encoding="utf-8")
        assert "audit_frontend_rendering.py" in Path(bundle["frontendAuditCommand"]).read_text(encoding="utf-8")
        assert "apply_batch_upload_publish.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")


def test_batch_upload_publish_evidence_bundle_preserves_source_context_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, context = source_context_batch_runbook(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            output_dir=root / "batch-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key, value in context.items():
            assert bundle[key] == value
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key, value in context.items():
            assert template[key] == value

        drifted = json.loads(json.dumps(bundle))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_bundle(drifted)
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues


def test_batch_upload_publish_evidence_bundle_rejects_mutating_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path = batch_runbook(root)
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
    test_batch_upload_publish_evidence_bundle_builds()
    test_batch_upload_publish_evidence_bundle_preserves_source_context_when_present()
    test_batch_upload_publish_evidence_bundle_rejects_mutating_runbook()
    print("batch upload/publish evidence bundle regression tests passed.")
