#!/usr/bin/env python3
"""Regression tests for source package review packet helpers."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from make_source_package_review_packet import build_review_packet
from test_source_confirmation_execution_plan import make_package, write_json
from validate_source_package_review_packet import validate_review_packet


def test_review_packet_builds_from_publication_ready_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_path = root / "source-package-review-packet.json"
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
            review_packet_path=str(review_path),
        )
        assert not validate_review_packet(packet, package)
        assert packet["localOnly"] is True
        assert packet["isRemoteMutationAuthorization"] is False
        assert packet["counts"] == {
            "pages": 1,
            "products": 1,
            "posts": 1,
            "forms": 1,
            "media": 3,
            "siteInfoFields": 5,
            "navigationItems": 3,
        }
        assert packet["contentGoalCoverage"]["complete"] is True
        assert packet["contentGoalCoverage"]["checks"]["siteInfo"] is True
        assert packet["contentGoalCoverage"]["checks"]["pages"] is True
        assert packet["contentGoalCoverage"]["checks"]["products"] is True
        assert packet["contentGoalCoverage"]["checks"]["posts"] is True
        assert packet["contentGoalCoverage"]["checks"]["manifests.products"] is True
        assert packet["contentGoalCoverage"]["checks"]["manifests.posts"] is True
        assert packet["contentQualityReview"]["readyShape"] is True
        assert packet["contentQualityReview"]["warnings"] == []
        assert packet["contentQualityReview"]["reviewRequired"] is False
        assert packet["contentQualityReview"]["contentCounts"] == packet["counts"]
        assert packet["contentQualityReview"]["navigationPathsUnique"] is True
        assert packet["wikiReview"]["sourceWiki"] == package["sourceWiki"]
        assert Path(packet["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        assert packet["productsReview"][0]["slug"] == "industrial-sample-product"
        assert packet["productsReview"][0]["contentCharCount"] > 100
        media_policy = packet["siteInfoNavigationFormsMediaReview"]["mediaPolicy"]
        assert media_policy["present"] is True
        assert media_policy["status"] == "needs_user_confirmation"
        assert media_policy["sourceCandidateCount"] == 1
        assert media_policy["pageMediaNeedCount"] == 0
        assert media_policy["productMediaNeedCount"] == 1
        assert media_policy["postMediaNeedCount"] == 1
        assert media_policy["requiresFrontendImageProof"] is True
        contact_policy = packet["siteInfoNavigationFormsMediaReview"]["contactFormPolicy"]
        assert contact_policy["present"] is True
        assert contact_policy["status"] == "needs_user_confirmation"
        assert contact_policy["formCount"] == 1
        assert contact_policy["fieldNeedCount"] == 3
        assert contact_policy["requiresSubmissionProofOrDeferral"] is True
        taxonomy_plan = packet["siteInfoNavigationFormsMediaReview"]["taxonomyPlan"]
        assert taxonomy_plan["present"] is True
        assert taxonomy_plan["status"] == "needs_user_confirmation"
        assert taxonomy_plan["productCategoryCount"] == 1
        assert taxonomy_plan["postCategoryCount"] == 1
        assert taxonomy_plan["requiresCreationOrMappingPlan"] is True
        assert "直接上传" not in packet["suggestedConfirmationText"]
        assert packet["suggestedAcceptedFields"]
        assert {item["field"] for item in packet["suggestedAcceptedDeferrals"]} >= {
            "siteInfo.publicContact",
            "siteInfo.legalCompanyName",
            "domains.customDomain",
            "tracking.trackingCode",
        }
        assert str(review_path) in packet["confirmationCommandTemplate"]
        assert "/tmp/allincms-run/source-package-review-packet.json" not in packet["confirmationCommandTemplate"]
        expected_confirmation_output = str(root / "confirmation-record.json")
        expected_execution_dir = str(root / "confirmed-execution")
        expected_action_gate = str(root / "create-site-action-gate.json")
        assert packet["confirmationOutput"] == expected_confirmation_output
        assert packet["confirmedExecutionOutputDir"] == expected_execution_dir
        assert packet["createActionGateOutput"] == expected_action_gate
        assert expected_confirmation_output in packet["confirmationCommandTemplate"]
        assert expected_confirmation_output in packet["confirmationValidationCommandTemplate"]
        assert "--accepted-fields" in packet["confirmationCommandTemplate"]
        assert "--accepted-deferral" in packet["confirmationCommandTemplate"]
        execution_command = packet["confirmedExecutionCommandTemplate"]
        assert "prepare_confirmed_site_execution.py" in execution_command
        assert f"--package {package_path}" in execution_command
        assert f"--review-packet {review_path}" in execution_command
        assert "--user-confirmation-text '<paste current user confirmation text here>'" in execution_command
        assert "--accepted-fields" in execution_command
        assert "--accepted-deferral" in execution_command
        assert f"--output-dir {expected_execution_dir}" in execution_command
        assert "--target-mode new_site" in execution_command
        assert f"--create-authorization-output {expected_action_gate}" in execution_command
        assert "--create-action-gate-output" not in execution_command
        assert "/tmp/allincms-run/source-package-review-packet.json" not in execution_command
        covered = set(packet["suggestedAcceptedFields"]) | {item["field"] for item in packet["suggestedAcceptedDeferrals"]}
        assert set(packet["confirmationFields"]) <= covered


def test_review_packet_rejects_thin_unready_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["contentPlan"]["products"][0]["description"] = "Draft Product"
        try:
            build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        except ValueError as exc:
            assert "not ready for review confirmation" in str(exc)
        else:
            raise AssertionError("unready package should not build a review packet")


def test_review_packet_rejects_sensitive_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        packet["siteReview"]["siteName"] = "authorization: bearer secret"
        issues = validate_review_packet(packet, package)
        assert any("sensitive" in issue for issue in issues), issues
        write_json(root / "bad-review-packet.json", packet)


def test_review_packet_rejects_missing_confirmed_execution_template() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_path = root / "source-package-review-packet.json"
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
            review_packet_path=str(review_path),
        )
        packet.pop("confirmedExecutionCommandTemplate")
        issues = validate_review_packet(packet, package)
        assert "confirmedExecutionCommandTemplate is required" in issues, issues


def test_review_packet_rejects_confirmed_execution_path_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_path = root / "source-package-review-packet.json"
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
            review_packet_path=str(review_path),
        )
        packet["confirmedExecutionOutputDir"] = str(root / "other-execution")
        issues = validate_review_packet(packet, package)
        assert "confirmedExecutionCommandTemplate must write confirmedExecutionOutputDir" in issues, issues


def test_review_packet_accepts_equivalent_tmp_private_tmp_source_package_paths() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        real_package_path = os.path.realpath(package_path)
        if real_package_path == str(package_path):
            return
        packet["sourcePackage"] = real_package_path
        issues = validate_review_packet(packet, package)
        assert not issues, issues


def test_review_packet_rejects_content_goal_coverage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        packet["contentGoalCoverage"]["checks"]["posts"] = False
        packet["contentGoalCoverage"]["missing"] = ["posts"]
        issues = validate_review_packet(packet, package)
        assert "contentGoalCoverage.complete must be true" in issues or "contentGoalCoverage.missing must be empty" in issues
        assert "contentGoalCoverage must match source package coverage" in issues


def test_review_packet_surfaces_non_blocking_quality_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] = 0
        package["contentPlan"]["taxonomyPlan"]["postCategories"] = []
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        quality = packet["contentQualityReview"]
        assert quality["readyShape"] is False
        assert quality["reviewRequired"] is True
        assert "posts_present_without_post_categories" in quality["warnings"]
        assert "posts_present_without_post_categories" in packet["suggestedConfirmationText"]
        assert not validate_review_packet(packet, package)
        drifted = json.loads(json.dumps(packet))
        drifted["contentQualityReview"]["warnings"] = []
        issues = validate_review_packet(drifted, package)
        assert "contentQualityReview.reviewRequired must equal bool(warnings)" in issues
        assert "contentQualityReview must match source package quality review" in issues


def test_review_packet_surfaces_excess_declared_goal_warning_without_blocking_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["declaredContentGoals"] = {
            **package.get("declaredContentGoals", {}),
            "posts": 0,
        }
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        quality = packet["contentQualityReview"]
        assert quality["readyShape"] is True
        assert quality["reviewRequired"] is True
        assert "exceeds_declared_content_goal:posts" in quality["warnings"]
        assert "exceeds_declared_content_goal:posts" in packet["suggestedConfirmationText"]
        overages = packet["contentGoalOverages"]
        assert overages["present"] is True
        assert overages["details"]["posts"]["declared"] == 0
        assert overages["details"]["posts"]["actual"] == 1
        assert overages["details"]["posts"]["extraCount"] == 1
        assert overages["details"]["posts"]["items"][0]["title"] == "Industrial Sourcing Guide"
        assert overages["details"]["posts"]["likelyExtraItems"][0]["slug"] == "industrial-sourcing-guide"
        assert not validate_review_packet(packet, package)


def test_review_packet_lists_item_level_overages_for_generated_posts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        base_post = package["contentPlan"]["posts"][0]
        package["contentPlan"]["posts"] = [
            {
                **base_post,
                "title": "Generated Brief Article",
                "slug": "generated-brief-article",
                "sourceRefs": ["src-001"],
            },
            {
                **base_post,
                "title": "Generated Planning Checklist",
                "slug": "generated-planning-checklist",
                "sourceRefs": ["src-002"],
            },
            {
                **base_post,
                "title": "Generated Selection Guide",
                "slug": "generated-selection-guide",
                "sourceRefs": ["src-003"],
            },
            {
                **base_post,
                "title": "Generated Buyer Guide",
                "slug": "generated-buyer-guide",
                "sourceRefs": ["src-004"],
            },
        ]
        manifest_template = package["manifests"]["posts"]["items"][0]
        package["manifests"]["posts"]["items"] = [
            {
                **manifest_template,
                "title": post["title"],
                "slug": post["slug"],
                "sourceRef": post["sourceRefs"][0],
            }
            for post in package["contentPlan"]["posts"]
        ]
        package["declaredContentGoals"] = {
            **package.get("declaredContentGoals", {}),
            "posts": 3,
        }
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
        )
        assert "exceeds_declared_content_goal:posts" in packet["contentQualityReview"]["warnings"]
        detail = packet["contentGoalOverages"]["details"]["posts"]
        assert detail["declared"] == 3
        assert detail["actual"] == 4
        assert detail["extraCount"] == 1
        assert [item["title"] for item in detail["items"]] == [
            "Generated Brief Article",
            "Generated Planning Checklist",
            "Generated Selection Guide",
            "Generated Buyer Guide",
        ]
        assert detail["likelyExtraItems"] == [
            {
                "title": "Generated Buyer Guide",
                "slug": "generated-buyer-guide",
                "sourceRefs": ["src-004"],
            }
        ]
        assert not validate_review_packet(packet, package)
        drifted = json.loads(json.dumps(packet))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_review_packet(drifted, package)
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues
        assert "contentGoalOverages must match source package overage details" in issues


def test_review_packet_rejects_missing_wiki_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        packet["wikiReview"]["sourceWikiMarkdownIndex"] = ""
        issues = validate_review_packet(packet, package)
        assert "wikiReview.sourceWikiMarkdownIndex is required" in issues


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source package review packet regression tests passed.")
