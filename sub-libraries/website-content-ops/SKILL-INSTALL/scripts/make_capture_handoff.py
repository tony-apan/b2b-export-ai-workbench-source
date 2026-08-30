#!/usr/bin/env python3
"""Create the next real-browser capture handoff from a full E2E simulation output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from prepare_capture_authorization import build_package, select_stage
from validate_full_e2e_simulation import validate_directory


SIMULATED_SITE_KEYS = {"simsite01", "codexsimulatedsite"}
GROUP_PRIORITY = {
    "content_probe_capture": 10,
    "theme_page_design_capture": 20,
    "route_binding_capture": 30,
    "form_capture": 40,
    "media_upload_capture": 50,
    "site_settings_capture": 60,
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def sorted_stages(plan: dict[str, Any], preferred: str = "") -> list[dict[str, Any]]:
    stages = plan.get("stages")
    if not isinstance(stages, list):
        raise ValueError("capture plan stages must be an array")
    valid_stages = [stage for stage in stages if isinstance(stage, dict)]
    return sorted(
        valid_stages,
        key=lambda stage: (
            GROUP_PRIORITY.get(str(stage.get("group", "")), 999),
            0 if preferred and stage.get("module") == preferred else 1,
            str(stage.get("module", "")),
            str(stage.get("action", "")),
        ),
    )


def select_next_stage(plan: dict[str, Any], module: str, action: str, preferred: str = "") -> dict[str, Any]:
    if module or action:
        if not module or not action:
            raise ValueError("--module and --action must be supplied together")
        return select_stage(plan, module, action)
    stages = sorted_stages(plan, preferred)
    if not stages:
        raise ValueError("capture plan contains no stages")
    return stages[0]


def is_simulation_only(validation: dict[str, Any], site_key: object) -> bool:
    return validation.get("localOnly") is True or site_key in SIMULATED_SITE_KEYS


def strip_commands_for_simulation(package: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(package)
    simulated_target = cleaned.get("simulatedTarget", cleaned.get("target"))
    module = cleaned.get("module", "{module}")
    action = cleaned.get("action", "{action}")
    authorization_action = cleaned.get("authorizationAction", "{authorizationAction}")
    templated_target = f"https://workspace.laicms.com/{{realSiteKey}}/{module}"
    cleaned["simulatedTarget"] = simulated_target
    cleaned["target"] = templated_target
    cleaned["suggestedAuthorizationText"] = (
        f"授权 Codex 在 {templated_target} 执行 {authorization_action} 的单步真实站点捕获；"
        f"模块/动作：{module}/{action}；本次只允许完成该 stage 的验证，"
        "不得保存、发布、删除或继续下一阶段，除非另有单独授权。"
    )
    cleaned["authorizationRecordCommand"] = None
    cleaned["preMutationGateCommand"] = None
    cleaned["gateSupported"] = False
    cleaned["simulationOnly"] = True
    cleaned["warning"] = (
        "This package is derived from local-only simulation evidence. Do not run remote commands from it; "
        "refresh real-site evidence and regenerate a non-simulation handoff after user authorization."
    )
    return cleaned


def build_handoff(root: Path, module: str, action: str, output_dir: Path, allow_command_output: bool = False) -> dict[str, Any]:
    validation = validate_directory(root.resolve())
    if not validation["ok"]:
        raise ValueError("full E2E simulation output is invalid:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    capture_plan_path = root / "03-module-interface-plan" / "module-capture-plan.json"
    preflight_path = root / "01-site-creation" / "created-site-evidence.json"
    plan = load_json(capture_plan_path)
    module_scan = load_json(root / "03-module-interface-plan" / "module-scan.redacted.json")
    preferred = str(module_scan.get("contentType", "")).strip()
    stage = select_next_stage(plan, module, action, preferred)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{stage.get('module', 'module')}-{stage.get('action', 'action')}".replace("/", "-")
    authorization_output = output_dir / f"{slug}-authorization.json"
    package = build_package(stage, str(preflight_path), str(authorization_output), allow_simulated_target=allow_command_output)
    simulation_only = is_simulation_only(validation, stage.get("target", "").split("workspace.laicms.com/")[-1].split("/")[0])
    selected_stage = {
        "group": stage.get("group"),
        "module": stage.get("module"),
        "action": stage.get("action"),
        "authorizationAction": stage.get("authorizationAction"),
        "target": stage.get("target"),
        "stopAfter": stage.get("stopAfter"),
    }
    if simulation_only and not allow_command_output:
        package = strip_commands_for_simulation(package)
        selected_stage["simulatedTarget"] = selected_stage["target"]
        selected_stage["target"] = f"https://workspace.laicms.com/{{realSiteKey}}/{stage.get('module')}"
    return {
        "kind": "allincms_next_capture_handoff",
        "sourceFullE2E": str(root),
        "fullE2EValidation": validation,
        "simulationOnly": simulation_only,
        "commandsSuppressed": simulation_only and not allow_command_output,
        "selectedStage": selected_stage,
        "authorizationPackage": package,
        "authorizationOutput": str(authorization_output),
        "warning": (
            "This handoff prepares the next single capture stage only. It is not permission to mutate LAICMS. "
            "For local-only simulation output, command fields are suppressed by default."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build next AllinCMS capture handoff from full E2E simulation output.")
    parser.add_argument("full_e2e_output_dir")
    parser.add_argument("--module", default="")
    parser.add_argument("--action", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-command-output",
        action="store_true",
        help="Emit command fields even for non-simulation evidence. Local-only simulation keys still remain marked simulationOnly.",
    )
    args = parser.parse_args()

    try:
        handoff = build_handoff(
            Path(args.full_e2e_output_dir),
            args.module.strip(),
            args.action.strip(),
            Path(args.output_dir),
            args.allow_command_output,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(handoff, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
