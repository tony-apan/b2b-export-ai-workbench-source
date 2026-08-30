#!/usr/bin/env python3
"""Validate an AllinCMS launch proof plan artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_launch_plan import validate_launch_plan


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"launch plan JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid launch plan JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("launch plan JSON root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS launch proof plan safety.")
    parser.add_argument("launch_plan_json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_launch_plan(load_json(Path(args.launch_plan_json)))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Launch plan validation passed.")
    else:
        print("Launch plan validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
