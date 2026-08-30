#!/usr/bin/env python3
"""Build queue readiness from a validated browser-stage authorization package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES
from summarize_run_status import freshness_status
from validate_browser_stage_authorization_package import load_json, validate_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def action_from_package(package: dict[str, Any]) -> dict[str, str]:
    capture_stage = package.get("captureStage")
    if isinstance(capture_stage, dict) and capture_stage.get("authorizationAction"):
        return {
            "authorizationAction": str(capture_stage["authorizationAction"]),
            "source": "browser_stage_authorization_package.captureStage",
            "module": str(capture_stage.get("module", "")),
            "captureAction": str(capture_stage.get("action", "")),
        }
    return {
        "authorizationAction": str(package.get("authorizationAction", "")),
        "source": "browser_stage_authorization_package",
    }


def build_report(
    package_path: Path,
    *,
    packet_path: Path | None = None,
    preflight_path: Path | None = None,
    capture_plan_path: Path | None = None,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    package = load_json(package_path, "package")
    packet = load_json(packet_path, "packet") if packet_path else None
    preflight = load_json(preflight_path, "preflight") if preflight_path else None
    capture_plan = load_json(capture_plan_path, "capture plan") if capture_plan_path else None

    issues = validate_package(
        package,
        packet,
        preflight,
        capture_plan,
        max_age_minutes=max_age_minutes,
        now=now,
    )
    freshness = (
        freshness_status(preflight, max_age_minutes=max_age_minutes, now=now)
        if isinstance(preflight, dict)
        else {
            "generatedAt": "",
            "maxAgeMinutes": max_age_minutes,
            "freshForMutation": False,
            "reason": "missing_preflight_source",
        }
    )
    prepared_only_ok = (
        package.get("authorizationRequired") is True
        and package.get("remoteMutationsPerformed") is not True
        and package.get("gateSupported") is True
    )
    ready = not issues and prepared_only_ok and freshness.get("freshForMutation") is True
    blockers: list[str] = []
    if issues:
        blockers.append("browser_stage_authorization_package_validation_failed")
    if not prepared_only_ok:
        blockers.append("package_not_ready_for_gated_authorization")
    if freshness.get("freshForMutation") is not True:
        blockers.append("preflight_not_fresh_for_mutation")

    return {
        "kind": "allincms_next_browser_action_handoff_readiness",
        "generatedAt": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "remoteMutationsPerformed": False,
        "handoff": str(package_path),
        "preflight": str(preflight_path or ""),
        "target": package.get("target"),
        "action": action_from_package(package),
        "stopAfter": package.get("stopAfter"),
        "preparedOnly": True,
        "isUserAuthorization": False,
        "validation": {
            "ok": not issues,
            "issues": issues,
            "source": "validate_browser_stage_authorization_package",
        },
        "evidenceFreshness": freshness,
        "status": "ready_to_request_authorization" if ready else "blocked_refresh_readonly_evidence",
        "blockers": blockers,
        "nextAction": (
            "ask the user for exact action-time authorization; do not run commands until they provide it"
            if ready
            else "refresh read-only evidence or rebuild the browser-stage authorization package before asking for authorization"
        ),
        "sourceFiles": {
            "authorizationPackage": str(package_path),
            "packet": str(packet_path or ""),
            "preflight": str(preflight_path or ""),
            "capturePlan": str(capture_plan_path or ""),
        },
        "authorizationTextFromPackage": str(package.get("suggestedAuthorizationText", "") or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build queue readiness from a browser-stage authorization package.")
    parser.add_argument("package_json")
    parser.add_argument("--packet-json", default="")
    parser.add_argument("--preflight", default="")
    parser.add_argument("--capture-plan", default="")
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    try:
        report = build_report(
            Path(args.package_json),
            packet_path=Path(args.packet_json) if args.packet_json else None,
            preflight_path=Path(args.preflight) if args.preflight else None,
            capture_plan_path=Path(args.capture_plan) if args.capture_plan else None,
            max_age_minutes=args.max_age_minutes,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"status={report['status']} freshness={report['evidenceFreshness'].get('reason')}")
    if args.fail_on_blocked and report["status"] != "ready_to_request_authorization":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
