#!/usr/bin/env python3
"""Validate a redacted per-action AllinCMS JSON replay contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SAFE_SITE_KEY_RE = re.compile(r"^[a-z0-9]{6,16}$")
SAFE_ID_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:Id|ID|Ids|IDs)$")
SENSITIVE_PATTERNS = (
    re.compile(r"\b(cookie|authorization|bearer|token)\b\s*[:=]", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
PUBLIC_MODULES = {"posts", "products", "routes", "themes", "pages", "theme_pages", "design"}
VALID_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("contract root must be an object")
    return data


def non_empty_string(data: dict[str, Any], key: str) -> bool:
    return isinstance(data.get(key), str) and bool(str(data[key]).strip())


def non_empty_list(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def flattened_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def contains_sensitive_data(data: Any) -> list[str]:
    text = flattened_text(data)
    issues: list[str] = []
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            issues.append("contract contains raw sensitive or volatile account/header data")
            break
    return issues


def validate_backend_url(contract: dict[str, Any], errors: list[str]) -> None:
    site_key = str(contract.get("siteKey", "")).strip()
    url = str(contract.get("requestUrl", "")).strip()
    if not site_key:
        errors.append("siteKey: required")
        return
    if not SAFE_SITE_KEY_RE.match(site_key):
        errors.append("siteKey: must be lowercase letters/digits, 6-16 chars")
    if not url:
        errors.append("requestUrl: required")
        return
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        errors.append("requestUrl: must be an https workspace.laicms.com URL")
        return
    if not parsed.path.startswith(f"/{site_key}/"):
        errors.append("requestUrl: must belong to siteKey path")


def validate_headers(headers: Any, errors: list[str]) -> None:
    if not isinstance(headers, list) or not headers:
        errors.append("requiredHeaders: must be a non-empty array of redacted header names")
        return
    for index, header in enumerate(headers):
        if not isinstance(header, str) or not header.strip():
            errors.append(f"requiredHeaders[{index}]: must be a non-empty string")
            continue
        lowered = header.lower()
        if ":" in header or "=" in header:
            errors.append(f"requiredHeaders[{index}]: include header names only, not values")
        if lowered in {"cookie", "authorization"}:
            errors.append(f"requiredHeaders[{index}]: raw auth/cookie headers must not be stored")
    if not any(str(header).lower() == "content-type" for header in headers if isinstance(header, str)):
        errors.append("requiredHeaders: must include Content-Type")


def validate_id_fields(id_fields: Any, errors: list[str]) -> None:
    if not isinstance(id_fields, list) or not id_fields:
        errors.append("idFields: must be a non-empty array")
        return
    if not any(field == "siteId" for field in id_fields if isinstance(field, str)):
        errors.append("idFields: must include siteId")
    for index, field in enumerate(id_fields):
        if not isinstance(field, str) or not field.strip():
            errors.append(f"idFields[{index}]: must be a non-empty string")
        elif not SAFE_ID_FIELD_RE.match(field):
            errors.append(f"idFields[{index}]: must be an id field name, not a raw id value")


def public_verification_required(contract: dict[str, Any]) -> bool:
    module = str(contract.get("module", "")).strip()
    action = str(contract.get("action", "")).strip()
    if contract.get("publicEffect") is True:
        return True
    if module in PUBLIC_MODULES and action in {"publish", "publish_design", "set_homepage", "create_route", "bind_route", "batch_upload_publish"}:
        return True
    return False


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("kind") != "allincms_action_replay_contract":
        errors.append("kind: must be allincms_action_replay_contract")
    if contract.get("redacted") is not True:
        errors.append("redacted: must be true")
    if contract.get("localOnly") is not True:
        errors.append("localOnly: must be true")
    if contract.get("remoteMutationsPerformed") is not False:
        errors.append("remoteMutationsPerformed: must be false")
    for key in ("module", "action", "targetType", "authorizationAction", "payloadShape", "backendVerification", "rollbackOrCleanupPlan"):
        if not non_empty_string(contract, key):
            errors.append(f"{key}: required non-empty string")
    method = str(contract.get("method", "")).strip().upper()
    if method not in VALID_METHODS:
        errors.append(f"method: must be one of {sorted(VALID_METHODS)}")
    validate_backend_url(contract, errors)
    validate_headers(contract.get("requiredHeaders"), errors)
    validate_id_fields(contract.get("idFields"), errors)
    if not non_empty_list(contract, "payloadKeys"):
        errors.append("payloadKeys: must be a non-empty array")
    if "siteId" not in contract.get("payloadKeys", []):
        errors.append("payloadKeys: must include siteId")
    if contract.get("persistedVerified") is not True:
        errors.append("persistedVerified: must be true after backend verification")
    if public_verification_required(contract):
        if contract.get("frontendVerified") is not True:
            errors.append("frontendVerified: must be true for public-facing replay actions")
        if not non_empty_string(contract, "frontendVerification"):
            errors.append("frontendVerification: required for public-facing replay actions")
    if contract.get("sampleReplayVerified") is not True:
        errors.append("sampleReplayVerified: must be true before replay acceleration is ready")
    if contract.get("jsonReplayReady") is not True:
        errors.append("jsonReplayReady: must be true only after this validator passes")
    errors.extend(contains_sensitive_data(contract))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a redacted AllinCMS action replay contract.")
    parser.add_argument("contract_json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation result")
    args = parser.parse_args()

    try:
        contract = load_json(Path(args.contract_json))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_contract(contract)
    result = {
        "ok": not errors,
        "kind": "allincms_action_replay_contract_validation",
        "jsonReplayReady": not errors,
        "module": contract.get("module", ""),
        "action": contract.get("action", ""),
        "issues": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif errors:
        print("Action replay contract validation failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print("Action replay contract validation passed.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
