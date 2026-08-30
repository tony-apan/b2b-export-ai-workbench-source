#!/usr/bin/env python3
"""Prepare or validate create-site authorization from a confirmed create-site runbook."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES, validate_create_site_gate
from make_authorization_record import build_record as build_authorization_record
from make_authorization_record import validate_record as validate_authorization_record


AUTH_PLACEHOLDER = "<paste current user authorization text here>"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def runbook_path_from_apply_result(data: dict[str, Any]) -> str:
    artifacts = as_dict(data.get("artifacts"))
    return str(artifacts.get("createSiteRunbook") or "")


def create_site_continuation_artifacts(data: dict[str, Any]) -> dict[str, str]:
    artifacts = as_dict(data.get("artifacts"))
    return {
        "createdSiteEvidenceBundle": str(artifacts.get("createdSiteEvidenceBundle") or ""),
        "createdSiteEvidenceTarget": str(artifacts.get("createdSiteEvidenceTarget") or ""),
    }


def suggested_authorization_text(site_name: str) -> str:
    return (
        "I authorize Codex to create the site "
        f"{site_name!r} at https://workspace.laicms.com/sites using the confirmed name and description only; "
        "stop after the create-site submit and created-site evidence capture."
    )


def build_authorization_args(runbook: dict[str, Any], authorization_source: str, authorization_output: str) -> SimpleNamespace:
    site = as_dict(runbook.get("siteProposal"))
    site_name = str(site.get("siteName", "")).strip()
    return SimpleNamespace(
        action="create_site",
        site_key="",
        target="https://workspace.laicms.com/sites",
        target_type="site",
        target_identifier=site_name,
        fields_or_files="name,description",
        expected_result=f"site {site_name} is created once and created-site evidence is captured",
        verification_plan=(
            "verify created site key, backend dashboard URL, frontend base URL, module routes, "
            "and submitted name/description before any content upload or publish"
        ),
        cleanup_plan="no cleanup in this authorization; rollback/delete requires a separate explicit action",
        authorization_source=authorization_source,
        output=authorization_output,
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.runbook:
        runbook_path = Path(args.runbook).expanduser().resolve()
        continuation_artifacts = {}
    else:
        apply_result = load_json(Path(args.apply_result).expanduser().resolve(), "create-site apply result")
        runbook_path_value = runbook_path_from_apply_result(apply_result)
        if not runbook_path_value:
            raise SystemExit("ERROR: apply result does not expose artifacts.createSiteRunbook")
        runbook_path = Path(runbook_path_value).expanduser().resolve()
        continuation_artifacts = create_site_continuation_artifacts(apply_result)

    runbook = load_json(runbook_path, "create-site runbook")
    if runbook.get("kind") != "allincms_create_site_browser_runbook":
        raise SystemExit("ERROR: runbook.kind must be allincms_create_site_browser_runbook")
    if runbook.get("browserStepsExecutable") is not False:
        raise SystemExit("ERROR: runbook.browserStepsExecutable must be false before action-time gate")
    preflight_path = Path(str(runbook.get("preflight") or "")).expanduser().resolve()
    preflight = load_json(preflight_path, "create-site preflight")
    site = as_dict(runbook.get("siteProposal"))
    site_name = str(site.get("siteName", "")).strip()
    if not site_name:
        raise SystemExit("ERROR: runbook.siteProposal.siteName is required")
    created_site_evidence_target = str(
        continuation_artifacts.get("createdSiteEvidenceTarget")
        or runbook.get("createdSiteEvidenceTarget")
        or runbook.get("createdSiteEvidenceOutput")
        or ""
    )

    authorization_output = Path(args.authorization_output or runbook.get("authorizationRecord") or output_dir / "authorization-create-site.json")
    authorization_output = authorization_output.expanduser().resolve()
    suggested_text = suggested_authorization_text(site_name)
    authorization_source = args.user_authorization_text.strip()
    authorization_record_path = ""
    authorization_validation_issues: list[str] = []
    gate_issues: list[str] = []
    status = "awaiting_user_authorization"
    if authorization_source:
        try:
            record = build_authorization_record(
                build_authorization_args(runbook, authorization_source, str(authorization_output))
            )
            authorization_validation_issues = validate_authorization_record(record)
        except ValueError as exc:
            record = {}
            authorization_validation_issues = [str(exc)]
        if authorization_validation_issues:
            status = "authorization_record_invalid"
        else:
            write_json(authorization_output, record)
            authorization_record_path = str(authorization_output)
            gate_issues = validate_create_site_gate(
                preflight,
                record,
                max_age_minutes=args.max_age_minutes,
                expected_target_identifier=site_name,
            )
            status = "pre_mutation_gate_passed" if not gate_issues else "pre_mutation_gate_failed"

    result = {
        "kind": "allincms_create_site_authorization_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "status": status,
        "runbook": str(runbook_path),
        "preflight": str(preflight_path),
        "authorizationRecord": authorization_record_path,
        "authorizationRecordTarget": str(authorization_output),
        "target": "https://workspace.laicms.com/sites",
        "action": "create_site",
        "targetIdentifier": site_name,
        "fieldsOrFiles": ["name", "description"],
        "suggestedAuthorizationText": suggested_text,
        "authorizationRecordCommandTemplate": str(runbook.get("authorizationRecordCommand") or ""),
        "preMutationGateCommand": str(runbook.get("preMutationGateCommand") or ""),
        "gateReadyForBrowserSubmit": status == "pre_mutation_gate_passed",
        "artifacts": {
            "runbook": str(runbook_path),
            "preflight": str(preflight_path),
            "authorizationRecord": authorization_record_path,
            "authorizationRecordTarget": str(authorization_output),
            "createdSiteEvidenceBundle": str(
                continuation_artifacts.get("createdSiteEvidenceBundle")
                or runbook.get("createdSiteEvidenceBundle")
                or ""
            ),
            "createdSiteEvidenceTarget": created_site_evidence_target,
        },
        "validation": {
            "authorizationRecordIssues": authorization_validation_issues,
            "preMutationGateIssues": gate_issues,
            "maxAgeMinutes": args.max_age_minutes,
        },
        "nextAction": (
            "run the create-site browser runbook submit step, then fill created-site evidence"
            if status == "pre_mutation_gate_passed"
            else "ask for exact action-time create-site authorization text, then rerun this helper with --user-authorization-text"
        ),
        "adversarialChecks": [
            "This helper prepares or validates local authorization artifacts only.",
            "It does not submit the create-site form and does not make the runbook executable.",
            "The authorization record is written only when current user authorization text is supplied and validates.",
            "Passing the pre-mutation gate permits only the one create-site submit described by the runbook; uploads, publishing, themes, domains, and tracking remain forbidden.",
        ],
    }
    issues = validate_preparation(result)
    if issues:
        raise SystemExit("ERROR: invalid create-site authorization preparation:\n- " + "\n- ".join(issues))
    return result


def validate_preparation(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("kind") != "allincms_create_site_authorization_preparation":
        issues.append("kind must be allincms_create_site_authorization_preparation")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if result.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    status = result.get("status")
    if status not in {
        "awaiting_user_authorization",
        "authorization_record_invalid",
        "pre_mutation_gate_failed",
        "pre_mutation_gate_passed",
    }:
        issues.append("status is invalid")
    for key in ("runbook", "preflight"):
        value = result.get(key)
        if not isinstance(value, str) or not value:
            issues.append(f"{key} is required")
        elif not Path(value).exists():
            issues.append(f"{key} must point to an existing artifact")
    if result.get("action") != "create_site":
        issues.append("action must be create_site")
    if result.get("target") != "https://workspace.laicms.com/sites":
        issues.append("target must be https://workspace.laicms.com/sites")
    if not isinstance(result.get("targetIdentifier"), str) or not result["targetIdentifier"].strip():
        issues.append("targetIdentifier is required")
    command = result.get("authorizationRecordCommandTemplate")
    if not isinstance(command, str) or AUTH_PLACEHOLDER not in command:
        issues.append("authorizationRecordCommandTemplate must keep the authorization placeholder")
    gate_command = result.get("preMutationGateCommand")
    if not isinstance(gate_command, str) or "--action create_site" not in gate_command:
        issues.append("preMutationGateCommand must use --action create_site")
    validation = as_dict(result.get("validation"))
    artifacts = as_dict(result.get("artifacts"))
    if not artifacts:
        issues.append("artifacts must be a non-empty object")
    else:
        for key in ("runbook", "preflight", "authorizationRecordTarget"):
            value = artifacts.get(key)
            if value != result.get(key):
                issues.append(f"artifacts.{key} must match top-level {key}")
        if artifacts.get("authorizationRecord") != result.get("authorizationRecord"):
            issues.append("artifacts.authorizationRecord must match top-level authorizationRecord")
        for key in ("createdSiteEvidenceBundle", "createdSiteEvidenceTarget"):
            value = artifacts.get(key)
            if value is not None and not isinstance(value, str):
                issues.append(f"artifacts.{key} must be a string when present")
    if status == "pre_mutation_gate_passed":
        if not result.get("authorizationRecord") or not Path(str(result["authorizationRecord"])).exists():
            issues.append("authorizationRecord must exist when gate passed")
        if result.get("gateReadyForBrowserSubmit") is not True:
            issues.append("gateReadyForBrowserSubmit must be true when gate passed")
        if validation.get("authorizationRecordIssues") or validation.get("preMutationGateIssues"):
            issues.append("validation issues must be empty when gate passed")
    else:
        if result.get("gateReadyForBrowserSubmit") is not False:
            issues.append("gateReadyForBrowserSubmit must be false until gate passes")
    checks = result.get("adversarialChecks")
    if not isinstance(checks, list) or not checks:
        issues.append("adversarialChecks must be a non-empty array")
    elif not any("not" in item.lower() and "submit" in item.lower() for item in checks if isinstance(item, str)):
        issues.append("adversarialChecks must state the helper does not submit the form")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare create-site authorization from a confirmed create-site runbook.")
    parser.add_argument("--apply-result", default="", help="create-preflight apply result with artifacts.createSiteRunbook")
    parser.add_argument("--runbook", default="", help="direct create-site browser runbook path")
    parser.add_argument("--user-authorization-text", default="")
    parser.add_argument("--authorization-output", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.apply_result and not args.runbook:
        raise SystemExit("ERROR: provide --apply-result or --runbook")
    result = build(args)
    write_json(Path(args.output).expanduser().resolve(), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote create-site authorization preparation: {Path(args.output).expanduser().resolve()}")
        print(f"status={result['status']} gateReadyForBrowserSubmit={result['gateReadyForBrowserSubmit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
