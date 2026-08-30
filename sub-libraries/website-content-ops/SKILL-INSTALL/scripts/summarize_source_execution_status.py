#!/usr/bin/env python3
"""Summarize source-package-to-AllinCMS execution status from local artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from content_goal_coverage_utils import (
    matching_coverage,
    matching_confirmation_decision_matrix,
    matching_content_goal_overages,
    matching_created_site_submitted_values,
    matching_source_identity,
    matching_source_review_objective_coverage,
)


STAGE_ORDER = (
    "source_package",
    "review_packet",
    "confirmation",
    "execution_plan",
    "artifact_export",
    "create_site_handoff",
    "created_site_binding",
    "pages_site_info_handoff",
    "pages_site_info_execution",
    "taxonomy_execution_handoff",
    "taxonomy_execution",
    "schema_capture_handoff",
    "schema_manifests",
    "sample_upload",
    "batch_upload",
    "forms_media_settings",
    "launch_acceptance",
)
CONTENT_TYPES = ("products", "posts")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: str, label: str) -> tuple[Any | None, str]:
    if not path:
        return None, ""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"{label} not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid {label}: {exc}"


def stage(status: str, evidence: str = "", blockers: list[str] | None = None, next_action: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "evidence": evidence,
        "blockers": blockers or [],
        "nextAction": next_action,
    }


def path_status(path: str) -> str:
    return path if path else ""


def path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def same_path(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except OSError:
        return False


def non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def expected_counts_from_coverage(coverage: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(coverage, dict):
        return {}
    counts = coverage.get("counts")
    if not isinstance(counts, dict):
        return {}
    expected: dict[str, int] = {}
    for key in ("pages", "products", "posts"):
        value = non_negative_int(counts.get(key))
        if value is not None:
            expected[key] = value
    return expected


def target_mode_from_package_or_plan(package: Any, plan: Any) -> str:
    for source in (package, plan):
        if not isinstance(source, dict):
            continue
        for key in ("targetMode", "target_mode"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        execution = source.get("execution")
        if isinstance(execution, dict):
            for key in ("targetMode", "target_mode"):
                value = execution.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().lower()
    return ""


def source_status_requires_created_site_submitted_values(
    package: Any,
    plan: Any,
    created_site_binding: Any,
) -> bool:
    mode = target_mode_from_package_or_plan(package, plan)
    if mode in {"new_site", "create_site", "created_site", "from_scratch"}:
        return True
    if mode in {"existing_site", "selected_site"}:
        return False
    if not isinstance(created_site_binding, dict):
        return False
    return (
        created_site_binding.get("siteBindingMode") == "created_site"
        or created_site_binding.get("siteCreationStatus") == "created_verified"
    )


def content_quality_review_from_sources(*sources: Any) -> dict[str, Any]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        quality = source.get("contentQualityReview")
        if isinstance(quality, dict) and quality:
            return quality
    return {}


def matching_content_quality_review(*sources: Any) -> tuple[dict[str, Any], list[str]]:
    qualities: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        quality = source.get("contentQualityReview")
        if isinstance(quality, dict) and quality:
            qualities.append(quality)
    if not qualities:
        return {}, []
    issues = content_quality_issues(qualities[0])
    for quality in qualities[1:]:
        if quality != qualities[0]:
            issues.append("contentQualityReview mismatch between source-context artifacts")
            break
    return qualities[0], issues


def matching_wiki_review(*sources: Any) -> tuple[dict[str, Any], list[str]]:
    reviews: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        review = source.get("wikiReview")
        if isinstance(review, dict) and review:
            reviews.append(review)
    if not reviews:
        return {}, []
    issues = wiki_review_issues(reviews[0])
    for review in reviews[1:]:
        if review != reviews[0]:
            issues.append("wikiReview mismatch between source-context artifacts")
            break
    return reviews[0], issues


def content_quality_issues(quality: dict[str, Any]) -> list[str]:
    if not quality:
        return []
    issues: list[str] = []
    if not isinstance(quality.get("readyShape"), bool):
        issues.append("contentQualityReview.readyShape must be boolean")
    warnings = quality.get("warnings")
    if not isinstance(warnings, list) or not all(isinstance(item, str) and item.strip() for item in warnings):
        issues.append("contentQualityReview.warnings must be an array of strings")
        warnings = []
    if quality.get("reviewRequired") is not bool(warnings):
        issues.append("contentQualityReview.reviewRequired must equal bool(warnings)")
    return issues


def wiki_review_issues(review: dict[str, Any]) -> list[str]:
    if not review:
        return []
    issues: list[str] = []
    for key in ("sourceWiki", "sourceWikiMarkdown", "sourceWikiMarkdownIndex"):
        value = review.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"wikiReview.{key} is required")
    index = review.get("sourceWikiMarkdownIndex")
    if isinstance(index, str) and index.strip():
        index_path = Path(index).expanduser()
        if not index_path.exists():
            issues.append("wikiReview.sourceWikiMarkdownIndex must point to an existing Markdown file")
        elif index_path.suffix.lower() != ".md":
            issues.append("wikiReview.sourceWikiMarkdownIndex must be a Markdown .md file")
        else:
            try:
                content = index_path.read_text(encoding="utf-8")
            except OSError as exc:
                issues.append(f"wikiReview.sourceWikiMarkdownIndex is not readable: {exc}")
            else:
                if len(content.strip()) < 20 or "#" not in content:
                    issues.append("wikiReview.sourceWikiMarkdownIndex must be a readable Markdown wiki index")
    return issues


def package_stage(package: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="build and validate source-site package")
    if not isinstance(package, dict):
        return stage("blocked", blockers=["source package missing"], next_action="build_source_site_package.py")
    if package.get("kind") != "allincms_source_site_package":
        return stage("blocked", path, ["source package kind mismatch"], "validate_source_site_package.py")
    if package.get("remoteMutationsPerformed") is not False:
        return stage("blocked", path, ["source package must be local-only/no remote mutation"], "rebuild source package")
    return stage("passed", path)


def confirmation_stage(confirmation: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="make_source_package_confirmation.py")
    if not isinstance(confirmation, dict):
        return stage("blocked", blockers=["confirmation missing"], next_action="ask user to confirm source package")
    blockers: list[str] = []
    if confirmation.get("kind") != "allincms_source_site_package_confirmation":
        blockers.append("confirmation kind mismatch")
    if confirmation.get("isRemoteMutationAuthorization") is not False:
        blockers.append("confirmation must not be remote mutation authorization")
    if confirmation.get("remoteMutationsPerformed") is not False:
        blockers.append("confirmation must not perform remote mutations")
    if not isinstance(confirmation.get("sourceReviewPacket"), str) or not confirmation["sourceReviewPacket"].strip():
        blockers.append("confirmation must reference sourceReviewPacket")
    if blockers:
        return stage("blocked", path, blockers, "validate_source_package_confirmation.py")
    return stage("passed", path)


def review_packet_stage(review_packet: Any, path: str, error: str, package_path: str = "") -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="make_source_package_review_packet.py")
    if not isinstance(review_packet, dict):
        return stage("blocked", blockers=["review packet missing"], next_action="make_source_package_review_packet.py")
    blockers: list[str] = []
    if review_packet.get("kind") != "allincms_source_package_review_packet":
        blockers.append("review packet kind mismatch")
    if review_packet.get("localOnly") is not True:
        blockers.append("review packet must be localOnly")
    if review_packet.get("isRemoteMutationAuthorization") is not False:
        blockers.append("review packet must not be remote mutation authorization")
    if review_packet.get("remoteMutationsPerformed") is not False:
        blockers.append("review packet must not perform remote mutations")
    if package_path and not same_path(str(review_packet.get("sourcePackage", "")), package_path):
        blockers.append("review packet sourcePackage must match source package path")
    if blockers:
        return stage("blocked", path, blockers, "validate_source_package_review_packet.py")
    return stage("passed", path)


def execution_plan_stage(plan: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="build_confirmed_site_execution_plan.py")
    if not isinstance(plan, dict):
        return stage("blocked", blockers=["execution plan missing"], next_action="build confirmed-site execution plan")
    blockers: list[str] = []
    if plan.get("kind") != "allincms_confirmed_site_execution_plan":
        blockers.append("execution plan kind mismatch")
    if plan.get("preparedOnly") is not True:
        blockers.append("execution plan must remain preparedOnly")
    if plan.get("isUserAuthorization") is not False:
        blockers.append("execution plan must not be user authorization")
    if blockers:
        return stage("blocked", path, blockers, "rebuild execution plan")
    return stage("passed", path)


def artifact_stage(readiness: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="export_confirmed_site_artifacts.py")
    if not isinstance(readiness, dict):
        return stage("blocked", blockers=["artifact readiness missing"], next_action="export confirmed artifacts")
    blockers: list[str] = []
    if readiness.get("kind") != "allincms_confirmed_site_artifact_readiness":
        blockers.append("artifact readiness kind mismatch")
    if readiness.get("preparedOnly") is not True:
        blockers.append("artifact readiness must be preparedOnly")
    status = readiness.get("draftManifestStatus")
    if not isinstance(status, dict):
        blockers.append("draftManifestStatus missing")
    elif not any(isinstance(status.get(key), dict) and status[key].get("itemCount", 0) > 0 for key in ("products", "posts")):
        blockers.append("no products/posts draft manifest items exported")
    if blockers:
        return stage("blocked", path, blockers, "rerun export_confirmed_site_artifacts.py")
    return stage("passed", path)


def expected_content_types_from_artifacts(artifacts: Any) -> set[str]:
    expected: set[str] = set()
    if not isinstance(artifacts, dict):
        return expected
    status = artifacts.get("draftManifestStatus")
    if not isinstance(status, dict):
        return expected
    for content_type in CONTENT_TYPES:
        value = status.get(content_type)
        if isinstance(value, dict) and isinstance(value.get("itemCount"), int) and value["itemCount"] > 0:
            expected.add(content_type)
    return expected


def content_type_coverage_status(required: set[str], covered: set[str], label: str) -> list[str]:
    if not required:
        return []
    missing = sorted(required - covered)
    return [f"{label} missing required content types: {', '.join(missing)}"] if missing else []


def create_site_handoff_stage(handoff: Any, path: str, error: str, plan: Any, binding: Any) -> dict[str, Any]:
    target_mode = plan.get("targetMode") if isinstance(plan, dict) else ""
    if target_mode == "existing_site":
        return stage("passed", "existing-site-mode")
    if isinstance(binding, dict):
        return stage("passed", "created-site-binding-present")
    if error:
        return stage("blocked", blockers=[error], next_action="build_confirmed_create_site_handoff.py")
    if not isinstance(handoff, dict):
        return stage(
            "blocked",
            blockers=["create-site handoff missing"],
            next_action="refresh /sites create preflight, then run build_confirmed_create_site_handoff.py or prepare_confirmed_site_execution.py --create-preflight",
        )
    blockers: list[str] = []
    if handoff.get("kind") != "allincms_confirmed_create_site_handoff":
        blockers.append("create-site handoff kind mismatch")
    for key in ("localOnly", "preparedOnly", "authorizationRequired"):
        if handoff.get(key) is not True:
            blockers.append(f"create-site handoff {key} must be true")
    for key in ("isUserAuthorization", "remoteMutationsPerformed"):
        if handoff.get(key) is not False:
            blockers.append(f"create-site handoff {key} must be false")
    if handoff.get("action") != "create_site":
        blockers.append("create-site handoff action must be create_site")
    if handoff.get("target") != "https://workspace.laicms.com/sites":
        blockers.append("create-site handoff target must be https://workspace.laicms.com/sites")
    if handoff.get("authorizationRecordCommandHasPlaceholder") is not True:
        blockers.append("create-site handoff authorization command must retain the user-authorization placeholder")
    site = handoff.get("siteProposal")
    if not isinstance(site, dict) or not str(site.get("siteName", "")).strip() or not str(site.get("siteDescription", "")).strip():
        blockers.append("create-site handoff must include siteProposal.siteName and siteDescription")
    forbidden = handoff.get("forbiddenActions")
    if not isinstance(forbidden, list) or "uploading products/posts/media" not in forbidden:
        blockers.append("create-site handoff must explicitly forbid bundled content/media upload")
    if not str(handoff.get("stopAfter", "")).strip():
        blockers.append("create-site handoff must include stopAfter")
    if blockers:
        return stage("blocked", path, blockers, "rebuild create-site handoff from current preflight and confirmed package")
    return stage("passed", path)


def pages_site_info_handoff_stage(handoff: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="prepare_pages_site_info_execution.py")
    if not isinstance(handoff, dict):
        return stage(
            "blocked",
            blockers=["pages/site-info browser handoff missing"],
            next_action="after created or selected site setup inspection, run prepare_pages_site_info_execution.py",
        )
    blockers: list[str] = []
    if handoff.get("kind") != "allincms_pages_site_info_browser_handoff":
        blockers.append("pages/site-info handoff kind mismatch")
    if handoff.get("preparedOnly") is not True:
        blockers.append("pages/site-info handoff must remain preparedOnly")
    if handoff.get("remoteMutationsPerformed") is not False:
        blockers.append("pages/site-info handoff must be local-only/no remote mutation")
    if handoff.get("isUserAuthorization") is not False:
        blockers.append("pages/site-info handoff must not be user authorization")
    site_info = handoff.get("siteInfo")
    if not isinstance(site_info, dict) or site_info.get("browserStepsExecutable") is not False:
        blockers.append("siteInfo handoff must be non-executable until authorization/gate")
    pages = handoff.get("pages")
    if not isinstance(pages, list) or not pages:
        blockers.append("pages handoff must contain at least one page")
    else:
        for index, item in enumerate(pages):
            if not isinstance(item, dict):
                blockers.append(f"pages[{index}] must be an object")
                continue
            if item.get("browserStepsExecutable") is not False:
                blockers.append(f"pages[{index}] must be non-executable until authorization/gate")
            actions = item.get("actions")
            if not isinstance(actions, list) or not actions:
                blockers.append(f"pages[{index}].actions must be non-empty")
    if blockers:
        return stage("blocked", path, blockers, "rerun prepare_pages_site_info_execution.py from current preflight")
    return stage("passed", path)


def pages_site_info_execution_stage(
    evidence: Any,
    validation: Any,
    evidence_path: str,
    validation_path: str,
    error: str,
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="validate_pages_site_info_execution_evidence.py")
    if isinstance(validation, dict):
        if validation.get("valid") is True and validation.get("launchPrerequisiteSatisfied") is True:
            expected_pages = expected_counts.get("pages", 0)
            if expected_pages > 0:
                page_count = non_negative_int(validation.get("pageCount"))
                if page_count is None:
                    return stage(
                        "blocked",
                        validation_path,
                        ["pages/site-info validation must expose pageCount for confirmed page coverage"],
                        "rerun validate_pages_site_info_execution_evidence.py with current page count",
                    )
                if page_count < expected_pages:
                    return stage(
                        "blocked",
                        validation_path,
                        [f"pages/site-info pageCount {page_count} is lower than confirmed plan count {expected_pages}"],
                        "finish planned pages/site-info execution before schema capture",
                    )
            return stage("passed", validation_path)
        return stage(
            "blocked",
            validation_path,
            [str(item) for item in validation.get("issues", [])] or ["pages/site-info validation not valid"],
            "fix pages/site-info execution evidence",
        )
    if isinstance(evidence, dict):
        return stage(
            "blocked",
            evidence_path,
            ["pages/site-info execution evidence present but validation missing"],
            "run validate_pages_site_info_execution_evidence.py",
        )
    return stage(
        "blocked",
        blockers=["pages/site-info execution evidence missing"],
        next_action="execute one authorized page/site-info action at a time, then validate pages/site-info execution evidence",
    )


def taxonomy_plan_path_from_artifacts(artifacts: Any) -> str:
    if not isinstance(artifacts, dict):
        return ""
    artifact_paths = artifacts.get("artifacts")
    if not isinstance(artifact_paths, dict):
        return ""
    value = artifact_paths.get("taxonomyPlan")
    return value if isinstance(value, str) else ""


def taxonomy_terms_required_from_plan(plan: Any) -> bool:
    if not isinstance(plan, dict):
        return False
    items = plan.get("items")
    if not isinstance(items, dict):
        return False
    count_keys = (
        "productCategoryCount",
        "productTagCount",
        "postCategoryCount",
        "postTagCount",
    )
    for key in count_keys:
        value = items.get(key)
        if isinstance(value, int) and value > 0:
            return True
    list_keys = ("productCategories", "productTags", "postCategories", "postTags")
    for key in list_keys:
        value = items.get(key)
        if isinstance(value, list) and value:
            return True
    return False


def taxonomy_handoff_stage(handoff: Any, path: str, error: str, taxonomy_required: bool) -> dict[str, Any]:
    if not taxonomy_required:
        return stage("passed", "taxonomy-not-required")
    if error:
        return stage("blocked", blockers=[error], next_action="prepare_taxonomy_execution.py")
    if not isinstance(handoff, dict):
        return stage(
            "blocked",
            blockers=["taxonomy execution handoff missing"],
            next_action="run prepare_taxonomy_execution.py from taxonomy-plan.json and current products/posts preflight",
        )
    blockers: list[str] = []
    if handoff.get("kind") != "allincms_taxonomy_execution_handoff":
        blockers.append("taxonomy handoff kind mismatch")
    if handoff.get("preparedOnly") is not True:
        blockers.append("taxonomy handoff must remain preparedOnly")
    if handoff.get("remoteMutationsPerformed") is not False:
        blockers.append("taxonomy handoff must be local-only/no remote mutation")
    if handoff.get("isUserAuthorization") is not False:
        blockers.append("taxonomy handoff must not be user authorization")
    if handoff.get("browserStepsExecutable") is not False:
        blockers.append("taxonomy handoff must not be executable before authorization/gate")
    preflight_issues = handoff.get("preflightIssues")
    if isinstance(preflight_issues, list) and preflight_issues:
        blockers.extend(f"taxonomy preflight: {issue}" for issue in preflight_issues)
    actions = handoff.get("actions")
    if not isinstance(actions, list) or not actions:
        blockers.append("taxonomy handoff must contain create/map actions when taxonomy terms are required")
    if blockers:
        return stage("blocked", path, blockers, "refresh products/posts taxonomy preflight and rerun prepare_taxonomy_execution.py")
    return stage("passed", path)


def taxonomy_execution_stage(evidence: Any, validation: Any, evidence_path: str, validation_path: str, error: str, taxonomy_required: bool) -> dict[str, Any]:
    if not taxonomy_required:
        return stage("passed", "taxonomy-not-required")
    if error:
        return stage("blocked", blockers=[error], next_action="validate_taxonomy_execution_evidence.py")
    if isinstance(validation, dict):
        if validation.get("valid") is True and validation.get("taxonomyPrerequisiteSatisfied") is True:
            return stage("passed", validation_path)
        return stage(
            "blocked",
            validation_path,
            [str(item) for item in validation.get("issues", [])] or ["taxonomy validation not valid"],
            "fix taxonomy create/map evidence before schema capture or batch upload",
        )
    if isinstance(evidence, dict):
        return stage(
            "blocked",
            evidence_path,
            ["taxonomy execution evidence present but validation missing"],
            "run validate_taxonomy_execution_evidence.py",
        )
    return stage(
        "blocked",
        blockers=["taxonomy execution evidence missing"],
        next_action="execute/map taxonomy terms one action at a time, then validate taxonomy execution evidence",
    )


def created_site_binding_stage(binding: Any, path: str, error: str, artifacts: Any, target_mode: str = "") -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="bind_created_site_to_artifacts.py")
    if isinstance(binding, dict):
        blockers: list[str] = []
        if binding.get("kind") != "allincms_created_site_artifact_binding":
            blockers.append("created-site binding kind mismatch")
        if binding.get("remoteMutationsPerformed") is not False:
            blockers.append("created-site binding must be local-only/no remote mutation")
        if binding.get("schemaVerified") is not False:
            blockers.append("schemaVerified must remain false after created-site binding")
        bound = binding.get("boundArtifacts")
        if not isinstance(bound, dict) or not bound.get("productsManifest") or not bound.get("postsManifest"):
            blockers.append("bound products/posts manifests are required")
        if blockers:
            return stage("blocked", path, blockers, "rerun bind_created_site_to_artifacts.py")
        return stage("passed", path)
    if target_mode in {"existing_site", "selected_site"}:
        return stage(
            "blocked",
            blockers=["selected existing-site artifact binding missing"],
            next_action="refresh existing site read-only evidence, then run bind_created_site_to_artifacts.py",
        )
    if isinstance(artifacts, dict):
        site_key = artifacts.get("siteKey")
        if isinstance(site_key, str) and site_key and not site_key.startswith("{") and site_key != "pending_new_site":
            return stage("passed", path or "artifact-readiness-site-bound")
    return stage(
        "blocked",
        blockers=["created-site artifact binding missing"],
        next_action="after created-site evidence, run bind_created_site_to_artifacts.py",
    )


def schema_capture_handoff_stage(handoff: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="build_schema_capture_handoff.py")
    if not isinstance(handoff, dict):
        return stage(
            "blocked",
            blockers=["schema capture handoff missing"],
            next_action="build_schema_capture_handoff.py after created-site artifact binding",
        )
    blockers: list[str] = []
    if handoff.get("kind") != "allincms_schema_capture_handoff":
        blockers.append("schema capture handoff kind mismatch")
    if handoff.get("remoteMutationsPerformed") is not False:
        blockers.append("schema capture handoff must be local-only/no remote mutation")
    if handoff.get("isUserAuthorization") is not False:
        blockers.append("schema capture handoff must not be user authorization")
    stages = handoff.get("stages")
    if not isinstance(stages, list) or not stages:
        blockers.append("schema capture handoff must contain stages")
    else:
        ready = any(isinstance(item, dict) and item.get("status") == "ready_for_create_probe_authorization" for item in stages)
        blocked_preflight = [
            str(item.get("contentType"))
            for item in stages
            if isinstance(item, dict) and item.get("status") == "needs_readonly_content_preflight"
        ]
        if blocked_preflight:
            blockers.append("content types need read-only preflight before create-probe gate: " + ", ".join(blocked_preflight))
        if not ready and not blocked_preflight:
            blockers.append("no content type is ready for schema capture")
    if blockers:
        return stage("blocked", path, blockers, "refresh content-type read-only preflight, then rebuild schema capture handoff")
    return stage("passed", path)


def upload_readiness_content_types(readiness: Any) -> set[str]:
    covered: set[str] = set()
    if not isinstance(readiness, dict):
        return covered
    manifests = readiness.get("manifests")
    if not isinstance(manifests, list):
        return covered
    for item in manifests:
        if isinstance(item, dict) and item.get("status") == "ready_for_sample_upload":
            content_type = item.get("contentType")
            if content_type in CONTENT_TYPES:
                covered.add(str(content_type))
    return covered


def upload_readiness_stage(readiness_items: list[tuple[Any | None, str, str]], expected_content_types: set[str]) -> dict[str, Any]:
    errors = [error for _data, _path, error in readiness_items if error]
    if errors:
        return stage("blocked", blockers=errors, next_action="make_manifest_upload_readiness.py")
    valid_items = [(data, path) for data, path, _error in readiness_items if isinstance(data, dict)]
    if not valid_items:
        return stage("blocked", blockers=["upload readiness missing"], next_action="apply save captures to manifests, then run make_manifest_upload_readiness.py")
    blockers: list[str] = []
    evidence_paths: list[str] = []
    covered: set[str] = set()
    for readiness, path in valid_items:
        evidence_paths.append(path)
        if readiness.get("overallStatus") != "ready_for_sample_upload":
            blockers.append(f"{path}: upload readiness overallStatus is not ready_for_sample_upload")
            for item in readiness.get("manifests", []) if isinstance(readiness.get("manifests"), list) else []:
                if isinstance(item, dict) and item.get("blockers"):
                    blockers.append(f"{item.get('contentType')}: {', '.join(str(x) for x in item.get('blockers', []))}")
        covered.update(upload_readiness_content_types(readiness))
    if blockers:
        return stage("blocked", ", ".join(evidence_paths), blockers, "capture current-site save request and run apply_save_capture_to_manifest.py")
    coverage_blockers = content_type_coverage_status(
        expected_content_types,
        covered,
        "upload readiness",
    )
    if coverage_blockers:
        return stage("blocked", ", ".join(evidence_paths), coverage_blockers, "prepare schema-verified manifests for every exported products/posts content type")
    return stage("passed", ", ".join(evidence_paths))


def sample_content_types(samples: list[tuple[Any | None, str, str]]) -> set[str]:
    covered: set[str] = set()
    for data, _path, error in samples:
        if error or not isinstance(data, dict):
            continue
        content_type = data.get("contentType")
        if content_type in CONTENT_TYPES:
            covered.add(str(content_type))
    return covered


def sample_stage(samples: list[tuple[Any | None, str, str]], expected_content_types: set[str]) -> dict[str, Any]:
    if not samples:
        return stage("blocked", blockers=["sample evidence missing"], next_action="build_manifest_sample_upload_runbook.py and validate one sample")
    blockers: list[str] = []
    passed: list[str] = []
    for data, path, error in samples:
        if error:
            blockers.append(error)
            continue
        if not isinstance(data, dict):
            blockers.append(f"sample evidence invalid or missing: {path}")
            continue
        if data.get("kind") != "allincms_manifest_sample_upload_evidence":
            blockers.append(f"sample evidence kind mismatch: {path}")
            continue
        required = ("schemaGatePass", "backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified", "stopConditionMet")
        missing = [key for key in required if data.get(key) is not True]
        if data.get("saveStatus") != "ok":
            missing.append("saveStatus=ok")
        if data.get("publishStatus") != "ok":
            missing.append("publishStatus=ok")
        if data.get("coverOrMediaVerified") is not True and not data.get("coverOrMediaNote"):
            missing.append("cover/media proof or note")
        if missing:
            blockers.append(f"{path}: missing {', '.join(missing)}")
        else:
            passed.append(path)
    blockers.extend(content_type_coverage_status(expected_content_types, sample_content_types(samples), "sample evidence"))
    if blockers:
        return stage("blocked", ",".join(passed), blockers, "repair sample upload evidence before batch")
    return stage("passed", ",".join(passed))


def batch_validation_content_types(batch_validations: list[tuple[Any | None, str, str]]) -> set[str]:
    covered: set[str] = set()
    for data, _path, error in batch_validations:
        if error or not isinstance(data, dict):
            continue
        if data.get("valid") is not True:
            continue
        content_type = data.get("contentType")
        if content_type in CONTENT_TYPES:
            covered.add(str(content_type))
    return covered


def batch_validation_count(data: dict[str, Any]) -> int | None:
    count = non_negative_int(data.get("manifestItemCount"))
    if count is not None:
        return count
    return non_negative_int(data.get("progressCount"))


def batch_count_coverage_status(
    expected_counts: dict[str, int],
    batch_validations: list[tuple[Any | None, str, str]],
) -> list[str]:
    actual: dict[str, int] = {}
    for data, _path, error in batch_validations:
        if error or not isinstance(data, dict) or data.get("valid") is not True:
            continue
        content_type = data.get("contentType")
        if content_type not in CONTENT_TYPES:
            continue
        count = batch_validation_count(data)
        if count is None:
            continue
        actual[str(content_type)] = max(actual.get(str(content_type), 0), count)

    blockers: list[str] = []
    for content_type in CONTENT_TYPES:
        expected = expected_counts.get(content_type, 0)
        if expected <= 0:
            continue
        if content_type not in actual:
            blockers.append(f"batch validation for {content_type} must expose manifestItemCount or progressCount")
            continue
        if actual[content_type] < expected:
            blockers.append(f"batch validation {content_type} count {actual[content_type]} is lower than confirmed plan count {expected}")
    return blockers


def batch_stage(
    batch_validations: list[tuple[Any | None, str, str]],
    batch_evidence: Any,
    evidence_path: str,
    evidence_error: str,
    expected_content_types: set[str],
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    blockers: list[str] = []
    passed: list[str] = []
    if batch_validations:
        for data, path, error in batch_validations:
            if error:
                blockers.append(error)
                continue
            if not isinstance(data, dict):
                blockers.append(f"batch validation invalid or missing: {path}")
                continue
            if data.get("valid") is True:
                passed.append(path)
            else:
                blockers.extend(str(x) for x in data.get("issues", []) if str(x)) or blockers.append(f"{path}: batch validation not valid")
        blockers.extend(
            content_type_coverage_status(
                expected_content_types,
                batch_validation_content_types(batch_validations),
                "batch validation",
            )
        )
        blockers.extend(batch_count_coverage_status(expected_counts, batch_validations))
        if blockers:
            return stage("blocked", ",".join(passed), blockers, "fix batch evidence for every exported products/posts content type")
        return stage("passed", ",".join(passed))

    error = evidence_error
    if error:
        return stage("blocked", blockers=[error], next_action="validate_batch_upload_publish_evidence.py")
    if isinstance(batch_evidence, dict):
        return stage("blocked", evidence_path, ["batch evidence present but validation missing"], "run validate_batch_upload_publish_evidence.py")
    return stage("blocked", blockers=["batch evidence missing"], next_action="build_batch_upload_publish_runbook.py and run gated batch upload")


def forms_media_settings_stage(evidence: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="capture or explicitly defer forms/media/settings evidence")
    if not isinstance(evidence, dict):
        return stage(
            "blocked",
            blockers=["forms/media/settings evidence missing"],
            next_action="verify or explicitly defer site-info, forms, media, domains, and tracking before launch acceptance",
        )
    if evidence.get("kind") != "allincms_forms_media_settings_evidence":
        return stage("blocked", path, ["forms/media/settings evidence kind mismatch"], "rebuild forms/media/settings evidence")

    deferral_modules: set[str] = set()
    deferrals = evidence.get("deferrals")
    if isinstance(deferrals, list):
        for item in deferrals:
            if isinstance(item, dict) and isinstance(item.get("module"), str):
                deferral_modules.add(item["module"])

    status = evidence.get("status")
    if status == "explicitly_out_of_scope":
        if deferral_modules:
            return stage("passed", path)
        return stage(
            "blocked",
            path,
            ["explicitly_out_of_scope forms/media/settings evidence must include deferrals"],
            "record concrete forms/media/settings deferrals",
        )

    required = {
        "siteInfoVerified": "site-info",
        "formsVerified": "forms",
        "mediaVerified": "media",
        "domainsRecorded": "domains",
        "trackingRecorded": "tracking",
    }
    blockers: list[str] = []
    for key, module in required.items():
        if evidence.get(key) is True:
            continue
        if module in deferral_modules:
            continue
        blockers.append(f"{key} missing and no {module} deferral recorded")
    if blockers:
        return stage("blocked", path, blockers, "complete or explicitly defer forms/media/settings evidence")
    return stage("passed", path)


def launch_stage(launch_validation: Any, path: str, error: str) -> dict[str, Any]:
    if error:
        return stage("blocked", blockers=[error], next_action="validate_launch_acceptance.py")
    if not isinstance(launch_validation, dict):
        return stage("blocked", blockers=["launch acceptance validation missing"], next_action="run launch acceptance after batch/forms/final audit/cleanup")
    if launch_validation.get("valid") is True and launch_validation.get("complete") is True:
        return stage("passed", path)
    blockers: list[str] = []
    if launch_validation.get("valid") is not True:
        blockers.append("launch acceptance valid is not true")
    if launch_validation.get("complete") is not True:
        blockers.append("launch acceptance complete is not true")
    for item in launch_validation.get("acceptance", []) if isinstance(launch_validation.get("acceptance"), list) else []:
        if isinstance(item, dict) and item.get("status") == "blocked":
            blockers.extend(str(x) for x in item.get("blockers", []))
    return stage("blocked", path, blockers or ["launch acceptance incomplete"], "finish launch acceptance blockers")


def first_blocked(stages: dict[str, dict[str, Any]]) -> str:
    for key in STAGE_ORDER:
        if stages[key]["status"] != "passed":
            return key
    return ""


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    package, package_error = load_json(args.package, "source package")
    review_packet, review_packet_error = load_json(args.review_packet, "review packet")
    confirmation, confirmation_error = load_json(args.confirmation, "confirmation")
    plan, plan_error = load_json(args.execution_plan, "execution plan")
    artifacts, artifacts_error = load_json(args.artifact_readiness, "artifact readiness")
    create_site_handoff_path = getattr(args, "create_site_handoff", "")
    create_site_handoff, create_site_handoff_error = load_json(create_site_handoff_path, "create-site handoff")
    created_site_binding, binding_error = load_json(args.created_site_binding, "created-site artifact binding")
    pages_site_info_path = getattr(args, "pages_site_info_handoff", "")
    pages_site_info_handoff, pages_site_info_error = load_json(pages_site_info_path, "pages/site-info browser handoff")
    pages_site_info_evidence_path = getattr(args, "pages_site_info_evidence", "")
    pages_site_info_validation_path = getattr(args, "pages_site_info_validation", "")
    pages_site_info_evidence, pages_site_info_evidence_error = load_json(
        pages_site_info_evidence_path,
        "pages/site-info execution evidence",
    )
    pages_site_info_validation, pages_site_info_validation_error = load_json(
        pages_site_info_validation_path,
        "pages/site-info execution validation",
    )
    taxonomy_plan_path = taxonomy_plan_path_from_artifacts(artifacts)
    taxonomy_plan, taxonomy_plan_error = load_json(taxonomy_plan_path, "taxonomy plan")
    taxonomy_required = taxonomy_terms_required_from_plan(taxonomy_plan)
    taxonomy_handoff_path = getattr(args, "taxonomy_handoff", "")
    taxonomy_evidence_path = getattr(args, "taxonomy_evidence", "")
    taxonomy_validation_path = getattr(args, "taxonomy_validation", "")
    taxonomy_handoff, taxonomy_handoff_error = load_json(taxonomy_handoff_path, "taxonomy execution handoff")
    taxonomy_evidence, taxonomy_evidence_error = load_json(taxonomy_evidence_path, "taxonomy execution evidence")
    taxonomy_validation, taxonomy_validation_error = load_json(taxonomy_validation_path, "taxonomy execution validation")
    if taxonomy_plan_error and taxonomy_plan_path:
        taxonomy_required = True
    schema_capture_handoff, schema_handoff_error = load_json(args.schema_capture_handoff, "schema capture handoff")
    upload_readiness_items: list[tuple[Any | None, str, str]] = []
    for readiness_path in path_list(args.upload_readiness):
        readiness_data, readiness_error = load_json(readiness_path, "upload readiness")
        upload_readiness_items.append((readiness_data, readiness_path, readiness_error))
    batch_evidence, batch_evidence_error = load_json(args.batch_evidence, "batch evidence")
    batch_validation_items: list[tuple[Any | None, str, str]] = []
    for validation_path in path_list(args.batch_validation):
        validation_data, validation_error = load_json(validation_path, "batch validation")
        batch_validation_items.append((validation_data, validation_path, validation_error))
    forms_media_settings_path = getattr(args, "forms_media_settings", "")
    forms_media_settings, forms_media_settings_error = load_json(forms_media_settings_path, "forms/media/settings evidence")
    launch_validation, launch_error = load_json(args.launch_acceptance, "launch acceptance")
    sample_items: list[tuple[Any | None, str, str]] = []
    for sample_path in args.sample_evidence:
        sample_data, sample_error = load_json(sample_path, "sample evidence")
        sample_items.append((sample_data, sample_path, sample_error))
    expected_content_types = expected_content_types_from_artifacts(artifacts)
    source_coverage, source_coverage_issues = matching_coverage(
        [
            ("source package", package if isinstance(package, dict) else None),
            ("review packet", review_packet if isinstance(review_packet, dict) else None),
            ("confirmation", confirmation if isinstance(confirmation, dict) else None),
            ("execution plan", plan if isinstance(plan, dict) else None),
            ("artifact readiness", artifacts if isinstance(artifacts, dict) else None),
            ("created-site binding", created_site_binding if isinstance(created_site_binding, dict) else None),
        ],
        require_when_present=False,
    )
    expected_content_counts = expected_counts_from_coverage(source_coverage)
    content_quality, content_quality_validation_issues = matching_content_quality_review(
        package,
        confirmation,
        plan,
        review_packet,
        artifacts,
        created_site_binding,
        schema_capture_handoff,
    )
    content_goal_overages, content_goal_overage_issues = matching_content_goal_overages(
        [
            ("source package", package if isinstance(package, dict) else None),
            ("review packet", review_packet if isinstance(review_packet, dict) else None),
            ("confirmation", confirmation if isinstance(confirmation, dict) else None),
            ("execution plan", plan if isinstance(plan, dict) else None),
            ("artifact readiness", artifacts if isinstance(artifacts, dict) else None),
            ("created-site binding", created_site_binding if isinstance(created_site_binding, dict) else None),
            ("schema-capture handoff", schema_capture_handoff if isinstance(schema_capture_handoff, dict) else None),
            ("forms/media/settings evidence", forms_media_settings if isinstance(forms_media_settings, dict) else None),
        ],
        require_when_present=False,
        quality=content_quality,
    )
    wiki_review, wiki_review_validation_issues = matching_wiki_review(
        confirmation,
        plan,
        review_packet,
        artifacts,
        created_site_binding,
        schema_capture_handoff,
        forms_media_settings,
    )
    if wiki_review and isinstance(forms_media_settings, dict) and forms_media_settings.get("kind") == "allincms_forms_media_settings_evidence":
        if not isinstance(forms_media_settings.get("wikiReview"), dict):
            wiki_review_validation_issues.append("wikiReview missing from forms/media/settings evidence")
    decision_matrix, decision_matrix_issues = matching_confirmation_decision_matrix(
        [
            ("confirmation", confirmation),
            ("execution plan", plan),
            ("artifact readiness", artifacts if isinstance(artifacts, dict) else None),
            ("created-site binding", created_site_binding if isinstance(created_site_binding, dict) else None),
            ("schema-capture handoff", schema_capture_handoff if isinstance(schema_capture_handoff, dict) else None),
            ("forms/media/settings evidence", forms_media_settings if isinstance(forms_media_settings, dict) else None),
        ],
        require_when_present=False,
    )
    if decision_matrix and isinstance(forms_media_settings, dict) and forms_media_settings.get("kind") == "allincms_forms_media_settings_evidence":
        if not isinstance(forms_media_settings.get("confirmationDecisionMatrix"), list):
            decision_matrix_issues.append("confirmationDecisionMatrix missing from forms/media/settings evidence")
    source_identity, source_identity_issues = matching_source_identity(
        [
            ("confirmation", confirmation if isinstance(confirmation, dict) else None),
            ("execution plan", plan if isinstance(plan, dict) else None),
            ("artifact readiness", artifacts if isinstance(artifacts, dict) else None),
            ("created-site binding", created_site_binding if isinstance(created_site_binding, dict) else None),
            ("schema-capture handoff", schema_capture_handoff if isinstance(schema_capture_handoff, dict) else None),
        ],
        require_when_present=False,
    )
    review_objective_coverage, review_objective_coverage_issues = matching_source_review_objective_coverage(
        [
            ("confirmation", confirmation if isinstance(confirmation, dict) else None),
            ("execution plan", plan if isinstance(plan, dict) else None),
            ("artifact readiness", artifacts if isinstance(artifacts, dict) else None),
        ],
        require_when_present=False,
    )
    created_site_submitted_values, created_site_submitted_value_issues = matching_created_site_submitted_values(
        [
            ("created-site binding", created_site_binding if isinstance(created_site_binding, dict) else None),
            ("forms/media/settings", forms_media_settings if isinstance(forms_media_settings, dict) else None),
            ("launch acceptance", launch_validation if isinstance(launch_validation, dict) else None),
        ],
        require_when_present=source_status_requires_created_site_submitted_values(
            package,
            plan,
            created_site_binding,
        ),
    )
    target_mode = target_mode_from_package_or_plan(package, plan)

    stages = {
        "source_package": package_stage(package, args.package, package_error),
        "review_packet": review_packet_stage(review_packet, args.review_packet, review_packet_error, args.package),
        "confirmation": confirmation_stage(confirmation, args.confirmation, confirmation_error),
        "execution_plan": execution_plan_stage(plan, args.execution_plan, plan_error),
        "artifact_export": artifact_stage(artifacts, args.artifact_readiness, artifacts_error),
        "create_site_handoff": create_site_handoff_stage(
            create_site_handoff,
            create_site_handoff_path,
            create_site_handoff_error,
            plan,
            created_site_binding,
        ),
        "created_site_binding": created_site_binding_stage(
            created_site_binding,
            args.created_site_binding,
            binding_error,
            artifacts,
            target_mode,
        ),
        "pages_site_info_handoff": pages_site_info_handoff_stage(
            pages_site_info_handoff,
            pages_site_info_path,
            pages_site_info_error,
        ),
        "pages_site_info_execution": pages_site_info_execution_stage(
            pages_site_info_evidence,
            pages_site_info_validation,
            pages_site_info_evidence_path,
            pages_site_info_validation_path,
            pages_site_info_validation_error or pages_site_info_evidence_error,
            expected_content_counts,
        ),
        "taxonomy_execution_handoff": taxonomy_handoff_stage(
            taxonomy_handoff,
            taxonomy_handoff_path,
            taxonomy_handoff_error,
            taxonomy_required,
        ),
        "taxonomy_execution": taxonomy_execution_stage(
            taxonomy_evidence,
            taxonomy_validation,
            taxonomy_evidence_path,
            taxonomy_validation_path,
            taxonomy_validation_error or taxonomy_evidence_error,
            taxonomy_required,
        ),
        "schema_capture_handoff": schema_capture_handoff_stage(
            schema_capture_handoff,
            args.schema_capture_handoff,
            schema_handoff_error,
        ),
        "schema_manifests": upload_readiness_stage(upload_readiness_items, expected_content_types),
        "sample_upload": sample_stage(sample_items, expected_content_types),
        "batch_upload": batch_stage(
            batch_validation_items,
            batch_evidence,
            args.batch_evidence,
            batch_evidence_error,
            expected_content_types,
            expected_content_counts,
        ),
        "forms_media_settings": forms_media_settings_stage(
            forms_media_settings,
            forms_media_settings_path,
            forms_media_settings_error,
        ),
        "launch_acceptance": launch_stage(launch_validation, args.launch_acceptance, launch_error),
    }
    if source_coverage_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            source_coverage_issues,
            "rebuild source package/review/confirmation/artifacts so contentGoalCoverage is complete and consistent",
        )
    if content_quality_validation_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            content_quality_validation_issues,
            "rebuild review/confirmation/execution artifacts so contentQualityReview is valid and consistent",
        )
    if content_goal_overage_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            content_goal_overage_issues,
            "rebuild review/confirmation/execution artifacts so contentGoalOverages is valid and consistent",
        )
    if wiki_review_validation_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            wiki_review_validation_issues,
            "rebuild review/confirmation/execution artifacts so wikiReview is valid and consistent",
        )
    if decision_matrix_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            decision_matrix_issues,
            "rebuild review/confirmation/execution artifacts so confirmationDecisionMatrix is valid and consistent",
        )
    if source_identity_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            source_identity_issues,
            "rebuild source package/review/confirmation/artifacts so source identity hashes are valid and consistent",
        )
    if review_objective_coverage_issues:
        stages["source_package"] = stage(
            "blocked",
            args.package,
            review_objective_coverage_issues,
            "rebuild confirmation/execution plan/artifacts so sourceReviewObjectiveCoverage stays review-complete, live-incomplete, and consistent",
        )
    if created_site_submitted_value_issues:
        stages["created_site_binding"] = stage(
            "blocked",
            args.created_site_binding,
            created_site_submitted_value_issues,
            "rebuild created-site binding and downstream artifacts so submitted site name/description stay consistent",
        )
    blocked = first_blocked(stages)
    passed_count = sum(1 for item in stages.values() if item["status"] == "passed")
    return {
        "kind": "allincms_source_execution_status",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "complete": blocked == "",
        "currentStage": blocked or "complete",
        "passedCount": passed_count,
        "stageCount": len(STAGE_ORDER),
        "stages": stages,
        **({"targetMode": target_mode} if target_mode else {}),
        "requiredContentTypes": sorted(expected_content_types),
        "contentGoalCoverage": source_coverage or {},
        "contentGoalCoverageIssues": source_coverage_issues,
        "contentQualityReview": content_quality,
        "contentQualityReviewIssues": content_quality_validation_issues,
        "contentGoalOverages": content_goal_overages or {},
        "contentGoalOverageIssues": content_goal_overage_issues,
        "wikiReview": wiki_review,
        "wikiReviewIssues": wiki_review_validation_issues,
        **({"sourceReviewObjectiveCoverage": review_objective_coverage} if review_objective_coverage else {}),
        "sourceReviewObjectiveCoverageIssues": review_objective_coverage_issues,
        "confirmationDecisionMatrix": decision_matrix or [],
        "confirmationDecisionMatrixIssues": decision_matrix_issues,
        **(source_identity or {}),
        "sourceIdentityIssues": source_identity_issues,
        **({"createdSiteSubmittedValues": created_site_submitted_values} if created_site_submitted_values else {}),
        "createdSiteSubmittedValuesIssues": created_site_submitted_value_issues,
        "contentTypeCoverage": {
            "uploadReadiness": sorted(
                {
                    content_type
                    for readiness, _path, error in upload_readiness_items
                    if not error
                    for content_type in upload_readiness_content_types(readiness)
                }
            ),
            "sampleEvidence": sorted(sample_content_types(sample_items)),
            "batchValidation": sorted(batch_validation_content_types(batch_validation_items)),
        },
        "contentCountCoverage": expected_content_counts,
        "taxonomyRequired": taxonomy_required,
        "taxonomyPlan": taxonomy_plan_path,
        "nextAction": "complete" if not blocked else stages[blocked]["nextAction"],
        "rule": "This is a local status summary. It does not authorize or perform AllinCMS browser mutations.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize source-package to AllinCMS execution status.")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--create-site-handoff", default="")
    parser.add_argument("--pages-site-info-handoff", default="")
    parser.add_argument("--pages-site-info-evidence", default="")
    parser.add_argument("--pages-site-info-validation", default="")
    parser.add_argument("--created-site-binding", default="")
    parser.add_argument("--taxonomy-handoff", default="")
    parser.add_argument("--taxonomy-evidence", default="")
    parser.add_argument("--taxonomy-validation", default="")
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-blocked", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = summarize(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source execution status: {output}")
    print(f"currentStage={report['currentStage']} complete={str(report['complete']).lower()} passed={report['passedCount']}/{report['stageCount']}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_on_blocked and not report["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
