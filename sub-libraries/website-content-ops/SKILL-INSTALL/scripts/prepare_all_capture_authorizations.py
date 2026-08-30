#!/usr/bin/env python3
"""Prepare and validate authorization packages for every capture-plan stage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from prepare_capture_authorization import build_package, load_plan
from validate_capture_authorization_package import validate_package
from validate_all_capture_authorizations import validate_package_set


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def build_package_set(
    *,
    capture_plan: dict[str, Any],
    preflight_path: str,
    output_dir: Path,
    allow_simulated_target: bool = False,
) -> dict[str, Any]:
    stages = capture_plan.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("capture plan must contain at least one stage")

    output_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise ValueError(f"stage {index} must be an object")
        module = str(stage.get("module", "")).strip()
        action = str(stage.get("action", "")).strip()
        if not module or not action:
            raise ValueError(f"stage {index} must include module and action")

        package_path = output_dir / f"{safe_name(module)}-{safe_name(action)}-authorization-package.json"
        authorization_output = output_dir / f"{safe_name(module)}-{safe_name(action)}-authorization-record.json"
        package = build_package(
            stage,
            preflight_path,
            str(authorization_output),
            allow_simulated_target=allow_simulated_target,
        )
        issues = validate_package(package, capture_plan)
        package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        items.append(
            {
                "module": module,
                "action": action,
                "authorizationAction": package.get("authorizationAction"),
                "target": package.get("target"),
                "gateSupported": package.get("gateSupported"),
                "jsonReplayReady": package.get("jsonReplayReady"),
                "commandsSuppressed": package.get("commandsSuppressed", False),
                "valid": not issues,
                "issues": issues,
                "package": str(package_path),
                "authorizationRecordOutput": str(authorization_output),
            }
        )

    return {
        "kind": "allincms_capture_authorization_package_set",
        "preparedOnly": True,
        "isUserAuthorization": False,
        "count": len(items),
        "valid": all(item["valid"] for item in items),
        "jsonReplayReady": False,
        "items": items,
        "warning": "This package set prepares commands and suggested wording only. It is not user authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare authorization packages for every capture-plan stage.")
    parser.add_argument("capture_plan_json")
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--summary-output", help="Defaults to <output-dir>/summary.json")
    parser.add_argument("--allow-simulated-target", action="store_true")
    args = parser.parse_args()

    try:
        plan = load_plan(Path(args.capture_plan_json))
        summary = build_package_set(
            capture_plan=plan,
            preflight_path=args.preflight,
            output_dir=Path(args.output_dir),
            allow_simulated_target=args.allow_simulated_target,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary_path = Path(args.summary_output) if args.summary_output else Path(args.output_dir) / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_issues = validate_package_set(summary, plan)
    if summary_issues:
        print(f"Wrote {summary_path}")
        print("Generated package set failed self-validation:", file=sys.stderr)
        for issue in summary_issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Wrote {summary_path}")
    if not summary["valid"]:
        for item in summary["items"]:
            if item["issues"]:
                print(f"{item['module']}:{item['action']}", file=sys.stderr)
                for issue in item["issues"]:
                    print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
