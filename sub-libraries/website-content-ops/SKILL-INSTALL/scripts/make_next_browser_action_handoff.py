#!/usr/bin/env python3
"""Build a validated handoff for one next real-browser action."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES
from validate_browser_stage_authorization_package import load_json, validate_package


def package_action(package: dict[str, Any]) -> dict[str, str]:
    capture_stage = package.get("captureStage")
    if isinstance(capture_stage, dict):
        return {
            "module": str(capture_stage.get("module", "")),
            "action": str(capture_stage.get("action", "")),
            "authorizationAction": str(capture_stage.get("authorizationAction", "")),
        }
    launch_action = package.get("launchAction")
    if isinstance(launch_action, dict):
        return {
            "module": str(launch_action.get("module", "")),
            "action": str(launch_action.get("action", "")),
            "authorizationAction": str(launch_action.get("action", "")),
        }
    content_stage = package.get("contentStage")
    if isinstance(content_stage, dict):
        return {
            "module": str(content_stage.get("contentType", "")),
            "action": str(content_stage.get("stageId", "")),
            "authorizationAction": str(content_stage.get("authorizationAction", "")),
        }
    settings_action = package.get("settingsAction")
    if isinstance(settings_action, dict):
        return {
            "module": str(settings_action.get("module", "")),
            "action": str(settings_action.get("action", "")),
            "authorizationAction": str(settings_action.get("action", "")),
        }
    return {"module": "", "action": "", "authorizationAction": ""}


def build_handoff(
    *,
    package: dict[str, Any],
    packet: dict[str, Any],
    preflight: dict[str, Any],
    capture_plan: dict[str, Any] | None,
    package_path: str,
    packet_path: str,
    preflight_path: str,
    capture_plan_path: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    issues = validate_package(package, packet, preflight, capture_plan, max_age_minutes=max_age_minutes, now=now)
    if issues:
        raise ValueError("browser-stage authorization package is invalid:\n" + "\n".join(f"- {issue}" for issue in issues))

    stage_id = str(package.get("stageId", ""))
    action = package_action(package)
    return {
        "kind": "allincms_next_browser_action_handoff",
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "stageId": stage_id,
        "target": package.get("target"),
        "action": action,
        "authorizationRequired": package.get("authorizationRequired"),
        "gateSupported": package.get("gateSupported"),
        "commandsSuppressed": package.get("commandsSuppressed", False),
        "suggestedAuthorizationText": package.get("suggestedAuthorizationText"),
        "authorizationRecordCommand": package.get("authorizationRecordCommand"),
        "preMutationGateCommand": package.get("preMutationGateCommand"),
        "requiredProof": package.get("requiredProof", []),
        "mustCapture": package.get("mustCapture", []),
        "stopAfter": package.get("stopAfter", ""),
        "sourceFiles": {
            "authorizationPackage": package_path,
            "browserStagePacket": packet_path,
            "preflight": preflight_path,
            "capturePlan": capture_plan_path,
        },
        "validation": {
            "ok": True,
            "checks": [
                "authorization package shape",
                "browser-stage packet alignment",
                "preflight run-evidence validation",
                "capture-plan alignment when supplied",
                "current-user authorization placeholder retained when commands are emitted",
            ],
        },
        "warning": (
            "This handoff is preparation only. It is not user authorization and does not permit "
            "clicking, saving, uploading, publishing, deleting, replaying JSON, or continuing to another stage."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a validated handoff for one next browser action.")
    parser.add_argument("--package", required=True, dest="package_json")
    parser.add_argument("--packet-json", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--capture-plan", default="")
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        package = load_json(Path(args.package_json), "package")
        packet = load_json(Path(args.packet_json), "packet")
        preflight = load_json(Path(args.preflight), "preflight")
        capture_plan = load_json(Path(args.capture_plan), "capture plan") if args.capture_plan else None
        handoff = build_handoff(
            package=package,
            packet=packet,
            preflight=preflight,
            capture_plan=capture_plan,
            package_path=args.package_json,
            packet_path=args.packet_json,
            preflight_path=args.preflight,
            capture_plan_path=args.capture_plan,
            max_age_minutes=args.max_age_minutes,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).expanduser().write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
