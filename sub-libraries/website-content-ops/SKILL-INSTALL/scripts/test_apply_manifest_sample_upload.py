#!/usr/bin/env python3
"""Regression tests for applying manifest sample upload evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_manifest_sample_upload import build
from test_manifest_sample_upload import (
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
    wiki_review,
)


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def add_quality_warning_to_path(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["contentQualityReview"] = warning_quality()
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_wiki_review_to_path(path: str, review: dict) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["wikiReview"] = review
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


def sample_evidence_for(content_type: str) -> dict:
    evidence = sample_evidence()
    evidence["contentType"] = content_type
    slug = str(evidence.get("sampleSlug") or "industrial-demo-product")
    evidence["target"] = f"https://workspace.laicms.com/demo123/{content_type}"
    evidence["backendUrl"] = f"https://workspace.laicms.com/demo123/{content_type}/redacted/update"
    evidence["frontendUrl"] = f"https://demo123.web.allincms.com/{content_type}/{slug}"
    return evidence


def base_args(root: Path, *, bad_sample: bool = False) -> argparse.Namespace:
    package_path = write_json(root / "package.json", package())
    review_path = write_json(root / "review-packet.json", review_packet(package_path))
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    for path in (package_path, review_path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["contentCounts"] = content_counts()
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    confirmation_data["contentCounts"] = content_counts()
    evidence = sample_evidence()
    evidence["contentCounts"] = content_counts()
    evidence["createdSiteSubmittedValues"] = created_site_submitted_values()
    if bad_sample:
        evidence["frontendVerified"] = False
    manifest = schema_manifest()
    manifest["contentCounts"] = content_counts()
    manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
    execution_plan_data = execution_plan()
    execution_plan_data["contentCounts"] = content_counts()
    created_site_binding_data = created_site_binding()
    created_site_binding_data["contentCounts"] = content_counts()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    return argparse.Namespace(
        manifest=write_json(root / "products-schema-verified-manifest.json", manifest),
        sample_evidence=write_json(root / "products-sample-evidence.json", evidence),
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
        existing_sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        launch_acceptance="",
        output_dir=str(root / "apply-sample"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_manifest_sample_upload_advances_to_batch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root))
        assert summary["validationValid"] is True
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == content_counts()
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert len(summary["artifacts"]["mergedSampleEvidence"]) == 1
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "batch_upload"
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["sample_upload"]["status"] == "passed"
        assert status["currentStage"] == "batch_upload", status
        validation = json.loads(Path(summary["artifacts"]["sampleValidation"]).read_text(encoding="utf-8"))
        assert validation["batchPrerequisiteSatisfied"] is True
        progress = json.loads(Path(summary["artifacts"]["sampleProgressEntry"]).read_text(encoding="utf-8"))
        assert progress["slug"] == "industrial-demo-product"


def test_apply_manifest_sample_upload_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        manifest = schema_manifest()
        manifest["contentQualityReview"] = warning_quality()
        manifest["contentCounts"] = content_counts()
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        review = wiki_review(root)
        manifest["wikiReview"] = review
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
            add_wiki_review_to_path(path, review)
        confirmation_data = json.loads(Path(args.confirmation).read_text(encoding="utf-8"))
        add_quality_warning_to_path(confirmation_data["sourceReviewPacket"])
        add_wiki_review_to_path(confirmation_data["sourceReviewPacket"], review)
        summary = build(args)
        assert summary["contentQualityReview"] == warning_quality()
        assert summary["contentCounts"] == content_counts()
        assert summary["wikiReview"] == review
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert "posts_present_without_post_categories" in summary["contentQualityReview"]["warnings"]


def test_apply_manifest_sample_upload_keeps_invalid_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, bad_sample=True))
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_manifest_sample_evidence"
        assert summary["validation"]["manifestSampleIssues"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "sample_upload", status


def test_apply_manifest_sample_upload_merges_existing_content_type_sample() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        args.artifact_readiness = write_json(root / "artifact-readiness-dual.json", dual_artifact_readiness())
        products_sample = sample_evidence_for("products")
        products_sample["createdSiteSubmittedValues"] = created_site_submitted_values()
        args.sample_evidence = write_json(root / "products-sample-evidence.json", products_sample)
        args.existing_sample_evidence = [
            write_json(root / "posts-sample-evidence.json", sample_evidence_for("posts")),
        ]
        summary = build(args)
        assert summary["validationValid"] is True
        assert summary["sourceNextStage"]["currentStage"] == "batch_upload", summary
        assert len(summary["artifacts"]["mergedSampleEvidence"]) == 2
        assert summary["artifacts"]["sampleValidation"]
        handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        local_command = handoff["localCommand"]
        assert "--sample-evidence" in local_command
        assert "products-sample-evidence.json" in local_command
        assert "--existing-sample-evidence" in local_command
        assert "posts-sample-evidence.json" in local_command
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "batch_upload", status
        assert status["contentTypeCoverage"]["sampleEvidence"] == ["posts", "products"]


def test_apply_manifest_sample_upload_rejects_content_count_drift() -> None:
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
            raise AssertionError("contentCounts drift should block sample apply")


def test_apply_manifest_sample_upload_rejects_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        sample = sample_evidence()
        sample["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "name": "Different Demo",
        }
        args.sample_evidence = write_json(root / "products-sample-evidence.drift.json", sample)
        try:
            build(args)
        except SystemExit as exc:
            assert "created-site submitted values" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block sample apply")


if __name__ == "__main__":
    test_apply_manifest_sample_upload_advances_to_batch()
    test_apply_manifest_sample_upload_preserves_content_quality_warning()
    test_apply_manifest_sample_upload_keeps_invalid_blocked()
    test_apply_manifest_sample_upload_merges_existing_content_type_sample()
    test_apply_manifest_sample_upload_rejects_content_count_drift()
    test_apply_manifest_sample_upload_rejects_created_site_submitted_value_drift()
    print("apply manifest sample upload regression tests passed.")
