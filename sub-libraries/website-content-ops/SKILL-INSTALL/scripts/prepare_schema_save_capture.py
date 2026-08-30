#!/usr/bin/env python3
"""Prepare save-capture artifacts after a create-probe stage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from build_probe_save_runbook import build_runbook, validate_runbook
from prepare_probe_save_handoff import build_handoff as build_save_handoff
from prepare_probe_save_handoff import validate_handoff as validate_save_handoff
from summarize_schema_capture_progress import summarize as summarize_schema_progress
from summarize_schema_capture_progress import validate_create_evidence_for_stage


CONTENT_TYPES = {"products", "posts"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def stage_for_content_type(handoff: dict[str, Any], content_type: str) -> dict[str, Any]:
    stages = handoff.get("stages")
    if not isinstance(stages, list):
        raise SystemExit("ERROR: schema-capture handoff stages must be an array")
    for stage in stages:
        if isinstance(stage, dict) and stage.get("contentType") == content_type:
            return stage
    raise SystemExit(f"ERROR: content type not found in schema-capture handoff: {content_type}")


def best_edit_url(create_evidence: dict[str, Any]) -> str:
    for key in ("editUrl", "probeEditUrl", "targetEditUrl"):
        value = create_evidence.get(key)
        if isinstance(value, str) and value.startswith("https://workspace.laicms.com/"):
            return value
    browser_action = create_evidence.get("browserAction")
    if isinstance(browser_action, dict):
        for key in ("editUrl", "probeEditUrl", "targetEditUrl", "currentUrl"):
            value = browser_action.get(key)
            if isinstance(value, str) and value.startswith("https://workspace.laicms.com/"):
                return value
    raise SystemExit("ERROR: create evidence must contain a concrete workspace probe edit URL")


def artifact_paths(output_dir: Path, content_type: str) -> dict[str, Path]:
    return {
        "save_handoff": output_dir / f"{content_type}-save-handoff.json",
        "save_runbook": output_dir / f"{content_type}-save-runbook.json",
        "schema_progress": output_dir / "schema-capture-progress.after-save-runbook.json",
        "summary": output_dir / f"{content_type}-schema-save-capture-preparation-summary.json",
    }


def content_pairs(existing: list[str], content_type: str, path: str) -> list[str]:
    pairs = [item for item in existing if not item.startswith(f"{content_type}=")]
    pairs.append(f"{content_type}={path}")
    return pairs


def build(args: argparse.Namespace) -> dict[str, Any]:
    if args.content_type not in CONTENT_TYPES:
        raise SystemExit(f"ERROR: --content-type must be one of {sorted(CONTENT_TYPES)}")
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    paths = artifact_paths(output_dir, args.content_type)

    schema_handoff = load_json(Path(args.schema_capture_handoff), "schema-capture handoff")
    if schema_handoff.get("kind") != "allincms_schema_capture_handoff":
        raise SystemExit("ERROR: schema-capture handoff kind mismatch")
    if schema_handoff.get("remoteMutationsPerformed") is not False:
        raise SystemExit("ERROR: schema-capture handoff must be local-only/no remote mutation")
    stage = stage_for_content_type(schema_handoff, args.content_type)
    if stage.get("status") != "ready_for_create_probe_authorization":
        raise SystemExit(f"ERROR: content type is not ready for create-probe evidence: {stage.get('status')}")
    create_evidence = load_json(Path(args.create_evidence), "create evidence")
    create_issues = validate_create_evidence_for_stage(create_evidence, stage)
    if create_issues:
        raise SystemExit("ERROR: invalid create evidence:\n- " + "\n- ".join(create_issues))

    edit_url = args.edit_url or best_edit_url(create_evidence)
    create_probe = stage.get("createProbe") if isinstance(stage.get("createProbe"), dict) else {}
    authorization_output = args.authorization_output or str(create_probe.get("authorizationOutput", "")).replace(
        "create-probe",
        "save-probe",
    )
    if not authorization_output:
        authorization_output = str(output_dir / f"{args.content_type}-save-authorization.json")
    preflight_path = args.preflight or str(stage.get("contentPreflight", {}).get("preflightEvidence", ""))
    if not preflight_path:
        raise SystemExit("ERROR: preflight path missing; pass --preflight")

    save_handoff = build_save_handoff(
        create_evidence=create_evidence,
        create_evidence_path=args.create_evidence,
        preflight_path=preflight_path,
        edit_url=edit_url,
        authorization_output=authorization_output,
    )
    save_handoff_issues = validate_save_handoff(save_handoff)
    if save_handoff_issues:
        raise SystemExit("ERROR: generated save handoff invalid:\n- " + "\n- ".join(save_handoff_issues))
    write_json(paths["save_handoff"], save_handoff)

    save_runbook = build_runbook(save_handoff, handoff_path=str(paths["save_handoff"]))
    save_runbook_issues = validate_runbook(save_runbook)
    if save_runbook_issues:
        raise SystemExit("ERROR: generated save runbook invalid:\n- " + "\n- ".join(save_runbook_issues))
    write_json(paths["save_runbook"], save_runbook)

    progress = summarize_schema_progress(
        SimpleNamespace(
            schema_capture_handoff=args.schema_capture_handoff,
            create_evidence=content_pairs(args.existing_create_evidence, args.content_type, args.create_evidence),
            save_handoff=content_pairs(args.existing_save_handoff, args.content_type, str(paths["save_handoff"])),
            save_runbook=content_pairs(args.existing_save_runbook, args.content_type, str(paths["save_runbook"])),
            save_capture=args.existing_save_capture,
            base_run_evidence=args.existing_base_run_evidence,
            schema_manifest=args.existing_schema_manifest,
            output=str(paths["schema_progress"]),
            fail_on_incomplete=False,
            json=False,
        )
    )
    write_json(paths["schema_progress"], progress)
    content_result = next(
        (item for item in progress.get("results", []) if isinstance(item, dict) and item.get("contentType") == args.content_type),
        {},
    )
    summary = {
        "kind": "allincms_schema_save_capture_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentType": args.content_type,
        "siteKey": save_handoff.get("siteKey"),
        "target": edit_url,
        "artifacts": {
            "saveHandoff": str(paths["save_handoff"]),
            "saveRunbook": str(paths["save_runbook"]),
            "schemaCaptureProgress": str(paths["schema_progress"]),
        },
        "validation": {
            "createEvidenceIssues": create_issues,
            "saveHandoffIssues": save_handoff_issues,
            "saveRunbookIssues": save_runbook_issues,
        },
        "progressStatus": content_result.get("status", ""),
        "nextAction": content_result.get("nextAction", "execute save runbook after action-time authorization and gate"),
        "adversarialChecks": [
            "This step prepares save capture only; it does not click save or capture a real request.",
            "The save runbook remains browserStepsExecutable=false until save_probe authorization and gate pass.",
            "Create-probe authorization does not authorize save, publish, cleanup, sample upload, or batch upload.",
            "Products and posts keep separate save handoff/runbook artifacts.",
        ],
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare save-capture handoff/runbook after create-probe evidence.")
    parser.add_argument("--schema-capture-handoff", required=True)
    parser.add_argument("--content-type", required=True, choices=sorted(CONTENT_TYPES))
    parser.add_argument("--create-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--preflight", default="")
    parser.add_argument("--edit-url", default="")
    parser.add_argument("--authorization-output", default="")
    parser.add_argument("--existing-create-evidence", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-handoff", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-runbook", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-capture", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-base-run-evidence", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-schema-manifest", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    print(f"Wrote schema save-capture preparation summary: {summary['artifacts']['schemaCaptureProgress']}")
    print(f"contentType={summary['contentType']} progressStatus={summary['progressStatus']} nextAction={summary['nextAction']}")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
