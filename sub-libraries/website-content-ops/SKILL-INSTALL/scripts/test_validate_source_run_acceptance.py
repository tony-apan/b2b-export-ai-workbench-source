#!/usr/bin/env python3
"""Regression tests for source-run acceptance validation."""

from __future__ import annotations

import sys

import json
import hashlib
import tempfile
from pathlib import Path

from test_summarize_source_execution_status import (
    batch_validation,
    confirmation,
    confirmation_decision_matrix,
    content_goal_coverage,
    content_quality_review,
    created_site_binding,
    execution_plan,
    forms_media_settings,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    sample_evidence,
    schema_capture_handoff,
    summarize,
    upload_readiness,
    wiki_review,
    write_json,
    base_args,
)
from test_manifest_sample_upload import content_goal_overages, created_site_submitted_values, overage_quality
from validate_source_run_acceptance import validate_acceptance


def url_fingerprint(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "draftManifestStatus": {
            "products": {"itemCount": 1, "schemaVerified": False},
            "posts": {"itemCount": 1, "schemaVerified": False},
        },
    }


def content_counts() -> dict:
    return {"pages": 1, "products": 1, "posts": 1, "forms": 1, "media": 1, "siteInfoFields": 2}


def source_identity() -> dict:
    return {
        "sourcePackageSha256": "a" * 64,
        "sourceReviewPacketSha256": "b" * 64,
    }


def create_site_handoff() -> dict:
    return {
        "kind": "allincms_confirmed_create_site_handoff",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "authorizationRequired": True,
        "action": "create_site",
        "target": "https://workspace.laicms.com/sites",
        "authorizationRecordCommandHasPlaceholder": True,
        "siteProposal": {"siteName": "Example Site", "siteDescription": "Example description."},
        "forbiddenActions": ["uploading products/posts/media"],
        "stopAfter": "created-site evidence is captured",
    }


def batch_evidence() -> dict:
    return {"kind": "allincms_batch_upload_publish_evidence", "remoteMutationsPerformed": True}


def manifest(content_type: str) -> dict:
    if content_type == "products":
        item = {
            "name": "Example Product",
            "slug": "example-product",
            "description": "Source-backed product description.",
            "content": [{"type": "paragraph", "text": "Source-backed product body."}],
        }
        field_mapping = {"titleField": "name", "descriptionField": "description", "bodyField": "content"}
    else:
        item = {
            "title": "Example Post",
            "slug": "example-post",
            "excerpt": "Source-backed article excerpt.",
            "content": [{"type": "paragraph", "text": "Source-backed article body."}],
        }
        field_mapping = {"titleField": "title", "descriptionField": "excerpt", "bodyField": "content"}
    return {
        "siteKey": "demo123",
        "contentType": content_type,
        "frontendBaseUrl": "https://demo123.web.allincms.com",
        "schemaVerified": True,
        "fieldMapping": field_mapping,
        "payloadTemplate": {"mode": "update", "contentType": content_type},
        "items": [item],
        **source_identity(),
    }


def launch_acceptance() -> dict:
    return {
        "kind": "allincms_launch_acceptance_validation",
        "valid": True,
        "complete": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        **source_identity(),
    }


def final_frontend_audit() -> dict:
    return {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "browserStageMutatedRemote": False,
        "stageId": "final_frontend_audit",
        "siteKey": "demo123",
        "status": "completed",
        "redactedEvidencePointers": [],
        "proofRecorded": ["HTTP status report", "DOM/rich-text report", "image report", "broken-entry list empty"],
        "blockingIssues": [],
        "createdSiteSubmittedValues": created_site_submitted_values(),
        **source_identity(),
    }


def cleanup_evidence() -> dict:
    return {
        "kind": "allincms_probe_cleanup_evidence",
        "siteKey": "demo123",
        "status": "completed",
        "backendVerified": True,
        "frontendVerified": True,
        "cleanedCount": 0,
        "cleanedCandidates": [],
        "noCandidatesVerified": True,
        "scannedSurfaces": ["products", "posts"],
    }


def round_closeout() -> dict:
    return {
        "kind": "allincms_source_run_final_closeout",
        "valid": True,
        "complete": True,
        "localOnly": False,
        "remoteMutationsPerformed": True,
        "completionGaps": [],
        "proof": [
            "source wiki and source package confirmed",
            "site creation and created-site binding verified",
            "schema capture verified for products and posts",
            "manifest sample backend/frontend verification passed",
            "batch upload and publish validation passed",
            "final frontend audit passed",
            "probe cleanup verified",
            "launch acceptance completed",
        ],
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "wikiReview": {},
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "createdSiteSubmittedValues": created_site_submitted_values(),
        **source_identity(),
        "sedimentation": {"status": "updated", "note": "Final launch proof recorded."},
    }


