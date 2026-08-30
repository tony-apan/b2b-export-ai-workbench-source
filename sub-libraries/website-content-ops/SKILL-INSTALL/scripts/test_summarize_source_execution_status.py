#!/usr/bin/env python3
"""Regression tests for source execution status summary."""

from __future__ import annotations

import sys

import argparse
import json
import tempfile
from pathlib import Path

from summarize_source_execution_status import summarize


_WIKI_REVIEW: dict | None = None


def wiki_review(root: Path | None = None) -> dict:
    global _WIKI_REVIEW
    existing_index = _WIKI_REVIEW.get("sourceWikiMarkdownIndex") if isinstance(_WIKI_REVIEW, dict) else ""
    if _WIKI_REVIEW is None or (existing_index and not Path(existing_index).exists()):
        base = root or Path(tempfile.mkdtemp())
        wiki_dir = base / "wiki-review"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        index = wiki_dir / "index.md"
        source_wiki = wiki_dir / "source-wiki.json"
        manifest = wiki_dir / "manifest.json"
        index.write_text("# Source Wiki\n\n- site\n- pages\n- products\n- posts\n", encoding="utf-8")
        source_wiki.write_text('{"kind":"allincms_source_wiki"}\n', encoding="utf-8")
        manifest.write_text('{"kind":"allincms_source_wiki_markdown_export"}\n', encoding="utf-8")
        _WIKI_REVIEW = {
            "sourceWiki": str(source_wiki),
            "sourceWikiMarkdown": str(manifest),
            "sourceWikiMarkdownIndex": str(index),
        }
    return dict(_WIKI_REVIEW)


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict) and "contentQualityReview" in data and "wikiReview" not in data:
        data = {**data, "wikiReview": wiki_review(path.parent)}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def base_args(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        package="",
        review_packet="",
        confirmation="",
        execution_plan="",
        artifact_readiness="",
        create_site_handoff="",
        pages_site_info_handoff="",
        pages_site_info_evidence="",
        pages_site_info_validation="",
        created_site_binding="",
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff="",
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation=[],
        forms_media_settings="",
        launch_acceptance="",
        output=str(root / "status.json"),
        fail_on_blocked=False,
        json=False,
    )


def package() -> dict:
    return {
        "kind": "allincms_source_site_package",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "targetMode": "new_site",
        "siteProposal": {"siteName": "Example Site", "siteDescription": "Example description."},
        "contentPlan": {
            "siteInfo": {"draftSeoTitle": "Example Site", "draftSeoDescription": "Example SEO description."},
            "navigation": {"items": [{"label": "Home", "path": "/"}]},
            "pages": [{"title": "Home", "path": "/"}],
            "products": [{"name": "Example Product", "slug": "example-product"}],
            "posts": [{"title": "Example Post", "slug": "example-post"}],
            "forms": [{"name": "Contact Form", "fieldCount": 3}],
            "media": [{"kind": "image", "usage": "logo"}],
        },
        "manifests": {
            "products": {"items": [{"slug": "example-product"}]},
            "posts": {"items": [{"slug": "example-post"}]},
        },
    }


def content_goal_coverage() -> dict:
    return {
        "goal": "source files distilled into website information, single pages, products, articles, navigation, and draft manifests",
        "complete": True,
        "checks": {
            "siteProposal": True,
            "siteInfo": True,
            "pages": True,
            "products": True,
            "posts": True,
            "navigation": True,
            "manifests.products": True,
            "manifests.posts": True,
        },
        "missing": [],
        "counts": {
            "pages": 1,
            "products": 1,
            "posts": 1,
            "forms": 1,
            "media": 1,
            "siteInfoFields": 2,
            "navigationItems": 1,
            "productCategories": 0,
            "postCategories": 0,
            "productTags": 0,
            "postTags": 0,
            "productManifestItems": 1,
            "postManifestItems": 1,
        },
        "declaredContentGoals": {},
    }


