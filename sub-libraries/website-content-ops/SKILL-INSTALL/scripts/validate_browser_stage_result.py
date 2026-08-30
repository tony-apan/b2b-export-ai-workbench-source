#!/usr/bin/env python3
"""Validate an AllinCMS browser stage result artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apply_browser_stage_result import validate_browser_stage_result
from build_browser_stage_packet import validate_browser_stage_packet


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"browser stage result JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid browser stage result JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("browser stage result JSON root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS browser stage result safety.")
    parser.add_argument("browser_stage_result_json")
    parser.add_argument("--packet-json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        packet = load_json(Path(args.packet_json)) if args.packet_json else None
        if packet:
            packet_validation = validate_browser_stage_packet(packet)
            if not packet_validation["ok"]:
                raise ValueError("packet validation failed:\n" + "\n".join(f"- {issue}" for issue in packet_validation["issues"]))
        result = validate_browser_stage_result(load_json(Path(args.browser_stage_result_json)), packet)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Browser stage result validation passed.")
    else:
        print("Browser stage result validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
