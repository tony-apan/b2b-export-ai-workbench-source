#!/usr/bin/env python3
"""Regression tests for source-site package build and validation helpers."""

from __future__ import annotations

import sys

import json
import tempfile
from pathlib import Path

from build_source_site_package import build_package, hosted_cover_image, normalize_posts, normalize_products
from validate_manifest import validate_manifest
from validate_source_site_package import content_goal_coverage, validate_package


VALID_SHA = "a" * 64


class Args:
    def __init__(self, source_wiki: str, output: str) -> None:
        self.source_wiki = source_wiki
        self.requirements = ""
        self.site_key = ""
        self.frontend_base_url = ""
        self.output = output


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_valid_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "catalog.pdf"),
                            "name": "catalog.pdf",
                            "type": "pdf",
                            "sourceRef": "src-catalog",
                            "sizeBytes": 1234,
                            "sha256": VALID_SHA,
                        }
                    ],
                    "rawExtractionRefs": [str(root / "raw/catalog.json")],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                                "sourceRefs": ["src-catalog"],
                            }
                        ],
                        "mediaNeeds": [{"target": "home.hero", "kind": "hero-image", "sourceHint": "catalog hero image"}],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                                "sourceRefs": ["src-catalog"],
                            }
                        ],
                        "categories": ["Example Category"],
                        "tags": ["example-tag"],
                        "mediaNeeds": [{"target": "product.cover", "kind": "cover", "sourceHint": "catalog product image"}],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                                "sourceRefs": ["src-catalog"],
                            }
                        ],
                        "categories": ["Buying Guides"],
                        "tags": ["selection"],
                        "mediaNeeds": [{"target": "post.cover", "kind": "cover", "sourceHint": "source article image"}],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "contentGoals": {
                    "pages": 1,
                    "products": 1,
                    "posts": 1,
                    "navigationItems": 3,
                    "productCategories": 1,
                    "postCategories": 1,
                    "forms": 1,
                    "media": 4,
                    "siteInfoFields": 5,
                },
                "forms": [
                    {
                        "name": "Contact Form",
                        "slug": "contact-form",
                        "fields": [{"name": "name"}, {"name": "email"}, {"name": "message"}],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "media": [{"sourceRef": "src-catalog", "kind": "image", "usage": "product_or_post_cover"}],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        issues = validate_package(package, require_complete=True)
        assert not issues, issues
        publication_issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert not publication_issues, publication_issues
        assert package["sourceSet"]["inputFiles"][0]["sha256"] == VALID_SHA
        assert package["sourceSet"]["inputFiles"][0]["sizeBytes"] == 1234
        assert package["contentPlan"]["siteInfo"]["draftSeoTitle"] == "Example Demo"
        assert package["contentPlan"]["siteInfo"]["userConfirmationRequired"] is True
        assert package["contentPlan"]["navigation"]["items"][:3] == [
            {"label": "Home", "path": "/"},
            {"label": "Products", "path": "/products"},
            {"label": "Posts", "path": "/posts"},
        ]
        assert package["contentPlan"]["navigation"]["userConfirmationRequired"] is True
        taxonomy_plan = package["contentPlan"]["taxonomyPlan"]
        assert taxonomy_plan["status"] == "needs_user_confirmation"
        assert taxonomy_plan["productCategoryCount"] == 1
        assert taxonomy_plan["postCategoryCount"] == 1
        assert taxonomy_plan["productTagCount"] == 1
        assert taxonomy_plan["postTagCount"] == 1
        assert taxonomy_plan["productCategories"][0]["slug"] == "example-category"
        assert taxonomy_plan["postCategories"][0]["slug"] == "buying-guides"
        assert taxonomy_plan["requiresCategorySchemaCapture"] is True
        assert taxonomy_plan["requiresTagSchemaCapture"] is True
        media_policy = package["contentPlan"]["mediaPolicy"]
        assert media_policy["status"] == "needs_user_confirmation"
        assert media_policy["sourceCandidateCount"] == 1
        assert media_policy["pageMediaNeedCount"] == 1
        assert media_policy["productMediaNeedCount"] == 1
        assert media_policy["postMediaNeedCount"] == 1
        assert media_policy["requiresSchemaCapture"] is True
        assert media_policy["requiresFrontendImageProof"] is True
        contact_policy = package["contentPlan"]["contactFormPolicy"]
        assert contact_policy["status"] == "needs_user_confirmation"
        assert contact_policy["formCount"] == 1
        assert contact_policy["fieldNeedCount"] == 3
        assert contact_policy["notificationDestinationPolicy"] == "requires_user_confirmation"
        assert contact_policy["requiresFormSchemaCapture"] is True
        assert contact_policy["requiresSubmissionProofOrDeferral"] is True
        assert "contentPlan.siteInfo" in package["confirmationGate"]["fieldsNeedingUserConfirmation"]
        assert "contentPlan.navigation" in package["confirmationGate"]["fieldsNeedingUserConfirmation"]
        assert "contentPlan.taxonomyPlan" in package["confirmationGate"]["fieldsNeedingUserConfirmation"]
        assert "contentPlan.mediaPolicy" in package["confirmationGate"]["fieldsNeedingUserConfirmation"]
        assert "contentPlan.contactFormPolicy" in package["confirmationGate"]["fieldsNeedingUserConfirmation"]
        assert package["manifests"]["products"]["schemaVerified"] is False
        assert package["contentPlan"]["pages"][0]["sections"][0]["sourceRefs"] == ["src-catalog"]
        assert package["contentPlan"]["products"][0]["content"][0]["sourceRefs"] == ["src-catalog"]
        assert package["contentPlan"]["posts"][0]["content"][0]["sourceRefs"] == ["src-catalog"]
        assert package["confirmationGate"]["required"] is True
        coverage = content_goal_coverage(package)
        assert coverage["complete"] is True, coverage
        assert coverage["declaredContentGoals"]["productCategories"] == 1
        assert coverage["declaredContentGoals"]["postCategories"] == 1
        assert coverage["declaredContentGoals"]["forms"] == 1
        assert coverage["declaredContentGoals"]["media"] == 4
        assert coverage["declaredContentGoals"]["siteInfoFields"] == 5
        assert coverage["counts"]["forms"] == 1
        assert coverage["counts"]["media"] == 4
        assert coverage["counts"]["siteInfoFields"] == 5
        assert coverage["checks"]["pages"] is True
        assert coverage["checks"]["products"] is True
        assert coverage["checks"]["posts"] is True
        assert coverage["checks"]["siteInfo"] is True
        assert coverage["checks"]["manifests.products"] is True
        assert coverage["checks"]["manifests.posts"] is True


def test_package_validates_page_section_source_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "brief.md"),
                            "name": "brief.md",
                            "type": "markdown",
                            "sourceRef": "src-brief",
                            "sizeBytes": 1234,
                            "sha256": VALID_SHA,
                        }
                    ],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                                "sourceRefs": ["src-brief"],
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        assert package["contentPlan"]["pages"][0]["sections"][0]["sourceRefs"] == ["src-brief"]
        assert not validate_package(package, require_complete=True), package

        package["contentPlan"]["pages"][0]["sections"][0]["sourceRefs"] = ["src-missing"]
        issues = validate_package(package, require_complete=True)
        assert any("unknown source reference src-missing" in issue for issue in issues), issues

        package["contentPlan"]["pages"][0]["sections"][0]["sourceRefs"] = [""]
        issues = validate_package(package, require_complete=True)
        assert any("sourceRefs must contain non-empty source reference strings" in issue for issue in issues), issues

        package["contentPlan"]["pages"][0]["sections"][0]["sourceRefs"] = "src-brief"
        issues = validate_package(package, require_complete=True)
        assert any("sourceRefs must be an array when present" in issue for issue in issues), issues


