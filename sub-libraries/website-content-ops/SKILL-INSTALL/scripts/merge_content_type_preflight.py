#!/usr/bin/env python3
"""Merge one content-type read-only preflight into created-site evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_run_evidence import validate as validate_run_evidence


CONTENT_TYPES = {"products", "posts"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_created_site(data: dict[str, Any]) -> str:
    errors = validate_run_evidence(data)
    if errors:
        raise ValueError("created evidence validation failed:\n- " + "\n- ".join(errors))
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "created_verified":
        raise ValueError("created evidence must have siteCreation.status=created_verified")
    identity = data.get("siteIdentity")
    if not isinstance(identity, dict) or not isinstance(identity.get("siteKey"), str):
        raise ValueError("created evidence must include siteIdentity.siteKey")
    if site_creation.get("createdSiteKey") != identity["siteKey"]:
        raise ValueError("createdSiteKey must match siteIdentity.siteKey")
    return identity["siteKey"]


def require_refresh(data: dict[str, Any], expected_site_key: str, content_type: str) -> dict[str, Any]:
    errors = validate_run_evidence(data)
    if errors:
        raise ValueError("refresh evidence validation failed:\n- " + "\n- ".join(errors))
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "existing_site_selected":
        raise ValueError("refresh evidence must have siteCreation.status=existing_site_selected")
    identity = data.get("siteIdentity")
    if not isinstance(identity, dict) or identity.get("siteKey") != expected_site_key:
        raise ValueError("refresh evidence siteKey must match created evidence siteKey")
    inspection = data.get("contentInspection")
    if not isinstance(inspection, dict):
        raise ValueError("refresh evidence must include contentInspection")
    if inspection.get("contentType") != content_type:
        raise ValueError(f"refresh evidence contentInspection.contentType must be {content_type}")
    if not isinstance(inspection.get("listColumns"), list) or not inspection["listColumns"]:
        raise ValueError("refresh evidence contentInspection.listColumns must be non-empty")
    if not isinstance(inspection.get("editFields"), list) or not inspection["editFields"]:
        raise ValueError("refresh evidence contentInspection.editFields must be non-empty")
    return inspection


def merge_content_preflight(
    created: dict[str, Any],
    refresh: dict[str, Any],
    *,
    refresh_path: Path,
    content_type: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if content_type not in CONTENT_TYPES:
        raise ValueError(f"content type must be one of {sorted(CONTENT_TYPES)}")
    site_key = require_created_site(created)
    inspection = require_refresh(refresh, site_key, content_type)

    merged = json.loads(json.dumps(created, ensure_ascii=False))
    existing_map = merged.get("contentTypePreflights")
    if existing_map is None:
        existing_map = {}
    if not isinstance(existing_map, dict):
        raise ValueError("created evidence contentTypePreflights must be an object when present")
    entry = {
        "contentType": content_type,
        "listColumns": inspection["listColumns"],
        "editFields": inspection["editFields"],
        "sourceReadOnlyEvidence": str(refresh_path),
        "mergedEvidence": str(output_path) if output_path is not None else "",
        "readyForCreateProbeGate": True,
        "remoteMutationsPerformed": False,
    }
    existing_map[content_type] = entry
    merged["contentTypePreflights"] = existing_map
    # Keep top-level contentInspection aligned with this target so existing gates can use the merged file directly.
    merged["contentInspection"] = {
        "contentType": content_type,
        "listColumns": inspection["listColumns"],
        "editFields": inspection["editFields"],
    }
    local_checks = merged.setdefault("localChecks", {})
    if not isinstance(local_checks, dict):
        raise ValueError("created evidence localChecks must be an object when present")
    local_checks["contentTypePreflightMerged"] = str(refresh_path)
    local_checks["contentTypePreflightContentType"] = content_type
    local_checks["contentTypePreflightMergeNote"] = (
        "Read-only content list/edit evidence was merged for one content type; "
        "created-site submit proof, generatedAt, and authorization remain from the original created evidence."
    )
    errors = validate_run_evidence(merged)
    if errors:
        raise ValueError("merged evidence validation failed:\n- " + "\n- ".join(errors))
    return merged


def validate_merge_result(data: dict[str, Any], content_type: str) -> list[str]:
    issues: list[str] = []
    if data.get("mode") != "site_creation":
        issues.append("mode must remain site_creation")
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "created_verified":
        issues.append("siteCreation.status must remain created_verified")
    inspection = data.get("contentInspection")
    if not isinstance(inspection, dict) or inspection.get("contentType") != content_type:
        issues.append("top-level contentInspection must match merged content type")
    preflights = data.get("contentTypePreflights")
    if not isinstance(preflights, dict) or content_type not in preflights:
        issues.append("contentTypePreflights must include merged content type")
    else:
        entry = preflights[content_type]
        if not isinstance(entry, dict) or entry.get("readyForCreateProbeGate") is not True:
            issues.append("merged preflight entry must be readyForCreateProbeGate=true")
        if isinstance(entry, dict) and entry.get("remoteMutationsPerformed") is not False:
            issues.append("merged preflight entry must not perform remote mutations")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge one content-type read-only preflight into created-site evidence.")
    parser.add_argument("--created-evidence", required=True)
    parser.add_argument("--refresh-evidence", required=True)
    parser.add_argument("--content-type", required=True, choices=sorted(CONTENT_TYPES))
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        refresh_path = Path(args.refresh_evidence)
        merged = merge_content_preflight(
            load_json(Path(args.created_evidence)),
            load_json(refresh_path),
            refresh_path=refresh_path,
            content_type=args.content_type,
            output_path=Path(args.output),
        )
        issues = validate_merge_result(merged, args.content_type)
        if issues:
            raise ValueError("merge result validation failed:\n- " + "\n- ".join(issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_json(Path(args.output), merged)
    print(f"Wrote merged content-type preflight evidence: {args.output}")
    if args.json:
        print(json.dumps(merged, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
