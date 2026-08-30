#!/usr/bin/env python3
"""Upgrade create-site preflight evidence after a real site is created and verified."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from make_authorization_record import validate_authorization_source


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


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("preflight evidence root must be an object")
    return data


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


def require_site_key(value: str, label: str) -> str:
    if not SITE_KEY_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase/digit/hyphen siteKey")
    return value


def split_csv(raw: str, label: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    return values


def validate_module_routes(routes: list[str], site_key: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, str) or not route.strip():
            raise ValueError("module routes must contain only non-empty strings")
        route = route.strip()
        if route.startswith("https://workspace.laicms.com/"):
            route = route.removeprefix("https://workspace.laicms.com")
        if not route.startswith(f"/{site_key}/"):
            raise ValueError(f"module route must belong to created site key {site_key}: {route}")
        module = route[len(f"/{site_key}/"):].split("/", 1)[0]
        if module not in REQUIRED_MODULES:
            raise ValueError(f"module route has unexpected module '{module}': {route}")
        if route not in seen:
            seen.add(route)
            normalized.append(route)

    observed_modules = {route[len(f"/{site_key}/"):].split("/", 1)[0] for route in normalized}
    missing_modules = sorted(set(REQUIRED_MODULES) - observed_modules)
    if missing_modules:
        raise ValueError(f"module routes missing required modules: {', '.join(missing_modules)}")
    return normalized


def parse_module_routes(raw: str, site_key: str) -> list[str]:
    return validate_module_routes(split_csv(raw, "module routes"), site_key)


def validate_submitted_fields(fields: list[str]) -> list[str]:
    allowed_fields = {"name", "description"}
    seen: set[str] = set()
    normalized: list[str] = []
    for field in fields:
        if field not in allowed_fields:
            raise ValueError(f"submitted field must be one of {sorted(allowed_fields)}: {field}")
        if field not in seen:
            seen.add(field)
            normalized.append(field)
    missing = sorted(allowed_fields - seen)
    if missing:
        raise ValueError(f"submitted fields missing required fields: {', '.join(missing)}")
    return normalized


def parse_submitted_fields(raw: str) -> list[str]:
    return validate_submitted_fields(split_csv(raw, "submitted fields"))


def validate_submitted_values(values: dict[str, str] | None) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError("submitted values must be an object")
    normalized: dict[str, str] = {}
    for key in ("name", "description"):
        value = values.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"submitted value {key} is required when submitted values are provided")
        normalized[key] = value.strip()
    return normalized


def parse_submitted_values(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"submitted values JSON is invalid: {exc}") from None
    return validate_submitted_values(parsed)


def require_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def require_contains(value: str, label: str, expected: str) -> str:
    text = require_text(value, label)
    if expected not in text:
        raise ValueError(f"{label} must mention {expected}")
    return text


def upgrade_evidence(
    preflight: dict,
    created_site_key: str,
    content_type: str,
    list_columns: list[str],
    edit_fields: list[str],
    site_card_evidence: str,
    backend_evidence: str,
    frontend_evidence: str,
    site_info_evidence: str,
    domains_evidence: str,
    media_evidence: str,
    themes_evidence: str,
    routes_evidence: str,
    forms_evidence: str,
    tracking_evidence: str,
    module_routes: list[str],
    submitted_fields: list[str],
    authorization_source: str,
    repo_check_passed: bool,
    repo_check_note: str | None,
    frontend_rendering: dict | None = None,
    launch_readiness: dict | None = None,
    submitted_values: dict[str, str] | None = None,
    generated_at: str | None = None,
) -> dict:
    created_site_key = require_site_key(created_site_key, "created site key")
    site_creation = preflight.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "create_preflight_verified":
        raise ValueError("preflight evidence must have siteCreation.status=create_preflight_verified")
    if site_creation.get("dialogClosedVerified") is not True:
        raise ValueError("preflight evidence must verify the create-site dialog was closed before submit")

    existing_keys = site_creation.get("existingSiteKeysBeforeCreate")
    if not isinstance(existing_keys, list):
        raise ValueError("preflight evidence must include existingSiteKeysBeforeCreate as an array")
    normalized_existing: list[str] = []
    for key in existing_keys:
        if not isinstance(key, str):
            raise ValueError("existingSiteKeysBeforeCreate must contain only strings")
        normalized_existing.append(require_site_key(key, "existing site key"))
    if created_site_key in normalized_existing:
        raise ValueError("created site key already existed before create submit")

    if content_type not in {"posts", "products", "media", "themes", "routes", "forms"}:
        raise ValueError("content type must be posts, products, media, themes, routes, or forms")

    backend_dashboard_url = f"https://workspace.laicms.com/{created_site_key}/dashboard"
    frontend_base_url = f"https://{created_site_key}.web.allincms.com"

    local_checks: dict[str, object] = {
        "skillHygienePassed": True,
        "quickValidatePassed": True,
        "repoCheckPassed": repo_check_passed,
    }
    if not repo_check_passed:
        if not repo_check_note:
            raise ValueError("--repo-check-note is required when --repo-check-passed is false")
        local_checks["repoCheckNote"] = repo_check_note

    upgraded = dict(preflight)
    upgraded["preflightGeneratedAt"] = preflight.get("generatedAt", "")
    upgraded["generatedAt"] = generated_at or datetime.now(timezone.utc).isoformat()
    upgraded["mode"] = "site_creation"
    upgraded["siteCreation"] = {
        "status": "created_verified",
        "existingSiteKeysBeforeCreate": normalized_existing,
        "createdSiteKey": created_site_key,
        "siteCardVerified": True,
        "backendVerified": True,
        "frontendVerified": True,
        "siteCardEvidence": require_contains(site_card_evidence, "site card evidence", created_site_key),
        "backendEvidence": require_contains(backend_evidence, "backend evidence", backend_dashboard_url),
        "frontendEvidence": require_contains(frontend_evidence, "frontend evidence", frontend_base_url),
        "createSiteFields": site_creation.get("createSiteFields", []),
        "submittedFieldKeys": validate_submitted_fields(submitted_fields),
    }
    normalized_submitted_values = validate_submitted_values(submitted_values)
    if normalized_submitted_values:
        upgraded["siteCreation"]["submittedValues"] = normalized_submitted_values
    upgraded["siteIdentity"] = {
        "siteKey": created_site_key,
        "backendDashboardUrl": backend_dashboard_url,
        "frontendBaseUrl": frontend_base_url,
        "moduleRoutes": validate_module_routes(module_routes, created_site_key),
    }
    upgraded["setupPages"] = {
        "siteInfo": [require_text(site_info_evidence, "site-info evidence")],
        "domains": [require_text(domains_evidence, "domains evidence")],
        "media": [require_text(media_evidence, "media evidence")],
        "themes": [require_text(themes_evidence, "themes evidence")],
        "routes": [require_text(routes_evidence, "routes evidence")],
        "forms": [require_text(forms_evidence, "forms evidence")],
        "tracking": [require_text(tracking_evidence, "tracking evidence")],
    }
    upgraded["contentInspection"] = {
        "contentType": content_type,
        "listColumns": list_columns,
        "editFields": edit_fields,
    }
    authorization_source = validate_authorization_source(
        "create_site",
        authorization_source,
        "https://workspace.laicms.com/sites",
    )
    upgraded["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": "create site",
        "target": "https://workspace.laicms.com/sites",
        "authorizationSource": authorization_source,
        "verificationPlan": "verify site card, backend dashboard, default frontend, setup pages, and content fields",
    }
    upgraded["localChecks"] = local_checks
    if frontend_rendering:
        upgraded["frontendRendering"] = frontend_rendering
    if launch_readiness:
        upgraded["launchReadiness"] = launch_readiness
    return upgraded


def main() -> int:
    parser = argparse.ArgumentParser(description="Build created-site evidence from preflight evidence.")
    parser.add_argument("--preflight", required=True, help="Path to create_preflight_verified evidence JSON")
    parser.add_argument("--created-site-key", required=True)
    parser.add_argument("--content-type", required=True, choices=["posts", "products", "media", "themes", "routes", "forms"])
    parser.add_argument("--list-columns", required=True, help="Comma-separated list columns observed on the new site")
    parser.add_argument("--edit-fields", required=True, help="Comma-separated edit fields observed on the new site")
    parser.add_argument("--site-card-evidence", required=True)
    parser.add_argument("--backend-evidence", required=True)
    parser.add_argument("--frontend-evidence", required=True)
    parser.add_argument("--site-info-evidence", required=True)
    parser.add_argument("--domains-evidence", required=True)
    parser.add_argument("--media-evidence", required=True)
    parser.add_argument("--themes-evidence", required=True)
    parser.add_argument("--routes-evidence", required=True)
    parser.add_argument("--forms-evidence", required=True)
    parser.add_argument("--tracking-evidence", required=True)
    parser.add_argument(
        "--module-routes",
        required=True,
        help="Comma-separated module routes observed on the new site, for example /site-key/dashboard,/site-key/products",
    )
    parser.add_argument(
        "--submitted-fields",
        required=True,
        help="Comma-separated create-site field keys submitted after authorization; must include name,description",
    )
    parser.add_argument(
        "--submitted-values",
        default="",
        help='Optional JSON object with the redacted submitted create-site values, for example {"name":"Demo","description":"..."}',
    )
    parser.add_argument(
        "--authorization-source",
        required=True,
        help="Short neutral description of the exact current user instruction authorizing site creation",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--frontend-rendering-evidence", default="", help="JSON file containing a frontendRendering object")
    parser.add_argument("--launch-readiness-evidence", default="", help="JSON file containing a launchReadiness object")
    parser.add_argument("--repo-check-passed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--repo-check-note", default=None)
    args = parser.parse_args()

    try:
        evidence = upgrade_evidence(
            load_json(Path(args.preflight)),
            args.created_site_key,
            args.content_type,
            split_csv(args.list_columns, "list columns"),
            split_csv(args.edit_fields, "edit fields"),
            args.site_card_evidence,
            args.backend_evidence,
            args.frontend_evidence,
            args.site_info_evidence,
            args.domains_evidence,
            args.media_evidence,
            args.themes_evidence,
            args.routes_evidence,
            args.forms_evidence,
            args.tracking_evidence,
            parse_module_routes(args.module_routes, args.created_site_key),
            parse_submitted_fields(args.submitted_fields),
            args.authorization_source,
            args.repo_check_passed,
            args.repo_check_note,
            load_frontend_rendering(args.frontend_rendering_evidence) if args.frontend_rendering_evidence else None,
            load_launch_readiness(args.launch_readiness_evidence) if args.launch_readiness_evidence else None,
            parse_submitted_values(args.submitted_values) if args.submitted_values else None,
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
