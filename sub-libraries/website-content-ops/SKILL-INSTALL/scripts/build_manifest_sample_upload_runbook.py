#!/usr/bin/env python3
"""Build a local runbook for uploading one schema-verified manifest sample item."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from prepare_probe_save_handoff import PLACEHOLDER
from validate_manifest import load_manifest, validate_manifest
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings


ROUTE_PREFIX = {"products": "products", "posts": "posts"}
SOURCE_CONTEXT_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
    "createdSiteSubmittedValues",
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "contentGoalOverages",
    "wikiReview",
    "confirmationDecisionMatrix",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def manifest_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def choose_sample_item(manifest: dict[str, Any], sample_slug: str = "") -> dict[str, Any]:
    items = manifest_items(manifest)
    if not items:
        raise ValueError("manifest.items must contain at least one item")
    if sample_slug:
        for item in items:
            if item.get("slug") == sample_slug:
                return item
        raise ValueError(f"sample slug not found in manifest: {sample_slug}")
    return items[0]


def item_title(item: dict[str, Any]) -> str:
    value = item.get("name") or item.get("title")
    return value if isinstance(value, str) and value.strip() else str(item.get("slug", "sample"))


def detail_url(frontend_base: str, content_type: str, slug: str) -> str:
    return f"{frontend_base.rstrip('/')}/{ROUTE_PREFIX[content_type]}/{slug}"


def source_context(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: manifest.get(key) for key in SOURCE_CONTEXT_KEYS if key in manifest}


def source_context_issues(data: dict[str, Any]) -> list[str]:
    if not any(key in data for key in SOURCE_CONTEXT_KEYS):
        return []
    issues: list[str] = []
    if any(key in data for key in ("sourcePackageSha256", "sourceReviewPacketSha256")):
        for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
            value = data.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                issues.append(f"{key} must be a lowercase 64-character sha256 when source identity is present")
    submitted = data.get("createdSiteSubmittedValues")
    if submitted is not None:
        if not isinstance(submitted, dict):
            issues.append("createdSiteSubmittedValues must be an object when present")
        else:
            for key in ("name", "description"):
                value = submitted.get(key)
                if not isinstance(value, str) or not value.strip():
                    issues.append(f"createdSiteSubmittedValues.{key} must be a non-empty string when present")
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true when source context is present")
    counts = data.get("contentCounts")
    if counts is not None:
        if not isinstance(counts, dict):
            issues.append("contentCounts must be an object when present")
        else:
            for key in ("pages", "products", "posts"):
                value = counts.get(key)
                if not isinstance(value, int) or value < 0:
                    issues.append(f"contentCounts.{key} must be a non-negative integer when present")
    quality = data.get("contentQualityReview")
    if not isinstance(quality, dict) or "warnings" not in quality:
        issues.append("contentQualityReview with warnings is required when source context is present")
    overages = data.get("contentGoalOverages")
    if overages is not None:
        validate_content_goal_overages(overages, issues)
    validate_content_goal_overages_for_warnings(overages, quality, issues)
    wiki = data.get("wikiReview")
    if not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex"):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required when source context is present")
    matrix = data.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix is required when source context is present")
    return issues


def build_runbook(
    *,
    manifest: dict[str, Any],
    manifest_path: str,
    target: str,
    authorization_output: str,
    sample_slug: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    manifest_errors = validate_manifest(manifest, require_schema_verified=True)
    if manifest_errors:
        raise ValueError("manifest must be schema-verified before sample upload:\n- " + "\n- ".join(manifest_errors))
    content_type = str(manifest.get("contentType"))
    if content_type not in ROUTE_PREFIX:
        raise ValueError("contentType must be posts or products")
    site_key = str(manifest.get("siteKey", "")).strip()
    if not site_key or site_key.startswith("{"):
        raise ValueError("manifest.siteKey must be concrete before sample upload")
    frontend_base = str(manifest.get("frontendBaseUrl", "")).strip().rstrip("/")
    if not frontend_base:
        raise ValueError("manifest.frontendBaseUrl is required")
    expected_target = f"https://workspace.laicms.com/{site_key}/{content_type}"
    if not target.startswith(expected_target):
        raise ValueError(f"target must be under {expected_target}")

    sample = choose_sample_item(manifest, sample_slug)
    slug = str(sample["slug"])
    title = item_title(sample)
    frontend_url = detail_url(frontend_base, content_type, slug)
    fields = "schemaGatePass,sampleSlug,saveStatus,publishStatus,backendVerified,frontendVerified,bodyVerified,coverOrMediaVerified"
    expected = f"{content_type} manifest sample {slug} uploaded, published, and frontend detail verified"
    verification = "create or update one manifest item, publish it, verify backend row and frontend detail DOM"
    cleanup = "stop after sample proof; cleanup or batch upload requires separate authorization"
    authorization_text = (
        f"授权 Codex 在 {target} 仅上传/更新并发布 schema-verified {content_type} manifest 的 1 条样例 `{slug}`，"
        "记录后台状态和前台详情页审计；本次不批量上传、不删除、不修改主题/路由/设置。"
    )
    runbook = {
        "kind": "allincms_manifest_sample_upload_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "manifest": manifest_path,
        "siteKey": site_key,
        "contentType": content_type,
        "target": target,
        "sampleSlug": slug,
        "sampleTitleOrName": title,
        "frontendUrl": frontend_url,
        "action": "manifest_sample_upload",
        "authorizationRequired": True,
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": (
            "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
            "--action batch_upload "
            f"--site-key {site_key} "
            f"--target {target} "
            f"--target-type {content_type} "
            f"--target-identifier 'manifest sample {slug}' "
            f"--fields-or-files {fields} "
            f"--expected-result '{expected}' "
            f"--verification-plan '{verification}' "
            f"--cleanup-plan '{cleanup}' "
            f"--authorization-source '{PLACEHOLDER}' "
            f"--output {authorization_output}"
        ),
        "authorizationRecordCommandHasPlaceholder": True,
        "preMutationGateCommand": (
            "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
            "--action batch_upload "
            f"--preflight ~/allincms-projects/current-run-evidence-after-save-capture.json "
            f"--authorization {authorization_output}"
        ),
        "mustRunBeforeBrowserSample": [
            "validate_manifest.py --require-schema-verified on manifest",
            "generate action-time authorization record from current user text",
            "run the batch_upload pre-mutation gate with current run evidence and authorization",
            "confirm target list/edit route belongs to manifest.siteKey and manifest.contentType",
            "prepare one evidence JSON from the redactedEvidenceTemplate",
        ],
        "browserStepsAfterGate": [
            {
                "step": "create_or_update_sample_item",
                "mode": "mutating_after_gate",
                "sampleSlug": slug,
                "verify": [
                    "only the selected sample slug is created or updated",
                    "saveStatus is ok",
                    "captured backend URL belongs to the same site/content type",
                    "do not process remaining manifest items",
                ],
            },
            {
                "step": "publish_sample_item",
                "mode": "mutating_after_gate",
                "verify": ["publishStatus is ok", "backend status is published", "slug remains unchanged"],
            },
            {
                "step": "verify_frontend_detail",
                "mode": "read_only_after_mutation",
                "target": frontend_url,
                "verify": [
                    "HTTP 200",
                    "title/name visible",
                    "body visible with no raw Markdown residue",
                    "cover/media visible or explicit no-image note",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_manifest_sample_upload_evidence",
            "siteKey": site_key,
            "contentType": content_type,
            "manifestPath": manifest_path,
            "sampleSlug": slug,
            "target": target,
            "backendUrl": "",
            "frontendUrl": frontend_url,
            "authorizationRecord": authorization_output,
            "preMutationGate": "passed|required_before_sample",
            "schemaGatePass": False,
            "saveStatus": "",
            "publishStatus": "",
            "backendVerified": False,
            "frontendVerified": False,
            "titleOrNameVerified": False,
            "bodyVerified": False,
            "coverOrMediaVerified": False,
            "coverOrMediaNote": "",
            "renderAudit": "",
            "blockingIssues": [],
            "stopConditionMet": False,
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "uploading or publishing any manifest item other than sampleSlug",
            "deleting or cleaning probes/test items",
            "mutating themes, routes, forms, domains, tracking, or site settings",
            "changing schema/payloadTemplate during sample upload",
            "starting batch upload before sample evidence validates",
        ],
        "stopAfter": "one manifest sample has backend and frontend proof; do not continue to batch",
        "warning": "Local preparation only. The browser steps remain locked until action-time authorization and pre-mutation gate pass.",
    }
    context = source_context(manifest)
    runbook.update(context)
    runbook["redactedEvidenceTemplate"].update(context)
    return runbook


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_manifest_sample_upload_runbook":
        issues.append("kind must be allincms_manifest_sample_upload_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "manifest_sample_upload":
        issues.append("action must be manifest_sample_upload")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must keep the authorization placeholder")
    if runbook.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must be false until authorization and gate pass")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 3:
        issues.append("browserStepsAfterGate must include save/update, publish, and frontend verification")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("schemaGatePass") is not False:
        issues.append("redactedEvidenceTemplate must start incomplete")
    forbidden = runbook.get("forbiddenActions")
    if not isinstance(forbidden, list) or not any("other than sampleSlug" in str(item) for item in forbidden):
        issues.append("forbiddenActions must restrict operation to sampleSlug")
    issues.extend(source_context_issues(runbook))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local runbook for one AllinCMS manifest sample upload.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target", required=True, help="Concrete backend list/edit URL prefix for the content type")
    parser.add_argument("--sample-slug", default="")
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        manifest = load_manifest(Path(args.manifest))
        runbook = build_runbook(
            manifest=manifest,
            manifest_path=args.manifest,
            target=args.target,
            sample_slug=args.sample_slug,
            authorization_output=args.authorization_output,
        )
        issues = validate_runbook(runbook)
        if issues:
            raise ValueError("generated runbook failed validation:\n- " + "\n- ".join(issues))
    except (SystemExit, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest sample upload runbook: {output}")
    print("browserStepsExecutable=false")
    if args.json:
        print(json.dumps(runbook, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
