#!/usr/bin/env python3
"""Simulate AllinCMS manifest normalization and schema gate behavior locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from make_source_input_requirements import build_report as build_source_input_requirements
from validate_manifest import validate_manifest


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_draft_manifest(site_key: str, content_type: str, frontend_base_url: str = "") -> dict[str, Any]:
    if content_type == "posts":
        return {
            "siteKey": site_key,
            "contentType": "posts",
            "frontendBaseUrl": frontend_base_url or f"https://{site_key}.web.allincms.com",
            "schemaVerified": False,
            "fieldMapping": {
                "titleField": "title",
                "summaryField": "excerpt",
                "bodyField": "content",
            },
            "items": [
                {
                    "operation": "create",
                    "title": "Codex Probe - Delete Me Sample Post",
                    "slug": "codex-probe-delete-me-sample-post",
                    "excerpt": "Temporary local validation excerpt.",
                    "coverImage": {
                        "url": "https://example.com/image.jpg",
                        "alt": "Temporary post validation image",
                    },
                    "categories": [],
                    "tags": [],
                    "content": [
                        {
                            "type": "paragraph",
                            "children": [{"text": "Temporary local validation content."}],
                        }
                    ],
                }
            ],
        }
    if content_type == "products":
        return {
            "siteKey": site_key,
            "contentType": "products",
            "frontendBaseUrl": frontend_base_url or f"https://{site_key}.web.allincms.com",
            "schemaVerified": False,
            "fieldMapping": {
                "titleField": "name",
                "descriptionField": "description",
                "bodyField": "content",
            },
            "items": [
                {
                    "operation": "create",
                    "name": "Codex Probe - Delete Me Sample Product",
                    "slug": "codex-probe-delete-me-sample-product",
                    "description": "Temporary local validation product.",
                    "media": {
                        "url": "https://example.com/image.jpg",
                        "alt": "Temporary product validation image",
                    },
                    "categories": [],
                    "tags": [],
                    "specs": [],
                    "content": [
                        {
                            "type": "paragraph",
                            "children": [{"text": "Temporary local validation content."}],
                        }
                    ],
                }
            ],
        }
    raise ValueError("content type must be posts or products for manifest rehearsal")


def summarize_gate(errors: list[str]) -> dict[str, Any]:
    return {
        "passed": not errors,
        "errorCount": len(errors),
        "errors": errors,
    }


def build_simulated_gap_ledger(site_key: str, content_type: str) -> dict[str, Any]:
    if content_type == "products":
        entries = [
            {
                "recordedAt": "2026-06-30T00:00:00+00:00",
                "contentType": "products",
                "field": "specifications",
                "target": "products.specifications",
                "classification": ["recommended", "source-derived", "blocked-until-schema-captured"],
                "sourceHint": "PDF/catalog specification table such as wattage, dimensions, certifications, and model attributes.",
                "generationRule": "Generate structured spec rows only after the current-site specification schema is captured.",
                "currentEvidence": "simulated-only",
                "decisionNeeded": "needs-schema-capture",
                "evidencePointer": "~/allincms-projects/allincms-simulated-product-field-gap.json",
                "operatorNote": "Local rehearsal gap; no LAICMS browser state was mutated.",
            }
        ]
    elif content_type == "posts":
        entries = [
            {
                "recordedAt": "2026-06-30T00:00:00+00:00",
                "contentType": "posts",
                "field": "rich body blocks",
                "target": "posts.content",
                "classification": ["required", "source-derived", "blocked-until-schema-captured"],
                "sourceHint": "PDF/article source sections with headings, paragraphs, lists, tables, and links.",
                "generationRule": "Convert source text into the captured posts editor block schema; do not upload raw Markdown.",
                "currentEvidence": "simulated-only",
                "decisionNeeded": "needs-schema-capture",
                "evidencePointer": "~/allincms-projects/allincms-simulated-post-field-gap.json",
                "operatorNote": "Local rehearsal gap; no LAICMS browser state was mutated.",
            }
        ]
    else:
        entries = []

    return {
        "kind": "allincms_source_input_gap_ledger",
        "generatedAt": "2026-06-30T00:00:00+00:00",
        "updatedAt": "2026-06-30T00:00:00+00:00",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": site_key,
        "entries": entries,
        "summary": {
            "entryCount": len(entries),
            "byContentType": {content_type: len(entries)} if entries else {},
            "byDecisionNeeded": {"needs-schema-capture": len(entries)} if entries else {},
            "blockedFields": [f"{entry['contentType']}.{entry['field']}" for entry in entries],
            "userInputFields": [],
        },
    }


def run_rehearsal(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = Path(args.output_dir)
    manifest = build_draft_manifest(args.site_key, args.content_type, args.frontend_base_url)
    draft_errors = validate_manifest(manifest, require_schema_verified=False)
    schema_errors = validate_manifest(manifest, require_schema_verified=True)
    if draft_errors:
        raise ValueError("draft manifest validation failed:\n" + "\n".join(f"- {error}" for error in draft_errors))
    if not schema_errors:
        raise ValueError("schema gate unexpectedly passed without a captured payload template")
    if not any("schemaVerified" in error for error in schema_errors):
        raise ValueError("schema gate failure did not mention schemaVerified")
    if not any("payloadTemplate" in error for error in schema_errors):
        raise ValueError("schema gate failure did not mention payloadTemplate")

    manifest_path = output_dir / "draft-manifest.json"
    gap_ledger_path = output_dir / "source-input-gap-ledger.json"
    source_requirements_path = output_dir / "source-input-requirements.json"
    summary_path = output_dir / "manifest-rehearsal-summary.json"
    write_json(manifest_path, manifest)
    write_json(gap_ledger_path, build_simulated_gap_ledger(args.site_key, args.content_type))
    source_requirements_args = argparse.Namespace(
        site_key=args.site_key,
        content_types=args.content_type,
        source_types="pdf_catalog,product_datasheet,website_copy,image_urls,spreadsheet,plain_brief",
        manifest=[str(manifest_path)],
        save_capture_evidence=[],
        media_evidence=None,
        readiness_evidence=None,
        gap_ledger=[str(gap_ledger_path)],
    )
    source_requirements = build_source_input_requirements(source_requirements_args)
    write_json(source_requirements_path, source_requirements)
    summary = {
        "kind": "allincms_manifest_rehearsal_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": args.site_key,
        "contentType": args.content_type,
        "draftManifestPath": str(manifest_path),
        "sourceInputGapLedgerPath": str(gap_ledger_path),
        "sourceInputRequirementsPath": str(source_requirements_path),
        "sourceInputRequirements": {
            "overallStatus": source_requirements.get("overallStatus"),
            "blockedUntilCount": len(source_requirements.get("blockedUntil", [])),
            "contentTypes": sorted(source_requirements.get("contentTypes", {}).keys()),
            "operationGapCount": source_requirements.get("operationGaps", {}).get("entryCount"),
            "operationGapBlockedFields": source_requirements.get("operationGaps", {}).get("blockedFields", []),
        },
        "draftValidation": summarize_gate(draft_errors),
        "schemaGate": {
            **summarize_gate(schema_errors),
            "expectedFailure": True,
            "reason": "No current-site save request has been captured, so schemaVerified remains false and payloadTemplate is absent.",
        },
        "nextRequiredProof": [
            "Capture the exact save request for this content type on the current site.",
            "Record fieldMapping and payloadTemplate from the captured request.",
            "Set schemaVerified true only after backend persistence and frontend sample verification.",
        ],
        "warning": "This is local-only manifest rehearsal. Do not upload from this draft manifest.",
    }
    write_json(summary_path, summary)
    return {
        "draftManifest": manifest_path,
        "sourceInputGapLedger": gap_ledger_path,
        "sourceInputRequirements": source_requirements_path,
        "summary": summary_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only AllinCMS manifest rehearsal.")
    parser.add_argument("--site-key", default="simsite01")
    parser.add_argument("--content-type", choices=["posts", "products"], default="products")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    try:
        paths = run_rehearsal(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for label, path in paths.items():
        print(f"{label}: {path}")
    print("Manifest rehearsal passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
