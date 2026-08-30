#!/usr/bin/env python3
"""Create resolved operation-gap evidence for AllinCMS source-input runs.

This helper does not edit the append-only gap ledger. It writes a separate
allincms_resolved_source_input_gaps file that later requirements generation can
use to filter superseded browser findings while preserving audit history.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from record_source_input_gap import ensure_output_outside_skill, load_ledger, reject_sensitive, validate_ledger


SENSITIVE_PATTERNS = {
    "credential_file": re.compile(r"\b(?:cookie|authorization|bearer|next-action)\b", re.IGNORECASE),
    "raw_object_id": re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_resolved_gap(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split("|")]
    data: dict[str, str] = {}
    for part in parts:
        if not part:
            continue
        if "=" not in part:
            raise SystemExit("ERROR: --resolved-gap items must use fieldLabel=...,proof=...,note=...")
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def reject_extra_sensitive(label: str, value: str) -> None:
    reject_sensitive(label, value)
    for code, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(value):
            raise SystemExit(f"ERROR: {label} contains sensitive or raw identifier pattern: {code}")


def validate_field_label(label: str) -> None:
    if "." not in label:
        raise SystemExit("ERROR: fieldLabel must be contentType.field")
    content_type, field = label.split(".", 1)
    if not content_type.strip() or not field.strip():
        raise SystemExit("ERROR: fieldLabel must contain non-empty contentType and field")


def gap_labels_from_ledger(path: str, site_key: str) -> set[str]:
    data = load_ledger(Path(path))
    errors = validate_ledger(data, expected_site_key=site_key)
    if errors:
        raise SystemExit("ERROR: invalid gap ledger:\n- " + "\n- ".join(errors))
    labels: set[str] = set()
    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue
        labels.add(f"{entry.get('contentType')}.{entry.get('field')}")
    return labels


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if not args.resolved_gap:
        raise SystemExit("ERROR: at least one --resolved-gap is required")

    ledger_labels: set[str] = set()
    if args.gap_ledger:
        ledger_labels = gap_labels_from_ledger(args.gap_ledger, args.site_key)

    resolved: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in args.resolved_gap:
        item = parse_resolved_gap(raw)
        label = item.get("fieldLabel", "")
        proof = item.get("proof", "")
        note = item.get("note", "")
        validate_field_label(label)
        if not proof:
            raise SystemExit("ERROR: proof is required for every resolved gap")
        if len(note.strip()) < 12:
            raise SystemExit("ERROR: note must explain the superseding evidence")
        for key, value in {"fieldLabel": label, "proof": proof, "note": note}.items():
            reject_extra_sensitive(key, value)
        if args.gap_ledger and label not in ledger_labels:
            raise SystemExit(f"ERROR: resolved fieldLabel {label!r} is not present in gap ledger")
        if label in seen:
            raise SystemExit(f"ERROR: duplicate resolved fieldLabel: {label}")
        seen.add(label)
        resolved.append({"fieldLabel": label, "proof": proof, "note": note})

    return {
        "kind": "allincms_resolved_source_input_gaps",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": args.site_key,
        "sourceGapLedger": args.gap_ledger,
        "resolvedGaps": resolved,
        "summary": {
            "resolvedCount": len(resolved),
            "resolvedFields": sorted(seen),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create AllinCMS resolved source-input gap evidence JSON.")
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--gap-ledger", default="", help="Optional gap ledger to prove each fieldLabel exists")
    parser.add_argument(
        "--resolved-gap",
        action="append",
        default=[],
        help="Repeatable: fieldLabel=products.specifications|proof=~/allincms-projects/redacted.json|note=Later proof superseded this gap.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    ensure_output_outside_skill(output)
    report = build_report(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"Wrote resolved gap evidence: {output}")
    print(f"resolvedCount={report['summary']['resolvedCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
