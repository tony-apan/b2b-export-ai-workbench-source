#!/usr/bin/env python3
"""Validate taxonomy execution evidence and refresh source execution status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from content_goal_coverage_utils import (
    matching_created_site_submitted_values,
    matching_confirmation_decision_matrix,
    matching_content_counts,
    matching_coverage,
    matching_quality_review,
    matching_source_identity,
    matching_wiki_review,
)
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_source_status
from validate_taxonomy_execution_evidence import load_json as load_taxonomy_json
from validate_taxonomy_execution_evidence import validate_evidence as validate_taxonomy_evidence


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


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "validation": output_dir / "taxonomy-execution-validation.json",
        "source_status": output_dir / "source-execution-status.after-taxonomy.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-taxonomy.json",
        "summary": output_dir / "taxonomy-execution-apply-summary.json",
    }


def source_context_entries(args: argparse.Namespace, handoff: dict[str, Any], evidence: dict[str, Any]) -> list[tuple[str, dict[str, Any] | None]]:
    review_path = args.review_packet or review_packet_from_confirmation(args.confirmation)
    return [
        ("source package", load_json(args.package, "source package") if args.package else None),
        ("review packet", load_json(review_path, "review packet") if review_path else None),
        ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
        ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
        ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
        ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
        ("taxonomy handoff", handoff),
        ("taxonomy evidence", evidence),
    ]


def post_create_context_entries(args: argparse.Namespace, handoff: dict[str, Any], evidence: dict[str, Any]) -> list[tuple[str, dict[str, Any] | None]]:
    return [
        ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
        ("taxonomy handoff", handoff),
        ("taxonomy evidence", evidence),
    ]


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    evidence = load_taxonomy_json(Path(args.taxonomy_evidence), "taxonomy execution evidence")
    handoff = load_taxonomy_json(Path(args.taxonomy_handoff), "taxonomy execution handoff")
    context_entries = source_context_entries(args, handoff, evidence)
    post_create_entries = post_create_context_entries(args, handoff, evidence)
    source_identity, source_identity_issues = matching_source_identity(context_entries, require_when_present=False)
    submitted_values, submitted_values_issues = matching_created_site_submitted_values(
        post_create_entries,
        require_when_present=False,
    )
    source_coverage, source_coverage_issues = matching_coverage(context_entries, require_when_present=False)
    source_counts, source_counts_issues = matching_content_counts(context_entries)
    source_quality, source_quality_issues = matching_quality_review(context_entries, require_when_present=False)
    source_wiki_review, source_wiki_review_issues = matching_wiki_review(context_entries, require_when_present=False)
    source_decision_matrix, source_decision_matrix_issues = matching_confirmation_decision_matrix(
        context_entries,
        require_when_present=False,
    )
    context_issues = [
        *source_identity_issues,
        *submitted_values_issues,
        *source_coverage_issues,
        *source_counts_issues,
        *source_quality_issues,
        *source_wiki_review_issues,
        *source_decision_matrix_issues,
    ]
    if context_issues:
        raise SystemExit("ERROR: taxonomy source context invalid:\n- " + "\n- ".join(context_issues))
    issues = validate_taxonomy_evidence(evidence, handoff)
    validation = {
        "kind": "allincms_taxonomy_execution_evidence_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "evidence": args.taxonomy_evidence,
        "handoff": args.taxonomy_handoff,
        "siteKey": evidence.get("siteKey"),
        "taxonomyMappingCount": len(evidence.get("taxonomyMappings", [])) if isinstance(evidence.get("taxonomyMappings"), list) else 0,
        "taxonomyPrerequisiteSatisfied": not issues,
        "issues": issues,
    }
    write_json(paths["validation"], validation)
    if issues and args.fail_on_invalid:
        raise SystemExit("ERROR: taxonomy execution evidence invalid:\n- " + "\n- ".join(issues))

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
            taxonomy_validation=str(paths["validation"]),
            schema_capture_handoff=args.schema_capture_handoff,
            upload_readiness=args.upload_readiness,
            sample_evidence=args.sample_evidence,
            batch_evidence=args.batch_evidence,
            batch_validation=args.batch_validation,
            forms_media_settings=getattr(args, "forms_media_settings", ""),
            launch_acceptance=args.launch_acceptance,
        )
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
        taxonomy_evidence=args.taxonomy_evidence,
    )

    ready_for_next = "blocked_taxonomy_evidence" if issues else str(source_status.get("currentStage"))
    summary = {
        "kind": "allincms_taxonomy_execution_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": evidence.get("siteKey"),
        "contentGoalCoverage": source_coverage or {},
        "contentCounts": source_counts or {},
        "contentQualityReview": source_quality or {},
        "wikiReview": source_wiki_review or {},
        "confirmationDecisionMatrix": source_decision_matrix or [],
        **(source_identity or {}),
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "validationValid": not issues,
        "readyForNextStage": ready_for_next,
        "artifacts": {
            "taxonomyValidation": str(paths["validation"]),
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {"taxonomyIssues": issues},
        "adversarialChecks": [
            "This helper validates redacted evidence and refreshes local status only; it does not mutate AllinCMS.",
            "Taxonomy proof must map every source-confirmed handoff term and include backend plus mapping proof.",
            "A valid taxonomy stage does not skip schema capture, sample upload, batch upload, launch QA, or cleanup gates.",
            "Pass the resulting taxonomyValidation into manifest readiness and batch preparation when manifests contain categories/tags/categoryIds.",
            "Source next-stage handoff is generated from refreshed status and must be followed before later browser or helper stages.",
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
    parser = argparse.ArgumentParser(description="Apply taxonomy execution evidence to source execution status.")
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
    parser.add_argument("--taxonomy-handoff", required=True)
    parser.add_argument("--taxonomy-evidence", required=True)
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", default="")
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
        print(f"Wrote taxonomy execution apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["validationValid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
