#!/usr/bin/env python3
"""Regression tests for source package confirmation and execution plan helpers."""

from __future__ import annotations

import sys

import argparse
import json
import hashlib
import tempfile
from pathlib import Path

from build_source_site_package import build_package
from make_source_package_review_packet import build_review_packet
from make_source_review_objective_coverage import build_coverage
from make_source_package_confirmation import build_confirmation
from build_confirmed_site_execution_plan import build_plan, validate_plan
from validate_source_package_confirmation import validate_confirmation, validate_confirmation_with_review_packet


class PackageArgs:
    def __init__(self, source_wiki: str, output: str) -> None:
        self.source_wiki = source_wiki
        self.requirements = ""
        self.site_key = ""
        self.frontend_base_url = ""
        self.output = output


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_package(root: Path) -> Path:
    wiki_dir = root / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "index.md").write_text("# Source Wiki\n\n- site\n- pages\n- products\n- posts\n", encoding="utf-8")
    write_json(
        wiki_dir / "manifest.json",
        {
            "kind": "allincms_source_wiki_markdown_export",
            "files": {"index": str(wiki_dir / "index.md")},
        },
    )
    catalog_path = root / "catalog.txt"
    catalog_path.write_text(
        "Example catalog source text for one industrial product, one sourcing guide, and one contact form.",
        encoding="utf-8",
    )
    source_wiki = root / "source-wiki.json"
    write_json(
        source_wiki,
        {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [
                    {
                        "path": str(catalog_path),
                        "name": "catalog.txt",
                        "type": "text",
                        "sizeBytes": catalog_path.stat().st_size,
                        "sha256": file_sha256(catalog_path),
                        "sourceRef": "src-001",
                    }
                ],
                "wikiRefs": [str(wiki_dir / "manifest.json"), str(wiki_dir / "index.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example demo site for source-backed industrial product and article publishing.",
                "language": "en",
                "industry": "example",
            },
            "pages": [
                {
                    "title": "Home",
                    "path": "/",
                    "sections": [
                        {
                            "heading": "Source-Backed Product Site",
                            "body": (
                                "The homepage introduces the product range, buyer use cases, sourcing context, "
                                "and the site structure generated from the provided source files."
                            ),
                        }
                    ],
                    "sourceRefs": ["src-001"],
                }
            ],
            "products": [
                {
                    "name": "Industrial Sample Product",
                    "slug": "industrial-sample-product",
                    "description": "A source-backed product summary for buyers comparing industrial sourcing options.",
                    "content": [
                        {
                            "text": (
                                "The product body explains the practical buyer scenario, selection context, "
                                "application notes, and source-backed differentiators for this sample item."
                            )
                        }
                    ],
                    "mediaNeeds": [{"target": "product.cover", "kind": "cover", "sourceHint": "source product image"}],
                    "categories": ["Example Category"],
                    "tags": ["example-tag"],
                    "sourceRefs": ["src-001"],
                }
            ],
            "posts": [
                {
                    "title": "Industrial Sourcing Guide",
                    "slug": "industrial-sourcing-guide",
                    "excerpt": "A source-backed article excerpt for buyers comparing options and supplier fit.",
                    "content": [
                        {
                            "text": (
                                "The article body summarizes buyer evaluation criteria, common sourcing questions, "
                                "and how the source material supports a practical purchase decision."
                            )
                        }
                    ],
                    "mediaNeeds": [{"target": "post.cover", "kind": "cover", "sourceHint": "source article image"}],
                    "categories": ["Buying Guides"],
                    "tags": ["selection"],
                    "sourceRefs": ["src-001"],
                }
            ],
            "forms": [
                {
                    "name": "Contact Form",
                    "slug": "contact-form",
                    "fields": [{"name": "name"}, {"name": "email"}, {"name": "message"}],
                    "sourceRefs": ["src-001"],
                }
            ],
            "media": [{"sourceRef": "src-001", "kind": "image", "usage": "cover candidate"}],
        },
    )
    package = build_package(PackageArgs(str(source_wiki), str(root / "source-site-package.json")))
    package_path = root / "source-site-package.json"
    write_json(package_path, package)
    return package_path


def add_generated_post_overage(package: dict) -> None:
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


def test_confirmation_and_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        assert Path(review_packet["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        assert review_packet["siteInfoNavigationFormsMediaReview"]["mediaPolicy"]["status"] == "needs_user_confirmation"
        assert review_packet["siteInfoNavigationFormsMediaReview"]["mediaPolicy"]["productMediaNeedCount"] == 1
        assert review_packet["siteInfoNavigationFormsMediaReview"]["contactFormPolicy"]["status"] == "needs_user_confirmation"
        assert review_packet["siteInfoNavigationFormsMediaReview"]["contactFormPolicy"]["formCount"] == 1
        assert review_packet["siteInfoNavigationFormsMediaReview"]["taxonomyPlan"]["status"] == "needs_user_confirmation"
        assert review_packet["siteInfoNavigationFormsMediaReview"]["taxonomyPlan"]["productCategoryCount"] == 1
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation_args = argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package for a temporary demo site.",
            accepted_fields="contentPlan.forms,contentPlan.media",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="local test",
            output=str(root / "confirmation.json"),
            json=False,
        )
        confirmation = build_confirmation(confirmation_args)
        assert not validate_confirmation_with_review_packet(confirmation, package, review_packet)
        assert confirmation["sourceReviewPacket"] == str(review_packet_path)
        assert confirmation["sourcePackageSha256"] == file_sha256(package_path)
        assert confirmation["sourceReviewPacketSha256"] == file_sha256(review_packet_path)
        assert confirmation["contentGoalCoverage"] == review_packet["contentGoalCoverage"]
        assert confirmation["contentGoalCoverage"]["complete"] is True
        assert confirmation["contentQualityReview"] == review_packet["contentQualityReview"]
        assert confirmation["contentGoalOverages"] == review_packet["contentGoalOverages"]
        assert confirmation["wikiReview"] == review_packet["wikiReview"]
        assert "contentPlan.mediaPolicy" in confirmation["acceptedFields"]
        assert "contentPlan.contactFormPolicy" in confirmation["acceptedFields"]
        assert "contentPlan.taxonomyPlan" in confirmation["acceptedFields"]
        assert {item["field"] for item in confirmation["acceptedDeferrals"]} >= {
            "siteInfo.publicContact",
            "siteInfo.legalCompanyName",
            "domains.customDomain",
            "tracking.trackingCode",
        }
        confirmation_path = root / "confirmation.json"
        write_json(confirmation_path, confirmation)
        plan_args = argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            target_mode="new_site",
            site_key="",
            output=str(root / "execution-plan.json"),
            json=False,
        )
        plan = build_plan(plan_args)
        assert not validate_plan(plan)
        assert plan["preparedOnly"] is True
        assert plan["isUserAuthorization"] is False
        assert plan["contentCounts"]["navigationItems"] >= 3
        assert plan["contentCounts"]["siteInfoFields"] >= 3
        assert plan["contentCounts"]["media"] == plan["contentGoalCoverage"]["counts"]["media"]
        assert plan["contentCounts"]["media"] >= 3
        assert plan["contentGoalCoverage"]["complete"] is True
        assert plan["contentGoalCoverage"] == confirmation["contentGoalCoverage"]
        assert plan["sourcePackageSha256"] == confirmation["sourcePackageSha256"]
        assert plan["sourceReviewPacketSha256"] == confirmation["sourceReviewPacketSha256"]
        assert plan["contentQualityReview"] == confirmation["contentQualityReview"]
        assert plan["contentGoalOverages"] == confirmation["contentGoalOverages"]
        assert plan["wikiReview"] == confirmation["wikiReview"]
        stages = [item["stage"] for item in plan["stageOrder"]]
        assert stages.index("pages_site_info_handoff") < stages.index("schema_capture")
        assert stages.index("pages_site_info_execution") < stages.index("schema_capture")
        assert stages.index("batch_upload_publish") < stages.index("forms_media_settings")
        assert "<paste current user authorization text here>" in plan["commandTemplates"]["createSiteAuthorizationRecord"]


def test_plan_rejects_content_count_scope_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                user_confirmation_text="User confirms the generated source package for a temporary demo site.",
                accepted_fields="contentPlan.forms,contentPlan.media",
                accepted_deferral=[
                    "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                    "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                    "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
                ],
                notes="local test",
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
        plan["contentCounts"]["media"] = 0
        issues = validate_plan(plan)
        assert any("contentCounts.media must match contentGoalCoverage.counts.media" in issue for issue in issues), issues


def test_confirmation_rejects_missing_required_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        bad = {
            "kind": "allincms_source_site_package_confirmation",
            "confirmedAt": "2026-07-01T00:00:00+00:00",
            "confirmedBy": "user",
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "isRemoteMutationAuthorization": False,
            "sourcePackage": str(package_path),
            "sourceReviewPacket": str(root / "missing-review-packet.json"),
            "userConfirmationText": "User confirms package.",
            "acceptedFields": ["siteProposal.siteName"],
            "blockedRemoteActionsStillRequireActionAuthorization": ["create_site"],
            "confirmedCounts": {"pages": 1, "products": 1, "posts": 1},
        }
        issues = validate_confirmation(bad, package)
        assert any("acceptedFields missing" in issue for issue in issues), issues
        assert any("blocked remote action list missing" in issue for issue in issues), issues


def test_confirmation_rejects_missing_decision_deferrals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = {
            "kind": "allincms_source_site_package_confirmation",
            "confirmedAt": "2026-07-01T00:00:00+00:00",
            "confirmedBy": "user",
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "isRemoteMutationAuthorization": False,
            "sourcePackage": str(package_path),
            "sourcePackageSha256": file_sha256(package_path),
            "sourceReviewPacket": str(review_packet_path),
            "sourceReviewPacketSha256": file_sha256(review_packet_path),
            "userConfirmationText": "User confirms the generated package for local planning only.",
            "acceptedFields": review_packet["confirmationFields"],
            "acceptedDeferrals": [],
            "blockedRemoteActionsStillRequireActionAuthorization": package["confirmationGate"]["blockedRemoteActions"],
            "confirmedCounts": {"pages": 1, "products": 1, "posts": 1},
        }
        for field in ("siteInfo.publicContact", "siteInfo.legalCompanyName", "domains.customDomain", "tracking.trackingCode"):
            confirmation["acceptedFields"].remove(field)
        issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
        assert any("acceptedFields or acceptedDeferrals missing required decision fields" in issue for issue in issues), issues


def test_confirmation_rejects_content_goal_coverage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = {
            "kind": "allincms_source_site_package_confirmation",
            "confirmedAt": "2026-07-01T00:00:00+00:00",
            "confirmedBy": "user",
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "isRemoteMutationAuthorization": False,
            "sourcePackage": str(package_path),
            "sourcePackageSha256": file_sha256(package_path),
            "sourceReviewPacket": str(review_packet_path),
            "sourceReviewPacketSha256": file_sha256(review_packet_path),
            "userConfirmationText": "User confirms the generated package for local planning only.",
            "acceptedFields": review_packet["confirmationFields"],
            "acceptedDeferrals": [],
            "blockedRemoteActionsStillRequireActionAuthorization": package["confirmationGate"]["blockedRemoteActions"],
            "confirmedCounts": {"pages": 1, "products": 1, "posts": 1},
            "contentGoalCoverage": {**review_packet["contentGoalCoverage"], "missing": ["posts"]},
        }
        for field in ("siteInfo.publicContact", "siteInfo.legalCompanyName", "domains.customDomain", "tracking.trackingCode"):
            confirmation["acceptedFields"].remove(field)
            confirmation["acceptedDeferrals"].append({"field": field, "decision": "defer", "reason": "Deferred for this local test."})
        issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
        assert "contentGoalCoverage must match source package coverage" in issues
        assert "contentGoalCoverage must match review packet contentGoalCoverage" in issues


def test_confirmation_rejects_review_packet_hash_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation_args = argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package after reviewing the current packet.",
            accepted_fields="contentPlan.forms,contentPlan.media",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="local hash mismatch test",
            output=str(root / "confirmation.json"),
            json=False,
        )
        confirmation = build_confirmation(confirmation_args)
        confirmation["sourceReviewPacketSha256"] = "0" * 64
        issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
        assert "sourceReviewPacketSha256 must match the current sourceReviewPacket file" in issues


