#!/usr/bin/env python3
"""Focused regression tests for validate_run_evidence.py."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import inspect
import json
import sys
import tempfile
import time
from pathlib import Path

from make_created_site_evidence import parse_module_routes, upgrade_evidence
from make_create_preflight_evidence import build_evidence, parse_observed_fields, parse_site_key_evidence, parse_site_keys
from make_create_preflight_from_existing_site_evidence import build_from_existing as build_create_preflight_from_existing
from validate_run_evidence import validate
import audit_skill_hygiene
import audit_frontend_rendering
from make_existing_site_readonly_evidence import build_evidence as build_existing_site_evidence
from make_existing_site_readonly_evidence import load_frontend_rendering
from make_existing_site_readonly_evidence import load_launch_readiness as load_existing_site_launch_readiness
from make_existing_site_evidence_from_scan import build_args as build_existing_site_args_from_scan
from make_frontend_rendering_evidence import build_evidence as build_frontend_rendering_evidence
from make_launch_readiness_evidence import build_evidence as build_launch_readiness_evidence
from make_launch_readiness_evidence import parse_blocking_issues, parse_checked_paths
from make_launch_audit_inputs import build_url, normalize_base_url, parse_paths
from make_final_frontend_audit_inputs import (
    build_inputs as build_final_frontend_audit_inputs,
    load_manifest as load_final_audit_manifest,
    progress_entries as final_audit_progress_entries,
    validate_progress_complete as validate_final_audit_progress_complete,
)
from make_final_frontend_audit_stage_result import build_result as build_final_frontend_audit_stage_result
from make_final_frontend_audit_stage_result import url_fingerprint as final_audit_url_fingerprint
from merge_probe_evidence import merge as merge_probe_evidence
from merge_probe_evidence import merge_from_save_capture_evidence
from merge_probe_evidence import merge_from_publish_sample_evidence
from merge_probe_evidence import merge_from_cleanup_evidence
from redact_browser_scan import redact_scan
from check_round_closeout import validate_closeout
from make_authorization_record import build_record as build_authorization_record, validate_record as validate_authorization_record
from check_pre_mutation_gate import (
    validate_batch_gate,
    validate_cleanup_probe_gate,
    validate_create_site_gate,
    validate_probe_gate,
    validate_publish_probe_gate,
    validate_save_probe_gate,
    validate_existing_content_gate,
    validate_site_action_gate,
)
from apply_browser_stage_result import apply_stage_result, build_stage_result, validate_browser_stage_result
from summarize_module_scan import summarize as summarize_module_scan
from summarize_module_scan import module_items_from_object
from summarize_module_scan import validate_redaction as validate_module_scan_redaction
from plan_module_capture import build_plan as build_module_capture_plan
from prepare_capture_authorization import build_package as build_capture_authorization_package
from prepare_capture_authorization import AUTHORIZATION_SOURCE_PLACEHOLDER
from prepare_capture_authorization import select_stage as select_capture_stage
from prepare_all_capture_authorizations import build_package_set as build_all_capture_authorization_packages
from validate_all_capture_authorizations import validate_package_set as validate_all_capture_authorization_packages
from validate_capture_authorization_package import validate_package as validate_capture_authorization_package
from summarize_run_status import summarize as summarize_run_status
from validate_manifest import validate_manifest
from make_manifest_upload_readiness import build_report as build_manifest_upload_readiness_report
from make_source_input_requirements import build_report as build_source_input_requirements_report
import simulate_manifest_rehearsal
from validate_manifest_rehearsal import validate_rehearsal as validate_manifest_rehearsal_summary
import simulate_site_creation_chain
import simulate_probe_lifecycle
import simulate_full_e2e_chain
import run_full_rehearsal
from build_browser_execution_ledger import build_browser_execution_ledger, validate_browser_execution_ledger
from branch_existing_site_ledger import branch_ledger as branch_existing_site_ledger
from build_browser_execution_plan import build_browser_execution_plan, validate_browser_execution_plan
from build_browser_stage_packet import build_browser_stage_packet, validate_browser_stage_packet
from make_browser_stage_result import build_from_packet as build_browser_stage_result_from_packet
from prepare_browser_stage_evidence_bundle import prepare_bundle as prepare_browser_stage_evidence_bundle
from validate_browser_stage_evidence_bundle import validate_bundle as validate_browser_stage_evidence_bundle
from make_browser_runbook_summary import build_runbook_summary
from make_browser_runbook_summary import ledger_expected_stage_result_path
from validate_browser_runbook_summary import validate_runbook as validate_browser_runbook_summary
from summarize_rehearsal_stage_coverage import (
    build_summary as build_rehearsal_stage_coverage_summary,
    validate_summary as validate_rehearsal_stage_coverage_summary,
)
from prepare_browser_stage_authorization import build_package as build_browser_stage_authorization_package
from validate_browser_stage_authorization_package import validate_package as validate_browser_stage_authorization_package
from make_next_browser_action_handoff import build_handoff as build_next_browser_action_handoff
from validate_next_browser_action_handoff import validate_handoff as validate_next_browser_action_handoff
from make_handoff_readiness import build_report as build_handoff_readiness_report
from make_browser_stage_authorization_readiness import build_report as build_browser_stage_authorization_readiness_report
from make_browser_stage_queue import build_queue as build_browser_stage_queue
from make_browser_stage_queue import validate_queue as validate_browser_stage_queue
from make_browser_stage_queue_from_summary import build_queue_from_summary as build_browser_stage_queue_from_summary
from make_e2e_gap_audit import build_audit as build_e2e_gap_audit
from make_e2e_gap_audit import validate_audit as validate_e2e_gap_audit
from prepare_probe_save_handoff import build_handoff as build_probe_save_handoff
from prepare_probe_save_handoff import validate_handoff as validate_probe_save_handoff
from prepare_existing_probe_save_handoff import build_handoff as build_existing_probe_save_handoff
from prepare_existing_probe_save_handoff import validate_handoff as validate_existing_probe_save_handoff
from build_probe_save_runbook import build_runbook as build_probe_save_runbook
from build_probe_save_runbook import validate_runbook as validate_probe_save_runbook
from prepare_probe_save_evidence_bundle import build_bundle as build_probe_save_evidence_bundle
from prepare_probe_save_evidence_bundle import validate_bundle as validate_probe_save_evidence_bundle
from validate_probe_save_runbook import build_report as build_probe_save_runbook_validation_report
from validate_probe_save_capture_evidence import validate_capture_evidence as validate_probe_save_capture_evidence
from build_probe_publish_runbook import build_runbook as build_probe_publish_runbook
from build_probe_publish_runbook import validate_runbook as validate_probe_publish_runbook
from validate_probe_publish_sample_evidence import (
    validate_publish_sample_evidence as validate_probe_publish_sample_evidence,
)
from build_probe_cleanup_runbook import build_runbook as build_probe_cleanup_runbook
from build_probe_cleanup_runbook import validate_runbook as validate_probe_cleanup_runbook
from prepare_existing_probe_cleanup_handoff import build_handoff as build_existing_probe_cleanup_handoff
from prepare_existing_probe_cleanup_handoff import validate_handoff as validate_existing_probe_cleanup_handoff
from build_existing_probe_cleanup_runbook import (
    build_runbook as build_existing_probe_cleanup_runbook,
    validate_runbook as validate_existing_probe_cleanup_runbook,
)
from validate_probe_cleanup_evidence import validate_cleanup_evidence as validate_probe_cleanup_evidence
from build_theme_page_create_runbook import build_runbook as build_theme_page_create_runbook
from build_theme_page_create_runbook import validate_runbook as validate_theme_page_create_runbook
from validate_theme_page_create_evidence import validate_evidence as validate_theme_page_create_evidence
from build_batch_upload_publish_runbook import (
    build_runbook as build_batch_upload_publish_runbook,
    validate_runbook as validate_batch_upload_publish_runbook,
)
from validate_batch_upload_publish_evidence import validate_batch_evidence as validate_batch_upload_publish_evidence
from validate_launch_acceptance import build_report as build_launch_acceptance_report
from prepare_next_action_authorization import build_package as build_next_action_authorization_package
from prepare_next_action_authorization import select_detail as select_next_action_authorization_detail
from prepare_next_action_authorization import validate_package as validate_next_action_authorization_package
from build_launch_plan import build_launch_plan, validate_launch_plan
from validate_full_rehearsal import validate_rehearsal
from validate_full_e2e_simulation import validate_directory as validate_full_e2e_directory
from make_capture_handoff import build_handoff as build_capture_handoff
from validate_capture_handoff import validate_handoff as validate_capture_handoff
from validate_capture_plan_gate_coverage import validate_plan_gate_coverage
from update_module_capture_coverage import (
    build_capture_result,
    sync_ledger_with_coverage,
    update_coverage,
    validate_capture_result,
    validate_coverage,
)
from make_round_maintenance_summary import build_summary as build_round_maintenance_summary
from merge_created_site_readonly_refresh import merge_evidence as merge_created_site_readonly_refresh
from validate_action_replay_contract import validate_contract as validate_action_replay_contract
from apply_action_replay_contracts import apply_contracts as apply_action_replay_contracts
import record_source_input_gap

RECENT_PREFLIGHT_AT = "2026-06-29T12:00:00+00:00"
RECENT_AUTHORIZATION_AT = "2026-06-29T12:05:00+00:00"
GATE_NOW = datetime(2026, 6, 29, 12, 10, tzinfo=timezone.utc)
STALE_AT = "2026-06-29T10:00:00+00:00"


def complete_test_browser_stage_packet(packet: dict) -> dict:
    expectation = packet.get("remoteMutationExpectation")
    if expectation not in {"must", "may", "must_not"}:
        if packet.get("mode") == "requires_authorization":
            expectation = "must" if packet.get("stageId") == "create_site_submit" else "may"
        else:
            expectation = "must_not"
        packet["remoteMutationExpectation"] = expectation
    capture = packet.get("evidenceCaptureTemplate")
    if isinstance(capture, dict) and "browserStageMutatedRemote" not in capture:
        capture["browserStageMutatedRemote"] = expectation == "must"
    return packet


def base_evidence() -> dict:
    site_key = "mysite01"
    return {
        "completionClaimed": False,
        "mode": "read_only_simulation",
        "workspaceUrl": "https://workspace.laicms.com",
        "siteListUrl": "https://workspace.laicms.com/sites",
        "siteCreation": {
            "status": "simulated_not_submitted",
            "createSiteFields": [
                "input name: name, placeholder: 站点名称",
                "textarea name: description, placeholder: 站点简介",
            ],
        },
        "siteIdentity": {
            "siteKey": site_key,
            "backendDashboardUrl": f"https://workspace.laicms.com/{site_key}/dashboard",
            "frontendBaseUrl": f"https://{site_key}.web.allincms.com",
            "moduleRoutes": [
                f"/{site_key}/dashboard",
                f"/{site_key}/products",
                f"/{site_key}/posts",
                f"/{site_key}/media",
                f"/{site_key}/themes",
                f"/{site_key}/routes",
                f"/{site_key}/forms",
                f"/{site_key}/site-info",
                f"/{site_key}/tracking",
                f"/{site_key}/domains",
            ],
        },
        "setupPages": {
            "siteInfo": ["name, description, notificationEmail, save"],
            "domains": ["CNAME copy, domain input, add domain"],
            "media": ["upload controls, asset grid, public URL hints"],
            "themes": ["search themes, create theme, page/design/preview"],
            "routes": ["path, bound page, status, notes, updated time"],
            "forms": ["name, slug, description, fields, status, updated time"],
            "tracking": ["Google Tag ID input and add action"],
        },
        "contentInspection": {
            "contentType": "products",
            "listColumns": ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
            "editFields": [
                "name input",
                "slug input",
                "category control",
                "tag control",
                "description textarea",
                "order control",
                "main media control",
                "gallery control",
                "body editor",
                "publish/update controls",
            ],
        },
        "cleanup": {
            "status": "not_needed",
            "candidates": [],
        },
        "localChecks": {
            "skillHygienePassed": True,
            "quickValidatePassed": True,
            "repoCheckPassed": False,
            "repoCheckNote": "Repository-wide check failed on unrelated source backlink outside this skill.",
        },
    }


def assert_valid(data: dict) -> None:
    errors = validate(data)
    assert not errors, "\n".join(errors)


def assert_invalid_contains(data: dict, expected: str) -> None:
    errors = validate(data)
    assert any(expected in error for error in errors), "\n".join(errors)


def recent_base_evidence() -> dict:
    data = base_evidence()
    data["generatedAt"] = RECENT_PREFLIGHT_AT
    return data


def observed_create_fields() -> list[str]:
    return [
        "button: create site entry 创建站点",
        "dialog title: 创建站点",
        "input name: name, placeholder: 站点名称",
        "textarea name: description, placeholder: 站点简介",
        "submit button: 创建",
        "close button: Close",
    ]


def strong_site_key_evidence() -> dict[str, str]:
    return {
        "mysite01": "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard",
        "mysite02": "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard",
    }


def created_site_evidence() -> dict:
    site_key = "codex-test-site"
    data = base_evidence()
    data["generatedAt"] = RECENT_AUTHORIZATION_AT
    data["preflightGeneratedAt"] = RECENT_PREFLIGHT_AT
    data["mode"] = "site_creation"
    data["completionClaimed"] = False
    data["siteCreation"] = {
        "status": "created_verified",
        "existingSiteKeysBeforeCreate": ["mysite01", "mysite02"],
        "createdSiteKey": site_key,
        "siteCardVerified": True,
        "backendVerified": True,
        "frontendVerified": True,
        "siteCardEvidence": f"site list shows {site_key} card and enter-backend control",
        "backendEvidence": f"new dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        "frontendEvidence": f"default frontend opens at https://{site_key}.web.allincms.com",
        "submittedFieldKeys": ["name", "description"],
        "submittedValues": {
            "name": "Example Demo",
            "description": "Example demo site for source-backed product publishing and article planning.",
        },
        "createSiteFields": [
            "input name: name, placeholder: 站点名称",
            "textarea name: description, placeholder: 站点简介",
        ],
    }
    data["siteIdentity"] = {
        "siteKey": site_key,
        "backendDashboardUrl": f"https://workspace.laicms.com/{site_key}/dashboard",
        "frontendBaseUrl": f"https://{site_key}.web.allincms.com",
        "moduleRoutes": [
            f"/{site_key}/dashboard",
            f"/{site_key}/products",
            f"/{site_key}/posts",
            f"/{site_key}/media",
            f"/{site_key}/themes",
            f"/{site_key}/routes",
            f"/{site_key}/forms",
            f"/{site_key}/site-info",
            f"/{site_key}/tracking",
            f"/{site_key}/domains",
        ],
    }
    data["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": "create site",
        "target": "https://workspace.laicms.com/sites",
        "authorizationSource": "current user instruction",
        "verificationPlan": "verify site card, backend dashboard, and default frontend",
    }
    data["localChecks"]["repoCheckPassed"] = True
    data["localChecks"].pop("repoCheckNote", None)
    return data


def observed_module_routes(site_key: str) -> list[str]:
    return [
        f"/{site_key}/dashboard",
        f"/{site_key}/products",
        f"/{site_key}/posts",
        f"/{site_key}/media",
        f"/{site_key}/themes",
        f"/{site_key}/routes",
        f"/{site_key}/forms",
        f"/{site_key}/site-info",
        f"/{site_key}/tracking",
        f"/{site_key}/domains",
    ]


def create_preflight_evidence() -> dict:
    data = base_evidence()
    data["generatedAt"] = RECENT_PREFLIGHT_AT
    data["siteCreation"] = {
        "status": "create_preflight_verified",
        "existingSiteKeysBeforeCreate": ["mysite01", "mysite02"],
        "dialogClosedVerified": True,
        "createSiteFields": [
            "button: 创建站点",
            "dialog title: 创建站点",
            "input name: name, placeholder: 站点名称",
            "textarea name: description, placeholder: 站点简介",
            "submit button: 创建",
            "close button: Close",
        ],
        "siteKeyEvidence": strong_site_key_evidence(),
    }
    data.pop("siteIdentity")
    data.pop("setupPages")
    data.pop("contentInspection")
    return data


def existing_site_selected_evidence() -> dict:
    data = base_evidence()
    data["siteCreation"] = {
        "status": "existing_site_selected",
        "existingSiteKeysBeforeCreate": ["mysite01", "mysite02"],
        "siteKeyEvidence": {
            "mysite01": "backend route href observed for site key mysite01",
            "mysite02": "backend route href observed for site key mysite02",
        },
        "selectedSiteEvidence": (
            "backend dashboard route verified for selected site key mysite01: "
            "https://workspace.laicms.com/mysite01/dashboard"
        ),
        "dialogClosedVerified": True,
        "createSiteFields": observed_create_fields(),
    }
    return data


def test_phase_evidence_allows_repo_check_failure_with_note() -> None:
    assert_valid(base_evidence())


def test_completion_claim_requires_repo_check_passed() -> None:
    data = base_evidence()
    data["completionClaimed"] = True
    assert_invalid_contains(data, "repoCheckPassed")


def test_completion_claim_rejects_local_only_simulation() -> None:
    data = base_evidence()
    data["completionClaimed"] = True
    data["localOnly"] = True
    data["simulationOnly"] = True
    data["remoteMutationsPerformed"] = False
    data["localChecks"]["repoCheckPassed"] = True
    data["localChecks"].pop("repoCheckNote", None)
    assert_invalid_contains(data, "local-only or simulation-only")


def test_local_only_simulation_requires_no_remote_mutations() -> None:
    data = base_evidence()
    data["localOnly"] = True
    data["simulationOnly"] = True
    data["remoteMutationsPerformed"] = True
    assert_invalid_contains(data, "remoteMutationsPerformed")


def test_repo_check_failure_requires_note_when_not_complete() -> None:
    data = copy.deepcopy(base_evidence())
    data["localChecks"].pop("repoCheckNote")
    assert_invalid_contains(data, "repoCheckNote")


def test_created_site_evidence_requires_new_site_key() -> None:
    assert_valid(created_site_evidence())


def test_merge_created_site_readonly_refresh_adds_tracking_setup() -> None:
    created = created_site_evidence()
    created["setupPages"].pop("tracking")
    refresh = existing_site_selected_evidence()
    refresh["siteIdentity"]["siteKey"] = created["siteIdentity"]["siteKey"]
    refresh["siteIdentity"]["backendDashboardUrl"] = created["siteIdentity"]["backendDashboardUrl"]
    refresh["siteIdentity"]["frontendBaseUrl"] = created["siteIdentity"]["frontendBaseUrl"]
    refresh["siteIdentity"]["moduleRoutes"] = list(created["siteIdentity"]["moduleRoutes"])
    refresh["setupPages"]["tracking"] = ["tracking read-only inspected: add Google Tag ID visible"]

    merged = merge_created_site_readonly_refresh(created, refresh, Path("/tmp/refresh-evidence.json"))
    assert merged["siteCreation"]["status"] == "created_verified"
    assert merged["generatedAt"] == created["generatedAt"]
    assert merged["setupPages"]["tracking"] == refresh["setupPages"]["tracking"]
    assert "readOnlyRefreshMerged" in merged["localChecks"]
    assert_valid(merged)


def test_merge_created_site_readonly_refresh_rejects_wrong_site() -> None:
    created = created_site_evidence()
    refresh = existing_site_selected_evidence()
    refresh["siteIdentity"]["siteKey"] = "othersite"
    try:
        merge_created_site_readonly_refresh(created, refresh, Path("/tmp/refresh-evidence.json"))
    except ValueError as exc:
        assert "siteKey must match" in str(exc)
    else:
        raise AssertionError("merge accepted refresh evidence for another site")


def test_created_site_rejects_read_only_mode() -> None:
    data = created_site_evidence()
    data["mode"] = "read_only_simulation"
    assert_invalid_contains(data, "site_creation")


def test_created_site_rejects_missing_before_create_keys() -> None:
    data = created_site_evidence()
    data["siteCreation"].pop("existingSiteKeysBeforeCreate")
    assert_invalid_contains(data, "existingSiteKeysBeforeCreate")


def test_created_site_rejects_existing_key_reuse() -> None:
    data = created_site_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"].append(data["siteCreation"]["createdSiteKey"])
    assert_invalid_contains(data, "must not already exist")


def test_created_site_rejects_invalid_before_create_key() -> None:
    data = created_site_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"].append("Invalid Site Key")
    assert_invalid_contains(data, "existingSiteKeysBeforeCreate")


def test_created_site_rejects_site_card_evidence_without_site_key() -> None:
    data = created_site_evidence()
    data["siteCreation"]["siteCardEvidence"] = "site list shows the new site card and enter-backend control"
    assert_invalid_contains(data, "siteCreation.siteCardEvidence")


def test_created_site_rejects_backend_evidence_for_old_site() -> None:
    data = created_site_evidence()
    data["siteCreation"]["backendEvidence"] = "new dashboard opens at https://workspace.laicms.com/mysite01/dashboard"
    assert_invalid_contains(data, "siteCreation.backendEvidence")


def test_created_site_rejects_frontend_evidence_for_old_site() -> None:
    data = created_site_evidence()
    data["siteCreation"]["frontendEvidence"] = "default frontend opens at https://mysite01.web.allincms.com"
    assert_invalid_contains(data, "siteCreation.frontendEvidence")


def test_created_site_requires_new_site_context() -> None:
    data = created_site_evidence()
    data.pop("siteIdentity")
    data.pop("setupPages")
    data.pop("contentInspection")
    assert_invalid_contains(data, "siteIdentity")


def test_create_preflight_evidence_requires_before_create_keys() -> None:
    assert_valid(create_preflight_evidence())


def test_create_preflight_allows_empty_before_create_keys() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"] = []
    data["siteCreation"].pop("siteKeyEvidence")
    data["siteCreation"]["emptySiteListEvidence"] = "verified empty /sites list"
    assert_valid(data)


def test_create_preflight_rejects_missing_before_create_keys() -> None:
    data = create_preflight_evidence()
    data["siteCreation"].pop("existingSiteKeysBeforeCreate")
    assert_invalid_contains(data, "existingSiteKeysBeforeCreate")


def test_create_preflight_rejects_created_site_key() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["createdSiteKey"] = "codex-test-site"
    assert_invalid_contains(data, "must not be set before submitting")


def test_create_preflight_rejects_missing_site_key_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"].pop("siteKeyEvidence")
    assert_invalid_contains(data, "siteCreation.siteKeyEvidence")


def test_create_preflight_rejects_weak_site_key_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["siteKeyEvidence"] = {
        "mysite01": "mysite01 from page text body regex",
        "mysite02": "mysite02 from page text body regex",
    }
    assert_invalid_contains(data, "must not rely on memory")


def test_create_preflight_accepts_scoped_site_card_frontend_domain_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["siteKeyEvidence"] = {
        "mysite01": "mysite01 shown as /sites card frontend domain mysite01.web.allincms.com",
        "mysite02": "mysite02 shown as /sites card frontend domain mysite02.web.allincms.com",
    }
    assert_valid(data)


def test_create_preflight_rejects_mismatched_site_key_evidence_keys() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["siteKeyEvidence"] = {
        "mysite01": strong_site_key_evidence()["mysite01"],
    }
    assert_invalid_contains(data, "keys must exactly match")


def test_create_preflight_rejects_site_key_evidence_without_site_key() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["siteKeyEvidence"] = {
        "mysite01": "observed from backend url route https://workspace.laicms.com/dashboard",
        "mysite02": strong_site_key_evidence()["mysite02"],
    }
    assert_invalid_contains(data, "must mention the site key")


def test_create_preflight_rejects_empty_list_without_empty_site_list_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"] = []
    data["siteCreation"].pop("siteKeyEvidence")
    assert_invalid_contains(data, "emptySiteListEvidence")


def test_create_preflight_rejects_empty_list_evidence_without_empty_claim() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"] = []
    data["siteCreation"].pop("siteKeyEvidence")
    data["siteCreation"]["emptySiteListEvidence"] = "site cards inspected"
    assert_invalid_contains(data, "verified empty")


def test_create_preflight_requires_dialog_closed_verification() -> None:
    data = create_preflight_evidence()
    data["siteCreation"].pop("dialogClosedVerified")
    assert_invalid_contains(data, "dialogClosedVerified")


def test_create_preflight_requires_create_site_entry_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["createSiteFields"] = [
        "dialog title: 创建站点",
        "input name: name, placeholder: 站点名称",
        "textarea name: description, placeholder: 站点简介",
        "submit button: 创建",
        "close button: Close",
    ]
    assert_invalid_contains(data, "observed create-site-entry")


def test_create_preflight_requires_close_control_evidence() -> None:
    data = create_preflight_evidence()
    data["siteCreation"]["createSiteFields"] = [
        "button: 创建站点",
        "dialog title: 创建站点",
        "input name: name, placeholder: 站点名称",
        "textarea name: description, placeholder: 站点简介",
        "submit button: 创建",
    ]
    assert_invalid_contains(data, "observed close")


def test_existing_site_selected_requires_site_key_in_site_list() -> None:
    assert_valid(existing_site_selected_evidence())


def test_existing_site_selected_rejects_missing_site_list() -> None:
    data = existing_site_selected_evidence()
    data["siteCreation"].pop("existingSiteKeysBeforeCreate")
    assert_invalid_contains(data, "existingSiteKeysBeforeCreate")


def test_existing_site_selected_rejects_unlisted_site_key() -> None:
    data = existing_site_selected_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"] = ["mysite02"]
    assert_invalid_contains(data, "must be present in siteCreation.existingSiteKeysBeforeCreate")


def test_existing_site_selected_rejects_full_page_regex_site_key_noise() -> None:
    data = existing_site_selected_evidence()
    data["siteCreation"]["existingSiteKeysBeforeCreate"] = [
        "mysite01",
        *[f"{index:02d}abcdefghi" for index in range(21)],
    ]
    assert_invalid_contains(data, "too many keys")


def test_existing_site_selected_does_not_require_create_dialog_fields() -> None:
    data = existing_site_selected_evidence()
    data["siteCreation"].pop("createSiteFields")
    data["siteCreation"].pop("dialogClosedVerified")
    assert_valid(data)


def test_existing_site_selected_requires_selected_site_evidence() -> None:
    data = existing_site_selected_evidence()
    data["siteCreation"].pop("selectedSiteEvidence")
    assert_invalid_contains(data, "selectedSiteEvidence")


def test_completion_claim_requires_site_context() -> None:
    data = create_preflight_evidence()
    data["completionClaimed"] = True
    data["localChecks"]["repoCheckPassed"] = True
    data["localChecks"].pop("repoCheckNote", None)
    assert_invalid_contains(data, "siteIdentity")


def test_preflight_builder_outputs_valid_evidence() -> None:
    site_keys = parse_site_keys("mysite01,mysite02,mysite01")
    assert site_keys == ["mysite01", "mysite02"]
    fields = parse_observed_fields(";".join(observed_create_fields()))
    assert fields == observed_create_fields()
    assert_valid(build_evidence(site_keys, fields, True, True, None, site_key_evidence=strong_site_key_evidence()))


def test_preflight_builder_outputs_valid_empty_site_list_evidence() -> None:
    assert_valid(
        build_evidence(
            [],
            observed_create_fields(),
            True,
            True,
            None,
            empty_site_list_evidence="verified empty /sites list",
        )
    )


def test_preflight_builder_rejects_invalid_site_key() -> None:
    try:
        parse_site_keys("mysite01,Invalid Site Key")
    except ValueError as exc:
        assert "invalid site key" in str(exc)
    else:
        raise AssertionError("invalid site key was accepted")


def test_preflight_builder_requires_site_key_evidence() -> None:
    try:
        build_evidence(["mysite01"], observed_create_fields(), True, True, None)
    except ValueError as exc:
        assert "site key evidence" in str(exc)
    else:
        raise AssertionError("site key evidence was not required")


def test_preflight_builder_rejects_weak_site_key_evidence() -> None:
    try:
        parse_site_key_evidence("mysite01 from page text body regex", ["mysite01"])
    except ValueError as exc:
        assert "must not rely" in str(exc)
    else:
        raise AssertionError("weak site key evidence was accepted")


def test_preflight_builder_requires_repo_check_note_on_failure() -> None:
    try:
        build_evidence(
            ["mysite01"],
            observed_create_fields(),
            True,
            False,
            None,
            site_key_evidence={"mysite01": strong_site_key_evidence()["mysite01"]},
        )
    except ValueError as exc:
        assert "repo-check-note" in str(exc)
    else:
        raise AssertionError("repo check failure without note was accepted")


def test_preflight_builder_rejects_missing_observed_description() -> None:
    try:
        parse_observed_fields("button: 创建站点;input name: name, placeholder: 站点名称;submit button: 创建;close button: Close")
    except ValueError as exc:
        assert "description" in str(exc)
    else:
        raise AssertionError("observed fields missing description were accepted")


def test_preflight_builder_rejects_unclosed_dialog() -> None:
    try:
        build_evidence(
            ["mysite01"],
            observed_create_fields(),
            False,
            True,
            None,
            site_key_evidence={"mysite01": strong_site_key_evidence()["mysite01"]},
        )
    except ValueError as exc:
        assert "dialog-closed-verified" in str(exc)
    else:
        raise AssertionError("unclosed create-site dialog was accepted")


def test_created_site_builder_outputs_valid_evidence() -> None:
    site_key = "codex-test-site"
    evidence = upgrade_evidence(
        create_preflight_evidence(),
        site_key,
        "products",
        ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
        ["name input", "slug input", "description textarea", "body editor"],
        f"site list shows {site_key} card and enter-backend control",
        f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        f"frontend opens at https://{site_key}.web.allincms.com",
        "site-info inspected for name, description, icon, notificationEmail, save",
        "domains inspected for CNAME, domain input, add domain",
        "media inspected for upload controls, asset grid, public URL hints",
        "themes inspected for search, create theme, page/design/preview controls",
        "routes inspected for columns and create controls",
        "forms inspected for name, slug, description, fields, status, update time",
        "tracking inspected for Google Tag ID input and add action",
        observed_module_routes(site_key),
        ["name", "description"],
        "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
        True,
        None,
        submitted_values={"name": "Example Demo", "description": "Example source-backed demo site."},
    )
    assert_valid(evidence)
    assert evidence["preflightGeneratedAt"] == RECENT_PREFLIGHT_AT
    assert evidence["generatedAt"] != RECENT_PREFLIGHT_AT
    assert evidence["siteCreation"]["submittedValues"]["name"] == "Example Demo"


def test_created_site_builder_supports_frontend_rendering_evidence() -> None:
    site_key = "codex-test-site"
    frontend_rendering = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    evidence = upgrade_evidence(
        create_preflight_evidence(),
        site_key,
        "products",
        ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
        ["name input", "slug input", "description textarea", "body editor"],
        f"site list shows {site_key} card and enter-backend control",
        f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        f"frontend opens at https://{site_key}.web.allincms.com",
        "site-info inspected for name, description, icon, notificationEmail, save",
        "domains inspected for CNAME, domain input, add domain",
        "media inspected for upload controls, asset grid, public URL hints",
        "themes inspected for search, create theme, page/design/preview controls",
        "routes inspected for columns and create controls",
        "forms inspected for name, slug, description, fields, status, update time",
        "tracking inspected for Google Tag ID input and add action",
        observed_module_routes(site_key),
        ["name", "description"],
        "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
        True,
        None,
        frontend_rendering,
    )
    assert_valid(evidence)
    summary = summarize_run_status(evidence, require_created_site=True)
    assert summary["valid"] is True
    assert "site_created_and_verified" in summary["proven"]
    assert "static_frontend_routes_render" in summary["proven"]
    assert "request_capture_persisted_verified" in summary["completionGaps"]


def test_created_site_builder_supports_launch_readiness_evidence() -> None:
    site_key = "codex-test-site"
    launch_readiness = build_launch_readiness_evidence(
        theme_active=True,
        pages_published=True,
        pages_enabled=True,
        routes_bound=True,
        frontend_http_ok=True,
        frontend_dom_verified=True,
        checked_paths=parse_checked_paths("/,/home,/products"),
        evidence="theme active, page rows published and enabled, routes bound, frontend audited",
        blocking_issues=[],
    )["launchReadiness"]
    evidence = upgrade_evidence(
        create_preflight_evidence(),
        site_key,
        "products",
        ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
        ["name input", "slug input", "description textarea", "body editor"],
        f"site list shows {site_key} card and enter-backend control",
        f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        f"frontend opens at https://{site_key}.web.allincms.com",
        "site-info inspected for name, description, icon, notificationEmail, save",
        "domains inspected for CNAME, domain input, add domain",
        "media inspected for upload controls, asset grid, public URL hints",
        "themes inspected for search, create theme, page/design/preview controls",
        "routes inspected for columns and create controls",
        "forms inspected for name, slug, description, fields, status, update time",
        "tracking inspected for Google Tag ID input and add action",
        observed_module_routes(site_key),
        ["name", "description"],
        "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
        True,
        None,
        None,
        launch_readiness,
    )
    assert_valid(evidence)
    summary = summarize_run_status(evidence, require_created_site=True)
    assert "theme_route_launch_ready" in summary["proven"]


def test_created_site_builder_allows_empty_before_create_list() -> None:
    site_key = "codex-test-site"
    preflight = create_preflight_evidence()
    preflight["siteCreation"]["existingSiteKeysBeforeCreate"] = []
    evidence = upgrade_evidence(
        preflight,
        site_key,
        "products",
        ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
        ["name input", "slug input", "description textarea", "body editor"],
        f"site list shows {site_key} card and enter-backend control",
        f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
        f"frontend opens at https://{site_key}.web.allincms.com",
        "site-info inspected for name, description, icon, notificationEmail, save",
        "domains inspected for CNAME, domain input, add domain",
        "media inspected for upload controls, asset grid, public URL hints",
        "themes inspected for search, create theme, page/design/preview controls",
        "routes inspected for columns and create controls",
        "forms inspected for name, slug, description, fields, status, update time",
        "tracking inspected for Google Tag ID input and add action",
        observed_module_routes(site_key),
        ["name", "description"],
        "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
        True,
        None,
    )
    assert_valid(evidence)


def test_created_site_evidence_requires_preflight_generated_at() -> None:
    data = created_site_evidence()
    data.pop("preflightGeneratedAt")
    assert_invalid_contains(data, "preflightGeneratedAt")


def test_run_evidence_rejects_invalid_generated_at() -> None:
    data = create_preflight_evidence()
    data["generatedAt"] = "2026-06-29 12:00:00"
    assert_invalid_contains(data, "timezone")


def test_created_site_builder_rejects_existing_key_reuse() -> None:
    site_key = "mysite01"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for mysite01",
            True,
            None,
        )
    except ValueError as exc:
        assert "already existed" in str(exc)
    else:
        raise AssertionError("created site key reused an existing key")


def test_created_site_builder_rejects_missing_page_evidence() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
            True,
            None,
        )
    except ValueError as exc:
        assert "site-info evidence" in str(exc)
    else:
        raise AssertionError("missing setup page evidence was accepted")


def test_created_site_builder_rejects_preflight_without_closed_dialog() -> None:
    site_key = "codex-test-site"
    preflight = create_preflight_evidence()
    preflight["siteCreation"].pop("dialogClosedVerified")
    try:
        upgrade_evidence(
            preflight,
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
            True,
            None,
        )
    except ValueError as exc:
        assert "dialog was closed" in str(exc)
    else:
        raise AssertionError("preflight without closed dialog verification was accepted")


def test_created_site_builder_requires_authorization_source() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "",
            True,
            None,
        )
    except ValueError as exc:
        assert "authorization source" in str(exc)
    else:
        raise AssertionError("empty authorization source was accepted")


def test_created_site_builder_rejects_generic_authorization_source() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "continue",
            True,
            None,
        )
    except ValueError as exc:
        assert "too generic" in str(exc)
    else:
        raise AssertionError("generic created-site authorization source was accepted")


def test_created_site_builder_rejects_evidence_for_wrong_site() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            "site list shows codex-test-site card",
            "dashboard opens at https://workspace.laicms.com/mysite01/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
            True,
            None,
        )
    except ValueError as exc:
        assert "backend evidence" in str(exc)
    else:
        raise AssertionError("backend evidence for a different site was accepted")


def test_created_site_builder_rejects_site_card_evidence_without_site_key() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            "site list shows the new card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name", "description"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
            True,
            None,
        )
    except ValueError as exc:
        assert "site card evidence" in str(exc)
    else:
        raise AssertionError("site card evidence without created site key was accepted")


def test_created_site_builder_requires_submitted_fields() -> None:
    site_key = "codex-test-site"
    try:
        upgrade_evidence(
            create_preflight_evidence(),
            site_key,
            "products",
            ["名称"],
            ["name input"],
            f"site list shows {site_key} card",
            f"dashboard opens at https://workspace.laicms.com/{site_key}/dashboard",
            f"frontend opens at https://{site_key}.web.allincms.com",
            "site-info evidence",
            "domains evidence",
            "media evidence",
            "themes evidence",
            "routes evidence",
            "forms evidence",
            "tracking evidence",
            observed_module_routes(site_key),
            ["name"],
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites for codex-test-site",
            True,
            None,
        )
    except ValueError as exc:
        assert "submitted fields" in str(exc)
    else:
        raise AssertionError("submitted fields missing description were accepted")


def test_created_site_validator_rejects_bad_submitted_values() -> None:
    data = created_site_evidence()
    data["siteCreation"]["submittedValues"] = {"name": "Example Demo", "description": ""}
    assert_invalid_contains(data, "siteCreation.submittedValues.description")


def test_created_site_builder_requires_observed_module_routes() -> None:
    site_key = "codex-test-site"
    try:
        parse_module_routes(
            ",".join(route for route in observed_module_routes(site_key) if not route.endswith("/domains")),
            site_key,
        )
    except ValueError as exc:
        assert "missing required modules" in str(exc)
    else:
        raise AssertionError("module routes missing domains were accepted")


def test_created_site_builder_rejects_wrong_site_module_route() -> None:
    site_key = "codex-test-site"
    routes = observed_module_routes(site_key)
    routes[0] = "/other-site/dashboard"
    try:
        parse_module_routes(",".join(routes), site_key)
    except ValueError as exc:
        assert "belong to created site key" in str(exc)
    else:
        raise AssertionError("module route for another site was accepted")


def test_run_evidence_rejects_business_domain_residue() -> None:
    data = create_preflight_evidence()
    data["notes"] = "lai" + "faxin.com should not be stored in LAICMS run evidence"
    assert_invalid_contains(data, "business-domain residue")


def test_skill_hygiene_rejects_non_cms_workflow_terms() -> None:
    pattern = audit_skill_hygiene.BLOCKLIST_PATTERNS["non_cms_workflow_leakage"]
    assert pattern.search("lead " + "search workflow belongs elsewhere")


def test_existing_site_builder_outputs_valid_evidence() -> None:
    class Args:
        site_key = "mysite01"
        existing_site_keys = "mysite01,mysite02"
        observed_create_fields = "button: 创建站点;dialog title: 创建站点;input name: name;textarea name: description;submit button: 创建;close button: Close"
        dialog_closed_verified = True
        module_routes = ",".join(observed_module_routes(site_key))
        content_type = "products"
        list_columns = "媒体,名称,Slug,描述,排序,状态,分类,标签,创建时间"
        edit_fields = "contenteditable editor,name input,product-slug input,description textarea,specs,main media,gallery,update,publish"
        site_info_evidence = "site-info fields: name, description, notificationEmail, save"
        domains_evidence = "domains fields: CNAME copy, domain input, add domain"
        media_evidence = "media fields: upload controls, asset grid, public URL hints"
        themes_evidence = "themes controls: search, create theme, page/design/preview"
        routes_evidence = "routes columns: path, bound page, status, notes, updated time"
        forms_evidence = "forms columns: name, slug, description, fields, status, updated time"
        tracking_evidence = "tracking fields: Google Tag ID input, add action"
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        frontend_route_patterns = ""
        markdown_residue_checked = False
        structured_rich_text_checked = False
        frontend_blocking_issues = ""
        repo_check_passed = True
        repo_check_note = None

    assert_valid(build_existing_site_evidence(Args()))


def test_create_preflight_from_existing_site_evidence_outputs_valid_preflight() -> None:
    data = existing_site_selected_evidence()
    preflight = build_create_preflight_from_existing(data)
    assert preflight["siteCreation"]["status"] == "create_preflight_verified"
    assert preflight["siteCreation"]["existingSiteKeysBeforeCreate"] == ["mysite01", "mysite02"]
    assert "siteIdentity" not in preflight
    assert_valid(preflight)


def test_create_preflight_from_existing_site_evidence_rejects_created_site_evidence() -> None:
    try:
        build_create_preflight_from_existing(created_site_evidence())
    except ValueError as exc:
        assert "existing_site_selected" in str(exc)
    else:
        raise AssertionError("created-site evidence was accepted as existing-site preflight source")


def test_existing_site_builder_rejects_unlisted_site_key() -> None:
    class Args:
        site_key = "mysite01"
        existing_site_keys = "mysite02"
        observed_create_fields = "button: 创建站点;dialog title: 创建站点;input name: name;textarea name: description;submit button: 创建;close button: Close"
        dialog_closed_verified = True
        module_routes = ",".join(observed_module_routes(site_key))
        content_type = "products"
        list_columns = "媒体,名称"
        edit_fields = "name input"
        site_info_evidence = "site-info evidence"
        domains_evidence = "domains evidence"
        media_evidence = "media evidence"
        themes_evidence = "themes evidence"
        routes_evidence = "routes evidence"
        forms_evidence = "forms evidence"
        tracking_evidence = "tracking evidence"
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        frontend_route_patterns = ""
        markdown_residue_checked = False
        structured_rich_text_checked = False
        frontend_blocking_issues = ""
        repo_check_passed = True
        repo_check_note = None

    try:
        build_existing_site_evidence(Args())
    except ValueError as exc:
        assert "present in --existing-site-keys" in str(exc)
    else:
        raise AssertionError("existing-site evidence accepted a site key absent from the site list")


def test_existing_site_builder_supports_pending_cleanup_candidates() -> None:
    class Args:
        site_key = "mysite01"
        existing_site_keys = "mysite01,mysite02"
        observed_create_fields = "button: 创建站点;dialog title: 创建站点;input name: name;textarea name: description;submit button: 创建;close button: Close"
        dialog_closed_verified = True
        module_routes = ",".join(observed_module_routes(site_key))
        content_type = "products"
        list_columns = "媒体,名称"
        edit_fields = "name input"
        site_info_evidence = "site-info evidence"
        domains_evidence = "domains evidence"
        media_evidence = "media evidence"
        themes_evidence = "themes evidence"
        routes_evidence = "routes evidence"
        forms_evidence = "forms evidence"
        tracking_evidence = "tracking evidence"
        cleanup_status = "pending_user_authorization"
        cleanup_candidates = "posts Untitled draft pattern,products Untitled draft pattern,forms Untitled draft pattern"
        frontend_route_patterns = ""
        markdown_residue_checked = False
        structured_rich_text_checked = False
        frontend_blocking_issues = ""
        repo_check_passed = True
        repo_check_note = None

    evidence = build_existing_site_evidence(Args())
    assert evidence["cleanup"]["status"] == "pending_user_authorization"
    assert_valid(evidence)


def test_existing_site_builder_supports_frontend_rendering_evidence() -> None:
    class Args:
        site_key = "mysite01"
        existing_site_keys = "mysite01,mysite02"
        observed_create_fields = "button: 创建站点;dialog title: 创建站点;input name: name;textarea name: description;submit button: 创建;close button: Close"
        dialog_closed_verified = True
        module_routes = ",".join(observed_module_routes(site_key))
        content_type = "products"
        list_columns = "媒体,名称"
        edit_fields = "name input"
        site_info_evidence = "site-info evidence"
        domains_evidence = "domains evidence"
        media_evidence = "media evidence"
        themes_evidence = "themes evidence"
        routes_evidence = "routes evidence"
        forms_evidence = "forms evidence"
        tracking_evidence = "tracking evidence"
        cleanup_status = "pending_user_authorization"
        cleanup_candidates = "posts Untitled draft pattern"
        frontend_route_patterns = "/posts,/posts/{slug},/products,/products/{slug}"
        markdown_residue_checked = True
        structured_rich_text_checked = True
        frontend_blocking_issues = "/posts/{slug}|literal_bold|redacted raw Markdown marker"
        repo_check_passed = True
        repo_check_note = None

    evidence = build_existing_site_evidence(Args())
    assert evidence["frontendRendering"]["checked"] is True
    assert_valid(evidence)


def minimal_existing_site_scan() -> dict:
    site_key = "mysite01"
    module_routes = {
        name: {
            "url": f"https://workspace.laicms.com/{site_key}/{name}",
            "headings": [name],
            "buttons": ["创建" if name in {"products", "posts", "forms", "routes", "themes"} else "保存"],
            "inputs": [{"tag": "input", "name": "name", "placeholder": "search"}],
            "tableHeads": [],
        }
        for name in ("dashboard", "media", "themes", "routes", "forms", "site-info", "tracking", "domains")
    }
    module_routes["posts"] = {
        "url": f"https://workspace.laicms.com/{site_key}/posts",
        "headings": ["文章"],
        "buttons": ["创建", "状态", "视图"],
        "inputs": [{"tag": "input", "name": "", "placeholder": "搜索文章..."}],
        "tableHeads": ["标题", "Slug", "摘要", "排序", "状态", "分类", "标签", "创建时间"],
    }
    module_routes["products"] = {
        "url": f"https://workspace.laicms.com/{site_key}/products",
        "headings": ["产品"],
        "buttons": ["创建", "状态", "视图"],
        "inputs": [{"tag": "input", "name": "", "placeholder": "搜索产品..."}],
        "tableHeads": ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
    }
    return {
        "siteKey": site_key,
        "contentType": "products",
        "sites": {
            "existingSiteKeys": [site_key, "mysite02"],
            "createDialog": {
                "closedVerified": True,
                "fields": ["input name", "textarea description"],
                "buttons": ["submit 创建", "Close"],
                "headings": ["创建站点"],
            },
        },
        "modules": module_routes,
    }


def test_existing_site_scan_builder_outputs_valid_evidence() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible, create control visible but not clicked"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(minimal_existing_site_scan(), Args()))
    assert evidence["siteIdentity"]["siteKey"] == "mysite01"
    assert evidence["siteCreation"]["dialogClosedVerified"] is True
    assert_valid(evidence)


def test_existing_site_scan_builder_accepts_redacted_module_url_placeholders() -> None:
    class Args:
        site_key = "mysite01"
        content_type = "products"
        edit_fields = "product list columns visible, create control visible but not clicked"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    for module_name, item in scan["modules"].items():
        item["url"] = f"https://workspace.laicms.com/{{siteKey}}/{module_name}"
    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(scan, Args()))
    assert f"/{Args.site_key}/products" in evidence["siteIdentity"]["moduleRoutes"]
    assert_valid(evidence)


def test_existing_site_scan_builder_accepts_table_headers_alias() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible, create control visible but not clicked"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["modules"]["products"]["tableHeaders"] = scan["modules"]["products"].pop("tableHeads")
    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(scan, Args()))
    assert "媒体" in evidence["contentInspection"]["listColumns"]
    assert_valid(evidence)


def test_existing_site_scan_builder_accepts_controller_dialog_shape() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible, create control visible but not clicked"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["sites"]["existingSiteKeysBeforeCreate"] = scan["sites"].pop("existingSiteKeys")
    scan["sites"]["dialogClosed"] = {"dialogCount": 0, "dialogs": [], "url": "https://workspace.laicms.com/sites"}
    scan["sites"]["createDialog"] = {
        "dialogs": [
            {
                "role": "dialog",
                "headings": ["创建站点"],
                "inputs": [
                    {"tag": "input", "name": "name", "placeholder": "站点名称"},
                    {"tag": "textarea", "name": "description", "placeholder": "站点简介"},
                ],
                "buttons": [
                    {"text": "创建", "type": "submit"},
                    {"text": "Close", "type": "button"},
                ],
            }
        ]
    }
    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(scan, Args()))
    assert evidence["siteCreation"]["existingSiteKeysBeforeCreate"] == ["mysite01", "mysite02"]
    assert evidence["siteCreation"]["dialogClosedVerified"] is True
    assert_valid(evidence)


def test_existing_site_scan_builder_accepts_without_create_dialog_for_existing_site_continuation() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible, create control visible but not clicked"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["sites"].pop("createDialog")
    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(scan, Args()))
    assert evidence["siteIdentity"]["siteKey"] == "mysite01"
    assert "createSiteFields" not in evidence["siteCreation"]
    assert "dialogClosedVerified" not in evidence["siteCreation"]
    assert evidence["siteCreation"]["selectedSiteEvidence"]
    assert_valid(evidence)


def test_existing_site_scan_builder_rejects_route_names_as_site_keys() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["sites"]["existingSiteKeys"] = ["dashboard", "help-center"]
    try:
        build_existing_site_args_from_scan(scan, Args())
    except ValueError as exc:
        assert "non-site route names" in str(exc)
    else:
        raise AssertionError("scan builder accepted route names as site keys")


def test_existing_site_scan_builder_rejects_unclosed_create_dialog() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["sites"]["createDialog"]["closedVerified"] = False
    try:
        build_existing_site_args_from_scan(scan, Args())
    except ValueError as exc:
        assert "closedVerified" in str(exc)
    else:
        raise AssertionError("scan builder accepted unclosed create dialog")


def test_existing_site_scan_builder_rejects_missing_module_url() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["modules"]["domains"].pop("url")
    try:
        build_existing_site_args_from_scan(scan, Args())
    except ValueError as exc:
        assert "domains.url" in str(exc)
    else:
        raise AssertionError("scan builder accepted missing module URL")


def test_existing_site_scan_builder_rejects_wrong_site_module_url() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["modules"]["products"]["url"] = "https://workspace.laicms.com/othersite/products"
    try:
        build_existing_site_args_from_scan(scan, Args())
    except ValueError as exc:
        assert "products.url" in str(exc)
    else:
        raise AssertionError("scan builder accepted wrong-site module URL")


def test_existing_site_scan_builder_filters_account_noise() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["modules"]["site-info"]["buttons"] = [
        "TO operator@example.com",
        "Toggle Sidebar",
        "LE Demo example.web.allincms.com",
        "保存",
    ]
    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(scan, Args()))
    site_info_text = " ".join(evidence["setupPages"]["siteInfo"])
    assert "operator@example.com" not in site_info_text
    assert "web.allincms.com" not in site_info_text
    assert "保存" in site_info_text


def test_browser_scan_redactor_removes_raw_noise_and_preserves_evidence_shape() -> None:
    class Args:
        site_key = ""
        content_type = "products"
        edit_fields = "product list columns visible"
        frontend_rendering_evidence = ""
        launch_readiness_evidence = ""
        cleanup_status = "not_needed"
        cleanup_candidates = ""
        repo_check_passed = True
        repo_check_note = None

    scan = minimal_existing_site_scan()
    scan["sites"]["url"] = "https://workspace.laicms.com/sites"
    scan["modules"]["site-info"]["buttons"] = [
        "TO operator@example.com",
        "Toggle Sidebar",
        "LE Demo example.web.allincms.com",
        "中文",
        "保存",
    ]
    scan["modules"]["products"]["links"] = ["https://mysite01.web.allincms.com/products"]
    scan["modules"]["products"]["relativeLinks"] = [
        "/mysite01/products",
        "/mysite01/posts?tab=tags",
        "/mysite01/themes/0123456789abcdef01234567",
    ]
    scan["modules"]["products"]["body"] = "temporary business copy that must not become evidence"
    scan["modules"]["dashboard"]["headings"] = ["LED Lighting Demo"]
    scan["modules"]["products"]["headings"].append("产品")
    scan["modules"]["products"]["buttons"].append("[redacted-email]")

    redacted = redact_scan(scan)
    dumped = json.dumps(redacted, ensure_ascii=False)
    assert "operator@example.com" not in dumped
    assert ".web.allincms.com" not in dumped
    assert "Toggle Sidebar" not in dumped
    assert "[redacted-email]" not in dumped
    assert "temporary business copy" not in dumped
    assert "LED Lighting Demo" not in dumped
    assert "0123456789abcdef01234567" not in dumped
    assert "/mysite01/products" not in dumped
    assert "/{siteKey}/themes/0123456789abcdef01234567" not in dumped
    assert "/{siteKey}/products" in dumped
    assert redacted["modules"]["products"]["url"] == "https://workspace.laicms.com/{siteKey}/products"
    assert "媒体" in redacted["modules"]["products"]["tableHeads"]

    evidence = build_existing_site_evidence(build_existing_site_args_from_scan(redacted, Args()))
    assert evidence["siteIdentity"]["siteKey"] == "mysite01"
    assert_valid(evidence)


def test_browser_scan_redactor_rejects_route_names_as_existing_site_keys() -> None:
    scan = minimal_existing_site_scan()
    scan["sites"]["existingSiteKeys"] = ["dashboard", "help-center"]
    try:
        redact_scan(scan)
    except ValueError as exc:
        assert "unsafe site key" in str(exc)
    else:
        raise AssertionError("redactor accepted route names as existing site keys")


def test_browser_scan_redactor_accepts_site_key_placeholders() -> None:
    scan = {
        "siteKey": "{realSiteKey}",
        "modules": {
            "products": {
                "url": "https://workspace.laicms.com/{realSiteKey}/products",
                "tableHeaders": ["名称"],
                "buttons": ["创建产品", "[redacted-email]"],
                "links": ["/mysite01/products", "/{realSiteKey}/posts"],
            }
        },
    }
    redacted = redact_scan(scan)
    dumped = json.dumps(redacted, ensure_ascii=False)
    assert redacted["siteKey"] == "{realSiteKey}"
    assert "[redacted-email]" not in dumped
    assert "/mysite01/products" not in dumped
    assert "/{siteKey}/products" in dumped


def test_browser_scan_redactor_preserves_existing_site_keys_before_create_alias() -> None:
    scan = minimal_existing_site_scan()
    scan["sites"]["existingSiteKeysBeforeCreate"] = scan["sites"].pop("existingSiteKeys")
    redacted = redact_scan(scan)
    assert redacted["sites"]["existingSiteKeysBeforeCreate"] == ["mysite01", "mysite02"]


def test_frontend_rendering_rejects_concrete_slug() -> None:
    data = base_evidence()
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/posts/" + "concrete-slug"],
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    assert_invalid_contains(data, "routePatterns")


def test_frontend_audit_redacts_urls_headings_and_issue_messages() -> None:
    reports = [
        {
            "url": "https://example.web.allincms.com/posts/example-slug",
            "status": 200,
            "headings": {"h1": ["Sensitive title"], "h2": []},
            "issues": [{"severity": "error", "code": "literal_bold", "message": "**Sensitive**"}],
        }
    ]
    redacted = audit_frontend_rendering.redact_reports(reports)
    assert redacted[0]["url"] == "/posts/{slug}"
    assert redacted[0]["headings"]["h1"] == ["redacted-h1-1"]
    assert redacted[0]["issues"][0]["message"] == "redacted"


def test_frontend_audit_redaction_preserves_detail_route_instances() -> None:
    reports = [
        {
            "url": "https://example.web.allincms.com/products/example-one",
            "status": 200,
            "headings": {"h1": ["Sensitive title 1"]},
            "issues": [],
        },
        {
            "url": "https://example.web.allincms.com/products/example-two",
            "status": 200,
            "headings": {"h1": ["Sensitive title 2"]},
            "issues": [],
        },
    ]
    redacted = audit_frontend_rendering.redact_reports(reports)
    assert [item["url"] for item in redacted] == ["/products/{slug}", "/products/{slug}"]
    assert [item["routeInstance"] for item in redacted] == ["products-detail-1", "products-detail-2"]


def test_frontend_audit_ignores_tailwind_double_star_class_markers() -> None:
    html = """
    <html><body>
      <main>
        <h1>Sample Product</h1>
        <p>Visible copy has no Markdown residue.</p>
        <div class="**:data-slate-placeholder:top-[auto_!important] placeholder:text-muted-foreground/80"></div>
      </main>
    </body></html>
    """
    report = audit_frontend_rendering.audit_html(
        "https://example.web.allincms.com/products/sample",
        html,
        200,
        "text/html; charset=utf-8",
        200,
    )
    assert report["diagnostics"]["htmlDoubleStarCount"] == 1
    assert report["diagnostics"]["visibleTextDoubleStarCount"] == 0
    assert not any(issue["code"] == "literal_bold" for issue in report["issues"])


def test_frontend_audit_fetch_respects_max_bytes() -> None:
    original_urlopen = audit_frontend_rendering.urlopen

    class FakeHeaders:
        def get(self, key: str, default: str = "") -> str:
            return "text/html; charset=utf-8" if key == "content-type" else default

    class FakeResponse:
        status = 200
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size: int = -1) -> bytes:
            payload = b"abcdefg"
            return payload if size in {-1, 0} else payload[:size]

    def fake_urlopen(request, timeout=0):
        return FakeResponse()

    try:
        audit_frontend_rendering.urlopen = fake_urlopen
        status, content_type, body = audit_frontend_rendering.fetch("https://example.web.allincms.com/", timeout=1, max_bytes=4)
    finally:
        audit_frontend_rendering.urlopen = original_urlopen

    assert status == 200
    assert "text/html" in content_type
    assert body == "abcd"


def test_frontend_audit_alarm_timeout_raises() -> None:
    try:
        with audit_frontend_rendering.alarm_timeout(1):
            time.sleep(2)
    except TimeoutError as exc:
        assert "exceeded" in str(exc)
    else:
        raise AssertionError("expected alarm_timeout to raise TimeoutError")


def test_launch_audit_input_helpers_generate_expected_urls() -> None:
    base_url = normalize_base_url("https://example.web.allincms.com")
    assert base_url == "https://example.web.allincms.com/"
    assert parse_paths("/,/home,/products", "static paths") == ["/", "/home", "/products"]
    assert build_url(base_url, "/products/codex-probe-delete-me") == "https://example.web.allincms.com/products/codex-probe-delete-me"


def test_launch_audit_input_helpers_reject_bad_paths() -> None:
    try:
        parse_paths("home", "static paths")
    except ValueError as exc:
        assert "start with /" in str(exc)
    else:
        raise AssertionError("relative launch audit path was accepted")


def schema_verified_product_manifest() -> dict:
    manifest = simulate_manifest_rehearsal.build_draft_manifest(
        "mysite01",
        "products",
        "https://mysite01.web.allincms.com",
    )
    manifest["schemaVerified"] = True
    manifest["payloadTemplate"] = {
        "productId": "{productId}",
        "siteId": "{siteId}",
        "mode": "update",
        "content": "{contentBlocks}",
    }
    manifest["items"].append(
        {
            "operation": "create",
            "name": "Codex Probe - Delete Me Second Product",
            "slug": "codex-probe-delete-me-second-product",
            "description": "Temporary local validation product.",
            "media": {
                "url": "https://example.com/image-2.jpg",
                "alt": "Temporary product validation image",
            },
            "categories": [],
            "tags": [],
            "specs": [],
            "content": [{"type": "paragraph", "children": [{"text": "Temporary local validation content."}]}],
        }
    )
    return manifest


def test_final_frontend_audit_inputs_generate_detail_urls_from_schema_manifest() -> None:
    manifest = schema_verified_product_manifest()
    urls, statuses, summary = build_final_frontend_audit_inputs(
        manifest,
        "https://mysite01.web.allincms.com",
        ["/", "/products"],
    )
    assert "https://mysite01.web.allincms.com/" in urls
    assert "https://mysite01.web.allincms.com/products" in urls
    assert "https://mysite01.web.allincms.com/products/codex-probe-delete-me-sample-product" in urls
    assert "https://mysite01.web.allincms.com/products/codex-probe-delete-me-second-product" in urls
    assert set(statuses.values()) == {200}
    assert summary["detailRouteCount"] == 2
    assert "/products/{slug}" in summary["routePatterns"]


def test_final_frontend_audit_progress_complete_rejects_missing_slug() -> None:
    manifest = schema_verified_product_manifest()
    progress = [
        {
            "slug": "codex-probe-delete-me-sample-product",
            "contentType": "products",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverVerified": True,
            "errors": [],
        }
    ]
    errors = validate_final_audit_progress_complete(manifest, progress)
    assert any("missing manifest slug codex-probe-delete-me-second-product" in error for error in errors), errors


def test_final_frontend_audit_progress_complete_rejects_extra_slug() -> None:
    manifest = schema_verified_product_manifest()
    progress = [
        {
            "slug": item["slug"],
            "contentType": "products",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverVerified": True,
            "errors": [],
        }
        for item in manifest["items"]
    ]
    progress.append(
        {
            "slug": "unexpected-extra-product",
            "contentType": "products",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverVerified": True,
            "errors": [],
        }
    )
    errors = validate_final_audit_progress_complete(manifest, progress)
    assert any("unexpected-extra-product is not present in manifest" in error for error in errors), errors


def test_final_frontend_audit_progress_complete_rejects_skipped_publish() -> None:
    manifest = schema_verified_product_manifest()
    progress = [
        {
            "slug": item["slug"],
            "contentType": "products",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverVerified": True,
            "errors": [],
        }
        for item in manifest["items"]
    ]
    progress[0]["publishStatus"] = "skipped"
    errors = validate_final_audit_progress_complete(manifest, progress)
    assert any("publishStatus must be ok for final frontend audit" in error for error in errors), errors


def test_final_frontend_audit_progress_complete_accepts_successful_batch() -> None:
    manifest = schema_verified_product_manifest()
    progress = [
        {
            "slug": item["slug"],
            "contentType": "products",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverOrMediaVerified": True,
            "errors": [],
        }
        for item in manifest["items"]
    ]
    assert validate_final_audit_progress_complete(manifest, progress) == []


def test_final_frontend_audit_manifest_loader_requires_schema_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manifest_path = Path(tmp_dir) / "draft.json"
        manifest_path.write_text(
            json.dumps(simulate_manifest_rehearsal.build_draft_manifest("mysite01", "products"), indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            load_final_audit_manifest(manifest_path, require_schema_verified=True)
        except ValueError as exc:
            assert "schemaVerified" in str(exc)
            assert "payloadTemplate" in str(exc)
        else:
            raise AssertionError("final frontend audit manifest loader accepted unverified schema")


def test_final_frontend_audit_progress_entries_accepts_wrapped_progress_log() -> None:
    data = {"progressLog": [{"slug": "example-product"}]}
    assert final_audit_progress_entries(data) == [{"slug": "example-product"}]


def final_frontend_audit_packet() -> dict:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "generatedAt": RECENT_AUTHORIZATION_AT,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "final_frontend_audit",
        "recovery": False,
        "phase": "final QA",
        "mode": "verification",
        "targetTemplate": "https://{realSiteKey}.web.allincms.com",
        "authorizationRequired": False,
        "remoteMutationExpectation": "must_not",
        "suggestedAuthorizationText": "",
        "allowedActions": ["audit all static routes and uploaded detail routes"],
        "requiredProof": [
            "HTTP status report",
            "DOM/rich-text report",
            "image report",
            "broken-entry list empty",
        ],
        "forbiddenActions": ["backend mutation while auditing"],
        "stopAfter": "Stop if any expected route, image, description, body, or status fails.",
        "evidenceCaptureTemplate": {
            "stageId": "final_frontend_audit",
            "status": "completed|blocked|partial",
            "redactedEvidencePointers": [],
            "proofRecorded": [
                "HTTP status report",
                "DOM/rich-text report",
                "image report",
                "broken-entry list empty",
            ],
            "blockingIssues": [],
            "operatorNote": "",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "afterStageCompletes": "Apply a completed, partial, or blocked stage result after redacted evidence is recorded.",
            "expectedCompletedStageIdsAfterApply": ["final_frontend_audit"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json "
                "--packet ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json "
                "--result-json /tmp/allincms-stage-result.json "
                "--output ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.updated.json"
            ),
        },
        "warnings": ["This packet is local-only and does not authorize remote LAICMS mutation."],
    }
    validation = validate_browser_stage_packet(packet)
    assert validation["ok"], validation["issues"]
    return packet


def clean_final_frontend_report() -> list[dict]:
    return [
        {
            "url": "/products",
            "urlFingerprint": final_audit_url_fingerprint("https://example.web.allincms.com/products"),
            "routeInstance": "route-products-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "strong": 2, "table": 1},
            "headings": {"h1": ["redacted-h1-1"], "h2": []},
            "imageCount": 3,
            "linkCount": 8,
            "issues": [],
        },
        {
            "url": "/products/{slug}",
            "urlFingerprint": final_audit_url_fingerprint("https://example.web.allincms.com/products/example-product"),
            "routeInstance": "products-detail-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "strong": 1, "table": 1},
            "headings": {"h1": ["redacted-h1-1"], "h2": ["redacted-h2-1"]},
            "imageCount": 4,
            "linkCount": 6,
            "issues": [{"severity": "warn", "code": "missing_h1", "message": "redacted"}],
        },
    ]


def write_final_frontend_report(tmp_dir: str, reports: list[dict]) -> Path:
    path = Path(tmp_dir) / "final-audit-report.json"
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_final_frontend_audit_stage_result_completes_clean_report() -> None:
    packet = final_frontend_audit_packet()
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, clean_final_frontend_report())
        result = build_final_frontend_audit_stage_result(
            packet,
            report_path,
            ["local://final-audit-report.json", "local://final-audit-inputs-summary.json"],
            False,
        )
    assert result["stageId"] == "final_frontend_audit"
    assert result["status"] == "completed"
    assert result["browserStageMutatedRemote"] is False
    assert set(packet["requiredProof"]) <= set(result["proofRecorded"])
    assert result["blockingIssues"] == []


def test_final_frontend_audit_stage_result_completes_with_expected_coverage() -> None:
    packet = final_frontend_audit_packet()
    audit_inputs_summary = {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "contentType": "products",
        "staticRouteCount": 1,
        "detailRouteCount": 1,
        "routePatterns": ["/products", "/products/{slug}"],
    }
    expected_statuses = {
        "https://example.web.allincms.com/products": 200,
        "https://example.web.allincms.com/products/example-product": 200,
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, clean_final_frontend_report())
        result = build_final_frontend_audit_stage_result(
            packet,
            report_path,
            ["local://final-audit-report.json", "local://final-audit-inputs-summary.json"],
            False,
            audit_inputs_summary,
            expected_statuses,
        )
    assert result["status"] == "completed"
    assert result["blockingIssues"] == []


def test_final_frontend_audit_stage_result_requires_detail_instances_for_multiple_items() -> None:
    packet = final_frontend_audit_packet()
    audit_inputs_summary = {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "contentType": "products",
        "staticRouteCount": 1,
        "detailRouteCount": 2,
        "routePatterns": ["/products", "/products/{slug}"],
    }
    expected_statuses = {
        "https://example.web.allincms.com/products": 200,
        "https://example.web.allincms.com/products/example-one": 200,
        "https://example.web.allincms.com/products/example-two": 200,
    }
    reports = clean_final_frontend_report()
    reports.append(dict(reports[1]))
    for report in reports:
        report.pop("routeInstance", None)
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, reports)
        result = build_final_frontend_audit_stage_result(
            packet,
            report_path,
            ["local://final-audit-report.json", "local://final-audit-inputs-summary.json"],
            False,
            audit_inputs_summary,
            expected_statuses,
        )
    assert result["status"] == "partial"
    assert any("missing unique redacted routeInstance" in issue for issue in result["blockingIssues"])
    assert any("detail route instance count" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_partials_when_expected_route_missing() -> None:
    packet = final_frontend_audit_packet()
    audit_inputs_summary = {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "contentType": "products",
        "staticRouteCount": 1,
        "detailRouteCount": 1,
        "routePatterns": ["/products", "/products/{slug}"],
    }
    expected_statuses = {
        "https://example.web.allincms.com/products": 200,
        "https://example.web.allincms.com/products/example-product": 200,
    }
    reports = clean_final_frontend_report()[:1]
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, reports)
        result = build_final_frontend_audit_stage_result(
            packet,
            report_path,
            ["local://final-audit-report.json", "local://final-audit-inputs-summary.json"],
            False,
            audit_inputs_summary,
            expected_statuses,
        )
    assert result["status"] == "partial"
    assert "broken-entry list empty" not in result["proofRecorded"]
    assert any("audit report route count 1 != expected 2" in issue for issue in result["blockingIssues"])
    assert any("missing expected route pattern /products/{slug}" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_partials_on_http_mismatch() -> None:
    packet = final_frontend_audit_packet()
    reports = clean_final_frontend_report()
    reports[1]["status"] = 404
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, reports)
        result = build_final_frontend_audit_stage_result(packet, report_path, ["local://final-audit-report.json"], False)
    assert result["status"] == "partial"
    assert "broken-entry list empty" not in result["proofRecorded"]
    assert any("HTTP status 404 != expected 200" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_partials_on_dom_issue() -> None:
    packet = final_frontend_audit_packet()
    reports = clean_final_frontend_report()
    reports[0]["issues"] = [{"severity": "error", "code": "literal_bold", "message": "redacted"}]
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, reports)
        result = build_final_frontend_audit_stage_result(packet, report_path, ["local://final-audit-report.json"], False)
    assert result["status"] == "partial"
    assert any("DOM/rich-text issue literal_bold" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_partials_on_image_issue() -> None:
    packet = final_frontend_audit_packet()
    reports = clean_final_frontend_report()
    reports[0]["issues"] = [{"severity": "error", "code": "image_missing_src", "message": "redacted"}]
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, reports)
        result = build_final_frontend_audit_stage_result(packet, report_path, ["local://final-audit-report.json"], False)
    assert result["status"] == "partial"
    assert any("image issue image_missing_src" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_can_fail_on_warn() -> None:
    packet = final_frontend_audit_packet()
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, clean_final_frontend_report())
        result = build_final_frontend_audit_stage_result(packet, report_path, ["local://final-audit-report.json"], True)
    assert result["status"] == "partial"
    assert any("DOM/rich-text issue missing_h1" in issue for issue in result["blockingIssues"])


def test_final_frontend_audit_stage_result_rejects_wrong_packet_stage() -> None:
    packet = final_frontend_audit_packet()
    packet["stageId"] = "static_frontend_audit"
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = write_final_frontend_report(tmp_dir, clean_final_frontend_report())
        try:
            build_final_frontend_audit_stage_result(packet, report_path, ["local://final-audit-report.json"], False)
        except ValueError as exc:
            assert "packet stageId must be final_frontend_audit" in str(exc)
        else:
            raise AssertionError("final frontend audit result accepted a non-final packet")


def test_frontend_rendering_evidence_builder_preserves_statuses_and_issues() -> None:
    evidence = build_frontend_rendering_evidence(
        [
            {
                "url": "/products",
                "expectedStatus": 200,
                "issues": [],
            },
            {
                "url": "/products/{slug}",
                "expectedStatus": 404,
                "issues": [{"severity": "error", "code": "http_status", "message": "redacted"}],
            },
        ],
        include_warnings=False,
    )
    rendering = evidence["frontendRendering"]
    assert rendering["routePatterns"] == ["/products", "/products/{slug}"]
    assert rendering["expectedStatuses"] == {"/products": 200, "/products/{slug}": 404}
    assert rendering["blockingIssues"] == [
        {"routePattern": "/products/{slug}", "code": "http_status", "evidence": "redacted audit issue"}
    ]


def test_existing_site_builder_loads_frontend_rendering_evidence_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "frontend.json"
        path.write_text(
            json.dumps(
                {
                    "frontendRendering": {
                        "checked": True,
                        "routePatterns": ["/products", "/products/{slug}"],
                        "expectedStatuses": {"/products": 200, "/products/{slug}": 404},
                        "markdownResidueChecked": True,
                        "structuredRichTextChecked": True,
                        "blockingIssues": [],
                    }
                }
            ),
            encoding="utf-8",
        )
        loaded = load_frontend_rendering(str(path))
    assert loaded["expectedStatuses"]["/products/{slug}"] == 404


def test_existing_site_builder_loads_launch_readiness_evidence_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "launch.json"
        path.write_text(
            json.dumps(
                build_launch_readiness_evidence(
                    theme_active=True,
                    pages_published=True,
                    pages_enabled=True,
                    routes_bound=True,
                    frontend_http_ok=True,
                    frontend_dom_verified=True,
                    checked_paths=parse_checked_paths("/,/home,/products"),
                    evidence="theme active, page rows published and enabled, routes bound, frontend audited",
                    blocking_issues=[],
                )
            ),
            encoding="utf-8",
        )
        loaded = load_existing_site_launch_readiness(str(path))
    assert loaded["routesBound"] is True


def test_module_scan_summary_treats_rsc_fetches_as_read_only_prefetches() -> None:
    scan = [
        {
            "module": "routes",
            "url": "https://workspace.laicms.com/{siteKey}/routes",
            "requests": [
                {
                    "method": "GET",
                    "path": "/{siteKey}/routes",
                    "type": "Document",
                    "status": 200,
                    "mime": "text/html",
                },
                {
                    "method": "GET",
                    "path": "/{siteKey}/products?_rsc={token}",
                    "type": "Fetch",
                    "status": 200,
                    "mime": "text/x-component",
                },
            ],
            "dom": {
                "tableHeaders": ["路径", "绑定页面", "绑定状态"],
                "inputs": [],
                "buttons": ["创建"],
            },
        }
    ]
    assert validate_module_scan_redaction(scan) == []
    summary = summarize_module_scan(scan)
    module = summary["modules"][0]
    assert summary["jsonReplayReady"] is False
    assert summary["captureNextActions"][0]["module"] == "routes"
    assert module["jsonSuitability"] == "read_only_prefetch_only"
    assert module["postPaths"] == []
    assert "/{siteKey}/products?_rsc={token}" in module["rscFetchPaths"]
    assert "No mutation request captured" in module["jsonAccelerationRule"]


def test_module_scan_summary_flags_post_as_action_specific_review() -> None:
    scan = [
        {
            "module": "routes",
            "url": "https://workspace.laicms.com/{siteKey}/routes",
            "requests": [
                {
                    "method": "GET",
                    "path": "/{siteKey}/routes",
                    "type": "Document",
                    "status": 200,
                    "mime": "text/html",
                },
                {
                    "method": "POST",
                    "path": "/{siteKey}/routes",
                    "type": "Fetch",
                    "status": 200,
                    "mime": "text/x-component",
                    "payloadShape": "siteId,path,query,routeMode,parentPath,note",
                },
            ],
            "dom": {
                "tableHeaders": ["路径", "绑定页面", "绑定状态"],
                "inputs": ["路径", "备注"],
                "buttons": ["创建"],
            },
        }
    ]
    assert validate_module_scan_redaction(scan) == []
    summary = summarize_module_scan(scan)
    module = summary["modules"][0]
    assert summary["jsonReplayReady"] is False
    assert summary["blockedReplayActions"][0]["status"] == "captured_post_requires_review"
    assert summary["captureNextActions"] == []
    assert module["jsonSuitability"] == "captured_post_requires_review"
    assert module["postPaths"] == ["/{siteKey}/routes"]
    assert module["payloadShapes"] == {"siteId,path,query,routeMode,parentPath,note": 1}
    assert any(action["action"] == "create" for action in module["inferredActions"])
    assert "Do not replay" in module["jsonAccelerationRule"]


def test_module_scan_accepts_redacted_object_scan_without_network_requests() -> None:
    scan_object = {
        "siteKey": "{siteKey}",
        "contentType": "products",
        "modules": {
            "products": {
                "url": "https://workspace.laicms.com/{siteKey}/products",
                "tableHeads": ["媒体", "名称", "Slug", "描述"],
                "buttons": ["创建产品"],
                "inputs": [{"tag": "input", "name": "search", "placeholder": "搜索"}],
                "headings": ["产品"],
            },
            "routes": {
                "url": "https://workspace.laicms.com/{siteKey}/routes",
                "tableHeads": ["路径", "绑定页面", "绑定状态"],
                "buttons": ["创建"],
                "inputs": [],
                "headings": ["路由"],
            },
        },
    }
    scan = module_items_from_object(scan_object)
    assert validate_module_scan_redaction(scan) == []
    summary = summarize_module_scan(scan)
    modules = {module["module"]: module for module in summary["modules"]}
    assert summary["jsonReplayReady"] is False
    assert any(action["module"] == "products" for action in summary["captureNextActions"])
    assert modules["products"]["jsonSuitability"] == "read_only_only"
    assert modules["products"]["postPaths"] == []
    assert modules["products"]["documentPaths"] == ["/{siteKey}/products"]
    assert any(action["status"] == "visible_control_only" for action in modules["products"]["inferredActions"])
    assert "No mutation request captured" in modules["products"]["jsonAccelerationRule"]


def test_module_scan_accepts_compact_browser_network_summary() -> None:
    scan_object = {
        "kind": "allincms_redacted_readonly_browser_scan",
        "siteKey": "{siteKey}",
        "modules": {
            "products": {
                "url": "https://workspace.laicms.com/{siteKey}/products",
                "tableHeaders": ["媒体", "名称", "Slug", "描述"],
                "buttons": ["创建产品"],
                "inputs": [{"tag": "input", "placeholder": "搜索产品..."}],
                "headings": ["产品"],
                "network": {
                    "documentGetObserved": True,
                    "rscGetCount": 3,
                    "postCount": 0,
                    "postSamples": [],
                },
            },
            "routes": {
                "url": "https://workspace.laicms.com/{siteKey}/routes",
                "tableHeaders": ["路径", "绑定页面", "绑定状态"],
                "buttons": ["创建"],
                "inputs": [],
                "headings": ["路由"],
                "network": {
                    "documentGetObserved": True,
                    "rscGetCount": 0,
                    "postCount": 1,
                    "postSamples": [
                        {
                            "method": "POST",
                            "url": "https://workspace.laicms.com/{siteKey}/routes",
                            "payloadShape": "redacted route server action payload",
                        }
                    ],
                },
            },
        },
    }
    scan = module_items_from_object(scan_object)
    assert validate_module_scan_redaction(scan) == []
    summary = summarize_module_scan(scan)
    modules = {module["module"]: module for module in summary["modules"]}
    assert modules["products"]["tableHeaders"] == ["媒体", "名称", "Slug", "描述"]
    assert modules["products"]["jsonSuitability"] == "read_only_prefetch_only"
    assert "/{siteKey}/products?_rsc={token}" in modules["products"]["rscFetchPaths"]
    assert modules["routes"]["jsonSuitability"] == "captured_post_requires_review"
    assert modules["routes"]["payloadShapes"]["redacted route server action payload"] == 1


def test_module_scan_redaction_accepts_real_site_key_placeholder() -> None:
    scan = [
        {
            "module": "products",
            "url": "https://workspace.laicms.com/{realSiteKey}/products",
            "requests": [
                {
                    "method": "GET",
                    "path": "/{realSiteKey}/products",
                    "type": "Document",
                    "mime": "text/html",
                }
            ],
            "dom": {"tableHeaders": ["名称"], "buttons": ["创建产品"], "inputs": []},
        }
    ]
    assert validate_module_scan_redaction(scan) == []
    summary = summarize_module_scan(scan)
    assert summary["modules"][0]["documentPaths"] == ["/{realSiteKey}/products"]


def test_module_scan_redaction_accepts_safe_workspace_site_key() -> None:
    scan = [
        {
            "module": "products",
            "url": "https://workspace.laicms.com/mysite01/products",
            "requests": [
                {
                    "method": "GET",
                    "path": "/mysite01/products",
                    "type": "Document",
                    "mime": "text/html",
                }
            ],
            "dom": {"tableHeaders": ["名称"], "buttons": ["创建产品"], "inputs": []},
        }
    ]
    assert validate_module_scan_redaction(scan) == []


def test_module_scan_redaction_rejects_unsafe_site_key_and_headers() -> None:
    scan = [
        {
            "module": "products",
            "url": "https://workspace.laicms.com/not-safe-key/products",
            "requests": [
                {
                    "method": "POST",
                    "path": "/not-safe-key/products",
                    "payloadShape": "next-action,siteId",
                }
            ],
            "dom": {"tableHeaders": [], "buttons": [], "inputs": []},
        }
    ]
    issues = validate_module_scan_redaction(scan)
    assert any("unsafe" in issue for issue in issues)
    assert any("sensitive" in issue for issue in issues)


def test_module_capture_plan_groups_visible_controls_by_authorization_boundary() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {
                "module": "products",
                "action": "create",
                "status": "visible_control_only",
                "requiredProof": ["request capture"],
            },
            {
                "module": "routes",
                "action": "bind",
                "status": "visible_control_only",
                "requiredProof": ["frontend proof"],
            },
            {
                "module": "media",
                "action": "upload",
                "status": "visible_control_only",
                "requiredProof": ["multipart proof"],
            },
        ],
    }
    plan = build_module_capture_plan(summary, "mysite01", None)
    assert plan["kind"] == "allincms_module_capture_plan"
    assert plan["jsonReplayReady"] is False
    stages = {(stage["module"], stage["action"]): stage for stage in plan["stages"]}
    assert stages[("products", "create")]["authorizationAction"] == "create_product_probe"
    assert "do not save or publish" in stages[("products", "create")]["stopAfter"]
    assert stages[("routes", "bind")]["authorizationAction"] == "bind_route"
    assert any("frontend HTTP and DOM" in item for item in stages[("routes", "bind")]["mustCapture"])
    assert stages[("media", "upload")]["authorizationAction"] == "upload_media"


def test_module_capture_plan_can_filter_modules() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
            {"module": "routes", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "", {"routes"})
    assert [stage["module"] for stage in plan["stages"]] == ["routes"]
    assert plan["stages"][0]["target"] == "https://workspace.laicms.com/{siteKey}/routes"


def test_module_capture_plan_includes_domain_and_tracking_add_actions() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "domains", "action": "create", "status": "visible_control_only"},
            {"module": "tracking", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "{realSiteKey}", None)
    stages = {(stage["module"], stage["action"]): stage for stage in plan["stages"]}
    assert stages[("domains", "create")]["group"] == "external_or_destructive_manual_review"
    assert stages[("domains", "create")]["authorizationAction"] == "add_domain"
    assert stages[("tracking", "create")]["group"] == "site_settings_capture"
    assert stages[("tracking", "create")]["authorizationAction"] == "add_tracking_tag"


def test_capture_authorization_package_for_product_probe_stage() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    stage = select_capture_stage(plan, "products", "create")
    package = build_capture_authorization_package(
        stage,
        "/tmp/created-site-evidence.json",
        "/tmp/create-product-auth.json",
    )
    assert package["authorizationAction"] == "create_product_probe"
    assert package["gateSupported"] is True
    assert "Codex Probe - Delete Me" in package["suggestedAuthorizationText"]
    assert "产品测试草稿" in package["suggestedAuthorizationText"]
    assert "products 测试草稿" not in package["suggestedAuthorizationText"]
    assert "make_authorization_record.py --action create_product_probe" in package["authorizationRecordCommand"]
    assert AUTHORIZATION_SOURCE_PLACEHOLDER in package["authorizationRecordCommand"]
    assert "授权 Codex" not in package["authorizationRecordCommand"]
    assert package["suggestedAuthorizationText"] not in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_product_probe" in package["preMutationGateCommand"]
    assert validate_capture_authorization_package(package, plan) == []


def test_capture_authorization_package_validator_rejects_target_drift() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    stage = select_capture_stage(plan, "products", "create")
    package = build_capture_authorization_package(stage, "/tmp/evidence.json", "/tmp/auth.json")
    package["target"] = "https://workspace.laicms.com/realsite01/posts"
    issues = validate_capture_authorization_package(package, plan)

    assert any("target module" in issue or "target must match" in issue for issue in issues)


def test_capture_authorization_package_validator_rejects_embedded_suggested_authorization() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    stage = select_capture_stage(plan, "products", "create")
    package = build_capture_authorization_package(stage, "/tmp/evidence.json", "/tmp/auth.json")
    package["authorizationRecordCommand"] = package["authorizationRecordCommand"].replace(
        AUTHORIZATION_SOURCE_PLACEHOLDER,
        package["suggestedAuthorizationText"],
    )
    issues = validate_capture_authorization_package(package, plan)

    assert any("current-user authorization placeholder" in issue for issue in issues)
    assert any("suggestedAuthorizationText" in issue for issue in issues)
    assert any("helper-generated authorization wording" in issue for issue in issues)


def test_capture_authorization_package_marks_unsupported_gate() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "media", "action": "upload", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    stage = select_capture_stage(plan, "media", "upload")
    package = build_capture_authorization_package(stage, "/tmp/evidence.json", "/tmp/auth.json")
    assert package["authorizationAction"] == "upload_media"
    assert package["gateSupported"] is False
    assert package["preMutationGateCommand"] is None


def test_capture_authorization_package_supports_domain_and_tracking_gates() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "domains", "action": "create", "status": "visible_control_only"},
            {"module": "tracking", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    domain_package = build_capture_authorization_package(
        select_capture_stage(plan, "domains", "create"),
        "/tmp/evidence.json",
        "/tmp/auth-domain.json",
    )
    tracking_package = build_capture_authorization_package(
        select_capture_stage(plan, "tracking", "create"),
        "/tmp/evidence.json",
        "/tmp/auth-tracking.json",
    )
    assert domain_package["authorizationAction"] == "add_domain"
    assert domain_package["gateSupported"] is True
    assert "make_authorization_record.py --action add_domain" in domain_package["authorizationRecordCommand"]
    assert AUTHORIZATION_SOURCE_PLACEHOLDER in domain_package["authorizationRecordCommand"]
    assert "授权 Codex" not in domain_package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action add_domain" in domain_package["preMutationGateCommand"]
    assert tracking_package["authorizationAction"] == "add_tracking_tag"
    assert tracking_package["gateSupported"] is True
    assert "make_authorization_record.py --action add_tracking_tag" in tracking_package["authorizationRecordCommand"]
    assert AUTHORIZATION_SOURCE_PLACEHOLDER in tracking_package["authorizationRecordCommand"]
    assert "授权 Codex" not in tracking_package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action add_tracking_tag" in tracking_package["preMutationGateCommand"]


def test_capture_authorization_package_suppresses_simulated_targets_by_default() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "domains", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "simsite01", None)
    package = build_capture_authorization_package(
        select_capture_stage(plan, "domains", "create"),
        "/tmp/evidence.json",
        "/tmp/auth-domain.json",
    )
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert package["preMutationGateCommand"] is None
    assert "simsite01" not in package["suggestedAuthorizationText"]
    assert "{realSiteKey}" in package["suggestedAuthorizationText"]
    assert package["simulatedTarget"] == "https://workspace.laicms.com/simsite01/domains"
    assert validate_capture_authorization_package(package, plan) == []


def test_capture_authorization_package_can_allow_simulated_targets_for_local_tests() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "domains", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "simsite01", None)
    package = build_capture_authorization_package(
        select_capture_stage(plan, "domains", "create"),
        "/tmp/evidence.json",
        "/tmp/auth-domain.json",
        allow_simulated_target=True,
    )
    assert package.get("commandsSuppressed") is not True
    assert "make_authorization_record.py --action add_domain" in package["authorizationRecordCommand"]
    assert AUTHORIZATION_SOURCE_PLACEHOLDER in package["authorizationRecordCommand"]


def test_all_capture_authorization_package_builder_writes_valid_package_set() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
            {"module": "media", "action": "upload", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "packages"
        package_set = build_all_capture_authorization_packages(
            capture_plan=plan,
            preflight_path="/tmp/evidence.json",
            output_dir=output_dir,
        )
        assert package_set["valid"] is True
        assert package_set["preparedOnly"] is True
        assert package_set["isUserAuthorization"] is False
        assert package_set["count"] == 2
        items = {(item["module"], item["action"]): item for item in package_set["items"]}
        assert items[("products", "create")]["gateSupported"] is True
        assert items[("media", "upload")]["gateSupported"] is False
        for item in package_set["items"]:
            assert Path(item["package"]).exists()
            package = json.loads(Path(item["package"]).read_text(encoding="utf-8"))
            if package.get("commandsSuppressed") is not True:
                assert AUTHORIZATION_SOURCE_PLACEHOLDER in package["authorizationRecordCommand"]
                assert "授权 Codex" not in package["authorizationRecordCommand"]
            assert validate_capture_authorization_package(package, plan) == []
        assert validate_all_capture_authorization_packages(package_set, plan) == []


def test_all_capture_authorization_package_builder_suppresses_simulated_targets() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "domains", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "simsite01", None)
    with tempfile.TemporaryDirectory() as tmp:
        package_set = build_all_capture_authorization_packages(
            capture_plan=plan,
            preflight_path="/tmp/evidence.json",
            output_dir=Path(tmp),
        )
        item = package_set["items"][0]
        assert package_set["valid"] is True
        assert item["commandsSuppressed"] is True
        package = json.loads(Path(item["package"]).read_text(encoding="utf-8"))
        assert package["authorizationRecordCommand"] is None
        assert "{realSiteKey}" in package["suggestedAuthorizationText"]
        assert "simsite01" not in package["suggestedAuthorizationText"]
        assert validate_all_capture_authorization_packages(package_set, plan) == []


def test_all_capture_authorization_package_validator_rejects_summary_drift() -> None:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
        ],
    }
    plan = build_module_capture_plan(summary, "realsite01", None)
    with tempfile.TemporaryDirectory() as tmp:
        package_set = build_all_capture_authorization_packages(
            capture_plan=plan,
            preflight_path="/tmp/evidence.json",
            output_dir=Path(tmp),
        )
        package_set["items"][0]["target"] = "https://workspace.laicms.com/realsite01/posts"
        package_set["valid"] = True
        issues = validate_all_capture_authorization_packages(package_set, plan)
        assert any("summary target does not match package" in issue for issue in issues)


def full_capture_plan_for_gate_coverage() -> dict:
    summary = {
        "kind": "allincms_module_scan_summary",
        "captureNextActions": [
            {"module": "products", "action": "create", "status": "visible_control_only"},
            {"module": "posts", "action": "create", "status": "visible_control_only"},
            {"module": "media", "action": "upload", "status": "visible_control_only"},
            {"module": "themes", "action": "create", "status": "visible_control_only"},
            {"module": "routes", "action": "create", "status": "visible_control_only"},
            {"module": "routes", "action": "bind", "status": "visible_control_only"},
            {"module": "forms", "action": "create", "status": "visible_control_only"},
            {"module": "site-info", "action": "save", "status": "visible_control_only"},
            {"module": "domains", "action": "create", "status": "visible_control_only"},
            {"module": "tracking", "action": "create", "status": "visible_control_only"},
        ],
    }
    return build_module_capture_plan(summary, "realsite01", None)


def test_capture_plan_gate_coverage_accepts_current_full_plan() -> None:
    result = validate_plan_gate_coverage(full_capture_plan_for_gate_coverage())
    assert result["ok"] is True, result["issues"]
    assert result["stageCount"] == 10
    assert "upload_media" in result["ungatedAllowedActions"]
    assert "add_domain" in result["coveredActions"]
    assert "add_tracking_tag" in result["coveredActions"]


def test_capture_plan_gate_coverage_rejects_unknown_action() -> None:
    plan = full_capture_plan_for_gate_coverage()
    plan["stages"][0]["authorizationAction"] = "launch_everything"
    result = validate_plan_gate_coverage(plan)
    assert result["ok"] is False
    assert any("unknown authorizationAction launch_everything" in issue for issue in result["issues"])
    assert any("not explicitly allowlisted" in issue for issue in result["issues"])


def test_capture_plan_gate_coverage_rejects_known_action_missing_gate() -> None:
    plan = full_capture_plan_for_gate_coverage()
    plan["stages"][0]["authorizationAction"] = "publish"
    result = validate_plan_gate_coverage(plan)
    assert result["ok"] is False
    assert any("missing field template for publish" in issue for issue in result["issues"])
    assert any("publish has no pre-mutation gate" in issue for issue in result["issues"])


def test_capture_plan_gate_coverage_allows_upload_media_only_by_allowlist() -> None:
    plan = full_capture_plan_for_gate_coverage()
    result = validate_plan_gate_coverage(plan, ungated_allowed_actions=set())
    assert result["ok"] is False
    assert any("upload_media has no pre-mutation gate" in issue for issue in result["issues"])


def draft_product_manifest() -> dict:
    return {
        "siteKey": "mysite03",
        "contentType": "products",
        "frontendBaseUrl": "https://mysite03.web.allincms.com",
        "schemaVerified": False,
        "fieldMapping": {
            "titleField": "name",
            "descriptionField": "description",
        },
        "items": [
            {
                "operation": "create",
                "name": "Codex Probe - Delete Me Sample Product",
                "slug": "codex-probe-delete-me-sample-product",
                "description": "Temporary local validation product.",
                "media": {
                    "url": "https://example.com/image.jpg",
                    "alt": "Temporary product validation image",
                },
                "categories": [],
                "tags": [],
                "specs": [],
                "content": [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Temporary local validation content."}],
                    }
                ],
            }
        ],
    }


def test_manifest_validator_allows_draft_manifest_without_schema_gate() -> None:
    errors = validate_manifest(draft_product_manifest())
    assert errors == [], errors


def test_manifest_validator_requires_schema_before_upload_gate() -> None:
    errors = validate_manifest(draft_product_manifest(), require_schema_verified=True)
    assert any("schemaVerified" in error for error in errors), errors
    assert any("payloadTemplate" in error for error in errors), errors


def test_manifest_validator_accepts_schema_verified_upload_manifest() -> None:
    manifest = draft_product_manifest()
    manifest["schemaVerified"] = True
    manifest["payloadTemplate"] = {
        "request": "captured server action payload shape placeholder",
        "contentType": "products",
    }
    errors = validate_manifest(manifest, require_schema_verified=True)
    assert errors == [], errors


def test_manifest_rehearsal_proves_draft_pass_and_schema_gate_failure() -> None:
    class Args:
        site_key = "simsite01"
        content_type = "products"
        frontend_base_url = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        paths = simulate_manifest_rehearsal.run_rehearsal(Args())
        summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
        assert summary["kind"] == "allincms_manifest_rehearsal_summary"
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["draftValidation"]["passed"] is True
        assert summary["schemaGate"]["passed"] is False
        assert summary["schemaGate"]["expectedFailure"] is True
        assert summary["sourceInputRequirements"]["operationGapCount"] == 1
        assert summary["sourceInputRequirements"]["operationGapBlockedFields"] == ["products.specifications"]
        source_requirements = json.loads(paths["sourceInputRequirements"].read_text(encoding="utf-8"))
        assert source_requirements["operationGaps"]["entryCount"] == 1
        validation = validate_manifest_rehearsal_summary(paths["summary"])
        assert validation["ok"] is True
        assert validation["draftValidationPassed"] is True
        assert validation["schemaGateExpectedFailure"] is True
        assert validation["sourceInputOperationGapCount"] == 1


def test_manifest_upload_readiness_report_blocks_draft_manifests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "products-draft-manifest.json"
        manifest_path.write_text(json.dumps(draft_product_manifest(), indent=2) + "\n", encoding="utf-8")

        report = build_manifest_upload_readiness_report([manifest_path])

    assert report["kind"] == "allincms_manifest_upload_readiness_report"
    assert report["remoteMutationsPerformed"] is False
    assert report["overallStatus"] == "blocked"
    assert report["readyCount"] == 0
    assert report["blockedCount"] == 1
    assert report["manifests"][0]["status"] == "blocked"
    assert "schema_gate_not_passed" in report["manifests"][0]["blockers"]
    assert "capture a live save request" in report["manifests"][0]["nextAction"]


def test_manifest_upload_readiness_report_marks_schema_verified_ready() -> None:
    manifest = draft_product_manifest()
    manifest["schemaVerified"] = True
    manifest["payloadTemplate"] = {
        "request": "captured server action payload shape placeholder",
        "contentType": "products",
    }

    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "products-schema-verified-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        report = build_manifest_upload_readiness_report([manifest_path])

    assert report["kind"] == "allincms_manifest_upload_readiness_report"
    assert report["overallStatus"] == "ready_for_sample_upload"
    assert report["readyCount"] == 1
    assert report["blockedCount"] == 0
    assert report["manifests"][0]["schemaGate"]["ok"] is True
    assert report["manifests"][0]["status"] == "ready_for_sample_upload"


def schema_verified_manifest_for_batch() -> dict:
    manifest = draft_product_manifest()
    manifest["siteKey"] = "mysite01"
    manifest["frontendBaseUrl"] = "https://mysite01.web.allincms.com"
    manifest["schemaVerified"] = True
    manifest["payloadTemplate"] = {
        "request": "captured server action payload shape placeholder",
        "contentType": "products",
        "mode": "update",
    }
    manifest["items"][0]["slug"] = "codex-probe-delete-me-sample-product"
    manifest["items"].append(
        {
            "operation": "create",
            "name": "Codex Probe - Delete Me Batch Product",
            "slug": "codex-probe-delete-me-batch-product",
            "description": "Temporary local validation product.",
            "media": {
                "url": "https://example.com/image-2.jpg",
                "alt": "Temporary product validation image",
            },
            "categories": [],
            "tags": [],
            "specs": [],
            "content": [{"type": "paragraph", "children": [{"text": "Temporary local validation content."}]}],
        }
    )
    return manifest


def valid_batch_progress_log() -> list[dict]:
    return [
        {
            "slug": "codex-probe-delete-me-sample-product",
            "contentType": "products",
            "operation": "create",
            "backendUrl": "https://workspace.laicms.com/mysite01/products/product-1/update",
            "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe-delete-me-sample-product",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverVerified": True,
            "bodyVerified": True,
            "errors": [],
        },
        {
            "slug": "codex-probe-delete-me-batch-product",
            "contentType": "products",
            "operation": "create",
            "backendUrl": "https://workspace.laicms.com/mysite01/products/product-2/update",
            "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe-delete-me-batch-product",
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverOrMediaVerified": True,
            "bodyVerified": True,
            "errors": [],
        },
    ]


def valid_batch_frontend_audit_reports() -> list[dict]:
    return [
        {
            "url": "/products/{slug}",
            "routeInstance": "products-detail-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "h2": 1, "h3": 0, "strong": 1, "b": 0, "code": 0, "pre": 0, "table": 0, "ul": 0, "ol": 0, "li": 0, "img": 1, "a": 2},
            "headings": {"h1": ["redacted-h1-1"], "h2": ["redacted-h2-1"], "h3": []},
            "imageCount": 1,
            "linkCount": 2,
            "issues": [],
        },
        {
            "url": "/products/{slug}",
            "routeInstance": "products-detail-2",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "h2": 1, "h3": 0, "strong": 0, "b": 0, "code": 0, "pre": 0, "table": 1, "ul": 0, "ol": 0, "li": 0, "img": 1, "a": 2},
            "headings": {"h1": ["redacted-h1-1"], "h2": ["redacted-h2-1"], "h3": []},
            "imageCount": 1,
            "linkCount": 2,
            "issues": [],
        },
    ]


def valid_batch_upload_publish_evidence() -> dict:
    return {
        "kind": "allincms_batch_upload_publish_evidence",
        "siteKey": "mysite01",
        "contentType": "products",
        "target": "https://workspace.laicms.com/mysite01/products",
        "manifestPath": "/tmp/products-schema-verified-manifest.json",
        "authorizationRecord": "/tmp/batch-auth.json",
        "preMutationGate": "passed",
        "action": "batch_upload",
        "schemaGatePass": True,
        "sampleVerificationPass": True,
        "progressLogComplete": True,
        "frontendDetailAuditPass": True,
        "progressLog": valid_batch_progress_log(),
        "frontendDetailAudit": {
            "checked": True,
            "detailRouteCount": 2,
            "markdownResidueChecked": True,
            "structuredRichTextChecked": True,
            "blockingIssues": [],
        },
        "stopConditionMet": True,
    }


def launch_ready_run_evidence() -> dict:
    data = created_site_evidence()
    site_key = data["siteIdentity"]["siteKey"]
    data["contentInspection"] = {
        "contentType": "products",
        "backendListUrl": f"https://workspace.laicms.com/{site_key}/products",
        "listColumns": ["Name", "Slug", "Description", "Status"],
        "editFields": ["name", "slug", "description", "content", "media"],
        "fieldMapping": {
            "nameField": "name",
            "slugField": "slug",
            "descriptionField": "description",
            "bodyField": "content",
            "mediaField": "media",
        },
    }
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/products", "/products/{slug}"],
        "expectedStatuses": {"/": 200, "/products": 200, "/products/{slug}": 200},
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    data["launchReadiness"] = {
        "checked": True,
        "themeActive": True,
        "pagesPublished": True,
        "pagesEnabled": True,
        "routesBound": True,
        "frontendHttpOk": True,
        "frontendDomVerified": True,
        "checkedPaths": ["/", "/products", "/products/{slug}"],
        "evidence": "redacted backend route/theme/page proof plus frontend DOM proof",
        "blockingIssues": [],
    }
    data["requestCapture"] = {
        "url": f"https://workspace.laicms.com/{site_key}/products/probe/update",
        "method": "POST",
        "headers": {"Accept": "text/x-component", "Content-Type": "text/plain;charset=UTF-8"},
        "payloadShape": {"name": "string", "slug": "string", "description": "string", "content": "blocks", "media": "object"},
        "contentBlockShape": "non-empty structured content blocks",
        "idFields": ["siteId", "productId"],
        "mode": "update",
        "publishBehavior": "publish is separate",
        "persistedVerified": True,
    }
    data["sampleVerification"] = {
        "backendVerified": True,
        "frontendVerified": True,
        "backendUrl": f"https://workspace.laicms.com/{site_key}/products/probe/update",
        "frontendUrl": f"https://{site_key}.web.allincms.com/products/probe",
        "status": "published",
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
        "renderAudit": {"issues": []},
    }
    data["cleanup"] = {"status": "not_needed", "candidates": []}
    return data


def launch_acceptance_args(**overrides: object) -> object:
    values = {
        "run_evidence": "/tmp/run-evidence.json",
        "module_coverage": "",
        "stage_coverage": "",
        "upload_readiness": "",
        "sample_evidence": [],
        "batch_evidence": "",
        "batch_validation": "",
        "forms_media_settings": "",
        "final_frontend_audit": "",
        "cleanup_evidence": "",
        "round_closeout": "",
        "require_created_site": True,
    }
    values.update(overrides)
    return type("Args", (), values)()


def launch_module_coverage() -> dict:
    return {"kind": "allincms_module_capture_coverage", "complete": True, "jsonReplayReady": True}


def launch_upload_readiness() -> dict:
    return {
        "kind": "allincms_manifest_upload_readiness_report",
        "overallStatus": "ready_for_sample_upload",
        "manifests": [
            {
                "path": "/tmp/products.json",
                "contentType": "products",
                "siteKey": "codex-test-site",
                "schemaVerified": True,
                "status": "ready_for_sample_upload",
                "schemaGate": {"ok": True, "errors": []},
            }
        ],
    }


def launch_forms_media_settings_out_of_scope() -> dict:
    return {
        "kind": "allincms_forms_media_settings_evidence",
        "status": "explicitly_out_of_scope",
        "deferrals": [
            {"module": "forms", "reason": "not required for this temporary launch"},
            {"module": "tracking", "reason": "tracking intentionally deferred"},
        ],
    }


def launch_forms_media_settings_mixed_verified_deferred() -> dict:
    return {
        "kind": "allincms_forms_media_settings_evidence",
        "status": "partially_verified_with_explicit_deferrals",
        "siteInfoVerified": True,
        "formsVerified": True,
        "mediaVerified": False,
        "domainsRecorded": True,
        "trackingRecorded": False,
        "deferrals": [
            {"module": "media", "reason": "media upload storage proof deferred for this demo scope"},
            {"module": "tracking", "reason": "Google Tag ID not supplied for this temporary site"},
        ],
    }


def launch_final_frontend_audit_result() -> dict:
    return {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "browserStageMutatedRemote": False,
        "stageId": "final_frontend_audit",
        "status": "completed",
        "proof": ["HTTP status report", "DOM/rich-text report", "image report", "broken-entry list empty"],
        "proofRecorded": ["HTTP status report", "DOM/rich-text report", "image report", "broken-entry list empty"],
        "blockers": [],
        "blockingIssues": [],
    }


def launch_final_frontend_audit_report() -> list[dict]:
    return [
        {
            "url": "https://codex-test-site.web.allincms.com/",
            "urlFingerprint": final_audit_url_fingerprint("https://codex-test-site.web.allincms.com/"),
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "img": 1},
            "headings": {"h1": ["redacted-h1-1"], "h2": [], "h3": []},
            "imageCount": 1,
            "linkCount": 2,
            "issues": [],
        },
        {
            "url": "https://codex-test-site.web.allincms.com/products/codex-probe-delete-me-batch-product",
            "urlFingerprint": final_audit_url_fingerprint(
                "https://codex-test-site.web.allincms.com/products/codex-probe-delete-me-batch-product"
            ),
            "routeInstance": "products-detail-1",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html",
            "tagCounts": {"h1": 1, "img": 1},
            "headings": {"h1": ["redacted-h1-1"], "h2": [], "h3": []},
            "imageCount": 1,
            "linkCount": 2,
            "issues": [],
        },
    ]


def launch_final_frontend_audit_inputs_summary() -> dict:
    return {
        "kind": "allincms_final_frontend_audit_inputs_summary",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "contentType": "products",
        "staticRouteCount": 1,
        "detailRouteCount": 1,
        "detailRouteInstances": ["products-detail-1"],
        "routePatterns": ["/", "/products/{slug}"],
        "expectedStatus": 200,
    }


def launch_final_frontend_expected_statuses() -> dict[str, int]:
    return {
        "https://codex-test-site.web.allincms.com/": 200,
        "https://codex-test-site.web.allincms.com/products/codex-probe-delete-me-batch-product": 200,
    }


def write_launch_final_frontend_audit(root: Path) -> str:
    report_path = write_json(root / "final-audit-report.json", launch_final_frontend_audit_report())
    summary_path = write_json(root / "final-audit-inputs-summary.json", launch_final_frontend_audit_inputs_summary())
    statuses_path = write_json(root / "final-expected-statuses.json", launch_final_frontend_expected_statuses())
    audit = launch_final_frontend_audit_result()
    audit["redactedEvidencePointers"] = [report_path]
    audit["auditReport"] = report_path
    audit["auditInputsSummary"] = summary_path
    audit["expectedStatuses"] = statuses_path
    return write_json(root / "final.json", audit)


def launch_cleanup_evidence() -> dict:
    return {
        "kind": "allincms_probe_cleanup_evidence",
        "status": "completed",
        "cleanedCount": 1,
        "cleanedCandidates": [
            {
                "contentType": "products",
                "titlePattern": "Codex Probe",
                "backendUrl": "https://workspace.laicms.com/codex-test-site/products/probe/update",
                "reason": "probe cleanup",
            }
        ],
        "backendVerified": True,
        "frontendVerified": True,
        "backendEvidence": "probe row absent or unpublished",
        "frontendEvidence": "probe detail 404",
    }


def launch_cleanup_absence_evidence() -> dict:
    return {
        "kind": "allincms_probe_cleanup_evidence",
        "status": "verified",
        "cleanedCount": 0,
        "cleanedCandidates": [],
        "noCandidatesVerified": True,
        "backendVerified": True,
        "frontendVerified": True,
        "scannedSurfaces": [
            "backend products list",
            "backend posts list",
            "backend forms list",
            "public home/products/posts/about/contact pages",
        ],
        "backendEvidence": "probe, Delete Me, and Untitled terms absent from backend list scan",
        "frontendEvidence": "probe, Delete Me, and Untitled terms absent from public route scan",
    }


def launch_round_closeout() -> dict:
    return {
        "kind": "allincms_source_run_final_closeout",
        "valid": True,
        "complete": True,
        "localOnly": False,
        "remoteMutationsPerformed": True,
        "completionGaps": [],
        "proof": ["launch frontend audit and cleanup proof recorded"],
        "sedimentation": {"status": "updated", "note": "Recorded launch acceptance proof."},
    }


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def test_batch_upload_publish_runbook_builds_safe_browser_steps() -> None:
    runbook = build_batch_upload_publish_runbook(
        run_evidence=batch_ready_evidence(),
        run_evidence_path="/tmp/batch-ready-run-evidence.json",
        manifest=schema_verified_manifest_for_batch(),
        manifest_path="/tmp/products-schema-verified-manifest.json",
        authorization_output="/tmp/batch-auth.json",
        target="https://workspace.laicms.com/mysite01/products",
        target_identifier="products manifest batch",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    errors = validate_batch_upload_publish_runbook(runbook)
    assert errors == [], errors
    assert runbook["browserStepsExecutable"] is False
    assert runbook["authorizationRequired"] is True
    assert "--action batch_upload" in runbook["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in runbook["authorizationRecordCommand"]
    assert "deleting or cleaning probe/test items" in runbook["forbiddenActions"]


def test_batch_upload_publish_evidence_validator_accepts_complete_redacted_evidence() -> None:
    errors = validate_batch_upload_publish_evidence(
        valid_batch_upload_publish_evidence(),
        manifest=schema_verified_manifest_for_batch(),
        base_run_evidence=batch_ready_evidence(),
        audit_reports=valid_batch_frontend_audit_reports(),
    )
    assert errors == [], errors


def test_batch_upload_publish_evidence_validator_rejects_missing_slug_progress() -> None:
    evidence = valid_batch_upload_publish_evidence()
    evidence["progressLog"] = evidence["progressLog"][:1]
    errors = validate_batch_upload_publish_evidence(
        evidence,
        manifest=schema_verified_manifest_for_batch(),
        base_run_evidence=batch_ready_evidence(),
        audit_reports=valid_batch_frontend_audit_reports(),
    )
    assert any("progress" in error and "missing" in error for error in errors), errors


def test_batch_upload_publish_evidence_validator_rejects_frontend_audit_issue() -> None:
    reports = valid_batch_frontend_audit_reports()
    reports[0]["issues"] = [{"severity": "error", "code": "literal_bold", "message": "redacted"}]
    errors = validate_batch_upload_publish_evidence(
        valid_batch_upload_publish_evidence(),
        manifest=schema_verified_manifest_for_batch(),
        base_run_evidence=batch_ready_evidence(),
        audit_reports=reports,
    )
    assert any("issues must be empty" in error for error in errors), errors


def test_launch_acceptance_rejects_local_stage_coverage_as_live_completion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_path = write_json(root / "run.json", launch_ready_run_evidence())
        stage_path = write_json(
            root / "stage-coverage.json",
            {
                "kind": "allincms_rehearsal_stage_coverage_summary",
                "moduleInterfaceCapture": {"completionCovered": True},
            },
        )
        upload_path = write_json(root / "upload.json", launch_upload_readiness())
        batch_path = write_json(root / "batch.json", valid_batch_upload_publish_evidence() | {"siteKey": "codex-test-site"})
        sample_path = write_json(root / "sample.json", valid_manifest_sample_upload_evidence())
        batch_validation_path = write_json(root / "batch-validation.json", {"valid": True, "contentType": "products"})
        forms_path = write_json(root / "forms.json", launch_forms_media_settings_out_of_scope())
        final_path = write_launch_final_frontend_audit(root)
        cleanup_path = write_json(root / "cleanup.json", launch_cleanup_evidence())
        closeout_path = write_json(root / "closeout.json", launch_round_closeout())

        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=run_path,
                stage_coverage=stage_path,
                upload_readiness=upload_path,
                sample_evidence=[sample_path],
                batch_evidence=batch_path,
                batch_validation=batch_validation_path,
                forms_media_settings=forms_path,
                final_frontend_audit=final_path,
                cleanup_evidence=cleanup_path,
                round_closeout=closeout_path,
            )
        )

    assert report["valid"] is False
    module_item = next(item for item in report["items"] if item["key"] == "module_interface_capture_complete")
    assert module_item["status"] == "blocked"
    assert "local rehearsal evidence only" in module_item["blockers"][0]


def test_launch_acceptance_blocks_missing_batch_forms_final_qa_and_cleanup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_path = write_json(root / "run.json", launch_ready_run_evidence())
        module_path = write_json(root / "module.json", launch_module_coverage())
        upload_path = write_json(root / "upload.json", launch_upload_readiness())
        closeout_path = write_json(root / "closeout.json", launch_round_closeout())

        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=run_path,
                module_coverage=module_path,
                upload_readiness=upload_path,
                round_closeout=closeout_path,
            )
        )

    blocked_keys = {item["key"] for item in report["blocked"]}
    assert "batch_upload_publish_verified" in blocked_keys
    assert "forms_media_settings_verified_or_explicitly_out_of_scope" in blocked_keys
    assert "final_frontend_audit_passed" in blocked_keys
    assert "probe_cleanup_completed" in blocked_keys
    assert report["complete"] is False


def test_launch_acceptance_accepts_complete_redacted_launch_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_path = write_json(root / "run.json", launch_ready_run_evidence())
        module_path = write_json(root / "module.json", launch_module_coverage())
        upload_path = write_json(root / "upload.json", launch_upload_readiness())
        batch = valid_batch_upload_publish_evidence()
        batch["siteKey"] = "codex-test-site"
        batch["target"] = "https://workspace.laicms.com/codex-test-site/products"
        for entry in batch["progressLog"]:
            entry["backendUrl"] = entry["backendUrl"].replace("mysite01", "codex-test-site")
            entry["frontendUrl"] = entry["frontendUrl"].replace("mysite01", "codex-test-site")
        batch_path = write_json(root / "batch.json", batch)
        sample_path = write_json(root / "sample.json", valid_manifest_sample_upload_evidence())
        batch_validation_path = write_json(root / "batch-validation.json", {"valid": True, "contentType": "products"})
        forms_path = write_json(root / "forms.json", launch_forms_media_settings_out_of_scope())
        final_path = write_launch_final_frontend_audit(root)
        cleanup_path = write_json(root / "cleanup.json", launch_cleanup_evidence())
        closeout_path = write_json(root / "closeout.json", launch_round_closeout())

        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=run_path,
                module_coverage=module_path,
                upload_readiness=upload_path,
                sample_evidence=[sample_path],
                batch_evidence=batch_path,
                batch_validation=batch_validation_path,
                forms_media_settings=forms_path,
                final_frontend_audit=final_path,
                cleanup_evidence=cleanup_path,
                round_closeout=closeout_path,
            )
        )

    assert report["valid"] is True
    assert report["complete"] is True
    assert set(report["checkedAcceptanceKeys"]).issubset(set(report["passed"]))


def test_launch_acceptance_accepts_mixed_forms_media_settings_deferrals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=write_json(root / "run.json", launch_ready_run_evidence()),
                module_coverage=write_json(root / "module.json", launch_module_coverage()),
                upload_readiness=write_json(root / "upload.json", launch_upload_readiness()),
                sample_evidence=[write_json(root / "sample.json", valid_manifest_sample_upload_evidence())],
                batch_evidence=write_json(root / "batch.json", valid_batch_upload_publish_evidence()),
                batch_validation=write_json(root / "batch-validation.json", {"valid": True, "contentType": "products"}),
                forms_media_settings=write_json(
                    root / "forms.json",
                    launch_forms_media_settings_mixed_verified_deferred(),
                ),
                final_frontend_audit=write_launch_final_frontend_audit(root),
                cleanup_evidence=write_json(root / "cleanup.json", launch_cleanup_evidence()),
                round_closeout=write_json(root / "closeout.json", launch_round_closeout()),
            )
        )

    assert report["valid"] is True
    item = next(item for item in report["items"] if item["key"] == "forms_media_settings_verified_or_explicitly_out_of_scope")
    assert item["status"] == "passed"
    assert item["details"] == "mixed verified/deferred"


def test_launch_acceptance_accepts_cleanup_absence_scan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=write_json(root / "run.json", launch_ready_run_evidence()),
                module_coverage=write_json(root / "module.json", launch_module_coverage()),
                upload_readiness=write_json(root / "upload.json", launch_upload_readiness()),
                sample_evidence=[write_json(root / "sample.json", valid_manifest_sample_upload_evidence())],
                batch_evidence=write_json(root / "batch.json", valid_batch_upload_publish_evidence()),
                batch_validation=write_json(root / "batch-validation.json", {"valid": True, "contentType": "products"}),
                forms_media_settings=write_json(root / "forms.json", launch_forms_media_settings_out_of_scope()),
                final_frontend_audit=write_launch_final_frontend_audit(root),
                cleanup_evidence=write_json(root / "cleanup.json", launch_cleanup_absence_evidence()),
                round_closeout=write_json(root / "closeout.json", launch_round_closeout()),
            )
        )

    assert report["valid"] is True
    item = next(item for item in report["items"] if item["key"] == "probe_cleanup_completed")
    assert item["status"] == "passed"


def test_launch_acceptance_accepts_merged_probe_evidence_shapes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run = launch_ready_run_evidence()
        run["requestCapture"]["headers"] = "Accept, Content-Type, next-action"
        run["requestCapture"]["payloadShape"] = json.dumps(
            {"name": "string", "slug": "string", "siteId": "redacted-id", "productId": "redacted-id", "mode": "update"}
        )
        run["requestCapture"]["idFields"] = "siteId and productId present; values redacted"
        run["requestCapture"]["publishBehavior"] = "publish-separate"
        run["sampleVerification"]["status"] = "已发布"
        run["sampleVerification"]["renderAudit"] = "HTTP 200; no visible Markdown residue"
        report = build_launch_acceptance_report(
            launch_acceptance_args(
                run_evidence=write_json(root / "run.json", run),
                module_coverage=write_json(root / "module.json", launch_module_coverage()),
                upload_readiness=write_json(root / "upload.json", launch_upload_readiness()),
                sample_evidence=[write_json(root / "sample.json", valid_manifest_sample_upload_evidence())],
                batch_evidence=write_json(root / "batch.json", valid_batch_upload_publish_evidence()),
                batch_validation=write_json(root / "batch-validation.json", {"valid": True, "contentType": "products"}),
                forms_media_settings=write_json(root / "forms.json", launch_forms_media_settings_out_of_scope()),
                final_frontend_audit=write_launch_final_frontend_audit(root),
                cleanup_evidence=write_json(root / "cleanup.json", launch_cleanup_evidence()),
                round_closeout=write_json(root / "closeout.json", launch_round_closeout()),
            )
        )

    assert report["valid"] is True
    request_item = next(item for item in report["items"] if item["key"] == "content_type_save_request_captured_and_persisted")
    sample_item = next(item for item in report["items"] if item["key"] == "sample_backend_frontend_verified")
    assert request_item["status"] == "passed"
    assert sample_item["status"] == "passed"


def test_run_status_summary_marks_read_only_launch_as_incomplete() -> None:
    data = existing_site_selected_evidence()
    data["generatedAt"] = RECENT_PREFLIGHT_AT
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    summary = summarize_run_status(data, max_mutation_evidence_age_minutes=9999999)
    assert summary["valid"] is True
    assert summary["complete"] is False
    assert "static_frontend_routes_render" in summary["proven"]
    assert "upload_not_in_scope" in summary["missing"]
    assert "request_capture_persisted_verified" in summary["completionGaps"]
    assert "sample_backend_frontend_verified" in summary["completionGaps"]
    assert "cleanup_completed" in summary["completionGaps"]
    assert "authorize_content_probe" in summary["nextActions"]
    assert summary["nextActionDetails"], summary
    detail = summary["nextActionDetails"][0]
    assert detail["action"] == "create_product_probe"
    assert detail["target"] == "https://workspace.laicms.com/mysite01/products"
    assert "Codex Probe - Delete Me" in detail["authorizationText"]
    assert "https://workspace.laicms.com/mysite01/products" in detail["authorizationText"]
    assert "产品" in detail["authorizationText"]
    assert "check_pre_mutation_gate.py --action create_product_probe" in detail["preMutationGateCommand"]
    assert "make_authorization_record.py --action create_product_probe" in detail["authorizationRecordCommand"]


def test_run_status_summary_proves_theme_route_launch_readiness_separately() -> None:
    data = existing_site_selected_evidence()
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    data["launchReadiness"] = {
        "checked": True,
        "themeActive": True,
        "pagesPublished": True,
        "pagesEnabled": True,
        "routesBound": True,
        "frontendHttpOk": True,
        "frontendDomVerified": True,
        "checkedPaths": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us"],
        "evidence": "theme row active, page rows published/enabled, routes bound, frontend DOM audited",
        "blockingIssues": [],
    }
    assert_valid(data)
    summary = summarize_run_status(data)
    assert summary["valid"] is True
    assert "theme_route_launch_ready" in summary["proven"]
    assert "request_capture_persisted_verified" in summary["completionGaps"]
    assert "sample_backend_frontend_verified" in summary["completionGaps"]


def test_run_evidence_rejects_partial_launch_readiness() -> None:
    data = existing_site_selected_evidence()
    data["launchReadiness"] = {
        "checked": True,
        "themeActive": True,
        "pagesPublished": True,
        "pagesEnabled": True,
        "routesBound": False,
        "frontendHttpOk": True,
        "frontendDomVerified": True,
        "checkedPaths": ["/", "/home"],
        "evidence": "theme active but one route remains unbound",
        "blockingIssues": [{"routePattern": "/home", "code": "route_unbound", "evidence": "route row not bound"}],
    }
    assert_invalid_contains(data, "launchReadiness.routesBound")
    summary = summarize_run_status(data)
    assert "theme_route_launch_ready" not in summary["proven"]
    assert "theme_route_launch_readiness" in summary["missing"]


def test_launch_readiness_builder_outputs_valid_all_true_evidence() -> None:
    launch = build_launch_readiness_evidence(
        theme_active=True,
        pages_published=True,
        pages_enabled=True,
        routes_bound=True,
        frontend_http_ok=True,
        frontend_dom_verified=True,
        checked_paths=parse_checked_paths("/,/home,/products"),
        evidence="theme active, page rows published and enabled, routes bound, frontend audited",
        blocking_issues=[],
    )["launchReadiness"]
    data = existing_site_selected_evidence()
    data["launchReadiness"] = launch
    assert_valid(data)


def test_launch_readiness_builder_rejects_partial_without_blocker() -> None:
    try:
        build_launch_readiness_evidence(
            theme_active=True,
            pages_published=True,
            pages_enabled=True,
            routes_bound=False,
            frontend_http_ok=True,
            frontend_dom_verified=True,
            checked_paths=parse_checked_paths("/,/home"),
            evidence="route state was checked",
            blocking_issues=[],
        )
    except ValueError as exc:
        assert "requires at least one blocking issue" in str(exc)
    else:
        raise AssertionError("partial launch readiness without blocker was accepted")


def test_launch_readiness_builder_partial_with_blocker_is_not_launch_ready_evidence() -> None:
    launch = build_launch_readiness_evidence(
        theme_active=True,
        pages_published=True,
        pages_enabled=True,
        routes_bound=False,
        frontend_http_ok=True,
        frontend_dom_verified=True,
        checked_paths=parse_checked_paths("/,/home"),
        evidence="route state was checked and one route remains unbound",
        blocking_issues=parse_blocking_issues("/home|route_unbound|route row not bound"),
    )["launchReadiness"]
    data = existing_site_selected_evidence()
    data["launchReadiness"] = launch
    assert_invalid_contains(data, "launchReadiness.routesBound")


def test_launch_readiness_builder_rejects_concrete_slug_path() -> None:
    try:
        parse_checked_paths("/products/codex-probe-delete-me")
    except ValueError as exc:
        assert "concrete slug" in str(exc)
    else:
        raise AssertionError("concrete launch readiness path was accepted")


def test_run_status_summary_requires_full_completion_proof() -> None:
    data = existing_site_selected_evidence()
    data["completionClaimed"] = True
    data["uploadInScope"] = True
    data["localChecks"]["repoCheckPassed"] = True
    data["localChecks"].pop("repoCheckNote", None)
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 200,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    data["requestCapture"] = {
        "url": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "method": "POST",
        "headers": "Accept, Content-Type, next-action",
        "payloadShape": "redacted server action payload",
        "contentBlockShape": "structured rich text blocks",
        "idFields": "siteId, productId",
        "mode": "update",
        "publishBehavior": "publish separate",
        "persistedVerified": True,
    }
    data["sampleVerification"] = {
        "backendVerified": True,
        "frontendVerified": True,
        "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe",
        "status": "published",
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
        "renderAudit": "no markdown residue, structured rich text and media verified",
    }
    data["cleanup"] = {
        "status": "completed",
        "cleanedCount": 1,
        "cleanedCandidates": [
            {
                "contentType": "products",
                "titlePattern": "Codex Probe - Delete Me product draft",
                "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
                "reason": "probe cleanup",
            }
        ],
        "backendVerified": True,
        "frontendVerified": True,
        "backendEvidence": "probe product absent from products list",
        "frontendEvidence": "probe product frontend detail returned 404",
    }
    data["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": "create product probe, save sample, publish sample, and cleanup probe",
        "target": "https://workspace.laicms.com/mysite01/products",
        "authorizationSource": "current user explicitly authorizes product probe upload, publish, and cleanup at https://workspace.laicms.com/mysite01/products",
        "verificationPlan": "verify backend product state, frontend detail page, and cleanup result",
    }
    summary = summarize_run_status(data)
    assert summary["valid"] is True
    assert summary["complete"] is True
    assert summary["completionGaps"] == []
    assert "request_capture_persisted_verified" in summary["proven"]
    assert "sample_backend_frontend_verified" in summary["proven"]
    assert "cleanup_completed" in summary["proven"]


def test_run_status_summary_can_require_created_site_for_from_scratch_goal() -> None:
    data = existing_site_selected_evidence()
    data["completionClaimed"] = True
    data["uploadInScope"] = True
    data["localChecks"]["repoCheckPassed"] = True
    data["localChecks"].pop("repoCheckNote", None)
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 200,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    data["requestCapture"] = {
        "url": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "method": "POST",
        "headers": "Accept, Content-Type, next-action",
        "payloadShape": "redacted server action payload",
        "contentBlockShape": "structured rich text blocks",
        "idFields": "siteId, productId",
        "mode": "update",
        "publishBehavior": "publish separate",
        "persistedVerified": True,
    }
    data["sampleVerification"] = {
        "backendVerified": True,
        "frontendVerified": True,
        "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe",
        "status": "published",
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
        "renderAudit": "no markdown residue, structured rich text and media verified",
    }
    data["cleanup"] = {
        "status": "completed",
        "cleanedCount": 1,
        "cleanedCandidates": [
            {
                "contentType": "products",
                "titlePattern": "Codex Probe - Delete Me product draft",
                "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
                "reason": "probe cleanup",
            }
        ],
        "backendVerified": True,
        "frontendVerified": True,
        "backendEvidence": "probe product absent from products list",
        "frontendEvidence": "probe product frontend detail returned 404",
    }
    data["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": "create product probe, save sample, publish sample, and cleanup probe",
        "target": "https://workspace.laicms.com/mysite01/products",
        "authorizationSource": "current user explicitly authorizes product probe upload, publish, and cleanup at https://workspace.laicms.com/mysite01/products",
        "verificationPlan": "verify backend product state, frontend detail page, and cleanup result",
    }
    summary = summarize_run_status(data, require_created_site=True)
    assert summary["valid"] is True
    assert summary["complete"] is False
    assert summary["requireCreatedSite"] is True
    assert "existing_site_selected" in summary["proven"]
    assert "site_created_and_verified" in summary["completionGaps"]
    assert summary["requiredForCompletion"][0] == "site_created_and_verified"


def test_run_status_summary_does_not_overclaim_partial_static_launch() -> None:
    data = existing_site_selected_evidence()
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    summary = summarize_run_status(data)
    assert summary["valid"] is True
    assert summary["complete"] is False
    assert "static_frontend_routes_render" not in summary["proven"]
    assert "static_frontend_routes_clean_audit" in summary["missing"]
    assert "content_detail_sample_200" in summary["missing"]


def test_run_status_summary_accepts_content_type_specific_static_routes() -> None:
    data = created_site_evidence()
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/products", "/about-us", "/contact-us"],
        "expectedStatuses": {
            "/": 200,
            "/products": 200,
            "/about-us": 200,
            "/contact-us": 200,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    summary = summarize_run_status(data, require_created_site=True)
    assert summary["valid"] is True
    assert "static_frontend_routes_render" in summary["proven"]
    assert "static_frontend_routes_clean_audit" not in summary["missing"]
    assert "request_capture_persisted_verified" in summary["completionGaps"]


def test_run_status_summary_rejects_wrong_content_type_static_list_route() -> None:
    data = existing_site_selected_evidence()
    data["contentInspection"]["contentType"] = "posts"
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/products", "/about-us", "/contact-us"],
        "expectedStatuses": {
            "/": 200,
            "/products": 200,
            "/about-us": 200,
            "/contact-us": 200,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    summary = summarize_run_status(data)
    assert summary["valid"] is True
    assert "static_frontend_routes_render" not in summary["proven"]
    assert "static_frontend_routes_clean_audit" in summary["missing"]


def test_run_status_summary_matches_detail_probe_to_content_type() -> None:
    data = existing_site_selected_evidence()
    data["contentInspection"]["contentType"] = "posts"
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    summary = summarize_run_status(data)
    assert summary["valid"] is True
    assert "static_frontend_routes_render" not in summary["proven"]
    assert "static_frontend_routes_clean_audit" in summary["missing"]
    assert "content_detail_probe_routes_absent_or_unverified" not in summary["proven"]
    assert "content_detail_sample_200" not in summary["missing"]
    assert "authorize_content_probe" not in summary["nextActions"]


def test_run_status_summary_includes_create_site_next_action_details() -> None:
    summary = summarize_run_status(
        create_preflight_evidence(),
        "/tmp/allincms-create-site-preflight.json",
        max_mutation_evidence_age_minutes=9999999,
    )
    assert summary["valid"] is True
    assert summary["complete"] is False
    assert "create_site_preflight_verified" in summary["proven"]
    assert "real_create_site_submit" in summary["missing"]
    assert "authorize_create_site" in summary["nextActions"]
    assert summary["nextActionDetails"], summary
    detail = summary["nextActionDetails"][0]
    assert detail["action"] == "create_site"
    assert detail["target"] == "https://workspace.laicms.com/sites"
    assert "创建站点" in detail["authorizationText"]
    assert "https://workspace.laicms.com/sites" in detail["authorizationText"]
    assert "make_authorization_record.py --action create_site" in detail["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_site" in detail["preMutationGateCommand"]
    assert "--preflight /tmp/allincms-create-site-preflight.json" in detail["preMutationGateCommand"]


def test_run_status_summary_warns_when_mutation_evidence_is_stale() -> None:
    summary = summarize_run_status(create_preflight_evidence(), "/tmp/allincms-create-site-preflight.json")
    assert summary["evidenceFreshness"]["freshForMutation"] is False
    assert summary["nextActions"][0] == "refresh_readonly_evidence"
    assert summary["nextActionDetails"][0]["action"] == "refresh_readonly_evidence"


def mutating_probe_evidence_without_request_capture() -> dict:
    data = existing_site_selected_evidence()
    data["mode"] = "mutating_probe"
    data["uploadInScope"] = True
    data["generatedAt"] = RECENT_PREFLIGHT_AT
    data["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": "create product probe and save sample content",
        "target": "https://workspace.laicms.com/mysite01/products",
        "authorizationSource": "current user explicitly authorizes product probe work at https://workspace.laicms.com/mysite01/products",
        "verificationPlan": "verify backend product state and frontend detail page when published",
    }
    data["frontendRendering"] = {
        "checked": True,
        "routePatterns": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us", "/products/{slug}"],
        "expectedStatuses": {
            "/": 200,
            "/home": 200,
            "/products": 200,
            "/solutions": 200,
            "/about-us": 200,
            "/contact-us": 200,
            "/products/{slug}": 404,
        },
        "markdownResidueChecked": True,
        "structuredRichTextChecked": True,
        "blockingIssues": [],
    }
    return data


def mutating_probe_evidence_with_request_capture() -> dict:
    data = mutating_probe_evidence_without_request_capture()
    data["requestCapture"] = {
        "url": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "method": "POST",
        "headers": "Accept, Content-Type, next-action",
        "payloadShape": "redacted server action payload",
        "contentBlockShape": "structured rich text blocks",
        "idFields": "siteId, productId",
        "mode": "update",
        "publishBehavior": "publish separate",
        "persistedVerified": True,
    }
    return data


def mutating_probe_evidence_with_sample_verification() -> dict:
    data = mutating_probe_evidence_with_request_capture()
    data["sampleVerification"] = {
        "backendVerified": True,
        "frontendVerified": True,
        "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe",
        "status": "published",
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
        "renderAudit": "no markdown residue, structured rich text and media verified",
    }
    data["cleanup"] = {
        "status": "pending_user_authorization",
        "candidates": ["Codex Probe - Delete Me product draft"],
    }
    return data


def probe_merge_args(**overrides):
    class Args:
        request_capture = False
        url = None
        method = None
        headers = None
        payloadShape = None
        contentBlockShape = None
        idFields = None
        mode = None
        publishBehavior = None
        sample_verification = False
        backendUrl = None
        frontendUrl = None
        status = None
        renderAudit = None
        cleanup_completed = False
        cleaned_candidates = ""
        cleanup_backend_evidence = ""
        cleanup_frontend_evidence = ""

    args = Args()
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_probe_evidence_merge_adds_valid_request_capture() -> None:
    data = existing_site_selected_evidence()
    merged = merge_probe_evidence(
        data,
        probe_merge_args(
            request_capture=True,
            url="https://workspace.laicms.com/mysite01/products/product-id/update",
            method="POST",
            headers="Accept, Content-Type, next-action",
            payloadShape="redacted server action payload",
            contentBlockShape="structured rich text blocks",
            idFields="siteId, productId",
            mode="update",
            publishBehavior="publish separate",
        ),
    )
    assert merged["uploadInScope"] is True
    assert merged["requestCapture"]["persistedVerified"] is True
    summary = summarize_run_status(merged)
    assert "request_capture_persisted_verified" in summary["proven"]
    assert "sample_backend_frontend_verified" in summary["completionGaps"]
    assert "authorize_publish_probe" in summary["nextActions"]


def test_created_site_can_carry_probe_authorization_history() -> None:
    data = created_site_evidence()
    data["mode"] = "mutating_probe"
    merged = merge_probe_evidence(
        data,
        probe_merge_args(
            request_capture=True,
            url="https://workspace.laicms.com/codex-test-site/products/product-id/update",
            method="POST",
            headers="Accept, Content-Type, next-action",
            payloadShape="redacted server action payload",
            contentBlockShape="structured rich text blocks",
            idFields="siteId, productId",
            mode="update",
            publishBehavior="publish separate",
        ),
    )

    assert merged["authorization"]["authorizedAction"] == "create site"
    assert any(
        "probe" in entry["authorizedAction"] or "save" in entry["authorizedAction"]
        for entry in merged["authorizationHistory"]
    )
    errors = validate(merged)
    assert any("sampleVerification: required object when upload is in scope" in error for error in errors), errors
    summary = summarize_run_status(merged)
    assert "authorize_publish_probe" in summary["nextActions"]


def test_probe_evidence_merge_adds_valid_sample_verification() -> None:
    data = mutating_probe_evidence_with_request_capture()
    merged = merge_probe_evidence(
        data,
        probe_merge_args(
            sample_verification=True,
            backendUrl="https://workspace.laicms.com/mysite01/products/product-id/update",
            frontendUrl="https://mysite01.web.allincms.com/products/codex-probe",
            status="published",
            renderAudit="no markdown residue, structured rich text and media verified",
        ),
    )
    assert merged["sampleVerification"]["frontendVerified"] is True
    assert_valid(merged)


def test_probe_evidence_merge_adds_valid_cleanup() -> None:
    data = mutating_probe_evidence_with_sample_verification()
    merged = merge_probe_evidence(
        data,
        probe_merge_args(
            cleanup_completed=True,
            cleaned_candidates="products|Codex Probe - Delete Me|https://workspace.laicms.com/mysite01/products/product-id/update|probe cleanup",
            cleanup_backend_evidence="backend product list no longer shows Codex Probe - Delete Me",
            cleanup_frontend_evidence="frontend probe detail returns 404",
        ),
    )
    assert merged["cleanup"]["status"] == "completed"
    assert_valid(merged)
    summary = summarize_run_status(merged)
    assert "cleanup_completed" in summary["proven"]


def test_probe_evidence_merge_rejects_wrong_site_url() -> None:
    data = existing_site_selected_evidence()
    try:
        merge_probe_evidence(
            data,
            probe_merge_args(
                request_capture=True,
                url="https://workspace.laicms.com/othersite/products/product-id/update",
                method="POST",
                headers="Accept, Content-Type, next-action",
                payloadShape="redacted server action payload",
                contentBlockShape="structured rich text blocks",
                idFields="siteId, productId",
                mode="update",
                publishBehavior="publish separate",
            ),
        )
    except ValueError as exc:
        assert "siteKey mysite01" in str(exc)
    else:
        raise AssertionError("wrong-site request URL was accepted")


def test_run_status_summary_suggests_save_probe_after_probe_creation() -> None:
    summary = summarize_run_status(
        mutating_probe_evidence_without_request_capture(),
        "/tmp/preflight.json",
        max_mutation_evidence_age_minutes=9999999,
    )
    assert summary["valid"] is False
    assert "authorize_save_probe" in summary["nextActions"]
    assert "authorize_content_probe" not in summary["nextActions"]
    detail = summary["nextActionDetails"][0]
    assert detail["action"] == "save_probe"
    assert detail["target"] == "https://workspace.laicms.com/mysite01/products"
    assert "保存" in detail["authorizationText"]
    assert "捕获" in detail["authorizationText"]
    assert "make_authorization_record.py --action save_probe" in detail["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action save_probe" in detail["preMutationGateCommand"]
    assert "--preflight /tmp/preflight.json" in detail["preMutationGateCommand"]


def test_run_status_summary_suggests_publish_probe_after_request_capture() -> None:
    summary = summarize_run_status(
        mutating_probe_evidence_with_request_capture(),
        "/tmp/preflight.json",
        max_mutation_evidence_age_minutes=9999999,
    )
    assert summary["valid"] is False
    assert "request_capture_persisted_verified" in summary["proven"]
    assert "authorize_publish_probe" in summary["nextActions"]
    assert "authorize_save_probe" not in summary["nextActions"]
    detail = summary["nextActionDetails"][0]
    assert detail["action"] == "publish_probe"
    assert detail["target"] == "https://workspace.laicms.com/mysite01/products/product-id/update"
    assert "发布" in detail["authorizationText"]
    assert "frontendVerified" in detail["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action publish_probe" in detail["preMutationGateCommand"]


def test_run_status_summary_suggests_cleanup_probe_after_sample_verification() -> None:
    summary = summarize_run_status(
        mutating_probe_evidence_with_sample_verification(),
        "/tmp/preflight.json",
        max_mutation_evidence_age_minutes=9999999,
    )
    assert summary["valid"] is True
    assert "sample_backend_frontend_verified" in summary["proven"]
    assert "authorize_cleanup_probe" in summary["nextActions"]
    assert "authorize_publish_probe" not in summary["nextActions"]
    detail = summary["nextActionDetails"][0]
    assert detail["action"] == "cleanup_probe"
    assert detail["target"] == "https://workspace.laicms.com/mysite01/products/product-id/update"
    assert "清理" in detail["authorizationText"]
    assert "cleanedCandidates" in detail["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action cleanup_probe" in detail["preMutationGateCommand"]


def minimal_valid_summary() -> dict:
    return {
        "valid": True,
        "complete": False,
        "siteKey": "mysite01",
        "contentType": "products",
        "evidenceFreshness": {"freshForMutation": True},
        "proven": ["existing_site_selected"],
        "missing": ["content_detail_sample_200"],
        "completionGaps": ["request_capture_persisted_verified"],
        "nextActions": ["authorize_content_probe"],
    }


def summary_with_product_probe_next_action() -> dict:
    summary = minimal_valid_summary()
    summary["nextActionDetails"] = [
        {
            "action": "create_product_probe",
            "target": "https://workspace.laicms.com/mysite01/products",
            "authorizationText": (
                "授权 Codex 在 https://workspace.laicms.com/mysite01/products "
                "创建一个 Codex Probe - Delete Me 产品草稿，用于捕获产品字段和保存请求；"
                "本次只允许创建 probe 草稿，不发布、不删除、不批量上传，保存和清理另行授权。"
            ),
            "authorizationRecordCommand": (
                "python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py "
                "--action create_product_probe --site-key mysite01 "
                "--target https://workspace.laicms.com/mysite01/products "
                "--target-type products --target-identifier 'Codex Probe - Delete Me product draft' "
                "--fields-or-files 'name,slug,description,content,media' "
                "--expected-result 'temporary product probe draft opens for request capture' "
                "--verification-plan 'verify backend product draft and capture save request before any publish' "
                "--cleanup-plan 'no automatic cleanup; request separate cleanup authorization' "
                "--authorization-source '<paste current user authorization text here>' "
                "--output /tmp/allincms-mysite01-products-probe-authorization.json"
            ),
            "preMutationGateCommand": (
                "python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py "
                "--action create_product_probe --preflight /tmp/preflight.json "
                "--authorization /tmp/allincms-mysite01-products-probe-authorization.json"
            ),
        }
    ]
    return summary


def test_next_action_authorization_package_is_preparatory_only() -> None:
    summary = summary_with_product_probe_next_action()
    detail = select_next_action_authorization_detail(summary, "create_product_probe")
    package = build_next_action_authorization_package(summary, detail, "/tmp/preflight.json")
    assert package["preparedOnly"] is True
    assert package["isUserAuthorization"] is False
    assert package["action"] == "create_product_probe"
    assert package["target"] == "https://workspace.laicms.com/mysite01/products"
    assert package["authorizationTextToRequest"] == detail["authorizationText"]
    assert package["authorizationRecordCommandHasPlaceholder"] is True
    assert validate_next_action_authorization_package(package) == []


def test_next_action_authorization_package_requires_placeholder() -> None:
    summary = summary_with_product_probe_next_action()
    detail = select_next_action_authorization_detail(summary, "create_product_probe")
    detail["authorizationRecordCommand"] = detail["authorizationRecordCommand"].replace(
        "<paste current user authorization text here>",
        "current user authorizes create product probe",
    )
    package = build_next_action_authorization_package(summary, detail, "/tmp/preflight.json")
    issues = validate_next_action_authorization_package(package)
    assert any("placeholder" in issue for issue in issues)


def test_round_closeout_accepts_skill_update_with_changed_files() -> None:
    result = validate_closeout(
        minimal_valid_summary(),
        "updated",
        "Recorded reusable scan redaction finding in operational-findings.md.",
        ["skills/allincms-bulk-content-upload/references/operational-findings.md"],
        Path("skills/allincms-bulk-content-upload"),
        ["Recorded reusable scan redaction finding."],
    )
    assert result["ok"] is True


def test_round_closeout_rejects_changed_files_without_updated_sedimentation() -> None:
    result = validate_closeout(
        minimal_valid_summary(),
        "none",
        "no reusable skill update needed after checking",
        ["skills/allincms-bulk-content-upload/SKILL.md"],
        Path("skills/allincms-bulk-content-upload"),
        ["Checked the turn and found no reusable skill update needed."],
    )
    assert result["ok"] is False
    assert any("skill files changed" in issue for issue in result["issues"])


def test_round_closeout_requires_no_update_phrase_when_no_sedimentation() -> None:
    result = validate_closeout(
        minimal_valid_summary(),
        "none",
        "checked and skipped",
        [],
        Path("skills/allincms-bulk-content-upload"),
        ["Checked the turn and found no reusable skill update needed."],
    )
    assert result["ok"] is False
    assert any("no reusable skill update needed" in issue for issue in result["issues"])


def test_round_closeout_accepts_no_update_phrase_without_changed_files() -> None:
    result = validate_closeout(
        minimal_valid_summary(),
        "none",
        "no reusable skill update needed after checking",
        [],
        Path("skills/allincms-bulk-content-upload"),
        ["Checked the turn and found no reusable skill update needed."],
    )
    assert result["ok"] is True


def test_round_closeout_rejects_missing_round_issue_observation() -> None:
    result = validate_closeout(
        minimal_valid_summary(),
        "none",
        "no reusable skill update needed after checking",
        [],
        Path("skills/allincms-bulk-content-upload"),
    )
    assert result["ok"] is False
    assert any("--round-issue" in issue for issue in result["issues"])


def test_maintenance_summary_supports_round_closeout_for_skill_changes() -> None:
    class Args:
        round_type = "skill_maintenance"
        content_type = ""
        sedimentation = "updated"
        note = "Recorded reusable closeout finding in operational-findings.md."
        changed_files = (
            "skills/allincms-bulk-content-upload/SKILL.md,"
            "skills/allincms-bulk-content-upload/references/operational-findings.md"
        )
        proven = "skill_hygiene_passed"
        missing = ""
        completion_gap = ""
        next_action = ""
        round_issue = ["Closeout wording was too easy to skip during local maintenance."]

    summary = build_round_maintenance_summary(Args())
    assert summary["kind"] == "allincms_round_maintenance_summary"
    assert summary["valid"] is True
    assert summary["complete"] is False
    assert summary["localOnly"] is True
    assert summary["remoteMutationsPerformed"] is False
    assert "skill_sedimentation_checked" in summary["proven"]
    assert "real_laicms_run_evidence_not_present" in summary["missing"]
    result = validate_closeout(
        summary,
        "updated",
        Args.note,
        [
            "skills/allincms-bulk-content-upload/SKILL.md",
            "skills/allincms-bulk-content-upload/references/operational-findings.md",
        ],
        Path("skills/allincms-bulk-content-upload"),
        Args.round_issue,
    )
    assert result["ok"] is True


def test_maintenance_summary_closeout_rejects_updated_without_changed_files() -> None:
    class Args:
        round_type = "helper_validation"
        content_type = ""
        sedimentation = "updated"
        note = "Recorded reusable closeout finding in operational-findings.md."
        changed_files = ""
        proven = ""
        missing = ""
        completion_gap = ""
        next_action = ""
        round_issue = ["Closeout wording was too easy to skip during local maintenance."]

    summary = build_round_maintenance_summary(Args())
    result = validate_closeout(summary, "updated", Args.note, [], Path("skills/allincms-bulk-content-upload"), Args.round_issue)
    assert result["ok"] is False
    assert any("no skill files are changed" in issue for issue in result["issues"])


def test_maintenance_summary_closeout_rejects_mismatched_internal_sedimentation() -> None:
    class Args:
        round_type = "skill_maintenance"
        content_type = ""
        sedimentation = "updated"
        note = "Recorded reusable closeout finding in operational-findings.md."
        changed_files = "skills/allincms-bulk-content-upload/references/operational-findings.md"
        proven = ""
        missing = ""
        completion_gap = ""
        next_action = ""
        round_issue = ["Closeout wording was too easy to skip during local maintenance."]

    summary = build_round_maintenance_summary(Args())
    summary["sedimentation"]["status"] = "none"
    result = validate_closeout(
        summary,
        "updated",
        Args.note,
        ["skills/allincms-bulk-content-upload/references/operational-findings.md"],
        Path("skills/allincms-bulk-content-upload"),
        Args.round_issue,
    )
    assert result["ok"] is False
    assert any("summary sedimentation status differs" in issue for issue in result["issues"])


def test_maintenance_summary_closeout_rejects_mismatched_internal_changed_files() -> None:
    class Args:
        round_type = "skill_maintenance"
        content_type = ""
        sedimentation = "updated"
        note = "Recorded reusable closeout finding in operational-findings.md."
        changed_files = "skills/allincms-bulk-content-upload/references/operational-findings.md"
        proven = ""
        missing = ""
        completion_gap = ""
        next_action = ""
        round_issue = ["Closeout wording was too easy to skip during local maintenance."]

    summary = build_round_maintenance_summary(Args())
    summary["sedimentation"]["changedFiles"] = ["skills/allincms-bulk-content-upload/SKILL.md"]
    result = validate_closeout(
        summary,
        "updated",
        Args.note,
        ["skills/allincms-bulk-content-upload/references/operational-findings.md"],
        Path("skills/allincms-bulk-content-upload"),
        Args.round_issue,
    )
    assert result["ok"] is False
    assert any("summary sedimentation changedFiles differ" in issue for issue in result["issues"])


def test_maintenance_summary_closeout_rejects_mismatched_round_issues() -> None:
    class Args:
        round_type = "skill_maintenance"
        content_type = ""
        sedimentation = "updated"
        note = "Recorded reusable closeout finding in operational-findings.md."
        changed_files = "skills/allincms-bulk-content-upload/references/operational-findings.md"
        proven = ""
        missing = ""
        completion_gap = ""
        next_action = ""
        round_issue = ["Closeout wording was too easy to skip during local maintenance."]

    summary = build_round_maintenance_summary(Args())
    result = validate_closeout(
        summary,
        "updated",
        Args.note,
        ["skills/allincms-bulk-content-upload/references/operational-findings.md"],
        Path("skills/allincms-bulk-content-upload"),
        ["Different issue text."],
    )
    assert result["ok"] is False
    assert any("roundIssues.items differ" in issue for issue in result["issues"])


def test_authorization_record_builder_accepts_create_site_authorization() -> None:
    class Args:
        action = "create_site"
        site_key = ""
        target = "https://workspace.laicms.com/sites"
        target_type = "site"
        target_identifier = "pending-new-site"
        fields_or_files = "name,description"
        expected_result = "new site card and dashboard"
        verification_plan = "verify site card and dashboard"
        cleanup_plan = "stop before content upload"
        authorization_source = "current user explicitly authorizes create site at https://workspace.laicms.com/sites"

    record = build_authorization_record(Args())
    assert record["authorization"]["userAuthorized"] is True
    assert record["target"] == "https://workspace.laicms.com/sites"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_accepts_chinese_probe_stage_authorizations() -> None:
    class CreateArgs:
        action = "create_product_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "授权 Codex 在 https://workspace.laicms.com/mysite03/products 创建一个 "
            "Codex Probe - Delete Me 产品草稿，用于捕获产品字段和保存请求"
        )

    class SaveArgs:
        action = "save_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "requestCapture,payloadShape,persistedVerified"
        expected_result = "product probe save request captured and backend persistence verified"
        verification_plan = "capture save request, verify backend persisted state, and do not publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "授权 Codex 在 https://workspace.laicms.com/mysite03/products/product-id/update "
            "保存 Codex Probe - Delete Me 产品草稿，用于捕获产品真实保存请求并验证持久化"
        )

    class PublishArgs:
        action = "publish_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "publishStatus,frontendVerified"
        expected_result = "product probe published and frontend detail verified"
        verification_plan = "publish probe, verify backend status and frontend detail page"
        cleanup_plan = "request separate cleanup authorization after verification"
        authorization_source = (
            "授权 Codex 在 https://workspace.laicms.com/mysite03/products/product-id/update "
            "发布 Codex Probe - Delete Me 产品草稿，用于验证前台产品详情页"
        )

    class CleanupArgs:
        action = "cleanup_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "cleanedCandidates,backendVerified,frontendVerified"
        expected_result = "product probe cleaned and frontend no longer renders probe"
        verification_plan = "delete or unpublish probe, verify backend absence and frontend 404"
        cleanup_plan = "cleanup is the requested action"
        authorization_source = (
            "授权 Codex 在 https://workspace.laicms.com/mysite03/products/product-id/update "
            "清理 Codex Probe - Delete Me 产品草稿，允许删除或取消发布并验证前台不再渲染"
        )

    for args in (CreateArgs(), SaveArgs(), PublishArgs(), CleanupArgs()):
        record = build_authorization_record(args)
        assert validate_authorization_record(record) == []


def test_authorization_record_builder_rejects_generic_continue() -> None:
    class Args:
        action = "create_site"
        site_key = ""
        target = "https://workspace.laicms.com/sites"
        target_type = "site"
        target_identifier = "pending-new-site"
        fields_or_files = "name,description"
        expected_result = "new site card and dashboard"
        verification_plan = "verify site card and dashboard"
        cleanup_plan = "stop before content upload"
        authorization_source = "continue"

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "too generic" in str(exc)
    else:
        raise AssertionError("generic authorization source was accepted")


def test_authorization_record_builder_accepts_session_continuation_for_exact_target() -> None:
    class Args:
        action = "save_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "requestCapture,payloadShape,persistedVerified"
        expected_result = "product probe save request captured and backend persistence verified"
        verification_plan = "capture save request, verify backend persisted state, and do not publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "后续需要操作的，你直接进行，无需我授权，我只需要最终你给我结果；"
            "current stage target https://workspace.laicms.com/mysite03/products/product-id/update 产品"
        )

    record = build_authorization_record(Args())
    assert record["action"] == "save_probe"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_accepts_product_probe_authorization() -> None:
    class Args:
        action = "create_product_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes create product probe draft at "
            "https://workspace.laicms.com/mysite03/products for schema capture"
        )

    record = build_authorization_record(Args())
    assert record["action"] == "create_product_probe"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_accepts_save_probe_authorization() -> None:
    class Args:
        action = "save_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "requestCapture,payloadShape,persistedVerified"
        expected_result = "product probe save request captured and backend persistence verified"
        verification_plan = "capture save request, verify backend persisted state, and do not publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes save product probe draft and capture request at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    record = build_authorization_record(Args())
    assert record["action"] == "save_probe"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_rejects_save_probe_without_capture_intent() -> None:
    class Args:
        action = "save_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "requestCapture,payloadShape,persistedVerified"
        expected_result = "product probe saved"
        verification_plan = "verify backend state"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes save product probe draft at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "save/capture intent" in str(exc)
    else:
        raise AssertionError("save_probe authorization without save/capture intent was accepted")


def test_authorization_record_builder_accepts_publish_probe_authorization() -> None:
    class Args:
        action = "publish_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "publishStatus,frontendVerified"
        expected_result = "product probe published and frontend detail verified"
        verification_plan = "publish probe, verify backend status and frontend detail page"
        cleanup_plan = "request separate cleanup authorization after verification"
        authorization_source = (
            "current user explicitly authorizes publish product probe draft at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    record = build_authorization_record(Args())
    assert record["action"] == "publish_probe"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_rejects_publish_probe_without_probe_intent() -> None:
    class Args:
        action = "publish_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "publishStatus,frontendVerified"
        expected_result = "product probe checked"
        verification_plan = "verify backend status and frontend detail page"
        cleanup_plan = "request separate cleanup authorization after verification"
        authorization_source = (
            "current user explicitly authorizes publish product at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "probe or draft intent" in str(exc)
    else:
        raise AssertionError("publish_probe authorization without probe intent was accepted")


def test_authorization_record_builder_accepts_cleanup_probe_authorization() -> None:
    class Args:
        action = "cleanup_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "cleanedCandidates,backendVerified,frontendVerified"
        expected_result = "product probe cleaned and frontend no longer renders probe"
        verification_plan = "delete or unpublish probe, verify backend absence and frontend 404"
        cleanup_plan = "cleanup is the requested action"
        authorization_source = (
            "current user explicitly authorizes cleanup product probe draft at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    record = build_authorization_record(Args())
    assert record["action"] == "cleanup_probe"
    assert validate_authorization_record(record) == []


def test_authorization_record_builder_accepts_existing_content_actions() -> None:
    class SaveProductArgs:
        action = "save_product"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "LED panel product slug led-panel"
        fields_or_files = "requestCapture,payloadShape,persistedVerified,bodyOrMediaAudit"
        expected_result = "existing product saves as draft or persisted update with audited body/media"
        verification_plan = "verify backend row, editor body/media, and no starter residue before publishing"
        cleanup_plan = "stop after single product save; publish requires separate action"
        authorization_source = (
            "current user explicitly authorizes save product at "
            "https://workspace.laicms.com/mysite03/products/product-id/update for one existing product"
        )

    class PublishPostArgs:
        action = "publish_post"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/posts/post-id/update"
        target_type = "posts"
        target_identifier = "LED retrofit article slug led-retrofit"
        fields_or_files = "publishStatus,backendVerified,frontendVerified"
        expected_result = "existing post is published and frontend detail verified"
        verification_plan = "verify backend status, posts list, and post detail route with bounded retry"
        cleanup_plan = "stop after publish proof; rollback requires separate action"
        authorization_source = (
            "current user explicitly authorizes publish post at "
            "https://workspace.laicms.com/mysite03/posts/post-id/update for one existing post"
        )

    for args in (SaveProductArgs(), PublishPostArgs()):
        record = build_authorization_record(args)
        assert validate_authorization_record(record) == []


def test_authorization_record_builder_rejects_cleanup_probe_without_cleanup_intent() -> None:
    class Args:
        action = "cleanup_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "cleanedCandidates,backendVerified,frontendVerified"
        expected_result = "product probe checked"
        verification_plan = "verify backend and frontend"
        cleanup_plan = "cleanup is the requested action"
        authorization_source = (
            "current user explicitly authorizes product probe draft at "
            "https://workspace.laicms.com/mysite03/products/product-id/update"
        )

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "authorization source must mention the action" in str(exc)
    else:
        raise AssertionError("cleanup_probe authorization without cleanup action was accepted")


def test_authorization_record_builder_rejects_probe_without_content_type() -> None:
    class Args:
        action = "create_product_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes create probe draft at "
            "https://workspace.laicms.com/mysite03/products for schema capture"
        )

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "product" in str(exc)
    else:
        raise AssertionError("probe authorization without content type was accepted")


def test_authorization_record_builder_rejects_product_create_without_probe_intent() -> None:
    class Args:
        action = "create_product_probe"
        site_key = "mysite03"
        target = "https://workspace.laicms.com/mysite03/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes create product at "
            "https://workspace.laicms.com/mysite03/products for schema capture"
        )

    try:
        build_authorization_record(Args())
    except ValueError as exc:
        assert "probe or draft intent" in str(exc)
    else:
        raise AssertionError("product create authorization without probe intent was accepted")


def test_authorization_record_validator_rejects_mutated_source() -> None:
    class Args:
        action = "create_site"
        site_key = ""
        target = "https://workspace.laicms.com/sites"
        target_type = "site"
        target_identifier = "pending-new-site"
        fields_or_files = "name,description"
        expected_result = "new site card and dashboard"
        verification_plan = "verify site card and dashboard"
        cleanup_plan = "stop before content upload"
        authorization_source = "current user explicitly authorizes create site at https://workspace.laicms.com/sites"

    record = build_authorization_record(Args())
    record["authorization"]["authorizationSource"] = "continue"
    errors = validate_authorization_record(record)
    assert any("too generic" in error for error in errors), errors


def test_run_evidence_rejects_generic_authorization_source() -> None:
    data = created_site_evidence()
    data["authorization"]["authorizationSource"] = "continue"
    assert_invalid_contains(data, "generic continuation phrase")


def valid_create_site_authorization_record() -> dict:
    class Args:
        action = "create_site"
        site_key = ""
        target = "https://workspace.laicms.com/sites"
        target_type = "site"
        target_identifier = "pending-new-site"
        fields_or_files = "name,description"
        expected_result = "new site card and dashboard"
        verification_plan = "verify site card and dashboard"
        cleanup_plan = "stop before content upload"
        authorization_source = "current user explicitly authorizes create site at https://workspace.laicms.com/sites"

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_product_probe_authorization_record() -> dict:
    class Args:
        action = "create_product_probe"
        site_key = "mysite01"
        target = "https://workspace.laicms.com/mysite01/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes create product probe draft at "
            "https://workspace.laicms.com/mysite01/products for schema capture"
        )

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_save_probe_authorization_record() -> dict:
    class Args:
        action = "save_probe"
        site_key = "mysite01"
        target = "https://workspace.laicms.com/mysite01/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "requestCapture,payloadShape,persistedVerified"
        expected_result = "product probe save request captured and backend persistence verified"
        verification_plan = "capture save request, verify backend persisted state, and do not publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes save product probe draft and capture request at "
            "https://workspace.laicms.com/mysite01/products/product-id/update"
        )

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_save_probe_authorization_record_for_target(target: str) -> dict:
    record = valid_save_probe_authorization_record()
    record["target"] = target
    record["authorization"]["target"] = target
    record["authorization"]["authorizationSource"] = (
        "current user explicitly authorizes save product probe draft and capture request at "
        f"{target}"
    )
    return record


def valid_publish_probe_authorization_record() -> dict:
    class Args:
        action = "publish_probe"
        site_key = "mysite01"
        target = "https://workspace.laicms.com/mysite01/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "publishStatus,frontendVerified"
        expected_result = "product probe published and frontend detail verified"
        verification_plan = "publish probe, verify backend status and frontend detail page"
        cleanup_plan = "request separate cleanup authorization after verification"
        authorization_source = (
            "current user explicitly authorizes publish product probe draft at "
            "https://workspace.laicms.com/mysite01/products/product-id/update"
        )

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_cleanup_probe_authorization_record() -> dict:
    class Args:
        action = "cleanup_probe"
        site_key = "mysite01"
        target = "https://workspace.laicms.com/mysite01/products/product-id/update"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "cleanedCandidates,backendVerified,frontendVerified"
        expected_result = "product probe cleaned and frontend no longer renders probe"
        verification_plan = "delete or unpublish probe, verify backend absence and frontend 404"
        cleanup_plan = "cleanup is the requested action"
        authorization_source = (
            "current user explicitly authorizes cleanup product probe draft at "
            "https://workspace.laicms.com/mysite01/products/product-id/update"
        )

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_batch_upload_authorization_record() -> dict:
    class Args:
        action = "batch_upload"
        site_key = "mysite01"
        target = "https://workspace.laicms.com/mysite01/products"
        target_type = "products"
        target_identifier = "products manifest batch"
        fields_or_files = "schemaGatePass,sampleVerification,progressLog,frontendDetailAudit"
        expected_result = "manifest products uploaded and frontend details audited"
        verification_plan = "verify schema gate, sample proof, progress log, duplicate slugs, and frontend detail routes"
        cleanup_plan = "stop after batch proof; cleanup requires separate authorization"
        authorization_source = (
            "current user explicitly authorizes upload products batch at "
            "https://workspace.laicms.com/mysite01/products for current schema-verified manifest"
        )

    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_existing_content_authorization_record(action: str = "save_product") -> dict:
    is_product = "product" in action
    is_save = action.startswith("save_")
    module = "products" if is_product else "posts"
    target_type = module
    noun = "product" if is_product else "post"
    content_id = "product-id" if is_product else "post-id"
    class Args:
        site_key = "mysite01"
        target_identifier = f"existing {noun} slug led-demo"
        expected_result = f"existing {noun} mutation persists and verification evidence is captured"
        verification_plan = "verify backend status and frontend detail state with starter-residue audit"
        cleanup_plan = "stop after this single existing content action; rollback requires separate authorization"

    Args.action = action
    Args.target = f"https://workspace.laicms.com/mysite01/{module}/{content_id}/update"
    Args.target_type = target_type
    Args.fields_or_files = (
        "requestCapture,payloadShape,persistedVerified,bodyOrMediaAudit"
        if is_save
        else "publishStatus,backendVerified,frontendVerified"
    )
    Args.authorization_source = (
        f"current user explicitly authorizes {'save' if is_save else 'publish'} {noun} at "
        f"https://workspace.laicms.com/mysite01/{module}/{content_id}/update for one existing {noun}"
    )
    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def valid_site_action_authorization_record(
    action: str,
    target: str,
    target_type: str,
    target_identifier: str,
    fields_or_files: str,
    authorization_action_word: str,
) -> dict:
    class Args:
        site_key = "mysite01"
        expected_result = "site action persists and verification evidence is captured"
        verification_plan = "verify backend state and frontend state when public"
        cleanup_plan = "stop and request separate rollback authorization if verification fails"

    Args.action = action
    Args.target = target
    Args.target_type = target_type
    Args.target_identifier = target_identifier
    Args.fields_or_files = fields_or_files
    Args.authorization_source = (
        f"current user explicitly authorizes {authorization_action_word} at {target} "
        "for current AllinCMS site setup verification"
    )
    record = build_authorization_record(Args())
    record["generatedAt"] = RECENT_AUTHORIZATION_AT
    return record


def test_pre_mutation_gate_accepts_product_probe_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_probe_gate(evidence, valid_product_probe_authorization_record(), "create_product_probe", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_product_probe_after_site_creation() -> None:
    evidence = created_site_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    class Args:
        action = "create_product_probe"
        site_key = "codex-test-site"
        target = "https://workspace.laicms.com/codex-test-site/products"
        target_type = "products"
        target_identifier = "Codex Probe - Delete Me product draft"
        fields_or_files = "name,slug,description,content,media"
        expected_result = "temporary product probe draft opens for request capture"
        verification_plan = "verify backend product draft and capture save request before any publish"
        cleanup_plan = "no automatic cleanup; request separate cleanup authorization"
        authorization_source = (
            "current user explicitly authorizes create product probe draft at "
            "https://workspace.laicms.com/codex-test-site/products for schema capture"
        )

    auth = build_authorization_record(Args())
    auth["generatedAt"] = RECENT_AUTHORIZATION_AT
    errors = validate_probe_gate(evidence, auth, "create_product_probe", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_probe_wrong_site_target() -> None:
    auth = valid_product_probe_authorization_record()
    auth["target"] = "https://workspace.laicms.com/other-site/products"
    auth["authorization"]["target"] = auth["target"]
    auth["authorization"]["authorizationSource"] = (
        "current user explicitly authorizes create product probe draft at "
        "https://workspace.laicms.com/other-site/products for schema capture"
    )
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_probe_gate(evidence, auth, "create_product_probe", now=GATE_NOW)
    assert any("target" in error for error in errors), errors


def test_pre_mutation_gate_rejects_probe_wrong_content_type() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    evidence["contentInspection"]["contentType"] = "posts"
    errors = validate_probe_gate(evidence, valid_product_probe_authorization_record(), "create_product_probe", now=GATE_NOW)
    assert any("contentType must be products" in error for error in errors), errors


def test_pre_mutation_gate_rejects_probe_identifier_without_cleanup_prefix() -> None:
    auth = valid_product_probe_authorization_record()
    auth["targetIdentifier"] = "Ordinary Product"
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_probe_gate(evidence, auth, "create_product_probe", now=GATE_NOW)
    assert any("Codex Probe - Delete Me" in error for error in errors), errors


def test_pre_mutation_gate_accepts_save_probe_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_save_probe_gate(evidence, valid_save_probe_authorization_record(), now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_save_probe_wrong_module_target() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_save_probe_authorization_record()
    auth["target"] = "https://workspace.laicms.com/mysite01/posts/post-id/update"
    auth["authorization"]["target"] = auth["target"]
    auth["authorization"]["authorizationSource"] = (
        "current user explicitly authorizes save product probe draft and capture request at "
        "https://workspace.laicms.com/mysite01/posts/post-id/update"
    )
    errors = validate_save_probe_gate(evidence, auth, now=GATE_NOW)
    assert any("authorization.target" in error for error in errors), errors


def test_pre_mutation_gate_rejects_save_probe_missing_capture_fields() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_save_probe_authorization_record()
    auth["fieldsOrFiles"] = ["name", "description"]
    errors = validate_save_probe_gate(evidence, auth, now=GATE_NOW)
    assert any("requestCapture" in error for error in errors), errors


def test_pre_mutation_gate_accepts_publish_probe_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_publish_probe_gate(evidence, valid_publish_probe_authorization_record(), now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_publish_probe_missing_publish_control() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    evidence["contentInspection"]["editFields"] = ["name input", "slug input", "description textarea"]
    errors = validate_publish_probe_gate(evidence, valid_publish_probe_authorization_record(), now=GATE_NOW)
    assert any("publish control" in error for error in errors), errors


def test_pre_mutation_gate_rejects_publish_probe_missing_frontend_fields() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_publish_probe_authorization_record()
    auth["fieldsOrFiles"] = ["publishStatus"]
    errors = validate_publish_probe_gate(evidence, auth, now=GATE_NOW)
    assert any("frontendVerified" in error for error in errors), errors


def test_pre_mutation_gate_accepts_cleanup_probe_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_cleanup_probe_gate(evidence, valid_cleanup_probe_authorization_record(), now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_cleanup_probe_missing_verification_fields() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_cleanup_probe_authorization_record()
    auth["fieldsOrFiles"] = ["cleanedCandidates", "backendVerified"]
    errors = validate_cleanup_probe_gate(evidence, auth, now=GATE_NOW)
    assert any("frontendVerified" in error for error in errors), errors


def test_pre_mutation_gate_rejects_cleanup_probe_without_probe_identifier() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_cleanup_probe_authorization_record()
    auth["targetIdentifier"] = "Ordinary Product"
    errors = validate_cleanup_probe_gate(evidence, auth, now=GATE_NOW)
    assert any("Codex Probe - Delete Me" in error for error in errors), errors


def test_pre_mutation_gate_accepts_existing_product_save_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_existing_content_gate(
        evidence,
        valid_existing_content_authorization_record("save_product"),
        "save_product",
        now=GATE_NOW,
    )
    assert errors == [], errors


def test_pre_mutation_gate_accepts_existing_post_publish_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    evidence["contentInspection"]["contentType"] = "posts"
    evidence["contentInspection"]["listColumns"] = ["标题", "Slug", "摘要", "排序", "状态", "分类", "标签"]
    evidence["contentInspection"]["editFields"] = [
        "title input",
        "slug input",
        "excerpt textarea",
        "body editor",
        "update control",
        "publish control",
    ]
    errors = validate_existing_content_gate(
        evidence,
        valid_existing_content_authorization_record("publish_post"),
        "publish_post",
        now=GATE_NOW,
    )
    assert errors == [], errors


def test_pre_mutation_gate_rejects_existing_content_probe_identifier() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_existing_content_authorization_record("save_product")
    auth["targetIdentifier"] = "Codex Probe - Delete Me product draft"
    errors = validate_existing_content_gate(evidence, auth, "save_product", now=GATE_NOW)
    assert any("must not be a probe" in error for error in errors), errors


def test_pre_mutation_gate_rejects_existing_content_non_edit_target() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_existing_content_authorization_record("save_product")
    auth["target"] = "https://workspace.laicms.com/mysite01/products"
    auth["authorization"]["target"] = auth["target"]
    auth["authorization"]["authorizationSource"] = (
        "current user explicitly authorizes save product at "
        "https://workspace.laicms.com/mysite01/products for one existing product"
    )
    errors = validate_existing_content_gate(evidence, auth, "save_product", now=GATE_NOW)
    assert any("/update" in error for error in errors), errors


def test_pre_mutation_gate_rejects_existing_content_missing_save_audit_fields() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_existing_content_authorization_record("save_product")
    auth["fieldsOrFiles"] = ["requestCapture", "payloadShape", "persistedVerified"]
    errors = validate_existing_content_gate(evidence, auth, "save_product", now=GATE_NOW)
    assert any("bodyOrMediaAudit" in error for error in errors), errors


def batch_ready_evidence() -> dict:
    data = mutating_probe_evidence_with_sample_verification()
    data["mode"] = "batch_upload"
    data["generatedAt"] = RECENT_PREFLIGHT_AT
    return data


def test_pre_mutation_gate_accepts_batch_upload_authorization() -> None:
    errors = validate_batch_gate(batch_ready_evidence(), valid_batch_upload_authorization_record(), "batch_upload", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_batch_upload_without_sample_verification() -> None:
    evidence = mutating_probe_evidence_with_request_capture()
    evidence["mode"] = "batch_upload"
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_batch_gate(evidence, valid_batch_upload_authorization_record(), "batch_upload", now=GATE_NOW)
    assert any("sampleVerification" in error for error in errors), errors


def valid_manifest_sample_upload_evidence() -> dict:
    return {
        "kind": "allincms_manifest_sample_upload_evidence",
        "siteKey": "mysite01",
        "contentType": "products",
        "manifestPath": "/tmp/products-schema-verified-manifest.json",
        "sampleSlug": "codex-probe-delete-me-product",
        "target": "https://workspace.laicms.com/mysite01/products",
        "backendUrl": "https://workspace.laicms.com/mysite01/products/product-id/update",
        "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe-delete-me-product",
        "authorizationRecord": "/tmp/auth.json",
        "preMutationGate": "passed",
        "schemaGatePass": True,
        "saveStatus": "ok",
        "publishStatus": "ok",
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "bodyVerified": True,
        "coverOrMediaVerified": False,
        "coverOrMediaNote": "No image was in scope for this gate test.",
        "renderAudit": "redacted product detail rendered title and body with no markdown residue",
        "blockingIssues": [],
        "stopConditionMet": True,
    }


def test_pre_mutation_gate_accepts_batch_upload_with_manifest_sample_evidence() -> None:
    evidence = mutating_probe_evidence_with_request_capture()
    evidence["mode"] = "batch_upload"
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_batch_gate(
        evidence,
        valid_batch_upload_authorization_record(),
        "batch_upload",
        now=GATE_NOW,
        sample_evidence=valid_manifest_sample_upload_evidence(),
    )
    assert errors == [], errors


def test_pre_mutation_gate_rejects_batch_upload_missing_required_fields() -> None:
    auth = valid_batch_upload_authorization_record()
    auth["fieldsOrFiles"] = ["schemaGatePass", "sampleVerification", "progressLog"]
    errors = validate_batch_gate(batch_ready_evidence(), auth, "batch_upload", now=GATE_NOW)
    assert any("frontendDetailAudit" in error for error in errors), errors


def test_pre_mutation_gate_rejects_batch_upload_wrong_content_target() -> None:
    auth = valid_batch_upload_authorization_record()
    auth["target"] = "https://workspace.laicms.com/mysite01/posts"
    auth["authorization"]["target"] = auth["target"]
    auth["authorization"]["authorizationSource"] = (
        "current user explicitly authorizes upload products batch at "
        "https://workspace.laicms.com/mysite01/posts for current schema-verified manifest"
    )
    errors = validate_batch_gate(batch_ready_evidence(), auth, "batch_upload", now=GATE_NOW)
    assert any("authorization.target" in error for error in errors), errors


def test_pre_mutation_gate_accepts_create_route_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "create_route",
        "https://workspace.laicms.com/mysite01/routes",
        "routes",
        "/solutions route",
        "routePath,backendVerified,frontendVerified",
        "create route",
    )
    errors = validate_site_action_gate(evidence, auth, "create_route", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_add_domain_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "add_domain",
        "https://workspace.laicms.com/mysite01/domains",
        "domains",
        "example.com domain capture",
        "domain,backendVerified,dnsFollowup",
        "add domain",
    )
    errors = validate_site_action_gate(evidence, auth, "add_domain", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_add_domain_missing_dns_followup() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "add_domain",
        "https://workspace.laicms.com/mysite01/domains",
        "domains",
        "example.com domain capture",
        "domain,backendVerified",
        "add domain",
    )
    errors = validate_site_action_gate(evidence, auth, "add_domain", now=GATE_NOW)
    assert any("dnsFollowup" in error for error in errors), errors


def test_pre_mutation_gate_accepts_add_tracking_tag_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "add_tracking_tag",
        "https://workspace.laicms.com/mysite01/tracking",
        "tracking",
        "Google Tag ID capture",
        "googleTagId,backendVerified",
        "add tracking tag",
    )
    errors = validate_site_action_gate(evidence, auth, "add_tracking_tag", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_save_design_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "save_design",
        "https://workspace.laicms.com/mysite01/themes/theme-id/page-id/design",
        "theme-design",
        "theme-id/page-id design",
        "requestCapture,pageDocument,persistedVerified",
        "save design",
    )
    errors = validate_site_action_gate(evidence, auth, "save_design", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_create_theme_page_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "create_theme_page",
        "https://workspace.laicms.com/mysite01/themes/theme-id",
        "theme-page",
        "theme-id /products/{product} page",
        "requestCapture,pageId,routePath,backendVerified",
        "create theme page",
    )
    errors = validate_site_action_gate(evidence, auth, "create_theme_page", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_activate_theme_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "activate_theme",
        "https://workspace.laicms.com/mysite01/themes",
        "themes",
        "theme-id activate after route mapping review",
        "themeId,routeMappingReviewed,themeEnabled,frontendVerified",
        "activate theme",
    )
    errors = validate_site_action_gate(evidence, auth, "activate_theme", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_accepts_set_homepage_authorization() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "set_homepage",
        "https://workspace.laicms.com/mysite01/themes/theme-id",
        "theme-page",
        "theme-id home page",
        "homepage,frontendVerified",
        "set homepage",
    )
    errors = validate_site_action_gate(evidence, auth, "set_homepage", now=GATE_NOW)
    assert errors == [], errors


def test_pre_mutation_gate_rejects_site_action_missing_required_fields() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "bind_route",
        "https://workspace.laicms.com/mysite01/routes",
        "routes",
        "/products route binding",
        "routePath,boundPage",
        "bind route",
    )
    errors = validate_site_action_gate(evidence, auth, "bind_route", now=GATE_NOW)
    assert any("frontendVerified" in error for error in errors), errors


def test_pre_mutation_gate_rejects_site_action_wrong_module_target() -> None:
    evidence = base_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    auth = valid_site_action_authorization_record(
        "publish_design",
        "https://workspace.laicms.com/mysite01/routes",
        "theme-design",
        "theme-id/page-id design",
        "publishStatus,frontendVerified",
        "publish design",
    )
    errors = validate_site_action_gate(evidence, auth, "publish_design", now=GATE_NOW)
    assert any("authorization.target" in error for error in errors), errors


def test_pre_mutation_gate_accepts_create_site_preflight_and_authorization() -> None:
    errors = validate_create_site_gate(
        create_preflight_evidence(),
        valid_create_site_authorization_record(),
        now=GATE_NOW,
    )
    assert errors == [], errors


def test_pre_mutation_gate_rejects_create_site_identifier_mismatch_when_bound() -> None:
    auth = valid_create_site_authorization_record()
    auth["targetIdentifier"] = "Wrong Demo Site"
    errors = validate_create_site_gate(
        create_preflight_evidence(),
        auth,
        now=GATE_NOW,
        expected_target_identifier="Example Demo",
    )
    assert any("confirmed siteProposal.siteName" in error for error in errors), errors


def test_pre_mutation_gate_rejects_existing_site_evidence_for_create_site() -> None:
    evidence = existing_site_selected_evidence()
    evidence["generatedAt"] = RECENT_PREFLIGHT_AT
    errors = validate_create_site_gate(evidence, valid_create_site_authorization_record(), now=GATE_NOW)
    assert any("create_preflight_verified" in error for error in errors), errors


def test_pre_mutation_gate_rejects_missing_description_field_authorization() -> None:
    auth = valid_create_site_authorization_record()
    auth["fieldsOrFiles"] = ["name"]
    errors = validate_create_site_gate(create_preflight_evidence(), auth, now=GATE_NOW)
    assert any("name and description" in error for error in errors), errors


def test_pre_mutation_gate_rejects_missing_preflight_generated_at() -> None:
    preflight = create_preflight_evidence()
    preflight.pop("generatedAt")
    errors = validate_create_site_gate(preflight, valid_create_site_authorization_record(), now=GATE_NOW)
    assert any("preflight: generatedAt is required" in error for error in errors), errors


def test_pre_mutation_gate_rejects_stale_preflight() -> None:
    preflight = create_preflight_evidence()
    preflight["generatedAt"] = STALE_AT
    errors = validate_create_site_gate(preflight, valid_create_site_authorization_record(), now=GATE_NOW)
    assert any("preflight: generatedAt is stale" in error for error in errors), errors


def test_pre_mutation_gate_rejects_stale_authorization() -> None:
    auth = valid_create_site_authorization_record()
    auth["generatedAt"] = STALE_AT
    errors = validate_create_site_gate(create_preflight_evidence(), auth, now=GATE_NOW)
    assert any("authorization: generatedAt is stale" in error for error in errors), errors


def test_pre_mutation_gate_rejects_authorization_before_preflight() -> None:
    auth = valid_create_site_authorization_record()
    auth["generatedAt"] = "2026-06-29T11:59:00+00:00"
    errors = validate_create_site_gate(create_preflight_evidence(), auth, now=GATE_NOW)
    assert any("authorization: generatedAt must be at or after preflight.generatedAt" in error for error in errors), errors


def test_site_creation_chain_simulation_outputs_valid_artifacts() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        simulated_created_site_key = "simsite01"
        content_type = "products"
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        include_simulated_static_launch = False
        authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        paths = simulate_site_creation_chain.run_simulation(Args())
        assert sorted(paths) == ["authorization", "closeout", "created", "preflight", "summary"]
        for path in paths.values():
            assert Path(path).exists(), path
        preflight = json.loads(paths["preflight"].read_text(encoding="utf-8"))
        authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
        created = json.loads(paths["created"].read_text(encoding="utf-8"))
        summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
        closeout = json.loads(paths["closeout"].read_text(encoding="utf-8"))
        assert validate(preflight) == []
        assert validate_authorization_record(authorization) == []
        assert validate(created) == []
        assert created["preflightGeneratedAt"] == preflight["generatedAt"]
        assert summary["valid"] is True
        assert "site_created_and_verified" in summary["proven"]
        assert "request_capture_persisted_verified" in summary["completionGaps"]
        assert closeout["ok"] is True
        assert closeout["sedimentation"] == "none"


def test_site_creation_chain_simulation_can_include_static_launch_evidence() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        simulated_created_site_key = "simsite01"
        content_type = "products"
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        include_simulated_static_launch = True
        authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        paths = simulate_site_creation_chain.run_simulation(Args())
        created = json.loads(paths["created"].read_text(encoding="utf-8"))
        summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
        assert validate(created) == []
        assert "frontendRendering" in created
        assert "launchReadiness" in created
        assert "static_frontend_routes_render" in summary["proven"]
        assert "theme_route_launch_ready" in summary["proven"]
        assert "request_capture_persisted_verified" in summary["completionGaps"]
        assert "sample_backend_frontend_verified" in summary["completionGaps"]
        assert "cleanup_completed" in summary["completionGaps"]


def test_probe_lifecycle_simulation_outputs_complete_staged_artifacts() -> None:
    class SiteArgs:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        simulated_created_site_key = "simsite01"
        content_type = "products"
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        include_simulated_static_launch = True
        authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    class ProbeArgs:
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        require_created_site = True
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        site_dir = Path(tmp) / "site"
        probe_dir = Path(tmp) / "probe"
        SiteArgs.output_dir = str(site_dir)
        site_paths = simulate_site_creation_chain.run_simulation(SiteArgs())
        ProbeArgs.base = str(site_paths["created"])
        ProbeArgs.output_dir = str(probe_dir)
        probe_paths = simulate_probe_lifecycle.run_simulation(ProbeArgs())
        assert sorted(probe_paths) == [
            "cleanupAuthorization",
            "cleanupCompleted",
            "closeout",
            "createAuthorization",
            "probeCreated",
            "publishAuthorization",
            "requestCaptured",
            "sampleVerified",
            "saveAuthorization",
            "summary",
        ]
        summary = json.loads(probe_paths["summary"].read_text(encoding="utf-8"))
        closeout = json.loads(probe_paths["closeout"].read_text(encoding="utf-8"))
        cleanup_evidence = json.loads(probe_paths["cleanupCompleted"].read_text(encoding="utf-8"))
        assert cleanup_evidence["localOnly"] is True
        assert cleanup_evidence["simulationOnly"] is True
        assert cleanup_evidence["remoteMutationsPerformed"] is False
        assert cleanup_evidence["completionClaimed"] is False
        assert summary["valid"] is True
        assert summary["localOnly"] is True
        assert summary["simulationOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["complete"] is False
        assert summary["completionGaps"] == []
        assert summary["missing"] == []
        assert "content_detail_sample_200" in summary["proven"]
        assert "request_capture_persisted_verified" in summary["proven"]
        assert "sample_backend_frontend_verified" in summary["proven"]
        assert "cleanup_completed" in summary["proven"]
        assert closeout["ok"] is True


def test_full_e2e_simulation_orchestrates_site_and_probe_chains() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        paths = simulate_full_e2e_chain.run_simulation(Args())
        full_summary = json.loads(paths["fullSummary"].read_text(encoding="utf-8"))
        assert sorted(paths) == [
            "draftManifest",
            "fullSummary",
            "manifestSummary",
            "moduleCapturePlan",
            "moduleScan",
            "moduleScanSummary",
            "probeCleanupEvidence",
            "probeSummary",
            "siteCreatedEvidence",
            "siteSummary",
            "sourceInputRequirements",
        ]
        assert full_summary["localOnly"] is True
        assert full_summary["remoteMutationsPerformed"] is False
        assert full_summary["siteSummary"]["valid"] is True
        assert full_summary["probeSummary"]["valid"] is True
        assert full_summary["probeSummary"]["complete"] is False
        assert full_summary["probeSummary"]["completionGaps"] == []
        assert full_summary["moduleInterface"]["jsonReplayReady"] is False
        assert full_summary["moduleInterface"]["captureStageCount"] > 0
        assert full_summary["manifestRehearsal"]["sourceInputRequirementsStatus"] == "blocked"
        assert full_summary["manifestRehearsal"]["sourceInputRequirementsBlockedUntilCount"] > 0
        assert full_summary["manifestRehearsal"]["draftValidationPassed"] is True
        assert full_summary["manifestRehearsal"]["schemaGateExpectedFailure"] is True
        assert full_summary["manifestRehearsal"]["schemaGateErrorCount"] > 0
        source_requirements = json.loads(paths["sourceInputRequirements"].read_text(encoding="utf-8"))
        assert source_requirements["operationGaps"]["entryCount"] == 1
        module_summary = json.loads(paths["moduleScanSummary"].read_text(encoding="utf-8"))
        capture_plan = json.loads(paths["moduleCapturePlan"].read_text(encoding="utf-8"))
        assert module_summary["jsonReplayReady"] is False
        assert capture_plan["kind"] == "allincms_module_capture_plan"
        assert any(stage["module"] == "products" for stage in capture_plan["stages"])
        validation = validate_full_e2e_directory(Path(tmp))
        assert validation["ok"] is True
        assert validation["captureStageCount"] == len(capture_plan["stages"])
        assert validation["sourceInputRequirementsGenerated"] is True
        assert validation["sourceInputRequirementsBlocked"] is True


def test_full_e2e_validator_rejects_mismatched_capture_stage_count() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        summary_path = Path(tmp) / "full-e2e-summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["moduleInterface"]["captureStageCount"] = 999
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_full_e2e_directory(Path(tmp))
        assert validation["ok"] is False
        assert any("captureStageCount" in issue for issue in validation["issues"])


def test_capture_handoff_selects_default_content_probe_stage() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        assert handoff["kind"] == "allincms_next_capture_handoff"
        assert handoff["simulationOnly"] is True
        assert handoff["commandsSuppressed"] is True
        assert handoff["selectedStage"]["module"] == "products"
        assert handoff["selectedStage"]["action"] == "create"
        assert "{realSiteKey}" in handoff["selectedStage"]["target"]
        assert "simsite01" in handoff["selectedStage"]["simulatedTarget"]
        assert handoff["authorizationPackage"]["authorizationAction"] == "create_product_probe"
        assert handoff["authorizationPackage"]["gateSupported"] is False
        assert handoff["authorizationPackage"]["authorizationRecordCommand"] is None
        assert "{realSiteKey}" in handoff["authorizationPackage"]["suggestedAuthorizationText"]
        assert "simsite01" not in handoff["authorizationPackage"]["suggestedAuthorizationText"]
        assert "simsite01" in handoff["authorizationPackage"]["simulatedTarget"]
        handoff_validation = validate_capture_handoff(handoff)
        assert handoff_validation["ok"] is True


def test_capture_handoff_can_select_explicit_route_stage() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "routes", "bind", Path(tmp) / "handoff", allow_command_output=True)
        assert handoff["selectedStage"]["module"] == "routes"
        assert handoff["selectedStage"]["action"] == "bind"
        assert handoff["authorizationPackage"]["authorizationAction"] == "bind_route"
        assert handoff["simulationOnly"] is True
        assert handoff["commandsSuppressed"] is False
        assert handoff["authorizationPackage"]["gateSupported"] is True
        handoff_validation = validate_capture_handoff(handoff, allow_command_output=True)
        assert handoff_validation["ok"] is True


def test_capture_handoff_validator_rejects_simulated_url_in_auth_text() -> None:
    handoff = {
        "kind": "allincms_next_capture_handoff",
        "simulationOnly": True,
        "commandsSuppressed": True,
        "selectedStage": {
            "target": "https://workspace.laicms.com/{realSiteKey}/products",
            "simulatedTarget": "https://workspace.laicms.com/simsite01/products",
        },
        "authorizationPackage": {
            "target": "https://workspace.laicms.com/{realSiteKey}/products",
            "simulatedTarget": "https://workspace.laicms.com/simsite01/products",
            "suggestedAuthorizationText": "授权 https://workspace.laicms.com/simsite01/products",
            "authorizationRecordCommand": None,
            "preMutationGateCommand": None,
            "gateSupported": False,
        },
    }
    validation = validate_capture_handoff(handoff)
    assert validation["ok"] is False
    assert any("authorization text" in issue for issue in validation["issues"])


def test_capture_handoff_validator_accepts_custom_simulated_target_audit() -> None:
    handoff = {
        "kind": "allincms_next_capture_handoff",
        "simulationOnly": True,
        "commandsSuppressed": True,
        "selectedStage": {
            "target": "https://workspace.laicms.com/{realSiteKey}/products",
            "simulatedTarget": "https://workspace.laicms.com/simleddemo1/products",
        },
        "authorizationPackage": {
            "target": "https://workspace.laicms.com/{realSiteKey}/products",
            "simulatedTarget": "https://workspace.laicms.com/simleddemo1/products",
            "suggestedAuthorizationText": "授权 Codex 在 https://workspace.laicms.com/{realSiteKey}/products 执行 create_product_probe",
            "authorizationRecordCommand": None,
            "preMutationGateCommand": None,
            "gateSupported": False,
        },
    }
    validation = validate_capture_handoff(handoff)
    assert validation["ok"] is True


def test_launch_plan_builds_neutral_launch_proof_gates() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        plan = build_launch_plan(Path(tmp), handoff)
        validation = validate_launch_plan(plan)
        assert validation["ok"] is True
        assert plan["kind"] == "allincms_launch_proof_plan"
        assert plan["localOnly"] is True
        assert plan["remoteMutationsPerformed"] is False
        assert plan["contentType"] == "products"
        assert "/products/{slug}" in plan["routePlan"]["detailRoutePatterns"]
        assert plan["routePlan"]["expectedStatusesBeforeUpload"]["/products/{slug}"] == 404
        assert plan["routePlan"]["expectedStatusesAfterSample"]["/products/{slug}"] == 200
        gate_names = {gate["gate"] for gate in plan["proofGates"]}
        assert {"theme_route_launch", "content_schema_capture", "final_frontend_audit"} <= gate_names
        assert "{realSiteKey}" in plan["commandTemplates"]["makeLaunchAuditInputs"]
        assert "simsite01" not in plan["commandTemplates"]["makeLaunchAuditInputs"]


def test_launch_plan_validator_rejects_concrete_or_simulated_user_facing_routes() -> None:
    plan = {
        "kind": "allincms_launch_proof_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "contentType": "products",
        "frontendBaseUrlTemplate": "https://simsite01.web.allincms.com",
        "backendBaseUrlTemplate": "https://workspace.laicms.com/{realSiteKey}",
        "routePlan": {
            "staticPaths": ["/", "/products/custom-slug"],
            "detailRoutePatterns": ["/products/{slug}"],
            "expectedStatusesBeforeUpload": {"/": 200, "/products/{slug}": 404},
            "expectedStatusesAfterSample": {"/": 200, "/products/{slug}": 200},
        },
        "proofGates": [],
    }
    validation = validate_launch_plan(plan)
    assert validation["ok"] is False
    assert any("routePlan.staticPaths" in issue for issue in validation["issues"])
    assert any("frontend template" in issue for issue in validation["issues"])


def test_browser_execution_plan_builds_staged_real_browser_runbook() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        validation = validate_browser_execution_plan(plan)
        assert validation["ok"] is True
        assert plan["kind"] == "allincms_browser_execution_plan"
        assert plan["localOnly"] is True
        assert plan["remoteMutationsPerformed"] is False
        stage_ids = {stage["stageId"] for stage in plan["stages"]}
        assert {
            "refresh_readonly_site_evidence",
            "create_site_submit",
            "module_interface_capture",
            "theme_page_route_launch",
            "save_request_capture",
            "manifest_schema_gate",
            "batch_upload_publish",
            "cleanup_probes",
        } <= stage_ids
        assert any(stage["authorizationRequired"] is True for stage in plan["stages"])
        assert any("JSON replay" in stage["jsonReplayRule"] for stage in plan["stages"])


def test_browser_execution_plan_validator_rejects_simulated_site_key_in_user_facing_fields() -> None:
    plan = {
        "kind": "allincms_browser_execution_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKeyTemplate": "{realSiteKey}",
        "backendBaseUrlTemplate": "https://workspace.laicms.com/{realSiteKey}",
        "frontendBaseUrlTemplate": "https://{realSiteKey}.web.allincms.com",
        "nextSuggestedStage": {"targetTemplate": "https://workspace.laicms.com/simsite01/products"},
        "stages": [
            {
                "stageId": "refresh_readonly_site_evidence",
                "phase": "read-only refresh",
                "mode": "read_only",
                "targetTemplate": "https://workspace.laicms.com/simsite01/products",
                "authorizationRequired": False,
                "allowedActions": ["open page"],
                "stopAfter": "stop",
                "requiredProof": ["proof"],
                "forbiddenActions": ["save"],
                "dependsOn": [],
                "jsonReplayRule": "",
            }
        ],
    }
    validation = validate_browser_execution_plan(plan)
    assert validation["ok"] is False
    assert any("simulated site keys" in issue for issue in validation["issues"])


def test_browser_execution_ledger_tracks_next_safe_stage() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        validation = validate_browser_execution_ledger(ledger)
        assert validation["ok"] is True
        assert ledger["kind"] == "allincms_browser_execution_ledger"
        assert ledger["nextStageId"] == "refresh_readonly_site_evidence"
        assert ledger["stageCounts"]["ready"] == 1
        assert ledger["stageCounts"]["pending"] == ledger["stageCounts"]["total"] - 1
        first = ledger["entries"][0]
        assert first["stageId"] == "refresh_readonly_site_evidence"
        assert first["status"] == "ready"
        assert first["nextAllowedActions"]


def test_browser_execution_ledger_validator_rejects_dependency_jump() -> None:
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePlanKind": "allincms_browser_execution_plan",
        "siteKeyTemplate": "{realSiteKey}",
        "stageCounts": {
            "total": 14,
            "ready": 1,
            "pending": 13,
            "completed": 0,
            "blocked": 0,
            "requiresAuthorization": 1,
        },
        "nextStageId": "create_site_submit",
        "entries": [
            {
                "stageId": "refresh_readonly_site_evidence",
                "phase": "read-only refresh",
                "mode": "read_only",
                "status": "pending",
                "targetTemplate": "https://workspace.laicms.com/sites",
                "authorizationRequired": False,
                "dependsOn": [],
                "requiredProof": ["proof"],
                "stopAfter": "stop",
                "nextAllowedActions": [],
                "blockedUntil": [],
                "evidencePointers": [],
                "proofRecorded": [],
            },
            {
                "stageId": "create_site_submit",
                "phase": "site creation",
                "mode": "requires_authorization",
                "status": "ready",
                "targetTemplate": "https://workspace.laicms.com/sites",
                "authorizationRequired": True,
                "dependsOn": ["refresh_readonly_site_evidence"],
                "requiredProof": ["proof"],
                "stopAfter": "stop",
                "nextAllowedActions": ["submit"],
                "blockedUntil": [],
                "evidencePointers": [],
                "proofRecorded": [],
            },
        ]
        + [
            {
                "stageId": stage_id,
                "phase": "placeholder",
                "mode": "verification",
                "status": "pending",
                "targetTemplate": "local",
                "authorizationRequired": False,
                "dependsOn": ["create_site_submit"],
                "requiredProof": ["proof"],
                "stopAfter": "stop",
                "nextAllowedActions": [],
                "blockedUntil": ["complete:create_site_submit"],
                "evidencePointers": [],
                "proofRecorded": [],
            }
            for stage_id in (
                "setup_pages_inspection",
                "module_interface_capture",
                "theme_page_route_launch",
                "static_frontend_audit",
                "content_probe_create",
                "save_request_capture",
                "publish_sample_verify",
                "manifest_schema_gate",
                "batch_upload_publish",
                "forms_media_settings",
                "final_frontend_audit",
                "cleanup_probes",
            )
        ],
    }
    validation = validate_browser_execution_ledger(ledger)
    assert validation["ok"] is False
    assert any("cannot be ready until dependency" in issue for issue in validation["issues"])


def test_browser_stage_packet_targets_ledger_next_stage() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        packet = build_browser_stage_packet(ledger)
        validation = validate_browser_stage_packet(packet)
        assert validation["ok"] is True
        assert packet["kind"] == "allincms_browser_stage_packet"
        assert packet["stageId"] == ledger["nextStageId"] == "refresh_readonly_site_evidence"
        assert packet["authorizationRequired"] is False
        assert packet["suggestedAuthorizationText"] == ""
        assert packet["evidenceCaptureTemplate"]["status"] == "completed|blocked|partial"
        assert "refresh_readonly_site_evidence" in packet["ledgerUpdate"]["expectedCompletedStageIdsAfterApply"]
        assert packet["ledgerUpdate"]["stageResultRequired"] is True
        assert "completedStageIds" not in packet["ledgerUpdate"]
        assert "apply_browser_stage_result.py" in packet["ledgerUpdate"]["commandTemplate"]
        assert "--result-json" in packet["ledgerUpdate"]["commandTemplate"]
        assert "--completed-stage-ids" not in packet["ledgerUpdate"]["commandTemplate"]
        assert "{ledgerPath}" in packet["ledgerUpdate"]["commandTemplate"]
        assert "{packetPath}" in packet["ledgerUpdate"]["commandTemplate"]
        assert "{stageResultPath}" in packet["ledgerUpdate"]["commandTemplate"]
        assert "{updatedLedgerPath}" in packet["ledgerUpdate"]["commandTemplate"]


def test_browser_stage_evidence_bundle_scaffolds_from_packet() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = str(Path(tmp) / "full")
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(Args.output_dir), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(Args.output_dir), handoff)
        plan = build_browser_execution_plan(Path(Args.output_dir), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        packet = build_browser_stage_packet(ledger)
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_dir = Path(tmp) / "stage-proof"
        manifest = prepare_browser_stage_evidence_bundle(packet_path, output_dir)
        template = json.loads((output_dir / "stage-result-template.json").read_text(encoding="utf-8"))
        notes = (output_dir / "notes.md").read_text(encoding="utf-8")

    assert manifest["kind"] == "allincms_browser_stage_evidence_bundle"
    assert manifest["stageId"] == packet["stageId"]
    assert manifest["authorizationRequired"] == packet["authorizationRequired"]
    assert manifest["remoteMutationExpectation"] == packet["remoteMutationExpectation"]
    assert manifest["localOnly"] is True
    assert manifest["remoteMutationsPerformed"] is False
    assert "stage-result.json" in manifest["expectedEvidenceFiles"]
    assert "does not authorize" in manifest["warning"]
    assert template["stageId"] == packet["stageId"]
    assert template["status"] == "partial"
    assert template["proofRecorded"] == []
    assert template["browserStageMutatedRemote"] is False
    assert "Required Proof" in notes


def build_test_browser_stage_evidence_bundle(tmp: str) -> tuple[dict, Path, Path]:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    Args.output_dir = str(Path(tmp) / "full")
    simulate_full_e2e_chain.run_simulation(Args())
    handoff = build_capture_handoff(Path(Args.output_dir), "", "", Path(tmp) / "handoff")
    launch_plan = build_launch_plan(Path(Args.output_dir), handoff)
    plan = build_browser_execution_plan(Path(Args.output_dir), handoff, launch_plan)
    ledger = build_browser_execution_ledger(plan)
    packet = build_browser_stage_packet(ledger)
    packet_path = Path(tmp) / "packet.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_dir = Path(tmp) / "stage-proof"
    prepare_browser_stage_evidence_bundle(packet_path, output_dir)
    return packet, packet_path, output_dir


def create_site_submit_packet() -> dict:
    return {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "create_site_submit",
        "recovery": False,
        "phase": "site creation",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": True,
        "remoteMutationExpectation": "must",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/sites 执行 stage=create_site_submit",
        "allowedActions": ["submit create-site form"],
        "requiredProof": ["create-site preflight", "action-specific authorization record", "backend proof"],
        "forbiddenActions": ["batch upload"],
        "stopAfter": "stop after site card and dashboard proof",
        "evidenceCaptureTemplate": {
            "stageId": "create_site_submit",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": True,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["create_site_submit"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }


def test_browser_stage_evidence_bundle_validator_accepts_generated_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet, packet_path, output_dir = build_test_browser_stage_evidence_bundle(tmp)
        validation = validate_browser_stage_evidence_bundle(output_dir, packet_path)

    assert validation["ok"] is True, validation["issues"]
    assert validation["stageId"] == packet["stageId"]


def test_browser_stage_evidence_bundle_validator_rejects_stage_id_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _packet, packet_path, output_dir = build_test_browser_stage_evidence_bundle(tmp)
        manifest_path = output_dir / "evidence-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["stageId"] = "create_site_submit"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_browser_stage_evidence_bundle(output_dir, packet_path)

    assert validation["ok"] is False
    assert any("stageId must match" in issue for issue in validation["issues"])


def test_browser_stage_evidence_bundle_validator_rejects_completed_template() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet, packet_path, output_dir = build_test_browser_stage_evidence_bundle(tmp)
        template_path = output_dir / "stage-result-template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["status"] = "completed"
        template["proofRecorded"] = list(packet["requiredProof"])
        template["redactedEvidencePointers"] = ["local://premature-proof.json"]
        template["blockingIssues"] = []
        template_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_browser_stage_evidence_bundle(output_dir, packet_path)

    assert validation["ok"] is False
    assert any("template must start partial" in issue for issue in validation["issues"])


def test_browser_stage_evidence_bundle_validator_rejects_missing_notes_rules() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _packet, packet_path, output_dir = build_test_browser_stage_evidence_bundle(tmp)
        (output_dir / "notes.md").write_text("notes missing the evidence contract\n", encoding="utf-8")
        validation = validate_browser_stage_evidence_bundle(output_dir, packet_path)

    assert validation["ok"] is False
    assert any("notes must include Required Proof" in issue for issue in validation["issues"])
    assert any("notes must state the bundle is not authorization" in issue for issue in validation["issues"])


def test_browser_stage_authorization_package_for_create_site() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-create-site-preflight.json",
        "/tmp/allincms-authorization-create-site.json",
    )
    assert package["stageId"] == "create_site_submit"
    assert package["gateSupported"] is True
    assert "创建站点" in package["suggestedAuthorizationText"]
    assert "make_authorization_record.py --action create_site" in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_site" in package["preMutationGateCommand"]
    assert "--preflight /tmp/allincms-create-site-preflight.json" in package["preMutationGateCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert validate_browser_stage_authorization_package(package, packet, create_preflight_evidence(), now=GATE_NOW) == []


def test_browser_stage_authorization_package_validator_rejects_missing_user_authorization_placeholder() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-create-site-preflight.json",
        "/tmp/allincms-authorization-create-site.json",
    )
    package["authorizationRecordCommand"] = package["authorizationRecordCommand"].replace(
        "<paste current user authorization text here>",
        "current user authorized in an earlier chat",
    )
    issues = validate_browser_stage_authorization_package(package, packet, create_preflight_evidence(), now=GATE_NOW)

    assert any("current-user authorization placeholder" in issue for issue in issues)


def test_browser_stage_authorization_package_validator_rejects_missing_warning() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-create-site-preflight.json",
        "/tmp/allincms-authorization-create-site.json",
    )
    package.pop("warning")
    issues = validate_browser_stage_authorization_package(package, packet, create_preflight_evidence(), now=GATE_NOW)

    assert any("package.warning is required" in issue for issue in issues)


def test_browser_stage_authorization_package_validator_rejects_stale_preflight() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-create-site-preflight.json",
        "/tmp/allincms-authorization-create-site.json",
    )
    preflight = create_preflight_evidence()
    preflight["generatedAt"] = STALE_AT
    issues = validate_browser_stage_authorization_package(package, packet, preflight, now=GATE_NOW)

    assert any("preflight freshness: preflight: generatedAt is stale" in issue for issue in issues), issues


def test_browser_stage_authorization_package_marks_readonly_stage_unsupported() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "remoteMutationExpectation": "must_not",
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog"],
        "forbiddenActions": ["submit forms"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    package = build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    assert package["authorizationRequired"] is False
    assert package["gateSupported"] is False
    assert package["authorizationRecordCommand"] is None
    assert package["preMutationGateCommand"] is None


def test_browser_stage_authorization_package_for_module_capture_uses_next_coverage_stage() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        paths = simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        packet = build_browser_stage_packet(ledger)
        first_result = build_stage_result(packet["stageId"], "completed", ["local://refresh.json"], packet["requiredProof"], [])
        after_refresh = apply_stage_result(ledger, packet, first_result)
        create_packet = build_browser_stage_packet(after_refresh)
        create_result = build_stage_result(
            create_packet["stageId"],
            "completed",
            ["local://created-site.json"],
            create_packet["requiredProof"],
            [],
            True,
        )
        after_create = apply_stage_result(after_refresh, create_packet, create_result)
        setup_packet = build_browser_stage_packet(after_create)
        setup_result = build_stage_result(setup_packet["stageId"], "completed", ["local://setup.json"], setup_packet["requiredProof"], [])
        after_setup = apply_stage_result(after_create, setup_packet, setup_result)
        module_packet = build_browser_stage_packet(after_setup)
        capture_plan = json.loads(Path(paths["moduleCapturePlan"]).read_text(encoding="utf-8"))
        first_stage = capture_plan["stages"][0]
        one_result = build_capture_result(
            first_stage["module"],
            first_stage["action"],
            "captured",
            ["request capture"],
            ["local://products-create.json"],
            [],
        )
        coverage = update_coverage(capture_plan, one_result)
        coverage_path = Path(tmp) / "coverage-after-one.json"
        coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = build_browser_stage_authorization_package(
            module_packet,
            "/tmp/allincms-created-site-evidence.json",
            "/tmp/allincms-authorization-module-capture.json",
            str(paths["moduleCapturePlan"]),
            str(coverage_path),
        )
        assert package["stageId"] == "module_interface_capture"
        assert package["captureStage"]["module"] == "posts"
        assert package["captureStage"]["action"] == "create"
    assert package["captureStage"]["authorizationAction"] == "create_post_probe"
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert "{realSiteKey}" in package["suggestedAuthorizationText"]
    assert "simsite01" not in package["suggestedAuthorizationText"]
    assert validate_browser_stage_authorization_package(package, module_packet, None, capture_plan) == []


def test_browser_stage_authorization_package_for_module_capture_can_allow_simulated_commands() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 stage=module_interface_capture",
        "allowedActions": ["run exactly one capture-plan stage"],
        "requiredProof": ["fresh authorization", "captured request or explicit UI-only finding"],
        "forbiddenActions": ["batch replay"],
        "stopAfter": "stop after one module/action capture",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    plan = {
        "kind": "allincms_module_capture_plan",
        "siteKey": "simsite01",
        "jsonReplayReady": False,
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "target": "https://workspace.laicms.com/simsite01/products",
                "authorizationAction": "create_product_probe",
                "stopAfter": "probe draft is verified",
                "mustCapture": ["draft row"],
                "requiredProof": ["request capture"],
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/preflight.json",
            "/tmp/auth.json",
            str(plan_path),
            "",
            True,
        )
    assert package["gateSupported"] is True
    assert package.get("commandsSuppressed") is not True
    assert "make_authorization_record.py --action create_product_probe" in package["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert "授权 Codex" not in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_product_probe" in package["preMutationGateCommand"]
    assert validate_browser_stage_authorization_package(package, packet, None, plan) == []


def test_browser_stage_authorization_package_validator_rejects_module_capture_plan_drift() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 stage=module_interface_capture",
        "allowedActions": ["run exactly one capture-plan stage"],
        "requiredProof": ["fresh authorization", "captured request or explicit UI-only finding"],
        "forbiddenActions": ["batch replay"],
        "stopAfter": "stop after one module/action capture",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    plan = {
        "kind": "allincms_module_capture_plan",
        "siteKey": "mysite01",
        "jsonReplayReady": False,
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "target": "https://workspace.laicms.com/mysite01/products",
                "authorizationAction": "create_product_probe",
                "stopAfter": "probe draft is verified",
                "mustCapture": ["draft row"],
                "requiredProof": ["request capture"],
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/preflight.json",
            "/tmp/auth.json",
            str(plan_path),
            "",
        )
    package["captureStage"]["action"] = "update"
    package["target"] = "https://workspace.laicms.com/mysite01/posts"
    issues = validate_browser_stage_authorization_package(package, packet, None, plan)

    assert any("captureStage must match capture plan" in issue for issue in issues)
    assert any("package.target must include captureStage.module" in issue for issue in issues)


def test_next_browser_action_handoff_wraps_valid_module_capture_package() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 stage=module_interface_capture",
        "allowedActions": ["run exactly one capture-plan stage"],
        "requiredProof": ["fresh authorization", "captured request or explicit UI-only finding"],
        "forbiddenActions": ["batch replay"],
        "stopAfter": "stop after one module/action capture",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    plan = {
        "kind": "allincms_module_capture_plan",
        "siteKey": "mysite01",
        "jsonReplayReady": False,
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "target": "https://workspace.laicms.com/mysite01/products",
                "authorizationAction": "create_product_probe",
                "stopAfter": "probe draft is verified",
                "mustCapture": ["draft row"],
                "requiredProof": ["request capture"],
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/preflight.json",
            "/tmp/auth.json",
            str(plan_path),
            "",
            True,
        )
    preflight = recent_base_evidence()
    handoff = build_next_browser_action_handoff(
        package=package,
        packet=packet,
        preflight=preflight,
        capture_plan=plan,
        package_path="/tmp/package.json",
        packet_path="/tmp/packet.json",
        preflight_path="/tmp/preflight.json",
        capture_plan_path="/tmp/plan.json",
        now=GATE_NOW,
    )
    assert handoff["kind"] == "allincms_next_browser_action_handoff"
    assert handoff["preparedOnly"] is True
    assert handoff["isUserAuthorization"] is False
    assert handoff["remoteMutationsPerformed"] is False
    assert handoff["action"]["authorizationAction"] == "create_product_probe"
    assert handoff["sourceFiles"]["authorizationPackage"] == "/tmp/package.json"
    assert "not user authorization" in handoff["warning"]


def test_next_browser_action_handoff_validator_reopens_sources() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 stage=module_interface_capture",
        "allowedActions": ["run exactly one capture-plan stage"],
        "requiredProof": ["fresh authorization", "captured request or explicit UI-only finding"],
        "forbiddenActions": ["batch replay"],
        "stopAfter": "stop after one module/action capture",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    plan = {
        "kind": "allincms_module_capture_plan",
        "siteKey": "mysite01",
        "jsonReplayReady": False,
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "target": "https://workspace.laicms.com/mysite01/products",
                "authorizationAction": "create_product_probe",
                "stopAfter": "probe draft is verified",
                "mustCapture": ["draft row"],
                "requiredProof": ["request capture"],
            }
        ],
    }
    preflight = recent_base_evidence()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        packet_path = tmp_path / "packet.json"
        preflight_path = tmp_path / "preflight.json"
        plan_path = tmp_path / "plan.json"
        package_path = tmp_path / "package.json"
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        preflight_path.write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        package = build_browser_stage_authorization_package(
            packet,
            str(preflight_path),
            str(tmp_path / "authorization.json"),
            str(plan_path),
            "",
            True,
        )
        package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        handoff = build_next_browser_action_handoff(
            package=package,
            packet=packet,
            preflight=preflight,
            capture_plan=plan,
            package_path=str(package_path),
            packet_path=str(packet_path),
            preflight_path=str(preflight_path),
            capture_plan_path=str(plan_path),
            now=GATE_NOW,
        )
        result = validate_next_browser_action_handoff(handoff, now=GATE_NOW)

    assert result["ok"] is True, result["issues"]


def test_next_browser_action_handoff_validator_rejects_handoff_drift() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    handoff = build_next_browser_action_handoff(
        package=package,
        packet=packet,
        preflight=create_preflight_evidence(),
        capture_plan=None,
        package_path="/tmp/package.json",
        packet_path="/tmp/packet.json",
        preflight_path="/tmp/preflight.json",
        capture_plan_path="",
        now=GATE_NOW,
    )
    handoff["target"] = "https://workspace.laicms.com/mysite01/products"
    handoff["authorizationRecordCommand"] = str(handoff["authorizationRecordCommand"]).replace(
        "<paste current user authorization text here>",
        "current user authorized yesterday",
    )
    result = validate_next_browser_action_handoff(handoff, package, packet, create_preflight_evidence(), None, now=GATE_NOW)

    assert result["ok"] is False
    assert any("handoff.target must match authorization package" in issue for issue in result["issues"])
    assert any("current-user authorization placeholder" in issue for issue in result["issues"])


def test_next_browser_action_handoff_rejects_invalid_package() -> None:
    packet = create_site_submit_packet()
    package = build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    package["stageId"] = "wrong_stage"
    try:
        build_next_browser_action_handoff(
            package=package,
            packet=packet,
            preflight=create_preflight_evidence(),
            capture_plan=None,
            package_path="/tmp/package.json",
            packet_path="/tmp/packet.json",
            preflight_path="/tmp/preflight.json",
            capture_plan_path="",
            now=GATE_NOW,
        )
    except ValueError as exc:
        assert "browser-stage authorization package is invalid" in str(exc)
    else:
        raise AssertionError("next browser action handoff accepted invalid package")


def module_capture_handoff_fixture(tmp_path: Path, preflight: dict | None = None) -> Path:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "generatedAt": RECENT_PREFLIGHT_AT,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": (
            "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 "
            "stage=module_interface_capture；完成 requiredProof 后停止。"
        ),
        "allowedActions": ["capture one module create behavior"],
        "requiredProof": ["probe draft or dialog state verified"],
        "forbiddenActions": ["save", "publish", "delete", "batch upload"],
        "stopAfter": "probe draft or dialog state is verified",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "redactedEvidencePointers": [],
            "proofRecorded": ["probe draft or dialog state verified"],
            "blockingIssues": [],
            "operatorNote": "",
            "browserStageMutatedRemote": True,
        },
        "ledgerUpdate": {
            "afterStageCompletes": "Apply a completed, partial, or blocked stage result after redacted evidence is recorded.",
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.after.json"
            ),
        },
        "warnings": ["This packet is local-only and does not authorize remote LAICMS mutation."],
    }
    plan = {
        "kind": "allincms_module_capture_plan",
        "siteKey": "mysite01",
        "jsonReplayReady": False,
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "target": "https://workspace.laicms.com/mysite01/products",
                "authorizationAction": "create_product_probe",
                "stopAfter": "probe draft is verified",
                "mustCapture": ["draft row"],
                "requiredProof": ["request capture"],
            }
        ],
    }
    preflight_data = preflight or recent_base_evidence()
    packet_path = tmp_path / "packet.json"
    preflight_path = tmp_path / "preflight.json"
    plan_path = tmp_path / "plan.json"
    package_path = tmp_path / "package.json"
    handoff_path = tmp_path / "handoff.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preflight_path.write_text(json.dumps(preflight_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    package = build_browser_stage_authorization_package(
        packet,
        str(preflight_path),
        str(tmp_path / "authorization.json"),
        str(plan_path),
        "",
        True,
    )
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff = build_next_browser_action_handoff(
        package=package,
        packet=packet,
        preflight=preflight_data,
        capture_plan=plan,
        package_path=str(package_path),
        packet_path=str(packet_path),
        preflight_path=str(preflight_path),
        capture_plan_path=str(plan_path),
        now=GATE_NOW,
    )
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return handoff_path


def test_handoff_readiness_marks_fresh_handoff_ready_to_request_authorization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        handoff_path = module_capture_handoff_fixture(Path(tmp))
        report = build_handoff_readiness_report(handoff_path, now=GATE_NOW)

    assert report["kind"] == "allincms_next_browser_action_handoff_readiness"
    assert report["remoteMutationsPerformed"] is False
    assert report["status"] == "ready_to_request_authorization"
    assert report["evidenceFreshness"]["freshForMutation"] is True
    assert report["blockers"] == []
    assert "exact action-time authorization" in report["nextAction"]


def test_handoff_readiness_blocks_stale_preflight_before_authorization_request() -> None:
    stale_preflight = recent_base_evidence()
    stale_preflight["generatedAt"] = STALE_AT
    with tempfile.TemporaryDirectory() as tmp:
        handoff_path = module_capture_handoff_fixture(Path(tmp))
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        preflight_path = Path(handoff["sourceFiles"]["preflight"])
        preflight_path.write_text(json.dumps(stale_preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = build_handoff_readiness_report(handoff_path, now=GATE_NOW)

    assert report["status"] == "blocked_refresh_readonly_evidence"
    assert "preflight_not_fresh_for_mutation" in report["blockers"]
    assert report["evidenceFreshness"]["reason"] == "stale"
    assert "refresh read-only evidence" in report["nextAction"]


def test_browser_stage_authorization_readiness_accepts_fresh_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_path = module_capture_handoff_fixture(tmp_path)
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        package_path = Path(handoff["sourceFiles"]["authorizationPackage"])
        packet_path = Path(handoff["sourceFiles"]["browserStagePacket"])
        preflight_path = Path(handoff["sourceFiles"]["preflight"])
        capture_plan_path = Path(handoff["sourceFiles"]["capturePlan"])
        report = build_browser_stage_authorization_readiness_report(
            package_path,
            packet_path=packet_path,
            preflight_path=preflight_path,
            capture_plan_path=capture_plan_path,
            now=GATE_NOW,
        )

    assert report["kind"] == "allincms_next_browser_action_handoff_readiness"
    assert report["status"] == "ready_to_request_authorization"
    assert report["validation"]["ok"] is True
    assert report["action"]["authorizationAction"] == "create_product_probe"
    assert report["target"] == "https://workspace.laicms.com/mysite01/products"
    assert report["preparedOnly"] is True
    assert report["isUserAuthorization"] is False
    assert report["remoteMutationsPerformed"] is False
    assert "授权 Codex" in report["authorizationTextFromPackage"]


def test_browser_stage_authorization_readiness_blocks_stale_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        handoff_path = module_capture_handoff_fixture(tmp_path)
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        package_path = Path(handoff["sourceFiles"]["authorizationPackage"])
        packet_path = Path(handoff["sourceFiles"]["browserStagePacket"])
        preflight_path = Path(handoff["sourceFiles"]["preflight"])
        capture_plan_path = Path(handoff["sourceFiles"]["capturePlan"])
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        preflight["generatedAt"] = STALE_AT
        preflight_path.write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = build_browser_stage_authorization_readiness_report(
            package_path,
            packet_path=packet_path,
            preflight_path=preflight_path,
            capture_plan_path=capture_plan_path,
            now=GATE_NOW,
        )

    assert report["status"] == "blocked_refresh_readonly_evidence"
    assert "browser_stage_authorization_package_validation_failed" in report["blockers"]
    assert "preflight_not_fresh_for_mutation" in report["blockers"]
    assert report["evidenceFreshness"]["reason"] == "stale"


def upload_readiness_fixture() -> dict:
    return {
        "kind": "allincms_manifest_upload_readiness_report",
        "generatedAt": RECENT_PREFLIGHT_AT,
        "remoteMutationsPerformed": False,
        "contentTypes": ["posts", "products"],
        "manifestCount": 2,
        "readyCount": 0,
        "blockedCount": 2,
        "overallStatus": "blocked",
        "manifests": [
            {
                "path": "/tmp/products.json",
                "contentType": "products",
                "siteKey": "mysite01",
                "schemaVerified": False,
                "itemCount": 3,
                "status": "blocked",
                "blockers": ["schema_gate_not_passed"],
            },
            {
                "path": "/tmp/posts.json",
                "contentType": "posts",
                "siteKey": "mysite01",
                "schemaVerified": False,
                "itemCount": 2,
                "status": "blocked",
                "blockers": ["schema_gate_not_passed"],
            },
        ],
    }


def source_input_requirements_fixture() -> dict:
    return {
        "kind": "allincms_source_input_requirements",
        "generatedAt": RECENT_PREFLIGHT_AT,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": "mysite01",
        "overallStatus": "blocked",
        "contentTypes": {
            "products": {
                "sectionStatus": "blocked",
                "blockedFields": ["content/body", "main media"],
            },
            "posts": {
                "sectionStatus": "blocked",
                "blockedFields": ["content/body", "cover image"],
            },
        },
        "blockedUntil": [
            "products.content/body: capture schema or record explicit omission/acceptance rule",
            "products.main media: capture schema or record explicit omission/acceptance rule",
            "posts.content/body: capture schema or record explicit omission/acceptance rule",
        ],
    }


def run_summary_next_action_fixture() -> dict:
    return {
        "valid": True,
        "complete": False,
        "siteKey": "mysite01",
        "contentType": "products",
        "evidenceFreshness": {
            "freshForMutation": True,
            "reason": "fresh",
        },
        "nextActions": ["authorize_content_probe"],
        "nextActionDetails": [
            {
                "action": "create_product_probe",
                "target": "https://workspace.laicms.com/mysite01/products",
                "authorizationText": (
                    "授权 Codex 在 https://workspace.laicms.com/mysite01/products 创建一个 "
                    "Codex Probe - Delete Me 产品草稿，用于捕获产品字段和保存请求；"
                    "本次只允许创建 probe 草稿，不发布、不删除、不批量上传，保存和清理另行授权。"
                ),
            }
        ],
    }


def test_browser_stage_queue_marks_only_product_probe_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        handoff_path = module_capture_handoff_fixture(Path(tmp))
        readiness = build_handoff_readiness_report(handoff_path, now=GATE_NOW)
        queue = build_browser_stage_queue(
            readiness,
            upload_readiness_fixture(),
            readiness_path=str(handoff_path.with_name("readiness.json")),
            upload_readiness_path="/tmp/upload-readiness.json",
            products_manifest="/tmp/products.json",
            posts_manifest="/tmp/posts.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )

    errors = validate_browser_stage_queue(queue)
    assert not errors, "\n".join(errors)
    assert queue["kind"] == "allincms_browser_stage_authorization_queue"
    assert len(queue["queue"]) == 10
    ready = [item["id"] for item in queue["queue"] if item["status"] == "ready_to_request_authorization"]
    assert ready == ["products_create_probe"]
    assert queue["queue"][8]["id"] == "batch_upload_publish"
    assert queue["queue"][8]["status"] == "waiting_for_schema_gate_and_user_authorization"
    assert "授权 Codex" in queue["queue"][0]["authorizationText"]


def test_browser_stage_queue_can_be_built_from_run_summary_next_action() -> None:
    queue = build_browser_stage_queue_from_summary(
        run_summary_next_action_fixture(),
        upload_readiness_fixture(),
        summary_path="/tmp/run-summary.json",
        upload_readiness_path="/tmp/upload-readiness.json",
        products_manifest="/tmp/products.json",
        posts_manifest="/tmp/posts.json",
    )

    errors = validate_browser_stage_queue(queue)
    assert not errors, "\n".join(errors)
    ready = [item["id"] for item in queue["queue"] if item["status"] == "ready_to_request_authorization"]
    assert ready == ["products_create_probe"]
    assert queue["sourceArtifacts"]["runSummary"] == "/tmp/run-summary.json"
    assert queue["sourceArtifacts"]["summaryNextActionDetail"] == "create_product_probe"
    assert "保存和清理另行授权" in queue["queue"][0]["authorizationText"]


def test_browser_stage_queue_blocks_first_stage_when_readiness_is_stale() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        handoff_path = module_capture_handoff_fixture(Path(tmp))
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        preflight_path = Path(handoff["sourceFiles"]["preflight"])
        stale_preflight = recent_base_evidence()
        stale_preflight["generatedAt"] = STALE_AT
        preflight_path.write_text(json.dumps(stale_preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        readiness = build_handoff_readiness_report(handoff_path, now=GATE_NOW)
        queue = build_browser_stage_queue(
            readiness,
            upload_readiness_fixture(),
            readiness_path=str(handoff_path.with_name("readiness.json")),
            upload_readiness_path="/tmp/upload-readiness.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )

    errors = validate_browser_stage_queue(queue)
    assert not errors, "\n".join(errors)
    ready = [item["id"] for item in queue["queue"] if item["status"] == "ready_to_request_authorization"]
    assert ready == []
    assert queue["queue"][0]["status"] == "blocked_refresh_readonly_evidence"
    assert "refresh read-only evidence" in queue["queue"][0]["authorizationNeeded"]


def test_e2e_gap_audit_reports_remaining_proof_after_stage_queue() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        handoff_path = module_capture_handoff_fixture(Path(tmp))
        readiness = build_handoff_readiness_report(handoff_path, now=GATE_NOW)
        upload_readiness = upload_readiness_fixture()
        queue = build_browser_stage_queue(
            readiness,
            upload_readiness,
            readiness_path=str(handoff_path.with_name("readiness.json")),
            upload_readiness_path="/tmp/upload-readiness.json",
            products_manifest="/tmp/products.json",
            posts_manifest="/tmp/posts.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
        evidence = recent_base_evidence()
        evidence["siteCreation"]["status"] = "existing_site_selected"
        audit = build_e2e_gap_audit(
            evidence,
            upload_readiness,
            queue,
            objective="simulate site-build and content upload",
            evidence_path="/tmp/evidence.json",
            upload_readiness_path="/tmp/upload-readiness.json",
            queue_path="/tmp/queue.json",
            source_input_requirements=source_input_requirements_fixture(),
            source_input_requirements_path="/tmp/source-input-requirements.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )

    errors = validate_e2e_gap_audit(audit)
    assert not errors, "\n".join(errors)
    assert audit["kind"] == "allincms_e2e_goal_gap_audit"
    assert audit["completionVerdict"]["complete"] is False
    assert audit["nextAuthorizedActionNeeded"]["action"] == "create_product_probe"
    assert audit["site"]["siteCreationProofStatus"] == "existing-site continuation; not fresh proof of new site creation in this run"
    assert audit["currentEvidence"]["sourceInputRequirements"] == "/tmp/source-input-requirements.json"
    assert audit["sourceInputRequirements"]["status"] == "blocked"
    assert audit["sourceInputRequirements"]["blockedUntilCount"] == 3
    assert any(
        item["requirement"] == "generate manifests from source materials" and item["status"] == "blocked"
        for item in audit["notYetProven"]
    )
    assert any(item["requirement"] == "capture posts save request and payload template" for item in audit["notYetProven"])


def test_probe_save_handoff_builds_non_authorizing_save_package() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    handoff = build_probe_save_handoff(
        create_evidence=create_evidence,
        create_evidence_path="/tmp/create-evidence.json",
        preflight_path="/tmp/preflight.json",
        edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        authorization_output="/tmp/save-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )

    errors = validate_probe_save_handoff(handoff)
    assert not errors, "\n".join(errors)
    assert handoff["preparedOnly"] is True
    assert handoff["isUserAuthorization"] is False
    assert "saving the probe" in handoff["automationPreference"]["doesNotAuthorize"]
    assert "action-time authorization" in handoff["automationPreference"]["rule"]
    assert handoff["action"] == "save_probe"
    assert "保存一次" in handoff["suggestedAuthorizationText"]
    assert "捕获保存请求" in handoff["suggestedAuthorizationText"]
    assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
    assert "--action save_probe" in handoff["preMutationGateCommand"]


def test_source_input_gap_ledger_records_blockers_and_user_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "source-input-gaps.json"

        Args = type("Args", (), {})
        Args.action = "append"
        Args.output = str(output)
        Args.site_key = "mysite01"
        Args.content_type = "products"
        Args.field = "specifications"
        Args.target = "products.specifications"
        Args.classification = "recommended,source-derived,blocked-until-schema-captured"
        Args.source_hint = "catalog rows for wattage, lumen, voltage, dimensions, certifications"
        Args.generation_rule = "Generate structured rows only after spec row schema capture."
        Args.current_evidence = "blocked"
        Args.decision_needed = "needs-schema-capture"
        Args.evidence_pointer = "/tmp/redacted-product-edit-evidence.json"
        Args.operator_note = "Spec control visible but nested schema is not captured."

        ledger = record_source_input_gap.apply_action(Args())
        assert ledger["kind"] == "allincms_source_input_gap_ledger"
        assert ledger["siteKey"] == "mysite01"
        assert ledger["summary"]["entryCount"] == 1
        assert ledger["summary"]["blockedFields"] == ["products.specifications"]
        assert ledger["summary"]["byDecisionNeeded"]["needs-schema-capture"] == 1


def test_source_input_gap_ledger_rejects_skill_package_output() -> None:
    Args = type("Args", (), {})
    Args.action = "init"
    Args.output = str(Path(__file__).resolve().parents[1] / "source-input-gaps.json")
    Args.site_key = ""

    try:
        record_source_input_gap.apply_action(Args())
    except SystemExit as exc:
        assert "outside the skill package" in str(exc)
    else:
        raise AssertionError("expected skill-package output path to be rejected")


def test_source_input_gap_ledger_requires_extraction_contract_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Args = type("Args", (), {})
        Args.action = "append"
        Args.output = str(Path(tmp) / "source-input-gaps.json")
        Args.site_key = "mysite01"
        Args.content_type = "products"
        Args.field = "specifications"
        Args.target = "products.specifications"
        Args.classification = "recommended,source-derived,blocked-until-schema-captured"
        Args.source_hint = ""
        Args.generation_rule = ""
        Args.current_evidence = "blocked"
        Args.decision_needed = "needs-schema-capture"
        Args.evidence_pointer = ""
        Args.operator_note = ""

        try:
            record_source_input_gap.apply_action(Args())
        except SystemExit as exc:
            message = str(exc)
            assert "sourceHint is required" in message
            assert "generationRule is required" in message
            assert "evidencePointer is required" in message
        else:
            raise AssertionError("expected missing extraction contract fields to be rejected")


def test_source_input_gap_ledger_requires_operator_note_for_claimed_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Args = type("Args", (), {})
        Args.action = "append"
        Args.output = str(Path(tmp) / "source-input-gaps.json")
        Args.site_key = "mysite01"
        Args.content_type = "products"
        Args.field = "description"
        Args.target = "products.description"
        Args.classification = "required,source-derived"
        Args.source_hint = "catalog summary paragraph"
        Args.generation_rule = "Summarize into one plain-text product description."
        Args.current_evidence = "request-captured"
        Args.decision_needed = "can-infer-from-source"
        Args.evidence_pointer = "/tmp/redacted-save-evidence.json"
        Args.operator_note = ""

        try:
            record_source_input_gap.apply_action(Args())
        except SystemExit as exc:
            assert "operatorNote is required" in str(exc)
        else:
            raise AssertionError("expected claimed proof without operator note to be rejected")


def test_source_input_gap_ledger_validate_ledger_accepts_complete_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Args = type("Args", (), {})
        Args.action = "append"
        Args.output = str(Path(tmp) / "source-input-gaps.json")
        Args.site_key = "mysite01"
        Args.content_type = "products"
        Args.field = "certifications"
        Args.target = "products.certifications"
        Args.classification = "recommended,source-derived,blocked-until-schema-captured"
        Args.source_hint = "catalog certification badges or datasheet compliance section"
        Args.generation_rule = "Normalize certification names only after target field/schema is captured."
        Args.current_evidence = "blocked"
        Args.decision_needed = "needs-schema-capture"
        Args.evidence_pointer = "/tmp/redacted-product-field-evidence.json"
        Args.operator_note = "Certification field is planned but no current request schema was captured."

        ledger = record_source_input_gap.apply_action(Args())
        errors = record_source_input_gap.validate_ledger(ledger, expected_site_key="mysite01")
        assert not errors, "\n".join(errors)


def test_source_input_gap_ledger_validate_ledger_rejects_merged_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Args = type("Args", (), {})
        Args.action = "append"
        Args.output = str(Path(tmp) / "source-input-gaps.json")
        Args.site_key = "mysite01"
        Args.content_type = "forms"
        Args.field = "inquiry destination"
        Args.target = "forms.submit.destination"
        Args.classification = "required,user-confirmed,blocked-until-schema-captured"
        Args.source_hint = "public contact policy from user brief"
        Args.generation_rule = "Use only user-approved public destination after form submit schema capture."
        Args.current_evidence = "ui-only"
        Args.decision_needed = "needs-user-confirmation"
        Args.evidence_pointer = "/tmp/redacted-form-editor-evidence.json"
        Args.operator_note = "Form editor showed submit controls but no request schema was captured."

        ledger = record_source_input_gap.apply_action(Args())
        ledger["entries"].append(dict(ledger["entries"][0]))
        ledger["summary"]["entryCount"] = 1
        errors = record_source_input_gap.validate_ledger(ledger, expected_site_key="mysite01")
        assert any("duplicates contentType/field/target" in error for error in errors), errors
        assert any("summary.entryCount does not match entries" in error for error in errors), errors


def test_source_input_requirements_merges_operation_gap_ledgers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "source-input-gaps.json"

        GapArgs = type("GapArgs", (), {})
        GapArgs.action = "append"
        GapArgs.output = str(ledger_path)
        GapArgs.site_key = "mysite01"
        GapArgs.content_type = "forms"
        GapArgs.field = "inquiry destination"
        GapArgs.target = "forms.submit.destination"
        GapArgs.classification = "required,user-confirmed,blocked-until-schema-captured"
        GapArgs.source_hint = "public contact policy from user brief"
        GapArgs.generation_rule = "Use only user-approved public destination after form submit schema capture."
        GapArgs.current_evidence = "ui-only"
        GapArgs.decision_needed = "needs-user-confirmation"
        GapArgs.evidence_pointer = "/tmp/redacted-form-editor-evidence.json"
        GapArgs.operator_note = "Form editor showed submit controls but no request schema was captured."
        ledger = record_source_input_gap.apply_action(GapArgs())
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        ReqArgs = type("ReqArgs", (), {})
        ReqArgs.site_key = "mysite01"
        ReqArgs.content_types = "forms"
        ReqArgs.source_types = "pdf_catalog,plain_brief"
        ReqArgs.manifest = []
        ReqArgs.save_capture_evidence = []
        ReqArgs.media_evidence = None
        ReqArgs.readiness_evidence = None
        ReqArgs.gap_ledger = [str(ledger_path)]

        report = build_source_input_requirements_report(ReqArgs())

    assert report["operationGaps"]["entryCount"] == 1
    assert report["operationGaps"]["blockedFields"] == ["forms.inquiry destination"]
    assert report["operationGaps"]["userInputFields"] == ["forms.inquiry destination"]
    assert any("forms.inquiry destination" in item for item in report["blockedUntil"])
    assert any("operation-time fields" in item for item in report["nextBestInputFromUser"])


def test_source_input_requirements_filters_resolved_operation_gaps() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "source-input-gaps.json"
        resolved_path = Path(tmp) / "resolved-gaps.json"

        GapArgs = type("GapArgs", (), {})
        GapArgs.action = "append"
        GapArgs.output = str(ledger_path)
        GapArgs.site_key = "mysite01"
        GapArgs.content_type = "products"
        GapArgs.field = "specifications"
        GapArgs.target = "products.specifications"
        GapArgs.classification = "recommended,source-derived,blocked-until-schema-captured"
        GapArgs.source_hint = "product datasheet spec rows"
        GapArgs.generation_rule = "Generate structured spec rows after schema capture."
        GapArgs.current_evidence = "ui-only"
        GapArgs.decision_needed = "needs-schema-capture"
        GapArgs.evidence_pointer = "/tmp/redacted-product-spec-ui.json"
        GapArgs.operator_note = "Product editor showed spec rows but save behavior was not captured yet."
        ledger = record_source_input_gap.apply_action(GapArgs())
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        resolved_path.write_text(
            json.dumps(
                {
                    "kind": "allincms_resolved_source_input_gaps",
                    "siteKey": "mysite01",
                    "resolvedGaps": [
                        {
                            "fieldLabel": "products.specifications",
                            "proof": "/tmp/redacted-product-spec-final-audit.json",
                            "note": "Later browser verification proved product specs rendered without old placeholder terms.",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        ReqArgs = type("ReqArgs", (), {})
        ReqArgs.site_key = "mysite01"
        ReqArgs.content_types = "products"
        ReqArgs.source_types = "pdf_catalog,plain_brief"
        ReqArgs.manifest = []
        ReqArgs.save_capture_evidence = []
        ReqArgs.media_evidence = None
        ReqArgs.readiness_evidence = None
        ReqArgs.gap_ledger = [str(ledger_path)]
        ReqArgs.resolved_gap_evidence = [str(resolved_path)]

        report = build_source_input_requirements_report(ReqArgs())

    assert report["operationGaps"]["entryCount"] == 0
    assert report["operationGaps"]["resolvedEntryCount"] == 1
    assert report["operationGaps"]["resolvedFields"] == ["products.specifications"]
    assert "products.specifications" not in report["operationGaps"]["blockedFields"]
    assert not any("products.specifications: operation-time gap" in item for item in report["blockedUntil"])


def test_source_input_requirements_rejects_gap_ledger_wrong_site() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "source-input-gaps.json"

        GapArgs = type("GapArgs", (), {})
        GapArgs.action = "init"
        GapArgs.output = str(ledger_path)
        GapArgs.site_key = "otherkey"
        ledger = record_source_input_gap.apply_action(GapArgs())
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        ReqArgs = type("ReqArgs", (), {})
        ReqArgs.site_key = "mysite01"
        ReqArgs.content_types = "products"
        ReqArgs.source_types = "pdf_catalog"
        ReqArgs.manifest = []
        ReqArgs.save_capture_evidence = []
        ReqArgs.media_evidence = None
        ReqArgs.readiness_evidence = None
        ReqArgs.gap_ledger = [str(ledger_path)]

        try:
            build_source_input_requirements_report(ReqArgs())
        except SystemExit as exc:
            assert "does not match" in str(exc)
        else:
            raise AssertionError("expected wrong-site gap ledger to be rejected")


def test_existing_probe_save_handoff_builds_from_readonly_state() -> None:
    edit_url = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
    handoff = build_existing_probe_save_handoff(
        backend_state=existing_probe_backend_state(),
        backend_state_path="/tmp/backend-readonly.json",
        edit_url=edit_url,
        preflight_path="/tmp/preflight.json",
        authorization_output="/tmp/save-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )

    errors = validate_existing_probe_save_handoff(handoff)
    assert not errors, "\n".join(errors)
    assert handoff["kind"] == "allincms_existing_probe_save_handoff"
    assert handoff["preparedOnly"] is True
    assert handoff["isUserAuthorization"] is False
    assert handoff["remoteMutationsPerformed"] is False
    assert handoff["action"] == "save_probe"
    assert handoff["currentReadOnlyState"]["bodyEditorState"] == "placeholder_only"
    assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
    assert "--action save_probe" in handoff["preMutationGateCommand"]
    assert "creating another probe" in handoff["forbiddenActions"]
    assert "cleaning or deleting the probe" in handoff["forbiddenActions"]


def test_existing_probe_save_handoff_rejects_non_placeholder_body() -> None:
    state = existing_probe_backend_state()
    state["observations"]["bodyEditor"]["state"] = "non_empty"
    try:
        build_existing_probe_save_handoff(
            backend_state=state,
            backend_state_path="/tmp/backend-readonly.json",
            edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            preflight_path="/tmp/preflight.json",
            authorization_output="/tmp/save-auth.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
    except ValueError as exc:
        assert "placeholder_only" in str(exc)
    else:
        raise AssertionError("existing-probe save handoff accepted non-placeholder body state")


def test_probe_save_handoff_rejects_create_evidence_with_prior_save() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": True,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    try:
        build_probe_save_handoff(
            create_evidence=create_evidence,
            create_evidence_path="/tmp/create-evidence.json",
            preflight_path="/tmp/preflight.json",
            edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            authorization_output="/tmp/save-auth.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
    except ValueError as exc:
        assert "save was not clicked" in str(exc)
    else:
        raise AssertionError("save handoff accepted create evidence that already clicked save")


def test_probe_save_runbook_builds_browser_capture_steps() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    handoff = build_probe_save_handoff(
        create_evidence=create_evidence,
        create_evidence_path="/tmp/create-evidence.json",
        preflight_path="/tmp/preflight.json",
        edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        authorization_output="/tmp/save-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    runbook = build_probe_save_runbook(handoff, handoff_path="/tmp/save-handoff.json", generated_at=RECENT_PREFLIGHT_AT)

    errors = validate_probe_save_runbook(runbook)
    assert not errors, "\n".join(errors)
    assert runbook["kind"] == "allincms_probe_save_browser_runbook"
    assert runbook["authorizationRequired"] is True
    assert runbook["redactedEvidenceTemplate"]["savedOnce"] is False
    assert runbook["redactedEvidenceTemplate"]["published"] is False
    assert runbook["browserStepsExecutable"] is False
    assert "saving the probe" in runbook["automationPreferenceDoesNotAuthorize"]
    assert "publishing the probe" in runbook["forbiddenActions"]
    assert "saving the probe" not in runbook["forbiddenActions"]
    step_names = [step["step"] for step in runbook["browserStepsAfterGate"]]
    assert step_names == ["open_or_claim_target", "edit_probe_fields", "capture_save_request", "verify_persistence"]
    edit_step = runbook["browserStepsAfterGate"][1]
    assert any(field["value"] == "Codex Probe - Delete Me" for field in edit_step["fields"])


def test_probe_save_runbook_accepts_existing_probe_handoff() -> None:
    handoff = build_existing_probe_save_handoff(
        backend_state=existing_probe_backend_state(),
        backend_state_path="/tmp/backend-readonly.json",
        edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        preflight_path="/tmp/preflight.json",
        authorization_output="/tmp/save-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    runbook = build_probe_save_runbook(handoff, handoff_path="/tmp/existing-save-handoff.json", generated_at=RECENT_PREFLIGHT_AT)

    errors = validate_probe_save_runbook(runbook)
    assert not errors, "\n".join(errors)
    assert runbook["sourceHandoffKind"] == "allincms_existing_probe_save_handoff"
    assert runbook["existingProbeResume"] is True
    assert runbook["browserStepsExecutable"] is False
    edit_step = runbook["browserStepsAfterGate"][1]
    assert any(field["label"] == "正文编辑器" for field in edit_step["fields"])
    assert not any(field.get("label") == "名称" for field in edit_step["fields"])
    assert "publishing the probe" in runbook["forbiddenActions"]


def test_probe_save_runbook_rejects_authorizing_handoff() -> None:
    handoff = {
        "kind": "allincms_probe_save_handoff",
        "preparedOnly": True,
        "isUserAuthorization": True,
        "remoteMutationsPerformed": False,
        "target": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        "action": "save_probe",
        "suggestedAuthorizationText": "授权 Codex 保存一次并捕获保存请求",
        "authorizationRecordCommand": "python3 x --authorization-source '<paste current user authorization text here>'",
        "authorizationRecordCommandHasPlaceholder": True,
        "preMutationGateCommand": "python3 gate --action save_probe",
        "sourceFiles": {"createEvidence": "/tmp/create.json", "preflight": "/tmp/preflight.json"},
        "automationPreference": {"doesNotAuthorize": ["saving the probe"], "rule": "requires action-time authorization"},
        "warning": "This is not user authorization",
    }
    try:
        build_probe_save_runbook(handoff, handoff_path="/tmp/save-handoff.json", generated_at=RECENT_PREFLIGHT_AT)
    except ValueError as exc:
        assert "isUserAuthorization must be false" in str(exc)
    else:
        raise AssertionError("runbook accepted a handoff marked as user authorization")


def test_probe_save_runbook_validation_blocks_missing_authorization_safely() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        preflight_path = tmpdir / "preflight.json"
        authorization_path = tmpdir / "save-auth.json"
        handoff_path = tmpdir / "save-handoff.json"
        runbook_path = tmpdir / "save-runbook.json"
        preflight = existing_site_selected_evidence()
        preflight["generatedAt"] = RECENT_PREFLIGHT_AT
        preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
        handoff = build_probe_save_handoff(
            create_evidence=create_evidence,
            create_evidence_path=str(tmpdir / "create-evidence.json"),
            preflight_path=str(preflight_path),
            edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            authorization_output=str(authorization_path),
            generated_at=RECENT_PREFLIGHT_AT,
        )
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
        runbook = build_probe_save_runbook(handoff, handoff_path=str(handoff_path), generated_at=RECENT_PREFLIGHT_AT)
        runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

        report = build_probe_save_runbook_validation_report(
            str(runbook_path),
            expect_missing_authorization=True,
            now=GATE_NOW,
        )

    assert report["valid"] is True
    assert report["status"] == "blocked_missing_authorization"
    assert report["browserStepsExecutable"] is False
    assert report["checks"]["runbookValid"] is True
    assert report["checks"]["handoffValid"] is True
    assert report["checks"]["redactedEvidenceStartsUnsaved"] is True
    assert "authorization_record_missing" in report["blockers"]


def test_probe_save_runbook_validation_accepts_existing_probe_handoff_missing_authorization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        preflight_path = tmpdir / "preflight.json"
        authorization_path = tmpdir / "save-auth.json"
        handoff_path = tmpdir / "existing-save-handoff.json"
        runbook_path = tmpdir / "existing-save-runbook.json"
        preflight = existing_site_selected_evidence()
        preflight["generatedAt"] = RECENT_PREFLIGHT_AT
        preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
        handoff = build_existing_probe_save_handoff(
            backend_state=existing_probe_backend_state(),
            backend_state_path="/tmp/backend-readonly.json",
            edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            preflight_path=str(preflight_path),
            authorization_output=str(authorization_path),
            generated_at=RECENT_PREFLIGHT_AT,
        )
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
        runbook = build_probe_save_runbook(handoff, handoff_path=str(handoff_path), generated_at=RECENT_PREFLIGHT_AT)
        runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

        report = build_probe_save_runbook_validation_report(
            str(runbook_path),
            expect_missing_authorization=True,
            now=GATE_NOW,
        )

    assert report["valid"] is True
    assert report["status"] == "blocked_missing_authorization"
    assert report["browserStepsExecutable"] is False
    assert report["checks"]["runbookValid"] is True
    assert report["checks"]["handoffValid"] is True
    assert "authorization_record_missing" in report["blockers"]


def test_probe_save_runbook_validation_allows_execution_after_gate_passes() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        preflight_path = tmpdir / "preflight.json"
        authorization_path = tmpdir / "save-auth.json"
        handoff_path = tmpdir / "save-handoff.json"
        runbook_path = tmpdir / "save-runbook.json"
        preflight = existing_site_selected_evidence()
        preflight["generatedAt"] = RECENT_PREFLIGHT_AT
        preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
        target = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
        authorization_path.write_text(json.dumps(valid_save_probe_authorization_record_for_target(target)), encoding="utf-8")
        handoff = build_probe_save_handoff(
            create_evidence=create_evidence,
            create_evidence_path=str(tmpdir / "create-evidence.json"),
            preflight_path=str(preflight_path),
            edit_url=target,
            authorization_output=str(authorization_path),
            generated_at=RECENT_PREFLIGHT_AT,
        )
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
        runbook = build_probe_save_runbook(handoff, handoff_path=str(handoff_path), generated_at=RECENT_PREFLIGHT_AT)
        runbook_path.write_text(json.dumps(runbook), encoding="utf-8")

        report = build_probe_save_runbook_validation_report(str(runbook_path), now=GATE_NOW)

    assert report["valid"] is True
    assert report["status"] == "ready_after_gate"
    assert report["browserStepsExecutable"] is True
    assert report["checks"]["authorizationRecordValid"] is True
    assert report["checks"]["saveGatePassed"] is True


def test_probe_save_evidence_bundle_targets_filled_evidence_and_base_run_evidence() -> None:
    create_evidence = {
        "kind": "allincms_redacted_browser_stage_evidence",
        "action": "create_product_probe",
        "contentType": "products",
        "target": "https://workspace.laicms.com/{siteKey}/products",
        "browserAction": {
            "stopConditionMet": True,
            "saveClicked": False,
            "publishClicked": False,
        },
        "cleanupCandidate": {
            "exists": True,
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        preflight_path = tmpdir / "preflight.json"
        handoff_path = tmpdir / "save-handoff.json"
        output_dir = tmpdir / "save-evidence-bundle"
        preflight = existing_site_selected_evidence()
        preflight["generatedAt"] = RECENT_PREFLIGHT_AT
        preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
        target = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
        handoff = build_probe_save_handoff(
            create_evidence=create_evidence,
            create_evidence_path=str(tmpdir / "create-evidence.json"),
            preflight_path=str(preflight_path),
            edit_url=target,
            authorization_output=str(tmpdir / "save-auth.json"),
            generated_at=RECENT_PREFLIGHT_AT,
        )
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
        runbook = build_probe_save_runbook(handoff, handoff_path=str(handoff_path), generated_at=RECENT_PREFLIGHT_AT)

        bundle = build_probe_save_evidence_bundle(runbook, runbook_path=str(tmpdir / "save-runbook.json"), output_dir=output_dir)
        errors = validate_probe_save_evidence_bundle(bundle)
        command = (output_dir / "validation-command.txt").read_text(encoding="utf-8")
        template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
        filled_template = json.loads(Path(bundle["filledEvidencePath"]).read_text(encoding="utf-8"))

    assert errors == [], errors
    assert bundle["baseRunEvidence"] == str(preflight_path)
    assert bundle["validationCommandRequiresFilledEvidence"] is True
    assert filled_template == template
    assert "save-capture-evidence.filled.json" in command
    assert "save-capture-evidence.template.json" not in command
    assert str(preflight_path) in command
    assert str(handoff_path) not in command


def valid_probe_save_capture_evidence() -> dict:
    return {
        "kind": "allincms_probe_save_capture_evidence",
        "contentType": "products",
        "target": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        "authorizationRecord": "/tmp/save-auth.json",
        "preMutationGate": "passed",
        "savedOnce": True,
        "published": False,
        "requestCapture": {
            "method": "POST",
            "url": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            "headers": ["Accept", "Content-Type", "next-action", "next-router-state-tree"],
            "payloadShape": {
                "siteId": "<redacted>",
                "productId": "<redacted>",
                "title": "string",
                "slug": "string",
                "description": "string",
                "mode": "update",
            },
            "contentBlockShape": "redacted editor blocks array with paragraph nodes",
            "idFields": "siteId, productId values redacted",
            "mode": "update",
            "publishBehavior": "publish-separate",
            "responseStatus": 200,
            "responseMimeType": "text/x-component",
        },
        "fieldMapping": {
            "nameField": "title",
            "slugField": "slug",
            "descriptionField": "description",
            "bodyField": "content",
            "mediaField": "coverImage",
            "statusField": "status",
        },
        "payloadTemplate": {
            "siteId": "<redacted>",
            "productId": "<redacted>",
            "title": "{title}",
            "slug": "{slug}",
            "description": "{description}",
            "mode": "update",
        },
        "backendPersisted": True,
        "stopConditionMet": True,
    }


def test_probe_save_capture_evidence_validator_accepts_redacted_capture() -> None:
    errors = validate_probe_save_capture_evidence(valid_probe_save_capture_evidence())
    assert errors == [], errors


def test_probe_save_capture_evidence_validator_rejects_wrong_base_site() -> None:
    base = base_evidence()
    base["siteIdentity"]["siteKey"] = "mysite03"
    errors = validate_probe_save_capture_evidence(valid_probe_save_capture_evidence(), base)
    assert any("siteKey" in error for error in errors), errors


def test_probe_save_capture_evidence_validator_rejects_cookie_header() -> None:
    evidence = valid_probe_save_capture_evidence()
    evidence["requestCapture"]["headers"].append("Cookie")
    errors = validate_probe_save_capture_evidence(evidence)
    assert any("cookie" in error.lower() or "credential" in error.lower() for error in errors), errors


def test_probe_save_capture_evidence_validator_rejects_unfilled_template_placeholders() -> None:
    evidence = valid_probe_save_capture_evidence()
    evidence["requestCapture"]["contentBlockShape"] = "to_fill_after_capture"
    evidence["payloadTemplate"]["content"] = "{capturedContentBlocks}"
    errors = validate_probe_save_capture_evidence(evidence)
    assert any("placeholder" in error.lower() for error in errors), errors


def test_merge_probe_evidence_from_save_capture_json() -> None:
    base = base_evidence()
    base["generatedAt"] = RECENT_PREFLIGHT_AT
    merged = merge_from_save_capture_evidence(base, valid_probe_save_capture_evidence())
    assert merged["requestCapture"]["persistedVerified"] is True
    assert merged["requestCapture"]["method"] == "POST"
    assert merged["requestCapture"]["url"].endswith("/products/6a4357aa8081156046558032/update")
    assert merged["uploadInScope"] is True


def run_evidence_after_request_capture() -> dict:
    base = base_evidence()
    base["generatedAt"] = RECENT_PREFLIGHT_AT
    return merge_from_save_capture_evidence(base, valid_probe_save_capture_evidence())


def test_probe_publish_runbook_builds_browser_verification_steps() -> None:
    evidence = run_evidence_after_request_capture()
    runbook = build_probe_publish_runbook(
        run_evidence=evidence,
        run_evidence_path="/tmp/request-captured.json",
        authorization_output="/tmp/publish-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    errors = validate_probe_publish_runbook(runbook)
    assert not errors, "\n".join(errors)
    assert runbook["action"] == "publish_probe"
    assert runbook["authorizationRequired"] is True
    assert "<paste current user authorization text here>" in runbook["authorizationRecordCommand"]
    assert "--action publish_probe" in runbook["preMutationGateCommand"]
    assert runbook["browserStepsExecutable"] is False
    assert "deleting or cleaning the probe" in runbook["forbiddenActions"]
    assert "publishing the probe" not in runbook["forbiddenActions"]
    assert runbook["redactedEvidenceTemplate"]["publishedOnce"] is False


def valid_probe_publish_sample_evidence() -> dict:
    return {
        "kind": "allincms_probe_publish_sample_evidence",
        "contentType": "products",
        "target": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        "backendUrl": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
        "frontendUrl": "https://mysite01.web.allincms.com/products/codex-probe-delete-me-product",
        "authorizationRecord": "/tmp/publish-auth.json",
        "preMutationGate": "passed",
        "publishedOnce": True,
        "publishRequestCaptured": True,
        "backendVerified": True,
        "frontendVerified": True,
        "titleOrNameVerified": True,
        "coverOrMediaVerified": True,
        "bodyVerified": True,
        "status": "published",
        "renderAudit": "HTTP 200; heading/body/media checked; no raw markdown residue",
        "stopConditionMet": True,
    }


def test_probe_publish_sample_evidence_validator_accepts_redacted_sample() -> None:
    errors = validate_probe_publish_sample_evidence(
        valid_probe_publish_sample_evidence(),
        run_evidence_after_request_capture(),
    )
    assert errors == [], errors


def test_probe_publish_sample_evidence_validator_rejects_unrelated_frontend_host() -> None:
    evidence = valid_probe_publish_sample_evidence()
    evidence["frontendUrl"] = "https://other-site.web.allincms.com/products/codex-probe-delete-me-product"
    errors = validate_probe_publish_sample_evidence(evidence, run_evidence_after_request_capture())
    assert any("frontendUrl" in error for error in errors), errors


def test_merge_probe_evidence_from_publish_sample_json() -> None:
    merged = merge_from_publish_sample_evidence(
        run_evidence_after_request_capture(),
        valid_probe_publish_sample_evidence(),
    )
    assert merged["sampleVerification"]["frontendVerified"] is True
    assert merged["sampleVerification"]["backendVerified"] is True
    assert merged["sampleVerification"]["frontendUrl"].endswith("/products/codex-probe-delete-me-product")


def run_evidence_after_publish_sample() -> dict:
    return merge_from_publish_sample_evidence(
        run_evidence_after_request_capture(),
        valid_probe_publish_sample_evidence(),
    )


def test_probe_cleanup_runbook_builds_cleanup_steps() -> None:
    runbook = build_probe_cleanup_runbook(
        run_evidence=run_evidence_after_publish_sample(),
        run_evidence_path="/tmp/published-sample.json",
        authorization_output="/tmp/cleanup-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    errors = validate_probe_cleanup_runbook(runbook)
    assert not errors, "\n".join(errors)
    assert runbook["action"] == "cleanup_probe"
    assert "<paste current user authorization text here>" in runbook["authorizationRecordCommand"]
    assert "--action cleanup_probe" in runbook["preMutationGateCommand"]
    assert runbook["browserStepsExecutable"] is False
    assert "cleaning any non-probe business content" in runbook["forbiddenActions"]
    assert runbook["redactedEvidenceTemplate"]["cleanedCount"] == 0


def existing_probe_backend_state() -> dict:
    return {
        "kind": "allincms_product_edit_readonly_state",
        "generatedAt": RECENT_PREFLIGHT_AT,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": "mysite01",
        "contentType": "products",
        "backendUrl": "https://workspace.laicms.com/mysite01/products/{contentId}/update",
        "observations": {
            "pageHeading": "更新产品",
            "statusText": "published_visible",
            "updateDisabled": True,
            "unpublishVisible": True,
            "bodyEditor": {"count": 1, "text": "placeholder", "state": "placeholder_only"},
            "media": {"chooseMediaButtonVisible": True, "imageCount": 1, "srcPresent": False, "altLen": 0},
            "fieldsVisible": ["产品名称", "Slug", "产品描述"],
        },
        "blocked": ["cleanup_or_unpublish_probe_not_completed"],
    }


def existing_probe_frontend_audit() -> list[dict]:
    return [
        {
            "url": "/products/{slug}",
            "status": 200,
            "expectedStatus": 200,
            "contentType": "text/html; charset=utf-8",
            "imageCount": 0,
            "issues": [],
        }
    ]


def test_existing_probe_cleanup_handoff_builds_from_readonly_state() -> None:
    edit_url = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
    handoff = build_existing_probe_cleanup_handoff(
        backend_state=existing_probe_backend_state(),
        backend_state_path="/tmp/backend-readonly.json",
        frontend_audit=existing_probe_frontend_audit(),
        frontend_audit_path="/tmp/frontend-audit.json",
        edit_url=edit_url,
        frontend_url="https://mysite01.web.allincms.com/products/codex-probe-delete-me",
        preflight_path="/tmp/preflight.json",
        authorization_output="/tmp/cleanup-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )

    errors = validate_existing_probe_cleanup_handoff(handoff)
    assert not errors, "\n".join(errors)
    assert handoff["kind"] == "allincms_existing_probe_cleanup_handoff"
    assert handoff["preparedOnly"] is True
    assert handoff["isUserAuthorization"] is False
    assert handoff["remoteMutationsPerformed"] is False
    assert handoff["currentReadOnlyState"]["frontendStatus"] == 200
    assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
    assert "--action cleanup_probe" in handoff["preMutationGateCommand"]
    assert "creating another probe" in handoff["forbiddenActions"]


def test_existing_probe_cleanup_handoff_rejects_non_public_frontend() -> None:
    audit = existing_probe_frontend_audit()
    audit[0]["status"] = 404
    try:
        build_existing_probe_cleanup_handoff(
            backend_state=existing_probe_backend_state(),
            backend_state_path="/tmp/backend-readonly.json",
            frontend_audit=audit,
            frontend_audit_path="/tmp/frontend-audit.json",
            edit_url="https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update",
            frontend_url="https://mysite01.web.allincms.com/products/codex-probe-delete-me",
            preflight_path="/tmp/preflight.json",
            authorization_output="/tmp/cleanup-auth.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
    except ValueError as exc:
        assert "returns 200" in str(exc)
    else:
        raise AssertionError("existing-probe cleanup handoff accepted non-public frontend evidence")


def test_existing_probe_cleanup_runbook_builds_from_handoff_without_authorizing() -> None:
    edit_url = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
    handoff = build_existing_probe_cleanup_handoff(
        backend_state=existing_probe_backend_state(),
        backend_state_path="/tmp/backend-readonly.json",
        frontend_audit=existing_probe_frontend_audit(),
        frontend_audit_path="/tmp/frontend-audit.json",
        edit_url=edit_url,
        frontend_url="https://mysite01.web.allincms.com/products/codex-probe-delete-me",
        preflight_path="/tmp/preflight.json",
        authorization_output="/tmp/cleanup-auth.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )
    runbook = build_existing_probe_cleanup_runbook(
        handoff=handoff,
        handoff_path="/tmp/existing-probe-cleanup-handoff.json",
        generated_at=RECENT_PREFLIGHT_AT,
    )

    errors = validate_existing_probe_cleanup_runbook(runbook)
    assert not errors, "\n".join(errors)
    assert runbook["kind"] == "allincms_existing_probe_cleanup_browser_runbook"
    assert runbook["browserStepsExecutable"] is False
    assert runbook["authorizationRequired"] is True
    assert runbook["remoteMutationsPerformed"] is False
    assert "<paste current user authorization text here>" in runbook["authorizationRecordCommand"]
    assert runbook["redactedEvidenceTemplate"]["preMutationGate"] == "passed|required_before_cleanup"
    assert "saving product fields or body" in runbook["forbiddenActions"]


def test_existing_probe_cleanup_runbook_rejects_invalid_handoff() -> None:
    handoff = {"kind": "allincms_existing_probe_cleanup_handoff", "target": "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"}
    try:
        build_existing_probe_cleanup_runbook(
            handoff=handoff,
            handoff_path="/tmp/bad-existing-probe-cleanup-handoff.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
    except ValueError as exc:
        assert "existing cleanup handoff is not valid" in str(exc)
    else:
        raise AssertionError("existing-probe cleanup runbook accepted invalid handoff")


def valid_probe_cleanup_evidence() -> dict:
    target = "https://workspace.laicms.com/mysite01/products/6a4357aa8081156046558032/update"
    return {
        "kind": "allincms_probe_cleanup_evidence",
        "contentType": "products",
        "target": target,
        "authorizationRecord": "/tmp/cleanup-auth.json",
        "preMutationGate": "passed",
        "cleanupAction": "delete",
        "cleanedCandidates": [
            {
                "contentType": "products",
                "titlePattern": "Codex Probe - Delete Me product draft",
                "backendUrl": target,
                "reason": "probe cleanup after sample verification",
            }
        ],
        "cleanedCount": 1,
        "backendVerified": True,
        "frontendVerified": True,
        "backendEvidence": "backend product list/search no longer shows Codex Probe item",
        "frontendEvidence": "frontend detail route returns 404 or no longer renders probe content",
        "stopConditionMet": True,
    }


def test_probe_cleanup_evidence_validator_accepts_redacted_cleanup() -> None:
    errors = validate_probe_cleanup_evidence(valid_probe_cleanup_evidence(), run_evidence_after_publish_sample())
    assert errors == [], errors


def test_probe_cleanup_evidence_validator_rejects_non_probe_candidate() -> None:
    evidence = valid_probe_cleanup_evidence()
    evidence["cleanedCandidates"][0]["titlePattern"] = "Business Product"
    errors = validate_probe_cleanup_evidence(evidence, run_evidence_after_publish_sample())
    assert any("Codex Probe" in error for error in errors), errors


def test_merge_probe_evidence_from_cleanup_json() -> None:
    merged = merge_from_cleanup_evidence(run_evidence_after_publish_sample(), valid_probe_cleanup_evidence())
    assert merged["cleanup"]["status"] == "completed"
    assert merged["cleanup"]["cleanedCount"] == 1
    assert merged["cleanup"]["backendVerified"] is True


def test_merge_probe_evidence_from_cleanup_json_accepts_comma_reason() -> None:
    evidence = valid_probe_cleanup_evidence()
    evidence["cleanedCandidates"][0]["reason"] = (
        "probe cleanup after request capture, sample verification, and frontend 404 proof"
    )
    merged = merge_from_cleanup_evidence(run_evidence_after_publish_sample(), evidence)
    assert merged["cleanup"]["cleanedCandidates"][0]["reason"] == evidence["cleanedCandidates"][0]["reason"]


def test_browser_stage_authorization_package_for_module_capture_requires_plan() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "module_interface_capture",
        "recovery": False,
        "phase": "interface capture",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{module}",
        "authorizationRequired": True,
        "remoteMutationExpectation": "may",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{module} 执行 stage=module_interface_capture",
        "allowedActions": ["run exactly one capture-plan stage"],
        "requiredProof": ["fresh authorization"],
        "forbiddenActions": ["batch replay"],
        "stopAfter": "stop after one module/action capture",
        "evidenceCaptureTemplate": {
            "stageId": "module_interface_capture",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["module_interface_capture"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    try:
        build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    except ValueError as exc:
        assert "--capture-plan" in str(exc)
    else:
        raise AssertionError("module capture authorization package accepted missing capture plan")


def theme_launch_packet() -> dict:
    return {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "theme_page_route_launch",
        "recovery": False,
        "phase": "theme/page/route launch",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/themes and https://workspace.laicms.com/{realSiteKey}/routes",
        "authorizationRequired": True,
        "remoteMutationExpectation": "must",
        "suggestedAuthorizationText": (
            "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/themes and "
            "https://workspace.laicms.com/{realSiteKey}/routes 执行 stage=theme_page_route_launch"
        ),
        "allowedActions": ["save design", "publish page", "enable page", "set homepage", "bind route"],
        "requiredProof": ["active theme", "published pages", "enabled pages", "routes bound", "frontend DOM verified"],
        "forbiddenActions": ["batch content upload", "delete pages"],
        "stopAfter": "stop after backend launch readiness and frontend DOM proof are both recorded",
        "evidenceCaptureTemplate": {
            "stageId": "theme_page_route_launch",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": True,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["theme_page_route_launch"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }


def browser_stage_packet(stage_id: str, target_template: str, remote_mutation_expectation: str = "must") -> dict:
    return {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": stage_id,
        "recovery": False,
        "phase": stage_id.replace("_", " "),
        "mode": "requires_authorization",
        "targetTemplate": target_template,
        "authorizationRequired": True,
        "remoteMutationExpectation": remote_mutation_expectation,
        "suggestedAuthorizationText": f"授权 Codex 仅在 {target_template} 执行 stage={stage_id}",
        "allowedActions": ["run exactly this stage"],
        "requiredProof": ["fresh authorization", "stage proof"],
        "forbiddenActions": ["next stage", "batch upload"],
        "stopAfter": "stop after this stage proof is recorded",
        "evidenceCaptureTemplate": {
            "stageId": stage_id,
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": True,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": [stage_id],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }


def test_browser_stage_authorization_package_for_theme_launch_requires_granular_action() -> None:
    try:
        build_browser_stage_authorization_package(
            theme_launch_packet(),
            "/tmp/allincms-created-site-evidence.json",
            "/tmp/allincms-authorization-launch.json",
        )
    except ValueError as exc:
        assert "--launch-action" in str(exc)
        assert "aggregate stage" in str(exc)
    else:
        raise AssertionError("theme launch authorization package accepted aggregate stage without action")


def test_browser_stage_authorization_package_for_theme_launch_suppresses_templated_target_commands() -> None:
    package = build_browser_stage_authorization_package(
        theme_launch_packet(),
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-launch.json",
        launch_action="save_design",
    )
    assert package["stageId"] == "theme_page_route_launch"
    assert package["launchAction"]["action"] == "save_design"
    assert package["launchAction"]["targetType"] == "theme-design"
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert package["preMutationGateCommand"] is None
    assert "{realSiteKey}" in package["suggestedAuthorizationText"]
    assert "simsite01" not in package["suggestedAuthorizationText"]


def test_browser_stage_authorization_package_for_theme_launch_real_target_emits_site_action_gate() -> None:
    package = build_browser_stage_authorization_package(
        theme_launch_packet(),
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-launch.json",
        launch_action="save_design",
        launch_target="https://workspace.laicms.com/mysite01/themes/theme-id/page-id/design",
        launch_target_identifier="theme-id/page-id design",
    )
    assert package["gateSupported"] is True
    assert package["commandsSuppressed"] is False
    assert package["launchAction"]["fieldsOrFiles"] == ["requestCapture", "pageDocument", "persistedVerified"]
    assert "make_authorization_record.py --action save_design" in package["authorizationRecordCommand"]
    assert "--site-key mysite01" in package["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert "授权 Codex" not in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action save_design" in package["preMutationGateCommand"]
    assert "--preflight /tmp/allincms-created-site-evidence.json" in package["preMutationGateCommand"]


def test_browser_stage_authorization_package_for_create_theme_page_real_target() -> None:
    package = build_browser_stage_authorization_package(
        theme_launch_packet(),
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-create-theme-page.json",
        launch_action="create_theme_page",
        launch_target="https://workspace.laicms.com/mysite01/themes/theme-id",
        launch_target_identifier="theme-id /products/{product} page",
    )
    assert package["gateSupported"] is True
    assert package["commandsSuppressed"] is False
    assert package["launchAction"]["action"] == "create_theme_page"
    assert package["launchAction"]["targetType"] == "theme-page"
    assert package["launchAction"]["fieldsOrFiles"] == ["requestCapture", "pageId", "routePath", "backendVerified"]
    assert "make_authorization_record.py --action create_theme_page" in package["authorizationRecordCommand"]
    assert "--target https://workspace.laicms.com/mysite01/themes/theme-id" in package["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_theme_page" in package["preMutationGateCommand"]


def valid_create_theme_page_package() -> dict:
    return build_browser_stage_authorization_package(
        theme_launch_packet(),
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-create-theme-page.json",
        launch_action="create_theme_page",
        launch_target="https://workspace.laicms.com/mysite01/themes/theme-id",
        launch_target_identifier="theme-id /products/{product} theme page",
    )


def test_theme_page_create_runbook_stays_preparation_only() -> None:
    preflight = base_evidence()
    preflight["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    runbook = build_theme_page_create_runbook(
        valid_create_theme_page_package(),
        package_path="/tmp/create-theme-page-package.json",
        packet=theme_launch_packet(),
        packet_path="/tmp/theme-launch-packet.json",
        preflight=preflight,
        preflight_path="/tmp/preflight.json",
        page_name="Product Detail",
        route_path="/products/{product}",
        description="Dynamic product detail page for product routes.",
        generated_at=RECENT_AUTHORIZATION_AT,
    )
    errors = validate_theme_page_create_runbook(runbook)
    assert errors == [], errors
    assert runbook["action"] == "create_theme_page"
    assert runbook["browserStepsExecutable"] is False
    assert "<paste current user authorization text here>" in runbook["authorizationRecordCommand"]
    assert "--action create_theme_page" in runbook["preMutationGateCommand"]
    assert "publishing page design" in runbook["forbiddenActions"]
    assert runbook["redactedEvidenceTemplate"]["createdOnce"] is False


def valid_theme_page_create_evidence() -> dict:
    return {
        "kind": "allincms_theme_page_create_evidence",
        "action": "create_theme_page",
        "target": "https://workspace.laicms.com/mysite01/themes/theme-id",
        "targetIdentifier": "theme-id /products/{product} theme page",
        "pageName": "Product Detail",
        "routePath": "/products/{product}",
        "preMutationGate": "passed",
        "createdOnce": True,
        "requestCapture": {
            "method": "POST",
            "url": "https://workspace.laicms.com/mysite01/themes/theme-id",
            "headers": ["Accept", "Content-Type", "next-action"],
            "payloadShape": {
                "siteId": "redacted",
                "themeId": "redacted",
                "name": "string",
                "path": "string",
                "description": "string",
                "_status": "string",
            },
            "responseStatus": 200,
            "responseMimeType": "text/x-component",
        },
        "pageId": "redacted-page-id",
        "backendVerified": True,
        "backendEvidence": "theme page list shows Product Detail with /products/{product}",
        "stopConditionMet": True,
    }


def test_theme_page_create_evidence_validator_accepts_redacted_dynamic_page() -> None:
    errors = validate_theme_page_create_evidence(valid_theme_page_create_evidence(), base_evidence())
    assert errors == [], errors


def test_theme_page_create_evidence_validator_rejects_missing_page_id() -> None:
    evidence = valid_theme_page_create_evidence()
    evidence["pageId"] = "to_verify"
    errors = validate_theme_page_create_evidence(evidence, base_evidence())
    assert any("pageId" in error for error in errors), errors


def test_theme_page_create_evidence_validator_rejects_static_route() -> None:
    evidence = valid_theme_page_create_evidence()
    evidence["routePath"] = "/products"
    errors = validate_theme_page_create_evidence(evidence, base_evidence())
    assert any("routePath" in error for error in errors), errors


def test_browser_stage_authorization_package_for_content_probe_requires_content_type() -> None:
    packet = browser_stage_packet("content_probe_create", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    try:
        build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    except ValueError as exc:
        assert "--content-type" in str(exc)
        assert "do not infer" in str(exc)
    else:
        raise AssertionError("content probe authorization package accepted missing content type")


def test_browser_stage_authorization_package_for_content_probe_suppresses_templated_target_commands() -> None:
    packet = browser_stage_packet("content_probe_create", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/preflight.json",
        "/tmp/auth.json",
        content_type="products",
    )
    assert package["stageId"] == "content_probe_create"
    assert package["contentStage"]["authorizationAction"] == "create_product_probe"
    assert package["contentStage"]["fieldsOrFiles"] == ["name", "slug", "description", "content", "coverImage", "status"]
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert "{realSiteKey}" in package["suggestedAuthorizationText"]
    assert "产品测试草稿" in package["suggestedAuthorizationText"]
    assert "products 测试草稿" not in package["suggestedAuthorizationText"]


def test_content_probe_authorization_text_uses_chinese_content_type_labels() -> None:
    packet = browser_stage_packet("content_probe_create", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    cases = [
        ("posts", "文章测试草稿", "posts 测试草稿"),
        ("products", "产品测试草稿", "products 测试草稿"),
        ("forms", "表单测试草稿", "forms 测试草稿"),
    ]
    for content_type, expected_text, rejected_text in cases:
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/preflight.json",
            "/tmp/auth.json",
            content_type=content_type,
        )
        assert expected_text in package["suggestedAuthorizationText"]
        assert rejected_text not in package["suggestedAuthorizationText"]


def test_browser_stage_authorization_package_for_content_probe_real_target_emits_create_probe_gate() -> None:
    packet = browser_stage_packet("content_probe_create", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-product-probe.json",
        content_type="products",
        content_target="https://workspace.laicms.com/mysite01/products",
        content_target_identifier="Codex Probe - Delete Me product draft",
    )
    assert package["gateSupported"] is True
    assert package["commandsSuppressed"] is False
    assert "make_authorization_record.py --action create_product_probe" in package["authorizationRecordCommand"]
    assert "--site-key mysite01" in package["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert "授权 Codex" not in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action create_product_probe" in package["preMutationGateCommand"]


def test_browser_stage_authorization_package_for_save_publish_cleanup_probe_real_targets() -> None:
    cases = [
        ("save_request_capture", "save_probe", "requestCapture,payloadShape,persistedVerified"),
        ("publish_sample_verify", "publish_probe", "publishStatus,frontendVerified"),
        ("cleanup_probes", "cleanup_probe", "cleanedCandidates,backendVerified,frontendVerified"),
    ]
    for stage_id, action, fields in cases:
        packet = browser_stage_packet(
            stage_id,
            "https://workspace.laicms.com/{realSiteKey}/{contentType}/{contentId}/edit",
            "may" if stage_id == "publish_sample_verify" else "must",
        )
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/allincms-created-site-evidence.json",
            f"/tmp/allincms-authorization-{action}.json",
            content_type="products",
            content_target="https://workspace.laicms.com/mysite01/products/product-id/update",
            content_target_identifier="Codex Probe - Delete Me product draft",
        )
        assert package["gateSupported"] is True
        assert package["commandsSuppressed"] is False
        assert package["contentStage"]["authorizationAction"] == action
        assert f"make_authorization_record.py --action {action}" in package["authorizationRecordCommand"]
        assert f"--fields-or-files {fields}" in package["authorizationRecordCommand"]
        assert f"check_pre_mutation_gate.py --action {action}" in package["preMutationGateCommand"]


def test_browser_stage_authorization_package_for_batch_requires_content_type() -> None:
    packet = browser_stage_packet("batch_upload_publish", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    try:
        build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    except ValueError as exc:
        assert "--content-type" in str(exc)
        assert "do not infer" in str(exc)
    else:
        raise AssertionError("batch authorization package accepted missing content type")


def test_browser_stage_authorization_package_for_batch_suppresses_templated_target_commands() -> None:
    packet = browser_stage_packet("batch_upload_publish", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/preflight.json",
        "/tmp/auth.json",
        content_type="products",
    )
    assert package["stageId"] == "batch_upload_publish"
    assert package["batchStage"]["authorizationAction"] == "batch_upload"
    assert package["batchStage"]["fieldsOrFiles"] == [
        "schemaGatePass",
        "sampleVerification",
        "progressLog",
        "frontendDetailAudit",
    ]
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None


def test_browser_stage_authorization_package_for_batch_real_target_emits_batch_gate() -> None:
    packet = browser_stage_packet("batch_upload_publish", "https://workspace.laicms.com/{realSiteKey}/{contentType}")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-batch-upload.json",
        content_type="products",
        content_target="https://workspace.laicms.com/mysite01/products",
        content_target_identifier="products manifest batch",
    )
    assert package["gateSupported"] is True
    assert package["commandsSuppressed"] is False
    assert "make_authorization_record.py --action batch_upload" in package["authorizationRecordCommand"]
    assert "--fields-or-files schemaGatePass,sampleVerification,progressLog,frontendDetailAudit" in package["authorizationRecordCommand"]
    assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
    assert "授权 Codex" not in package["authorizationRecordCommand"]
    assert "check_pre_mutation_gate.py --action batch_upload" in package["preMutationGateCommand"]


def test_browser_stage_authorization_package_for_forms_media_settings_requires_granular_action() -> None:
    packet = browser_stage_packet("forms_media_settings", "https://workspace.laicms.com/{realSiteKey}/{module}")
    try:
        build_browser_stage_authorization_package(packet, "/tmp/preflight.json", "/tmp/auth.json")
    except ValueError as exc:
        assert "--settings-action" in str(exc)
        assert "aggregate stage" in str(exc)
    else:
        raise AssertionError("forms/media/settings authorization package accepted aggregate stage without action")


def test_browser_stage_authorization_package_for_forms_media_settings_suppresses_templated_target_commands() -> None:
    packet = browser_stage_packet("forms_media_settings", "https://workspace.laicms.com/{realSiteKey}/{module}")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/preflight.json",
        "/tmp/auth.json",
        settings_action="save_site_settings",
    )
    assert package["stageId"] == "forms_media_settings"
    assert package["settingsAction"]["action"] == "save_site_settings"
    assert package["settingsAction"]["targetType"] == "site-info"
    assert package["settingsAction"]["fieldsOrFiles"] == ["fieldMapping", "persistedVerified"]
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert package["preMutationGateCommand"] is None
    assert "{realSiteKey}" in package["suggestedAuthorizationText"]


def test_browser_stage_authorization_package_for_forms_media_settings_real_targets_emit_site_action_gates() -> None:
    packet = browser_stage_packet("forms_media_settings", "https://workspace.laicms.com/{realSiteKey}/{module}")
    cases = [
        (
            "save_site_settings",
            "https://workspace.laicms.com/mysite01/site-info",
            "site-info settings",
            "site-info",
            "fieldMapping,persistedVerified",
        ),
        (
            "create_form",
            "https://workspace.laicms.com/mysite01/forms",
            "contact form",
            "forms",
            "requestCapture,formId,backendVerified",
        ),
        (
            "add_domain",
            "https://workspace.laicms.com/mysite01/domains",
            "example.com domain",
            "domains",
            "domain,backendVerified,dnsFollowup",
        ),
        (
            "add_tracking_tag",
            "https://workspace.laicms.com/mysite01/tracking",
            "google tag",
            "tracking",
            "googleTagId,backendVerified",
        ),
    ]
    for action, target, identifier, target_type, fields in cases:
        package = build_browser_stage_authorization_package(
            packet,
            "/tmp/allincms-created-site-evidence.json",
            f"/tmp/allincms-authorization-{action}.json",
            settings_action=action,
            settings_target=target,
            settings_target_identifier=identifier,
        )
        assert package["gateSupported"] is True
        assert package["commandsSuppressed"] is False
        assert package["settingsAction"]["targetType"] == target_type
        assert f"make_authorization_record.py --action {action}" in package["authorizationRecordCommand"]
        assert "--site-key mysite01" in package["authorizationRecordCommand"]
        assert f"--fields-or-files {fields}" in package["authorizationRecordCommand"]
        assert "<paste current user authorization text here>" in package["authorizationRecordCommand"]
        assert "授权 Codex" not in package["authorizationRecordCommand"]
        assert f"check_pre_mutation_gate.py --action {action}" in package["preMutationGateCommand"]


def test_browser_stage_authorization_package_for_upload_media_stays_ungated_ui_first() -> None:
    packet = browser_stage_packet("forms_media_settings", "https://workspace.laicms.com/{realSiteKey}/media")
    package = build_browser_stage_authorization_package(
        packet,
        "/tmp/allincms-created-site-evidence.json",
        "/tmp/allincms-authorization-upload-media.json",
        settings_action="upload_media",
        settings_target="https://workspace.laicms.com/mysite01/media",
        settings_target_identifier="test media upload",
    )
    assert package["stageId"] == "forms_media_settings"
    assert package["settingsAction"]["action"] == "upload_media"
    assert package["gateSupported"] is False
    assert package["commandsSuppressed"] is True
    assert package["authorizationRecordCommand"] is None
    assert package["preMutationGateCommand"] is None
    assert "UI-first" in package["suppressionReason"]
    assert package["uiFirstCaptureRequired"] is True
    assert package["mustCaptureBeforeReplay"] == ["file", "uploadRequest", "publicUrl", "metadata"]
    assert "不得 JSON replay" in package["suggestedAuthorizationText"]
    assert "不得批量上传" in package["suggestedAuthorizationText"]
    assert "multipart/storage request shape is captured" in package["mustNotReplayUntil"]
    assert "public URL loads successfully" in package["mustNotReplayUntil"]


def test_browser_stage_authorization_package_for_forms_media_settings_rejects_invalid_action() -> None:
    packet = browser_stage_packet("forms_media_settings", "https://workspace.laicms.com/{realSiteKey}/{module}")
    try:
        build_browser_stage_authorization_package(
            packet,
            "/tmp/preflight.json",
            "/tmp/auth.json",
            settings_action="save_everything",
        )
    except ValueError as exc:
        assert "--settings-action" in str(exc)
    else:
        raise AssertionError("forms/media/settings authorization package accepted an invalid action")


def test_browser_stage_packet_rejects_pending_stage_selection() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        try:
            build_browser_stage_packet(ledger, "create_site_submit")
        except ValueError as exc:
            assert "not ready" in str(exc)
        else:
            raise AssertionError("pending stage was accepted as a browser stage packet")


def test_browser_stage_result_apply_advances_ledger() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        packet = build_browser_stage_packet(ledger)
        result = build_stage_result(
            packet["stageId"],
            "completed",
            ["local://redacted-readonly-scan.json"],
            packet["requiredProof"],
            [],
        )
        assert validate_browser_stage_result(result, packet)["ok"] is True
        updated = apply_stage_result(ledger, packet, result)
        assert updated["entries"][0]["stageId"] == packet["stageId"]
        assert updated["entries"][0]["status"] == "completed"
        assert updated["stageCounts"]["completed"] == 1
        assert updated["nextStageId"] == "create_site_submit"
        next_packet = build_browser_stage_packet(updated)
        assert next_packet["stageId"] == "create_site_submit"
        assert next_packet["authorizationRequired"] is True
        assert next_packet["allowedActions"] == ["submit create-site form with authorized name and description only"]
        assert "https://workspace.laicms.com/sites" in next_packet["suggestedAuthorizationText"]
        create_result = build_stage_result(
            next_packet["stageId"],
            "completed",
            ["local://create-site-preflight.json", "local://created-site-evidence.json"],
            next_packet["requiredProof"],
            [],
            True,
        )
        after_create = apply_stage_result(updated, next_packet, create_result)
        assert after_create["nextStageId"] == "setup_pages_inspection"
        setup_packet = build_browser_stage_packet(after_create)
        assert setup_packet["stageId"] == "setup_pages_inspection"
        assert setup_packet["authorizationRequired"] is False
        assert "inspect site-info" in setup_packet["allowedActions"]
        setup_result = build_stage_result(
            setup_packet["stageId"],
            "completed",
            [
                "local://site-info-fields.json",
                "local://domains-controls.json",
                "local://themes-controls.json",
                "local://routes-columns.json",
                "local://forms-columns.json",
            ],
            setup_packet["requiredProof"],
            [],
        )
        after_setup = apply_stage_result(after_create, setup_packet, setup_result)
        assert after_setup["nextStageId"] == "module_interface_capture"


def test_existing_site_ledger_branch_skips_create_site_submit() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        refresh_packet = build_browser_stage_packet(ledger)
        refresh_result = build_stage_result(
            refresh_packet["stageId"],
            "completed",
            ["local://redacted-readonly-scan.json"],
            refresh_packet["requiredProof"],
            [],
        )
        after_refresh = apply_stage_result(ledger, refresh_packet, refresh_result)
        assert after_refresh["nextStageId"] == "create_site_submit"

        branched = branch_existing_site_ledger(
            after_refresh,
            existing_site_selected_evidence(),
            "/tmp/allincms-existing-site-readonly-evidence.json",
        )
        assert branched["nextStageId"] == "setup_pages_inspection"
        assert branched["existingSiteContinuation"]["enabled"] is True
        assert branched["existingSiteContinuation"]["siteKey"] == "mysite01"
        create_entry = next(entry for entry in branched["entries"] if entry["stageId"] == "create_site_submit")
        assert create_entry["status"] == "skipped"
        assert create_entry["proofRecorded"] == ["existing site selected; create-site submit skipped"]
        setup_packet = build_browser_stage_packet(branched)
        assert setup_packet["stageId"] == "setup_pages_inspection"
        assert setup_packet["authorizationRequired"] is False
        assert "inspect site-info" in setup_packet["allowedActions"]


def test_existing_site_ledger_branch_rejects_create_preflight_evidence() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        simulate_full_e2e_chain.run_simulation(Args())
        handoff = build_capture_handoff(Path(tmp), "", "", Path(tmp) / "handoff")
        launch_plan = build_launch_plan(Path(tmp), handoff)
        plan = build_browser_execution_plan(Path(tmp), handoff, launch_plan)
        ledger = build_browser_execution_ledger(plan)
        refresh_packet = build_browser_stage_packet(ledger)
        refresh_result = build_stage_result(
            refresh_packet["stageId"],
            "completed",
            ["local://redacted-readonly-scan.json"],
            refresh_packet["requiredProof"],
            [],
        )
        after_refresh = apply_stage_result(ledger, refresh_packet, refresh_result)
        preflight = build_create_preflight_from_existing(existing_site_selected_evidence())
        try:
            branch_existing_site_ledger(after_refresh, preflight, "/tmp/allincms-create-preflight.json")
        except ValueError as exc:
            assert "existing_site_selected" in str(exc)
        else:
            raise AssertionError("existing-site branch accepted create-preflight evidence")


def test_browser_stage_packet_requires_explicit_partial_recovery_selection() -> None:
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePlanKind": "allincms_browser_execution_plan",
        "siteKeyTemplate": "{realSiteKey}",
        "stageCounts": {
            "total": 14,
            "ready": 0,
            "pending": 0,
            "completed": 13,
            "blocked": 1,
            "requiresAuthorization": 1,
        },
        "nextStageId": "cleanup_probes",
        "entries": [
            {
                "stageId": stage_id,
                "phase": "completed phase",
                "mode": "read_only",
                "status": "completed",
                "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/dashboard",
                "authorizationRequired": False,
                "remoteMutationExpectation": "must_not",
                "dependsOn": [],
                "requiredProof": ["proof"],
                "stopAfter": "stop",
                "plannedActions": ["inspect"],
                "nextAllowedActions": [],
                "blockedUntil": [],
                "evidencePointers": ["local://proof.json"],
                "proofRecorded": ["proof"],
                "notes": "",
            }
            for stage_id in (
                "refresh_readonly_site_evidence",
                "create_site_submit",
                "setup_pages_inspection",
                "module_interface_capture",
                "theme_page_route_launch",
                "static_frontend_audit",
                "content_probe_create",
                "save_request_capture",
                "publish_sample_verify",
                "manifest_schema_gate",
                "batch_upload_publish",
                "forms_media_settings",
                "final_frontend_audit",
            )
        ]
        + [
            {
                "stageId": "cleanup_probes",
                "phase": "cleanup",
                "mode": "requires_authorization",
                "status": "partial",
                "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}",
                "authorizationRequired": True,
                "remoteMutationExpectation": "may",
                "dependsOn": ["final_frontend_audit"],
                "requiredProof": ["cleanup authorization", "candidate list", "backend cleanup proof", "frontend non-public proof"],
                "stopAfter": "stop after cleanup proof",
                "plannedActions": ["cleanup probes"],
                "nextAllowedActions": [],
                "blockedUntil": ["backend cleanup proof missing"],
                "evidencePointers": ["local://cleanup-candidates.json"],
                "proofRecorded": ["cleanup authorization", "candidate list"],
                "notes": "",
            }
        ],
    }
    validation = validate_browser_execution_ledger(ledger)
    assert validation["ok"] is False
    assert any("nextStageId must be empty" in issue for issue in validation["issues"])
    ledger["nextStageId"] = ""
    assert validate_browser_execution_ledger(ledger)["ok"] is True
    try:
        build_browser_stage_packet(ledger)
    except ValueError as exc:
        assert "no stage is ready" in str(exc)
    else:
        raise AssertionError("partial stage was selected without explicit recovery stage id")
    packet = build_browser_stage_packet(ledger, "cleanup_probes")
    assert packet["recovery"] is True
    assert packet["authorizationRequired"] is True
    assert packet["evidenceCaptureTemplate"]["status"] == "completed|blocked|partial"


def test_browser_stage_packet_rejects_stale_capture_template_status() -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": "cmd --completed-stage-ids refresh_readonly_site_evidence",
        },
        "warnings": ["local only"],
    })
    validation = validate_browser_stage_packet(packet)
    assert validation["ok"] is False
    assert any("completed|blocked|partial" in issue for issue in validation["issues"])


def test_browser_stage_packet_rejects_completed_stage_ids_update_field() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "remoteMutationExpectation": "must_not",
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": False,
        },
        "ledgerUpdate": {
            "completedStageIds": ["refresh_readonly_site_evidence"],
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    validation = validate_browser_stage_packet(packet)
    assert validation["ok"] is False
    assert any("must not expose completedStageIds" in issue for issue in validation["issues"])


def test_module_capture_coverage_records_one_capture_without_replay_ready() -> None:
    plan = {
        "kind": "allincms_module_capture_plan",
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "authorizationAction": "create_product_probe",
                "requiredProof": ["request", "backend state"],
            },
            {
                "group": "content_probe_capture",
                "module": "posts",
                "action": "create",
                "authorizationAction": "create_post_probe",
                "requiredProof": ["request", "backend state"],
            },
        ],
    }
    result = build_capture_result(
        "products",
        "create",
        "captured",
        ["request", "backend state"],
        ["local://products-create-request.json"],
        [],
    )
    coverage = update_coverage(plan, result)
    validation = validate_coverage(coverage, plan)
    assert validation["ok"] is True
    assert coverage["coverageCounts"] == {
        "total": 2,
        "captured": 1,
        "pending": 1,
        "blocked": 0,
        "notApplicable": 0,
    }
    assert coverage["capturedStageKeys"] == ["products:create"]
    assert coverage["pendingStageKeys"] == ["posts:create"]
    assert coverage["nextUncapturedStageKey"] == "posts:create"
    assert coverage["complete"] is False
    assert coverage["interfaceCoverageComplete"] is False
    assert coverage["actionReplayContractsVerified"] is False
    assert coverage["jsonReplayReady"] is False
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "entries": [
            {
                "stageId": "module_interface_capture",
                "status": "partial",
                "authorizationRequired": True,
                "nextAllowedActions": [],
                "blockedUntil": ["coverage incomplete"],
            },
            {
                "stageId": "theme_page_route_launch",
                "status": "pending",
                "authorizationRequired": True,
                "nextAllowedActions": [],
                "blockedUntil": ["complete:module_interface_capture"],
            },
        ],
    }
    synced = sync_ledger_with_coverage(ledger, coverage)
    assert synced["nextStageId"] == "module_interface_capture"
    assert synced["stageCounts"]["ready"] == 1
    module_entry = synced["entries"][0]
    assert module_entry["status"] == "ready"
    assert any("posts:create" in action for action in module_entry["nextAllowedActions"])
    assert synced["entries"][1]["status"] == "pending"
    complete_result = build_capture_result(
        "posts",
        "create",
        "captured",
        ["request", "backend state"],
        ["local://posts-create-request.json"],
        [],
    )
    complete_coverage = update_coverage(plan, complete_result, coverage)
    assert complete_coverage["complete"] is True
    assert complete_coverage["interfaceCoverageComplete"] is True
    assert complete_coverage["actionReplayContractsVerified"] is False
    assert complete_coverage["jsonReplayReady"] is False
    complete_synced = sync_ledger_with_coverage(synced, complete_coverage)
    assert complete_synced["nextStageId"] == "theme_page_route_launch"
    assert complete_synced["entries"][0]["status"] == "completed"
    assert complete_synced["entries"][1]["status"] == "ready"


def action_replay_contract() -> dict:
    return {
        "kind": "allincms_action_replay_contract",
        "redacted": True,
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteKey": "mysite01",
        "module": "themes",
        "action": "publish_design",
        "targetType": "theme_page_design",
        "authorizationAction": "publish_design",
        "requestUrl": "https://workspace.laicms.com/mysite01/themes/theme-id/page-id/design",
        "method": "POST",
        "requiredHeaders": ["Accept", "Content-Type", "next-action", "next-router-state-tree"],
        "payloadKeys": ["siteId", "themeId", "pageId", "intent", "pageDocument"],
        "payloadShape": "redacted Next.js Server Action array with publish intent",
        "idFields": ["siteId", "themeId", "pageId"],
        "backendVerification": "designer status reloaded as Published",
        "persistedVerified": True,
        "publicEffect": True,
        "frontendVerified": True,
        "frontendVerification": "redacted route audit showed expected page DOM and no 404",
        "sampleReplayVerified": True,
        "rollbackOrCleanupPlan": "republish previous page version or restore captured draft if verification fails",
        "jsonReplayReady": True,
    }


def action_replay_contract_for(module: str, action: str) -> dict:
    contract = action_replay_contract()
    contract["module"] = module
    contract["action"] = action
    contract["authorizationAction"] = f"{action}_{module}"
    contract["targetType"] = module
    contract["requestUrl"] = f"https://workspace.laicms.com/mysite01/{module}/capture-target"
    if module in {"products", "posts"}:
        contract["publicEffect"] = False
        contract["frontendVerified"] = False
        contract.pop("frontendVerification", None)
    return contract


def test_action_replay_contract_accepts_redacted_public_action() -> None:
    errors = validate_action_replay_contract(action_replay_contract())
    assert errors == []


def test_action_replay_contract_rejects_missing_frontend_for_public_action() -> None:
    contract = action_replay_contract()
    contract["frontendVerified"] = False
    contract.pop("frontendVerification")
    errors = validate_action_replay_contract(contract)
    assert any("frontendVerified" in error for error in errors), errors
    assert any("frontendVerification" in error for error in errors), errors


def test_action_replay_contract_rejects_header_values_and_raw_action_id() -> None:
    contract = action_replay_contract()
    contract["requiredHeaders"] = ["Content-Type: text/plain;charset=UTF-8", "next-action: abcdef1234567890"]
    errors = validate_action_replay_contract(contract)
    assert any("header names only" in error for error in errors), errors
    assert any("sensitive or volatile" in error for error in errors), errors


def test_action_replay_contract_rejects_wrong_site_url_and_raw_id_value() -> None:
    contract = action_replay_contract()
    contract["requestUrl"] = "https://workspace.laicms.com/othersite/themes/theme-id/page-id/design"
    contract["idFields"] = ["siteId", "6a4275cdff2f32828d4a4d0f"]
    errors = validate_action_replay_contract(contract)
    assert any("requestUrl" in error and "siteKey" in error for error in errors), errors
    assert any("raw id value" in error for error in errors), errors


def complete_two_stage_coverage() -> dict:
    plan = {
        "kind": "allincms_module_capture_plan",
        "stages": [
            {
                "group": "content_probe_capture",
                "module": "products",
                "action": "create",
                "authorizationAction": "create_product_probe",
                "requiredProof": ["request", "backend state"],
            },
            {
                "group": "content_probe_capture",
                "module": "posts",
                "action": "create",
                "authorizationAction": "create_post_probe",
                "requiredProof": ["request", "backend state"],
            },
        ],
    }
    first = update_coverage(
        plan,
        build_capture_result("products", "create", "captured", ["request"], ["local://products-create.json"], []),
    )
    return update_coverage(
        plan,
        build_capture_result("posts", "create", "captured", ["request"], ["local://posts-create.json"], []),
        first,
    )


def test_apply_action_replay_contracts_marks_complete_coverage_replay_ready() -> None:
    coverage = complete_two_stage_coverage()
    updated = apply_action_replay_contracts(
        coverage,
        [
            action_replay_contract_for("products", "create"),
            action_replay_contract_for("posts", "create"),
        ],
    )
    assert updated["interfaceCoverageComplete"] is True
    assert updated["actionReplayContractsVerified"] is True
    assert updated["jsonReplayReady"] is True
    assert updated["replayContractStageKeys"] == ["products:create", "posts:create"]
    assert validate_coverage(updated)["ok"] is True


def test_replay_ready_coverage_syncs_clear_ledger_proof() -> None:
    coverage = apply_action_replay_contracts(
        complete_two_stage_coverage(),
        [
            action_replay_contract_for("products", "create"),
            action_replay_contract_for("posts", "create"),
        ],
    )
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "entries": [
            {
                "stageId": "module_interface_capture",
                "status": "partial",
                "authorizationRequired": True,
                "nextAllowedActions": [],
                "blockedUntil": ["coverage incomplete"],
            },
            {
                "stageId": "theme_page_route_launch",
                "status": "pending",
                "authorizationRequired": True,
                "nextAllowedActions": [],
                "blockedUntil": ["complete:module_interface_capture"],
            },
        ],
    }
    synced = sync_ledger_with_coverage(ledger, coverage)
    module_entry = synced["entries"][0]
    assert synced["lastCoverageSync"]["jsonReplayReady"] is True
    assert module_entry["status"] == "completed"
    assert module_entry["proofRecorded"] == ["module capture coverage complete; per-action replay contracts verified"]
    assert any("fresh action-time authorization" in action for action in module_entry["nextAllowedActions"])


def test_apply_action_replay_contracts_rejects_missing_contract() -> None:
    coverage = complete_two_stage_coverage()
    try:
        apply_action_replay_contracts(coverage, [action_replay_contract_for("products", "create")])
    except ValueError as exc:
        assert "missing replay contracts" in str(exc)
    else:
        raise AssertionError("missing replay contract was accepted")


def test_apply_action_replay_contracts_rejects_wrong_stage_contract() -> None:
    coverage = complete_two_stage_coverage()
    try:
        apply_action_replay_contracts(
            coverage,
            [
                action_replay_contract_for("products", "create"),
                action_replay_contract_for("routes", "create"),
            ],
        )
    except ValueError as exc:
        assert "does not match a captured coverage stage" in str(exc)
    else:
        raise AssertionError("wrong-stage replay contract was accepted")


def test_module_capture_result_rejects_unauditable_evidence_pointer() -> None:
    result = {
        "kind": "allincms_module_capture_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "module": "products",
        "action": "create",
        "status": "captured",
        "proofRecorded": ["request", "backend state"],
        "redactedEvidencePointers": ["verified"],
        "blockingIssues": [],
    }
    validation = validate_capture_result(result)
    assert validation["ok"] is False
    assert any("auditable pointers" in issue for issue in validation["issues"])


def test_browser_stage_result_rejects_missing_required_proof() -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog", "backend module URLs"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {"stageId": "refresh_readonly_site_evidence"},
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    result = {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "stageId": "refresh_readonly_site_evidence",
        "status": "completed",
        "redactedEvidencePointers": ["local://proof.json"],
        "proofRecorded": ["closed create dialog"],
        "blockingIssues": [],
    }
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is False
    assert any("missing required proof" in issue for issue in validation["issues"])


def test_browser_stage_result_rejects_unauditable_evidence_pointer() -> None:
    result = {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "stageId": "refresh_readonly_site_evidence",
        "status": "completed",
        "redactedEvidencePointers": ["done"],
        "proofRecorded": ["closed create dialog"],
        "blockingIssues": [],
    }
    validation = validate_browser_stage_result(result)
    assert validation["ok"] is False
    assert any("auditable pointers" in issue for issue in validation["issues"])


def test_browser_stage_result_rejects_concrete_workspace_site_url() -> None:
    result = {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "stageId": "content_probe_create",
        "status": "completed",
        "redactedEvidencePointers": ["https://workspace.laicms.com/abc123/products"],
        "proofRecorded": ["backend draft proof"],
        "blockingIssues": [],
    }
    validation = validate_browser_stage_result(result)
    assert validation["ok"] is False
    assert any("workspace site URLs" in issue for issue in validation["issues"])


def test_browser_stage_result_allows_redacted_workspace_site_url_template() -> None:
    result = {
        "kind": "allincms_browser_stage_result",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "browserStageMutatedRemote": False,
        "stageId": "content_probe_create",
        "status": "completed",
        "redactedEvidencePointers": ["https://workspace.laicms.com/{realSiteKey}/products"],
        "proofRecorded": ["backend draft proof"],
        "blockingIssues": [],
    }
    validation = validate_browser_stage_result(result)
    assert validation["ok"] is True


def test_browser_stage_result_allows_authorized_completed_remote_mutation_flag() -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "create_site_submit",
        "recovery": False,
        "phase": "site creation",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": True,
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/sites 执行 stage=create_site_submit",
        "allowedActions": ["submit create-site form"],
        "requiredProof": ["authorization record", "backend proof"],
        "forbiddenActions": ["batch upload"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "create_site_submit",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["create_site_submit"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    result = build_stage_result(
        "create_site_submit",
        "completed",
        ["local://created-site-proof.json"],
        packet["requiredProof"],
        [],
        True,
    )
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is True


def test_browser_stage_result_requires_expected_remote_mutation_flag() -> None:
    packet = {
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "create_site_submit",
        "recovery": False,
        "phase": "site creation",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": True,
        "remoteMutationExpectation": "must",
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/sites 执行 stage=create_site_submit",
        "allowedActions": ["submit create-site form"],
        "requiredProof": ["authorization record", "backend proof"],
        "forbiddenActions": ["batch upload"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "create_site_submit",
            "status": "completed|blocked|partial",
            "browserStageMutatedRemote": True,
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["create_site_submit"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    }
    result = build_stage_result(
        "create_site_submit",
        "completed",
        ["local://created-site-proof.json"],
        packet["requiredProof"],
        [],
    )
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is False
    assert any("must set browserStageMutatedRemote true" in issue for issue in validation["issues"])


def test_browser_stage_result_rejects_readonly_remote_mutation_flag() -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog"],
        "forbiddenActions": ["submit forms"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    result = build_stage_result(
        "refresh_readonly_site_evidence",
        "completed",
        ["local://readonly-proof.json"],
        packet["requiredProof"],
        [],
        True,
    )
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is False
    assert any("authorization-required" in issue for issue in validation["issues"])


def test_browser_stage_result_rejects_partial_remote_mutation_flag() -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "content_probe_create",
        "recovery": False,
        "phase": "content probe",
        "mode": "requires_authorization",
        "targetTemplate": "https://workspace.laicms.com/{realSiteKey}/{contentType}",
        "authorizationRequired": True,
        "suggestedAuthorizationText": "授权 Codex 仅在 https://workspace.laicms.com/{realSiteKey}/{contentType} 执行 stage=content_probe_create",
        "allowedActions": ["create probe draft"],
        "requiredProof": ["probe naming proof", "backend draft proof"],
        "forbiddenActions": ["publish"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "content_probe_create",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["content_probe_create"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    result = build_stage_result(
        "content_probe_create",
        "partial",
        ["local://probe-click-proof.json"],
        ["probe naming proof"],
        ["backend draft proof missing"],
        True,
    )
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is False
    assert any("completed stage status" in issue for issue in validation["issues"])


def test_browser_stage_result_builder_inherits_packet_required_proof(tmp_path: Path) -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog", "backend module URLs"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    class Args:
        packet_json = str(packet_path)
        status = "completed"
        evidence_pointers = "local://readonly-proof.json"
        proof_recorded = ""
        blocking_issues = ""
        operator_note = "redacted proof captured"

    result = build_browser_stage_result_from_packet(Args)
    assert result["stageId"] == "refresh_readonly_site_evidence"
    assert result["status"] == "completed"
    assert result["proofRecorded"] == packet["requiredProof"]
    assert result["redactedEvidencePointers"] == ["local://readonly-proof.json"]
    assert result["operatorNote"] == "redacted proof captured"
    validation = validate_browser_stage_result(result, packet)
    assert validation["ok"] is True


def test_browser_stage_result_builder_rejects_partial_without_blocker(tmp_path: Path) -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "static_frontend_audit",
        "recovery": False,
        "phase": "static audit",
        "mode": "verification",
        "targetTemplate": "https://{realSiteKey}.web.allincms.com",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["audit static pages"],
        "requiredProof": ["expected status map", "frontend rendering evidence"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "static_frontend_audit",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["static_frontend_audit"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    class Args:
        packet_json = str(packet_path)
        status = "partial"
        evidence_pointers = "local://static-audit-partial.json"
        proof_recorded = "expected status map"
        blocking_issues = ""
        operator_note = ""

    try:
        build_browser_stage_result_from_packet(Args)
    except ValueError as exc:
        assert "partial result requires blockingIssues" in str(exc)
    else:
        raise AssertionError("partial stage result without blocker was accepted")


def test_browser_stage_result_builder_rejects_manual_completed_missing_required_proof(tmp_path: Path) -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog", "backend module URLs"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    class Args:
        packet_json = str(packet_path)
        status = "completed"
        evidence_pointers = "local://readonly-proof.json"
        proof_recorded = "closed create dialog"
        blocking_issues = ""
        operator_note = ""

    try:
        build_browser_stage_result_from_packet(Args)
    except ValueError as exc:
        assert "missing required proof" in str(exc)
    else:
        raise AssertionError("manual completed result missing packet required proof was accepted")


def test_browser_stage_result_builder_rejects_unredacted_operator_note(tmp_path: Path) -> None:
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    class Args:
        packet_json = str(packet_path)
        status = "completed"
        evidence_pointers = "local://readonly-proof.json"
        proof_recorded = ""
        blocking_issues = ""
        operator_note = "account owner tony@example.com confirmed"

    try:
        build_browser_stage_result_from_packet(Args)
    except ValueError as exc:
        assert "email addresses" in str(exc)
    else:
        raise AssertionError("unredacted operator note was accepted")


def test_apply_stage_result_cli_inline_rejects_missing_packet_required_proof(tmp_path: Path) -> None:
    ledger = {
        "kind": "allincms_browser_execution_ledger",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourcePlanKind": "allincms_browser_execution_plan",
        "siteKeyTemplate": "{realSiteKey}",
        "stageCounts": {
            "total": 1,
            "ready": 1,
            "pending": 0,
            "completed": 0,
            "blocked": 0,
            "requiresAuthorization": 0,
        },
        "nextStageId": "refresh_readonly_site_evidence",
        "entries": [
            {
                "stageId": "refresh_readonly_site_evidence",
                "phase": "read-only refresh",
                "mode": "read_only",
                "status": "ready",
                "targetTemplate": "https://workspace.laicms.com/sites",
                "authorizationRequired": False,
                "dependsOn": [],
                "requiredProof": ["closed create dialog", "backend module URLs"],
                "stopAfter": "stop",
                "plannedActions": ["open sites list"],
                "nextAllowedActions": ["open sites list"],
                "blockedUntil": [],
            }
        ],
        "warnings": ["local only"],
    }
    packet = complete_test_browser_stage_packet({
        "kind": "allincms_browser_stage_packet",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": "allincms_browser_execution_ledger",
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": "refresh_readonly_site_evidence",
        "recovery": False,
        "phase": "read-only refresh",
        "mode": "read_only",
        "targetTemplate": "https://workspace.laicms.com/sites",
        "authorizationRequired": False,
        "suggestedAuthorizationText": "",
        "allowedActions": ["open sites list"],
        "requiredProof": ["closed create dialog", "backend module URLs"],
        "forbiddenActions": ["save"],
        "stopAfter": "stop",
        "evidenceCaptureTemplate": {
            "stageId": "refresh_readonly_site_evidence",
            "status": "completed|blocked|partial",
        },
        "ledgerUpdate": {
            "expectedCompletedStageIdsAfterApply": ["refresh_readonly_site_evidence"],
            "stageResultRequired": True,
            "commandTemplate": (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
                "--ledger ledger.json --packet packet.json --result-json result.json --output ledger.updated.json"
            ),
        },
        "warnings": ["local only"],
    })
    ledger_path = tmp_path / "ledger.json"
    packet_path = tmp_path / "packet.json"
    output_path = tmp_path / "updated.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py",
            "--ledger",
            str(ledger_path),
            "--packet",
            str(packet_path),
            "--stage-id",
            "refresh_readonly_site_evidence",
            "--status",
            "completed",
            "--evidence-pointers",
            "local://readonly-proof.json",
            "--proof-recorded",
            "closed create dialog",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 2
    assert "missing required proof" in result.stderr
    assert not output_path.exists()


def test_full_rehearsal_runs_all_local_gates_and_writes_summary() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        summary = run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        handoff_path = Path(tmp) / "next-capture-handoff" / "handoff.json"
        launch_plan_path = Path(tmp) / "launch-plan.json"
        browser_execution_plan_path = Path(tmp) / "browser-execution-plan.json"
        browser_execution_ledger_path = Path(tmp) / "browser-execution-ledger.json"
        browser_stage_packet_path = Path(tmp) / "next-browser-stage-packet.json"
        browser_stage_evidence_bundle_dir = Path(tmp) / "next-browser-stage-evidence-bundle"
        browser_stage_evidence_manifest_path = browser_stage_evidence_bundle_dir / "evidence-manifest.json"
        browser_runbook_summary_path = Path(tmp) / "browser-runbook-summary.json"
        simulated_stage_result_path = Path(tmp) / "simulated-first-stage-result.json"
        ledger_after_first_stage_path = Path(tmp) / "browser-execution-ledger-after-first-stage.json"
        browser_stage_packet_after_first_stage_path = Path(tmp) / "next-browser-stage-packet-after-first-stage.json"
        simulated_create_site_result_path = Path(tmp) / "simulated-create-site-result.json"
        ledger_after_create_site_path = Path(tmp) / "browser-execution-ledger-after-create-site.json"
        browser_stage_packet_after_create_site_path = Path(tmp) / "next-browser-stage-packet-after-create-site.json"
        simulated_setup_result_path = Path(tmp) / "simulated-setup-pages-result.json"
        ledger_after_setup_path = Path(tmp) / "browser-execution-ledger-after-setup-pages.json"
        browser_stage_packet_after_setup_path = Path(tmp) / "next-browser-stage-packet-after-setup-pages.json"
        browser_stage_module_capture_authorization_package_path = (
            Path(tmp) / "browser-stage-module-interface-authorization-package.json"
        )
        next_browser_action_handoff_path = Path(tmp) / "next-browser-action-handoff.json"
        simulated_module_capture_partial_result_path = Path(tmp) / "simulated-module-capture-partial-result.json"
        ledger_after_module_capture_partial_path = Path(tmp) / "browser-execution-ledger-after-module-capture-partial.json"
        simulated_module_capture_stage_result_path = Path(tmp) / "simulated-module-capture-stage-result.json"
        module_capture_coverage_path = Path(tmp) / "module-capture-coverage-after-one-stage.json"
        ledger_after_module_capture_coverage_sync_path = Path(tmp) / "browser-execution-ledger-after-module-capture-coverage-sync.json"
        module_capture_coverage_complete_path = Path(tmp) / "module-capture-coverage-complete.json"
        ledger_after_module_capture_complete_path = Path(tmp) / "browser-execution-ledger-after-module-capture-complete.json"
        browser_stage_packet_after_module_capture_complete_path = Path(tmp) / "next-browser-stage-packet-after-module-capture-complete.json"
        simulated_theme_launch_partial_result_path = Path(tmp) / "simulated-theme-launch-partial-result.json"
        ledger_after_theme_launch_partial_path = Path(tmp) / "browser-execution-ledger-after-theme-launch-partial.json"
        browser_stage_packet_after_theme_launch_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-theme-launch-partial-recovery.json"
        )
        ledger_after_theme_launch_recovery_complete_path = (
            Path(tmp) / "browser-execution-ledger-after-theme-launch-recovery-complete.json"
        )
        simulated_theme_launch_complete_result_path = Path(tmp) / "simulated-theme-launch-complete-result.json"
        ledger_after_theme_launch_complete_path = Path(tmp) / "browser-execution-ledger-after-theme-launch-complete.json"
        browser_stage_packet_after_theme_launch_complete_path = Path(tmp) / "next-browser-stage-packet-after-theme-launch-complete.json"
        simulated_static_audit_partial_result_path = Path(tmp) / "simulated-static-audit-partial-result.json"
        ledger_after_static_audit_partial_path = Path(tmp) / "browser-execution-ledger-after-static-audit-partial.json"
        browser_stage_packet_after_static_audit_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-static-audit-partial-recovery.json"
        )
        simulated_static_audit_complete_result_path = Path(tmp) / "simulated-static-audit-complete-result.json"
        ledger_after_static_audit_complete_path = Path(tmp) / "browser-execution-ledger-after-static-audit-complete.json"
        browser_stage_packet_after_static_audit_complete_path = Path(tmp) / "next-browser-stage-packet-after-static-audit-complete.json"
        simulated_content_probe_partial_result_path = Path(tmp) / "simulated-content-probe-partial-result.json"
        ledger_after_content_probe_partial_path = Path(tmp) / "browser-execution-ledger-after-content-probe-partial.json"
        browser_stage_packet_after_content_probe_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-content-probe-partial-recovery.json"
        )
        simulated_content_probe_complete_result_path = Path(tmp) / "simulated-content-probe-complete-result.json"
        ledger_after_content_probe_complete_path = Path(tmp) / "browser-execution-ledger-after-content-probe-complete.json"
        browser_stage_packet_after_content_probe_complete_path = Path(tmp) / "next-browser-stage-packet-after-content-probe-complete.json"
        simulated_save_request_partial_result_path = Path(tmp) / "simulated-save-request-partial-result.json"
        ledger_after_save_request_partial_path = Path(tmp) / "browser-execution-ledger-after-save-request-partial.json"
        browser_stage_packet_after_save_request_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-save-request-partial-recovery.json"
        )
        simulated_save_request_complete_result_path = Path(tmp) / "simulated-save-request-complete-result.json"
        ledger_after_save_request_complete_path = Path(tmp) / "browser-execution-ledger-after-save-request-complete.json"
        browser_stage_packet_after_save_request_complete_path = Path(tmp) / "next-browser-stage-packet-after-save-request-complete.json"
        simulated_publish_sample_partial_result_path = Path(tmp) / "simulated-publish-sample-partial-result.json"
        ledger_after_publish_sample_partial_path = Path(tmp) / "browser-execution-ledger-after-publish-sample-partial.json"
        browser_stage_packet_after_publish_sample_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-publish-sample-partial-recovery.json"
        )
        simulated_publish_sample_complete_result_path = Path(tmp) / "simulated-publish-sample-complete-result.json"
        ledger_after_publish_sample_complete_path = Path(tmp) / "browser-execution-ledger-after-publish-sample-complete.json"
        browser_stage_packet_after_publish_sample_complete_path = Path(tmp) / "next-browser-stage-packet-after-publish-sample-complete.json"
        simulated_manifest_gate_partial_result_path = Path(tmp) / "simulated-manifest-gate-partial-result.json"
        ledger_after_manifest_gate_partial_path = Path(tmp) / "browser-execution-ledger-after-manifest-gate-partial.json"
        browser_stage_packet_after_manifest_gate_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-manifest-gate-partial-recovery.json"
        )
        simulated_manifest_gate_complete_result_path = Path(tmp) / "simulated-manifest-gate-complete-result.json"
        ledger_after_manifest_gate_complete_path = Path(tmp) / "browser-execution-ledger-after-manifest-gate-complete.json"
        browser_stage_packet_after_manifest_gate_complete_path = Path(tmp) / "next-browser-stage-packet-after-manifest-gate-complete.json"
        simulated_batch_upload_partial_result_path = Path(tmp) / "simulated-batch-upload-partial-result.json"
        ledger_after_batch_upload_partial_path = Path(tmp) / "browser-execution-ledger-after-batch-upload-partial.json"
        browser_stage_packet_after_batch_upload_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-batch-upload-partial-recovery.json"
        )
        simulated_batch_upload_complete_result_path = Path(tmp) / "simulated-batch-upload-complete-result.json"
        ledger_after_batch_upload_complete_path = Path(tmp) / "browser-execution-ledger-after-batch-upload-complete.json"
        browser_stage_packet_after_batch_upload_complete_path = Path(tmp) / "next-browser-stage-packet-after-batch-upload-complete.json"
        simulated_forms_media_settings_partial_result_path = Path(tmp) / "simulated-forms-media-settings-partial-result.json"
        ledger_after_forms_media_settings_partial_path = Path(tmp) / "browser-execution-ledger-after-forms-media-settings-partial.json"
        browser_stage_packet_after_forms_media_settings_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-forms-media-settings-partial-recovery.json"
        )
        simulated_forms_media_settings_complete_result_path = Path(tmp) / "simulated-forms-media-settings-complete-result.json"
        ledger_after_forms_media_settings_complete_path = Path(tmp) / "browser-execution-ledger-after-forms-media-settings-complete.json"
        browser_stage_packet_after_forms_media_settings_complete_path = (
            Path(tmp) / "next-browser-stage-packet-after-forms-media-settings-complete.json"
        )
        simulated_final_frontend_audit_partial_result_path = Path(tmp) / "simulated-final-frontend-audit-partial-result.json"
        simulated_final_frontend_audit_partial_report_path = Path(tmp) / "simulated-final-audit-report-missing-detail.json"
        ledger_after_final_frontend_audit_partial_path = Path(tmp) / "browser-execution-ledger-after-final-frontend-audit-partial.json"
        browser_stage_packet_after_final_frontend_audit_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-final-frontend-audit-partial-recovery.json"
        )
        simulated_final_frontend_audit_complete_result_path = Path(tmp) / "simulated-final-frontend-audit-complete-result.json"
        simulated_final_frontend_audit_complete_report_path = Path(tmp) / "simulated-final-audit-report-complete.json"
        simulated_final_frontend_audit_inputs_summary_path = Path(tmp) / "simulated-final-audit-inputs-summary.json"
        simulated_final_frontend_audit_expected_statuses_path = Path(tmp) / "simulated-final-expected-statuses.json"
        ledger_after_final_frontend_audit_complete_path = Path(tmp) / "browser-execution-ledger-after-final-frontend-audit-complete.json"
        browser_stage_packet_after_final_frontend_audit_complete_path = (
            Path(tmp) / "next-browser-stage-packet-after-final-frontend-audit-complete.json"
        )
        simulated_cleanup_probes_partial_result_path = Path(tmp) / "simulated-cleanup-probes-partial-result.json"
        ledger_after_cleanup_probes_partial_path = Path(tmp) / "browser-execution-ledger-after-cleanup-probes-partial.json"
        browser_stage_packet_after_cleanup_probes_partial_recovery_path = (
            Path(tmp) / "next-browser-stage-packet-after-cleanup-probes-partial-recovery.json"
        )
        simulated_cleanup_probes_complete_result_path = Path(tmp) / "simulated-cleanup-probes-complete-result.json"
        ledger_after_cleanup_probes_complete_path = Path(tmp) / "browser-execution-ledger-after-cleanup-probes-complete.json"
        assert summary_path.exists()
        assert handoff_path.exists()
        assert launch_plan_path.exists()
        assert browser_execution_plan_path.exists()
        assert browser_execution_ledger_path.exists()
        assert browser_stage_packet_path.exists()
        assert simulated_stage_result_path.exists()
        assert ledger_after_first_stage_path.exists()
        assert browser_stage_packet_after_first_stage_path.exists()
        assert simulated_create_site_result_path.exists()
        assert ledger_after_create_site_path.exists()
        assert browser_stage_packet_after_create_site_path.exists()
        assert simulated_setup_result_path.exists()
        assert ledger_after_setup_path.exists()
        assert browser_stage_packet_after_setup_path.exists()
        assert browser_stage_module_capture_authorization_package_path.exists()
        assert next_browser_action_handoff_path.exists()
        assert simulated_module_capture_partial_result_path.exists()
        assert ledger_after_module_capture_partial_path.exists()
        assert simulated_module_capture_stage_result_path.exists()
        assert module_capture_coverage_path.exists()
        assert ledger_after_module_capture_coverage_sync_path.exists()
        assert module_capture_coverage_complete_path.exists()
        assert ledger_after_module_capture_complete_path.exists()
        assert browser_stage_packet_after_module_capture_complete_path.exists()
        assert simulated_theme_launch_partial_result_path.exists()
        assert ledger_after_theme_launch_partial_path.exists()
        assert browser_stage_packet_after_theme_launch_partial_recovery_path.exists()
        assert ledger_after_theme_launch_recovery_complete_path.exists()
        assert simulated_theme_launch_complete_result_path.exists()
        assert ledger_after_theme_launch_complete_path.exists()
        assert browser_stage_packet_after_theme_launch_complete_path.exists()
        assert simulated_static_audit_partial_result_path.exists()
        assert ledger_after_static_audit_partial_path.exists()
        assert browser_stage_packet_after_static_audit_partial_recovery_path.exists()
        assert simulated_static_audit_complete_result_path.exists()
        assert ledger_after_static_audit_complete_path.exists()
        assert browser_stage_packet_after_static_audit_complete_path.exists()
        assert simulated_content_probe_partial_result_path.exists()
        assert ledger_after_content_probe_partial_path.exists()
        assert browser_stage_packet_after_content_probe_partial_recovery_path.exists()
        assert simulated_content_probe_complete_result_path.exists()
        assert ledger_after_content_probe_complete_path.exists()
        assert browser_stage_packet_after_content_probe_complete_path.exists()
        assert simulated_save_request_partial_result_path.exists()
        assert ledger_after_save_request_partial_path.exists()
        assert browser_stage_packet_after_save_request_partial_recovery_path.exists()
        assert simulated_save_request_complete_result_path.exists()
        assert ledger_after_save_request_complete_path.exists()
        assert browser_stage_packet_after_save_request_complete_path.exists()
        assert simulated_publish_sample_partial_result_path.exists()
        assert ledger_after_publish_sample_partial_path.exists()
        assert browser_stage_packet_after_publish_sample_partial_recovery_path.exists()
        assert simulated_publish_sample_complete_result_path.exists()
        assert ledger_after_publish_sample_complete_path.exists()
        assert browser_stage_packet_after_publish_sample_complete_path.exists()
        assert simulated_manifest_gate_partial_result_path.exists()
        assert ledger_after_manifest_gate_partial_path.exists()
        assert browser_stage_packet_after_manifest_gate_partial_recovery_path.exists()
        assert simulated_manifest_gate_complete_result_path.exists()
        assert ledger_after_manifest_gate_complete_path.exists()
        assert browser_stage_packet_after_manifest_gate_complete_path.exists()
        assert simulated_batch_upload_partial_result_path.exists()
        assert ledger_after_batch_upload_partial_path.exists()
        assert browser_stage_packet_after_batch_upload_partial_recovery_path.exists()
        assert simulated_batch_upload_complete_result_path.exists()
        assert ledger_after_batch_upload_complete_path.exists()
        assert browser_stage_packet_after_batch_upload_complete_path.exists()
        assert simulated_forms_media_settings_partial_result_path.exists()
        assert ledger_after_forms_media_settings_partial_path.exists()
        assert browser_stage_packet_after_forms_media_settings_partial_recovery_path.exists()
        assert simulated_forms_media_settings_complete_result_path.exists()
        assert ledger_after_forms_media_settings_complete_path.exists()
        assert browser_stage_packet_after_forms_media_settings_complete_path.exists()
        assert simulated_final_frontend_audit_partial_result_path.exists()
        assert simulated_final_frontend_audit_partial_report_path.exists()
        assert ledger_after_final_frontend_audit_partial_path.exists()
        assert browser_stage_packet_after_final_frontend_audit_partial_recovery_path.exists()
        assert simulated_final_frontend_audit_complete_result_path.exists()
        assert simulated_final_frontend_audit_complete_report_path.exists()
        assert simulated_final_frontend_audit_inputs_summary_path.exists()
        assert simulated_final_frontend_audit_expected_statuses_path.exists()
        assert ledger_after_final_frontend_audit_complete_path.exists()
        assert browser_stage_packet_after_final_frontend_audit_complete_path.exists()
        assert simulated_cleanup_probes_partial_result_path.exists()
        assert ledger_after_cleanup_probes_partial_path.exists()
        assert browser_stage_packet_after_cleanup_probes_partial_recovery_path.exists()
        assert simulated_cleanup_probes_complete_result_path.exists()
        assert ledger_after_cleanup_probes_complete_path.exists()
        assert summary["kind"] == "allincms_full_rehearsal_summary"
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["commandsSuppressed"] is True
        assert summary["fullE2EValidation"]["ok"] is True
        assert summary["handoffSafety"]["ok"] is True
        assert summary["launchPlanSafety"]["ok"] is True
        assert summary["browserExecutionPlanSafety"]["ok"] is True
        assert summary["browserExecutionLedgerSafety"]["ok"] is True
        assert summary["browserStagePacketSafety"]["ok"] is True
        assert summary["browserStageEvidenceBundleSafety"]["ok"] is True
        assert summary["simulatedStageResultSafety"]["ok"] is True
        assert summary["ledgerAfterFirstStageSafety"]["ok"] is True
        assert summary["browserStagePacketAfterFirstStageSafety"]["ok"] is True
        assert summary["simulatedCreateSiteResultSafety"]["ok"] is True
        assert summary["ledgerAfterCreateSiteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterCreateSiteSafety"]["ok"] is True
        assert summary["simulatedSetupResultSafety"]["ok"] is True
        assert summary["ledgerAfterSetupSafety"]["ok"] is True
        assert summary["browserStagePacketAfterSetupSafety"]["ok"] is True
        assert summary["nextBrowserActionHandoffSafety"]["ok"] is True
        assert summary["simulatedModuleCapturePartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterModuleCapturePartialSafety"]["ok"] is True
        assert summary["moduleCaptureCoverageSafety"]["ok"] is True
        assert summary["ledgerAfterModuleCaptureCoverageSyncSafety"]["ok"] is True
        assert summary["moduleCaptureCoverageCompleteSafety"]["ok"] is True
        assert summary["ledgerAfterModuleCaptureCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterModuleCaptureCompleteSafety"]["ok"] is True
        assert summary["simulatedThemeLaunchPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterThemeLaunchPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterThemeLaunchPartialRecoverySafety"]["ok"] is True
        assert summary["ledgerAfterThemeLaunchRecoveryCompleteSafety"]["ok"] is True
        assert summary["simulatedThemeLaunchCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterThemeLaunchCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterThemeLaunchCompleteSafety"]["ok"] is True
        assert summary["simulatedStaticAuditPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterStaticAuditPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterStaticAuditPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedStaticAuditCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterStaticAuditCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterStaticAuditCompleteSafety"]["ok"] is True
        assert summary["simulatedContentProbePartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterContentProbePartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterContentProbePartialRecoverySafety"]["ok"] is True
        assert summary["simulatedContentProbeCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterContentProbeCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterContentProbeCompleteSafety"]["ok"] is True
        assert summary["simulatedSaveRequestPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterSaveRequestPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterSaveRequestPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedSaveRequestCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterSaveRequestCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterSaveRequestCompleteSafety"]["ok"] is True
        assert summary["simulatedPublishSamplePartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterPublishSamplePartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterPublishSamplePartialRecoverySafety"]["ok"] is True
        assert summary["simulatedPublishSampleCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterPublishSampleCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterPublishSampleCompleteSafety"]["ok"] is True
        assert summary["simulatedManifestGatePartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterManifestGatePartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterManifestGatePartialRecoverySafety"]["ok"] is True
        assert summary["simulatedManifestGateCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterManifestGateCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterManifestGateCompleteSafety"]["ok"] is True
        assert summary["simulatedBatchUploadPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterBatchUploadPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterBatchUploadPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedBatchUploadCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterBatchUploadCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterBatchUploadCompleteSafety"]["ok"] is True
        assert summary["simulatedFormsMediaSettingsPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterFormsMediaSettingsPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterFormsMediaSettingsPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedFormsMediaSettingsCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterFormsMediaSettingsCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterFormsMediaSettingsCompleteSafety"]["ok"] is True
        assert summary["simulatedFinalFrontendAuditPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterFinalFrontendAuditPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterFinalFrontendAuditPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedFinalFrontendAuditCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterFinalFrontendAuditCompleteSafety"]["ok"] is True
        assert summary["browserStagePacketAfterFinalFrontendAuditCompleteSafety"]["ok"] is True
        assert summary["simulatedCleanupProbesPartialResultSafety"]["ok"] is True
        assert summary["ledgerAfterCleanupProbesPartialSafety"]["ok"] is True
        assert summary["browserStagePacketAfterCleanupProbesPartialRecoverySafety"]["ok"] is True
        assert summary["simulatedCleanupProbesCompleteResultSafety"]["ok"] is True
        assert summary["ledgerAfterCleanupProbesCompleteSafety"]["ok"] is True
        assert summary["manifestRehearsal"]["sourceInputRequirementsGenerated"] is True
        assert summary["manifestRehearsal"]["sourceInputRequirementsBlocked"] is True
        assert summary["manifestRehearsal"]["sourceInputRequirementsBlockedUntilCount"] > 0
        source_requirements = json.loads(
            (Path(tmp) / "full-e2e" / "04-manifest-rehearsal" / "source-input-requirements.json").read_text(
                encoding="utf-8"
            )
        )
        assert source_requirements["operationGaps"]["entryCount"] == 1
        assert summary["manifestRehearsal"]["draftValidationPassed"] is True
        assert summary["manifestRehearsal"]["schemaGateExpectedFailure"] is True
        assert summary["selectedStage"]["module"] == "products"
        assert summary["launchPlan"]["proofGateCount"] >= 10
        assert summary["browserExecutionPlan"]["stageCount"] >= 14
        assert summary["browserExecutionPlan"]["authorizationStageCount"] >= 6
        assert summary["browserExecutionLedger"]["nextStageId"] == "refresh_readonly_site_evidence"
        assert summary["browserStagePacket"]["stageId"] == "refresh_readonly_site_evidence"
        assert summary["stageResultSimulation"]["stageId"] == "refresh_readonly_site_evidence"
        assert summary["stageResultSimulation"]["nextStageIdAfterApply"] == "create_site_submit"
        assert summary["browserStagePacketAfterFirstStage"]["stageId"] == "create_site_submit"
        assert summary["browserStagePacketAfterFirstStage"]["authorizationRequired"] is True
        assert summary["createSiteStageSimulation"]["stageId"] == "create_site_submit"
        assert summary["createSiteStageSimulation"]["nextStageIdAfterApply"] == "setup_pages_inspection"
        assert summary["browserStagePacketAfterCreateSite"]["stageId"] == "setup_pages_inspection"
        assert summary["browserStagePacketAfterCreateSite"]["authorizationRequired"] is False
        assert summary["setupStageSimulation"]["stageId"] == "setup_pages_inspection"
        assert summary["setupStageSimulation"]["nextStageIdAfterApply"] == "module_interface_capture"
        assert summary["browserStagePacketAfterSetup"]["stageId"] == "module_interface_capture"
        assert summary["browserStagePacketAfterSetup"]["authorizationRequired"] is True
        assert summary["moduleCapturePartialSimulation"]["stageId"] == "module_interface_capture"
        assert summary["moduleCapturePartialSimulation"]["status"] == "partial"
        assert summary["moduleCapturePartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["moduleCaptureCoverage"]["complete"] is False
        assert summary["moduleCaptureCoverage"]["interfaceCoverageComplete"] is False
        assert summary["moduleCaptureCoverage"]["actionReplayContractsVerified"] is False
        assert summary["moduleCaptureCoverage"]["jsonReplayReady"] is False
        assert summary["moduleCaptureCoverage"]["coverageCounts"]["captured"] == 1
        assert summary["moduleCaptureCoverage"]["coverageCounts"]["pending"] > 0
        assert summary["moduleCaptureCoverageLedgerSync"]["nextStageIdAfterSync"] == "module_interface_capture"
        assert any("posts:create" in action for action in summary["moduleCaptureCoverageLedgerSync"]["nextAllowedActions"])
        assert summary["moduleCaptureCompletionSimulation"]["complete"] is True
        assert summary["moduleCaptureCompletionSimulation"]["interfaceCoverageComplete"] is True
        assert summary["moduleCaptureCompletionSimulation"]["actionReplayContractsVerified"] is False
        assert summary["moduleCaptureCompletionSimulation"]["jsonReplayReady"] is False
        assert summary["moduleCaptureCompletionSimulation"]["coverageCounts"]["pending"] == 0
        assert summary["moduleCaptureCompletionSimulation"]["nextStageIdAfterSync"] == "theme_page_route_launch"
        assert summary["moduleCaptureCompletionSimulation"]["nextPacketStageId"] == "theme_page_route_launch"
        assert summary["themeLaunchPartialSimulation"]["stageId"] == "theme_page_route_launch"
        assert summary["themeLaunchPartialSimulation"]["status"] == "partial"
        assert summary["themeLaunchPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["themeLaunchPartialSimulation"]["recoveryPacketStageId"] == "theme_page_route_launch"
        assert summary["themeLaunchPartialSimulation"]["recoveryPacket"] is True
        assert summary["themeLaunchCompletionSimulation"]["stageId"] == "theme_page_route_launch"
        assert summary["themeLaunchCompletionSimulation"]["status"] == "completed"
        assert summary["themeLaunchCompletionSimulation"]["nextStageIdAfterApply"] == "static_frontend_audit"
        assert summary["themeLaunchCompletionSimulation"]["completedFromRecoveryPacket"] is True
        assert summary["themeLaunchCompletionSimulation"]["nextPacketStageId"] == "static_frontend_audit"
        assert summary["themeLaunchCompletionSimulation"]["nextPacketAuthorizationRequired"] is False
        assert summary["staticAuditPartialSimulation"]["stageId"] == "static_frontend_audit"
        assert summary["staticAuditPartialSimulation"]["status"] == "partial"
        assert summary["staticAuditPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["staticAuditPartialSimulation"]["recoveryPacketStageId"] == "static_frontend_audit"
        assert summary["staticAuditPartialSimulation"]["recoveryPacket"] is True
        assert summary["staticAuditCompletionSimulation"]["stageId"] == "static_frontend_audit"
        assert summary["staticAuditCompletionSimulation"]["status"] == "completed"
        assert summary["staticAuditCompletionSimulation"]["nextStageIdAfterApply"] == "content_probe_create"
        assert summary["staticAuditCompletionSimulation"]["nextPacketStageId"] == "content_probe_create"
        assert summary["staticAuditCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["contentProbePartialSimulation"]["stageId"] == "content_probe_create"
        assert summary["contentProbePartialSimulation"]["status"] == "partial"
        assert summary["contentProbePartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["contentProbePartialSimulation"]["recoveryPacketStageId"] == "content_probe_create"
        assert summary["contentProbePartialSimulation"]["recoveryPacket"] is True
        assert summary["contentProbeCompletionSimulation"]["stageId"] == "content_probe_create"
        assert summary["contentProbeCompletionSimulation"]["status"] == "completed"
        assert summary["contentProbeCompletionSimulation"]["nextStageIdAfterApply"] == "save_request_capture"
        assert summary["contentProbeCompletionSimulation"]["nextPacketStageId"] == "save_request_capture"
        assert summary["contentProbeCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["saveRequestPartialSimulation"]["stageId"] == "save_request_capture"
        assert summary["saveRequestPartialSimulation"]["status"] == "partial"
        assert summary["saveRequestPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["saveRequestPartialSimulation"]["recoveryPacketStageId"] == "save_request_capture"
        assert summary["saveRequestPartialSimulation"]["recoveryPacket"] is True
        assert summary["saveRequestCompletionSimulation"]["stageId"] == "save_request_capture"
        assert summary["saveRequestCompletionSimulation"]["status"] == "completed"
        assert summary["saveRequestCompletionSimulation"]["nextStageIdAfterApply"] == "publish_sample_verify"
        assert summary["saveRequestCompletionSimulation"]["nextPacketStageId"] == "publish_sample_verify"
        assert summary["saveRequestCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["saveRequestCompletionSimulation"]["manifestSchemaGateReady"] is True
        assert summary["publishSamplePartialSimulation"]["stageId"] == "publish_sample_verify"
        assert summary["publishSamplePartialSimulation"]["status"] == "partial"
        assert summary["publishSamplePartialSimulation"]["nextStageIdAfterApply"] == "manifest_schema_gate"
        assert summary["publishSamplePartialSimulation"]["recoveryPacketStageId"] == "publish_sample_verify"
        assert summary["publishSamplePartialSimulation"]["recoveryPacket"] is True
        assert summary["publishSamplePartialSimulation"]["manifestSchemaGateStillReady"] is True
        assert summary["publishSampleCompletionSimulation"]["stageId"] == "publish_sample_verify"
        assert summary["publishSampleCompletionSimulation"]["status"] == "completed"
        assert summary["publishSampleCompletionSimulation"]["nextStageIdAfterApply"] == "manifest_schema_gate"
        assert summary["publishSampleCompletionSimulation"]["nextPacketStageId"] == "manifest_schema_gate"
        assert summary["publishSampleCompletionSimulation"]["nextPacketAuthorizationRequired"] is False
        assert summary["manifestGatePartialSimulation"]["stageId"] == "manifest_schema_gate"
        assert summary["manifestGatePartialSimulation"]["status"] == "partial"
        assert summary["manifestGatePartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["manifestGatePartialSimulation"]["recoveryPacketStageId"] == "manifest_schema_gate"
        assert summary["manifestGatePartialSimulation"]["recoveryPacket"] is True
        assert summary["manifestGateCompletionSimulation"]["stageId"] == "manifest_schema_gate"
        assert summary["manifestGateCompletionSimulation"]["status"] == "completed"
        assert summary["manifestGateCompletionSimulation"]["nextStageIdAfterApply"] == "batch_upload_publish"
        assert summary["manifestGateCompletionSimulation"]["nextPacketStageId"] == "batch_upload_publish"
        assert summary["manifestGateCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["batchUploadPartialSimulation"]["stageId"] == "batch_upload_publish"
        assert summary["batchUploadPartialSimulation"]["status"] == "partial"
        assert summary["batchUploadPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["batchUploadPartialSimulation"]["recoveryPacketStageId"] == "batch_upload_publish"
        assert summary["batchUploadPartialSimulation"]["recoveryPacket"] is True
        assert summary["batchUploadCompletionSimulation"]["stageId"] == "batch_upload_publish"
        assert summary["batchUploadCompletionSimulation"]["status"] == "completed"
        assert summary["batchUploadCompletionSimulation"]["nextStageIdAfterApply"] == "forms_media_settings"
        assert summary["batchUploadCompletionSimulation"]["nextPacketStageId"] == "forms_media_settings"
        assert summary["batchUploadCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["formsMediaSettingsPartialSimulation"]["stageId"] == "forms_media_settings"
        assert summary["formsMediaSettingsPartialSimulation"]["status"] == "partial"
        assert summary["formsMediaSettingsPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["formsMediaSettingsPartialSimulation"]["recoveryPacketStageId"] == "forms_media_settings"
        assert summary["formsMediaSettingsPartialSimulation"]["recoveryPacket"] is True
        assert summary["formsMediaSettingsCompletionSimulation"]["stageId"] == "forms_media_settings"
        assert summary["formsMediaSettingsCompletionSimulation"]["status"] == "completed"
        assert summary["formsMediaSettingsCompletionSimulation"]["nextStageIdAfterApply"] == "final_frontend_audit"
        assert summary["formsMediaSettingsCompletionSimulation"]["nextPacketStageId"] == "final_frontend_audit"
        assert summary["formsMediaSettingsCompletionSimulation"]["nextPacketAuthorizationRequired"] is False
        assert summary["finalFrontendAuditPartialSimulation"]["stageId"] == "final_frontend_audit"
        assert summary["finalFrontendAuditPartialSimulation"]["status"] == "partial"
        assert summary["finalFrontendAuditPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["finalFrontendAuditPartialSimulation"]["recoveryPacketStageId"] == "final_frontend_audit"
        assert summary["finalFrontendAuditPartialSimulation"]["recoveryPacket"] is True
        assert summary["finalFrontendAuditCompletionSimulation"]["stageId"] == "final_frontend_audit"
        assert summary["finalFrontendAuditCompletionSimulation"]["status"] == "completed"
        assert summary["finalFrontendAuditCompletionSimulation"]["nextStageIdAfterApply"] == "cleanup_probes"
        assert summary["finalFrontendAuditCompletionSimulation"]["nextPacketStageId"] == "cleanup_probes"
        assert summary["finalFrontendAuditCompletionSimulation"]["nextPacketAuthorizationRequired"] is True
        assert summary["cleanupProbesPartialSimulation"]["stageId"] == "cleanup_probes"
        assert summary["cleanupProbesPartialSimulation"]["status"] == "partial"
        assert summary["cleanupProbesPartialSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["cleanupProbesPartialSimulation"]["recoveryPacketStageId"] == "cleanup_probes"
        assert summary["cleanupProbesPartialSimulation"]["recoveryPacket"] is True
        assert summary["cleanupProbesCompletionSimulation"]["stageId"] == "cleanup_probes"
        assert summary["cleanupProbesCompletionSimulation"]["status"] == "completed"
        assert summary["cleanupProbesCompletionSimulation"]["nextStageIdAfterApply"] == ""
        assert summary["finalLedgerExhaustion"]["allStagesCompleted"] is True
        assert summary["finalLedgerExhaustion"]["nextStageId"] == ""
        assert summary["finalLedgerExhaustion"]["packetBuildRejected"] is True
        assert "no nextStageId" in summary["finalLedgerExhaustion"]["rejectionReason"]
        for recovery_completion_key in (
            "staticAuditCompletionSimulation",
            "contentProbeCompletionSimulation",
            "saveRequestCompletionSimulation",
            "publishSampleCompletionSimulation",
            "manifestGateCompletionSimulation",
            "batchUploadCompletionSimulation",
            "formsMediaSettingsCompletionSimulation",
            "finalFrontendAuditCompletionSimulation",
            "cleanupProbesCompletionSimulation",
        ):
            assert summary[recovery_completion_key]["completedFromRecoveryPacket"] is True
        persisted = json.loads(summary_path.read_text(encoding="utf-8"))
        assert browser_runbook_summary_path.exists()
        browser_runbook_summary = json.loads(browser_runbook_summary_path.read_text(encoding="utf-8"))
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
        browser_execution_plan = json.loads(browser_execution_plan_path.read_text(encoding="utf-8"))
        browser_execution_ledger = json.loads(browser_execution_ledger_path.read_text(encoding="utf-8"))
        browser_stage_packet = json.loads(browser_stage_packet_path.read_text(encoding="utf-8"))
        assert browser_stage_evidence_bundle_dir.exists()
        assert browser_stage_evidence_manifest_path.exists()
        browser_stage_evidence_manifest = json.loads(browser_stage_evidence_manifest_path.read_text(encoding="utf-8"))
        simulated_stage_result = json.loads(simulated_stage_result_path.read_text(encoding="utf-8"))
        ledger_after_first_stage = json.loads(ledger_after_first_stage_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_first_stage = json.loads(browser_stage_packet_after_first_stage_path.read_text(encoding="utf-8"))
        simulated_create_site_result = json.loads(simulated_create_site_result_path.read_text(encoding="utf-8"))
        ledger_after_create_site = json.loads(ledger_after_create_site_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_create_site = json.loads(browser_stage_packet_after_create_site_path.read_text(encoding="utf-8"))
        simulated_setup_result = json.loads(simulated_setup_result_path.read_text(encoding="utf-8"))
        ledger_after_setup = json.loads(ledger_after_setup_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_setup = json.loads(browser_stage_packet_after_setup_path.read_text(encoding="utf-8"))
        browser_stage_module_capture_authorization_package = json.loads(
            browser_stage_module_capture_authorization_package_path.read_text(encoding="utf-8")
        )
        next_browser_action_handoff = json.loads(next_browser_action_handoff_path.read_text(encoding="utf-8"))
        simulated_module_capture_partial_result = json.loads(simulated_module_capture_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_module_capture_partial = json.loads(ledger_after_module_capture_partial_path.read_text(encoding="utf-8"))
        simulated_module_capture_stage_result = json.loads(simulated_module_capture_stage_result_path.read_text(encoding="utf-8"))
        module_capture_coverage = json.loads(module_capture_coverage_path.read_text(encoding="utf-8"))
        ledger_after_module_capture_coverage_sync = json.loads(
            ledger_after_module_capture_coverage_sync_path.read_text(encoding="utf-8")
        )
        module_capture_coverage_complete = json.loads(module_capture_coverage_complete_path.read_text(encoding="utf-8"))
        ledger_after_module_capture_complete = json.loads(ledger_after_module_capture_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_module_capture_complete = json.loads(
            browser_stage_packet_after_module_capture_complete_path.read_text(encoding="utf-8")
        )
        simulated_theme_launch_partial_result = json.loads(simulated_theme_launch_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_theme_launch_partial = json.loads(ledger_after_theme_launch_partial_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_theme_launch_partial_recovery = json.loads(
            browser_stage_packet_after_theme_launch_partial_recovery_path.read_text(encoding="utf-8")
        )
        ledger_after_theme_launch_recovery_complete = json.loads(
            ledger_after_theme_launch_recovery_complete_path.read_text(encoding="utf-8")
        )
        simulated_theme_launch_complete_result = json.loads(simulated_theme_launch_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_theme_launch_complete = json.loads(ledger_after_theme_launch_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_theme_launch_complete = json.loads(
            browser_stage_packet_after_theme_launch_complete_path.read_text(encoding="utf-8")
        )
        simulated_static_audit_partial_result = json.loads(simulated_static_audit_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_static_audit_partial = json.loads(ledger_after_static_audit_partial_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_static_audit_partial_recovery = json.loads(
            browser_stage_packet_after_static_audit_partial_recovery_path.read_text(encoding="utf-8")
        )
        simulated_static_audit_complete_result = json.loads(simulated_static_audit_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_static_audit_complete = json.loads(ledger_after_static_audit_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_static_audit_complete = json.loads(
            browser_stage_packet_after_static_audit_complete_path.read_text(encoding="utf-8")
        )
        simulated_content_probe_partial_result = json.loads(simulated_content_probe_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_content_probe_partial = json.loads(ledger_after_content_probe_partial_path.read_text(encoding="utf-8"))
        simulated_content_probe_complete_result = json.loads(simulated_content_probe_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_content_probe_complete = json.loads(ledger_after_content_probe_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_content_probe_complete = json.loads(
            browser_stage_packet_after_content_probe_complete_path.read_text(encoding="utf-8")
        )
        simulated_save_request_partial_result = json.loads(simulated_save_request_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_save_request_partial = json.loads(ledger_after_save_request_partial_path.read_text(encoding="utf-8"))
        simulated_save_request_complete_result = json.loads(simulated_save_request_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_save_request_complete = json.loads(ledger_after_save_request_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_save_request_complete = json.loads(
            browser_stage_packet_after_save_request_complete_path.read_text(encoding="utf-8")
        )
        simulated_publish_sample_partial_result = json.loads(simulated_publish_sample_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_publish_sample_partial = json.loads(ledger_after_publish_sample_partial_path.read_text(encoding="utf-8"))
        simulated_publish_sample_complete_result = json.loads(simulated_publish_sample_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_publish_sample_complete = json.loads(ledger_after_publish_sample_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_publish_sample_complete = json.loads(
            browser_stage_packet_after_publish_sample_complete_path.read_text(encoding="utf-8")
        )
        simulated_manifest_gate_partial_result = json.loads(simulated_manifest_gate_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_manifest_gate_partial = json.loads(ledger_after_manifest_gate_partial_path.read_text(encoding="utf-8"))
        simulated_manifest_gate_complete_result = json.loads(simulated_manifest_gate_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_manifest_gate_complete = json.loads(ledger_after_manifest_gate_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_manifest_gate_complete = json.loads(
            browser_stage_packet_after_manifest_gate_complete_path.read_text(encoding="utf-8")
        )
        simulated_batch_upload_partial_result = json.loads(simulated_batch_upload_partial_result_path.read_text(encoding="utf-8"))
        ledger_after_batch_upload_partial = json.loads(ledger_after_batch_upload_partial_path.read_text(encoding="utf-8"))
        simulated_batch_upload_complete_result = json.loads(simulated_batch_upload_complete_result_path.read_text(encoding="utf-8"))
        ledger_after_batch_upload_complete = json.loads(ledger_after_batch_upload_complete_path.read_text(encoding="utf-8"))
        browser_stage_packet_after_batch_upload_complete = json.loads(
            browser_stage_packet_after_batch_upload_complete_path.read_text(encoding="utf-8")
        )
        simulated_forms_media_settings_partial_result = json.loads(
            simulated_forms_media_settings_partial_result_path.read_text(encoding="utf-8")
        )
        ledger_after_forms_media_settings_partial = json.loads(
            ledger_after_forms_media_settings_partial_path.read_text(encoding="utf-8")
        )
        simulated_forms_media_settings_complete_result = json.loads(
            simulated_forms_media_settings_complete_result_path.read_text(encoding="utf-8")
        )
        ledger_after_forms_media_settings_complete = json.loads(
            ledger_after_forms_media_settings_complete_path.read_text(encoding="utf-8")
        )
        browser_stage_packet_after_forms_media_settings_complete = json.loads(
            browser_stage_packet_after_forms_media_settings_complete_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_partial_result = json.loads(
            simulated_final_frontend_audit_partial_result_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_partial_report = json.loads(
            simulated_final_frontend_audit_partial_report_path.read_text(encoding="utf-8")
        )
        ledger_after_final_frontend_audit_partial = json.loads(
            ledger_after_final_frontend_audit_partial_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_complete_result = json.loads(
            simulated_final_frontend_audit_complete_result_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_complete_report = json.loads(
            simulated_final_frontend_audit_complete_report_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_inputs_summary = json.loads(
            simulated_final_frontend_audit_inputs_summary_path.read_text(encoding="utf-8")
        )
        simulated_final_frontend_audit_expected_statuses = json.loads(
            simulated_final_frontend_audit_expected_statuses_path.read_text(encoding="utf-8")
        )
        ledger_after_final_frontend_audit_complete = json.loads(
            ledger_after_final_frontend_audit_complete_path.read_text(encoding="utf-8")
        )
        browser_stage_packet_after_final_frontend_audit_complete = json.loads(
            browser_stage_packet_after_final_frontend_audit_complete_path.read_text(encoding="utf-8")
        )
        simulated_cleanup_probes_partial_result = json.loads(
            simulated_cleanup_probes_partial_result_path.read_text(encoding="utf-8")
        )
        ledger_after_cleanup_probes_partial = json.loads(ledger_after_cleanup_probes_partial_path.read_text(encoding="utf-8"))
        simulated_cleanup_probes_complete_result = json.loads(
            simulated_cleanup_probes_complete_result_path.read_text(encoding="utf-8")
        )
        ledger_after_cleanup_probes_complete = json.loads(ledger_after_cleanup_probes_complete_path.read_text(encoding="utf-8"))
        def assert_packet_command_paths(packet: dict, ledger_path: Path, packet_path: Path) -> None:
            command = packet["ledgerUpdate"]["commandTemplate"]
            assert str(ledger_path) in command
            assert str(packet_path) in command
            assert str(packet_path.with_name(packet_path.stem + "-stage-result.json")) in command
            assert str(ledger_path.with_name(ledger_path.stem + f".after-{packet['stageId']}.json")) in command
            assert "~/allincms-projects/allincms-full-rehearsal/" not in command or str(packet_path).startswith("~/allincms-projects/allincms-full-rehearsal/")

        assert_packet_command_paths(browser_stage_packet, browser_execution_ledger_path, browser_stage_packet_path)
        assert_packet_command_paths(
            browser_stage_packet_after_first_stage,
            ledger_after_first_stage_path,
            browser_stage_packet_after_first_stage_path,
        )
        assert_packet_command_paths(
            browser_stage_packet_after_static_audit_complete,
            ledger_after_static_audit_complete_path,
            browser_stage_packet_after_static_audit_complete_path,
        )
        assert_packet_command_paths(
            browser_stage_packet_after_static_audit_partial_recovery,
            ledger_after_static_audit_partial_path,
            browser_stage_packet_after_static_audit_partial_recovery_path,
        )
        assert persisted["artifacts"]["handoff"] == str(handoff_path)
        assert persisted["artifacts"]["launchPlan"] == str(launch_plan_path)
        assert persisted["artifacts"]["browserExecutionPlan"] == str(browser_execution_plan_path)
        assert persisted["artifacts"]["browserExecutionLedger"] == str(browser_execution_ledger_path)
        assert persisted["artifacts"]["browserStagePacket"] == str(browser_stage_packet_path)
        assert persisted["artifacts"]["browserStageEvidenceBundle"] == str(browser_stage_evidence_bundle_dir)
        assert persisted["artifacts"]["browserStageEvidenceManifest"] == str(browser_stage_evidence_manifest_path)
        assert persisted["browserStageEvidenceManifest"]["stageId"] == browser_stage_packet["stageId"]
        assert browser_stage_evidence_manifest["stageId"] == browser_stage_packet["stageId"]
        assert browser_stage_evidence_manifest["remoteMutationsPerformed"] is False
        assert persisted["browserRunbookSummaryPath"] == str(browser_runbook_summary_path)
        assert persisted["artifacts"]["browserRunbookSummary"] == str(browser_runbook_summary_path)
        assert persisted["browserRunbookSummary"]["kind"] == "allincms_browser_runbook_summary"
        assert persisted["browserRunbookSummary"]["sourceValid"] is True
        assert persisted["browserRunbookSummary"]["nextStageId"] == "refresh_readonly_site_evidence"
        assert persisted["browserRunbookSummary"]["authorizationRequired"] is False
        assert persisted["browserRunbookSummary"]["commandsSuppressed"] is True
        assert persisted["browserRunbookSummary"]["initialLedgerNextStageId"] == "refresh_readonly_site_evidence"
        assert browser_runbook_summary["nextRealBrowserStep"]["stageId"] == "refresh_readonly_site_evidence"
        assert browser_runbook_summary["nextRealBrowserStep"]["evidenceBundle"] == str(browser_stage_evidence_bundle_dir)
        assert browser_runbook_summary["nextRealBrowserStep"]["evidenceManifest"] == str(browser_stage_evidence_manifest_path)
        assert browser_runbook_summary["requiredLocalArtifacts"]["nextBrowserStageEvidenceBundle"] == str(
            browser_stage_evidence_bundle_dir
        )
        assert browser_runbook_summary["requiredLocalArtifacts"]["nextBrowserStageEvidenceManifest"] == str(
            browser_stage_evidence_manifest_path
        )
        assert browser_runbook_summary["coverage"]["initialLedgerNextStageId"] == "refresh_readonly_site_evidence"
        assert persisted["artifacts"]["simulatedStageResult"] == str(simulated_stage_result_path)
        assert persisted["artifacts"]["ledgerAfterFirstStage"] == str(ledger_after_first_stage_path)
        assert persisted["artifacts"]["browserStagePacketAfterFirstStage"] == str(browser_stage_packet_after_first_stage_path)
        assert persisted["artifacts"]["simulatedCreateSiteResult"] == str(simulated_create_site_result_path)
        assert persisted["artifacts"]["ledgerAfterCreateSite"] == str(ledger_after_create_site_path)
        assert persisted["artifacts"]["browserStagePacketAfterCreateSite"] == str(browser_stage_packet_after_create_site_path)
        assert persisted["artifacts"]["simulatedSetupResult"] == str(simulated_setup_result_path)
        assert persisted["artifacts"]["ledgerAfterSetup"] == str(ledger_after_setup_path)
        assert persisted["artifacts"]["browserStagePacketAfterSetup"] == str(browser_stage_packet_after_setup_path)
        assert persisted["artifacts"]["browserStageModuleCaptureAuthorizationPackage"] == str(
            browser_stage_module_capture_authorization_package_path
        )
        assert persisted["artifacts"]["nextBrowserActionHandoff"] == str(next_browser_action_handoff_path)
        assert persisted["artifacts"]["simulatedModuleCapturePartialResult"] == str(simulated_module_capture_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterModuleCapturePartial"] == str(ledger_after_module_capture_partial_path)
        assert persisted["artifacts"]["simulatedModuleCaptureStageResult"] == str(simulated_module_capture_stage_result_path)
        assert persisted["artifacts"]["moduleCaptureCoverage"] == str(module_capture_coverage_path)
        assert persisted["artifacts"]["ledgerAfterModuleCaptureCoverageSync"] == str(ledger_after_module_capture_coverage_sync_path)
        assert persisted["artifacts"]["moduleCaptureCoverageComplete"] == str(module_capture_coverage_complete_path)
        assert persisted["artifacts"]["ledgerAfterModuleCaptureComplete"] == str(ledger_after_module_capture_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterModuleCaptureComplete"] == str(
            browser_stage_packet_after_module_capture_complete_path
        )
        assert persisted["artifacts"]["simulatedThemeLaunchPartialResult"] == str(simulated_theme_launch_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterThemeLaunchPartial"] == str(ledger_after_theme_launch_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterThemeLaunchPartialRecovery"] == str(
            browser_stage_packet_after_theme_launch_partial_recovery_path
        )
        assert persisted["artifacts"]["ledgerAfterThemeLaunchRecoveryComplete"] == str(
            ledger_after_theme_launch_recovery_complete_path
        )
        assert persisted["artifacts"]["simulatedThemeLaunchCompleteResult"] == str(simulated_theme_launch_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterThemeLaunchComplete"] == str(ledger_after_theme_launch_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterThemeLaunchComplete"] == str(
            browser_stage_packet_after_theme_launch_complete_path
        )
        assert persisted["artifacts"]["simulatedStaticAuditPartialResult"] == str(simulated_static_audit_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterStaticAuditPartial"] == str(ledger_after_static_audit_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterStaticAuditPartialRecovery"] == str(
            browser_stage_packet_after_static_audit_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedStaticAuditCompleteResult"] == str(simulated_static_audit_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterStaticAuditComplete"] == str(ledger_after_static_audit_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterStaticAuditComplete"] == str(
            browser_stage_packet_after_static_audit_complete_path
        )
        assert persisted["artifacts"]["simulatedContentProbePartialResult"] == str(simulated_content_probe_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterContentProbePartial"] == str(ledger_after_content_probe_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterContentProbePartialRecovery"] == str(
            browser_stage_packet_after_content_probe_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedContentProbeCompleteResult"] == str(simulated_content_probe_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterContentProbeComplete"] == str(ledger_after_content_probe_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterContentProbeComplete"] == str(
            browser_stage_packet_after_content_probe_complete_path
        )
        assert persisted["artifacts"]["simulatedSaveRequestPartialResult"] == str(simulated_save_request_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterSaveRequestPartial"] == str(ledger_after_save_request_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterSaveRequestPartialRecovery"] == str(
            browser_stage_packet_after_save_request_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedSaveRequestCompleteResult"] == str(simulated_save_request_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterSaveRequestComplete"] == str(ledger_after_save_request_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterSaveRequestComplete"] == str(
            browser_stage_packet_after_save_request_complete_path
        )
        assert persisted["artifacts"]["simulatedPublishSamplePartialResult"] == str(simulated_publish_sample_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterPublishSamplePartial"] == str(ledger_after_publish_sample_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterPublishSamplePartialRecovery"] == str(
            browser_stage_packet_after_publish_sample_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedPublishSampleCompleteResult"] == str(simulated_publish_sample_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterPublishSampleComplete"] == str(ledger_after_publish_sample_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterPublishSampleComplete"] == str(
            browser_stage_packet_after_publish_sample_complete_path
        )
        assert persisted["artifacts"]["simulatedManifestGatePartialResult"] == str(simulated_manifest_gate_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterManifestGatePartial"] == str(ledger_after_manifest_gate_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterManifestGatePartialRecovery"] == str(
            browser_stage_packet_after_manifest_gate_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedManifestGateCompleteResult"] == str(simulated_manifest_gate_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterManifestGateComplete"] == str(ledger_after_manifest_gate_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterManifestGateComplete"] == str(
            browser_stage_packet_after_manifest_gate_complete_path
        )
        assert persisted["artifacts"]["simulatedBatchUploadPartialResult"] == str(simulated_batch_upload_partial_result_path)
        assert persisted["artifacts"]["ledgerAfterBatchUploadPartial"] == str(ledger_after_batch_upload_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterBatchUploadPartialRecovery"] == str(
            browser_stage_packet_after_batch_upload_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedBatchUploadCompleteResult"] == str(simulated_batch_upload_complete_result_path)
        assert persisted["artifacts"]["ledgerAfterBatchUploadComplete"] == str(ledger_after_batch_upload_complete_path)
        assert persisted["artifacts"]["browserStagePacketAfterBatchUploadComplete"] == str(
            browser_stage_packet_after_batch_upload_complete_path
        )
        assert persisted["artifacts"]["simulatedFormsMediaSettingsPartialResult"] == str(
            simulated_forms_media_settings_partial_result_path
        )
        assert persisted["artifacts"]["ledgerAfterFormsMediaSettingsPartial"] == str(
            ledger_after_forms_media_settings_partial_path
        )
        assert persisted["artifacts"]["browserStagePacketAfterFormsMediaSettingsPartialRecovery"] == str(
            browser_stage_packet_after_forms_media_settings_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedFormsMediaSettingsCompleteResult"] == str(
            simulated_forms_media_settings_complete_result_path
        )
        assert persisted["artifacts"]["ledgerAfterFormsMediaSettingsComplete"] == str(
            ledger_after_forms_media_settings_complete_path
        )
        assert persisted["artifacts"]["browserStagePacketAfterFormsMediaSettingsComplete"] == str(
            browser_stage_packet_after_forms_media_settings_complete_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditPartialResult"] == str(
            simulated_final_frontend_audit_partial_result_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditPartialReport"] == str(
            simulated_final_frontend_audit_partial_report_path
        )
        assert persisted["artifacts"]["ledgerAfterFinalFrontendAuditPartial"] == str(
            ledger_after_final_frontend_audit_partial_path
        )
        assert persisted["artifacts"]["browserStagePacketAfterFinalFrontendAuditPartialRecovery"] == str(
            browser_stage_packet_after_final_frontend_audit_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditCompleteResult"] == str(
            simulated_final_frontend_audit_complete_result_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditCompleteReport"] == str(
            simulated_final_frontend_audit_complete_report_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditInputsSummary"] == str(
            simulated_final_frontend_audit_inputs_summary_path
        )
        assert persisted["artifacts"]["simulatedFinalFrontendAuditExpectedStatuses"] == str(
            simulated_final_frontend_audit_expected_statuses_path
        )
        assert persisted["artifacts"]["ledgerAfterFinalFrontendAuditComplete"] == str(
            ledger_after_final_frontend_audit_complete_path
        )
        assert persisted["artifacts"]["browserStagePacketAfterFinalFrontendAuditComplete"] == str(
            browser_stage_packet_after_final_frontend_audit_complete_path
        )
        assert persisted["artifacts"]["simulatedCleanupProbesPartialResult"] == str(
            simulated_cleanup_probes_partial_result_path
        )
        assert persisted["artifacts"]["ledgerAfterCleanupProbesPartial"] == str(ledger_after_cleanup_probes_partial_path)
        assert persisted["artifacts"]["browserStagePacketAfterCleanupProbesPartialRecovery"] == str(
            browser_stage_packet_after_cleanup_probes_partial_recovery_path
        )
        assert persisted["artifacts"]["simulatedCleanupProbesCompleteResult"] == str(
            simulated_cleanup_probes_complete_result_path
        )
        assert persisted["artifacts"]["ledgerAfterCleanupProbesComplete"] == str(ledger_after_cleanup_probes_complete_path)
        assert persisted["artifacts"]["draftManifest"].endswith("/04-manifest-rehearsal/draft-manifest.json")
        assert persisted["artifacts"]["sourceInputRequirements"].endswith(
            "/04-manifest-rehearsal/source-input-requirements.json"
        )
        assert persisted["artifacts"]["manifestSummary"].endswith("/04-manifest-rehearsal/manifest-rehearsal-summary.json")
        assert handoff["commandsSuppressed"] is True
        assert "{realSiteKey}" in handoff["authorizationPackage"]["target"]
        assert launch_plan["routePlan"]["expectedStatusesAfterSample"]["/products/{slug}"] == 200
        assert browser_execution_plan["stages"][0]["stageId"] == "refresh_readonly_site_evidence"
        assert browser_execution_ledger["stageCounts"]["ready"] == 1
        assert browser_stage_packet["stageId"] == browser_execution_ledger["nextStageId"]
        assert simulated_stage_result["stageId"] == browser_stage_packet["stageId"]
        assert ledger_after_first_stage["entries"][0]["status"] == "completed"
        assert browser_stage_packet_after_first_stage["stageId"] == ledger_after_first_stage["nextStageId"]
        assert browser_stage_packet_after_first_stage["allowedActions"]
        assert simulated_create_site_result["stageId"] == browser_stage_packet_after_first_stage["stageId"]
        assert ledger_after_create_site["nextStageId"] == "setup_pages_inspection"
        assert browser_stage_packet_after_create_site["stageId"] == ledger_after_create_site["nextStageId"]
        assert browser_stage_packet_after_create_site["authorizationRequired"] is False
        assert simulated_setup_result["stageId"] == browser_stage_packet_after_create_site["stageId"]
        assert ledger_after_setup["nextStageId"] == "module_interface_capture"
        assert browser_stage_packet_after_setup["stageId"] == ledger_after_setup["nextStageId"]
        assert browser_stage_packet_after_setup["authorizationRequired"] is True
        assert browser_stage_module_capture_authorization_package["stageId"] == "module_interface_capture"
        assert browser_stage_module_capture_authorization_package["commandsSuppressed"] is True
        assert next_browser_action_handoff["stageId"] == "module_interface_capture"
        assert next_browser_action_handoff["preparedOnly"] is True
        assert next_browser_action_handoff["isUserAuthorization"] is False
        assert next_browser_action_handoff["remoteMutationsPerformed"] is False
        assert next_browser_action_handoff["commandsSuppressed"] is True
        assert next_browser_action_handoff["sourceFiles"]["authorizationPackage"] == str(
            browser_stage_module_capture_authorization_package_path
        )
        assert next_browser_action_handoff["action"]["authorizationAction"] == "create_product_probe"
        assert simulated_module_capture_partial_result["stageId"] == browser_stage_packet_after_setup["stageId"]
        assert simulated_module_capture_partial_result["status"] == "partial"
        assert ledger_after_module_capture_partial["nextStageId"] == ""
        assert next(
            entry
            for entry in ledger_after_module_capture_partial["entries"]
            if entry["stageId"] == "module_interface_capture"
        )["status"] == "partial"
        assert simulated_module_capture_stage_result["status"] == "captured"
        assert module_capture_coverage["complete"] is False
        assert module_capture_coverage["interfaceCoverageComplete"] is False
        assert module_capture_coverage["actionReplayContractsVerified"] is False
        assert module_capture_coverage["jsonReplayReady"] is False
        assert module_capture_coverage["coverageCounts"]["captured"] == 1
        assert module_capture_coverage["coverageCounts"]["pending"] > 0
        assert ledger_after_module_capture_coverage_sync["nextStageId"] == "module_interface_capture"
        synced_module_entry = next(
            entry
            for entry in ledger_after_module_capture_coverage_sync["entries"]
            if entry["stageId"] == "module_interface_capture"
        )
        assert synced_module_entry["status"] == "ready"
        assert any("posts:create" in action for action in synced_module_entry["nextAllowedActions"])
        assert module_capture_coverage_complete["complete"] is True
        assert module_capture_coverage_complete["interfaceCoverageComplete"] is True
        assert module_capture_coverage_complete["actionReplayContractsVerified"] is False
        assert module_capture_coverage_complete["jsonReplayReady"] is False
        assert module_capture_coverage_complete["coverageCounts"]["captured"] == module_capture_coverage_complete["coverageCounts"]["total"]
        assert ledger_after_module_capture_complete["nextStageId"] == "theme_page_route_launch"
        completed_module_entry = next(
            entry
            for entry in ledger_after_module_capture_complete["entries"]
            if entry["stageId"] == "module_interface_capture"
        )
        assert completed_module_entry["status"] == "completed"
        assert browser_stage_packet_after_module_capture_complete["stageId"] == "theme_page_route_launch"
        assert simulated_theme_launch_partial_result["stageId"] == browser_stage_packet_after_module_capture_complete["stageId"]
        assert simulated_theme_launch_partial_result["status"] == "partial"
        assert ledger_after_theme_launch_partial["nextStageId"] == ""
        partial_theme_entry = next(
            entry
            for entry in ledger_after_theme_launch_partial["entries"]
            if entry["stageId"] == "theme_page_route_launch"
        )
        assert partial_theme_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_theme_launch_partial["entries"]
            if entry["stageId"] == "static_frontend_audit" and entry["status"] == "ready"
        ]
        assert browser_stage_packet_after_theme_launch_partial_recovery["stageId"] == "theme_page_route_launch"
        assert browser_stage_packet_after_theme_launch_partial_recovery["recovery"] is True
        assert simulated_theme_launch_complete_result["stageId"] == browser_stage_packet_after_module_capture_complete["stageId"]
        assert simulated_theme_launch_complete_result["status"] == "completed"
        assert ledger_after_theme_launch_recovery_complete["nextStageId"] == "static_frontend_audit"
        assert ledger_after_theme_launch_complete["nextStageId"] == "static_frontend_audit"
        completed_theme_entry = next(
            entry
            for entry in ledger_after_theme_launch_complete["entries"]
            if entry["stageId"] == "theme_page_route_launch"
        )
        assert completed_theme_entry["status"] == "completed"
        assert browser_stage_packet_after_theme_launch_complete["stageId"] == "static_frontend_audit"
        assert browser_stage_packet_after_theme_launch_complete["authorizationRequired"] is False
        assert simulated_static_audit_partial_result["stageId"] == browser_stage_packet_after_theme_launch_complete["stageId"]
        assert simulated_static_audit_partial_result["status"] == "partial"
        assert ledger_after_static_audit_partial["nextStageId"] == ""
        partial_static_entry = next(
            entry
            for entry in ledger_after_static_audit_partial["entries"]
            if entry["stageId"] == "static_frontend_audit"
        )
        assert partial_static_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_static_audit_partial["entries"]
            if entry["stageId"] == "content_probe_create" and entry["status"] == "ready"
        ]
        assert simulated_static_audit_complete_result["stageId"] == browser_stage_packet_after_theme_launch_complete["stageId"]
        assert simulated_static_audit_complete_result["status"] == "completed"
        assert ledger_after_static_audit_complete["nextStageId"] == "content_probe_create"
        completed_static_entry = next(
            entry
            for entry in ledger_after_static_audit_complete["entries"]
            if entry["stageId"] == "static_frontend_audit"
        )
        assert completed_static_entry["status"] == "completed"
        assert browser_stage_packet_after_static_audit_complete["stageId"] == "content_probe_create"
        assert browser_stage_packet_after_static_audit_complete["authorizationRequired"] is True
        assert simulated_content_probe_partial_result["stageId"] == browser_stage_packet_after_static_audit_complete["stageId"]
        assert simulated_content_probe_partial_result["status"] == "partial"
        assert ledger_after_content_probe_partial["nextStageId"] == ""
        partial_probe_entry = next(
            entry
            for entry in ledger_after_content_probe_partial["entries"]
            if entry["stageId"] == "content_probe_create"
        )
        assert partial_probe_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_content_probe_partial["entries"]
            if entry["stageId"] == "save_request_capture" and entry["status"] == "ready"
        ]
        assert simulated_content_probe_complete_result["stageId"] == browser_stage_packet_after_static_audit_complete["stageId"]
        assert simulated_content_probe_complete_result["status"] == "completed"
        assert ledger_after_content_probe_complete["nextStageId"] == "save_request_capture"
        completed_probe_entry = next(
            entry
            for entry in ledger_after_content_probe_complete["entries"]
            if entry["stageId"] == "content_probe_create"
        )
        assert completed_probe_entry["status"] == "completed"
        assert browser_stage_packet_after_content_probe_complete["stageId"] == "save_request_capture"
        assert browser_stage_packet_after_content_probe_complete["authorizationRequired"] is True
        assert simulated_save_request_partial_result["stageId"] == browser_stage_packet_after_content_probe_complete["stageId"]
        assert simulated_save_request_partial_result["status"] == "partial"
        assert ledger_after_save_request_partial["nextStageId"] == ""
        partial_save_entry = next(
            entry
            for entry in ledger_after_save_request_partial["entries"]
            if entry["stageId"] == "save_request_capture"
        )
        assert partial_save_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_save_request_partial["entries"]
            if entry["stageId"] in {"publish_sample_verify", "manifest_schema_gate"} and entry["status"] == "ready"
        ]
        assert simulated_save_request_complete_result["stageId"] == browser_stage_packet_after_content_probe_complete["stageId"]
        assert simulated_save_request_complete_result["status"] == "completed"
        assert ledger_after_save_request_complete["nextStageId"] == "publish_sample_verify"
        completed_save_entry = next(
            entry
            for entry in ledger_after_save_request_complete["entries"]
            if entry["stageId"] == "save_request_capture"
        )
        assert completed_save_entry["status"] == "completed"
        manifest_gate_entry = next(
            entry
            for entry in ledger_after_save_request_complete["entries"]
            if entry["stageId"] == "manifest_schema_gate"
        )
        assert manifest_gate_entry["status"] == "ready"
        assert browser_stage_packet_after_save_request_complete["stageId"] == "publish_sample_verify"
        assert browser_stage_packet_after_save_request_complete["authorizationRequired"] is True
        assert simulated_publish_sample_partial_result["stageId"] == browser_stage_packet_after_save_request_complete["stageId"]
        assert simulated_publish_sample_partial_result["status"] == "partial"
        assert ledger_after_publish_sample_partial["nextStageId"] == "manifest_schema_gate"
        partial_publish_entry = next(
            entry
            for entry in ledger_after_publish_sample_partial["entries"]
            if entry["stageId"] == "publish_sample_verify"
        )
        assert partial_publish_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_publish_sample_partial["entries"]
            if entry["stageId"] == "batch_upload_publish" and entry["status"] == "ready"
        ]
        assert simulated_publish_sample_complete_result["stageId"] == browser_stage_packet_after_save_request_complete["stageId"]
        assert simulated_publish_sample_complete_result["status"] == "completed"
        assert ledger_after_publish_sample_complete["nextStageId"] == "manifest_schema_gate"
        completed_publish_entry = next(
            entry
            for entry in ledger_after_publish_sample_complete["entries"]
            if entry["stageId"] == "publish_sample_verify"
        )
        assert completed_publish_entry["status"] == "completed"
        batch_entry_after_publish = next(
            entry
            for entry in ledger_after_publish_sample_complete["entries"]
            if entry["stageId"] == "batch_upload_publish"
        )
        assert batch_entry_after_publish["status"] == "pending"
        assert browser_stage_packet_after_publish_sample_complete["stageId"] == "manifest_schema_gate"
        assert browser_stage_packet_after_publish_sample_complete["authorizationRequired"] is False
        assert simulated_manifest_gate_partial_result["stageId"] == browser_stage_packet_after_publish_sample_complete["stageId"]
        assert simulated_manifest_gate_partial_result["status"] == "partial"
        assert any(
            "source-input-requirements.json" in item
            for item in simulated_manifest_gate_partial_result["redactedEvidencePointers"]
        )
        assert ledger_after_manifest_gate_partial["nextStageId"] == ""
        partial_manifest_entry = next(
            entry
            for entry in ledger_after_manifest_gate_partial["entries"]
            if entry["stageId"] == "manifest_schema_gate"
        )
        assert partial_manifest_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_manifest_gate_partial["entries"]
            if entry["stageId"] == "batch_upload_publish" and entry["status"] == "ready"
        ]
        assert simulated_manifest_gate_complete_result["stageId"] == browser_stage_packet_after_publish_sample_complete["stageId"]
        assert simulated_manifest_gate_complete_result["status"] == "completed"
        assert any(
            "source-input-requirements.json" in item
            for item in simulated_manifest_gate_complete_result["redactedEvidencePointers"]
        )
        assert ledger_after_manifest_gate_complete["nextStageId"] == "batch_upload_publish"
        completed_manifest_entry = next(
            entry
            for entry in ledger_after_manifest_gate_complete["entries"]
            if entry["stageId"] == "manifest_schema_gate"
        )
        assert completed_manifest_entry["status"] == "completed"
        batch_entry_after_manifest = next(
            entry
            for entry in ledger_after_manifest_gate_complete["entries"]
            if entry["stageId"] == "batch_upload_publish"
        )
        assert batch_entry_after_manifest["status"] == "ready"
        assert browser_stage_packet_after_manifest_gate_complete["stageId"] == "batch_upload_publish"
        assert browser_stage_packet_after_manifest_gate_complete["authorizationRequired"] is True
        assert simulated_batch_upload_partial_result["stageId"] == browser_stage_packet_after_manifest_gate_complete["stageId"]
        assert simulated_batch_upload_partial_result["status"] == "partial"
        assert ledger_after_batch_upload_partial["nextStageId"] == ""
        partial_batch_entry = next(
            entry
            for entry in ledger_after_batch_upload_partial["entries"]
            if entry["stageId"] == "batch_upload_publish"
        )
        assert partial_batch_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_batch_upload_partial["entries"]
            if entry["stageId"] in {"forms_media_settings", "final_frontend_audit", "cleanup_probes"} and entry["status"] == "ready"
        ]
        assert simulated_batch_upload_complete_result["stageId"] == browser_stage_packet_after_manifest_gate_complete["stageId"]
        assert simulated_batch_upload_complete_result["status"] == "completed"
        assert ledger_after_batch_upload_complete["nextStageId"] == "forms_media_settings"
        completed_batch_entry = next(
            entry
            for entry in ledger_after_batch_upload_complete["entries"]
            if entry["stageId"] == "batch_upload_publish"
        )
        assert completed_batch_entry["status"] == "completed"
        forms_entry_after_batch = next(
            entry
            for entry in ledger_after_batch_upload_complete["entries"]
            if entry["stageId"] == "forms_media_settings"
        )
        assert forms_entry_after_batch["status"] == "ready"
        final_entry_after_batch = next(
            entry
            for entry in ledger_after_batch_upload_complete["entries"]
            if entry["stageId"] == "final_frontend_audit"
        )
        assert final_entry_after_batch["status"] == "pending"
        assert browser_stage_packet_after_batch_upload_complete["stageId"] == "forms_media_settings"
        assert browser_stage_packet_after_batch_upload_complete["authorizationRequired"] is True
        assert simulated_forms_media_settings_partial_result["stageId"] == browser_stage_packet_after_batch_upload_complete["stageId"]
        assert simulated_forms_media_settings_partial_result["status"] == "partial"
        assert ledger_after_forms_media_settings_partial["nextStageId"] == ""
        partial_forms_entry = next(
            entry
            for entry in ledger_after_forms_media_settings_partial["entries"]
            if entry["stageId"] == "forms_media_settings"
        )
        assert partial_forms_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_forms_media_settings_partial["entries"]
            if entry["stageId"] in {"final_frontend_audit", "cleanup_probes"} and entry["status"] == "ready"
        ]
        assert simulated_forms_media_settings_complete_result["stageId"] == browser_stage_packet_after_batch_upload_complete["stageId"]
        assert simulated_forms_media_settings_complete_result["status"] == "completed"
        assert ledger_after_forms_media_settings_complete["nextStageId"] == "final_frontend_audit"
        completed_forms_entry = next(
            entry
            for entry in ledger_after_forms_media_settings_complete["entries"]
            if entry["stageId"] == "forms_media_settings"
        )
        assert completed_forms_entry["status"] == "completed"
        final_entry_after_forms = next(
            entry
            for entry in ledger_after_forms_media_settings_complete["entries"]
            if entry["stageId"] == "final_frontend_audit"
        )
        assert final_entry_after_forms["status"] == "ready"
        cleanup_entry_after_forms = next(
            entry
            for entry in ledger_after_forms_media_settings_complete["entries"]
            if entry["stageId"] == "cleanup_probes"
        )
        assert cleanup_entry_after_forms["status"] == "pending"
        assert browser_stage_packet_after_forms_media_settings_complete["stageId"] == "final_frontend_audit"
        assert browser_stage_packet_after_forms_media_settings_complete["authorizationRequired"] is False
        assert simulated_final_frontend_audit_partial_result["stageId"] == browser_stage_packet_after_forms_media_settings_complete["stageId"]
        assert simulated_final_frontend_audit_partial_result["status"] == "partial"
        assert len(simulated_final_frontend_audit_partial_report) == 1
        assert any(
            "audit report route count" in issue for issue in simulated_final_frontend_audit_partial_result["blockingIssues"]
        )
        assert any(
            "missing expected route pattern" in issue
            for issue in simulated_final_frontend_audit_partial_result["blockingIssues"]
        )
        assert ledger_after_final_frontend_audit_partial["nextStageId"] == ""
        partial_final_entry = next(
            entry
            for entry in ledger_after_final_frontend_audit_partial["entries"]
            if entry["stageId"] == "final_frontend_audit"
        )
        assert partial_final_entry["status"] == "partial"
        assert not [
            entry
            for entry in ledger_after_final_frontend_audit_partial["entries"]
            if entry["stageId"] == "cleanup_probes" and entry["status"] == "ready"
        ]
        assert simulated_final_frontend_audit_complete_result["stageId"] == browser_stage_packet_after_forms_media_settings_complete["stageId"]
        assert simulated_final_frontend_audit_complete_result["status"] == "completed"
        assert simulated_final_frontend_audit_inputs_summary["staticRouteCount"] == 1
        assert simulated_final_frontend_audit_inputs_summary["detailRouteCount"] == 1
        assert len(simulated_final_frontend_audit_expected_statuses) == 2
        assert len(simulated_final_frontend_audit_complete_report) == 2
        assert any(
            "simulated-final-audit-inputs-summary" in pointer
            for pointer in simulated_final_frontend_audit_complete_result["redactedEvidencePointers"]
        )
        assert any(
            "simulated-final-expected-statuses" in pointer
            for pointer in simulated_final_frontend_audit_complete_result["redactedEvidencePointers"]
        )
        assert ledger_after_final_frontend_audit_complete["nextStageId"] == "cleanup_probes"
        completed_final_entry = next(
            entry
            for entry in ledger_after_final_frontend_audit_complete["entries"]
            if entry["stageId"] == "final_frontend_audit"
        )
        assert completed_final_entry["status"] == "completed"
        cleanup_entry_after_final = next(
            entry
            for entry in ledger_after_final_frontend_audit_complete["entries"]
            if entry["stageId"] == "cleanup_probes"
        )
        assert cleanup_entry_after_final["status"] == "ready"
        assert browser_stage_packet_after_final_frontend_audit_complete["stageId"] == "cleanup_probes"
        assert browser_stage_packet_after_final_frontend_audit_complete["authorizationRequired"] is True
        assert simulated_cleanup_probes_partial_result["stageId"] == browser_stage_packet_after_final_frontend_audit_complete["stageId"]
        assert simulated_cleanup_probes_partial_result["status"] == "partial"
        assert ledger_after_cleanup_probes_partial["nextStageId"] == ""
        partial_cleanup_entry = next(
            entry
            for entry in ledger_after_cleanup_probes_partial["entries"]
            if entry["stageId"] == "cleanup_probes"
        )
        assert partial_cleanup_entry["status"] == "partial"
        assert simulated_cleanup_probes_complete_result["stageId"] == browser_stage_packet_after_final_frontend_audit_complete["stageId"]
        assert simulated_cleanup_probes_complete_result["status"] == "completed"
        assert ledger_after_cleanup_probes_complete["nextStageId"] == ""
        completed_cleanup_entry = next(
            entry
            for entry in ledger_after_cleanup_probes_complete["entries"]
            if entry["stageId"] == "cleanup_probes"
        )
        assert completed_cleanup_entry["status"] == "completed"
        assert ledger_after_cleanup_probes_complete["stageCounts"]["completed"] == ledger_after_cleanup_probes_complete["stageCounts"]["total"]
        assert ledger_after_cleanup_probes_complete["stageCounts"]["ready"] == 0
        assert ledger_after_cleanup_probes_complete["stageCounts"]["pending"] == 0
        assert ledger_after_cleanup_probes_complete["stageCounts"]["blocked"] == 0


def test_rehearsal_stage_coverage_summary_compacts_full_launch_path() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "old-site-a"
        site_key_evidence = "old-site-a from backend url route https://workspace.laicms.com/old-site-a/dashboard"
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        summary = run_full_rehearsal.run_rehearsal(Args())
        coverage = build_rehearsal_stage_coverage_summary(
            Path(tmp) / "rehearsal-summary.json",
            generated_at=RECENT_PREFLIGHT_AT,
        )
        errors = validate_rehearsal_stage_coverage_summary(coverage)

    assert errors == [], errors
    assert summary["finalLedgerExhaustion"]["allStagesCompleted"] is True
    assert coverage["stageCount"] == 14
    assert coverage["authorizationStageCount"] == 9
    assert "batch_upload_publish" in coverage["authorizationRequiredStages"]
    assert "final_frontend_audit" in coverage["verificationOnlyStages"]
    assert coverage["sourceInputRequirements"]["requirementsGenerated"] is True
    assert coverage["sourceInputRequirements"]["requirementsBlocked"] is True
    assert coverage["finalLedgerExhaustion"]["packetBuildRejected"] is True
    assert "not live LAICMS" in coverage["completionMeaning"]
    module_stage = next(stage for stage in coverage["stages"] if stage["stageId"] == "module_interface_capture")
    assert module_stage["completionCovered"] is True
    assert module_stage["nextStageAfterCompletion"] == "theme_page_route_launch"


def test_full_rehearsal_validator_cross_checks_top_level_summary() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is True
        assert validation["capturePlanGateCoverageSafety"]["ok"] is True
        assert validation["browserRunbookSummarySafety"]["ok"] is True
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["capturePlanGateCoverage"]["stageCount"] == 10
        assert summary["browserRunbookSummary"]["nextStageId"] == "refresh_readonly_site_evidence"
        assert "upload_media" in summary["capturePlanGateCoverage"]["ungatedAllowedActions"]
        assert (Path(tmp) / "browser-runbook-summary.json").exists()
        assert (Path(tmp) / "capture-plan-gate-coverage.json").exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["launchPlan"]["proofGateCount"] = 999
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert any("proofGateCount" in issue for issue in validation["issues"])


def test_full_rehearsal_validator_rejects_browser_runbook_summary_drift() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        runbook_path = Path(tmp) / "browser-runbook-summary.json"
        runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
        runbook["nextRealBrowserStep"]["stageId"] = "create_site_submit"
        runbook_path.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert validation["browserRunbookSummarySafety"]["ok"] is False
        assert any("browser runbook summary" in issue and "stageId mismatch" in issue for issue in validation["issues"])


def test_full_rehearsal_validator_rejects_browser_runbook_evidence_bundle_drift() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        runbook_path = Path(tmp) / "browser-runbook-summary.json"
        runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
        runbook["nextRealBrowserStep"]["evidenceManifest"] = str(Path(tmp) / "wrong-evidence-manifest.json")
        runbook_path.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert validation["browserRunbookSummarySafety"]["ok"] is False
        assert any("evidenceManifest mismatch" in issue for issue in validation["issues"])


def test_full_rehearsal_validator_rejects_packet_command_path_drift() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        packet_path = Path(tmp) / "next-browser-stage-packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["ledgerUpdate"]["commandTemplate"] = (
            "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
            "--ledger ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json "
            "--packet ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json "
            "--result-json /tmp/allincms-stage-result.json "
            "--output ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.updated.json"
        )
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert any("commandTemplate missing ledger path" in issue for issue in validation["issues"])


def test_browser_runbook_summary_blocks_simulation_commands_before_real_evidence() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary = build_runbook_summary(Path(tmp) / "rehearsal-summary.json")
        assert summary["sourceRehearsal"]["valid"] is True
        assert summary["sourceRehearsal"]["commandsSuppressed"] is True
        assert summary["nextRealBrowserStep"]["mode"] == "prepare_real_browser_stage"
        assert summary["nextRealBrowserStep"]["stageId"] == "refresh_readonly_site_evidence"
        assert summary["nextRealBrowserStep"]["authorizationRequired"] is False
        assert summary["nextRealBrowserStep"]["evidenceBundle"] == str(Path(tmp) / "next-browser-stage-evidence-bundle")
        assert summary["nextRealBrowserStep"]["evidenceManifest"] == str(
            Path(tmp) / "next-browser-stage-evidence-bundle" / "evidence-manifest.json"
        )
        assert summary["requiredLocalArtifacts"]["nextBrowserStageEvidenceBundle"] == str(
            Path(tmp) / "next-browser-stage-evidence-bundle"
        )
        assert summary["requiredLocalArtifacts"]["nextBrowserActionHandoff"] == str(
            Path(tmp) / "next-browser-action-handoff.json"
        )
        assert summary["requiredLocalArtifacts"]["browserStageModuleCaptureAuthorizationPackage"] == str(
            Path(tmp) / "browser-stage-module-interface-authorization-package.json"
        )
        operator_handoff = summary["operatorHandoff"]
        assert operator_handoff["status"] == "ready"
        assert operator_handoff["notAuthorization"] is True
        assert operator_handoff["packetPath"] == str(Path(tmp) / "next-browser-stage-packet.json")
        assert operator_handoff["ledgerPath"] == str(Path(tmp) / "browser-execution-ledger.json")
        assert operator_handoff["nextBrowserActionHandoffPath"] == str(Path(tmp) / "next-browser-action-handoff.json")
        assert operator_handoff["browserStageModuleCaptureAuthorizationPackagePath"] == str(
            Path(tmp) / "browser-stage-module-interface-authorization-package.json"
        )
        assert operator_handoff["stageResultTemplatePath"] == str(
            Path(tmp) / "next-browser-stage-evidence-bundle" / "stage-result-template.json"
        )
        assert operator_handoff["bundleStageResultDraftPath"] == str(
            Path(tmp) / "next-browser-stage-evidence-bundle" / "stage-result.json"
        )
        assert operator_handoff["ledgerExpectedStageResultPath"] == str(
            Path(tmp) / "next-browser-stage-packet-stage-result.json"
        )
        assert operator_handoff["stageResultOutputPath"] == operator_handoff["ledgerExpectedStageResultPath"]
        assert operator_handoff["ledgerExpectedStageResultPath"] in operator_handoff["ledgerApplyCommand"]
        assert operator_handoff["requiredProof"]
        assert operator_handoff["authorizationPreparation"]["required"] is False
        assert "not action-time user authorization" in operator_handoff["authorizationPreparation"]["note"]
        assert "not user authorization" in operator_handoff["warning"]
        assert "fresh /sites list" in summary["requiredRealEvidenceBeforeMutation"][0]
        assert summary["coverage"]["initialLedgerNextStageId"] == "refresh_readonly_site_evidence"
        assert "do not run suppressed command templates against LAICMS" in summary["stopConditions"]


def test_browser_runbook_summary_reports_blocked_when_rehearsal_invalid() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        raw_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        raw_summary["browserStagePacket"]["stageId"] = "wrong_stage"
        summary_path.write_text(json.dumps(raw_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary = build_runbook_summary(summary_path)
        assert summary["sourceRehearsal"]["valid"] is False
        assert summary["nextRealBrowserStep"]["mode"] == "blocked"
        assert summary["operatorHandoff"]["status"] == "blocked"
        assert summary["sourceRehearsal"]["issues"]


def test_browser_runbook_summary_extracts_ledger_expected_stage_result_path() -> None:
    command = (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py "
        "--ledger /tmp/run/browser-execution-ledger.json "
        "--packet /tmp/run/next-browser-stage-packet.json "
        "--result-json /tmp/run/current-stage-result.json "
        "--output /tmp/run/browser-execution-ledger.after-stage.json"
    )
    assert ledger_expected_stage_result_path("/tmp/run/next-browser-stage-packet.json", command) == (
        "/tmp/run/current-stage-result.json"
    )
    assert ledger_expected_stage_result_path("/tmp/run/next-browser-stage-packet.json", "") == (
        "/tmp/run/next-browser-stage-packet-stage-result.json"
    )


def test_standalone_browser_runbook_summary_validator_accepts_generated_runbook() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        runbook_path = Path(tmp) / "browser-runbook-summary.json"
        runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
        validation = validate_browser_runbook_summary(runbook, runbook_path)
        assert validation["ok"] is True
        assert validation["nextStageId"] == "refresh_readonly_site_evidence"
        assert validation["nextBrowserActionHandoff"] == str(Path(tmp) / "next-browser-action-handoff.json")


def test_standalone_browser_runbook_summary_validator_rejects_handoff_path_drift() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        runbook_path = Path(tmp) / "browser-runbook-summary.json"
        runbook = json.loads(runbook_path.read_text(encoding="utf-8"))
        runbook["requiredLocalArtifacts"]["nextBrowserActionHandoff"] = str(Path(tmp) / "wrong-handoff.json")
        runbook["operatorHandoff"]["nextBrowserActionHandoffPath"] = str(Path(tmp) / "wrong-handoff.json")
        validation = validate_browser_runbook_summary(runbook, runbook_path)
        assert validation["ok"] is False
        assert any("nextBrowserActionHandoff" in issue for issue in validation["issues"])


def test_full_rehearsal_validator_rejects_capture_plan_gate_coverage_drift() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        coverage_path = Path(tmp) / "capture-plan-gate-coverage.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        coverage["coveredActions"] = []
        coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert any("capture-plan-gate-coverage.json" in issue for issue in validation["issues"])


def test_full_rehearsal_validator_rejects_capture_plan_unknown_action() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        simulated_created_site_key = "simsite01"
        content_type = "products"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        create_authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        simulated_content_id = "codex-probe-id"
        simulated_slug = "codex-probe-delete-me"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""
        module = ""
        action = ""
        allow_command_output = False

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        run_full_rehearsal.run_rehearsal(Args())
        summary_path = Path(tmp) / "rehearsal-summary.json"
        plan_path = Path(tmp) / "full-e2e" / "03-module-interface-plan" / "module-capture-plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["stages"][0]["authorizationAction"] = "launch_everything"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation = validate_rehearsal(summary_path)
        assert validation["ok"] is False
        assert any("unknown authorizationAction launch_everything" in issue for issue in validation["issues"])


def test_site_creation_chain_simulation_rejects_generic_authorization() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = (
            "mysite01 from backend url route https://workspace.laicms.com/mysite01/dashboard;"
            "mysite02 from backend url route https://workspace.laicms.com/mysite02/dashboard"
        )
        empty_site_list_evidence = "verified empty /sites list"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        simulated_created_site_key = "simsite01"
        content_type = "products"
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        include_simulated_static_launch = False
        authorization_source = "continue"
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        try:
            simulate_site_creation_chain.run_simulation(Args())
        except ValueError as exc:
            assert "too generic" in str(exc), exc
        else:
            raise AssertionError("generic authorization was accepted by simulation chain")


def test_site_creation_chain_simulation_requires_site_key_evidence() -> None:
    class Args:
        no_existing_sites = False
        existing_site_keys = "mysite01,mysite02"
        site_key_evidence = ""
        empty_site_list_evidence = "verified empty /sites list"
        observed_create_fields = simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS
        simulated_created_site_key = "simsite01"
        content_type = "products"
        list_columns = simulate_site_creation_chain.DEFAULT_LIST_COLUMNS
        edit_fields = simulate_site_creation_chain.DEFAULT_EDIT_FIELDS
        include_simulated_static_launch = False
        authorization_source = (
            "current user explicitly authorizes create site at https://workspace.laicms.com/sites "
            "for local simulation only"
        )
        max_age_minutes = 30
        sedimentation = "none"
        closeout_note = "no reusable skill update needed after checking"
        changed_files = ""

    with tempfile.TemporaryDirectory() as tmp:
        Args.output_dir = tmp
        try:
            simulate_site_creation_chain.run_simulation(Args())
        except ValueError as exc:
            assert "--site-key-evidence" in str(exc), exc
        else:
            raise AssertionError("simulation chain accepted existing site keys without site key evidence")


def main() -> int:
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if not name.startswith("test_"):
            continue
        fn = getattr(current_module, name)
        if not callable(fn):
            continue
        signature = inspect.signature(fn)
        if signature.parameters:
            continue
        fn()
    print("validate_run_evidence regression tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
