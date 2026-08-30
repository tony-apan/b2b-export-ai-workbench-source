#!/usr/bin/env python3
"""Build a launchReadiness evidence block for AllinCMS run evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_run_evidence import ALLOWED_FRONTEND_ROUTE_PATTERNS


LAUNCH_BOOL_FIELDS = (
    "themeActive",
    "pagesPublished",
    "pagesEnabled",
    "routesBound",
    "frontendHttpOk",
    "frontendDomVerified",
)


def parse_checked_paths(raw: str) -> list[str]:
    paths = [item.strip() for item in raw.split(",") if item.strip()]
    if not paths:
        raise ValueError("--checked-paths must contain at least one redacted route pattern")
    for path in paths:
        if path not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
            raise ValueError(
                f"checked path must be one of {sorted(ALLOWED_FRONTEND_ROUTE_PATTERNS)}, not a concrete slug: {path}"
            )
    return paths


def parse_blocking_issues(raw: str | None) -> list[dict[str, str]]:
    if raw is None or not raw.strip():
        return []

    issues: list[dict[str, str]] = []
    for index, item in enumerate(part.strip() for part in raw.split(",") if part.strip()):
        parts = [part.strip() for part in item.split("|", 2)]
        if len(parts) != 3:
            raise ValueError(
                f"blocking issue {index} must use routePattern|code|evidence"
            )
        route_pattern, code, evidence = parts
        if route_pattern not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
            raise ValueError(
                f"blocking issue {index} routePattern must be a redacted route pattern, not a concrete slug: {route_pattern}"
            )
        if not code:
            raise ValueError(f"blocking issue {index} code must be non-empty")
        if not evidence:
            raise ValueError(f"blocking issue {index} evidence must be non-empty")
        issues.append(
            {
                "routePattern": route_pattern,
                "code": code,
                "evidence": evidence,
            }
        )
    return issues


def build_evidence(
    *,
    theme_active: bool,
    pages_published: bool,
    pages_enabled: bool,
    routes_bound: bool,
    frontend_http_ok: bool,
    frontend_dom_verified: bool,
    checked_paths: list[str],
    evidence: str,
    blocking_issues: list[dict[str, str]],
) -> dict[str, Any]:
    if not evidence.strip():
        raise ValueError("--evidence must be non-empty and redacted")

    readiness = {
        "checked": True,
        "themeActive": theme_active,
        "pagesPublished": pages_published,
        "pagesEnabled": pages_enabled,
        "routesBound": routes_bound,
        "frontendHttpOk": frontend_http_ok,
        "frontendDomVerified": frontend_dom_verified,
        "checkedPaths": checked_paths,
        "evidence": evidence.strip(),
        "blockingIssues": blocking_issues,
    }

    all_ready = all(readiness[field] is True for field in LAUNCH_BOOL_FIELDS)
    if all_ready and blocking_issues:
        raise ValueError("launch-ready evidence must not include blocking issues")
    if not all_ready and not blocking_issues:
        raise ValueError("partial launch readiness requires at least one blocking issue")

    return {"launchReadiness": readiness}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate run-evidence launchReadiness JSON.")
    parser.add_argument("--theme-active", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--pages-published", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--pages-enabled", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--routes-bound", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--frontend-http-ok", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--frontend-dom-verified", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--checked-paths", required=True, help="Comma-separated redacted route patterns")
    parser.add_argument("--evidence", required=True, help="Neutral redacted launch proof")
    parser.add_argument(
        "--blocking-issues",
        help="Comma-separated routePattern|code|evidence issues; required when any launch boolean is false",
    )
    parser.add_argument("--output", help="Optional output path; defaults to stdout")
    args = parser.parse_args()

    try:
        evidence = build_evidence(
            theme_active=args.theme_active,
            pages_published=args.pages_published,
            pages_enabled=args.pages_enabled,
            routes_bound=args.routes_bound,
            frontend_http_ok=args.frontend_http_ok,
            frontend_dom_verified=args.frontend_dom_verified,
            checked_paths=parse_checked_paths(args.checked_paths),
            evidence=args.evidence,
            blocking_issues=parse_blocking_issues(args.blocking_issues),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
