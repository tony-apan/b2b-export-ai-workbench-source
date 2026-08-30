#!/usr/bin/env python3
"""Regression tests for confirmed source-package create-site handoff."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_confirmed_create_site_handoff import build_handoff, validate_handoff
from build_confirmed_site_execution_plan import build_plan
from make_create_preflight_evidence import build_evidence, parse_observed_fields
from make_source_package_confirmation import build_confirmation
from make_source_package_review_packet import build_review_packet
from test_source_confirmation_execution_plan import add_generated_post_overage, make_package, write_json


def prepare_inputs(root: Path, *, with_post_overage: bool = False) -> argparse.Namespace:
    package_path = make_package(root)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if with_post_overage:
        add_generated_post_overage(package)
        write_json(package_path, package)
    review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
    review_packet_path = root / "source-package-review-packet.json"
    write_json(review_packet_path, review_packet)
    confirmation = build_confirmation(
        argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package for a temporary demo site.",
            accepted_fields="",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="handoff test",
            output=str(root / "confirmation.json"),
            json=False,
        )
    )
    confirmation_path = root / "confirmation.json"
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
    plan_path = root / "execution-plan.json"
    write_json(plan_path, plan)
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
    return argparse.Namespace(
        package=str(package_path),
        review_packet=str(review_packet_path),
        confirmation=str(confirmation_path),
        execution_plan=str(plan_path),
        preflight=str(preflight_path),
        authorization_output=str(root / "authorization-create-site.json"),
        output=str(root / "create-site-handoff.json"),
        json=False,
    )


def test_create_site_handoff_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = build_handoff(prepare_inputs(root))
        assert not validate_handoff(handoff)
        assert handoff["preparedOnly"] is True
        assert handoff["isUserAuthorization"] is False
        assert handoff["siteProposal"]["siteName"] == "Example Demo"
        assert handoff["contentCounts"]["navigationItems"] >= 3
        assert handoff["contentCounts"]["siteInfoFields"] >= 3
        assert handoff["contentGoalCoverage"]["complete"] is True
        assert handoff["contentGoalCoverage"]["checks"]["products"] is True
        assert handoff["contentGoalCoverage"]["checks"]["posts"] is True
        assert len(handoff["sourcePackageSha256"]) == 64
        assert len(handoff["sourceReviewPacketSha256"]) == 64
        assert handoff["contentQualityReview"]["reviewRequired"] is False
        assert handoff["contentQualityReview"]["warnings"] == []
        assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
        assert "--expected-target-identifier 'Example Demo'" in handoff["preMutationGateCommand"]
        assert "uploading products/posts/media" in handoff["forbiddenActions"]
        assert handoff["createdSiteEvidenceBrief"].endswith("created-site-evidence-brief.json")
        assert handoff["createdSiteEvidenceOutput"].endswith("created-site-evidence.json")


def test_create_site_handoff_preserves_empty_site_list_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root)
        preflight = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
        preflight["siteCreation"]["existingSiteKeysBeforeCreate"] = []
        preflight["siteCreation"].pop("siteKeyEvidence")
        preflight["siteCreation"]["emptySiteListEvidence"] = "verified empty /sites list after loading the workspace sites page"
        write_json(Path(args.preflight), preflight)
        handoff = build_handoff(args)
        assert not validate_handoff(handoff)
        assert handoff["existingSiteKeysBeforeCreate"] == []
        assert handoff["emptySiteListEvidence"] == "verified empty /sites list after loading the workspace sites page"


def test_create_site_handoff_rejects_empty_site_list_without_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root)
        preflight = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
        preflight["siteCreation"]["existingSiteKeysBeforeCreate"] = []
        preflight["siteCreation"].pop("siteKeyEvidence")
        preflight["siteCreation"].pop("emptySiteListEvidence", None)
        write_json(Path(args.preflight), preflight)
        try:
            build_handoff(args)
        except SystemExit as exc:
            assert "emptySiteListEvidence" in str(exc)
        else:
            raise AssertionError("empty site list without evidence should not build handoff")


def test_create_site_handoff_rejects_existing_site_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root)
        plan = json.loads(Path(args.execution_plan).read_text(encoding="utf-8"))
        plan["targetMode"] = "existing_site"
        write_json(Path(args.execution_plan), plan)
        try:
            build_handoff(args)
        except SystemExit as exc:
            assert "targetMode must be new_site" in str(exc)
        else:
            raise AssertionError("existing_site plan should not build create-site handoff")


def test_create_site_handoff_rejects_identity_hash_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root)
        plan = json.loads(Path(args.execution_plan).read_text(encoding="utf-8"))
        plan["sourcePackageSha256"] = "0" * 64
        write_json(Path(args.execution_plan), plan)
        try:
            build_handoff(args)
        except SystemExit as exc:
            assert "executionPlan.sourcePackageSha256 must match confirmation.sourcePackageSha256" in str(exc)
        else:
            raise AssertionError("identity hash drift should not build create-site handoff")


def test_create_site_handoff_rejects_missing_content_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = build_handoff(prepare_inputs(root))
        handoff.pop("contentCounts", None)
        issues = validate_handoff(handoff)
        assert "contentCounts must be an object" in issues


def test_create_site_handoff_rejects_incomplete_scope_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = build_handoff(prepare_inputs(root))
        handoff["contentCounts"].pop("navigationItems", None)
        issues = validate_handoff(handoff)
        assert "contentCounts.navigationItems must be a non-negative integer" in issues

        handoff = build_handoff(prepare_inputs(root))
        handoff["contentCounts"].pop("siteInfoFields", None)
        issues = validate_handoff(handoff)
        assert "contentCounts.siteInfoFields must be a non-negative integer" in issues


def test_create_site_handoff_preserves_content_quality_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root)
        package = json.loads(Path(args.package).read_text(encoding="utf-8"))
        package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] = 0
        package["contentPlan"]["taxonomyPlan"]["postCategories"] = []
        write_json(Path(args.package), package)
        review_packet = build_review_packet(package, args.package, generated_at="2026-07-01T00:00:00+00:00")
        write_json(Path(args.review_packet), review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=args.package,
                review_packet=args.review_packet,
                user_confirmation_text="User confirms the generated source package after reviewing quality warnings.",
                accepted_fields="",
                accepted_deferral=[
                    "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                    "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                    "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
                ],
                notes="handoff warning test",
                output=args.confirmation,
                json=False,
            )
        )
        write_json(Path(args.confirmation), confirmation)
        plan = build_plan(
            argparse.Namespace(
                package=args.package,
                confirmation=args.confirmation,
                target_mode="new_site",
                site_key="",
                output=args.execution_plan,
                json=False,
            )
        )
        write_json(Path(args.execution_plan), plan)
        handoff = build_handoff(args)
        warning_quality = review_packet["contentQualityReview"]
        assert not validate_handoff(handoff), handoff
        assert handoff["contentQualityReview"] == warning_quality
        assert handoff["contentQualityReview"]["reviewRequired"] is True
        assert "posts_present_without_post_categories" in handoff["contentQualityReview"]["warnings"]
        assert "contentQualityReview warnings" in " ".join(handoff["mustRunBeforeBrowserSubmit"])


def test_create_site_handoff_preserves_content_goal_overages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root, with_post_overage=True)
        review_packet = json.loads(Path(args.review_packet).read_text(encoding="utf-8"))
        assert "exceeds_declared_content_goal:posts" in review_packet["contentQualityReview"]["warnings"]
        handoff = build_handoff(args)
        assert not validate_handoff(handoff), handoff
        assert handoff["contentGoalOverages"] == review_packet["contentGoalOverages"]
        assert handoff["contentGoalOverages"]["details"]["posts"]["likelyExtraItems"][0]["slug"] == "generated-buyer-guide"
        assert "contentGoalOverages" in " ".join(handoff["mustRunBeforeBrowserSubmit"])

        drifted = json.loads(json.dumps(handoff))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_handoff(drifted)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues


def test_create_site_handoff_rejects_overage_drift_from_execution_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = prepare_inputs(root, with_post_overage=True)
        plan = json.loads(Path(args.execution_plan).read_text(encoding="utf-8"))
        plan["contentGoalOverages"]["present"] = False
        write_json(Path(args.execution_plan), plan)
        try:
            build_handoff(args)
        except SystemExit as exc:
            assert "contentGoalOverages.present must equal bool(details)" in str(exc)
        else:
            raise AssertionError("overage drift should not build create-site handoff")


if __name__ == "__main__":
    test_create_site_handoff_builds()
    test_create_site_handoff_preserves_empty_site_list_evidence()
    test_create_site_handoff_rejects_empty_site_list_without_evidence()
    test_create_site_handoff_rejects_existing_site_plan()
    test_create_site_handoff_rejects_identity_hash_drift()
    test_create_site_handoff_rejects_missing_content_counts()
    test_create_site_handoff_rejects_incomplete_scope_counts()
    test_create_site_handoff_preserves_content_quality_warnings()
    test_create_site_handoff_preserves_content_goal_overages()
    test_create_site_handoff_rejects_overage_drift_from_execution_plan()
    print("confirmed create-site handoff regression tests passed.")
