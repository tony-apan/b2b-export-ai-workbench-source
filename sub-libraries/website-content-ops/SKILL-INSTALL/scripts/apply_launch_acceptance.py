#!/usr/bin/env python3
"""Validate launch acceptance evidence and refresh source execution status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from content_goal_coverage_utils import (
    load_matching_confirmation_decision_matrix,
    load_matching_content_goal_overages,
    load_matching_coverage,
    load_matching_created_site_submitted_values,
    load_matching_quality_review,
    load_matching_wiki_review,
    matching_content_counts,
    matching_source_identity,
)
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from make_source_run_final_closeout import build_summary as build_final_closeout_summary
from summarize_source_execution_status import summarize as summarize_source_status
from validate_launch_acceptance import build_report as build_launch_report
from validate_source_run_acceptance import validate_acceptance as validate_source_run_acceptance


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


def first_path(value: Any) -> str:
    paths = path_list(value)
    return paths[0] if paths else ""


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "validation": output_dir / "launch-acceptance-validation.json",
        "source_status": output_dir / "source-execution-status.after-launch-acceptance.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-launch-acceptance.json",
        "source_run_acceptance": output_dir / "source-run-acceptance-validation.json",
        "final_closeout": output_dir / "source-run-final-closeout.json",
        "summary": output_dir / "launch-acceptance-apply-summary.json",
    }


def launch_args(args: argparse.Namespace, validation_path: Path, round_closeout_path: str) -> SimpleNamespace:
    return SimpleNamespace(
        run_evidence=args.run_evidence,
        module_coverage=args.module_coverage,
        stage_coverage=args.stage_coverage,
        upload_readiness=args.upload_readiness,
        sample_evidence=args.sample_evidence,
        batch_evidence=args.batch_evidence,
        batch_validation=path_list(args.batch_validation),
        forms_media_settings=args.forms_media_settings,
        final_frontend_audit=args.final_frontend_audit,
        cleanup_evidence=args.cleanup_evidence,
        round_closeout=round_closeout_path,
        require_created_site=args.require_created_site,
        output=str(validation_path),
        json=False,
    )


def maybe_build_final_closeout(
    args: argparse.Namespace,
    paths: dict[str, Path],
    *,
    source_status_path: str,
    next_stage_handoff_path: str,
    existing_round_closeout: str,
) -> str:
    final_closeout_output = getattr(args, "final_closeout_output", "") or ""
    if not final_closeout_output:
        final_closeout_output = str(paths["final_closeout"]) if getattr(args, "auto_final_closeout", False) else ""
    if not final_closeout_output:
        return existing_round_closeout

    sedimentation = getattr(args, "final_closeout_sedimentation", "") or ""
    sedimentation_note = getattr(args, "final_closeout_sedimentation_note", "") or ""
    if not sedimentation or not sedimentation_note:
        raise SystemExit("ERROR: final closeout generation requires --final-closeout-sedimentation and --final-closeout-sedimentation-note")

    closeout_args = SimpleNamespace(
        source_status=source_status_path,
        source_next_stage_handoff=next_stage_handoff_path,
        package=args.package,
        review_packet=args.review_packet or review_packet_from_confirmation(args.confirmation),
        confirmation=args.confirmation,
        created_site_binding=args.created_site_binding,
        upload_readiness=args.upload_readiness,
        sample_evidence=args.sample_evidence,
        batch_validation=path_list(args.batch_validation),
        forms_media_settings=args.forms_media_settings,
        final_frontend_audit=args.final_frontend_audit,
        cleanup_evidence=args.cleanup_evidence,
        launch_acceptance=str(paths["validation"]),
        objective=getattr(args, "objective", "source files to confirmed AllinCMS site with pages, products, posts, and launch proof"),
        sedimentation=sedimentation,
        sedimentation_note=sedimentation_note,
    )
    closeout = build_final_closeout_summary(closeout_args)
    output = Path(final_closeout_output).expanduser().resolve()
    ensure_output_dir_outside_skill(output.parent)
    write_json(output, closeout)
    return str(output)


def build_source_status(args: argparse.Namespace, launch_acceptance_path: str) -> dict[str, Any]:
    return summarize_source_status(
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
            batch_evidence=args.batch_evidence,
            batch_validation=path_list(args.batch_validation),
            forms_media_settings=getattr(args, "forms_media_settings", ""),
            launch_acceptance=launch_acceptance_path,
        )
    )


def build_next_stage_handoff(
    args: argparse.Namespace,
    paths: dict[str, Path],
    output_dir: Path,
    round_closeout_path: str,
) -> dict[str, Any]:
    return build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
        run_evidence=args.run_evidence,
        module_coverage=args.module_coverage,
        stage_coverage=args.stage_coverage,
        final_frontend_audit=args.final_frontend_audit,
        cleanup_evidence=args.cleanup_evidence,
        round_closeout=round_closeout_path,
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)
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
    source_quality, source_quality_issues = load_matching_quality_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=True,
    )
    if source_quality_issues:
        raise SystemExit("ERROR: source content quality review invalid:\n- " + "\n- ".join(source_quality_issues))
    source_overages, source_overage_issues = load_matching_content_goal_overages(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
            ("forms/media/settings", args.forms_media_settings),
            ("final frontend audit", args.final_frontend_audit),
        ],
        require_when_any_source=False,
        quality=source_quality,
    )
    if source_overage_issues:
        raise SystemExit("ERROR: source content goal overages invalid:\n- " + "\n- ".join(source_overage_issues))
    source_wiki_review, source_wiki_review_issues = load_matching_wiki_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=True,
    )
    if source_wiki_review_issues:
        raise SystemExit("ERROR: source wiki review invalid:\n- " + "\n- ".join(source_wiki_review_issues))
    source_decision_matrix, source_decision_matrix_issues = load_matching_confirmation_decision_matrix(
        [
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=True,
    )
    if source_decision_matrix_issues:
        raise SystemExit("ERROR: source confirmation decision matrix invalid:\n- " + "\n- ".join(source_decision_matrix_issues))
    source_counts, source_count_issues = matching_content_counts(
        [
            ("source package", load_json(args.package, "source package") if args.package else None),
            (
                "review packet",
                load_json(args.review_packet or review_packet_from_confirmation(args.confirmation), "review packet")
                if (args.review_packet or review_packet_from_confirmation(args.confirmation))
                else None,
            ),
            ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
            ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
            ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
            ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
            ("forms/media/settings", load_json(args.forms_media_settings, "forms/media/settings") if args.forms_media_settings else None),
            ("final frontend audit", load_json(args.final_frontend_audit, "final frontend audit") if args.final_frontend_audit else None),
        ],
        require_labels={"forms/media/settings", "final frontend audit"},
    )
    if source_count_issues:
        raise SystemExit("ERROR: source content counts invalid:\n- " + "\n- ".join(source_count_issues))
    source_identity, source_identity_issues = matching_source_identity(
        [
            ("source package", load_json(args.package, "source package") if args.package else None),
            (
                "review packet",
                load_json(args.review_packet or review_packet_from_confirmation(args.confirmation), "review packet")
                if (args.review_packet or review_packet_from_confirmation(args.confirmation))
                else None,
            ),
            ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
            ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
            ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
            ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
            ("forms/media/settings", load_json(args.forms_media_settings, "forms/media/settings") if args.forms_media_settings else None),
            ("final frontend audit", load_json(args.final_frontend_audit, "final frontend audit") if args.final_frontend_audit else None),
        ],
        require_when_present=True,
    )
    if source_identity_issues:
        raise SystemExit("ERROR: source identity hashes invalid:\n- " + "\n- ".join(source_identity_issues))
    created_site_submitted_values, created_site_submitted_value_issues = load_matching_created_site_submitted_values(
        [
            ("created-site binding", args.created_site_binding),
            ("forms/media/settings", args.forms_media_settings),
            ("final frontend audit", args.final_frontend_audit),
        ],
        require_when_any_source=False,
    )
    if created_site_submitted_value_issues:
        raise SystemExit(
            "ERROR: created-site submitted values invalid:\n- "
            + "\n- ".join(created_site_submitted_value_issues)
        )

    initial_round_closeout = args.round_closeout
    auto_closeout_requested = bool(getattr(args, "auto_final_closeout", False) or getattr(args, "final_closeout_output", ""))
    if not initial_round_closeout and auto_closeout_requested:
        initial_round_closeout = ""
    validation = build_launch_report(launch_args(args, paths["validation"], initial_round_closeout))
    validation["generatedAt"] = now_iso()
    validation["contentGoalCoverage"] = source_coverage or {}
    validation["contentCounts"] = source_counts or {}
    validation["contentQualityReview"] = source_quality or {}
    validation["contentGoalOverages"] = source_overages or {}
    validation["wikiReview"] = source_wiki_review or {}
    validation["confirmationDecisionMatrix"] = source_decision_matrix or []
    validation.update(source_identity or {})
    if created_site_submitted_values:
        validation["createdSiteSubmittedValues"] = created_site_submitted_values
    write_json(paths["validation"], validation)
    validation_valid = validation.get("valid") is True and validation.get("complete") is True

    source_status = build_source_status(
        args,
        str(paths["validation"]) if validation_valid or auto_closeout_requested else "",
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_next_stage_handoff(args, paths, output_dir, initial_round_closeout)
    write_json(paths["next_stage_handoff"], next_stage_handoff)
    final_round_closeout = maybe_build_final_closeout(
        args,
        paths,
        source_status_path=str(paths["source_status"]),
        next_stage_handoff_path=str(paths["next_stage_handoff"]),
        existing_round_closeout=initial_round_closeout,
    )
    if final_round_closeout != initial_round_closeout or auto_closeout_requested:
        validation = build_launch_report(launch_args(args, paths["validation"], final_round_closeout))
        validation["generatedAt"] = now_iso()
        validation["contentGoalCoverage"] = source_coverage or {}
        validation["contentCounts"] = source_counts or {}
        validation["contentQualityReview"] = source_quality or {}
        validation["contentGoalOverages"] = source_overages or {}
        validation["wikiReview"] = source_wiki_review or {}
        validation["confirmationDecisionMatrix"] = source_decision_matrix or []
        validation.update(source_identity or {})
        if created_site_submitted_values:
            validation["createdSiteSubmittedValues"] = created_site_submitted_values
        write_json(paths["validation"], validation)
        validation_valid = validation.get("valid") is True and validation.get("complete") is True
        source_status = build_source_status(args, str(paths["validation"]) if validation_valid else "")
        write_json(paths["source_status"], source_status)
        next_stage_handoff = build_next_stage_handoff(args, paths, output_dir, final_round_closeout)
    source_run_acceptance = validate_source_run_acceptance(
        status_path=str(paths["source_status"]),
        next_stage_handoff_path=str(paths["next_stage_handoff"]),
        package_path=args.package,
        review_packet_path=args.review_packet or review_packet_from_confirmation(args.confirmation),
        confirmation_path=args.confirmation,
        launch_acceptance_path=str(paths["validation"]),
        created_site_binding_path=args.created_site_binding,
        upload_readiness_path=args.upload_readiness,
        sample_evidence_paths=args.sample_evidence,
        batch_validation_paths=path_list(args.batch_validation),
        forms_media_settings_path=args.forms_media_settings,
        final_frontend_audit_path=args.final_frontend_audit,
        cleanup_evidence_path=args.cleanup_evidence,
        round_closeout_path=final_round_closeout,
        objective=getattr(args, "objective", "source files to confirmed AllinCMS site with pages, products, posts, and launch proof"),
    )
    write_json(paths["source_run_acceptance"], source_run_acceptance)

    blocked_keys = [
        str(item.get("key"))
        for item in validation.get("blocked", [])
        if isinstance(item, dict) and item.get("key")
    ]
    ready_for_next = str(source_status.get("currentStage"))
    if not validation_valid:
        ready_for_next = "blocked_launch_acceptance"

    summary = {
        "kind": "allincms_launch_acceptance_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "requireCreatedSite": args.require_created_site,
        **(source_identity or {}),
        **({"createdSiteSubmittedValues": created_site_submitted_values} if created_site_submitted_values else {}),
        "contentGoalCoverage": source_coverage or {},
        "contentCounts": source_counts or {},
        "contentQualityReview": source_quality or {},
        "contentGoalOverages": source_overages or {},
        "wikiReview": source_wiki_review or {},
        "confirmationDecisionMatrix": source_decision_matrix or [],
        "validationValid": validation_valid,
        "readyForNextStage": ready_for_next,
        "artifacts": {
            "launchAcceptanceValidation": str(paths["validation"]),
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
            "sourceRunAcceptance": str(paths["source_run_acceptance"]),
            "sourceRunFinalCloseout": final_round_closeout,
        },
        "validation": {
            "blockedKeys": blocked_keys,
            "blockedCount": len(blocked_keys),
        },
        "adversarialChecks": [
            "This helper validates launch acceptance evidence and refreshes local status only; it does not mutate AllinCMS.",
            "Launch acceptance is complete only when the validator reports both valid=true and complete=true.",
            "A valid batch upload does not imply launch acceptance; forms/media/settings, final frontend audit, cleanup, and round closeout remain separate proof.",
            "If launch acceptance is invalid, source execution status must remain blocked at launch_acceptance rather than being marked complete.",
            "Source next-stage handoff is generated from refreshed status; complete remains unproven unless that status is complete.",
        ],
        "nextAction": str(source_status.get("nextAction") or "inspect refreshed source execution status"),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
        "sourceRunAcceptance": {
            "accepted": source_run_acceptance.get("accepted"),
            "issueCount": len(source_run_acceptance.get("issues", [])) if isinstance(source_run_acceptance.get("issues"), list) else 0,
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply launch acceptance validation to source execution status.")
    parser.add_argument("--run-evidence", required=True)
    parser.add_argument("--module-coverage", default="")
    parser.add_argument("--stage-coverage", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--final-frontend-audit", default="")
    parser.add_argument("--cleanup-evidence", default="")
    parser.add_argument("--round-closeout", default="")
    parser.add_argument("--auto-final-closeout", action="store_true")
    parser.add_argument("--final-closeout-output", default="")
    parser.add_argument("--final-closeout-sedimentation", choices=["updated", "none", "read-only-deferred"], default="")
    parser.add_argument("--final-closeout-sedimentation-note", default="")
    parser.add_argument("--objective", default="source files to confirmed AllinCMS site with pages, products, posts, and launch proof")
    parser.add_argument("--require-created-site", action="store_true")
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
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote launch acceptance apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["validationValid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
