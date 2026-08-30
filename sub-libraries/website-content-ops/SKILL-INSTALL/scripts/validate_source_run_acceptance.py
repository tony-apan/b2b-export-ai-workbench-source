#!/usr/bin/env python3
"""Validate source-file-to-site execution acceptance from local status artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from content_goal_coverage_utils import (
    matching_confirmation_decision_matrix,
    matching_content_counts,
    matching_content_goal_overages,
    matching_coverage,
    matching_created_site_submitted_values,
    matching_quality_review,
    matching_source_identity,
    matching_wiki_review,
)
from apply_browser_stage_result import validate_browser_stage_result
from validate_batch_upload_publish_evidence import load_json_any, validate_batch_evidence
from validate_forms_media_settings_evidence import validate_evidence as validate_forms_media_settings_evidence
from make_final_frontend_audit_stage_result import load_reports, summarize_reports, validate_expected_coverage
from validate_manifest import load_manifest
from validate_manifest_sample_upload_evidence import validate_sample_evidence
from validate_probe_cleanup_evidence import validate_cleanup_evidence
from validate_source_wiki import validate_source_wiki


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: str, label: str, *, required: bool = False) -> tuple[dict[str, Any] | None, str]:
    if not path:
        if required:
            return None, f"{label} path is required"
        return None, ""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{label} not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid {label}: {exc}"
    if not isinstance(data, dict):
        return None, f"{label} root must be an object"
    return data, ""


def existing_path(path: str) -> bool:
    return bool(path) and Path(path).expanduser().exists()


def same_path(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except OSError:
        return False


def add_issue(issues: list[dict[str, str]], key: str, message: str, evidence: str = "") -> None:
    issues.append({"key": key, "message": message, "evidence": evidence})


def path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def stage_failures(status: dict[str, Any]) -> list[str]:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return ["stages missing or not an object"]
    failures: list[str] = []
    for stage_id, data in stages.items():
        if not isinstance(data, dict):
            failures.append(f"{stage_id}: stage is not an object")
            continue
        if data.get("status") != "passed":
            blockers = data.get("blockers")
            detail = ", ".join(str(item) for item in blockers) if isinstance(blockers, list) and blockers else "not passed"
            failures.append(f"{stage_id}: {detail}")
    return failures


def passed_stage_count(status: dict[str, Any]) -> int:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return 0
    return sum(1 for data in stages.values() if isinstance(data, dict) and data.get("status") == "passed")


def package_source_wiki_path(package: dict[str, Any] | None) -> str:
    if not isinstance(package, dict):
        return ""
    value = package.get("sourceWiki")
    return value if isinstance(value, str) else ""


def target_mode_from_package(package: dict[str, Any] | None) -> str:
    if not isinstance(package, dict):
        return ""
    for key in ("targetMode", "target_mode"):
        value = package.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    execution = package.get("execution")
    if isinstance(execution, dict):
        for key in ("targetMode", "target_mode"):
            value = execution.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def objective_requires_new_site(objective: str, package: dict[str, Any] | None) -> bool:
    mode = target_mode_from_package(package).lower()
    if mode in {"new_site", "create_site", "created_site", "from_scratch"}:
        return True
    if mode in {"existing_site", "selected_site"}:
        return False
    text = objective.lower()
    new_site_markers = (
        "new site",
        "create site",
        "created site",
        "from scratch",
        "新建站点",
        "创建站点",
        "从零",
        "从头",
    )
    existing_site_markers = ("existing site", "selected site", "已有站点", "现有站点", "选中站点")
    return any(marker in text for marker in new_site_markers) and not any(marker in text for marker in existing_site_markers)


def source_wiki_markdown_refs(source_wiki: dict[str, Any] | None) -> list[str]:
    if not isinstance(source_wiki, dict):
        return []
    source_set = source_wiki.get("sourceSet")
    if not isinstance(source_set, dict):
        return []
    refs = source_set.get("wikiRefs")
    return [item for item in refs if isinstance(item, str) and item.strip()] if isinstance(refs, list) else []


def is_markdown_path(path: str) -> bool:
    return Path(path).expanduser().suffix.lower() == ".md"


def readable_markdown(path: str) -> tuple[bool, str]:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        return False, "source wiki Markdown artifact not found"
    if file_path.suffix.lower() != ".md":
        return False, "source wiki readable proof must be a Markdown .md file or a markdown export manifest"
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"source wiki Markdown artifact is not readable: {exc}"
    stripped = content.strip()
    if len(stripped) < 20 or "#" not in stripped:
        return False, "source wiki Markdown artifact does not look user-reviewable"
    return True, ""


def markdown_export_index(path: str) -> tuple[str, str]:
    manifest, error = load_json(path, "source wiki Markdown export")
    if error:
        return "", error
    assert manifest is not None
    if manifest.get("kind") != "allincms_source_wiki_markdown_export":
        return "", "JSON wiki refs are not readable proof unless they are allincms_source_wiki_markdown_export manifests"
    files = manifest.get("files")
    if not isinstance(files, dict) or not isinstance(files.get("index"), str) or not files["index"].strip():
        return "", "source wiki Markdown export manifest must include files.index"
    ok, markdown_error = readable_markdown(files["index"])
    if not ok:
        return "", markdown_error
    return files["index"], ""


def resolve_readable_wiki_proof(
    issues: list[dict[str, str]],
    *,
    source_wiki_markdown_path: str,
    source_wiki_markdown_index_path: str,
    refs: list[str],
) -> tuple[str, str]:
    markdown_path = source_wiki_markdown_path
    markdown_index_path = source_wiki_markdown_index_path

    explicit_candidates = [path for path in (markdown_index_path, markdown_path) if path]
    for candidate in explicit_candidates:
        if is_markdown_path(candidate):
            ok, error = readable_markdown(candidate)
            if ok:
                if not markdown_path:
                    markdown_path = candidate
                if not markdown_index_path and Path(candidate).name == "index.md":
                    markdown_index_path = candidate
                return markdown_path, markdown_index_path
            add_issue(issues, "source_wiki_markdown_missing", error, candidate)
            continue
        index, error = markdown_export_index(candidate)
        if index:
            markdown_path = candidate
            markdown_index_path = index
            return markdown_path, markdown_index_path
        add_issue(issues, "source_wiki_markdown_missing", error, candidate)

    for ref in refs:
        if is_markdown_path(ref):
            ok, _ = readable_markdown(ref)
            if ok:
                markdown_path = ref
                markdown_index_path = ref if Path(ref).name == "index.md" else markdown_index_path
                return markdown_path, markdown_index_path
            parent_index = Path(ref).expanduser().parent / "index.md"
            if parent_index.exists():
                ok, _ = readable_markdown(str(parent_index))
                if ok:
                    markdown_path = ref
                    markdown_index_path = str(parent_index)
                    return markdown_path, markdown_index_path

    for ref in refs:
        if Path(ref).expanduser().suffix.lower() == ".json":
            index, _ = markdown_export_index(ref)
            if index:
                return ref, index

    add_issue(
        issues,
        "source_wiki_markdown_missing",
        "readable source wiki Markdown index or markdown export manifest is required for user-reviewable wiki proof",
        "",
    )
    return markdown_path, markdown_index_path


def validate_wiki_layer(
    issues: list[dict[str, str]],
    *,
    source_wiki_path: str,
    source_wiki_markdown_path: str,
    source_wiki_markdown_index_path: str,
) -> tuple[str, str, str]:
    wiki, wiki_error = load_json(source_wiki_path, "source wiki", required=True)
    if wiki_error:
        add_issue(issues, "source_wiki_missing", wiki_error, source_wiki_path)
        return source_wiki_path, source_wiki_markdown_path, source_wiki_markdown_index_path
    assert wiki is not None
    wiki_issues = validate_source_wiki(wiki)
    if wiki_issues:
        add_issue(issues, "source_wiki_invalid", "source wiki validation failed: " + "; ".join(wiki_issues[:8]), source_wiki_path)

    refs = source_wiki_markdown_refs(wiki)
    markdown_path, markdown_index_path = resolve_readable_wiki_proof(
        issues,
        source_wiki_markdown_path=source_wiki_markdown_path,
        source_wiki_markdown_index_path=source_wiki_markdown_index_path,
        refs=refs,
    )
    return source_wiki_path, markdown_path, markdown_index_path


def validate_content_goal_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, Any]:
    status_coverage_issues = status.get("contentGoalCoverageIssues")
    if isinstance(status_coverage_issues, list) and status_coverage_issues:
        add_issue(
            issues,
            "content_goal_coverage_status_issues",
            "source status reports contentGoalCoverage issues: " + "; ".join(str(item) for item in status_coverage_issues[:8]),
            evidence,
        )
    coverage, coverage_errors = matching_coverage(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=True,
    )
    for error in coverage_errors:
        add_issue(issues, "content_goal_coverage_invalid", error, evidence)
    return coverage or {}


def validate_source_identity_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, str]:
    identity, identity_errors = matching_source_identity(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=True,
    )
    for error in identity_errors:
        add_issue(issues, "source_identity_invalid", error, evidence)
    return identity or {}


def validate_created_site_submitted_values_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    objective: str,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, str]:
    submitted_values, submitted_value_errors = matching_created_site_submitted_values(
        [
            ("source execution status", status),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=objective_requires_new_site(objective, package),
    )
    for error in submitted_value_errors:
        add_issue(issues, "created_site_submitted_values_invalid", error, evidence)
    return submitted_values or {}


def validate_content_counts_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, int]:
    counts, count_errors = matching_content_counts(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ]
    )
    for error in count_errors:
        add_issue(issues, "content_counts_invalid", error, evidence)
    return counts or {}


def validate_content_quality_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, Any]:
    status_quality_issues = status.get("contentQualityReviewIssues")
    if isinstance(status_quality_issues, list) and status_quality_issues:
        add_issue(
            issues,
            "content_quality_review_status_issues",
            "source status reports contentQualityReview issues: " + "; ".join(str(item) for item in status_quality_issues[:8]),
            evidence,
        )
    quality, quality_errors = matching_quality_review(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=True,
    )
    for error in quality_errors:
        add_issue(issues, "content_quality_review_invalid", error, evidence)
    return quality or {}


def validate_content_goal_overages_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    quality: dict[str, Any],
    evidence: str,
) -> dict[str, Any]:
    overages, overage_errors = matching_content_goal_overages(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=False,
        quality=quality,
    )
    for error in overage_errors:
        add_issue(issues, "content_goal_overages_invalid", error, evidence)
    return overages or {}


def validate_wiki_review_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> dict[str, Any]:
    status_wiki_issues = status.get("wikiReviewIssues")
    if isinstance(status_wiki_issues, list) and status_wiki_issues:
        add_issue(
            issues,
            "wiki_review_status_issues",
            "source status reports wikiReview issues: " + "; ".join(str(item) for item in status_wiki_issues[:8]),
            evidence,
        )
    review, review_errors = matching_wiki_review(
        [
            ("source execution status", status),
            ("source package", package),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=True,
    )
    for error in review_errors:
        add_issue(issues, "wiki_review_invalid", error, evidence)
    return review or {}


def validate_confirmation_decision_matrix_layer(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
    round_closeout: dict[str, Any] | None,
    evidence: str,
) -> list[dict[str, Any]]:
    status_matrix_issues = status.get("confirmationDecisionMatrixIssues")
    if isinstance(status_matrix_issues, list) and status_matrix_issues:
        add_issue(
            issues,
            "confirmation_decision_matrix_status_issues",
            "source status reports confirmationDecisionMatrix issues: "
            + "; ".join(str(item) for item in status_matrix_issues[:8]),
            evidence,
        )
    matrix, matrix_errors = matching_confirmation_decision_matrix(
        [
            ("source execution status", status),
            ("review packet", review_packet),
            ("confirmation", confirmation),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
            ("final source-run closeout", round_closeout),
        ],
        require_when_present=True,
    )
    for error in matrix_errors:
        add_issue(issues, "confirmation_decision_matrix_invalid", error, evidence)
    return matrix or []


def validate_wiki_review_bindings(
    issues: list[dict[str, str]],
    *,
    wiki_review: dict[str, Any],
    source_wiki_path: str,
    source_wiki_markdown_path: str,
    source_wiki_markdown_index_path: str,
    evidence: str,
) -> None:
    if not wiki_review:
        return
    expected = {
        "sourceWiki": source_wiki_path,
        "sourceWikiMarkdownIndex": source_wiki_markdown_index_path,
    }
    if source_wiki_markdown_path:
        expected["sourceWikiMarkdown"] = source_wiki_markdown_path
    for key, value in expected.items():
        review_value = wiki_review.get(key)
        if isinstance(review_value, str) and isinstance(value, str) and review_value and value and same_path(review_value, value):
            continue
        add_issue(
            issues,
            "wiki_review_binding_mismatch",
            f"wikiReview.{key} must match final verified {key}",
            evidence,
        )


def require_artifact_object(
    issues: list[dict[str, str]],
    *,
    path: str,
    label: str,
    key: str,
    expected_kind: str = "",
) -> dict[str, Any] | None:
    data, error = load_json(path, label)
    if error:
        add_issue(issues, key, error or f"{label} is required", path)
        return None
    if not isinstance(data, dict):
        add_issue(issues, key, f"{label} root must be an object", path)
        return None
    if expected_kind and data.get("kind") != expected_kind:
        add_issue(issues, key, f"{label} kind must be {expected_kind}", path)
    return data


def non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def expected_content_counts(coverage: dict[str, Any]) -> dict[str, int]:
    counts = coverage.get("counts")
    if not isinstance(counts, dict):
        return {}
    expected: dict[str, int] = {}
    for key in ("pages", "products", "posts"):
        value = non_negative_int(counts.get(key))
        if value is not None:
            expected[key] = value
    return expected


def stage_evidence_path(status: dict[str, Any], stage_id: str) -> str:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return ""
    stage_data = stages.get(stage_id)
    if not isinstance(stage_data, dict):
        return ""
    value = stage_data.get("evidence")
    return value if isinstance(value, str) else ""


def count_from_pages_validation(path: str) -> int | None:
    data, error = load_json(path, "pages/site-info validation")
    if error or not isinstance(data, dict):
        return None
    return non_negative_int(data.get("pageCount"))


def site_info_count_from_pages_validation(path: str) -> int | None:
    data, error = load_json(path, "pages/site-info validation")
    if error or not isinstance(data, dict):
        return None
    return non_negative_int(data.get("siteInfoFieldCount"))


def site_info_count_from_forms_media_settings(data: dict[str, Any] | None) -> int | None:
    return forms_media_count(
        data,
        "siteInfoFieldCount",
        "siteInfoFields",
        "verifiedSiteInfoFieldCount",
    )


def forms_media_settings_with_site_info_count(
    data: dict[str, Any] | None,
    status: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    if site_info_count_from_forms_media_settings(data) is not None:
        return data
    if data.get("siteInfoVerified") is not True:
        return data
    count = site_info_count_from_pages_validation(stage_evidence_path(status, "pages_site_info_execution"))
    if count is None:
        return data
    enriched = dict(data)
    verified = dict(enriched.get("verifiedCounts")) if isinstance(enriched.get("verifiedCounts"), dict) else {}
    verified["siteInfoFieldCount"] = count
    enriched["verifiedCounts"] = verified
    return enriched


def batch_validation_counts(batch_validations: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for data in batch_validations:
        content_type = data.get("contentType")
        if content_type not in {"products", "posts"}:
            continue
        count = non_negative_int(data.get("manifestItemCount"))
        if count is None:
            count = non_negative_int(data.get("progressCount"))
        if count is None:
            continue
        counts[content_type] = max(counts.get(content_type, 0), count)
    return counts


def manifest_paths_from_upload_readiness(upload_readiness_items: list[tuple[str, dict[str, Any]]]) -> dict[str, list[str]]:
    paths: dict[str, list[str]] = {}
    for report_path, report in upload_readiness_items:
        manifests = report.get("manifests")
        if not isinstance(manifests, list):
            continue
        for index, manifest_ref in enumerate(manifests):
            if not isinstance(manifest_ref, dict):
                continue
            content_type = manifest_ref.get("contentType")
            manifest_path = manifest_ref.get("path")
            if content_type not in {"products", "posts"}:
                continue
            if isinstance(manifest_path, str) and manifest_path.strip():
                paths.setdefault(content_type, []).append(manifest_path)
            else:
                paths.setdefault(content_type, [])
    return paths


def load_manifest_for_content_type(
    issues: list[dict[str, str]],
    *,
    content_type: Any,
    explicit_path: Any = "",
    manifest_paths_by_type: dict[str, list[str]],
    evidence: str,
    issue_key: str,
) -> tuple[dict[str, Any] | None, str]:
    if content_type not in {"products", "posts"}:
        add_issue(issues, issue_key, "contentType must be products or posts before direct manifest validation", evidence)
        return None, ""
    candidate_paths: list[str] = []
    if isinstance(explicit_path, str) and explicit_path.strip():
        candidate_paths.append(explicit_path)
    candidate_paths.extend(manifest_paths_by_type.get(content_type, []))
    seen: set[str] = set()
    candidate_paths = [path for path in candidate_paths if not (path in seen or seen.add(path))]
    if not candidate_paths:
        add_issue(
            issues,
            issue_key,
            f"final acceptance requires a schema-verified manifest path for {content_type} from sample/batch evidence or upload readiness",
            evidence,
        )
        return None, ""
    for candidate in candidate_paths:
        try:
            return load_manifest(Path(candidate)), candidate
        except SystemExit as exc:
            add_issue(issues, issue_key, f"manifest cannot be loaded for direct validation: {exc}", candidate)
    return None, candidate_paths[0]


def validate_manifest_samples_directly(
    issues: list[dict[str, str]],
    *,
    sample_evidence_paths: list[str],
    sample_evidence: list[dict[str, Any]],
    manifest_paths_by_type: dict[str, list[str]],
    expected_counts: dict[str, int],
) -> None:
    sampled_types = {
        data.get("contentType")
        for data in sample_evidence
        if data.get("contentType") in {"products", "posts"}
    }
    for content_type in ("products", "posts"):
        if expected_counts.get(content_type, 0) > 0 and content_type not in sampled_types:
            add_issue(
                issues,
                "sample_direct_validation_failed",
                f"sample evidence for {content_type} is required because the confirmed content plan includes {content_type}",
                "",
            )
    for path, data in zip(sample_evidence_paths, sample_evidence):
        manifest, manifest_path = load_manifest_for_content_type(
            issues,
            content_type=data.get("contentType"),
            explicit_path=data.get("manifestPath"),
            manifest_paths_by_type=manifest_paths_by_type,
            evidence=path,
            issue_key="sample_direct_validation_failed",
        )
        if manifest is None:
            continue
        sample_issues = validate_sample_evidence(data, manifest)
        for issue in sample_issues:
            add_issue(
                issues,
                "sample_direct_validation_failed",
                f"sample evidence must pass validate_manifest_sample_upload_evidence.py against {manifest_path}: {issue}",
                path,
            )


def validate_batch_validations_directly(
    issues: list[dict[str, str]],
    *,
    batch_validation_paths: list[str],
    batch_validations: list[dict[str, Any]],
    manifest_paths_by_type: dict[str, list[str]],
) -> None:
    for path, validation in zip(batch_validation_paths, batch_validations):
        evidence_path = validation.get("evidence")
        manifest_path = validation.get("manifest")
        base_path = validation.get("baseRunEvidence")
        audit_path = validation.get("frontendAuditReport")
        content_type = validation.get("contentType")
        if not isinstance(evidence_path, str) or not evidence_path.strip():
            add_issue(issues, "batch_direct_validation_failed", "batch validation must include evidence path for final direct validation", path)
            continue
        evidence, evidence_error = load_json(evidence_path, "batch evidence")
        if evidence_error:
            add_issue(issues, "batch_direct_validation_failed", evidence_error, evidence_path)
            continue
        assert evidence is not None
        manifest, resolved_manifest_path = load_manifest_for_content_type(
            issues,
            content_type=content_type,
            explicit_path=manifest_path,
            manifest_paths_by_type=manifest_paths_by_type,
            evidence=path,
            issue_key="batch_direct_validation_failed",
        )
        if manifest is None:
            continue
        base_run_evidence = None
        if isinstance(base_path, str) and base_path.strip():
            base_run_evidence, base_error = load_json(base_path, "base run evidence")
            if base_error:
                add_issue(issues, "batch_direct_validation_failed", base_error, base_path)
                continue
        audit_reports = None
        if isinstance(audit_path, str) and audit_path.strip():
            try:
                audit_reports = load_json_any(Path(audit_path), "frontend audit report JSON")
            except ValueError as exc:
                add_issue(issues, "batch_direct_validation_failed", str(exc), audit_path)
                continue
        batch_issues = validate_batch_evidence(
            evidence,
            manifest=manifest,
            base_run_evidence=base_run_evidence,
            audit_reports=audit_reports,
        )
        for issue in batch_issues:
            add_issue(
                issues,
                "batch_direct_validation_failed",
                f"batch validation must re-pass validate_batch_upload_publish_evidence.py against {resolved_manifest_path}: {issue}",
                path,
            )


def final_frontend_pointer(result: dict[str, Any], key: str) -> str:
    value = result.get(key)
    if isinstance(value, str) and value.strip():
        return value
    nested = result.get("auditArtifacts")
    if isinstance(nested, dict):
        nested_value = nested.get(key)
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value
    return ""


def validate_final_frontend_audit_directly(
    issues: list[dict[str, str]],
    *,
    final_frontend_audit: dict[str, Any],
    final_frontend_audit_path: str,
) -> None:
    validation = validate_browser_stage_result(final_frontend_audit)
    for issue in validation.get("issues", []):
        add_issue(
            issues,
            "final_frontend_audit_direct_validation_failed",
            f"final frontend audit result must pass validate_browser_stage_result.py: {issue}",
            final_frontend_audit_path,
        )
    if final_frontend_audit.get("stageId") != "final_frontend_audit":
        add_issue(
            issues,
            "final_frontend_audit_direct_validation_failed",
            "final frontend audit result stageId must be final_frontend_audit",
            final_frontend_audit_path,
        )

    audit_report_path = final_frontend_pointer(final_frontend_audit, "auditReport")
    if not audit_report_path:
        pointers = final_frontend_audit.get("redactedEvidencePointers")
        if isinstance(pointers, list):
            json_pointers = [
                item
                for item in pointers
                if isinstance(item, str)
                and item.strip()
                and not item.startswith("local://")
                and Path(item).expanduser().suffix.lower() == ".json"
            ]
            if len(json_pointers) == 1:
                audit_report_path = json_pointers[0]
    if not audit_report_path:
        add_issue(
            issues,
            "final_frontend_audit_direct_validation_failed",
            "final frontend audit must point to the redacted audit report JSON with auditReport or a single JSON redactedEvidencePointer",
            final_frontend_audit_path,
        )
        return

    try:
        reports = load_reports(Path(audit_report_path).expanduser())
    except ValueError as exc:
        add_issue(issues, "final_frontend_audit_direct_validation_failed", str(exc), audit_report_path)
        return

    summary_data = None
    summary_path = final_frontend_pointer(final_frontend_audit, "auditInputsSummary")
    if summary_path:
        summary_data, summary_error = load_json(summary_path, "final frontend audit inputs summary")
        if summary_error:
            add_issue(issues, "final_frontend_audit_direct_validation_failed", summary_error, summary_path)
            summary_data = None

    expected_statuses = None
    expected_path = final_frontend_pointer(final_frontend_audit, "expectedStatuses")
    if expected_path:
        try:
            loaded_statuses = load_json_any(Path(expected_path).expanduser(), "final frontend expected statuses")
        except ValueError as exc:
            add_issue(issues, "final_frontend_audit_direct_validation_failed", str(exc), expected_path)
            loaded_statuses = None
        if isinstance(loaded_statuses, dict):
            expected_statuses = loaded_statuses
        elif loaded_statuses is not None:
            add_issue(
                issues,
                "final_frontend_audit_direct_validation_failed",
                "final frontend expected statuses must be a JSON object",
                expected_path,
            )

    _proof, blockers = summarize_reports(reports, fail_on_warn=bool(final_frontend_audit.get("failOnWarn")))
    blockers.extend(validate_expected_coverage(reports, summary_data, expected_statuses))
    for blocker in blockers:
        add_issue(
            issues,
            "final_frontend_audit_direct_validation_failed",
            f"final frontend audit report still has blocking issue: {blocker}",
            audit_report_path,
        )


def validate_cleanup_directly(
    issues: list[dict[str, str]],
    *,
    cleanup_evidence: dict[str, Any],
    cleanup_evidence_path: str,
) -> None:
    candidates = cleanup_evidence.get("cleanedCandidates")
    if isinstance(candidates, list) and candidates:
        direct_issues = validate_cleanup_evidence(cleanup_evidence)
        for issue in direct_issues:
            add_issue(
                issues,
                "cleanup_evidence_direct_validation_failed",
                f"cleanup evidence must pass validate_probe_cleanup_evidence.py: {issue}",
                cleanup_evidence_path,
            )
        return

    if candidates not in ([], None):
        add_issue(
            issues,
            "cleanup_evidence_direct_validation_failed",
            "cleanedCandidates must be an array when present",
            cleanup_evidence_path,
        )
    if cleanup_evidence.get("noCandidatesVerified") is not True:
        add_issue(
            issues,
            "cleanup_evidence_direct_validation_failed",
            "cleanup evidence with no cleaned candidates must set noCandidatesVerified=true",
            cleanup_evidence_path,
        )
    scanned = cleanup_evidence.get("scannedSurfaces")
    if not isinstance(scanned, list) or not scanned or not all(isinstance(item, str) and item.strip() for item in scanned):
        add_issue(
            issues,
            "cleanup_evidence_direct_validation_failed",
            "cleanup evidence with no candidates must list scannedSurfaces",
            cleanup_evidence_path,
        )
    for key in ("backendVerified", "frontendVerified"):
        if cleanup_evidence.get(key) is not True:
            add_issue(
                issues,
                "cleanup_evidence_direct_validation_failed",
                f"cleanup evidence with no candidates must have {key}=true",
                cleanup_evidence_path,
            )


def validate_round_closeout_directly(
    issues: list[dict[str, str]],
    *,
    round_closeout: dict[str, Any],
    round_closeout_path: str,
) -> None:
    if round_closeout.get("valid") is not True:
        add_issue(issues, "round_closeout_invalid", "round closeout must have valid=true", round_closeout_path)
    if round_closeout.get("kind") == "allincms_round_maintenance_summary":
        add_issue(
            issues,
            "round_closeout_invalid",
            "maintenance closeout summaries cannot prove final source-run browser/upload/launch completion",
            round_closeout_path,
        )
    if round_closeout.get("complete") is not True:
        add_issue(issues, "round_closeout_invalid", "final source-run closeout must have complete=true", round_closeout_path)
    if round_closeout.get("localOnly") is True and round_closeout.get("remoteMutationsPerformed") is False:
        add_issue(
            issues,
            "round_closeout_invalid",
            "final source-run closeout cannot be local-only maintenance evidence with no remote mutation proof",
            round_closeout_path,
        )
    completion_gaps = round_closeout.get("completionGaps")
    if isinstance(completion_gaps, list) and completion_gaps:
        add_issue(issues, "round_closeout_invalid", "final source-run closeout completionGaps must be empty", round_closeout_path)
    sedimentation = round_closeout.get("sedimentation")
    sedimentation_status = sedimentation.get("status") if isinstance(sedimentation, dict) else sedimentation
    if sedimentation_status not in {"updated", "none", "read-only-deferred"}:
        add_issue(issues, "round_closeout_invalid", "round closeout sedimentation must be updated, none, or read-only-deferred", round_closeout_path)
    proof = round_closeout.get("proof") or round_closeout.get("proven")
    if not isinstance(proof, list) or not proof:
        add_issue(issues, "round_closeout_invalid", "final source-run closeout must list browser/run proof", round_closeout_path)
        return
    required_proof_terms = ("source", "site", "schema", "sample", "batch", "frontend", "cleanup", "launch")
    proof_text = " ".join(str(item).lower() for item in proof)
    missing_terms = [term for term in required_proof_terms if term not in proof_text]
    if missing_terms:
        add_issue(
            issues,
            "round_closeout_invalid",
            "final source-run closeout proof must mention: " + ", ".join(missing_terms),
            round_closeout_path,
        )
    required_source_context = (
        ("contentGoalCoverage", dict),
        ("contentCounts", dict),
        ("contentQualityReview", dict),
        ("wikiReview", dict),
        ("confirmationDecisionMatrix", list),
    )
    for key, expected_type in required_source_context:
        value = round_closeout.get(key)
        if not isinstance(value, expected_type) or not value:
            add_issue(
                issues,
                "round_closeout_invalid",
                f"final source-run closeout must carry non-empty {key} from the confirmed source scope",
                round_closeout_path,
            )
    quality = round_closeout.get("contentQualityReview")
    warnings = quality.get("warnings") if isinstance(quality, dict) else []
    has_overage_warning = isinstance(warnings, list) and any(
        isinstance(item, str) and item.startswith("exceeds_declared_content_goal:")
        for item in warnings
    )
    overages = round_closeout.get("contentGoalOverages")
    if has_overage_warning and (not isinstance(overages, dict) or not overages):
        add_issue(
            issues,
            "round_closeout_invalid",
            "final source-run closeout must carry non-empty contentGoalOverages when contentQualityReview has declared-goal overage warnings",
            round_closeout_path,
        )


def validate_final_content_counts(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    content_goal_coverage: dict[str, Any],
    batch_validations: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = expected_content_counts(content_goal_coverage)
    actual: dict[str, int] = {}
    if not expected:
        add_issue(
            issues,
            "final_content_count_mismatch",
            "contentGoalCoverage.counts must expose expected pages/products/posts counts for final acceptance",
            "",
        )
        return {"expected": expected, "actual": actual}

    expected_pages = expected.get("pages", 0)
    if expected_pages > 0:
        pages_validation_path = stage_evidence_path(status, "pages_site_info_execution")
        page_count = count_from_pages_validation(pages_validation_path)
        if page_count is None:
            add_issue(
                issues,
                "final_content_count_mismatch",
                "pages/site-info validation must expose pageCount for final acceptance",
                pages_validation_path,
            )
        else:
            actual["pages"] = page_count
            if page_count < expected_pages:
                add_issue(
                    issues,
                    "final_content_count_mismatch",
                    f"final page proof count {page_count} is lower than confirmed plan count {expected_pages}",
                    pages_validation_path,
                )

    batch_counts = batch_validation_counts(batch_validations)
    for key, content_type in (("products", "products"), ("posts", "posts")):
        expected_count = expected.get(key, 0)
        if expected_count <= 0:
            continue
        actual_count = batch_counts.get(content_type)
        if actual_count is None:
            add_issue(
                issues,
                "final_content_count_mismatch",
                f"{content_type} batch validation must expose manifestItemCount or progressCount for final acceptance",
                "",
            )
            continue
        actual[key] = actual_count
        if actual_count < expected_count:
            add_issue(
                issues,
                "final_content_count_mismatch",
                f"final {content_type} proof count {actual_count} is lower than confirmed plan count {expected_count}",
                "",
            )

    return {"expected": expected, "actual": actual}


def first_non_negative_int(*values: Any) -> int | None:
    for value in values:
        parsed = non_negative_int(value)
        if parsed is not None:
            return parsed
    return None


def nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def load_optional_json(path: str, label: str, issues: list[dict[str, str]], issue_key: str) -> dict[str, Any] | None:
    if not path:
        return None
    data, error = load_json(path, label)
    if error:
        add_issue(issues, issue_key, error, path)
        return None
    return data


def final_frontend_count(final_frontend_audit: dict[str, Any], key: str, issues: list[dict[str, str]]) -> int | None:
    direct = first_non_negative_int(
        final_frontend_audit.get(key),
        nested_dict(final_frontend_audit.get("auditArtifacts")).get(key),
    )
    if direct is not None:
        return direct
    summary_path = final_frontend_pointer(final_frontend_audit, "auditInputsSummary")
    summary = load_optional_json(summary_path, "final frontend audit inputs summary", issues, "final_structure_count_mismatch")
    if isinstance(summary, dict):
        return first_non_negative_int(summary.get(key))
    return None


def module_deferred(evidence: dict[str, Any] | None, module: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    deferrals = evidence.get("deferrals")
    if not isinstance(deferrals, list):
        return False
    for item in deferrals:
        if isinstance(item, dict) and item.get("module") == module:
            return True
    return False


def forms_media_count(evidence: dict[str, Any] | None, *keys: str) -> int | None:
    if not isinstance(evidence, dict):
        return None
    values: list[Any] = [evidence.get(key) for key in keys]
    proof = evidence.get("proof")
    if isinstance(proof, dict):
        values.extend(proof.get(key) for key in keys)
    verified = evidence.get("verifiedCounts")
    if isinstance(verified, dict):
        values.extend(verified.get(key) for key in keys)
    return first_non_negative_int(*values)


def expected_site_info_fields(content_counts: dict[str, int], content_goal_coverage: dict[str, Any]) -> int:
    count = non_negative_int(content_counts.get("siteInfoFields"))
    if count is not None:
        return count
    coverage_counts = content_goal_coverage.get("counts")
    if isinstance(coverage_counts, dict):
        count = non_negative_int(coverage_counts.get("siteInfoFields"))
        if count is not None:
            return count
    return 0


def validate_final_structure_counts(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    content_goal_coverage: dict[str, Any],
    content_counts: dict[str, int],
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    coverage_counts = content_goal_coverage.get("counts")
    if not isinstance(coverage_counts, dict):
        coverage_counts = {}
    expected = {
        "navigationItems": non_negative_int(coverage_counts.get("navigationItems")) or 0,
        "taxonomyTerms": sum(
            non_negative_int(coverage_counts.get(key)) or 0
            for key in ("productCategories", "postCategories", "productTags", "postTags")
        ),
        "forms": non_negative_int(content_counts.get("forms")) or 0,
        "media": non_negative_int(content_counts.get("media")) or 0,
        "siteInfoFields": expected_site_info_fields(content_counts, content_goal_coverage),
    }
    actual: dict[str, Any] = {}

    if expected["navigationItems"] > 0:
        count = final_frontend_count(final_frontend_audit or {}, "navigationItemCount", issues)
        if count is None:
            add_issue(
                issues,
                "final_structure_count_mismatch",
                "final frontend audit must expose navigationItemCount when the confirmed plan includes navigation items",
                "",
            )
        else:
            actual["navigationItems"] = count
            if count < expected["navigationItems"]:
                add_issue(
                    issues,
                    "final_structure_count_mismatch",
                    f"final navigation proof count {count} is lower than confirmed plan count {expected['navigationItems']}",
                    "",
                )

    if expected["taxonomyTerms"] > 0:
        taxonomy_validation_path = stage_evidence_path(status, "taxonomy_execution")
        taxonomy = load_optional_json(
            taxonomy_validation_path,
            "taxonomy execution validation",
            issues,
            "final_structure_count_mismatch",
        )
        count = first_non_negative_int(taxonomy.get("taxonomyMappingCount") if isinstance(taxonomy, dict) else None)
        if count is None:
            add_issue(
                issues,
                "final_structure_count_mismatch",
                "taxonomy execution validation must expose taxonomyMappingCount when confirmed categories/tags exist",
                taxonomy_validation_path,
            )
        else:
            actual["taxonomyTerms"] = count
            if count < expected["taxonomyTerms"]:
                add_issue(
                    issues,
                    "final_structure_count_mismatch",
                    f"final taxonomy mapping count {count} is lower than confirmed taxonomy term count {expected['taxonomyTerms']}",
                    taxonomy_validation_path,
                )

    if expected["forms"] > 0:
        if module_deferred(forms_media_settings, "forms"):
            actual["forms"] = "deferred"
        else:
            count = forms_media_count(forms_media_settings, "formCount", "formsCount", "verifiedFormCount")
            if count is None:
                add_issue(
                    issues,
                    "final_structure_count_mismatch",
                    "forms/media/settings evidence must expose formCount when confirmed contentCounts.forms is greater than zero",
                    "",
                )
            else:
                actual["forms"] = count
                if count < expected["forms"]:
                    add_issue(
                        issues,
                        "final_structure_count_mismatch",
                        f"final form proof count {count} is lower than confirmed form count {expected['forms']}",
                        "",
                    )

    if expected["siteInfoFields"] > 0:
        if module_deferred(forms_media_settings, "site-info"):
            actual["siteInfoFields"] = "deferred"
        else:
            pages_validation_path = stage_evidence_path(status, "pages_site_info_execution")
            forms_count = site_info_count_from_forms_media_settings(forms_media_settings)
            count = forms_count
            if count is None:
                count = site_info_count_from_pages_validation(pages_validation_path)
            if count is None:
                add_issue(
                    issues,
                    "final_structure_count_mismatch",
                    "pages/site-info validation or forms/media/settings evidence must expose siteInfoFieldCount when confirmed contentCounts.siteInfoFields is greater than zero",
                    pages_validation_path,
                )
            else:
                actual["siteInfoFields"] = count
                if count < expected["siteInfoFields"]:
                    add_issue(
                        issues,
                        "final_structure_count_mismatch",
                        f"final site-info field proof count {count} is lower than confirmed site-info field count {expected['siteInfoFields']}",
                        "",
                    )

    if expected["media"] > 0:
        if module_deferred(forms_media_settings, "media"):
            actual["media"] = "deferred"
        else:
            count = forms_media_count(forms_media_settings, "mediaCount", "uploadedMediaCount", "verifiedMediaCount")
            if count is None:
                add_issue(
                    issues,
                    "final_structure_count_mismatch",
                    "forms/media/settings evidence must expose mediaCount when confirmed contentCounts.media is greater than zero",
                    "",
                )
            else:
                actual["media"] = count
                if count < expected["media"]:
                    add_issue(
                        issues,
                        "final_structure_count_mismatch",
                        f"final media proof count {count} is lower than confirmed media count {expected['media']}",
                        "",
                    )

    return {"expected": expected, "actual": actual}


def validate_final_artifact_bindings(
    issues: list[dict[str, str]],
    *,
    status: dict[str, Any],
    package: dict[str, Any] | None,
    objective: str,
    content_goal_coverage: dict[str, Any],
    content_counts: dict[str, int],
    created_site_binding_path: str,
    upload_readiness_path: Any,
    sample_evidence_paths: list[str],
    batch_validation_paths: list[str],
    forms_media_settings_path: str,
    final_frontend_audit_path: str,
    cleanup_evidence_path: str,
    round_closeout_path: str,
) -> dict[str, Any]:
    created_site_binding = require_artifact_object(
        issues,
        path=created_site_binding_path,
        label="created-site binding",
        key="created_site_binding_missing",
        expected_kind="allincms_created_site_artifact_binding",
    )
    upload_readiness_paths = path_list(upload_readiness_path)
    upload_readiness_items: list[tuple[str, dict[str, Any]]] = []
    if not upload_readiness_paths:
        add_issue(issues, "upload_readiness_missing", "at least one upload readiness artifact is required", "")
    for path in upload_readiness_paths:
        data = require_artifact_object(
            issues,
            path=path,
            label="upload readiness",
            key="upload_readiness_missing",
            expected_kind="allincms_manifest_upload_readiness_report",
        )
        if isinstance(data, dict):
            upload_readiness_items.append((path, data))
    forms_media_settings = require_artifact_object(
        issues,
        path=forms_media_settings_path,
        label="forms/media/settings evidence",
        key="forms_media_settings_missing",
        expected_kind="allincms_forms_media_settings_evidence",
    )
    final_frontend_audit = require_artifact_object(
        issues,
        path=final_frontend_audit_path,
        label="final frontend audit",
        key="final_frontend_audit_missing",
    )
    cleanup_evidence = require_artifact_object(
        issues,
        path=cleanup_evidence_path,
        label="cleanup evidence",
        key="cleanup_evidence_missing",
    )
    round_closeout = require_artifact_object(
        issues,
        path=round_closeout_path,
        label="round closeout",
        key="round_closeout_missing",
    )
    sample_evidence: list[dict[str, Any]] = []
    if not sample_evidence_paths:
        add_issue(issues, "sample_evidence_missing", "at least one manifest sample evidence artifact is required", "")
    for path in sample_evidence_paths:
        data = require_artifact_object(
            issues,
            path=path,
            label="sample evidence",
            key="sample_evidence_missing",
            expected_kind="allincms_manifest_sample_upload_evidence",
        )
        if isinstance(data, dict):
            sample_evidence.append(data)
    batch_validations: list[dict[str, Any]] = []
    if not batch_validation_paths:
        add_issue(issues, "batch_validation_missing", "at least one batch validation artifact is required", "")
    for path in batch_validation_paths:
        data = require_artifact_object(
            issues,
            path=path,
            label="batch validation",
            key="batch_validation_missing",
            expected_kind="allincms_batch_upload_publish_evidence_validation",
        )
        if isinstance(data, dict):
            batch_validations.append(data)

    if isinstance(created_site_binding, dict):
        site_key = created_site_binding.get("siteKey")
        frontend_base_url = created_site_binding.get("frontendBaseUrl")
        if not isinstance(site_key, str) or not site_key.strip():
            add_issue(issues, "site_identity_mismatch", "created-site binding must include siteKey", created_site_binding_path)
            site_key = ""
        if not isinstance(frontend_base_url, str) or not frontend_base_url.startswith("https://"):
            add_issue(issues, "site_identity_mismatch", "created-site binding must include frontendBaseUrl", created_site_binding_path)
            frontend_base_url = ""
        if created_site_binding.get("schemaVerified") is not False:
            add_issue(issues, "created_site_binding_invalid", "created-site binding must have schemaVerified=false", created_site_binding_path)
        binding_mode = created_site_binding.get("siteBindingMode")
        creation_status = created_site_binding.get("siteCreationStatus")
        if binding_mode == "existing_site" and objective_requires_new_site(objective, package):
            add_issue(
                issues,
                "created_site_required",
                "final acceptance for a new-site objective requires siteBindingMode=created_site with siteCreationStatus=created_verified; existing-site binding is continuation proof only",
                created_site_binding_path,
            )
        if binding_mode == "created_site" and creation_status not in {None, "", "created_verified"}:
            add_issue(issues, "created_site_binding_invalid", "created_site binding must have siteCreationStatus=created_verified", created_site_binding_path)
        if binding_mode == "existing_site" and creation_status not in {None, "", "existing_site_selected"}:
            add_issue(issues, "created_site_binding_invalid", "existing_site binding must have siteCreationStatus=existing_site_selected", created_site_binding_path)
        bound = created_site_binding.get("boundArtifacts")
        if not isinstance(bound, dict) or not bound.get("productsManifest") or not bound.get("postsManifest"):
            add_issue(issues, "created_site_binding_invalid", "created-site binding must include bound products/posts manifests", created_site_binding_path)
    else:
        site_key = ""
        frontend_base_url = ""
    for path, upload_readiness in upload_readiness_items:
        if upload_readiness.get("overallStatus") != "ready_for_sample_upload":
            add_issue(issues, "upload_readiness_invalid", "upload readiness overallStatus must be ready_for_sample_upload", path)
        if site_key:
            for index, manifest in enumerate(upload_readiness.get("manifests", []) if isinstance(upload_readiness.get("manifests"), list) else []):
                if isinstance(manifest, dict) and manifest.get("siteKey") not in {None, "", site_key}:
                    add_issue(issues, "site_identity_mismatch", f"upload readiness manifest {index} siteKey must match created-site binding", path)
    manifest_paths_by_type = manifest_paths_from_upload_readiness(upload_readiness_items)
    for path, data in zip(sample_evidence_paths, sample_evidence):
        if site_key and data.get("siteKey") != site_key:
            add_issue(issues, "site_identity_mismatch", "sample evidence siteKey must match created-site binding", path)
        frontend_url = data.get("frontendUrl")
        if frontend_base_url and isinstance(frontend_url, str) and not frontend_url.startswith(frontend_base_url + "/"):
            add_issue(issues, "site_identity_mismatch", "sample evidence frontendUrl must use created-site frontendBaseUrl", path)
        required = ("schemaGatePass", "backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified", "stopConditionMet")
        missing = [key for key in required if data.get(key) is not True]
        if missing:
            add_issue(issues, "sample_evidence_invalid", "sample evidence missing required proof: " + ", ".join(missing), path)
    for path, data in zip(batch_validation_paths, batch_validations):
        if site_key and data.get("siteKey") != site_key:
            add_issue(issues, "site_identity_mismatch", "batch validation siteKey must match created-site binding", path)
        if data.get("valid") is not True:
            add_issue(issues, "batch_validation_invalid", "batch validation must have valid=true", path)
    validate_manifest_samples_directly(
        issues,
        sample_evidence_paths=sample_evidence_paths,
        sample_evidence=sample_evidence,
        manifest_paths_by_type=manifest_paths_by_type,
        expected_counts=expected_content_counts(content_goal_coverage),
    )
    validate_batch_validations_directly(
        issues,
        batch_validation_paths=batch_validation_paths,
        batch_validations=batch_validations,
        manifest_paths_by_type=manifest_paths_by_type,
    )
    if isinstance(forms_media_settings, dict):
        forms_media_settings_for_direct_validation = forms_media_settings_with_site_info_count(
            forms_media_settings,
            status,
        )
        direct_issues = validate_forms_media_settings_evidence(forms_media_settings_for_direct_validation or forms_media_settings)
        for issue in direct_issues:
            add_issue(
                issues,
                "forms_media_settings_direct_validation_failed",
                f"forms/media/settings evidence must pass validate_forms_media_settings_evidence.py: {issue}",
                forms_media_settings_path,
            )
        if site_key and forms_media_settings.get("siteKey") not in {None, "", site_key}:
            add_issue(issues, "site_identity_mismatch", "forms/media/settings siteKey must match created-site binding", forms_media_settings_path)
        forms_media_status = forms_media_settings.get("status")
        if forms_media_status == "explicitly_out_of_scope":
            if not forms_media_settings.get("deferrals"):
                add_issue(issues, "forms_media_settings_invalid", "out-of-scope forms/media/settings evidence needs deferrals", forms_media_settings_path)
        elif not any(forms_media_settings.get(key) is True for key in ("siteInfoVerified", "formsVerified", "mediaVerified", "domainsRecorded", "trackingRecorded")):
            add_issue(issues, "forms_media_settings_invalid", "forms/media/settings evidence must verify or defer in-scope modules", forms_media_settings_path)
    if isinstance(final_frontend_audit, dict):
        validate_final_frontend_audit_directly(
            issues,
            final_frontend_audit=final_frontend_audit,
            final_frontend_audit_path=final_frontend_audit_path,
        )
        if site_key and final_frontend_audit.get("siteKey") not in {None, "", site_key}:
            add_issue(issues, "site_identity_mismatch", "final frontend audit siteKey must match created-site binding", final_frontend_audit_path)
        if final_frontend_audit.get("status") not in {"completed", "passed"}:
            add_issue(issues, "final_frontend_audit_invalid", "final frontend audit status must be completed or passed", final_frontend_audit_path)
        if final_frontend_audit.get("blockers"):
            add_issue(issues, "final_frontend_audit_invalid", "final frontend audit blockers must be empty", final_frontend_audit_path)
    if isinstance(cleanup_evidence, dict):
        validate_cleanup_directly(
            issues,
            cleanup_evidence=cleanup_evidence,
            cleanup_evidence_path=cleanup_evidence_path,
        )
        if site_key and cleanup_evidence.get("siteKey") not in {None, "", site_key}:
            add_issue(issues, "site_identity_mismatch", "cleanup evidence siteKey must match created-site binding", cleanup_evidence_path)
        if cleanup_evidence.get("status") not in {"completed", "cleaned", "verified"}:
            add_issue(issues, "cleanup_evidence_invalid", "cleanup status must be completed, cleaned, or verified", cleanup_evidence_path)
    if isinstance(round_closeout, dict):
        validate_round_closeout_directly(
            issues,
            round_closeout=round_closeout,
            round_closeout_path=round_closeout_path,
        )

    final_content_counts = validate_final_content_counts(
        issues,
        status=status,
        content_goal_coverage=content_goal_coverage,
        batch_validations=batch_validations,
    )
    final_structure_counts = validate_final_structure_counts(
        issues,
        status=status,
        content_goal_coverage=content_goal_coverage,
        content_counts=content_counts,
        forms_media_settings=forms_media_settings if isinstance(forms_media_settings, dict) else None,
        final_frontend_audit=final_frontend_audit if isinstance(final_frontend_audit, dict) else None,
    )

    return {
        "createdSiteBinding": created_site_binding_path,
        "uploadReadiness": upload_readiness_paths,
        "sampleEvidence": sample_evidence_paths,
        "batchValidation": batch_validation_paths,
        "formsMediaSettings": forms_media_settings_path,
        "finalFrontendAudit": final_frontend_audit_path,
        "cleanupEvidence": cleanup_evidence_path,
        "roundCloseout": round_closeout_path,
        "siteKey": site_key,
        "frontendBaseUrl": frontend_base_url,
        "finalContentCounts": final_content_counts,
        "finalStructureCounts": final_structure_counts,
    }


def validate_acceptance(
    *,
    status_path: str,
    next_stage_handoff_path: str = "",
    package_path: str = "",
    review_packet_path: str = "",
    confirmation_path: str = "",
    launch_acceptance_path: str = "",
    created_site_binding_path: str = "",
    upload_readiness_path: Any = "",
    sample_evidence_paths: Any = None,
    batch_validation_paths: Any = None,
    forms_media_settings_path: str = "",
    final_frontend_audit_path: str = "",
    cleanup_evidence_path: str = "",
    round_closeout_path: str = "",
    source_wiki_path: str = "",
    source_wiki_markdown_path: str = "",
    source_wiki_markdown_index_path: str = "",
    objective: str = "",
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    status, error = load_json(status_path, "source execution status", required=True)
    if error:
        add_issue(issues, "source_status_load_failed", error, status_path)
        status = {}
    assert status is not None
    if status.get("kind") != "allincms_source_execution_status":
        add_issue(issues, "source_status_kind", "status kind must be allincms_source_execution_status", status_path)
    if status.get("localOnly") is not True:
        add_issue(issues, "source_status_local_only", "source status must be localOnly=true", status_path)
    if status.get("remoteMutationsPerformed") is not False:
        add_issue(issues, "source_status_remote_mutation", "source status must not itself perform remote mutations", status_path)
    if status.get("complete") is not True or status.get("currentStage") != "complete":
        add_issue(
            issues,
            "source_status_incomplete",
            f"source status must be complete/currentStage=complete, got complete={status.get('complete')} currentStage={status.get('currentStage')}",
            status_path,
        )
    failures = stage_failures(status)
    if failures:
        add_issue(issues, "source_stage_failures", "all source execution stages must be passed: " + "; ".join(failures[:8]), status_path)
    if isinstance(status.get("stageCount"), int) and status.get("stageCount") != passed_stage_count(status):
        add_issue(
            issues,
            "source_stage_count_mismatch",
            f"passedCount/stageCount mismatch: passed={passed_stage_count(status)} stageCount={status.get('stageCount')}",
            status_path,
        )

    if next_stage_handoff_path:
        handoff, handoff_error = load_json(next_stage_handoff_path, "source next-stage handoff")
        if handoff_error:
            add_issue(issues, "next_stage_handoff_load_failed", handoff_error, next_stage_handoff_path)
        else:
            assert handoff is not None
            if handoff.get("kind") != "allincms_source_next_stage_handoff":
                add_issue(issues, "next_stage_handoff_kind", "handoff kind must be allincms_source_next_stage_handoff", next_stage_handoff_path)
            if handoff.get("currentStage") != "complete":
                add_issue(issues, "next_stage_not_complete", f"handoff currentStage must be complete, got {handoff.get('currentStage')}", next_stage_handoff_path)
            if handoff.get("sourceExecutionStatus") and str(Path(handoff["sourceExecutionStatus"]).resolve()) != str(Path(status_path).resolve()):
                add_issue(issues, "next_stage_status_mismatch", "handoff sourceExecutionStatus must point to this status file", next_stage_handoff_path)
    else:
        add_issue(issues, "next_stage_handoff_missing", "source next-stage handoff is required for acceptance", "")

    package, package_error = load_json(package_path, "source package")
    if package_error:
        add_issue(issues, "package_missing", package_error or "source package is required", package_path)
    elif package and package.get("kind") != "allincms_source_site_package":
        add_issue(issues, "package_kind", "source package kind mismatch", package_path)
    if not source_wiki_path:
        source_wiki_path = package_source_wiki_path(package)
    source_wiki_path, source_wiki_markdown_path, source_wiki_markdown_index_path = validate_wiki_layer(
        issues,
        source_wiki_path=source_wiki_path,
        source_wiki_markdown_path=source_wiki_markdown_path,
        source_wiki_markdown_index_path=source_wiki_markdown_index_path,
    )

    review_packet, review_error = load_json(review_packet_path, "review packet")
    if review_error:
        add_issue(issues, "review_packet_missing", review_error or "review packet is required", review_packet_path)
    elif review_packet and review_packet.get("kind") != "allincms_source_package_review_packet":
        add_issue(issues, "review_packet_kind", "review packet kind mismatch", review_packet_path)

    confirmation, confirmation_error = load_json(confirmation_path, "confirmation")
    if confirmation_error:
        add_issue(issues, "confirmation_missing", confirmation_error or "confirmation record is required", confirmation_path)
    elif confirmation:
        if confirmation.get("kind") != "allincms_source_site_package_confirmation":
            add_issue(issues, "confirmation_kind", "confirmation kind mismatch", confirmation_path)
        if confirmation.get("isRemoteMutationAuthorization") is not False:
            add_issue(issues, "confirmation_authorization_confusion", "content confirmation must not be remote mutation authorization", confirmation_path)

    launch, launch_error = load_json(launch_acceptance_path, "launch acceptance validation")
    if launch_error:
        add_issue(issues, "launch_acceptance_missing", launch_error or "launch acceptance validation is required", launch_acceptance_path)
    elif launch:
        if launch.get("kind") != "allincms_launch_acceptance_validation":
            add_issue(issues, "launch_acceptance_kind", "launch acceptance kind mismatch", launch_acceptance_path)
        if launch.get("valid") is not True or launch.get("complete") is not True:
            add_issue(issues, "launch_acceptance_incomplete", "launch acceptance must have valid=true and complete=true", launch_acceptance_path)

    final_frontend_audit_for_context, _final_frontend_audit_context_error = load_json(
        final_frontend_audit_path,
        "final frontend audit",
    )
    round_closeout_for_context, _round_closeout_context_error = load_json(
        round_closeout_path,
        "final source-run closeout",
    )
    coverage = validate_content_goal_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    created_site_binding_for_quality, _created_site_binding_quality_error = load_json(
        created_site_binding_path,
        "created-site binding",
    )
    forms_media_settings_for_wiki, _forms_media_settings_wiki_error = load_json(
        forms_media_settings_path,
        "forms/media/settings evidence",
    )
    content_counts = validate_content_counts_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        forms_media_settings=forms_media_settings_for_wiki,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    quality = validate_content_quality_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    overages = validate_content_goal_overages_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        quality=quality,
        evidence=status_path,
    )
    wiki_review = validate_wiki_review_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        forms_media_settings=forms_media_settings_for_wiki,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    validate_wiki_review_bindings(
        issues,
        wiki_review=wiki_review,
        source_wiki_path=source_wiki_path,
        source_wiki_markdown_path=source_wiki_markdown_path,
        source_wiki_markdown_index_path=source_wiki_markdown_index_path,
        evidence=status_path,
    )
    decision_matrix = validate_confirmation_decision_matrix_layer(
        issues,
        status=status,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        forms_media_settings=forms_media_settings_for_wiki,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    source_identity = validate_source_identity_layer(
        issues,
        status=status,
        package=package,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        forms_media_settings=forms_media_settings_for_wiki,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    submitted_values = validate_created_site_submitted_values_layer(
        issues,
        status=status,
        package=package,
        objective=objective,
        launch=launch,
        created_site_binding=created_site_binding_for_quality,
        forms_media_settings=forms_media_settings_for_wiki,
        final_frontend_audit=final_frontend_audit_for_context,
        round_closeout=round_closeout_for_context,
        evidence=status_path,
    )
    final_artifacts = validate_final_artifact_bindings(
        issues,
        status=status,
        package=package,
        objective=objective,
        content_goal_coverage=coverage,
        content_counts=content_counts,
        created_site_binding_path=created_site_binding_path,
        upload_readiness_path=upload_readiness_path,
        sample_evidence_paths=path_list(sample_evidence_paths),
        batch_validation_paths=path_list(batch_validation_paths),
        forms_media_settings_path=forms_media_settings_path,
        final_frontend_audit_path=final_frontend_audit_path,
        cleanup_evidence_path=cleanup_evidence_path,
        round_closeout_path=round_closeout_path,
    )

    accepted = not issues
    return {
        "kind": "allincms_source_run_acceptance_validation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "objective": objective,
        "accepted": accepted,
        "complete": accepted,
        "sourceExecutionStatus": status_path,
        "sourceNextStageHandoff": next_stage_handoff_path,
        "contentGoalCoverage": coverage,
        "contentCounts": content_counts,
        "contentQualityReview": quality,
        "contentGoalOverages": overages,
        "wikiReview": wiki_review,
        "confirmationDecisionMatrix": decision_matrix,
        **source_identity,
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "artifacts": {
            "sourceWiki": source_wiki_path,
            "sourceWikiMarkdown": source_wiki_markdown_path,
            "sourceWikiMarkdownIndex": source_wiki_markdown_index_path,
            "sourcePackage": package_path,
            "reviewPacket": review_packet_path,
            "confirmation": confirmation_path,
            "launchAcceptance": launch_acceptance_path,
            **final_artifacts,
        },
        "stageSummary": {
            "currentStage": status.get("currentStage"),
            "passedCount": passed_stage_count(status),
            "stageCount": status.get("stageCount"),
        },
        "issues": issues,
        "adversarialChecks": [
            "This validates local acceptance artifacts only; it does not replace real browser evidence.",
            "Do not accept a source-file run unless the source wiki JSON and readable wiki layer are present.",
            "Do not accept a run unless contentGoalCoverage is complete and consistent across status, package, review, confirmation, and launch artifacts.",
            "Do not accept a run unless contentCounts is valid and consistent across final source-context artifacts when present.",
            "Do not accept a run unless contentQualityReview is present, valid, and consistent across final source-context artifacts.",
            "Do not accept a run unless contentGoalOverages is present when overage warnings exist and remains consistent across final source-context artifacts.",
            "Do not accept a run unless wikiReview is present, valid, readable, and consistent across final source-context artifacts.",
            "Do not accept a run unless confirmationDecisionMatrix is present and consistent across final source-context artifacts.",
            "Do not accept a run unless sourcePackageSha256 and sourceReviewPacketSha256 are present and consistent across final source-context artifacts.",
            "Do not accept a run unless final acceptance can directly load created-site binding, upload readiness, sample, batch, forms/media/settings, final frontend audit, cleanup, and round closeout artifacts.",
            "Do not accept existing-site binding as proof for a new-site objective; require created-site binding with created_verified status.",
            "Do not mark the user objective complete unless source status is complete and launch acceptance is valid.",
            "Do not treat source-package confirmation as remote mutation authorization.",
            "Do not accept a run when next-stage handoff still points to a non-complete stage.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-file-to-AllinCMS run acceptance.")
    parser.add_argument("--source-status", required=True)
    parser.add_argument("--source-next-stage-handoff", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--created-site-binding", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--final-frontend-audit", default="")
    parser.add_argument("--cleanup-evidence", default="")
    parser.add_argument("--round-closeout", default="")
    parser.add_argument("--source-wiki", default="")
    parser.add_argument("--source-wiki-markdown", default="")
    parser.add_argument("--source-wiki-markdown-index", default="")
    parser.add_argument("--objective", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    report = validate_acceptance(
        status_path=args.source_status,
        next_stage_handoff_path=args.source_next_stage_handoff,
        package_path=args.package,
        review_packet_path=args.review_packet,
        confirmation_path=args.confirmation,
        launch_acceptance_path=args.launch_acceptance,
        created_site_binding_path=args.created_site_binding,
        upload_readiness_path=args.upload_readiness,
        sample_evidence_paths=args.sample_evidence,
        batch_validation_paths=args.batch_validation,
        forms_media_settings_path=args.forms_media_settings,
        final_frontend_audit_path=args.final_frontend_audit,
        cleanup_evidence_path=args.cleanup_evidence,
        round_closeout_path=args.round_closeout,
        source_wiki_path=args.source_wiki,
        source_wiki_markdown_path=args.source_wiki_markdown,
        source_wiki_markdown_index_path=args.source_wiki_markdown_index,
        objective=args.objective,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source run acceptance validation: {output}")
        print(f"accepted={str(report['accepted']).lower()} issues={len(report['issues'])}")
    if args.fail_on_incomplete and not report["accepted"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
