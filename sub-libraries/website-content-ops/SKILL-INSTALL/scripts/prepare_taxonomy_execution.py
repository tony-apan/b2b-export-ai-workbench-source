#!/usr/bin/env python3
"""Prepare local taxonomy create/map runbook from a confirmed taxonomy plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from prepare_browser_stage_authorization import AUTH_PLACEHOLDER
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


def plan_items(plan: dict[str, Any]) -> dict[str, Any]:
    items = plan.get("items")
    if not isinstance(items, dict):
        raise SystemExit("ERROR: taxonomy plan items must be an object")
    return items


def site_identity(preflight: dict[str, Any]) -> tuple[str, str]:
    errors = validate_run_evidence(preflight)
    if errors:
        raise SystemExit("ERROR: invalid preflight/run evidence:\n- " + "\n- ".join(errors))
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


def require_taxonomy_preflight(preflight: dict[str, Any]) -> list[str]:
    setup = preflight.get("setupPages")
    missing: list[str] = []
    for key in ("products", "posts"):
        if not isinstance(setup, dict) or not isinstance(setup.get(key), list) or not setup[key]:
            missing.append(f"preflight.setupPages.{key}")
    identity = preflight.get("siteIdentity") if isinstance(preflight.get("siteIdentity"), dict) else {}
    routes = identity.get("moduleRoutes")
    for route in ("products", "posts"):
        site_key = identity.get("siteKey", "")
        expected = f"/{site_key}/{route}" if isinstance(site_key, str) else ""
        if not isinstance(routes, list) or expected not in routes:
            missing.append(f"siteIdentity.moduleRoutes:{expected}")
    return missing


def as_terms(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    terms: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("name") or "").strip()
        slug = str(item.get("slug") or "").strip()
        if not label or not slug:
            continue
        terms.append(
            {
                "label": label,
                "slug": slug,
                "sourceRefs": [ref for ref in item.get("sourceRefs", []) if isinstance(ref, str)]
                if isinstance(item.get("sourceRefs"), list)
                else [],
            }
        )
    return terms


def taxonomy_scopes(items: dict[str, Any]) -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    return [
        ("productCategories", "products", "category", as_terms(items.get("productCategories"))),
        ("productTags", "products", "tag", as_terms(items.get("productTags"))),
        ("postCategories", "posts", "category", as_terms(items.get("postCategories"))),
        ("postTags", "posts", "tag", as_terms(items.get("postTags"))),
    ]


def authorization_command(
    *,
    action: str,
    site_key: str,
    target: str,
    target_type: str,
    target_identifier: str,
    output: str,
) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        f"--action {action} "
        f"--site-key {site_key} "
        f"--target {target} "
        f"--target-type {target_type} "
        f"--target-identifier '{target_identifier}' "
        "--fields-or-files requestCapture,taxonomyTerm,backendVerified,mappingVerified "
        "--expected-result 'taxonomy term is created or mapped and backend proof is recorded' "
        "--verification-plan 'verify category/tag row or selector option exists, then stop before product/post upload' "
        "--cleanup-plan 'do not delete taxonomy terms unless a separate cleanup authorization is created' "
        f"--authorization-source '{AUTH_PLACEHOLDER}' "
        f"--output {output}"
    )


def gate_command(action: str, preflight_path: str, authorization_path: str) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        f"--action {action} "
        f"--preflight {preflight_path} "
        f"--authorization {authorization_path}"
    )


def build_term_action(
    *,
    site_key: str,
    content_type: str,
    term_kind: str,
    term: dict[str, Any],
    preflight_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    action = f"create_or_map_{content_type}_{term_kind}"
    slug = term["slug"]
    target = f"https://workspace.laicms.com/{site_key}/{content_type}?tab={term_kind}s"
    authorization = output_dir / f"authorization-{action}-{slug}.json"
    return {
        "action": action,
        "contentType": content_type,
        "termKind": term_kind,
        "term": term,
        "target": target,
        "targetType": f"{content_type}-{term_kind}",
        "targetIdentifier": f"{content_type}:{term_kind}:{slug}",
        "authorizationOutput": str(authorization),
        "authorizationRecordCommand": authorization_command(
            action=action,
            site_key=site_key,
            target=target,
            target_type=f"{content_type}-{term_kind}",
            target_identifier=f"{content_type}:{term_kind}:{slug}",
            output=str(authorization),
        ),
        "preMutationGateCommand": gate_command(action, preflight_path, str(authorization)),
        "requiresSchemaCapture": True,
        "requiresCreateOrMapProof": True,
        "browserStepsExecutable": False,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    taxonomy_plan = load_json(Path(args.taxonomy_plan), "taxonomy plan")
    preflight = load_json(Path(args.preflight), "preflight")
    site_key, frontend_base = site_identity(preflight)
    items = plan_items(taxonomy_plan)
    missing_preflight = require_taxonomy_preflight(preflight)

    actions: list[dict[str, Any]] = []
    term_counts: dict[str, int] = {}
    for field, content_type, term_kind, terms in taxonomy_scopes(items):
        term_counts[field] = len(terms)
        for term in terms:
            actions.append(
                build_term_action(
                    site_key=site_key,
                    content_type=content_type,
                    term_kind=term_kind,
                    term=term,
                    preflight_path=args.preflight,
                    output_dir=output_dir,
                )
            )

    handoff = {
        "kind": "allincms_taxonomy_execution_handoff",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourceTaxonomyPlan": args.taxonomy_plan,
        "sourcePreflight": args.preflight,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        "taxonomyPlanStatus": str(items.get("status") or ""),
        "termCounts": term_counts,
        "actions": actions,
        "preflightIssues": missing_preflight,
        "browserStepsExecutable": False,
        "readyForBrowserStage": "blocked_taxonomy_preflight" if missing_preflight else "ready_to_prepare_action_specific_taxonomy_authorization",
        "mustRunBeforeProductPostUpload": [
            "inspect current products/posts category and tag UI or capture request schema",
            "create or map every required taxonomy term one action at a time",
            "validate taxonomy execution evidence before relying on categories/tags in product/post manifests",
        ],
        "forbiddenActions": [
            "treating taxonomy labels as remote category or tag IDs",
            "creating categories/tags without action-specific authorization",
            "uploading products/posts with taxonomy before taxonomy execution evidence passes",
            "assuming product taxonomy and post taxonomy share the same schema",
        ],
        "evidenceTemplate": {
            "kind": "allincms_taxonomy_execution_evidence",
            "siteKey": site_key,
            "remoteMutationsPerformed": True,
            "preMutationGatesPassed": True,
            "taxonomyMappings": [],
            "blockingIssues": [],
            "stopConditionMet": True,
        },
    }
    output = output_dir / "taxonomy-execution-handoff.json"
    summary_path = output_dir / "taxonomy-execution-preparation-summary.json"
    write_json(output, handoff)
    summary = {
        "kind": "allincms_taxonomy_execution_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": site_key,
        "termCounts": term_counts,
        "actionCount": len(actions),
        "preflightIssues": missing_preflight,
        "readyForBrowserStage": handoff["readyForBrowserStage"],
        "artifacts": {"handoff": str(output)},
        "nextAction": (
            "refresh products/posts category/tag read-only evidence before taxonomy execution"
            if missing_preflight
            else "choose exactly one taxonomy action, capture schema or UI proof, request action-time authorization, then run the pre-mutation gate"
        ),
        "adversarialChecks": handoff["forbiddenActions"],
    }
    write_json(summary_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare taxonomy create/map browser handoff from confirmed taxonomy plan.")
    parser.add_argument("--taxonomy-plan", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = build(args)
    print(f"Wrote taxonomy execution preparation summary: {summary['artifacts']['handoff']}")
    print(f"siteKey={summary['siteKey']} actionCount={summary['actionCount']} ready={summary['readyForBrowserStage']}")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
