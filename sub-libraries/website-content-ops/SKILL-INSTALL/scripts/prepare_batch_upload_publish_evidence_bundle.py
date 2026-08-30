#!/usr/bin/env python3
"""Prepare a local evidence bundle for batch upload/publish browser execution."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

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


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("output directory must be outside the skill package")


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


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def evidence_template(runbook: dict[str, Any]) -> dict[str, Any]:
    template = runbook.get("redactedEvidenceTemplate")
    if not isinstance(template, dict):
        raise ValueError("runbook.redactedEvidenceTemplate must be an object")
    return dict(template)


def source_context(runbook: dict[str, Any]) -> dict[str, Any]:
    return {key: runbook.get(key) for key in SOURCE_CONTEXT_KEYS if key in runbook}


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


def validation_command(filled_path: Path, runbook: dict[str, Any], output_dir: Path) -> str:
    manifest = str(runbook.get("sourceManifest") or "").strip()
    base = str(runbook.get("sourceRunEvidence") or "").strip()
    audit = output_dir / "final-audit-report.redacted.json"
    command = (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_batch_upload_publish_evidence.py "
        f"{filled_path} --manifest {manifest} "
        f"--output {output_dir / 'batch-upload-publish-validation.json'}"
    )
    if base:
        command += f" --base-run-evidence {base}"
    command += f" --frontend-audit-report {audit}"
    return command


def final_audit_inputs_command(runbook: dict[str, Any], output_dir: Path) -> str:
    manifest = str(runbook.get("sourceManifest") or "").strip()
    progress = output_dir / "batch-progress-log.filled.json"
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/make_final_frontend_audit_inputs.py "
        f"--manifest {manifest} "
        f"--progress-log {progress} "
        "--require-schema-verified --require-progress-complete "
        "--static-paths /,/products,/posts "
        f"--urls-output {output_dir / 'final-audit-urls.txt'} "
        f"--statuses-output {output_dir / 'final-expected-statuses.json'} "
        f"--summary-output {output_dir / 'final-audit-inputs-summary.json'}"
    )


def frontend_audit_command(output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py "
        "--json --redact --timeout 8 --max-bytes 2000000 "
        f"--urls-file {output_dir / 'final-audit-urls.txt'} "
        f"> {output_dir / 'final-audit-report.redacted.json'}"
    )


def apply_command(filled_path: Path, runbook: dict[str, Any], output_dir: Path) -> str:
    manifest = str(runbook.get("sourceManifest") or "").strip()
    base = str(runbook.get("sourceRunEvidence") or "").strip()
    audit = output_dir / "final-audit-report.redacted.json"
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_batch_upload_publish.py "
        f"--batch-evidence {filled_path} "
        f"--manifest {manifest} "
        f"--base-run-evidence {base} "
        f"--frontend-audit-report {audit} "
        "--package <source-site-package.json> "
        "--confirmation <confirmation-record.json> "
        "--execution-plan <confirmed-site-execution-plan.json> "
        "--artifact-readiness <artifact-readiness.json> "
        "--created-site-binding <created-site-artifact-binding.json> "
        "--pages-site-info-handoff <pages-site-info-browser-handoff.json> "
        "--pages-site-info-validation <pages-site-info-execution-validation.json> "
        "--schema-capture-handoff <schema-capture-handoff.json> "
        "--upload-readiness <upload-readiness.json> "
        "--sample-evidence <manifest-sample-evidence.json> "
        f"--output-dir {output_dir / 'batch-upload-applied'}"
    )


def build_notes(runbook: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Batch Upload/Publish Evidence Bundle",
            "",
            "This bundle is local scaffolding only. It does not authorize browser actions.",
            "",
            "Before filling `batch-upload-publish-evidence.filled.json`:",
            "- create the action-time batch authorization record from current user text",
            "- run the batch pre-mutation gate with the same sample evidence used by the runbook",
            "- upload or update exactly one backend item per manifest slug",
            "- publish only the intended manifest items",
            "- write one progress row per manifest slug into `progressLog`",
            "- generate final frontend audit inputs from the schema-verified manifest and completed progress log",
            "- run a redacted frontend detail audit for every detail route",
            "- stop before cleanup, forms/media/settings, domains, tracking, routes, or unrelated content",
            "- do not store raw cookies, authorization headers, server-action IDs, router state, account emails, raw object IDs, or business copy",
            "",
            f"Content type: {runbook.get('contentType')}",
            f"Manifest item count: {runbook.get('manifestItemCount')}",
            f"Target: {runbook.get('target')}",
            "",
            "The filled evidence is complete only when validate_batch_upload_publish_evidence.py passes and apply_batch_upload_publish.py refreshes the source status.",
        ]
    ) + "\n"


def build_bundle(*, runbook: dict[str, Any], runbook_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if runbook.get("kind") != "allincms_batch_upload_publish_browser_runbook":
        raise ValueError("runbook kind must be allincms_batch_upload_publish_browser_runbook")
    if runbook.get("remoteMutationsPerformed") is not False:
        raise ValueError("runbook must be local-only/no remote mutation")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "batch-upload-publish-evidence.template.json"
    filled_path = output_dir / "batch-upload-publish-evidence.filled.json"
    progress_path = output_dir / "batch-progress-log.filled.json"
    notes_path = output_dir / "notes.md"
    validation_command_path = output_dir / "validation-command.txt"
    final_audit_inputs_command_path = output_dir / "final-audit-inputs-command.txt"
    frontend_audit_command_path = output_dir / "frontend-audit-command.txt"
    apply_command_path = output_dir / "apply-command.txt"
    template = evidence_template(runbook)
    write_json(template_path, template)
    write_json(filled_path, template)
    write_json(
        progress_path,
        {
            "kind": "allincms_batch_progress_log",
            "siteKey": runbook.get("siteKey"),
            "contentType": runbook.get("contentType"),
            "rows": template.get("progressLog", []),
        },
    )
    notes_path.write_text(build_notes(runbook), encoding="utf-8")
    validation_command_path.write_text(validation_command(filled_path, runbook, output_dir) + "\n", encoding="utf-8")
    final_audit_inputs_command_path.write_text(final_audit_inputs_command(runbook, output_dir) + "\n", encoding="utf-8")
    frontend_audit_command_path.write_text(frontend_audit_command(output_dir) + "\n", encoding="utf-8")
    apply_command_path.write_text(apply_command(filled_path, runbook, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_batch_upload_publish_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "runbook": runbook_path,
        "manifest": runbook.get("sourceManifest"),
        "sourceRunEvidence": runbook.get("sourceRunEvidence"),
        "sourceSampleEvidence": runbook.get("sourceSampleEvidence", ""),
        "siteKey": runbook.get("siteKey"),
        "contentType": runbook.get("contentType"),
        "manifestItemCount": runbook.get("manifestItemCount"),
        "target": runbook.get("target"),
        "evidenceTemplate": str(template_path),
        "filledEvidencePath": str(filled_path),
        "progressLogPath": str(progress_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "finalAuditInputsCommand": str(final_audit_inputs_command_path),
        "frontendAuditCommand": str(frontend_audit_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "schema-verified manifest gate pass",
            "validated manifest sample evidence",
            "action-time batch authorization",
            "matching batch pre-mutation gate pass",
            "one progress row per manifest slug",
            "redacted frontend detail audit for every uploaded route",
        ],
        "nextAction": "fill redacted batch evidence after browser actions, run final frontend audit, validate evidence, then run apply_batch_upload_publish.py",
    }
    bundle.update(source_context(runbook))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_batch_upload_publish_evidence_bundle":
        issues.append("kind must be allincms_batch_upload_publish_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in (
        "runbook",
        "manifest",
        "sourceRunEvidence",
        "siteKey",
        "contentType",
        "target",
        "evidenceTemplate",
        "filledEvidencePath",
        "progressLogPath",
        "notes",
        "validationCommand",
        "finalAuditInputsCommand",
        "frontendAuditCommand",
        "applyCommand",
    ):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    if not isinstance(bundle.get("manifestItemCount"), int):
        issues.append("manifestItemCount must be an integer")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "matching batch pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include matching batch pre-mutation gate pass")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local batch upload/publish evidence bundle.")
    parser.add_argument("--runbook", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            runbook=load_json(Path(args.runbook), "batch runbook"),
            runbook_path=args.runbook,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("batch evidence bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "evidence-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote batch upload/publish evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