def content_quality_review() -> dict:
    return {
        "readyShape": True,
        "warnings": [],
        "contentCounts": {"pages": 1, "products": 1, "posts": 1, "forms": 0, "media": 0},
        "navigationPathCount": 1,
        "navigationPathsUnique": True,
        "taxonomyCounts": {"productCategories": 1, "postCategories": 1, "productTags": 0, "postTags": 0},
        "minimumCopyLengths": {"page": 140, "product": 120, "post": 160},
        "reviewRequired": False,
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


def created_site_submitted_values() -> dict:
    return {
        "name": "Example Demo",
        "description": "Example demo site for source-backed product publishing and article planning.",
    }


def confirmation() -> dict:
    return {
        "kind": "allincms_source_site_package_confirmation",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourceReviewPacket": "/tmp/review-packet.json",
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
    }


def review_packet(package_path: str) -> dict:
    return {
        "kind": "allincms_source_package_review_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourcePackage": package_path,
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
    }


def execution_plan() -> dict:
    return {
        "kind": "allincms_confirmed_site_execution_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "targetMode": "new_site",
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
    }


def artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
        "draftManifestStatus": {"products": {"itemCount": 1, "schemaVerified": False}, "posts": {"itemCount": 1, "schemaVerified": False}},
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


def pages_site_info_handoff() -> dict:
    return {
        "kind": "allincms_pages_site_info_browser_handoff",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "siteInfo": {
            "browserStepsExecutable": False,
            "preMutationGateCommand": "python3 check_pre_mutation_gate.py --action save_site_settings",
        },
        "pages": [
            {
                "browserStepsExecutable": False,
                "actions": [
                    {
                        "action": "create_theme_page",
                        "browserStepsExecutable": False,
                    }
                ],
            }
        ],
    }


def pages_site_info_validation() -> dict:
    return {
        "kind": "allincms_pages_site_info_execution_evidence_validation",
        "valid": True,
        "launchPrerequisiteSatisfied": True,
        "pageCount": 1,
        "issues": [],
    }


def created_site_binding() -> dict:
    return {
        "kind": "allincms_created_site_artifact_binding",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "schemaVerified": False,
        "siteBindingMode": "created_site",
        "siteCreationStatus": "created_verified",
        "siteKey": "demo123",
        "frontendBaseUrl": "https://demo123.web.allincms.com",
        "createdSiteSubmittedValues": created_site_submitted_values(),
        "contentGoalCoverage": content_goal_coverage(),
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
        "boundArtifacts": {
            "productsManifest": "/tmp/products.json",
            "postsManifest": "/tmp/posts.json",
        },
    }


def taxonomy_plan() -> dict:
    return {
        "kind": "allincms_confirmed_taxonomy_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "items": {
            "productCategoryCount": 1,
            "productTagCount": 0,
            "postCategoryCount": 0,
            "postTagCount": 0,
            "productCategories": [{"label": "Example Category", "slug": "example-category"}],
        },
    }


def artifact_readiness_with_taxonomy_plan(root: Path) -> dict:
    data = artifact_readiness()
    taxonomy_path = root / "taxonomy-plan.json"
    write_json(taxonomy_path, taxonomy_plan())
    data["artifacts"] = {"taxonomyPlan": str(taxonomy_path)}
    return data


def taxonomy_handoff() -> dict:
    return {
        "kind": "allincms_taxonomy_execution_handoff",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "browserStepsExecutable": False,
        "preflightIssues": [],
        "actions": [
            {
                "action": "create_or_map_products_category",
                "contentType": "products",
                "termKind": "category",
                "term": {"label": "Example Category", "slug": "example-category"},
                "targetIdentifier": "products:category:example-category",
                "browserStepsExecutable": False,
            }
        ],
    }


def taxonomy_validation() -> dict:
    return {
        "kind": "allincms_taxonomy_execution_evidence_validation",
        "valid": True,
        "siteKey": "demo123",
        "taxonomyPrerequisiteSatisfied": True,
        "issues": [],
    }


