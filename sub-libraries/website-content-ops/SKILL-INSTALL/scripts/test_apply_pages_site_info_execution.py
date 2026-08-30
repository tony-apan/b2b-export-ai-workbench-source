#!/usr/bin/env python3
"""Regression tests for applying pages/site-info execution evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_pages_site_info_execution import build
from test_summarize_source_execution_status import (
    artifact_readiness_with_taxonomy_plan,
    confirmation,
    confirmation_decision_matrix,
    content_goal_coverage,
    content_quality_review,
    created_site_binding,
    created_site_submitted_values,
    execution_plan,
    package,
    pages_site_info_handoff,
    review_packet,
    taxonomy_handoff,
    wiki_review,
)


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def action_proof() -> dict:
    return {"preMutationGate": "passed", "verified": True, "evidence": "redacted proof"}


def page(path: str, frontend_url: str, *, homepage: bool = False) -> dict:
    data = {
        "path": path,
        "routePath": path,
        "backendUrl": "https://workspace.laicms.com/demo123/themes/theme-redacted/page-redacted/design",
        "frontendUrl": frontend_url,
        "createThemePageVerified": True,
        "designSaved": True,
        "designPublished": True,
        "pageEnabled": True,
        "routeBound": True,
        "frontendVerified": True,
        "renderAudit": {
            "sourceContentVerified": True,
            "starterTemplateAbsent": True,
            "expectedSourceSignals": ["source-confirmed heading rendered", "source-confirmed body rendered"],
            "unexpectedStarterSignals": [],
            "proof": "redacted DOM rendered expected source copy and no unrelated old copy",
        },
        "actionEvidence": {
            "create_theme_page": action_proof(),
            "save_design": action_proof(),
            "publish_design": action_proof(),
            "enable_theme_page": action_proof(),
            "bind_route": action_proof(),
        },
    }
    if homepage:
        data["homepageVerified"] = True
    return data


def pages_handoff() -> dict:
    handoff = pages_site_info_handoff()
    handoff["siteKey"] = "demo123"
    handoff["frontendBaseUrl"] = "https://demo123.web.allincms.com"
    handoff["createdSiteSubmittedValues"] = created_site_submitted_values()
    handoff["contentGoalCoverage"] = content_goal_coverage()
    handoff["contentCounts"] = {"pages": 1, "products": 1, "posts": 1}
    handoff["contentQualityReview"] = content_quality_review()
    handoff["wikiReview"] = wiki_review()
    handoff["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    handoff["pages"] = [
        {
            "page": {"title": "Home", "path": "/", "sourceRefs": ["src-001"]},
            "browserStepsExecutable": False,
            "actions": [{"action": "create_theme_page", "browserStepsExecutable": False}],
        }
    ]
    return handoff


def valid_evidence() -> dict:
    return {
        "kind": "allincms_pages_site_info_execution_evidence",
        "siteKey": "demo123",
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": {"pages": 1, "products": 1, "posts": 1},
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": True,
        "stopConditionMet": True,
        "blockingIssues": [],
        "siteInfo": {
            "status": "verified",
            "target": "https://workspace.laicms.com/demo123/site-info",
            "saveStatus": "ok",
            "backendVerified": True,
            "persistedVerified": True,
            "requestCapture": {
                "method": "POST",
                "headers": ["accept", "content-type"],
                "payloadShape": {"name": "string", "description": "string"},
                "responseStatus": 200,
            },
        },
        "pages": [page("/", "https://demo123.web.allincms.com", homepage=True)],
}


def base_args(root: Path) -> argparse.Namespace:
    package_path = write_json(root / "package.json", package())
    review_path = write_json(root / "review-packet.json", review_packet(package_path))
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    created_site_binding_data = created_site_binding()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    return argparse.Namespace(
        package=package_path,
        review_packet="",
        confirmation=write_json(root / "confirmation.json", confirmation_data),
        execution_plan=write_json(root / "execution-plan.json", execution_plan()),
        artifact_readiness=write_json(root / "artifact-readiness.json", artifact_readiness_with_taxonomy_plan(root)),
        created_site_binding=write_json(root / "created-site-binding.json", created_site_binding_data),
        pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_handoff()),
        pages_site_info_evidence=write_json(root / "pages-site-info-evidence.json", valid_evidence()),
        taxonomy_handoff=write_json(root / "taxonomy-handoff.json", taxonomy_handoff()),
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff="",
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        launch_acceptance="",
        output_dir=str(root / "apply-pages"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_pages_site_info_execution_advances_to_taxonomy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root))
        assert summary["validationValid"] is True
        assert summary["pageCount"] == 1
        assert summary["siteInfoFieldCount"] == 6
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == {"pages": 1, "products": 1, "posts": 1}
        assert summary["contentQualityReview"] == content_quality_review()
        assert summary["wikiReview"] == wiki_review()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert summary["sourcePackageSha256"] == "a" * 64
        assert summary["sourceReviewPacketSha256"] == "b" * 64
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "taxonomy_execution"
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["pages_site_info_execution"]["status"] == "passed"
        assert status["currentStage"] == "taxonomy_execution", status
        validation = json.loads(Path(summary["artifacts"]["pagesSiteInfoValidation"]).read_text(encoding="utf-8"))
        assert validation["launchPrerequisiteSatisfied"] is True
        assert validation["siteInfoFieldCount"] == 6


def test_apply_pages_site_info_execution_keeps_invalid_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        evidence = valid_evidence()
        evidence["pages"][0]["frontendVerified"] = False
        args.pages_site_info_evidence = write_json(root / "bad-pages-site-info-evidence.json", evidence)
        summary = build(args)
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_pages_site_info_evidence"
        assert summary["validation"]["pagesSiteInfoIssues"]


def test_apply_pages_site_info_execution_rejects_content_count_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        evidence = valid_evidence()
        evidence["contentCounts"] = {"pages": 2, "products": 1, "posts": 1}
        args.pages_site_info_evidence = write_json(root / "drift-pages-site-info-evidence.json", evidence)
        try:
            build(args)
        except SystemExit as exc:
            assert "contentCounts mismatch" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block pages/site-info apply")


def test_apply_pages_site_info_execution_rejects_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        evidence = valid_evidence()
        evidence["createdSiteSubmittedValues"] = {
            "name": "Changed Site",
            "description": "Example description.",
        }
        args.pages_site_info_evidence = write_json(root / "drift-submitted-values-evidence.json", evidence)
        try:
            build(args)
        except SystemExit as exc:
            assert "createdSiteSubmittedValues mismatch" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block pages/site-info apply")


if __name__ == "__main__":
    test_apply_pages_site_info_execution_advances_to_taxonomy()
    test_apply_pages_site_info_execution_keeps_invalid_blocked()
    test_apply_pages_site_info_execution_rejects_content_count_drift()
    test_apply_pages_site_info_execution_rejects_created_site_submitted_value_drift()
    print("apply pages/site-info execution regression tests passed.")
