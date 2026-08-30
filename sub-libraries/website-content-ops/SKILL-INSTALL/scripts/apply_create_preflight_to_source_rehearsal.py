#!/usr/bin/env python3
"""Apply create-site preflight evidence to a source-file rehearsal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from apply_create_preflight_to_confirmed_execution import build as apply_create_preflight
from apply_create_preflight_to_confirmed_execution import validate_apply_result as validate_create_preflight_apply_result


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


def artifact_path(summary: dict[str, Any], key: str) -> str:
    value = as_dict(summary.get("artifacts")).get(key)
    return value if isinstance(value, str) else ""


def require_artifact(summary: dict[str, Any], key: str) -> str:
    value = artifact_path(summary, key)
    if not value:
        raise SystemExit(f"ERROR: source rehearsal summary missing artifacts.{key}")
    if not Path(value).exists():
        raise SystemExit(f"ERROR: source rehearsal artifacts.{key} does not exist: {value}")
    return value


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = Path(args.rehearsal_summary).expanduser().resolve()
    preflight_path = Path(args.create_preflight).expanduser().resolve()
    summary = load_json(summary_path, "source-file rehearsal summary")
    if summary.get("kind") != "allincms_source_file_rehearsal_summary":
        raise SystemExit("ERROR: rehearsal summary kind must be allincms_source_file_rehearsal_summary")
    if summary.get("confirmationPrepared") is not True:
        raise SystemExit("ERROR: source rehearsal must have confirmationPrepared=true")
    if summary.get("readyForBrowserStage") != "needs_create_site_preflight":
        raise SystemExit("ERROR: source rehearsal must be at needs_create_site_preflight")
    confirmed = as_dict(summary.get("confirmedExecution"))
    if confirmed.get("targetMode") not in {"new_site", "create_site", ""}:
        raise SystemExit("ERROR: confirmedExecution.targetMode must be new_site for create preflight apply")

    inner_output_dir = output_dir / "create-site-handoff"
    inner_output = inner_output_dir / "create-preflight-confirmed-execution-apply.json"
    inner_result = apply_create_preflight(
        argparse.Namespace(
            apply_result=require_artifact(summary, "confirmedSourceNextStageHandoff"),
            create_preflight=str(preflight_path),
            output_dir=str(inner_output_dir),
            output=str(inner_output),
            json=False,
        )
    )
    issues = validate_create_preflight_apply_result(inner_result)
    if issues:
        raise SystemExit("ERROR: generated create-preflight apply result is invalid:\n- " + "\n- ".join(issues))
    write_json(inner_output, inner_result)
    artifacts = as_dict(inner_result.get("artifacts"))
    result = {
        "kind": "allincms_create_preflight_source_rehearsal_apply",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourceRehearsalSummary": str(summary_path),
        "createPreflight": str(preflight_path),
        "status": "create_site_handoff_prepared",
        "readyForBrowserStage": inner_result.get("readyForBrowserStage"),
        "targetMode": "new_site",
        "confirmedExecutionSummary": artifacts.get("confirmedExecutionSummary", ""),
        "sourceExecutionStatus": artifacts.get("sourceExecutionStatus", ""),
        "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
        "artifacts": {
            "createPreflightConfirmedExecutionApply": str(inner_output),
            "confirmedExecutionSummary": artifacts.get("confirmedExecutionSummary", ""),
            "sourceExecutionStatus": artifacts.get("sourceExecutionStatus", ""),
            "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
            "confirmation": artifacts.get("confirmation", ""),
            "executionPlan": artifacts.get("executionPlan", ""),
            "artifactReadiness": artifacts.get("artifactReadiness", ""),
            "createSiteHandoff": artifacts.get("createSiteHandoff", ""),
            "createSiteHandoffValidation": artifacts.get("createSiteHandoffValidation", ""),
            "createSiteRunbook": artifacts.get("createSiteRunbook", ""),
            "createSiteRunbookValidation": artifacts.get("createSiteRunbookValidation", ""),
            "createdSiteEvidenceBrief": artifacts.get("createdSiteEvidenceBrief", ""),
            "createdSiteEvidenceBundle": artifacts.get("createdSiteEvidenceBundle", ""),
            "createdSiteEvidenceBundleValidation": artifacts.get("createdSiteEvidenceBundleValidation", ""),
            "createdSiteEvidenceTarget": artifacts.get("createdSiteEvidenceTarget", ""),
        },
        "nextAction": inner_result.get("nextAction", ""),
        "adversarialChecks": [
            "This helper applies read-only create-site preflight evidence to local source artifacts only.",
            "It does not submit the create-site form and does not authorize browser mutation.",
            "The generated create-site runbook remains browserStepsExecutable=false until action-time authorization and the pre-mutation gate pass.",
            "After the one-submit create-site stage, fill the created-site evidence bundle and apply it before schema capture or upload.",
        ],
    }
    result_issues = validate_apply_result(result)
    if result_issues:
        raise SystemExit("ERROR: invalid create-preflight source rehearsal apply result:\n- " + "\n- ".join(result_issues))
    return result


def validate_apply_result(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("kind") != "allincms_create_preflight_source_rehearsal_apply":
        issues.append("kind must be allincms_create_preflight_source_rehearsal_apply")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if result.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    if result.get("status") != "create_site_handoff_prepared":
        issues.append("status must be create_site_handoff_prepared")
    if result.get("readyForBrowserStage") != "create_site_handoff_ready":
        issues.append("readyForBrowserStage must be create_site_handoff_ready")
    if result.get("targetMode") != "new_site":
        issues.append("targetMode must be new_site")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        return issues
    for key in (
        "createPreflightConfirmedExecutionApply",
        "confirmedExecutionSummary",
        "sourceExecutionStatus",
        "sourceNextStageHandoff",
        "confirmation",
        "executionPlan",
        "artifactReadiness",
        "createSiteHandoff",
        "createSiteHandoffValidation",
        "createSiteRunbook",
        "createSiteRunbookValidation",
        "createdSiteEvidenceBrief",
        "createdSiteEvidenceBundle",
        "createdSiteEvidenceBundleValidation",
        "createdSiteEvidenceTarget",
    ):
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"artifacts.{key} is required")
        elif key != "createdSiteEvidenceTarget" and not Path(value).exists():
            issues.append(f"artifacts.{key} must exist")
    for key in ("confirmedExecutionSummary", "sourceExecutionStatus", "sourceNextStageHandoff"):
        if result.get(key) != artifacts.get(key):
            issues.append(f"{key} must mirror artifacts.{key}")
    checks = result.get("adversarialChecks")
    if not isinstance(checks, list) or not checks:
        issues.append("adversarialChecks must be a non-empty array")
    elif not any("does not" in item.lower() and "authorize" in item.lower() for item in checks if isinstance(item, str)):
        issues.append("adversarialChecks must state the result does not authorize browser mutation")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply create-site preflight evidence to source-file rehearsal artifacts.")
    parser.add_argument("--rehearsal-summary", required=True)
    parser.add_argument("--create-preflight", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(args)
    output = Path(args.output).expanduser().resolve() if args.output else Path(args.output_dir).expanduser().resolve() / "create-preflight-source-rehearsal-apply.json"
    write_json(output, result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote create-preflight source rehearsal apply result: {output}")
        print(f"readyForBrowserStage={result['readyForBrowserStage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
