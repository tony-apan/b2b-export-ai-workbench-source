#!/usr/bin/env python3
"""Regression tests for source progress status summaries."""

from __future__ import annotations

import tempfile
from pathlib import Path

from make_source_progress_status import rehearsal_progress, status_progress
from test_run_source_file_rehearsal import base_args as rehearsal_base_args
from test_run_source_file_rehearsal import refined_target, wiki_for_rehearsal_inventory
from test_run_source_file_rehearsal import write_json as write_rehearsal_json
from run_source_file_rehearsal import build as build_rehearsal
from test_summarize_source_execution_status import (
    base_args as status_base_args,
    batch_validation,
    created_site_binding,
    create_site_handoff,
    fill_base,
    forms_media_settings,
    launch_acceptance,
    pages_site_info_handoff,
    pages_site_info_validation,
    sample_evidence,
    schema_capture_handoff,
    summarize,
    upload_readiness,
    write_json,
)
from test_make_source_objective_coverage import acceptance_report


def test_progress_from_rehearsal_waits_for_user_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = rehearsal_base_args(root, source)
        args.refined_source_wiki = write_rehearsal_json(refined_target(root), wiki_for_rehearsal_inventory())
        summary = build_rehearsal(args)
        progress = rehearsal_progress(summary, source_path="/tmp/source-file-rehearsal-summary.json", objective="files to site")
        assert progress["complete"] is False
        assert progress["reviewReady"] is True
        assert progress["confirmationPrepared"] is False
        assert progress["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert progress["nextBlockingLabel"] == "user content-intent confirmation converted to execution artifacts"
        assert progress["nextActionGate"]["remoteMutationAllowed"] is False
        assert progress["nextActionGate"]["requiresUserContentConfirmation"] is True
        assert progress["nextActionGate"]["nextGate"] == "user_content_confirmation"
        assert progress["batchReadiness"]["readyForBatchUpload"] is False
        assert any(item["label"] == "source-backed wiki generated" and item["status"] == "proven" for item in progress["progress"])


def test_progress_from_status_reports_batch_ready_after_samples() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = status_base_args(root)
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
        status = summarize(args)
        progress = status_progress(status, source_path="/tmp/source-execution-status.json", objective="files to site")
        assert progress["complete"] is False
        assert progress["currentStage"] == "batch_upload"
        assert progress["nextBlockingId"] == "batch_upload"
        assert progress["batchReadiness"]["readyForBatchUpload"] is True
        assert progress["nextActionGate"]["remoteMutationAllowed"] is False
        assert progress["nextActionGate"]["requiresActionTimeAuthorization"] is True
        assert progress["nextActionGate"]["nextGate"] == "action_time_authorization_and_pre_mutation_gate"
        assert progress["contentTypeCoverage"]["sampleEvidence"] == ["posts", "products"]


def test_progress_from_rehearsal_create_site_preflight_requires_readonly_browser_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = rehearsal_base_args(root, source)
        args.refined_source_wiki = write_rehearsal_json(refined_target(root), wiki_for_rehearsal_inventory())
        args.user_confirmation_text = "I confirm this source package content intent for a temporary demo site."
        summary = build_rehearsal(args)
        progress = rehearsal_progress(summary, source_path="/tmp/source-file-rehearsal-summary.json", objective="files to site")
        assert progress["readyForBrowserStage"] == "needs_create_site_preflight"
        assert progress["nextActionGate"]["remoteMutationAllowed"] is False
        assert progress["nextActionGate"]["requiresReadOnlyBrowserEvidence"] is True
        assert progress["nextActionGate"]["requiresActionTimeAuthorization"] is False
        assert progress["nextActionGate"]["nextGate"] == "read_only_browser_preflight"


def test_progress_from_complete_status_is_not_objective_complete_without_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = status_base_args(root)
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
        status = summarize(args)
        progress = status_progress(status, source_path="/tmp/source-execution-status.json", objective="files to site")
        assert status["complete"] is True
        assert progress["sourceStatusComplete"] is True
        assert progress["finalAcceptanceAccepted"] is False
        assert progress["complete"] is False
        assert any("sourceStatusComplete without finalAcceptanceAccepted is not enough" in item for item in progress["adversarialChecks"])


def test_progress_complete_only_with_accepted_final_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = acceptance_report(root)
        status = {
            "kind": "allincms_source_execution_status",
            "complete": True,
            "currentStage": "complete",
            "passedCount": 17,
            "stageCount": 17,
            "stages": {stage_id: {"status": "passed", "evidence": f"/tmp/{stage_id}.json", "blockers": [], "nextAction": ""} for stage_id in (
                "source_package",
                "review_packet",
                "confirmation",
                "execution_plan",
                "artifact_export",
                "created_site_binding",
                "pages_site_info_execution",
                "taxonomy_execution",
                "schema_manifests",
                "sample_upload",
                "batch_upload",
                "forms_media_settings",
                "launch_acceptance",
            )},
            "nextAction": "complete",
        }
        progress = status_progress(
            status,
            source_path="/tmp/source-execution-status.json",
            objective="files to site",
            final_acceptance=report,
            final_acceptance_path="/tmp/source-run-acceptance-validation.json",
        )
        assert report["accepted"] is True
        assert progress["sourceStatusComplete"] is True
        assert progress["finalAcceptanceAccepted"] is True
        assert progress["complete"] is True


if __name__ == "__main__":
    test_progress_from_rehearsal_waits_for_user_confirmation()
    test_progress_from_status_reports_batch_ready_after_samples()
    test_progress_from_rehearsal_create_site_preflight_requires_readonly_browser_evidence()
    test_progress_from_complete_status_is_not_objective_complete_without_final_acceptance()
    test_progress_complete_only_with_accepted_final_acceptance()
    print("source progress status tests passed.")