def schema_capture_handoff() -> dict:
    return {
        "kind": "allincms_schema_capture_handoff",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "contentQualityReview": content_quality_review(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
        "stages": [
            {
                "contentType": "products",
                "status": "ready_for_create_probe_authorization",
                "itemCount": 1,
                "manifest": "/tmp/products.json",
                "createProbe": {
                    "authorizationRecordCommand": "python3 ... <paste current user authorization text here>",
                    "preMutationGateCommand": "python3 check_pre_mutation_gate.py --action create_product_probe",
                    "browserStepsExecutable": False,
                },
            }
        ],
    }


def upload_readiness() -> dict:
    return {
        "kind": "allincms_manifest_upload_readiness_report",
        "overallStatus": "ready_for_sample_upload",
        **source_identity(),
        "manifests": [
            {
                "contentType": "products",
                "siteKey": "demo123",
                "schemaVerified": True,
                "status": "ready_for_sample_upload",
                "schemaGate": {"ok": True},
            },
            {
                "contentType": "posts",
                "siteKey": "demo123",
                "schemaVerified": True,
                "status": "ready_for_sample_upload",
                "schemaGate": {"ok": True},
            }
        ],
    }


def upload_readiness_for(content_type: str) -> dict:
    return {
        "kind": "allincms_manifest_upload_readiness_report",
        "overallStatus": "ready_for_sample_upload",
        "manifests": [
            {
                "contentType": content_type,
                "status": "ready_for_sample_upload",
                "itemCount": 1,
            }
        ],
    }


def sample_evidence(content_type: str = "products") -> dict:
    return {
        "kind": "allincms_manifest_sample_upload_evidence",
        "siteKey": "demo123",
        "contentType": content_type,
        "frontendUrl": f"https://demo123.web.allincms.com/{content_type}/example",
        "schemaGatePass": True,
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": False,
        "coverOrMediaNote": "No image in scope for this test.",
        "saveStatus": "ok",
        "publishStatus": "ok",
        "stopConditionMet": True,
        **source_identity(),
    }


def batch_validation(content_type: str = "products") -> dict:
    return {
        "kind": "allincms_batch_upload_publish_evidence_validation",
        "valid": True,
        "siteKey": "demo123",
        "contentType": content_type,
        "manifestItemCount": 1,
        "progressCount": 1,
        "issues": [],
        **source_identity(),
    }


def forms_media_settings() -> dict:
    return {
        "kind": "allincms_forms_media_settings_evidence",
        "siteKey": "demo123",
        "status": "partially_verified_with_explicit_deferrals",
        "siteInfoVerified": True,
        "formsVerified": True,
        "mediaVerified": False,
        "domainsRecorded": True,
        "trackingRecorded": False,
        "siteInfoFieldCount": 1,
        "formCount": 1,
        "mediaCount": 0,
        "verifiedCounts": {"siteInfoFieldCount": 1, "formCount": 1, "mediaCount": 0},
        "deferrals": [
            {"module": "media", "reason": "temporary demo has no uploaded media beyond remote image URLs"},
            {"module": "tracking", "reason": "analytics tracking is out of scope until user provides an ID"},
        ],
        "createdSiteSubmittedValues": created_site_submitted_values(),
        "wikiReview": wiki_review(),
        "confirmationDecisionMatrix": confirmation_decision_matrix(),
        **source_identity(),
    }


def launch_acceptance() -> dict:
    return {
        "kind": "allincms_launch_acceptance_validation",
        "valid": True,
        "complete": True,
        "createdSiteSubmittedValues": created_site_submitted_values(),
    }


def fill_base(root: Path, args: argparse.Namespace) -> None:
    args.package = write_json(root / "package.json", package())
    args.review_packet = write_json(root / "review-packet.json", review_packet(args.package))
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = args.review_packet
    args.confirmation = write_json(root / "confirmation.json", confirmation_data)
    args.execution_plan = write_json(root / "plan.json", execution_plan())
    args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness())


def test_status_blocks_at_review_packet_before_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        args.package = write_json(root / "package.json", package())
        report = summarize(args)
        assert report["currentStage"] == "review_packet", report
        assert report["stages"]["source_package"]["status"] == "passed"


