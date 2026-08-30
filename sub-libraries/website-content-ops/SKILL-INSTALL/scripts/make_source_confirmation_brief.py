#!/usr/bin/env python3
"""Build a compact user-facing confirmation brief from source rehearsal summary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_confirmation_brief import validate_brief


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def first_blocking_requirement(audit: dict[str, Any]) -> str:
    value = audit.get("nextBlockingRequirement")
    if isinstance(value, str) and value.strip():
        return value.strip()
    for item in as_list(audit.get("checks")):
        if isinstance(item, dict) and item.get("status") in {"missing", "blocked", "not_started", "not_proven"}:
            requirement = item.get("requirement")
            if isinstance(requirement, str) and requirement.strip():
                return requirement.strip()
    return ""


def status(summary: dict[str, Any], confirmation_review: dict[str, Any], objective_audit: dict[str, Any]) -> str:
    if summary.get("confirmationPrepared") is True:
        return "confirmed_execution_prepared"
    if summary.get("reviewReady") is True and confirmation_review.get("available") is True:
        return "waiting_for_user_content_confirmation"
    if summary.get("reviewReady") is True:
        return "review_ready_missing_confirmation_surface"
    return "needs_source_wiki_refinement"


def build_confirmation_question(confirmation_review: dict[str, Any]) -> str:
    suggested = confirmation_review.get("suggestedConfirmationText")
    if isinstance(suggested, str) and suggested.strip():
        return suggested.strip()
    return (
        "请确认当前 review packet 中的网站信息、单页、产品、文章、导航、媒体、表单、分类/标签规划，"
        "并确认所有列出的 deferrals 仅作为后续独立动作处理。"
    )


def safe_count(counts: dict[str, Any], key: str) -> int:
    value = counts.get(key)
    return value if isinstance(value, int) and value >= 0 else 0


def source_review_objective(summary: dict[str, Any]) -> dict[str, Any]:
    meta = as_dict(summary.get("sourceReviewObjectiveCoverage"))
    artifacts = as_dict(summary.get("artifacts"))
    return {
        "json": meta.get("json", "") if isinstance(meta.get("json"), str) else artifacts.get("sourceReviewObjectiveCoverage", "")
        if isinstance(artifacts.get("sourceReviewObjectiveCoverage"), str)
        else "",
        "reviewComplete": meta.get("reviewComplete") is True,
        "complete": meta.get("complete") is True,
        "remoteMutationAllowed": meta.get("remoteMutationAllowed") is True,
        "readyForBrowserStage": meta.get("readyForBrowserStage", "") if isinstance(meta.get("readyForBrowserStage"), str) else "",
        "missingForReview": as_list(meta.get("missingForReview")),
        "missingForFinal": as_list(meta.get("missingForFinal")),
    }


def confirmation_decision_matrix(confirmation_review: dict[str, Any]) -> list[dict[str, Any]]:
    existing = confirmation_review.get("confirmationDecisionMatrix")
    if isinstance(existing, list):
        return [item for item in existing if isinstance(item, dict)]
    fields = [item for item in as_list(confirmation_review.get("confirmationFields")) if isinstance(item, str) and item.strip()]
    accepted = {item for item in as_list(confirmation_review.get("suggestedAcceptedFields")) if isinstance(item, str) and item.strip()}
    deferrals = {
        item.get("field"): item
        for item in as_list(confirmation_review.get("suggestedAcceptedDeferrals"))
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
    matrix: list[dict[str, Any]] = []
    for field in fields:
        deferred = deferrals.get(field)
        if isinstance(deferred, dict):
            matrix.append(
                {
                    "field": field,
                    "decision": "defer",
                    "source": "suggestedAcceptedDeferrals",
                    "deferDecision": deferred.get("decision", ""),
                    "reason": deferred.get("reason", ""),
                    "blocksRemoteMutation": False,
                    "operatorNote": "Confirm this deferral explicitly before creating or updating the site.",
                }
            )
        elif field in accepted:
            matrix.append(
                {
                    "field": field,
                    "decision": "accept",
                    "source": "suggestedAcceptedFields",
                    "deferDecision": "",
                    "reason": "",
                    "blocksRemoteMutation": False,
                    "operatorNote": "Confirm this source-backed field before preparing execution artifacts.",
                }
            )
        else:
            matrix.append(
                {
                    "field": field,
                    "decision": "missing_decision",
                    "source": "",
                    "deferDecision": "",
                    "reason": "",
                    "blocksRemoteMutation": True,
                    "operatorNote": "Do not proceed until this field is accepted or explicitly deferred.",
                }
            )
    return matrix


def execution_intake(summary: dict[str, Any], confirmation_review: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    status_value = status(summary, confirmation_review, as_dict(summary.get("objectiveAudit")))
    confirmation_prepared = status_value == "confirmed_execution_prepared"
    confirmed_output_dir = (
        artifacts.get("confirmedExecutionSummary", "")
        if isinstance(artifacts.get("confirmedExecutionSummary"), str)
        else ""
    )
    if confirmed_output_dir:
        confirmed_output_dir = str(Path(confirmed_output_dir).parent)
    commands = {
        "confirmationCommandTemplate": confirmation_review.get("confirmationCommandTemplate", "")
        if isinstance(confirmation_review.get("confirmationCommandTemplate"), str)
        else "",
        "confirmedExecutionCommandTemplate": confirmation_review.get("confirmedExecutionCommandTemplate", "")
        if isinstance(confirmation_review.get("confirmedExecutionCommandTemplate"), str)
        else "",
        "confirmationOutput": (
            str(Path(confirmed_output_dir) / "confirmation-record.json")
            if confirmation_prepared and confirmed_output_dir
            else confirmation_review.get("confirmationOutput", "")
            if isinstance(confirmation_review.get("confirmationOutput"), str)
            else ""
        ),
        "confirmedExecutionOutputDir": (
            confirmed_output_dir
            if confirmation_prepared and confirmed_output_dir
            else confirmation_review.get("confirmedExecutionOutputDir", "")
            if isinstance(confirmation_review.get("confirmedExecutionOutputDir"), str)
            else ""
        ),
        "createActionGateOutput": confirmation_review.get("createActionGateOutput", "")
        if isinstance(confirmation_review.get("createActionGateOutput"), str)
        else "",
    }
    mode = "refine_source_wiki"
    if status_value == "waiting_for_user_content_confirmation":
        mode = "await_user_confirmation_text"
    elif status_value == "confirmed_execution_prepared":
        mode = "collect_create_preflight"
        if summary.get("readyForBrowserStage") == "create_site_handoff_ready":
            mode = "run_gated_create_site"
    return {
        "mode": mode,
        "requiresUserConfirmationText": status_value == "waiting_for_user_content_confirmation",
        "requiresCreatePreflight": status_value == "confirmed_execution_prepared"
        and summary.get("readyForBrowserStage") == "needs_create_site_preflight",
        "readyForGatedCreateSiteRunbook": status_value == "confirmed_execution_prepared"
        and summary.get("readyForBrowserStage") == "create_site_handoff_ready",
        "sourcePackage": artifacts.get("sourceSitePackage", "") if isinstance(artifacts.get("sourceSitePackage"), str) else "",
        "reviewPacket": confirmation_review.get("reviewPacket", "") if isinstance(confirmation_review.get("reviewPacket"), str) else "",
        "sourceConfirmationBrief": artifacts.get("sourceConfirmationBrief", "")
        if isinstance(artifacts.get("sourceConfirmationBrief"), str)
        else "",
        "confirmationOutput": commands["confirmationOutput"],
        "confirmedExecutionOutputDir": commands["confirmedExecutionOutputDir"],
        "createPreflightTarget": artifacts.get("confirmedCreateSitePreflightTarget", "")
        if isinstance(artifacts.get("confirmedCreateSitePreflightTarget"), str)
        else "",
        "createSiteHandoff": artifacts.get("confirmedCreateSiteHandoff", "")
        if isinstance(artifacts.get("confirmedCreateSiteHandoff"), str)
        else "",
        "createSiteRunbook": artifacts.get("confirmedCreateSiteRunbook", "")
        if isinstance(artifacts.get("confirmedCreateSiteRunbook"), str)
        else "",
        "createdSiteEvidenceBundle": artifacts.get("confirmedCreatedSiteEvidenceBundle", "")
        if isinstance(artifacts.get("confirmedCreatedSiteEvidenceBundle"), str)
        else "",
        "createActionGateOutput": commands["createActionGateOutput"],
        "nextCommandTemplate": commands["confirmedExecutionCommandTemplate"]
        if status_value == "waiting_for_user_content_confirmation"
        else "",
        "adversarialChecks": [
            "This intake block is local execution routing only; it is not remote mutation authorization.",
            "Run the confirmed execution template only after the user accepts or overrides the review packet decisions.",
            "Run the create-site runbook only after fresh preflight, action-time authorization, and the pre-mutation gate pass.",
        ],
    }


def markdown_lines(brief: dict[str, Any]) -> list[str]:
    counts = brief["counts"]
    coverage = brief["contentGoalCoverage"]
    quality = brief["contentQualityReview"]
    overages = as_dict(brief.get("contentGoalOverages"))
    review_objective = as_dict(brief.get("sourceReviewObjectiveCoverage"))
    gate = brief["gate"]
    lines = [
        "# AllinCMS Source Confirmation Brief",
        "",
        f"- Status: {brief['status']}",
        f"- Ready for browser stage: {brief['readyForBrowserStage'] or 'not ready'}",
        f"- Next blocking requirement: {brief['nextBlockingRequirement'] or 'none reported'}",
        f"- Review packet: {brief['reviewPacket'] or 'not available'}",
        f"- Source wiki Markdown index: {brief['wikiReview'].get('sourceWikiMarkdownIndex') or 'not available'}",
        "",
        "## Content Counts",
        "",
        f"- Pages: {safe_count(counts, 'pages')}",
        f"- Products: {safe_count(counts, 'products')}",
        f"- Posts: {safe_count(counts, 'posts')}",
        f"- Forms: {safe_count(counts, 'forms')}",
        f"- Media needs: {safe_count(counts, 'media')}",
        "",
        "## Coverage",
        "",
        f"- Complete package coverage: {str(coverage.get('complete') is True).lower()}",
        f"- Missing: {', '.join(str(item) for item in as_list(coverage.get('missing'))) or 'none'}",
        "",
        "## Review Objective Coverage",
        "",
        f"- Review complete: {str(review_objective.get('reviewComplete') is True).lower()}",
        f"- Full objective complete: {str(review_objective.get('complete') is True).lower()}",
        f"- Remote mutation allowed: {str(review_objective.get('remoteMutationAllowed') is True).lower()}",
        f"- Coverage artifact: {review_objective.get('json') or 'not available'}",
        f"- Missing for review: {', '.join(str(item) for item in as_list(review_objective.get('missingForReview'))) or 'none'}",
        f"- Missing for final: {', '.join(str(item) for item in as_list(review_objective.get('missingForFinal'))) or 'none'}",
        "",
        "## Content Quality Review",
        "",
        f"- Ready shape: {str(quality.get('readyShape') is True).lower()}",
        f"- Review required: {str(quality.get('reviewRequired') is True).lower()}",
        f"- Warnings: {', '.join(str(item) for item in as_list(quality.get('warnings'))) or 'none'}",
        "",
        "## Content Goal Overages",
        "",
        f"- Present: {str(overages.get('present') is True).lower()}",
    ]
    overage_details = as_dict(overages.get("details"))
    if overage_details:
        for key in sorted(overage_details):
            detail = as_dict(overage_details.get(key))
            lines.append(
                f"- {key}: declared {detail.get('declared', 0)}, actual {detail.get('actual', 0)}, extra {detail.get('extraCount', 0)}"
            )
            likely = as_list(detail.get("likelyExtraItems")) or as_list(detail.get("items"))
            for item in likely[:8]:
                if not isinstance(item, dict):
                    continue
                label = (
                    item.get("title")
                    or item.get("name")
                    or item.get("label")
                    or item.get("field")
                    or item.get("slug")
                    or item.get("path")
                    or item.get("usage")
                    or "unnamed"
                )
                suffix_parts = [
                    str(item.get(part, "")).strip()
                    for part in ("slug", "path", "sourceRef")
                    if str(item.get(part, "")).strip()
                ]
                suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
                lines.append(f"  - likely extra: {label}{suffix}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
        "## Wiki Review Artifacts",
        "",
        f"- Source wiki JSON: {brief['wikiReview'].get('sourceWiki') or 'not available'}",
        f"- Markdown export manifest: {brief['wikiReview'].get('sourceWikiMarkdown') or 'not available'}",
        f"- Markdown index: {brief['wikiReview'].get('sourceWikiMarkdownIndex') or 'not available'}",
        "",
        "## User Confirmation Text",
        "",
        brief["userConfirmationPrompt"],
        "",
        "## Accepted Fields",
        "",
        ]
    )
    fields = as_list(brief.get("suggestedAcceptedFields"))
    lines.extend([f"- {item}" for item in fields] if fields else ["- none"])
    lines.extend(["", "## Suggested Deferrals", ""])
    deferrals = as_list(brief.get("suggestedAcceptedDeferrals"))
    if deferrals:
        for item in deferrals:
            if isinstance(item, dict):
                lines.append(f"- {item.get('field', '')}: {item.get('decision', '')} ({item.get('reason', '')})")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Confirmation Decision Matrix", ""])
    matrix = as_list(brief.get("confirmationDecisionMatrix"))
    if matrix:
        for item in matrix:
            if isinstance(item, dict):
                detail = item.get("deferDecision") or item.get("source") or ""
                suffix = f" - {detail}" if detail else ""
                lines.append(f"- {item.get('field', '')}: {item.get('decision', '')}{suffix}")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Gate Boundary",
            "",
            f"- Local only: {str(gate['localOnly']).lower()}",
            f"- Remote mutations performed: {str(gate['remoteMutationsPerformed']).lower()}",
            f"- Is remote mutation authorization: {str(gate['isRemoteMutationAuthorization']).lower()}",
            f"- Confirmation command available: {str(bool(brief['commands'].get('confirmationCommandTemplate'))).lower()}",
            f"- Confirmed execution command available: {str(bool(brief['commands'].get('confirmedExecutionCommandTemplate'))).lower()}",
            "",
            "## Execution Intake",
            "",
            f"- Mode: {brief['executionIntake'].get('mode') or 'unknown'}",
            f"- Requires user confirmation text: {str(brief['executionIntake'].get('requiresUserConfirmationText') is True).lower()}",
            f"- Requires create preflight: {str(brief['executionIntake'].get('requiresCreatePreflight') is True).lower()}",
            f"- Ready for gated create-site runbook: {str(brief['executionIntake'].get('readyForGatedCreateSiteRunbook') is True).lower()}",
            f"- Source package: {brief['executionIntake'].get('sourcePackage') or 'not available'}",
            f"- Review packet: {brief['executionIntake'].get('reviewPacket') or 'not available'}",
            f"- Create preflight target: {brief['executionIntake'].get('createPreflightTarget') or 'not available'}",
            f"- Create-site runbook: {brief['executionIntake'].get('createSiteRunbook') or 'not available'}",
            "",
            "## Next Actions",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in as_list(brief.get("nextActions"))] or ["- none"])
    lines.extend(["", "## Adversarial Checks", ""])
    lines.extend([f"- {item}" for item in as_list(brief.get("adversarialChecks"))] or ["- none"])
    return lines


def build_brief(summary: dict[str, Any], summary_path: str = "") -> dict[str, Any]:
    if summary.get("kind") != "allincms_source_file_rehearsal_summary":
        raise SystemExit("ERROR: summary kind must be allincms_source_file_rehearsal_summary")
    confirmation_review = as_dict(summary.get("confirmationReview"))
    objective_audit = as_dict(summary.get("objectiveAudit"))
    artifacts = as_dict(summary.get("artifacts"))
    counts = as_dict(confirmation_review.get("counts"))
    coverage = as_dict(confirmation_review.get("contentGoalCoverage"))
    status_value = status(summary, confirmation_review, objective_audit)
    ready_stage = summary.get("readyForBrowserStage")
    ready_stage = ready_stage if isinstance(ready_stage, str) else ""
    next_blocking = first_blocking_requirement(objective_audit)
    next_actions: list[str]
    if status_value == "needs_source_wiki_refinement":
        next_actions = [
            "Refine source-wiki JSON using source-wiki-refinement-plan and rerun source rehearsal.",
            "Do not ask for user content confirmation or create a site from the current package.",
        ]
    elif status_value == "waiting_for_user_content_confirmation":
        next_actions = [
            "Show this brief or the review packet to the user for content-intent confirmation.",
            "After confirmation, run the review packet's confirmedExecutionCommandTemplate with the current user confirmation text.",
        ]
    else:
        next_actions = [
            "Use the confirmed execution handoff to proceed to the exact browser create/select-site boundary.",
            "Do not upload products/posts until created/selected site binding, schema capture, and sample verification exist.",
        ]
    intake = execution_intake(summary, confirmation_review, artifacts)
    review_objective = source_review_objective(summary)
    commands = {
        "confirmationCommandTemplate": confirmation_review.get("confirmationCommandTemplate", "")
        if isinstance(confirmation_review.get("confirmationCommandTemplate"), str)
        else "",
        "confirmedExecutionCommandTemplate": confirmation_review.get("confirmedExecutionCommandTemplate", "")
        if isinstance(confirmation_review.get("confirmedExecutionCommandTemplate"), str)
        else "",
        "confirmationOutput": intake.get("confirmationOutput", ""),
        "confirmedExecutionOutputDir": intake.get("confirmedExecutionOutputDir", ""),
        "createActionGateOutput": confirmation_review.get("createActionGateOutput", "")
        if isinstance(confirmation_review.get("createActionGateOutput"), str)
        else "",
    }
    return {
        "kind": "allincms_source_confirmation_brief",
        "generatedAt": now_iso(),
        "summary": summary_path,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "status": status_value,
        "reviewReady": summary.get("reviewReady") is True,
        "confirmationPrepared": summary.get("confirmationPrepared") is True,
        "readyForBrowserStage": ready_stage,
        "nextBlockingRequirement": next_blocking,
        "reviewPacket": confirmation_review.get("reviewPacket", "") if isinstance(confirmation_review.get("reviewPacket"), str) else "",
        "counts": counts,
        "contentGoalCoverage": coverage,
        "sourceReviewObjectiveCoverage": review_objective,
        "contentQualityReview": as_dict(confirmation_review.get("contentQualityReview")),
        "contentGoalOverages": as_dict(confirmation_review.get("contentGoalOverages")),
        "wikiReview": {
            "sourceWiki": artifacts.get("sourceWiki", "") if isinstance(artifacts.get("sourceWiki"), str) else "",
            "sourceWikiMarkdown": artifacts.get("sourceWikiMarkdown", "")
            if isinstance(artifacts.get("sourceWikiMarkdown"), str)
            else "",
            "sourceWikiMarkdownIndex": artifacts.get("sourceWikiMarkdownIndex", "")
            if isinstance(artifacts.get("sourceWikiMarkdownIndex"), str)
            else "",
        },
        "siteReview": as_dict(confirmation_review.get("siteReview")),
        "operationGapsSummary": as_dict(confirmation_review.get("operationGapsSummary")),
        "policySummaries": as_dict(confirmation_review.get("policySummaries")),
        "confirmationFields": as_list(confirmation_review.get("confirmationFields")),
        "suggestedAcceptedFields": as_list(confirmation_review.get("suggestedAcceptedFields")),
        "suggestedAcceptedDeferrals": as_list(confirmation_review.get("suggestedAcceptedDeferrals")),
        "confirmationDecisionMatrix": confirmation_decision_matrix(confirmation_review),
        "blockedRemoteActions": as_list(confirmation_review.get("blockedRemoteActions")),
        "userConfirmationPrompt": build_confirmation_question(confirmation_review),
        "commands": commands,
        "executionIntake": intake,
        "artifacts": {
            "sourceWikiRefinementPlan": artifacts.get("sourceWikiRefinementPlan", ""),
            "sourceWikiRefinementBrief": artifacts.get("sourceWikiRefinementBrief", ""),
            "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
            "sourceReviewObjectiveCoverage": artifacts.get("sourceReviewObjectiveCoverage", ""),
            "refinedSourceNextStageHandoff": artifacts.get("refinedSourceNextStageHandoff", ""),
            "confirmedSourceNextStageHandoff": artifacts.get("confirmedSourceNextStageHandoff", ""),
            "confirmedCreateSiteHandoff": artifacts.get("confirmedCreateSiteHandoff", ""),
        },
        "gate": {
            "localOnly": True,
            "remoteMutationsPerformed": False,
            "isRemoteMutationAuthorization": False,
            "mustNotCreateSaveUploadPublish": True,
        },
        "objectiveAudit": {
            "complete": objective_audit.get("complete") is True,
            "nextBlockingRequirement": next_blocking,
            "completionRule": objective_audit.get("completionRule", ""),
        },
        "nextActions": next_actions,
        "adversarialChecks": [
            "This brief summarizes content intent only; it is not create-site, save, upload, publish, route, media, domain, or tracking authorization.",
            "If reviewReady is false, do not ask for final user confirmation.",
            "If confirmationPrepared is true, draft manifests still require current-site schema capture and one sample before batch upload.",
            "Review objective coverage can prove local confirmation readiness only; it must keep complete=false and remoteMutationAllowed=false before live browser completion.",
            "Only final source-run acceptance with live browser evidence can complete the user's end-to-end objective.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a compact confirmation brief from a source-file rehearsal summary.")
    parser.add_argument("summary")
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown-output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary_path = Path(args.summary).expanduser().resolve()
    summary = load_json(summary_path, "source rehearsal summary")
    brief = build_brief(summary, str(summary_path))
    issues = validate_brief(brief, summary)
    if issues:
        raise SystemExit("ERROR: generated confirmation brief is invalid:\n- " + "\n- ".join(issues))
    write_json(Path(args.output).expanduser().resolve(), brief)
    if args.markdown_output:
        write_text(Path(args.markdown_output).expanduser().resolve(), "\n".join(markdown_lines(brief)))
        brief["markdownOutput"] = str(Path(args.markdown_output).expanduser().resolve())
        write_json(Path(args.output).expanduser().resolve(), brief)
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source confirmation brief: {Path(args.output).expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
