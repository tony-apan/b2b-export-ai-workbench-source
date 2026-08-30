#!/usr/bin/env python3
"""Prepare the next local handoff from allincms_source_execution_status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from typing import Any

from prepare_launch_acceptance_inputs_bundle import validate_inputs as validate_launch_acceptance_inputs


SUPPORTED_STAGES = {
    "source_package",
    "review_packet",
    "confirmation",
    "execution_plan",
    "artifact_export",
    "create_site_handoff",
    "created_site_binding",
    "pages_site_info_handoff",
    "pages_site_info_execution",
    "taxonomy_execution_handoff",
    "taxonomy_execution",
    "schema_capture_handoff",
    "schema_manifests",
    "sample_upload",
    "batch_upload",
    "forms_media_settings",
    "launch_acceptance",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts if part != "")


def stage(status: dict[str, Any], stage_id: str) -> dict[str, Any]:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return {}
    value = stages.get(stage_id)
    return value if isinstance(value, dict) else {}


def evidence(status: dict[str, Any], stage_id: str) -> str:
    value = stage(status, stage_id).get("evidence")
    return value if isinstance(value, str) else ""


def first_evidence(status: dict[str, Any], *stage_ids: str) -> str:
    for stage_id in stage_ids:
        value = evidence(status, stage_id)
        if value and not value.endswith("-present") and value not in {"existing-site-mode", "taxonomy-not-required"}:
            return value
    return ""


def csv_evidence(status: dict[str, Any], stage_id: str) -> list[str]:
    value = evidence(status, stage_id)
    if not value:
        return []
    return [item for item in value.split(",") if item]


def artifact_path(status: dict[str, Any], key: str) -> str:
    artifacts = status.get("artifacts")
    if not isinstance(artifacts, dict):
        return ""
    value = artifacts.get(key)
    return value if isinstance(value, str) else ""


def output_dir(base: Path, stage_id: str) -> str:
    return str(base / stage_id)


def context_paths(status: dict[str, Any]) -> dict[str, str]:
    return {
        "package": first_evidence(status, "source_package"),
        "review_packet": first_evidence(status, "review_packet"),
        "confirmation": first_evidence(status, "confirmation"),
        "execution_plan": first_evidence(status, "execution_plan"),
        "artifact_readiness": first_evidence(status, "artifact_export"),
        "create_site_handoff": first_evidence(status, "create_site_handoff"),
        "created_site_binding": first_evidence(status, "created_site_binding"),
        "pages_site_info_handoff": first_evidence(status, "pages_site_info_handoff"),
        "pages_site_info_validation": first_evidence(status, "pages_site_info_execution"),
        "taxonomy_handoff": first_evidence(status, "taxonomy_execution_handoff"),
        "taxonomy_validation": first_evidence(status, "taxonomy_execution"),
        "schema_capture_handoff": first_evidence(status, "schema_capture_handoff"),
        "upload_readiness": first_evidence(status, "schema_manifests"),
        "batch_validation": first_evidence(status, "batch_upload"),
        "forms_media_settings": first_evidence(status, "forms_media_settings"),
        "launch_acceptance": first_evidence(status, "launch_acceptance"),
    }


def source_identity_context(status: dict[str, Any]) -> dict[str, str]:
    context: dict[str, str] = {}
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = status.get(key)
        if isinstance(value, str) and value:
            context[key] = value
    return context


def created_site_submitted_values_context(status: dict[str, Any]) -> dict[str, Any]:
    values = status.get("createdSiteSubmittedValues")
    if isinstance(values, dict) and values:
        return {"createdSiteSubmittedValues": values}
    return {}


def stage_handoff_preflight_blocker(stage_id: str, paths: dict[str, str]) -> dict[str, Any]:
    if stage_id not in {"taxonomy_execution_handoff", "schema_capture_handoff"}:
        return {}
    path_key = "taxonomy_handoff" if stage_id == "taxonomy_execution_handoff" else "schema_capture_handoff"
    label = "taxonomy handoff" if stage_id == "taxonomy_execution_handoff" else "schema-capture handoff"
    path = paths.get(path_key) or ""
    if not path:
        return {}
    try:
        handoff = load_json(Path(path), label)
    except SystemExit:
        return {}
    blocked_content_types: list[str] = []
    if stage_id == "schema_capture_handoff":
        stages = handoff.get("stages")
        if isinstance(stages, list):
            for item in stages:
                if not isinstance(item, dict):
                    continue
                if item.get("status") == "needs_readonly_content_preflight":
                    content_type = item.get("contentType")
                    if isinstance(content_type, str) and content_type.strip():
                        blocked_content_types.append(content_type.strip())
        issues = [f"preflight.contentTypes.{content_type}" for content_type in blocked_content_types]
        ready_stage = handoff.get("overallStatus")
        blocked_ready_stage = bool(blocked_content_types) or ready_stage == "needs_readonly_content_preflight"
        if not issues and not blocked_ready_stage:
            return {}
        return {
            "handoffReadyForBrowserStage": ready_stage if isinstance(ready_stage, str) else "",
            "handoffPreflightIssues": issues,
            "handoffBlockedContentTypes": blocked_content_types,
            "blocker": (
                "Schema-capture handoff is blocked by missing current-site read-only content preflight; "
                "refresh the listed products/posts list/edit evidence before preparing create-probe actions."
            ),
        }
    issues = handoff.get("preflightIssues")
    if not isinstance(issues, list):
        issues = []
    issues = [item for item in issues if isinstance(item, str) and item.strip()]
    ready_stage = handoff.get("readyForBrowserStage")
    blocked_ready_stage = isinstance(ready_stage, str) and ready_stage.startswith("blocked")
    if not issues and not blocked_ready_stage:
        return {}
    return {
        "handoffReadyForBrowserStage": ready_stage if isinstance(ready_stage, str) else "",
        "handoffPreflightIssues": issues,
        "blocker": (
            "Taxonomy handoff is blocked by missing current-site read-only preflight evidence; "
            "refresh the listed products/posts setup evidence before preparing taxonomy actions."
        ),
    }


def add_optional(parts: list[str], flag: str, value: str) -> None:
    if value:
        if flag in {"--upload-readiness", "--batch-validation"}:
            for item in [part.strip() for part in value.split(",") if part.strip()]:
                parts.extend([flag, item])
            return
        parts.extend([flag, value])


def assert_bundle_ready(bundle: dict[str, Any], label: str, expected_stage: str = "") -> None:
    """Reject evidence/input bundles that explicitly say their source handoff is blocked."""
    ready_stage = bundle.get("handoffReadyForBrowserStage")
    if isinstance(ready_stage, str) and ready_stage and expected_stage and ready_stage != expected_stage:
        raise SystemExit(
            f"ERROR: {label} was generated from a blocked or stale handoff; "
            "refresh the current read-only preflight/handoff and regenerate the bundle before applying evidence"
        )
    preflight_issues = bundle.get("handoffPreflightIssues")
    if isinstance(preflight_issues, list) and preflight_issues:
        raise SystemExit(
            f"ERROR: {label} has handoffPreflightIssues; "
            "refresh the current read-only preflight/handoff and regenerate the bundle before applying evidence"
        )
    source_stage = bundle.get("sourceCurrentStage")
    if isinstance(source_stage, str) and source_stage and expected_stage and source_stage != expected_stage:
        raise SystemExit(
            f"ERROR: {label} was generated for sourceCurrentStage={source_stage}; "
            f"current apply stage expects {expected_stage}"
        )
    source_status_stage = bundle.get("sourceStatusCurrentStage")
    if isinstance(source_status_stage, str) and source_status_stage and expected_stage and source_status_stage != expected_stage:
        raise SystemExit(
            f"ERROR: {label} was generated for sourceStatusCurrentStage={source_status_stage}; "
            f"current apply stage expects {expected_stage}"
        )
    blocked = bundle.get("blocked")
    if blocked is True:
        raise SystemExit(f"ERROR: {label} declares blocked=true; resolve blockers before applying evidence")
    blockers = bundle.get("blockers")
    if isinstance(blockers, list) and blockers:
        raise SystemExit(f"ERROR: {label} declares blockers; resolve them before applying evidence")
    validation = bundle.get("validation")
    if isinstance(validation, dict) and validation.get("ok") is False:
        raise SystemExit(f"ERROR: {label} declares validation.ok=false; regenerate the bundle before applying evidence")


def require_bundle_file(bundle: dict[str, Any], label: str, key: str) -> str:
    value = str(bundle.get(key) or "").strip()
    if not value:
        raise SystemExit(f"ERROR: {label} must include {key}")
    if value.startswith("<") or value.endswith(">"):
        raise SystemExit(f"ERROR: {label} {key} is still a placeholder")
    path = Path(value)
    if not path.exists() or not path.is_file():
        raise SystemExit(f"ERROR: {label} {key} does not exist: {value}")
    return value


def replace_confirmation_placeholder(command: str, confirmation_text: str) -> str:
    quoted = shlex.quote(confirmation_text)
    return command.replace("'<paste current user confirmation text here>'", quoted).replace(
        '"<paste current user confirmation text here>"',
        quoted,
    ).replace("<paste current user confirmation text here>", quoted)


def append_optional_command_flags(command: str, args: argparse.Namespace) -> str:
    parts: list[str] = []
    for flag, value in (
        ("--site-key", args.site_key),
        ("--frontend-base-url", args.frontend_base_url),
        ("--accepted-fields", args.accepted_fields),
        ("--notes", args.notes),
        ("--create-preflight", args.create_preflight),
        ("--create-authorization-output", args.create_authorization_output),
    ):
        if value and flag not in command:
            parts.extend([flag, value])
    if args.target_mode and "--target-mode" not in command:
        parts.extend(["--target-mode", args.target_mode])
    if "--accepted-deferral" not in command:
        for value in args.accepted_deferral:
            if value:
                parts.extend(["--accepted-deferral", value])
    if not parts:
        return command
    return command + " " + shell_join(parts)


def review_packet_confirmed_execution_template(review_packet_path: str) -> str:
    if not review_packet_path:
        return ""
    packet = load_json(Path(review_packet_path), "review packet")
    value = packet.get("confirmedExecutionCommandTemplate")
    return value if isinstance(value, str) and value.strip() else ""


def command_prepare_created_site(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    if not args.created_site_evidence:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/prepare_created_site_schema_capture.py",
        "--artifact-readiness",
        paths["artifact_readiness"],
        "--created-site-evidence",
        args.created_site_evidence,
    ]
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
    ):
        add_optional(parts, flag, paths[key])
    add_optional(parts, "--authorization-dir", args.authorization_dir)
    add_optional(parts, "--theme-target", args.theme_target)
    parts.extend(["--output-dir", output_dir(base, "created-site-schema-capture")])
    return shell_join(parts)


def command_apply_created_site_evidence_bundle(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    if not (args.created_site_evidence_bundle and args.filled_created_site_evidence_template):
        return ""
    created_site_evidence = args.created_site_evidence or str(base / "created-site-evidence" / "created-site-evidence.json")
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_created_site_evidence_bundle.py",
        "--bundle",
        args.created_site_evidence_bundle,
        "--filled-template",
        args.filled_created_site_evidence_template,
        "--output-dir",
        output_dir(base, "created-site-evidence-applied"),
        "--created-site-evidence-output",
        created_site_evidence,
        "--prepare-created-site-schema-capture",
    ]
    for flag, key in (
        ("--artifact-readiness", "artifact_readiness"),
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
    ):
        add_optional(parts, flag, paths[key])
    add_optional(parts, "--authorization-dir", args.authorization_dir)
    add_optional(parts, "--theme-target", args.theme_target)
    return shell_join(parts)


def command_apply_created_site_evidence_to_source_rehearsal(
    status: dict[str, Any],
    paths: dict[str, str],
    base: Path,
    args: argparse.Namespace,
) -> str:
    if not (args.create_preflight_source_apply_result and args.filled_created_site_evidence_template):
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_created_site_evidence_to_source_rehearsal.py",
        "--source-apply-result",
        args.create_preflight_source_apply_result,
        "--filled-created-site-evidence-template",
        args.filled_created_site_evidence_template,
    ]
    add_optional(parts, "--created-site-evidence-bundle", args.created_site_evidence_bundle)
    parts.extend(["--output-dir", output_dir(base, "created-site-source-rehearsal-applied")])
    add_optional(parts, "--authorization-dir", args.authorization_dir)
    add_optional(parts, "--theme-target", args.theme_target)
    return shell_join(parts)


def command_apply_default_theme_bootstrap(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    if not (args.created_site_evidence and args.default_theme_bootstrap_runbook and args.default_theme_bootstrap_evidence):
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_default_theme_bootstrap.py",
        "--created-site-evidence",
        args.created_site_evidence,
        "--runbook",
        args.default_theme_bootstrap_runbook,
        "--bootstrap-evidence",
        args.default_theme_bootstrap_evidence,
        "--output-dir",
        output_dir(base, "default-theme-bootstrap-applied"),
        "--fail-on-invalid",
    ]
    return shell_join(parts)


def command_prepare_confirmed_execution(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    confirmation_text = args.user_confirmation_text or ""
    if not confirmation_text:
        return ""
    template = review_packet_confirmed_execution_template(paths["review_packet"])
    if template:
        return append_optional_command_flags(replace_confirmation_placeholder(template, confirmation_text), args)
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/prepare_confirmed_site_execution.py",
        "--package",
        paths["package"],
        "--review-packet",
        paths["review_packet"],
        "--user-confirmation-text",
        confirmation_text,
        "--target-mode",
        args.target_mode,
    ]
    add_optional(parts, "--site-key", args.site_key)
    add_optional(parts, "--frontend-base-url", args.frontend_base_url)
    for field in args.accepted_deferral:
        parts.extend(["--accepted-deferral", field])
    add_optional(parts, "--accepted-fields", args.accepted_fields)
    add_optional(parts, "--notes", args.notes)
    add_optional(parts, "--create-preflight", args.create_preflight)
    add_optional(parts, "--create-authorization-output", args.create_authorization_output)
    parts.extend(["--output-dir", output_dir(base, "confirmed-site-execution")])
    return shell_join(parts)


def command_build_execution_plan(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/build_confirmed_site_execution_plan.py",
        "--package",
        paths["package"],
        "--confirmation",
        paths["confirmation"],
        "--target-mode",
        args.target_mode,
        "--output",
        str(base / "confirmed-site-execution-plan.json"),
    ]
    add_optional(parts, "--site-key", args.site_key)
    return shell_join(parts)


def command_export_artifacts(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/export_confirmed_site_artifacts.py",
        "--package",
        paths["package"],
        "--confirmation",
        paths["confirmation"],
        "--execution-plan",
        paths["execution_plan"],
    ]
    add_optional(parts, "--site-key", args.site_key)
    add_optional(parts, "--frontend-base-url", args.frontend_base_url)
    parts.extend(["--output-dir", output_dir(base, "confirmed-artifacts")])
    return shell_join(parts)


def command_build_create_site_runbook(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    create_site_handoff = paths["create_site_handoff"] or "<create-site-handoff.json>"
    authorization_record = args.create_authorization_output or str(base / "create-site" / "authorization-create-site.json")
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/build_create_site_runbook.py",
        "--create-site-handoff",
        create_site_handoff,
        "--authorization-record",
        authorization_record,
        "--output",
        str(base / "create-site" / "create-site-browser-runbook.json"),
    ]
    return shell_join(parts)


def command_apply_refined_source_wiki(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    refined_wiki = args.source_wiki or "<refined-source-wiki.json>"
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_refined_source_wiki.py",
        "--source-wiki",
        refined_wiki,
    ]
    add_optional(parts, "--inventory", args.inventory)
    add_optional(parts, "--requirements", args.requirements)
    add_optional(parts, "--site-key", args.site_key)
    add_optional(parts, "--frontend-base-url", args.frontend_base_url)
    parts.extend(["--output-dir", output_dir(base, "refined-source-wiki-apply")])
    return shell_join(parts)


def command_apply_pages(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    pages_handoff = paths["pages_site_info_handoff"]
    pages_evidence = args.pages_site_info_evidence
    if args.pages_site_info_evidence_bundle:
        bundle = load_json(Path(args.pages_site_info_evidence_bundle), "pages/site-info evidence bundle")
        assert_bundle_ready(bundle, "pages/site-info evidence bundle", "pages_site_info_execution")
        pages_handoff = str(bundle.get("handoff") or pages_handoff).strip()
        pages_evidence = require_bundle_file(bundle, "pages/site-info evidence bundle", "filledEvidencePath")
        if not pages_handoff:
            raise SystemExit("ERROR: pages/site-info evidence bundle must include handoff")
    if not pages_evidence:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_pages_site_info_execution.py",
        "--pages-site-info-handoff",
        pages_handoff,
        "--pages-site-info-evidence",
        pages_evidence,
    ]
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--upload-readiness", "upload_readiness"),
        ("--batch-validation", "batch_validation"),
        ("--forms-media-settings", "forms_media_settings"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    for sample in csv_evidence(status, "sample_upload"):
        parts.extend(["--sample-evidence", sample])
    parts.extend(["--output-dir", output_dir(base, "pages-site-info-applied")])
    return shell_join(parts)


def command_apply_taxonomy(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    taxonomy_handoff = paths["taxonomy_handoff"]
    taxonomy_evidence = args.taxonomy_evidence
    if args.taxonomy_evidence_bundle:
        bundle = load_json(Path(args.taxonomy_evidence_bundle), "taxonomy evidence bundle")
        assert_bundle_ready(
            bundle,
            "taxonomy evidence bundle",
            "ready_to_prepare_action_specific_taxonomy_authorization",
        )
        taxonomy_handoff = str(bundle.get("handoff") or taxonomy_handoff).strip()
        taxonomy_evidence = require_bundle_file(bundle, "taxonomy evidence bundle", "filledEvidencePath")
        if not taxonomy_handoff:
            raise SystemExit("ERROR: taxonomy evidence bundle must include handoff")
    if not taxonomy_evidence:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_taxonomy_execution.py",
        "--taxonomy-handoff",
        taxonomy_handoff,
        "--taxonomy-evidence",
        taxonomy_evidence,
    ]
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--upload-readiness", "upload_readiness"),
        ("--batch-validation", "batch_validation"),
        ("--forms-media-settings", "forms_media_settings"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    for sample in csv_evidence(status, "sample_upload"):
        parts.extend(["--sample-evidence", sample])
    parts.extend(["--output-dir", output_dir(base, "taxonomy-applied")])
    return shell_join(parts)


def command_schema_manifest_sample(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    manifest = args.manifest or "<draft-products-or-posts-manifest.json>"
    save_capture = args.save_capture_evidence or "<save-capture-evidence.json>"
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/prepare_schema_manifest_sample.py",
        "--manifest",
        manifest,
        "--save-capture-evidence",
        save_capture,
    ]
    add_optional(parts, "--base-run-evidence", args.base_run_evidence)
    for flag, key in (
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--batch-validation", "batch_validation"),
        ("--forms-media-settings", "forms_media_settings"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    for sample in csv_evidence(status, "sample_upload"):
        parts.extend(["--sample-evidence", sample])
    existing_upload_readiness = list(args.existing_upload_readiness)
    for item in [
        item
        for item in csv_evidence(status, "schema_manifests")
        if item and item not in {args.save_capture_evidence, args.manifest}
    ]:
        if item not in existing_upload_readiness:
            existing_upload_readiness.append(item)
    for readiness in existing_upload_readiness:
        parts.extend(["--existing-upload-readiness", readiness])
    add_optional(parts, "--site-key", args.site_key)
    add_optional(parts, "--frontend-base-url", args.frontend_base_url)
    add_optional(parts, "--target", args.target)
    add_optional(parts, "--sample-slug", args.sample_slug)
    parts.extend(["--output-dir", output_dir(base, "schema-manifest-sample")])
    return shell_join(parts)


def command_prepare_batch(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    sample_paths = csv_evidence(status, "sample_upload")
    sample = args.sample_evidence or (
        sample_paths[0] if len(sample_paths) == 1 else "<sample-evidence-for-selected-manifest.json>"
    )
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/prepare_batch_upload_publish.py",
        "--run-evidence",
        args.base_run_evidence or "<base-run-evidence-after-save-capture.json>",
        "--manifest",
        args.manifest or "<schema-verified-manifest.json>",
        "--sample-evidence",
        sample,
        "--output-dir",
        output_dir(base, "batch-upload-publish"),
    ]
    existing_samples = list(args.existing_sample_evidence)
    for existing_sample in sample_paths:
        if existing_sample != sample and existing_sample not in existing_samples:
            existing_samples.append(existing_sample)
    for existing_sample in existing_samples:
        parts.extend(["--existing-sample-evidence", existing_sample])
    add_optional(parts, "--taxonomy-validation", paths["taxonomy_validation"])
    add_optional(parts, "--target", args.target)
    return shell_join(parts)


def command_apply_sample(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    sample_evidence = args.sample_evidence
    manifest = args.manifest or "<schema-verified-manifest.json>"
    if args.sample_evidence_bundle:
        bundle = load_json(Path(args.sample_evidence_bundle), "manifest sample evidence bundle")
        assert_bundle_ready(bundle, "manifest sample evidence bundle", "sample_upload")
        sample_evidence = require_bundle_file(bundle, "manifest sample evidence bundle", "filledEvidencePath")
        manifest = str(bundle.get("manifest") or manifest).strip()
    if not sample_evidence:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_manifest_sample_upload.py",
        "--manifest",
        manifest,
        "--sample-evidence",
        sample_evidence,
    ]
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--upload-readiness", "upload_readiness"),
        ("--batch-validation", "batch_validation"),
        ("--forms-media-settings", "forms_media_settings"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    existing_samples = list(args.existing_sample_evidence)
    for sample in csv_evidence(status, "sample_upload"):
        if sample != sample_evidence and sample not in existing_samples:
            existing_samples.append(sample)
    for sample in existing_samples:
        parts.extend(["--existing-sample-evidence", sample])
    parts.extend(["--output-dir", output_dir(base, "manifest-sample-applied")])
    return shell_join(parts)


def command_apply_batch(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    batch_evidence = args.batch_evidence
    manifest = args.manifest or "<schema-verified-manifest.json>"
    base_run_evidence = args.base_run_evidence
    frontend_audit_report = args.frontend_audit_report
    if args.batch_evidence_bundle:
        bundle_path = Path(args.batch_evidence_bundle)
        bundle = load_json(bundle_path, "batch upload/publish evidence bundle")
        assert_bundle_ready(bundle, "batch upload/publish evidence bundle", "batch_upload")
        batch_evidence = require_bundle_file(bundle, "batch upload/publish evidence bundle", "filledEvidencePath")
        manifest = str(bundle.get("manifest") or manifest).strip()
        base_run_evidence = str(bundle.get("sourceRunEvidence") or base_run_evidence).strip()
        frontend_audit_report = frontend_audit_report or str(bundle_path.parent / "final-audit-report.redacted.json")
        if not manifest or manifest.startswith("<"):
            raise SystemExit("ERROR: batch upload/publish evidence bundle must include manifest")
        if not base_run_evidence:
            raise SystemExit("ERROR: batch upload/publish evidence bundle must include sourceRunEvidence")
    if not batch_evidence:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_batch_upload_publish.py",
        "--batch-evidence",
        batch_evidence,
        "--manifest",
        manifest,
    ]
    add_optional(parts, "--base-run-evidence", base_run_evidence)
    add_optional(parts, "--frontend-audit-report", frontend_audit_report)
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--upload-readiness", "upload_readiness"),
        ("--forms-media-settings", "forms_media_settings"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    for sample in csv_evidence(status, "sample_upload"):
        parts.extend(["--sample-evidence", sample])
    existing_validations = list(args.existing_batch_validation)
    for validation in csv_evidence(status, "batch_upload"):
        if validation not in existing_validations:
            existing_validations.append(validation)
    for validation in existing_validations:
        parts.extend(["--existing-batch-validation", validation])
    parts.extend(["--output-dir", output_dir(base, "batch-applied")])
    return shell_join(parts)


def command_apply_forms_media_settings(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    evidence_path = args.forms_media_settings_evidence or ""
    if args.forms_media_settings_evidence_bundle:
        bundle = load_json(Path(args.forms_media_settings_evidence_bundle), "forms/media/settings evidence bundle")
        assert_bundle_ready(bundle, "forms/media/settings evidence bundle", "forms_media_settings")
        evidence_path = require_bundle_file(bundle, "forms/media/settings evidence bundle", "filledEvidencePath")
    if not evidence_path:
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_forms_media_settings.py",
        "--forms-media-settings-evidence",
        evidence_path,
    ]
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
        ("--upload-readiness", "upload_readiness"),
        ("--launch-acceptance", "launch_acceptance"),
    ):
        add_optional(parts, flag, paths[key])
    for sample in csv_evidence(status, "sample_upload"):
        parts.extend(["--sample-evidence", sample])
    existing_validations = list(args.existing_batch_validation)
    for validation in csv_evidence(status, "batch_upload"):
        if validation not in existing_validations:
            existing_validations.append(validation)
    for validation in existing_validations:
        parts.extend(["--batch-validation", validation])
    parts.extend(["--output-dir", output_dir(base, "forms-media-settings-applied")])
    return shell_join(parts)


def command_prepare_forms_media_settings_bundle(status_path: Path, base: Path) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/prepare_forms_media_settings_evidence_bundle.py",
            "--status",
            str(status_path),
            "--output-dir",
            output_dir(base, "forms-media-settings-evidence-bundle"),
        ]
    )


def command_prepare_launch_acceptance_inputs_bundle(status_path: Path, base: Path) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/prepare_launch_acceptance_inputs_bundle.py",
            "--status",
            str(status_path),
            "--output-dir",
            output_dir(base, "launch-acceptance-inputs-bundle"),
        ]
    )


def command_launch_acceptance(status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    launch_inputs: dict[str, Any] = {}
    if args.launch_acceptance_inputs_bundle:
        bundle = load_json(Path(args.launch_acceptance_inputs_bundle), "launch acceptance inputs bundle")
        assert_bundle_ready(bundle, "launch acceptance inputs bundle", "launch_acceptance")
        filled_path = require_bundle_file(bundle, "launch acceptance inputs bundle", "filledInputsPath")
        launch_inputs = load_json(Path(filled_path), "filled launch acceptance inputs")
        input_issues = validate_launch_acceptance_inputs(launch_inputs)
        if input_issues:
            raise SystemExit(
                "ERROR: filled launch acceptance inputs are invalid:\n- " + "\n- ".join(input_issues)
            )
    elif not any(
        [
            args.run_evidence,
            args.module_coverage,
            args.stage_coverage,
            args.final_frontend_audit,
            args.cleanup_evidence,
            args.round_closeout,
        ]
    ):
        return ""
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/apply_launch_acceptance.py",
        "--run-evidence",
        args.run_evidence or str(launch_inputs.get("runEvidence") or "") or "<final-run-evidence.json>",
        "--output-dir",
        output_dir(base, "launch-acceptance-applied"),
    ]
    add_optional(parts, "--module-coverage", args.module_coverage or str(launch_inputs.get("moduleCoverage") or ""))
    add_optional(parts, "--stage-coverage", args.stage_coverage or str(launch_inputs.get("stageCoverage") or ""))
    for upload_readiness in launch_inputs.get("uploadReadiness", []) if isinstance(launch_inputs.get("uploadReadiness"), list) else []:
        if isinstance(upload_readiness, str) and upload_readiness:
            parts.extend(["--upload-readiness", upload_readiness])
    for batch_validation in launch_inputs.get("batchValidation", []) if isinstance(launch_inputs.get("batchValidation"), list) else []:
        if isinstance(batch_validation, str) and batch_validation:
            parts.extend(["--batch-validation", batch_validation])
    add_optional(parts, "--forms-media-settings", str(launch_inputs.get("formsMediaSettings") or ""))
    add_optional(parts, "--final-frontend-audit", args.final_frontend_audit or str(launch_inputs.get("finalFrontendAudit") or ""))
    add_optional(parts, "--cleanup-evidence", args.cleanup_evidence or str(launch_inputs.get("cleanupEvidence") or ""))
    add_optional(parts, "--round-closeout", args.round_closeout or str(launch_inputs.get("roundCloseout") or ""))
    if launch_inputs.get("autoFinalCloseout") is True and "--round-closeout" not in parts:
        parts.append("--auto-final-closeout")
        add_optional(parts, "--final-closeout-sedimentation", str(launch_inputs.get("finalCloseoutSedimentation") or ""))
        add_optional(parts, "--final-closeout-sedimentation-note", str(launch_inputs.get("finalCloseoutSedimentationNote") or ""))
    if launch_inputs.get("requireCreatedSite") is True:
        parts.append("--require-created-site")
    add_optional(parts, "--objective", str(launch_inputs.get("objective") or ""))
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "review_packet"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "execution_plan"),
        ("--artifact-readiness", "artifact_readiness"),
        ("--create-site-handoff", "create_site_handoff"),
        ("--created-site-binding", "created_site_binding"),
        ("--pages-site-info-handoff", "pages_site_info_handoff"),
        ("--pages-site-info-validation", "pages_site_info_validation"),
        ("--taxonomy-handoff", "taxonomy_handoff"),
        ("--taxonomy-validation", "taxonomy_validation"),
        ("--schema-capture-handoff", "schema_capture_handoff"),
    ):
        add_optional(parts, flag, paths[key])
    if not launch_inputs:
        for upload_readiness in csv_evidence(status, "schema_manifests"):
            parts.extend(["--upload-readiness", upload_readiness])
        for batch_validation in csv_evidence(status, "batch_upload"):
            parts.extend(["--batch-validation", batch_validation])
        add_optional(parts, "--forms-media-settings", paths["forms_media_settings"])
    for flag, key in (
        ("--package", "package"),
        ("--review-packet", "reviewPacket"),
        ("--confirmation", "confirmation"),
        ("--execution-plan", "executionPlan"),
        ("--artifact-readiness", "artifactReadiness"),
        ("--created-site-binding", "createdSiteBinding"),
        ("--pages-site-info-handoff", "pagesSiteInfoHandoff"),
        ("--pages-site-info-validation", "pagesSiteInfoValidation"),
        ("--taxonomy-handoff", "taxonomyHandoff"),
        ("--taxonomy-validation", "taxonomyValidation"),
        ("--schema-capture-handoff", "schemaCaptureHandoff"),
    ):
        add_optional(parts, flag, str(launch_inputs.get(key) or ""))
    if not launch_inputs:
        for sample in csv_evidence(status, "sample_upload"):
            parts.extend(["--sample-evidence", sample])
    for sample in launch_inputs.get("sampleEvidence", []) if isinstance(launch_inputs.get("sampleEvidence"), list) else []:
        if isinstance(sample, str) and sample:
            parts.extend(["--sample-evidence", sample])
    return shell_join(parts)


def stage_command(stage_id: str, status: dict[str, Any], paths: dict[str, str], base: Path, args: argparse.Namespace) -> str:
    bootstrap_command = command_apply_default_theme_bootstrap(status, paths, base, args)
    if bootstrap_command and stage_id in {
        "created_site_binding",
        "pages_site_info_handoff",
        "pages_site_info_execution",
        "taxonomy_execution_handoff",
        "taxonomy_execution",
        "schema_capture_handoff",
    }:
        return bootstrap_command
    if stage_id in {"source_package", "review_packet"}:
        return command_apply_refined_source_wiki(status, paths, base, args)
    if stage_id == "confirmation":
        return command_prepare_confirmed_execution(status, paths, base, args)
    if stage_id == "execution_plan":
        return command_build_execution_plan(status, paths, base, args)
    if stage_id == "artifact_export":
        return command_export_artifacts(status, paths, base, args)
    if stage_id == "create_site_handoff":
        return command_build_create_site_runbook(status, paths, base, args)
    if stage_id == "created_site_binding":
        source_rehearsal_command = command_apply_created_site_evidence_to_source_rehearsal(status, paths, base, args)
        if source_rehearsal_command:
            return source_rehearsal_command
        bundle_command = command_apply_created_site_evidence_bundle(status, paths, base, args)
        if bundle_command:
            return bundle_command
        return command_prepare_created_site(status, paths, base, args)
    if stage_handoff_preflight_blocker(stage_id, paths):
        return ""
    if stage_id in {"pages_site_info_handoff", "taxonomy_execution_handoff"}:
        return command_prepare_created_site(status, paths, base, args)
    if stage_id == "pages_site_info_execution" and (args.pages_site_info_evidence or args.pages_site_info_evidence_bundle):
        return command_apply_pages(status, paths, base, args)
    if stage_id == "taxonomy_execution" and (args.taxonomy_evidence or args.taxonomy_evidence_bundle):
        return command_apply_taxonomy(status, paths, base, args)
    if stage_id == "schema_manifests":
        return command_schema_manifest_sample(status, paths, base, args)
    if stage_id == "sample_upload" and (args.sample_evidence or args.sample_evidence_bundle):
        return command_apply_sample(status, paths, base, args)
    if stage_id == "batch_upload":
        if args.batch_evidence or args.batch_evidence_bundle:
            return command_apply_batch(status, paths, base, args)
        return command_prepare_batch(status, paths, base, args)
    if stage_id == "forms_media_settings":
        return command_apply_forms_media_settings(status, paths, base, args)
    if stage_id == "launch_acceptance":
        return command_launch_acceptance(status, paths, base, args)
    return ""


def stage_mode(stage_id: str, command: str = "") -> str:
    if stage_id == "confirmation":
        return "local_helper_prepares_or_applies_stage" if command else "user_confirmation_required"
    if stage_id == "created_site_binding":
        return "local_helper_prepares_or_applies_stage" if command else "browser_action_or_capture_required"
    if stage_id == "create_site_handoff":
        return "local_helper_prepares_or_applies_stage" if command else "browser_action_or_capture_required"
    if stage_id in {"pages_site_info_execution", "taxonomy_execution", "forms_media_settings"} and command:
        return "local_helper_prepares_or_applies_stage"
    if stage_id in {
        "create_site_handoff",
        "pages_site_info_execution",
        "taxonomy_execution",
        "schema_capture_handoff",
        "sample_upload",
        "forms_media_settings",
    }:
        if command and stage_id in {"pages_site_info_execution", "taxonomy_execution", "sample_upload", "forms_media_settings"}:
            return "local_helper_prepares_or_applies_stage"
        return "browser_action_or_capture_required"
    if stage_id in {
        "source_package",
        "review_packet",
        "execution_plan",
        "artifact_export",
        "pages_site_info_handoff",
        "taxonomy_execution_handoff",
        "schema_manifests",
        "batch_upload",
        "launch_acceptance",
    }:
        return "local_helper_prepares_or_applies_stage"
    if stage_id == "complete":
        return "complete"
    return "blocked_or_unsupported"


def needs_create_site_preflight(stage_id: str, status: dict[str, Any], paths: dict[str, str]) -> bool:
    if stage_id != "create_site_handoff":
        return False
    target_mode = status.get("targetMode")
    if target_mode == "existing_site":
        return False
    return not bool(paths.get("create_site_handoff"))


def required_inputs(stage_id: str) -> list[str]:
    mapping = {
        "source_package": ["valid refined source wiki JSON that can build a complete source-site package"],
        "confirmation": ["user content-intent confirmation text covering the review packet; optional accepted deferrals for contact/domain/tracking decisions"],
        "review_packet": ["refined source wiki JSON that fixes source-wiki-refinement-plan items"],
        "execution_plan": ["valid source package and confirmation record"],
        "artifact_export": ["valid confirmed-site execution plan"],
        "create_site_handoff": [
            "validated confirmed create-site handoff from fresh workspace API session preflight",
            "build the create-site browser runbook before asking for action-time browser submit",
            "after action-time authorization and the create-site gate pass, stop at created-site evidence; do not save or publish content in the same authorization",
        ],
        "created_site_binding": [
            "gated real browser create-site submit or selected-site verification",
            "created-site evidence from the real browser create/select-site stage, or a filled created-site evidence bundle template plus its bundle",
            "pass --created-site-evidence only after the evidence file exists and validates; otherwise pass --created-site-evidence-bundle and --filled-created-site-evidence-template after the browser proof template is filled",
            "if the site needed default-theme bootstrap, pass --default-theme-bootstrap-runbook and --default-theme-bootstrap-evidence before regenerating downstream handoffs",
        ],
        "pages_site_info_handoff": ["created-site evidence and confirmed artifact readiness; regenerate pages/site-info handoff from current site state", "default-theme bootstrap evidence if the prior frontend state was blank or 404"],
        "pages_site_info_execution": [
            "redacted pages/site-info execution evidence after authorized browser work, or a filled pages/site-info evidence bundle",
            "pass --pages-site-info-evidence after the evidence file exists, or pass --pages-site-info-evidence-bundle after filling the generated bundle template",
        ],
        "taxonomy_execution_handoff": ["created-site evidence and confirmed taxonomy plan; regenerate taxonomy handoff from current site state", "default-theme bootstrap evidence if the prior frontend state was blank or 404"],
        "taxonomy_execution": [
            "redacted taxonomy create/map evidence after authorized browser work, or a filled taxonomy evidence bundle",
            "pass --taxonomy-evidence after the evidence file exists, or pass --taxonomy-evidence-bundle after filling the generated bundle template",
        ],
        "schema_capture_handoff": ["current content-type read-only preflight and schema-capture handoff readiness"],
        "schema_manifests": ["draft manifest for one content type", "validated save-capture evidence for that content type"],
        "sample_upload": [
            "schema-verified manifest sample runbook",
            "action-time sample authorization",
            "sample backend/frontend evidence, or a filled manifest sample evidence bundle",
            "pass --sample-evidence after the evidence file exists, or pass --sample-evidence-bundle after filling the generated bundle template",
        ],
        "batch_upload": [
            "schema-verified manifest",
            "validated sample evidence for the same content type as the selected manifest",
            "base run evidence after save capture",
            "batch backend/frontend evidence, or a filled batch upload/publish evidence bundle",
            "when products and posts both have sample evidence, pass --sample-evidence explicitly for the current manifest; do not rely on sample order in source status",
            "pass --batch-evidence after the evidence file exists, or pass --batch-evidence-bundle after filling the generated bundle template and final audit report",
        ],
        "forms_media_settings": [
            "forms/media/settings browser evidence or explicit deferrals; pass --forms-media-settings-evidence after it exists, or pass --forms-media-settings-evidence-bundle after filling the generated bundle template"
        ],
        "launch_acceptance": [
            "launch acceptance evidence after final frontend audit, forms/media/settings, and cleanup",
            "pass --launch-acceptance-inputs-bundle after filling the generated launch acceptance inputs template",
        ],
    }
    return mapping.get(stage_id, [])


def forbidden_actions(stage_id: str) -> list[str]:
    common = [
        "do not infer missing evidence from chat memory",
        "do not skip the currentStage boundary",
        "do not store cookies, headers, server-action ids, private emails, or raw object ids in the skill package",
    ]
    stage_specific = {
        "source_package": ["do not proceed to review or confirmation while the source package is missing or invalid", "do not hand-build package JSON from chat memory"],
        "create_site_handoff": [
            "do not create the site without action-time authorization and create-site gate",
            "do not skip build_create_site_runbook.py or hand-write browser submit steps from memory",
            "do not bundle content upload, theme edits, route binding, domains, tracking, or publish actions into the create-site submit authorization",
        ],
        "confirmation": ["do not treat package review as user confirmation", "do not treat content confirmation as remote mutation authorization"],
        "review_packet": ["do not ask for user confirmation until the review packet exists and validates", "do not manually create a review packet from a non-publication-ready package"],
        "execution_plan": ["do not create a site or export runtime artifacts until the execution plan exists and validates"],
        "artifact_export": ["do not upload exported artifacts; draft manifests remain schemaVerified=false"],
        "created_site_binding": [
            "do not hand-edit siteKey into manifests without created/selected-site evidence",
            "do not run schema-capture preparation until a real created-site evidence file exists or a filled created-site evidence bundle is applied",
            "do not treat create-site handoff readiness as proof that the site was created",
            "do not hand-copy filled bundle fields into make_created_site_evidence.py when the apply helper can consume the bundle",
            "do not continue from stale pre-bootstrap created-site evidence after default-theme bootstrap evidence exists",
        ],
        "pages_site_info_handoff": ["do not save site-info, create pages, publish designs, enable pages, or bind routes from the handoff stage"],
        "pages_site_info_execution": [
            "do not batch upload content before pages/site-info execution evidence passes",
            "do not hand-copy pages/site-info bundle fields when --pages-site-info-evidence-bundle can derive the filled evidence path and handoff",
        ],
        "taxonomy_execution_handoff": ["do not create or map taxonomy terms from labels until action-specific schema/UI proof and authorization exist"],
        "taxonomy_execution": [
            "do not rely on category/tag labels as remote taxonomy ids",
            "do not hand-copy taxonomy bundle fields when --taxonomy-evidence-bundle can derive the filled evidence path and handoff",
        ],
        "schema_capture_handoff": ["do not create probes until content-type read-only preflight and authorization are current"],
        "schema_manifests": ["do not toggle schemaVerified by hand", "do not reuse posts payload for products"],
        "sample_upload": [
            "do not batch upload before one manifest sample passes backend and frontend proof",
            "do not hand-copy sample bundle fields when --sample-evidence-bundle can derive the filled evidence path and manifest",
        ],
        "batch_upload": [
            "do not treat batch proof as launch readiness",
            "do not hand-copy batch bundle fields when --batch-evidence-bundle can derive the filled evidence, manifest, base run evidence, and final audit paths",
        ],
        "forms_media_settings": [
            "do not claim launch readiness while forms/media/settings are unverified or undeferred",
            "do not hand-write source status; apply validated evidence when available",
            "do not hand-copy forms/media/settings bundle fields when --forms-media-settings-evidence-bundle can derive the filled evidence path",
        ],
        "launch_acceptance": [
            "do not mark complete unless launch acceptance passes",
            "do not hand-copy launch acceptance input paths when --launch-acceptance-inputs-bundle can expand the filled inputs",
        ],
    }
    return common + stage_specific.get(stage_id, [])


def build_handoff(args: argparse.Namespace) -> dict[str, Any]:
    status_path = Path(args.status).expanduser().resolve()
    status = load_json(status_path, "source execution status")
    if status.get("kind") != "allincms_source_execution_status":
        raise SystemExit("ERROR: status kind must be allincms_source_execution_status")
    if status.get("remoteMutationsPerformed") is not False:
        raise SystemExit("ERROR: status must be local-only/no remote mutation")
    current_stage = str(status.get("currentStage", "")).strip()
    paths = context_paths(status)
    out_path = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(out_path)
    base = Path(args.output_dir).expanduser().resolve() if args.output_dir else out_path.parent / "next-stage"
    ensure_output_outside_skill(base)
    command = stage_command(current_stage, status, paths, base, args)
    handoff_preflight_blocker = stage_handoff_preflight_blocker(current_stage, paths)
    source_identity = source_identity_context(status)
    submitted_values = created_site_submitted_values_context(status)
    supported = current_stage in SUPPORTED_STAGES
    create_preflight_needed = needs_create_site_preflight(current_stage, status, paths)
    api_session_preflight_required = create_preflight_needed
    browser_only_stage = current_stage in {"create_site_handoff", "schema_capture_handoff", "sample_upload"}
    browser_evidence_stage = current_stage in {
        "created_site_binding",
        "pages_site_info_execution",
        "taxonomy_execution",
        "forms_media_settings",
    }
    browser_work_required = (
        ((browser_only_stage or browser_evidence_stage) and not command and not create_preflight_needed)
        or bool(handoff_preflight_blocker)
    )
    next_preparation_command = ""
    if current_stage == "forms_media_settings" and browser_work_required and not command:
        next_preparation_command = command_prepare_forms_media_settings_bundle(status_path, base)
    if (
        current_stage == "launch_acceptance"
        and not args.launch_acceptance_inputs_bundle
        and not command
    ):
        next_preparation_command = command_prepare_launch_acceptance_inputs_bundle(status_path, base)
    mode = "local_helper_prepares_or_applies_stage" if create_preflight_needed else stage_mode(current_stage, command)
    if handoff_preflight_blocker and not command:
        mode = "browser_action_or_capture_required"
    handoff = {
        "kind": "allincms_source_next_stage_handoff",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "sourceExecutionStatus": str(status_path),
        "currentStage": current_stage,
        "stageStatus": stage(status, current_stage),
        "mode": mode,
        "supported": supported,
        "nextAction": status.get("nextAction", ""),
        "contextPaths": paths,
        "contentQualityReview": status.get("contentQualityReview", {})
        if isinstance(status.get("contentQualityReview"), dict)
        else {},
        "wikiReview": status.get("wikiReview", {})
        if isinstance(status.get("wikiReview"), dict)
        else {},
        "sourceReviewObjectiveCoverage": status.get("sourceReviewObjectiveCoverage", {})
        if isinstance(status.get("sourceReviewObjectiveCoverage"), dict)
        else {},
        **source_identity,
        **submitted_values,
        "requiredInputs": required_inputs(current_stage),
        "localCommand": command,
        "nextPreparationCommand": next_preparation_command,
        "browserWorkRequired": browser_work_required,
        "apiSessionPreflightRequired": api_session_preflight_required,
        "apiSessionPreflight": ({
            "method": "GET",
            "urlTemplate": "https://workspace.laicms.com/sites?_rsc={nonce}",
            "transport": "in_app_browser_same_origin_cdp_fetch",
            "credentials": "include",
            "visibleNavigationAllowed": False,
            "foregroundAllowed": False,
            "loginNavigationGate": "api_result_login_required_only",
        } if api_session_preflight_required else {}),
        "needsCreateSitePreflight": create_preflight_needed,
        "forbiddenActions": forbidden_actions(current_stage),
        "adversarialChecks": [
            "This handoff is local preparation only and does not authorize browser mutation.",
            "Follow currentStage from the source execution status; do not jump to later helpers.",
            "If default-theme bootstrap evidence exists for a blank/404 recovery, apply it to created-site evidence before regenerating pages/site-info, taxonomy, or schema-capture handoffs.",
            "If created-site evidence is still in a filled bundle template, apply the bundle before schema-capture preparation instead of hand-copying fields.",
            "If pages/site-info evidence is still in a filled bundle template, pass the bundle to derive the filled evidence path and handoff before applying pages/site-info proof.",
            "If taxonomy evidence is still in a filled bundle template, pass the bundle to derive the filled evidence path and handoff before applying taxonomy proof.",
            "If manifest sample evidence is still in a filled bundle template, pass the bundle to derive the filled evidence path before applying sample proof.",
            "If batch upload evidence is still in a filled bundle template, pass the batch bundle to derive filled evidence, manifest, base run evidence, and final audit paths before applying batch proof.",
            "For batch preparation, select the sample evidence that matches the selected schema-verified manifest content type; multiple source-status samples are continuity context only.",
            "If forms/media/settings evidence is still in a filled bundle template, pass the bundle to derive the filled evidence path before applying settings proof.",
            "If launch acceptance inputs are still in a filled bundle template, pass the bundle to expand final run evidence, audit, cleanup, closeout, and source-context paths.",
            "For workspace preflight, reuse the in-app browser only as a same-origin API session transport; do not navigate to /sites, foreground a page, or click UI.",
            "Only an API result classified as login_required may open and foreground /sign-in.",
            "If localCommand contains placeholders, gather the named evidence before running it.",
            "Carry contentQualityReview warnings into the next browser/helper stage; review-ready packages can still have non-blocking risks.",
            "Carry wikiReview into the next browser/helper stage so the user-reviewed source wiki remains auditable after site creation.",
            "After the next browser or helper stage, refresh source execution status and generate a new next-stage handoff.",
        ],
    }
    if handoff_preflight_blocker:
        handoff.update(handoff_preflight_blocker)
        issues = handoff_preflight_blocker.get("handoffPreflightIssues")
        if isinstance(issues, list) and issues:
            handoff["requiredInputs"] = list(handoff["requiredInputs"]) + [
                "refresh current-site read-only evidence for " + ", ".join(issues)
            ]
        if current_stage == "taxonomy_execution_handoff":
            handoff["adversarialChecks"].append(
                "Do not regenerate or execute taxonomy actions while the taxonomy handoff reports preflightIssues; refresh the missing read-only products/posts proof first."
            )
        if current_stage == "schema_capture_handoff":
            handoff["adversarialChecks"].append(
                "Do not create product/post probes while the schema-capture handoff reports needs_readonly_content_preflight; refresh the missing list/edit proof first."
            )
    if current_stage == "complete":
        handoff["completionRule"] = "Complete only when launch acceptance status is passed and the status report complete=true."
    elif create_preflight_needed:
        handoff["blocker"] = "Create-site handoff is missing because fresh workspace API session preflight evidence has not been supplied yet."
        handoff["localCommand"] = command_prepare_confirmed_execution(status, paths, base, args)
    elif not supported:
        handoff["blocker"] = "No next-stage handoff recipe exists for this currentStage yet."
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return handoff


def build_default_handoff(
    *,
    status_path: str,
    output_path: str,
    output_dir: str = "",
    **overrides: str,
) -> dict[str, Any]:
    defaults = {
        "status": status_path,
        "output": output_path,
        "output_dir": output_dir,
        "created_site_evidence": "",
        "create_preflight_source_apply_result": "",
        "created_site_evidence_bundle": "",
        "filled_created_site_evidence_template": "",
        "default_theme_bootstrap_runbook": "",
        "default_theme_bootstrap_evidence": "",
        "source_wiki": "",
        "inventory": "",
        "requirements": "",
        "user_confirmation_text": "",
        "target_mode": "new_site",
        "accepted_fields": "",
        "accepted_deferral": [],
        "notes": "",
        "create_preflight": "",
        "create_authorization_output": "",
        "pages_site_info_evidence": "",
        "pages_site_info_evidence_bundle": "",
        "taxonomy_evidence": "",
        "taxonomy_evidence_bundle": "",
        "manifest": "",
        "save_capture_evidence": "",
        "base_run_evidence": "",
        "sample_evidence": "",
        "sample_evidence_bundle": "",
        "existing_sample_evidence": [],
        "existing_upload_readiness": [],
        "batch_evidence": "",
        "batch_evidence_bundle": "",
        "existing_batch_validation": [],
        "frontend_audit_report": "",
        "forms_media_settings_evidence": "",
        "forms_media_settings_evidence_bundle": "",
        "run_evidence": "",
        "module_coverage": "",
        "stage_coverage": "",
        "final_frontend_audit": "",
        "cleanup_evidence": "",
        "round_closeout": "",
        "launch_acceptance_inputs_bundle": "",
        "authorization_dir": "",
        "theme_target": "",
        "site_key": "",
        "frontend_base_url": "",
        "target": "",
        "sample_slug": "",
        "json": False,
    }
    defaults.update({key: value for key, value in overrides.items() if value is not None})
    return build_handoff(argparse.Namespace(**defaults))


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_source_next_stage_handoff":
        issues.append("kind must be allincms_source_next_stage_handoff")
    for key in ("localOnly", "preparedOnly"):
        if handoff.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization"):
        if handoff.get(key) is not False:
            issues.append(f"{key} must be false")
    stage_id = handoff.get("currentStage")
    if not isinstance(stage_id, str) or not stage_id:
        issues.append("currentStage is required")
    if handoff.get("supported") is True and stage_id not in SUPPORTED_STAGES:
        issues.append("supported=true is allowed only for supported stages")
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = handoff.get(key)
        if value is not None and (not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
            issues.append(f"{key} must be a lowercase 64-character sha256 when present")
    submitted_values = handoff.get("createdSiteSubmittedValues")
    if submitted_values is not None:
        if not isinstance(submitted_values, dict):
            issues.append("createdSiteSubmittedValues must be an object when present")
        else:
            for key in ("name", "description"):
                value = submitted_values.get(key)
                if not isinstance(value, str) or not value.strip():
                    issues.append(f"createdSiteSubmittedValues.{key} must be a non-empty string")
    if handoff.get("supported") is True and stage_id == "confirmation":
        command = handoff.get("localCommand")
        if command and handoff.get("mode") != "local_helper_prepares_or_applies_stage":
            issues.append("confirmation with localCommand must use local helper mode")
        if not command and handoff.get("mode") != "user_confirmation_required":
            issues.append("confirmation without user text must remain user_confirmation_required")
    if handoff.get("supported") is True and stage_id not in {
        "confirmation",
        "create_site_handoff",
        "created_site_binding",
        "pages_site_info_execution",
        "taxonomy_execution",
        "taxonomy_execution_handoff",
        "schema_capture_handoff",
        "sample_upload",
        "forms_media_settings",
        "launch_acceptance",
        "complete",
    }:
        command = handoff.get("localCommand")
        if not isinstance(command, str) or not command.strip():
            issues.append("supported local-helper stages must include localCommand")
    if handoff.get("supported") is True and stage_id == "created_site_binding":
        command = handoff.get("localCommand")
        if command and handoff.get("browserWorkRequired") is True:
            issues.append("created_site_binding with localCommand must not require browser work")
        if not command and handoff.get("browserWorkRequired") is not True:
            issues.append("created_site_binding without evidence command must require browser work")
    if handoff.get("supported") is True and stage_id in {
        "pages_site_info_execution",
        "taxonomy_execution",
        "forms_media_settings",
    }:
        command = handoff.get("localCommand")
        if command and handoff.get("browserWorkRequired") is True:
            issues.append(f"{stage_id} with localCommand must not require browser work")
        if not command and handoff.get("browserWorkRequired") is not True:
            issues.append(f"{stage_id} without evidence command must require browser work")
        next_preparation = handoff.get("nextPreparationCommand", "")
        if stage_id == "forms_media_settings" and not command:
            if not isinstance(next_preparation, str) or "prepare_forms_media_settings_evidence_bundle.py" not in next_preparation:
                issues.append("forms_media_settings without evidence must expose the evidence-bundle preparation command")
        elif next_preparation:
            issues.append(f"{stage_id} with local evidence command must not expose nextPreparationCommand")
    if handoff.get("supported") is True and stage_id == "launch_acceptance":
        command = handoff.get("localCommand")
        next_preparation = handoff.get("nextPreparationCommand", "")
        if not command:
            if not isinstance(next_preparation, str) or "prepare_launch_acceptance_inputs_bundle.py" not in next_preparation:
                issues.append("launch_acceptance without filled inputs bundle must expose the launch inputs-bundle preparation command")
        elif next_preparation:
            issues.append("launch_acceptance with localCommand must not expose nextPreparationCommand")
    if handoff.get("supported") is True and stage_id == "taxonomy_execution_handoff":
        command = handoff.get("localCommand")
        preflight_issues = handoff.get("handoffPreflightIssues")
        if isinstance(preflight_issues, list) and preflight_issues:
            if command:
                issues.append("blocked taxonomy_execution_handoff must not include localCommand")
            if handoff.get("browserWorkRequired") is not True:
                issues.append("blocked taxonomy_execution_handoff must require browser/read-only preflight work")
            if handoff.get("mode") != "browser_action_or_capture_required":
                issues.append("blocked taxonomy_execution_handoff must use browser action/capture mode")
            if not isinstance(handoff.get("blocker"), str) or "preflight" not in handoff.get("blocker", ""):
                issues.append("blocked taxonomy_execution_handoff must explain the preflight blocker")
        elif not command:
            issues.append("taxonomy_execution_handoff without preflight blockers must include localCommand")
    if handoff.get("supported") is True and stage_id == "schema_capture_handoff":
        command = handoff.get("localCommand")
        preflight_issues = handoff.get("handoffPreflightIssues")
        blocked_content_types = handoff.get("handoffBlockedContentTypes")
        if isinstance(preflight_issues, list) and preflight_issues:
            if command:
                issues.append("blocked schema_capture_handoff must not include localCommand")
            if handoff.get("browserWorkRequired") is not True:
                issues.append("blocked schema_capture_handoff must require browser/read-only preflight work")
            if handoff.get("mode") != "browser_action_or_capture_required":
                issues.append("blocked schema_capture_handoff must use browser action/capture mode")
            if not isinstance(blocked_content_types, list) or not all(
                isinstance(item, str) and item for item in blocked_content_types
            ):
                issues.append("blocked schema_capture_handoff must expose handoffBlockedContentTypes")
            if not isinstance(handoff.get("blocker"), str) or "preflight" not in handoff.get("blocker", ""):
                issues.append("blocked schema_capture_handoff must explain the preflight blocker")
    if handoff.get("supported") is True and stage_id in {"create_site_handoff", "schema_capture_handoff", "sample_upload"}:
        if stage_id == "create_site_handoff" and handoff.get("needsCreateSitePreflight") is True:
            if handoff.get("browserWorkRequired") is not False:
                issues.append("create_site_handoff needing preflight must not require browser mutation work yet")
            if handoff.get("apiSessionPreflightRequired") is not True:
                issues.append("create_site_handoff needing preflight must require workspace API session preflight")
            api_preflight = handoff.get("apiSessionPreflight")
            if not isinstance(api_preflight, dict):
                issues.append("create_site_handoff needing preflight must expose apiSessionPreflight")
            else:
                if api_preflight.get("method") != "GET":
                    issues.append("workspace API session preflight must use GET")
                if api_preflight.get("urlTemplate") != "https://workspace.laicms.com/sites?_rsc={nonce}":
                    issues.append("workspace API session preflight must expose the RSC URL template")
                if api_preflight.get("transport") != "in_app_browser_same_origin_cdp_fetch":
                    issues.append("workspace API session preflight must use the in-app-browser same-origin CDP fetch transport")
                if api_preflight.get("visibleNavigationAllowed") is not False:
                    issues.append("workspace API session preflight must forbid visible navigation")
                if api_preflight.get("foregroundAllowed") is not False:
                    issues.append("workspace API session preflight must forbid foregrounding")
                if api_preflight.get("loginNavigationGate") != "api_result_login_required_only":
                    issues.append("workspace API session preflight must gate login navigation on login_required")
            if handoff.get("mode") != "local_helper_prepares_or_applies_stage":
                issues.append("create_site_handoff needing preflight must use local helper mode")
            if not isinstance(handoff.get("blocker"), str) or "preflight" not in handoff.get("blocker", ""):
                issues.append("create_site_handoff needing preflight must explain the preflight blocker")
        elif stage_id == "schema_capture_handoff" and isinstance(handoff.get("handoffPreflightIssues"), list) and handoff.get("handoffPreflightIssues"):
            pass
        elif handoff.get("localCommand"):
            if handoff.get("browserWorkRequired") is True:
                issues.append(f"{stage_id} with localCommand must not require browser work")
        elif handoff.get("browserWorkRequired") is not True:
            issues.append("browserWorkRequired must be true for browser-only stages")
    if not isinstance(handoff.get("requiredInputs"), list):
        issues.append("requiredInputs must be an array")
    if not isinstance(handoff.get("forbiddenActions"), list) or not handoff.get("forbiddenActions"):
        issues.append("forbiddenActions must be a non-empty array")
    context = handoff.get("contextPaths")
    if not isinstance(context, dict):
        issues.append("contextPaths must be an object")
    quality = handoff.get("contentQualityReview")
    if quality is not None and not isinstance(quality, dict):
        issues.append("contentQualityReview must be an object when present")
    if isinstance(quality, dict) and quality:
        warnings = quality.get("warnings")
        if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
            issues.append("contentQualityReview.warnings must be an array of strings")
            warnings = []
        if quality.get("reviewRequired") is not bool(warnings):
            issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")
    wiki_review = handoff.get("wikiReview")
    if wiki_review is not None and not isinstance(wiki_review, dict):
        issues.append("wikiReview must be an object when present")
    if isinstance(wiki_review, dict) and wiki_review:
        for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
            if not isinstance(wiki_review.get(key), str) or not wiki_review.get(key, "").strip():
                issues.append(f"wikiReview.{key} is required")
        index = wiki_review.get("sourceWikiMarkdownIndex")
        if isinstance(index, str) and index.strip():
            index_path = Path(index).expanduser()
            if not index_path.exists():
                issues.append("wikiReview.sourceWikiMarkdownIndex must point to an existing Markdown file")
            elif index_path.suffix.lower() != ".md":
                issues.append("wikiReview.sourceWikiMarkdownIndex must be a Markdown .md file")
    stage_status = handoff.get("stageStatus")
    if stage_id != "complete" and (not isinstance(stage_status, dict) or stage_status.get("status") == "passed"):
        issues.append("stageStatus must describe the blocked current stage")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the next handoff from source execution status.")
    parser.add_argument("--status", required=True, help="allincms_source_execution_status JSON")
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-dir", default="", help="Base directory for next-stage helper outputs")
    parser.add_argument("--created-site-evidence", default="")
    parser.add_argument("--create-preflight-source-apply-result", default="")
    parser.add_argument("--created-site-evidence-bundle", default="")
    parser.add_argument("--filled-created-site-evidence-template", default="")
    parser.add_argument("--default-theme-bootstrap-runbook", default="")
    parser.add_argument("--default-theme-bootstrap-evidence", default="")
    parser.add_argument("--source-wiki", default="")
    parser.add_argument("--inventory", default="")
    parser.add_argument("--requirements", default="")
    parser.add_argument("--user-confirmation-text", default="")
    parser.add_argument("--target-mode", choices=["new_site", "existing_site"], default="new_site")
    parser.add_argument("--accepted-fields", default="")
    parser.add_argument("--accepted-deferral", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--create-preflight", default="")
    parser.add_argument("--create-authorization-output", default="")
    parser.add_argument("--pages-site-info-evidence", default="")
    parser.add_argument("--pages-site-info-evidence-bundle", default="")
    parser.add_argument("--taxonomy-evidence", default="")
    parser.add_argument("--taxonomy-evidence-bundle", default="")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--save-capture-evidence", default="")
    parser.add_argument("--base-run-evidence", default="")
    parser.add_argument("--sample-evidence", default="")
    parser.add_argument("--sample-evidence-bundle", default="")
    parser.add_argument("--existing-sample-evidence", action="append", default=[])
    parser.add_argument("--existing-upload-readiness", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-evidence-bundle", default="")
    parser.add_argument("--existing-batch-validation", action="append", default=[])
    parser.add_argument("--frontend-audit-report", default="")
    parser.add_argument("--forms-media-settings-evidence", default="")
    parser.add_argument("--forms-media-settings-evidence-bundle", default="")
    parser.add_argument("--run-evidence", default="")
    parser.add_argument("--module-coverage", default="")
    parser.add_argument("--stage-coverage", default="")
    parser.add_argument("--final-frontend-audit", default="")
    parser.add_argument("--cleanup-evidence", default="")
    parser.add_argument("--round-closeout", default="")
    parser.add_argument("--launch-acceptance-inputs-bundle", default="")
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="")
    parser.add_argument("--site-key", default="")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--sample-slug", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    handoff = build_handoff(args)
    issues = validate_handoff(handoff)
    if issues:
        raise SystemExit("ERROR: generated next-stage handoff invalid:\n- " + "\n- ".join(issues))
    if args.json:
        print(json.dumps(handoff, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source next-stage handoff: {args.output}")
        print(f"currentStage={handoff['currentStage']} mode={handoff['mode']} supported={str(handoff['supported']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