def test_confirmation_rejects_source_package_hash_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation_args = argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package after reviewing the current packet.",
            accepted_fields="contentPlan.forms,contentPlan.media",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="local package hash mismatch test",
            output=str(root / "confirmation.json"),
            json=False,
        )
        confirmation = build_confirmation(confirmation_args)
        confirmation["sourcePackageSha256"] = "0" * 64
        issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
        assert "sourcePackageSha256 must match the current sourcePackage file" in issues


def test_confirmation_and_plan_preserve_content_quality_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] = 0
        package["contentPlan"]["taxonomyPlan"]["postCategories"] = []
        write_json(package_path, package)
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        assert "posts_present_without_post_categories" in review_packet["contentQualityReview"]["warnings"]
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation_args = argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package after reviewing quality warnings.",
            accepted_fields="contentPlan.forms,contentPlan.media",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="local quality warning test",
            output=str(root / "confirmation.json"),
            json=False,
        )
        confirmation = build_confirmation(confirmation_args)
        assert confirmation["contentQualityReview"] == review_packet["contentQualityReview"]
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
        assert plan["contentQualityReview"] == review_packet["contentQualityReview"]
        assert not validate_plan(plan)
        drifted = json.loads(json.dumps(confirmation))
        drifted["contentQualityReview"]["warnings"] = []
        issues = validate_confirmation_with_review_packet(drifted, package, review_packet)
        assert "contentQualityReview.reviewRequired must equal bool(warnings)" in issues
        assert "contentQualityReview must match review packet contentQualityReview" in issues
        drifted = json.loads(json.dumps(confirmation))
        drifted["wikiReview"]["sourceWikiMarkdownIndex"] = ""
        issues = validate_confirmation_with_review_packet(drifted, package, review_packet)
        assert "wikiReview.sourceWikiMarkdownIndex is required" in issues
        assert "wikiReview must match review packet wikiReview" in issues