def test_status_blocks_at_create_site_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        report = summarize(args)
        assert report["currentStage"] == "create_site_handoff", report
        assert report["stages"]["artifact_export"]["status"] == "passed"
        assert report["contentGoalCoverage"]["complete"] is True
        assert report["contentGoalCoverageIssues"] == []
        assert report["contentQualityReview"] == content_quality_review()
        assert report["contentQualityReviewIssues"] == []
        assert report["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert report["confirmationDecisionMatrixIssues"] == []


def test_status_blocks_at_created_site_binding_after_create_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        report = summarize(args)
        assert report["currentStage"] == "created_site_binding", report
        assert report["stages"]["create_site_handoff"]["status"] == "passed"


def test_review_packet_source_package_accepts_equivalent_resolved_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        real_root = base / "real"
        alias_root = base / "alias"
        real_root.mkdir()
        alias_root.symlink_to(real_root, target_is_directory=True)
        args = base_args(real_root)
        fill_base(real_root, args)
        alias_package = alias_root / "package.json"
        review_data = review_packet(str(alias_package))
        args.review_packet = write_json(real_root / "review-packet-alias.json", review_data)
        report = summarize(args)
        assert report["stages"]["review_packet"]["status"] == "passed", report["stages"]["review_packet"]
        assert report["currentStage"] == "create_site_handoff", report


def test_status_blocks_at_pages_site_info_handoff_after_created_site_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        report = summarize(args)
        assert report["currentStage"] == "pages_site_info_handoff", report
        assert report["stages"]["created_site_binding"]["status"] == "passed"


def test_status_blocks_missing_created_site_submitted_values_for_new_site_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        binding = created_site_binding()
        binding.pop("createdSiteSubmittedValues", None)
        args.created_site_binding = write_json(root / "binding-missing-submitted-values.json", binding)
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        report = summarize(args)
        assert report["currentStage"] == "created_site_binding", report
        assert report["stages"]["created_site_binding"]["status"] == "blocked"
        assert "createdSiteSubmittedValues missing from created-site source-context artifacts" in report["stages"]["created_site_binding"]["blockers"]
        assert report["createdSiteSubmittedValuesIssues"] == [
            "createdSiteSubmittedValues missing from created-site source-context artifacts"
        ]


def test_status_allows_existing_site_binding_without_submitted_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        package_data = json.loads(Path(args.package).read_text(encoding="utf-8"))
        package_data["targetMode"] = "existing_site"
        args.package = write_json(Path(args.package), package_data)
        plan_data = json.loads(Path(args.execution_plan).read_text(encoding="utf-8"))
        plan_data["targetMode"] = "existing_site"
        args.execution_plan = write_json(Path(args.execution_plan), plan_data)
        binding = created_site_binding()
        binding["siteBindingMode"] = "existing_site"
        binding["siteCreationStatus"] = "existing_site_selected"
        binding.pop("createdSiteSubmittedValues", None)
        args.created_site_binding = write_json(root / "existing-site-binding.json", binding)
        report = summarize(args)
        assert report["currentStage"] == "pages_site_info_handoff", report
        assert report["stages"]["created_site_binding"]["status"] == "passed"
        assert report["createdSiteSubmittedValuesIssues"] == []
        assert "createdSiteSubmittedValues" not in report


def test_status_blocks_at_schema_manifests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        report = summarize(args)
        assert report["currentStage"] == "pages_site_info_execution", report
        assert report["stages"]["created_site_binding"]["status"] == "passed"
        assert report["stages"]["pages_site_info_handoff"]["status"] == "passed"


def test_status_blocks_at_schema_capture_handoff_after_pages_site_info_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        report = summarize(args)
        assert report["currentStage"] == "schema_capture_handoff", report
        assert report["stages"]["pages_site_info_execution"]["status"] == "passed"


def test_status_blocks_at_taxonomy_handoff_when_taxonomy_plan_has_terms() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness_with_taxonomy_plan(root))
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        report = summarize(args)
        assert report["taxonomyRequired"] is True
        assert report["currentStage"] == "taxonomy_execution_handoff", report


