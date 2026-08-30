#!/usr/bin/env python3
"""Apply validated per-action replay contracts to module-capture coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from update_module_capture_coverage import load_json, stage_key, validate_coverage, write_json
from validate_action_replay_contract import validate_contract


def load_contract(path: Path) -> dict[str, Any]:
    data = load_json(path)
    errors = validate_contract(data)
    if errors:
        raise ValueError(f"contract validation failed for {path}:\n" + "\n".join(f"- {error}" for error in errors))
    data["_sourcePath"] = str(path)
    return data


def apply_contracts(coverage: dict[str, Any], contracts: list[dict[str, Any]]) -> dict[str, Any]:
    validation = validate_coverage(coverage)
    if not validation["ok"]:
        raise ValueError("coverage validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    if coverage.get("interfaceCoverageComplete") is not True:
        raise ValueError("coverage.interfaceCoverageComplete must be true before replay contracts can make JSON replay ready")

    stages = coverage.get("stages")
    if not isinstance(stages, list):
        raise ValueError("coverage.stages must be an array")
    captured_stage_keys = [
        str(stage.get("stageKey"))
        for stage in stages
        if isinstance(stage, dict) and stage.get("status") == "captured"
    ]
    captured_set = set(captured_stage_keys)
    by_stage: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        key = stage_key(str(contract.get("module", "")).strip(), str(contract.get("action", "")).strip())
        if key not in captured_set:
            raise ValueError(f"contract {key} does not match a captured coverage stage")
        if key in by_stage:
            raise ValueError(f"duplicate replay contract for stage {key}")
        by_stage[key] = contract

    missing = [key for key in captured_stage_keys if key not in by_stage]
    if missing:
        raise ValueError("missing replay contracts for captured stages: " + ", ".join(missing))

    updated = json.loads(json.dumps(coverage, ensure_ascii=False))
    updated["actionReplayContractsVerified"] = True
    updated["jsonReplayReady"] = True
    updated["replayContractStageKeys"] = captured_stage_keys
    updated["replayContractCount"] = len(captured_stage_keys)
    updated["replayContracts"] = [
        {
            "stageKey": key,
            "module": by_stage[key].get("module", ""),
            "action": by_stage[key].get("action", ""),
            "authorizationAction": by_stage[key].get("authorizationAction", ""),
            "requestUrl": by_stage[key].get("requestUrl", ""),
            "contractPath": by_stage[key].get("_sourcePath", ""),
        }
        for key in captured_stage_keys
    ]
    updated["rule"] = (
        "JSON replay is ready only for the listed module/action contracts. "
        "This does not authorize replay and does not validate neighboring actions or future sessions."
    )
    updated_validation = validate_coverage(updated)
    if not updated_validation["ok"]:
        raise ValueError("updated coverage validation failed:\n" + "\n".join(f"- {issue}" for issue in updated_validation["issues"]))
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply per-action replay contracts to module coverage.")
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--contract", action="append", default=[], help="Replay contract JSON; repeat for each captured stage")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.contract:
        print("ERROR: provide at least one --contract", file=sys.stderr)
        return 2
    try:
        updated = apply_contracts(
            load_json(Path(args.coverage)),
            [load_contract(Path(path)) for path in args.contract],
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_json(Path(args.output), updated)
    if args.json:
        print(json.dumps({"ok": True, "output": args.output, "jsonReplayReady": updated.get("jsonReplayReady")}, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
