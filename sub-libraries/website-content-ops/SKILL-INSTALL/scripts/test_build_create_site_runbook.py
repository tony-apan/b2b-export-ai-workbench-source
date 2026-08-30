#!/usr/bin/env python3
"""Regression tests for create-site browser runbook preparation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from build_confirmed_create_site_handoff import AUTH_PLACEHOLDER
from build_confirmed_create_site_handoff import build_handoff as build_create_site_handoff
from build_create_site_runbook import build_runbook, validate_runbook
from test_confirmed_create_site_handoff import prepare_inputs, write_json


def prepared_handoff(root: Path) -> tuple[dict, str]:
    args = prepare_inputs(root)
    handoff = build_create_site_handoff(args)
    handoff_path = root / "create-site-handoff.json"
    write_json(handoff_path, handoff)
    return handoff, str(handoff_path)


def prepared_handoff_with_post_overage(root: Path) -> tuple[dict, str]:
    args = prepare_inputs(root, with_post_overage=True)
    handoff = build_create_site_handoff(args)
    handoff_path = root / "create-site-handoff.json"
    write_json(handoff_path, handoff)
    return handoff, str(handoff_path)


def test_create_site_runbook_builds_from_confirmed_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff, handoff_path = prepared_handoff(root)
        authorization_record = str(root / "authorization-create-site.json")
        runbook = build_runbook(
            handoff=handoff,
            handoff_path=handoff_path,
            authorization_record=authorization_record,
            generated_at="2026-07-02T00:00:00+00:00",
        )
        assert not validate_runbook(runbook), runbook
        assert runbook["preparedOnly"] is True
        assert runbook["browserStepsExecutable"] is False
        assert runbook["remoteMutationsPerformed"] is False
        assert runbook["authorizationRecord"] == authorization_record
        assert AUTH_PLACEHOLDER in runbook["authorizationRecordCommand"]
        assert runbook["authorizationRecordCommandHasPlaceholder"] is True
        assert "--action create_site" in runbook["preMutationGateCommand"]
        assert "--expected-target-identifier 'Example Demo'" in runbook["preMutationGateCommand"]
        assert runbook["siteProposal"]["siteName"] == handoff["siteProposal"]["siteName"]
        assert runbook["siteProposal"]["siteDescription"] == handoff["siteProposal"]["siteDescription"]
        assert runbook["contentCounts"] == handoff["contentCounts"]
        assert runbook["contentCounts"]["navigationItems"] >= 3
        assert runbook["contentCounts"]["siteInfoFields"] >= 3
        assert runbook["contentGoalCoverage"] == handoff["contentGoalCoverage"]
        assert runbook["contentGoalOverages"] == handoff["contentGoalOverages"]
        assert runbook["sourcePackageSha256"] == handoff["sourcePackageSha256"]
        assert runbook["sourceReviewPacketSha256"] == handoff["sourceReviewPacketSha256"]
        assert runbook["contentQualityReview"] == handoff["contentQualityReview"]
        assert runbook["wikiReview"] == handoff["wikiReview"]
        assert runbook["confirmationDecisionMatrix"] == handoff["confirmationDecisionMatrix"]
        assert runbook["redactedEvidenceTemplate"]["createdOnce"] is False
        assert runbook["redactedEvidenceTemplate"]["siteName"] == handoff["siteProposal"]["siteName"]
        assert "uploading products/posts/media" in runbook["forbiddenActions"]
        assert "created-site evidence is captured" in runbook["stopAfter"]


def test_create_site_runbook_rejects_missing_wiki_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff, handoff_path = prepared_handoff(root)
        handoff["wikiReview"] = {}
        try:
            build_runbook(
                handoff=handoff,
                handoff_path=handoff_path,
                authorization_record=str(root / "authorization-create-site.json"),
            )
        except ValueError as exc:
            assert "create-site handoff validation failed" in str(exc)
        else:
            raise AssertionError("runbook should reject a handoff missing wikiReview")


def test_create_site_runbook_rejects_missing_content_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff, handoff_path = prepared_handoff(root)
        handoff.pop("contentCounts", None)
        try:
            build_runbook(
                handoff=handoff,
                handoff_path=handoff_path,
                authorization_record=str(root / "authorization-create-site.json"),
            )
        except ValueError as exc:
            assert "contentCounts" in str(exc)
        else:
            raise AssertionError("runbook should reject a handoff missing contentCounts")


def test_create_site_runbook_rejects_incomplete_scope_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff, handoff_path = prepared_handoff(root)
        handoff["contentCounts"].pop("navigationItems", None)
        try:
            build_runbook(
                handoff=handoff,
                handoff_path=handoff_path,
                authorization_record=str(root / "authorization-create-site.json"),
            )
        except ValueError as exc:
            assert "contentCounts.navigationItems" in str(exc)
        else:
            raise AssertionError("runbook should reject missing navigationItems count")


def test_create_site_runbook_preserves_content_goal_overages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff, handoff_path = prepared_handoff_with_post_overage(root)
        runbook = build_runbook(
            handoff=handoff,
            handoff_path=handoff_path,
            authorization_record=str(root / "authorization-create-site.json"),
        )
        assert not validate_runbook(runbook), runbook
        assert runbook["contentGoalOverages"] == handoff["contentGoalOverages"]
        assert runbook["contentGoalOverages"]["details"]["posts"]["likelyExtraItems"][0]["slug"] == "generated-buyer-guide"
        assert "contentGoalOverages" in " ".join(runbook["mustRunBeforeBrowserSubmit"])

        drifted = json.loads(json.dumps(runbook))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_runbook(drifted)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues


def test_create_site_runbook_cli_writes_non_executable_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, handoff_path = prepared_handoff(root)
        output = root / "create-site-browser-runbook.json"
        from build_create_site_runbook import main

        import sys

        old_argv = sys.argv
        try:
            sys.argv = [
                "build_create_site_runbook.py",
                "--create-site-handoff",
                handoff_path,
                "--authorization-record",
                str(root / "authorization-create-site.json"),
                "--output",
                str(output),
            ]
            assert main() == 0
        finally:
            sys.argv = old_argv
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["kind"] == "allincms_create_site_browser_runbook"
        assert data["browserStepsExecutable"] is False


if __name__ == "__main__":
    test_create_site_runbook_builds_from_confirmed_handoff()
    test_create_site_runbook_rejects_missing_wiki_review()
    test_create_site_runbook_rejects_missing_content_counts()
    test_create_site_runbook_rejects_incomplete_scope_counts()
    test_create_site_runbook_preserves_content_goal_overages()
    test_create_site_runbook_cli_writes_non_executable_runbook()
    print("create-site runbook regression tests passed.")