def test_status_blocks_at_schema_capture_after_taxonomy_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness_with_taxonomy_plan(root))
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.taxonomy_handoff = write_json(root / "taxonomy-handoff.json", taxonomy_handoff())
        args.taxonomy_validation = write_json(root / "taxonomy-validation.json", taxonomy_validation())
        report = summarize(args)
        assert report["currentStage"] == "schema_capture_handoff", report
        assert report["stages"]["taxonomy_execution"]["status"] == "passed"


def test_status_blocks_at_schema_manifests_after_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        report = summarize(args)
        assert report["currentStage"] == "schema_manifests", report
        assert report["stages"]["schema_capture_handoff"]["status"] == "passed"


def test_status_blocks_at_batch_after_sample() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        report = summarize(args)
        assert report["currentStage"] == "batch_upload", report
        assert report["stages"]["sample_upload"]["status"] == "passed"


def test_status_merges_multiple_upload_readiness_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = [
            write_json(root / "products-upload-readiness.json", upload_readiness_for("products")),
            write_json(root / "posts-upload-readiness.json", upload_readiness_for("posts")),
        ]
        report = summarize(args)
        assert report["currentStage"] == "sample_upload", report
        assert report["stages"]["schema_manifests"]["status"] == "passed"
        assert report["contentTypeCoverage"]["uploadReadiness"] == ["posts", "products"]


def test_status_blocks_at_forms_media_settings_after_batch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        args.batch_validation = [
            write_json(root / "products-batch-validation.json", batch_validation("products")),
            write_json(root / "posts-batch-validation.json", batch_validation("posts")),
        ]
        report = summarize(args)
        assert report["currentStage"] == "forms_media_settings", report
        assert report["stages"]["batch_upload"]["status"] == "passed"


def test_status_blocks_at_launch_acceptance_after_forms_media_settings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        args.batch_validation = [
            write_json(root / "products-batch-validation.json", batch_validation("products")),
            write_json(root / "posts-batch-validation.json", batch_validation("posts")),
        ]
        args.forms_media_settings = write_json(root / "forms-media-settings.json", forms_media_settings())
        report = summarize(args)
        assert report["currentStage"] == "launch_acceptance", report
        assert report["stages"]["forms_media_settings"]["status"] == "passed"


def test_status_complete_when_all_artifacts_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        args.batch_validation = [
            write_json(root / "products-batch-validation.json", batch_validation("products")),
            write_json(root / "posts-batch-validation.json", batch_validation("posts")),
        ]
        args.forms_media_settings = write_json(root / "forms-media-settings.json", forms_media_settings())
        args.launch_acceptance = write_json(root / "launch.json", launch_acceptance())
        report = summarize(args)
        assert report["complete"] is True, report
        assert report["currentStage"] == "complete"
        assert report["contentGoalCoverage"]["checks"]["products"] is True
        assert report["contentGoalCoverage"]["checks"]["posts"] is True


def test_status_blocks_mismatched_content_goal_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        bad_review = review_packet(args.package)
        bad_review["contentGoalCoverage"] = {**content_goal_coverage(), "missing": ["posts"], "complete": False}
        args.review_packet = write_json(root / "review-packet.bad.json", bad_review)
        report = summarize(args)
        assert report["currentStage"] == "source_package", report
        assert report["stages"]["source_package"]["status"] == "blocked"
        assert any("contentGoalCoverage" in issue for issue in report["contentGoalCoverageIssues"])


def test_status_preserves_non_blocking_content_quality_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        warning_quality = {
            **content_quality_review(),
            "readyShape": False,
            "warnings": ["posts_present_without_post_categories"],
            "reviewRequired": True,
        }
        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = args.review_packet
        confirmation_data["contentQualityReview"] = warning_quality
        args.confirmation = write_json(root / "confirmation-warning.json", confirmation_data)
        review_data = review_packet(args.package)
        review_data["contentQualityReview"] = warning_quality
        args.review_packet = write_json(root / "review-packet-warning.json", review_data)
        readiness_data = artifact_readiness()
        readiness_data["contentQualityReview"] = warning_quality
        args.artifact_readiness = write_json(root / "artifacts-warning.json", readiness_data)
        plan = execution_plan()
        plan["contentQualityReview"] = warning_quality
        args.execution_plan = write_json(root / "plan-warning.json", plan)
        report = summarize(args)
        assert report["currentStage"] == "create_site_handoff", report
        assert report["contentQualityReview"] == warning_quality
        assert report["contentQualityReview"]["reviewRequired"] is True


