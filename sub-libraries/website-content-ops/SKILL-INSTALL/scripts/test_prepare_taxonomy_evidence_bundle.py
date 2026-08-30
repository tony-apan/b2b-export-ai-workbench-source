#!/usr/bin/env python3
"""Regression tests for taxonomy evidence bundle preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_taxonomy_evidence_bundle import build_bundle, validate_bundle
from test_apply_taxonomy_execution import taxonomy_handoff, write_json


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
        {"field": "contentPlan.taxonomyPlan", "decision": "accept", "blocksRemoteMutation": False}
    ]
    return handoff


def test_taxonomy_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "taxonomy-execution-handoff.json"
        handoff = taxonomy_handoff()
        handoff["siteKey"] = "demo123"
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "taxonomy-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["browserStepsExecutable"] is False
        assert bundle["handoffReadyForBrowserStage"] == ""
        assert bundle["handoffPreflightIssues"] == []
        assert bundle["actionCount"] == len(handoff["actions"])
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidencePath"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["validationCommand"]).exists()
        assert Path(bundle["applyCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["kind"] == "allincms_taxonomy_execution_evidence"
        assert template["sourceHandoff"] == str(handoff_path)
        assert template["siteKey"] == handoff["siteKey"]
        assert template["preMutationGatesPassed"] is False
        assert len(template["taxonomyMappings"]) == len(handoff["actions"])
        assert template["taxonomyMappings"][0]["targetIdentifier"] == handoff["actions"][0]["targetIdentifier"]
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert "apply_taxonomy_execution.py" in Path(bundle["applyCommand"]).read_text(encoding="utf-8")


def test_taxonomy_evidence_bundle_exposes_blocked_handoff_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "taxonomy-execution-handoff.json"
        handoff = taxonomy_handoff()
        handoff["siteKey"] = "demo123"
        handoff["readyForBrowserStage"] = "blocked_taxonomy_preflight"
        handoff["preflightIssues"] = ["preflight.setupPages.products"]
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "taxonomy-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["handoffReadyForBrowserStage"] == "blocked_taxonomy_preflight"
        assert bundle["handoffPreflightIssues"] == ["preflight.setupPages.products"]
        assert bundle["nextAction"] == "resolve taxonomy handoff preflight blockers before browser actions"


def test_taxonomy_evidence_bundle_preserves_source_context_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "taxonomy-execution-handoff.json"
        handoff = taxonomy_handoff()
        handoff["siteKey"] = "demo123"
        add_source_context(handoff)
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "taxonomy-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert bundle[key] == handoff[key]
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
            assert template[key] == handoff[key]


def test_taxonomy_evidence_bundle_rejects_missing_content_counts_with_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "taxonomy-execution-handoff.json"
        handoff = taxonomy_handoff()
        handoff["siteKey"] = "demo123"
        add_source_context(handoff)
        del handoff["contentCounts"]
        write_json(handoff_path, handoff)
        bundle = build_bundle(
            handoff=handoff,
            handoff_path=str(handoff_path),
            output_dir=root / "taxonomy-evidence-bundle",
        )
        assert "contentCounts is required when source context is present" in validate_bundle(bundle)


def test_taxonomy_evidence_bundle_rejects_executed_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = taxonomy_handoff()
        handoff["siteKey"] = "demo123"
        handoff["remoteMutationsPerformed"] = True
        try:
            build_bundle(
                handoff=handoff,
                handoff_path=str(root / "taxonomy-execution-handoff.json"),
                output_dir=root / "bundle",
            )
        except ValueError as exc:
            assert "local-only/no remote mutation" in str(exc)
        else:
            raise AssertionError("bundle should reject a mutating handoff")


if __name__ == "__main__":
    test_taxonomy_evidence_bundle_builds()
    test_taxonomy_evidence_bundle_exposes_blocked_handoff_preflight()
    test_taxonomy_evidence_bundle_preserves_source_context_when_present()
    test_taxonomy_evidence_bundle_rejects_missing_content_counts_with_source_context()
    test_taxonomy_evidence_bundle_rejects_executed_handoff()
    print("taxonomy evidence bundle regression tests passed.")
