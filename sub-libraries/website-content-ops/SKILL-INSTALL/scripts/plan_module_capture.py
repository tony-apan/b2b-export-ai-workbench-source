#!/usr/bin/env python3
"""Build a staged browser-capture plan from an AllinCMS module scan summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTENT_MODULES = {"posts", "products"}
LAUNCH_MODULES = {"themes", "routes", "site-info", "tracking"}
UPLOAD_MODULES = {"media"}
FORM_MODULES = {"forms"}
DESTRUCTIVE_OR_EXTERNAL_MODULES = {"domains"}


def load_summary(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"summary JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid summary JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("summary JSON root must be an object")
    if data.get("kind") != "allincms_module_scan_summary":
        raise ValueError("summary kind must be allincms_module_scan_summary")
    return data


def risk_group(module: str, action: str) -> str:
    if module in CONTENT_MODULES:
        return "content_probe_capture"
    if module == "themes":
        return "theme_page_design_capture"
    if module == "routes":
        return "route_binding_capture"
    if module in FORM_MODULES:
        return "form_capture"
    if module in UPLOAD_MODULES:
        return "media_upload_capture"
    if module in DESTRUCTIVE_OR_EXTERNAL_MODULES:
        return "external_or_destructive_manual_review"
    if module in LAUNCH_MODULES:
        return "site_settings_capture"
    return f"{module}_{action}_capture"


def target_path(site_key: str, module: str) -> str:
    if site_key:
        return f"https://workspace.laicms.com/{site_key}/{module}"
    return f"https://workspace.laicms.com/{{siteKey}}/{module}"


def stage_for(module: str, action: str) -> dict[str, Any]:
    if module in CONTENT_MODULES and action == "create":
        return {
            "authorizationAction": f"create_{module[:-1]}_probe",
            "stopAfter": "probe draft or dialog state is verified; do not save or publish in the same authorization",
            "mustCapture": [
                "whether create button opens a dialog or immediately creates a draft",
                "new edit URL or draft row identity, redacted",
                "backend list state after create",
                "cleanup candidate for later authorization",
            ],
        }
    if module == "themes" and action == "create":
        return {
            "authorizationAction": "create_theme",
            "stopAfter": "theme draft appears; do not activate, edit design, or publish in the same authorization",
            "mustCapture": [
                "dialog fields",
                "create POST URL and method if submitted",
                "payload shape with ids redacted",
                "new theme row state",
            ],
        }
    if module == "routes":
        return {
            "authorizationAction": "create_route" if action == "create" else "bind_route",
            "stopAfter": "route row or binding state is verified; do not assume frontend render",
            "mustCapture": [
                "route dialog fields",
                "POST URL/method and payload shape",
                "component response validation errors if any",
                "backend route row binding state",
                "frontend HTTP and DOM for the affected path",
            ],
        }
    if module == "forms":
        return {
            "authorizationAction": "create_form_probe",
            "stopAfter": "probe form row or dialog state is verified; do not publish/embed/delete in same authorization",
            "mustCapture": [
                "whether create opens dialog or creates row",
                "form field schema",
                "save POST URL/method and payload shape if saved",
                "backend row state",
            ],
        }
    if module == "media":
        return {
            "authorizationAction": "upload_media",
            "stopAfter": "single test asset upload is verified; do not reuse endpoint for batch media yet",
            "mustCapture": [
                "file picker or upload endpoint behavior",
                "multipart/storage request shape",
                "public asset URL load",
                "media row metadata",
            ],
        }
    if module == "site-info":
        return {
            "authorizationAction": "save_site_settings",
            "stopAfter": "settings save is verified; do not combine with domain/tracking/theme changes",
            "mustCapture": [
                "save POST URL/method and payload shape",
                "site name/description fields only if user authorized exact values",
                "backend reload state",
                "frontend metadata if relevant",
            ],
        }
    if module == "domains":
        return {
            "authorizationAction": "add_domain",
            "stopAfter": "domain row/status is verified; do not change DNS or retry SSL checks in the same authorization",
            "mustCapture": [
                "domain input validation behavior",
                "add-domain POST URL/method and payload shape",
                "CNAME/verification response, redacted",
                "backend domain row status",
                "external DNS follow-up required, if any",
            ],
        }
    if module == "tracking":
        return {
            "authorizationAction": "add_tracking_tag",
            "stopAfter": "tracking tag row/state is verified; do not combine with site-info, theme, or domain changes",
            "mustCapture": [
                "tracking input validation behavior",
                "add-tag POST URL/method and payload shape",
                "backend tracking state after reload",
                "frontend tag presence only if public verification is in scope",
            ],
        }
    return {
        "authorizationAction": f"{action}_{module}",
        "stopAfter": "one action is captured and backend state is re-read",
        "mustCapture": [
            "action-specific authorization",
            "POST URL/method and payload shape",
            "required ids and volatile headers, redacted",
            "backend state verification",
            "frontend verification when public",
        ],
    }


def build_plan(summary: dict[str, Any], site_key: str, modules_filter: set[str] | None) -> dict[str, Any]:
    actions = summary.get("captureNextActions")
    if not isinstance(actions, list):
        raise ValueError("summary.captureNextActions must be an array")
    stages: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        module = str(action.get("module", "")).strip()
        action_name = str(action.get("action", "")).strip()
        if not module or not action_name:
            continue
        if modules_filter and module not in modules_filter:
            continue
        stage = stage_for(module, action_name)
        stages.append(
            {
                "group": risk_group(module, action_name),
                "module": module,
                "action": action_name,
                "target": target_path(site_key, module),
                "currentStatus": action.get("status", ""),
                "jsonReplayReady": False,
                "authorizationAction": stage["authorizationAction"],
                "stopAfter": stage["stopAfter"],
                "mustCapture": stage["mustCapture"],
                "requiredProof": action.get("requiredProof", []),
            }
        )
    return {
        "kind": "allincms_module_capture_plan",
        "siteKey": site_key or "{siteKey}",
        "sourceSummaryKind": summary.get("kind"),
        "jsonReplayReady": False,
        "rule": "Execute at most one capture stage per explicit authorization; a capture plan is not permission to mutate LAICMS.",
        "stages": stages,
    }


def parse_modules(raw: str) -> set[str] | None:
    if not raw.strip():
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a staged AllinCMS module capture plan.")
    parser.add_argument("summary_json")
    parser.add_argument("--site-key", default="", help="Optional safe site key for target URLs")
    parser.add_argument("--modules", default="", help="Comma-separated module filter, e.g. products,routes")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        plan = build_plan(load_summary(Path(args.summary_json)), args.site_key.strip(), parse_modules(args.modules))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
