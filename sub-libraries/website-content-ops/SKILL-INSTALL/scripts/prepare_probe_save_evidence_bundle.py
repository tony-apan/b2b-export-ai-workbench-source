#!/usr/bin/env python3
"""Prepare a local evidence bundle for one save-probe browser run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import sys
from typing import Any

from build_probe_save_runbook import validate_runbook
from prepare_probe_save_handoff import parse_edit_url


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def evidence_template(runbook: dict[str, Any]) -> dict[str, Any]:
    target = str(runbook["target"])
    parts = parse_edit_url(target)
    authorization_record = str(runbook.get("redactedEvidenceTemplate", {}).get("authorizationRecord", ""))
    return {
        "kind": "allincms_probe_save_capture_evidence",
        "contentType": parts["contentType"],
        "target": target,
        "authorizationRecord": authorization_record,
        "preMutationGate": "passed|required_before_save",
        "savedOnce": False,
        "published": False,
        "requestCapture": {
            "method": "POST",
            "url": target,
            "headers": ["Accept", "Content-Type"],
            "payloadShape": {
                "siteId": "<redacted>",
                f"{parts['contentType'].rstrip('s')}Id": "<redacted>",
                "mode": "update",
                "content": "captured-non-empty-editor-block-shape-required",
            },
            "contentBlockShape": "to_fill_after_capture",
            "idFields": "siteId and content id values redacted",
            "mode": "update",
            "publishBehavior": "publish-separate",
            "responseStatus": None,
            "responseMimeType": "",
        },
        "fieldMapping": {
            "nameField": "to_verify",
            "slugField": "to_verify",
            "descriptionField": "to_verify",
            "bodyField": "to_verify",
            "mediaField": "to_verify",
            "statusField": "to_verify",
        },
        "payloadTemplate": {
            "siteId": "<redacted>",
            f"{parts['contentType'].rstrip('s')}Id": "<redacted>",
            "mode": "update",
            "content": "{capturedContentBlocks}",
        },
        "backendPersisted": False,
        "stopConditionMet": False,
    }


def source_handoff_base_run_evidence(runbook: dict[str, Any]) -> str:
    handoff_path = str(runbook.get("sourceHandoff", ""))
    if not handoff_path:
        return ""
    handoff = load_json(Path(handoff_path), "source handoff")
    source_files = handoff.get("sourceFiles")
    if not isinstance(source_files, dict):
        return ""
    base_run_evidence = str(source_files.get("preflight", ""))
    if base_run_evidence and Path(base_run_evidence).exists():
        return base_run_evidence
    return ""


def validation_command(evidence_path: Path, output_dir: Path, base_run_evidence: str) -> str:
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/validate_probe_save_capture_evidence.py",
        str(evidence_path),
    ]
    if base_run_evidence:
        parts.extend(["--base-run-evidence", base_run_evidence])
    parts.extend(["--output", str(output_dir / "save-capture-evidence-validation.json")])
    return " ".join(shlex.quote(part) for part in parts)


def build_bundle(runbook: dict[str, Any], *, runbook_path: str, output_dir: Path) -> dict[str, Any]:
    issues = validate_runbook(runbook)
    if issues:
        raise ValueError("runbook validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    target = str(runbook.get("target", ""))
    parts = parse_edit_url(target)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "save-capture-evidence.template.json"
    filled_evidence_path = output_dir / "save-capture-evidence.filled.json"
    notes_path = output_dir / "capture-notes.md"
    validation_path = output_dir / "validation-command.txt"

    template = evidence_template(runbook)
    evidence_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    filled_evidence_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    base_run_evidence = source_handoff_base_run_evidence(runbook)
    validation_path.write_text(validation_command(filled_evidence_path, output_dir, base_run_evidence) + "\n", encoding="utf-8")
    notes = [
        "# Save Probe Evidence Bundle",
        "",
        "This bundle is local scaffolding only. It does not authorize browser actions.",
        "",
        "Before creating `save-capture-evidence.filled.json`:",
        "- create the action-time authorization record",
        "- run the save_probe pre-mutation gate",
        "- confirm the browser is still on the target edit URL",
        "- enable network capture",
        "- copy the template to `save-capture-evidence.filled.json` only after replacing all template placeholders with redacted real evidence",
        "",
        "During the browser run, capture:",
        "- unique rich editor focus and typed sample proof",
        "- update button enabled after typing",
        "- exactly one save/update click",
        "- POST URL, method, response status, response MIME type",
        "- header names only, never cookie/authorization/header values",
        "- redacted payload keys and nested content block shape",
        "- backend persistence proof",
        "- proof that publish/upload/batch/cleanup did not happen",
        "",
        "The validation command binds to base run evidence only when the source handoff exposes a preflight/run-evidence file.",
        "Do not pass the handoff JSON itself as `--base-run-evidence`.",
        "The validation command intentionally targets `save-capture-evidence.filled.json`, not the unfilled template.",
        "",
        f"Target: `{target}`",
        f"Content type: `{parts['contentType']}`",
    ]
    notes_path.write_text("\n".join(notes) + "\n", encoding="utf-8")

    return {
        "kind": "allincms_probe_save_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "runbook": runbook_path,
        "sourceHandoff": str(runbook.get("sourceHandoff", "")),
        "baseRunEvidence": base_run_evidence,
        "target": target,
        "siteKey": parts["siteKey"],
        "contentType": parts["contentType"],
        "evidenceTemplate": str(evidence_path),
        "filledEvidencePath": str(filled_evidence_path),
        "captureNotes": str(notes_path),
        "validationCommandFile": str(validation_path),
        "validationCommandRequiresFilledEvidence": True,
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "action-time save_probe authorization",
            "pre-mutation gate pass",
            "network capture enabled",
            "browser target URL rechecked",
        ],
    }


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_probe_save_evidence_bundle":
        issues.append("kind must be allincms_probe_save_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    if bundle.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if bundle.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must be false")
    for key in ("runbook", "target", "evidenceTemplate", "filledEvidencePath", "captureNotes", "validationCommandFile"):
        value = bundle.get(key)
        if not isinstance(value, str) or not value:
            issues.append(f"{key} must be present")
    if bundle.get("validationCommandRequiresFilledEvidence") is not True:
        issues.append("validationCommandRequiresFilledEvidence must be true")
    base = bundle.get("baseRunEvidence")
    if base is not None and not isinstance(base, str):
        issues.append("baseRunEvidence must be a string when present")
    if isinstance(bundle.get("target"), str):
        try:
            parse_edit_url(bundle["target"])
        except ValueError as exc:
            issues.append(str(exc))
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include pre-mutation gate pass")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local evidence bundle for save-probe capture.")
    parser.add_argument("runbook_json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        runbook = load_json(Path(args.runbook_json), "runbook")
        output_dir = Path(args.output_dir)
        bundle = build_bundle(runbook, runbook_path=args.runbook_json, output_dir=output_dir)
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("bundle validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
        manifest_path = output_dir / "evidence-bundle.json"
        manifest_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote save evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
