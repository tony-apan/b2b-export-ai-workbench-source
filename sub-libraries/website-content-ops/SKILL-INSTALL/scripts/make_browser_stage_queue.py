#!/usr/bin/env python3
"""Build a local staged browser authorization queue for an AllinCMS content run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any


PROBE_NAME = "Codex Probe - Delete Me"


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


def target_from_readiness(readiness: dict[str, Any]) -> str:
    target = readiness.get("target")
    if not isinstance(target, str) or not target.startswith("https://workspace.laicms.com/"):
        raise ValueError("readiness.target must be a workspace.laicms.com URL")
    return target


def site_key_from_target(target: str) -> str:
    parts = [part for part in target.split("workspace.laicms.com/", 1)[-1].split("/") if part]
    if not parts:
        raise ValueError("target URL does not contain a site key path segment")
    site_key = parts[0]
    if not site_key or "{" in site_key or "}" in site_key:
        raise ValueError("target URL must contain a concrete site key")
    return site_key


def frontend_base_from_gap(gap_audit: dict[str, Any] | None, site_key: str) -> str:
    if isinstance(gap_audit, dict):
        site = gap_audit.get("site")
        if isinstance(site, dict):
            frontend = site.get("frontendBaseUrl")
            if isinstance(frontend, str) and frontend.startswith("https://"):
                return frontend
    return f"https://{site_key}.web.allincms.com"


def stage(
    number: int,
    stage_id: str,
    status: str,
    action: str,
    target: str,
    authorization_needed: str,
    required_proof: list[str],
    stop_after: str,
    *,
    authorization_text: str = "",
    preflight: str = "",
) -> dict[str, Any]:
    item = {
        "stage": number,
        "id": stage_id,
        "status": status,
        "action": action,
        "target": target,
        "authorizationNeeded": authorization_needed,
        "requiredProofAfterAction": required_proof,
        "stopAfter": stop_after,
    }
    if authorization_text:
        item["authorizationText"] = authorization_text
    if preflight:
        item["preflight"] = preflight
    return item


def build_queue(
    readiness: dict[str, Any],
    upload_readiness: dict[str, Any],
    *,
    readiness_path: str,
    upload_readiness_path: str,
    gap_audit: dict[str, Any] | None = None,
    gap_audit_path: str = "",
    products_manifest: str = "",
    posts_manifest: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    if readiness.get("kind") != "allincms_next_browser_action_handoff_readiness":
        raise ValueError("readiness.kind must be allincms_next_browser_action_handoff_readiness")
    if upload_readiness.get("kind") != "allincms_manifest_upload_readiness_report":
        raise ValueError("upload readiness kind must be allincms_manifest_upload_readiness_report")

    target = target_from_readiness(readiness)
    site_key = site_key_from_target(target)
    action = readiness.get("action")
    if not isinstance(action, dict):
        raise ValueError("readiness.action must be an object")
    authorization_action = action.get("authorizationAction")
    if authorization_action != "create_product_probe":
        raise ValueError("this queue currently starts from create_product_probe readiness")
    if readiness.get("status") not in {"ready_to_request_authorization", "blocked_refresh_readonly_evidence"}:
        raise ValueError("readiness.status is not recognized")

    preflight = readiness.get("preflight")
    preflight_path = preflight if isinstance(preflight, str) else ""
    frontend_base = frontend_base_from_gap(gap_audit, site_key)
    posts_target = target.rsplit("/", 1)[0] + "/posts"
    upload_overall = upload_readiness.get("overallStatus")
    schema_status = "waiting_for_payload_templates"
    if upload_overall == "ready_for_sample_upload":
        schema_status = "ready_after_sample_proof_review"
    elif upload_overall == "blocked":
        schema_status = "waiting_for_stage_2_and_stage_6_payload_templates"

    first_status = str(readiness.get("status"))
    first_authorization = (
        "ask user for exact current action-time authorization"
        if first_status == "ready_to_request_authorization"
        else "refresh read-only evidence and rebuild handoff before asking for authorization"
    )
    suggested_text = ""
    source_handoff = readiness.get("handoff")
    if isinstance(gap_audit, dict):
        next_needed = gap_audit.get("nextAuthorizedActionNeeded")
        if isinstance(next_needed, dict) and isinstance(next_needed.get("authorizationText"), str):
            suggested_text = next_needed["authorizationText"]
    if not suggested_text and first_status == "ready_to_request_authorization":
        suggested_text = (
            f"授权 Codex 在 {target} 创建一个 {PROBE_NAME} 产品测试草稿，仅用于捕获创建行为；"
            "本次停止条件：probe draft or dialog state is verified; do not save or publish in the same authorization。"
        )

    queue = [
        stage(
            1,
            "products_create_probe",
            first_status,
            "create_product_probe",
            target,
            first_authorization,
            [
                "whether clicking create opens a dialog or immediately creates a draft",
                "probe draft backend URL or dialog state",
                "no save, publish, upload, delete, or batch operation performed",
            ],
            "probe draft or dialog state is verified; do not save or publish in the same authorization",
            authorization_text=suggested_text,
            preflight=preflight_path,
        ),
        stage(
            2,
            "products_save_request_capture",
            "waiting_for_stage_1_proof",
            "save_probe",
            "{productProbeEditUrl}",
            "fresh user authorization naming save request capture, product probe, exact edit URL, requestCapture, payloadShape, persistedVerified",
            [
                "request URL, method, redacted volatile header names, payload keys/shape",
                "product fieldMapping and payloadTemplate",
                "backend persisted state confirmed",
            ],
            "save request and backend persistence are captured; do not publish or batch upload",
        ),
        stage(
            3,
            "products_publish_sample_verify",
            "waiting_for_stage_2_schema",
            "publish_probe",
            "{productProbeEditUrl}",
            "fresh user authorization naming product probe publish and frontend verification",
            [
                "backend status is published",
                "frontend /products/{slug} returns expected status",
                "title/name, description, cover, body render without raw Markdown residue",
            ],
            "sample backend and frontend verification are captured; do not clean up or batch upload",
        ),
        stage(
            4,
            "products_cleanup_probe",
            "waiting_for_stage_3_proof",
            "cleanup_probe",
            "{productProbeEditUrl}",
            "fresh user authorization naming cleanup/delete/unpublish of the exact product probe",
            [
                "probe removed or unpublished in backend",
                "frontend probe URL no longer renders published content",
            ],
            "cleanup backend and frontend proof is captured",
        ),
        stage(
            5,
            "posts_create_probe",
            "waiting_for_products_probe_lifecycle_or_user_prioritization",
            "create_post_probe",
            posts_target,
            "fresh user authorization naming post probe draft creation and stop condition",
            [
                "post probe draft or dialog state",
                "no save or publish in same authorization",
            ],
            "probe draft or dialog state is verified; do not save or publish",
        ),
        stage(
            6,
            "posts_save_request_capture",
            "waiting_for_posts_probe",
            "save_probe",
            "{postProbeEditUrl}",
            "fresh user authorization naming post save request capture",
            [
                "post fieldMapping and payloadTemplate",
                "backend persisted state confirmed",
            ],
            "save request and backend persistence are captured; do not publish or batch upload",
        ),
        stage(
            7,
            "posts_publish_sample_verify_cleanup",
            "waiting_for_posts_schema",
            "publish_probe_then_cleanup_with_separate_authorizations",
            "{postProbeEditUrl}",
            "publish and cleanup must remain separate action-time authorizations",
            [
                "post frontend detail renders correctly",
                "probe cleanup backend/frontend proof",
            ],
            "post sample verification and cleanup are captured",
        ),
        stage(
            8,
            "schema_gate_products_posts",
            schema_status,
            "local_schema_gate",
            " and ".join(path for path in (products_manifest, posts_manifest) if path) or "products and posts manifests",
            "none; local validation only",
            [
                "schemaVerified=true for each content type",
                "fieldMapping and payloadTemplate filled from current-site request captures",
                "validate_manifest.py --require-schema-verified passes for both manifests",
            ],
            "schema gate passes locally; do not upload yet",
        ),
        stage(
            9,
            "batch_upload_publish",
            "waiting_for_schema_gate_and_user_authorization",
            "batch_upload_publish",
            f"{target} and {posts_target}",
            "fresh user authorization naming batch upload/publish, content counts, and progress log requirement",
            [
                "progress log for each slug",
                "backend created/updated/published status",
                "duplicate slug handling",
                "failure list if any",
            ],
            "batch progress log and backend verification are captured",
        ),
        stage(
            10,
            "final_frontend_audit",
            "waiting_for_batch_upload_publish",
            "final_frontend_audit",
            frontend_base,
            "none for read-only frontend audit",
            [
                "product and post list/detail URLs audited",
                "covers, descriptions, body content, status, and raw Markdown residue checked",
                "frontend list page left open",
            ],
            "final audit report and launch readiness summary are recorded",
        ),
    ]

    return {
        "kind": "allincms_browser_stage_authorization_queue",
        "generatedAt": generated_at or now_iso(),
        "siteKey": site_key,
        "remoteMutationsPerformed": False,
        "rule": (
            "Each queued mutation requires fresh current-user action-time authorization, "
            "a matching authorization record, a pre-mutation gate, and stop-after proof before moving to the next stage."
        ),
        "sourceArtifacts": {
            "readiness": readiness_path,
            "handoff": str(source_handoff) if isinstance(source_handoff, str) else "",
            "preflight": preflight_path,
            "uploadReadiness": upload_readiness_path,
            "gapAudit": gap_audit_path,
            "productsManifest": products_manifest,
            "postsManifest": posts_manifest,
        },
        "queue": queue,
        "currentBlockingCondition": (
            "No current user action-time authorization for stage 1 product probe creation."
            if first_status == "ready_to_request_authorization"
            else "Read-only evidence must be refreshed before requesting product probe authorization."
        ),
        "completionVerdict": {
            "complete": False,
            "reason": (
                "Only stage 1 is ready to request authorization. No remote mutation has been authorized or performed, "
                "and no save schema, sample verification, cleanup, batch upload, or final frontend audit proof exists yet."
            ),
        },
    }


def validate_queue(queue: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if queue.get("kind") != "allincms_browser_stage_authorization_queue":
        errors.append("kind must be allincms_browser_stage_authorization_queue")
    if queue.get("remoteMutationsPerformed") is not False:
        errors.append("remoteMutationsPerformed must be false")
    if not isinstance(queue.get("siteKey"), str) or not queue["siteKey"].strip():
        errors.append("siteKey must be a non-empty string")
    stages = queue.get("queue")
    if not isinstance(stages, list) or len(stages) != 10:
        errors.append("queue must contain exactly 10 stages")
        return errors
    expected_ids = [
        "products_create_probe",
        "products_save_request_capture",
        "products_publish_sample_verify",
        "products_cleanup_probe",
        "posts_create_probe",
        "posts_save_request_capture",
        "posts_publish_sample_verify_cleanup",
        "schema_gate_products_posts",
        "batch_upload_publish",
        "final_frontend_audit",
    ]
    ids = [stage.get("id") if isinstance(stage, dict) else None for stage in stages]
    if ids != expected_ids:
        errors.append("queue stage ids are not in the expected order")
    ready = [stage for stage in stages if isinstance(stage, dict) and stage.get("status") == "ready_to_request_authorization"]
    if len(ready) > 1:
        errors.append("at most one stage may be ready_to_request_authorization")
    if not ready and stages[0].get("status") == "ready_to_request_authorization":
        errors.append("internal ready stage mismatch")
    for index, item in enumerate(stages, start=1):
        if not isinstance(item, dict):
            errors.append(f"queue[{index - 1}] must be an object")
            continue
        if item.get("stage") != index:
            errors.append(f"queue[{index - 1}].stage must be {index}")
        for key in ("id", "status", "action", "target", "authorizationNeeded", "stopAfter"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{item.get('id', 'stage')}:{key} must be a non-empty string")
        proof = item.get("requiredProofAfterAction")
        if not isinstance(proof, list) or not proof or not all(isinstance(entry, str) and entry.strip() for entry in proof):
            errors.append(f"{item.get('id', 'stage')}: requiredProofAfterAction must be a non-empty string array")
    first = stages[0]
    if first.get("status") == "ready_to_request_authorization":
        auth_text = first.get("authorizationText")
        if not isinstance(auth_text, str) or "授权 Codex" not in auth_text or "do not save or publish" not in auth_text:
            errors.append("ready first stage must include exact suggested authorization text and stop condition")
    batch = stages[8]
    if batch.get("status") == "ready_to_request_authorization":
        errors.append("batch stage must not be ready before schema/sample proof")
    final = stages[9]
    if "none" not in str(final.get("authorizationNeeded", "")).lower():
        errors.append("final frontend audit must be read-only/no authorization")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a staged AllinCMS browser authorization queue.")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--upload-readiness", required=True)
    parser.add_argument("--gap-audit", default="")
    parser.add_argument("--products-manifest", default="")
    parser.add_argument("--posts-manifest", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        gap = load_json(Path(args.gap_audit), "gap audit") if args.gap_audit else None
        queue = build_queue(
            load_json(Path(args.readiness), "handoff readiness"),
            load_json(Path(args.upload_readiness), "upload readiness"),
            readiness_path=args.readiness,
            upload_readiness_path=args.upload_readiness,
            gap_audit=gap,
            gap_audit_path=args.gap_audit,
            products_manifest=args.products_manifest,
            posts_manifest=args.posts_manifest,
        )
        errors = validate_queue(queue)
        if errors:
            raise ValueError("queue validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).expanduser().write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = [item["id"] for item in queue["queue"] if item["status"] == "ready_to_request_authorization"]
    print(f"Wrote {args.output}")
    print(f"queueStages={len(queue['queue'])} ready={','.join(ready) if ready else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
