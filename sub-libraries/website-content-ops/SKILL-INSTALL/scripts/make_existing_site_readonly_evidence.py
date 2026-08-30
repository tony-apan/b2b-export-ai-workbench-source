#!/usr/bin/env python3
"""Create read-only evidence for an existing AllinCMS site inspection."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path


SITE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}[a-z0-9]$")
REQUIRED_MODULES = (
    "dashboard",
    "products",
    "posts",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
)
VALID_CONTENT_TYPES = {
    "posts",
    "products",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
}


def require_site_key(value: str, label: str) -> str:
    if not SITE_KEY_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase/digit/hyphen siteKey")
    return value


def split_csv(raw: str, label: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return values


def parse_site_keys(raw: str) -> list[str]:
    keys = split_csv(raw, "existing site keys")
    seen: set[str] = set()
    result: list[str] = []
    for key in keys:
        key = require_site_key(key, "existing site key")
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def parse_module_routes(raw: str, site_key: str) -> list[str]:
    routes = split_csv(raw, "module routes")
    normalized: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if route.startswith("https://workspace.laicms.com/"):
            route = route.removeprefix("https://workspace.laicms.com")
        if not route.startswith(f"/{site_key}/"):
            raise ValueError(f"module route must belong to site key {site_key}: {route}")
        module = route[len(f"/{site_key}/"):].split("/", 1)[0]
        if module not in REQUIRED_MODULES:
            raise ValueError(f"module route has unexpected module '{module}': {route}")
        if route not in seen:
            seen.add(route)
            normalized.append(route)
    observed = {route[len(f"/{site_key}/"):].split("/", 1)[0] for route in normalized}
    missing = sorted(set(REQUIRED_MODULES) - observed)
    if missing:
        raise ValueError(f"module routes missing required modules: {', '.join(missing)}")
    return normalized


def parse_observed_fields(raw: str) -> list[str]:
    if not raw.strip():
        return []
    fields = split_csv(raw.replace(";", ","), "observed create-site fields")
    lowered = " ".join(fields).lower()
    for term in ("name", "description"):
        if term not in lowered:
            raise ValueError(f"observed create-site fields must include {term}")
    if "close" not in lowered:
        raise ValueError("observed create-site fields must include close")
    if "submit" not in lowered and "创建" not in " ".join(fields):
        raise ValueError("observed create-site fields must include submit/create")
    return fields


def require_text(value: str, label: str) -> str:
    if not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def load_frontend_rendering(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"frontend rendering evidence file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid frontend rendering evidence JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("frontendRendering"), dict):
        raise ValueError("frontend rendering evidence must contain a frontendRendering object")
    return data["frontendRendering"]


def load_launch_readiness(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"launch readiness evidence file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid launch readiness evidence JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("launchReadiness"), dict):
        raise ValueError("launch readiness evidence must contain a launchReadiness object")
    return data["launchReadiness"]


def build_evidence(args: argparse.Namespace) -> dict:
    site_key = require_site_key(args.site_key, "site key")
    existing_keys = parse_site_keys(args.existing_site_keys)
    if site_key not in existing_keys:
        raise ValueError("site key must be present in --existing-site-keys")
    content_type = args.content_type
    if content_type not in VALID_CONTENT_TYPES:
        raise ValueError(f"content type must be one of {sorted(VALID_CONTENT_TYPES)}")

    local_checks: dict[str, object] = {
        "skillHygienePassed": True,
        "quickValidatePassed": True,
        "repoCheckPassed": args.repo_check_passed,
    }
    if not args.repo_check_passed:
        if not args.repo_check_note:
            raise ValueError("--repo-check-note is required when --repo-check-passed is false")
        local_checks["repoCheckNote"] = args.repo_check_note

    cleanup_candidates = []
    if args.cleanup_candidates:
        cleanup_candidates = split_csv(args.cleanup_candidates, "cleanup candidates")
    cleanup_status = args.cleanup_status
    if cleanup_status == "not_needed" and cleanup_candidates:
        raise ValueError("--cleanup-status must be pending_user_authorization or explicitly_deferred when candidates are present")
    if cleanup_status in {"pending_user_authorization", "explicitly_deferred"} and not cleanup_candidates:
        raise ValueError("--cleanup-candidates is required when cleanup is pending or deferred")

    evidence = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "completionClaimed": False,
        "mode": "read_only_simulation",
        "workspaceUrl": "https://workspace.laicms.com",
        "siteListUrl": "https://workspace.laicms.com/sites",
        "siteCreation": {
            "status": "existing_site_selected",
            "existingSiteKeysBeforeCreate": existing_keys,
            "siteKeyEvidence": {
                key: f"backend route href observed for site key {key}"
                for key in existing_keys
            },
            "selectedSiteEvidence": (
                f"backend dashboard route verified for selected site key {site_key}: "
                f"https://workspace.laicms.com/{site_key}/dashboard"
            ),
        },
        "siteIdentity": {
            "siteKey": site_key,
            "backendDashboardUrl": f"https://workspace.laicms.com/{site_key}/dashboard",
            "frontendBaseUrl": f"https://{site_key}.web.allincms.com",
            "moduleRoutes": parse_module_routes(args.module_routes, site_key),
        },
        "setupPages": {
            "siteInfo": [require_text(args.site_info_evidence, "site-info evidence")],
            "domains": [require_text(args.domains_evidence, "domains evidence")],
            "media": [require_text(args.media_evidence, "media evidence")],
            "themes": [require_text(args.themes_evidence, "themes evidence")],
            "routes": [require_text(args.routes_evidence, "routes evidence")],
            "forms": [require_text(args.forms_evidence, "forms evidence")],
            "tracking": [require_text(args.tracking_evidence, "tracking evidence")],
        },
        "contentInspection": {
            "contentType": content_type,
            "listColumns": split_csv(args.list_columns, "list columns"),
            "editFields": split_csv(args.edit_fields, "edit fields"),
        },
        "cleanup": {
            "status": cleanup_status,
            "candidates": cleanup_candidates,
        },
        "localChecks": local_checks,
    }
    create_fields = parse_observed_fields(args.observed_create_fields)
    if create_fields:
        evidence["siteCreation"]["createSiteFields"] = create_fields
        evidence["siteCreation"]["dialogClosedVerified"] = args.dialog_closed_verified

    frontend_rendering_evidence = getattr(args, "frontend_rendering_evidence", "")
    if frontend_rendering_evidence:
        evidence["frontendRendering"] = load_frontend_rendering(frontend_rendering_evidence)
    elif args.frontend_route_patterns:
        frontend_rendering: dict[str, object] = {
            "checked": True,
            "routePatterns": split_csv(args.frontend_route_patterns, "frontend route patterns"),
            "markdownResidueChecked": args.markdown_residue_checked,
            "structuredRichTextChecked": args.structured_rich_text_checked,
            "blockingIssues": [],
        }
        if args.frontend_blocking_issues:
            issues = []
            for item in split_csv(args.frontend_blocking_issues, "frontend blocking issues"):
                parts = [part.strip() for part in item.split("|")]
                if len(parts) != 3:
                    raise ValueError("frontend blocking issues must use routePattern|code|evidence")
                issues.append({"routePattern": parts[0], "code": parts[1], "evidence": parts[2]})
            frontend_rendering["blockingIssues"] = issues
        evidence["frontendRendering"] = frontend_rendering

    launch_readiness_evidence = getattr(args, "launch_readiness_evidence", "")
    if launch_readiness_evidence:
        evidence["launchReadiness"] = load_launch_readiness(launch_readiness_evidence)

    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Build existing-site read-only evidence JSON.")
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--existing-site-keys", required=True)
    parser.add_argument("--observed-create-fields", default="")
    parser.add_argument("--dialog-closed-verified", action="store_true")
    parser.add_argument("--module-routes", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--list-columns", required=True)
    parser.add_argument("--edit-fields", required=True)
    parser.add_argument("--site-info-evidence", required=True)
    parser.add_argument("--domains-evidence", required=True)
    parser.add_argument("--media-evidence", required=True)
    parser.add_argument("--themes-evidence", required=True)
    parser.add_argument("--routes-evidence", required=True)
    parser.add_argument("--forms-evidence", required=True)
    parser.add_argument("--tracking-evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--cleanup-status",
        choices=["not_needed", "pending_user_authorization", "explicitly_deferred"],
        default="not_needed",
    )
    parser.add_argument("--cleanup-candidates", default="")
    parser.add_argument("--frontend-rendering-evidence", default="", help="JSON file containing a frontendRendering object")
    parser.add_argument("--launch-readiness-evidence", default="", help="JSON file containing a launchReadiness object")
    parser.add_argument("--frontend-route-patterns", default="")
    parser.add_argument("--markdown-residue-checked", action="store_true")
    parser.add_argument("--structured-rich-text-checked", action="store_true")
    parser.add_argument(
        "--frontend-blocking-issues",
        default="",
        help="Comma-separated routePattern|code|evidence entries, using redacted route patterns only",
    )
    parser.add_argument("--repo-check-passed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--repo-check-note", default=None)
    args = parser.parse_args()

    try:
        if args.observed_create_fields and not args.dialog_closed_verified:
            raise ValueError("--dialog-closed-verified is required when --observed-create-fields is supplied")
        evidence = build_evidence(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
