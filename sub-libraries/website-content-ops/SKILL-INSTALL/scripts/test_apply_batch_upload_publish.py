#!/usr/bin/env python3
"""Regression tests for applying batch upload/publish evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_batch_upload_publish import build
from test_manifest_sample_upload import (
    base_run_evidence,
    content_counts,
    created_site_submitted_values,
    sample_evidence,
    schema_manifest,
    warning_quality,
)
from test_summarize_source_execution_status import (
    confirmation,
    confirmation_decision_matrix,
    content_goal_coverage,
    created_site_binding,
    execution_plan,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    schema_capture_handoff,
    upload_readiness,
)
from test_validate_source_run_acceptance import counted_batch_validation


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def add_quality_warning_to_path(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["contentQualityReview"] = warning_quality()
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "draftManifestStatus": {
            "products": {"itemCount": 2, "schemaVerified": False},
            "posts": {"itemCount": 0, "schemaVerified": False},
        },
    }


def dual_artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "draftManifestStatus": {
            "products": {"itemCount": 1, "schemaVerified": False},
            "posts": {"itemCount": 1, "schemaVerified": False},
        },
    }


def run_evidence_with_sample() -> dict:
    data = base_run_evidence()
    data["contentCounts"] = content_counts()
    data["createdSiteSubmittedValues"] = created_site_submitted_values()
    data["sampleVerification"] = {
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
    }
    return data


def sample_evidence_for(content_type: str) -> dict:
    data = sample_evidence()
    data["contentType"] = content_type
    data["target"] = f"https://workspace.laicms.com/demo123/{content_type}"
    data["backendUrl"] = f"https://workspace.laicms.com/demo123/{content_type}/redacted/update"
    data["frontendUrl"] = f"https://demo123.web.allincms.com/{content_type}/industrial-demo"
    return data


def progress_row(slug: str) -> dict:
    return {
        "slug": slug,
        "contentType": "products",
        "backendUrl": f"https://workspace.laicms.com/demo123/products/{slug}/update",
        "frontendUrl": f"https://demo123.web.allincms.com/products/{slug}",
        "saveStatus": "ok",
        "publishStatus": "ok",
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": True,
        "errors": [],
    }


def batch_evidence() -> dict:
    return {
        "kind": "allincms_batch_upload_publish_evidence",
        "siteKey": "demo123",
        "contentType": "products",
        "contentCounts": content_counts(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        "target": "https://workspace.laicms.com/demo123/products",
        "manifestPath": "/tmp/products-schema-verified-manifest.json",
        "authorizationRecord": "/tmp/batch-auth.json",
        "preMutationGate": "passed",
        "action": "batch_upload",
        "schemaGatePass": True,
        "sampleVerificationPass": True,
        "progressLogComplete": True,
        "frontendDetailAuditPass": True,
        "progressLog": [
            progress_row("industrial-demo-product"),
            progress_row("industrial-demo-product-two"),
        ],
        "frontendDetailAudit": {
            "checked": True,
            "detailRouteCount": 2,
            "markdownResidueChecked": True,
            "structuredRichTextChecked": True,
            "blockingIssues": [],
        },
        "stopConditionMet": True,
    }


def frontend_audit_reports() -> list[dict]:
    return [
        {
            "url": "/products/{slug}",
            "status": 200,
            "expectedStatus": 200,
            "tagCounts": {"h1": 1, "h2": 1, "h3": 0, "li": 1, "table": 0, "strong": 0, "b": 0, "code": 0, "img": 1, "a": 2},
            "issues": [],
        },
        {
            "url": "/products/{slug}",
            "status": 200,
            "expectedStatus": 200,
            "tagCounts": {"h1": 1, "h2": 1, "h3": 0, "li": 1, "table": 0, "strong": 0, "b": 0, "code": 0, "img": 1, "a": 2},
            "issues": [],
        },
    ]


def base_args(root: Path, *, bad_batch: bool = False) -> argparse.Namespace:
    package_path = write_json(root / "package.json", package())
    review_path = write_json(root / "review-packet.json", review_packet(package_path))
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    for path in (package_path, review_path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["contentCounts"] = content_counts()
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    confirmation_data["contentCounts"] = content_counts()
    evidence = batch_evidence()
    if bad_batch:
        evidence["progressLog"] = evidence["progressLog"][:1]
    manifest = schema_manifest()
    manifest["contentCounts"] = content_counts()
    manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
    execution_plan_data = execution_plan()
    execution_plan_data["contentCounts"] = content_counts()
    created_site_binding_data = created_site_binding()
    created_site_binding_data["contentCounts"] = content_counts()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    sample_data = sample_evidence()
    sample_data["contentCounts"] = content_counts()
    sample_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    return argparse.Namespace(
        batch_evidence=write_json(root / "batch-evidence.json", evidence),
        manifest=write_json(root / "products-schema-verified-manifest.json", manifest),
        base_run_evidence=write_json(root / "run-evidence.json", run_evidence_with_sample()),
        frontend_audit_report=write_json(root / "frontend-audit-report.json", frontend_audit_reports()),
        package=package_path,
        review_packet="",
        confirmation=write_json(root / "confirmation.json", confirmation_data),
        execution_plan=write_json(root / "execution-plan.json", execution_plan_data),
        artifact_readiness=write_json(root / "artifact-readiness.json", artifact_readiness()),
        created_site_binding=write_json(root / "created-site-binding.json", created_site_binding_data),
        pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
        pages_site_info_evidence="",
        pages_site_info_validation=write_json(root / "pages-site-info-validation.json", pages_site_info_validation()),
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff=write_json(root / "schema-capture-handoff.json", schema_capture_handoff()),
        upload_readiness=write_json(root / "upload-readiness.json", upload_readiness()),
        sample_evidence=[write_json(root / "sample-evidence.json", sample_data)],
        existing_batch_validation=[
            write_json(root / "posts-batch-validation.json", counted_batch_validation("posts")),
        ],
        forms_media_settings="",
        launch_acceptance="",
        output_dir=str(root / "apply-batch"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_batch_upload_publish_advances_to_forms_media_settings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root))
        assert summary["validationValid"] is True
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == content_counts()
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert len(summary["artifacts"]["mergedBatchValidation"]) == 2
        assert summary["artifacts"]["batchValidation"] in summary["artifacts"]["mergedBatchValidation"]
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "forms_media_settings"
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["batch_upload"]["status"] == "passed"
        assert status["currentStage"] == "forms_media_settings", status
        validation = json.loads(Path(summary["artifacts"]["batchValidation"]).read_text(encoding="utf-8"))
        assert validation["mergeReady"] is True
        progress = json.loads(Path(summary["artifacts"]["batchProgressLog"]).read_text(encoding="utf-8"))
        assert len(progress["rows"]) == 2


def test_apply_batch_upload_publish_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        manifest = schema_manifest()
        manifest["contentQualityReview"] = warning_quality()
        manifest["contentCounts"] = content_counts()
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        args.manifest = write_json(root / "products-schema-verified-manifest.warning.json", manifest)
        for path in (
            args.confirmation,
            args.execution_plan,
            args.artifact_readiness,
            args.created_site_binding,
            args.schema_capture_handoff,
        ):
            add_quality_warning_to_path(path)
        confirmation_data = json.loads(Path(args.confirmation).read_text(encoding="utf-8"))
        add_quality_warning_to_path(confirmation_data["sourceReviewPacket"])
        summary = build(args)
        assert summary["contentQualityReview"] == warning_quality()
        assert summary["contentCounts"] == content_counts()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert "posts_present_without_post_categories" in summary["contentQualityReview"]["warnings"]


def test_apply_batch_upload_publish_keeps_invalid_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, bad_batch=True))
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_batch_upload_evidence"
        assert summary["validation"]["batchIssues"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "batch_upload", status


def test_apply_batch_upload_publish_blocks_missing_manifest_media_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        manifest = schema_manifest()
        manifest["contentCounts"] = content_counts()
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        manifest["items"][0]["coverImage"] = {
            "url": "https://example.com/source-cover.jpg",
            "alt": "Source-backed product cover",
        }
        evidence = batch_evidence()
        evidence["progressLog"][0]["coverOrMediaVerified"] = False
        args.manifest = write_json(root / "products-schema-verified-manifest.with-cover.json", manifest)
        args.batch_evidence = write_json(root / "batch-evidence.missing-cover.json", evidence)
        summary = build(args)
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_batch_upload_evidence"
        assert any("manifest item has media" in issue for issue in summary["validation"]["batchIssues"])


def test_apply_batch_upload_publish_blocks_missing_media_needs_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        manifest = schema_manifest()
        manifest["contentCounts"] = content_counts()
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        manifest["items"][0]["mediaNeeds"] = [{"target": "product.cover", "kind": "cover"}]
        evidence = batch_evidence()
        evidence["progressLog"][0]["coverOrMediaVerified"] = False
        args.manifest = write_json(root / "products-schema-verified-manifest.with-media-needs.json", manifest)
        args.batch_evidence = write_json(root / "batch-evidence.missing-media-needs-proof.json", evidence)
        summary = build(args)
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_batch_upload_evidence"
        assert any("manifest item has media" in issue for issue in summary["validation"]["batchIssues"])


def test_apply_batch_upload_publish_merges_existing_content_type_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        args.artifact_readiness = write_json(root / "artifact-readiness-dual.json", dual_artifact_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample-evidence.json", sample_evidence_for("products")),
            write_json(root / "posts-sample-evidence.json", sample_evidence_for("posts")),
        ]
        summary = build(args)
        assert summary["validationValid"] is True
        assert summary["sourceNextStage"]["currentStage"] == "forms_media_settings", summary
        assert len(summary["artifacts"]["mergedBatchValidation"]) == 2
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "forms_media_settings", status
        assert status["contentTypeCoverage"]["batchValidation"] == ["posts", "products"]


def test_apply_batch_upload_publish_rejects_content_count_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        manifest = schema_manifest()
        manifest["contentCounts"] = {**content_counts(), "products": 3}
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        args.manifest = write_json(root / "products-schema-verified-manifest.drift.json", manifest)
        try:
            build(args)
        except SystemExit as exc:
            assert "contentCounts mismatch" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block batch apply")


def test_apply_batch_upload_publish_rejects_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        evidence = batch_evidence()
        evidence["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "description": "Different submitted description.",
        }
        args.batch_evidence = write_json(root / "batch-evidence.submitted-values-drift.json", evidence)
        try:
            build(args)
        except SystemExit as exc:
            assert "created-site submitted values" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block batch apply")


if __name__ == "__main__":
    test_apply_batch_upload_publish_advances_to_forms_media_settings()
    test_apply_batch_upload_publish_preserves_content_quality_warning()
    test_apply_batch_upload_publish_keeps_invalid_blocked()
    test_apply_batch_upload_publish_blocks_missing_manifest_media_proof()
    test_apply_batch_upload_publish_blocks_missing_media_needs_proof()
    test_apply_batch_upload_publish_merges_existing_content_type_validation()
    test_apply_batch_upload_publish_rejects_content_count_drift()
    test_apply_batch_upload_publish_rejects_created_site_submitted_value_drift()
    print("apply batch upload/publish regression tests passed.")
