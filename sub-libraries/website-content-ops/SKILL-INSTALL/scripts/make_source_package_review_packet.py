#!/usr/bin/env python3
"""Build a local, redacted review packet before confirming a source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_package_confirmation import REQUIRED_ACCEPTED_FIELDS
from validate_source_package_review_packet import validate_review_packet
from validate_source_site_package import load_json as load_package_json
from validate_source_site_package import plain_text, validate_package
from validate_source_site_package import content_goal_coverage

from _common import default_run_root


MAX_PREVIEW_CHARS = 160
COUNTED_SITE_INFO_FIELDS = ("draftSeoTitle", "draftSeoDescription", "publicContact", "legalCompanyName", "logoPolicy")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_preview(value: Any, limit: int = MAX_PREVIEW_CHARS) -> str:
    text = plain_text(value) if not isinstance(value, str) else value.strip()
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def count_headings(sections: Any) -> int:
    count = 0
    for section in as_list(sections):
        if isinstance(section, dict) and isinstance(section.get("heading"), str) and section["heading"].strip():
            count += 1
    return count


def compact_refs(value: Any) -> list[str]:
    refs = [item for item in as_list(value) if isinstance(item, str) and item.strip()]
    return refs[:12]


def package_counts(package: dict[str, Any]) -> dict[str, int]:
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


def content_quality_review(package: dict[str, Any]) -> dict[str, Any]:
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
        "contentCounts": package_counts(package),
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


def review_pages(pages: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in as_list(pages):
        if not isinstance(page, dict):
            continue
        sections = as_list(page.get("sections"))
        out.append(
            {
                "title": str(page.get("title", "")).strip(),
                "path": str(page.get("path", "")).strip(),
                "purpose": str(page.get("purpose", "")).strip(),
                "sectionCount": len(sections),
                "headingCount": count_headings(sections),
                "bodyCharCount": len(plain_text(sections)),
                "sourceRefs": compact_refs(page.get("sourceRefs")),
            }
        )
    return out


def review_products(products: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for product in as_list(products):
        if not isinstance(product, dict):
            continue
        out.append(
            {
                "name": str(product.get("name") or product.get("title") or "").strip(),
                "slug": str(product.get("slug", "")).strip(),
                "descriptionPreview": safe_preview(product.get("description")),
                "descriptionCharCount": len(str(product.get("description", "")).strip()),
                "contentBlockCount": len(as_list(product.get("content"))),
                "contentCharCount": len(plain_text(product.get("content"))),
                "specCount": len(as_list(product.get("specs"))),
                "categoryCount": len(as_list(product.get("categories"))),
                "tagCount": len(as_list(product.get("tags"))),
                "mediaNeedCount": len(as_list(product.get("mediaNeeds"))),
                "sourceRefs": compact_refs(product.get("sourceRefs")),
            }
        )
    return out


def review_posts(posts: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for post in as_list(posts):
        if not isinstance(post, dict):
            continue
        out.append(
            {
                "title": str(post.get("title", "")).strip(),
                "slug": str(post.get("slug", "")).strip(),
                "excerptPreview": safe_preview(post.get("excerpt")),
                "excerptCharCount": len(str(post.get("excerpt", "")).strip()),
                "contentBlockCount": len(as_list(post.get("content"))),
                "contentCharCount": len(plain_text(post.get("content"))),
                "categoryCount": len(as_list(post.get("categories"))),
                "tagCount": len(as_list(post.get("tags"))),
                "mediaNeedCount": len(as_list(post.get("mediaNeeds"))),
                "sourceRefs": compact_refs(post.get("sourceRefs")),
            }
        )
    return out


def overage_item(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    if kind == "pages":
        return {
            "title": str(item.get("title", "")).strip(),
            "path": str(item.get("path", "")).strip(),
            "sourceRefs": compact_refs(item.get("sourceRefs")),
        }
    if kind == "products":
        return {
            "name": str(item.get("name") or item.get("title") or "").strip(),
            "slug": str(item.get("slug", "")).strip(),
            "sourceRefs": compact_refs(item.get("sourceRefs")),
        }
    if kind == "posts":
        return {
            "title": str(item.get("title", "")).strip(),
            "slug": str(item.get("slug", "")).strip(),
            "sourceRefs": compact_refs(item.get("sourceRefs")),
        }
    return {"sourceRefs": compact_refs(item.get("sourceRefs"))}


def item_lists_for_overages(package: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    taxonomy = plan.get("taxonomyPlan") if isinstance(plan.get("taxonomyPlan"), dict) else {}
    site_info = plan.get("siteInfo") if isinstance(plan.get("siteInfo"), dict) else {}
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}
    return {
        "pages": [
            overage_item("pages", item)
            for item in as_list(plan.get("pages"))
            if isinstance(item, dict)
        ],
        "products": [
            overage_item("products", item)
            for item in as_list(plan.get("products"))
            if isinstance(item, dict)
        ],
        "posts": [
            overage_item("posts", item)
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


def content_goal_overages(package: dict[str, Any]) -> dict[str, Any]:
    coverage = content_goal_coverage(package)
    counts = coverage.get("counts") if isinstance(coverage.get("counts"), dict) else {}
    declared = coverage.get("declaredContentGoals") if isinstance(coverage.get("declaredContentGoals"), dict) else {}
    item_lists = item_lists_for_overages(package)
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


def review_navigation(navigation: Any) -> list[dict[str, str]]:
    if not isinstance(navigation, dict):
        return []
    out: list[dict[str, str]] = []
    for item in as_list(navigation.get("items")):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        path = str(item.get("path", "")).strip()
        if label or path:
            out.append({"label": label, "path": path})
    return out


def operation_gaps_summary(operation_gaps: Any) -> dict[str, Any]:
    if not isinstance(operation_gaps, dict):
        return {"present": False, "blockedFieldCount": 0, "userInputFieldCount": 0, "entryCount": 0}
    return {
        "present": operation_gaps.get("present") is True,
        "requirementsPathStatus": operation_gaps.get("requirementsPathStatus", ""),
        "blockedFieldCount": len(as_list(operation_gaps.get("blockedFields"))),
        "userInputFieldCount": len(as_list(operation_gaps.get("userInputFields"))),
        "entryCount": len(as_list(operation_gaps.get("entries"))),
        "blockedFields": compact_refs(operation_gaps.get("blockedFields")),
        "userInputFields": compact_refs(operation_gaps.get("userInputFields")),
    }


def media_policy_summary(media_policy: Any) -> dict[str, Any]:
    if not isinstance(media_policy, dict):
        return {"present": False}
    return {
        "present": True,
        "status": str(media_policy.get("status", "")).strip(),
        "sourceCandidateCount": media_policy.get("sourceCandidateCount", 0),
        "pageMediaNeedCount": media_policy.get("pageMediaNeedCount", 0),
        "productMediaNeedCount": media_policy.get("productMediaNeedCount", 0),
        "postMediaNeedCount": media_policy.get("postMediaNeedCount", 0),
        "missingImageFieldCount": media_policy.get("missingImageFieldCount", 0),
        "allowedSources": compact_refs(media_policy.get("allowedSources")),
        "requiresSchemaCapture": media_policy.get("requiresSchemaCapture") is True,
        "requiresFrontendImageProof": media_policy.get("requiresFrontendImageProof") is True,
        "acceptedNoImage": media_policy.get("acceptedNoImage") is True,
        "userConfirmationRequired": media_policy.get("userConfirmationRequired") is True,
    }


def contact_form_policy_summary(contact_form_policy: Any) -> dict[str, Any]:
    if not isinstance(contact_form_policy, dict):
        return {"present": False}
    return {
        "present": True,
        "status": str(contact_form_policy.get("status", "")).strip(),
        "formCount": contact_form_policy.get("formCount", 0),
        "fieldNeedCount": contact_form_policy.get("fieldNeedCount", 0),
        "contactGapCount": contact_form_policy.get("contactGapCount", 0),
        "publicContactStatus": str(contact_form_policy.get("publicContactStatus", "")).strip(),
        "legalCompanyNameStatus": str(contact_form_policy.get("legalCompanyNameStatus", "")).strip(),
        "notificationDestinationPolicy": str(contact_form_policy.get("notificationDestinationPolicy", "")).strip(),
        "ctaDestinationPolicy": str(contact_form_policy.get("ctaDestinationPolicy", "")).strip(),
        "allowedPublicContactSources": compact_refs(contact_form_policy.get("allowedPublicContactSources")),
        "requiresFormSchemaCapture": contact_form_policy.get("requiresFormSchemaCapture") is True,
        "requiresSubmissionProofOrDeferral": contact_form_policy.get("requiresSubmissionProofOrDeferral") is True,
        "userConfirmationRequired": contact_form_policy.get("userConfirmationRequired") is True,
    }


def taxonomy_plan_summary(taxonomy_plan: Any) -> dict[str, Any]:
    if not isinstance(taxonomy_plan, dict):
        return {"present": False}
    return {
        "present": True,
        "status": str(taxonomy_plan.get("status", "")).strip(),
        "productCategoryCount": taxonomy_plan.get("productCategoryCount", 0),
        "postCategoryCount": taxonomy_plan.get("postCategoryCount", 0),
        "productTagCount": taxonomy_plan.get("productTagCount", 0),
        "postTagCount": taxonomy_plan.get("postTagCount", 0),
        "productCategorySlugs": compact_refs([item.get("slug") for item in as_list(taxonomy_plan.get("productCategories")) if isinstance(item, dict)]),
        "postCategorySlugs": compact_refs([item.get("slug") for item in as_list(taxonomy_plan.get("postCategories")) if isinstance(item, dict)]),
        "requiresCategorySchemaCapture": taxonomy_plan.get("requiresCategorySchemaCapture") is True,
        "requiresTagSchemaCapture": taxonomy_plan.get("requiresTagSchemaCapture") is True,
        "requiresCreationOrMappingPlan": taxonomy_plan.get("requiresCreationOrMappingPlan") is True,
        "userConfirmationRequired": taxonomy_plan.get("userConfirmationRequired") is True,
    }


def suggested_deferrals(confirmation_fields: list[str]) -> list[dict[str, str]]:
    defaults = {
        "siteInfo.publicContact": {
            "decision": "defer_until_real_company_details",
            "reason": "Public contact channels must be confirmed by the user before launch.",
        },
        "siteInfo.legalCompanyName": {
            "decision": "defer_until_real_company_details",
            "reason": "Legal company name must be confirmed by the user before launch.",
        },
        "domains.customDomain": {
            "decision": "out_of_scope_until_domain_setup",
            "reason": "Custom domain binding requires a separate domain decision and action gate.",
        },
        "tracking.trackingCode": {
            "decision": "out_of_scope_until_tracking_setup",
            "reason": "Tracking setup requires user-supplied tracking configuration and a separate action gate.",
        },
    }
    return [
        {"field": field, **defaults[field]}
        for field in confirmation_fields
        if field in defaults
    ]


def shell_deferral_args(deferrals: list[dict[str, str]]) -> str:
    return " ".join(
        f"--accepted-deferral '{item['field']}|{item['decision']}|{item['reason']}'"
        for item in deferrals
    )


def confirmation_decision_matrix(
    confirmation_fields: list[str],
    suggested_accepted_fields: list[str],
    suggested_deferral_items: list[dict[str, str]],
) -> list[dict[str, Any]]:
    accepted = {field for field in suggested_accepted_fields if isinstance(field, str) and field.strip()}
    deferrals = {
        item.get("field"): item
        for item in suggested_deferral_items
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
    matrix: list[dict[str, Any]] = []
    for field in confirmation_fields:
        if field in deferrals:
            deferral = deferrals[field]
            matrix.append(
                {
                    "field": field,
                    "decision": "defer",
                    "source": "suggestedAcceptedDeferrals",
                    "deferDecision": deferral.get("decision", ""),
                    "reason": deferral.get("reason", ""),
                    "blocksRemoteMutation": False,
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
                }
            )
    return matrix


def load_json_or_empty(path: str) -> dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def source_wiki_refs(source_wiki_path: str) -> list[str]:
    wiki = load_json_or_empty(source_wiki_path)
    source_set = wiki.get("sourceSet") if isinstance(wiki.get("sourceSet"), dict) else {}
    refs = source_set.get("wikiRefs")
    return [item for item in refs if isinstance(item, str) and item.strip()] if isinstance(refs, list) else []


def markdown_export_index(path: str) -> str:
    data = load_json_or_empty(path)
    if data.get("kind") != "allincms_source_wiki_markdown_export":
        return ""
    files = data.get("files") if isinstance(data.get("files"), dict) else {}
    index = files.get("index")
    return index if isinstance(index, str) and index.strip() else ""


def wiki_review(package: dict[str, Any]) -> dict[str, str]:
    source_wiki = package.get("sourceWiki")
    source_wiki = source_wiki if isinstance(source_wiki, str) else ""
    refs = source_wiki_refs(source_wiki)
    markdown_manifest = ""
    markdown_index = ""
    for ref in refs:
        if ref.endswith(".json"):
            index = markdown_export_index(ref)
            if index:
                markdown_manifest = ref
                markdown_index = index
                break
        if Path(ref).name == "index.md":
            markdown_index = ref
            manifest = Path(ref).parent / "manifest.json"
            markdown_manifest = str(manifest) if manifest.exists() else ""
            break
    if not markdown_index:
        for ref in refs:
            if ref.endswith(".md"):
                parent_index = Path(ref).expanduser().parent / "index.md"
                if parent_index.exists():
                    markdown_index = str(parent_index)
                    manifest = parent_index.parent / "manifest.json"
                    markdown_manifest = str(manifest) if manifest.exists() else ""
                    break
    return {
        "sourceWiki": source_wiki,
        "sourceWikiMarkdown": markdown_manifest,
        "sourceWikiMarkdownIndex": markdown_index,
    }


def review_run_paths(review_packet_path: str | None) -> dict[str, str]:
    review_ref = review_packet_path or str(default_run_root() / "source-package-review-packet.json")
    review_path = Path(review_ref).expanduser()
    run_dir = review_path.parent if str(review_path.parent) not in ("", ".") else default_run_root()
    return {
        "reviewPacket": review_ref,
        "confirmationOutput": str(run_dir / "confirmation-record.json"),
        "confirmedExecutionOutputDir": str(run_dir / "confirmed-execution"),
        "createActionGateOutput": str(run_dir / "create-site-action-gate.json"),
    }


def build_review_packet(
    package: dict[str, Any],
    package_path: str,
    generated_at: str | None = None,
    review_packet_path: str | None = None,
    wiki_review_override: dict[str, str] | None = None,
) -> dict[str, Any]:
    package_errors = validate_package(package, require_complete=True, require_publication_ready=True)
    if package_errors:
        raise ValueError("source package is not ready for review confirmation:\n- " + "\n- ".join(package_errors))

    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    site = package.get("siteProposal") if isinstance(package.get("siteProposal"), dict) else {}
    gate = package.get("confirmationGate") if isinstance(package.get("confirmationGate"), dict) else {}
    counts = package_counts(package)
    quality_review = content_quality_review(package)
    overages = content_goal_overages(package)
    wiki_review_info = wiki_review_override if isinstance(wiki_review_override, dict) else wiki_review(package)
    accepted_fields = sorted(set(REQUIRED_ACCEPTED_FIELDS) | set(as_list(gate.get("fieldsNeedingUserConfirmation"))))
    blocked_actions = sorted({item for item in as_list(gate.get("blockedRemoteActions")) if isinstance(item, str)})
    suggested_deferral_items = suggested_deferrals(accepted_fields)
    suggested_deferral_fields = {item["field"] for item in suggested_deferral_items}
    suggested_accepted_fields = [field for field in accepted_fields if field not in suggested_deferral_fields]
    decision_matrix = confirmation_decision_matrix(accepted_fields, suggested_accepted_fields, suggested_deferral_items)
    run_paths = review_run_paths(review_packet_path)
    review_packet_ref = run_paths["reviewPacket"]
    confirmation_output = run_paths["confirmationOutput"]
    confirmed_execution_output_dir = run_paths["confirmedExecutionOutputDir"]
    create_action_gate_output = run_paths["createActionGateOutput"]
    accepted_fields_arg = ",".join(suggested_accepted_fields)
    suggested_confirmation = (
        "我已审阅本地 source-site package review packet，确认网站基础信息、"
        f"{counts['pages']} 个单页、{counts['products']} 个产品、{counts['posts']} 篇文章的内容意图，"
        f"并已看到内容质量检查 warning: {', '.join(quality_review['warnings']) or 'none'}；"
        "允许继续生成本地 confirmation record 和后续执行计划；这不是远程创建、保存、上传或发布授权。"
    )
    confirmation_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_source_package_confirmation.py "
        f"--package {package_path} "
        f"--review-packet {review_packet_ref} "
        "--user-confirmation-text '<paste current user confirmation text here>' "
        f"--accepted-fields '{accepted_fields_arg}' "
        f"{shell_deferral_args(suggested_deferral_items)} "
        f"--output {confirmation_output}"
    )
    confirmation_validation_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_source_package_confirmation.py "
        f"{confirmation_output} "
        f"--package {package_path} "
        f"--review-packet {review_packet_ref}"
    )
    confirmed_execution_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/prepare_confirmed_site_execution.py "
        f"--package {package_path} "
        f"--review-packet {review_packet_ref} "
        "--user-confirmation-text '<paste current user confirmation text here>' "
        f"--accepted-fields '{accepted_fields_arg}' "
        f"{shell_deferral_args(suggested_deferral_items)} "
        f"--output-dir {confirmed_execution_output_dir} "
        "--target-mode new_site "
        f"--create-authorization-output {create_action_gate_output}"
    )

    packet = {
        "kind": "allincms_source_package_review_packet",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourcePackage": package_path,
        "packageGeneratedAt": package.get("generatedAt", ""),
        "contentGoalCoverage": content_goal_coverage(package),
        "counts": counts,
        "contentQualityReview": quality_review,
        "contentGoalOverages": overages,
        "wikiReview": wiki_review_info,
        "siteReview": {
            "siteName": str(site.get("siteName", "")).strip(),
            "siteDescriptionPreview": safe_preview(site.get("siteDescription")),
            "siteDescriptionCharCount": len(str(site.get("siteDescription", "")).strip()),
            "language": str(site.get("language", "")).strip(),
            "industry": str(site.get("industry", "")).strip(),
        },
        "pagesReview": review_pages(plan.get("pages")),
        "productsReview": review_products(plan.get("products")),
        "postsReview": review_posts(plan.get("posts")),
        "siteInfoNavigationFormsMediaReview": {
            "siteInfoKeys": sorted(str(key) for key in (plan.get("siteInfo") or {}).keys()) if isinstance(plan.get("siteInfo"), dict) else [],
            "navigationKeys": sorted(str(key) for key in (plan.get("navigation") or {}).keys()) if isinstance(plan.get("navigation"), dict) else [],
            "navigationItems": review_navigation(plan.get("navigation")),
            "taxonomyPlan": taxonomy_plan_summary(plan.get("taxonomyPlan")),
            "formCount": counts["forms"],
            "mediaCount": counts["media"],
            "mediaPolicy": media_policy_summary(plan.get("mediaPolicy")),
            "contactFormPolicy": contact_form_policy_summary(plan.get("contactFormPolicy")),
        },
        "operationGapsSummary": operation_gaps_summary(package.get("operationGaps")),
        "needsUserConfirmation": True,
        "confirmationFields": accepted_fields,
        "suggestedAcceptedFields": suggested_accepted_fields,
        "suggestedAcceptedDeferrals": suggested_deferral_items,
        "confirmationDecisionMatrix": decision_matrix,
        "confirmationOutput": confirmation_output,
        "confirmedExecutionOutputDir": confirmed_execution_output_dir,
        "createActionGateOutput": create_action_gate_output,
        "blockedRemoteActions": blocked_actions,
        "adversarialChecks": [
            "This packet is generated only after validate_source_site_package.py --require-complete-package --require-publication-ready passes.",
            "The packet contains counts, previews, slugs, paths, source refs, and gaps; it must not contain full body copy or raw source files.",
            "Package confirmation proves content intent only; remote create/save/upload/publish actions still need action-specific gates.",
            "Products and posts remain blocked for upload until the current site has separate save-request capture and sample verification.",
            "Domains, tracking, contact channels, legal details, pricing, inventory, and unsupported claims require explicit confirmation or deferral.",
            "Media policy must say whether source images/public URLs/no-image scope are accepted before sample or batch upload.",
            "Contact/form policy must keep public contact channels, CTA destinations, notification destinations, and submission proof as explicit user-confirmed or deferred decisions.",
            "Taxonomy plan must keep product/post categories and tags as explicit user-confirmed or deferred decisions before category/tag creation or mapping.",
            "contentQualityReview warnings are non-blocking only when surfaced to the user before confirmation; hidden warnings must block confirmation-surface generation.",
            "If content goals are exceeded, item-level overage details must be shown before confirmation; do not hide expanded scope behind a generic warning.",
        ],
        "suggestedConfirmationText": suggested_confirmation,
        "confirmationCommandTemplate": confirmation_command,
        "confirmationValidationCommandTemplate": confirmation_validation_command,
        "confirmedExecutionCommandTemplate": confirmed_execution_command,
        "nextCommands": [
            confirmation_command,
            confirmation_validation_command,
            confirmed_execution_command,
        ],
    }
    issues = validate_review_packet(packet, package)
    if issues:
        raise ValueError("generated review packet failed validation:\n- " + "\n- ".join(issues))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local review packet for an AllinCMS source-site package.")
    parser.add_argument("--package", required=True, help="Publication-ready source-site package JSON")
    parser.add_argument("--output", required=True, help="Path to write review packet JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        package = load_package_json(Path(args.package))
        packet = build_review_packet(package, args.package, review_packet_path=args.output)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source package review packet: {output}")
    print(
        "counts="
        f"pages:{packet['counts']['pages']},"
        f"products:{packet['counts']['products']},"
        f"posts:{packet['counts']['posts']}"
    )
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
