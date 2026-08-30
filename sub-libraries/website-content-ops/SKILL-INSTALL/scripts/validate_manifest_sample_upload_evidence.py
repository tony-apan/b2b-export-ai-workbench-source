#!/usr/bin/env python3
"""Validate one uploaded/published manifest sample before batch upload."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

from validate_manifest import load_manifest, validate_manifest


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"cookie\s*[:=]", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
ROUTE_PREFIX = {"products": "products", "posts": "posts"}


def load_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} root must be an object")
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


def manifest_slugs(manifest: dict[str, Any]) -> set[str]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return set()
    return {item["slug"] for item in items if isinstance(item, dict) and isinstance(item.get("slug"), str)}


def manifest_item_by_slug(manifest: dict[str, Any], slug: str) -> dict[str, Any]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and item.get("slug") == slug:
            return item
    return {}


def item_requires_media(item: dict[str, Any]) -> bool:
    for key in ("coverImage", "media"):
        value = item.get(key)
        if isinstance(value, dict) and value.get("url"):
            return True
    gallery = item.get("gallery")
    if isinstance(gallery, list) and bool(gallery):
        return True
    media_needs = item.get("mediaNeeds")
    return isinstance(media_needs, list) and bool(media_needs)


def expected_backend_prefix(site_key: str, content_type: str) -> str:
    return f"https://workspace.laicms.com/{site_key}/{content_type}"


def expected_frontend_url(site_key: str, content_type: str, slug: str) -> str:
    return f"https://{site_key}.web.allincms.com/{ROUTE_PREFIX[content_type]}/{slug}"


def validate_sample_evidence(data: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_manifest_sample_upload_evidence":
        issues.append("kind must be allincms_manifest_sample_upload_evidence")
    manifest_errors = validate_manifest(manifest, require_schema_verified=True)
    issues.extend(f"manifest: {error}" for error in manifest_errors)

    site_key = manifest.get("siteKey")
    content_type = manifest.get("contentType")
    if not isinstance(site_key, str) or not site_key:
        issues.append("manifest.siteKey must be present")
        site_key = ""
    if content_type not in ROUTE_PREFIX:
        issues.append("manifest.contentType must be posts or products")
        content_type = ""

    if data.get("siteKey") != site_key:
        issues.append("siteKey must match manifest.siteKey")
    if data.get("contentType") != content_type:
        issues.append("contentType must match manifest.contentType")
    if data.get("manifestPath") and not isinstance(data.get("manifestPath"), str):
        issues.append("manifestPath must be a string when present")

    slug = data.get("sampleSlug")
    if not isinstance(slug, str) or not slug:
        issues.append("sampleSlug is required")
    elif slug not in manifest_slugs(manifest):
        issues.append("sampleSlug must exist in manifest.items")

    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")
    if data.get("schemaGatePass") is not True:
        issues.append("schemaGatePass must be true")
    if data.get("saveStatus") != "ok":
        issues.append("saveStatus must be ok")
    if data.get("publishStatus") != "ok":
        issues.append("publishStatus must be ok")
    for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified", "stopConditionMet"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    sample_item = manifest_item_by_slug(manifest, slug) if isinstance(slug, str) else {}
    if data.get("coverOrMediaVerified") is not True and item_requires_media(sample_item):
        issues.append("coverOrMediaVerified must be true because the manifest sample item has coverImage/media/gallery/mediaNeeds")
    elif data.get("coverOrMediaVerified") is not True:
        note = data.get("coverOrMediaNote")
        if not isinstance(note, str) or len(note.strip()) < 8:
            issues.append("coverOrMediaVerified must be true or coverOrMediaNote must explain the accepted absence")

    backend_url = data.get("backendUrl")
    if isinstance(backend_url, str) and site_key and content_type:
        if not backend_url.startswith(expected_backend_prefix(site_key, content_type)):
            issues.append("backendUrl must belong to the manifest site/content type")
    else:
        issues.append("backendUrl is required")

    frontend_url = data.get("frontendUrl")
    if isinstance(frontend_url, str) and site_key and content_type and isinstance(slug, str):
        if frontend_url != expected_frontend_url(site_key, content_type, slug):
            issues.append("frontendUrl must match manifest site/content type and sampleSlug")
    else:
        issues.append("frontendUrl is required")

    target = data.get("target")
    if isinstance(target, str) and site_key and content_type:
        if not target.startswith(expected_backend_prefix(site_key, content_type)):
            issues.append("target must belong to the manifest site/content type")
    else:
        issues.append("target is required")

    render_audit = data.get("renderAudit")
    if not isinstance(render_audit, str) or not render_audit.strip():
        issues.append("renderAudit must be a non-empty redacted string")
    blocking = data.get("blockingIssues")
    if not isinstance(blocking, list):
        issues.append("blockingIssues must be an array")
    elif blocking:
        issues.append("blockingIssues must be empty")

    all_text = "\n".join(walk_strings(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def progress_entry(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": data["sampleSlug"],
        "contentType": data["contentType"],
        "backendUrl": data["backendUrl"],
        "frontendUrl": data["frontendUrl"],
        "saveStatus": data["saveStatus"],
        "publishStatus": data["publishStatus"],
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": data.get("coverOrMediaVerified") is True,
        "coverOrMediaNote": data.get("coverOrMediaNote", ""),
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS manifest sample upload evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--progress-entry-output", help="Write one progress-log entry for the sample")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json), "evidence JSON")
        manifest = load_manifest(Path(args.manifest))
        issues = validate_sample_evidence(evidence, manifest)
        report = {
            "kind": "allincms_manifest_sample_upload_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "manifest": args.manifest,
            "siteKey": evidence.get("siteKey"),
            "contentType": evidence.get("contentType"),
            "sampleSlug": evidence.get("sampleSlug"),
            "issues": issues,
            "batchPrerequisiteSatisfied": not issues,
        }
        if args.progress_entry_output and not issues:
            output = Path(args.progress_entry_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(progress_entry(evidence), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (SystemExit, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
