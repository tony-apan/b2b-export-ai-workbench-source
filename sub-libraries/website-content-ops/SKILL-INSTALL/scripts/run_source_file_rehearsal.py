#!/usr/bin/env python3
"""Run a local source-file-to-site-package rehearsal without remote mutation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from apply_refined_source_wiki import build as apply_refined_source_wiki
from draft_refined_source_wiki import build_refined_wiki as draft_refined_source_wiki
from make_source_confirmation_brief import build_brief as build_confirmation_brief
from make_source_confirmation_brief import markdown_lines as confirmation_brief_markdown_lines
from make_source_review_objective_coverage import build_coverage as build_review_objective_coverage
from prepare_confirmed_site_execution import build as prepare_confirmed_execution
from prepare_source_site_package import build as prepare_source_site_package
from validate_source_confirmation_brief import validate_brief as validate_confirmation_brief
from validate_source_file_rehearsal import build_report as build_rehearsal_validation_report
from validate_source_file_rehearsal import validate_summary as validate_rehearsal_summary
from validate_source_package_review_packet import load_json as load_review_json


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


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "source_prepare": output_dir / "01-source-prepare",
        "source_prepare_summary": output_dir / "01-source-prepare" / "prepare-source-site-package-summary.json",
        "refined_apply": output_dir / "02-refined-source-apply",
        "refined_apply_summary": output_dir / "02-refined-source-apply" / "refined-source-wiki-apply-summary.json",
        "confirmed_execution": output_dir / "03-confirmed-execution",
        "confirmed_execution_summary": output_dir
        / "03-confirmed-execution"
        / "confirmed-site-execution-preparation-summary.json",
        "confirmation_brief": output_dir / "source-confirmation-brief.json",
        "confirmation_brief_markdown": output_dir / "source-confirmation-brief.md",
        "confirmation_brief_validation": output_dir / "source-confirmation-brief-validation.json",
        "review_objective_coverage": output_dir / "source-review-objective-coverage.json",
        "rehearsal_validation": output_dir / "source-file-rehearsal-validation.json",
        "summary": output_dir / "source-file-rehearsal-summary.json",
    }


def source_prepare_args(args: argparse.Namespace, output_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        sources=args.sources,
        output_dir=str(output_dir),
        recursive=args.recursive,
        run_label=args.run_label,
        site_name=args.site_name,
        site_description=args.site_description,
        language=args.language,
        industry=args.industry,
        site_key=args.site_key,
        frontend_base_url=args.frontend_base_url,
        content_types=args.content_types,
        source_types=args.source_types,
        gap_ledger=args.gap_ledger,
        resolved_gap_evidence=args.resolved_gap_evidence,
        max_text_chars=args.max_text_chars,
        max_table_rows=args.max_table_rows,
    )


def refined_apply_args(args: argparse.Namespace, source_summary: dict[str, Any], output_dir: Path) -> SimpleNamespace:
    artifacts = source_summary.get("artifacts") if isinstance(source_summary.get("artifacts"), dict) else {}
    return SimpleNamespace(
        source_wiki=args.refined_source_wiki,
        inventory=str(artifacts.get("inventory", "")),
        refinement_brief=str(artifacts.get("sourceWikiRefinementBrief", "")),
        requirements=str(artifacts.get("sourceInputRequirements", "")),
        site_key=args.site_key,
        frontend_base_url=args.frontend_base_url,
        confirmation="",
        execution_plan="",
        artifact_readiness="",
        create_site_handoff="",
        created_site_binding="",
        pages_site_info_handoff="",
        pages_site_info_evidence="",
        pages_site_info_validation="",
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff="",
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        forms_media_settings="",
        launch_acceptance="",
        output_dir=str(output_dir),
        fail_on_invalid=False,
        json=False,
    )


def draft_refined_args(args: argparse.Namespace, source_summary: dict[str, Any]) -> SimpleNamespace:
    artifacts = source_summary.get("artifacts") if isinstance(source_summary.get("artifacts"), dict) else {}
    return SimpleNamespace(
        source_wiki=str(artifacts.get("sourceWiki", "")),
        refinement_brief=str(artifacts.get("sourceWikiRefinementBrief", "")),
        inventory=str(artifacts.get("inventory", "")),
        output=str(artifacts.get("refinedSourceWikiTarget", "")),
        validate_contract=False,
        json=False,
    )


def format_suggested_deferral(deferral: Any) -> str:
    if not isinstance(deferral, dict):
        return ""
    field = str(deferral.get("field", "")).strip()
    decision = str(deferral.get("decision", "")).strip()
    reason = str(deferral.get("reason", "")).strip()
    if not field or not decision:
        return ""
    return f"{field}|{decision}|{reason}"


def review_packet_suggested_accepted_fields(review_packet_path: str) -> str:
    if not review_packet_path:
        return ""
    review_packet = load_review_json(Path(review_packet_path), "review packet")
    fields = review_packet.get("suggestedAcceptedFields")
    if not isinstance(fields, list):
        return ""
    clean = [str(field).strip() for field in fields if isinstance(field, str) and field.strip()]
    return ",".join(clean)


def review_packet_suggested_deferrals(review_packet_path: str) -> list[str]:
    if not review_packet_path:
        return []
    review_packet = load_review_json(Path(review_packet_path), "review packet")
    deferrals = review_packet.get("suggestedAcceptedDeferrals")
    if not isinstance(deferrals, list):
        return []
    return [item for item in (format_suggested_deferral(deferral) for deferral in deferrals) if item]


def accepted_fields(args: argparse.Namespace, review_packet_path: str) -> str:
    if args.accepted_fields:
        return args.accepted_fields
    return review_packet_suggested_accepted_fields(review_packet_path)


def accepted_deferrals(args: argparse.Namespace, review_packet_path: str) -> list[str]:
    if args.accepted_deferral:
        return list(args.accepted_deferral)
    return review_packet_suggested_deferrals(review_packet_path)


def confirmed_execution_args(
    args: argparse.Namespace,
    *,
    package_path: str,
    review_packet_path: str,
    review_objective_coverage_path: str,
    output_dir: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        package=package_path,
        review_packet=review_packet_path,
        source_review_objective_coverage=review_objective_coverage_path,
        user_confirmation_text=args.user_confirmation_text,
        output_dir=str(output_dir),
        target_mode=args.target_mode,
        site_key=args.site_key,
        frontend_base_url=args.frontend_base_url,
        accepted_fields=accepted_fields(args, review_packet_path),
        accepted_deferral=accepted_deferrals(args, review_packet_path),
        notes=args.notes,
        create_preflight=args.create_preflight,
        create_authorization_output=args.create_authorization_output
        or review_packet_create_action_gate_output(review_packet_path),
        fail_if_no_create_handoff=False,
        json=False,
    )


def review_packet_create_action_gate_output(review_packet_path: str) -> str:
    if review_packet_path:
        review_packet = load_review_json(Path(review_packet_path), "review packet")
        value = review_packet.get("createActionGateOutput")
        if isinstance(value, str) and value.strip():
            return value
    return ""


def confirmed_execution_output_dir(review_packet_path: str, fallback: Path) -> Path:
    if review_packet_path:
        review_packet = load_review_json(Path(review_packet_path), "review packet")
        value = review_packet.get("confirmedExecutionOutputDir")
        if isinstance(value, str) and value.strip():
            return Path(value).expanduser().resolve()
    return fallback


def review_artifacts(source_summary: dict[str, Any], refined_summary: dict[str, Any] | None) -> tuple[str, str, str]:
    chosen = refined_summary if refined_summary and refined_summary.get("reviewReady") is True else source_summary
    artifacts = chosen.get("artifacts") if isinstance(chosen.get("artifacts"), dict) else {}
    package_path = str(artifacts.get("sourceSitePackage", ""))
    review_packet_path = str(artifacts.get("reviewPacket", ""))
    status_path = str(artifacts.get("sourceExecutionStatus", ""))
    return package_path, review_packet_path, status_path


def chosen_source_wiki_artifacts(source_summary: dict[str, Any], refined_summary: dict[str, Any] | None) -> dict[str, str]:
    chosen = refined_summary if refined_summary and refined_summary.get("reviewReady") is True else source_summary
    artifacts = chosen.get("artifacts") if isinstance(chosen.get("artifacts"), dict) else {}
    return {
        "sourceWiki": str(artifacts.get("sourceWiki", "")),
        "sourceWikiMarkdown": str(artifacts.get("sourceWikiMarkdown", "")),
        "sourceWikiMarkdownIndex": str(artifacts.get("sourceWikiMarkdownIndex", "")),
    }


def current_source_stage_paths(
    source_summary: dict[str, Any],
    refined_summary: dict[str, Any] | None,
    confirmed_summary: dict[str, Any] | None,
    fallback_status_path: str,
) -> dict[str, str]:
    source_artifacts = source_summary.get("artifacts") if isinstance(source_summary.get("artifacts"), dict) else {}
    current = {
        "sourceExecutionStatus": fallback_status_path,
        "sourceNextStageHandoff": str(source_artifacts.get("sourceNextStageHandoff", "")),
    }
    if isinstance(refined_summary, dict) and isinstance(refined_summary.get("artifacts"), dict):
        refined_artifacts = refined_summary["artifacts"]
        current["sourceExecutionStatus"] = str(refined_artifacts.get("sourceExecutionStatus", "")) or current["sourceExecutionStatus"]
        current["sourceNextStageHandoff"] = str(refined_artifacts.get("sourceNextStageHandoff", "")) or current["sourceNextStageHandoff"]
    if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict):
        confirmed_artifacts = confirmed_summary["artifacts"]
        current["sourceExecutionStatus"] = str(confirmed_artifacts.get("sourceExecutionStatus", "")) or current["sourceExecutionStatus"]
        current["sourceNextStageHandoff"] = str(confirmed_artifacts.get("sourceNextStageHandoff", "")) or current["sourceNextStageHandoff"]
    return current


def confirmation_review_summary(review_packet_path: str) -> dict[str, Any]:
    if not review_packet_path:
        return {
            "available": False,
            "reviewPacket": "",
            "reason": "review packet is not available; refine source wiki before asking for confirmation",
        }
    packet = load_review_json(Path(review_packet_path), "review packet")
    site_info = packet.get("siteInfoNavigationFormsMediaReview")
    site_info = site_info if isinstance(site_info, dict) else {}
    return {
        "available": True,
        "reviewPacket": review_packet_path,
        "counts": packet.get("counts", {}),
        "contentGoalCoverage": packet.get("contentGoalCoverage", {}),
        "contentQualityReview": packet.get("contentQualityReview", {}),
        "contentGoalOverages": packet.get("contentGoalOverages", {}),
        "siteReview": packet.get("siteReview", {}),
        "operationGapsSummary": packet.get("operationGapsSummary", {}),
        "policySummaries": {
            "taxonomyPlan": site_info.get("taxonomyPlan", {}),
            "mediaPolicy": site_info.get("mediaPolicy", {}),
            "contactFormPolicy": site_info.get("contactFormPolicy", {}),
        },
        "confirmationFields": packet.get("confirmationFields", []),
        "suggestedAcceptedFields": packet.get("suggestedAcceptedFields", []),
        "suggestedAcceptedDeferrals": packet.get("suggestedAcceptedDeferrals", []),
        "confirmationDecisionMatrix": packet.get("confirmationDecisionMatrix", []),
        "blockedRemoteActions": packet.get("blockedRemoteActions", []),
        "suggestedConfirmationText": packet.get("suggestedConfirmationText", ""),
        "confirmationCommandTemplate": packet.get("confirmationCommandTemplate", ""),
        "confirmedExecutionCommandTemplate": packet.get("confirmedExecutionCommandTemplate", ""),
        "confirmationOutput": packet.get("confirmationOutput", ""),
        "confirmedExecutionOutputDir": packet.get("confirmedExecutionOutputDir", ""),
        "createActionGateOutput": packet.get("createActionGateOutput", ""),
    }


def review_objective_coverage(
    *,
    package_path: str,
    review_packet_path: str,
    output_path: Path,
) -> dict[str, Any] | None:
    if not package_path or not review_packet_path:
        return None
    package = load_review_json(Path(package_path), "source package")
    packet = load_review_json(Path(review_packet_path), "review packet")
    coverage = build_review_objective_coverage(
        packet,
        review_packet_path=review_packet_path,
        package=package,
        package_path=package_path,
        objective="source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
    )
    write_json(output_path, coverage)
    return coverage


def evidence_paths(*values: Any) -> list[str]:
    return [str(value).strip() for value in values if isinstance(value, str) and str(value).strip()]


def objective_audit(
    *,
    review_ready: bool,
    confirmation_prepared: bool,
    ready_for_browser_stage: str,
    source_summary: dict[str, Any],
    refined_summary: dict[str, Any] | None,
    confirmed_summary: dict[str, Any] | None,
    confirmation_review: dict[str, Any],
) -> dict[str, Any]:
    source_artifacts = source_summary.get("artifacts") if isinstance(source_summary.get("artifacts"), dict) else {}
    refined_artifacts = refined_summary.get("artifacts") if isinstance(refined_summary, dict) and isinstance(refined_summary.get("artifacts"), dict) else {}
    confirmed_artifacts = confirmed_summary.get("artifacts") if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict) else {}
    content_quality = source_summary.get("contentQuality") if isinstance(source_summary.get("contentQuality"), dict) else {}
    confirmation_quality = (
        confirmation_review.get("contentQualityReview")
        if isinstance(confirmation_review.get("contentQualityReview"), dict)
        else {}
    )
    create_preflight_prepared = (
        ready_for_browser_stage in {"create_site_handoff_ready", "ready_for_existing_site_readonly_refresh"}
    )
    effective_ready_shape = (
        confirmation_quality.get("readyShape")
        if review_ready and "readyShape" in confirmation_quality
        else content_quality.get("readyShape")
    )
    checks = [
        {
            "requirement": "user files inventoried and extracted",
            "status": "proven" if bool(source_artifacts.get("inventory")) and bool(source_artifacts.get("rawExtractionSummary")) else "missing",
            "evidence": evidence_paths(source_artifacts.get("inventory", ""), source_artifacts.get("rawExtractionSummary", "")),
        },
        {
            "requirement": "source-backed wiki generated",
            "status": "proven" if bool(source_artifacts.get("sourceWiki")) and bool(source_artifacts.get("sourceWikiMarkdownIndex")) else "missing",
            "evidence": evidence_paths(source_artifacts.get("sourceWiki", ""), source_artifacts.get("sourceWikiMarkdownIndex", "")),
        },
        {
            "requirement": "publishable pages/products/posts/site-info package review-ready",
            "status": "proven" if review_ready else "blocked",
            "evidence": evidence_paths(
                refined_artifacts.get("sourceSitePackage", "") or source_artifacts.get("sourceSitePackage", ""),
                refined_artifacts.get("reviewPacket", "") or source_artifacts.get("reviewPacket", ""),
            ),
            "note": "contentQuality.readyShape is not enough; reviewReady requires source/package/review validation",
        },
        {
            "requirement": "operator has compact confirmation surface",
            "status": "proven" if confirmation_review.get("available") is True else "blocked",
            "evidence": evidence_paths(confirmation_review.get("reviewPacket", "")),
        },
        {
            "requirement": "user content-intent confirmation converted to execution artifacts",
            "status": "proven" if confirmation_prepared else "not_started" if review_ready else "blocked",
            "evidence": evidence_paths(
                confirmed_artifacts.get("confirmation", ""),
                confirmed_artifacts.get("executionPlan", ""),
                confirmed_artifacts.get("artifactReadiness", ""),
            ),
        },
        {
            "requirement": "create/select site execution boundary prepared",
            "status": "prepared" if confirmation_prepared else "not_started",
            "evidence": evidence_paths(
                confirmed_artifacts.get("createSitePreflightBrief", ""),
                confirmed_artifacts.get("createSiteHandoff", ""),
                confirmed_artifacts.get("createSiteRunbook", ""),
                confirmed_artifacts.get("createdSiteEvidenceBundle", ""),
                confirmed_artifacts.get("sourceNextStageHandoff", ""),
            ),
            "readyForBrowserStage": ready_for_browser_stage,
        },
        {
            "requirement": "create-site read-only preflight collected",
            "status": "proven" if create_preflight_prepared else "not_started" if confirmation_prepared else "blocked",
            "evidence": evidence_paths(
                confirmed_artifacts.get("createSiteHandoff", ""),
                confirmed_artifacts.get("createSiteRunbook", ""),
                confirmed_artifacts.get("createdSiteEvidenceBundle", ""),
            ),
            "note": "requires complete workspace API session/site-list preflight evidence before action-time create-site authorization; visible navigation remains forbidden unless the API returns login_required",
            "readyForBrowserStage": ready_for_browser_stage,
        },
        {
            "requirement": "remote site created or selected and bound to artifacts",
            "status": "not_proven",
            "evidence": [],
            "note": "requires exact backend readback that proves the created or selected site identity and binds it to the approved artifacts",
        },
        {
            "requirement": "current-site schemas captured separately for products and posts",
            "status": "not_proven",
            "evidence": [],
            "note": "requires live save-request capture for each content type",
        },
        {
            "requirement": "sample upload/publish verified on backend and frontend",
            "status": "not_proven",
            "evidence": [],
            "note": "requires action-time authorization, sample evidence, and frontend detail proof",
        },
        {
            "requirement": "batch upload/publish and launch QA complete",
            "status": "not_proven",
            "evidence": [],
            "note": "requires batch validation, forms/media/settings evidence, final frontend audit, cleanup, and source-run acceptance",
        },
    ]
    return {
        "complete": False,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "readyShape": effective_ready_shape,
        "reviewReady": review_ready,
        "confirmationPrepared": confirmation_prepared,
        "readyForBrowserStage": ready_for_browser_stage,
        "checks": checks,
        "nextBlockingRequirement": next((item["requirement"] for item in checks if item["status"] in {"missing", "blocked", "not_started", "not_proven"}), ""),
        "completionRule": "Complete only after canonical API/readback evidence proves site creation/selection, schema capture, sample verification, batch upload/publish, applicable editor and anonymous frontend QA, and source-run acceptance; cleanup is separate and only runs when explicitly planned and authorized.",
    }


def summary_next_action(
    *,
    confirmed_summary: dict[str, Any] | None,
    ready_for_user_confirmation: bool,
) -> str:
    if isinstance(confirmed_summary, dict):
        next_action = confirmed_summary.get("nextAction")
        if isinstance(next_action, str) and next_action.strip():
            return next_action
        return "continue from the confirmed execution source-next-stage handoff"
    if ready_for_user_confirmation:
        return "show review packet and ask user for content-intent confirmation"
    return "refine source wiki using source-wiki-refinement-plan.json, then rerun this rehearsal with --refined-source-wiki"


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    source_summary = prepare_source_site_package(source_prepare_args(args, paths["source_prepare"]))
    refined_summary: dict[str, Any] | None = None
    auto_drafted_refined_source_wiki = ""
    if args.auto_draft_refined_source_wiki and not args.refined_source_wiki:
        draft_args = draft_refined_args(args, source_summary)
        if not draft_args.source_wiki or not draft_args.refinement_brief or not draft_args.output:
            raise SystemExit("ERROR: auto draft refined source wiki needs source wiki, refinement brief, and target path")
        drafted = draft_refined_source_wiki(draft_args)
        write_json(Path(draft_args.output), drafted)
        auto_drafted_refined_source_wiki = draft_args.output
        args.refined_source_wiki = auto_drafted_refined_source_wiki
    if args.refined_source_wiki:
        refined_summary = apply_refined_source_wiki(refined_apply_args(args, source_summary, paths["refined_apply"]))

    package_path, review_packet_path, status_path = review_artifacts(source_summary, refined_summary)
    wiki_artifacts = chosen_source_wiki_artifacts(source_summary, refined_summary)
    review_ready = bool(package_path and review_packet_path)
    confirmation_review = confirmation_review_summary(review_packet_path)
    review_objective = review_objective_coverage(
        package_path=package_path,
        review_packet_path=review_packet_path,
        output_path=paths["review_objective_coverage"],
    )
    confirmed_summary: dict[str, Any] | None = None
    if review_ready and args.user_confirmation_text:
        confirmed_output_dir = confirmed_execution_output_dir(review_packet_path, paths["confirmed_execution"])
        confirmed_summary = prepare_confirmed_execution(
            confirmed_execution_args(
                args,
                package_path=package_path,
                review_packet_path=review_packet_path,
                review_objective_coverage_path=str(paths["review_objective_coverage"]) if review_objective else "",
                output_dir=confirmed_output_dir,
            )
        )

    ready_for_user_confirmation = review_ready and not args.user_confirmation_text
    ready_for_browser = bool(confirmed_summary)
    if confirmed_summary:
        ready_for_browser_stage = str(confirmed_summary.get("readyForBrowserStage", ""))
    elif ready_for_user_confirmation:
        ready_for_browser_stage = "waiting_for_user_content_confirmation"
    else:
        ready_for_browser_stage = "needs_source_wiki_refinement"
    audit = objective_audit(
        review_ready=review_ready,
        confirmation_prepared=bool(confirmed_summary),
        ready_for_browser_stage=ready_for_browser_stage,
        source_summary=source_summary,
        refined_summary=refined_summary,
        confirmed_summary=confirmed_summary,
        confirmation_review=confirmation_review,
    )
    current_stage_paths = current_source_stage_paths(source_summary, refined_summary, confirmed_summary, status_path)
    source_artifacts = source_summary.get("artifacts") if isinstance(source_summary.get("artifacts"), dict) else {}

    summary = {
        "kind": "allincms_source_file_rehearsal_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "sourceCount": len(args.sources),
        "inputFileCount": source_summary.get("contentQuality", {}).get("inputFileCount", len(args.sources))
        if isinstance(source_summary.get("contentQuality"), dict)
        else len(args.sources),
        "reviewReady": review_ready,
        "confirmationPrepared": bool(confirmed_summary),
        "readyForBrowserStage": ready_for_browser_stage,
        "confirmationReview": confirmation_review,
        "objectiveAudit": audit,
        "artifacts": {
            "sourcePrepareSummary": str(paths["source_prepare_summary"]),
            "sourceExecutionStatus": current_stage_paths["sourceExecutionStatus"],
            "sourceWiki": wiki_artifacts["sourceWiki"],
            "sourceWikiMarkdown": wiki_artifacts["sourceWikiMarkdown"],
            "sourceWikiMarkdownIndex": wiki_artifacts["sourceWikiMarkdownIndex"],
            "sourceNextStageHandoff": current_stage_paths["sourceNextStageHandoff"],
            "sourceReviewObjectiveCoverage": str(paths["review_objective_coverage"]) if review_objective else "",
            "initialSourceExecutionStatus": str(source_artifacts.get("sourceExecutionStatus", "")),
            "initialSourceNextStageHandoff": str(source_artifacts.get("sourceNextStageHandoff", "")),
            "sourceSitePackage": package_path,
            "reviewPacket": review_packet_path,
            "sourceWikiRefinementPlan": source_summary.get("artifacts", {}).get("sourceWikiRefinementPlan", "")
            if isinstance(source_summary.get("artifacts"), dict)
            else "",
            "sourceWikiRefinementBrief": source_summary.get("artifacts", {}).get("sourceWikiRefinementBrief", "")
            if isinstance(source_summary.get("artifacts"), dict)
            else "",
            "refinedSourceWikiTarget": source_summary.get("artifacts", {}).get("refinedSourceWikiTarget", "")
            if isinstance(source_summary.get("artifacts"), dict)
            else "",
            "autoDraftedRefinedSourceWiki": auto_drafted_refined_source_wiki,
            "refinedApplySummary": str(paths["refined_apply_summary"]) if isinstance(refined_summary, dict) else "",
            "refinedSourceExecutionStatus": refined_summary.get("artifacts", {}).get("sourceExecutionStatus", "")
            if isinstance(refined_summary, dict) and isinstance(refined_summary.get("artifacts"), dict)
            else "",
            "refinedSourceNextStageHandoff": refined_summary.get("artifacts", {}).get("sourceNextStageHandoff", "")
            if isinstance(refined_summary, dict) and isinstance(refined_summary.get("artifacts"), dict)
            else "",
            "confirmedExecutionSummary": confirmed_summary.get("artifacts", {}).get("summary", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else str(paths["confirmed_execution_summary"])
            if isinstance(confirmed_summary, dict)
            else "",
            "confirmedConfirmation": confirmed_summary.get("artifacts", {}).get("confirmation", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedExecutionPlan": confirmed_summary.get("artifacts", {}).get("executionPlan", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedArtifactReadiness": confirmed_summary.get("artifacts", {}).get("artifactReadiness", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedSourceExecutionStatus": confirmed_summary.get("artifacts", {}).get("sourceExecutionStatus", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedSourceNextStageHandoff": confirmed_summary.get("artifacts", {}).get("sourceNextStageHandoff", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSitePreflightBrief": confirmed_summary.get("artifacts", {}).get("createSitePreflightBrief", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSitePreflightBriefValidation": confirmed_summary.get("artifacts", {}).get("createSitePreflightBriefValidation", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSitePreflightTarget": confirmed_summary.get("artifacts", {}).get("createSitePreflightTarget", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSiteHandoff": confirmed_summary.get("artifacts", {}).get("createSiteHandoff", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSiteHandoffValidation": confirmed_summary.get("artifacts", {}).get("createSiteHandoffValidation", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSiteRunbook": confirmed_summary.get("artifacts", {}).get("createSiteRunbook", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreateSiteRunbookValidation": confirmed_summary.get("artifacts", {}).get("createSiteRunbookValidation", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreatedSiteEvidenceBrief": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBrief", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreatedSiteEvidenceBundle": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBundle", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreatedSiteEvidenceBundleValidation": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceBundleValidation", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
            "confirmedCreatedSiteEvidenceTarget": confirmed_summary.get("artifacts", {}).get("createdSiteEvidenceTarget", "")
            if isinstance(confirmed_summary, dict) and isinstance(confirmed_summary.get("artifacts"), dict)
            else "",
        },
        "sourceReviewObjectiveCoverage": {
            "json": str(paths["review_objective_coverage"]) if review_objective else "",
            "reviewComplete": review_objective.get("reviewComplete") if isinstance(review_objective, dict) else False,
            "complete": review_objective.get("complete") if isinstance(review_objective, dict) else False,
            "readyForBrowserStage": review_objective.get("readyForBrowserStage") if isinstance(review_objective, dict) else "",
            "missingForReview": review_objective.get("missingForReview", []) if isinstance(review_objective, dict) else [],
            "missingForFinal": review_objective.get("missingForFinal", []) if isinstance(review_objective, dict) else [],
            "remoteMutationAllowed": review_objective.get("remoteMutationAllowed") if isinstance(review_objective, dict) else False,
        },
        "sourcePrepare": {
            "packageStatus": source_summary.get("packageStatus"),
            "nextAction": source_summary.get("nextAction"),
            "sourceNextStage": source_summary.get("sourceNextStage", {}),
            "contentQuality": source_summary.get("contentQuality", {}),
        },
        "refinedSource": {
            "used": bool(refined_summary),
            "autoDrafted": bool(auto_drafted_refined_source_wiki),
            "reviewReady": refined_summary.get("reviewReady") if isinstance(refined_summary, dict) else None,
            "nextAction": refined_summary.get("nextAction") if isinstance(refined_summary, dict) else "",
            "sourceNextStage": refined_summary.get("sourceNextStage", {}) if isinstance(refined_summary, dict) else {},
        },
        "confirmedExecution": {
            "prepared": bool(confirmed_summary),
            "targetMode": confirmed_summary.get("targetMode") if isinstance(confirmed_summary, dict) else "",
            "readyForBrowserStage": confirmed_summary.get("readyForBrowserStage") if isinstance(confirmed_summary, dict) else "",
            "sourceNextStage": confirmed_summary.get("sourceNextStage", {}) if isinstance(confirmed_summary, dict) else {},
        },
        "adversarialChecks": [
            "This rehearsal is local-only; it must not create, save, upload, publish, or authorize AllinCMS mutations.",
            "If reviewReady=false, refine source-wiki JSON before asking the user to confirm.",
            "If autoDraftedRefinedSourceWiki is set, it is only a local draft refinement and still requires reviewReady=true plus user content confirmation before browser work.",
            "If reviewReady=true but no user confirmation text is supplied, use confirmationReview to summarize counts, gaps, deferrals, and confirmation text before stopping at content-intent confirmation.",
            "If confirmation is prepared, exported draft manifests remain schemaVerified=false until current-site save capture.",
            "Create-site handoff, runbook, and evidence bundle may be prepared only when fresh create-preflight evidence is supplied; none is authorization or browser proof.",
            "Existing-site confirmation requires fresh read-only selected-site evidence and artifact binding before pages/site-info, taxonomy, schema capture, sample upload, or batch upload.",
        ],
        "nextAction": summary_next_action(
            confirmed_summary=confirmed_summary,
            ready_for_user_confirmation=ready_for_user_confirmation,
        ),
    }
    confirmation_brief = build_confirmation_brief(summary, str(paths["summary"]))
    confirmation_brief_issues = validate_confirmation_brief(confirmation_brief, summary)
    if confirmation_brief_issues:
        raise SystemExit("ERROR: generated confirmation brief is invalid:\n- " + "\n- ".join(confirmation_brief_issues))
    write_json(paths["confirmation_brief"], confirmation_brief)
    write_json(
        paths["confirmation_brief_validation"],
        {
            "kind": "allincms_source_confirmation_brief_validation",
            "brief": str(paths["confirmation_brief"]),
            "summary": str(paths["summary"]),
            "ok": True,
            "issues": [],
        },
    )
    paths["confirmation_brief_markdown"].write_text(
        "\n".join(confirmation_brief_markdown_lines(confirmation_brief)).rstrip() + "\n",
        encoding="utf-8",
    )
    summary["confirmationBrief"] = {
        "json": str(paths["confirmation_brief"]),
        "markdown": str(paths["confirmation_brief_markdown"]),
        "validation": str(paths["confirmation_brief_validation"]),
        "status": confirmation_brief["status"],
        "nextBlockingRequirement": confirmation_brief["nextBlockingRequirement"],
        "isRemoteMutationAuthorization": False,
    }
    summary["artifacts"]["sourceConfirmationBrief"] = str(paths["confirmation_brief"])
    summary["artifacts"]["sourceConfirmationBriefMarkdown"] = str(paths["confirmation_brief_markdown"])
    summary["artifacts"]["sourceConfirmationBriefValidation"] = str(paths["confirmation_brief_validation"])
    write_json(paths["summary"], summary)
    rehearsal_validation_issues = validate_rehearsal_summary(summary, paths["summary"])
    rehearsal_validation = build_rehearsal_validation_report(paths["summary"], summary, rehearsal_validation_issues)
    write_json(paths["rehearsal_validation"], rehearsal_validation)
    if rehearsal_validation_issues:
        raise SystemExit("ERROR: generated source-file rehearsal summary is invalid:\n- " + "\n- ".join(rehearsal_validation_issues))
    summary["artifacts"]["sourceFileRehearsalValidation"] = str(paths["rehearsal_validation"])
    summary["sourceFileRehearsalValidation"] = {
        "json": str(paths["rehearsal_validation"]),
        "ok": True,
        "issues": [],
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local source-file-to-site-package rehearsal.")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--run-label", default="")
    parser.add_argument("--site-name", required=True)
    parser.add_argument("--site-description", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--industry", default="")
    parser.add_argument("--site-key", default="")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--content-types", default="products,posts,themes/pages,site-info,forms,media,navigation")
    parser.add_argument("--source-types", default="pdf_catalog,product_datasheet,company_profile,website_copy,spreadsheet,plain_brief")
    parser.add_argument("--gap-ledger", action="append", default=[])
    parser.add_argument("--resolved-gap-evidence", action="append", default=[])
    parser.add_argument("--max-text-chars", type=int, default=12000)
    parser.add_argument("--max-table-rows", type=int, default=40)
    parser.add_argument("--refined-source-wiki", default="")
    parser.add_argument("--auto-draft-refined-source-wiki", action="store_true")
    parser.add_argument("--user-confirmation-text", default="")
    parser.add_argument("--target-mode", choices=["new_site", "existing_site"], default="new_site")
    parser.add_argument("--accepted-fields", default="")
    parser.add_argument("--accepted-deferral", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--create-preflight", default="")
    parser.add_argument("--create-authorization-output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.target_mode == "existing_site" and not args.site_key:
        raise SystemExit("ERROR: --site-key is required for existing_site mode")
    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source file rehearsal summary: {Path(args.output_dir).expanduser().resolve() / 'source-file-rehearsal-summary.json'}")
        print(f"reviewReady={str(summary['reviewReady']).lower()} readyForBrowserStage={summary['readyForBrowserStage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
