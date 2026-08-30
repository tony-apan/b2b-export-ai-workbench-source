#!/usr/bin/env python3
"""Validate a prepared AllinCMS browser-stage authorization package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from build_browser_stage_packet import validate_browser_stage_packet
from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES, validate_freshness
from prepare_capture_authorization import redact_simulated_target
from prepare_capture_authorization import select_stage as select_capture_stage
from validate_run_evidence import validate as validate_run_evidence

AUTH_PLACEHOLDER = "<paste current user authorization text here>"


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


def validate_package(
    package: dict[str, Any],
    packet: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    capture_plan: dict[str, Any] | None = None,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    issues: list[str] = []
    if package.get("kind") != "allincms_browser_stage_authorization_package":
        issues.append("package.kind must be allincms_browser_stage_authorization_package")

    stage_id = str(package.get("stageId", "")).strip()
    if not stage_id:
        issues.append("package.stageId is required")
    if package.get("authorizationRequired") is not True:
        issues.append("package.authorizationRequired must be true")
    warning = str(package.get("warning", "")).strip()
    if not warning:
        issues.append("package.warning is required and must say it is not user authorization")
    elif "not user authorization" not in warning.lower():
        issues.append("package.warning must explicitly say it is not user authorization")

    commands_suppressed = package.get("commandsSuppressed") is True
    authorization_command = str(package.get("authorizationRecordCommand", "") or "").strip()
    target = str(package.get("target", "")).strip()
    if commands_suppressed:
        if package.get("authorizationRecordCommand") is not None:
            issues.append("authorizationRecordCommand must be empty when commandsSuppressed is true")
    else:
        if AUTH_PLACEHOLDER not in authorization_command:
            issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
        if "--authorization-source" not in authorization_command:
            issues.append("authorizationRecordCommand must include --authorization-source")
        if target and target not in authorization_command:
            issues.append("authorizationRecordCommand must include package.target")

    gate_supported = package.get("gateSupported")
    gate_command = package.get("preMutationGateCommand")
    if gate_supported is True:
        if not isinstance(gate_command, str) or not gate_command.strip():
            issues.append("preMutationGateCommand is required when gateSupported is true")
        elif "check_pre_mutation_gate.py" not in gate_command:
            issues.append("preMutationGateCommand must call check_pre_mutation_gate.py")
    elif gate_supported is False:
        if gate_command:
            issues.append("preMutationGateCommand must be empty when gateSupported is false")
    else:
        issues.append("package.gateSupported must be a boolean")

    if packet is not None:
        packet_validation = validate_browser_stage_packet(packet)
        if not packet_validation["ok"]:
            issues.extend(f"packet: {issue}" for issue in packet_validation["issues"])
        packet_stage = str(packet.get("stageId", "")).strip()
        if stage_id != packet_stage:
            issues.append("package.stageId must match packet.stageId")
        if package.get("authorizationRequired") != packet.get("authorizationRequired"):
            issues.append("package.authorizationRequired must match packet.authorizationRequired")
        if package.get("remoteMutationExpectation") != packet.get("remoteMutationExpectation"):
            issues.append("package.remoteMutationExpectation must match packet.remoteMutationExpectation")
        packet_target = str(packet.get("targetTemplate", "")).strip()
        if target and packet_target and target != packet_target and "{" not in packet_target:
            issues.append("package.target must match packet.targetTemplate for concrete targets")

    if preflight is not None:
        preflight_errors = validate_run_evidence(preflight)
        issues.extend(f"preflight: {error}" for error in preflight_errors)
        if commands_suppressed is False and gate_supported is True:
            placeholder_authorization = {
                "generatedAt": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds"),
            }
            freshness_errors = validate_freshness(preflight, placeholder_authorization, max_age_minutes, now)
            issues.extend(
                "preflight freshness: " + error
                for error in freshness_errors
                if error.startswith("preflight:")
            )

    if stage_id == "create_site_submit":
        if target != "https://workspace.laicms.com/sites":
            issues.append("create_site_submit package.target must be https://workspace.laicms.com/sites")
        if package.get("gateSupported") is not True:
            issues.append("create_site_submit must have gateSupported=true")
        if "--action create_site" not in authorization_command:
            issues.append("create_site_submit authorizationRecordCommand must use --action create_site")
        if "--fields-or-files name,description" not in authorization_command:
            issues.append("create_site_submit authorizationRecordCommand must include name,description fields")
        if isinstance(gate_command, str):
            if "--action create_site" not in gate_command:
                issues.append("create_site_submit preMutationGateCommand must use --action create_site")
            if preflight is not None and str(package.get("target", "")) not in authorization_command:
                issues.append("create_site_submit command must keep /sites target")
        if preflight is not None:
            site_creation = preflight.get("siteCreation")
            if not isinstance(site_creation, dict) or site_creation.get("status") != "create_preflight_verified":
                issues.append("create_site_submit preflight must have siteCreation.status=create_preflight_verified")

    if stage_id == "module_interface_capture":
        capture_stage = package.get("captureStage")
        if not isinstance(capture_stage, dict):
            issues.append("module_interface_capture package.captureStage is required")
        else:
            module = str(capture_stage.get("module", "")).strip()
            action = str(capture_stage.get("action", "")).strip()
            authorization_action = str(capture_stage.get("authorizationAction", "")).strip()
            if not module or not action or not authorization_action:
                issues.append("module_interface_capture captureStage must include module, action, and authorizationAction")
            if target and module and f"/{module}" not in target:
                issues.append("module_interface_capture package.target must include captureStage.module")
            if not commands_suppressed and authorization_action and f"--action {authorization_action}" not in authorization_command:
                issues.append("module_interface_capture authorizationRecordCommand must use captureStage.authorizationAction")
            if isinstance(gate_command, str) and authorization_action and f"--action {authorization_action}" not in gate_command:
                issues.append("module_interface_capture preMutationGateCommand must use captureStage.authorizationAction")
            if capture_plan is not None and module and action:
                if capture_plan.get("kind") != "allincms_module_capture_plan":
                    issues.append("capture_plan.kind must be allincms_module_capture_plan")
                else:
                    try:
                        plan_stage = select_capture_stage(capture_plan, module, action)
                    except ValueError as exc:
                        issues.append(f"captureStage must match capture plan: {exc}")
                    else:
                        expected_target = redact_simulated_target(str(plan_stage.get("target", "")))
                        if package.get("target") not in {plan_stage.get("target"), expected_target}:
                            issues.append("module_interface_capture package.target must match capture-plan stage target")
                        if authorization_action != plan_stage.get("authorizationAction"):
                            issues.append("module_interface_capture captureStage.authorizationAction must match capture-plan stage")
                        if package.get("mustCapture") != plan_stage.get("mustCapture", []):
                            issues.append("module_interface_capture package.mustCapture must match capture-plan stage")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a browser-stage authorization package.")
    parser.add_argument("package_json")
    parser.add_argument("--packet-json", default="")
    parser.add_argument("--preflight", default="")
    parser.add_argument("--capture-plan", default="")
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        package = load_json(Path(args.package_json), "package")
        packet = load_json(Path(args.packet_json), "packet") if args.packet_json else None
        preflight = load_json(Path(args.preflight), "preflight") if args.preflight else None
        capture_plan = load_json(Path(args.capture_plan), "capture plan") if args.capture_plan else None
        issues = validate_package(package, packet, preflight, capture_plan, args.max_age_minutes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = {"ok": not issues, "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Browser stage authorization package validation passed.")
    else:
        print("Browser stage authorization package validation failed:")
        for issue in issues:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
