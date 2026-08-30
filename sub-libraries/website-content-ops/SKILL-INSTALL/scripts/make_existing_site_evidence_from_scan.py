#!/usr/bin/env python3
"""Build existing-site read-only evidence from a redacted browser scan JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

from make_existing_site_readonly_evidence import build_evidence


REQUIRED_SCAN_MODULES = (
    "dashboard",
    "products",
    "posts",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
)
CREATE_FIELD_LABELS = (
    "button: 创建站点",
    "dialog title: 创建站点",
    "input name: name, placeholder: 站点名称",
    "textarea name: description, placeholder: 站点简介",
    "submit button: 创建",
    "close button: Close",
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SITE_KEY_RE = re.compile(r"^[a-z0-9]{6,16}$")
SITE_KEY_PLACEHOLDERS = {"{siteKey}", "{realSiteKey}"}
RESERVED_ROUTE_NAMES = {
    "dashboard",
    "sites",
    "users",
    "help-center",
    "products",
    "posts",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
}
NOISY_BUTTON_TERMS = (
    "Toggle Sidebar",
    "中文",
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"scan JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid scan JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("scan JSON root must be an object")
    return data


def require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"scan.{key} must be an array")
    return value


def require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"scan.{key} must be an object")
    return value


def text_join(values: object) -> str:
    if not isinstance(values, list):
        return ""
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text:
            continue
        if EMAIL_RE.search(text):
            continue
        if any(term in text for term in NOISY_BUTTON_TERMS):
            continue
        if ".web.allincms.com" in text:
            continue
        cleaned.append(text)
    return " ".join(cleaned)


def extract_existing_site_keys(scan: dict[str, Any]) -> str:
    sites = require_dict(scan, "sites")
    site_keys = sites.get("existingSiteKeys")
    if site_keys is None:
        site_keys = sites.get("existingSiteKeysBeforeCreate")
    if not isinstance(site_keys, list):
        raise ValueError("scan.sites.existingSiteKeys must be an array")
    if not site_keys:
        raise ValueError("scan.sites.existingSiteKeys must not be empty for existing-site evidence")
    invalid = [
        str(key)
        for key in site_keys
        if str(key) in RESERVED_ROUTE_NAMES
        or (str(key) not in SITE_KEY_PLACEHOLDERS and not SITE_KEY_RE.match(str(key)))
    ]
    if invalid:
        raise ValueError("scan.sites.existingSiteKeys contains non-site route names or unsafe keys: " + ", ".join(invalid[:5]))
    return ",".join(str(key) for key in site_keys)


def validate_create_dialog(scan: dict[str, Any]) -> str:
    sites = require_dict(scan, "sites")
    dialog_value = sites.get("createDialog")
    if dialog_value is None:
        return ""
    if not isinstance(dialog_value, dict):
        raise ValueError("scan.sites.createDialog must be an object when present")
    dialog = dialog_value
    closed_verified = dialog.get("closedVerified") is True
    if not closed_verified:
        closed = sites.get("dialogClosed")
        if isinstance(closed, dict) and closed.get("dialogCount") == 0:
            closed_verified = True
    if not closed_verified:
        raise ValueError("scan.sites.createDialog.closedVerified must be true")

    fields_value = dialog.get("fields")
    buttons = dialog.get("buttons")
    headings = dialog.get("headings")
    if fields_value is None and isinstance(dialog.get("dialogs"), list):
        fields_value = []
        buttons = [] if buttons is None else buttons
        headings = [] if headings is None else headings
        for dialog_item in dialog["dialogs"]:
            if not isinstance(dialog_item, dict):
                continue
            for input_item in dialog_item.get("inputs", []):
                if isinstance(input_item, dict):
                    rendered = " ".join(
                        str(input_item.get(part, "")).strip()
                        for part in ("tag", "name", "placeholder")
                        if str(input_item.get(part, "")).strip()
                    )
                    if rendered:
                        fields_value.append(rendered)
            if isinstance(dialog_item.get("buttons"), list):
                buttons.extend(str(button_item.get("text", button_item)) for button_item in dialog_item["buttons"])
            if isinstance(dialog_item.get("headings"), list):
                headings.extend(str(heading) for heading in dialog_item["headings"])

    if not isinstance(fields_value, list):
        raise ValueError("scan.sites.createDialog.fields must be an array")
    fields = fields_value
    joined = " ".join(
        str(part)
        for values in (fields, buttons if isinstance(buttons, list) else [], headings if isinstance(headings, list) else [])
        for part in values
    )
    for term in ("name", "description", "Close"):
        if term not in joined:
            raise ValueError(f"scan.sites.createDialog.fields must include {term}")
    return ";".join(CREATE_FIELD_LABELS)


def module(scan: dict[str, Any], name: str) -> dict[str, Any]:
    modules = require_dict(scan, "modules")
    item = modules.get(name)
    if not isinstance(item, dict):
        raise ValueError(f"scan.modules.{name} must be an object")
    return item


def module_route_from_scan(scan: dict[str, Any], name: str, site_key: str) -> str:
    item = module(scan, name)
    raw_url = item.get("url")
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError(f"scan.modules.{name}.url is required")
    parsed = urlparse(raw_url)
    path = parsed.path if parsed.scheme else raw_url
    if parsed.scheme and parsed.netloc != "workspace.laicms.com":
        raise ValueError(f"scan.modules.{name}.url must be under workspace.laicms.com")
    expected_prefix = f"/{site_key}/{name}"
    redacted_prefixes = {f"/{{siteKey}}/{name}", f"/{{realSiteKey}}/{name}"}
    if path.rstrip("/") != expected_prefix and path.rstrip("/") not in redacted_prefixes:
        raise ValueError(f"scan.modules.{name}.url must be {expected_prefix} or a redacted site-key placeholder")
    return expected_prefix


def module_routes(scan: dict[str, Any], site_key: str) -> str:
    return ",".join(module_route_from_scan(scan, module_name, site_key) for module_name in REQUIRED_SCAN_MODULES)


NON_TABLE_CONTENT_TYPES = {"media", "site-info", "tracking", "domains"}


def render_controls_or_columns(item: dict[str, Any], content_type: str) -> str:
    controls = []
    for key in ("buttons", "buttonTexts", "controls", "visibleControls"):
        values = item.get(key)
        if isinstance(values, list):
            controls.extend(str(value).strip() for value in values if str(value).strip())
    inputs = item.get("inputs")
    if isinstance(inputs, list):
        for input_item in inputs[:12]:
            if isinstance(input_item, dict):
                tag = str(input_item.get("tag", "")).strip()
                name = str(input_item.get("name", "") or "").strip()
                placeholder = str(input_item.get("placeholder", "") or "").strip()
                rendered = ":".join(part for part in (tag, name, placeholder) if part)
                if rendered:
                    controls.append(rendered)
    deduped = []
    seen = set()
    for control in controls:
        if control in seen:
            continue
        seen.add(control)
        deduped.append(control)
    if not deduped:
        raise ValueError(f"scan.modules.{content_type} must include visible controls or inputs")
    return ",".join(deduped)


def list_columns(scan: dict[str, Any], content_type: str) -> str:
    item = module(scan, content_type)
    columns = item.get("tableHeads")
    if columns is None:
        columns = item.get("tableHeaders")
    if not isinstance(columns, list):
        if content_type in NON_TABLE_CONTENT_TYPES:
            return render_controls_or_columns(item, content_type)
        raise ValueError(f"scan.modules.{content_type}.tableHeads or tableHeaders must be an array")
    if not columns:
        if content_type in NON_TABLE_CONTENT_TYPES:
            return render_controls_or_columns(item, content_type)
        raise ValueError(f"scan.modules.{content_type}.tableHeads or tableHeaders must not be empty")
    return ",".join(str(column) for column in columns)


def setup_evidence(scan: dict[str, Any], name: str, prefix: str) -> str:
    item = module(scan, name)
    bits = []
    headings = text_join(item.get("headings"))
    buttons = text_join(item.get("buttons"))
    inputs = item.get("inputs")
    if headings:
        bits.append(f"headings {headings}")
    if buttons:
        bits.append(f"controls {buttons}")
    if isinstance(inputs, list) and inputs:
        rendered_inputs = []
        for input_item in inputs[:12]:
            if isinstance(input_item, dict):
                rendered_inputs.append(
                    f"{input_item.get('tag', '')}:{input_item.get('name', '')}:{input_item.get('placeholder', '')}"
                )
        if rendered_inputs:
            bits.append("inputs " + " | ".join(rendered_inputs))
    if not bits:
        raise ValueError(f"scan.modules.{name} lacks setup evidence")
    return f"{prefix}: " + "; ".join(bits)


def build_args(scan: dict[str, Any], args: argparse.Namespace) -> SimpleNamespace:
    site_key = args.site_key or str(scan.get("siteKey", "")).strip()
    content_type = args.content_type or str(scan.get("contentType", "products")).strip()
    if not site_key:
        raise ValueError("site key is required in scan.siteKey or --site-key")
    create_dialog_fields = validate_create_dialog(scan)

    return SimpleNamespace(
        site_key=site_key,
        existing_site_keys=extract_existing_site_keys(scan),
        observed_create_fields=create_dialog_fields,
        dialog_closed_verified=bool(create_dialog_fields),
        module_routes=module_routes(scan, site_key),
        content_type=content_type,
        list_columns=list_columns(scan, content_type),
        edit_fields=args.edit_fields,
        site_info_evidence=setup_evidence(scan, "site-info", "site-info read-only inspected"),
        domains_evidence=setup_evidence(scan, "domains", "domains read-only inspected"),
        media_evidence=setup_evidence(scan, "media", "media read-only inspected"),
        themes_evidence=setup_evidence(scan, "themes", "themes read-only inspected"),
        routes_evidence=setup_evidence(scan, "routes", "routes read-only inspected"),
        forms_evidence=setup_evidence(scan, "forms", "forms read-only inspected"),
        tracking_evidence=setup_evidence(scan, "tracking", "tracking read-only inspected"),
        cleanup_status=args.cleanup_status,
        cleanup_candidates=args.cleanup_candidates,
        frontend_rendering_evidence=args.frontend_rendering_evidence,
        launch_readiness_evidence=args.launch_readiness_evidence,
        frontend_route_patterns="",
        markdown_residue_checked=False,
        structured_rich_text_checked=False,
        frontend_blocking_issues="",
        repo_check_passed=args.repo_check_passed,
        repo_check_note=args.repo_check_note,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build existing-site read-only evidence from browser scan JSON.")
    parser.add_argument("scan_json")
    parser.add_argument("--site-key", default="")
    parser.add_argument("--content-type", default="products")
    parser.add_argument(
        "--edit-fields",
        required=True,
        help="Neutral observed edit/list fields for the target content type; do not include business content",
    )
    parser.add_argument("--frontend-rendering-evidence", default="")
    parser.add_argument("--launch-readiness-evidence", default="")
    parser.add_argument(
        "--cleanup-status",
        choices=["not_needed", "pending_user_authorization", "explicitly_deferred"],
        default="not_needed",
    )
    parser.add_argument("--cleanup-candidates", default="")
    parser.add_argument("--repo-check-passed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--repo-check-note", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        evidence = build_evidence(build_args(load_json(Path(args.scan_json)), args))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).expanduser().write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
