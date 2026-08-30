#!/usr/bin/env python3
"""Regression tests for schema manifest and sample runbook preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_schema_capture_handoff import build_handoff as build_schema_handoff
from prepare_schema_save_capture import build as build_save_capture_prep
from prepare_schema_manifest_sample import build
from test_apply_save_capture_to_manifest import (
    base_run_evidence,
    confirmation_decision_matrix,
    draft_manifest,
    save_capture,
)
from test_manifest_sample_upload import content_counts, warning_quality
from test_schema_capture_handoff import prepare_binding
from test_summarize_schema_capture_progress import create_evidence
from test_summarize_source_execution_status import (
    confirmation,
    content_goal_coverage,
    created_site_binding,
    execution_plan,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    schema_capture_handoff as source_schema_capture_handoff,
    upload_readiness_for,
    wiki_review,
)


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


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


def test_prepare_schema_manifest_sample_outputs_ready_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = prepare_schema_handoff(root)
        create_path = Path(write_json(root / "products-create-evidence.json", create_evidence()))
        save_prep = build_save_capture_prep(
            argparse.Namespace(
                schema_capture_handoff=str(handoff_path),
                content_type="products",
                create_evidence=str(create_path),
                output_dir=str(root / "save-capture-prep"),
                preflight="",
                edit_url="",
                authorization_output="",
                existing_create_evidence=[],
                existing_save_handoff=[],
                existing_save_runbook=[],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                existing_upload_readiness=[],
                json=False,
            )
        )
        manifest_path = Path(write_json(root / "products-draft-manifest.json", draft_manifest("products")))
        capture_path = Path(write_json(root / "products-save-capture.json", save_capture("products")))
        base_path = Path(write_json(root / "products-base-run-evidence.json", base_run_evidence("products")))
        summary = build(
            argparse.Namespace(
                manifest=str(manifest_path),
                save_capture_evidence=str(capture_path),
                base_run_evidence=str(base_path),
                schema_capture_handoff=str(handoff_path),
                package="",
                review_packet="",
                confirmation="",
                execution_plan="",
                artifact_readiness="",
                create_site_handoff="",
                created_site_binding="",
                pages_site_info_handoff="",
                pages_site_info_evidence="",
                pages_site_info_validation="",
                taxonomy_handoff="",
                taxonomy_evidence="",
                taxonomy_validation="",
                sample_evidence=[],
                batch_evidence="",
                batch_validation="",
                launch_acceptance="",
                output_dir=str(root / "schema-manifest-sample"),
                site_key="",
                frontend_base_url="",
                target="",
                sample_slug="",
                authorization_output="",
                existing_create_evidence=[f"products={create_path}"],
                existing_save_handoff=[f"products={save_prep['artifacts']['saveHandoff']}"],
                existing_save_runbook=[f"products={save_prep['artifacts']['saveRunbook']}"],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                existing_upload_readiness=[],
                json=False,
            )
        )
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["contentType"] == "products"
        assert Path(summary["artifacts"]["sampleEvidenceBundle"]).exists()
        schema_manifest = json.loads(Path(summary["artifacts"]["schemaVerifiedManifest"]).read_text(encoding="utf-8"))
        readiness = json.loads(Path(summary["artifacts"]["uploadReadiness"]).read_text(encoding="utf-8"))
        runbook = json.loads(Path(summary["artifacts"]["sampleRunbook"]).read_text(encoding="utf-8"))
        sample_bundle = json.loads(Path(summary["artifacts"]["sampleEvidenceBundle"]).read_text(encoding="utf-8"))
        progress = json.loads(Path(summary["artifacts"]["schemaCaptureProgress"]).read_text(encoding="utf-8"))
        assert schema_manifest["schemaVerified"] is True
        assert readiness["overallStatus"] == "ready_for_sample_upload"
        assert runbook["kind"] == "allincms_manifest_sample_upload_runbook"
        assert runbook["browserStepsExecutable"] is False
        assert sample_bundle["kind"] == "allincms_manifest_sample_evidence_bundle"
        assert sample_bundle["browserStepsExecutable"] is False
        assert sample_bundle["runbook"] == summary["artifacts"]["sampleRunbook"]
        assert sample_bundle["sampleSlug"] == runbook["sampleSlug"]
        sample_template = json.loads(Path(sample_bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert sample_template["kind"] == "allincms_manifest_sample_upload_evidence"
        assert sample_template["sampleSlug"] == runbook["sampleSlug"]
        assert "other than sampleSlug" in " ".join(runbook["forbiddenActions"])
        products = next(item for item in progress["results"] if item["contentType"] == "products")
        assert products["status"] == "schema_manifest_ready"
        assert summary["artifacts"]["sourceExecutionStatus"] == ""


def test_prepare_schema_manifest_sample_refreshes_source_status() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = Path(write_json(root / "source-schema-capture-handoff.json", source_schema_capture_handoff()))
        manifest_path = Path(write_json(root / "products-draft-manifest.json", draft_manifest("products")))
        capture_path = Path(write_json(root / "products-save-capture.json", save_capture("products")))
        base_path = Path(write_json(root / "products-base-run-evidence.json", base_run_evidence("products")))
        package_path = write_json(root / "package.json", package())
        review_path = write_json(root / "review-packet.json", review_packet(package_path))
        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = review_path
        summary = build(
            argparse.Namespace(
                manifest=str(manifest_path),
                save_capture_evidence=str(capture_path),
                base_run_evidence=str(base_path),
                schema_capture_handoff=str(handoff_path),
                package=package_path,
                review_packet=review_path,
                confirmation=write_json(root / "confirmation.json", confirmation_data),
                execution_plan=write_json(root / "execution-plan.json", execution_plan()),
                artifact_readiness=write_json(root / "artifact-readiness.json", {
                    "kind": "allincms_confirmed_site_artifact_readiness",
                    "localOnly": True,
                    "remoteMutationsPerformed": False,
                    "preparedOnly": True,
                    "contentGoalCoverage": content_goal_coverage(),
                    "draftManifestStatus": {
                        "products": {"itemCount": 1, "schemaVerified": False},
                        "posts": {"itemCount": 0, "schemaVerified": False},
                    },
                }),
                create_site_handoff="",
                created_site_binding=write_json(root / "created-site-binding.json", created_site_binding()),
                pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
                pages_site_info_evidence="",
                pages_site_info_validation=write_json(root / "pages-site-info-validation.json", pages_site_info_validation()),
                taxonomy_handoff="",
                taxonomy_evidence="",
                taxonomy_validation="",
                sample_evidence=[],
                batch_evidence="",
                batch_validation="",
                launch_acceptance="",
                output_dir=str(root / "schema-manifest-sample-status"),
                site_key="",
                frontend_base_url="",
                target="",
                sample_slug="",
                authorization_output="",
                existing_create_evidence=[],
                existing_save_handoff=[],
                existing_save_runbook=[],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                existing_upload_readiness=[],
                json=False,
            )
        )
        status_path = summary["artifacts"]["sourceExecutionStatus"]
        assert status_path
        status = json.loads(Path(status_path).read_text(encoding="utf-8"))
        assert status["stages"]["schema_manifests"]["status"] == "passed"
        assert status["currentStage"] == "sample_upload", status
        assert summary["readyForNextStage"] == "sample_upload"
        assert summary["contentGoalCoverage"]["complete"] is True
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "sample_upload"


def test_prepare_schema_manifest_sample_merges_existing_upload_readiness() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = Path(write_json(root / "source-schema-capture-handoff.json", source_schema_capture_handoff()))
        manifest_path = Path(write_json(root / "posts-draft-manifest.json", draft_manifest("posts")))
        capture_path = Path(write_json(root / "posts-save-capture.json", save_capture("posts")))
        base_path = Path(write_json(root / "posts-base-run-evidence.json", base_run_evidence("posts")))
        package_path = write_json(root / "package.json", package())
        review_path = write_json(root / "review-packet.json", review_packet(package_path))
        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = review_path
        products_readiness = write_json(root / "products-upload-readiness.json", upload_readiness_for("products"))
        summary = build(
            argparse.Namespace(
                manifest=str(manifest_path),
                save_capture_evidence=str(capture_path),
                base_run_evidence=str(base_path),
                schema_capture_handoff=str(handoff_path),
                package=package_path,
                review_packet=review_path,
                confirmation=write_json(root / "confirmation.json", confirmation_data),
                execution_plan=write_json(root / "execution-plan.json", execution_plan()),
                artifact_readiness=write_json(root / "artifact-readiness.json", {
                    "kind": "allincms_confirmed_site_artifact_readiness",
                    "localOnly": True,
                    "remoteMutationsPerformed": False,
                    "preparedOnly": True,
                    "contentGoalCoverage": content_goal_coverage(),
                    "draftManifestStatus": {
                        "products": {"itemCount": 1, "schemaVerified": False},
                        "posts": {"itemCount": 1, "schemaVerified": False},
                    },
                }),
                create_site_handoff="",
                created_site_binding=write_json(root / "created-site-binding.json", created_site_binding()),
                pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
                pages_site_info_evidence="",
                pages_site_info_validation=write_json(root / "pages-site-info-validation.json", pages_site_info_validation()),
                taxonomy_handoff="",
                taxonomy_evidence="",
                taxonomy_validation="",
                sample_evidence=[],
                batch_evidence="",
                batch_validation="",
                launch_acceptance="",
                output_dir=str(root / "schema-manifest-sample-merged-readiness"),
                site_key="",
                frontend_base_url="",
                target="",
                sample_slug="",
                authorization_output="",
                existing_create_evidence=[],
                existing_save_handoff=[],
                existing_save_runbook=[],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                existing_upload_readiness=[products_readiness],
                json=False,
            )
        )
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "sample_upload", status
        assert status["contentTypeCoverage"]["uploadReadiness"] == ["posts", "products"]
        assert products_readiness in summary["artifacts"]["mergedUploadReadiness"]
        assert summary["artifacts"]["uploadReadiness"] in summary["artifacts"]["mergedUploadReadiness"]


def test_prepare_schema_manifest_sample_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = draft_manifest("products")
        manifest["contentGoalCoverage"] = content_goal_coverage()
        manifest["contentCounts"] = content_counts()
        manifest["contentQualityReview"] = warning_quality()
        manifest["wikiReview"] = wiki_review(root)
        manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
        summary = build(
            argparse.Namespace(
                manifest=write_json(root / "products-draft-manifest.json", manifest),
                save_capture_evidence=write_json(root / "save-capture.json", save_capture("products")),
                base_run_evidence=write_json(root / "base-run-evidence.json", base_run_evidence("products")),
                schema_capture_handoff="",
                package="",
                review_packet="",
                confirmation="",
                execution_plan="",
                artifact_readiness="",
                create_site_handoff="",
                created_site_binding="",
                pages_site_info_handoff="",
                pages_site_info_evidence="",
                pages_site_info_validation="",
                taxonomy_handoff="",
                taxonomy_evidence="",
                taxonomy_validation="",
                sample_evidence=[],
                batch_evidence="",
                batch_validation="",
                forms_media_settings="",
                launch_acceptance="",
                output_dir=str(root / "schema-sample"),
                site_key="",
                frontend_base_url="",
                target="",
                sample_slug="",
                authorization_output="",
                existing_create_evidence=[],
                existing_save_handoff=[],
                existing_save_runbook=[],
                existing_save_capture=[],
                existing_base_run_evidence=[],
                existing_schema_manifest=[],
                existing_upload_readiness=[],
                json=False,
            )
        )
        schema_manifest = json.loads(Path(summary["artifacts"]["schemaVerifiedManifest"]).read_text(encoding="utf-8"))
        assert summary["contentGoalCoverage"] == content_goal_coverage()
        assert summary["contentCounts"] == content_counts()
        assert summary["contentQualityReview"] == warning_quality()
        assert summary["wikiReview"] == manifest["wikiReview"]
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert schema_manifest["contentGoalCoverage"] == content_goal_coverage()
        assert schema_manifest["contentCounts"] == content_counts()
        assert schema_manifest["contentQualityReview"] == warning_quality()
        assert schema_manifest["wikiReview"] == manifest["wikiReview"]
        assert schema_manifest["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        sample_runbook = json.loads(Path(summary["artifacts"]["sampleRunbook"]).read_text(encoding="utf-8"))
        sample_bundle = json.loads(Path(summary["artifacts"]["sampleEvidenceBundle"]).read_text(encoding="utf-8"))
        sample_template = json.loads(Path(sample_bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert sample_runbook[key] == manifest[key]
            assert sample_runbook["redactedEvidenceTemplate"][key] == manifest[key]
            assert sample_bundle[key] == manifest[key]
            assert sample_template[key] == manifest[key]


if __name__ == "__main__":
    test_prepare_schema_manifest_sample_outputs_ready_runbook()
    test_prepare_schema_manifest_sample_refreshes_source_status()
    test_prepare_schema_manifest_sample_merges_existing_upload_readiness()
    test_prepare_schema_manifest_sample_preserves_content_quality_warning()
    print("schema manifest sample preparation regression tests passed.")
