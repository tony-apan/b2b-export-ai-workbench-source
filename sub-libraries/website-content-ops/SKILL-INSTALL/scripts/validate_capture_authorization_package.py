#!/usr/bin/env python3
"""Validate a prepared AllinCMS capture-plan authorization package."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SIMULATED_SITE_KEYS = {"simsite01", "codexsimulatedsite"}
AUTHORIZATION_SOURCE_PLACEHOLDER = "<paste current user authorization text here>"
SAFE_TARGET_RE = re.compile(r"^https://workspace\.laicms\.com/([a-z0-9]{6,16})/([a-z0-9-]+)$")


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


def matching_plan_stage(plan: dict[str, Any], package: dict[str, Any]) -> dict[str, Any] | None:
    stages = plan.get("stages")
    if not isinstance(stages, list):
        return None
    matches = [
        stage
        for stage in stages
        if isinstance(stage, dict)
        and stage.get("module") == package.get("module")
        and stage.get("action") == package.get("action")
    ]
    return matches[0] if len(matches) == 1 else None


def validate_package(package: dict[str, Any], plan: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if package.get("kind") != "allincms_capture_authorization_package":
        issues.append("package.kind must be allincms_capture_authorization_package")

    module = str(package.get("module", "")).strip()
    action = str(package.get("action", "")).strip()
    auth_action = str(package.get("authorizationAction", "")).strip()
    target = str(package.get("target", "")).strip()
    if not module:
        issues.append("package.module is required")
    if not action:
        issues.append("package.action is required")
    if not auth_action:
        issues.append("package.authorizationAction is required")
    if not target:
        issues.append("package.target is required")

    warning = str(package.get("warning", "")).strip()
    if "not user authorization" not in warning.lower():
        issues.append("package.warning must explicitly say it is not user authorization")

    if package.get("jsonReplayReady") is not False:
        issues.append("package.jsonReplayReady must be false")

    commands_suppressed = package.get("commandsSuppressed") is True
    gate_supported = package.get("gateSupported")
    auth_command = package.get("authorizationRecordCommand")
    gate_command = package.get("preMutationGateCommand")

    templated_target = "{" in target or "}" in target
    target_match = SAFE_TARGET_RE.match(target)
    site_key = target_match.group(1) if target_match else ""
    target_module = target_match.group(2) if target_match else ""
    simulated_target = site_key in SIMULATED_SITE_KEYS

    if commands_suppressed:
        if auth_command is not None or gate_command is not None:
            issues.append("suppressed package must not emit authorization or gate commands")
        if "{" not in target and not package.get("simulatedTarget"):
            issues.append("suppressed package should expose a templated target or simulatedTarget audit field")
    else:
        if templated_target:
            issues.append("non-suppressed package.target must be concrete, not templated")
        if simulated_target:
            issues.append("non-suppressed package.target must not use a simulated site key")
        if not target_match:
            issues.append("non-suppressed package.target must be a workspace module URL")
        elif target_module != module:
            issues.append("package.target module must match package.module")
        if not isinstance(auth_command, str) or not auth_command.strip():
            issues.append("authorizationRecordCommand is required when commands are not suppressed")
        elif f"--action {auth_action}" not in auth_command:
            issues.append("authorizationRecordCommand must use package.authorizationAction")
        if isinstance(auth_command, str):
            suggested_text = str(package.get("suggestedAuthorizationText", "")).strip()
            if AUTHORIZATION_SOURCE_PLACEHOLDER not in auth_command:
                issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
            if suggested_text and suggested_text in auth_command:
                issues.append("authorizationRecordCommand must not embed suggestedAuthorizationText as authorization source")
            if "授权 Codex" in auth_command:
                issues.append("authorizationRecordCommand must not embed helper-generated authorization wording")
        if gate_supported is True:
            if not isinstance(gate_command, str) or not gate_command.strip():
                issues.append("preMutationGateCommand is required when gateSupported is true")
            elif f"--action {auth_action}" not in gate_command:
                issues.append("preMutationGateCommand must use package.authorizationAction")
        elif gate_supported is False:
            if gate_command is not None:
                issues.append("preMutationGateCommand must be null when gateSupported is false")
        else:
            issues.append("package.gateSupported must be a boolean")

    if plan is not None:
        if plan.get("kind") != "allincms_module_capture_plan":
            issues.append("plan.kind must be allincms_module_capture_plan")
        stage = matching_plan_stage(plan, package)
        if stage is None:
            issues.append("package module/action must match exactly one capture-plan stage")
        else:
            if stage.get("authorizationAction") != auth_action:
                issues.append("package.authorizationAction must match capture-plan stage")
            if stage.get("target") != target and not commands_suppressed:
                issues.append("package.target must match capture-plan stage target")
            if package.get("mustCapture") != stage.get("mustCapture", []):
                issues.append("package.mustCapture must match capture-plan stage")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a capture-plan authorization package.")
    parser.add_argument("package_json")
    parser.add_argument("--plan-json", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        package = load_json(Path(args.package_json), "package")
        plan = load_json(Path(args.plan_json), "plan") if args.plan_json else None
        issues = validate_package(package, plan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = {"ok": not issues, "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Capture authorization package validation passed.")
    else:
        print("Capture authorization package validation failed:")
        for issue in issues:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
