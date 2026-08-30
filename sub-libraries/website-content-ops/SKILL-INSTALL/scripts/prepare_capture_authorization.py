#!/usr/bin/env python3
"""Prepare an authorization package for one AllinCMS capture-plan stage."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any


GATED_ACTIONS = {
    "create_post_probe": "probe",
    "create_product_probe": "probe",
    "create_form_probe": "probe",
    "save_site_settings": "site_action",
    "create_theme": "site_action",
    "create_theme_page": "site_action",
    "bind_route": "site_action",
    "create_route": "site_action",
    "create_form": "site_action",
    "add_domain": "site_action",
    "add_tracking_tag": "site_action",
    "save_product": "existing_content",
    "publish_product": "existing_content",
    "save_post": "existing_content",
    "publish_post": "existing_content",
}
SIMULATED_SITE_KEYS = {"simsite01", "codexsimulatedsite"}
AUTHORIZATION_SOURCE_PLACEHOLDER = "<paste current user authorization text here>"
TARGET_TYPES = {
    "products": "products",
    "posts": "posts",
    "forms": "forms",
    "media": "media",
    "themes": "themes",
    "routes": "routes",
    "site-info": "site-info",
}
FIELDS_BY_ACTION = {
    "create_post_probe": ["title", "slug", "excerpt", "content", "coverImage", "status"],
    "create_product_probe": ["name", "slug", "description", "content", "coverImage", "status"],
    "create_form_probe": ["name", "slug", "fields", "status"],
    "save_product": ["requestCapture", "payloadShape", "persistedVerified", "bodyOrMediaAudit"],
    "publish_product": ["publishStatus", "backendVerified", "frontendVerified"],
    "save_post": ["requestCapture", "payloadShape", "persistedVerified", "bodyOrMediaAudit"],
    "publish_post": ["publishStatus", "backendVerified", "frontendVerified"],
    "upload_media": ["file", "uploadRequest", "publicUrl", "metadata"],
    "create_theme": ["requestCapture", "themeId", "backendVerified"],
    "create_theme_page": ["requestCapture", "pageId", "routePath", "backendVerified"],
    "create_route": ["routePath", "backendVerified", "frontendVerified"],
    "bind_route": ["routePath", "boundPage", "frontendVerified"],
    "save_site_settings": ["fieldMapping", "persistedVerified"],
    "add_domain": ["domain", "backendVerified", "dnsFollowup"],
    "add_tracking_tag": ["googleTagId", "backendVerified"],
}
MODULE_LABELS = {
    "posts": "文章",
    "products": "产品",
    "forms": "表单",
}


def load_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"capture plan not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid capture plan JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("capture plan root must be an object")
    if data.get("kind") != "allincms_module_capture_plan":
        raise ValueError("capture plan kind must be allincms_module_capture_plan")
    return data


def select_stage(plan: dict[str, Any], module: str, action: str) -> dict[str, Any]:
    stages = plan.get("stages")
    if not isinstance(stages, list):
        raise ValueError("capture plan stages must be an array")
    matches = [
        stage
        for stage in stages
        if isinstance(stage, dict) and stage.get("module") == module and stage.get("action") == action
    ]
    if not matches:
        raise ValueError(f"stage not found for module={module} action={action}")
    if len(matches) > 1:
        raise ValueError(f"multiple stages found for module={module} action={action}")
    return matches[0]


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def site_key_from_stage(stage: dict[str, Any]) -> str:
    target = str(stage.get("target", ""))
    if "workspace.laicms.com/" not in target:
        return ""
    return target.split("workspace.laicms.com/", 1)[-1].split("/", 1)[0]


def redact_simulated_target(value: str) -> str:
    for site_key in SIMULATED_SITE_KEYS:
        value = value.replace(f"/{site_key}/", "/{realSiteKey}/")
        value = value.replace(f" {site_key} ", " {realSiteKey} ")
    return value


def suggested_authorization_text(stage: dict[str, Any]) -> str:
    action = stage["authorizationAction"]
    target = stage["target"]
    module = stage["module"]
    module_label = MODULE_LABELS.get(str(module), str(module))
    stop_after = stage["stopAfter"]
    if action.endswith("_probe"):
        return (
            f"授权 Codex 在 {target} 创建一个 Codex Probe - Delete Me {module_label}测试草稿，"
            f"仅用于捕获创建行为；本次停止条件：{stop_after}。"
        )
    if action == "upload_media":
        return (
            f"授权 Codex 在 {target} 上传一个明确的测试媒体文件，仅用于捕获上传请求；"
            f"本次停止条件：{stop_after}。"
        )
    return (
        f"授权 Codex 在 {target} 执行 {action} 的单步测试捕获；"
        f"本次停止条件：{stop_after}。"
    )


def build_authorization_command(stage: dict[str, Any], output: str) -> str:
    action = stage["authorizationAction"]
    module = stage["module"]
    target_type = TARGET_TYPES.get(module, module)
    target_identifier = "Codex Probe - Delete Me" if action.endswith("_probe") else f"{module}:{stage['action']}:capture"
    fields = FIELDS_BY_ACTION.get(action, ["requestCapture", "backendVerified"])
    parts = [
        "python3",
        "skills/allincms-bulk-content-upload/scripts/make_authorization_record.py",
        "--action",
        action,
        "--site-key",
        stage.get("target", "").split("workspace.laicms.com/")[-1].split("/")[0],
        "--target",
        stage["target"],
        "--target-type",
        target_type,
        "--target-identifier",
        target_identifier,
        "--fields-or-files",
        ",".join(fields),
        "--expected-result",
        stage["stopAfter"],
        "--verification-plan",
        "; ".join(stage.get("mustCapture", [])),
        "--cleanup-plan",
        "stop after this capture stage; cleanup or next mutation requires separate authorization",
        "--authorization-source",
        AUTHORIZATION_SOURCE_PLACEHOLDER,
        "--output",
        output,
    ]
    return shell_join(parts)


def build_gate_command(stage: dict[str, Any], preflight: str, authorization: str) -> str | None:
    action = stage["authorizationAction"]
    gate_kind = GATED_ACTIONS.get(action)
    if not gate_kind:
        return None
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


def simulated_target_package(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "allincms_capture_authorization_package",
        "module": stage["module"],
        "action": stage["action"],
        "authorizationAction": stage["authorizationAction"],
        "target": redact_simulated_target(str(stage["target"])),
        "simulatedTarget": stage["target"],
        "jsonReplayReady": False,
        "suggestedAuthorizationText": redact_simulated_target(suggested_authorization_text(stage)),
        "authorizationRecordCommand": None,
        "preMutationGateCommand": None,
        "gateSupported": False,
        "commandsSuppressed": True,
        "stopAfter": stage["stopAfter"],
        "mustCapture": stage.get("mustCapture", []),
        "warning": (
            "Simulated rehearsal target detected. Commands are suppressed; rebuild from real browser evidence "
            "before mutating LAICMS. This package is not user authorization."
        ),
    }


def build_package(stage: dict[str, Any], preflight: str, authorization_output: str, allow_simulated_target: bool = False) -> dict[str, Any]:
    if site_key_from_stage(stage) in SIMULATED_SITE_KEYS and not allow_simulated_target:
        return simulated_target_package(stage)
    authorization_command = build_authorization_command(stage, authorization_output)
    gate_command = build_gate_command(stage, preflight, authorization_output)
    return {
        "kind": "allincms_capture_authorization_package",
        "module": stage["module"],
        "action": stage["action"],
        "authorizationAction": stage["authorizationAction"],
        "target": stage["target"],
        "jsonReplayReady": False,
        "suggestedAuthorizationText": suggested_authorization_text(stage),
        "authorizationRecordCommand": authorization_command,
        "preMutationGateCommand": gate_command,
        "gateSupported": gate_command is not None,
        "stopAfter": stage["stopAfter"],
        "mustCapture": stage.get("mustCapture", []),
        "warning": "This package prepares commands and suggested wording only. It is not user authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare authorization commands for one capture-plan stage.")
    parser.add_argument("capture_plan_json")
    parser.add_argument("--module", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output")
    parser.add_argument("--allow-simulated-target", action="store_true", help="Allow command output for local tests that intentionally use simulated site keys")
    args = parser.parse_args()

    try:
        plan = load_plan(Path(args.capture_plan_json))
        stage = select_stage(plan, args.module, args.action)
        package = build_package(stage, args.preflight, args.authorization_output, args.allow_simulated_target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(package, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
