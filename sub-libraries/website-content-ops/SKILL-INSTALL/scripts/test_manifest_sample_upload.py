#!/usr/bin/env python3
"""Regression tests for manifest sample upload runbook and evidence gates."""

from __future__ import annotations

from build_batch_upload_publish_runbook import build_runbook as build_batch_runbook
from build_manifest_sample_upload_runbook import build_runbook as build_sample_runbook
from validate_manifest_sample_upload_evidence import validate_sample_evidence
from test_summarize_source_execution_status import content_goal_coverage
from test_apply_save_capture_to_manifest import confirmation_decision_matrix, source_identity


def schema_manifest() -> dict:
    return {
        "siteKey": "demo123",
        "contentType": "products",
        "frontendBaseUrl": "https://demo123.web.allincms.com",
        "schemaVerified": True,
        "fieldMapping": {
            "nameField": "name",
            "slugField": "slug",
            "descriptionField": "description",
            "bodyField": "content",
            "mediaField": "coverImage",
            "statusField": "status",
        },
        "payloadTemplate": {
            "siteId": "<redacted>",
            "productId": "<redacted>",
            "mode": "update",
            "content": [{"type": "paragraph", "children": [{"text": "{bodyText}"}]}],
        },
        "items": [
            {
                "name": "Industrial Demo Product",
                "slug": "industrial-demo-product",
                "description": "A source-backed product summary for sample upload validation.",
                "content": [{"type": "paragraph", "text": "Source-backed product body for sample upload validation."}],
            },
            {
                "name": "Industrial Demo Product Two",
                "slug": "industrial-demo-product-two",
                "description": "A second product summary for batch sequencing validation.",
                "content": [{"type": "paragraph", "text": "Second product body for batch sequencing validation."}],
            },
        ],
    }


def warning_quality() -> dict:
    return {
        "readyShape": False,
        "warnings": ["posts_present_without_post_categories"],
        "contentCounts": {"pages": 1, "products": 1, "posts": 1},
        "reviewRequired": True,
    }


def content_goal_overages() -> dict:
    return {
        "present": True,
        "details": {
            "posts": {
                "declared": 1,
                "actual": 2,
                "extraCount": 1,
                "items": [
                    {
                        "title": "Generated Planning Checklist",
                        "slug": "generated-planning-checklist",
                        "sourceRefs": ["src-002"],
                    }
                ],
                "likelyExtraItems": [
                    {
                        "title": "Generated Planning Checklist",
                        "slug": "generated-planning-checklist",
                        "sourceRefs": ["src-002"],
                    }
                ],
                "selectionRule": "generated items after declared count are likely extras",
            }
        },
        "operatorNote": "Review generated items that exceed declared source goals before batch upload.",
    }


def overage_quality() -> dict:
    quality = warning_quality()
    quality["warnings"] = ["exceeds_declared_content_goal:posts"]
    quality["reviewRequired"] = True
    return quality


def wiki_review() -> dict:
    return {
        "sourceWiki": "/tmp/source-wiki.json",
        "sourceWikiMarkdown": "/tmp/wiki/manifest.json",
        "sourceWikiMarkdownIndex": "/tmp/wiki/index.md",
    }


def content_counts() -> dict:
    return {"pages": 1, "products": 2, "posts": 1}


def created_site_submitted_values() -> dict:
    return {
        "name": "Example Demo",
        "description": "Example demo site for source-backed product publishing and article planning.",
    }


def base_run_evidence() -> dict:
    return {
        "siteIdentity": {"siteKey": "demo123"},
        "contentInspection": {"contentType": "products"},
        "requestCapture": {
            "url": "https://workspace.laicms.com/demo123/products/redacted/update",
            "method": "POST",
            "headers": "Accept, Content-Type",
            "payloadShape": "{}",
            "contentBlockShape": "paragraph blocks",
            "idFields": "siteId productId",
            "mode": "update",
            "publishBehavior": "publish-separate",
            "persistedVerified": True,
        },
    }


def sample_evidence(slug: str = "industrial-demo-product") -> dict:
    return {
        "kind": "allincms_manifest_sample_upload_evidence",
        "siteKey": "demo123",
        "contentType": "products",
        "manifestPath": "/tmp/products-schema-verified-manifest.json",
        "sampleSlug": slug,
        "target": "https://workspace.laicms.com/demo123/products",
        "backendUrl": "https://workspace.laicms.com/demo123/products/redacted/update",
        "frontendUrl": f"https://demo123.web.allincms.com/products/{slug}",
        "authorizationRecord": "/tmp/auth.json",
        "preMutationGate": "passed",
        "schemaGatePass": True,
        "saveStatus": "ok",
        "publishStatus": "ok",
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": False,
        "coverOrMediaNote": "No image was in scope for this local sample test.",
        "renderAudit": "redacted frontend detail rendered title and body with no markdown residue",
        "blockingIssues": [],
        "stopConditionMet": True,
    }


