#!/usr/bin/env python3
"""Regression tests for forms/media/settings evidence bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_forms_media_settings_evidence_bundle import build_bundle, validate_bundle
from test_prepare_source_next_stage import status_at_forms_media_settings, write_status


def test_forms_media_settings_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_forms_media_settings(root)
        status_path = write_status(root, status)
        bundle = build_bundle(
            status=status,
            status_path=status_path,
            output_dir=root / "forms-media-settings-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["kind"] == "allincms_forms_media_settings_evidence_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["sourceExecutionStatus"] == status_path
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidencePath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_forms_media_settings_evidence"
        assert template["sourceExecutionStatus"] == status_path
        assert template["remoteMutationsPerformed"] is False
        assert template["siteInfoFieldCount"] == 0
        assert template["formCount"] == 0
        assert template["mediaCount"] == 0
        assert template["verifiedCounts"] == {"siteInfoFieldCount": 0, "formCount": 0, "mediaCount": 0}
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert "apply_forms_media_settings.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")


def test_forms_media_settings_evidence_bundle_preserves_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_forms_media_settings(root)
        status_path = write_status(root, status)
        bundle = build_bundle(
            status=status,
            status_path=status_path,
            output_dir=root / "forms-media-settings-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key in ("contentGoalCoverage", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert bundle[key] == status[key]
        assert bundle["contentCounts"] == status["contentQualityReview"]["contentCounts"]
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in ("contentGoalCoverage", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert template[key] == status[key]
        assert template["contentCounts"] == status["contentQualityReview"]["contentCounts"]


def test_forms_media_settings_evidence_bundle_rejects_wrong_stage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_forms_media_settings(root)
        status["currentStage"] = "batch_upload"
        try:
            build_bundle(
                status=status,
                status_path=str(root / "source-execution-status.json"),
                output_dir=root / "forms-media-settings-evidence-bundle",
            )
        except ValueError as exc:
            assert "forms_media_settings" in str(exc)
        else:
            raise AssertionError("bundle should reject a non-forms_media_settings stage")


def test_forms_media_settings_evidence_bundle_rejects_missing_counts_with_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_forms_media_settings(root)
        del status["contentQualityReview"]["contentCounts"]
        del status["contentGoalCoverage"]["counts"]
        bundle = build_bundle(
            status=status,
            status_path=str(root / "source-execution-status.json"),
            output_dir=root / "forms-media-settings-evidence-bundle",
        )
        assert "contentCounts is required when source context is present" in validate_bundle(bundle)


if __name__ == "__main__":
    test_forms_media_settings_evidence_bundle_builds()
    test_forms_media_settings_evidence_bundle_preserves_source_context()
    test_forms_media_settings_evidence_bundle_rejects_wrong_stage()
    test_forms_media_settings_evidence_bundle_rejects_missing_counts_with_source_context()
    print("forms/media/settings evidence bundle regression tests passed.")
