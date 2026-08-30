#!/usr/bin/env python3
"""Validate a theme design-save (pageDocument) JSON replay payload before it is sent.

Theme page design-save is a Next.js Server Action (`POST .../design`) whose body is a
one-element array carrying the whole-page `pageDocument`. It is JSON-replayable, but the
save action must be captured via CDP (a late window.fetch patch cannot see it). This gate
validates the replay body shape locally so that, once a live session supplies the current
`next-action` id, the whole-page replay is ready and cannot ship placeholder copy or local
image paths.

Payload contract (redacted; real ids stay in the run folder):
  [ { "siteId", "themeId", "pageId", "intent": "save",
      "pageDocument": { "root": "page-root",
                        "elements": { "<blockId>": { "type": "<blockType>", "props": {...} } } } } ]

See references/server-action-save-api.md (§7 theme scopes) and references/request-capture.md
(2026-06-29 captured pageDocument shape).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# Unambiguous placeholder/residue terms only. Do NOT include common words like "your" —
# professional copy legitimately says "send us your instrument ports and test conditions".
PLACEHOLDER_TERMS = ("待补", "lorem ipsum", "todo", "tbd", "placeholder", "draft product", "example.com/image")
LOCAL_PATH_HINTS = ("/tmp/", "./", "../", "file://", "C:\\", "/Users/", "/home/")


def _iter_prop_strings(props: Any, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(props, dict):
        for k, v in props.items():
            out.extend(_iter_prop_strings(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(props, list):
        for i, v in enumerate(props):
            out.extend(_iter_prop_strings(v, f"{prefix}[{i}]"))
    elif isinstance(props, str):
        out.append((prefix, props))
    return out


def _validate_media_urls(props: Any, block_id: str, issues: list[str]) -> None:
    for path, value in _iter_prop_strings(props):
        lowered = path.lower()
        if ("url" in lowered or "src" in lowered or "image" in lowered) and value:
            if value.startswith(("http://", "https://")):
                continue
            if any(hint in value for hint in LOCAL_PATH_HINTS) or value.startswith("/") or value.startswith("."):
                issues.append(f"element {block_id} prop {path} is a local/relative path, not a public URL: {value!r}")


def validate_theme_replay(payload: Any, require_publication_ready: bool = False) -> dict:
    """Validate a theme design-save replay body; `valid` is False when it must not be sent."""
    issues: list[str] = []
    if not isinstance(payload, list) or len(payload) != 1:
        return {"kind": "allincms_theme_page_document_validation", "valid": False,
                "issues": ["payload must be a one-element array (the Server Action argument list)"]}
    obj = payload[0]
    if not isinstance(obj, dict):
        return {"kind": "allincms_theme_page_document_validation", "valid": False,
                "issues": ["payload[0] must be an object"]}

    for key in ("siteId", "themeId", "pageId"):
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            issues.append(f"payload[0].{key} is required and must be a non-empty string")
    if obj.get("intent") != "save":
        issues.append("payload[0].intent must be 'save' for a design-save replay")

    doc = obj.get("pageDocument")
    if not isinstance(doc, dict):
        issues.append("payload[0].pageDocument must be an object")
        return {"kind": "allincms_theme_page_document_validation", "valid": not issues, "issues": issues}
    if not isinstance(doc.get("root"), str) or not doc["root"].strip():
        issues.append("pageDocument.root is required (e.g. 'page-root')")
    elements = doc.get("elements")
    if not isinstance(elements, dict) or not elements:
        issues.append("pageDocument.elements must be a non-empty object keyed by block id")
        return {"kind": "allincms_theme_page_document_validation", "valid": not issues, "issues": issues}

    for block_id, block in elements.items():
        if not isinstance(block, dict):
            issues.append(f"element {block_id} must be an object")
            continue
        if not isinstance(block.get("type"), str) or not block["type"].strip():
            issues.append(f"element {block_id}.type is required and must be a non-empty string")
        props = block.get("props")
        if props is not None and not isinstance(props, dict):
            issues.append(f"element {block_id}.props must be an object when present")
            continue
        _validate_media_urls(props, block_id, issues)
        if require_publication_ready and isinstance(props, dict):
            for path, value in _iter_prop_strings(props):
                low = value.lower()
                if any(term in low for term in PLACEHOLDER_TERMS):
                    issues.append(f"element {block_id} prop {path} contains placeholder/residue text: {value[:40]!r}")

    return {
        "kind": "allincms_theme_page_document_validation",
        "elementCount": len(elements),
        "requirePublicationReady": require_publication_ready,
        "valid": not issues,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a theme design-save (pageDocument) JSON replay payload.")
    parser.add_argument("payload_json")
    parser.add_argument("--require-publication-ready", action="store_true")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.payload_json, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report = validate_theme_replay(payload, args.require_publication_ready)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["valid"]:
        print("theme pageDocument validation passed.")
    else:
        for issue in report["issues"]:
            print(f"  [theme] {issue}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
