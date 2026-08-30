#!/usr/bin/env python3
"""Build or update AllinCMS module-capture coverage from a capture plan and one result."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


VALID_RESULT_STATUSES = {"captured", "blocked", "not_applicable"}
SIMULATED_SITE_KEYS = ("simsite01", "codexsimulatedsite")
EVIDENCE_POINTER_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|/|\.{1,2}/).+")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_key(module: str, action: str) -> str:
    return f"{module}:{action}"


def split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()] if raw else []


def is_evidence_pointer(value: str) -> bool:
    return bool(EVIDENCE_POINTER_RE.match(value.strip()))


def plan_stages(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if plan.get("kind") != "allincms_module_capture_plan":
        raise ValueError("capture plan kind must be allincms_module_capture_plan")
    stages = plan.get("stages")
    if not isinstance(stages, list):
        raise ValueError("capture plan stages must be an array")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise ValueError(f"capture plan stages[{index}] must be an object")
        module = str(stage.get("module", "")).strip()
        action = str(stage.get("action", "")).strip()
        if not module or not action:
            raise ValueError(f"capture plan stages[{index}] must include module and action")
        key = stage_key(module, action)
        if key in seen:
            raise ValueError(f"duplicate capture stage: {key}")
        seen.add(key)
        normalized.append(stage)
    return normalized


def empty_coverage(plan: dict[str, Any]) -> dict[str, Any]:
    stages = []
    for stage in plan_stages(plan):
        module = str(stage["module"])
        action = str(stage["action"])
        stages.append(
            {
                "stageKey": stage_key(module, action),
                "group": stage.get("group", ""),
                "module": module,
                "action": action,
                "authorizationAction": stage.get("authorizationAction", ""),
                "status": "pending",
                "requiredProof": list(stage.get("requiredProof", [])),
                "proofRecorded": [],
                "redactedEvidencePointers": [],
                "blockingIssues": [],
                "lastUpdatedAt": "",
            }
        )
    pending_stage_keys = [stage["stageKey"] for stage in stages]
    return {
        "kind": "allincms_module_capture_coverage",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePlanKind": plan.get("kind"),
        "siteKeyTemplate": "{realSiteKey}",
        "jsonReplayReady": False,
        "interfaceCoverageComplete": False,
        "actionReplayContractsVerified": False,
        "complete": False,
        "coverageCounts": summarize_counts(stages),
        "pendingStageKeys": pending_stage_keys,
        "capturedStageKeys": [],
        "blockedStageKeys": [],
        "nextUncapturedStageKey": pending_stage_keys[0] if pending_stage_keys else "",
        "stages": stages,
        "rule": (
            "One captured module/action is phase progress only. Keep module_interface_capture partial until "
            "all required capture stages are captured or an explicit current coverage rule narrows the scope."
        ),
    }


def build_capture_result(
    module: str,
    action: str,
    status: str,
    proof_recorded: list[str],
    evidence_pointers: list[str],
    blocking_issues: list[str],
) -> dict[str, Any]:
    result = {
        "kind": "allincms_module_capture_stage_result",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "module": module,
        "action": action,
        "status": status,
        "proofRecorded": proof_recorded,
        "redactedEvidencePointers": evidence_pointers,
        "blockingIssues": blocking_issues,
    }
    validation = validate_capture_result(result)
    if not validation["ok"]:
        raise ValueError("module capture result validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return result


def validate_capture_result(result: dict[str, Any], plan: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[str] = []
    if result.get("kind") != "allincms_module_capture_stage_result":
        issues.append("kind must be allincms_module_capture_stage_result")
    if result.get("localOnly") is not True:
        issues.append("capture result must be localOnly")
    if result.get("remoteMutationsPerformed") is not False:
        issues.append("capture result must record no remote mutations")
    module = result.get("module")
    action = result.get("action")
    if not isinstance(module, str) or not module.strip():
        issues.append("module must be a non-empty string")
    if not isinstance(action, str) or not action.strip():
        issues.append("action must be a non-empty string")
    if result.get("status") not in VALID_RESULT_STATUSES:
        issues.append(f"status must be one of {sorted(VALID_RESULT_STATUSES)}")
    for key in ("proofRecorded", "redactedEvidencePointers", "blockingIssues"):
        value = result.get(key)
        if not isinstance(value, list):
            issues.append(f"{key} must be an array")
        elif not all(isinstance(item, str) and item.strip() for item in value):
            issues.append(f"{key} must contain non-empty strings")
    evidence_pointers = result.get("redactedEvidencePointers")
    if isinstance(evidence_pointers, list):
        for pointer in evidence_pointers:
            if isinstance(pointer, str) and pointer.strip() and not is_evidence_pointer(pointer):
                issues.append(
                    "redactedEvidencePointers must be auditable pointers such as local://..., "
                    "https://..., or a filesystem path"
                )
    if result.get("status") == "captured":
        if not result.get("proofRecorded"):
            issues.append("captured result requires proofRecorded")
        if not result.get("redactedEvidencePointers"):
            issues.append("captured result requires redactedEvidencePointers")
        if result.get("blockingIssues"):
            issues.append("captured result must not include blockingIssues")
    if result.get("status") == "blocked" and not result.get("blockingIssues"):
        issues.append("blocked result requires blockingIssues")
    if plan and isinstance(module, str) and isinstance(action, str):
        keys = {stage_key(str(stage["module"]), str(stage["action"])) for stage in plan_stages(plan)}
        if stage_key(module, action) not in keys:
            issues.append(f"capture result stage is not in plan: {stage_key(module, action)}")
    issues.extend(redaction_issues(result, "capture result"))
    return {"ok": not issues, "issues": issues}


def summarize_counts(stages: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(stages),
        "captured": len([stage for stage in stages if stage.get("status") == "captured"]),
        "pending": len([stage for stage in stages if stage.get("status") == "pending"]),
        "blocked": len([stage for stage in stages if stage.get("status") == "blocked"]),
        "notApplicable": len([stage for stage in stages if stage.get("status") == "not_applicable"]),
    }


def update_coverage(plan: dict[str, Any], result: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    result_validation = validate_capture_result(result, plan)
    if not result_validation["ok"]:
        raise ValueError("module capture result validation failed:\n" + "\n".join(f"- {issue}" for issue in result_validation["issues"]))
    coverage = existing if existing else empty_coverage(plan)
    coverage_validation = validate_coverage(coverage, plan)
    if not coverage_validation["ok"]:
        raise ValueError("module capture coverage validation failed:\n" + "\n".join(f"- {issue}" for issue in coverage_validation["issues"]))

    updated = json.loads(json.dumps(coverage, ensure_ascii=False))
    target_key = stage_key(str(result["module"]), str(result["action"]))
    for stage in updated["stages"]:
        if stage.get("stageKey") != target_key:
            continue
        stage["status"] = result["status"]
        stage["proofRecorded"] = list(result.get("proofRecorded", []))
        stage["redactedEvidencePointers"] = list(result.get("redactedEvidencePointers", []))
        stage["blockingIssues"] = list(result.get("blockingIssues", []))
        stage["lastUpdatedAt"] = str(result.get("generatedAt", "")) or now_iso()
        break
    else:
        raise ValueError(f"stage not found in coverage: {target_key}")

    stages = updated["stages"]
    captured = [stage["stageKey"] for stage in stages if stage.get("status") == "captured"]
    pending = [stage["stageKey"] for stage in stages if stage.get("status") == "pending"]
    blocked = [stage["stageKey"] for stage in stages if stage.get("status") == "blocked"]
    complete = len(captured) + len([stage for stage in stages if stage.get("status") == "not_applicable"]) == len(stages)
    updated["generatedAt"] = now_iso()
    updated["coverageCounts"] = summarize_counts(stages)
    updated["capturedStageKeys"] = captured
    updated["pendingStageKeys"] = pending
    updated["blockedStageKeys"] = blocked
    updated["complete"] = complete
    updated["interfaceCoverageComplete"] = complete and not blocked
    updated["actionReplayContractsVerified"] = False
    updated["jsonReplayReady"] = False
    updated["nextUncapturedStageKey"] = (pending + blocked)[0] if pending or blocked else ""
    validation = validate_coverage(updated, plan)
    if not validation["ok"]:
        raise ValueError("updated module capture coverage validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return updated


def recalc_ledger_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(entries),
        "ready": len([entry for entry in entries if entry.get("status") == "ready"]),
        "pending": len([entry for entry in entries if entry.get("status") == "pending"]),
        "completed": len([entry for entry in entries if entry.get("status") == "completed"]),
        "blocked": len([entry for entry in entries if entry.get("status") in {"blocked", "partial"}]),
        "requiresAuthorization": len([entry for entry in entries if entry.get("authorizationRequired") is True]),
    }


def first_ready_stage_id(entries: list[dict[str, Any]]) -> str:
    for entry in entries:
        if entry.get("status") == "ready":
            return str(entry.get("stageId", ""))
    return ""


def unblock_pending_ledger_entries(entries: list[dict[str, Any]], completed: set[str]) -> None:
    for entry in entries:
        if entry.get("status") != "pending":
            continue
        dependencies = [str(item) for item in entry.get("dependsOn", []) if isinstance(item, str)]
        missing = [dependency for dependency in dependencies if dependency not in completed]
        if missing:
            entry["blockedUntil"] = [f"complete:{dependency}" for dependency in missing]
            entry["nextAllowedActions"] = []
        else:
            entry["status"] = "ready"
            entry["blockedUntil"] = []
            entry["nextAllowedActions"] = list(entry.get("plannedActions", []))


def sync_ledger_with_coverage(ledger: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    coverage_validation = validate_coverage(coverage)
    if not coverage_validation["ok"]:
        raise ValueError("module capture coverage validation failed:\n" + "\n".join(f"- {issue}" for issue in coverage_validation["issues"]))
    if ledger.get("kind") != "allincms_browser_execution_ledger":
        raise ValueError("ledger kind must be allincms_browser_execution_ledger")
    if ledger.get("localOnly") is not True or ledger.get("remoteMutationsPerformed") is not False:
        raise ValueError("ledger must be localOnly and record no remote mutations")
    updated = json.loads(json.dumps(ledger, ensure_ascii=False))
    entries = [entry for entry in updated.get("entries", []) if isinstance(entry, dict)]
    module_entry = next((entry for entry in entries if entry.get("stageId") == "module_interface_capture"), None)
    if not module_entry:
        raise ValueError("ledger missing module_interface_capture stage")
    next_key = str(coverage.get("nextUncapturedStageKey", ""))
    if coverage.get("complete") is True and coverage.get("interfaceCoverageComplete") is True:
        replay_ready = coverage.get("jsonReplayReady") is True
        module_entry["status"] = "completed"
        module_entry["nextAllowedActions"] = (
            [
                "JSON replay is technically ready for validated contract stages only",
                "request fresh action-time authorization before any replay",
                "run action-specific mutation gate before touching LAICMS",
            ]
            if replay_ready
            else []
        )
        module_entry["blockedUntil"] = []
        module_entry["proofRecorded"] = [
            (
                "module capture coverage complete; per-action replay contracts verified"
                if replay_ready
                else "module capture coverage complete; action replay contracts still require per-action validation"
            )
        ]
        module_entry["evidencePointers"] = ["local://module-capture-coverage.json"]
        completed = {str(entry.get("stageId")) for entry in entries if entry.get("status") == "completed"}
        unblock_pending_ledger_entries(entries, completed)
    else:
        if not next_key:
            raise ValueError("incomplete coverage must provide nextUncapturedStageKey")
        module_entry["status"] = "ready"
        module_entry["nextAllowedActions"] = [
            f"capture next module/action coverage stage: {next_key}",
            "capture request URL/method/headers/payload or explicit UI-only finding",
            "verify whether persistence occurred",
            "update module capture coverage before continuing",
        ]
        module_entry["blockedUntil"] = []
        module_entry["proofRecorded"] = list(coverage.get("capturedStageKeys", []))
        module_entry["evidencePointers"] = ["local://module-capture-coverage.json"]
    updated["entries"] = entries
    updated["stageCounts"] = recalc_ledger_counts(entries)
    updated["nextStageId"] = first_ready_stage_id(entries)
    updated["lastCoverageSync"] = {
        "stageId": "module_interface_capture",
        "coverageComplete": coverage.get("complete") is True,
        "interfaceCoverageComplete": coverage.get("interfaceCoverageComplete") is True,
        "actionReplayContractsVerified": coverage.get("actionReplayContractsVerified") is True,
        "jsonReplayReady": coverage.get("jsonReplayReady") is True,
        "nextUncapturedStageKey": next_key,
        "syncedAt": now_iso(),
    }
    return updated


def redaction_issues(data: dict[str, Any], label: str) -> list[str]:
    issues: list[str] = []
    text = json.dumps(data, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append(f"{label} must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"{label} contains forbidden evidence term: {term}")
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in text:
            issues.append(f"{label} must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", text):
        issues.append(f"{label} must use route patterns instead of concrete frontend origins")
    return issues


def validate_coverage(coverage: dict[str, Any], plan: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[str] = []
    if coverage.get("kind") != "allincms_module_capture_coverage":
        issues.append("kind must be allincms_module_capture_coverage")
    if coverage.get("localOnly") is not True:
        issues.append("coverage must be localOnly")
    if coverage.get("remoteMutationsPerformed") is not False:
        issues.append("coverage must record no remote mutations")
    if coverage.get("siteKeyTemplate") != "{realSiteKey}":
        issues.append("siteKeyTemplate must be {realSiteKey}")
    stages = coverage.get("stages")
    if not isinstance(stages, list):
        issues.append("stages must be an array")
        stages = []
    stage_keys: list[str] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            issues.append(f"stages[{index}] must be an object")
            continue
        key = stage.get("stageKey")
        if not isinstance(key, str) or ":" not in key:
            issues.append(f"stages[{index}].stageKey must be module:action")
        else:
            stage_keys.append(key)
        if stage.get("status") not in {"pending", "captured", "blocked", "not_applicable"}:
            issues.append(f"stages[{index}].status is invalid")
        for list_key in ("requiredProof", "proofRecorded", "redactedEvidencePointers", "blockingIssues"):
            value = stage.get(list_key)
            if not isinstance(value, list):
                issues.append(f"stages[{index}].{list_key} must be an array")
            elif not all(isinstance(item, str) for item in value):
                issues.append(f"stages[{index}].{list_key} must contain strings")
        if stage.get("status") == "captured" and not stage.get("redactedEvidencePointers"):
            issues.append(f"stages[{index}] captured status requires evidence pointers")
        if stage.get("status") == "blocked" and not stage.get("blockingIssues"):
            issues.append(f"stages[{index}] blocked status requires blockingIssues")
    if len(stage_keys) != len(set(stage_keys)):
        issues.append("coverage stages must not contain duplicate stageKey values")
    if plan:
        expected = [stage_key(str(stage["module"]), str(stage["action"])) for stage in plan_stages(plan)]
        if stage_keys != expected:
            issues.append("coverage stage keys must match capture plan stage order")
    counts = coverage.get("coverageCounts")
    if not isinstance(counts, dict):
        issues.append("coverageCounts must be an object")
        counts = {}
    expected_counts = summarize_counts([stage for stage in stages if isinstance(stage, dict)])
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            issues.append(f"coverageCounts.{key} must be {expected}")
    captured = [stage.get("stageKey") for stage in stages if isinstance(stage, dict) and stage.get("status") == "captured"]
    pending = [stage.get("stageKey") for stage in stages if isinstance(stage, dict) and stage.get("status") == "pending"]
    blocked = [stage.get("stageKey") for stage in stages if isinstance(stage, dict) and stage.get("status") == "blocked"]
    if coverage.get("capturedStageKeys") != captured:
        issues.append("capturedStageKeys mismatch")
    if coverage.get("pendingStageKeys") != pending:
        issues.append("pendingStageKeys mismatch")
    if coverage.get("blockedStageKeys") != blocked:
        issues.append("blockedStageKeys mismatch")
    complete = len(captured) + len([stage for stage in stages if isinstance(stage, dict) and stage.get("status") == "not_applicable"]) == len(stages)
    if coverage.get("complete") is not complete:
        issues.append("complete flag mismatch")
    if coverage.get("interfaceCoverageComplete") is not (complete and not blocked):
        issues.append("interfaceCoverageComplete must require complete coverage and no blocked stages")
    replay_contract_stage_keys = coverage.get("replayContractStageKeys", [])
    if replay_contract_stage_keys is None:
        replay_contract_stage_keys = []
    if not isinstance(replay_contract_stage_keys, list) or not all(isinstance(item, str) for item in replay_contract_stage_keys):
        issues.append("replayContractStageKeys must be an array of strings when present")
        replay_contract_stage_keys = []
    replay_contracts_verified = coverage.get("actionReplayContractsVerified") is True
    if replay_contracts_verified:
        if coverage.get("interfaceCoverageComplete") is not True:
            issues.append("actionReplayContractsVerified requires interfaceCoverageComplete true")
        if sorted(replay_contract_stage_keys) != sorted(captured):
            issues.append("replayContractStageKeys must cover every captured stage before replay is ready")
    elif coverage.get("actionReplayContractsVerified") is not False:
        issues.append("actionReplayContractsVerified must be boolean")
    expected_json_ready = replay_contracts_verified and coverage.get("interfaceCoverageComplete") is True
    if coverage.get("jsonReplayReady") is not expected_json_ready:
        issues.append("jsonReplayReady must require complete interface coverage plus verified per-action replay contracts")
    if not complete and not coverage.get("nextUncapturedStageKey"):
        issues.append("incomplete coverage must include nextUncapturedStageKey")
    issues.extend(redaction_issues(coverage, "coverage"))
    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Update local AllinCMS module-capture coverage.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--existing-coverage", default="")
    parser.add_argument("--sync-ledger", default="")
    parser.add_argument("--ledger-output", default="")
    parser.add_argument("--result-json", default="")
    parser.add_argument("--module", default="")
    parser.add_argument("--action", default="")
    parser.add_argument("--status", choices=sorted(VALID_RESULT_STATUSES))
    parser.add_argument("--proof-recorded", default="")
    parser.add_argument("--evidence-pointers", default="")
    parser.add_argument("--blocking-issues", default="")
    parser.add_argument("--output")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        plan = load_json(Path(args.plan))
        if args.validate_only:
            coverage = load_json(Path(args.existing_coverage or args.output))
            validation = validate_coverage(coverage, plan)
            if args.json:
                print(json.dumps(validation, ensure_ascii=False, indent=2))
            elif validation["ok"]:
                print("Module capture coverage validation passed.")
            else:
                print("Module capture coverage validation failed:")
                for issue in validation["issues"]:
                    print(f"- {issue}")
            return 0 if validation["ok"] else 1
        existing = load_json(Path(args.existing_coverage)) if args.existing_coverage else None
        if args.result_json:
            result = load_json(Path(args.result_json))
        else:
            if not args.module or not args.action or not args.status:
                raise ValueError("--module, --action, and --status are required when --result-json is not supplied")
            result = build_capture_result(
                args.module,
                args.action,
                args.status,
                split_csv(args.proof_recorded),
                split_csv(args.evidence_pointers),
                split_csv(args.blocking_issues),
            )
        coverage = update_coverage(plan, result, existing)
        if args.sync_ledger:
            synced_ledger = sync_ledger_with_coverage(load_json(Path(args.sync_ledger)), coverage)
            if args.ledger_output:
                write_json(Path(args.ledger_output), synced_ledger)
            coverage = {
                "coverage": coverage,
                "ledger": synced_ledger,
            }
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), coverage)
    else:
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
