#!/usr/bin/env python3
"""Build a local browser runbook for one create_theme_page action."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from validate_browser_stage_authorization_package import AUTH_PLACEHOLDER, validate_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def site_key_from_target(target: str) -> str:
    marker = "https://workspace.laicms.com/"
    if not target.startswith(marker):
        raise ValueError("target must be under https://workspace.laicms.com")
    rest = target[len(marker) :]
    site_key = rest.split("/", 1)[0]
    if not site_key:
        raise ValueError("target must include a site key")
    return site_key


def validate_create_theme_page_package(package: dict[str, Any], packet: dict[str, Any] | None, preflight: dict[str, Any] | None) -> list[str]:
    issues = validate_package(package, packet, preflight)
    launch_action = package.get("launchAction")
    if not isinstance(launch_action, dict):
        issues.append("package.launchAction must be an object")
        return issues
    if launch_action.get("action") != "create_theme_page":
        issues.append("package.launchAction.action must be create_theme_page")
    if package.get("stageId") != "theme_page_route_launch":
        issues.append("package.stageId must be theme_page_route_launch")
    if package.get("gateSupported") is not True:
        issues.append("create_theme_page package must have gateSupported=true")
    if package.get("commandsSuppressed") is not False:
        issues.append("create_theme_page package must have concrete commands")
    command = package.get("authorizationRecordCommand")
    if not isinstance(command, str) or AUTH_PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    gate = package.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action create_theme_page" not in gate:
        issues.append("preMutationGateCommand must use --action create_theme_page")
    return issues


def build_runbook(
    package: dict[str, Any],
    *,
    package_path: str,
    packet: dict[str, Any] | None = None,
    packet_path: str = "",
    preflight: dict[str, Any] | None = None,
    preflight_path: str = "",
    page_name: str,
    route_path: str,
    description: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    issues = validate_create_theme_page_package(package, packet, preflight)
    if issues:
        raise ValueError("authorization package validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))

    target = str(package["target"])
    site_key = site_key_from_target(target)
    launch_action = package["launchAction"]
    target_identifier = str(launch_action.get("targetIdentifier", ""))
    if not page_name.strip():
        raise ValueError("--page-name is required")
    if route_path not in {"/products/{product}", "/posts/{post}"}:
        raise ValueError("--route-path must be a redacted dynamic detail route such as /products/{product}")
    if not description.strip():
        raise ValueError("--description is required")

    return {
        "kind": "allincms_theme_page_create_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourcePackage": package_path,
        "sourcePacket": packet_path,
        "sourcePreflight": preflight_path,
        "siteKey": site_key,
        "target": target,
        "targetIdentifier": target_identifier,
        "action": "create_theme_page",
        "authorizationRequired": True,
        "authorizationRecordCommand": package.get("authorizationRecordCommand"),
        "preMutationGateCommand": package.get("preMutationGateCommand"),
        "pageDraft": {
            "name": page_name.strip(),
            "routePath": route_path,
            "description": description.strip(),
        },
        "mustRunBeforeBrowserCreate": [
            "generate authorization record from current user action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "confirm browser is still on the exact target theme page list",
            "enable network capture before clicking the dialog submit button",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_or_claim_theme_page_list",
                "mode": "read_only_until_dialog_submit",
                "target": target,
                "verify": ["URL matches target", "theme page list is visible", "parent Products/Posts row is visible for child-page creation"],
            },
            {
                "step": "open_child_page_dialog",
                "mode": "read_only_dialog_open",
                "action": "open the relevant parent row 创建子页面 dialog",
                "verify": ["dialog title is 创建子页面", "route editor allows the requested dynamic param"],
            },
            {
                "step": "fill_dynamic_page_fields",
                "mode": "mutating_after_gate_on_submit_only",
                "fields": [
                    {"label": "名称", "value": page_name.strip(), "required": True},
                    {"label": "路由", "value": route_path, "required": True},
                    {"label": "描述", "value": description.strip(), "required": True},
                ],
                "verify": ["dialog submit button remains scoped to the create-page dialog"],
            },
            {
                "step": "capture_create_theme_page_request",
                "mode": "mutating_after_gate",
                "action": "click 创建 exactly once",
                "capture": [
                    "POST request under the current theme URL",
                    "redacted request header names only",
                    "payload shape including siteId, themeId, name, path, description, and status fields when present",
                    "response status and component/server-action error state",
                ],
            },
            {
                "step": "verify_backend_page_row",
                "mode": "read_only_after_create",
                "verify": [
                    "theme page list shows the new dynamic page row",
                    "route path is the requested redacted dynamic pattern",
                    "page id or design URL is recorded",
                    "do not save design, publish, enable, bind route, upload products, or cleanup in this authorization",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_theme_page_create_evidence",
            "action": "create_theme_page",
            "target": target,
            "targetIdentifier": target_identifier,
            "pageName": page_name.strip(),
            "routePath": route_path,
            "preMutationGate": "passed|required_before_create",
            "createdOnce": False,
            "requestCapture": {
                "method": "POST",
                "urlPattern": "https://workspace.laicms.com/{siteKey}/themes/{themeId}",
                "headers": [],
                "payloadShape": {},
                "responseStatus": None,
                "responseMimeType": "",
            },
            "pageId": "to_verify",
            "backendVerified": False,
            "backendEvidence": "",
            "stopConditionMet": False,
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "saving page design",
            "publishing page design",
            "enabling the page",
            "setting homepage",
            "binding or rebinding routes",
            "saving, publishing, uploading, or deleting products/posts",
            "JSON/Server Action replay beyond this single create action",
            "cleanup or rollback without separate authorization",
        ],
        "stopAfter": package.get("stopAfter", ""),
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "create_theme_page authorization record exists and the pre-mutation gate passes."
        ),
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_theme_page_create_browser_runbook":
        issues.append("kind must be allincms_theme_page_create_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "create_theme_page":
        issues.append("action must be create_theme_page")
    if runbook.get("authorizationRequired") is not True:
        issues.append("authorizationRequired must be true")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false")
    draft = runbook.get("pageDraft")
    if not isinstance(draft, dict) or draft.get("routePath") not in {"/products/{product}", "/posts/{post}"}:
        issues.append("pageDraft.routePath must be a supported redacted dynamic detail route")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 5:
        issues.append("browserStepsAfterGate must include open, dialog, fill, capture, and verify steps")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("createdOnce") is not False or template.get("backendVerified") is not False:
        issues.append("redactedEvidenceTemplate must start uncreated and unverified")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or AUTH_PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action create_theme_page" not in gate:
        issues.append("preMutationGateCommand must use --action create_theme_page")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "publishing page design" not in forbidden or "binding or rebinding routes" not in forbidden:
        issues.append("forbiddenActions must keep neighboring launch mutations out of scope")
    warning = runbook.get("warning")
    if not isinstance(warning, str) or "local preparation only" not in warning:
        issues.append("warning must state this is local preparation only")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook for one create_theme_page action.")
    parser.add_argument("--package", required=True, help="Validated browser-stage authorization package JSON")
    parser.add_argument("--packet-json", default="")
    parser.add_argument("--preflight", default="")
    parser.add_argument("--page-name", required=True)
    parser.add_argument("--route-path", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        package = load_json(Path(args.package), "package")
        packet = load_json(Path(args.packet_json), "packet") if args.packet_json else None
        preflight = load_json(Path(args.preflight), "preflight") if args.preflight else None
        runbook = build_runbook(
            package,
            package_path=args.package,
            packet=packet,
            packet_path=args.packet_json,
            preflight=preflight,
            preflight_path=args.preflight,
            page_name=args.page_name,
            route_path=args.route_path,
            description=args.description,
        )
        issues = validate_runbook(runbook)
        if issues:
            raise ValueError("runbook validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(runbook, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
