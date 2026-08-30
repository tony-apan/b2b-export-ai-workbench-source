#!/usr/bin/env python3
"""Draft a refined source wiki from an initial source wiki and refinement brief."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from build_source_site_package import slugify
from validate_refined_source_wiki_contract import build_report as build_contract_report
from validate_source_wiki import load_json, validate_source_wiki


PLACEHOLDER_RE = re.compile(
    r"\b(?:draft page copy requires review|requires review|requires source extraction|todo|placeholder|tbd)\b",
    re.IGNORECASE,
)
MIN_PAGE_BODY_CHARS = 140
MIN_PRODUCT_DESCRIPTION_CHARS = 40
MIN_PRODUCT_BODY_CHARS = 100
MIN_POST_EXCERPT_CHARS = 40
MIN_POST_BODY_CHARS = 140
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output refined source wiki must be outside the skill package")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def text(value: Any) -> str:
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def output_path(args: argparse.Namespace, brief: dict[str, Any]) -> Path:
    requested = args.output or text(brief.get("outputRefinedSourceWiki"))
    if not requested:
        raise SystemExit("ERROR: --output is required when brief.outputRefinedSourceWiki is empty")
    output = Path(requested).expanduser().resolve()
    ensure_output_outside_skill(output)
    return output


def first_existing(values: list[str], fallback: str) -> str:
    for value in values:
        cleaned = text(value)
        if cleaned:
            return cleaned
    return fallback


def product_names(wiki: dict[str, Any], limit: int = 4) -> list[str]:
    names: list[str] = []
    for item in as_list(wiki.get("products")):
        if not isinstance(item, dict):
            continue
        name = text(item.get("name")) or text(item.get("title"))
        if name:
            names.append(name)
    return names[:limit]


def product_categories(wiki: dict[str, Any], limit: int = 5) -> list[str]:
    values: list[str] = []
    taxonomy = as_dict(wiki.get("taxonomyPlan"))
    for item in as_list(taxonomy.get("productCategories")):
        if isinstance(item, dict):
            label = text(item.get("label")) or text(item.get("name"))
        else:
            label = text(item)
        if label and label not in values:
            values.append(label)
    for product in as_list(wiki.get("products")):
        if not isinstance(product, dict):
            continue
        for item in as_list(product.get("categories")):
            label = text(item.get("label")) if isinstance(item, dict) else text(item)
            if label and label not in values:
                values.append(label)
    return values[:limit]


def post_topics(wiki: dict[str, Any], limit: int = 3) -> list[str]:
    topics: list[str] = []
    for item in as_list(wiki.get("posts")):
        if not isinstance(item, dict):
            continue
        title = text(item.get("title"))
        if title:
            topics.append(title)
    return topics[:limit]


def declared_goal(wiki: dict[str, Any], key: str) -> int:
    goals = as_dict(wiki.get("contentGoals"))
    value = goals.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def source_refs_for_page(page: dict[str, Any], fallback_refs: list[str]) -> list[str]:
    refs = [ref for ref in as_list(page.get("sourceRefs")) if isinstance(ref, str) and ref.strip()]
    return refs or fallback_refs


def source_refs(wiki: dict[str, Any], brief: dict[str, Any]) -> list[str]:
    refs = [ref for ref in as_list(brief.get("sourceRefs")) if isinstance(ref, str) and ref.strip()]
    if refs:
        return refs
    source_set = as_dict(wiki.get("sourceSet"))
    for item in as_list(source_set.get("inputFiles")):
        if isinstance(item, dict) and text(item.get("sourceRef")):
            refs.append(text(item.get("sourceRef")))
    return refs


def join_list(items: list[str], fallback: str) -> str:
    clean = [item for item in items if item]
    if not clean:
        return fallback
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + ", and " + clean[-1]


def section_text(section: Any) -> str:
    if isinstance(section, dict):
        return " ".join(text(section.get(key)) for key in ("heading", "body", "text") if text(section.get(key))).strip()
    return text(section)


def content_text(value: Any) -> str:
    return " ".join(section_text(item) for item in as_list(value)).strip() if isinstance(value, list) else section_text(value)


def needs_copy_refinement(value: str, min_chars: int) -> bool:
    cleaned = text(value)
    return len(cleaned) < min_chars or bool(PLACEHOLDER_RE.search(cleaned))


def usable_copy(value: Any) -> str:
    cleaned = text(value)
    return "" if not cleaned or PLACEHOLDER_RE.search(cleaned) else cleaned


def normalize_labels(value: Any) -> list[str]:
    labels: list[str] = []
    for item in as_list(value):
        if isinstance(item, dict):
            label = text(item.get("label")) or text(item.get("name")) or text(item.get("title"))
        else:
            label = text(item)
        if label and label not in labels:
            labels.append(label)
    return labels


def normalize_specs(value: Any) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    if isinstance(value, dict):
        iterable = value.items()
        for label, item in iterable:
            clean_label = text(str(label))
            clean_value = text(str(item))
            if clean_label and clean_value:
                specs.append({"label": clean_label, "value": clean_value})
        return specs
    for item in as_list(value):
        if isinstance(item, dict):
            label = text(item.get("label")) or text(item.get("name")) or text(item.get("key"))
            value_text = text(item.get("value")) or text(item.get("text"))
            if label and value_text:
                specs.append({"label": label, "value": value_text})
        elif isinstance(item, str) and text(item):
            specs.append({"label": "spec", "value": text(item)})
    return specs


def product_default_category(product: dict[str, Any], wiki: dict[str, Any]) -> str:
    name = text(product.get("name")) or text(product.get("title"))
    haystack = f"{name} {text(product.get('description'))} {content_text(product.get('content'))}".lower()
    if any(token in haystack for token in ("outdoor", "field", "site", "external")):
        return "Outdoor Products"
    if any(token in haystack for token in ("office", "school", "retail", "commercial", "interior")):
        return "Commercial Products"
    if any(token in haystack for token in ("facility", "factory", "industrial", "workshop", "production")):
        return "Industrial Products"
    categories = product_categories(wiki, limit=1)
    return categories[0] if categories else "Featured Products"


def product_body(product: dict[str, Any], wiki: dict[str, Any], categories: list[str], specs: list[dict[str, str]]) -> str:
    site = as_dict(wiki.get("site"))
    industry = text(site.get("industry")) or "the target industry"
    site_name = text(site.get("siteName")) or "the site"
    name = text(product.get("name")) or text(product.get("title")) or "Product"
    summary = usable_copy(product.get("summary")) or usable_copy(product.get("description"))
    category_text = join_list(categories, product_default_category(product, wiki))
    spec_text = "; ".join(f"{spec['label']}: {spec['value']}" for spec in specs[:6])
    if not summary:
        summary = f"{name} is a source-backed {industry} product option for project buyers comparing performance, application fit, and sourcing requirements."
    details = [
        summary.rstrip(".") + ".",
        f"It belongs to {category_text} and should be presented in {site_name}'s product catalog with source-backed buyer context.",
        "Use the detail page to explain application fit, specification considerations, and inquiry guidance without adding unverified pricing, inventory, certification, or warranty claims.",
    ]
    if spec_text:
        details.insert(1, f"Available source specifications include {spec_text}.")
    return " ".join(details)


def refine_products(wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(wiki.get("products"))):
        if not isinstance(item, dict):
            continue
        product = deepcopy(item)
        name = text(product.get("name")) or text(product.get("title")) or f"Product {index + 1}"
        product["name"] = name
        product["slug"] = text(product.get("slug")) or slugify(name)
        categories = normalize_labels(product.get("categories"))
        category = text(product.get("category"))
        if category and category not in categories:
            categories.append(category)
        if not categories:
            categories = [product_default_category(product, wiki)]
        specs = normalize_specs(product.get("specs"))
        body = product_body(product, wiki, categories, specs)
        if needs_copy_refinement(text(product.get("description")) or text(product.get("summary")), MIN_PRODUCT_DESCRIPTION_CHARS):
            product["description"] = body[:220].rstrip()
        if needs_copy_refinement(content_text(product.get("content")), MIN_PRODUCT_BODY_CHARS):
            product["content"] = [{"type": "paragraph", "text": body}]
        product["specs"] = specs
        product["categories"] = categories
        product["sourceRefs"] = source_refs_for_page(product, fallback_refs)
        products.append(product)
    return products


def post_default_category(post: dict[str, Any]) -> str:
    haystack = f"{text(post.get('title'))} {text(post.get('excerpt'))} {content_text(post.get('content'))}".lower()
    if any(token in haystack for token in ("choose", "selection", "guide", "compare")):
        return "Buying Guides"
    if any(token in haystack for token in ("retrofit", "benefit", "payback", "maintenance")):
        return "Project Planning"
    if any(token in haystack for token in ("use case", "application", "deployment", "facility")):
        return "Application Guides"
    return "Buying Guides"


def post_body(post: dict[str, Any], wiki: dict[str, Any], categories: list[str]) -> str:
    site = as_dict(wiki.get("site"))
    industry = text(site.get("industry")) or "the target industry"
    title = text(post.get("title")) or "Article"
    summary = usable_copy(post.get("summary")) or usable_copy(post.get("excerpt")) or usable_copy(post.get("description"))
    products = join_list(product_names(wiki), "the planned product range")
    category_text = join_list(categories, post_default_category(post))
    if not summary:
        summary = f"This article gives buyers a practical source-backed view of {title.lower()} for {industry} projects."
    return (
        f"{summary.rstrip('.')}. The article should help buyers evaluate project requirements, application fit, operating environment, and sourcing questions. "
        f"It connects the topic to {products} and the {category_text} content category while avoiding unverified savings, certification, pricing, or legal claims. "
        f"Use the final section to guide readers toward comparing specifications and submitting an inquiry after the current site schema and contact policy are confirmed."
    )


def refine_posts(wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(wiki.get("posts"))):
        if not isinstance(item, dict):
            continue
        post = deepcopy(item)
        title = text(post.get("title")) or f"Article {index + 1}"
        post["title"] = title
        post["slug"] = text(post.get("slug")) or slugify(title)
        categories = normalize_labels(post.get("categories"))
        if not categories:
            categories = [post_default_category(post)]
        body = post_body(post, wiki, categories)
        if needs_copy_refinement(text(post.get("excerpt")) or text(post.get("summary")), MIN_POST_EXCERPT_CHARS):
            post["excerpt"] = body[:180].rstrip()
        if needs_copy_refinement(content_text(post.get("content")), MIN_POST_BODY_CHARS):
            post["content"] = [{"type": "paragraph", "text": body}]
        post["categories"] = categories
        post["sourceRefs"] = source_refs_for_page(post, fallback_refs)
        posts.append(post)
    return posts


def path_for_page_label(label: str) -> str:
    cleaned = text(label).strip("-: ")
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered in {"home", "homepage"}:
        return "/"
    return "/" + slugify(cleaned)


def page_candidate_is_reserved(path: str) -> bool:
    normalized = text(path).rstrip("/") or "/"
    return normalized in RESERVED_NAV_PATHS or "{" in normalized or "}" in normalized


def existing_page_paths(pages: list[dict[str, Any]]) -> set[str]:
    return {text(page.get("path")).rstrip("/") or "/" for page in pages if isinstance(page, dict) and text(page.get("path"))}


def all_page_source_text(wiki: dict[str, Any]) -> str:
    parts: list[str] = []
    for page in as_list(wiki.get("pages")):
        if not isinstance(page, dict):
            continue
        parts.append(text(page.get("title")))
        for section in as_list(page.get("sections")):
            parts.append(section_text(section))
    for item in as_list(wiki.get("openQuestions")):
        parts.append(text(item))
    return " ".join(part for part in parts if part)


def required_page_labels_from_text(wiki: dict[str, Any]) -> list[str]:
    haystack = all_page_source_text(wiki)
    if not haystack:
        return []
    labels: list[str] = []
    for match in re.finditer(
        r"\b(?:required\s+pages?|page\s+plan|pages?)\s*:\s*(.+?)(?=\b(?:contact\s+policy|navigation|products?|posts?|articles?|content\s+goals?|site\s+name|industry|audience|positioning)\s*:|$)",
        haystack,
        flags=re.IGNORECASE,
    ):
        segment = match.group(1)
        for raw in re.split(r"\s+-\s+|[,;]\s*|\n+", segment):
            candidate = text(raw).strip("-: ")
            if not candidate:
                continue
            candidate = re.sub(r"\s+(?:page|section)$", "", candidate, flags=re.IGNORECASE).strip()
            if not candidate or len(candidate) > 60:
                continue
            if candidate.lower() in {"required", "pages", "required pages"}:
                continue
            if candidate not in labels:
                labels.append(candidate)
    return labels


def page_body_needs_refinement(page: dict[str, Any]) -> bool:
    body = " ".join(section_text(section) for section in as_list(page.get("sections"))).strip()
    return len(body) < MIN_PAGE_BODY_CHARS or bool(PLACEHOLDER_RE.search(body))


def page_draft_body(page: dict[str, Any], wiki: dict[str, Any]) -> str:
    site = as_dict(wiki.get("site"))
    site_name = text(site.get("siteName")) or "the website"
    site_description = text(site.get("siteDescription")) or "source-backed products and practical buyer information"
    industry = text(site.get("industry")) or "the target industry"
    title = text(page.get("title")) or "Page"
    purpose = text(page.get("purpose")) or "content page"
    products = join_list(product_names(wiki), "the planned product range")
    categories = join_list(product_categories(wiki), "the planned product categories")
    topics = join_list(post_topics(wiki), "buyer education topics")
    title_lower = title.lower()

    if "contact" in title_lower:
        return (
            f"{title} helps project buyers start a focused conversation with {site_name} about {industry} requirements. "
            f"Visitors can describe applications, target specifications, project timing, sample needs, and OEM questions while final public contact channels remain user-confirmed. "
            f"The page should route inquiries toward product families such as {products} and keep notification destinations, legal company details, and custom contact information deferred until the user approves them."
        )
    if "about" in title_lower:
        return (
            f"{title} introduces {site_name} as {site_description} The page explains the product scope around {categories}, highlights representative options such as {products}, "
            f"and gives buyers a concise reason to continue into the catalog or article library. It should stay source-backed, avoid unsupported certification or pricing claims, and keep legal identity details pending user confirmation."
        )
    if title_lower in {"home", "homepage"} or text(page.get("path")) == "/":
        return (
            f"{site_name} presents {site_description} The homepage should guide buyers from the main offer into product categories, featured products such as {products}, "
            f"and educational posts including {topics}. It should make the catalog, article library, and inquiry path visible without claiming unverified domains, tracking, pricing, or legal contact details."
        )
    return (
        f"{title} supports the {purpose} goal for {site_name}. The page summarizes source-backed information for buyers comparing {categories}, points to products such as {products}, "
        f"and connects the content to buyer education topics like {topics}. Keep the copy concise, practical, and pending user confirmation for contact, media, pricing, and unsupported claims."
    )


def refine_pages(wiki: dict[str, Any], fallback_refs: list[str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(wiki.get("pages"))):
        if not isinstance(item, dict):
            continue
        page = deepcopy(item)
        title = text(page.get("title")) or f"Page {index + 1}"
        page["title"] = title
        path = text(page.get("path")) or ("/" if title.lower() == "home" else "/" + slugify(title))
        page["path"] = path if path.startswith("/") else "/" + path
        page["purpose"] = text(page.get("purpose")) or ("homepage" if page["path"] == "/" else "content_page")
        page["sourceRefs"] = source_refs_for_page(page, fallback_refs)
        if page_body_needs_refinement(page):
            page["sections"] = [{"heading": title, "body": page_draft_body(page, wiki)}]
        pages.append(page)
    if not any(page.get("path") == "/" for page in pages):
        home = {
            "title": "Home",
            "path": "/",
            "purpose": "homepage",
            "sourceRefs": fallback_refs,
        }
        home["sections"] = [{"heading": text(as_dict(wiki.get("site")).get("siteName")) or "Home", "body": page_draft_body(home, wiki)}]
        pages.insert(0, home)
    return pages


def navigation_items(wiki: dict[str, Any], pages: list[dict[str, Any]]) -> list[dict[str, str]]:
    existing = as_list(as_dict(wiki.get("navigation")).get("items"))
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, path: str) -> None:
        clean_label = text(label)
        clean_path = text(path)
        if not clean_label or not clean_path:
            return
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
        if clean_path in seen:
            return
        items.append({"label": clean_label, "path": clean_path})
        seen.add(clean_path)

    for item in existing:
        if isinstance(item, dict):
            add(text(item.get("label")), text(item.get("path")))
    add("Home", "/")
    if as_list(wiki.get("products")):
        add("Products", "/products")
    if as_list(wiki.get("posts")):
        add("Posts", "/posts")
    for page in pages:
        if isinstance(page, dict):
            path = text(page.get("path"))
            if path not in {"/", "/products", "/posts"}:
                add(text(page.get("title")), path)
    return items


def navigation_static_pages(wiki: dict[str, Any], existing_pages: list[dict[str, Any]], fallback_refs: list[str]) -> list[dict[str, Any]]:
    existing_paths = existing_page_paths(existing_pages)
    pages: list[dict[str, Any]] = []
    for item in as_list(as_dict(wiki.get("navigation")).get("items")):
        if isinstance(item, str):
            label = item.strip("/").replace("-", " ").title() or "Home"
            path = text(item)
        elif isinstance(item, dict):
            label = text(item.get("label")) or text(item.get("title"))
            path = text(item.get("path"))
        else:
            continue
        if not path:
            continue
        if not path.startswith("/"):
            path = "/" + path
        normalized_path = path.rstrip("/") or "/"
        if page_candidate_is_reserved(normalized_path) or normalized_path in existing_paths:
            continue
        title = label or normalized_path.strip("/").replace("-", " ").title()
        page = {
            "title": title,
            "path": normalized_path,
            "purpose": "navigation_static_page",
            "sourceRefs": fallback_refs,
        }
        page["sections"] = [{"heading": title, "body": page_draft_body(page, wiki)}]
        pages.append(page)
        existing_paths.add(normalized_path)
    return pages


def declared_or_source_static_pages(wiki: dict[str, Any], existing_pages: list[dict[str, Any]], fallback_refs: list[str]) -> list[dict[str, Any]]:
    required_count = declared_goal(wiki, "pages")
    existing_paths = existing_page_paths(existing_pages)
    needed = max(0, required_count - len(existing_paths)) if required_count else 0
    labels = required_page_labels_from_text(wiki)
    if needed and not labels:
        labels = ["About Us", "Applications", "Contact Us", "Solutions", "Resources"]

    pages: list[dict[str, Any]] = []
    for label in labels:
        path = path_for_page_label(label)
        if not path:
            continue
        normalized_path = path.rstrip("/") or "/"
        if page_candidate_is_reserved(normalized_path) or normalized_path in existing_paths:
            continue
        page = {
            "title": label,
            "path": normalized_path,
            "purpose": "declared_source_page",
            "sourceRefs": fallback_refs,
        }
        page["sections"] = [{"heading": label, "body": page_draft_body(page, wiki)}]
        pages.append(page)
        existing_paths.add(normalized_path)
        if needed and len(pages) >= needed:
            break
    return pages


def ensure_policy_objects(wiki: dict[str, Any], pages: list[dict[str, Any]]) -> None:
    site = as_dict(wiki.get("site"))
    site_name = text(site.get("siteName")) or "AllinCMS Site"
    site_description = text(site.get("siteDescription")) or "Source-backed website content for user review."
    site_info = as_dict(wiki.get("siteInfo"))
    site_info.setdefault("draftSeoTitle", site_name)
    site_info.setdefault("draftSeoDescription", site_description)
    site_info.setdefault("publicContact", "requires_user_confirmation")
    site_info.setdefault("legalCompanyName", "requires_user_confirmation")
    wiki["siteInfo"] = site_info

    wiki["navigation"] = {"items": navigation_items(wiki, pages)}

    media_policy = as_dict(wiki.get("mediaPolicy"))
    media_policy.setdefault("status", "needs_user_confirmation")
    media_policy.setdefault("allowedSources", ["source_files", "public_urls_after_user_confirmation"])
    if "source" in media_policy and "notes" not in media_policy:
        media_policy["notes"] = text(media_policy.get("source"))
    wiki["mediaPolicy"] = media_policy

    contact_policy = as_dict(wiki.get("contactFormPolicy"))
    contact_policy.setdefault("status", "needs_user_confirmation")
    contact_policy.setdefault("notificationDestinationPolicy", "requires_user_confirmation")
    contact_policy.setdefault("ctaDestinationPolicy", "requires_user_confirmation")
    contact_policy.setdefault("allowedPublicContactSources", ["user_confirmation", "explicit_source_material"])
    wiki["contactFormPolicy"] = contact_policy

    taxonomy = as_dict(wiki.get("taxonomyPlan"))
    taxonomy.setdefault("status", "needs_user_confirmation")
    ensure_taxonomy_goal_terms(wiki, taxonomy)
    wiki["taxonomyPlan"] = taxonomy


def unique_labels(values: list[Any]) -> list[str]:
    labels: list[str] = []
    for value in values:
        if isinstance(value, dict):
            label = text(value.get("label")) or text(value.get("name")) or text(value.get("title"))
        else:
            label = text(value)
        if label and label not in labels:
            labels.append(label)
    return labels


def set_taxonomy_terms(taxonomy: dict[str, Any], key: str, labels: list[str], fallback_refs: list[str]) -> None:
    existing = as_list(taxonomy.get(key))
    existing_labels = unique_labels(existing)
    merged: list[Any] = list(existing)
    for label in labels:
        if label in existing_labels:
            continue
        merged.append({"label": label, "sourceRefs": fallback_refs})
        existing_labels.append(label)
    taxonomy[key] = merged


def post_category_candidates(wiki: dict[str, Any]) -> list[str]:
    thematic: list[str] = ["Buying Guides"]
    fallback_titles: list[str] = []

    def add_thematic(label: str) -> None:
        if label and label not in thematic:
            thematic.append(label)

    def add_fallback(label: str) -> None:
        if label and label not in fallback_titles and label not in thematic:
            fallback_titles.append(label)

    for post in as_list(wiki.get("posts")):
        if not isinstance(post, dict):
            continue
        title_raw = text(post.get("title"))
        title = title_raw.lower()
        tags_raw = unique_labels(as_list(post.get("tags")))
        tags = " ".join(tags_raw).lower()
        haystack = f"{title} {tags}"
        if any(token in haystack for token in ("retrofit", "checklist", "maintenance", "planning")):
            add_thematic("Project Planning")
        if any(token in haystack for token in ("use case", "application", "deployment", "facility")):
            add_thematic("Application Guides")
        if any(token in haystack for token in ("compare", "selection", "specification", "option")):
            add_thematic("Product Selection")
        if any(token in haystack for token in ("project", "planning", "timeline", "budget")):
            add_thematic("Project Planning")
        if any(token in haystack for token in ("facility", "site", "environment", "workspace", "operation")):
            add_thematic("Application Guides")
        if any(token in haystack for token in ("supplier", "source", "quote", "procurement", "buyer")):
            add_thematic("Sourcing Guides")
        for label in tags_raw:
            add_fallback(label)
        add_fallback(title_raw)
    return thematic + fallback_titles


def ensure_taxonomy_goal_terms(wiki: dict[str, Any], taxonomy: dict[str, Any]) -> None:
    fallback_refs = source_refs(wiki, {})
    product_goal = declared_goal(wiki, "productCategories")
    if product_goal:
        labels = product_categories(wiki, limit=max(product_goal, 5))
        set_taxonomy_terms(taxonomy, "productCategories", labels[:product_goal], fallback_refs)
    post_goal = declared_goal(wiki, "postCategories")
    if post_goal:
        labels = unique_labels(as_list(taxonomy.get("postCategories")))
        for candidate in post_category_candidates(wiki):
            if len(labels) >= post_goal:
                break
            if candidate not in labels:
                labels.append(candidate)
        set_taxonomy_terms(taxonomy, "postCategories", labels[:post_goal], fallback_refs)


def ensure_declared_forms(wiki: dict[str, Any], fallback_refs: list[str]) -> None:
    goal = declared_goal(wiki, "forms")
    forms = [deepcopy(item) for item in as_list(wiki.get("forms")) if isinstance(item, dict)]
    existing_slugs = {text(form.get("slug")) for form in forms if text(form.get("slug"))}
    while goal and len(forms) < goal:
        index = len(forms) + 1
        title = "Project Inquiry Form" if index == 1 else f"Project Inquiry Form {index}"
        slug = slugify(title)
        if slug in existing_slugs:
            slug = f"{slug}-{index}"
        forms.append(
            {
                "title": title,
                "slug": slug,
                "purpose": "Collect project requirements, buyer contact context, and quotation notes after the user confirms public contact and notification policy.",
                "fields": [
                    {"name": "name", "label": "Name", "type": "text", "required": True},
                    {"name": "email", "label": "Email", "type": "email", "required": True},
                    {"name": "company", "label": "Company", "type": "text", "required": False},
                    {"name": "message", "label": "Project Requirements", "type": "textarea", "required": True},
                ],
                "notificationDestinationPolicy": "requires_user_confirmation",
                "submissionProofRequired": True,
                "requiresFormSchemaCapture": True,
                "userConfirmationRequired": True,
                "sourceRefs": fallback_refs,
            }
        )
        existing_slugs.add(slug)
    wiki["forms"] = forms


def media_need_count(items: list[Any]) -> int:
    return sum(len(as_list(item.get("mediaNeeds"))) for item in items if isinstance(item, dict))


def explicit_media_count(wiki: dict[str, Any]) -> int:
    return len([item for item in as_list(wiki.get("media")) if isinstance(item, dict)])


def media_goal_count(wiki: dict[str, Any]) -> int:
    return (
        explicit_media_count(wiki)
        + media_need_count(as_list(wiki.get("pages")))
        + media_need_count(as_list(wiki.get("products")))
        + media_need_count(as_list(wiki.get("posts")))
    )


def target_has_media_need(target: dict[str, Any], target_key: str) -> bool:
    for item in as_list(target.get("mediaNeeds")):
        if isinstance(item, dict) and text(item.get("target")) == target_key:
            return True
    return False


def add_media_need(target: dict[str, Any], need: dict[str, Any]) -> bool:
    target_key = text(need.get("target"))
    if target_key and target_has_media_need(target, target_key):
        return False
    needs = [deepcopy(item) for item in as_list(target.get("mediaNeeds")) if isinstance(item, dict)]
    needs.append(need)
    target["mediaNeeds"] = needs
    return True


def deferred_media_need(target_key: str, kind: str, role: str, label: str, fallback_refs: list[str]) -> dict[str, Any]:
    return {
        "target": target_key,
        "kind": kind,
        "role": role,
        "label": label,
        "source": "user_confirmation_or_public_url_required",
        "status": "needs_user_confirmation",
        "requiresSchemaCapture": True,
        "requiresFrontendImageProof": True,
        "sourceRefs": fallback_refs,
    }


def ensure_declared_media_needs(wiki: dict[str, Any], fallback_refs: list[str]) -> None:
    goal = declared_goal(wiki, "media")
    if not goal:
        return

    pages = as_list(wiki.get("pages"))
    products = as_list(wiki.get("products"))
    posts = as_list(wiki.get("posts"))

    def remaining() -> int:
        return max(0, goal - media_goal_count(wiki))

    for page in pages:
        if remaining() <= 0:
            return
        if not isinstance(page, dict):
            continue
        title = text(page.get("title")) or "Page"
        path = text(page.get("path"))
        if path == "/":
            add_media_need(page, deferred_media_need("home.hero", "image", "hero", "Homepage hero image", fallback_refs))
        elif "contact" not in title.lower():
            add_media_need(
                page,
                deferred_media_need(
                    f"page.{slugify(title)}.section",
                    "image",
                    "page_section",
                    f"{title} section image",
                    fallback_refs,
                ),
            )

    for product in products:
        if remaining() <= 0:
            return
        if not isinstance(product, dict):
            continue
        name = text(product.get("name")) or text(product.get("title")) or "Product"
        add_media_need(
            product,
            deferred_media_need(
                "product.cover",
                "image",
                "product_cover",
                f"{name} product cover image",
                source_refs_for_page(product, fallback_refs),
            ),
        )

    for post in posts:
        if remaining() <= 0:
            return
        if not isinstance(post, dict):
            continue
        title = text(post.get("title")) or "Article"
        add_media_need(
            post,
            deferred_media_need(
                "post.cover",
                "image",
                "post_cover",
                f"{title} article cover image",
                source_refs_for_page(post, fallback_refs),
            ),
        )

    generic_index = 1
    while remaining() > 0 and pages:
        page = next((item for item in pages if isinstance(item, dict)), None)
        if not page:
            break
        add_media_need(
            page,
            deferred_media_need(
                f"site.media.{generic_index}",
                "image",
                "site_supporting",
                f"Site supporting image {generic_index}",
                fallback_refs,
            ),
        )
        generic_index += 1


def clean_open_questions(wiki: dict[str, Any]) -> None:
    cleaned: list[str] = []
    for item in as_list(wiki.get("openQuestions")):
        value = text(item)
        if not value:
            continue
        if PLACEHOLDER_RE.search(value):
            continue
        if value not in cleaned:
            cleaned.append(value)
    wiki["openQuestions"] = cleaned


def build_refined_wiki(args: argparse.Namespace) -> dict[str, Any]:
    source_wiki = load_json(Path(args.source_wiki), "source wiki")
    brief = load_json(Path(args.refinement_brief), "source wiki refinement brief") if args.refinement_brief else {}
    fallback_refs = source_refs(source_wiki, brief)
    if not fallback_refs:
        raise SystemExit("ERROR: source wiki has no source refs")
    refined = deepcopy(source_wiki)
    refined["generatedAt"] = now_iso()
    refined["localOnly"] = True
    refined["remoteMutationsPerformed"] = False
    refined["products"] = refine_products(refined, fallback_refs)
    refined["posts"] = refine_posts(refined, fallback_refs)
    refined["pages"] = refine_pages(refined, fallback_refs)
    refined["pages"].extend(navigation_static_pages(refined, refined["pages"], fallback_refs))
    refined["pages"].extend(declared_or_source_static_pages(refined, refined["pages"], fallback_refs))
    ensure_declared_forms(refined, fallback_refs)
    ensure_declared_media_needs(refined, fallback_refs)
    ensure_policy_objects(refined, refined["pages"])
    clean_open_questions(refined)
    notes = as_list(refined.get("adversarialNotes"))
    notes.append(
        "Page, product, and post copy was deterministically expanded from source-wiki site, product, post, navigation, taxonomy, and policy fields; user confirmation and live AllinCMS schema capture remain required."
    )
    refined["adversarialNotes"] = notes
    return refined


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft a refined AllinCMS source wiki from local source-wiki artifacts.")
    parser.add_argument("--source-wiki", required=True)
    parser.add_argument("--refinement-brief", default="")
    parser.add_argument("--inventory", default="")
    parser.add_argument("--output", default="", help="Defaults to refinement brief outputRefinedSourceWiki")
    parser.add_argument("--validate-contract", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    brief = load_json(Path(args.refinement_brief), "source wiki refinement brief") if args.refinement_brief else {}
    output = output_path(args, brief)
    refined = build_refined_wiki(args)
    inventory = load_json(Path(args.inventory), "inventory") if args.inventory else None
    issues = validate_source_wiki(refined, inventory)
    if issues:
        print("ERROR: drafted refined source wiki is invalid:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 2
    write_json(output, refined)
    contract_report: dict[str, Any] | None = None
    if args.validate_contract and args.refinement_brief:
        contract_report = build_contract_report(
            argparse.Namespace(
                refined_source_wiki=str(output),
                refinement_brief=args.refinement_brief,
                inventory=args.inventory,
                output="",
                json=False,
            )
        )
        if contract_report.get("issues"):
            print("ERROR: drafted refined source wiki failed refinement contract:", file=sys.stderr)
            for issue in contract_report["issues"]:
                print(f"- {issue}", file=sys.stderr)
            return 2
    summary = {
        "kind": "allincms_draft_refined_source_wiki_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "sourceWiki": args.source_wiki,
        "refinementBrief": args.refinement_brief,
        "inventory": args.inventory,
        "outputRefinedSourceWiki": str(output),
        "pageCount": len(as_list(refined.get("pages"))),
        "productCount": len(as_list(refined.get("products"))),
        "postCount": len(as_list(refined.get("posts"))),
        "validationIssues": issues,
        "contractIssues": contract_report.get("issues", []) if contract_report else [],
        "nextAction": "run apply_refined_source_wiki.py and require reviewReady=true before user confirmation",
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote drafted refined source wiki: {output}")
        print(summary["nextAction"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
