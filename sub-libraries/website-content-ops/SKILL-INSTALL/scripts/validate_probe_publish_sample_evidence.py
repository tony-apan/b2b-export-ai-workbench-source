#!/usr/bin/env python3
"""Validate redacted publish-probe sample evidence before merging."""

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


def base_site_key_and_content_type(base: dict[str, Any]) -> tuple[str, str]:
    site_identity = base.get("siteIdentity")
    content_inspection = base.get("contentInspection")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("base run evidence must include siteIdentity.siteKey")
    if not isinstance(content_inspection, dict) or not isinstance(content_inspection.get("contentType"), str):
        raise ValueError("base run evidence must include contentInspection.contentType")
    return site_identity["siteKey"], content_inspection["contentType"]


def expected_frontend_prefix(site_key: str, content_type: str) -> str:
    if content_type == "products":
        return f"https://{site_key}.web.allincms.com/products/"
    if content_type == "posts":
        return f"https://{site_key}.web.allincms.com/posts/"
    return f"https://{site_key}.web.allincms.com/{content_type}/"


def validate_publish_sample_evidence(data: dict[str, Any], base_run_evidence: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_probe_publish_sample_evidence":
        issues.append("kind must be allincms_probe_publish_sample_evidence")
    for key in ("publishedOnce", "publishRequestCaptured", "backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified", "stopConditionMet"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")
    if data.get("coverOrMediaVerified") is not True and not isinstance(data.get("coverOrMediaNote"), str):
        issues.append("coverOrMediaVerified must be true or coverOrMediaNote must explain absence")
    status = data.get("status")
    if status not in {"published", "已发布"}:
        issues.append("status must be published or 已发布")
    render_audit = data.get("renderAudit")
    if not isinstance(render_audit, str) or not render_audit.strip():
        issues.append("renderAudit must be a non-empty redacted string")

    target = data.get("target") or data.get("backendUrl")
    parts: dict[str, str] = {}
    if not isinstance(target, str):
        issues.append("target/backendUrl must be a concrete edit URL")
    else:
        try:
            parts = parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    backend_url = data.get("backendUrl")
    if isinstance(backend_url, str) and parts:
        if backend_url != target:
            issues.append("backendUrl must match target")
    else:
        issues.append("backendUrl must be present")
    content_type = data.get("contentType")
    if parts and content_type != parts["contentType"]:
        issues.append("contentType must match target")
    if parts and parts["contentType"] not in {"posts", "products"}:
        issues.append("publish sample evidence currently supports posts or products")

    frontend_url = data.get("frontendUrl")
    if isinstance(frontend_url, str) and parts:
        parsed = urlparse(frontend_url)
        if parsed.scheme != "https" or parsed.netloc != f"{parts['siteKey']}.web.allincms.com":
            issues.append("frontendUrl must belong to the matching AllinCMS frontend host")
        if not frontend_url.startswith(expected_frontend_prefix(parts["siteKey"], parts["contentType"])):
            issues.append("frontendUrl must use the matching content detail route")
    else:
        issues.append("frontendUrl must be present")

    if base_run_evidence is not None:
        try:
            base_site_key, base_content_type = base_site_key_and_content_type(base_run_evidence)
        except ValueError as exc:
            issues.append(str(exc))
        else:
            if parts and parts["siteKey"] != base_site_key:
                issues.append("target siteKey must match base run evidence siteKey")
            if parts and parts["contentType"] != base_content_type:
                issues.append("target contentType must match base run evidence contentType")
            request_capture = base_run_evidence.get("requestCapture")
            if not isinstance(request_capture, dict) or request_capture.get("persistedVerified") is not True:
                issues.append("base run evidence must contain persisted requestCapture before publish sample merge")
            elif parts and request_capture.get("url") != target:
                issues.append("base requestCapture.url must match publish target")

    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def to_merge_args(data: dict[str, Any]) -> dict[str, str]:
    return {
        "backendUrl": data["backendUrl"],
        "frontendUrl": data["frontendUrl"],
        "status": data["status"],
        "renderAudit": data["renderAudit"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted publish-probe sample evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--base-run-evidence", help="Optional run evidence JSON to bind siteKey/contentType/requestCapture")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--merge-args-output", help="Write merge_probe_evidence-compatible JSON args")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json))
        base = load_json(Path(args.base_run_evidence)) if args.base_run_evidence else None
        issues = validate_publish_sample_evidence(evidence, base)
        report = {
            "kind": "allincms_probe_publish_sample_evidence_validation",
            "valid": not issues,
            "evidence": args.evidence_json,
            "baseRunEvidence": args.base_run_evidence or "",
            "target": evidence.get("target") or evidence.get("backendUrl"),
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
