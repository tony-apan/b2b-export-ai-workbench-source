#!/usr/bin/env python3
"""Build a local browser runbook for one confirmed create_site action."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from build_confirmed_create_site_handoff import AUTH_PLACEHOLDER, validate_handoff
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings


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


def build_runbook(
    *,
    handoff: dict[str, Any],
    handoff_path: str,
    authorization_record: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    handoff_issues = validate_handoff(handoff)
    if handoff_issues:
        raise ValueError("create-site handoff validation failed:\n- " + "\n- ".join(handoff_issues))
    site = handoff.get("siteProposal") if isinstance(handoff.get("siteProposal"), dict) else {}
    site_name = str(site.get("siteName", "")).strip()
    site_description = str(site.get("siteDescription", "")).strip()
    if not site_name or not site_description:
        raise ValueError("handoff.siteProposal.siteName and siteDescription are required")
    authorization_record = authorization_record or str(handoff.get("authorizationOutput", "")).strip()
    if not authorization_record:
        raise ValueError("authorization record path is required")
    created_site_evidence_output = str(handoff.get("createdSiteEvidenceOutput", "")).strip()
    if not created_site_evidence_output:
        raise ValueError("handoff.createdSiteEvidenceOutput is required")

    return {
        "kind": "allincms_create_site_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceCreateSiteHandoff": handoff_path,
        "sourcePackage": handoff.get("sourcePackage", ""),
        "sourcePackageSha256": handoff.get("sourcePackageSha256", ""),
        "sourceReviewPacket": handoff.get("sourceReviewPacket", ""),
        "sourceReviewPacketSha256": handoff.get("sourceReviewPacketSha256", ""),
        "confirmation": handoff.get("confirmation", ""),
        "executionPlan": handoff.get("executionPlan", ""),
        "preflight": handoff.get("preflight", ""),
        "authorizationRecord": authorization_record,
        "target": "https://workspace.laicms.com/sites",
        "action": "create_site",
        "siteProposal": {
            "siteName": site_name,
            "siteDescription": site_description,
            "language": str(site.get("language", "")).strip(),
            "industry": str(site.get("industry", "")).strip(),
        },
        "contentCounts": handoff.get("contentCounts", {}),
        "contentGoalCoverage": handoff.get("contentGoalCoverage", {}),
        "contentQualityReview": handoff.get("contentQualityReview", {}),
        "contentGoalOverages": handoff.get("contentGoalOverages", {}),
        "wikiReview": handoff.get("wikiReview", {}),
        "confirmationDecisionMatrix": handoff.get("confirmationDecisionMatrix", []),
        "existingSiteKeysBeforeCreate": handoff.get("existingSiteKeysBeforeCreate", []),
        "emptySiteListEvidence": handoff.get("emptySiteListEvidence", ""),
        "authorizationRequired": True,
        "authorizationRecordCommand": handoff.get("authorizationRecordCommand", ""),
        "authorizationRecordCommandHasPlaceholder": AUTH_PLACEHOLDER in str(handoff.get("authorizationRecordCommand", "")),
        "preMutationGateCommand": handoff.get("preMutationGateCommand", ""),
        "createdSiteEvidenceBrief": handoff.get("createdSiteEvidenceBrief", ""),
        "createdSiteEvidenceOutput": created_site_evidence_output,
        "mustRunBeforeBrowserSubmit": [
            "replace the authorizationRecordCommand placeholder with current user authorization text",
            "run make_authorization_record.py and require the authorization record to validate",
            "run preMutationGateCommand and require it to pass against the fresh create preflight",
            "re-open or re-check the create-site dialog still has name and description fields",
            "review contentQualityReview warnings and confirmationDecisionMatrix deferrals",
            "review contentGoalOverages so expanded source scope remains visible before submit",
            "confirm no content upload, theme edit, route bind, domain, tracking, or publish action is bundled",
        ],
        "browserStepsAfterGate": [
            {
                "step": "open_sites",
                "mode": "read_only_before_submit",
                "target": "https://workspace.laicms.com/sites",
                "verify": [
                    "same logged-in workspace session",
                    "existing site keys still match or are refreshed before gate if stale",
                    "create-site dialog can be opened",
                ],
            },
            {
                "step": "fill_create_site_dialog",
                "mode": "mutating_only_on_submit",
                "fields": [
                    {"name": "name", "value": site_name, "source": "confirmed source package"},
                    {"name": "description", "value": site_description, "source": "confirmed source package"},
                ],
                "verify": ["fields are scoped to the create-site dialog", "submit button is the dialog create control"],
            },
            {
                "step": "submit_create_site_once",
                "mode": "mutating_after_gate",
                "capture": [
                    "created site key",
                    "new site card or dashboard route",
                    "backend dashboard URL",
                    "frontend base URL",
                    "module routes visible after creation",
                    "whether default frontend renders, 404s, or is blank",
                ],
            },
            {
                "step": "write_created_site_evidence",
                "mode": "local_evidence_after_browser",
                "target": created_site_evidence_output,
                "verify": [
                    "new site key was absent from existingSiteKeysBeforeCreate or empty-list proof exists",
                    "backendVerified and frontendVerified are recorded",
                    "setup/module routes are recorded for the next stage",
                    "no content upload/publish/schema capture occurred in this authorization",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_created_site_browser_evidence",
            "sourceCreateSiteHandoff": handoff_path,
            "authorizationRecord": authorization_record,
            "preMutationGate": "passed|required_before_submit",
            "action": "create_site",
            "target": "https://workspace.laicms.com/sites",
            "siteName": site_name,
            "createdOnce": False,
            "createdSiteKey": "",
            "backendDashboardUrl": "",
            "frontendBaseUrl": "",
            "existingSiteKeysBeforeCreate": handoff.get("existingSiteKeysBeforeCreate", []),
            "newKeyAbsentBeforeCreate": False,
            "siteCardVerified": False,
            "backendVerified": False,
            "frontendVerified": False,
            "moduleRoutes": [],
            "frontendInitialState": "normal|404|blank|unknown",
            "forbiddenNeighborActionsVerified": False,
            "stopConditionMet": False,
            "blockingIssues": [],
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "uploading products/posts/media",
            "creating probes",
            "saving product/post/page/schema content",
            "publishing content or design",
            "editing themes, routes, forms, domains, tracking, or site settings",
            "deleting or cleaning anything",
            "continuing to schema capture before created-site evidence validates",
        ],
        "stopAfter": "created-site evidence is captured and written; next stage binds artifacts to the created/selected site",
        "warning": "Local preparation only. Browser steps remain locked until action-time create_site authorization and pre-mutation gate pass.",
    }


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_create_site_browser_runbook":
        issues.append("kind must be allincms_create_site_browser_runbook")
    for key in ("localOnly", "preparedOnly", "authorizationRequired"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("isUserAuthorization", "remoteMutationsPerformed", "browserStepsExecutable"):
        if runbook.get(key) is not False:
            issues.append(f"{key} must be false")
    if runbook.get("action") != "create_site":
        issues.append("action must be create_site")
    if runbook.get("target") != "https://workspace.laicms.com/sites":
        issues.append("target must be https://workspace.laicms.com/sites")
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = runbook.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            issues.append(f"{key} must be a lowercase sha256 hex digest")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or AUTH_PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must keep the user authorization placeholder")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action create_site" not in gate:
        issues.append("preMutationGateCommand must use --action create_site")
    site = runbook.get("siteProposal")
    if not isinstance(site, dict) or not site.get("siteName") or not site.get("siteDescription"):
        issues.append("siteProposal.siteName and siteDescription are required")
    elif "--expected-target-identifier" not in str(gate) or str(site.get("siteName")) not in str(gate):
        issues.append("preMutationGateCommand must bind the confirmed siteProposal.siteName")
    if not isinstance(runbook.get("contentGoalCoverage"), dict) or runbook["contentGoalCoverage"].get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    counts = runbook.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "navigationItems", "siteInfoFields"):
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
    quality = runbook.get("contentQualityReview")
    if not isinstance(quality, dict) or "warnings" not in quality:
        issues.append("contentQualityReview with warnings is required")
    overages = runbook.get("contentGoalOverages")
    validate_content_goal_overages(overages, issues)
    validate_content_goal_overages_for_warnings(overages, quality, issues)
    wiki = runbook.get("wikiReview")
    if not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex"):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required")
    matrix = runbook.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix is required")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include open, fill, submit, and evidence steps")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("createdOnce") is not False:
        issues.append("redactedEvidenceTemplate must start with createdOnce=false")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or "uploading products/posts/media" not in forbidden:
        issues.append("forbiddenActions must block content/media upload")
    return issues


def build_validation_report(runbook: dict[str, Any], runbook_path: str = "") -> dict[str, Any]:
    issues = validate_runbook(runbook)
    return {
        "kind": "allincms_create_site_browser_runbook_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "runbook": runbook_path,
        "preparedOnly": runbook.get("preparedOnly"),
        "browserStepsExecutable": runbook.get("browserStepsExecutable"),
        "remoteMutationsPerformed": runbook.get("remoteMutationsPerformed"),
        "isUserAuthorization": runbook.get("isUserAuthorization"),
        "action": runbook.get("action"),
        "target": runbook.get("target"),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a browser runbook for one confirmed create_site action.")
    parser.add_argument("--create-site-handoff", required=True)
    parser.add_argument("--authorization-record", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.create_site_handoff), "create-site handoff")
        runbook = build_runbook(
            handoff=handoff,
            handoff_path=args.create_site_handoff,
            authorization_record=args.authorization_record,
        )
        issues = validate_runbook(runbook)
        if issues:
            raise ValueError("generated create-site runbook failed validation:\n- " + "\n- ".join(issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote create-site browser runbook: {output}")
    print("browserStepsExecutable=false")
    if args.json:
        print(json.dumps(runbook, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
