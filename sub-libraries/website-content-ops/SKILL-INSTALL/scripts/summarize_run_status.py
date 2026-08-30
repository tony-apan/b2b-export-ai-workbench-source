#!/usr/bin/env python3
"""Summarize current AllinCMS run evidence without overstating completion."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from typing import Any

from validate_run_evidence import validate as validate_run_evidence


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("run evidence must be a JSON object")
    return data


OPTIONAL_STATIC_LAUNCH_PATHS = ("/home", "/solutions", "/about-us", "/contact-us")
CONTENT_LIST_PATHS = {
    "products": "/products",
    "posts": "/posts",
}
DETAIL_ROUTE_PATTERNS = {
    "products": "/products/{slug}",
    "posts": "/posts/{slug}",
}
CONTENT_TYPE_META = {
    "products": {
        "module": "products",
        "zh": "产品",
        "english": "product",
        "createAction": "create_product_probe",
        "createFields": "name,slug,description,content,media",
        "saveFields": "requestCapture,payloadShape,persistedVerified",
        "publishFields": "publishStatus,frontendVerified",
        "cleanupFields": "cleanedCandidates,backendVerified,frontendVerified",
    },
    "posts": {
        "module": "posts",
        "zh": "文章",
        "english": "post",
        "createAction": "create_post_probe",
        "createFields": "title,slug,excerpt,content,coverImage",
        "saveFields": "requestCapture,payloadShape,persistedVerified",
        "publishFields": "publishStatus,frontendVerified",
        "cleanupFields": "cleanedCandidates,backendVerified,frontendVerified",
    },
    "forms": {
        "module": "forms",
        "zh": "表单",
        "english": "form",
        "createAction": "create_form_probe",
        "createFields": "name,slug,description,fields",
        "saveFields": "requestCapture,payloadShape,persistedVerified",
        "cleanupFields": "cleanedCandidates,backendVerified,frontendVerified",
    },
}
REQUIRED_COMPLETION_PROOF = (
    "site_identity_verified",
    "setup_pages_read_only_inspected",
    "static_frontend_routes_render",
    "request_capture_persisted_verified",
    "sample_backend_frontend_verified",
    "cleanup_completed",
)
SITE_SOURCE_PROOF = ("site_created_and_verified", "existing_site_selected")
DEFAULT_MUTATION_EVIDENCE_MAX_AGE_MINUTES = 30


def parse_generated_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def freshness_status(
    data: dict[str, Any],
    max_age_minutes: int = DEFAULT_MUTATION_EVIDENCE_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = parse_generated_at(data.get("generatedAt"))
    if generated_at is None:
        return {
            "generatedAt": data.get("generatedAt", ""),
            "maxAgeMinutes": max_age_minutes,
            "freshForMutation": False,
            "reason": "missing_or_invalid_generatedAt",
        }
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age = now_utc - generated_at
    if age < timedelta(0):
        return {
            "generatedAt": generated_at.isoformat(),
            "maxAgeMinutes": max_age_minutes,
            "freshForMutation": False,
            "reason": "generatedAt_in_future",
        }
    age_minutes = age.total_seconds() / 60
    return {
        "generatedAt": generated_at.isoformat(),
        "maxAgeMinutes": max_age_minutes,
        "ageMinutes": round(age_minutes, 2),
        "freshForMutation": age <= timedelta(minutes=max_age_minutes),
        "reason": "fresh" if age <= timedelta(minutes=max_age_minutes) else "stale",
    }


def frontend_static_ok(frontend: dict[str, Any], content_type: str) -> bool:
    if frontend.get("checked") is not True or frontend.get("blockingIssues"):
        return False
    statuses = frontend.get("expectedStatuses")
    if not isinstance(statuses, dict):
        return False
    required_paths = ["/"]
    content_list_path = CONTENT_LIST_PATHS.get(content_type)
    if content_list_path:
        required_paths.append(content_list_path)
    if not all(statuses.get(path) == 200 for path in required_paths):
        return False
    return all(statuses.get(path) == 200 for path in OPTIONAL_STATIC_LAUNCH_PATHS if path in statuses)


def detail_routes_absent(frontend: dict[str, Any], content_type: str) -> bool:
    statuses = frontend.get("expectedStatuses")
    if not isinstance(statuses, dict):
        return False
    expected_pattern = DETAIL_ROUTE_PATTERNS.get(content_type)
    if expected_pattern:
        return statuses.get(expected_pattern) == 404
    return any(statuses.get(pattern) == 404 for pattern in DETAIL_ROUTE_PATTERNS.values())


def launch_readiness_ok(readiness: dict[str, Any]) -> bool:
    return (
        readiness.get("checked") is True
        and readiness.get("themeActive") is True
        and readiness.get("pagesPublished") is True
        and readiness.get("pagesEnabled") is True
        and readiness.get("routesBound") is True
        and readiness.get("frontendHttpOk") is True
        and readiness.get("frontendDomVerified") is True
        and not readiness.get("blockingIssues")
    )


def workspace_module_url(site_key: str, content_type: str) -> str:
    meta = CONTENT_TYPE_META.get(content_type, {})
    module = meta.get("module", content_type)
    return f"https://workspace.laicms.com/{site_key}/{module}"


def safe_backend_target(site_key: str, content_type: str, *candidates: object) -> str:
    base = workspace_module_url(site_key, content_type)
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.startswith(base):
            return candidate
    return base


def probe_identifier(content_type: str) -> str:
    meta = CONTENT_TYPE_META.get(content_type, {})
    english_type = meta.get("english", content_type.rstrip("s") or "content")
    return f"Codex Probe - Delete Me {english_type} draft"


def mutation_action_details(
    action: str,
    site_key: str,
    content_type: str,
    target: str,
    fields: str,
    evidence_path_hint: str,
    expected_result: str,
    verification_plan: str,
    cleanup_plan: str,
    authorization_text: str,
) -> dict[str, str]:
    if not site_key or content_type not in CONTENT_TYPE_META:
        return {}
    auth_path = f"~/allincms-projects/allincms-{site_key}-{content_type}-{action.replace('_', '-')}-authorization.json"
    make_authorization_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        f"--action {action} "
        f"--site-key {site_key} "
        f"--target {target} "
        f"--target-type {content_type} "
        f"--target-identifier '{probe_identifier(content_type)}' "
        f"--fields-or-files '{fields}' "
        f"--expected-result '{expected_result}' "
        f"--verification-plan '{verification_plan}' "
        f"--cleanup-plan '{cleanup_plan}' "
        f"--authorization-source '<paste current user authorization text here>' "
        f"--output {auth_path}"
    )
    gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        f"--action {action} "
        f"--preflight {evidence_path_hint} "
        f"--authorization {auth_path}"
    )
    return {
        "action": action,
        "target": target,
        "authorizationText": authorization_text,
        "authorizationRecordCommand": make_authorization_command,
        "preMutationGateCommand": gate_command,
    }


def probe_action_details(site_key: str, content_type: str, evidence_path_hint: str) -> dict[str, str]:
    meta = CONTENT_TYPE_META.get(content_type)
    if not site_key or not meta:
        return {}
    action = str(meta["createAction"])
    zh_type = str(meta["zh"])
    english_type = str(meta["english"])
    fields = str(meta["createFields"])
    target = workspace_module_url(site_key, content_type)
    auth_path = f"~/allincms-projects/allincms-{site_key}-{content_type}-probe-authorization.json"
    authorization_text = (
        f"授权 Codex 在 {target} 创建一个 Codex Probe - Delete Me {zh_type}草稿，"
        f"用于捕获{zh_type}字段和保存请求；本次只允许创建 probe 草稿，不发布、不删除、不批量上传，"
        "保存和清理另行授权。"
    )
    make_authorization_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        f"--action {action} "
        f"--site-key {site_key} "
        f"--target {target} "
        f"--target-type {content_type} "
        f"--target-identifier '{probe_identifier(content_type)}' "
        f"--fields-or-files '{fields}' "
        f"--expected-result 'temporary {english_type} probe draft opens for request capture' "
        f"--verification-plan 'verify backend {english_type} draft and capture save request before any publish' "
        "--cleanup-plan 'no automatic cleanup; request separate cleanup authorization' "
        f"--authorization-source '<paste current user authorization text here>' "
        f"--output {auth_path}"
    )
    gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        f"--action {action} "
        f"--preflight {evidence_path_hint} "
        f"--authorization {auth_path}"
    )
    return {
        "action": action,
        "target": target,
        "authorizationText": authorization_text,
        "authorizationRecordCommand": make_authorization_command,
        "preMutationGateCommand": gate_command,
    }


def save_probe_action_details(
    site_key: str,
    content_type: str,
    target: str,
    evidence_path_hint: str,
) -> dict[str, str]:
    meta = CONTENT_TYPE_META.get(content_type)
    if not meta or "saveFields" not in meta:
        return {}
    zh_type = str(meta["zh"])
    english_type = str(meta["english"])
    authorization_text = (
        f"授权 Codex 在 {target} 保存 Codex Probe - Delete Me {zh_type}草稿，"
        f"用于捕获{zh_type}真实保存请求、记录 payload 结构，并验证后台确实持久化；"
        "本次只允许保存和捕获请求，不发布、不删除、不批量上传，发布和清理另行授权。"
    )
    return mutation_action_details(
        "save_probe",
        site_key,
        content_type,
        target,
        str(meta["saveFields"]),
        evidence_path_hint,
        f"{english_type} probe save request captured and backend persistence verified",
        "capture save request, verify backend persisted state, and do not publish",
        "no automatic cleanup; request separate cleanup authorization",
        authorization_text,
    )


def publish_probe_action_details(
    site_key: str,
    content_type: str,
    target: str,
    evidence_path_hint: str,
) -> dict[str, str]:
    meta = CONTENT_TYPE_META.get(content_type)
    if not meta or "publishFields" not in meta:
        return {}
    zh_type = str(meta["zh"])
    english_type = str(meta["english"])
    authorization_text = (
        f"授权 Codex 在 {target} 发布 Codex Probe - Delete Me {zh_type}草稿，"
        f"用于验证后台发布状态和前台{zh_type}详情页；"
        "本次只允许发布该 probe 并验证，不删除、不批量上传，清理另行授权。"
    )
    return mutation_action_details(
        "publish_probe",
        site_key,
        content_type,
        target,
        str(meta["publishFields"]),
        evidence_path_hint,
        f"{english_type} probe published and frontend detail verified",
        "publish probe, verify backend status and frontend detail page",
        "request separate cleanup authorization after verification",
        authorization_text,
    )


def cleanup_probe_action_details(
    site_key: str,
    content_type: str,
    target: str,
    evidence_path_hint: str,
) -> dict[str, str]:
    meta = CONTENT_TYPE_META.get(content_type)
    if not meta or "cleanupFields" not in meta:
        return {}
    zh_type = str(meta["zh"])
    english_type = str(meta["english"])
    authorization_text = (
        f"授权 Codex 在 {target} 清理 Codex Probe - Delete Me {zh_type}草稿/测试项，"
        "允许删除或取消发布该 probe，并验证后台不存在、前台不再渲染；"
        "本次只允许清理 probe，不影响真实业务内容。"
    )
    return mutation_action_details(
        "cleanup_probe",
        site_key,
        content_type,
        target,
        str(meta["cleanupFields"]),
        evidence_path_hint,
        f"{english_type} probe cleaned and frontend no longer renders probe",
        "delete or unpublish probe, verify backend absence and frontend 404",
        "cleanup is the requested action",
        authorization_text,
    )


def create_site_action_details(evidence_path_hint: str) -> dict[str, str]:
    auth_path = "~/allincms-projects/allincms-create-site-authorization.json"
    authorization_text = (
        "授权 Codex 在 https://workspace.laicms.com/sites 提交创建站点表单；"
        "本次只允许提交创建站点并验证站点卡片、后台 dashboard、前台默认域名和模块路由，"
        "不进行内容上传、发布、删除或后续设置保存。"
    )
    make_authorization_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action create_site "
        "--target https://workspace.laicms.com/sites "
        "--target-type site "
        "--target-identifier pending-new-site "
        "--fields-or-files name,description "
        "--expected-result 'new site card, backend dashboard, and default frontend open' "
        "--verification-plan 'verify site card, backend dashboard, frontend base URL, and module routes' "
        "--cleanup-plan 'no automatic deletion; stop before content upload' "
        "--authorization-source '<paste current user authorization text here>' "
        f"--output {auth_path}"
    )
    gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action create_site "
        f"--preflight {evidence_path_hint} "
        f"--authorization {auth_path}"
    )
    return {
        "action": "create_site",
        "target": "https://workspace.laicms.com/sites",
        "authorizationText": authorization_text,
        "authorizationRecordCommand": make_authorization_command,
        "preMutationGateCommand": gate_command,
    }


def summarize(
    data: dict[str, Any],
    evidence_path_hint: str = "~/allincms-projects/allincms-existing-site-readonly-evidence.json",
    require_created_site: bool = False,
    max_mutation_evidence_age_minutes: int = DEFAULT_MUTATION_EVIDENCE_MAX_AGE_MINUTES,
) -> dict[str, Any]:
    validation_errors = validate_run_evidence(data)
    site_creation = data.get("siteCreation") if isinstance(data.get("siteCreation"), dict) else {}
    site_identity = data.get("siteIdentity") if isinstance(data.get("siteIdentity"), dict) else {}
    content = data.get("contentInspection") if isinstance(data.get("contentInspection"), dict) else {}
    frontend = data.get("frontendRendering") if isinstance(data.get("frontendRendering"), dict) else {}
    launch_readiness = data.get("launchReadiness") if isinstance(data.get("launchReadiness"), dict) else {}
    cleanup = data.get("cleanup") if isinstance(data.get("cleanup"), dict) else {}

    proven: list[str] = []
    missing: list[str] = []
    next_actions: list[str] = []
    next_action_details: list[dict[str, str]] = []
    evidence_freshness = freshness_status(data, max_mutation_evidence_age_minutes)

    if site_creation.get("status") == "created_verified":
        proven.append("site_created_and_verified")
    elif site_creation.get("status") == "existing_site_selected":
        proven.append("existing_site_selected")
    elif site_creation.get("status") == "create_preflight_verified":
        proven.append("create_site_preflight_verified")
        missing.append("real_create_site_submit")
        next_actions.append("authorize_create_site")
        next_action_details.append(create_site_action_details(evidence_path_hint))

    if site_identity.get("siteKey") and site_identity.get("frontendBaseUrl"):
        proven.append("site_identity_verified")
    else:
        missing.append("site_identity")

    setup_pages = data.get("setupPages")
    if isinstance(setup_pages, dict) and all(setup_pages.get(key) for key in ("siteInfo", "domains", "themes", "routes", "forms")):
        proven.append("setup_pages_read_only_inspected")
    else:
        missing.append("setup_pages_read_only_inspection")

    if launch_readiness:
        if launch_readiness_ok(launch_readiness):
            proven.append("theme_route_launch_ready")
        else:
            missing.append("theme_route_launch_readiness")

    content_type = content.get("contentType")
    site_key = str(site_identity.get("siteKey", ""))

    if frontend_static_ok(frontend, str(content_type or "")):
        proven.append("static_frontend_routes_render")
    elif frontend:
        missing.append("static_frontend_routes_clean_audit")

    if content_type:
        proven.append(f"{content_type}_list_columns_inspected")
    else:
        missing.append("content_type_inspection")

    upload_in_scope = data.get("uploadInScope") is True or data.get("mode") == "batch_upload"
    request_capture = data.get("requestCapture")
    sample = data.get("sampleVerification")
    request_capture_proven = isinstance(request_capture, dict) and request_capture.get("persistedVerified") is True
    sample_proven = (
        isinstance(sample, dict)
        and sample.get("backendVerified") is True
        and sample.get("frontendVerified") is True
    )
    if sample_proven:
        proven.append("content_detail_sample_200")
    elif detail_routes_absent(frontend, str(content_type or "")):
        proven.append("content_detail_probe_routes_absent_or_unverified")
        missing.append("content_detail_sample_200")

    if upload_in_scope:
        if request_capture_proven:
            proven.append("request_capture_persisted_verified")
        else:
            missing.append("request_capture_persisted_verified")
        if sample_proven:
            proven.append("sample_backend_frontend_verified")
        else:
            missing.append("sample_backend_frontend_verified")
    else:
        missing.append("upload_not_in_scope")

    cleanup_status = cleanup.get("status")
    if cleanup_status == "completed":
        proven.append("cleanup_completed")
    elif cleanup_status in {"pending_user_authorization", "explicitly_deferred"}:
        missing.append(f"cleanup_{cleanup_status}")

    required_for_completion = [
        "site_created_and_verified" if require_created_site else "site_created_and_verified_or_existing_site_selected",
        *REQUIRED_COMPLETION_PROOF,
    ]
    completion_gaps: list[str] = []
    if require_created_site:
        if "site_created_and_verified" not in proven:
            completion_gaps.append("site_created_and_verified")
    elif not any(item in proven for item in SITE_SOURCE_PROOF):
        completion_gaps.append("site_created_and_verified_or_existing_site_selected")
    completion_gaps.extend(item for item in REQUIRED_COMPLETION_PROOF if item not in proven)

    local_only = data.get("localOnly") is True or data.get("simulationOnly") is True
    completed = (
        data.get("completionClaimed") is True
        and not local_only
        and not validation_errors
        and not missing
        and not completion_gaps
    )

    if not completed and site_key and content_type in CONTENT_TYPE_META:
        save_target = safe_backend_target(
            site_key,
            str(content_type),
            request_capture.get("url") if isinstance(request_capture, dict) else "",
            sample.get("backendUrl") if isinstance(sample, dict) else "",
        )
        publish_or_cleanup_target = safe_backend_target(
            site_key,
            str(content_type),
            sample.get("backendUrl") if isinstance(sample, dict) else "",
            request_capture.get("url") if isinstance(request_capture, dict) else "",
        )

        if upload_in_scope and not request_capture_proven:
            next_actions.append("authorize_save_probe")
            detail = save_probe_action_details(site_key, str(content_type), save_target, evidence_path_hint)
            if detail:
                next_action_details.append(detail)
        elif upload_in_scope and request_capture_proven and not sample_proven:
            next_actions.append("authorize_publish_probe")
            detail = publish_probe_action_details(site_key, str(content_type), publish_or_cleanup_target, evidence_path_hint)
            if detail:
                next_action_details.append(detail)
        elif upload_in_scope and request_capture_proven and sample_proven and "cleanup_completed" not in proven:
            next_actions.append("authorize_cleanup_probe")
            detail = cleanup_probe_action_details(site_key, str(content_type), publish_or_cleanup_target, evidence_path_hint)
            if detail:
                next_action_details.append(detail)
        elif not upload_in_scope and "content_detail_sample_200" in missing:
            next_actions.append("authorize_content_probe")

    if not completed and "authorize_content_probe" not in next_actions and "content_detail_sample_200" in missing and not upload_in_scope:
        next_actions.append("authorize_content_probe")
    if "authorize_content_probe" in next_actions:
        detail = probe_action_details(site_key, str(content_type or ""), evidence_path_hint)
        if detail:
            next_action_details.append(detail)

    if next_action_details and evidence_freshness.get("freshForMutation") is not True:
        next_actions.insert(0, "refresh_readonly_evidence")
        next_action_details.insert(
            0,
            {
                "action": "refresh_readonly_evidence",
                "reason": str(evidence_freshness.get("reason", "stale")),
                "summary": "Re-open the backend list/setup pages and regenerate read-only run evidence before creating a fresh authorization record or running a mutation gate.",
            },
        )

    return {
        "valid": not validation_errors,
        "completionClaimed": data.get("completionClaimed") is True,
        "complete": completed,
        "localOnly": data.get("localOnly") is True,
        "simulationOnly": data.get("simulationOnly") is True,
        "remoteMutationsPerformed": data.get("remoteMutationsPerformed"),
        "mode": data.get("mode"),
        "siteKey": site_identity.get("siteKey", ""),
        "contentType": content_type or "",
        "requireCreatedSite": require_created_site,
        "evidenceFreshness": evidence_freshness,
        "proven": proven,
        "missing": missing,
        "requiredForCompletion": required_for_completion,
        "completionGaps": completion_gaps,
        "nextActions": next_actions,
        "nextActionDetails": next_action_details,
        "validationErrors": validation_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize AllinCMS run evidence status.")
    parser.add_argument("run_evidence_json")
    parser.add_argument("--output")
    parser.add_argument(
        "--require-created-site",
        action="store_true",
        help="Require siteCreation.status=created_verified for from-scratch site-build completion.",
    )
    parser.add_argument(
        "--max-mutation-evidence-age-minutes",
        type=int,
        default=DEFAULT_MUTATION_EVIDENCE_MAX_AGE_MINUTES,
        help="Freshness window for warning about mutation gates; default matches check_pre_mutation_gate.py.",
    )
    args = parser.parse_args()

    try:
        summary = summarize(
            load_json(Path(args.run_evidence_json)),
            evidence_path_hint=args.run_evidence_json,
            require_created_site=args.require_created_site,
            max_mutation_evidence_age_minutes=args.max_mutation_evidence_age_minutes,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
