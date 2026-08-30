#!/usr/bin/env python3
"""Build a local browser runbook for one authorized probe cleanup."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
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


def cleanup_target(evidence: dict[str, Any]) -> str:
    sample = evidence.get("sampleVerification")
    if isinstance(sample, dict) and isinstance(sample.get("backendUrl"), str):
        return sample["backendUrl"]
    request_capture = evidence.get("requestCapture")
    if isinstance(request_capture, dict) and isinstance(request_capture.get("url"), str):
        return request_capture["url"]
    return ""


def validate_evidence_for_cleanup(evidence: dict[str, Any], target: str) -> list[str]:
    issues: list[str] = []
    sample = evidence.get("sampleVerification")
    if not isinstance(sample, dict):
        issues.append("base evidence must contain sampleVerification before cleanup")
    else:
        for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified"):
            if sample.get(key) is not True:
                issues.append(f"sampleVerification.{key} must be true before cleanup")
        if isinstance(sample.get("backendUrl"), str) and target and sample["backendUrl"] != target:
            issues.append("sampleVerification.backendUrl must match cleanup target")
    content = evidence.get("contentInspection")
    if not isinstance(content, dict) or content.get("contentType") not in {"posts", "products", "forms"}:
        issues.append("cleanup runbook supports posts, products, or forms")
    return issues


def build_runbook(
    *,
    run_evidence: dict[str, Any],
    run_evidence_path: str,
    authorization_output: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    target = cleanup_target(run_evidence)
    if not target:
        raise ValueError("run evidence must include sampleVerification.backendUrl or requestCapture.url")
    parts = parse_edit_url(target)
    content_type = parts["contentType"]
    issues = validate_evidence_for_cleanup(run_evidence, target)
    if issues:
        raise ValueError("run evidence is not ready for cleanup_probe:\n" + "\n".join(f"- {issue}" for issue in issues))
    label = CONTENT_LABELS[content_type]
    fields = "cleanedCandidates,backendVerified,frontendVerified"
    expected = f"{content_type} probe cleaned and frontend no longer renders probe"
    verification = "delete or unpublish probe, verify backend absence and frontend 404"
    authorization_text = (
        f"授权 Codex 在 {target} 清理 {PROBE_NAME} {label}测试项，"
        "允许删除或取消发布该 probe，并验证后台不存在、前台不再渲染；"
        "本次只允许清理 probe，不影响真实业务内容。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action cleanup_probe "
        f"--site-key {parts['siteKey']} "
        f"--target {target} "
        f"--target-type {content_type} "
        f"--target-identifier '{PROBE_NAME} {content_type.rstrip('s')} draft' "
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
        f"--preflight {run_evidence_path} "
        f"--authorization {authorization_output}"
    )
    frontend_url = ""
    sample = run_evidence.get("sampleVerification")
    if isinstance(sample, dict) and isinstance(sample.get("frontendUrl"), str):
        frontend_url = sample["frontendUrl"]
    return {
        "kind": "allincms_probe_cleanup_browser_runbook",
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
        "action": "cleanup_probe",
        "authorizationRequired": True,
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustRunBeforeBrowserCleanup": [
            "generate authorization record from current user action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "confirm sampleVerification backend/frontend proof exists",
            "confirm cleanup candidate is the Codex Probe item, not business content",
            "enable network capture before delete/unpublish",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_or_claim_target",
                "mode": "read_only_until_cleanup_click",
                "target": target,
                "verify": ["URL matches target", "probe title/name and slug are visible", "status/control allows cleanup"],
            },
            {
                "step": "cleanup_probe",
                "mode": "mutating_after_gate",
                "action": "delete or unpublish exactly the Codex Probe item once",
                "capture": [
                    "Network request for delete/unpublish action under the same site/content target",
                    "response status and mime type",
                    "redacted request header names only",
                    "redacted payload top-level keys/shape",
                ],
            },
            {
                "step": "verify_backend_absence",
                "mode": "read_only_after_cleanup",
                "verify": ["backend list/search no longer shows the probe or shows it unpublished as intended"],
            },
            {
                "step": "verify_frontend_non_public",
                "mode": "read_only_after_cleanup",
                "target": frontend_url,
                "verify": ["frontend detail returns 404 or no longer renders the probe content"],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_probe_cleanup_evidence",
            "contentType": content_type,
            "target": target.replace(parts["contentId"], "{contentId}").replace(parts["siteKey"], "{siteKey}"),
            "authorizationRecord": authorization_output,
            "preMutationGate": "passed|required_before_cleanup",
            "cleanupAction": "",
            "cleanedCandidates": [],
            "cleanedCount": 0,
            "backendVerified": False,
            "frontendVerified": False,
            "backendEvidence": "",
            "frontendEvidence": "",
            "stopConditionMet": False,
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "cleaning any non-probe business content",
            "uploading media",
            "batch upload or batch publish",
            "JSON/Server Action replay against LAICMS",
            "running a second cleanup action unless a new cleanup authorization is issued",
        ],
        "stopAfter": "probe cleanup and backend/frontend non-public proof captured",
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "cleanup_probe authorization record exists and the pre-mutation gate passes."
        ),
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_probe_cleanup_browser_runbook":
        issues.append("kind must be allincms_probe_cleanup_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "cleanup_probe":
        issues.append("action must be cleanup_probe")
    target = runbook.get("target")
    if not isinstance(target, str):
        issues.append("target must be a string")
    else:
        try:
            parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if runbook.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action cleanup_probe" not in gate:
        issues.append("preMutationGateCommand must run the cleanup_probe gate")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include open, cleanup, backend verify, and frontend verify steps")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false until authorization and gate pass")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("cleanedCount") != 0 or template.get("backendVerified") is not False:
        issues.append("redactedEvidenceTemplate must start uncleaned and unverified")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "cleaning any non-probe business content" not in forbidden:
        issues.append("forbiddenActions must include cleaning any non-probe business content")
    warning = runbook.get("warning")
    if not isinstance(warning, str) or "local preparation only" not in warning:
        issues.append("warning must state this is local preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook for one probe cleanup.")
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
