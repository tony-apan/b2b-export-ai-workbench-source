#!/usr/bin/env python3
"""Build a staged real-browser execution plan from local AllinCMS rehearsal artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_full_e2e_simulation import validate_directory
from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


SIMULATED_SITE_KEYS = ("simsite01", "codexsimulatedsite")
REQUIRED_STAGE_IDS = (
    "refresh_readonly_site_evidence",
    "create_site_submit",
    "setup_pages_inspection",
    "module_interface_capture",
    "theme_page_route_launch",
    "static_frontend_audit",
    "content_probe_create",
    "save_request_capture",
    "publish_sample_verify",
    "manifest_schema_gate",
    "batch_upload_publish",
    "forms_media_settings",
    "final_frontend_audit",
    "cleanup_probes",
)
VALID_MODES = {"read_only", "requires_authorization", "verification"}
REMOTE_MUTATION_EXPECTATIONS = {"must", "may", "must_not"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def module_stage_summary(full_e2e_dir: Path) -> dict[str, Any]:
    capture_plan = load_json(full_e2e_dir / "03-module-interface-plan" / "module-capture-plan.json")
    stages = capture_plan.get("stages") if isinstance(capture_plan.get("stages"), list) else []
    return {
        "plannedStageCount": len([stage for stage in stages if isinstance(stage, dict)]),
        "jsonReplayReady": capture_plan.get("jsonReplayReady") is True,
        "authorizationGroups": sorted(
            {str(stage.get("group", "")) for stage in stages if isinstance(stage, dict) and stage.get("group")}
        ),
    }


def stage(
    stage_id: str,
    phase: str,
    mode: str,
    target_template: str,
    authorization_required: bool,
    remote_mutation_expectation: str,
    allowed_actions: list[str],
    stop_after: str,
    required_proof: list[str],
    forbidden_actions: list[str],
    depends_on: list[str] | None = None,
    json_replay_rule: str = "",
) -> dict[str, Any]:
    return {
        "stageId": stage_id,
        "phase": phase,
        "mode": mode,
        "targetTemplate": target_template,
        "authorizationRequired": authorization_required,
        "remoteMutationExpectation": remote_mutation_expectation,
        "allowedActions": allowed_actions,
        "stopAfter": stop_after,
        "requiredProof": required_proof,
        "forbiddenActions": forbidden_actions,
        "dependsOn": depends_on or [],
        "jsonReplayRule": json_replay_rule,
    }


def build_browser_execution_plan(
    full_e2e_dir: Path,
    handoff: dict[str, Any] | None = None,
    launch_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_directory(full_e2e_dir)
    if not validation.get("ok"):
        raise ValueError("full E2E validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))

    module_summary = module_stage_summary(full_e2e_dir)
    handoff_stage = handoff.get("selectedStage") if isinstance(handoff, dict) else {}
    if not isinstance(handoff_stage, dict):
        handoff_stage = {}
    route_plan = launch_plan.get("routePlan") if isinstance(launch_plan, dict) and isinstance(launch_plan.get("routePlan"), dict) else {}

    plan = {
        "kind": "allincms_browser_execution_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceRehearsalSummary": str(full_e2e_dir.parent / "rehearsal-summary.json"),
        "sourceFullE2E": str(full_e2e_dir),
        "simulatedSource": {
            "siteKey": validation.get("siteKey"),
            "contentType": validation.get("contentType"),
        },
        "siteKeyTemplate": "{realSiteKey}",
        "backendBaseUrlTemplate": "https://workspace.laicms.com/{realSiteKey}",
        "frontendBaseUrlTemplate": "https://{realSiteKey}.web.allincms.com",
        "contentType": validation.get("contentType"),
        "moduleCapture": module_summary,
        "routeExpectations": {
            "staticPaths": route_plan.get("staticPaths", ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us"]),
            "detailRoutePatterns": route_plan.get("detailRoutePatterns", ["/products/{slug}"]),
        },
        "nextSuggestedStage": {
            "stageId": "module_interface_capture",
            "module": handoff_stage.get("module", ""),
            "action": handoff_stage.get("action", ""),
            "targetTemplate": handoff_stage.get("target", "https://workspace.laicms.com/{realSiteKey}/{module}"),
        },
        "stages": [
            stage(
                "refresh_readonly_site_evidence",
                "read-only refresh",
                "read_only",
                "https://workspace.laicms.com/sites and https://workspace.laicms.com/{realSiteKey}/dashboard",
                False,
                "must_not",
                ["open sites list", "open create-site dialog and close it", "open module pages read-only", "redact browser scan"],
                "Stop after redacted scan and run evidence are regenerated.",
                ["existing site keys or empty-list proof", "closed create dialog", "backend module URLs for the same site key"],
                ["submit forms", "click create controls", "save", "publish", "delete", "upload"],
            ),
            stage(
                "create_site_submit",
                "site creation",
                "requires_authorization",
                "https://workspace.laicms.com/sites",
                True,
                "must",
                ["submit create-site form with authorized name and description only"],
                "Stop after site card, backend dashboard, default frontend origin, and module routes are verified.",
                ["create-site preflight", "action-specific authorization record", "site card proof", "backend proof", "frontend proof"],
                ["content upload", "theme mutation", "page mutation", "batch operation", "delete"],
                ["refresh_readonly_site_evidence"],
            ),
            stage(
                "setup_pages_inspection",
                "first-site setup",
                "read_only",
                "https://workspace.laicms.com/{realSiteKey}/{site-info|domains|themes|routes|forms}",
                False,
                "must_not",
                ["inspect site-info", "inspect domains", "inspect themes", "inspect routes", "inspect forms"],
                "Stop after fields, columns, and controls are recorded in redacted evidence.",
                ["site-info fields", "domain controls", "theme controls", "route columns", "form columns"],
                ["save settings", "add domain", "create route", "create form", "apply theme"],
                ["create_site_submit"],
            ),
            stage(
                "module_interface_capture",
                "interface capture",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{module}",
                True,
                "may",
                ["run exactly one capture-plan stage", "capture request URL/method/headers/payload", "verify whether persistence occurred"],
                "Stop after one module/action capture result is redacted and classified.",
                ["fresh authorization", "captured request or explicit UI-only finding", "persistence or no-persistence proof"],
                ["continue to another module", "batch replay", "delete cleanup candidates"],
                ["setup_pages_inspection"],
                "JSON replay is blocked until the exact action payload, ids, and persistence proof are captured.",
            ),
            stage(
                "theme_page_route_launch",
                "theme/page/route launch",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/themes and https://workspace.laicms.com/{realSiteKey}/routes",
                True,
                "must",
                ["save design", "publish page", "enable page", "set homepage", "bind route", "apply theme"],
                "Stop after backend launch readiness and frontend DOM proof are both recorded.",
                ["active theme", "published pages", "enabled pages", "routes bound", "frontend HTTP ok", "frontend DOM verified"],
                ["batch content upload", "domain changes", "delete pages"],
                ["module_interface_capture"],
                "JSON replay can be considered only after each theme/page/route action has a current captured request.",
            ),
            stage(
                "static_frontend_audit",
                "frontend verification",
                "verification",
                "https://{realSiteKey}.web.allincms.com/{staticPath}",
                False,
                "must_not",
                ["audit expected static routes", "record HTTP/DOM/image/rich-text issues"],
                "Stop if any expected static route is not 200 or has blocking rendering issues.",
                ["expected status map", "redacted frontend audit", "frontendRendering evidence"],
                ["backend mutation", "content upload", "publish"],
                ["theme_page_route_launch"],
            ),
            stage(
                "content_probe_create",
                "content probe",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{contentType}",
                True,
                "must",
                ["create one clearly named probe draft for the exact content type"],
                "Stop after the probe draft URL or list-row proof is captured.",
                ["content-type-specific authorization", "probe/test naming proof", "backend draft proof"],
                ["save real business content", "publish", "batch upload", "delete unrelated entries"],
                ["static_frontend_audit"],
            ),
            stage(
                "save_request_capture",
                "request capture",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{contentType}/{contentId}/edit",
                True,
                "must",
                ["save the probe once through UI", "capture the real save request", "verify backend persisted state"],
                "Stop after payload template, field mapping, and persistence proof are recorded.",
                ["request URL", "method", "required headers", "payloadTemplate", "fieldMapping", "backend persistence proof"],
                ["batch replay", "publish without sample verification", "reuse a different content-type schema"],
                ["content_probe_create"],
                "This is the first point where content JSON replay may become possible for this exact content type.",
            ),
            stage(
                "publish_sample_verify",
                "sample verification",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{contentType}/{contentId}/edit",
                True,
                "may",
                ["publish the probe/sample if requested", "verify backend status", "verify frontend detail route"],
                "Stop if frontend detail route, cover/media, rich text, or status is wrong.",
                ["backend published status", "frontend detail 200", "title/name", "cover/media", "structured body"],
                ["batch upload", "cleanup before verification"],
                ["save_request_capture"],
            ),
            stage(
                "manifest_schema_gate",
                "manifest gate",
                "verification",
                "local manifest file",
                False,
                "must_not",
                ["run generic validation", "run require-schema-verified validation"],
                "Stop unless schemaVerified true, fieldMapping, and payloadTemplate all exist from current-site capture.",
                ["validate_manifest.py pass", "validate_manifest.py --require-schema-verified pass"],
                ["upload draft manifest", "fill missing schema from memory"],
                ["save_request_capture"],
            ),
            stage(
                "batch_upload_publish",
                "batch upload",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{contentType}",
                True,
                "must",
                ["upload/update manifest items", "track progress", "handle duplicate slugs", "publish after sample proof"],
                "Stop after progress report and per-entry backend/frontend verification are complete.",
                ["schema gate pass", "sample verification pass", "progress log", "frontend detail audit for each uploaded route"],
                ["upload another content type", "change theme/routes/domains", "delete cleanup candidates"],
                ["manifest_schema_gate", "publish_sample_verify"],
                "Prefer JSON replay only for the captured content type; use UI fallback when browser auth or payload state is uncertain.",
            ),
            stage(
                "forms_media_settings",
                "forms/media/settings",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{forms|media|site-info|domains|tracking}",
                True,
                "must",
                ["mutate one settings/media/forms stage at a time after capture"],
                "Stop after each module's backend and frontend-facing effect is verified.",
                ["action-specific request capture", "backend persisted proof", "public or integration effect proof when applicable"],
                ["treat media/forms/settings as content payloads", "upload local-only image paths", "domain changes without DNS proof"],
                ["batch_upload_publish"],
                "JSON replay is module-specific; media and domains remain UI-first until storage/DNS behavior is captured.",
            ),
            stage(
                "final_frontend_audit",
                "final QA",
                "verification",
                "https://{realSiteKey}.web.allincms.com",
                False,
                "must_not",
                ["audit all static routes and uploaded detail routes", "check covers/media", "check rich text", "check broken links"],
                "Stop if any expected route, image, description, body, or status fails.",
                ["HTTP status report", "DOM/rich-text report", "image report", "broken-entry list empty"],
                ["backend mutation while auditing"],
                ["batch_upload_publish", "forms_media_settings"],
            ),
            stage(
                "cleanup_probes",
                "cleanup",
                "requires_authorization",
                "https://workspace.laicms.com/{realSiteKey}/{contentType}",
                True,
                "must",
                ["delete or unpublish probe/test/Untitled entries only"],
                "Stop after backend absence/unpublished state and frontend 404/non-public proof are recorded.",
                ["cleanup authorization", "candidate list", "backend cleanup proof", "frontend non-public proof"],
                ["delete real entries", "cleanup without candidate list", "batch delete"],
                ["final_frontend_audit"],
            ),
        ],
        "warnings": [
            "This plan is local-only and template-only; it is not browser authorization.",
            "Use only {realSiteKey} templates in user-facing fields until real read-only evidence is refreshed.",
            "JSON acceleration is safer only after current-site request capture, schema gate, and persistence proof.",
        ],
    }
    validation_result = validate_browser_execution_plan(plan)
    if not validation_result["ok"]:
        raise ValueError("browser execution plan validation failed:\n" + "\n".join(f"- {issue}" for issue in validation_result["issues"]))
    return plan


def iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def validate_browser_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if plan.get("kind") != "allincms_browser_execution_plan":
        issues.append("kind must be allincms_browser_execution_plan")
    if plan.get("localOnly") is not True:
        issues.append("browser execution plan must be localOnly")
    if plan.get("remoteMutationsPerformed") is not False:
        issues.append("browser execution plan must record no remote mutations")
    if plan.get("siteKeyTemplate") != "{realSiteKey}":
        issues.append("siteKeyTemplate must be {realSiteKey}")

    stages = plan.get("stages")
    if not isinstance(stages, list):
        issues.append("stages must be an array")
        stages = []
    stage_ids = [stage.get("stageId") for stage in stages if isinstance(stage, dict)]
    for required in REQUIRED_STAGE_IDS:
        if required not in stage_ids:
            issues.append(f"stages missing {required}")
    seen: set[str] = set()
    for index, item in enumerate(stages):
        if not isinstance(item, dict):
            issues.append(f"stages[{index}] must be an object")
            continue
        stage_id = item.get("stageId")
        if not isinstance(stage_id, str) or not stage_id.strip():
            issues.append(f"stages[{index}].stageId must be a non-empty string")
        elif stage_id in seen:
            issues.append(f"duplicate stageId: {stage_id}")
        else:
            seen.add(stage_id)
        if item.get("mode") not in VALID_MODES:
            issues.append(f"stages[{index}].mode must be one of {sorted(VALID_MODES)}")
        requires_auth = item.get("mode") == "requires_authorization"
        if item.get("authorizationRequired") is not requires_auth:
            issues.append(f"stages[{index}].authorizationRequired must match mode")
        expectation = item.get("remoteMutationExpectation")
        if expectation not in REMOTE_MUTATION_EXPECTATIONS:
            issues.append(f"stages[{index}].remoteMutationExpectation must be one of {sorted(REMOTE_MUTATION_EXPECTATIONS)}")
        elif not requires_auth and expectation != "must_not":
            issues.append(f"stages[{index}].remoteMutationExpectation must be must_not for non-authorization stages")
        elif requires_auth and expectation == "must_not":
            issues.append(f"stages[{index}].remoteMutationExpectation must not be must_not for authorization stages")
        for key in ("phase", "targetTemplate", "stopAfter", "jsonReplayRule"):
            if not isinstance(item.get(key), str):
                issues.append(f"stages[{index}].{key} must be a string")
        for key in ("allowedActions", "requiredProof", "forbiddenActions", "dependsOn"):
            values = item.get(key)
            if not isinstance(values, list):
                issues.append(f"stages[{index}].{key} must be an array")
                continue
            if key != "dependsOn" and not values:
                issues.append(f"stages[{index}].{key} must not be empty")
            if not all(isinstance(value, str) and value.strip() for value in values):
                issues.append(f"stages[{index}].{key} must contain non-empty strings")
        for dependency in item.get("dependsOn", []) if isinstance(item.get("dependsOn"), list) else []:
            if dependency not in REQUIRED_STAGE_IDS:
                issues.append(f"stages[{index}].dependsOn contains unknown stage {dependency}")

    text = json.dumps(plan, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append("browser execution plan must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"browser execution plan contains forbidden evidence term: {term}")

    user_facing = {
        "siteKeyTemplate": plan.get("siteKeyTemplate"),
        "backendBaseUrlTemplate": plan.get("backendBaseUrlTemplate"),
        "frontendBaseUrlTemplate": plan.get("frontendBaseUrlTemplate"),
        "nextSuggestedStage": plan.get("nextSuggestedStage"),
        "stages": [
            {
                "targetTemplate": stage.get("targetTemplate"),
                "allowedActions": stage.get("allowedActions"),
                "requiredProof": stage.get("requiredProof"),
                "forbiddenActions": stage.get("forbiddenActions"),
            }
            for stage in stages
            if isinstance(stage, dict)
        ],
    }
    user_facing_text = json.dumps(user_facing, ensure_ascii=False)
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in user_facing_text:
            issues.append("user-facing browser execution plan fields must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", user_facing_text):
        issues.append("user-facing browser execution plan fields must use {realSiteKey} frontend template")

    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local-only staged browser execution plan for AllinCMS.")
    parser.add_argument("full_e2e_dir")
    parser.add_argument("--handoff-json")
    parser.add_argument("--launch-plan-json")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.handoff_json)) if args.handoff_json else None
        launch_plan = load_json(Path(args.launch_plan_json)) if args.launch_plan_json else None
        plan = build_browser_execution_plan(Path(args.full_e2e_dir), handoff, launch_plan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), plan)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
