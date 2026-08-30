#!/usr/bin/env python3
"""Validate a save-probe browser runbook before any browser mutation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from build_probe_save_runbook import validate_runbook, validate_supported_handoff
from check_pre_mutation_gate import validate_save_probe_gate
from make_authorization_record import validate_record as validate_authorization_record
from prepare_probe_save_handoff import PLACEHOLDER, parse_edit_url


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


def parse_now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must include a timezone")
    return parsed.astimezone(timezone.utc)


def _same_path(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return str(Path(left)) == str(Path(right))


def build_report(
    runbook_path: str,
    *,
    expect_missing_authorization: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    blockers: list[str] = []
    checks: dict[str, Any] = {
        "runbookValid": False,
        "handoffValid": False,
        "preflightExists": False,
        "authorizationRecordExists": False,
        "authorizationRecordValid": False,
        "saveGatePassed": False,
        "redactedEvidenceStartsUnsaved": False,
        "browserStepsExecutableBeforeGate": False,
    }

    runbook = load_json(Path(runbook_path), "runbook")
    runbook_issues = validate_runbook(runbook)
    if runbook_issues:
        issues.extend(f"runbook: {issue}" for issue in runbook_issues)
    else:
        checks["runbookValid"] = True

    target = runbook.get("target")
    target_parts: dict[str, str] = {}
    if isinstance(target, str):
        try:
            target_parts = parse_edit_url(target)
        except ValueError as exc:
            issues.append(f"runbook.target: {exc}")
    else:
        issues.append("runbook.target must be a string")

    template = runbook.get("redactedEvidenceTemplate")
    if isinstance(template, dict):
        checks["redactedEvidenceStartsUnsaved"] = (
            template.get("savedOnce") is False
            and template.get("published") is False
            and template.get("backendPersisted") is False
            and template.get("stopConditionMet") is False
        )
        if not checks["redactedEvidenceStartsUnsaved"]:
            issues.append("redactedEvidenceTemplate must start unsaved, unpublished, unpersisted, and incomplete")
    else:
        issues.append("redactedEvidenceTemplate must be an object")

    if runbook.get("browserStepsExecutable") is True:
        checks["browserStepsExecutableBeforeGate"] = True
        issues.append("browserStepsExecutable must not be true before authorization and pre-mutation gate pass")

    handoff_path = str(runbook.get("sourceHandoff", ""))
    handoff: dict[str, Any] | None = None
    if not handoff_path:
        issues.append("sourceHandoff is required")
    else:
        try:
            handoff = load_json(Path(handoff_path), "handoff")
        except ValueError as exc:
            issues.append(str(exc))
        else:
            handoff_issues = validate_supported_handoff(handoff)
            if handoff_issues:
                issues.extend(f"handoff: {issue}" for issue in handoff_issues)
            else:
                checks["handoffValid"] = True
            if handoff.get("target") != runbook.get("target"):
                issues.append("handoff.target must match runbook.target")
            if handoff.get("action") != "save_probe":
                issues.append("handoff.action must be save_probe")
            command = handoff.get("authorizationRecordCommand")
            if not isinstance(command, str) or PLACEHOLDER not in command:
                issues.append("handoff authorizationRecordCommand must retain the current-user placeholder")

    preflight_path = ""
    authorization_path = ""
    if handoff:
        source_files = handoff.get("sourceFiles")
        if isinstance(source_files, dict):
            preflight_path = str(source_files.get("preflight", ""))
            authorization_path = str(source_files.get("authorizationOutput", ""))
    if isinstance(template, dict):
        template_authorization_path = str(template.get("authorizationRecord", ""))
        if authorization_path and template_authorization_path and not _same_path(authorization_path, template_authorization_path):
            issues.append("runbook redactedEvidenceTemplate.authorizationRecord must match handoff authorizationOutput")
        authorization_path = authorization_path or template_authorization_path

    preflight: dict[str, Any] | None = None
    if not preflight_path:
        issues.append("handoff.sourceFiles.preflight is required")
    else:
        try:
            preflight = load_json(Path(preflight_path), "preflight")
        except ValueError as exc:
            issues.append(str(exc))
        else:
            checks["preflightExists"] = True
            site_identity = preflight.get("siteIdentity")
            content_inspection = preflight.get("contentInspection")
            if target_parts and isinstance(site_identity, dict) and site_identity.get("siteKey") != target_parts["siteKey"]:
                issues.append("preflight.siteIdentity.siteKey must match runbook target")
            if target_parts and isinstance(content_inspection, dict) and content_inspection.get("contentType") != target_parts["contentType"]:
                issues.append("preflight.contentInspection.contentType must match runbook target")

    authorization: dict[str, Any] | None = None
    if not authorization_path:
        blockers.append("authorization_output_path_missing")
    elif not Path(authorization_path).exists():
        blockers.append("authorization_record_missing")
        if not expect_missing_authorization:
            issues.append("authorization record is missing; pass --expect-missing-authorization only for local preparation")
    else:
        checks["authorizationRecordExists"] = True
        authorization = load_json(Path(authorization_path), "authorization")
        auth_issues = validate_authorization_record(authorization)
        if auth_issues:
            issues.extend(f"authorization: {issue}" for issue in auth_issues)
        else:
            checks["authorizationRecordValid"] = True

    gate_errors: list[str] = []
    if preflight is not None and authorization is not None:
        if isinstance(target, str) and authorization.get("target") != target:
            issues.append("authorization.target must match runbook.target")
        gate_errors = validate_save_probe_gate(preflight, authorization, now=now)
        if gate_errors:
            blockers.append("pre_mutation_gate_failed")
            issues.extend(f"save gate: {issue}" for issue in gate_errors)
        else:
            checks["saveGatePassed"] = True

    if issues:
        status = "invalid"
    elif checks["saveGatePassed"]:
        status = "ready_after_gate"
    elif "authorization_record_missing" in blockers:
        status = "blocked_missing_authorization"
    elif blockers:
        status = "blocked"
    else:
        status = "blocked_gate_not_run"

    return {
        "kind": "allincms_probe_save_runbook_validation",
        "runbook": runbook_path,
        "valid": not issues,
        "status": status,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "action": "save_probe",
        "target": runbook.get("target"),
        "contentType": runbook.get("contentType"),
        "checks": checks,
        "blockers": blockers,
        "issues": issues,
        "expectedMissingAuthorization": expect_missing_authorization,
        "browserStepsExecutable": checks["saveGatePassed"],
        "nextActions": [
            "Create an action-time authorization record from current user text and rerun this validator."
            if status == "blocked_missing_authorization"
            else "Run the save_probe browser steps exactly once and capture redacted persistence evidence."
            if status == "ready_after_gate"
            else "Fix validation issues before touching the browser."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a save-probe runbook before browser execution.")
    parser.add_argument("runbook_json")
    parser.add_argument("--output", help="Path to write validation report JSON")
    parser.add_argument("--expect-missing-authorization", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    parser.add_argument("--now", help="ISO timestamp for deterministic freshness checks")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        report = build_report(
            args.runbook_json,
            expect_missing_authorization=args.expect_missing_authorization,
            now=parse_now(args.now),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.output:
        print(f"Wrote {args.output}")

    if not report["valid"]:
        return 2
    if args.fail_on_blocked and report["status"] != "ready_after_gate":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