def maintenance_round_closeout() -> dict:
    return {
        "kind": "allincms_round_maintenance_summary",
        "valid": True,
        "complete": False,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "completionGaps": [
            "This is a maintenance closeout summary, not proof of site creation, launch, upload, publish, or cleanup."
        ],
        "proof": ["skill sedimentation checked"],
        "sedimentation": {"status": "updated", "note": "Maintenance finding recorded."},
    }


def counted_pages_site_info_validation(count: int = 1) -> dict:
    data = pages_site_info_validation()
    data["pageCount"] = count
    data["siteInfoFieldCount"] = 2
    return data


def batch_progress_entry(content_type: str) -> dict:
    slug = "example-product" if content_type == "products" else "example-post"
    return {
        "slug": slug,
        "contentType": content_type,
        "backendUrl": f"https://workspace.laicms.com/demo123/{content_type}/abc/update",
        "frontendUrl": f"https://demo123.web.allincms.com/{content_type}/{slug}",
        "saveStatus": "ok",
        "publishStatus": "ok",
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": True,
        "errors": [],
    }


def full_batch_evidence(content_type: str = "products") -> dict:
    return {
        "kind": "allincms_batch_upload_publish_evidence",
        "siteKey": "demo123",
        "contentType": content_type,
        "action": "batch_upload",
        "target": f"https://workspace.laicms.com/demo123/{content_type}",
        "preMutationGate": "passed",
        "schemaGatePass": True,
        "sampleVerificationPass": True,
        "progressLogComplete": True,
        "frontendDetailAuditPass": True,
        "stopConditionMet": True,
        "progressLog": [batch_progress_entry(content_type)],
        "frontendDetailAudit": {
            "checked": True,
            "markdownResidueChecked": True,
            "structuredRichTextChecked": True,
            "detailRouteCount": 1,
            "blockingIssues": [],
        },
        **source_identity(),
    }


def counted_batch_validation(content_type: str = "products", count: int = 1, evidence: str = "", manifest_path: str = "") -> dict:
    data = batch_validation(content_type)
    data.update(source_identity())
    data["manifestItemCount"] = count
    data["progressCount"] = count
    if evidence:
        data["evidence"] = evidence
    if manifest_path:
        data["manifest"] = manifest_path
    return data


def upload_readiness_with_manifest_paths(products_manifest: str, posts_manifest: str) -> dict:
    data = upload_readiness()
    data.update(source_identity())
    for item in data["manifests"]:
        if item["contentType"] == "products":
            item["path"] = products_manifest
            item["itemCount"] = 1
        if item["contentType"] == "posts":
            item["path"] = posts_manifest
            item["itemCount"] = 1
    return data


def full_sample_evidence(content_type: str, manifest_path: str) -> dict:
    data = sample_evidence(content_type)
    slug = "example-product" if content_type == "products" else "example-post"
    data.update(
        {
            "manifestPath": manifest_path,
            "sampleSlug": slug,
            "target": f"https://workspace.laicms.com/demo123/{content_type}",
            "backendUrl": f"https://workspace.laicms.com/demo123/{content_type}/abc/update",
            "frontendUrl": f"https://demo123.web.allincms.com/{content_type}/{slug}",
            "preMutationGate": "passed",
            "coverOrMediaVerified": True,
            "coverOrMediaNote": "",
            "renderAudit": "redacted browser render proof",
            "blockingIssues": [],
            **source_identity(),
        }
    )
    return data


def source_wiki(root: Path) -> tuple[str, str]:
    wiki_dir = root / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    index = wiki_dir / "index.md"
    index.write_text("# Wiki Index\n\n- site\n- pages\n- products\n- posts\n", encoding="utf-8")
    wiki = {
        "kind": "allincms_source_wiki",
        "sourceSet": {
            "inputFiles": [{"path": str(root / "brief.md"), "type": "markdown", "sourceRef": "src-001"}],
            "wikiRefs": [str(index)],
        },
        "site": {
            "siteName": "Example Site",
            "siteDescription": "Example source-backed site.",
            "language": "en",
            "industry": "example",
        },
        "pages": [
            {
                "title": "Home",
                "path": "/",
                "sections": [{"heading": "Example", "body": "Source-backed home page copy."}],
                "sourceRefs": ["src-001"],
            }
        ],
        "products": [
            {
                "name": "Example Product",
                "slug": "example-product",
                "description": "Source-backed product description.",
                "content": [{"type": "paragraph", "text": "Source-backed product body."}],
                "sourceRefs": ["src-001"],
            }
        ],
        "posts": [
            {
                "title": "Example Guide",
                "slug": "example-guide",
                "excerpt": "Source-backed article excerpt.",
                "content": [{"type": "paragraph", "text": "Source-backed article body."}],
                "sourceRefs": ["src-001"],
            }
        ],
        "navigation": {"items": [{"label": "Home", "path": "/"}]},
    }
    return write_json(root / "source-wiki.json", wiki), str(index)


