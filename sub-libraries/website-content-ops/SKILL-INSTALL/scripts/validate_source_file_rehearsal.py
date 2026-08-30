#!/usr/bin/env python3
"""Validate a local source-file rehearsal summary before browser continuation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any

from validate_source_confirmation_brief import validate_brief
from validate_source_package_review_packet import validate_review_packet
from validate_source_site_package import validate_package


SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cookie|authorization|next-action|next-router-state-tree)\s*[:=]", re.IGNORECASE),
    re.compile(r"\bbearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} root must be an object")
    return data


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(walk_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(walk_strings(item))
        return out
    return []


def safe_strings_for_sensitive_scan(value: Any, key: str = "") -> list[str]:
    allowed_keys = {
        "adversarialChecks",
        "authorizationRecordCommand",
        "blockedRemoteActions",
        "confirmationCommandTemplate",
        "confirmationValidationCommandTemplate",
        "confirmedExecutionCommandTemplate",
        "createActionGateOutput",
        "nextAction",
        "nextActions",
        "suggestedAuthorizationText",
        "suggestedConfirmationText",
        "userConfirmationPrompt",
    }
    if key in allowed_keys:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for child_key, item in value.items():
            out.extend(safe_strings_for_sensitive_scan(item, str(child_key)))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(safe_strings_for_sensitive_scan(item, key))
        return out
    return []


def existing_file(path: str) -> bool:
    return bool(path) and Path(path).expanduser().exists()


def parse_time(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label} must be an ISO 8601 timestamp")


def require_bool(data: dict[str, Any], key: str, expected: bool, issues: list[str]) -> None:
    if data.get(key) is not expected:
        issues.append(f"{key} must be {str(expected).lower()}")


def require_existing_artifact(artifacts: dict[str, Any], key: str, issues: list[str]) -> str:
    value = artifacts.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"artifacts.{key} is required")
        return ""
    if not existing_file(value):
        issues.append(f"artifacts.{key} must point to an existing file")
    return value


def first_blocked_requirement(audit: dict[str, Any]) -> str:
    for item in as_list(audit.get("checks")):
        if not isinstance(item, dict):
            continue
        if item.get("status") in {"missing", "blocked", "not_started", "not_proven"}:
            requirement = item.get("requirement")
            return requirement if isinstance(requirement, str) else ""
    return ""


def expected_stage(summary: dict[str, Any]) -> str:
    if summary.get("confirmationPrepared") is True:
        return str(summary.get("readyForBrowserStage", ""))
    if summary.get("reviewReady") is True:
        return "waiting_for_user_content_confirmation"
    return "needs_source_wiki_refinement"


def validate_confirmation_surface(summary: dict[str, Any], summary_path: Path, issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    brief_meta = as_dict(summary.get("confirmationBrief"))
    brief_path = str(brief_meta.get("json") or artifacts.get("sourceConfirmationBrief") or "")
    markdown_path = str(brief_meta.get("markdown") or artifacts.get("sourceConfirmationBriefMarkdown") or "")
    validation_path = str(brief_meta.get("validation") or artifacts.get("sourceConfirmationBriefValidation") or "")
    if not brief_path:
        issues.append("confirmationBrief.json or artifacts.sourceConfirmationBrief is required")
        return
    if not existing_file(brief_path):
        issues.append("confirmation brief JSON must exist")
        return
    try:
        brief = load_json(Path(brief_path), "confirmation brief")
    except ValueError as exc:
        issues.append(str(exc))
        return
    for issue in validate_brief(brief, summary):
        issues.append(f"confirmation brief invalid: {issue}")
    if not markdown_path or not existing_file(markdown_path):
        issues.append("confirmation brief Markdown must exist")
    if not validation_path or not existing_file(validation_path):
        issues.append("confirmation brief validation must exist")
    else:
        try:
            validation = load_json(Path(validation_path), "confirmation brief validation")
        except ValueError as exc:
            issues.append(str(exc))
        else:
            if validation.get("ok") is not True:
                issues.append("confirmation brief validation must have ok=true")
            if validation.get("summary") not in {str(summary_path), str(summary_path.resolve())}:
                issues.append("confirmation brief validation should bind to the rehearsal summary path")


def validate_rehearsal_validation_artifact(summary: dict[str, Any], summary_path: Path, issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    validation_path = artifacts.get("sourceFileRehearsalValidation")
    if not isinstance(validation_path, str) or not validation_path.strip():
        return
    if not existing_file(validation_path):
        issues.append("artifacts.sourceFileRehearsalValidation must point to an existing file when present")
        return
    try:
        validation = load_json(Path(validation_path), "source-file rehearsal validation")
    except ValueError as exc:
        issues.append(str(exc))
        return
    if validation.get("kind") != "allincms_source_file_rehearsal_validation":
        issues.append("source-file rehearsal validation kind is invalid")
    if validation.get("ok") is not True:
        issues.append("source-file rehearsal validation artifact must have ok=true")
    if validation.get("summary") not in {str(summary_path), str(summary_path.resolve())}:
        issues.append("source-file rehearsal validation must bind to the rehearsal summary path")


def validate_review_ready_artifacts(summary: dict[str, Any], issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    review = as_dict(summary.get("confirmationReview"))
    coverage_meta = as_dict(summary.get("sourceReviewObjectiveCoverage"))
    package_path = str(artifacts.get("sourceSitePackage") or "")
    review_packet_path = str(artifacts.get("reviewPacket") or "")
    if summary.get("reviewReady") is not True:
        if review.get("available") is True:
            issues.append("confirmationReview.available must be false when reviewReady=false")
        if coverage_meta.get("json") or artifacts.get("sourceReviewObjectiveCoverage"):
            issues.append("sourceReviewObjectiveCoverage must be empty when reviewReady=false")
        return

    if review.get("available") is not True:
        issues.append("confirmationReview.available must be true when reviewReady=true")
    if review.get("reviewPacket") != review_packet_path:
        issues.append("confirmationReview.reviewPacket must match artifacts.reviewPacket")
    if not package_path or not existing_file(package_path):
        issues.append("review-ready summary must point to an existing sourceSitePackage")
        return
    if not review_packet_path or not existing_file(review_packet_path):
        issues.append("review-ready summary must point to an existing reviewPacket")
        return
    try:
        package = load_json(Path(package_path), "source-site package")
        review_packet = load_json(Path(review_packet_path), "review packet")
    except ValueError as exc:
        issues.append(str(exc))
        return
    for issue in validate_package(package, require_complete=True, require_publication_ready=True):
        issues.append(f"source-site package invalid: {issue}")
    for issue in validate_review_packet(review_packet, package):
        issues.append(f"review packet invalid: {issue}")
    for key in ("counts", "contentGoalCoverage", "contentQualityReview"):
        if review.get(key) != review_packet.get(key):
            issues.append(f"confirmationReview.{key} must match review packet")
    coverage_path = str(coverage_meta.get("json") or artifacts.get("sourceReviewObjectiveCoverage") or "")
    if not coverage_path:
        issues.append("sourceReviewObjectiveCoverage.json or artifacts.sourceReviewObjectiveCoverage is required when reviewReady=true")
        return
    if not existing_file(coverage_path):
        issues.append("sourceReviewObjectiveCoverage JSON must exist when reviewReady=true")
        return
    try:
        coverage = load_json(Path(coverage_path), "source review objective coverage")
    except ValueError as exc:
        issues.append(str(exc))
        return
    if coverage.get("kind") != "allincms_source_review_objective_coverage":
        issues.append("sourceReviewObjectiveCoverage kind is invalid")
    if coverage.get("reviewComplete") is not True:
        issues.append("sourceReviewObjectiveCoverage.reviewComplete must be true when reviewReady=true")
    if coverage.get("complete") is not False:
        issues.append("sourceReviewObjectiveCoverage.complete must remain false before live browser completion")
    if coverage.get("remoteMutationAllowed") is not False:
        issues.append("sourceReviewObjectiveCoverage.remoteMutationAllowed must be false")
    if coverage.get("readyForBrowserStage") != "waiting_for_user_content_confirmation":
        issues.append("sourceReviewObjectiveCoverage.readyForBrowserStage must be waiting_for_user_content_confirmation")
    if coverage.get("reviewPacket") and not same_path(coverage.get("reviewPacket"), review_packet_path):
        issues.append("sourceReviewObjectiveCoverage.reviewPacket must bind to artifacts.reviewPacket")
    if coverage.get("sourcePackage") and not same_path(coverage.get("sourcePackage"), package_path):
        issues.append("sourceReviewObjectiveCoverage.sourcePackage must bind to artifacts.sourceSitePackage")
    if as_list(coverage.get("missingForReview")):
        issues.append("sourceReviewObjectiveCoverage.missingForReview must be empty when reviewReady=true")
    if "remote_site_creation_not_started" not in as_list(coverage.get("missingForFinal")):
        issues.append("sourceReviewObjectiveCoverage.missingForFinal must include remote_site_creation_not_started")
    if coverage_meta:
        for key in ("reviewComplete", "complete", "readyForBrowserStage", "remoteMutationAllowed"):
            if coverage_meta.get(key) != coverage.get(key):
                issues.append(f"sourceReviewObjectiveCoverage.{key} must match coverage artifact")
        if coverage_meta.get("missingForReview") != coverage.get("missingForReview"):
            issues.append("sourceReviewObjectiveCoverage.missingForReview must match coverage artifact")
        if coverage_meta.get("missingForFinal") != coverage.get("missingForFinal"):
            issues.append("sourceReviewObjectiveCoverage.missingForFinal must match coverage artifact")


def validate_confirmed_artifacts(summary: dict[str, Any], issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    confirmed = as_dict(summary.get("confirmedExecution"))
    if summary.get("confirmationPrepared") is not True:
        return
    for key in ("confirmedExecutionSummary", "confirmedSourceExecutionStatus", "confirmedSourceNextStageHandoff"):
        require_existing_artifact(artifacts, key, issues)
    if confirmed.get("prepared") is not True:
        issues.append("confirmedExecution.prepared must be true when confirmationPrepared=true")
    if confirmed.get("readyForBrowserStage") != summary.get("readyForBrowserStage"):
        issues.append("confirmedExecution.readyForBrowserStage must match summary.readyForBrowserStage")
    if summary.get("readyForBrowserStage") == "create_site_handoff_ready":
        validate_create_site_handoff_ready_artifacts(summary, issues)
    elif summary.get("readyForBrowserStage") == "needs_create_site_preflight":
        validate_create_site_preflight_needed_artifacts(summary, issues)


def expected_current_handoff_stage(summary: dict[str, Any]) -> str:
    if summary.get("confirmationPrepared") is True:
        ready = summary.get("readyForBrowserStage")
        if ready == "create_site_handoff_ready":
            return "created_site_binding"
        if ready == "ready_for_existing_site_readonly_refresh":
            return "created_site_binding"
        return "create_site_handoff"
    if summary.get("reviewReady") is True:
        return "confirmation"
    return ""


def validate_current_stage_handoff(summary: dict[str, Any], issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    status_path = require_existing_artifact(artifacts, "sourceExecutionStatus", issues)
    handoff_path = require_existing_artifact(artifacts, "sourceNextStageHandoff", issues)
    if not status_path or not handoff_path:
        return
    try:
        status = load_json(Path(status_path), "current source execution status")
        handoff = load_json(Path(handoff_path), "current source next-stage handoff")
    except ValueError as exc:
        issues.append(str(exc))
        return
    status_stage = status.get("currentStage")
    handoff_stage = handoff.get("currentStage")
    if handoff_stage != status_stage:
        issues.append("artifacts.sourceNextStageHandoff currentStage must match artifacts.sourceExecutionStatus currentStage")
    expected = expected_current_handoff_stage(summary)
    if expected and handoff_stage != expected:
        issues.append(f"artifacts.sourceNextStageHandoff must point to current stage {expected}")
    if handoff.get("status") and not same_path(handoff.get("status"), status_path):
        issues.append("artifacts.sourceNextStageHandoff status must bind to artifacts.sourceExecutionStatus")
    if summary.get("confirmationPrepared") is True:
        confirmed = artifacts.get("confirmedSourceNextStageHandoff")
        if isinstance(confirmed, str) and confirmed.strip() and not same_path(handoff_path, confirmed):
            issues.append("artifacts.sourceNextStageHandoff must use confirmedSourceNextStageHandoff after confirmation")
    elif summary.get("reviewReady") is True:
        refined = artifacts.get("refinedSourceNextStageHandoff")
        if isinstance(refined, str) and refined.strip() and not same_path(handoff_path, refined):
            issues.append("artifacts.sourceNextStageHandoff must use refinedSourceNextStageHandoff after refinement")


def same_path(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str) or not left.strip() or not right.strip():
        return False
    return str(Path(left).expanduser().resolve()) == str(Path(right).expanduser().resolve())


def validate_create_site_handoff_ready_artifacts(summary: dict[str, Any], issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    handoff_path = require_existing_artifact(artifacts, "confirmedCreateSiteHandoff", issues)
    handoff_validation_path = require_existing_artifact(artifacts, "confirmedCreateSiteHandoffValidation", issues)
    runbook_path = require_existing_artifact(artifacts, "confirmedCreateSiteRunbook", issues)
    runbook_validation_path = require_existing_artifact(artifacts, "confirmedCreateSiteRunbookValidation", issues)
    evidence_brief_path = require_existing_artifact(artifacts, "confirmedCreatedSiteEvidenceBrief", issues)
    evidence_bundle_path = require_existing_artifact(artifacts, "confirmedCreatedSiteEvidenceBundle", issues)
    evidence_bundle_validation_path = require_existing_artifact(
        artifacts,
        "confirmedCreatedSiteEvidenceBundleValidation",
        issues,
    )
    evidence_target = str(artifacts.get("confirmedCreatedSiteEvidenceTarget") or "")
    if not evidence_target:
        issues.append("artifacts.confirmedCreatedSiteEvidenceTarget is required when create_site_handoff_ready")
    if not all(
        (
            handoff_path,
            handoff_validation_path,
            runbook_path,
            runbook_validation_path,
            evidence_brief_path,
            evidence_bundle_path,
            evidence_bundle_validation_path,
        )
    ):
        return
    try:
        handoff = load_json(Path(handoff_path), "confirmed create-site handoff")
        handoff_validation = load_json(Path(handoff_validation_path), "confirmed create-site handoff validation")
        runbook = load_json(Path(runbook_path), "confirmed create-site runbook")
        runbook_validation = load_json(Path(runbook_validation_path), "confirmed create-site runbook validation")
        evidence_brief = load_json(Path(evidence_brief_path), "created-site evidence brief")
        evidence_bundle = load_json(Path(evidence_bundle_path), "created-site evidence bundle")
        evidence_bundle_validation = load_json(
            Path(evidence_bundle_validation_path),
            "created-site evidence bundle validation",
        )
    except ValueError as exc:
        issues.append(str(exc))
        return

    if handoff.get("kind") != "allincms_confirmed_create_site_handoff":
        issues.append("confirmedCreateSiteHandoff kind is invalid")
    if handoff_validation.get("kind") != "allincms_confirmed_create_site_handoff_validation":
        issues.append("confirmedCreateSiteHandoffValidation kind is invalid")
    if runbook.get("kind") != "allincms_create_site_browser_runbook":
        issues.append("confirmedCreateSiteRunbook kind is invalid")
    if runbook_validation.get("kind") != "allincms_create_site_browser_runbook_validation":
        issues.append("confirmedCreateSiteRunbookValidation kind is invalid")
    if evidence_brief.get("kind") != "allincms_created_site_evidence_brief":
        issues.append("confirmedCreatedSiteEvidenceBrief kind is invalid")
    if evidence_bundle.get("kind") != "allincms_created_site_evidence_bundle":
        issues.append("confirmedCreatedSiteEvidenceBundle kind is invalid")
    if evidence_bundle_validation.get("kind") != "allincms_created_site_evidence_bundle_validation":
        issues.append("confirmedCreatedSiteEvidenceBundleValidation kind is invalid")

    if handoff_validation.get("valid") is not True or handoff_validation.get("issues") not in ([], None):
        issues.append("confirmedCreateSiteHandoffValidation must be valid with no issues")
    if runbook_validation.get("valid") is not True or runbook_validation.get("issues") not in ([], None):
        issues.append("confirmedCreateSiteRunbookValidation must be valid with no issues")
    if evidence_bundle_validation.get("valid") is not True or evidence_bundle_validation.get("issues") not in ([], None):
        issues.append("confirmedCreatedSiteEvidenceBundleValidation must be valid with no issues")

    if runbook.get("browserStepsExecutable") is not False:
        issues.append("confirmed create-site runbook must keep browserStepsExecutable=false")
    if evidence_bundle.get("browserStepsExecutable") is not False:
        issues.append("confirmed created-site evidence bundle must keep browserStepsExecutable=false")
    if handoff.get("remoteMutationsPerformed") is not False or runbook.get("remoteMutationsPerformed") is not False:
        issues.append("confirmed create-site handoff/runbook must not claim remote mutation")
    if evidence_bundle.get("remoteMutationsPerformed") is not False:
        issues.append("confirmed created-site evidence bundle must not claim remote mutation")

    if not same_path(runbook.get("sourceCreateSiteHandoff"), handoff_path):
        issues.append("confirmed create-site runbook sourceCreateSiteHandoff must bind to artifacts.confirmedCreateSiteHandoff")
    if not same_path(handoff_validation.get("handoff"), handoff_path):
        issues.append("confirmed create-site handoff validation must bind to artifacts.confirmedCreateSiteHandoff")
    if not same_path(runbook_validation.get("runbook"), runbook_path):
        issues.append("confirmed create-site runbook validation must bind to artifacts.confirmedCreateSiteRunbook")
    if not same_path(evidence_brief.get("createSiteHandoff"), handoff_path):
        issues.append("created-site evidence brief createSiteHandoff must bind to artifacts.confirmedCreateSiteHandoff")
    if not same_path(evidence_bundle.get("createSiteHandoff"), handoff_path):
        issues.append("created-site evidence bundle createSiteHandoff must bind to artifacts.confirmedCreateSiteHandoff")
    if not same_path(evidence_bundle.get("runbook"), runbook_path):
        issues.append("created-site evidence bundle runbook must bind to artifacts.confirmedCreateSiteRunbook")
    if not same_path(evidence_bundle.get("createdSiteEvidenceBrief"), evidence_brief_path):
        issues.append("created-site evidence bundle createdSiteEvidenceBrief must bind to artifacts.confirmedCreatedSiteEvidenceBrief")
    if not same_path(evidence_bundle_validation.get("bundle"), evidence_bundle_path):
        issues.append("created-site evidence bundle validation must bind to artifacts.confirmedCreatedSiteEvidenceBundle")

    if evidence_target and not same_path(handoff.get("createdSiteEvidenceOutput"), evidence_target):
        issues.append("confirmed create-site handoff createdSiteEvidenceOutput must match artifacts.confirmedCreatedSiteEvidenceTarget")
    if evidence_target and not same_path(runbook.get("createdSiteEvidenceOutput"), evidence_target):
        issues.append("confirmed create-site runbook createdSiteEvidenceOutput must match artifacts.confirmedCreatedSiteEvidenceTarget")
    if evidence_target and not same_path(evidence_brief.get("createdSiteEvidenceOutput"), evidence_target):
        issues.append("created-site evidence brief createdSiteEvidenceOutput must match artifacts.confirmedCreatedSiteEvidenceTarget")
    if evidence_target and not same_path(evidence_bundle.get("createdSiteEvidenceOutput"), evidence_target):
        issues.append("created-site evidence bundle createdSiteEvidenceOutput must match artifacts.confirmedCreatedSiteEvidenceTarget")

    if handoff.get("contentGoalCoverage") != runbook.get("contentGoalCoverage"):
        issues.append("create-site handoff and runbook contentGoalCoverage must match")
    if handoff.get("contentGoalCoverage") != evidence_bundle.get("contentGoalCoverage"):
        issues.append("create-site handoff and evidence bundle contentGoalCoverage must match")
    if handoff.get("contentCounts") != runbook.get("contentCounts"):
        issues.append("create-site handoff and runbook contentCounts must match")
    if handoff.get("contentCounts") != evidence_bundle.get("contentCounts"):
        issues.append("create-site handoff and evidence bundle contentCounts must match")


def validate_create_site_preflight_needed_artifacts(summary: dict[str, Any], issues: list[str]) -> None:
    artifacts = as_dict(summary.get("artifacts"))
    brief_path = require_existing_artifact(artifacts, "confirmedCreateSitePreflightBrief", issues)
    validation_path = require_existing_artifact(artifacts, "confirmedCreateSitePreflightBriefValidation", issues)
    target = str(artifacts.get("confirmedCreateSitePreflightTarget") or "")
    if not target:
        issues.append("artifacts.confirmedCreateSitePreflightTarget is required when needs_create_site_preflight")
    if not brief_path or not validation_path:
        return
    try:
        brief = load_json(Path(brief_path), "create-site preflight brief")
        validation = load_json(Path(validation_path), "create-site preflight brief validation")
    except ValueError as exc:
        issues.append(str(exc))
        return
    if brief.get("kind") != "allincms_create_site_preflight_brief":
        issues.append("confirmedCreateSitePreflightBrief kind is invalid")
    if validation.get("kind") != "allincms_create_site_preflight_brief_validation":
        issues.append("confirmedCreateSitePreflightBriefValidation kind is invalid")
    if validation.get("valid") is not True or validation.get("issues") not in ([], None):
        issues.append("confirmedCreateSitePreflightBriefValidation must be valid with no issues")
    if not same_path(validation.get("brief"), brief_path):
        issues.append("confirmedCreateSitePreflightBriefValidation must bind to confirmedCreateSitePreflightBrief")
    if target and not same_path(brief.get("preflightOutput"), target):
        issues.append("confirmedCreateSitePreflightBrief preflightOutput must match confirmedCreateSitePreflightTarget")
    if brief.get("remoteMutationsPerformed") is not False or brief.get("isUserAuthorization") is not False:
        issues.append("confirmedCreateSitePreflightBrief must remain read-only and non-authorizing")


def validate_objective_audit(summary: dict[str, Any], issues: list[str]) -> None:
    audit = as_dict(summary.get("objectiveAudit"))
    if not audit:
        issues.append("objectiveAudit is required")
        return
    if audit.get("complete") is not False:
        issues.append("objectiveAudit.complete must remain false for local source-file rehearsal")
    if audit.get("localOnly") is not True:
        issues.append("objectiveAudit.localOnly must be true")
    if audit.get("remoteMutationsPerformed") is not False:
        issues.append("objectiveAudit.remoteMutationsPerformed must be false")
    if audit.get("reviewReady") is not (summary.get("reviewReady") is True):
        issues.append("objectiveAudit.reviewReady must match summary.reviewReady")
    if audit.get("confirmationPrepared") is not (summary.get("confirmationPrepared") is True):
        issues.append("objectiveAudit.confirmationPrepared must match summary.confirmationPrepared")
    if audit.get("readyForBrowserStage") != summary.get("readyForBrowserStage"):
        issues.append("objectiveAudit.readyForBrowserStage must match summary.readyForBrowserStage")
    expected_next = first_blocked_requirement(audit)
    if expected_next and audit.get("nextBlockingRequirement") != expected_next:
        issues.append("objectiveAudit.nextBlockingRequirement must match the first incomplete objective check")
    if not as_list(audit.get("checks")):
        issues.append("objectiveAudit.checks must be a non-empty array")
    for index, check in enumerate(as_list(audit.get("checks"))):
        if not isinstance(check, dict):
            issues.append(f"objectiveAudit.checks[{index}] must be an object")
            continue
        evidence = check.get("evidence")
        if evidence is None:
            continue
        if not isinstance(evidence, list):
            issues.append(f"objectiveAudit.checks[{index}].evidence must be an array when present")
            continue
        for evidence_index, item in enumerate(evidence):
            if not isinstance(item, str) or not item.strip():
                issues.append(f"objectiveAudit.checks[{index}].evidence[{evidence_index}] must be a non-empty string")


def validate_summary(summary: dict[str, Any], summary_path: Path) -> list[str]:
    issues: list[str] = []
    if summary.get("kind") != "allincms_source_file_rehearsal_summary":
        issues.append("kind must be allincms_source_file_rehearsal_summary")
    parse_time(summary.get("generatedAt"), "generatedAt", issues)
    require_bool(summary, "localOnly", True, issues)
    require_bool(summary, "remoteMutationsPerformed", False, issues)
    require_bool(summary, "preparedOnly", True, issues)
    if not isinstance(summary.get("sourceCount"), int) or summary.get("sourceCount", 0) <= 0:
        issues.append("sourceCount must be a positive integer")
    if not isinstance(summary.get("inputFileCount"), int) or summary.get("inputFileCount", 0) <= 0:
        issues.append("inputFileCount must be a positive integer")
    if not isinstance(summary.get("reviewReady"), bool):
        issues.append("reviewReady must be boolean")
    if not isinstance(summary.get("confirmationPrepared"), bool):
        issues.append("confirmationPrepared must be boolean")
    if not isinstance(summary.get("readyForBrowserStage"), str) or not summary["readyForBrowserStage"].strip():
        issues.append("readyForBrowserStage must be a non-empty string")
    if summary.get("readyForBrowserStage") != expected_stage(summary):
        issues.append("readyForBrowserStage does not match reviewReady/confirmationPrepared state")

    artifacts = as_dict(summary.get("artifacts"))
    for key in ("sourcePrepareSummary", "sourceExecutionStatus", "sourceWiki", "sourceWikiMarkdownIndex"):
        require_existing_artifact(artifacts, key, issues)
    validate_current_stage_handoff(summary, issues)
    validate_review_ready_artifacts(summary, issues)
    validate_confirmed_artifacts(summary, issues)
    validate_confirmation_surface(summary, summary_path, issues)
    validate_rehearsal_validation_artifact(summary, summary_path, issues)
    validate_objective_audit(summary, issues)

    if not as_list(summary.get("adversarialChecks")):
        issues.append("adversarialChecks must be a non-empty array")
    if not isinstance(summary.get("nextAction"), str) or not summary["nextAction"].strip():
        issues.append("nextAction must be a non-empty string")
    all_text = "\n".join(safe_strings_for_sensitive_scan(summary))
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(all_text):
            issues.append("summary contains sensitive credential/header/account text")
            break
    return issues


def build_report(summary_path: Path, summary: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    return {
        "kind": "allincms_source_file_rehearsal_validation",
        "generatedAt": now_iso(),
        "summary": str(summary_path),
        "ok": not issues,
        "reviewReady": summary.get("reviewReady"),
        "confirmationPrepared": summary.get("confirmationPrepared"),
        "readyForBrowserStage": summary.get("readyForBrowserStage"),
        "issues": issues,
        "nextAction": (
            "continue from the validated source-file rehearsal boundary"
            if not issues
            else "repair or regenerate the source-file rehearsal artifacts before confirmation or browser work"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source-file rehearsal summary.")
    parser.add_argument("summary")
    parser.add_argument("--output", default="")
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary_path = Path(args.summary).expanduser().resolve()
    try:
        summary = load_json(summary_path, "source-file rehearsal summary")
    except ValueError as exc:
        raise SystemExit(f"ERROR: {exc}") from None
    issues = validate_summary(summary, summary_path)
    report = build_report(summary_path, summary, issues)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif issues:
        print("source-file rehearsal validation failed:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("source-file rehearsal validation passed")
    if issues and args.fail_on_invalid:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