def test_package_validates_product_post_content_block_source_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "catalog.pdf"),
                            "name": "catalog.pdf",
                            "type": "pdf",
                            "sourceRef": "src-catalog",
                            "sizeBytes": 1234,
                            "sha256": VALID_SHA,
                        }
                    ],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                                "sourceRefs": ["src-catalog"],
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                                "sourceRefs": ["src-catalog"],
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        assert package["contentPlan"]["products"][0]["content"][0]["sourceRefs"] == ["src-catalog"]
        assert package["contentPlan"]["posts"][0]["content"][0]["sourceRefs"] == ["src-catalog"]
        assert not validate_package(package, require_complete=True), package

        package["contentPlan"]["products"][0]["content"][0]["sourceRefs"] = ["src-missing"]
        issues = validate_package(package, require_complete=True)
        assert any("unknown source reference src-missing" in issue for issue in issues), issues

        package["contentPlan"]["products"][0]["content"][0]["sourceRefs"] = ["src-catalog"]
        package["contentPlan"]["posts"][0]["content"][0]["sourceRefs"] = [""]
        issues = validate_package(package, require_complete=True)
        assert any("sourceRefs must contain non-empty source reference strings" in issue for issue in issues), issues

        package["contentPlan"]["posts"][0]["content"][0]["sourceRefs"] = "src-catalog"
        issues = validate_package(package, require_complete=True)
        assert any("sourceRefs must be an array when present" in issue for issue in issues), issues


