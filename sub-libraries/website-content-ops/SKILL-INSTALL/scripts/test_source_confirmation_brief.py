#!/usr/bin/env python3
"""Regression tests for source confirmation brief generation."""

from __future__ import annotations

import json
import copy
import subprocess
import sys
import tempfile
from pathlib import Path

from make_source_confirmation_brief import build_brief, markdown_lines
from run_source_file_rehearsal import build
from test_run_source_file_rehearsal import base_args, make_preflight, refined_target, wiki_for_rehearsal_inventory, write_json
from validate_source_confirmation_brief import validate_brief


def make_review_ready_summary(root: Path) -> dict:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    return build(args)


def test_brief_blocks_confirmation_when_rehearsal_is_not_review_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        summary = build(base_args(root, source))
        brief = build_brief(summary, str(root / "source-file-rehearsal-summary.json"))
        assert brief["kind"] == "allincms_source_confirmation_brief"
        assert brief["status"] == "needs_source_wiki_refinement"
        assert brief["reviewReady"] is False
        assert brief["localOnly"] is True
        assert brief["remoteMutationsPerformed"] is False
        assert brief["isRemoteMutationAuthorization"] is False
        assert brief["gate"]["mustNotCreateSaveUploadPublish"] is True
        assert brief["nextBlockingRequirement"] == "publishable pages/products/posts/site-info package review-ready"
        assert "Do not ask for user content confirmation" in " ".join(brief["nextActions"])
        assert Path(summary["confirmationBrief"]["json"]).exists()
        assert Path(summary["confirmationBrief"]["markdown"]).exists()
        assert Path(summary["confirmationBrief"]["validation"]).exists()
        assert not validate_brief(brief, summary)


