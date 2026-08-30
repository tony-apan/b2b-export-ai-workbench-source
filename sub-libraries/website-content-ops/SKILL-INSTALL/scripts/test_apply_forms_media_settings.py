#!/usr/bin/env python3
"""Regression tests for applying forms/media/settings evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_forms_media_settings import build
from test_summarize_source_execution_status import (
    batch_validation,
    confirmation,
    confirmation_decision_matrix,
    created_site_binding,
    created_site_submitted_values,
    execution_plan,
    forms_media_settings,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    sample_evidence,
    schema_capture_handoff,
    upload_readiness,
    wiki_review,
)
from test_validate_source_run_acceptance import content_counts


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "draftManifestStatus": {
            "products": {"itemCount": 1, "schemaVerified": False},
            "posts": {"itemCount": 1, "schemaVerified": False},
        },
    }


def invalid_missing_deferral() -> dict:
    data = forms_media_settings()
    data["mediaVerified"] = False
    data["trackingRecorded"] = False
    data["deferrals"] = [{"module": "tracking", "reason": "tracking ID was not supplied by the user"}]
    return data


def sensitive_evidence() -> dict:
    data = forms_media_settings()
    data["proof"] = {"request": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz"}
    return data


def base_args(root: Path, evidence: dict) -> argparse.Namespace:
    shared_wiki_review = wiki_review(root)
    evidence = {
        **evidence,
        "wikiReview": evidence.get("wikiReview", shared_wiki_review),
        "createdSiteSubmittedValues": evidence.get("createdSiteSubmittedValues", created_site_submitted_values()),
    }
    evidence = {
        **evidence,
        "contentCounts": evidence.get("contentCounts", content_counts()),
        "confirmationDecisionMatrix": evidence.get("confirmationDecisionMatrix", confirmation_decision_matrix()),
    }
    package_path = write_json(root / "package.json", package())
    review_packet_data = review_packet(package_path)
    review_packet_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    review_packet_data["contentCounts"] = content_counts()
    review_path = write_json(root / "review-packet.json", review_packet_data)
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    confirmation_data["wikiReview"] = shared_wiki_review
    confirmation_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    confirmation_data["contentCounts"] = content_counts()
    plan_data = execution_plan()
    plan_data["wikiReview"] = shared_wiki_review
    plan_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    plan_data["contentCounts"] = content_counts()
    artifact_readiness_data = artifact_readiness()
    artifact_readiness_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    artifact_readiness_data["contentCounts"] = content_counts()
    binding_data = created_site_binding()
    binding_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    binding_data["contentCounts"] = content_counts()
    binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    schema_handoff_data = schema_capture_handoff()
    schema_handoff_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    return argparse.Namespace(
        forms_media_settings_evidence=write_json(root / "forms-media-settings.json", evidence),
        package=package_path,
        review_packet="",
        confirmation=write_json(root / "confirmation.json", confirmation_data),
        execution_plan=write_json(root / "execution-plan.json", plan_data),
        artifact_readiness=write_json(root / "artifact-readiness.json", artifact_readiness_data),
        create_site_handoff="",
        created_site_binding=write_json(root / "created-site-binding.json", binding_data),
        pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
        pages_site_info_evidence="",
        pages_site_info_validation=write_json(root / "pages-site-info-validation.json", pages_site_info_validation()),
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff=write_json(root / "schema-capture-handoff.json", schema_handoff_data),
        upload_readiness=write_json(root / "upload-readiness.json", upload_readiness()),
        sample_evidence=[
            write_json(root / "products-sample-evidence.json", sample_evidence("products")),
            write_json(root / "posts-sample-evidence.json", sample_evidence("posts")),
        ],
        batch_evidence="",
        batch_validation=[
            write_json(root / "products-batch-validation.json", batch_validation("products")),
            write_json(root / "posts-batch-validation.json", batch_validation("posts")),
        ],
        launch_acceptance="",
        output_dir=str(root / "apply-forms-media-settings"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_forms_media_settings_advances_to_launch_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, forms_media_settings()))
        assert summary["validationValid"] is True
        assert summary["contentCounts"] == content_counts()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "launch_acceptance"
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["forms_media_settings"]["status"] == "passed"
        assert status["currentStage"] == "launch_acceptance", status
        validation = json.loads(Path(summary["artifacts"]["formsMediaSettingsValidation"]).read_text(encoding="utf-8"))
        assert validation["launchPrerequisiteSatisfied"] is True


def test_apply_forms_media_settings_blocks_missing_deferral() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, invalid_missing_deferral()))
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_forms_media_settings_evidence"
        assert any("media" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "forms_media_settings", status


def test_apply_forms_media_settings_rejects_sensitive_material() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, sensitive_evidence()))
        assert summary["validationValid"] is False
        assert any("sensitive" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_missing_wiki_review_for_source_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["wikiReview"] = None
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is True
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "source_package", status
        assert any("wikiReview mismatch" in issue or "wikiReview" in issue for issue in status["wikiReviewIssues"])


def test_apply_forms_media_settings_blocks_wiki_review_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        drift = wiki_review(root)
        drift["sourceWiki"] = str(root / "other-source-wiki.json")
        evidence["wikiReview"] = drift
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("wikiReview mismatch" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_decision_matrix_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["confirmationDecisionMatrix"] = [
            {**confirmation_decision_matrix()[0], "decision": "defer", "deferDecision": "changed"}
        ]
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("confirmationDecisionMatrix mismatch" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_content_counts_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["contentCounts"] = {**content_counts(), "products": 3}
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("contentCounts mismatch" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_source_identity_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["sourcePackageSha256"] = "c" * 64
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("sourcePackageSha256/sourceReviewPacketSha256 mismatch" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["createdSiteSubmittedValues"] = {
            "name": "Changed Site",
            "description": "Example description.",
        }
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("createdSiteSubmittedValues mismatch" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_missing_content_counts_when_source_has_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["contentCounts"] = None
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("contentCounts is required" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_verified_forms_without_positive_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence.pop("formCount", None)
        evidence["verifiedCounts"] = {"mediaCount": 0}
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("formsVerified=true requires formCount" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])

        evidence = forms_media_settings()
        evidence["formCount"] = 0
        evidence["verifiedCounts"] = {"formCount": 0, "mediaCount": 0}
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("formsVerified=true requires a positive form count" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_verified_site_info_without_positive_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["siteInfoVerified"] = True
        evidence.pop("siteInfoFieldCount", None)
        evidence["verifiedCounts"] = {"formCount": 1, "mediaCount": 0}
        summary = build(base_args(root, evidence=evidence))
        assert summary["readyForNextStage"] == "blocked_forms_media_settings_evidence"
        assert any("siteInfoVerified=true requires siteInfoFieldCount" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])

        evidence = forms_media_settings()
        evidence["siteInfoVerified"] = True
        evidence["siteInfoFieldCount"] = 0
        evidence["verifiedCounts"] = {"siteInfoFieldCount": 0, "formCount": 1, "mediaCount": 0}
        summary = build(base_args(root, evidence=evidence))
        assert summary["readyForNextStage"] == "blocked_forms_media_settings_evidence"
        assert any("siteInfoVerified=true requires a positive site-info field count" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


def test_apply_forms_media_settings_blocks_verified_media_without_positive_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = forms_media_settings()
        evidence["mediaVerified"] = True
        evidence.pop("mediaCount", None)
        evidence["verifiedCounts"] = {"formCount": 1}
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("mediaVerified=true requires mediaCount" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])

        evidence = forms_media_settings()
        evidence["mediaVerified"] = True
        evidence["mediaCount"] = 0
        evidence["verifiedCounts"] = {"formCount": 1, "mediaCount": 0}
        summary = build(base_args(root, evidence))
        assert summary["validationValid"] is False
        assert any("mediaVerified=true requires a positive media count" in issue for issue in summary["validation"]["formsMediaSettingsIssues"])


if __name__ == "__main__":
    test_apply_forms_media_settings_advances_to_launch_acceptance()
    test_apply_forms_media_settings_blocks_missing_deferral()
    test_apply_forms_media_settings_rejects_sensitive_material()
    test_apply_forms_media_settings_blocks_missing_wiki_review_for_source_run()
    test_apply_forms_media_settings_blocks_wiki_review_drift()
    test_apply_forms_media_settings_blocks_decision_matrix_drift()
    test_apply_forms_media_settings_blocks_content_counts_drift()
    test_apply_forms_media_settings_blocks_source_identity_drift()
    test_apply_forms_media_settings_blocks_created_site_submitted_value_drift()
    test_apply_forms_media_settings_blocks_missing_content_counts_when_source_has_counts()
    test_apply_forms_media_settings_blocks_verified_forms_without_positive_count()
    test_apply_forms_media_settings_blocks_verified_site_info_without_positive_count()
    test_apply_forms_media_settings_blocks_verified_media_without_positive_count()
    print("apply forms/media/settings regression tests passed.")
