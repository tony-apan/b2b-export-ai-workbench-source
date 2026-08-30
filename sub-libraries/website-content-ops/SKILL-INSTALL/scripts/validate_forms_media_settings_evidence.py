#!/usr/bin/env python3
"""Validate redacted forms/media/settings evidence for AllinCMS launch flow."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from content_goal_coverage_utils import confirmation_decision_matrix_issues


REQUIRED_FLAGS = {
    "siteInfoVerified": "site-info",
    "formsVerified": "forms",
    "mediaVerified": "media",
    "domainsRecorded": "domains",
    "trackingRecorded": "tracking",
}

ALLOWED_MODULES = {"site-info", "forms", "media", "domains", "tracking"}
SAFE_STATUSES = {
    "verified",
    "partially_verified_with_explicit_deferrals",
    "explicitly_out_of_scope",
}

SENSITIVE_PATTERNS = (
    re.compile(r"authorization\s*[:=]", re.IGNORECASE),
    re.compile(r"\bcookie\s*[:=]", re.IGNORECASE),
    re.compile(r"next-action\s*[:=]", re.IGNORECASE),
    re.compile(r"next-router-state-tree", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def iter_strings(value: Any, prefix: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(prefix, value)]
    if isinstance(value, dict):
        found: list[tuple[str, str]] = []
        for key, item in value.items():
            found.extend(iter_strings(item, f"{prefix}.{key}"))
        return found
    if isinstance(value, list):
        found = []
        for index, item in enumerate(value):
            found.extend(iter_strings(item, f"{prefix}[{index}]"))
        return found
    return []


def validate_redaction(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for path, value in iter_strings(data):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                issues.append(f"{path} contains sensitive or raw request material")
                break
    return issues


def validate_wiki_review(data: dict[str, Any], issues: list[str]) -> None:
    review = data.get("wikiReview")
    if review is None:
        return
    if not isinstance(review, dict):
        issues.append("wikiReview must be an object when present")
        return
    for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
        value = review.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"wikiReview.{key} is required when wikiReview is present")
    index = review.get("sourceWikiMarkdownIndex")
    if isinstance(index, str) and index.strip():
        index_path = Path(index).expanduser()
        if not index_path.exists():
            issues.append("wikiReview.sourceWikiMarkdownIndex must point to an existing Markdown file")
        elif index_path.suffix.lower() != ".md":
            issues.append("wikiReview.sourceWikiMarkdownIndex must be a Markdown .md file")
        else:
            try:
                content = index_path.read_text(encoding="utf-8")
            except OSError as exc:
                issues.append(f"wikiReview.sourceWikiMarkdownIndex is not readable: {exc}")
            else:
                if len(content.strip()) < 20 or "#" not in content:
                    issues.append("wikiReview.sourceWikiMarkdownIndex must be a readable Markdown wiki index")


def validate_confirmation_decision_matrix(data: dict[str, Any], issues: list[str]) -> None:
    matrix = data.get("confirmationDecisionMatrix")
    if matrix is None:
        return
    issues.extend(confirmation_decision_matrix_issues(matrix if isinstance(matrix, list) else None))


def deferral_modules(data: dict[str, Any], issues: list[str]) -> set[str]:
    modules: set[str] = set()
    deferrals = data.get("deferrals")
    if deferrals is None:
        return modules
    if not isinstance(deferrals, list):
        issues.append("deferrals must be an array when present")
        return modules
    for index, item in enumerate(deferrals):
        if not isinstance(item, dict):
            issues.append(f"deferrals[{index}] must be an object")
            continue
        module = item.get("module")
        reason = item.get("reason")
        if not isinstance(module, str) or not module.strip():
            issues.append(f"deferrals[{index}].module missing")
            continue
        module = module.strip()
        if module not in ALLOWED_MODULES:
            issues.append(f"deferrals[{index}].module unsupported: {module}")
        modules.add(module)
        if not isinstance(reason, str) or len(reason.strip()) < 8:
            issues.append(f"deferrals[{index}].reason must be a concrete reason")
    return modules


def count_value(data: dict[str, Any], *keys: str) -> int | None:
    candidates = [data.get(key) for key in keys]
    proof = data.get("proof")
    if isinstance(proof, dict):
        candidates.extend(proof.get(key) for key in keys)
    verified = data.get("verifiedCounts")
    if isinstance(verified, dict):
        candidates.extend(verified.get(key) for key in keys)
    for value in candidates:
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return value
    return None


def validate_structure_counts(data: dict[str, Any], modules: set[str], issues: list[str]) -> None:
    site_info_count = count_value(data, "siteInfoFieldCount", "siteInfoFields", "verifiedSiteInfoFieldCount")
    form_count = count_value(data, "formCount", "formsCount", "verifiedFormCount")
    media_count = count_value(data, "mediaCount", "uploadedMediaCount", "verifiedMediaCount")
    if data.get("siteInfoVerified") is True:
        if site_info_count is None:
            issues.append("siteInfoVerified=true requires siteInfoFieldCount, siteInfoFields, or verifiedSiteInfoFieldCount")
        elif site_info_count <= 0:
            issues.append("siteInfoVerified=true requires a positive site-info field count")
    elif site_info_count is not None and site_info_count > 0 and "site-info" not in modules:
        issues.append("positive site-info field count requires siteInfoVerified=true or module=site-info deferral context")
    if data.get("formsVerified") is True:
        if form_count is None:
            issues.append("formsVerified=true requires formCount, formsCount, or verifiedFormCount")
        elif form_count <= 0:
            issues.append("formsVerified=true requires a positive form count")
    elif form_count is not None and form_count > 0 and "forms" not in modules:
        issues.append("positive form count requires formsVerified=true or module=forms deferral context")
    if data.get("mediaVerified") is True:
        if media_count is None:
            issues.append("mediaVerified=true requires mediaCount, uploadedMediaCount, or verifiedMediaCount")
        elif media_count <= 0:
            issues.append("mediaVerified=true requires a positive media count")
    elif media_count is not None and media_count > 0 and "media" not in modules:
        issues.append("positive media count requires mediaVerified=true or module=media deferral context")


def validate_evidence(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_forms_media_settings_evidence":
        issues.append("kind must be allincms_forms_media_settings_evidence")
    if data.get("remoteMutationsPerformed") is True:
        issues.append("forms/media/settings evidence must not claim remote mutation was performed by the validator")
    status = data.get("status")
    if not isinstance(status, str) or not status.strip():
        issues.append("status is required")
    elif status not in SAFE_STATUSES:
        issues.append(f"status unsupported: {status}")

    modules = deferral_modules(data, issues)
    if status == "explicitly_out_of_scope":
        if not modules:
            issues.append("explicitly_out_of_scope requires at least one concrete deferral")
        validate_structure_counts(data, modules, issues)
        return issues + validate_redaction(data)

    for key, module in REQUIRED_FLAGS.items():
        value = data.get(key)
        if value is True:
            continue
        if module in modules:
            continue
        if value is not False and value is not None:
            issues.append(f"{key} must be true, false, or omitted")
        issues.append(f"{key} must be true or explicitly deferred with module={module}")

    proof = data.get("proof")
    if proof is not None and not isinstance(proof, dict):
        issues.append("proof must be an object when present")
    if status == "verified" and modules:
        issues.append("status verified must not include deferrals")
    if status == "verified":
        missing_true = [key for key in REQUIRED_FLAGS if data.get(key) is not True]
        if missing_true:
            issues.append("status verified requires all flags true: " + ", ".join(missing_true))

    validate_wiki_review(data, issues)
    validate_confirmation_decision_matrix(data, issues)
    validate_structure_counts(data, modules, issues)
    return issues + validate_redaction(data)


def build_report(evidence_path: str, evidence: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    return {
        "kind": "allincms_forms_media_settings_evidence_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "evidence": evidence_path,
        "siteKey": evidence.get("siteKey"),
        "status": evidence.get("status"),
        "launchPrerequisiteSatisfied": not issues,
        "verified": {key: evidence.get(key) is True for key in REQUIRED_FLAGS},
        "structureCounts": {
            "siteInfoFields": count_value(evidence, "siteInfoFieldCount", "siteInfoFields", "verifiedSiteInfoFieldCount"),
            "forms": count_value(evidence, "formCount", "formsCount", "verifiedFormCount"),
            "media": count_value(evidence, "mediaCount", "uploadedMediaCount", "verifiedMediaCount"),
        },
        "deferrals": evidence.get("deferrals") if isinstance(evidence.get("deferrals"), list) else [],
        "issues": issues,
        "adversarialChecks": [
            "This validation checks only redacted evidence; it does not save settings, create forms, upload media, add domains, or mutate tracking.",
            "Every false or omitted module flag must be backed by an explicit module deferral with a reason.",
            "A valid forms/media/settings evidence file unlocks launch-acceptance evaluation only; it does not prove final frontend QA or cleanup.",
            "Do not store cookies, authorization headers, server-action ids, router-state blobs, account emails, or raw private settings in this evidence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS forms/media/settings evidence.")
    parser.add_argument("evidence")
    parser.add_argument("--output", default="")
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    evidence = load_json(Path(args.evidence), "forms/media/settings evidence")
    issues = validate_evidence(evidence)
    report = build_report(args.evidence, evidence, issues)
    if args.output:
        write_json(Path(args.output), report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"valid={str(report['valid']).lower()} issues={len(issues)}")
    if args.fail_on_invalid and issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
