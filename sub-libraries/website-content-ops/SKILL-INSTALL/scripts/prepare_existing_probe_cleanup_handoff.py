#!/usr/bin/env python3
"""Prepare a cleanup handoff for an already-existing public probe.

Use this after a read-only resume finds a Codex Probe item already published or
public, but older queue/runbook artifacts still point at create-probe.
"""

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


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None


def frontend_audit_status(audit: Any) -> dict[str, Any]:
    if isinstance(audit, list) and audit:
        first = audit[0]
        if isinstance(first, dict):
            return {
                "status": first.get("status"),
                "imageCount": first.get("imageCount"),
                "issues": first.get("issues") if isinstance(first.get("issues"), list) else [],
                "route": first.get("url"),
            }
    if isinstance(audit, dict):
        return {
            "status": audit.get("status"),
            "imageCount": audit.get("imageCount"),
            "issues": audit.get("issues") if isinstance(audit.get("issues"), list) else [],
            "route": audit.get("url"),
        }
    return {"status": None, "imageCount": None, "issues": ["frontend audit shape is not recognized"], "route": ""}


def validate_backend_state(state: dict[str, Any], site_key: str, content_type: str) -> list[str]:
    issues: list[str] = []
    if state.get("kind") != "allincms_product_edit_readonly_state":
        issues.append("backend state kind must be allincms_product_edit_readonly_state")
    if state.get("siteKey") != site_key:
        issues.append("backend state siteKey must match target")
    if state.get("contentType") != content_type:
        issues.append("backend state contentType must match target")
    observations = state.get("observations")
    if not isinstance(observations, dict):
        issues.append("backend state observations are required")
    else:
        if observations.get("statusText") != "published_visible":
            issues.append("backend state must show published_visible before public-probe cleanup handoff")
        if observations.get("unpublishVisible") is not True:
            issues.append("backend state must show an unpublish/cleanup-capable control")
        body = observations.get("bodyEditor")
        if not isinstance(body, dict):
            issues.append("backend state bodyEditor observation is required")
    if state.get("remoteMutationsPerformed") is not False:
        issues.append("backend state must be read-only evidence")
    return issues


def build_handoff(
    *,
    backend_state: dict[str, Any],
    backend_state_path: str,
    frontend_audit: Any,
    frontend_audit_path: str,
    edit_url: str,
    frontend_url: str,
    preflight_path: str,
    authorization_output: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    parts = parse_edit_url(edit_url)
    site_key = parts["siteKey"]
    content_type = parts["contentType"]
    issues = validate_backend_state(backend_state, site_key, content_type)
    audit_status = frontend_audit_status(frontend_audit)
    if audit_status["status"] != 200:
        issues.append("frontend audit must show the probe detail currently returns 200")
    if issues:
        raise ValueError("existing probe cleanup handoff validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))

    label = CONTENT_LABELS.get(content_type, content_type)
    fields = "cleanedCandidates,backendVerified,frontendVerified"
    expected = f"{content_type} public probe unpublished or deleted and frontend no longer renders probe"
    verification = "unpublish or delete exactly the Codex Probe item, verify backend non-public state and frontend 404/non-rendering"
    authorization_text = (
        f"授权 Codex 在 {edit_url} 清理已公开的 {PROBE_NAME} {label}测试项，"
        f"允许取消发布或删除该 probe，并验证 {frontend_url} 不再公开渲染；"
        "本次只允许清理这个 probe，不允许保存正文、上传媒体、批量上传、或影响真实业务内容。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action cleanup_probe "
        f"--site-key {site_key} "
        f"--target {edit_url} "
        f"--target-type {content_type} "
        f"--target-identifier '{PROBE_NAME} {content_type.rstrip('s')} public probe' "
        f"--fields-or-files {fields} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        "--cleanup-plan 'cleanup is the requested action' "
        f"--authorization-source '{PLACEHOLDER}' "
        f"--output {authorization_output}"
    )
    pre_mutation_gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action cleanup_probe "
        f"--preflight {preflight_path} "
        f"--authorization {authorization_output}"
    )
    return {
        "kind": "allincms_existing_probe_cleanup_handoff",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "siteKey": site_key,
        "contentType": content_type,
        "action": "cleanup_probe",
        "target": edit_url,
        "frontendUrl": frontend_url,
        "sourceFiles": {
            "backendReadonlyEvidence": backend_state_path,
            "frontendAudit": frontend_audit_path,
            "preflight": preflight_path,
            "authorizationOutput": authorization_output,
        },
        "currentReadOnlyState": {
            "backendPublishedVisible": True,
            "frontendStatus": audit_status["status"],
            "frontendImageCount": audit_status["imageCount"],
            "frontendIssues": audit_status["issues"],
        },
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustCaptureAfterAuthorization": [
            "cleanup/unpublish/delete request shape with secret values redacted",
            "backend list or edit page proves probe is deleted or unpublished",
            "frontend detail URL returns 404 or no longer renders probe content",
            "no save, media upload, batch operation, or non-probe content changes",
        ],
        "forbiddenActions": [
            "saving product fields or body",
            "uploading media",
            "batch upload or publish",
            "cleaning non-probe content",
            "creating another probe",
        ],
        "stopAfter": "existing public probe cleanup and backend/frontend non-public proof are captured",
        "warning": (
            "This handoff is preparation only. It does not authorize cleanup. "
            "Generate the authorization record from current user action-time authorization, then run the pre-mutation gate."
        ),
    }


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_existing_probe_cleanup_handoff":
        issues.append("kind must be allincms_existing_probe_cleanup_handoff")
    for key in ("localOnly", "preparedOnly"):
        if handoff.get(key) is not True:
            issues.append(f"{key} must be true")
    if handoff.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if handoff.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if handoff.get("action") != "cleanup_probe":
        issues.append("action must be cleanup_probe")
    target = handoff.get("target")
    if not isinstance(target, str):
        issues.append("target must be present")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    current_state = handoff.get("currentReadOnlyState")
    if not isinstance(current_state, dict) or current_state.get("frontendStatus") != 200:
        issues.append("currentReadOnlyState.frontendStatus must be 200")
    if PROBE_NAME not in str(handoff.get("suggestedAuthorizationText", "")):
        issues.append("suggestedAuthorizationText must identify the Codex Probe")
    command = handoff.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if handoff.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = handoff.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action cleanup_probe" not in gate:
        issues.append("preMutationGateCommand must use cleanup_probe")
    forbidden = handoff.get("forbiddenActions")
    if not isinstance(forbidden, list) or "creating another probe" not in forbidden:
        issues.append("forbiddenActions must include creating another probe")
    warning = handoff.get("warning")
    if not isinstance(warning, str) or "preparation only" not in warning:
        issues.append("warning must state this is preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare cleanup handoff for an existing public Codex Probe item.")
    parser.add_argument("--backend-state", required=True)
    parser.add_argument("--frontend-audit", required=True)
    parser.add_argument("--edit-url", required=True)
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        backend_state = load_json(Path(args.backend_state), "backend state")
        frontend_audit = load_json(Path(args.frontend_audit), "frontend audit")
        if not isinstance(backend_state, dict):
            raise ValueError("backend state JSON root must be an object")
        handoff = build_handoff(
            backend_state=backend_state,
            backend_state_path=args.backend_state,
            frontend_audit=frontend_audit,
            frontend_audit_path=args.frontend_audit,
            edit_url=args.edit_url,
            frontend_url=args.frontend_url,
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
        print(f"Wrote existing-probe cleanup handoff: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
