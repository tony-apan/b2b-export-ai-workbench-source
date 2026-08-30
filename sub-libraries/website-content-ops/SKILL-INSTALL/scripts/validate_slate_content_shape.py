#!/usr/bin/env python3
"""Validate that manifest/product/post `content` fields are Slate node arrays.

AllinCMS stores rich-text bodies as Slate node arrays (`[{type, children:[{text}], id?}]`),
not markdown or HTML strings. A UI form save does not bind the Slate editor, so a body
authored as a markdown/HTML string will persist as an empty body on the live frontend.
This gate rejects `content` that is a string or a malformed node array BEFORE it enters a
manifest or a JSON replay payload, so the silent-empty-body failure is caught locally.

See references/server-action-save-api.md (Slate content contract) and
references/operational-findings.md (UI form save wipes Slate body).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

MARKDOWN_HINTS = ("#", "* ", "- ", "```", "<p>", "<div", "<br", "<span", "<h1", "<ul", "<ol")


def validate_slate_content(content: Any, path: str = "content") -> list[str]:
    """Return issues if `content` is not a valid Slate node array."""
    issues: list[str] = []
    if isinstance(content, str):
        issues.append(
            f"{path} is a string, not a Slate node array; author the body as "
            f"[{{'type':'p','children':[{{'text':...}}]}}], not markdown/HTML"
        )
        return issues
    if not isinstance(content, list):
        issues.append(f"{path} must be a list of Slate nodes, got {type(content).__name__}")
        return issues
    if not content:
        issues.append(f"{path} is empty; a body must have at least one Slate paragraph node")
        return issues
    for i, node in enumerate(content):
        node_path = f"{path}[{i}]"
        if not isinstance(node, dict):
            issues.append(f"{node_path} must be an object node, got {type(node).__name__}")
            continue
        if "type" not in node or not isinstance(node.get("type"), str) or not node["type"].strip():
            issues.append(f"{node_path}.type is required and must be a non-empty string")
        children = node.get("children")
        text = node.get("text")
        if children is None and text is None:
            issues.append(f"{node_path} must have `children` (leaf array) or a `text` value")
        if children is not None:
            if not isinstance(children, list) or not children:
                issues.append(f"{node_path}.children must be a non-empty list of leaves")
            else:
                for j, leaf in enumerate(children):
                    if not isinstance(leaf, dict) or "text" not in leaf:
                        issues.append(f"{node_path}.children[{j}] must be a leaf object with a `text` key")
    # Whole-body text sanity: flag only unambiguous markdown/HTML residue smuggled into leaf
    # text. Do NOT flag a leading '#' or '<' alone — technical copy legitimately uses "<10 GHz",
    # "#1 choice", etc. Only a real HTML tag or a fenced code block is a reliable residue signal.
    joined = _collect_text(content)
    if "```" in joined or re.search(r"</?[a-zA-Z][a-zA-Z0-9]*(\s[^<>]*)?>", joined):
        issues.append(
            f"{path} leaf text contains an HTML tag or code fence; author clean Slate text, not markup"
        )
    return issues


def _collect_text(content: Any) -> str:
    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                out.append(node["text"])
            walk(node.get("children"))
        elif isinstance(node, list):
            for n in node:
                walk(n)

    walk(content)
    return "\n".join(out)


def validate_manifest_content_shapes(manifest: dict, content_field: str = "content") -> list[str]:
    """Validate the `content` field of every item in a manifest's items list."""
    issues: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    items = manifest.get("items")
    if items is None:
        items = (manifest.get("manifest") or {}).get("items") if isinstance(manifest.get("manifest"), dict) else None
    if not isinstance(items, list):
        return ["manifest has no `items` list to validate"]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"items[{i}] must be an object")
            continue
        if content_field not in item:
            # Not every item type carries a body; only validate when present.
            continue
        label = item.get("slug") or item.get("name") or item.get("title") or f"items[{i}]"
        issues.extend(validate_slate_content(item[content_field], path=f"{label}.{content_field}"))
    return issues


def build_report(manifest: dict, content_field: str = "content") -> dict:
    issues = validate_manifest_content_shapes(manifest, content_field)
    return {
        "kind": "allincms_slate_content_shape_validation",
        "contentField": content_field,
        "valid": not issues,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate manifest content fields are Slate node arrays.")
    parser.add_argument("manifest_json")
    parser.add_argument("--content-field", default="content")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.manifest_json, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report = build_report(manifest, args.content_field)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["valid"]:
        print("Slate content shape validation passed.")
    else:
        for issue in report["issues"]:
            print(f"  [slate] {issue}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
