#!/usr/bin/env python3
"""Build a local handoff from created/selected-site bound manifests to schema capture."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from prepare_probe_save_handoff import PLACEHOLDER
from validate_manifest import load_manifest, validate_manifest
from validate_run_evidence import validate as validate_run_evidence
from validate_source_package_confirmation import validate_content_quality_review, validate_wiki_review
from content_goal_coverage_utils import (
    confirmation_decision_matrix_issues,
    created_site_submitted_values_issues,
    source_identity_issues,
)


CONTENT_SPECS = {
    "products": {
        "createAction": "create_product_probe",
        "label": "产品",
        "fields": "name,slug,description,content,coverImage,status",
    },
    "posts": {
        "createAction": "create_post_probe",
        "label": "文章",
        "fields": "title,slug,excerpt,content,coverImage,status",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def manifest_item_count(manifest: dict[str, Any]) -> int:
    items = manifest.get("items")
    return len(items) if isinstance(items, list) else 0


def site_identity(evidence: dict[str, Any]) -> tuple[str, str, str]:
    errors = validate_run_evidence(evidence)
    if errors:
        raise ValueError("created/selected-site evidence is invalid:\n- " + "\n- ".join(errors))
    site_creation = evidence.get("siteCreation") if isinstance(evidence.get("siteCreation"), dict) else {}
    status = site_creation.get("status")
    if status not in {"created_verified", "existing_site_selected"}:
        raise ValueError(
            "site evidence must have siteCreation.status=created_verified or existing_site_selected"
        )
    identity = evidence.get("siteIdentity") if isinstance(evidence.get("siteIdentity"), dict) else {}
    site_key = identity.get("siteKey")
    frontend_base = identity.get("frontendBaseUrl")
    if not isinstance(site_key, str) or not site_key.strip() or site_key.startswith("{"):
        raise ValueError("site evidence must contain a concrete siteIdentity.siteKey")
    if not isinstance(frontend_base, str) or not frontend_base.startswith("https://"):
        raise ValueError("site evidence must contain siteIdentity.frontendBaseUrl")
    return site_key.strip(), frontend_base.rstrip("/"), str(status)


def content_preflight_state(evidence: dict[str, Any], content_type: str, default_evidence_path: str) -> dict[str, Any]:
    preflights = evidence.get("contentTypePreflights")
    if isinstance(preflights, dict) and isinstance(preflights.get(content_type), dict):
        entry = preflights[content_type]
        list_columns = entry.get("listColumns")
        edit_fields = entry.get("editFields")
        source_evidence = entry.get("mergedEvidence") or entry.get("sourceMergedEvidence") or default_evidence_path
        ready = (
            entry.get("readyForCreateProbeGate") is True
            and isinstance(list_columns, list)
            and bool(list_columns)
            and isinstance(edit_fields, list)
            and bool(edit_fields)
        )
        return {
            "contentType": content_type,
            "readyForCreateProbeGate": ready,
            "evidenceContentType": entry.get("contentType", content_type),
            "preflightEvidence": str(source_evidence),
            "sourceReadOnlyEvidence": entry.get("sourceReadOnlyEvidence", ""),
            "fromContentTypePreflights": True,
            "missing": []
            if ready
            else [
                "fresh read-only list columns for this content type",
                "fresh read-only edit/probe field evidence for this content type",
            ],
        }
    inspection = evidence.get("contentInspection") if isinstance(evidence.get("contentInspection"), dict) else {}
    list_columns = inspection.get("listColumns")
    edit_fields = inspection.get("editFields")
    ready = (
        inspection.get("contentType") == content_type
        and isinstance(list_columns, list)
        and bool(list_columns)
        and isinstance(edit_fields, list)
        and bool(edit_fields)
    )
    return {
        "contentType": content_type,
        "readyForCreateProbeGate": ready,
        "evidenceContentType": inspection.get("contentType", ""),
        "preflightEvidence": default_evidence_path,
        "fromContentTypePreflights": False,
        "missing": []
        if ready
        else [
            "fresh read-only list columns for this content type",
            "fresh read-only edit/probe field evidence for this content type",
        ],
    }


def load_bound_manifest(path: str, content_type: str, site_key: str, frontend_base: str) -> dict[str, Any]:
    manifest = load_manifest(Path(path))
    if manifest.get("contentType") != content_type:
        raise ValueError(f"{content_type} manifest contentType mismatch")
    items = manifest.get("items")
    if isinstance(items, list) and not items:
        if manifest.get("siteKey") != site_key:
            raise ValueError(f"{content_type} manifest.siteKey must match created/selected-site evidence")
        if str(manifest.get("frontendBaseUrl", "")).rstrip("/") != frontend_base:
            raise ValueError(f"{content_type} manifest.frontendBaseUrl must match created/selected-site evidence")
        if manifest.get("schemaVerified") is not False:
            raise ValueError(f"{content_type} manifest must remain schemaVerified=false before schema capture")
        return manifest
    errors = validate_manifest(manifest, require_schema_verified=False)
    if errors:
        raise ValueError(f"{content_type} draft manifest failed generic validation:\n- " + "\n- ".join(errors))
    if manifest.get("siteKey") != site_key:
        raise ValueError(f"{content_type} manifest.siteKey must match created/selected-site evidence")
    if str(manifest.get("siteKey", "")).startswith("{"):
        raise ValueError(f"{content_type} manifest.siteKey is still a placeholder")
    if str(manifest.get("frontendBaseUrl", "")).rstrip("/") != frontend_base:
        raise ValueError(f"{content_type} manifest.frontendBaseUrl must match created/selected-site evidence")
    if manifest.get("schemaVerified") is not False:
        raise ValueError(f"{content_type} manifest must remain schemaVerified=false before schema capture")
    for key in ("fieldMapping", "payloadTemplate"):
        value = manifest.get(key)
        if value not in ({}, None):
            raise ValueError(f"{content_type} manifest.{key} must be empty before schema capture")
    return manifest


def auth_command(action: str, site_key: str, target: str, target_type: str, target_identifier: str, fields: str, output: str) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            action,
            "--site-key",
            site_key,
            "--target",
            target,
            "--target-type",
            target_type,
            "--target-identifier",
            target_identifier,
            "--fields-or-files",
            fields,
            "--expected-result",
            "temporary Codex Probe draft opens or appears in the backend list; do not save or publish",
            "--verification-plan",
            "verify probe draft URL or backend row proof, then stop before save",
            "--cleanup-plan",
            "save capture and cleanup require separate authorization",
            "--authorization-source",
            PLACEHOLDER,
            "--output",
            output,
        ]
    )


def gate_command(action: str, preflight: str, authorization: str) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py",
            "--action",
            action,
            "--preflight",
            preflight,
            "--authorization",
            authorization,
        ]
    )


def stage_for_manifest(
    *,
    content_type: str,
    manifest_path: str,
    manifest: dict[str, Any],
    site_key: str,
    frontend_base: str,
    created_site_evidence_path: str,
    authorization_dir: Path,
    output_dir: Path,
    preflight_state: dict[str, Any],
) -> dict[str, Any]:
    spec = CONTENT_SPECS[content_type]
    target = f"https://workspace.laicms.com/{site_key}/{content_type}"
    item_count = manifest_item_count(manifest)
    if item_count <= 0:
        return {
            "contentType": content_type,
            "status": "skipped_no_manifest_items",
            "manifest": manifest_path,
            "itemCount": 0,
            "remoteMutationsPerformed": False,
        }

    auth_output = str(authorization_dir / f"{content_type}-create-probe-authorization.json")
    save_capture_output = str(output_dir / f"{content_type}-save-capture-evidence.json")
    run_evidence_after_save = str(output_dir / f"{content_type}-run-evidence-after-save-capture.json")
    schema_manifest_output = str(output_dir / f"{content_type}-schema-verified-manifest.json")
    sample_runbook_output = str(output_dir / f"{content_type}-manifest-sample-runbook.json")
    sample_evidence_output = str(output_dir / f"{content_type}-manifest-sample-evidence.json")
    sample_validation_output = str(output_dir / f"{content_type}-manifest-sample-validation.json")
    status = "ready_for_create_probe_authorization" if preflight_state["readyForCreateProbeGate"] else "needs_readonly_content_preflight"
    return {
        "contentType": content_type,
        "status": status,
        "manifest": manifest_path,
        "itemCount": item_count,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "target": target,
        "contentPreflight": preflight_state,
        "createProbe": {
            "action": spec["createAction"],
            "authorizationOutput": auth_output,
            "suggestedAuthorizationText": (
                f"授权 Codex 在 {target} 创建一个 Codex Probe - Delete Me {spec['label']}测试草稿，"
                "仅用于捕获创建行为；本次停止条件：probe draft or dialog state is verified; do not save or publish。"
            ),
            "authorizationRecordCommand": auth_command(
                spec["createAction"],
                site_key,
                target,
                content_type,
                "Codex Probe - Delete Me",
                spec["fields"],
                auth_output,
            ),
            "authorizationRecordCommandHasPlaceholder": True,
            "preMutationGateCommand": gate_command(
                spec["createAction"],
                str(preflight_state.get("preflightEvidence") or created_site_evidence_path),
                auth_output,
            ),
            "browserStepsExecutable": False,
        },
        "afterCreateProbe": {
            "next": "prepare_probe_save_handoff.py after the browser captures concrete probe edit URL/create evidence",
            "saveCaptureEvidenceOutput": save_capture_output,
            "runEvidenceAfterSaveCapture": run_evidence_after_save,
        },
        "afterSaveCapture": {
            "applySaveCaptureCommand": shell_join(
                [
                    "python3",
                    "skills/allincms-bulk-content-upload/scripts/apply_save_capture_to_manifest.py",
                    "--manifest",
                    manifest_path,
                    "--save-capture-evidence",
                    save_capture_output,
                    "--base-run-evidence",
                    run_evidence_after_save,
                    "--output",
                    schema_manifest_output,
                ]
            ),
            "validateSchemaManifestCommand": shell_join(
                [
                    "python3",
                    "skills/allincms-bulk-content-upload/scripts/validate_manifest.py",
                    "--require-schema-verified",
                    schema_manifest_output,
                ]
            ),
        },
        "afterSchemaManifest": {
            "buildManifestSampleRunbookCommand": shell_join(
                [
                    "python3",
                    "skills/allincms-bulk-content-upload/scripts/build_manifest_sample_upload_runbook.py",
                    "--manifest",
                    schema_manifest_output,
                    "--target",
                    target,
                    "--authorization-output",
                    str(authorization_dir / f"{content_type}-sample-authorization.json"),
                    "--output",
                    sample_runbook_output,
                ]
            ),
            "sampleEvidenceOutput": sample_evidence_output,
            "validateManifestSampleEvidenceCommand": shell_join(
                [
                    "python3",
                    "skills/allincms-bulk-content-upload/scripts/validate_manifest_sample_upload_evidence.py",
                    sample_evidence_output,
                    "--manifest",
                    schema_manifest_output,
                    "--output",
                    sample_validation_output,
                ]
            ),
        },
        "forbiddenActions": [
            "saving the create-probe draft during create-probe authorization",
            "publishing the probe before save/request capture evidence exists",
            "batch uploading from this draft manifest",
            "reusing this content type schema for a different content type",
            "mutating routes, themes, media, forms, domains, tracking, or site settings in this stage",
        ],
    }


def build_handoff(args: argparse.Namespace) -> dict[str, Any]:
    binding = load_json(Path(args.created_site_binding), "created/selected-site artifact binding")
    evidence = load_json(Path(args.created_site_evidence), "created/selected-site evidence")
    if binding.get("kind") != "allincms_created_site_artifact_binding":
        raise ValueError("created-site binding kind mismatch")
    if binding.get("remoteMutationsPerformed") is not False:
        raise ValueError("created-site binding must not have performed remote mutations")
    if binding.get("schemaVerified") is not False:
        raise ValueError("created-site binding schemaVerified must be false")
    site_key, frontend_base, site_creation_status = site_identity(evidence)
    site_binding_mode = binding.get("siteBindingMode")
    if site_binding_mode not in {"created_site", "existing_site"}:
        raise ValueError("created-site binding siteBindingMode must be created_site or existing_site")
    if site_binding_mode == "created_site" and site_creation_status != "created_verified":
        raise ValueError("created_site binding must use created_verified evidence")
    if site_binding_mode == "existing_site" and site_creation_status != "existing_site_selected":
        raise ValueError("existing_site binding must use existing_site_selected evidence")
    if binding.get("siteKey") != site_key:
        raise ValueError("created-site binding siteKey must match created/selected-site evidence")
    if str(binding.get("frontendBaseUrl", "")).rstrip("/") != frontend_base:
        raise ValueError("created-site binding frontendBaseUrl must match created/selected-site evidence")
    artifacts = binding.get("boundArtifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("created-site binding boundArtifacts must be an object")
    quality_issues: list[str] = []
    validate_content_quality_review(binding.get("contentQualityReview"), quality_issues)
    if quality_issues:
        raise ValueError("created-site binding contentQualityReview is invalid:\n- " + "\n- ".join(quality_issues))
    wiki_issues: list[str] = []
    validate_wiki_review(binding.get("wikiReview"), wiki_issues)
    if wiki_issues:
        raise ValueError("created-site binding wikiReview is invalid:\n- " + "\n- ".join(wiki_issues))
    matrix_issues = confirmation_decision_matrix_issues(binding.get("confirmationDecisionMatrix"))
    if matrix_issues:
        raise ValueError("created-site binding confirmationDecisionMatrix is invalid:\n- " + "\n- ".join(matrix_issues))

    output_dir = Path(args.output_dir)
    authorization_dir = Path(args.authorization_dir or output_dir / "authorizations")
    stages: list[dict[str, Any]] = []
    for content_type in ("products", "posts"):
        manifest_path = artifacts.get(f"{content_type}Manifest")
        if not isinstance(manifest_path, str) or not manifest_path:
            raise ValueError(f"created-site binding missing boundArtifacts.{content_type}Manifest")
        manifest = load_bound_manifest(manifest_path, content_type, site_key, frontend_base)
        stages.append(
            stage_for_manifest(
                content_type=content_type,
                manifest_path=manifest_path,
                manifest=manifest,
                site_key=site_key,
                frontend_base=frontend_base,
                created_site_evidence_path=args.created_site_evidence,
                authorization_dir=authorization_dir,
                output_dir=output_dir,
                preflight_state=content_preflight_state(evidence, content_type, args.created_site_evidence),
            )
        )
    ready_count = sum(1 for stage in stages if stage.get("status") == "ready_for_create_probe_authorization")
    blocked_count = sum(1 for stage in stages if stage.get("status") == "needs_readonly_content_preflight")
    skipped_count = sum(1 for stage in stages if stage.get("status") == "skipped_no_manifest_items")
    return {
        "kind": "allincms_schema_capture_handoff",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "createdSiteBinding": args.created_site_binding,
        "createdSiteEvidence": args.created_site_evidence,
        "siteBindingMode": site_binding_mode,
        "siteCreationStatus": site_creation_status,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "contentTypes": [stage["contentType"] for stage in stages if stage.get("itemCount", 0) > 0],
        "sourcePackageSha256": binding.get("sourcePackageSha256"),
        "sourceReviewPacketSha256": binding.get("sourceReviewPacketSha256"),
        **({"createdSiteSubmittedValues": binding.get("createdSiteSubmittedValues")} if binding.get("createdSiteSubmittedValues") else {}),
        "contentQualityReview": binding.get("contentQualityReview", {}),
        "wikiReview": binding.get("wikiReview", {}),
        "confirmationDecisionMatrix": binding.get("confirmationDecisionMatrix", []),
        "readyForCreateProbeAuthorizationCount": ready_count,
        "blockedByReadonlyPreflightCount": blocked_count,
        "skippedCount": skipped_count,
        "overallStatus": "ready_for_schema_capture" if ready_count and not blocked_count else "needs_readonly_content_preflight",
        "stages": stages,
        "rule": (
            "This handoff prepares schema-capture actions only. It does not create probes, save, publish, "
            "apply payload templates, sample upload, batch upload, or authorize browser mutations."
        ),
    }


def validate_handoff(handoff: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if handoff.get("kind") != "allincms_schema_capture_handoff":
        issues.append("kind must be allincms_schema_capture_handoff")
    for key in ("localOnly", "preparedOnly"):
        if handoff.get(key) is not True:
            issues.append(f"{key} must be true")
    if handoff.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if handoff.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    stages = handoff.get("stages")
    validate_content_quality_review(handoff.get("contentQualityReview"), issues)
    validate_wiki_review(handoff.get("wikiReview"), issues)
    issues.extend(confirmation_decision_matrix_issues(handoff.get("confirmationDecisionMatrix")))
    identity = (
        {key: handoff.get(key) for key in ("sourcePackageSha256", "sourceReviewPacketSha256")}
        if any(key in handoff for key in ("sourcePackageSha256", "sourceReviewPacketSha256"))
        else None
    )
    issues.extend(source_identity_issues(identity))
    if "createdSiteSubmittedValues" in handoff:
        issues.extend(created_site_submitted_values_issues(handoff.get("createdSiteSubmittedValues")))
    if not isinstance(stages, list) or not stages:
        issues.append("stages must be a non-empty array")
    else:
        for stage in stages:
            if not isinstance(stage, dict):
                issues.append("each stage must be an object")
                continue
            status = stage.get("status")
            if status not in {"ready_for_create_probe_authorization", "needs_readonly_content_preflight", "skipped_no_manifest_items"}:
                issues.append(f"{stage.get('contentType')}: invalid status {status}")
            if status == "ready_for_create_probe_authorization":
                create_probe = stage.get("createProbe")
                if not isinstance(create_probe, dict):
                    issues.append(f"{stage.get('contentType')}: createProbe is required")
                else:
                    command = create_probe.get("authorizationRecordCommand")
                    if not isinstance(command, str) or PLACEHOLDER not in command:
                        issues.append(f"{stage.get('contentType')}: authorization command must retain placeholder")
                    gate = create_probe.get("preMutationGateCommand")
                    if not isinstance(gate, str) or "--action create_" not in gate:
                        issues.append(f"{stage.get('contentType')}: create-probe pre-mutation gate command is required")
                    if create_probe.get("browserStepsExecutable") is not False:
                        issues.append(f"{stage.get('contentType')}: browserStepsExecutable must be false")
            if stage.get("itemCount", 0) > 0 and stage.get("manifest"):
                manifest_path = Path(str(stage["manifest"]))
                if not manifest_path.exists():
                    issues.append(f"{stage.get('contentType')}: manifest path must exist")
    if not isinstance(handoff.get("rule"), str) or "does not create probes" not in handoff["rule"]:
        issues.append("rule must state no probes are created")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build schema-capture handoff for created-site bound manifests.")
    parser.add_argument("--created-site-binding", required=True)
    parser.add_argument("--created-site-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        handoff = build_handoff(args)
        issues = validate_handoff(handoff)
        if issues:
            raise ValueError("schema-capture handoff validation failed:\n- " + "\n- ".join(issues))
    except (SystemExit, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    write_json(output, handoff)
    print(f"Wrote schema-capture handoff: {output}")
    print(f"overallStatus={handoff['overallStatus']} ready={handoff['readyForCreateProbeAuthorizationCount']} blocked={handoff['blockedByReadonlyPreflightCount']}")
    if args.json:
        print(json.dumps(handoff, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