def test_confirmation_and_plan_preserve_content_goal_overage_details() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        add_generated_post_overage(package)
        write_json(package_path, package)
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        assert "exceeds_declared_content_goal:posts" in review_packet["contentQualityReview"]["warnings"]
        assert review_packet["contentGoalOverages"]["details"]["posts"]["likelyExtraItems"][0]["slug"] == "generated-buyer-guide"
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation_args = argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated source package after reviewing overage details.",
            accepted_fields="",
            accepted_deferral=[],
            notes="local overage propagation test",
            output=str(root / "confirmation.json"),
            json=False,
        )
        confirmation = build_confirmation(confirmation_args)
        assert confirmation["contentGoalOverages"] == review_packet["contentGoalOverages"]
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
        assert plan["contentGoalOverages"] == review_packet["contentGoalOverages"]
        assert not validate_plan(plan)
        drifted_confirmation = json.loads(json.dumps(confirmation))
        drifted_confirmation["contentGoalOverages"]["details"].pop("posts")
        issues = validate_confirmation_with_review_packet(drifted_confirmation, package, review_packet)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages must match review packet contentGoalOverages" in issues
        drifted_plan = json.loads(json.dumps(plan))
        drifted_plan["contentGoalOverages"]["present"] = False
        issues = validate_plan(drifted_plan)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages.present must be true when contentQualityReview has overage warnings"
