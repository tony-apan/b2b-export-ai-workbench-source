#!/usr/bin/env python3
"""Validate redacted create_theme_page evidence before later launch stages rely on it."""

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
ALLOWED_DYNAMIC_ROUTES = {"/products/{product}", "/posts/{post}"}
REQUIRED_PAYLOAD_KEYS = {"siteId", "themeId", "name", "path"}


def load_json(path: Path, label: str = "evidence") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def walk_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(walk_string_values(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(walk_string_values(item))
    return strings


def site_key_from_target(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        raise ValueError("target must be an https workspace.laicms.com URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[1] != "themes":
        raise ValueError("target must point to a site theme route")
    return parts[0]


def validate_headers(headers: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(headers, list) or not headers:
        return ["requestCapture.headers must be a non-empty list of header names"]
    lowered: list[str] = []
    for header in headers:
        if not isinstance(header, str) or not header.strip():
            issues.append("requestCapture.headers must contain non-empty strings")
            continue
        if ":" in header or "=" in header:
            issues.append("requestCapture.headers must contain header names only, not values")
        lowered.append(header.strip().lower())
    for forbidden in ("cookie", "authorization"):
        if forbidden in lowered:
            issues.append(f"requestCapture.headers must not include {forbidden}")
    for required in ("accept", "content-type"):
        if required not in lowered:
            issues.append(f"requestCapture.headers should include {required}")
    return issues


def validate_payload_shape(payload_shape: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(payload_shape, dict) or not payload_shape:
        return ["requestCapture.payloadShape must be a non-empty redacted object"]
    missing = sorted(REQUIRED_PAYLOAD_KEYS - set(payload_shape))
    if missing:
        issues.append(f"requestCapture.payloadShape missing required keys: {missing}")
    return issues


def validate_evidence(data: dict[str, Any], base_run_evidence: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_theme_page_create_evidence":
        issues.append("kind must be allincms_theme_page_create_evidence")
    if data.get("action") != "create_theme_page":
        issues.append("action must be create_theme_page")
    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")
    if data.get("createdOnce") is not True:
        issues.append("createdOnce must be true after a completed create action")
    if data.get("backendVerified") is not True:
        issues.append("backendVerified must be true")
    if data.get("stopConditionMet") is not True:
        issues.append("stopConditionMet must be true")

    target = data.get("target")
    site_key = ""
    if not isinstance(target, str):
        issues.append("target must be a concrete theme URL")
    else:
        try:
            site_key = site_key_from_target(target)
        except ValueError as exc:
            issues.append(str(exc))
    if base_run_evidence is not None and site_key:
        site_identity = base_run_evidence.get("siteIdentity")
        if not isinstance(site_identity, dict) or site_identity.get("siteKey") != site_key:
            issues.append("target siteKey must match base run evidence siteKey")

    route_path = data.get("routePath")
    if route_path not in ALLOWED_DYNAMIC_ROUTES:
        issues.append(f"routePath must be one of {sorted(ALLOWED_DYNAMIC_ROUTES)}")
    page_name = data.get("pageName")
    if not isinstance(page_name, str) or not page_name.strip():
        issues.append("pageName must be a non-empty string")
    page_id = data.get("pageId")
    if not isinstance(page_id, str) or not page_id.strip() or page_id == "to_verify":
        issues.append("pageId must be recorded after backend verification")
    backend_evidence = data.get("backendEvidence")
    if not isinstance(backend_evidence, str) or not backend_evidence.strip():
        issues.append("backendEvidence must describe the verified backend row")

    request_capture = data.get("requestCapture")
    if not isinstance(request_capture, dict):
        issues.append("requestCapture must be an object")
    else:
        if request_capture.get("method") != "POST":
            issues.append("requestCapture.method must be POST")
        url = request_capture.get("url")
        if not isinstance(url, str) or not site_key or f"/{site_key}/themes" not in url:
            issues.append("requestCapture.url must be under the current site's themes route")
        issues.extend(validate_headers(request_capture.get("headers")))
        issues.extend(validate_payload_shape(request_capture.get("payloadShape")))
        response_status = request_capture.get("responseStatus")
        if not isinstance(response_status, int) or response_status < 200 or response_status >= 300:
            issues.append("requestCapture.responseStatus must be a 2xx integer")
        response_mime = request_capture.get("responseMimeType")
        if not isinstance(response_mime, str) or not response_mime.strip():
            issues.append("requestCapture.responseMimeType must be recorded")

    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted create_theme_page evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--base-run-evidence", default="")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json), "evidence")
        base = load_json(Path(args.base_run_evidence), "base run evidence") if args.base_run_evidence else None
        issues = validate_evidence(evidence, base)
        report = {
            "kind": "allincms_theme_page_create_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "baseRunEvidence": args.base_run_evidence,
            "target": evidence.get("target"),
            "routePath": evidence.get("routePath"),
            "issues": issues,
            "nextStageReady": not issues,
            "nextActions": [
                "Proceed to a separately authorized design/save/publish/enable/bind stage."
                if not issues
                else "Fix evidence gaps before relying on this theme page for product/post detail routes."
            ],
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
