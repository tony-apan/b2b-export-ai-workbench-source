#!/usr/bin/env python3
"""Validate an AllinCMS posts/products bulk upload manifest before live upload."""

from __future__ import annotations

import json
import re
import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse


VALID_TYPES = {"posts", "products"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_public_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("ERROR: manifest root must be a JSON object")
    return data


def validate_item(
    item: dict,
    index: int,
    content_type: str,
    seen_slugs: set[str],
    field_mapping: dict | None = None,
) -> list[str]:
    errors: list[str] = []
    label = f"items[{index}]"

    if not isinstance(item, dict):
        return [f"{label}: must be an object"]

    slug = item.get("slug")
    if not isinstance(slug, str) or not slug:
        errors.append(f"{label}.slug: required string")
    elif not SLUG_RE.match(slug):
        errors.append(f"{label}.slug: use lowercase kebab-case letters and digits only")
    elif slug in seen_slugs:
        errors.append(f"{label}.slug: duplicate slug '{slug}'")
    else:
        seen_slugs.add(slug)

    title = item.get("title") or item.get("name")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"{label}.title/name: required non-empty string")

    if content_type == "posts":
        excerpt = item.get("excerpt")
        if excerpt is not None and not isinstance(excerpt, str):
            errors.append(f"{label}.excerpt: must be a string when present")
        if "description" in item and "excerpt" not in item:
            errors.append(f"{label}.description: posts usually use excerpt; confirm description is a captured backend field")

    if content_type == "products":
        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{label}.description: required non-empty string for products")
        title_field = field_mapping.get("titleField") if isinstance(field_mapping, dict) else None
        if "title" in item and "name" not in item and title_field != "title":
            errors.append(f"{label}.title: products may require name instead of title; confirm title is a captured backend field")

    cover = item.get("coverImage") or item.get("media")
    if cover is not None:
        if not isinstance(cover, dict):
            errors.append(f"{label}.coverImage/media: must be an object when present")
        else:
            url = cover.get("url")
            if not isinstance(url, str) or not is_public_http_url(url):
                errors.append(f"{label}.coverImage/media.url: must be a public http(s) URL")
            alt = cover.get("alt")
            if alt is not None and not isinstance(alt, str):
                errors.append(f"{label}.coverImage/media.alt: must be a string when present")

    content = item.get("content")
    if content is None:
        errors.append(f"{label}.content: required")
    elif not isinstance(content, (str, list, dict)):
        errors.append(f"{label}.content: must be a string, list, or object")
    elif isinstance(content, str) and looks_like_rich_markdown(content):
        errors.append(f"{label}.content: raw Markdown/HTML-like rich text detected; convert to captured editor block schema before upload")

    for key in ("categories", "tags", "specs", "gallery", "variants", "categoryIds"):
        if key in item and not isinstance(item[key], list):
            errors.append(f"{label}.{key}: must be an array when present")

    for key in ("price", "sku", "attributes", "inventory", "operation", "sourceRef", "frontendUrl"):
        if key in item and item[key] is None:
            errors.append(f"{label}.{key}: must not be null when present")

    return errors


def looks_like_rich_markdown(value: str) -> bool:
    patterns = (
        r"\*\*[^*\n].{0,120}?\*\*",
        r"`[^`\n]{1,160}`",
        r"(?<!!)\[[^\]]+]\([^)]+\)",
        r"!\[[^\]]*]\([^)]+\)",
        r"(^|\n)\s*\|[^|\n]+\|[^|\n]*\n\s*\|[-: |]+\|",
        r"style=\{\{[^}]+}}",
        r"</?(?:u|span|div|table|tr|td|strong|code|br)\b[^>]*>",
    )
    return any(re.search(pattern, value, re.MULTILINE) for pattern in patterns)


def validate_manifest(data: dict, require_schema_verified: bool = False) -> list[str]:
    errors: list[str] = []

    content_type = data.get("contentType")
    if content_type not in VALID_TYPES:
        errors.append(
            f"contentType: must be one of {sorted(VALID_TYPES)}; "
            "media/themes/routes require a freshly captured schema-specific validator"
        )

    site_key = data.get("siteKey")
    if site_key is not None and not isinstance(site_key, str):
        errors.append("siteKey: must be a string when present")

    frontend_base = data.get("frontendBaseUrl")
    if frontend_base is not None:
        if not isinstance(frontend_base, str) or not is_public_http_url(frontend_base):
            errors.append("frontendBaseUrl: must be a public http(s) URL when present")

    field_mapping = data.get("fieldMapping")
    if field_mapping is not None and not isinstance(field_mapping, dict):
        errors.append("fieldMapping: must be an object when present")

    payload_template = data.get("payloadTemplate")
    if payload_template is not None and not isinstance(payload_template, dict):
        errors.append("payloadTemplate: must be an object when present")

    schema_verified = data.get("schemaVerified")
    if require_schema_verified:
        if schema_verified is not True:
            errors.append("schemaVerified: must be true before upload; capture the live save request for this content type first")
        if not isinstance(field_mapping, dict) or not field_mapping:
            errors.append("fieldMapping: required before upload when --require-schema-verified is used")
        if not isinstance(payload_template, dict) or not payload_template:
            errors.append("payloadTemplate: required before upload when --require-schema-verified is used")
    elif schema_verified is not None and not isinstance(schema_verified, bool):
        errors.append("schemaVerified: must be a boolean when present")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items: must be a non-empty array")
        return errors

    if content_type in VALID_TYPES:
        seen_slugs: set[str] = set()
        for index, item in enumerate(items):
            errors.extend(validate_item(item, index, content_type, seen_slugs, field_mapping))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an AllinCMS posts/products manifest before live upload.",
    )
    parser.add_argument("manifest", type=Path, help="Path to the manifest JSON file.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of human-readable status text.",
    )
    parser.add_argument(
        "--require-schema-verified",
        action="store_true",
        help=(
            "Require schemaVerified=true, fieldMapping, and payloadTemplate from a "
            "validated current-site save capture."
        ),
    )
    args = parser.parse_args()

    manifest_path = args.manifest
    data = load_manifest(manifest_path)
    errors = validate_manifest(data, require_schema_verified=args.require_schema_verified)
    result = {
        "kind": "allincms_manifest_validation",
        "manifest": str(manifest_path),
        "valid": not errors,
        "requireSchemaVerified": args.require_schema_verified,
        "issues": errors,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if errors:
        print("Manifest validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Manifest validation passed.")
    if args.require_schema_verified:
        print("Schema gate passed. Still verify one sample in backend and frontend before batch upload.")
    else:
        print("Reminder: this only validates generic structure; still capture the live save request per content type.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
