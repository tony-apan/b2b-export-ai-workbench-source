#!/usr/bin/env python3
"""Validate taxonomy create/map evidence from a prepared taxonomy handoff."""

from __future__ import annotations

import argparse
import json
import re
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


def load_json(path: Path, label: str) -> dict[str, Any]:
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
        out: list[str] = []
        for item in value:
            out.extend(walk_strings(item))
        return out
    return []


def expected_terms(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    terms: dict[str, dict[str, Any]] = {}
    actions = handoff.get("actions")
    if not isinstance(actions, list):
        return terms
    for action in actions:
        if not isinstance(action, dict):
            continue
        term = action.get("term")
        if not isinstance(term, dict):
            continue
        key = action.get("targetIdentifier")
        if isinstance(key, str) and key:
            terms[key] = {
                "contentType": action.get("contentType"),
                "termKind": action.get("termKind"),
                "slug": term.get("slug"),
                "label": term.get("label"),
                "action": action.get("action"),
            }
    return terms


def validate_backend_url(value: Any, site_key: str, label: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{label} is required"]
    if "{" in value or "}" in value:
        return [f"{label} must be concrete, not a placeholder"]
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        return [f"{label} must be under https://workspace.laicms.com"]
    if f"/{site_key}/" not in parsed.path:
        return [f"{label} must belong to the current site"]
    return []


def validate_mapping(mapping: dict[str, Any], expected: dict[str, dict[str, Any]], site_key: str, index: int) -> list[str]:
    issues: list[str] = []
    label = f"taxonomyMappings[{index}]"
    target_identifier = mapping.get("targetIdentifier")
    if not isinstance(target_identifier, str) or target_identifier not in expected:
        issues.append(f"{label}.targetIdentifier must match a handoff taxonomy action")
        expected_item: dict[str, Any] = {}
    else:
        expected_item = expected[target_identifier]
    for key in ("contentType", "termKind", "slug", "label"):
        if expected_item and mapping.get(key) != expected_item.get(key):
            issues.append(f"{label}.{key} must match handoff term")
    if mapping.get("status") not in {"created", "mapped_existing"}:
        issues.append(f"{label}.status must be created or mapped_existing")
    if mapping.get("preMutationGate") != "passed":
        issues.append(f"{label}.preMutationGate must be passed")
    if mapping.get("backendVerified") is not True:
        issues.append(f"{label}.backendVerified must be true")
    if mapping.get("mappingVerified") is not True:
        issues.append(f"{label}.mappingVerified must be true")
    issues.extend(validate_backend_url(mapping.get("backendUrl"), site_key, f"{label}.backendUrl"))
    request = mapping.get("requestCapture")
    if mapping.get("status") == "created":
        if not isinstance(request, dict):
            issues.append(f"{label}.requestCapture is required for created taxonomy terms")
        else:
            if request.get("method") != "POST":
                issues.append(f"{label}.requestCapture.method must be POST")
            response_status = request.get("responseStatus")
            if not isinstance(response_status, int) or response_status < 200 or response_status >= 300:
                issues.append(f"{label}.requestCapture.responseStatus must be a 2xx integer")
            if not isinstance(request.get("payloadShape"), dict) or not request["payloadShape"]:
                issues.append(f"{label}.requestCapture.payloadShape must be a redacted non-empty object")
    return issues


def validate_evidence(data: dict[str, Any], handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_taxonomy_execution_evidence":
        issues.append("kind must be allincms_taxonomy_execution_evidence")
    if handoff.get("kind") != "allincms_taxonomy_execution_handoff":
        issues.append("handoff kind must be allincms_taxonomy_execution_handoff")
    site_key = data.get("siteKey")
    if not isinstance(site_key, str) or not site_key.strip():
        issues.append("siteKey is required")
        site_key = ""
    elif site_key != handoff.get("siteKey"):
        issues.append("siteKey must match handoff.siteKey")
    ready_stage = handoff.get("readyForBrowserStage")
    if isinstance(ready_stage, str) and ready_stage != "ready_to_prepare_action_specific_taxonomy_authorization":
        issues.append("handoff.readyForBrowserStage must be ready_to_prepare_action_specific_taxonomy_authorization")
    preflight_issues = handoff.get("preflightIssues")
    if isinstance(preflight_issues, list) and preflight_issues:
        issues.append("handoff.preflightIssues must be empty before taxonomy evidence can pass")
    for key in ("remoteMutationsPerformed", "preMutationGatesPassed", "stopConditionMet"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    blocking = data.get("blockingIssues")
    if not isinstance(blocking, list):
        issues.append("blockingIssues must be an array")
    elif blocking:
        issues.append("blockingIssues must be empty")
    expected = expected_terms(handoff)
    mappings = data.get("taxonomyMappings")
    if not isinstance(mappings, list):
        issues.append("taxonomyMappings must be an array")
        mappings = []
    seen: set[str] = set()
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            issues.append(f"taxonomyMappings[{index}] must be an object")
            continue
        target_identifier = mapping.get("targetIdentifier")
        if isinstance(target_identifier, str):
            seen.add(target_identifier)
        issues.extend(validate_mapping(mapping, expected, site_key, index))
    missing = sorted(set(expected) - seen)
    if missing:
        issues.append("taxonomyMappings missing handoff terms: " + ", ".join(missing))
    all_text = "\n".join(walk_strings(data))
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(all_text):
            issues.append("evidence contains forbidden raw credential/header/account text")
            break
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate taxonomy execution evidence.")
    parser.add_argument("evidence_json")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        evidence = load_json(Path(args.evidence_json), "evidence")
        handoff = load_json(Path(args.handoff), "handoff")
        issues = validate_evidence(evidence, handoff)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    report = {
        "kind": "allincms_taxonomy_execution_evidence_validation",
        "valid": not issues,
        "evidence": args.evidence_json,
        "handoff": args.handoff,
        "siteKey": evidence.get("siteKey"),
        "taxonomyMappingCount": len(evidence.get("taxonomyMappings", [])) if isinstance(evidence.get("taxonomyMappings"), list) else 0,
        "taxonomyPrerequisiteSatisfied": not issues,
        "issues": issues,
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
