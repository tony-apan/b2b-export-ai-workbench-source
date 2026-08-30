#!/usr/bin/env python3
"""Prepare a local input bundle for launch acceptance apply."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from content_goal_coverage_utils import created_site_submitted_values_issues
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings


SOURCE_CONTEXT_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "contentGoalOverages",
    "wikiReview",
    "confirmationDecisionMatrix",
    "createdSiteSubmittedValues",
)

REQUIRED_CONTENT_COUNT_KEYS = ("pages", "products", "posts")
EXTENDED_CONTENT_COUNT_KEYS = ("forms", "media", "navigationItems", "siteInfoFields")
REQUIRED_PATH_FIELDS = (
    "runEvidence",
    "finalFrontendAudit",
    "cleanupEvidence",
    "formsMediaSettings",
    "package",
    "confirmation",
    "executionPlan",
    "artifactReadiness",
    "createdSiteBinding",
)
OPTIONAL_PATH_FIELDS = (
    "moduleCoverage",
    "stageCoverage",
    "roundCloseout",
    "reviewPacket",
    "pagesSiteInfoHandoff",
    "pagesSiteInfoValidation",
    "taxonomyHandoff",
    "taxonomyValidation",
    "schemaCaptureHandoff",
)
PATH_LIST_FIELDS = ("uploadReadiness", "sampleEvidence", "batchValidation")


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


def is_placeholder_path(value: str) -> bool:
    normalized = value.strip()
    lowered = normalized.lower()
    return (
        normalized.startswith("<")
        or normalized.endswith(">")
        or "<from " in lowered
        or "replace with" in lowered
        or "{real" in normalized
        or "{site" in normalized
        or "{theme" in normalized
        or "{page" in normalized
        or "{content" in normalized
    )


def validate_path_value(inputs: dict[str, Any], key: str, *, required: bool, issues: list[str]) -> None:
    value = inputs.get(key)
    if value in (None, "") and not required:
        return
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} is required" if required else f"{key} must be a path string when present")
        return
    if is_placeholder_path(value):
        issues.append(f"{key} must be a concrete path, not a placeholder")


def validate_path_list(inputs: dict[str, Any], key: str, issues: list[str]) -> None:
    value = inputs.get(key)
    if not isinstance(value, list) or not value:
        issues.append(f"{key} must be a non-empty array of paths")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{key}[{index}] must be a non-empty path string")
            continue
        if is_placeholder_path(item):
            issues.append(f"{key}[{index}] must be a concrete path, not a placeholder")


def source_context(status: dict[str, Any]) -> dict[str, Any]:
    context = {key: status.get(key) for key in SOURCE_CONTEXT_KEYS if key in status}
    if context.get("contentGoalOverages") == {}:
        context.pop("contentGoalOverages", None)
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
    if "createdSiteSubmittedValues" in data:
        submitted = data.get("createdSiteSubmittedValues")
        if not isinstance(submitted, dict):
            issues.append("createdSiteSubmittedValues must be an object when present")
        else:
            issues.extend(created_site_submitted_values_issues(submitted))
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


def expected_content_type_count(inputs: dict[str, Any]) -> int:
    return len(expected_content_types(inputs))


def expected_content_types(inputs: dict[str, Any]) -> set[str]:
    counts = inputs.get("contentCounts")
    if not isinstance(counts, dict):
        return set()
    expected: set[str] = set()
    for key in ("products", "posts"):
        value = counts.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value > 0:
            expected.add(key)
    return expected


def evidence_content_types(paths: list[str], label: str, issues: list[str]) -> set[str]:
    content_types: set[str] = set()
    for index, path in enumerate(paths):
        if is_placeholder_path(path):
            continue
        try:
            data = load_json(Path(path).expanduser(), f"{label}[{index}]")
        except ValueError as exc:
            issues.append(str(exc))
            continue
        content_type = data.get("contentType")
        if content_type in {"products", "posts"}:
            content_types.add(str(content_type))
        else:
            issues.append(f"{label}[{index}].contentType must be products or posts")
    return content_types


def validate_content_type_evidence_coverage(inputs: dict[str, Any], issues: list[str]) -> None:
    expected_types = expected_content_types(inputs)
    if len(expected_types) <= 1:
        return
    expected_count = len(expected_types)
    labels = {
        "sampleEvidence": "sample evidence",
        "batchValidation": "batch validation",
    }
    for key, label in labels.items():
        value = inputs.get(key)
        actual = len(value) if isinstance(value, list) else 0
        if actual < expected_count:
            issues.append(
                f"{key} must include at least {expected_count} paths for the planned products/posts content types"
            )
            continue
        if not isinstance(value, list):
            continue
        actual_types = evidence_content_types([item for item in value if isinstance(item, str)], label, issues)
        missing_types = sorted(expected_types - actual_types)
        if missing_types:
            issues.append(f"{key} missing contentType coverage: " + ", ".join(missing_types))


def context_paths(status: dict[str, Any]) -> dict[str, str]:
    artifacts = status.get("artifacts")
    return artifacts if isinstance(artifacts, dict) else {}


def stage_evidence(status: dict[str, Any], stage_id: str) -> str:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return ""
    stage = stages.get(stage_id)
    if not isinstance(stage, dict):
        return ""
    value = stage.get("evidence")
    return value if isinstance(value, str) else ""


def first_stage_path(status: dict[str, Any], stage_id: str) -> str:
    value = stage_evidence(status, stage_id)
    if not value:
        return ""
    return value.split(",")[0].strip()


def stage_paths(status: dict[str, Any], stage_id: str) -> list[str]:
    value = stage_evidence(status, stage_id)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def input_template(status: dict[str, Any], status_path: str) -> dict[str, Any]:
    paths = context_paths(status)
    template = {
        "kind": "allincms_launch_acceptance_inputs",
        "sourceExecutionStatus": status_path,
        "sourceStatusCurrentStage": status.get("currentStage", ""),
        "runEvidence": "",
        "moduleCoverage": "",
        "stageCoverage": "",
        "finalFrontendAudit": "",
        "cleanupEvidence": "",
        "roundCloseout": "",
        "autoFinalCloseout": True,
        "finalCloseoutSedimentation": "updated|none|read-only-deferred",
        "finalCloseoutSedimentationNote": "replace with final launch sedimentation note",
        "requireCreatedSite": True,
        "objective": "source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
        "package": paths.get("sourcePackage", "") or first_stage_path(status, "source_package"),
        "reviewPacket": paths.get("reviewPacket", "") or first_stage_path(status, "review_packet"),
        "confirmation": first_stage_path(status, "confirmation"),
        "executionPlan": first_stage_path(status, "execution_plan"),
        "artifactReadiness": first_stage_path(status, "artifact_export"),
        "createdSiteBinding": first_stage_path(status, "created_site_binding"),
        "pagesSiteInfoHandoff": first_stage_path(status, "pages_site_info_handoff"),
        "pagesSiteInfoValidation": first_stage_path(status, "pages_site_info_execution"),
        "taxonomyHandoff": first_stage_path(status, "taxonomy_execution_handoff"),
        "taxonomyValidation": first_stage_path(status, "taxonomy_execution"),
        "schemaCaptureHandoff": first_stage_path(status, "schema_capture_handoff"),
        "uploadReadiness": stage_paths(status, "schema_manifests"),
        "sampleEvidence": stage_paths(status, "sample_upload"),
        "batchValidation": stage_paths(status, "batch_upload"),
        "formsMediaSettings": first_stage_path(status, "forms_media_settings"),
    }
    template.update(source_context(status))
    return template


def validation_command(filled_path: Path, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/prepare_launch_acceptance_inputs_bundle.py "
        f"--validate-inputs {filled_path} --output-dir {output_dir}"
    )


def apply_command(filled_path: Path, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_launch_acceptance.py "
        "--run-evidence <from launch-acceptance-inputs.filled.json:runEvidence> "
        "--module-coverage <from launch-acceptance-inputs.filled.json:moduleCoverage> "
        "--upload-readiness <from launch-acceptance-inputs.filled.json:uploadReadiness[]> "
        "--sample-evidence <from launch-acceptance-inputs.filled.json:sampleEvidence[]> "
        "--batch-validation <from launch-acceptance-inputs.filled.json:batchValidation[]> "
        "--forms-media-settings <from launch-acceptance-inputs.filled.json:formsMediaSettings> "
        "--final-frontend-audit <from launch-acceptance-inputs.filled.json:finalFrontendAudit> "
        "--cleanup-evidence <from launch-acceptance-inputs.filled.json:cleanupEvidence> "
        "--auto-final-closeout "
        "--final-closeout-sedimentation <from launch-acceptance-inputs.filled.json:finalCloseoutSedimentation> "
        "--final-closeout-sedimentation-note <from launch-acceptance-inputs.filled.json:finalCloseoutSedimentationNote> "
        "--package <source-site-package.json> "
        "--confirmation <confirmation-record.json> "
        "--execution-plan <confirmed-site-execution-plan.json> "
        "--artifact-readiness <artifact-readiness.json> "
        "--created-site-binding <created-site-artifact-binding.json> "
        "--pages-site-info-handoff <pages-site-info-browser-handoff.json> "
        "--pages-site-info-validation <pages-site-info-execution-validation.json> "
        "--schema-capture-handoff <schema-capture-handoff.json> "
        f"--output-dir {output_dir / 'launch-acceptance-applied'}"
    )


def build_notes(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Launch Acceptance Inputs Bundle",
            "",
            "This bundle is local scaffolding only. It does not prove launch acceptance or mutate AllinCMS.",
            "",
            "Before filling `launch-acceptance-inputs.filled.json`:",
            "- provide real run evidence from the browser execution, not local rehearsal evidence",
            "- provide final frontend audit stage result after public route/detail checks",
            "- provide cleanup evidence for probes or an absence scan",
            "- provide a launch closeout, or keep autoFinalCloseout=true with sedimentation fields",
            "- keep source-context counts, wikiReview, and confirmationDecisionMatrix aligned with the confirmed source package",
            "- do not store cookies, authorization headers, server-action IDs, router state, account emails, raw IDs, or business copy",
            "",
            f"Current source stage: {status.get('currentStage')}",
            "",
            "The filled inputs are ready only when this helper validates them and prepare_source_next_stage.py expands the bundle into apply_launch_acceptance.py.",
        ]
    ) + "\n"


def build_bundle(*, status: dict[str, Any], status_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if status.get("kind") != "allincms_source_execution_status":
        raise ValueError("status kind must be allincms_source_execution_status")
    if status.get("remoteMutationsPerformed") is not False:
        raise ValueError("status must be local-only/no remote mutation")
    if status.get("currentStage") != "launch_acceptance":
        raise ValueError("status.currentStage must be launch_acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "launch-acceptance-inputs.template.json"
    filled_path = output_dir / "launch-acceptance-inputs.filled.json"
    notes_path = output_dir / "notes.md"
    validation_command_path = output_dir / "validation-command.txt"
    apply_command_path = output_dir / "apply-command.txt"
    template = input_template(status, status_path)
    write_json(template_path, template)
    write_json(filled_path, template)
    notes_path.write_text(build_notes(status), encoding="utf-8")
    validation_command_path.write_text(validation_command(filled_path, output_dir) + "\n", encoding="utf-8")
    apply_command_path.write_text(apply_command(filled_path, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_launch_acceptance_inputs_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "sourceExecutionStatus": status_path,
        "sourceStatusCurrentStage": status.get("currentStage", ""),
        "inputsTemplate": str(template_path),
        "filledInputsPath": str(filled_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "real launch run evidence",
            "module coverage or approved UI-first module coverage",
            "final frontend audit stage result",
            "cleanup evidence or absence scan",
            "final launch sedimentation closeout or auto-final-closeout fields",
            "matching source-context counts and confirmation decisions",
        ],
        "nextAction": "fill launch acceptance inputs after final browser proof, validate inputs, then run prepare_source_next_stage.py with --launch-acceptance-inputs-bundle",
    }
    bundle.update(source_context(status))
    return bundle


def validate_inputs(inputs: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if inputs.get("kind") != "allincms_launch_acceptance_inputs":
        issues.append("kind must be allincms_launch_acceptance_inputs")
    for key in REQUIRED_PATH_FIELDS:
        validate_path_value(inputs, key, required=True, issues=issues)
    for key in OPTIONAL_PATH_FIELDS:
        validate_path_value(inputs, key, required=False, issues=issues)
    if not inputs.get("roundCloseout") and inputs.get("autoFinalCloseout") is not True:
        issues.append("roundCloseout is required unless autoFinalCloseout is true")
    if inputs.get("autoFinalCloseout") is True:
        if inputs.get("finalCloseoutSedimentation") not in {"updated", "none", "read-only-deferred"}:
            issues.append("finalCloseoutSedimentation must be updated, none, or read-only-deferred")
        note = inputs.get("finalCloseoutSedimentationNote")
        if not isinstance(note, str) or len(note.strip()) < 8 or "replace with" in note:
            issues.append("finalCloseoutSedimentationNote must be concrete when autoFinalCloseout is true")
    for key in PATH_LIST_FIELDS:
        validate_path_list(inputs, key, issues)
    issues.extend(source_context_issues(inputs))
    validate_content_type_evidence_coverage(inputs, issues)
    return issues


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_launch_acceptance_inputs_bundle":
        issues.append("kind must be allincms_launch_acceptance_inputs_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in ("sourceExecutionStatus", "inputsTemplate", "filledInputsPath", "notes", "validationCommand", "applyCommand"):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "final frontend audit stage result" not in required:
        issues.append("requiredBeforeUse must include final frontend audit stage result")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate a local launch acceptance inputs bundle.")
    parser.add_argument("--status", default="", help="allincms_source_execution_status JSON at launch_acceptance")
    parser.add_argument("--validate-inputs", default="", help="filled launch-acceptance-inputs JSON to validate")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        if args.validate_inputs:
            inputs = load_json(Path(args.validate_inputs), "launch acceptance inputs")
            issues = validate_inputs(inputs)
            report = {
                "kind": "allincms_launch_acceptance_inputs_validation",
                "generatedAt": now_iso(),
                "valid": not issues,
                "inputs": args.validate_inputs,
                "issues": issues,
            }
            write_json(output_dir / "launch-acceptance-inputs-validation.json", report)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            elif issues:
                print("Launch acceptance inputs invalid:")
                for issue in issues:
                    print(f"- {issue}")
            else:
                print("Launch acceptance inputs validation passed.")
            return 0 if not issues else 1
        if not args.status:
            raise ValueError("--status is required unless --validate-inputs is used")
        bundle = build_bundle(
            status=load_json(Path(args.status), "source execution status"),
            status_path=args.status,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("launch acceptance inputs bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "inputs-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote launch acceptance inputs bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
