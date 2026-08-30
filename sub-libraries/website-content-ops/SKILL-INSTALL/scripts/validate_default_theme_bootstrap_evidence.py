#!/usr/bin/env python3
"""Validate redacted evidence from a default-theme bootstrap stage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"cookie\s*[:=]", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
REQUIRED_PUBLIC_PATHS = {"/", "/home", "/products", "/posts", "/about-us", "/contact-us"}
REQUIRED_ROUTE_PATHS = {"/home", "/products", "/products/{product}", "/posts", "/posts/{post}", "/about-us", "/contact-us"}
MIN_DEFAULT_PAGE_COUNT = 5


def load_json(path: Path, label: str = "evidence") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def walk_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(walk_string_values(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(walk_string_values(item))
    return strings


def validate_workspace_theme_target(target: Any, site_key: str, issues: list[str]) -> None:
    if not isinstance(target, str):
        issues.append("target must be a workspace themes URL")
        return
    parsed = urlparse(target)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        issues.append("target must be under https://workspace.laicms.com")
        return
    if not parsed.path.startswith(f"/{site_key}/themes"):
        issues.append("target must be under the current site's themes route")


def validate_headers(headers: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(headers, list) or not headers:
        return ["requestCapture.headers must be a non-empty list of header names"]
    lowered: list[str] = []
    for header in headers:
        if not isinstance(header, str) or not header.strip():
            issues.append("requestCapture.headers must contain non-empty strings")
            continue
        if ":" in header or "=" in header:
            issues.append("requestCapture.headers must contain header names only, not values")
        lowered.append(header.strip().lower())
    for forbidden in ("cookie", "authorization"):
        if forbidden in lowered:
            issues.append(f"requestCapture.headers must not include {forbidden}")
    for required in ("accept", "content-type"):
        if required not in lowered:
            issues.append(f"requestCapture.headers should include {required}")
    return issues


def validate_request_capture(capture: Any, site_key: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(capture, dict):
        return ["createTheme.requestCapture must be an object"]
    if capture.get("method") != "POST":
        issues.append("createTheme.requestCapture.method must be POST")
    url = capture.get("url")
    if not isinstance(url, str) or f"/{site_key}/themes" not in url:
        issues.append("createTheme.requestCapture.url must be under the current site's themes route")
    issues.extend(validate_headers(capture.get("headers")))
    payload = capture.get("payloadShape")
    if not isinstance(payload, dict) or not payload:
        issues.append("createTheme.requestCapture.payloadShape must be a non-empty object")
    else:
        joined = " ".join(str(value) for value in payload.values())
        keys = set(payload)
        if "preset" not in keys and "template" not in keys:
            issues.append("createTheme.requestCapture.payloadShape must include preset or template key")
        if "默认" not in joined and "default" not in joined.lower():
            issues.append("createTheme.requestCapture.payloadShape must prove 默认/default preset")
    status = capture.get("responseStatus")
    if not isinstance(status, int) or status < 200 or status >= 300:
        issues.append("createTheme.requestCapture.responseStatus must be a 2xx integer")
    return issues


def validate_frontend(frontend: Any, site_key: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(frontend, dict):
        return ["frontend must be an object"]
    base_url = frontend.get("baseUrl")
    if not isinstance(base_url, str) or urlparse(base_url).netloc != f"{site_key}.web.allincms.com":
        issues.append("frontend.baseUrl must match the current site default frontend domain")
    rows = frontend.get("checkedPaths")
    if not isinstance(rows, list) or not rows:
        return issues + ["frontend.checkedPaths must be a non-empty array"]
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            issues.append("frontend.checkedPaths entries must be objects")
            continue
        path = row.get("path")
        if isinstance(path, str):
            seen.add(path)
        else:
            issues.append("frontend.checkedPaths.path must be a string")
            continue
        url = row.get("url")
        parsed = urlparse(url) if isinstance(url, str) else None
        if parsed is None or parsed.scheme != "https" or parsed.netloc != f"{site_key}.web.allincms.com":
            issues.append(f"frontend checked URL for {path} must match current site frontend")
        if row.get("statusOk") is not True:
            issues.append(f"frontend.checkedPaths[{path}].statusOk must be true")
        if row.get("domNonEmpty") is not True:
            issues.append(f"frontend.checkedPaths[{path}].domNonEmpty must be true")
    missing = sorted(REQUIRED_PUBLIC_PATHS - seen)
    if missing:
        issues.append(f"frontend.checkedPaths missing required paths: {missing}")
    if frontend.get("businessContentComplete") is True:
        issues.append("frontend.businessContentComplete must not be true for default-template bootstrap evidence")
    return issues


def validate_evidence(data: dict[str, Any], runbook: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_default_theme_bootstrap_evidence":
        issues.append("kind must be allincms_default_theme_bootstrap_evidence")
    site_key = data.get("siteKey")
    if not isinstance(site_key, str) or not site_key.strip():
        issues.append("siteKey must be a non-empty string")
        site_key = ""
    if runbook is not None and site_key and runbook.get("siteKey") != site_key:
        issues.append("evidence siteKey must match runbook siteKey")
    if site_key:
        validate_workspace_theme_target(data.get("target"), site_key, issues)
    for key in ("remoteMutationsPerformed", "preMutationGatesPassed", "stopConditionMet", "createdDefaultTheme"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    if data.get("preset") not in {"默认", "default", "Default"}:
        issues.append("preset must prove 默认/default theme selection")
    theme_id = data.get("themeId")
    if not isinstance(theme_id, str) or not theme_id.strip() or theme_id.startswith("<") or "{" in theme_id:
        issues.append("themeId must be concrete after backend verification")
    page_count = data.get("pageCount")
    if not isinstance(page_count, int) or page_count < MIN_DEFAULT_PAGE_COUNT:
        issues.append(f"pageCount must be at least {MIN_DEFAULT_PAGE_COUNT} for default-theme bootstrap")
    create_theme = data.get("createTheme")
    if not isinstance(create_theme, dict):
        issues.append("createTheme must be an object")
    else:
        if create_theme.get("action") != "create_theme":
            issues.append("createTheme.action must be create_theme")
        if create_theme.get("preMutationGate") != "passed":
            issues.append("createTheme.preMutationGate must be passed")
        if create_theme.get("backendVerified") is not True:
            issues.append("createTheme.backendVerified must be true")
        if site_key:
            issues.extend(validate_request_capture(create_theme.get("requestCapture"), site_key))
    activate = data.get("activateTheme")
    if not isinstance(activate, dict):
        issues.append("activateTheme must be an object")
    else:
        if activate.get("action") != "activate_theme":
            issues.append("activateTheme.action must be activate_theme")
        if activate.get("preMutationGate") != "passed":
            issues.append("activateTheme.preMutationGate must be passed")
        if activate.get("routeMappingReviewed") is not True:
            issues.append("activateTheme.routeMappingReviewed must be true")
        if activate.get("themeEnabled") is not True:
            issues.append("activateTheme.themeEnabled must be true")
        if activate.get("backendVerified") is not True:
            issues.append("activateTheme.backendVerified must be true")
    routes = data.get("routes")
    if not isinstance(routes, dict):
        issues.append("routes must be an object")
    else:
        if routes.get("routesBound") is not True:
            issues.append("routes.routesBound must be true")
        checked = routes.get("checkedRoutes")
        checked_set = set(checked) if isinstance(checked, list) else set()
        missing_routes = sorted(REQUIRED_ROUTE_PATHS - checked_set)
        if missing_routes:
            issues.append(f"routes.checkedRoutes missing required paths: {missing_routes}")
    if site_key:
        issues.extend(validate_frontend(data.get("frontend"), site_key))
    blockers = data.get("blockingIssues")
    if blockers not in ([], None):
        issues.append("blockingIssues must be empty after completed default-theme bootstrap")
    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate default-theme bootstrap evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--runbook", default="")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json), "evidence")
        runbook = load_json(Path(args.runbook), "runbook") if args.runbook else None
        issues = validate_evidence(evidence, runbook)
        report = {
            "kind": "allincms_default_theme_bootstrap_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "runbook": args.runbook,
            "siteKey": evidence.get("siteKey"),
            "themeId": evidence.get("themeId"),
            "pageCount": evidence.get("pageCount"),
            "issues": issues,
            "nextStageReady": not issues,
            "nextActions": [
                "Proceed to source pages/site-info, taxonomy, and content schema capture; default template content still needs replacement."
                if not issues
                else "Fix bootstrap evidence gaps before using the default theme as launch foundation."
            ],
        }
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
