#!/usr/bin/env python3
"""Summarize per-content-type schema-capture progress from local artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from build_probe_save_runbook import build_runbook as build_save_runbook
from prepare_probe_save_handoff import build_handoff as build_save_handoff
from validate_manifest import load_manifest, validate_manifest
from validate_probe_save_capture_evidence import load_json as load_capture_json
from validate_probe_save_capture_evidence import validate_capture_evidence


CONTENT_TYPES = ("products", "posts")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: str, label: str) -> tuple[dict[str, Any] | None, str]:
    if not path:
        return None, ""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{label} not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid {label}: {exc}"
    if not isinstance(data, dict):
        return None, f"{label} root must be an object"
    return data, ""


def require_handoff(data: dict[str, Any]) -> None:
    if data.get("kind") != "allincms_schema_capture_handoff":
        raise ValueError("schema-capture handoff kind mismatch")
    if data.get("remoteMutationsPerformed") is not False:
        raise ValueError("schema-capture handoff must be local-only/no remote mutation")


def stage_by_content_type(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = handoff.get("stages")
    if not isinstance(stages, list):
        raise ValueError("schema-capture handoff stages must be an array")
    result: dict[str, dict[str, Any]] = {}
    for item in stages:
        if isinstance(item, dict) and item.get("contentType") in CONTENT_TYPES:
            result[str(item["contentType"])] = item
    return result


def validate_create_evidence_for_stage(create_evidence: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    content_type = stage.get("contentType")
    expected_action = stage.get("createProbe", {}).get("action") if isinstance(stage.get("createProbe"), dict) else ""
    if create_evidence.get("kind") != "allincms_redacted_browser_stage_evidence":
        issues.append("create evidence kind must be allincms_redacted_browser_stage_evidence")
    if create_evidence.get("action") != expected_action:
        issues.append(f"create evidence action must be {expected_action}")
    if create_evidence.get("contentType") != content_type:
        issues.append("create evidence contentType must match stage")
    browser_action = create_evidence.get("browserAction")
    if not isinstance(browser_action, dict):
        issues.append("create evidence browserAction is required")
    else:
        if browser_action.get("stopConditionMet") is not True:
            issues.append("create evidence must prove stopConditionMet")
        if browser_action.get("saveClicked") is not False:
            issues.append("create evidence must show saveClicked=false")
        if browser_action.get("publishClicked") is not False:
            issues.append("create evidence must show publishClicked=false")
    cleanup = create_evidence.get("cleanupCandidate")
    if not isinstance(cleanup, dict) or cleanup.get("exists") is not True:
        issues.append("create evidence must record cleanupCandidate.exists=true")
    return issues


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
    return ""


def artifact_path(mapping: dict[str, str], content_type: str) -> str:
    return mapping.get(content_type, "")


def parse_pairs(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"expected contentType=path pair: {raw}")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in CONTENT_TYPES:
            raise ValueError(f"contentType must be one of {CONTENT_TYPES}: {key}")
        if not value:
            raise ValueError(f"path is required for {key}")
        result[key] = value
    return result


def schema_manifest_status(path: str) -> tuple[bool, list[str]]:
    if not path:
        return False, ["schema manifest missing"]
    manifest = load_manifest(Path(path))
    errors = validate_manifest(manifest, require_schema_verified=True)
    return not errors, errors


def summarize_content_type(
    *,
    stage: dict[str, Any],
    create_evidence_path: str,
    save_handoff_path: str,
    save_runbook_path: str,
    save_capture_path: str,
    base_run_evidence_path: str,
    schema_manifest_path: str,
) -> dict[str, Any]:
    content_type = str(stage.get("contentType", ""))
    if stage.get("status") == "skipped_no_manifest_items":
        return {
            "contentType": content_type,
            "status": "skipped_no_manifest_items",
            "nextAction": "none",
            "blockers": [],
        }
    if stage.get("status") != "ready_for_create_probe_authorization":
        return {
            "contentType": content_type,
            "status": "blocked_readonly_preflight",
            "nextAction": "merge content-type read-only preflight and rebuild schema-capture handoff",
            "blockers": [f"stage status is {stage.get('status')}"],
        }

    create_evidence, create_error = load_json(create_evidence_path, f"{content_type} create evidence")
    if create_error or not isinstance(create_evidence, dict):
        return {
            "contentType": content_type,
            "status": "ready_for_create_probe",
            "nextAction": "run create-probe browser stage after action-time authorization and gate",
            "blockers": [create_error or "create evidence missing"],
            "authorizationRecordCommand": stage.get("createProbe", {}).get("authorizationRecordCommand", ""),
            "preMutationGateCommand": stage.get("createProbe", {}).get("preMutationGateCommand", ""),
        }
    create_issues = validate_create_evidence_for_stage(create_evidence, stage)
    edit_url = best_edit_url(create_evidence)
    if create_issues or not edit_url:
        blockers = create_issues[:]
        if not edit_url:
            blockers.append("create evidence must contain concrete probe edit URL")
        return {
            "contentType": content_type,
            "status": "create_probe_evidence_blocked",
            "nextAction": "repair create evidence before save handoff",
            "blockers": blockers,
        }

    save_handoff, save_handoff_error = load_json(save_handoff_path, f"{content_type} save handoff")
    if save_handoff_error or not isinstance(save_handoff, dict):
        create_probe = stage.get("createProbe") if isinstance(stage.get("createProbe"), dict) else {}
        auth_output = str(create_probe.get("authorizationOutput", "")).replace("create-probe", "save-probe")
        return {
            "contentType": content_type,
            "status": "ready_for_save_handoff",
            "nextAction": "run prepare_probe_save_handoff.py and build_probe_save_runbook.py",
            "blockers": [save_handoff_error or "save handoff missing"],
            "prepareProbeSaveHandoffCommand": (
                "python3 skills/allincms-bulk-content-upload/scripts/prepare_probe_save_handoff.py "
                f"--create-evidence {create_evidence_path} "
                f"--preflight {stage.get('contentPreflight', {}).get('preflightEvidence', '')} "
                f"--edit-url {edit_url} "
                f"--authorization-output {auth_output} "
                f"--output {save_handoff_path}"
            ),
        }
    if save_handoff.get("kind") != "allincms_probe_save_handoff" or save_handoff.get("contentType") != content_type:
        return {
            "contentType": content_type,
            "status": "save_handoff_blocked",
            "nextAction": "repair save handoff for this content type",
            "blockers": ["save handoff kind/contentType mismatch"],
        }

    save_runbook, save_runbook_error = load_json(save_runbook_path, f"{content_type} save runbook")
    if save_runbook_error or not isinstance(save_runbook, dict):
        return {
            "contentType": content_type,
            "status": "ready_for_save_runbook",
            "nextAction": "run build_probe_save_runbook.py",
            "blockers": [save_runbook_error or "save runbook missing"],
            "buildProbeSaveRunbookCommand": (
                "python3 skills/allincms-bulk-content-upload/scripts/build_probe_save_runbook.py "
                f"{save_handoff_path} --output {save_runbook_path}"
            ),
        }
    if save_runbook.get("kind") != "allincms_probe_save_browser_runbook" or save_runbook.get("contentType") != content_type:
        return {
            "contentType": content_type,
            "status": "save_runbook_blocked",
            "nextAction": "repair save runbook for this content type",
            "blockers": ["save runbook kind/contentType mismatch"],
        }

    capture, capture_error = load_json(save_capture_path, f"{content_type} save capture evidence")
    if capture_error or not isinstance(capture, dict):
        return {
            "contentType": content_type,
            "status": "ready_for_save_capture",
            "nextAction": "execute save runbook after action-time authorization and pre-mutation gate",
            "blockers": [capture_error or "save capture evidence missing"],
            "saveRunbook": save_runbook_path,
        }
    base_run_evidence = None
    if base_run_evidence_path:
        base_run_evidence, base_error = load_json(base_run_evidence_path, f"{content_type} base run evidence")
        if base_error:
            return {
                "contentType": content_type,
                "status": "save_capture_blocked",
                "nextAction": "provide base run evidence for save-capture validation",
                "blockers": [base_error],
            }
    capture_issues = validate_capture_evidence(capture, base_run_evidence)
    if capture_issues:
        return {
            "contentType": content_type,
            "status": "save_capture_blocked",
            "nextAction": "repair save capture evidence",
            "blockers": capture_issues,
        }

    if not schema_manifest_path:
        schema_manifest_path = str(stage.get("afterSaveCapture", {}).get("applySaveCaptureCommand", "")).split("--output ")[-1].split()[0]
    if schema_manifest_path:
        try:
            schema_ok, schema_errors = schema_manifest_status(schema_manifest_path)
        except SystemExit as exc:
            schema_ok, schema_errors = False, [str(exc)]
    else:
        schema_ok, schema_errors = False, ["schema manifest path missing"]
    if not schema_ok:
        return {
            "contentType": content_type,
            "status": "ready_to_apply_save_capture",
            "nextAction": "run apply_save_capture_to_manifest.py and validate_manifest.py --require-schema-verified",
            "blockers": schema_errors,
            "applySaveCaptureCommand": stage.get("afterSaveCapture", {}).get("applySaveCaptureCommand", ""),
            "validateSchemaManifestCommand": stage.get("afterSaveCapture", {}).get("validateSchemaManifestCommand", ""),
        }

    return {
        "contentType": content_type,
        "status": "schema_manifest_ready",
        "nextAction": "build manifest sample upload runbook",
        "blockers": [],
        "schemaManifest": schema_manifest_path,
        "buildManifestSampleRunbookCommand": stage.get("afterSchemaManifest", {}).get("buildManifestSampleRunbookCommand", ""),
    }


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    handoff_data, handoff_error = load_json(args.schema_capture_handoff, "schema capture handoff")
    if handoff_error or not isinstance(handoff_data, dict):
        raise ValueError(handoff_error or "schema capture handoff missing")
    require_handoff(handoff_data)
    stages = stage_by_content_type(handoff_data)
    create_map = parse_pairs(args.create_evidence)
    save_handoff_map = parse_pairs(args.save_handoff)
    save_runbook_map = parse_pairs(args.save_runbook)
    save_capture_map = parse_pairs(args.save_capture)
    base_map = parse_pairs(args.base_run_evidence)
    schema_map = parse_pairs(args.schema_manifest)
    content_results: list[dict[str, Any]] = []
    for content_type in CONTENT_TYPES:
        stage = stages.get(content_type)
        if not stage:
            continue
        content_results.append(
            summarize_content_type(
                stage=stage,
                create_evidence_path=artifact_path(create_map, content_type),
                save_handoff_path=artifact_path(save_handoff_map, content_type),
                save_runbook_path=artifact_path(save_runbook_map, content_type),
                save_capture_path=artifact_path(save_capture_map, content_type),
                base_run_evidence_path=artifact_path(base_map, content_type),
                schema_manifest_path=artifact_path(schema_map, content_type),
            )
        )
    incomplete = [item for item in content_results if item.get("status") not in {"schema_manifest_ready", "skipped_no_manifest_items"}]
    return {
        "kind": "allincms_schema_capture_progress",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "schemaCaptureHandoff": args.schema_capture_handoff,
        "complete": not incomplete,
        "contentTypes": [item["contentType"] for item in content_results],
        "results": content_results,
        "nextAction": "build manifest sample upload runbook" if not incomplete else incomplete[0].get("nextAction", ""),
        "rule": "This status report reads local artifacts only; it does not authorize or perform browser mutations.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize schema-capture progress from local artifacts.")
    parser.add_argument("--schema-capture-handoff", required=True)
    parser.add_argument("--create-evidence", action="append", default=[], help="contentType=path")
    parser.add_argument("--save-handoff", action="append", default=[], help="contentType=path")
    parser.add_argument("--save-runbook", action="append", default=[], help="contentType=path")
    parser.add_argument("--save-capture", action="append", default=[], help="contentType=path")
    parser.add_argument("--base-run-evidence", action="append", default=[], help="contentType=path")
    parser.add_argument("--schema-manifest", action="append", default=[], help="contentType=path")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        report = summarize(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote schema-capture progress: {output}")
    print(f"complete={str(report['complete']).lower()} nextAction={report['nextAction']}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_on_incomplete and not report["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