def test_sample_runbook_and_evidence() -> None:
    manifest = schema_manifest()
    runbook = build_sample_runbook(
        manifest=manifest,
        manifest_path="/tmp/products-schema-verified-manifest.json",
        target="https://workspace.laicms.com/demo123/products",
        authorization_output="/tmp/auth-sample.json",
    )
    assert runbook["sampleSlug"] == "industrial-demo-product"
    assert runbook["browserStepsExecutable"] is False
    assert "other than sampleSlug" in " ".join(runbook["forbiddenActions"])

    issues = validate_sample_evidence(sample_evidence(), manifest)
    assert not issues, issues


def test_sample_runbook_preserves_manifest_source_context() -> None:
    manifest = schema_manifest()
    manifest["contentGoalCoverage"] = content_goal_coverage()
    manifest["contentCounts"] = content_counts()
    manifest["contentQualityReview"] = overage_quality()
    manifest["contentGoalOverages"] = content_goal_overages()
    manifest["wikiReview"] = wiki_review()
    manifest["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    manifest["createdSiteSubmittedValues"] = created_site_submitted_values()
    manifest.update(source_identity())
    runbook = build_sample_runbook(
        manifest=manifest,
        manifest_path="/tmp/products-schema-verified-manifest.json",
        target="https://workspace.laicms.com/demo123/products",
        authorization_output="/tmp/auth-sample.json",
    )
    for key in (
        "sourcePackageSha256",
        "sourceReviewPacketSha256",
        "createdSiteSubmittedValues",
        "contentGoalCoverage",
        "contentCounts",
        "contentQualityReview",
        "contentGoalOverages",
        "wikiReview",
        "confirmationDecisionMatrix",
    ):
        assert runbook[key] == manifest[key]
        assert runbook["redactedEvidenceTemplate"][key] == manifest[key]


def test_batch_runbook_accepts_sample_evidence() -> None:
    manifest = schema_manifest()
    runbook = build_batch_runbook(
        run_evidence=base_run_evidence(),
        run_evidence_path="/tmp/run-evidence.json",
        manifest=manifest,
        manifest_path="/tmp/products-schema-verified-manifest.json",
        sample_evidence=sample_evidence(),
        sample_evidence_path="/tmp/sample-evidence.json",
        authorization_output="/tmp/auth-batch.json",
        target="https://workspace.laicms.com/demo123/products",
        target_identifier="products manifest batch",
    )
    assert runbook["sourceSampleEvidence"] == "/tmp/sample-evidence.json"
    assert runbook["browserStepsExecutable"] is False


def test_batch_runbook_preserves_content_counts() -> None:
    context = {
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        **source_identity(),
    }
    runbook = build_batch_runbook(
        run_evidence={**base_run_evidence(), **context},
        run_evidence_path="/tmp/run-evidence.json",
        manifest={**schema_manifest(), **context},
        manifest_path="/tmp/products-schema-verified-manifest.json",
        sample_evidence={**sample_evidence(), **context},
        sample_evidence_path="/tmp/sample-evidence.json",
        authorization_output="/tmp/auth-batch.json",
        target="https://workspace.laicms.com/demo123/products",
        target_identifier="products manifest batch",
    )
    for key, value in context.items():
        assert runbook[key] == value
        assert runbook["redactedEvidenceTemplate"][key] == value


def test_rejects_unknown_sample_slug() -> None:
    issues = validate_sample_evidence(sample_evidence("missing-slug"), schema_manifest())
    assert any("sampleSlug must exist" in issue for issue in issues), issues


def test_sample_evidence_requires_cover_when_manifest_item_has_media() -> None:
    manifest = schema_manifest()
    manifest["items"][0]["coverImage"] = {
        "url": "https://example.com/source-cover.jpg",
        "alt": "Source-backed product cover",
    }
    evidence = sample_evidence()
    evidence["coverOrMediaVerified"] = False
    evidence["coverOrMediaNote"] = "Image missing but should not pass because manifest requires it."
    issues = validate_sample_evidence(evidence, manifest)
    assert any("manifest sample item has coverImage/media/gallery" in issue for issue in issues), issues


def test_sample_evidence_requires_cover_when_manifest_item_has_media_needs() -> None:
    manifest = schema_manifest()
    manifest["items"][0]["mediaNeeds"] = [{"target": "product.cover", "kind": "cover"}]
    evidence = sample_evidence()
    evidence["coverOrMediaVerified"] = False
    evidence["coverOrMediaNote"] = "Source media requirement still needs public proof."
    issues = validate_sample_evidence(evidence, manifest)
    assert any("mediaNeeds" in issue for issue in issues), issues


if __name__ == "__main__":
    test_sample_runbook_and_evidence()
    test_sample_runbook_preserves_manifest_source_context()
    test_batch_runbook_accepts_sample_evidence()
    test_batch_runbook_preserves_content_counts()
    test_rejects_unknown_sample_slug()
    test_sample_evidence_requires_cover_when_manifest_item_has_media()
    test_sample_evidence_requires_cover_when_manifest_item_has_media_needs()
    print("manifest sample upload regression tests passed.")
