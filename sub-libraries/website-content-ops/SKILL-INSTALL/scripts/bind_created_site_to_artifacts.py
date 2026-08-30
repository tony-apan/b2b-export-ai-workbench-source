#!/usr/bin/env python3
"""Bind created or selected site identity into confirmed source runtime artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_manifest import validate_manifest
from validate_run_evidence import validate as validate_run_evidence
from validate_source_package_confirmation import validate_content_quality_review, validate_wiki_review
from content_goal_coverage_utils import confirmation_decision_matrix_issues, source_identity_issues


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def site_identity(evidence: dict[str, Any]) -> tuple[str, str, str]:
    errors = validate_run_evidence(evidence)
    if errors:
        raise SystemExit("ERROR: invalid created/selected-site evidence:\n- " + "\n- ".join(errors))
    site_creation = evidence.get("siteCreation") if isinstance(evidence.get("siteCreation"), dict) else {}
    status = site_creation.get("status")
    if status not in {"created_verified", "existing_site_selected"}:
        raise SystemExit(
            "ERROR: site evidence must have siteCreation.status=created_verified or existing_site_selected"
        )
    identity = evidence.get("siteIdentity") if isinstance(evidence.get("siteIdentity"), dict) else {}
    site_key = identity.get("siteKey")
    frontend_base = identity.get("frontendBaseUrl")
    if not isinstance(site_key, str) or not site_key.strip():
        raise SystemExit("ERROR: siteIdentity.siteKey is required")
    if not isinstance(frontend_base, str) or not frontend_base.startswith("https://"):
        raise SystemExit("ERROR: siteIdentity.frontendBaseUrl is required")
    return site_key.strip(), frontend_base.rstrip("/"), str(status)


def confirmed_site_proposal(readiness: dict[str, Any]) -> dict[str, str]:
    package_path = readiness.get("sourcePackage")
    if not isinstance(package_path, str) or not package_path.strip():
        raise SystemExit("ERROR: artifact readiness missing sourcePackage path")
    package = load_json(Path(package_path), "source package")
    proposal = package.get("siteProposal")
    if not isinstance(proposal, dict):
        raise SystemExit("ERROR: source package missing siteProposal")
    expected = {
        "name": proposal.get("siteName"),
        "description": proposal.get("siteDescription"),
    }
    for key, value in expected.items():
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"ERROR: source package siteProposal missing {key}")
        expected[key] = value.strip()
    return expected


def created_site_submitted_values(
    readiness: dict[str, Any],
    evidence: dict[str, Any],
    site_creation_status: str,
) -> dict[str, str]:
    if site_creation_status != "created_verified":
        return {}
    expected = confirmed_site_proposal(readiness)
    site_creation = evidence.get("siteCreation") if isinstance(evidence.get("siteCreation"), dict) else {}
    submitted = site_creation.get("submittedValues")
    if not isinstance(submitted, dict):
        raise SystemExit(
            "ERROR: created-site evidence must include siteCreation.submittedValues for source-package new-site binding"
        )
    actual: dict[str, str] = {}
    for key in ("name", "description"):
        value = submitted.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"ERROR: created-site evidence missing siteCreation.submittedValues.{key}")
        actual[key] = value.strip()
        if actual[key] != expected[key]:
            source_key = "siteName" if key == "name" else "siteDescription"
            raise SystemExit(
                f"ERROR: created-site submittedValues.{key} must match confirmed siteProposal.{source_key}"
            )
    return actual


def bind_manifest(
    manifest: dict[str, Any],
    site_key: str,
    frontend_base: str,
    source_manifest: str,
    *,
    content_goal_coverage: dict[str, Any],
    content_counts: dict[str, int],
    source_identity: dict[str, str],
) -> dict[str, Any]:
    bound = dict(manifest)
    bound["siteKey"] = site_key
    bound["frontendBaseUrl"] = frontend_base
    bound["schemaVerified"] = False
    bound["fieldMapping"] = {}
    bound["payloadTemplate"] = {}
    bound["contentGoalCoverage"] = content_goal_coverage
    bound["contentCounts"] = content_counts
    bound.update(source_identity)
    bound["createdSiteBinding"] = {
        "boundAt": now_iso(),
        "sourceManifest": source_manifest,
        "schemaCaptureStillRequired": True,
    }
    errors = validate_manifest(bound, require_schema_verified=False)
    if errors:
        raise SystemExit(f"ERROR: bound manifest failed validation for {source_manifest}:\n- " + "\n- ".join(errors))
    return bound


def existing_artifacts(readiness: dict[str, Any]) -> dict[str, str]:
    artifacts = readiness.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("ERROR: artifact readiness missing artifacts object")
    required = ("productsManifest", "postsManifest")
    missing = [key for key in required if not isinstance(artifacts.get(key), str) or not artifacts[key]]
    if missing:
        raise SystemExit("ERROR: artifact readiness missing paths: " + ", ".join(missing))
    return {key: str(value) for key, value in artifacts.items() if isinstance(value, str)}


def readiness_content_goal_coverage(readiness: dict[str, Any]) -> dict[str, Any]:
    coverage = readiness.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        raise SystemExit("ERROR: artifact readiness missing contentGoalCoverage")
    if coverage.get("complete") is not True:
        raise SystemExit("ERROR: artifact readiness contentGoalCoverage.complete must be true")
    return coverage


def readiness_content_counts(readiness: dict[str, Any], coverage: dict[str, Any]) -> dict[str, int]:
    coverage_counts = coverage.get("counts")
    if not isinstance(coverage_counts, dict):
        raise SystemExit("ERROR: contentGoalCoverage.counts must be an object")
    counts = readiness.get("contentCounts")
    if not isinstance(counts, dict):
        raise SystemExit("ERROR: artifact readiness missing contentCounts")
    result: dict[str, int] = {}
    for key in ("pages", "products", "posts", "forms", "media", "navigationItems", "siteInfoFields"):
        value = counts.get(key)
        if not isinstance(value, int) or value < 0:
            raise SystemExit(f"ERROR: contentCounts.{key} must be a non-negative integer")
        result[key] = value
    for key in ("pages", "products", "posts", "navigationItems"):
        if result.get(key) != coverage_counts.get(key):
            raise SystemExit(f"ERROR: contentCounts.{key} must match contentGoalCoverage.counts.{key}")
    return result


def readiness_content_quality_review(readiness: dict[str, Any]) -> dict[str, Any]:
    quality = readiness.get("contentQualityReview")
    issues: list[str] = []
    validate_content_quality_review(quality, issues)
    if issues:
        raise SystemExit("ERROR: artifact readiness invalid contentQualityReview:\n- " + "\n- ".join(issues))
    return quality


def readiness_wiki_review(readiness: dict[str, Any]) -> dict[str, Any]:
    review = readiness.get("wikiReview")
    issues: list[str] = []
    validate_wiki_review(review, issues)
    if issues:
        raise SystemExit("ERROR: artifact readiness invalid wikiReview:\n- " + "\n- ".join(issues))
    return review


def readiness_confirmation_decision_matrix(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = readiness.get("confirmationDecisionMatrix")
    issues = confirmation_decision_matrix_issues(matrix if isinstance(matrix, list) else None)
    if issues:
        raise SystemExit("ERROR: artifact readiness invalid confirmationDecisionMatrix:\n- " + "\n- ".join(issues))
    return matrix


def readiness_source_identity(readiness: dict[str, Any]) -> dict[str, str]:
    identity = {key: readiness.get(key) for key in ("sourcePackageSha256", "sourceReviewPacketSha256")}
    issues = source_identity_issues(identity)
    if issues:
        raise SystemExit("ERROR: artifact readiness invalid source identity hashes:\n- " + "\n- ".join(issues))
    return {key: str(identity[key]) for key in ("sourcePackageSha256", "sourceReviewPacketSha256")}


def binding_mode(site_creation_status: str) -> str:
    if site_creation_status == "created_verified":
        return "created_site"
    if site_creation_status == "existing_site_selected":
        return "existing_site"
    raise SystemExit("ERROR: unsupported site creation status")


def build_binding(args: argparse.Namespace) -> dict[str, Any]:
    readiness = load_json(Path(args.artifact_readiness), "artifact readiness")
    evidence = load_json(Path(args.created_site_evidence), "created/selected-site evidence")
    if readiness.get("kind") != "allincms_confirmed_site_artifact_readiness":
        raise SystemExit("ERROR: artifact readiness kind mismatch")
    coverage = readiness_content_goal_coverage(readiness)
    content_counts = readiness_content_counts(readiness, coverage)
    quality_review = readiness_content_quality_review(readiness)
    wiki_review = readiness_wiki_review(readiness)
    decision_matrix = readiness_confirmation_decision_matrix(readiness)
    identity = readiness_source_identity(readiness)
    site_key, frontend_base, site_creation_status = site_identity(evidence)
    mode = binding_mode(site_creation_status)
    submitted_values = created_site_submitted_values(readiness, evidence, site_creation_status)
    artifacts = existing_artifacts(readiness)
    output_dir = Path(args.output_dir)

    products_manifest = load_json(Path(artifacts["productsManifest"]), "products manifest")
    posts_manifest = load_json(Path(artifacts["postsManifest"]), "posts manifest")
    bound_products_path = output_dir / "products-draft-manifest.bound-created-site.json"
    bound_posts_path = output_dir / "posts-draft-manifest.bound-created-site.json"
    bound_products = bind_manifest(
        products_manifest,
        site_key,
        frontend_base,
        artifacts["productsManifest"],
        content_goal_coverage=coverage,
        content_counts=content_counts,
        source_identity=identity,
    )
    bound_posts = bind_manifest(
        posts_manifest,
        site_key,
        frontend_base,
        artifacts["postsManifest"],
        content_goal_coverage=coverage,
        content_counts=content_counts,
        source_identity=identity,
    )
    write_json(bound_products_path, bound_products)
    write_json(bound_posts_path, bound_posts)

    bound_readiness = dict(readiness)
    bound_readiness["kind"] = "allincms_confirmed_site_artifact_readiness"
    bound_readiness["generatedAt"] = now_iso()
    bound_readiness["siteKey"] = site_key
    bound_readiness["frontendBaseUrl"] = frontend_base
    bound_readiness["createdSiteEvidence"] = args.created_site_evidence
    bound_readiness["siteBindingMode"] = mode
    if submitted_values:
        bound_readiness["createdSiteSubmittedValues"] = submitted_values
    bound_readiness["contentGoalCoverage"] = coverage
    bound_readiness["contentCounts"] = content_counts
    bound_readiness["contentQualityReview"] = quality_review
    bound_readiness["wikiReview"] = wiki_review
    bound_readiness["confirmationDecisionMatrix"] = decision_matrix
    bound_readiness.update(identity)
    bound_artifacts = dict(artifacts)
    bound_artifacts["productsManifest"] = str(bound_products_path)
    bound_artifacts["postsManifest"] = str(bound_posts_path)
    bound_readiness["artifacts"] = bound_artifacts
    status = bound_readiness.get("draftManifestStatus")
    if isinstance(status, dict):
        for key in ("products", "posts"):
            if isinstance(status.get(key), dict):
                status[key]["schemaVerified"] = False
                status[key]["siteBound"] = True
                status[key]["siteKey"] = site_key
                status[key]["uploadBlockedUntil"] = f"current-site {key} save request capture and sample verification"
    bound_readiness["createdSiteBinding"] = {
        "boundAt": now_iso(),
        "createdSiteEvidence": args.created_site_evidence,
        "siteBindingMode": mode,
        "siteCreationStatus": site_creation_status,
        "schemaCaptureStillRequired": True,
        "sampleUploadStillRequired": True,
        "remoteMutationsPerformedByThisStep": False,
    }
    if submitted_values:
        bound_readiness["createdSiteBinding"]["submittedValues"] = submitted_values
    bound_readiness["nextActions"] = [
        "Run make_manifest_upload_readiness.py on the bound draft manifests; blocked is expected before schema capture.",
        "Capture products/posts save requests separately on the bound site.",
        "Use apply_save_capture_to_manifest.py to create schema-verified manifests before sample upload.",
    ]
    bound_readiness_path = output_dir / "artifact-readiness.bound-created-site.json"
    write_json(bound_readiness_path, bound_readiness)
    return {
        "kind": "allincms_created_site_artifact_binding",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "artifactReadiness": args.artifact_readiness,
        "createdSiteEvidence": args.created_site_evidence,
        "siteBindingMode": mode,
        "siteCreationStatus": site_creation_status,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base,
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "contentGoalCoverage": coverage,
        "contentCounts": content_counts,
        "contentQualityReview": quality_review,
        "wikiReview": wiki_review,
        "confirmationDecisionMatrix": decision_matrix,
        **identity,
        "boundArtifacts": {
            "productsManifest": str(bound_products_path),
            "postsManifest": str(bound_posts_path),
            "artifactReadiness": str(bound_readiness_path),
        },
        "schemaVerified": False,
        "blockedUntil": [
            "current-site products save request capture",
            "current-site posts save request capture",
            "manifest sample upload and frontend verification",
        ],
        "adversarialChecks": [
            "created_verified proves a new site was created; existing_site_selected proves only a selected existing site was refreshed read-only",
            "existing_site binding must not be used as proof for a from-scratch site-creation objective",
            "schema capture, sample upload, batch upload, and launch acceptance remain required after either binding mode",
        ],
    }


def validate_binding(binding: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if binding.get("kind") != "allincms_created_site_artifact_binding":
        issues.append("kind must be allincms_created_site_artifact_binding")
    for key in ("localOnly", "preparedOnly"):
        if binding.get(key) is not True:
            issues.append(f"{key} must be true")
    if binding.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if binding.get("schemaVerified") is not False:
        issues.append("schemaVerified must remain false after site binding")
    if binding.get("siteBindingMode") not in {"created_site", "existing_site"}:
        issues.append("siteBindingMode must be created_site or existing_site")
    status = binding.get("siteCreationStatus")
    if binding.get("siteBindingMode") == "created_site" and status != "created_verified":
        issues.append("created_site binding must have siteCreationStatus=created_verified")
    if binding.get("siteBindingMode") == "existing_site" and status != "existing_site_selected":
        issues.append("existing_site binding must have siteCreationStatus=existing_site_selected")
    coverage = binding.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        issues.append("contentGoalCoverage must be an object")
    elif coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    counts = binding.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts must be an object")
    else:
        for key in ("pages", "products", "posts", "forms", "media", "navigationItems", "siteInfoFields"):
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
    if isinstance(coverage, dict) and isinstance(coverage.get("counts"), dict) and isinstance(counts, dict):
        for key in ("pages", "products", "posts", "navigationItems"):
            if counts.get(key) != coverage["counts"].get(key):
                issues.append(f"contentCounts.{key} must match contentGoalCoverage.counts.{key}")
    validate_content_quality_review(binding.get("contentQualityReview"), issues)
    validate_wiki_review(binding.get("wikiReview"), issues)
    issues.extend(confirmation_decision_matrix_issues(binding.get("confirmationDecisionMatrix")))
    identity = (
        {key: binding.get(key) for key in ("sourcePackageSha256", "sourceReviewPacketSha256")}
        if any(key in binding for key in ("sourcePackageSha256", "sourceReviewPacketSha256"))
        else None
    )
    issues.extend(source_identity_issues(identity))
    artifacts = binding.get("boundArtifacts")
    if not isinstance(artifacts, dict):
        issues.append("boundArtifacts must be an object")
    else:
        for key in ("productsManifest", "postsManifest", "artifactReadiness"):
            value = artifacts.get(key)
            if not isinstance(value, str) or not Path(value).exists():
                issues.append(f"boundArtifacts.{key} must exist")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind created or selected site identity into confirmed source artifacts.")
    parser.add_argument("--artifact-readiness", required=True)
    parser.add_argument(
        "--created-site-evidence",
        required=True,
        help="Run evidence with siteCreation.status=created_verified or existing_site_selected",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    binding = build_binding(args)
    issues = validate_binding(binding)
    if issues:
        raise SystemExit("ERROR: invalid created/selected-site artifact binding:\n- " + "\n- ".join(issues))
    output = Path(args.output)
    write_json(output, binding)
    if args.json:
        print(json.dumps(binding, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote created/selected-site artifact binding: {output}")
        print("schemaVerified=false schemaCaptureStillRequired=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
