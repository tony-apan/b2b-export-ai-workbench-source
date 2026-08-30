#!/usr/bin/env python3
"""Regression tests for source inventory and source wiki helpers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from build_source_inventory import build_inventory, validate_inventory
from extract_source_materials import build_summary, extract_entry
from build_source_wiki import build_source_wiki
from export_source_wiki_markdown import build as export_source_wiki_markdown
from validate_source_wiki import validate_source_wiki


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_inventory_and_wiki_build() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "catalog.txt"
        write(source, "Example catalog source text")
        inventory_path = root / "source-index.json"
        inventory_args = argparse.Namespace(
            sources=[str(source)],
            recursive=False,
            run_label="test-run",
            output=str(inventory_path),
            json=False,
        )
        inventory = build_inventory(inventory_args)
        assert not validate_inventory(inventory)
        write_json(inventory_path, inventory)
        summary = root / "summary.json"
        write_json(
            summary,
            {
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Example source-backed description.",
                    "language": "en",
                    "industry": "example",
                },
                "wikiRefs": [str(root / "wiki/brief.md")],
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [{"heading": "Example", "body": "Plain page copy."}],
                        "mediaNeeds": [{"target": "home.hero", "kind": "hero-image"}],
                        "sourceRefs": ["src-001"],
                    }
                ],
                "products": [
                    {
                        "name": "Example Product",
                        "slug": "example-product",
                        "description": "Product summary.",
                        "content": [{"type": "paragraph", "text": "Product body."}],
                        "categories": ["Example Category"],
                        "tags": ["example-tag"],
                        "mediaNeeds": [{"target": "product.cover", "kind": "cover"}],
                        "sourceRefs": ["src-001"],
                    }
                ],
                "posts": [
                    {
                        "title": "Example Guide",
                        "slug": "example-guide",
                        "excerpt": "Guide excerpt.",
                        "content": [{"type": "paragraph", "text": "Guide body."}],
                        "categories": ["Buying Guides"],
                        "tags": ["selection"],
                        "mediaNeeds": [{"target": "post.cover", "kind": "cover"}],
                        "sourceRefs": ["src-001"],
                    }
                ],
                "siteInfo": {
                    "draftSeoTitle": "Example Demo",
                    "publicContact": "requires_user_confirmation",
                },
                "navigation": {
                    "items": [
                        {"label": "Home", "path": "/"},
                        {"label": "Products", "path": "/products"},
                    ]
                },
                "taxonomyPlan": {
                    "status": "needs_user_confirmation",
                    "productCategories": [{"label": "Example Category", "slug": "example-category", "sourceRefs": ["src-001"]}],
                },
                "mediaPolicy": {
                    "status": "needs_user_confirmation",
                    "allowedSources": ["source_files"],
                },
                "contactFormPolicy": {
                    "status": "needs_user_confirmation",
                    "notificationDestinationPolicy": "requires_user_confirmation",
                },
            },
        )
        wiki_args = argparse.Namespace(
            inventory=str(inventory_path),
            extraction_summary=str(summary),
            site_name="",
            site_description="",
            language="en",
            industry="unspecified",
            wiki_ref=[],
            output=str(root / "source-wiki.json"),
            json=False,
        )
        wiki = build_source_wiki(wiki_args)
        assert not validate_source_wiki(wiki, inventory)
        assert wiki["sourceSet"]["inputFiles"][0]["sha256"] == inventory["entries"][0]["sha256"]
        assert wiki["sourceSet"]["inputFiles"][0]["sizeBytes"] == inventory["entries"][0]["sizeBytes"]
        assert wiki["sourceSet"]["inputFiles"][0]["name"] == "catalog.txt"
        assert wiki["products"][0]["slug"] == "example-product"
        assert wiki["products"][0]["categories"] == ["Example Category"]
        assert wiki["posts"][0]["categories"] == ["Buying Guides"]
        assert wiki["taxonomyPlan"]["productCategories"][0]["slug"] == "example-category"
        assert wiki["pages"][0]["mediaNeeds"][0]["target"] == "home.hero"
        assert wiki["products"][0]["mediaNeeds"][0]["target"] == "product.cover"
        assert wiki["posts"][0]["mediaNeeds"][0]["target"] == "post.cover"
        assert wiki["siteInfo"]["draftSeoTitle"] == "Example Demo"
        assert wiki["navigation"]["items"][1]["path"] == "/products"
        assert wiki["mediaPolicy"]["status"] == "needs_user_confirmation"
        assert wiki["contactFormPolicy"]["notificationDestinationPolicy"] == "requires_user_confirmation"
        wiki_path = root / "source-wiki.json"
        write_json(wiki_path, wiki)
        export = export_source_wiki_markdown(
            argparse.Namespace(
                source_wiki=str(wiki_path),
                inventory=str(inventory_path),
                output_dir=str(root / "wiki"),
                fail_on_invalid=True,
                json=False,
            )
        )
        assert Path(export["files"]["index"]).exists()
        assert Path(export["files"]["products"]).read_text(encoding="utf-8").count("Example Product") >= 1
        assert Path(export["files"]["posts"]).read_text(encoding="utf-8").count("Example Guide") >= 1
        assert "products.md" in Path(export["files"]["index"]).read_text(encoding="utf-8")


def test_inventory_rejects_empty_source_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "empty-brief.txt"
        source.write_text("", encoding="utf-8")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="empty-source-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        assert inventory["summary"]["emptyFileCount"] == 1
        assert any("empty source files" in item for item in inventory["blockedUntil"])
        issues = validate_inventory(inventory)
        assert any("sizeBytes must be greater than zero" in issue for issue in issues), issues


def test_inventory_rejects_unsupported_and_sensitive_source_names() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unsupported = root / "catalog.weird"
        sensitive = root / "password-brief.txt"
        unsupported.write_text("unsupported source payload", encoding="utf-8")
        sensitive.write_text("sensitive filename source payload", encoding="utf-8")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(unsupported), str(sensitive)],
                recursive=False,
                run_label="unsupported-sensitive-source-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        assert inventory["summary"]["unsupportedCount"] == 1
        assert inventory["summary"]["sensitiveNameCount"] == 1
        assert any("unsupported source files" in item for item in inventory["blockedUntil"])
        assert any("sensitive values" in item for item in inventory["blockedUntil"])
        issues = validate_inventory(inventory)
        assert any("unsupported source files" in issue for issue in issues), issues
        assert any("sensitive-looking source file names" in issue for issue in issues), issues
        assert any("type must be supported" in issue for issue in issues), issues
        assert any("name may contain sensitive values" in issue for issue in issues), issues


def test_inventory_cli_fails_for_blocked_sources() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "password-brief.txt"
        output = root / "source-index.json"
        source.write_text("source payload with unsafe filename", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("build_source_inventory.py")),
                str(source),
                "--output",
                str(output),
            ],
            cwd=str(Path(__file__).resolve().parents[1]),
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 1
        assert "sensitive-looking source file names" in result.stderr
        assert not output.exists()


def test_source_wiki_preserves_structured_product_post_summaries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "site-plan.json"
        write_json(
            source,
            {
                "siteName": "Example Equipment Demo",
                "siteDescription": "Industrial equipment supplier website for buyer comparison.",
                "industry": "example equipment",
                "products": [
                    {
                        "name": "Example Industrial Fixture",
                        "slug": "example-industrial-fixture",
                        "category": "Industrial Products",
                        "summary": "High-efficiency industrial fixture for facilities, workshops, and logistics centers.",
                        "specs": {"wattage": "100W-240W", "ip": "IP65"},
                    }
                ],
                "posts": [
                    {
                        "title": "How to Choose Example Industrial Fixtures",
                        "slug": "choose-example-industrial-fixtures",
                        "summary": "Guide for selecting wattage, mounting height, and efficiency.",
                    }
                ],
            },
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="structured-json-wiki-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        inventory_path = root / "source-index.json"
        write_json(inventory_path, inventory)
        summary = root / "summary.json"
        source_ref = inventory["entries"][0]["sourceRef"]
        write_json(
            summary,
            {
                "site": {
                    "siteName": "Example Equipment Demo",
                    "siteDescription": "Industrial equipment supplier website for buyer comparison.",
                    "language": "en",
                    "industry": "example equipment",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [{"heading": "Home", "body": "Source-backed home page copy."}],
                        "sourceRefs": [source_ref],
                    }
                ],
                "products": [
                    {
                        "name": "Example Industrial Fixture",
                        "slug": "example-industrial-fixture",
                        "category": "Industrial Products",
                        "summary": "High-efficiency industrial fixture for facilities, workshops, and logistics centers.",
                        "specs": {"wattage": "100W-240W", "ip": "IP65"},
                        "sourceRefs": [source_ref],
                    }
                ],
                "posts": [
                    {
                        "title": "How to Choose Example Industrial Fixtures",
                        "slug": "choose-example-industrial-fixtures",
                        "summary": "Guide for selecting wattage, mounting height, and efficiency.",
                        "sourceRefs": [source_ref],
                    }
                ],
            },
        )
        wiki = build_source_wiki(
            argparse.Namespace(
                inventory=str(inventory_path),
                extraction_summary=str(summary),
                site_name="",
                site_description="",
                language="en",
                industry="unspecified",
                wiki_ref=[],
                output=str(root / "source-wiki.json"),
                json=False,
            )
        )
        assert not validate_source_wiki(wiki, inventory)
        product = wiki["products"][0]
        post = wiki["posts"][0]
        assert product["description"].startswith("High-efficiency industrial")
        assert product["categories"] == ["Industrial Products"]
        assert product["specs"] == [{"label": "wattage", "value": "100W-240W"}, {"label": "ip", "value": "IP65"}]
        assert "100W-240W" in product["content"][0]["text"]
        assert post["excerpt"].startswith("Guide for selecting wattage")
        assert "source-backed selection context" in post["content"][0]["text"]
        assert "requires review" not in json.dumps(wiki, ensure_ascii=False).lower()


def test_source_wiki_merges_duplicate_product_and_post_slugs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_a = root / "site-plan.json"
        source_b = root / "catalog.csv"
        write_json(source_a, {"siteName": "Example Demo"})
        write(source_b, "name,slug,description\nMerged Product,merged-product,CSV details")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source_a), str(source_b)],
                recursive=False,
                run_label="duplicate-slug-merge-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        inventory_path = root / "source-index.json"
        write_json(inventory_path, inventory)
        ref_a = inventory["entries"][0]["sourceRef"]
        ref_b = inventory["entries"][1]["sourceRef"]
        summary = root / "summary.json"
        write_json(
            summary,
            {
                "site": {
                    "siteName": "Example Demo",
                    "siteDescription": "Example duplicate merge test.",
                    "language": "en",
                    "industry": "example",
                },
                "pages": [
                    {
                        "title": "Home",
                        "path": "/",
                        "sections": [{"heading": "Home", "body": "Source-backed home page."}],
                        "sourceRefs": [ref_a],
                    }
                ],
                "products": [
                    {
                        "name": "Merged Product",
                        "slug": "merged-product",
                        "description": "Primary product description.",
                        "categories": ["Industrial"],
                        "tags": ["primary"],
                        "sourceRefs": [ref_a],
                    },
                    {
                        "name": "Merged Product",
                        "slug": "merged-product",
                        "summary": "Secondary summary from table.",
                        "specs": {"wattage": "150W", "rating": "IP65"},
                        "category": "Outdoor",
                        "tags": ["table"],
                        "mediaNeeds": [{"target": "product.cover", "kind": "cover"}],
                        "sourceRefs": [ref_b],
                    },
                ],
                "posts": [
                    {
                        "title": "Merged Buying Guide",
                        "slug": "merged-buying-guide",
                        "excerpt": "Primary buying guide excerpt.",
                        "categories": ["Guides"],
                        "tags": ["selection"],
                        "sourceRefs": [ref_a],
                    },
                    {
                        "title": "Merged Buying Guide",
                        "slug": "merged-buying-guide",
                        "content": [{"type": "paragraph", "text": "Detailed guide body from markdown."}],
                        "categories": ["Applications"],
                        "tags": ["installation"],
                        "mediaNeeds": [{"target": "post.cover", "kind": "cover"}],
                        "sourceRefs": [ref_b],
                    },
                ],
            },
        )
        wiki = build_source_wiki(
            argparse.Namespace(
                inventory=str(inventory_path),
                extraction_summary=str(summary),
                site_name="",
                site_description="",
                language="en",
                industry="unspecified",
                wiki_ref=[],
                output=str(root / "source-wiki.json"),
                json=False,
            )
        )
        assert not validate_source_wiki(wiki, inventory)
        assert len(wiki["products"]) == 1
        assert len(wiki["posts"]) == 1
        product = wiki["products"][0]
        post = wiki["posts"][0]
        assert product["slug"] == "merged-product"
        assert product["description"] == "Primary product description."
        assert product["categories"] == ["Industrial", "Outdoor"]
        assert product["tags"] == ["primary", "table"]
        assert product["specs"] == [{"label": "wattage", "value": "150W"}, {"label": "rating", "value": "IP65"}]
        assert product["mediaNeeds"] == [{"target": "product.cover", "kind": "cover"}]
        assert product["sourceRefs"] == [ref_a, ref_b]
        assert post["slug"] == "merged-buying-guide"
        assert post["excerpt"] == "Primary buying guide excerpt."
        assert post["categories"] == ["Guides", "Applications"]
        assert post["tags"] == ["selection", "installation"]
        assert post["mediaNeeds"] == [{"target": "post.cover", "kind": "cover"}]
        assert post["sourceRefs"] == [ref_a, ref_b]
        assert any("Detailed guide body" in block.get("text", "") for block in post["content"])


def test_structured_source_redacts_contact_values_and_preserves_extended_goals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "site-plan.json"
        contact_value = "contact" + "@" + "example.test"
        write_json(
            source,
            {
                "siteName": "Example Fixture Demo",
                "siteDescription": "Commercial fixture source package.",
                "industry": "example fixtures",
                "contentGoals": {
                    "pages": 3,
                    "products": 1,
                    "posts": 1,
                    "navigationItems": 4,
                    "productCategories": 1,
                    "postCategories": 1,
                    "forms": 1,
                    "media": 4,
                    "siteInfoFields": 5,
                },
                "siteInfo": {
                    "draftSeoTitle": "Example Fixture Demo",
                    "publicContact": contact_value,
                    "legalCompanyName": "Example Fixture Co.",
                },
                "forms": [{"name": "Project Inquiry", "fields": ["name", "email", "message"]}],
                "pages": [{"title": "Home", "path": "/", "sections": [{"heading": "Example Fixtures", "body": "Source-backed fixture homepage."}]}],
                "products": [{"name": "Example Fixture", "summary": "Workspace fixture.", "category": "Fixture Category"}],
                "posts": [{"title": "Example Fixture Buying Guide", "summary": "How to compare output and mounting requirements."}],
            },
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="structured-json-contact-redaction-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        inventory_path = root / "source-index.json"
        write_json(inventory_path, inventory)
        extract_args = argparse.Namespace(max_text_chars=12000, max_table_rows=40)
        extraction = extract_entry(inventory["entries"][0], extract_args)
        assert contact_value not in json.dumps(extraction, ensure_ascii=False)
        assert "[REDACTED_EMAIL]" in extraction["text"]
        summary = build_summary(
            inventory,
            [extraction],
            argparse.Namespace(
                inventory=str(inventory_path),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Fixture Demo",
                site_description="Commercial fixture source package.",
                language="en",
                industry="example fixtures",
                max_text_chars=12000,
            ),
        )
        dumped_summary = json.dumps(summary, ensure_ascii=False)
        assert contact_value not in dumped_summary
        assert summary["contentGoals"]["forms"] == 1
        assert summary["contentGoals"]["media"] == 4
        assert summary["contentGoals"]["siteInfoFields"] == 5
        public_contact = summary["siteInfo"]["publicContact"]
        assert public_contact["status"] == "provided_in_source_redacted"
        assert public_contact["contactType"] == "email"
        assert public_contact["requiresUserConfirmation"] is True

        summary_path = root / "summary.json"
        write_json(summary_path, summary)
        wiki = build_source_wiki(
            argparse.Namespace(
                inventory=str(inventory_path),
                extraction_summary=str(summary_path),
                site_name="",
                site_description="",
                language="en",
                industry="unspecified",
                wiki_ref=[],
                output=str(root / "source-wiki.json"),
                json=False,
            )
        )
        dumped_wiki = json.dumps(wiki, ensure_ascii=False)
        assert contact_value not in dumped_wiki
        assert not validate_source_wiki(wiki, inventory)
        assert wiki["siteInfo"]["publicContact"]["valueRedacted"] is True
        assert wiki["contentGoals"]["forms"] == 1
        assert wiki["contentGoals"]["media"] == 4
        assert wiki["contentGoals"]["siteInfoFields"] == 5


def test_source_wiki_rejects_unknown_source_ref() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(source, "Example source")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="test-run",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        wiki = {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [{"path": str(source), "type": "text", "sourceRef": "src-999"}],
                "wikiRefs": [str(root / "wiki.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example description.",
                "language": "en",
                "industry": "example",
            },
            "pages": [{"title": "Home", "path": "/", "sections": [{"heading": "Home", "body": "Plain"}], "sourceRefs": ["src-999"]}],
            "products": [{"name": "Product", "slug": "product", "description": "Desc", "content": [{"text": "Body"}], "sourceRefs": ["src-999"]}],
            "posts": [{"title": "Post", "slug": "post", "excerpt": "Excerpt", "content": [{"text": "Body"}], "sourceRefs": ["src-999"]}],
        }
        issues = validate_source_wiki(wiki, inventory)
        assert any("not present in inventory" in issue for issue in issues), issues


def test_source_wiki_rejects_source_hash_drift_against_inventory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(source, "Example source for hash continuity")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="test-run",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        entry = inventory["entries"][0]
        wiki = {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [
                    {
                        "path": str(source),
                        "type": "text",
                        "sourceRef": "src-001",
                        "sizeBytes": entry["sizeBytes"],
                        "sha256": "0" * 64,
                    }
                ],
                "wikiRefs": [str(root / "wiki.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example description.",
                "language": "en",
                "industry": "example",
            },
            "pages": [{"title": "Home", "path": "/", "sections": [{"heading": "Home", "body": "Plain"}], "sourceRefs": ["src-001"]}],
            "products": [{"name": "Product", "slug": "product", "description": "Desc", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
            "posts": [{"title": "Post", "slug": "post", "excerpt": "Excerpt", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
        }
        issues = validate_source_wiki(wiki, inventory)
        assert any("sha256 does not match inventory" in issue for issue in issues), issues


def test_source_wiki_rejects_bad_navigation_policy_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(source, "Example source")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="test-run",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        wiki = {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [
                    {
                        "path": str(source),
                        "type": "text",
                        "sourceRef": "src-001",
                        "sha256": inventory["entries"][0]["sha256"],
                        "sizeBytes": inventory["entries"][0]["sizeBytes"],
                    }
                ],
                "wikiRefs": [str(root / "wiki.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example description.",
                "language": "en",
                "industry": "example",
            },
            "pages": [{"title": "Home", "path": "/", "sections": [{"heading": "Home", "body": "Plain"}], "sourceRefs": ["src-001"], "mediaNeeds": ["bad"]}],
            "products": [{"name": "Product", "slug": "product", "description": "Desc", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
            "posts": [{"title": "Post", "slug": "post", "excerpt": "Excerpt", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
            "navigation": {"items": [{"label": "Bad", "path": "bad"}]},
            "taxonomyPlan": [],
            "mediaPolicy": [],
        }
        issues = validate_source_wiki(wiki, inventory)
        assert any("navigation.items[0].path" in issue for issue in issues), issues
        assert any("taxonomyPlan must be an object" in issue for issue in issues), issues
        assert any("mediaPolicy must be an object" in issue for issue in issues), issues
        assert any("pages[0].mediaNeeds[0]" in issue for issue in issues), issues


def test_source_wiki_rejects_bad_page_sections_before_package_build() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(source, "Example source")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="bad-page-section-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        wiki = {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [{"path": str(source), "type": "text", "sourceRef": "src-001"}],
                "wikiRefs": [str(root / "wiki.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example description.",
                "language": "en",
                "industry": "example",
            },
            "pages": [
                {
                    "title": "Home",
                    "path": "/",
                    "sections": [
                        {"heading": "Home", "body": "Source-backed page copy.", "sourceRefs": ["src-001"]},
                        {"heading": "", "body": ""},
                        "loose section text",
                    ],
                    "sourceRefs": [],
                }
            ],
            "products": [{"name": "Product", "slug": "product", "description": "Desc", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
            "posts": [{"title": "Post", "slug": "post", "excerpt": "Excerpt", "content": [{"text": "Body"}], "sourceRefs": ["src-001"]}],
        }
        issues = validate_source_wiki(wiki, inventory)
        assert any("pages[0].sections[1].heading is required" in issue for issue in issues), issues
        assert any("pages[0].sections[1].body is required" in issue for issue in issues), issues
        assert any("pages[0].sections[1].sourceRefs" in issue for issue in issues), issues
        assert any("pages[0].sections[2] must be an object" in issue for issue in issues), issues
        assert any("pages[0].sourceRefs must be non-empty" in issue for issue in issues), issues


def test_source_wiki_rejects_bad_product_post_content_blocks_before_package_build() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(source, "Example source")
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="bad-content-block-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        wiki = {
            "kind": "allincms_source_wiki",
            "sourceSet": {
                "inputFiles": [{"path": str(source), "type": "text", "sourceRef": "src-001"}],
                "wikiRefs": [str(root / "wiki.md")],
            },
            "site": {
                "siteName": "Example Demo",
                "siteDescription": "Example description.",
                "language": "en",
                "industry": "example",
            },
            "pages": [
                {
                    "title": "Home",
                    "path": "/",
                    "sections": [{"heading": "Home", "body": "Source-backed page copy."}],
                    "sourceRefs": ["src-001"],
                }
            ],
            "products": [
                {
                    "name": "Product",
                    "slug": "product",
                    "description": "Desc",
                    "content": [
                        {"text": "Product body", "sourceRefs": ["src-999"]},
                        {},
                        "loose product body",
                    ],
                    "sourceRefs": ["src-001"],
                }
            ],
            "posts": [
                {
                    "title": "Post",
                    "slug": "post",
                    "excerpt": "Excerpt",
                    "content": [{"text": "Post body", "sourceRefs": [""]}],
                    "sourceRefs": ["src-001"],
                }
            ],
        }
        issues = validate_source_wiki(wiki, inventory)
        assert any("products[0].content[1].text or body is required" in issue for issue in issues), issues
        assert any("products[0].content[2] must be an object" in issue for issue in issues), issues
        assert any("posts[0].content[0].sourceRefs" in issue for issue in issues), issues
        assert any("content uses sourceRefs not present in inventory: src-999" in issue for issue in issues), issues


if __name__ == "__main__":
    test_inventory_and_wiki_build()
    test_inventory_rejects_empty_source_files()
    test_inventory_rejects_unsupported_and_sensitive_source_names()
    test_inventory_cli_fails_for_blocked_sources()
    test_source_wiki_preserves_structured_product_post_summaries()
    test_source_wiki_merges_duplicate_product_and_post_slugs()
    test_structured_source_redacts_contact_values_and_preserves_extended_goals()
    test_source_wiki_rejects_unknown_source_ref()
    test_source_wiki_rejects_source_hash_drift_against_inventory()
    test_source_wiki_rejects_bad_navigation_policy_shape()
    test_source_wiki_rejects_bad_page_sections_before_package_build()
    test_source_wiki_rejects_bad_product_post_content_blocks_before_package_build()
    print("source files to wiki regression tests passed.")
