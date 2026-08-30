#!/usr/bin/env python3
"""Build a cleanup runbook from an existing public-probe cleanup handoff."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from prepare_existing_probe_cleanup_handoff import validate_handoff as validate_existing_cleanup_handoff
from prepare_probe_save_handoff import PLACEHOLDER, parse_edit_url


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def build_runbook(
    *,
    handoff: dict[str, Any],
    handoff_path: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    issues = validate_existing_cleanup_handoff(handoff)
    if issues:
        raise ValueError("existing cleanup handoff is not valid:\n" + "\n".join(f"- {issue}" for issue in issues))

    target = str(handoff["target"])
    parts = parse_edit_url(target)
    frontend_url = str(handoff.get("frontendUrl") or "")
    current_state = handoff.get("currentReadOnlyState")
    if not isinstance(current_state, dict):
        current_state = {}

    template_target = target.replace(parts["siteKey"], "{siteKey}").replace(parts["contentId"], "{contentId}")
    return {
        "kind": "allincms_existing_probe_cleanup_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceHandoff": handoff_path,
        "siteKey": parts["siteKey"],
        "contentType": parts["contentType"],
        "target": target,
        "frontendUrl": frontend_url,
        "action": "cleanup_probe",
        "authorizationRequired": True,
        "suggestedAuthorizationText": handoff.get("suggestedAuthorizationText", ""),
        "authorizationRecordCommand": handoff.get("authorizationRecordCommand", ""),
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in str(handoff.get("authorizationRecordCommand", "")),
        "preMutationGateCommand": handoff.get("preMutationGateCommand", ""),
        "mustRunBeforeBrowserCleanup": [
            "generate authorization record from current user action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "re-open the target edit page and confirm it is still the Codex Probe item",
            "confirm frontend detail is still public before cleanup, or update the handoff if it changed",
            "enable network capture before clicking unpublish/delete",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_or_claim_target",
                "mode": "read_only_until_cleanup_click",
                "target": target,
                "verify": [
                    "URL matches target",
                    "probe/test title or slug is visible",
                    "unpublish/delete-capable control is visible",
                ],
            },
            {
                "step": "cleanup_existing_public_probe",
                "mode": "mutating_after_gate",
                "action": "unpublish or delete exactly the existing Codex Probe item once",
                "capture": [
                    "cleanup/unpublish/delete request URL and method",
                    "response status and mime type",
                    "redacted request header names only",
                    "redacted payload top-level keys/shape",
                ],
            },
            {
                "step": "verify_backend_non_public",
                "mode": "read_only_after_cleanup",
                "verify": ["backend no longer shows the probe as public"],
            },
            {
                "step": "verify_frontend_non_public",
                "mode": "read_only_after_cleanup",
                "target": frontend_url,
                "verify": ["frontend detail returns 404 or no longer renders probe content"],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_probe_cleanup_evidence",
            "contentType": parts["contentType"],
            "target": template_target,
            "authorizationRecord": handoff.get("sourceFiles", {}).get("authorizationOutput", ""),
            "preMutationGate": "passed|required_before_cleanup",
            "cleanupAction": "",
            "cleanedCandidates": [
                {
                    "contentType": parts["contentType"],
                    "titlePattern": "Codex Probe - Delete Me",
                    "backendUrl": template_target,
                    "reason": "existing public probe cleanup",
                }
            ],
            "cleanedCount": 0,
            "backendVerified": False,
            "frontendVerified": False,
            "backendEvidence": "",
            "frontendEvidence": "",
            "stopConditionMet": False,
        },
        "currentReadOnlyState": current_state,
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "saving product fields or body",
            "uploading media",
            "batch upload or publish",
            "cleaning non-probe content",
            "creating another probe",
            "running a second cleanup action without new authorization",
        ],
        "stopAfter": "existing public probe cleanup and backend/frontend non-public proof captured",
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "cleanup_probe authorization record exists and the pre-mutation gate passes."
        ),
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_existing_probe_cleanup_browser_runbook":
        issues.append("kind must be allincms_existing_probe_cleanup_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "cleanup_probe":
        issues.append("action must be cleanup_probe")
    if runbook.get("authorizationRequired") is not True:
        issues.append("authorizationRequired must be true")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if runbook.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action cleanup_probe" not in gate:
        issues.append("preMutationGateCommand must use cleanup_probe")
    try:
        parse_edit_url(str(runbook.get("target", "")))
    except ValueError as exc:
        issues.append(str(exc))
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include open, cleanup, backend verify, and frontend verify")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict):
        issues.append("redactedEvidenceTemplate must be an object")
    else:
        if template.get("preMutationGate") != "passed|required_before_cleanup":
            issues.append("redactedEvidenceTemplate.preMutationGate must remain unfilled")
        if template.get("cleanedCount") != 0 or template.get("backendVerified") is not False:
            issues.append("redactedEvidenceTemplate must start uncleaned and unverified")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "cleaning non-probe content" not in forbidden:
        issues.append("forbiddenActions must block non-probe cleanup")
    warning = runbook.get("warning")
    if not isinstance(warning, str) or "local preparation only" not in warning:
        issues.append("warning must state this is local preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook from an existing-probe cleanup handoff.")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.handoff), "handoff")
        runbook = build_runbook(handoff=handoff, handoff_path=args.handoff)
        issues = validate_runbook(runbook)
        if issues:
            raise ValueError("runbook validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(runbook, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote existing-probe cleanup runbook: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
