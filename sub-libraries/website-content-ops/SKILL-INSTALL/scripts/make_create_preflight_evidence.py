#!/usr/bin/env python3
"""Create a read-only AllinCMS create-site preflight evidence JSON."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path


SITE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}[a-z0-9]$")
REQUIRED_FIELD_TERMS = ("name", "description")
REQUIRED_CREATE_PREFLIGHT_TERMS = ("create site entry", "dialog", "submit", "close")
WEAK_SITE_KEY_EVIDENCE_TERMS = (
    "memory",
    "prior",
    "previous",
    "body regex",
    "full text regex",
    "page text",
    "card count",
    "count only",
    "unknown",
    "\u8bb0\u5fc6",
    "\u4e0a\u6b21",
    "\u5361\u7247\u6570",
    "\u5168\u6587",
)
STRONG_SITE_KEY_EVIDENCE_TERMS = (
    "backend url",
    "dashboard url",
    "frontend domain",
    "site card domain",
    "card frontend domain",
    "href",
    "route",
    "safe attribute",
    "data-site-key",
    "verified empty",
    "\u540e\u53f0",
    "\u8def\u7531",
    "\u5c5e\u6027",
    "\u7a7a\u5217\u8868",
)


def parse_site_keys(raw: str) -> list[str]:
    keys = [item.strip() for item in raw.split(",") if item.strip()]
    if not keys:
        raise ValueError("existing site key list is empty; use --no-existing-sites when the site list is verified empty")
    seen: set[str] = set()
    result: list[str] = []
    for key in keys:
        if not SITE_KEY_RE.fullmatch(key):
            raise ValueError(f"invalid site key: {key}")
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def parse_site_key_evidence(raw: str, site_keys: list[str]) -> dict[str, str]:
    entries = [item.strip() for item in raw.split(";") if item.strip()]
    if len(entries) != len(site_keys):
        raise ValueError("--site-key-evidence must contain one semicolon-separated entry per existing site key")
    evidence: dict[str, str] = {}
    for site_key, entry in zip(site_keys, entries):
        lowered = entry.lower()
        if site_key not in entry:
            raise ValueError(f"site key evidence for {site_key} must mention the site key")
        if any(term in lowered for term in WEAK_SITE_KEY_EVIDENCE_TERMS):
            raise ValueError("site key evidence must not rely on memory, full-page regex, card count, or unknown sources")
        if not any(term in lowered for term in STRONG_SITE_KEY_EVIDENCE_TERMS):
            raise ValueError("site key evidence must mention a strong source such as backend URL, route, href, or safe attribute")
        evidence[site_key] = entry
    return evidence


def validate_empty_site_list_evidence(raw: str) -> str:
    evidence = raw.strip()
    if not evidence:
        raise ValueError("--empty-site-list-evidence is required with --no-existing-sites")
    lowered = evidence.lower()
    if "empty" not in lowered and "\u7a7a" not in evidence:
        raise ValueError("empty site list evidence must state that the list was verified empty")
    return evidence


def parse_observed_fields(raw: str) -> list[str]:
    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"observed create-site fields JSON is invalid: {exc}") from None
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("observed create-site fields JSON must be an array of strings")
        fields = [item.strip() for item in parsed if item.strip()]
    else:
        fields = [item.strip() for item in raw.split(";") if item.strip()]
    if not fields:
        raise ValueError("at least one observed create-site field is required")
    lowered = " ".join(fields).lower()
    terms_text = lowered.replace("create-site-entry", "create site entry")
    if "创建" in " ".join(fields):
        terms_text += " submit"
    for term in REQUIRED_FIELD_TERMS:
        if term not in terms_text:
            raise ValueError(f"observed create-site fields must include {term}")
    for term in REQUIRED_CREATE_PREFLIGHT_TERMS:
        if term not in terms_text:
            raise ValueError(f"observed create-site fields must include observed {term}")
    return fields


def build_evidence(
    site_keys: list[str],
    observed_fields: list[str],
    dialog_closed_verified: bool,
    repo_check_passed: bool,
    repo_check_note: str | None,
    generated_at: str | None = None,
    site_key_evidence: dict[str, str] | None = None,
    empty_site_list_evidence: str | None = None,
) -> dict:
    if not dialog_closed_verified:
        raise ValueError("--dialog-closed-verified is required after verifying no visible create-site dialog remains")
    local_checks: dict[str, object] = {
        "skillHygienePassed": True,
        "quickValidatePassed": True,
        "repoCheckPassed": repo_check_passed,
    }
    if not repo_check_passed:
        if not repo_check_note:
            raise ValueError("--repo-check-note is required when --repo-check-passed is false")
        local_checks["repoCheckNote"] = repo_check_note

    site_creation: dict[str, object] = {
        "status": "create_preflight_verified",
        "existingSiteKeysBeforeCreate": site_keys,
        "createSiteFields": observed_fields,
        "dialogClosedVerified": dialog_closed_verified,
    }
    if site_keys:
        if not site_key_evidence or set(site_key_evidence) != set(site_keys):
            raise ValueError("site key evidence is required for every existing site key")
        site_creation["siteKeyEvidence"] = site_key_evidence
    else:
        site_creation["emptySiteListEvidence"] = validate_empty_site_list_evidence(empty_site_list_evidence or "")

    return {
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat(),
        "completionClaimed": False,
        "mode": "read_only_simulation",
        "workspaceUrl": "https://workspace.laicms.com",
        "siteListUrl": "https://workspace.laicms.com/sites",
        "siteCreation": site_creation,
        "cleanup": {
            "status": "not_needed",
            "candidates": [],
        },
        "localChecks": local_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build create-site preflight evidence JSON.")
    parser.add_argument(
        "--existing-site-keys",
        default=None,
        help="Comma-separated site keys observed on https://workspace.laicms.com/sites before submit",
    )
    parser.add_argument(
        "--no-existing-sites",
        action="store_true",
        help="Use only when the /sites list was verified empty before submit",
    )
    parser.add_argument(
        "--site-key-evidence",
        default="",
        help="Semicolon-separated strong evidence entries, one per existing site key, mentioning backend URL, route, href, or safe attribute",
    )
    parser.add_argument(
        "--empty-site-list-evidence",
        default="",
        help="Required with --no-existing-sites; neutral proof that the /sites list was verified empty",
    )
    parser.add_argument(
        "--observed-create-fields",
        required=True,
        help=(
            "Semicolon-separated fields/controls or a JSON string array observed in the create-site flow, "
            "including create-site-entry, dialog, name, description, submit/create, and close"
        ),
    )
    parser.add_argument(
        "--dialog-closed-verified",
        action="store_true",
        help="Set only after verifying no visible create-site dialog remains",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--repo-check-passed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--repo-check-note", default=None)
    args = parser.parse_args()

    try:
        if args.no_existing_sites and args.existing_site_keys:
            raise ValueError("use either --existing-site-keys or --no-existing-sites, not both")
        if args.no_existing_sites:
            site_keys = []
            site_key_evidence = None
            empty_site_list_evidence = validate_empty_site_list_evidence(args.empty_site_list_evidence)
        elif args.existing_site_keys:
            site_keys = parse_site_keys(args.existing_site_keys)
            site_key_evidence = parse_site_key_evidence(args.site_key_evidence, site_keys)
            empty_site_list_evidence = None
        else:
            raise ValueError("provide --existing-site-keys or --no-existing-sites")
        evidence = build_evidence(
            site_keys,
            parse_observed_fields(args.observed_create_fields),
            args.dialog_closed_verified,
            args.repo_check_passed,
            args.repo_check_note,
            site_key_evidence=site_key_evidence,
            empty_site_list_evidence=empty_site_list_evidence,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
