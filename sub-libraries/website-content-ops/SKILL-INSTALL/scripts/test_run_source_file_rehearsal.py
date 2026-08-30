#!/usr/bin/env python3
"""Regression tests for local source-file rehearsal orchestration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from make_create_preflight_evidence import build_evidence, parse_observed_fields
from run_source_file_rehearsal import build
from test_apply_refined_source_wiki import refined_wiki, write_json
from validate_source_file_rehearsal import validate_summary


def wiki_for_rehearsal_inventory() -> dict:
    data = refined_wiki()
    original = "src-example-brief"
    replacement = "src-001"

    def rewrite(value):
        if isinstance(value, str):
            return replacement if value == original else value
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    return rewrite(data)


def base_args(root: Path, source: Path) -> argparse.Namespace:
    return argparse.Namespace(
        sources=[str(source)],
        output_dir=str(root / "rehearsal"),
        recursive=False,
        run_label="source-rehearsal-test",
        site_name="Example Product Demo",
        site_description="A source-backed example site for product buyers and practical product selection.",
        language="en",
        industry="example industry",
        site_key="",
        frontend_base_url="",
        content_types="products,posts,themes/pages,site-info,forms,media,navigation",
        source_types="plain_brief,product_datasheet,website_copy",
        gap_ledger=[],
        resolved_gap_evidence=[],
        max_text_chars=12000,
        max_table_rows=40,
        refined_source_wiki="",
        user_confirmation_text="",
        target_mode="new_site",
        accepted_fields="",
        accepted_deferral=[
            "siteInfo.publicContact|defer_until_real_company_details|Public contact was not supplied.",
            "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company was not supplied.",
            "domains.customDomain|out_of_scope_for_demo|No custom domain for rehearsal.",
            "tracking.trackingCode|out_of_scope_for_demo|No tracking code for rehearsal.",
        ],
        notes="local rehearsal",
        create_preflight="",
        create_authorization_output="",
        auto_draft_refined_source_wiki=False,
        json=False,
    )


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
    return Path(write_json(root / "create-site-preflight.json", preflight))


def refined_target(root: Path) -> Path:
    return root / "rehearsal" / "01-source-prepare" / "source-wiki.refined.json"


def test_rehearsal_stops_at_refinement_without_refined_wiki() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        summary = build(base_args(root, source))
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["reviewReady"] is False
        assert summary["confirmationPrepared"] is False
        assert summary["readyForBrowserStage"] == "needs_source_wiki_refinement"
        assert summary["nextAction"].startswith("refine source wiki")
        assert summary["confirmationReview"]["available"] is False
        assert summary["confirmationReview"]["reviewPacket"] == ""
        assert summary["confirmationBrief"]["status"] == "needs_source_wiki_refinement"
        assert summary["confirmationBrief"]["isRemoteMutationAuthorization"] is False
        assert Path(summary["artifacts"]["sourceConfirmationBrief"]).exists()
        assert Path(summary["artifacts"]["sourceConfirmationBriefMarkdown"]).exists()
        assert Path(summary["artifacts"]["sourceConfirmationBriefValidation"]).exists()
        assert Path(summary["artifacts"]["sourceFileRehearsalValidation"]).exists()
        assert summary["sourceFileRehearsalValidation"]["ok"] is True
        audit = summary["objectiveAudit"]
        assert audit["complete"] is False
        assert audit["reviewReady"] is False
        assert audit["confirmationPrepared"] is False
        assert audit["nextBlockingRequirement"] == "publishable pages/products/posts/site-info package review-ready"
        assert any(item["requirement"] == "source-backed wiki generated" and item["status"] == "proven" for item in audit["checks"])
        source_prepare_summary = Path(summary["artifacts"]["sourcePrepareSummary"])
        assert source_prepare_summary.exists()
        assert json.loads(source_prepare_summary.read_text(encoding="utf-8"))["kind"] == "allincms_prepared_source_site_package"
        assert Path(summary["artifacts"]["sourceExecutionStatus"]).exists()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert Path(summary["artifacts"]["sourceWikiRefinementPlan"]).exists()
        assert Path(summary["artifacts"]["sourceWikiRefinementBrief"]).exists()
        assert summary["artifacts"]["refinedSourceWikiTarget"].endswith("source-wiki.refined.json")
        assert summary["sourcePrepare"]["sourceNextStage"]["currentStage"] in {"review_packet", "source_package"}


def test_rehearsal_with_refined_wiki_reaches_user_confirmation_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        summary = build(args)
        assert summary["reviewReady"] is True, summary
        assert summary["confirmationPrepared"] is False
        assert summary["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert Path(summary["artifacts"]["reviewPacket"]).exists()
        assert Path(summary["artifacts"]["sourceReviewObjectiveCoverage"]).exists()
        review_coverage = json.loads(Path(summary["artifacts"]["sourceReviewObjectiveCoverage"]).read_text(encoding="utf-8"))
        assert review_coverage["kind"] == "allincms_source_review_objective_coverage"
        assert review_coverage["reviewComplete"] is True
        assert review_coverage["complete"] is False
        assert review_coverage["remoteMutationAllowed"] is False
        assert review_coverage["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert review_coverage["missingForReview"] == []
        assert "remote_site_creation_not_started" in review_coverage["missingForFinal"]
        assert summary["sourceReviewObjectiveCoverage"]["json"] == summary["artifacts"]["sourceReviewObjectiveCoverage"]
        assert summary["sourceReviewObjectiveCoverage"]["reviewComplete"] is True
        assert summary["sourceReviewObjectiveCoverage"]["complete"] is False
        assert summary["sourceReviewObjectiveCoverage"]["remoteMutationAllowed"] is False
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        confirmation_review = summary["confirmationReview"]
        assert confirmation_review["available"] is True
        assert summary["confirmationBrief"]["status"] == "waiting_for_user_content_confirmation"
        assert summary["confirmationBrief"]["nextBlockingRequirement"] == "user content-intent confirmation converted to execution artifacts"
        assert Path(summary["confirmationBrief"]["validation"]).exists()
        assert Path(summary["artifacts"]["sourceFileRehearsalValidation"]).exists()
        assert summary["sourceFileRehearsalValidation"]["ok"] is True
        assert Path(summary["artifacts"]["sourceWiki"]).exists()
        assert Path(summary["artifacts"]["sourceWikiMarkdown"]).exists()
        assert Path(summary["artifacts"]["sourceWikiMarkdownIndex"]).exists()
        assert confirmation_review["reviewPacket"] == summary["artifacts"]["reviewPacket"]
        assert confirmation_review["counts"] == review_packet["counts"]
        assert confirmation_review["contentGoalCoverage"] == review_packet["contentGoalCoverage"]
        assert confirmation_review["contentQualityReview"] == review_packet["contentQualityReview"]
        assert confirmation_review["suggestedConfirmationText"] == review_packet["suggestedConfirmationText"]
        assert confirmation_review["confirmationCommandTemplate"] == review_packet["confirmationCommandTemplate"]
        assert confirmation_review["confirmedExecutionCommandTemplate"] == review_packet["confirmedExecutionCommandTemplate"]
        assert confirmation_review["confirmedExecutionOutputDir"] == review_packet["confirmedExecutionOutputDir"]
        assert confirmation_review["createActionGateOutput"] == review_packet["createActionGateOutput"]
        assert "mediaPolicy" in confirmation_review["policySummaries"]
        assert "contactFormPolicy" in confirmation_review["policySummaries"]
        assert "taxonomyPlan" in confirmation_review["policySummaries"]
        audit = summary["objectiveAudit"]
        assert audit["complete"] is False
        assert audit["readyShape"] is True
        assert audit["reviewReady"] is True
        assert audit["confirmationPrepared"] is False
        assert audit["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert audit["nextBlockingRequirement"] == "user content-intent confirmation converted to execution artifacts"
        assert any(item["requirement"] == "operator has compact confirmation surface" and item["status"] == "proven" for item in audit["checks"])
        refined_summary = Path(summary["artifacts"]["refinedApplySummary"])
        assert refined_summary.exists()
        assert json.loads(refined_summary.read_text(encoding="utf-8"))["kind"] == "allincms_refined_source_wiki_apply_summary"
        assert Path(summary["artifacts"]["refinedSourceExecutionStatus"]).exists()
        assert Path(summary["artifacts"]["refinedSourceNextStageHandoff"]).exists()
        assert summary["artifacts"]["sourceExecutionStatus"] == summary["artifacts"]["refinedSourceExecutionStatus"]
        assert summary["artifacts"]["sourceNextStageHandoff"] == summary["artifacts"]["refinedSourceNextStageHandoff"]
        current_handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert current_handoff["currentStage"] == "confirmation"
        assert summary["refinedSource"]["sourceNextStage"]["currentStage"] == "confirmation"


def test_rehearsal_validation_requires_review_objective_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        summary = build(args)
        summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
        assert validate_summary(summary, summary_path) == []
        summary["sourceReviewObjectiveCoverage"]["json"] = ""
        summary["artifacts"]["sourceReviewObjectiveCoverage"] = ""
        issues = validate_summary(summary, summary_path)
        assert any("sourceReviewObjectiveCoverage" in issue for issue in issues)


def test_rehearsal_can_auto_draft_refined_wiki_to_confirmation_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_dir = root / "sources"
        source_dir.mkdir()
        (source_dir / "brief.md").write_text(
            "example products demo for electrical contractors, facility managers, and OEM buyers.",
            encoding="utf-8",
        )
        (source_dir / "products.csv").write_text(
            "name,category,summary,applications,specs\n"
            "Example Primary Product,Example Facility Products,Representative product option for demanding facilities and project buyers,warehouses and workshops,specification range; performance tier; protection rating\n"
            "Example Secondary Product,Example Secondary Products,Representative secondary product option for buyer comparison and project requirements,secondary applications and facility use cases,specification range; protection rating; material tier\n",
            encoding="utf-8",
        )
        (source_dir / "posts.md").write_text(
            "## How to Choose Example Products for Facility Projects\n"
            "Cover application fit, specification range, operating environment, and sourcing requirements.\n\n"
            "## Example Secondary Product Buying Guide\n"
            "Explain protection rating, application fit, operating environment, and housing durability.\n",
            encoding="utf-8",
        )
        (source_dir / "site-plan.json").write_text(
            json.dumps(
                {
                    "navigation": ["/", "/products", "/posts", "/contact"],
                    "pages": [
                        {"title": "About ExampleCo", "path": "/about", "purpose": "Introduce example products capability"},
                        {"title": "Contact", "path": "/contact", "purpose": "Capture project inquiries"},
                    ],
                    "taxonomyPlan": {
                        "productCategories": ["Example Facility Products", "Example Secondary Products"],
                        "postCategories": ["Buying Guides"],
                    },
                    "mediaPolicy": {"source": "use placeholders until product photos are confirmed"},
                    "contactFormPolicy": {"fields": ["name", "email", "company", "message"]},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        args = base_args(root, source_dir)
        args.recursive = True
        args.site_name = "Example Product Demo"
        args.site_description = "Example product catalog demo for practical B2B buyers."
        args.industry = "example products"
        args.auto_draft_refined_source_wiki = True
        summary = build(args)
        assert summary["reviewReady"] is True, summary
        assert summary["confirmationPrepared"] is False
        assert summary["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert summary["refinedSource"]["used"] is True
        assert summary["refinedSource"]["autoDrafted"] is True
        assert Path(summary["artifacts"]["autoDraftedRefinedSourceWiki"]).exists()
        assert Path(summary["artifacts"]["reviewPacket"]).exists()
        assert summary["confirmationReview"]["available"] is True
        assert summary["sourceFileRehearsalValidation"]["ok"] is True
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        page_paths = {item["path"] for item in review_packet["pagesReview"]}
        nav_paths = {
            item["path"]
            for item in review_packet["siteInfoNavigationFormsMediaReview"]["navigationItems"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        assert {"/", "/about", "/contact"}.issubset(page_paths)
        assert {"/", "/products", "/posts", "/contact"}.issubset(nav_paths)


def test_rehearsal_preserves_structured_site_plan_pages_and_navigation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_dir = root / "sources"
        source_dir.mkdir()
        (source_dir / "brief.md").write_text(
            "Example fixture supplier for project buyers, contractors, and distributor teams.",
            encoding="utf-8",
        )
        (source_dir / "products.csv").write_text(
            "name,category,slug,summary,applications,specs\n"
            "Example Fixture Alpha,Example Category A,example-fixture-alpha,Compact fixture for demanding project spaces,primary project areas,performance tier; protection rating; control option\n"
            "Example Fixture Beta,Example Category A,example-fixture-beta,Linear fixture for structured interior layouts,secondary project spaces,performance tier; sensor option\n"
            "Example Fixture Gamma,Example Category B,example-fixture-gamma,Durable fixture for exposed project areas,outer project areas,protection rating; mounting option\n"
            "Example Fixture Delta,Example Category B,example-fixture-delta,Project fixture for route and area coverage,route and campus areas,optics option; maintenance feature\n",
            encoding="utf-8",
        )
        (source_dir / "posts.md").write_text(
            "## How to Choose Example Fixtures for Project Sites\n"
            "Explain layout, target performance level, controls, mounting, and maintenance access.\n\n"
            "## Example Fixture Buying Checklist for Exposed Projects\n"
            "Explain protection rating, beam pattern, bracket strength, and control requirements.\n\n"
            "## Why Reliability Design Matters in Project Fixtures\n"
            "Explain service life, component protection, ambient conditions, and quality testing.\n",
            encoding="utf-8",
        )
        (source_dir / "site-plan.json").write_text(
            json.dumps(
                {
                    "siteName": "Example Fixture Demo",
                    "siteDescription": "Temporary B2B example fixture demo site for project buyers and sourcing teams.",
                    "industry": "example fixtures",
                    "contentGoals": {"pages": 4, "products": 4, "posts": 3, "navigationItems": 6, "productCategories": 2},
                    "pages": [
                        {"title": "Home", "path": "/", "purpose": "Example fixture supplier homepage"},
                        {"title": "About Us", "path": "/about-us", "purpose": "Explain engineering support and quality process"},
                        {"title": "Applications", "path": "/applications", "purpose": "Show project use cases and selection contexts"},
                        {"title": "Contact Us", "path": "/contact-us", "purpose": "Collect project requirement inquiries without unconfirmed contact details"},
                    ],
                    "navigation": [
                        {"label": "Home", "path": "/"},
                        {"label": "Products", "path": "/products"},
                        {"label": "Applications", "path": "/applications"},
                        {"label": "News", "path": "/posts"},
                        {"label": "About", "path": "/about-us"},
                        {"label": "Contact", "path": "/contact-us"},
                    ],
                    "launchDeferrals": ["custom domain", "tracking scripts", "real company email"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        args = base_args(root, source_dir)
        args.recursive = True
        args.site_name = "Example Fixture Demo"
        args.site_description = "Temporary B2B example fixture demo site for project buyers and sourcing teams."
        args.industry = "example fixtures"
        args.auto_draft_refined_source_wiki = True
        summary = build(args)
        assert summary["reviewReady"] is True, summary
        assert summary["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        assert review_packet["counts"]["pages"] == 4
        assert review_packet["counts"]["products"] == 4
        assert review_packet["counts"]["posts"] == 3
        assert review_packet["contentGoalCoverage"]["counts"]["pages"] == 4
        assert review_packet["contentGoalCoverage"]["counts"]["productCategories"] == 2
        assert review_packet["contentGoalCoverage"]["declaredContentGoals"]["pages"] == 4
        assert review_packet["contentGoalCoverage"]["declaredContentGoals"]["navigationItems"] == 6
        assert review_packet["contentGoalCoverage"]["declaredContentGoals"]["productCategories"] == 2
        assert review_packet["contentQualityReview"]["navigationPathCount"] == 6
        page_paths = {item["path"] for item in review_packet["pagesReview"]}
        nav_paths = {
            item["path"]
            for item in review_packet["siteInfoNavigationFormsMediaReview"]["navigationItems"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        assert page_paths == {"/", "/about-us", "/applications", "/contact-us"}
        assert nav_paths == {"/", "/products", "/applications", "/posts", "/about-us", "/contact-us"}


def test_rehearsal_with_confirmation_prepares_execution_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        summary = build(args)
        assert summary["reviewReady"] is True
        assert summary["confirmationPrepared"] is True
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        assert summary["nextAction"] == "use create-site-preflight-brief.json to collect workspace API session preflight via background CDP fetch before asking for create-site authorization"
        assert summary["confirmationBrief"]["status"] == "confirmed_execution_prepared"
        assert summary["confirmationBrief"]["nextBlockingRequirement"] == "create-site read-only preflight collected"
        audit = summary["objectiveAudit"]
        assert audit["complete"] is False
        assert audit["confirmationPrepared"] is True
        assert audit["readyForBrowserStage"] == "needs_create_site_preflight"
        assert audit["nextBlockingRequirement"] == "create-site read-only preflight collected"
        assert any(item["requirement"] == "create/select site execution boundary prepared" and item["status"] == "prepared" for item in audit["checks"])
        preflight_check = next(item for item in audit["checks"] if item["requirement"] == "create-site read-only preflight collected")
        assert preflight_check["status"] == "not_started"
        assert preflight_check["readyForBrowserStage"] == "needs_create_site_preflight"
        assert summary["confirmedExecution"]["sourceNextStage"]["currentStage"] == "create_site_handoff"
        source_next_stage = summary["confirmedExecution"]["sourceNextStage"]
        assert source_next_stage["browserWorkRequired"] is False
        assert source_next_stage["apiSessionPreflightRequired"] is True
        assert source_next_stage["apiSessionPreflight"]["visibleNavigationAllowed"] is False
        assert source_next_stage["apiSessionPreflight"]["foregroundAllowed"] is False
        assert source_next_stage["apiSessionPreflight"]["loginNavigationGate"] == "api_result_login_required_only"
        confirmed_execution_summary = Path(summary["artifacts"]["confirmedExecutionSummary"])
        assert confirmed_execution_summary.exists()
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        assert confirmed_execution_summary == Path(review_packet["confirmedExecutionOutputDir"]) / "confirmed-site-execution-preparation-summary.json"
        assert "03-confirmed-execution" not in str(confirmed_execution_summary)
        confirmed_data = json.loads(confirmed_execution_summary.read_text(encoding="utf-8"))
        preflight_brief = json.loads(Path(confirmed_data["artifacts"]["createSitePreflightBrief"]).read_text(encoding="utf-8"))
        assert review_packet["createActionGateOutput"] in preflight_brief["nextCommandAfterPreflight"]
        assert "/tmp/allincms-authorization-create-site.json" not in preflight_brief["nextCommandAfterPreflight"]
        assert (
            confirmed_data["kind"] == "allincms_confirmed_site_execution_preparation"
        )
        assert Path(summary["artifacts"]["confirmedSourceExecutionStatus"]).exists()
        assert Path(summary["artifacts"]["confirmedSourceNextStageHandoff"]).exists()
        assert summary["artifacts"]["sourceExecutionStatus"] == summary["artifacts"]["confirmedSourceExecutionStatus"]
        assert summary["artifacts"]["sourceNextStageHandoff"] == summary["artifacts"]["confirmedSourceNextStageHandoff"]
        current_handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert current_handoff["currentStage"] == "create_site_handoff"
        assert Path(summary["artifacts"]["sourceFileRehearsalValidation"]).exists()
        assert summary["sourceFileRehearsalValidation"]["ok"] is True
        assert Path(summary["artifacts"]["confirmedCreateSitePreflightBrief"]).exists()
        assert Path(summary["artifacts"]["confirmedCreateSitePreflightBriefValidation"]).exists()
        assert summary["artifacts"]["confirmedCreateSitePreflightTarget"].endswith("create-site-preflight.json")
        assert summary["artifacts"]["confirmedCreateSiteHandoff"] == ""
        assert summary["artifacts"]["confirmedCreatedSiteEvidenceBrief"] == ""
        assert summary["artifacts"]["confirmedCreatedSiteEvidenceTarget"] == ""
        status = json.loads(Path(summary["artifacts"]["confirmedSourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "create_site_handoff"


def test_rehearsal_existing_site_confirmation_prepares_readonly_refresh_boundary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for updating an existing AllinCMS demo site."
        args.target_mode = "existing_site"
        args.site_key = "existing-demo-site"
        args.frontend_base_url = "https://existing-demo-site.web.allincms.com"
        summary = build(args)
        assert summary["reviewReady"] is True
        assert summary["confirmationPrepared"] is True
        assert summary["readyForBrowserStage"] == "ready_for_existing_site_readonly_refresh"
        assert summary["nextAction"] == "perform existing-site read-only refresh and bind artifacts to that site"
        assert summary["confirmationBrief"]["status"] == "confirmed_execution_prepared"
        assert summary["confirmationBrief"]["isRemoteMutationAuthorization"] is False
        assert summary["objectiveAudit"]["complete"] is False
        assert summary["objectiveAudit"]["readyForBrowserStage"] == "ready_for_existing_site_readonly_refresh"
        assert summary["objectiveAudit"]["nextBlockingRequirement"] == "remote site created or selected and bound to artifacts"
        existing_preflight_check = next(
            item for item in summary["objectiveAudit"]["checks"] if item["requirement"] == "create-site read-only preflight collected"
        )
        assert existing_preflight_check["status"] == "proven"
        assert summary["confirmedExecution"]["targetMode"] == "existing_site"
        assert summary["confirmedExecution"]["sourceNextStage"]["currentStage"] == "created_site_binding"
        assert summary["confirmedExecution"]["sourceNextStage"]["browserWorkRequired"] is True
        assert summary["artifacts"]["confirmedCreateSitePreflightBrief"] == ""
        assert summary["artifacts"]["confirmedCreateSitePreflightBriefValidation"] == ""
        assert summary["artifacts"]["confirmedCreateSitePreflightTarget"] == ""
        assert summary["artifacts"]["confirmedCreateSiteHandoff"] == ""
        assert summary["artifacts"]["confirmedCreateSiteRunbook"] == ""
        assert summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"] == ""
        assert Path(summary["artifacts"]["confirmedConfirmation"]).exists()
        assert Path(summary["artifacts"]["confirmedExecutionPlan"]).exists()
        assert Path(summary["artifacts"]["confirmedArtifactReadiness"]).exists()
        assert summary["artifacts"]["sourceExecutionStatus"] == summary["artifacts"]["confirmedSourceExecutionStatus"]
        assert summary["artifacts"]["sourceNextStageHandoff"] == summary["artifacts"]["confirmedSourceNextStageHandoff"]

        confirmed_summary = json.loads(Path(summary["artifacts"]["confirmedExecutionSummary"]).read_text(encoding="utf-8"))
        assert summary["artifacts"]["confirmedConfirmation"] == confirmed_summary["artifacts"]["confirmation"]
        assert summary["artifacts"]["confirmedExecutionPlan"] == confirmed_summary["artifacts"]["executionPlan"]
        assert summary["artifacts"]["confirmedArtifactReadiness"] == confirmed_summary["artifacts"]["artifactReadiness"]
        execution_plan = json.loads(Path(confirmed_summary["artifacts"]["executionPlan"]).read_text(encoding="utf-8"))
        readiness = json.loads(Path(confirmed_summary["artifacts"]["artifactReadiness"]).read_text(encoding="utf-8"))
        status = json.loads(Path(summary["artifacts"]["confirmedSourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage_handoff = json.loads(Path(summary["artifacts"]["confirmedSourceNextStageHandoff"]).read_text(encoding="utf-8"))

        assert execution_plan["targetMode"] == "existing_site"
        assert execution_plan["siteTarget"] == "existing-demo-site"
        assert readiness["siteKey"] == "existing-demo-site"
        assert readiness["frontendBaseUrl"] == "https://existing-demo-site.web.allincms.com"
        assert status["targetMode"] == "existing_site"
        assert status["currentStage"] == "created_site_binding"
        assert status["stages"]["create_site_handoff"]["status"] == "passed"
        assert status["stages"]["create_site_handoff"]["evidence"] == "existing-site-mode"
        assert status["createdSiteSubmittedValuesIssues"] == []
        assert "createdSiteSubmittedValues" not in status
        assert next_stage_handoff["currentStage"] == "created_site_binding"
        assert next_stage_handoff["mode"] == "browser_action_or_capture_required"
        assert next_stage_handoff["browserWorkRequired"] is True
        assert Path(summary["artifacts"]["sourceFileRehearsalValidation"]).exists()
        assert summary["sourceFileRehearsalValidation"]["ok"] is True


def test_rehearsal_with_confirmation_uses_review_packet_acceptance_defaults() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        args.accepted_fields = ""
        args.accepted_deferral = []
        summary = build(args)
        assert summary["confirmationPrepared"] is True
        confirmed_summary = json.loads(Path(summary["artifacts"]["confirmedExecutionSummary"]).read_text(encoding="utf-8"))
        confirmation = json.loads(Path(confirmed_summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        assert confirmation["acceptedFields"] == review_packet["suggestedAcceptedFields"]
        assert confirmation["acceptedDeferrals"] == review_packet["suggestedAcceptedDeferrals"]


def test_rehearsal_with_confirmation_keeps_explicit_acceptance_overrides() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        args.accepted_fields = (
            "siteProposal.siteName,siteProposal.siteDescription,contentPlan.pages,"
            "contentPlan.products,contentPlan.posts,contentPlan.forms,contentPlan.media,"
            "contentPlan.siteInfo,contentPlan.navigation,contentPlan.taxonomyPlan,"
            "contentPlan.mediaPolicy,contentPlan.contactFormPolicy,siteInfo.publicContact"
        )
        args.accepted_deferral = [
            "siteInfo.legalCompanyName|defer_until_real_company_details|Explicit legal deferral.",
            "domains.customDomain|out_of_scope_for_demo|Explicit domain deferral.",
            "tracking.trackingCode|out_of_scope_for_demo|Explicit tracking deferral.",
        ]
        summary = build(args)
        assert summary["confirmationPrepared"] is True
        confirmed_summary = json.loads(Path(summary["artifacts"]["confirmedExecutionSummary"]).read_text(encoding="utf-8"))
        confirmation = json.loads(Path(confirmed_summary["artifacts"]["confirmation"]).read_text(encoding="utf-8"))
        assert "siteInfo.publicContact" in confirmation["acceptedFields"]
        assert not any(item["field"] == "siteInfo.publicContact" for item in confirmation["acceptedDeferrals"])
        assert {item["field"] for item in confirmation["acceptedDeferrals"]} == {
            "siteInfo.legalCompanyName",
            "domains.customDomain",
            "tracking.trackingCode",
        }


def test_rehearsal_with_confirmation_and_preflight_prepares_create_site_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        args.create_preflight = str(make_preflight(root))
        summary = build(args)
        assert summary["reviewReady"] is True
        assert summary["confirmationPrepared"] is True
        assert summary["readyForBrowserStage"] == "create_site_handoff_ready"
        assert summary["nextAction"] == "use create-site-browser-runbook.json for the gated one-submit create-site browser stage"
        assert summary["confirmationBrief"]["status"] == "confirmed_execution_prepared"
        assert summary["confirmationBrief"]["isRemoteMutationAuthorization"] is False
        assert summary["objectiveAudit"]["complete"] is False
        assert summary["objectiveAudit"]["readyForBrowserStage"] == "create_site_handoff_ready"
        assert summary["objectiveAudit"]["nextBlockingRequirement"] == "remote site created or selected and bound to artifacts"
        preflight_check = next(
            item for item in summary["objectiveAudit"]["checks"] if item["requirement"] == "create-site read-only preflight collected"
        )
        assert preflight_check["status"] == "proven"
        for check in summary["objectiveAudit"]["checks"]:
            assert all(isinstance(item, str) and item.strip() for item in check.get("evidence", []))
        create_boundary_check = next(
            item
            for item in summary["objectiveAudit"]["checks"]
            if item["requirement"] == "create/select site execution boundary prepared"
        )
        assert summary["artifacts"]["confirmedCreateSiteHandoff"] in create_boundary_check["evidence"]
        assert "" not in create_boundary_check["evidence"]
        assert summary["confirmedExecution"]["sourceNextStage"]["currentStage"] == "created_site_binding"
        assert summary["confirmedExecution"]["sourceNextStage"]["browserWorkRequired"] is True
        next_stage_handoff = json.loads(Path(summary["artifacts"]["confirmedSourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert next_stage_handoff["localCommand"] == ""
        assert next_stage_handoff["mode"] == "browser_action_or_capture_required"
        assert summary["artifacts"]["sourceExecutionStatus"] == summary["artifacts"]["confirmedSourceExecutionStatus"]
        assert summary["artifacts"]["sourceNextStageHandoff"] == summary["artifacts"]["confirmedSourceNextStageHandoff"]
        current_handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert current_handoff["currentStage"] == "created_site_binding"
        assert summary["artifacts"]["confirmedCreateSitePreflightBrief"] == ""
        assert summary["artifacts"]["confirmedCreateSitePreflightBriefValidation"] == ""
        assert summary["artifacts"]["confirmedCreateSitePreflightTarget"] == ""
        assert Path(summary["artifacts"]["confirmedCreateSiteHandoff"]).exists()
        assert Path(summary["artifacts"]["confirmedCreateSiteHandoffValidation"]).exists()
        assert Path(summary["artifacts"]["confirmedCreateSiteRunbook"]).exists()
        assert Path(summary["artifacts"]["confirmedCreateSiteRunbookValidation"]).exists()
        assert Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBrief"]).exists()
        assert Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"]).exists()
        assert Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBundleValidation"]).exists()
        assert summary["artifacts"]["confirmedCreatedSiteEvidenceTarget"].endswith("created-site-evidence.json")
        handoff = json.loads(Path(summary["artifacts"]["confirmedCreateSiteHandoff"]).read_text(encoding="utf-8"))
        handoff_validation = json.loads(Path(summary["artifacts"]["confirmedCreateSiteHandoffValidation"]).read_text(encoding="utf-8"))
        runbook = json.loads(Path(summary["artifacts"]["confirmedCreateSiteRunbook"]).read_text(encoding="utf-8"))
        runbook_validation = json.loads(Path(summary["artifacts"]["confirmedCreateSiteRunbookValidation"]).read_text(encoding="utf-8"))
        bundle = json.loads(Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"]).read_text(encoding="utf-8"))
        bundle_validation = json.loads(Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBundleValidation"]).read_text(encoding="utf-8"))
        review_packet = json.loads(Path(summary["artifacts"]["reviewPacket"]).read_text(encoding="utf-8"))
        assert handoff["authorizationOutput"] == review_packet["createActionGateOutput"]
        assert handoff["preparedOnly"] is True
        assert handoff["remoteMutationsPerformed"] is False
        assert handoff_validation["valid"] is True
        assert handoff_validation["handoff"] == summary["artifacts"]["confirmedCreateSiteHandoff"]
        assert runbook["kind"] == "allincms_create_site_browser_runbook"
        assert runbook["browserStepsExecutable"] is False
        assert runbook["sourceCreateSiteHandoff"] == summary["artifacts"]["confirmedCreateSiteHandoff"]
        assert runbook_validation["valid"] is True
        assert runbook_validation["runbook"] == summary["artifacts"]["confirmedCreateSiteRunbook"]
        assert bundle["kind"] == "allincms_created_site_evidence_bundle"
        assert bundle["browserStepsExecutable"] is False
        assert bundle["runbook"] == summary["artifacts"]["confirmedCreateSiteRunbook"]
        assert bundle_validation["valid"] is True
        assert bundle_validation["bundle"] == summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"]
        assert handoff["contentGoalCoverage"] == review_packet["contentGoalCoverage"]
        assert runbook["contentGoalCoverage"] == handoff["contentGoalCoverage"]
        assert bundle["contentGoalCoverage"] == handoff["contentGoalCoverage"]
        assert handoff["contentQualityReview"] == review_packet["contentQualityReview"]
        assert runbook["contentQualityReview"] == handoff["contentQualityReview"]
        assert bundle["contentQualityReview"] == handoff["contentQualityReview"]
        assert handoff["wikiReview"] == review_packet["wikiReview"]
        assert runbook["wikiReview"] == handoff["wikiReview"]
        assert bundle["wikiReview"] == handoff["wikiReview"]
        assert runbook["confirmationDecisionMatrix"] == handoff["confirmationDecisionMatrix"]
        assert bundle["confirmationDecisionMatrix"] == handoff["confirmationDecisionMatrix"]
        bundle_template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert bundle_template["contentGoalCoverage"] == bundle["contentGoalCoverage"]
        assert bundle_template["contentQualityReview"] == bundle["contentQualityReview"]
        assert bundle_template["wikiReview"] == bundle["wikiReview"]
        assert bundle_template["confirmationDecisionMatrix"] == bundle["confirmationDecisionMatrix"]


def test_rehearsal_validation_rejects_create_site_artifact_binding_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        args.create_preflight = str(make_preflight(root))
        summary = build(args)
        summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
        assert validate_summary(summary, summary_path) == []

        bundle_path = Path(summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle["runbook"] = str(root / "wrong-runbook.json")
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        issues = validate_summary(summary, summary_path)
        assert any("evidence bundle runbook must bind" in issue for issue in issues)

        summary["artifacts"]["confirmedCreatedSiteEvidenceBundleValidation"] = ""
        issues = validate_summary(summary, summary_path)
        assert "artifacts.confirmedCreatedSiteEvidenceBundleValidation is required" in issues


def test_rehearsal_reports_recursive_input_file_count_and_quality_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        (sources / "brief.md").write_text(
            "Example supplier supports project buyers with a focused catalog, practical guidance, and inquiry handling.",
            encoding="utf-8",
        )
        (sources / "products.csv").write_text(
            "name,slug,description,category,tags,wattage,lumen\n"
            "Example Product Alpha,example-product-alpha,High-efficiency example product for large facilities,Example Category A,\"facility,industrial\",150W,22500lm\n"
            "Example Product Beta,example-product-beta,Slim example product for commercial interiors,Example Category B,\"office,ceiling\",40W,4000lm\n",
            encoding="utf-8",
        )
        (sources / "content-plan.md").write_text(
            "# Content Plan\n\n"
            "Home page should introduce the catalog and project capability.\n\n"
            "About Us page should explain engineering support and export service.\n\n"
            "Contact page should provide an inquiry form.\n\n"
            "Article 1: How to choose example products for large facilities. "
            "Cover capacity planning, installation height, configuration angle, and operating efficiency.\n\n"
            "Article 2: Example products for commercial interiors. "
            "Cover usability control, configuration options, installation type, and maintenance.\n",
            encoding="utf-8",
        )
        args = base_args(root, sources)
        args.recursive = True
        summary = build(args)
        quality = summary["sourcePrepare"]["contentQuality"]
        assert summary["sourceCount"] == 1
        assert summary["inputFileCount"] == 3
        assert quality["inputFileCount"] == 3
        assert quality["readyShape"] is True
        assert quality["contentCounts"]["pages"] == 3
        assert quality["contentCounts"]["products"] == 2
        assert quality["contentCounts"]["posts"] == 2
        assert quality["taxonomyCounts"]["productCategories"] == 2
        assert quality["taxonomyCounts"]["postCategories"] == 1
        assert quality["navigationPathsUnique"] is True
        assert quality["warnings"] == []


def test_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        script = Path(__file__).resolve().parent / "run_source_file_rehearsal.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(source),
                "--output-dir",
                str(root / "cli-rehearsal"),
                "--site-name",
                "Example Product Demo",
                "--site-description",
                "A source-backed example site for product buyers and practical product selection.",
                "--industry",
                "example industry",
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_source_file_rehearsal_summary"
        assert "Wrote source file rehearsal summary" not in result.stdout


def test_rehearsal_threads_review_objective_coverage_into_confirmed_chain() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        summary = build(args)
        assert summary["confirmationPrepared"] is True
        coverage = json.loads(Path(summary["artifacts"]["sourceReviewObjectiveCoverage"]).read_text(encoding="utf-8"))
        assert coverage["reviewComplete"] is True
        assert coverage["complete"] is False
        confirmation = json.loads(Path(summary["artifacts"]["confirmedConfirmation"]).read_text(encoding="utf-8"))
        plan = json.loads(Path(summary["artifacts"]["confirmedExecutionPlan"]).read_text(encoding="utf-8"))
        readiness = json.loads(Path(summary["artifacts"]["confirmedArtifactReadiness"]).read_text(encoding="utf-8"))
        status = json.loads(Path(summary["artifacts"]["confirmedSourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(summary["artifacts"]["confirmedSourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert confirmation["sourceReviewObjectiveCoverage"] == coverage
        assert plan["sourceReviewObjectiveCoverage"] == coverage
        assert readiness["sourceReviewObjectiveCoverage"] == coverage
        assert status["sourceReviewObjectiveCoverage"] == coverage
        assert status["sourceReviewObjectiveCoverageIssues"] == []
        assert next_stage["sourceReviewObjectiveCoverage"] == coverage


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source file rehearsal regression tests passed.")
