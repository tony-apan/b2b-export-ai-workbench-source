#!/usr/bin/env python3
"""Build a readiness report for a prepared AllinCMS next-browser-action handoff."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from check_pre_mutation_gate import DEFAULT_MAX_AGE_MINUTES
from summarize_run_status import freshness_status
from validate_browser_stage_authorization_package import load_json
from validate_next_browser_action_handoff import validate_handoff


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_preflight_from_handoff(handoff: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    source_files = handoff.get("sourceFiles")
    if not isinstance(source_files, dict):
        return None, ""
    preflight_path = str(source_files.get("preflight", "") or "").strip()
    if not preflight_path:
        return None, ""
    return load_json(Path(preflight_path), "preflight"), preflight_path


def build_report(
    handoff_path: Path,
    *,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    handoff = load_json(handoff_path, "handoff")
    validation = validate_handoff(handoff, max_age_minutes=max_age_minutes, now=now)
    preflight, preflight_path = load_preflight_from_handoff(handoff)
    freshness = (
        freshness_status(preflight, max_age_minutes=max_age_minutes, now=now)
        if isinstance(preflight, dict)
        else {
            "generatedAt": "",
            "maxAgeMinutes": max_age_minutes,
            "freshForMutation": False,
            "reason": "missing_preflight_source",
        }
    )
    prepared_only_ok = (
        handoff.get("preparedOnly") is True
        and handoff.get("isUserAuthorization") is False
        and handoff.get("remoteMutationsPerformed") is False
    )
    ready = validation["ok"] and prepared_only_ok and freshness.get("freshForMutation") is True
    blockers: list[str] = []
    if not validation["ok"]:
        blockers.append("handoff_validation_failed")
    if not prepared_only_ok:
        blockers.append("preparation_only_flags_invalid")
    if freshness.get("freshForMutation") is not True:
        blockers.append("preflight_not_fresh_for_mutation")

    return {
        "kind": "allincms_next_browser_action_handoff_readiness",
        "generatedAt": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "remoteMutationsPerformed": False,
        "handoff": str(handoff_path),
        "preflight": preflight_path,
        "target": handoff.get("target"),
        "action": handoff.get("action"),
        "stopAfter": handoff.get("stopAfter"),
        "preparedOnly": handoff.get("preparedOnly"),
        "isUserAuthorization": handoff.get("isUserAuthorization"),
        "validation": validation,
        "evidenceFreshness": freshness,
        "status": "ready_to_request_authorization" if ready else "blocked_refresh_readonly_evidence",
        "blockers": blockers,
        "nextAction": (
            "ask the user for exact action-time authorization; do not run commands until they provide it"
            if ready
            else "refresh read-only evidence and rebuild the next-browser-action handoff before asking for authorization"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build readiness for one AllinCMS next-browser-action handoff.")
    parser.add_argument("handoff_json")
    parser.add_argument("--max-age-minutes", type=int, default=DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    try:
        report = build_report(Path(args.handoff_json), max_age_minutes=args.max_age_minutes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).expanduser().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"status={report['status']} freshness={report['evidenceFreshness'].get('reason')}")
    if args.fail_on_blocked and report["status"] != "ready_to_request_authorization":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