def test_complete_package_blocks_declared_forms_media_site_info_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "brief.md"), "type": "markdown", "sourceRef": "src-brief"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "contentGoals": {
                    "pages": 1,
                    "products": 1,
                    "posts": 1,
                    "navigationItems": 3,
                    "forms": 1,
                    "media": 1,
                    "siteInfoFields": 6,
                },
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        coverage = content_goal_coverage(package)
        assert coverage["counts"]["forms"] == 0
        assert coverage["counts"]["media"] == 0
        assert coverage["counts"]["siteInfoFields"] == 5
        assert "declaredContentGoals.forms" in coverage["missing"]
        assert "declaredContentGoals.media" in coverage["missing"]
        assert "declaredContentGoals.siteInfoFields" in coverage["missing"]
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("declaredContentGoals.forms" in issue for issue in issues), issues
        assert any("declaredContentGoals.media" in issue for issue in issues), issues
        assert any("declaredContentGoals.siteInfoFields" in issue for issue in issues), issues


def test_publication_ready_package_requires_source_hashes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "rawExtractionRefs": [str(root / "raw/catalog.json")],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, buyer problems, sourcing advantages, quality focus, "
                                    "and practical selection questions for visitors considering this product family."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains intended application, buyer-fit criteria, selection notes, "
                                    "project usage context, and practical value points supported by source material."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes selection "
                                    "factors, and connects source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        structural_issues = validate_package(package, require_complete=True)
        assert not any("sha256 is required" in issue for issue in structural_issues), structural_issues
        publication_issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("sourceSet.inputFiles[0].sha256 is required" in issue for issue in publication_issues), publication_issues
        assert any("sourceSet.inputFiles[0].sizeBytes is required" in issue for issue in publication_issues), publication_issues


def test_complete_package_blocks_declared_taxonomy_goal_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product One",
                        "slug": "example-product-one",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "categories": ["Example Category A"],
                        "sourceRefs": ["src-catalog"],
                    },
                    {
                        "name": "Example Product Two",
                        "slug": "example-product-two",
                        "description": "A second source-backed product summary for buyers comparing related options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This second product detail explains the application fit, selection notes, "
                                    "configuration considerations, and project buyer questions supported by the source catalog."
                                ),
                            }
                        ],
                        "categories": ["Example Category B"],
                        "sourceRefs": ["src-catalog"],
                    },
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "categories": ["Buying Guides"],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "contentGoals": {
                    "pages": 1,
                    "products": 2,
                    "posts": 1,
                    "navigationItems": 3,
                    "productCategories": 3,
                    "postCategories": 1,
                },
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        coverage = content_goal_coverage(package)
        assert coverage["counts"]["productCategories"] == 2
        assert coverage["declaredContentGoals"]["productCategories"] == 3
        assert coverage["complete"] is False
        assert "declaredContentGoals.productCategories" in coverage["missing"]
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("declaredContentGoals.productCategories" in issue for issue in issues), issues


