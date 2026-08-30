#!/usr/bin/env python3
"""Validate pages/site-info execution evidence from a browser handoff."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"cookie\s*[:=]", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
REQUIRED_PAGE_PROOFS = (
    "createThemePageVerified",
    "designSaved",
    "designPublished",
    "pageEnabled",
    "routeBound",
    "frontendVerified",
)
STARTER_TEMPLATE_TERMS = (
    "starter template",
    "starter commerce",
    "default template",
    "legacy demo",
    "template residue",
    "template body",
    "template product",
    "template post",
    "template navigation",
)
ACTION_TO_PAGE_PROOF = {
    "create_theme_page": "createThemePageVerified",
    "save_design": "designSaved",
    "publish_design": "designPublished",
    "enable_theme_page": "pageEnabled",
    "bind_route": "routeBound",
}


def load_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} root must be an object")
    return data


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(walk_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(walk_strings(item))
        return out
    return []


def no_placeholder_url(value: str, label: str) -> list[str]:
    issues: list[str] = []
    if not value.strip():
        return [f"{label} is required"]
    if "{" in value or "}" in value:
        issues.append(f"{label} must be concrete, not a placeholder URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        issues.append(f"{label} must be an https URL")
    return issues


def expected_frontend_url(frontend_base: str, path: str) -> str:
    if path == "/":
        return frontend_base.rstrip("/")
    return frontend_base.rstrip("/") + path


def handoff_page_paths(handoff: dict[str, Any]) -> set[str]:
    pages = handoff.get("pages")
    paths: set[str] = set()
    if isinstance(pages, list):
        for item in pages:
            if not isinstance(item, dict):
                continue
            page = item.get("page")
            if isinstance(page, dict) and isinstance(page.get("path"), str):
                paths.add(page["path"])
    return paths


def handoff_page_action_names(handoff: dict[str, Any], path: str) -> set[str]:
    pages = handoff.get("pages")
    if not isinstance(pages, list):
        return set()
    for item in pages:
        if not isinstance(item, dict):
            continue
        page = item.get("page")
        if not isinstance(page, dict) or page.get("path") != path:
            continue
        actions = item.get("actions")
        if not isinstance(actions, list):
            return set()
        return {
            action.get("action")
            for action in actions
            if isinstance(action, dict) and isinstance(action.get("action"), str)
        }
    return set()


def validate_site_info(site_info: Any, site_key: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(site_info, dict):
        return ["siteInfo must be an object"]
    if site_info.get("status") != "verified":
        issues.append("siteInfo.status must be verified")
    for key in ("saveStatus", "backendVerified", "persistedVerified"):
        expected = "ok" if key == "saveStatus" else True
        if site_info.get(key) != expected:
            issues.append(f"siteInfo.{key} must be {expected}")
    target = site_info.get("target")
    if not isinstance(target, str):
        issues.append("siteInfo.target is required")
    else:
        issues.extend(no_placeholder_url(target, "siteInfo.target"))
        if f"/{site_key}/site-info" not in target:
            issues.append("siteInfo.target must belong to the current site-info route")
    request = site_info.get("requestCapture")
    if not isinstance(request, dict):
        issues.append("siteInfo.requestCapture must be an object")
    else:
        if request.get("method") != "POST":
            issues.append("siteInfo.requestCapture.method must be POST")
        if not isinstance(request.get("payloadShape"), dict) or not request["payloadShape"]:
            issues.append("siteInfo.requestCapture.payloadShape must be a non-empty redacted object")
        response_status = request.get("responseStatus")
        if not isinstance(response_status, int) or response_status < 200 or response_status >= 300:
            issues.append("siteInfo.requestCapture.responseStatus must be a 2xx integer")
        headers = request.get("headers")
        if not isinstance(headers, list) or not headers:
            issues.append("siteInfo.requestCapture.headers must be header names only")
        else:
            for header in headers:
                if not isinstance(header, str) or not header.strip() or ":" in header or "=" in header:
                    issues.append("siteInfo.requestCapture.headers must contain header names only")
                    break
    return issues


def site_info_field_count(site_info: Any) -> int:
    if not isinstance(site_info, dict):
        return 0
    count = 0
    if site_info.get("status") == "verified":
        count += 1
    for key, expected in (("saveStatus", "ok"), ("backendVerified", True), ("persistedVerified", True)):
        if site_info.get(key) == expected:
            count += 1
    request = site_info.get("requestCapture")
    if isinstance(request, dict) and request.get("method") == "POST" and isinstance(request.get("payloadShape"), dict):
        count += len([key for key, value in request["payloadShape"].items() if isinstance(key, str) and value])
    return count


def validate_pages(pages: Any, handoff: dict[str, Any], site_key: str, frontend_base: str) -> list[str]:
    issues: list[str] = []
    expected_paths = handoff_page_paths(handoff)
    if not isinstance(pages, list) or not pages:
        return ["pages must be a non-empty array"]
    seen: set[str] = set()
    for index, page in enumerate(pages):
        label = f"pages[{index}]"
        if not isinstance(page, dict):
            issues.append(f"{label} must be an object")
            continue
        path = page.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(f"{label}.path must be an absolute path")
            continue
        seen.add(path)
        if path not in expected_paths:
            issues.append(f"{label}.path was not present in the handoff pages")
        required_action_names = handoff_page_action_names(handoff, path)
        if not required_action_names:
            issues.append(f"{label}.actions could not be derived from handoff")
        required_page_proofs = {
            ACTION_TO_PAGE_PROOF[action]
            for action in required_action_names
            if action in ACTION_TO_PAGE_PROOF
        }
        required_page_proofs.add("frontendVerified")
        for key in sorted(required_page_proofs):
            if page.get(key) is not True:
                issues.append(f"{label}.{key} must be true")
        if path == "/" and page.get("homepageVerified") is not True:
            issues.append(f"{label}.homepageVerified must be true for homepage path")
        backend_url = page.get("backendUrl")
        if not isinstance(backend_url, str):
            issues.append(f"{label}.backendUrl is required")
        else:
            issues.extend(no_placeholder_url(backend_url, f"{label}.backendUrl"))
            if f"/{site_key}/themes" not in backend_url and f"/{site_key}/routes" not in backend_url:
                issues.append(f"{label}.backendUrl must belong to current site theme or route area")
        frontend_url = page.get("frontendUrl")
        expected_url = expected_frontend_url(frontend_base, path)
        if frontend_url != expected_url:
            issues.append(f"{label}.frontendUrl must be {expected_url}")
        route_path = page.get("routePath")
        if not isinstance(route_path, str) or route_path != path:
            issues.append(f"{label}.routePath must match path")
        render_audit = page.get("renderAudit")
        if not isinstance(render_audit, dict):
            issues.append(f"{label}.renderAudit must be an object with source-content and starter-template checks")
        else:
            if render_audit.get("sourceContentVerified") is not True:
                issues.append(f"{label}.renderAudit.sourceContentVerified must be true")
            if render_audit.get("starterTemplateAbsent") is not True:
                issues.append(f"{label}.renderAudit.starterTemplateAbsent must be true")
            expected_signals = render_audit.get("expectedSourceSignals")
            if not isinstance(expected_signals, list) or not expected_signals:
                issues.append(f"{label}.renderAudit.expectedSourceSignals must list redacted source-content signals")
            elif not all(isinstance(item, str) and item.strip() for item in expected_signals):
                issues.append(f"{label}.renderAudit.expectedSourceSignals must contain non-empty strings")
            unexpected_signals = render_audit.get("unexpectedStarterSignals")
            if not isinstance(unexpected_signals, list):
                issues.append(f"{label}.renderAudit.unexpectedStarterSignals must be an array")
            elif unexpected_signals:
                issues.append(f"{label}.renderAudit.unexpectedStarterSignals must be empty")
            proof = render_audit.get("proof")
            if not isinstance(proof, str) or not proof.strip():
                issues.append(f"{label}.renderAudit.proof must be a non-empty redacted string")
            audit_text = "\n".join(walk_strings(render_audit)).lower()
            if any(term in audit_text for term in STARTER_TEMPLATE_TERMS):
                issues.append(f"{label}.renderAudit must not contain starter-template terms as proof")
        action_evidence = page.get("actionEvidence")
        if not isinstance(action_evidence, dict):
            issues.append(f"{label}.actionEvidence must be an object keyed by action")
        else:
            for action in sorted(required_action_names):
                proof = action_evidence.get(action)
                if not isinstance(proof, dict) or proof.get("preMutationGate") != "passed" or proof.get("verified") is not True:
                    issues.append(f"{label}.actionEvidence.{action} must have preMutationGate=passed and verified=true")
    missing = sorted(expected_paths - seen)
    if missing:
        issues.append("pages missing handoff paths: " + ", ".join(missing))
    return issues


def validate_evidence(data: dict[str, Any], handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_pages_site_info_execution_evidence":
        issues.append("kind must be allincms_pages_site_info_execution_evidence")
    if handoff.get("kind") != "allincms_pages_site_info_browser_handoff":
        issues.append("handoff kind must be allincms_pages_site_info_browser_handoff")
    site_key = data.get("siteKey")
    handoff_site_key = handoff.get("siteKey")
    if not isinstance(site_key, str) or not site_key:
        issues.append("siteKey is required")
        site_key = ""
    elif site_key != handoff_site_key:
        issues.append("siteKey must match handoff.siteKey")
    frontend_base = handoff.get("frontendBaseUrl")
    if not isinstance(frontend_base, str) or not frontend_base.startswith("https://"):
        issues.append("handoff.frontendBaseUrl must be an https URL")
        frontend_base = ""
    if data.get("remoteMutationsPerformed") is not True:
        issues.append("remoteMutationsPerformed must be true for completed execution evidence")
    if data.get("preMutationGatesPassed") is not True:
        issues.append("preMutationGatesPassed must be true")
    if data.get("stopConditionMet") is not True:
        issues.append("stopConditionMet must be true")
    blocking = data.get("blockingIssues")
    if not isinstance(blocking, list):
        issues.append("blockingIssues must be an array")
    elif blocking:
        issues.append("blockingIssues must be empty")
    if site_key:
        issues.extend(validate_site_info(data.get("siteInfo"), site_key))
    if site_key and frontend_base:
        issues.extend(validate_pages(data.get("pages"), handoff, site_key, frontend_base))
    all_text = "\n".join(walk_strings(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pages/site-info execution evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json), "evidence")
        handoff = load_json(Path(args.handoff), "handoff")
        issues = validate_evidence(evidence, handoff)
        report = {
            "kind": "allincms_pages_site_info_execution_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "handoff": args.handoff,
            "siteKey": evidence.get("siteKey"),
            "pageCount": len(evidence.get("pages", [])) if isinstance(evidence.get("pages"), list) else 0,
            "siteInfoFieldCount": site_info_field_count(evidence.get("siteInfo")),
            "issues": issues,
            "launchPrerequisiteSatisfied": not issues,
        }
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
