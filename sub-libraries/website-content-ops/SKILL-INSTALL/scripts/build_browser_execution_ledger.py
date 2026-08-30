#!/usr/bin/env python3
"""Build and validate a staged browser execution ledger from an AllinCMS execution plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_browser_execution_plan import REQUIRED_STAGE_IDS, SIMULATED_SITE_KEYS, VALID_MODES, load_json, validate_browser_execution_plan
from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


VALID_STATUSES = {"pending", "ready", "completed", "blocked", "partial", "skipped"}
USER_VISIBLE_KEYS = {
    "stageId",
    "phase",
    "mode",
    "status",
    "targetTemplate",
    "authorizationRequired",
        "requiredProof",
        "stopAfter",
        "nextAllowedActions",
        "plannedActions",
        "blockedUntil",
}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_stage_entry(stage: dict[str, Any], completed: set[str], failed: set[str]) -> dict[str, Any]:
    stage_id = str(stage.get("stageId", ""))
    dependencies = [str(item) for item in stage.get("dependsOn", []) if isinstance(item, str)]
    planned_actions = list(stage.get("allowedActions", []))
    missing_dependencies = [dependency for dependency in dependencies if dependency not in completed]
    if stage_id in failed:
        status = "blocked"
        blocked_until = ["resolve recorded blocker", "refresh plan before retry"]
        next_actions: list[str] = []
    elif missing_dependencies:
        status = "pending"
        blocked_until = [f"complete:{dependency}" for dependency in missing_dependencies]
        next_actions = []
    elif stage_id in completed:
        status = "completed"
        blocked_until = []
        next_actions = []
    else:
        status = "ready"
        blocked_until = []
        next_actions = planned_actions

    return {
        "stageId": stage_id,
        "phase": stage.get("phase", ""),
        "mode": stage.get("mode", ""),
        "status": status,
        "targetTemplate": stage.get("targetTemplate", ""),
        "authorizationRequired": stage.get("authorizationRequired") is True,
        "remoteMutationExpectation": stage.get("remoteMutationExpectation", ""),
        "dependsOn": dependencies,
        "requiredProof": list(stage.get("requiredProof", [])),
        "stopAfter": stage.get("stopAfter", ""),
        "plannedActions": planned_actions,
        "nextAllowedActions": next_actions,
        "blockedUntil": blocked_until,
        "evidencePointers": [],
        "proofRecorded": [],
        "notes": "",
    }


def build_browser_execution_ledger(
    plan: dict[str, Any],
    completed_stage_ids: list[str] | None = None,
    failed_stage_ids: list[str] | None = None,
) -> dict[str, Any]:
    plan_validation = validate_browser_execution_plan(plan)
    if not plan_validation.get("ok"):
        raise ValueError("browser execution plan validation failed:\n" + "\n".join(f"- {issue}" for issue in plan_validation["issues"]))

    completed = {stage.strip() for stage in (completed_stage_ids or []) if stage.strip()}
    failed = {stage.strip() for stage in (failed_stage_ids or []) if stage.strip()}
    known_stage_ids = {stage.get("stageId") for stage in plan.get("stages", []) if isinstance(stage, dict)}
    unknown = sorted((completed | failed) - {str(stage_id) for stage_id in known_stage_ids})
    if unknown:
        raise ValueError("unknown stage ids: " + ", ".join(unknown))

    entries = [build_stage_entry(stage, completed, failed) for stage in plan["stages"]]
    ready = [entry["stageId"] for entry in entries if entry["status"] == "ready"]
    blocked = [entry["stageId"] for entry in entries if entry["status"] in {"blocked", "partial"}]
    next_stage = ready[0] if ready else ""
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePlanKind": plan.get("kind"),
        "sourcePlan": plan.get("sourceRehearsalSummary", ""),
        "siteKeyTemplate": "{realSiteKey}",
        "contentType": plan.get("contentType", ""),
        "stageCounts": {
            "total": len(entries),
            "ready": len(ready),
            "pending": len([entry for entry in entries if entry["status"] == "pending"]),
            "completed": len([entry for entry in entries if entry["status"] == "completed"]),
            "blocked": len(blocked),
            "requiresAuthorization": len([entry for entry in entries if entry["authorizationRequired"] is True]),
        },
        "nextStageId": next_stage,
        "entries": entries,
        "executionRules": [
            "Run only nextStageId unless the ledger is regenerated after evidence changes.",
            "A requires_authorization stage needs fresh action-time authorization and a matching pre-mutation gate.",
            "Record redacted evidence pointers after each browser stage; do not store account data or business copy in this skill.",
            "Regenerate or update the ledger after every completed, blocked, or skipped stage.",
        ],
    }
    validation = validate_browser_execution_ledger(ledger)
    if not validation.get("ok"):
        raise ValueError("browser execution ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return ledger


def parse_stage_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else []


def iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def validate_browser_execution_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if ledger.get("kind") != "allincms_browser_execution_ledger":
        issues.append("kind must be allincms_browser_execution_ledger")
    if ledger.get("localOnly") is not True:
        issues.append("ledger must be localOnly")
    if ledger.get("remoteMutationsPerformed") is not False:
        issues.append("ledger must record no remote mutations")
    if ledger.get("sourcePlanKind") != "allincms_browser_execution_plan":
        issues.append("sourcePlanKind must be allincms_browser_execution_plan")
    if ledger.get("siteKeyTemplate") != "{realSiteKey}":
        issues.append("siteKeyTemplate must be {realSiteKey}")

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        issues.append("entries must be an array")
        entries = []
    stage_ids = [entry.get("stageId") for entry in entries if isinstance(entry, dict)]
    for required in REQUIRED_STAGE_IDS:
        if required not in stage_ids:
            issues.append(f"entries missing {required}")
    if len(stage_ids) != len(set(stage_ids)):
        issues.append("entries must not contain duplicate stageId values")

    completed = {str(entry.get("stageId")) for entry in entries if isinstance(entry, dict) and entry.get("status") == "completed"}
    dependency_satisfied = {
        str(entry.get("stageId"))
        for entry in entries
        if isinstance(entry, dict) and entry.get("status") in {"completed", "skipped"}
    }
    ready = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(f"entries[{index}] must be an object")
            continue
        stage_id = entry.get("stageId")
        status = entry.get("status")
        if not isinstance(stage_id, str) or not stage_id.strip():
            issues.append(f"entries[{index}].stageId must be a non-empty string")
        if status not in VALID_STATUSES:
            issues.append(f"entries[{index}].status must be one of {sorted(VALID_STATUSES)}")
        if entry.get("mode") not in VALID_MODES:
            issues.append(f"entries[{index}].mode must be one of {sorted(VALID_MODES)}")
        requires_auth = entry.get("mode") == "requires_authorization"
        if entry.get("authorizationRequired") is not requires_auth:
            issues.append(f"entries[{index}].authorizationRequired must match mode")
        expectation = entry.get("remoteMutationExpectation")
        if expectation not in {"must", "may", "must_not"}:
            issues.append(f"entries[{index}].remoteMutationExpectation must be must, may, or must_not")
        elif not requires_auth and expectation != "must_not":
            issues.append(f"entries[{index}].remoteMutationExpectation must be must_not for non-authorization stages")
        elif requires_auth and expectation == "must_not":
            issues.append(f"entries[{index}].remoteMutationExpectation must not be must_not for authorization stages")
        dependencies = entry.get("dependsOn")
        if not isinstance(dependencies, list):
            issues.append(f"entries[{index}].dependsOn must be an array")
            dependencies = []
        for dependency in dependencies:
            if dependency not in REQUIRED_STAGE_IDS:
                issues.append(f"entries[{index}].dependsOn contains unknown stage {dependency}")
            if status in {"ready", "completed", "skipped"} and dependency not in dependency_satisfied:
                issues.append(f"entries[{index}] cannot be {status} until dependency {dependency} is completed")
        if status == "ready":
            ready.append(stage_id)
            if entry.get("blockedUntil"):
                issues.append(f"entries[{index}].blockedUntil must be empty for ready stages")
            if not entry.get("nextAllowedActions"):
                issues.append(f"entries[{index}].nextAllowedActions must not be empty for ready stages")
        if status == "pending" and not dependencies:
            issues.append(f"entries[{index}] is pending without dependencies; use ready, blocked, completed, or skipped")
        if status in {"blocked", "partial"} and not entry.get("blockedUntil"):
            issues.append(f"entries[{index}].blockedUntil must explain blocked status")
        for key in ("requiredProof", "evidencePointers", "proofRecorded", "nextAllowedActions", "plannedActions", "blockedUntil"):
            value = entry.get(key)
            if not isinstance(value, list):
                issues.append(f"entries[{index}].{key} must be an array")
            elif not all(isinstance(item, str) for item in value):
                issues.append(f"entries[{index}].{key} must contain strings")
        if status in {"pending", "ready"} and not entry.get("plannedActions"):
            issues.append(f"entries[{index}].plannedActions must preserve original allowed actions")

    counts = ledger.get("stageCounts")
    if not isinstance(counts, dict):
        issues.append("stageCounts must be an object")
        counts = {}
    expected_counts = {
        "total": len(entries),
        "ready": len([entry for entry in entries if isinstance(entry, dict) and entry.get("status") == "ready"]),
        "pending": len([entry for entry in entries if isinstance(entry, dict) and entry.get("status") == "pending"]),
        "completed": len([entry for entry in entries if isinstance(entry, dict) and entry.get("status") == "completed"]),
        "blocked": len([entry for entry in entries if isinstance(entry, dict) and entry.get("status") in {"blocked", "partial"}]),
        "requiresAuthorization": len(
            [entry for entry in entries if isinstance(entry, dict) and entry.get("authorizationRequired") is True]
        ),
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            issues.append(f"stageCounts.{key} must be {expected}")

    next_stage = ledger.get("nextStageId")
    if ready:
        if next_stage != ready[0]:
            issues.append("nextStageId must be the first ready stage")
    elif next_stage not in {"", None}:
        issues.append("nextStageId must be empty when no stage is ready")

    text = json.dumps(ledger, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append("ledger must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"ledger contains forbidden evidence term: {term}")

    user_visible = []
    for entry in entries:
        if isinstance(entry, dict):
            user_visible.append({key: entry.get(key) for key in USER_VISIBLE_KEYS})
    user_visible_text = json.dumps(
        {
            "siteKeyTemplate": ledger.get("siteKeyTemplate"),
            "nextStageId": ledger.get("nextStageId"),
            "entries": user_visible,
            "executionRules": ledger.get("executionRules"),
        },
        ensure_ascii=False,
    )
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in user_visible_text:
            issues.append("user-facing ledger fields must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", user_visible_text):
        issues.append("user-facing ledger fields must use {realSiteKey} frontend template")

    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local-only staged browser execution ledger for AllinCMS.")
    parser.add_argument("browser_execution_plan_json")
    parser.add_argument("--completed-stage-ids", default="")
    parser.add_argument("--failed-stage-ids", default="")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        ledger = build_browser_execution_ledger(
            load_json(Path(args.browser_execution_plan_json)),
            parse_stage_list(args.completed_stage_ids),
            parse_stage_list(args.failed_stage_ids),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), ledger)
    else:
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
