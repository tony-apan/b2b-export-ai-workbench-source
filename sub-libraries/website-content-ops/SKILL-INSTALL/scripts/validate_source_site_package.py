#!/usr/bin/env python3
"""Validate a local AllinCMS source-site package before user confirmation or upload planning."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_manifest import SLUG_RE, looks_like_rich_markdown, validate_manifest


# Accepted policy `status` values when the policy carries items/terms/gaps. Kept as module
# constants so the refinement brief can advertise the exact same values it will be checked
# against (no drift between "what the brief says to set" and "what the validator accepts").
TAXONOMY_STATUS_ALLOWED = {"needs_user_confirmation", "source_taxonomy_pending_schema_capture", "accepted_taxonomy_mapping_deferred"}
MEDIA_STATUS_ALLOWED = {"needs_user_confirmation", "source_candidates_pending_schema_capture", "accepted_no_image_for_launch_scope"}
CONTACT_STATUS_ALLOWED = {"needs_user_confirmation", "source_contact_pending_user_confirmation", "accepted_demo_deferral"}


SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:cookie|authorization|bearer|next-action|next-router-state-tree)\b", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b[a-f0-9]{24}\b", re.IGNORECASE),
)
PLACEHOLDER_TEXT_PATTERNS = (
    re.compile(r"^\s*(?:draft|untitled|placeholder)(?:\s|[-_:]|$)", re.IGNORECASE),
    re.compile(r"\b(?:draft product|draft article|untitled|placeholder|lorem ipsum)\b", re.IGNORECASE),
)
REVIEW_REQUIRED_PATTERNS = (
    re.compile(r"\brequires?\s+(?:review|source extraction|user review|confirmation)\b", re.IGNORECASE),
    re.compile(r"\b(?:replace|fill in|to be confirmed|tbd|todo)\b", re.IGNORECASE),
)
MIN_SITE_DESCRIPTION_CHARS = 40
MIN_PAGE_BODY_CHARS = 120
MIN_PRODUCT_DESCRIPTION_CHARS = 40
MIN_PRODUCT_BODY_CHARS = 100
MIN_POST_EXCERPT_CHARS = 40
MIN_POST_BODY_CHARS = 140
CONTENT_GOAL_REQUIREMENTS = {
    "siteProposal": "site proposal",
    "siteInfo": "website information",
    "pages": "single pages",
    "products": "products",
    "posts": "articles",
    "navigation": "navigation",
    "manifests.products": "products manifest",
    "manifests.posts": "posts manifest",
    "declaredContentGoals.forms": "forms",
    "declaredContentGoals.media": "media assets or media needs",
    "declaredContentGoals.siteInfoFields": "site information fields",
}
RESERVED_NAV_PATHS = {
    "/",
    "/home",
    "/products",
    "/posts",
    "/post",
    "/news",
    "/blog",
    "/categories",
    "/tags",
    "/search",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit("ERROR: package root must be an object")
    return data


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


def plain_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts: list[str] = []
        for key in ("heading", "title", "body", "text", "description", "excerpt"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
        if not parts:
            for item in value.values():
                text = plain_text(item)
                if text:
                    parts.append(text)
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(text for item in value if (text := plain_text(item)))
    return ""


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def has_pattern(value: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(value) for pattern in patterns)


def publication_text_errors(value: str, label: str, *, allow_short: bool = False, min_chars: int = 0) -> list[str]:
    issues: list[str] = []
    text = value.strip()
    if not text:
        issues.append(f"{label} must be non-empty publication-ready copy")
        return issues
    if has_pattern(text, PLACEHOLDER_TEXT_PATTERNS):
        issues.append(f"{label} contains placeholder/draft wording")
    if has_pattern(text, REVIEW_REQUIRED_PATTERNS):
        issues.append(f"{label} contains review-required or unresolved wording")
    if not allow_short and min_chars and len(text) < min_chars:
        issues.append(f"{label} is too short for publication-ready copy; expected at least {min_chars} characters")
    return issues


def source_ref_errors(item: dict[str, Any], label: str) -> list[str]:
    refs = item.get("sourceRefs")
    if not isinstance(refs, list) or not any(isinstance(ref, str) and ref.strip() for ref in refs):
        return [f"{label}.sourceRefs must contain at least one source reference"]
    return []


def optional_source_ref_shape_errors(item: dict[str, Any], label: str) -> list[str]:
    refs = item.get("sourceRefs")
    if refs is None:
        return []
    if not isinstance(refs, list):
        return [f"{label}.sourceRefs must be an array when present"]
    if not all(isinstance(ref, str) and ref.strip() for ref in refs):
        return [f"{label}.sourceRefs must contain non-empty source reference strings"]
    return []


def source_set_refs(source_set: Any) -> set[str]:
    if not isinstance(source_set, dict):
        return set()
    input_files = source_set.get("inputFiles")
    if not isinstance(input_files, list):
        return set()
    return {
        item["sourceRef"]
        for item in input_files
        if isinstance(item, dict) and isinstance(item.get("sourceRef"), str) and item["sourceRef"].strip()
    }


def source_ref_inventory_errors(value: Any, label: str, valid_refs: set[str]) -> list[str]:
    if not valid_refs or not isinstance(value, dict):
        return []
    issues: list[str] = []
    refs = value.get("sourceRefs")
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, str) and ref.strip() and ref not in valid_refs:
                issues.append(f"{label}.sourceRefs contains unknown source reference {ref}")
    return issues


def publication_content_block_errors(blocks: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(blocks, list) or not blocks:
        issues.append(f"{label} must contain at least one publication-ready content block")
        return issues
    for index, block in enumerate(blocks):
        block_label = f"{label}[{index}]"
        if not isinstance(block, dict):
            issues.append(f"{block_label} must be an object")
            continue
        text = plain_text(block)
        issues.extend(
            publication_text_errors(
                text,
                block_label,
                allow_short=True,
            )
        )
    return issues


def content_block_source_ref_errors(blocks: Any, label: str, valid_refs: set[str]) -> list[str]:
    if not isinstance(blocks, list):
        return []
    issues: list[str] = []
    for index, block in enumerate(blocks):
        block_label = f"{label}[{index}]"
        if not isinstance(block, dict):
            continue
        issues.extend(optional_source_ref_shape_errors(block, block_label))
        issues.extend(source_ref_inventory_errors(block, block_label, valid_refs))
    return issues


def page_section_source_ref_errors(sections: Any, label: str, valid_refs: set[str]) -> list[str]:
    if not isinstance(sections, list):
        return []
    issues: list[str] = []
    for index, section in enumerate(sections):
        section_label = f"{label}[{index}]"
        if not isinstance(section, dict):
            continue
        issues.extend(optional_source_ref_shape_errors(section, section_label))
        issues.extend(source_ref_inventory_errors(section, section_label, valid_refs))
    return issues


def content_goal_coverage(data: dict[str, Any]) -> dict[str, Any]:
    plan = data.get("contentPlan") if isinstance(data.get("contentPlan"), dict) else {}
    manifests = data.get("manifests") if isinstance(data.get("manifests"), dict) else {}
    site = data.get("siteProposal") if isinstance(data.get("siteProposal"), dict) else {}
    site_info = plan.get("siteInfo") if isinstance(plan.get("siteInfo"), dict) else {}
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}
    pages = as_list(plan.get("pages")) if isinstance(plan, dict) else []
    products = as_list(plan.get("products")) if isinstance(plan, dict) else []
    posts = as_list(plan.get("posts")) if isinstance(plan, dict) else []
    forms = as_list(plan.get("forms")) if isinstance(plan, dict) else []
    media = as_list(plan.get("media")) if isinstance(plan, dict) else []
    media_policy = plan.get("mediaPolicy") if isinstance(plan.get("mediaPolicy"), dict) else {}
    navigation_items = as_list(navigation.get("items"))
    taxonomy = plan.get("taxonomyPlan") if isinstance(plan.get("taxonomyPlan"), dict) else {}
    product_manifest = manifests.get("products") if isinstance(manifests.get("products"), dict) else {}
    post_manifest = manifests.get("posts") if isinstance(manifests.get("posts"), dict) else {}
    product_manifest_items = as_list(product_manifest.get("items"))
    post_manifest_items = as_list(post_manifest.get("items"))
    declared = data.get("declaredContentGoals") if isinstance(data.get("declaredContentGoals"), dict) else {}
    site_info_field_count = sum(
        1
        for key in ("draftSeoTitle", "draftSeoDescription", "publicContact", "legalCompanyName", "logoPolicy")
        if site_info.get(key) not in (None, "")
    )
    media_count = len(media) + sum(
        nonnegative_int(media_policy.get(key))
        for key in ("pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount")
    )
    counts = {
        "pages": len(pages),
        "products": len(products),
        "posts": len(posts),
        "forms": len(forms),
        "media": media_count,
        "siteInfoFields": site_info_field_count,
        "navigationItems": len(navigation_items),
        "productCategories": nonnegative_int(taxonomy.get("productCategoryCount")),
        "postCategories": nonnegative_int(taxonomy.get("postCategoryCount")),
        "productTags": nonnegative_int(taxonomy.get("productTagCount")),
        "postTags": nonnegative_int(taxonomy.get("postTagCount")),
        "productManifestItems": len(product_manifest_items),
        "postManifestItems": len(post_manifest_items),
    }
    checks = {
        "siteProposal": bool(site.get("siteName") and site.get("siteDescription")),
        "siteInfo": bool(site_info.get("draftSeoTitle") and site_info.get("draftSeoDescription")),
        "pages": len(pages) > 0,
        "products": len(products) > 0,
        "posts": len(posts) > 0,
        "navigation": len(navigation_items) > 0,
        "manifests.products": len(product_manifest_items) == len(products) and len(products) > 0,
        "manifests.posts": len(post_manifest_items) == len(posts) and len(posts) > 0,
    }
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
        expected = declared.get(key)
        if isinstance(expected, int) and expected > 0:
            checks[f"declaredContentGoals.{key}"] = counts.get(key, 0) >= expected
    missing = [key for key, ok in checks.items() if not ok]
    return {
        "goal": "source files distilled into website information, single pages, products, articles, navigation, and draft manifests",
        "complete": not missing,
        "checks": checks,
        "missing": missing,
        "counts": counts,
        "declaredContentGoals": declared,
    }


def validate_content_goal_coverage(data: dict[str, Any]) -> list[str]:
    coverage = content_goal_coverage(data)
    if coverage["complete"]:
        return []
    return [
        f"content goal coverage missing {key}: {CONTENT_GOAL_REQUIREMENTS.get(key, key)}"
        for key in coverage["missing"]
    ]


def validate_pages(pages: Any, require_complete: bool, valid_refs: set[str] | None = None) -> list[str]:
    issues: list[str] = []
    valid_refs = valid_refs or set()
    if not isinstance(pages, list):
        return ["contentPlan.pages must be an array"]
    if require_complete and not pages:
        issues.append("contentPlan.pages must contain at least one page")
    seen_paths: set[str] = set()
    for index, page in enumerate(pages):
        label = f"contentPlan.pages[{index}]"
        if not isinstance(page, dict):
            issues.append(f"{label} must be an object")
            continue
        title = page.get("title")
        path = page.get("path")
        if not isinstance(title, str) or not title.strip():
            issues.append(f"{label}.title is required")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(f"{label}.path must be a leading-slash path")
        elif path in seen_paths:
            issues.append(f"{label}.path duplicates {path}")
        else:
            seen_paths.add(path)
        sections = page.get("sections")
        if require_complete and (not isinstance(sections, list) or not sections):
            issues.append(f"{label}.sections must be non-empty")
        issues.extend(source_ref_errors(page, label))
        issues.extend(page_section_source_ref_errors(sections, f"{label}.sections", valid_refs))
    return issues


def validate_products(products: Any, require_complete: bool, valid_refs: set[str] | None = None) -> list[str]:
    issues: list[str] = []
    valid_refs = valid_refs or set()
    if not isinstance(products, list):
        return ["contentPlan.products must be an array"]
    if require_complete and not products:
        issues.append("contentPlan.products must contain at least one product")
    seen_slugs: set[str] = set()
    for index, product in enumerate(products):
        label = f"contentPlan.products[{index}]"
        if not isinstance(product, dict):
            issues.append(f"{label} must be an object")
            continue
        name = product.get("name") or product.get("title")
        slug = product.get("slug")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"{label}.name is required")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            issues.append(f"{label}.slug must be lowercase kebab-case")
        elif slug in seen_slugs:
            issues.append(f"{label}.slug duplicates {slug}")
        else:
            seen_slugs.add(slug)
        if not isinstance(product.get("description"), str) or not product["description"].strip():
            issues.append(f"{label}.description is required")
        if require_complete and not product.get("content"):
            issues.append(f"{label}.content is required")
        issues.extend(source_ref_errors(product, label))
        issues.extend(content_block_source_ref_errors(product.get("content"), f"{label}.content", valid_refs))
    return issues


def validate_posts(posts: Any, require_complete: bool, valid_refs: set[str] | None = None) -> list[str]:
    issues: list[str] = []
    valid_refs = valid_refs or set()
    if not isinstance(posts, list):
        return ["contentPlan.posts must be an array"]
    if require_complete and not posts:
        issues.append("contentPlan.posts must contain at least one post")
    seen_slugs: set[str] = set()
    for index, post in enumerate(posts):
        label = f"contentPlan.posts[{index}]"
        if not isinstance(post, dict):
            issues.append(f"{label} must be an object")
            continue
        slug = post.get("slug")
        if not isinstance(post.get("title"), str) or not post["title"].strip():
            issues.append(f"{label}.title is required")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            issues.append(f"{label}.slug must be lowercase kebab-case")
        elif slug in seen_slugs:
            issues.append(f"{label}.slug duplicates {slug}")
        else:
            seen_slugs.add(slug)
        if not isinstance(post.get("excerpt"), str) or not post["excerpt"].strip():
            issues.append(f"{label}.excerpt is required")
        if require_complete and not post.get("content"):
            issues.append(f"{label}.content is required")
        issues.extend(source_ref_errors(post, label))
        issues.extend(content_block_source_ref_errors(post.get("content"), f"{label}.content", valid_refs))
    return issues


def validate_site_info(site_info: Any, require_complete: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(site_info, dict):
        return ["contentPlan.siteInfo must be an object"]
    if require_complete:
        for key in ("draftSeoTitle", "draftSeoDescription"):
            if not isinstance(site_info.get(key), str) or not site_info[key].strip():
                issues.append(f"contentPlan.siteInfo.{key} is required")
        if site_info.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.siteInfo.userConfirmationRequired must be true")
    return issues


def validate_navigation(navigation: Any, require_complete: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(navigation, dict):
        return ["contentPlan.navigation must be an object"]
    items = navigation.get("items")
    if not isinstance(items, list):
        return ["contentPlan.navigation.items must be an array"]
    if require_complete and not items:
        issues.append("contentPlan.navigation.items must be non-empty")
    seen_paths: set[str] = set()
    for index, item in enumerate(items):
        label = f"contentPlan.navigation.items[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            issues.append(f"{label}.label is required")
        path = item.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(f"{label}.path must be a leading-slash path")
        elif path in seen_paths:
            issues.append(f"{label}.path duplicates {path}")
        else:
            seen_paths.add(path)
    if require_complete and navigation.get("userConfirmationRequired") is not True:
        issues.append("contentPlan.navigation.userConfirmationRequired must be true")
    return issues


def route_requires_page_plan(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    if normalized in RESERVED_NAV_PATHS:
        return False
    if "{" in normalized or "}" in normalized:
        return False
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return False
    if any(part.startswith(":") or part.startswith("[") or part.startswith("*") for part in parts):
        return False
    if any(part in {"category", "categories", "tag", "tags", "search"} for part in parts):
        return False
    return True


def validate_navigation_page_coverage(plan: dict[str, Any], require_publication_ready: bool) -> list[str]:
    if not require_publication_ready:
        return []
    navigation = plan.get("navigation")
    pages = plan.get("pages")
    if not isinstance(navigation, dict) or not isinstance(pages, list):
        return []
    page_paths = {
        page.get("path").rstrip("/") or "/"
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("path"), str)
    }
    issues: list[str] = []
    for index, item in enumerate(navigation.get("items") if isinstance(navigation.get("items"), list) else []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        path = item["path"].rstrip("/") or "/"
        if route_requires_page_plan(path) and path not in page_paths:
            issues.append(
                f"contentPlan.navigation.items[{index}].path {path} is a static navigation route without a matching contentPlan.pages entry"
            )
    return issues


def validate_media_policy(media_policy: Any, require_complete: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(media_policy, dict):
        return ["contentPlan.mediaPolicy must be an object"]
    if require_complete:
        if media_policy.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.mediaPolicy.userConfirmationRequired must be true")
        if media_policy.get("requiresSchemaCapture") is not True:
            issues.append("contentPlan.mediaPolicy.requiresSchemaCapture must be true")
        if media_policy.get("requiresFrontendImageProof") is not True:
            issues.append("contentPlan.mediaPolicy.requiresFrontendImageProof must be true")
        status = media_policy.get("status")
        if not isinstance(status, str) or not status.strip():
            issues.append("contentPlan.mediaPolicy.status is required")
        allowed = media_policy.get("allowedSources")
        if not isinstance(allowed, list) or not all(isinstance(item, str) and item.strip() for item in allowed):
            issues.append("contentPlan.mediaPolicy.allowedSources must contain source labels")
        for key in ("sourceCandidateCount", "pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount"):
            if not isinstance(media_policy.get(key), int) or media_policy.get(key) < 0:
                issues.append(f"contentPlan.mediaPolicy.{key} must be a non-negative integer")
    return issues


def validate_contact_form_policy(contact_form_policy: Any, require_complete: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(contact_form_policy, dict):
        return ["contentPlan.contactFormPolicy must be an object"]
    if require_complete:
        if contact_form_policy.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.contactFormPolicy.userConfirmationRequired must be true")
        if contact_form_policy.get("requiresFormSchemaCapture") is not True:
            issues.append("contentPlan.contactFormPolicy.requiresFormSchemaCapture must be true")
        if contact_form_policy.get("requiresSubmissionProofOrDeferral") is not True:
            issues.append("contentPlan.contactFormPolicy.requiresSubmissionProofOrDeferral must be true")
        status = contact_form_policy.get("status")
        if not isinstance(status, str) or not status.strip():
            issues.append("contentPlan.contactFormPolicy.status is required")
        allowed = contact_form_policy.get("allowedPublicContactSources")
        if not isinstance(allowed, list) or not all(isinstance(item, str) and item.strip() for item in allowed):
            issues.append("contentPlan.contactFormPolicy.allowedPublicContactSources must contain source labels")
        for key in ("formCount", "fieldNeedCount", "contactGapCount"):
            if not isinstance(contact_form_policy.get(key), int) or contact_form_policy.get(key) < 0:
                issues.append(f"contentPlan.contactFormPolicy.{key} must be a non-negative integer")
        for key in ("publicContactStatus", "legalCompanyNameStatus", "notificationDestinationPolicy", "ctaDestinationPolicy"):
            if not isinstance(contact_form_policy.get(key), str) or not contact_form_policy[key].strip():
                issues.append(f"contentPlan.contactFormPolicy.{key} is required")
    return issues


def validate_taxonomy_terms(value: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, list):
        return [f"{label} must be an array"]
    seen_slugs: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{item_label} must be an object")
            continue
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            issues.append(f"{item_label}.label is required")
        slug = item.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            issues.append(f"{item_label}.slug must be lowercase kebab-case")
        elif slug in seen_slugs:
            issues.append(f"{item_label}.slug duplicates {slug}")
        else:
            seen_slugs.add(slug)
        refs = item.get("sourceRefs")
        if refs is not None and (not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs)):
            issues.append(f"{item_label}.sourceRefs must be source reference strings when present")
    return issues


def validate_taxonomy_plan(taxonomy_plan: Any, require_complete: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(taxonomy_plan, dict):
        return ["contentPlan.taxonomyPlan must be an object"]
    for key in ("productCategories", "postCategories", "productTags", "postTags"):
        issues.extend(validate_taxonomy_terms(taxonomy_plan.get(key), f"contentPlan.taxonomyPlan.{key}"))
    if require_complete:
        if taxonomy_plan.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.taxonomyPlan.userConfirmationRequired must be true")
        for key in ("requiresCategorySchemaCapture", "requiresTagSchemaCapture", "requiresCreationOrMappingPlan"):
            if taxonomy_plan.get(key) is not True:
                issues.append(f"contentPlan.taxonomyPlan.{key} must be true")
        status = taxonomy_plan.get("status")
        if not isinstance(status, str) or not status.strip():
            issues.append("contentPlan.taxonomyPlan.status is required")
        for key in ("productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount"):
            if not isinstance(taxonomy_plan.get(key), int) or taxonomy_plan.get(key) < 0:
                issues.append(f"contentPlan.taxonomyPlan.{key} must be a non-negative integer")
    return issues


def validate_confirmation_gate(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    gate = data.get("confirmationGate")
    if not isinstance(gate, dict):
        return ["confirmationGate must be an object"]
    if gate.get("required") is not True:
        issues.append("confirmationGate.required must be true")
    if gate.get("confirmed") is True and not gate.get("confirmationEvidence"):
        issues.append("confirmationGate.confirmationEvidence is required when confirmed=true")
    fields = gate.get("fieldsNeedingUserConfirmation")
    if not isinstance(fields, list) or not fields:
        issues.append("confirmationGate.fieldsNeedingUserConfirmation must be non-empty")
    blocked = gate.get("blockedRemoteActions")
    if not isinstance(blocked, list) or not blocked:
        issues.append("confirmationGate.blockedRemoteActions must be non-empty before remote execution")
    return issues


def validate_manifests(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    manifests = data.get("manifests")
    if not isinstance(manifests, dict):
        return ["manifests must be an object"]
    for key in ("products", "posts"):
        manifest = manifests.get(key)
        if not isinstance(manifest, dict):
            issues.append(f"manifests.{key} must be an object")
            continue
        for error in validate_manifest(manifest, require_schema_verified=False):
            issues.append(f"manifests.{key}: {error}")
        if manifest.get("schemaVerified") is True:
            issues.append(f"manifests.{key}.schemaVerified must remain false until current-site save request capture")
        if manifest.get("payloadTemplate"):
            issues.append(f"manifests.{key}.payloadTemplate must remain empty in source-site package stage")
    return issues


def validate_source_set(source_set: Any, require_hashes: bool) -> list[str]:
    issues: list[str] = []
    if not isinstance(source_set, dict):
        return ["sourceSet must be an object"]
    input_files = source_set.get("inputFiles")
    if not isinstance(input_files, list) or not input_files:
        return ["sourceSet.inputFiles must be non-empty"]
    for index, item in enumerate(input_files):
        label = f"sourceSet.inputFiles[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        for key in ("path", "type", "sourceRef"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                issues.append(f"{label}.{key} is required")
        sha = item.get("sha256")
        if sha is None:
            if require_hashes:
                issues.append(f"{label}.sha256 is required for publication-ready source packages")
        elif not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            issues.append(f"{label}.sha256 must be a lowercase sha256 hex digest")
        size = item.get("sizeBytes")
        if size is None:
            if require_hashes:
                issues.append(f"{label}.sizeBytes is required for publication-ready source packages")
        elif not isinstance(size, int) or size < 0:
            issues.append(f"{label}.sizeBytes must be a non-negative integer")
    return issues


def validate_publication_ready_package(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    site = data.get("siteProposal")
    if isinstance(site, dict):
        issues.extend(
            publication_text_errors(
                str(site.get("siteName", "")),
                "siteProposal.siteName",
                allow_short=True,
            )
        )
        issues.extend(
            publication_text_errors(
                str(site.get("siteDescription", "")),
                "siteProposal.siteDescription",
                min_chars=MIN_SITE_DESCRIPTION_CHARS,
            )
        )

    plan = data.get("contentPlan")
    if not isinstance(plan, dict):
        return issues

    for index, page in enumerate(plan.get("pages", []) if isinstance(plan.get("pages"), list) else []):
        if not isinstance(page, dict):
            continue
        label = f"contentPlan.pages[{index}]"
        title = str(page.get("title", ""))
        issues.extend(publication_text_errors(title, f"{label}.title", allow_short=True))
        sections = page.get("sections")
        section_text = plain_text(sections)
        issues.extend(publication_text_errors(section_text, f"{label}.sections", min_chars=MIN_PAGE_BODY_CHARS))
        if isinstance(sections, list):
            heading_count = sum(1 for section in sections if isinstance(section, dict) and isinstance(section.get("heading"), str) and section["heading"].strip())
            if heading_count == 0:
                issues.append(f"{label}.sections must include at least one meaningful heading")
            for section_index, section in enumerate(sections):
                section_label = f"{label}.sections[{section_index}]"
                if not isinstance(section, dict):
                    issues.append(f"{section_label} must be an object")
                    continue
                if not isinstance(section.get("heading"), str) or not section["heading"].strip():
                    issues.append(f"{section_label}.heading is required for publication-ready pages")
                issues.extend(
                    publication_text_errors(
                        str(section.get("body", "")),
                        f"{section_label}.body",
                        min_chars=MIN_PAGE_BODY_CHARS,
                    )
                )

    for index, product in enumerate(plan.get("products", []) if isinstance(plan.get("products"), list) else []):
        if not isinstance(product, dict):
            continue
        label = f"contentPlan.products[{index}]"
        name = str(product.get("name") or product.get("title") or "")
        issues.extend(publication_text_errors(name, f"{label}.name", allow_short=True))
        issues.extend(
            publication_text_errors(
                str(product.get("description", "")),
                f"{label}.description",
                min_chars=MIN_PRODUCT_DESCRIPTION_CHARS,
            )
        )
        issues.extend(
            publication_text_errors(
                plain_text(product.get("content")),
                f"{label}.content",
                min_chars=MIN_PRODUCT_BODY_CHARS,
            )
        )
        issues.extend(publication_content_block_errors(product.get("content"), f"{label}.content"))

    for index, post in enumerate(plan.get("posts", []) if isinstance(plan.get("posts"), list) else []):
        if not isinstance(post, dict):
            continue
        label = f"contentPlan.posts[{index}]"
        issues.extend(publication_text_errors(str(post.get("title", "")), f"{label}.title", allow_short=True))
        issues.extend(
            publication_text_errors(
                str(post.get("excerpt", "")),
                f"{label}.excerpt",
                min_chars=MIN_POST_EXCERPT_CHARS,
            )
        )
        issues.extend(
            publication_text_errors(
                plain_text(post.get("content")),
                f"{label}.content",
                min_chars=MIN_POST_BODY_CHARS,
            )
        )
        issues.extend(publication_content_block_errors(post.get("content"), f"{label}.content"))

    site_info = plan.get("siteInfo")
    if isinstance(site_info, dict):
        issues.extend(
            publication_text_errors(
                str(site_info.get("draftSeoTitle", "")),
                "contentPlan.siteInfo.draftSeoTitle",
                allow_short=True,
            )
        )
        issues.extend(
            publication_text_errors(
                str(site_info.get("draftSeoDescription", "")),
                "contentPlan.siteInfo.draftSeoDescription",
                min_chars=MIN_SITE_DESCRIPTION_CHARS,
            )
        )
        if site_info.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.siteInfo.userConfirmationRequired must be true")

    media_policy = plan.get("mediaPolicy")
    if isinstance(media_policy, dict):
        total_media_need = sum(
            int(media_policy.get(key, 0) or 0)
            for key in ("sourceCandidateCount", "pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount")
        )
        status = str(media_policy.get("status", "")).strip()
        if total_media_need > 0 and status not in MEDIA_STATUS_ALLOWED:
            issues.append(
                "contentPlan.mediaPolicy.status must explicitly confirm media handling when media candidates or "
                f"image needs exist; set it to one of {sorted(MEDIA_STATUS_ALLOWED)} (got {status!r})"
            )
        if media_policy.get("acceptedNoImage") is True and total_media_need > int(media_policy.get("missingImageFieldCount", 0) or 0):
            issues.append("contentPlan.mediaPolicy.acceptedNoImage cannot be true while source media candidates or mediaNeeds remain")
        if media_policy.get("requiresFrontendImageProof") is not True:
            issues.append("contentPlan.mediaPolicy.requiresFrontendImageProof must be true before publication-ready confirmation")

    contact_form_policy = plan.get("contactFormPolicy")
    if isinstance(contact_form_policy, dict):
        total_contact_need = int(contact_form_policy.get("formCount", 0) or 0) + int(contact_form_policy.get("contactGapCount", 0) or 0)
        status = str(contact_form_policy.get("status", "")).strip()
        if total_contact_need > 0 and status not in CONTACT_STATUS_ALLOWED:
            issues.append(
                "contentPlan.contactFormPolicy.status must explicitly confirm form/contact handling when forms or "
                f"contact gaps exist; set it to one of {sorted(CONTACT_STATUS_ALLOWED)} (got {status!r})"
            )
        if contact_form_policy.get("requiresSubmissionProofOrDeferral") is not True:
            issues.append("contentPlan.contactFormPolicy.requiresSubmissionProofOrDeferral must be true before publication-ready confirmation")
        for key in ("notificationDestinationPolicy", "ctaDestinationPolicy"):
            value = str(contact_form_policy.get(key, "")).strip()
            if not value or value == "implicit":
                issues.append(f"contentPlan.contactFormPolicy.{key} must be explicit")

    navigation = plan.get("navigation")
    if isinstance(navigation, dict):
        items = navigation.get("items")
        if not isinstance(items, list) or not items:
            issues.append("contentPlan.navigation.items must contain user-reviewable navigation items")
        else:
            paths = {item.get("path") for item in items if isinstance(item, dict)}
            if "/" not in paths:
                issues.append("contentPlan.navigation.items must include the homepage path /")
            if plan.get("products") and "/products" not in paths:
                issues.append("contentPlan.navigation.items must include /products when products are planned")
            if plan.get("posts") and "/posts" not in paths:
                issues.append("contentPlan.navigation.items must include /posts when posts are planned")
        if navigation.get("userConfirmationRequired") is not True:
            issues.append("contentPlan.navigation.userConfirmationRequired must be true")

    taxonomy_plan = plan.get("taxonomyPlan")
    if isinstance(taxonomy_plan, dict):
        total_terms = sum(
            int(taxonomy_plan.get(key, 0) or 0)
            for key in ("productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount")
        )
        status = str(taxonomy_plan.get("status", "")).strip()
        if total_terms > 0 and status not in TAXONOMY_STATUS_ALLOWED:
            issues.append(
                "contentPlan.taxonomyPlan.status must explicitly confirm taxonomy handling when categories or tags "
                f"exist; set it to one of {sorted(TAXONOMY_STATUS_ALLOWED)} (got {status!r})"
            )
        for key in ("requiresCategorySchemaCapture", "requiresTagSchemaCapture", "requiresCreationOrMappingPlan"):
            if taxonomy_plan.get(key) is not True:
                issues.append(f"contentPlan.taxonomyPlan.{key} must be true before publication-ready confirmation")

    open_questions = data.get("openQuestions")
    if isinstance(open_questions, list):
        for index, question in enumerate(open_questions):
            if isinstance(question, str) and has_pattern(question, REVIEW_REQUIRED_PATTERNS + PLACEHOLDER_TEXT_PATTERNS):
                issues.append(f"openQuestions[{index}] must be resolved before publication-ready confirmation")

    return issues


def validate_package(
    data: dict[str, Any],
    require_complete: bool = False,
    require_publication_ready: bool = False,
) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_source_site_package":
        issues.append("kind must be allincms_source_site_package")
    if data.get("localOnly") is not True:
        issues.append("localOnly must be true")
    if data.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    source_set = data.get("sourceSet")
    issues.extend(validate_source_set(source_set, require_publication_ready))
    valid_refs = source_set_refs(source_set)
    if isinstance(source_set, dict):
        if not isinstance(source_set.get("wikiRefs"), list) or not source_set["wikiRefs"]:
            issues.append("sourceSet.wikiRefs must be non-empty")
    site = data.get("siteProposal")
    if not isinstance(site, dict):
        issues.append("siteProposal must be an object")
    else:
        for key in ("siteName", "siteDescription", "language", "industry"):
            if require_complete and (not isinstance(site.get(key), str) or not site[key].strip()):
                issues.append(f"siteProposal.{key} is required")
        if site.get("userConfirmationRequired") is not True:
            issues.append("siteProposal.userConfirmationRequired must be true")
    plan = data.get("contentPlan")
    if not isinstance(plan, dict):
        issues.append("contentPlan must be an object")
    else:
        issues.extend(validate_pages(plan.get("pages"), require_complete, valid_refs))
        issues.extend(validate_products(plan.get("products"), require_complete, valid_refs))
        issues.extend(validate_posts(plan.get("posts"), require_complete, valid_refs))
        issues.extend(validate_site_info(plan.get("siteInfo"), require_complete))
        issues.extend(validate_navigation(plan.get("navigation"), require_complete))
        issues.extend(validate_taxonomy_plan(plan.get("taxonomyPlan"), require_complete))
        issues.extend(validate_media_policy(plan.get("mediaPolicy"), require_complete))
        issues.extend(validate_contact_form_policy(plan.get("contactFormPolicy"), require_complete))
        issues.extend(validate_navigation_page_coverage(plan, require_publication_ready))
        if require_complete:
            issues.extend(validate_content_goal_coverage(data))
    issues.extend(validate_confirmation_gate(data))
    issues.extend(validate_manifests(data))
    for text in walk_strings(data):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                issues.append("package contains sensitive credential/header/email/raw-id text")
                return issues
        if looks_like_rich_markdown(text):
            issues.append("package contains raw Markdown/HTML-like rich text; convert to structured blocks or plain text before upload")
            return issues
    if require_publication_ready:
        issues.extend(validate_publication_ready_package(data))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS source-site package JSON.")
    parser.add_argument("package")
    parser.add_argument("--require-complete-package", action="store_true")
    parser.add_argument("--require-publication-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = load_json(Path(args.package))
    issues = validate_package(
        data,
        require_complete=args.require_complete_package,
        require_publication_ready=args.require_publication_ready,
    )
    report = {
        "kind": "allincms_source_site_package_validation",
        "package": args.package,
        "valid": not issues,
        "requireCompletePackage": args.require_complete_package,
        "requirePublicationReady": args.require_publication_ready,
        "contentGoalCoverage": content_goal_coverage(data),
        "issues": issues,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        if not args.json:
            print("Source site package validation failed:")
            for issue in issues:
                print(f"- {issue}")
        return 1
    if not args.json:
        print("Source site package validation passed.")
        print("Reminder: this is local package proof only; current-site schema capture and user confirmation are still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
