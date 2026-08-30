#!/usr/bin/env python3
"""Validate a standalone AllinCMS browser runbook summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_full_rehearsal import validate_rehearsal


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def same_path(recorded: object, expected: str | Path) -> bool:
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    return Path(recorded).resolve() == Path(expected).resolve()


def validate_runbook(runbook: dict[str, Any], runbook_path: Path | None = None) -> dict[str, Any]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_browser_runbook_summary":
        issues.append("runbook.kind must be allincms_browser_runbook_summary")
    if runbook.get("localOnly") is not True:
        issues.append("runbook.localOnly must be true")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("runbook.remoteMutationsPerformed must be false")

    source_summary = str(runbook.get("sourceSummary", "") or "").strip()
    if not source_summary:
        issues.append("runbook.sourceSummary is required")
        return {"ok": False, "issues": issues}

    source_path = Path(source_summary)
    source_validation = validate_rehearsal(source_path)
    if not source_validation.get("ok"):
        issues.extend(f"source rehearsal: {issue}" for issue in source_validation.get("issues", []))

    try:
        source = load_json(source_path, "source rehearsal summary")
    except ValueError as exc:
        source = {}
        issues.append(str(exc))

    artifacts = source.get("artifacts") if isinstance(source.get("artifacts"), dict) else {}
    source_packet_path = str(artifacts.get("browserStagePacket", "") or "")
    source_ledger_path = str(artifacts.get("browserExecutionLedger", "") or "")
    source_bundle_path = str(artifacts.get("browserStageEvidenceBundle", "") or "")
    source_manifest_path = str(artifacts.get("browserStageEvidenceManifest", "") or "")
    source_next_handoff_path = str(artifacts.get("nextBrowserActionHandoff", "") or "")
    source_auth_package_path = str(artifacts.get("browserStageModuleCaptureAuthorizationPackage", "") or "")

    source_packet = {}
    if source_packet_path:
        try:
            source_packet = load_json(Path(source_packet_path), "source browser stage packet")
        except ValueError as exc:
            issues.append(str(exc))

    source_rehearsal = runbook.get("sourceRehearsal") if isinstance(runbook.get("sourceRehearsal"), dict) else {}
    next_step = runbook.get("nextRealBrowserStep") if isinstance(runbook.get("nextRealBrowserStep"), dict) else {}
    required_artifacts = (
        runbook.get("requiredLocalArtifacts") if isinstance(runbook.get("requiredLocalArtifacts"), dict) else {}
    )
    operator_handoff = runbook.get("operatorHandoff") if isinstance(runbook.get("operatorHandoff"), dict) else {}
    auth_prep = (
        operator_handoff.get("authorizationPreparation")
        if isinstance(operator_handoff.get("authorizationPreparation"), dict)
        else {}
    )

    if source_rehearsal.get("valid") is not True:
        issues.append("runbook.sourceRehearsal.valid must be true")
    if source_rehearsal.get("localOnly") is not True:
        issues.append("runbook.sourceRehearsal.localOnly must be true")
    if source_rehearsal.get("remoteMutationsPerformed") is not False:
        issues.append("runbook.sourceRehearsal.remoteMutationsPerformed must be false")
    if source_rehearsal.get("commandsSuppressed") != source.get("commandsSuppressed"):
        issues.append("runbook.sourceRehearsal.commandsSuppressed must match source summary")

    if next_step.get("stageId") != source_packet.get("stageId"):
        issues.append("runbook.nextRealBrowserStep.stageId must match source packet")
    if next_step.get("authorizationRequired") != source_packet.get("authorizationRequired"):
        issues.append("runbook.nextRealBrowserStep.authorizationRequired must match source packet")
    if next_step.get("commandsSuppressed") != source.get("commandsSuppressed"):
        issues.append("runbook.nextRealBrowserStep.commandsSuppressed must match source summary")
    if not same_path(next_step.get("evidenceBundle"), source_bundle_path):
        issues.append("runbook.nextRealBrowserStep.evidenceBundle must match source artifact")
    if not same_path(next_step.get("evidenceManifest"), source_manifest_path):
        issues.append("runbook.nextRealBrowserStep.evidenceManifest must match source artifact")

    expected_paths = {
        "browserExecutionLedger": source_ledger_path,
        "nextBrowserStagePacket": source_packet_path,
        "nextBrowserStageEvidenceBundle": source_bundle_path,
        "nextBrowserStageEvidenceManifest": source_manifest_path,
        "nextBrowserActionHandoff": source_next_handoff_path,
        "browserStageModuleCaptureAuthorizationPackage": source_auth_package_path,
        "captureHandoff": str(artifacts.get("handoff", "") or ""),
        "capturePlanGateCoverage": str(artifacts.get("capturePlanGateCoverage", "") or ""),
    }
    for key, expected in expected_paths.items():
        if expected and not same_path(required_artifacts.get(key), expected):
            issues.append(f"runbook.requiredLocalArtifacts.{key} must match source artifact")

    if operator_handoff.get("status") != "ready":
        issues.append("runbook.operatorHandoff.status must be ready")
    if operator_handoff.get("notAuthorization") is not True:
        issues.append("runbook.operatorHandoff.notAuthorization must be true")
    operator_paths = {
        "packetPath": source_packet_path,
        "ledgerPath": source_ledger_path,
        "evidenceBundleDir": source_bundle_path,
        "evidenceManifestPath": source_manifest_path,
        "nextBrowserActionHandoffPath": source_next_handoff_path,
        "browserStageModuleCaptureAuthorizationPackagePath": source_auth_package_path,
    }
    for key, expected in operator_paths.items():
        if expected and not same_path(operator_handoff.get(key), expected):
            issues.append(f"runbook.operatorHandoff.{key} must match source artifact")
    if operator_handoff.get("stageId") != source_packet.get("stageId"):
        issues.append("runbook.operatorHandoff.stageId must match source packet")
    if operator_handoff.get("requiredProof") != source_packet.get("requiredProof"):
        issues.append("runbook.operatorHandoff.requiredProof must match source packet")
    if operator_handoff.get("stopAfter") != source_packet.get("stopAfter"):
        issues.append("runbook.operatorHandoff.stopAfter must match source packet")
    if operator_handoff.get("nextActionMode") != next_step.get("mode"):
        issues.append("runbook.operatorHandoff.nextActionMode must match nextRealBrowserStep.mode")
    if "not user authorization" not in str(operator_handoff.get("warning", "")):
        issues.append("runbook.operatorHandoff.warning must say it is not user authorization")
    if auth_prep.get("required") != (source_packet.get("authorizationRequired") is True):
        issues.append("runbook.operatorHandoff.authorizationPreparation.required must match source packet")
    if "not action-time user authorization" not in str(auth_prep.get("note", "")):
        issues.append("runbook.operatorHandoff.authorizationPreparation.note must warn about authorization")

    stop_conditions = runbook.get("stopConditions")
    stop_text = "\n".join(str(item) for item in stop_conditions) if isinstance(stop_conditions, list) else ""
    if "suppressed command" not in stop_text:
        issues.append("runbook.stopConditions must warn about suppressed commands")
    if "authorization" not in stop_text:
        issues.append("runbook.stopConditions must warn about authorization")

    result = {
        "ok": not issues,
        "issues": issues,
        "sourceSummary": source_summary,
        "runbookPath": str(runbook_path) if runbook_path else "",
        "nextStageId": next_step.get("stageId", ""),
        "nextBrowserActionHandoff": required_artifacts.get("nextBrowserActionHandoff", ""),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a standalone AllinCMS browser runbook summary.")
    parser.add_argument("runbook_json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        runbook_path = Path(args.runbook_json)
        result = validate_runbook(load_json(runbook_path, "runbook"), runbook_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Browser runbook summary validation passed.")
    else:
        print("Browser runbook summary validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
