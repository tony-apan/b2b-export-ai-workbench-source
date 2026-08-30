#!/usr/bin/env python3
"""Validate batch upload/publish evidence and refresh source execution status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from content_goal_coverage_utils import (
    load_matching_coverage,
    matching_confirmation_decision_matrix,
    matching_content_counts,
    matching_created_site_submitted_values,
    matching_quality_review,
    matching_source_identity,
    matching_wiki_review,
)
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_source_status
from validate_batch_upload_publish_evidence import (
    build_report,
    load_json as load_batch_json,
    load_json_any,
    validate_batch_evidence,
)
from validate_manifest import load_manifest


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


def review_packet_from_confirmation(confirmation_path: str) -> str:
    if not confirmation_path:
        return ""
    confirmation = load_json(confirmation_path, "confirmation")
    value = confirmation.get("sourceReviewPacket")
    return value if isinstance(value, str) else ""


def path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def source_context_quality_entries(args: argparse.Namespace, manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any] | None]]:
    review_path = args.review_packet or review_packet_from_confirmation(args.confirmation)
    return [
        ("source package", load_json(args.package, "source package") if args.package else None),
        ("review packet", load_json(review_path, "review packet") if review_path else None),
        ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
        ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
        ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
        ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
        ("manifest", manifest),
    ]


def source_context_wiki_entries(args: argparse.Namespace, manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any] | None]]:
    review_path = args.review_packet or review_packet_from_confirmation(args.confirmation)
    return [
        ("source package", load_json(args.package, "source package") if args.package else None),
        ("review packet", load_json(review_path, "review packet") if review_path else None),
        ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
        ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
        ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
        ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
        ("manifest", manifest),
    ]


def artifact_paths(output_dir: Path, content_type: str) -> dict[str, Path]:
    return {
        "validation": output_dir / f"{content_type}-batch-upload-publish-validation.json",
        "progress_log": output_dir / f"{content_type}-batch-progress-log.json",
        "source_status": output_dir / "source-execution-status.after-batch-upload.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-batch-upload.json",
        "summary": output_dir / f"{content_type}-batch-upload-publish-apply-summary.json",
    }


def progress_log(data: dict[str, Any]) -> dict[str, Any]:
    rows = data.get("progressLog")
    return {
        "kind": "allincms_batch_progress_log",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": data.get("siteKey"),
        "contentType": data.get("contentType"),
        "rows": rows if isinstance(rows, list) else [],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence = load_batch_json(Path(args.batch_evidence), "batch evidence")
    manifest = load_manifest(Path(args.manifest))
    base = load_batch_json(Path(args.base_run_evidence), "base run evidence") if args.base_run_evidence else None
    audit_reports = load_json_any(Path(args.frontend_audit_report), "frontend audit report") if args.frontend_audit_report else None
    content_type = str(manifest.get("contentType", "")).strip() or str(evidence.get("contentType", "")).strip() or "content"
    paths = artifact_paths(output_dir, content_type)
    source_coverage, source_coverage_issues = load_matching_coverage(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    if source_coverage_issues:
        raise SystemExit("ERROR: source content goal coverage invalid:\n- " + "\n- ".join(source_coverage_issues))
    source_quality, source_quality_issues = matching_quality_review(
        source_context_quality_entries(args, manifest),
        require_when_present=False,
    )
    if source_quality_issues:
        raise SystemExit("ERROR: source content quality review invalid:\n- " + "\n- ".join(source_quality_issues))
    source_wiki_review, source_wiki_review_issues = matching_wiki_review(
        source_context_wiki_entries(args, manifest),
        require_when_present=False,
    )
    if source_wiki_review_issues:
        raise SystemExit("ERROR: source wiki review invalid:\n- " + "\n- ".join(source_wiki_review_issues))
    source_decision_matrix, source_decision_matrix_issues = matching_confirmation_decision_matrix(
        source_context_wiki_entries(args, manifest),
        require_when_present=False,
    )
    if source_decision_matrix_issues:
        raise SystemExit("ERROR: source confirmation decision matrix invalid:\n- " + "\n- ".join(source_decision_matrix_issues))
    source_counts, source_counts_issues = matching_content_counts(
        [
            *source_context_wiki_entries(args, manifest),
            ("base run evidence", base),
            ("batch evidence", evidence),
        ]
    )
    if source_counts_issues:
        raise SystemExit("ERROR: source content counts invalid:\n- " + "\n- ".join(source_counts_issues))
    source_identity, source_identity_issues = matching_source_identity(
        [
            *source_context_wiki_entries(args, manifest),
            ("base run evidence", base),
            ("batch evidence", evidence),
        ],
        require_when_present=False,
    )
    if source_identity_issues:
        raise SystemExit("ERROR: source identity hashes invalid:\n- " + "\n- ".join(source_identity_issues))
    submitted_values, submitted_values_issues = matching_created_site_submitted_values(
        [
            ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
            ("manifest", manifest),
            ("base run evidence", base),
            ("batch evidence", evidence),
        ],
        require_when_present=False,
    )
    if submitted_values_issues:
        raise SystemExit("ERROR: created-site submitted values invalid:\n- " + "\n- ".join(submitted_values_issues))

    issues = validate_batch_evidence(
        evidence,
        manifest=manifest,
        base_run_evidence=base,
        audit_reports=audit_reports,
    )
    validation = build_report(
        args.batch_evidence,
        evidence,
        args.manifest,
        manifest,
        args.base_run_evidence,
        args.frontend_audit_report,
        issues,
    )
    validation["generatedAt"] = now_iso()
    write_json(paths["validation"], validation)
    batch_validation_paths = path_list(getattr(args, "existing_batch_validation", []))
    if not issues:
        batch_validation_paths.append(str(paths["validation"]))

    progress_path = ""
    if not issues:
        progress_path = write_json(paths["progress_log"], progress_log(evidence))
    elif args.fail_on_invalid:
        raise SystemExit("ERROR: batch upload/publish evidence invalid:\n- " + "\n- ".join(issues))

    source_status = summarize_source_status(
        SimpleNamespace(
            package=args.package,
            review_packet=args.review_packet or review_packet_from_confirmation(args.confirmation),
            confirmation=args.confirmation,
            execution_plan=args.execution_plan,
            artifact_readiness=args.artifact_readiness,
            create_site_handoff=getattr(args, "create_site_handoff", ""),
            created_site_binding=args.created_site_binding,
            pages_site_info_handoff=args.pages_site_info_handoff,
            pages_site_info_evidence=args.pages_site_info_evidence,
            pages_site_info_validation=args.pages_site_info_validation,
            taxonomy_handoff=args.taxonomy_handoff,
            taxonomy_evidence=args.taxonomy_evidence,
            taxonomy_validation=args.taxonomy_validation,
            schema_capture_handoff=args.schema_capture_handoff,
            upload_readiness=args.upload_readiness,
            sample_evidence=args.sample_evidence,
            batch_evidence=args.batch_evidence if not issues else "",
            batch_validation=batch_validation_paths if not issues else path_list(getattr(args, "existing_batch_validation", [])),
            forms_media_settings=getattr(args, "forms_media_settings", ""),
            launch_acceptance=args.launch_acceptance,
        )
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
        manifest=args.manifest,
    )

    ready_for_next = "blocked_batch_upload_evidence" if issues else str(source_status.get("currentStage"))
    summary = {
        "kind": "allincms_batch_upload_publish_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": evidence.get("siteKey"),
        "contentType": evidence.get("contentType"),
        "contentGoalCoverage": source_coverage or {},
        "contentCounts": source_counts or {},
        "contentQualityReview": source_quality or {},
        "wikiReview": source_wiki_review or {},
        "confirmationDecisionMatrix": source_decision_matrix or [],
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        **(source_identity or {}),
        "validationValid": not issues,
        "readyForNextStage": ready_for_next,
        "artifacts": {
            "batchValidation": str(paths["validation"]),
            "existingBatchValidation": path_list(getattr(args, "existing_batch_validation", [])),
            "mergedBatchValidation": batch_validation_paths,
            "batchProgressLog": progress_path,
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {"batchIssues": issues},
        "adversarialChecks": [
            "This helper validates redacted batch evidence and refreshes local status only; it does not mutate AllinCMS.",
            "A valid batch stage proves only the manifest/content type named by the evidence, manifest, and audit reports.",
            "Forms/media/settings evidence remains locked after batch upload until sourceExecutionStatus.currentStage is forms_media_settings and that proof is captured or explicitly deferred.",
            "Launch acceptance remains locked until sourceExecutionStatus.currentStage is launch_acceptance and the launch gate passes.",
            "Batch validation does not authorize forms, media, settings, cleanup, or final frontend audit mutations.",
            "Source next-stage handoff is generated from refreshed status and must be followed before forms/media/settings or launch work.",
        ],
        "nextAction": str(source_status.get("nextAction") or "inspect refreshed source execution status"),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply batch upload/publish evidence to source execution status.")
    parser.add_argument("--batch-evidence", required=True)
    parser.add_argument("--manifest", required=True, help="Schema-verified posts/products manifest JSON")
    parser.add_argument("--base-run-evidence", default="")
    parser.add_argument("--frontend-audit-report", default="")
    parser.add_argument("--existing-batch-validation", action="append", default=[])
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
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote batch upload/publish apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["validationValid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
