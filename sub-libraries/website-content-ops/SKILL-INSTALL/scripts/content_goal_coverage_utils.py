#!/usr/bin/env python3
"""Helpers for carrying source content goal coverage through upload stages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate_source_site_package import content_goal_coverage
from validate_source_package_confirmation import (
    same_resolved_path,
    validate_content_goal_overages,
    validate_content_goal_overages_for_warnings,
    validate_content_quality_review,
    validate_source_review_objective_coverage,
    validate_wiki_review,
)

SOURCE_IDENTITY_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
)
CREATED_SITE_SUBMITTED_VALUE_KEYS = ("name", "description")


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def source_identity_from_artifact(data: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(data, dict):
        return None
    identity: dict[str, str] = {}
    for key in SOURCE_IDENTITY_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value:
            identity[key] = value
    return identity or None


def source_identity_issues(identity: dict[str, str] | None) -> list[str]:
    if identity is None:
        return ["sourcePackageSha256/sourceReviewPacketSha256 missing from source-context artifacts"]
    issues: list[str] = []
    for key in SOURCE_IDENTITY_KEYS:
        value = identity.get(key)
        if not valid_sha256(value):
            issues.append(f"{key} must be a lowercase 64-character sha256")
    return issues


def matching_source_identity(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[dict[str, str] | None, list[str]]:
    identities: list[tuple[str, dict[str, str]]] = []
    for label, data in entries:
        identity = source_identity_from_artifact(data)
        if identity is not None:
            identities.append((label, identity))

    if not identities:
        return None, ["sourcePackageSha256/sourceReviewPacketSha256 missing from source-context artifacts"] if require_when_present else []

    first_label, first = identities[0]
    issues = source_identity_issues(first)
    for label, identity in identities[1:]:
        issues.extend(f"{label}: {issue}" for issue in source_identity_issues(identity))
        if identity != first:
            issues.append(f"sourcePackageSha256/sourceReviewPacketSha256 mismatch between {first_label} and {label}")
    return first, issues


def created_site_submitted_values_from_artifact(data: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(data, dict):
        return None
    values = data.get("createdSiteSubmittedValues")
    return values if isinstance(values, dict) and values else None


def created_site_submitted_values_issues(values: dict[str, Any] | None) -> list[str]:
    if values is None:
        return ["createdSiteSubmittedValues missing from created-site source-context artifacts"]
    issues: list[str] = []
    for key in CREATED_SITE_SUBMITTED_VALUE_KEYS:
        value = values.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"createdSiteSubmittedValues.{key} must be a non-empty string")
    return issues


def matching_created_site_submitted_values(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[dict[str, str] | None, list[str]]:
    values_entries: list[tuple[str, dict[str, str]]] = []
    labels_with_data: list[str] = []
    for label, data in entries:
        if isinstance(data, dict):
            labels_with_data.append(label)
        values = created_site_submitted_values_from_artifact(data)
        if values is not None:
            values_entries.append((label, values))

    if not values_entries:
        return None, ["createdSiteSubmittedValues missing from created-site source-context artifacts"] if require_when_present else []

    first_label, first = values_entries[0]
    issues = created_site_submitted_values_issues(first)
    labels_with_values = {label for label, _ in values_entries}
    for label in labels_with_data:
        if label not in labels_with_values:
            issues.append(f"{label}: createdSiteSubmittedValues is required when present in source context")
    for label, values in values_entries[1:]:
        issues.extend(f"{label}: {issue}" for issue in created_site_submitted_values_issues(values))
        if values != first:
            issues.append(f"createdSiteSubmittedValues mismatch between {first_label} and {label}")
    return first, issues


def load_matching_created_site_submitted_values(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
) -> tuple[dict[str, str] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_created_site_submitted_values(loaded, require_when_present=require_when_any_source)


def load_json_object(path: str, label: str) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def coverage_from_artifact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    coverage = data.get("contentGoalCoverage")
    if isinstance(coverage, dict):
        return coverage
    if data.get("kind") == "allincms_source_site_package":
        return content_goal_coverage(data)
    return None


def coverage_issues(coverage: dict[str, Any] | None) -> list[str]:
    if coverage is None:
        return ["contentGoalCoverage missing from source-context artifacts"]
    issues: list[str] = []
    if coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    checks = coverage.get("checks")
    if not isinstance(checks, dict) or not checks:
        issues.append("contentGoalCoverage.checks must be a non-empty object")
    else:
        for key, value in checks.items():
            if value is not True:
                issues.append(f"contentGoalCoverage.checks.{key} must be true")
    missing = coverage.get("missing")
    if not isinstance(missing, list):
        issues.append("contentGoalCoverage.missing must be an array")
    elif missing:
        issues.append("contentGoalCoverage.missing must be empty")
    counts = coverage.get("counts")
    if not isinstance(counts, dict):
        issues.append("contentGoalCoverage.counts must be an object")
    return issues


def matching_coverage(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    coverages: list[tuple[str, dict[str, Any]]] = []
    for label, data in entries:
        coverage = coverage_from_artifact(data)
        if coverage is not None:
            coverages.append((label, coverage))

    if not coverages:
        return None, ["contentGoalCoverage missing from source-context artifacts"] if require_when_present else []

    first_label, first = coverages[0]
    issues = coverage_issues(first)
    for label, coverage in coverages[1:]:
        if coverage != first:
            issues.append(f"contentGoalCoverage mismatch between {first_label} and {label}")
    return first, issues


def load_matching_coverage(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_coverage(loaded, require_when_present=require_when_any_source)


def source_review_objective_coverage_from_artifact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    coverage = data.get("sourceReviewObjectiveCoverage")
    if isinstance(coverage, dict) and coverage:
        return coverage
    if data.get("kind") == "allincms_source_review_objective_coverage":
        return data
    return None


def source_review_objective_coverage_issues(coverage: dict[str, Any] | None) -> list[str]:
    if coverage is None:
        return ["sourceReviewObjectiveCoverage missing from source-context artifacts"]
    issues: list[str] = []
    validate_source_review_objective_coverage(coverage, issues)
    return issues


# Fields that legitimately differ between two copies of the same carried coverage
# (they are stamped at generation time). Exclude them from cross-artifact equality
# so a re-generated-but-semantically-identical coverage does not read as drift.
SOURCE_REVIEW_OBJECTIVE_COVERAGE_VOLATILE_KEYS = ("generatedAt",)


def source_review_objective_coverage_semantic(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in coverage.items()
        if key not in SOURCE_REVIEW_OBJECTIVE_COVERAGE_VOLATILE_KEYS
    }


def source_review_objective_coverage_binding_issues(
    coverage: dict[str, Any] | None,
    *,
    source_package: Any = None,
    review_packet: Any = None,
    label: str = "sourceReviewObjectiveCoverage",
) -> list[str]:
    """Re-bind a carried coverage to the hosting artifact's own package/review packet.

    The structural validator only requires reviewPacket/sourcePackage be non-empty
    strings. Downstream artifacts (plan, readiness) must additionally prove the
    carried coverage points at the same package/review packet the artifact itself
    references, so a hand-edited coverage cannot smuggle in a different source.
    """
    if not isinstance(coverage, dict):
        return []
    issues: list[str] = []
    if isinstance(source_package, str) and source_package.strip():
        if not same_resolved_path(coverage.get("sourcePackage"), source_package):
            issues.append(f"{label}.sourcePackage must match the artifact sourcePackage")
    if isinstance(review_packet, str) and review_packet.strip():
        if not same_resolved_path(coverage.get("reviewPacket"), review_packet):
            issues.append(f"{label}.reviewPacket must match the artifact sourceReviewPacket")
    return issues


def matching_source_review_objective_coverage(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    coverages: list[tuple[str, dict[str, Any]]] = []
    labels_with_data: list[str] = []
    for label, data in entries:
        if isinstance(data, dict):
            labels_with_data.append(label)
        coverage = source_review_objective_coverage_from_artifact(data)
        if coverage is not None:
            coverages.append((label, coverage))

    if not coverages:
        return None, ["sourceReviewObjectiveCoverage missing from source-context artifacts"] if require_when_present else []

    first_label, first = coverages[0]
    issues = source_review_objective_coverage_issues(first)
    # Once any source-context artifact carries coverage, every present artifact must
    # carry it too; a silent drop (confirmation has it, plan/readiness dropped it)
    # is drift and must be caught here, not only in the export helper.
    labels_with_coverage = {label for label, _ in coverages}
    for label in labels_with_data:
        if label not in labels_with_coverage:
            issues.append(f"{label}: sourceReviewObjectiveCoverage is required when present in source context")
    first_semantic = source_review_objective_coverage_semantic(first)
    for label, coverage in coverages[1:]:
        if source_review_objective_coverage_semantic(coverage) != first_semantic:
            issues.append(f"sourceReviewObjectiveCoverage mismatch between {first_label} and {label}")
    return first, issues


def load_matching_source_review_objective_coverage(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_source_review_objective_coverage(loaded, require_when_present=require_when_any_source)


def quality_from_artifact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    quality = data.get("contentQualityReview")
    return quality if isinstance(quality, dict) and quality else None


def matching_quality_review(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    qualities: list[tuple[str, dict[str, Any]]] = []
    for label, data in entries:
        quality = quality_from_artifact(data)
        if quality is not None:
            qualities.append((label, quality))

    if not qualities:
        return None, ["contentQualityReview missing from source-context artifacts"] if require_when_present else []

    first_label, first = qualities[0]
    issues: list[str] = []
    validate_content_quality_review(first, issues)
    for label, quality in qualities[1:]:
        local_issues: list[str] = []
        validate_content_quality_review(quality, local_issues)
        issues.extend(f"{label}: {issue}" for issue in local_issues)
        if quality != first:
            issues.append(f"contentQualityReview mismatch between {first_label} and {label}")
    return first, issues


def load_matching_quality_review(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_quality_review(loaded, require_when_present=require_when_any_source)


def content_goal_overages_from_artifact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    overages = data.get("contentGoalOverages")
    return overages if isinstance(overages, dict) and overages else None


def matching_content_goal_overages(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
    quality: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    overage_entries: list[tuple[str, dict[str, Any]]] = []
    labels_with_data: list[str] = []
    data_by_label = {label: data for label, data in entries}
    overage_warnings_present = False
    for label, data in entries:
        if isinstance(data, dict):
            labels_with_data.append(label)
            data_quality = data.get("contentQualityReview")
            if isinstance(data_quality, dict):
                warnings = data_quality.get("warnings")
                if isinstance(warnings, list) and any(
                    isinstance(item, str) and item.startswith("exceeds_declared_content_goal:")
                    for item in warnings
                ):
                    overage_warnings_present = True
        overages = content_goal_overages_from_artifact(data)
        if overages is not None:
            overage_entries.append((label, overages))
    if isinstance(quality, dict):
        warnings = quality.get("warnings")
        if isinstance(warnings, list) and any(
            isinstance(item, str) and item.startswith("exceeds_declared_content_goal:")
            for item in warnings
        ):
            overage_warnings_present = True

    if not overage_entries:
        if require_when_present or overage_warnings_present:
            return None, ["contentGoalOverages missing from source-context artifacts"]
        return None, []

    first_label, first = overage_entries[0]
    issues: list[str] = []
    validate_content_goal_overages(first, issues)
    validate_content_goal_overages_for_warnings(first, quality, issues)
    labels_with_overages = {label for label, _ in overage_entries}
    for label, data in entries:
        if not isinstance(data, dict) or label in labels_with_overages:
            continue
        data_quality = data.get("contentQualityReview")
        if require_when_present or overage_warnings_present or (
            isinstance(data_quality, dict) and data_quality.get("warnings")
        ):
            issues.append(f"{label}: contentGoalOverages is required when present in source context")
    for label, overages in overage_entries[1:]:
        local_issues: list[str] = []
        validate_content_goal_overages(overages, local_issues)
        local_quality = data_by_label.get(label)
        validate_content_goal_overages_for_warnings(
            overages,
            local_quality.get("contentQualityReview") if isinstance(local_quality, dict) else quality,
            local_issues,
        )
        issues.extend(f"{label}: {issue}" for issue in local_issues)
        if overages != first:
            issues.append(f"contentGoalOverages mismatch between {first_label} and {label}")
    return first, issues


def load_matching_content_goal_overages(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
    quality: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_content_goal_overages(loaded, require_when_present=require_when_any_source, quality=quality)


def wiki_review_from_artifact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    review = data.get("wikiReview")
    return review if isinstance(review, dict) and review else None


def matching_wiki_review(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    reviews: list[tuple[str, dict[str, Any]]] = []
    for label, data in entries:
        review = wiki_review_from_artifact(data)
        if review is not None:
            reviews.append((label, review))

    if not reviews:
        return None, ["wikiReview missing from source-context artifacts"] if require_when_present else []

    first_label, first = reviews[0]
    issues: list[str] = []
    validate_wiki_review(first, issues)
    for label, review in reviews[1:]:
        local_issues: list[str] = []
        validate_wiki_review(review, local_issues)
        issues.extend(f"{label}: {issue}" for issue in local_issues)
        if review != first:
            issues.append(f"wikiReview mismatch between {first_label} and {label}")
    return first, issues


def load_matching_wiki_review(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_wiki_review(loaded, require_when_present=require_when_any_source)


def confirmation_decision_matrix_from_artifact(data: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not isinstance(data, dict):
        return None
    matrix = data.get("confirmationDecisionMatrix")
    return matrix if isinstance(matrix, list) and matrix else None


def confirmation_decision_matrix_issues(matrix: list[dict[str, Any]] | None) -> list[str]:
    if matrix is None:
        return ["confirmationDecisionMatrix missing from source-context artifacts"]
    issues: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(matrix):
        if not isinstance(row, dict):
            issues.append(f"confirmationDecisionMatrix[{index}] must be an object")
            continue
        field = row.get("field")
        if not isinstance(field, str) or not field.strip():
            issues.append(f"confirmationDecisionMatrix[{index}].field is required")
            continue
        if field in seen:
            issues.append(f"confirmationDecisionMatrix duplicate field {field}")
        seen.add(field)
        if row.get("decision") not in {"accept", "defer"}:
            issues.append(f"confirmationDecisionMatrix[{field}].decision must be accept or defer")
        if row.get("blocksRemoteMutation") is not False:
            issues.append(f"confirmationDecisionMatrix[{field}].blocksRemoteMutation must be false")
        if row.get("decision") == "defer" and not isinstance(row.get("deferDecision"), str):
            issues.append(f"confirmationDecisionMatrix[{field}].deferDecision must be a string")
    return issues


CONFIRMATION_DECISION_SEMANTIC_KEYS = (
    "field",
    "decision",
    "deferDecision",
    "reason",
    "blocksRemoteMutation",
)


def normalized_confirmation_decision_matrix(matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in matrix:
        if not isinstance(row, dict):
            continue
        rows.append({key: row.get(key) for key in CONFIRMATION_DECISION_SEMANTIC_KEYS})
    return sorted(rows, key=lambda item: str(item.get("field") or ""))


def matching_confirmation_decision_matrix(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_when_present: bool = False,
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    matrices: list[tuple[str, list[dict[str, Any]]]] = []
    for label, data in entries:
        matrix = confirmation_decision_matrix_from_artifact(data)
        if matrix is not None:
            matrices.append((label, matrix))

    if not matrices:
        return None, ["confirmationDecisionMatrix missing from source-context artifacts"] if require_when_present else []

    first_label, first = matrices[0]
    issues = confirmation_decision_matrix_issues(first)
    normalized_first = normalized_confirmation_decision_matrix(first)
    for label, matrix in matrices[1:]:
        issues.extend(f"{label}: {issue}" for issue in confirmation_decision_matrix_issues(matrix))
        if normalized_confirmation_decision_matrix(matrix) != normalized_first:
            issues.append(f"confirmationDecisionMatrix mismatch between {first_label} and {label}")
    return first, issues


def load_matching_confirmation_decision_matrix(
    sources: list[tuple[str, str]],
    *,
    require_when_any_source: bool = False,
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any] | None]] = []
    for label, path in sources:
        if path:
            loaded.append((label, load_json_object(path, label)))
    if not loaded:
        return None, []
    return matching_confirmation_decision_matrix(loaded, require_when_present=require_when_any_source)


def matching_content_counts(
    entries: list[tuple[str, dict[str, Any] | None]],
    *,
    require_labels: set[str] | None = None,
) -> tuple[dict[str, int] | None, list[str]]:
    require_labels = require_labels or set()
    counts_entries: list[tuple[str, dict[str, Any]]] = []
    labels_with_data: set[str] = set()
    for label, data in entries:
        if isinstance(data, dict):
            labels_with_data.add(label)
            if isinstance(data.get("contentCounts"), dict):
                counts_entries.append((label, data["contentCounts"]))
    if not counts_entries:
        return None, []
    first_label, first = counts_entries[0]
    issues: list[str] = []
    count_labels = {label for label, _ in counts_entries}
    for label in sorted(require_labels & labels_with_data):
        if label not in count_labels:
            issues.append(f"{label}: contentCounts is required when source contentCounts are present")
    required_keys = ["pages", "products", "posts"]
    optional_keys = ["forms", "media", "navigationItems", "siteInfoFields"]
    for key in optional_keys:
        if any(key in counts for _, counts in counts_entries):
            required_keys.append(key)
    for key in required_keys:
        value = first.get(key)
        if not isinstance(value, int) or value < 0:
            issues.append(f"{first_label}: contentCounts.{key} must be a non-negative integer")
    for label, counts in counts_entries[1:]:
        for key in required_keys:
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"{label}: contentCounts.{key} must be a non-negative integer")
        normalized_first = {key: first.get(key) for key in required_keys}
        normalized_counts = {key: counts.get(key) for key in required_keys}
        if normalized_counts != normalized_first:
            issues.append(f"contentCounts mismatch between {first_label} and {label}")
    return first, issues
