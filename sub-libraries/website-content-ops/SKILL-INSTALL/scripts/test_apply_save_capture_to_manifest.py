#!/usr/bin/env python3
"""Regression tests for applying save-capture schema proof to manifests."""

from __future__ import annotations

from apply_save_capture_to_manifest import build_schema_verified_manifest
from validate_manifest import validate_manifest


def draft_manifest(content_type: str = "products") -> dict:
    if content_type == "products":
        item = {
            "name": "Industrial Demo Product",
            "slug": "industrial-demo-product",
            "description": "A source-backed product summary for buyers comparing industrial options.",
            "content": [{"type": "paragraph", "text": "Source-backed product body for upload preparation."}],
        }
    else:
        item = {
            "title": "Industrial Buying Guide",
            "slug": "industrial-buying-guide",
            "excerpt": "A source-backed article excerpt for buyers comparing supplier and product fit.",
            "content": [{"type": "paragraph", "text": "Source-backed article body for upload preparation."}],
        }
    return {
        "siteKey": "{siteKey-after-creation}",
        "contentType": content_type,
        "frontendBaseUrl": "https://{siteKey}.web.allincms.com",
        "schemaVerified": False,
        "fieldMapping": {},
        "payloadTemplate": {},
        "items": [item],
    }


def warning_quality() -> dict:
    return {
        "readyShape": False,
        "warnings": ["posts_present_without_post_categories"],
        "contentCounts": {"pages": 1, "products": 1, "posts": 1},
        "reviewRequired": True,
    }


def wiki_review() -> dict:
    return {
        "sourceWiki": "/tmp/source-wiki.json",
        "sourceWikiMarkdown": "/tmp/wiki/manifest.json",
        "sourceWikiMarkdownIndex": "/tmp/wiki/index.md",
    }


def confirmation_decision_matrix() -> list[dict]:
    return [
        {
            "field": "siteProposal.siteName",
            "decision": "accept",
            "source": "acceptedFields",
            "deferDecision": "",
            "reason": "",
            "blocksRemoteMutation": False,
        },
        {
            "field": "domains.customDomain",
            "decision": "defer",
            "source": "acceptedDeferrals",
            "deferDecision": "out_of_scope_for_demo",
            "reason": "No custom domain is needed for this demo.",
            "blocksRemoteMutation": False,
        },
    ]


def source_identity() -> dict:
    return {
        "sourcePackageSha256": "a" * 64,
        "sourceReviewPacketSha256": "b" * 64,
    }


def save_capture(content_type: str = "products") -> dict:
    singular = content_type.rstrip("s")
    return {
        "kind": "allincms_probe_save_capture_evidence",
        "contentType": content_type,
        "target": f"https://workspace.laicms.com/demo123/{content_type}/redacted/update",
        "authorizationRecord": "/tmp/auth.json",
        "preMutationGate": "passed",
        "savedOnce": True,
        "published": False,
        "requestCapture": {
            "method": "POST",
            "url": f"https://workspace.laicms.com/demo123/{content_type}/redacted/update",
            "headers": ["Accept", "Content-Type"],
            "payloadShape": {
                "siteId": "<redacted>",
                f"{singular}Id": "<redacted>",
                "mode": "update",
                "content": [{"type": "paragraph", "children": [{"text": "redacted"}]}],
            },
            "contentBlockShape": "array of paragraph blocks with children text nodes",
            "idFields": f"siteId and {singular}Id redacted",
            "mode": "update",
            "publishBehavior": "publish-separate",
            "responseStatus": 200,
            "responseMimeType": "text/x-component",
        },
        "fieldMapping": {
            "nameField": "name" if content_type == "products" else "title",
            "slugField": "slug",
            "descriptionField": "description" if content_type == "products" else "excerpt",
            "bodyField": "content",
            "mediaField": "coverImage",
            "statusField": "status",
        },
        "payloadTemplate": {
            "siteId": "<redacted>",
            f"{singular}Id": "<redacted>",
            "mode": "update",
            "content": [{"type": "paragraph", "children": [{"text": "{bodyText}"}]}],
        },
        "backendPersisted": True,
        "stopConditionMet": True,
    }


def base_run_evidence(content_type: str = "products") -> dict:
    return {
        "siteIdentity": {"siteKey": "demo123"},
        "contentInspection": {"contentType": content_type},
    }


def test_apply_capture_to_manifest() -> None:
    upgraded = build_schema_verified_manifest(
        manifest=draft_manifest("products"),
        capture=save_capture("products"),
        capture_path="/tmp/save-capture.json",
        base_run_evidence=base_run_evidence("products"),
        base_run_evidence_path="/tmp/base-run-evidence.json",
    )
    assert upgraded["siteKey"] == "demo123"
    assert upgraded["frontendBaseUrl"] == "https://demo123.web.allincms.com"
    assert upgraded["schemaVerified"] is True
    assert upgraded["fieldMapping"]["nameField"] == "name"
    assert upgraded["payloadTemplate"]["mode"] == "update"
    assert upgraded["schemaCaptureEvidence"]["backendPersisted"] is True
    assert not validate_manifest(upgraded, require_schema_verified=True)


def test_apply_capture_preserves_source_context() -> None:
    manifest = draft_manifest("products")
    manifest["contentGoalCoverage"] = {
        "complete": True,
        "checks": {"pages": True, "products": True, "posts": True},
        "missing": [],
        "counts": {"pages": 1, "products": 1, "posts": 1},
    }
    manifest["contentCounts"] = {"pages": 1, "products": 1, "posts": 1}
    manifest["contentQualityReview"] = warning_quality()
    manifest["wikiReview"] = wiki_review()
    manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    manifest.update(source_identity())
    upgraded = build_schema_verified_manifest(
        manifest=manifest,
        capture=save_capture("products"),
        capture_path="/tmp/save-capture.json",
        base_run_evidence=base_run_evidence("products"),
        base_run_evidence_path="/tmp/base-run-evidence.json",
    )
    assert upgraded["contentGoalCoverage"] == manifest["contentGoalCoverage"]
    assert upgraded["contentCounts"] == manifest["contentCounts"]
    assert upgraded["contentQualityReview"] == warning_quality()
    assert upgraded["wikiReview"] == wiki_review()
    assert upgraded["confirmationDecisionMatrix"] == confirmation_decision_matrix()
    assert upgraded["sourcePackageSha256"] == source_identity()["sourcePackageSha256"]
    assert upgraded["sourceReviewPacketSha256"] == source_identity()["sourceReviewPacketSha256"]
    assert "posts_present_without_post_categories" in upgraded["contentQualityReview"]["warnings"]


def test_rejects_content_type_mismatch() -> None:
    try:
        build_schema_verified_manifest(
            manifest=draft_manifest("posts"),
            capture=save_capture("products"),
            capture_path="/tmp/save-capture.json",
            base_run_evidence=base_run_evidence("posts"),
            base_run_evidence_path="/tmp/base-run-evidence.json",
        )
    except ValueError as exc:
        assert "contentType" in str(exc)
    else:
        raise AssertionError("content type mismatch should fail")


if __name__ == "__main__":
    test_apply_capture_to_manifest()
    test_apply_capture_preserves_source_context()
    test_rejects_content_type_mismatch()
    print("apply save capture to manifest regression tests passed.")
