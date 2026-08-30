#!/usr/bin/env python3
"""Validate redacted batch upload/publish evidence before final audit or cleanup."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from make_final_frontend_audit_inputs import progress_entries, validate_progress_complete
from validate_manifest import load_manifest, validate_manifest


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"cookie\s*[:=]", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
ROUTE_PREFIX = {"posts": "posts", "products": "products"}


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


def load_json_any(path: Path, label: str = "JSON") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc}") from None


def walk_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(walk_string_values(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(walk_string_values(item))
    return strings


def base_site_key_and_content_type(base: dict[str, Any]) -> tuple[str, str]:
    site_identity = base.get("siteIdentity")
    content_inspection = base.get("contentInspection")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("base run evidence must include siteIdentity.siteKey")
    if not isinstance(content_inspection, dict) or not isinstance(content_inspection.get("contentType"), str):
        raise ValueError("base run evidence must include contentInspection.contentType")
    return site_identity["siteKey"], content_inspection["contentType"]


def expected_backend_prefix(site_key: str, content_type: str) -> str:
    return f"https://workspace.laicms.com/{site_key}/{content_type}"


def expected_frontend_prefix(site_key: str, content_type: str) -> str:
    return f"https://{site_key}.web.allincms.com/{ROUTE_PREFIX[content_type]}/"


def manifest_slugs(manifest: dict[str, Any]) -> list[str]:
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest.items must be an array")
    slugs: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("slug"), str):
            raise ValueError(f"manifest.items[{index}].slug is required")
        slugs.append(item["slug"])
    return slugs


def manifest_items_by_slug(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("slug"), str):
            result[item["slug"]] = item
    return result


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


def validate_frontend_audit_reports(
    reports: Any,
    *,
    content_type: str,
    expected_count: int,
    require_body_tags: bool,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(reports, list):
        return ["frontend audit report must be the JSON array from audit_frontend_rendering.py --json --redact"]

    expected_route = f"/{ROUTE_PREFIX[content_type]}/{{slug}}"
    detail_reports = [report for report in reports if isinstance(report, dict) and report.get("url") == expected_route]
    if len(detail_reports) < expected_count:
        issues.append(f"frontend audit must include at least {expected_count} redacted {expected_route} detail reports")

    for index, report in enumerate(detail_reports):
        if report.get("status") != 200 or report.get("expectedStatus") != 200:
            issues.append(f"frontend audit detail report {index} must have status 200 and expectedStatus 200")
        report_issues = report.get("issues")
        if not isinstance(report_issues, list):
            issues.append(f"frontend audit detail report {index}.issues must be an array")
        elif report_issues:
            issues.append(f"frontend audit detail report {index}.issues must be empty")
        tag_counts = report.get("tagCounts")
        if not isinstance(tag_counts, dict):
            issues.append(f"frontend audit detail report {index}.tagCounts must be present")
        elif require_body_tags:
            rich_count = sum(int(tag_counts.get(tag, 0) or 0) for tag in ("h1", "h2", "h3", "li", "table", "strong", "b", "code", "img", "a"))
            if rich_count <= 0:
                issues.append(f"frontend audit detail report {index} must include structural tag counts")
    return issues


def validate_batch_evidence(
    data: dict[str, Any],
    *,
    manifest: dict[str, Any],
    base_run_evidence: dict[str, Any] | None = None,
    audit_reports: Any | None = None,
) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_batch_upload_publish_evidence":
        issues.append("kind must be allincms_batch_upload_publish_evidence")
    for key in ("schemaGatePass", "sampleVerificationPass", "progressLogComplete", "frontendDetailAuditPass", "stopConditionMet"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")
    action = data.get("action")
    if action not in {"batch_upload", "batch_publish"}:
        issues.append("action must be batch_upload or batch_publish")

    manifest_errors = validate_manifest(manifest, require_schema_verified=True)
    if manifest_errors:
        issues.extend(f"manifest: {error}" for error in manifest_errors)
    manifest_site_key = manifest.get("siteKey")
    manifest_content_type = manifest.get("contentType")
    if manifest_content_type not in ROUTE_PREFIX:
        issues.append("manifest.contentType must be posts or products")

    site_key = data.get("siteKey")
    content_type = data.get("contentType")
    if site_key != manifest_site_key:
        issues.append("siteKey must match manifest.siteKey")
    if content_type != manifest_content_type:
        issues.append("contentType must match manifest.contentType")

    if base_run_evidence is not None:
        try:
            base_site_key, base_content_type = base_site_key_and_content_type(base_run_evidence)
        except ValueError as exc:
            issues.append(str(exc))
        else:
            if site_key != base_site_key:
                issues.append("siteKey must match base run evidence")
            if content_type != base_content_type:
                issues.append("contentType must match base run evidence")
            request_capture = base_run_evidence.get("requestCapture")
            if not isinstance(request_capture, dict) or request_capture.get("persistedVerified") is not True:
                issues.append("base run evidence must include persisted requestCapture")
            sample = base_run_evidence.get("sampleVerification")
            if not isinstance(sample, dict):
                issues.append("base run evidence must include sampleVerification")
            else:
                for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "coverOrMediaVerified", "bodyVerified"):
                    if sample.get(key) is not True:
                        issues.append(f"base sampleVerification.{key} must be true")

    target = data.get("target")
    if not isinstance(target, str):
        issues.append("target must be a concrete workspace URL")
    elif isinstance(site_key, str) and isinstance(content_type, str):
        expected = expected_backend_prefix(site_key, content_type)
        if not target.startswith(expected):
            issues.append(f"target must be under {expected}")

    progress = progress_entries(data.get("progressLog"))
    if not progress:
        issues.append("progressLog must contain entries")
    else:
        progress_errors = validate_progress_complete(manifest, progress)
        issues.extend(f"progressLog: {error}" for error in progress_errors)
        manifest_by_slug = manifest_items_by_slug(manifest)
        if isinstance(site_key, str) and isinstance(content_type, str) and content_type in ROUTE_PREFIX:
            backend_prefix = expected_backend_prefix(site_key, content_type)
            frontend_prefix = expected_frontend_prefix(site_key, content_type)
            for entry in progress:
                slug = entry.get("slug")
                backend_url = entry.get("backendUrl")
                frontend_url = entry.get("frontendUrl")
                if not isinstance(backend_url, str) or not backend_url.startswith(backend_prefix):
                    issues.append(f"progress[{slug}].backendUrl must be under {backend_prefix}")
                if not isinstance(frontend_url, str) or not frontend_url.startswith(frontend_prefix):
                    issues.append(f"progress[{slug}].frontendUrl must be under {frontend_prefix}")
                if entry.get("bodyVerified") is not True:
                    issues.append(f"progress[{slug}].bodyVerified must be true")
                if isinstance(slug, str) and item_requires_media(manifest_by_slug.get(slug, {})):
                    if entry.get("coverOrMediaVerified") is not True and entry.get("coverVerified") is not True:
                        issues.append(f"progress[{slug}].coverOrMediaVerified must be true because manifest item has media")

    frontend_audit = data.get("frontendDetailAudit")
    if not isinstance(frontend_audit, dict):
        issues.append("frontendDetailAudit must be an object")
    else:
        for key in ("checked", "markdownResidueChecked", "structuredRichTextChecked"):
            if frontend_audit.get(key) is not True:
                issues.append(f"frontendDetailAudit.{key} must be true")
        blocking = frontend_audit.get("blockingIssues")
        if not isinstance(blocking, list):
            issues.append("frontendDetailAudit.blockingIssues must be an array")
        elif blocking:
            issues.append("frontendDetailAudit.blockingIssues must be empty")
        count = frontend_audit.get("detailRouteCount")
        try:
            expected_count = len(manifest_slugs(manifest))
        except ValueError as exc:
            issues.append(str(exc))
            expected_count = 0
        if count != expected_count:
            issues.append("frontendDetailAudit.detailRouteCount must match manifest item count")

    if audit_reports is not None and isinstance(manifest_content_type, str):
        issues.extend(
            validate_frontend_audit_reports(
                audit_reports,
                content_type=manifest_content_type,
                expected_count=len(manifest_slugs(manifest)),
                require_body_tags=True,
            )
        )

    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def build_report(
    evidence_path: str,
    data: dict[str, Any],
    manifest_path: str,
    manifest: dict[str, Any],
    base_path: str,
    audit_path: str,
    issues: list[str],
) -> dict[str, Any]:
    slugs: list[str] = []
    try:
        slugs = manifest_slugs(manifest)
    except ValueError:
        pass
    return {
        "kind": "allincms_batch_upload_publish_evidence_validation",
        "valid": not issues,
        "evidence": evidence_path,
        "manifest": manifest_path,
        "baseRunEvidence": base_path,
        "frontendAuditReport": audit_path,
        "siteKey": data.get("siteKey"),
        "contentType": data.get("contentType"),
        "action": data.get("action"),
        "manifestItemCount": len(slugs),
        "progressCount": len(progress_entries(data.get("progressLog"))) if isinstance(data.get("progressLog"), (dict, list)) else 0,
        "issues": issues,
        "mergeReady": not issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted AllinCMS batch upload/publish evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--manifest", required=True, help="Schema-verified posts/products manifest JSON")
    parser.add_argument("--base-run-evidence", help="Optional run evidence JSON to bind siteKey/contentType/sample proof")
    parser.add_argument("--frontend-audit-report", help="Optional redacted frontend audit JSON array")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json), "evidence JSON")
        manifest = load_manifest(Path(args.manifest))
        base = load_json(Path(args.base_run_evidence), "base run evidence JSON") if args.base_run_evidence else None
        audit_reports = load_json_any(Path(args.frontend_audit_report), "frontend audit report JSON") if args.frontend_audit_report else None
        issues = validate_batch_evidence(
            evidence,
            manifest=manifest,
            base_run_evidence=base,
            audit_reports=audit_reports,
        )
        report = build_report(
            args.evidence_json,
            evidence,
            args.manifest,
            manifest,
            args.base_run_evidence or "",
            args.frontend_audit_report or "",
            issues,
        )
    except (ValueError, SystemExit) as exc:
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
