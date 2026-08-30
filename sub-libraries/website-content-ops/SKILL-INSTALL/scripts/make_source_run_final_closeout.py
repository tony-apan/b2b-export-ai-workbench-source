#!/usr/bin/env python3
"""Create final source-run closeout evidence for AllinCMS source-file runs."""

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
from validate_manifest import load_manifest
from validate_manifest_sample_upload_evidence import validate_sample_evidence
from make_final_frontend_audit_stage_result import load_reports, summarize_reports, validate_expected_coverage
from validate_source_wiki import validate_source_wiki


REQUIRED_PROOF_TERMS = ("source", "site", "schema", "sample", "batch", "frontend", "cleanup", "launch")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: str, label: str, *, required: bool = True) -> tuple[dict[str, Any] | None, str]:
    if not path:
        return None, f"{label} path is required" if required else ""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{label} not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid {label}: {exc}"
    if not isinstance(data, dict):
        return None, f"{label} root must be an object"
    return data, ""


def path_list(values: Any) -> list[str]:
    if isinstance(values, str):
        return [values] if values.strip() else []
    if isinstance(values, list):
        return [item for item in values if isinstance(item, str) and item.strip()]
    return []


def non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def add_issue(issues: list[str], message: str) -> None:
    if message not in issues:
        issues.append(message)


def artifact_exists(issues: list[str], path: str, label: str) -> None:
    if not path:
        add_issue(issues, f"{label} path is required")
    elif not Path(path).expanduser().exists():
        add_issue(issues, f"{label} not found: {path}")


