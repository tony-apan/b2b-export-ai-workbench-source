#!/usr/bin/env python3
"""Validate evidence collected during an AllinCMS end-to-end simulation run."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
SITE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}[a-z0-9]$")
FORBIDDEN_EVIDENCE_TERMS = [
    "lai" + "faxin",
    "\u6765\u53d1\u4fe1",
    "\u641c\u5ba2",
    "\u4e3b\u52a8\u5f00\u53d1",
    "\u8054\u7cfb\u4eba",
    "\u90ae\u4ef6\u8425\u9500",
    "web." + "lai" + "faxin.com",
]
STALE_EVIDENCE_TERMS = (
    "previously verified",
    "not re-opened",
    "not reopened",
    "prior run",
    "earlier run",
    "\u4e4b\u524d\u9a8c\u8bc1",
    "\u672a\u91cd\u65b0\u6253\u5f00",
    "\u4e0a\u6b21\u9a8c\u8bc1",
)
WORKSPACE_ORIGIN = "https://workspace.laicms.com"
REQUIRED_MODULE_PATHS = {
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
}
REQUIRED_SETUP_PAGES = ("siteInfo", "domains", "media", "themes", "routes", "forms", "tracking")
VALID_CONTENT_TYPES = {"posts", "products", "media", "themes", "routes", "forms"}
REQUIRED_REQUEST_CAPTURE_FIELDS = (
    "url",
    "method",
    "headers",
    "payloadShape",
    "contentBlockShape",
    "idFields",
    "mode",
    "publishBehavior",
    "persistedVerified",
)
REQUIRED_SAMPLE_VERIFICATION_FIELDS = (
    "backendVerified",
    "frontendVerified",
    "backendUrl",
    "frontendUrl",
    "status",
    "titleOrNameVerified",
    "coverOrMediaVerified",
    "bodyVerified",
    "renderAudit",
)
REQUIRED_COMPLETED_CLEANUP_FIELDS = (
    "cleanedCount",
    "cleanedCandidates",
    "backendVerified",
    "frontendVerified",
    "backendEvidence",
    "frontendEvidence",
)
REQUIRED_CREATED_SITE_FIELDS = (
    "createdSiteKey",
    "existingSiteKeysBeforeCreate",
    "submittedFieldKeys",
    "siteCardVerified",
    "backendVerified",
    "frontendVerified",
    "siteCardEvidence",
    "backendEvidence",
    "frontendEvidence",
)
REQUIRED_AUTHORIZATION_FIELDS = (
    "userAuthorized",
    "authorizedAction",
    "target",
    "authorizationSource",
    "verificationPlan",
)
SITE_CREATION_STATUSES = {
    "simulated_not_submitted",
    "create_preflight_verified",
    "created_verified",
    "existing_site_selected",
}
REQUIRED_CLEANED_CANDIDATE_FIELDS = (
    "contentType",
    "titlePattern",
    "backendUrl",
    "reason",
)
REQUIRED_FRONTEND_RENDERING_FIELDS = (
    "checked",
    "routePatterns",
    "markdownResidueChecked",
    "structuredRichTextChecked",
    "blockingIssues",
)
REQUIRED_LAUNCH_READINESS_FIELDS = (
    "checked",
    "themeActive",
    "pagesPublished",
    "pagesEnabled",
    "routesBound",
    "frontendHttpOk",
    "frontendDomVerified",
    "checkedPaths",
    "evidence",
    "blockingIssues",
)
ALLOWED_FRONTEND_ROUTE_PATTERNS = {
    "/",
    "/home",
    "/about-us",
    "/contact-us",
    "/solutions",
    "/posts",
    "/products",
    "/posts/{slug}",
    "/products/{slug}",
}
FUZZY_AUTHORIZATION_SOURCES = {
    "continue",
    "go ahead",
    "proceed",
    "ok",
    "yes",
    "\u7ee7\u7eed",
    "\u53ef\u4ee5",
    "\u597d\u7684",
    "\u884c",
    "\u9010\u4e2a\u9a8c\u8bc1",
}
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
    "href",
    "route",
    "safe attribute",
    "data-site-key",
    "site card domain",
    "card frontend domain",
    "\u540e\u53f0",
    "\u8def\u7531",
    "\u5c5e\u6027",
)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("ERROR: evidence root must be a JSON object")
    return data


def non_empty_string(data: dict, key: str) -> bool:
    return isinstance(data.get(key), str) and bool(data[key].strip())


def non_empty_evidence_value(data: dict, key: str) -> bool:
    value = data.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return False


def non_empty_list(data: dict, key: str) -> bool:
    return isinstance(data.get(key), list) and bool(data[key])


def list_value(data: dict, key: str) -> bool:
    return isinstance(data.get(key), list)


def truthy(data: dict, key: str) -> bool:
    return data.get(key) is True


def non_negative_int(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip()) >= 0
    return False


def site_key_in_route(route: str, site_key: str) -> bool:
    parsed = urlparse(route)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc == "workspace.laicms.com" and parsed.path.startswith(f"/{site_key}/")
    return route.startswith(f"/{site_key}/")


def frontend_url_matches_site(url: str, site_key: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc == f"{site_key}.web.allincms.com"


def validate_iso_timestamp(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: must be a non-empty ISO 8601 timestamp")
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: must be an ISO 8601 timestamp")
        return
    if parsed.tzinfo is None:
        errors.append(f"{path}: must include a timezone")


def valid_site_key(value: str) -> bool:
    return bool(SITE_KEY_RE.fullmatch(value))


def route_slug(route: str, site_key: str) -> str | None:
    parsed = urlparse(route)
    path = parsed.path if parsed.scheme and parsed.netloc else route
    prefix = f"/{site_key}/"
    if not path.startswith(prefix):
        return None
    return path[len(prefix):].split("/", 1)[0].split("?", 1)[0]


def field_terms(fields: object) -> set[str]:
    if not isinstance(fields, list):
        return set()
    terms: set[str] = set()
    for field in fields:
        if isinstance(field, str):
            lowered = field.lower()
            if "name" in lowered or "名称" in field or "站点名称" in field:
                terms.add("name")
            if "description" in lowered or "描述" in field or "站点简介" in field:
                terms.add("description")
            if (
                ("创建站点" in field or "create site" in lowered)
                and any(control in lowered for control in ("button", "link", "entry", "action", "control"))
            ):
                terms.add("create-site-entry")
            if "dialog" in lowered or "弹窗" in field or "对话框" in field:
                terms.add("dialog")
            if "submit" in lowered or "创建" in field:
                terms.add("submit")
            if "close" in lowered or "关闭" in field:
                terms.add("close")
    return terms


def validate_site_key_list(value: object, path: str, errors: list[str]) -> set[str]:
    valid_keys: set[str] = set()
    if not isinstance(value, list):
        return valid_keys
    for index, site_key in enumerate(value):
        if not isinstance(site_key, str) or not valid_site_key(site_key):
            errors.append(f"{path}[{index}]: must be a valid siteKey")
        else:
            valid_keys.add(site_key)
    return valid_keys


def validate_site_key_evidence(site_creation: dict, existing_keys: set[str], errors: list[str]) -> None:
    evidence = site_creation.get("siteKeyEvidence")
    if not isinstance(evidence, dict):
        errors.append("siteCreation.siteKeyEvidence: required object with one strong source per existing site key")
        return
    evidence_keys = {key for key in evidence if isinstance(key, str)}
    if evidence_keys != existing_keys:
        errors.append("siteCreation.siteKeyEvidence: keys must exactly match existingSiteKeysBeforeCreate")
    for site_key in sorted(existing_keys):
        value = evidence.get(site_key)
        label = f"siteCreation.siteKeyEvidence.{site_key}"
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: required non-empty string")
            continue
        lowered = value.lower()
        if site_key not in value:
            errors.append(f"{label}: must mention the site key")
        if any(term in lowered for term in WEAK_SITE_KEY_EVIDENCE_TERMS):
            errors.append(f"{label}: must not rely on memory, full-page regex, card count, or unknown sources")
        if not any(term in lowered for term in STRONG_SITE_KEY_EVIDENCE_TERMS):
            errors.append(
                f"{label}: must mention a strong source such as backend URL, route, href, "
                "safe attribute, or scoped /sites card frontend domain"
            )


def validate_empty_site_list_evidence(site_creation: dict, errors: list[str]) -> None:
    evidence = site_creation.get("emptySiteListEvidence")
    if not isinstance(evidence, str) or not evidence.strip():
        errors.append("siteCreation.emptySiteListEvidence: required when existingSiteKeysBeforeCreate is empty")
        return
    lowered = evidence.lower()
    if "empty" not in lowered and "\u7a7a" not in evidence:
        errors.append("siteCreation.emptySiteListEvidence: must state that the /sites list was verified empty")


def require_text_contains(data: dict, key: str, expected: str, errors: list[str]) -> None:
    value = data.get(key)
    if isinstance(value, str) and expected not in value:
        errors.append(f"siteCreation.{key}: must mention {expected}")


def authorization_candidates(data: dict) -> list[dict]:
    candidates: list[dict] = []
    auth = data.get("authorization")
    if isinstance(auth, dict):
        candidates.append(auth)
    history = data.get("authorizationHistory")
    if isinstance(history, list):
        candidates.extend(entry for entry in history if isinstance(entry, dict))
    return candidates


def authorization_matches(auth: dict, action_terms: tuple[str, ...], target_check) -> bool:
    action = auth.get("authorizedAction", "")
    action_lower = action.lower() if isinstance(action, str) else ""
    return any(term in action_lower for term in action_terms) and target_check(auth.get("target", ""))


def find_authorization(data: dict, action_terms: tuple[str, ...], target_check) -> dict | None:
    for auth in authorization_candidates(data):
        if authorization_matches(auth, action_terms, target_check):
            return auth
    return None


def validate_authorization_object(auth: dict, label: str, errors: list[str]) -> None:
    if not isinstance(auth, dict):
        errors.append(f"{label}: required object when evidence includes remote mutation")
        return

    for key in REQUIRED_AUTHORIZATION_FIELDS:
        if key == "userAuthorized":
            if not truthy(auth, key):
                errors.append(f"{label}.userAuthorized: must be true when evidence includes remote mutation")
        elif not non_empty_string(auth, key):
            errors.append(f"{label}.{key}: required non-empty string when evidence includes remote mutation")
    source = auth.get("authorizationSource")
    if isinstance(source, str):
        lowered = source.strip().lower()
        if lowered in FUZZY_AUTHORIZATION_SOURCES:
            errors.append(f"{label}.authorizationSource: must name the exact action and target, not a generic continuation phrase")


def validate_authorization(data: dict, errors: list[str]) -> None:
    if not authorization_candidates(data):
        errors.append("authorization: required object when evidence includes remote mutation")
        return
    for index, auth in enumerate(authorization_candidates(data)):
        label = "authorization" if auth is data.get("authorization") else f"authorizationHistory[{index - 1}]"
        validate_authorization_object(auth, label, errors)


def validate_authorization_history(data: dict, errors: list[str]) -> None:
    history = data.get("authorizationHistory")
    if history is None:
        return
    if not isinstance(history, list):
        errors.append("authorizationHistory: must be an array when present")
        return
    for index, auth in enumerate(history):
        if not isinstance(auth, dict):
            errors.append(f"authorizationHistory[{index}]: must be an object")
            continue
        validate_authorization_object(auth, f"authorizationHistory[{index}]", errors)


def validate_site_creation_authorization(data: dict, errors: list[str]) -> None:
    def target_check(target: object) -> bool:
        parsed = urlparse(target if isinstance(target, str) else "")
        target_is_sites_url = (
            parsed.scheme in {"http", "https"}
            and parsed.netloc == "workspace.laicms.com"
            and parsed.path.rstrip("/") == "/sites"
        )
        target_is_sites_path = isinstance(target, str) and target.rstrip("/") in {
            "workspace.laicms.com/sites",
            "/sites",
        }
        return target_is_sites_url or target_is_sites_path

    auth = find_authorization(
        data,
        ("create site", "create_site", "\u521b\u5efa\u7ad9\u70b9"),
        target_check,
    )
    if auth is None:
        errors.append("authorization.authorizedAction: must explicitly authorize creating a site when siteCreation.status is created_verified")
        errors.append("authorization.target: must be https://workspace.laicms.com/sites when siteCreation.status is created_verified")


def validate_cleanup_authorization(data: dict, site_key: str | None, errors: list[str]) -> None:
    terms = ("cleanup", "clean", "delete", "unpublish", "\u6e05\u7406", "\u5220\u9664", "\u53d6\u6d88\u53d1\u5e03")
    auth = find_authorization(
        data,
        terms,
        lambda target: bool(site_key and isinstance(target, str) and site_key_in_route(target, site_key)),
    )
    if auth is None:
        errors.append("authorization.authorizedAction: must explicitly authorize cleanup/delete/unpublish when cleanup.status is completed")
        errors.append("authorization.target: must belong to the verified backend siteKey when cleanup.status is completed")


def validate_upload_authorization(data: dict, site_key: str | None, errors: list[str]) -> None:
    allowed_terms = (
        "probe",
        "save",
        "update",
        "upload",
        "batch",
        "publish",
        "create content",
        "sample",
        "\u63a2\u9488",
        "\u4fdd\u5b58",
        "\u66f4\u65b0",
        "\u4e0a\u4f20",
        "\u6279\u91cf",
        "\u53d1\u5e03",
        "\u6837\u672c",
    )
    auth = find_authorization(
        data,
        allowed_terms,
        lambda target: bool(site_key and isinstance(target, str) and site_key_in_route(target, site_key)),
    )
    if auth is None:
        errors.append("authorization.authorizedAction: must explicitly authorize probe/save/upload/batch/publish when upload is in scope")
        errors.append("authorization.target: must belong to the verified backend siteKey when upload is in scope")


def validate_cleaned_candidates(cleanup: dict, site_key: str | None, errors: list[str]) -> None:
    candidates = cleanup.get("cleanedCandidates")
    if not isinstance(candidates, list):
        return

    for index, candidate in enumerate(candidates):
        label = f"cleanup.cleanedCandidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{label}: must be an object")
            continue
        for key in REQUIRED_CLEANED_CANDIDATE_FIELDS:
            if not non_empty_string(candidate, key):
                errors.append(f"{label}.{key}: required non-empty string when cleanup is completed")
        if non_empty_string(candidate, "contentType") and candidate["contentType"] not in VALID_CONTENT_TYPES:
            errors.append(f"{label}.contentType: must be one of {sorted(VALID_CONTENT_TYPES)}")
        if non_empty_string(candidate, "backendUrl") and site_key and not site_key_in_route(candidate["backendUrl"], site_key):
            errors.append(f"{label}.backendUrl: must belong to the verified backend siteKey")


def validate_frontend_rendering(data: dict, errors: list[str]) -> None:
    rendering = data.get("frontendRendering")
    if rendering is None:
        return
    if not isinstance(rendering, dict):
        errors.append("frontendRendering: must be an object when present")
        return

    for key in REQUIRED_FRONTEND_RENDERING_FIELDS:
        if key not in rendering:
            errors.append(f"frontendRendering.{key}: required when frontendRendering is present")

    if rendering.get("checked") is not True:
        errors.append("frontendRendering.checked: must be true when frontendRendering is present")

    route_patterns = rendering.get("routePatterns")
    if not isinstance(route_patterns, list) or not route_patterns:
        errors.append("frontendRendering.routePatterns: required non-empty array")
    else:
        for index, route in enumerate(route_patterns):
            if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                errors.append(
                    f"frontendRendering.routePatterns[{index}]: must be one of {sorted(ALLOWED_FRONTEND_ROUTE_PATTERNS)}"
                )

    for key in ("markdownResidueChecked", "structuredRichTextChecked"):
        if rendering.get(key) is not True:
            errors.append(f"frontendRendering.{key}: must be true")

    blocking = rendering.get("blockingIssues")
    if not isinstance(blocking, list):
        errors.append("frontendRendering.blockingIssues: must be an array")
    else:
        for index, issue in enumerate(blocking):
            label = f"frontendRendering.blockingIssues[{index}]"
            if not isinstance(issue, dict):
                errors.append(f"{label}: must be an object")
                continue
            for key in ("routePattern", "code", "evidence"):
                if not non_empty_string(issue, key):
                    errors.append(f"{label}.{key}: required non-empty string")
            if non_empty_string(issue, "routePattern") and issue["routePattern"] not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                errors.append(f"{label}.routePattern: must be a redacted route pattern, not a concrete slug")

    expected_statuses = rendering.get("expectedStatuses")
    if expected_statuses is not None:
        if not isinstance(expected_statuses, dict):
            errors.append("frontendRendering.expectedStatuses: must be an object when present")
        else:
            for route, status in expected_statuses.items():
                if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                    errors.append(f"frontendRendering.expectedStatuses.{route}: route must be an allowed redacted route pattern")
                if status not in {200, 404}:
                    errors.append(f"frontendRendering.expectedStatuses.{route}: status must be 200 or 404")
            if isinstance(route_patterns, list):
                missing = [route for route in route_patterns if route not in expected_statuses]
                if missing:
                    errors.append(f"frontendRendering.expectedStatuses: missing statuses for routePatterns {missing}")


def validate_launch_readiness(data: dict, errors: list[str]) -> None:
    readiness = data.get("launchReadiness")
    if readiness is None:
        return
    if not isinstance(readiness, dict):
        errors.append("launchReadiness: must be an object when present")
        return

    for key in REQUIRED_LAUNCH_READINESS_FIELDS:
        if key not in readiness:
            errors.append(f"launchReadiness.{key}: required when launchReadiness is present")

    if readiness.get("checked") is not True:
        errors.append("launchReadiness.checked: must be true when launchReadiness is present")

    for key in (
        "themeActive",
        "pagesPublished",
        "pagesEnabled",
        "routesBound",
        "frontendHttpOk",
        "frontendDomVerified",
    ):
        if readiness.get(key) is not True:
            errors.append(f"launchReadiness.{key}: must be true for launch-ready evidence")

    checked_paths = readiness.get("checkedPaths")
    if not isinstance(checked_paths, list) or not checked_paths:
        errors.append("launchReadiness.checkedPaths: required non-empty array")
    else:
        for index, route in enumerate(checked_paths):
            if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                errors.append(
                    f"launchReadiness.checkedPaths[{index}]: must be one of {sorted(ALLOWED_FRONTEND_ROUTE_PATTERNS)}"
                )

    if not isinstance(readiness.get("evidence"), str) or not readiness["evidence"].strip():
        errors.append("launchReadiness.evidence: required non-empty string")

    blocking = readiness.get("blockingIssues")
    if not isinstance(blocking, list):
        errors.append("launchReadiness.blockingIssues: must be an array")
    else:
        for index, issue in enumerate(blocking):
            label = f"launchReadiness.blockingIssues[{index}]"
            if not isinstance(issue, dict):
                errors.append(f"{label}: must be an object")
                continue
            for key in ("code", "evidence"):
                if not non_empty_string(issue, key):
                    errors.append(f"{label}.{key}: required non-empty string")
            if "routePattern" in issue and issue["routePattern"] not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                errors.append(f"{label}.routePattern: must be a redacted route pattern when present")


def iter_strings(value: object, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(item, f"{path}.{key}")


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    mode = data.get("mode")
    if mode not in {"read_only_simulation", "site_creation", "mutating_probe", "batch_upload"}:
        errors.append("mode: must be read_only_simulation, site_creation, mutating_probe, or batch_upload")
    mutation_in_scope = mode in {"site_creation", "mutating_probe", "batch_upload"}

    for key in ("workspaceUrl", "siteListUrl"):
        if not non_empty_string(data, key):
            errors.append(f"{key}: required non-empty string")
    if data.get("workspaceUrl") != WORKSPACE_ORIGIN:
        errors.append(f"workspaceUrl: must be {WORKSPACE_ORIGIN}")
    if data.get("siteListUrl") != f"{WORKSPACE_ORIGIN}/sites":
        errors.append(f"siteListUrl: must be {WORKSPACE_ORIGIN}/sites")
    if "generatedAt" in data:
        validate_iso_timestamp(data.get("generatedAt"), "generatedAt", errors)
    if "preflightGeneratedAt" in data:
        validate_iso_timestamp(data.get("preflightGeneratedAt"), "preflightGeneratedAt", errors)

    site_creation = data.get("siteCreation")
    created_site_key = None
    site_creation_status = None
    existing_selected_keys: set[str] = set()
    if not isinstance(site_creation, dict):
        errors.append("siteCreation: required object")
    else:
        status = site_creation.get("status")
        site_creation_status = status
        if status not in SITE_CREATION_STATUSES:
            errors.append("siteCreation.status: must be simulated_not_submitted, create_preflight_verified, created_verified, or existing_site_selected")
        if status == "created_verified" and not non_empty_string(site_creation, "createdSiteKey"):
            errors.append("siteCreation.createdSiteKey: required when status is created_verified")
        elif status == "created_verified":
            created_site_key = site_creation["createdSiteKey"].strip()
            if not valid_site_key(created_site_key):
                errors.append("siteCreation.createdSiteKey: must be lowercase letters, digits, or hyphens")
        if status == "created_verified":
            if mode not in {"site_creation", "mutating_probe", "batch_upload"}:
                errors.append("mode: must be site_creation, mutating_probe, or batch_upload when siteCreation.status is created_verified")
            if not non_empty_string(data, "preflightGeneratedAt"):
                errors.append("preflightGeneratedAt: required when siteCreation.status is created_verified")
            mutation_in_scope = True
            for key in REQUIRED_CREATED_SITE_FIELDS:
                if key == "createdSiteKey":
                    continue
                if key == "existingSiteKeysBeforeCreate":
                    if not list_value(site_creation, key):
                        errors.append("siteCreation.existingSiteKeysBeforeCreate: required array when status is created_verified")
                    continue
                if key == "submittedFieldKeys":
                    submitted = site_creation.get(key)
                    if not non_empty_list(site_creation, key):
                        errors.append("siteCreation.submittedFieldKeys: required non-empty array when status is created_verified")
                    elif not {"name", "description"}.issubset(set(item for item in submitted if isinstance(item, str))):
                        errors.append("siteCreation.submittedFieldKeys: must include name and description")
                    continue
                if key in {"siteCardVerified", "backendVerified", "frontendVerified"}:
                    if not truthy(site_creation, key):
                        errors.append(f"siteCreation.{key}: must be true when status is created_verified")
                elif not non_empty_string(site_creation, key):
                    errors.append(f"siteCreation.{key}: required non-empty string when status is created_verified")
            existing_keys = validate_site_key_list(
                site_creation.get("existingSiteKeysBeforeCreate"),
                "siteCreation.existingSiteKeysBeforeCreate",
                errors,
            )
            if created_site_key and created_site_key in existing_keys:
                errors.append("siteCreation.createdSiteKey: must not already exist in existingSiteKeysBeforeCreate")
            if created_site_key:
                require_text_contains(site_creation, "siteCardEvidence", created_site_key, errors)
                require_text_contains(
                    site_creation,
                    "backendEvidence",
                    f"{WORKSPACE_ORIGIN}/{created_site_key}/dashboard",
                    errors,
                )
                require_text_contains(
                    site_creation,
                    "frontendEvidence",
                    f"https://{created_site_key}.web.allincms.com",
                    errors,
                )
            submitted_values = site_creation.get("submittedValues")
            if submitted_values is not None:
                if not isinstance(submitted_values, dict):
                    errors.append("siteCreation.submittedValues: must be an object when present")
                else:
                    for submitted_key in ("name", "description"):
                        value = submitted_values.get(submitted_key)
                        if not isinstance(value, str) or not value.strip():
                            errors.append(f"siteCreation.submittedValues.{submitted_key}: required non-empty string when submittedValues is present")
        if status == "create_preflight_verified":
            if not list_value(site_creation, "existingSiteKeysBeforeCreate"):
                errors.append("siteCreation.existingSiteKeysBeforeCreate: required array when status is create_preflight_verified")
            else:
                preflight_existing_keys = validate_site_key_list(
                    site_creation.get("existingSiteKeysBeforeCreate"),
                    "siteCreation.existingSiteKeysBeforeCreate",
                    errors,
                )
                if preflight_existing_keys:
                    validate_site_key_evidence(site_creation, preflight_existing_keys, errors)
                else:
                    validate_empty_site_list_evidence(site_creation, errors)
            if non_empty_string(site_creation, "createdSiteKey"):
                errors.append("siteCreation.createdSiteKey: must not be set before submitting the create-site form")
            if not truthy(site_creation, "dialogClosedVerified"):
                errors.append("siteCreation.dialogClosedVerified: must be true after inspecting and closing the create-site dialog")
        if status == "existing_site_selected":
            if not non_empty_list(site_creation, "existingSiteKeysBeforeCreate"):
                errors.append("siteCreation.existingSiteKeysBeforeCreate: required non-empty array when status is existing_site_selected")
            else:
                existing_selected_keys = validate_site_key_list(
                    site_creation.get("existingSiteKeysBeforeCreate"),
                    "siteCreation.existingSiteKeysBeforeCreate",
                    errors,
                )
                if len(existing_selected_keys) > 20:
                    errors.append("siteCreation.existingSiteKeysBeforeCreate: too many keys for existing-site read-only evidence; use scoped site-card links, not full-page regex extraction")
                if existing_selected_keys:
                    validate_site_key_evidence(site_creation, existing_selected_keys, errors)
            if not non_empty_string(site_creation, "selectedSiteEvidence"):
                errors.append("siteCreation.selectedSiteEvidence: required non-empty string when status is existing_site_selected")
        create_fields_required = status in {"create_preflight_verified", "created_verified"}
        if create_fields_required and not non_empty_list(site_creation, "createSiteFields"):
            errors.append("siteCreation.createSiteFields: required non-empty array")
        elif non_empty_list(site_creation, "createSiteFields"):
            terms = field_terms(site_creation.get("createSiteFields"))
            for required_field in ("name", "description"):
                if required_field not in terms:
                    errors.append(f"siteCreation.createSiteFields: must include {required_field}")
            if status == "create_preflight_verified":
                for required_term in ("create-site-entry", "dialog", "submit", "close"):
                    if required_term not in terms:
                        errors.append(f"siteCreation.createSiteFields: must include observed {required_term}")

    upload_in_scope = mode == "batch_upload" or data.get("uploadInScope") is True
    requires_site_context = (
        site_creation_status in {"created_verified", "existing_site_selected"}
        or upload_in_scope
        or data.get("completionClaimed") is True
    )

    site_identity = data.get("siteIdentity")
    site_key = None
    if not isinstance(site_identity, dict):
        if requires_site_context:
            errors.append("siteIdentity: required object")
    else:
        for key in ("siteKey", "backendDashboardUrl", "frontendBaseUrl"):
            if not non_empty_string(site_identity, key):
                errors.append(f"siteIdentity.{key}: required non-empty string")
        if non_empty_string(site_identity, "siteKey"):
            site_key = site_identity["siteKey"].strip()
            if not valid_site_key(site_key):
                errors.append("siteIdentity.siteKey: must be lowercase letters, digits, or hyphens")
        if not non_empty_list(site_identity, "moduleRoutes"):
            errors.append("siteIdentity.moduleRoutes: required non-empty array")
        if site_key:
            expected_backend = f"{WORKSPACE_ORIGIN}/{site_key}/dashboard"
            expected_frontend = f"https://{site_key}.web.allincms.com"
            if site_identity.get("backendDashboardUrl") != expected_backend:
                errors.append(f"siteIdentity.backendDashboardUrl: must be {expected_backend}")
            if site_identity.get("frontendBaseUrl") != expected_frontend:
                errors.append(f"siteIdentity.frontendBaseUrl: must be {expected_frontend}")
            routes = site_identity.get("moduleRoutes")
            if isinstance(routes, list):
                observed_modules: set[str] = set()
                for index, route in enumerate(routes):
                    if not isinstance(route, str) or not site_key_in_route(route, site_key):
                        errors.append(f"siteIdentity.moduleRoutes[{index}]: route must belong to siteKey {site_key}")
                    elif (slug := route_slug(route, site_key)):
                        observed_modules.add(slug)
                missing_modules = sorted(REQUIRED_MODULE_PATHS - observed_modules)
                if missing_modules:
                    errors.append(f"siteIdentity.moduleRoutes: missing required modules {missing_modules}")

    if created_site_key and site_key and created_site_key != site_key:
        errors.append("siteCreation.createdSiteKey: must match siteIdentity.siteKey")
    elif created_site_key and requires_site_context and not site_key:
        errors.append("siteIdentity.siteKey: required to verify createdSiteKey")
    if (
        isinstance(site_creation, dict)
        and site_creation.get("status") == "existing_site_selected"
        and site_key
        and site_key not in existing_selected_keys
    ):
        errors.append("siteIdentity.siteKey: must be present in siteCreation.existingSiteKeysBeforeCreate when status is existing_site_selected")

    setup = data.get("setupPages")
    if not isinstance(setup, dict):
        if requires_site_context:
            errors.append("setupPages: required object")
    else:
        for key in REQUIRED_SETUP_PAGES:
            if key not in setup:
                errors.append(f"setupPages.{key}: required")
            elif not non_empty_list(setup, key):
                errors.append(f"setupPages.{key}: required non-empty evidence array")

    content = data.get("contentInspection")
    if not isinstance(content, dict):
        if requires_site_context:
            errors.append("contentInspection: required object")
    else:
        if not non_empty_string(content, "contentType"):
            errors.append("contentInspection.contentType: required non-empty string")
        elif content.get("contentType") not in VALID_CONTENT_TYPES:
            errors.append(f"contentInspection.contentType: must be one of {sorted(VALID_CONTENT_TYPES)}")
        if not non_empty_list(content, "listColumns"):
            errors.append("contentInspection.listColumns: required non-empty array")
        if not non_empty_list(content, "editFields"):
            errors.append("contentInspection.editFields: required non-empty array")

    if data.get("uploadInScope") is True:
        mutation_in_scope = True
    if upload_in_scope:
        if not site_key:
            errors.append("siteIdentity.siteKey: required when upload is in scope")
        request_capture = data.get("requestCapture")
        if not isinstance(request_capture, dict):
            errors.append("requestCapture: required object when upload is in scope")
        else:
            for key in REQUIRED_REQUEST_CAPTURE_FIELDS:
                if key == "persistedVerified":
                    if not truthy(request_capture, key):
                        errors.append(f"requestCapture.{key}: must be true when upload is in scope")
                elif not non_empty_evidence_value(request_capture, key):
                    errors.append(f"requestCapture.{key}: required non-empty evidence value when upload is in scope")
            if non_empty_string(request_capture, "method") and request_capture["method"].upper() not in {"POST", "PUT", "PATCH"}:
                errors.append("requestCapture.method: must be POST, PUT, or PATCH when upload is in scope")
            if non_empty_string(request_capture, "url") and site_key and not site_key_in_route(request_capture["url"], site_key):
                errors.append("requestCapture.url: must belong to the verified backend siteKey")

        sample = data.get("sampleVerification")
        if not isinstance(sample, dict):
            errors.append("sampleVerification: required object when upload is in scope")
        else:
            for key in REQUIRED_SAMPLE_VERIFICATION_FIELDS:
                if key in {"backendVerified", "frontendVerified", "titleOrNameVerified", "coverOrMediaVerified", "bodyVerified"}:
                    if not truthy(sample, key):
                        errors.append(f"sampleVerification.{key}: must be true when upload is in scope")
                elif not non_empty_evidence_value(sample, key):
                    errors.append(f"sampleVerification.{key}: required non-empty evidence value when upload is in scope")
            if non_empty_string(sample, "frontendUrl") and site_key and not frontend_url_matches_site(sample["frontendUrl"], site_key):
                errors.append("sampleVerification.frontendUrl: must belong to the verified frontend base URL")
            if non_empty_string(sample, "backendUrl") and site_key and not site_key_in_route(sample["backendUrl"], site_key):
                errors.append("sampleVerification.backendUrl: must belong to the verified backend siteKey")

    cleanup = data.get("cleanup")
    if not isinstance(cleanup, dict):
        errors.append("cleanup: required object")
    else:
        status = cleanup.get("status")
        if status not in {"not_needed", "completed", "pending_user_authorization", "explicitly_deferred"}:
            errors.append("cleanup.status: must be not_needed, completed, pending_user_authorization, or explicitly_deferred")
        if status in {"pending_user_authorization", "explicitly_deferred"} and not non_empty_list(cleanup, "candidates"):
            errors.append("cleanup.candidates: required when cleanup is pending or deferred")
        if status == "completed":
            mutation_in_scope = True
            for key in REQUIRED_COMPLETED_CLEANUP_FIELDS:
                if key == "cleanedCount":
                    if not non_negative_int(cleanup.get(key)):
                        errors.append("cleanup.cleanedCount: required non-negative integer when cleanup is completed")
                elif key == "cleanedCandidates":
                    if not non_empty_list(cleanup, key):
                        errors.append("cleanup.cleanedCandidates: required non-empty array when cleanup is completed")
                elif key in {"backendVerified", "frontendVerified"}:
                    if not truthy(cleanup, key):
                        errors.append(f"cleanup.{key}: must be true when cleanup is completed")
                elif not non_empty_string(cleanup, key):
                    errors.append(f"cleanup.{key}: required non-empty string when cleanup is completed")
            if non_negative_int(cleanup.get("cleanedCount")) and non_empty_list(cleanup, "cleanedCandidates"):
                cleaned_count = int(str(cleanup["cleanedCount"]).strip())
                if cleaned_count != len(cleanup["cleanedCandidates"]):
                    errors.append("cleanup.cleanedCount: must match length of cleanup.cleanedCandidates")
            validate_cleaned_candidates(cleanup, site_key, errors)

    if mutation_in_scope:
        validate_authorization_history(data, errors)
        validate_authorization(data, errors)
    if (
        isinstance(site_creation, dict)
        and site_creation.get("status") == "created_verified"
        and mode == "site_creation"
    ):
        validate_site_creation_authorization(data, errors)
    if upload_in_scope:
        validate_upload_authorization(data, site_key, errors)
    if isinstance(cleanup, dict) and cleanup.get("status") == "completed":
        validate_cleanup_authorization(data, site_key, errors)

    validate_frontend_rendering(data, errors)
    validate_launch_readiness(data, errors)

    completion_claimed = data.get("completionClaimed") is True
    if completion_claimed and (data.get("localOnly") is True or data.get("simulationOnly") is True):
        errors.append("completionClaimed: local-only or simulation-only evidence must not claim real completion")
    if (data.get("localOnly") is True or data.get("simulationOnly") is True) and data.get("remoteMutationsPerformed") is not False:
        errors.append("remoteMutationsPerformed: must be false for local-only or simulation-only evidence")

    local_checks = data.get("localChecks")
    if not isinstance(local_checks, dict):
        errors.append("localChecks: required object")
    else:
        for key in ("skillHygienePassed", "quickValidatePassed"):
            if not truthy(local_checks, key):
                errors.append(f"localChecks.{key}: must be true")
        if completion_claimed and not truthy(local_checks, "repoCheckPassed"):
            errors.append("localChecks.repoCheckPassed: must be true when completionClaimed is true")
        elif local_checks.get("repoCheckPassed") is not True and not non_empty_string(local_checks, "repoCheckNote"):
            errors.append("localChecks.repoCheckNote: required when repoCheckPassed is not true")

    for path, text in iter_strings(data):
        if EMAIL_RE.search(text):
            errors.append(f"{path}: evidence must not contain account emails or contact emails")
        lowered = text.lower()
        if completion_claimed:
            for term in STALE_EVIDENCE_TERMS:
                if term.lower() in lowered:
                    errors.append(f"{path}: completionClaimed evidence must be current, not stale or partial: {term}")
        for term in FORBIDDEN_EVIDENCE_TERMS:
            if term.lower() in lowered:
                errors.append(f"{path}: evidence must not contain business-domain residue: {term}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS run evidence JSON.")
    parser.add_argument("evidence", help="Path to run evidence JSON")
    args = parser.parse_args()

    errors = validate(load_json(Path(args.evidence)))
    if errors:
        print("Run evidence validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Run evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
