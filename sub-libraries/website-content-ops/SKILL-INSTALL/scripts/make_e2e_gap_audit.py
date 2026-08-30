#!/usr/bin/env python3
"""Build a local E2E completion-gap audit for an AllinCMS site/content run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any


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


def site_key_from_evidence(evidence: dict[str, Any]) -> str:
    identity = evidence.get("siteIdentity")
    if not isinstance(identity, dict):
        raise ValueError("run evidence must contain siteIdentity")
    site_key = identity.get("siteKey")
    if not isinstance(site_key, str) or not site_key.strip():
        raise ValueError("siteIdentity.siteKey must be a non-empty string")
    return site_key


def frontend_base_from_evidence(evidence: dict[str, Any], site_key: str) -> str:
    identity = evidence.get("siteIdentity")
    if isinstance(identity, dict):
        frontend = identity.get("frontendBaseUrl")
        if isinstance(frontend, str) and frontend.startswith("https://"):
            return frontend
    return f"https://{site_key}.web.allincms.com"


def content_type_from_evidence(evidence: dict[str, Any]) -> str:
    inspection = evidence.get("contentInspection")
    if isinstance(inspection, dict) and isinstance(inspection.get("contentType"), str):
        return inspection["contentType"]
    return ""


def readonly_fields_proven(evidence: dict[str, Any]) -> bool:
    inspection = evidence.get("contentInspection")
    if not isinstance(inspection, dict):
        return False
    columns = inspection.get("listColumns")
    return isinstance(columns, list) and bool(columns)


def upload_blocked(upload_readiness: dict[str, Any]) -> bool:
    return upload_readiness.get("overallStatus") == "blocked"


def ready_stage_ids(queue: dict[str, Any]) -> list[str]:
    stages = queue.get("queue")
    if not isinstance(stages, list):
        return []
    return [str(stage.get("id")) for stage in stages if isinstance(stage, dict) and stage.get("status") == "ready_to_request_authorization"]


def has_stage(queue: dict[str, Any], stage_id: str) -> bool:
    stages = queue.get("queue")
    if not isinstance(stages, list):
        return False
    return any(isinstance(stage, dict) and stage.get("id") == stage_id for stage in stages)


def next_action_from_queue(queue: dict[str, Any]) -> dict[str, str]:
    stages = queue.get("queue")
    if not isinstance(stages, list):
        return {}
    for stage in stages:
        if isinstance(stage, dict) and stage.get("status") == "ready_to_request_authorization":
            return {
                "action": str(stage.get("action", "")),
                "target": str(stage.get("target", "")),
                "stopAfter": str(stage.get("stopAfter", "")),
                "authorizationText": str(stage.get("authorizationText", "")),
            }
    return {}


def build_audit(
    evidence: dict[str, Any],
    upload_readiness: dict[str, Any],
    queue: dict[str, Any],
    *,
    objective: str,
    evidence_path: str,
    upload_readiness_path: str,
    queue_path: str,
    source_input_requirements: dict[str, Any] | None = None,
    source_input_requirements_path: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    if queue.get("kind") != "allincms_browser_stage_authorization_queue":
        raise ValueError("queue.kind must be allincms_browser_stage_authorization_queue")
    if upload_readiness.get("kind") != "allincms_manifest_upload_readiness_report":
        raise ValueError("upload readiness kind must be allincms_manifest_upload_readiness_report")
    if source_input_requirements is not None and source_input_requirements.get("kind") != "allincms_source_input_requirements":
        raise ValueError("source input requirements kind must be allincms_source_input_requirements")
    site_key = site_key_from_evidence(evidence)
    site_creation = evidence.get("siteCreation") if isinstance(evidence.get("siteCreation"), dict) else {}
    site_creation_status = site_creation.get("status", "")
    content_type = content_type_from_evidence(evidence)
    ready_ids = ready_stage_ids(queue)
    next_authorized = next_action_from_queue(queue)
    source_status = "not_supplied"
    source_blockers: list[str] = []
    source_content_types: list[str] = []
    if isinstance(source_input_requirements, dict):
        source_status = str(source_input_requirements.get("overallStatus", ""))
        blockers = source_input_requirements.get("blockedUntil")
        if isinstance(blockers, list):
            source_blockers = [str(item) for item in blockers if str(item).strip()]
        content_types = source_input_requirements.get("contentTypes")
        if isinstance(content_types, dict):
            source_content_types = sorted(str(key) for key in content_types.keys())

    proven: list[dict[str, str]] = []
    if readonly_fields_proven(evidence):
        proven.append(
            {
                "requirement": "inspect current backend content list fields",
                "status": "proven",
                "evidence": f"{content_type or 'content'} list columns present in run evidence",
            }
        )
    if upload_blocked(upload_readiness):
        proven.append(
            {
                "requirement": "prevent upload before schema capture",
                "status": "proven",
                "evidence": "upload readiness overallStatus=blocked",
            }
        )
    if source_status == "blocked":
        proven.append(
            {
                "requirement": "prevent source-material extraction from bypassing field requirements",
                "status": "proven",
                "evidence": f"source input requirements overallStatus=blocked with {len(source_blockers)} blockers",
            }
        )
    if ready_ids:
        proven.append(
            {
                "requirement": "prepare next safe browser action",
                "status": "proven",
                "evidence": "ready stages: " + ",".join(ready_ids),
            }
        )
    if has_stage(queue, "final_frontend_audit"):
        proven.append(
            {
                "requirement": "sequence final frontend audit after batch proof",
                "status": "proven",
                "evidence": "stage queue keeps final_frontend_audit behind batch upload proof",
            }
        )

    not_yet = [
        {
            "requirement": "fresh proof that this run created the site from scratch",
            "status": "not_proven" if site_creation_status != "created_verified" else "proven",
            "reason": (
                "current evidence is existing-site continuation, not created_verified"
                if site_creation_status != "created_verified"
                else "siteCreation.status is created_verified"
            ),
        },
        {
            "requirement": "create a product probe draft",
            "status": "blocked_on_user_authorization" if "products_create_probe" in ready_ids else "not_ready",
            "reason": "remote draft creation needs current user action-time authorization",
        },
        {
            "requirement": "capture products save request and payload template",
            "status": "not_started",
            "reason": "requires authorized product probe and separate save/capture authorization",
        },
        {
            "requirement": "capture posts save request and payload template",
            "status": "not_started",
            "reason": "posts and products schemas must be captured separately",
        },
        {
            "requirement": "sample upload, publish, backend verify, frontend verify, cleanup",
            "status": "not_started",
            "reason": "depends on content-type-specific payload templates and action-specific authorization",
        },
        {
            "requirement": "batch upload/publish source manifests",
            "status": "not_ready",
            "reason": "manifest schema gate is not passed for every content type",
        },
        {
            "requirement": "generate manifests from source materials",
            "status": "blocked" if source_status == "blocked" else "not_proven",
            "reason": (
                f"source input requirements remain blocked for {len(source_blockers)} field/schema decisions"
                if source_status == "blocked"
                else "source input requirements were not supplied to this gap audit"
            ),
        },
        {
            "requirement": "final launch QA",
            "status": "not_ready",
            "reason": "requires published content and frontend audit proof",
        },
    ]

    return {
        "kind": "allincms_e2e_goal_gap_audit",
        "generatedAt": generated_at or now_iso(),
        "objective": objective,
        "remoteMutationsPerformedThisRound": False,
        "site": {
            "siteKey": site_key,
            "backendProductsUrl": f"https://workspace.laicms.com/{site_key}/products",
            "frontendBaseUrl": frontend_base_from_evidence(evidence, site_key),
            "siteCreationProofStatus": (
                "created_verified" if site_creation_status == "created_verified" else "existing-site continuation; not fresh proof of new site creation in this run"
            ),
        },
        "currentEvidence": {
            "readonlyEvidence": evidence_path,
            "uploadReadiness": upload_readiness_path,
            "browserStageQueue": queue_path,
            "sourceInputRequirements": source_input_requirements_path,
        },
        "sourceInputRequirements": {
            "status": source_status,
            "contentTypes": source_content_types,
            "blockedUntilCount": len(source_blockers),
            "topBlockers": source_blockers[:10],
        },
        "proven": proven,
        "notYetProven": not_yet,
        "nextAuthorizedActionNeeded": next_authorized,
        "completionVerdict": {
            "complete": False,
            "reason": (
                "Current evidence is not enough to complete the full site-build/content-upload objective. "
                "Missing proof remains for authorized probe creation, save request capture, sample verification, cleanup, batch upload, and final frontend audit."
            ),
        },
    }


def validate_audit(audit: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if audit.get("kind") != "allincms_e2e_goal_gap_audit":
        errors.append("kind must be allincms_e2e_goal_gap_audit")
    if audit.get("remoteMutationsPerformedThisRound") is not False:
        errors.append("remoteMutationsPerformedThisRound must be false")
    verdict = audit.get("completionVerdict")
    if not isinstance(verdict, dict) or verdict.get("complete") is not False:
        errors.append("completionVerdict.complete must be false for a gap audit")
    if not isinstance(audit.get("proven"), list):
        errors.append("proven must be an array")
    not_yet = audit.get("notYetProven")
    if not isinstance(not_yet, list) or len(not_yet) < 5:
        errors.append("notYetProven must list the remaining required proof")
    next_action = audit.get("nextAuthorizedActionNeeded")
    if not isinstance(next_action, dict):
        errors.append("nextAuthorizedActionNeeded must be an object")
    else:
        if next_action.get("action") == "create_product_probe":
            auth_text = next_action.get("authorizationText")
            if not isinstance(auth_text, str) or "授权 Codex" not in auth_text:
                errors.append("create_product_probe next action must include suggested authorization text")
        elif next_action:
            errors.append("unexpected next authorized action")
    source = audit.get("sourceInputRequirements")
    if not isinstance(source, dict):
        errors.append("sourceInputRequirements must be an object")
    else:
        status = source.get("status")
        if status == "blocked":
            if not isinstance(source.get("blockedUntilCount"), int) or source["blockedUntilCount"] <= 0:
                errors.append("blocked sourceInputRequirements must have a positive blockedUntilCount")
        elif status not in {"not_supplied", "ready_for_source_extraction", "blocked"}:
            errors.append("sourceInputRequirements.status is not recognized")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS E2E completion-gap audit.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--upload-readiness", required=True)
    parser.add_argument("--stage-queue", required=True)
    parser.add_argument("--source-input-requirements", default="")
    parser.add_argument("--objective", default="模拟实操 从创建网站开始，边实操边完善 skill")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        audit = build_audit(
            load_json(Path(args.evidence), "run evidence"),
            load_json(Path(args.upload_readiness), "upload readiness"),
            load_json(Path(args.stage_queue), "stage queue"),
            objective=args.objective,
            evidence_path=args.evidence,
            upload_readiness_path=args.upload_readiness,
            queue_path=args.stage_queue,
            source_input_requirements=(
                load_json(Path(args.source_input_requirements), "source input requirements")
                if args.source_input_requirements
                else None
            ),
            source_input_requirements_path=args.source_input_requirements,
        )
        errors = validate_audit(audit)
        if errors:
            raise ValueError("gap audit validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).expanduser().write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"complete={audit['completionVerdict']['complete']} notYetProven={len(audit['notYetProven'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
