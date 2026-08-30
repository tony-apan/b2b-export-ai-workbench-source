#!/usr/bin/env python3
"""Prepare a local evidence bundle for one manifest sample upload."""

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


def validation_command(filled_path: Path, manifest_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_manifest_sample_upload_evidence.py "
        f"{filled_path} --manifest {manifest_path} "
        f"--output {output_dir / 'manifest-sample-validation.json'} "
        f"--progress-entry-output {output_dir / 'manifest-sample-progress-entry.json'}"
    )


def apply_command(filled_path: Path, manifest_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_manifest_sample_upload.py "
        f"--manifest {manifest_path} "
        f"--sample-evidence {filled_path} "
        "--package <source-site-package.json> "
        "--confirmation <confirmation-record.json> "
        "--execution-plan <confirmed-site-execution-plan.json> "
        "--artifact-readiness <artifact-readiness.json> "
        "--created-site-binding <created-site-artifact-binding.json> "
        "--pages-site-info-handoff <pages-site-info-browser-handoff.json> "
        "--pages-site-info-validation <pages-site-info-execution-validation.json> "
        "--schema-capture-handoff <schema-capture-handoff.json> "
        "--upload-readiness <upload-readiness.json> "
        f"--output-dir {output_dir / 'manifest-sample-applied'}"
    )


def build_notes(runbook: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Manifest Sample Evidence Bundle",
            "",
            "This bundle is local scaffolding only. It does not authorize browser actions.",
            "",
            "Before filling `manifest-sample-evidence.filled.json`:",
            "- run the schema-verified manifest gate",
            "- create the action-time authorization record from current user text",
            "- run the sample pre-mutation gate",
            "- upload or update only the selected sample slug",
            "- publish only that sample item",
            "- verify backend row, frontend detail route, body, title/name, and cover/media or accepted no-image note",
            "- stop before batch upload, cleanup, theme/routes/settings/forms/domains/tracking, or other manifest items",
            "- do not store raw cookies, authorization headers, server-action IDs, router state, account emails, or business copy",
            "",
            f"Content type: {runbook.get('contentType')}",
            f"Sample slug: {runbook.get('sampleSlug')}",
            f"Frontend URL: {runbook.get('frontendUrl')}",
            "",
            "The filled evidence is complete only when validate_manifest_sample_upload_evidence.py passes and the source status advances to batch_upload after apply.",
        ]
    ) + "\n"


def build_bundle(*, runbook: dict[str, Any], runbook_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if runbook.get("kind") != "allincms_manifest_sample_upload_runbook":
        raise ValueError("runbook kind must be allincms_manifest_sample_upload_runbook")
    if runbook.get("remoteMutationsPerformed") is not False:
        raise ValueError("runbook must be local-only/no remote mutation")
    manifest_path = str(runbook.get("manifest") or "").strip()
    if not manifest_path:
        raise ValueError("runbook.manifest is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "manifest-sample-evidence.template.json"
    filled_path = output_dir / "manifest-sample-evidence.filled.json"
    notes_path = output_dir / "notes.md"
    validation_command_path = output_dir / "validation-command.txt"
    apply_command_path = output_dir / "apply-command.txt"
    template = evidence_template(runbook)
    write_json(template_path, template)
    write_json(filled_path, template)
    notes_path.write_text(build_notes(runbook), encoding="utf-8")
    validation_command_path.write_text(validation_command(filled_path, manifest_path, output_dir) + "\n", encoding="utf-8")
    apply_command_path.write_text(apply_command(filled_path, manifest_path, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_manifest_sample_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "runbook": runbook_path,
        "sourceCurrentStage": "sample_upload",
        "manifest": manifest_path,
        "siteKey": runbook.get("siteKey"),
        "contentType": runbook.get("contentType"),
        "sampleSlug": runbook.get("sampleSlug"),
        "frontendUrl": runbook.get("frontendUrl"),
        "evidenceTemplate": str(template_path),
        "filledEvidencePath": str(filled_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "schema-verified manifest gate pass",
            "action-time authorization for the selected sample slug",
            "matching sample pre-mutation gate pass",
            "redacted backend and frontend proof for the selected sample only",
        ],
        "nextAction": "fill redacted sample evidence after browser actions, validate it, then run apply_manifest_sample_upload.py",
    }
    bundle.update(source_context(runbook))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_manifest_sample_evidence_bundle":
        issues.append("kind must be allincms_manifest_sample_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in (
        "runbook",
        "manifest",
        "siteKey",
        "contentType",
        "sampleSlug",
        "frontendUrl",
        "evidenceTemplate",
        "filledEvidencePath",
        "notes",
        "validationCommand",
        "applyCommand",
    ):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "matching sample pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include matching sample pre-mutation gate pass")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local manifest sample evidence bundle.")
    parser.add_argument("--runbook", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            runbook=load_json(Path(args.runbook), "manifest sample runbook"),
            runbook_path=args.runbook,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("manifest sample evidence bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "evidence-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote manifest sample evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
