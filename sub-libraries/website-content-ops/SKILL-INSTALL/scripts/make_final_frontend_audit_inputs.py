#!/usr/bin/env python3
"""Generate final frontend audit inputs from AllinCMS upload manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from make_launch_audit_inputs import build_url, normalize_base_url, parse_paths
from validate_manifest import SLUG_RE, validate_manifest


ROUTE_PREFIX_BY_CONTENT_TYPE = {
    "posts": "posts",
    "products": "products",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path, require_schema_verified: bool) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a JSON object")
    errors = validate_manifest(data, require_schema_verified=require_schema_verified)
    if errors:
        raise ValueError("manifest validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    return data


def progress_entries(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        raw_entries = data
    elif isinstance(data, dict):
        raw_entries = []
        for key in ("items", "entries", "progressLog", "results"):
            value = data.get(key)
            if isinstance(value, list):
                raw_entries = value
                break
    else:
        raw_entries = []
    entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    if len(entries) != len(raw_entries):
        raise ValueError("progress log entries must be objects")
    return entries


def item_slugs(manifest: dict[str, Any]) -> list[str]:
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest.items must be an array")
    slugs: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"manifest.items[{index}] must be an object")
        slug = item.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            raise ValueError(f"manifest.items[{index}].slug must be lowercase kebab-case")
        slugs.append(slug)
    return slugs


def validate_progress_complete(manifest: dict[str, Any], progress: list[dict[str, Any]]) -> list[str]:
    return validate_progress_complete_for_manifest(manifest, progress, allow_other_content_types=False)


def validate_progress_complete_for_manifest(
    manifest: dict[str, Any],
    progress: list[dict[str, Any]],
    *,
    allow_other_content_types: bool,
) -> list[str]:
    errors: list[str] = []
    content_type = str(manifest.get("contentType", ""))
    manifest_slugs = set(item_slugs(manifest))
    by_slug: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(progress):
        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug:
            errors.append(f"progress[{index}].slug is required")
            continue
        entry_type = entry.get("contentType")
        if allow_other_content_types and slug not in manifest_slugs and entry_type != content_type:
            continue
        if slug not in manifest_slugs:
            errors.append(f"progress[{index}].slug {slug} is not present in manifest")
            continue
        if slug in by_slug:
            errors.append(f"progress[{index}].slug duplicates {slug}")
            continue
        by_slug[slug] = entry

    for slug in manifest_slugs:
        entry = by_slug.get(slug)
        if entry is None:
            errors.append(f"progress missing manifest slug {slug}")
            continue
        entry_type = entry.get("contentType")
        if entry_type is not None and entry_type != content_type:
            errors.append(f"progress[{slug}].contentType must be {content_type}")
        if entry.get("saveStatus") != "ok":
            errors.append(f"progress[{slug}].saveStatus must be ok")
        if entry.get("publishStatus") != "ok":
            errors.append(f"progress[{slug}].publishStatus must be ok for final frontend audit")
        if entry.get("backendVerified") is not True:
            errors.append(f"progress[{slug}].backendVerified must be true")
        if entry.get("frontendVerified") is not True:
            errors.append(f"progress[{slug}].frontendVerified must be true")
        cover_ok = entry.get("coverVerified") is True or entry.get("coverOrMediaVerified") is True
        if not cover_ok:
            errors.append(f"progress[{slug}].coverVerified or coverOrMediaVerified must be true")
        entry_errors = entry.get("errors")
        if isinstance(entry_errors, list) and entry_errors:
            errors.append(f"progress[{slug}].errors must be empty")
    return errors


def detail_path(content_type: str, slug: str) -> str:
    prefix = ROUTE_PREFIX_BY_CONTENT_TYPE.get(content_type)
    if not prefix:
        raise ValueError("contentType must be posts or products")
    return f"/{prefix}/{slug}"


def build_inputs(
    manifest: dict[str, Any],
    frontend_base_url: str,
    static_paths: list[str],
) -> tuple[list[str], dict[str, int], dict[str, Any]]:
    return build_inputs_for_manifests([manifest], frontend_base_url, static_paths)


def manifest_frontend_base(manifest: dict[str, Any]) -> str:
    return str(manifest.get("frontendBaseUrl", "")).strip()


def resolve_frontend_base(manifests: list[dict[str, Any]], frontend_base_url: str) -> str:
    if frontend_base_url.strip():
        return frontend_base_url.strip()
    bases = {manifest_frontend_base(manifest) for manifest in manifests if manifest_frontend_base(manifest)}
    if len(bases) != 1:
        raise ValueError("frontend base URL is required and must be identical across manifests unless --frontend-base-url is supplied")
    return next(iter(bases))


def build_inputs_for_manifests(
    manifests: list[dict[str, Any]],
    frontend_base_url: str,
    static_paths: list[str],
) -> tuple[list[str], dict[str, int], dict[str, Any]]:
    if not manifests:
        raise ValueError("at least one manifest is required")
    content_types: list[str] = []
    detail_counts: dict[str, int] = {}
    detail_instances: list[str] = []
    base_url = normalize_base_url(frontend_base_url)
    statuses: dict[str, int] = {}

    for path in static_paths:
        statuses[build_url(base_url, path)] = 200
    route_patterns = list(static_paths)
    for manifest in manifests:
        content_type = str(manifest.get("contentType", ""))
        if content_type not in ROUTE_PREFIX_BY_CONTENT_TYPE:
            raise ValueError("contentType must be posts or products")
        if content_type in content_types:
            raise ValueError(f"duplicate manifest contentType {content_type}; merge same-type manifests before final audit input generation")
        content_types.append(content_type)
        slugs = item_slugs(manifest)
        detail_counts[content_type] = len(slugs)
        prefix = ROUTE_PREFIX_BY_CONTENT_TYPE[content_type]
        for index, slug in enumerate(slugs, start=1):
            statuses[build_url(base_url, detail_path(content_type, slug))] = 200
            detail_instances.append(f"{prefix}-detail-{index}")
        route_patterns.append(f"/{prefix}/{{slug}}")

    detail_count = sum(detail_counts.values())
    summary = {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "contentType": content_types[0] if len(content_types) == 1 else "mixed",
        "contentTypes": content_types,
        "manifestCount": len(manifests),
        "staticRouteCount": len(static_paths),
        "detailRouteCount": detail_count,
        "detailRouteCountByContentType": detail_counts,
        "detailRouteInstances": detail_instances,
        "routePatterns": route_patterns,
        "expectedStatus": 200,
        "warning": "Runtime audit input files may contain concrete slugs; do not copy them into skill references.",
    }
    return list(statuses.keys()), statuses, summary


def validate_progress_for_manifests(
    manifests: list[dict[str, Any]],
    progress_logs: list[Path],
) -> list[str]:
    if not progress_logs:
        return ["--progress-log is required when --require-progress-complete is used"]
    if len(progress_logs) == 1:
        progress = progress_entries(load_json(progress_logs[0]))
        allow_other = len(manifests) > 1
        errors: list[str] = []
        for manifest in manifests:
            errors.extend(
                validate_progress_complete_for_manifest(
                    manifest,
                    progress,
                    allow_other_content_types=allow_other,
                )
            )
        return errors
    if len(progress_logs) != len(manifests):
        return ["when multiple --progress-log values are supplied, count must be 1 or match --manifest count"]
    errors = []
    for manifest, progress_log in zip(manifests, progress_logs):
        progress = progress_entries(load_json(progress_log))
        errors.extend(validate_progress_complete_for_manifest(manifest, progress, allow_other_content_types=False))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final frontend audit URL/status files from one or more manifests.")
    parser.add_argument(
        "--manifest",
        required=True,
        action="append",
        help="Schema-verified posts/products manifest JSON; repeat for mixed products/posts final audits",
    )
    parser.add_argument("--frontend-base-url", default="", help="Override manifest.frontendBaseUrl")
    parser.add_argument("--static-paths", default="", help="Optional comma-separated static routes expected to return 200")
    parser.add_argument(
        "--progress-log",
        action="append",
        default=[],
        help="Optional batch progress log JSON; repeat to pair with repeated --manifest, or pass one combined log",
    )
    parser.add_argument("--require-schema-verified", action="store_true", help="Require manifest schemaVerified/payloadTemplate gate")
    parser.add_argument("--require-progress-complete", action="store_true", help="Require progress log to prove every manifest item succeeded")
    parser.add_argument("--urls-output", required=True, help="Output text file containing one URL per line")
    parser.add_argument("--statuses-output", required=True, help="Output JSON file mapping URL to expected status")
    parser.add_argument("--summary-output", default="", help="Optional redacted summary JSON path")
    args = parser.parse_args()

    try:
        manifests = [load_manifest(Path(path), args.require_schema_verified) for path in args.manifest]
        frontend_base_url = resolve_frontend_base(manifests, args.frontend_base_url)
        static_paths = parse_paths(args.static_paths, "static paths") if args.static_paths else []
        if args.require_progress_complete:
            progress_errors = validate_progress_for_manifests(manifests, [Path(path) for path in args.progress_log])
            if progress_errors:
                raise ValueError("progress completeness check failed:\n" + "\n".join(f"- {error}" for error in progress_errors))
        urls, statuses, summary = build_inputs_for_manifests(manifests, frontend_base_url, static_paths)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    urls_output = Path(args.urls_output)
    statuses_output = Path(args.statuses_output)
    urls_output.parent.mkdir(parents=True, exist_ok=True)
    statuses_output.parent.mkdir(parents=True, exist_ok=True)
    urls_output.write_text("\n".join(urls) + "\n", encoding="utf-8")
    write_json(statuses_output, statuses)
    if args.summary_output:
        write_json(Path(args.summary_output), summary)
    print(f"Wrote {urls_output}")
    print(f"Wrote {statuses_output}")
    if args.summary_output:
        print(f"Wrote {args.summary_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
