#!/usr/bin/env python3
"""Regression tests for create-site preflight brief generation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from make_create_site_preflight_brief import build, validate_brief
from test_prepare_confirmed_site_execution import base_args, prepare_package_and_review
from prepare_confirmed_site_execution import build as prepare_confirmed


def prepare_confirmed_artifacts(root: Path) -> tuple[dict, Path, Path]:
    package_path, review_path = prepare_package_and_review(root)
    args = base_args(root, package_path, review_path)
    summary = prepare_confirmed(args)
    return summary, package_path, review_path


def test_create_site_preflight_brief_is_readonly_and_actionable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary, package_path, review_path = prepare_confirmed_artifacts(root)
        brief_path = root / "manual-preflight-brief.json"
        brief = build(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_path),
                confirmation=summary["artifacts"]["confirmation"],
                execution_plan=summary["artifacts"]["executionPlan"],
                output=str(brief_path),
                preflight_output=str(root / "create-site-preflight.json"),
                create_authorization_output=str(root / "authorization-create-site.json"),
                json=False,
            )
        )
        assert brief["kind"] == "allincms_create_site_preflight_brief"
        assert brief["localOnly"] is True
        assert brief["remoteMutationsPerformed"] is False
        assert brief["isUserAuthorization"] is False
        assert brief["target"] == "https://workspace.laicms.com/sites"
        assert brief["preflightOutput"].endswith("create-site-preflight.json")
        assert not validate_brief(brief), brief
        assert "--dialog-closed-verified" in brief["preflightCommandTemplate"]
        assert "prepare_confirmed_site_execution.py" in brief["nextCommandAfterPreflight"]
        assert "do not submit the create-site form" in brief["forbiddenActions"]
        assert brief_path.exists()


def test_confirmed_execution_without_preflight_writes_preflight_brief() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary, _, _ = prepare_confirmed_artifacts(root)
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        assert summary["artifacts"]["createSitePreflightBrief"]
        assert summary["artifacts"]["createSitePreflightTarget"].endswith("create-site-preflight.json")
        brief = json.loads(Path(summary["artifacts"]["createSitePreflightBrief"]).read_text(encoding="utf-8"))
        assert brief["kind"] == "allincms_create_site_preflight_brief"
        assert brief["preflightOutput"] == summary["artifacts"]["createSitePreflightTarget"]
        assert brief["remoteMutationsPerformed"] is False
        assert "do not submit the create-site form" in brief["forbiddenActions"]
        assert summary["artifacts"]["createSitePreflightBriefValidation"]
        validation = json.loads(Path(summary["artifacts"]["createSitePreflightBriefValidation"]).read_text(encoding="utf-8"))
        assert validation["valid"] is True
        assert validation["issues"] == []


def test_create_site_preflight_brief_rejects_authorizing_or_mutating_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary, _, _ = prepare_confirmed_artifacts(root)
        brief = json.loads(Path(summary["artifacts"]["createSitePreflightBrief"]).read_text(encoding="utf-8"))
        bad = dict(brief)
        bad["isUserAuthorization"] = True
        bad["forbiddenActions"] = ["inspect only"]
        bad["preflightCommandTemplate"] = "echo missing gate"
        issues = validate_brief(bad)
        assert "isUserAuthorization must be false" in issues
        assert any("preflightCommandTemplate" in issue for issue in issues)
        assert any("forbiddenActions must include do not submit" in issue for issue in issues)


if __name__ == "__main__":
    test_create_site_preflight_brief_is_readonly_and_actionable()
    test_confirmed_execution_without_preflight_writes_preflight_brief()
    test_create_site_preflight_brief_rejects_authorizing_or_mutating_shape()
    print("create-site preflight brief regression tests passed.")