def frontend_audit_report() -> list[dict]:
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
        },
        {
            "url": "https://demo123.web.allincms.com/products/example-product",
            "urlFingerprint": url_fingerprint("https://demo123.web.allincms.com/products/example-product"),
            "routeInstance": "products-detail-1",
            "expectedStatus": 200,
            "status": 200,
            "tagCounts": {"h1": 1},
            "headings": {"h1": ["Example Product"]},
            "imageCount": 1,
            "issues": [],
        },
        {
            "url": "https://demo123.web.allincms.com/posts/example-post",
            "urlFingerprint": url_fingerprint("https://demo123.web.allincms.com/posts/example-post"),
            "routeInstance": "posts-detail-1",
            "expectedStatus": 200,
            "status": 200,
            "tagCounts": {"h1": 1},
            "headings": {"h1": ["Example Post"]},
            "imageCount": 1,
            "issues": [],
        },
    ]


def frontend_audit_inputs_summary() -> dict:
    return {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "contentType": "mixed",
        "staticRouteCount": 1,
        "detailRouteCount": 2,
        "detailRouteInstances": ["products-detail-1", "posts-detail-1"],
        "routePatterns": ["/", "/products/{slug}", "/posts/{slug}"],
        "navigationItemCount": 1,
        "expectedStatus": 200,
    }


def frontend_expected_statuses() -> dict:
    return {
        "https://demo123.web.allincms.com/": 200,
        "https://demo123.web.allincms.com/products/example-product": 200,
        "https://demo123.web.allincms.com/posts/example-post": 200,
    }


