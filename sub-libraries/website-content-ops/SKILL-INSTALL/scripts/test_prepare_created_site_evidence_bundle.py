#!/usr/bin/env python3
"""Regression tests for created-site evidence bundle preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_confirmed_create_site_handoff import build_handoff as build_create_site_handoff
from build_create_site_runbook import build_runbook as build_create_site_runbook
from make_created_site_evidence_brief import build as build_created_site_evidence_brief
from prepare_created_site_evidence_bundle import build_bundle, validate_bundle
from test_confirmed_create_site_handoff import prepare_inputs, write_json


def prepared_inputs(root: Path) -> tuple[dict, str, dict, str]:
    args = prepare_inputs(root)
    handoff = build_create_site_handoff(args)
    handoff_path = root / "create-site-handoff.json"
    write_json(handoff_path, handoff)
    runbook = build_create_site_runbook(
        handoff=handoff,
        handoff_path=str(handoff_path),
        authorization_record=str(root / "authorization-create-site.json"),
    )
    runbook_path = root / "create-site-browser-runbook.json"
    write_json(runbook_path, runbook)
    brief = build_created_site_evidence_brief(
        argparse.Namespace(
            create_site_handoff=str(handoff_path),
            output=str(root / "created-site-evidence-brief.json"),
            created_site_evidence_output=str(root / "created-site-evidence.json"),
            json=False,
        )
    )
    brief_path = root / "created-site-evidence-brief.json"
    return runbook, str(runbook_path), brief, str(brief_path)


def prepared_inputs_with_post_overage(root: Path) -> tuple[dict, str, dict, str]:
    args = prepare_inputs(root, with_post_overage=True)
    handoff = build_create_site_handoff(args)
    handoff_path = root / "create-site-handoff.json"
    write_json(handoff_path, handoff)
    runbook = build_create_site_runbook(
        handoff=handoff,
        handoff_path=str(handoff_path),
        authorization_record=str(root / "authorization-create-site.json"),
    )
    runbook_path = root / "create-site-browser-runbook.json"
    write_json(runbook_path, runbook)
    brief = build_created_site_evidence_brief(
        argparse.Namespace(
            create_site_handoff=str(handoff_path),
            output=str(root / "created-site-evidence-brief.json"),
            created_site_evidence_output=str(root / "created-site-evidence.json"),
            json=False,
        )
    )
    brief_path = root / "created-site-evidence-brief.json"
    return runbook, str(runbook_path), brief, str(brief_path)


def test_created_site_evidence_bundle_builds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, brief, brief_path = prepared_inputs(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            brief=brief,
            brief_path=brief_path,
            output_dir=root / "created-site-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["browserStepsExecutable"] is False
        assert bundle["createdSiteEvidenceOutput"].endswith("created-site-evidence.json")
        assert bundle["contentGoalCoverage"] == runbook["contentGoalCoverage"]
        assert bundle["contentGoalOverages"] == runbook["contentGoalOverages"]
        assert bundle["contentCounts"] == runbook["contentCounts"]
        assert bundle["contentCounts"]["navigationItems"] >= 3
        assert bundle["contentCounts"]["siteInfoFields"] >= 3
        assert bundle["contentQualityReview"] == runbook["contentQualityReview"]
        assert bundle["wikiReview"] == runbook["wikiReview"]
        assert bundle["confirmationDecisionMatrix"] == runbook["confirmationDecisionMatrix"]
        assert Path(bundle["evidenceTemplate"]).exists()
        assert Path(bundle["filledEvidenceTemplate"]).exists()
        assert Path(bundle["notes"]).exists()
        assert Path(bundle["applyCreatedSiteEvidenceBundleCommand"]).exists()
        assert Path(bundle["makeCreatedSiteEvidenceCommand"]).exists()
        assert Path(bundle["prepareCreatedSiteSchemaCaptureCommand"]).exists()
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["sourceRunbook"] == runbook_path
        assert template["sourceCreatedSiteEvidenceBrief"] == brief_path
        assert template["createdSiteKey"] == "<created-site-key>"
        assert template["preMutationGateStatus"] == "passed|required_before_submit"
        assert template["gateReadyForBrowserSubmit"] is False
        assert template["submittedSiteName"] == "Example Demo"
        assert template["submittedValues"]["name"] == "Example Demo"
        assert template["submittedValues"]["description"] == runbook["siteProposal"]["siteDescription"]
        assert template["forbiddenNeighborActionsVerified"] is False
        assert "media" in template["setupPageEvidence"]
        assert "/<created-site-key>/media" in template["moduleRoutes"]
        assert template["contentGoalCoverage"] == runbook["contentGoalCoverage"]
        assert template["contentGoalOverages"] == runbook["contentGoalOverages"]
        assert template["contentCounts"] == runbook["contentCounts"]
        assert template["contentQualityReview"] == runbook["contentQualityReview"]
        assert template["wikiReview"] == runbook["wikiReview"]
        assert template["confirmationDecisionMatrix"] == runbook["confirmationDecisionMatrix"]
        filled_template = json.loads(Path(bundle["filledEvidenceTemplate"]).read_text(encoding="utf-8"))
        assert filled_template == template
        assert bundle["submittedValues"] == template["submittedValues"]
        command = Path(bundle["makeCreatedSiteEvidenceCommand"]).read_text(encoding="utf-8")
        assert "make_created_site_evidence.py" in command
        assert "<copy from template.createdSiteKey>" in command
        assert "<JSON copy from template.submittedValues>" in command
        apply_command = Path(bundle["applyCreatedSiteEvidenceBundleCommand"]).read_text(encoding="utf-8")
        assert "apply_created_site_evidence_bundle.py" in apply_command
        assert bundle["filledEvidenceTemplate"] in apply_command


def test_created_site_evidence_bundle_rejects_brief_handoff_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, brief, brief_path = prepared_inputs(root)
        brief["createSiteHandoff"] = str(root / "other-handoff.json")
        try:
            build_bundle(
                runbook=runbook,
                runbook_path=runbook_path,
                brief=brief,
                brief_path=brief_path,
                output_dir=root / "bundle",
            )
        except ValueError as exc:
            assert "created-site evidence brief validation failed" in str(exc)
        else:
            raise AssertionError("bundle should reject brief/runbook handoff drift")


def test_created_site_evidence_bundle_rejects_missing_content_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, brief, brief_path = prepared_inputs(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            brief=brief,
            brief_path=brief_path,
            output_dir=root / "created-site-evidence-bundle",
        )
        bundle.pop("contentCounts")
        assert "contentCounts is required" in validate_bundle(bundle)


def test_created_site_evidence_bundle_preserves_content_goal_overages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runbook, runbook_path, brief, brief_path = prepared_inputs_with_post_overage(root)
        bundle = build_bundle(
            runbook=runbook,
            runbook_path=runbook_path,
            brief=brief,
            brief_path=brief_path,
            output_dir=root / "created-site-evidence-bundle",
        )
        assert not validate_bundle(bundle), bundle
        assert bundle["contentGoalOverages"] == runbook["contentGoalOverages"]
        assert bundle["contentGoalOverages"]["details"]["posts"]["likelyExtraItems"][0]["slug"] == "generated-buyer-guide"
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        assert template["contentGoalOverages"] == runbook["contentGoalOverages"]

        drifted = json.loads(json.dumps(bundle))
        drifted["contentGoalOverages"]["details"].pop("posts")
        issues = validate_bundle(drifted)
        assert "contentGoalOverages.present must equal bool(details)" in issues
        assert "contentGoalOverages.details.posts is required for warning exceeds_declared_content_goal:posts" in issues


if __name__ == "__main__":
    test_created_site_evidence_bundle_builds()
    test_created_site_evidence_bundle_rejects_brief_handoff_drift()
    test_created_site_evidence_bundle_rejects_missing_content_counts()
    test_created_site_evidence_bundle_preserves_content_goal_overages()
    print("created-site evidence bundle regression tests passed.")
