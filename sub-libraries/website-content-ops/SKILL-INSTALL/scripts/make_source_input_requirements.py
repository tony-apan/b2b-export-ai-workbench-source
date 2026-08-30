#!/usr/bin/env python3
"""Build source-input requirements before generating AllinCMS manifests.

The output is run evidence for PDF/catalog/brief ingestion. It says which
fields can be extracted, which fields need user confirmation, and which fields
are blocked until the current site schema is captured.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from record_source_input_gap import reject_sensitive, validate_ledger


SUPPORTED_CONTENT_TYPES = {
    "products",
    "posts",
    "forms",
    "media",
    "themes/pages",
    "site-info",
    "routes",
    "domains",
    "tracking",
    "navigation",
}
DEFAULT_SOURCE_TYPES = [
    "pdf_catalog",
    "product_datasheet",
    "company_profile",
    "website_copy",
    "image_urls",
    "spreadsheet",
    "sitemap_or_navigation_brief",
    "domain_dns_confirmation",
    "tracking_configuration",
    "plain_brief",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_json(path: str | None) -> Any:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def load_json_many(paths: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_path in paths:
        data = load_json(raw_path)
        if not isinstance(data, dict):
            raise SystemExit(f"ERROR: JSON root must be an object: {raw_path}")
        data["_sourcePath"] = raw_path
        items.append(data)
    return items


def load_resolved_gap_evidence(paths: list[str], site_key: str) -> dict[str, Any]:
    resolved: dict[str, dict[str, Any]] = {}
    sources: list[str] = []
    for raw_path in paths:
        data = load_json(raw_path)
        if not isinstance(data, dict):
            raise SystemExit(f"ERROR: resolved gap evidence JSON root must be an object: {raw_path}")
        if data.get("kind") != "allincms_resolved_source_input_gaps":
            raise SystemExit(f"ERROR: unsupported resolved gap evidence kind: {raw_path}")
        evidence_site_key = data.get("siteKey")
        if evidence_site_key and site_key and evidence_site_key != site_key:
            raise SystemExit(
                f"ERROR: resolved gap evidence siteKey {evidence_site_key!r} does not match {site_key!r}: {raw_path}"
            )
        items = data.get("resolvedGaps")
        if not isinstance(items, list) or not items:
            raise SystemExit(f"ERROR: resolvedGaps must be a non-empty array: {raw_path}")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise SystemExit(f"ERROR: resolvedGaps[{index}] must be an object: {raw_path}")
            label = item.get("fieldLabel")
            proof = item.get("proof")
            note = item.get("note")
            if not isinstance(label, str) or "." not in label or not label.strip():
                raise SystemExit(f"ERROR: resolvedGaps[{index}].fieldLabel must be contentType.field: {raw_path}")
            if not isinstance(proof, str) or not proof.strip():
                raise SystemExit(f"ERROR: resolvedGaps[{index}].proof is required: {raw_path}")
            if not isinstance(note, str) or len(note.strip()) < 12:
                raise SystemExit(f"ERROR: resolvedGaps[{index}].note must explain the superseding evidence: {raw_path}")
            for key, value in {"fieldLabel": label, "proof": proof, "note": note}.items():
                try:
                    reject_sensitive(f"resolvedGaps[{index}].{key}", value)
                except SystemExit as exc:
                    raise SystemExit(str(exc)) from None
            resolved[label] = {
                "fieldLabel": label,
                "proof": proof,
                "note": note,
                "_sourcePath": raw_path,
            }
        sources.append(raw_path)
    return {"sourceFiles": sources, "items": resolved}


def load_gap_ledgers(paths: list[str], site_key: str, resolved_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    sources: list[str] = []
    resolved_items = resolved_evidence.get("items", {}) if isinstance(resolved_evidence, dict) else {}
    if not isinstance(resolved_items, dict):
        resolved_items = {}
    resolved_entries: list[dict[str, Any]] = []
    for raw_path in paths:
        data = load_json(raw_path)
        if not isinstance(data, dict):
            raise SystemExit(f"ERROR: gap ledger JSON root must be an object: {raw_path}")
        if data.get("kind") != "allincms_source_input_gap_ledger":
            raise SystemExit(f"ERROR: unsupported gap ledger kind: {raw_path}")
        errors = validate_ledger(data, expected_site_key=site_key)
        if errors:
            raise SystemExit(
                "ERROR: invalid gap ledger "
                + raw_path
                + ":\n- "
                + "\n- ".join(errors)
            )
        ledger_site_key = data.get("siteKey")
        if ledger_site_key and site_key and ledger_site_key != site_key:
            raise SystemExit(f"ERROR: gap ledger siteKey {ledger_site_key!r} does not match {site_key!r}: {raw_path}")
        ledger_entries = data.get("entries")
        if not isinstance(ledger_entries, list):
            raise SystemExit(f"ERROR: gap ledger entries must be an array: {raw_path}")
        for item in ledger_entries:
            if not isinstance(item, dict):
                raise SystemExit(f"ERROR: gap ledger entry must be an object: {raw_path}")
            copied = dict(item)
            copied["_sourcePath"] = raw_path
            label = f"{copied.get('contentType')}.{copied.get('field')}"
            if label in resolved_items:
                resolved_entry = dict(copied)
                resolved_entry["resolution"] = dict(resolved_items[label])
                resolved_entries.append(resolved_entry)
            else:
                entries.append(copied)
        sources.append(raw_path)
    blocked_fields: list[str] = []
    user_input_fields: list[str] = []
    by_content_type: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    for entry in entries:
        content_type = str(entry.get("contentType", "global"))
        field_name = str(entry.get("field", "unknown"))
        label = f"{content_type}.{field_name}"
        by_content_type[content_type] = by_content_type.get(content_type, 0) + 1
        decision = str(entry.get("decisionNeeded", ""))
        if decision:
            by_decision[decision] = by_decision.get(decision, 0) + 1
        classes = entry.get("classification", [])
        if isinstance(classes, list) and (
            "blocked-until-schema-captured" in classes or decision == "needs-schema-capture"
        ):
            blocked_fields.append(label)
        if isinstance(classes, list) and (
            "user-confirmed" in classes or decision in {"user-must-provide", "needs-user-confirmation"}
        ):
            user_input_fields.append(label)
    return {
        "sourceLedgers": sources,
        "entryCount": len(entries),
        "byContentType": dict(sorted(by_content_type.items())),
        "byDecisionNeeded": dict(sorted(by_decision.items())),
        "blockedFields": sorted(set(blocked_fields)),
        "userInputFields": sorted(set(user_input_fields)),
        "entries": entries,
        "resolvedFields": sorted(resolved_items.keys()),
        "resolvedEntryCount": len(resolved_entries),
        "resolvedEntries": resolved_entries,
        "resolvedEvidenceSources": resolved_evidence.get("sourceFiles", []) if isinstance(resolved_evidence, dict) else [],
    }


def evidence_by_content_type(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in evidence:
        content_type = item.get("contentType")
        if isinstance(content_type, str):
            result[content_type] = item
    return result


def manifest_by_content_type(manifests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        content_type = manifest.get("contentType")
        if isinstance(content_type, str):
            result[content_type] = manifest
    return result


def payload_shape(capture: dict[str, Any] | None) -> dict[str, Any]:
    if not capture:
        return {}
    request_capture = capture.get("requestCapture")
    if not isinstance(request_capture, dict):
        return {}
    shape = request_capture.get("payloadShape")
    return shape if isinstance(shape, dict) else {}


def field_mapping(capture: dict[str, Any] | None) -> dict[str, Any]:
    if not capture:
        return {}
    mapping = capture.get("fieldMapping")
    return mapping if isinstance(mapping, dict) else {}


def captured_key(
    capture: dict[str, Any] | None,
    key: str,
    *,
    empty_schema_blocks: bool = False,
) -> tuple[str, list[str]]:
    shape = payload_shape(capture)
    if key not in shape:
        return "not-captured", ["blocked-until-schema-captured"]
    classifications = ["source-derived"]
    if empty_schema_blocks:
        classifications.append("blocked-until-schema-captured")
        return "request-captured-empty-schema-only", classifications
    return "request-captured", classifications


def content_is_empty_schema_only(capture: dict[str, Any] | None) -> bool:
    if not capture:
        return False
    request_capture = capture.get("requestCapture")
    if not isinstance(request_capture, dict):
        return False
    block_shape = str(request_capture.get("contentBlockShape", "")).lower()
    return "empty" in block_shape and "content" in block_shape


def media_status(media_evidence: dict[str, Any] | None) -> tuple[str, list[str]]:
    if not media_evidence:
        return "not-captured", ["blocked-until-schema-captured"]
    if media_evidence.get("publicUrlVerified") is True and media_evidence.get("backendMediaRowVerified") is True:
        return "sample-verified", ["source-derived"]
    if media_evidence.get("remoteMutationsPerformed") is False or media_evidence.get("requestCaptured") is False:
        return "simulated-only", ["source-derived", "blocked-until-schema-captured"]
    return "captured-needs-review", ["source-derived", "blocked-until-schema-captured"]


def manifest_status(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not manifest:
        return {
            "present": False,
            "schemaVerified": False,
            "itemCount": 0,
            "fieldsPresent": [],
        }
    items = manifest.get("items")
    fields: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                fields.update(str(key) for key in item.keys())
    return {
        "present": True,
        "schemaVerified": manifest.get("schemaVerified") is True,
        "itemCount": len(items) if isinstance(items, list) else 0,
        "fieldsPresent": sorted(fields),
    }


def field(
    name: str,
    backend_key: str,
    requirement: str,
    source_hint: str,
    generation_rule: str,
    current_evidence: str,
    decision_needed: str,
    classification: list[str],
) -> dict[str, Any]:
    classes = sorted(set(classification))
    if "source-derived" in classes and "user-confirmed" in classes:
        source_owner = "source-material-plus-user-confirmation"
    elif "source-derived" in classes:
        source_owner = "source-material"
    elif "user-confirmed" in classes:
        source_owner = "user-confirmation"
    else:
        source_owner = "schema-or-operator-decision"

    if "blocked-until-schema-captured" in classes:
        upload_blocker = "capture current-site schema or record explicit omission/acceptance before live upload"
    elif "user-confirmed" in classes and requirement in {"required", "required_for_rich_detail", "required_for_usable_form", "required_for_polished_site", "required_for_public_page"}:
        upload_blocker = "user confirmation required before live upload"
    else:
        upload_blocker = "none known from this planning record; still verify backend/frontend after save"

    if current_evidence in {"not-captured", "blocked", "simulated-only", "request-captured-empty-schema-only"}:
        potential_issue = "value may be ignored, saved in the wrong shape, or overclaim readiness without real schema proof"
    elif "user-confirmed" in classes:
        potential_issue = "source material may be insufficient or ambiguous without user confirmation"
    else:
        potential_issue = "low schema risk after current evidence, but stale site versions still require verification"

    return {
        "field": name,
        "backendKey": backend_key,
        "requirement": requirement,
        "classification": classes,
        "sourceOwner": source_owner,
        "sourceHint": source_hint,
        "generationRule": generation_rule,
        "currentEvidence": current_evidence,
        "decisionNeeded": decision_needed,
        "potentialIssue": potential_issue,
        "uploadBlocker": upload_blocker,
    }


def product_fields(capture: dict[str, Any] | None, media_evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    mapping = field_mapping(capture)
    body_empty = content_is_empty_schema_only(capture)
    media_evidence_status, media_classes = media_status(media_evidence)

    name_key = str(mapping.get("nameField") or mapping.get("titleField") or "name")
    slug_key = str(mapping.get("slugField") or "slug")
    description_key = str(mapping.get("descriptionField") or "description")
    body_key = str(mapping.get("bodyField") or "content")
    media_key = str(mapping.get("mediaField") or "media")
    media_list_key = str(mapping.get("mediaListField") or "mediaList")
    specifications_key = str(mapping.get("specificationsField") or "specifications")

    name_status, name_classes = captured_key(capture, name_key)
    slug_status, slug_classes = captured_key(capture, slug_key)
    description_status, description_classes = captured_key(capture, description_key)
    body_status, body_classes = captured_key(capture, body_key, empty_schema_blocks=body_empty)
    media_list_status, media_list_classes = captured_key(capture, media_list_key)
    specs_status, specs_classes = captured_key(capture, specifications_key)
    categories_status, categories_classes = captured_key(capture, "categories")
    tags_status, tags_classes = captured_key(capture, "tags")
    order_status, order_classes = captured_key(capture, "order")

    return [
        field(
            "product name",
            name_key,
            "required",
            "Product model/name from catalog title, datasheet heading, or spreadsheet row.",
            "Use concise product name; do not use probe/test prefixes.",
            name_status,
            "Extract from source; user confirms if source has multiple naming levels.",
            ["required", *name_classes],
        ),
        field(
            "slug",
            slug_key,
            "required",
            "Derived from product name/model.",
            "Lowercase ASCII kebab-case; unique per site.",
            slug_status,
            "Can infer, but user must resolve duplicate or preferred SEO slugs.",
            ["required", *slug_classes],
        ),
        field(
            "description",
            description_key,
            "required",
            "Short product summary, application intro, or catalog overview.",
            "Write 1-2 plain-text sentences; no raw Markdown.",
            description_status,
            "Extract or summarize from source; ask user if source lacks a summary.",
            ["required", *description_classes],
        ),
        field(
            "content/body",
            body_key,
            "required_for_rich_detail",
            "Features, benefits, applications, installation notes, warranty, certifications.",
            "Convert to captured editor block schema; do not send raw Markdown tables/bold unless proven.",
            body_status,
            "Blocked until non-empty editor block schema is captured, unless user accepts no-body items.",
            ["required", *body_classes],
        ),
        field(
            "main media",
            media_key,
            "recommended_or_required_if_visual_site",
            "Public product image URL or user-approved uploaded/generated file.",
            "Use captured media object shape; include alt text.",
            media_evidence_status,
            "Blocked until real media upload/public URL proof exists, unless user accepts no-image items.",
            ["recommended", *media_classes],
        ),
        field(
            "media gallery",
            media_list_key,
            "optional",
            "Additional product photos, renderings, certifications, packaging images.",
            "Use captured array item shape; do not guess gallery object schema.",
            media_list_status,
            "Defer unless source has multiple image assets and gallery schema is captured.",
            ["optional", *media_list_classes],
        ),
        field(
            "specifications",
            specifications_key,
            "recommended_for_products",
            "Wattage, lumen, CCT, CRI, beam angle, IP rating, dimensions, voltage, material, certifications.",
            "Generate structured rows/groups from source; do not upload pipe-table Markdown directly.",
            specs_status,
            "Blocked for non-empty upload until specification row/group schema is captured or user omits specs.",
            ["recommended", *specs_classes],
        ),
        field(
            "categories",
            "categories",
            "optional",
            "Product family, application category, or navigation grouping.",
            "Requires captured ids/objects or a captured category creation/selection flow.",
            categories_status,
            "User confirms taxonomy; preserve/omit if category schema is not captured.",
            ["optional", "user-confirmed", *categories_classes],
        ),
        field(
            "tags",
            "tags",
            "optional",
            "Feature, application, certification, or market keywords.",
            "Requires captured ids/objects or a captured tag creation/selection flow.",
            tags_status,
            "User confirms tag policy; omit if no tag schema is captured.",
            ["optional", "user-confirmed", *tags_classes],
        ),
        field(
            "order",
            "order",
            "optional",
            "Desired product ordering from spreadsheet or user priority.",
            "Use integer sort order; default only if user accepts default ordering.",
            order_status,
            "Can infer from source row order or ask user for priority.",
            ["optional", "user-confirmed", *order_classes],
        ),
    ]


def post_fields(capture: dict[str, Any] | None, media_evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    mapping = field_mapping(capture)
    body_empty = content_is_empty_schema_only(capture)
    media_evidence_status, media_classes = media_status(media_evidence)

    title_key = str(mapping.get("titleField") or "title")
    slug_key = str(mapping.get("slugField") or "slug")
    excerpt_key = str(mapping.get("excerptField") or "excerpt")
    body_key = str(mapping.get("bodyField") or "content")
    cover_key = str(mapping.get("coverField") or "coverImage")

    title_status, title_classes = captured_key(capture, title_key)
    slug_status, slug_classes = captured_key(capture, slug_key)
    excerpt_status, excerpt_classes = captured_key(capture, excerpt_key)
    body_status, body_classes = captured_key(capture, body_key, empty_schema_blocks=body_empty)
    categories_status, categories_classes = captured_key(capture, "categories")
    tags_status, tags_classes = captured_key(capture, "tags")

    return [
        field("title", title_key, "required", "Article title from brief, PDF section, or editorial plan.", "Use a clear article title.", title_status, "Extract from source or ask user for title.", ["required", *title_classes]),
        field("slug", slug_key, "required", "Derived from article title.", "Lowercase ASCII kebab-case; unique per site.", slug_status, "Can infer, but user resolves duplicates or SEO preference.", ["required", *slug_classes]),
        field("excerpt", excerpt_key, "recommended", "Short article summary.", "Write 1-2 plain-text sentences; no raw Markdown.", excerpt_status, "Extract/summarize or ask user if summary is absent.", ["recommended", *excerpt_classes]),
        field("content/body", body_key, "required", "Article sections, FAQs, application guide, comparisons.", "Convert to captured posts editor schema; do not reuse product body schema.", body_status, "Blocked until posts save/body schema is captured.", ["required", *body_classes]),
        field("cover image", cover_key, "recommended", "Public article image URL or uploaded media.", "Use captured cover/media object shape; include alt text.", media_evidence_status, "Blocked until media/cover proof exists, unless user accepts text-only posts.", ["recommended", *media_classes]),
        field("categories", "categories", "optional", "Topic or blog category.", "Requires captured ids/objects or category creation flow.", categories_status, "User confirms taxonomy; omit if schema is not captured.", ["optional", "user-confirmed", *categories_classes]),
        field("tags", "tags", "optional", "Topic keywords.", "Requires captured ids/objects or tag creation flow.", tags_status, "User confirms tag policy; omit if schema is not captured.", ["optional", "user-confirmed", *tags_classes]),
    ]


def form_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    name_status, name_classes = captured_key(capture, "name")
    slug_status, slug_classes = captured_key(capture, "slug")
    description_status, description_classes = captured_key(capture, "description")
    fields_status, fields_classes = captured_key(capture, "fields")
    submit_status, submit_classes = captured_key(capture, "submit")
    return [
        field("form name", "name", "required", "Contact, quote request, sample request, or support form purpose.", "Choose from site objective and route placement.", name_status, "User confirms form purpose.", ["required", "user-confirmed", *name_classes]),
        field("slug", "slug", "required", "Derived from form purpose.", "Lowercase ASCII kebab-case.", slug_status, "Can infer once form purpose is confirmed.", ["required", *slug_classes]),
        field("description", "description", "recommended", "What the form is for.", "Plain text; verify whether it is public or internal.", description_status, "User confirms public wording if rendered.", ["recommended", "user-confirmed", *description_classes]),
        field("fields", "fields", "required_for_usable_form", "Name, email, company, message, product interest, quantity, country.", "Must use captured form-field editor schema.", fields_status, "Blocked until form field editor schema is captured.", ["required", "user-confirmed", *fields_classes]),
        field("submit label/success message", "submit", "recommended", "CTA and thank-you copy.", "Plain localized copy; verify request payload keys.", submit_status, "User confirms destination and success message.", ["recommended", "user-confirmed", *submit_classes]),
    ]


def media_fields(media_evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    status, classes = media_status(media_evidence)
    return [
        field(
            "file/image",
            "upload file/media object",
            "required_for_visual_products",
            "Public image URL or local user-approved non-private file.",
            "Real upload or external public URL; verify backend media row and public URL.",
            status,
            "User provides files/URLs or approves generated images; browser upload may need non-in-app path.",
            ["required", "user-confirmed", *classes],
        ),
        field(
            "alt text",
            "alt/name metadata if supported",
            "recommended",
            "Image subject, product name, or application.",
            "Derive alt text from product/media purpose; verify metadata payload if editable.",
            "not-captured" if status == "not-captured" else status,
            "Can infer from source after media schema is captured.",
            ["recommended", "source-derived"] + (["blocked-until-schema-captured"] if status != "sample-verified" else []),
        ),
    ]


def theme_page_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    page_doc_status, page_doc_classes = captured_key(capture, "pageDocument")
    route_status, route_classes = captured_key(capture, "routePath")
    return [
        field(
            "page headline/body copy",
            "pageDocument props",
            "required_for_polished_site",
            "Brand positioning, product categories, applications, differentiators, FAQs.",
            "Map source material to captured page block props; verify save, publish, and frontend DOM.",
            page_doc_status,
            "User/source provides brand and page copy; capture block schema before JSON replay.",
            ["required", "source-derived", *page_doc_classes],
        ),
        field(
            "navigation labels and CTAs",
            "pageDocument actions/links",
            "recommended",
            "Desired pages, conversion actions, route labels, button destinations.",
            "Use captured target object shapes; do not write plain href if action object is required.",
            page_doc_status,
            "User confirms conversion routes and CTA destinations.",
            ["recommended", "user-confirmed", *page_doc_classes],
        ),
        field(
            "route path/binding",
            "routePath/pageId",
            "required_for_public_page",
            "Desired public path and matching theme page.",
            "Verify page published, enabled, bound, theme active, HTTP status, and DOM.",
            route_status,
            "User confirms required routes; schema capture required for create/bind replay.",
            ["required", "user-confirmed", *route_classes],
        ),
    ]


def site_info_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    name_status, name_classes = captured_key(capture, "name")
    description_status, description_classes = captured_key(capture, "description")
    notification_status, notification_classes = captured_key(capture, "notificationEmail")
    return [
        field(
            "site name",
            "name",
            "required",
            "Approved brand, demo name, or product-line site name.",
            "Use only a user-approved public-facing name; do not infer legal company identity from unrelated source files.",
            name_status,
            "User confirms for real sites; temporary demos may use explicit demo naming.",
            ["required", "user-confirmed", *name_classes],
        ),
        field(
            "site description",
            "description",
            "required_for_polished_site",
            "Company profile, catalog overview, website About copy, or user brief.",
            "Summarize conservatively into positioning/SEO copy; avoid unsupported certifications, regions, or capacity claims.",
            description_status,
            "Can draft from source; user confirms final positioning for real sites.",
            ["required", "source-derived", "user-confirmed", *description_classes],
        ),
        field(
            "notification email",
            "notificationEmail",
            "required_for_forms_if_enabled",
            "Public or operational inquiry destination explicitly provided by the user.",
            "Keep private account emails out of public copy; verify whether the field is internal notification only.",
            notification_status,
            "User must provide or confirm; never infer from login/account labels.",
            ["recommended", "user-confirmed", *notification_classes],
        ),
    ]


def route_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    path_status, path_classes = captured_key(capture, "path")
    page_status, page_classes = captured_key(capture, "pageId")
    status_status, status_classes = captured_key(capture, "status")
    return [
        field(
            "public path",
            "path",
            "required_for_public_page",
            "Desired site map from brief, sitemap, navigation plan, or source website.",
            "Normalize to leading-slash route paths and check conflicts before create/bind.",
            path_status,
            "User confirms public sitemap; source can suggest but not authorize route changes.",
            ["required", "user-confirmed", *path_classes],
        ),
        field(
            "bound page",
            "pageId",
            "required_for_public_page",
            "Theme page that should render the route.",
            "Use captured page identifiers from current backend; never invent pageId values.",
            page_status,
            "Blocked until theme page exists and bind/create-route schema is captured.",
            ["required", "user-confirmed", *page_classes],
        ),
        field(
            "route status",
            "status",
            "recommended",
            "Whether route should be enabled/public.",
            "Verify backend status and public HTTP/DOM after binding.",
            status_status,
            "User confirms intended visibility before launch.",
            ["recommended", "user-confirmed", *status_classes],
        ),
    ]


def domain_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    domain_status, domain_classes = captured_key(capture, "domain")
    cname_status, cname_classes = captured_key(capture, "cname")
    return [
        field(
            "custom domain",
            "domain",
            "optional_for_demo_required_for_custom_launch",
            "Domain name explicitly supplied by the user.",
            "Add only after user confirms ownership and intended launch domain.",
            domain_status,
            "User must provide and authorize; never infer from source documents.",
            ["optional", "user-confirmed", *domain_classes],
        ),
        field(
            "DNS/CNAME proof",
            "cname",
            "required_for_custom_launch",
            "DNS record value shown by LAICMS plus external DNS verification.",
            "Record redacted proof that DNS points to the expected target before claiming custom-domain launch.",
            cname_status,
            "Blocked until DNS proof is available or custom domain is explicitly out of scope.",
            ["required", "user-confirmed", *cname_classes],
        ),
    ]


def tracking_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    provider_status, provider_classes = captured_key(capture, "provider")
    snippet_status, snippet_classes = captured_key(capture, "trackingCode")
    return [
        field(
            "analytics provider",
            "provider",
            "optional",
            "Analytics or tracking provider selected by the user.",
            "Do not add third-party tracking to a demo or real site without explicit user approval.",
            provider_status,
            "User must provide provider/account choice.",
            ["optional", "user-confirmed", *provider_classes],
        ),
        field(
            "tracking code",
            "trackingCode",
            "optional",
            "User-provided measurement ID or tracking snippet.",
            "Treat snippets as sensitive operational input; store only redacted evidence and verify frontend load if enabled.",
            snippet_status,
            "User must provide; do not extract from PDFs/catalogs.",
            ["optional", "user-confirmed", *snippet_classes],
        ),
    ]


def navigation_fields(capture: dict[str, Any] | None) -> list[dict[str, Any]]:
    page_doc_status, page_doc_classes = captured_key(capture, "pageDocument")
    nav_status, nav_classes = captured_key(capture, "navigation")
    return [
        field(
            "menu labels",
            "navigation labels or pageDocument nav props",
            "recommended",
            "Sitemap, source website navigation, product categories, and conversion goals.",
            "Generate short labels only after confirming route paths and page targets.",
            nav_status if nav_status != "not-captured" else page_doc_status,
            "Source can suggest labels; user confirms final sitemap and ordering.",
            ["recommended", "source-derived", "user-confirmed", *nav_classes, *page_doc_classes],
        ),
        field(
            "CTA destinations",
            "navigation actions or pageDocument target objects",
            "recommended",
            "Inquiry, quote, contact, catalog download, or product-list destinations.",
            "Use captured target object schema; verify links on frontend.",
            page_doc_status,
            "User confirms conversion routes and external link destinations.",
            ["recommended", "user-confirmed", *page_doc_classes],
        ),
    ]


def global_inputs() -> list[dict[str, Any]]:
    return [
        {
            "field": "brand/site name",
            "target": "site-info.name, theme copy, SEO",
            "requirement": "required",
            "classification": ["required", "user-confirmed"],
            "sourceHint": "Company name, demo brand, or product line name.",
            "generationRule": "Use the user-approved name; do not infer legal identity from unrelated materials.",
            "decisionNeeded": "User must confirm for real sites.",
        },
        {
            "field": "site description",
            "target": "site-info.description, SEO meta, homepage intro",
            "requirement": "required",
            "classification": ["required", "source-derived", "user-confirmed"],
            "sourceHint": "One paragraph company/product positioning from brief, profile, catalog, or website.",
            "generationRule": "Summarize conservatively; avoid claims not supported by source material.",
            "decisionNeeded": "Can draft from source; user confirms final positioning.",
        },
        {
            "field": "contact channels",
            "target": "contact page, forms, footer",
            "requirement": "recommended",
            "classification": ["recommended", "user-confirmed"],
            "sourceHint": "Email, phone, address, WhatsApp, inquiry destination, privacy-safe public contacts.",
            "generationRule": "Do not copy private backend notification emails into public content without approval.",
            "decisionNeeded": "User must provide or approve public contact details.",
        },
        {
            "field": "target markets/applications",
            "target": "homepage, product lists, solution pages, descriptions",
            "requirement": "recommended",
            "classification": ["recommended", "source-derived"],
            "sourceHint": "Applications, industries, geographies, buyer use cases from catalog or brief.",
            "generationRule": "Use as taxonomy and copy source; keep unsupported claims out.",
            "decisionNeeded": "Can infer from source; user resolves priority/order.",
        },
    ]


def build_content_type_section(
    content_type: str,
    site_key: str,
    capture: dict[str, Any] | None,
    manifest: dict[str, Any] | None,
    media_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    if content_type == "products":
        fields = product_fields(capture, media_evidence)
    elif content_type == "posts":
        fields = post_fields(capture, media_evidence)
    elif content_type == "forms":
        fields = form_fields(capture)
    elif content_type == "media":
        fields = media_fields(media_evidence)
    elif content_type == "themes/pages":
        fields = theme_page_fields(capture)
    elif content_type == "site-info":
        fields = site_info_fields(capture)
    elif content_type == "routes":
        fields = route_fields(capture)
    elif content_type == "domains":
        fields = domain_fields(capture)
    elif content_type == "tracking":
        fields = tracking_fields(capture)
    elif content_type == "navigation":
        fields = navigation_fields(capture)
    else:
        raise SystemExit(f"ERROR: unsupported content type: {content_type}")

    blocked_fields = [item["field"] for item in fields if "blocked-until-schema-captured" in item["classification"]]
    user_confirmed = [item["field"] for item in fields if "user-confirmed" in item["classification"]]
    route_part_map = {
        "themes/pages": "themes",
        "navigation": "themes",
    }
    route_part = route_part_map.get(content_type, content_type)
    return {
        "backendRoute": f"/{site_key}/{route_part}",
        "schemaEvidence": {
            "saveCapture": capture.get("_sourcePath") if capture else None,
            "payloadKeys": sorted(payload_shape(capture).keys()),
            "fieldMapping": field_mapping(capture),
            "backendPersisted": capture.get("backendPersisted") if capture else None,
        },
        "manifestEvidence": manifest_status(manifest),
        "fields": fields,
        "blockedFields": blocked_fields,
        "userConfirmedFields": user_confirmed,
        "sectionStatus": "blocked" if blocked_fields else "ready_for_source_extraction",
    }


def collect_blockers(report: dict[str, Any], readiness: dict[str, Any] | None) -> list[str]:
    blockers: list[str] = []
    for content_type, section in report["contentTypes"].items():
        for field_name in section.get("blockedFields", []):
            blockers.append(f"{content_type}.{field_name}: capture schema or record explicit omission/acceptance rule")
    operation_gaps = report.get("operationGaps")
    if isinstance(operation_gaps, dict):
        for field_name in operation_gaps.get("blockedFields", []):
            blockers.append(f"{field_name}: operation-time gap requires schema capture, user decision, or omission rule")
    if isinstance(readiness, dict):
        issues = readiness.get("blockingIssues")
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict):
                    code = issue.get("code")
                    message = issue.get("message")
                    blockers.append(f"{code}: {message}" if code and message else str(issue))
                else:
                    blockers.append(str(issue))
    return sorted(set(blockers))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    content_types = parse_csv(args.content_types)
    unsupported = sorted(set(content_types) - SUPPORTED_CONTENT_TYPES)
    if unsupported:
        raise SystemExit(f"ERROR: unsupported content types: {', '.join(unsupported)}")

    captures = evidence_by_content_type(load_json_many(args.save_capture_evidence))
    manifests = manifest_by_content_type(load_json_many(args.manifest))
    media_evidence = load_json(args.media_evidence)
    if media_evidence is not None and not isinstance(media_evidence, dict):
        raise SystemExit("ERROR: --media-evidence JSON root must be an object")
    readiness = load_json(args.readiness_evidence)
    if readiness is not None and not isinstance(readiness, dict):
        raise SystemExit("ERROR: --readiness-evidence JSON root must be an object")
    resolved_gap_evidence = load_resolved_gap_evidence(getattr(args, "resolved_gap_evidence", []), args.site_key)
    operation_gaps = load_gap_ledgers(getattr(args, "gap_ledger", []), args.site_key, resolved_gap_evidence)

    report: dict[str, Any] = {
        "kind": "allincms_source_input_requirements",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": args.site_key,
        "purpose": (
            "Record what user/source material must provide before generating "
            "AllinCMS manifests from PDFs, catalogs, websites, spreadsheets, or briefs."
        ),
        "sourceTypesSupported": parse_csv(args.source_types) or DEFAULT_SOURCE_TYPES,
        "globalInputs": global_inputs(),
        "operationGaps": operation_gaps,
        "contentTypes": {},
        "rules": [
            "Do not invent missing product specs, prices, certifications, contacts, media, or form destinations.",
            "Do not reuse posts payload schema for products, forms, media, or theme pages.",
            "Keep this requirements record in run evidence; do not store business copy in the skill.",
            "Fields blocked until schema capture must stay out of live upload unless the user records an explicit acceptance/omission rule.",
            "Operation-time gap ledger rows are source-intake contracts; use them before extracting PDF/catalog/website/spreadsheet content.",
        ],
    }
    for content_type in content_types:
        report["contentTypes"][content_type] = build_content_type_section(
            content_type,
            args.site_key,
            captures.get(content_type),
            manifests.get(content_type),
            media_evidence,
        )

    report["nextBestInputFromUser"] = [
        "PDF/catalog/datasheet/website/spreadsheet source files for the selected content types.",
        "Public image URLs or user-approved/generated non-private image files.",
        "Public contact details and form destination policy.",
        "Target content types to publish and any no-image/no-body acceptance rule.",
    ]
    if operation_gaps["userInputFields"]:
        report["nextBestInputFromUser"].append(
            "User confirmation for operation-time fields: " + ", ".join(operation_gaps["userInputFields"])
        )
    report["blockedUntil"] = collect_blockers(report, readiness)
    report["overallStatus"] = "blocked" if report["blockedUntil"] else "ready_for_source_extraction"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AllinCMS source-input requirements JSON.")
    parser.add_argument("--site-key", required=True)
    parser.add_argument(
        "--content-types",
        default="products,posts",
        help="Comma-separated content types: " + ",".join(sorted(SUPPORTED_CONTENT_TYPES)),
    )
    parser.add_argument("--source-types", default=",".join(DEFAULT_SOURCE_TYPES))
    parser.add_argument("--manifest", action="append", default=[], help="Optional manifest JSON; repeatable")
    parser.add_argument(
        "--save-capture-evidence",
        action="append",
        default=[],
        help="Optional save-capture evidence JSON; repeatable",
    )
    parser.add_argument("--media-evidence", help="Optional media upload/public URL evidence JSON")
    parser.add_argument("--readiness-evidence", help="Optional readiness/blocker evidence JSON")
    parser.add_argument(
        "--gap-ledger",
        action="append",
        default=[],
        help="Optional operation-time source-input gap ledger JSON; repeatable",
    )
    parser.add_argument(
        "--resolved-gap-evidence",
        action="append",
        default=[],
        help="Optional resolved/superseded gap evidence JSON; repeatable",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true", help="Also print generated JSON")
    args = parser.parse_args()

    report = build_report(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"Wrote {output}")
    print(f"overallStatus={report['overallStatus']} contentTypes={','.join(report['contentTypes'].keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
