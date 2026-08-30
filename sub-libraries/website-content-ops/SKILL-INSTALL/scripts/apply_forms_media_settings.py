#!/usr/bin/env python3
"""Validate forms/media/settings evidence and refresh source execution status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from content_goal_coverage_utils import (
    matching_created_site_submitted_values,
    load_matching_confirmation_decision_matrix,
    load_matching_quality_review,
    load_matching_wiki_review,
    matching_content_counts,
    matching_confirmation_decision_matrix,
    matching_quality_review,
    matching_source_identity,
    matching_wiki_review,
)
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_source_status
from validate_forms_media_settings_evidence import build_report, load_json, validate_evidence


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


def review_packet_from_confirmation(confirmation_path: str) -> str:
    if not confirmation_path:
        return ""
    confirmation = load_json(Path(confirmation_path), "confirmation")
    value = confirmation.get("sourceReviewPacket")
    return value if isinstance(value, str) else ""


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "validation": output_dir / "forms-media-settings-validation.json",
        "source_status": output_dir / "source-execution-status.after-forms-media-settings.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-forms-media-settings.json",
        "summary": output_dir / "forms-media-settings-apply-summary.json",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    evidence = load_json(Path(args.forms_media_settings_evidence), "forms/media/settings evidence")
    issues = validate_evidence(evidence)
    source_identity, source_identity_issues = matching_source_identity(
        [
            ("review packet", load_json(Path(args.review_packet or review_packet_from_confirmation(args.confirmation)), "review packet") if (args.review_packet or review_packet_from_confirmation(args.confirmation)) else None),
            ("confirmation", load_json(Path(args.confirmation), "confirmation") if args.confirmation else None),
            ("execution plan", load_json(Path(args.execution_plan), "execution plan") if args.execution_plan else None),
            ("artifact readiness", load_json(Path(args.artifact_readiness), "artifact readiness") if args.artifact_readiness else None),
            ("created-site binding", load_json(Path(args.created_site_binding), "created-site binding") if args.created_site_binding else None),
            ("forms/media/settings evidence", evidence),
        ],
        require_when_present=True,
    )
    submitted_values, submitted_values_issues = matching_created_site_submitted_values(
        [
            ("created-site binding", load_json(Path(args.created_site_binding), "created-site binding") if args.created_site_binding else None),
            ("forms/media/settings evidence", evidence),
        ],
        require_when_present=False,
    )
    if source_identity_issues and args.fail_on_invalid:
        raise SystemExit("ERROR: forms/media/settings source identity invalid:\n- " + "\n- ".join(source_identity_issues))
    source_quality, source_quality_issues = load_matching_quality_review(
        [
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=False,
    )
    evidence_quality, evidence_quality_issues = matching_quality_review(
        [
            ("source context", {"contentQualityReview": source_quality} if source_quality else None),
            ("forms/media/settings evidence", evidence),
        ],
        require_when_present=False,
    )
    source_wiki_review, source_wiki_review_issues = load_matching_wiki_review(
        [
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=False,
    )
    evidence_wiki_review, evidence_wiki_review_issues = matching_wiki_review(
        [
            ("source context", {"wikiReview": source_wiki_review} if source_wiki_review else None),
            ("forms/media/settings evidence", evidence),
        ],
        require_when_present=False,
    )
    source_decision_matrix, source_decision_matrix_issues = load_matching_confirmation_decision_matrix(
        [
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=False,
    )
    evidence_decision_matrix, evidence_decision_matrix_issues = matching_confirmation_decision_matrix(
        [
            (
                "source context",
                {"confirmationDecisionMatrix": source_decision_matrix} if source_decision_matrix else None,
            ),
            ("forms/media/settings evidence", evidence),
        ],
        require_when_present=False,
    )
    source_counts, source_count_issues = matching_content_counts(
        [
            ("review packet", load_json(Path(args.review_packet or review_packet_from_confirmation(args.confirmation)), "review packet") if (args.review_packet or review_packet_from_confirmation(args.confirmation)) else None),
            ("confirmation", load_json(Path(args.confirmation), "confirmation") if args.confirmation else None),
            ("execution plan", load_json(Path(args.execution_plan), "execution plan") if args.execution_plan else None),
            ("artifact readiness", load_json(Path(args.artifact_readiness), "artifact readiness") if args.artifact_readiness else None),
            ("created-site binding", load_json(Path(args.created_site_binding), "created-site binding") if args.created_site_binding else None),
        ]
    )
    evidence_counts, evidence_count_issues = matching_content_counts(
        [
            ("source context", {"contentCounts": source_counts} if source_counts else None),
            ("forms/media/settings evidence", evidence),
        ],
        require_labels={"forms/media/settings evidence"} if source_counts else set(),
    )
    source_context_issues = [
        *source_identity_issues,
        *submitted_values_issues,
        *source_quality_issues,
        *evidence_quality_issues,
        *source_wiki_review_issues,
        *evidence_wiki_review_issues,
        *source_decision_matrix_issues,
        *evidence_decision_matrix_issues,
        *source_count_issues,
        *evidence_count_issues,
    ]
    if source_context_issues and args.fail_on_invalid:
        raise SystemExit("ERROR: forms/media/settings source context invalid:\n- " + "\n- ".join(source_context_issues))
    issues = [*issues, *source_context_issues]
    validation = build_report(args.forms_media_settings_evidence, evidence, issues)
    write_json(paths["validation"], validation)
    if issues and args.fail_on_invalid:
        raise SystemExit("ERROR: forms/media/settings evidence invalid:\n- " + "\n- ".join(issues))

    source_status = summarize_source_status(
        SimpleNamespace(
            package=args.package,
            review_packet=args.review_packet or review_packet_from_confirmation(args.confirmation),
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
            upload_readiness=args.upload_readiness,
            sample_evidence=args.sample_evidence,
            batch_evidence=args.batch_evidence,
            batch_validation=args.batch_validation,
            forms_media_settings=args.forms_media_settings_evidence if not issues else "",
            launch_acceptance=args.launch_acceptance,
        )
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
    )

    ready_for_next = "blocked_forms_media_settings_evidence" if issues else str(source_status.get("currentStage"))
    summary = {
        "kind": "allincms_forms_media_settings_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": evidence.get("siteKey"),
        **(source_identity or {}),
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "contentCounts": evidence_counts or source_counts or {},
        "contentQualityReview": evidence_quality or source_quality or {},
        "wikiReview": evidence_wiki_review or source_wiki_review or {},
        "confirmationDecisionMatrix": evidence_decision_matrix or source_decision_matrix or [],
        "validationValid": not issues,
        "readyForNextStage": ready_for_next,
        "artifacts": {
            "formsMediaSettingsValidation": str(paths["validation"]),
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {"formsMediaSettingsIssues": issues},
        "adversarialChecks": [
            "This helper validates redacted forms/media/settings evidence and refreshes local status only; it does not mutate AllinCMS.",
            "Every unverified module must have an explicit deferral; silent omission cannot advance to launch acceptance.",
            "Valid forms/media/settings proof unlocks launch-acceptance evaluation only; final frontend audit, cleanup, and launch gate still decide completion.",
            "Source next-stage handoff is generated from refreshed status and must be followed before launch acceptance.",
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
    parser = argparse.ArgumentParser(description="Apply forms/media/settings evidence to source execution status.")
    parser.add_argument("--forms-media-settings-evidence", required=True)
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
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote forms/media/settings apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["validationValid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
