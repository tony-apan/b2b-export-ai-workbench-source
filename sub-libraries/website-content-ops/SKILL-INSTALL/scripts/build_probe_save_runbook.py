#!/usr/bin/env python3
"""Build a local browser runbook for one authorized save-probe capture."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from prepare_existing_probe_save_handoff import validate_handoff as validate_existing_probe_save_handoff
from prepare_probe_save_handoff import PROBE_NAME, parse_edit_url, validate_handoff


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def default_slug(content_type: str) -> str:
    if content_type == "products":
        return "codex-probe-product-delete-me"
    if content_type == "posts":
        return "codex-probe-post-delete-me"
    return "codex-probe-delete-me"


def validate_supported_handoff(handoff: dict[str, Any]) -> list[str]:
    kind = handoff.get("kind")
    if kind == "allincms_existing_probe_save_handoff":
        return validate_existing_probe_save_handoff(handoff)
    return validate_handoff(handoff)


def is_existing_probe_handoff(handoff: dict[str, Any]) -> bool:
    return handoff.get("kind") == "allincms_existing_probe_save_handoff"


def build_runbook(handoff: dict[str, Any], *, handoff_path: str, generated_at: str | None = None) -> dict[str, Any]:
    issues = validate_supported_handoff(handoff)
    if issues:
        raise ValueError("handoff validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    target = str(handoff["target"])
    parts = parse_edit_url(target)
    content_type = parts["contentType"]
    slug = default_slug(content_type)
    existing_probe = is_existing_probe_handoff(handoff)
    open_verify = ["URL matches target", "publish/unpublish controls are not clicked"]
    if existing_probe:
        open_verify.extend(["body editor is placeholder-only before typing", "更新 button starts disabled before field changes"])
    else:
        open_verify.extend(["status is draft", "publish button is visible but not clicked"])
    edit_fields = [
        {
            "label": "正文编辑器",
            "value": "Temporary non-business body sample for schema capture.",
            "required": True,
            "purpose": "force a non-empty body/editor payload shape",
        }
    ]
    if not existing_probe:
        edit_fields = [
            {"label": "名称", "value": PROBE_NAME, "required": True},
            {"label": "Slug", "value": slug, "required": True},
            {
                "label": "描述",
                "value": "Temporary probe for request capture. Delete after verification.",
                "required": True,
            },
            *edit_fields,
        ]
    return {
        "kind": "allincms_probe_save_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceHandoff": handoff_path,
        "sourceHandoffKind": handoff.get("kind"),
        "existingProbeResume": existing_probe,
        "siteKey": parts["siteKey"],
        "contentType": content_type,
        "target": target,
        "action": "save_probe",
        "authorizationRequired": True,
        "mustRunBeforeBrowserSave": [
            "generate authorization record from current user action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "confirm the browser is still on the target edit URL",
            "enable network capture before clicking 更新",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_or_claim_target",
                "mode": "read_only_until_fields_change",
                "target": target,
                "verify": open_verify,
            },
            {
                "step": "edit_probe_fields",
                "mode": "mutating_after_gate",
                "fields": edit_fields,
                "verify": ["更新 button becomes enabled", "publish/unpublish controls remain unclicked"],
            },
            {
                "step": "capture_save_request",
                "mode": "mutating_after_gate",
                "action": "click 更新 exactly once",
                "capture": [
                    "Network.requestWillBeSent for POST under the target edit URL or content module",
                    "Network.responseReceived status and mime type",
                    "redacted request header names only",
                    "redacted payload top-level keys/shape",
                    "siteId and productId/postId/formId field names with values redacted",
                ],
            },
            {
                "step": "verify_persistence",
                "mode": "read_only_after_save",
                "verify": [
                    "backend edit page or list shows the probe name or slug",
                    "status remains draft unless publish is separately authorized",
                    "no publish, upload, delete, cleanup, batch, or replay action occurred",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_probe_save_capture_evidence",
            "contentType": content_type,
            "target": target.replace(parts["contentId"], "{contentId}").replace(parts["siteKey"], "{siteKey}"),
            "authorizationRecord": str(handoff.get("sourceFiles", {}).get("authorizationOutput", "")),
            "preMutationGate": "passed|required_before_save",
            "savedOnce": False,
            "published": False,
            "requestCapture": {
                "method": "POST",
                "urlPattern": "https://workspace.laicms.com/{siteKey}/...",
                "headersShape": [],
                "payloadShape": {},
                "responseStatus": None,
                "responseMimeType": "",
            },
            "fieldMapping": {
                "nameField": "to_verify",
                "slugField": "to_verify",
                "descriptionField": "to_verify",
                "bodyField": "to_verify",
                "mediaField": "to_verify",
                "statusField": "to_verify",
            },
            "payloadTemplate": "to_build_from_redacted_capture",
            "backendPersisted": False,
            "stopConditionMet": False,
        },
        "automationPreferenceDoesNotAuthorize": list(
            handoff.get("automationPreference", {}).get("doesNotAuthorize", ["saving the probe"])
        ),
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "publishing the probe",
            "deleting or cleaning the probe",
            "uploading media",
            "batch upload or batch publish",
            "JSON/Server Action replay against LAICMS",
            "clicking 更新 more than once unless a new save authorization is issued",
        ],
        "stopAfter": handoff.get("stopAfter", ""),
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "save_probe authorization record exists and the pre-mutation gate passes."
        ),
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_probe_save_browser_runbook":
        issues.append("kind must be allincms_probe_save_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "save_probe":
        issues.append("action must be save_probe")
    if runbook.get("authorizationRequired") is not True:
        issues.append("authorizationRequired must be true")
    target = runbook.get("target")
    if not isinstance(target, str):
        issues.append("target must be a string")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include open, edit, capture, and verify steps")
    else:
        step_names = [step.get("step") for step in steps if isinstance(step, dict)]
        for required in ("open_or_claim_target", "edit_probe_fields", "capture_save_request", "verify_persistence"):
            if required not in step_names:
                issues.append(f"browserStepsAfterGate missing {required}")
    gate_steps = runbook.get("mustRunBeforeBrowserSave")
    if not isinstance(gate_steps, list) or not any("preMutationGateCommand" in str(item) for item in gate_steps):
        issues.append("mustRunBeforeBrowserSave must require the pre-mutation gate")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("savedOnce") is not False or template.get("published") is not False:
        issues.append("redactedEvidenceTemplate must start unsaved and unpublished")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false until authorization and gate pass")
    preference_denials = runbook.get("automationPreferenceDoesNotAuthorize")
    if not isinstance(preference_denials, list) or "saving the probe" not in preference_denials:
        issues.append("automationPreferenceDoesNotAuthorize must include saving the probe")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "publishing the probe" not in forbidden:
        issues.append("forbiddenActions must include publishing the probe")
    elif "saving the probe" in forbidden:
        issues.append("forbiddenActions must not include saving the probe; save is allowed only after the gate passes")
    warning = runbook.get("warning")
    if not isinstance(warning, str) or "local preparation only" not in warning:
        issues.append("warning must state this is local preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook for one save-probe capture.")
    parser.add_argument("handoff_json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.handoff_json))
        runbook = build_runbook(handoff, handoff_path=args.handoff_json)
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
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
