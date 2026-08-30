#!/usr/bin/env python3
"""Redact raw LAICMS browser scan JSON before evidence conversion or storage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


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
WORKSPACE_ORIGIN = "workspace.laicms.com"
MODULE_NAMES = {
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
}
SAFE_MODULE_HEADINGS = {
    "dashboard": {"仪表盘", "Dashboard"},
    "products": {"产品", "Products"},
    "posts": {"文章", "Posts"},
    "media": {"媒体", "Media"},
    "themes": {"主题", "Themes"},
    "routes": {"路由", "Routes"},
    "forms": {"表单", "Forms"},
    "site-info": {"站点信息", "Site Info"},
    "tracking": {"Google 追踪", "Tracking"},
    "domains": {"域名", "Domains"},
}

DROP_STRING_TERMS = (
    "[redacted-email]",
    ".web.allincms.com",
    "Toggle Sidebar",
    "中文",
    "English",
    "Sign Out",
    "Log out",
    "Logout",
)
DROP_VALUE_KEYS = {
    "body",
    "content",
    "innerText",
    "outerText",
    "textContent",
    "snippet",
    "sample",
    "samples",
    "rawText",
    "rawHtml",
    "html",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"scan JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid scan JSON: {exc}") from None


def is_workspace_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.netloc == WORKSPACE_ORIGIN


def is_protected_path(path: tuple[str, ...]) -> bool:
    if path == ("siteKey",) or path == ("contentType",):
        return True
    if path == ("sites", "url"):
        return True
    if len(path) == 3 and path[:2] == ("sites", "existingSiteKeys"):
        return True
    if len(path) == 3 and path[:2] == ("sites", "existingSiteKeysBeforeCreate"):
        return True
    if len(path) == 4 and path[0] == "modules" and path[2] == "url":
        return True
    return False


def is_safe_site_key_text(text: str) -> bool:
    return text in SITE_KEY_PLACEHOLDERS or (text not in RESERVED_ROUTE_NAMES and bool(SITE_KEY_RE.match(text)))


def should_drop_string(value: str) -> bool:
    text = value.strip()
    if not text:
        return True
    if EMAIL_RE.search(text):
        return True
    if text.upper().startswith("TO "):
        return True
    return any(term in text for term in DROP_STRING_TERMS)


def redact_nonprotected_string(value: str) -> str:
    text = value.strip()
    text = re.sub(
        r"https://workspace\.laicms\.com/([a-z0-9]{6,16})(?=/|$)",
        "https://workspace.laicms.com/{siteKey}",
        text,
    )
    text = re.sub(r"(?<![\w{])/[a-z0-9]{6,16}(?=/)", "/{siteKey}", text)
    return text


def module_name_from_path(path: tuple[str, ...]) -> str:
    if len(path) >= 2 and path[0] == "modules":
        return path[1]
    return ""


def is_heading_path(path: tuple[str, ...]) -> bool:
    return len(path) >= 4 and path[0] == "modules" and path[2] == "headings"


def is_link_path(path: tuple[str, ...]) -> bool:
    if len(path) >= 4 and path[0] == "modules" and path[2] in {"links", "relativeLinks"}:
        return True
    return False


def is_safe_module_heading(text: str, path: tuple[str, ...]) -> bool:
    module_name = module_name_from_path(path)
    allowed = SAFE_MODULE_HEADINGS.get(module_name, set())
    return text in allowed


def is_safe_module_link(text: str) -> bool:
    parsed = urlparse(text)
    raw_path = parsed.path if parsed.scheme else text.split("?", 1)[0]
    query = parsed.query if parsed.scheme else (text.split("?", 1)[1] if "?" in text else "")
    parts = [part for part in raw_path.split("/") if part]
    if not parts:
        return False
    if parts[0] in SITE_KEY_PLACEHOLDERS or SITE_KEY_RE.match(parts[0]):
        parts = parts[1:]
    if len(parts) != 1 or parts[0] not in MODULE_NAMES:
        return False
    if query and not query.startswith("tab="):
        return False
    return True


def redact_value(value: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            child_path = path + (str(key),)
            if str(key) in DROP_VALUE_KEYS:
                continue
            cleaned = redact_value(child, child_path)
            if cleaned is None:
                continue
            redacted[str(key)] = cleaned
        return redacted

    if isinstance(value, list):
        cleaned_list: list[Any] = []
        for index, child in enumerate(value):
            cleaned = redact_value(child, path + (str(index),))
            if cleaned is None:
                continue
            cleaned_list.append(cleaned)
        return cleaned_list

    if isinstance(value, str):
        text = value.strip()
        if is_protected_path(path):
            if path == ("siteKey",) and not is_safe_site_key_text(text):
                raise ValueError("scan.siteKey is not a safe site key")
            if len(path) == 3 and path[:2] == ("sites", "existingSiteKeys") and not is_safe_site_key_text(text):
                raise ValueError("scan.sites.existingSiteKeys contains an unsafe site key")
            if len(path) == 3 and path[:2] == ("sites", "existingSiteKeysBeforeCreate") and not is_safe_site_key_text(text):
                raise ValueError("scan.sites.existingSiteKeysBeforeCreate contains an unsafe site key")
            if path == ("sites", "url") and text and not is_workspace_url(text):
                raise ValueError("scan.sites.url must stay under workspace.laicms.com")
            if len(path) == 4 and path[0] == "modules" and path[2] == "url" and not is_workspace_url(text):
                raise ValueError(f"scan.modules.{path[1]}.url must stay under workspace.laicms.com")
            return text
        if is_heading_path(path) and not is_safe_module_heading(text, path):
            return None
        if is_link_path(path) and not is_safe_module_link(text):
            return None
        if should_drop_string(text):
            return None
        return redact_nonprotected_string(text)

    return value


def collect_sensitive(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            issues.extend(collect_sensitive(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(collect_sensitive(child, path + (str(index),)))
    elif isinstance(value, str) and not is_protected_path(path):
        if should_drop_string(value):
            issues.append(".".join(path) or "<root>")
    return issues


def redact_scan(data: Any) -> Any:
    if not isinstance(data, dict):
        raise ValueError("scan JSON root must be an object")
    redacted = redact_value(data)
    if not isinstance(redacted, dict):
        raise ValueError("redacted scan root must be an object")
    issues = collect_sensitive(redacted)
    if issues:
        raise ValueError("redaction left sensitive strings at: " + ", ".join(issues[:12]))
    return redacted


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact a raw LAICMS browser scan JSON.")
    parser.add_argument("scan_json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        redacted = redact_scan(load_json(Path(args.scan_json)))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).expanduser().write_text(json.dumps(redacted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
