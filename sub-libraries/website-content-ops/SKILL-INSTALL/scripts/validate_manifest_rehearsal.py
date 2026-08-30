#!/usr/bin/env python3
"""Validate AllinCMS manifest rehearsal artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_manifest import validate_manifest


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


def same_path(recorded: object, expected: Path) -> bool:
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    return Path(recorded).resolve() == expected.resolve()


def validate_rehearsal(summary_path: Path) -> dict[str, Any]:
    issues: list[str] = []
    try:
        summary = load_json(summary_path)
    except ValueError as exc:
        return {"ok": False, "summaryPath": str(summary_path), "issues": [str(exc)]}
    if summary.get("kind") != "allincms_manifest_rehearsal_summary":
        issues.append("kind must be allincms_manifest_rehearsal_summary")
    if summary.get("localOnly") is not True:
        issues.append("summary must be localOnly")
    if summary.get("remoteMutationsPerformed") is not False:
        issues.append("summary must record no remote mutations")

    manifest_path = summary_path.parent / "draft-manifest.json"
    gap_ledger_path = summary_path.parent / "source-input-gap-ledger.json"
    source_requirements_path = summary_path.parent / "source-input-requirements.json"
    if not same_path(summary.get("draftManifestPath"), manifest_path):
        issues.append("draftManifestPath must point to sibling draft-manifest.json")
    if not same_path(summary.get("sourceInputGapLedgerPath"), gap_ledger_path):
        issues.append("sourceInputGapLedgerPath must point to sibling source-input-gap-ledger.json")
    if not same_path(summary.get("sourceInputRequirementsPath"), source_requirements_path):
        issues.append("sourceInputRequirementsPath must point to sibling source-input-requirements.json")
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        manifest = {}
        issues.append(str(exc))
    try:
        gap_ledger = load_json(gap_ledger_path)
    except ValueError as exc:
        gap_ledger = {}
        issues.append(str(exc))
    try:
        source_requirements = load_json(source_requirements_path)
    except ValueError as exc:
        source_requirements = {}
        issues.append(str(exc))

    draft_errors = validate_manifest(manifest, require_schema_verified=False)
    schema_errors = validate_manifest(manifest, require_schema_verified=True)
    if draft_errors:
        issues.extend(f"draft manifest: {error}" for error in draft_errors)
    if not schema_errors:
        issues.append("schema gate must fail for draft rehearsal manifest")
    if not any("schemaVerified" in error for error in schema_errors):
        issues.append("schema gate failure must include schemaVerified")
    if not any("payloadTemplate" in error for error in schema_errors):
        issues.append("schema gate failure must include payloadTemplate")

    draft_summary = summary.get("draftValidation") if isinstance(summary.get("draftValidation"), dict) else {}
    schema_summary = summary.get("schemaGate") if isinstance(summary.get("schemaGate"), dict) else {}
    if draft_summary.get("passed") is not True or draft_summary.get("errorCount") != 0:
        issues.append("draftValidation summary must report pass with zero errors")
    if schema_summary.get("passed") is not False or schema_summary.get("expectedFailure") is not True:
        issues.append("schemaGate summary must report expected failure")
    if schema_summary.get("errorCount") != len(schema_errors):
        issues.append("schemaGate.errorCount mismatch")
    if summary.get("contentType") != manifest.get("contentType"):
        issues.append("summary contentType must match manifest")
    if summary.get("siteKey") != manifest.get("siteKey"):
        issues.append("summary siteKey must match manifest")
    if source_requirements:
        if source_requirements.get("kind") != "allincms_source_input_requirements":
            issues.append("source requirements kind must be allincms_source_input_requirements")
        if source_requirements.get("localOnly") is not True:
            issues.append("source requirements must be localOnly")
        if source_requirements.get("remoteMutationsPerformed") is not False:
            issues.append("source requirements must record no remote mutations")
        if source_requirements.get("siteKey") != manifest.get("siteKey"):
            issues.append("source requirements siteKey must match manifest")
        content_types = source_requirements.get("contentTypes")
        if not isinstance(content_types, dict) or manifest.get("contentType") not in content_types:
            issues.append("source requirements must include the manifest content type")
        if source_requirements.get("overallStatus") != "blocked":
            issues.append("source requirements should be blocked in draft rehearsal until schema capture exists")
        if not source_requirements.get("blockedUntil"):
            issues.append("source requirements must list blockedUntil items for draft rehearsal")
        operation_gaps = source_requirements.get("operationGaps")
        if not isinstance(operation_gaps, dict):
            issues.append("source requirements must include operationGaps")
            operation_gaps = {}
        if operation_gaps.get("entryCount", 0) <= 0:
            issues.append("source requirements operationGaps.entryCount must be positive in rehearsal")
        if not operation_gaps.get("blockedFields"):
            issues.append("source requirements operationGaps.blockedFields must be non-empty in rehearsal")
        if gap_ledger:
            if gap_ledger.get("kind") != "allincms_source_input_gap_ledger":
                issues.append("source gap ledger kind must be allincms_source_input_gap_ledger")
            if gap_ledger.get("localOnly") is not True:
                issues.append("source gap ledger must be localOnly")
            if gap_ledger.get("remoteMutationsPerformed") is not False:
                issues.append("source gap ledger must record no remote mutations")
            if gap_ledger.get("siteKey") != manifest.get("siteKey"):
                issues.append("source gap ledger siteKey must match manifest")
            entries = gap_ledger.get("entries")
            if not isinstance(entries, list) or not entries:
                issues.append("source gap ledger entries must be non-empty in rehearsal")
            if isinstance(entries, list) and operation_gaps.get("entryCount") != len(entries):
                issues.append("operationGaps.entryCount must match gap ledger entries")
        req_summary = summary.get("sourceInputRequirements") if isinstance(summary.get("sourceInputRequirements"), dict) else {}
        if req_summary.get("overallStatus") != source_requirements.get("overallStatus"):
            issues.append("sourceInputRequirements.overallStatus mismatch")
        if req_summary.get("blockedUntilCount") != len(source_requirements.get("blockedUntil", [])):
            issues.append("sourceInputRequirements.blockedUntilCount mismatch")
        if req_summary.get("contentTypes") != sorted(content_types.keys()):
            issues.append("sourceInputRequirements.contentTypes mismatch")
        if req_summary.get("operationGapCount") != operation_gaps.get("entryCount"):
            issues.append("sourceInputRequirements.operationGapCount mismatch")
        if req_summary.get("operationGapBlockedFields") != operation_gaps.get("blockedFields"):
            issues.append("sourceInputRequirements.operationGapBlockedFields mismatch")

    return {
        "ok": not issues,
        "summaryPath": str(summary_path),
        "contentType": summary.get("contentType"),
        "draftValidationPassed": not draft_errors,
        "schemaGateExpectedFailure": bool(schema_errors),
        "sourceInputRequirementsBlocked": source_requirements.get("overallStatus") == "blocked",
        "sourceInputOperationGapCount": (
            source_requirements.get("operationGaps", {}).get("entryCount") if isinstance(source_requirements.get("operationGaps"), dict) else 0
        ),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS manifest rehearsal summary.")
    parser.add_argument("manifest_rehearsal_summary")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_rehearsal(Path(args.manifest_rehearsal_summary))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Manifest rehearsal validation passed.")
    else:
        print("Manifest rehearsal validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
