#!/usr/bin/env python3
"""Apply verified AllinCMS save-capture evidence to a draft posts/products manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from validate_manifest import load_manifest, validate_manifest
from validate_probe_save_capture_evidence import (
    base_site_key_and_content_type,
    load_json,
    validate_capture_evidence,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def frontend_base_for_site(site_key: str) -> str:
    return f"https://{site_key}.web.allincms.com"


def require_matching_scope(
    manifest: dict[str, Any],
    capture: dict[str, Any],
    *,
    base_run_evidence: dict[str, Any] | None = None,
    site_key_override: str = "",
    frontend_base_override: str = "",
) -> tuple[str, str, str]:
    content_type = manifest.get("contentType")
    capture_type = capture.get("contentType")
    if content_type != capture_type:
        raise ValueError(f"manifest.contentType {content_type!r} does not match capture.contentType {capture_type!r}")
    if content_type not in {"products", "posts"}:
        raise ValueError("only posts/products manifests can be schema-verified by this helper")

    site_key = site_key_override.strip()
    if base_run_evidence is not None:
        base_site_key, base_content_type = base_site_key_and_content_type(base_run_evidence)
        if base_content_type != content_type:
            raise ValueError("base run evidence contentType must match manifest contentType")
        if site_key and site_key != base_site_key:
            raise ValueError("site-key override must match base run evidence siteKey")
        site_key = base_site_key

    manifest_site_key = manifest.get("siteKey")
    if not site_key and isinstance(manifest_site_key, str) and manifest_site_key and not manifest_site_key.startswith("{"):
        site_key = manifest_site_key
    if not site_key:
        raise ValueError("siteKey is required; pass --site-key or --base-run-evidence after site creation")
    if isinstance(manifest_site_key, str) and manifest_site_key and not manifest_site_key.startswith("{") and manifest_site_key != site_key:
        raise ValueError("manifest.siteKey must match the captured current site")

    frontend_base = frontend_base_override.strip().rstrip("/")
    if not frontend_base:
        manifest_frontend = manifest.get("frontendBaseUrl")
        if isinstance(manifest_frontend, str) and manifest_frontend and "{siteKey}" not in manifest_frontend:
            frontend_base = manifest_frontend.rstrip("/")
    if not frontend_base:
        frontend_base = frontend_base_for_site(site_key)

    return site_key, content_type, frontend_base


def build_schema_verified_manifest(
    *,
    manifest: dict[str, Any],
    capture: dict[str, Any],
    capture_path: str,
    base_run_evidence: dict[str, Any] | None = None,
    base_run_evidence_path: str = "",
    site_key_override: str = "",
    frontend_base_override: str = "",
) -> dict[str, Any]:
    capture_issues = validate_capture_evidence(capture, base_run_evidence)
    if capture_issues:
        raise ValueError("save capture evidence is not valid:\n- " + "\n- ".join(capture_issues))

    generic_errors = validate_manifest(manifest, require_schema_verified=False)
    if generic_errors:
        raise ValueError("draft manifest failed generic validation:\n- " + "\n- ".join(generic_errors))

    site_key, content_type, frontend_base = require_matching_scope(
        manifest,
        capture,
        base_run_evidence=base_run_evidence,
        site_key_override=site_key_override,
        frontend_base_override=frontend_base_override,
    )
    upgraded = dict(manifest)
    upgraded["siteKey"] = site_key
    upgraded["contentType"] = content_type
    upgraded["frontendBaseUrl"] = frontend_base
    upgraded["schemaVerified"] = True
    upgraded["fieldMapping"] = capture["fieldMapping"]
    upgraded["payloadTemplate"] = capture["payloadTemplate"]
    for source_context_key in (
        "sourcePackageSha256",
        "sourceReviewPacketSha256",
        "contentGoalCoverage",
        "contentCounts",
        "contentQualityReview",
        "wikiReview",
    ):
        if isinstance(manifest.get(source_context_key), dict) and manifest[source_context_key]:
            upgraded[source_context_key] = manifest[source_context_key]
        elif isinstance(manifest.get(source_context_key), str) and manifest[source_context_key]:
            upgraded[source_context_key] = manifest[source_context_key]
    if isinstance(manifest.get("confirmationDecisionMatrix"), list) and manifest["confirmationDecisionMatrix"]:
        upgraded["confirmationDecisionMatrix"] = manifest["confirmationDecisionMatrix"]
    upgraded["schemaCaptureEvidence"] = {
        "kind": capture.get("kind"),
        "path": capture_path,
        "baseRunEvidence": base_run_evidence_path,
        "target": capture.get("target"),
        "requestUrl": capture.get("requestCapture", {}).get("url") if isinstance(capture.get("requestCapture"), dict) else "",
        "method": capture.get("requestCapture", {}).get("method") if isinstance(capture.get("requestCapture"), dict) else "",
        "capturedAt": now_iso(),
        "backendPersisted": capture.get("backendPersisted") is True,
        "publishBehavior": capture.get("requestCapture", {}).get("publishBehavior") if isinstance(capture.get("requestCapture"), dict) else "",
        "warning": "Schema verification proves current-site save shape only; sample publish/frontend verification is still required before batch upload.",
    }
    schema_errors = validate_manifest(upgraded, require_schema_verified=True)
    if schema_errors:
        raise ValueError("schema-verified manifest failed upload gate:\n- " + "\n- ".join(schema_errors))
    return upgraded


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply verified save capture evidence to a draft AllinCMS manifest.")
    parser.add_argument("--manifest", required=True, help="Draft posts/products manifest JSON")
    parser.add_argument("--save-capture-evidence", required=True, help="Validated allincms_probe_save_capture_evidence JSON")
    parser.add_argument("--base-run-evidence", default="", help="Optional run evidence JSON to bind siteKey/contentType")
    parser.add_argument("--site-key", default="", help="Required when manifest still has a siteKey placeholder and no base run evidence is supplied")
    parser.add_argument("--frontend-base-url", default="", help="Optional frontend base URL override")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        manifest = load_manifest(Path(args.manifest))
        capture = load_json(Path(args.save_capture_evidence))
        base = load_json(Path(args.base_run_evidence)) if args.base_run_evidence else None
        upgraded = build_schema_verified_manifest(
            manifest=manifest,
            capture=capture,
            capture_path=args.save_capture_evidence,
            base_run_evidence=base,
            base_run_evidence_path=args.base_run_evidence,
            site_key_override=args.site_key,
            frontend_base_override=args.frontend_base_url,
        )
    except (SystemExit, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(upgraded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote schema-verified manifest: {output}")
    print(f"contentType={upgraded['contentType']} siteKey={upgraded['siteKey']} schemaVerified=true")
    if args.json:
        print(json.dumps(upgraded, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
