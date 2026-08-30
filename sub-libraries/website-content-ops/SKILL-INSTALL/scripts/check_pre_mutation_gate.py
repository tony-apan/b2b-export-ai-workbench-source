#!/usr/bin/env python3
"""Validate the final gate before an AllinCMS remote mutation."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path

from make_authorization_record import validate_record as validate_authorization_record
from validate_manifest_sample_upload_evidence import validate_sample_evidence
from validate_run_evidence import validate as validate_run_evidence

DEFAULT_MAX_AGE_MINUTES = 30
PROBE_ACTION_MODULES = {
    "create_post_probe": ("posts", "posts"),
    "create_product_probe": ("products", "products"),
    "create_form_probe": ("forms", "forms"),
}
SAVE_PROBE_MODULES = {
    "posts": "posts",
    "products": "products",
    "forms": "forms",
}
PUBLISH_PROBE_MODULES = {
    "posts": "posts",
    "products": "products",
}
CLEANUP_PROBE_MODULES = {
    "posts": "posts",
    "products": "products",
    "forms": "forms",
}
BATCH_ACTION_MODULES = {
    "posts": "posts",
    "products": "products",
}
BATCH_ACTION_REQUIRED_FIELDS = {
    "batch_upload": {"schemaGatePass", "sampleVerification", "progressLog", "frontendDetailAudit"},
    "batch_publish": {"schemaGatePass", "sampleVerification", "progressLog", "frontendDetailAudit"},
}
EXISTING_CONTENT_ACTION_MODULES = {
    "save_product": ("products", "products"),
    "publish_product": ("products", "products"),
    "save_post": ("posts", "posts"),
    "publish_post": ("posts", "posts"),
}
EXISTING_CONTENT_ACTION_REQUIRED_FIELDS = {
    "save_product": {"requestCapture", "payloadShape", "persistedVerified", "bodyOrMediaAudit"},
    "save_post": {"requestCapture", "payloadShape", "persistedVerified", "bodyOrMediaAudit"},
    "publish_product": {"publishStatus", "backendVerified", "frontendVerified"},
    "publish_post": {"publishStatus", "backendVerified", "frontendVerified"},
}
SITE_ACTION_MODULES = {
    "save_site_settings": ("site-info", "site-info"),
    "create_theme": ("themes", "themes"),
    "activate_theme": ("themes", "themes"),
    "save_design": ("themes", "theme-design"),
    "publish_design": ("themes", "theme-design"),
    "create_theme_page": ("themes", "theme-page"),
    "set_homepage": ("themes", "theme-page"),
    "enable_theme_page": ("themes", "theme-page"),
    "bind_route": ("routes", "routes"),
    "create_route": ("routes", "routes"),
    "create_form": ("forms", "forms"),
    "add_domain": ("domains", "domains"),
    "add_tracking_tag": ("tracking", "tracking"),
    "create_or_map_products_category": ("products", "products-category"),
    "create_or_map_products_tag": ("products", "products-tag"),
    "create_or_map_posts_category": ("posts", "posts-category"),
    "create_or_map_posts_tag": ("posts", "posts-tag"),
}
SITE_ACTION_REQUIRED_FIELDS = {
    "save_site_settings": {"fieldMapping", "persistedVerified"},
    "create_theme": {"requestCapture", "themeId", "backendVerified"},
    "activate_theme": {"themeId", "routeMappingReviewed", "themeEnabled", "frontendVerified"},
    "save_design": {"requestCapture", "pageDocument", "persistedVerified"},
    "publish_design": {"publishStatus", "frontendVerified"},
    "create_theme_page": {"requestCapture", "pageId", "routePath", "backendVerified"},
    "set_homepage": {"homepage", "frontendVerified"},
    "enable_theme_page": {"enabled", "frontendVerified"},
    "bind_route": {"routePath", "boundPage", "frontendVerified"},
    "create_route": {"routePath", "backendVerified", "frontendVerified"},
    "create_form": {"requestCapture", "formId", "backendVerified"},
    "add_domain": {"domain", "backendVerified", "dnsFollowup"},
    "add_tracking_tag": {"googleTagId", "backendVerified"},
    "create_or_map_products_category": {"requestCapture", "taxonomyTerm", "backendVerified", "mappingVerified"},
    "create_or_map_products_tag": {"requestCapture", "taxonomyTerm", "backendVerified", "mappingVerified"},
    "create_or_map_posts_category": {"requestCapture", "taxonomyTerm", "backendVerified", "mappingVerified"},
    "create_or_map_posts_tag": {"requestCapture", "taxonomyTerm", "backendVerified", "mappingVerified"},
}
MEDIA_ACTION_REQUIRED_FIELDS = {
    "upload_media": {"uploadFile", "requestCapture", "mediaId", "publicUrl", "backendVerified", "cleanupPlan"},
}


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def parse_timestamp(value: object, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: generatedAt is required")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label}: generatedAt must be an ISO 8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{label}: generatedAt must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def validate_freshness(
    preflight: dict,
    authorization: dict,
    max_age_minutes: int,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    if max_age_minutes <= 0:
        errors.append("max_age_minutes must be positive")
        return errors

    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    max_age = timedelta(minutes=max_age_minutes)
    preflight_at = parse_timestamp(preflight.get("generatedAt"), "preflight", errors)
    authorization_at = parse_timestamp(authorization.get("generatedAt"), "authorization", errors)

    for label, generated_at in (("preflight", preflight_at), ("authorization", authorization_at)):
        if generated_at is None:
            continue
        age = now_utc - generated_at
        if age < timedelta(0):
            errors.append(f"{label}: generatedAt must not be in the future")
        elif age > max_age:
            errors.append(f"{label}: generatedAt is stale; regenerate within {max_age_minutes} minutes")

    if preflight_at and authorization_at and authorization_at < preflight_at:
        errors.append("authorization: generatedAt must be at or after preflight.generatedAt")

    return errors


def validate_run_evidence_allowing(preflight: dict, allowed_prefixes: tuple[str, ...] = ()) -> list[str]:
    return [
        error
        for error in validate_run_evidence(preflight)
        if not any(error.startswith(prefix) for prefix in allowed_prefixes)
    ]


def validate_create_site_gate(
    preflight: dict,
    authorization: dict,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
    expected_target_identifier: str = "",
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"preflight: {error}" for error in validate_run_evidence(preflight))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    site_creation = preflight.get("siteCreation")
    if not isinstance(site_creation, dict):
        errors.append("preflight.siteCreation must be an object")
    else:
        if site_creation.get("status") != "create_preflight_verified":
            errors.append("preflight.siteCreation.status must be create_preflight_verified")
        if site_creation.get("dialogClosedVerified") is not True:
            errors.append("preflight.siteCreation.dialogClosedVerified must be true")
        if not isinstance(site_creation.get("existingSiteKeysBeforeCreate"), list):
            errors.append("preflight.siteCreation.existingSiteKeysBeforeCreate must be an array")
        fields = site_creation.get("createSiteFields")
        joined = " ".join(item for item in fields if isinstance(item, str)) if isinstance(fields, list) else ""
        for term in ("name", "description"):
            if term not in joined.lower():
                errors.append(f"preflight.siteCreation.createSiteFields must include {term}")
        if "close" not in joined.lower():
            errors.append("preflight.siteCreation.createSiteFields must include close control")
        if "submit" not in joined.lower() and "创建" not in joined:
            errors.append("preflight.siteCreation.createSiteFields must include submit/create control")

    if authorization.get("action") != "create_site":
        errors.append("authorization.action must be create_site")
    if authorization.get("target") != "https://workspace.laicms.com/sites":
        errors.append("authorization.target must be https://workspace.laicms.com/sites")
    if expected_target_identifier:
        actual_identifier = authorization.get("targetIdentifier")
        if actual_identifier != expected_target_identifier:
            errors.append("authorization.targetIdentifier must match the confirmed siteProposal.siteName")
    fields_or_files = authorization.get("fieldsOrFiles")
    if not isinstance(fields_or_files, list) or not {"name", "description"}.issubset(set(fields_or_files)):
        errors.append("authorization.fieldsOrFiles must include name and description")
    return errors


def validate_probe_gate(
    preflight: dict,
    authorization: dict,
    action: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"preflight: {error}" for error in validate_run_evidence(preflight))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    expected = PROBE_ACTION_MODULES.get(action)
    if expected is None:
        errors.append(f"unsupported probe action: {action}")
        return errors
    module, content_type = expected

    if preflight.get("mode") not in {"read_only_simulation", "site_creation"}:
        errors.append("preflight.mode must be read_only_simulation or site_creation before creating a probe")
    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before creating a probe")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before creating a probe")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")
        module_routes = site_identity.get("moduleRoutes")
        expected_route = f"/{site_key}/{module}" if site_key else ""
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")

    content_inspection = preflight.get("contentInspection")
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before creating a probe")
    else:
        if content_inspection.get("contentType") != content_type:
            errors.append(f"preflight.contentInspection.contentType must be {content_type}")
        list_columns = content_inspection.get("listColumns")
        if not isinstance(list_columns, list) or not list_columns:
            errors.append("preflight.contentInspection.listColumns must be a non-empty array")
        edit_fields = content_inspection.get("editFields")
        if not isinstance(edit_fields, list) or not edit_fields:
            errors.append("preflight.contentInspection.editFields must explain edit/probe field status")

    expected_target = f"https://workspace.laicms.com/{site_key}/{module}" if site_key else ""
    if authorization.get("action") != action:
        errors.append(f"authorization.action must be {action}")
    if expected_target and authorization.get("target") != expected_target:
        errors.append(f"authorization.target must be {expected_target}")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or "Codex Probe - Delete Me" not in target_identifier:
        errors.append('authorization.targetIdentifier must include "Codex Probe - Delete Me"')
    fields_or_files = authorization.get("fieldsOrFiles")
    if not isinstance(fields_or_files, list) or not fields_or_files:
        errors.append("authorization.fieldsOrFiles must describe expected probe fields")
    return errors


def validate_save_probe_gate(
    preflight: dict,
    authorization: dict,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        f"preflight: {error}"
        for error in validate_run_evidence_allowing(
            preflight,
            ("requestCapture:", "sampleVerification:", "cleanup.candidates:"),
        )
    )
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before saving a probe")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before saving a probe")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")

    content_inspection = preflight.get("contentInspection")
    content_type = ""
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before saving a probe")
    else:
        content_type_value = content_inspection.get("contentType")
        if isinstance(content_type_value, str):
            content_type = content_type_value
        else:
            errors.append("preflight.contentInspection.contentType must be a string")
        if content_type_value not in SAVE_PROBE_MODULES:
            errors.append(f"preflight.contentInspection.contentType must be one of {sorted(SAVE_PROBE_MODULES)}")
        edit_fields = content_inspection.get("editFields")
        if not isinstance(edit_fields, list) or not edit_fields:
            errors.append("preflight.contentInspection.editFields must explain save/probe field status")

    module = SAVE_PROBE_MODULES.get(content_type, "")
    if site_key and module:
        module_routes = site_identity.get("moduleRoutes") if isinstance(site_identity, dict) else None
        expected_route = f"/{site_key}/{module}"
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")
        target = authorization.get("target")
        if not isinstance(target, str) or not target.startswith(f"https://workspace.laicms.com/{site_key}/{module}"):
            errors.append(f"authorization.target must be under https://workspace.laicms.com/{site_key}/{module}")

    if authorization.get("action") != "save_probe":
        errors.append("authorization.action must be save_probe")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if content_type and authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or "Codex Probe - Delete Me" not in target_identifier:
        errors.append('authorization.targetIdentifier must include "Codex Probe - Delete Me"')
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = {"requestCapture", "payloadShape", "persistedVerified"}
    if not required_fields.issubset(field_set):
        errors.append("authorization.fieldsOrFiles must include requestCapture, payloadShape, and persistedVerified")
    return errors


def validate_publish_probe_gate(
    preflight: dict,
    authorization: dict,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        f"preflight: {error}"
        for error in validate_run_evidence_allowing(
            preflight,
            ("sampleVerification:", "cleanup.candidates:"),
        )
    )
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before publishing a probe")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before publishing a probe")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")

    content_inspection = preflight.get("contentInspection")
    content_type = ""
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before publishing a probe")
    else:
        content_type_value = content_inspection.get("contentType")
        if isinstance(content_type_value, str):
            content_type = content_type_value
        else:
            errors.append("preflight.contentInspection.contentType must be a string")
        if content_type_value not in PUBLISH_PROBE_MODULES:
            errors.append(f"preflight.contentInspection.contentType must be one of {sorted(PUBLISH_PROBE_MODULES)}")
        edit_fields = content_inspection.get("editFields")
        joined_fields = " ".join(item for item in edit_fields if isinstance(item, str)) if isinstance(edit_fields, list) else ""
        if not joined_fields or ("publish" not in joined_fields.lower() and "发布" not in joined_fields):
            errors.append("preflight.contentInspection.editFields must include publish control evidence")

    module = PUBLISH_PROBE_MODULES.get(content_type, "")
    if site_key and module:
        module_routes = site_identity.get("moduleRoutes") if isinstance(site_identity, dict) else None
        expected_route = f"/{site_key}/{module}"
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")
        target = authorization.get("target")
        if not isinstance(target, str) or not target.startswith(f"https://workspace.laicms.com/{site_key}/{module}"):
            errors.append(f"authorization.target must be under https://workspace.laicms.com/{site_key}/{module}")

    if authorization.get("action") != "publish_probe":
        errors.append("authorization.action must be publish_probe")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if content_type and authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or "Codex Probe - Delete Me" not in target_identifier:
        errors.append('authorization.targetIdentifier must include "Codex Probe - Delete Me"')
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = {"publishStatus", "frontendVerified"}
    if not required_fields.issubset(field_set):
        errors.append("authorization.fieldsOrFiles must include publishStatus and frontendVerified")
    return errors


def validate_cleanup_probe_gate(
    preflight: dict,
    authorization: dict,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"preflight: {error}" for error in validate_run_evidence(preflight))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before cleaning a probe")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before cleaning a probe")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")

    content_inspection = preflight.get("contentInspection")
    content_type = ""
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before cleaning a probe")
    else:
        content_type_value = content_inspection.get("contentType")
        if isinstance(content_type_value, str):
            content_type = content_type_value
        else:
            errors.append("preflight.contentInspection.contentType must be a string")
        if content_type_value not in CLEANUP_PROBE_MODULES:
            errors.append(f"preflight.contentInspection.contentType must be one of {sorted(CLEANUP_PROBE_MODULES)}")

    module = CLEANUP_PROBE_MODULES.get(content_type, "")
    if site_key and module:
        module_routes = site_identity.get("moduleRoutes") if isinstance(site_identity, dict) else None
        expected_route = f"/{site_key}/{module}"
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")
        target = authorization.get("target")
        if not isinstance(target, str) or not target.startswith(f"https://workspace.laicms.com/{site_key}/{module}"):
            errors.append(f"authorization.target must be under https://workspace.laicms.com/{site_key}/{module}")

    if authorization.get("action") != "cleanup_probe":
        errors.append("authorization.action must be cleanup_probe")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if content_type and authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or "Codex Probe - Delete Me" not in target_identifier:
        errors.append('authorization.targetIdentifier must include "Codex Probe - Delete Me"')
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = {"cleanedCandidates", "backendVerified", "frontendVerified"}
    if not required_fields.issubset(field_set):
        errors.append("authorization.fieldsOrFiles must include cleanedCandidates, backendVerified, and frontendVerified")
    return errors


def validate_batch_gate(
    preflight: dict,
    authorization: dict,
    action: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
    sample_evidence: dict | None = None,
) -> list[str]:
    errors: list[str] = []
    allowed_prefixes: tuple[str, ...] = ()
    if sample_evidence is not None:
        allowed_prefixes = ("sampleVerification:",)
    errors.extend(f"preflight: {error}" for error in validate_run_evidence_allowing(preflight, allowed_prefixes))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    if action not in BATCH_ACTION_REQUIRED_FIELDS:
        errors.append(f"unsupported batch action: {action}")
        return errors

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before batch upload or publish")
    if preflight.get("uploadInScope") is not True and preflight.get("mode") != "batch_upload":
        errors.append("preflight.uploadInScope must be true or mode must be batch_upload before batch upload or publish")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before batch upload or publish")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")

    content_inspection = preflight.get("contentInspection")
    content_type = ""
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before batch upload or publish")
    else:
        content_type_value = content_inspection.get("contentType")
        if isinstance(content_type_value, str):
            content_type = content_type_value
        else:
            errors.append("preflight.contentInspection.contentType must be a string")
        if content_type_value not in BATCH_ACTION_MODULES:
            errors.append(f"preflight.contentInspection.contentType must be one of {sorted(BATCH_ACTION_MODULES)}")
        if not isinstance(content_inspection.get("listColumns"), list) or not content_inspection.get("listColumns"):
            errors.append("preflight.contentInspection.listColumns must be present before batch upload or publish")
        if not isinstance(content_inspection.get("editFields"), list) or not content_inspection.get("editFields"):
            errors.append("preflight.contentInspection.editFields must be present before batch upload or publish")

    module = BATCH_ACTION_MODULES.get(content_type, "")
    if site_key and module:
        module_routes = site_identity.get("moduleRoutes") if isinstance(site_identity, dict) else None
        expected_route = f"/{site_key}/{module}"
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")
        target = authorization.get("target")
        if not isinstance(target, str) or not target.startswith(f"https://workspace.laicms.com/{site_key}/{module}"):
            errors.append(f"authorization.target must be under https://workspace.laicms.com/{site_key}/{module}")

    request_capture = preflight.get("requestCapture")
    if not isinstance(request_capture, dict):
        errors.append("preflight.requestCapture must be present before batch upload or publish")
    else:
        if request_capture.get("persistedVerified") is not True:
            errors.append("preflight.requestCapture.persistedVerified must be true before batch upload or publish")
        for key in ("url", "method", "headers", "payloadShape"):
            value = request_capture.get(key)
            if not (
                (isinstance(value, str) and value.strip())
                or (isinstance(value, dict) and value)
                or (isinstance(value, list) and value)
            ):
                errors.append(f"preflight.requestCapture.{key} must be present before batch upload or publish")

    sample = preflight.get("sampleVerification")
    if sample_evidence is not None:
        sample_manifest = {
            "siteKey": site_key,
            "contentType": content_type,
            "frontendBaseUrl": f"https://{site_key}.web.allincms.com" if site_key else "",
            "schemaVerified": True,
            "fieldMapping": {"nameField": "evidence-bound", "slugField": "slug"},
            "payloadTemplate": {"mode": "evidence-bound"},
            "items": [{"slug": sample_evidence.get("sampleSlug"), "name": "evidence-bound", "description": "evidence-bound", "content": "evidence-bound"}],
        }
        errors.extend(f"sampleEvidence: {error}" for error in validate_sample_evidence(sample_evidence, sample_manifest))
    elif not isinstance(sample, dict):
        errors.append("preflight.sampleVerification must be present before batch upload or publish")
    else:
        for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "coverOrMediaVerified", "bodyVerified"):
            if sample.get(key) is not True:
                errors.append(f"preflight.sampleVerification.{key} must be true before batch upload or publish")

    if authorization.get("action") != action:
        errors.append(f"authorization.action must be {action}")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if content_type and authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or not target_identifier.strip():
        errors.append("authorization.targetIdentifier must describe the manifest or batch identifier")
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = BATCH_ACTION_REQUIRED_FIELDS[action]
    if not required_fields.issubset(field_set):
        errors.append(f"authorization.fieldsOrFiles must include {', '.join(sorted(required_fields))}")
    return errors


def validate_existing_content_gate(
    preflight: dict,
    authorization: dict,
    action: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        f"preflight: {error}"
        for error in validate_run_evidence_allowing(
            preflight,
            ("sampleVerification:", "cleanup.candidates:"),
        )
    )
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    expected = EXISTING_CONTENT_ACTION_MODULES.get(action)
    if expected is None:
        errors.append(f"unsupported existing content action: {action}")
        return errors
    module, content_type = expected

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before updating existing content")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before updating existing content")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")
        module_routes = site_identity.get("moduleRoutes")
        expected_route = f"/{site_key}/{module}" if site_key else ""
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")

    content_inspection = preflight.get("contentInspection")
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before updating existing content")
    else:
        if content_inspection.get("contentType") != content_type:
            errors.append(f"preflight.contentInspection.contentType must be {content_type}")
        if not isinstance(content_inspection.get("listColumns"), list) or not content_inspection.get("listColumns"):
            errors.append("preflight.contentInspection.listColumns must be present before updating existing content")
        edit_fields = content_inspection.get("editFields")
        joined_fields = " ".join(item for item in edit_fields if isinstance(item, str)) if isinstance(edit_fields, list) else ""
        if not joined_fields:
            errors.append("preflight.contentInspection.editFields must be present before updating existing content")
        if action.startswith("save_") and not (
            "update" in joined_fields.lower()
            or "save" in joined_fields.lower()
            or "\u66f4\u65b0" in joined_fields
            or "\u4fdd\u5b58" in joined_fields
        ):
            errors.append("preflight.contentInspection.editFields must include update/save control evidence")
        if action.startswith("publish_") and not ("publish" in joined_fields.lower() or "\u53d1\u5e03" in joined_fields):
            errors.append("preflight.contentInspection.editFields must include publish control evidence")

    if authorization.get("action") != action:
        errors.append(f"authorization.action must be {action}")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if authorization.get("targetType") != content_type:
        errors.append(f"authorization.targetType must be {content_type}")
    if site_key:
        target = authorization.get("target")
        expected_prefix = f"https://workspace.laicms.com/{site_key}/{module}"
        if not isinstance(target, str) or not target.startswith(expected_prefix):
            errors.append(f"authorization.target must be under {expected_prefix}")
        if isinstance(target, str) and not target.rstrip("/").endswith("/update"):
            errors.append("authorization.target must be a concrete existing content edit URL ending in /update")

    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or not target_identifier.strip():
        errors.append("authorization.targetIdentifier must describe the exact existing content title or slug")
    elif "Codex Probe - Delete Me" in target_identifier:
        errors.append("authorization.targetIdentifier must not be a probe item for existing content actions")
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = EXISTING_CONTENT_ACTION_REQUIRED_FIELDS[action]
    if not required_fields.issubset(field_set):
        errors.append(f"authorization.fieldsOrFiles must include {', '.join(sorted(required_fields))}")
    return errors


def validate_site_action_gate(
    preflight: dict,
    authorization: dict,
    action: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"preflight: {error}" for error in validate_run_evidence(preflight))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    expected = SITE_ACTION_MODULES.get(action)
    if expected is None:
        errors.append(f"unsupported site action: {action}")
        return errors
    module, target_type = expected

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before mutating site setup or theme state")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before mutating site setup or theme state")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")
        module_routes = site_identity.get("moduleRoutes")
        expected_route = f"/{site_key}/{module}" if site_key else ""
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")

    setup_pages = preflight.get("setupPages")
    if not isinstance(setup_pages, dict):
        errors.append("preflight.setupPages must be present before mutating site setup or theme state")
    else:
        page_key = "siteInfo" if module == "site-info" else module
        if module in {"themes", "routes", "forms", "site-info", "domains", "tracking", "products", "posts"}:
            if not isinstance(setup_pages.get(page_key), list) or not setup_pages.get(page_key):
                errors.append(f"preflight.setupPages.{page_key} must contain read-only inspection evidence")

    if authorization.get("action") != action:
        errors.append(f"authorization.action must be {action}")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if authorization.get("targetType") != target_type:
        errors.append(f"authorization.targetType must be {target_type}")
    if site_key:
        target = authorization.get("target")
        expected_prefix = f"https://workspace.laicms.com/{site_key}/{module}"
        if not isinstance(target, str) or not target.startswith(expected_prefix):
            errors.append(f"authorization.target must be under {expected_prefix}")

    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or not target_identifier.strip():
        errors.append("authorization.targetIdentifier must describe the exact site/theme/page/route/form target")
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = SITE_ACTION_REQUIRED_FIELDS[action]
    if not required_fields.issubset(field_set):
        errors.append(f"authorization.fieldsOrFiles must include {', '.join(sorted(required_fields))}")
    return errors


def validate_media_action_gate(
    preflight: dict,
    authorization: dict,
    action: str,
    max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"preflight: {error}" for error in validate_run_evidence(preflight))
    errors.extend(f"authorization: {error}" for error in validate_authorization_record(authorization))
    errors.extend(validate_freshness(preflight, authorization, max_age_minutes, now))

    if action not in MEDIA_ACTION_REQUIRED_FIELDS:
        errors.append(f"unsupported media action: {action}")
        return errors

    if preflight.get("completionClaimed") is True:
        errors.append("preflight.completionClaimed must be false before media upload")

    site_identity = preflight.get("siteIdentity")
    site_key = ""
    if not isinstance(site_identity, dict):
        errors.append("preflight.siteIdentity must be present before media upload")
    else:
        site_key_value = site_identity.get("siteKey")
        if isinstance(site_key_value, str):
            site_key = site_key_value
        else:
            errors.append("preflight.siteIdentity.siteKey must be a string")
        module_routes = site_identity.get("moduleRoutes")
        expected_route = f"/{site_key}/media" if site_key else ""
        if not isinstance(module_routes, list) or expected_route not in module_routes:
            errors.append(f"preflight.siteIdentity.moduleRoutes must include {expected_route}")

    content_inspection = preflight.get("contentInspection")
    if not isinstance(content_inspection, dict):
        errors.append("preflight.contentInspection must be present before media upload")
    else:
        if content_inspection.get("contentType") != "media":
            errors.append("preflight.contentInspection.contentType must be media")
        list_columns = content_inspection.get("listColumns")
        visible_controls = content_inspection.get("visibleControls")
        if not isinstance(list_columns, list):
            list_columns = []
        if not isinstance(visible_controls, list):
            visible_controls = []
        media_controls = [*list_columns, *visible_controls]
        if not media_controls:
            errors.append("preflight.contentInspection.listColumns or visibleControls must include media controls")
        joined = " ".join(item for item in media_controls if isinstance(item, str))
        if "上传" not in joined and "upload" not in joined.lower():
            errors.append("preflight.contentInspection.listColumns or visibleControls must include upload control evidence")
        edit_fields = content_inspection.get("editFields")
        if not isinstance(edit_fields, list) or not edit_fields:
            errors.append("preflight.contentInspection.editFields must explain media upload/file policy")

    setup_pages = preflight.get("setupPages")
    if not isinstance(setup_pages, dict):
        errors.append("preflight.setupPages must be present before media upload")

    if authorization.get("action") != action:
        errors.append(f"authorization.action must be {action}")
    if authorization.get("siteKey") != site_key:
        errors.append("authorization.siteKey must match preflight.siteIdentity.siteKey")
    if authorization.get("targetType") != "media":
        errors.append("authorization.targetType must be media")
    if site_key:
        target = authorization.get("target")
        expected_prefix = f"https://workspace.laicms.com/{site_key}/media"
        if not isinstance(target, str) or not target.startswith(expected_prefix):
            errors.append(f"authorization.target must be under {expected_prefix}")
    target_identifier = authorization.get("targetIdentifier")
    if not isinstance(target_identifier, str) or not target_identifier.strip():
        errors.append("authorization.targetIdentifier must describe the exact media upload target")
    fields_or_files = authorization.get("fieldsOrFiles")
    field_set = set(fields_or_files) if isinstance(fields_or_files, list) else set()
    required_fields = MEDIA_ACTION_REQUIRED_FIELDS[action]
    if not required_fields.issubset(field_set):
        errors.append(f"authorization.fieldsOrFiles must include {', '.join(sorted(required_fields))}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check final gate before an AllinCMS mutation.")
    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "create_site",
            "save_probe",
            "publish_probe",
            "cleanup_probe",
            *sorted(PROBE_ACTION_MODULES),
            *sorted(EXISTING_CONTENT_ACTION_REQUIRED_FIELDS),
            *sorted(BATCH_ACTION_REQUIRED_FIELDS),
            *sorted(SITE_ACTION_MODULES),
            *sorted(MEDIA_ACTION_REQUIRED_FIELDS),
        ],
    )
    parser.add_argument("--preflight", required=True, help="Path to preflight/read-only evidence JSON")
    parser.add_argument("--authorization", default="", help="Path to action-specific authorization JSON")
    parser.add_argument(
        "--run-authorization",
        default="",
        help="Path to a run-scoped authorization JSON (run_authorization.py). For an in-scope content-build "
        "action it derives the per-action authorization so no fresh prompt is needed; a carve-out (create_site, "
        "delete, outward-facing settings, wrong site) still requires an explicit --authorization. Needs --target.",
    )
    parser.add_argument("--target", default="", help="Action target URL (required with --run-authorization)")
    parser.add_argument("--target-identifier", default="", help="Optional target identifier for run-authorization derivation")
    parser.add_argument("--sample-evidence", default="", help="Optional manifest sample upload evidence JSON for batch actions")
    parser.add_argument(
        "--expected-target-identifier",
        default="",
        help="Optional confirmed target identifier to bind create_site authorization to the source package site name",
    )
    parser.add_argument(
        "--max-age-minutes",
        type=int,
        default=DEFAULT_MAX_AGE_MINUTES,
        help="Maximum allowed age for preflight and authorization records, default 30 minutes",
    )
    args = parser.parse_args()

    try:
        preflight = load_json(Path(args.preflight))
        if args.authorization:
            authorization = load_json(Path(args.authorization))
        elif args.run_authorization:
            from run_authorization import validate_run_authorization, derive_action_authorization
            run_auth = load_json(Path(args.run_authorization))
            ra_errors = validate_run_authorization(run_auth)
            if ra_errors:
                for e in ra_errors:
                    print(f"ERROR: run-authorization: {e}", file=sys.stderr)
                return 2
            if not args.target:
                print("ERROR: --target is required with --run-authorization", file=sys.stderr)
                return 2
            try:
                authorization = derive_action_authorization(
                    run_auth, args.action, args.target, target_identifier=args.target_identifier
                )
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                print("ERROR: this action is a carve-out under the run-scoped authorization; get an explicit "
                      "per-action --authorization from the user for it.", file=sys.stderr)
                return 2
        else:
            print("ERROR: provide --authorization, or --run-authorization + --target for an in-scope action", file=sys.stderr)
            return 2
        sample_evidence = load_json(Path(args.sample_evidence)) if args.sample_evidence else None
        if args.action == "create_site":
            errors = validate_create_site_gate(
                preflight,
                authorization,
                args.max_age_minutes,
                expected_target_identifier=args.expected_target_identifier,
            )
        elif args.action == "save_probe":
            errors = validate_save_probe_gate(preflight, authorization, args.max_age_minutes)
        elif args.action == "publish_probe":
            errors = validate_publish_probe_gate(preflight, authorization, args.max_age_minutes)
        elif args.action == "cleanup_probe":
            errors = validate_cleanup_probe_gate(preflight, authorization, args.max_age_minutes)
        elif args.action in EXISTING_CONTENT_ACTION_REQUIRED_FIELDS:
            errors = validate_existing_content_gate(preflight, authorization, args.action, args.max_age_minutes)
        elif args.action in BATCH_ACTION_REQUIRED_FIELDS:
            errors = validate_batch_gate(preflight, authorization, args.action, args.max_age_minutes, sample_evidence=sample_evidence)
        elif args.action in MEDIA_ACTION_REQUIRED_FIELDS:
            errors = validate_media_action_gate(preflight, authorization, args.action, args.max_age_minutes)
        elif args.action in PROBE_ACTION_MODULES:
            errors = validate_probe_gate(preflight, authorization, args.action, args.max_age_minutes)
        elif args.action in SITE_ACTION_MODULES:
            errors = validate_site_action_gate(preflight, authorization, args.action, args.max_age_minutes)
        else:
            errors = [f"unsupported action: {args.action}"]
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Pre-mutation gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
