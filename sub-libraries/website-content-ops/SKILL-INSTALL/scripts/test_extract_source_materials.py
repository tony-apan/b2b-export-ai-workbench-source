#!/usr/bin/env python3
"""Regression tests for raw source material extraction."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_source_inventory import build_inventory
from extract_source_materials import build_extraction


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_extract_text_csv_html_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "brief.txt",
            (
                "Example product overview for the site. Buyers compare supplier fit, application needs, "
                "quality expectations, installation context, and long-term sourcing reliability before "
                "selecting a product family for the project. The source also explains selection criteria, "
                "maintenance concerns, procurement timing, and the questions a buyer should ask before "
                "shortlisting products for a commercial deployment."
            ),
        )
        write(
            sources / "table.csv",
            "name,description,wattage,application\n"
            "Example Product,A source-backed product candidate with enough neutral description for extraction validation,120W,Example application\n",
        )
        write(sources / "page.html", "<html><body><h1>Example Heading</h1><p>HTML copy.</p></body></html>")
        write_json(sources / "data.json", {"site": "Example", "claim": "Source backed"})
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Demo",
                site_description="",
                language="en",
                industry="example",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        assert summary["extractionStats"]["extractedCount"] == 4
        assert summary["sourceRefs"]
        assert (root / "raw-extraction" / "summary.json").exists()
        assert (root / "raw-extraction" / "extractions.json").exists()
        assert "Example" in summary["pages"][0]["sections"][0]["body"]
        assert summary["products"][0]["name"] == "Example Product"
        assert summary["products"][0]["slug"] == "example-product"
        assert summary["products"][0]["specs"]
        assert summary["posts"]
        assert summary["posts"][0]["content"][0]["text"]
        assert summary["sourceFileFingerprints"]
        assert all(item["hashVerified"] is True for item in summary["sourceFileFingerprints"])
        extractions = json.loads((root / "raw-extraction" / "extractions.json").read_text(encoding="utf-8"))
        first = extractions["items"][0]
        assert first["sha256"]
        assert first["sizeBytes"] >= 0
        assert first["hashVerified"] is True


def test_extraction_blocks_changed_source_after_inventory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        write(
            source,
            (
                "Original source text explains buyer selection criteria, application context, "
                "product usage notes, maintenance requirements, and sourcing reliability."
            ),
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(source)],
                recursive=False,
                run_label="extract-hash-drift-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        write(source, "Changed source text after inventory was generated.")
        try:
            build_extraction(
                argparse.Namespace(
                    inventory=str(root / "source-index.json"),
                    output_dir=str(root / "raw-extraction"),
                    site_name="Example Demo",
                    site_description="",
                    language="en",
                    industry="example",
                    max_text_chars=4000,
                    max_table_rows=20,
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "sourceFileFingerprints contains unverified" in str(exc)
        else:
            raise AssertionError("changed source file should block extraction")


def test_extracts_csv_taxonomy_and_content_plan_pages_articles() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "products.csv",
            "name,slug,description,category,tags,wattage,lumen\n"
            "Example Product Alpha,example-product-alpha,High-efficiency example product for large facilities,Example Category A,\"facility,industrial\",150W,22500lm\n"
            "Example Product Beta,example-product-beta,Slim example product for commercial interiors,Example Category B,\"office,ceiling\",40W,4000lm\n",
        )
        write(
            sources / "content-plan.md",
            "# Content Plan\n\n"
            "Home page should introduce the catalog and project capability.\n\n"
            "About Us page should explain engineering support and export service.\n\n"
            "Contact page should provide an inquiry form.\n\n"
            "Article 1: How to choose example products for large facilities. "
            "Cover capacity planning, installation height, configuration angle, and operating efficiency.\n\n"
            "Article 2: Example products for commercial interiors. "
            "Cover usability control, configuration options, installation type, and maintenance.\n",
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-taxonomy-plan-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Demo",
                site_description="Source-backed example demo site.",
                language="en",
                industry="example industry",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        product = summary["products"][0]
        assert product["categories"] == ["Example Category A"]
        assert product["tags"] == ["facility", "industrial"]
        assert {page["path"] for page in summary["pages"]} >= {"/", "/about-us", "/contact"}
        about_page = next(page for page in summary["pages"] if page["path"] == "/about-us")
        about_text = about_page["sections"][0]["body"]
        assert "About Us explain" not in about_text
        assert "The about us page explains" in about_text
        assert [post["title"] for post in summary["posts"]] == [
            "How to choose example products for large facilities",
            "Example products for commercial interiors",
        ]
        assert all(post["slug"] != "products" for post in summary["posts"])
        published_text = json.dumps({"pages": summary["pages"], "posts": summary["posts"]}, ensure_ascii=False).lower()
        assert "review before publishing" not in published_text
        assert "source material" not in published_text
        assert "allincms" not in published_text


def test_extracts_structured_json_navigation_taxonomy_with_bound_source_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "products.csv",
            "name,description,category\n"
            "Example Product,Source-backed product for project planning and catalog validation,Example Category\n",
        )
        write_json(
            sources / "site-plan.json",
            {
                "navigation": [
                    {"label": "Home", "path": "/"},
                    {"label": "Products", "path": "/products"},
                    {"label": "Articles", "path": "/posts"},
                    {"label": "Contact", "path": "/contact"},
                ],
                "taxonomyPlan": {
                    "productCategories": ["Example Category"],
                    "postCategories": ["Example Guides", "Planning Notes"],
                },
                "pages": [
                    {
                        "title": "Contact",
                        "path": "/contact",
                        "sections": [{"heading": "Contact the team", "body": "Share project needs for a source-backed recommendation."}],
                        "sourceRefs": ["wrong-user-authored-ref"],
                    }
                ],
            },
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-structured-json-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Demo",
                site_description="Source-backed example demo site.",
                language="en",
                industry="example industry",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        assert [item["path"] for item in summary["navigation"]["items"]] == ["/", "/products", "/posts", "/contact"]
        assert summary["taxonomyPlan"]["postCategories"] == ["Example Guides", "Planning Notes"]
        json_ref = next(entry["sourceRef"] for entry in inventory["entries"] if entry["path"].endswith("site-plan.json"))
        assert summary["pages"][0]["sourceRefs"] == [json_ref]
        assert all("wrong-user-authored-ref" not in json.dumps(page, ensure_ascii=False) for page in summary["pages"])
        assert all(post["title"] != "Site Plan" for post in summary["posts"])


def test_extracts_markdown_heading_article_ideas_as_separate_posts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "article-ideas.md",
            "# Article Ideas\n\n"
            "## How to Choose Example Products for a Project\n"
            "A practical guide covering buyer goals, usage context, selection criteria, deployment method, documentation needs, and approval workflow.\n\n"
            "## Project Readiness Checklist for Buyers\n"
            "A checklist comparing existing conditions, operating requirements, budget timing, maintenance access, and replacement priorities before selecting new products.\n\n"
            "## Why Channel Partners Need Reliable Suppliers\n"
            "A B2B article about stable lead times, documentation support, private label packaging, and after-sales technical response.\n",
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-markdown-heading-articles-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Product Demo",
                site_description="Source-backed example product site.",
                language="en",
                industry="example products",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        assert [post["title"] for post in summary["posts"]] == [
            "How to Choose Example Products for a Project",
            "Project Readiness Checklist for Buyers",
            "Why Channel Partners Need Reliable Suppliers",
        ]
        assert all(post["slug"] for post in summary["posts"])
        assert all(post["sourceRefs"] for post in summary["posts"])
        first_tags = summary["posts"][0]["tags"]
        assert "How to Choose Example Products for a Project" in first_tags
        assert "a Project" not in first_tags
        assert all(len(tag.split()) >= 2 for post in summary["posts"] for tag in post["tags"])


def test_extracts_plain_markdown_headings_without_article_keyword() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "posts.md",
            "# Posts\n\n"
            "## Choosing Sensors for Harsh Rooms\n"
            "Buyers should compare temperature, vibration, enclosure ratings, wiring access, output signals, and service routines before selecting rugged sensors.\n\n"
            "## Retrofit Planning for Control Panels\n"
            "Teams should document panel space, power limits, communication protocols, downtime windows, and replacement priorities before approving a retrofit plan.\n\n"
            "## Distributor Project Checklist\n"
            "Channel partners should collect application details, signal requirements, environmental limits, delivery timing, and documentation needs before requesting a quote.\n",
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-plain-markdown-headings-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Sensors Demo",
                site_description="Source-backed example sensors site.",
                language="en",
                industry="industrial sensors",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        assert [post["title"] for post in summary["posts"]] == [
            "Choosing Sensors for Harsh Rooms",
            "Retrofit Planning for Control Panels",
            "Distributor Project Checklist",
        ]
        assert all(post["sourceRefs"] for post in summary["posts"])


def test_extracts_multiple_level_one_markdown_article_headings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sources"
        sources.mkdir()
        write(
            sources / "articles.md",
            "# Facility Product Buyer Guide\n\n"
            "Project buyers should compare performance output, installation context, operating savings, and maintenance access before selecting source-backed product options.\n\n"
            "# How to Choose Outdoor Project Equipment\n\n"
            "For outdoor project equipment, check protection rating, housing material, usage environment, configuration options, and installation constraints.\n\n"
            "# Benefits of Remote Site Equipment\n\n"
            "Remote site equipment can reduce installation dependency, but buyers should validate capacity, operating conditions, and local service requirements.\n",
        )
        inventory = build_inventory(
            argparse.Namespace(
                sources=[str(sources)],
                recursive=True,
                run_label="extract-level-one-markdown-articles-test",
                output=str(root / "source-index.json"),
                json=False,
            )
        )
        write_json(root / "source-index.json", inventory)
        summary = build_extraction(
            argparse.Namespace(
                inventory=str(root / "source-index.json"),
                output_dir=str(root / "raw-extraction"),
                site_name="Example Equipment Demo",
                site_description="Source-backed example equipment site.",
                language="en",
                industry="example equipment",
                max_text_chars=4000,
                max_table_rows=20,
                json=False,
            )
        )
        assert [post["title"] for post in summary["posts"]] == [
            "Facility Product Buyer Guide",
            "How to Choose Outdoor Project Equipment",
            "Benefits of Remote Site Equipment",
        ]
        assert all(len(post["content"][0]["text"]) >= 140 for post in summary["posts"])


if __name__ == "__main__":
    test_extract_text_csv_html_json()
    test_extraction_blocks_changed_source_after_inventory()
    test_extracts_csv_taxonomy_and_content_plan_pages_articles()
    test_extracts_structured_json_navigation_taxonomy_with_bound_source_refs()
    test_extracts_markdown_heading_article_ideas_as_separate_posts()
    test_extracts_plain_markdown_headings_without_article_keyword()
    test_extracts_multiple_level_one_markdown_article_headings()
    print("source material extraction regression tests passed.")
