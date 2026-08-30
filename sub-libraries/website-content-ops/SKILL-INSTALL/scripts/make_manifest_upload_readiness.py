#!/usr/bin/env python3
"""Build an upload-readiness report for one or more AllinCMS manifests."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from validate_manifest import load_manifest, validate_manifest


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def item_has_taxonomy(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    for key in ("categories", "tags", "categoryIds"):
        value = item.get(key)
        if isinstance(value, list) and value:
            return True
    return False


def manifest_requires_taxonomy(manifest: dict[str, Any]) -> bool:
    items = manifest.get("items")
    if not isinstance(items, list):
        return False
    return any(item_has_taxonomy(item) for item in items)


def taxonomy_validation_ok(validation: Any, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    if not manifest_requires_taxonomy(manifest):
        return True, []
    if not isinstance(validation, dict):
        return False, ["taxonomy_validation_missing"]
    issues: list[str] = []
    if validation.get("valid") is not True:
        issues.append("taxonomy_validation_not_valid")
    if validation.get("taxonomyPrerequisiteSatisfied") is not True:
        issues.append("taxonomy_prerequisite_not_satisfied")
    validation_site = validation.get("siteKey")
    manifest_site = manifest.get("siteKey")
    if isinstance(manifest_site, str) and manifest_site and validation_site != manifest_site:
        issues.append("taxonomy_validation_site_mismatch")
    raw_issues = validation.get("issues")
    if isinstance(raw_issues, list) and raw_issues:
        issues.append("taxonomy_validation_has_issues")
    return not issues, issues


def item_count(manifest: dict[str, Any]) -> int:
    items = manifest.get("items")
    return len(items) if isinstance(items, list) else 0


def report_for_manifest(path: Path, taxonomy_validation: Any = None) -> dict[str, Any]:
    manifest = load_manifest(path)
    generic_errors = validate_manifest(manifest, require_schema_verified=False)
    schema_errors = validate_manifest(manifest, require_schema_verified=True)
    taxonomy_required = manifest_requires_taxonomy(manifest)
    taxonomy_ok, taxonomy_errors = taxonomy_validation_ok(taxonomy_validation, manifest)
    generic_ok = not generic_errors
    schema_ok = not schema_errors
    status = "ready_for_sample_upload" if generic_ok and schema_ok and taxonomy_ok else "blocked"
    blockers: list[str] = []
    if generic_errors:
        blockers.append("generic_manifest_validation_failed")
    if schema_errors:
        blockers.append("schema_gate_not_passed")
    if taxonomy_errors:
        blockers.append("taxonomy_gate_not_passed")
    return {
        "path": str(path),
        "contentType": manifest.get("contentType"),
        "siteKey": manifest.get("siteKey"),
        "frontendBaseUrl": manifest.get("frontendBaseUrl"),
        "schemaVerified": manifest.get("schemaVerified"),
        "itemCount": item_count(manifest),
        "taxonomyRequired": taxonomy_required,
        "genericValidation": {"ok": generic_ok, "errors": generic_errors},
        "schemaGate": {"ok": schema_ok, "errors": schema_errors},
        "taxonomyGate": {
            "ok": taxonomy_ok,
            "required": taxonomy_required,
            "errors": taxonomy_errors,
            "validationKind": taxonomy_validation.get("kind") if isinstance(taxonomy_validation, dict) else "",
        },
        "status": status,
        "blockers": blockers,
        "nextAction": (
            "upload one sample and verify backend/frontend"
            if status == "ready_for_sample_upload"
            else "capture a live save request/schema and, when categories/tags/categoryIds exist, validate taxonomy create/map evidence"
        ),
    }


def build_report(paths: list[Path], taxonomy_validation: Any = None) -> dict[str, Any]:
    manifests = [report_for_manifest(path, taxonomy_validation) for path in paths]
    ready = [item for item in manifests if item["status"] == "ready_for_sample_upload"]
    blocked = [item for item in manifests if item["status"] == "blocked"]
    content_types = sorted({str(item.get("contentType")) for item in manifests if item.get("contentType")})
    return {
        "kind": "allincms_manifest_upload_readiness_report",
        "generatedAt": now_iso(),
        "remoteMutationsPerformed": False,
        "contentTypes": content_types,
        "manifestCount": len(manifests),
        "readyCount": len(ready),
        "blockedCount": len(blocked),
        "overallStatus": "ready_for_sample_upload" if manifests and not blocked else "blocked",
        "manifests": manifests,
        "rule": (
            "Generic manifest validation proves local source hygiene only. "
            "Live upload requires schemaGate.ok=true for each content type, and taxonomyGate.ok=true "
            "when any item contains categories, tags, or categoryIds."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS manifest upload readiness report.")
    parser.add_argument("manifest_json", nargs="+", help="One or more posts/products manifest JSON files")
    parser.add_argument("--taxonomy-validation", default="", help="Optional validate_taxonomy_execution_evidence.py report JSON")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    try:
        taxonomy_validation: Any = None
        if args.taxonomy_validation:
            taxonomy_validation = json.loads(Path(args.taxonomy_validation).read_text(encoding="utf-8"))
        report = build_report([Path(path) for path in args.manifest_json], taxonomy_validation)
    except FileNotFoundError as exc:
        print(f"taxonomy validation not found: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"invalid taxonomy validation JSON: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"overallStatus={report['overallStatus']} ready={report['readyCount']} blocked={report['blockedCount']}")
    if args.fail_on_blocked and report["overallStatus"] == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
