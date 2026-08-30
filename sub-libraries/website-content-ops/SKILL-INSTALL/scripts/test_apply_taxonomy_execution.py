#!/usr/bin/env python3
"""Regression tests for applying taxonomy execution evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_taxonomy_execution import build
from test_summarize_source_execution_status import (
    artifact_readiness_with_taxonomy_plan,
    confirmation,
    confirmation_decision_matrix,
    content_goal_coverage,
    content_quality_review,
    created_site_binding,
    execution_plan,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    schema_capture_handoff,
    taxonomy_handoff,
    wiki_review,
)


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def taxonomy_evidence(handoff: dict) -> dict:
    mappings = []
    for action in handoff["actions"]:
        term = action["term"]
        mappings.append(
            {
                "targetIdentifier": action["targetIdentifier"],
                "contentType": action["contentType"],
                "termKind": action["termKind"],
                "slug": term["slug"],
                "label": term["label"],
                "status": "created",
                "preMutationGate": "passed",
                "backendVerified": True,
                "mappingVerified": True,
                "backendUrl": "https://workspace.laicms.com/demo123/products?tab=categorys",
                "requestCapture": {
                    "method": "POST",
                    "responseStatus": 200,
                    "payloadShape": {"label": "string", "slug": "string"},
                },
            }
        )
    return {
        "kind": "allincms_taxonomy_execution_evidence",
        "siteKey": "demo123",
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": {"pages": 1, "products": 1, "posts": 1},
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": True,
        "taxonomyMappings": mappings,
        "blockingIssues": [],
        "stopConditionMet": True,
    }


def created_site_submitted_values() -> dict:
    return {
        "name": "Example Site",
        "description": "Example description.",
    }


def base_args(root: Path, *, bad_taxonomy: bool = False) -> argparse.Namespace:
    package_path = write_json(root / "package.json", package())
    review_path = write_json(root / "review-packet.json", review_packet(package_path))
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    handoff = taxonomy_handoff()
    handoff["siteKey"] = "demo123"
    handoff["contentGoalCoverage"] = content_goal_coverage()
    handoff["contentCounts"] = {"pages": 1, "products": 1, "posts": 1}
    handoff["contentQualityReview"] = content_quality_review()
    handoff["wikiReview"] = wiki_review()
    handoff["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    handoff["createdSiteSubmittedValues"] = created_site_submitted_values()
    evidence = taxonomy_evidence(handoff)
    if bad_taxonomy:
        evidence["taxonomyMappings"] = []
    created_site_binding_data = created_site_binding()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    return argparse.Namespace(
        package=package_path,
        review_packet="",
        confirmation=write_json(root / "confirmation.json", confirmation_data),
        execution_plan=write_json(root / "execution-plan.json", execution_plan()),
        artifact_readiness=write_json(root / "artifact-readiness.json", artifact_readiness_with_taxonomy_plan(root)),
        created_site_binding=write_json(root / "created-site-binding.json", created_site_binding_data),
        pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
        pages_site_info_evidence="",
        pages_site_info_validation=write_json(root / "pages-site-info-validation.json", pages_site_info_validation()),
        taxonomy_handoff=write_json(root / "taxonomy-handoff.json", handoff),
        taxonomy_evidence=write_json(root / "taxonomy-evidence.json", evidence),
        schema_capture_handoff=write_json(root / "schema-capture-handoff.json", schema_capture_handoff()),
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        launch_acceptance="",
        output_dir=str(root / "apply-taxonomy"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_taxonomy_execution_advances_to_schema_manifests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root))
        assert summary["validationValid"] is True
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == {"pages": 1, "products": 1, "posts": 1}
        assert summary["contentQualityReview"] == content_quality_review()
        assert summary["wikiReview"] == wiki_review()
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert summary["sourcePackageSha256"] == "a" * 64
        assert summary["sourceReviewPacketSha256"] == "b" * 64
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "schema_manifests"
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["stages"]["taxonomy_execution"]["status"] == "passed"
        assert status["currentStage"] == "schema_manifests", status
        validation = json.loads(Path(summary["artifacts"]["taxonomyValidation"]).read_text(encoding="utf-8"))
        assert validation["taxonomyPrerequisiteSatisfied"] is True


def test_apply_taxonomy_execution_keeps_invalid_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, bad_taxonomy=True))
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_taxonomy_evidence"
        assert summary["validation"]["taxonomyIssues"]


def test_apply_taxonomy_execution_rejects_blocked_handoff_even_with_complete_mappings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        handoff = json.loads(Path(args.taxonomy_handoff).read_text(encoding="utf-8"))
        handoff["readyForBrowserStage"] = "blocked_taxonomy_preflight"
        handoff["preflightIssues"] = ["preflight.setupPages.posts"]
        args.taxonomy_handoff = write_json(root / "taxonomy-handoff-blocked.json", handoff)
        args.taxonomy_evidence = write_json(root / "taxonomy-evidence-complete.json", taxonomy_evidence(handoff))
        summary = build(args)
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_taxonomy_evidence"
        assert any("handoff.readyForBrowserStage" in issue for issue in summary["validation"]["taxonomyIssues"])
        assert any("handoff.preflightIssues must be empty" in issue for issue in summary["validation"]["taxonomyIssues"])


def test_apply_taxonomy_execution_rejects_content_count_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        handoff = json.loads(Path(args.taxonomy_handoff).read_text(encoding="utf-8"))
        evidence = taxonomy_evidence(handoff)
        evidence["contentCounts"] = {"pages": 1, "products": 2, "posts": 1}
        args.taxonomy_evidence = write_json(root / "taxonomy-evidence-drift.json", evidence)
        try:
            build(args)
        except SystemExit as exc:
            assert "contentCounts mismatch" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block taxonomy apply")


def test_apply_taxonomy_execution_rejects_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        handoff = json.loads(Path(args.taxonomy_handoff).read_text(encoding="utf-8"))
        evidence = taxonomy_evidence(handoff)
        evidence["createdSiteSubmittedValues"] = {
            "name": "Changed Site",
            "description": "Example description.",
        }
        args.taxonomy_evidence = write_json(root / "taxonomy-evidence-submitted-value-drift.json", evidence)
        try:
            build(args)
        except SystemExit as exc:
            assert "createdSiteSubmittedValues mismatch" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block taxonomy apply")


if __name__ == "__main__":
    test_apply_taxonomy_execution_advances_to_schema_manifests()
    test_apply_taxonomy_execution_keeps_invalid_blocked()
    test_apply_taxonomy_execution_rejects_blocked_handoff_even_with_complete_mappings()
    test_apply_taxonomy_execution_rejects_content_count_drift()
    test_apply_taxonomy_execution_rejects_created_site_submitted_value_drift()
    print("apply taxonomy execution regression tests passed.")
