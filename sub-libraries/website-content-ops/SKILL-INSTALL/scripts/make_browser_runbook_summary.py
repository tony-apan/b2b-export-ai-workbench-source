#!/usr/bin/env python3
"""Summarize a full rehearsal into the next real-browser runbook step."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from validate_full_rehearsal import validate_rehearsal


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue_list(validation: dict[str, Any]) -> list[str]:
    issues = validation.get("issues")
    return [str(issue) for issue in issues] if isinstance(issues, list) else []


def artifact(summary: dict[str, Any], key: str) -> str:
    artifacts = summary.get("artifacts")
    if isinstance(artifacts, dict):
        value = artifacts.get(key)
        if isinstance(value, str):
            return value
    value = summary.get(key)
    return value if isinstance(value, str) else ""


def load_artifact_object(path: str) -> dict[str, Any]:
    if not path:
        return {}
    try:
        return load_json(Path(path))
    except ValueError:
        return {}


def stage_result_output_path(evidence_bundle: str) -> str:
    return str(Path(evidence_bundle) / "stage-result.json") if evidence_bundle else ""


def ledger_expected_stage_result_path(packet_path: str, ledger_apply_command: str) -> str:
    if ledger_apply_command:
        try:
            parts = shlex.split(ledger_apply_command)
        except ValueError:
            parts = []
        for index, part in enumerate(parts):
            if part == "--result-json" and index + 1 < len(parts):
                return parts[index + 1]
    if packet_path:
        path = Path(packet_path)
        return str(path.with_name(path.stem + "-stage-result.json"))
    return "{stageResultPath}"


def authorization_preparation(stage_id: str, authorization_required: object, packet_path: str) -> dict[str, Any]:
    if authorization_required is not True:
        return {
            "required": False,
            "gateSupported": False,
            "commandTemplate": "",
            "stageSpecificInputs": [],
            "note": (
                "This stage is read-only or verification-only; it does not require mutation authorization. "
                "This is not action-time user authorization."
            ),
        }

    base = (
        "python3 skills/allincms-bulk-content-upload/scripts/prepare_browser_stage_authorization.py "
        f"{packet_path or '{packetPath}'} "
        "--preflight {preflightEvidencePath} "
        "--authorization-output {authorizationRecordPath}"
    )
    stage_inputs: list[str] = []
    if stage_id == "module_interface_capture":
        base += " --capture-plan {moduleCapturePlanPath} --coverage {moduleCaptureCoveragePath}"
        stage_inputs.extend(["moduleCapturePlanPath", "moduleCaptureCoveragePath"])
    elif stage_id == "theme_page_route_launch":
        base += (
            " --launch-action {launchAction} "
            "--launch-target {exactBackendTargetUrl} "
            "--launch-target-identifier {themePageOrRouteIdentifier}"
        )
        stage_inputs.extend(["launchAction", "exactBackendTargetUrl", "themePageOrRouteIdentifier"])
    elif stage_id in {"content_probe_create", "save_request_capture", "publish_sample_verify", "cleanup_probes"}:
        base += (
            " --content-type {postsOrProductsOrForms} "
            "--content-target {exactBackendTargetUrl} "
            "--content-target-identifier {probeIdentifier}"
        )
        stage_inputs.extend(["postsOrProductsOrForms", "exactBackendTargetUrl", "probeIdentifier"])
    elif stage_id == "batch_upload_publish":
        base += (
            " --content-type {postsOrProducts} "
            "--content-target {exactBackendTargetUrl} "
            "--content-target-identifier {manifestBatchIdentifier}"
        )
        stage_inputs.extend(["postsOrProducts", "exactBackendTargetUrl", "manifestBatchIdentifier"])
    elif stage_id == "forms_media_settings":
        base += (
            " --settings-action {settingsAction} "
            "--settings-target {exactBackendTargetUrl} "
            "--settings-target-identifier {settingsOrMediaIdentifier}"
        )
        stage_inputs.extend(["settingsAction", "exactBackendTargetUrl", "settingsOrMediaIdentifier"])
    elif stage_id != "create_site_submit":
        return {
            "required": True,
            "gateSupported": False,
            "commandTemplate": "",
            "stageSpecificInputs": [],
            "note": (
                "No local authorization recipe exists for this stage; extend the helper before mutating LAICMS. "
                "This is not action-time user authorization."
            ),
        }

    return {
        "required": True,
        "gateSupported": True,
        "commandTemplate": base,
        "stageSpecificInputs": stage_inputs,
        "note": "This prepares a local authorization package only. It is not action-time user authorization.",
    }


def build_runbook_summary(summary_path: Path) -> dict[str, Any]:
    summary = load_json(summary_path)
    validation = validate_rehearsal(summary_path)
    packet_path = artifact(summary, "browserStagePacket")
    packet = load_artifact_object(packet_path)
    if not isinstance(packet, dict):
        packet = {}
    if not packet:
        packet = summary.get("browserStagePacket")
        if not isinstance(packet, dict):
            packet = {}
    handoff = summary.get("selectedStage")
    if not isinstance(handoff, dict):
        handoff = {}
    capture = summary.get("capturePlanGateCoverage")
    if not isinstance(capture, dict):
        capture = {}
    ledger = summary.get("browserExecutionLedger")
    if not isinstance(ledger, dict):
        ledger = {}

    stage_id = str(packet.get("stageId", ""))
    authorization_required = packet.get("authorizationRequired")
    evidence_bundle = artifact(summary, "browserStageEvidenceBundle")
    evidence_manifest = artifact(summary, "browserStageEvidenceManifest")
    next_browser_action_handoff = artifact(summary, "nextBrowserActionHandoff")
    module_capture_authorization_package = artifact(summary, "browserStageModuleCaptureAuthorizationPackage")
    evidence_manifest_obj = load_artifact_object(evidence_manifest)
    required_proof = [item for item in packet.get("requiredProof", []) if isinstance(item, str)]
    stage_result_template = str(evidence_manifest_obj.get("stageResultTemplate", "") or "")
    if not stage_result_template and evidence_bundle:
        stage_result_template = str(Path(evidence_bundle) / "stage-result-template.json")
    bundle_stage_result_output = stage_result_output_path(evidence_bundle)
    ledger_update = packet.get("ledgerUpdate") if isinstance(packet.get("ledgerUpdate"), dict) else {}
    ledger_apply_command = str(ledger_update.get("commandTemplate", "") or "")
    ledger_stage_result_output = ledger_expected_stage_result_path(packet_path, ledger_apply_command)
    stage_result_command = str(evidence_manifest_obj.get("applyCommandTemplate", "") or "")
    commands_suppressed = summary.get("commandsSuppressed") is True
    local_only = summary.get("localOnly") is True
    remote_mutations = summary.get("remoteMutationsPerformed") is True
    next_mode = "blocked"
    if validation.get("ok"):
        next_mode = "prepare_real_browser_stage"
    if commands_suppressed and authorization_required is True:
        next_mode = "refresh_real_evidence_then_authorize"

    real_evidence_required = [
        "fresh /sites list and create-dialog open/close proof",
        "real existing site-key evidence or verified empty site list",
        "redacted browser scan artifact, not raw account/menu text",
        "action-time user authorization before any mutation stage",
    ]
    if stage_id == "create_site_submit":
        real_evidence_required.append("create-site preflight regenerated from the current browser session")
    elif stage_id:
        real_evidence_required.append("stage packet rebuilt from the current real-site ledger before execution")

    return {
        "kind": "allincms_browser_runbook_summary",
        "sourceSummary": str(summary_path),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceRehearsal": {
            "valid": validation.get("ok") is True,
            "localOnly": local_only,
            "remoteMutationsPerformed": remote_mutations,
            "commandsSuppressed": commands_suppressed,
            "issues": issue_list(validation),
        },
        "nextRealBrowserStep": {
            "mode": next_mode,
            "stageId": stage_id,
            "authorizationRequired": authorization_required,
            "targetTemplate": packet.get("targetTemplate", ""),
            "commandsSuppressed": commands_suppressed,
            "evidenceBundle": evidence_bundle,
            "evidenceManifest": evidence_manifest,
            "reason": (
                "local-only rehearsal targets must be refreshed with real browser evidence before mutation"
                if commands_suppressed
                else "rehearsal summary is valid and exposes the next packet"
            ),
        },
        "requiredRealEvidenceBeforeMutation": real_evidence_required,
        "requiredLocalArtifacts": {
            "browserExecutionLedger": artifact(summary, "browserExecutionLedger"),
            "nextBrowserStagePacket": artifact(summary, "browserStagePacket"),
            "nextBrowserStageEvidenceBundle": evidence_bundle,
            "nextBrowserStageEvidenceManifest": evidence_manifest,
            "nextBrowserActionHandoff": next_browser_action_handoff,
            "browserStageModuleCaptureAuthorizationPackage": module_capture_authorization_package,
            "captureHandoff": artifact(summary, "handoff"),
            "capturePlanGateCoverage": artifact(summary, "capturePlanGateCoverage"),
        },
        "operatorHandoff": {
            "status": "ready" if validation.get("ok") else "blocked",
            "notAuthorization": True,
            "stageId": stage_id,
            "packetPath": packet_path,
            "ledgerPath": artifact(summary, "browserExecutionLedger"),
            "evidenceBundleDir": evidence_bundle,
            "evidenceManifestPath": evidence_manifest,
            "nextBrowserActionHandoffPath": next_browser_action_handoff,
            "browserStageModuleCaptureAuthorizationPackagePath": module_capture_authorization_package,
            "stageResultTemplatePath": stage_result_template,
            "bundleStageResultDraftPath": bundle_stage_result_output,
            "ledgerExpectedStageResultPath": ledger_stage_result_output,
            "stageResultOutputPath": ledger_stage_result_output,
            "stageResultCommandTemplate": stage_result_command,
            "ledgerApplyCommand": ledger_apply_command,
            "authorizationPreparation": authorization_preparation(stage_id, authorization_required, packet_path),
            "requiredProof": required_proof,
            "stopAfter": packet.get("stopAfter", ""),
            "nextActionMode": next_mode,
            "warning": (
                "This handoff is local scaffolding and a checklist only. It is not user authorization, "
                "does not prove remote persistence, and must be refreshed from real browser evidence before mutation. "
                "Copy or write the final stage result to ledgerExpectedStageResultPath before using ledgerApplyCommand."
            ),
        },
        "selectedCaptureStage": {
            "group": handoff.get("group", ""),
            "module": handoff.get("module", ""),
            "action": handoff.get("action", ""),
            "authorizationAction": handoff.get("authorizationAction", ""),
        },
        "coverage": {
            "captureStageCount": capture.get("stageCount", 0),
            "coveredActions": capture.get("coveredActions", []),
            "ungatedAllowedActions": capture.get("ungatedAllowedActions", []),
            "initialLedgerNextStageId": ledger.get("nextStageId", ""),
            "initialLedgerStageCounts": ledger.get("stageCounts", {}),
        },
        "stopConditions": [
            "do not run suppressed command templates against LAICMS",
            "do not treat rehearsal artifacts as action-time user authorization",
            "do not skip from a partial stage to a later stage; recover the same stage first",
            "do not store concrete site keys, account text, cookies, tokens, or business copy in the skill",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the next real-browser runbook summary from a rehearsal summary.")
    parser.add_argument("rehearsal_summary_json")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = build_runbook_summary(Path(args.rehearsal_summary_json))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), summary)
    if args.json or not args.output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
