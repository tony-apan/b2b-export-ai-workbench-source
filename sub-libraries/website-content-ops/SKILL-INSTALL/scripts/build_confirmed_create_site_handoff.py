#!/usr/bin/env python3
"""Build a local handoff from confirmed source package to create-site authorization."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_run_evidence import validate as validate_run_evidence
from validate_source_package_confirmation import load_json, validate_confirmation_with_review_packet
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings
from validate_source_package_review_packet import load_json as load_review_packet_json
from validate_source_site_package import content_goal_coverage, validate_package
from make_created_site_evidence_brief import build as build_created_site_evidence_brief
from content_goal_coverage_utils import (
    confirmation_decision_matrix_issues,
    matching_confirmation_decision_matrix,
    matching_content_goal_overages,
)
from build_confirmed_site_execution_plan import content_counts as confirmed_content_counts


AUTH_PLACEHOLDER = "<paste current user authorization text here>"
SHA256_HEX_LEN = 64


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def site_proposal(package: dict[str, Any]) -> dict[str, str]:
    site = package.get("siteProposal") if isinstance(package.get("siteProposal"), dict) else {}
    return {
        "siteName": str(site.get("siteName", "")).strip(),
        "siteDescription": str(site.get("siteDescription", "")).strip(),
        "language": str(site.get("language", "")).strip(),
        "industry": str(site.get("industry", "")).strip(),
    }


def content_counts(package: dict[str, Any]) -> dict[str, int]:
    return confirmed_content_counts(package)


def preflight_existing_keys(preflight: dict[str, Any]) -> list[str]:
    site_creation = preflight.get("siteCreation") if isinstance(preflight.get("siteCreation"), dict) else {}
    keys = site_creation.get("existingSiteKeysBeforeCreate")
    return [item for item in keys if isinstance(item, str)] if isinstance(keys, list) else []


def preflight_empty_site_list_evidence(preflight: dict[str, Any]) -> str:
    site_creation = preflight.get("siteCreation") if isinstance(preflight.get("siteCreation"), dict) else {}
    evidence = site_creation.get("emptySiteListEvidence")
    return evidence.strip() if isinstance(evidence, str) else ""


def validate_inputs(
    package: dict[str, Any],
    review_packet: dict[str, Any],
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
    preflight: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    issues.extend("package: " + issue for issue in validate_package(package, require_complete=True, require_publication_ready=True))
    issues.extend("confirmation: " + issue for issue in validate_confirmation_with_review_packet(confirmation, package, review_packet))
    issues.extend("preflight: " + issue for issue in validate_run_evidence(preflight))
    if execution_plan.get("kind") != "allincms_confirmed_site_execution_plan":
        issues.append("executionPlan.kind must be allincms_confirmed_site_execution_plan")
    if execution_plan.get("targetMode") != "new_site":
        issues.append("executionPlan.targetMode must be new_site for create-site handoff")
    if execution_plan.get("preparedOnly") is not True:
        issues.append("executionPlan.preparedOnly must be true")
    if execution_plan.get("isUserAuthorization") is not False:
        issues.append("executionPlan.isUserAuthorization must be false")
    if execution_plan.get("sourcePackage") and execution_plan["sourcePackage"] != confirmation.get("sourcePackage"):
        issues.append("executionPlan.sourcePackage must match confirmation.sourcePackage")
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        confirmation_value = confirmation.get(key)
        execution_value = execution_plan.get(key)
        if not isinstance(confirmation_value, str) or len(confirmation_value) != SHA256_HEX_LEN:
            issues.append(f"confirmation.{key} must be present")
        if execution_value != confirmation_value:
            issues.append(f"executionPlan.{key} must match confirmation.{key}")
    expected_coverage = content_goal_coverage(package)
    if execution_plan.get("contentGoalCoverage") != expected_coverage:
        issues.append("executionPlan.contentGoalCoverage must match source package coverage")
    confirmation_quality = confirmation.get("contentQualityReview") if isinstance(confirmation, dict) else None
    execution_quality = execution_plan.get("contentQualityReview") if isinstance(execution_plan, dict) else None
    review_quality = review_packet.get("contentQualityReview") if isinstance(review_packet, dict) else None
    if not isinstance(execution_quality, dict) or not execution_quality:
        issues.append("executionPlan.contentQualityReview must be a non-empty object")
    if review_quality is not None and execution_quality != review_quality:
        issues.append("executionPlan.contentQualityReview must match review packet contentQualityReview")
    if confirmation_quality is not None and execution_quality != confirmation_quality:
        issues.append("executionPlan.contentQualityReview must match confirmation contentQualityReview")
    overages, overage_issues = matching_content_goal_overages(
        [
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("execution plan", execution_plan),
        ],
        require_when_present=True,
    )
    issues.extend(overage_issues)
    if isinstance(execution_quality, dict) and isinstance(overages, dict):
        warnings = [
            item
            for item in execution_quality.get("warnings", [])
            if isinstance(item, str) and item.startswith("exceeds_declared_content_goal:")
        ]
        if warnings and overages.get("present") is not True:
            issues.append("contentGoalOverages.present must be true when contentQualityReview has overage warnings")
    execution_wiki = execution_plan.get("wikiReview") if isinstance(execution_plan, dict) else None
    confirmation_wiki = confirmation.get("wikiReview") if isinstance(confirmation, dict) else None
    review_wiki = review_packet.get("wikiReview") if isinstance(review_packet, dict) else None
    if not isinstance(execution_wiki, dict) or not execution_wiki:
        issues.append("executionPlan.wikiReview must be a non-empty object")
    if review_wiki is not None and execution_wiki != review_wiki:
        issues.append("executionPlan.wikiReview must match review packet wikiReview")
    if confirmation_wiki is not None and execution_wiki != confirmation_wiki:
        issues.append("executionPlan.wikiReview must match confirmation wikiReview")
    matrix, matrix_issues = matching_confirmation_decision_matrix(
        [
            ("confirmation", confirmation),
            ("execution plan", execution_plan),
        ],
        require_when_present=True,
    )
    issues.extend(matrix_issues)
    packet_matrix = review_packet.get("confirmationDecisionMatrix") if isinstance(review_packet, dict) else None
    if isinstance(packet_matrix, list) and matrix is not None:
        packet_fields = {
            row.get("field")
            for row in packet_matrix
            if isinstance(row, dict) and isinstance(row.get("field"), str) and row.get("field")
        }
        matrix_fields = {
            row.get("field")
            for row in matrix
            if isinstance(row, dict) and isinstance(row.get("field"), str) and row.get("field")
        }
        if packet_fields and packet_fields != matrix_fields:
            issues.append("confirmationDecisionMatrix fields must match review packet confirmationDecisionMatrix fields")
    return issues


def authorization_record_command(site: dict[str, str], output: str) -> str:
    expected = "new site card, backend dashboard, default frontend open, and site identity recorded"
    verification = "verify site card absence-before/presence-after, backend dashboard, frontend base URL, and module routes"
    cleanup = "no automatic deletion; stop after created-site evidence before content upload"
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
        "--action create_site "
        "--target https://workspace.laicms.com/sites "
        "--target-type site "
        f"--target-identifier '{site['siteName']}' "
        "--fields-or-files name,description "
        f"--expected-result '{expected}' "
        f"--verification-plan '{verification}' "
        f"--cleanup-plan '{cleanup}' "
        f"--authorization-source '{AUTH_PLACEHOLDER}' "
        f"--output {output}"
    )


def build_handoff(args: argparse.Namespace) -> dict[str, Any]:
    package = load_json(Path(args.package), "package")
    review_packet = load_review_packet_json(Path(args.review_packet), "review packet")
    confirmation = load_json(Path(args.confirmation), "confirmation")
    execution_plan = load_json(Path(args.execution_plan), "execution plan")
    preflight = load_json(Path(args.preflight), "preflight")
    issues = validate_inputs(package, review_packet, confirmation, execution_plan, preflight)
    if issues:
        raise SystemExit("ERROR: create-site handoff inputs are invalid:\n- " + "\n- ".join(issues))
    site = site_proposal(package)
    if not site["siteName"] or not site["siteDescription"]:
        raise SystemExit("ERROR: siteProposal.siteName and siteDescription are required")

    auth_command = authorization_record_command(site, args.authorization_output)
    output_path = Path(args.output).expanduser()
    created_site_evidence_brief_path = output_path.with_name("created-site-evidence-brief.json")
    created_site_evidence_output = output_path.with_name("created-site-evidence.json")
    pre_mutation_gate_command = (
        "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
        "--action create_site "
        f"--preflight {args.preflight} "
        f"--authorization {args.authorization_output} "
        f"--expected-target-identifier '{site['siteName']}'"
    )
    existing_keys = preflight_existing_keys(preflight)
    empty_site_list_evidence = preflight_empty_site_list_evidence(preflight)
    handoff = {
        "kind": "allincms_confirmed_create_site_handoff",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "remoteMutationsPerformed": False,
        "sourcePackage": args.package,
        "sourcePackageSha256": execution_plan.get("sourcePackageSha256", ""),
        "sourceReviewPacket": args.review_packet,
        "sourceReviewPacketSha256": execution_plan.get("sourceReviewPacketSha256", ""),
        "confirmation": args.confirmation,
        "executionPlan": args.execution_plan,
        "preflight": args.preflight,
        "authorizationOutput": args.authorization_output,
        "target": "https://workspace.laicms.com/sites",
        "action": "create_site",
        "siteProposal": site,
        "contentCounts": content_counts(package),
        "contentGoalCoverage": content_goal_coverage(package),
        "contentQualityReview": execution_plan.get("contentQualityReview", {}),
        "contentGoalOverages": execution_plan.get("contentGoalOverages", {}),
        "wikiReview": execution_plan.get("wikiReview", {}),
        "confirmationDecisionMatrix": execution_plan.get("confirmationDecisionMatrix", []),
        "existingSiteKeysBeforeCreate": existing_keys,
        "emptySiteListEvidence": empty_site_list_evidence if not existing_keys else "",
        "authorizationRequired": True,
        "suggestedAuthorizationText": (
            f"授权 Codex 在 https://workspace.laicms.com/sites 创建站点，站点名称为 {site['siteName']}，"
            f"站点描述使用已确认 source package 中的描述；本次只提交创建站点并验证新站点后台和前台，"
            "不上传内容、不发布产品/文章、不绑定域名、不修改主题。"
        ),
        "authorizationRecordCommand": auth_command,
        "authorizationRecordCommandHasPlaceholder": AUTH_PLACEHOLDER in auth_command,
        "preMutationGateCommand": pre_mutation_gate_command,
        "createdSiteEvidenceBrief": str(created_site_evidence_brief_path),
        "createdSiteEvidenceOutput": str(created_site_evidence_output),
        "mustRunBeforeBrowserSubmit": [
            "paste current user authorization into authorizationRecordCommand",
            "run make_authorization_record.py --validate-only on authorizationOutput",
            "run preMutationGateCommand and require it to pass",
            "confirm create-site dialog still shows name and description fields",
            "review contentQualityReview warnings before submitting create-site so post-create planning preserves quality-risk context",
            "review contentGoalOverages before submitting create-site so expanded source scope stays visible after creation",
            "confirm no source content upload, publish, theme, route, media, domain, or tracking action is bundled",
        ],
        "browserStepsAfterGate": [
            "open https://workspace.laicms.com/sites",
            "open the create-site dialog",
            f"fill site name: {site['siteName']}",
            "fill site description from the confirmed package",
            "submit create-site once",
            "record created-site evidence with new site key, backend dashboard URL, frontend base URL, and module routes",
            "stop before schema capture or content upload",
        ],
        "forbiddenActions": [
            "uploading products/posts/media",
            "publishing content",
            "creating probes",
            "editing themes/routes/forms/settings",
            "binding domains or adding tracking",
            "claiming launch completion",
        ],
        "stopAfter": "created-site evidence is captured; continue with setup inspection and schema capture in separate gated stages",
    }
    handoff_issues = validate_handoff(handoff)
    if handoff_issues:
        raise SystemExit("ERROR: generated create-site handoff is invalid:\n- " + "\n- ".join(handoff_issues))
    return handoff


def validate_handoff(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_confirmed_create_site_handoff":
        issues.append("kind must be allincms_confirmed_create_site_handoff")
    for key in ("localOnly", "preparedOnly", "authorizationRequired"):
        if data.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("isUserAuthorization", "remoteMutationsPerformed"):
        if data.get(key) is not False:
            issues.append(f"{key} must be false")
    if data.get("action") != "create_site":
        issues.append("action must be create_site")
    if data.get("target") != "https://workspace.laicms.com/sites":
        issues.append("target must be https://workspace.laicms.com/sites")
    for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
        value = data.get(key)
        if not isinstance(value, str) or len(value) != SHA256_HEX_LEN or any(char not in "0123456789abcdef" for char in value):
            issues.append(f"{key} must be a lowercase sha256 hex digest")
    if data.get("authorizationRecordCommandHasPlaceholder") is not True:
        issues.append("authorizationRecordCommand must retain authorization placeholder")
    gate = data.get("preMutationGateCommand")
    site_for_gate = data.get("siteProposal") if isinstance(data.get("siteProposal"), dict) else {}
    site_name_for_gate = str(site_for_gate.get("siteName", "")).strip()
    if not isinstance(gate, str) or "--expected-target-identifier" not in gate:
        issues.append("preMutationGateCommand must include --expected-target-identifier")
    elif site_name_for_gate and site_name_for_gate not in gate:
        issues.append("preMutationGateCommand must bind the confirmed siteProposal.siteName")
    site = data.get("siteProposal")
    if not isinstance(site, dict) or not isinstance(site.get("siteName"), str) or not isinstance(site.get("siteDescription"), str):
        issues.append("siteProposal.siteName and siteDescription are required")
    if not isinstance(data.get("mustRunBeforeBrowserSubmit"), list) or not data["mustRunBeforeBrowserSubmit"]:
        issues.append("mustRunBeforeBrowserSubmit must be non-empty")
    counts = data.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "navigationItems", "siteInfoFields"):
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
    if not isinstance(data.get("forbiddenActions"), list) or "uploading products/posts/media" not in data["forbiddenActions"]:
        issues.append("forbiddenActions must block content/media upload")
    existing_keys = data.get("existingSiteKeysBeforeCreate")
    if not isinstance(existing_keys, list):
        issues.append("existingSiteKeysBeforeCreate must be an array")
        existing_keys = []
    if not existing_keys:
        evidence = data.get("emptySiteListEvidence")
        if not isinstance(evidence, str) or not evidence.strip():
            issues.append("emptySiteListEvidence is required when existingSiteKeysBeforeCreate is empty")
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        issues.append("contentGoalCoverage must be an object")
    elif coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    quality = data.get("contentQualityReview")
    if not isinstance(quality, dict) or not quality:
        issues.append("contentQualityReview must be a non-empty object")
    else:
        warnings = quality.get("warnings")
        if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
            issues.append("contentQualityReview.warnings must be an array of strings")
            warnings = []
        if quality.get("reviewRequired") is not bool(warnings):
            issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")
    overages = data.get("contentGoalOverages")
    validate_content_goal_overages(overages, issues)
    validate_content_goal_overages_for_warnings(overages, quality, issues)
    wiki_review = data.get("wikiReview")
    if not isinstance(wiki_review, dict) or not wiki_review:
        issues.append("wikiReview must be a non-empty object")
    else:
        for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
            if not isinstance(wiki_review.get(key), str) or not wiki_review[key].strip():
                issues.append(f"wikiReview.{key} is required")
    issues.extend(confirmation_decision_matrix_issues(data.get("confirmationDecisionMatrix")))
    return issues


def build_validation_report(data: dict[str, Any], handoff_path: str = "") -> dict[str, Any]:
    issues = validate_handoff(data)
    return {
        "kind": "allincms_confirmed_create_site_handoff_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "handoff": handoff_path,
        "preparedOnly": data.get("preparedOnly"),
        "remoteMutationsPerformed": data.get("remoteMutationsPerformed"),
        "isUserAuthorization": data.get("isUserAuthorization"),
        "action": data.get("action"),
        "target": data.get("target"),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a confirmed source-package create-site handoff.")
    parser.add_argument("--package", required=True)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--execution-plan", required=True)
    parser.add_argument("--preflight", required=True, help="Fresh create-site preflight evidence JSON")
    parser.add_argument("--authorization-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    handoff = build_handoff(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_created_site_evidence_brief(
        argparse.Namespace(
            create_site_handoff=str(output),
            output=handoff["createdSiteEvidenceBrief"],
            created_site_evidence_output=handoff["createdSiteEvidenceOutput"],
            json=False,
        )
    )
    print(f"Wrote confirmed create-site handoff: {output}")
    print("preparedOnly=true isUserAuthorization=false remoteMutationsPerformed=false")
    if args.json:
        print(json.dumps(handoff, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
