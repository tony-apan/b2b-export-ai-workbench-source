#!/usr/bin/env python3
"""Regression tests for drafting a refined source wiki."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_refined_source_wiki import build as apply_refined
from draft_refined_source_wiki import build_refined_wiki
from make_source_wiki_refinement_brief import build as build_refinement_brief
from test_apply_refined_source_wiki import base_args, inventory, write_json
from validate_source_site_package import content_goal_coverage, validate_package
from validate_source_wiki import validate_source_wiki


def thin_source_wiki(root: Path, source_inventory: dict | None = None) -> dict:
    input_file = {"path": str(root / "brief.txt"), "type": "txt", "sourceRef": "src-example-brief"}
    if source_inventory and source_inventory.get("entries"):
        entry = source_inventory["entries"][0]
        input_file = {
            "path": entry["path"],
            "type": entry["type"],
            "sourceRef": entry["sourceRef"],
            "sizeBytes": entry.get("sizeBytes"),
            "sha256": entry.get("sha256"),
        }
    return {
        "kind": "allincms_source_wiki",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceSet": {
            "inputFiles": [input_file],
            "rawExtractionRefs": [str(root / "raw-extraction/summary.json")],
            "wikiRefs": [str(root / "wiki/source.md")],
        },
        "site": {
            "siteName": "Example Product Demo",
            "siteDescription": "Example product catalog demo for practical B2B buyers.",
            "language": "en",
            "industry": "example products",
        },
        "pages": [
            {
                "title": "About ExampleCo",
                "path": "/about",
                "purpose": "Introduce industrial example products capability",
                "sections": [{"heading": "About ExampleCo", "body": "Draft page copy requires review."}],
                "sourceRefs": ["src-example-brief"],
            },
            {
                "title": "Contact",
                "path": "/contact",
                "purpose": "Capture project inquiries",
                "sections": [{"heading": "Contact", "body": "Draft page copy requires review."}],
                "sourceRefs": ["src-example-brief"],
            },
        ],
        "products": [
            {
                "name": "Example Primary Product",
                "slug": "example-primary-product",
                "description": "Representative product option for demanding facilities and project buyers",
                "content": [
                    {
                        "type": "paragraph",
                        "text": "Representative product option for demanding facilities and project buyers specs: specification range; performance tier; protection rating. Category: Example Facility Products.",
                    }
                ],
                "specs": [{"label": "specs", "value": "specification range; performance tier; protection rating"}],
                "categories": ["Example Facility Products"],
                "sourceRefs": ["src-example-brief"],
            }
        ],
        "posts": [
            {
                "title": "How to Choose Example Products for Facility Projects",
                "slug": "how-to-choose-example-products-for-facility-projects",
                "excerpt": "Cover application fit, specification range, operating environment, and sourcing requirements.",
                "content": [
                    {
                        "type": "paragraph",
                        "text": "Cover application fit, specification range, operating environment, and sourcing requirements. This article helps buyers evaluate example products for project requirements.",
                    }
                ],
                "categories": ["Buying Guides"],
                "sourceRefs": ["src-example-brief"],
            }
        ],
        "taxonomyPlan": {"productCategories": ["Example Facility Products"], "postCategories": ["Buying Guides"]},
        "mediaPolicy": {"source": "use public placeholder images until user supplies real product photos"},
        "contactFormPolicy": {"fields": ["name", "email", "company", "message"]},
        "openQuestions": [
            "Review generated product candidates against source tables before final package confirmation.",
            "Confirm public contact details, media policy, domains, and tracking before launch.",
        ],
    }


def refinement_plan() -> dict:
    return {
        "kind": "allincms_source_wiki_refinement_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "reviewReadyBlocked": True,
        "classificationCounts": {"needs_source_backed_rewrite": 2},
        "items": [
            {
                "sourceWikiTarget": "source_wiki",
                "classification": "needs_source_backed_rewrite",
                "issue": "contentPlan.pages[0].sections contains review-required or unresolved wording",
                "suggestedAction": "Rewrite source wiki page copy.",
            },
            {
                "sourceWikiTarget": "source_wiki",
                "classification": "needs_source_backed_rewrite",
                "issue": "contentPlan.pages[1].sections is too short for publication-ready copy",
                "suggestedAction": "Rewrite source wiki page copy.",
            },
        ],
    }


def make_brief(root: Path, wiki_path: str, refined_path: str) -> str:
    plan_path = write_json(root / "source-wiki-refinement-plan.json", refinement_plan())
    return write_json(
        root / "source-wiki-refinement-brief.json",
        build_refinement_brief(
            argparse.Namespace(
                source_wiki=wiki_path,
                refinement_plan=plan_path,
                output=str(root / "source-wiki-refinement-brief.json"),
                output_refined_source_wiki=refined_path,
                site_markdown="",
                pages_markdown="",
                products_markdown="",
                posts_markdown="",
                max_markdown_chars=2000,
                json=False,
            )
        ),
    )


def test_draft_refined_source_wiki_expands_thin_pages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_wiki_path = write_json(root / "source-wiki.json", thin_source_wiki(root, source_inventory))
        refined_path = str(root / "source-wiki.refined.json")
        brief_path = make_brief(root, source_wiki_path, refined_path)
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=refined_path,
                validate_contract=False,
                json=False,
            )
        )
        assert not validate_source_wiki(refined, json.loads(Path(inventory_path).read_text(encoding="utf-8")))
        assert any(page["path"] == "/" for page in refined["pages"])
        about = next(page for page in refined["pages"] if page["path"] == "/about")
        contact = next(page for page in refined["pages"] if page["path"] == "/contact")
        assert len(about["sections"][0]["body"]) >= 140
        assert len(contact["sections"][0]["body"]) >= 140
        assert "requires review" not in about["sections"][0]["body"].lower()
        assert refined["siteInfo"]["draftSeoTitle"] == "Example Product Demo"
        assert {item["path"] for item in refined["navigation"]["items"]} >= {"/", "/products", "/posts", "/about", "/contact"}
        assert refined["mediaPolicy"]["status"] == "needs_user_confirmation"
        assert refined["contactFormPolicy"]["notificationDestinationPolicy"] == "requires_user_confirmation"


def test_draft_refined_source_wiki_rewrites_placeholder_products_and_posts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example equipment source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["site"] = {
            "siteName": "Example Equipment Demo",
            "siteDescription": "Industrial example equipment supplier website for buyers comparing efficient fixtures.",
            "language": "en",
            "industry": "example equipment",
        }
        source_data["products"] = [
            {
                "name": "Example Industrial Fixture",
                "slug": "example-industrial-fixture",
                "description": "Draft product description requires review.",
                "content": [{"type": "paragraph", "text": "Draft product detail requires review."}],
                "specs": {"wattage": "100W-240W", "ip": "IP65"},
                "categories": [],
                "sourceRefs": ["src-example-brief"],
            }
        ]
        source_data["posts"] = [
            {
                "title": "How to Choose Example Industrial Fixtures for Facilities",
                "slug": "choose-example-industrial-fixtures",
                "excerpt": "Draft article excerpt requires review.",
                "content": [{"type": "paragraph", "text": "Draft article body requires review."}],
                "categories": [],
                "sourceRefs": ["src-example-brief"],
            }
        ]
        source_data["contentGoals"] = {"pages": 2, "products": 1, "posts": 1, "productCategories": 1, "postCategories": 1}
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        product = refined["products"][0]
        post = refined["posts"][0]
        assert len(product["description"]) >= 40
        assert len(product["content"][0]["text"]) >= 100
        assert product["categories"] == ["Industrial Products"]
        assert product["specs"] == [{"label": "wattage", "value": "100W-240W"}, {"label": "ip", "value": "IP65"}]
        assert len(post["excerpt"]) >= 40
        assert len(post["content"][0]["text"]) >= 140
        assert post["categories"] == ["Buying Guides"]
        serialized = json.dumps({"products": refined["products"], "posts": refined["posts"]}, ensure_ascii=False).lower()
        assert "requires review" not in serialized
        assert "draft product" not in serialized
        assert "draft article" not in serialized
        write_json(refined_path, refined)
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary


def test_draft_refined_source_wiki_adds_static_navigation_pages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["pages"] = [
            {
                "title": "Home",
                "path": "/",
                "purpose": "homepage",
                "sections": [{"heading": "Home", "body": "Draft page copy requires review."}],
                "sourceRefs": ["src-example-brief"],
            }
        ]
        source_data["navigation"] = {
            "items": [
                {"label": "Home", "path": "/"},
                {"label": "Products", "path": "/products"},
                {"label": "Applications", "path": "/applications"},
                {"label": "Posts", "path": "/posts"},
                {"label": "Contact", "path": "/contact-us"},
            ]
        }
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = str(root / "source-wiki.refined.json")
        brief_path = make_brief(root, source_wiki_path, refined_path)
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=refined_path,
                validate_contract=False,
                json=False,
            )
        )
        paths = {page["path"] for page in refined["pages"]}
        assert {"/", "/applications", "/contact-us"} <= paths
        assert "/products" not in paths
        assert "/posts" not in paths
        applications = next(page for page in refined["pages"] if page["path"] == "/applications")
        assert applications["purpose"] == "navigation_static_page"
        assert len(applications["sections"][0]["body"]) >= 140
        assert not validate_source_wiki(refined, json.loads(Path(inventory_path).read_text(encoding="utf-8")))


def test_draft_refined_source_wiki_satisfies_declared_post_category_goal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["contentGoals"] = {"postCategories": 3}
        source_data["posts"][0]["tags"] = ["retrofit planning", "buyer sourcing"]
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        write_json(refined_path, refined)
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary
        package = json.loads(Path(summary["artifacts"]["sourceSitePackage"]).read_text(encoding="utf-8"))
        assert package["declaredContentGoals"]["postCategories"] == 3
        assert package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] >= 3
        labels = [item["label"] for item in package["contentPlan"]["taxonomyPlan"]["postCategories"]]
        assert "Buying Guides" in labels
        assert len(set(labels)) >= 3
        assert not validate_package(package, require_complete=True, require_publication_ready=True)


def test_draft_refined_source_wiki_adds_required_pages_from_source_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["contentGoals"] = {"pages": 4, "postCategories": 2}
        source_data["pages"] = [
            {
                "title": "Home",
                "path": "/",
                "purpose": "homepage",
                "sections": [
                    {
                        "heading": "Home",
                        "body": (
                            "Required pages: - Home - Applications - About Us - Contact Us "
                            "Contact policy: use a generic contact form until the user confirms public contact details."
                        ),
                    }
                ],
                "sourceRefs": ["src-example-brief"],
            }
        ]
        source_data["navigation"] = {
            "items": [
                {"label": "Home", "path": "/"},
                {"label": "Products", "path": "/products"},
                {"label": "Applications", "path": "/applications"},
                {"label": "Posts", "path": "/posts"},
                {"label": "Contact", "path": "/contact-us"},
            ]
        }
        source_data["posts"][0]["tags"] = ["retrofit planning"]
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        write_json(refined_path, refined)
        paths = {page["path"] for page in refined["pages"]}
        assert {"/", "/applications", "/about-us", "/contact-us"} <= paths
        about = next(page for page in refined["pages"] if page["path"] == "/about-us")
        assert about["purpose"] == "declared_source_page"
        assert len(about["sections"][0]["body"]) >= 140
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary
        package = json.loads(Path(summary["artifacts"]["sourceSitePackage"]).read_text(encoding="utf-8"))
        assert package["declaredContentGoals"]["pages"] == 4
        assert len(package["contentPlan"]["pages"]) >= 4
        assert not validate_package(package, require_complete=True, require_publication_ready=True)


def test_draft_refined_source_wiki_satisfies_declared_form_goal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["contentGoals"] = {"forms": 1}
        source_data["forms"] = []
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        assert len(refined["forms"]) == 1
        form = refined["forms"][0]
        assert form["slug"] == "project-inquiry-form"
        assert form["requiresFormSchemaCapture"] is True
        assert form["userConfirmationRequired"] is True
        assert form["sourceRefs"]
        write_json(refined_path, refined)
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary
        package = json.loads(Path(summary["artifacts"]["sourceSitePackage"]).read_text(encoding="utf-8"))
        assert package["declaredContentGoals"]["forms"] == 1
        assert len(package["contentPlan"]["forms"]) == 1
        assert package["contentPlan"]["contactFormPolicy"]["formCount"] == 1
        assert not validate_package(package, require_complete=True, require_publication_ready=True)


def test_draft_refined_source_wiki_satisfies_declared_media_goal_without_fabricating_urls() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_data = thin_source_wiki(root, source_inventory)
        source_data["contentGoals"] = {"media": 6}
        source_data["media"] = []
        source_data["mediaPolicy"] = {}
        for key in ("pages", "products", "posts"):
            for item in source_data[key]:
                item.pop("mediaNeeds", None)
        source_wiki_path = write_json(root / "source-wiki.json", source_data)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        write_json(refined_path, refined)
        media_needs = []
        for key in ("pages", "products", "posts"):
            for item in refined[key]:
                media_needs.extend(item.get("mediaNeeds", []))
        assert len(media_needs) >= 6
        for need in media_needs:
            assert need["source"] == "user_confirmation_or_public_url_required"
            assert need["status"] == "needs_user_confirmation"
            assert need["requiresSchemaCapture"] is True
            assert need["requiresFrontendImageProof"] is True
            assert need["sourceRefs"]
            serialized_need = json.dumps(need, ensure_ascii=False).lower()
            assert "http://" not in serialized_need
            assert "https://" not in serialized_need
            assert "placeholder" not in serialized_need
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary
        package = json.loads(Path(summary["artifacts"]["sourceSitePackage"]).read_text(encoding="utf-8"))
        coverage = content_goal_coverage(package)
        assert coverage["checks"]["declaredContentGoals.media"] is True
        assert coverage["counts"]["media"] >= 6
        media_policy = package["contentPlan"]["mediaPolicy"]
        assert media_policy["status"] == "needs_user_confirmation"
        assert media_policy["requiresSchemaCapture"] is True
        assert media_policy["requiresFrontendImageProof"] is True
        assert not validate_package(package, require_complete=True, require_publication_ready=True)


def test_drafted_refined_source_wiki_reaches_review_ready_after_apply() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "brief.txt").write_text("example products source brief.", encoding="utf-8")
        source_inventory = inventory(root)
        inventory_path = write_json(root / "source-index.json", source_inventory)
        source_wiki_path = write_json(root / "source-wiki.json", thin_source_wiki(root, source_inventory))
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, source_wiki_path, str(refined_path))
        refined = build_refined_wiki(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_brief=brief_path,
                inventory=inventory_path,
                output=str(refined_path),
                validate_contract=False,
                json=False,
            )
        )
        write_json(refined_path, refined)
        args = base_args(root, str(refined_path), inventory_path)
        args.refinement_brief = brief_path
        summary = apply_refined(args)
        assert summary["reviewReady"] is True, summary
        package = json.loads(Path(summary["artifacts"]["sourceSitePackage"]).read_text(encoding="utf-8"))
        assert not validate_package(package, require_complete=True, require_publication_ready=True)
        assert Path(summary["artifacts"]["reviewPacket"]).exists()


if __name__ == "__main__":
    test_draft_refined_source_wiki_expands_thin_pages()
    test_draft_refined_source_wiki_rewrites_placeholder_products_and_posts()
    test_draft_refined_source_wiki_adds_static_navigation_pages()
    test_draft_refined_source_wiki_satisfies_declared_post_category_goal()
    test_draft_refined_source_wiki_adds_required_pages_from_source_text()
    test_draft_refined_source_wiki_satisfies_declared_form_goal()
    test_draft_refined_source_wiki_satisfies_declared_media_goal_without_fabricating_urls()
    test_drafted_refined_source_wiki_reaches_review_ready_after_apply()
    print("draft refined source wiki regression tests passed.")
