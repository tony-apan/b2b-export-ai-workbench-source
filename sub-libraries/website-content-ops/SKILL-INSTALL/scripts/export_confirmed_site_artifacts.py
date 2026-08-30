#!/usr/bin/env python3
"""Export runtime artifacts from a confirmed AllinCMS source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from build_confirmed_site_execution_plan import content_counts as confirmed_content_counts
from build_confirmed_site_execution_plan import validate_plan
from content_goal_coverage_utils import (
    confirmation_decision_matrix_issues,
    matching_content_goal_overages,
    matching_confirmation_decision_matrix,
    matching_source_identity,
    matching_source_review_objective_coverage,
    source_identity_issues,
    source_review_objective_coverage_binding_issues,
    source_review_objective_coverage_from_artifact,
    source_review_objective_coverage_issues,
)
from validate_manifest import validate_manifest
from validate_source_package_confirmation import (
    load_json,
    validate_confirmation_with_review_packet,
    validate_content_goal_overages,
    validate_content_quality_review,
    validate_wiki_review,
)
from validate_source_package_review_packet import load_json as load_review_packet_json
from validate_source_site_package import content_goal_coverage, validate_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def site_key_or_placeholder(args: argparse.Namespace, plan: dict[str, Any]) -> str:
    return args.site_key.strip() or str(plan.get("siteTarget") or "{siteKey-after-creation}")


def frontend_base(args: argparse.Namespace, site_key: str) -> str:
    if args.frontend_base_url.strip():
        return args.frontend_base_url.strip().rstrip("/")
    if site_key.startswith("{"):
        return "https://{siteKey}.web.allincms.com"
    return f"https://{site_key}.web.allincms.com"


def content_plan(package: dict[str, Any]) -> dict[str, Any]:
    plan = package.get("contentPlan")
    return plan if isinstance(plan, dict) else {}


def content_quality_review(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
    review_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    quality = confirmation.get("contentQualityReview")
    issues: list[str] = []
    validate_content_quality_review(quality, issues)
    if issues:
        raise SystemExit("ERROR: invalid confirmation contentQualityReview:\n- " + "\n- ".join(issues))
    if execution_plan.get("contentQualityReview") != quality:
        raise SystemExit("ERROR: execution plan contentQualityReview must match confirmation")
    if isinstance(review_packet, dict) and review_packet.get("contentQualityReview") != quality:
        raise SystemExit("ERROR: review packet contentQualityReview must match confirmation")
    return quality


def content_goal_overages(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
    review_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    entries: list[tuple[str, dict[str, Any] | None]] = [
        ("confirmation", confirmation),
        ("execution plan", execution_plan),
    ]
    if isinstance(review_packet, dict):
        entries.append(("review packet", review_packet))
    overages, issues = matching_content_goal_overages(entries, require_when_present=True)
    if issues:
        raise SystemExit("ERROR: invalid contentGoalOverages:\n- " + "\n- ".join(issues))
    return overages or {}


def wiki_review(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
    review_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    review = confirmation.get("wikiReview")
    issues: list[str] = []
    validate_wiki_review(review, issues)
    if issues:
        raise SystemExit("ERROR: invalid confirmation wikiReview:\n- " + "\n- ".join(issues))
    if execution_plan.get("wikiReview") != review:
        raise SystemExit("ERROR: execution plan wikiReview must match confirmation")
    if isinstance(review_packet, dict) and review_packet.get("wikiReview") != review:
        raise SystemExit("ERROR: review packet wikiReview must match confirmation")
    return review


def confirmation_decision_matrix(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
    review_packet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    matrix, issues = matching_confirmation_decision_matrix(
        [
            ("confirmation", confirmation),
            ("execution plan", execution_plan),
        ],
        require_when_present=True,
    )
    if isinstance(review_packet, dict):
        packet_matrix = review_packet.get("confirmationDecisionMatrix")
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
    if issues:
        raise SystemExit("ERROR: invalid confirmationDecisionMatrix:\n- " + "\n- ".join(issues))
    return matrix or []


def source_review_objective_coverage(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, Any] | None:
    if (
        source_review_objective_coverage_from_artifact(confirmation) is None
        and source_review_objective_coverage_from_artifact(execution_plan) is None
    ):
        return None
    # The matcher enforces symmetry: once either artifact carries coverage, the
    # other must too (silent-drop drift) and both must agree. require_when_present
    # also catches the impossible "neither carries but one was expected" case.
    coverage, issues = matching_source_review_objective_coverage(
        [
            ("confirmation", confirmation),
            ("execution plan", execution_plan),
        ],
        require_when_present=True,
    )
    if issues:
        raise SystemExit("ERROR: invalid sourceReviewObjectiveCoverage:\n- " + "\n- ".join(issues))
    return coverage


def content_counts(
    package: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, int]:
    expected = confirmed_content_counts(package)
    counts = execution_plan.get("contentCounts")
    issues: list[str] = []
    if not isinstance(counts, dict):
        issues.append("executionPlan.contentCounts must be an object")
        counts = {}
    for key in ("pages", "products", "posts", "forms", "media", "navigationItems", "siteInfoFields"):
        value = counts.get(key)
        if not isinstance(value, int) or value < 0:
            issues.append(f"executionPlan.contentCounts.{key} must be a non-negative integer")
    if counts and counts != expected:
        issues.append("executionPlan.contentCounts must match the confirmed source package scope")
    if issues:
        raise SystemExit("ERROR: invalid contentCounts:\n- " + "\n- ".join(issues))
    return {key: int(counts[key]) for key in expected}


def package_manifest(package: dict[str, Any], content_type: str, site_key: str, frontend: str) -> dict[str, Any]:
    manifests = package.get("manifests")
    if not isinstance(manifests, dict) or not isinstance(manifests.get(content_type), dict):
        raise SystemExit(f"ERROR: package missing manifests.{content_type}")
    manifest = dict(manifests[content_type])
    manifest["siteKey"] = site_key
    manifest["frontendBaseUrl"] = frontend
    manifest["schemaVerified"] = False
    manifest["fieldMapping"] = {}
    manifest["payloadTemplate"] = {}
    return manifest


def source_identity(
    confirmation: dict[str, Any],
    execution_plan: dict[str, Any],
) -> dict[str, str]:
    identity, issues = matching_source_identity(
        [
            ("confirmation", confirmation),
            ("execution plan", execution_plan),
        ],
        require_when_present=True,
    )
    if issues:
        raise SystemExit("ERROR: invalid source identity hashes:\n- " + "\n- ".join(issues))
    return identity or {}


def static_plan(package: dict[str, Any], artifact_type: str, data: Any) -> dict[str, Any]:
    return {
        "kind": f"allincms_confirmed_{artifact_type}_plan",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePackage": package.get("sourceWiki"),
        "items": data if isinstance(data, list) else data if isinstance(data, dict) else [],
        "schemaVerified": False,
        "warning": "This is source-confirmed planning only; capture current AllinCMS request schema before remote mutation.",
    }


def build_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    package = load_json(Path(args.package), "package")
    confirmation = load_json(Path(args.confirmation), "confirmation")
    review_packet_path = confirmation.get("sourceReviewPacket") if isinstance(confirmation, dict) else ""
    review_packet = (
        load_review_packet_json(Path(review_packet_path), "review packet")
        if isinstance(review_packet_path, str) and review_packet_path.strip()
        else None
    )
    execution_plan = load_json(Path(args.execution_plan), "execution plan")
    package_errors = validate_package(package, require_complete=True)
    if package_errors:
        raise SystemExit("ERROR: invalid package:\n- " + "\n- ".join(package_errors))
    confirmation_errors = validate_confirmation_with_review_packet(confirmation, package, review_packet)
    if confirmation_errors:
        raise SystemExit("ERROR: invalid confirmation:\n- " + "\n- ".join(confirmation_errors))
    plan_errors = validate_plan(execution_plan)
    if plan_errors:
        raise SystemExit("ERROR: invalid execution plan:\n- " + "\n- ".join(plan_errors))
    coverage = content_goal_coverage(package)
    quality_review = content_quality_review(confirmation, execution_plan, review_packet)
    overages = content_goal_overages(confirmation, execution_plan, review_packet)
    wiki_review_info = wiki_review(confirmation, execution_plan, review_packet)
    decision_matrix = confirmation_decision_matrix(confirmation, execution_plan, review_packet)
    review_objective_coverage = source_review_objective_coverage(confirmation, execution_plan)
    counts = content_counts(package, execution_plan)
    identity = source_identity(confirmation, execution_plan)

    output_dir = Path(args.output_dir)
    site_key = site_key_or_placeholder(args, execution_plan)
    frontend = frontend_base(args, site_key)
    plan = content_plan(package)

    products_manifest = package_manifest(package, "products", site_key, frontend)
    posts_manifest = package_manifest(package, "posts", site_key, frontend)
    products_manifest.update(identity)
    posts_manifest.update(identity)
    manifest_errors = {
        "products": validate_manifest(products_manifest, require_schema_verified=False),
        "posts": validate_manifest(posts_manifest, require_schema_verified=False),
    }
    if manifest_errors["products"] or manifest_errors["posts"]:
        raise SystemExit(
            "ERROR: exported draft manifests failed generic validation:\n"
            + "\n".join(f"{key}: {errors}" for key, errors in manifest_errors.items() if errors)
        )

    artifacts = {
        "productsManifest": output_dir / "products-draft-manifest.json",
        "postsManifest": output_dir / "posts-draft-manifest.json",
        "pagesPlan": output_dir / "pages-plan.json",
        "siteInfoPlan": output_dir / "site-info-plan.json",
        "formsPlan": output_dir / "forms-plan.json",
        "contactFormPolicyPlan": output_dir / "contact-form-policy-plan.json",
        "mediaPlan": output_dir / "media-plan.json",
        "mediaPolicyPlan": output_dir / "media-policy-plan.json",
        "navigationPlan": output_dir / "navigation-plan.json",
        "taxonomyPlan": output_dir / "taxonomy-plan.json",
        "readiness": output_dir / "artifact-readiness.json",
    }
    write_json(artifacts["productsManifest"], products_manifest)
    write_json(artifacts["postsManifest"], posts_manifest)
    write_json(artifacts["pagesPlan"], static_plan(package, "pages", plan.get("pages", [])))
    write_json(artifacts["siteInfoPlan"], static_plan(package, "site_info", {"siteProposal": package.get("siteProposal"), "siteInfo": plan.get("siteInfo", {})}))
    write_json(artifacts["formsPlan"], static_plan(package, "forms", plan.get("forms", [])))
    write_json(artifacts["contactFormPolicyPlan"], static_plan(package, "contact_form_policy", plan.get("contactFormPolicy", {})))
    write_json(artifacts["mediaPlan"], static_plan(package, "media", plan.get("media", [])))
    write_json(artifacts["mediaPolicyPlan"], static_plan(package, "media_policy", plan.get("mediaPolicy", {})))
    write_json(artifacts["navigationPlan"], static_plan(package, "navigation", plan.get("navigation", {})))
    write_json(artifacts["taxonomyPlan"], static_plan(package, "taxonomy", plan.get("taxonomyPlan", {})))

    readiness = {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "sourcePackage": args.package,
        "sourceReviewPacket": review_packet_path,
        "sourcePackageSha256": identity["sourcePackageSha256"],
        "sourceReviewPacketSha256": identity["sourceReviewPacketSha256"],
        "confirmation": args.confirmation,
        "executionPlan": args.execution_plan,
        "siteKey": site_key,
        "frontendBaseUrl": frontend,
        "contentGoalCoverage": coverage,
        "contentCounts": counts,
        "contentQualityReview": quality_review,
        "contentGoalOverages": overages,
        "wikiReview": wiki_review_info,
        **(
            {"sourceReviewObjectiveCoverage": review_objective_coverage}
            if review_objective_coverage is not None
            else {}
        ),
        "confirmationDecisionMatrix": decision_matrix,
        "artifacts": {key: str(path) for key, path in artifacts.items() if key != "readiness"},
        "draftManifestStatus": {
            "products": {
                "schemaVerified": products_manifest.get("schemaVerified"),
                "itemCount": len(products_manifest.get("items", [])),
                "uploadBlockedUntil": "current-site products save request capture and sample verification",
            },
            "posts": {
                "schemaVerified": posts_manifest.get("schemaVerified"),
                "itemCount": len(posts_manifest.get("items", [])),
                "uploadBlockedUntil": "current-site posts save request capture and sample verification",
            },
        },
        "nextActions": [
            "Run make_manifest_upload_readiness.py on exported posts/products manifests; blocked is expected before schema capture.",
            "After site creation or selection, capture products/posts schemas separately.",
            "Fill schemaVerified manifests from captured fieldMapping/payloadTemplate before sample upload.",
            "Use pages/forms/media/site-info plans only after their current AllinCMS request schemas are captured or UI path is verified.",
            "Use contact-form-policy-plan.json to keep public contact channels, CTA destinations, notification destinations, and submission proof explicit.",
            "Use media-policy-plan.json to decide whether source images, public URLs, or explicit no-image scope must be proven before sample and batch evidence.",
            "Use taxonomy-plan.json to create or map product/post categories and tags only after current-site taxonomy schema capture.",
        ],
        "adversarialChecks": [
            "Do not upload exported draft manifests directly.",
            "Do not treat page/site-info/form/media plans as JSON replay payloads.",
            "Do not copy runtime artifacts containing business copy into the skill package.",
        ],
    }
    write_json(artifacts["readiness"], readiness)
    return readiness


def validate_readiness(readiness: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if readiness.get("kind") != "allincms_confirmed_site_artifact_readiness":
        issues.append("kind must be allincms_confirmed_site_artifact_readiness")
    for key in ("localOnly", "preparedOnly"):
        if readiness.get(key) is not True:
            issues.append(f"{key} must be true")
    if readiness.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    coverage = readiness.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        issues.append("contentGoalCoverage must be an object")
    elif coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    counts = readiness.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "navigationItems", "siteInfoFields"):
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
    validate_content_quality_review(readiness.get("contentQualityReview"), issues)
    validate_content_goal_overages(readiness.get("contentGoalOverages"), issues)
    validate_wiki_review(readiness.get("wikiReview"), issues)
    if readiness.get("sourceReviewObjectiveCoverage") is not None:
        issues.extend(source_review_objective_coverage_issues(readiness.get("sourceReviewObjectiveCoverage")))
        issues.extend(
            source_review_objective_coverage_binding_issues(
                readiness.get("sourceReviewObjectiveCoverage"),
                source_package=readiness.get("sourcePackage"),
                review_packet=readiness.get("sourceReviewPacket"),
            )
        )
    issues.extend(confirmation_decision_matrix_issues(readiness.get("confirmationDecisionMatrix")))
    identity = (
        {key: readiness.get(key) for key in ("sourcePackageSha256", "sourceReviewPacketSha256")}
        if any(key in readiness for key in ("sourcePackageSha256", "sourceReviewPacketSha256"))
        else None
    )
    issues.extend(source_identity_issues(identity))
    artifacts = readiness.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        issues.append("artifacts must be a non-empty object")
    else:
        for label, path in artifacts.items():
            if not isinstance(path, str) or not path:
                issues.append(f"artifacts.{label} must be a path string")
            elif not Path(path).exists():
                issues.append(f"artifacts.{label} does not exist: {path}")
    status = readiness.get("draftManifestStatus")
    if not isinstance(status, dict):
        issues.append("draftManifestStatus must be an object")
    else:
        for key in ("products", "posts"):
            item = status.get(key)
            if not isinstance(item, dict):
                issues.append(f"draftManifestStatus.{key} must be an object")
                continue
            if item.get("schemaVerified") is not False:
                issues.append(f"draftManifestStatus.{key}.schemaVerified must be false at export stage")
            if not item.get("uploadBlockedUntil"):
                issues.append(f"draftManifestStatus.{key}.uploadBlockedUntil is required")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Export confirmed AllinCMS source package runtime artifacts.")
    parser.add_argument("--package", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--execution-plan", required=True)
    parser.add_argument("--site-key", default="", help="Optional existing or newly created site key")
    parser.add_argument("--frontend-base-url", default="", help="Optional frontend base URL")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    readiness = build_artifacts(args)
    issues = validate_readiness(readiness)
    if issues:
        print("Confirmed artifact readiness validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Wrote confirmed site artifacts under: {args.output_dir}")
    print("draftManifestSchemaVerified=false uploadBlockedUntil=schema_capture")
    if args.json:
        print(json.dumps(readiness, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
