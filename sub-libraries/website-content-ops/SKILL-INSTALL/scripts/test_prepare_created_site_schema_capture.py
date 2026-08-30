#!/usr/bin/env python3
"""Regression tests for created-site schema-capture preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from export_confirmed_site_artifacts import build_artifacts
from build_confirmed_site_execution_plan import build_plan
from make_source_package_confirmation import build_confirmation
from make_source_package_review_packet import build_review_packet
from prepare_created_site_schema_capture import build
from test_bind_created_site_to_artifacts import created_site_evidence, existing_site_evidence
from test_export_confirmed_site_artifacts import prepare_confirmed_plan


SOURCE_IDENTITY_KEYS = ("sourcePackageSha256", "sourceReviewPacketSha256")
CREATED_SITE_SUBMITTED_VALUES = {
    "name": "Example Demo",
    "description": "Example demo site for source-backed product publishing and article planning.",
}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_artifacts(root: Path) -> tuple[Path, Path, Path, Path]:
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
    return package_path, confirmation_path, plan_path, readiness_path


def prepare_existing_site_artifacts(root: Path, site_key: str = "newsite123") -> tuple[Path, Path, Path, Path]:
    package_path, confirmation_path, _ = prepare_confirmed_plan(root)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["targetMode"] = "existing_site"
    write_json(package_path, package)
    review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
    review_packet_path = root / "source-package-review-packet.existing-site.json"
    write_json(review_packet_path, review_packet)
    confirmation = build_confirmation(
        argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated package for updating an existing temporary demo site.",
            accepted_fields="",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="existing site test",
            output=str(root / "confirmation.existing-site.json"),
            json=False,
        )
    )
    confirmation_path = root / "confirmation.existing-site.json"
    write_json(confirmation_path, confirmation)
    plan = build_plan(
        argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            target_mode="existing_site",
            site_key=site_key,
            output=str(root / "execution-plan.existing-site.json"),
            json=False,
        )
    )
    plan_path = root / "execution-plan.existing-site.json"
    write_json(plan_path, plan)
    readiness = build_artifacts(
        argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            execution_plan=str(plan_path),
            site_key=site_key,
            frontend_base_url=f"https://{site_key}.web.allincms.com",
            output_dir=str(root / "artifacts-existing-site"),
            json=False,
        )
    )
    readiness_path = root / "artifacts-existing-site" / "artifact-readiness.json"
    write_json(readiness_path, readiness)
    return package_path, confirmation_path, plan_path, readiness_path


def test_created_site_schema_capture_preparation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path, readiness_path = prepare_artifacts(root)
        evidence_path = created_site_evidence(root)
        summary = build(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                package=str(package_path),
                review_packet="",
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                authorization_dir="",
                theme_target="",
                output_dir=str(root / "created-site-schema"),
                json=False,
            )
        )
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentGoalCoverage"]["checks"]["pages"] is True
        assert summary["contentGoalCoverage"]["checks"]["products"] is True
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        assert summary["contentGoalCoverage"]["checks"]["posts"] is True
        assert summary["contentCounts"] == readiness["contentCounts"]
        assert summary["contentCounts"]["navigationItems"] == 3
        assert summary["contentCounts"]["siteInfoFields"] >= 1
        assert summary["createdSiteSubmittedValues"] == CREATED_SITE_SUBMITTED_VALUES
        assert summary["contentQualityReview"]["warnings"] == []
        assert summary["contentQualityReview"]["reviewRequired"] is False
        assert summary["wikiReview"] == readiness["wikiReview"]
        for key in SOURCE_IDENTITY_KEYS:
            assert summary[key] == readiness[key]
        assert Path(summary["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        assert summary["readyForCreateProbeAuthorizationCount"] == 1
        assert summary["blockedByReadonlyPreflightCount"] == 1
        assert "schemaCaptureHandoff" in summary["artifacts"]
        assert "pagesSiteInfoHandoff" in summary["artifacts"]
        assert "pagesSiteInfoEvidenceBundle" in summary["artifacts"]
        assert "taxonomyHandoff" in summary["artifacts"]
        assert "taxonomyEvidenceBundle" in summary["artifacts"]
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "pages_site_info_execution"
        assert Path(summary["artifacts"]["pagesSiteInfoHandoff"]).exists()
        assert Path(summary["artifacts"]["pagesSiteInfoEvidenceBundle"]).exists()
        assert Path(summary["artifacts"]["taxonomyHandoff"]).exists()
        assert Path(summary["artifacts"]["taxonomyEvidenceBundle"]).exists()
        handoff = json.loads(Path(summary["artifacts"]["pagesSiteInfoHandoff"]).read_text(encoding="utf-8"))
        schema_handoff = json.loads(Path(summary["artifacts"]["schemaCaptureHandoff"]).read_text(encoding="utf-8"))
        binding = json.loads(Path(summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        bound_readiness = json.loads(Path(summary["artifacts"]["boundArtifactReadiness"]).read_text(encoding="utf-8"))
        assert binding["contentCounts"] == summary["contentCounts"]
        assert bound_readiness["contentCounts"] == summary["contentCounts"]
        assert binding["createdSiteSubmittedValues"] == summary["createdSiteSubmittedValues"]
        assert bound_readiness["createdSiteSubmittedValues"] == summary["createdSiteSubmittedValues"]
        for key in SOURCE_IDENTITY_KEYS:
            assert binding[key] == summary[key]
            assert bound_readiness[key] == summary[key]
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert handoff[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert handoff[key] == summary[key]
            assert schema_handoff[key] == summary[key]
        assert schema_handoff["createdSiteSubmittedValues"] == summary["createdSiteSubmittedValues"]
        assert handoff["navigation"]["items"]
        assert not handoff["navigation"]["issues"], handoff["navigation"]["issues"]
        bundle = json.loads(Path(summary["artifacts"]["pagesSiteInfoEvidenceBundle"]).read_text(encoding="utf-8"))
        assert bundle["kind"] == "allincms_pages_site_info_evidence_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["handoff"] == summary["artifacts"]["pagesSiteInfoHandoff"]
        assert bundle["pageCount"] == len(handoff["pages"])
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert bundle[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert bundle[key] == summary[key]
        pages_template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert pages_template[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert pages_template[key] == summary[key]
        taxonomy_handoff = json.loads(Path(summary["artifacts"]["taxonomyHandoff"]).read_text(encoding="utf-8"))
        assert taxonomy_handoff["kind"] == "allincms_taxonomy_execution_handoff"
        assert taxonomy_handoff["browserStepsExecutable"] is False
        assert taxonomy_handoff["actions"]
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert taxonomy_handoff[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert taxonomy_handoff[key] == summary[key]
        taxonomy_bundle = json.loads(Path(summary["artifacts"]["taxonomyEvidenceBundle"]).read_text(encoding="utf-8"))
        assert taxonomy_bundle["kind"] == "allincms_taxonomy_evidence_bundle"
        assert taxonomy_bundle["browserStepsExecutable"] is False
        assert taxonomy_bundle["handoff"] == summary["artifacts"]["taxonomyHandoff"]
        assert taxonomy_bundle["actionCount"] == len(taxonomy_handoff["actions"])
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert taxonomy_bundle[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert taxonomy_bundle[key] == summary[key]
        taxonomy_template = json.loads(Path(taxonomy_bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert taxonomy_template["kind"] == "allincms_taxonomy_execution_evidence"
        assert len(taxonomy_template["taxonomyMappings"]) == len(taxonomy_handoff["actions"])
        for key in (
            "createdSiteSubmittedValues",
            "contentGoalCoverage",
            "contentCounts",
            "contentQualityReview",
            "wikiReview",
            "confirmationDecisionMatrix",
        ):
            assert taxonomy_template[key] == summary[key]
        for key in SOURCE_IDENTITY_KEYS:
            assert taxonomy_template[key] == summary[key]
        assert Path(summary["artifacts"]["schemaCaptureProgress"]).exists()
        products_manifest = json.loads(Path(summary["artifacts"]["productsBoundDraftManifest"]).read_text(encoding="utf-8"))
        posts_manifest = json.loads(Path(summary["artifacts"]["postsBoundDraftManifest"]).read_text(encoding="utf-8"))
        assert products_manifest["schemaVerified"] is False
        assert posts_manifest["schemaVerified"] is False
        for key in SOURCE_IDENTITY_KEYS:
            assert products_manifest[key] == summary[key]
            assert posts_manifest[key] == summary[key]
        progress = json.loads(Path(summary["artifacts"]["schemaCaptureProgress"]).read_text(encoding="utf-8"))
        statuses = {item["contentType"]: item["status"] for item in progress["results"]}
        assert statuses["products"] == "ready_for_create_probe"
        assert statuses["posts"] == "blocked_readonly_preflight"
        source_status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert source_status["stages"]["pages_site_info_handoff"]["status"] == "passed"
        assert source_status["stages"]["taxonomy_execution_handoff"]["status"] == "blocked"
        assert source_status["wikiReview"] == summary["wikiReview"]
        for key in SOURCE_IDENTITY_KEYS:
            assert source_status[key] == summary[key]
        assert source_status["wikiReviewIssues"] == []
        assert source_status["taxonomyRequired"] is True
        assert source_status["currentStage"] == "pages_site_info_execution"
        assert "pages/site-info execution evidence missing" in source_status["stages"]["pages_site_info_execution"]["blockers"]
        assert summary["taxonomyStatus"] == "blocked_taxonomy_preflight"
        assert summary["nextAction"] == source_status["nextAction"]


def test_created_site_schema_capture_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path, readiness_path = prepare_artifacts(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] = 0
        package["contentPlan"]["taxonomyPlan"]["postCategories"] = []
        write_json(package_path, package)
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                user_confirmation_text="User confirms the generated package after reviewing quality warnings.",
                accepted_fields="",
                accepted_deferral=[
                    "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                    "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                    "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
                ],
                notes="warning propagation test",
                output=str(root / "confirmation.json"),
                json=False,
            )
        )
        write_json(confirmation_path, confirmation)
        plan = build_plan(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                target_mode="new_site",
                site_key="",
                output=str(root / "execution-plan.json"),
                json=False,
            )
        )
        write_json(plan_path, plan)
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
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        summary = build(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                package=str(package_path),
                review_packet=str(review_packet_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                authorization_dir="",
                theme_target="",
                output_dir=str(root / "created-site-schema"),
                json=False,
            )
        )
        warning = "posts_present_without_post_categories"
        assert warning in summary["contentQualityReview"]["warnings"]
        binding = json.loads(Path(summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        schema_handoff = json.loads(Path(summary["artifacts"]["schemaCaptureHandoff"]).read_text(encoding="utf-8"))
        source_status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert warning in binding["contentQualityReview"]["warnings"]
        assert binding["contentCounts"] == summary["contentCounts"]
        assert warning in schema_handoff["contentQualityReview"]["warnings"]
        assert warning in source_status["contentQualityReview"]["warnings"]
        assert warning in next_stage["contentQualityReview"]["warnings"]
        assert source_status["contentQualityReviewIssues"] == []
        assert summary["wikiReview"] == review_packet["wikiReview"]
        assert binding["wikiReview"] == review_packet["wikiReview"]
        assert schema_handoff["wikiReview"] == review_packet["wikiReview"]
        assert source_status["wikiReview"] == review_packet["wikiReview"]
        assert next_stage["wikiReview"] == review_packet["wikiReview"]
        assert source_status["wikiReviewIssues"] == []


def test_selected_existing_site_schema_capture_preparation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path, readiness_path = prepare_artifacts(root)
        evidence_path = existing_site_evidence(root)
        summary = build(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                package=str(package_path),
                review_packet="",
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                authorization_dir="",
                theme_target="",
                output_dir=str(root / "existing-site-schema"),
                json=False,
            )
        )
        binding = json.loads(Path(summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        bound_readiness = json.loads(Path(summary["artifacts"]["boundArtifactReadiness"]).read_text(encoding="utf-8"))
        assert binding["siteBindingMode"] == "existing_site"
        assert binding["siteCreationStatus"] == "existing_site_selected"
        assert "createdSiteSubmittedValues" not in binding
        assert "createdSiteSubmittedValues" not in summary
        assert bound_readiness["siteBindingMode"] == "existing_site"
        assert summary["readyForCreateProbeAuthorizationCount"] == 1
        assert Path(summary["artifacts"]["pagesSiteInfoHandoff"]).exists()
        assert Path(summary["artifacts"]["taxonomyHandoff"]).exists()
        assert Path(summary["artifacts"]["schemaCaptureHandoff"]).exists()
        source_status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert source_status["stages"]["create_site_handoff"]["status"] == "passed"
        assert source_status["currentStage"] == "created_site_binding"


def test_existing_site_source_execution_schema_capture_preparation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path, readiness_path = prepare_existing_site_artifacts(root)
        evidence_path = existing_site_evidence(root)
        summary = build(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                package=str(package_path),
                review_packet="",
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                authorization_dir="",
                theme_target="",
                output_dir=str(root / "existing-site-source-schema"),
                json=False,
            )
        )
        package = json.loads(package_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        binding = json.loads(Path(summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        bound_readiness = json.loads(Path(summary["artifacts"]["boundArtifactReadiness"]).read_text(encoding="utf-8"))
        source_status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        schema_handoff = json.loads(Path(summary["artifacts"]["schemaCaptureHandoff"]).read_text(encoding="utf-8"))

        assert package["targetMode"] == "existing_site"
        assert plan["targetMode"] == "existing_site"
        assert plan["siteTarget"] == "newsite123"
        assert readiness["siteKey"] == "newsite123"
        assert readiness["frontendBaseUrl"] == "https://newsite123.web.allincms.com"
        assert binding["siteBindingMode"] == "existing_site"
        assert binding["siteCreationStatus"] == "existing_site_selected"
        assert bound_readiness["siteBindingMode"] == "existing_site"
        assert summary["siteKey"] == "newsite123"
        assert summary["frontendBaseUrl"] == "https://newsite123.web.allincms.com"

        for artifact in (summary, binding, bound_readiness, source_status, next_stage, schema_handoff):
            assert "createdSiteSubmittedValues" not in artifact
        assert source_status["targetMode"] == "existing_site"
        assert source_status["createdSiteSubmittedValuesIssues"] == []
        assert source_status["stages"]["create_site_handoff"]["status"] == "passed"
        assert source_status["stages"]["create_site_handoff"]["evidence"] == "existing-site-mode"
        assert source_status["currentStage"] == "pages_site_info_execution"
        assert next_stage["currentStage"] == "pages_site_info_execution"
        assert next_stage["mode"] == "browser_action_or_capture_required"
        assert next_stage["browserWorkRequired"] is True
        assert summary["sourceNextStage"]["currentStage"] == "pages_site_info_execution"
        assert summary["sourceNextStage"]["mode"] == "browser_action_or_capture_required"
        assert summary["sourceNextStage"]["browserWorkRequired"] is True
        assert summary["readyForCreateProbeAuthorizationCount"] == 1
        assert summary["blockedByReadonlyPreflightCount"] == 1


if __name__ == "__main__":
    test_created_site_schema_capture_preparation()
    test_created_site_schema_capture_preserves_content_quality_warning()
    test_selected_existing_site_schema_capture_preparation()
    test_existing_site_source_execution_schema_capture_preparation()
    print("created-site schema-capture preparation regression tests passed.")
