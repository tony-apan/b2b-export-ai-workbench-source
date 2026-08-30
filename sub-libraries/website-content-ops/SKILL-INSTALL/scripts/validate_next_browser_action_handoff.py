#!/usr/bin/env python3
"""Validate one AllinCMS next-browser-action handoff and its source files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES
from make_next_browser_action_handoff import package_action
from validate_browser_stage_authorization_package import AUTH_PLACEHOLDER, load_json, validate_package


REQUIRED_SOURCE_KEYS = ("authorizationPackage", "browserStagePacket", "preflight")


def load_handoff_sources(
    handoff: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    source_files = handoff.get("sourceFiles")
    if not isinstance(source_files, dict):
        return None, None, None, None, ["handoff.sourceFiles must be an object"]

    loaded: dict[str, dict[str, Any] | None] = {
        "authorizationPackage": None,
        "browserStagePacket": None,
        "preflight": None,
        "capturePlan": None,
    }
    for key in REQUIRED_SOURCE_KEYS:
        path = str(source_files.get(key, "") or "").strip()
        if not path:
            issues.append(f"handoff.sourceFiles.{key} is required")
            continue
        try:
            loaded[key] = load_json(Path(path), key)
        except ValueError as exc:
            issues.append(str(exc))

    capture_plan_path = str(source_files.get("capturePlan", "") or "").strip()
    if capture_plan_path:
        try:
            loaded["capturePlan"] = load_json(Path(capture_plan_path), "capturePlan")
        except ValueError as exc:
            issues.append(str(exc))

    if handoff.get("stageId") == "module_interface_capture" and not capture_plan_path:
        issues.append("module_interface_capture handoff.sourceFiles.capturePlan is required")

    return (
        loaded["authorizationPackage"],
        loaded["browserStagePacket"],
        loaded["preflight"],
        loaded["capturePlan"],
        issues,
    )


def validate_handoff(
    handoff: dict[str, Any],
    package: dict[str, Any] | None = None,
    packet: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    capture_plan: dict[str, Any] | None = None,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    issues: list[str] = []

    if handoff.get("kind") != "allincms_next_browser_action_handoff":
        issues.append("handoff.kind must be allincms_next_browser_action_handoff")
    if handoff.get("preparedOnly") is not True:
        issues.append("handoff.preparedOnly must be true")
    if handoff.get("isUserAuthorization") is not False:
        issues.append("handoff.isUserAuthorization must be false")
    if handoff.get("remoteMutationsPerformed") is not False:
        issues.append("handoff.remoteMutationsPerformed must be false")

    warning = str(handoff.get("warning", "") or "").strip()
    if not warning:
        issues.append("handoff.warning is required")
    else:
        warning_lower = warning.lower()
        if "preparation only" not in warning_lower:
            issues.append("handoff.warning must say it is preparation only")
        if "not user authorization" not in warning_lower:
            issues.append("handoff.warning must say it is not user authorization")

    validation = handoff.get("validation")
    if not isinstance(validation, dict) or validation.get("ok") is not True:
        issues.append("handoff.validation.ok must be true")

    if package is None or packet is None or preflight is None:
        loaded_package, loaded_packet, loaded_preflight, loaded_capture_plan, load_issues = load_handoff_sources(handoff)
        issues.extend(load_issues)
        package = package or loaded_package
        packet = packet or loaded_packet
        preflight = preflight or loaded_preflight
        capture_plan = capture_plan or loaded_capture_plan

    if package is None or packet is None or preflight is None:
        return {"ok": False, "issues": issues}

    package_issues = validate_package(
        package,
        packet,
        preflight,
        capture_plan,
        max_age_minutes=max_age_minutes,
        now=now,
    )
    issues.extend(f"source package: {issue}" for issue in package_issues)

    expected_action = package_action(package)
    comparisons = {
        "stageId": package.get("stageId"),
        "target": package.get("target"),
        "authorizationRequired": package.get("authorizationRequired"),
        "gateSupported": package.get("gateSupported"),
        "commandsSuppressed": package.get("commandsSuppressed", False),
        "suggestedAuthorizationText": package.get("suggestedAuthorizationText"),
        "authorizationRecordCommand": package.get("authorizationRecordCommand"),
        "preMutationGateCommand": package.get("preMutationGateCommand"),
        "requiredProof": package.get("requiredProof", []),
        "mustCapture": package.get("mustCapture", []),
        "stopAfter": package.get("stopAfter", ""),
    }
    for key, expected in comparisons.items():
        if handoff.get(key) != expected:
            issues.append(f"handoff.{key} must match authorization package")

    if handoff.get("action") != expected_action:
        issues.append("handoff.action must match authorization package action")

    authorization_command = handoff.get("authorizationRecordCommand")
    commands_suppressed = handoff.get("commandsSuppressed") is True
    if commands_suppressed:
        if authorization_command is not None:
            issues.append("handoff.authorizationRecordCommand must be empty when commandsSuppressed is true")
    else:
        if not isinstance(authorization_command, str) or not authorization_command.strip():
            issues.append("handoff.authorizationRecordCommand is required when commands are emitted")
        else:
            if "--authorization-source" not in authorization_command:
                issues.append("handoff.authorizationRecordCommand must include --authorization-source")
            if AUTH_PLACEHOLDER not in authorization_command:
                issues.append("handoff.authorizationRecordCommand must retain the current-user authorization placeholder")

    if handoff.get("gateSupported") is True:
        gate_command = handoff.get("preMutationGateCommand")
        if not isinstance(gate_command, str) or "check_pre_mutation_gate.py" not in gate_command:
            issues.append("handoff.preMutationGateCommand must call check_pre_mutation_gate.py when gateSupported is true")

    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one next-browser-action handoff and source files.")
    parser.add_argument("handoff_json")
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.handoff_json), "handoff")
        result = validate_handoff(handoff, max_age_minutes=args.max_age_minutes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Next browser action handoff validation passed.")
    else:
        print("Next browser action handoff validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