def test_status_blocks_mismatched_confirmation_decision_matrix() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        warning_quality = {
            **content_quality_review(),
            "readyShape": False,
            "warnings": ["posts_present_without_post_categories"],
            "reviewRequired": True,
        }
        confirmation_data = confirmation()
        confirmation_data["contentQualityReview"] = warning_quality
        args.confirmation = write_json(root / "confirmation-warning.json", confirmation_data)
        review_data = review_packet(args.package)
        review_data["contentQualityReview"] = warning_quality
        args.review_packet = write_json(root / "review-packet-warning.json", review_data)
        readiness_data = artifact_readiness()
        readiness_data["contentQualityReview"] = warning_quality
        args.artifact_readiness = write_json(root / "artifacts-warning.json", readiness_data)
        bad_plan = execution_plan()
        bad_plan["contentQualityReview"] = warning_quality
        bad_plan["confirmationDecisionMatrix"] = [
            {**confirmation_decision_matrix()[0], "decision": "defer", "deferDecision": "changed"}
        ]
        args.execution_plan = write_json(root / "plan-bad-matrix.json", bad_plan)
        report = summarize(args)
        assert report["currentStage"] == "source_package", report
        assert report["stages"]["source_package"]["status"] == "blocked"
        assert any("confirmationDecisionMatrix" in issue for issue in report["confirmationDecisionMatrixIssues"])
        assert "posts_present_without_post_categories" in report["contentQualityReview"]["warnings"]
        assert report["contentQualityReviewIssues"] == []


def test_launch_acceptance_requires_valid_and_complete() -> None:
    cases = (
        (
            {
                "kind": "allincms_launch_acceptance_validation",
                "valid": True,
                "complete": False,
                "createdSiteSubmittedValues": created_site_submitted_values(),
            },
            "launch acceptance complete is not true",
        ),
        (
            {
                "kind": "allincms_launch_acceptance_validation",
                "valid": False,
                "complete": True,
                "createdSiteSubmittedValues": created_site_submitted_values(),
            },
            "launch acceptance valid is not true",
        ),
    )
    for launch_data, expected_blocker in cases:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = base_args(root)
            fill_base(root, args)
            args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
            args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
            args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
            args.created_site_binding = write_json(root / "binding.json", created_site_binding())
            args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
            args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
            args.sample_evidence = [
                write_json(root / "products-sample.json", sample_evidence("products")),
                write_json(root / "posts-sample.json", sample_evidence("posts")),
            ]
            args.batch_validation = [
                write_json(root / "products-batch-validation.json", batch_validation("products")),
                write_json(root / "posts-batch-validation.json", batch_validation("posts")),
            ]
            args.forms_media_settings = write_json(root / "forms-media-settings.json", forms_media_settings())
            args.launch_acceptance = write_json(root / "launch.json", launch_data)
            report = summarize(args)
            assert report["complete"] is False, report
            assert report["currentStage"] == "launch_acceptance"
            assert report["stages"]["launch_acceptance"]["status"] == "blocked"
            assert expected_blocker in report["stages"]["launch_acceptance"]["blockers"]


def test_status_blocks_single_content_type_sample_when_products_and_posts_exported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [write_json(root / "products-sample.json", sample_evidence("products"))]
        report = summarize(args)
        assert report["currentStage"] == "sample_upload", report
        assert report["requiredContentTypes"] == ["posts", "products"]
        assert report["contentTypeCoverage"]["sampleEvidence"] == ["products"]
        assert "sample evidence missing required content types: posts" in report["stages"]["sample_upload"]["blockers"]