def same_path(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except OSError:
        return False


def package_source_wiki_path(package: dict[str, Any] | None) -> str:
    if not isinstance(package, dict):
        return ""
    value = package.get("sourceWiki")
    return value if isinstance(value, str) and value.strip() else ""


def source_wiki_markdown_refs(source_wiki: dict[str, Any] | None) -> list[str]:
    if not isinstance(source_wiki, dict):
        return []
    source_set = source_wiki.get("sourceSet")
    if not isinstance(source_set, dict):
        return []
    refs = source_set.get("wikiRefs")
    if not isinstance(refs, list):
        return []
    return [item for item in refs if isinstance(item, str) and item.strip()]


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
    issues: list[str],
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
            add_issue(issues, error)
            continue
        index, error = markdown_export_index(candidate)
        if index:
            markdown_path = candidate
            markdown_index_path = index
            return markdown_path, markdown_index_path
        add_issue(issues, error)

    for ref in refs:
        if is_markdown_path(ref):
            ok, _error = readable_markdown(ref)
            if ok:
                markdown_path = ref
                markdown_index_path = ref if Path(ref).name == "index.md" else markdown_index_path
                return markdown_path, markdown_index_path
            parent_index = Path(ref).expanduser().parent / "index.md"
            if parent_index.exists():
                ok, _error = readable_markdown(str(parent_index))
                if ok:
                    markdown_path = ref
                    markdown_index_path = str(parent_index)
                    return markdown_path, markdown_index_path

    for ref in refs:
        if Path(ref).expanduser().suffix.lower() == ".json":
            index, _error = markdown_export_index(ref)
            if index:
                return ref, index

    add_issue(
        issues,
        "readable source wiki Markdown index or markdown export manifest is required for user-reviewable wiki proof",
    )
    return markdown_path, markdown_index_path


def validate_wiki_layer(
    issues: list[str],
    *,
    package: dict[str, Any] | None,
    wiki_review: dict[str, Any],
) -> dict[str, str]:
    source_wiki_path = package_source_wiki_path(package)
    if not source_wiki_path:
        add_issue(issues, "source package must include sourceWiki for final closeout")
        return {"sourceWiki": "", "sourceWikiMarkdown": "", "sourceWikiMarkdownIndex": ""}
    wiki, wiki_error = load_json(source_wiki_path, "source wiki")
    if wiki_error:
        add_issue(issues, wiki_error)
        return {"sourceWiki": source_wiki_path, "sourceWikiMarkdown": "", "sourceWikiMarkdownIndex": ""}
    assert wiki is not None
    wiki_issues = validate_source_wiki(wiki)
    if wiki_issues:
        add_issue(issues, "source wiki validation failed: " + "; ".join(wiki_issues[:8]))

    markdown_path = wiki_review.get("sourceWikiMarkdown") if isinstance(wiki_review.get("sourceWikiMarkdown"), str) else ""
    markdown_index_path = (
        wiki_review.get("sourceWikiMarkdownIndex")
        if isinstance(wiki_review.get("sourceWikiMarkdownIndex"), str)
        else ""
    )
    markdown_path, markdown_index_path = resolve_readable_wiki_proof(
        issues,
        source_wiki_markdown_path=markdown_path,
        source_wiki_markdown_index_path=markdown_index_path,
        refs=source_wiki_markdown_refs(wiki),
    )
    return {
        "sourceWiki": source_wiki_path,
        "sourceWikiMarkdown": markdown_path,
        "sourceWikiMarkdownIndex": markdown_index_path,
    }


def validate_wiki_review_bindings(
    issues: list[str],
    *,
    wiki_review: dict[str, Any],
    verified_wiki: dict[str, str],
) -> None:
    if not wiki_review:
        return
    expected = {
        "sourceWiki": verified_wiki.get("sourceWiki", ""),
        "sourceWikiMarkdownIndex": verified_wiki.get("sourceWikiMarkdownIndex", ""),
    }
    if verified_wiki.get("sourceWikiMarkdown"):
        expected["sourceWikiMarkdown"] = verified_wiki["sourceWikiMarkdown"]
    for key, value in expected.items():
        review_value = wiki_review.get(key)
        if isinstance(review_value, str) and value and same_path(review_value, value):
            continue
        add_issue(issues, f"wikiReview.{key} must match final verified {key}")


def load_artifact(issues: list[str], path: str, label: str) -> dict[str, Any] | None:
    data, error = load_json(path, label)
    if error:
        add_issue(issues, error)
        return None
    return data


def upload_readiness_manifest_paths(issues: list[str], upload_readiness_paths: list[str]) -> dict[str, list[str]]:
    by_type: dict[str, list[str]] = {}
    for path in upload_readiness_paths:
        report = load_artifact(issues, path, "upload readiness")
        if not isinstance(report, dict):
            continue
        manifests = report.get("manifests")
        if not isinstance(manifests, list):
            continue
        for manifest_ref in manifests:
            if not isinstance(manifest_ref, dict):
                continue
            content_type = manifest_ref.get("contentType")
            manifest_path = manifest_ref.get("path")
            if content_type not in {"products", "posts"}:
                continue
            if isinstance(manifest_path, str) and manifest_path.strip():
                by_type.setdefault(content_type, []).append(manifest_path)
            else:
                by_type.setdefault(content_type, [])
    return by_type


def load_manifest_for_content_type(
    issues: list[str],
    *,
    content_type: Any,
    explicit_path: Any,
    manifests_by_type: dict[str, list[str]],
    label: str,
) -> tuple[dict[str, Any] | None, str]:
    if content_type not in {"products", "posts"}:
        add_issue(issues, f"{label} contentType must be products or posts")
        return None, ""
    candidates: list[str] = []
    if isinstance(explicit_path, str) and explicit_path.strip():
        candidates.append(explicit_path)
    candidates.extend(manifests_by_type.get(content_type, []))
    seen: set[str] = set()
    candidates = [path for path in candidates if not (path in seen or seen.add(path))]
    if not candidates:
        add_issue(issues, f"{label} requires a schema-verified manifest path for {content_type}")
        return None, ""
    for candidate in candidates:
        try:
            return load_manifest(Path(candidate)), candidate
        except SystemExit as exc:
            add_issue(issues, f"{label} manifest cannot be loaded: {exc}")
    return None, candidates[0]


def expected_content_counts(source_context: dict[str, Any]) -> dict[str, int]:
    coverage = source_context.get("contentGoalCoverage")
    if not isinstance(coverage, dict):
        return {}
    counts = coverage.get("counts")
    if not isinstance(counts, dict):
        return {}
    expected: dict[str, int] = {}
    for key in ("products", "posts"):
        value = non_negative_int(counts.get(key))
        if value is not None:
            expected[key] = value
    return expected


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


def validate_created_site_binding(
    issues: list[str],
    *,
    created_site_binding: dict[str, Any] | None,
    package: dict[str, Any] | None,
    objective: str,
) -> None:
    if not isinstance(created_site_binding, dict):
        return
    binding_mode = created_site_binding.get("siteBindingMode")
    creation_status = created_site_binding.get("siteCreationStatus")
    if objective_requires_new_site(objective, package):
        if binding_mode != "created_site" or creation_status != "created_verified":
            add_issue(
                issues,
                "final closeout for a new-site objective requires siteBindingMode=created_site and siteCreationStatus=created_verified",
            )
    elif binding_mode == "created_site" and creation_status not in {None, "", "created_verified"}:
        add_issue(issues, "created_site binding must have siteCreationStatus=created_verified")
    elif binding_mode == "existing_site" and creation_status not in {None, "", "existing_site_selected"}:
        add_issue(issues, "existing_site binding must have siteCreationStatus=existing_site_selected")


def validate_source_next_stage_handoff(
    issues: list[str],
    *,
    handoff: dict[str, Any] | None,
    handoff_path: str,
    status: dict[str, Any] | None,
    source_status_path: str,
) -> None:
    if not isinstance(handoff, dict):
        return
    if handoff.get("kind") != "allincms_source_next_stage_handoff":
        add_issue(issues, "source next-stage handoff kind must be allincms_source_next_stage_handoff")
    allowed_stages = {"complete"}
    if is_pre_final_closeout_status(status):
        allowed_stages.add("launch_acceptance")
    if handoff.get("currentStage") not in allowed_stages:
        add_issue(
            issues,
            "source next-stage handoff currentStage must be complete"
            + (" or launch_acceptance before auto-final-closeout" if "launch_acceptance" in allowed_stages else "")
            + f", got {handoff.get('currentStage')}",
        )
    status_ref = handoff.get("sourceExecutionStatus")
    if isinstance(status_ref, str) and status_ref.strip():
        if not same_path(status_ref, source_status_path):
            add_issue(issues, "source next-stage handoff sourceExecutionStatus must point to this source status file")
    else:
        add_issue(issues, "source next-stage handoff must include sourceExecutionStatus")


def is_pre_final_closeout_status(status: dict[str, Any] | None) -> bool:
    if not isinstance(status, dict):
        return False
    if status.get("currentStage") != "launch_acceptance" or status.get("complete") is not False:
        return False
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return False
    non_passed = [
        stage_id
        for stage_id, data in stages.items()
        if not isinstance(data, dict) or data.get("status") != "passed"
    ]
    return non_passed == ["launch_acceptance"]


def validate_manifest_samples_directly(
    issues: list[str],
    *,
    sample_paths: list[str],
    manifests_by_type: dict[str, list[str]],
    expected_counts: dict[str, int],
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    sampled_types: set[str] = set()
    for path in sample_paths:
        sample = load_artifact(issues, path, "sample evidence")
        if not isinstance(sample, dict):
            continue
        samples.append(sample)
        content_type = sample.get("contentType")
        if content_type in {"products", "posts"}:
            sampled_types.add(content_type)
        manifest, manifest_path = load_manifest_for_content_type(
            issues,
            content_type=content_type,
            explicit_path=sample.get("manifestPath"),
            manifests_by_type=manifests_by_type,
            label="sample evidence",
        )
        if manifest is None:
            continue
        for issue in validate_sample_evidence(sample, manifest):
            add_issue(issues, f"sample evidence must re-pass validate_manifest_sample_upload_evidence.py against {manifest_path}: {issue}")
    for content_type in ("products", "posts"):
        if expected_counts.get(content_type, 0) > 0 and content_type not in sampled_types:
            add_issue(issues, f"sample evidence for {content_type} is required because the confirmed content plan includes {content_type}")
    return samples


def validate_batch_validations_directly(
    issues: list[str],
    *,
    batch_validation_paths: list[str],
    manifests_by_type: dict[str, list[str]],
    expected_counts: dict[str, int],
) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []
    validated_types: set[str] = set()
    for path in batch_validation_paths:
        validation = load_artifact(issues, path, "batch validation")
        if not isinstance(validation, dict):
            continue
        validations.append(validation)
        content_type = validation.get("contentType")
        if content_type in {"products", "posts"}:
            validated_types.add(content_type)
        if validation.get("valid") is not True:
            add_issue(issues, f"batch validation must have valid=true: {path}")
        evidence_path = validation.get("evidence")
        if not isinstance(evidence_path, str) or not evidence_path.strip():
            add_issue(issues, f"batch validation must include evidence path for direct closeout validation: {path}")
            continue
        evidence = load_artifact(issues, evidence_path, "batch evidence")
        if not isinstance(evidence, dict):
            continue
        manifest, manifest_path = load_manifest_for_content_type(
            issues,
            content_type=content_type,
            explicit_path=validation.get("manifest"),
            manifests_by_type=manifests_by_type,
            label="batch validation",
        )
        if manifest is None:
            continue
        base_run_evidence = None
        base_path = validation.get("baseRunEvidence")
        if isinstance(base_path, str) and base_path.strip():
            base_run_evidence = load_artifact(issues, base_path, "base run evidence")
            if not isinstance(base_run_evidence, dict):
                continue
        audit_reports = None
        audit_path = validation.get("frontendAuditReport")
        if isinstance(audit_path, str) and audit_path.strip():
            try:
                audit_reports = load_json_any(Path(audit_path), "frontend audit report JSON")
            except ValueError as exc:
                add_issue(issues, str(exc))
                continue
        for issue in validate_batch_evidence(evidence, manifest=manifest, base_run_evidence=base_run_evidence, audit_reports=audit_reports):
            add_issue(issues, f"batch validation must re-pass validate_batch_upload_publish_evidence.py against {manifest_path}: {issue}")
    for content_type in ("products", "posts"):
        if expected_counts.get(content_type, 0) > 0 and content_type not in validated_types:
            add_issue(issues, f"batch validation for {content_type} is required because the confirmed content plan includes {content_type}")
    return validations


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


def validate_forms_media_settings_directly(issues: list[str], forms_media_settings: dict[str, Any] | None) -> None:
    if not isinstance(forms_media_settings, dict):
        return
    for issue in validate_forms_media_settings_evidence(forms_media_settings):
        add_issue(issues, f"forms/media/settings evidence must re-pass validate_forms_media_settings_evidence.py: {issue}")


def validate_final_frontend_audit_directly(
    issues: list[str],
    final_frontend_audit: dict[str, Any] | None,
) -> None:
    if not isinstance(final_frontend_audit, dict):
        return
    validation = validate_browser_stage_result(final_frontend_audit)
    for issue in validation.get("issues", []):
        add_issue(issues, f"final frontend audit must re-pass validate_browser_stage_result.py: {issue}")
    if final_frontend_audit.get("stageId") != "final_frontend_audit":
        add_issue(issues, "final frontend audit stageId must be final_frontend_audit")

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
        add_issue(issues, "final frontend audit must point to a redacted audit report JSON")
        return
    try:
        reports = load_reports(Path(audit_report_path).expanduser())
    except ValueError as exc:
        add_issue(issues, str(exc))
        return

    summary_data = None
    summary_path = final_frontend_pointer(final_frontend_audit, "auditInputsSummary")
    if summary_path:
        summary_data, summary_error = load_json(summary_path, "final frontend audit inputs summary")
        if summary_error:
            add_issue(issues, summary_error)
            summary_data = None

    expected_statuses = None
    expected_path = final_frontend_pointer(final_frontend_audit, "expectedStatuses")
    if expected_path:
        try:
            loaded_statuses = load_json_any(Path(expected_path).expanduser(), "final frontend expected statuses")
        except ValueError as exc:
            add_issue(issues, str(exc))
            loaded_statuses = None
        if isinstance(loaded_statuses, dict):
            expected_statuses = loaded_statuses
        elif loaded_statuses is not None:
            add_issue(issues, "final frontend expected statuses must be a JSON object")

    _proof, blockers = summarize_reports(reports, fail_on_warn=bool(final_frontend_audit.get("failOnWarn")))
    blockers.extend(validate_expected_coverage(reports, summary_data, expected_statuses))
    for blocker in blockers:
        add_issue(issues, f"final frontend audit report still has blocking issue: {blocker}")


def passed_stage_count(status: dict[str, Any]) -> int:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return 0
    return sum(1 for data in stages.values() if isinstance(data, dict) and data.get("status") == "passed")


def validate_status(issues: list[str], status: dict[str, Any] | None) -> None:
    if not isinstance(status, dict):
        return
    if status.get("kind") != "allincms_source_execution_status":
        add_issue(issues, "source status kind must be allincms_source_execution_status")
    pre_closeout_only = status.get("currentStage") == "launch_acceptance" and status.get("complete") is False
    if status.get("currentStage") != "complete" and not pre_closeout_only:
        add_issue(issues, f"source status currentStage must be complete, got {status.get('currentStage')}")
    if status.get("complete") is not True and not pre_closeout_only:
        add_issue(issues, "source status complete must be true")
    stages = status.get("stages")
    if not isinstance(stages, dict) or not stages:
        add_issue(issues, "source status stages must be a non-empty object")
        return
    blocked = []
    for stage_id, stage in stages.items():
        if not isinstance(stage, dict) or stage.get("status") != "passed":
            blocked.append(str(stage_id))
    if blocked and not (pre_closeout_only and blocked == ["launch_acceptance"]):
        add_issue(issues, "source status has non-passed stages: " + ", ".join(blocked[:8]))


def validate_launch(issues: list[str], launch: dict[str, Any] | None) -> None:
    if not isinstance(launch, dict):
        return
    if launch.get("kind") != "allincms_launch_acceptance_validation":
        add_issue(issues, "launch acceptance kind must be allincms_launch_acceptance_validation")
    pre_closeout_only = False
    blocked = launch.get("blocked")
    if isinstance(blocked, list):
        blocked_keys = [
            item.get("key")
            for item in blocked
            if isinstance(item, dict)
        ]
        pre_closeout_only = blocked_keys == ["skill_sedimentation_completed_or_readonly_exception_recorded"]
    if launch.get("valid") is not True and not pre_closeout_only:
        add_issue(issues, "launch acceptance valid must be true")
    if launch.get("complete") is not True and not pre_closeout_only:
        add_issue(issues, "launch acceptance complete must be true")


def validate_cleanup(issues: list[str], cleanup: dict[str, Any] | None) -> None:
    if not isinstance(cleanup, dict):
        return
    if cleanup.get("siteKey") in (None, ""):
        add_issue(issues, "cleanup evidence must expose siteKey")
    candidates = cleanup.get("cleanedCandidates")
    if candidates == []:
        if cleanup.get("noCandidatesVerified") is not True:
            add_issue(issues, "cleanup evidence with no candidates must set noCandidatesVerified=true")
        scanned = cleanup.get("scannedSurfaces")
        if not isinstance(scanned, list) or not scanned:
            add_issue(issues, "cleanup evidence with no candidates must list scannedSurfaces")
    for key in ("backendVerified", "frontendVerified"):
        if cleanup.get(key) is not True:
            add_issue(issues, f"cleanup evidence must have {key}=true")


def validate_source_context(
    issues: list[str],
    *,
    status: dict[str, Any] | None,
    package: dict[str, Any] | None,
    objective: str,
    review_packet: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    launch: dict[str, Any] | None,
    created_site_binding: dict[str, Any] | None,
    forms_media_settings: dict[str, Any] | None,
    final_frontend_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    entries = [
        ("source execution status", status),
        ("source package", package),
        ("review packet", review_packet),
        ("confirmation", confirmation),
        ("launch acceptance", launch),
        ("created-site binding", created_site_binding),
        ("forms/media/settings evidence", forms_media_settings),
        ("final frontend audit", final_frontend_audit),
    ]
    coverage, coverage_errors = matching_coverage(entries, require_when_present=True)
    for error in coverage_errors:
        add_issue(issues, error)
    counts, count_errors = matching_content_counts(entries)
    for error in count_errors:
        add_issue(issues, error)
    quality, quality_errors = matching_quality_review(entries, require_when_present=True)
    for error in quality_errors:
        add_issue(issues, error)
    overages, overage_errors = matching_content_goal_overages(entries, require_when_present=False, quality=quality)
    for error in overage_errors:
        add_issue(issues, error)
    wiki_review, wiki_errors = matching_wiki_review(entries, require_when_present=True)
    for error in wiki_errors:
        add_issue(issues, error)
    matrix, matrix_errors = matching_confirmation_decision_matrix(entries, require_when_present=True)
    for error in matrix_errors:
        add_issue(issues, error)
    source_identity, source_identity_errors = matching_source_identity(entries, require_when_present=True)
    for error in source_identity_errors:
        add_issue(issues, error)
    submitted_values, submitted_value_errors = matching_created_site_submitted_values(
        [
            ("source execution status", status),
            ("launch acceptance", launch),
            ("created-site binding", created_site_binding),
            ("forms/media/settings evidence", forms_media_settings),
            ("final frontend audit", final_frontend_audit),
        ],
        require_when_present=objective_requires_new_site(objective, package),
    )
    for error in submitted_value_errors:
        add_issue(issues, error)

    return {
        **(source_identity or {}),
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "contentGoalCoverage": coverage or {},
        "contentCounts": counts or {},
        "contentQualityReview": quality or {},
        "contentGoalOverages": overages or {},
        "wikiReview": wiki_review or {},
        "confirmationDecisionMatrix": matrix or [],
    }


def proof_items(args: argparse.Namespace, status: dict[str, Any] | None) -> list[str]:
    stage_count = status.get("stageCount") if isinstance(status, dict) else ""
    passed_count = passed_stage_count(status or {})
    return [
        "source wiki and source package confirmed",
        "site creation or selected site binding verified",
        "schema capture verified for planned products/posts",
        "sample backend/frontend verification passed for planned content types",
        "batch upload and publish validation passed",
        "frontend launch audit passed",
        "cleanup proof recorded",
        "launch acceptance completed",
        f"source execution status complete with {passed_count}/{stage_count or passed_count} stages passed",
    ]


def completion_gaps(issues: list[str]) -> list[str]:
    return [] if not issues else issues


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    issues: list[str] = []
    status, status_error = load_json(args.source_status, "source status")
    if status_error:
        add_issue(issues, status_error)
    launch, launch_error = load_json(args.launch_acceptance, "launch acceptance")
    if launch_error:
        add_issue(issues, launch_error)
    cleanup, cleanup_error = load_json(args.cleanup_evidence, "cleanup evidence")
    if cleanup_error:
        add_issue(issues, cleanup_error)
    package, package_error = load_json(args.package, "source package")
    if package_error:
        add_issue(issues, package_error)
    review_packet, review_error = load_json(args.review_packet, "review packet")
    if review_error:
        add_issue(issues, review_error)
    confirmation, confirmation_error = load_json(args.confirmation, "confirmation")
    if confirmation_error:
        add_issue(issues, confirmation_error)
    created_site_binding, created_site_binding_error = load_json(args.created_site_binding, "created-site binding")
    if created_site_binding_error:
        add_issue(issues, created_site_binding_error)
    forms_media_settings, forms_media_error = load_json(args.forms_media_settings, "forms/media/settings evidence")
    if forms_media_error:
        add_issue(issues, forms_media_error)
    final_frontend_audit, final_frontend_error = load_json(args.final_frontend_audit, "final frontend audit")
    if final_frontend_error:
        add_issue(issues, final_frontend_error)
    source_next_stage_handoff, source_next_stage_handoff_error = load_json(
        args.source_next_stage_handoff,
        "source next-stage handoff",
    )
    if source_next_stage_handoff_error:
        add_issue(issues, source_next_stage_handoff_error)

    validate_status(issues, status)
    validate_source_next_stage_handoff(
        issues,
        handoff=source_next_stage_handoff,
        handoff_path=args.source_next_stage_handoff,
        status=status,
        source_status_path=args.source_status,
    )
    validate_launch(issues, launch)
    validate_cleanup(issues, cleanup)
    validate_forms_media_settings_directly(issues, forms_media_settings)
    validate_final_frontend_audit_directly(issues, final_frontend_audit)
    validate_created_site_binding(
        issues,
        created_site_binding=created_site_binding,
        package=package,
        objective=args.objective,
    )
    source_context = validate_source_context(
        issues,
        status=status,
        package=package,
        objective=args.objective,
        review_packet=review_packet,
        confirmation=confirmation,
        launch=launch,
        created_site_binding=created_site_binding,
        forms_media_settings=forms_media_settings,
        final_frontend_audit=final_frontend_audit,
    )
    package_wiki_review = package.get("wikiReview") if isinstance(package, dict) and isinstance(package.get("wikiReview"), dict) else {}
    context_wiki_review = source_context.get("wikiReview") if isinstance(source_context.get("wikiReview"), dict) else {}
    verified_wiki = validate_wiki_layer(
        issues,
        package=package,
        wiki_review=package_wiki_review or context_wiki_review,
    )
    validate_wiki_review_bindings(
        issues,
        wiki_review=context_wiki_review,
        verified_wiki=verified_wiki,
    )
    if verified_wiki.get("sourceWiki"):
        source_context["wikiReview"] = {
            **(source_context.get("wikiReview") if isinstance(source_context.get("wikiReview"), dict) else {}),
            **verified_wiki,
        }

    artifact_requirements = [
        (args.source_status, "source status"),
        (args.source_next_stage_handoff, "source next-stage handoff"),
        (args.package, "source package"),
        (args.review_packet, "review packet"),
        (args.confirmation, "confirmation"),
        (args.created_site_binding, "created-site binding"),
        (args.forms_media_settings, "forms/media/settings evidence"),
        (args.final_frontend_audit, "final frontend audit"),
        (args.cleanup_evidence, "cleanup evidence"),
        (args.launch_acceptance, "launch acceptance"),
    ]
    for path, label in artifact_requirements:
        artifact_exists(issues, path, label)
    for index, path in enumerate(path_list(args.upload_readiness), start=1):
        artifact_exists(issues, path, f"upload readiness {index}")
    for index, path in enumerate(path_list(args.sample_evidence), start=1):
        artifact_exists(issues, path, f"sample evidence {index}")
    for index, path in enumerate(path_list(args.batch_validation), start=1):
        artifact_exists(issues, path, f"batch validation {index}")

    if not path_list(args.upload_readiness):
        add_issue(issues, "at least one upload readiness artifact is required")
    if not path_list(args.sample_evidence):
        add_issue(issues, "at least one sample evidence artifact is required")
    if not path_list(args.batch_validation):
        add_issue(issues, "at least one batch validation artifact is required")

    upload_readiness_paths = path_list(args.upload_readiness)
    manifests_by_type = upload_readiness_manifest_paths(issues, upload_readiness_paths)
    expected_counts = expected_content_counts(source_context)
    validate_manifest_samples_directly(
        issues,
        sample_paths=path_list(args.sample_evidence),
        manifests_by_type=manifests_by_type,
        expected_counts=expected_counts,
    )
    validate_batch_validations_directly(
        issues,
        batch_validation_paths=path_list(args.batch_validation),
        manifests_by_type=manifests_by_type,
        expected_counts=expected_counts,
    )

    sedimentation_status = args.sedimentation
    if sedimentation_status not in {"updated", "none", "read-only-deferred"}:
        add_issue(issues, "sedimentation must be updated, none, or read-only-deferred")
    if not args.sedimentation_note.strip():
        add_issue(issues, "sedimentation note is required")

    proof = proof_items(args, status)
    proof_text = " ".join(item.lower() for item in proof)
    missing_terms = [term for term in REQUIRED_PROOF_TERMS if term not in proof_text]
    if missing_terms:
        add_issue(issues, "final closeout proof must mention: " + ", ".join(missing_terms))

    complete = not issues
    return {
        "kind": "allincms_source_run_final_closeout",
        "generatedAt": now_iso(),
        "valid": complete,
        "complete": complete,
        "localOnly": False,
        "remoteMutationsPerformed": True,
        "siteKey": (status or {}).get("siteKey") or (cleanup or {}).get("siteKey") or "",
        "objective": args.objective,
        "sourceExecutionStatus": args.source_status,
        "sourceNextStageHandoff": args.source_next_stage_handoff,
        "artifacts": {
            "sourcePackage": args.package,
            "reviewPacket": args.review_packet,
            "confirmation": args.confirmation,
            "createdSiteBinding": args.created_site_binding,
            "uploadReadiness": path_list(args.upload_readiness),
            "sampleEvidence": path_list(args.sample_evidence),
            "batchValidation": path_list(args.batch_validation),
            "formsMediaSettings": args.forms_media_settings,
            "finalFrontendAudit": args.final_frontend_audit,
            "cleanupEvidence": args.cleanup_evidence,
            "launchAcceptance": args.launch_acceptance,
        },
        "proof": proof,
        **source_context,
        "missing": [] if complete else ["final source-run acceptance prerequisites are incomplete"],
        "completionGaps": completion_gaps(issues),
        "nextActions": [] if complete else ["Fix completionGaps, rerun the failing stage helper, then regenerate final source-run closeout."],
        "sedimentation": {
            "status": sedimentation_status,
            "note": args.sedimentation_note,
        },
        "adversarialChecks": [
            "This helper creates final closeout evidence only; it does not perform browser verification or upload.",
            "Final closeout is valid only when source status and launch acceptance are complete.",
            "Final closeout must still be passed into validate_source_run_acceptance.py before claiming the full objective complete.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create final source-run closeout evidence.")
    parser.add_argument("--source-status", required=True)
    parser.add_argument("--source-next-stage-handoff", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--created-site-binding", required=True)
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--forms-media-settings", required=True)
    parser.add_argument("--final-frontend-audit", required=True)
    parser.add_argument("--cleanup-evidence", required=True)
    parser.add_argument("--launch-acceptance", required=True)
    parser.add_argument("--objective", default="source files to launched AllinCMS site")
    parser.add_argument("--sedimentation", required=True, choices=["updated", "none", "read-only-deferred"])
    parser.add_argument("--sedimentation-note", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    ensure_output_outside_skill(output)
    summary = build_summary(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote final source-run closeout: {output}")
    if args.fail_on_incomplete and summary.get("complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
