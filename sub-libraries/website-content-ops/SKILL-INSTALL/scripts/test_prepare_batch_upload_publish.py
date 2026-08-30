#!/usr/bin/env python3
"""Regression tests for batch upload/publish preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from prepare_batch_upload_publish import build
from test_apply_save_capture_to_manifest import source_identity
from test_apply_manifest_sample_upload import sample_evidence_for
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
from test_summarize_source_execution_status import confirmation_decision_matrix, content_goal_coverage, wiki_review


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def test_prepare_batch_upload_publish_outputs_non_executable_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        run_evidence["contentGoalCoverage"] = content_goal_coverage()
        run_evidence["contentCounts"] = content_counts()
        run_evidence["contentQualityReview"] = overage_quality()
        run_evidence["contentGoalOverages"] = content_goal_overages()
        review = wiki_review(root)
        run_evidence["wikiReview"] = review
        run_evidence["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        run_evidence["createdSiteSubmittedValues"] = created_site_submitted_values()
        run_evidence.update(source_identity())
        run_evidence_path = Path(write_json(root / "run-evidence.json", run_evidence))
        manifest = schema_manifest()
        manifest["contentGoalCoverage"] = content_goal_coverage()
        manifest["contentCounts"] = content_counts()
        manifest["contentQualityReview"] = overage_quality()
        manifest["contentGoalOverages"] = content_goal_overages()
        manifest["wikiReview"] = review
        manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
        manifest.update(source_identity())
        manifest_path = Path(write_json(root / "products-schema-verified-manifest.json", manifest))
        sample = sample_evidence()
        sample["contentGoalCoverage"] = content_goal_coverage()
        sample["contentCounts"] = content_counts()
        sample["contentQualityReview"] = overage_quality()
        sample["contentGoalOverages"] = content_goal_overages()
        sample["wikiReview"] = review
        sample["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        sample["createdSiteSubmittedValues"] = created_site_submitted_values()
        sample.update(source_identity())
        sample_path = Path(write_json(root / "products-sample-evidence.json", sample))
        summary = build(
            argparse.Namespace(
                run_evidence=str(run_evidence_path),
                manifest=str(manifest_path),
                sample_evidence=str(sample_path),
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )

        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == content_counts()
        assert summary["contentQualityReview"] == overage_quality()
        assert summary["contentGoalOverages"] == content_goal_overages()
        assert summary["wikiReview"] == review
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert summary["sourcePackageSha256"] == source_identity()["sourcePackageSha256"]
        assert summary["sourceReviewPacketSha256"] == source_identity()["sourceReviewPacketSha256"]
        assert summary["readyForBrowserStage"] == "ready_to_request_batch_upload_authorization"
        runbook = json.loads(Path(summary["artifacts"]["batchRunbook"]).read_text(encoding="utf-8"))
        bundle = json.loads(Path(summary["artifacts"]["batchEvidenceBundle"]).read_text(encoding="utf-8"))
        progress = json.loads(Path(summary["artifacts"]["batchProgressSeed"]).read_text(encoding="utf-8"))
        assert runbook["browserStepsExecutable"] is False
        for key in (
            "sourcePackageSha256",
            "sourceReviewPacketSha256",
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert runbook[key] == summary[key]
            assert runbook["redactedEvidenceTemplate"][key] == summary[key]
        assert "--sample-evidence" in runbook["preMutationGateCommand"]
        assert str(sample_path) in runbook["preMutationGateCommand"]
        assert bundle["kind"] == "allincms_batch_upload_publish_evidence_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["runbook"] == summary["artifacts"]["batchRunbook"]
        assert bundle["manifestItemCount"] == runbook["manifestItemCount"]
        for key in (
            "sourcePackageSha256",
            "sourceReviewPacketSha256",
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert bundle[key] == summary[key]
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_batch_upload_publish_evidence"
        assert template["progressLogComplete"] is False
        for key in (
            "sourcePackageSha256",
            "sourceReviewPacketSha256",
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert template[key] == summary[key]
        assert "make_final_frontend_audit_inputs.py" in Path(bundle["finalAuditInputsCommand"]).read_text(encoding="utf-8")
        assert "apply_batch_upload_publish.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")
        assert progress["manifestItemCount"] == 2
        assert progress["rows"][0]["source"] == "validated_sample_evidence"
        assert progress["rows"][0]["mediaRequired"] is False
        assert progress["rows"][1]["saveStatus"] == "pending"
        assert progress["rows"][1]["mediaRequired"] is False


def test_prepare_batch_upload_publish_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        run_evidence["contentCounts"] = content_counts()
        run_evidence["contentQualityReview"] = warning_quality()
        review = wiki_review(root)
        run_evidence["wikiReview"] = review
        run_evidence["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        manifest = schema_manifest()
        manifest["contentCounts"] = content_counts()
        manifest["contentQualityReview"] = warning_quality()
        manifest["wikiReview"] = review
        manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        sample = sample_evidence()
        sample["contentCounts"] = content_counts()
        sample["contentQualityReview"] = warning_quality()
        sample["wikiReview"] = review
        sample["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        summary = build(
            argparse.Namespace(
                run_evidence=str(Path(write_json(root / "run-evidence.json", run_evidence))),
                manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        assert summary["contentQualityReview"] == warning_quality()
        assert summary["contentCounts"] == content_counts()
        assert summary["wikiReview"] == review
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert "posts_present_without_post_categories" in summary["contentQualityReview"]["warnings"]


def test_prepare_batch_upload_publish_preserves_content_goal_overages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        context = {
            "contentGoalCoverage": content_goal_coverage(),
            "contentCounts": content_counts(),
            "contentQualityReview": overage_quality(),
            "contentGoalOverages": content_goal_overages(),
            "wikiReview": wiki_review(root),
            "confirmationDecisionMatrix": confirmation_decision_matrix(),
            "createdSiteSubmittedValues": created_site_submitted_values(),
            **source_identity(),
        }
        summary = build(
            argparse.Namespace(
                run_evidence=str(Path(write_json(root / "run-evidence.json", {**base_run_evidence(), **context}))),
                manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", {**schema_manifest(), **context}))),
                sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", {**sample_evidence(), **context}))),
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        assert summary["contentGoalOverages"] == content_goal_overages()
        runbook = json.loads(Path(summary["artifacts"]["batchRunbook"]).read_text(encoding="utf-8"))
        bundle = json.loads(Path(summary["artifacts"]["batchEvidenceBundle"]).read_text(encoding="utf-8"))
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert runbook["contentGoalOverages"] == content_goal_overages()
        assert runbook["redactedEvidenceTemplate"]["contentGoalOverages"] == content_goal_overages()
        assert bundle["contentGoalOverages"] == content_goal_overages()
        assert template["contentGoalOverages"] == content_goal_overages()


def test_prepare_batch_upload_publish_blocks_content_goal_overage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base_context = {
            "contentQualityReview": overage_quality(),
            "contentGoalOverages": content_goal_overages(),
            "wikiReview": wiki_review(root),
            "confirmationDecisionMatrix": confirmation_decision_matrix(),
        }
        manifest_context = json.loads(json.dumps(base_context))
        manifest_context["contentGoalOverages"]["details"].pop("posts")
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(Path(write_json(root / "run-evidence.json", {**base_run_evidence(), **base_context}))),
                    manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", {**schema_manifest(), **manifest_context}))),
                    sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", {**sample_evidence(), **base_context}))),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "content goal overages" in str(exc)
        else:
            raise AssertionError("contentGoalOverages drift should block batch preparation")


def test_prepare_batch_upload_publish_blocks_decision_matrix_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        run_evidence["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        manifest = schema_manifest()
        manifest["confirmationDecisionMatrix"] = [
            {**confirmation_decision_matrix()[0], "decision": "defer", "deferDecision": "changed"}
        ]
        sample = sample_evidence()
        sample["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(Path(write_json(root / "run-evidence.json", run_evidence))),
                    manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                    sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "decision matrix" in str(exc)
        else:
            raise AssertionError("confirmationDecisionMatrix drift should block batch preparation")


def test_prepare_batch_upload_publish_blocks_wiki_review_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        review = wiki_review(root)
        run_evidence["wikiReview"] = review
        manifest = schema_manifest()
        manifest["wikiReview"] = {**review, "sourceWikiMarkdown": str(root / "other-manifest.json")}
        sample = sample_evidence()
        sample["wikiReview"] = review
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(Path(write_json(root / "run-evidence.json", run_evidence))),
                    manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                    sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "wiki review" in str(exc)
        else:
            raise AssertionError("wikiReview drift should block batch preparation")


def test_prepare_batch_upload_publish_blocks_content_count_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        run_evidence["contentCounts"] = content_counts()
        manifest = schema_manifest()
        manifest["contentCounts"] = {**content_counts(), "products": 3}
        sample = sample_evidence()
        sample["contentCounts"] = content_counts()
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(Path(write_json(root / "run-evidence.json", run_evidence))),
                    manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                    sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "content counts" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block batch preparation")


def test_prepare_batch_upload_publish_blocks_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence = base_run_evidence()
        run_evidence["createdSiteSubmittedValues"] = created_site_submitted_values()
        manifest = schema_manifest()
        manifest["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "description": "Different submitted description.",
        }
        sample = sample_evidence()
        sample["createdSiteSubmittedValues"] = created_site_submitted_values()
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(Path(write_json(root / "run-evidence.json", run_evidence))),
                    manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                    sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "created-site submitted values" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block batch preparation")


def test_prepare_batch_upload_publish_blocks_taxonomy_manifest_without_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["categories"] = ["Example Category"]
        run_evidence_path = Path(write_json(root / "run-evidence.json", base_run_evidence()))
        manifest_path = Path(write_json(root / "products-schema-verified-manifest.json", manifest))
        sample_path = Path(write_json(root / "products-sample-evidence.json", sample_evidence()))
        try:
            build(
                argparse.Namespace(
                    run_evidence=str(run_evidence_path),
                    manifest=str(manifest_path),
                    sample_evidence=str(sample_path),
                    taxonomy_validation="",
                    output_dir=str(root / "batch-prep"),
                    target="",
                    target_identifier="",
                    authorization_output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "taxonomy gate" in str(exc)
        else:
            raise AssertionError("taxonomy manifest should require taxonomy validation before batch prep")


def test_prepare_batch_upload_publish_marks_manifest_media_required_rows() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["coverImage"] = {
            "url": "https://example.com/source-cover.jpg",
            "alt": "Source-backed product cover",
        }
        sample = sample_evidence()
        sample["coverOrMediaVerified"] = True
        summary = build(
            argparse.Namespace(
                run_evidence=str(Path(write_json(root / "run-evidence.json", base_run_evidence()))),
                manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        progress = json.loads(Path(summary["artifacts"]["batchProgressSeed"]).read_text(encoding="utf-8"))
        by_slug = {row["slug"]: row for row in progress["rows"]}
        assert by_slug["industrial-demo-product"]["mediaRequired"] is True
        assert by_slug["industrial-demo-product-two"]["mediaRequired"] is False


def test_prepare_batch_upload_publish_marks_media_needs_required_rows() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["mediaNeeds"] = [{"target": "product.cover", "kind": "cover"}]
        sample = sample_evidence()
        sample["coverOrMediaVerified"] = True
        summary = build(
            argparse.Namespace(
                run_evidence=str(Path(write_json(root / "run-evidence.json", base_run_evidence()))),
                manifest=str(Path(write_json(root / "products-schema-verified-manifest.json", manifest))),
                sample_evidence=str(Path(write_json(root / "products-sample-evidence.json", sample))),
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        progress = json.loads(Path(summary["artifacts"]["batchProgressSeed"]).read_text(encoding="utf-8"))
        by_slug = {row["slug"]: row for row in progress["rows"]}
        assert by_slug["industrial-demo-product"]["mediaRequired"] is True
        assert by_slug["industrial-demo-product-two"]["mediaRequired"] is False


def test_prepare_batch_upload_publish_accepts_valid_taxonomy_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = schema_manifest()
        manifest["items"][0]["categories"] = ["Example Category"]
        run_evidence_path = Path(write_json(root / "run-evidence.json", base_run_evidence()))
        manifest_path = Path(write_json(root / "products-schema-verified-manifest.json", manifest))
        sample_path = Path(write_json(root / "products-sample-evidence.json", sample_evidence()))
        taxonomy_path = Path(
            write_json(
                root / "taxonomy-validation.json",
                {
                    "kind": "allincms_taxonomy_execution_evidence_validation",
                    "valid": True,
                    "siteKey": "demo123",
                    "taxonomyPrerequisiteSatisfied": True,
                    "issues": [],
                },
            )
        )
        summary = build(
            argparse.Namespace(
                run_evidence=str(run_evidence_path),
                manifest=str(manifest_path),
                sample_evidence=str(sample_path),
                taxonomy_validation=str(taxonomy_path),
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        assert summary["validation"]["taxonomyRequired"] is True
        assert summary["readyForBrowserStage"] == "ready_to_request_batch_upload_authorization"


def test_prepare_batch_upload_publish_preserves_existing_sample_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_evidence_path = Path(write_json(root / "run-evidence.json", base_run_evidence()))
        manifest_path = Path(write_json(root / "products-schema-verified-manifest.json", schema_manifest()))
        products_sample_path = Path(write_json(root / "products-sample-evidence.json", sample_evidence_for("products")))
        posts_sample_path = Path(write_json(root / "posts-sample-evidence.json", sample_evidence_for("posts")))
        summary = build(
            argparse.Namespace(
                run_evidence=str(run_evidence_path),
                manifest=str(manifest_path),
                sample_evidence=str(products_sample_path),
                existing_sample_evidence=[str(posts_sample_path)],
                taxonomy_validation="",
                output_dir=str(root / "batch-prep"),
                target="",
                target_identifier="",
                authorization_output="",
                json=False,
            )
        )
        assert summary["sampleEvidence"] == str(products_sample_path)
        assert summary["existingSampleEvidence"] == [str(posts_sample_path)]
        assert summary["mergedSampleEvidence"] == [str(posts_sample_path), str(products_sample_path)]
        assert summary["sampleEvidenceContentTypes"] == ["posts", "products"]
        assert summary["readyForBrowserStage"] == "ready_to_request_batch_upload_authorization"


if __name__ == "__main__":
    test_prepare_batch_upload_publish_outputs_non_executable_runbook()
    test_prepare_batch_upload_publish_preserves_content_quality_warning()
    test_prepare_batch_upload_publish_preserves_content_goal_overages()
    test_prepare_batch_upload_publish_blocks_content_goal_overage_drift()
    test_prepare_batch_upload_publish_blocks_decision_matrix_drift()
    test_prepare_batch_upload_publish_blocks_content_count_drift()
    test_prepare_batch_upload_publish_blocks_wiki_review_drift()
    test_prepare_batch_upload_publish_blocks_created_site_submitted_value_drift()
    test_prepare_batch_upload_publish_blocks_taxonomy_manifest_without_validation()
    test_prepare_batch_upload_publish_marks_manifest_media_required_rows()
    test_prepare_batch_upload_publish_marks_media_needs_required_rows()
    test_prepare_batch_upload_publish_accepts_valid_taxonomy_validation()
    test_prepare_batch_upload_publish_preserves_existing_sample_context()
    print("batch upload/publish preparation regression tests passed.")
