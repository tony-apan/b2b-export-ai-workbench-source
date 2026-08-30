#!/usr/bin/env python3
"""Apply validated default-theme bootstrap evidence to created-site evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from prepare_created_site_schema_capture import build as build_created_site_schema_capture
from validate_default_theme_bootstrap_evidence import validate_evidence as validate_bootstrap_evidence
from validate_run_evidence import validate as validate_run_evidence


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


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


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def require_created_site(data: dict[str, Any]) -> str:
    site_creation = data.get("siteCreation")
    if not isinstance(site_creation, dict) or site_creation.get("status") != "created_verified":
        raise ValueError("created-site evidence must have siteCreation.status=created_verified")
    site_identity = data.get("siteIdentity")
    if not isinstance(site_identity, dict) or not isinstance(site_identity.get("siteKey"), str):
        raise ValueError("created-site evidence must include siteIdentity.siteKey")
    site_key = site_identity["siteKey"]
    if site_creation.get("createdSiteKey") != site_key:
        raise ValueError("createdSiteKey must match siteIdentity.siteKey")
    return site_key


def normalize_checked_routes(routes: Any) -> list[str]:
    if not isinstance(routes, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, str) or not route.strip():
            continue
        route = route.strip()
        if route not in seen:
            seen.add(route)
            result.append(route)
    return result


def frontend_route_patterns(frontend: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for row in frontend.get("checkedPaths", []):
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        normalized = path.strip()
        if normalized not in seen:
            seen.add(normalized)
            patterns.append(normalized)
    return patterns


def build_frontend_rendering(evidence: dict[str, Any]) -> dict[str, Any]:
    frontend = evidence.get("frontend") if isinstance(evidence.get("frontend"), dict) else {}
    route_patterns = frontend_route_patterns(frontend)
    expected_statuses = {route: 200 for route in route_patterns}
    return {
        "checked": True,
        "routePatterns": route_patterns,
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "expectedStatuses": expected_statuses,
        "blockingIssues": [],
        "evidence": "default-theme bootstrap verified required starter paths with non-empty public DOM; business content still requires later replacement",
    }


def build_launch_readiness(evidence: dict[str, Any]) -> dict[str, Any]:
    frontend = evidence.get("frontend") if isinstance(evidence.get("frontend"), dict) else {}
    return {
        "checked": True,
        "themeActive": True,
        "pagesPublished": True,
        "pagesEnabled": True,
        "routesBound": True,
        "frontendHttpOk": True,
        "frontendDomVerified": True,
        "checkedPaths": frontend_route_patterns(frontend),
        "evidence": "default-theme bootstrap only: active default theme, bound starter routes, and non-empty public DOM were verified; launch content remains incomplete",
        "blockingIssues": [],
    }


def apply_bootstrap(
    created: dict[str, Any],
    runbook: dict[str, Any],
    bootstrap: dict[str, Any],
    *,
    created_path: Path,
    runbook_path: Path,
    bootstrap_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    site_key = require_created_site(created)
    issues = validate_bootstrap_evidence(bootstrap, runbook)
    validation = {
        "kind": "allincms_default_theme_bootstrap_evidence_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "evidence": str(bootstrap_path),
        "runbook": str(runbook_path),
        "siteKey": bootstrap.get("siteKey"),
        "themeId": bootstrap.get("themeId"),
        "pageCount": bootstrap.get("pageCount"),
        "issues": issues,
        "nextStageReady": not issues,
        "nextActions": [
            "Proceed to source pages/site-info, taxonomy, and content schema capture; default template content still needs replacement."
            if not issues
            else "Fix bootstrap evidence gaps before using the default theme as launch foundation."
        ],
    }
    if issues:
        return created, validation
    if bootstrap.get("siteKey") != site_key:
        validation["valid"] = False
        validation["issues"].append("bootstrap evidence siteKey must match created-site evidence siteKey")
        validation["nextStageReady"] = False
        return created, validation

    merged = json.loads(json.dumps(created, ensure_ascii=False))
    setup_pages = merged.setdefault("setupPages", {})
    if not isinstance(setup_pages, dict):
        raise ValueError("created-site evidence setupPages must be an object when present")

    theme_id = str(bootstrap.get("themeId"))
    page_count = int(bootstrap.get("pageCount", 0))
    checked_routes = normalize_checked_routes((bootstrap.get("routes") or {}).get("checkedRoutes") if isinstance(bootstrap.get("routes"), dict) else [])
    setup_pages["themes"] = [
        f"default-theme bootstrap validated from {bootstrap_path}: preset=默认 themeId={theme_id} pageCount={page_count}",
        "theme activation verified after separate activate_theme authorization; default template content still requires replacement",
    ]
    setup_pages["routes"] = [
        f"default-theme bootstrap routes bound from {bootstrap_path}: {', '.join(checked_routes)}",
        "public starter routes verified non-empty; business route/page copy remains a later pages/site-info and launch gate",
    ]

    merged["defaultThemeBootstrap"] = {
        "appliedAt": now_iso(),
        "sourceCreatedSiteEvidence": str(created_path),
        "runbook": str(runbook_path),
        "evidence": str(bootstrap_path),
        "validation": "default-theme-bootstrap-validation.json",
        "siteKey": site_key,
        "themeId": theme_id,
        "pageCount": page_count,
        "preset": bootstrap.get("preset"),
        "routesBound": True,
        "frontendDomVerified": True,
        "businessContentComplete": False,
        "note": "Foundation proof only; does not satisfy page copy, taxonomy, products/posts schema capture, sample upload, batch upload, forms/media/settings, or launch acceptance.",
    }
    merged["frontendRendering"] = build_frontend_rendering(bootstrap)
    merged["launchReadiness"] = build_launch_readiness(bootstrap)

    local_checks = merged.setdefault("localChecks", {})
    if not isinstance(local_checks, dict):
        raise ValueError("created-site evidence localChecks must be an object when present")
    local_checks["defaultThemeBootstrapApplied"] = str(bootstrap_path)
    local_checks["defaultThemeBootstrapNote"] = (
        "Validated default theme creation and activation evidence was merged as foundation proof only; "
        "remote mutations already happened in the authorized browser stage."
    )

    run_errors = validate_run_evidence(merged)
    if run_errors:
        validation["valid"] = False
        validation["nextStageReady"] = False
        validation["issues"].extend(f"merged created-site evidence: {error}" for error in run_errors)
    return merged, validation


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "validation": output_dir / "default-theme-bootstrap-validation.json",
        "created": output_dir / "created-site-evidence.after-default-theme-bootstrap.json",
        "schema_capture_dir": output_dir / "created-site-schema-capture-after-default-theme-bootstrap",
        "summary": output_dir / "default-theme-bootstrap-apply-summary.json",
    }


def has_schema_capture_inputs(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "prepare_created_site_schema_capture", False)
        and getattr(args, "artifact_readiness", "")
    )


def build_downstream_schema_capture(args: argparse.Namespace, paths: dict[str, Path]) -> dict[str, Any] | None:
    if not has_schema_capture_inputs(args):
        return None
    return build_created_site_schema_capture(
        SimpleNamespace(
            artifact_readiness=args.artifact_readiness,
            created_site_evidence=str(paths["created"]),
            package=args.package,
            review_packet=args.review_packet,
            confirmation=args.confirmation,
            execution_plan=args.execution_plan,
            authorization_dir=args.authorization_dir,
            theme_target=args.theme_target,
            output_dir=str(paths["schema_capture_dir"]),
            json=False,
        )
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    created_path = Path(args.created_site_evidence)
    runbook_path = Path(args.runbook)
    bootstrap_path = Path(args.bootstrap_evidence)
    created = load_json(created_path, "created-site evidence")
    runbook = load_json(runbook_path, "default-theme bootstrap runbook")
    bootstrap = load_json(bootstrap_path, "default-theme bootstrap evidence")

    merged, validation = apply_bootstrap(
        created,
        runbook,
        bootstrap,
        created_path=created_path,
        runbook_path=runbook_path,
        bootstrap_path=bootstrap_path,
    )
    write_json(paths["validation"], validation)
    downstream_summary: dict[str, Any] | None = None
    if validation["valid"]:
        write_json(paths["created"], merged)
        downstream_summary = build_downstream_schema_capture(args, paths)
    elif args.fail_on_invalid:
        raise SystemExit("ERROR: default-theme bootstrap evidence invalid:\n- " + "\n- ".join(validation["issues"]))

    downstream_artifacts = downstream_summary.get("artifacts", {}) if isinstance(downstream_summary, dict) else {}
    summary = {
        "kind": "allincms_default_theme_bootstrap_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": bootstrap.get("siteKey"),
        "validationValid": validation["valid"],
        "artifacts": {
            "defaultThemeBootstrapValidation": str(paths["validation"]),
            "createdSiteEvidenceAfterDefaultThemeBootstrap": str(paths["created"]) if validation["valid"] else "",
            "createdSiteSchemaCapturePreparation": str(paths["schema_capture_dir"] / "created-site-schema-capture-preparation-summary.json")
            if downstream_summary
            else "",
            "sourceExecutionStatus": downstream_artifacts.get("sourceExecutionStatus", ""),
            "sourceNextStageHandoff": downstream_artifacts.get("sourceNextStageHandoff", ""),
        },
        "validation": {"issues": validation["issues"]},
        "downstreamPreparation": {
            "requested": bool(getattr(args, "prepare_created_site_schema_capture", False)),
            "ran": downstream_summary is not None,
            "blockedReason": ""
            if downstream_summary
            else (
                "artifact readiness is required to prepare created-site schema capture"
                if getattr(args, "prepare_created_site_schema_capture", False)
                else ""
            ),
        },
        "adversarialChecks": [
            "This helper applies already-captured redacted evidence only; it does not create or activate a theme.",
            "Default-theme bootstrap proof is foundation proof, not business-content completion.",
            "Use the refreshed created-site evidence for subsequent pages/site-info, taxonomy, and schema-capture preparation.",
            "Downstream created-site schema-capture preparation is local-only and runs only when explicitly requested with artifact readiness context.",
            "Do not skip products/posts schema capture, sample upload, batch upload, forms/media/settings, or final launch acceptance.",
        ],
        "nextAction": (
            "follow artifacts.sourceNextStageHandoff from downstream created-site schema-capture preparation"
            if downstream_summary
            else "rerun created-site schema-capture preparation with created-site-evidence.after-default-theme-bootstrap.json"
            if validation["valid"]
            else "fix default-theme bootstrap evidence before refreshing created-site evidence"
        ),
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply default-theme bootstrap evidence to created-site evidence.")
    parser.add_argument("--created-site-evidence", required=True)
    parser.add_argument("--runbook", required=True)
    parser.add_argument("--bootstrap-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--prepare-created-site-schema-capture",
        action="store_true",
        help="After applying bootstrap evidence, rerun local created-site schema-capture preparation from the refreshed evidence.",
    )
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="")
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = build(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote default-theme bootstrap apply summary: {summary['artifacts']['defaultThemeBootstrapValidation']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    return 0 if summary["validationValid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
