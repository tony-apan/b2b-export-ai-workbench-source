#!/usr/bin/env python3
"""Create a closeout summary for AllinCMS skill-maintenance rounds.

Use this when the current round updates docs/scripts or runs local validation
without producing a run-evidence file for summarize_run_status.py.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_round_issues(values: list[str]) -> list[str]:
    issues = [item.strip() for item in values if item.strip()]
    return issues


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    changed_files = parse_csv(args.changed_files)
    round_issues = parse_round_issues(args.round_issue)
    findings_recorded = args.sedimentation == "updated"
    summary = {
        "kind": "allincms_round_maintenance_summary",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "valid": True,
        "complete": False,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": "",
        "contentType": args.content_type,
        "roundType": args.round_type,
        "proven": [
            "skill_sedimentation_checked",
            "local_maintenance_summary_generated",
        ],
        "missing": [
            "remote_browser_persistence_not_checked",
            "real_laicms_run_evidence_not_present",
        ],
        "completionGaps": [
            "This is a maintenance closeout summary, not proof of site creation, launch, upload, publish, or cleanup.",
        ],
        "nextActions": [
            "Use real run evidence from browser operation or full rehearsal before claiming LAICMS site-build/upload completion.",
        ],
        "evidenceFreshness": {
            "freshForMutation": False,
            "reason": "maintenance summary is not mutation preflight evidence",
        },
        "roundIssues": {
            "checked": True,
            "items": round_issues,
            "reusableFindingsRecorded": findings_recorded,
            "noReusableUpdateNeeded": args.sedimentation == "none",
        },
        "sedimentation": {
            "status": args.sedimentation,
            "note": args.note,
            "findingsRecorded": findings_recorded,
            "changedFiles": changed_files,
        },
    }
    if args.proven:
        summary["proven"].extend(parse_csv(args.proven))
    if args.missing:
        summary["missing"].extend(parse_csv(args.missing))
    if args.completion_gap:
        summary["completionGaps"].extend(parse_csv(args.completion_gap))
    if args.next_action:
        summary["nextActions"].extend(parse_csv(args.next_action))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an AllinCMS maintenance-round summary.")
    parser.add_argument("--output", required=True, help="Path to write summary JSON")
    parser.add_argument(
        "--round-type",
        default="skill_maintenance",
        choices=["skill_maintenance", "documentation_update", "helper_validation", "request_analysis"],
    )
    parser.add_argument("--content-type", default="", help="Optional content type under discussion")
    parser.add_argument("--sedimentation", choices=["updated", "none"], required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--changed-files", default="", help="Comma-separated changed skill files")
    parser.add_argument(
        "--round-issue",
        action="append",
        default=[],
        help="Reusable problem, command drift, validation gap, or explicit no-change observation from this round.",
    )
    parser.add_argument("--proven", default="", help="Comma-separated extra proven items")
    parser.add_argument("--missing", default="", help="Comma-separated extra missing items")
    parser.add_argument("--completion-gap", default="", help="Comma-separated extra completion gaps")
    parser.add_argument("--next-action", default="", help="Comma-separated extra next actions")
    parser.add_argument("--json", action="store_true", help="Also print summary JSON")
    args = parser.parse_args()

    summary = build_summary(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote maintenance summary: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
