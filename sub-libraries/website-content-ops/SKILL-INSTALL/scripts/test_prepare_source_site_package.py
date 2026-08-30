#!/usr/bin/env python3
"""Regression tests for local source-site package preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from prepare_source_site_package import build


def base_args(root: Path, source: Path) -> argparse.Namespace:
    return argparse.Namespace(
        sources=[str(source)],
        output_dir=str(root / "run"),
        recursive=False,
        run_label="test-source-run",
        site_name="Test Source Demo",
        site_description="A local test source package generated from user files.",
        language="en",
        industry="example",
        site_key="",
        frontend_base_url="",
        content_types="products,posts,themes/pages,site-info,forms,media,navigation",
        source_types="pdf_catalog,product_datasheet,company_profile,website_copy,spreadsheet,plain_brief",
        gap_ledger=[],
        resolved_gap_evidence=[],
        max_text_chars=12000,
        max_table_rows=40,
    )


def test_plain_source_prepares_artifacts_without_review_packet() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text(
            "This file describes a demo product family and possible article topics for a generated site.",
            encoding="utf-8",
        )
        summary = build(base_args(root, source))
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["packageStatus"] == "needs_source_wiki_refinement"
        artifacts = summary["artifacts"]
        for key in (
            "inventory",
            "rawExtractionSummary",
            "sourceWiki",
            "sourceWikiMarkdown",
            "sourceWikiMarkdownIndex",
            "sourceInputRequirements",
            "sourceSitePackage",
            "sourceWikiRefinementPlan",
            "sourceWikiRefinementBrief",
            "refinedSourceWikiTarget",
            "sourceExecutionStatus",
            "sourceNextStageHandoff",
        ):
            assert artifacts[key], key
            if key != "refinedSourceWikiTarget":
                assert Path(artifacts[key]).exists(), artifacts[key]
        assert artifacts["reviewPacket"] == ""
        refinement = json.loads(Path(artifacts["sourceWikiRefinementPlan"]).read_text(encoding="utf-8"))
        assert refinement["reviewReadyBlocked"] is True
        assert refinement["itemCount"] > 0
        brief = json.loads(Path(artifacts["sourceWikiRefinementBrief"]).read_text(encoding="utf-8"))
        assert brief["kind"] == "allincms_source_wiki_refinement_brief"
        assert brief["blockerCount"] == refinement["itemCount"]
        assert brief["outputRefinedSourceWiki"] == artifacts["refinedSourceWikiTarget"]
        assert brief["remoteMutationsPerformed"] is False
        assert Path(artifacts["sourceWikiMarkdown"]).exists()
        assert Path(artifacts["sourceWikiMarkdownIndex"]).exists()
        assert "Wiki Index" in Path(artifacts["sourceWikiMarkdownIndex"]).read_text(encoding="utf-8")
        status = json.loads(Path(artifacts["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        handoff = json.loads(Path(artifacts["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert handoff["sourceExecutionStatus"] == artifacts["sourceExecutionStatus"]
        assert handoff["currentStage"] == status["currentStage"]
        for stage in (
            "pages_site_info_handoff",
            "pages_site_info_execution",
            "taxonomy_execution_handoff",
            "taxonomy_execution",
            "forms_media_settings",
        ):
            assert stage in status["stages"], stage
        assert status["currentStage"] in {"review_packet", "confirmation"}, status
        issues = summary["validation"]["packagePublicationIssues"]
        assert issues
        assert any("Draft Product" in issue or "Draft Article" in issue or "review-required" in issue for issue in issues), issues
        assert summary["validation"]["refinementBriefBlockerCount"] == refinement["itemCount"]
        assert "source-wiki-refinement-brief.json" in summary["nextAction"]
        assert summary["contentQuality"]["inputFileCount"] == 1
        assert summary["contentQuality"]["contentCounts"]["pages"] >= 1
        assert "warnings" in summary["contentQuality"]


if __name__ == "__main__":
    test_plain_source_prepares_artifacts_without_review_packet()
    print("prepare source site package regression tests passed.")
