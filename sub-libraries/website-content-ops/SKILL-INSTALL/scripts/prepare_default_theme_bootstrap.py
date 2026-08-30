#!/usr/bin/env python3
"""Prepare a default-theme bootstrap runbook for blank AllinCMS sites."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from prepare_browser_stage_authorization import AUTH_PLACEHOLDER
from validate_run_evidence import validate as validate_run_evidence


REQUIRED_PUBLIC_PATHS = ["/", "/home", "/products", "/posts", "/about-us", "/contact-us"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output path must be outside the skill package")


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def site_identity(preflight: dict[str, Any]) -> tuple[str, str]:
    site = preflight.get("siteIdentity")
    if not isinstance(site, dict):
        raise SystemExit("ERROR: preflight.siteIdentity is required")
    site_key = site.get("siteKey")
    frontend_base = site.get("frontendBaseUrl")
    if not isinstance(site_key, str) or not site_key.strip() or site_key.startswith("{"):
        raise SystemExit("ERROR: preflight.siteIdentity.siteKey must be concrete")
    if not isinstance(frontend_base, str) or not frontend_base.startswith("https://"):
        raise SystemExit("ERROR: preflight.siteIdentity.frontendBaseUrl must be concrete")
    return site_key, frontend_base.rstrip("/")


def require_theme_preflight(preflight: dict[str, Any]) -> list[str]:
    setup = preflight.get("setupPages")
    if not isinstance(setup, dict):
        return ["preflight.setupPages is required"]
    issues: list[str] = []
    for key in ("themes", "routes"):
        if not isinstance(setup.get(key), list) or not setup[key]:
            issues.append(f"preflight.setupPages.{key} must contain read-only evidence")
    return issues


def auth_command(
    *,
    action: str,
    site_key: str,
    target: str,
    target_identifier: str,
    fields: list[str],
    expected: str,
    verification: str,
    cleanup: str,
    output: str,
) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        f"--action {action} "
        f"--site-key {site_key} "
        f"--target {target} "
        "--target-type themes "
        f"--target-identifier '{target_identifier}' "
        f"--fields-or-files {','.join(fields)} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{AUTH_PLACEHOLDER}' "
        f"--output {output}"
    )


def gate_command(action: str, preflight: str, authorization: str) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        f"--action {action} --preflight {preflight} --authorization {authorization}"
    )


def evidence_template(site_key: str, frontend_base: str, target: str, theme_name: str) -> dict[str, Any]:
    return {
        "kind": "allincms_default_theme_bootstrap_evidence",
        "siteKey": site_key,
        "target": target,
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": True,
        "stopConditionMet": True,
        "createdDefaultTheme": True,
        "preset": "默认",
        "themeName": theme_name,
        "themeId": "<record after backend row/design URL verification>",
        "pageCount": 0,
        "expectedStarterPages": [
            {"name": "Home", "path": "/home"},
            {"name": "Products", "path": "/products"},
            {"name": "Product Detail", "path": "/products/{product}"},
            {"name": "Posts", "path": "/posts"},
            {"name": "Post Detail", "path": "/posts/{post}"},
            {"name": "About Us", "path": "/about-us"},
            {"name": "Contact Us", "path": "/contact-us"},
        ],
        "createTheme": {
            "action": "create_theme",
            "preMutationGate": "passed",
            "backendVerified": True,
            "requestCapture": {
                "method": "POST",
                "url": target,
                "headers": ["accept", "content-type"],
                "payloadShape": {"name": "string", "preset": "default", "description": "string"},
                "responseStatus": 200,
                "responseMimeType": "text/x-component or application/json",
            },
        },
        "activateTheme": {
            "action": "activate_theme",
            "preMutationGate": "passed",
            "routeMappingReviewed": True,
            "themeEnabled": True,
            "backendVerified": True,
        },
        "routes": {
            "routesBound": True,
            "backendVerified": True,
            "checkedRoutes": ["/home", "/products", "/products/{product}", "/posts", "/posts/{post}", "/about-us", "/contact-us"],
        },
        "frontend": {
            "baseUrl": frontend_base,
            "checkedPaths": [
                {"path": path, "url": frontend_base + ("" if path == "/" else path), "statusOk": True, "domNonEmpty": True}
                for path in REQUIRED_PUBLIC_PATHS
            ],
            "genericTemplateContentRemaining": True,
            "businessContentComplete": False,
        },
        "blockingIssues": [],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    preflight = load_json(Path(args.preflight), "preflight")
    validation_issues = validate_run_evidence(preflight)
    validation_issues.extend(require_theme_preflight(preflight))
    site_key, frontend_base = site_identity(preflight)
    target = f"https://workspace.laicms.com/{site_key}/themes"
    auth_create = str(output.parent / "authorization-create-default-theme.json")
    auth_activate = str(output.parent / "authorization-activate-default-theme.json")
    theme_name = args.theme_name.strip() or "Default Launch Theme"

    runbook = {
        "kind": "allincms_default_theme_bootstrap_runbook",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourcePreflight": args.preflight,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "target": target,
        "theme": {
            "name": theme_name,
            "preset": "默认",
            "description": "Default starter theme to unblock blank/404 first-launch setup.",
        },
        "readyForBrowserStage": "blocked_preflight" if validation_issues else "ready_to_prepare_action_specific_authorization",
        "validationIssues": validation_issues,
        "actions": [
            {
                "action": "create_theme",
                "target": target,
                "targetType": "themes",
                "targetIdentifier": f"{theme_name} preset 默认",
                "fieldsOrFiles": ["requestCapture", "themeId", "backendVerified", "preset", "pageCount"],
                "authorizationOutput": auth_create,
                "authorizationRecordCommand": auth_command(
                    action="create_theme",
                    site_key=site_key,
                    target=target,
                    target_identifier=f"{theme_name} preset 默认",
                    fields=["requestCapture", "themeId", "backendVerified", "preset", "pageCount"],
                    expected="default preset theme row exists and generated starter pages are visible",
                    verification="capture create-theme request, verify preset 默认, theme id, backend row, and generated page count",
                    cleanup="stop after default theme creation proof; activation requires a separate action",
                    output=auth_create,
                ),
                "preMutationGateCommand": gate_command("create_theme", args.preflight, auth_create),
                "browserStepsExecutable": False,
            },
            {
                "action": "activate_theme",
                "target": target,
                "targetType": "themes",
                "targetIdentifier": f"{theme_name} activate after route mapping review",
                "fieldsOrFiles": ["themeId", "routeMappingReviewed", "themeEnabled", "frontendVerified"],
                "authorizationOutput": auth_activate,
                "authorizationRecordCommand": auth_command(
                    action="activate_theme",
                    site_key=site_key,
                    target=target,
                    target_identifier=f"{theme_name} activate after route mapping review",
                    fields=["themeId", "routeMappingReviewed", "themeEnabled", "frontendVerified"],
                    expected="default theme is enabled and required public routes render non-empty DOM",
                    verification="verify theme list enabled state, route mapping, and public frontend paths",
                    cleanup="stop after activation and frontend route proof; content replacement remains separate",
                    output=auth_activate,
                ),
                "preMutationGateCommand": gate_command("activate_theme", args.preflight, auth_activate),
                "browserStepsExecutable": False,
            },
        ],
        "evidenceTemplate": evidence_template(site_key, frontend_base, target, theme_name),
        "forbiddenActions": [
            "creating a blank theme for first-launch recovery unless explicitly requested",
            "claiming business content is complete from default template pages",
            "uploading products/posts before schema capture and sample verification",
            "treating theme activation toast as public route proof without refreshed backend and frontend checks",
        ],
        "nextAction": (
            "refresh themes/routes preflight before default theme bootstrap"
            if validation_issues
            else "create the default theme and activate it as two separately authorized mutations, then validate bootstrap evidence"
        ),
    }
    write_json(output, runbook)
    return {
        "kind": "allincms_default_theme_bootstrap_preparation",
        "runbook": str(output),
        "readyForBrowserStage": runbook["readyForBrowserStage"],
        "validationIssues": validation_issues,
        "siteKey": site_key,
        "nextAction": runbook["nextAction"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a default-theme bootstrap runbook.")
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--theme-name", default="Default Launch Theme")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    print(f"Wrote default-theme bootstrap runbook: {summary['runbook']}")
    print(f"siteKey={summary['siteKey']} ready={summary['readyForBrowserStage']} nextAction={summary['nextAction']}")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["validationIssues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
