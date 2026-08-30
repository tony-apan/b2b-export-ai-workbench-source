#!/usr/bin/env python3
"""Regression tests for launch acceptance inputs bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_launch_acceptance_inputs_bundle import build_bundle, validate_bundle, validate_inputs
from test_manifest_sample_upload import content_goal_overages, created_site_submitted_values, overage_quality
from test_prepare_source_next_stage import status_at_launch_acceptance, write_status


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def test_launch_acceptance_inputs_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_launch_acceptance(root)
        status_path = write_status(root, status)
        bundle = build_bundle(
            status=status,
            status_path=status_path,
            output_dir=root / "launch-acceptance-inputs-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["kind"] == "allincms_launch_acceptance_inputs_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["sourceExecutionStatus"] == status_path
        assert "contentGoalOverages" not in bundle
        assert Path(bundle["inputsTemplate"]).exists()
        assert Path(bundle["filledInputsPath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["inputsTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_launch_acceptance_inputs"
        assert template["sourceExecutionStatus"] == status_path
        assert "contentGoalOverages" not in template
        assert template["formsMediaSettings"].endswith("forms-media-settings.json")
        filled_template = json.loads(Path(bundle["filledInputsPath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        apply_command = Path(bundle["applyCommand"]).read_text(encoding="utf-8")
        assert "apply_launch_acceptance.py" in apply_command
        assert "--sample-evidence <from launch-acceptance-inputs.filled.json:sampleEvidence[]>" in apply_command


def test_launch_acceptance_inputs_bundle_preserves_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_launch_acceptance(root)
        status["createdSiteSubmittedValues"] = created_site_submitted_values()
        status["contentQualityReview"] = overage_quality()
        status["contentGoalOverages"] = content_goal_overages()
        status_path = write_status(root, status)
        bundle = build_bundle(
            status=status,
            status_path=status_path,
            output_dir=root / "launch-acceptance-inputs-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key in (
            "contentGoalCoverage",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
            "createdSiteSubmittedValues",
        ):
            assert bundle[key] == status[key]
        assert bundle["contentCounts"] == status["contentQualityReview"]["contentCounts"]
        template = json.loads(Path(bundle["inputsTemplate"]).read_text(encoding="utf-8"))
        for key in (
            "contentGoalCoverage",
            "contentQualityReview",
            "contentGoalOverages",
            "wikiReview",
            "confirmationDecisionMatrix",
            "createdSiteSubmittedValues",
        ):
            assert template[key] == status[key]
        assert template["contentCounts"] == status["contentQualityReview"]["contentCounts"]


def test_launch_acceptance_inputs_bundle_rejects_wrong_stage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_launch_acceptance(root)
        status["currentStage"] = "forms_media_settings"
        try:
            build_bundle(
                status=status,
                status_path=str(root / "source-execution-status.json"),
                output_dir=root / "launch-acceptance-inputs-bundle",
            )
        except ValueError as exc:
            assert "launch_acceptance" in str(exc)
        else:
            raise AssertionError("bundle should reject a non-launch_acceptance stage")


def test_launch_acceptance_inputs_validation_requires_final_inputs() -> None:
    inputs = {
        "kind": "allincms_launch_acceptance_inputs",
        "runEvidence": "/tmp/run-evidence.json",
        "moduleCoverage": "/tmp/module-coverage.json",
        "finalFrontendAudit": "/tmp/final-frontend-audit.json",
        "cleanupEvidence": "/tmp/cleanup-evidence.json",
        "formsMediaSettings": "/tmp/forms-media-settings.json",
        "roundCloseout": "",
        "autoFinalCloseout": True,
        "finalCloseoutSedimentation": "updated",
        "finalCloseoutSedimentationNote": "Recorded final launch proof.",
        "uploadReadiness": ["/tmp/upload-readiness.json"],
        "sampleEvidence": ["/tmp/products-sample.json"],
        "batchValidation": ["/tmp/products-batch-validation.json"],
        "package": "/tmp/package.json",
        "confirmation": "/tmp/confirmation.json",
        "executionPlan": "/tmp/execution-plan.json",
        "artifactReadiness": "/tmp/artifact-readiness.json",
        "createdSiteBinding": "/tmp/created-site-binding.json",
    }
    assert not validate_inputs(inputs)
    inputs["createdSiteSubmittedValues"] = created_site_submitted_values()
    inputs["sourcePackageSha256"] = "a" * 64
    inputs["sourceReviewPacketSha256"] = "b" * 64
    inputs["contentGoalCoverage"] = {"complete": True}
    inputs["contentCounts"] = {"pages": 1, "products": 1, "posts": 0}
    inputs["contentQualityReview"] = overage_quality()
    inputs["contentGoalOverages"] = content_goal_overages()
    inputs["wikiReview"] = {"sourceWikiMarkdownIndex": "/tmp/wiki/index.md"}
    inputs["confirmationDecisionMatrix"] = [
        {"field": "siteProposal.siteName", "decision": "accept", "blocksRemoteMutation": False}
    ]
    assert not validate_inputs(inputs)
    drifted_overages = json.loads(json.dumps(inputs))
    drifted_overages["contentGoalOverages"]["details"].pop("posts")
    assert (
        "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts"
        in validate_inputs(drifted_overages)
    )
    bad_submitted = dict(inputs)
    bad_submitted["createdSiteSubmittedValues"] = {"name": "", "description": "Example"}
    assert "createdSiteSubmittedValues.name must be a non-empty string" in validate_inputs(bad_submitted)
    bad = dict(inputs)
    bad["finalFrontendAudit"] = ""
    assert "finalFrontendAudit is required" in validate_inputs(bad)


def test_launch_acceptance_inputs_validation_rejects_placeholder_paths() -> None:
    inputs = {
        "kind": "allincms_launch_acceptance_inputs",
        "runEvidence": "/tmp/run-evidence.json",
        "moduleCoverage": "/tmp/module-coverage.json",
        "finalFrontendAudit": "/tmp/final-frontend-audit.json",
        "cleanupEvidence": "/tmp/cleanup-evidence.json",
        "formsMediaSettings": "/tmp/forms-media-settings.json",
        "roundCloseout": "",
        "autoFinalCloseout": True,
        "finalCloseoutSedimentation": "updated",
        "finalCloseoutSedimentationNote": "Recorded final launch proof.",
        "uploadReadiness": ["/tmp/upload-readiness.json"],
        "sampleEvidence": ["/tmp/products-sample.json"],
        "batchValidation": ["/tmp/products-batch-validation.json"],
        "package": "/tmp/package.json",
        "confirmation": "/tmp/confirmation.json",
        "executionPlan": "/tmp/execution-plan.json",
        "artifactReadiness": "/tmp/artifact-readiness.json",
        "createdSiteBinding": "/tmp/created-site-binding.json",
    }
    bad = dict(inputs)
    bad["runEvidence"] = "<final-run-evidence.json>"
    bad["uploadReadiness"] = ["<upload-readiness.json>"]
    bad["package"] = "<source-site-package.json>"
    issues = validate_inputs(bad)
    assert "runEvidence must be a concrete path, not a placeholder" in issues
    assert "uploadReadiness[0] must be a concrete path, not a placeholder" in issues
    assert "package must be a concrete path, not a placeholder" in issues


def test_launch_acceptance_inputs_validation_requires_per_content_type_sample_and_batch_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        products_sample = write_json(root / "products-sample.json", {"contentType": "products"})
        products_sample_2 = write_json(root / "products-sample-2.json", {"contentType": "products"})
        posts_sample = write_json(root / "posts-sample.json", {"contentType": "posts"})
        products_batch = write_json(root / "products-batch-validation.json", {"contentType": "products"})
        products_batch_2 = write_json(root / "products-batch-validation-2.json", {"contentType": "products"})
        posts_batch = write_json(root / "posts-batch-validation.json", {"contentType": "posts"})
        inputs = {
            "kind": "allincms_launch_acceptance_inputs",
            "runEvidence": "/tmp/run-evidence.json",
            "moduleCoverage": "/tmp/module-coverage.json",
            "finalFrontendAudit": "/tmp/final-frontend-audit.json",
            "cleanupEvidence": "/tmp/cleanup-evidence.json",
            "formsMediaSettings": "/tmp/forms-media-settings.json",
            "roundCloseout": "",
            "autoFinalCloseout": True,
            "finalCloseoutSedimentation": "updated",
            "finalCloseoutSedimentationNote": "Recorded final launch proof.",
            "uploadReadiness": ["/tmp/upload-readiness.json"],
            "sampleEvidence": [products_sample],
            "batchValidation": [products_batch],
            "package": "/tmp/package.json",
            "confirmation": "/tmp/confirmation.json",
            "executionPlan": "/tmp/execution-plan.json",
            "artifactReadiness": "/tmp/artifact-readiness.json",
            "createdSiteBinding": "/tmp/created-site-binding.json",
            "sourcePackageSha256": "a" * 64,
            "sourceReviewPacketSha256": "b" * 64,
            "contentGoalCoverage": {"complete": True},
            "contentCounts": {"pages": 3, "products": 2, "posts": 3},
            "contentQualityReview": {"warnings": [], "reviewRequired": False},
            "wikiReview": {"sourceWikiMarkdownIndex": "/tmp/wiki/index.md"},
            "confirmationDecisionMatrix": [{"field": "siteName", "decision": "accept", "blocksRemoteMutation": False}],
        }
        issues = validate_inputs(inputs)
        assert "sampleEvidence must include at least 2 paths for the planned products/posts content types" in issues
        assert "batchValidation must include at least 2 paths for the planned products/posts content types" in issues
        inputs["sampleEvidence"] = [products_sample, products_sample_2]
        inputs["batchValidation"] = [products_batch, products_batch_2]
        issues = validate_inputs(inputs)
        assert "sampleEvidence missing contentType coverage: posts" in issues
        assert "batchValidation missing contentType coverage: posts" in issues
        inputs["sampleEvidence"] = [products_sample, posts_sample]
        inputs["batchValidation"] = [products_batch, posts_batch]
        assert not validate_inputs(inputs)


if __name__ == "__main__":
    test_launch_acceptance_inputs_bundle_builds()
    test_launch_acceptance_inputs_bundle_preserves_source_context()
    test_launch_acceptance_inputs_bundle_rejects_wrong_stage()
    test_launch_acceptance_inputs_validation_requires_final_inputs()
    test_launch_acceptance_inputs_validation_rejects_placeholder_paths()
    test_launch_acceptance_inputs_validation_requires_per_content_type_sample_and_batch_paths()
    print("launch acceptance inputs bundle regression tests passed.")