def test_status_blocks_single_content_type_batch_when_products_and_posts_exported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.created_site_binding = write_json(root / "binding.json", created_site_binding())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        args.batch_validation = [write_json(root / "products-batch-validation.json", batch_validation("products"))]
        report = summarize(args)
        assert report["currentStage"] == "batch_upload", report
        assert report["contentTypeCoverage"]["batchValidation"] == ["products"]
        assert "batch validation missing required content types: posts" in report["stages"]["batch_upload"]["blockers"]


def test_status_blocks_page_count_shortfall_before_schema_capture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)

        coverage = content_goal_coverage()
        coverage["counts"] = {**coverage["counts"], "pages": 2}
        package_data = json.loads(Path(args.package).read_text(encoding="utf-8"))
        package_data["contentGoalCoverage"] = coverage
        package_data["contentPlan"]["pages"].append({"title": "About", "path": "/about"})
        args.package = write_json(root / "package-two-pages.json", package_data)

        review_data = review_packet(args.package)
        review_data["contentGoalCoverage"] = coverage
        args.review_packet = write_json(root / "review-packet-two-pages.json", review_data)

        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = args.review_packet
        confirmation_data["contentGoalCoverage"] = coverage
        args.confirmation = write_json(root / "confirmation-two-pages.json", confirmation_data)

        for path_key in ("execution_plan", "artifact_readiness"):
            data = json.loads(Path(getattr(args, path_key)).read_text(encoding="utf-8"))
            data["contentGoalCoverage"] = coverage
            setattr(args, path_key, write_json(root / f"{path_key}-two-pages.json", data))

        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", {**created_site_binding(), "contentGoalCoverage": coverage})
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        report = summarize(args)
        assert report["currentStage"] == "pages_site_info_execution", report
        assert report["contentCountCoverage"]["pages"] == 2
        assert "pages/site-info pageCount 1 is lower than confirmed plan count 2" in report["stages"]["pages_site_info_execution"]["blockers"]


def test_status_blocks_batch_count_shortfall_before_forms_media_settings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        fill_base(root, args)

        coverage = content_goal_coverage()
        coverage["counts"] = {**coverage["counts"], "products": 2, "productManifestItems": 2}
        package_data = json.loads(Path(args.package).read_text(encoding="utf-8"))
        package_data["contentGoalCoverage"] = coverage
        package_data["contentPlan"]["products"].append({"name": "Second Product", "slug": "second-product"})
        package_data["manifests"]["products"]["items"].append({"slug": "second-product"})
        args.package = write_json(root / "package-two-products.json", package_data)

        review_data = review_packet(args.package)
        review_data["contentGoalCoverage"] = coverage
        args.review_packet = write_json(root / "review-packet-two-products.json", review_data)

        confirmation_data = confirmation()
        confirmation_data["sourceReviewPacket"] = args.review_packet
        confirmation_data["contentGoalCoverage"] = coverage
        args.confirmation = write_json(root / "confirmation-two-products.json", confirmation_data)

        plan_data = json.loads(Path(args.execution_plan).read_text(encoding="utf-8"))
        plan_data["contentGoalCoverage"] = coverage
        args.execution_plan = write_json(root / "execution-plan-two-products.json", plan_data)

        readiness_data = json.loads(Path(args.artifact_readiness).read_text(encoding="utf-8"))
        readiness_data["contentGoalCoverage"] = coverage
        readiness_data["draftManifestStatus"]["products"]["itemCount"] = 2
        args.artifact_readiness = write_json(root / "artifact-readiness-two-products.json", readiness_data)

        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        args.created_site_binding = write_json(root / "binding.json", {**created_site_binding(), "contentGoalCoverage": coverage})
        args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
        args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
        args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
        args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
        args.sample_evidence = [
            write_json(root / "products-sample.json", sample_evidence("products")),
            write_json(root / "posts-sample.json", sample_evidence("posts")),
        ]
        args.batch_validation = [
            write_json(root / "products-batch-validation.json", batch_validation("products")),
            write_json(root / "posts-batch-validation.json", batch_validation("posts")),
        ]
        report = summarize(args)
        assert report["currentStage"] == "batch_upload", report
        assert report["contentCountCoverage"]["products"] == 2
        assert "batch validation products count 1 is lower than confirmed plan count 2" in report["stages"]["batch_upload"]["blockers"]
