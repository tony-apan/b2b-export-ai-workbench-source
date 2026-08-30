#!/usr/bin/env python3
"""Regression tests for pages/site-info evidence bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_pages_site_info_evidence_bundle import build_bundle, validate_bundle
from test_apply_pages_site_info_execution import pages_handoff, write_json


def add_source_context(handoff: dict) -> dict:
    handoff["contentGoalCoverage"] = {
        "complete": True,
        "checks": {"siteProposal": True, "pages": True, "products": True, "posts": True},
        "missing": [],
        "counts": {"pages": 1, "products": 1, "posts": 1},
    }
    handoff["contentCounts"] = {
        "pages": 1,
        "products": 1,
        "posts": 1,
        "forms": 1,
        "media": 2,
        "navigationItems": 3,
        "siteInfoFields": 2,
    }
    handoff["contentQualityReview"] = {"warnings": [], "reviewRequired": False}
    handoff["wikiReview"] = {
        "sourceWiki": "/tmp/source-wiki.json",
        "sourceWikiMarkdown": "/tmp/wiki",
        "sourceWikiMarkdownIndex": "/tmp/wiki/index.md",
    }
    handoff["confirmationDecisionMatrix"] = [
        {"field": "contentPlan.pages", "decision": "accept", "blocksRemoteMutation": False}
    ]
    return handoff


def reuse_handoff() -> dict:
    handoff = pages_handoff()
    handoff["defaultTemplateState"] = {
        "reuseExistingPagesFirst": True,
        "existingRoutePaths": ["/"],
    }
    for item in handoff["pages"]:
        item["executionStrategy"] = "reuse_existing_theme_page_first"
        item["actions"] = [
            {"action": "save_design", "existingPageReuse": True},
            {"action": "publish_design", "existingPageReuse": True},
            {"action": "enable_theme_page", "existingPageReuse": True},
            {"action": "bind_route", "existingPageReuse": True},
        ]
    return handoff


def test_pages_site_info_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "pages-site-info-handoff.json"
        handoff = pages_handoff()
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "pages-site-info-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["browserStepsExecutable"] is False
        assert bundle["pageCount"] == 1
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidencePath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_pages_site_info_execution_evidence"
        assert template["sourceHandoff"] == str(handoff_path)
        assert template["siteKey"] == handoff["siteKey"]
        assert template["preMutationGatesPassed"] is False
        assert template["pages"][0]["frontendUrl"] == "https://demo123.web.allincms.com"
        assert template["pages"][0]["homepageVerified"] is False
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert "apply_pages_site_info_execution.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")


def test_pages_site_info_evidence_bundle_preserves_source_context_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "pages-site-info-handoff.json"
        handoff = add_source_context(pages_handoff())
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "pages-site-info-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert bundle[key] == handoff[key]
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert template[key] == handoff[key]


def test_pages_site_info_evidence_bundle_omits_create_action_for_existing_page_reuse() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "pages-site-info-handoff.json"
        handoff = reuse_handoff()
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "pages-site-info-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        page = template["pages"][0]
        assert "create_theme_page" not in page["actionEvidence"]
        assert page["createThemePageVerified"] == "not_required_existing_page_reuse"
        assert page["designSaved"] is False
        assert page["designPublished"] is False
        assert page["pageEnabled"] is False
        assert page["routeBound"] is False
        assert set(page["actionEvidence"]) == {
            "save_design",
            "publish_design",
            "enable_theme_page",
            "bind_route",
        }


def test_pages_site_info_evidence_bundle_rejects_missing_content_counts_with_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "pages-site-info-handoff.json"
        handoff = add_source_context(pages_handoff())
        del handoff["contentCounts"]
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "pages-site-info-evidence-bundle",
        )
        assert "contentCounts is required when source context is present" in validate_bundle(bundle)


def test_pages_site_info_evidence_bundle_rejects_executed_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = pages_handoff()
        handoff["remoteMutationsPerformed"] = True
        try:
            build_bundle(
                handoff=handoff,
                handoff_path=str(root / "pages-site-info-handoff.json"),
                output_dir=root / "bundle",
            )
        except ValueError as exc:
            assert "local-only/no remote mutation" in str(exc)
        else:
            raise AssertionError("bundle should reject a mutating handoff")


if __name__ == "__main__":
    test_pages_site_info_evidence_bundle_builds()
    test_pages_site_info_evidence_bundle_preserves_source_context_when_present()
    test_pages_site_info_evidence_bundle_omits_create_action_for_existing_page_reuse()
    test_pages_site_info_evidence_bundle_rejects_missing_content_counts_with_source_context()
    test_pages_site_info_evidence_bundle_rejects_executed_handoff()
    print("pages/site-info evidence bundle regression tests passed.")
