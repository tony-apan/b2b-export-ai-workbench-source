#!/usr/bin/env python3
"""Build a read-only browser brief for collecting create-site preflight evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_package_confirmation import load_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output path must be outside the skill package")


def site_proposal(package: dict[str, Any]) -> dict[str, str]:
    site = package.get("siteProposal") if isinstance(package.get("siteProposal"), dict) else {}
    return {
        "siteName": str(site.get("siteName", "")).strip(),
        "siteDescription": str(site.get("siteDescription", "")).strip(),
        "language": str(site.get("language", "")).strip(),
        "industry": str(site.get("industry", "")).strip(),
    }


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_brief(brief: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if brief.get("kind") != "allincms_create_site_preflight_brief":
        issues.append("kind must be allincms_create_site_preflight_brief")
    for key in ("localOnly", "preparedOnly"):
        if brief.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization"):
        if brief.get(key) is not False:
            issues.append(f"{key} must be false")
    if brief.get("target") != "https://workspace.laicms.com/sites":
        issues.append("target must be https://workspace.laicms.com/sites")
    for key in ("package", "confirmation", "executionPlan", "preflightOutput", "nextCommandAfterPreflight"):
        if not nonempty_string(brief.get(key)):
            issues.append(f"{key} is required")
    site = brief.get("siteProposal")
    if not isinstance(site, dict):
        issues.append("siteProposal must be an object")
    else:
        for key in ("siteName", "siteDescription"):
            if not nonempty_string(site.get(key)):
                issues.append(f"siteProposal.{key} is required")
    tasks = brief.get("readOnlyBrowserTasks")
    if not isinstance(tasks, list) or not tasks:
        issues.append("readOnlyBrowserTasks must be a non-empty array")
    else:
        task_text = " ".join(str(item).lower() for item in tasks)
        for phrase in ("open https://workspace.laicms.com/sites", "dialog", "close"):
            if phrase not in task_text:
                issues.append(f"readOnlyBrowserTasks must include {phrase}")
    evidence_rules = brief.get("evidenceRules")
    if not isinstance(evidence_rules, list) or not evidence_rules:
        issues.append("evidenceRules must be a non-empty array")
    command = str(brief.get("preflightCommandTemplate") or "")
    empty_command = str(brief.get("emptyListCommandTemplate") or "")
    if "make_create_preflight_evidence.py" not in command or "--dialog-closed-verified" not in command:
        issues.append("preflightCommandTemplate must build create preflight evidence and require dialog closure")
    if "make_create_preflight_evidence.py" not in empty_command or "--no-existing-sites" not in empty_command:
        issues.append("emptyListCommandTemplate must support verified empty site lists")
    next_command = str(brief.get("nextCommandAfterPreflight") or "")
    if "prepare_confirmed_site_execution.py" not in next_command or "--create-preflight" not in next_command:
        issues.append("nextCommandAfterPreflight must rerun confirmed execution with --create-preflight")
    forbidden = brief.get("forbiddenActions")
    if not isinstance(forbidden, list) or not forbidden:
        issues.append("forbiddenActions must be a non-empty array")
    else:
        forbidden_text = " ".join(str(item).lower() for item in forbidden)
        for phrase in ("do not submit", "do not use this brief as user authorization"):
            if phrase not in forbidden_text:
                issues.append(f"forbiddenActions must include {phrase}")
    for key in ("preflightOutput", "package", "confirmation", "executionPlan"):
        value = brief.get(key)
        if isinstance(value, str) and value:
            try:
                resolved = Path(value).expanduser().resolve()
            except OSError:
                issues.append(f"{key} must be a valid path")
                continue
            root = skill_root().resolve()
            if resolved == root or root in resolved.parents:
                issues.append(f"{key} must point outside the skill package")
    return issues


def build_validation_report(brief: dict[str, Any], brief_path: str = "") -> dict[str, Any]:
    issues = validate_brief(brief)
    return {
        "kind": "allincms_create_site_preflight_brief_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "brief": brief_path,
        "issues": issues,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    package = load_json(Path(args.package), "package")
    confirmation = load_json(Path(args.confirmation), "confirmation")
    execution_plan = load_json(Path(args.execution_plan), "execution plan")
    site = site_proposal(package)
    if not site["siteName"] or not site["siteDescription"]:
        raise SystemExit("ERROR: package siteProposal.siteName and siteDescription are required")
    if confirmation.get("kind") != "allincms_source_site_package_confirmation":
        raise SystemExit("ERROR: confirmation kind must be allincms_source_site_package_confirmation")
    if execution_plan.get("kind") != "allincms_confirmed_site_execution_plan":
        raise SystemExit("ERROR: execution plan kind must be allincms_confirmed_site_execution_plan")
    if execution_plan.get("targetMode") != "new_site":
        raise SystemExit("ERROR: create-site preflight brief requires a new_site execution plan")
    # The review packet path is baked into nextCommandAfterPreflight; validate it here so a
    # bad/missing path fails at brief time instead of surfacing two steps later in
    # prepare_confirmed_site_execution.py.
    if args.review_packet:
        review_packet = load_json(Path(args.review_packet), "review packet")
        if review_packet.get("kind") != "allincms_source_package_review_packet":
            raise SystemExit("ERROR: review packet kind must be allincms_source_package_review_packet")

    preflight_output = args.preflight_output or str(output.with_name("create-site-preflight.json"))
    brief = {
        "kind": "allincms_create_site_preflight_brief",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "target": "https://workspace.laicms.com/sites",
        "package": args.package,
        "confirmation": args.confirmation,
        "executionPlan": args.execution_plan,
        "siteProposal": site,
        "preflightOutput": preflight_output,
        "readOnlyBrowserTasks": [
            "open https://workspace.laicms.com/sites",
            "verify login by loading the /sites route in the current browser session",
            "record existing site keys from backend URLs, hrefs, safe attributes, or verified empty list",
            "open the create-site dialog without submitting it",
            "within the scoped dialog, record create site entry, dialog, name field, description field, submit/create control, and close control",
            "close the dialog and verify no visible create-site dialog remains",
        ],
        "evidenceRules": [
            "site keys must come from strong route/href/safe-attribute evidence, not memory or full-page regex",
            "empty site list is valid only with explicit verified-empty evidence",
            "create fields must include normalized create site entry and dialog evidence scoped to the modal/dialog surface",
            "dialogClosedVerified must be true before preflight evidence is accepted",
        ],
        "preflightCommandTemplate": (
            "python3 skills/allincms-bulk-content-upload/scripts/make_create_preflight_evidence.py "
            "--existing-site-keys <comma-separated-site-keys> "
            "--site-key-evidence '<semicolon-separated-strong-evidence>' "
            "--observed-create-fields '<semicolon-separated fields including create site entry, dialog, name, description, submit, close>' "
            "--dialog-closed-verified "
            f"--output {preflight_output}"
        ),
        "emptyListCommandTemplate": (
            "python3 skills/allincms-bulk-content-upload/scripts/make_create_preflight_evidence.py "
            "--no-existing-sites "
            "--empty-site-list-evidence '<verified empty /sites list evidence>' "
            "--observed-create-fields '<semicolon-separated fields including create site entry, dialog, name, description, submit, close>' "
            "--dialog-closed-verified "
            f"--output {preflight_output}"
        ),
        "nextCommandAfterPreflight": (
            "python3 skills/allincms-bulk-content-upload/scripts/prepare_confirmed_site_execution.py "
            f"--package {args.package} "
            f"--review-packet {args.review_packet} "
            "--user-confirmation-text '<current user confirmation text>' "
            f"--output-dir {Path(output).parent} "
            "--target-mode new_site "
            f"--create-preflight {preflight_output} "
            f"--create-authorization-output {args.create_authorization_output}"
        ),
        "forbiddenActions": [
            "do not submit the create-site form",
            "do not save, upload, publish, create probes, edit theme/routes/forms/settings, bind domains, or add tracking",
            "do not use this brief as user authorization",
            "do not infer site keys or dialog fields from memory",
        ],
        "nextAction": "collect read-only create-site preflight evidence, then rerun confirmed execution preparation with --create-preflight",
    }
    validation_issues = validate_brief(brief)
    if validation_issues:
        raise SystemExit("ERROR: generated create-site preflight brief is invalid:\n- " + "\n- ".join(validation_issues))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only brief for create-site preflight collection.")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--preflight-output", default="")
    parser.add_argument("--create-authorization-output", default="~/allincms-projects/allincms-authorization-create-site.json")
    parser.add_argument("--validate-only", default="")
    parser.add_argument("--validation-output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        brief = load_json(Path(args.validate_only), "create-site preflight brief")
        report = build_validation_report(brief, args.validate_only)
        if args.validation_output:
            output = Path(args.validation_output).expanduser().resolve()
            ensure_output_outside_skill(output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif report["issues"]:
            print("Create-site preflight brief invalid:")
            for issue in report["issues"]:
                print(f"- {issue}")
        else:
            print("Create-site preflight brief validation passed.")
        return 0 if report["valid"] else 1

    for key in ("package", "review_packet", "confirmation", "execution_plan", "output"):
        if not getattr(args, key):
            parser.error(f"--{key.replace('_', '-')} is required unless --validate-only is used")
    brief = build(args)
    print(f"Wrote create-site preflight brief: {args.output}")
    print(f"preflightOutput={brief['preflightOutput']}")
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
