#!/usr/bin/env python3
"""Prepare a local evidence bundle for forms/media/settings browser proof."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


SOURCE_CONTEXT_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "wikiReview",
    "confirmationDecisionMatrix",
)

REQUIRED_CONTENT_COUNT_KEYS = ("pages", "products", "posts")
EXTENDED_CONTENT_COUNT_KEYS = ("forms", "media", "navigationItems", "siteInfoFields")


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


def source_context(status: dict[str, Any]) -> dict[str, Any]:
    context = {key: status.get(key) for key in SOURCE_CONTEXT_KEYS if key in status}
    if "contentCounts" not in context:
        quality = status.get("contentQualityReview")
        if isinstance(quality, dict) and isinstance(quality.get("contentCounts"), dict):
            context["contentCounts"] = quality["contentCounts"]
        else:
            coverage = status.get("contentGoalCoverage")
            if isinstance(coverage, dict) and isinstance(coverage.get("counts"), dict):
                context["contentCounts"] = coverage["counts"]
    return context


def source_context_issues(data: dict[str, Any]) -> list[str]:
    if not any(key in data for key in SOURCE_CONTEXT_KEYS):
        return []
    issues: list[str] = []
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = data.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            issues.append(f"{key} must be a lowercase 64-character sha256 when source context is present")
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true when source context is present")
    quality = data.get("contentQualityReview")
    if not isinstance(quality, dict) or "warnings" not in quality:
        issues.append("contentQualityReview with warnings is required when source context is present")
    wiki = data.get("wikiReview")
    if not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex"):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required when source context is present")
    matrix = data.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix is required when source context is present")
    counts = data.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts is required when source context is present")
    else:
        for key in REQUIRED_CONTENT_COUNT_KEYS:
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
        for key in EXTENDED_CONTENT_COUNT_KEYS:
            if key in counts:
                value = counts.get(key)
                if not isinstance(value, int) or value < 0:
                    issues.append(f"contentCounts.{key} must be a non-negative integer")
    return issues


def site_key(status: dict[str, Any]) -> str:
    value = str(status.get("siteKey") or "").strip()
    if value:
        return value
    artifacts = status.get("artifacts")
    if isinstance(artifacts, dict):
        value = str(artifacts.get("siteKey") or "").strip()
        if value:
            return value
    stages = status.get("stages")
    if isinstance(stages, dict):
        for key in ("created_site_binding", "pages_site_info_execution", "batch_upload"):
            stage = stages.get(key)
            if isinstance(stage, dict):
                value = str(stage.get("siteKey") or "").strip()
                if value:
                    return value
    return ""


def evidence_template(status: dict[str, Any], status_path: str) -> dict[str, Any]:
    resolved_site_key = site_key(status)
    template = {
        "kind": "allincms_forms_media_settings_evidence",
        "sourceExecutionStatus": status_path,
        "siteKey": resolved_site_key,
        "remoteMutationsPerformed": False,
        "status": "verified|partially_verified_with_explicit_deferrals|explicitly_out_of_scope",
        "siteInfoVerified": False,
        "formsVerified": False,
        "mediaVerified": False,
        "domainsRecorded": False,
        "trackingRecorded": False,
        "siteInfoFieldCount": 0,
        "formCount": 0,
        "mediaCount": 0,
        "verifiedCounts": {
            "siteInfoFieldCount": 0,
            "formCount": 0,
            "mediaCount": 0,
        },
        "deferrals": [
            {
                "module": "forms|media|domains|tracking|site-info",
                "reason": "replace with explicit user-approved reason when a module is not verified",
            }
        ],
        "proof": {
            "siteInfo": "redacted backend/front-end proof or explicit deferral",
            "forms": "redacted form proof or explicit deferral",
            "media": "redacted media proof or explicit deferral",
            "domains": "redacted domain/status proof or explicit deferral",
            "tracking": "redacted tracking proof or explicit deferral",
        },
    }
    template.update(source_context(status))
    return template


def validation_command(filled_path: Path, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_forms_media_settings_evidence.py "
        f"{filled_path} --output {output_dir / 'forms-media-settings-validation.json'}"
    )


def apply_command(filled_path: Path, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_forms_media_settings.py "
        f"--forms-media-settings-evidence {filled_path} "
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
        "--batch-validation <batch-upload-publish-validation.json> "
        f"--output-dir {output_dir / 'forms-media-settings-applied'}"
    )


def build_notes(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Forms/Media/Settings Evidence Bundle",
            "",
            "This bundle is local scaffolding only. It does not authorize browser actions.",
            "",
            "Before filling `forms-media-settings-evidence.filled.json`:",
            "- verify site-info, forms, media, domains, and tracking in the current site, or record explicit deferrals",
            "- when site info is verified, fill siteInfoFieldCount with the number of confirmed site-info fields proven in backend or frontend evidence",
            "- when forms or media are verified, fill formCount/mediaCount with the number proven in backend or public DOM evidence",
            "- keep every browser mutation bound to one action-time authorization and matching pre-mutation gate",
            "- include only redacted backend/frontend proof, not raw request headers, cookies, server-action ids, account emails, or business copy",
            "- stop before launch acceptance, cleanup, unrelated content upload, or domain DNS changes outside the confirmed scope",
            "- keep contentCounts, wikiReview, and confirmationDecisionMatrix identical to the confirmed source context when present",
            "",
            f"Current source stage: {status.get('currentStage')}",
            f"Site key: {site_key(status)}",
            "",
            "The filled evidence is complete only when validate_forms_media_settings_evidence.py passes and apply_forms_media_settings.py refreshes the source status.",
        ]
    ) + "\n"


def build_bundle(*, status: dict[str, Any], status_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if status.get("kind") != "allincms_source_execution_status":
        raise ValueError("status kind must be allincms_source_execution_status")
    if status.get("remoteMutationsPerformed") is not False:
        raise ValueError("status must be local-only/no remote mutation")
    if status.get("currentStage") != "forms_media_settings":
        raise ValueError("status.currentStage must be forms_media_settings")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "forms-media-settings-evidence.template.json"
    filled_path = output_dir / "forms-media-settings-evidence.filled.json"
    notes_path = output_dir / "notes.md"
    validation_command_path = output_dir / "validation-command.txt"
    apply_command_path = output_dir / "apply-command.txt"
    template = evidence_template(status, status_path)
    write_json(template_path, template)
    write_json(filled_path, template)
    notes_path.write_text(build_notes(status), encoding="utf-8")
    validation_command_path.write_text(validation_command(filled_path, output_dir) + "\n", encoding="utf-8")
    apply_command_path.write_text(apply_command(filled_path, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_forms_media_settings_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "sourceExecutionStatus": status_path,
        "sourceStatusCurrentStage": status.get("currentStage", ""),
        "siteKey": site_key(status),
        "evidenceTemplate": str(template_path),
        "filledEvidencePath": str(filled_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "current site forms/media/settings browser proof",
            "action-time authorization for any save/create/upload/add action",
            "matching pre-mutation gate pass for every mutation",
            "explicit deferral for every unverified module",
            "redacted proof with no raw credentials or request secrets",
        ],
        "nextAction": "fill redacted forms/media/settings evidence after browser proof, validate it, then run apply_forms_media_settings.py",
    }
    bundle.update(source_context(status))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_forms_media_settings_evidence_bundle":
        issues.append("kind must be allincms_forms_media_settings_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in ("sourceExecutionStatus", "evidenceTemplate", "filledEvidencePath", "notes", "validationCommand", "applyCommand"):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "explicit deferral for every unverified module" not in required:
        issues.append("requiredBeforeUse must include explicit deferral for every unverified module")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local forms/media/settings evidence bundle.")
    parser.add_argument("--status", required=True, help="allincms_source_execution_status JSON at forms_media_settings")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            status=load_json(Path(args.status), "source execution status"),
            status_path=args.status,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("forms/media/settings evidence bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "evidence-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote forms/media/settings evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
