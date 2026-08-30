#!/usr/bin/env python3
"""Regression tests for source next-stage handoff preparation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_source_next_stage import build_handoff, validate_handoff
from test_summarize_source_execution_status import (
    artifact_readiness,
    artifact_readiness_with_taxonomy_plan,
    base_args as status_base_args,
    batch_validation,
    create_site_handoff,
    created_site_binding,
    fill_base,
    content_quality_review,
    confirmation,
    execution_plan,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    sample_evidence,
    schema_capture_handoff,
    summarize,
    taxonomy_handoff,
    upload_readiness,
    write_json,
    forms_media_settings,
)
from test_source_confirmation_execution_plan import make_package
from make_source_package_review_packet import build_review_packet


SCRIPT = Path(__file__).resolve().parent / "prepare_source_next_stage.py"


def write_status(root: Path, status: dict) -> str:
    return write_json(root / "source-execution-status.json", status)


def handoff_args(root: Path, status_path: str, **overrides: str) -> argparse.Namespace:
    values = {
        "status": status_path,
        "output": str(root / "next-stage-handoff.json"),
        "output_dir": str(root / "next-stage-output"),
        "created_site_evidence": "",
        "create_preflight_source_apply_result": "",
        "created_site_evidence_bundle": "",
        "filled_created_site_evidence_template": "",
        "default_theme_bootstrap_runbook": "",
        "default_theme_bootstrap_evidence": "",
        "source_wiki": "",
        "inventory": "",
        "requirements": "",
        "user_confirmation_text": "",
        "target_mode": "new_site",
        "accepted_fields": "",
        "accepted_deferral": [],
        "notes": "",
        "create_preflight": "",
        "create_authorization_output": "",
        "pages_site_info_evidence": "",
        "pages_site_info_evidence_bundle": "",
        "taxonomy_evidence": "",
        "taxonomy_evidence_bundle": "",
        "manifest": "",
        "save_capture_evidence": "",
        "base_run_evidence": "",
        "sample_evidence": "",
        "sample_evidence_bundle": "",
        "existing_sample_evidence": [],
        "batch_evidence": "",
        "batch_evidence_bundle": "",
        "existing_batch_validation": [],
        "existing_upload_readiness": [],
        "frontend_audit_report": "",
        "forms_media_settings_evidence": "",
        "forms_media_settings_evidence_bundle": "",
        "launch_acceptance_inputs_bundle": "",
        "launch_evidence": "",
        "run_evidence": "",
        "module_coverage": "",
        "stage_coverage": "",
        "final_frontend_audit": "",
        "cleanup_evidence": "",
        "round_closeout": "",
        "authorization_dir": "",
        "theme_target": "",
        "site_key": "",
        "frontend_base_url": "",
        "target": "",
        "sample_slug": "",
        "json": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def status_at_created_site_binding(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    return summarize(args)


def status_at_confirmation(root: Path) -> dict:
    package_path = make_package(root)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    review_packet_path = root / "source-package-review-packet.json"
    review_packet = build_review_packet(
        package,
        str(package_path),
        generated_at="2026-07-01T00:00:00+00:00",
        review_packet_path=str(review_packet_path),
    )
    write_json(review_packet_path, review_packet)
    args = status_base_args(root)
    args.package = str(package_path)
    args.review_packet = str(review_packet_path)
    return summarize(args)


def status_at_execution_plan(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.execution_plan = ""
    args.artifact_readiness = ""
    return summarize(args)


def status_at_artifact_export(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.artifact_readiness = ""
    return summarize(args)


def status_at_review_packet(root: Path) -> dict:
    args = status_base_args(root)
    args.package = write_json(root / "package.json", package())
    return summarize(args)


def status_at_pages_execution(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    return summarize(args)


def status_at_pages_site_info_handoff(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    return summarize(args)


def status_at_taxonomy_handoff(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness_with_taxonomy_plan(root))
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    return summarize(args)


def status_with_taxonomy_handoff(root: Path, *, blocked_preflight: bool = False) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness_with_taxonomy_plan(root))
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    handoff = taxonomy_handoff()
    handoff["siteKey"] = "demo123"
    if blocked_preflight:
        handoff["readyForBrowserStage"] = "blocked_taxonomy_preflight"
        handoff["preflightIssues"] = ["preflight.setupPages.products", "preflight.setupPages.posts"]
    args.taxonomy_handoff = write_json(root / "taxonomy-handoff.json", handoff)
    return summarize(args)


def status_at_taxonomy_execution(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.artifact_readiness = write_json(root / "artifacts.json", artifact_readiness_with_taxonomy_plan(root))
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    handoff = taxonomy_handoff()
    handoff["siteKey"] = "demo123"
    args.taxonomy_handoff = write_json(root / "taxonomy-handoff.json", handoff)
    return summarize(args)


def status_at_schema_manifests(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
    return summarize(args)


def status_at_batch_upload(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
    args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
    args.sample_evidence = [
        write_json(root / "products-sample.json", sample_evidence("products")),
        write_json(root / "posts-sample.json", sample_evidence("posts")),
    ]
    return summarize(args)


def status_at_sample_upload_with_existing_sample(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
    args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
    args.sample_evidence = [write_json(root / "products-sample.json", sample_evidence("products"))]
    return summarize(args)


def status_at_batch_upload_with_existing_batch_validation(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
    args.pages_site_info_handoff = write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff())
    args.pages_site_info_validation = write_json(root / "pages-site-info-validation.json", pages_site_info_validation())
    args.schema_capture_handoff = write_json(root / "schema-capture-handoff.json", schema_capture_handoff())
    args.upload_readiness = write_json(root / "upload-readiness.json", upload_readiness())
    args.sample_evidence = [
        write_json(root / "products-sample.json", sample_evidence("products")),
        write_json(root / "posts-sample.json", sample_evidence("posts")),
    ]
    args.batch_validation = [write_json(root / "products-batch-validation.json", batch_validation("products"))]
    return summarize(args)


def status_at_forms_media_settings(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
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
    return summarize(args)


def status_at_launch_acceptance(root: Path) -> dict:
    args = status_base_args(root)
    fill_base(root, args)
    args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
    args.created_site_binding = write_json(root / "binding.json", created_site_binding())
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
    args.forms_media_settings = write_json(root / "forms-media-settings.json", forms_media_settings())
    return summarize(args)


def test_created_site_binding_handoff_contains_prepare_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_created_site_binding(root))
        handoff = build_handoff(handoff_args(root, status_path, created_site_evidence=str(root / "created-site.json")))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "created_site_binding"
        assert "prepare_created_site_schema_capture.py" in handoff["localCommand"]
        assert "--created-site-evidence" in handoff["localCommand"]
        assert "created-site.json" in handoff["localCommand"]


def test_created_site_binding_handoff_can_apply_evidence_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_created_site_binding(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                created_site_evidence_bundle=str(root / "created-site-evidence-bundle" / "evidence-bundle.json"),
                filled_created_site_evidence_template=str(root / "created-site-evidence-bundle" / "created-site-evidence.filled-template.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "created_site_binding"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_created_site_evidence_bundle.py" in handoff["localCommand"]
        assert "--bundle" in handoff["localCommand"]
        assert "--filled-template" in handoff["localCommand"]
        assert "--prepare-created-site-schema-capture" in handoff["localCommand"]
        assert "--artifact-readiness" in handoff["localCommand"]
        assert "--confirmation" in handoff["localCommand"]
        assert "created-site-evidence.filled-template.json" in handoff["localCommand"]
        assert "filled created-site evidence bundle" in " ".join(handoff["requiredInputs"])
        assert "apply the bundle" in " ".join(handoff["adversarialChecks"])


def test_created_site_binding_handoff_prefers_source_rehearsal_apply() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_created_site_binding(root))
        source_apply = root / "create-preflight-source-rehearsal-apply.json"
        source_apply.write_text('{"kind":"allincms_create_preflight_source_rehearsal_apply"}\n', encoding="utf-8")
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                create_preflight_source_apply_result=str(source_apply),
                created_site_evidence_bundle=str(root / "created-site-evidence-bundle" / "evidence-bundle.json"),
                filled_created_site_evidence_template=str(root / "created-site-evidence-bundle" / "created-site-evidence.filled-template.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "created_site_binding"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_created_site_evidence_to_source_rehearsal.py" in handoff["localCommand"]
        assert "--source-apply-result" in handoff["localCommand"]
        assert "--filled-created-site-evidence-template" in handoff["localCommand"]
        assert "--created-site-evidence-bundle" in handoff["localCommand"]
        assert "apply_created_site_evidence_bundle.py" not in handoff["localCommand"]


def test_created_site_binding_without_evidence_remains_browser_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_created_site_binding(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "created_site_binding"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert "created-site evidence" in " ".join(handoff["requiredInputs"])
        assert "do not run schema-capture preparation" in " ".join(handoff["forbiddenActions"])


def test_confirmation_without_user_text_requires_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_confirmation(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "confirmation"
        assert handoff["mode"] == "user_confirmation_required"
        assert handoff["browserWorkRequired"] is False
        assert handoff["localCommand"] == ""
        assert "user content-intent confirmation text" in " ".join(handoff["requiredInputs"])


def test_review_packet_stage_emits_refined_source_wiki_apply_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_review_packet(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                source_wiki=str(root / "source-wiki.refined.json"),
                inventory=str(root / "source-index.json"),
                requirements=str(root / "source-input-requirements.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "review_packet"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_refined_source_wiki.py" in handoff["localCommand"]
        assert "source-wiki.refined.json" in handoff["localCommand"]
        assert "--inventory" in handoff["localCommand"]
        assert "--requirements" in handoff["localCommand"]


def test_confirmation_with_user_text_emits_prepare_confirmed_execution_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_confirmation(root))
        review_packet_path = root / "source-package-review-packet.json"
        expected_execution_dir = root / "confirmed-execution"
        expected_action_gate = root / "create-site-action-gate.json"
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                user_confirmation_text="User confirms the source package content intent for a temporary demo site.",
                accepted_deferral=[
                    "siteInfo.publicContact|defer_until_real_company_details|No public contact was supplied in source files.",
                    "siteInfo.legalCompanyName|defer_until_real_company_details|No legal company name was supplied in source files.",
                    "domains.customDomain|out_of_scope_for_demo|No custom domain is needed for this demo.",
                    "tracking.trackingCode|out_of_scope_for_demo|No tracking code is needed for this demo.",
                ],
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "confirmation"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert "prepare_confirmed_site_execution.py" in handoff["localCommand"]
        assert "--user-confirmation-text" in handoff["localCommand"]
        assert "--review-packet" in handoff["localCommand"]
        assert "--accepted-deferral" in handoff["localCommand"]
        assert str(review_packet_path) in handoff["localCommand"]
        assert f"--output-dir {expected_execution_dir}" in handoff["localCommand"]
        assert f"--create-authorization-output {expected_action_gate}" in handoff["localCommand"]
        assert "--create-action-gate-output" not in handoff["localCommand"]
        assert "next-stage-output/confirmed-site-execution" not in handoff["localCommand"]


def test_next_stage_handoff_preserves_content_quality_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = status_base_args(root)
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
        review_data = {
            "kind": "allincms_source_package_review_packet",
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "isRemoteMutationAuthorization": False,
            "sourcePackage": args.package,
            "contentGoalCoverage": artifact_readiness()["contentGoalCoverage"],
            "contentQualityReview": warning_quality,
        }
        args.review_packet = write_json(root / "review-packet-warning.json", review_data)
        readiness_data = artifact_readiness()
        readiness_data["contentQualityReview"] = warning_quality
        args.artifact_readiness = write_json(root / "artifacts-warning.json", readiness_data)
        plan = execution_plan()
        plan["contentQualityReview"] = warning_quality
        args.execution_plan = write_json(root / "plan-warning.json", plan)
        status = summarize(args)
        status_path = write_status(root, status)
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "create_site_handoff"
        assert handoff["contentQualityReview"] == warning_quality
        assert handoff["contentQualityReview"]["reviewRequired"] is True
        assert "posts_present_without_post_categories" in handoff["contentQualityReview"]["warnings"]
        assert "contentQualityReview warnings" in " ".join(handoff["adversarialChecks"])


def test_create_site_handoff_stage_without_handoff_requires_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = status_base_args(root)
        fill_base(root, args)
        status_path = write_status(root, summarize(args))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                create_authorization_output=str(root / "authorization-create-site.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "create_site_handoff"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert handoff["apiSessionPreflightRequired"] is True
        assert handoff["apiSessionPreflight"]["method"] == "GET"
        assert handoff["apiSessionPreflight"]["urlTemplate"] == "https://workspace.laicms.com/sites?_rsc={nonce}"
        assert handoff["apiSessionPreflight"]["transport"] == "in_app_browser_same_origin_cdp_fetch"
        assert handoff["apiSessionPreflight"]["visibleNavigationAllowed"] is False
        assert handoff["apiSessionPreflight"]["foregroundAllowed"] is False
        assert handoff["apiSessionPreflight"]["loginNavigationGate"] == "api_result_login_required_only"
        assert handoff["needsCreateSitePreflight"] is True
        assert "preflight" in handoff["blocker"]
        assert handoff["localCommand"] == ""
        assert "fresh workspace API session preflight" in " ".join(handoff["requiredInputs"])


def test_valid_create_site_handoff_advances_to_created_site_binding_browser_boundary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = status_base_args(root)
        fill_base(root, args)
        args.create_site_handoff = write_json(root / "create-site-handoff.json", create_site_handoff())
        status_path = write_status(root, summarize(args))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                create_authorization_output=str(root / "authorization-create-site.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "created_site_binding"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["needsCreateSitePreflight"] is False
        assert handoff["localCommand"] == ""
        assert "created-site evidence" in " ".join(handoff["requiredInputs"])
        assert "do not treat create-site handoff readiness as proof that the site was created" in " ".join(
            handoff["forbiddenActions"]
        )


def test_execution_plan_stage_emits_plan_builder_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_execution_plan(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "execution_plan"
        assert "build_confirmed_site_execution_plan.py" in handoff["localCommand"]
        assert "--package" in handoff["localCommand"]
        assert "--confirmation" in handoff["localCommand"]
        assert "--output" in handoff["localCommand"]


def test_artifact_export_stage_emits_export_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_artifact_export(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "artifact_export"
        assert "export_confirmed_site_artifacts.py" in handoff["localCommand"]
        assert "--execution-plan" in handoff["localCommand"]
        assert "--output-dir" in handoff["localCommand"]


def test_pages_site_info_handoff_stage_regenerates_created_site_handoffs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_pages_site_info_handoff(root))
        handoff = build_handoff(handoff_args(root, status_path, created_site_evidence=str(root / "created-site.json")))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "pages_site_info_handoff"
        assert "prepare_created_site_schema_capture.py" in handoff["localCommand"]
        assert "--created-site-evidence" in handoff["localCommand"]
        assert "created-site.json" in handoff["localCommand"]
        assert handoff["browserWorkRequired"] is False


def test_pages_site_info_handoff_applies_default_theme_bootstrap_before_regeneration() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_pages_site_info_handoff(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                created_site_evidence=str(root / "created-site.json"),
                default_theme_bootstrap_runbook=str(root / "default-theme-runbook.json"),
                default_theme_bootstrap_evidence=str(root / "default-theme-evidence.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "pages_site_info_handoff"
        assert "apply_default_theme_bootstrap.py" in handoff["localCommand"]
        assert "--created-site-evidence" in handoff["localCommand"]
        assert "--runbook" in handoff["localCommand"]
        assert "--bootstrap-evidence" in handoff["localCommand"]
        assert "prepare_created_site_schema_capture.py" not in handoff["localCommand"]
        assert "default-theme bootstrap evidence" in " ".join(handoff["requiredInputs"])
        assert any("default-theme bootstrap" in check for check in handoff["adversarialChecks"])


def test_taxonomy_handoff_stage_regenerates_created_site_handoffs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_taxonomy_handoff(root))
        handoff = build_handoff(handoff_args(root, status_path, created_site_evidence=str(root / "created-site.json")))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "taxonomy_execution_handoff"
        assert "prepare_created_site_schema_capture.py" in handoff["localCommand"]
        assert "--artifact-readiness" in handoff["localCommand"]
        assert "--created-site-evidence" in handoff["localCommand"]
        assert handoff["browserWorkRequired"] is False


def test_blocked_taxonomy_handoff_exposes_preflight_blocker_instead_of_regeneration_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_with_taxonomy_handoff(root, blocked_preflight=True)
        status_path = write_status(root, status)
        handoff = build_handoff(handoff_args(root, status_path, created_site_evidence=str(root / "created-site.json")))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "taxonomy_execution_handoff"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert handoff["handoffReadyForBrowserStage"] == "blocked_taxonomy_preflight"
        assert handoff["handoffPreflightIssues"] == ["preflight.setupPages.products", "preflight.setupPages.posts"]
        assert "preflight" in handoff["blocker"]
        assert "preflight.setupPages.products" in " ".join(handoff["requiredInputs"])
        assert "preflightIssues" in " ".join(handoff["adversarialChecks"])


def test_pages_site_info_handoff_contains_context_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_pages_execution(root))
        handoff = build_handoff(handoff_args(root, status_path, pages_site_info_evidence=str(root / "pages-evidence.json")))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "pages_site_info_execution"
        assert "apply_pages_site_info_execution.py" in handoff["localCommand"]
        assert "--pages-site-info-handoff" in handoff["localCommand"]
        assert "--created-site-binding" in handoff["localCommand"]
        assert "pages-evidence.json" in handoff["localCommand"]


def test_pages_site_info_execution_without_evidence_remains_browser_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_pages_execution(root)
        submitted_values = {
            "name": "Example Source Site",
            "description": "Example submitted site description.",
        }
        status["createdSiteSubmittedValues"] = submitted_values
        status_path = write_status(root, status)
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "pages_site_info_execution"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert "filled pages/site-info evidence bundle" in " ".join(handoff["requiredInputs"])
        assert handoff["createdSiteSubmittedValues"] == submitted_values


def test_cli_json_stdout_is_parseable_and_preserves_submitted_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_pages_execution(root)
        submitted_values = {
            "name": "Example Source Site",
            "description": "Example submitted site description.",
        }
        status["createdSiteSubmittedValues"] = submitted_values
        status_path = write_status(root, status)
        output_path = root / "next-stage-handoff.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--status",
                status_path,
                "--output",
                str(output_path),
                "--output-dir",
                str(root / "next-stage-output"),
                "--json",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        handoff = json.loads(result.stdout)
        assert handoff["kind"] == "allincms_source_next_stage_handoff"
        assert handoff["currentStage"] == "pages_site_info_execution"
        assert handoff["createdSiteSubmittedValues"] == submitted_values
        assert "Wrote source next-stage handoff" not in result.stdout
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["createdSiteSubmittedValues"] == submitted_values


def test_pages_site_info_execution_with_evidence_bundle_derives_apply_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_pages_execution(root))
        filled_path = write_json(
            root / "pages-site-info-evidence-bundle" / "pages-site-info-evidence.filled.json",
            {"kind": "allincms_pages_site_info_execution_evidence"},
        )
        bundle = {
            "kind": "allincms_pages_site_info_evidence_bundle",
            "handoff": str(root / "pages-site-info-handoff.json"),
            "filledEvidencePath": filled_path,
        }
        bundle_path = write_json(root / "pages-site-info-evidence-bundle" / "evidence-bundle.json", bundle)
        handoff = build_handoff(handoff_args(root, status_path, pages_site_info_evidence_bundle=bundle_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "pages_site_info_execution"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_pages_site_info_execution.py" in handoff["localCommand"]
        assert "pages-site-info-handoff.json" in handoff["localCommand"]
        assert "pages-site-info-evidence.filled.json" in handoff["localCommand"]
        assert "pages/site-info evidence" in " ".join(handoff["adversarialChecks"])


def test_pages_site_info_execution_rejects_stale_evidence_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_pages_execution(root))
        bundle = {
            "kind": "allincms_pages_site_info_evidence_bundle",
            "handoff": str(root / "pages-site-info-handoff.json"),
            "filledEvidencePath": str(root / "pages-site-info-evidence-bundle" / "pages-site-info-evidence.filled.json"),
            "sourceCurrentStage": "taxonomy_execution",
        }
        bundle_path = write_json(root / "pages-site-info-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, pages_site_info_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "pages/site-info evidence bundle was generated for sourceCurrentStage=taxonomy_execution" in str(exc)
        else:
            raise AssertionError("stale pages/site-info evidence bundle should not produce an apply command")


def test_taxonomy_execution_without_evidence_remains_browser_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_taxonomy_execution(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "taxonomy_execution"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert "filled taxonomy evidence bundle" in " ".join(handoff["requiredInputs"])


def test_taxonomy_execution_with_evidence_bundle_derives_apply_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_taxonomy_execution(root))
        filled_path = write_json(
            root / "taxonomy-evidence-bundle" / "taxonomy-execution-evidence.filled.json",
            {"kind": "allincms_taxonomy_execution_evidence"},
        )
        bundle = {
            "kind": "allincms_taxonomy_evidence_bundle",
            "handoff": str(root / "taxonomy-handoff.json"),
            "filledEvidencePath": filled_path,
        }
        bundle_path = write_json(root / "taxonomy-evidence-bundle" / "evidence-bundle.json", bundle)
        handoff = build_handoff(handoff_args(root, status_path, taxonomy_evidence_bundle=bundle_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "taxonomy_execution"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_taxonomy_execution.py" in handoff["localCommand"]
        assert "taxonomy-handoff.json" in handoff["localCommand"]
        assert "taxonomy-execution-evidence.filled.json" in handoff["localCommand"]
        assert "taxonomy evidence" in " ".join(handoff["adversarialChecks"])


def test_taxonomy_execution_rejects_blocked_evidence_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_taxonomy_execution(root))
        bundle = {
            "kind": "allincms_taxonomy_evidence_bundle",
            "handoff": str(root / "taxonomy-handoff.json"),
            "filledEvidencePath": str(root / "taxonomy-evidence-bundle" / "taxonomy-execution-evidence.filled.json"),
            "handoffReadyForBrowserStage": "blocked_taxonomy_preflight",
            "handoffPreflightIssues": ["preflight.setupPages.products"],
        }
        bundle_path = write_json(root / "taxonomy-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, taxonomy_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "taxonomy evidence bundle was generated from a blocked or stale handoff" in str(exc)
        else:
            raise AssertionError("blocked taxonomy evidence bundle should not produce an apply command")


def test_schema_manifest_handoff_keeps_placeholders_for_required_capture_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_schema_manifests(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "schema_manifests"
        assert "prepare_schema_manifest_sample.py" in handoff["localCommand"]
        assert "<draft-products-or-posts-manifest.json>" in handoff["localCommand"]
        assert "<save-capture-evidence.json>" in handoff["localCommand"]
        assert "--pages-site-info-validation" in handoff["localCommand"]


def test_blocked_schema_capture_handoff_exposes_content_preflight_blocker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        schema_handoff = schema_capture_handoff()
        posts_manifest = root / "posts.json"
        posts_manifest.write_text('{"items":[{"slug":"example-post"}]}\n', encoding="utf-8")
        schema_handoff["overallStatus"] = "needs_readonly_content_preflight"
        schema_handoff["blockedByReadonlyPreflightCount"] = 1
        schema_handoff["stages"].append(
            {
                "contentType": "posts",
                "status": "needs_readonly_content_preflight",
                "itemCount": 1,
                "manifest": str(posts_manifest),
                "contentPreflight": {
                    "readyForCreateProbeGate": False,
                    "missing": ["listColumns", "editFields"],
                },
            }
        )
        schema_handoff_path = write_json(root / "schema-capture-handoff.json", schema_handoff)
        status = {
            "kind": "allincms_source_execution_status",
            "remoteMutationsPerformed": False,
            "currentStage": "schema_capture_handoff",
            "stages": {
                "schema_capture_handoff": {
                    "status": "blocked",
                    "evidence": schema_handoff_path,
                    "blockers": ["content types need read-only preflight before create-probe gate: posts"],
                    "nextAction": "refresh content-type read-only preflight, then rebuild schema capture handoff",
                }
            },
            "sourcePackageSha256": "a" * 64,
            "sourceReviewPacketSha256": "b" * 64,
        }
        status_path = write_status(root, status)
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "schema_capture_handoff"
        assert handoff["mode"] == "browser_action_or_capture_required"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert handoff["handoffReadyForBrowserStage"] == "needs_readonly_content_preflight"
        assert handoff["handoffPreflightIssues"] == ["preflight.contentTypes.posts"]
        assert handoff["handoffBlockedContentTypes"] == ["posts"]
        assert "preflight" in handoff["blocker"]
        assert "preflight.contentTypes.posts" in " ".join(handoff["requiredInputs"])
        assert "needs_readonly_content_preflight" in " ".join(handoff["adversarialChecks"])


def test_schema_manifest_handoff_preserves_existing_upload_readiness() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_schema_manifests(root)
        status["stages"]["schema_manifests"]["evidence"] = str(root / "products-upload-readiness.json")
        status_path = write_status(root, status)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                manifest=str(root / "posts-draft-manifest.json"),
                save_capture_evidence=str(root / "posts-save-capture.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "schema_manifests"
        assert "prepare_schema_manifest_sample.py" in handoff["localCommand"]
        assert "--existing-upload-readiness" in handoff["localCommand"]
        assert "products-upload-readiness.json" in handoff["localCommand"]


def test_sample_upload_with_evidence_applies_stage_and_preserves_existing_samples() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_sample_upload_with_existing_sample(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                manifest=str(root / "posts-schema-manifest.json"),
                sample_evidence=str(root / "posts-sample.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "sample_upload"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_manifest_sample_upload.py" in handoff["localCommand"]
        assert "--sample-evidence" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]
        assert "--existing-sample-evidence" in handoff["localCommand"]
        assert "products-sample.json" in handoff["localCommand"]


def test_sample_upload_with_evidence_bundle_derives_filled_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_sample_upload_with_existing_sample(root))
        filled_path = write_json(
            root / "sample-evidence-bundle" / "manifest-sample-evidence.filled.json",
            {"kind": "allincms_manifest_sample_upload_evidence"},
        )
        bundle = {
            "kind": "allincms_manifest_sample_evidence_bundle",
            "manifest": str(root / "posts-schema-manifest.json"),
            "filledEvidencePath": filled_path,
        }
        bundle_path = write_json(root / "sample-evidence-bundle" / "evidence-bundle.json", bundle)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                sample_evidence_bundle=bundle_path,
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "sample_upload"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_manifest_sample_upload.py" in handoff["localCommand"]
        assert "posts-schema-manifest.json" in handoff["localCommand"]
        assert "manifest-sample-evidence.filled.json" in handoff["localCommand"]
        assert "--existing-sample-evidence" in handoff["localCommand"]
        assert "products-sample.json" in handoff["localCommand"]
        assert "filled manifest sample evidence bundle" in " ".join(handoff["requiredInputs"])
        assert "manifest sample evidence" in " ".join(handoff["adversarialChecks"])


def test_sample_upload_rejects_blocked_evidence_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_sample_upload_with_existing_sample(root))
        bundle = {
            "kind": "allincms_manifest_sample_evidence_bundle",
            "manifest": str(root / "posts-schema-manifest.json"),
            "filledEvidencePath": str(root / "sample-evidence-bundle" / "manifest-sample-evidence.filled.json"),
            "sourceCurrentStage": "sample_upload",
            "blockers": ["sample frontend proof missing"],
        }
        bundle_path = write_json(root / "sample-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, sample_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "manifest sample evidence bundle declares blockers" in str(exc)
        else:
            raise AssertionError("blocked sample evidence bundle should not produce an apply command")


def test_sample_upload_rejects_missing_filled_evidence_bundle_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_sample_upload_with_existing_sample(root))
        missing_filled_path = root / "sample-evidence-bundle" / "manifest-sample-evidence.filled.json"
        bundle = {
            "kind": "allincms_manifest_sample_evidence_bundle",
            "manifest": str(root / "posts-schema-manifest.json"),
            "filledEvidencePath": str(missing_filled_path),
            "sourceCurrentStage": "sample_upload",
        }
        bundle_path = write_json(root / "sample-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, sample_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "manifest sample evidence bundle filledEvidencePath does not exist" in str(exc)
        else:
            raise AssertionError("missing filled sample evidence file should not produce an apply command")


def test_batch_handoff_uses_sample_evidence_and_taxonomy_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_batch_upload(root)
        status_path = write_status(root, status)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                manifest=str(root / "schema-manifest.json"),
                base_run_evidence=str(root / "base-run.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "batch_upload"
        assert "prepare_batch_upload_publish.py" in handoff["localCommand"]
        assert "<sample-evidence-for-selected-manifest.json>" in handoff["localCommand"]
        assert "products-sample.json" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]
        assert "schema-manifest.json" in handoff["localCommand"]
        assert "same content type as the selected manifest" in " ".join(handoff["requiredInputs"])


def test_batch_handoff_accepts_explicit_sample_for_selected_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status = status_at_batch_upload(root)
        status_path = write_status(root, status)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                manifest=str(root / "posts-schema-manifest.json"),
                base_run_evidence=str(root / "base-run.json"),
                sample_evidence=str(root / "posts-sample.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "batch_upload"
        assert "prepare_batch_upload_publish.py" in handoff["localCommand"]
        assert "--sample-evidence" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]
        assert "<sample-evidence-for-selected-manifest.json>" not in handoff["localCommand"]


def test_batch_upload_with_evidence_applies_stage_and_preserves_existing_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_batch_upload_with_existing_batch_validation(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                manifest=str(root / "posts-schema-manifest.json"),
                base_run_evidence=str(root / "base-run.json"),
                batch_evidence=str(root / "posts-batch-evidence.json"),
                frontend_audit_report=str(root / "posts-frontend-audit.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "batch_upload"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_batch_upload_publish.py" in handoff["localCommand"]
        assert "--batch-evidence" in handoff["localCommand"]
        assert "posts-batch-evidence.json" in handoff["localCommand"]
        assert "--existing-batch-validation" in handoff["localCommand"]
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "products-sample.json" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]


def test_batch_upload_with_evidence_bundle_derives_apply_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_batch_upload_with_existing_batch_validation(root))
        filled_path = write_json(
            root / "posts-batch-evidence-bundle" / "batch-upload-publish-evidence.filled.json",
            {"kind": "allincms_batch_upload_publish_evidence"},
        )
        bundle = {
            "kind": "allincms_batch_upload_publish_evidence_bundle",
            "manifest": str(root / "posts-schema-manifest.json"),
            "sourceRunEvidence": str(root / "base-run.json"),
            "filledEvidencePath": filled_path,
            "sourceSampleEvidence": str(root / "posts-sample.json"),
        }
        bundle_path = write_json(root / "posts-batch-evidence-bundle" / "evidence-bundle.json", bundle)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                batch_evidence_bundle=bundle_path,
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "batch_upload"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_batch_upload_publish.py" in handoff["localCommand"]
        assert "batch-upload-publish-evidence.filled.json" in handoff["localCommand"]
        assert "posts-schema-manifest.json" in handoff["localCommand"]
        assert "base-run.json" in handoff["localCommand"]
        assert "final-audit-report.redacted.json" in handoff["localCommand"]
        assert "--existing-batch-validation" in handoff["localCommand"]
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "products-sample.json" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]
        assert "batch upload evidence" in " ".join(handoff["adversarialChecks"])


def test_batch_upload_rejects_stale_evidence_bundle_stage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_batch_upload_with_existing_batch_validation(root))
        bundle = {
            "kind": "allincms_batch_upload_publish_evidence_bundle",
            "manifest": str(root / "posts-schema-manifest.json"),
            "sourceRunEvidence": str(root / "base-run.json"),
            "filledEvidencePath": str(root / "posts-batch-evidence-bundle" / "batch-upload-publish-evidence.filled.json"),
            "sourceCurrentStage": "sample_upload",
        }
        bundle_path = write_json(root / "posts-batch-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, batch_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "batch upload/publish evidence bundle was generated for sourceCurrentStage=sample_upload" in str(exc)
        else:
            raise AssertionError("stale batch evidence bundle should not produce an apply command")


def test_forms_media_settings_without_evidence_remains_browser_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_forms_media_settings(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "forms_media_settings"
        assert handoff["browserWorkRequired"] is True
        assert handoff["localCommand"] == ""
        assert "prepare_forms_media_settings_evidence_bundle.py" in handoff["nextPreparationCommand"]
        assert status_path in handoff["nextPreparationCommand"]
        assert "forms-media-settings-evidence-bundle" in handoff["nextPreparationCommand"]
        assert "forms/media/settings browser evidence" in " ".join(handoff["requiredInputs"])


def test_forms_media_settings_with_evidence_emits_apply_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_forms_media_settings(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                forms_media_settings_evidence=str(root / "forms-media-settings-evidence.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "forms_media_settings"
        assert handoff["browserWorkRequired"] is False
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["nextPreparationCommand"] == ""
        assert "apply_forms_media_settings.py" in handoff["localCommand"]
        assert "forms-media-settings-evidence.json" in handoff["localCommand"]
        assert handoff["localCommand"].count("--batch-validation") == 2
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "posts-batch-validation.json" in handoff["localCommand"]
        assert "--sample-evidence" in handoff["localCommand"]


def test_forms_media_settings_with_evidence_bundle_derives_filled_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_forms_media_settings(root))
        filled_path = write_json(
            root / "forms-media-settings-evidence-bundle" / "forms-media-settings-evidence.filled.json",
            {"kind": "allincms_forms_media_settings_evidence"},
        )
        bundle = {
            "kind": "allincms_forms_media_settings_evidence_bundle",
            "filledEvidencePath": filled_path,
        }
        bundle_path = write_json(root / "forms-media-settings-evidence-bundle" / "evidence-bundle.json", bundle)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                forms_media_settings_evidence_bundle=bundle_path,
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "forms_media_settings"
        assert handoff["browserWorkRequired"] is False
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert "apply_forms_media_settings.py" in handoff["localCommand"]
        assert "forms-media-settings-evidence.filled.json" in handoff["localCommand"]
        assert handoff["localCommand"].count("--batch-validation") == 2
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "posts-batch-validation.json" in handoff["localCommand"]
        assert "--sample-evidence" in handoff["localCommand"]
        assert "If forms/media/settings evidence is still in a filled bundle template" in " ".join(handoff["adversarialChecks"])


def test_forms_media_settings_rejects_blocked_evidence_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_forms_media_settings(root))
        bundle = {
            "kind": "allincms_forms_media_settings_evidence_bundle",
            "filledEvidencePath": str(
                root
                / "forms-media-settings-evidence-bundle"
                / "forms-media-settings-evidence.filled.json"
            ),
            "sourceStatusCurrentStage": "forms_media_settings",
            "blocked": True,
        }
        bundle_path = write_json(root / "forms-media-settings-evidence-bundle" / "evidence-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, forms_media_settings_evidence_bundle=bundle_path))
        except SystemExit as exc:
            assert "forms/media/settings evidence bundle declares blocked=true" in str(exc)
        else:
            raise AssertionError("blocked forms/media/settings evidence bundle should not produce an apply command")


def test_launch_acceptance_with_inputs_bundle_expands_apply_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_launch_acceptance(root))
        filled_inputs = {
            "kind": "allincms_launch_acceptance_inputs",
            "runEvidence": str(root / "run-evidence.json"),
            "moduleCoverage": str(root / "module-coverage.json"),
            "stageCoverage": "",
            "uploadReadiness": [str(root / "upload-readiness.json")],
            "batchValidation": [
                str(root / "products-batch-validation.json"),
                str(root / "posts-batch-validation.json"),
            ],
            "formsMediaSettings": str(root / "forms-media-settings.json"),
            "finalFrontendAudit": str(root / "final-frontend-audit.json"),
            "cleanupEvidence": str(root / "cleanup-evidence.json"),
            "roundCloseout": "",
            "autoFinalCloseout": True,
            "finalCloseoutSedimentation": "updated",
            "finalCloseoutSedimentationNote": "Recorded final launch proof.",
            "requireCreatedSite": True,
            "objective": "source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
            "package": str(root / "package.json"),
            "confirmation": str(root / "confirmation.json"),
            "executionPlan": str(root / "execution-plan.json"),
            "artifactReadiness": str(root / "artifact-readiness.json"),
            "createdSiteBinding": str(root / "binding.json"),
            "pagesSiteInfoHandoff": str(root / "pages-site-info-handoff.json"),
            "pagesSiteInfoValidation": str(root / "pages-site-info-validation.json"),
            "schemaCaptureHandoff": str(root / "schema-capture-handoff.json"),
            "sampleEvidence": [str(root / "products-sample.json"), str(root / "posts-sample.json")],
        }
        filled_path = write_json(root / "launch-acceptance-inputs-bundle" / "launch-acceptance-inputs.filled.json", filled_inputs)
        bundle = {
            "kind": "allincms_launch_acceptance_inputs_bundle",
            "filledInputsPath": filled_path,
        }
        bundle_path = write_json(root / "launch-acceptance-inputs-bundle" / "inputs-bundle.json", bundle)
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                launch_acceptance_inputs_bundle=bundle_path,
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "launch_acceptance"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert "apply_launch_acceptance.py" in handoff["localCommand"]
        assert "run-evidence.json" in handoff["localCommand"]
        assert "final-frontend-audit.json" in handoff["localCommand"]
        assert "cleanup-evidence.json" in handoff["localCommand"]
        assert "--auto-final-closeout" in handoff["localCommand"]
        assert "--require-created-site" in handoff["localCommand"]
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "posts-batch-validation.json" in handoff["localCommand"]
        assert "If launch acceptance inputs are still in a filled bundle template" in " ".join(handoff["adversarialChecks"])


def test_launch_acceptance_without_bundle_preserves_all_source_status_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_launch_acceptance(root))
        handoff = build_handoff(
            handoff_args(
                root,
                status_path,
                run_evidence=str(root / "run-evidence.json"),
                final_frontend_audit=str(root / "final-frontend-audit.json"),
                cleanup_evidence=str(root / "cleanup-evidence.json"),
            )
        )
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "launch_acceptance"
        assert "apply_launch_acceptance.py" in handoff["localCommand"]
        assert handoff["localCommand"].count("--upload-readiness") == 1
        assert handoff["localCommand"].count("--sample-evidence") == 2
        assert handoff["localCommand"].count("--batch-validation") == 2
        assert "products-sample.json" in handoff["localCommand"]
        assert "posts-sample.json" in handoff["localCommand"]
        assert "products-batch-validation.json" in handoff["localCommand"]
        assert "posts-batch-validation.json" in handoff["localCommand"]


def test_launch_acceptance_without_inputs_exposes_bundle_preparation_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_launch_acceptance(root))
        handoff = build_handoff(handoff_args(root, status_path))
        assert not validate_handoff(handoff), handoff
        assert handoff["currentStage"] == "launch_acceptance"
        assert handoff["mode"] == "local_helper_prepares_or_applies_stage"
        assert handoff["browserWorkRequired"] is False
        assert handoff["localCommand"] == ""
        assert "prepare_launch_acceptance_inputs_bundle.py" in handoff["nextPreparationCommand"]
        assert status_path in handoff["nextPreparationCommand"]
        assert "launch-acceptance-inputs-bundle" in handoff["nextPreparationCommand"]
        assert "<final-run-evidence.json>" not in handoff["nextPreparationCommand"]


def test_launch_acceptance_rejects_stale_inputs_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_launch_acceptance(root))
        filled_inputs = {
            "kind": "allincms_launch_acceptance_inputs",
            "runEvidence": str(root / "run-evidence.json"),
            "finalFrontendAudit": str(root / "final-frontend-audit.json"),
            "cleanupEvidence": str(root / "cleanup-evidence.json"),
            "formsMediaSettings": str(root / "forms-media-settings.json"),
            "autoFinalCloseout": True,
            "finalCloseoutSedimentation": "updated",
            "finalCloseoutSedimentationNote": "Recorded final launch proof.",
            "uploadReadiness": [str(root / "upload-readiness.json")],
            "sampleEvidence": [str(root / "products-sample.json")],
            "batchValidation": [str(root / "products-batch-validation.json")],
            "package": str(root / "package.json"),
            "confirmation": str(root / "confirmation.json"),
            "executionPlan": str(root / "execution-plan.json"),
            "artifactReadiness": str(root / "artifact-readiness.json"),
            "createdSiteBinding": str(root / "binding.json"),
        }
        filled_path = write_json(root / "launch-acceptance-inputs-bundle" / "launch-acceptance-inputs.filled.json", filled_inputs)
        bundle = {
            "kind": "allincms_launch_acceptance_inputs_bundle",
            "filledInputsPath": filled_path,
            "sourceStatusCurrentStage": "forms_media_settings",
        }
        bundle_path = write_json(root / "launch-acceptance-inputs-bundle" / "inputs-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, launch_acceptance_inputs_bundle=bundle_path))
        except SystemExit as exc:
            assert "launch acceptance inputs bundle was generated for sourceStatusCurrentStage=forms_media_settings" in str(exc)
        else:
            raise AssertionError("stale launch inputs bundle should not produce an apply command")


def test_launch_acceptance_rejects_placeholder_filled_inputs_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        status_path = write_status(root, status_at_launch_acceptance(root))
        filled_inputs = {
            "kind": "allincms_launch_acceptance_inputs",
            "runEvidence": "<final-run-evidence.json>",
            "finalFrontendAudit": str(root / "final-frontend-audit.json"),
            "cleanupEvidence": str(root / "cleanup-evidence.json"),
            "formsMediaSettings": str(root / "forms-media-settings.json"),
            "autoFinalCloseout": True,
            "finalCloseoutSedimentation": "updated",
            "finalCloseoutSedimentationNote": "Recorded final launch proof.",
            "uploadReadiness": [str(root / "upload-readiness.json")],
            "sampleEvidence": [str(root / "products-sample.json")],
            "batchValidation": [str(root / "products-batch-validation.json")],
            "package": str(root / "package.json"),
            "confirmation": str(root / "confirmation.json"),
            "executionPlan": str(root / "execution-plan.json"),
            "artifactReadiness": str(root / "artifact-readiness.json"),
            "createdSiteBinding": str(root / "binding.json"),
        }
        filled_path = write_json(root / "launch-acceptance-inputs-bundle" / "launch-acceptance-inputs.filled.json", filled_inputs)
        bundle = {
            "kind": "allincms_launch_acceptance_inputs_bundle",
            "filledInputsPath": filled_path,
            "sourceStatusCurrentStage": "launch_acceptance",
        }
        bundle_path = write_json(root / "launch-acceptance-inputs-bundle" / "inputs-bundle.json", bundle)
        try:
            build_handoff(handoff_args(root, status_path, launch_acceptance_inputs_bundle=bundle_path))
        except SystemExit as exc:
            assert "filled launch acceptance inputs are invalid" in str(exc)
            assert "runEvidence must be a concrete path, not a placeholder" in str(exc)
        else:
            raise AssertionError("placeholder launch inputs bundle should not produce an apply command")


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source next-stage handoff regression tests passed.")
