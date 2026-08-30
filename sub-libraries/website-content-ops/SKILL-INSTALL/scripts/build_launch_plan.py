#!/usr/bin/env python3
"""Build a local-only AllinCMS launch proof plan from full rehearsal artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_full_e2e_simulation import validate_directory
from validate_run_evidence import ALLOWED_FRONTEND_ROUTE_PATTERNS, EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


DETAIL_ROUTE_BY_CONTENT_TYPE = {
    "products": "/products/{slug}",
    "posts": "/posts/{slug}",
}
DEFAULT_STATIC_PATHS = ("/", "/home", "/products", "/solutions", "/about-us", "/contact-us")
REQUIRED_GATES = (
    "site_creation",
    "setup_pages",
    "theme_route_launch",
    "frontend_static_audit",
    "module_interface_capture",
    "content_schema_capture",
    "sample_content_upload",
    "batch_content_upload",
    "form_media_settings",
    "final_frontend_audit",
    "probe_cleanup",
)
SIMULATED_SITE_KEYS = ("simsite01", "codexsimulatedsite")


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


def parse_route_patterns(raw: str, default: tuple[str, ...], label: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()] if raw else list(default)
    if not values:
        raise ValueError(f"{label} must contain at least one route pattern")
    for route in values:
        if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
            raise ValueError(f"{label} route must be an allowed redacted pattern, not {route}")
    return values


def infer_content_type(full_e2e_dir: Path, validation: dict[str, Any]) -> str:
    module_scan = load_json(full_e2e_dir / "03-module-interface-plan" / "module-scan.redacted.json")
    content_type = str(module_scan.get("contentType", "")).strip()
    if content_type:
        return content_type
    return str(validation.get("contentType", "")).strip()


def stage_summary(capture_plan: dict[str, Any]) -> dict[str, Any]:
    stages = capture_plan.get("stages")
    if not isinstance(stages, list):
        stages = []
    valid_stages = [stage for stage in stages if isinstance(stage, dict)]
    return {
        "jsonReplayReady": capture_plan.get("jsonReplayReady") is True,
        "stageCount": len(valid_stages),
        "groups": sorted({str(stage.get("group", "")) for stage in valid_stages if stage.get("group")}),
        "modules": sorted({str(stage.get("module", "")) for stage in valid_stages if stage.get("module")}),
    }


def proof_gate(gate: str, current_state: str, real_requirement: str, evidence: str, stop_condition: str) -> dict[str, str]:
    return {
        "gate": gate,
        "currentState": current_state,
        "realRequirement": real_requirement,
        "evidence": evidence,
        "stopCondition": stop_condition,
    }


def build_launch_plan(
    full_e2e_dir: Path,
    handoff: dict[str, Any] | None = None,
    static_paths: list[str] | None = None,
    detail_route_patterns: list[str] | None = None,
) -> dict[str, Any]:
    validation = validate_directory(full_e2e_dir)
    if not validation.get("ok"):
        raise ValueError("full E2E validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))

    capture_plan = load_json(full_e2e_dir / "03-module-interface-plan" / "module-capture-plan.json")
    content_type = infer_content_type(full_e2e_dir, validation)
    static_paths = static_paths or list(DEFAULT_STATIC_PATHS)
    if detail_route_patterns is None:
        detail_route_patterns = [DETAIL_ROUTE_BY_CONTENT_TYPE.get(content_type, "/products/{slug}")]
    selected_stage = handoff.get("selectedStage") if isinstance(handoff, dict) else {}
    if not isinstance(selected_stage, dict):
        selected_stage = {}

    plan = {
        "kind": "allincms_launch_proof_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceFullE2E": str(full_e2e_dir),
        "siteKey": validation.get("siteKey"),
        "contentType": content_type,
        "frontendBaseUrlTemplate": "https://{realSiteKey}.web.allincms.com",
        "backendBaseUrlTemplate": "https://workspace.laicms.com/{realSiteKey}",
        "routePlan": {
            "staticPaths": static_paths,
            "detailRoutePatterns": detail_route_patterns,
            "expectedStatusesBeforeUpload": {**{path: 200 for path in static_paths}, **{path: 404 for path in detail_route_patterns}},
            "expectedStatusesAfterSample": {**{path: 200 for path in static_paths}, **{path: 200 for path in detail_route_patterns}},
        },
        "interfaceCapture": stage_summary(capture_plan),
        "nextCaptureStage": {
            "group": selected_stage.get("group", ""),
            "module": selected_stage.get("module", ""),
            "action": selected_stage.get("action", ""),
            "authorizationAction": selected_stage.get("authorizationAction", ""),
            "targetTemplate": selected_stage.get("target", ""),
            "stopAfter": selected_stage.get("stopAfter", ""),
        },
        "proofGates": [
            proof_gate(
                "site_creation",
                "local_simulated",
                "Real site card, new backend dashboard, and default frontend origin verified for the same site key.",
                "full E2E rehearsal validates created-site evidence shape only.",
                "Stop before upload if site card, backend dashboard, or frontend origin is not verified.",
            ),
            proof_gate(
                "setup_pages",
                "local_simulated",
                "site-info, domains, themes, routes, and forms inspected read-only on the real site.",
                "full E2E rehearsal validates setup-page evidence shape only.",
                "Stop before mutation if any setup module is missing or belongs to the wrong site key.",
            ),
            proof_gate(
                "theme_route_launch",
                "requires_real_backend_and_frontend_proof",
                "Active theme, published pages, enabled pages, bound routes, frontend HTTP success, and DOM content verified.",
                "Use generated launchReadiness evidence after browser checks.",
                "Do not treat active theme, Published status, or HTTP 200 Server Action as launch-ready proof.",
            ),
            proof_gate(
                "frontend_static_audit",
                "requires_real_frontend_audit",
                "Static public routes return expected 200 and have no blocking rendering issues.",
                "Use audit_frontend_rendering.py output converted by make_frontend_rendering_evidence.py.",
                "Stop if Markdown residue, raw HTML text, missing images, or wrong status appears.",
            ),
            proof_gate(
                "module_interface_capture",
                "planned_not_captured",
                "Each create/save/publish/upload/bind action has fresh request capture before JSON replay.",
                "module capture plan groups single-stage browser work by authorization boundary.",
                "Run at most one capture stage per explicit user authorization.",
            ),
            proof_gate(
                "content_schema_capture",
                "planned_not_captured",
                "Current content type save request captured with field mapping and payload template.",
                "manifest upload must wait for schemaVerified true.",
                "Do not upload a product/post manifest from generic draft validation only.",
            ),
            proof_gate(
                "sample_content_upload",
                "local_simulated",
                "One sample item saved, published if requested, backend-verified, frontend detail route verified, and render-audited.",
                "probe lifecycle rehearsal validates evidence states only.",
                "Stop before batch if sample detail route or rich text structure fails.",
            ),
            proof_gate(
                "batch_content_upload",
                "not_started",
                "Every manifest item uploaded or updated with progress tracking, duplicate slug handling, and frontend verification.",
                "batch upload must follow a verified sample.",
                "Do not batch publish until sample backend and frontend proof pass.",
            ),
            proof_gate(
                "form_media_settings",
                "planned_not_captured",
                "Forms, media uploads, site-info, domains, and tracking changed only after action-specific capture and authorization.",
                "module capture plan includes form/media/site settings boundaries.",
                "Prefer UI for media/domain flows until upload/DNS behavior is captured.",
            ),
            proof_gate(
                "final_frontend_audit",
                "not_started",
                "All static routes and uploaded detail routes pass HTTP, DOM, image, rich-text, and status checks.",
                "launch plan defines before/after expected status maps.",
                "Leave frontend list page open only after final audit has no blocking issues.",
            ),
            proof_gate(
                "probe_cleanup",
                "local_simulated",
                "Probe drafts, accidental Untitled items, duplicate slugs, and broken entries are deleted or unpublished with proof.",
                "probe lifecycle rehearsal validates cleanup evidence shape only.",
                "Cleanup needs separate explicit authorization.",
            ),
        ],
        "commandTemplates": {
            "makeLaunchAuditInputs": (
                "python3 skills/allincms-bulk-content-upload/scripts/make_launch_audit_inputs.py "
                "--frontend-base-url https://{realSiteKey}.web.allincms.com "
                f"--static-paths {','.join(static_paths)} "
                f"--detail-probe-paths {','.join(detail_route_patterns)} "
                "--urls-output ~/allincms-projects/allincms-launch-audit-urls.txt "
                "--statuses-output ~/allincms-projects/allincms-launch-expected-statuses.json"
            ),
            "frontendAudit": (
                "python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py "
                "--json --redact --urls-file ~/allincms-projects/allincms-launch-audit-urls.txt "
                "--expect-statuses-file ~/allincms-projects/allincms-launch-expected-statuses.json"
            ),
        },
        "warnings": [
            "This plan is local-only and does not prove a real site is launch-ready.",
            "Do not copy simulated site keys into real authorization text.",
            "Do not use JSON replay until the exact action payload, ids, authorization, and persistence proof are captured.",
        ],
    }
    validation_result = validate_launch_plan(plan)
    if not validation_result["ok"]:
        raise ValueError("launch plan validation failed:\n" + "\n".join(f"- {issue}" for issue in validation_result["issues"]))
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


def validate_launch_plan(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if plan.get("kind") != "allincms_launch_proof_plan":
        issues.append("kind must be allincms_launch_proof_plan")
    if plan.get("localOnly") is not True:
        issues.append("launch plan must be localOnly")
    if plan.get("remoteMutationsPerformed") is not False:
        issues.append("launch plan must record no remote mutations")

    route_plan = plan.get("routePlan")
    if not isinstance(route_plan, dict):
        issues.append("routePlan must be an object")
        route_plan = {}
    for key in ("staticPaths", "detailRoutePatterns"):
        values = route_plan.get(key)
        if not isinstance(values, list) or not values:
            issues.append(f"routePlan.{key} must be a non-empty array")
            continue
        for route in values:
            if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                issues.append(f"routePlan.{key} contains unsupported or concrete route: {route}")

    content_type = plan.get("contentType")
    expected_detail = DETAIL_ROUTE_BY_CONTENT_TYPE.get(str(content_type))
    detail_routes = route_plan.get("detailRoutePatterns")
    if expected_detail and isinstance(detail_routes, list) and expected_detail not in detail_routes:
        issues.append(f"routePlan.detailRoutePatterns must include {expected_detail} for {content_type}")

    for key in ("expectedStatusesBeforeUpload", "expectedStatusesAfterSample"):
        statuses = route_plan.get(key)
        if not isinstance(statuses, dict) or not statuses:
            issues.append(f"routePlan.{key} must be a non-empty object")
            continue
        for route, status in statuses.items():
            if route not in ALLOWED_FRONTEND_ROUTE_PATTERNS:
                issues.append(f"routePlan.{key}.{route} must be a redacted route pattern")
            if status not in {200, 404}:
                issues.append(f"routePlan.{key}.{route} must be 200 or 404")

    gates = plan.get("proofGates")
    if not isinstance(gates, list):
        issues.append("proofGates must be an array")
        gates = []
    gate_names = [gate.get("gate") for gate in gates if isinstance(gate, dict)]
    for required in REQUIRED_GATES:
        if required not in gate_names:
            issues.append(f"proofGates missing {required}")
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            issues.append(f"proofGates[{index}] must be an object")
            continue
        for key in ("gate", "currentState", "realRequirement", "evidence", "stopCondition"):
            if not isinstance(gate.get(key), str) or not gate[key].strip():
                issues.append(f"proofGates[{index}].{key} must be a non-empty string")

    text = json.dumps(plan, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append("launch plan must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"launch plan contains forbidden evidence term: {term}")
    user_facing = [
        plan.get("frontendBaseUrlTemplate"),
        plan.get("backendBaseUrlTemplate"),
        plan.get("commandTemplates"),
        plan.get("nextCaptureStage", {}).get("targetTemplate") if isinstance(plan.get("nextCaptureStage"), dict) else "",
    ]
    user_facing_text = json.dumps(user_facing, ensure_ascii=False)
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in user_facing_text:
            issues.append("user-facing launch plan fields must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", user_facing_text):
        issues.append("user-facing launch plan fields must use {realSiteKey} frontend template")

    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local-only AllinCMS launch proof plan.")
    parser.add_argument("full_e2e_dir")
    parser.add_argument("--handoff-json", help="Optional generated handoff JSON for next-stage context")
    parser.add_argument("--static-paths", default=",".join(DEFAULT_STATIC_PATHS))
    parser.add_argument("--detail-route-patterns", default="")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        handoff = load_json(Path(args.handoff_json)) if args.handoff_json else None
        static_paths = parse_route_patterns(args.static_paths, DEFAULT_STATIC_PATHS, "static paths")
        detail_patterns = parse_route_patterns(args.detail_route_patterns, (), "detail route patterns") if args.detail_route_patterns else None
        plan = build_launch_plan(Path(args.full_e2e_dir), handoff, static_paths, detail_patterns)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        write_json(Path(args.output), plan)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
