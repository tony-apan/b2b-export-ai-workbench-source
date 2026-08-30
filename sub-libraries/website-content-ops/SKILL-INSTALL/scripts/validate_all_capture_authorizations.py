#!/usr/bin/env python3
"""Validate a capture authorization package-set summary and its packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from prepare_capture_authorization import load_plan
from validate_capture_authorization_package import load_json, validate_package


def load_summary(path: Path) -> dict[str, Any]:
    return load_json(path, "package set summary")


def validate_package_set(summary: dict[str, Any], plan: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if summary.get("kind") != "allincms_capture_authorization_package_set":
        issues.append("summary.kind must be allincms_capture_authorization_package_set")
    if summary.get("preparedOnly") is not True:
        issues.append("summary.preparedOnly must be true")
    if summary.get("isUserAuthorization") is not False:
        issues.append("summary.isUserAuthorization must be false")
    if summary.get("jsonReplayReady") is not False:
        issues.append("summary.jsonReplayReady must be false")
    warning = str(summary.get("warning", "")).strip().lower()
    if "not user authorization" not in warning:
        issues.append("summary.warning must explicitly say it is not user authorization")

    items = summary.get("items")
    if not isinstance(items, list) or not items:
        issues.append("summary.items must be a non-empty array")
        return issues

    expected_count = summary.get("count")
    if expected_count != len(items):
        issues.append("summary.count must equal len(summary.items)")

    seen: set[tuple[str, str]] = set()
    all_items_valid = True
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"item {index} must be an object")
            all_items_valid = False
            continue
        module = str(item.get("module", "")).strip()
        action = str(item.get("action", "")).strip()
        key = (module, action)
        if not module or not action:
            issues.append(f"item {index} must include module and action")
            all_items_valid = False
        elif key in seen:
            issues.append(f"duplicate item for {module}:{action}")
            all_items_valid = False
        else:
            seen.add(key)

        package_path = str(item.get("package", "")).strip()
        if not package_path:
            issues.append(f"item {index} package path is required")
            all_items_valid = False
            continue

        try:
            package = load_json(Path(package_path), f"item {index} package")
        except ValueError as exc:
            issues.append(str(exc))
            all_items_valid = False
            continue

        package_issues = validate_package(package, plan)
        if package_issues:
            all_items_valid = False
            issues.extend(f"{module}:{action}: {issue}" for issue in package_issues)

        checks = {
            "authorizationAction": package.get("authorizationAction"),
            "target": package.get("target"),
            "gateSupported": package.get("gateSupported"),
            "jsonReplayReady": package.get("jsonReplayReady"),
            "commandsSuppressed": package.get("commandsSuppressed", False),
        }
        for field, package_value in checks.items():
            if item.get(field) != package_value:
                issues.append(f"{module}:{action}: summary {field} does not match package")
                all_items_valid = False

        if item.get("valid") is not (not package_issues):
            issues.append(f"{module}:{action}: item.valid does not match package validation result")
            all_items_valid = False
        if item.get("issues") != package_issues:
            issues.append(f"{module}:{action}: item.issues does not match package validation issues")
            all_items_valid = False

    if plan is not None:
        stages = plan.get("stages")
        if isinstance(stages, list):
            plan_keys = {
                (str(stage.get("module", "")).strip(), str(stage.get("action", "")).strip())
                for stage in stages
                if isinstance(stage, dict)
            }
            if seen != plan_keys:
                issues.append("summary items must match capture-plan module/action set")

    if summary.get("valid") is not all_items_valid:
        issues.append("summary.valid must match aggregate item validation")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a capture authorization package-set summary.")
    parser.add_argument("summary_json")
    parser.add_argument("--plan-json", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = load_summary(Path(args.summary_json))
        plan = load_plan(Path(args.plan_json)) if args.plan_json else None
        issues = validate_package_set(summary, plan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = {"ok": not issues, "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Capture authorization package set validation passed.")
    else:
        print("Capture authorization package set validation failed:")
        for issue in issues:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
