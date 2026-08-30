#!/usr/bin/env python3
"""Run the full local-only AllinCMS rehearsal and handoff safety checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import simulate_full_e2e_chain
from apply_browser_stage_result import apply_stage_result, build_stage_result, validate_browser_stage_result
from build_browser_execution_ledger import build_browser_execution_ledger, validate_browser_execution_ledger
from build_browser_execution_plan import build_browser_execution_plan, validate_browser_execution_plan
from build_browser_stage_packet import build_browser_stage_packet, validate_browser_stage_packet
from build_launch_plan import build_launch_plan, validate_launch_plan, write_json as write_launch_json
from make_capture_handoff import build_handoff
from make_next_browser_action_handoff import build_handoff as build_next_browser_action_handoff
from make_final_frontend_audit_stage_result import build_result as build_final_frontend_audit_stage_result
from make_final_frontend_audit_stage_result import url_fingerprint as final_audit_url_fingerprint
from make_browser_runbook_summary import build_runbook_summary
from prepare_browser_stage_authorization import build_package as build_browser_stage_authorization_package
from prepare_browser_stage_evidence_bundle import prepare_bundle as prepare_browser_stage_evidence_bundle
from validate_browser_stage_evidence_bundle import validate_bundle as validate_browser_stage_evidence_bundle
from update_module_capture_coverage import build_capture_result, sync_ledger_with_coverage, update_coverage, validate_coverage
from validate_capture_plan_gate_coverage import validate_plan_gate_coverage
from validate_capture_handoff import validate_handoff
from validate_full_e2e_simulation import validate_directory
from validate_next_browser_action_handoff import validate_handoff as validate_next_browser_action_handoff


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_complete_module_capture_coverage(module_capture_plan: dict, seed_coverage: dict) -> dict:
    coverage = seed_coverage
    for stage in module_capture_plan.get("stages", []):
        if not isinstance(stage, dict):
            continue
        module = str(stage.get("module", ""))
        action = str(stage.get("action", ""))
        if not module or not action:
            continue
        result = build_capture_result(
            module,
            action,
            "captured",
            list(stage.get("requiredProof", [])),
            [f"local://module-capture-{module}-{action}-redacted.json"],
            [],
        )
        coverage = update_coverage(module_capture_plan, result, coverage)
    return coverage


def ensure_ok(label: str, validation: dict) -> None:
    if not validation.get("ok"):
        raise ValueError(f"{label} failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))


def build_packet_for_paths(ledger: dict, ledger_path: Path, packet_path: Path, stage_id: str = "") -> dict:
    return build_browser_stage_packet(
        ledger,
        stage_id,
        str(ledger_path),
        str(packet_path),
        str(packet_path.with_name(packet_path.stem + "-stage-result.json")),
        str(ledger_path.with_name(ledger_path.stem + f".after-{stage_id or ledger.get('nextStageId', 'stage')}.json")),
    )


def apply_completed_result_after_partial(
    partial_ledger: dict,
    stage_id: str,
    complete_result: dict,
    label: str,
    partial_ledger_path: Path | None = None,
    recovery_packet_path: Path | None = None,
) -> tuple[dict, dict, dict, dict]:
    recovery_packet = build_browser_stage_packet(partial_ledger, stage_id)
    if partial_ledger_path is not None and recovery_packet_path is not None:
        recovery_packet = build_packet_for_paths(partial_ledger, partial_ledger_path, recovery_packet_path, stage_id)
    recovery_packet_validation = validate_browser_stage_packet(recovery_packet)
    ensure_ok(f"{label} recovery packet validation", recovery_packet_validation)
    complete_result_validation = validate_browser_stage_result(complete_result, recovery_packet)
    ensure_ok(f"{label} complete result validation", complete_result_validation)
    complete_ledger = apply_stage_result(partial_ledger, recovery_packet, complete_result)
    complete_ledger_validation = validate_browser_execution_ledger(complete_ledger)
    ensure_ok(f"{label} recovery complete ledger validation", complete_ledger_validation)
    return recovery_packet, recovery_packet_validation, complete_ledger, complete_ledger_validation


def run_rehearsal(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    full_e2e_dir = output_dir / "full-e2e"
    handoff_dir = output_dir / "next-capture-handoff"
    handoff_path = handoff_dir / "handoff.json"
    launch_plan_path = output_dir / "launch-plan.json"
    browser_execution_plan_path = output_dir / "browser-execution-plan.json"
    browser_execution_ledger_path = output_dir / "browser-execution-ledger.json"
    browser_stage_packet_path = output_dir / "next-browser-stage-packet.json"
    browser_stage_evidence_bundle_dir = output_dir / "next-browser-stage-evidence-bundle"
    browser_stage_evidence_manifest_path = browser_stage_evidence_bundle_dir / "evidence-manifest.json"
    simulated_stage_result_path = output_dir / "simulated-first-stage-result.json"
    ledger_after_first_stage_path = output_dir / "browser-execution-ledger-after-first-stage.json"
    browser_stage_packet_after_first_stage_path = output_dir / "next-browser-stage-packet-after-first-stage.json"
    simulated_create_site_result_path = output_dir / "simulated-create-site-result.json"
    ledger_after_create_site_path = output_dir / "browser-execution-ledger-after-create-site.json"
    browser_stage_packet_after_create_site_path = output_dir / "next-browser-stage-packet-after-create-site.json"
    simulated_setup_result_path = output_dir / "simulated-setup-pages-result.json"
    ledger_after_setup_path = output_dir / "browser-execution-ledger-after-setup-pages.json"
    browser_stage_packet_after_setup_path = output_dir / "next-browser-stage-packet-after-setup-pages.json"
    browser_stage_module_capture_authorization_package_path = (
        output_dir / "browser-stage-module-interface-authorization-package.json"
    )
    next_browser_action_handoff_path = output_dir / "next-browser-action-handoff.json"
    simulated_module_capture_partial_result_path = output_dir / "simulated-module-capture-partial-result.json"
    ledger_after_module_capture_partial_path = output_dir / "browser-execution-ledger-after-module-capture-partial.json"
    simulated_module_capture_stage_result_path = output_dir / "simulated-module-capture-stage-result.json"
    capture_plan_gate_coverage_path = output_dir / "capture-plan-gate-coverage.json"
    module_capture_coverage_path = output_dir / "module-capture-coverage-after-one-stage.json"
    ledger_after_module_capture_coverage_sync_path = output_dir / "browser-execution-ledger-after-module-capture-coverage-sync.json"
    module_capture_coverage_complete_path = output_dir / "module-capture-coverage-complete.json"
    ledger_after_module_capture_complete_path = output_dir / "browser-execution-ledger-after-module-capture-complete.json"
    browser_stage_packet_after_module_capture_complete_path = output_dir / "next-browser-stage-packet-after-module-capture-complete.json"
    simulated_theme_launch_partial_result_path = output_dir / "simulated-theme-launch-partial-result.json"
    ledger_after_theme_launch_partial_path = output_dir / "browser-execution-ledger-after-theme-launch-partial.json"
    browser_stage_packet_after_theme_launch_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-theme-launch-partial-recovery.json"
    )
    ledger_after_theme_launch_recovery_complete_path = (
        output_dir / "browser-execution-ledger-after-theme-launch-recovery-complete.json"
    )
    simulated_theme_launch_complete_result_path = output_dir / "simulated-theme-launch-complete-result.json"
    ledger_after_theme_launch_complete_path = output_dir / "browser-execution-ledger-after-theme-launch-complete.json"
    browser_stage_packet_after_theme_launch_complete_path = output_dir / "next-browser-stage-packet-after-theme-launch-complete.json"
    simulated_static_audit_partial_result_path = output_dir / "simulated-static-audit-partial-result.json"
    ledger_after_static_audit_partial_path = output_dir / "browser-execution-ledger-after-static-audit-partial.json"
    browser_stage_packet_after_static_audit_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-static-audit-partial-recovery.json"
    )
    simulated_static_audit_complete_result_path = output_dir / "simulated-static-audit-complete-result.json"
    ledger_after_static_audit_complete_path = output_dir / "browser-execution-ledger-after-static-audit-complete.json"
    browser_stage_packet_after_static_audit_complete_path = output_dir / "next-browser-stage-packet-after-static-audit-complete.json"
    simulated_content_probe_partial_result_path = output_dir / "simulated-content-probe-partial-result.json"
    ledger_after_content_probe_partial_path = output_dir / "browser-execution-ledger-after-content-probe-partial.json"
    browser_stage_packet_after_content_probe_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-content-probe-partial-recovery.json"
    )
    simulated_content_probe_complete_result_path = output_dir / "simulated-content-probe-complete-result.json"
    ledger_after_content_probe_complete_path = output_dir / "browser-execution-ledger-after-content-probe-complete.json"
    browser_stage_packet_after_content_probe_complete_path = output_dir / "next-browser-stage-packet-after-content-probe-complete.json"
    simulated_save_request_partial_result_path = output_dir / "simulated-save-request-partial-result.json"
    ledger_after_save_request_partial_path = output_dir / "browser-execution-ledger-after-save-request-partial.json"
    browser_stage_packet_after_save_request_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-save-request-partial-recovery.json"
    )
    simulated_save_request_complete_result_path = output_dir / "simulated-save-request-complete-result.json"
    ledger_after_save_request_complete_path = output_dir / "browser-execution-ledger-after-save-request-complete.json"
    browser_stage_packet_after_save_request_complete_path = output_dir / "next-browser-stage-packet-after-save-request-complete.json"
    simulated_publish_sample_partial_result_path = output_dir / "simulated-publish-sample-partial-result.json"
    ledger_after_publish_sample_partial_path = output_dir / "browser-execution-ledger-after-publish-sample-partial.json"
    browser_stage_packet_after_publish_sample_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-publish-sample-partial-recovery.json"
    )
    simulated_publish_sample_complete_result_path = output_dir / "simulated-publish-sample-complete-result.json"
    ledger_after_publish_sample_complete_path = output_dir / "browser-execution-ledger-after-publish-sample-complete.json"
    browser_stage_packet_after_publish_sample_complete_path = output_dir / "next-browser-stage-packet-after-publish-sample-complete.json"
    simulated_manifest_gate_partial_result_path = output_dir / "simulated-manifest-gate-partial-result.json"
    source_input_requirements_path = output_dir / "full-e2e" / "04-manifest-rehearsal" / "source-input-requirements.json"
    ledger_after_manifest_gate_partial_path = output_dir / "browser-execution-ledger-after-manifest-gate-partial.json"
    browser_stage_packet_after_manifest_gate_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-manifest-gate-partial-recovery.json"
    )
    simulated_manifest_gate_complete_result_path = output_dir / "simulated-manifest-gate-complete-result.json"
    ledger_after_manifest_gate_complete_path = output_dir / "browser-execution-ledger-after-manifest-gate-complete.json"
    browser_stage_packet_after_manifest_gate_complete_path = output_dir / "next-browser-stage-packet-after-manifest-gate-complete.json"
    simulated_batch_upload_partial_result_path = output_dir / "simulated-batch-upload-partial-result.json"
    ledger_after_batch_upload_partial_path = output_dir / "browser-execution-ledger-after-batch-upload-partial.json"
    browser_stage_packet_after_batch_upload_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-batch-upload-partial-recovery.json"
    )
    simulated_batch_upload_complete_result_path = output_dir / "simulated-batch-upload-complete-result.json"
    ledger_after_batch_upload_complete_path = output_dir / "browser-execution-ledger-after-batch-upload-complete.json"
    browser_stage_packet_after_batch_upload_complete_path = output_dir / "next-browser-stage-packet-after-batch-upload-complete.json"
    simulated_forms_media_settings_partial_result_path = output_dir / "simulated-forms-media-settings-partial-result.json"
    ledger_after_forms_media_settings_partial_path = output_dir / "browser-execution-ledger-after-forms-media-settings-partial.json"
    browser_stage_packet_after_forms_media_settings_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-forms-media-settings-partial-recovery.json"
    )
    simulated_forms_media_settings_complete_result_path = output_dir / "simulated-forms-media-settings-complete-result.json"
    ledger_after_forms_media_settings_complete_path = output_dir / "browser-execution-ledger-after-forms-media-settings-complete.json"
    browser_stage_packet_after_forms_media_settings_complete_path = output_dir / "next-browser-stage-packet-after-forms-media-settings-complete.json"
    simulated_final_frontend_audit_partial_result_path = output_dir / "simulated-final-frontend-audit-partial-result.json"
    simulated_final_frontend_audit_partial_report_path = output_dir / "simulated-final-audit-report-missing-detail.json"
    ledger_after_final_frontend_audit_partial_path = output_dir / "browser-execution-ledger-after-final-frontend-audit-partial.json"
    browser_stage_packet_after_final_frontend_audit_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-final-frontend-audit-partial-recovery.json"
    )
    simulated_final_frontend_audit_complete_result_path = output_dir / "simulated-final-frontend-audit-complete-result.json"
    simulated_final_frontend_audit_complete_report_path = output_dir / "simulated-final-audit-report-complete.json"
    simulated_final_frontend_audit_inputs_summary_path = output_dir / "simulated-final-audit-inputs-summary.json"
    simulated_final_frontend_audit_expected_statuses_path = output_dir / "simulated-final-expected-statuses.json"
    ledger_after_final_frontend_audit_complete_path = output_dir / "browser-execution-ledger-after-final-frontend-audit-complete.json"
    browser_stage_packet_after_final_frontend_audit_complete_path = output_dir / "next-browser-stage-packet-after-final-frontend-audit-complete.json"
    simulated_cleanup_probes_partial_result_path = output_dir / "simulated-cleanup-probes-partial-result.json"
    ledger_after_cleanup_probes_partial_path = output_dir / "browser-execution-ledger-after-cleanup-probes-partial.json"
    browser_stage_packet_after_cleanup_probes_partial_recovery_path = (
        output_dir / "next-browser-stage-packet-after-cleanup-probes-partial-recovery.json"
    )
    simulated_cleanup_probes_complete_result_path = output_dir / "simulated-cleanup-probes-complete-result.json"
    ledger_after_cleanup_probes_complete_path = output_dir / "browser-execution-ledger-after-cleanup-probes-complete.json"
    summary_path = output_dir / "rehearsal-summary.json"
    browser_runbook_summary_path = output_dir / "browser-runbook-summary.json"

    full_args = argparse.Namespace(
        no_existing_sites=args.no_existing_sites,
        existing_site_keys=args.existing_site_keys,
        site_key_evidence=args.site_key_evidence,
        empty_site_list_evidence=args.empty_site_list_evidence,
        simulated_created_site_key=args.simulated_created_site_key,
        content_type=args.content_type,
        observed_create_fields=args.observed_create_fields,
        list_columns=args.list_columns,
        edit_fields=args.edit_fields,
        create_authorization_source=args.create_authorization_source,
        simulated_content_id=args.simulated_content_id,
        simulated_slug=args.simulated_slug,
        max_age_minutes=args.max_age_minutes,
        sedimentation=args.sedimentation,
        closeout_note=args.closeout_note,
        changed_files=args.changed_files,
        output_dir=str(full_e2e_dir),
    )
    full_paths = simulate_full_e2e_chain.run_simulation(full_args)
    full_validation = validate_directory(full_e2e_dir)
    if not full_validation.get("ok"):
        raise ValueError("full E2E validation failed:\n" + "\n".join(f"- {issue}" for issue in full_validation["issues"]))

    handoff = build_handoff(
        full_e2e_dir,
        args.module.strip(),
        args.action.strip(),
        handoff_dir,
        args.allow_command_output,
    )
    handoff_validation = validate_handoff(handoff, args.allow_command_output)
    if not handoff_validation.get("ok"):
        raise ValueError("capture handoff validation failed:\n" + "\n".join(f"- {issue}" for issue in handoff_validation["issues"]))
    write_json(handoff_path, handoff)

    launch_plan = build_launch_plan(full_e2e_dir, handoff)
    launch_plan_validation = validate_launch_plan(launch_plan)
    if not launch_plan_validation.get("ok"):
        raise ValueError("launch plan validation failed:\n" + "\n".join(f"- {issue}" for issue in launch_plan_validation["issues"]))
    write_launch_json(launch_plan_path, launch_plan)

    browser_execution_plan = build_browser_execution_plan(full_e2e_dir, handoff, launch_plan)
    browser_execution_plan_validation = validate_browser_execution_plan(browser_execution_plan)
    if not browser_execution_plan_validation.get("ok"):
        raise ValueError(
            "browser execution plan validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_execution_plan_validation["issues"])
        )
    write_json(browser_execution_plan_path, browser_execution_plan)

    browser_execution_ledger = build_browser_execution_ledger(browser_execution_plan)
    browser_execution_ledger_validation = validate_browser_execution_ledger(browser_execution_ledger)
    if not browser_execution_ledger_validation.get("ok"):
        raise ValueError(
            "browser execution ledger validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_execution_ledger_validation["issues"])
        )
    write_json(browser_execution_ledger_path, browser_execution_ledger)

    browser_stage_packet = build_packet_for_paths(browser_execution_ledger, browser_execution_ledger_path, browser_stage_packet_path)
    browser_stage_packet_validation = validate_browser_stage_packet(browser_stage_packet)
    if not browser_stage_packet_validation.get("ok"):
        raise ValueError(
            "browser stage packet validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_validation["issues"])
        )
    write_json(browser_stage_packet_path, browser_stage_packet)
    browser_stage_evidence_manifest = prepare_browser_stage_evidence_bundle(
        browser_stage_packet_path,
        browser_stage_evidence_bundle_dir,
        True,
    )
    browser_stage_evidence_bundle_validation = validate_browser_stage_evidence_bundle(
        browser_stage_evidence_bundle_dir,
        browser_stage_packet_path,
    )
    if not browser_stage_evidence_bundle_validation.get("ok"):
        raise ValueError(
            "browser stage evidence bundle validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_evidence_bundle_validation["issues"])
        )

    simulated_stage_result = build_stage_result(
        str(browser_stage_packet.get("stageId", "")),
        "completed",
        ["local://redacted-readonly-scan.json", "local://create-dialog-closed-proof.json"],
        list(browser_stage_packet.get("requiredProof", [])),
        [],
    )
    simulated_stage_result_validation = validate_browser_stage_result(simulated_stage_result, browser_stage_packet)
    if not simulated_stage_result_validation.get("ok"):
        raise ValueError(
            "simulated browser stage result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_stage_result_validation["issues"])
        )
    write_json(simulated_stage_result_path, simulated_stage_result)

    ledger_after_first_stage = apply_stage_result(browser_execution_ledger, browser_stage_packet, simulated_stage_result)
    ledger_after_first_stage_validation = validate_browser_execution_ledger(ledger_after_first_stage)
    if not ledger_after_first_stage_validation.get("ok"):
        raise ValueError(
            "ledger after first stage validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_first_stage_validation["issues"])
        )
    write_json(ledger_after_first_stage_path, ledger_after_first_stage)

    browser_stage_packet_after_first_stage = build_packet_for_paths(ledger_after_first_stage, ledger_after_first_stage_path, browser_stage_packet_after_first_stage_path)
    browser_stage_packet_after_first_stage_validation = validate_browser_stage_packet(browser_stage_packet_after_first_stage)
    if not browser_stage_packet_after_first_stage_validation.get("ok"):
        raise ValueError(
            "browser stage packet after first stage validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_first_stage_validation["issues"])
        )
    write_json(browser_stage_packet_after_first_stage_path, browser_stage_packet_after_first_stage)

    simulated_create_site_result = build_stage_result(
        str(browser_stage_packet_after_first_stage.get("stageId", "")),
        "completed",
        [
            "local://create-site-preflight.json",
            "local://create-site-authorization.json",
            "local://created-site-evidence.json",
        ],
        list(browser_stage_packet_after_first_stage.get("requiredProof", [])),
        [],
        True,
    )
    simulated_create_site_result_validation = validate_browser_stage_result(
        simulated_create_site_result,
        browser_stage_packet_after_first_stage,
    )
    if not simulated_create_site_result_validation.get("ok"):
        raise ValueError(
            "simulated create-site stage result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_create_site_result_validation["issues"])
        )
    write_json(simulated_create_site_result_path, simulated_create_site_result)

    ledger_after_create_site = apply_stage_result(
        ledger_after_first_stage,
        browser_stage_packet_after_first_stage,
        simulated_create_site_result,
    )
    ledger_after_create_site_validation = validate_browser_execution_ledger(ledger_after_create_site)
    if not ledger_after_create_site_validation.get("ok"):
        raise ValueError(
            "ledger after create site validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_create_site_validation["issues"])
        )
    write_json(ledger_after_create_site_path, ledger_after_create_site)

    browser_stage_packet_after_create_site = build_packet_for_paths(ledger_after_create_site, ledger_after_create_site_path, browser_stage_packet_after_create_site_path)
    browser_stage_packet_after_create_site_validation = validate_browser_stage_packet(browser_stage_packet_after_create_site)
    if not browser_stage_packet_after_create_site_validation.get("ok"):
        raise ValueError(
            "browser stage packet after create site validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_create_site_validation["issues"])
        )
    write_json(browser_stage_packet_after_create_site_path, browser_stage_packet_after_create_site)

    simulated_setup_result = build_stage_result(
        str(browser_stage_packet_after_create_site.get("stageId", "")),
        "completed",
        [
            "local://site-info-fields.json",
            "local://domains-controls.json",
            "local://themes-controls.json",
            "local://routes-columns.json",
            "local://forms-columns.json",
        ],
        list(browser_stage_packet_after_create_site.get("requiredProof", [])),
        [],
    )
    simulated_setup_result_validation = validate_browser_stage_result(
        simulated_setup_result,
        browser_stage_packet_after_create_site,
    )
    if not simulated_setup_result_validation.get("ok"):
        raise ValueError(
            "simulated setup-pages stage result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_setup_result_validation["issues"])
        )
    write_json(simulated_setup_result_path, simulated_setup_result)

    ledger_after_setup = apply_stage_result(
        ledger_after_create_site,
        browser_stage_packet_after_create_site,
        simulated_setup_result,
    )
    ledger_after_setup_validation = validate_browser_execution_ledger(ledger_after_setup)
    if not ledger_after_setup_validation.get("ok"):
        raise ValueError(
            "ledger after setup pages validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_setup_validation["issues"])
        )
    write_json(ledger_after_setup_path, ledger_after_setup)

    browser_stage_packet_after_setup = build_packet_for_paths(ledger_after_setup, ledger_after_setup_path, browser_stage_packet_after_setup_path)
    browser_stage_packet_after_setup_validation = validate_browser_stage_packet(browser_stage_packet_after_setup)
    if not browser_stage_packet_after_setup_validation.get("ok"):
        raise ValueError(
            "browser stage packet after setup pages validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_setup_validation["issues"])
        )
    write_json(browser_stage_packet_after_setup_path, browser_stage_packet_after_setup)

    module_capture_plan_path = Path(full_paths["moduleCapturePlan"])
    module_capture_plan = json.loads(module_capture_plan_path.read_text(encoding="utf-8"))
    browser_stage_module_capture_authorization_package = build_browser_stage_authorization_package(
        browser_stage_packet_after_setup,
        str(full_paths["siteCreatedEvidence"]),
        str(output_dir / "module-interface-authorization-record.json"),
        str(module_capture_plan_path),
        "",
        args.allow_command_output,
    )
    write_json(
        browser_stage_module_capture_authorization_package_path,
        browser_stage_module_capture_authorization_package,
    )
    site_created_evidence = json.loads(Path(full_paths["siteCreatedEvidence"]).read_text(encoding="utf-8"))
    next_browser_action_handoff = build_next_browser_action_handoff(
        package=browser_stage_module_capture_authorization_package,
        packet=browser_stage_packet_after_setup,
        preflight=site_created_evidence,
        capture_plan=module_capture_plan,
        package_path=str(browser_stage_module_capture_authorization_package_path),
        packet_path=str(browser_stage_packet_after_setup_path),
        preflight_path=str(full_paths["siteCreatedEvidence"]),
        capture_plan_path=str(module_capture_plan_path),
    )
    write_json(next_browser_action_handoff_path, next_browser_action_handoff)
    next_browser_action_handoff_validation = validate_next_browser_action_handoff(next_browser_action_handoff)
    if not next_browser_action_handoff_validation.get("ok"):
        raise ValueError(
            "next browser action handoff validation failed:\n"
            + "\n".join(f"- {issue}" for issue in next_browser_action_handoff_validation["issues"])
        )

    simulated_module_capture_partial_result = build_stage_result(
        str(browser_stage_packet_after_setup.get("stageId", "")),
        "partial",
        [
            "local://module-capture-products-create-redacted.json",
            "local://module-capture-classification.json",
        ],
        list(browser_stage_packet_after_setup.get("requiredProof", [])),
        [
            "only one module/action capture is recorded",
            "module capture coverage is incomplete; do not unlock launch or batch stages",
        ],
    )
    simulated_module_capture_partial_result_validation = validate_browser_stage_result(
        simulated_module_capture_partial_result,
        browser_stage_packet_after_setup,
    )
    if not simulated_module_capture_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated module-capture partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_module_capture_partial_result_validation["issues"])
        )
    write_json(simulated_module_capture_partial_result_path, simulated_module_capture_partial_result)

    ledger_after_module_capture_partial = apply_stage_result(
        ledger_after_setup,
        browser_stage_packet_after_setup,
        simulated_module_capture_partial_result,
    )
    ledger_after_module_capture_partial_validation = validate_browser_execution_ledger(ledger_after_module_capture_partial)
    if not ledger_after_module_capture_partial_validation.get("ok"):
        raise ValueError(
            "ledger after module-capture partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_module_capture_partial_validation["issues"])
        )
    write_json(ledger_after_module_capture_partial_path, ledger_after_module_capture_partial)

    capture_plan_gate_coverage = validate_plan_gate_coverage(module_capture_plan)
    if not capture_plan_gate_coverage.get("ok"):
        raise ValueError(
            "capture plan gate coverage validation failed:\n"
            + "\n".join(f"- {issue}" for issue in capture_plan_gate_coverage["issues"])
        )
    write_json(capture_plan_gate_coverage_path, capture_plan_gate_coverage)
    selected_stage = handoff.get("selectedStage") if isinstance(handoff.get("selectedStage"), dict) else {}
    simulated_module_capture_stage_result = build_capture_result(
        str(selected_stage.get("module", "products")),
        str(selected_stage.get("action", "create")),
        "captured",
        [
            "fresh request capture for this exact module/action",
            "redacted payload shape and required id fields",
            "backend state verification",
        ],
        [
            "local://module-capture-products-create-request.json",
            "local://module-capture-products-create-backend-state.json",
        ],
        [],
    )
    write_json(simulated_module_capture_stage_result_path, simulated_module_capture_stage_result)
    module_capture_coverage = update_coverage(module_capture_plan, simulated_module_capture_stage_result)
    module_capture_coverage_validation = validate_coverage(module_capture_coverage, module_capture_plan)
    if not module_capture_coverage_validation.get("ok"):
        raise ValueError(
            "module capture coverage validation failed:\n"
            + "\n".join(f"- {issue}" for issue in module_capture_coverage_validation["issues"])
        )
    write_json(module_capture_coverage_path, module_capture_coverage)
    ledger_after_module_capture_coverage_sync = sync_ledger_with_coverage(
        ledger_after_module_capture_partial,
        module_capture_coverage,
    )
    ledger_after_module_capture_coverage_sync_validation = validate_browser_execution_ledger(
        ledger_after_module_capture_coverage_sync
    )
    if not ledger_after_module_capture_coverage_sync_validation.get("ok"):
        raise ValueError(
            "ledger after module-capture coverage sync validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_module_capture_coverage_sync_validation["issues"])
        )
    write_json(ledger_after_module_capture_coverage_sync_path, ledger_after_module_capture_coverage_sync)

    module_capture_coverage_complete = build_complete_module_capture_coverage(
        module_capture_plan,
        module_capture_coverage,
    )
    module_capture_coverage_complete_validation = validate_coverage(module_capture_coverage_complete, module_capture_plan)
    if not module_capture_coverage_complete_validation.get("ok"):
        raise ValueError(
            "complete module capture coverage validation failed:\n"
            + "\n".join(f"- {issue}" for issue in module_capture_coverage_complete_validation["issues"])
        )
    write_json(module_capture_coverage_complete_path, module_capture_coverage_complete)
    ledger_after_module_capture_complete = sync_ledger_with_coverage(
        ledger_after_module_capture_coverage_sync,
        module_capture_coverage_complete,
    )
    ledger_after_module_capture_complete_validation = validate_browser_execution_ledger(ledger_after_module_capture_complete)
    if not ledger_after_module_capture_complete_validation.get("ok"):
        raise ValueError(
            "ledger after complete module-capture validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_module_capture_complete_validation["issues"])
        )
    write_json(ledger_after_module_capture_complete_path, ledger_after_module_capture_complete)
    browser_stage_packet_after_module_capture_complete = build_packet_for_paths(ledger_after_module_capture_complete, ledger_after_module_capture_complete_path, browser_stage_packet_after_module_capture_complete_path)
    browser_stage_packet_after_module_capture_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_module_capture_complete
    )
    if not browser_stage_packet_after_module_capture_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after complete module-capture validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_module_capture_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_module_capture_complete_path, browser_stage_packet_after_module_capture_complete)

    simulated_theme_launch_partial_result = build_stage_result(
        str(browser_stage_packet_after_module_capture_complete.get("stageId", "")),
        "partial",
        [
            "local://theme-active-proof.json",
            "local://page-published-proof.json",
            "local://launch-readiness-partial.json",
        ],
        [
            "active theme",
            "published pages",
        ],
        [
            "enabled pages, bound routes, frontend HTTP, and frontend DOM proof are still missing",
        ],
    )
    simulated_theme_launch_partial_result_validation = validate_browser_stage_result(
        simulated_theme_launch_partial_result,
        browser_stage_packet_after_module_capture_complete,
    )
    if not simulated_theme_launch_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated theme-launch partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_theme_launch_partial_result_validation["issues"])
        )
    write_json(simulated_theme_launch_partial_result_path, simulated_theme_launch_partial_result)

    ledger_after_theme_launch_partial = apply_stage_result(
        ledger_after_module_capture_complete,
        browser_stage_packet_after_module_capture_complete,
        simulated_theme_launch_partial_result,
    )
    ledger_after_theme_launch_partial_validation = validate_browser_execution_ledger(ledger_after_theme_launch_partial)
    if not ledger_after_theme_launch_partial_validation.get("ok"):
        raise ValueError(
            "ledger after theme-launch partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_theme_launch_partial_validation["issues"])
        )
    write_json(ledger_after_theme_launch_partial_path, ledger_after_theme_launch_partial)

    browser_stage_packet_after_theme_launch_partial_recovery = build_packet_for_paths(
        ledger_after_theme_launch_partial,
        ledger_after_theme_launch_partial_path,
        browser_stage_packet_after_theme_launch_partial_recovery_path,
        str(browser_stage_packet_after_module_capture_complete.get("stageId", "")),
    )
    browser_stage_packet_after_theme_launch_partial_recovery_validation = validate_browser_stage_packet(
        browser_stage_packet_after_theme_launch_partial_recovery
    )
    if not browser_stage_packet_after_theme_launch_partial_recovery_validation.get("ok"):
        raise ValueError(
            "browser stage packet after theme-launch partial recovery validation failed:\n"
            + "\n".join(
                f"- {issue}" for issue in browser_stage_packet_after_theme_launch_partial_recovery_validation["issues"]
            )
        )
    write_json(
        browser_stage_packet_after_theme_launch_partial_recovery_path,
        browser_stage_packet_after_theme_launch_partial_recovery,
    )

    simulated_theme_launch_complete_result = build_stage_result(
        str(browser_stage_packet_after_theme_launch_partial_recovery.get("stageId", "")),
        "completed",
        [
            "local://launch-readiness-complete.json",
            "local://frontend-static-dom-audit.json",
            "local://route-binding-proof.json",
        ],
        list(browser_stage_packet_after_module_capture_complete.get("requiredProof", [])),
        [],
        True,
    )
    simulated_theme_launch_complete_result_validation = validate_browser_stage_result(
        simulated_theme_launch_complete_result,
        browser_stage_packet_after_theme_launch_partial_recovery,
    )
    if not simulated_theme_launch_complete_result_validation.get("ok"):
        raise ValueError(
            "simulated theme-launch complete result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_theme_launch_complete_result_validation["issues"])
        )
    write_json(simulated_theme_launch_complete_result_path, simulated_theme_launch_complete_result)

    ledger_after_theme_launch_recovery_complete = apply_stage_result(
        ledger_after_theme_launch_partial,
        browser_stage_packet_after_theme_launch_partial_recovery,
        simulated_theme_launch_complete_result,
    )
    ledger_after_theme_launch_recovery_complete_validation = validate_browser_execution_ledger(
        ledger_after_theme_launch_recovery_complete
    )
    if not ledger_after_theme_launch_recovery_complete_validation.get("ok"):
        raise ValueError(
            "ledger after theme-launch recovery complete validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_theme_launch_recovery_complete_validation["issues"])
        )
    write_json(ledger_after_theme_launch_recovery_complete_path, ledger_after_theme_launch_recovery_complete)
    ledger_after_theme_launch_complete = ledger_after_theme_launch_recovery_complete
    ledger_after_theme_launch_complete_validation = validate_browser_execution_ledger(ledger_after_theme_launch_complete)
    if not ledger_after_theme_launch_complete_validation.get("ok"):
        raise ValueError(
            "ledger after theme-launch complete validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_theme_launch_complete_validation["issues"])
        )
    write_json(ledger_after_theme_launch_complete_path, ledger_after_theme_launch_complete)
    browser_stage_packet_after_theme_launch_complete = build_packet_for_paths(ledger_after_theme_launch_complete, ledger_after_theme_launch_complete_path, browser_stage_packet_after_theme_launch_complete_path)
    browser_stage_packet_after_theme_launch_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_theme_launch_complete
    )
    if not browser_stage_packet_after_theme_launch_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after theme launch validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_theme_launch_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_theme_launch_complete_path, browser_stage_packet_after_theme_launch_complete)

    simulated_static_audit_partial_result = build_stage_result(
        str(browser_stage_packet_after_theme_launch_complete.get("stageId", "")),
        "partial",
        [
            "local://static-audit-home-only.json",
            "local://static-audit-blockers.json",
        ],
        [
            "expected status map",
            "redacted frontend audit",
        ],
        [
            "frontendRendering evidence is incomplete; one or more static routes still have blocking issues",
        ],
    )
    simulated_static_audit_partial_result_validation = validate_browser_stage_result(
        simulated_static_audit_partial_result,
        browser_stage_packet_after_theme_launch_complete,
    )
    if not simulated_static_audit_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated static-audit partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_static_audit_partial_result_validation["issues"])
        )
    write_json(simulated_static_audit_partial_result_path, simulated_static_audit_partial_result)

    ledger_after_static_audit_partial = apply_stage_result(
        ledger_after_theme_launch_complete,
        browser_stage_packet_after_theme_launch_complete,
        simulated_static_audit_partial_result,
    )
    ledger_after_static_audit_partial_validation = validate_browser_execution_ledger(ledger_after_static_audit_partial)
    if not ledger_after_static_audit_partial_validation.get("ok"):
        raise ValueError(
            "ledger after static-audit partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_static_audit_partial_validation["issues"])
        )
    write_json(ledger_after_static_audit_partial_path, ledger_after_static_audit_partial)

    simulated_static_audit_complete_result = build_stage_result(
        str(browser_stage_packet_after_theme_launch_complete.get("stageId", "")),
        "completed",
        [
            "local://static-expected-status-map.json",
            "local://static-frontend-audit-redacted.json",
            "local://frontend-rendering-evidence.json",
        ],
        list(browser_stage_packet_after_theme_launch_complete.get("requiredProof", [])),
        [],
    )
    (
        browser_stage_packet_after_static_audit_partial_recovery,
        browser_stage_packet_after_static_audit_partial_recovery_validation,
        ledger_after_static_audit_complete,
        ledger_after_static_audit_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_static_audit_partial,
        str(browser_stage_packet_after_theme_launch_complete.get("stageId", "")),
        simulated_static_audit_complete_result,
        "static-audit",
        ledger_after_static_audit_partial_path,
        browser_stage_packet_after_static_audit_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_static_audit_partial_recovery_path,
        browser_stage_packet_after_static_audit_partial_recovery,
    )
    simulated_static_audit_complete_result_validation = validate_browser_stage_result(
        simulated_static_audit_complete_result,
        browser_stage_packet_after_static_audit_partial_recovery,
    )
    write_json(simulated_static_audit_complete_result_path, simulated_static_audit_complete_result)
    write_json(ledger_after_static_audit_complete_path, ledger_after_static_audit_complete)
    browser_stage_packet_after_static_audit_complete = build_packet_for_paths(ledger_after_static_audit_complete, ledger_after_static_audit_complete_path, browser_stage_packet_after_static_audit_complete_path)
    browser_stage_packet_after_static_audit_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_static_audit_complete
    )
    if not browser_stage_packet_after_static_audit_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after static audit validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_static_audit_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_static_audit_complete_path, browser_stage_packet_after_static_audit_complete)

    simulated_content_probe_partial_result = build_stage_result(
        str(browser_stage_packet_after_static_audit_complete.get("stageId", "")),
        "partial",
        [
            "local://content-probe-authorization-record.json",
            "local://content-probe-naming-proof.json",
        ],
        [
            "content-type-specific authorization",
            "probe/test naming proof",
        ],
        [
            "backend draft proof is missing; do not unlock save_request_capture",
        ],
    )
    simulated_content_probe_partial_result_validation = validate_browser_stage_result(
        simulated_content_probe_partial_result,
        browser_stage_packet_after_static_audit_complete,
    )
    if not simulated_content_probe_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated content-probe partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_content_probe_partial_result_validation["issues"])
        )
    write_json(simulated_content_probe_partial_result_path, simulated_content_probe_partial_result)

    ledger_after_content_probe_partial = apply_stage_result(
        ledger_after_static_audit_complete,
        browser_stage_packet_after_static_audit_complete,
        simulated_content_probe_partial_result,
    )
    ledger_after_content_probe_partial_validation = validate_browser_execution_ledger(ledger_after_content_probe_partial)
    if not ledger_after_content_probe_partial_validation.get("ok"):
        raise ValueError(
            "ledger after content-probe partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_content_probe_partial_validation["issues"])
        )
    write_json(ledger_after_content_probe_partial_path, ledger_after_content_probe_partial)

    simulated_content_probe_complete_result = build_stage_result(
        str(browser_stage_packet_after_static_audit_complete.get("stageId", "")),
        "completed",
        [
            "local://content-probe-authorization-record.json",
            "local://content-probe-draft-row.json",
            "local://content-probe-edit-url.json",
        ],
        list(browser_stage_packet_after_static_audit_complete.get("requiredProof", [])),
        [],
        True,
    )
    (
        browser_stage_packet_after_content_probe_partial_recovery,
        browser_stage_packet_after_content_probe_partial_recovery_validation,
        ledger_after_content_probe_complete,
        ledger_after_content_probe_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_content_probe_partial,
        str(browser_stage_packet_after_static_audit_complete.get("stageId", "")),
        simulated_content_probe_complete_result,
        "content-probe",
        ledger_after_content_probe_partial_path,
        browser_stage_packet_after_content_probe_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_content_probe_partial_recovery_path,
        browser_stage_packet_after_content_probe_partial_recovery,
    )
    simulated_content_probe_complete_result_validation = validate_browser_stage_result(
        simulated_content_probe_complete_result,
        browser_stage_packet_after_content_probe_partial_recovery,
    )
    write_json(simulated_content_probe_complete_result_path, simulated_content_probe_complete_result)
    write_json(ledger_after_content_probe_complete_path, ledger_after_content_probe_complete)
    browser_stage_packet_after_content_probe_complete = build_packet_for_paths(ledger_after_content_probe_complete, ledger_after_content_probe_complete_path, browser_stage_packet_after_content_probe_complete_path)
    browser_stage_packet_after_content_probe_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_content_probe_complete
    )
    if not browser_stage_packet_after_content_probe_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after content probe validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_content_probe_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_content_probe_complete_path, browser_stage_packet_after_content_probe_complete)

    simulated_save_request_partial_result = build_stage_result(
        str(browser_stage_packet_after_content_probe_complete.get("stageId", "")),
        "partial",
        [
            "local://save-request-url-method-headers.json",
            "local://save-request-payload-shape.json",
        ],
        [
            "request URL",
            "method",
            "required headers",
            "payloadTemplate",
        ],
        [
            "fieldMapping and backend persistence proof are still missing; do not unlock publish or manifest stages",
        ],
    )
    simulated_save_request_partial_result_validation = validate_browser_stage_result(
        simulated_save_request_partial_result,
        browser_stage_packet_after_content_probe_complete,
    )
    if not simulated_save_request_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated save-request partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_save_request_partial_result_validation["issues"])
        )
    write_json(simulated_save_request_partial_result_path, simulated_save_request_partial_result)

    ledger_after_save_request_partial = apply_stage_result(
        ledger_after_content_probe_complete,
        browser_stage_packet_after_content_probe_complete,
        simulated_save_request_partial_result,
    )
    ledger_after_save_request_partial_validation = validate_browser_execution_ledger(ledger_after_save_request_partial)
    if not ledger_after_save_request_partial_validation.get("ok"):
        raise ValueError(
            "ledger after save-request partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_save_request_partial_validation["issues"])
        )
    write_json(ledger_after_save_request_partial_path, ledger_after_save_request_partial)

    simulated_save_request_complete_result = build_stage_result(
        str(browser_stage_packet_after_content_probe_complete.get("stageId", "")),
        "completed",
        [
            "local://save-request-url-method-headers.json",
            "local://save-request-payload-template.json",
            "local://save-request-field-mapping.json",
            "local://save-request-backend-persistence-proof.json",
        ],
        list(browser_stage_packet_after_content_probe_complete.get("requiredProof", [])),
        [],
        True,
    )
    (
        browser_stage_packet_after_save_request_partial_recovery,
        browser_stage_packet_after_save_request_partial_recovery_validation,
        ledger_after_save_request_complete,
        ledger_after_save_request_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_save_request_partial,
        str(browser_stage_packet_after_content_probe_complete.get("stageId", "")),
        simulated_save_request_complete_result,
        "save-request",
        ledger_after_save_request_partial_path,
        browser_stage_packet_after_save_request_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_save_request_partial_recovery_path,
        browser_stage_packet_after_save_request_partial_recovery,
    )
    simulated_save_request_complete_result_validation = validate_browser_stage_result(
        simulated_save_request_complete_result,
        browser_stage_packet_after_save_request_partial_recovery,
    )
    write_json(simulated_save_request_complete_result_path, simulated_save_request_complete_result)
    write_json(ledger_after_save_request_complete_path, ledger_after_save_request_complete)
    browser_stage_packet_after_save_request_complete = build_packet_for_paths(ledger_after_save_request_complete, ledger_after_save_request_complete_path, browser_stage_packet_after_save_request_complete_path)
    browser_stage_packet_after_save_request_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_save_request_complete
    )
    if not browser_stage_packet_after_save_request_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after save request validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_save_request_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_save_request_complete_path, browser_stage_packet_after_save_request_complete)

    simulated_publish_sample_partial_result = build_stage_result(
        str(browser_stage_packet_after_save_request_complete.get("stageId", "")),
        "partial",
        [
            "local://publish-sample-backend-status.json",
            "local://publish-sample-frontend-status.json",
        ],
        [
            "backend published status",
            "frontend detail 200",
        ],
        [
            "title/name, cover/media, and structured body proof are still missing; do not unlock batch upload",
        ],
    )
    simulated_publish_sample_partial_result_validation = validate_browser_stage_result(
        simulated_publish_sample_partial_result,
        browser_stage_packet_after_save_request_complete,
    )
    if not simulated_publish_sample_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated publish-sample partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_publish_sample_partial_result_validation["issues"])
        )
    write_json(simulated_publish_sample_partial_result_path, simulated_publish_sample_partial_result)

    ledger_after_publish_sample_partial = apply_stage_result(
        ledger_after_save_request_complete,
        browser_stage_packet_after_save_request_complete,
        simulated_publish_sample_partial_result,
    )
    ledger_after_publish_sample_partial_validation = validate_browser_execution_ledger(ledger_after_publish_sample_partial)
    if not ledger_after_publish_sample_partial_validation.get("ok"):
        raise ValueError(
            "ledger after publish-sample partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_publish_sample_partial_validation["issues"])
        )
    write_json(ledger_after_publish_sample_partial_path, ledger_after_publish_sample_partial)

    simulated_publish_sample_complete_result = build_stage_result(
        str(browser_stage_packet_after_save_request_complete.get("stageId", "")),
        "completed",
        [
            "local://publish-sample-backend-status.json",
            "local://publish-sample-frontend-detail-200.json",
            "local://publish-sample-title-cover-body.json",
        ],
        list(browser_stage_packet_after_save_request_complete.get("requiredProof", [])),
        [],
    )
    (
        browser_stage_packet_after_publish_sample_partial_recovery,
        browser_stage_packet_after_publish_sample_partial_recovery_validation,
        ledger_after_publish_sample_complete,
        ledger_after_publish_sample_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_publish_sample_partial,
        str(browser_stage_packet_after_save_request_complete.get("stageId", "")),
        simulated_publish_sample_complete_result,
        "publish-sample",
        ledger_after_publish_sample_partial_path,
        browser_stage_packet_after_publish_sample_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_publish_sample_partial_recovery_path,
        browser_stage_packet_after_publish_sample_partial_recovery,
    )
    simulated_publish_sample_complete_result_validation = validate_browser_stage_result(
        simulated_publish_sample_complete_result,
        browser_stage_packet_after_publish_sample_partial_recovery,
    )
    write_json(simulated_publish_sample_complete_result_path, simulated_publish_sample_complete_result)
    write_json(ledger_after_publish_sample_complete_path, ledger_after_publish_sample_complete)
    browser_stage_packet_after_publish_sample_complete = build_packet_for_paths(ledger_after_publish_sample_complete, ledger_after_publish_sample_complete_path, browser_stage_packet_after_publish_sample_complete_path)
    browser_stage_packet_after_publish_sample_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_publish_sample_complete
    )
    if not browser_stage_packet_after_publish_sample_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after publish sample validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_publish_sample_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_publish_sample_complete_path, browser_stage_packet_after_publish_sample_complete)

    simulated_manifest_gate_partial_result = build_stage_result(
        str(browser_stage_packet_after_publish_sample_complete.get("stageId", "")),
        "partial",
        [
            str(source_input_requirements_path),
            "local://manifest-generic-validation-pass.json",
        ],
        [
            "source input requirements generated",
            "validate_manifest.py pass",
        ],
        [
            "schema-verified validation is still missing; do not unlock batch upload",
        ],
    )
    simulated_manifest_gate_partial_result_validation = validate_browser_stage_result(
        simulated_manifest_gate_partial_result,
        browser_stage_packet_after_publish_sample_complete,
    )
    if not simulated_manifest_gate_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated manifest-gate partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_manifest_gate_partial_result_validation["issues"])
        )
    write_json(simulated_manifest_gate_partial_result_path, simulated_manifest_gate_partial_result)

    ledger_after_manifest_gate_partial = apply_stage_result(
        ledger_after_publish_sample_complete,
        browser_stage_packet_after_publish_sample_complete,
        simulated_manifest_gate_partial_result,
    )
    ledger_after_manifest_gate_partial_validation = validate_browser_execution_ledger(ledger_after_manifest_gate_partial)
    if not ledger_after_manifest_gate_partial_validation.get("ok"):
        raise ValueError(
            "ledger after manifest-gate partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_manifest_gate_partial_validation["issues"])
        )
    write_json(ledger_after_manifest_gate_partial_path, ledger_after_manifest_gate_partial)

    simulated_manifest_gate_complete_result = build_stage_result(
        str(browser_stage_packet_after_publish_sample_complete.get("stageId", "")),
        "completed",
        [
            str(source_input_requirements_path),
            "local://manifest-generic-validation-pass.json",
            "local://manifest-require-schema-verified-pass.json",
        ],
        list(browser_stage_packet_after_publish_sample_complete.get("requiredProof", [])),
        [],
    )
    (
        browser_stage_packet_after_manifest_gate_partial_recovery,
        browser_stage_packet_after_manifest_gate_partial_recovery_validation,
        ledger_after_manifest_gate_complete,
        ledger_after_manifest_gate_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_manifest_gate_partial,
        str(browser_stage_packet_after_publish_sample_complete.get("stageId", "")),
        simulated_manifest_gate_complete_result,
        "manifest-gate",
        ledger_after_manifest_gate_partial_path,
        browser_stage_packet_after_manifest_gate_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_manifest_gate_partial_recovery_path,
        browser_stage_packet_after_manifest_gate_partial_recovery,
    )
    simulated_manifest_gate_complete_result_validation = validate_browser_stage_result(
        simulated_manifest_gate_complete_result,
        browser_stage_packet_after_manifest_gate_partial_recovery,
    )
    write_json(simulated_manifest_gate_complete_result_path, simulated_manifest_gate_complete_result)
    write_json(ledger_after_manifest_gate_complete_path, ledger_after_manifest_gate_complete)
    browser_stage_packet_after_manifest_gate_complete = build_packet_for_paths(ledger_after_manifest_gate_complete, ledger_after_manifest_gate_complete_path, browser_stage_packet_after_manifest_gate_complete_path)
    browser_stage_packet_after_manifest_gate_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_manifest_gate_complete
    )
    if not browser_stage_packet_after_manifest_gate_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after manifest gate validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_manifest_gate_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_manifest_gate_complete_path, browser_stage_packet_after_manifest_gate_complete)

    simulated_batch_upload_partial_result = build_stage_result(
        str(browser_stage_packet_after_manifest_gate_complete.get("stageId", "")),
        "partial",
        [
            "local://batch-upload-progress-partial.json",
            "local://batch-upload-some-frontend-audits.json",
        ],
        [
            "schema gate pass",
            "sample verification pass",
            "progress log",
        ],
        [
            "frontend detail audit for each uploaded route is incomplete; do not unlock forms/media/settings",
        ],
    )
    simulated_batch_upload_partial_result_validation = validate_browser_stage_result(
        simulated_batch_upload_partial_result,
        browser_stage_packet_after_manifest_gate_complete,
    )
    if not simulated_batch_upload_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated batch-upload partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_batch_upload_partial_result_validation["issues"])
        )
    write_json(simulated_batch_upload_partial_result_path, simulated_batch_upload_partial_result)

    ledger_after_batch_upload_partial = apply_stage_result(
        ledger_after_manifest_gate_complete,
        browser_stage_packet_after_manifest_gate_complete,
        simulated_batch_upload_partial_result,
    )
    ledger_after_batch_upload_partial_validation = validate_browser_execution_ledger(ledger_after_batch_upload_partial)
    if not ledger_after_batch_upload_partial_validation.get("ok"):
        raise ValueError(
            "ledger after batch-upload partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_batch_upload_partial_validation["issues"])
        )
    write_json(ledger_after_batch_upload_partial_path, ledger_after_batch_upload_partial)

    simulated_batch_upload_complete_result = build_stage_result(
        str(browser_stage_packet_after_manifest_gate_complete.get("stageId", "")),
        "completed",
        [
            "local://batch-upload-schema-gate-pass.json",
            "local://batch-upload-sample-verification-pass.json",
            "local://batch-upload-progress-log.json",
            "local://batch-upload-all-frontend-detail-audits.json",
        ],
        list(browser_stage_packet_after_manifest_gate_complete.get("requiredProof", [])),
        [],
        True,
    )
    (
        browser_stage_packet_after_batch_upload_partial_recovery,
        browser_stage_packet_after_batch_upload_partial_recovery_validation,
        ledger_after_batch_upload_complete,
        ledger_after_batch_upload_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_batch_upload_partial,
        str(browser_stage_packet_after_manifest_gate_complete.get("stageId", "")),
        simulated_batch_upload_complete_result,
        "batch-upload",
        ledger_after_batch_upload_partial_path,
        browser_stage_packet_after_batch_upload_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_batch_upload_partial_recovery_path,
        browser_stage_packet_after_batch_upload_partial_recovery,
    )
    simulated_batch_upload_complete_result_validation = validate_browser_stage_result(
        simulated_batch_upload_complete_result,
        browser_stage_packet_after_batch_upload_partial_recovery,
    )
    write_json(simulated_batch_upload_complete_result_path, simulated_batch_upload_complete_result)
    write_json(ledger_after_batch_upload_complete_path, ledger_after_batch_upload_complete)
    browser_stage_packet_after_batch_upload_complete = build_packet_for_paths(ledger_after_batch_upload_complete, ledger_after_batch_upload_complete_path, browser_stage_packet_after_batch_upload_complete_path)
    browser_stage_packet_after_batch_upload_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_batch_upload_complete
    )
    if not browser_stage_packet_after_batch_upload_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after batch upload validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_batch_upload_complete_validation["issues"])
        )
    write_json(browser_stage_packet_after_batch_upload_complete_path, browser_stage_packet_after_batch_upload_complete)

    simulated_forms_media_settings_partial_result = build_stage_result(
        str(browser_stage_packet_after_batch_upload_complete.get("stageId", "")),
        "partial",
        [
            "local://forms-media-settings-action-request-capture.json",
            "local://forms-media-settings-backend-proof.json",
        ],
        [
            "action-specific request capture",
            "backend persisted proof",
        ],
        [
            "public or integration effect proof is missing where applicable; do not unlock final frontend audit",
        ],
    )
    simulated_forms_media_settings_partial_result_validation = validate_browser_stage_result(
        simulated_forms_media_settings_partial_result,
        browser_stage_packet_after_batch_upload_complete,
    )
    if not simulated_forms_media_settings_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated forms-media-settings partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_forms_media_settings_partial_result_validation["issues"])
        )
    write_json(simulated_forms_media_settings_partial_result_path, simulated_forms_media_settings_partial_result)

    ledger_after_forms_media_settings_partial = apply_stage_result(
        ledger_after_batch_upload_complete,
        browser_stage_packet_after_batch_upload_complete,
        simulated_forms_media_settings_partial_result,
    )
    ledger_after_forms_media_settings_partial_validation = validate_browser_execution_ledger(
        ledger_after_forms_media_settings_partial
    )
    if not ledger_after_forms_media_settings_partial_validation.get("ok"):
        raise ValueError(
            "ledger after forms-media-settings partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_forms_media_settings_partial_validation["issues"])
        )
    write_json(ledger_after_forms_media_settings_partial_path, ledger_after_forms_media_settings_partial)

    simulated_forms_media_settings_complete_result = build_stage_result(
        str(browser_stage_packet_after_batch_upload_complete.get("stageId", "")),
        "completed",
        [
            "local://forms-media-settings-action-request-capture.json",
            "local://forms-media-settings-backend-persisted-proof.json",
            "local://forms-media-settings-public-integration-effect-proof.json",
        ],
        list(browser_stage_packet_after_batch_upload_complete.get("requiredProof", [])),
        [],
        True,
    )
    (
        browser_stage_packet_after_forms_media_settings_partial_recovery,
        browser_stage_packet_after_forms_media_settings_partial_recovery_validation,
        ledger_after_forms_media_settings_complete,
        ledger_after_forms_media_settings_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_forms_media_settings_partial,
        str(browser_stage_packet_after_batch_upload_complete.get("stageId", "")),
        simulated_forms_media_settings_complete_result,
        "forms-media-settings",
        ledger_after_forms_media_settings_partial_path,
        browser_stage_packet_after_forms_media_settings_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_forms_media_settings_partial_recovery_path,
        browser_stage_packet_after_forms_media_settings_partial_recovery,
    )
    simulated_forms_media_settings_complete_result_validation = validate_browser_stage_result(
        simulated_forms_media_settings_complete_result,
        browser_stage_packet_after_forms_media_settings_partial_recovery,
    )
    write_json(simulated_forms_media_settings_complete_result_path, simulated_forms_media_settings_complete_result)
    write_json(ledger_after_forms_media_settings_complete_path, ledger_after_forms_media_settings_complete)
    browser_stage_packet_after_forms_media_settings_complete = build_packet_for_paths(
        ledger_after_forms_media_settings_complete,
        ledger_after_forms_media_settings_complete_path,
        browser_stage_packet_after_forms_media_settings_complete_path,
    )
    browser_stage_packet_after_forms_media_settings_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_forms_media_settings_complete
    )
    if not browser_stage_packet_after_forms_media_settings_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after forms/media/settings validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_forms_media_settings_complete_validation["issues"])
        )
    write_json(
        browser_stage_packet_after_forms_media_settings_complete_path,
        browser_stage_packet_after_forms_media_settings_complete,
    )

    simulated_final_audit_inputs_summary = {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "contentType": args.content_type,
        "staticRouteCount": 1,
        "detailRouteCount": 1,
        "detailRouteInstances": [f"{args.content_type}-detail-1"],
        "routePatterns": [f"/{args.content_type}", f"/{args.content_type}/{{slug}}"],
        "expectedStatus": 200,
        "warning": "Simulated final audit inputs for local rehearsal only.",
    }
    simulated_final_audit_expected_statuses = {
        f"https://simsite01.web.allincms.com/{args.content_type}": 200,
        f"https://simsite01.web.allincms.com/{args.content_type}/{args.simulated_slug}": 200,
    }
    simulated_final_audit_complete_report = [
        {
            "url": f"/{args.content_type}",
            "urlFingerprint": final_audit_url_fingerprint(f"https://simsite01.web.allincms.com/{args.content_type}"),
            "routeInstance": f"route-{args.content_type}-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "strong": 2, "table": 1, "img": 2, "a": 4},
            "headings": {"h1": ["redacted-h1-1"], "h2": ["redacted-h2-1"], "h3": []},
            "imageCount": 2,
            "linkCount": 4,
            "issues": [],
        },
        {
            "url": f"/{args.content_type}/{{slug}}",
            "urlFingerprint": final_audit_url_fingerprint(
                f"https://simsite01.web.allincms.com/{args.content_type}/{args.simulated_slug}"
            ),
            "routeInstance": f"{args.content_type}-detail-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "strong": 1, "table": 1, "img": 1, "a": 3},
            "headings": {"h1": ["redacted-h1-1"], "h2": ["redacted-h2-1"], "h3": []},
            "imageCount": 1,
            "linkCount": 3,
            "issues": [],
        },
    ]
    simulated_final_audit_partial_report = simulated_final_audit_complete_report[:1]
    write_json(simulated_final_frontend_audit_inputs_summary_path, simulated_final_audit_inputs_summary)
    write_json(simulated_final_frontend_audit_expected_statuses_path, simulated_final_audit_expected_statuses)
    simulated_final_frontend_audit_partial_report_path.write_text(
        json.dumps(simulated_final_audit_partial_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    simulated_final_frontend_audit_complete_report_path.write_text(
        json.dumps(simulated_final_audit_complete_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    simulated_final_frontend_audit_partial_result = build_final_frontend_audit_stage_result(
        browser_stage_packet_after_forms_media_settings_complete,
        simulated_final_frontend_audit_partial_report_path,
        [
            "local://simulated-final-audit-report-missing-detail.json",
            "local://simulated-final-audit-inputs-summary.json",
            "local://simulated-final-expected-statuses.json",
        ],
        False,
        simulated_final_audit_inputs_summary,
        simulated_final_audit_expected_statuses,
    )
    simulated_final_frontend_audit_partial_result_validation = validate_browser_stage_result(
        simulated_final_frontend_audit_partial_result,
        browser_stage_packet_after_forms_media_settings_complete,
    )
    if not simulated_final_frontend_audit_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated final-frontend-audit partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_final_frontend_audit_partial_result_validation["issues"])
        )
    write_json(simulated_final_frontend_audit_partial_result_path, simulated_final_frontend_audit_partial_result)

    ledger_after_final_frontend_audit_partial = apply_stage_result(
        ledger_after_forms_media_settings_complete,
        browser_stage_packet_after_forms_media_settings_complete,
        simulated_final_frontend_audit_partial_result,
    )
    ledger_after_final_frontend_audit_partial_validation = validate_browser_execution_ledger(
        ledger_after_final_frontend_audit_partial
    )
    if not ledger_after_final_frontend_audit_partial_validation.get("ok"):
        raise ValueError(
            "ledger after final-frontend-audit partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_final_frontend_audit_partial_validation["issues"])
        )
    write_json(ledger_after_final_frontend_audit_partial_path, ledger_after_final_frontend_audit_partial)

    simulated_final_frontend_audit_complete_result = build_final_frontend_audit_stage_result(
        browser_stage_packet_after_forms_media_settings_complete,
        simulated_final_frontend_audit_complete_report_path,
        [
            "local://simulated-final-audit-report-complete.json",
            "local://simulated-final-audit-inputs-summary.json",
            "local://simulated-final-expected-statuses.json",
        ],
        False,
        simulated_final_audit_inputs_summary,
        simulated_final_audit_expected_statuses,
    )
    (
        browser_stage_packet_after_final_frontend_audit_partial_recovery,
        browser_stage_packet_after_final_frontend_audit_partial_recovery_validation,
        ledger_after_final_frontend_audit_complete,
        ledger_after_final_frontend_audit_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_final_frontend_audit_partial,
        str(browser_stage_packet_after_forms_media_settings_complete.get("stageId", "")),
        simulated_final_frontend_audit_complete_result,
        "final-frontend-audit",
        ledger_after_final_frontend_audit_partial_path,
        browser_stage_packet_after_final_frontend_audit_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_final_frontend_audit_partial_recovery_path,
        browser_stage_packet_after_final_frontend_audit_partial_recovery,
    )
    simulated_final_frontend_audit_complete_result_validation = validate_browser_stage_result(
        simulated_final_frontend_audit_complete_result,
        browser_stage_packet_after_final_frontend_audit_partial_recovery,
    )
    write_json(simulated_final_frontend_audit_complete_result_path, simulated_final_frontend_audit_complete_result)
    write_json(ledger_after_final_frontend_audit_complete_path, ledger_after_final_frontend_audit_complete)
    browser_stage_packet_after_final_frontend_audit_complete = build_packet_for_paths(
        ledger_after_final_frontend_audit_complete,
        ledger_after_final_frontend_audit_complete_path,
        browser_stage_packet_after_final_frontend_audit_complete_path,
    )
    browser_stage_packet_after_final_frontend_audit_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_final_frontend_audit_complete
    )
    if not browser_stage_packet_after_final_frontend_audit_complete_validation.get("ok"):
        raise ValueError(
            "browser stage packet after final frontend audit validation failed:\n"
            + "\n".join(f"- {issue}" for issue in browser_stage_packet_after_final_frontend_audit_complete_validation["issues"])
        )
    write_json(
        browser_stage_packet_after_final_frontend_audit_complete_path,
        browser_stage_packet_after_final_frontend_audit_complete,
    )

    simulated_cleanup_probes_partial_result = build_stage_result(
        str(browser_stage_packet_after_final_frontend_audit_complete.get("stageId", "")),
        "partial",
        [
            "local://cleanup-authorization-record.json",
            "local://cleanup-candidate-list.json",
        ],
        [
            "cleanup authorization",
            "candidate list",
        ],
        [
            "backend cleanup proof and frontend non-public proof are still missing",
        ],
    )
    simulated_cleanup_probes_partial_result_validation = validate_browser_stage_result(
        simulated_cleanup_probes_partial_result,
        browser_stage_packet_after_final_frontend_audit_complete,
    )
    if not simulated_cleanup_probes_partial_result_validation.get("ok"):
        raise ValueError(
            "simulated cleanup-probes partial result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in simulated_cleanup_probes_partial_result_validation["issues"])
        )
    write_json(simulated_cleanup_probes_partial_result_path, simulated_cleanup_probes_partial_result)

    ledger_after_cleanup_probes_partial = apply_stage_result(
        ledger_after_final_frontend_audit_complete,
        browser_stage_packet_after_final_frontend_audit_complete,
        simulated_cleanup_probes_partial_result,
    )
    ledger_after_cleanup_probes_partial_validation = validate_browser_execution_ledger(ledger_after_cleanup_probes_partial)
    if not ledger_after_cleanup_probes_partial_validation.get("ok"):
        raise ValueError(
            "ledger after cleanup-probes partial validation failed:\n"
            + "\n".join(f"- {issue}" for issue in ledger_after_cleanup_probes_partial_validation["issues"])
        )
    write_json(ledger_after_cleanup_probes_partial_path, ledger_after_cleanup_probes_partial)

    simulated_cleanup_probes_complete_result = build_stage_result(
        str(browser_stage_packet_after_final_frontend_audit_complete.get("stageId", "")),
        "completed",
        [
            "local://cleanup-authorization-record.json",
            "local://cleanup-candidate-list.json",
            "local://cleanup-backend-proof.json",
            "local://cleanup-frontend-non-public-proof.json",
        ],
        list(browser_stage_packet_after_final_frontend_audit_complete.get("requiredProof", [])),
        [],
        True,
    )
    (
        browser_stage_packet_after_cleanup_probes_partial_recovery,
        browser_stage_packet_after_cleanup_probes_partial_recovery_validation,
        ledger_after_cleanup_probes_complete,
        ledger_after_cleanup_probes_complete_validation,
    ) = apply_completed_result_after_partial(
        ledger_after_cleanup_probes_partial,
        str(browser_stage_packet_after_final_frontend_audit_complete.get("stageId", "")),
        simulated_cleanup_probes_complete_result,
        "cleanup-probes",
        ledger_after_cleanup_probes_partial_path,
        browser_stage_packet_after_cleanup_probes_partial_recovery_path,
    )
    write_json(
        browser_stage_packet_after_cleanup_probes_partial_recovery_path,
        browser_stage_packet_after_cleanup_probes_partial_recovery,
    )
    simulated_cleanup_probes_complete_result_validation = validate_browser_stage_result(
        simulated_cleanup_probes_complete_result,
        browser_stage_packet_after_cleanup_probes_partial_recovery,
    )
    write_json(simulated_cleanup_probes_complete_result_path, simulated_cleanup_probes_complete_result)
    write_json(ledger_after_cleanup_probes_complete_path, ledger_after_cleanup_probes_complete)
    try:
        build_packet_for_paths(ledger_after_cleanup_probes_complete, ledger_after_cleanup_probes_complete_path, output_dir / "next-browser-stage-packet-after-cleanup-probes-complete.json")
        final_packet_rejected = False
        final_packet_rejection_reason = ""
    except ValueError as exc:
        final_packet_rejected = True
        final_packet_rejection_reason = str(exc).splitlines()[0]

    summary = {
        "kind": "allincms_full_rehearsal_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "commandsSuppressed": handoff.get("commandsSuppressed"),
        "allowCommandOutput": args.allow_command_output,
        "fullE2EDir": str(full_e2e_dir),
        "handoffPath": str(handoff_path),
        "launchPlanPath": str(launch_plan_path),
        "browserExecutionPlanPath": str(browser_execution_plan_path),
        "browserExecutionLedgerPath": str(browser_execution_ledger_path),
        "browserStagePacketPath": str(browser_stage_packet_path),
        "browserStageEvidenceBundleDir": str(browser_stage_evidence_bundle_dir),
        "browserStageEvidenceManifestPath": str(browser_stage_evidence_manifest_path),
        "simulatedStageResultPath": str(simulated_stage_result_path),
        "ledgerAfterFirstStagePath": str(ledger_after_first_stage_path),
        "browserStagePacketAfterFirstStagePath": str(browser_stage_packet_after_first_stage_path),
        "simulatedCreateSiteResultPath": str(simulated_create_site_result_path),
        "ledgerAfterCreateSitePath": str(ledger_after_create_site_path),
        "browserStagePacketAfterCreateSitePath": str(browser_stage_packet_after_create_site_path),
        "simulatedSetupResultPath": str(simulated_setup_result_path),
        "ledgerAfterSetupPath": str(ledger_after_setup_path),
        "browserStagePacketAfterSetupPath": str(browser_stage_packet_after_setup_path),
        "browserStageModuleCaptureAuthorizationPackagePath": str(browser_stage_module_capture_authorization_package_path),
        "nextBrowserActionHandoffPath": str(next_browser_action_handoff_path),
        "simulatedModuleCapturePartialResultPath": str(simulated_module_capture_partial_result_path),
        "ledgerAfterModuleCapturePartialPath": str(ledger_after_module_capture_partial_path),
        "simulatedModuleCaptureStageResultPath": str(simulated_module_capture_stage_result_path),
        "capturePlanGateCoveragePath": str(capture_plan_gate_coverage_path),
        "moduleCaptureCoveragePath": str(module_capture_coverage_path),
        "ledgerAfterModuleCaptureCoverageSyncPath": str(ledger_after_module_capture_coverage_sync_path),
        "moduleCaptureCoverageCompletePath": str(module_capture_coverage_complete_path),
        "ledgerAfterModuleCaptureCompletePath": str(ledger_after_module_capture_complete_path),
        "browserStagePacketAfterModuleCaptureCompletePath": str(browser_stage_packet_after_module_capture_complete_path),
        "simulatedThemeLaunchPartialResultPath": str(simulated_theme_launch_partial_result_path),
        "ledgerAfterThemeLaunchPartialPath": str(ledger_after_theme_launch_partial_path),
        "browserStagePacketAfterThemeLaunchPartialRecoveryPath": str(
            browser_stage_packet_after_theme_launch_partial_recovery_path
        ),
        "ledgerAfterThemeLaunchRecoveryCompletePath": str(ledger_after_theme_launch_recovery_complete_path),
        "simulatedThemeLaunchCompleteResultPath": str(simulated_theme_launch_complete_result_path),
        "ledgerAfterThemeLaunchCompletePath": str(ledger_after_theme_launch_complete_path),
        "browserStagePacketAfterThemeLaunchCompletePath": str(browser_stage_packet_after_theme_launch_complete_path),
        "simulatedStaticAuditPartialResultPath": str(simulated_static_audit_partial_result_path),
        "ledgerAfterStaticAuditPartialPath": str(ledger_after_static_audit_partial_path),
        "browserStagePacketAfterStaticAuditPartialRecoveryPath": str(
            browser_stage_packet_after_static_audit_partial_recovery_path
        ),
        "simulatedStaticAuditCompleteResultPath": str(simulated_static_audit_complete_result_path),
        "ledgerAfterStaticAuditCompletePath": str(ledger_after_static_audit_complete_path),
        "browserStagePacketAfterStaticAuditCompletePath": str(browser_stage_packet_after_static_audit_complete_path),
        "simulatedContentProbePartialResultPath": str(simulated_content_probe_partial_result_path),
        "ledgerAfterContentProbePartialPath": str(ledger_after_content_probe_partial_path),
        "browserStagePacketAfterContentProbePartialRecoveryPath": str(
            browser_stage_packet_after_content_probe_partial_recovery_path
        ),
        "simulatedContentProbeCompleteResultPath": str(simulated_content_probe_complete_result_path),
        "ledgerAfterContentProbeCompletePath": str(ledger_after_content_probe_complete_path),
        "browserStagePacketAfterContentProbeCompletePath": str(browser_stage_packet_after_content_probe_complete_path),
        "simulatedSaveRequestPartialResultPath": str(simulated_save_request_partial_result_path),
        "ledgerAfterSaveRequestPartialPath": str(ledger_after_save_request_partial_path),
        "browserStagePacketAfterSaveRequestPartialRecoveryPath": str(
            browser_stage_packet_after_save_request_partial_recovery_path
        ),
        "simulatedSaveRequestCompleteResultPath": str(simulated_save_request_complete_result_path),
        "ledgerAfterSaveRequestCompletePath": str(ledger_after_save_request_complete_path),
        "browserStagePacketAfterSaveRequestCompletePath": str(browser_stage_packet_after_save_request_complete_path),
        "simulatedPublishSamplePartialResultPath": str(simulated_publish_sample_partial_result_path),
        "ledgerAfterPublishSamplePartialPath": str(ledger_after_publish_sample_partial_path),
        "browserStagePacketAfterPublishSamplePartialRecoveryPath": str(
            browser_stage_packet_after_publish_sample_partial_recovery_path
        ),
        "simulatedPublishSampleCompleteResultPath": str(simulated_publish_sample_complete_result_path),
        "ledgerAfterPublishSampleCompletePath": str(ledger_after_publish_sample_complete_path),
        "browserStagePacketAfterPublishSampleCompletePath": str(browser_stage_packet_after_publish_sample_complete_path),
        "simulatedManifestGatePartialResultPath": str(simulated_manifest_gate_partial_result_path),
        "ledgerAfterManifestGatePartialPath": str(ledger_after_manifest_gate_partial_path),
        "browserStagePacketAfterManifestGatePartialRecoveryPath": str(
            browser_stage_packet_after_manifest_gate_partial_recovery_path
        ),
        "simulatedManifestGateCompleteResultPath": str(simulated_manifest_gate_complete_result_path),
        "ledgerAfterManifestGateCompletePath": str(ledger_after_manifest_gate_complete_path),
        "browserStagePacketAfterManifestGateCompletePath": str(browser_stage_packet_after_manifest_gate_complete_path),
        "simulatedBatchUploadPartialResultPath": str(simulated_batch_upload_partial_result_path),
        "ledgerAfterBatchUploadPartialPath": str(ledger_after_batch_upload_partial_path),
        "browserStagePacketAfterBatchUploadPartialRecoveryPath": str(
            browser_stage_packet_after_batch_upload_partial_recovery_path
        ),
        "simulatedBatchUploadCompleteResultPath": str(simulated_batch_upload_complete_result_path),
        "ledgerAfterBatchUploadCompletePath": str(ledger_after_batch_upload_complete_path),
        "browserStagePacketAfterBatchUploadCompletePath": str(browser_stage_packet_after_batch_upload_complete_path),
        "simulatedFormsMediaSettingsPartialResultPath": str(simulated_forms_media_settings_partial_result_path),
        "ledgerAfterFormsMediaSettingsPartialPath": str(ledger_after_forms_media_settings_partial_path),
        "browserStagePacketAfterFormsMediaSettingsPartialRecoveryPath": str(
            browser_stage_packet_after_forms_media_settings_partial_recovery_path
        ),
        "simulatedFormsMediaSettingsCompleteResultPath": str(simulated_forms_media_settings_complete_result_path),
        "ledgerAfterFormsMediaSettingsCompletePath": str(ledger_after_forms_media_settings_complete_path),
        "browserStagePacketAfterFormsMediaSettingsCompletePath": str(
            browser_stage_packet_after_forms_media_settings_complete_path
        ),
        "simulatedFinalFrontendAuditPartialResultPath": str(simulated_final_frontend_audit_partial_result_path),
        "simulatedFinalFrontendAuditPartialReportPath": str(simulated_final_frontend_audit_partial_report_path),
        "ledgerAfterFinalFrontendAuditPartialPath": str(ledger_after_final_frontend_audit_partial_path),
        "browserStagePacketAfterFinalFrontendAuditPartialRecoveryPath": str(
            browser_stage_packet_after_final_frontend_audit_partial_recovery_path
        ),
        "simulatedFinalFrontendAuditCompleteResultPath": str(simulated_final_frontend_audit_complete_result_path),
        "simulatedFinalFrontendAuditCompleteReportPath": str(simulated_final_frontend_audit_complete_report_path),
        "simulatedFinalFrontendAuditInputsSummaryPath": str(simulated_final_frontend_audit_inputs_summary_path),
        "simulatedFinalFrontendAuditExpectedStatusesPath": str(simulated_final_frontend_audit_expected_statuses_path),
        "ledgerAfterFinalFrontendAuditCompletePath": str(ledger_after_final_frontend_audit_complete_path),
        "browserStagePacketAfterFinalFrontendAuditCompletePath": str(
            browser_stage_packet_after_final_frontend_audit_complete_path
        ),
        "simulatedCleanupProbesPartialResultPath": str(simulated_cleanup_probes_partial_result_path),
        "ledgerAfterCleanupProbesPartialPath": str(ledger_after_cleanup_probes_partial_path),
        "browserStagePacketAfterCleanupProbesPartialRecoveryPath": str(
            browser_stage_packet_after_cleanup_probes_partial_recovery_path
        ),
        "simulatedCleanupProbesCompleteResultPath": str(simulated_cleanup_probes_complete_result_path),
        "ledgerAfterCleanupProbesCompletePath": str(ledger_after_cleanup_probes_complete_path),
        "fullE2EValidation": full_validation,
        "handoffSafety": handoff_validation,
        "launchPlanSafety": launch_plan_validation,
        "browserExecutionPlanSafety": browser_execution_plan_validation,
        "browserExecutionLedgerSafety": browser_execution_ledger_validation,
        "browserStagePacketSafety": browser_stage_packet_validation,
        "browserStageEvidenceBundleSafety": browser_stage_evidence_bundle_validation,
        "browserStageEvidenceManifest": browser_stage_evidence_manifest,
        "simulatedStageResultSafety": simulated_stage_result_validation,
        "ledgerAfterFirstStageSafety": ledger_after_first_stage_validation,
        "browserStagePacketAfterFirstStageSafety": browser_stage_packet_after_first_stage_validation,
        "simulatedCreateSiteResultSafety": simulated_create_site_result_validation,
        "ledgerAfterCreateSiteSafety": ledger_after_create_site_validation,
        "browserStagePacketAfterCreateSiteSafety": browser_stage_packet_after_create_site_validation,
        "simulatedSetupResultSafety": simulated_setup_result_validation,
        "ledgerAfterSetupSafety": ledger_after_setup_validation,
        "browserStagePacketAfterSetupSafety": browser_stage_packet_after_setup_validation,
        "nextBrowserActionHandoffSafety": next_browser_action_handoff_validation,
        "simulatedModuleCapturePartialResultSafety": simulated_module_capture_partial_result_validation,
        "ledgerAfterModuleCapturePartialSafety": ledger_after_module_capture_partial_validation,
        "moduleCaptureCoverageSafety": module_capture_coverage_validation,
        "ledgerAfterModuleCaptureCoverageSyncSafety": ledger_after_module_capture_coverage_sync_validation,
        "moduleCaptureCoverageCompleteSafety": module_capture_coverage_complete_validation,
        "ledgerAfterModuleCaptureCompleteSafety": ledger_after_module_capture_complete_validation,
        "browserStagePacketAfterModuleCaptureCompleteSafety": browser_stage_packet_after_module_capture_complete_validation,
        "simulatedThemeLaunchPartialResultSafety": simulated_theme_launch_partial_result_validation,
        "ledgerAfterThemeLaunchPartialSafety": ledger_after_theme_launch_partial_validation,
        "browserStagePacketAfterThemeLaunchPartialRecoverySafety": (
            browser_stage_packet_after_theme_launch_partial_recovery_validation
        ),
        "ledgerAfterThemeLaunchRecoveryCompleteSafety": ledger_after_theme_launch_recovery_complete_validation,
        "simulatedThemeLaunchCompleteResultSafety": simulated_theme_launch_complete_result_validation,
        "ledgerAfterThemeLaunchCompleteSafety": ledger_after_theme_launch_complete_validation,
        "browserStagePacketAfterThemeLaunchCompleteSafety": browser_stage_packet_after_theme_launch_complete_validation,
        "simulatedStaticAuditPartialResultSafety": simulated_static_audit_partial_result_validation,
        "ledgerAfterStaticAuditPartialSafety": ledger_after_static_audit_partial_validation,
        "browserStagePacketAfterStaticAuditPartialRecoverySafety": (
            browser_stage_packet_after_static_audit_partial_recovery_validation
        ),
        "simulatedStaticAuditCompleteResultSafety": simulated_static_audit_complete_result_validation,
        "ledgerAfterStaticAuditCompleteSafety": ledger_after_static_audit_complete_validation,
        "browserStagePacketAfterStaticAuditCompleteSafety": browser_stage_packet_after_static_audit_complete_validation,
        "simulatedContentProbePartialResultSafety": simulated_content_probe_partial_result_validation,
        "ledgerAfterContentProbePartialSafety": ledger_after_content_probe_partial_validation,
        "browserStagePacketAfterContentProbePartialRecoverySafety": (
            browser_stage_packet_after_content_probe_partial_recovery_validation
        ),
        "simulatedContentProbeCompleteResultSafety": simulated_content_probe_complete_result_validation,
        "ledgerAfterContentProbeCompleteSafety": ledger_after_content_probe_complete_validation,
        "browserStagePacketAfterContentProbeCompleteSafety": browser_stage_packet_after_content_probe_complete_validation,
        "simulatedSaveRequestPartialResultSafety": simulated_save_request_partial_result_validation,
        "ledgerAfterSaveRequestPartialSafety": ledger_after_save_request_partial_validation,
        "browserStagePacketAfterSaveRequestPartialRecoverySafety": (
            browser_stage_packet_after_save_request_partial_recovery_validation
        ),
        "simulatedSaveRequestCompleteResultSafety": simulated_save_request_complete_result_validation,
        "ledgerAfterSaveRequestCompleteSafety": ledger_after_save_request_complete_validation,
        "browserStagePacketAfterSaveRequestCompleteSafety": browser_stage_packet_after_save_request_complete_validation,
        "simulatedPublishSamplePartialResultSafety": simulated_publish_sample_partial_result_validation,
        "ledgerAfterPublishSamplePartialSafety": ledger_after_publish_sample_partial_validation,
        "browserStagePacketAfterPublishSamplePartialRecoverySafety": (
            browser_stage_packet_after_publish_sample_partial_recovery_validation
        ),
        "simulatedPublishSampleCompleteResultSafety": simulated_publish_sample_complete_result_validation,
        "ledgerAfterPublishSampleCompleteSafety": ledger_after_publish_sample_complete_validation,
        "browserStagePacketAfterPublishSampleCompleteSafety": browser_stage_packet_after_publish_sample_complete_validation,
        "simulatedManifestGatePartialResultSafety": simulated_manifest_gate_partial_result_validation,
        "ledgerAfterManifestGatePartialSafety": ledger_after_manifest_gate_partial_validation,
        "browserStagePacketAfterManifestGatePartialRecoverySafety": (
            browser_stage_packet_after_manifest_gate_partial_recovery_validation
        ),
        "simulatedManifestGateCompleteResultSafety": simulated_manifest_gate_complete_result_validation,
        "ledgerAfterManifestGateCompleteSafety": ledger_after_manifest_gate_complete_validation,
        "browserStagePacketAfterManifestGateCompleteSafety": browser_stage_packet_after_manifest_gate_complete_validation,
        "simulatedBatchUploadPartialResultSafety": simulated_batch_upload_partial_result_validation,
        "ledgerAfterBatchUploadPartialSafety": ledger_after_batch_upload_partial_validation,
        "browserStagePacketAfterBatchUploadPartialRecoverySafety": (
            browser_stage_packet_after_batch_upload_partial_recovery_validation
        ),
        "simulatedBatchUploadCompleteResultSafety": simulated_batch_upload_complete_result_validation,
        "ledgerAfterBatchUploadCompleteSafety": ledger_after_batch_upload_complete_validation,
        "browserStagePacketAfterBatchUploadCompleteSafety": browser_stage_packet_after_batch_upload_complete_validation,
        "simulatedFormsMediaSettingsPartialResultSafety": simulated_forms_media_settings_partial_result_validation,
        "ledgerAfterFormsMediaSettingsPartialSafety": ledger_after_forms_media_settings_partial_validation,
        "browserStagePacketAfterFormsMediaSettingsPartialRecoverySafety": (
            browser_stage_packet_after_forms_media_settings_partial_recovery_validation
        ),
        "simulatedFormsMediaSettingsCompleteResultSafety": simulated_forms_media_settings_complete_result_validation,
        "ledgerAfterFormsMediaSettingsCompleteSafety": ledger_after_forms_media_settings_complete_validation,
        "browserStagePacketAfterFormsMediaSettingsCompleteSafety": (
            browser_stage_packet_after_forms_media_settings_complete_validation
        ),
        "simulatedFinalFrontendAuditPartialResultSafety": simulated_final_frontend_audit_partial_result_validation,
        "ledgerAfterFinalFrontendAuditPartialSafety": ledger_after_final_frontend_audit_partial_validation,
        "browserStagePacketAfterFinalFrontendAuditPartialRecoverySafety": (
            browser_stage_packet_after_final_frontend_audit_partial_recovery_validation
        ),
        "simulatedFinalFrontendAuditCompleteResultSafety": simulated_final_frontend_audit_complete_result_validation,
        "ledgerAfterFinalFrontendAuditCompleteSafety": ledger_after_final_frontend_audit_complete_validation,
        "browserStagePacketAfterFinalFrontendAuditCompleteSafety": (
            browser_stage_packet_after_final_frontend_audit_complete_validation
        ),
        "simulatedCleanupProbesPartialResultSafety": simulated_cleanup_probes_partial_result_validation,
        "ledgerAfterCleanupProbesPartialSafety": ledger_after_cleanup_probes_partial_validation,
        "browserStagePacketAfterCleanupProbesPartialRecoverySafety": (
            browser_stage_packet_after_cleanup_probes_partial_recovery_validation
        ),
        "simulatedCleanupProbesCompleteResultSafety": simulated_cleanup_probes_complete_result_validation,
        "ledgerAfterCleanupProbesCompleteSafety": ledger_after_cleanup_probes_complete_validation,
        "manifestRehearsal": {
            "sourceInputRequirementsGenerated": full_validation.get("sourceInputRequirementsGenerated"),
            "sourceInputRequirementsBlocked": full_validation.get("sourceInputRequirementsBlocked"),
            "sourceInputRequirementsBlockedUntilCount": full_validation.get("sourceInputRequirementsBlockedUntilCount"),
            "draftValidationPassed": full_validation.get("manifestDraftValidationPassed"),
            "schemaGateExpectedFailure": full_validation.get("manifestSchemaGateExpectedFailure"),
        },
        "selectedStage": handoff.get("selectedStage"),
        "launchPlan": {
            "proofGateCount": len(launch_plan.get("proofGates", [])),
            "staticPaths": launch_plan.get("routePlan", {}).get("staticPaths", []),
            "detailRoutePatterns": launch_plan.get("routePlan", {}).get("detailRoutePatterns", []),
        },
        "browserExecutionPlan": {
            "stageCount": len(browser_execution_plan.get("stages", [])),
            "authorizationStageCount": len(
                [
                    stage
                    for stage in browser_execution_plan.get("stages", [])
                    if isinstance(stage, dict) and stage.get("authorizationRequired") is True
                ]
            ),
            "nextSuggestedStage": browser_execution_plan.get("nextSuggestedStage", {}),
        },
        "browserExecutionLedger": {
            "stageCounts": browser_execution_ledger.get("stageCounts", {}),
            "nextStageId": browser_execution_ledger.get("nextStageId", ""),
        },
        "browserStagePacket": {
            "stageId": browser_stage_packet.get("stageId", ""),
            "authorizationRequired": browser_stage_packet.get("authorizationRequired"),
            "targetTemplate": browser_stage_packet.get("targetTemplate", ""),
        },
        "stageResultSimulation": {
            "stageId": simulated_stage_result.get("stageId", ""),
            "status": simulated_stage_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_first_stage.get("nextStageId", ""),
            "stageCountsAfterApply": ledger_after_first_stage.get("stageCounts", {}),
        },
        "browserStagePacketAfterFirstStage": {
            "stageId": browser_stage_packet_after_first_stage.get("stageId", ""),
            "authorizationRequired": browser_stage_packet_after_first_stage.get("authorizationRequired"),
            "targetTemplate": browser_stage_packet_after_first_stage.get("targetTemplate", ""),
            "allowedActionCount": len(browser_stage_packet_after_first_stage.get("allowedActions", [])),
        },
        "createSiteStageSimulation": {
            "stageId": simulated_create_site_result.get("stageId", ""),
            "status": simulated_create_site_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_create_site.get("nextStageId", ""),
            "stageCountsAfterApply": ledger_after_create_site.get("stageCounts", {}),
        },
        "browserStagePacketAfterCreateSite": {
            "stageId": browser_stage_packet_after_create_site.get("stageId", ""),
            "authorizationRequired": browser_stage_packet_after_create_site.get("authorizationRequired"),
            "targetTemplate": browser_stage_packet_after_create_site.get("targetTemplate", ""),
            "allowedActionCount": len(browser_stage_packet_after_create_site.get("allowedActions", [])),
        },
        "setupStageSimulation": {
            "stageId": simulated_setup_result.get("stageId", ""),
            "status": simulated_setup_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_setup.get("nextStageId", ""),
            "stageCountsAfterApply": ledger_after_setup.get("stageCounts", {}),
        },
        "browserStagePacketAfterSetup": {
            "stageId": browser_stage_packet_after_setup.get("stageId", ""),
            "authorizationRequired": browser_stage_packet_after_setup.get("authorizationRequired"),
            "targetTemplate": browser_stage_packet_after_setup.get("targetTemplate", ""),
            "allowedActionCount": len(browser_stage_packet_after_setup.get("allowedActions", [])),
        },
        "moduleCapturePartialSimulation": {
            "stageId": simulated_module_capture_partial_result.get("stageId", ""),
            "status": simulated_module_capture_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_module_capture_partial.get("nextStageId", ""),
            "stageCountsAfterApply": ledger_after_module_capture_partial.get("stageCounts", {}),
        },
        "capturePlanGateCoverage": {
            "ok": capture_plan_gate_coverage.get("ok"),
            "stageCount": capture_plan_gate_coverage.get("stageCount"),
            "coveredActions": capture_plan_gate_coverage.get("coveredActions", []),
            "ungatedAllowedActions": capture_plan_gate_coverage.get("ungatedAllowedActions", []),
        },
        "moduleCaptureCoverage": {
            "complete": module_capture_coverage.get("complete"),
            "interfaceCoverageComplete": module_capture_coverage.get("interfaceCoverageComplete"),
            "actionReplayContractsVerified": module_capture_coverage.get("actionReplayContractsVerified"),
            "jsonReplayReady": module_capture_coverage.get("jsonReplayReady"),
            "coverageCounts": module_capture_coverage.get("coverageCounts", {}),
            "nextUncapturedStageKey": module_capture_coverage.get("nextUncapturedStageKey", ""),
        },
        "moduleCaptureCoverageLedgerSync": {
            "nextStageIdAfterSync": ledger_after_module_capture_coverage_sync.get("nextStageId", ""),
            "stageCountsAfterSync": ledger_after_module_capture_coverage_sync.get("stageCounts", {}),
            "nextAllowedActions": next(
                (
                    entry.get("nextAllowedActions", [])
                    for entry in ledger_after_module_capture_coverage_sync.get("entries", [])
                    if isinstance(entry, dict) and entry.get("stageId") == "module_interface_capture"
                ),
                [],
            ),
        },
        "moduleCaptureCompletionSimulation": {
            "complete": module_capture_coverage_complete.get("complete"),
            "interfaceCoverageComplete": module_capture_coverage_complete.get("interfaceCoverageComplete"),
            "actionReplayContractsVerified": module_capture_coverage_complete.get("actionReplayContractsVerified"),
            "jsonReplayReady": module_capture_coverage_complete.get("jsonReplayReady"),
            "coverageCounts": module_capture_coverage_complete.get("coverageCounts", {}),
            "nextStageIdAfterSync": ledger_after_module_capture_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_module_capture_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_module_capture_complete.get("authorizationRequired"),
        },
        "themeLaunchPartialSimulation": {
            "stageId": simulated_theme_launch_partial_result.get("stageId", ""),
            "status": simulated_theme_launch_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_theme_launch_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_theme_launch_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_theme_launch_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_theme_launch_partial.get("stageCounts", {}),
        },
        "themeLaunchCompletionSimulation": {
            "stageId": simulated_theme_launch_complete_result.get("stageId", ""),
            "status": simulated_theme_launch_complete_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_theme_launch_complete.get("nextStageId", ""),
            "completedFromRecoveryPacket": browser_stage_packet_after_theme_launch_partial_recovery.get("recovery"),
            "nextPacketStageId": browser_stage_packet_after_theme_launch_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_theme_launch_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_theme_launch_complete.get("stageCounts", {}),
        },
        "staticAuditPartialSimulation": {
            "stageId": simulated_static_audit_partial_result.get("stageId", ""),
            "status": simulated_static_audit_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_static_audit_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_static_audit_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_static_audit_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_static_audit_partial.get("stageCounts", {}),
        },
        "staticAuditCompletionSimulation": {
            "stageId": simulated_static_audit_complete_result.get("stageId", ""),
            "status": simulated_static_audit_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_static_audit_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_static_audit_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_static_audit_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_static_audit_complete.get("stageCounts", {}),
        },
        "contentProbePartialSimulation": {
            "stageId": simulated_content_probe_partial_result.get("stageId", ""),
            "status": simulated_content_probe_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_content_probe_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_content_probe_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_content_probe_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_content_probe_partial.get("stageCounts", {}),
        },
        "contentProbeCompletionSimulation": {
            "stageId": simulated_content_probe_complete_result.get("stageId", ""),
            "status": simulated_content_probe_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_content_probe_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_content_probe_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_content_probe_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_content_probe_complete.get("stageCounts", {}),
        },
        "saveRequestPartialSimulation": {
            "stageId": simulated_save_request_partial_result.get("stageId", ""),
            "status": simulated_save_request_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_save_request_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_save_request_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_save_request_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_save_request_partial.get("stageCounts", {}),
        },
        "saveRequestCompletionSimulation": {
            "stageId": simulated_save_request_complete_result.get("stageId", ""),
            "status": simulated_save_request_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_save_request_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_save_request_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_save_request_complete.get("authorizationRequired"),
            "manifestSchemaGateReady": any(
                isinstance(entry, dict)
                and entry.get("stageId") == "manifest_schema_gate"
                and entry.get("status") == "ready"
                for entry in ledger_after_save_request_complete.get("entries", [])
            ),
            "stageCountsAfterApply": ledger_after_save_request_complete.get("stageCounts", {}),
        },
        "publishSamplePartialSimulation": {
            "stageId": simulated_publish_sample_partial_result.get("stageId", ""),
            "status": simulated_publish_sample_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_publish_sample_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_publish_sample_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_publish_sample_partial_recovery.get("recovery"),
            "manifestSchemaGateStillReady": any(
                isinstance(entry, dict)
                and entry.get("stageId") == "manifest_schema_gate"
                and entry.get("status") == "ready"
                for entry in ledger_after_publish_sample_partial.get("entries", [])
            ),
            "stageCountsAfterApply": ledger_after_publish_sample_partial.get("stageCounts", {}),
        },
        "publishSampleCompletionSimulation": {
            "stageId": simulated_publish_sample_complete_result.get("stageId", ""),
            "status": simulated_publish_sample_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_publish_sample_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_publish_sample_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_publish_sample_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_publish_sample_complete.get("stageCounts", {}),
        },
        "manifestGatePartialSimulation": {
            "stageId": simulated_manifest_gate_partial_result.get("stageId", ""),
            "status": simulated_manifest_gate_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_manifest_gate_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_manifest_gate_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_manifest_gate_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_manifest_gate_partial.get("stageCounts", {}),
        },
        "manifestGateCompletionSimulation": {
            "stageId": simulated_manifest_gate_complete_result.get("stageId", ""),
            "status": simulated_manifest_gate_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_manifest_gate_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_manifest_gate_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_manifest_gate_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_manifest_gate_complete.get("stageCounts", {}),
        },
        "batchUploadPartialSimulation": {
            "stageId": simulated_batch_upload_partial_result.get("stageId", ""),
            "status": simulated_batch_upload_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_batch_upload_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_batch_upload_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_batch_upload_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_batch_upload_partial.get("stageCounts", {}),
        },
        "batchUploadCompletionSimulation": {
            "stageId": simulated_batch_upload_complete_result.get("stageId", ""),
            "status": simulated_batch_upload_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_batch_upload_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_batch_upload_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_batch_upload_complete.get("authorizationRequired"),
            "stageCountsAfterApply": ledger_after_batch_upload_complete.get("stageCounts", {}),
        },
        "formsMediaSettingsPartialSimulation": {
            "stageId": simulated_forms_media_settings_partial_result.get("stageId", ""),
            "status": simulated_forms_media_settings_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_forms_media_settings_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_forms_media_settings_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_forms_media_settings_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_forms_media_settings_partial.get("stageCounts", {}),
        },
        "formsMediaSettingsCompletionSimulation": {
            "stageId": simulated_forms_media_settings_complete_result.get("stageId", ""),
            "status": simulated_forms_media_settings_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_forms_media_settings_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_forms_media_settings_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_forms_media_settings_complete.get(
                "authorizationRequired"
            ),
            "stageCountsAfterApply": ledger_after_forms_media_settings_complete.get("stageCounts", {}),
        },
        "finalFrontendAuditPartialSimulation": {
            "stageId": simulated_final_frontend_audit_partial_result.get("stageId", ""),
            "status": simulated_final_frontend_audit_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_final_frontend_audit_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_final_frontend_audit_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_final_frontend_audit_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_final_frontend_audit_partial.get("stageCounts", {}),
        },
        "finalFrontendAuditCompletionSimulation": {
            "stageId": simulated_final_frontend_audit_complete_result.get("stageId", ""),
            "status": simulated_final_frontend_audit_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_final_frontend_audit_complete.get("nextStageId", ""),
            "nextPacketStageId": browser_stage_packet_after_final_frontend_audit_complete.get("stageId", ""),
            "nextPacketAuthorizationRequired": browser_stage_packet_after_final_frontend_audit_complete.get(
                "authorizationRequired"
            ),
            "stageCountsAfterApply": ledger_after_final_frontend_audit_complete.get("stageCounts", {}),
        },
        "cleanupProbesPartialSimulation": {
            "stageId": simulated_cleanup_probes_partial_result.get("stageId", ""),
            "status": simulated_cleanup_probes_partial_result.get("status", ""),
            "nextStageIdAfterApply": ledger_after_cleanup_probes_partial.get("nextStageId", ""),
            "recoveryPacketStageId": browser_stage_packet_after_cleanup_probes_partial_recovery.get("stageId", ""),
            "recoveryPacket": browser_stage_packet_after_cleanup_probes_partial_recovery.get("recovery"),
            "stageCountsAfterApply": ledger_after_cleanup_probes_partial.get("stageCounts", {}),
        },
        "cleanupProbesCompletionSimulation": {
            "stageId": simulated_cleanup_probes_complete_result.get("stageId", ""),
            "status": simulated_cleanup_probes_complete_result.get("status", ""),
            "completedFromRecoveryPacket": True,
            "nextStageIdAfterApply": ledger_after_cleanup_probes_complete.get("nextStageId", ""),
            "stageCountsAfterApply": ledger_after_cleanup_probes_complete.get("stageCounts", {}),
        },
        "finalLedgerExhaustion": {
            "allStagesCompleted": ledger_after_cleanup_probes_complete.get("stageCounts", {}).get("completed")
            == ledger_after_cleanup_probes_complete.get("stageCounts", {}).get("total"),
            "nextStageId": ledger_after_cleanup_probes_complete.get("nextStageId", ""),
            "packetBuildRejected": final_packet_rejected,
            "rejectionReason": final_packet_rejection_reason,
        },
        "artifacts": {
            "fullSummary": str(full_paths["fullSummary"]),
            "moduleCapturePlan": str(full_paths["moduleCapturePlan"]),
            "draftManifest": str(full_paths["draftManifest"]),
            "sourceInputRequirements": str(full_paths["sourceInputRequirements"]),
            "manifestSummary": str(full_paths["manifestSummary"]),
            "handoff": str(handoff_path),
            "launchPlan": str(launch_plan_path),
            "browserExecutionPlan": str(browser_execution_plan_path),
            "browserExecutionLedger": str(browser_execution_ledger_path),
            "browserStagePacket": str(browser_stage_packet_path),
            "browserStageEvidenceBundle": str(browser_stage_evidence_bundle_dir),
            "browserStageEvidenceManifest": str(browser_stage_evidence_manifest_path),
            "simulatedStageResult": str(simulated_stage_result_path),
            "ledgerAfterFirstStage": str(ledger_after_first_stage_path),
            "browserStagePacketAfterFirstStage": str(browser_stage_packet_after_first_stage_path),
            "simulatedCreateSiteResult": str(simulated_create_site_result_path),
            "ledgerAfterCreateSite": str(ledger_after_create_site_path),
            "browserStagePacketAfterCreateSite": str(browser_stage_packet_after_create_site_path),
            "simulatedSetupResult": str(simulated_setup_result_path),
            "ledgerAfterSetup": str(ledger_after_setup_path),
            "browserStagePacketAfterSetup": str(browser_stage_packet_after_setup_path),
            "browserStageModuleCaptureAuthorizationPackage": str(
                browser_stage_module_capture_authorization_package_path
            ),
            "nextBrowserActionHandoff": str(next_browser_action_handoff_path),
            "simulatedModuleCapturePartialResult": str(simulated_module_capture_partial_result_path),
            "ledgerAfterModuleCapturePartial": str(ledger_after_module_capture_partial_path),
            "simulatedModuleCaptureStageResult": str(simulated_module_capture_stage_result_path),
            "capturePlanGateCoverage": str(capture_plan_gate_coverage_path),
            "moduleCaptureCoverage": str(module_capture_coverage_path),
            "ledgerAfterModuleCaptureCoverageSync": str(ledger_after_module_capture_coverage_sync_path),
            "moduleCaptureCoverageComplete": str(module_capture_coverage_complete_path),
            "ledgerAfterModuleCaptureComplete": str(ledger_after_module_capture_complete_path),
            "browserStagePacketAfterModuleCaptureComplete": str(browser_stage_packet_after_module_capture_complete_path),
            "simulatedThemeLaunchPartialResult": str(simulated_theme_launch_partial_result_path),
            "ledgerAfterThemeLaunchPartial": str(ledger_after_theme_launch_partial_path),
            "browserStagePacketAfterThemeLaunchPartialRecovery": str(
                browser_stage_packet_after_theme_launch_partial_recovery_path
            ),
            "ledgerAfterThemeLaunchRecoveryComplete": str(ledger_after_theme_launch_recovery_complete_path),
            "simulatedThemeLaunchCompleteResult": str(simulated_theme_launch_complete_result_path),
            "ledgerAfterThemeLaunchComplete": str(ledger_after_theme_launch_complete_path),
            "browserStagePacketAfterThemeLaunchComplete": str(browser_stage_packet_after_theme_launch_complete_path),
            "simulatedStaticAuditPartialResult": str(simulated_static_audit_partial_result_path),
            "ledgerAfterStaticAuditPartial": str(ledger_after_static_audit_partial_path),
            "browserStagePacketAfterStaticAuditPartialRecovery": str(
                browser_stage_packet_after_static_audit_partial_recovery_path
            ),
            "simulatedStaticAuditCompleteResult": str(simulated_static_audit_complete_result_path),
            "ledgerAfterStaticAuditComplete": str(ledger_after_static_audit_complete_path),
            "browserStagePacketAfterStaticAuditComplete": str(browser_stage_packet_after_static_audit_complete_path),
            "simulatedContentProbePartialResult": str(simulated_content_probe_partial_result_path),
            "ledgerAfterContentProbePartial": str(ledger_after_content_probe_partial_path),
            "browserStagePacketAfterContentProbePartialRecovery": str(
                browser_stage_packet_after_content_probe_partial_recovery_path
            ),
            "simulatedContentProbeCompleteResult": str(simulated_content_probe_complete_result_path),
            "ledgerAfterContentProbeComplete": str(ledger_after_content_probe_complete_path),
            "browserStagePacketAfterContentProbeComplete": str(browser_stage_packet_after_content_probe_complete_path),
            "simulatedSaveRequestPartialResult": str(simulated_save_request_partial_result_path),
            "ledgerAfterSaveRequestPartial": str(ledger_after_save_request_partial_path),
            "browserStagePacketAfterSaveRequestPartialRecovery": str(
                browser_stage_packet_after_save_request_partial_recovery_path
            ),
            "simulatedSaveRequestCompleteResult": str(simulated_save_request_complete_result_path),
            "ledgerAfterSaveRequestComplete": str(ledger_after_save_request_complete_path),
            "browserStagePacketAfterSaveRequestComplete": str(browser_stage_packet_after_save_request_complete_path),
            "simulatedPublishSamplePartialResult": str(simulated_publish_sample_partial_result_path),
            "ledgerAfterPublishSamplePartial": str(ledger_after_publish_sample_partial_path),
            "browserStagePacketAfterPublishSamplePartialRecovery": str(
                browser_stage_packet_after_publish_sample_partial_recovery_path
            ),
            "simulatedPublishSampleCompleteResult": str(simulated_publish_sample_complete_result_path),
            "ledgerAfterPublishSampleComplete": str(ledger_after_publish_sample_complete_path),
            "browserStagePacketAfterPublishSampleComplete": str(browser_stage_packet_after_publish_sample_complete_path),
            "simulatedManifestGatePartialResult": str(simulated_manifest_gate_partial_result_path),
            "ledgerAfterManifestGatePartial": str(ledger_after_manifest_gate_partial_path),
            "browserStagePacketAfterManifestGatePartialRecovery": str(
                browser_stage_packet_after_manifest_gate_partial_recovery_path
            ),
            "simulatedManifestGateCompleteResult": str(simulated_manifest_gate_complete_result_path),
            "ledgerAfterManifestGateComplete": str(ledger_after_manifest_gate_complete_path),
            "browserStagePacketAfterManifestGateComplete": str(browser_stage_packet_after_manifest_gate_complete_path),
            "simulatedBatchUploadPartialResult": str(simulated_batch_upload_partial_result_path),
            "ledgerAfterBatchUploadPartial": str(ledger_after_batch_upload_partial_path),
            "browserStagePacketAfterBatchUploadPartialRecovery": str(
                browser_stage_packet_after_batch_upload_partial_recovery_path
            ),
            "simulatedBatchUploadCompleteResult": str(simulated_batch_upload_complete_result_path),
            "ledgerAfterBatchUploadComplete": str(ledger_after_batch_upload_complete_path),
            "browserStagePacketAfterBatchUploadComplete": str(browser_stage_packet_after_batch_upload_complete_path),
            "simulatedFormsMediaSettingsPartialResult": str(simulated_forms_media_settings_partial_result_path),
            "ledgerAfterFormsMediaSettingsPartial": str(ledger_after_forms_media_settings_partial_path),
            "browserStagePacketAfterFormsMediaSettingsPartialRecovery": str(
                browser_stage_packet_after_forms_media_settings_partial_recovery_path
            ),
            "simulatedFormsMediaSettingsCompleteResult": str(simulated_forms_media_settings_complete_result_path),
            "ledgerAfterFormsMediaSettingsComplete": str(ledger_after_forms_media_settings_complete_path),
            "browserStagePacketAfterFormsMediaSettingsComplete": str(
                browser_stage_packet_after_forms_media_settings_complete_path
            ),
            "simulatedFinalFrontendAuditPartialResult": str(simulated_final_frontend_audit_partial_result_path),
            "simulatedFinalFrontendAuditPartialReport": str(simulated_final_frontend_audit_partial_report_path),
            "ledgerAfterFinalFrontendAuditPartial": str(ledger_after_final_frontend_audit_partial_path),
            "browserStagePacketAfterFinalFrontendAuditPartialRecovery": str(
                browser_stage_packet_after_final_frontend_audit_partial_recovery_path
            ),
            "simulatedFinalFrontendAuditCompleteResult": str(simulated_final_frontend_audit_complete_result_path),
            "simulatedFinalFrontendAuditCompleteReport": str(simulated_final_frontend_audit_complete_report_path),
            "simulatedFinalFrontendAuditInputsSummary": str(simulated_final_frontend_audit_inputs_summary_path),
            "simulatedFinalFrontendAuditExpectedStatuses": str(simulated_final_frontend_audit_expected_statuses_path),
            "ledgerAfterFinalFrontendAuditComplete": str(ledger_after_final_frontend_audit_complete_path),
            "browserStagePacketAfterFinalFrontendAuditComplete": str(
                browser_stage_packet_after_final_frontend_audit_complete_path
            ),
            "simulatedCleanupProbesPartialResult": str(simulated_cleanup_probes_partial_result_path),
            "ledgerAfterCleanupProbesPartial": str(ledger_after_cleanup_probes_partial_path),
            "browserStagePacketAfterCleanupProbesPartialRecovery": str(
                browser_stage_packet_after_cleanup_probes_partial_recovery_path
            ),
            "simulatedCleanupProbesCompleteResult": str(simulated_cleanup_probes_complete_result_path),
            "ledgerAfterCleanupProbesComplete": str(ledger_after_cleanup_probes_complete_path),
            "rehearsalSummary": str(summary_path),
        },
        "warning": (
            "This rehearsal is local-only. It does not access LAICMS, does not create or modify a site, "
            "and does not grant user authorization for a browser mutation."
        ),
    }
    write_json(summary_path, summary)
    browser_runbook_summary = build_runbook_summary(summary_path)
    write_json(browser_runbook_summary_path, browser_runbook_summary)
    summary["browserRunbookSummaryPath"] = str(browser_runbook_summary_path)
    summary["artifacts"]["browserRunbookSummary"] = str(browser_runbook_summary_path)
    summary["browserRunbookSummary"] = {
        "kind": browser_runbook_summary.get("kind", ""),
        "sourceValid": browser_runbook_summary.get("sourceRehearsal", {}).get("valid"),
        "nextStageId": browser_runbook_summary.get("nextRealBrowserStep", {}).get("stageId", ""),
        "authorizationRequired": browser_runbook_summary.get("nextRealBrowserStep", {}).get("authorizationRequired"),
        "commandsSuppressed": browser_runbook_summary.get("nextRealBrowserStep", {}).get("commandsSuppressed"),
        "mode": browser_runbook_summary.get("nextRealBrowserStep", {}).get("mode", ""),
        "initialLedgerNextStageId": browser_runbook_summary.get("coverage", {}).get("initialLedgerNextStageId", ""),
    }
    write_json(summary_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full local-only AllinCMS rehearsal with handoff safety validation.")
    site_keys = parser.add_mutually_exclusive_group(required=True)
    site_keys.add_argument("--existing-site-keys", help="Comma-separated site keys observed before create")
    site_keys.add_argument("--no-existing-sites", action="store_true")
    parser.add_argument("--site-key-evidence", default="")
    parser.add_argument("--empty-site-list-evidence", default="verified empty /sites list")
    parser.add_argument("--simulated-created-site-key", default="simsite01")
    parser.add_argument("--content-type", choices=["posts", "products", "forms"], default="products")
    parser.add_argument("--observed-create-fields", default=simulate_full_e2e_chain.simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS)
    parser.add_argument("--list-columns", default=simulate_full_e2e_chain.simulate_site_creation_chain.DEFAULT_LIST_COLUMNS)
    parser.add_argument("--edit-fields", default=simulate_full_e2e_chain.simulate_site_creation_chain.DEFAULT_EDIT_FIELDS)
    parser.add_argument(
        "--create-authorization-source",
        default="current user explicitly authorizes create site at https://workspace.laicms.com/sites for local simulation only",
    )
    parser.add_argument("--simulated-content-id", default="codex-probe-id")
    parser.add_argument("--simulated-slug", default="codex-probe-delete-me")
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument("--sedimentation", choices=["updated", "none"], default="none")
    parser.add_argument("--closeout-note", default="no reusable skill update needed after checking")
    parser.add_argument("--changed-files", default="")
    parser.add_argument("--module", default="")
    parser.add_argument("--action", default="")
    parser.add_argument("--allow-command-output", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    try:
        summary = run_rehearsal(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
