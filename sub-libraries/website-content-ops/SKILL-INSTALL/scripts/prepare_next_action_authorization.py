#!/usr/bin/env python3
"""Prepare a non-authorizing package from summarize_run_status next action details."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_DETAIL_FIELDS = (
    "action",
    "target",
    "authorizationText",
    "authorizationRecordCommand",
    "preMutationGateCommand",
)
PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"summary JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid summary JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("summary JSON root must be an object")
    return data


def select_detail(summary: dict[str, Any], action: str) -> dict[str, str]:
    if summary.get("valid") is not True:
        raise ValueError("summary must be valid before preparing authorization")
    details = summary.get("nextActionDetails")
    if not isinstance(details, list) or not details:
        raise ValueError("summary.nextActionDetails must contain at least one action detail")

    candidates: list[dict[str, Any]] = []
    for item in details:
        if isinstance(item, dict) and (not action or item.get("action") == action):
            candidates.append(item)
    if not candidates:
        raise ValueError(f"no nextActionDetails item found for action: {action}")
    if len(candidates) > 1:
        raise ValueError("multiple matching nextActionDetails found; pass --action")

    selected = candidates[0]
    missing = [key for key in REQUIRED_DETAIL_FIELDS if not isinstance(selected.get(key), str) or not selected[key].strip()]
    if missing:
        raise ValueError("next action detail missing fields: " + ", ".join(missing))
    return {key: str(selected[key]).strip() for key in REQUIRED_DETAIL_FIELDS}


def build_package(summary: dict[str, Any], detail: dict[str, str], preflight: str) -> dict[str, Any]:
    authorization_record_command = detail["authorizationRecordCommand"]
    pre_mutation_gate_command = detail["preMutationGateCommand"]
    return {
        "kind": "allincms_prepared_authorization_package",
        "stage": "next_action",
        "preparedOnly": True,
        "isUserAuthorization": False,
        "summarySiteKey": summary.get("siteKey", ""),
        "summaryContentType": summary.get("contentType", ""),
        "summaryNextActions": summary.get("nextActions", []),
        "evidenceFreshness": summary.get("evidenceFreshness", {}),
        "action": detail["action"],
        "target": detail["target"],
        "authorizationTextToRequest": detail["authorizationText"],
        "authorizationRecordCommandTemplate": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": bool(PLACEHOLDER_RE.search(authorization_record_command)),
        "preMutationGateCommand": pre_mutation_gate_command,
        "preflightEvidence": preflight,
        "stopCondition": (
            "Do not run the authorization-record command or mutate LAICMS until the current user sends "
            "action-time authorization text matching authorizationTextToRequest."
        ),
    }


def run_expected_gate_failure(command: str) -> dict[str, Any]:
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    combined = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    ok = result.returncode != 0 and "file not found" in combined.lower()
    return {
        "checked": True,
        "ok": ok,
        "exitCode": result.returncode,
        "expectedFailure": "missing authorization JSON",
        "output": combined,
    }


def validate_package(package: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if package.get("preparedOnly") is not True:
        issues.append("preparedOnly must be true")
    if package.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if not isinstance(package.get("authorizationTextToRequest"), str) or not package["authorizationTextToRequest"].strip():
        issues.append("authorizationTextToRequest is required")
    if not isinstance(package.get("authorizationRecordCommandTemplate"), str) or not package["authorizationRecordCommandTemplate"].strip():
        issues.append("authorizationRecordCommandTemplate is required")
    elif not package.get("authorizationRecordCommandHasPlaceholder"):
        issues.append("authorizationRecordCommandTemplate must retain the authorization-source placeholder")
    if not isinstance(package.get("preMutationGateCommand"), str) or not package["preMutationGateCommand"].strip():
        issues.append("preMutationGateCommand is required")
    gate = package.get("expectedGateFailure")
    if gate is not None:
        if not isinstance(gate, dict):
            issues.append("expectedGateFailure must be an object")
        elif gate.get("ok") is not True:
            issues.append("expectedGateFailure.ok must be true")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a non-authorizing package from run-summary next action details.")
    parser.add_argument("summary_json")
    parser.add_argument("--action", default="", help="Optional action to select from nextActionDetails")
    parser.add_argument("--preflight", required=True, help="Run evidence path used by the pre-mutation gate")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--expect-missing-authorization-failure",
        action="store_true",
        help="Run the pre-mutation gate command and require it to fail because the authorization JSON is missing",
    )
    args = parser.parse_args()

    try:
        summary = load_json(Path(args.summary_json))
        detail = select_detail(summary, args.action)
        package = build_package(summary, detail, args.preflight)
        if args.expect_missing_authorization_failure:
            package["expectedGateFailure"] = run_expected_gate_failure(detail["preMutationGateCommand"])
        issues = validate_package(package)
        if issues:
            raise ValueError("prepared package validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
