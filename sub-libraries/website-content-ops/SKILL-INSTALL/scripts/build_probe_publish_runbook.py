#!/usr/bin/env python3
"""Build a local browser runbook for one authorized publish-probe verification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def request_capture_target(summary: dict[str, Any]) -> str:
    request_capture = summary.get("requestCapture")
    if isinstance(request_capture, dict) and isinstance(request_capture.get("url"), str):
        return request_capture["url"]
    return ""


def run_evidence_target(evidence: dict[str, Any]) -> str:
    request_capture = evidence.get("requestCapture")
    if isinstance(request_capture, dict) and isinstance(request_capture.get("url"), str):
        return request_capture["url"]
    sample = evidence.get("sampleVerification")
    if isinstance(sample, dict) and isinstance(sample.get("backendUrl"), str):
        return sample["backendUrl"]
    return ""


def frontend_detail_url(site_key: str, content_type: str) -> str:
    if content_type == "products":
        return f"https://{site_key}.web.allincms.com/products/codex-probe-delete-me-product"
    if content_type == "posts":
        return f"https://{site_key}.web.allincms.com/posts/codex-probe-delete-me-post"
    return f"https://{site_key}.web.allincms.com/{content_type}/codex-probe-delete-me"


def validate_evidence_for_publish(evidence: dict[str, Any], target: str) -> list[str]:
    issues: list[str] = []
    if evidence.get("uploadInScope") is not True:
        issues.append("base evidence must have uploadInScope true after request capture")
    request_capture = evidence.get("requestCapture")
    if not isinstance(request_capture, dict):
        issues.append("base evidence must contain requestCapture")
    else:
        if request_capture.get("persistedVerified") is not True:
            issues.append("requestCapture.persistedVerified must be true before publish")
        url = request_capture.get("url")
        if isinstance(url, str) and target and url != target:
            issues.append("requestCapture.url must match publish target")
    content = evidence.get("contentInspection")
    if not isinstance(content, dict) or content.get("contentType") not in {"posts", "products"}:
        issues.append("publish runbook currently supports posts or products")
    return issues


def build_runbook(
    *,
    run_evidence: dict[str, Any],
    run_evidence_path: str,
    authorization_output: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    target = run_evidence_target(run_evidence)
    if not target:
        raise ValueError("run evidence must include requestCapture.url or sampleVerification.backendUrl")
    parts = parse_edit_url(target)
    content_type = parts["contentType"]
    issues = validate_evidence_for_publish(run_evidence, target)
    if issues:
        raise ValueError("run evidence is not ready for publish_probe:\n" + "\n".join(f"- {issue}" for issue in issues))
    label = CONTENT_LABELS[content_type]
    frontend_url = frontend_detail_url(parts["siteKey"], content_type)
    fields = "publishStatus,frontendVerified"
    expected = f"{content_type} probe published and frontend detail verified"
    verification = "publish probe, verify backend status and frontend detail page"
    cleanup = "request separate cleanup authorization after verification"
    authorization_text = (
        f"授权 Codex 在 {target} 发布 {PROBE_NAME} {label}草稿，用于验证后台发布状态和前台详情页；"
        "本次只允许发布该 probe 并验证，不删除、不批量上传，清理另行授权。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action publish_probe "
        f"--site-key {parts['siteKey']} "
        f"--target {target} "
        f"--target-type {content_type} "
        f"--target-identifier '{PROBE_NAME} {content_type.rstrip('s')} draft' "
        f"--fields-or-files {fields} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{PLACEHOLDER}' "
        f"--output {authorization_output}"
    )
    pre_mutation_gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action publish_probe "
        f"--preflight {run_evidence_path} "
        f"--authorization {authorization_output}"
    )
    return {
        "kind": "allincms_probe_publish_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceRunEvidence": run_evidence_path,
        "siteKey": parts["siteKey"],
        "contentType": content_type,
        "target": target,
        "frontendUrl": frontend_url,
        "action": "publish_probe",
        "authorizationRequired": True,
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustRunBeforeBrowserPublish": [
            "generate authorization record from current user action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "confirm requestCapture.persistedVerified is true",
            "confirm the browser is still on the target edit URL",
            "enable network capture before clicking 发布",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_or_claim_target",
                "mode": "read_only_until_publish_click",
                "target": target,
                "verify": ["URL matches target", "probe title/name and slug are visible", "publish button is visible"],
            },
            {
                "step": "capture_publish_request",
                "mode": "mutating_after_gate",
                "action": "click 发布 exactly once",
                "capture": [
                    "Network request for publish action under the same site/content target",
                    "response status and mime type",
                    "redacted request header names only",
                    "redacted payload top-level keys/shape",
                ],
            },
            {
                "step": "verify_backend_published",
                "mode": "read_only_after_publish",
                "verify": ["backend edit page or list shows published status", "probe name/slug remains unchanged"],
            },
            {
                "step": "verify_frontend_detail",
                "mode": "read_only_after_publish",
                "target": frontend_url,
                "verify": [
                    "frontend detail returns HTTP 200",
                    "title/name renders",
                    "description/body render",
                    "cover/media state is checked or absence is explicitly explained",
                    "no raw Markdown residue is present",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_probe_publish_sample_evidence",
            "contentType": content_type,
            "target": target.replace(parts["contentId"], "{contentId}").replace(parts["siteKey"], "{siteKey}"),
            "backendUrl": target.replace(parts["contentId"], "{contentId}").replace(parts["siteKey"], "{siteKey}"),
            "frontendUrl": frontend_url.replace(parts["siteKey"], "{siteKey}"),
            "authorizationRecord": authorization_output,
            "preMutationGate": "passed|required_before_publish",
            "publishedOnce": False,
            "publishRequestCaptured": False,
            "backendVerified": False,
            "frontendVerified": False,
            "titleOrNameVerified": False,
            "coverOrMediaVerified": False,
            "bodyVerified": False,
            "status": "",
            "renderAudit": "",
            "stopConditionMet": False,
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "deleting or cleaning the probe",
            "uploading media",
            "batch upload or batch publish",
            "JSON/Server Action replay against LAICMS",
            "clicking 发布 more than once unless a new publish authorization is issued",
        ],
        "stopAfter": "backend published state and frontend detail verification captured; do not delete or batch upload",
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "publish_probe authorization record exists and the pre-mutation gate passes."
        ),
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_probe_publish_browser_runbook":
        issues.append("kind must be allincms_probe_publish_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "publish_probe":
        issues.append("action must be publish_probe")
    target = runbook.get("target")
    if not isinstance(target, str):
        issues.append("target must be a string")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    frontend_url = runbook.get("frontendUrl")
    if not isinstance(frontend_url, str):
        issues.append("frontendUrl must be a string")
    else:
        parsed = urlparse(frontend_url)
        if parsed.scheme != "https" or not parsed.netloc.endswith(".web.allincms.com"):
            issues.append("frontendUrl must be an AllinCMS frontend URL")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if runbook.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action publish_probe" not in gate:
        issues.append("preMutationGateCommand must run the publish_probe gate")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include open, publish, backend verify, and frontend verify steps")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false until authorization and gate pass")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("publishedOnce") is not False or template.get("frontendVerified") is not False:
        issues.append("redactedEvidenceTemplate must start unpublished and unverified")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "deleting or cleaning the probe" not in forbidden:
        issues.append("forbiddenActions must include deleting or cleaning the probe")
    elif "publishing the probe" in forbidden:
        issues.append("forbiddenActions must not include publishing the probe; publish is allowed only after the gate passes")
    warning = runbook.get("warning")
    if not isinstance(warning, str) or "local preparation only" not in warning:
        issues.append("warning must state this is local preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook for one publish-probe verification.")
    parser.add_argument("--run-evidence", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.run_evidence), "run evidence")
        runbook = build_runbook(
            run_evidence=evidence,
            run_evidence_path=args.run_evidence,
            authorization_output=args.authorization_output,
        )
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
