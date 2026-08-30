#!/usr/bin/env python3
"""Validate redacted save-probe capture evidence before merging."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from prepare_probe_save_handoff import parse_edit_url


FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"cookie\s*[:=]", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]\s*[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"next-router-state-tree\s*[:=]", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
)
FORBIDDEN_PLACEHOLDER_PATTERNS = (
    re.compile(r"\bto_fill_after_capture\b", re.IGNORECASE),
    re.compile(r"\bto_verify\b", re.IGNORECASE),
    re.compile(r"\brequired_before_save\b", re.IGNORECASE),
    re.compile(r"\bcaptured-non-empty-editor-block-shape-required\b", re.IGNORECASE),
    re.compile(r"\{captured[^}]*\}", re.IGNORECASE),
    re.compile(r"\{[^}]*ContentBlocks[^}]*\}", re.IGNORECASE),
)
REQUIRED_CAPTURE_KEYS = (
    "method",
    "url",
    "headers",
    "payloadShape",
    "contentBlockShape",
    "idFields",
    "mode",
    "publishBehavior",
    "responseStatus",
    "responseMimeType",
)
REQUIRED_FIELD_MAPPING_KEYS = ("nameField", "slugField", "descriptionField", "statusField")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"evidence JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid evidence JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("evidence JSON root must be an object")
    return data


def base_site_key_and_content_type(base: dict[str, Any]) -> tuple[str, str]:
    site_identity = base.get("siteIdentity")
    content_inspection = base.get("contentInspection")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("base run evidence must include siteIdentity.siteKey")
    if not isinstance(content_inspection, dict) or not isinstance(content_inspection.get("contentType"), str):
        raise ValueError("base run evidence must include contentInspection.contentType")
    return site_identity["siteKey"], content_inspection["contentType"]


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


def validate_url(url: str, site_key: str, content_type: str) -> list[str]:
    issues: list[str] = []
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        issues.append("requestCapture.url must be an https workspace.laicms.com URL")
    expected_prefix = f"/{site_key}/{content_type}"
    if not parsed.path.startswith(expected_prefix):
        issues.append(f"requestCapture.url must start with {expected_prefix}")
    return issues


def validate_headers(headers: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(headers, list) or not headers:
        return ["requestCapture.headers must be a non-empty list of header names"]
    lowered = []
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
    for key in ("siteId", "mode"):
        if key not in payload_shape:
            issues.append(f"requestCapture.payloadShape must include {key}")
    if not any(key in payload_shape for key in ("productId", "postId", "formId", "id", "contentId")):
        issues.append("requestCapture.payloadShape must include a redacted content id field name")
    return issues


def validate_capture_evidence(data: dict[str, Any], base_run_evidence: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_probe_save_capture_evidence":
        issues.append("kind must be allincms_probe_save_capture_evidence")
    if data.get("savedOnce") is not True:
        issues.append("savedOnce must be true after a completed save capture")
    if data.get("published") is not False:
        issues.append("published must be false for the save-only stage")
    if data.get("backendPersisted") is not True:
        issues.append("backendPersisted must be true after backend persistence verification")
    if data.get("stopConditionMet") is not True:
        issues.append("stopConditionMet must be true")
    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")

    target = data.get("target")
    target_parts: dict[str, str] = {}
    if not isinstance(target, str):
        issues.append("target must be a concrete edit URL")
    else:
        try:
            target_parts = parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    content_type = data.get("contentType")
    if target_parts and content_type != target_parts["contentType"]:
        issues.append("contentType must match target")
    if base_run_evidence is not None:
        try:
            base_site_key, base_content_type = base_site_key_and_content_type(base_run_evidence)
        except ValueError as exc:
            issues.append(str(exc))
        else:
            if target_parts and target_parts["siteKey"] != base_site_key:
                issues.append("target siteKey must match base run evidence siteKey")
            if target_parts and target_parts["contentType"] != base_content_type:
                issues.append("target contentType must match base run evidence contentType")

    request_capture = data.get("requestCapture")
    if not isinstance(request_capture, dict):
        issues.append("requestCapture must be an object")
    else:
        for key in REQUIRED_CAPTURE_KEYS:
            if key not in request_capture:
                issues.append(f"requestCapture.{key} is required")
        method = request_capture.get("method")
        if method != "POST":
            issues.append("requestCapture.method must be POST for the verified save stage")
        url = request_capture.get("url")
        if target_parts and isinstance(url, str):
            issues.extend(validate_url(url, target_parts["siteKey"], target_parts["contentType"]))
        else:
            issues.append("requestCapture.url must be present")
        issues.extend(validate_headers(request_capture.get("headers")))
        issues.extend(validate_payload_shape(request_capture.get("payloadShape")))
        if not isinstance(request_capture.get("contentBlockShape"), str) or not request_capture["contentBlockShape"].strip():
            issues.append("requestCapture.contentBlockShape must be a redacted non-empty string")
        if not isinstance(request_capture.get("idFields"), str) or not request_capture["idFields"].strip():
            issues.append("requestCapture.idFields must be a redacted non-empty string")
        if not isinstance(request_capture.get("mode"), str) or not request_capture["mode"].strip():
            issues.append("requestCapture.mode must be a non-empty string")
        if request_capture.get("publishBehavior") != "publish-separate":
            issues.append("requestCapture.publishBehavior must be publish-separate for save-only proof")
        response_status = request_capture.get("responseStatus")
        if not isinstance(response_status, int) or response_status < 200 or response_status >= 300:
            issues.append("requestCapture.responseStatus must be a 2xx integer")

    field_mapping = data.get("fieldMapping")
    if not isinstance(field_mapping, dict):
        issues.append("fieldMapping must be an object")
    else:
        for key in REQUIRED_FIELD_MAPPING_KEYS:
            value = field_mapping.get(key)
            if not isinstance(value, str) or not value.strip() or value == "to_verify":
                issues.append(f"fieldMapping.{key} must be verified")

    payload_template = data.get("payloadTemplate")
    if not isinstance(payload_template, dict) or not payload_template:
        issues.append("payloadTemplate must be a non-empty redacted object")

    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    for pattern in FORBIDDEN_PLACEHOLDER_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains unfilled capture template placeholders")
            break
    return issues


def to_merge_args(data: dict[str, Any]) -> dict[str, str]:
    request = data["requestCapture"]
    return {
        "url": request["url"],
        "method": request["method"],
        "headers": ", ".join(request["headers"]),
        "payloadShape": json.dumps(request["payloadShape"], ensure_ascii=False, sort_keys=True),
        "contentBlockShape": request["contentBlockShape"],
        "idFields": request["idFields"],
        "mode": request["mode"],
        "publishBehavior": request["publishBehavior"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted save-probe capture evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--merge-args-output", help="Write merge_probe_evidence-compatible JSON args")
    parser.add_argument("--base-run-evidence", help="Optional run evidence JSON to bind siteKey/contentType before merge")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json))
        base = load_json(Path(args.base_run_evidence)) if args.base_run_evidence else None
        issues = validate_capture_evidence(evidence, base)
        report = {
            "kind": "allincms_probe_save_capture_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "baseRunEvidence": args.base_run_evidence or "",
            "target": evidence.get("target"),
            "contentType": evidence.get("contentType"),
            "issues": issues,
            "mergeReady": not issues,
        }
        if args.merge_args_output and not issues:
            output = Path(args.merge_args_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(to_merge_args(evidence), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
