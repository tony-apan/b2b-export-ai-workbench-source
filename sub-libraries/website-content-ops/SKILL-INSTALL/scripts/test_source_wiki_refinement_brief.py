#!/usr/bin/env python3
"""Regression tests for source wiki refinement brief generation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from make_source_wiki_refinement_brief import build
from test_source_wiki_refinement_plan import write_json


def source_wiki() -> dict:
    return {
        "kind": "allincms_source_wiki",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceSet": {
            "inputFiles": [{"path": "/tmp/catalog.txt", "type": "text", "sourceRef": "src-001"}],
            "wikiRefs": ["/tmp/wiki/index.md"],
        },
        "site": {"siteName": "Example Site", "siteDescription": "Draft source-backed example site."},
        "pages": [{"title": "Home", "path": "/", "sections": [{"heading": "Home", "body": "Draft copy"}], "sourceRefs": ["src-001"]}],
        "products": [
            {
                "name": "Draft Product",
                "slug": "draft-product",
                "description": "Draft product placeholder requires source extraction.",
                "content": [{"type": "paragraph", "text": "Draft product content requires source extraction."}],
                "sourceRefs": ["src-001"],
            }
        ],
        "posts": [
            {
                "title": "Draft Article",
                "slug": "draft-article",
                "excerpt": "Draft article placeholder requires source extraction.",
                "content": [{"type": "paragraph", "text": "Draft article content requires source extraction."}],
                "sourceRefs": ["src-001"],
            }
        ],
    }


def refinement_plan() -> dict:
    return {
        "kind": "allincms_source_wiki_refinement_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "reviewReadyBlocked": True,
        "classificationCounts": {"needs_source_backed_rewrite": 2, "needs_media_policy_or_user_deferral": 1},
        "items": [
            {
                "sourceWikiTarget": "products[0].description",
                "classification": "needs_source_backed_rewrite",
                "issue": "contentPlan.products[0].description is too short for publication-ready copy",
                "suggestedAction": "Rewrite products[0].description with concise publishable copy derived from source refs.",
            },
            {
                "sourceWikiTarget": "mediaPolicy",
                "classification": "needs_media_policy_or_user_deferral",
                "issue": "contentPlan.mediaPolicy.status must explicitly confirm media handling",
                "suggestedAction": "Update mediaPolicy with source media candidates or explicit no-image deferral.",
            },
        ],
    }


def test_refinement_brief_preserves_safe_output_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path = write_json(root / "source-wiki.json", source_wiki())
        plan_path = write_json(root / "source-wiki-refinement-plan.json", refinement_plan())
        products_md = root / "wiki" / "products.md"
        products_md.parent.mkdir(parents=True, exist_ok=True)
        products_md.write_text("# Products\n\nDraft Product needs refinement.\n", encoding="utf-8")
        brief = build(
            argparse.Namespace(
                source_wiki=wiki_path,
                refinement_plan=plan_path,
                output=str(root / "source-wiki-refinement-brief.json"),
                output_refined_source_wiki=str(root / "source-wiki.refined.json"),
                site_markdown="",
                pages_markdown="",
                products_markdown=str(products_md),
                posts_markdown="",
                max_markdown_chars=2000,
                json=False,
            )
        )
        assert brief["kind"] == "allincms_source_wiki_refinement_brief"
        assert brief["localOnly"] is True
        assert brief["remoteMutationsPerformed"] is False
        assert brief["isUserAuthorization"] is False
        assert brief["blockerCount"] == 2
        assert brief["outputRefinedSourceWiki"].endswith("source-wiki.refined.json")
        assert brief["counts"]["products"] == 1
        assert brief["classificationCounts"]["needs_source_backed_rewrite"] == 2
        assert brief["requiredEdits"][0]["sourceWikiTarget"] == "products[0].description"
        assert "products" in brief["markdownContext"]
        assert "Draft Product" in brief["outputContract"]["mustRemove"][0]
        assert "apply_refined_source_wiki.py" in brief["validationCommands"][0]
        assert Path(root / "source-wiki-refinement-brief.json").exists()


def test_brief_policy_status_options_match_validator() -> None:
    """The enum values the brief advertises must equal what the validator accepts (no drift)."""
    from validate_source_site_package import (
        TAXONOMY_STATUS_ALLOWED,
        MEDIA_STATUS_ALLOWED,
        CONTACT_STATUS_ALLOWED,
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path = write_json(root / "source-wiki.json", source_wiki())
        plan_path = write_json(root / "source-wiki-refinement-plan.json", refinement_plan())
        brief = build(
            argparse.Namespace(
                source_wiki=wiki_path,
                refinement_plan=plan_path,
                output=str(root / "source-wiki-refinement-brief.json"),
                output_refined_source_wiki=str(root / "source-wiki.refined.json"),
                site_markdown="",
                pages_markdown="",
                products_markdown="",
                posts_markdown="",
                max_markdown_chars=2000,
                json=False,
            )
        )
        opts = brief["outputContract"]["policyStatusOptions"]
        assert set(opts["contentPlan.taxonomyPlan.status"]) == TAXONOMY_STATUS_ALLOWED
        assert set(opts["contentPlan.mediaPolicy.status"]) == MEDIA_STATUS_ALLOWED
        assert set(opts["contentPlan.contactFormPolicy.status"]) == CONTACT_STATUS_ALLOWED
        assert "product" in brief["outputContract"]["contentFloors"]


if __name__ == "__main__":
    test_refinement_brief_preserves_safe_output_contract()
    test_brief_policy_status_options_match_validator()
    print("source wiki refinement brief regression tests passed.")
