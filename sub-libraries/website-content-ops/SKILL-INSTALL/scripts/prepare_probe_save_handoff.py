#!/usr/bin/env python3
"""Prepare a non-authorizing save-probe handoff from create-probe evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

from make_authorization_record import WORKSPACE_ORIGIN


EDIT_URL_RE = re.compile(
    r"^https://workspace\.laicms\.com/(?P<siteKey>[a-z0-9][a-z0-9-]{2,62}[a-z0-9])/"
    r"(?P<contentType>posts|products|forms)/(?P<contentId>[a-f0-9]{8,}|[A-Za-z0-9_-]{8,})/update$"
)
CONTENT_LABELS = {
    "posts": "文章",
    "products": "产品",
    "forms": "表单",
}
PROBE_NAME = "Codex Probe - Delete Me"
PLACEHOLDER = "<paste current user authorization text here>"


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


def parse_edit_url(url: str) -> dict[str, str]:
    match = EDIT_URL_RE.fullmatch(url.strip())
    if not match:
        raise ValueError("probe edit URL must be a concrete workspace /{siteKey}/{contentType}/{contentId}/update URL")
    return match.groupdict()


def validate_create_evidence(evidence: dict[str, Any], site_key: str, content_type: str) -> list[str]:
    issues: list[str] = []
    if evidence.get("kind") != "allincms_redacted_browser_stage_evidence":
        issues.append("create evidence kind must be allincms_redacted_browser_stage_evidence")
    if evidence.get("action") not in {"create_post_probe", "create_product_probe", "create_form_probe"}:
        issues.append("create evidence action must be a create_*_probe action")
    if evidence.get("contentType") != content_type:
        issues.append("create evidence contentType must match edit URL")
    target = evidence.get("target")
    if target not in {
        f"{WORKSPACE_ORIGIN}/{{siteKey}}/{content_type}",
        f"{WORKSPACE_ORIGIN}/{site_key}/{content_type}",
    }:
        issues.append("create evidence target must match the content type")
    browser_action = evidence.get("browserAction")
    if not isinstance(browser_action, dict):
        issues.append("create evidence browserAction is required")
    else:
        if browser_action.get("stopConditionMet") is not True:
            issues.append("create evidence must prove the create-stage stop condition was met")
        if browser_action.get("saveClicked") is not False:
            issues.append("create evidence must show save was not clicked")
        if browser_action.get("publishClicked") is not False:
            issues.append("create evidence must show publish was not clicked")
    cleanup_candidate = evidence.get("cleanupCandidate")
    if not isinstance(cleanup_candidate, dict) or cleanup_candidate.get("exists") is not True:
        issues.append("create evidence must record a cleanup candidate")
    return issues


def build_handoff(
    *,
    create_evidence: dict[str, Any],
    create_evidence_path: str,
    preflight_path: str,
    edit_url: str,
    authorization_output: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    parts = parse_edit_url(edit_url)
    site_key = parts["siteKey"]
    content_type = parts["contentType"]
    issues = validate_create_evidence(create_evidence, site_key, content_type)
    if issues:
        raise ValueError("create evidence validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))

    label = CONTENT_LABELS[content_type]
    target_identifier = PROBE_NAME
    fields = "requestCapture,payloadShape,persistedVerified,name,slug,description,content,status"
    expected = "capture save request URL/method/headers/payload shape and verify backend persisted draft state; do not publish or batch upload"
    verification = (
        f"rename the {content_type} draft to {PROBE_NAME}, save once, capture redacted save request, "
        "and confirm backend persisted fields"
    )
    cleanup = "cleanup requires separate cleanup authorization after request capture and verification"
    authorization_text = (
        f"授权 Codex 在 {edit_url} 保存一次 {PROBE_NAME} {label}测试草稿，用于捕获保存请求和 payload 结构，"
        "并验证后台草稿持久化；本次停止条件：save request and backend persistence are captured; do not publish or batch upload。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action save_probe "
        f"--site-key {site_key} "
        f"--target {edit_url} "
        f"--target-type {content_type} "
        f"--target-identifier '{target_identifier}' "
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
        "kind": "allincms_probe_save_handoff",
        "generatedAt": generated_at or now_iso(),
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "automationPreference": {
            "canProceedWithoutAsking": [
                "local JSON preparation",
                "read-only browser verification",
                "local validation commands",
                "pre-mutation gate checks that do not mutate LAICMS",
            ],
            "doesNotAuthorize": [
                "saving the probe",
                "publishing the probe",
                "deleting or cleaning the probe",
                "uploading media",
                "batch upload or batch publish",
                "JSON/Server Action replay against LAICMS",
            ],
            "rule": (
                "A broad user preference to reduce interruptions can drive local preparation and read-only checks, "
                "but the save_probe mutation still needs action-time authorization that names the exact save/capture action and target."
            ),
        },
        "siteKey": site_key,
        "contentType": content_type,
        "target": edit_url,
        "action": "save_probe",
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustCapture": [
            "request URL, method, volatile header names, payload keys/shape",
            "fieldMapping and payloadTemplate for the current content type",
            "backend persisted draft state",
            "no publish, upload, delete, or batch operation performed",
        ],
        "stopAfter": "save request and backend persistence are captured; do not publish or batch upload",
        "sourceFiles": {
            "createEvidence": create_evidence_path,
            "preflight": preflight_path,
            "authorizationOutput": authorization_output,
        },
        "warning": (
            "This handoff is preparation only. It is not user authorization and does not permit saving, "
            "publishing, deleting, uploading, or replaying JSON until the current user provides matching action-time authorization."
        ),
    }


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_probe_save_handoff":
        issues.append("kind must be allincms_probe_save_handoff")
    if handoff.get("preparedOnly") is not True:
        issues.append("preparedOnly must be true")
    if handoff.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if handoff.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    automation_preference = handoff.get("automationPreference")
    if not isinstance(automation_preference, dict):
        issues.append("automationPreference must describe what broad proceed preferences do and do not authorize")
    else:
        not_authorized = automation_preference.get("doesNotAuthorize")
        rule = automation_preference.get("rule")
        if not isinstance(not_authorized, list) or "saving the probe" not in not_authorized:
            issues.append("automationPreference.doesNotAuthorize must include saving the probe")
        if not isinstance(rule, str) or "action-time authorization" not in rule:
            issues.append("automationPreference.rule must require action-time authorization")
    target = handoff.get("target")
    if not isinstance(target, str):
        issues.append("target must be a string")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    if handoff.get("action") != "save_probe":
        issues.append("action must be save_probe")
    suggested = handoff.get("suggestedAuthorizationText")
    if not isinstance(suggested, str) or "保存一次" not in suggested or "捕获保存请求" not in suggested:
        issues.append("suggestedAuthorizationText must name save and request-capture intent")
    command = handoff.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if handoff.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = handoff.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action save_probe" not in gate:
        issues.append("preMutationGateCommand must run the save_probe gate")
    warning = handoff.get("warning")
    if not isinstance(warning, str) or "not user authorization" not in warning:
        issues.append("warning must state this is not user authorization")
    source_files = handoff.get("sourceFiles")
    if not isinstance(source_files, dict) or not source_files.get("createEvidence") or not source_files.get("preflight"):
        issues.append("sourceFiles must include createEvidence and preflight")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a save-probe handoff from create-probe evidence.")
    parser.add_argument("--create-evidence", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--edit-url", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        create_evidence = load_json(Path(args.create_evidence), "create evidence")
        handoff = build_handoff(
            create_evidence=create_evidence,
            create_evidence_path=args.create_evidence,
            preflight_path=args.preflight,
            edit_url=args.edit_url,
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
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
