#!/usr/bin/env python3
"""Refuse a JSON batch when the captured `next-action` IDs are stale for the current deployment.

AllinCMS Server Action `next-action` IDs are build artifacts: they change on every
deployment. Replaying a batch with action IDs captured against an older deployment fails
silently (the server rejects or misroutes the action). This gate compares the save
contract's captured deployment against the deployment observed live right before the batch
and refuses when they differ, when the capture is missing a deployment marker, or when
required action IDs are absent.

Read the current deployment id live (e.g. from the backend build/deployment marker) right
before the batch and pass it via --current-deployment-id. See
references/server-action-save-api.md (§5 next-action per-deployment drift).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

REQUIRED_ACTION_GROUPS = ("actions", "postActions", "deleteActions")


def _collect_action_ids(contract: dict) -> dict[str, str]:
    ids: dict[str, str] = {}
    for group in REQUIRED_ACTION_GROUPS:
        block = contract.get(group)
        if isinstance(block, dict):
            for name, value in block.items():
                if isinstance(value, str) and value.strip():
                    ids[f"{group}.{name}"] = value
    return ids


def check_freshness(contract: dict, current_deployment_id: str, required_actions: list[str] | None = None) -> dict:
    """Return a freshness report; `fresh` is False when the contract must not be replayed."""
    issues: list[str] = []
    if not isinstance(contract, dict):
        return {"kind": "allincms_next_action_freshness", "fresh": False, "issues": ["contract must be an object"]}

    captured = str(contract.get("deploymentId") or contract.get("capturedForDeployment") or "").strip()
    current = str(current_deployment_id or "").strip()

    if not current:
        issues.append("current deployment id is empty; read it live before the batch and pass --current-deployment-id")
    if not captured:
        issues.append("contract has no deploymentId/capturedForDeployment marker; re-capture the actions and record the deployment")
    elif current and captured != current:
        issues.append(
            f"captured deployment {captured!r} != current {current!r}; next-action IDs are stale, re-capture before the batch"
        )

    action_ids = _collect_action_ids(contract)
    if not action_ids:
        issues.append("contract has no next-action IDs under actions/postActions/deleteActions")
    for name, value in action_ids.items():
        if not isinstance(value, str) or len(value.strip()) < 8:
            issues.append(f"{name} is not a plausible next-action id: {value!r}")

    for wanted in required_actions or []:
        if wanted not in action_ids:
            issues.append(f"required action {wanted!r} is missing from the contract")

    return {
        "kind": "allincms_next_action_freshness",
        "capturedDeployment": captured,
        "currentDeployment": current,
        "actionCount": len(action_ids),
        "fresh": not issues,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check next-action freshness for the current deployment before a batch.")
    parser.add_argument("contract_json")
    parser.add_argument("--current-deployment-id", required=True)
    parser.add_argument("--require-action", action="append", default=[], help="Require this <group>.<name> action id to be present")
    parser.add_argument("--output", help="Write the freshness report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.contract_json, encoding="utf-8") as fh:
            contract = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report = check_freshness(contract, args.current_deployment_id, args.require_action)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["fresh"]:
        print("next-action freshness check passed.")
    else:
        for issue in report["issues"]:
            print(f"  [next-action] {issue}")
    return 0 if report["fresh"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
