#!/usr/bin/env python3
"""Run a local-only AllinCMS site-creation evidence chain simulation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

from check_pre_mutation_gate import validate_create_site_gate
from check_round_closeout import validate_closeout
from make_authorization_record import build_record, validate_record as validate_authorization_record
from make_create_preflight_evidence import build_evidence as build_preflight_evidence
from make_create_preflight_evidence import parse_observed_fields, parse_site_key_evidence, parse_site_keys
from make_create_preflight_evidence import validate_empty_site_list_evidence
from make_created_site_evidence import upgrade_evidence
from make_launch_readiness_evidence import build_evidence as build_launch_readiness_evidence
from make_launch_readiness_evidence import parse_checked_paths
from summarize_run_status import summarize as summarize_run_status
from validate_run_evidence import validate as validate_run_evidence


DEFAULT_OBSERVED_CREATE_FIELDS = (
    "button: create site entry 创建站点;dialog title: 创建站点;"
    "input name: name, placeholder: 站点名称;"
    "textarea name: description, placeholder: 站点简介;"
    "submit button: 创建;close button: Close"
)
DEFAULT_LIST_COLUMNS = "媒体,名称,Slug,描述,排序,状态,分类,标签,创建时间"
DEFAULT_EDIT_FIELDS = "name input,slug input,description textarea,body editor,publish/update controls"
MODULES = (
    "dashboard",
    "products",
    "posts",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
)
STATIC_LAUNCH_PATHS = ("/", "/home", "/products", "/solutions", "/about-us", "/contact-us")
DETAIL_ROUTE_PATTERNS = {
    "products": "/products/{slug}",
    "posts": "/posts/{slug}",
}


def split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raise_if_errors(label: str, errors: list[str]) -> None:
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"{label} failed:\n{joined}")


def build_authorization(source: str) -> dict:
    class Args:
        action = "create_site"
        site_key = ""
        target = "https://workspace.laicms.com/sites"
        target_type = "site"
        target_identifier = "pending-new-site"
        fields_or_files = "name,description"
        expected_result = "new site card, backend dashboard, and default frontend open"
        verification_plan = "verify site card, backend dashboard, frontend base URL, and module routes"
        cleanup_plan = "no automatic deletion; stop before content upload"
        authorization_source = source

    return build_record(Args())


def simulated_frontend_rendering(content_type: str) -> dict:
    route_patterns = list(STATIC_LAUNCH_PATHS)
    detail_route = DETAIL_ROUTE_PATTERNS.get(content_type)
    if detail_route:
        route_patterns.append(detail_route)
    expected_statuses = {path: 200 for path in STATIC_LAUNCH_PATHS}
    if detail_route:
        expected_statuses[detail_route] = 404
    return {
        "checked": True,
        "routePatterns": route_patterns,
        "expectedStatuses": expected_statuses,
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }


def simulated_launch_readiness() -> dict:
    return build_launch_readiness_evidence(
        theme_active=True,
        pages_published=True,
        pages_enabled=True,
        routes_bound=True,
        frontend_http_ok=True,
        frontend_dom_verified=True,
        checked_paths=parse_checked_paths(",".join(STATIC_LAUNCH_PATHS)),
        evidence="simulated static launch proof: theme active, pages published/enabled, routes bound, frontend DOM audited",
        blocking_issues=[],
    )["launchReadiness"]


def run_simulation(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = Path(args.output_dir)
    generated_at = datetime.now(timezone.utc).isoformat()
    if args.no_existing_sites:
        existing_site_keys = []
        site_key_evidence = None
        empty_site_list_evidence = validate_empty_site_list_evidence(args.empty_site_list_evidence)
    else:
        existing_site_keys = parse_site_keys(args.existing_site_keys)
        site_key_evidence = parse_site_key_evidence(args.site_key_evidence, existing_site_keys)
        empty_site_list_evidence = None
    observed_fields = parse_observed_fields(args.observed_create_fields)

    preflight = build_preflight_evidence(
        existing_site_keys,
        observed_fields,
        True,
        True,
        None,
        generated_at=generated_at,
        site_key_evidence=site_key_evidence,
        empty_site_list_evidence=empty_site_list_evidence,
    )
    raise_if_errors("preflight validation", validate_run_evidence(preflight))

    authorization = build_authorization(args.authorization_source)
    authorization["generatedAt"] = generated_at
    raise_if_errors("authorization validation", validate_authorization_record(authorization))
    raise_if_errors(
        "pre-mutation gate",
        validate_create_site_gate(preflight, authorization, max_age_minutes=args.max_age_minutes),
    )

    site_key = args.simulated_created_site_key
    module_routes = [f"/{site_key}/{module}" for module in MODULES]
    created = upgrade_evidence(
        preflight,
        site_key,
        args.content_type,
        split_csv(args.list_columns),
        split_csv(args.edit_fields),
        f"site list shows {site_key} card and enter-backend control",
        f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        f"frontend opens at https://{site_key}.web.allincms.com",
        "site-info inspected for name, description, icon upload, notificationEmail, save",
        "domains inspected for CNAME target, domain input, add domain",
        "media inspected for upload controls, asset grid, and URL/public access hints",
        "themes inspected for search, create theme, page/design/preview controls",
        "routes inspected for path, bound page, binding status, notes, updated time",
        "forms inspected for name, slug, description, fields, status, updated time",
        "tracking inspected for Google Tag ID input and add action",
        module_routes,
        ["name", "description"],
        args.authorization_source,
        True,
        None,
        simulated_frontend_rendering(args.content_type) if args.include_simulated_static_launch else None,
        simulated_launch_readiness() if args.include_simulated_static_launch else None,
    )
    raise_if_errors("created-site validation", validate_run_evidence(created))

    paths = {
        "preflight": output_dir / "create-site-preflight.json",
        "authorization": output_dir / "create-site-authorization.json",
        "created": output_dir / "created-site-evidence.json",
        "summary": output_dir / "run-summary.json",
        "closeout": output_dir / "round-closeout.json",
    }
    summary = summarize_run_status(created, str(paths["created"]), require_created_site=True)
    round_issues = getattr(
        args,
        "round_issue",
        ["Checked local create-site simulation and found no reusable skill update needed."],
    )
    closeout = validate_closeout(
        summary,
        args.sedimentation,
        args.closeout_note,
        split_csv(args.changed_files),
        Path(__file__).resolve().parents[1],
        round_issues,
    )
    if not closeout["ok"]:
        raise_if_errors("round closeout", closeout["issues"])
    write_json(paths["preflight"], preflight)
    write_json(paths["authorization"], authorization)
    write_json(paths["created"], created)
    write_json(paths["summary"], summary)
    write_json(paths["closeout"], closeout)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate the AllinCMS create-site evidence chain locally.")
    site_keys = parser.add_mutually_exclusive_group(required=True)
    site_keys.add_argument("--existing-site-keys", help="Comma-separated site keys observed before create")
    site_keys.add_argument("--no-existing-sites", action="store_true")
    parser.add_argument(
        "--site-key-evidence",
        default="",
        help="Required with --existing-site-keys; semicolon-separated strong evidence entries, one per site key",
    )
    parser.add_argument("--empty-site-list-evidence", default="verified empty /sites list")
    parser.add_argument("--simulated-created-site-key", default="simsite01")
    parser.add_argument("--content-type", choices=["posts", "products", "media", "themes", "routes", "forms"], default="products")
    parser.add_argument("--observed-create-fields", default=DEFAULT_OBSERVED_CREATE_FIELDS)
    parser.add_argument("--list-columns", default=DEFAULT_LIST_COLUMNS)
    parser.add_argument("--edit-fields", default=DEFAULT_EDIT_FIELDS)
    parser.add_argument(
        "--include-simulated-static-launch",
        action="store_true",
        help="Include simulated frontendRendering and launchReadiness blocks for static launch routes.",
    )
    parser.add_argument(
        "--authorization-source",
        default="current user explicitly authorizes create site at https://workspace.laicms.com/sites for local simulation only",
        help="Must name create site and https://workspace.laicms.com/sites; local simulation only",
    )
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument(
        "--sedimentation",
        choices=["updated", "none"],
        default="none",
        help="Skill sedimentation outcome for the local simulation closeout.",
    )
    parser.add_argument(
        "--closeout-note",
        default="no reusable skill update needed after checking",
        help="Closeout note checked by check_round_closeout.py.",
    )
    parser.add_argument(
        "--changed-files",
        default="",
        help="Comma-separated skill files changed in this simulated round; used only by the local closeout check.",
    )
    parser.add_argument(
        "--round-issue",
        action="append",
        default=["Checked local create-site simulation and found no reusable skill update needed."],
        help="Issue/no-change observation for the local closeout check.",
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    try:
        paths = run_simulation(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for label, path in paths.items():
        print(f"{label}: {path}")
    print("Local site-creation evidence chain simulation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
