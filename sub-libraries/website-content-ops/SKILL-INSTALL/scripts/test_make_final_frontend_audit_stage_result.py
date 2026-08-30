#!/usr/bin/env python3
"""Regression tests for final frontend audit stage result generation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from make_final_frontend_audit_stage_result import build_result, url_fingerprint
from test_manifest_sample_upload import created_site_submitted_values
from test_summarize_source_execution_status import (
    confirmation_decision_matrix,
    content_goal_coverage,
    content_quality_review,
    wiki_review,
)
from test_validate_source_run_acceptance import content_counts


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def packet() -> dict:
    return {
        "kind": "allincms_browser_stage_packet",
        "generatedAt": "2026-07-01T00:00:00+00:00",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "final_frontend_audit",
        "recovery": False,
        "phase": "final QA",
        "mode": "verification",
        "targetTemplate": "https://{realSiteKey}.web.allincms.com",
        "authorizationRequired": False,
        "remoteMutationExpectation": "must_not",
        "suggestedAuthorizationText": "",
        "allowedActions": ["audit all static routes and uploaded detail routes"],
        "remoteMutationsAllowed": False,
        "requiredProof": [
            "HTTP status report",
            "DOM/rich-text report",
            "image report",
            "broken-entry list empty",
        ],
        "forbiddenActions": ["backend mutation while auditing"],
        "stopAfter": "Stop if any expected route, image, description, body, or status fails.",
        "evidenceCaptureTemplate": {
            "stageId": "final_frontend_audit",
            "status": "completed|blocked|partial",
            "redactedEvidencePointers": [],
            "proofRecorded": [
                "HTTP status report",
                "DOM/rich-text report",
                "image report",
                "broken-entry list empty",
            ],
            "blockingIssues": [],
            "operatorNote": "",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "afterStageCompletes": "Apply a completed, partial, or blocked stage result after redacted evidence is recorded.",
            "expectedCompletedStageIdsAfterApply": ["final_frontend_audit"],
            "stageResultRequired": True,
            "commandTemplate": "python3 apply_browser_stage_result.py --ledger /tmp/ledger.json --packet /tmp/packet.json --result-json /tmp/result.json --output /tmp/ledger.updated.json",
        },
        "warnings": ["This packet is local-only and does not authorize remote LAICMS mutation."],
    }


def audit_report() -> list[dict]:
    return [
        {
            "url": "https://demo123.web.allincms.com/",
            "urlFingerprint": url_fingerprint("https://demo123.web.allincms.com/"),
            "expectedStatus": 200,
            "status": 200,
            "tagCounts": {"h1": 1},
            "headings": {"h1": ["Home"]},
            "imageCount": 1,
            "issues": [],
        }
    ]


def detail_audit_report(*, wrong_fingerprint: bool = False) -> list[dict]:
    url = "https://demo123.web.allincms.com/products/example-product"
    fingerprint_url = "https://demo123.web.allincms.com/products/wrong-product" if wrong_fingerprint else url
    return [
        {
            "url": "/products/{slug}",
            "urlFingerprint": url_fingerprint(fingerprint_url),
            "routeInstance": "products-detail-1",
            "expectedStatus": 200,
            "status": 200,
            "tagCounts": {"h1": 1},
            "headings": {"h1": ["redacted-h1-1"]},
            "imageCount": 1,
            "issues": [],
        }
    ]


def source_context(
    root: Path,
    *,
    matrix_drift: bool = False,
    count_drift: bool = False,
    submitted_value_drift: bool = False,
) -> str:
    review = wiki_review(root)
    matrix = confirmation_decision_matrix()
    counts = content_counts()
    if matrix_drift:
        matrix = [{**matrix[0], "decision": "defer", "deferDecision": "changed"}]
    if count_drift:
        counts = {**counts, "products": counts["products"] + 1}
    submitted_values = created_site_submitted_values()
    if submitted_value_drift:
        submitted_values = {**submitted_values, "name": "Different Demo"}
    return write_json(
        root / (
            "source-context-drift.json"
            if (matrix_drift or count_drift or submitted_value_drift)
            else "source-context.json"
        ),
        {
            "contentGoalCoverage": content_goal_coverage(),
            "contentCounts": counts,
            "contentQualityReview": content_quality_review(),
            "wikiReview": review,
            "confirmationDecisionMatrix": matrix,
            "createdSiteSubmittedValues": submitted_values,
        },
    )


def test_build_result_carries_source_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report.json"
        write_json(report_path, audit_report())
        context_path = source_context(root)
        result = build_result(
            packet(),
            report_path,
            [],
            False,
            audit_inputs_summary={"staticRouteCount": 1, "detailRouteCount": 0, "navigationItemCount": 3},
            source_context_artifacts=[context_path],
        )
        assert result["status"] == "completed"
        assert result["navigationItemCount"] == 3
        assert result["contentGoalCoverage"] == content_goal_coverage()
        assert result["contentCounts"] == content_counts()
        assert result["contentQualityReview"] == content_quality_review()
        assert result["wikiReview"] == wiki_review(root)
        assert result["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert result["createdSiteSubmittedValues"] == created_site_submitted_values()


def test_build_result_blocks_source_context_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report.json"
        write_json(report_path, audit_report())
        good = source_context(root)
        bad = source_context(root, matrix_drift=True)
        try:
            build_result(packet(), report_path, [], False, source_context_artifacts=[good, bad])
        except ValueError as exc:
            assert "confirmationDecisionMatrix mismatch" in str(exc)
        else:
            raise AssertionError("source-context drift should block final frontend audit result generation")


def test_build_result_blocks_content_counts_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report.json"
        write_json(report_path, audit_report())
        good = source_context(root)
        bad = source_context(root, count_drift=True)
        try:
            build_result(packet(), report_path, [], False, source_context_artifacts=[good, bad])
        except ValueError as exc:
            assert "contentCounts mismatch" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block final frontend audit result generation")


def test_build_result_blocks_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report.json"
        write_json(report_path, audit_report())
        good = source_context(root)
        bad = source_context(root, submitted_value_drift=True)
        try:
            build_result(packet(), report_path, [], False, source_context_artifacts=[good, bad])
        except ValueError as exc:
            assert "createdSiteSubmittedValues mismatch" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block final frontend audit result generation")


def test_build_result_blocks_wrong_detail_url_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report-wrong-fingerprint.json"
        write_json(report_path, detail_audit_report(wrong_fingerprint=True))
        result = build_result(
            packet(),
            report_path,
            [],
            False,
            audit_inputs_summary={
                "staticRouteCount": 0,
                "detailRouteCount": 1,
                "detailRouteInstances": ["products-detail-1"],
                "routePatterns": ["/products/{slug}"],
            },
            expected_statuses={"https://demo123.web.allincms.com/products/example-product": 200},
        )
        assert result["status"] == "partial"
        assert any("expected concrete URL fingerprints" in issue for issue in result["blockingIssues"])


def test_build_result_requires_detail_url_fingerprint_when_expected_statuses_are_concrete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "audit-report-missing-fingerprint.json"
        report = detail_audit_report()
        report[0].pop("urlFingerprint", None)
        write_json(report_path, report)
        result = build_result(
            packet(),
            report_path,
            [],
            False,
            audit_inputs_summary={
                "staticRouteCount": 0,
                "detailRouteCount": 1,
                "detailRouteInstances": ["products-detail-1"],
                "routePatterns": ["/products/{slug}"],
            },
            expected_statuses={"https://demo123.web.allincms.com/products/example-product": 200},
        )
        assert result["status"] == "partial"
        assert any("redacted audit report must include urlFingerprint" in issue for issue in result["blockingIssues"])


if __name__ == "__main__":
    test_build_result_carries_source_context()
    test_build_result_blocks_source_context_drift()
    test_build_result_blocks_content_counts_drift()
    test_build_result_blocks_created_site_submitted_value_drift()
    test_build_result_blocks_wrong_detail_url_fingerprint()
    test_build_result_requires_detail_url_fingerprint_when_expected_statuses_are_concrete()
    print("final frontend audit stage result regression tests passed.")