def test_brief_summarizes_review_ready_confirmation_surface() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        brief = build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json"))
        assert brief["status"] == "waiting_for_user_content_confirmation"
        assert brief["reviewReady"] is True
        assert brief["confirmationPrepared"] is False
        assert brief["counts"]["pages"] >= 1
        assert brief["counts"]["products"] >= 1
        assert brief["counts"]["posts"] >= 1
        assert brief["contentGoalCoverage"]["complete"] is True
        assert brief["sourceReviewObjectiveCoverage"]["json"] == summary["artifacts"]["sourceReviewObjectiveCoverage"]
        assert brief["sourceReviewObjectiveCoverage"]["reviewComplete"] is True
        assert brief["sourceReviewObjectiveCoverage"]["complete"] is False
        assert brief["sourceReviewObjectiveCoverage"]["remoteMutationAllowed"] is False
        assert brief["sourceReviewObjectiveCoverage"]["missingForReview"] == []
        assert "remote_site_creation_not_started" in brief["sourceReviewObjectiveCoverage"]["missingForFinal"]
        assert brief["contentQualityReview"] == summary["confirmationReview"]["contentQualityReview"]
        assert Path(brief["wikiReview"]["sourceWiki"]).exists()
        assert Path(brief["wikiReview"]["sourceWikiMarkdown"]).exists()
        assert Path(brief["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        assert brief["commands"]["confirmationCommandTemplate"]
        assert brief["commands"]["confirmedExecutionCommandTemplate"]
        assert brief["executionIntake"]["mode"] == "await_user_confirmation_text"
        assert brief["executionIntake"]["requiresUserConfirmationText"] is True
        assert brief["executionIntake"]["requiresCreatePreflight"] is False
        assert brief["executionIntake"]["readyForGatedCreateSiteRunbook"] is False
        assert brief["executionIntake"]["sourcePackage"] == summary["artifacts"]["sourceSitePackage"]
        assert brief["executionIntake"]["reviewPacket"] == summary["confirmationReview"]["reviewPacket"]
        assert brief["executionIntake"]["nextCommandTemplate"] == brief["commands"]["confirmedExecutionCommandTemplate"]
        assert brief["userConfirmationPrompt"] == summary["confirmationReview"]["suggestedConfirmationText"]
        matrix_fields = {item["field"] for item in brief["confirmationDecisionMatrix"]}
        assert matrix_fields == set(summary["confirmationReview"]["confirmationFields"])
        assert {item["decision"] for item in brief["confirmationDecisionMatrix"]} <= {"accept", "defer"}
        assert all(item["blocksRemoteMutation"] is False for item in brief["confirmationDecisionMatrix"])
        assert brief["objectiveAudit"]["complete"] is False
        assert not validate_brief(brief, summary)
        md = "\n".join(markdown_lines(brief))
        assert "AllinCMS Source Confirmation Brief" in md
        assert "Content Quality Review" in md
        assert "Review Objective Coverage" in md
        assert "Full objective complete: false" in md
        assert "Remote mutation allowed: false" in md
        assert "Wiki Review Artifacts" in md
        assert "Confirmation Decision Matrix" in md
        assert "Execution Intake" in md
        assert "Mode: await_user_confirmation_text" in md
        assert "Markdown index:" in md
        assert "Is remote mutation authorization: false" in md
        assert "Only final source-run acceptance" in md


def test_brief_markdown_surfaces_content_quality_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        summary["confirmationReview"]["contentQualityReview"] = {
            **summary["confirmationReview"]["contentQualityReview"],
            "readyShape": False,
            "warnings": ["posts_present_without_post_categories"],
            "reviewRequired": True,
        }
        brief = build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json"))
        assert brief["contentQualityReview"]["reviewRequired"] is True
        assert not validate_brief(brief, summary)
        md = "\n".join(markdown_lines(brief))
        assert "Content Quality Review" in md
        assert "posts_present_without_post_categories" in md


def test_brief_markdown_surfaces_content_goal_overage_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        summary["confirmationReview"]["contentQualityReview"] = {
            **summary["confirmationReview"]["contentQualityReview"],
            "warnings": ["exceeds_declared_content_goal:posts"],
            "reviewRequired": True,
        }
        summary["confirmationReview"]["contentGoalOverages"] = {
            "present": True,
            "details": {
                "posts": {
                    "declared": 3,
                    "actual": 4,
                    "extraCount": 1,
                    "items": [
                        {
                            "title": "Generated Brief Article",
                            "slug": "generated-brief-article",
                            "sourceRefs": ["src-001"],
                        },
                        {
                            "title": "Generated Planning Checklist",
                            "slug": "generated-planning-checklist",
                            "sourceRefs": ["src-002"],
                        },
                        {
                            "title": "Generated Selection Guide",
                            "slug": "generated-selection-guide",
                            "sourceRefs": ["src-003"],
                        },
                        {
                            "title": "Generated Buyer Guide",
                            "slug": "generated-buyer-guide",
                            "sourceRefs": ["src-004"],
                        },
                    ],
                    "likelyExtraItems": [
                        {
                            "title": "Generated Buyer Guide",
                            "slug": "generated-buyer-guide",
                            "sourceRefs": ["src-004"],
                        }
                    ],
                    "selectionRule": "likelyExtraItems uses generated item order after the declared count; verify with sourceRefs before pruning.",
                }
            },
            "operatorNote": "Content goals are minimum scope; overages are non-blocking only when item-level details are shown before user confirmation.",
        }
        brief = build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json"))
        assert brief["contentGoalOverages"] == summary["confirmationReview"]["contentGoalOverages"]
        assert not validate_brief(brief, summary)
        md = "\n".join(markdown_lines(brief))
        assert "Content Goal Overages" in md
        assert "posts: declared 3, actual 4, extra 1" in md
        assert "likely extra: Generated Buyer Guide (generated-buyer-guide)" in md

        drifted = copy.deepcopy(brief)
        drifted["contentGoalOverages"]["details"] = {}
        issues = validate_brief(drifted, summary)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues
        assert "contentGoalOverages must match confirmationReview.contentGoalOverages" in issues


def test_brief_keeps_browser_boundary_after_confirmation_and_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        args.create_preflight = str(make_preflight(root))
        summary = build(args)
        brief = json.loads(Path(summary["confirmationBrief"]["json"]).read_text(encoding="utf-8"))
        assert brief["status"] == "confirmed_execution_prepared"
        assert brief["readyForBrowserStage"] == "create_site_handoff_ready"
        assert brief["nextBlockingRequirement"] == "remote site created or selected and bound to artifacts"
        assert brief["gate"]["isRemoteMutationAuthorization"] is False
        assert brief["executionIntake"]["mode"] == "run_gated_create_site"
        assert brief["executionIntake"]["readyForGatedCreateSiteRunbook"] is True
        assert brief["executionIntake"]["requiresCreatePreflight"] is False
        assert brief["executionIntake"]["createSiteRunbook"] == summary["artifacts"]["confirmedCreateSiteRunbook"]
        assert brief["executionIntake"]["createdSiteEvidenceBundle"] == summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"]
        assert brief["executionIntake"]["confirmationOutput"] == str(
            Path(summary["artifacts"]["confirmedExecutionSummary"]).parent / "confirmation-record.json"
        )
        assert Path(brief["executionIntake"]["confirmationOutput"]).exists()
        assert brief["commands"]["confirmationOutput"] == brief["executionIntake"]["confirmationOutput"]
        assert "schema capture" in " ".join(brief["nextActions"])
        assert not validate_brief(brief, summary)


def test_brief_execution_intake_collects_create_preflight_after_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
        summary = build(args)
        brief = json.loads(Path(summary["confirmationBrief"]["json"]).read_text(encoding="utf-8"))
        assert brief["status"] == "confirmed_execution_prepared"
        assert brief["readyForBrowserStage"] == "needs_create_site_preflight"
        assert brief["executionIntake"]["mode"] == "collect_create_preflight"
        assert brief["executionIntake"]["requiresCreatePreflight"] is True
        assert brief["executionIntake"]["readyForGatedCreateSiteRunbook"] is False
        assert brief["executionIntake"]["createPreflightTarget"] == summary["artifacts"]["confirmedCreateSitePreflightTarget"]
        assert brief["executionIntake"]["createSiteRunbook"] == ""
        assert brief["executionIntake"]["confirmedExecutionOutputDir"] == str(
            Path(summary["artifacts"]["confirmedExecutionSummary"]).parent
        )
        assert brief["executionIntake"]["confirmationOutput"] == str(
            Path(summary["artifacts"]["confirmedExecutionSummary"]).parent / "confirmation-record.json"
        )
        assert Path(brief["executionIntake"]["confirmationOutput"]).exists()
        assert brief["commands"]["confirmationOutput"] == brief["executionIntake"]["confirmationOutput"]
        assert not validate_brief(brief, summary)


def test_validator_rejects_authorizing_or_drifted_brief() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["isRemoteMutationAuthorization"] = True
        issues = validate_brief(brief, summary)
        assert "isRemoteMutationAuthorization must be false" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["commands"]["confirmationCommandTemplate"] = ""
        issues = validate_brief(brief, summary)
        assert "waiting confirmation brief must include confirmationCommandTemplate" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["contentGoalCoverage"]["missing"] = ["posts"]
        issues = validate_brief(brief, summary)
        assert "contentGoalCoverage.missing must be empty when reviewReady is true" in issues
        assert "contentGoalCoverage must match confirmationReview.contentGoalCoverage" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["contentQualityReview"]["warnings"] = ["unexpected_warning"]
        brief["contentQualityReview"]["reviewRequired"] = True
        issues = validate_brief(brief, summary)
        assert "contentQualityReview must match confirmationReview.contentQualityReview" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["sourceReviewObjectiveCoverage"]["complete"] = True
        issues = validate_brief(brief, summary)
        assert "sourceReviewObjectiveCoverage.complete must be false before final live acceptance" in issues
        assert "sourceReviewObjectiveCoverage.complete must match source rehearsal summary" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["sourceReviewObjectiveCoverage"]["json"] = ""
        issues = validate_brief(brief, summary)
        assert "sourceReviewObjectiveCoverage.json is required when reviewReady is true" in issues
        assert "sourceReviewObjectiveCoverage.json must match source rehearsal summary" in issues
        assert "sourceReviewObjectiveCoverage.json must match summary artifacts.sourceReviewObjectiveCoverage" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["wikiReview"]["sourceWikiMarkdownIndex"] = ""
        issues = validate_brief(brief, summary)
        assert "wikiReview.sourceWikiMarkdownIndex is required when reviewReady is true" in issues
        assert "wikiReview.sourceWikiMarkdownIndex must match summary artifacts.sourceWikiMarkdownIndex" in issues

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["confirmationDecisionMatrix"] = brief["confirmationDecisionMatrix"][:-1]
        issues = validate_brief(brief, summary)
        assert any(issue.startswith("confirmationDecisionMatrix missing fields:") for issue in issues)

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["confirmationDecisionMatrix"][0]["decision"] = "missing_decision"
        issues = validate_brief(brief, summary)
        assert any(".decision must be accept or defer" in issue for issue in issues)

        brief = copy.deepcopy(build_brief(summary, str(root / "rehearsal/source-file-rehearsal-summary.json")))
        brief["executionIntake"]["mode"] = "run_gated_create_site"
        issues = validate_brief(brief, summary)
        assert "executionIntake.mode must be await_user_confirmation_text while waiting for confirmation" in issues


def test_cli_json_stdout_is_parseable_and_writes_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        output = root / "brief.json"
        markdown = root / "brief.md"
        script = Path(__file__).resolve().parent / "make_source_confirmation_brief.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(summary_path),
                "--output",
                str(output),
                "--markdown-output",
                str(markdown),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_source_confirmation_brief"
        assert parsed["markdownOutput"] == str(markdown.resolve())
        assert output.exists()
        assert markdown.exists()
        assert "Wrote source confirmation brief" not in result.stdout


def test_validator_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        brief_path = Path(summary["confirmationBrief"]["json"])
        script = Path(__file__).resolve().parent / "validate_source_confirmation_brief.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(brief_path),
                "--summary",
                str(summary_path),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_source_confirmation_brief_validation"
        assert parsed["ok"] is True
        assert "validation passed" not in result.stdout.lower()


if __name__ == "__main__":
    test_brief_blocks_confirmation_when_rehearsal_is_not_review_ready()
    test_brief_summarizes_review_ready_confirmation_surface()
    test_brief_markdown_surfaces_content_quality_warnings()
    test_brief_markdown_surfaces_content_goal_overage_items()
    test_brief_keeps_browser_boundary_after_confirmation_and_preflight()
    test_brief_execution_intake_collects_create_preflight_after_confirmation()
    test_validator_rejects_authorizing_or_drifted_brief()
    test_cli_json_stdout_is_parseable_and_writes_markdown()
    test_validator_cli_json_stdout_is_parseable()
    print("source confirmation brief regression tests passed.")
