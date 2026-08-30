#!/usr/bin/env python3
"""Validate AllinCMS next-capture handoff safety."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SIMULATED_SITE_KEYS = ("simsite01", "codexsimulatedsite")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"handoff JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid handoff JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("handoff JSON root must be an object")
    return data


def contains_simulated_target(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=False)
    if any(site_key in text for site_key in SIMULATED_SITE_KEYS):
        return True
    return "workspace.laicms.com/" in text and "{realSiteKey}" not in text


def validate_handoff(handoff: dict[str, Any], allow_command_output: bool = False) -> dict[str, Any]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_next_capture_handoff":
        issues.append("kind must be allincms_next_capture_handoff")
    package = handoff.get("authorizationPackage")
    if not isinstance(package, dict):
        issues.append("authorizationPackage must be an object")
        package = {}

    simulation_only = handoff.get("simulationOnly") is True
    commands_suppressed = handoff.get("commandsSuppressed") is True
    if simulation_only and not allow_command_output:
        if not commands_suppressed:
            issues.append("simulation handoff must suppress commands by default")
        for key in ("authorizationRecordCommand", "preMutationGateCommand"):
            if package.get(key) is not None:
                issues.append(f"{key} must be null for default simulation handoff")
        if package.get("gateSupported") is not False:
            issues.append("gateSupported must be false when commands are suppressed")
        target = package.get("target")
        if not isinstance(target, str) or "{realSiteKey}" not in target:
            issues.append("simulation handoff target must use {realSiteKey} template")
        auth_text = package.get("suggestedAuthorizationText")
        if not isinstance(auth_text, str) or "{realSiteKey}" not in auth_text:
            issues.append("simulation handoff authorization text must use {realSiteKey} template")
        if contains_simulated_target(auth_text):
            issues.append("simulation handoff authorization text must not contain simulated site key")
        selected_stage = handoff.get("selectedStage")
        if isinstance(selected_stage, dict):
            if "{realSiteKey}" not in str(selected_stage.get("target", "")):
                issues.append("selectedStage.target must use {realSiteKey} template")
            if not contains_simulated_target(selected_stage.get("simulatedTarget")):
                issues.append("selectedStage.simulatedTarget must preserve the simulated target for audit")
        if not contains_simulated_target(package.get("simulatedTarget")):
            issues.append("authorizationPackage.simulatedTarget must preserve the simulated target for audit")
    if not simulation_only and commands_suppressed:
        issues.append("non-simulation handoff should not report commandsSuppressed")

    return {
        "ok": not issues,
        "simulationOnly": simulation_only,
        "commandsSuppressed": commands_suppressed,
        "allowCommandOutput": allow_command_output,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS capture handoff safety.")
    parser.add_argument("handoff_json")
    parser.add_argument("--allow-command-output", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_handoff(load_json(Path(args.handoff_json)), args.allow_command_output)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Capture handoff safety validation passed.")
    else:
        print("Capture handoff safety validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
