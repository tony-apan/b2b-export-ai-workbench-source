#!/usr/bin/env python3
"""Prepare the next handoff from a source confirmation brief."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from typing import Any

from validate_source_confirmation_brief import load_json, validate_brief


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def replace_confirmation_placeholder(command: str, confirmation_text: str) -> str:
    quoted = shlex.quote(confirmation_text)
    return (
        command.replace("'<paste current user confirmation text here>'", quoted)
        .replace('"<paste current user confirmation text here>"', quoted)
        .replace("<paste current user confirmation text here>", quoted)
    )


def next_action_for_intake(intake: dict[str, Any], has_confirmation_text: bool) -> str:
    mode = intake.get("mode")
    if mode == "await_user_confirmation_text":
        if has_confirmation_text:
            return "run localCommand to prepare confirmed execution artifacts; this does not authorize remote mutation"
        return "show the confirmation brief to the user and capture explicit content-intent confirmation text"
    if mode == "collect_create_preflight":
        return "collect read-only /sites create preflight evidence into createPreflightTarget, then rerun confirmed execution preparation"
    if mode == "run_gated_create_site":
        return "use createSiteRunbook only after action-time authorization and the create_site pre-mutation gate pass"
    return "refine source wiki/package before asking for user confirmation"


def build_handoff(args: argparse.Namespace) -> dict[str, Any]:
    brief_path = Path(args.brief).expanduser().resolve()
    brief = load_json(brief_path, "source confirmation brief")
    summary = load_json(Path(args.summary).expanduser().resolve(), "source rehearsal summary") if args.summary else None
    issues = validate_brief(brief, summary)
    if issues:
        raise SystemExit("ERROR: invalid source confirmation brief:\n- " + "\n- ".join(issues))

    intake = as_dict(brief.get("executionIntake"))
    mode = str(intake.get("mode") or "")
    confirmation_text = args.user_confirmation_text.strip()
    local_command = ""
    if mode == "await_user_confirmation_text" and confirmation_text:
        template = str(intake.get("nextCommandTemplate") or "")
        if not template:
            raise SystemExit("ERROR: executionIntake.nextCommandTemplate is required when user confirmation text is supplied")
        local_command = replace_confirmation_placeholder(template, confirmation_text)

    browser_boundary: dict[str, Any] = {
        "required": False,
        "action": "",
        "readOnly": True,
        "requiresActionAuthorization": False,
        "browserStepsExecutable": False,
        "runbook": "",
        "evidenceBundle": "",
        "targetEvidence": "",
    }
    if mode == "collect_create_preflight":
        browser_boundary.update(
            {
                "required": True,
                "action": "collect_create_site_preflight",
                "readOnly": True,
                "targetEvidence": intake.get("createPreflightTarget", ""),
            }
        )
    elif mode == "run_gated_create_site":
        browser_boundary.update(
            {
                "required": True,
                "action": "create_site_submit",
                "readOnly": False,
                "requiresActionAuthorization": True,
                "runbook": intake.get("createSiteRunbook", ""),
                "evidenceBundle": intake.get("createdSiteEvidenceBundle", ""),
            }
        )

    handoff = {
        "kind": "allincms_source_confirmation_next_step_handoff",
        "generatedAt": now_iso(),
        "brief": str(brief_path),
        "summary": str(Path(args.summary).expanduser().resolve()) if args.summary else str(brief.get("summary") or ""),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "mode": mode,
        "status": brief.get("status"),
        "readyForBrowserStage": brief.get("readyForBrowserStage"),
        "sourcePackage": intake.get("sourcePackage", ""),
        "reviewPacket": intake.get("reviewPacket", ""),
        "confirmationOutput": intake.get("confirmationOutput", ""),
        "confirmedExecutionOutputDir": intake.get("confirmedExecutionOutputDir", ""),
        "createActionGateOutput": intake.get("createActionGateOutput", ""),
        "localCommand": local_command,
        "localCommandReady": bool(local_command),
        "browserBoundary": browser_boundary,
        "nextAction": next_action_for_intake(intake, bool(confirmation_text)),
        "adversarialChecks": [
            "This handoff is derived from a validated source confirmation brief.",
            "It does not create, save, upload, publish, delete, bind routes, bind domains, or authorize remote mutation.",
            "If browserBoundary.requiresActionAuthorization is true, run the action-time authorization and pre-mutation gate before browser execution.",
            "Draft manifests remain schemaVerified=false until current-site save-request capture and sample verification.",
        ],
        "blockedRemoteActions": as_list(brief.get("blockedRemoteActions")),
    }
    return handoff


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_source_confirmation_next_step_handoff":
        issues.append("kind must be allincms_source_confirmation_next_step_handoff")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if handoff.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    mode = handoff.get("mode")
    if mode not in {"refine_source_wiki", "await_user_confirmation_text", "collect_create_preflight", "run_gated_create_site"}:
        issues.append("mode must be a known executionIntake mode")
    boundary = handoff.get("browserBoundary")
    if not isinstance(boundary, dict):
        issues.append("browserBoundary must be an object")
        boundary = {}
    if mode == "await_user_confirmation_text" and handoff.get("localCommandReady") is True:
        if "prepare_confirmed_site_execution.py" not in str(handoff.get("localCommand") or ""):
            issues.append("localCommand must prepare confirmed execution when confirmation text is supplied")
    if mode == "collect_create_preflight":
        if boundary.get("required") is not True or boundary.get("readOnly") is not True:
            issues.append("collect_create_preflight browserBoundary must be required and read-only")
        if not boundary.get("targetEvidence"):
            issues.append("collect_create_preflight browserBoundary.targetEvidence is required")
        if handoff.get("localCommand"):
            issues.append("collect_create_preflight handoff must not include localCommand")
    if mode == "run_gated_create_site":
        if boundary.get("required") is not True or boundary.get("readOnly") is not False:
            issues.append("run_gated_create_site browserBoundary must be required and mutating")
        if boundary.get("requiresActionAuthorization") is not True:
            issues.append("run_gated_create_site must require action authorization")
        if boundary.get("browserStepsExecutable") is not False:
            issues.append("browserStepsExecutable must remain false until the pre-mutation gate passes")
        if not boundary.get("runbook"):
            issues.append("run_gated_create_site browserBoundary.runbook is required")
        if not boundary.get("evidenceBundle"):
            issues.append("run_gated_create_site browserBoundary.evidenceBundle is required")
    checks = as_list(handoff.get("adversarialChecks"))
    if not checks or not all(isinstance(item, str) and item.strip() for item in checks):
        issues.append("adversarialChecks must contain non-empty strings")
    if not any("not" in item.lower() and "authorize" in item.lower() for item in checks):
        issues.append("adversarialChecks must state the handoff does not authorize remote mutation")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the next handoff from a source confirmation brief.")
    parser.add_argument("brief")
    parser.add_argument("--summary", default="")
    parser.add_argument("--user-confirmation-text", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    handoff = build_handoff(args)
    issues = validate_handoff(handoff)
    if issues:
        raise SystemExit("ERROR: generated source confirmation next-step handoff is invalid:\n- " + "\n- ".join(issues))
    write_json(output, handoff)
    if args.json:
        print(json.dumps(handoff, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source confirmation next-step handoff: {output}")
        print(f"mode={handoff['mode']} nextAction={handoff['nextAction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
