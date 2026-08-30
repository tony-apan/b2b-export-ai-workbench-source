#!/usr/bin/env python3
"""Branch a from-scratch browser ledger into an existing-site continuation ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from build_browser_execution_ledger import validate_browser_execution_ledger, write_json
from validate_run_evidence import validate as validate_run_evidence


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


def require_existing_site_evidence(evidence: dict[str, Any]) -> str:
    errors = validate_run_evidence(evidence)
    if errors:
        raise ValueError("existing-site evidence validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    site_creation = evidence.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "existing_site_selected":
        raise ValueError("existing-site evidence must have siteCreation.status=existing_site_selected")
    site_identity = evidence.get("siteIdentity")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("existing-site evidence must include siteIdentity.siteKey")
    return str(site_identity["siteKey"])


def find_entry(entries: list[dict[str, Any]], stage_id: str) -> dict[str, Any]:
    for entry in entries:
        if entry.get("stageId") == stage_id:
            return entry
    raise ValueError(f"ledger missing stage: {stage_id}")


def branch_ledger(ledger: dict[str, Any], existing_site_evidence: dict[str, Any], evidence_pointer: str) -> dict[str, Any]:
    ledger_validation = validate_browser_execution_ledger(ledger)
    if not ledger_validation.get("ok"):
        raise ValueError("browser execution ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in ledger_validation["issues"]))
    site_key = require_existing_site_evidence(existing_site_evidence)
    if not evidence_pointer.strip():
        raise ValueError("evidence pointer is required")

    updated = json.loads(json.dumps(ledger, ensure_ascii=False))
    entries = [entry for entry in updated.get("entries", []) if isinstance(entry, dict)]
    refresh = find_entry(entries, "refresh_readonly_site_evidence")
    create = find_entry(entries, "create_site_submit")
    setup = find_entry(entries, "setup_pages_inspection")

    if refresh.get("status") != "completed":
        raise ValueError("refresh_readonly_site_evidence must be completed before branching to existing-site continuation")
    if create.get("status") not in {"ready", "pending"}:
        raise ValueError("create_site_submit must be ready or pending before it can be skipped for existing-site continuation")

    create["status"] = "skipped"
    create["blockedUntil"] = []
    create["nextAllowedActions"] = []
    create["evidencePointers"] = [evidence_pointer]
    create["proofRecorded"] = ["existing site selected; create-site submit skipped"]
    create["notes"] = f"Skipped create_site_submit because existing site {site_key} was verified for continuation."

    setup["status"] = "ready"
    setup["blockedUntil"] = []
    setup["nextAllowedActions"] = list(setup.get("plannedActions", []))

    updated["entries"] = entries
    updated["stageCounts"] = recalc_counts(entries)
    updated["nextStageId"] = first_ready_stage(entries)
    updated["existingSiteContinuation"] = {
        "enabled": True,
        "siteKey": site_key,
        "branchedAt": now_iso(),
        "sourceEvidence": evidence_pointer,
        "skippedStageId": "create_site_submit",
        "nextStageId": updated["nextStageId"],
        "remoteMutationsPerformed": False,
    }
    updated["executionRules"] = list(updated.get("executionRules", [])) + [
        "create_site_submit was skipped only because current existing-site evidence was validated.",
        "Do not use this branch as proof of from-scratch site creation.",
    ]
    validation = validate_browser_execution_ledger(updated)
    if not validation.get("ok"):
        raise ValueError("branched ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Branch a from-scratch AllinCMS ledger to an existing-site continuation.")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--existing-site-evidence", required=True)
    parser.add_argument("--evidence-pointer", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        evidence_pointer = args.evidence_pointer or args.existing_site_evidence
        updated = branch_ledger(load_json(Path(args.ledger)), load_json(Path(args.existing_site_evidence)), evidence_pointer)
        write_json(Path(args.output), updated)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote existing-site continuation ledger: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
