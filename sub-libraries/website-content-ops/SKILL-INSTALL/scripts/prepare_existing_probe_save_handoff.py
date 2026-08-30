#!/usr/bin/env python3
"""Prepare a save-probe handoff for an already-existing probe edit page."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from prepare_probe_save_handoff import CONTENT_LABELS, PLACEHOLDER, PROBE_NAME, parse_edit_url


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


def validate_backend_state(state: dict[str, Any], site_key: str, content_type: str) -> list[str]:
    issues: list[str] = []
    if state.get("kind") != "allincms_product_edit_readonly_state":
        issues.append("backend state kind must be allincms_product_edit_readonly_state")
    if state.get("siteKey") != site_key:
        issues.append("backend state siteKey must match target")
    if state.get("contentType") != content_type:
        issues.append("backend state contentType must match target")
    if state.get("remoteMutationsPerformed") is not False:
        issues.append("backend state must be read-only evidence")
    observations = state.get("observations")
    if not isinstance(observations, dict):
        issues.append("backend state observations are required")
        return issues
    body = observations.get("bodyEditor")
    if not isinstance(body, dict):
        issues.append("backend state must include bodyEditor observation")
    else:
        if body.get("count") != 1:
            issues.append("bodyEditor.count must be 1 before save-probe body schema capture")
        if body.get("state") != "placeholder_only":
            issues.append("bodyEditor.state must be placeholder_only before non-empty schema capture handoff")
    if observations.get("updateDisabled") is not True:
        issues.append("updateDisabled must be true before edit/save capture starts")
    fields = observations.get("fieldsVisible")
    if not isinstance(fields, list) or "产品描述" not in fields:
        issues.append("fieldsVisible must include product description/edit fields")
    return issues


def build_handoff(
    *,
    backend_state: dict[str, Any],
    backend_state_path: str,
    edit_url: str,
    preflight_path: str,
    authorization_output: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    parts = parse_edit_url(edit_url)
    site_key = parts["siteKey"]
    content_type = parts["contentType"]
    issues = validate_backend_state(backend_state, site_key, content_type)
    if issues:
        raise ValueError("existing probe save handoff validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))

    label = CONTENT_LABELS.get(content_type, content_type)
    fields = "requestCapture,payloadShape,persistedVerified,name,slug,description,content,status"
    expected = "capture save request URL/method/header names/payload shape and verify backend persisted state; do not publish or batch upload"
    verification = (
        "type one small non-business body sample into the existing probe, save once, "
        "capture redacted request shape, and confirm backend persisted state"
    )
    cleanup = "cleanup or revert requires separate cleanup authorization after request capture"
    authorization_text = (
        f"授权 Codex 在 {edit_url} 保存一次现有 {PROBE_NAME} {label}测试项，"
        "仅用于捕获非空正文编辑器保存请求、payload 结构和后台持久化证明；"
        "本次停止条件：save request and backend persistence are captured; do not publish, upload media, batch upload, or clean up。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action save_probe "
        f"--site-key {site_key} "
        f"--target {edit_url} "
        f"--target-type {content_type} "
        f"--target-identifier '{PROBE_NAME} {content_type.rstrip('s')} existing probe' "
        f"--fields-or-files {fields} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{PLACEHOLDER}' "
        f"--output {authorization_output}"
    )
    pre_mutation_gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action save_probe "
        f"--preflight {preflight_path} "
        f"--authorization {authorization_output}"
    )
    return {
        "kind": "allincms_existing_probe_save_handoff",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "siteKey": site_key,
        "contentType": content_type,
        "action": "save_probe",
        "target": edit_url,
        "sourceFiles": {
            "backendReadonlyEvidence": backend_state_path,
            "preflight": preflight_path,
            "authorizationOutput": authorization_output,
        },
        "currentReadOnlyState": {
            "bodyEditorState": backend_state.get("observations", {}).get("bodyEditor", {}).get("state"),
            "updateDisabled": backend_state.get("observations", {}).get("updateDisabled"),
            "statusText": backend_state.get("observations", {}).get("statusText"),
        },
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustCaptureAfterAuthorization": [
            "unique rich editor focus and typed text proof",
            "update/save button enabled before save",
            "save request URL, method, volatile header names, payload keys/shape",
            "non-empty content block schema or explicit proof that body still serialized empty",
            "backend persisted state after one save",
            "no publish, upload, batch operation, delete, or cleanup performed",
        ],
        "forbiddenActions": [
            "publishing or unpublishing",
            "uploading media",
            "batch upload or publish",
            "cleaning or deleting the probe",
            "creating another probe",
        ],
        "stopAfter": "save request and backend persistence are captured; do not publish, upload media, batch upload, or clean up",
        "warning": (
            "This handoff is preparation only. It does not authorize saving. "
            "Generate the authorization record from current user action-time authorization, then run the pre-mutation gate."
        ),
    }


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_existing_probe_save_handoff":
        issues.append("kind must be allincms_existing_probe_save_handoff")
    for key in ("localOnly", "preparedOnly"):
        if handoff.get(key) is not True:
            issues.append(f"{key} must be true")
    if handoff.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if handoff.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if handoff.get("action") != "save_probe":
        issues.append("action must be save_probe")
    target = handoff.get("target")
    if not isinstance(target, str):
        issues.append("target must be present")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    current = handoff.get("currentReadOnlyState")
    if not isinstance(current, dict) or current.get("bodyEditorState") != "placeholder_only":
        issues.append("currentReadOnlyState.bodyEditorState must be placeholder_only")
    if PROBE_NAME not in str(handoff.get("suggestedAuthorizationText", "")):
        issues.append("suggestedAuthorizationText must identify the Codex Probe")
    command = handoff.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if handoff.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = handoff.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action save_probe" not in gate:
        issues.append("preMutationGateCommand must use save_probe")
    forbidden = handoff.get("forbiddenActions")
    if not isinstance(forbidden, list) or "creating another probe" not in forbidden or "cleaning or deleting the probe" not in forbidden:
        issues.append("forbiddenActions must block duplicate probe creation and cleanup")
    warning = handoff.get("warning")
    if not isinstance(warning, str) or "preparation only" not in warning:
        issues.append("warning must state this is preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare save handoff for an existing Codex Probe edit page.")
    parser.add_argument("--backend-state", required=True)
    parser.add_argument("--edit-url", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        backend_state = load_json(Path(args.backend_state), "backend state")
        handoff = build_handoff(
            backend_state=backend_state,
            backend_state_path=args.backend_state,
            edit_url=args.edit_url,
            preflight_path=args.preflight,
            authorization_output=args.authorization_output,
        )
        issues = validate_handoff(handoff)
        if issues:
            raise ValueError("handoff validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(handoff, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote existing-probe save handoff: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
