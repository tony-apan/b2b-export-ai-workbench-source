#!/usr/bin/env python3
"""Validate authorization and gate coverage for an AllinCMS capture plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from make_authorization_record import MUTATING_ACTIONS
from prepare_capture_authorization import FIELDS_BY_ACTION, GATED_ACTIONS


UNGATED_ALLOWED_ACTIONS = {"upload_media"}


def load_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"capture plan not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid capture plan JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("capture plan root must be an object")
    return data


def validate_plan_gate_coverage(
    plan: dict[str, Any],
    ungated_allowed_actions: set[str] | None = None,
) -> dict[str, Any]:
    allowed = set(UNGATED_ALLOWED_ACTIONS if ungated_allowed_actions is None else ungated_allowed_actions)
    issues: list[str] = []
    covered_actions: set[str] = set()
    ungated_allowed_seen: set[str] = set()

    if plan.get("kind") != "allincms_module_capture_plan":
        issues.append("capture plan kind must be allincms_module_capture_plan")

    stages = plan.get("stages")
    if not isinstance(stages, list):
        issues.append("capture plan stages must be an array")
        stages = []

    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            issues.append(f"stages[{index}] must be an object")
            continue
        label = f"stages[{index}]"
        module = stage.get("module", "")
        action_name = stage.get("action", "")
        if module or action_name:
            label = f"{label} {module}:{action_name}"

        authorization_action = stage.get("authorizationAction")
        if not isinstance(authorization_action, str) or not authorization_action.strip():
            issues.append(f"{label}: authorizationAction is required")
            continue
        authorization_action = authorization_action.strip()
        covered_actions.add(authorization_action)

        if authorization_action not in MUTATING_ACTIONS:
            issues.append(f"{label}: unknown authorizationAction {authorization_action}")
        if authorization_action not in FIELDS_BY_ACTION:
            issues.append(f"{label}: missing field template for {authorization_action}")
        elif not FIELDS_BY_ACTION[authorization_action]:
            issues.append(f"{label}: empty field template for {authorization_action}")

        if authorization_action in GATED_ACTIONS:
            continue
        if authorization_action in allowed:
            ungated_allowed_seen.add(authorization_action)
            continue
        issues.append(
            f"{label}: {authorization_action} has no pre-mutation gate and is not explicitly allowlisted"
        )

    return {
        "kind": "allincms_capture_plan_gate_coverage",
        "ok": not issues,
        "issues": issues,
        "stageCount": len(stages),
        "coveredActions": sorted(covered_actions),
        "ungatedAllowedActions": sorted(ungated_allowed_seen),
        "ungatedAllowlist": sorted(allowed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate capture-plan authorization and gate coverage.")
    parser.add_argument("capture_plan_json")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation output")
    args = parser.parse_args()

    try:
        plan = load_plan(Path(args.capture_plan_json))
        result = validate_plan_gate_coverage(plan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    elif args.json:
        print(text, end="")
    elif result["ok"]:
        print(
            "Capture plan gate coverage passed: "
            f"{result['stageCount']} stages, actions={','.join(result['coveredActions'])}"
        )
    else:
        print("Capture plan gate coverage failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
