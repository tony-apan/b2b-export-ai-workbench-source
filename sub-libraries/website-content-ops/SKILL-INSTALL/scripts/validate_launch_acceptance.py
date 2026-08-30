#!/usr/bin/env python3
"""Validate AllinCMS launch acceptance evidence without overclaiming."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from apply_browser_stage_result import validate_browser_stage_result
from make_final_frontend_audit_stage_result import load_reports, summarize_reports, validate_expected_coverage
from validate_run_evidence import validate as validate_run_evidence
from validate_batch_upload_publish_evidence import load_json_any


REQUIRED_SETUP_KEYS = ("siteInfo", "domains", "themes", "routes", "forms", "tracking")
REQUIRED_ACCEPTANCE_KEYS = (
    "site_created_and_verified",
    "setup_pages_read_only_inspected",
    "module_interface_capture_complete",
    "theme_route_launch_ready",
    "static_frontend_routes_render",
    "content_type_save_request_captured_and_persisted",
    "sample_backend_frontend_verified",
    "manifest_schema_gate_passed",
    "batch_upload_publish_verified",
    "forms_media_settings_verified_or_explicitly_out_of_scope",
    "final_frontend_audit_passed",
    "probe_cleanup_completed",
    "skill_sedimentation_completed_or_readonly_exception_recorded",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: str | None, label: str) -> Any:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}")


def path_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def load_json_items(paths: Any, label: str) -> list[Any]:
    return [load_json(path, f"{label}: {path}") for path in path_list(paths)]


def ok_item(key: str, evidence: str, details: str = "") -> dict[str, Any]:
    return {"key": key, "status": "passed", "evidence": evidence, "details": details, "blockers": []}


def blocked_item(key: str, blockers: list[str], evidence: str = "", details: str = "") -> dict[str, Any]:
    return {
        "key": key,
        "status": "blocked",
        "evidence": evidence,
        "details": details,
        "blockers": blockers or ["missing proof"],
    }


def bools_true(data: dict[str, Any], keys: tuple[str, ...] | list[str]) -> list[str]:
    return [key for key in keys if data.get(key) is not True]


def non_empty_shape(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return True
        return not isinstance(parsed, dict) or bool(parsed)
    return False


def non_empty_render_audit(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return False


def setup_passed(run: dict[str, Any]) -> dict[str, Any]:
    setup = run.get("setupPages")
    if not isinstance(setup, dict):
        return blocked_item("setup_pages_read_only_inspected", ["runEvidence.setupPages missing"])
    missing = [key for key in REQUIRED_SETUP_KEYS if not isinstance(setup.get(key), list) or not setup.get(key)]
    if missing:
        return blocked_item("setup_pages_read_only_inspected", [f"missing setup page proof: {', '.join(missing)}"])
    return ok_item("setup_pages_read_only_inspected", "runEvidence.setupPages", ",".join(REQUIRED_SETUP_KEYS))


def site_created_passed(run: dict[str, Any], require_created_site: bool) -> dict[str, Any]:
    site_creation = run.get("siteCreation")
    if not isinstance(site_creation, dict):
        return blocked_item("site_created_and_verified", ["runEvidence.siteCreation missing"])
    status = site_creation.get("status")
    if require_created_site:
        if status != "created_verified":
            return blocked_item(
                "site_created_and_verified",
                [f"siteCreation.status is {status!r}, expected 'created_verified' for from-scratch launch"],
            )
        missing = bools_true(site_creation, ["siteCardVerified", "backendVerified", "frontendVerified"])
        if missing:
            return blocked_item("site_created_and_verified", [f"siteCreation.{key} must be true" for key in missing])
        if not site_creation.get("createdSiteKey"):
            return blocked_item("site_created_and_verified", ["siteCreation.createdSiteKey missing"])
        return ok_item("site_created_and_verified", "runEvidence.siteCreation", "created_verified")
    if status in {"created_verified", "existing_site_selected"}:
        return ok_item("site_created_and_verified", "runEvidence.siteCreation", str(status))
    return blocked_item("site_created_and_verified", [f"unsupported siteCreation.status for launch acceptance: {status!r}"])


def frontend_static_passed(run: dict[str, Any]) -> dict[str, Any]:
    frontend = run.get("frontendRendering")
    if not isinstance(frontend, dict):
        return blocked_item("static_frontend_routes_render", ["runEvidence.frontendRendering missing"])
    missing = bools_true(frontend, ["checked", "markdownResidueChecked", "structuredRichTextChecked"])
    blockers = [f"frontendRendering.{key} must be true" for key in missing]
    if frontend.get("blockingIssues"):
        blockers.append("frontendRendering.blockingIssues must be empty")
    statuses = frontend.get("expectedStatuses")
    if not isinstance(statuses, dict) or statuses.get("/") != 200:
        blockers.append("frontendRendering.expectedStatuses must include / = 200")
    if blockers:
        return blocked_item("static_frontend_routes_render", blockers)
    return ok_item("static_frontend_routes_render", "runEvidence.frontendRendering")


def launch_readiness_passed(run: dict[str, Any]) -> dict[str, Any]:
    readiness = run.get("launchReadiness")
    if not isinstance(readiness, dict):
        return blocked_item("theme_route_launch_ready", ["runEvidence.launchReadiness missing"])
    required = (
        "checked",
        "themeActive",
        "pagesPublished",
        "pagesEnabled",
        "routesBound",
        "frontendHttpOk",
        "frontendDomVerified",
    )
    blockers = [f"launchReadiness.{key} must be true" for key in bools_true(readiness, required)]
    if readiness.get("blockingIssues"):
        blockers.append("launchReadiness.blockingIssues must be empty")
    if not readiness.get("checkedPaths"):
        blockers.append("launchReadiness.checkedPaths must be non-empty")
    if blockers:
        return blocked_item("theme_route_launch_ready", blockers)
    return ok_item("theme_route_launch_ready", "runEvidence.launchReadiness")


def request_capture_passed(run: dict[str, Any]) -> dict[str, Any]:
    capture = run.get("requestCapture")
    if not isinstance(capture, dict):
        return blocked_item("content_type_save_request_captured_and_persisted", ["runEvidence.requestCapture missing"])
    blockers: list[str] = []
    if capture.get("persistedVerified") is not True:
        blockers.append("requestCapture.persistedVerified must be true")
    for key in ("url", "method", "headers", "payloadShape", "contentBlockShape", "idFields", "mode", "publishBehavior"):
        if key not in capture:
            blockers.append(f"requestCapture.{key} missing")
    payload_shape = capture.get("payloadShape")
    if not non_empty_shape(payload_shape):
        blockers.append("requestCapture.payloadShape must be a non-empty object or redacted shape string")
    if blockers:
        return blocked_item("content_type_save_request_captured_and_persisted", blockers)
    return ok_item("content_type_save_request_captured_and_persisted", "runEvidence.requestCapture")


def sample_passed(run: dict[str, Any]) -> dict[str, Any]:
    sample = run.get("sampleVerification")
    if not isinstance(sample, dict):
        return blocked_item("sample_backend_frontend_verified", ["runEvidence.sampleVerification missing"])
    required = ("backendVerified", "frontendVerified", "titleOrNameVerified", "coverOrMediaVerified", "bodyVerified")
    blockers = [f"sampleVerification.{key} must be true" for key in bools_true(sample, required)]
    if sample.get("status") not in {"published", "已发布"}:
        blockers.append("sampleVerification.status must be published or 已发布")
    if not non_empty_render_audit(sample.get("renderAudit")):
        blockers.append("sampleVerification.renderAudit missing")
    if blockers:
        return blocked_item("sample_backend_frontend_verified", blockers)
    return ok_item("sample_backend_frontend_verified", "runEvidence.sampleVerification")


def upload_readiness_content_types(upload_readiness_items: list[Any]) -> set[str]:
    content_types: set[str] = set()
    for readiness in upload_readiness_items:
        if not isinstance(readiness, dict):
            continue
        manifests = readiness.get("manifests")
        if not isinstance(manifests, list):
            continue
        for manifest in manifests:
            if isinstance(manifest, dict) and manifest.get("contentType") in {"products", "posts"}:
                content_types.add(str(manifest["contentType"]))
    return content_types


def sample_evidence_items_passed(sample_evidence_items: list[Any], expected_content_types: set[str] | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    if not sample_evidence_items:
        return blocked_item("sample_backend_frontend_verified", ["at least one manifest sample evidence artifact is required"])
    content_types: set[str] = set()
    for index, sample in enumerate(sample_evidence_items, start=1):
        if not isinstance(sample, dict):
            blockers.append(f"sample evidence {index} root must be an object")
            continue
        content_type = sample.get("contentType")
        if content_type in {"products", "posts"}:
            content_types.add(content_type)
        else:
            blockers.append(f"sample evidence {index}.contentType must be products or posts")
        for key in ("backendVerified", "frontendVerified", "titleOrNameVerified", "bodyVerified", "stopConditionMet"):
            if sample.get(key) is not True:
                blockers.append(f"sample evidence {index}.{key} must be true")
        if sample.get("preMutationGate") != "passed":
            blockers.append(f"sample evidence {index}.preMutationGate must be passed")
        if sample.get("schemaGatePass") is not True:
            blockers.append(f"sample evidence {index}.schemaGatePass must be true")
        if sample.get("saveStatus") != "ok":
            blockers.append(f"sample evidence {index}.saveStatus must be ok")
        if sample.get("publishStatus") != "ok":
            blockers.append(f"sample evidence {index}.publishStatus must be ok")
        if not isinstance(sample.get("sampleSlug"), str) or not sample.get("sampleSlug", "").strip():
            blockers.append(f"sample evidence {index}.sampleSlug is required")
        if not isinstance(sample.get("frontendUrl"), str) or not sample.get("frontendUrl", "").strip():
            blockers.append(f"sample evidence {index}.frontendUrl is required")
        if not isinstance(sample.get("backendUrl"), str) or not sample.get("backendUrl", "").strip():
            blockers.append(f"sample evidence {index}.backendUrl is required")
        if not non_empty_render_audit(sample.get("renderAudit")):
            blockers.append(f"sample evidence {index}.renderAudit missing")
        blocking = sample.get("blockingIssues")
        if not isinstance(blocking, list):
            blockers.append(f"sample evidence {index}.blockingIssues must be an array")
        elif blocking:
            blockers.append(f"sample evidence {index}.blockingIssues must be empty")
    expected_content_types = expected_content_types or set()
    missing_types = sorted(expected_content_types - content_types)
    if missing_types:
        blockers.append("sample evidence missing required content types from upload readiness: " + ", ".join(missing_types))
    if blockers:
        return blocked_item("sample_backend_frontend_verified", blockers, "sampleEvidence")
    return ok_item("sample_backend_frontend_verified", "sampleEvidence", "contentTypes=" + ",".join(sorted(content_types)))


def cleanup_passed(run: dict[str, Any], cleanup_evidence: dict[str, Any] | None) -> dict[str, Any]:
    cleanup = cleanup_evidence if isinstance(cleanup_evidence, dict) else run.get("cleanup")
    if not isinstance(cleanup, dict):
        return blocked_item("probe_cleanup_completed", ["cleanup evidence missing"])
    if cleanup.get("status") not in {"completed", "cleaned", "verified"}:
        return blocked_item("probe_cleanup_completed", ["cleanup status must be completed, cleaned, or verified"])
    required = ("backendVerified", "frontendVerified")
    blockers = [f"cleanup.{key} must be true" for key in bools_true(cleanup, required)]
    if cleanup.get("cleanedCount") is None:
        blockers.append("cleanup.cleanedCount missing")
    cleaned_candidates = cleanup.get("cleanedCandidates")
    if not isinstance(cleaned_candidates, list):
        blockers.append("cleanup.cleanedCandidates must be an array")
    if cleaned_candidates == [] and cleanup.get("noCandidatesVerified") is not True:
        blockers.append("cleanup.noCandidatesVerified must be true when cleanedCandidates is empty")
    if cleaned_candidates == []:
        scans = cleanup.get("scannedSurfaces")
        if not isinstance(scans, list) or not scans:
            blockers.append("cleanup.scannedSurfaces must be non-empty when cleanedCandidates is empty")
    if blockers:
        return blocked_item("probe_cleanup_completed", blockers)
    return ok_item("probe_cleanup_completed", "cleanupEvidence" if cleanup_evidence else "runEvidence.cleanup")


def module_capture_passed(module_coverage: dict[str, Any] | None, stage_coverage: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(module_coverage, dict):
        if module_coverage.get("complete") is True and module_coverage.get("jsonReplayReady") is True:
            return ok_item("module_interface_capture_complete", "moduleCoverage", "complete and replay-ready")
        if module_coverage.get("uiFirst") is True and module_coverage.get("complete") is True:
            return ok_item("module_interface_capture_complete", "moduleCoverage", "complete UI-first coverage")
        return blocked_item(
            "module_interface_capture_complete",
            ["module coverage is present but not complete/replay-ready or explicitly UI-first complete"],
            "moduleCoverage",
        )
    if isinstance(stage_coverage, dict):
        module = stage_coverage.get("moduleInterfaceCapture")
        if isinstance(module, dict) and module.get("completionCovered") is True:
            return blocked_item(
                "module_interface_capture_complete",
                ["stage coverage is local rehearsal evidence only; provide real module coverage before launch acceptance"],
                "stageCoverage",
            )
    return blocked_item("module_interface_capture_complete", ["module capture coverage evidence missing"])


def upload_readiness_passed(upload_readiness: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(upload_readiness, dict):
        return blocked_item("manifest_schema_gate_passed", ["manifest upload readiness report missing"])
    if upload_readiness.get("overallStatus") != "ready_for_sample_upload":
        return blocked_item("manifest_schema_gate_passed", ["upload readiness overallStatus must be ready_for_sample_upload"])
    manifests = upload_readiness.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        return blocked_item("manifest_schema_gate_passed", ["upload readiness manifests must be non-empty"])
    blockers: list[str] = []
    for index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            blockers.append(f"manifest readiness {index} must be an object")
            continue
        if manifest.get("schemaVerified") is not True:
            blockers.append(f"manifest readiness {index}.schemaVerified must be true")
        schema_gate = manifest.get("schemaGate")
        if isinstance(schema_gate, dict) and schema_gate.get("ok") is not True:
            blockers.append(f"manifest readiness {index}.schemaGate.ok must be true")
        if manifest.get("status") != "ready_for_sample_upload":
            blockers.append(f"manifest readiness {index}.status must be ready_for_sample_upload")
    if blockers:
        return blocked_item("manifest_schema_gate_passed", blockers)
    return ok_item("manifest_schema_gate_passed", "uploadReadiness")


def upload_readiness_items_passed(upload_readiness_items: list[Any]) -> dict[str, Any]:
    if not upload_readiness_items:
        return blocked_item("manifest_schema_gate_passed", ["manifest upload readiness report missing"])
    blockers: list[str] = []
    manifest_count = 0
    for index, readiness in enumerate(upload_readiness_items):
        item = upload_readiness_passed(readiness if isinstance(readiness, dict) else None)
        if item["status"] != "passed":
            blockers.extend(f"upload readiness {index}: {blocker}" for blocker in item["blockers"])
        if isinstance(readiness, dict) and isinstance(readiness.get("manifests"), list):
            manifest_count += len(readiness["manifests"])
    if manifest_count == 0:
        blockers.append("combined upload readiness manifests must be non-empty")
    if blockers:
        return blocked_item("manifest_schema_gate_passed", blockers)
    return ok_item("manifest_schema_gate_passed", "uploadReadiness", f"reports={len(upload_readiness_items)} manifests={manifest_count}")


def batch_passed(
    batch_evidence: dict[str, Any] | None,
    batch_validations: list[Any],
    expected_content_types: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(batch_evidence, dict):
        return blocked_item("batch_upload_publish_verified", ["batch upload/publish evidence missing"])
    blockers = [f"batchEvidence.{key} must be true" for key in bools_true(batch_evidence, (
        "schemaGatePass",
        "sampleVerificationPass",
        "progressLogComplete",
        "frontendDetailAuditPass",
        "stopConditionMet",
    ))]
    if batch_evidence.get("preMutationGate") != "passed":
        blockers.append("batchEvidence.preMutationGate must be passed")
    if not batch_evidence.get("progressLog"):
        blockers.append("batchEvidence.progressLog must be non-empty")
    if not batch_validations:
        blockers.append("at least one batch validation report is required")
    content_types: set[str] = set()
    for index, batch_validation in enumerate(batch_validations, start=1):
        if not isinstance(batch_validation, dict):
            blockers.append(f"batch validation {index} root must be an object")
            continue
        content_type = batch_validation.get("contentType")
        if content_type in {"products", "posts"}:
            content_types.add(str(content_type))
        else:
            blockers.append(f"batch validation {index}.contentType must be products or posts")
        if batch_validation.get("valid") is not True:
            blockers.append(f"batch validation {index} report must be valid")
    expected_content_types = expected_content_types or set()
    missing_types = sorted(expected_content_types - content_types)
    if missing_types:
        blockers.append("batch validation missing required content types from upload readiness: " + ", ".join(missing_types))
    if blockers:
        return blocked_item("batch_upload_publish_verified", blockers)
    return ok_item(
        "batch_upload_publish_verified",
        "batchEvidence",
        f"validations={len(batch_validations)} contentTypes=" + ",".join(sorted(content_types)),
    )


def forms_media_settings_passed(forms_media_settings: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(forms_media_settings, dict):
        return blocked_item("forms_media_settings_verified_or_explicitly_out_of_scope", ["forms/media/settings evidence or deferral missing"])
    if forms_media_settings.get("status") == "explicitly_out_of_scope":
        decisions = forms_media_settings.get("deferrals")
        if isinstance(decisions, list) and decisions:
            return ok_item(
                "forms_media_settings_verified_or_explicitly_out_of_scope",
                "formsMediaSettings",
                "explicitly out of scope",
            )
        return blocked_item(
            "forms_media_settings_verified_or_explicitly_out_of_scope",
            ["explicit out-of-scope status requires non-empty deferrals"],
        )
    required = ("siteInfoVerified", "formsVerified", "mediaVerified", "domainsRecorded", "trackingRecorded")
    deferrals = forms_media_settings.get("deferrals")
    deferred_modules = set()
    if isinstance(deferrals, list):
        for decision in deferrals:
            if not isinstance(decision, dict):
                continue
            module = decision.get("module")
            reason = str(decision.get("reason", "")).strip()
            if isinstance(module, str) and module.strip() and reason:
                deferred_modules.add(module.strip())
    key_to_module = {
        "siteInfoVerified": "site-info",
        "formsVerified": "forms",
        "mediaVerified": "media",
        "domainsRecorded": "domains",
        "trackingRecorded": "tracking",
    }
    blockers = [
        f"formsMediaSettings.{key} must be true or explicitly deferred"
        for key in bools_true(forms_media_settings, required)
        if key_to_module[key] not in deferred_modules
    ]
    if blockers:
        return blocked_item("forms_media_settings_verified_or_explicitly_out_of_scope", blockers)
    details = "mixed verified/deferred" if deferred_modules else ""
    return ok_item("forms_media_settings_verified_or_explicitly_out_of_scope", "formsMediaSettings", details)


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


def final_frontend_direct_blockers(final_audit: dict[str, Any], final_audit_path: str = "") -> list[str]:
    blockers: list[str] = []
    validation = validate_browser_stage_result(final_audit)
    for issue in validation.get("issues", []):
        blockers.append(f"final frontend audit result must pass validate_browser_stage_result.py: {issue}")
    if final_audit.get("stageId") != "final_frontend_audit":
        blockers.append("final frontend audit result stageId must be final_frontend_audit")

    audit_report_path = final_frontend_pointer(final_audit, "auditReport")
    if not audit_report_path:
        pointers = final_audit.get("redactedEvidencePointers")
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
        where = f" in {final_audit_path}" if final_audit_path else ""
        blockers.append(
            "final frontend audit must point to the redacted audit report JSON with auditReport "
            f"or a single JSON redactedEvidencePointer{where}"
        )
        return blockers

    try:
        reports = load_reports(Path(audit_report_path).expanduser())
    except ValueError as exc:
        blockers.append(str(exc))
        return blockers

    summary_data = None
    summary_path = final_frontend_pointer(final_audit, "auditInputsSummary")
    if summary_path:
        summary_data = load_json(summary_path, "final frontend audit inputs summary")
        if summary_data is not None and not isinstance(summary_data, dict):
            blockers.append("final frontend audit inputs summary must be a JSON object")
            summary_data = None

    expected_statuses = None
    expected_path = final_frontend_pointer(final_audit, "expectedStatuses")
    if expected_path:
        try:
            loaded_statuses = load_json_any(Path(expected_path).expanduser(), "final frontend expected statuses")
        except ValueError as exc:
            blockers.append(str(exc))
            loaded_statuses = None
        if isinstance(loaded_statuses, dict):
            expected_statuses = loaded_statuses
        elif loaded_statuses is not None:
            blockers.append("final frontend expected statuses must be a JSON object")

    _proof, report_blockers = summarize_reports(reports, fail_on_warn=bool(final_audit.get("failOnWarn")))
    blockers.extend(report_blockers)
    blockers.extend(validate_expected_coverage(reports, summary_data, expected_statuses))
    return blockers


def final_frontend_passed(final_audit: dict[str, Any] | None, final_audit_path: str = "") -> dict[str, Any]:
    if not isinstance(final_audit, dict):
        return blocked_item("final_frontend_audit_passed", ["final frontend audit stage result missing"])
    status = final_audit.get("status")
    blockers = []
    if status not in {"completed", "passed"}:
        blockers.append("final frontend audit status must be completed or passed")
    proof = final_audit.get("proof")
    if not isinstance(proof, list) or not proof:
        blockers.append("final frontend audit proof must be non-empty")
    if final_audit.get("blockers"):
        blockers.append("final frontend audit blockers must be empty")
    blockers.extend(final_frontend_direct_blockers(final_audit, final_audit_path))
    if blockers:
        return blocked_item("final_frontend_audit_passed", blockers)
    return ok_item("final_frontend_audit_passed", "finalFrontendAudit")


def sedimentation_passed(closeout: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(closeout, dict):
        return blocked_item("skill_sedimentation_completed_or_readonly_exception_recorded", ["round closeout evidence missing"])
    blockers = []
    if closeout.get("valid") is not True:
        blockers.append("round closeout must have valid=true")
    if closeout.get("kind") == "allincms_round_maintenance_summary":
        blockers.append("maintenance closeout cannot prove launch completion")
    if closeout.get("complete") is not True:
        blockers.append("launch closeout must have complete=true")
    completion_gaps = closeout.get("completionGaps")
    if isinstance(completion_gaps, list) and completion_gaps:
        blockers.append("launch closeout completionGaps must be empty")
    if closeout.get("localOnly") is True and closeout.get("remoteMutationsPerformed") is False:
        blockers.append("launch closeout cannot be local-only maintenance evidence")
    proof = closeout.get("proof") or closeout.get("proven")
    if not isinstance(proof, list) or not proof:
        blockers.append("launch closeout proof must be non-empty")
    else:
        proof_text = " ".join(str(item).lower() for item in proof)
        missing_terms = [term for term in ("launch", "frontend", "cleanup") if term not in proof_text]
        if missing_terms:
            blockers.append("launch closeout proof must mention: " + ", ".join(missing_terms))
    sedimentation = closeout.get("sedimentation")
    if isinstance(sedimentation, dict):
        status = sedimentation.get("status") or sedimentation.get("sedimentation")
    else:
        status = closeout.get("sedimentation")
    if status not in {"updated", "none", "read-only-deferred"}:
        blockers.append("round closeout sedimentation must be updated, none, or read-only-deferred")
    if not blockers:
        return ok_item("skill_sedimentation_completed_or_readonly_exception_recorded", "roundCloseout", str(status))
    return blocked_item(
        "skill_sedimentation_completed_or_readonly_exception_recorded",
        blockers,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    run = load_json(args.run_evidence, "run evidence")
    if not isinstance(run, dict):
        raise SystemExit("ERROR: run evidence root must be an object")

    module_coverage = load_json(args.module_coverage, "module coverage")
    stage_coverage = load_json(args.stage_coverage, "stage coverage")
    upload_readiness_items = load_json_items(args.upload_readiness, "upload readiness")
    sample_evidence_items = load_json_items(args.sample_evidence, "sample evidence")
    expected_sample_types = upload_readiness_content_types(upload_readiness_items)
    batch_evidence = load_json(args.batch_evidence, "batch evidence")
    batch_validations = load_json_items(args.batch_validation, "batch validation")
    forms_media_settings = load_json(args.forms_media_settings, "forms/media/settings evidence")
    final_frontend_audit = load_json(args.final_frontend_audit, "final frontend audit")
    cleanup_evidence = load_json(args.cleanup_evidence, "cleanup evidence")
    closeout = load_json(args.round_closeout, "round closeout")

    run_errors = validate_run_evidence(run)
    items = [
        site_created_passed(run, args.require_created_site),
        setup_passed(run),
        module_capture_passed(module_coverage if isinstance(module_coverage, dict) else None, stage_coverage if isinstance(stage_coverage, dict) else None),
        launch_readiness_passed(run),
        frontend_static_passed(run),
        request_capture_passed(run),
        sample_evidence_items_passed(sample_evidence_items, expected_sample_types),
        upload_readiness_items_passed(upload_readiness_items),
        batch_passed(batch_evidence if isinstance(batch_evidence, dict) else None, batch_validations, expected_sample_types),
        forms_media_settings_passed(forms_media_settings if isinstance(forms_media_settings, dict) else None),
        final_frontend_passed(
            final_frontend_audit if isinstance(final_frontend_audit, dict) else None,
            args.final_frontend_audit,
        ),
        cleanup_passed(run, cleanup_evidence if isinstance(cleanup_evidence, dict) else None),
        sedimentation_passed(closeout if isinstance(closeout, dict) else None),
    ]
    if run_errors:
        items.insert(0, blocked_item("run_evidence_valid", run_errors, "runEvidence"))
    else:
        items.insert(0, ok_item("run_evidence_valid", "runEvidence"))

    passed = [item["key"] for item in items if item["status"] == "passed"]
    blocked = [item for item in items if item["status"] != "passed"]
    return {
        "kind": "allincms_launch_acceptance_validation",
        "generatedAt": now_iso(),
        "valid": not blocked,
        "complete": not blocked,
        "requireCreatedSite": args.require_created_site,
        "runEvidence": args.run_evidence,
        "sampleEvidenceCount": len(sample_evidence_items),
        "batchValidationCount": len(batch_validations),
        "checkedAcceptanceKeys": list(REQUIRED_ACCEPTANCE_KEYS),
        "passed": passed,
        "blocked": blocked,
        "items": items,
        "rule": "Local rehearsals and stage coverage are not live launch proof; every acceptance item needs real redacted evidence or explicit deferral where allowed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AllinCMS from-scratch launch acceptance evidence.")
    parser.add_argument("--run-evidence", required=True)
    parser.add_argument("--module-coverage", default="")
    parser.add_argument("--stage-coverage", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", action="append", default=[])
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--final-frontend-audit", default="")
    parser.add_argument("--cleanup-evidence", default="")
    parser.add_argument("--round-closeout", default="")
    parser.add_argument("--require-created-site", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["valid"]:
        print("Launch acceptance validation passed.")
    else:
        print("Launch acceptance validation failed:")
        for item in report["blocked"]:
            print(f"- {item['key']}: {'; '.join(item['blockers'])}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
