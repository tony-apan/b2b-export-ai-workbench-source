#!/usr/bin/env python3
"""Validate a local source confirmation brief."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any


STATUSES = {
    "needs_source_wiki_refinement",
    "waiting_for_user_content_confirmation",
    "review_ready_missing_confirmation_surface",
    "confirmed_execution_prepared",
}


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


def parse_time(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label} must be an ISO 8601 timestamp")


def validate_counts(counts: Any, issues: list[str]) -> None:
    if not isinstance(counts, dict):
        issues.append("counts must be an object")
        return
    for key in ("pages", "products", "posts", "forms", "media"):
        value = counts.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            issues.append(f"counts.{key} must be a non-negative integer when present")


def validate_coverage(brief: dict[str, Any], issues: list[str]) -> None:
    coverage = brief.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        if brief.get("reviewReady") is True:
            issues.append("contentGoalCoverage must be an object when reviewReady is true")
        return
    if brief.get("reviewReady") is True:
        if coverage.get("complete") is not True:
            issues.append("contentGoalCoverage.complete must be true when reviewReady is true")
        checks = coverage.get("checks")
        if not isinstance(checks, dict) or not checks:
            issues.append("contentGoalCoverage.checks must be a non-empty object when reviewReady is true")
        missing = coverage.get("missing")
        if not isinstance(missing, list):
            issues.append("contentGoalCoverage.missing must be an array when reviewReady is true")
        elif missing:
                issues.append("contentGoalCoverage.missing must be empty when reviewReady is true")


def validate_content_quality(brief: dict[str, Any], issues: list[str]) -> None:
    quality = brief.get("contentQualityReview")
    if not isinstance(quality, dict):
        if brief.get("reviewReady") is True:
            issues.append("contentQualityReview must be an object when reviewReady is true")
        return
    if brief.get("reviewReady") is not True and not quality:
        return
    if not isinstance(quality.get("readyShape"), bool):
        issues.append("contentQualityReview.readyShape must be boolean")
    warnings = quality.get("warnings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
        issues.append("contentQualityReview.warnings must be an array of strings")
        warnings = []
    if quality.get("reviewRequired") is not bool(warnings):
        issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")
    counts = quality.get("contentCounts")
    if brief.get("reviewReady") is True and not isinstance(counts, dict):
        issues.append("contentQualityReview.contentCounts must be an object when reviewReady is true")


def validate_content_goal_overages(brief: dict[str, Any], issues: list[str]) -> None:
    overages = brief.get("contentGoalOverages")
    if not isinstance(overages, dict):
        if brief.get("reviewReady") is True:
            issues.append("contentGoalOverages must be an object when reviewReady is true")
        return
    if not overages and brief.get("reviewReady") is not True:
        return
    if not isinstance(overages.get("present"), bool):
        issues.append("contentGoalOverages.present must be boolean")
    details = overages.get("details")
    if not isinstance(details, dict):
        issues.append("contentGoalOverages.details must be an object")
        details = {}
    if bool(details) is not (overages.get("present") is True):
        issues.append("contentGoalOverages.present must equal bool(details)")
    if not isinstance(overages.get("operatorNote"), str) or not overages["operatorNote"].strip():
        issues.append("contentGoalOverages.operatorNote is required")
    quality = as_dict(brief.get("contentQualityReview"))
    warned_keys = sorted(
        warning.split(":", 1)[1]
        for warning in as_list(quality.get("warnings"))
        if isinstance(warning, str) and warning.startswith("exceeds_declared_content_goal:") and ":" in warning
    )
    for key in warned_keys:
        detail = details.get(key)
        if not isinstance(detail, dict):
            issues.append(f"contentGoalOverages.details.{key} is required for warning exceeds_declared_content_goal:{key}")
            continue
        for field in ("declared", "actual", "extraCount"):
            if not isinstance(detail.get(field), int) or detail[field] < 0:
                issues.append(f"contentGoalOverages.details.{key}.{field} must be a non-negative integer")
        if isinstance(detail.get("declared"), int) and isinstance(detail.get("actual"), int) and isinstance(detail.get("extraCount"), int):
            if detail["actual"] - detail["declared"] != detail["extraCount"]:
                issues.append(f"contentGoalOverages.details.{key}.extraCount must equal actual - declared")
        if not isinstance(detail.get("items"), list):
            issues.append(f"contentGoalOverages.details.{key}.items must be an array")
        if key in {"pages", "products", "posts"} and not as_list(detail.get("items")):
            issues.append(f"contentGoalOverages.details.{key}.items must list generated content items")
        if not isinstance(detail.get("likelyExtraItems"), list):
            issues.append(f"contentGoalOverages.details.{key}.likelyExtraItems must be an array")
    if warned_keys and overages.get("present") is not True:
        issues.append("contentGoalOverages.present must be true when exceeds_declared_content_goal warnings exist")


def validate_wiki_review(brief: dict[str, Any], issues: list[str]) -> None:
    wiki_review = brief.get("wikiReview")
    if not isinstance(wiki_review, dict):
        issues.append("wikiReview must be an object")
        return
    for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
        if not isinstance(wiki_review.get(key), str):
            issues.append(f"wikiReview.{key} must be a string")
    if brief.get("reviewReady") is not True:
        return
    source_wiki = wiki_review.get("sourceWiki", "")
    markdown_manifest = wiki_review.get("sourceWikiMarkdown", "")
    markdown_index = wiki_review.get("sourceWikiMarkdownIndex", "")
    if not source_wiki:
        issues.append("wikiReview.sourceWiki is required when reviewReady is true")
    if not markdown_manifest:
        issues.append("wikiReview.sourceWikiMarkdown is required when reviewReady is true")
    if not markdown_index:
        issues.append("wikiReview.sourceWikiMarkdownIndex is required when reviewReady is true")
        return
    index_path = Path(markdown_index).expanduser()
    if not index_path.exists():
        issues.append("wikiReview.sourceWikiMarkdownIndex must point to an existing Markdown file when reviewReady is true")
        return
    if index_path.suffix.lower() != ".md":
        issues.append("wikiReview.sourceWikiMarkdownIndex must be a Markdown .md file")
        return
    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        issues.append(f"wikiReview.sourceWikiMarkdownIndex is not readable: {exc}")
        return
    if len(content.strip()) < 20 or "#" not in content:
        issues.append("wikiReview.sourceWikiMarkdownIndex must be a readable Markdown wiki index")


def validate_source_review_objective_coverage(brief: dict[str, Any], issues: list[str]) -> None:
    coverage = brief.get("sourceReviewObjectiveCoverage")
    if not isinstance(coverage, dict):
        if brief.get("reviewReady") is True:
            issues.append("sourceReviewObjectiveCoverage must be an object when reviewReady is true")
        return
    for key in ("json", "readyForBrowserStage"):
        if not isinstance(coverage.get(key), str):
            issues.append(f"sourceReviewObjectiveCoverage.{key} must be a string")
    for key in ("reviewComplete", "complete", "remoteMutationAllowed"):
        if not isinstance(coverage.get(key), bool):
            issues.append(f"sourceReviewObjectiveCoverage.{key} must be boolean")
    for key in ("missingForReview", "missingForFinal"):
        if not isinstance(coverage.get(key), list):
            issues.append(f"sourceReviewObjectiveCoverage.{key} must be an array")
    if brief.get("reviewReady") is not True:
        return
    if not coverage.get("json"):
        issues.append("sourceReviewObjectiveCoverage.json is required when reviewReady is true")
    if coverage.get("reviewComplete") is not True:
        issues.append("sourceReviewObjectiveCoverage.reviewComplete must be true when reviewReady is true")
    if coverage.get("complete") is not False:
        issues.append("sourceReviewObjectiveCoverage.complete must be false before final live acceptance")
    if coverage.get("remoteMutationAllowed") is not False:
        issues.append("sourceReviewObjectiveCoverage.remoteMutationAllowed must be false before final live acceptance")
    if coverage.get("readyForBrowserStage") != "waiting_for_user_content_confirmation":
        issues.append("sourceReviewObjectiveCoverage.readyForBrowserStage must be waiting_for_user_content_confirmation")
    if as_list(coverage.get("missingForReview")):
        issues.append("sourceReviewObjectiveCoverage.missingForReview must be empty when reviewReady is true")
    if "remote_site_creation_not_started" not in as_list(coverage.get("missingForFinal")):
        issues.append("sourceReviewObjectiveCoverage.missingForFinal must include remote_site_creation_not_started")


def validate_commands(brief: dict[str, Any], issues: list[str]) -> None:
    commands = brief.get("commands")
    if not isinstance(commands, dict):
        issues.append("commands must be an object")
        return
    status = brief.get("status")
    confirmation_command = commands.get("confirmationCommandTemplate")
    execution_command = commands.get("confirmedExecutionCommandTemplate")
    if status == "waiting_for_user_content_confirmation":
        if not isinstance(confirmation_command, str) or "make_source_package_confirmation.py" not in confirmation_command:
            issues.append("waiting confirmation brief must include confirmationCommandTemplate")
        if not isinstance(execution_command, str) or "prepare_confirmed_site_execution.py" not in execution_command:
            issues.append("waiting confirmation brief must include confirmedExecutionCommandTemplate")
        if isinstance(confirmation_command, str) and "--user-confirmation-text '<paste current user confirmation text here>'" not in confirmation_command:
            issues.append("confirmationCommandTemplate must keep user confirmation placeholder")
        if isinstance(execution_command, str) and "--user-confirmation-text '<paste current user confirmation text here>'" not in execution_command:
            issues.append("confirmedExecutionCommandTemplate must keep user confirmation placeholder")
    if status == "confirmed_execution_prepared":
        if not isinstance(commands.get("createActionGateOutput"), str):
            issues.append("confirmed execution brief must carry createActionGateOutput field")


def validate_execution_intake(brief: dict[str, Any], issues: list[str]) -> None:
    intake = brief.get("executionIntake")
    if not isinstance(intake, dict):
        issues.append("executionIntake must be an object")
        return
    mode = intake.get("mode")
    if mode not in {
        "refine_source_wiki",
        "await_user_confirmation_text",
        "collect_create_preflight",
        "run_gated_create_site",
    }:
        issues.append("executionIntake.mode must be a known mode")
    for key in ("requiresUserConfirmationText", "requiresCreatePreflight", "readyForGatedCreateSiteRunbook"):
        if not isinstance(intake.get(key), bool):
            issues.append(f"executionIntake.{key} must be boolean")
    for key in (
        "sourcePackage",
        "reviewPacket",
        "sourceConfirmationBrief",
        "confirmationOutput",
        "confirmedExecutionOutputDir",
        "createPreflightTarget",
        "createSiteHandoff",
        "createSiteRunbook",
        "createdSiteEvidenceBundle",
        "createActionGateOutput",
        "nextCommandTemplate",
    ):
        if not isinstance(intake.get(key), str):
            issues.append(f"executionIntake.{key} must be a string")
    checks = as_list(intake.get("adversarialChecks"))
    if not checks or not all(isinstance(item, str) and item.strip() for item in checks):
        issues.append("executionIntake.adversarialChecks must contain non-empty strings")
    if not any("not" in item.lower() and "authorization" in item.lower() for item in checks):
        issues.append("executionIntake.adversarialChecks must state it is not authorization")

    status = brief.get("status")
    ready_stage = brief.get("readyForBrowserStage")
    if status == "needs_source_wiki_refinement":
        if mode != "refine_source_wiki":
            issues.append("executionIntake.mode must be refine_source_wiki when source wiki refinement is needed")
        if intake.get("requiresUserConfirmationText") is not False:
            issues.append("executionIntake.requiresUserConfirmationText must be false before review-ready confirmation")
    elif status == "waiting_for_user_content_confirmation":
        if mode != "await_user_confirmation_text":
            issues.append("executionIntake.mode must be await_user_confirmation_text while waiting for confirmation")
        if intake.get("requiresUserConfirmationText") is not True:
            issues.append("executionIntake.requiresUserConfirmationText must be true while waiting for confirmation")
        if not intake.get("sourcePackage"):
            issues.append("executionIntake.sourcePackage is required while waiting for confirmation")
        if not intake.get("reviewPacket"):
            issues.append("executionIntake.reviewPacket is required while waiting for confirmation")
        if "prepare_confirmed_site_execution.py" not in intake.get("nextCommandTemplate", ""):
            issues.append("executionIntake.nextCommandTemplate must prepare confirmed execution while waiting for confirmation")
    elif status == "confirmed_execution_prepared":
        if intake.get("requiresUserConfirmationText") is not False:
            issues.append("executionIntake.requiresUserConfirmationText must be false after confirmation is prepared")
        if ready_stage == "needs_create_site_preflight":
            if mode != "collect_create_preflight":
                issues.append("executionIntake.mode must be collect_create_preflight when create preflight is missing")
            if intake.get("requiresCreatePreflight") is not True:
                issues.append("executionIntake.requiresCreatePreflight must be true when create preflight is missing")
            if not intake.get("createPreflightTarget"):
                issues.append("executionIntake.createPreflightTarget is required when create preflight is missing")
        elif ready_stage == "create_site_handoff_ready":
            if mode != "run_gated_create_site":
                issues.append("executionIntake.mode must be run_gated_create_site when create-site handoff is ready")
            if intake.get("readyForGatedCreateSiteRunbook") is not True:
                issues.append("executionIntake.readyForGatedCreateSiteRunbook must be true when handoff is ready")
            if not intake.get("createSiteRunbook"):
                issues.append("executionIntake.createSiteRunbook is required when handoff is ready")
            if not intake.get("createdSiteEvidenceBundle"):
                issues.append("executionIntake.createdSiteEvidenceBundle is required when handoff is ready")


def validate_confirmation_decision_matrix(brief: dict[str, Any], issues: list[str]) -> None:
    fields = [item for item in as_list(brief.get("confirmationFields")) if isinstance(item, str) and item.strip()]
    accepted = {item for item in as_list(brief.get("suggestedAcceptedFields")) if isinstance(item, str) and item.strip()}
    deferrals = {
        item.get("field"): item
        for item in as_list(brief.get("suggestedAcceptedDeferrals"))
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
    matrix = brief.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list):
        issues.append("confirmationDecisionMatrix must be an array")
        return
    rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(matrix):
        if not isinstance(row, dict):
            issues.append(f"confirmationDecisionMatrix[{index}] must be an object")
            continue
        field = row.get("field")
        if not isinstance(field, str) or not field.strip():
            issues.append(f"confirmationDecisionMatrix[{index}].field is required")
            continue
        if field in rows:
            issues.append(f"confirmationDecisionMatrix duplicate field {field}")
        rows[field] = row
        decision = row.get("decision")
        if decision not in {"accept", "defer"}:
            issues.append(f"confirmationDecisionMatrix[{field}].decision must be accept or defer")
        if row.get("blocksRemoteMutation") is not False:
            issues.append(f"confirmationDecisionMatrix[{field}].blocksRemoteMutation must be false after suggested decisions cover the field")
        if decision == "accept" and field not in accepted:
            issues.append(f"confirmationDecisionMatrix[{field}] accept decision must be backed by suggestedAcceptedFields")
        if decision == "defer":
            deferral = deferrals.get(field)
            if not isinstance(deferral, dict):
                issues.append(f"confirmationDecisionMatrix[{field}] defer decision must be backed by suggestedAcceptedDeferrals")
            elif row.get("deferDecision") != deferral.get("decision"):
                issues.append(f"confirmationDecisionMatrix[{field}].deferDecision must match suggested deferral decision")
    missing = sorted(set(fields) - set(rows))
    extra = sorted(set(rows) - set(fields))
    if missing:
        issues.append("confirmationDecisionMatrix missing fields: " + ", ".join(missing))
    if extra:
        issues.append("confirmationDecisionMatrix contains fields outside confirmationFields: " + ", ".join(extra))
    uncovered = sorted(set(fields) - accepted - set(deferrals))
    if uncovered:
        issues.append("confirmationFields not covered by accepted fields or deferrals: " + ", ".join(uncovered))


def validate_gate(brief: dict[str, Any], issues: list[str]) -> None:
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if brief.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    gate = brief.get("gate")
    if not isinstance(gate, dict):
        issues.append("gate must be an object")
        return
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
        ("mustNotCreateSaveUploadPublish", True),
    ):
        if gate.get(key) is not expected:
            issues.append(f"gate.{key} must be {str(expected).lower()}")


def validate_brief(brief: dict[str, Any], summary: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if brief.get("kind") != "allincms_source_confirmation_brief":
        issues.append("kind must be allincms_source_confirmation_brief")
    parse_time(brief.get("generatedAt"), "generatedAt", issues)
    status = brief.get("status")
    if status not in STATUSES:
        issues.append("status must be a known source confirmation brief status")
    if not isinstance(brief.get("reviewReady"), bool):
        issues.append("reviewReady must be boolean")
    if not isinstance(brief.get("confirmationPrepared"), bool):
        issues.append("confirmationPrepared must be boolean")
    if not isinstance(brief.get("readyForBrowserStage"), str):
        issues.append("readyForBrowserStage must be a string")
    if not isinstance(brief.get("nextBlockingRequirement"), str):
        issues.append("nextBlockingRequirement must be a string")
    if not isinstance(brief.get("userConfirmationPrompt"), str) or not brief["userConfirmationPrompt"].strip():
        issues.append("userConfirmationPrompt is required")
    validate_gate(brief, issues)
    validate_counts(brief.get("counts"), issues)
    validate_coverage(brief, issues)
    validate_content_quality(brief, issues)
    validate_content_goal_overages(brief, issues)
    validate_wiki_review(brief, issues)
    validate_source_review_objective_coverage(brief, issues)
    validate_commands(brief, issues)
    validate_execution_intake(brief, issues)
    validate_confirmation_decision_matrix(brief, issues)

    next_actions = as_list(brief.get("nextActions"))
    if not next_actions or not all(isinstance(item, str) and item.strip() for item in next_actions):
        issues.append("nextActions must contain non-empty strings")
    checks = as_list(brief.get("adversarialChecks"))
    if not checks or not all(isinstance(item, str) and item.strip() for item in checks):
        issues.append("adversarialChecks must contain non-empty strings")
    if not any("not" in item.lower() and "authorization" in item.lower() for item in checks):
        issues.append("adversarialChecks must state the brief is not authorization")

    if status == "needs_source_wiki_refinement" and brief.get("reviewReady") is True:
        issues.append("needs_source_wiki_refinement status requires reviewReady=false")
    if status == "waiting_for_user_content_confirmation" and brief.get("confirmationPrepared") is True:
        issues.append("waiting_for_user_content_confirmation requires confirmationPrepared=false")
    if status == "confirmed_execution_prepared" and brief.get("confirmationPrepared") is not True:
        issues.append("confirmed_execution_prepared requires confirmationPrepared=true")

    objective = as_dict(brief.get("objectiveAudit"))
    if objective.get("complete") is True:
        issues.append("objectiveAudit.complete must stay false for confirmation brief")
    if brief.get("nextBlockingRequirement") != objective.get("nextBlockingRequirement"):
        issues.append("nextBlockingRequirement must match objectiveAudit.nextBlockingRequirement")

    if summary is not None:
        if summary.get("kind") != "allincms_source_file_rehearsal_summary":
            issues.append("summary kind must be allincms_source_file_rehearsal_summary")
        if brief.get("reviewReady") is not (summary.get("reviewReady") is True):
            issues.append("reviewReady must match source rehearsal summary")
        if brief.get("confirmationPrepared") is not (summary.get("confirmationPrepared") is True):
            issues.append("confirmationPrepared must match source rehearsal summary")
        ready = summary.get("readyForBrowserStage")
        if isinstance(ready, str) and brief.get("readyForBrowserStage") != ready:
            issues.append("readyForBrowserStage must match source rehearsal summary")
        review = as_dict(summary.get("confirmationReview"))
        if brief.get("reviewReady") is True and brief.get("reviewPacket") != review.get("reviewPacket"):
            issues.append("reviewPacket must match confirmationReview.reviewPacket")
        audit = as_dict(summary.get("objectiveAudit"))
        if brief.get("nextBlockingRequirement") != audit.get("nextBlockingRequirement"):
            issues.append("nextBlockingRequirement must match summary objectiveAudit")
        if brief.get("counts") != as_dict(review.get("counts")):
            issues.append("counts must match confirmationReview.counts")
        if brief.get("contentGoalCoverage") != as_dict(review.get("contentGoalCoverage")):
            issues.append("contentGoalCoverage must match confirmationReview.contentGoalCoverage")
        if brief.get("contentQualityReview") != as_dict(review.get("contentQualityReview")):
            issues.append("contentQualityReview must match confirmationReview.contentQualityReview")
        if brief.get("contentGoalOverages") != as_dict(review.get("contentGoalOverages")):
            issues.append("contentGoalOverages must match confirmationReview.contentGoalOverages")
        summary_review_objective = as_dict(summary.get("sourceReviewObjectiveCoverage"))
        brief_review_objective = as_dict(brief.get("sourceReviewObjectiveCoverage"))
        if brief.get("reviewReady") is True:
            for key in ("json", "reviewComplete", "complete", "remoteMutationAllowed", "readyForBrowserStage", "missingForReview", "missingForFinal"):
                if brief_review_objective.get(key) != summary_review_objective.get(key):
                    issues.append(f"sourceReviewObjectiveCoverage.{key} must match source rehearsal summary")
        expected_matrix_fields = {item for item in as_list(review.get("confirmationFields")) if isinstance(item, str)}
        actual_matrix_fields = {
            item.get("field")
            for item in as_list(brief.get("confirmationDecisionMatrix"))
            if isinstance(item, dict) and isinstance(item.get("field"), str)
        }
        if actual_matrix_fields != expected_matrix_fields:
            issues.append("confirmationDecisionMatrix fields must match confirmationReview.confirmationFields")
        summary_artifacts = as_dict(summary.get("artifacts"))
        for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
            if as_dict(brief.get("wikiReview")).get(key) != summary_artifacts.get(key):
                issues.append(f"wikiReview.{key} must match summary artifacts.{key}")
        if brief.get("reviewReady") is True and brief_review_objective.get("json") != summary_artifacts.get("sourceReviewObjectiveCoverage", ""):
            issues.append("sourceReviewObjectiveCoverage.json must match summary artifacts.sourceReviewObjectiveCoverage")
        intake = as_dict(brief.get("executionIntake"))
        if intake.get("sourcePackage") != summary_artifacts.get("sourceSitePackage", ""):
            issues.append("executionIntake.sourcePackage must match summary artifacts.sourceSitePackage")
        if intake.get("reviewPacket") != as_dict(summary.get("confirmationReview")).get("reviewPacket", ""):
            issues.append("executionIntake.reviewPacket must match confirmationReview.reviewPacket")
        for brief_key, summary_key in (
            ("createPreflightTarget", "confirmedCreateSitePreflightTarget"),
            ("createSiteHandoff", "confirmedCreateSiteHandoff"),
            ("createSiteRunbook", "confirmedCreateSiteRunbook"),
            ("createdSiteEvidenceBundle", "confirmedCreatedSiteEvidenceBundle"),
        ):
            if intake.get(brief_key) != summary_artifacts.get(summary_key, ""):
                issues.append(f"executionIntake.{brief_key} must match summary artifacts.{summary_key}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source confirmation brief.")
    parser.add_argument("brief")
    parser.add_argument("--summary", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    brief_path = Path(args.brief).expanduser().resolve()
    summary = load_json(Path(args.summary).expanduser().resolve(), "source rehearsal summary") if args.summary else None
    issues = validate_brief(load_json(brief_path, "source confirmation brief"), summary)
    result = {
        "kind": "allincms_source_confirmation_brief_validation",
        "brief": str(brief_path),
        "summary": str(Path(args.summary).expanduser().resolve()) if args.summary else "",
        "ok": not issues,
        "issues": issues,
    }
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Source confirmation brief validation passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
