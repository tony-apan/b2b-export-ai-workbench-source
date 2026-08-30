#!/usr/bin/env python3
"""Build a local AllinCMS source-to-site content package from a distilled wiki JSON."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: str | None, label: str) -> dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or "untitled"


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def source_refs(item: dict[str, Any], fallback: list[str]) -> list[str]:
    refs = [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()]
    return refs or fallback


def normalize_content(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        blocks: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if isinstance(item, dict):
                blocks.append(item)
            elif isinstance(item, str) and item.strip():
                blocks.append({"type": "paragraph", "text": item.strip(), "sourceIndex": index})
        return blocks
    if isinstance(value, str) and value.strip():
        return [{"type": "paragraph", "text": value.strip()}]
    if isinstance(value, dict):
        return [value]
    return []


def source_set(source_wiki: dict[str, Any]) -> dict[str, Any]:
    data = source_wiki.get("sourceSet")
    if not isinstance(data, dict):
        data = {}
    input_files = as_list(data.get("inputFiles"))
    refs: list[str] = []
    normalized_files: list[dict[str, Any]] = []
    for index, item in enumerate(input_files):
        if isinstance(item, dict):
            copied = {
                "path": nonempty_string(item.get("path")),
                "name": nonempty_string(item.get("name")),
                "type": nonempty_string(item.get("type")) or "unknown",
                "sourceRef": nonempty_string(item.get("sourceRef")) or f"source-{index + 1}",
            }
            if isinstance(item.get("sizeBytes"), int):
                copied["sizeBytes"] = item["sizeBytes"]
            if nonempty_string(item.get("sha256")):
                copied["sha256"] = nonempty_string(item.get("sha256"))
            if item.get("hashVerified") is True:
                copied["hashVerified"] = True
            normalized_files.append(copied)
            refs.append(copied["sourceRef"])
        elif isinstance(item, str) and item.strip():
            ref = f"source-{index + 1}"
            normalized_files.append({"path": item.strip(), "type": "unknown", "sourceRef": ref})
            refs.append(ref)
    raw_refs = [item for item in as_list(data.get("rawExtractionRefs")) if isinstance(item, str) and item.strip()]
    wiki_refs = [item for item in as_list(data.get("wikiRefs")) if isinstance(item, str) and item.strip()]
    return {
        "inputFiles": normalized_files,
        "rawExtractionRefs": raw_refs,
        "wikiRefs": wiki_refs,
        "defaultSourceRefs": refs,
    }


def normalize_site(source_wiki: dict[str, Any]) -> dict[str, Any]:
    site = source_wiki.get("site")
    if not isinstance(site, dict):
        site = {}
    return {
        "siteName": nonempty_string(site.get("siteName")) or "Draft AllinCMS Site",
        "siteDescription": nonempty_string(site.get("siteDescription")) or nonempty_string(site.get("description")),
        "language": nonempty_string(site.get("language")) or "en",
        "industry": nonempty_string(site.get("industry")) or "unspecified",
        "userConfirmationRequired": True,
    }


def normalize_content_goals(source_wiki: dict[str, Any]) -> dict[str, int]:
    raw = source_wiki.get("contentGoals")
    if not isinstance(raw, dict):
        return {}
    goals: dict[str, int] = {}
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
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            goals[key] = value
        elif isinstance(value, str) and value.strip().isdigit():
            goals[key] = int(value.strip())
    return goals


def hosted_cover_image(value: Any, default_alt: str) -> dict[str, str] | None:
    """Normalize a source coverImage into the manifest `{url, alt}` contract.

    Accepts either a bare hosted URL string or an object with url/alt. Only an
    already-uploaded public http(s) URL is carried into the package/manifest so
    an upload can set a real cover; local file paths must be uploaded to a
    public host first and are rejected here.
    """
    url = ""
    alt = ""
    if isinstance(value, str):
        url = value.strip()
    elif isinstance(value, dict):
        url = value.get("url", "").strip() if isinstance(value.get("url"), str) else ""
        alt = value.get("alt", "").strip() if isinstance(value.get("alt"), str) else ""
    if not (url.startswith("http://") or url.startswith("https://")):
        return None
    return {"url": url, "alt": alt or default_alt}


def normalize_pages(source_wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(source_wiki.get("pages"))):
        if not isinstance(item, dict):
            continue
        title = nonempty_string(item.get("title")) or f"Page {index + 1}"
        path = nonempty_string(item.get("path")) or "/" + slugify(title)
        if title.lower() == "home":
            path = "/"
        sections = as_list(item.get("sections"))
        normalized_sections: list[dict[str, Any]] = []
        for section in sections:
            if isinstance(section, dict):
                normalized_sections.append(section)
            elif isinstance(section, str) and section.strip():
                normalized_sections.append({"heading": "", "body": section.strip()})
        pages.append(
            {
                "title": title,
                "path": path if path.startswith("/") else "/" + path,
                "purpose": nonempty_string(item.get("purpose")) or "content_page",
                "sections": normalized_sections,
                "mediaNeeds": as_list(item.get("mediaNeeds")),
                "sourceRefs": source_refs(item, fallback_refs),
                "status": "draft_pending_user_confirmation",
            }
        )
    return pages


def normalize_products(source_wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(source_wiki.get("products"))):
        if not isinstance(item, dict):
            continue
        name = nonempty_string(item.get("name")) or nonempty_string(item.get("title")) or f"Product {index + 1}"
        slug = nonempty_string(item.get("slug")) or slugify(name)
        product = {
            "name": name,
            "slug": slug,
            "description": nonempty_string(item.get("description")),
            "content": normalize_content(item.get("content")),
            "specs": as_list(item.get("specs")),
            "categories": as_list(item.get("categories")),
            "tags": as_list(item.get("tags")),
            "mediaNeeds": as_list(item.get("mediaNeeds")),
            "sourceRefs": source_refs(item, fallback_refs),
        }
        cover = hosted_cover_image(item.get("coverImage"), name)
        if cover:
            product["coverImage"] = cover
        products.append(product)
    return products


def normalize_posts(source_wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(source_wiki.get("posts"))):
        if not isinstance(item, dict):
            continue
        title = nonempty_string(item.get("title")) or f"Article {index + 1}"
        slug = nonempty_string(item.get("slug")) or slugify(title)
        post = {
            "title": title,
            "slug": slug,
            "excerpt": nonempty_string(item.get("excerpt")) or nonempty_string(item.get("description")),
            "content": normalize_content(item.get("content")),
            "categories": as_list(item.get("categories")),
            "tags": as_list(item.get("tags")),
            "mediaNeeds": as_list(item.get("mediaNeeds")),
            "sourceRefs": source_refs(item, fallback_refs),
        }
        cover = hosted_cover_image(item.get("coverImage"), title)
        if cover:
            post["coverImage"] = cover
        posts.append(post)
    return posts


def normalize_site_info(source_wiki: dict[str, Any], site: dict[str, Any]) -> dict[str, Any]:
    source_site_info = source_wiki.get("siteInfo")
    if not isinstance(source_site_info, dict):
        source_site_info = {}
    site_name = nonempty_string(site.get("siteName"))
    site_description = nonempty_string(site.get("siteDescription"))
    return {
        "draftSeoTitle": nonempty_string(source_site_info.get("draftSeoTitle")) or site_name,
        "draftSeoDescription": nonempty_string(source_site_info.get("draftSeoDescription")) or site_description,
        "publicContact": source_site_info.get("publicContact", "requires_user_confirmation"),
        "legalCompanyName": source_site_info.get("legalCompanyName", "requires_user_confirmation"),
        "logoPolicy": source_site_info.get("logoPolicy", "derive_from_source_or_defer"),
        "userConfirmationRequired": True,
    }


def media_need_count(items: list[dict[str, Any]]) -> int:
    return sum(len(as_list(item.get("mediaNeeds"))) for item in items)


def normalize_media_policy(
    source_wiki: dict[str, Any],
    pages: list[dict[str, Any]],
    products: list[dict[str, Any]],
    posts: list[dict[str, Any]],
    media: list[dict[str, Any]],
    requirements: dict[str, Any],
) -> dict[str, Any]:
    source_policy = source_wiki.get("mediaPolicy")
    if not isinstance(source_policy, dict):
        source_policy = {}
    operation_gaps = requirements_gaps(requirements)
    missing_image_fields = [
        item
        for item in operation_gaps.get("blockedFields", []) + operation_gaps.get("userInputFields", [])
        if isinstance(item, str) and any(token in item.lower() for token in ("image", "media", "cover", "logo"))
    ]
    source_candidate_count = len(media)
    product_need_count = media_need_count(products)
    post_need_count = media_need_count(posts)
    page_need_count = media_need_count(pages)
    has_needs = bool(source_candidate_count or product_need_count or post_need_count or page_need_count or missing_image_fields)
    default_status = "needs_user_confirmation" if has_needs else "explicit_no_media_needed_for_source_package"
    return {
        "status": nonempty_string(source_policy.get("status")) or default_status,
        "sourceCandidateCount": source_candidate_count,
        "pageMediaNeedCount": page_need_count,
        "productMediaNeedCount": product_need_count,
        "postMediaNeedCount": post_need_count,
        "missingImageFieldCount": len(missing_image_fields),
        "allowedSources": as_list(source_policy.get("allowedSources")) or ["source_files", "public_urls_after_user_confirmation"],
        "requiresSchemaCapture": True,
        "requiresFrontendImageProof": True,
        "acceptedNoImage": source_policy.get("acceptedNoImage") is True,
        "userConfirmationRequired": True,
        "notes": nonempty_string(source_policy.get("notes")),
    }


def normalize_contact_form_policy(
    source_wiki: dict[str, Any],
    forms: list[dict[str, Any]],
    site_info: dict[str, Any],
    requirements: dict[str, Any],
) -> dict[str, Any]:
    source_policy = source_wiki.get("contactFormPolicy")
    if not isinstance(source_policy, dict):
        source_policy = {}
    operation_gaps = requirements_gaps(requirements)
    gap_values = [
        item
        for item in operation_gaps.get("blockedFields", []) + operation_gaps.get("userInputFields", [])
        if isinstance(item, str)
    ]
    contact_gap_count = sum(
        1
        for item in gap_values
        if any(token in item.lower() for token in ("contact", "email", "notification", "form", "cta", "legal", "phone", "whatsapp"))
    )
    has_forms = bool(forms)
    public_contact = site_info.get("publicContact")
    legal_company = site_info.get("legalCompanyName")
    default_status = "needs_user_confirmation" if has_forms or contact_gap_count else "explicit_contact_details_pending_or_not_required"
    return {
        "status": nonempty_string(source_policy.get("status")) or default_status,
        "formCount": len(forms),
        "fieldNeedCount": sum(len(as_list(form.get("fields"))) for form in forms),
        "contactGapCount": contact_gap_count,
        "publicContactStatus": "provided_in_source" if isinstance(public_contact, dict) else str(public_contact or "requires_user_confirmation"),
        "legalCompanyNameStatus": "provided_in_source" if isinstance(legal_company, dict) else str(legal_company or "requires_user_confirmation"),
        "notificationDestinationPolicy": nonempty_string(source_policy.get("notificationDestinationPolicy")) or "requires_user_confirmation",
        "ctaDestinationPolicy": nonempty_string(source_policy.get("ctaDestinationPolicy")) or "requires_user_confirmation",
        "allowedPublicContactSources": as_list(source_policy.get("allowedPublicContactSources")) or ["user_confirmation", "explicit_source_material"],
        "requiresFormSchemaCapture": True,
        "requiresSubmissionProofOrDeferral": True,
        "userConfirmationRequired": True,
        "notes": nonempty_string(source_policy.get("notes")),
    }


def normalize_navigation(source_wiki: dict[str, Any], pages: list[dict[str, Any]], products: list[dict[str, Any]], posts: list[dict[str, Any]]) -> dict[str, Any]:
    source_navigation = source_wiki.get("navigation")
    source_items = source_navigation.get("items") if isinstance(source_navigation, dict) else None
    items: list[dict[str, Any]] = []
    for item in as_list(source_items):
        if not isinstance(item, dict):
            continue
        label = nonempty_string(item.get("label"))
        path = nonempty_string(item.get("path"))
        if label and path:
            items.append({"label": label, "path": path if path.startswith("/") else "/" + path})
    if not items:
        page_paths = {page.get("path") for page in pages if isinstance(page.get("path"), str)}
        items.append({"label": "Home", "path": "/"})
        if products:
            items.append({"label": "Products", "path": "/products"})
        if posts:
            items.append({"label": "Posts", "path": "/posts"})
        for page in pages:
            path = page.get("path")
            title = page.get("title")
            if isinstance(path, str) and isinstance(title, str) and path not in {"/", "/products", "/posts"}:
                items.append({"label": title, "path": path})
        existing_paths = {item["path"] for item in items if isinstance(item.get("path"), str)}
        if "/contact" in page_paths and "/contact" not in existing_paths:
            items.append({"label": "Contact", "path": "/contact"})
    return {
        "items": items,
        "userConfirmationRequired": True,
        "source": "source_wiki_or_generated_from_content_plan",
    }


def taxonomy_label(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("label", "name", "title", "slug"):
            item = nonempty_string(value.get(key))
            if item:
                return item
    return ""


def taxonomy_refs(value: Any, fallback_refs: list[str]) -> list[str]:
    if isinstance(value, dict):
        refs = [ref for ref in as_list(value.get("sourceRefs")) if isinstance(ref, str) and ref.strip()]
        if refs:
            return refs
    return fallback_refs


def merge_taxonomy_terms(values: list[Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for value in values:
        label = taxonomy_label(value)
        if not label:
            continue
        slug_source = nonempty_string(value.get("slug")) if isinstance(value, dict) else ""
        slug = slugify(slug_source or label)
        existing = merged.setdefault(slug, {"label": label, "slug": slug, "sourceRefs": []})
        for ref in taxonomy_refs(value, fallback_refs):
            if ref not in existing["sourceRefs"]:
                existing["sourceRefs"].append(ref)
    return list(merged.values())


def collect_item_taxonomy(items: list[dict[str, Any]], key: str) -> list[Any]:
    values: list[Any] = []
    for item in items:
        refs = source_refs(item, [])
        for value in as_list(item.get(key)):
            if isinstance(value, dict):
                copied = dict(value)
                copied.setdefault("sourceRefs", refs)
                values.append(copied)
            else:
                values.append({"label": value, "sourceRefs": refs})
    return values


def normalize_taxonomy_plan(
    source_wiki: dict[str, Any],
    products: list[dict[str, Any]],
    posts: list[dict[str, Any]],
    fallback_refs: list[str],
) -> dict[str, Any]:
    source_plan = source_wiki.get("taxonomyPlan") or source_wiki.get("taxonomy")
    if not isinstance(source_plan, dict):
        source_plan = {}
    product_categories = merge_taxonomy_terms(
        as_list(source_plan.get("productCategories")) + collect_item_taxonomy(products, "categories"),
        fallback_refs,
    )
    post_categories = merge_taxonomy_terms(
        as_list(source_plan.get("postCategories")) + collect_item_taxonomy(posts, "categories"),
        fallback_refs,
    )
    product_tags = merge_taxonomy_terms(
        as_list(source_plan.get("productTags")) + collect_item_taxonomy(products, "tags"),
        fallback_refs,
    )
    post_tags = merge_taxonomy_terms(
        as_list(source_plan.get("postTags")) + collect_item_taxonomy(posts, "tags"),
        fallback_refs,
    )
    total_terms = len(product_categories) + len(post_categories) + len(product_tags) + len(post_tags)
    status = nonempty_string(source_plan.get("status"))
    if not status:
        status = "needs_user_confirmation" if total_terms else "explicit_taxonomy_pending_or_not_required"
    return {
        "status": status,
        "productCategories": product_categories,
        "postCategories": post_categories,
        "productTags": product_tags,
        "postTags": post_tags,
        "productCategoryCount": len(product_categories),
        "postCategoryCount": len(post_categories),
        "productTagCount": len(product_tags),
        "postTagCount": len(post_tags),
        "requiresCategorySchemaCapture": True,
        "requiresTagSchemaCapture": True,
        "requiresCreationOrMappingPlan": True,
        "userConfirmationRequired": True,
        "notes": nonempty_string(source_plan.get("notes")),
        "source": "source_wiki_or_derived_from_item_categories_tags",
    }


def draft_manifest(site_key: str, frontend_base: str, content_type: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "siteKey": site_key,
        "contentType": content_type,
        "frontendBaseUrl": frontend_base,
        "schemaVerified": False,
        "fieldMapping": {},
        "payloadTemplate": {},
        "items": items,
    }


def requirements_gaps(requirements: dict[str, Any]) -> dict[str, Any]:
    if not requirements:
        return {"present": False, "blockedFields": [], "userInputFields": [], "entries": []}
    gaps = requirements.get("operationGaps")
    if not isinstance(gaps, dict):
        gaps = {}
    blocked = requirements.get("blockedUntil")
    return {
        "present": True,
        "requirementsPathStatus": requirements.get("overallStatus", "unknown"),
        "blockedFields": as_list(gaps.get("blockedFields")) + as_list(blocked),
        "userInputFields": as_list(gaps.get("userInputFields")),
        "entries": as_list(gaps.get("entries")),
    }


def build_package(args: argparse.Namespace) -> dict[str, Any]:
    source_wiki = load_json(args.source_wiki, "source wiki")
    requirements = load_json(args.requirements, "requirements") if args.requirements else {}
    source = source_set(source_wiki)
    site = normalize_site(source_wiki)
    site_key = nonempty_string(args.site_key) or "{siteKey-after-creation}"
    frontend_base = nonempty_string(args.frontend_base_url) or "https://{siteKey}.web.allincms.com"
    pages = normalize_pages(source_wiki, source["defaultSourceRefs"])
    products = normalize_products(source_wiki, source["defaultSourceRefs"])
    posts = normalize_posts(source_wiki, source["defaultSourceRefs"])
    site_info = normalize_site_info(source_wiki, site)
    navigation = normalize_navigation(source_wiki, pages, products, posts)
    taxonomy_plan = normalize_taxonomy_plan(source_wiki, products, posts, source["defaultSourceRefs"])
    content_goals = normalize_content_goals(source_wiki)
    forms = [item for item in as_list(source_wiki.get("forms")) if isinstance(item, dict)]
    media = [item for item in as_list(source_wiki.get("media")) if isinstance(item, dict)]
    media_policy = normalize_media_policy(source_wiki, pages, products, posts, media, requirements)
    contact_form_policy = normalize_contact_form_policy(source_wiki, forms, site_info, requirements)

    package = {
        "kind": "allincms_source_site_package",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceWiki": args.source_wiki,
        "sourceSet": {
            "inputFiles": source["inputFiles"],
            "rawExtractionRefs": source["rawExtractionRefs"],
            "wikiRefs": source["wikiRefs"],
        },
        "siteProposal": site,
        "contentPlan": {
            "pages": pages,
            "products": products,
            "posts": posts,
            "forms": forms,
            "media": media,
            "mediaPolicy": media_policy,
            "contactFormPolicy": contact_form_policy,
            "navigation": navigation,
            "taxonomyPlan": taxonomy_plan,
            "siteInfo": site_info,
        },
        "declaredContentGoals": content_goals,
        "manifests": {
            "products": draft_manifest(site_key, frontend_base, "products", products),
            "posts": draft_manifest(site_key, frontend_base, "posts", posts),
        },
        "operationGaps": requirements_gaps(requirements),
        "confirmationGate": {
            "required": True,
            "confirmed": False,
            "confirmationEvidence": None,
            "fieldsNeedingUserConfirmation": [
                "siteProposal.siteName",
                "siteProposal.siteDescription",
                "contentPlan.pages",
                "contentPlan.products",
                "contentPlan.posts",
                "contentPlan.forms",
                "contentPlan.media",
                "contentPlan.mediaPolicy",
                "contentPlan.contactFormPolicy",
                "contentPlan.taxonomyPlan",
                "contentPlan.siteInfo",
                "contentPlan.navigation",
                "siteInfo.publicContact",
                "siteInfo.legalCompanyName",
                "domains.customDomain",
                "tracking.trackingCode",
            ],
            "blockedRemoteActions": [
                "create_site",
                "create_theme_page",
                "save_design",
                "bind_route",
                "create_route",
                "upload_media",
                "create_or_map_categories",
                "create_or_map_tags",
                "save_site_settings",
                "upload_products",
                "upload_posts",
                "publish",
                "bind_domain",
                "add_tracking",
            ],
        },
        "schemaGate": {
            "productsSchemaVerified": False,
            "postsSchemaVerified": False,
            "blockedUntilSchemaCapture": ["products", "posts"],
        },
        "adversarialChecks": [
            "Every claim has sourceRefs or is marked for user confirmation.",
            "Products and posts remain draft manifests until current-site save requests are captured.",
            "No domains, tracking snippets, contact channels, prices, inventory, or unsupported claims are treated as confirmed by source files alone.",
            "Raw Markdown must be converted to the captured AllinCMS editor schema before upload.",
            "Media, cover images, logos, and no-image decisions must be user-confirmed and later proven on the public frontend.",
            "Forms, CTA destinations, public contacts, legal identity, and notification destinations must be user-confirmed and later proven or explicitly deferred.",
            "Taxonomy categories/tags must be user-confirmed, mapped or created on the current site, and captured separately from product/post save payloads.",
            "Remote actions remain blocked until user confirmation plus action-specific mutation gates.",
        ],
        "nextActions": [
            "Run validate_source_site_package.py on this package.",
            "Ask the user to review/confirm or revise the generated site package.",
            "After confirmation, create/select the site and capture current schemas before upload.",
        ],
    }
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS source-site package JSON.")
    parser.add_argument("--source-wiki", required=True, help="Distilled source wiki JSON")
    parser.add_argument("--requirements", help="Optional allincms_source_input_requirements JSON")
    parser.add_argument("--site-key", default="", help="Optional existing site key; omit before site creation")
    parser.add_argument("--frontend-base-url", default="", help="Optional existing frontend base URL")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    package = build_package(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source site package: {output}")
    print(
        "counts="
        f"pages:{len(package['contentPlan']['pages'])},"
        f"products:{len(package['contentPlan']['products'])},"
        f"posts:{len(package['contentPlan']['posts'])}"
    )
    if args.json:
        print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
