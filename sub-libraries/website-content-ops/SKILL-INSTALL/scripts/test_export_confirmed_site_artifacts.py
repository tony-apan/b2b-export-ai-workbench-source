#!/usr/bin/env python3
"""Regression tests for confirmed source package artifact export."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from build_confirmed_site_execution_plan import build_plan
from build_source_site_package import build_package
from export_confirmed_site_artifacts import build_artifacts, validate_readiness
from make_source_package_confirmation import build_confirmation
from make_source_package_review_packet import build_review_packet
from make_source_review_objective_coverage import build_coverage


class PackageArgs:
    def __init__(self, source_wiki: str) -> None:
        self.source_wiki = source_wiki
        self.requirements = ""
        self.site_key = ""
        self.frontend_base_url = ""
        self.output = ""


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def prepare_confirmed_plan(root: Path) -> tuple[Path, Path, Path]:
    wiki_dir = root / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    source_file = root / "catalog.txt"
    source_file.write_text(
        "Example catalog source for a product, article, page, form, media, and site information demo.\n",
        encoding="utf-8",
    )
    source_bytes = source_file.read_bytes()
    (wiki_dir / "index.md").write_text("# Source Wiki\n\n- site\n- pages\n- products\n- posts\n", encoding="utf-8")
    write_json(
        wiki_dir / "manifest.json",
        {
            "kind": "allincms_source_wiki_markdown_export",
            "files": {"index": str(wiki_dir / "index.md")},
        },
    )
    source_wiki = root / "source-wiki.json"
    write_json(
        source_wiki,
        {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [
                    {
                        "path": str(source_file),
                        "type": "text",
                        "sourceRef": "src-001",
                        "sha256": hashlib.sha256(source_bytes).hexdigest(),
                        "sizeBytes": len(source_bytes),
                    }
                ],
                "wikiRefs": [str(wiki_dir / "manifest.json"), str(wiki_dir / "index.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example demo site for source-backed product publishing and article planning.",
                "language": "en",
                "industry": "example",
            },
            "pages": [
                {
                    "title": "Home",
                    "path": "/",
                    "sections": [
                        {
                            "heading": "Source-Backed Product Publishing",
                            "body": (
                                "The homepage explains the generated site structure, product range, buyer context, "
                                "article plan, and the source-backed information that will guide the temporary demo."
                            ),
                        }
                    ],
                    "sourceRefs": ["src-001"],
                }
            ],
            "products": [
                {
                    "name": "Industrial Demo Product",
                    "slug": "industrial-demo-product",
                    "description": "A source-backed product summary for validating AllinCMS upload preparation.",
                    "content": [
                        {
                            "text": (
                                "The product body describes the buyer use case, application context, selection notes, "
                                "and source-backed differentiators needed for a realistic demo upload."
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
                    "title": "Product Selection Guide",
                    "slug": "product-selection-guide",
                    "excerpt": "A source-backed article excerpt for validating generated publishing artifacts.",
                    "content": [
                        {
                            "text": (
                                "The article body explains how buyers can evaluate products, compare sourcing criteria, "
                                "and use the source material to frame a practical purchase decision."
                            )
                        }
                    ],
                    "categories": ["Buying Guides"],
                    "tags": ["selection"],
                    "sourceRefs": ["src-001"],
                }
            ],
            "navigation": {
                "items": [
                    {"label": "Home", "path": "/"},
                    {"label": "Products", "path": "/products"},
                    {"label": "Posts", "path": "/posts"},
                ]
            },
            "siteInfo": {"draftSeoTitle": "Example Demo"},
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
    package = build_package(PackageArgs(str(source_wiki)))
    package_path = root / "source-site-package.json"
    write_json(package_path, package)
    review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
    review_packet_path = root / "source-package-review-packet.json"
    write_json(review_packet_path, review_packet)
    confirmation = build_confirmation(
        argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            user_confirmation_text="User confirms the generated package for a temporary demo site.",
            accepted_fields="",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="test",
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
    return package_path, confirmation_path, plan_path


def test_export_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="demo-site",
                frontend_base_url="https://demo-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        assert not validate_readiness(readiness)
        assert readiness["contentGoalCoverage"]["complete"] is True
        assert readiness["contentGoalCoverage"]["checks"]["pages"] is True
        assert readiness["contentGoalCoverage"]["checks"]["products"] is True
        assert readiness["contentGoalCoverage"]["checks"]["posts"] is True
        assert readiness["contentCounts"]["navigationItems"] == 3
        assert readiness["contentCounts"]["siteInfoFields"] >= 1
        assert readiness["contentQualityReview"]["reviewRequired"] is False
        assert readiness["contentQualityReview"]["warnings"] == []
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        assert readiness["contentGoalOverages"] == confirmation["contentGoalOverages"]
        assert readiness["sourcePackageSha256"] == confirmation["sourcePackageSha256"]
        assert readiness["sourceReviewPacketSha256"] == confirmation["sourceReviewPacketSha256"]
        assert len(readiness["sourcePackageSha256"]) == 64
        assert readiness["wikiReview"] == confirmation["wikiReview"]
        assert readiness["confirmationDecisionMatrix"] == confirmation["confirmationDecisionMatrix"]
        assert Path(readiness["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        products = json.loads(Path(readiness["artifacts"]["productsManifest"]).read_text(encoding="utf-8"))
        posts = json.loads(Path(readiness["artifacts"]["postsManifest"]).read_text(encoding="utf-8"))
        assert products["schemaVerified"] is False
        assert posts["schemaVerified"] is False
        assert products["sourcePackageSha256"] == readiness["sourcePackageSha256"]
        assert posts["sourceReviewPacketSha256"] == readiness["sourceReviewPacketSha256"]
        assert products["siteKey"] == "demo-site"
        assert Path(readiness["artifacts"]["pagesPlan"]).exists()
        assert Path(readiness["artifacts"]["contactFormPolicyPlan"]).exists()
        contact_policy_plan = json.loads(Path(readiness["artifacts"]["contactFormPolicyPlan"]).read_text(encoding="utf-8"))
        assert contact_policy_plan["items"]["status"] == "needs_user_confirmation"
        assert contact_policy_plan["items"]["formCount"] == 1
        assert Path(readiness["artifacts"]["mediaPolicyPlan"]).exists()
        media_policy_plan = json.loads(Path(readiness["artifacts"]["mediaPolicyPlan"]).read_text(encoding="utf-8"))
        assert media_policy_plan["items"]["status"] == "needs_user_confirmation"
        assert media_policy_plan["items"]["sourceCandidateCount"] == 1
        assert Path(readiness["artifacts"]["taxonomyPlan"]).exists()
        taxonomy_plan = json.loads(Path(readiness["artifacts"]["taxonomyPlan"]).read_text(encoding="utf-8"))
        assert taxonomy_plan["items"]["productCategoryCount"] == 1
        assert taxonomy_plan["items"]["postCategoryCount"] == 1


def test_export_artifacts_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
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
                site_key="demo-site",
                frontend_base_url="https://demo-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        assert not validate_readiness(readiness)
        assert readiness["contentQualityReview"] == review_packet["contentQualityReview"]
        assert readiness["contentQualityReview"]["reviewRequired"] is True
        assert "posts_present_without_post_categories" in readiness["contentQualityReview"]["warnings"]
        assert readiness["wikiReview"] == review_packet["wikiReview"]
        assert readiness["confirmationDecisionMatrix"] == confirmation["confirmationDecisionMatrix"]


def test_export_artifacts_preserves_content_goal_overages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        add_generated_post_overage(package)
        write_json(package_path, package)
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                user_confirmation_text="User confirms the generated package after reviewing overage details.",
                accepted_fields="",
                accepted_deferral=[],
                notes="overage propagation test",
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
                site_key="demo-site",
                frontend_base_url="https://demo-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        assert not validate_readiness(readiness)
        assert readiness["contentGoalOverages"] == review_packet["contentGoalOverages"]
        assert readiness["contentGoalOverages"]["details"]["posts"]["likelyExtraItems"][0]["slug"] == "generated-buyer-guide"
        drifted_plan = json.loads(json.dumps(plan))
        drifted_plan["contentGoalOverages"]["details"].pop("posts")
        write_json(plan_path, drifted_plan)
        try:
            build_artifacts(
                argparse.Namespace(
                    package=str(package_path),
                    confirmation=str(confirmation_path),
                    execution_plan=str(plan_path),
                    site_key="demo-site",
                    frontend_base_url="https://demo-site.web.allincms.com",
                    output_dir=str(root / "artifacts-drifted"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "contentGoalOverages" in str(exc)
        else:
            raise AssertionError("drifted execution-plan overage details should block artifact export")


def test_export_artifacts_rejects_missing_wiki_index() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        Path(confirmation["wikiReview"]["sourceWikiMarkdownIndex"]).unlink()
        try:
            build_artifacts(
                argparse.Namespace(
                    package=str(package_path),
                    confirmation=str(confirmation_path),
                    execution_plan=str(plan_path),
                    site_key="demo-site",
                    frontend_base_url="https://demo-site.web.allincms.com",
                    output_dir=str(root / "artifacts"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "wikiReview" in str(exc)
        else:
            raise AssertionError("missing readable wiki index should block artifact export")


def test_export_artifacts_rejects_incomplete_content_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["contentCounts"].pop("navigationItems", None)
        write_json(plan_path, plan)
        try:
            build_artifacts(
                argparse.Namespace(
                    package=str(package_path),
                    confirmation=str(confirmation_path),
                    execution_plan=str(plan_path),
                    site_key="demo-site",
                    frontend_base_url="https://demo-site.web.allincms.com",
                    output_dir=str(root / "artifacts"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "contentCounts" in str(exc)
        else:
            raise AssertionError("missing navigationItems count should block artifact export")


def _confirmation_with_coverage(root: Path, package_path: Path) -> tuple[Path, Path, dict]:
    review_packet_path = root / "source-package-review-packet.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    review_packet = json.loads(review_packet_path.read_text(encoding="utf-8"))
    coverage = build_coverage(
        review_packet,
        review_packet_path=str(review_packet_path),
        package=package,
        package_path=str(package_path),
        objective="source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
    )
    coverage_path = root / "source-review-objective-coverage.json"
    write_json(coverage_path, coverage)
    confirmation = build_confirmation(
        argparse.Namespace(
            package=str(package_path),
            review_packet=str(review_packet_path),
            source_review_objective_coverage=str(coverage_path),
            user_confirmation_text="User confirms the generated source package for a temporary demo site.",
            accepted_fields="",
            accepted_deferral=[
                "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
            ],
            notes="coverage export",
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
    return confirmation_path, plan_path, coverage


def test_export_artifacts_carries_review_objective_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, _confirmation_path, _plan_path = prepare_confirmed_plan(root)
        confirmation_path, plan_path, coverage = _confirmation_with_coverage(root, package_path)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="demo-site",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        assert not validate_readiness(readiness)
        assert readiness["sourceReviewObjectiveCoverage"] == coverage
        assert readiness["sourceReviewObjectiveCoverage"]["reviewComplete"] is True
        assert readiness["sourceReviewObjectiveCoverage"]["complete"] is False


def test_export_artifacts_rejects_review_objective_coverage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, _confirmation_path, _plan_path = prepare_confirmed_plan(root)
        confirmation_path, plan_path, _coverage = _confirmation_with_coverage(root, package_path)
        # Plan that drops the carried coverage while the confirmation still carries it.
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan.pop("sourceReviewObjectiveCoverage")
        drift_plan_path = root / "execution-plan-missing-coverage.json"
        write_json(drift_plan_path, plan)
        try:
            build_artifacts(
                argparse.Namespace(
                    package=str(package_path),
                    confirmation=str(confirmation_path),
                    execution_plan=str(drift_plan_path),
                    site_key="demo-site",
                    frontend_base_url="",
                    output_dir=str(root / "artifacts-drift"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "execution plan: sourceReviewObjectiveCoverage is required when present in source context" in str(exc), str(exc)
        else:
            raise AssertionError("dropping carried coverage from the plan should block artifact export")


if __name__ == "__main__":
    test_export_artifacts()
    test_export_artifacts_preserves_content_quality_warning()
    test_export_artifacts_preserves_content_goal_overages()
    test_export_artifacts_rejects_missing_wiki_index()
    test_export_artifacts_rejects_incomplete_content_counts()
    test_export_artifacts_carries_review_objective_coverage()
    test_export_artifacts_rejects_review_objective_coverage_drift()
    print("confirmed site artifact export regression tests passed.")
