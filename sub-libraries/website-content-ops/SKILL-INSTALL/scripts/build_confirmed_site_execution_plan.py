#!/usr/bin/env python3
"""Build a local execution plan after source package confirmation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_package_confirmation import load_json, validate_confirmation_with_review_packet
from validate_source_package_confirmation import validate_content_goal_overages
from validate_source_package_confirmation import validate_source_review_objective_coverage
from content_goal_coverage_utils import source_review_objective_coverage_binding_issues
from validate_source_package_review_packet import load_json as load_review_packet_json
from validate_source_site_package import content_goal_coverage, validate_package


SHA256_HEX_LEN = 64


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_counts(package: dict[str, Any]) -> dict[str, int]:
    plan = package.get("contentPlan") if isinstance(package.get("contentPlan"), dict) else {}
    coverage = content_goal_coverage(package)
    coverage_counts = coverage.get("counts") if isinstance(coverage.get("counts"), dict) else {}
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}
    site_info = plan.get("siteInfo") if isinstance(plan.get("siteInfo"), dict) else {}
    return {
        "pages": int(coverage_counts.get("pages", len(plan.get("pages", [])) if isinstance(plan.get("pages"), list) else 0)),
        "products": int(coverage_counts.get("products", len(plan.get("products", [])) if isinstance(plan.get("products"), list) else 0)),
        "posts": int(coverage_counts.get("posts", len(plan.get("posts", [])) if isinstance(plan.get("posts"), list) else 0)),
        "forms": int(coverage_counts.get("forms", len(plan.get("forms", [])) if isinstance(plan.get("forms"), list) else 0)),
        "media": int(coverage_counts.get("media", len(plan.get("media", [])) if isinstance(plan.get("media"), list) else 0)),
        "navigationItems": int(coverage_counts.get("navigationItems", len(navigation.get("items", [])) if isinstance(navigation.get("items"), list) else 0)),
        "siteInfoFields": int(coverage_counts.get("siteInfoFields", len(site_info))),
    }


def site_name(package: dict[str, Any]) -> str:
    site = package.get("siteProposal")
    if isinstance(site, dict) and isinstance(site.get("siteName"), str):
        return site["siteName"]
    return "confirmed-source-site"


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    package = load_json(Path(args.package), "package")
    confirmation = load_json(Path(args.confirmation), "confirmation")
    review_packet_path = confirmation.get("sourceReviewPacket") if isinstance(confirmation, dict) else ""
    review_packet = (
        load_review_packet_json(Path(review_packet_path), "review packet")
        if isinstance(review_packet_path, str) and review_packet_path.strip()
        else None
    )
    package_errors = validate_package(package, require_complete=True, require_publication_ready=True)
    if package_errors:
        raise SystemExit("ERROR: invalid package:\n- " + "\n- ".join(package_errors))
    confirmation_errors = validate_confirmation_with_review_packet(confirmation, package, review_packet)
    if confirmation_errors:
        raise SystemExit("ERROR: invalid confirmation:\n- " + "\n- ".join(confirmation_errors))

    counts = content_counts(package)
    coverage = content_goal_coverage(package)
    target_mode = args.target_mode
    site_target = args.site_key if target_mode == "existing_site" else "pending_new_site"
    plan = {
        "kind": "allincms_confirmed_site_execution_plan",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "sourcePackage": args.package,
        "sourcePackageSha256": confirmation.get("sourcePackageSha256", ""),
        "sourceReviewPacket": review_packet_path,
        "sourceReviewPacketSha256": confirmation.get("sourceReviewPacketSha256", ""),
        "confirmation": args.confirmation,
        "targetMode": target_mode,
        "siteTarget": site_target,
        "siteName": site_name(package),
        "contentCounts": counts,
        "contentGoalCoverage": coverage,
        "contentQualityReview": confirmation.get("contentQualityReview"),
        "contentGoalOverages": confirmation.get("contentGoalOverages", {}),
        "wikiReview": confirmation.get("wikiReview", {}),
        **(
            {"sourceReviewObjectiveCoverage": confirmation["sourceReviewObjectiveCoverage"]}
            if isinstance(confirmation.get("sourceReviewObjectiveCoverage"), dict)
            else {}
        ),
        "confirmationDecisionMatrix": confirmation.get("confirmationDecisionMatrix", []),
        "remoteActionsStillRequireAuthorization": [
            "create_site" if target_mode == "new_site" else "select_existing_site",
            "inspect_setup_pages",
            "pages_site_info_launch",
            "capture_product_schema" if counts["products"] else "skip_products_no_items",
            "capture_post_schema" if counts["posts"] else "skip_posts_no_items",
            "sample_upload_product" if counts["products"] else "skip_product_sample",
            "sample_upload_post" if counts["posts"] else "skip_post_sample",
            "batch_upload_products" if counts["products"] else "skip_product_batch",
            "batch_upload_posts" if counts["posts"] else "skip_post_batch",
            "forms_media_settings",
            "final_frontend_audit",
            "cleanup_probes",
        ],
        "stageOrder": [
            {
                "stage": "create_or_select_site",
                "remoteMutation": target_mode == "new_site",
                "requiredProof": ["site identity", "backend dashboard", "frontend base URL"],
                "authorizationBoundary": "action-specific AllinCMS mutation authorization required for create_site",
            },
            {
                "stage": "setup_inspection",
                "remoteMutation": False,
                "requiredProof": ["site-info", "domains", "themes", "routes", "forms", "tracking"],
            },
            {
                "stage": "pages_site_info_handoff",
                "remoteMutation": False,
                "requiredProof": ["pages-plan", "site-info-plan", "navigation-plan", "current setup-page preflight"],
                "authorizationBoundary": "handoff only; site-info save, page design, publish, enable, and route binding remain separate actions",
            },
            {
                "stage": "pages_site_info_execution",
                "remoteMutation": True,
                "requiredProof": [
                    "site-info save/persistence proof",
                    "page save/publish/enable proof",
                    "route binding proof",
                    "frontend DOM proof for planned pages",
                ],
                "authorizationBoundary": "authorize one page/site-info action at a time; do not treat handoff as execution proof",
            },
            {
                "stage": "schema_capture",
                "remoteMutation": True,
                "requiredProof": ["products save request" if counts["products"] else "products not in scope", "posts save request" if counts["posts"] else "posts not in scope"],
                "authorizationBoundary": "probe create/save/publish actions are separate from source-package confirmation",
            },
            {
                "stage": "schema_verified_manifests",
                "remoteMutation": False,
                "requiredProof": ["validate_manifest.py --require-schema-verified for each in-scope manifest"],
            },
            {
                "stage": "sample_upload_and_publish",
                "remoteMutation": True,
                "requiredProof": ["backend persistence", "frontend detail DOM", "body/media checks"],
            },
            {
                "stage": "batch_upload_publish",
                "remoteMutation": True,
                "requiredProof": ["progress log", "backend rows", "frontend detail audit"],
            },
            {
                "stage": "forms_media_settings",
                "remoteMutation": True,
                "requiredProof": ["form/media/settings proof or explicit deferral"],
            },
            {
                "stage": "launch_acceptance",
                "remoteMutation": False,
                "requiredProof": ["final frontend audit", "cleanup proof", "launch acceptance gate"],
            },
        ],
        "commandTemplates": {
            "createSiteAuthorizationRecord": (
                "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
                "--action create_site --target https://workspace.laicms.com/sites --target-type site "
                "--target-identifier pending-new-site --fields-or-files name,description "
                "--expected-result 'new site card, backend dashboard, and default frontend open' "
                "--verification-plan 'verify site card, backend dashboard, frontend base URL, and module routes' "
                "--cleanup-plan 'no automatic deletion; stop before content upload' "
                "--authorization-source '<paste current user authorization text here>' "
                "--output ~/allincms-projects/allincms-authorization-create-site.json"
            ),
            "sourcePackageValidation": (
                f"python3 skills/allincms-bulk-content-upload/scripts/validate_source_site_package.py "
                f"--require-complete-package --require-publication-ready {args.package}"
            ),
            "confirmationValidation": (
                f"python3 skills/allincms-bulk-content-upload/scripts/validate_source_package_confirmation.py "
                f"{args.confirmation} --package {args.package} --review-packet {review_packet_path}"
            ),
        },
        "blockedUntil": [
            "fresh AllinCMS browser auth and site/create-site preflight evidence",
            "action-specific authorization record for each remote mutation",
            "current-site products/posts/page/form schema capture before JSON replay or batch upload",
        ],
        "adversarialChecks": [
            "Do not treat package confirmation as remote mutation authorization.",
            "Do not upload package draft manifests until they are converted to schema-verified current-site manifests.",
            "Do not create another site if the user selected existing_site mode.",
            "Do not batch upload content before pages/site-info handoff and execution evidence have passed.",
            "Do not mark launch complete until launch acceptance inputs are current and pass.",
            "Carry contentQualityReview warnings into every downstream handoff; review-ready packages can still have non-blocking risks.",
            "Carry contentGoalOverages into every downstream handoff; user-confirmed expanded scope must stay visible after confirmation.",
        ],
    }
    return plan


def validate_plan(plan: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if plan.get("kind") != "allincms_confirmed_site_execution_plan":
        issues.append("kind must be allincms_confirmed_site_execution_plan")
    for key in ("localOnly", "preparedOnly"):
        if plan.get(key) is not True:
            issues.append(f"{key} must be true")
    if plan.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if plan.get("isUserAuthorization") is not False:
        issues.append("isUserAuthorization must be false")
    if plan.get("targetMode") not in {"new_site", "existing_site"}:
        issues.append("targetMode must be new_site or existing_site")
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = plan.get(key)
        if not isinstance(value, str) or len(value) != SHA256_HEX_LEN or any(char not in "0123456789abcdef" for char in value):
            issues.append(f"{key} must be a lowercase sha256 hex digest")
    coverage = plan.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        issues.append("contentGoalCoverage must be an object")
    elif coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    counts = plan.get("contentCounts")
    coverage_counts = coverage.get("counts") if isinstance(coverage, dict) and isinstance(coverage.get("counts"), dict) else {}
    if not isinstance(counts, dict):
        issues.append("contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "forms", "media", "navigationItems", "siteInfoFields"):
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
                continue
            expected = coverage_counts.get(key)
            if isinstance(expected, int) and expected >= 0 and value != expected:
                issues.append(f"contentCounts.{key} must match contentGoalCoverage.counts.{key}")
    quality = plan.get("contentQualityReview")
    if not isinstance(quality, dict):
        issues.append("contentQualityReview must be an object")
    else:
        warnings = quality.get("warnings")
        if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
            issues.append("contentQualityReview.warnings must be an array of strings")
            warnings = []
        if quality.get("reviewRequired") is not bool(warnings):
            issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")
    overages = plan.get("contentGoalOverages")
    validate_content_goal_overages(overages, issues)
    if isinstance(quality, dict) and isinstance(overages, dict):
        warnings = [
            item
            for item in quality.get("warnings", [])
            if isinstance(item, str) and item.startswith("exceeds_declared_content_goal:")
        ]
        if warnings and overages.get("present") is not True:
            issues.append("contentGoalOverages.present must be true when contentQualityReview has overage warnings")
    if plan.get("sourceReviewObjectiveCoverage") is not None:
        validate_source_review_objective_coverage(plan.get("sourceReviewObjectiveCoverage"), issues)
        issues.extend(
            source_review_objective_coverage_binding_issues(
                plan.get("sourceReviewObjectiveCoverage"),
                source_package=plan.get("sourcePackage"),
                review_packet=plan.get("sourceReviewPacket"),
            )
        )
    wiki_review = plan.get("wikiReview")
    if not isinstance(wiki_review, dict):
        issues.append("wikiReview must be an object")
    else:
        for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
            if not isinstance(wiki_review.get(key), str) or not wiki_review[key].strip():
                issues.append(f"wikiReview.{key} is required")
    matrix = plan.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix must be a non-empty array")
    else:
        for index, row in enumerate(matrix):
            if not isinstance(row, dict):
                issues.append(f"confirmationDecisionMatrix[{index}] must be an object")
                continue
            if row.get("decision") not in {"accept", "defer"}:
                issues.append(f"confirmationDecisionMatrix[{index}].decision must be accept or defer")
            if row.get("blocksRemoteMutation") is not False:
                issues.append(f"confirmationDecisionMatrix[{index}].blocksRemoteMutation must be false")
    commands = plan.get("commandTemplates")
    if not isinstance(commands, dict):
        issues.append("commandTemplates must be an object")
    else:
        create_cmd = commands.get("createSiteAuthorizationRecord", "")
        if plan.get("targetMode") == "new_site" and "<paste current user authorization text here>" not in create_cmd:
            issues.append("createSiteAuthorizationRecord must retain authorization-source placeholder")
    stage_order = plan.get("stageOrder")
    if not isinstance(stage_order, list) or not stage_order:
        issues.append("stageOrder must be non-empty")
    else:
        stages = [item.get("stage") for item in stage_order if isinstance(item, dict)]
        required = [
            "create_or_select_site",
            "setup_inspection",
            "pages_site_info_handoff",
            "pages_site_info_execution",
            "schema_capture",
            "schema_verified_manifests",
            "sample_upload_and_publish",
            "batch_upload_publish",
            "forms_media_settings",
            "launch_acceptance",
        ]
        missing = [stage for stage in required if stage not in stages]
        if missing:
            issues.append("stageOrder missing required stages: " + ", ".join(missing))
        for before, after in zip(required, required[1:]):
            if before in stages and after in stages and stages.index(before) > stages.index(after):
                issues.append(f"stageOrder must place {before} before {after}")
    if not isinstance(plan.get("blockedUntil"), list) or not plan["blockedUntil"]:
        issues.append("blockedUntil must be non-empty")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a confirmed AllinCMS site execution plan.")
    parser.add_argument("--package", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--target-mode", choices=["new_site", "existing_site"], default="new_site")
    parser.add_argument("--site-key", default="", help="Required only for existing_site mode")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.target_mode == "existing_site" and not args.site_key:
        raise SystemExit("ERROR: --site-key is required for existing_site mode")
    plan = build_plan(args)
    issues = validate_plan(plan)
    if issues:
        raise SystemExit("ERROR: invalid execution plan:\n- " + "\n- ".join(issues))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote confirmed site execution plan: {output}")
    print(f"targetMode={plan['targetMode']} preparedOnly=true remoteMutationsPerformed=false")
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
