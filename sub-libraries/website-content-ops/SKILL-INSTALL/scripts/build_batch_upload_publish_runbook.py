#!/usr/bin/env python3
"""Build a local browser runbook for one AllinCMS batch upload/publish stage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from prepare_probe_save_handoff import PLACEHOLDER
from validate_batch_upload_publish_evidence import base_site_key_and_content_type
from validate_manifest import load_manifest, validate_manifest
from validate_manifest_sample_upload_evidence import validate_sample_evidence
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings


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


def manifest_item_count(manifest: dict[str, Any]) -> int:
    items = manifest.get("items")
    return len(items) if isinstance(items, list) else 0


def validate_base_for_batch(base: dict[str, Any], manifest: dict[str, Any], sample_evidence: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    request_capture = base.get("requestCapture")
    if not isinstance(request_capture, dict) or request_capture.get("persistedVerified") is not True:
        issues.append("base evidence must contain persisted requestCapture")
    if sample_evidence is not None:
        sample_issues = validate_sample_evidence(sample_evidence, manifest)
        issues.extend(f"sampleEvidence: {issue}" for issue in sample_issues)
        return issues
    sample = base.get("sampleVerification")
    if not isinstance(sample, dict):
        issues.append("base evidence must contain sampleVerification or pass --sample-evidence")
    else:
        for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "coverOrMediaVerified", "bodyVerified"):
            if sample.get(key) is not True:
                issues.append(f"sampleVerification.{key} must be true")
    return issues


def validate_target(target: str, site_key: str, content_type: str) -> None:
    parsed = urlparse(target)
    expected_path = f"/{site_key}/{content_type}"
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com" or not parsed.path.startswith(expected_path):
        raise ValueError(f"target must be under https://workspace.laicms.com{expected_path}")


def source_context_from_artifacts(*artifacts: dict[str, Any] | None) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for key in SOURCE_CONTEXT_KEYS:
        values = [artifact[key] for artifact in artifacts if isinstance(artifact, dict) and key in artifact]
        if not values:
            continue
        first = values[0]
        if any(value != first for value in values[1:]):
            raise ValueError(f"{key} mismatch between batch source-context artifacts")
        context[key] = first
    return context


def source_context_issues(data: dict[str, Any]) -> list[str]:
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
    if coverage is not None and (not isinstance(coverage, dict) or coverage.get("complete") is not True):
        issues.append("contentGoalCoverage.complete must be true when present")
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
    if quality is not None and (not isinstance(quality, dict) or "warnings" not in quality):
        issues.append("contentQualityReview with warnings is required when present")
    overages = data.get("contentGoalOverages")
    if overages is not None:
        validate_content_goal_overages(overages, issues)
    validate_content_goal_overages_for_warnings(overages, quality, issues)
    wiki = data.get("wikiReview")
    if wiki is not None and (not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex")):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required when present")
    matrix = data.get("confirmationDecisionMatrix")
    if matrix is not None and (not isinstance(matrix, list) or not matrix):
        issues.append("confirmationDecisionMatrix is required when present")
    return issues


def build_runbook(
    *,
    run_evidence: dict[str, Any],
    run_evidence_path: str,
    manifest: dict[str, Any],
    manifest_path: str,
    authorization_output: str,
    target: str,
    target_identifier: str,
    sample_evidence: dict[str, Any] | None = None,
    sample_evidence_path: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    base_site_key, base_content_type = base_site_key_and_content_type(run_evidence)
    manifest_errors = validate_manifest(manifest, require_schema_verified=True)
    if manifest_errors:
        raise ValueError("manifest is not ready for batch upload:\n" + "\n".join(f"- {error}" for error in manifest_errors))
    if manifest.get("siteKey") != base_site_key:
        raise ValueError("manifest.siteKey must match run evidence siteKey")
    if manifest.get("contentType") != base_content_type:
        raise ValueError("manifest.contentType must match run evidence contentType")
    base_issues = validate_base_for_batch(run_evidence, manifest, sample_evidence)
    if base_issues:
        raise ValueError("run evidence is not ready for batch upload:\n" + "\n".join(f"- {issue}" for issue in base_issues))
    validate_target(target, base_site_key, base_content_type)

    fields = "schemaGatePass,sampleVerification,progressLog,frontendDetailAudit"
    expected = f"{base_content_type} manifest batch uploaded/published and frontend detail routes audited"
    verification = "verify schema gate, sample proof, progress log, duplicate slugs, and frontend detail routes"
    cleanup = "stop after batch proof; rollback or cleanup requires separate authorization"
    authorization_text = (
        f"授权 Codex 在 {target} 对当前 schema-verified {base_content_type} manifest 执行批量上传/发布，"
        "并逐条记录 progress log、后台状态和前台详情页审计；本次不删除、不清理 probe、不修改站点设置。"
    )
    authorization_record_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action batch_upload "
        f"--site-key {base_site_key} "
        f"--target {target} "
        f"--target-type {base_content_type} "
        f"--target-identifier '{target_identifier}' "
        f"--fields-or-files {fields} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{PLACEHOLDER}' "
        f"--output {authorization_output}"
    )
    pre_mutation_gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action batch_upload "
        f"--preflight {run_evidence_path} "
        f"--authorization {authorization_output}"
    )
    if sample_evidence_path:
        pre_mutation_gate_command += f" --sample-evidence {sample_evidence_path}"
    frontend_base = str(manifest.get("frontendBaseUrl", "")).rstrip("/")
    source_context = source_context_from_artifacts(run_evidence, manifest, sample_evidence)
    runbook = {
        "kind": "allincms_batch_upload_publish_browser_runbook",
        "generatedAt": generated_at or now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceRunEvidence": run_evidence_path,
        "sourceManifest": manifest_path,
        "sourceSampleEvidence": sample_evidence_path,
        "siteKey": base_site_key,
        "contentType": base_content_type,
        "target": target,
        "targetIdentifier": target_identifier,
        "manifestItemCount": manifest_item_count(manifest),
        "frontendBaseUrl": frontend_base,
        "action": "batch_upload",
        "authorizationRequired": True,
        "suggestedAuthorizationText": authorization_text,
        "authorizationRecordCommand": authorization_record_command,
        "authorizationRecordCommandHasPlaceholder": PLACEHOLDER in authorization_record_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "mustRunBeforeBrowserBatch": [
            "generate authorization record from current user instruction or action-time authorization",
            "run preMutationGateCommand and require it to pass",
            "run validate_manifest.py --require-schema-verified on sourceManifest",
            "confirm sampleEvidence or sampleVerification and requestCapture are from the same site/content type",
            "prepare a progress log file with one row per manifest slug",
        ],
        "browserStepsAfterGate": [
            {
                "step": "iterate_manifest_items",
                "mode": "mutating_after_gate",
                "verify": [
                    "create or update exactly one backend item per manifest slug",
                    "saveStatus is ok for each item",
                    "record backend URL/id as redacted runtime evidence, not in the skill package",
                ],
            },
            {
                "step": "publish_each_item",
                "mode": "mutating_after_gate",
                "verify": [
                    "publishStatus is ok for each item that should be public",
                    "do not publish unrelated drafts",
                    "record failures and stop or skip according to the progress log policy",
                ],
            },
            {
                "step": "backend_progress_verification",
                "mode": "read_only_after_mutation",
                "verify": [
                    "each slug appears once in backend progress log",
                    "backendVerified, coverOrMediaVerified, and bodyVerified are true for each item",
                    "duplicate slugs are absent or resolved explicitly",
                ],
            },
            {
                "step": "frontend_detail_audit",
                "mode": "read_only_after_mutation",
                "verify": [
                    "generate final audit inputs from the schema-verified manifest and complete progress log",
                    "run audit_frontend_rendering.py --json --redact over every detail URL",
                    "validate batch evidence with validate_batch_upload_publish_evidence.py before unlocking later stages",
                ],
            },
        ],
        "redactedEvidenceTemplate": {
            "kind": "allincms_batch_upload_publish_evidence",
            "siteKey": base_site_key,
            "contentType": base_content_type,
            "target": target,
            "manifestPath": manifest_path,
            "authorizationRecord": authorization_output,
            "preMutationGate": "passed|required_before_batch",
            "action": "batch_upload",
            "schemaGatePass": False,
            "sampleVerificationPass": False,
            "progressLogComplete": False,
            "frontendDetailAuditPass": False,
            "progressLog": [],
            "frontendDetailAudit": {
                "checked": False,
                "detailRouteCount": manifest_item_count(manifest),
                "markdownResidueChecked": False,
                "structuredRichTextChecked": False,
                "blockingIssues": [],
            },
            "stopConditionMet": False,
        },
        "browserStepsExecutable": False,
        "forbiddenActions": [
            "deleting or cleaning probe/test items",
            "mutating themes, routes, forms, domains, tracking, or site settings",
            "uploading media outside manifest needs",
            "changing posts/products schemas without a new save request capture",
            "treating HTTP 200 as proof without DOM/rich-text/image audit",
        ],
        "stopAfter": "batch progress log and frontend detail audit are complete; do not cleanup or change settings",
        "warning": (
            "This runbook is local preparation only. Do not execute browserStepsAfterGate until the "
            "batch_upload authorization record exists and the pre-mutation gate passes."
        ),
    }
    runbook.update(source_context)
    runbook["redactedEvidenceTemplate"].update(source_context)
    return runbook


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if runbook.get("kind") != "allincms_batch_upload_publish_browser_runbook":
        issues.append("kind must be allincms_batch_upload_publish_browser_runbook")
    for key in ("localOnly", "preparedOnly"):
        if runbook.get(key) is not True:
            issues.append(f"{key} must be true")
    if runbook.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if runbook.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if runbook.get("action") != "batch_upload":
        issues.append("action must be batch_upload")
    command = runbook.get("authorizationRecordCommand")
    if not isinstance(command, str) or PLACEHOLDER not in command:
        issues.append("authorizationRecordCommand must retain the current-user authorization placeholder")
    if runbook.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommandHasPlaceholder must be true")
    gate = runbook.get("preMutationGateCommand")
    if not isinstance(gate, str) or "--action batch_upload" not in gate:
        issues.append("preMutationGateCommand must run the batch_upload gate")
    if runbook.get("browserStepsExecutable") is not False:
        issues.append("browserStepsExecutable must start false until authorization and gate pass")
    steps = runbook.get("browserStepsAfterGate")
    if not isinstance(steps, list) or len(steps) < 4:
        issues.append("browserStepsAfterGate must include upload, publish, backend verify, and frontend audit steps")
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict) or template.get("progressLogComplete") is not False:
        issues.append("redactedEvidenceTemplate must start incomplete")
    issues.extend(source_context_issues(runbook))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local AllinCMS batch upload/publish runbook.")
    parser.add_argument("--run-evidence", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sample-evidence", default="", help="Optional allincms_manifest_sample_upload_evidence JSON")
    parser.add_argument("--target", required=True, help="Concrete backend content list URL")
    parser.add_argument("--target-identifier", default="posts/products manifest batch")
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        run_evidence = load_json(Path(args.run_evidence), "run evidence")
        manifest = load_manifest(Path(args.manifest))
        sample_evidence = load_json(Path(args.sample_evidence), "sample evidence") if args.sample_evidence else None
        runbook = build_runbook(
            run_evidence=run_evidence,
            run_evidence_path=args.run_evidence,
            manifest=manifest,
            manifest_path=args.manifest,
            sample_evidence=sample_evidence,
            sample_evidence_path=args.sample_evidence,
            authorization_output=args.authorization_output,
            target=args.target,
            target_identifier=args.target_identifier,
        )
        issues = validate_runbook(runbook)
        if issues:
            raise ValueError("generated runbook failed validation:\n" + "\n".join(f"- {issue}" for issue in issues))
    except (ValueError, SystemExit) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print("browserStepsExecutable=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
