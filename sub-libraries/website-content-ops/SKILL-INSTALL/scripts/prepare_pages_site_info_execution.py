#!/usr/bin/env python3
"""Prepare page and site-info browser execution handoff from confirmed plans."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from prepare_browser_stage_authorization import AUTH_PLACEHOLDER
from validate_run_evidence import validate as validate_run_evidence


SUPPORTED_PAGE_ACTIONS = (
    "create_theme_page",
    "save_design",
    "publish_design",
    "enable_theme_page",
    "create_route",
    "bind_route",
)
EXISTING_PAGE_ACTIONS = (
    "save_design",
    "publish_design",
    "enable_theme_page",
    "bind_route",
)


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
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def site_identity(preflight: dict[str, Any]) -> tuple[str, str]:
    site = preflight.get("siteIdentity")
    if not isinstance(site, dict):
        raise SystemExit("ERROR: preflight.siteIdentity is required")
    site_key = site.get("siteKey")
    frontend_base = site.get("frontendBaseUrl")
    if not isinstance(site_key, str) or not site_key.strip() or site_key.startswith("{"):
        raise SystemExit("ERROR: preflight.siteIdentity.siteKey must be concrete")
    if not isinstance(frontend_base, str) or not frontend_base.startswith("https://"):
        raise SystemExit("ERROR: preflight.siteIdentity.frontendBaseUrl must be concrete")
    return site_key, frontend_base.rstrip("/")


def require_setup(preflight: dict[str, Any], key: str, label: str) -> None:
    setup = preflight.get("setupPages")
    if not isinstance(setup, dict) or not isinstance(setup.get(key), list) or not setup[key]:
        raise SystemExit(f"ERROR: preflight.setupPages.{key} evidence is required before preparing {label}")


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "handoff": output_dir / "pages-site-info-browser-handoff.json",
        "summary": output_dir / "pages-site-info-preparation-summary.json",
    }


def plan_items(plan: dict[str, Any]) -> Any:
    return plan.get("items")


def normalize_pages(pages_plan: dict[str, Any]) -> list[dict[str, Any]]:
    items = plan_items(pages_plan)
    if not isinstance(items, list):
        raise SystemExit("ERROR: pages plan items must be an array")
    pages: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"Page {index + 1}").strip()
        path = str(item.get("path") or f"/page-{index + 1}").strip()
        if not path.startswith("/"):
            path = "/" + path
        sections = item.get("sections")
        section_count = len(sections) if isinstance(sections, list) else 0
        pages.append(
            {
                "title": title,
                "path": path,
                "purpose": str(item.get("purpose") or "content_page"),
                "sectionCount": section_count,
                "sourceRefs": [ref for ref in item.get("sourceRefs", []) if isinstance(ref, str)]
                if isinstance(item.get("sourceRefs"), list)
                else [],
            }
        )
    if not pages:
        raise SystemExit("ERROR: pages plan must contain at least one page")
    return pages


def normalize_navigation(navigation_plan: dict[str, Any] | None) -> dict[str, Any]:
    if not navigation_plan:
        return {"items": [], "sourcePlanPresent": False}
    items = plan_items(navigation_plan)
    if not isinstance(items, dict):
        raise SystemExit("ERROR: navigation plan items must be an object")
    raw_items = items.get("items")
    if not isinstance(raw_items, list):
        raise SystemExit("ERROR: navigation plan items.items must be an array")
    normalized: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or f"Navigation {index + 1}").strip()
        path = str(item.get("path") or "").strip()
        if not label or not path:
            continue
        if not path.startswith("/"):
            path = "/" + path
        if path in seen_paths:
            continue
        normalized.append({"label": label, "path": path})
        seen_paths.add(path)
    return {"items": normalized, "sourcePlanPresent": True}


def navigation_issues(navigation: dict[str, Any], pages: list[dict[str, Any]]) -> list[str]:
    items = navigation.get("items") if isinstance(navigation.get("items"), list) else []
    paths = {item.get("path") for item in items if isinstance(item, dict)}
    page_paths = {page["path"] for page in pages}
    issues: list[str] = []
    if not navigation.get("sourcePlanPresent"):
        issues.append("navigation plan not supplied; confirmed navigation cannot be prepared for route verification")
    elif not items:
        issues.append("navigation plan has no items")
    for required in sorted(page_paths):
        if required not in paths:
            issues.append(f"navigation plan missing page path {required}")
    return issues


def setup_text(preflight: dict[str, Any], key: str) -> str:
    setup = preflight.get("setupPages")
    if not isinstance(setup, dict):
        return ""
    value = setup.get(key)
    if isinstance(value, list):
        return "\n".join(item for item in value if isinstance(item, str))
    return ""


def default_template_state(preflight: dict[str, Any]) -> dict[str, Any]:
    themes_text = setup_text(preflight, "themes")
    routes_text = setup_text(preflight, "routes")
    combined = f"{themes_text}\n{routes_text}".lower()
    existing_paths = sorted({path for path in ("/", "/home", "/products", "/posts", "/about-us", "/contact-us") if path in combined})
    default_theme_detected = (
        "default" in combined
        and any(term in combined for term in ("active", "启用", "starter theme", "pages/design/preview"))
    )
    has_route_table = any(term in combined for term in ("default route", "已绑定", "bound page", "routes page shows"))
    return {
        "defaultTemplateDetected": default_theme_detected,
        "defaultRoutesDetected": has_route_table,
        "existingRoutePaths": existing_paths,
        "reuseExistingPagesFirst": default_theme_detected or has_route_table,
        "evidence": {
            "themes": themes_text,
            "routes": routes_text,
        },
    }


def site_info_payload(site_info_plan: dict[str, Any]) -> dict[str, Any]:
    items = plan_items(site_info_plan)
    if not isinstance(items, dict):
        raise SystemExit("ERROR: site-info plan items must be an object")
    proposal = items.get("siteProposal") if isinstance(items.get("siteProposal"), dict) else {}
    site_info = items.get("siteInfo") if isinstance(items.get("siteInfo"), dict) else {}
    name = str(proposal.get("siteName") or site_info.get("name") or "").strip()
    description = str(proposal.get("siteDescription") or site_info.get("description") or "").strip()
    if not name:
        raise SystemExit("ERROR: site-info plan must provide site name")
    if not description:
        raise SystemExit("ERROR: site-info plan must provide site description")
    return {
        "name": name,
        "description": description,
        "language": str(proposal.get("language") or site_info.get("language") or "").strip(),
        "industry": str(proposal.get("industry") or site_info.get("industry") or "").strip(),
        "userConfirmedFields": ["name", "description"],
        "requiresUserConfirmationBeforeLiveSave": [
            "notificationEmail",
            "legalCompanyName",
            "publicContactChannels",
            "customDomain",
            "trackingCode",
        ],
    }


def authorization_template(
    *,
    action: str,
    site_key: str,
    target: str,
    target_type: str,
    target_identifier: str,
    fields: list[str],
    expected: str,
    verification: str,
    cleanup: str,
    output_path: str,
) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        f"--action {action} "
        f"--site-key {site_key} "
        f"--target {target} "
        f"--target-type {target_type} "
        f"--target-identifier '{target_identifier}' "
        f"--fields-or-files {','.join(fields)} "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{AUTH_PLACEHOLDER}' "
        f"--output {output_path}"
    )


def gate_template(action: str, preflight_path: str, authorization_path: str) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        f"--action {action} "
        f"--preflight {preflight_path} "
        f"--authorization {authorization_path}"
    )


def page_actions(
    page: dict[str, Any],
    *,
    site_key: str,
    target: str,
    preflight_path: str,
    output_dir: Path,
    default_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    slug = page["path"].strip("/").replace("/", "-") or "home"
    path = page["path"]
    existing_paths = set(default_state.get("existingRoutePaths", []) if isinstance(default_state, dict) else [])
    reuse_existing = bool(default_state and default_state.get("reuseExistingPagesFirst")) and (
        path in existing_paths or (path == "/" and "/home" in existing_paths)
    )
    actions_to_prepare = EXISTING_PAGE_ACTIONS if reuse_existing else SUPPORTED_PAGE_ACTIONS
    actions: list[dict[str, Any]] = []
    for action in actions_to_prepare:
        authorization_path = output_dir / f"authorization-{slug}-{action}.json"
        target_type = "theme-page" if action in {"create_theme_page", "enable_theme_page"} else "theme-design" if action in {"save_design", "publish_design"} else "routes"
        action_target = target if action in {"create_theme_page", "enable_theme_page"} else f"https://workspace.laicms.com/{site_key}/routes" if action in {"create_route", "bind_route"} else f"{target}/{{pageId}}/design"
        fields = {
            "create_theme_page": ["requestCapture", "pageId", "routePath", "backendVerified"],
            "save_design": ["requestCapture", "pageDocument", "persistedVerified"],
            "publish_design": ["publishStatus", "frontendVerified"],
            "enable_theme_page": ["enabled", "frontendVerified"],
            "create_route": ["routePath", "backendVerified", "frontendVerified"],
            "bind_route": ["routePath", "boundPage", "frontendVerified"],
        }[action]
        actions.append(
            {
                "action": action,
                "target": action_target,
                "targetType": target_type,
                "targetIdentifier": f"{page['path']} {action}",
                "authorizationOutput": str(authorization_path),
                "authorizationRecordCommand": authorization_template(
                    action=action,
                    site_key=site_key,
                    target=action_target,
                    target_type=target_type,
                    target_identifier=f"{page['path']} {action}",
                    fields=fields,
                    expected=f"{page['path']} {action} proof is recorded",
                    verification="verify backend request/state and public frontend proof when applicable",
                    cleanup="stop after this page action proof; neighboring page actions require separate authorization",
                    output_path=str(authorization_path),
                ),
                "preMutationGateCommand": gate_template(action, preflight_path, str(authorization_path)),
                "requiresConcreteTargetBeforeAuthorization": "{pageId}" in action_target,
                "browserStepsExecutable": False,
                "existingPageReuse": reuse_existing,
            }
        )
    return actions


def page_handoff_entry(
    page: dict[str, Any],
    *,
    site_key: str,
    frontend_base: str,
    theme_target: str,
    preflight_path: str,
    output_dir: Path,
    default_state: dict[str, Any],
) -> dict[str, Any]:
    actions = page_actions(
        page,
        site_key=site_key,
        target=theme_target,
        preflight_path=preflight_path,
        output_dir=output_dir,
        default_state=default_state,
    )
    return {
        "page": page,
        "frontendTarget": frontend_base + ("" if page["path"] == "/" else page["path"]),
        "themeTargetTemplate": theme_target,
        "actions": actions,
        "executionStrategy": "reuse_existing_theme_page_first"
        if any(action.get("existingPageReuse") for action in actions)
        else "create_missing_theme_page",
        "browserStepsExecutable": False,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    paths = artifact_paths(output_dir)
    pages_plan = load_json(Path(args.pages_plan), "pages plan")
    site_info_plan = load_json(Path(args.site_info_plan), "site-info plan")
    navigation_plan = load_json(Path(args.navigation_plan), "navigation plan") if getattr(args, "navigation_plan", "") else None
    preflight = load_json(Path(args.preflight), "preflight")
    preflight_errors = validate_run_evidence(preflight)
    if preflight_errors:
        raise SystemExit("ERROR: invalid preflight/run evidence:\n- " + "\n- ".join(preflight_errors))
    site_key, frontend_base = site_identity(preflight)
    require_setup(preflight, "siteInfo", "site-info save handoff")
    require_setup(preflight, "themes", "page/theme handoff")
    require_setup(preflight, "routes", "route handoff")
    default_state = default_template_state(preflight)

    pages = normalize_pages(pages_plan)
    navigation = normalize_navigation(navigation_plan)
    nav_issues = navigation_issues(navigation, pages)
    site_info = site_info_payload(site_info_plan)
    theme_target = args.theme_target.strip() or f"https://workspace.laicms.com/{site_key}/themes/{{themeId}}"
    site_info_target = f"https://workspace.laicms.com/{site_key}/site-info"
    site_info_authorization = output_dir / "authorization-site-info-save.json"

    handoff = {
        "kind": "allincms_pages_site_info_browser_handoff",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourcePagesPlan": args.pages_plan,
        "sourceSiteInfoPlan": args.site_info_plan,
        "sourcePreflight": args.preflight,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "siteInfo": {
            "target": site_info_target,
            "draftFields": site_info,
            "authorizationOutput": str(site_info_authorization),
            "authorizationRecordCommand": authorization_template(
                action="save_site_settings",
                site_key=site_key,
                target=site_info_target,
                target_type="site-info",
                target_identifier="site-info settings from confirmed source package",
                fields=["fieldMapping", "persistedVerified"],
                expected="site-info name/description save request and persisted state are verified",
                verification="capture site-info save request and verify backend or frontend metadata state",
                cleanup="stop after site-info save proof; domains/tracking/contact changes require separate authorization",
                output_path=str(site_info_authorization),
            ),
            "preMutationGateCommand": gate_template("save_site_settings", args.preflight, str(site_info_authorization)),
            "browserStepsExecutable": False,
        },
        "navigation": {
            "items": navigation["items"],
            "sourceNavigationPlan": getattr(args, "navigation_plan", ""),
            "issues": nav_issues,
            "routeVerificationRequired": True,
            "browserStepsExecutable": False,
        },
        "defaultTemplateState": default_state,
        "pages": [
            page_handoff_entry(
                page,
                site_key=site_key,
                frontend_base=frontend_base,
                theme_target=theme_target,
                preflight_path=args.preflight,
                output_dir=output_dir,
                default_state=default_state,
            )
            for page in pages
        ],
        "mustRunBeforeBrowserMutation": [
            "replace themeTargetTemplate placeholders with concrete theme/page URLs from current browser evidence",
            "when defaultTemplateState.reuseExistingPagesFirst is true, map existing default theme pages/routes before creating any new page",
            "generate one action-specific authorization record from current user instruction",
            "run the matching preMutationGateCommand and require it to pass",
            "capture request and backend/frontend proof for that one action before moving to the next action",
        ],
        "forbiddenActions": [
            "treating pages-plan or site-info-plan as replay payloads",
            "saving design before current pageDocument/request schema is captured",
            "creating or binding routes with placeholder themeId/pageId targets",
            "combining site-info save with domains, tracking, media upload, forms, products, posts, or cleanup",
            "creating duplicate Home/About/Contact/Products/Posts pages when the default theme already provides matching pages/routes",
            "claiming public page launch before save, publish, enable, route binding, and frontend DOM proof all pass",
            "claiming navigation is implemented before each confirmed navigation path is present in public frontend links or routes",
        ],
        "warning": "This handoff is local preparation only; every listed action remains non-executable until action-time authorization and the pre-mutation gate pass.",
    }
    write_json(paths["handoff"], handoff)

    summary = {
        "kind": "allincms_pages_site_info_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": site_key,
        "pageCount": len(pages),
        "navigationItemCount": len(navigation["items"]),
        "navigationIssues": nav_issues,
        "defaultTemplateState": default_state,
        "artifacts": {"handoff": str(paths["handoff"])},
        "readyForBrowserStage": "blocked_navigation_plan" if nav_issues else "ready_to_prepare_action_specific_authorization",
        "nextAction": (
            "repair or confirm navigation plan before preparing page/site-info browser actions"
            if nav_issues
            else "choose exactly one site-info/page action, replace placeholders with current browser evidence, request action-time authorization, then run the pre-mutation gate"
        ),
        "adversarialChecks": [
            "Pages and site-info plans are source-confirmed drafts, not AllinCMS replay payloads.",
            "Homepage/single-page public launch requires separate create/save/publish/enable/route/frontend proof.",
            "Site-info save must not be bundled with domains, tracking, notification email, forms, media, products, posts, or cleanup.",
            "Any action target containing {themeId} or {pageId} is template-only and must be rebound from live browser evidence before authorization.",
            "Confirmed navigation paths must be checked against generated page paths and later public frontend links.",
        ],
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare pages/site-info browser handoff from confirmed plans.")
    parser.add_argument("--pages-plan", required=True)
    parser.add_argument("--site-info-plan", required=True)
    parser.add_argument("--navigation-plan", default="")
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--theme-target", default="", help="Optional concrete or templated theme page-list URL")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    print(f"Wrote pages/site-info preparation summary: {summary['artifacts']['handoff']}")
    print(f"siteKey={summary['siteKey']} pageCount={summary['pageCount']} nextAction={summary['nextAction']}")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
