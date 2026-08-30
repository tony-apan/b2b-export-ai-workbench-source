#!/usr/bin/env python3
"""Regression tests for source wiki refinement plan generation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from make_source_wiki_refinement_plan import build


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def test_refinement_plan_groups_actionable_issues() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path = write_json(
            root / "source-wiki.json",
            {
                "kind": "allincms_source_wiki",
                "site": {"siteName": "Example"},
            },
        )
        package_path = write_json(root / "source-package.json", {"kind": "allincms_source_site_package"})
        plan = build(
            argparse.Namespace(
                source_wiki=wiki_path,
                package=package_path,
                source_wiki_issue=["products[0].sourceRefs must be non-empty"],
                package_issue=[
                    "contentPlan.products[0].description is too short for publication-ready copy; expected at least 40 characters",
                    "contentPlan.mediaPolicy.status must explicitly confirm media handling when media candidates or image needs exist",
                    "contentPlan.navigation.items must include /products when products are planned",
                ],
                review_packet_issue=[],
                output=str(root / "source-wiki-refinement-plan.json"),
                json=False,
            )
        )
        assert plan["reviewReadyBlocked"] is True
        assert plan["itemCount"] == 4
        assert plan["classificationCounts"]["needs_source_backed_rewrite"] == 1
        assert plan["classificationCounts"]["needs_media_policy_or_user_deferral"] == 1
        assert plan["classificationCounts"]["needs_navigation_confirmation"] == 1
        assert plan["classificationCounts"]["needs_source_reference_repair"] == 1
        assert Path(root / "source-wiki-refinement-plan.json").exists()


def test_declared_taxonomy_goal_issue_classifies_as_taxonomy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path = write_json(root / "source-wiki.json", {"kind": "allincms_source_wiki", "site": {"siteName": "Example"}})
        package_path = write_json(root / "source-package.json", {"kind": "allincms_source_site_package"})
        plan = build(
            argparse.Namespace(
                source_wiki=wiki_path,
                package=package_path,
                source_wiki_issue=[],
                package_issue=[
                    "content goal coverage missing declaredContentGoals.postCategories: declaredContentGoals.postCategories"
                ],
                review_packet_issue=[],
                output=str(root / "source-wiki-refinement-plan.json"),
                json=False,
            )
        )
        assert plan["classificationCounts"] == {"needs_taxonomy_confirmation": 1}
        assert plan["items"][0]["classification"] == "needs_taxonomy_confirmation"
        assert "category/tag labels" in plan["items"][0]["suggestedAction"]


if __name__ == "__main__":
    test_refinement_plan_groups_actionable_issues()
    test_declared_taxonomy_goal_issue_classifies_as_taxonomy()
    print("source wiki refinement plan regression tests passed.")