DEMO_DEFERRALS = [
    "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
    "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
    "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
]


def build_coverage_file(root: Path, package_path: Path, review_packet_path: Path, review_packet: dict) -> tuple[Path, dict]:
    package = json.loads(package_path.read_text(encoding="utf-8"))
    coverage = build_coverage(
        review_packet,
        review_packet_path=str(review_packet_path),
        package=package,
        package_path=str(package_path),
        objective="source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
    )
    coverage_path = root / "source-review-objective-coverage.json"
    write_json(coverage_path, coverage)
    return coverage_path, coverage


def test_confirmation_and_plan_carry_review_objective_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        coverage_path, coverage = build_coverage_file(root, package_path, review_packet_path, review_packet)
        assert coverage["reviewComplete"] is True
        assert coverage["complete"] is False
        assert coverage["missingForReview"] == []
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                source_review_objective_coverage=str(coverage_path),
                user_confirmation_text="User confirms the generated source package for a temporary demo site.",
                accepted_fields="contentPlan.forms,contentPlan.media",
                accepted_deferral=list(DEMO_DEFERRALS),
                notes="coverage carry",
                output=str(root / "confirmation.json"),
                json=False,
            )
        )
        assert confirmation["sourceReviewObjectiveCoverage"] == coverage
        assert not validate_confirmation_with_review_packet(confirmation, package, review_packet)
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
        assert not validate_plan(plan)
        assert plan["sourceReviewObjectiveCoverage"] == coverage
        # A plan that claims the full objective is complete must be rejected.
        drifted_plan = json.loads(json.dumps(plan))
        drifted_plan["sourceReviewObjectiveCoverage"]["complete"] = True
        issues = validate_plan(drifted_plan)
        assert any("sourceReviewObjectiveCoverage.complete must be false" in issue for issue in issues), issues
        # A confirmation that claims remote mutation is allowed must be rejected.
        drifted_confirmation = json.loads(json.dumps(confirmation))
        drifted_confirmation["sourceReviewObjectiveCoverage"]["remoteMutationAllowed"] = True
        issues = validate_confirmation_with_review_packet(drifted_confirmation, package, review_packet)
        assert any("sourceReviewObjectiveCoverage.remoteMutationAllowed must be false" in issue for issue in issues), issues


