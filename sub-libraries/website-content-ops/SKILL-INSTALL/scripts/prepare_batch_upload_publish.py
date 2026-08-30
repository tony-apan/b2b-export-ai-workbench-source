#!/usr/bin/env python3
"""Prepare batch upload/publish artifacts after one manifest sample passes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from build_batch_upload_publish_runbook import build_runbook as build_batch_runbook
from build_batch_upload_publish_runbook import validate_runbook as validate_batch_runbook
from content_goal_coverage_utils import (
    matching_created_site_submitted_values,
    matching_confirmation_decision_matrix,
    matching_content_counts,
    matching_content_goal_overages,
    matching_coverage,
    matching_quality_review,
    matching_source_identity,
    matching_wiki_review,
)
from make_manifest_upload_readiness import manifest_requires_taxonomy, taxonomy_validation_ok
from prepare_batch_upload_publish_evidence_bundle import build_bundle as build_batch_evidence_bundle
from prepare_batch_upload_publish_evidence_bundle import validate_bundle as validate_batch_evidence_bundle
from validate_manifest import load_manifest, validate_manifest
from validate_manifest_sample_upload_evidence import progress_entry, validate_sample_evidence


CONTENT_TYPES = {"products", "posts"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def unique_paths(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for group in groups:
        for item in group:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            paths.append(value)
    return paths


def evidence_content_type(path: str) -> str:
    data = load_json(Path(path), "existing sample evidence")
    return str(data.get("contentType", "")).strip()


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def artifact_paths(output_dir: Path, content_type: str) -> dict[str, Path]:
    return {
        "sample_validation": output_dir / f"{content_type}-sample-validation.json",
        "sample_progress_entry": output_dir / f"{content_type}-sample-progress-entry.json",
        "batch_runbook": output_dir / f"{content_type}-batch-upload-publish-runbook.json",
        "batch_evidence_bundle_dir": output_dir / f"{content_type}-batch-upload-publish-evidence-bundle",
        "batch_evidence_bundle": output_dir / f"{content_type}-batch-upload-publish-evidence-bundle" / "evidence-bundle.json",
        "batch_progress_seed": output_dir / f"{content_type}-batch-progress-seed.json",
        "summary": output_dir / f"{content_type}-batch-upload-publish-preparation-summary.json",
    }


def backend_target(manifest: dict[str, Any], override: str = "") -> str:
    if override:
        return override.rstrip("/")
    site_key = str(manifest.get("siteKey", "")).strip()
    content_type = str(manifest.get("contentType", "")).strip()
    if not site_key or site_key.startswith("{"):
        raise SystemExit("ERROR: schema-verified manifest must have concrete siteKey for batch runbook")
    if content_type not in CONTENT_TYPES:
        raise SystemExit("ERROR: contentType must be products or posts")
    return f"https://workspace.laicms.com/{site_key}/{content_type}"


def manifest_slugs(manifest: dict[str, Any]) -> list[str]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return []
    return [item["slug"] for item in items if isinstance(item, dict) and isinstance(item.get("slug"), str)]


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


def manifest_items_by_slug(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return {}
    return {item["slug"]: item for item in items if isinstance(item, dict) and isinstance(item.get("slug"), str)}


def progress_seed(manifest: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    sample_entry = progress_entry(sample)
    sample_slug = sample_entry["slug"]
    item_by_slug = manifest_items_by_slug(manifest)
    rows: list[dict[str, Any]] = []
    for slug in manifest_slugs(manifest):
        media_required = item_requires_media(item_by_slug.get(slug, {}))
        if slug == sample_slug:
            rows.append({**sample_entry, "mediaRequired": media_required, "source": "validated_sample_evidence"})
        else:
            rows.append(
                {
                    "slug": slug,
                    "contentType": manifest.get("contentType"),
                    "backendUrl": "",
                    "frontendUrl": "",
                    "saveStatus": "pending",
                    "publishStatus": "pending",
                    "backendVerified": False,
                    "frontendVerified": False,
                    "titleOrNameVerified": False,
                    "bodyVerified": False,
                    "coverOrMediaVerified": False,
                    "coverOrMediaNote": "",
                    "mediaRequired": media_required,
                    "errors": [],
                    "source": "manifest_pending_batch_stage",
                }
            )
    return {
        "kind": "allincms_batch_progress_seed",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": manifest.get("siteKey"),
        "contentType": manifest.get("contentType"),
        "manifestItemCount": len(rows),
        "sampleSlug": sample_slug,
        "rows": rows,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    run_evidence_path = Path(args.run_evidence)
    manifest_path = Path(args.manifest)
    sample_evidence_path = Path(args.sample_evidence)

    run_evidence = load_json(run_evidence_path, "run evidence")
    manifest = load_manifest(manifest_path)
    sample_evidence = load_json(sample_evidence_path, "sample evidence")
    existing_sample_paths = unique_paths(getattr(args, "existing_sample_evidence", []))
    merged_sample_paths = unique_paths(existing_sample_paths, [str(sample_evidence_path)])
    sample_content_types = sorted(
        {
            content_type
            for content_type in [evidence_content_type(path) for path in merged_sample_paths]
            if content_type
        }
    )
    source_coverage, source_coverage_issues = matching_coverage(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_coverage_issues:
        raise SystemExit("ERROR: source content goal coverage invalid:\n- " + "\n- ".join(source_coverage_issues))
    source_quality, source_quality_issues = matching_quality_review(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_quality_issues:
        raise SystemExit("ERROR: source content quality review invalid:\n- " + "\n- ".join(source_quality_issues))
    source_overages, source_overage_issues = matching_content_goal_overages(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_overage_issues:
        raise SystemExit("ERROR: source content goal overages invalid:\n- " + "\n- ".join(source_overage_issues))
    source_wiki_review, source_wiki_review_issues = matching_wiki_review(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_wiki_review_issues:
        raise SystemExit("ERROR: source wiki review invalid:\n- " + "\n- ".join(source_wiki_review_issues))
    source_decision_matrix, source_decision_matrix_issues = matching_confirmation_decision_matrix(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_decision_matrix_issues:
        raise SystemExit("ERROR: source confirmation decision matrix invalid:\n- " + "\n- ".join(source_decision_matrix_issues))
    source_counts, source_counts_issues = matching_content_counts(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ]
    )
    if source_counts_issues:
        raise SystemExit("ERROR: source content counts invalid:\n- " + "\n- ".join(source_counts_issues))
    source_identity, source_identity_issues = matching_source_identity(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if source_identity_issues:
        raise SystemExit("ERROR: source identity hashes invalid:\n- " + "\n- ".join(source_identity_issues))
    created_site_submitted_values, submitted_values_issues = matching_created_site_submitted_values(
        [
            ("run evidence", run_evidence),
            ("manifest", manifest),
            ("sample evidence", sample_evidence),
        ],
        require_when_present=False,
    )
    if submitted_values_issues:
        raise SystemExit("ERROR: created-site submitted values invalid:\n- " + "\n- ".join(submitted_values_issues))
    taxonomy_validation_path = getattr(args, "taxonomy_validation", "")
    taxonomy_validation = load_json(Path(taxonomy_validation_path), "taxonomy validation") if taxonomy_validation_path else None
    content_type = str(manifest.get("contentType", ""))
    if content_type not in CONTENT_TYPES:
        raise SystemExit("ERROR: manifest.contentType must be products or posts")
    paths = artifact_paths(output_dir, content_type)

    manifest_errors = validate_manifest(manifest, require_schema_verified=True)
    if manifest_errors:
        raise SystemExit("ERROR: manifest is not schema-verified:\n- " + "\n- ".join(manifest_errors))

    taxonomy_required = manifest_requires_taxonomy(manifest)
    taxonomy_ok, taxonomy_issues = taxonomy_validation_ok(taxonomy_validation, manifest)
    if taxonomy_issues:
        raise SystemExit("ERROR: taxonomy gate does not unlock batch preparation:\n- " + "\n- ".join(taxonomy_issues))

    sample_issues = validate_sample_evidence(sample_evidence, manifest)
    sample_validation = {
        "kind": "allincms_manifest_sample_upload_evidence_validation",
        "valid": not sample_issues,
        "evidence": str(sample_evidence_path),
        "manifest": str(manifest_path),
        "siteKey": sample_evidence.get("siteKey"),
        "contentType": sample_evidence.get("contentType"),
        "sampleSlug": sample_evidence.get("sampleSlug"),
        "issues": sample_issues,
        "batchPrerequisiteSatisfied": not sample_issues,
    }
    write_json(paths["sample_validation"], sample_validation)
    if sample_issues:
        raise SystemExit("ERROR: sample evidence does not unlock batch preparation:\n- " + "\n- ".join(sample_issues))

    write_json(paths["sample_progress_entry"], progress_entry(sample_evidence))
    seed = progress_seed(manifest, sample_evidence)
    write_json(paths["batch_progress_seed"], seed)

    target = backend_target(manifest, args.target)
    authorization_output = args.authorization_output or str(output_dir / f"{content_type}-batch-authorization.json")
    target_identifier = args.target_identifier or f"{content_type} manifest batch"
    batch_runbook = build_batch_runbook(
        run_evidence=run_evidence,
        run_evidence_path=str(run_evidence_path),
        manifest=manifest,
        manifest_path=str(manifest_path),
        sample_evidence=sample_evidence,
        sample_evidence_path=str(sample_evidence_path),
        authorization_output=authorization_output,
        target=target,
        target_identifier=target_identifier,
    )
    runbook_issues = validate_batch_runbook(batch_runbook)
    if runbook_issues:
        raise SystemExit("ERROR: generated batch runbook invalid:\n- " + "\n- ".join(runbook_issues))
    write_json(paths["batch_runbook"], batch_runbook)
    batch_evidence_bundle = build_batch_evidence_bundle(
        runbook=batch_runbook,
        runbook_path=str(paths["batch_runbook"]),
        output_dir=paths["batch_evidence_bundle_dir"],
    )
    batch_evidence_bundle_issues = validate_batch_evidence_bundle(batch_evidence_bundle)
    if batch_evidence_bundle_issues:
        raise SystemExit(
            "ERROR: generated batch evidence bundle invalid:\n- "
            + "\n- ".join(batch_evidence_bundle_issues)
        )
    write_json(paths["batch_evidence_bundle"], batch_evidence_bundle)

    summary = {
        "kind": "allincms_batch_upload_publish_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentType": content_type,
        "siteKey": manifest.get("siteKey"),
        "target": target,
        "manifestItemCount": len(manifest_slugs(manifest)),
        "sampleSlug": sample_evidence.get("sampleSlug"),
        "sampleEvidence": str(sample_evidence_path),
        "existingSampleEvidence": existing_sample_paths,
        "mergedSampleEvidence": merged_sample_paths,
        "sampleEvidenceContentTypes": sample_content_types,
        "contentGoalCoverage": source_coverage or {},
        "contentCounts": source_counts or {},
        "contentQualityReview": source_quality or {},
        "contentGoalOverages": source_overages or {},
        "wikiReview": source_wiki_review or {},
        "confirmationDecisionMatrix": source_decision_matrix or [],
        **({"createdSiteSubmittedValues": created_site_submitted_values} if created_site_submitted_values else {}),
        **(source_identity or {}),
        "artifacts": {
            "sampleValidation": str(paths["sample_validation"]),
            "sampleProgressEntry": str(paths["sample_progress_entry"]),
            "batchProgressSeed": str(paths["batch_progress_seed"]),
            "batchRunbook": str(paths["batch_runbook"]),
            "batchEvidenceBundle": str(paths["batch_evidence_bundle"]),
        },
        "validation": {
            "manifestErrors": manifest_errors,
            "taxonomyRequired": taxonomy_required,
            "taxonomyIssues": taxonomy_issues,
            "taxonomyValidation": taxonomy_validation_path,
            "sampleEvidenceIssues": sample_issues,
            "batchRunbookIssues": runbook_issues,
            "batchEvidenceBundleIssues": batch_evidence_bundle_issues,
        },
        "readyForBrowserStage": "ready_to_request_batch_upload_authorization",
        "nextAction": "request action-time batch_upload authorization, generate the authorization record, then run the batch pre-mutation gate with the same sample evidence",
        "nextCommands": {
            "_note": "exact auth-record + pre-mutation-gate commands for this batch, transcribed from the batch runbook so the operator need not open it; keep the current-user authorization placeholder until action-time",
            "authorizationRecord": batch_runbook.get("authorizationRecordCommand"),
            "preMutationGate": batch_runbook.get("preMutationGateCommand"),
        },
        "adversarialChecks": [
            "This step only prepares the batch runbook; it does not upload, publish, delete, cleanup, or mutate settings.",
            "Validated sample evidence unlocks batch preparation only, not browser execution.",
            "The batch runbook keeps browserStepsExecutable=false until action-time authorization and check_pre_mutation_gate.py --action batch_upload pass.",
            "The batch evidence bundle is scaffolding only; it does not authorize or prove batch upload.",
            "When manifest items contain categories, tags, or categoryIds, a valid taxonomy execution validation is required before batch preparation.",
            "Use the same sample evidence in both the batch runbook and the pre-mutation gate.",
            "Existing sample evidence is continuity context for other content types; only the current --sample-evidence validates this manifest.",
            "Batch evidence still needs one progress row per manifest slug plus backend/frontend detail audit proof before later launch stages can rely on it.",
        ],
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare batch upload/publish runbook after sample evidence passes.")
    parser.add_argument("--run-evidence", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sample-evidence", required=True)
    parser.add_argument("--existing-sample-evidence", action="append", default=[])
    parser.add_argument("--taxonomy-validation", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target", default="")
    parser.add_argument("--target-identifier", default="")
    parser.add_argument("--authorization-output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote batch upload/publish preparation summary: {summary['artifacts']['batchRunbook']}")
        print(f"contentType={summary['contentType']} readyForBrowserStage={summary['readyForBrowserStage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
