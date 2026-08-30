#!/usr/bin/env python3
"""Build a single-stage browser execution packet from an AllinCMS execution ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from build_browser_execution_ledger import load_json, validate_browser_execution_ledger
from build_browser_execution_plan import SIMULATED_SITE_KEYS, VALID_MODES
from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_stage(ledger: dict[str, Any], stage_id: str) -> dict[str, Any]:
    entries = ledger.get("entries") if isinstance(ledger.get("entries"), list) else []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("stageId") == stage_id:
            return entry
    raise ValueError(f"stage not found in ledger: {stage_id}")


def build_authorization_template(entry: dict[str, Any]) -> str:
    if entry.get("authorizationRequired") is not True:
        return ""
    return (
        "授权 Codex 仅在 {targetTemplate} 执行 stage={stageId}；"
        "只允许执行本 stage 的 allowedActions；完成 requiredProof 后停止，"
        "不得继续下一阶段、批量操作、发布、删除或上传，除非另有单独授权。"
    ).format(targetTemplate=entry.get("targetTemplate", ""), stageId=entry.get("stageId", ""))


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def default_result_path(packet_path: str) -> str:
    if packet_path and not any(marker in packet_path for marker in ("{", "}")):
        packet = Path(packet_path)
        return str(packet.with_name(packet.stem + "-stage-result.json"))
    return "{stageResultPath}"


def default_updated_ledger_path(ledger_path: str, stage_id: str) -> str:
    if ledger_path and not any(marker in ledger_path for marker in ("{", "}")):
        ledger = Path(ledger_path)
        return str(ledger.with_name(f"{ledger.stem}.after-{stage_id}.json"))
    return "{updatedLedgerPath}"


def build_completion_template(
    ledger: dict[str, Any],
    entry: dict[str, Any],
    recovery: bool = False,
    ledger_path: str = "{ledgerPath}",
    packet_path: str = "{packetPath}",
    stage_result_path: str = "",
    output_ledger_path: str = "",
) -> dict[str, Any]:
    completed = [
        str(item.get("stageId"))
        for item in ledger.get("entries", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    ]
    stage_id = str(entry.get("stageId", ""))
    completed_after = completed if stage_id in completed else completed + [stage_id]
    result_path = stage_result_path or default_result_path(packet_path)
    updated_path = output_ledger_path or default_updated_ledger_path(ledger_path, stage_id)
    return {
        "afterStageCompletes": (
            "Apply a completed, partial, or blocked result to this partial stage, then regenerate the next packet."
            if recovery
            else "Apply a completed, partial, or blocked stage result after redacted evidence is recorded."
        ),
        "expectedCompletedStageIdsAfterApply": completed_after,
        "stageResultRequired": True,
        "commandTemplate": shell_join(
            [
                "python3",
                "skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py",
                "--ledger",
                ledger_path,
                "--packet",
                packet_path,
                "--result-json",
                result_path,
                "--output",
                updated_path,
            ]
        ),
    }


def build_browser_stage_packet(
    ledger: dict[str, Any],
    stage_id: str = "",
    ledger_path: str = "{ledgerPath}",
    packet_path: str = "{packetPath}",
    stage_result_path: str = "",
    output_ledger_path: str = "",
) -> dict[str, Any]:
    ledger_validation = validate_browser_execution_ledger(ledger)
    if not ledger_validation.get("ok"):
        raise ValueError("browser execution ledger validation failed:\n" + "\n".join(f"- {issue}" for issue in ledger_validation["issues"]))
    selected_stage_id = stage_id.strip() or str(ledger.get("nextStageId", "")).strip()
    if not selected_stage_id:
        raise ValueError("ledger has no nextStageId; no stage is ready")
    entry = find_stage(ledger, selected_stage_id)
    recovery = False
    if entry.get("status") == "partial":
        if not stage_id.strip():
            raise ValueError(f"stage is partial and must be selected explicitly for recovery: {selected_stage_id}")
        recovery = True
    elif entry.get("status") != "ready":
        raise ValueError(f"stage is not ready: {selected_stage_id}")

    packet = {
        "kind": "allincms_browser_stage_packet",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceLedgerKind": ledger.get("kind"),
        "siteKeyTemplate": "{realSiteKey}",
        "stageId": selected_stage_id,
        "recovery": recovery,
        "phase": entry.get("phase", ""),
        "mode": entry.get("mode", ""),
        "targetTemplate": entry.get("targetTemplate", ""),
        "authorizationRequired": entry.get("authorizationRequired") is True,
        "remoteMutationExpectation": entry.get("remoteMutationExpectation", ""),
        "suggestedAuthorizationText": build_authorization_template(entry),
        "allowedActions": (
            [
                "resume same partial stage only",
                "capture the missing proof listed in blockedUntil",
                "do not run a later stage until this stage is completed and the ledger exposes it",
            ]
            if recovery
            else list(entry.get("nextAllowedActions", []))
        ),
        "requiredProof": list(entry.get("requiredProof", [])),
        "forbiddenActions": [
            "continue to another stage without regenerating the ledger",
            "store account data, cookies, tokens, raw IDs, or business copy in this skill",
        ],
        "stopAfter": entry.get("stopAfter", ""),
        "evidenceCaptureTemplate": {
            "stageId": selected_stage_id,
            "status": "completed|blocked|partial",
            "redactedEvidencePointers": [],
            "proofRecorded": list(entry.get("requiredProof", [])),
            "blockingIssues": [],
            "operatorNote": "",
            "browserStageMutatedRemote": entry.get("remoteMutationExpectation") == "must",
        },
        "ledgerUpdate": build_completion_template(
            ledger,
            entry,
            recovery,
            ledger_path,
            packet_path,
            stage_result_path,
            output_ledger_path,
        ),
        "warnings": [
            "This packet is local-only and does not authorize remote LAICMS mutation.",
            "For requires_authorization stages, use the suggested text as a template and wait for action-time user approval.",
            "Run only this stage, then update or regenerate the ledger before continuing.",
        ],
    }
    validation = validate_browser_stage_packet(packet)
    if not validation.get("ok"):
        raise ValueError("browser stage packet validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return packet


def validate_browser_stage_packet(packet: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if packet.get("kind") != "allincms_browser_stage_packet":
        issues.append("kind must be allincms_browser_stage_packet")
    if packet.get("localOnly") is not True:
        issues.append("packet must be localOnly")
    if packet.get("remoteMutationsPerformed") is not False:
        issues.append("packet must record no remote mutations")
    if packet.get("sourceLedgerKind") != "allincms_browser_execution_ledger":
        issues.append("sourceLedgerKind must be allincms_browser_execution_ledger")
    if not isinstance(packet.get("recovery"), bool):
        issues.append("recovery must be a boolean")
    if packet.get("siteKeyTemplate") != "{realSiteKey}":
        issues.append("siteKeyTemplate must be {realSiteKey}")
    if packet.get("mode") not in VALID_MODES:
        issues.append(f"mode must be one of {sorted(VALID_MODES)}")
    requires_auth = packet.get("mode") == "requires_authorization"
    if packet.get("authorizationRequired") is not requires_auth:
        issues.append("authorizationRequired must match mode")
    expectation = packet.get("remoteMutationExpectation")
    if expectation not in {"must", "may", "must_not"}:
        issues.append("remoteMutationExpectation must be must, may, or must_not")
    elif not requires_auth and expectation != "must_not":
        issues.append("remoteMutationExpectation must be must_not for non-authorization stages")
    elif requires_auth and expectation == "must_not":
        issues.append("remoteMutationExpectation must not be must_not for authorization stages")
    auth_text = packet.get("suggestedAuthorizationText")
    target_template = packet.get("targetTemplate")
    if requires_auth and not isinstance(auth_text, str):
        issues.append("suggestedAuthorizationText must be a string for authorization stages")
    elif requires_auth:
        if isinstance(target_template, str) and target_template not in auth_text:
            issues.append("suggestedAuthorizationText must contain targetTemplate for authorization stages")
        if isinstance(target_template, str) and target_template != "https://workspace.laicms.com/sites" and "{realSiteKey}" not in auth_text:
            issues.append("suggestedAuthorizationText must contain {realSiteKey} for site-scoped authorization stages")
    if not requires_auth and auth_text not in {"", None}:
        issues.append("suggestedAuthorizationText must be empty for non-authorization stages")
    for key in ("stageId", "phase", "targetTemplate", "stopAfter"):
        if not isinstance(packet.get(key), str) or not packet[key].strip():
            issues.append(f"{key} must be a non-empty string")
    for key in ("allowedActions", "requiredProof", "forbiddenActions", "warnings"):
        value = packet.get(key)
        if not isinstance(value, list) or not value:
            issues.append(f"{key} must be a non-empty array")
        elif not all(isinstance(item, str) and item.strip() for item in value):
            issues.append(f"{key} must contain non-empty strings")
    capture = packet.get("evidenceCaptureTemplate")
    if not isinstance(capture, dict):
        issues.append("evidenceCaptureTemplate must be an object")
    elif capture.get("stageId") != packet.get("stageId"):
        issues.append("evidenceCaptureTemplate.stageId must match packet stageId")
    elif capture.get("status") != "completed|blocked|partial":
        issues.append("evidenceCaptureTemplate.status must list completed|blocked|partial")
    elif not isinstance(capture.get("browserStageMutatedRemote"), bool):
        issues.append("evidenceCaptureTemplate.browserStageMutatedRemote must be a boolean")
    update = packet.get("ledgerUpdate")
    if not isinstance(update, dict):
        issues.append("ledgerUpdate must be an object")
    else:
        if "completedStageIds" in update:
            issues.append("ledgerUpdate must not expose completedStageIds; use result-json apply path")
        completed = update.get("expectedCompletedStageIdsAfterApply")
        if not isinstance(completed, list) or packet.get("stageId") not in completed:
            issues.append("ledgerUpdate.expectedCompletedStageIdsAfterApply must include packet stageId")
        if update.get("stageResultRequired") is not True:
            issues.append("ledgerUpdate.stageResultRequired must be true")
        command = update.get("commandTemplate")
        if not isinstance(command, str) or "apply_browser_stage_result.py" not in command:
            issues.append("ledgerUpdate.commandTemplate must use apply_browser_stage_result.py")
        elif "--result-json" not in command:
            issues.append("ledgerUpdate.commandTemplate must apply a result JSON")
        elif "--completed-stage-ids" in command:
            issues.append("ledgerUpdate.commandTemplate must not rebuild from completed-stage ids")

    text = json.dumps(packet, ensure_ascii=False)
    if EMAIL_RE.search(text):
        issues.append("packet must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"packet contains forbidden evidence term: {term}")
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in text:
            issues.append("packet must not contain simulated site keys")
    if re.search(r"https://[a-z0-9-]+\.web\.allincms\.com", text):
        issues.append("packet must use {realSiteKey} frontend template")

    return {"ok": not issues, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a single-stage browser packet from an AllinCMS execution ledger.")
    parser.add_argument("browser_execution_ledger_json")
    parser.add_argument("--stage-id", default="")
    parser.add_argument("--output")
    parser.add_argument("--stage-result-path", default="")
    parser.add_argument("--updated-ledger-output", default="")
    args = parser.parse_args()

    try:
        packet_output = args.output or "{packetPath}"
        packet = build_browser_stage_packet(
            load_json(Path(args.browser_execution_ledger_json)),
            args.stage_id,
            args.browser_execution_ledger_json,
            packet_output,
            args.stage_result_path,
            args.updated_ledger_output,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        write_json(Path(args.output), packet)
    else:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