def test_blocks_markdown_and_missing_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "brief.txt"), "type": "txt", "sourceRef": "src-brief"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [{"title": "Home", "path": "/", "sections": [{"body": "Plain copy."}], "sourceRefs": []}],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A concise product summary.",
                        "content": "**raw markdown**",
                        "sourceRefs": [],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A concise article excerpt.",
                        "content": [{"type": "paragraph", "text": "Structured article body."}],
                        "sourceRefs": ["src-brief"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        issues = validate_package(package, require_complete=True)
        assert issues
        assert any("raw Markdown" in issue for issue in issues)


def test_complete_package_blocks_missing_article_goal_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        coverage = content_goal_coverage(package)
        assert coverage["complete"] is False
        assert "posts" in coverage["missing"]
        assert "manifests.posts" in coverage["missing"]
        issues = validate_package(package, require_complete=True)
        assert any("content goal coverage missing posts" in issue for issue in issues), issues


def test_publication_ready_blocks_placeholders() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "brief.txt"), "type": "txt", "sourceRef": "src-brief"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Draft Site",
                    "siteDescription": "Draft site description requires user review.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [{"heading": "Home", "body": "Draft homepage copy requires review."}],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "products": [
                    {
                        "name": "Draft Product",
                        "slug": "draft-product",
                        "description": "Draft product placeholder requires source extraction.",
                        "content": [{"type": "paragraph", "text": "Draft product content requires source extraction."}],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "posts": [
                    {
                        "title": "Draft Article",
                        "slug": "draft-article",
                        "excerpt": "Draft article placeholder requires source extraction.",
                        "content": [{"type": "paragraph", "text": "Draft article content requires source extraction."}],
                        "sourceRefs": ["src-brief"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        structure_issues = validate_package(package, require_complete=True)
        assert not structure_issues, structure_issues
        publication_issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert publication_issues
        assert any("placeholder" in issue or "review-required" in issue for issue in publication_issues), publication_issues


def test_publication_ready_blocks_missing_site_info_and_navigation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        package["contentPlan"]["siteInfo"] = {}
        package["contentPlan"]["navigation"] = {"items": []}
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("contentPlan.siteInfo.draftSeoTitle" in issue for issue in issues), issues
        assert any("contentPlan.navigation.items" in issue for issue in issues), issues


def test_publication_ready_blocks_empty_or_placeholder_page_sections() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "catalog.pdf"),
                            "type": "pdf",
                            "sourceRef": "src-catalog",
                            "sha256": VALID_SHA,
                            "sizeBytes": 1234,
                        }
                    ],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, buyer questions, project fit, service context, application "
                                    "examples, and practical selection criteria for visitors comparing options."
                                ),
                            },
                            {"heading": "", "body": "TODO"},
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("contentPlan.pages[0].sections[1].heading" in issue for issue in issues), issues
        assert any("contentPlan.pages[0].sections[1].body" in issue for issue in issues), issues


def test_publication_ready_blocks_empty_or_placeholder_product_post_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "catalog.pdf"),
                            "type": "pdf",
                            "sourceRef": "src-catalog",
                            "sha256": VALID_SHA,
                            "sizeBytes": 1234,
                        }
                    ],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, buyer questions, project fit, service context, application "
                                    "examples, and practical selection criteria for visitors comparing options."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            },
                            {"type": "paragraph", "text": "TODO"},
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            },
                            {},
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("contentPlan.products[0].content[1] contains review-required" in issue for issue in issues), issues
        assert any("contentPlan.posts[0].content[1] must be non-empty" in issue for issue in issues), issues


def test_publication_ready_blocks_static_navigation_without_page_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [
                        {
                            "path": str(root / "catalog.pdf"),
                            "type": "pdf",
                            "sourceRef": "src-catalog",
                            "sha256": VALID_SHA,
                            "sizeBytes": 1234,
                        }
                    ],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "navigation": {
                    "items": [
                        {"label": "Home", "path": "/"},
                        {"label": "Products", "path": "/products"},
                        {"label": "Posts", "path": "/posts"},
                        {"label": "Applications", "path": "/applications"},
                    ]
                },
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("static navigation route without a matching contentPlan.pages entry" in issue for issue in issues), issues
        assert not any("path /products is a static navigation route" in issue for issue in issues), issues
        assert not any("path /posts is a static navigation route" in issue for issue in issues), issues

        package["contentPlan"]["pages"].append(
            {
                "title": "Applications",
                "path": "/applications",
                "purpose": "content_page",
                "sections": [
                    {
                        "heading": "Applications",
                        "body": (
                            "Explain the main application scenarios, buyer questions, project fit, and source-backed "
                            "usage considerations for visitors evaluating the product range."
                        ),
                    }
                ],
                "mediaNeeds": [],
                "sourceRefs": ["src-catalog"],
                "status": "draft_pending_user_confirmation",
            }
        )
        fixed_issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert not any("static navigation route without a matching contentPlan.pages entry" in issue for issue in fixed_issues), fixed_issues


def test_publication_ready_blocks_ambiguous_media_policy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "mediaNeeds": [{"target": "product.cover", "kind": "cover"}],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        package["contentPlan"]["mediaPolicy"]["status"] = "implicit"
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("mediaPolicy.status" in issue for issue in issues), issues


def test_publication_ready_blocks_ambiguous_contact_form_policy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "brief.txt"), "type": "txt", "sourceRef": "src-brief"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-brief"],
                    }
                ],
                "forms": [{"name": "Contact Form", "fields": [{"name": "email"}], "sourceRefs": ["src-brief"]}],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        package["contentPlan"]["contactFormPolicy"]["status"] = "implicit"
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("contactFormPolicy.status" in issue for issue in issues), issues


