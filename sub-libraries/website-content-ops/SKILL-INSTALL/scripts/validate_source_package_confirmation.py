#!/usr/bin/env python3
"""Validate user confirmation for a local AllinCMS source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import sys
from typing import Any

from validate_source_site_package import content_goal_coverage, validate_package
from validate_source_package_review_packet import validate_review_packet


REQUIRED_ACCEPTED_FIELDS = {
    "siteProposal.siteName",
    "siteProposal.siteDescription",
    "contentPlan.pages",
    "contentPlan.products",
    "contentPlan.posts",
    "contentPlan.forms",
    "contentPlan.media",
    "contentPlan.siteInfo",
    "contentPlan.navigation",
    "contentPlan.taxonomyPlan",
    "contentPlan.mediaPolicy",
    "contentPlan.contactFormPolicy",
}
DECISION_OR_DEFERRAL_FIELDS = {
    "siteInfo.publicContact",
    "siteInfo.legalCompanyName",
    "domains.customDomain",
    "tracking.trackingCode",
}
REMOTE_ACTION_TERMS = {
    "create_site",
    "upload_products",
    "upload_posts",
    "publish",
    "save_design",
    "bind_route",
}
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cookie|bearer|next-action|next-router-state-tree)\b", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


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


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same_resolved_path(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    if not left.strip() or not right.strip():
        return False
    if left == right:
        return True
    return os.path.realpath(left) == os.path.realpath(right)


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(walk_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(walk_strings(item))
        return out
    return []


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def parse_time(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label} must be an ISO 8601 timestamp")


def package_counts(package: dict[str, Any]) -> dict[str, int]:
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    return {
        "pages": len(plan.get("pages", [])) if isinstance(plan.get("pages"), list) else 0,
        "products": len(plan.get("products", [])) if isinstance(plan.get("products"), list) else 0,
        "posts": len(plan.get("posts", [])) if isinstance(plan.get("posts"), list) else 0,
    }


def confirmation_gate_fields(package: dict[str, Any] | None) -> set[str]:
    if not isinstance(package, dict):
        return set()
    gate = package.get("confirmationGate")
    if not isinstance(gate, dict):
        return set()
    fields = gate.get("fieldsNeedingUserConfirmation")
    return {item for item in as_list(fields) if isinstance(item, str) and item.strip()}


def package_required_accepted_fields(package: dict[str, Any] | None = None) -> set[str]:
    fields = set(REQUIRED_ACCEPTED_FIELDS)
    for field in confirmation_gate_fields(package):
        if field not in DECISION_OR_DEFERRAL_FIELDS:
            fields.add(field)
    return fields


def package_decision_fields(package: dict[str, Any] | None = None) -> set[str]:
    fields = confirmation_gate_fields(package) & DECISION_OR_DEFERRAL_FIELDS
    if not isinstance(package, dict):
        return fields
    plan = package.get("contentPlan")
    site_info = plan.get("siteInfo") if isinstance(plan, dict) and isinstance(plan.get("siteInfo"), dict) else {}
    for package_key, decision_field in (
        ("publicContact", "siteInfo.publicContact"),
        ("legalCompanyName", "siteInfo.legalCompanyName"),
    ):
        value = site_info.get(package_key)
        if isinstance(value, str) and value.strip() in {"requires_user_confirmation", "pending_user_confirmation"}:
            fields.add(decision_field)
    return fields


def accepted_field_set(data: dict[str, Any]) -> set[str]:
    accepted = data.get("acceptedFields")
    if not isinstance(accepted, list):
        return set()
    return {item for item in accepted if isinstance(item, str) and item.strip()}


def accepted_deferral_fields(data: dict[str, Any]) -> set[str]:
    deferrals = data.get("acceptedDeferrals")
    if not isinstance(deferrals, list):
        return set()
    return {
        item.get("field")
        for item in deferrals
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item["field"].strip()
    }


def validate_confirmation_decision_matrix(
    data: dict[str, Any],
    issues: list[str],
    review_packet: dict[str, Any] | None = None,
) -> None:
    accepted = accepted_field_set(data)
    deferrals = {
        item.get("field"): item
        for item in as_list(data.get("acceptedDeferrals"))
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
    if isinstance(review_packet, dict) and isinstance(review_packet.get("confirmationFields"), list):
        fields = [item for item in review_packet["confirmationFields"] if isinstance(item, str) and item.strip()]
    else:
        fields = sorted(accepted | set(deferrals))
    matrix = data.get("confirmationDecisionMatrix")
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
            issues.append(f"confirmationDecisionMatrix[{field}].blocksRemoteMutation must be false after confirmation")
        if decision == "accept" and field not in accepted:
            issues.append(f"confirmationDecisionMatrix[{field}] accept decision must match acceptedFields")
        if decision == "defer":
            deferral = deferrals.get(field)
            if not isinstance(deferral, dict):
                issues.append(f"confirmationDecisionMatrix[{field}] defer decision must match acceptedDeferrals")
            elif row.get("deferDecision") != deferral.get("decision"):
                issues.append(f"confirmationDecisionMatrix[{field}].deferDecision must match acceptedDeferrals decision")
    missing = sorted(set(fields) - set(rows))
    extra = sorted(set(rows) - set(fields))
    if missing:
        issues.append("confirmationDecisionMatrix missing fields: " + ", ".join(missing))
    if extra:
        issues.append("confirmationDecisionMatrix contains fields outside confirmation scope: " + ", ".join(extra))
    if isinstance(review_packet, dict):
        packet_matrix = review_packet.get("confirmationDecisionMatrix")
        if isinstance(packet_matrix, list):
            packet_fields = {
                row.get("field")
                for row in packet_matrix
                if isinstance(row, dict) and isinstance(row.get("field"), str) and row.get("field")
            }
            if packet_fields and set(rows) != packet_fields:
                issues.append("confirmationDecisionMatrix fields must match source review packet confirmationDecisionMatrix fields")


def validate_content_quality_review(value: Any, issues: list[str], label: str = "contentQualityReview") -> None:
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return
    if not isinstance(value.get("readyShape"), bool):
        issues.append(f"{label}.readyShape must be boolean")
    warnings = value.get("warnings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
        issues.append(f"{label}.warnings must be an array of strings")
        warnings = []
    if value.get("reviewRequired") is not bool(warnings):
        issues.append(f"{label}.reviewRequired must equal bool(warnings)")
    counts = value.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append(f"{label}.contentCounts must be an object")


def validate_content_goal_overages(value: Any, issues: list[str], label: str = "contentGoalOverages") -> None:
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return
    if not isinstance(value.get("present"), bool):
        issues.append(f"{label}.present must be boolean")
    details = value.get("details")
    if not isinstance(details, dict):
        issues.append(f"{label}.details must be an object")
        details = {}
    if bool(details) is not (value.get("present") is True):
        issues.append(f"{label}.present must equal bool(details)")
    if not isinstance(value.get("operatorNote"), str) or not value["operatorNote"].strip():
        issues.append(f"{label}.operatorNote is required")
    for key, detail in details.items():
        if not isinstance(key, str) or not key.strip():
            issues.append(f"{label}.details keys must be non-empty strings")
            continue
        if not isinstance(detail, dict):
            issues.append(f"{label}.details.{key} must be an object")
            continue
        for field in ("declared", "actual", "extraCount"):
            if not isinstance(detail.get(field), int) or detail[field] < 0:
                issues.append(f"{label}.details.{key}.{field} must be a non-negative integer")
        if isinstance(detail.get("declared"), int) and isinstance(detail.get("actual"), int) and isinstance(detail.get("extraCount"), int):
            if detail["actual"] - detail["declared"] != detail["extraCount"]:
                issues.append(f"{label}.details.{key}.extraCount must equal actual - declared")
        if not isinstance(detail.get("items"), list):
            issues.append(f"{label}.details.{key}.items must be an array")
        if not isinstance(detail.get("likelyExtraItems"), list):
            issues.append(f"{label}.details.{key}.likelyExtraItems must be an array")
        if not isinstance(detail.get("selectionRule"), str) or not detail["selectionRule"].strip():
            issues.append(f"{label}.details.{key}.selectionRule is required")


def validate_content_goal_overages_for_warnings(
    value: Any,
    quality: Any,
    issues: list[str],
    label: str = "contentGoalOverages",
) -> None:
    if not isinstance(quality, dict):
        return
    warnings = quality.get("warnings")
    if not isinstance(warnings, list):
        return
    required_keys = [
        warning.split(":", 1)[1]
        for warning in warnings
        if isinstance(warning, str) and warning.startswith("exceeds_declared_content_goal:") and ":" in warning
    ]
    if not required_keys:
        return
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object when contentQualityReview has overage warnings")
        return
    if value.get("present") is not True:
        issues.append(f"{label}.present must be true when contentQualityReview has overage warnings")
    details = value.get("details")
    if not isinstance(details, dict):
        issues.append(f"{label}.details must be an object when contentQualityReview has overage warnings")
        return
    for key in required_keys:
        if key not in details:
            issues.append(f"{label}.details.{key} is required for warning exceeds_declared_content_goal:{key}")


def validate_wiki_review(value: Any, issues: list[str], label: str = "wikiReview") -> None:
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return
    for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
        if not isinstance(value.get(key), str) or not value.get(key, "").strip():
            issues.append(f"{label}.{key} is required")
    index = value.get("sourceWikiMarkdownIndex")
    if not isinstance(index, str) or not index.strip():
        return
    index_path = Path(index).expanduser()
    if not index_path.exists():
        issues.append(f"{label}.sourceWikiMarkdownIndex must point to an existing Markdown file")
        return
    if index_path.suffix.lower() != ".md":
        issues.append(f"{label}.sourceWikiMarkdownIndex must be a Markdown .md file")
        return
    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        issues.append(f"{label}.sourceWikiMarkdownIndex is not readable: {exc}")
        return
    if len(content.strip()) < 20 or "#" not in content:
        issues.append(f"{label}.sourceWikiMarkdownIndex must be a readable Markdown wiki index")


SOURCE_REVIEW_OBJECTIVE_COVERAGE_KIND = "allincms_source_review_objective_coverage"
SOURCE_REVIEW_OBJECTIVE_LIVE_BLOCKER_IDS = (
    "remote_site_creation_not_started",
    "schema_capture_not_started",
    "sample_batch_upload_not_started",
    "final_launch_not_started",
)


def validate_source_review_objective_coverage(
    value: Any,
    issues: list[str],
    label: str = "sourceReviewObjectiveCoverage",
) -> None:
    """Structurally validate a carried pre-browser objective coverage summary.

    A carried coverage must prove local review readiness (reviewComplete=true,
    missingForReview=[]) while still keeping the full source-to-live-site
    objective open (complete=false, remoteMutationAllowed=false, and the live
    browser blockers still listed in missingForFinal). This keeps a
    review-complete package from being mistaken for a live target completion
    once it is copied into the confirmed execution chain.
    """
    if not isinstance(value, dict):
        issues.append(f"{label} must be an object")
        return
    if value.get("kind") != SOURCE_REVIEW_OBJECTIVE_COVERAGE_KIND:
        issues.append(f"{label}.kind must be {SOURCE_REVIEW_OBJECTIVE_COVERAGE_KIND}")
    if value.get("reviewComplete") is not True:
        issues.append(f"{label}.reviewComplete must be true")
    if value.get("complete") is not False:
        issues.append(f"{label}.complete must be false")
    if value.get("remoteMutationAllowed") is not False:
        issues.append(f"{label}.remoteMutationAllowed must be false")
    if value.get("remoteMutationsPerformed") is not False:
        issues.append(f"{label}.remoteMutationsPerformed must be false")
    if value.get("localOnly") is not True:
        issues.append(f"{label}.localOnly must be true")
    missing_for_review = value.get("missingForReview")
    if not isinstance(missing_for_review, list):
        issues.append(f"{label}.missingForReview must be an array")
    elif missing_for_review:
        issues.append(f"{label}.missingForReview must be empty for a review-complete coverage")
    missing_for_final = value.get("missingForFinal")
    if not isinstance(missing_for_final, list) or not missing_for_final:
        issues.append(f"{label}.missingForFinal must list the remaining live objective blockers")
    else:
        absent = [item for item in SOURCE_REVIEW_OBJECTIVE_LIVE_BLOCKER_IDS if item not in missing_for_final]
        if absent:
            issues.append(f"{label}.missingForFinal must include live blockers: " + ", ".join(absent))
    review_packet = value.get("reviewPacket")
    if not isinstance(review_packet, str) or not review_packet.strip():
        issues.append(f"{label}.reviewPacket is required")
    source_package = value.get("sourcePackage")
    if not isinstance(source_package, str) or not source_package.strip():
        issues.append(f"{label}.sourcePackage is required")


def validate_confirmation(data: dict[str, Any], package: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_source_site_package_confirmation":
        issues.append("kind must be allincms_source_site_package_confirmation")
    if data.get("localOnly") is not True:
        issues.append("localOnly must be true")
    if data.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if data.get("isRemoteMutationAuthorization") is not False:
        issues.append("isRemoteMutationAuthorization must be false")
    validate_content_quality_review(data.get("contentQualityReview"), issues)
    validate_content_goal_overages(data.get("contentGoalOverages"), issues)
    validate_wiki_review(data.get("wikiReview"), issues)
    if data.get("sourceReviewObjectiveCoverage") is not None:
        validate_source_review_objective_coverage(data.get("sourceReviewObjectiveCoverage"), issues)
    parse_time(data.get("confirmedAt"), "confirmedAt", issues)
    if data.get("confirmedBy") != "user":
        issues.append("confirmedBy must be user")
    source_package = data.get("sourcePackage")
    if not isinstance(source_package, str) or not source_package.strip():
        issues.append("sourcePackage is required")
    package_hash = data.get("sourcePackageSha256")
    if package_hash is not None and (not isinstance(package_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", package_hash)):
        issues.append("sourcePackageSha256 must be a lowercase sha256 hex digest when present")
    source_review_packet = data.get("sourceReviewPacket")
    if not isinstance(source_review_packet, str) or not source_review_packet.strip():
        issues.append("sourceReviewPacket is required")
    packet_hash = data.get("sourceReviewPacketSha256")
    if packet_hash is not None and (not isinstance(packet_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", packet_hash)):
        issues.append("sourceReviewPacketSha256 must be a lowercase sha256 hex digest when present")
    text = data.get("userConfirmationText")
    if not isinstance(text, str) or len(text.strip()) < 12:
        issues.append("userConfirmationText must contain the user's confirmation text")
    accepted = data.get("acceptedFields")
    if not isinstance(accepted, list):
        issues.append("acceptedFields must be an array")
        accepted_set: set[str] = set()
    else:
        accepted_set = accepted_field_set(data)
        missing = sorted(package_required_accepted_fields(package) - accepted_set)
        if missing:
            issues.append("acceptedFields missing required fields: " + ", ".join(missing))
    blocked_remote = data.get("blockedRemoteActionsStillRequireActionAuthorization")
    if not isinstance(blocked_remote, list):
        issues.append("blockedRemoteActionsStillRequireActionAuthorization must be an array")
    else:
        missing_remote = sorted(REMOTE_ACTION_TERMS - {item for item in blocked_remote if isinstance(item, str)})
        if missing_remote:
            issues.append("blocked remote action list missing: " + ", ".join(missing_remote))
    deferrals = data.get("acceptedDeferrals")
    deferral_set = accepted_deferral_fields(data)
    if deferrals is not None:
        if not isinstance(deferrals, list):
            issues.append("acceptedDeferrals must be an array when present")
        else:
            for index, item in enumerate(deferrals):
                if not isinstance(item, dict):
                    issues.append(f"acceptedDeferrals[{index}] must be an object")
                    continue
                if not isinstance(item.get("field"), str) or not item["field"].strip():
                    issues.append(f"acceptedDeferrals[{index}].field is required")
                if not isinstance(item.get("decision"), str) or not item["decision"].strip():
                    issues.append(f"acceptedDeferrals[{index}].decision is required")
                if not isinstance(item.get("reason"), str) or len(item["reason"].strip()) < 8:
                    issues.append(f"acceptedDeferrals[{index}].reason must explain the deferral")
            duplicated = sorted(accepted_set & deferral_set)
            if duplicated:
                issues.append("fields cannot be both accepted and deferred: " + ", ".join(duplicated))
    if package is not None:
        package_errors = validate_package(package, require_complete=True, require_publication_ready=True)
        if package_errors:
            issues.extend("sourcePackage: " + error for error in package_errors)
        expected_coverage = content_goal_coverage(package)
        if data.get("contentGoalCoverage") != expected_coverage:
            issues.append("contentGoalCoverage must match source package coverage")
        expected_counts = package_counts(package)
        confirmed_counts = data.get("confirmedCounts")
        if confirmed_counts != expected_counts:
            issues.append(f"confirmedCounts must match package counts {expected_counts}")
        gate = package.get("confirmationGate") if isinstance(package.get("confirmationGate"), dict) else {}
        blocked = set(gate.get("blockedRemoteActions", [])) if isinstance(gate.get("blockedRemoteActions"), list) else set()
        if blocked_remote and not blocked.issubset(set(blocked_remote)):
            issues.append("confirmation must preserve all package blockedRemoteActions as needing later action authorization")
        decision_fields = package_decision_fields(package)
        missing_decisions = sorted(decision_fields - (accepted_set | deferral_set))
        if missing_decisions:
            issues.append("acceptedFields or acceptedDeferrals missing required decision fields: " + ", ".join(missing_decisions))
    validate_confirmation_decision_matrix(data, issues)
    for value in walk_strings(data):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                issues.append("confirmation contains sensitive credential/header/email/raw-id text")
                return issues
    return issues


def validate_confirmation_with_review_packet(
    data: dict[str, Any],
    package: dict[str, Any] | None = None,
    review_packet: dict[str, Any] | None = None,
) -> list[str]:
    issues = validate_confirmation(data, package)
    if review_packet is None:
        return issues
    if package is None:
        issues.append("package is required when validating sourceReviewPacket binding")
        return issues
    review_issues = validate_review_packet(review_packet, package)
    issues.extend("sourceReviewPacket: " + issue for issue in review_issues)
    package_path = data.get("sourcePackage")
    packet_path = data.get("sourceReviewPacket")
    packet_source_package = review_packet.get("sourcePackage") if isinstance(review_packet, dict) else None
    confirmation_source_package = data.get("sourcePackage")
    if not isinstance(packet_path, str) or not packet_path.strip():
        issues.append("sourceReviewPacket path is required")
    else:
        packet_hash = data.get("sourceReviewPacketSha256")
        if not isinstance(packet_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", packet_hash):
            issues.append("sourceReviewPacketSha256 is required when validating sourceReviewPacket binding")
        else:
            try:
                actual_hash = file_sha256(packet_path)
            except OSError as exc:
                issues.append(f"sourceReviewPacketSha256 could not be verified: {exc}")
            else:
                if actual_hash != packet_hash:
                    issues.append("sourceReviewPacketSha256 must match the current sourceReviewPacket file")
    if not isinstance(package_path, str) or not package_path.strip():
        issues.append("sourcePackage path is required")
    else:
        package_hash = data.get("sourcePackageSha256")
        if not isinstance(package_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", package_hash):
            issues.append("sourcePackageSha256 is required when validating sourcePackage binding")
        else:
            try:
                actual_hash = file_sha256(package_path)
            except OSError as exc:
                issues.append(f"sourcePackageSha256 could not be verified: {exc}")
            else:
                if actual_hash != package_hash:
                    issues.append("sourcePackageSha256 must match the current sourcePackage file")
    if not same_resolved_path(packet_source_package, confirmation_source_package):
        issues.append("sourceReviewPacket.sourcePackage must match confirmation.sourcePackage")
    confirmed_counts = data.get("confirmedCounts")
    packet_counts = review_packet.get("counts") if isinstance(review_packet, dict) else None
    if isinstance(packet_counts, dict):
        expected_counts = {key: packet_counts.get(key) for key in ("pages", "products", "posts")}
        if confirmed_counts != expected_counts:
            issues.append(f"confirmedCounts must match review packet package counts {expected_counts}")
    packet_coverage = review_packet.get("contentGoalCoverage") if isinstance(review_packet, dict) else None
    if packet_coverage is not None and data.get("contentGoalCoverage") != packet_coverage:
        issues.append("contentGoalCoverage must match review packet contentGoalCoverage")
    packet_quality = review_packet.get("contentQualityReview") if isinstance(review_packet, dict) else None
    if packet_quality is not None and data.get("contentQualityReview") != packet_quality:
        issues.append("contentQualityReview must match review packet contentQualityReview")
    packet_overages = review_packet.get("contentGoalOverages") if isinstance(review_packet, dict) else None
    if packet_overages is not None and data.get("contentGoalOverages") != packet_overages:
        issues.append("contentGoalOverages must match review packet contentGoalOverages")
    packet_wiki_review = review_packet.get("wikiReview") if isinstance(review_packet, dict) else None
    if packet_wiki_review is not None and data.get("wikiReview") != packet_wiki_review:
        issues.append("wikiReview must match review packet wikiReview")
    coverage = data.get("sourceReviewObjectiveCoverage")
    if isinstance(coverage, dict):
        if not same_resolved_path(coverage.get("reviewPacket"), packet_path):
            issues.append("sourceReviewObjectiveCoverage.reviewPacket must match confirmation.sourceReviewPacket")
        if not same_resolved_path(coverage.get("sourcePackage"), package_path):
            issues.append("sourceReviewObjectiveCoverage.sourcePackage must match confirmation.sourcePackage")
    packet_fields = review_packet.get("confirmationFields")
    if isinstance(packet_fields, list):
        covered = accepted_field_set(data) | accepted_deferral_fields(data)
        missing_packet_fields = sorted({item for item in packet_fields if isinstance(item, str)} - covered)
        if missing_packet_fields:
            issues.append("confirmation must cover every review packet confirmationField by acceptance or deferral: " + ", ".join(missing_packet_fields))
    validate_confirmation_decision_matrix(data, issues, review_packet)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source package confirmation JSON.")
    parser.add_argument("confirmation")
    parser.add_argument("--package", help="Optional source-site package JSON to bind against")
    parser.add_argument("--review-packet", help="Optional source package review packet JSON to bind against")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    confirmation = load_json(Path(args.confirmation), "confirmation")
    package = load_json(Path(args.package), "package") if args.package else None
    review_packet = load_json(Path(args.review_packet), "review packet") if args.review_packet else None
    issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
    report = {
        "kind": "allincms_source_site_package_confirmation_validation",
        "confirmation": args.confirmation,
        "package": args.package,
        "reviewPacket": args.review_packet,
        "valid": not issues,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        if not args.json:
            print("Source package confirmation validation failed:")
            for issue in issues:
                print(f"- {issue}")
        return 1
    if not args.json:
        print("Source package confirmation validation passed.")
        print("Reminder: this confirms content/package intent only; remote actions still require action-specific authorization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
