#!/usr/bin/env python3
"""Validate a local review packet for an AllinCMS source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any

from validate_source_site_package import content_goal_coverage, plain_text, validate_package


MAX_PREVIEW_CHARS = 180
COUNTED_SITE_INFO_FIELDS = ("draftSeoTitle", "draftSeoDescription", "publicContact", "legalCompanyName", "logoPolicy")
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cookie|authorization|bearer|next-action|next-router-state-tree)\b", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE),
)
REMOTE_ACTION_TERMS = {"create_site", "upload_products", "upload_posts", "publish", "save_design", "bind_route"}


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


def path_text_present(path_value: str, text: str) -> bool:
    variants = {path_value}
    try:
        resolved = str(Path(path_value).expanduser().resolve())
    except OSError:
        resolved = ""
    if resolved:
        variants.add(resolved)
    for value in list(variants):
        if value.startswith("/private/tmp/"):
            variants.add("/tmp/" + value.removeprefix("/private/tmp/"))
        elif value.startswith("/tmp/"):
            variants.add("/private/tmp/" + value.removeprefix("/tmp/"))
    return any(value and value in text for value in variants)


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
    allowed_command_or_path_keys = {
        "confirmationCommandTemplate",
        "confirmationValidationCommandTemplate",
        "confirmedExecutionCommandTemplate",
        "confirmationOutput",
        "confirmedExecutionOutputDir",
        "createActionGateOutput",
        "nextCommands",
    }
    if key in allowed_command_or_path_keys:
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


def parse_time(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label} must be an ISO 8601 timestamp")


def expected_counts(package: dict[str, Any]) -> dict[str, int]:
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    counts = {
        "pages": len(as_list(plan.get("pages"))),
        "products": len(as_list(plan.get("products"))),
        "posts": len(as_list(plan.get("posts"))),
        "forms": len(as_list(plan.get("forms"))),
        "media": len(as_list(plan.get("media"))),
    }
    coverage = content_goal_coverage(package)
    coverage_counts = coverage.get("counts") if isinstance(coverage.get("counts"), dict) else {}
    for key in ("forms", "media", "siteInfoFields", "navigationItems"):
        value = coverage_counts.get(key)
        if isinstance(value, int) and value >= 0:
            counts[key] = value
    return counts


def expected_content_quality_review(package: dict[str, Any]) -> dict[str, Any]:
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    pages = [item for item in as_list(plan.get("pages")) if isinstance(item, dict)]
    products = [item for item in as_list(plan.get("products")) if isinstance(item, dict)]
    posts = [item for item in as_list(plan.get("posts")) if isinstance(item, dict)]
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}
    nav_items = [item for item in as_list(navigation.get("items")) if isinstance(item, dict)]
    nav_paths = [item.get("path") for item in nav_items if isinstance(item.get("path"), str)]
    taxonomy = plan.get("taxonomyPlan") if isinstance(plan.get("taxonomyPlan"), dict) else {}
    page_lengths = [len(plain_text(page.get("sections"))) for page in pages]
    product_body_lengths = [len(plain_text(product.get("content"))) for product in products]
    post_body_lengths = [len(plain_text(post.get("content"))) for post in posts]
    warnings: list[str] = []
    if len(nav_paths) != len(set(nav_paths)):
        warnings.append("navigation_paths_not_unique")
    if products and not taxonomy.get("productCategoryCount"):
        warnings.append("products_present_without_product_categories")
    if posts and not taxonomy.get("postCategoryCount"):
        warnings.append("posts_present_without_post_categories")
    if pages and min(page_lengths or [0]) < 120:
        warnings.append("short_page_copy")
    if products and min(product_body_lengths or [0]) < 100:
        warnings.append("short_product_copy")
    if posts and min(post_body_lengths or [0]) < 140:
        warnings.append("short_post_copy")
    coverage = content_goal_coverage(package)
    coverage_counts = coverage.get("counts") if isinstance(coverage.get("counts"), dict) else {}
    declared_goals = coverage.get("declaredContentGoals") if isinstance(coverage.get("declaredContentGoals"), dict) else {}
    for key in ("pages", "products", "posts", "navigationItems", "productCategories", "postCategories", "forms", "media", "siteInfoFields"):
        actual = coverage_counts.get(key)
        declared = declared_goals.get(key)
        if isinstance(actual, int) and isinstance(declared, int) and declared >= 0 and actual > declared:
            warnings.append(f"exceeds_declared_content_goal:{key}")
    blocking_warnings = [
        warning
        for warning in warnings
        if not warning.startswith("exceeds_declared_content_goal:")
    ]
    return {
        "readyShape": not blocking_warnings and bool(pages and products and posts),
        "warnings": warnings,
        "contentCounts": expected_counts(package),
        "navigationPathCount": len(nav_paths),
        "navigationPathsUnique": len(nav_paths) == len(set(nav_paths)),
        "taxonomyCounts": {
            "productCategories": taxonomy.get("productCategoryCount", 0),
            "postCategories": taxonomy.get("postCategoryCount", 0),
            "productTags": taxonomy.get("productTagCount", 0),
            "postTags": taxonomy.get("postTagCount", 0),
        },
        "minimumCopyLengths": {
            "page": min(page_lengths) if page_lengths else 0,
            "product": min(product_body_lengths) if product_body_lengths else 0,
            "post": min(post_body_lengths) if post_body_lengths else 0,
        },
        "reviewRequired": bool(warnings),
    }


def expected_content_goal_overages(package: dict[str, Any]) -> dict[str, Any]:
    coverage = content_goal_coverage(package)
    counts = coverage.get("counts") if isinstance(coverage.get("counts"), dict) else {}
    declared = coverage.get("declaredContentGoals") if isinstance(coverage.get("declaredContentGoals"), dict) else {}
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    taxonomy = plan.get("taxonomyPlan") if isinstance(plan.get("taxonomyPlan"), dict) else {}
    site_info = plan.get("siteInfo") if isinstance(plan.get("siteInfo"), dict) else {}
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}

    def refs(item: dict[str, Any]) -> list[str]:
        return [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()][:12]

    item_lists: dict[str, list[dict[str, Any]]] = {
        "pages": [
            {
                "title": str(item.get("title", "")).strip(),
                "path": str(item.get("path", "")).strip(),
                "sourceRefs": refs(item),
            }
            for item in as_list(plan.get("pages"))
            if isinstance(item, dict)
        ],
        "products": [
            {
                "name": str(item.get("name") or item.get("title") or "").strip(),
                "slug": str(item.get("slug", "")).strip(),
                "sourceRefs": refs(item),
            }
            for item in as_list(plan.get("products"))
            if isinstance(item, dict)
        ],
        "posts": [
            {
                "title": str(item.get("title", "")).strip(),
                "slug": str(item.get("slug", "")).strip(),
                "sourceRefs": refs(item),
            }
            for item in as_list(plan.get("posts"))
            if isinstance(item, dict)
        ],
        "navigationItems": [
            {"label": str(item.get("label", "")).strip(), "path": str(item.get("path", "")).strip()}
            for item in as_list(navigation.get("items"))
            if isinstance(item, dict)
        ],
        "productCategories": [
            {"name": str(item.get("name", "")).strip(), "slug": str(item.get("slug", "")).strip()}
            for item in as_list(taxonomy.get("productCategories"))
            if isinstance(item, dict)
        ],
        "postCategories": [
            {"name": str(item.get("name", "")).strip(), "slug": str(item.get("slug", "")).strip()}
            for item in as_list(taxonomy.get("postCategories"))
            if isinstance(item, dict)
        ],
        "forms": [
            {"name": str(item.get("name", "")).strip(), "slug": str(item.get("slug", "")).strip()}
            for item in as_list(plan.get("forms"))
            if isinstance(item, dict)
        ],
        "media": [
            {
                "kind": str(item.get("kind", "")).strip(),
                "usage": str(item.get("usage", "")).strip(),
                "sourceRef": str(item.get("sourceRef", "")).strip(),
            }
            for item in as_list(plan.get("media"))
            if isinstance(item, dict)
        ],
        "siteInfoFields": [
            {"field": key}
            for key in COUNTED_SITE_INFO_FIELDS
            if site_info.get(key) not in (None, "")
        ],
    }
    details: dict[str, Any] = {}
    for key in (
        "pages",
        "products",
        "posts",
        "navigationItems",
        "productCategories",
        "postCategories",
        "forms",
        "media",
        "siteInfoFields",
    ):
        actual = counts.get(key)
        declared_count = declared.get(key)
        if not (isinstance(actual, int) and isinstance(declared_count, int) and declared_count >= 0 and actual > declared_count):
            continue
        items = item_lists.get(key, [])
        extra_count = actual - declared_count
        details[key] = {
            "declared": declared_count,
            "actual": actual,
            "extraCount": extra_count,
            "items": items[:24],
            "likelyExtraItems": items[declared_count : declared_count + extra_count] if declared_count < len(items) else [],
            "selectionRule": "likelyExtraItems uses generated item order after the declared count; verify with sourceRefs before pruning.",
        }
    return {
        "present": bool(details),
        "details": details,
        "operatorNote": "Content goals are minimum scope; overages are non-blocking only when item-level details are shown before user confirmation.",
    }


def validate_content_quality_review(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("contentQualityReview must be an object")
        return
    if not isinstance(value.get("readyShape"), bool):
        issues.append("contentQualityReview.readyShape must be boolean")
    warnings = value.get("warnings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
        issues.append("contentQualityReview.warnings must be an array of strings")
        warnings = []
    counts = value.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentQualityReview.contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "forms", "media"):
            if not isinstance(counts.get(key), int) or counts.get(key) < 0:
                issues.append(f"contentQualityReview.contentCounts.{key} must be a non-negative integer")
    for key in ("navigationPathCount",):
        if not isinstance(value.get(key), int) or value.get(key) < 0:
            issues.append(f"contentQualityReview.{key} must be a non-negative integer")
    if not isinstance(value.get("navigationPathsUnique"), bool):
        issues.append("contentQualityReview.navigationPathsUnique must be boolean")
    for object_key in ("taxonomyCounts", "minimumCopyLengths"):
        nested = value.get(object_key)
        if not isinstance(nested, dict):
            issues.append(f"contentQualityReview.{object_key} must be an object")
        else:
            for nested_key, nested_value in nested.items():
                if not isinstance(nested_key, str) or not isinstance(nested_value, int) or nested_value < 0:
                    issues.append(f"contentQualityReview.{object_key} values must be non-negative integers")
                    break
    if value.get("reviewRequired") is not bool(warnings):
        issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")


def validate_content_goal_overages(data: dict[str, Any], package: dict[str, Any] | None, issues: list[str]) -> None:
    overages = data.get("contentGoalOverages")
    if not isinstance(overages, dict):
        issues.append("contentGoalOverages must be an object")
        return
    if not isinstance(overages.get("present"), bool):
        issues.append("contentGoalOverages.present must be boolean")
    details = overages.get("details")
    if not isinstance(details, dict):
        issues.append("contentGoalOverages.details must be an object")
        details = {}
    if not isinstance(overages.get("operatorNote"), str) or not overages["operatorNote"].strip():
        issues.append("contentGoalOverages.operatorNote is required")

    quality = data.get("contentQualityReview") if isinstance(data.get("contentQualityReview"), dict) else {}
    warnings = [item for item in as_list(quality.get("warnings")) if isinstance(item, str)]
    warned_keys = sorted(
        warning.split(":", 1)[1]
        for warning in warnings
        if warning.startswith("exceeds_declared_content_goal:") and ":" in warning
    )
    if bool(details) is not (overages.get("present") is True):
        issues.append("contentGoalOverages.present must equal bool(details)")
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
        if not isinstance(detail.get("selectionRule"), str) or not detail["selectionRule"].strip():
            issues.append(f"contentGoalOverages.details.{key}.selectionRule is required")
    if warned_keys and overages.get("present") is not True:
        issues.append("contentGoalOverages.present must be true when exceeds_declared_content_goal warnings exist")

    if package is not None:
        expected = expected_content_goal_overages(package)
        if overages != expected:
            issues.append("contentGoalOverages must match source package overage details")


def validate_wiki_review(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("wikiReview must be an object")
        return
    for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            issues.append(f"wikiReview.{key} is required")
    index = value.get("sourceWikiMarkdownIndex")
    if not isinstance(index, str) or not index.strip():
        return
    index_path = Path(index).expanduser()
    if not index_path.exists():
        issues.append("wikiReview.sourceWikiMarkdownIndex must point to an existing Markdown file")
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


def validate_content_goal_packet(data: dict[str, Any], issues: list[str]) -> None:
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        issues.append("contentGoalCoverage must be an object")
        return
    if coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    checks = coverage.get("checks")
    if not isinstance(checks, dict) or not checks:
        issues.append("contentGoalCoverage.checks must be a non-empty object")
    else:
        for key in ("siteProposal", "siteInfo", "pages", "products", "posts", "navigation", "manifests.products", "manifests.posts"):
            if checks.get(key) is not True:
                issues.append(f"contentGoalCoverage.checks.{key} must be true")
    missing = coverage.get("missing")
    if not isinstance(missing, list):
        issues.append("contentGoalCoverage.missing must be an array")
    elif missing:
        issues.append("contentGoalCoverage.missing must be empty")
    counts = coverage.get("counts")
    if not isinstance(counts, dict):
        issues.append("contentGoalCoverage.counts must be an object")


def validate_review_list(items: Any, label: str, required_keys: tuple[str, ...], count: int, issues: list[str]) -> None:
    if not isinstance(items, list):
        issues.append(f"{label} must be an array")
        return
    if len(items) != count:
        issues.append(f"{label} length must match package count {count}")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"{label}[{index}] must be an object")
            continue
        for key in required_keys:
            if key not in item:
                issues.append(f"{label}[{index}].{key} is required")
        refs = item.get("sourceRefs")
        if not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs):
            issues.append(f"{label}[{index}].sourceRefs must contain source references")
        for key, value in item.items():
            if key.endswith("Preview") and isinstance(value, str) and len(value) > MAX_PREVIEW_CHARS:
                issues.append(f"{label}[{index}].{key} is too long for a review preview")


def validate_command_templates(data: dict[str, Any], issues: list[str]) -> None:
    source_package = data.get("sourcePackage")
    confirmation_output = data.get("confirmationOutput")
    confirmed_execution_output_dir = data.get("confirmedExecutionOutputDir")
    create_action_gate_output = data.get("createActionGateOutput")
    for key in ("confirmationOutput", "confirmedExecutionOutputDir", "createActionGateOutput"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{key} is required")

    confirmation_command = data.get("confirmationCommandTemplate")
    if not isinstance(confirmation_command, str) or not confirmation_command.strip():
        issues.append("confirmationCommandTemplate is required")
    else:
        required_parts = (
            "make_source_package_confirmation.py",
            "--package ",
            "--review-packet ",
            "--user-confirmation-text '<paste current user confirmation text here>'",
            "--accepted-fields",
            "--accepted-deferral",
            "--output ",
        )
        for part in required_parts:
            if part not in confirmation_command:
                issues.append(f"confirmationCommandTemplate missing {part}")
        if isinstance(source_package, str) and source_package and not path_text_present(source_package, confirmation_command):
            issues.append("confirmationCommandTemplate must reference sourcePackage")
        if isinstance(confirmation_output, str) and confirmation_output and confirmation_output not in confirmation_command:
            issues.append("confirmationCommandTemplate must write confirmationOutput")

    validation_command = data.get("confirmationValidationCommandTemplate")
    if not isinstance(validation_command, str) or not validation_command.strip():
        issues.append("confirmationValidationCommandTemplate is required")
    else:
        for part in ("validate_source_package_confirmation.py", "--package ", "--review-packet "):
            if part not in validation_command:
                issues.append(f"confirmationValidationCommandTemplate missing {part}")
        if isinstance(source_package, str) and source_package and not path_text_present(source_package, validation_command):
            issues.append("confirmationValidationCommandTemplate must reference sourcePackage")
        if isinstance(confirmation_output, str) and confirmation_output and confirmation_output not in validation_command:
            issues.append("confirmationValidationCommandTemplate must validate confirmationOutput")

    execution_command = data.get("confirmedExecutionCommandTemplate")
    if not isinstance(execution_command, str) or not execution_command.strip():
        issues.append("confirmedExecutionCommandTemplate is required")
    else:
        required_parts = (
            "prepare_confirmed_site_execution.py",
            "--package ",
            "--review-packet ",
            "--user-confirmation-text '<paste current user confirmation text here>'",
            "--accepted-fields",
            "--accepted-deferral",
            "--output-dir ",
            "--target-mode new_site",
            "--create-authorization-output ",
        )
        for part in required_parts:
            if part not in execution_command:
                issues.append(f"confirmedExecutionCommandTemplate missing {part}")
        if isinstance(source_package, str) and source_package and not path_text_present(source_package, execution_command):
            issues.append("confirmedExecutionCommandTemplate must reference sourcePackage")
        if isinstance(confirmed_execution_output_dir, str) and confirmed_execution_output_dir and confirmed_execution_output_dir not in execution_command:
            issues.append("confirmedExecutionCommandTemplate must write confirmedExecutionOutputDir")
        if isinstance(create_action_gate_output, str) and create_action_gate_output and create_action_gate_output not in execution_command:
            issues.append("confirmedExecutionCommandTemplate must reference createActionGateOutput")

    next_commands = as_list(data.get("nextCommands"))
    for key in ("confirmationCommandTemplate", "confirmationValidationCommandTemplate", "confirmedExecutionCommandTemplate"):
        command = data.get(key)
        if isinstance(command, str) and command.strip() and command not in next_commands:
            issues.append(f"nextCommands must include {key}")


def validate_confirmation_decision_matrix(data: dict[str, Any], issues: list[str]) -> None:
    fields = [item for item in as_list(data.get("confirmationFields")) if isinstance(item, str) and item.strip()]
    accepted = {item for item in as_list(data.get("suggestedAcceptedFields")) if isinstance(item, str) and item.strip()}
    deferrals = {
        item.get("field"): item
        for item in as_list(data.get("suggestedAcceptedDeferrals"))
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
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
            issues.append(f"confirmationDecisionMatrix[{field}].blocksRemoteMutation must be false")
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


def validate_review_packet(data: dict[str, Any], package: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_source_package_review_packet":
        issues.append("kind must be allincms_source_package_review_packet")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
        ("needsUserConfirmation", True),
    ):
        if data.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    parse_time(data.get("generatedAt"), "generatedAt", issues)
    if not isinstance(data.get("sourcePackage"), str) or not data["sourcePackage"].strip():
        issues.append("sourcePackage is required")
    validate_content_goal_packet(data, issues)
    validate_content_quality_review(data.get("contentQualityReview"), issues)
    validate_content_goal_overages(data, package, issues)
    validate_wiki_review(data.get("wikiReview"), issues)

    counts = data.get("counts")
    if not isinstance(counts, dict):
        issues.append("counts must be an object")
        counts = {}
    for key in ("pages", "products", "posts", "forms", "media"):
        if not isinstance(counts.get(key), int) or counts.get(key, -1) < 0:
            issues.append(f"counts.{key} must be a non-negative integer")
    for key in ("siteInfoFields", "navigationItems"):
        if key in counts and (not isinstance(counts.get(key), int) or counts.get(key, -1) < 0):
            issues.append(f"counts.{key} must be a non-negative integer when present")

    site_review = data.get("siteReview")
    if not isinstance(site_review, dict):
        issues.append("siteReview must be an object")
    else:
        for key in ("siteName", "siteDescriptionPreview", "language", "industry"):
            if not isinstance(site_review.get(key), str) or not site_review[key].strip():
                issues.append(f"siteReview.{key} is required")
        if isinstance(site_review.get("siteDescriptionPreview"), str) and len(site_review["siteDescriptionPreview"]) > MAX_PREVIEW_CHARS:
            issues.append("siteReview.siteDescriptionPreview is too long")

    validate_review_list(
        data.get("pagesReview"),
        "pagesReview",
        ("title", "path", "sectionCount", "headingCount", "bodyCharCount", "sourceRefs"),
        int(counts.get("pages", -1)) if isinstance(counts.get("pages"), int) else -1,
        issues,
    )
    validate_review_list(
        data.get("productsReview"),
        "productsReview",
        ("name", "slug", "descriptionPreview", "contentBlockCount", "contentCharCount", "sourceRefs"),
        int(counts.get("products", -1)) if isinstance(counts.get("products"), int) else -1,
        issues,
    )
    validate_review_list(
        data.get("postsReview"),
        "postsReview",
        ("title", "slug", "excerptPreview", "contentBlockCount", "contentCharCount", "sourceRefs"),
        int(counts.get("posts", -1)) if isinstance(counts.get("posts"), int) else -1,
        issues,
    )
    site_info_nav = data.get("siteInfoNavigationFormsMediaReview")
    if not isinstance(site_info_nav, dict):
        issues.append("siteInfoNavigationFormsMediaReview must be an object")
    else:
        site_info_keys = site_info_nav.get("siteInfoKeys")
        navigation_keys = site_info_nav.get("navigationKeys")
        navigation_items = site_info_nav.get("navigationItems")
        if not isinstance(site_info_keys, list) or not site_info_keys:
            issues.append("siteInfoNavigationFormsMediaReview.siteInfoKeys must be a non-empty array")
        if not isinstance(navigation_keys, list) or "items" not in navigation_keys:
            issues.append("siteInfoNavigationFormsMediaReview.navigationKeys must include items")
        if not isinstance(navigation_items, list) or not navigation_items:
            issues.append("siteInfoNavigationFormsMediaReview.navigationItems must be a non-empty array")
        else:
            for index, item in enumerate(navigation_items):
                label = f"siteInfoNavigationFormsMediaReview.navigationItems[{index}]"
                if not isinstance(item, dict):
                    issues.append(f"{label} must be an object")
                    continue
                if not isinstance(item.get("label"), str) or not item["label"].strip():
                    issues.append(f"{label}.label is required")
                if not isinstance(item.get("path"), str) or not item["path"].startswith("/"):
                    issues.append(f"{label}.path must be a leading-slash path")
        taxonomy_plan = site_info_nav.get("taxonomyPlan")
        if not isinstance(taxonomy_plan, dict) or taxonomy_plan.get("present") is not True:
            issues.append("siteInfoNavigationFormsMediaReview.taxonomyPlan must summarize contentPlan.taxonomyPlan")
        else:
            for key in ("status", "productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount"):
                if key not in taxonomy_plan:
                    issues.append(f"siteInfoNavigationFormsMediaReview.taxonomyPlan.{key} is required")
            for key in ("productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount"):
                if not isinstance(taxonomy_plan.get(key), int) or taxonomy_plan.get(key) < 0:
                    issues.append(f"siteInfoNavigationFormsMediaReview.taxonomyPlan.{key} must be a non-negative integer")
            for key in ("requiresCategorySchemaCapture", "requiresTagSchemaCapture", "requiresCreationOrMappingPlan"):
                if taxonomy_plan.get(key) is not True:
                    issues.append(f"siteInfoNavigationFormsMediaReview.taxonomyPlan.{key} must be true")
        media_policy = site_info_nav.get("mediaPolicy")
        if not isinstance(media_policy, dict) or media_policy.get("present") is not True:
            issues.append("siteInfoNavigationFormsMediaReview.mediaPolicy must summarize contentPlan.mediaPolicy")
        else:
            for key in ("status", "allowedSources"):
                if key not in media_policy:
                    issues.append(f"siteInfoNavigationFormsMediaReview.mediaPolicy.{key} is required")
            for key in ("sourceCandidateCount", "pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount"):
                if not isinstance(media_policy.get(key), int) or media_policy.get(key) < 0:
                    issues.append(f"siteInfoNavigationFormsMediaReview.mediaPolicy.{key} must be a non-negative integer")
            if media_policy.get("requiresSchemaCapture") is not True:
                issues.append("siteInfoNavigationFormsMediaReview.mediaPolicy.requiresSchemaCapture must be true")
            if media_policy.get("requiresFrontendImageProof") is not True:
                issues.append("siteInfoNavigationFormsMediaReview.mediaPolicy.requiresFrontendImageProof must be true")
        contact_form_policy = site_info_nav.get("contactFormPolicy")
        if not isinstance(contact_form_policy, dict) or contact_form_policy.get("present") is not True:
            issues.append("siteInfoNavigationFormsMediaReview.contactFormPolicy must summarize contentPlan.contactFormPolicy")
        else:
            for key in (
                "status",
                "publicContactStatus",
                "legalCompanyNameStatus",
                "notificationDestinationPolicy",
                "ctaDestinationPolicy",
                "allowedPublicContactSources",
            ):
                if key not in contact_form_policy:
                    issues.append(f"siteInfoNavigationFormsMediaReview.contactFormPolicy.{key} is required")
            for key in ("formCount", "fieldNeedCount", "contactGapCount"):
                if not isinstance(contact_form_policy.get(key), int) or contact_form_policy.get(key) < 0:
                    issues.append(f"siteInfoNavigationFormsMediaReview.contactFormPolicy.{key} must be a non-negative integer")
            if contact_form_policy.get("requiresFormSchemaCapture") is not True:
                issues.append("siteInfoNavigationFormsMediaReview.contactFormPolicy.requiresFormSchemaCapture must be true")
            if contact_form_policy.get("requiresSubmissionProofOrDeferral") is not True:
                issues.append("siteInfoNavigationFormsMediaReview.contactFormPolicy.requiresSubmissionProofOrDeferral must be true")

    for key in ("confirmationFields", "blockedRemoteActions", "adversarialChecks", "nextCommands"):
        value = data.get(key)
        if not isinstance(value, list) or not value:
            issues.append(f"{key} must be a non-empty array")
    validate_confirmation_decision_matrix(data, issues)
    blocked = {item for item in as_list(data.get("blockedRemoteActions")) if isinstance(item, str)}
    missing_remote = sorted(REMOTE_ACTION_TERMS - blocked)
    if missing_remote:
        issues.append("blockedRemoteActions missing later authorization actions: " + ", ".join(missing_remote))
    suggested = data.get("suggestedConfirmationText")
    if not isinstance(suggested, str) or len(suggested.strip()) < 40:
        issues.append("suggestedConfirmationText must explain the confirmation boundary")
    elif any(term in suggested.lower() for term in ("直接上传", "已经授权上传", "remote mutation authorized")):
        issues.append("suggestedConfirmationText must not imply remote mutation authorization")
    validate_command_templates(data, issues)

    if package is not None:
        package_errors = validate_package(package, require_complete=True, require_publication_ready=True)
        if package_errors:
            issues.extend("sourcePackage: " + error for error in package_errors)
        expected = expected_counts(package)
        if counts != expected:
            issues.append(f"counts must match package counts {expected}")
        expected_goal = content_goal_coverage(package)
        if data.get("contentGoalCoverage") != expected_goal:
            issues.append("contentGoalCoverage must match source package coverage")
        navigation_count = expected_goal.get("counts", {}).get("navigationItems") if isinstance(expected_goal.get("counts"), dict) else None
        if isinstance(navigation_items, list) and isinstance(navigation_count, int) and len(navigation_items) != navigation_count:
            issues.append("siteInfoNavigationFormsMediaReview.navigationItems must match contentGoalCoverage.counts.navigationItems")
        expected_quality = expected_content_quality_review(package)
        if data.get("contentQualityReview") != expected_quality:
            issues.append("contentQualityReview must match source package quality review")
        package_source_wiki = package.get("sourceWiki")
        packet_wiki_review = data.get("wikiReview") if isinstance(data.get("wikiReview"), dict) else {}
        if isinstance(package_source_wiki, str) and packet_wiki_review.get("sourceWiki") != package_source_wiki:
            issues.append("wikiReview.sourceWiki must match package sourceWiki")
        gate = package.get("confirmationGate") if isinstance(package.get("confirmationGate"), dict) else {}
        package_blocked = {item for item in as_list(gate.get("blockedRemoteActions")) if isinstance(item, str)}
        if package_blocked and not package_blocked.issubset(blocked):
            issues.append("blockedRemoteActions must preserve package blockedRemoteActions")
        plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
        package_taxonomy_plan = plan.get("taxonomyPlan") if isinstance(plan, dict) else None
        packet_taxonomy_plan = (
            site_info_nav.get("taxonomyPlan")
            if isinstance(site_info_nav, dict) and isinstance(site_info_nav.get("taxonomyPlan"), dict)
            else None
        )
        if isinstance(package_taxonomy_plan, dict) and isinstance(packet_taxonomy_plan, dict):
            for key in ("status", "productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount"):
                if packet_taxonomy_plan.get(key) != package_taxonomy_plan.get(key):
                    issues.append(f"taxonomyPlan summary must match package contentPlan.taxonomyPlan.{key}")
        package_media_policy = plan.get("mediaPolicy") if isinstance(plan, dict) else None
        packet_media_policy = (
            site_info_nav.get("mediaPolicy")
            if isinstance(site_info_nav, dict) and isinstance(site_info_nav.get("mediaPolicy"), dict)
            else None
        )
        if isinstance(package_media_policy, dict) and isinstance(packet_media_policy, dict):
            for key in ("status", "sourceCandidateCount", "pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount"):
                if packet_media_policy.get(key) != package_media_policy.get(key):
                    issues.append(f"mediaPolicy summary must match package contentPlan.mediaPolicy.{key}")
        package_contact_form_policy = plan.get("contactFormPolicy") if isinstance(plan, dict) else None
        packet_contact_form_policy = (
            site_info_nav.get("contactFormPolicy")
            if isinstance(site_info_nav, dict) and isinstance(site_info_nav.get("contactFormPolicy"), dict)
            else None
        )
        if isinstance(package_contact_form_policy, dict) and isinstance(packet_contact_form_policy, dict):
            for key in ("status", "formCount", "fieldNeedCount", "contactGapCount", "notificationDestinationPolicy", "ctaDestinationPolicy"):
                if packet_contact_form_policy.get(key) != package_contact_form_policy.get(key):
                    issues.append(f"contactFormPolicy summary must match package contentPlan.contactFormPolicy.{key}")

    all_text = "\n".join(safe_strings_for_sensitive_scan(data))
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(all_text):
            issues.append("review packet contains sensitive credential/header/email/raw-id text")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source-package review packet JSON.")
    parser.add_argument("review_packet")
    parser.add_argument("--package", help="Optional source-site package JSON to bind against")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = load_json(Path(args.review_packet), "review packet")
    package = load_json(Path(args.package), "package") if args.package else None
    issues = validate_review_packet(packet, package)
    report = {
        "kind": "allincms_source_package_review_packet_validation",
        "reviewPacket": args.review_packet,
        "package": args.package,
        "valid": not issues,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        if not args.json:
            print("Source package review packet validation failed:")
            for issue in issues:
                print(f"- {issue}")
        return 1
    if not args.json:
        print("Source package review packet validation passed.")
        print("Reminder: this is local review proof only; remote actions still require action-specific authorization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