def test_plan_rejects_review_objective_coverage_binding_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        coverage_path, _coverage = build_coverage_file(root, package_path, review_packet_path, review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                source_review_objective_coverage=str(coverage_path),
                user_confirmation_text="User confirms the generated source package for a temporary demo site.",
                accepted_fields="contentPlan.forms,contentPlan.media",
                accepted_deferral=list(DEMO_DEFERRALS),
                notes="binding drift",
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
        # Point the plan's carried coverage at a different package than the plan itself.
        plan["sourceReviewObjectiveCoverage"]["sourcePackage"] = str(root / "some-other-package.json")
        issues = validate_plan(plan)
        assert any("sourceReviewObjectiveCoverage.sourcePackage must match the artifact sourcePackage" in i for i in issues), issues


def test_confirmation_rejects_review_objective_coverage_binding_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        coverage_path, coverage = build_coverage_file(root, package_path, review_packet_path, review_packet)
        # Point the carried coverage at a different review packet path.
        coverage["reviewPacket"] = str(root / "other-review-packet.json")
        write_json(coverage_path, coverage)
        raised = ""
        try:
            build_confirmation(
                argparse.Namespace(
                    package=str(package_path),
                    review_packet=str(review_packet_path),
                    source_review_objective_coverage=str(coverage_path),
                    user_confirmation_text="User confirms the generated source package for a temporary demo site.",
                    accepted_fields="contentPlan.forms,contentPlan.media",
                    accepted_deferral=list(DEMO_DEFERRALS),
                    notes="binding mismatch",
                    output=str(root / "confirmation.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            raised = str(exc)
        assert "sourceReviewObjectiveCoverage.reviewPacket must match --review-packet" in raised, raised


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source confirmation execution plan regression tests passed.")
