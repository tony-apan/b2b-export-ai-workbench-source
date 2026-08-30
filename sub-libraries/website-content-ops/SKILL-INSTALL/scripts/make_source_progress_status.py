#!/usr/bin/env python3
"""Summarize in-progress source-file-to-site status from current local artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: {label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def load_optional_json(path: str, label: str) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        return load_json(path, label)
    except SystemExit:
        return None


def status_to_progress(status: str) -> str:
    if status == "passed":
        return "proven"
    if status in {"blocked", "missing", "failed"}:
        return "blocked"
    return "not_started"


def stage(status: dict[str, Any], stage_id: str) -> dict[str, Any]:
    stages = status.get("stages")
    if not isinstance(stages, dict):
        return {}
    value = stages.get(stage_id)
    return value if isinstance(value, dict) else {}


def stage_item(status: dict[str, Any], stage_id: str, label: str) -> dict[str, Any]:
    item = stage(status, stage_id)
    stage_status = str(item.get("status") or "")
    evidence = str(item.get("evidence") or "")
    blockers = item.get("blockers") if isinstance(item.get("blockers"), list) else []
    return {
        "id": stage_id,
        "label": label,
        "status": status_to_progress(stage_status),
        "stageStatus": stage_status,
        "evidence": [evidence] if evidence else [],
        "blockers": [str(blocker) for blocker in blockers if str(blocker).strip()],
        "nextAction": str(item.get("nextAction") or ""),
    }


def first_blocked_item(items: list[dict[str, Any]]) -> dict[str, Any]:
    for item in items:
        if item.get("status") != "proven":
            return item
    return {}


def batch_readiness(status: dict[str, Any]) -> dict[str, Any]:
    sample = stage(status, "sample_upload")
    batch = stage(status, "batch_upload")
    sample_passed = sample.get("status") == "passed"
    batch_passed = batch.get("status") == "passed"
    return {
        "readyForBatchUpload": sample_passed and not batch_passed,
        "batchAlreadyApplied": batch_passed,
        "reason": (
            "sample_upload passed; batch_upload is the current remaining upload stage"
            if sample_passed and not batch_passed
            else "batch_upload already passed"
            if batch_passed
            else "batch upload remains blocked until schema manifests and sample evidence pass"
        ),
    }


def final_acceptance_accepted(report: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(report, dict)
        and report.get("kind") == "allincms_source_run_acceptance_validation"
        and report.get("accepted") is True
        and report.get("complete") is True
    )


def gate_for_status_stage(current_stage: str, batch: dict[str, Any]) -> dict[str, Any]:
    if current_stage in {"", "complete"}:
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": False,
            "requiresActionTimeAuthorization": False,
            "nextGate": "final_acceptance" if current_stage == "complete" else "inspect_source_status",
            "reason": (
                "source execution status is complete; run final source-run acceptance before claiming the objective"
                if current_stage == "complete"
                else "source execution status does not expose a current stage"
            ),
        }
    read_only_stages = {"create_site_handoff", "pages_site_info_handoff", "taxonomy_execution_handoff", "schema_capture_handoff"}
    mutation_stages = {
        "created_site_binding",
        "pages_site_info_execution",
        "taxonomy_execution",
        "schema_manifests",
        "sample_upload",
        "batch_upload",
        "forms_media_settings",
        "launch_acceptance",
    }
    if current_stage in read_only_stages:
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": True,
            "requiresActionTimeAuthorization": False,
            "nextGate": "read_only_browser_preflight_or_handoff_refresh",
            "reason": "current stage prepares or refreshes handoff evidence; collect/read current backend state before any mutation authorization",
        }
    if current_stage in mutation_stages:
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": False,
            "requiresActionTimeAuthorization": True,
            "nextGate": "action_time_authorization_and_pre_mutation_gate",
            "reason": (
                "batch upload is ready only after sample proof; still require action-time authorization and pre-mutation gate"
                if current_stage == "batch_upload" and batch.get("readyForBatchUpload") is True
                else "stage may involve remote changes; prepare exact action authorization and run the matching gate before browser mutation"
            ),
        }
    return {
        "remoteMutationAllowed": False,
        "requiresUserContentConfirmation": current_stage == "confirmation",
        "requiresReadOnlyBrowserEvidence": False,
        "requiresActionTimeAuthorization": False,
        "nextGate": "local_preparation",
        "reason": "continue local preparation; no remote mutation is authorized by this progress report",
    }


def gate_for_rehearsal(summary: dict[str, Any]) -> dict[str, Any]:
    ready_stage = str(summary.get("readyForBrowserStage") or "")
    review_ready = summary.get("reviewReady") is True
    confirmation_prepared = summary.get("confirmationPrepared") is True
    if ready_stage == "waiting_for_user_content_confirmation":
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": True,
            "requiresReadOnlyBrowserEvidence": False,
            "requiresActionTimeAuthorization": False,
            "nextGate": "user_content_confirmation",
            "reason": "review packet is ready; user must confirm content intent before create/select-site preparation",
        }
    if ready_stage in {"needs_create_site_preflight", "ready_for_existing_site_readonly_refresh"}:
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": True,
            "requiresActionTimeAuthorization": False,
            "nextGate": "read_only_browser_preflight",
            "reason": "collect current /sites or existing-site read-only evidence before preparing any mutation",
        }
    if ready_stage == "create_site_handoff_ready":
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": False,
            "requiresActionTimeAuthorization": True,
            "nextGate": "action_time_create_site_authorization",
            "reason": "create-site handoff/runbook exists; submit only after exact action-time authorization and pre-mutation gate",
        }
    if ready_stage.startswith("blocked") or ready_stage in {"needs_source_wiki_refinement", ""}:
        return {
            "remoteMutationAllowed": False,
            "requiresUserContentConfirmation": False,
            "requiresReadOnlyBrowserEvidence": False,
            "requiresActionTimeAuthorization": False,
            "nextGate": "local_refinement",
            "reason": "source package is not ready for browser work; refine local source/wiki/package artifacts first",
        }
    return {
        "remoteMutationAllowed": False,
        "requiresUserContentConfirmation": review_ready and not confirmation_prepared,
        "requiresReadOnlyBrowserEvidence": False,
        "requiresActionTimeAuthorization": False,
        "nextGate": "inspect_rehearsal_summary",
        "reason": "progress report is local-only; inspect the rehearsal summary before any browser action",
    }


def status_progress(
    status: dict[str, Any],
    *,
    source_path: str,
    objective: str,
    final_acceptance: dict[str, Any] | None = None,
    final_acceptance_path: str = "",
) -> dict[str, Any]:
    if status.get("kind") != "allincms_source_execution_status":
        raise SystemExit("ERROR: source status kind must be allincms_source_execution_status")
    items = [
        stage_item(status, "source_package", "Source package exists and content-goal coverage is valid"),
        stage_item(status, "review_packet", "Review packet is ready for user confirmation"),
        stage_item(status, "confirmation", "User content-intent confirmation is recorded"),
        stage_item(status, "artifact_export", "Confirmed draft artifacts are exported"),
        stage_item(status, "created_site_binding", "Created or selected site is bound to source artifacts"),
        stage_item(status, "pages_site_info_execution", "Pages, navigation, routes, and site-info proof is applied"),
        stage_item(status, "taxonomy_execution", "Taxonomy is created, mapped, or not required"),
        stage_item(status, "schema_manifests", "Products/posts save schemas are captured and manifests are schema-verified"),
        stage_item(status, "sample_upload", "One products/posts sample is uploaded, published, and frontend-verified"),
        stage_item(status, "batch_upload", "Products/posts batch upload and publish proof is applied"),
        stage_item(status, "forms_media_settings", "Forms, media, domains, tracking, and settings are handled or deferred"),
        stage_item(status, "launch_acceptance", "Launch acceptance proof is applied"),
    ]
    blocked = first_blocked_item(items)
    source_status_complete = status.get("complete") is True and not blocked
    acceptance_accepted = final_acceptance_accepted(final_acceptance)
    complete = source_status_complete and acceptance_accepted
    batch = batch_readiness(status)
    return {
        "kind": "allincms_source_progress_status",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceArtifact": source_path,
        "sourceArtifactKind": "allincms_source_execution_status",
        "objective": objective,
        "complete": complete,
        "sourceStatusComplete": source_status_complete,
        "finalAcceptance": final_acceptance_path,
        "finalAcceptanceAccepted": acceptance_accepted,
        "currentStage": str(status.get("currentStage") or ""),
        "passedCount": status.get("passedCount"),
        "stageCount": status.get("stageCount"),
        "nextBlockingId": str(blocked.get("id") or ""),
        "nextBlockingLabel": str(blocked.get("label") or ""),
        "nextAction": str(status.get("nextAction") or blocked.get("nextAction") or ""),
        "batchReadiness": batch,
        "nextActionGate": gate_for_status_stage(str(status.get("currentStage") or ""), batch),
        "contentTypeCoverage": status.get("contentTypeCoverage") if isinstance(status.get("contentTypeCoverage"), dict) else {},
        "contentCountCoverage": status.get("contentCountCoverage") if isinstance(status.get("contentCountCoverage"), dict) else {},
        "progress": items,
        "adversarialChecks": [
            "This progress status reads existing local artifacts only; it does not rebuild source status, authorize browser actions, or prove final launch.",
            "Do not claim the full objective complete unless complete=true; sourceStatusComplete without finalAcceptanceAccepted is not enough.",
            "Do not batch upload unless batchReadiness.readyForBatchUpload=true, nextActionGate.requiresActionTimeAuthorization=true, and the action-time batch authorization/gate also passes.",
        ],
    }


def rehearsal_progress(summary: dict[str, Any], *, source_path: str, objective: str) -> dict[str, Any]:
    if summary.get("kind") != "allincms_source_file_rehearsal_summary":
        raise SystemExit("ERROR: rehearsal summary kind must be allincms_source_file_rehearsal_summary")
    audit = summary.get("objectiveAudit") if isinstance(summary.get("objectiveAudit"), dict) else {}
    checks = audit.get("checks") if isinstance(audit.get("checks"), list) else []
    items: list[dict[str, Any]] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            continue
        evidence = check.get("evidence") if isinstance(check.get("evidence"), list) else []
        items.append(
            {
                "id": f"objective_check_{index + 1}",
                "label": str(check.get("requirement") or ""),
                "status": str(check.get("status") or "not_started"),
                "evidence": [str(item) for item in evidence if str(item).strip()],
                "blockers": [str(check.get("note"))] if check.get("note") else [],
                "readyForBrowserStage": str(check.get("readyForBrowserStage") or ""),
            }
        )
    next_blocking = str(audit.get("nextBlockingRequirement") or summary.get("confirmationBrief", {}).get("nextBlockingRequirement") or "")
    source_status_path = ""
    artifacts = summary.get("artifacts")
    if isinstance(artifacts, dict):
        value = artifacts.get("sourceExecutionStatus")
        source_status_path = value if isinstance(value, str) else ""
    status = load_optional_json(source_status_path, "source execution status")
    status_stage = str(status.get("currentStage") or "") if isinstance(status, dict) else ""
    return {
        "kind": "allincms_source_progress_status",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceArtifact": source_path,
        "sourceArtifactKind": "allincms_source_file_rehearsal_summary",
        "objective": objective,
        "complete": False,
        "reviewReady": summary.get("reviewReady") is True,
        "confirmationPrepared": summary.get("confirmationPrepared") is True,
        "readyForBrowserStage": str(summary.get("readyForBrowserStage") or ""),
        "sourceExecutionStatus": source_status_path,
        "sourceExecutionCurrentStage": status_stage,
        "nextBlockingId": next_blocking,
        "nextBlockingLabel": next_blocking,
        "nextAction": str(summary.get("nextAction") or ""),
        "batchReadiness": {
            "readyForBatchUpload": False,
            "batchAlreadyApplied": False,
            "reason": "source-file rehearsal has not reached schema sample proof; remote batch upload is not ready",
        },
        "nextActionGate": gate_for_rehearsal(summary),
        "progress": items,
        "adversarialChecks": [
            "A rehearsal summary is local-only preparation; it cannot prove remote site creation, schema capture, upload, publish, or launch.",
            "User content confirmation is not remote mutation authorization.",
            "If readyForBrowserStage is a preflight boundary, collect read-only evidence before preparing or executing any mutation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize current source-file-to-site progress from existing local artifacts.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rehearsal-summary", default="")
    group.add_argument("--source-status", default="")
    parser.add_argument("--objective", default="")
    parser.add_argument("--final-acceptance", default="", help="Optional validate_source_run_acceptance.py report.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-if-batch-not-ready", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    ensure_output_outside_skill(output)
    if args.rehearsal_summary:
        data = load_json(args.rehearsal_summary, "rehearsal summary")
        report = rehearsal_progress(data, source_path=args.rehearsal_summary, objective=args.objective)
    else:
        data = load_json(args.source_status, "source execution status")
        acceptance = load_optional_json(args.final_acceptance, "final acceptance") if args.final_acceptance else None
        report = status_progress(
            data,
            source_path=args.source_status,
            objective=args.objective,
            final_acceptance=acceptance,
            final_acceptance_path=args.final_acceptance,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source progress status: {output}")
        print(f"next={report.get('nextBlockingLabel') or report.get('currentStage')} batchReady={str(report['batchReadiness']['readyForBatchUpload']).lower()}")
    if args.fail_if_batch_not_ready and not report["batchReadiness"]["readyForBatchUpload"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