def complete_status(root: Path) -> tuple[str, dict[str, str]]:
    source_wiki_path, source_wiki_index = source_wiki(root)
    review = {
        "sourceWiki": source_wiki_path,
        "sourceWikiMarkdown": source_wiki_index,
        "sourceWikiMarkdownIndex": source_wiki_index,
    }
    package_data = package()
    package_data["sourceWiki"] = source_wiki_path
    package_data["wikiReview"] = review
    package_data["contentCounts"] = content_counts()
    package_data["contentQualityReview"] = overage_quality()
    package_data["contentGoalOverages"] = content_goal_overages()
    package_data.update(source_identity())
    package_path = write_json(root / "package.json", package_data)
    review_packet_data = review_packet(package_path)
    review_packet_data["wikiReview"] = review
    review_packet_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    review_packet_data["contentCounts"] = content_counts()
    review_packet_data["contentQualityReview"] = overage_quality()
    review_packet_data["contentGoalOverages"] = content_goal_overages()
    review_packet_data.update(source_identity())
    review_path = write_json(root / "review-packet.json", review_packet_data)
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    confirmation_data["wikiReview"] = review
    confirmation_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    confirmation_data["contentCounts"] = content_counts()
    confirmation_data["contentQualityReview"] = overage_quality()
    confirmation_data["contentGoalOverages"] = content_goal_overages()
    confirmation_data.update(source_identity())
    args = base_args(root)
    args.package = package_path
    args.review_packet = review_path
    args.confirmation = write_json(root / "confirmation.json", confirmation_data)
    execution_plan_data = execution_plan()
    execution_plan_data["wikiReview"] = review
    execution_plan_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    execution_plan_data["contentQualityReview"] = overage_quality()
    execution_plan_data["contentGoalOverages"] = content_goal_overages()
    execution_plan_data.update(source_identity())
    args.execution_plan = write_json(root / "execution-plan.json", execution_plan_data)
    artifact_readiness_data = artifact_readiness()
    artifact_readiness_data["wikiReview"] = review
    artifact_readiness_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    artifact_readiness_data["contentCounts"] = content_counts()
    artifact_readiness_data["contentQualityReview"] = overage_quality()
    artifact_readiness_data["contentGoalOverages"] = content_goal_overages()
    artifact_readiness_data.update(source_identity())
    args.artifact_readiness = write_json(root / "artifact-readiness.json", artifact_readiness_data)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    created_site_binding_data = created_site_binding()
    created_site_binding_data["wikiReview"] = review
    created_site_binding_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    created_site_binding_data["contentCounts"] = content_counts()
    created_site_binding_data["contentQualityReview"] = overage_quality()
    created_site_binding_data["contentGoalOverages"] = content_goal_overages()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    created_site_binding_data.update(source_identity())
    args.created_site_binding = write_json(root / "created-site-binding.json", created_site_binding_data)
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", counted_pages_site_info_validation())
    schema_capture_handoff_data = schema_capture_handoff()
    schema_capture_handoff_data["wikiReview"] = review
    schema_capture_handoff_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    schema_capture_handoff_data["contentQualityReview"] = overage_quality()
    schema_capture_handoff_data["contentGoalOverages"] = content_goal_overages()
    schema_capture_handoff_data.update(source_identity())
    args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff_data)
    manifest_context = {
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "wikiReview": review,
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        "contentCounts": content_counts(),
    }
    products_manifest = write_json(root / "products-manifest.json", {**manifest("products"), **manifest_context})
    posts_manifest = write_json(root / "posts-manifest.json", {**manifest("posts"), **manifest_context})
    args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness_with_manifest_paths(products_manifest, posts_manifest))
    args.sample_evidence = [
        write_json(root / "products-sample-evidence.json", full_sample_evidence("products", products_manifest)),
        write_json(root / "posts-sample-evidence.json", full_sample_evidence("posts", posts_manifest)),
    ]
    products_batch_evidence = write_json(root / "products-batch-evidence.json", full_batch_evidence("products"))
    posts_batch_evidence = write_json(root / "posts-batch-evidence.json", full_batch_evidence("posts"))
    args.batch_evidence = write_json(root / "batch-evidence.json", batch_evidence())
    args.batch_validation = [
        write_json(root / "products-batch-validation.json", counted_batch_validation("products", evidence=products_batch_evidence, manifest_path=products_manifest)),
        write_json(root / "posts-batch-validation.json", counted_batch_validation("posts", evidence=posts_batch_evidence, manifest_path=posts_manifest)),
    ]
    forms_media_settings_data = forms_media_settings()
    forms_media_settings_data["wikiReview"] = review
    forms_media_settings_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    forms_media_settings_data["contentCounts"] = content_counts()
    forms_media_settings_data["contentQualityReview"] = overage_quality()
    forms_media_settings_data["contentGoalOverages"] = content_goal_overages()
    forms_media_settings_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    forms_media_settings_data.update(source_identity())
    forms_media_settings_data["siteInfoFieldCount"] = 2
    forms_media_settings_data["formCount"] = 1
    forms_media_settings_data["mediaCount"] = 1
    forms_media_settings_data.setdefault("verifiedCounts", {})["siteInfoFieldCount"] = 2
    forms_media_settings_data["mediaVerified"] = True
    forms_media_settings_data["deferrals"] = [
        item for item in forms_media_settings_data.get("deferrals", []) if item.get("module") != "media"
    ]
    args.forms_media_settings = write_json(root / "forms-media-settings.json", forms_media_settings_data)
    launch_acceptance_data = launch_acceptance()
    launch_acceptance_data["wikiReview"] = review
    launch_acceptance_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    launch_acceptance_data["contentCounts"] = content_counts()
    launch_acceptance_data["contentQualityReview"] = overage_quality()
    launch_acceptance_data["contentGoalOverages"] = content_goal_overages()
    launch_acceptance_data.update(source_identity())
    args.launch_acceptance = write_json(root / "launch-acceptance.json", launch_acceptance_data)
    frontend_audit_report_path = root / "final-frontend-audit-report.json"
    frontend_audit_report_path.write_text(json.dumps(frontend_audit_report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frontend_audit_inputs_summary_path = write_json(root / "final-frontend-audit-inputs-summary.json", frontend_audit_inputs_summary())
    frontend_expected_statuses_path = write_json(root / "final-frontend-expected-statuses.json", frontend_expected_statuses())
    final_frontend_audit_data = final_frontend_audit()
    final_frontend_audit_data["redactedEvidencePointers"] = [str(frontend_audit_report_path)]
    final_frontend_audit_data["auditReport"] = str(frontend_audit_report_path)
    final_frontend_audit_data["auditInputsSummary"] = frontend_audit_inputs_summary_path
    final_frontend_audit_data["expectedStatuses"] = frontend_expected_statuses_path
    final_frontend_audit_data["navigationItemCount"] = 1
    final_frontend_audit_data["contentGoalCoverage"] = content_goal_coverage()
    final_frontend_audit_data["contentQualityReview"] = overage_quality()
    final_frontend_audit_data["contentGoalOverages"] = content_goal_overages()
    final_frontend_audit_data["wikiReview"] = review
    final_frontend_audit_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    final_frontend_audit_data["contentCounts"] = content_counts()
    final_frontend_audit_data.update(source_identity())
    final_frontend_audit_path = write_json(root / "final-frontend-audit.json", final_frontend_audit_data)
    cleanup_path = write_json(root / "cleanup-evidence.json", cleanup_evidence())
    round_closeout_data = round_closeout()
    round_closeout_data["wikiReview"] = review
    round_closeout_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    round_closeout_data["contentQualityReview"] = overage_quality()
    round_closeout_data["contentGoalOverages"] = content_goal_overages()
    round_closeout_data.update(source_identity())
    round_closeout_path = write_json(root / "round-closeout.json", round_closeout_data)
    status = summarize(args)
    status_path = write_json(root / "source-execution-status.json", status)
    paths = {
        "package": args.package,
        "review_packet": args.review_packet,
        "confirmation": args.confirmation,
        "launch_acceptance": args.launch_acceptance,
        "created_site_binding": args.created_site_binding,
        "upload_readiness": args.upload_readiness,
        "products_manifest": products_manifest,
        "posts_manifest": posts_manifest,
        "products_sample": args.sample_evidence[0],
        "posts_sample": args.sample_evidence[1],
        "products_batch_evidence": products_batch_evidence,
        "posts_batch_evidence": posts_batch_evidence,
        "products_batch_validation": args.batch_validation[0],
        "posts_batch_validation": args.batch_validation[1],
        "forms_media_settings": args.forms_media_settings,
        "final_frontend_audit": final_frontend_audit_path,
        "final_frontend_audit_report": str(frontend_audit_report_path),
        "final_frontend_audit_inputs_summary": frontend_audit_inputs_summary_path,
        "final_frontend_expected_statuses": frontend_expected_statuses_path,
        "cleanup_evidence": cleanup_path,
        "round_closeout": round_closeout_path,
        "source_wiki": source_wiki_path,
        "source_wiki_markdown_index": source_wiki_index,
    }
    return status_path, paths


def complete_handoff(root: Path, status_path: str) -> str:
    return write_json(
        root / "source-next-stage-handoff.json",
        {
            "kind": "allincms_source_next_stage_handoff",
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "preparedOnly": True,
            "isUserAuthorization": False,
            "sourceExecutionStatus": status_path,
            "currentStage": "complete",
            "supported": False,
            "mode": "complete",
        },
    )


def add_taxonomy_validation_to_status(root: Path, status_path: str, taxonomy_count: int = 2) -> str:
    taxonomy_path = write_json(
        root / f"taxonomy-validation-{taxonomy_count}.json",
        {
            "kind": "allincms_taxonomy_execution_evidence_validation",
            "valid": True,
            "siteKey": "demo123",
            "taxonomyMappingCount": taxonomy_count,
            "taxonomyPrerequisiteSatisfied": True,
            "issues": [],
        },
    )
    status = json.loads(Path(status_path).read_text(encoding="utf-8"))
    status["stages"]["taxonomy_execution"] = {
        "status": "passed",
        "evidence": taxonomy_path,
        "blockers": [],
        "nextAction": "",
    }
    status["stageCount"] = len(status["stages"])
    return write_json(root / f"source-execution-status-taxonomy-{taxonomy_count}.json", status)


def rewrite_content_goal_coverage(path: str, coverage: dict) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["contentGoalCoverage"] = coverage
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_accepts_complete_source_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is True, report
        assert report["contentGoalOverages"] == content_goal_overages()


def test_rejects_final_closeout_missing_content_goal_overages_when_warning_exists() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        closeout = json.loads(Path(paths["round_closeout"]).read_text(encoding="utf-8"))
        closeout.pop("contentGoalOverages", None)
        bad_closeout = write_json(root / "round-closeout-missing-overages.json", closeout)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=bad_closeout,
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        assert any(
            issue["key"] == "round_closeout_invalid" and "contentGoalOverages" in issue["message"]
            for issue in report["issues"]
        )


def test_accepts_site_info_count_from_pages_site_info_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        forms_data = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms_data.pop("siteInfoFieldCount", None)
        forms_data.get("verifiedCounts", {}).pop("siteInfoFieldCount", None)
        paths["forms_media_settings"] = write_json(root / "forms-media-settings-no-site-info-count.json", forms_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is True, report
        assert report["artifacts"]["finalStructureCounts"]["actual"]["siteInfoFields"] == 2


def test_blocks_existing_site_binding_for_new_site_objective() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        binding = json.loads(Path(paths["created_site_binding"]).read_text(encoding="utf-8"))
        binding["siteBindingMode"] = "existing_site"
        binding["siteCreationStatus"] = "existing_site_selected"
        existing_binding_path = write_json(root / "existing-site-binding.json", binding)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=existing_binding_path,
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="用户确认后 AI 新建站点并上传内容",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "created_site_required" in keys


def test_accepts_multiple_upload_readiness_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        extra_readiness_path = write_json(root / "posts-upload-readiness.json", upload_readiness())
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=[paths["upload_readiness"], extra_readiness_path],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is True, report
        assert report["artifacts"]["uploadReadiness"] == [paths["upload_readiness"], extra_readiness_path]


def test_blocks_incomplete_source_status_and_missing_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status = json.loads(Path(status_path).read_text(encoding="utf-8"))
        status["complete"] = False
        status["currentStage"] = "launch_acceptance"
        status["stages"]["launch_acceptance"]["status"] = "blocked"
        status["stages"]["launch_acceptance"]["blockers"] = ["final frontend audit missing"]
        status_path = write_json(root / "source-execution-status.incomplete.json", status)
        report = validate_acceptance(
            status_path=status_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "source_status_incomplete" in keys
        assert "source_stage_failures" in keys
        assert "next_stage_handoff_missing" in keys


def test_blocks_missing_source_wiki_layer() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        package_data = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package_data.pop("sourceWiki", None)
        package_path = write_json(root / "package-without-source-wiki.json", package_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=package_path,
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "source_wiki_missing" in keys


def test_blocks_json_wikiref_without_readable_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        wiki_data = json.loads(Path(paths["source_wiki"]).read_text(encoding="utf-8"))
        json_ref = write_json(root / "raw-extraction" / "source-wiki.json", wiki_data)
        wiki_data["sourceSet"]["wikiRefs"] = [json_ref]
        source_wiki_path = write_json(root / "source-wiki-json-ref-only.json", wiki_data)
        package_data = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package_data["sourceWiki"] = source_wiki_path
        package_path = write_json(root / "package-json-ref-only.json", package_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=package_path,
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "source_wiki_markdown_missing" in keys


def test_blocks_content_goal_coverage_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        launch_data = launch_acceptance()
        launch_data["contentGoalCoverage"] = {**content_goal_coverage(), "complete": False, "missing": ["posts"]}
        launch_path = write_json(root / "launch-acceptance-drift.json", launch_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=launch_path,
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "content_goal_coverage_invalid" in keys


def test_blocks_content_quality_review_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        launch_data = launch_acceptance()
        launch_data["contentQualityReview"] = {
            **content_quality_review(),
            "readyShape": False,
            "warnings": ["posts_present_without_post_categories"],
            "reviewRequired": True,
        }
        launch_path = write_json(root / "launch-acceptance-quality-drift.json", launch_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=launch_path,
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "content_quality_review_invalid" in keys


def test_blocks_wiki_review_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        launch_data = json.loads(Path(paths["launch_acceptance"]).read_text(encoding="utf-8"))
        launch_data["wikiReview"] = {**launch_data["wikiReview"], "sourceWikiMarkdown": str(root / "other-manifest.json")}
        launch_path = write_json(root / "launch-acceptance-wiki-drift.json", launch_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=launch_path,
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "wiki_review_invalid" in keys


def test_blocks_confirmation_decision_matrix_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        launch_data = json.loads(Path(paths["launch_acceptance"]).read_text(encoding="utf-8"))
        launch_data["confirmationDecisionMatrix"] = [
            {**confirmation_decision_matrix()[0], "decision": "defer", "deferDecision": "changed"}
        ]
        launch_path = write_json(root / "launch-acceptance-matrix-drift.json", launch_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=launch_path,
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "confirmation_decision_matrix_invalid" in keys


def test_blocks_forms_media_settings_direct_validation_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        forms_data = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms_data["mediaVerified"] = False
        forms_data["deferrals"] = [
            {"module": "tracking", "reason": "analytics tracking is out of scope until user provides an ID"}
        ]
        bad_forms_path = write_json(root / "forms-media-settings-missing-media-deferral.json", forms_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=bad_forms_path,
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "forms_media_settings_direct_validation_failed" in keys


def test_blocks_forms_media_settings_wiki_review_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        forms_data = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms_data["wikiReview"] = {**forms_data["wikiReview"], "sourceWikiMarkdown": str(root / "other-manifest.json")}
        bad_forms_path = write_json(root / "forms-media-settings-wiki-drift.json", forms_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=bad_forms_path,
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "wiki_review_invalid" in keys


def test_blocks_final_frontend_audit_report_with_blocking_issue() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        reports = frontend_audit_report()
        reports[1]["issues"] = [{"code": "literal_bold", "severity": "error"}]
        bad_report_path = root / "final-frontend-audit-report-blocked.json"
        bad_report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["redactedEvidencePointers"] = [str(bad_report_path)]
        audit_data["auditReport"] = str(bad_report_path)
        bad_audit_path = write_json(root / "final-frontend-audit-with-blocked-report.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "DOM/rich-text issue literal_bold" in messages


def test_blocks_final_frontend_audit_wrong_detail_slug_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        reports = frontend_audit_report()
        reports[1]["url"] = "https://demo123.web.allincms.com/products/wrong-product"
        reports[1]["urlFingerprint"] = url_fingerprint("https://demo123.web.allincms.com/products/wrong-product")
        bad_report_path = root / "final-frontend-audit-report-wrong-slug.json"
        bad_report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["redactedEvidencePointers"] = [str(bad_report_path)]
        audit_data["auditReport"] = str(bad_report_path)
        bad_audit_path = write_json(root / "final-frontend-audit-wrong-slug.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "expected concrete URL fingerprints" in messages


def test_blocks_final_frontend_audit_source_context_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["wikiReview"] = {**audit_data["wikiReview"], "sourceWikiMarkdown": str(root / "other-manifest.json")}
        bad_audit_path = write_json(root / "final-frontend-audit-source-context-drift.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "wiki_review_invalid" in keys


def test_blocks_created_site_submitted_value_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "name": "Different Demo",
        }
        bad_audit_path = write_json(root / "final-frontend-audit-submitted-value-drift.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "created_site_submitted_values_invalid" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "createdSiteSubmittedValues mismatch" in messages


def test_blocks_missing_created_site_submitted_values_for_new_site_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        for key in (
            "created_site_binding",
            "launch_acceptance",
            "forms_media_settings",
            "final_frontend_audit",
            "round_closeout",
        ):
            data = json.loads(Path(paths[key]).read_text(encoding="utf-8"))
            data.pop("createdSiteSubmittedValues", None)
            paths[key] = write_json(root / f"{key}-missing-submitted-values.json", data)
        status = json.loads(Path(status_path).read_text(encoding="utf-8"))
        status.pop("createdSiteSubmittedValues", None)
        status_path = write_json(root / "source-execution-status-missing-submitted-values.json", status)
        handoff_path = complete_handoff(root, status_path)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="用户确认后 AI 新建站点并上传内容",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "created_site_submitted_values_invalid" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "createdSiteSubmittedValues missing from created-site source-context artifacts" in messages


def test_blocks_final_content_counts_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["contentCounts"] = {"pages": 1, "products": 2, "posts": 1}
        bad_audit_path = write_json(root / "final-frontend-audit-content-counts-drift.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "content_counts_invalid" in keys


def test_blocks_source_identity_drift_at_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["sourceReviewPacketSha256"] = "c" * 64
        bad_audit_path = write_json(root / "final-frontend-audit-source-identity-drift.json", audit_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "source_identity_invalid" in keys


def test_blocks_final_closeout_source_context_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        closeout_data = json.loads(Path(paths["round_closeout"]).read_text(encoding="utf-8"))
        closeout_data["contentCounts"] = {"pages": 1, "products": 2, "posts": 1}
        bad_closeout_path = write_json(root / "round-closeout-content-counts-drift.json", closeout_data)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=bad_closeout_path,
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "content_counts_invalid" in keys


def test_blocks_cleanup_without_candidate_scan_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        cleanup = cleanup_evidence()
        cleanup.pop("noCandidatesVerified", None)
        cleanup.pop("scannedSurfaces", None)
        bad_cleanup_path = write_json(root / "cleanup-without-scan-proof.json", cleanup)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=bad_cleanup_path,
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "cleanup_evidence_direct_validation_failed" in keys


def test_blocks_maintenance_round_closeout_as_final_source_run_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        maintenance_closeout_path = write_json(root / "maintenance-round-closeout.json", maintenance_round_closeout())
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=maintenance_closeout_path,
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "maintenance closeout summaries cannot prove final source-run browser/upload/launch completion" in messages
        assert "final source-run closeout must have complete=true" in messages


def test_blocks_wiki_review_not_bound_to_final_source_wiki() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_path=write_json(root / "other-source-wiki.json", {
                **json.loads(Path(paths["source_wiki"]).read_text(encoding="utf-8")),
                "site": {
                    "siteName": "Other",
                    "siteDescription": "Other source-backed site.",
                    "language": "en",
                    "industry": "example",
                },
            }),
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "wiki_review_binding_mismatch" in keys


def test_blocks_missing_final_artifact_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "created_site_binding_missing" in keys
        assert "upload_readiness_missing" in keys
        assert "sample_evidence_missing" in keys
        assert "batch_validation_missing" in keys


def test_blocks_cross_site_sample_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        sample = json.loads(Path(paths["products_sample"]).read_text(encoding="utf-8"))
        sample["siteKey"] = "other-site"
        sample["frontendUrl"] = "https://other-site.web.allincms.com/products/example"
        bad_sample_path = write_json(root / "products-sample-other-site.json", sample)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[bad_sample_path, paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "site_identity_mismatch" in keys


def test_blocks_sample_evidence_that_fails_direct_manifest_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        sample = json.loads(Path(paths["products_sample"]).read_text(encoding="utf-8"))
        sample["sampleSlug"] = "not-in-manifest"
        sample["frontendUrl"] = "https://demo123.web.allincms.com/products/not-in-manifest"
        bad_sample_path = write_json(root / "products-sample-bad-slug.json", sample)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[bad_sample_path, paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "sampleSlug must exist in manifest.items" in messages


def test_blocks_missing_sample_evidence_for_planned_content_type() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "sample evidence for posts is required" in messages


def test_blocks_batch_validation_without_direct_evidence_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)
        validation = json.loads(Path(paths["products_batch_validation"]).read_text(encoding="utf-8"))
        validation.pop("evidence", None)
        bad_validation_path = write_json(root / "products-batch-validation-without-evidence.json", validation)
        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[bad_validation_path, paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "batch_direct_validation_failed" in keys


def test_blocks_final_content_count_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        handoff_path = complete_handoff(root, status_path)

        package_data = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package_data["contentPlan"]["products"].append({"name": "Second Product", "slug": "second-product"})
        package_data["manifests"]["products"]["items"].append({"slug": "second-product"})
        coverage = content_goal_coverage()
        coverage["counts"] = {**coverage["counts"], "products": 2, "productManifestItems": 2}
        package_data["contentGoalCoverage"] = coverage
        package_path = write_json(root / "package-two-products.json", package_data)

        review_data = review_packet(package_path)
        review_data["contentGoalCoverage"] = coverage
        review_path = write_json(root / "review-packet-two-products.json", review_data)

        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = review_path
        confirmation_data["contentGoalCoverage"] = coverage
        confirmation_path = write_json(root / "confirmation-two-products.json", confirmation_data)

        launch_data = launch_acceptance()
        launch_data["contentGoalCoverage"] = coverage
        launch_path = write_json(root / "launch-acceptance-two-products.json", launch_data)

        status = json.loads(Path(status_path).read_text(encoding="utf-8"))
        status["contentGoalCoverage"] = coverage
        status_path = write_json(root / "source-execution-status-two-products.json", status)
        handoff_path = complete_handoff(root, status_path)

        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=package_path,
            review_packet_path=review_path,
            confirmation_path=confirmation_path,
            launch_acceptance_path=launch_path,
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "final_content_count_mismatch" in keys


def test_blocks_final_navigation_count_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        audit_data = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit_data["navigationItemCount"] = 0
        bad_audit_path = write_json(root / "final-frontend-audit-navigation-shortfall.json", audit_data)

        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=bad_audit_path,
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "final_structure_count_mismatch" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "navigation proof count 0" in messages


def test_blocks_final_taxonomy_count_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        coverage = content_goal_coverage()
        coverage["counts"] = {**coverage["counts"], "productCategories": 1, "postCategories": 1}
        for key in ("package", "review_packet", "confirmation", "launch_acceptance", "final_frontend_audit"):
            rewrite_content_goal_coverage(paths[key], coverage)
        status = json.loads(Path(status_path).read_text(encoding="utf-8"))
        status["contentGoalCoverage"] = coverage
        status_path = write_json(root / "source-execution-status-taxonomy-goal.json", status)
        status_path = add_taxonomy_validation_to_status(root, status_path, taxonomy_count=1)
        handoff_path = complete_handoff(root, status_path)

        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "final_structure_count_mismatch" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "taxonomy mapping count 1" in messages


def test_blocks_final_forms_media_count_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        forms_data = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms_data["formCount"] = 0
        forms_data["mediaCount"] = 0
        bad_forms_path = write_json(root / "forms-media-settings-count-shortfall.json", forms_data)

        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=bad_forms_path,
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "final_structure_count_mismatch" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "form proof count 0" in messages
        assert "media proof count 0" in messages


def test_blocks_final_site_info_field_count_shortfall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path, paths = complete_status(root)
        status_path = add_taxonomy_validation_to_status(root, status_path)
        handoff_path = complete_handoff(root, status_path)
        forms_data = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms_data["siteInfoFieldCount"] = 1
        forms_data["verifiedCounts"]["siteInfoFieldCount"] = 1
        bad_forms_path = write_json(root / "forms-media-settings-site-info-shortfall.json", forms_data)

        report = validate_acceptance(
            status_path=status_path,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=bad_forms_path,
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=paths["round_closeout"],
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is False
        keys = {issue["key"] for issue in report["issues"]}
        assert "final_structure_count_mismatch" in keys
        messages = "\n".join(issue["message"] for issue in report["issues"])
        assert "site-info field proof count 1" in messages
if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source run acceptance validation regression tests passed.")
