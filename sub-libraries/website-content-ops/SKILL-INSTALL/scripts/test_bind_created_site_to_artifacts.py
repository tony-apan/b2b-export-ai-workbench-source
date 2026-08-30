#!/usr/bin/env python3
"""Regression tests for binding created-site identity into exported artifacts."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from bind_created_site_to_artifacts import build_binding, validate_binding
from export_confirmed_site_artifacts import build_artifacts
from make_source_package_confirmation import build_confirmation
from make_source_package_review_packet import build_review_packet
from build_confirmed_site_execution_plan import build_plan
from make_create_preflight_evidence import build_evidence, parse_observed_fields
from make_created_site_evidence import upgrade_evidence
from make_existing_site_readonly_evidence import build_evidence as build_existing_site_evidence
from test_export_confirmed_site_artifacts import prepare_confirmed_plan


SITE_KEY = "newsite123"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def module_routes(site_key: str) -> list[str]:
    return [
        f"/{site_key}/dashboard",
        f"/{site_key}/products",
        f"/{site_key}/posts",
        f"/{site_key}/media",
        f"/{site_key}/themes",
        f"/{site_key}/routes",
        f"/{site_key}/forms",
        f"/{site_key}/site-info",
        f"/{site_key}/tracking",
        f"/{site_key}/domains",
    ]


def created_site_evidence(root: Path) -> Path:
    preflight = build_evidence(
        ["oldsite123"],
        parse_observed_fields(
            "observed create site entry button 创建站点;observed dialog title 创建站点;"
            "name input;description textarea;submit 创建;close Close"
        ),
        dialog_closed_verified=True,
        repo_check_passed=True,
        repo_check_note=None,
        generated_at="2026-07-01T00:00:00+00:00",
        site_key_evidence={"oldsite123": "backend URL https://workspace.laicms.com/oldsite123/dashboard"},
    )
    evidence = upgrade_evidence(
        preflight,
        created_site_key=SITE_KEY,
        content_type="products",
        list_columns=["名称", "Slug", "状态"],
        edit_fields=["名称", "Slug", "描述", "更新"],
        site_card_evidence=f"site card href https://workspace.laicms.com/{SITE_KEY}/dashboard",
        backend_evidence=f"backend URL https://workspace.laicms.com/{SITE_KEY}/dashboard loaded",
        frontend_evidence=f"frontend URL https://{SITE_KEY}.web.allincms.com loaded",
        site_info_evidence="site-info settings page controls visible",
        domains_evidence="domains page controls visible",
        media_evidence="media page controls visible",
        themes_evidence="themes page controls visible",
        routes_evidence="routes page controls visible",
        forms_evidence="forms page controls visible",
        tracking_evidence="tracking page controls visible",
        module_routes=module_routes(SITE_KEY),
        submitted_fields=["name", "description"],
        submitted_values={
            "name": "Example Demo",
            "description": "Example demo site for source-backed product publishing and article planning.",
        },
        authorization_source="授权 Codex 在 https://workspace.laicms.com/sites 创建站点，站点名称为 Example Demo。",
        repo_check_passed=True,
        repo_check_note=None,
        generated_at="2026-07-01T00:05:00+00:00",
    )
    path = root / "created-site-evidence.json"
    write_json(path, evidence)
    return path


def existing_site_evidence(root: Path) -> Path:
    evidence = build_existing_site_evidence(
        argparse.Namespace(
            site_key=SITE_KEY,
            existing_site_keys=f"oldsite123,{SITE_KEY}",
            observed_create_fields="name input,description textarea,submit 创建,close Close",
            dialog_closed_verified=True,
            module_routes=",".join(module_routes(SITE_KEY)),
            content_type="products",
            list_columns="名称,Slug,状态",
            edit_fields="名称,Slug,描述,更新",
            site_info_evidence="site-info settings page controls visible",
            domains_evidence="domains page controls visible",
            media_evidence="media page controls visible",
        themes_evidence="themes page controls visible",
            routes_evidence="routes page controls visible",
            forms_evidence="forms page controls visible",
            tracking_evidence="tracking page controls visible",
            cleanup_status="not_needed",
            cleanup_candidates="",
            frontend_rendering_evidence="",
            launch_readiness_evidence="",
            frontend_route_patterns="/,/products,/posts",
            markdown_residue_checked=True,
            structured_rich_text_checked=True,
            frontend_blocking_issues="",
            repo_check_passed=True,
            repo_check_note=None,
        )
    )
    path = root / "existing-site-readonly-evidence.json"
    write_json(path, evidence)
    return path


def test_bind_created_site_to_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        binding = build_binding(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "bound-artifacts"),
                output=str(root / "binding.json"),
                json=False,
            )
        )
        assert not validate_binding(binding)
        assert binding["siteBindingMode"] == "created_site"
        assert binding["siteCreationStatus"] == "created_verified"
        assert binding["createdSiteSubmittedValues"] == {
            "name": "Example Demo",
            "description": "Example demo site for source-backed product publishing and article planning.",
        }
        assert binding["contentGoalCoverage"]["complete"] is True
        assert binding["contentGoalCoverage"]["checks"]["siteInfo"] is True
        assert binding["contentCounts"] == readiness["contentCounts"]
        assert binding["contentCounts"]["navigationItems"] == 3
        assert binding["contentCounts"]["siteInfoFields"] >= 1
        assert binding["contentQualityReview"]["reviewRequired"] is False
        assert binding["contentQualityReview"]["warnings"] == []
        assert binding["wikiReview"] == readiness["wikiReview"]
        assert binding["confirmationDecisionMatrix"] == readiness["confirmationDecisionMatrix"]
        assert binding["sourcePackageSha256"] == readiness["sourcePackageSha256"]
        assert binding["sourceReviewPacketSha256"] == readiness["sourceReviewPacketSha256"]
        assert Path(binding["wikiReview"]["sourceWikiMarkdownIndex"]).exists()
        bound_readiness = json.loads(Path(binding["boundArtifacts"]["artifactReadiness"]).read_text(encoding="utf-8"))
        assert bound_readiness["contentGoalCoverage"] == binding["contentGoalCoverage"]
        assert bound_readiness["contentCounts"] == binding["contentCounts"]
        assert bound_readiness["contentQualityReview"] == binding["contentQualityReview"]
        assert bound_readiness["wikiReview"] == binding["wikiReview"]
        assert bound_readiness["confirmationDecisionMatrix"] == binding["confirmationDecisionMatrix"]
        assert bound_readiness["sourcePackageSha256"] == binding["sourcePackageSha256"]
        assert bound_readiness["sourceReviewPacketSha256"] == binding["sourceReviewPacketSha256"]
        assert bound_readiness["createdSiteSubmittedValues"] == binding["createdSiteSubmittedValues"]
        assert bound_readiness["createdSiteBinding"]["submittedValues"] == binding["createdSiteSubmittedValues"]
        products = json.loads(Path(binding["boundArtifacts"]["productsManifest"]).read_text(encoding="utf-8"))
        posts = json.loads(Path(binding["boundArtifacts"]["postsManifest"]).read_text(encoding="utf-8"))
        assert products["siteKey"] == SITE_KEY
        assert posts["siteKey"] == SITE_KEY
        assert products["frontendBaseUrl"] == f"https://{SITE_KEY}.web.allincms.com"
        assert products["schemaVerified"] is False
        assert products["contentGoalCoverage"] == binding["contentGoalCoverage"]
        assert products["contentCounts"] == binding["contentCounts"]
        assert products["sourcePackageSha256"] == binding["sourcePackageSha256"]
        assert products["sourceReviewPacketSha256"] == binding["sourceReviewPacketSha256"]
        assert posts["contentGoalCoverage"] == binding["contentGoalCoverage"]
        assert posts["contentCounts"] == binding["contentCounts"]
        assert posts["sourcePackageSha256"] == binding["sourcePackageSha256"]
        assert products["createdSiteBinding"]["schemaCaptureStillRequired"] is True


def test_bind_selected_existing_site_to_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = existing_site_evidence(root)
        binding = build_binding(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "bound-existing-artifacts"),
                output=str(root / "binding.json"),
                json=False,
            )
        )
        assert not validate_binding(binding)
        assert binding["siteBindingMode"] == "existing_site"
        assert binding["siteCreationStatus"] == "existing_site_selected"
        assert "createdSiteSubmittedValues" not in binding
        assert "not be used as proof for a from-scratch site-creation objective" in " ".join(binding["adversarialChecks"])
        bound_readiness = json.loads(Path(binding["boundArtifacts"]["artifactReadiness"]).read_text(encoding="utf-8"))
        assert bound_readiness["siteBindingMode"] == "existing_site"
        products = json.loads(Path(binding["boundArtifacts"]["productsManifest"]).read_text(encoding="utf-8"))
        assert products["siteKey"] == SITE_KEY
        assert products["schemaVerified"] is False


def test_bind_created_site_rejects_missing_coverage_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness["contentGoalCoverage"]["counts"].pop("posts")
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        try:
            build_binding(
                argparse.Namespace(
                    artifact_readiness=str(readiness_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "bound-artifacts"),
                    output=str(root / "binding.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "contentGoalCoverage.counts.posts" in str(exc)
        else:
            raise AssertionError("missing posts count should block created-site binding")


def test_bind_created_site_rejects_missing_extended_content_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness["contentCounts"].pop("navigationItems")
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        try:
            build_binding(
                argparse.Namespace(
                    artifact_readiness=str(readiness_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "bound-artifacts"),
                    output=str(root / "binding.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "contentCounts.navigationItems" in str(exc)
        else:
            raise AssertionError("missing navigationItems content count should block created-site binding")


def test_bind_created_site_rejects_missing_submitted_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["siteCreation"].pop("submittedValues")
        write_json(evidence_path, evidence)
        try:
            build_binding(
                argparse.Namespace(
                    artifact_readiness=str(readiness_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "bound-artifacts"),
                    output=str(root / "binding.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "siteCreation.submittedValues" in str(exc)
        else:
            raise AssertionError("missing submittedValues should block new-site artifact binding")


def test_bind_created_site_rejects_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["siteCreation"]["submittedValues"]["name"] = "Wrong Demo"
        write_json(evidence_path, evidence)
        try:
            build_binding(
                argparse.Namespace(
                    artifact_readiness=str(readiness_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "bound-artifacts"),
                    output=str(root / "binding.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "submittedValues.name" in str(exc)
            assert "siteProposal.siteName" in str(exc)
        else:
            raise AssertionError("submitted name drift should block new-site artifact binding")


def test_bind_created_site_preserves_content_quality_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["contentPlan"]["taxonomyPlan"]["postCategoryCount"] = 0
        package["contentPlan"]["taxonomyPlan"]["postCategories"] = []
        write_json(package_path, package)
        review_packet = build_review_packet(package, str(package_path), generated_at="2026-07-01T00:00:00+00:00")
        review_packet_path = root / "source-package-review-packet.json"
        write_json(review_packet_path, review_packet)
        confirmation = build_confirmation(
            argparse.Namespace(
                package=str(package_path),
                review_packet=str(review_packet_path),
                user_confirmation_text="User confirms the generated package after reviewing quality warnings.",
                accepted_fields="",
                accepted_deferral=[
                    "siteInfo.publicContact|defer_until_real_company_details|Public contact channels are not available in the demo source files.",
                    "siteInfo.legalCompanyName|defer_until_real_company_details|Legal company name is not available in the demo source files.",
                    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                    "tracking.trackingCode|out_of_scope_for_demo|No analytics or tracking code is needed for this demo.",
                ],
                notes="warning propagation test",
                output=str(root / "confirmation.json"),
                json=False,
            )
        )
        write_json(confirmation_path, confirmation)
        plan = build_plan(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                target_mode="new_site",
                site_key="",
                output=str(root / "execution-plan.json"),
                json=False,
            )
        )
        write_json(plan_path, plan)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        binding = build_binding(
            argparse.Namespace(
                artifact_readiness=str(readiness_path),
                created_site_evidence=str(evidence_path),
                output_dir=str(root / "bound-artifacts"),
                output=str(root / "binding.json"),
                json=False,
            )
        )
        assert not validate_binding(binding)
        assert binding["contentQualityReview"] == review_packet["contentQualityReview"]
        assert binding["contentQualityReview"]["reviewRequired"] is True
        assert "posts_present_without_post_categories" in binding["contentQualityReview"]["warnings"]
        assert binding["wikiReview"] == review_packet["wikiReview"]
        assert binding["confirmationDecisionMatrix"] == confirmation["confirmationDecisionMatrix"]
        bound_readiness = json.loads(Path(binding["boundArtifacts"]["artifactReadiness"]).read_text(encoding="utf-8"))
        assert bound_readiness["contentQualityReview"] == binding["contentQualityReview"]
        assert bound_readiness["wikiReview"] == binding["wikiReview"]
        assert bound_readiness["confirmationDecisionMatrix"] == binding["confirmationDecisionMatrix"]


def test_bind_created_site_rejects_missing_wiki_index() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="",
                frontend_base_url="",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        Path(readiness["wikiReview"]["sourceWikiMarkdownIndex"]).unlink()
        readiness_path = root / "artifacts" / "artifact-readiness.json"
        write_json(readiness_path, readiness)
        evidence_path = created_site_evidence(root)
        try:
            build_binding(
                argparse.Namespace(
                    artifact_readiness=str(readiness_path),
                    created_site_evidence=str(evidence_path),
                    output_dir=str(root / "bound-artifacts"),
                    output=str(root / "binding.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "wikiReview" in str(exc)
        else:
            raise AssertionError("missing readable wiki index should block created-site binding")


if __name__ == "__main__":
    test_bind_created_site_to_artifacts()
    test_bind_selected_existing_site_to_artifacts()
    test_bind_created_site_rejects_missing_coverage_count()
    test_bind_created_site_rejects_missing_extended_content_counts()
    test_bind_created_site_rejects_missing_submitted_values()
    test_bind_created_site_rejects_submitted_value_drift()
    test_bind_created_site_preserves_content_quality_warning()
    test_bind_created_site_rejects_missing_wiki_index()
    print("created-site artifact binding regression tests passed.")
