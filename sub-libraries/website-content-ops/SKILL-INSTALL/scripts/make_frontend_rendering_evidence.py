#!/usr/bin/env python3
"""Build a frontendRendering evidence block from redacted frontend audit JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_reports(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, list):
        raise ValueError("audit JSON must be an array")
    reports: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"audit JSON item {index} must be an object")
        reports.append(item)
    return reports


def build_evidence(reports: list[dict[str, Any]], include_warnings: bool) -> dict[str, Any]:
    route_patterns: list[str] = []
    expected_statuses: dict[str, int] = {}
    blocking_issues: list[dict[str, str]] = []

    for index, report in enumerate(reports):
        route = report.get("url")
        if not isinstance(route, str) or not route.strip():
            raise ValueError(f"report {index} missing redacted url")
        if route not in route_patterns:
            route_patterns.append(route)

        expected_status = report.get("expectedStatus")
        if not isinstance(expected_status, int) or isinstance(expected_status, bool):
            raise ValueError(f"report {index} missing integer expectedStatus")
        expected_statuses[route] = expected_status

        issues = report.get("issues", [])
        if not isinstance(issues, list):
            raise ValueError(f"report {index} issues must be an array")
        for issue_index, issue in enumerate(issues):
            if not isinstance(issue, dict):
                raise ValueError(f"report {index} issue {issue_index} must be an object")
            severity = str(issue.get("severity", "error"))
            if severity == "warn" and not include_warnings:
                continue
            code = str(issue.get("code", "unknown"))
            blocking_issues.append(
                {
                    "routePattern": route,
                    "code": code,
                    "evidence": "redacted audit issue",
                }
            )

    return {
        "frontendRendering": {
            "checked": True,
            "routePatterns": route_patterns,
            "expectedStatuses": expected_statuses,
            "markdownResidueChecked": True,
            "structuredRichTextChecked": True,
            "blockingIssues": blocking_issues,
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert frontend audit JSON into run-evidence frontendRendering JSON.")
    parser.add_argument("audit_json", help="Path to JSON output from audit_frontend_rendering.py --json --redact")
    parser.add_argument("--include-warnings", action="store_true", help="Include warning issues as blockingIssues")
    parser.add_argument("--output", help="Optional output path; defaults to stdout")
    args = parser.parse_args()

    try:
        evidence = build_evidence(load_reports(Path(args.audit_json)), args.include_warnings)
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
