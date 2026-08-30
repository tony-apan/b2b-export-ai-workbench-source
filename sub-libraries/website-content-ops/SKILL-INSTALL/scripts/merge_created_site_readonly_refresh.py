#!/usr/bin/env python3
"""Merge current read-only setup evidence into older created-site evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_run_evidence import validate as validate_run_evidence


MERGEABLE_SETUP_KEYS = ("siteInfo", "domains", "themes", "routes", "forms", "tracking")


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
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "created_verified":
        raise ValueError("created evidence must have siteCreation.status=created_verified")
    site_identity = data.get("siteIdentity")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("created evidence must include siteIdentity.siteKey")
    created_key = site_creation.get("createdSiteKey")
    site_key = site_identity["siteKey"]
    if created_key != site_key:
        raise ValueError("createdSiteKey must match siteIdentity.siteKey")
    return site_key


def require_readonly_site(data: dict[str, Any], expected_site_key: str) -> None:
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "existing_site_selected":
        raise ValueError("refresh evidence must have siteCreation.status=existing_site_selected")
    site_identity = data.get("siteIdentity")
    if not isinstance(site_identity, dict) or site_identity.get("siteKey") != expected_site_key:
        raise ValueError("refresh evidence siteKey must match created evidence siteKey")
    if not isinstance(data.get("setupPages"), dict):
        raise ValueError("refresh evidence must include setupPages")


def merge_evidence(created: dict[str, Any], refresh: dict[str, Any], refresh_path: Path) -> dict[str, Any]:
    site_key = require_created_site(created)
    require_readonly_site(refresh, site_key)

    merged = json.loads(json.dumps(created, ensure_ascii=False))
    setup_pages = merged.setdefault("setupPages", {})
    if not isinstance(setup_pages, dict):
        raise ValueError("created evidence setupPages must be an object when present")
    refresh_setup = refresh["setupPages"]
    for key in MERGEABLE_SETUP_KEYS:
        value = refresh_setup.get(key)
        if isinstance(value, list) and value:
            setup_pages[key] = value

    # Keep original created-site timestamp and authorization as the create proof.
    local_checks = merged.setdefault("localChecks", {})
    if not isinstance(local_checks, dict):
        raise ValueError("created evidence localChecks must be an object when present")
    local_checks["readOnlyRefreshMerged"] = str(refresh_path)
    local_checks["readOnlyRefreshMergeNote"] = (
        "Current setup-page evidence was merged from a read-only refresh; "
        "created-site submit proof, generatedAt, and authorization remain from the original created evidence."
    )
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge read-only setup evidence into created-site evidence.")
    parser.add_argument("--created-evidence", required=True)
    parser.add_argument("--refresh-evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--validate", action="store_true", help="Validate merged run evidence before writing success")
    args = parser.parse_args()

    try:
        refresh_path = Path(args.refresh_evidence)
        merged = merge_evidence(load_json(Path(args.created_evidence)), load_json(refresh_path), refresh_path)
        if args.validate:
            errors = validate_run_evidence(merged)
            if errors:
                raise ValueError("merged evidence validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_json(Path(args.output), merged)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
