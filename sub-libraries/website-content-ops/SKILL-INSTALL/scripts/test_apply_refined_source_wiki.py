#!/usr/bin/env python3
"""Regression tests for applying refined source wiki artifacts."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_refined_source_wiki import build
from make_source_wiki_refinement_brief import build as build_refinement_brief


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def inventory(root: Path) -> dict:
    source = root / "example-brief.txt"
    source.write_text("Example product family and buyer education brief.", encoding="utf-8")
    return {
        "kind": "allincms_source_inventory",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "entries": [
            {
                "path": str(source),
                "type": "txt",
                "sourceRef": "src-example-brief",
                "sizeBytes": source.stat().st_size,
                "sha256": "0" * 64,
            }
        ],
        "summary": {"fileCount": 1},
    }


def refined_wiki() -> dict:
    return {
        "kind": "allincms_source_wiki",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceSet": {
            "inputFiles": [{"path": "/tmp/example-brief.txt", "type": "txt", "sourceRef": "src-example-brief"}],
            "rawExtractionRefs": ["/tmp/raw-extraction/summary.json"],
            "wikiRefs": ["/tmp/wiki/example-product-family.md"],
        },
        "site": {
            "siteName": "Example Product Demo",
            "siteDescription": "A source-backed example website for buyers comparing representative product options and practical selection factors.",
            "language": "en",
            "industry": "example industry",
        },
        "siteInfo": {
            "draftSeoTitle": "Example Product Demo",
            "draftSeoDescription": "Example product solutions for buyers comparing use cases, selection criteria, and sourcing requirements.",
            "publicContact": "requires_user_confirmation",
            "legalCompanyName": "requires_user_confirmation",
        },
        "navigation": {
            "items": [
                {"label": "Home", "path": "/"},
                {"label": "Products", "path": "/products"},
                {"label": "Posts", "path": "/posts"},
                {"label": "Contact", "path": "/contact"},
            ]
        },
        "pages": [
            {
                "title": "Home",
                "path": "/",
                "purpose": "homepage",
                "sections": [
                    {
                        "heading": "Example Products For Demanding Projects",
                        "body": (
                            "Present the example product range for representative buyer projects, "
                            "with emphasis on practical benefits, reliability, comparison criteria, and source-backed selection factors."
                        ),
                    }
                ],
                "sourceRefs": ["src-example-brief"],
            },
            {
                "title": "Contact",
                "path": "/contact",
                "purpose": "contact_page",
                "sections": [
                    {
                        "heading": "Discuss Your Product Project",
                        "body": (
                            "Invite buyers to share application needs, installation environment, target specifications, and order timing, "
                            "while keeping final email, phone, and notification destination pending user confirmation."
                        ),
                    }
                ],
                "sourceRefs": ["src-example-brief"],
            },
        ],
        "products": [
            {
                "name": "Example Industrial Product",
                "slug": "example-industrial-product",
                "description": "Representative industrial product for buyers comparing durable options, application fit, and sourcing requirements.",
                "content": [
                    {
                        "type": "paragraph",
                        "text": (
                            "This example product is positioned for buyers who need reliable performance, clear specification guidance, "
                            "and practical supplier evaluation points in demanding operating environments."
                        ),
                    }
                ],
                "categories": ["Example Product Category"],
                "tags": ["example-selection"],
                "sourceRefs": ["src-example-brief"],
            }
        ],
        "posts": [
            {
                "title": "How To Choose Example Products For Industrial Use",
                "slug": "choose-example-products-industrial-use",
                "excerpt": "A practical guide for comparing example product options by application, specifications, operating environment, and reliability needs.",
                "content": [
                    {
                        "type": "paragraph",
                        "text": (
                            "Industrial buyers should compare products by application fit, specification targets, operating environment, supplier evidence, "
                            "operating schedule, and maintenance expectations before selecting a suitable product solution."
                        ),
                    }
                ],
                "categories": ["Buying Guides"],
                "tags": ["example-product-selection"],
                "sourceRefs": ["src-example-brief"],
            }
        ],
        "mediaPolicy": {
            "status": "needs_user_confirmation",
            "allowedSources": ["source_files", "public_urls_after_user_confirmation"],
        },
        "contactFormPolicy": {
            "status": "needs_user_confirmation",
            "notificationDestinationPolicy": "requires_user_confirmation",
            "ctaDestinationPolicy": "requires_user_confirmation",
        },
        "taxonomyPlan": {
            "status": "needs_user_confirmation",
            "productCategories": [{"label": "Example Product Category", "slug": "example-product-category", "sourceRefs": ["src-example-brief"]}],
            "postCategories": [{"label": "Buying Guides", "slug": "buying-guides", "sourceRefs": ["src-example-brief"]}],
        },
        "forms": [
            {
                "name": "Project Inquiry",
                "slug": "project-inquiry",
                "fields": [{"name": "name"}, {"name": "email"}, {"name": "project_details"}],
                "sourceRefs": ["src-example-brief"],
            }
        ],
        "media": [],
        "openQuestions": [],
    }


def placeholder_wiki() -> dict:
    data = refined_wiki()
    data["products"] = [
        {
            "name": "Draft Product",
            "slug": "draft-product",
            "description": "Draft product placeholder requires source extraction.",
            "content": [{"type": "paragraph", "text": "Draft product content requires source extraction."}],
            "sourceRefs": ["src-example-brief"],
        }
    ]
    return data


def invalid_wiki() -> dict:
    return {
        "kind": "allincms_source_wiki",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceSet": {"inputFiles": []},
        "site": {},
    }


def base_args(root: Path, wiki_path: str, inventory_path: str) -> argparse.Namespace:
    return argparse.Namespace(
        source_wiki=wiki_path,
        inventory=inventory_path,
        requirements="",
        site_key="",
        frontend_base_url="",
        confirmation="",
        execution_plan="",
        artifact_readiness="",
        created_site_binding="",
        pages_site_info_handoff="",
        pages_site_info_evidence="",
        pages_site_info_validation="",
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff="",
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        launch_acceptance="",
        output_dir=str(root / "refined-apply"),
        fail_on_invalid=False,
        json=False,
        refinement_brief="",
    )


def refinement_plan_for_apply() -> dict:
    return {
        "kind": "allincms_source_wiki_refinement_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "reviewReadyBlocked": True,
        "classificationCounts": {"needs_source_backed_rewrite": 1},
        "items": [
            {
                "sourceWikiTarget": "products[0].description",
                "classification": "needs_source_backed_rewrite",
                "issue": "placeholder product copy needs replacement",
                "suggestedAction": "Replace placeholder product copy with source-backed content.",
            }
        ],
    }


def make_refinement_brief(root: Path, wiki_path: str, refined_wiki_path: str) -> str:
    plan_path = write_json(root / "source-wiki-refinement-plan.json", refinement_plan_for_apply())
    return write_json(
        root / "source-wiki-refinement-brief.json",
        build_refinement_brief(
            argparse.Namespace(
                source_wiki=wiki_path,
                refinement_plan=plan_path,
                output=str(root / "source-wiki-refinement-brief.json"),
                output_refined_source_wiki=refined_wiki_path,
                site_markdown="",
                pages_markdown="",
                products_markdown="",
                posts_markdown="",
                max_markdown_chars=2000,
                json=False,
            )
        ),
    )


def test_apply_refined_source_wiki_generates_review_packet() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        wiki_path = write_json(root / "source-wiki.refined.json", refined_wiki())
        args = base_args(root, wiki_path, inventory_path)
        args.refinement_brief = make_refinement_brief(root, wiki_path, wiki_path)
        summary = build(args)
        assert summary["reviewReady"] is True, summary
        assert summary["readyForNextStage"] == "review_packet"
        assert summary["artifacts"]["hydratedSourceWiki"], summary
        hydrated = json.loads(Path(summary["artifacts"]["hydratedSourceWiki"]).read_text(encoding="utf-8"))
        source_inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
        assert hydrated["sourceSet"]["inputFiles"][0]["sha256"] == source_inventory["entries"][0]["sha256"]
        assert Path(summary["artifacts"]["sourceSitePackage"]).exists()
        assert Path(summary["artifacts"]["reviewPacket"]).exists()
        assert Path(summary["artifacts"]["sourceWikiRefinementPlan"]).exists()
        assert Path(summary["artifacts"]["refinedSourceWikiContractValidation"]).exists()
        contract = json.loads(Path(summary["artifacts"]["refinedSourceWikiContractValidation"]).read_text(encoding="utf-8"))
        assert contract["ok"] is True
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        refinement = json.loads(Path(summary["artifacts"]["sourceWikiRefinementPlan"]).read_text(encoding="utf-8"))
        assert refinement["reviewReadyBlocked"] is False
        assert refinement["itemCount"] == 0
        assert Path(summary["artifacts"]["sourceWikiMarkdown"]).exists()
        assert Path(summary["artifacts"]["sourceWikiMarkdownIndex"]).exists()
        assert "Example Industrial Product" in Path(summary["artifacts"]["sourceWikiMarkdownIndex"]).with_name("products.md").read_text(encoding="utf-8")
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "confirmation", status
        handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert handoff["currentStage"] == "confirmation"
        assert handoff["mode"] == "user_confirmation_required"


def test_apply_refined_source_wiki_blocks_placeholder_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        wiki_path = write_json(root / "source-wiki.placeholder.json", placeholder_wiki())
        summary = build(base_args(root, wiki_path, inventory_path))
        assert summary["reviewReady"] is False
        assert summary["readyForNextStage"] == "source_wiki_refinement"
        assert summary["artifacts"]["reviewPacket"] == ""
        assert Path(summary["artifacts"]["sourceWikiRefinementPlan"]).exists()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        refinement = json.loads(Path(summary["artifacts"]["sourceWikiRefinementPlan"]).read_text(encoding="utf-8"))
        assert refinement["reviewReadyBlocked"] is True
        assert refinement["itemCount"] > 0
        assert summary["validation"]["packagePublicationIssues"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "review_packet", status
        handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert handoff["currentStage"] == "review_packet"


def test_apply_refined_source_wiki_blocks_contract_drift_before_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        wiki_path = write_json(root / "source-wiki.refined.json", refined_wiki())
        args = base_args(root, wiki_path, inventory_path)
        args.refinement_brief = make_refinement_brief(root, wiki_path, str(root / "different-output.json"))
        summary = build(args)
        assert summary["reviewReady"] is False
        assert summary["artifacts"]["sourceSitePackage"] == ""
        assert summary["validation"]["refinedSourceWikiContractIssues"]
        assert any("path must match" in issue for issue in summary["validation"]["refinedSourceWikiContractIssues"])


def test_apply_refined_source_wiki_invalid_wiki_routes_to_source_package_refinement() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        wiki_path = write_json(root / "source-wiki.invalid.json", invalid_wiki())
        summary = build(base_args(root, wiki_path, inventory_path))
        assert summary["reviewReady"] is False
        assert summary["readyForNextStage"] == "source_wiki_refinement"
        assert summary["artifacts"]["sourceSitePackage"] == ""
        assert summary["validation"]["sourceWikiIssues"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["currentStage"] == "source_package", status
        handoff = json.loads(Path(summary["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert handoff["currentStage"] == "source_package"
        assert handoff["supported"] is True
        assert "apply_refined_source_wiki.py" in handoff["localCommand"]
        assert "<refined-source-wiki.json>" in handoff["localCommand"]


if __name__ == "__main__":
    test_apply_refined_source_wiki_generates_review_packet()
    test_apply_refined_source_wiki_blocks_placeholder_package()
    test_apply_refined_source_wiki_blocks_contract_drift_before_package()
    test_apply_refined_source_wiki_invalid_wiki_routes_to_source_package_refinement()
    print("apply refined source wiki regression tests passed.")
