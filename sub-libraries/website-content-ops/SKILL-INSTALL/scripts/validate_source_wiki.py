#!/usr/bin/env python3
"""Validate distilled source wiki JSON before building an AllinCMS source-site package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

from validate_manifest import SLUG_RE, looks_like_rich_markdown


SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cookie|authorization|bearer|next-action|next-router-state-tree)\b", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE),
)


def load_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(walk_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(walk_strings(item))
        return out
    return []


def inventory_refs(inventory: dict[str, Any] | None) -> set[str]:
    if not inventory:
        return set()
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        return set()
    return {entry["sourceRef"] for entry in entries if isinstance(entry, dict) and isinstance(entry.get("sourceRef"), str)}


def inventory_entries_by_ref(inventory: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not inventory:
        return {}
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        return {}
    return {
        entry["sourceRef"]: entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("sourceRef"), str)
    }


def wiki_source_refs(data: dict[str, Any]) -> set[str]:
    source_set = data.get("sourceSet")
    refs: set[str] = set()
    if isinstance(source_set, dict):
        for item in source_set.get("inputFiles", []):
            if isinstance(item, dict) and isinstance(item.get("sourceRef"), str):
                refs.add(item["sourceRef"])
    return refs


def wiki_input_files(data: dict[str, Any]) -> list[dict[str, Any]]:
    source_set = data.get("sourceSet")
    if not isinstance(source_set, dict):
        return []
    return [item for item in source_set.get("inputFiles", []) if isinstance(item, dict)]


def item_refs(item: dict[str, Any]) -> list[str]:
    refs = item.get("sourceRefs")
    return [ref for ref in refs if isinstance(ref, str) and ref.strip()] if isinstance(refs, list) else []


def source_ref_shape_errors(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{label} must be an array when present"]
    if not all(isinstance(ref, str) and ref.strip() for ref in value):
        return [f"{label} must contain non-empty source reference strings"]
    return []


def validate_page_sections(page: dict[str, Any], label: str) -> list[str]:
    issues: list[str] = []
    sections = page.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append(f"{label}.sections must be non-empty")
        return issues
    page_has_refs = bool(item_refs(page))
    for section_index, section in enumerate(sections):
        section_label = f"{label}.sections[{section_index}]"
        if not isinstance(section, dict):
            issues.append(f"{section_label} must be an object")
            continue
        heading = section.get("heading")
        body = section.get("body")
        if not isinstance(heading, str) or not heading.strip():
            issues.append(f"{section_label}.heading is required")
        if not isinstance(body, str) or not body.strip():
            issues.append(f"{section_label}.body is required")
        issues.extend(source_ref_shape_errors(section.get("sourceRefs"), f"{section_label}.sourceRefs"))
        if not page_has_refs and not item_refs(section):
            issues.append(f"{section_label}.sourceRefs must be non-empty when {label}.sourceRefs is empty")
    return issues


def validate_media_needs(item: dict[str, Any], label: str) -> list[str]:
    needs = item.get("mediaNeeds")
    if needs is None:
        return []
    if not isinstance(needs, list):
        return [f"{label}.mediaNeeds must be an array when present"]
    issues: list[str] = []
    for index, need in enumerate(needs):
        if not isinstance(need, dict):
            issues.append(f"{label}.mediaNeeds[{index}] must be an object")
    return issues


def block_text(block: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("text", "body", "description", "excerpt"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return " ".join(parts).strip()


def validate_content_blocks(blocks: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(blocks, list) or not blocks:
        return [f"{label} must be a non-empty array"]
    for index, block in enumerate(blocks):
        block_label = f"{label}[{index}]"
        if not isinstance(block, dict):
            issues.append(f"{block_label} must be an object")
            continue
        if not block_text(block):
            issues.append(f"{block_label}.text or body is required")
        issues.extend(source_ref_shape_errors(block.get("sourceRefs"), f"{block_label}.sourceRefs"))
    return issues


def validate_pages(pages: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(pages, list) or not pages:
        return ["pages must be a non-empty array"]
    seen_paths: set[str] = set()
    for index, page in enumerate(pages):
        label = f"pages[{index}]"
        if not isinstance(page, dict):
            issues.append(f"{label} must be an object")
            continue
        if not isinstance(page.get("title"), str) or not page["title"].strip():
            issues.append(f"{label}.title is required")
        path = page.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(f"{label}.path must be a leading-slash path")
        elif path in seen_paths:
            issues.append(f"{label}.path duplicates {path}")
        else:
            seen_paths.add(path)
        issues.extend(validate_page_sections(page, label))
        if not item_refs(page):
            issues.append(f"{label}.sourceRefs must be non-empty")
        issues.extend(validate_media_needs(page, label))
    return issues


def validate_products(products: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(products, list) or not products:
        return ["products must be a non-empty array"]
    seen_slugs: set[str] = set()
    for index, item in enumerate(products):
        label = f"products[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        name = item.get("name") or item.get("title")
        slug = item.get("slug")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"{label}.name is required")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            issues.append(f"{label}.slug must be lowercase kebab-case")
        elif slug in seen_slugs:
            issues.append(f"{label}.slug duplicates {slug}")
        else:
            seen_slugs.add(slug)
        if not isinstance(item.get("description"), str) or not item["description"].strip():
            issues.append(f"{label}.description is required")
        issues.extend(validate_content_blocks(item.get("content"), f"{label}.content"))
        if not item_refs(item):
            issues.append(f"{label}.sourceRefs must be non-empty")
        issues.extend(validate_media_needs(item, label))
    return issues


def validate_posts(posts: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(posts, list) or not posts:
        return ["posts must be a non-empty array"]
    seen_slugs: set[str] = set()
    for index, item in enumerate(posts):
        label = f"posts[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        slug = item.get("slug")
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            issues.append(f"{label}.title is required")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            issues.append(f"{label}.slug must be lowercase kebab-case")
        elif slug in seen_slugs:
            issues.append(f"{label}.slug duplicates {slug}")
        else:
            seen_slugs.add(slug)
        if not isinstance(item.get("excerpt"), str) or not item["excerpt"].strip():
            issues.append(f"{label}.excerpt is required")
        issues.extend(validate_content_blocks(item.get("content"), f"{label}.content"))
        if not item_refs(item):
            issues.append(f"{label}.sourceRefs must be non-empty")
        issues.extend(validate_media_needs(item, label))
    return issues


def validate_optional_object(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{label} must be an object when present"]
    return []


def validate_navigation(navigation: Any) -> list[str]:
    issues = validate_optional_object(navigation, "navigation")
    if issues or not isinstance(navigation, dict) or not navigation:
        return issues
    items = navigation.get("items")
    if items is None:
        return issues
    if not isinstance(items, list):
        return ["navigation.items must be an array when present"]
    seen_paths: set[str] = set()
    for index, item in enumerate(items):
        label = f"navigation.items[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            issues.append(f"{label}.label is required")
        path = item.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(f"{label}.path must be a leading-slash path")
        elif path in seen_paths:
            issues.append(f"{label}.path duplicates {path}")
        else:
            seen_paths.add(path)
    return issues


def validate_source_wiki(data: dict[str, Any], inventory: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_source_wiki":
        issues.append("kind must be allincms_source_wiki")
    source_set = data.get("sourceSet")
    if not isinstance(source_set, dict):
        issues.append("sourceSet must be an object")
    else:
        if not isinstance(source_set.get("inputFiles"), list) or not source_set["inputFiles"]:
            issues.append("sourceSet.inputFiles must be non-empty")
        if not isinstance(source_set.get("wikiRefs"), list) or not source_set["wikiRefs"]:
            issues.append("sourceSet.wikiRefs must be non-empty")
    site = data.get("site")
    if not isinstance(site, dict):
        issues.append("site must be an object")
    else:
        for key in ("siteName", "siteDescription", "language", "industry"):
            if not isinstance(site.get(key), str) or not site[key].strip():
                issues.append(f"site.{key} is required")
    issues.extend(validate_pages(data.get("pages")))
    issues.extend(validate_products(data.get("products")))
    issues.extend(validate_posts(data.get("posts")))
    issues.extend(validate_optional_object(data.get("siteInfo"), "siteInfo"))
    issues.extend(validate_navigation(data.get("navigation")))
    issues.extend(validate_optional_object(data.get("taxonomyPlan"), "taxonomyPlan"))
    issues.extend(validate_optional_object(data.get("mediaPolicy"), "mediaPolicy"))
    issues.extend(validate_optional_object(data.get("contactFormPolicy"), "contactFormPolicy"))
    if inventory:
        inv_refs = inventory_refs(inventory)
        refs = wiki_source_refs(data)
        if not refs.issubset(inv_refs):
            issues.append("sourceSet.inputFiles contains sourceRefs not present in inventory: " + ", ".join(sorted(refs - inv_refs)))
        inv_by_ref = inventory_entries_by_ref(inventory)
        for index, source_file in enumerate(wiki_input_files(data)):
            ref = source_file.get("sourceRef")
            if not isinstance(ref, str) or ref not in inv_by_ref:
                continue
            inventory_entry = inv_by_ref[ref]
            expected_sha = inventory_entry.get("sha256")
            actual_sha = source_file.get("sha256")
            if not isinstance(actual_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", actual_sha):
                issues.append(f"sourceSet.inputFiles[{index}].sha256 must preserve the inventory sha256 for {ref}")
            elif actual_sha != expected_sha:
                issues.append(f"sourceSet.inputFiles[{index}].sha256 does not match inventory for {ref}")
            expected_size = inventory_entry.get("sizeBytes")
            actual_size = source_file.get("sizeBytes")
            if isinstance(expected_size, int):
                if not isinstance(actual_size, int):
                    issues.append(f"sourceSet.inputFiles[{index}].sizeBytes must preserve the inventory size for {ref}")
                elif actual_size != expected_size:
                    issues.append(f"sourceSet.inputFiles[{index}].sizeBytes does not match inventory for {ref}")
        used_refs: set[str] = set()
        for section in ("pages", "products", "posts"):
            for item in data.get(section, []):
                if isinstance(item, dict):
                    used_refs.update(item_refs(item))
                    if section == "pages":
                        for page_section in item.get("sections", []):
                            if isinstance(page_section, dict):
                                used_refs.update(item_refs(page_section))
                    if section in {"products", "posts"}:
                        for block in item.get("content", []):
                            if isinstance(block, dict):
                                used_refs.update(item_refs(block))
        unknown_used = used_refs - inv_refs
        if unknown_used:
            issues.append("content uses sourceRefs not present in inventory: " + ", ".join(sorted(unknown_used)))
    for text in walk_strings(data):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                issues.append("source wiki contains sensitive credential/header/email/raw-id text")
                return issues
        if looks_like_rich_markdown(text):
            issues.append("source wiki contains raw Markdown/HTML-like rich text; convert to structured blocks or plain text before package build")
            return issues
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source wiki JSON.")
    parser.add_argument("source_wiki")
    parser.add_argument("--inventory", help="Optional allincms_source_inventory JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    wiki = load_json(Path(args.source_wiki), "source wiki")
    inventory = load_json(Path(args.inventory), "inventory") if args.inventory else None
    issues = validate_source_wiki(wiki, inventory)
    report = {
        "kind": "allincms_source_wiki_validation",
        "sourceWiki": args.source_wiki,
        "inventory": args.inventory,
        "valid": not issues,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        if not args.json:
            print("Source wiki validation failed:")
            for issue in issues:
                print(f"- {issue}")
        return 1
    if not args.json:
        print("Source wiki validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
