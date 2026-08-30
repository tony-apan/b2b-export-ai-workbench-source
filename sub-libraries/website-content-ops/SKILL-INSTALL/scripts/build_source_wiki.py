#!/usr/bin/env python3
"""Build a source wiki JSON from a source inventory and distilled extraction summary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from build_source_inventory import validate_inventory
from build_source_site_package import slugify
from validate_source_wiki import validate_source_wiki


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def inventory_input_files(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for entry in as_list(inventory.get("entries")):
        if not isinstance(entry, dict):
            continue
        item: dict[str, Any] = {
            "path": nonempty(entry.get("path")),
            "name": nonempty(entry.get("name")),
            "type": nonempty(entry.get("type")) or "unknown",
            "sourceRef": nonempty(entry.get("sourceRef")),
        }
        if isinstance(entry.get("sizeBytes"), int):
            item["sizeBytes"] = entry["sizeBytes"]
        if nonempty(entry.get("sha256")):
            item["sha256"] = nonempty(entry.get("sha256"))
        files.append(item)
    return files


def inventory_refs(inventory: dict[str, Any]) -> list[str]:
    refs = [entry.get("sourceRef") for entry in as_list(inventory.get("entries")) if isinstance(entry, dict)]
    return [ref for ref in refs if isinstance(ref, str) and ref]


def normalize_blocks(value: Any, fallback: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        result: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str) and item.strip():
                result.append({"type": "paragraph", "text": item.strip()})
        return result or [{"type": "paragraph", "text": fallback}]
    if isinstance(value, str) and value.strip():
        return [{"type": "paragraph", "text": value.strip()}]
    return [{"type": "paragraph", "text": fallback}]


def specs_list(value: Any) -> list[dict[str, str]]:
    if isinstance(value, dict):
        return [
            {"label": str(label).strip(), "value": str(item).strip()}
            for label, item in value.items()
            if str(label).strip() and str(item).strip()
        ]
    if isinstance(value, list):
        specs: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                label = nonempty(item.get("label")) or nonempty(item.get("name")) or nonempty(item.get("key"))
                spec_value = nonempty(item.get("value")) or nonempty(item.get("text"))
                if label and spec_value:
                    specs.append({"label": label, "value": spec_value})
            elif isinstance(item, str) and item.strip():
                specs.append({"label": "spec", "value": item.strip()})
        return specs
    return []


def categories_list(item: dict[str, Any]) -> list[Any]:
    categories = as_list(item.get("categories"))
    category = nonempty(item.get("category"))
    if category and category not in categories:
        categories.append(category)
    return categories


def content_from_summary(summary: str, additions: list[str], fallback: str) -> list[dict[str, Any]]:
    parts = [summary.strip()] if summary.strip() else [fallback]
    for addition in additions:
        cleaned = nonempty(addition)
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    text = " ".join(part for part in parts if part).strip()
    return [{"type": "paragraph", "text": text}]


def stable_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def unique_list(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        key = stable_key(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def string_value_quality(value: str) -> int:
    cleaned = value.strip().lower()
    if not cleaned:
        return 0
    if "requires review" in cleaned or cleaned.startswith("draft "):
        return 1
    return 2


def choose_text(existing: str, incoming: str) -> str:
    existing_quality = string_value_quality(existing)
    incoming_quality = string_value_quality(incoming)
    if incoming_quality > existing_quality:
        return incoming
    return existing or incoming


def block_text(block: dict[str, Any]) -> str:
    text = block.get("text")
    if isinstance(text, str):
        return text
    body = block.get("body")
    if isinstance(body, str):
        return body
    return ""


def content_quality(blocks: Any) -> tuple[int, int]:
    if not isinstance(blocks, list) or not blocks:
        return (0, 0)
    texts = [block_text(block) for block in blocks if isinstance(block, dict)]
    joined = " ".join(texts).strip().lower()
    if not joined:
        return (0, len(blocks))
    if "requires review" in joined and len(joined) < 180:
        return (1, len(joined))
    return (2, len(joined))


def merge_content_blocks(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_quality = content_quality(existing)
    incoming_quality = content_quality(incoming)
    if incoming_quality > existing_quality:
        base = incoming
        extra = existing
    else:
        base = existing
        extra = incoming
    merged = list(base)
    seen = {stable_key(item) for item in merged}
    for block in extra:
        key = stable_key(block)
        if key not in seen:
            seen.add(key)
            merged.append(block)
    return merged


def merge_specs(existing: list[dict[str, str]], incoming: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for spec in existing + incoming:
        label = nonempty(spec.get("label"))
        value = nonempty(spec.get("value"))
        if not label or not value:
            continue
        key = (label.lower(), value.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append({"label": label, "value": value})
    return merged


def merge_product(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    return {
        **existing,
        "name": choose_text(nonempty(existing.get("name")), nonempty(incoming.get("name"))),
        "description": choose_text(nonempty(existing.get("description")), nonempty(incoming.get("description"))),
        "content": merge_content_blocks(as_list(existing.get("content")), as_list(incoming.get("content"))),
        "specs": merge_specs(specs_list(existing.get("specs")), specs_list(incoming.get("specs"))),
        "categories": unique_list(as_list(existing.get("categories")) + as_list(incoming.get("categories"))),
        "tags": unique_list(as_list(existing.get("tags")) + as_list(incoming.get("tags"))),
        "mediaNeeds": unique_list(as_list(existing.get("mediaNeeds")) + as_list(incoming.get("mediaNeeds"))),
        "sourceRefs": unique_list(as_list(existing.get("sourceRefs")) + as_list(incoming.get("sourceRefs"))),
    }


def merge_post(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    return {
        **existing,
        "title": choose_text(nonempty(existing.get("title")), nonempty(incoming.get("title"))),
        "excerpt": choose_text(nonempty(existing.get("excerpt")), nonempty(incoming.get("excerpt"))),
        "content": merge_content_blocks(as_list(existing.get("content")), as_list(incoming.get("content"))),
        "categories": unique_list(as_list(existing.get("categories")) + as_list(incoming.get("categories"))),
        "tags": unique_list(as_list(existing.get("tags")) + as_list(incoming.get("tags"))),
        "mediaNeeds": unique_list(as_list(existing.get("mediaNeeds")) + as_list(incoming.get("mediaNeeds"))),
        "sourceRefs": unique_list(as_list(existing.get("sourceRefs")) + as_list(incoming.get("sourceRefs"))),
    }


def merge_by_slug(items: list[dict[str, Any]], merger: Any) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index_by_slug: dict[str, int] = {}
    for item in items:
        slug = nonempty(item.get("slug"))
        if not slug:
            merged.append(item)
            continue
        if slug in index_by_slug:
            existing_index = index_by_slug[slug]
            merged[existing_index] = merger(merged[existing_index], item)
            continue
        index_by_slug[slug] = len(merged)
        merged.append(item)
    return merged


def normalize_pages(summary: dict[str, Any], default_refs: list[str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(summary.get("pages"))):
        if not isinstance(item, dict):
            continue
        title = nonempty(item.get("title")) or f"Page {index + 1}"
        path = nonempty(item.get("path")) or ("/" if title.lower() == "home" else "/" + slugify(title))
        refs = [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()] or default_refs
        sections = as_list(item.get("sections")) or [{"heading": title, "body": nonempty(item.get("body")) or "Draft page copy requires review."}]
        pages.append(
            {
                "title": title,
                "path": path if path.startswith("/") else "/" + path,
                "purpose": nonempty(item.get("purpose")) or "content_page",
                "sections": sections,
                "mediaNeeds": as_list(item.get("mediaNeeds")),
                "sourceRefs": refs,
            }
        )
    return pages


def normalize_products(summary: dict[str, Any], default_refs: list[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(summary.get("products"))):
        if not isinstance(item, dict):
            continue
        name = nonempty(item.get("name")) or nonempty(item.get("title")) or f"Product {index + 1}"
        refs = [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()] or default_refs
        description = nonempty(item.get("description")) or nonempty(item.get("summary"))
        specs = specs_list(item.get("specs"))
        categories = categories_list(item)
        spec_sentence = " ".join(f"{spec['label']}: {spec['value']}." for spec in specs[:8])
        category_sentence = f"Category: {', '.join(str(category) for category in categories)}." if categories else ""
        products.append(
            {
                "name": name,
                "slug": nonempty(item.get("slug")) or slugify(name),
                "description": description or "Draft product description requires review.",
                "content": normalize_blocks(
                    item.get("content"),
                    content_from_summary(
                        description,
                        [spec_sentence, category_sentence],
                        "Draft product detail requires review.",
                    )[0]["text"],
                ),
                "specs": specs,
                "categories": categories,
                "tags": as_list(item.get("tags")),
                "mediaNeeds": as_list(item.get("mediaNeeds")),
                "sourceRefs": refs,
            }
        )
    return merge_by_slug(products, merge_product)


def normalize_posts(summary: dict[str, Any], default_refs: list[str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(summary.get("posts"))):
        if not isinstance(item, dict):
            continue
        title = nonempty(item.get("title")) or f"Article {index + 1}"
        refs = [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()] or default_refs
        excerpt = nonempty(item.get("excerpt")) or nonempty(item.get("description")) or nonempty(item.get("summary"))
        posts.append(
            {
                "title": title,
                "slug": nonempty(item.get("slug")) or slugify(title),
                "excerpt": excerpt or "Draft article excerpt requires review.",
                "content": normalize_blocks(
                    item.get("content"),
                    content_from_summary(
                        excerpt,
                        [f"This article supports buyers researching {title.lower()} with source-backed selection context and practical next-step questions."],
                        "Draft article body requires review.",
                    )[0]["text"],
                ),
                "categories": as_list(item.get("categories")),
                "tags": as_list(item.get("tags")),
                "mediaNeeds": as_list(item.get("mediaNeeds")),
                "sourceRefs": refs,
            }
        )
    return merge_by_slug(posts, merge_post)


def object_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def default_home_page(site_name: str, default_refs: list[str]) -> dict[str, Any]:
    return {
        "title": "Home",
        "path": "/",
        "purpose": "homepage",
        "sections": [
            {
                "heading": site_name,
                "body": "Draft homepage copy was generated from source inventory and must be reviewed against extracted source notes.",
            }
        ],
        "sourceRefs": default_refs,
    }


def build_source_wiki(args: argparse.Namespace) -> dict[str, Any]:
    inventory = load_json(args.inventory, "inventory")
    inv_errors = validate_inventory(inventory)
    if inv_errors:
        raise SystemExit("ERROR: invalid inventory:\n- " + "\n- ".join(inv_errors))
    summary = load_json(args.extraction_summary, "extraction summary") if args.extraction_summary else {}
    default_refs = inventory_refs(inventory)
    if not default_refs:
        raise SystemExit("ERROR: inventory has no source refs")
    site = summary.get("site") if isinstance(summary.get("site"), dict) else {}
    site_name = nonempty(site.get("siteName")) or nonempty(args.site_name) or "Draft AllinCMS Site"
    wiki_refs = [item for item in as_list(summary.get("wikiRefs")) if isinstance(item, str) and item.strip()]
    if args.wiki_ref:
        wiki_refs.extend(args.wiki_ref)
    if not wiki_refs:
        wiki_refs = [str(Path(args.output).with_name("source-wiki.json"))]
    pages = normalize_pages(summary, default_refs)
    if not pages:
        pages = [default_home_page(site_name, default_refs)]
    wiki = {
        "kind": "allincms_source_wiki",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceSet": {
            "inputFiles": inventory_input_files(inventory),
            "rawExtractionRefs": [item for item in as_list(summary.get("rawExtractionRefs")) if isinstance(item, str) and item.strip()],
            "wikiRefs": wiki_refs,
        },
        "site": {
            "siteName": site_name,
            "siteDescription": nonempty(site.get("siteDescription")) or nonempty(site.get("description")) or nonempty(args.site_description) or "Draft site description requires user review.",
            "language": nonempty(site.get("language")) or args.language,
            "industry": nonempty(site.get("industry")) or args.industry,
        },
        "pages": pages,
        "products": normalize_products(summary, default_refs),
        "posts": normalize_posts(summary, default_refs),
        "forms": as_list(summary.get("forms")),
        "media": as_list(summary.get("media")),
        "siteInfo": object_or_empty(summary.get("siteInfo")),
        "navigation": object_or_empty(summary.get("navigation")),
        "taxonomyPlan": object_or_empty(summary.get("taxonomyPlan") or summary.get("taxonomy")),
        "mediaPolicy": object_or_empty(summary.get("mediaPolicy")),
        "contactFormPolicy": object_or_empty(summary.get("contactFormPolicy")),
        "contentGoals": object_or_empty(summary.get("contentGoals")),
        "openQuestions": as_list(summary.get("openQuestions")),
        "adversarialNotes": [
            "This wiki is source-backed planning, not user confirmation.",
            "Missing extraction summary fields use review-required placeholders and should be improved before package confirmation.",
            "Site-info, navigation, media policy, and contact/form policy remain review surfaces and must still pass package confirmation.",
            "Remote AllinCMS mutations remain blocked until source package confirmation and current-site schema capture.",
        ],
    }
    if not wiki["products"]:
        wiki["products"] = [
            {
                "name": "Draft Product",
                "slug": "draft-product",
                "description": "Draft product placeholder requires source extraction.",
                "content": [{"type": "paragraph", "text": "Draft product content requires source extraction."}],
                "sourceRefs": default_refs,
            }
        ]
        wiki["openQuestions"].append("Replace Draft Product with source-extracted product data before user confirmation.")
    if not wiki["posts"]:
        wiki["posts"] = [
            {
                "title": "Draft Article",
                "slug": "draft-article",
                "excerpt": "Draft article placeholder requires source extraction.",
                "content": [{"type": "paragraph", "text": "Draft article content requires source extraction."}],
                "sourceRefs": default_refs,
            }
        ]
        wiki["openQuestions"].append("Replace Draft Article with source-extracted article data before user confirmation.")
    return wiki


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS source wiki JSON from inventory and extraction summary.")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--extraction-summary", help="Optional distilled extraction summary JSON")
    parser.add_argument("--site-name", default="")
    parser.add_argument("--site-description", default="")
    parser.add_argument("--language", default="en")
    parser.add_argument("--industry", default="unspecified")
    parser.add_argument("--wiki-ref", action="append", default=[], help="Optional wiki artifact path/reference; repeatable")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    wiki = build_source_wiki(args)
    inventory = load_json(args.inventory, "inventory")
    issues = validate_source_wiki(wiki, inventory)
    if issues:
        print("Source wiki build produced invalid output:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(wiki, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source wiki: {output}")
    print(f"counts=pages:{len(wiki['pages'])},products:{len(wiki['products'])},posts:{len(wiki['posts'])}")
    if args.json:
        print(json.dumps(wiki, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
