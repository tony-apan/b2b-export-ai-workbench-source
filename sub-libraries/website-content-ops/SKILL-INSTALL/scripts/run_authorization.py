#!/usr/bin/env python3
"""Run-scoped authorization: one upfront grant that auto-covers the in-scope content build.

Model (user-approved 2026-07-05): instead of prompting the user for a fresh authorization
before EVERY remote mutation, the user grants ONE run-scoped authorization at the content-intent
confirmation point (after reviewing the prepared package). That grant is bound to a single target
`siteKey` and the confirmed package hash, and it auto-covers only the repetitive, in-scope content
build actions (allowlist below). It removes the repeated PROMPT, not the gates: every covered
action still flows through `check_pre_mutation_gate.py` (preflight/schema/evidence/freshness) via a
DERIVED per-action authorization, and a gate FAILURE still stops.

Hard carve-outs (always require an explicit fresh per-action authorization, even under a run-auth):
creating a NEW site, delete/cleanup/unpublish, any outward-facing setting (domains, tracking,
forms/webhooks, site-settings saves), operating on a site whose key != the authorized one, and any
action not on the allowlist (including unknown/future actions — allowlist is the safe default). PII
/ contact / price are never a mutation the run-auth covers — they are user-supplied content, never
fabricated (that rule is enforced upstream in content preparation, not here).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RUN_AUTH_KIND = "allincms_run_authorization"
WORKSPACE_ORIGIN = "https://workspace.laicms.com"
# A run-scoped grant is bound to ONE build session. Past this TTL it stops auto-covering and the
# user must re-grant, so a stale grant from an earlier session can't silently keep authorizing.
DEFAULT_TTL_HOURS = 8

# Allowlist: the repetitive, in-scope content-build actions a run-scoped grant may auto-cover.
# Anything NOT here (create_site, delete_or_cleanup, unpublish, cleanup_probe, add_domain,
# add_tracking_tag, create_form, create_form_probe, save_site_settings, or any unknown/future
# action) is a carve-out and still needs an explicit per-action authorization.
COVERED_ACTIONS = frozenset({
    # taxonomy on the authorized site
    "create_or_map_products_category", "create_or_map_posts_category",
    "create_or_map_products_tag", "create_or_map_posts_tag",
    # product/post create, save, publish
    "create_draft", "create_product_probe", "create_post_probe",
    "save_product", "save_post", "save_probe",
    "publish", "publish_product", "publish_post", "publish_probe",
    # batch
    "batch_upload", "batch_publish",
    # media upload of the package's hosted images
    "upload_media",
    # theme/route build for the authorized site's presentation (not new-site / delete / outward)
    "create_theme", "activate_theme", "create_theme_page", "enable_theme_page",
    "save_design", "publish_design", "set_homepage", "create_route", "bind_route",
})

_SITE_KEY_RE = re.compile(r"^[a-z0-9]{6,}$")
# Match actual secret VALUES (not field names): an email, or a credential/header assignment.
_SENSITIVE_VALUE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|(?:cookie|bearer|password|passwd|token|api[_-]?key|next-action)\s*[:=]\s*\S{6,}"
    r"|\bBearer\s+[A-Za-z0-9._~+/=-]{12,}",
    re.IGNORECASE,
)


def _string_values(obj: Any) -> list[str]:
    if isinstance(obj, dict):
        out: list[str] = []
        for v in obj.values():
            out.extend(_string_values(v))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_string_values(v))
        return out
    return [obj] if isinstance(obj, str) else []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def validate_run_authorization(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["run authorization must be a JSON object"]
    if record.get("kind") != RUN_AUTH_KIND:
        errors.append(f"kind must be {RUN_AUTH_KIND}")
    if record.get("workspace") != WORKSPACE_ORIGIN:
        errors.append(f"workspace must be {WORKSPACE_ORIGIN}")
    if record.get("mode") != "run_scoped_auto":
        errors.append("mode must be 'run_scoped_auto'")
    site_key = record.get("siteKey", "")
    if not isinstance(site_key, str) or not _SITE_KEY_RE.match(site_key):
        errors.append("siteKey must be a lowercase alphanumeric site key")
    if not isinstance(record.get("packageHash"), str) or not record["packageHash"].strip():
        errors.append("packageHash is required (binds the grant to the reviewed content package)")
    if not isinstance(record.get("confirmedItemCount"), int) or record["confirmedItemCount"] < 0:
        errors.append("confirmedItemCount must be a non-negative integer")
    ga = record.get("generatedAt")
    ga_dt = _parse_iso(ga) if isinstance(ga, str) else None
    if not isinstance(ga, str) or not ga.strip():
        errors.append("generatedAt is required")
    elif ga_dt is None:
        errors.append("generatedAt must be an ISO 8601 timestamp")
    ea = record.get("expiresAt")
    ea_dt = _parse_iso(ea) if isinstance(ea, str) else None
    if not isinstance(ea, str) or not ea.strip():
        errors.append("expiresAt is required (a run-scoped grant must expire so it can't outlive its session)")
    elif ea_dt is None:
        errors.append("expiresAt must be an ISO 8601 timestamp")
    elif ga_dt is not None and ea_dt <= ga_dt:
        errors.append("expiresAt must be after generatedAt")
    covered = record.get("coveredActions")
    if not isinstance(covered, list) or not covered:
        errors.append("coveredActions must be a non-empty list")
    else:
        bad = [a for a in covered if a not in COVERED_ACTIONS]
        if bad:
            errors.append(f"coveredActions may only include allowlisted content-build actions; not: {sorted(bad)}")
    auth = record.get("authorization")
    if not isinstance(auth, dict):
        errors.append("authorization object is required")
    else:
        if auth.get("userAuthorized") is not True:
            errors.append("authorization.userAuthorized must be true")
        for key in ("grantScope", "verificationPlan"):
            if not isinstance(auth.get(key), str) or not auth[key].strip():
                errors.append(f"authorization.{key} is required")
    # never store secrets/PII in the grant (scan values only, not field names)
    if any(_SENSITIVE_VALUE.search(v) for v in _string_values(record)):
        errors.append("run authorization must not contain cookies, tokens, passwords, or email/PII")
    return errors


def run_authorization_covers(record: dict, action: str, site_key: str,
                             now: datetime | None = None) -> tuple[bool, str]:
    """Return (covered, reason). Covered only for an in-scope action on the authorized site
    while the grant is still within its TTL — an expired grant falls back to explicit auth."""
    if validate_run_authorization(record):
        return False, "run authorization is invalid; use an explicit per-action authorization"
    now = now or datetime.now(timezone.utc)
    expires = _parse_iso(record.get("expiresAt", ""))
    if expires is None or now >= expires:
        return False, (f"carve-out: run authorization expired at {record.get('expiresAt')!r}; "
                       "re-grant a fresh run authorization at the content-review point")
    if str(site_key) != record.get("siteKey"):
        return False, f"carve-out: action targets site {site_key!r}, not the authorized {record.get('siteKey')!r}"
    if action not in COVERED_ACTIONS:
        return False, f"carve-out: {action} is not an auto-covered content-build action; needs explicit authorization"
    if action not in set(record.get("coveredActions", [])):
        return False, f"carve-out: {action} was not granted in this run authorization's coveredActions"
    return True, "covered by run-scoped authorization"


def derive_action_authorization(record: dict, action: str, target: str, *, target_identifier: str = "",
                                expected_result: str = "", verification_plan: str = "",
                                fields_or_files: list | None = None) -> dict:
    """Emit a FULL per-action authorization (accepted by make_authorization_record.validate_record)
    for a covered action, so the existing pre-mutation gate needs no fresh human prompt. Raises
    ValueError for a carve-out / out-of-scope / invalid run-auth — those still need explicit auth."""
    covered, reason = run_authorization_covers(record, action, record.get("siteKey", ""))
    if not covered:
        raise ValueError(reason)
    pkg = record["packageHash"]
    vplan = verification_plan or record.get("authorization", {}).get("verificationPlan") or (
        "backend re-read (isDraft:false + content) then public frontend verify; stop on any gate failure")
    source = f"run_scoped_authorization: package {pkg} action {action} at {target}"
    return {
        "workspace": WORKSPACE_ORIGIN,
        "generatedAt": now_iso(),
        "action": action,
        "siteKey": record["siteKey"],
        "target": target,
        "targetType": action,
        "targetIdentifier": target_identifier or f"{action}@{record['siteKey']}",
        "expectedResult": expected_result or f"{action} persisted for the confirmed package on {record['siteKey']}",
        "verificationPlan": vplan,
        "cleanupPlan": "in-scope content build; cleanup/delete remains a carve-out requiring separate authorization",
        "fieldsOrFiles": list(fields_or_files or []),
        "authorization": {
            "userAuthorized": True,
            "authorizedAction": action,
            "target": target,
            "authorizationSource": source,
            "verificationPlan": vplan,
        },
        "derivedFromRunAuthorization": {"packageHash": pkg, "grantedAt": record.get("generatedAt"),
                                        "expiresAt": record.get("expiresAt")},
    }


def build_record(args: argparse.Namespace) -> dict:
    covered = [a.strip() for a in (args.covered_actions or "").split(",") if a.strip()] or sorted(COVERED_ACTIONS)
    generated = datetime.now(timezone.utc)
    ttl_hours = float(getattr(args, "ttl_hours", DEFAULT_TTL_HOURS) or DEFAULT_TTL_HOURS)
    return {
        "kind": RUN_AUTH_KIND,
        "workspace": WORKSPACE_ORIGIN,
        "generatedAt": generated.isoformat(timespec="seconds"),
        "expiresAt": (generated + timedelta(hours=ttl_hours)).isoformat(timespec="seconds"),
        "mode": "run_scoped_auto",
        "siteKey": args.site_key,
        "packageHash": args.package_hash,
        "confirmedItemCount": int(args.confirmed_item_count),
        "coveredActions": covered,
        "carveOutsAlwaysReconfirm": [
            "create_site", "delete_or_cleanup", "unpublish", "cleanup_probe",
            "add_domain", "add_tracking_tag", "create_form", "create_form_probe", "save_site_settings",
            "any site other than siteKey", "any action not in coveredActions", "any gate failure",
            "entering PII / contact / price (never fabricated)",
        ],
        "authorization": {
            "userAuthorized": True,
            "grantScope": args.grant_scope,
            "verificationPlan": args.verification_plan
            or "backend re-read + public frontend verification per covered action; stop on any carve-out or gate failure",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or validate a run-scoped authorization record.")
    parser.add_argument("--validate-only", help="Validate an existing run-authorization JSON instead of writing one")
    parser.add_argument("--site-key")
    parser.add_argument("--package-hash")
    parser.add_argument("--confirmed-item-count", default="0")
    parser.add_argument("--grant-scope", help="the user's own words granting run-scoped auto for this package/site")
    parser.add_argument("--covered-actions", default="", help="comma list; defaults to all allowlisted content-build actions")
    parser.add_argument("--ttl-hours", type=float, default=DEFAULT_TTL_HOURS,
                        help=f"hours the grant stays valid before re-consent is required (default {DEFAULT_TTL_HOURS})")
    parser.add_argument("--verification-plan", default="")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        try:
            record = json.loads(Path(args.validate_only).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        errors = validate_run_authorization(record)
        if errors:
            for e in errors:
                print(f"  [run-auth] {e}")
            return 1
        print("run authorization valid.")
        return 0

    if not (args.site_key and args.package_hash and args.grant_scope):
        print("ERROR: --site-key, --package-hash, and --grant-scope are required to build a run authorization", file=sys.stderr)
        return 2
    record = build_record(args)
    errors = validate_run_authorization(record)
    if errors:
        for e in errors:
            print(f"  [run-auth] {e}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).expanduser().write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(f"run authorization written for site {record['siteKey']} covering {len(record['coveredActions'])} action classes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
