#!/usr/bin/env python3
"""Check per-round AllinCMS skill sedimentation and closeout reporting."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SEDIMENTATION = {"updated", "none"}


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


def git_changed_files(root: Path) -> list[str]:
    repo = root.parents[1]
    rel_root = root.relative_to(repo)
    result = subprocess.run(
        ["git", "status", "--short", "--", str(rel_root)],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"git status failed: {result.stderr.strip()}")
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip())
    return files


def parse_changed_files(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def validate_closeout(
    summary: dict[str, Any],
    sedimentation: str,
    note: str,
    changed_files: list[str],
    skill_root: Path,
    round_issues: list[str] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    if sedimentation not in ALLOWED_SEDIMENTATION:
        issues.append("sedimentation must be 'updated' or 'none'")
    if not note.strip():
        issues.append("sedimentation note is required")

    skill_changed = bool(changed_files)
    if skill_changed and sedimentation != "updated":
        issues.append("skill files changed, so sedimentation must be 'updated'")
    if not skill_changed and sedimentation == "updated":
        issues.append("sedimentation says updated, but no skill files are changed")

    if summary.get("valid") is not True:
        issues.append("run summary is not valid")
    if summary.get("complete") is True and summary.get("completionGaps"):
        issues.append("summary cannot be complete while completionGaps is non-empty")

    required_mentions = ("proven", "missing", "completionGaps", "nextActions")
    missing_mentions = [field for field in required_mentions if field not in summary]
    if missing_mentions:
        issues.append("summary missing fields: " + ", ".join(missing_mentions))

    summary_round_issues = summary.get("roundIssues")
    closeout_round_issues = [item.strip() for item in (round_issues or []) if item.strip()]
    if not closeout_round_issues:
        issues.append("closeout must include at least one --round-issue item or no-change observation")
    if summary.get("kind") == "allincms_round_maintenance_summary":
        if not isinstance(summary_round_issues, dict):
            issues.append("maintenance summary must include a roundIssues object")
        else:
            if summary_round_issues.get("checked") is not True:
                issues.append("roundIssues.checked must be true")
            issue_items = summary_round_issues.get("items")
            if not isinstance(issue_items, list) or not all(isinstance(item, str) and item.strip() for item in issue_items):
                issues.append("roundIssues.items must contain at least one non-empty issue or no-change observation")
            elif issue_items != closeout_round_issues:
                issues.append("summary roundIssues.items differ from closeout --round-issue arguments")
            if sedimentation == "updated" and summary_round_issues.get("reusableFindingsRecorded") is not True:
                issues.append("roundIssues.reusableFindingsRecorded must be true when sedimentation is updated")
            if sedimentation == "none" and summary_round_issues.get("noReusableUpdateNeeded") is not True:
                issues.append("roundIssues.noReusableUpdateNeeded must be true when sedimentation is none")

    note_lower = note.lower()
    if sedimentation == "none" and "no reusable skill update needed" not in note_lower:
        issues.append("no-update closeout note must include 'no reusable skill update needed'")

    summary_sedimentation = summary.get("sedimentation")
    if summary.get("kind") == "allincms_round_maintenance_summary" and not isinstance(summary_sedimentation, dict):
        issues.append("maintenance summary must include a sedimentation object")
    if summary_sedimentation is not None:
        if not isinstance(summary_sedimentation, dict):
            issues.append("summary sedimentation must be an object when present")
        else:
            summary_status = summary_sedimentation.get("status")
            summary_note = str(summary_sedimentation.get("note", "")).strip()
            summary_changed_files = summary_sedimentation.get("changedFiles", [])
            summary_findings_recorded = summary_sedimentation.get("findingsRecorded")

            if summary_status != sedimentation:
                issues.append("summary sedimentation status differs from closeout argument")
            if summary_note != note.strip():
                issues.append("summary sedimentation note differs from closeout argument")
            if summary_changed_files != changed_files:
                issues.append("summary sedimentation changedFiles differ from closeout argument")
            if sedimentation == "updated" and summary_findings_recorded is not True:
                issues.append("summary sedimentation findingsRecorded must be true when updated")
            if sedimentation == "none" and summary_findings_recorded is not False:
                issues.append("summary sedimentation findingsRecorded must be false when none")

    return {
        "ok": not issues,
        "skillRoot": str(skill_root),
        "sedimentation": sedimentation,
        "note": note,
        "skillChanged": skill_changed,
        "changedFiles": changed_files,
        "roundIssues": closeout_round_issues,
        "summary": {
            "valid": summary.get("valid"),
            "complete": summary.get("complete"),
            "siteKey": summary.get("siteKey"),
            "contentType": summary.get("contentType"),
            "freshForMutation": summary.get("evidenceFreshness", {}).get("freshForMutation"),
            "proven": summary.get("proven", []),
            "missing": summary.get("missing", []),
            "completionGaps": summary.get("completionGaps", []),
            "nextActions": summary.get("nextActions", []),
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AllinCMS per-round closeout.")
    parser.add_argument("--summary", required=True, help="JSON output from summarize_run_status.py")
    parser.add_argument("--sedimentation", choices=sorted(ALLOWED_SEDIMENTATION), required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--skill-root", default=str(DEFAULT_ROOT))
    parser.add_argument(
        "--changed-files",
        default=None,
        help="Comma-separated skill files changed in this round; defaults to git status for the skill root",
    )
    parser.add_argument(
        "--round-issue",
        action="append",
        default=[],
        help="Reusable problem, command drift, validation gap, or explicit no-change observation from this round.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    try:
        root = Path(args.skill_root).resolve()
        changed_files = parse_changed_files(args.changed_files) if args.changed_files is not None else git_changed_files(root)
        result = validate_closeout(
            load_json(Path(args.summary)),
            args.sedimentation,
            args.note,
            changed_files,
            root,
            args.round_issue,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["ok"]:
            print("Round closeout check passed.")
        else:
            print("Round closeout check failed:")
            for issue in result["issues"]:
                print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
