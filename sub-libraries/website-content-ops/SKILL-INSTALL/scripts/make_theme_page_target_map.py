#!/usr/bin/env python3
"""Build a concrete theme/page target map from read-only browser evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DESIGN_URL_RE = re.compile(
    r"^https://workspace\.laicms\.com/(?P<site_key>[a-z0-9][a-z0-9-]{2,62}[a-z0-9])"
    r"/themes/(?P<theme_id>[^/]+)/(?P<page_id>[^/]+)/design$"
)
THEME_URL_RE = re.compile(
    r"^https://workspace\.laicms\.com/(?P<site_key>[a-z0-9][a-z0-9-]{2,62}[a-z0-9])"
    r"/themes/(?P<theme_id>[^/]+)$"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


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


def write_json(path: Path, data: dict[str, Any]) -> str:
    ensure_output_outside_skill(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def source_pages(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    pages = []
    for item in as_list(handoff.get("pages")):
        if not isinstance(item, dict) or not isinstance(item.get("page"), dict):
            continue
        page = item["page"]
        title = str(page.get("title") or "").strip()
        path = str(page.get("path") or "").strip()
        if title and path.startswith("/"):
            pages.append({"title": title, "path": path, "actions": as_list(item.get("actions"))})
    if not pages:
        raise SystemExit("ERROR: handoff.pages contains no concrete source pages")
    return pages


def parse_theme_id(observation: dict[str, Any], site_key: str) -> str:
    theme_id = str(observation.get("themeId") or "").strip()
    if theme_id:
        return theme_id
    for candidate in [observation.get("themeUrl"), observation.get("themePageListUrl")]:
        if not isinstance(candidate, str):
            continue
        match = THEME_URL_RE.fullmatch(candidate)
        if match and match.group("site_key") == site_key:
            return match.group("theme_id")
    raise SystemExit("ERROR: observation must provide themeId or concrete themeUrl for the current site")


def normalize_path(path: str) -> str:
    path = path.strip()
    if not path:
        return ""
    return path if path.startswith("/") else "/" + path


def observed_pages(observation: dict[str, Any], site_key: str, theme_id: str) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(as_list(observation.get("pageRows"))):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        route_path = normalize_path(str(row.get("path") or row.get("routePath") or ""))
        design_url = str(row.get("designUrl") or "").strip()
        page_id = str(row.get("pageId") or "").strip()
        if design_url:
            match = DESIGN_URL_RE.fullmatch(design_url)
            if not match:
                raise SystemExit(f"ERROR: pageRows[{index}].designUrl must be a concrete current-site design URL")
            if match.group("site_key") != site_key:
                raise SystemExit(f"ERROR: pageRows[{index}].designUrl site key does not match handoff.siteKey")
            if match.group("theme_id") != theme_id:
                raise SystemExit(f"ERROR: pageRows[{index}].designUrl theme id does not match observation theme")
            parsed_page_id = match.group("page_id")
            if page_id and page_id != parsed_page_id:
                raise SystemExit(f"ERROR: pageRows[{index}].pageId does not match designUrl")
            page_id = parsed_page_id
        if title and route_path:
            rows.append(
                {
                    "title": title,
                    "path": route_path,
                    "queryType": str(row.get("queryType") or "").strip(),
                    "status": str(row.get("status") or "").strip(),
                    "enabled": row.get("enabled"),
                    "homepage": row.get("homepage"),
                    "description": str(row.get("description") or "").strip(),
                    "pageId": page_id,
                    "designUrl": design_url,
                    "source": str(row.get("source") or "theme page list read-only scan"),
                }
            )
    if not rows:
        raise SystemExit("ERROR: observation.pageRows must include at least one observed page row")
    return rows


def match_observed(source: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    source_path = source["path"]
    title = source["title"].strip().lower()
    if source_path == "/":
        for row in rows:
            if row["path"] == "/home" or row["title"].strip().lower() == "home":
                return row, "homepage_root_reuses_home_page"
    for row in rows:
        if row["path"] == source_path:
            return row, "path_match"
    for row in rows:
        if row["title"].strip().lower() == title:
            return row, "title_match"
    return None, "missing"


def replace_placeholders(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        out = value
        for key, replacement in replacements.items():
            out = out.replace("{" + key + "}", replacement)
        return out
    if isinstance(value, list):
        return [replace_placeholders(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_placeholders(item, replacements) for key, item in value.items()}
    return value


def concrete_actions(source: dict[str, Any], row: dict[str, Any] | None, site_key: str, theme_id: str) -> list[dict[str, Any]]:
    out = []
    for action in source["actions"]:
        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            continue
        cloned = dict(action)
        name = cloned["action"]
        if row and name in {"save_design", "publish_design"} and row.get("designUrl"):
            cloned["target"] = row["designUrl"]
            cloned["targetIdentifier"] = f"{source['path']} {name} {row['title']}"
            cloned["requiresConcreteTargetBeforeAuthorization"] = False
        elif row and name in {"enable_theme_page", "set_homepage"}:
            cloned["target"] = f"https://workspace.laicms.com/{site_key}/themes/{theme_id}"
            cloned["targetIdentifier"] = f"{source['path']} {name} {row['title']}"
            cloned["requiresConcreteTargetBeforeAuthorization"] = False
        elif name in {"create_route", "bind_route"}:
            cloned["target"] = f"https://workspace.laicms.com/{site_key}/routes"
            cloned["requiresConcreteTargetBeforeAuthorization"] = False
        elif name == "create_theme_page":
            cloned["target"] = f"https://workspace.laicms.com/{site_key}/themes/{theme_id}"
            cloned["requiresConcreteTargetBeforeAuthorization"] = False
        replacements = {"themeId": theme_id}
        if row and row.get("pageId"):
            replacements["pageId"] = str(row["pageId"])
        cloned = replace_placeholders(cloned, replacements)
        cloned["targetConcrete"] = "{" not in str(cloned.get("target", "")) and "}" not in str(cloned.get("target", ""))
        command_text = "\n".join(
            str(cloned.get(field, ""))
            for field in ("authorizationRecordCommand", "preMutationGateCommand")
        )
        cloned["commandsConcrete"] = "{" not in command_text and "}" not in command_text
        out.append(cloned)
    return out


def build(handoff: dict[str, Any], observation: dict[str, Any], source_observation: str) -> dict[str, Any]:
    if handoff.get("kind") != "allincms_pages_site_info_browser_handoff":
        raise SystemExit("ERROR: handoff.kind must be allincms_pages_site_info_browser_handoff")
    site_key = str(handoff.get("siteKey") or "").strip()
    if not site_key:
        raise SystemExit("ERROR: handoff.siteKey is required")
    frontend_base = str(handoff.get("frontendBaseUrl") or "").rstrip("/")
    if not frontend_base.startswith("https://"):
        raise SystemExit("ERROR: handoff.frontendBaseUrl must be an https URL")
    if observation.get("siteKey") and observation["siteKey"] != site_key:
        raise SystemExit("ERROR: observation.siteKey must match handoff.siteKey")
    theme_id = parse_theme_id(observation, site_key)
    rows = observed_pages(observation, site_key, theme_id)
    mapped_pages = []
    missing_pages = []
    for source in source_pages(handoff):
        row, reason = match_observed(source, rows)
        frontend_path = "" if source["path"] == "/" else source["path"]
        item = {
            "sourceTitle": source["title"],
            "sourcePath": source["path"],
            "frontendUrl": frontend_base + frontend_path,
            "matchStatus": "existing_page_mapped" if row else "missing_page_requires_create",
            "matchReason": reason,
            "observedPage": row or {},
            "actions": concrete_actions(source, row, site_key, theme_id),
            "homepageRootUsesHomeRoute": source["path"] == "/" and bool(row and row.get("path") == "/home"),
        }
        if not row:
            missing_pages.append(source["path"])
        mapped_pages.append(item)
    blocking = []
    for page in mapped_pages:
        if page["matchStatus"] == "existing_page_mapped":
            for action in page["actions"]:
                if action.get("requiresConcreteTargetBeforeAuthorization") or not action.get("targetConcrete"):
                    blocking.append(f"{page['sourcePath']} action {action.get('action')} still has placeholder target")
    return {
        "kind": "allincms_theme_page_target_map",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "sourceHandoff": source_observation,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "themeId": theme_id,
        "themeUrl": f"https://workspace.laicms.com/{site_key}/themes/{theme_id}",
        "observedPageCount": len(rows),
        "mappedPages": mapped_pages,
        "missingSourcePaths": missing_pages,
        "blockingIssues": blocking,
        "readyForExistingPageAuthorization": not blocking,
        "nextAction": (
            "prepare one action-specific authorization using a concrete target for an existing page, or create missing pages separately"
            if not blocking
            else "refresh read-only page/design URLs until every reused page action has a concrete target"
        ),
        "adversarialChecks": [
            "This target map is read-only evidence and does not authorize saving, publishing, enabling, binding, or creating pages.",
            "Root / can reuse the observed Home /home page, but frontend / must still be verified after publish/homepage binding.",
            "Missing source pages such as /applications require a separate create_theme_page and route-binding stage.",
            "Do not authorize save_design or publish_design while a target still contains {themeId} or {pageId}.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a concrete AllinCMS theme/page target map.")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--observation", required=True, help="Read-only JSON with themeUrl/themeId and pageRows")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    handoff_path = Path(args.handoff).expanduser().resolve()
    observation_path = Path(args.observation).expanduser().resolve()
    result = build(
        load_json(handoff_path, "pages/site-info handoff"),
        load_json(observation_path, "theme page observation"),
        str(handoff_path),
    )
    write_json(Path(args.output).expanduser().resolve(), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote theme page target map: {Path(args.output).expanduser().resolve()}")
        print(f"mapped={len(result['mappedPages'])} missing={','.join(result['missingSourcePaths']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
