#!/usr/bin/env python3
"""Validate redacted probe cleanup evidence before merging."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from prepare_probe_save_handoff import PROBE_NAME, parse_edit_url


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


def validate_candidate(candidate: Any, site_key: str, content_type: str, index: int) -> list[str]:
    issues: list[str] = []
    if not isinstance(candidate, dict):
        return [f"cleanedCandidates[{index}] must be an object"]
    if candidate.get("contentType") != content_type:
        issues.append(f"cleanedCandidates[{index}].contentType must match cleanup contentType")
    title_pattern = candidate.get("titlePattern")
    if not isinstance(title_pattern, str) or PROBE_NAME not in title_pattern:
        issues.append(f"cleanedCandidates[{index}].titlePattern must include {PROBE_NAME}")
    reason = candidate.get("reason")
    if not isinstance(reason, str) or "probe" not in reason.lower() and "测试" not in reason:
        issues.append(f"cleanedCandidates[{index}].reason must identify probe/test cleanup")
    backend_url = candidate.get("backendUrl")
    if not isinstance(backend_url, str):
        issues.append(f"cleanedCandidates[{index}].backendUrl must be present")
    else:
        parsed = urlparse(backend_url)
        if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
            issues.append(f"cleanedCandidates[{index}].backendUrl must be a workspace URL")
        if not parsed.path.startswith(f"/{site_key}/{content_type}"):
            issues.append(f"cleanedCandidates[{index}].backendUrl must belong to current site/content type")
    return issues


def validate_cleanup_evidence(data: dict[str, Any], base_run_evidence: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_probe_cleanup_evidence":
        issues.append("kind must be allincms_probe_cleanup_evidence")
    if data.get("preMutationGate") != "passed":
        issues.append("preMutationGate must be passed")
    if data.get("backendVerified") is not True:
        issues.append("backendVerified must be true")
    if data.get("frontendVerified") is not True:
        issues.append("frontendVerified must be true")
    if data.get("stopConditionMet") is not True:
        issues.append("stopConditionMet must be true")
    cleanup_action = data.get("cleanupAction")
    if cleanup_action not in {"delete", "unpublish"}:
        issues.append("cleanupAction must be delete or unpublish")
    backend_evidence = data.get("backendEvidence")
    if not isinstance(backend_evidence, str) or not backend_evidence.strip():
        issues.append("backendEvidence must be a non-empty redacted string")
    frontend_evidence = data.get("frontendEvidence")
    if not isinstance(frontend_evidence, str) or not frontend_evidence.strip():
        issues.append("frontendEvidence must be a non-empty redacted string")

    target = data.get("target")
    parts: dict[str, str] = {}
    if not isinstance(target, str):
        issues.append("target must be a concrete edit URL")
    else:
        try:
            parts = parse_edit_url(target)
        except ValueError as exc:
            issues.append(str(exc))
    content_type = data.get("contentType")
    if parts and content_type != parts["contentType"]:
        issues.append("contentType must match target")

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
            sample = base_run_evidence.get("sampleVerification")
            if not isinstance(sample, dict) or sample.get("backendVerified") is not True or sample.get("frontendVerified") is not True:
                issues.append("base run evidence must contain backend/frontend sampleVerification before cleanup")
            elif parts and sample.get("backendUrl") != target:
                issues.append("base sampleVerification.backendUrl must match cleanup target")

    candidates = data.get("cleanedCandidates")
    if not isinstance(candidates, list) or not candidates:
        issues.append("cleanedCandidates must be a non-empty list")
        candidates = []
    cleaned_count = data.get("cleanedCount")
    if cleaned_count != len(candidates):
        issues.append("cleanedCount must equal len(cleanedCandidates)")
    site_key = parts.get("siteKey", "")
    candidate_content_type = parts.get("contentType", str(content_type or ""))
    for index, candidate in enumerate(candidates):
        issues.extend(validate_candidate(candidate, site_key, candidate_content_type, index))

    all_text = "\n".join(walk_string_values(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def to_merge_args(data: dict[str, Any]) -> dict[str, str]:
    candidates = []
    for candidate in data["cleanedCandidates"]:
        candidates.append(
            "|".join(
                [
                    candidate["contentType"],
                    candidate["titlePattern"],
                    candidate["backendUrl"],
                    candidate["reason"],
                ]
            )
        )
    return {
        "cleaned_candidates": ",".join(candidates),
        "cleanup_backend_evidence": data["backendEvidence"],
        "cleanup_frontend_evidence": data["frontendEvidence"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted probe cleanup evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--base-run-evidence", help="Optional run evidence JSON to bind siteKey/contentType/sampleVerification")
    parser.add_argument("--output", help="Write validation report JSON")
    parser.add_argument("--merge-args-output", help="Write merge_probe_evidence-compatible JSON args")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        evidence = load_json(Path(args.evidence_json))
        base = load_json(Path(args.base_run_evidence)) if args.base_run_evidence else None
        issues = validate_cleanup_evidence(evidence, base)
        report = {
            "kind": "allincms_probe_cleanup_evidence_validation",
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