def test_publication_ready_blocks_ambiguous_taxonomy_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_wiki = root / "source-wiki.json"
        write_json(
            source_wiki,
            {
                "kind": "allincms_source_wiki",
                "sourceSet": {
                    "inputFiles": [{"path": str(root / "catalog.pdf"), "type": "pdf", "sourceRef": "src-catalog"}],
                    "wikiRefs": [str(root / "wiki/brief.md")],
                },
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Source-backed example positioning for buyers comparing reliable industrial products.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [
                            {
                                "heading": "Industrial Product Solutions",
                                "body": (
                                    "Introduce the product range, typical use cases, sourcing advantages, "
                                    "quality focus, and the practical buyer questions this demo site answers."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "A source-backed product summary for buyers comparing durable industrial options.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This product detail explains the intended application, buyer-fit criteria, "
                                    "selection notes, and the practical value points supported by the source catalog."
                                ),
                            }
                        ],
                        "categories": ["Example Category"],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "A source-backed guide excerpt for buyers comparing product options and supplier fit.",
                        "content": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "This article gives buyers a practical evaluation framework, summarizes the "
                                    "main selection factors, and connects the source material to concrete purchase questions."
                                ),
                            }
                        ],
                        "sourceRefs": ["src-catalog"],
                    }
                ],
            },
        )
        package = build_package(Args(str(source_wiki), str(root / "package.json")))
        package["contentPlan"]["taxonomyPlan"]["status"] = "implicit"
        issues = validate_package(package, require_complete=True, require_publication_ready=True)
        assert any("taxonomyPlan.status" in issue for issue in issues), issues
def test_hosted_cover_image_normalizes_and_rejects_local_paths() -> None:
    assert hosted_cover_image("https://cdn.example.com/a.png", "Fallback Alt") == {
        "url": "https://cdn.example.com/a.png",
        "alt": "Fallback Alt",
    }
    assert hosted_cover_image({"url": "https://cdn.example.com/b.png", "alt": "B alt"}, "Fallback Alt") == {
        "url": "https://cdn.example.com/b.png",
        "alt": "B alt",
    }
    # Local paths and non-http strings must be rejected: only uploaded public URLs may be carried.
    assert hosted_cover_image("/tmp/img/c.png", "Fallback Alt") is None
    assert hosted_cover_image("c.png", "Fallback Alt") is None
    assert hosted_cover_image(None, "Fallback Alt") is None


def test_cover_image_propagates_into_products_posts_and_validates_as_manifest() -> None:
    wiki = {
        "products": [
            {"name": "Cable A", "slug": "cable-a", "description": "d", "content": ["b"], "coverImage": "https://cdn.example.com/a.png"},
            {"name": "Cable B", "slug": "cable-b", "description": "d", "content": ["b"], "coverImage": {"url": "https://cdn.example.com/b.png", "alt": "B alt"}},
            {"name": "Cable C", "slug": "cable-c", "description": "d", "content": ["b"], "coverImage": "/local/path/c.png"},
            {"name": "Cable D", "slug": "cable-d", "description": "d", "content": ["b"]},
        ],
        "posts": [
            {"title": "Guide", "slug": "guide", "excerpt": "e", "content": ["b"], "coverImage": "https://cdn.example.com/g.png"},
        ],
    }
    products = normalize_products(wiki, ["src-1"])
    by_slug = {p["slug"]: p for p in products}
    assert by_slug["cable-a"]["coverImage"] == {"url": "https://cdn.example.com/a.png", "alt": "Cable A"}
    assert by_slug["cable-b"]["coverImage"] == {"url": "https://cdn.example.com/b.png", "alt": "B alt"}
    assert "coverImage" not in by_slug["cable-c"], "local path must not be carried into the manifest"
    assert "coverImage" not in by_slug["cable-d"]
    posts = normalize_posts(wiki, ["src-1"])
    assert posts[0]["coverImage"] == {"url": "https://cdn.example.com/g.png", "alt": "Guide"}
    # The carried cover object must satisfy the manifest coverImage/media contract.
    manifest = {
        "siteKey": "demo",
        "contentType": "products",
        "frontendBaseUrl": "https://demo.web.allincms.com",
        "schemaVerified": False,
        "fieldMapping": {},
        "payloadTemplate": {},
        "items": products,
    }
    assert not [e for e in validate_manifest(manifest, require_schema_verified=False) if "coverImage" in e]


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source site package regression tests passed.")
