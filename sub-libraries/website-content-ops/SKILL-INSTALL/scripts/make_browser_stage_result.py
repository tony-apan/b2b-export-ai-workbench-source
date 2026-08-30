#!/usr/bin/env python3
"""Create a redacted AllinCMS browser stage result from a stage packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apply_browser_stage_result import VALID_RESULT_STATUSES, build_stage_result, split_csv, validate_browser_stage_result
from build_browser_stage_packet import validate_browser_stage_packet


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"packet JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid packet JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("packet JSON root must be an object")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_from_packet(args: argparse.Namespace) -> dict:
    packet = load_json(Path(args.packet_json))
    packet_validation = validate_browser_stage_packet(packet)
    if not packet_validation["ok"]:
        raise ValueError("packet validation failed:\n" + "\n".join(f"- {issue}" for issue in packet_validation["issues"]))

    stage_id = str(packet.get("stageId", "")).strip()
    evidence_pointers = split_csv(args.evidence_pointers)
    blocking_issues = split_csv(args.blocking_issues)
    if args.proof_recorded:
        proof_recorded = split_csv(args.proof_recorded)
    elif args.status == "completed":
        proof_recorded = [str(item) for item in packet.get("requiredProof", []) if isinstance(item, str) and item.strip()]
    else:
        proof_recorded = []

    browser_stage_mutated_remote = args.browser_stage_mutated_remote or (
        args.status == "completed" and packet.get("remoteMutationExpectation") == "must"
    )

    result = build_stage_result(
        stage_id,
        args.status,
        evidence_pointers,
        proof_recorded,
        blocking_issues,
        browser_stage_mutated_remote,
    )
    if args.operator_note:
        result["operatorNote"] = args.operator_note
    result_validation = validate_browser_stage_result(result, packet)
    if not result_validation["ok"]:
        raise ValueError(
            "browser stage result validation failed:\n"
            + "\n".join(f"- {issue}" for issue in result_validation["issues"])
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an AllinCMS browser stage result JSON from a stage packet.")
    parser.add_argument("--packet-json", required=True)
    parser.add_argument("--status", choices=sorted(VALID_RESULT_STATUSES), required=True)
    parser.add_argument("--evidence-pointers", default="", help="Comma-separated redacted proof pointers")
    parser.add_argument("--proof-recorded", default="", help="Comma-separated proof labels; completed defaults to packet.requiredProof")
    parser.add_argument("--blocking-issues", default="", help="Comma-separated blockers for blocked or partial results")
    parser.add_argument("--operator-note", default="")
    parser.add_argument(
        "--browser-stage-mutated-remote",
        action="store_true",
        help=(
            "Set only after an authorized browser stage has actually changed LAICMS remote state. "
            "The result artifact itself remains localOnly and remoteMutationsPerformed=false."
        ),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_from_packet(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_json(Path(args.output), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote browser stage result: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
