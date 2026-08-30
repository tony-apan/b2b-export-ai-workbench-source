#!/usr/bin/env python3
"""Apply a source confirmation next-step handoff for local-only stages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from types import SimpleNamespace
from typing import Any

from prepare_confirmed_site_execution import build as prepare_confirmed_execution
from prepare_source_confirmation_next_step import load_json, validate_handoff


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def parse_shell_command(command: str) -> dict[str, Any]:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise SystemExit(f"ERROR: invalid localCommand shell quoting: {exc}") from None
    if len(parts) < 2 or not parts[0].endswith("python3") and parts[0] != "python":
        raise SystemExit("ERROR: localCommand must start with python/python3")
    if "prepare_confirmed_site_execution.py" not in parts[1]:
        raise SystemExit("ERROR: localCommand must call prepare_confirmed_site_execution.py")
    values: dict[str, Any] = {
        "package": "",
        "review_packet": "",
        "user_confirmation_text": "",
        "output_dir": "",
        "target_mode": "new_site",
        "site_key": "",
        "frontend_base_url": "",
        "accepted_fields": "",
        "accepted_deferral": [],
        "notes": "",
        "create_preflight": "",
        "create_authorization_output": "",
        "fail_if_no_create_handoff": False,
        "json": False,
    }
    flag_map = {
        "--package": "package",
        "--review-packet": "review_packet",
        "--user-confirmation-text": "user_confirmation_text",
        "--output-dir": "output_dir",
        "--target-mode": "target_mode",
        "--site-key": "site_key",
        "--frontend-base-url": "frontend_base_url",
        "--accepted-fields": "accepted_fields",
        "--notes": "notes",
        "--create-preflight": "create_preflight",
        "--create-authorization-output": "create_authorization_output",
        "--create-action-gate-output": "create_authorization_output",
    }
    index = 2
    while index < len(parts):
        token = parts[index]
        if token == "--accepted-deferral":
            if index + 1 >= len(parts):
                raise SystemExit("ERROR: --accepted-deferral is missing a value")
            values["accepted_deferral"].append(parts[index + 1])
            index += 2
            continue
        if token in flag_map:
            if index + 1 >= len(parts):
                raise SystemExit(f"ERROR: {token} is missing a value")
            values[flag_map[token]] = parts[index + 1]
            index += 2
            continue
        if token == "--json":
            values["json"] = True
            index += 1
            continue
        if token == "--fail-if-no-create-handoff":
            values["fail_if_no_create_handoff"] = True
            index += 1
            continue
        raise SystemExit(f"ERROR: unsupported localCommand token: {token}")
    for key in ("package", "review_packet", "user_confirmation_text", "output_dir"):
        if not values[key]:
            raise SystemExit(f"ERROR: localCommand missing --{key.replace('_', '-')}")
    return values


def apply_handoff(args: argparse.Namespace) -> dict[str, Any]:
    handoff_path = Path(args.handoff).expanduser().resolve()
    handoff = load_json(handoff_path, "source confirmation next-step handoff")
    issues = validate_handoff(handoff)
    if issues:
        raise SystemExit("ERROR: invalid source confirmation next-step handoff:\n- " + "\n- ".join(issues))
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    applied_summary: dict[str, Any] | None = None
    status = "blocked"
    if handoff.get("mode") == "await_user_confirmation_text" and handoff.get("localCommandReady") is True:
        parsed = parse_shell_command(str(handoff.get("localCommand") or ""))
        applied_summary = prepare_confirmed_execution(SimpleNamespace(**parsed))
        status = "local_confirmed_execution_prepared"
    elif handoff.get("mode") in {"collect_create_preflight", "run_gated_create_site"}:
        status = "browser_boundary_not_applied"
    else:
        status = "no_local_action_available"

    applied_artifacts = applied_summary.get("artifacts", {}) if isinstance(applied_summary, dict) else {}
    artifacts = {
        "handoff": str(handoff_path),
        "confirmedExecutionSummary": applied_artifacts.get("summary", ""),
        "sourceExecutionStatus": applied_artifacts.get("sourceExecutionStatus", ""),
        "sourceNextStageHandoff": applied_artifacts.get("sourceNextStageHandoff", ""),
    }
    if applied_artifacts:
        for key in (
            "confirmation",
            "executionPlan",
            "artifactReadiness",
            "productsDraftManifest",
            "postsDraftManifest",
            "createSitePreflightBrief",
            "createSitePreflightBriefValidation",
            "createSitePreflightTarget",
            "createSiteHandoff",
            "createSiteHandoffValidation",
            "createSiteRunbook",
            "createSiteRunbookValidation",
            "createdSiteEvidenceBrief",
            "createdSiteEvidenceBundle",
            "createdSiteEvidenceBundleValidation",
            "createdSiteEvidenceTarget",
        ):
            artifacts[key] = applied_artifacts.get(key, "")
    browser_boundary = handoff.get("browserBoundary", {})
    if isinstance(browser_boundary, dict):
        artifacts["browserBoundaryTargetEvidence"] = browser_boundary.get("targetEvidence", "")

    result = {
        "kind": "allincms_source_confirmation_next_step_apply",
        "generatedAt": now_iso(),
        "handoff": str(handoff_path),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "status": status,
        "mode": handoff.get("mode"),
        "appliedConfirmedExecution": bool(applied_summary),
        "confirmedExecutionSummary": applied_summary.get("artifacts", {}).get("summary", "")
        if isinstance(applied_summary, dict)
        else "",
        "sourceExecutionStatus": applied_summary.get("artifacts", {}).get("sourceExecutionStatus", "")
        if isinstance(applied_summary, dict)
        else "",
        "sourceNextStageHandoff": applied_summary.get("artifacts", {}).get("sourceNextStageHandoff", "")
        if isinstance(applied_summary, dict)
        else "",
        "artifacts": artifacts,
        "browserBoundary": browser_boundary,
        "nextAction": applied_summary.get("nextAction", "")
        if isinstance(applied_summary, dict)
        else handoff.get("nextAction", ""),
        "adversarialChecks": [
            "This apply helper executes local confirmed-execution preparation only.",
            "It does not create, save, upload, publish, delete, bind routes, bind domains, or authorize remote mutation.",
            "If status is browser_boundary_not_applied, use the reported browserBoundary with the normal action gate before any browser action.",
        ],
    }
    return result


def validate_apply_result(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("kind") != "allincms_source_confirmation_next_step_apply":
        issues.append("kind must be allincms_source_confirmation_next_step_apply")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if result.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    status = result.get("status")
    if status not in {"local_confirmed_execution_prepared", "browser_boundary_not_applied", "no_local_action_available"}:
        issues.append("status must be a known apply status")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        artifacts = {}
    elif artifacts.get("handoff") != result.get("handoff"):
        issues.append("artifacts.handoff must match handoff")
    if status == "local_confirmed_execution_prepared":
        for key in ("confirmedExecutionSummary", "sourceExecutionStatus", "sourceNextStageHandoff"):
            value = result.get(key)
            if not isinstance(value, str) or not value:
                issues.append(f"{key} is required when local confirmed execution is prepared")
            elif not Path(value).exists():
                issues.append(f"{key} must point to an existing artifact")
            if isinstance(artifacts, dict) and artifacts.get(key) != value:
                issues.append(f"artifacts.{key} must match top-level {key}")
        for key in ("confirmation", "executionPlan", "artifactReadiness"):
            value = artifacts.get(key)
            if not isinstance(value, str) or not value:
                issues.append(f"artifacts.{key} is required when local confirmed execution is prepared")
            elif not Path(value).exists():
                issues.append(f"artifacts.{key} must point to an existing artifact")
    checks = result.get("adversarialChecks")
    if not isinstance(checks, list) or not checks:
        issues.append("adversarialChecks must be a non-empty array")
    elif not any("not" in str(item).lower() and "authorize" in str(item).lower() for item in checks):
        issues.append("adversarialChecks must state the result does not authorize remote mutation")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a source confirmation next-step handoff for local-only stages.")
    parser.add_argument("handoff")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = apply_handoff(args)
    issues = validate_apply_result(result)
    if issues:
        raise SystemExit("ERROR: source confirmation next-step apply result is invalid:\n- " + "\n- ".join(issues))
    write_json(Path(args.output).expanduser().resolve(), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source confirmation next-step apply result: {Path(args.output).expanduser().resolve()}")
        print(f"status={result['status']} nextAction={result['nextAction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
