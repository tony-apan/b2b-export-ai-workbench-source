#!/usr/bin/env python3
"""Summarize a full rehearsal into compact stage-coverage evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from validate_full_rehearsal import validate_rehearsal


SIMULATION_KEYS = {
    "refresh_readonly_site_evidence": ("stageResultSimulation", None),
    "create_site_submit": ("createSiteStageSimulation", None),
    "setup_pages_inspection": ("setupStageSimulation", None),
    "module_interface_capture": ("moduleCapturePartialSimulation", "moduleCaptureCompletionSimulation"),
    "theme_page_route_launch": ("themeLaunchPartialSimulation", "themeLaunchCompletionSimulation"),
    "static_frontend_audit": ("staticAuditPartialSimulation", "staticAuditCompletionSimulation"),
    "content_probe_create": ("contentProbePartialSimulation", "contentProbeCompletionSimulation"),
    "save_request_capture": ("saveRequestPartialSimulation", "saveRequestCompletionSimulation"),
    "publish_sample_verify": ("publishSamplePartialSimulation", "publishSampleCompletionSimulation"),
    "manifest_schema_gate": ("manifestGatePartialSimulation", "manifestGateCompletionSimulation"),
    "batch_upload_publish": ("batchUploadPartialSimulation", "batchUploadCompletionSimulation"),
    "forms_media_settings": ("formsMediaSettingsPartialSimulation", "formsMediaSettingsCompletionSimulation"),
    "final_frontend_audit": ("finalFrontendAuditPartialSimulation", "finalFrontendAuditCompletionSimulation"),
    "cleanup_probes": ("cleanupProbesPartialSimulation", "cleanupProbesCompletionSimulation"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def stage_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = list_value(plan, "stages")
    result: dict[str, dict[str, Any]] = {}
    for stage in stages:
        if isinstance(stage, dict) and isinstance(stage.get("stageId"), str):
            result[stage["stageId"]] = stage
    return result


def first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def simulation_status(summary: dict[str, Any], stage_id: str) -> dict[str, Any]:
    partial_key, complete_key = SIMULATION_KEYS.get(stage_id, ("", None))
    partial = dict_value(summary, partial_key) if partial_key else {}
    complete = dict_value(summary, complete_key) if complete_key else {}
    completed = complete if complete else partial
    if stage_id == "module_interface_capture":
        if complete.get("complete") is True and not complete.get("status"):
            complete = {
                **complete,
                "status": "completed",
                "nextStageIdAfterApply": complete.get("nextStageIdAfterSync", ""),
            }
            completed = complete
        elif not complete:
            coverage_complete = dict_value(summary, "moduleCaptureCoverageComplete")
            ledger_complete = dict_value(summary, "ledgerAfterModuleCaptureComplete")
            if coverage_complete.get("complete") is True and ledger_complete.get("nextStageId") == "theme_page_route_launch":
                complete = {
                    "status": "completed",
                    "nextStageIdAfterApply": "theme_page_route_launch",
                    "stageCountsAfterApply": ledger_complete.get("stageCounts", {}),
                }
                completed = complete
    status = first_non_empty(completed.get("status"), partial.get("status"))
    next_stage = first_non_empty(completed.get("nextStageIdAfterApply"), completed.get("nextPacketStageId"))
    partial_status = str(partial.get("status", "")) if partial else ""
    return {
        "partialCovered": bool(partial) and partial_status == "partial",
        "completionCovered": bool(completed) and status == "completed",
        "completedFromRecoveryPacket": completed.get("completedFromRecoveryPacket") is True,
        "nextStageAfterCompletion": next_stage,
        "stageCountsAfterCompletion": completed.get("stageCountsAfterApply", {}),
    }


def source_blockers(summary: dict[str, Any]) -> dict[str, Any]:
    manifest = dict_value(summary, "manifestRehearsal")
    full = dict_value(summary, "fullE2EValidation")
    count = manifest.get("sourceInputRequirementsBlockedUntilCount")
    if not isinstance(count, int):
        count = full.get("sourceInputRequirementsBlockedUntilCount", 0)
    return {
        "requirementsGenerated": manifest.get("sourceInputRequirementsGenerated") is True
        or full.get("sourceInputRequirementsGenerated") is True,
        "requirementsBlocked": manifest.get("sourceInputRequirementsBlocked") is True
        or full.get("sourceInputRequirementsBlocked") is True,
        "blockedUntilCount": count if isinstance(count, int) else 0,
    }


def build_summary(rehearsal_path: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    rehearsal = load_json(rehearsal_path)
    validation = validate_rehearsal(rehearsal_path)
    plan = dict_value(rehearsal, "browserExecutionPlan")
    if not isinstance(plan.get("stages"), list):
        plan_path = rehearsal.get("browserExecutionPlanPath")
        if not isinstance(plan_path, str) or not plan_path:
            artifacts = dict_value(rehearsal, "artifacts")
            plan_path = artifacts.get("browserExecutionPlan") if isinstance(artifacts.get("browserExecutionPlan"), str) else ""
        if plan_path:
            plan = load_json(Path(plan_path))
    stages = stage_map(plan)
    stage_rows: list[dict[str, Any]] = []
    for stage_id, stage in stages.items():
        sim = simulation_status(rehearsal, stage_id)
        stage_rows.append(
            {
                "stageId": stage_id,
                "phase": stage.get("phase", ""),
                "mode": stage.get("mode", ""),
                "authorizationRequired": stage.get("authorizationRequired") is True,
                "remoteMutationExpectation": stage.get("remoteMutationExpectation", ""),
                "stopAfter": stage.get("stopAfter", ""),
                "requiredProofCount": len(list_value(stage, "requiredProof")),
                "forbiddenActionCount": len(list_value(stage, "forbiddenActions")),
                **sim,
            }
        )
    authorization_required = [stage["stageId"] for stage in stage_rows if stage["authorizationRequired"]]
    mutation_must = [
        stage["stageId"]
        for stage in stage_rows
        if stage.get("remoteMutationExpectation") == "must"
    ]
    verification_only = [
        stage["stageId"]
        for stage in stage_rows
        if stage.get("remoteMutationExpectation") == "must_not"
    ]
    runbook = dict_value(rehearsal, "browserRunbookSummary")
    if not isinstance(runbook.get("nextRealBrowserStep"), dict):
        runbook_path = rehearsal.get("browserRunbookSummaryPath")
        if not isinstance(runbook_path, str) or not runbook_path:
            artifacts = dict_value(rehearsal, "artifacts")
            runbook_path = artifacts.get("browserRunbookSummary") if isinstance(artifacts.get("browserRunbookSummary"), str) else ""
        if runbook_path:
            runbook = load_json(Path(runbook_path))
    next_step = dict_value(runbook, "nextRealBrowserStep")
    final_exhaustion = dict_value(rehearsal, "finalLedgerExhaustion")
    source = source_blockers(rehearsal)
    return {
        "kind": "allincms_rehearsal_stage_coverage_summary",
        "generatedAt": generated_at or now_iso(),
        "sourceSummary": str(rehearsal_path),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "validationOk": validation.get("ok") is True,
        "validationIssues": validation.get("issues", []),
        "stageCount": len(stage_rows),
        "authorizationStageCount": len(authorization_required),
        "authorizationRequiredStages": authorization_required,
        "remoteMutationMustStages": mutation_must,
        "verificationOnlyStages": verification_only,
        "sourceInputRequirements": source,
        "nextRealBrowserStep": {
            "stageId": next_step.get("stageId", ""),
            "mode": next_step.get("mode", ""),
            "authorizationRequired": next_step.get("authorizationRequired") is True,
            "reason": next_step.get("reason", ""),
        },
        "finalLedgerExhaustion": {
            "allStagesCompleted": final_exhaustion.get("allStagesCompleted") is True,
            "nextStageId": final_exhaustion.get("nextStageId", ""),
            "packetBuildRejected": final_exhaustion.get("packetBuildRejected") is True,
            "rejectionReason": final_exhaustion.get("rejectionReason", ""),
        },
        "stages": stage_rows,
        "completionMeaning": (
            "This proves local workflow coverage only. It is not live LAICMS site creation, "
            "content upload, publish, media upload, or cleanup proof."
        ),
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if summary.get("kind") != "allincms_rehearsal_stage_coverage_summary":
        issues.append("kind must be allincms_rehearsal_stage_coverage_summary")
    if summary.get("localOnly") is not True:
        issues.append("localOnly must be true")
    if summary.get("remoteMutationsPerformed") is not False:
        issues.append("remoteMutationsPerformed must be false")
    if summary.get("validationOk") is not True:
        issues.append("source rehearsal validation must be ok")
    stages = summary.get("stages")
    if not isinstance(stages, list) or len(stages) < 14:
        issues.append("stages must include the full 14-stage browser execution plan")
    else:
        stage_ids = {stage.get("stageId") for stage in stages if isinstance(stage, dict)}
        for required in SIMULATION_KEYS:
            if required not in stage_ids:
                issues.append(f"missing stage {required}")
    if isinstance(stages, list) and summary.get("stageCount") != len(stages):
        issues.append("stageCount must match stages length")
    source = summary.get("sourceInputRequirements")
    if not isinstance(source, dict) or source.get("requirementsGenerated") is not True:
        issues.append("sourceInputRequirements must report generated requirements")
    if not isinstance(summary.get("completionMeaning"), str) or "not live LAICMS" not in summary["completionMeaning"]:
        issues.append("completionMeaning must state this is not live LAICMS proof")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize AllinCMS full-rehearsal stage coverage.")
    parser.add_argument("rehearsal_summary_json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = build_summary(Path(args.rehearsal_summary_json))
        issues = validate_summary(summary)
        if issues:
            raise ValueError("stage coverage summary validation failed:\n" + "\n".join(f"- {issue}" for issue in issues))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote stage coverage summary: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
