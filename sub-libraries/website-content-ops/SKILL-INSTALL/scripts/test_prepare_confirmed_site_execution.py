#!/usr/bin/env python3
"""Regression tests for confirmed site execution preparation."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
import os
import sys

from make_create_preflight_evidence import build_evidence, parse_observed_fields
from make_source_review_objective_coverage import build_coverage
from prepare_confirmed_site_execution import build
from test_source_confirmation_execution_plan import make_package, write_json
from make_source_package_review_packet import build_review_packet
import json


def prepare_package_and_review(root: Path) -> tuple[Path, Path]:
    package_path = make_package(root)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    review = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
    review_path = root / "source-package-review-packet.json"
    write_json(review_path, review)
    return package_path, review_path


def make_preflight(root: Path) -> Path:
    preflight = build_evidence(
        ["abc123demo"],
        parse_observed_fields(
            "observed create site entry button 创建站点;observed dialog title 创建站点;"
            "name input;description textarea;submit 创建;close Close"
        ),
        dialog_closed_verified=True,
        repo_check_passed=True,
        repo_check_note=None,
        generated_at="2026-07-01T00:00:00+00:00",
        site_key_evidence={"abc123demo": "backend URL https://workspace.laicms.com/abc123demo/dashboard"},
    )
    preflight_path = root / "create-preflight.json"
    write_json(preflight_path, preflight)
    return preflight_path


def base_args(root: Path, package_path: Path, review_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        package=str(package_path),
        review_packet=str(review_path),
        user_confirmation_text="User confirms the generated source package for a temporary demo site.",
        output_dir=str(root / "execution"),
        target_mode="new_site",
        site_key="",
        frontend_base_url="",
        accepted_fields="",
        accepted_deferral=[
            "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
            "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
            "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
            "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
        ],
        notes="local test",
        create_preflight="",
        create_authorization_output=str(root / "authorization-create-site.json"),
        fail_if_no_create_handoff=False,
        json=False,
    )


def test_prepares_confirmation_plan_artifacts_without_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        summary = build(base_args(root, package_path, review_path))
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["isUserAuthorization"] is False
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        assert summary["contentGoalOverages"]["present"] is False
        assert Path(summary["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        assert Path(summary["artifacts"]["confirmation"]).exists()
        assert Path(summary["artifacts"]["executionPlan"]).exists()
        assert Path(summary["artifacts"]["artifactReadiness"]).exists()
        assert Path(summary["artifacts"]["createSitePreflightBrief"]).exists()
        assert Path(summary["artifacts"]["createSitePreflightBriefValidation"]).exists()
        assert summary["artifacts"]["createSitePreflightTarget"].endswith("create-site-preflight.json")
        assert summary["artifacts"]["createdSiteEvidenceBrief"] == ""
        assert summary["artifacts"]["createdSiteEvidenceTarget"] == ""
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["validation"]["createSitePreflightBriefPrepared"] is True
        assert summary["validation"]["createSitePreflightBriefIssues"] == []
        assert summary["validation"]["createdSiteEvidenceBriefPrepared"] is False
        assert summary["sourceNextStage"]["currentStage"] == "create_site_handoff"
        assert summary["artifacts"]["createSiteHandoff"] == ""
        assert summary["sourceNextStage"]["apiSessionPreflightRequired"] is True
        assert summary["sourceNextStage"]["apiSessionPreflight"]["visibleNavigationAllowed"] is False
        assert summary["sourceNextStage"]["apiSessionPreflight"]["loginNavigationGate"] == "api_result_login_required_only"
        next_stage = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert next_stage["needsCreateSitePreflight"] is True
        assert next_stage["browserWorkRequired"] is False
        assert next_stage["apiSessionPreflightRequired"] is True
        assert next_stage["apiSessionPreflight"]["urlTemplate"] == "https://workspace.laicms.com/sites?_rsc={nonce}"
        assert next_stage["apiSessionPreflight"]["visibleNavigationAllowed"] is False
        assert next_stage["mode"] == "local_helper_prepares_or_applies_stage"
        assert "preflight" in next_stage["blocker"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert "forms_media_settings" in status["stages"]
        assert status["currentStage"] == "create_site_handoff", status


def test_prepares_confirmation_with_review_packet_suggestions_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        args = base_args(root, package_path, review_path)
        args.accepted_fields = ""
        args.accepted_deferral = []
        summary = build(args)
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        confirmation = json.loads(Path(summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        assert set(review["suggestedAcceptedFields"]).issubset(set(confirmation["acceptedFields"]))
        assert {item["field"] for item in review["suggestedAcceptedDeferrals"]}.issubset(
            {item["field"] for item in confirmation["acceptedDeferrals"]}
        )
        assert all(row["decision"] in {"accept", "defer"} for row in confirmation["confirmationDecisionMatrix"])


def test_confirmation_accepts_equivalent_tmp_private_tmp_paths() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        real_package_path = os.path.realpath(package_path)
        if str(package_path) == real_package_path:
            return
        review["sourcePackage"] = real_package_path
        write_json(review_path, review)
        args = base_args(root, package_path, review_path)
        args.accepted_fields = ""
        args.accepted_deferral = []
        summary = build(args)
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        confirmation = json.loads(Path(summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        assert confirmation["sourcePackage"] == str(package_path)


def test_prepares_create_site_handoff_with_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        args = base_args(root, package_path, review_path)
        args.create_preflight = str(make_preflight(root))
        summary = build(args)
        assert summary["readyForBrowserStage"] == "create_site_handoff_ready"
        assert summary["artifacts"]["createSitePreflightBrief"] == ""
        assert summary["artifacts"]["createSitePreflightBriefValidation"] == ""
        assert summary["artifacts"]["createSitePreflightTarget"] == ""
        assert summary["artifacts"]["createSiteHandoff"]
        assert Path(summary["artifacts"]["createSiteHandoffValidation"]).exists()
        assert Path(summary["artifacts"]["createSiteRunbook"]).exists()
        assert Path(summary["artifacts"]["createSiteRunbookValidation"]).exists()
        assert Path(summary["artifacts"]["createdSiteEvidenceBrief"]).exists()
        assert Path(summary["artifacts"]["createdSiteEvidenceBundle"]).exists()
        assert Path(summary["artifacts"]["createdSiteEvidenceBundleValidation"]).exists()
        assert summary["artifacts"]["createdSiteEvidenceTarget"].endswith("created-site-evidence.json")
        assert summary["validation"]["createSiteHandoffValidationIssues"] == []
        assert summary["validation"]["createSiteRunbookValidationIssues"] == []
        assert summary["validation"]["createdSiteEvidenceBundleValidationIssues"] == []
        assert summary["validation"]["createSiteRunbookPrepared"] is True
        assert summary["validation"]["createdSiteEvidenceBriefPrepared"] is True
        assert summary["validation"]["createdSiteEvidenceBundlePrepared"] is True
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "created_site_binding"
        handoff_path = Path(summary["artifacts"]["createSiteHandoff"])
        assert handoff_path.exists()
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        assert handoff["preparedOnly"] is True
        assert handoff["remoteMutationsPerformed"] is False
        assert handoff["contentQualityReview"]["warnings"] == []
        assert handoff["wikiReview"] == summary["wikiReview"]
        assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
        handoff_validation = json.loads(Path(summary["artifacts"]["createSiteHandoffValidation"]).read_text(encoding="utf-8"))
        assert handoff_validation["kind"] == "allincms_confirmed_create_site_handoff_validation"
        assert handoff_validation["valid"] is True
        assert handoff_validation["handoff"] == str(handoff_path)
        runbook = json.loads(Path(summary["artifacts"]["createSiteRunbook"]).read_text(encoding="utf-8"))
        assert runbook["kind"] == "allincms_create_site_browser_runbook"
        assert runbook["browserStepsExecutable"] is False
        assert runbook["sourceCreateSiteHandoff"] == str(handoff_path)
        assert runbook["sourcePackageSha256"] == handoff["sourcePackageSha256"]
        assert runbook["sourceReviewPacketSha256"] == handoff["sourceReviewPacketSha256"]
        assert runbook["authorizationRecord"] == str(root / "authorization-create-site.json")
        runbook_validation = json.loads(Path(summary["artifacts"]["createSiteRunbookValidation"]).read_text(encoding="utf-8"))
        assert runbook_validation["kind"] == "allincms_create_site_browser_runbook_validation"
        assert runbook_validation["valid"] is True
        assert runbook_validation["runbook"] == summary["artifacts"]["createSiteRunbook"]
        bundle = json.loads(Path(summary["artifacts"]["createdSiteEvidenceBundle"]).read_text(encoding="utf-8"))
        assert bundle["kind"] == "allincms_created_site_evidence_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["runbook"] == summary["artifacts"]["createSiteRunbook"]
        assert bundle["createdSiteEvidenceBrief"] == summary["artifacts"]["createdSiteEvidenceBrief"]
        bundle_validation = json.loads(Path(summary["artifacts"]["createdSiteEvidenceBundleValidation"]).read_text(encoding="utf-8"))
        assert bundle_validation["kind"] == "allincms_created_site_evidence_bundle_validation"
        assert bundle_validation["valid"] is True
        assert bundle_validation["bundle"] == summary["artifacts"]["createdSiteEvidenceBundle"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["create_site_handoff"]["status"] == "passed"
        assert "forms_media_settings" in status["stages"]


def make_review_objective_coverage(root: Path, package_path: Path, review_path: Path) -> Path:
    package = json.loads(package_path.read_text(encoding="utf-8"))
    review_packet = json.loads(review_path.read_text(encoding="utf-8"))
    coverage = build_coverage(
        review_packet,
        review_packet_path=str(review_path),
        package=package,
        package_path=str(package_path),
        objective="source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
    )
    coverage_path = root / "source-review-objective-coverage.json"
    write_json(coverage_path, coverage)
    return coverage_path


def test_prepares_execution_carries_source_review_objective_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        coverage_path = make_review_objective_coverage(root, package_path, review_path)
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        args = base_args(root, package_path, review_path)
        args.source_review_objective_coverage = str(coverage_path)
        summary = build(args)
        assert summary["sourceReviewObjectiveCoverage"] == coverage
        confirmation = json.loads(Path(summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        plan = json.loads(Path(summary["artifacts"]["executionPlan"]).read_text(encoding="utf-8"))
        readiness = json.loads(Path(summary["artifacts"]["artifactReadiness"]).read_text(encoding="utf-8"))
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert confirmation["sourceReviewObjectiveCoverage"] == coverage
        assert plan["sourceReviewObjectiveCoverage"] == coverage
        assert readiness["sourceReviewObjectiveCoverage"] == coverage
        assert status["sourceReviewObjectiveCoverage"] == coverage
        assert status["sourceReviewObjectiveCoverageIssues"] == []
        assert next_stage["sourceReviewObjectiveCoverage"] == coverage
        assert coverage["reviewComplete"] is True
        assert coverage["complete"] is False
        assert coverage["remoteMutationAllowed"] is False


def test_prepares_execution_without_coverage_omits_field() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path = prepare_package_and_review(root)
        summary = build(base_args(root, package_path, review_path))
        assert "sourceReviewObjectiveCoverage" not in summary
        confirmation = json.loads(Path(summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        assert "sourceReviewObjectiveCoverage" not in confirmation
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert "sourceReviewObjectiveCoverage" not in status
        assert status["sourceReviewObjectiveCoverageIssues"] == []


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("prepare confirmed site execution regression tests passed.")
