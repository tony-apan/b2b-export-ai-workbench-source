#!/usr/bin/env python3
"""Apply one browser stage result to an AllinCMS execution ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_browser_execution_ledger import validate_browser_execution_ledger, write_json
from build_browser_execution_plan import SIMULATED_SITE_KEYS
from build_browser_stage_packet import validate_browser_stage_packet
from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


VALID_RESULT_STATUSES = {"completed", "blocked", "partial"}
EVIDENCE_POINTER_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|/|\.{1,2}/).+")
WORKSPACE_SITE_URL_RE = re.compile(r"https://workspace\.laicms\.com/([a-z0-9][a-z0-9-]{2,62}[a-z0-9])(?:/|$)")


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else []


def is_evidence_pointer(value: str) -> bool:
    return bool(EVIDENCE_POINTER_RE.match(value.strip()))


def build_stage_result(
    stage_id: str,
    status: str,
    evidence_pointers: list[str],
    proof_recorded: list[str],
    blocking_issues: list[str],
    browser_stage_mutated_remote: bool = False,
) -> dict[str, Any]:
    result = {
        "kind": "allincms_browser_stage_result",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "browserStageMutatedRemote": browser_stage_mutated_remote,
        "stageId": stage_id,
        "status": status,
        "redactedEvidencePointers": evidence_pointers,
        "proofRecorded": proof_recorded,
        "blockingIssues": blocking_issues,
        "operatorNote": "",
    }
    validation = validate_browser_stage_result(result)
    if not validation["ok"]:
        raise ValueError("browser stage result validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return result


def validate_browser_stage_result(result: dict[str, Any], packet: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[str] = []
    if result.get("kind") != "allincms_browser_stage_result":
        issues.append("kind must be allincms_browser_stage_result")
    if result.get("localOnly") is not True:
        issues.append("stage result must be localOnly")
    if result.get("remoteMutationsPerformed") is not False:
        issues.append("stage result must record no remote mutations")
    if not isinstance(result.get("browserStageMutatedRemote"), bool):
        issues.append("browserStageMutatedRemote must be a boolean")
    if not isinstance(result.get("stageId"), str) or not result["stageId"].strip():
        issues.append("stageId must be a non-empty string")
    if result.get("status") not in VALID_RESULT_STATUSES:
        issues.append(f"status must be one of {sorted(VALID_RESULT_STATUSES)}")
    for key in ("redactedEvidencePointers", "proofRecorded", "blockingIssues"):
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
    if result.get("status") == "completed":
        if not result.get("redactedEvidencePointers"):
            issues.append("completed result requires redactedEvidencePointers")
        if not result.get("proofRecorded"):
            issues.append("completed result requires proofRecorded")
        if result.get("blockingIssues"):
            issues.append("completed result must not include blockingIssues")
    if result.get("status") == "blocked":
        if not result.get("blockingIssues"):
            issues.append("blocked result requires blockingIssues")
    if result.get("status") == "partial":
        if not result.get("redactedEvidencePointers"):
            issues.append("partial result requires redactedEvidencePointers")
        if not result.get("proofRecorded"):
            issues.append("partial result requires proofRecorded")
        if not result.get("blockingIssues"):
            issues.append("partial result requires blockingIssues")

    if packet:
        packet_validation = validate_browser_stage_packet(packet)
        if not packet_validation["ok"]:
            issues.extend(f"packet: {issue}" for issue in packet_validation["issues"])
        if result.get("stageId") != packet.get("stageId"):
            issues.append("stage result must target packet stageId")
        if result.get("browserStageMutatedRemote") is True:
            if packet.get("authorizationRequired") is not True:
                issues.append("browserStageMutatedRemote true is allowed only for authorization-required stages")
            if result.get("status") != "completed":
                issues.append("browserStageMutatedRemote true requires completed stage status")
        expectation = packet.get("remoteMutationExpectation")
        if expectation == "must" and result.get("status") == "completed" and result.get("browserStageMutatedRemote") is not True:
            issues.append("completed stage result must set browserStageMutatedRemote true for this stage")
        if expectation == "must_not" and result.get("browserStageMutatedRemote") is not False:
            issues.append("stage result must keep browserStageMutatedRemote false for this stage")
        if result.get("status") == "completed":
            required = set(packet.get("requiredProof", []))
            recorded = set(result.get("proofRecorded", []))
            missing = sorted(required - recorded)
            if missing:
                issues.append("completed result missing required proof: " + ", ".join(missing))

    text = json.dumps(result, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append("stage result must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"stage result contains forbidden evidence term: {term}")
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in text:
            issues.append("stage result must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", text):
        issues.append("stage result must use redacted route patterns instead of concrete frontend origins")
    workspace_site_match = WORKSPACE_SITE_URL_RE.search(text)
    if workspace_site_match:
        issues.append("stage result must redact workspace site URLs with {realSiteKey}")

    return {"ok": not issues, "issues": issues}


def recalc_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(entries),
        "ready": len([entry for entry in entries if entry.get("status") == "ready"]),
        "pending": len([entry for entry in entries if entry.get("status") == "pending"]),
        "completed": len([entry for entry in entries if entry.get("status") == "completed"]),
        "blocked": len([entry for entry in entries if entry.get("status") in {"blocked", "partial"}]),
        "requiresAuthorization": len([entry for entry in entries if entry.get("authorizationRequired") is True]),
    }


def first_ready_stage(entries: list[dict[str, Any]]) -> str:
    for entry in entries:
        if entry.get("status") == "ready":
            return str(entry.get("stageId", ""))
    return ""


def unblock_entries(entries: list[dict[str, Any]], completed: set[str]) -> None:
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


def apply_stage_result(ledger: dict[str, Any], packet: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    ledger_validation = validate_browser_execution_ledger(ledger)
    if not ledger_validation["ok"]:
        raise ValueError("browser execution ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in ledger_validation["issues"]))
    result_validation = validate_browser_stage_result(result, packet)
    if not result_validation["ok"]:
        raise ValueError("browser stage result validation failed:\n" + "\n".join(f"- {issue}" for issue in result_validation["issues"]))
    stage_id = str(result["stageId"])
    recovery = packet.get("recovery") is True
    if not recovery and stage_id != ledger.get("nextStageId"):
        raise ValueError("stage result must target ledger nextStageId")

    updated = json.loads(json.dumps(ledger, ensure_ascii=False))
    entries = [entry for entry in updated.get("entries", []) if isinstance(entry, dict)]
    for entry in entries:
        if entry.get("stageId") != stage_id:
            continue
        if recovery:
            if entry.get("status") != "partial":
                raise ValueError(f"stage is not partial in ledger for recovery: {stage_id}")
        elif entry.get("status") != "ready":
            raise ValueError(f"stage is not ready in ledger: {stage_id}")
        entry["status"] = result["status"]
        entry["evidencePointers"] = list(result.get("redactedEvidencePointers", []))
        entry["proofRecorded"] = list(result.get("proofRecorded", []))
        entry["notes"] = str(result.get("operatorNote", ""))
        entry["nextAllowedActions"] = []
        if result["status"] in {"blocked", "partial"}:
            entry["blockedUntil"] = list(result.get("blockingIssues", []))
        else:
            entry["blockedUntil"] = []
        break
    else:
        raise ValueError(f"stage not found in ledger: {stage_id}")

    completed = {str(entry.get("stageId")) for entry in entries if entry.get("status") == "completed"}
    unblock_entries(entries, completed)
    updated["entries"] = entries
    updated["stageCounts"] = recalc_counts(entries)
    updated["nextStageId"] = first_ready_stage(entries)
    updated["lastAppliedStageResult"] = {
        "stageId": stage_id,
        "status": result["status"],
        "appliedAt": now_iso(),
    }
    validation = validate_browser_execution_ledger(updated)
    if not validation["ok"]:
        raise ValueError("updated ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a single browser stage result to an AllinCMS execution ledger.")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--result-json")
    parser.add_argument("--stage-id", default="")
    parser.add_argument("--status", choices=sorted(VALID_RESULT_STATUSES))
    parser.add_argument("--evidence-pointers", default="")
    parser.add_argument("--proof-recorded", default="")
    parser.add_argument("--blocking-issues", default="")
    parser.add_argument("--browser-stage-mutated-remote", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        ledger = load_json(Path(args.ledger))
        packet = load_json(Path(args.packet))
        if args.result_json:
            result = load_json(Path(args.result_json))
        else:
            if not args.stage_id or not args.status:
                raise ValueError("--stage-id and --status are required when --result-json is not supplied")
            result = build_stage_result(
                args.stage_id,
                args.status,
                split_csv(args.evidence_pointers),
                split_csv(args.proof_recorded),
                split_csv(args.blocking_issues),
                args.browser_stage_mutated_remote,
            )
            inline_validation = validate_browser_stage_result(result, packet)
            if not inline_validation["ok"]:
                raise ValueError(
                    "browser stage result validation failed:\n"
                    + "\n".join(f"- {issue}" for issue in inline_validation["issues"])
                )
        updated = apply_stage_result(ledger, packet, result)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), updated)
    else:
        print(json.dumps(updated, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
