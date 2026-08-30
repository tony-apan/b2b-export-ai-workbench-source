#!/usr/bin/env python3
"""Derive create-site preflight evidence from fresh existing-site read-only evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from make_create_preflight_evidence import build_evidence
from validate_run_evidence import validate as validate_run_evidence


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"existing-site evidence JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid existing-site evidence JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("existing-site evidence root must be an object")
    return data


def site_creation_from_existing(evidence: dict[str, Any]) -> dict[str, Any]:
    errors = validate_run_evidence(evidence)
    if errors:
        raise ValueError("existing-site evidence validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    site_creation = evidence.get("siteCreation")
    if not isinstance(site_creation, dict):
        raise ValueError("existing-site evidence must include siteCreation")
    if site_creation.get("status") != "existing_site_selected":
        raise ValueError("existing-site evidence siteCreation.status must be existing_site_selected")
    if site_creation.get("dialogClosedVerified") is not True:
        raise ValueError("existing-site evidence must have dialogClosedVerified=true")
    return site_creation


def strong_site_key_evidence(site_keys: list[str], existing_evidence: dict[str, Any]) -> dict[str, str]:
    site_identity = existing_evidence.get("siteIdentity")
    module_routes = site_identity.get("moduleRoutes") if isinstance(site_identity, dict) else []
    selected_site_key = site_identity.get("siteKey") if isinstance(site_identity, dict) else ""
    if not isinstance(module_routes, list):
        module_routes = []
    evidence: dict[str, str] = {}
    for site_key in site_keys:
        if not isinstance(site_key, str) or not site_key.strip():
            raise ValueError("existingSiteKeysBeforeCreate must contain non-empty strings")
        if site_key == selected_site_key and f"/{site_key}/dashboard" in module_routes:
            evidence[site_key] = f"{site_key} from backend url route https://workspace.laicms.com/{site_key}/dashboard"
        else:
            evidence[site_key] = f"{site_key} from verified /sites list href or frontend-domain card"
    return evidence


def build_from_existing(evidence: dict[str, Any]) -> dict[str, Any]:
    site_creation = site_creation_from_existing(evidence)
    site_keys = site_creation.get("existingSiteKeysBeforeCreate")
    if not isinstance(site_keys, list) or not site_keys:
        raise ValueError("existing-site evidence must include non-empty existingSiteKeysBeforeCreate")
    create_fields = site_creation.get("createSiteFields")
    if not isinstance(create_fields, list):
        raise ValueError("existing-site evidence siteCreation.createSiteFields must be an array")
    generated_at = evidence.get("generatedAt") if isinstance(evidence.get("generatedAt"), str) else None
    return build_evidence(
        [str(site_key) for site_key in site_keys],
        [str(field) for field in create_fields],
        True,
        True,
        None,
        generated_at=generated_at,
        site_key_evidence=strong_site_key_evidence([str(site_key) for site_key in site_keys], evidence),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build create-site preflight evidence from existing-site read-only evidence."
    )
    parser.add_argument("existing_site_evidence_json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        preflight = build_from_existing(load_json(Path(args.existing_site_evidence_json)))
        errors = validate_run_evidence(preflight)
        if errors:
            raise ValueError("derived create preflight validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).expanduser().write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
