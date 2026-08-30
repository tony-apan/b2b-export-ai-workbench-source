#!/usr/bin/env python3
"""Prepare schema-verified manifest and one-item sample upload runbook."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from apply_save_capture_to_manifest import build_schema_verified_manifest
from build_manifest_sample_upload_runbook import build_runbook as build_sample_runbook
from build_manifest_sample_upload_runbook import validate_runbook as validate_sample_runbook
from content_goal_coverage_utils import (
    load_matching_confirmation_decision_matrix,
    load_matching_coverage,
    load_matching_quality_review,
    load_matching_wiki_review,
    matching_coverage,
    matching_confirmation_decision_matrix,
    matching_quality_review,
    matching_wiki_review,
)
from make_manifest_upload_readiness import build_report as build_upload_readiness
from prepare_manifest_sample_evidence_bundle import build_bundle as build_sample_evidence_bundle
from prepare_manifest_sample_evidence_bundle import validate_bundle as validate_sample_evidence_bundle
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_schema_capture_progress import summarize as summarize_schema_progress
from summarize_source_execution_status import summarize as summarize_source_status
from validate_manifest import load_manifest, validate_manifest
from validate_probe_save_capture_evidence import load_json as load_capture_json


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


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def artifact_paths(output_dir: Path, content_type: str) -> dict[str, Path]:
    return {
        "schema_manifest": output_dir / f"{content_type}-schema-verified-manifest.json",
        "upload_readiness": output_dir / f"{content_type}-upload-readiness.json",
        "sample_runbook": output_dir / f"{content_type}-manifest-sample-runbook.json",
        "sample_evidence_bundle_dir": output_dir / f"{content_type}-manifest-sample-evidence-bundle",
        "sample_evidence_bundle": output_dir / f"{content_type}-manifest-sample-evidence-bundle" / "evidence-bundle.json",
        "schema_progress": output_dir / "schema-capture-progress.after-schema-manifest.json",
        "source_status": output_dir / "source-execution-status.after-schema-manifest.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-schema-manifest.json",
        "summary": output_dir / f"{content_type}-schema-manifest-sample-preparation-summary.json",
    }


def content_pairs(existing: list[str], content_type: str, path: str) -> list[str]:
    pairs = [item for item in existing if not item.startswith(f"{content_type}=")]
    pairs.append(f"{content_type}={path}")
    return pairs


def append_unique(paths: list[str], path: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in [*paths, path]:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def backend_target(manifest: dict[str, Any], override: str = "") -> str:
    if override:
        return override.rstrip("/")
    site_key = str(manifest.get("siteKey", "")).strip()
    content_type = str(manifest.get("contentType", "")).strip()
    if not site_key or site_key.startswith("{"):
        raise SystemExit("ERROR: schema-verified manifest must have concrete siteKey for sample runbook")
    if content_type not in CONTENT_TYPES:
        raise SystemExit("ERROR: contentType must be products or posts")
    return f"https://workspace.laicms.com/{site_key}/{content_type}"


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    manifest = load_manifest(Path(args.manifest))
    content_type = str(manifest.get("contentType", ""))
    if content_type not in CONTENT_TYPES:
        raise SystemExit("ERROR: manifest.contentType must be products or posts")
    paths = artifact_paths(output_dir, content_type)
    capture = load_capture_json(Path(args.save_capture_evidence))
    base_run_evidence = load_capture_json(Path(args.base_run_evidence)) if args.base_run_evidence else None
    source_coverage, source_coverage_issues = load_matching_coverage(
        [
            ("source package", args.package),
            ("review packet", args.review_packet),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    if source_coverage_issues:
        raise SystemExit("ERROR: source content goal coverage invalid:\n- " + "\n- ".join(source_coverage_issues))
    source_quality, source_quality_issues = load_matching_quality_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    if source_quality_issues:
        raise SystemExit("ERROR: source content quality review invalid:\n- " + "\n- ".join(source_quality_issues))
    source_wiki_review, source_wiki_review_issues = load_matching_wiki_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    if source_wiki_review_issues:
        raise SystemExit("ERROR: source wiki review invalid:\n- " + "\n- ".join(source_wiki_review_issues))
    source_decision_matrix, source_decision_matrix_issues = load_matching_confirmation_decision_matrix(
        [
            ("review packet", args.review_packet),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=True,
    )
    if source_decision_matrix_issues:
        raise SystemExit("ERROR: source confirmation decision matrix invalid:\n- " + "\n- ".join(source_decision_matrix_issues))

    schema_manifest = build_schema_verified_manifest(
        manifest=manifest,
        capture=capture,
        capture_path=args.save_capture_evidence,
        base_run_evidence=base_run_evidence,
        base_run_evidence_path=args.base_run_evidence,
        site_key_override=args.site_key,
        frontend_base_override=args.frontend_base_url,
    )
    schema_errors = validate_manifest(schema_manifest, require_schema_verified=True)
    if schema_errors:
        raise SystemExit("ERROR: generated schema manifest failed gate:\n- " + "\n- ".join(schema_errors))
    manifest_coverage, manifest_coverage_issues = matching_coverage(
        [
            ("source context", {"contentGoalCoverage": source_coverage} if source_coverage else None),
            ("schema manifest", schema_manifest),
        ],
        require_when_present=False,
    )
    if manifest_coverage_issues:
        raise SystemExit("ERROR: schema manifest content goal coverage invalid:\n- " + "\n- ".join(manifest_coverage_issues))
    manifest_quality, manifest_quality_issues = matching_quality_review(
        [
            ("source context", {"contentQualityReview": source_quality} if source_quality else None),
            ("schema manifest", schema_manifest),
        ],
        require_when_present=False,
    )
    if manifest_quality_issues:
        raise SystemExit("ERROR: schema manifest content quality review invalid:\n- " + "\n- ".join(manifest_quality_issues))
    manifest_wiki_review, manifest_wiki_review_issues = matching_wiki_review(
        [
            ("source context", {"wikiReview": source_wiki_review} if source_wiki_review else None),
            ("schema manifest", schema_manifest),
        ],
        require_when_present=False,
    )
    if manifest_wiki_review_issues:
        raise SystemExit("ERROR: schema manifest wiki review invalid:\n- " + "\n- ".join(manifest_wiki_review_issues))
    manifest_decision_matrix, manifest_decision_matrix_issues = matching_confirmation_decision_matrix(
        [
            ("source context", {"confirmationDecisionMatrix": source_decision_matrix} if source_decision_matrix else None),
            ("schema manifest", schema_manifest),
        ],
        require_when_present=False,
    )
    if manifest_decision_matrix_issues:
        raise SystemExit("ERROR: schema manifest confirmation decision matrix invalid:\n- " + "\n- ".join(manifest_decision_matrix_issues))
    write_json(paths["schema_manifest"], schema_manifest)

    readiness = build_upload_readiness([paths["schema_manifest"]])
    write_json(paths["upload_readiness"], readiness)
    if readiness.get("overallStatus") != "ready_for_sample_upload":
        raise SystemExit("ERROR: upload readiness did not reach ready_for_sample_upload")

    target = backend_target(schema_manifest, args.target)
    authorization_output = args.authorization_output or str(output_dir / f"{content_type}-sample-authorization.json")
    sample_runbook = build_sample_runbook(
        manifest=schema_manifest,
        manifest_path=str(paths["schema_manifest"]),
        target=target,
        authorization_output=authorization_output,
        sample_slug=args.sample_slug,
    )
    sample_runbook_issues = validate_sample_runbook(sample_runbook)
    if sample_runbook_issues:
        raise SystemExit("ERROR: generated sample runbook invalid:\n- " + "\n- ".join(sample_runbook_issues))
    write_json(paths["sample_runbook"], sample_runbook)
    sample_evidence_bundle = build_sample_evidence_bundle(
        runbook=sample_runbook,
        runbook_path=str(paths["sample_runbook"]),
        output_dir=paths["sample_evidence_bundle_dir"],
    )
    sample_evidence_bundle_issues = validate_sample_evidence_bundle(sample_evidence_bundle)
    if sample_evidence_bundle_issues:
        raise SystemExit(
            "ERROR: generated sample evidence bundle invalid:\n- "
            + "\n- ".join(sample_evidence_bundle_issues)
        )
    write_json(paths["sample_evidence_bundle"], sample_evidence_bundle)

    schema_progress: dict[str, Any] | None = None
    if args.schema_capture_handoff:
        schema_progress = summarize_schema_progress(
            SimpleNamespace(
                schema_capture_handoff=args.schema_capture_handoff,
                create_evidence=args.existing_create_evidence,
                save_handoff=args.existing_save_handoff,
                save_runbook=args.existing_save_runbook,
                save_capture=content_pairs(args.existing_save_capture, content_type, args.save_capture_evidence),
                base_run_evidence=content_pairs(args.existing_base_run_evidence, content_type, args.base_run_evidence)
                if args.base_run_evidence
                else args.existing_base_run_evidence,
                schema_manifest=content_pairs(args.existing_schema_manifest, content_type, str(paths["schema_manifest"])),
                output=str(paths["schema_progress"]),
                fail_on_incomplete=False,
                json=False,
            )
        )
        write_json(paths["schema_progress"], schema_progress)

    source_status: dict[str, Any] | None = None
    if args.package or args.artifact_readiness or args.created_site_binding:
        source_status = summarize_source_status(
            SimpleNamespace(
                package=args.package,
                review_packet=args.review_packet,
                confirmation=args.confirmation,
                execution_plan=args.execution_plan,
                artifact_readiness=args.artifact_readiness,
                create_site_handoff=args.create_site_handoff,
                created_site_binding=args.created_site_binding,
                pages_site_info_handoff=args.pages_site_info_handoff,
                pages_site_info_evidence=args.pages_site_info_evidence,
                pages_site_info_validation=args.pages_site_info_validation,
                taxonomy_handoff=args.taxonomy_handoff,
                taxonomy_evidence=args.taxonomy_evidence,
                taxonomy_validation=args.taxonomy_validation,
                schema_capture_handoff=args.schema_capture_handoff,
                upload_readiness=append_unique(args.existing_upload_readiness, str(paths["upload_readiness"])),
                sample_evidence=args.sample_evidence,
                batch_evidence=args.batch_evidence,
                batch_validation=args.batch_validation,
                forms_media_settings=getattr(args, "forms_media_settings", ""),
                launch_acceptance=args.launch_acceptance,
            )
        )
        write_json(paths["source_status"], source_status)
    next_stage_handoff: dict[str, Any] | None = None
    if source_status:
        next_stage_handoff = build_source_next_handoff(
            status_path=str(paths["source_status"]),
            output_path=str(paths["next_stage_handoff"]),
            output_dir=str(output_dir / "next-stage"),
            manifest=str(paths["schema_manifest"]),
            save_capture_evidence=args.save_capture_evidence,
            base_run_evidence=args.base_run_evidence,
            site_key=args.site_key,
            frontend_base_url=args.frontend_base_url,
            target=target,
            sample_slug=str(sample_runbook.get("sampleSlug") or ""),
        )

    summary = {
        "kind": "allincms_schema_manifest_sample_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentType": content_type,
        "siteKey": schema_manifest.get("siteKey"),
        "artifacts": {
            "schemaVerifiedManifest": str(paths["schema_manifest"]),
            "uploadReadiness": str(paths["upload_readiness"]),
            "mergedUploadReadiness": append_unique(args.existing_upload_readiness, str(paths["upload_readiness"])),
            "sampleRunbook": str(paths["sample_runbook"]),
            "sampleEvidenceBundle": str(paths["sample_evidence_bundle"]),
            "schemaCaptureProgress": str(paths["schema_progress"]) if schema_progress else "",
            "sourceExecutionStatus": str(paths["source_status"]) if source_status else "",
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]) if next_stage_handoff else "",
        },
        "validation": {
            "schemaManifestErrors": schema_errors,
            "sampleRunbookIssues": sample_runbook_issues,
            "sampleEvidenceBundleIssues": sample_evidence_bundle_issues,
            "uploadReadinessOverallStatus": readiness.get("overallStatus"),
        },
        "sampleSlug": sample_runbook.get("sampleSlug"),
        "contentGoalCoverage": manifest_coverage or source_coverage or {},
        "contentCounts": schema_manifest.get("contentCounts", {}),
        "contentQualityReview": manifest_quality or source_quality or {},
        "wikiReview": manifest_wiki_review or source_wiki_review or {},
        "confirmationDecisionMatrix": manifest_decision_matrix or source_decision_matrix or [],
        "readyForNextStage": str(source_status.get("currentStage")) if source_status else "sample_upload",
        "nextAction": str(source_status.get("nextAction")) if source_status else "request action-time manifest sample upload authorization and run the sample pre-mutation gate",
        "adversarialChecks": [
            "This step creates a schema-verified manifest locally; it does not upload or publish the sample.",
            "Sample runbook browserStepsExecutable remains false until action-time authorization and gate pass.",
            "Sample evidence bundle is scaffolding only; it does not authorize or prove the sample upload.",
            "Schema verification proves save payload shape only; sample backend/frontend proof is still required before batch upload.",
            "When source-status inputs are supplied, follow sourceExecutionStatus.currentStage; schema readiness still cannot skip pages/site-info, taxonomy, sample, batch, or launch gates.",
            "When source-status inputs are supplied, source next-stage handoff is generated from refreshed status and must be followed before browser execution.",
            "Do not use the sample runbook to upload remaining manifest items.",
        ],
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage") if next_stage_handoff else "",
            "mode": next_stage_handoff.get("mode") if next_stage_handoff else "",
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired") if next_stage_handoff else None,
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare schema-verified manifest and sample upload runbook.")
    parser.add_argument("--manifest", required=True, help="Draft posts/products manifest JSON")
    parser.add_argument("--save-capture-evidence", required=True)
    parser.add_argument("--base-run-evidence", default="")
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--create-site-handoff", default="")
    parser.add_argument("--created-site-binding", default="")
    parser.add_argument("--pages-site-info-handoff", default="")
    parser.add_argument("--pages-site-info-evidence", default="")
    parser.add_argument("--pages-site-info-validation", default="")
    parser.add_argument("--taxonomy-handoff", default="")
    parser.add_argument("--taxonomy-evidence", default="")
    parser.add_argument("--taxonomy-validation", default="")
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", default="")
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--site-key", default="")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--sample-slug", default="")
    parser.add_argument("--authorization-output", default="")
    parser.add_argument("--existing-create-evidence", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-handoff", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-runbook", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-save-capture", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-base-run-evidence", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-schema-manifest", action="append", default=[], help="contentType=path; repeatable")
    parser.add_argument("--existing-upload-readiness", action="append", default=[], help="Prior upload readiness report path; repeatable")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote schema manifest/sample preparation summary: {summary['artifacts']['sampleRunbook']}")
        print(f"contentType={summary['contentType']} sampleSlug={summary['sampleSlug']} nextAction={summary['nextAction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
