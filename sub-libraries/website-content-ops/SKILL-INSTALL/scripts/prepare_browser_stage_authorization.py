#!/usr/bin/env python3
"""Prepare authorization commands for one AllinCMS browser-stage packet."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from build_browser_stage_packet import validate_browser_stage_packet
from prepare_capture_authorization import build_package as build_capture_authorization_package
from prepare_capture_authorization import load_plan as load_capture_plan
from prepare_capture_authorization import select_stage as select_capture_stage

AUTH_PLACEHOLDER = "<paste current user authorization text here>"
SIMULATED_SITE_KEYS = {"simsite01", "codexsimulatedsite"}
CONTENT_TYPE_SPECS = {
    "posts": {
        "module": "posts",
        "createAction": "create_post_probe",
        "targetType": "posts",
        "createFields": ["title", "slug", "excerpt", "content", "coverImage", "status"],
    },
    "products": {
        "module": "products",
        "createAction": "create_product_probe",
        "targetType": "products",
        "createFields": ["name", "slug", "description", "content", "coverImage", "status"],
    },
    "forms": {
        "module": "forms",
        "createAction": "create_form_probe",
        "targetType": "forms",
        "createFields": ["name", "slug", "fields", "status"],
    },
}
CONTENT_STAGE_SPECS = {
    "content_probe_create": {
        "action": "create_probe_for_content_type",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}",
        "fieldsByKind": "createFields",
        "expectedResult": "temporary Codex Probe - Delete Me draft opens or appears in the backend list",
        "verificationPlan": "verify probe/test naming proof and backend draft proof before any save or publish",
        "cleanupPlan": "no automatic cleanup; save, publish, or cleanup requires separate authorization",
        "stopAfter": "stop after the probe draft URL or list-row proof is captured",
    },
    "save_request_capture": {
        "action": "save_probe",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}/{contentId}/edit",
        "fields": ["requestCapture", "payloadShape", "persistedVerified"],
        "expectedResult": "probe save request is captured and backend persistence is verified",
        "verificationPlan": "capture save request URL, method, headers, payload shape, field mapping, and persisted backend state",
        "cleanupPlan": "no automatic cleanup; publish or cleanup requires separate authorization",
        "stopAfter": "stop after payload template, field mapping, and persistence proof are recorded",
    },
    "publish_sample_verify": {
        "action": "publish_probe",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}/{contentId}/edit",
        "fields": ["publishStatus", "frontendVerified"],
        "expectedResult": "probe/sample is published and backend plus frontend detail route are verified",
        "verificationPlan": "verify backend published status, frontend detail status, cover/media, title/name, and structured body",
        "cleanupPlan": "request separate cleanup authorization after verification",
        "stopAfter": "stop after backend status and frontend detail proof are recorded",
    },
    "cleanup_probes": {
        "action": "cleanup_probe",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}",
        "fields": ["cleanedCandidates", "backendVerified", "frontendVerified"],
        "expectedResult": "probe/test/Untitled entries are deleted or unpublished and no longer public",
        "verificationPlan": "verify candidate list, backend cleanup proof, and frontend 404 or non-public proof",
        "cleanupPlan": "cleanup is the requested action; stop after verification",
        "stopAfter": "stop after backend absence/unpublished state and frontend non-public proof are recorded",
    },
}
CONTENT_TYPE_LABELS = {
    "posts": "文章",
    "products": "产品",
    "forms": "表单",
}
BATCH_STAGE_SPECS = {
    "batch_upload_publish": {
        "action": "batch_upload",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}",
        "fields": ["schemaGatePass", "sampleVerification", "progressLog", "frontendDetailAudit"],
        "expectedResult": "manifest items are uploaded or updated, progress is tracked, and frontend detail routes are audited",
        "verificationPlan": "verify schema gate pass, sample verification pass, progress log, duplicate slug handling, and frontend detail audit for every uploaded route",
        "cleanupPlan": "stop after batch proof; cleanup probes or rollback requires separate authorization",
        "stopAfter": "stop after progress report and per-entry backend/frontend verification are complete",
    },
}
FORMS_MEDIA_SETTINGS_ACTION_SPECS = {
    "save_site_settings": {
        "module": "site-info",
        "targetType": "site-info",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/site-info",
        "targetIdentifier": "site-info settings",
        "fields": ["fieldMapping", "persistedVerified"],
        "expectedResult": "site settings are saved and backend persisted state is verified",
        "verificationPlan": "capture the save request and verify the edited settings in backend, frontend, or metadata as applicable",
        "stopAfter": "stop after site settings request capture and persistence proof are recorded",
    },
    "create_theme": {
        "module": "themes",
        "targetType": "themes",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes",
        "targetIdentifier": "new theme",
        "fields": ["requestCapture", "themeId", "backendVerified"],
        "expectedResult": "theme is created and backend theme id/state are verified",
        "verificationPlan": "capture the create-theme request, theme id, and backend list/detail proof",
        "stopAfter": "stop after theme creation proof is recorded",
    },
    "create_form": {
        "module": "forms",
        "targetType": "forms",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/forms",
        "targetIdentifier": "new form",
        "fields": ["requestCapture", "formId", "backendVerified"],
        "expectedResult": "form is created and backend form id/state are verified",
        "verificationPlan": "capture the create-form request, form id, and backend list/detail proof",
        "stopAfter": "stop after form creation proof is recorded",
    },
    "add_domain": {
        "module": "domains",
        "targetType": "domains",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/domains",
        "targetIdentifier": "domain binding",
        "fields": ["domain", "backendVerified", "dnsFollowup"],
        "expectedResult": "domain entry is added and backend state plus DNS follow-up requirement are recorded",
        "verificationPlan": "verify domain row/status and record DNS follow-up requirement without assuming public DNS is live",
        "stopAfter": "stop after backend domain state and DNS follow-up proof are recorded",
    },
    "add_tracking_tag": {
        "module": "tracking",
        "targetType": "tracking",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/tracking",
        "targetIdentifier": "tracking tag",
        "fields": ["googleTagId", "backendVerified"],
        "expectedResult": "tracking tag is added and backend persisted state is verified",
        "verificationPlan": "verify tracking row/settings and record whether public script proof is still pending",
        "stopAfter": "stop after tracking backend state proof is recorded",
    },
    "upload_media": {
        "module": "media",
        "targetType": "media",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/media",
        "targetIdentifier": "test media upload",
        "fields": ["file", "uploadRequest", "publicUrl", "metadata"],
        "expectedResult": "test media upload request and resulting public URL are captured",
        "verificationPlan": "capture multipart/storage behavior and verify backend media row plus public URL before any replay",
        "stopAfter": "stop after media upload request shape and public URL proof are recorded",
        "gateSupported": False,
    },
}
LAUNCH_ACTION_SPECS = {
    "create_theme_page": {
        "module": "themes",
        "targetType": "theme-page",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes/{themeId}",
        "targetIdentifier": "{themeId}/{pageRoute} theme page",
        "fields": ["requestCapture", "pageId", "routePath", "backendVerified"],
        "expectedResult": "theme page row is created under the exact theme and backend state is verified",
        "verificationPlan": "capture create-page request, verify page id, route path, and backend page row before design or publish",
        "stopAfter": "stop after theme page creation request and backend row proof are recorded",
    },
    "save_design": {
        "module": "themes",
        "targetType": "theme-design",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes/{themeId}/{pageId}/design",
        "targetIdentifier": "{themeId}/{pageId} design",
        "fields": ["requestCapture", "pageDocument", "persistedVerified"],
        "expectedResult": "design payload is captured and persisted on the exact theme page",
        "verificationPlan": "capture request, verify pageDocument, then verify backend persisted state",
        "stopAfter": "stop after design save persistence proof is recorded",
    },
    "publish_design": {
        "module": "themes",
        "targetType": "theme-design",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes/{themeId}/{pageId}/design",
        "targetIdentifier": "{themeId}/{pageId} design publish",
        "fields": ["publishStatus", "frontendVerified"],
        "expectedResult": "theme page publish status and frontend rendering are verified",
        "verificationPlan": "verify publish status and public frontend route",
        "stopAfter": "stop after publish status and frontend proof are recorded",
    },
    "enable_theme_page": {
        "module": "themes",
        "targetType": "theme-page",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes/{themeId}",
        "targetIdentifier": "{themeId}/{pageId} enabled page",
        "fields": ["enabled", "frontendVerified"],
        "expectedResult": "theme page is enabled and frontend availability is verified",
        "verificationPlan": "verify enabled switch/state and public frontend route",
        "stopAfter": "stop after enabled state and frontend proof are recorded",
    },
    "set_homepage": {
        "module": "themes",
        "targetType": "theme-page",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes/{themeId}",
        "targetIdentifier": "{themeId}/{pageId} homepage",
        "fields": ["homepage", "frontendVerified"],
        "expectedResult": "selected theme page is set as homepage and public root renders",
        "verificationPlan": "verify homepage marker and public / route DOM",
        "stopAfter": "stop after homepage and frontend root proof are recorded",
    },
    "bind_route": {
        "module": "routes",
        "targetType": "routes",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/routes",
        "targetIdentifier": "{routePath} route binding",
        "fields": ["routePath", "boundPage", "frontendVerified"],
        "expectedResult": "route path is bound to the selected page and frontend route renders",
        "verificationPlan": "verify route row binding and public frontend route",
        "stopAfter": "stop after route binding and frontend proof are recorded",
    },
    "create_route": {
        "module": "routes",
        "targetType": "routes",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/routes",
        "targetIdentifier": "{routePath} route",
        "fields": ["routePath", "backendVerified", "frontendVerified"],
        "expectedResult": "route path exists in backend and expected public frontend status is verified",
        "verificationPlan": "verify route row and public frontend route",
        "stopAfter": "stop after route creation and frontend proof are recorded",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"packet JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid packet JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("packet JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def command_with_authorization_placeholder(command: str | None) -> str | None:
    if command is None:
        return None
    marker = " --authorization-source "
    if marker not in command:
        return command
    prefix, _source = command.split(marker, 1)
    return f"{prefix}{marker}{shlex.quote(AUTH_PLACEHOLDER)}"


def is_templated_or_simulated_target(target: str) -> bool:
    if "{" in target or "}" in target:
        return True
    site_key = site_key_from_target(target)
    return site_key in SIMULATED_SITE_KEYS


def should_suppress_launch_commands(target: str, allow_simulated_target: bool) -> bool:
    if "{" in target or "}" in target:
        return True
    site_key = site_key_from_target(target)
    return site_key in SIMULATED_SITE_KEYS and not allow_simulated_target


def should_suppress_commands(target: str, allow_simulated_target: bool) -> bool:
    if "{" in target or "}" in target:
        return True
    site_key = site_key_from_target(target)
    return site_key in SIMULATED_SITE_KEYS and not allow_simulated_target


def site_key_from_target(target: str) -> str:
    parsed = urlparse(target)
    path = parsed.path if parsed.scheme and parsed.netloc else target
    parts = [part for part in path.split("/") if part]
    return parts[0] if parts else ""


def redact_target(value: str) -> str:
    for site_key in SIMULATED_SITE_KEYS:
        value = value.replace(f"/{site_key}/", "/{realSiteKey}/")
        value = value.replace(f" {site_key} ", " {realSiteKey} ")
    return value


def content_stage_action(stage_id: str, content_type: str) -> str:
    stage_spec = CONTENT_STAGE_SPECS[stage_id]
    action = str(stage_spec["action"])
    if action == "create_probe_for_content_type":
        return str(CONTENT_TYPE_SPECS[content_type]["createAction"])
    return action


def content_stage_fields(stage_id: str, content_type: str) -> list[str]:
    stage_spec = CONTENT_STAGE_SPECS[stage_id]
    if "fieldsByKind" in stage_spec:
        return list(CONTENT_TYPE_SPECS[content_type][str(stage_spec["fieldsByKind"])])
    return list(stage_spec["fields"])


def content_stage_target(stage_id: str, content_type: str, explicit_target: str) -> str:
    if explicit_target.strip():
        return explicit_target.strip()
    stage_spec = CONTENT_STAGE_SPECS[stage_id]
    return str(stage_spec["targetTemplate"]).replace("{contentType}", content_type)


def content_stage_authorization_text(action: str, target: str, content_type: str, stop_after: str) -> str:
    content_label = CONTENT_TYPE_LABELS.get(content_type, content_type)
    verb_by_action = {
        "create_post_probe": "创建一个 Codex Probe - Delete Me 文章测试草稿",
        "create_product_probe": "创建一个 Codex Probe - Delete Me 产品测试草稿",
        "create_form_probe": "创建一个 Codex Probe - Delete Me 表单测试草稿",
        "save_probe": "保存 Codex Probe - Delete Me 测试草稿并捕获请求",
        "publish_probe": "发布 Codex Probe - Delete Me 测试草稿并验证前台",
        "cleanup_probe": "清理或取消发布 Codex Probe - Delete Me 测试草稿",
    }
    verb = verb_by_action.get(action, f"执行 {action}")
    return (
        f"授权 Codex 在 {target} 针对{content_label}{verb}；"
        f"只做该内容探针单步动作，不继续其它保存/发布/上传/清理步骤；本次停止条件：{stop_after}。"
    )


def batch_stage_authorization_text(action: str, target: str, content_type: str, stop_after: str) -> str:
    return (
        f"授权 Codex 在 {target} 针对 {content_type} 执行 {action} 批量上传/发布单步操作；"
        f"只使用当前站点已验证 schema 和 manifest，不切换内容类型、不改主题/路由/域名、不清理条目；"
        f"本次停止条件：{stop_after}。"
    )


def settings_action_authorization_text(action: str, target: str, stop_after: str) -> str:
    return (
        f"授权 Codex 在 {target} 执行 {action} 的单步 forms/media/settings 操作；"
        f"只做该动作，不继续其它表单、媒体、站点设置、域名、追踪、主题或内容上传动作；"
        f"本次停止条件：{stop_after}。"
    )


def ui_first_capture_authorization_text(action: str, target: str, stop_after: str) -> str:
    return (
        f"授权 Codex 在 {target} 仅通过 UI 手动执行一次 {action} 探测/捕获；"
        "只允许记录上传控件、请求形态、后端媒体行和公开 URL 证明；"
        "不得复用接口、不得 JSON replay、不得批量上传、不得继续其它 forms/media/settings 动作；"
        f"本次停止条件：{stop_after}。"
    )


def create_site_authorization_text(packet: dict[str, Any]) -> str:
    target = str(packet.get("targetTemplate", "https://workspace.laicms.com/sites"))
    return (
        f"授权 Codex 在 {target} 提交创建站点表单；"
        "仅填写本次明确授权的站点名称和描述；"
        "完成站点卡片、后台 dashboard、默认前台、模块路由 proof 后停止。"
    )


def build_create_site_package(packet: dict[str, Any], preflight: str, authorization_output: str) -> dict[str, Any]:
    target = "https://workspace.laicms.com/sites"
    auth_text = create_site_authorization_text(packet)
    authorization_command = shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            "create_site",
            "--target",
            target,
            "--target-type",
            "site",
            "--target-identifier",
            "pending-new-site",
            "--fields-or-files",
            "name,description",
            "--expected-result",
            "new site card, backend dashboard, default frontend, and module routes verified",
            "--verification-plan",
            "verify site card, backend dashboard, frontend base URL, and module routes",
            "--cleanup-plan",
            "no automatic deletion; stop before setup, theme, content, upload, or cleanup mutations",
            "--authorization-source",
            "<paste current user authorization text here>",
            "--output",
            authorization_output,
        ]
    )
    gate_command = shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py",
            "--action",
            "create_site",
            "--preflight",
            preflight,
            "--authorization",
            authorization_output,
        ]
    )
    return {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": "create_site_submit",
        "target": target,
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "suggestedAuthorizationText": auth_text,
        "authorizationRecordCommand": authorization_command,
        "preMutationGateCommand": gate_command,
        "gateSupported": True,
        "stopAfter": packet.get("stopAfter", ""),
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": (
            "This package prepares commands and suggested wording only. "
            "It is not user authorization and it does not permit any later stage."
        ),
    }


def split_stage_key(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise ValueError(f"capture stage key must be module:action, got: {value}")
    module, action = value.split(":", 1)
    module = module.strip()
    action = action.strip()
    if not module or not action:
        raise ValueError(f"capture stage key must include module and action, got: {value}")
    return module, action


def next_capture_stage_from_coverage(coverage: dict[str, Any]) -> tuple[str, str]:
    next_key = str(coverage.get("nextUncapturedStageKey", "")).strip()
    if next_key:
        return split_stage_key(next_key)
    stages = coverage.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if stage.get("status") in {"pending", "blocked"}:
                return str(stage.get("module", "")).strip(), str(stage.get("action", "")).strip()
    raise ValueError("module capture coverage has no next uncaptured stage")


def first_capture_stage(plan: dict[str, Any]) -> tuple[str, str]:
    stages = plan.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("capture plan has no stages")
    first = stages[0]
    if not isinstance(first, dict):
        raise ValueError("capture plan first stage must be an object")
    module = str(first.get("module", "")).strip()
    action = str(first.get("action", "")).strip()
    if not module or not action:
        raise ValueError("capture plan first stage must include module and action")
    return module, action


def build_module_capture_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    capture_plan_path: str,
    coverage_path: str,
    allow_command_output: bool = False,
) -> dict[str, Any]:
    if not capture_plan_path:
        raise ValueError("module_interface_capture requires --capture-plan")
    plan = load_capture_plan(Path(capture_plan_path))
    if coverage_path:
        coverage = load_json(Path(coverage_path))
        module, action = next_capture_stage_from_coverage(coverage)
    else:
        module, action = first_capture_stage(plan)
    stage = select_capture_stage(plan, module, action)
    package = build_capture_authorization_package(
        stage,
        preflight,
        authorization_output,
        allow_simulated_target=allow_command_output,
    )
    return {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": "module_interface_capture",
        "target": package.get("target", packet.get("targetTemplate", "")),
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "captureStage": {
            "module": module,
            "action": action,
            "authorizationAction": package.get("authorizationAction", ""),
        },
        "suggestedAuthorizationText": package.get("suggestedAuthorizationText", ""),
        "authorizationRecordCommand": command_with_authorization_placeholder(package.get("authorizationRecordCommand")),
        "preMutationGateCommand": package.get("preMutationGateCommand"),
        "gateSupported": package.get("gateSupported") is True,
        "commandsSuppressed": package.get("commandsSuppressed") is True,
        "stopAfter": package.get("stopAfter", packet.get("stopAfter", "")),
        "requiredProof": list(packet.get("requiredProof", [])),
        "mustCapture": list(package.get("mustCapture", [])),
        "warning": (
            "This package prepares one module/action capture only. "
            "It is not user authorization and it does not complete the aggregate module_interface_capture stage."
        ),
    }


def launch_authorization_text(action: str, target: str, stop_after: str) -> str:
    return (
        f"授权 Codex 在 {target} 执行 {action} 的单步主题/页面/路由操作；"
        f"只做该动作，不继续其它 launch 子动作或内容上传；本次停止条件：{stop_after}。"
    )


def build_launch_action_command(action: str, target: str, target_identifier: str, output: str) -> str:
    spec = LAUNCH_ACTION_SPECS[action]
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            action,
            "--site-key",
            site_key_from_target(target),
            "--target",
            target,
            "--target-type",
            spec["targetType"],
            "--target-identifier",
            target_identifier,
            "--fields-or-files",
            ",".join(spec["fields"]),
            "--expected-result",
            spec["expectedResult"],
            "--verification-plan",
            spec["verificationPlan"],
            "--cleanup-plan",
            "stop after this single launch action; rollback or next launch action requires separate authorization",
            "--authorization-source",
            launch_authorization_text(action, target, spec["stopAfter"]),
            "--output",
            output,
        ]
    )


def build_launch_gate_command(action: str, preflight: str, authorization_output: str) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py",
            "--action",
            action,
            "--preflight",
            preflight,
            "--authorization",
            authorization_output,
        ]
    )


def build_theme_launch_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    launch_action: str,
    launch_target: str,
    launch_target_identifier: str,
    allow_command_output: bool = False,
) -> dict[str, Any]:
    if not launch_action:
        raise ValueError(
            "theme_page_route_launch requires --launch-action "
            f"({', '.join(sorted(LAUNCH_ACTION_SPECS))}); do not authorize the aggregate stage"
        )
    if launch_action not in LAUNCH_ACTION_SPECS:
        raise ValueError(f"--launch-action must be one of {sorted(LAUNCH_ACTION_SPECS)}")
    spec = LAUNCH_ACTION_SPECS[launch_action]
    target = launch_target.strip() or spec["targetTemplate"]
    target_identifier = launch_target_identifier.strip() or spec["targetIdentifier"]
    suggested_text = launch_authorization_text(launch_action, target, spec["stopAfter"])
    suppress_commands = should_suppress_launch_commands(target, allow_command_output)
    package: dict[str, Any] = {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": "theme_page_route_launch",
        "target": redact_target(target),
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "launchAction": {
            "action": launch_action,
            "module": spec["module"],
            "targetType": spec["targetType"],
            "fieldsOrFiles": list(spec["fields"]),
            "targetIdentifier": target_identifier,
        },
        "suggestedAuthorizationText": redact_target(suggested_text),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "commandsSuppressed": suppress_commands,
        "stopAfter": spec["stopAfter"],
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": (
            "This package prepares one theme/page/route launch action only. "
            "It is not user authorization and it does not complete the aggregate theme_page_route_launch stage."
        ),
    }
    if suppress_commands:
        package["simulatedOrTemplatedTarget"] = target
        package["suppressionReason"] = (
            "Launch commands require a real current-site target. Rebuild from browser evidence "
            "with --launch-target before mutating LAICMS."
        )
        return package
    package["authorizationRecordCommand"] = command_with_authorization_placeholder(build_launch_action_command(
        launch_action,
        target,
        target_identifier,
        authorization_output,
    ))
    package["preMutationGateCommand"] = build_launch_gate_command(launch_action, preflight, authorization_output)
    package["gateSupported"] = True
    package["commandsSuppressed"] = False
    return package


def build_content_stage_command(
    stage_id: str,
    action: str,
    content_type: str,
    target: str,
    target_identifier: str,
    authorization_output: str,
) -> str:
    stage_spec = CONTENT_STAGE_SPECS[stage_id]
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            action,
            "--site-key",
            site_key_from_target(target),
            "--target",
            target,
            "--target-type",
            CONTENT_TYPE_SPECS[content_type]["targetType"],
            "--target-identifier",
            target_identifier,
            "--fields-or-files",
            ",".join(content_stage_fields(stage_id, content_type)),
            "--expected-result",
            str(stage_spec["expectedResult"]),
            "--verification-plan",
            str(stage_spec["verificationPlan"]),
            "--cleanup-plan",
            str(stage_spec["cleanupPlan"]),
            "--authorization-source",
            content_stage_authorization_text(action, target, content_type, str(stage_spec["stopAfter"])),
            "--output",
            authorization_output,
        ]
    )


def build_content_gate_command(action: str, preflight: str, authorization_output: str) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py",
            "--action",
            action,
            "--preflight",
            preflight,
            "--authorization",
            authorization_output,
        ]
    )


def build_batch_stage_command(
    stage_id: str,
    action: str,
    content_type: str,
    target: str,
    target_identifier: str,
    authorization_output: str,
) -> str:
    stage_spec = BATCH_STAGE_SPECS[stage_id]
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            action,
            "--site-key",
            site_key_from_target(target),
            "--target",
            target,
            "--target-type",
            CONTENT_TYPE_SPECS[content_type]["targetType"],
            "--target-identifier",
            target_identifier,
            "--fields-or-files",
            ",".join(stage_spec["fields"]),
            "--expected-result",
            str(stage_spec["expectedResult"]),
            "--verification-plan",
            str(stage_spec["verificationPlan"]),
            "--cleanup-plan",
            str(stage_spec["cleanupPlan"]),
            "--authorization-source",
            batch_stage_authorization_text(action, target, content_type, str(stage_spec["stopAfter"])),
            "--output",
            authorization_output,
        ]
    )


def build_batch_stage_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    content_type: str,
    content_target: str,
    content_target_identifier: str,
    allow_command_output: bool = False,
) -> dict[str, Any]:
    stage_id = str(packet.get("stageId", ""))
    if stage_id not in BATCH_STAGE_SPECS:
        raise ValueError(f"unsupported batch stage: {stage_id}")
    if not content_type:
        raise ValueError(
            f"{stage_id} requires --content-type ({', '.join(sorted(k for k in CONTENT_TYPE_SPECS if k != 'forms'))}); "
            "do not infer content type from a templated packet"
        )
    if content_type not in {"posts", "products"}:
        raise ValueError("--content-type for batch_upload_publish must be posts or products")
    stage_spec = BATCH_STAGE_SPECS[stage_id]
    action = str(stage_spec["action"])
    target = content_target.strip() or str(stage_spec["targetTemplate"]).replace("{contentType}", content_type)
    target_identifier = content_target_identifier.strip() or f"{content_type} manifest batch"
    suggested_text = batch_stage_authorization_text(action, target, content_type, str(stage_spec["stopAfter"]))
    suppress_commands = should_suppress_commands(target, allow_command_output)
    package: dict[str, Any] = {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": stage_id,
        "target": redact_target(target),
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "batchStage": {
            "contentType": content_type,
            "module": CONTENT_TYPE_SPECS[content_type]["module"],
            "authorizationAction": action,
            "targetType": CONTENT_TYPE_SPECS[content_type]["targetType"],
            "fieldsOrFiles": list(stage_spec["fields"]),
            "targetIdentifier": target_identifier,
        },
        "suggestedAuthorizationText": redact_target(suggested_text),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "commandsSuppressed": suppress_commands,
        "stopAfter": stage_spec["stopAfter"],
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": (
            "This package prepares one batch upload/publish authorization only. "
            "It is not user authorization and it does not permit another content type, theme/route changes, or cleanup."
        ),
    }
    if suppress_commands:
        package["simulatedOrTemplatedTarget"] = target
        package["suppressionReason"] = (
            "Batch commands require a real current-site target. Rebuild from browser evidence "
            "with --content-target before mutating LAICMS."
        )
        return package
    package["authorizationRecordCommand"] = command_with_authorization_placeholder(build_batch_stage_command(
        stage_id,
        action,
        content_type,
        target,
        target_identifier,
        authorization_output,
    ))
    package["preMutationGateCommand"] = build_content_gate_command(action, preflight, authorization_output)
    package["gateSupported"] = True
    package["commandsSuppressed"] = False
    return package


def build_settings_action_command(action: str, target: str, target_identifier: str, output: str) -> str:
    spec = FORMS_MEDIA_SETTINGS_ACTION_SPECS[action]
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
            "--action",
            action,
            "--site-key",
            site_key_from_target(target),
            "--target",
            target,
            "--target-type",
            spec["targetType"],
            "--target-identifier",
            target_identifier,
            "--fields-or-files",
            ",".join(spec["fields"]),
            "--expected-result",
            spec["expectedResult"],
            "--verification-plan",
            spec["verificationPlan"],
            "--cleanup-plan",
            "stop after this single forms/media/settings action; rollback or next mutation requires separate authorization",
            "--authorization-source",
            settings_action_authorization_text(action, target, spec["stopAfter"]),
            "--output",
            output,
        ]
    )


def build_settings_gate_command(action: str, preflight: str, authorization_output: str) -> str:
    return shell_join(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py",
            "--action",
            action,
            "--preflight",
            preflight,
            "--authorization",
            authorization_output,
        ]
    )


def build_forms_media_settings_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    settings_action: str,
    settings_target: str,
    settings_target_identifier: str,
    allow_command_output: bool = False,
) -> dict[str, Any]:
    if not settings_action:
        raise ValueError(
            "forms_media_settings requires --settings-action "
            f"({', '.join(sorted(FORMS_MEDIA_SETTINGS_ACTION_SPECS))}); do not authorize the aggregate stage"
        )
    if settings_action not in FORMS_MEDIA_SETTINGS_ACTION_SPECS:
        raise ValueError(f"--settings-action must be one of {sorted(FORMS_MEDIA_SETTINGS_ACTION_SPECS)}")
    spec = FORMS_MEDIA_SETTINGS_ACTION_SPECS[settings_action]
    target = settings_target.strip() or str(spec["targetTemplate"])
    target_identifier = settings_target_identifier.strip() or str(spec["targetIdentifier"])
    gate_supported = spec.get("gateSupported", True) is True
    suggested_text = (
        settings_action_authorization_text(settings_action, target, str(spec["stopAfter"]))
        if gate_supported
        else ui_first_capture_authorization_text(settings_action, target, str(spec["stopAfter"]))
    )
    suppress_commands = should_suppress_commands(target, allow_command_output)
    package: dict[str, Any] = {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": "forms_media_settings",
        "target": redact_target(target),
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "settingsAction": {
            "action": settings_action,
            "module": spec["module"],
            "targetType": spec["targetType"],
            "fieldsOrFiles": list(spec["fields"]),
            "targetIdentifier": target_identifier,
        },
        "suggestedAuthorizationText": redact_target(suggested_text),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "commandsSuppressed": suppress_commands or not gate_supported,
        "stopAfter": spec["stopAfter"],
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": (
            "This package prepares one forms/media/settings action only. "
            "It is not user authorization and it does not complete the aggregate forms_media_settings stage."
        ),
    }
    if not gate_supported:
        package["suppressionReason"] = (
            f"{settings_action} has no dedicated pre-mutation gate yet. Keep this action UI-first, "
            "capture multipart/storage or module-specific behavior, and add a gate before emitting commands."
        )
        package["uiFirstCaptureRequired"] = True
        package["mustCaptureBeforeReplay"] = list(spec["fields"])
        package["mustNotReplayUntil"] = [
            "dedicated pre-mutation gate exists",
            "multipart/storage request shape is captured",
            "backend media row is verified",
            "public URL loads successfully",
            "sample upload cleanup or rollback path is known",
        ]
        return package
    if suppress_commands:
        package["simulatedOrTemplatedTarget"] = target
        package["suppressionReason"] = (
            "Forms/media/settings commands require a real current-site target. Rebuild from browser evidence "
            "with --settings-target before mutating LAICMS."
        )
        return package
    package["authorizationRecordCommand"] = command_with_authorization_placeholder(build_settings_action_command(
        settings_action,
        target,
        target_identifier,
        authorization_output,
    ))
    package["preMutationGateCommand"] = build_settings_gate_command(settings_action, preflight, authorization_output)
    package["gateSupported"] = True
    package["commandsSuppressed"] = False
    return package


def build_content_stage_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    content_type: str,
    content_target: str,
    content_target_identifier: str,
    allow_command_output: bool = False,
) -> dict[str, Any]:
    stage_id = str(packet.get("stageId", ""))
    if stage_id not in CONTENT_STAGE_SPECS:
        raise ValueError(f"unsupported content stage: {stage_id}")
    if not content_type:
        raise ValueError(
            f"{stage_id} requires --content-type ({', '.join(sorted(CONTENT_TYPE_SPECS))}); "
            "do not infer content type from a templated packet"
        )
    if content_type not in CONTENT_TYPE_SPECS:
        raise ValueError(f"--content-type must be one of {sorted(CONTENT_TYPE_SPECS)}")
    stage_spec = CONTENT_STAGE_SPECS[stage_id]
    action = content_stage_action(stage_id, content_type)
    target = content_stage_target(stage_id, content_type, content_target)
    target_identifier = content_target_identifier.strip() or "Codex Probe - Delete Me content probe"
    suggested_text = content_stage_authorization_text(action, target, content_type, str(stage_spec["stopAfter"]))
    suppress_commands = should_suppress_commands(target, allow_command_output)
    package: dict[str, Any] = {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": stage_id,
        "target": redact_target(target),
        "authorizationRequired": True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "contentStage": {
            "contentType": content_type,
            "module": CONTENT_TYPE_SPECS[content_type]["module"],
            "authorizationAction": action,
            "targetType": CONTENT_TYPE_SPECS[content_type]["targetType"],
            "fieldsOrFiles": content_stage_fields(stage_id, content_type),
            "targetIdentifier": target_identifier,
        },
        "suggestedAuthorizationText": redact_target(suggested_text),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "commandsSuppressed": suppress_commands,
        "stopAfter": stage_spec["stopAfter"],
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": (
            "This package prepares one content probe lifecycle action only. "
            "It is not user authorization and it does not permit save, publish, upload, or cleanup beyond this stage."
        ),
    }
    if suppress_commands:
        package["simulatedOrTemplatedTarget"] = target
        package["suppressionReason"] = (
            "Content stage commands require a real current-site target. Rebuild from browser evidence "
            "with --content-target before mutating LAICMS."
        )
        return package
    package["authorizationRecordCommand"] = command_with_authorization_placeholder(build_content_stage_command(
        stage_id,
        action,
        content_type,
        target,
        target_identifier,
        authorization_output,
    ))
    package["preMutationGateCommand"] = build_content_gate_command(action, preflight, authorization_output)
    package["gateSupported"] = True
    package["commandsSuppressed"] = False
    return package


def build_package(
    packet: dict[str, Any],
    preflight: str,
    authorization_output: str,
    capture_plan_path: str = "",
    coverage_path: str = "",
    allow_command_output: bool = False,
    launch_action: str = "",
    launch_target: str = "",
    launch_target_identifier: str = "",
    content_type: str = "",
    content_target: str = "",
    content_target_identifier: str = "",
    settings_action: str = "",
    settings_target: str = "",
    settings_target_identifier: str = "",
) -> dict[str, Any]:
    validation = validate_browser_stage_packet(packet)
    if not validation["ok"]:
        raise ValueError("packet validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    stage_id = str(packet.get("stageId", ""))
    if packet.get("authorizationRequired") is not True:
        return {
            "kind": "allincms_browser_stage_authorization_package",
            "stageId": stage_id,
            "authorizationRequired": False,
            "gateSupported": False,
            "authorizationRecordCommand": None,
            "preMutationGateCommand": None,
            "warning": "This stage does not require mutation authorization.",
        }
    if stage_id == "create_site_submit":
        return build_create_site_package(packet, preflight, authorization_output)
    if stage_id == "module_interface_capture":
        return build_module_capture_package(
            packet,
            preflight,
            authorization_output,
            capture_plan_path,
            coverage_path,
            allow_command_output,
        )
    if stage_id == "theme_page_route_launch":
        return build_theme_launch_package(
            packet,
            preflight,
            authorization_output,
            launch_action,
            launch_target,
            launch_target_identifier,
            allow_command_output,
        )
    if stage_id in CONTENT_STAGE_SPECS:
        return build_content_stage_package(
            packet,
            preflight,
            authorization_output,
            content_type,
            content_target,
            content_target_identifier,
            allow_command_output,
        )
    if stage_id in BATCH_STAGE_SPECS:
        return build_batch_stage_package(
            packet,
            preflight,
            authorization_output,
            content_type,
            content_target,
            content_target_identifier,
            allow_command_output,
        )
    if stage_id == "forms_media_settings":
        return build_forms_media_settings_package(
            packet,
            preflight,
            authorization_output,
            settings_action,
            settings_target,
            settings_target_identifier,
            allow_command_output,
        )
    return {
        "kind": "allincms_browser_stage_authorization_package",
        "stageId": stage_id,
        "authorizationRequired": True,
        "target": packet.get("targetTemplate", ""),
        "remoteMutationExpectation": packet.get("remoteMutationExpectation"),
        "suggestedAuthorizationText": packet.get("suggestedAuthorizationText", ""),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "stopAfter": packet.get("stopAfter", ""),
        "requiredProof": list(packet.get("requiredProof", [])),
        "warning": "No local authorization/gate recipe exists for this browser stage yet; extend the helper before mutating.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare authorization commands for one browser-stage packet.")
    parser.add_argument("packet_json")
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--capture-plan", default="", help="Required for module_interface_capture packets")
    parser.add_argument("--coverage", default="", help="Optional module capture coverage JSON for selecting the next uncaptured stage")
    parser.add_argument("--launch-action", default="", help="Required for theme_page_route_launch packets; prepares exactly one launch sub-action")
    parser.add_argument("--launch-target", default="", help="Exact backend target URL for the selected launch action")
    parser.add_argument("--launch-target-identifier", default="", help="Exact theme/page/route identifier for the selected launch action")
    parser.add_argument("--content-type", default="", help="Required for content probe lifecycle packets: posts, products, or forms")
    parser.add_argument("--content-target", default="", help="Exact backend target URL for the selected content stage")
    parser.add_argument("--content-target-identifier", default="", help="Exact Codex Probe - Delete Me target identifier")
    parser.add_argument("--settings-action", default="", help="Required for forms_media_settings packets; prepares exactly one settings/media/forms sub-action")
    parser.add_argument("--settings-target", default="", help="Exact backend target URL for the selected forms/media/settings action")
    parser.add_argument("--settings-target-identifier", default="", help="Exact site/form/media/domain/tracking identifier for the selected action")
    parser.add_argument("--allow-command-output", action="store_true", help="Allow commands for simulated targets during local tests only")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        package = build_package(
            load_json(Path(args.packet_json)),
            args.preflight,
            args.authorization_output,
            args.capture_plan,
            args.coverage,
            args.allow_command_output,
            args.launch_action,
            args.launch_target,
            args.launch_target_identifier,
            args.content_type,
            args.content_target,
            args.content_target_identifier,
            args.settings_action,
            args.settings_target,
            args.settings_target_identifier,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), package)
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
