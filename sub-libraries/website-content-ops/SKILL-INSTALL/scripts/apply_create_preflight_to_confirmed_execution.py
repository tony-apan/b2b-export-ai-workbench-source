#!/usr/bin/env python3
"""Apply read-only create-site preflight evidence to confirmed execution artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from prepare_confirmed_site_execution import build as prepare_confirmed_execution
from validate_run_evidence import validate as validate_run_evidence


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


def continuation_paths(data: dict[str, Any]) -> dict[str, str]:
    kind = data.get("kind")
    if kind == "allincms_source_next_stage_handoff":
        context = as_dict(data.get("contextPaths"))
        return {
            "confirmation": str(context.get("confirmation") or ""),
            "executionPlan": str(context.get("execution_plan") or ""),
            "createActionGateOutput": "",
        }
    artifacts = as_dict(data.get("artifacts"))
    return {
        "confirmation": str(artifacts.get("confirmation") or ""),
        "executionPlan": str(artifacts.get("executionPlan") or ""),
        "createActionGateOutput": str(artifacts.get("createActionGateOutput") or ""),
    }


def deferral_arg(item: dict[str, Any]) -> str:
    return f"{item.get('field', '')}|{item.get('decision', '')}|{item.get('reason', '')}"


def validate_preflight(data: dict[str, Any]) -> list[str]:
    issues = validate_run_evidence(data)
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict):
        issues.append("siteCreation must be an object")
    elif site_creation.get("status") != "create_preflight_verified":
        issues.append("siteCreation.status must be create_preflight_verified")
    if data.get("completionClaimed") is not False:
        issues.append("completionClaimed must be false for create-site preflight evidence")
    return issues


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    apply_result_path = Path(args.apply_result).expanduser().resolve()
    preflight_path = Path(args.create_preflight).expanduser().resolve()
    apply_result = load_json(apply_result_path, "source confirmation apply result or source next-stage handoff")
    preflight = load_json(preflight_path, "create-site preflight evidence")
    preflight_issues = validate_preflight(preflight)
    if preflight_issues:
        raise SystemExit("ERROR: invalid create-site preflight evidence:\n- " + "\n- ".join(preflight_issues))

    paths = continuation_paths(apply_result)
    confirmation_path = paths["confirmation"]
    if not confirmation_path:
        raise SystemExit(
            "ERROR: input must expose a confirmation path via artifacts.confirmation "
            "or contextPaths.confirmation"
        )
    confirmation = load_json(Path(confirmation_path), "confirmation")
    for key in ("sourcePackage", "sourceReviewPacket", "userConfirmationText"):
        if not isinstance(confirmation.get(key), str) or not confirmation[key].strip():
            raise SystemExit(f"ERROR: confirmation.{key} is required")
    accepted_fields = ",".join(
        item.strip()
        for item in confirmation.get("acceptedFields", [])
        if isinstance(item, str) and item.strip()
    )
    accepted_deferrals = [
        deferral_arg(item)
        for item in confirmation.get("acceptedDeferrals", [])
        if isinstance(item, dict) and item.get("field") and item.get("decision") and item.get("reason")
    ]
    target_mode = "new_site"
    execution_plan_path = paths["executionPlan"]
    if execution_plan_path:
        execution_plan = load_json(Path(execution_plan_path), "execution plan")
        if execution_plan.get("targetMode") == "existing_site":
            raise SystemExit("ERROR: create-site preflight cannot be applied to an existing_site execution plan")
        target_mode = str(execution_plan.get("targetMode") or "new_site")

    create_authorization_output = paths["createActionGateOutput"]
    if not create_authorization_output:
        create_authorization_output = str(output_dir / "authorization-create-site.json")

    confirmed_summary = prepare_confirmed_execution(
        SimpleNamespace(
            package=confirmation["sourcePackage"],
            review_packet=confirmation["sourceReviewPacket"],
            user_confirmation_text=confirmation["userConfirmationText"],
            output_dir=str(output_dir / "confirmed-execution-with-preflight"),
            target_mode=target_mode,
            site_key="",
            frontend_base_url="",
            accepted_fields=accepted_fields,
            accepted_deferral=accepted_deferrals,
            notes=str(confirmation.get("notes") or ""),
            create_preflight=str(preflight_path),
            create_authorization_output=create_authorization_output,
            fail_if_no_create_handoff=False,
            json=False,
        )
    )
    result = {
        "kind": "allincms_create_preflight_confirmed_execution_apply",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourceApplyResult": str(apply_result_path),
        "createPreflight": str(preflight_path),
        "status": "create_site_handoff_prepared",
        "readyForBrowserStage": confirmed_summary.get("readyForBrowserStage"),
        "confirmedExecutionSummary": confirmed_summary.get("artifacts", {}).get("summary", ""),
        "sourceExecutionStatus": confirmed_summary.get("artifacts", {}).get("sourceExecutionStatus", ""),
        "sourceNextStageHandoff": confirmed_summary.get("artifacts", {}).get("sourceNextStageHandoff", ""),
        "artifacts": {
            "confirmedExecutionSummary": confirmed_summary.get("artifacts", {}).get("summary", ""),
            "sourceExecutionStatus": confirmed_summary.get("artifacts", {}).get("sourceExecutionStatus", ""),
            "sourceNextStageHandoff": confirmed_summary.get("artifacts", {}).get("sourceNextStageHandoff", ""),
            "confirmation": confirmed_summary.get("artifacts", {}).get("confirmation", ""),
            "executionPlan": confirmed_summary.get("artifacts", {}).get("executionPlan", ""),
            "artifactReadiness": confirmed_summary.get("artifacts", {}).get("artifactReadiness", ""),
            "createSiteHandoff": confirmed_summary.get("artifacts", {}).get("createSiteHandoff", ""),
            "createSiteHandoffValidation": confirmed_summary.get("artifacts", {}).get("createSiteHandoffValidation", ""),
            "createSiteRunbook": confirmed_summary.get("artifacts", {}).get("createSiteRunbook", ""),
            "createSiteRunbookValidation": confirmed_summary.get("artifacts", {}).get("createSiteRunbookValidation", ""),
            "createdSiteEvidenceBrief": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBrief", ""),
            "createdSiteEvidenceBundle": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBundle", ""),
            "createdSiteEvidenceBundleValidation": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBundleValidation", ""),
            "createdSiteEvidenceTarget": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceTarget", ""),
        },
        "nextAction": confirmed_summary.get("nextAction", ""),
        "adversarialChecks": [
            "This helper consumes read-only create-site preflight evidence and prepares local handoff/runbook artifacts only.",
            "It does not submit the create-site form and does not authorize remote mutation.",
            "Use the generated create-site runbook only after action-time authorization and check_pre_mutation_gate.py pass.",
        ],
    }
    issues = validate_apply_result(result)
    if issues:
        raise SystemExit("ERROR: invalid create-preflight apply result:\n- " + "\n- ".join(issues))
    return result


def validate_apply_result(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("kind") != "allincms_create_preflight_confirmed_execution_apply":
        issues.append("kind must be allincms_create_preflight_confirmed_execution_apply")
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
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        artifacts = {}
    for key in (
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
        if not isinstance(value, str) or not value:
            issues.append(f"artifacts.{key} is required")
        elif key != "createdSiteEvidenceTarget" and not Path(value).exists():
            issues.append(f"artifacts.{key} must point to an existing artifact")
    for key in ("confirmedExecutionSummary", "sourceExecutionStatus", "sourceNextStageHandoff"):
        if result.get(key) != artifacts.get(key):
            issues.append(f"{key} must match artifacts.{key}")
    checks = result.get("adversarialChecks")
    if not isinstance(checks, list) or not checks:
        issues.append("adversarialChecks must be a non-empty array")
    elif not any("not" in item.lower() and "authorize" in item.lower() for item in checks if isinstance(item, str)):
        issues.append("adversarialChecks must state the result does not authorize remote mutation")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply create-site preflight evidence to confirmed execution artifacts.")
    parser.add_argument("--apply-result", required=True, help="Source confirmation next-step apply-result.json")
    parser.add_argument("--create-preflight", required=True, help="Filled create-site preflight evidence JSON")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build(args)
    write_json(Path(args.output).expanduser().resolve(), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote create-preflight confirmed execution apply result: {Path(args.output).expanduser().resolve()}")
        print(f"readyForBrowserStage={result['readyForBrowserStage']} nextAction={result['nextAction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
