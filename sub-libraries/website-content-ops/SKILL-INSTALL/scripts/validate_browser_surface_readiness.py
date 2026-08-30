#!/usr/bin/env python3
"""Validate whether a browser surface is usable for an AllinCMS stage.

This helper consumes a redacted observation JSON created during browser work. It
does not authorize, click, save, publish, or replay requests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DESIGNER_ACTIONS = {
    "save_design",
    "publish_design",
    "create_theme_page",
    "enable_theme_page",
    "set_homepage",
    "bind_route",
    "theme_page_route_launch",
}

MUTATION_MODES = {"mutation_preparation", "mutation", "execute_mutation"}
READONLY_MODES = {"readonly", "read_only", "orientation"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"browser observation JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid browser observation JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("browser observation JSON root must be an object")
    return data


def as_bool(value: Any) -> bool:
    return value is True


def as_number(value: Any) -> float:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0
    return 0


def normalized_mode(value: Any) -> str:
    mode = str(value or "mutation_preparation").strip().lower()
    return mode or "mutation_preparation"


def current_url(obs: dict[str, Any]) -> str:
    return str(obs.get("currentUrl") or obs.get("url") or "").strip()


def expected_site_key(obs: dict[str, Any]) -> str:
    return str(obs.get("siteKey") or obs.get("expectedSiteKey") or "").strip()


def target_action(obs: dict[str, Any]) -> str:
    return str(obs.get("targetAction") or obs.get("action") or "").strip()


def blocking_issues(obs: dict[str, Any]) -> list[str]:
    raw = obs.get("blockingIssues", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        return ["blockingIssues must be a list"]
    return [str(item).strip() for item in raw if str(item).strip()]


def is_designer_action(action: str) -> bool:
    return action in DESIGNER_ACTIONS or action.endswith("_design")


def validate_surface(obs: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    proven: list[str] = []

    browser = str(obs.get("browser") or "").strip()
    action = target_action(obs)
    mode = normalized_mode(obs.get("mode") or obs.get("targetMode"))
    url = current_url(obs)
    site_key = expected_site_key(obs)
    mutation_requested = mode in MUTATION_MODES
    readonly_requested = mode in READONLY_MODES

    if browser not in {"in_app", "chrome"}:
        issues.append("browser must be 'in_app' or 'chrome'")
    else:
        proven.append(f"browser:{browser}")

    if not url:
        issues.append("currentUrl/url is required")
    elif "/sign-in" in url:
        issues.append("browser is on workspace sign-in page")
    elif "workspace.laicms.com" in url:
        proven.append("workspace_url_loaded")
    elif ".web.allincms.com" in url:
        proven.append("frontend_url_loaded")
    else:
        warnings.append("current URL is not an AllinCMS workspace or frontend URL")

    if site_key and url and "workspace.laicms.com" in url and f"/{site_key}/" not in url and not url.rstrip("/").endswith("/sites"):
        issues.append("current workspace URL does not include expected siteKey")

    issues.extend(blocking_issues(obs))

    designer_visible = as_bool(obs.get("designerVisible"))
    preview_width = as_number(obs.get("previewFrameWidth"))
    preview_height = as_number(obs.get("previewFrameHeight"))
    canvas_text = str(obs.get("canvasText") or obs.get("previewText") or "").strip()
    save_enabled = obs.get("saveEnabled")
    publish_enabled = obs.get("publishEnabled")

    if is_designer_action(action):
        if not designer_visible:
            issues.append("designer surface is not visible for designer action")
        else:
            proven.append("designer_visible")
        if preview_width <= 0 or preview_height <= 0:
            issues.append("preview frame has zero width or height")
        else:
            proven.append("preview_frame_nonzero")
        if "Render canvas" in canvas_text:
            issues.append("designer canvas is still stuck on Render canvas")
        if mutation_requested:
            if save_enabled is False and action in {"save_design", "theme_page_route_launch"}:
                issues.append("save control is disabled for requested design mutation")
            if publish_enabled is False and action == "publish_design":
                issues.append("publish control is disabled for requested design mutation")

    if readonly_requested and issues:
        status = "ready_for_readonly" if all(issue.startswith("designer ") or "preview frame" in issue or "Render canvas" in issue for issue in issues) else "blocked_browser_surface"
    elif issues:
        status = "blocked_login_required" if any("sign-in" in issue for issue in issues) else "blocked_browser_surface"
    elif mutation_requested:
        status = "ready_for_mutation_preparation"
    else:
        status = "ready_for_readonly"

    return {
        "ok": not issues or status == "ready_for_readonly",
        "status": status,
        "browser": browser,
        "mode": mode,
        "targetAction": action,
        "siteKey": site_key,
        "currentUrl": url,
        "remoteMutationAuthorized": False,
        "remoteMutationsPerformed": False,
        "proven": proven,
        "warnings": warnings,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted AllinCMS browser surface readiness.")
    parser.add_argument("observation_json")
    parser.add_argument("--fail-on-blocked", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_surface(load_json(Path(args.observation_json)))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["issues"]:
        print(f"Browser surface readiness: {result['status']}")
        for issue in result["issues"]:
            print(f"- {issue}")
    else:
        print(f"Browser surface readiness: {result['status']}")

    if args.fail_on_blocked and result["status"].startswith("blocked"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
