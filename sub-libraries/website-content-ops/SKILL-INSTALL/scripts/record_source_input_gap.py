#!/usr/bin/env python3
"""Append source-input field gaps discovered during AllinCMS operation.

The ledger is run evidence for later PDF/catalog/brief extraction. Keep it
outside the skill package so temporary business material does not become
durable skill content.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


VALID_CLASSIFICATIONS = {
    "required",
    "recommended",
    "optional",
    "user-confirmed",
    "source-derived",
    "blocked-until-schema-captured",
    "not-in-scope",
}
VALID_EVIDENCE = {
    "ui-only",
    "request-captured",
    "request-captured-empty-schema-only",
    "sample-verified",
    "simulated-only",
    "blocked",
    "not-captured",
}
VALID_DECISIONS = {
    "user-must-provide",
    "can-infer-from-source",
    "omit",
    "preserve-existing",
    "defer",
    "needs-schema-capture",
    "needs-user-confirmation",
}
VALID_ACTIONS = {"append", "init"}
SUPPORTED_CONTENT_TYPES = {
    "global",
    "products",
    "posts",
    "forms",
    "media",
    "themes/pages",
    "routes",
    "site-info",
    "domains",
    "tracking",
    "navigation",
}
SENSITIVE_PATTERNS = {
    "email_address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "credential_header": re.compile(r"\b(?:cookie|authorization|bearer|next-action)\b", re.IGNORECASE),
    "mongo_like_id": re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "kind": "allincms_source_input_gap_ledger",
            "generatedAt": now_iso(),
            "updatedAt": None,
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "siteKey": "",
            "entries": [],
            "summary": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in ledger: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit("ERROR: ledger root must be an object")
    if data.get("kind") != "allincms_source_input_gap_ledger":
        raise SystemExit("ERROR: unsupported ledger kind")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("ERROR: ledger.entries must be an array")
    return data


def repo_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = repo_skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: source-input gap ledgers must be stored outside the skill package")


def reject_sensitive(label: str, value: str) -> None:
    for code, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(value):
            raise SystemExit(f"ERROR: {label} contains sensitive or raw identifier pattern: {code}")


def validate_entry(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    content_type = entry.get("contentType")
    if content_type not in SUPPORTED_CONTENT_TYPES:
        errors.append(f"contentType must be one of {sorted(SUPPORTED_CONTENT_TYPES)}")
    if not isinstance(entry.get("field"), str) or not entry["field"].strip():
        errors.append("field is required")
    if not isinstance(entry.get("target"), str) or not entry["target"].strip():
        errors.append("target is required")
    classifications = entry.get("classification")
    if not isinstance(classifications, list) or not classifications:
        errors.append("classification must contain at least one value")
    else:
        unknown = sorted(set(classifications) - VALID_CLASSIFICATIONS)
        if unknown:
            errors.append("unknown classification: " + ", ".join(unknown))
    if entry.get("currentEvidence") not in VALID_EVIDENCE:
        errors.append(f"currentEvidence must be one of {sorted(VALID_EVIDENCE)}")
    if entry.get("decisionNeeded") not in VALID_DECISIONS:
        errors.append(f"decisionNeeded must be one of {sorted(VALID_DECISIONS)}")
    for key in ("sourceHint", "generationRule", "operatorNote"):
        value = entry.get(key)
        if value is not None and not isinstance(value, str):
            errors.append(f"{key} must be a string")
    for key in ("sourceHint", "generationRule", "evidencePointer"):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} is required so the gap can drive later source extraction")
    if entry.get("currentEvidence") in {"ui-only", "request-captured", "sample-verified"}:
        note = entry.get("operatorNote")
        if not isinstance(note, str) or not note.strip():
            errors.append("operatorNote is required when currentEvidence claims UI/request/sample proof")
    return errors


def build_entry(args: argparse.Namespace) -> dict[str, Any]:
    classification = parse_csv(args.classification)
    entry = {
        "recordedAt": now_iso(),
        "contentType": args.content_type,
        "field": args.field,
        "target": args.target,
        "classification": sorted(set(classification)),
        "sourceHint": args.source_hint,
        "generationRule": args.generation_rule,
        "currentEvidence": args.current_evidence,
        "decisionNeeded": args.decision_needed,
        "evidencePointer": args.evidence_pointer,
        "operatorNote": args.operator_note,
    }
    for key, value in entry.items():
        if isinstance(value, str):
            reject_sensitive(key, value)
    errors = validate_entry(entry)
    if errors:
        raise SystemExit("ERROR: invalid entry:\n- " + "\n- ".join(errors))
    return entry


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_content_type: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    blocked: list[str] = []
    user_inputs: list[str] = []
    for entry in entries:
        content_type = str(entry.get("contentType", ""))
        by_content_type[content_type] = by_content_type.get(content_type, 0) + 1
        decision = str(entry.get("decisionNeeded", ""))
        by_decision[decision] = by_decision.get(decision, 0) + 1
        classes = entry.get("classification", [])
        label = f"{content_type}.{entry.get('field')}"
        if "blocked-until-schema-captured" in classes or decision == "needs-schema-capture":
            blocked.append(label)
        if decision in {"user-must-provide", "needs-user-confirmation"} or "user-confirmed" in classes:
            user_inputs.append(label)
    return {
        "entryCount": len(entries),
        "byContentType": dict(sorted(by_content_type.items())),
        "byDecisionNeeded": dict(sorted(by_decision.items())),
        "blockedFields": sorted(set(blocked)),
        "userInputFields": sorted(set(user_inputs)),
    }


def validate_ledger(data: dict[str, Any], *, expected_site_key: str = "") -> list[str]:
    errors: list[str] = []
    if data.get("kind") != "allincms_source_input_gap_ledger":
        errors.append("kind must be allincms_source_input_gap_ledger")
    if data.get("localOnly") is not True:
        errors.append("localOnly must be true")
    if data.get("remoteMutationsPerformed") is not False:
        errors.append("remoteMutationsPerformed must be false")
    site_key = data.get("siteKey")
    if site_key is not None and not isinstance(site_key, str):
        errors.append("siteKey must be a string when present")
    elif expected_site_key and site_key and site_key != expected_site_key:
        errors.append(f"siteKey {site_key!r} does not match expected {expected_site_key!r}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        errors.append("entries must be an array")
        return errors
    seen: set[tuple[str, str, str]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{index}] must be an object")
            continue
        for field_error in validate_entry(entry):
            errors.append(f"entries[{index}]: {field_error}")
        key = (
            str(entry.get("contentType", "")),
            str(entry.get("field", "")),
            str(entry.get("target", "")),
        )
        if key in seen:
            errors.append(f"entries[{index}] duplicates contentType/field/target {key!r}")
        seen.add(key)
        for string_key, value in entry.items():
            if isinstance(value, str):
                try:
                    reject_sensitive(f"entries[{index}].{string_key}", value)
                except SystemExit as exc:
                    errors.append(str(exc).replace("ERROR: ", ""))
    summary = data.get("summary")
    if isinstance(summary, dict):
        actual = summarize([entry for entry in entries if isinstance(entry, dict)])
        for key in ("entryCount", "blockedFields", "userInputFields"):
            if summary.get(key) != actual.get(key):
                errors.append(f"summary.{key} does not match entries")
    return errors


def apply_action(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    ensure_output_outside_skill(output)
    ledger = load_ledger(output)
    if args.site_key:
        reject_sensitive("siteKey", args.site_key)
        ledger["siteKey"] = args.site_key
    if args.action == "append":
        ledger["entries"].append(build_entry(args))
    ledger["updatedAt"] = now_iso()
    ledger["summary"] = summarize(ledger["entries"])
    errors = validate_ledger(ledger, expected_site_key=args.site_key if args.site_key else "")
    if errors:
        raise SystemExit("ERROR: invalid ledger:\n- " + "\n- ".join(errors))
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description="Record AllinCMS source-input field gaps into a local run ledger.")
    parser.add_argument("--output", required=True, help="Ledger JSON path outside the skill package, usually ~/allincms-projects/...")
    parser.add_argument("--action", choices=sorted(VALID_ACTIONS), default="append")
    parser.add_argument("--site-key", default="", help="Optional site key; avoid account/private labels")
    parser.add_argument("--content-type", choices=sorted(SUPPORTED_CONTENT_TYPES), default="global")
    parser.add_argument("--field", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--classification", default="required,user-confirmed")
    parser.add_argument("--source-hint", default="")
    parser.add_argument("--generation-rule", default="")
    parser.add_argument("--current-evidence", choices=sorted(VALID_EVIDENCE), default="not-captured")
    parser.add_argument("--decision-needed", choices=sorted(VALID_DECISIONS), default="user-must-provide")
    parser.add_argument("--evidence-pointer", default="")
    parser.add_argument("--operator-note", default="")
    parser.add_argument("--validate-only", action="store_true", help="Validate an existing ledger without modifying it")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        output = Path(args.output)
        ensure_output_outside_skill(output)
        ledger = load_ledger(output)
        errors = validate_ledger(ledger, expected_site_key=args.site_key if args.site_key else "")
        if errors:
            print("ERROR: invalid source-input gap ledger:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 2
        print(f"Valid source-input gap ledger: {output}")
        if args.json:
            print(json.dumps(ledger, ensure_ascii=False, indent=2))
        return 0

    if args.action == "append" and (not args.field.strip() or not args.target.strip()):
        print("ERROR: --field and --target are required for append", file=sys.stderr)
        return 2

    ledger = apply_action(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source-input gap ledger: {output}")
    print(f"entryCount={ledger['summary']['entryCount']} blockedFields={len(ledger['summary']['blockedFields'])}")
    if args.json:
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
