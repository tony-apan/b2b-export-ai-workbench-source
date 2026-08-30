#!/usr/bin/env python3
"""Validate an AllinCMS staged browser execution ledger artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_browser_execution_ledger import validate_browser_execution_ledger


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"browser execution ledger JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid browser execution ledger JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("browser execution ledger JSON root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS staged browser execution ledger safety.")
    parser.add_argument("browser_execution_ledger_json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_browser_execution_ledger(load_json(Path(args.browser_execution_ledger_json)))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Browser execution ledger validation passed.")
    else:
        print("Browser execution ledger validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
