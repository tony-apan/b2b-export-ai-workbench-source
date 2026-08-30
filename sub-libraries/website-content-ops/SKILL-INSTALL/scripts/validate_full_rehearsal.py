#!/usr/bin/env python3
"""Validate a full local-only AllinCMS rehearsal summary artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_browser_stage_result import validate_browser_stage_result
from validate_browser_execution_ledger import validate_browser_execution_ledger
from validate_browser_execution_plan import validate_browser_execution_plan
from validate_browser_stage_packet import validate_browser_stage_packet
from validate_browser_stage_evidence_bundle import validate_bundle as validate_browser_stage_evidence_bundle
from validate_capture_plan_gate_coverage import validate_plan_gate_coverage
from validate_capture_handoff import validate_handoff
from validate_full_e2e_simulation import validate_directory
from validate_launch_plan import validate_launch_plan
from validate_next_browser_action_handoff import validate_handoff as validate_next_browser_action_handoff
from update_module_capture_coverage import validate_coverage


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def load_json_array(path: Path) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, list):
        raise ValueError(f"JSON root must be array: {path}")
    return data


def same_path(recorded: object, expected: Path) -> bool:
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    return Path(recorded).resolve() == expected.resolve()


def validate_packet_command_paths(
    label: str,
    packet: dict[str, Any],
    ledger_path: Path,
    packet_path: Path,
    issues: list[str],
) -> None:
    update = packet.get("ledgerUpdate")
    command = update.get("commandTemplate") if isinstance(update, dict) else ""
    if not isinstance(command, str) or not command.strip():
        issues.append(f"{label} ledgerUpdate.commandTemplate must be a non-empty string")
        return
    expected_result = str(packet_path.with_name(packet_path.stem + "-stage-result.json"))
    stage_id = str(packet.get("stageId", "stage"))
    expected_output = str(ledger_path.with_name(ledger_path.stem + f".after-{stage_id}.json"))
    for expected, name in (
        (str(ledger_path), "ledger path"),
        (str(packet_path), "packet path"),
        (expected_result, "stage-result path"),
        (expected_output, "updated-ledger path"),
    ):
        if expected not in command:
            issues.append(f"{label} commandTemplate missing {name}: {expected}")
    if "~/allincms-projects/allincms-full-rehearsal/" in command and "~/allincms-projects/allincms-full-rehearsal/" not in str(packet_path):
        issues.append(f"{label} commandTemplate must not use the default ~/allincms-projects/allincms-full-rehearsal path")


def require(condition: bool, issues: list[str], message: str) -> None:
    if not condition:
        issues.append(message)


def validate_recovery_packet_artifact(
    label: str,
    packet_path: Path,
    expected_stage_id: str,
    partial_summary: dict[str, Any],
    issues: list[str],
    partial_ledger_path: Path | None = None,
) -> dict[str, Any]:
    try:
        packet = load_json(packet_path)
    except ValueError as exc:
        packet = {}
        issues.append(str(exc))
    packet_validation = validate_browser_stage_packet(packet)
    issues.extend(f"{label} recovery packet: {issue}" for issue in packet_validation.get("issues", []))
    require(packet_validation.get("ok") is True, issues, f"{label} recovery packet validation must pass")
    require(packet.get("stageId") == expected_stage_id, issues, f"{label} recovery packet must target {expected_stage_id}")
    require(packet.get("recovery") is True, issues, f"{label} recovery packet must be marked recovery")
    require(
        partial_summary.get("recoveryPacketStageId") == expected_stage_id,
        issues,
        f"{label} partial summary must record recovery packet stage id",
    )
    require(
        partial_summary.get("recoveryPacket") is True,
        issues,
        f"{label} partial summary must record recovery packet true",
    )
    if partial_ledger_path is not None:
        validate_packet_command_paths(f"{label} recovery packet", packet, partial_ledger_path, packet_path, issues)
    return packet_validation


def validate_rehearsal(summary_path: Path) -> dict[str, Any]:
    issues: list[str] = []
    try:
        summary = load_json(summary_path)
    except ValueError as exc:
        return {"ok": False, "summaryPath": str(summary_path), "issues": [str(exc)]}

    root = summary_path.parent
    full_e2e_dir = root / "full-e2e"
    handoff_path = root / "next-capture-handoff" / "handoff.json"
    launch_plan_path = root / "launch-plan.json"
    browser_execution_plan_path = root / "browser-execution-plan.json"
    browser_execution_ledger_path = root / "browser-execution-ledger.json"
    browser_stage_packet_path = root / "next-browser-stage-packet.json"
    browser_stage_evidence_bundle_dir = root / "next-browser-stage-evidence-bundle"
    browser_stage_evidence_manifest_path = browser_stage_evidence_bundle_dir / "evidence-manifest.json"
    simulated_stage_result_path = root / "simulated-first-stage-result.json"
    ledger_after_first_stage_path = root / "browser-execution-ledger-after-first-stage.json"
    browser_stage_packet_after_first_stage_path = root / "next-browser-stage-packet-after-first-stage.json"
    simulated_create_site_result_path = root / "simulated-create-site-result.json"
    ledger_after_create_site_path = root / "browser-execution-ledger-after-create-site.json"
    browser_stage_packet_after_create_site_path = root / "next-browser-stage-packet-after-create-site.json"
    simulated_setup_result_path = root / "simulated-setup-pages-result.json"
    ledger_after_setup_path = root / "browser-execution-ledger-after-setup-pages.json"
    browser_stage_packet_after_setup_path = root / "next-browser-stage-packet-after-setup-pages.json"
    browser_stage_module_capture_authorization_package_path = root / "browser-stage-module-interface-authorization-package.json"
    next_browser_action_handoff_path = root / "next-browser-action-handoff.json"
    simulated_module_capture_partial_result_path = root / "simulated-module-capture-partial-result.json"
    ledger_after_module_capture_partial_path = root / "browser-execution-ledger-after-module-capture-partial.json"
    simulated_module_capture_stage_result_path = root / "simulated-module-capture-stage-result.json"
    capture_plan_gate_coverage_path = root / "capture-plan-gate-coverage.json"
    module_capture_coverage_path = root / "module-capture-coverage-after-one-stage.json"
    ledger_after_module_capture_coverage_sync_path = root / "browser-execution-ledger-after-module-capture-coverage-sync.json"
    module_capture_coverage_complete_path = root / "module-capture-coverage-complete.json"
    ledger_after_module_capture_complete_path = root / "browser-execution-ledger-after-module-capture-complete.json"
    browser_stage_packet_after_module_capture_complete_path = root / "next-browser-stage-packet-after-module-capture-complete.json"
    simulated_theme_launch_partial_result_path = root / "simulated-theme-launch-partial-result.json"
    ledger_after_theme_launch_partial_path = root / "browser-execution-ledger-after-theme-launch-partial.json"
    browser_stage_packet_after_theme_launch_partial_recovery_path = (
        root / "next-browser-stage-packet-after-theme-launch-partial-recovery.json"
    )
    ledger_after_theme_launch_recovery_complete_path = root / "browser-execution-ledger-after-theme-launch-recovery-complete.json"
    simulated_theme_launch_complete_result_path = root / "simulated-theme-launch-complete-result.json"
    ledger_after_theme_launch_complete_path = root / "browser-execution-ledger-after-theme-launch-complete.json"
    browser_stage_packet_after_theme_launch_complete_path = root / "next-browser-stage-packet-after-theme-launch-complete.json"
    simulated_static_audit_partial_result_path = root / "simulated-static-audit-partial-result.json"
    ledger_after_static_audit_partial_path = root / "browser-execution-ledger-after-static-audit-partial.json"
    browser_stage_packet_after_static_audit_partial_recovery_path = (
        root / "next-browser-stage-packet-after-static-audit-partial-recovery.json"
    )
    simulated_static_audit_complete_result_path = root / "simulated-static-audit-complete-result.json"
    ledger_after_static_audit_complete_path = root / "browser-execution-ledger-after-static-audit-complete.json"
    browser_stage_packet_after_static_audit_complete_path = root / "next-browser-stage-packet-after-static-audit-complete.json"
    simulated_content_probe_partial_result_path = root / "simulated-content-probe-partial-result.json"
    ledger_after_content_probe_partial_path = root / "browser-execution-ledger-after-content-probe-partial.json"
    browser_stage_packet_after_content_probe_partial_recovery_path = (
        root / "next-browser-stage-packet-after-content-probe-partial-recovery.json"
    )
    simulated_content_probe_complete_result_path = root / "simulated-content-probe-complete-result.json"
    ledger_after_content_probe_complete_path = root / "browser-execution-ledger-after-content-probe-complete.json"
    browser_stage_packet_after_content_probe_complete_path = root / "next-browser-stage-packet-after-content-probe-complete.json"
    simulated_save_request_partial_result_path = root / "simulated-save-request-partial-result.json"
    ledger_after_save_request_partial_path = root / "browser-execution-ledger-after-save-request-partial.json"
    browser_stage_packet_after_save_request_partial_recovery_path = (
        root / "next-browser-stage-packet-after-save-request-partial-recovery.json"
    )
    simulated_save_request_complete_result_path = root / "simulated-save-request-complete-result.json"
    ledger_after_save_request_complete_path = root / "browser-execution-ledger-after-save-request-complete.json"
    browser_stage_packet_after_save_request_complete_path = root / "next-browser-stage-packet-after-save-request-complete.json"
    simulated_publish_sample_partial_result_path = root / "simulated-publish-sample-partial-result.json"
    ledger_after_publish_sample_partial_path = root / "browser-execution-ledger-after-publish-sample-partial.json"
    browser_stage_packet_after_publish_sample_partial_recovery_path = (
        root / "next-browser-stage-packet-after-publish-sample-partial-recovery.json"
    )
    simulated_publish_sample_complete_result_path = root / "simulated-publish-sample-complete-result.json"
    ledger_after_publish_sample_complete_path = root / "browser-execution-ledger-after-publish-sample-complete.json"
    browser_stage_packet_after_publish_sample_complete_path = root / "next-browser-stage-packet-after-publish-sample-complete.json"
    simulated_manifest_gate_partial_result_path = root / "simulated-manifest-gate-partial-result.json"
    source_input_requirements_path = full_e2e_dir / "04-manifest-rehearsal" / "source-input-requirements.json"
    ledger_after_manifest_gate_partial_path = root / "browser-execution-ledger-after-manifest-gate-partial.json"
    browser_stage_packet_after_manifest_gate_partial_recovery_path = (
        root / "next-browser-stage-packet-after-manifest-gate-partial-recovery.json"
    )
    simulated_manifest_gate_complete_result_path = root / "simulated-manifest-gate-complete-result.json"
    ledger_after_manifest_gate_complete_path = root / "browser-execution-ledger-after-manifest-gate-complete.json"
    browser_stage_packet_after_manifest_gate_complete_path = root / "next-browser-stage-packet-after-manifest-gate-complete.json"
    simulated_batch_upload_partial_result_path = root / "simulated-batch-upload-partial-result.json"
    ledger_after_batch_upload_partial_path = root / "browser-execution-ledger-after-batch-upload-partial.json"
    browser_stage_packet_after_batch_upload_partial_recovery_path = (
        root / "next-browser-stage-packet-after-batch-upload-partial-recovery.json"
    )
    simulated_batch_upload_complete_result_path = root / "simulated-batch-upload-complete-result.json"
    ledger_after_batch_upload_complete_path = root / "browser-execution-ledger-after-batch-upload-complete.json"
    browser_stage_packet_after_batch_upload_complete_path = root / "next-browser-stage-packet-after-batch-upload-complete.json"
    simulated_forms_media_settings_partial_result_path = root / "simulated-forms-media-settings-partial-result.json"
    ledger_after_forms_media_settings_partial_path = root / "browser-execution-ledger-after-forms-media-settings-partial.json"
    browser_stage_packet_after_forms_media_settings_partial_recovery_path = (
        root / "next-browser-stage-packet-after-forms-media-settings-partial-recovery.json"
    )
    simulated_forms_media_settings_complete_result_path = root / "simulated-forms-media-settings-complete-result.json"
    ledger_after_forms_media_settings_complete_path = root / "browser-execution-ledger-after-forms-media-settings-complete.json"
    browser_stage_packet_after_forms_media_settings_complete_path = (
        root / "next-browser-stage-packet-after-forms-media-settings-complete.json"
    )
    simulated_final_frontend_audit_partial_result_path = root / "simulated-final-frontend-audit-partial-result.json"
    simulated_final_frontend_audit_partial_report_path = root / "simulated-final-audit-report-missing-detail.json"
    ledger_after_final_frontend_audit_partial_path = root / "browser-execution-ledger-after-final-frontend-audit-partial.json"
    browser_stage_packet_after_final_frontend_audit_partial_recovery_path = (
        root / "next-browser-stage-packet-after-final-frontend-audit-partial-recovery.json"
    )
    simulated_final_frontend_audit_complete_result_path = root / "simulated-final-frontend-audit-complete-result.json"
    simulated_final_frontend_audit_complete_report_path = root / "simulated-final-audit-report-complete.json"
    simulated_final_frontend_audit_inputs_summary_path = root / "simulated-final-audit-inputs-summary.json"
    simulated_final_frontend_audit_expected_statuses_path = root / "simulated-final-expected-statuses.json"
    ledger_after_final_frontend_audit_complete_path = root / "browser-execution-ledger-after-final-frontend-audit-complete.json"
    browser_stage_packet_after_final_frontend_audit_complete_path = (
        root / "next-browser-stage-packet-after-final-frontend-audit-complete.json"
    )
    simulated_cleanup_probes_partial_result_path = root / "simulated-cleanup-probes-partial-result.json"
    ledger_after_cleanup_probes_partial_path = root / "browser-execution-ledger-after-cleanup-probes-partial.json"
    browser_stage_packet_after_cleanup_probes_partial_recovery_path = (
        root / "next-browser-stage-packet-after-cleanup-probes-partial-recovery.json"
    )
    simulated_cleanup_probes_complete_result_path = root / "simulated-cleanup-probes-complete-result.json"
    ledger_after_cleanup_probes_complete_path = root / "browser-execution-ledger-after-cleanup-probes-complete.json"
    browser_runbook_summary_path = root / "browser-runbook-summary.json"

    require(summary.get("kind") == "allincms_full_rehearsal_summary", issues, "kind must be allincms_full_rehearsal_summary")
    require(summary.get("localOnly") is True, issues, "summary must be localOnly")
    require(summary.get("remoteMutationsPerformed") is False, issues, "summary must record no remote mutations")
    require(same_path(summary.get("fullE2EDir"), full_e2e_dir), issues, "fullE2EDir must point to sibling full-e2e directory")
    require(same_path(summary.get("handoffPath"), handoff_path), issues, "handoffPath must point to sibling handoff.json")
    require(same_path(summary.get("launchPlanPath"), launch_plan_path), issues, "launchPlanPath must point to sibling launch-plan.json")
    require(
        same_path(summary.get("browserExecutionPlanPath"), browser_execution_plan_path),
        issues,
        "browserExecutionPlanPath must point to sibling browser-execution-plan.json",
    )
    require(
        same_path(summary.get("browserExecutionLedgerPath"), browser_execution_ledger_path),
        issues,
        "browserExecutionLedgerPath must point to sibling browser-execution-ledger.json",
    )
    require(
        same_path(summary.get("browserStagePacketPath"), browser_stage_packet_path),
        issues,
        "browserStagePacketPath must point to sibling next-browser-stage-packet.json",
    )
    require(
        same_path(summary.get("browserStageEvidenceBundleDir"), browser_stage_evidence_bundle_dir),
        issues,
        "browserStageEvidenceBundleDir must point to sibling next-browser-stage-evidence-bundle directory",
    )
    require(
        same_path(summary.get("browserStageEvidenceManifestPath"), browser_stage_evidence_manifest_path),
        issues,
        "browserStageEvidenceManifestPath must point to sibling next-browser-stage-evidence-bundle/evidence-manifest.json",
    )
    require(
        same_path(summary.get("simulatedStageResultPath"), simulated_stage_result_path),
        issues,
        "simulatedStageResultPath must point to sibling simulated-first-stage-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterFirstStagePath"), ledger_after_first_stage_path),
        issues,
        "ledgerAfterFirstStagePath must point to sibling browser-execution-ledger-after-first-stage.json",
    )
    require(
        same_path(summary.get("browserStagePacketAfterFirstStagePath"), browser_stage_packet_after_first_stage_path),
        issues,
        "browserStagePacketAfterFirstStagePath must point to sibling next-browser-stage-packet-after-first-stage.json",
    )
    require(
        same_path(summary.get("simulatedCreateSiteResultPath"), simulated_create_site_result_path),
        issues,
        "simulatedCreateSiteResultPath must point to sibling simulated-create-site-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterCreateSitePath"), ledger_after_create_site_path),
        issues,
        "ledgerAfterCreateSitePath must point to sibling browser-execution-ledger-after-create-site.json",
    )
    require(
        same_path(summary.get("browserStagePacketAfterCreateSitePath"), browser_stage_packet_after_create_site_path),
        issues,
        "browserStagePacketAfterCreateSitePath must point to sibling next-browser-stage-packet-after-create-site.json",
    )
    require(
        same_path(summary.get("simulatedSetupResultPath"), simulated_setup_result_path),
        issues,
        "simulatedSetupResultPath must point to sibling simulated-setup-pages-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterSetupPath"), ledger_after_setup_path),
        issues,
        "ledgerAfterSetupPath must point to sibling browser-execution-ledger-after-setup-pages.json",
    )
    require(
        same_path(summary.get("browserStagePacketAfterSetupPath"), browser_stage_packet_after_setup_path),
        issues,
        "browserStagePacketAfterSetupPath must point to sibling next-browser-stage-packet-after-setup-pages.json",
    )
    require(
        same_path(
            summary.get("browserStageModuleCaptureAuthorizationPackagePath"),
            browser_stage_module_capture_authorization_package_path,
        ),
        issues,
        "browserStageModuleCaptureAuthorizationPackagePath must point to sibling browser-stage-module-interface-authorization-package.json",
    )
    require(
        same_path(summary.get("nextBrowserActionHandoffPath"), next_browser_action_handoff_path),
        issues,
        "nextBrowserActionHandoffPath must point to sibling next-browser-action-handoff.json",
    )
    require(
        same_path(summary.get("simulatedModuleCapturePartialResultPath"), simulated_module_capture_partial_result_path),
        issues,
        "simulatedModuleCapturePartialResultPath must point to sibling simulated-module-capture-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterModuleCapturePartialPath"), ledger_after_module_capture_partial_path),
        issues,
        "ledgerAfterModuleCapturePartialPath must point to sibling browser-execution-ledger-after-module-capture-partial.json",
    )
    require(
        same_path(summary.get("simulatedModuleCaptureStageResultPath"), simulated_module_capture_stage_result_path),
        issues,
        "simulatedModuleCaptureStageResultPath must point to sibling simulated-module-capture-stage-result.json",
    )
    require(
        same_path(summary.get("capturePlanGateCoveragePath"), capture_plan_gate_coverage_path),
        issues,
        "capturePlanGateCoveragePath must point to sibling capture-plan-gate-coverage.json",
    )
    require(
        same_path(summary.get("moduleCaptureCoveragePath"), module_capture_coverage_path),
        issues,
        "moduleCaptureCoveragePath must point to sibling module-capture-coverage-after-one-stage.json",
    )
    require(
        same_path(summary.get("ledgerAfterModuleCaptureCoverageSyncPath"), ledger_after_module_capture_coverage_sync_path),
        issues,
        "ledgerAfterModuleCaptureCoverageSyncPath must point to sibling browser-execution-ledger-after-module-capture-coverage-sync.json",
    )
    require(
        same_path(summary.get("moduleCaptureCoverageCompletePath"), module_capture_coverage_complete_path),
        issues,
        "moduleCaptureCoverageCompletePath must point to sibling module-capture-coverage-complete.json",
    )
    require(
        same_path(summary.get("ledgerAfterModuleCaptureCompletePath"), ledger_after_module_capture_complete_path),
        issues,
        "ledgerAfterModuleCaptureCompletePath must point to sibling browser-execution-ledger-after-module-capture-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterModuleCaptureCompletePath"),
            browser_stage_packet_after_module_capture_complete_path,
        ),
        issues,
        "browserStagePacketAfterModuleCaptureCompletePath must point to sibling next-browser-stage-packet-after-module-capture-complete.json",
    )
    require(
        same_path(summary.get("simulatedThemeLaunchPartialResultPath"), simulated_theme_launch_partial_result_path),
        issues,
        "simulatedThemeLaunchPartialResultPath must point to sibling simulated-theme-launch-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterThemeLaunchPartialPath"), ledger_after_theme_launch_partial_path),
        issues,
        "ledgerAfterThemeLaunchPartialPath must point to sibling browser-execution-ledger-after-theme-launch-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterThemeLaunchPartialRecoveryPath"),
            browser_stage_packet_after_theme_launch_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterThemeLaunchPartialRecoveryPath must point to sibling next-browser-stage-packet-after-theme-launch-partial-recovery.json",
    )
    require(
        same_path(
            summary.get("ledgerAfterThemeLaunchRecoveryCompletePath"),
            ledger_after_theme_launch_recovery_complete_path,
        ),
        issues,
        "ledgerAfterThemeLaunchRecoveryCompletePath must point to sibling browser-execution-ledger-after-theme-launch-recovery-complete.json",
    )
    require(
        same_path(summary.get("simulatedThemeLaunchCompleteResultPath"), simulated_theme_launch_complete_result_path),
        issues,
        "simulatedThemeLaunchCompleteResultPath must point to sibling simulated-theme-launch-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterThemeLaunchCompletePath"), ledger_after_theme_launch_complete_path),
        issues,
        "ledgerAfterThemeLaunchCompletePath must point to sibling browser-execution-ledger-after-theme-launch-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterThemeLaunchCompletePath"),
            browser_stage_packet_after_theme_launch_complete_path,
        ),
        issues,
        "browserStagePacketAfterThemeLaunchCompletePath must point to sibling next-browser-stage-packet-after-theme-launch-complete.json",
    )
    require(
        same_path(summary.get("simulatedStaticAuditPartialResultPath"), simulated_static_audit_partial_result_path),
        issues,
        "simulatedStaticAuditPartialResultPath must point to sibling simulated-static-audit-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterStaticAuditPartialPath"), ledger_after_static_audit_partial_path),
        issues,
        "ledgerAfterStaticAuditPartialPath must point to sibling browser-execution-ledger-after-static-audit-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterStaticAuditPartialRecoveryPath"),
            browser_stage_packet_after_static_audit_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterStaticAuditPartialRecoveryPath must point to sibling next-browser-stage-packet-after-static-audit-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedStaticAuditCompleteResultPath"), simulated_static_audit_complete_result_path),
        issues,
        "simulatedStaticAuditCompleteResultPath must point to sibling simulated-static-audit-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterStaticAuditCompletePath"), ledger_after_static_audit_complete_path),
        issues,
        "ledgerAfterStaticAuditCompletePath must point to sibling browser-execution-ledger-after-static-audit-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterStaticAuditCompletePath"),
            browser_stage_packet_after_static_audit_complete_path,
        ),
        issues,
        "browserStagePacketAfterStaticAuditCompletePath must point to sibling next-browser-stage-packet-after-static-audit-complete.json",
    )
    require(
        same_path(summary.get("simulatedContentProbePartialResultPath"), simulated_content_probe_partial_result_path),
        issues,
        "simulatedContentProbePartialResultPath must point to sibling simulated-content-probe-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterContentProbePartialPath"), ledger_after_content_probe_partial_path),
        issues,
        "ledgerAfterContentProbePartialPath must point to sibling browser-execution-ledger-after-content-probe-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterContentProbePartialRecoveryPath"),
            browser_stage_packet_after_content_probe_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterContentProbePartialRecoveryPath must point to sibling next-browser-stage-packet-after-content-probe-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedContentProbeCompleteResultPath"), simulated_content_probe_complete_result_path),
        issues,
        "simulatedContentProbeCompleteResultPath must point to sibling simulated-content-probe-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterContentProbeCompletePath"), ledger_after_content_probe_complete_path),
        issues,
        "ledgerAfterContentProbeCompletePath must point to sibling browser-execution-ledger-after-content-probe-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterContentProbeCompletePath"),
            browser_stage_packet_after_content_probe_complete_path,
        ),
        issues,
        "browserStagePacketAfterContentProbeCompletePath must point to sibling next-browser-stage-packet-after-content-probe-complete.json",
    )
    require(
        same_path(summary.get("simulatedSaveRequestPartialResultPath"), simulated_save_request_partial_result_path),
        issues,
        "simulatedSaveRequestPartialResultPath must point to sibling simulated-save-request-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterSaveRequestPartialPath"), ledger_after_save_request_partial_path),
        issues,
        "ledgerAfterSaveRequestPartialPath must point to sibling browser-execution-ledger-after-save-request-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterSaveRequestPartialRecoveryPath"),
            browser_stage_packet_after_save_request_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterSaveRequestPartialRecoveryPath must point to sibling next-browser-stage-packet-after-save-request-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedSaveRequestCompleteResultPath"), simulated_save_request_complete_result_path),
        issues,
        "simulatedSaveRequestCompleteResultPath must point to sibling simulated-save-request-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterSaveRequestCompletePath"), ledger_after_save_request_complete_path),
        issues,
        "ledgerAfterSaveRequestCompletePath must point to sibling browser-execution-ledger-after-save-request-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterSaveRequestCompletePath"),
            browser_stage_packet_after_save_request_complete_path,
        ),
        issues,
        "browserStagePacketAfterSaveRequestCompletePath must point to sibling next-browser-stage-packet-after-save-request-complete.json",
    )
    require(
        same_path(summary.get("simulatedPublishSamplePartialResultPath"), simulated_publish_sample_partial_result_path),
        issues,
        "simulatedPublishSamplePartialResultPath must point to sibling simulated-publish-sample-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterPublishSamplePartialPath"), ledger_after_publish_sample_partial_path),
        issues,
        "ledgerAfterPublishSamplePartialPath must point to sibling browser-execution-ledger-after-publish-sample-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterPublishSamplePartialRecoveryPath"),
            browser_stage_packet_after_publish_sample_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterPublishSamplePartialRecoveryPath must point to sibling next-browser-stage-packet-after-publish-sample-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedPublishSampleCompleteResultPath"), simulated_publish_sample_complete_result_path),
        issues,
        "simulatedPublishSampleCompleteResultPath must point to sibling simulated-publish-sample-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterPublishSampleCompletePath"), ledger_after_publish_sample_complete_path),
        issues,
        "ledgerAfterPublishSampleCompletePath must point to sibling browser-execution-ledger-after-publish-sample-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterPublishSampleCompletePath"),
            browser_stage_packet_after_publish_sample_complete_path,
        ),
        issues,
        "browserStagePacketAfterPublishSampleCompletePath must point to sibling next-browser-stage-packet-after-publish-sample-complete.json",
    )
    require(
        same_path(summary.get("simulatedManifestGatePartialResultPath"), simulated_manifest_gate_partial_result_path),
        issues,
        "simulatedManifestGatePartialResultPath must point to sibling simulated-manifest-gate-partial-result.json",
    )
    if not source_input_requirements_path.exists():
        issues.append("source-input-requirements.json must exist under full-e2e/04-manifest-rehearsal")
    require(
        same_path(summary.get("ledgerAfterManifestGatePartialPath"), ledger_after_manifest_gate_partial_path),
        issues,
        "ledgerAfterManifestGatePartialPath must point to sibling browser-execution-ledger-after-manifest-gate-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterManifestGatePartialRecoveryPath"),
            browser_stage_packet_after_manifest_gate_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterManifestGatePartialRecoveryPath must point to sibling next-browser-stage-packet-after-manifest-gate-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedManifestGateCompleteResultPath"), simulated_manifest_gate_complete_result_path),
        issues,
        "simulatedManifestGateCompleteResultPath must point to sibling simulated-manifest-gate-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterManifestGateCompletePath"), ledger_after_manifest_gate_complete_path),
        issues,
        "ledgerAfterManifestGateCompletePath must point to sibling browser-execution-ledger-after-manifest-gate-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterManifestGateCompletePath"),
            browser_stage_packet_after_manifest_gate_complete_path,
        ),
        issues,
        "browserStagePacketAfterManifestGateCompletePath must point to sibling next-browser-stage-packet-after-manifest-gate-complete.json",
    )
    require(
        same_path(summary.get("simulatedBatchUploadPartialResultPath"), simulated_batch_upload_partial_result_path),
        issues,
        "simulatedBatchUploadPartialResultPath must point to sibling simulated-batch-upload-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterBatchUploadPartialPath"), ledger_after_batch_upload_partial_path),
        issues,
        "ledgerAfterBatchUploadPartialPath must point to sibling browser-execution-ledger-after-batch-upload-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterBatchUploadPartialRecoveryPath"),
            browser_stage_packet_after_batch_upload_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterBatchUploadPartialRecoveryPath must point to sibling next-browser-stage-packet-after-batch-upload-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedBatchUploadCompleteResultPath"), simulated_batch_upload_complete_result_path),
        issues,
        "simulatedBatchUploadCompleteResultPath must point to sibling simulated-batch-upload-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterBatchUploadCompletePath"), ledger_after_batch_upload_complete_path),
        issues,
        "ledgerAfterBatchUploadCompletePath must point to sibling browser-execution-ledger-after-batch-upload-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterBatchUploadCompletePath"),
            browser_stage_packet_after_batch_upload_complete_path,
        ),
        issues,
        "browserStagePacketAfterBatchUploadCompletePath must point to sibling next-browser-stage-packet-after-batch-upload-complete.json",
    )
    require(
        same_path(
            summary.get("simulatedFormsMediaSettingsPartialResultPath"),
            simulated_forms_media_settings_partial_result_path,
        ),
        issues,
        "simulatedFormsMediaSettingsPartialResultPath must point to sibling simulated-forms-media-settings-partial-result.json",
    )
    require(
        same_path(
            summary.get("ledgerAfterFormsMediaSettingsPartialPath"),
            ledger_after_forms_media_settings_partial_path,
        ),
        issues,
        "ledgerAfterFormsMediaSettingsPartialPath must point to sibling browser-execution-ledger-after-forms-media-settings-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterFormsMediaSettingsPartialRecoveryPath"),
            browser_stage_packet_after_forms_media_settings_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterFormsMediaSettingsPartialRecoveryPath must point to sibling next-browser-stage-packet-after-forms-media-settings-partial-recovery.json",
    )
    require(
        same_path(
            summary.get("simulatedFormsMediaSettingsCompleteResultPath"),
            simulated_forms_media_settings_complete_result_path,
        ),
        issues,
        "simulatedFormsMediaSettingsCompleteResultPath must point to sibling simulated-forms-media-settings-complete-result.json",
    )
    require(
        same_path(
            summary.get("ledgerAfterFormsMediaSettingsCompletePath"),
            ledger_after_forms_media_settings_complete_path,
        ),
        issues,
        "ledgerAfterFormsMediaSettingsCompletePath must point to sibling browser-execution-ledger-after-forms-media-settings-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterFormsMediaSettingsCompletePath"),
            browser_stage_packet_after_forms_media_settings_complete_path,
        ),
        issues,
        "browserStagePacketAfterFormsMediaSettingsCompletePath must point to sibling next-browser-stage-packet-after-forms-media-settings-complete.json",
    )
    require(
        same_path(
            summary.get("simulatedFinalFrontendAuditPartialResultPath"),
            simulated_final_frontend_audit_partial_result_path,
        ),
        issues,
        "simulatedFinalFrontendAuditPartialResultPath must point to sibling simulated-final-frontend-audit-partial-result.json",
    )
    require(
        same_path(
            summary.get("ledgerAfterFinalFrontendAuditPartialPath"),
            ledger_after_final_frontend_audit_partial_path,
        ),
        issues,
        "ledgerAfterFinalFrontendAuditPartialPath must point to sibling browser-execution-ledger-after-final-frontend-audit-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterFinalFrontendAuditPartialRecoveryPath"),
            browser_stage_packet_after_final_frontend_audit_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterFinalFrontendAuditPartialRecoveryPath must point to sibling next-browser-stage-packet-after-final-frontend-audit-partial-recovery.json",
    )
    require(
        same_path(
            summary.get("simulatedFinalFrontendAuditCompleteResultPath"),
            simulated_final_frontend_audit_complete_result_path,
        ),
        issues,
        "simulatedFinalFrontendAuditCompleteResultPath must point to sibling simulated-final-frontend-audit-complete-result.json",
    )
    require(
        same_path(
            summary.get("ledgerAfterFinalFrontendAuditCompletePath"),
            ledger_after_final_frontend_audit_complete_path,
        ),
        issues,
        "ledgerAfterFinalFrontendAuditCompletePath must point to sibling browser-execution-ledger-after-final-frontend-audit-complete.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterFinalFrontendAuditCompletePath"),
            browser_stage_packet_after_final_frontend_audit_complete_path,
        ),
        issues,
        "browserStagePacketAfterFinalFrontendAuditCompletePath must point to sibling next-browser-stage-packet-after-final-frontend-audit-complete.json",
    )
    require(
        same_path(summary.get("simulatedCleanupProbesPartialResultPath"), simulated_cleanup_probes_partial_result_path),
        issues,
        "simulatedCleanupProbesPartialResultPath must point to sibling simulated-cleanup-probes-partial-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterCleanupProbesPartialPath"), ledger_after_cleanup_probes_partial_path),
        issues,
        "ledgerAfterCleanupProbesPartialPath must point to sibling browser-execution-ledger-after-cleanup-probes-partial.json",
    )
    require(
        same_path(
            summary.get("browserStagePacketAfterCleanupProbesPartialRecoveryPath"),
            browser_stage_packet_after_cleanup_probes_partial_recovery_path,
        ),
        issues,
        "browserStagePacketAfterCleanupProbesPartialRecoveryPath must point to sibling next-browser-stage-packet-after-cleanup-probes-partial-recovery.json",
    )
    require(
        same_path(summary.get("simulatedCleanupProbesCompleteResultPath"), simulated_cleanup_probes_complete_result_path),
        issues,
        "simulatedCleanupProbesCompleteResultPath must point to sibling simulated-cleanup-probes-complete-result.json",
    )
    require(
        same_path(summary.get("ledgerAfterCleanupProbesCompletePath"), ledger_after_cleanup_probes_complete_path),
        issues,
        "ledgerAfterCleanupProbesCompletePath must point to sibling browser-execution-ledger-after-cleanup-probes-complete.json",
    )
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        artifacts = {}
    require(same_path(artifacts.get("handoff"), handoff_path), issues, "artifacts.handoff mismatch")
    require(same_path(artifacts.get("launchPlan"), launch_plan_path), issues, "artifacts.launchPlan mismatch")
    require(
        same_path(artifacts.get("browserExecutionPlan"), browser_execution_plan_path),
        issues,
        "artifacts.browserExecutionPlan mismatch",
    )
    require(
        same_path(artifacts.get("browserExecutionLedger"), browser_execution_ledger_path),
        issues,
        "artifacts.browserExecutionLedger mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacket"), browser_stage_packet_path),
        issues,
        "artifacts.browserStagePacket mismatch",
    )
    require(
        same_path(artifacts.get("browserStageEvidenceBundle"), browser_stage_evidence_bundle_dir),
        issues,
        "artifacts.browserStageEvidenceBundle mismatch",
    )
    require(
        same_path(artifacts.get("browserStageEvidenceManifest"), browser_stage_evidence_manifest_path),
        issues,
        "artifacts.browserStageEvidenceManifest mismatch",
    )
    require(
        same_path(artifacts.get("simulatedStageResult"), simulated_stage_result_path),
        issues,
        "artifacts.simulatedStageResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterFirstStage"), ledger_after_first_stage_path),
        issues,
        "artifacts.ledgerAfterFirstStage mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterFirstStage"), browser_stage_packet_after_first_stage_path),
        issues,
        "artifacts.browserStagePacketAfterFirstStage mismatch",
    )
    require(
        same_path(artifacts.get("simulatedCreateSiteResult"), simulated_create_site_result_path),
        issues,
        "artifacts.simulatedCreateSiteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterCreateSite"), ledger_after_create_site_path),
        issues,
        "artifacts.ledgerAfterCreateSite mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterCreateSite"), browser_stage_packet_after_create_site_path),
        issues,
        "artifacts.browserStagePacketAfterCreateSite mismatch",
    )
    require(
        same_path(artifacts.get("simulatedSetupResult"), simulated_setup_result_path),
        issues,
        "artifacts.simulatedSetupResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterSetup"), ledger_after_setup_path),
        issues,
        "artifacts.ledgerAfterSetup mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterSetup"), browser_stage_packet_after_setup_path),
        issues,
        "artifacts.browserStagePacketAfterSetup mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStageModuleCaptureAuthorizationPackage"),
            browser_stage_module_capture_authorization_package_path,
        ),
        issues,
        "artifacts.browserStageModuleCaptureAuthorizationPackage mismatch",
    )
    require(
        same_path(artifacts.get("nextBrowserActionHandoff"), next_browser_action_handoff_path),
        issues,
        "artifacts.nextBrowserActionHandoff mismatch",
    )
    require(
        same_path(artifacts.get("simulatedModuleCapturePartialResult"), simulated_module_capture_partial_result_path),
        issues,
        "artifacts.simulatedModuleCapturePartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterModuleCapturePartial"), ledger_after_module_capture_partial_path),
        issues,
        "artifacts.ledgerAfterModuleCapturePartial mismatch",
    )
    require(
        same_path(artifacts.get("simulatedModuleCaptureStageResult"), simulated_module_capture_stage_result_path),
        issues,
        "artifacts.simulatedModuleCaptureStageResult mismatch",
    )
    require(
        same_path(artifacts.get("capturePlanGateCoverage"), capture_plan_gate_coverage_path),
        issues,
        "artifacts.capturePlanGateCoverage mismatch",
    )
    require(
        same_path(artifacts.get("moduleCaptureCoverage"), module_capture_coverage_path),
        issues,
        "artifacts.moduleCaptureCoverage mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterModuleCaptureCoverageSync"), ledger_after_module_capture_coverage_sync_path),
        issues,
        "artifacts.ledgerAfterModuleCaptureCoverageSync mismatch",
    )
    require(
        same_path(artifacts.get("moduleCaptureCoverageComplete"), module_capture_coverage_complete_path),
        issues,
        "artifacts.moduleCaptureCoverageComplete mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterModuleCaptureComplete"), ledger_after_module_capture_complete_path),
        issues,
        "artifacts.ledgerAfterModuleCaptureComplete mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterModuleCaptureComplete"),
            browser_stage_packet_after_module_capture_complete_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterModuleCaptureComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedThemeLaunchPartialResult"), simulated_theme_launch_partial_result_path),
        issues,
        "artifacts.simulatedThemeLaunchPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterThemeLaunchPartial"), ledger_after_theme_launch_partial_path),
        issues,
        "artifacts.ledgerAfterThemeLaunchPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterThemeLaunchPartialRecovery"),
            browser_stage_packet_after_theme_launch_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterThemeLaunchPartialRecovery mismatch",
    )
    require(
        same_path(
            artifacts.get("ledgerAfterThemeLaunchRecoveryComplete"),
            ledger_after_theme_launch_recovery_complete_path,
        ),
        issues,
        "artifacts.ledgerAfterThemeLaunchRecoveryComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedThemeLaunchCompleteResult"), simulated_theme_launch_complete_result_path),
        issues,
        "artifacts.simulatedThemeLaunchCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterThemeLaunchComplete"), ledger_after_theme_launch_complete_path),
        issues,
        "artifacts.ledgerAfterThemeLaunchComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterThemeLaunchComplete"), browser_stage_packet_after_theme_launch_complete_path),
        issues,
        "artifacts.browserStagePacketAfterThemeLaunchComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedStaticAuditPartialResult"), simulated_static_audit_partial_result_path),
        issues,
        "artifacts.simulatedStaticAuditPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterStaticAuditPartial"), ledger_after_static_audit_partial_path),
        issues,
        "artifacts.ledgerAfterStaticAuditPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterStaticAuditPartialRecovery"),
            browser_stage_packet_after_static_audit_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterStaticAuditPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedStaticAuditCompleteResult"), simulated_static_audit_complete_result_path),
        issues,
        "artifacts.simulatedStaticAuditCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterStaticAuditComplete"), ledger_after_static_audit_complete_path),
        issues,
        "artifacts.ledgerAfterStaticAuditComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterStaticAuditComplete"), browser_stage_packet_after_static_audit_complete_path),
        issues,
        "artifacts.browserStagePacketAfterStaticAuditComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedContentProbePartialResult"), simulated_content_probe_partial_result_path),
        issues,
        "artifacts.simulatedContentProbePartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterContentProbePartial"), ledger_after_content_probe_partial_path),
        issues,
        "artifacts.ledgerAfterContentProbePartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterContentProbePartialRecovery"),
            browser_stage_packet_after_content_probe_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterContentProbePartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedContentProbeCompleteResult"), simulated_content_probe_complete_result_path),
        issues,
        "artifacts.simulatedContentProbeCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterContentProbeComplete"), ledger_after_content_probe_complete_path),
        issues,
        "artifacts.ledgerAfterContentProbeComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterContentProbeComplete"), browser_stage_packet_after_content_probe_complete_path),
        issues,
        "artifacts.browserStagePacketAfterContentProbeComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedSaveRequestPartialResult"), simulated_save_request_partial_result_path),
        issues,
        "artifacts.simulatedSaveRequestPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterSaveRequestPartial"), ledger_after_save_request_partial_path),
        issues,
        "artifacts.ledgerAfterSaveRequestPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterSaveRequestPartialRecovery"),
            browser_stage_packet_after_save_request_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterSaveRequestPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedSaveRequestCompleteResult"), simulated_save_request_complete_result_path),
        issues,
        "artifacts.simulatedSaveRequestCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterSaveRequestComplete"), ledger_after_save_request_complete_path),
        issues,
        "artifacts.ledgerAfterSaveRequestComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterSaveRequestComplete"), browser_stage_packet_after_save_request_complete_path),
        issues,
        "artifacts.browserStagePacketAfterSaveRequestComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedPublishSamplePartialResult"), simulated_publish_sample_partial_result_path),
        issues,
        "artifacts.simulatedPublishSamplePartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterPublishSamplePartial"), ledger_after_publish_sample_partial_path),
        issues,
        "artifacts.ledgerAfterPublishSamplePartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterPublishSamplePartialRecovery"),
            browser_stage_packet_after_publish_sample_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterPublishSamplePartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedPublishSampleCompleteResult"), simulated_publish_sample_complete_result_path),
        issues,
        "artifacts.simulatedPublishSampleCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterPublishSampleComplete"), ledger_after_publish_sample_complete_path),
        issues,
        "artifacts.ledgerAfterPublishSampleComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterPublishSampleComplete"), browser_stage_packet_after_publish_sample_complete_path),
        issues,
        "artifacts.browserStagePacketAfterPublishSampleComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedManifestGatePartialResult"), simulated_manifest_gate_partial_result_path),
        issues,
        "artifacts.simulatedManifestGatePartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterManifestGatePartial"), ledger_after_manifest_gate_partial_path),
        issues,
        "artifacts.ledgerAfterManifestGatePartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterManifestGatePartialRecovery"),
            browser_stage_packet_after_manifest_gate_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterManifestGatePartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedManifestGateCompleteResult"), simulated_manifest_gate_complete_result_path),
        issues,
        "artifacts.simulatedManifestGateCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterManifestGateComplete"), ledger_after_manifest_gate_complete_path),
        issues,
        "artifacts.ledgerAfterManifestGateComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterManifestGateComplete"), browser_stage_packet_after_manifest_gate_complete_path),
        issues,
        "artifacts.browserStagePacketAfterManifestGateComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedBatchUploadPartialResult"), simulated_batch_upload_partial_result_path),
        issues,
        "artifacts.simulatedBatchUploadPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterBatchUploadPartial"), ledger_after_batch_upload_partial_path),
        issues,
        "artifacts.ledgerAfterBatchUploadPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterBatchUploadPartialRecovery"),
            browser_stage_packet_after_batch_upload_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterBatchUploadPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedBatchUploadCompleteResult"), simulated_batch_upload_complete_result_path),
        issues,
        "artifacts.simulatedBatchUploadCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterBatchUploadComplete"), ledger_after_batch_upload_complete_path),
        issues,
        "artifacts.ledgerAfterBatchUploadComplete mismatch",
    )
    require(
        same_path(artifacts.get("browserStagePacketAfterBatchUploadComplete"), browser_stage_packet_after_batch_upload_complete_path),
        issues,
        "artifacts.browserStagePacketAfterBatchUploadComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFormsMediaSettingsPartialResult"), simulated_forms_media_settings_partial_result_path),
        issues,
        "artifacts.simulatedFormsMediaSettingsPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterFormsMediaSettingsPartial"), ledger_after_forms_media_settings_partial_path),
        issues,
        "artifacts.ledgerAfterFormsMediaSettingsPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterFormsMediaSettingsPartialRecovery"),
            browser_stage_packet_after_forms_media_settings_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterFormsMediaSettingsPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFormsMediaSettingsCompleteResult"), simulated_forms_media_settings_complete_result_path),
        issues,
        "artifacts.simulatedFormsMediaSettingsCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterFormsMediaSettingsComplete"), ledger_after_forms_media_settings_complete_path),
        issues,
        "artifacts.ledgerAfterFormsMediaSettingsComplete mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterFormsMediaSettingsComplete"),
            browser_stage_packet_after_forms_media_settings_complete_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterFormsMediaSettingsComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFinalFrontendAuditPartialResult"), simulated_final_frontend_audit_partial_result_path),
        issues,
        "artifacts.simulatedFinalFrontendAuditPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFinalFrontendAuditPartialReport"), simulated_final_frontend_audit_partial_report_path),
        issues,
        "artifacts.simulatedFinalFrontendAuditPartialReport mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterFinalFrontendAuditPartial"), ledger_after_final_frontend_audit_partial_path),
        issues,
        "artifacts.ledgerAfterFinalFrontendAuditPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterFinalFrontendAuditPartialRecovery"),
            browser_stage_packet_after_final_frontend_audit_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterFinalFrontendAuditPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFinalFrontendAuditCompleteResult"), simulated_final_frontend_audit_complete_result_path),
        issues,
        "artifacts.simulatedFinalFrontendAuditCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFinalFrontendAuditCompleteReport"), simulated_final_frontend_audit_complete_report_path),
        issues,
        "artifacts.simulatedFinalFrontendAuditCompleteReport mismatch",
    )
    require(
        same_path(artifacts.get("simulatedFinalFrontendAuditInputsSummary"), simulated_final_frontend_audit_inputs_summary_path),
        issues,
        "artifacts.simulatedFinalFrontendAuditInputsSummary mismatch",
    )
    require(
        same_path(
            artifacts.get("simulatedFinalFrontendAuditExpectedStatuses"),
            simulated_final_frontend_audit_expected_statuses_path,
        ),
        issues,
        "artifacts.simulatedFinalFrontendAuditExpectedStatuses mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterFinalFrontendAuditComplete"), ledger_after_final_frontend_audit_complete_path),
        issues,
        "artifacts.ledgerAfterFinalFrontendAuditComplete mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterFinalFrontendAuditComplete"),
            browser_stage_packet_after_final_frontend_audit_complete_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterFinalFrontendAuditComplete mismatch",
    )
    require(
        same_path(artifacts.get("simulatedCleanupProbesPartialResult"), simulated_cleanup_probes_partial_result_path),
        issues,
        "artifacts.simulatedCleanupProbesPartialResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterCleanupProbesPartial"), ledger_after_cleanup_probes_partial_path),
        issues,
        "artifacts.ledgerAfterCleanupProbesPartial mismatch",
    )
    require(
        same_path(
            artifacts.get("browserStagePacketAfterCleanupProbesPartialRecovery"),
            browser_stage_packet_after_cleanup_probes_partial_recovery_path,
        ),
        issues,
        "artifacts.browserStagePacketAfterCleanupProbesPartialRecovery mismatch",
    )
    require(
        same_path(artifacts.get("simulatedCleanupProbesCompleteResult"), simulated_cleanup_probes_complete_result_path),
        issues,
        "artifacts.simulatedCleanupProbesCompleteResult mismatch",
    )
    require(
        same_path(artifacts.get("ledgerAfterCleanupProbesComplete"), ledger_after_cleanup_probes_complete_path),
        issues,
        "artifacts.ledgerAfterCleanupProbesComplete mismatch",
    )
    require(same_path(artifacts.get("draftManifest"), full_e2e_dir / "04-manifest-rehearsal" / "draft-manifest.json"), issues, "artifacts.draftManifest mismatch")
    require(
        same_path(artifacts.get("sourceInputRequirements"), source_input_requirements_path),
        issues,
        "artifacts.sourceInputRequirements mismatch",
    )
    require(
        same_path(artifacts.get("manifestSummary"), full_e2e_dir / "04-manifest-rehearsal" / "manifest-rehearsal-summary.json"),
        issues,
        "artifacts.manifestSummary mismatch",
    )
    require(same_path(artifacts.get("rehearsalSummary"), summary_path), issues, "artifacts.rehearsalSummary mismatch")
    runbook_declared = "browserRunbookSummaryPath" in summary or "browserRunbookSummary" in artifacts
    if runbook_declared:
        require(
            same_path(summary.get("browserRunbookSummaryPath"), browser_runbook_summary_path),
            issues,
            "browserRunbookSummaryPath must point to sibling browser-runbook-summary.json",
        )
        require(
            same_path(artifacts.get("browserRunbookSummary"), browser_runbook_summary_path),
            issues,
            "artifacts.browserRunbookSummary mismatch",
        )

    full_validation = validate_directory(full_e2e_dir)
    issues.extend(f"full E2E: {issue}" for issue in full_validation.get("issues", []))
    require(full_validation.get("ok") is True, issues, "full E2E validation must pass")

    try:
        module_capture_plan_for_gate = load_json(full_e2e_dir / "03-module-interface-plan" / "module-capture-plan.json")
    except ValueError as exc:
        module_capture_plan_for_gate = {}
        issues.append(str(exc))
    capture_plan_gate_coverage = validate_plan_gate_coverage(module_capture_plan_for_gate)
    issues.extend(f"capture plan gate coverage: {issue}" for issue in capture_plan_gate_coverage.get("issues", []))
    try:
        capture_plan_gate_coverage_artifact = load_json(capture_plan_gate_coverage_path)
    except ValueError as exc:
        capture_plan_gate_coverage_artifact = {}
        issues.append(str(exc))
    require(
        capture_plan_gate_coverage.get("ok") is True,
        issues,
        "capture plan gate coverage validation must pass",
    )
    require(
        capture_plan_gate_coverage_artifact == capture_plan_gate_coverage,
        issues,
        "capture-plan-gate-coverage.json must match recomputed coverage",
    )
    capture_plan_gate_coverage_summary = summary.get("capturePlanGateCoverage")
    if not isinstance(capture_plan_gate_coverage_summary, dict):
        issues.append("capturePlanGateCoverage summary must be an object")
        capture_plan_gate_coverage_summary = {}
    require(
        capture_plan_gate_coverage_summary.get("ok") is True,
        issues,
        "capturePlanGateCoverage.ok must be true",
    )
    require(
        capture_plan_gate_coverage_summary.get("stageCount") == capture_plan_gate_coverage.get("stageCount"),
        issues,
        "capturePlanGateCoverage.stageCount must match coverage artifact",
    )
    require(
        capture_plan_gate_coverage_summary.get("coveredActions") == capture_plan_gate_coverage.get("coveredActions"),
        issues,
        "capturePlanGateCoverage.coveredActions must match coverage artifact",
    )
    require(
        capture_plan_gate_coverage_summary.get("ungatedAllowedActions")
        == capture_plan_gate_coverage.get("ungatedAllowedActions"),
        issues,
        "capturePlanGateCoverage.ungatedAllowedActions must match coverage artifact",
    )
    require(summary.get("fullE2EValidation", {}).get("ok") is True, issues, "summary.fullE2EValidation.ok must be true")
    manifest_summary = summary.get("manifestRehearsal") if isinstance(summary.get("manifestRehearsal"), dict) else {}
    require(
        manifest_summary.get("sourceInputRequirementsGenerated") is True,
        issues,
        "summary.manifestRehearsal.sourceInputRequirementsGenerated must be true",
    )
    require(
        manifest_summary.get("sourceInputRequirementsBlocked") is True,
        issues,
        "summary.manifestRehearsal.sourceInputRequirementsBlocked must be true for draft rehearsal",
    )
    require(
        isinstance(manifest_summary.get("sourceInputRequirementsBlockedUntilCount"), int)
        and manifest_summary.get("sourceInputRequirementsBlockedUntilCount") > 0,
        issues,
        "summary.manifestRehearsal.sourceInputRequirementsBlockedUntilCount must be positive",
    )
    try:
        source_requirements = load_json(source_input_requirements_path)
    except Exception as exc:  # noqa: BLE001 - report as validation issue.
        source_requirements = {}
        issues.append(f"could not load source-input-requirements.json: {exc}")
    operation_gaps = source_requirements.get("operationGaps") if isinstance(source_requirements, dict) else {}
    require(
        isinstance(operation_gaps, dict) and operation_gaps.get("entryCount", 0) > 0,
        issues,
        "source-input-requirements operationGaps.entryCount must be positive",
    )
    require(manifest_summary.get("draftValidationPassed") is True, issues, "summary.manifestRehearsal.draftValidationPassed must be true")
    require(
        manifest_summary.get("schemaGateExpectedFailure") is True,
        issues,
        "summary.manifestRehearsal.schemaGateExpectedFailure must be true",
    )

    try:
        handoff = load_json(handoff_path)
    except ValueError as exc:
        handoff = {}
        issues.append(str(exc))
    handoff_validation = validate_handoff(handoff)
    issues.extend(f"handoff: {issue}" for issue in handoff_validation.get("issues", []))
    require(handoff_validation.get("ok") is True, issues, "handoff safety validation must pass")
    require(summary.get("handoffSafety", {}).get("ok") is True, issues, "summary.handoffSafety.ok must be true")
    require(summary.get("commandsSuppressed") == handoff.get("commandsSuppressed"), issues, "commandsSuppressed mismatch")
    require(summary.get("allowCommandOutput") is False, issues, "default rehearsal summary must not allow command output")

    try:
        launch_plan = load_json(launch_plan_path)
    except ValueError as exc:
        launch_plan = {}
        issues.append(str(exc))
    launch_validation = validate_launch_plan(launch_plan)
    issues.extend(f"launch plan: {issue}" for issue in launch_validation.get("issues", []))
    require(launch_validation.get("ok") is True, issues, "launch plan validation must pass")
    require(summary.get("launchPlanSafety", {}).get("ok") is True, issues, "summary.launchPlanSafety.ok must be true")

    try:
        browser_execution_plan = load_json(browser_execution_plan_path)
    except ValueError as exc:
        browser_execution_plan = {}
        issues.append(str(exc))
    browser_execution_validation = validate_browser_execution_plan(browser_execution_plan)
    issues.extend(f"browser execution plan: {issue}" for issue in browser_execution_validation.get("issues", []))
    require(browser_execution_validation.get("ok") is True, issues, "browser execution plan validation must pass")
    require(
        summary.get("browserExecutionPlanSafety", {}).get("ok") is True,
        issues,
        "summary.browserExecutionPlanSafety.ok must be true",
    )

    try:
        browser_execution_ledger = load_json(browser_execution_ledger_path)
    except ValueError as exc:
        browser_execution_ledger = {}
        issues.append(str(exc))
    browser_execution_ledger_validation = validate_browser_execution_ledger(browser_execution_ledger)
    issues.extend(f"browser execution ledger: {issue}" for issue in browser_execution_ledger_validation.get("issues", []))
    require(browser_execution_ledger_validation.get("ok") is True, issues, "browser execution ledger validation must pass")
    require(
        summary.get("browserExecutionLedgerSafety", {}).get("ok") is True,
        issues,
        "summary.browserExecutionLedgerSafety.ok must be true",
    )

    try:
        browser_stage_packet = load_json(browser_stage_packet_path)
    except ValueError as exc:
        browser_stage_packet = {}
        issues.append(str(exc))
    browser_stage_packet_validation = validate_browser_stage_packet(browser_stage_packet)
    issues.extend(f"browser stage packet: {issue}" for issue in browser_stage_packet_validation.get("issues", []))
    require(browser_stage_packet_validation.get("ok") is True, issues, "browser stage packet validation must pass")
    validate_packet_command_paths(
        "browser stage packet",
        browser_stage_packet,
        browser_execution_ledger_path,
        browser_stage_packet_path,
        issues,
    )
    require(
        summary.get("browserStagePacketSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketSafety.ok must be true",
    )
    browser_stage_evidence_bundle_validation = validate_browser_stage_evidence_bundle(
        browser_stage_evidence_bundle_dir,
        browser_stage_packet_path,
    )
    issues.extend(f"browser stage evidence bundle: {issue}" for issue in browser_stage_evidence_bundle_validation.get("issues", []))
    require(
        browser_stage_evidence_bundle_validation.get("ok") is True,
        issues,
        "browser stage evidence bundle validation must pass",
    )
    try:
        browser_stage_evidence_manifest = load_json(browser_stage_evidence_manifest_path)
    except ValueError as exc:
        browser_stage_evidence_manifest = {}
        issues.append(str(exc))
    require(
        summary.get("browserStageEvidenceManifest", {}).get("stageId") == browser_stage_packet.get("stageId"),
        issues,
        "summary.browserStageEvidenceManifest.stageId must match first packet",
    )
    require(
        summary.get("browserStageEvidenceBundleSafety", {}).get("ok") is True,
        issues,
        "summary.browserStageEvidenceBundleSafety.ok must be true",
    )

    try:
        simulated_stage_result = load_json(simulated_stage_result_path)
    except ValueError as exc:
        simulated_stage_result = {}
        issues.append(str(exc))
    simulated_stage_result_validation = validate_browser_stage_result(simulated_stage_result, browser_stage_packet)
    issues.extend(f"simulated stage result: {issue}" for issue in simulated_stage_result_validation.get("issues", []))
    require(simulated_stage_result_validation.get("ok") is True, issues, "simulated stage result validation must pass")
    require(
        summary.get("simulatedStageResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedStageResultSafety.ok must be true",
    )

    try:
        ledger_after_first_stage = load_json(ledger_after_first_stage_path)
    except ValueError as exc:
        ledger_after_first_stage = {}
        issues.append(str(exc))
    ledger_after_first_stage_validation = validate_browser_execution_ledger(ledger_after_first_stage)
    issues.extend(f"ledger after first stage: {issue}" for issue in ledger_after_first_stage_validation.get("issues", []))
    require(ledger_after_first_stage_validation.get("ok") is True, issues, "ledger after first stage validation must pass")
    require(
        summary.get("ledgerAfterFirstStageSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterFirstStageSafety.ok must be true",
    )

    try:
        browser_stage_packet_after_first_stage = load_json(browser_stage_packet_after_first_stage_path)
    except ValueError as exc:
        browser_stage_packet_after_first_stage = {}
        issues.append(str(exc))
    browser_stage_packet_after_first_stage_validation = validate_browser_stage_packet(browser_stage_packet_after_first_stage)
    issues.extend(
        f"browser stage packet after first stage: {issue}"
        for issue in browser_stage_packet_after_first_stage_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_first_stage_validation.get("ok") is True,
        issues,
        "browser stage packet after first stage validation must pass",
    )
    validate_packet_command_paths(
        "browser stage packet after first stage",
        browser_stage_packet_after_first_stage,
        ledger_after_first_stage_path,
        browser_stage_packet_after_first_stage_path,
        issues,
    )
    require(
        summary.get("browserStagePacketAfterFirstStageSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterFirstStageSafety.ok must be true",
    )

    try:
        simulated_create_site_result = load_json(simulated_create_site_result_path)
    except ValueError as exc:
        simulated_create_site_result = {}
        issues.append(str(exc))
    simulated_create_site_result_validation = validate_browser_stage_result(
        simulated_create_site_result,
        browser_stage_packet_after_first_stage,
    )
    issues.extend(f"simulated create-site result: {issue}" for issue in simulated_create_site_result_validation.get("issues", []))
    require(
        simulated_create_site_result_validation.get("ok") is True,
        issues,
        "simulated create-site result validation must pass",
    )
    require(
        summary.get("simulatedCreateSiteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedCreateSiteResultSafety.ok must be true",
    )

    try:
        ledger_after_create_site = load_json(ledger_after_create_site_path)
    except ValueError as exc:
        ledger_after_create_site = {}
        issues.append(str(exc))
    ledger_after_create_site_validation = validate_browser_execution_ledger(ledger_after_create_site)
    issues.extend(f"ledger after create site: {issue}" for issue in ledger_after_create_site_validation.get("issues", []))
    require(ledger_after_create_site_validation.get("ok") is True, issues, "ledger after create site validation must pass")
    require(
        summary.get("ledgerAfterCreateSiteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterCreateSiteSafety.ok must be true",
    )

    try:
        browser_stage_packet_after_create_site = load_json(browser_stage_packet_after_create_site_path)
    except ValueError as exc:
        browser_stage_packet_after_create_site = {}
        issues.append(str(exc))
    browser_stage_packet_after_create_site_validation = validate_browser_stage_packet(browser_stage_packet_after_create_site)
    issues.extend(
        f"browser stage packet after create site: {issue}"
        for issue in browser_stage_packet_after_create_site_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_create_site_validation.get("ok") is True,
        issues,
        "browser stage packet after create site validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterCreateSiteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterCreateSiteSafety.ok must be true",
    )

    try:
        simulated_setup_result = load_json(simulated_setup_result_path)
    except ValueError as exc:
        simulated_setup_result = {}
        issues.append(str(exc))
    simulated_setup_result_validation = validate_browser_stage_result(
        simulated_setup_result,
        browser_stage_packet_after_create_site,
    )
    issues.extend(f"simulated setup result: {issue}" for issue in simulated_setup_result_validation.get("issues", []))
    require(simulated_setup_result_validation.get("ok") is True, issues, "simulated setup result validation must pass")
    require(
        summary.get("simulatedSetupResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedSetupResultSafety.ok must be true",
    )

    try:
        ledger_after_setup = load_json(ledger_after_setup_path)
    except ValueError as exc:
        ledger_after_setup = {}
        issues.append(str(exc))
    ledger_after_setup_validation = validate_browser_execution_ledger(ledger_after_setup)
    issues.extend(f"ledger after setup: {issue}" for issue in ledger_after_setup_validation.get("issues", []))
    require(ledger_after_setup_validation.get("ok") is True, issues, "ledger after setup validation must pass")
    require(
        summary.get("ledgerAfterSetupSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterSetupSafety.ok must be true",
    )

    try:
        browser_stage_packet_after_setup = load_json(browser_stage_packet_after_setup_path)
    except ValueError as exc:
        browser_stage_packet_after_setup = {}
        issues.append(str(exc))
    browser_stage_packet_after_setup_validation = validate_browser_stage_packet(browser_stage_packet_after_setup)
    issues.extend(
        f"browser stage packet after setup: {issue}" for issue in browser_stage_packet_after_setup_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_setup_validation.get("ok") is True,
        issues,
        "browser stage packet after setup validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterSetupSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterSetupSafety.ok must be true",
    )
    try:
        next_browser_action_handoff = load_json(next_browser_action_handoff_path)
    except ValueError as exc:
        next_browser_action_handoff = {}
        issues.append(str(exc))
    next_browser_action_handoff_validation = validate_next_browser_action_handoff(next_browser_action_handoff)
    issues.extend(
        f"next browser action handoff: {issue}"
        for issue in next_browser_action_handoff_validation.get("issues", [])
    )
    require(
        next_browser_action_handoff_validation.get("ok") is True,
        issues,
        "next browser action handoff validation must pass",
    )
    require(
        summary.get("nextBrowserActionHandoffSafety", {}).get("ok") is True,
        issues,
        "summary.nextBrowserActionHandoffSafety.ok must be true",
    )
    require(
        next_browser_action_handoff.get("stageId") == "module_interface_capture",
        issues,
        "next browser action handoff must target module_interface_capture",
    )
    require(
        next_browser_action_handoff.get("preparedOnly") is True,
        issues,
        "next browser action handoff must be preparation only",
    )
    require(
        next_browser_action_handoff.get("isUserAuthorization") is False,
        issues,
        "next browser action handoff must not be user authorization",
    )
    require(
        next_browser_action_handoff.get("remoteMutationsPerformed") is False,
        issues,
        "next browser action handoff must record no remote mutations",
    )

    try:
        simulated_module_capture_partial_result = load_json(simulated_module_capture_partial_result_path)
    except ValueError as exc:
        simulated_module_capture_partial_result = {}
        issues.append(str(exc))
    simulated_module_capture_partial_result_validation = validate_browser_stage_result(
        simulated_module_capture_partial_result,
        browser_stage_packet_after_setup,
    )
    issues.extend(
        f"simulated module-capture partial result: {issue}"
        for issue in simulated_module_capture_partial_result_validation.get("issues", [])
    )
    require(
        simulated_module_capture_partial_result_validation.get("ok") is True,
        issues,
        "simulated module-capture partial result validation must pass",
    )
    require(
        summary.get("simulatedModuleCapturePartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedModuleCapturePartialResultSafety.ok must be true",
    )

    try:
        ledger_after_module_capture_partial = load_json(ledger_after_module_capture_partial_path)
    except ValueError as exc:
        ledger_after_module_capture_partial = {}
        issues.append(str(exc))
    ledger_after_module_capture_partial_validation = validate_browser_execution_ledger(ledger_after_module_capture_partial)
    issues.extend(
        f"ledger after module-capture partial: {issue}"
        for issue in ledger_after_module_capture_partial_validation.get("issues", [])
    )
    require(
        ledger_after_module_capture_partial_validation.get("ok") is True,
        issues,
        "ledger after module-capture partial validation must pass",
    )
    require(
        summary.get("ledgerAfterModuleCapturePartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterModuleCapturePartialSafety.ok must be true",
    )

    try:
        module_capture_coverage = load_json(module_capture_coverage_path)
    except ValueError as exc:
        module_capture_coverage = {}
        issues.append(str(exc))
    try:
        module_capture_plan = load_json(full_e2e_dir / "03-module-interface-plan" / "module-capture-plan.json")
    except ValueError as exc:
        module_capture_plan = {}
        issues.append(str(exc))
    module_capture_coverage_validation = validate_coverage(module_capture_coverage, module_capture_plan)
    issues.extend(f"module capture coverage: {issue}" for issue in module_capture_coverage_validation.get("issues", []))
    require(
        module_capture_coverage_validation.get("ok") is True,
        issues,
        "module capture coverage validation must pass",
    )
    require(
        summary.get("moduleCaptureCoverageSafety", {}).get("ok") is True,
        issues,
        "summary.moduleCaptureCoverageSafety.ok must be true",
    )
    try:
        ledger_after_module_capture_coverage_sync = load_json(ledger_after_module_capture_coverage_sync_path)
    except ValueError as exc:
        ledger_after_module_capture_coverage_sync = {}
        issues.append(str(exc))
    ledger_after_module_capture_coverage_sync_validation = validate_browser_execution_ledger(
        ledger_after_module_capture_coverage_sync
    )
    issues.extend(
        f"ledger after module-capture coverage sync: {issue}"
        for issue in ledger_after_module_capture_coverage_sync_validation.get("issues", [])
    )
    require(
        ledger_after_module_capture_coverage_sync_validation.get("ok") is True,
        issues,
        "ledger after module-capture coverage sync validation must pass",
    )
    require(
        summary.get("ledgerAfterModuleCaptureCoverageSyncSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterModuleCaptureCoverageSyncSafety.ok must be true",
    )
    try:
        module_capture_coverage_complete = load_json(module_capture_coverage_complete_path)
    except ValueError as exc:
        module_capture_coverage_complete = {}
        issues.append(str(exc))
    module_capture_coverage_complete_validation = validate_coverage(module_capture_coverage_complete, module_capture_plan)
    issues.extend(
        f"complete module capture coverage: {issue}"
        for issue in module_capture_coverage_complete_validation.get("issues", [])
    )
    require(
        module_capture_coverage_complete_validation.get("ok") is True,
        issues,
        "complete module capture coverage validation must pass",
    )
    require(
        summary.get("moduleCaptureCoverageCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.moduleCaptureCoverageCompleteSafety.ok must be true",
    )
    try:
        ledger_after_module_capture_complete = load_json(ledger_after_module_capture_complete_path)
    except ValueError as exc:
        ledger_after_module_capture_complete = {}
        issues.append(str(exc))
    ledger_after_module_capture_complete_validation = validate_browser_execution_ledger(ledger_after_module_capture_complete)
    issues.extend(
        f"ledger after complete module-capture: {issue}"
        for issue in ledger_after_module_capture_complete_validation.get("issues", [])
    )
    require(
        ledger_after_module_capture_complete_validation.get("ok") is True,
        issues,
        "ledger after complete module-capture validation must pass",
    )
    require(
        summary.get("ledgerAfterModuleCaptureCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterModuleCaptureCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_module_capture_complete = load_json(browser_stage_packet_after_module_capture_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_module_capture_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_module_capture_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_module_capture_complete
    )
    issues.extend(
        f"browser stage packet after complete module-capture: {issue}"
        for issue in browser_stage_packet_after_module_capture_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_module_capture_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after complete module-capture validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterModuleCaptureCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterModuleCaptureCompleteSafety.ok must be true",
    )
    try:
        simulated_theme_launch_partial_result = load_json(simulated_theme_launch_partial_result_path)
    except ValueError as exc:
        simulated_theme_launch_partial_result = {}
        issues.append(str(exc))
    simulated_theme_launch_partial_result_validation = validate_browser_stage_result(
        simulated_theme_launch_partial_result,
        browser_stage_packet_after_module_capture_complete,
    )
    issues.extend(
        f"simulated theme-launch partial result: {issue}"
        for issue in simulated_theme_launch_partial_result_validation.get("issues", [])
    )
    require(
        simulated_theme_launch_partial_result_validation.get("ok") is True,
        issues,
        "simulated theme-launch partial result validation must pass",
    )
    require(
        summary.get("simulatedThemeLaunchPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedThemeLaunchPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_theme_launch_partial = load_json(ledger_after_theme_launch_partial_path)
    except ValueError as exc:
        ledger_after_theme_launch_partial = {}
        issues.append(str(exc))
    ledger_after_theme_launch_partial_validation = validate_browser_execution_ledger(ledger_after_theme_launch_partial)
    issues.extend(
        f"ledger after theme-launch partial: {issue}"
        for issue in ledger_after_theme_launch_partial_validation.get("issues", [])
    )
    require(
        ledger_after_theme_launch_partial_validation.get("ok") is True,
        issues,
        "ledger after theme-launch partial validation must pass",
    )
    require(
        summary.get("ledgerAfterThemeLaunchPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterThemeLaunchPartialSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_theme_launch_partial_recovery = load_json(
            browser_stage_packet_after_theme_launch_partial_recovery_path
        )
    except ValueError as exc:
        browser_stage_packet_after_theme_launch_partial_recovery = {}
        issues.append(str(exc))
    browser_stage_packet_after_theme_launch_partial_recovery_validation = validate_browser_stage_packet(
        browser_stage_packet_after_theme_launch_partial_recovery
    )
    issues.extend(
        f"browser stage packet after theme-launch partial recovery: {issue}"
        for issue in browser_stage_packet_after_theme_launch_partial_recovery_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_theme_launch_partial_recovery_validation.get("ok") is True,
        issues,
        "browser stage packet after theme-launch partial recovery validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterThemeLaunchPartialRecoverySafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterThemeLaunchPartialRecoverySafety.ok must be true",
    )
    try:
        simulated_theme_launch_complete_result = load_json(simulated_theme_launch_complete_result_path)
    except ValueError as exc:
        simulated_theme_launch_complete_result = {}
        issues.append(str(exc))
    simulated_theme_launch_complete_result_validation = validate_browser_stage_result(
        simulated_theme_launch_complete_result,
        browser_stage_packet_after_theme_launch_partial_recovery,
    )
    issues.extend(
        f"simulated theme-launch complete result: {issue}"
        for issue in simulated_theme_launch_complete_result_validation.get("issues", [])
    )
    require(
        simulated_theme_launch_complete_result_validation.get("ok") is True,
        issues,
        "simulated theme-launch complete result validation must pass",
    )
    require(
        summary.get("simulatedThemeLaunchCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedThemeLaunchCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_theme_launch_recovery_complete = load_json(ledger_after_theme_launch_recovery_complete_path)
    except ValueError as exc:
        ledger_after_theme_launch_recovery_complete = {}
        issues.append(str(exc))
    ledger_after_theme_launch_recovery_complete_validation = validate_browser_execution_ledger(
        ledger_after_theme_launch_recovery_complete
    )
    issues.extend(
        f"ledger after theme-launch recovery complete: {issue}"
        for issue in ledger_after_theme_launch_recovery_complete_validation.get("issues", [])
    )
    require(
        ledger_after_theme_launch_recovery_complete_validation.get("ok") is True,
        issues,
        "ledger after theme-launch recovery complete validation must pass",
    )
    require(
        summary.get("ledgerAfterThemeLaunchRecoveryCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterThemeLaunchRecoveryCompleteSafety.ok must be true",
    )
    try:
        ledger_after_theme_launch_complete = load_json(ledger_after_theme_launch_complete_path)
    except ValueError as exc:
        ledger_after_theme_launch_complete = {}
        issues.append(str(exc))
    ledger_after_theme_launch_complete_validation = validate_browser_execution_ledger(ledger_after_theme_launch_complete)
    issues.extend(
        f"ledger after theme-launch complete: {issue}"
        for issue in ledger_after_theme_launch_complete_validation.get("issues", [])
    )
    require(
        ledger_after_theme_launch_complete_validation.get("ok") is True,
        issues,
        "ledger after theme-launch complete validation must pass",
    )
    require(
        summary.get("ledgerAfterThemeLaunchCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterThemeLaunchCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_theme_launch_complete = load_json(browser_stage_packet_after_theme_launch_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_theme_launch_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_theme_launch_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_theme_launch_complete
    )
    issues.extend(
        f"browser stage packet after theme launch: {issue}"
        for issue in browser_stage_packet_after_theme_launch_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_theme_launch_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after theme launch validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterThemeLaunchCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterThemeLaunchCompleteSafety.ok must be true",
    )
    try:
        simulated_static_audit_partial_result = load_json(simulated_static_audit_partial_result_path)
    except ValueError as exc:
        simulated_static_audit_partial_result = {}
        issues.append(str(exc))
    simulated_static_audit_partial_result_validation = validate_browser_stage_result(
        simulated_static_audit_partial_result,
        browser_stage_packet_after_theme_launch_complete,
    )
    issues.extend(
        f"simulated static-audit partial result: {issue}"
        for issue in simulated_static_audit_partial_result_validation.get("issues", [])
    )
    require(
        simulated_static_audit_partial_result_validation.get("ok") is True,
        issues,
        "simulated static-audit partial result validation must pass",
    )
    require(
        summary.get("simulatedStaticAuditPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedStaticAuditPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_static_audit_partial = load_json(ledger_after_static_audit_partial_path)
    except ValueError as exc:
        ledger_after_static_audit_partial = {}
        issues.append(str(exc))
    ledger_after_static_audit_partial_validation = validate_browser_execution_ledger(ledger_after_static_audit_partial)
    issues.extend(
        f"ledger after static-audit partial: {issue}"
        for issue in ledger_after_static_audit_partial_validation.get("issues", [])
    )
    require(
        ledger_after_static_audit_partial_validation.get("ok") is True,
        issues,
        "ledger after static-audit partial validation must pass",
    )
    require(
        summary.get("ledgerAfterStaticAuditPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterStaticAuditPartialSafety.ok must be true",
    )
    try:
        simulated_static_audit_complete_result = load_json(simulated_static_audit_complete_result_path)
    except ValueError as exc:
        simulated_static_audit_complete_result = {}
        issues.append(str(exc))
    simulated_static_audit_complete_result_validation = validate_browser_stage_result(
        simulated_static_audit_complete_result,
        browser_stage_packet_after_theme_launch_complete,
    )
    issues.extend(
        f"simulated static-audit complete result: {issue}"
        for issue in simulated_static_audit_complete_result_validation.get("issues", [])
    )
    require(
        simulated_static_audit_complete_result_validation.get("ok") is True,
        issues,
        "simulated static-audit complete result validation must pass",
    )
    require(
        summary.get("simulatedStaticAuditCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedStaticAuditCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_static_audit_complete = load_json(ledger_after_static_audit_complete_path)
    except ValueError as exc:
        ledger_after_static_audit_complete = {}
        issues.append(str(exc))
    ledger_after_static_audit_complete_validation = validate_browser_execution_ledger(ledger_after_static_audit_complete)
    issues.extend(
        f"ledger after static-audit complete: {issue}"
        for issue in ledger_after_static_audit_complete_validation.get("issues", [])
    )
    require(
        ledger_after_static_audit_complete_validation.get("ok") is True,
        issues,
        "ledger after static-audit complete validation must pass",
    )
    require(
        summary.get("ledgerAfterStaticAuditCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterStaticAuditCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_static_audit_complete = load_json(browser_stage_packet_after_static_audit_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_static_audit_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_static_audit_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_static_audit_complete
    )
    issues.extend(
        f"browser stage packet after static audit: {issue}"
        for issue in browser_stage_packet_after_static_audit_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_static_audit_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after static audit validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterStaticAuditCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterStaticAuditCompleteSafety.ok must be true",
    )
    try:
        simulated_content_probe_partial_result = load_json(simulated_content_probe_partial_result_path)
    except ValueError as exc:
        simulated_content_probe_partial_result = {}
        issues.append(str(exc))
    simulated_content_probe_partial_result_validation = validate_browser_stage_result(
        simulated_content_probe_partial_result,
        browser_stage_packet_after_static_audit_complete,
    )
    issues.extend(
        f"simulated content-probe partial result: {issue}"
        for issue in simulated_content_probe_partial_result_validation.get("issues", [])
    )
    require(
        simulated_content_probe_partial_result_validation.get("ok") is True,
        issues,
        "simulated content-probe partial result validation must pass",
    )
    require(
        summary.get("simulatedContentProbePartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedContentProbePartialResultSafety.ok must be true",
    )
    try:
        ledger_after_content_probe_partial = load_json(ledger_after_content_probe_partial_path)
    except ValueError as exc:
        ledger_after_content_probe_partial = {}
        issues.append(str(exc))
    ledger_after_content_probe_partial_validation = validate_browser_execution_ledger(ledger_after_content_probe_partial)
    issues.extend(
        f"ledger after content-probe partial: {issue}"
        for issue in ledger_after_content_probe_partial_validation.get("issues", [])
    )
    require(
        ledger_after_content_probe_partial_validation.get("ok") is True,
        issues,
        "ledger after content-probe partial validation must pass",
    )
    require(
        summary.get("ledgerAfterContentProbePartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterContentProbePartialSafety.ok must be true",
    )
    try:
        simulated_content_probe_complete_result = load_json(simulated_content_probe_complete_result_path)
    except ValueError as exc:
        simulated_content_probe_complete_result = {}
        issues.append(str(exc))
    simulated_content_probe_complete_result_validation = validate_browser_stage_result(
        simulated_content_probe_complete_result,
        browser_stage_packet_after_static_audit_complete,
    )
    issues.extend(
        f"simulated content-probe complete result: {issue}"
        for issue in simulated_content_probe_complete_result_validation.get("issues", [])
    )
    require(
        simulated_content_probe_complete_result_validation.get("ok") is True,
        issues,
        "simulated content-probe complete result validation must pass",
    )
    require(
        summary.get("simulatedContentProbeCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedContentProbeCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_content_probe_complete = load_json(ledger_after_content_probe_complete_path)
    except ValueError as exc:
        ledger_after_content_probe_complete = {}
        issues.append(str(exc))
    ledger_after_content_probe_complete_validation = validate_browser_execution_ledger(ledger_after_content_probe_complete)
    issues.extend(
        f"ledger after content-probe complete: {issue}"
        for issue in ledger_after_content_probe_complete_validation.get("issues", [])
    )
    require(
        ledger_after_content_probe_complete_validation.get("ok") is True,
        issues,
        "ledger after content-probe complete validation must pass",
    )
    require(
        summary.get("ledgerAfterContentProbeCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterContentProbeCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_content_probe_complete = load_json(browser_stage_packet_after_content_probe_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_content_probe_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_content_probe_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_content_probe_complete
    )
    issues.extend(
        f"browser stage packet after content probe: {issue}"
        for issue in browser_stage_packet_after_content_probe_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_content_probe_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after content probe validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterContentProbeCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterContentProbeCompleteSafety.ok must be true",
    )
    try:
        simulated_save_request_partial_result = load_json(simulated_save_request_partial_result_path)
    except ValueError as exc:
        simulated_save_request_partial_result = {}
        issues.append(str(exc))
    simulated_save_request_partial_result_validation = validate_browser_stage_result(
        simulated_save_request_partial_result,
        browser_stage_packet_after_content_probe_complete,
    )
    issues.extend(
        f"simulated save-request partial result: {issue}"
        for issue in simulated_save_request_partial_result_validation.get("issues", [])
    )
    require(
        simulated_save_request_partial_result_validation.get("ok") is True,
        issues,
        "simulated save-request partial result validation must pass",
    )
    require(
        summary.get("simulatedSaveRequestPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedSaveRequestPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_save_request_partial = load_json(ledger_after_save_request_partial_path)
    except ValueError as exc:
        ledger_after_save_request_partial = {}
        issues.append(str(exc))
    ledger_after_save_request_partial_validation = validate_browser_execution_ledger(ledger_after_save_request_partial)
    issues.extend(
        f"ledger after save-request partial: {issue}"
        for issue in ledger_after_save_request_partial_validation.get("issues", [])
    )
    require(
        ledger_after_save_request_partial_validation.get("ok") is True,
        issues,
        "ledger after save-request partial validation must pass",
    )
    require(
        summary.get("ledgerAfterSaveRequestPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterSaveRequestPartialSafety.ok must be true",
    )
    try:
        simulated_save_request_complete_result = load_json(simulated_save_request_complete_result_path)
    except ValueError as exc:
        simulated_save_request_complete_result = {}
        issues.append(str(exc))
    simulated_save_request_complete_result_validation = validate_browser_stage_result(
        simulated_save_request_complete_result,
        browser_stage_packet_after_content_probe_complete,
    )
    issues.extend(
        f"simulated save-request complete result: {issue}"
        for issue in simulated_save_request_complete_result_validation.get("issues", [])
    )
    require(
        simulated_save_request_complete_result_validation.get("ok") is True,
        issues,
        "simulated save-request complete result validation must pass",
    )
    require(
        summary.get("simulatedSaveRequestCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedSaveRequestCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_save_request_complete = load_json(ledger_after_save_request_complete_path)
    except ValueError as exc:
        ledger_after_save_request_complete = {}
        issues.append(str(exc))
    ledger_after_save_request_complete_validation = validate_browser_execution_ledger(ledger_after_save_request_complete)
    issues.extend(
        f"ledger after save-request complete: {issue}"
        for issue in ledger_after_save_request_complete_validation.get("issues", [])
    )
    require(
        ledger_after_save_request_complete_validation.get("ok") is True,
        issues,
        "ledger after save-request complete validation must pass",
    )
    require(
        summary.get("ledgerAfterSaveRequestCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterSaveRequestCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_save_request_complete = load_json(browser_stage_packet_after_save_request_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_save_request_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_save_request_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_save_request_complete
    )
    issues.extend(
        f"browser stage packet after save request: {issue}"
        for issue in browser_stage_packet_after_save_request_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_save_request_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after save request validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterSaveRequestCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterSaveRequestCompleteSafety.ok must be true",
    )
    try:
        simulated_publish_sample_partial_result = load_json(simulated_publish_sample_partial_result_path)
    except ValueError as exc:
        simulated_publish_sample_partial_result = {}
        issues.append(str(exc))
    simulated_publish_sample_partial_result_validation = validate_browser_stage_result(
        simulated_publish_sample_partial_result,
        browser_stage_packet_after_save_request_complete,
    )
    issues.extend(
        f"simulated publish-sample partial result: {issue}"
        for issue in simulated_publish_sample_partial_result_validation.get("issues", [])
    )
    require(
        simulated_publish_sample_partial_result_validation.get("ok") is True,
        issues,
        "simulated publish-sample partial result validation must pass",
    )
    require(
        summary.get("simulatedPublishSamplePartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedPublishSamplePartialResultSafety.ok must be true",
    )
    try:
        ledger_after_publish_sample_partial = load_json(ledger_after_publish_sample_partial_path)
    except ValueError as exc:
        ledger_after_publish_sample_partial = {}
        issues.append(str(exc))
    ledger_after_publish_sample_partial_validation = validate_browser_execution_ledger(ledger_after_publish_sample_partial)
    issues.extend(
        f"ledger after publish-sample partial: {issue}"
        for issue in ledger_after_publish_sample_partial_validation.get("issues", [])
    )
    require(
        ledger_after_publish_sample_partial_validation.get("ok") is True,
        issues,
        "ledger after publish-sample partial validation must pass",
    )
    require(
        summary.get("ledgerAfterPublishSamplePartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterPublishSamplePartialSafety.ok must be true",
    )
    try:
        simulated_publish_sample_complete_result = load_json(simulated_publish_sample_complete_result_path)
    except ValueError as exc:
        simulated_publish_sample_complete_result = {}
        issues.append(str(exc))
    simulated_publish_sample_complete_result_validation = validate_browser_stage_result(
        simulated_publish_sample_complete_result,
        browser_stage_packet_after_save_request_complete,
    )
    issues.extend(
        f"simulated publish-sample complete result: {issue}"
        for issue in simulated_publish_sample_complete_result_validation.get("issues", [])
    )
    require(
        simulated_publish_sample_complete_result_validation.get("ok") is True,
        issues,
        "simulated publish-sample complete result validation must pass",
    )
    require(
        summary.get("simulatedPublishSampleCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedPublishSampleCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_publish_sample_complete = load_json(ledger_after_publish_sample_complete_path)
    except ValueError as exc:
        ledger_after_publish_sample_complete = {}
        issues.append(str(exc))
    ledger_after_publish_sample_complete_validation = validate_browser_execution_ledger(ledger_after_publish_sample_complete)
    issues.extend(
        f"ledger after publish-sample complete: {issue}"
        for issue in ledger_after_publish_sample_complete_validation.get("issues", [])
    )
    require(
        ledger_after_publish_sample_complete_validation.get("ok") is True,
        issues,
        "ledger after publish-sample complete validation must pass",
    )
    require(
        summary.get("ledgerAfterPublishSampleCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterPublishSampleCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_publish_sample_complete = load_json(browser_stage_packet_after_publish_sample_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_publish_sample_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_publish_sample_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_publish_sample_complete
    )
    issues.extend(
        f"browser stage packet after publish sample: {issue}"
        for issue in browser_stage_packet_after_publish_sample_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_publish_sample_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after publish sample validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterPublishSampleCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterPublishSampleCompleteSafety.ok must be true",
    )
    try:
        simulated_manifest_gate_partial_result = load_json(simulated_manifest_gate_partial_result_path)
    except ValueError as exc:
        simulated_manifest_gate_partial_result = {}
        issues.append(str(exc))
    simulated_manifest_gate_partial_result_validation = validate_browser_stage_result(
        simulated_manifest_gate_partial_result,
        browser_stage_packet_after_publish_sample_complete,
    )
    issues.extend(
        f"simulated manifest-gate partial result: {issue}"
        for issue in simulated_manifest_gate_partial_result_validation.get("issues", [])
    )
    require(
        simulated_manifest_gate_partial_result_validation.get("ok") is True,
        issues,
        "simulated manifest-gate partial result validation must pass",
    )
    require(
        summary.get("simulatedManifestGatePartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedManifestGatePartialResultSafety.ok must be true",
    )
    try:
        ledger_after_manifest_gate_partial = load_json(ledger_after_manifest_gate_partial_path)
    except ValueError as exc:
        ledger_after_manifest_gate_partial = {}
        issues.append(str(exc))
    ledger_after_manifest_gate_partial_validation = validate_browser_execution_ledger(ledger_after_manifest_gate_partial)
    issues.extend(
        f"ledger after manifest-gate partial: {issue}"
        for issue in ledger_after_manifest_gate_partial_validation.get("issues", [])
    )
    require(
        ledger_after_manifest_gate_partial_validation.get("ok") is True,
        issues,
        "ledger after manifest-gate partial validation must pass",
    )
    require(
        summary.get("ledgerAfterManifestGatePartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterManifestGatePartialSafety.ok must be true",
    )
    try:
        simulated_manifest_gate_complete_result = load_json(simulated_manifest_gate_complete_result_path)
    except ValueError as exc:
        simulated_manifest_gate_complete_result = {}
        issues.append(str(exc))
    simulated_manifest_gate_complete_result_validation = validate_browser_stage_result(
        simulated_manifest_gate_complete_result,
        browser_stage_packet_after_publish_sample_complete,
    )
    issues.extend(
        f"simulated manifest-gate complete result: {issue}"
        for issue in simulated_manifest_gate_complete_result_validation.get("issues", [])
    )
    require(
        simulated_manifest_gate_complete_result_validation.get("ok") is True,
        issues,
        "simulated manifest-gate complete result validation must pass",
    )
    require(
        summary.get("simulatedManifestGateCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedManifestGateCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_manifest_gate_complete = load_json(ledger_after_manifest_gate_complete_path)
    except ValueError as exc:
        ledger_after_manifest_gate_complete = {}
        issues.append(str(exc))
    ledger_after_manifest_gate_complete_validation = validate_browser_execution_ledger(ledger_after_manifest_gate_complete)
    issues.extend(
        f"ledger after manifest-gate complete: {issue}"
        for issue in ledger_after_manifest_gate_complete_validation.get("issues", [])
    )
    require(
        ledger_after_manifest_gate_complete_validation.get("ok") is True,
        issues,
        "ledger after manifest-gate complete validation must pass",
    )
    require(
        summary.get("ledgerAfterManifestGateCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterManifestGateCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_manifest_gate_complete = load_json(browser_stage_packet_after_manifest_gate_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_manifest_gate_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_manifest_gate_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_manifest_gate_complete
    )
    issues.extend(
        f"browser stage packet after manifest gate: {issue}"
        for issue in browser_stage_packet_after_manifest_gate_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_manifest_gate_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after manifest gate validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterManifestGateCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterManifestGateCompleteSafety.ok must be true",
    )
    try:
        simulated_batch_upload_partial_result = load_json(simulated_batch_upload_partial_result_path)
    except ValueError as exc:
        simulated_batch_upload_partial_result = {}
        issues.append(str(exc))
    simulated_batch_upload_partial_result_validation = validate_browser_stage_result(
        simulated_batch_upload_partial_result,
        browser_stage_packet_after_manifest_gate_complete,
    )
    issues.extend(
        f"simulated batch-upload partial result: {issue}"
        for issue in simulated_batch_upload_partial_result_validation.get("issues", [])
    )
    require(
        simulated_batch_upload_partial_result_validation.get("ok") is True,
        issues,
        "simulated batch-upload partial result validation must pass",
    )
    require(
        summary.get("simulatedBatchUploadPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedBatchUploadPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_batch_upload_partial = load_json(ledger_after_batch_upload_partial_path)
    except ValueError as exc:
        ledger_after_batch_upload_partial = {}
        issues.append(str(exc))
    ledger_after_batch_upload_partial_validation = validate_browser_execution_ledger(ledger_after_batch_upload_partial)
    issues.extend(
        f"ledger after batch-upload partial: {issue}"
        for issue in ledger_after_batch_upload_partial_validation.get("issues", [])
    )
    require(
        ledger_after_batch_upload_partial_validation.get("ok") is True,
        issues,
        "ledger after batch-upload partial validation must pass",
    )
    require(
        summary.get("ledgerAfterBatchUploadPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterBatchUploadPartialSafety.ok must be true",
    )
    try:
        simulated_batch_upload_complete_result = load_json(simulated_batch_upload_complete_result_path)
    except ValueError as exc:
        simulated_batch_upload_complete_result = {}
        issues.append(str(exc))
    simulated_batch_upload_complete_result_validation = validate_browser_stage_result(
        simulated_batch_upload_complete_result,
        browser_stage_packet_after_manifest_gate_complete,
    )
    issues.extend(
        f"simulated batch-upload complete result: {issue}"
        for issue in simulated_batch_upload_complete_result_validation.get("issues", [])
    )
    require(
        simulated_batch_upload_complete_result_validation.get("ok") is True,
        issues,
        "simulated batch-upload complete result validation must pass",
    )
    require(
        summary.get("simulatedBatchUploadCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedBatchUploadCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_batch_upload_complete = load_json(ledger_after_batch_upload_complete_path)
    except ValueError as exc:
        ledger_after_batch_upload_complete = {}
        issues.append(str(exc))
    ledger_after_batch_upload_complete_validation = validate_browser_execution_ledger(ledger_after_batch_upload_complete)
    issues.extend(
        f"ledger after batch-upload complete: {issue}"
        for issue in ledger_after_batch_upload_complete_validation.get("issues", [])
    )
    require(
        ledger_after_batch_upload_complete_validation.get("ok") is True,
        issues,
        "ledger after batch-upload complete validation must pass",
    )
    require(
        summary.get("ledgerAfterBatchUploadCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterBatchUploadCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_batch_upload_complete = load_json(browser_stage_packet_after_batch_upload_complete_path)
    except ValueError as exc:
        browser_stage_packet_after_batch_upload_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_batch_upload_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_batch_upload_complete
    )
    issues.extend(
        f"browser stage packet after batch upload: {issue}"
        for issue in browser_stage_packet_after_batch_upload_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_batch_upload_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after batch upload validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterBatchUploadCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterBatchUploadCompleteSafety.ok must be true",
    )
    try:
        simulated_forms_media_settings_partial_result = load_json(simulated_forms_media_settings_partial_result_path)
    except ValueError as exc:
        simulated_forms_media_settings_partial_result = {}
        issues.append(str(exc))
    simulated_forms_media_settings_partial_result_validation = validate_browser_stage_result(
        simulated_forms_media_settings_partial_result,
        browser_stage_packet_after_batch_upload_complete,
    )
    issues.extend(
        f"simulated forms-media-settings partial result: {issue}"
        for issue in simulated_forms_media_settings_partial_result_validation.get("issues", [])
    )
    require(
        simulated_forms_media_settings_partial_result_validation.get("ok") is True,
        issues,
        "simulated forms-media-settings partial result validation must pass",
    )
    require(
        summary.get("simulatedFormsMediaSettingsPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedFormsMediaSettingsPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_forms_media_settings_partial = load_json(ledger_after_forms_media_settings_partial_path)
    except ValueError as exc:
        ledger_after_forms_media_settings_partial = {}
        issues.append(str(exc))
    ledger_after_forms_media_settings_partial_validation = validate_browser_execution_ledger(
        ledger_after_forms_media_settings_partial
    )
    issues.extend(
        f"ledger after forms-media-settings partial: {issue}"
        for issue in ledger_after_forms_media_settings_partial_validation.get("issues", [])
    )
    require(
        ledger_after_forms_media_settings_partial_validation.get("ok") is True,
        issues,
        "ledger after forms-media-settings partial validation must pass",
    )
    require(
        summary.get("ledgerAfterFormsMediaSettingsPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterFormsMediaSettingsPartialSafety.ok must be true",
    )
    try:
        simulated_forms_media_settings_complete_result = load_json(simulated_forms_media_settings_complete_result_path)
    except ValueError as exc:
        simulated_forms_media_settings_complete_result = {}
        issues.append(str(exc))
    simulated_forms_media_settings_complete_result_validation = validate_browser_stage_result(
        simulated_forms_media_settings_complete_result,
        browser_stage_packet_after_batch_upload_complete,
    )
    issues.extend(
        f"simulated forms-media-settings complete result: {issue}"
        for issue in simulated_forms_media_settings_complete_result_validation.get("issues", [])
    )
    require(
        simulated_forms_media_settings_complete_result_validation.get("ok") is True,
        issues,
        "simulated forms-media-settings complete result validation must pass",
    )
    require(
        summary.get("simulatedFormsMediaSettingsCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedFormsMediaSettingsCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_forms_media_settings_complete = load_json(ledger_after_forms_media_settings_complete_path)
    except ValueError as exc:
        ledger_after_forms_media_settings_complete = {}
        issues.append(str(exc))
    ledger_after_forms_media_settings_complete_validation = validate_browser_execution_ledger(
        ledger_after_forms_media_settings_complete
    )
    issues.extend(
        f"ledger after forms-media-settings complete: {issue}"
        for issue in ledger_after_forms_media_settings_complete_validation.get("issues", [])
    )
    require(
        ledger_after_forms_media_settings_complete_validation.get("ok") is True,
        issues,
        "ledger after forms-media-settings complete validation must pass",
    )
    require(
        summary.get("ledgerAfterFormsMediaSettingsCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterFormsMediaSettingsCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_forms_media_settings_complete = load_json(
            browser_stage_packet_after_forms_media_settings_complete_path
        )
    except ValueError as exc:
        browser_stage_packet_after_forms_media_settings_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_forms_media_settings_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_forms_media_settings_complete
    )
    issues.extend(
        f"browser stage packet after forms/media/settings: {issue}"
        for issue in browser_stage_packet_after_forms_media_settings_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_forms_media_settings_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after forms/media/settings validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterFormsMediaSettingsCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterFormsMediaSettingsCompleteSafety.ok must be true",
    )
    try:
        simulated_final_frontend_audit_partial_result = load_json(simulated_final_frontend_audit_partial_result_path)
    except ValueError as exc:
        simulated_final_frontend_audit_partial_result = {}
        issues.append(str(exc))
    simulated_final_frontend_audit_partial_result_validation = validate_browser_stage_result(
        simulated_final_frontend_audit_partial_result,
        browser_stage_packet_after_forms_media_settings_complete,
    )
    issues.extend(
        f"simulated final-frontend-audit partial result: {issue}"
        for issue in simulated_final_frontend_audit_partial_result_validation.get("issues", [])
    )
    require(
        simulated_final_frontend_audit_partial_result_validation.get("ok") is True,
        issues,
        "simulated final-frontend-audit partial result validation must pass",
    )
    require(
        summary.get("simulatedFinalFrontendAuditPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedFinalFrontendAuditPartialResultSafety.ok must be true",
    )
    try:
        simulated_final_frontend_audit_partial_report = load_json_array(simulated_final_frontend_audit_partial_report_path)
    except ValueError as exc:
        simulated_final_frontend_audit_partial_report = []
        issues.append(str(exc))
    require(
        isinstance(simulated_final_frontend_audit_partial_report, list)
        and len(simulated_final_frontend_audit_partial_report) == 1,
        issues,
        "simulated final frontend audit partial report must omit one expected route",
    )
    partial_final_audit_blockers = simulated_final_frontend_audit_partial_result.get("blockingIssues", [])
    require(
        isinstance(partial_final_audit_blockers, list)
        and any("audit report route count" in str(issue) for issue in partial_final_audit_blockers)
        and any("missing expected route pattern" in str(issue) for issue in partial_final_audit_blockers),
        issues,
        "simulated final frontend audit partial result must be produced by expected-route coverage blockers",
    )
    try:
        ledger_after_final_frontend_audit_partial = load_json(ledger_after_final_frontend_audit_partial_path)
    except ValueError as exc:
        ledger_after_final_frontend_audit_partial = {}
        issues.append(str(exc))
    ledger_after_final_frontend_audit_partial_validation = validate_browser_execution_ledger(
        ledger_after_final_frontend_audit_partial
    )
    issues.extend(
        f"ledger after final-frontend-audit partial: {issue}"
        for issue in ledger_after_final_frontend_audit_partial_validation.get("issues", [])
    )
    require(
        ledger_after_final_frontend_audit_partial_validation.get("ok") is True,
        issues,
        "ledger after final-frontend-audit partial validation must pass",
    )
    require(
        summary.get("ledgerAfterFinalFrontendAuditPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterFinalFrontendAuditPartialSafety.ok must be true",
    )
    try:
        simulated_final_frontend_audit_complete_result = load_json(simulated_final_frontend_audit_complete_result_path)
    except ValueError as exc:
        simulated_final_frontend_audit_complete_result = {}
        issues.append(str(exc))
    simulated_final_frontend_audit_complete_result_validation = validate_browser_stage_result(
        simulated_final_frontend_audit_complete_result,
        browser_stage_packet_after_forms_media_settings_complete,
    )
    issues.extend(
        f"simulated final-frontend-audit complete result: {issue}"
        for issue in simulated_final_frontend_audit_complete_result_validation.get("issues", [])
    )
    require(
        simulated_final_frontend_audit_complete_result_validation.get("ok") is True,
        issues,
        "simulated final-frontend-audit complete result validation must pass",
    )
    require(
        summary.get("simulatedFinalFrontendAuditCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedFinalFrontendAuditCompleteResultSafety.ok must be true",
    )
    try:
        simulated_final_frontend_audit_complete_report = load_json_array(simulated_final_frontend_audit_complete_report_path)
    except ValueError as exc:
        simulated_final_frontend_audit_complete_report = []
        issues.append(str(exc))
    try:
        simulated_final_frontend_audit_inputs_summary = load_json(simulated_final_frontend_audit_inputs_summary_path)
    except ValueError as exc:
        simulated_final_frontend_audit_inputs_summary = {}
        issues.append(str(exc))
    try:
        simulated_final_frontend_audit_expected_statuses = load_json(simulated_final_frontend_audit_expected_statuses_path)
    except ValueError as exc:
        simulated_final_frontend_audit_expected_statuses = {}
        issues.append(str(exc))
    require(
        isinstance(simulated_final_frontend_audit_inputs_summary, dict)
        and simulated_final_frontend_audit_inputs_summary.get("staticRouteCount") == 1
        and simulated_final_frontend_audit_inputs_summary.get("detailRouteCount") == 1,
        issues,
        "simulated final frontend audit inputs summary must define static and detail route counts",
    )
    require(
        isinstance(simulated_final_frontend_audit_inputs_summary, dict)
        and simulated_final_frontend_audit_inputs_summary.get("detailRouteInstances")
        == [f"{simulated_final_frontend_audit_inputs_summary.get('contentType')}-detail-1"],
        issues,
        "simulated final frontend audit inputs summary must define redacted detail route instances",
    )
    require(
        isinstance(simulated_final_frontend_audit_expected_statuses, dict)
        and len(simulated_final_frontend_audit_expected_statuses) == 2,
        issues,
        "simulated final frontend audit expected statuses must include both static and detail routes",
    )
    require(
        isinstance(simulated_final_frontend_audit_complete_report, list)
        and len(simulated_final_frontend_audit_complete_report) == len(simulated_final_frontend_audit_expected_statuses),
        issues,
        "simulated final frontend audit complete report must cover expected statuses count",
    )
    require(
        isinstance(simulated_final_frontend_audit_complete_report, list)
        and any(
            report.get("routeInstance") == f"{simulated_final_frontend_audit_inputs_summary.get('contentType')}-detail-1"
            for report in simulated_final_frontend_audit_complete_report
            if isinstance(report, dict)
        ),
        issues,
        "simulated final frontend audit complete report must preserve redacted detail route instance",
    )
    complete_final_audit_pointers = simulated_final_frontend_audit_complete_result.get("redactedEvidencePointers", [])
    require(
        isinstance(complete_final_audit_pointers, list)
        and any("simulated-final-audit-inputs-summary" in str(pointer) for pointer in complete_final_audit_pointers)
        and any("simulated-final-expected-statuses" in str(pointer) for pointer in complete_final_audit_pointers),
        issues,
        "simulated final frontend audit complete result must point to inputs summary and expected statuses",
    )
    try:
        ledger_after_final_frontend_audit_complete = load_json(ledger_after_final_frontend_audit_complete_path)
    except ValueError as exc:
        ledger_after_final_frontend_audit_complete = {}
        issues.append(str(exc))
    ledger_after_final_frontend_audit_complete_validation = validate_browser_execution_ledger(
        ledger_after_final_frontend_audit_complete
    )
    issues.extend(
        f"ledger after final-frontend-audit complete: {issue}"
        for issue in ledger_after_final_frontend_audit_complete_validation.get("issues", [])
    )
    require(
        ledger_after_final_frontend_audit_complete_validation.get("ok") is True,
        issues,
        "ledger after final-frontend-audit complete validation must pass",
    )
    require(
        summary.get("ledgerAfterFinalFrontendAuditCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterFinalFrontendAuditCompleteSafety.ok must be true",
    )
    try:
        browser_stage_packet_after_final_frontend_audit_complete = load_json(
            browser_stage_packet_after_final_frontend_audit_complete_path
        )
    except ValueError as exc:
        browser_stage_packet_after_final_frontend_audit_complete = {}
        issues.append(str(exc))
    browser_stage_packet_after_final_frontend_audit_complete_validation = validate_browser_stage_packet(
        browser_stage_packet_after_final_frontend_audit_complete
    )
    issues.extend(
        f"browser stage packet after final frontend audit: {issue}"
        for issue in browser_stage_packet_after_final_frontend_audit_complete_validation.get("issues", [])
    )
    require(
        browser_stage_packet_after_final_frontend_audit_complete_validation.get("ok") is True,
        issues,
        "browser stage packet after final frontend audit validation must pass",
    )
    require(
        summary.get("browserStagePacketAfterFinalFrontendAuditCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.browserStagePacketAfterFinalFrontendAuditCompleteSafety.ok must be true",
    )
    try:
        simulated_cleanup_probes_partial_result = load_json(simulated_cleanup_probes_partial_result_path)
    except ValueError as exc:
        simulated_cleanup_probes_partial_result = {}
        issues.append(str(exc))
    simulated_cleanup_probes_partial_result_validation = validate_browser_stage_result(
        simulated_cleanup_probes_partial_result,
        browser_stage_packet_after_final_frontend_audit_complete,
    )
    issues.extend(
        f"simulated cleanup-probes partial result: {issue}"
        for issue in simulated_cleanup_probes_partial_result_validation.get("issues", [])
    )
    require(
        simulated_cleanup_probes_partial_result_validation.get("ok") is True,
        issues,
        "simulated cleanup-probes partial result validation must pass",
    )
    require(
        summary.get("simulatedCleanupProbesPartialResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedCleanupProbesPartialResultSafety.ok must be true",
    )
    try:
        ledger_after_cleanup_probes_partial = load_json(ledger_after_cleanup_probes_partial_path)
    except ValueError as exc:
        ledger_after_cleanup_probes_partial = {}
        issues.append(str(exc))
    ledger_after_cleanup_probes_partial_validation = validate_browser_execution_ledger(ledger_after_cleanup_probes_partial)
    issues.extend(
        f"ledger after cleanup-probes partial: {issue}"
        for issue in ledger_after_cleanup_probes_partial_validation.get("issues", [])
    )
    require(
        ledger_after_cleanup_probes_partial_validation.get("ok") is True,
        issues,
        "ledger after cleanup-probes partial validation must pass",
    )
    require(
        summary.get("ledgerAfterCleanupProbesPartialSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterCleanupProbesPartialSafety.ok must be true",
    )
    try:
        simulated_cleanup_probes_complete_result = load_json(simulated_cleanup_probes_complete_result_path)
    except ValueError as exc:
        simulated_cleanup_probes_complete_result = {}
        issues.append(str(exc))
    simulated_cleanup_probes_complete_result_validation = validate_browser_stage_result(
        simulated_cleanup_probes_complete_result,
        browser_stage_packet_after_final_frontend_audit_complete,
    )
    issues.extend(
        f"simulated cleanup-probes complete result: {issue}"
        for issue in simulated_cleanup_probes_complete_result_validation.get("issues", [])
    )
    require(
        simulated_cleanup_probes_complete_result_validation.get("ok") is True,
        issues,
        "simulated cleanup-probes complete result validation must pass",
    )
    require(
        summary.get("simulatedCleanupProbesCompleteResultSafety", {}).get("ok") is True,
        issues,
        "summary.simulatedCleanupProbesCompleteResultSafety.ok must be true",
    )
    try:
        ledger_after_cleanup_probes_complete = load_json(ledger_after_cleanup_probes_complete_path)
    except ValueError as exc:
        ledger_after_cleanup_probes_complete = {}
        issues.append(str(exc))
    ledger_after_cleanup_probes_complete_validation = validate_browser_execution_ledger(ledger_after_cleanup_probes_complete)
    issues.extend(
        f"ledger after cleanup-probes complete: {issue}"
        for issue in ledger_after_cleanup_probes_complete_validation.get("issues", [])
    )
    require(
        ledger_after_cleanup_probes_complete_validation.get("ok") is True,
        issues,
        "ledger after cleanup-probes complete validation must pass",
    )
    require(
        summary.get("ledgerAfterCleanupProbesCompleteSafety", {}).get("ok") is True,
        issues,
        "summary.ledgerAfterCleanupProbesCompleteSafety.ok must be true",
    )

    selected = summary.get("selectedStage")
    handoff_selected = handoff.get("selectedStage") if isinstance(handoff.get("selectedStage"), dict) else {}
    if not isinstance(selected, dict):
        issues.append("selectedStage must be an object")
        selected = {}
    for key in ("group", "module", "action", "authorizationAction", "target", "stopAfter"):
        require(selected.get(key) == handoff_selected.get(key), issues, f"selectedStage.{key} mismatch with handoff")

    launch_summary = summary.get("launchPlan")
    if not isinstance(launch_summary, dict):
        issues.append("launchPlan summary must be an object")
        launch_summary = {}
    proof_gates = launch_plan.get("proofGates") if isinstance(launch_plan.get("proofGates"), list) else []
    route_plan = launch_plan.get("routePlan") if isinstance(launch_plan.get("routePlan"), dict) else {}
    require(launch_summary.get("proofGateCount") == len(proof_gates), issues, "launchPlan.proofGateCount mismatch")
    require(launch_summary.get("staticPaths") == route_plan.get("staticPaths"), issues, "launchPlan.staticPaths mismatch")
    require(launch_summary.get("detailRoutePatterns") == route_plan.get("detailRoutePatterns"), issues, "launchPlan.detailRoutePatterns mismatch")

    execution_summary = summary.get("browserExecutionPlan")
    if not isinstance(execution_summary, dict):
        issues.append("browserExecutionPlan summary must be an object")
        execution_summary = {}
    stages = browser_execution_plan.get("stages") if isinstance(browser_execution_plan.get("stages"), list) else []
    require(execution_summary.get("stageCount") == len(stages), issues, "browserExecutionPlan.stageCount mismatch")
    require(
        execution_summary.get("authorizationStageCount")
        == len([stage for stage in stages if isinstance(stage, dict) and stage.get("authorizationRequired") is True]),
        issues,
        "browserExecutionPlan.authorizationStageCount mismatch",
    )

    ledger_summary = summary.get("browserExecutionLedger")
    if not isinstance(ledger_summary, dict):
        issues.append("browserExecutionLedger summary must be an object")
        ledger_summary = {}
    require(
        ledger_summary.get("stageCounts") == browser_execution_ledger.get("stageCounts"),
        issues,
        "browserExecutionLedger.stageCounts mismatch",
    )
    require(
        ledger_summary.get("nextStageId") == browser_execution_ledger.get("nextStageId"),
        issues,
        "browserExecutionLedger.nextStageId mismatch",
    )

    packet_summary = summary.get("browserStagePacket")
    if not isinstance(packet_summary, dict):
        issues.append("browserStagePacket summary must be an object")
        packet_summary = {}
    require(
        packet_summary.get("stageId") == browser_stage_packet.get("stageId"),
        issues,
        "browserStagePacket.stageId mismatch",
    )
    require(
        browser_stage_packet.get("stageId") == browser_execution_ledger.get("nextStageId"),
        issues,
        "browser stage packet must target ledger nextStageId",
    )
    require(
        packet_summary.get("authorizationRequired") == browser_stage_packet.get("authorizationRequired"),
        issues,
        "browserStagePacket.authorizationRequired mismatch",
    )

    browser_runbook_summary_safety: dict[str, Any] = {"ok": True, "issues": []}
    if runbook_declared:
        runbook_issues: list[str] = []
        try:
            browser_runbook_summary = load_json(browser_runbook_summary_path)
        except ValueError as exc:
            browser_runbook_summary = {}
            runbook_issues.append(str(exc))
        next_real_step = (
            browser_runbook_summary.get("nextRealBrowserStep")
            if isinstance(browser_runbook_summary.get("nextRealBrowserStep"), dict)
            else {}
        )
        source_rehearsal = (
            browser_runbook_summary.get("sourceRehearsal")
            if isinstance(browser_runbook_summary.get("sourceRehearsal"), dict)
            else {}
        )
        coverage = (
            browser_runbook_summary.get("coverage")
            if isinstance(browser_runbook_summary.get("coverage"), dict)
            else {}
        )
        required_local_artifacts = (
            browser_runbook_summary.get("requiredLocalArtifacts")
            if isinstance(browser_runbook_summary.get("requiredLocalArtifacts"), dict)
            else {}
        )
        operator_handoff = (
            browser_runbook_summary.get("operatorHandoff")
            if isinstance(browser_runbook_summary.get("operatorHandoff"), dict)
            else {}
        )
        authorization_preparation = (
            operator_handoff.get("authorizationPreparation")
            if isinstance(operator_handoff.get("authorizationPreparation"), dict)
            else {}
        )
        stop_conditions = browser_runbook_summary.get("stopConditions")
        if not isinstance(stop_conditions, list):
            stop_conditions = []
        runbook_require = lambda condition, message: require(condition, runbook_issues, message)
        runbook_require(
            browser_runbook_summary.get("kind") == "allincms_browser_runbook_summary",
            "browser runbook summary kind must be allincms_browser_runbook_summary",
        )
        runbook_require(browser_runbook_summary.get("localOnly") is True, "browser runbook summary must be localOnly")
        runbook_require(
            browser_runbook_summary.get("remoteMutationsPerformed") is False,
            "browser runbook summary must record no remote mutations",
        )
        runbook_require(
            Path(str(browser_runbook_summary.get("sourceSummary", ""))).resolve() == summary_path.resolve(),
            "browser runbook summary sourceSummary must point to rehearsal summary",
        )
        runbook_require(source_rehearsal.get("valid") is True, "browser runbook summary sourceRehearsal.valid must be true")
        runbook_require(source_rehearsal.get("localOnly") is True, "browser runbook summary sourceRehearsal.localOnly must be true")
        runbook_require(
            source_rehearsal.get("remoteMutationsPerformed") is False,
            "browser runbook summary sourceRehearsal.remoteMutationsPerformed must be false",
        )
        runbook_require(
            source_rehearsal.get("commandsSuppressed") == summary.get("commandsSuppressed"),
            "browser runbook summary commandsSuppressed mismatch",
        )
        runbook_require(
            next_real_step.get("stageId") == browser_stage_packet.get("stageId"),
            "browser runbook summary nextRealBrowserStep.stageId mismatch",
        )
        runbook_require(
            next_real_step.get("authorizationRequired") == browser_stage_packet.get("authorizationRequired"),
            "browser runbook summary nextRealBrowserStep.authorizationRequired mismatch",
        )
        runbook_require(
            next_real_step.get("commandsSuppressed") == summary.get("commandsSuppressed"),
            "browser runbook summary nextRealBrowserStep.commandsSuppressed mismatch",
        )
        runbook_require(
            same_path(next_real_step.get("evidenceBundle"), browser_stage_evidence_bundle_dir),
            "browser runbook summary nextRealBrowserStep.evidenceBundle mismatch",
        )
        runbook_require(
            same_path(next_real_step.get("evidenceManifest"), browser_stage_evidence_manifest_path),
            "browser runbook summary nextRealBrowserStep.evidenceManifest mismatch",
        )
        runbook_require(
            same_path(required_local_artifacts.get("nextBrowserStageEvidenceBundle"), browser_stage_evidence_bundle_dir),
            "browser runbook summary requiredLocalArtifacts.nextBrowserStageEvidenceBundle mismatch",
        )
        runbook_require(
            same_path(required_local_artifacts.get("nextBrowserStageEvidenceManifest"), browser_stage_evidence_manifest_path),
            "browser runbook summary requiredLocalArtifacts.nextBrowserStageEvidenceManifest mismatch",
        )
        runbook_require(
            same_path(required_local_artifacts.get("nextBrowserActionHandoff"), next_browser_action_handoff_path),
            "browser runbook summary requiredLocalArtifacts.nextBrowserActionHandoff mismatch",
        )
        runbook_require(
            same_path(
                required_local_artifacts.get("browserStageModuleCaptureAuthorizationPackage"),
                browser_stage_module_capture_authorization_package_path,
            ),
            "browser runbook summary requiredLocalArtifacts.browserStageModuleCaptureAuthorizationPackage mismatch",
        )
        runbook_require(
            coverage.get("initialLedgerNextStageId") == browser_execution_ledger.get("nextStageId"),
            "browser runbook summary coverage.initialLedgerNextStageId mismatch",
        )
        runbook_require(operator_handoff.get("status") == "ready", "browser runbook operatorHandoff.status must be ready")
        runbook_require(operator_handoff.get("notAuthorization") is True, "browser runbook operatorHandoff must say it is not authorization")
        runbook_require(
            operator_handoff.get("stageId") == browser_stage_packet.get("stageId"),
            "browser runbook operatorHandoff.stageId mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("packetPath"), browser_stage_packet_path),
            "browser runbook operatorHandoff.packetPath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("ledgerPath"), browser_execution_ledger_path),
            "browser runbook operatorHandoff.ledgerPath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("evidenceBundleDir"), browser_stage_evidence_bundle_dir),
            "browser runbook operatorHandoff.evidenceBundleDir mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("evidenceManifestPath"), browser_stage_evidence_manifest_path),
            "browser runbook operatorHandoff.evidenceManifestPath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("nextBrowserActionHandoffPath"), next_browser_action_handoff_path),
            "browser runbook operatorHandoff.nextBrowserActionHandoffPath mismatch",
        )
        runbook_require(
            same_path(
                operator_handoff.get("browserStageModuleCaptureAuthorizationPackagePath"),
                browser_stage_module_capture_authorization_package_path,
            ),
            "browser runbook operatorHandoff.browserStageModuleCaptureAuthorizationPackagePath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("stageResultTemplatePath"), browser_stage_evidence_bundle_dir / "stage-result-template.json"),
            "browser runbook operatorHandoff.stageResultTemplatePath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("bundleStageResultDraftPath"), browser_stage_evidence_bundle_dir / "stage-result.json"),
            "browser runbook operatorHandoff.bundleStageResultDraftPath mismatch",
        )
        expected_ledger_stage_result = browser_stage_packet_path.with_name(browser_stage_packet_path.stem + "-stage-result.json")
        runbook_require(
            same_path(operator_handoff.get("ledgerExpectedStageResultPath"), expected_ledger_stage_result),
            "browser runbook operatorHandoff.ledgerExpectedStageResultPath mismatch",
        )
        runbook_require(
            same_path(operator_handoff.get("stageResultOutputPath"), expected_ledger_stage_result),
            "browser runbook operatorHandoff.stageResultOutputPath must match ledgerExpectedStageResultPath",
        )
        runbook_require(
            operator_handoff.get("requiredProof") == browser_stage_packet.get("requiredProof"),
            "browser runbook operatorHandoff.requiredProof mismatch",
        )
        runbook_require(
            operator_handoff.get("stopAfter") == browser_stage_packet.get("stopAfter"),
            "browser runbook operatorHandoff.stopAfter mismatch",
        )
        runbook_require(
            operator_handoff.get("nextActionMode") == next_real_step.get("mode"),
            "browser runbook operatorHandoff.nextActionMode mismatch",
        )
        runbook_require(
            isinstance(operator_handoff.get("stageResultCommandTemplate"), str)
            and str(browser_stage_packet_path) in operator_handoff.get("stageResultCommandTemplate", "")
            and str(browser_stage_evidence_bundle_dir / "stage-result.json") in operator_handoff.get("stageResultCommandTemplate", ""),
            "browser runbook operatorHandoff.stageResultCommandTemplate must reference current packet and stage result",
        )
        runbook_require(
            operator_handoff.get("ledgerApplyCommand") == browser_stage_packet.get("ledgerUpdate", {}).get("commandTemplate"),
            "browser runbook operatorHandoff.ledgerApplyCommand mismatch",
        )
        runbook_require(
            str(browser_execution_ledger_path) in str(operator_handoff.get("ledgerApplyCommand", "")),
            "browser runbook operatorHandoff.ledgerApplyCommand missing current ledger path",
        )
        runbook_require(
            str(browser_stage_packet_path) in str(operator_handoff.get("ledgerApplyCommand", "")),
            "browser runbook operatorHandoff.ledgerApplyCommand missing current packet path",
        )
        runbook_require(
            str(browser_stage_packet_path.with_name(browser_stage_packet_path.stem + "-stage-result.json"))
            in str(operator_handoff.get("ledgerApplyCommand", "")),
            "browser runbook operatorHandoff.ledgerApplyCommand missing expected stage-result path",
        )
        runbook_require(
            authorization_preparation.get("required") == (browser_stage_packet.get("authorizationRequired") is True),
            "browser runbook operatorHandoff.authorizationPreparation.required mismatch",
        )
        runbook_require(
            "not action-time user authorization" in str(authorization_preparation.get("note", "")),
            "browser runbook operatorHandoff.authorizationPreparation must warn about authorization",
        )
        runbook_require(
            "not user authorization" in str(operator_handoff.get("warning", "")),
            "browser runbook operatorHandoff.warning must say it is not user authorization",
        )
        runbook_require(
            summary.get("browserRunbookSummary", {}).get("nextStageId") == next_real_step.get("stageId"),
            "browserRunbookSummary.nextStageId mismatch",
        )
        runbook_require(
            summary.get("browserRunbookSummary", {}).get("authorizationRequired")
            == next_real_step.get("authorizationRequired"),
            "browserRunbookSummary.authorizationRequired mismatch",
        )
        runbook_require(
            summary.get("browserRunbookSummary", {}).get("initialLedgerNextStageId")
            == coverage.get("initialLedgerNextStageId"),
            "browserRunbookSummary.initialLedgerNextStageId mismatch",
        )
        stop_text = "\n".join(str(item) for item in stop_conditions)
        runbook_require("suppressed command" in stop_text, "browser runbook summary must warn about suppressed commands")
        runbook_require("authorization" in stop_text, "browser runbook summary must warn about authorization")
        browser_runbook_summary_safety = {"ok": not runbook_issues, "issues": runbook_issues}
        issues.extend(f"browser runbook summary: {issue}" for issue in runbook_issues)

    stage_result_summary = summary.get("stageResultSimulation")
    if not isinstance(stage_result_summary, dict):
        issues.append("stageResultSimulation summary must be an object")
        stage_result_summary = {}
    require(
        stage_result_summary.get("stageId") == simulated_stage_result.get("stageId") == browser_stage_packet.get("stageId"),
        issues,
        "stageResultSimulation.stageId must match packet stageId",
    )
    require(stage_result_summary.get("status") == "completed", issues, "stageResultSimulation.status must be completed")
    after_entries = ledger_after_first_stage.get("entries") if isinstance(ledger_after_first_stage.get("entries"), list) else []
    after_stage = next((entry for entry in after_entries if isinstance(entry, dict) and entry.get("stageId") == browser_stage_packet.get("stageId")), {})
    require(after_stage.get("status") == "completed", issues, "ledgerAfterFirstStage must mark packet stage completed")
    require(
        stage_result_summary.get("nextStageIdAfterApply") == ledger_after_first_stage.get("nextStageId"),
        issues,
        "stageResultSimulation.nextStageIdAfterApply mismatch",
    )

    packet_after_summary = summary.get("browserStagePacketAfterFirstStage")
    if not isinstance(packet_after_summary, dict):
        issues.append("browserStagePacketAfterFirstStage summary must be an object")
        packet_after_summary = {}
    require(
        packet_after_summary.get("stageId") == browser_stage_packet_after_first_stage.get("stageId"),
        issues,
        "browserStagePacketAfterFirstStage.stageId mismatch",
    )
    require(
        browser_stage_packet_after_first_stage.get("stageId") == ledger_after_first_stage.get("nextStageId"),
        issues,
        "browser stage packet after first stage must target ledgerAfterFirstStage nextStageId",
    )
    require(
        browser_stage_packet_after_first_stage.get("authorizationRequired") is True,
        issues,
        "browser stage packet after first stage should require authorization",
    )
    require(
        packet_after_summary.get("allowedActionCount") == len(browser_stage_packet_after_first_stage.get("allowedActions", [])),
        issues,
        "browserStagePacketAfterFirstStage.allowedActionCount mismatch",
    )

    create_site_simulation = summary.get("createSiteStageSimulation")
    if not isinstance(create_site_simulation, dict):
        issues.append("createSiteStageSimulation summary must be an object")
        create_site_simulation = {}
    require(
        create_site_simulation.get("stageId")
        == simulated_create_site_result.get("stageId")
        == browser_stage_packet_after_first_stage.get("stageId"),
        issues,
        "createSiteStageSimulation.stageId must match create-site packet stageId",
    )
    require(create_site_simulation.get("status") == "completed", issues, "createSiteStageSimulation.status must be completed")
    require(
        create_site_simulation.get("nextStageIdAfterApply") == ledger_after_create_site.get("nextStageId"),
        issues,
        "createSiteStageSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_create_site.get("nextStageId") == "setup_pages_inspection",
        issues,
        "ledgerAfterCreateSite.nextStageId must be setup_pages_inspection",
    )

    packet_after_create_summary = summary.get("browserStagePacketAfterCreateSite")
    if not isinstance(packet_after_create_summary, dict):
        issues.append("browserStagePacketAfterCreateSite summary must be an object")
        packet_after_create_summary = {}
    require(
        packet_after_create_summary.get("stageId") == browser_stage_packet_after_create_site.get("stageId"),
        issues,
        "browserStagePacketAfterCreateSite.stageId mismatch",
    )
    require(
        browser_stage_packet_after_create_site.get("stageId") == ledger_after_create_site.get("nextStageId"),
        issues,
        "browser stage packet after create site must target ledgerAfterCreateSite nextStageId",
    )
    require(
        browser_stage_packet_after_create_site.get("authorizationRequired") is False,
        issues,
        "browser stage packet after create site should be read-only",
    )
    require(
        packet_after_create_summary.get("allowedActionCount") == len(browser_stage_packet_after_create_site.get("allowedActions", [])),
        issues,
        "browserStagePacketAfterCreateSite.allowedActionCount mismatch",
    )

    setup_simulation = summary.get("setupStageSimulation")
    if not isinstance(setup_simulation, dict):
        issues.append("setupStageSimulation summary must be an object")
        setup_simulation = {}
    require(
        setup_simulation.get("stageId")
        == simulated_setup_result.get("stageId")
        == browser_stage_packet_after_create_site.get("stageId"),
        issues,
        "setupStageSimulation.stageId must match setup packet stageId",
    )
    require(setup_simulation.get("status") == "completed", issues, "setupStageSimulation.status must be completed")
    require(
        setup_simulation.get("nextStageIdAfterApply") == ledger_after_setup.get("nextStageId"),
        issues,
        "setupStageSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_setup.get("nextStageId") == "module_interface_capture",
        issues,
        "ledgerAfterSetup.nextStageId must be module_interface_capture",
    )

    packet_after_setup_summary = summary.get("browserStagePacketAfterSetup")
    if not isinstance(packet_after_setup_summary, dict):
        issues.append("browserStagePacketAfterSetup summary must be an object")
        packet_after_setup_summary = {}
    require(
        packet_after_setup_summary.get("stageId") == browser_stage_packet_after_setup.get("stageId"),
        issues,
        "browserStagePacketAfterSetup.stageId mismatch",
    )
    require(
        browser_stage_packet_after_setup.get("stageId") == ledger_after_setup.get("nextStageId"),
        issues,
        "browser stage packet after setup must target ledgerAfterSetup nextStageId",
    )
    require(
        browser_stage_packet_after_setup.get("authorizationRequired") is True,
        issues,
        "browser stage packet after setup should require authorization",
    )
    require(
        packet_after_setup_summary.get("allowedActionCount") == len(browser_stage_packet_after_setup.get("allowedActions", [])),
        issues,
        "browserStagePacketAfterSetup.allowedActionCount mismatch",
    )

    module_capture_partial = summary.get("moduleCapturePartialSimulation")
    if not isinstance(module_capture_partial, dict):
        issues.append("moduleCapturePartialSimulation summary must be an object")
        module_capture_partial = {}
    require(
        module_capture_partial.get("stageId")
        == simulated_module_capture_partial_result.get("stageId")
        == browser_stage_packet_after_setup.get("stageId"),
        issues,
        "moduleCapturePartialSimulation.stageId must match module capture packet stageId",
    )
    require(
        module_capture_partial.get("status") == "partial",
        issues,
        "moduleCapturePartialSimulation.status must be partial",
    )
    require(
        module_capture_partial.get("nextStageIdAfterApply") == ledger_after_module_capture_partial.get("nextStageId"),
        issues,
        "moduleCapturePartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_module_capture_partial.get("nextStageId") in {"", None},
        issues,
        "ledgerAfterModuleCapturePartial.nextStageId must be empty after one partial module capture",
    )
    module_capture_entries = (
        ledger_after_module_capture_partial.get("entries")
        if isinstance(ledger_after_module_capture_partial.get("entries"), list)
        else []
    )
    module_entry = next(
        (entry for entry in module_capture_entries if isinstance(entry, dict) and entry.get("stageId") == "module_interface_capture"),
        {},
    )
    require(
        module_entry.get("status") == "partial",
        issues,
        "ledgerAfterModuleCapturePartial must keep module_interface_capture partial",
    )
    later_ready = [
        entry.get("stageId")
        for entry in module_capture_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") not in {"module_interface_capture"}
    ]
    require(not later_ready, issues, "partial module capture must not unlock later ready stages")

    module_capture_coverage_summary = summary.get("moduleCaptureCoverage")
    if not isinstance(module_capture_coverage_summary, dict):
        issues.append("moduleCaptureCoverage summary must be an object")
        module_capture_coverage_summary = {}
    require(
        module_capture_coverage_summary.get("complete") is False,
        issues,
        "moduleCaptureCoverage.complete must remain false after one captured stage",
    )
    require(
        module_capture_coverage_summary.get("jsonReplayReady") is False,
        issues,
        "moduleCaptureCoverage.jsonReplayReady must remain false after one captured stage",
    )
    coverage_counts = module_capture_coverage_summary.get("coverageCounts")
    if not isinstance(coverage_counts, dict):
        issues.append("moduleCaptureCoverage.coverageCounts must be an object")
        coverage_counts = {}
    require(coverage_counts.get("captured") == 1, issues, "moduleCaptureCoverage.coverageCounts.captured must be 1")
    require(coverage_counts.get("pending", 0) > 0, issues, "moduleCaptureCoverage.coverageCounts.pending must be greater than 0")
    require(
        module_capture_coverage_summary.get("nextUncapturedStageKey") == module_capture_coverage.get("nextUncapturedStageKey"),
        issues,
        "moduleCaptureCoverage.nextUncapturedStageKey mismatch",
    )

    coverage_sync_summary = summary.get("moduleCaptureCoverageLedgerSync")
    if not isinstance(coverage_sync_summary, dict):
        issues.append("moduleCaptureCoverageLedgerSync summary must be an object")
        coverage_sync_summary = {}
    require(
        coverage_sync_summary.get("nextStageIdAfterSync") == "module_interface_capture",
        issues,
        "coverage sync must make module_interface_capture ready for the next missing capture",
    )
    synced_entries = (
        ledger_after_module_capture_coverage_sync.get("entries")
        if isinstance(ledger_after_module_capture_coverage_sync.get("entries"), list)
        else []
    )
    synced_module_entry = next(
        (entry for entry in synced_entries if isinstance(entry, dict) and entry.get("stageId") == "module_interface_capture"),
        {},
    )
    require(synced_module_entry.get("status") == "ready", issues, "synced module_interface_capture must be ready")
    synced_actions = synced_module_entry.get("nextAllowedActions") if isinstance(synced_module_entry.get("nextAllowedActions"), list) else []
    require(
        any(str(module_capture_coverage.get("nextUncapturedStageKey", "")) in str(action) for action in synced_actions),
        issues,
        "synced module capture actions must name nextUncapturedStageKey",
    )
    forbidden_ready = [
        entry.get("stageId")
        for entry in synced_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"theme_page_route_launch", "forms_media_settings", "batch_upload_publish"}
    ]
    require(not forbidden_ready, issues, "coverage sync before completion must not unlock downstream mutation stages")

    completion_summary = summary.get("moduleCaptureCompletionSimulation")
    if not isinstance(completion_summary, dict):
        issues.append("moduleCaptureCompletionSimulation summary must be an object")
        completion_summary = {}
    require(completion_summary.get("complete") is True, issues, "complete module capture coverage must be complete")
    require(
        completion_summary.get("interfaceCoverageComplete") is True,
        issues,
        "complete module capture coverage must set interfaceCoverageComplete true",
    )
    require(
        completion_summary.get("actionReplayContractsVerified") is False,
        issues,
        "complete module capture coverage must not verify action replay contracts",
    )
    require(
        completion_summary.get("jsonReplayReady") is False,
        issues,
        "complete module capture coverage must keep jsonReplayReady false",
    )
    complete_counts = completion_summary.get("coverageCounts")
    if not isinstance(complete_counts, dict):
        issues.append("moduleCaptureCompletionSimulation.coverageCounts must be an object")
        complete_counts = {}
    require(complete_counts.get("pending") == 0, issues, "complete module capture coverage must have no pending stages")
    require(
        complete_counts.get("captured") == complete_counts.get("total"),
        issues,
        "complete module capture coverage must capture every stage",
    )
    require(
        completion_summary.get("nextStageIdAfterSync") == "theme_page_route_launch",
        issues,
        "complete module capture sync must unlock theme_page_route_launch next",
    )
    require(
        completion_summary.get("nextPacketStageId") == "theme_page_route_launch",
        issues,
        "packet after complete module capture must target theme_page_route_launch",
    )
    require(
        completion_summary.get("nextPacketAuthorizationRequired") is True,
        issues,
        "theme_page_route_launch packet should require authorization",
    )
    completed_entries = (
        ledger_after_module_capture_complete.get("entries")
        if isinstance(ledger_after_module_capture_complete.get("entries"), list)
        else []
    )
    completed_module_entry = next(
        (entry for entry in completed_entries if isinstance(entry, dict) and entry.get("stageId") == "module_interface_capture"),
        {},
    )
    require(
        completed_module_entry.get("status") == "completed",
        issues,
        "complete coverage sync must mark module_interface_capture completed",
    )
    require(
        browser_stage_packet_after_module_capture_complete.get("stageId")
        == ledger_after_module_capture_complete.get("nextStageId")
        == "theme_page_route_launch",
        issues,
        "complete coverage packet must target ledger nextStageId theme_page_route_launch",
    )

    theme_partial = summary.get("themeLaunchPartialSimulation")
    if not isinstance(theme_partial, dict):
        issues.append("themeLaunchPartialSimulation summary must be an object")
        theme_partial = {}
    require(
        theme_partial.get("stageId")
        == simulated_theme_launch_partial_result.get("stageId")
        == browser_stage_packet_after_module_capture_complete.get("stageId"),
        issues,
        "themeLaunchPartialSimulation.stageId must match theme launch packet stageId",
    )
    require(theme_partial.get("status") == "partial", issues, "themeLaunchPartialSimulation.status must be partial")
    require(
        theme_partial.get("nextStageIdAfterApply") == ledger_after_theme_launch_partial.get("nextStageId"),
        issues,
        "themeLaunchPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_theme_launch_partial.get("nextStageId") in {"", None},
        issues,
        "partial theme launch must not unlock static_frontend_audit",
    )
    partial_theme_entries = (
        ledger_after_theme_launch_partial.get("entries")
        if isinstance(ledger_after_theme_launch_partial.get("entries"), list)
        else []
    )
    partial_theme_entry = next(
        (entry for entry in partial_theme_entries if isinstance(entry, dict) and entry.get("stageId") == "theme_page_route_launch"),
        {},
    )
    require(
        partial_theme_entry.get("status") == "partial",
        issues,
        "ledgerAfterThemeLaunchPartial must keep theme_page_route_launch partial",
    )
    partial_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_theme_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"static_frontend_audit", "content_probe_create", "batch_upload_publish"}
    ]
    require(not partial_forbidden_ready, issues, "partial theme launch must not unlock frontend audit or upload stages")
    require(
        browser_stage_packet_after_theme_launch_partial_recovery.get("stageId") == "theme_page_route_launch",
        issues,
        "theme launch recovery packet must target the same partial stage",
    )
    require(
        browser_stage_packet_after_theme_launch_partial_recovery.get("recovery") is True,
        issues,
        "theme launch recovery packet must be marked recovery",
    )
    require(
        theme_partial.get("recoveryPacketStageId") == "theme_page_route_launch",
        issues,
        "themeLaunchPartialSimulation must record recovery packet stage id",
    )
    require(
        theme_partial.get("recoveryPacket") is True,
        issues,
        "themeLaunchPartialSimulation must record recovery packet true",
    )

    theme_completion = summary.get("themeLaunchCompletionSimulation")
    if not isinstance(theme_completion, dict):
        issues.append("themeLaunchCompletionSimulation summary must be an object")
        theme_completion = {}
    require(
        theme_completion.get("stageId")
        == simulated_theme_launch_complete_result.get("stageId")
        == browser_stage_packet_after_theme_launch_partial_recovery.get("stageId"),
        issues,
        "themeLaunchCompletionSimulation.stageId must match theme launch recovery packet stageId",
    )
    require(
        theme_completion.get("status") == "completed",
        issues,
        "themeLaunchCompletionSimulation.status must be completed",
    )
    require(
        theme_completion.get("nextStageIdAfterApply") == "static_frontend_audit",
        issues,
        "complete theme launch must unlock static_frontend_audit",
    )
    require(
        theme_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "themeLaunchCompletionSimulation must complete from the recovery packet",
    )
    require(
        theme_completion.get("nextPacketStageId") == "static_frontend_audit",
        issues,
        "packet after complete theme launch must target static_frontend_audit",
    )
    require(
        theme_completion.get("nextPacketAuthorizationRequired") is False,
        issues,
        "static_frontend_audit packet should not require authorization",
    )
    complete_theme_entries = (
        ledger_after_theme_launch_complete.get("entries")
        if isinstance(ledger_after_theme_launch_complete.get("entries"), list)
        else []
    )
    recovery_complete_entries = (
        ledger_after_theme_launch_recovery_complete.get("entries")
        if isinstance(ledger_after_theme_launch_recovery_complete.get("entries"), list)
        else []
    )
    complete_theme_entry = next(
        (entry for entry in complete_theme_entries if isinstance(entry, dict) and entry.get("stageId") == "theme_page_route_launch"),
        {},
    )
    recovery_complete_theme_entry = next(
        (
            entry
            for entry in recovery_complete_entries
            if isinstance(entry, dict) and entry.get("stageId") == "theme_page_route_launch"
        ),
        {},
    )
    require(
        complete_theme_entry.get("status") == "completed",
        issues,
        "ledgerAfterThemeLaunchComplete must mark theme_page_route_launch completed",
    )
    require(
        recovery_complete_theme_entry.get("status") == "completed",
        issues,
        "ledgerAfterThemeLaunchRecoveryComplete must mark theme_page_route_launch completed",
    )
    require(
        ledger_after_theme_launch_recovery_complete.get("nextStageId") == "static_frontend_audit",
        issues,
        "theme launch recovery complete ledger must unlock static_frontend_audit",
    )
    require(
        browser_stage_packet_after_theme_launch_complete.get("stageId")
        == ledger_after_theme_launch_complete.get("nextStageId")
        == "static_frontend_audit",
        issues,
        "complete theme launch packet must target ledger nextStageId static_frontend_audit",
    )

    static_partial = summary.get("staticAuditPartialSimulation")
    if not isinstance(static_partial, dict):
        issues.append("staticAuditPartialSimulation summary must be an object")
        static_partial = {}
    require(
        static_partial.get("stageId")
        == simulated_static_audit_partial_result.get("stageId")
        == browser_stage_packet_after_theme_launch_complete.get("stageId"),
        issues,
        "staticAuditPartialSimulation.stageId must match static audit packet stageId",
    )
    require(static_partial.get("status") == "partial", issues, "staticAuditPartialSimulation.status must be partial")
    require(
        static_partial.get("nextStageIdAfterApply") == ledger_after_static_audit_partial.get("nextStageId"),
        issues,
        "staticAuditPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_static_audit_partial.get("nextStageId") in {"", None},
        issues,
        "partial static frontend audit must not unlock content_probe_create",
    )
    partial_static_entries = (
        ledger_after_static_audit_partial.get("entries")
        if isinstance(ledger_after_static_audit_partial.get("entries"), list)
        else []
    )
    partial_static_entry = next(
        (entry for entry in partial_static_entries if isinstance(entry, dict) and entry.get("stageId") == "static_frontend_audit"),
        {},
    )
    require(
        partial_static_entry.get("status") == "partial",
        issues,
        "ledgerAfterStaticAuditPartial must keep static_frontend_audit partial",
    )
    partial_static_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_static_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"content_probe_create", "save_request_capture", "batch_upload_publish"}
    ]
    require(not partial_static_forbidden_ready, issues, "partial static audit must not unlock content or upload stages")
    browser_stage_packet_after_static_audit_partial_recovery_validation = validate_recovery_packet_artifact(
        "static audit",
        browser_stage_packet_after_static_audit_partial_recovery_path,
        "static_frontend_audit",
        static_partial,
        issues,
        ledger_after_static_audit_partial_path,
    )

    static_completion = summary.get("staticAuditCompletionSimulation")
    if not isinstance(static_completion, dict):
        issues.append("staticAuditCompletionSimulation summary must be an object")
        static_completion = {}
    require(
        static_completion.get("stageId")
        == simulated_static_audit_complete_result.get("stageId")
        == browser_stage_packet_after_theme_launch_complete.get("stageId"),
        issues,
        "staticAuditCompletionSimulation.stageId must match static audit packet stageId",
    )
    require(
        static_completion.get("status") == "completed",
        issues,
        "staticAuditCompletionSimulation.status must be completed",
    )
    require(
        static_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "staticAuditCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        static_completion.get("nextStageIdAfterApply") == "content_probe_create",
        issues,
        "complete static audit must unlock content_probe_create",
    )
    require(
        static_completion.get("nextPacketStageId") == "content_probe_create",
        issues,
        "packet after complete static audit must target content_probe_create",
    )
    require(
        static_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "content_probe_create packet should require authorization",
    )
    complete_static_entries = (
        ledger_after_static_audit_complete.get("entries")
        if isinstance(ledger_after_static_audit_complete.get("entries"), list)
        else []
    )
    complete_static_entry = next(
        (entry for entry in complete_static_entries if isinstance(entry, dict) and entry.get("stageId") == "static_frontend_audit"),
        {},
    )
    require(
        complete_static_entry.get("status") == "completed",
        issues,
        "ledgerAfterStaticAuditComplete must mark static_frontend_audit completed",
    )
    require(
        browser_stage_packet_after_static_audit_complete.get("stageId")
        == ledger_after_static_audit_complete.get("nextStageId")
        == "content_probe_create",
        issues,
        "complete static audit packet must target ledger nextStageId content_probe_create",
    )

    content_probe_partial = summary.get("contentProbePartialSimulation")
    if not isinstance(content_probe_partial, dict):
        issues.append("contentProbePartialSimulation summary must be an object")
        content_probe_partial = {}
    require(
        content_probe_partial.get("stageId")
        == simulated_content_probe_partial_result.get("stageId")
        == browser_stage_packet_after_static_audit_complete.get("stageId"),
        issues,
        "contentProbePartialSimulation.stageId must match content probe packet stageId",
    )
    require(content_probe_partial.get("status") == "partial", issues, "contentProbePartialSimulation.status must be partial")
    require(
        content_probe_partial.get("nextStageIdAfterApply") == ledger_after_content_probe_partial.get("nextStageId"),
        issues,
        "contentProbePartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_content_probe_partial.get("nextStageId") in {"", None},
        issues,
        "partial content probe must not unlock save_request_capture",
    )
    partial_probe_entries = (
        ledger_after_content_probe_partial.get("entries")
        if isinstance(ledger_after_content_probe_partial.get("entries"), list)
        else []
    )
    partial_probe_entry = next(
        (entry for entry in partial_probe_entries if isinstance(entry, dict) and entry.get("stageId") == "content_probe_create"),
        {},
    )
    require(
        partial_probe_entry.get("status") == "partial",
        issues,
        "ledgerAfterContentProbePartial must keep content_probe_create partial",
    )
    partial_probe_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_probe_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"save_request_capture", "publish_sample_verify", "batch_upload_publish"}
    ]
    require(not partial_probe_forbidden_ready, issues, "partial content probe must not unlock save, publish, or upload stages")
    browser_stage_packet_after_content_probe_partial_recovery_validation = validate_recovery_packet_artifact(
        "content probe",
        browser_stage_packet_after_content_probe_partial_recovery_path,
        "content_probe_create",
        content_probe_partial,
        issues,
        ledger_after_content_probe_partial_path,
    )

    content_probe_completion = summary.get("contentProbeCompletionSimulation")
    if not isinstance(content_probe_completion, dict):
        issues.append("contentProbeCompletionSimulation summary must be an object")
        content_probe_completion = {}
    require(
        content_probe_completion.get("stageId")
        == simulated_content_probe_complete_result.get("stageId")
        == browser_stage_packet_after_static_audit_complete.get("stageId"),
        issues,
        "contentProbeCompletionSimulation.stageId must match content probe packet stageId",
    )
    require(
        content_probe_completion.get("status") == "completed",
        issues,
        "contentProbeCompletionSimulation.status must be completed",
    )
    require(
        content_probe_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "contentProbeCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        content_probe_completion.get("nextStageIdAfterApply") == "save_request_capture",
        issues,
        "complete content probe must unlock save_request_capture",
    )
    require(
        content_probe_completion.get("nextPacketStageId") == "save_request_capture",
        issues,
        "packet after complete content probe must target save_request_capture",
    )
    require(
        content_probe_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "save_request_capture packet should require authorization",
    )
    complete_probe_entries = (
        ledger_after_content_probe_complete.get("entries")
        if isinstance(ledger_after_content_probe_complete.get("entries"), list)
        else []
    )
    complete_probe_entry = next(
        (entry for entry in complete_probe_entries if isinstance(entry, dict) and entry.get("stageId") == "content_probe_create"),
        {},
    )
    require(
        complete_probe_entry.get("status") == "completed",
        issues,
        "ledgerAfterContentProbeComplete must mark content_probe_create completed",
    )
    require(
        browser_stage_packet_after_content_probe_complete.get("stageId")
        == ledger_after_content_probe_complete.get("nextStageId")
        == "save_request_capture",
        issues,
        "complete content probe packet must target ledger nextStageId save_request_capture",
    )

    save_request_partial = summary.get("saveRequestPartialSimulation")
    if not isinstance(save_request_partial, dict):
        issues.append("saveRequestPartialSimulation summary must be an object")
        save_request_partial = {}
    require(
        save_request_partial.get("stageId")
        == simulated_save_request_partial_result.get("stageId")
        == browser_stage_packet_after_content_probe_complete.get("stageId"),
        issues,
        "saveRequestPartialSimulation.stageId must match save request packet stageId",
    )
    require(save_request_partial.get("status") == "partial", issues, "saveRequestPartialSimulation.status must be partial")
    require(
        save_request_partial.get("nextStageIdAfterApply") == ledger_after_save_request_partial.get("nextStageId"),
        issues,
        "saveRequestPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_save_request_partial.get("nextStageId") in {"", None},
        issues,
        "partial save request must not unlock publish_sample_verify or manifest_schema_gate",
    )
    partial_save_entries = (
        ledger_after_save_request_partial.get("entries")
        if isinstance(ledger_after_save_request_partial.get("entries"), list)
        else []
    )
    partial_save_entry = next(
        (entry for entry in partial_save_entries if isinstance(entry, dict) and entry.get("stageId") == "save_request_capture"),
        {},
    )
    require(
        partial_save_entry.get("status") == "partial",
        issues,
        "ledgerAfterSaveRequestPartial must keep save_request_capture partial",
    )
    partial_save_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_save_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"publish_sample_verify", "manifest_schema_gate", "batch_upload_publish"}
    ]
    require(not partial_save_forbidden_ready, issues, "partial save request must not unlock publish, manifest, or upload stages")
    browser_stage_packet_after_save_request_partial_recovery_validation = validate_recovery_packet_artifact(
        "save request",
        browser_stage_packet_after_save_request_partial_recovery_path,
        "save_request_capture",
        save_request_partial,
        issues,
        ledger_after_save_request_partial_path,
    )

    save_request_completion = summary.get("saveRequestCompletionSimulation")
    if not isinstance(save_request_completion, dict):
        issues.append("saveRequestCompletionSimulation summary must be an object")
        save_request_completion = {}
    require(
        save_request_completion.get("stageId")
        == simulated_save_request_complete_result.get("stageId")
        == browser_stage_packet_after_content_probe_complete.get("stageId"),
        issues,
        "saveRequestCompletionSimulation.stageId must match save request packet stageId",
    )
    require(
        save_request_completion.get("status") == "completed",
        issues,
        "saveRequestCompletionSimulation.status must be completed",
    )
    require(
        save_request_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "saveRequestCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        save_request_completion.get("nextStageIdAfterApply") == "publish_sample_verify",
        issues,
        "complete save request must expose publish_sample_verify first",
    )
    require(
        save_request_completion.get("nextPacketStageId") == "publish_sample_verify",
        issues,
        "packet after complete save request must target publish_sample_verify",
    )
    require(
        save_request_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "publish_sample_verify packet should require authorization",
    )
    require(
        save_request_completion.get("manifestSchemaGateReady") is True,
        issues,
        "complete save request must also make manifest_schema_gate ready",
    )
    complete_save_entries = (
        ledger_after_save_request_complete.get("entries")
        if isinstance(ledger_after_save_request_complete.get("entries"), list)
        else []
    )
    complete_save_entry = next(
        (entry for entry in complete_save_entries if isinstance(entry, dict) and entry.get("stageId") == "save_request_capture"),
        {},
    )
    require(
        complete_save_entry.get("status") == "completed",
        issues,
        "ledgerAfterSaveRequestComplete must mark save_request_capture completed",
    )
    manifest_gate_entry = next(
        (entry for entry in complete_save_entries if isinstance(entry, dict) and entry.get("stageId") == "manifest_schema_gate"),
        {},
    )
    require(
        manifest_gate_entry.get("status") == "ready",
        issues,
        "ledgerAfterSaveRequestComplete must mark manifest_schema_gate ready",
    )
    require(
        browser_stage_packet_after_save_request_complete.get("stageId")
        == ledger_after_save_request_complete.get("nextStageId")
        == "publish_sample_verify",
        issues,
        "complete save request packet must target ledger nextStageId publish_sample_verify",
    )

    publish_sample_partial = summary.get("publishSamplePartialSimulation")
    if not isinstance(publish_sample_partial, dict):
        issues.append("publishSamplePartialSimulation summary must be an object")
        publish_sample_partial = {}
    require(
        publish_sample_partial.get("stageId")
        == simulated_publish_sample_partial_result.get("stageId")
        == browser_stage_packet_after_save_request_complete.get("stageId"),
        issues,
        "publishSamplePartialSimulation.stageId must match publish sample packet stageId",
    )
    require(
        publish_sample_partial.get("status") == "partial",
        issues,
        "publishSamplePartialSimulation.status must be partial",
    )
    require(
        publish_sample_partial.get("nextStageIdAfterApply") == ledger_after_publish_sample_partial.get("nextStageId"),
        issues,
        "publishSamplePartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_publish_sample_partial.get("nextStageId") == "manifest_schema_gate",
        issues,
        "partial publish sample may only expose the already-ready local manifest_schema_gate",
    )
    require(
        publish_sample_partial.get("manifestSchemaGateStillReady") is True,
        issues,
        "partial publish sample should preserve manifest_schema_gate readiness but not expose it as next stage",
    )
    partial_publish_entries = (
        ledger_after_publish_sample_partial.get("entries")
        if isinstance(ledger_after_publish_sample_partial.get("entries"), list)
        else []
    )
    partial_publish_entry = next(
        (entry for entry in partial_publish_entries if isinstance(entry, dict) and entry.get("stageId") == "publish_sample_verify"),
        {},
    )
    require(
        partial_publish_entry.get("status") == "partial",
        issues,
        "ledgerAfterPublishSamplePartial must keep publish_sample_verify partial",
    )
    partial_publish_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_publish_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"batch_upload_publish", "forms_media_settings"}
    ]
    require(not partial_publish_forbidden_ready, issues, "partial publish sample must not expose batch or settings stages")
    browser_stage_packet_after_publish_sample_partial_recovery_validation = validate_recovery_packet_artifact(
        "publish sample",
        browser_stage_packet_after_publish_sample_partial_recovery_path,
        "publish_sample_verify",
        publish_sample_partial,
        issues,
        ledger_after_publish_sample_partial_path,
    )

    publish_sample_completion = summary.get("publishSampleCompletionSimulation")
    if not isinstance(publish_sample_completion, dict):
        issues.append("publishSampleCompletionSimulation summary must be an object")
        publish_sample_completion = {}
    require(
        publish_sample_completion.get("stageId")
        == simulated_publish_sample_complete_result.get("stageId")
        == browser_stage_packet_after_save_request_complete.get("stageId"),
        issues,
        "publishSampleCompletionSimulation.stageId must match publish sample packet stageId",
    )
    require(
        publish_sample_completion.get("status") == "completed",
        issues,
        "publishSampleCompletionSimulation.status must be completed",
    )
    require(
        publish_sample_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "publishSampleCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        publish_sample_completion.get("nextStageIdAfterApply") == "manifest_schema_gate",
        issues,
        "complete publish sample must expose manifest_schema_gate before batch upload",
    )
    require(
        publish_sample_completion.get("nextPacketStageId") == "manifest_schema_gate",
        issues,
        "packet after complete publish sample must target manifest_schema_gate",
    )
    require(
        publish_sample_completion.get("nextPacketAuthorizationRequired") is False,
        issues,
        "manifest_schema_gate packet should not require authorization",
    )
    complete_publish_entries = (
        ledger_after_publish_sample_complete.get("entries")
        if isinstance(ledger_after_publish_sample_complete.get("entries"), list)
        else []
    )
    complete_publish_entry = next(
        (entry for entry in complete_publish_entries if isinstance(entry, dict) and entry.get("stageId") == "publish_sample_verify"),
        {},
    )
    require(
        complete_publish_entry.get("status") == "completed",
        issues,
        "ledgerAfterPublishSampleComplete must mark publish_sample_verify completed",
    )
    batch_after_publish_entry = next(
        (entry for entry in complete_publish_entries if isinstance(entry, dict) and entry.get("stageId") == "batch_upload_publish"),
        {},
    )
    require(
        batch_after_publish_entry.get("status") == "pending",
        issues,
        "complete publish sample alone must not unlock batch upload before manifest schema gate completes",
    )
    require(
        browser_stage_packet_after_publish_sample_complete.get("stageId")
        == ledger_after_publish_sample_complete.get("nextStageId")
        == "manifest_schema_gate",
        issues,
        "complete publish sample packet must target ledger nextStageId manifest_schema_gate",
    )

    manifest_gate_partial = summary.get("manifestGatePartialSimulation")
    if not isinstance(manifest_gate_partial, dict):
        issues.append("manifestGatePartialSimulation summary must be an object")
        manifest_gate_partial = {}
    require(
        manifest_gate_partial.get("stageId")
        == simulated_manifest_gate_partial_result.get("stageId")
        == browser_stage_packet_after_publish_sample_complete.get("stageId"),
        issues,
        "manifestGatePartialSimulation.stageId must match manifest gate packet stageId",
    )
    require(
        manifest_gate_partial.get("status") == "partial",
        issues,
        "manifestGatePartialSimulation.status must be partial",
    )
    require(
        manifest_gate_partial.get("nextStageIdAfterApply") == ledger_after_manifest_gate_partial.get("nextStageId"),
        issues,
        "manifestGatePartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_manifest_gate_partial.get("nextStageId") in {"", None},
        issues,
        "partial manifest gate must not unlock batch upload",
    )
    partial_manifest_entries = (
        ledger_after_manifest_gate_partial.get("entries")
        if isinstance(ledger_after_manifest_gate_partial.get("entries"), list)
        else []
    )
    partial_manifest_entry = next(
        (entry for entry in partial_manifest_entries if isinstance(entry, dict) and entry.get("stageId") == "manifest_schema_gate"),
        {},
    )
    require(
        partial_manifest_entry.get("status") == "partial",
        issues,
        "ledgerAfterManifestGatePartial must keep manifest_schema_gate partial",
    )
    partial_manifest_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_manifest_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"batch_upload_publish", "forms_media_settings", "final_frontend_audit"}
    ]
    require(not partial_manifest_forbidden_ready, issues, "partial manifest gate must not expose batch, settings, or final audit")
    browser_stage_packet_after_manifest_gate_partial_recovery_validation = validate_recovery_packet_artifact(
        "manifest gate",
        browser_stage_packet_after_manifest_gate_partial_recovery_path,
        "manifest_schema_gate",
        manifest_gate_partial,
        issues,
        ledger_after_manifest_gate_partial_path,
    )

    manifest_gate_completion = summary.get("manifestGateCompletionSimulation")
    if not isinstance(manifest_gate_completion, dict):
        issues.append("manifestGateCompletionSimulation summary must be an object")
        manifest_gate_completion = {}
    require(
        manifest_gate_completion.get("stageId")
        == simulated_manifest_gate_complete_result.get("stageId")
        == browser_stage_packet_after_publish_sample_complete.get("stageId"),
        issues,
        "manifestGateCompletionSimulation.stageId must match manifest gate packet stageId",
    )
    require(
        manifest_gate_completion.get("status") == "completed",
        issues,
        "manifestGateCompletionSimulation.status must be completed",
    )
    require(
        manifest_gate_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "manifestGateCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        manifest_gate_completion.get("nextStageIdAfterApply") == "batch_upload_publish",
        issues,
        "complete manifest gate must unlock batch_upload_publish",
    )
    require(
        manifest_gate_completion.get("nextPacketStageId") == "batch_upload_publish",
        issues,
        "packet after complete manifest gate must target batch_upload_publish",
    )
    require(
        manifest_gate_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "batch_upload_publish packet should require authorization",
    )
    complete_manifest_entries = (
        ledger_after_manifest_gate_complete.get("entries")
        if isinstance(ledger_after_manifest_gate_complete.get("entries"), list)
        else []
    )
    complete_manifest_entry = next(
        (entry for entry in complete_manifest_entries if isinstance(entry, dict) and entry.get("stageId") == "manifest_schema_gate"),
        {},
    )
    require(
        complete_manifest_entry.get("status") == "completed",
        issues,
        "ledgerAfterManifestGateComplete must mark manifest_schema_gate completed",
    )
    batch_after_manifest_entry = next(
        (entry for entry in complete_manifest_entries if isinstance(entry, dict) and entry.get("stageId") == "batch_upload_publish"),
        {},
    )
    require(
        batch_after_manifest_entry.get("status") == "ready",
        issues,
        "complete manifest gate must mark batch_upload_publish ready",
    )
    require(
        browser_stage_packet_after_manifest_gate_complete.get("stageId")
        == ledger_after_manifest_gate_complete.get("nextStageId")
        == "batch_upload_publish",
        issues,
        "complete manifest gate packet must target ledger nextStageId batch_upload_publish",
    )

    batch_upload_partial = summary.get("batchUploadPartialSimulation")
    if not isinstance(batch_upload_partial, dict):
        issues.append("batchUploadPartialSimulation summary must be an object")
        batch_upload_partial = {}
    require(
        batch_upload_partial.get("stageId")
        == simulated_batch_upload_partial_result.get("stageId")
        == browser_stage_packet_after_manifest_gate_complete.get("stageId"),
        issues,
        "batchUploadPartialSimulation.stageId must match batch upload packet stageId",
    )
    require(
        batch_upload_partial.get("status") == "partial",
        issues,
        "batchUploadPartialSimulation.status must be partial",
    )
    require(
        batch_upload_partial.get("nextStageIdAfterApply") == ledger_after_batch_upload_partial.get("nextStageId"),
        issues,
        "batchUploadPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_batch_upload_partial.get("nextStageId") in {"", None},
        issues,
        "partial batch upload must not unlock forms/media/settings",
    )
    partial_batch_entries = (
        ledger_after_batch_upload_partial.get("entries")
        if isinstance(ledger_after_batch_upload_partial.get("entries"), list)
        else []
    )
    partial_batch_entry = next(
        (entry for entry in partial_batch_entries if isinstance(entry, dict) and entry.get("stageId") == "batch_upload_publish"),
        {},
    )
    require(
        partial_batch_entry.get("status") == "partial",
        issues,
        "ledgerAfterBatchUploadPartial must keep batch_upload_publish partial",
    )
    partial_batch_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_batch_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"forms_media_settings", "final_frontend_audit", "cleanup_probes"}
    ]
    require(not partial_batch_forbidden_ready, issues, "partial batch upload must not expose forms/media/settings, final audit, or cleanup")
    browser_stage_packet_after_batch_upload_partial_recovery_validation = validate_recovery_packet_artifact(
        "batch upload",
        browser_stage_packet_after_batch_upload_partial_recovery_path,
        "batch_upload_publish",
        batch_upload_partial,
        issues,
        ledger_after_batch_upload_partial_path,
    )

    batch_upload_completion = summary.get("batchUploadCompletionSimulation")
    if not isinstance(batch_upload_completion, dict):
        issues.append("batchUploadCompletionSimulation summary must be an object")
        batch_upload_completion = {}
    require(
        batch_upload_completion.get("stageId")
        == simulated_batch_upload_complete_result.get("stageId")
        == browser_stage_packet_after_manifest_gate_complete.get("stageId"),
        issues,
        "batchUploadCompletionSimulation.stageId must match batch upload packet stageId",
    )
    require(
        batch_upload_completion.get("status") == "completed",
        issues,
        "batchUploadCompletionSimulation.status must be completed",
    )
    require(
        batch_upload_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "batchUploadCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        batch_upload_completion.get("nextStageIdAfterApply") == "forms_media_settings",
        issues,
        "complete batch upload must unlock forms_media_settings",
    )
    require(
        batch_upload_completion.get("nextPacketStageId") == "forms_media_settings",
        issues,
        "packet after complete batch upload must target forms_media_settings",
    )
    require(
        batch_upload_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "forms_media_settings packet should require authorization",
    )
    complete_batch_entries = (
        ledger_after_batch_upload_complete.get("entries")
        if isinstance(ledger_after_batch_upload_complete.get("entries"), list)
        else []
    )
    complete_batch_entry = next(
        (entry for entry in complete_batch_entries if isinstance(entry, dict) and entry.get("stageId") == "batch_upload_publish"),
        {},
    )
    require(
        complete_batch_entry.get("status") == "completed",
        issues,
        "ledgerAfterBatchUploadComplete must mark batch_upload_publish completed",
    )
    forms_after_batch_entry = next(
        (entry for entry in complete_batch_entries if isinstance(entry, dict) and entry.get("stageId") == "forms_media_settings"),
        {},
    )
    require(
        forms_after_batch_entry.get("status") == "ready",
        issues,
        "complete batch upload must mark forms_media_settings ready",
    )
    final_after_batch_entry = next(
        (entry for entry in complete_batch_entries if isinstance(entry, dict) and entry.get("stageId") == "final_frontend_audit"),
        {},
    )
    require(
        final_after_batch_entry.get("status") == "pending",
        issues,
        "complete batch upload alone must not unlock final_frontend_audit before forms/media/settings completes",
    )
    require(
        browser_stage_packet_after_batch_upload_complete.get("stageId")
        == ledger_after_batch_upload_complete.get("nextStageId")
        == "forms_media_settings",
        issues,
        "complete batch upload packet must target ledger nextStageId forms_media_settings",
    )

    forms_media_settings_partial = summary.get("formsMediaSettingsPartialSimulation")
    if not isinstance(forms_media_settings_partial, dict):
        issues.append("formsMediaSettingsPartialSimulation summary must be an object")
        forms_media_settings_partial = {}
    require(
        forms_media_settings_partial.get("stageId")
        == simulated_forms_media_settings_partial_result.get("stageId")
        == browser_stage_packet_after_batch_upload_complete.get("stageId"),
        issues,
        "formsMediaSettingsPartialSimulation.stageId must match forms/media/settings packet stageId",
    )
    require(
        forms_media_settings_partial.get("status") == "partial",
        issues,
        "formsMediaSettingsPartialSimulation.status must be partial",
    )
    require(
        forms_media_settings_partial.get("nextStageIdAfterApply")
        == ledger_after_forms_media_settings_partial.get("nextStageId"),
        issues,
        "formsMediaSettingsPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_forms_media_settings_partial.get("nextStageId") in {"", None},
        issues,
        "partial forms/media/settings must not unlock final frontend audit",
    )
    partial_forms_entries = (
        ledger_after_forms_media_settings_partial.get("entries")
        if isinstance(ledger_after_forms_media_settings_partial.get("entries"), list)
        else []
    )
    partial_forms_entry = next(
        (entry for entry in partial_forms_entries if isinstance(entry, dict) and entry.get("stageId") == "forms_media_settings"),
        {},
    )
    require(
        partial_forms_entry.get("status") == "partial",
        issues,
        "ledgerAfterFormsMediaSettingsPartial must keep forms_media_settings partial",
    )
    partial_forms_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_forms_entries
        if isinstance(entry, dict)
        and entry.get("status") == "ready"
        and entry.get("stageId") in {"final_frontend_audit", "cleanup_probes"}
    ]
    require(not partial_forms_forbidden_ready, issues, "partial forms/media/settings must not expose final audit or cleanup")
    browser_stage_packet_after_forms_media_settings_partial_recovery_validation = validate_recovery_packet_artifact(
        "forms media settings",
        browser_stage_packet_after_forms_media_settings_partial_recovery_path,
        "forms_media_settings",
        forms_media_settings_partial,
        issues,
        ledger_after_forms_media_settings_partial_path,
    )

    forms_media_settings_completion = summary.get("formsMediaSettingsCompletionSimulation")
    if not isinstance(forms_media_settings_completion, dict):
        issues.append("formsMediaSettingsCompletionSimulation summary must be an object")
        forms_media_settings_completion = {}
    require(
        forms_media_settings_completion.get("stageId")
        == simulated_forms_media_settings_complete_result.get("stageId")
        == browser_stage_packet_after_batch_upload_complete.get("stageId"),
        issues,
        "formsMediaSettingsCompletionSimulation.stageId must match forms/media/settings packet stageId",
    )
    require(
        forms_media_settings_completion.get("status") == "completed",
        issues,
        "formsMediaSettingsCompletionSimulation.status must be completed",
    )
    require(
        forms_media_settings_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "formsMediaSettingsCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        forms_media_settings_completion.get("nextStageIdAfterApply") == "final_frontend_audit",
        issues,
        "complete forms/media/settings must unlock final_frontend_audit",
    )
    require(
        forms_media_settings_completion.get("nextPacketStageId") == "final_frontend_audit",
        issues,
        "packet after complete forms/media/settings must target final_frontend_audit",
    )
    require(
        forms_media_settings_completion.get("nextPacketAuthorizationRequired") is False,
        issues,
        "final_frontend_audit packet should not require mutation authorization",
    )
    complete_forms_entries = (
        ledger_after_forms_media_settings_complete.get("entries")
        if isinstance(ledger_after_forms_media_settings_complete.get("entries"), list)
        else []
    )
    complete_forms_entry = next(
        (entry for entry in complete_forms_entries if isinstance(entry, dict) and entry.get("stageId") == "forms_media_settings"),
        {},
    )
    require(
        complete_forms_entry.get("status") == "completed",
        issues,
        "ledgerAfterFormsMediaSettingsComplete must mark forms_media_settings completed",
    )
    final_after_forms_entry = next(
        (entry for entry in complete_forms_entries if isinstance(entry, dict) and entry.get("stageId") == "final_frontend_audit"),
        {},
    )
    require(
        final_after_forms_entry.get("status") == "ready",
        issues,
        "complete forms/media/settings must mark final_frontend_audit ready",
    )
    cleanup_after_forms_entry = next(
        (entry for entry in complete_forms_entries if isinstance(entry, dict) and entry.get("stageId") == "cleanup_probes"),
        {},
    )
    require(
        cleanup_after_forms_entry.get("status") == "pending",
        issues,
        "complete forms/media/settings alone must not unlock cleanup before final audit completes",
    )
    require(
        browser_stage_packet_after_forms_media_settings_complete.get("stageId")
        == ledger_after_forms_media_settings_complete.get("nextStageId")
        == "final_frontend_audit",
        issues,
        "complete forms/media/settings packet must target ledger nextStageId final_frontend_audit",
    )

    final_frontend_audit_partial = summary.get("finalFrontendAuditPartialSimulation")
    if not isinstance(final_frontend_audit_partial, dict):
        issues.append("finalFrontendAuditPartialSimulation summary must be an object")
        final_frontend_audit_partial = {}
    require(
        final_frontend_audit_partial.get("stageId")
        == simulated_final_frontend_audit_partial_result.get("stageId")
        == browser_stage_packet_after_forms_media_settings_complete.get("stageId"),
        issues,
        "finalFrontendAuditPartialSimulation.stageId must match final frontend audit packet stageId",
    )
    require(
        final_frontend_audit_partial.get("status") == "partial",
        issues,
        "finalFrontendAuditPartialSimulation.status must be partial",
    )
    require(
        final_frontend_audit_partial.get("nextStageIdAfterApply")
        == ledger_after_final_frontend_audit_partial.get("nextStageId"),
        issues,
        "finalFrontendAuditPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_final_frontend_audit_partial.get("nextStageId") in {"", None},
        issues,
        "partial final frontend audit must not unlock cleanup",
    )
    partial_final_entries = (
        ledger_after_final_frontend_audit_partial.get("entries")
        if isinstance(ledger_after_final_frontend_audit_partial.get("entries"), list)
        else []
    )
    partial_final_entry = next(
        (entry for entry in partial_final_entries if isinstance(entry, dict) and entry.get("stageId") == "final_frontend_audit"),
        {},
    )
    require(
        partial_final_entry.get("status") == "partial",
        issues,
        "ledgerAfterFinalFrontendAuditPartial must keep final_frontend_audit partial",
    )
    partial_final_forbidden_ready = [
        entry.get("stageId")
        for entry in partial_final_entries
        if isinstance(entry, dict) and entry.get("status") == "ready" and entry.get("stageId") == "cleanup_probes"
    ]
    require(not partial_final_forbidden_ready, issues, "partial final frontend audit must not expose cleanup")
    browser_stage_packet_after_final_frontend_audit_partial_recovery_validation = validate_recovery_packet_artifact(
        "final frontend audit",
        browser_stage_packet_after_final_frontend_audit_partial_recovery_path,
        "final_frontend_audit",
        final_frontend_audit_partial,
        issues,
        ledger_after_final_frontend_audit_partial_path,
    )

    final_frontend_audit_completion = summary.get("finalFrontendAuditCompletionSimulation")
    if not isinstance(final_frontend_audit_completion, dict):
        issues.append("finalFrontendAuditCompletionSimulation summary must be an object")
        final_frontend_audit_completion = {}
    require(
        final_frontend_audit_completion.get("stageId")
        == simulated_final_frontend_audit_complete_result.get("stageId")
        == browser_stage_packet_after_forms_media_settings_complete.get("stageId"),
        issues,
        "finalFrontendAuditCompletionSimulation.stageId must match final frontend audit packet stageId",
    )
    require(
        final_frontend_audit_completion.get("status") == "completed",
        issues,
        "finalFrontendAuditCompletionSimulation.status must be completed",
    )
    require(
        final_frontend_audit_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "finalFrontendAuditCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        final_frontend_audit_completion.get("nextStageIdAfterApply") == "cleanup_probes",
        issues,
        "complete final frontend audit must unlock cleanup_probes",
    )
    require(
        final_frontend_audit_completion.get("nextPacketStageId") == "cleanup_probes",
        issues,
        "packet after complete final frontend audit must target cleanup_probes",
    )
    require(
        final_frontend_audit_completion.get("nextPacketAuthorizationRequired") is True,
        issues,
        "cleanup_probes packet should require cleanup authorization",
    )
    complete_final_entries = (
        ledger_after_final_frontend_audit_complete.get("entries")
        if isinstance(ledger_after_final_frontend_audit_complete.get("entries"), list)
        else []
    )
    complete_final_entry = next(
        (entry for entry in complete_final_entries if isinstance(entry, dict) and entry.get("stageId") == "final_frontend_audit"),
        {},
    )
    require(
        complete_final_entry.get("status") == "completed",
        issues,
        "ledgerAfterFinalFrontendAuditComplete must mark final_frontend_audit completed",
    )
    cleanup_after_final_entry = next(
        (entry for entry in complete_final_entries if isinstance(entry, dict) and entry.get("stageId") == "cleanup_probes"),
        {},
    )
    require(
        cleanup_after_final_entry.get("status") == "ready",
        issues,
        "complete final frontend audit must mark cleanup_probes ready",
    )
    require(
        browser_stage_packet_after_final_frontend_audit_complete.get("stageId")
        == ledger_after_final_frontend_audit_complete.get("nextStageId")
        == "cleanup_probes",
        issues,
        "complete final frontend audit packet must target ledger nextStageId cleanup_probes",
    )

    cleanup_probes_partial = summary.get("cleanupProbesPartialSimulation")
    if not isinstance(cleanup_probes_partial, dict):
        issues.append("cleanupProbesPartialSimulation summary must be an object")
        cleanup_probes_partial = {}
    require(
        cleanup_probes_partial.get("stageId")
        == simulated_cleanup_probes_partial_result.get("stageId")
        == browser_stage_packet_after_final_frontend_audit_complete.get("stageId"),
        issues,
        "cleanupProbesPartialSimulation.stageId must match cleanup packet stageId",
    )
    require(
        cleanup_probes_partial.get("status") == "partial",
        issues,
        "cleanupProbesPartialSimulation.status must be partial",
    )
    require(
        cleanup_probes_partial.get("nextStageIdAfterApply") == ledger_after_cleanup_probes_partial.get("nextStageId"),
        issues,
        "cleanupProbesPartialSimulation.nextStageIdAfterApply mismatch",
    )
    require(
        ledger_after_cleanup_probes_partial.get("nextStageId") in {"", None},
        issues,
        "partial cleanup must not expose a next stage or claim completion",
    )
    partial_cleanup_entries = (
        ledger_after_cleanup_probes_partial.get("entries")
        if isinstance(ledger_after_cleanup_probes_partial.get("entries"), list)
        else []
    )
    partial_cleanup_entry = next(
        (entry for entry in partial_cleanup_entries if isinstance(entry, dict) and entry.get("stageId") == "cleanup_probes"),
        {},
    )
    require(
        partial_cleanup_entry.get("status") == "partial",
        issues,
        "ledgerAfterCleanupProbesPartial must keep cleanup_probes partial",
    )
    browser_stage_packet_after_cleanup_probes_partial_recovery_validation = validate_recovery_packet_artifact(
        "cleanup probes",
        browser_stage_packet_after_cleanup_probes_partial_recovery_path,
        "cleanup_probes",
        cleanup_probes_partial,
        issues,
        ledger_after_cleanup_probes_partial_path,
    )

    cleanup_probes_completion = summary.get("cleanupProbesCompletionSimulation")
    if not isinstance(cleanup_probes_completion, dict):
        issues.append("cleanupProbesCompletionSimulation summary must be an object")
        cleanup_probes_completion = {}
    require(
        cleanup_probes_completion.get("stageId")
        == simulated_cleanup_probes_complete_result.get("stageId")
        == browser_stage_packet_after_final_frontend_audit_complete.get("stageId"),
        issues,
        "cleanupProbesCompletionSimulation.stageId must match cleanup packet stageId",
    )
    require(
        cleanup_probes_completion.get("status") == "completed",
        issues,
        "cleanupProbesCompletionSimulation.status must be completed",
    )
    require(
        cleanup_probes_completion.get("completedFromRecoveryPacket") is True,
        issues,
        "cleanupProbesCompletionSimulation.completedFromRecoveryPacket must be true",
    )
    require(
        cleanup_probes_completion.get("nextStageIdAfterApply") in {"", None},
        issues,
        "complete cleanup must leave nextStageId empty",
    )
    complete_cleanup_entries = (
        ledger_after_cleanup_probes_complete.get("entries")
        if isinstance(ledger_after_cleanup_probes_complete.get("entries"), list)
        else []
    )
    complete_cleanup_entry = next(
        (entry for entry in complete_cleanup_entries if isinstance(entry, dict) and entry.get("stageId") == "cleanup_probes"),
        {},
    )
    require(
        complete_cleanup_entry.get("status") == "completed",
        issues,
        "ledgerAfterCleanupProbesComplete must mark cleanup_probes completed",
    )
    complete_cleanup_counts = (
        ledger_after_cleanup_probes_complete.get("stageCounts")
        if isinstance(ledger_after_cleanup_probes_complete.get("stageCounts"), dict)
        else {}
    )
    require(
        complete_cleanup_counts.get("completed") == complete_cleanup_counts.get("total") == len(complete_cleanup_entries),
        issues,
        "complete cleanup ledger must have all stages completed",
    )
    require(
        complete_cleanup_counts.get("ready") == 0
        and complete_cleanup_counts.get("pending") == 0
        and complete_cleanup_counts.get("blocked") == 0,
        issues,
        "complete cleanup ledger must not leave ready, pending, or blocked stages",
    )
    require(
        ledger_after_cleanup_probes_complete.get("nextStageId") in {"", None},
        issues,
        "complete cleanup ledger must not expose a next stage",
    )
    final_exhaustion = summary.get("finalLedgerExhaustion")
    if not isinstance(final_exhaustion, dict):
        issues.append("finalLedgerExhaustion summary must be an object")
        final_exhaustion = {}
    require(
        final_exhaustion.get("allStagesCompleted") is True,
        issues,
        "finalLedgerExhaustion.allStagesCompleted must be true",
    )
    require(
        final_exhaustion.get("nextStageId") in {"", None},
        issues,
        "finalLedgerExhaustion.nextStageId must be empty",
    )
    require(
        final_exhaustion.get("packetBuildRejected") is True,
        issues,
        "finalLedgerExhaustion.packetBuildRejected must be true",
    )
    require(
        isinstance(final_exhaustion.get("rejectionReason"), str)
        and "no nextStageId" in final_exhaustion.get("rejectionReason", ""),
        issues,
        "finalLedgerExhaustion.rejectionReason must explain no nextStageId",
    )

    return {
        "ok": not issues,
        "summaryPath": str(summary_path),
        "localOnly": summary.get("localOnly"),
        "remoteMutationsPerformed": summary.get("remoteMutationsPerformed"),
        "commandsSuppressed": summary.get("commandsSuppressed"),
        "fullE2E": full_validation,
        "handoffSafety": handoff_validation,
        "launchPlanSafety": launch_validation,
        "browserExecutionPlanSafety": browser_execution_validation,
        "browserExecutionLedgerSafety": browser_execution_ledger_validation,
        "browserStagePacketSafety": browser_stage_packet_validation,
        "simulatedStageResultSafety": simulated_stage_result_validation,
        "ledgerAfterFirstStageSafety": ledger_after_first_stage_validation,
        "browserStagePacketAfterFirstStageSafety": browser_stage_packet_after_first_stage_validation,
        "simulatedCreateSiteResultSafety": simulated_create_site_result_validation,
        "ledgerAfterCreateSiteSafety": ledger_after_create_site_validation,
        "browserStagePacketAfterCreateSiteSafety": browser_stage_packet_after_create_site_validation,
        "simulatedSetupResultSafety": simulated_setup_result_validation,
        "ledgerAfterSetupSafety": ledger_after_setup_validation,
        "browserStagePacketAfterSetupSafety": browser_stage_packet_after_setup_validation,
        "simulatedModuleCapturePartialResultSafety": simulated_module_capture_partial_result_validation,
        "ledgerAfterModuleCapturePartialSafety": ledger_after_module_capture_partial_validation,
        "capturePlanGateCoverageSafety": capture_plan_gate_coverage,
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
        "browserRunbookSummarySafety": browser_runbook_summary_safety,
        "manifestRehearsal": manifest_summary,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS full rehearsal summary.")
    parser.add_argument("rehearsal_summary_json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_rehearsal(Path(args.rehearsal_summary_json))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Full rehearsal validation passed.")
    else:
        print("Full rehearsal validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