def review_objective_coverage(review_packet_path: str, package_path: str) -> dict:
    return {
        "kind": "allincms_source_review_objective_coverage",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "remoteMutationAllowed": False,
        "reviewPacket": review_packet_path,
        "sourcePackage": package_path,
        "reviewComplete": True,
        "complete": False,
        "missingForReview": [],
        "missingForFinal": [
            "user_confirmation_needed",
            "remote_site_creation_not_started",
            "schema_capture_not_started",
            "sample_batch_upload_not_started",
            "final_launch_not_started",
        ],
    }


def _fill_base_with_coverage(root: Path, args: argparse.Namespace, plan_coverage: dict | None = None) -> dict:
    args.package = write_json(root / "package.json", package())
    args.review_packet = write_json(root / "review-packet.json", review_packet(args.package))
    coverage = review_objective_coverage(args.review_packet, args.package)
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = args.review_packet
    confirmation_data["sourceReviewObjectiveCoverage"] = coverage
    args.confirmation = write_json(root / "confirmation.json", confirmation_data)
    plan = execution_plan()
    plan["sourceReviewObjectiveCoverage"] = plan_coverage if plan_coverage is not None else coverage
    args.execution_plan = write_json(root / "plan.json", plan)
    readiness = artifact_readiness()
    readiness["sourceReviewObjectiveCoverage"] = coverage
    args.artifact_readiness = write_json(root / "artifacts.json", readiness)
    return coverage


def test_status_exposes_source_review_objective_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        coverage = _fill_base_with_coverage(root, args)
        report = summarize(args)
        assert report["sourceReviewObjectiveCoverageIssues"] == []
        assert report["sourceReviewObjectiveCoverage"] == coverage
        assert report["currentStage"] == "create_site_handoff", report


def test_status_blocks_source_review_objective_coverage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        coverage = _fill_base_with_coverage(root, args, plan_coverage=None)
        # Rewrite the plan so its carried coverage claims the full objective is done.
        plan = execution_plan()
        plan["sourceReviewObjectiveCoverage"] = {**coverage, "complete": True}
        args.execution_plan = write_json(root / "plan.json", plan)
        report = summarize(args)
        assert report["currentStage"] == "source_package", report
        assert report["stages"]["source_package"]["status"] == "blocked"
        assert any("sourceReviewObjectiveCoverage" in issue for issue in report["sourceReviewObjectiveCoverageIssues"])


def test_status_blocks_source_review_objective_coverage_silent_drop() -> None:
    # Confirmation carries coverage but the plan and readiness silently drop it.
    # The status summarizer (the whole-chain drift monitor) must catch this, not
    # only the export helper.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        _fill_base_with_coverage(root, args)
        args.execution_plan = write_json(root / "plan.json", execution_plan())  # no coverage
        args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness())  # no coverage
        report = summarize(args)
        assert report["currentStage"] == "source_package", report
        assert report["stages"]["source_package"]["status"] == "blocked"
        issues = report["sourceReviewObjectiveCoverageIssues"]
        assert any("execution plan: sourceReviewObjectiveCoverage is required when present" in i for i in issues), issues
        assert any("artifact readiness: sourceReviewObjectiveCoverage is required when present" in i for i in issues), issues


def test_status_tolerates_review_objective_coverage_generated_at_difference() -> None:
    # Two copies of the same carried coverage that differ ONLY in generatedAt are
    # semantically identical and must NOT be reported as drift.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        coverage = _fill_base_with_coverage(root, args)
        plan = execution_plan()
        plan["sourceReviewObjectiveCoverage"] = {**coverage, "generatedAt": "2099-01-01T00:00:00+00:00"}
        args.execution_plan = write_json(root / "plan.json", plan)
        report = summarize(args)
        assert report["sourceReviewObjectiveCoverageIssues"] == [], report["sourceReviewObjectiveCoverageIssues"]
        assert report["currentStage"] == "create_site_handoff", report


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source execution status regression tests passed.")
