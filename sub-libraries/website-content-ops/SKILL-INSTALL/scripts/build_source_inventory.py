#!/usr/bin/env python3
"""Create a local source inventory for user files before AllinCMS site packaging."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import sys
from typing import Any


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "spreadsheet",
    ".xls": "spreadsheet",
    ".csv": "spreadsheet",
    ".tsv": "spreadsheet",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
}
SENSITIVE_NAME_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:password|secret|token|cookie|authorization|credential)\b", re.IGNORECASE),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: source inventory must be stored outside the skill package")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_type_for(path: Path) -> str:
    return SUPPORTED_EXTENSIONS.get(path.suffix.lower(), "unsupported")


def contains_sensitive_name(value: str) -> bool:
    return any(pattern.search(value) for pattern in SENSITIVE_NAME_PATTERNS)


def collect_files(paths: list[str], recursive: bool) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise SystemExit(f"ERROR: source path not found: {raw}")
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            found.extend(item for item in iterator if item.is_file())
        elif path.is_file():
            found.append(path)
    return sorted({item.resolve() for item in found})


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    ensure_output_outside_skill(output)
    files = collect_files(args.sources, args.recursive)
    entries: list[dict[str, Any]] = []
    unsupported: list[str] = []
    sensitive_names: list[str] = []
    empty_files: list[str] = []
    for index, path in enumerate(files):
        source_type = source_type_for(path)
        if source_type == "unsupported":
            unsupported.append(str(path))
        if contains_sensitive_name(path.name):
            sensitive_names.append(str(path))
        stat = path.stat()
        if stat.st_size == 0:
            empty_files.append(str(path))
        mime, _ = mimetypes.guess_type(str(path))
        entries.append(
            {
                "sourceRef": f"src-{index + 1:03d}",
                "path": str(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "type": source_type,
                "mimeType": mime or "application/octet-stream",
                "sizeBytes": stat.st_size,
                "sha256": file_hash(path),
                "intakeStatus": "needs_extraction" if source_type != "unsupported" else "unsupported",
                "notes": "",
            }
        )
    blockers: list[str] = []
    if not entries:
        blockers.append("no input files were found")
    if unsupported:
        blockers.append("unsupported source files: " + ", ".join(unsupported))
    if sensitive_names:
        blockers.append("source file names may contain sensitive values; rename or redact before durable handoff")
    if empty_files:
        blockers.append("empty source files: " + ", ".join(empty_files))
    return {
        "kind": "allincms_source_inventory",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "runLabel": args.run_label,
        "sourceRootPolicy": "runtime_artifacts_only_not_skill_package",
        "entries": entries,
        "summary": {
            "fileCount": len(entries),
            "byType": summarize_types(entries),
            "unsupportedCount": len(unsupported),
            "sensitiveNameCount": len(sensitive_names),
            "emptyFileCount": len(empty_files),
        },
        "blockedUntil": blockers,
        "nextActions": [
            "Extract raw text/tables/images/URLs into raw-extraction artifacts.",
            "Build source wiki from inventory plus extraction summaries.",
            "Keep raw files and extraction artifacts outside the skill package.",
        ],
    }


def summarize_types(entries: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in entries:
        source_type = str(entry.get("type", "unknown"))
        result[source_type] = result.get(source_type, 0) + 1
    return dict(sorted(result.items()))


def validate_inventory(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_source_inventory":
        issues.append("kind must be allincms_source_inventory")
    if data.get("localOnly") is not True:
        issues.append("localOnly must be true")
    if data.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    blocked_until = data.get("blockedUntil")
    if isinstance(blocked_until, list):
        for blocker in blocked_until:
            text = str(blocker)
            if text.startswith("unsupported source files:"):
                issues.append("blockedUntil contains unsupported source files")
            if text.startswith("source file names may contain sensitive values"):
                issues.append("blockedUntil contains sensitive-looking source file names")
            if text.startswith("empty source files:"):
                issues.append("blockedUntil contains empty source files")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        issues.append("entries must be a non-empty array")
        return issues
    seen_refs: set[str] = set()
    seen_hashes: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            issues.append(f"{label} must be an object")
            continue
        ref = entry.get("sourceRef")
        if not isinstance(ref, str) or not ref.startswith("src-"):
            issues.append(f"{label}.sourceRef must start with src-")
        elif ref in seen_refs:
            issues.append(f"{label}.sourceRef duplicates {ref}")
        else:
            seen_refs.add(ref)
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            issues.append(f"{label}.path is required")
        elif not Path(path).exists():
            issues.append(f"{label}.path does not exist")
        source_type = entry.get("type")
        if source_type not in set(SUPPORTED_EXTENSIONS.values()) | {"unsupported"}:
            issues.append(f"{label}.type is unsupported")
        elif source_type == "unsupported":
            issues.append(f"{label}.type must be supported before extraction")
        name = entry.get("name")
        if isinstance(name, str) and contains_sensitive_name(name):
            issues.append(f"{label}.name may contain sensitive values")
        size = entry.get("sizeBytes")
        if not isinstance(size, int) or size < 0:
            issues.append(f"{label}.sizeBytes must be a non-negative integer")
        elif size == 0:
            issues.append(f"{label}.sizeBytes must be greater than zero")
        sha = entry.get("sha256")
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            issues.append(f"{label}.sha256 must be a lowercase sha256 hex digest")
        elif sha in seen_hashes:
            issues.append(f"{label}.sha256 duplicates another source file")
        else:
            seen_hashes.add(sha)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS source inventory JSON from user files.")
    parser.add_argument("sources", nargs="+", help="Source files or directories")
    parser.add_argument("--recursive", action="store_true", help="Scan source directories recursively")
    parser.add_argument("--run-label", default="", help="Optional neutral run label")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    inventory = build_inventory(args)
    issues = validate_inventory(inventory)
    if issues:
        print("Source inventory validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source inventory: {output}")
    print(f"fileCount={inventory['summary']['fileCount']} blockedUntil={len(inventory['blockedUntil'])}")
    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
