#!/usr/bin/env python3
"""Validate an AllinCMS per-stage browser evidence bundle."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from apply_browser_stage_result import validate_browser_stage_result
from build_browser_execution_plan import SIMULATED_SITE_KEYS
from build_browser_stage_packet import validate_browser_stage_packet
from validate_run_evidence import EMAIL_RE, FORBIDDEN_EVIDENCE_TERMS


WORKSPACE_SITE_URL_RE = re.compile(r"https://workspace\.laicms\.com/([a-z0-9][a-z0-9-]{2,62}[a-z0-9])(?:/|$)")
FRONTEND_ORIGIN_RE = re.compile(r"https://[a-z0-9-]+\.web\.allincms\.com", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def same_path(recorded: object, expected: Path, base: Path | None = None) -> bool:
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    recorded_path = Path(recorded)
    if not recorded_path.is_absolute() and base is not None:
        recorded_path = base / recorded_path
    return recorded_path.resolve() == expected.resolve()


def resolve_recorded_path(recorded: object, base: Path) -> Path | None:
    if not isinstance(recorded, str) or not recorded.strip():
        return None
    path = Path(recorded)
    if not path.is_absolute():
        path = base / path
    return path


def require(condition: bool, issues: list[str], message: str) -> None:
    if not condition:
        issues.append(message)


def leakage_issues(label: str, text: str) -> list[str]:
    issues: list[str] = []
    if EMAIL_RE.search(text):
        issues.append(f"{label} must not contain email addresses")
    for term in FORBIDDEN_EVIDENCE_TERMS:
        if term and term in text:
            issues.append(f"{label} contains forbidden evidence term: {term}")
    for site_key in SIMULATED_SITE_KEYS:
        if site_key in text:
            issues.append(f"{label} must not contain simulated site keys")
    if FRONTEND_ORIGIN_RE.search(text):
        issues.append(f"{label} must use redacted route patterns instead of concrete frontend origins")
    for match in WORKSPACE_SITE_URL_RE.finditer(text):
        site_key = match.group(1)
        if site_key != "sites":
            issues.append(f"{label} must redact workspace site URLs with {{realSiteKey}}")
            break
    return issues


def validate_manifest_against_packet(
    manifest: dict[str, Any],
    packet: dict[str, Any],
    manifest_path: Path,
    packet_path: Path,
    output_dir: Path,
    issues: list[str],
) -> None:
    require(manifest.get("kind") == "allincms_browser_stage_evidence_bundle", issues, "manifest kind mismatch")
    require(manifest.get("localOnly") is True, issues, "manifest must be localOnly")
    require(manifest.get("remoteMutationsPerformed") is False, issues, "manifest must record no remote mutations")
    require(manifest.get("stageId") == packet.get("stageId"), issues, "manifest stageId must match packet stageId")
    require(manifest.get("recovery") == (packet.get("recovery") is True), issues, "manifest recovery must match packet")
    require(manifest.get("mode") == packet.get("mode"), issues, "manifest mode must match packet")
    require(
        manifest.get("authorizationRequired") == (packet.get("authorizationRequired") is True),
        issues,
        "manifest authorizationRequired must match packet",
    )
    require(
        manifest.get("remoteMutationExpectation") == packet.get("remoteMutationExpectation"),
        issues,
        "manifest remoteMutationExpectation must match packet",
    )
    require(
        manifest.get("targetTemplate") == packet.get("targetTemplate"),
        issues,
        "manifest targetTemplate must match packet",
    )
    require(
        manifest.get("requiredProof") == packet.get("requiredProof"),
        issues,
        "manifest requiredProof must match packet requiredProof",
    )
    require(same_path(manifest.get("sourcePacket"), packet_path, manifest_path.parent), issues, "manifest sourcePacket mismatch")
    require(same_path(manifest.get("outputDir"), output_dir, manifest_path.parent), issues, "manifest outputDir mismatch")
    require(
        same_path(manifest.get("stageResultTemplate"), output_dir / "stage-result-template.json", manifest_path.parent),
        issues,
        "manifest stageResultTemplate mismatch",
    )
    require(
        same_path(manifest.get("notesPath"), output_dir / "notes.md", manifest_path.parent),
        issues,
        "manifest notesPath mismatch",
    )
    expected_files = manifest.get("expectedEvidenceFiles")
    require(isinstance(expected_files, list) and "stage-result.json" in expected_files, issues, "manifest expectedEvidenceFiles must include stage-result.json")
    command = manifest.get("applyCommandTemplate")
    require(
        isinstance(command, str)
        and "make_browser_stage_result.py" in command
        and "--packet-json" in command
        and "stage-result.json" in command,
        issues,
        "manifest applyCommandTemplate must build a packet-aware stage result",
    )
    warning = manifest.get("warning")
    require(
        isinstance(warning, str) and "does not authorize browser actions" in warning and "does not prove remote persistence" in warning,
        issues,
        "manifest warning must state that the bundle is not authorization or persistence proof",
    )


def validate_stage_result_template(
    template: dict[str, Any],
    packet: dict[str, Any],
    issues: list[str],
) -> None:
    validation = validate_browser_stage_result(template, packet)
    allowed_template_issues = {
        "partial result requires redactedEvidencePointers",
        "partial result requires proofRecorded",
    }
    filtered = [issue for issue in validation.get("issues", []) if issue not in allowed_template_issues]
    issues.extend(f"stage-result template: {issue}" for issue in filtered)
    require(template.get("stageId") == packet.get("stageId"), issues, "stage-result template stageId must match packet")
    require(template.get("status") == "partial", issues, "stage-result template must start partial")
    require(template.get("localOnly") is True, issues, "stage-result template must be localOnly")
    require(template.get("remoteMutationsPerformed") is False, issues, "stage-result template must record no remote mutations")
    require(template.get("browserStageMutatedRemote") is False, issues, "stage-result template must not claim remote mutation")
    require(template.get("proofRecorded") == [], issues, "stage-result template proofRecorded must start empty")
    blockers = template.get("blockingIssues")
    require(isinstance(blockers, list) and len(blockers) >= 1, issues, "stage-result template must include a blocker placeholder")
    require(
        isinstance(blockers, list) and any("placeholder" in item for item in blockers if isinstance(item, str)),
        issues,
        "stage-result template blocker must clearly be a placeholder",
    )


def validate_notes(notes: str, packet: dict[str, Any], issues: list[str]) -> None:
    require("Required Proof" in notes, issues, "notes must include Required Proof section")
    require("Evidence Rules" in notes, issues, "notes must include Evidence Rules section")
    require("not user approval" in notes, issues, "notes must state the bundle is not authorization")
    require("redacted local evidence pointers" in notes, issues, "notes must require redacted local evidence pointers")
    require("cookies, tokens" in notes, issues, "notes must forbid cookies and tokens")
    require("concrete site-scoped workspace URLs" in notes, issues, "notes must forbid concrete site-scoped workspace URLs")
    for proof in packet.get("requiredProof", []):
        if isinstance(proof, str) and proof.strip():
            require(proof in notes, issues, f"notes missing required proof label: {proof}")


def validate_bundle(bundle_or_manifest_path: Path, packet_json: Path | None = None) -> dict[str, Any]:
    issues: list[str] = []
    manifest_path = bundle_or_manifest_path / "evidence-manifest.json" if bundle_or_manifest_path.is_dir() else bundle_or_manifest_path
    output_dir = manifest_path.parent

    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return {"ok": False, "manifestPath": str(manifest_path), "issues": [str(exc)]}

    packet_path = packet_json
    if packet_path is None:
        packet_path = resolve_recorded_path(manifest.get("sourcePacket"), manifest_path.parent)
    if packet_path is None:
        packet = {}
        issues.append("manifest sourcePacket must be a non-empty path")
    else:
        try:
            packet = load_json(packet_path)
        except ValueError as exc:
            packet = {}
            issues.append(str(exc))

    packet_validation = validate_browser_stage_packet(packet)
    issues.extend(f"source packet: {issue}" for issue in packet_validation.get("issues", []))
    require(packet_validation.get("ok") is True, issues, "source packet validation must pass")
    if packet_path is not None:
        validate_manifest_against_packet(manifest, packet, manifest_path, packet_path, output_dir, issues)

    template_path = output_dir / "stage-result-template.json"
    notes_path = output_dir / "notes.md"
    try:
        template = load_json(template_path)
    except ValueError as exc:
        template = {}
        issues.append(str(exc))
    validate_stage_result_template(template, packet, issues)
    try:
        notes = notes_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        notes = ""
        issues.append(f"file not found: {notes_path}")
    validate_notes(notes, packet, issues)

    manifest_text = json.dumps(manifest, ensure_ascii=False)
    template_text = json.dumps(template, ensure_ascii=False)
    packet_text = json.dumps(packet, ensure_ascii=False)
    issues.extend(leakage_issues("manifest", manifest_text))
    issues.extend(leakage_issues("stage-result template", template_text))
    issues.extend(leakage_issues("source packet", packet_text))
    issues.extend(leakage_issues("notes", notes))

    return {
        "ok": not issues,
        "manifestPath": str(manifest_path),
        "bundleDir": str(output_dir),
        "packetPath": str(packet_path) if packet_path is not None else "",
        "stageId": manifest.get("stageId", ""),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an AllinCMS browser stage evidence bundle.")
    parser.add_argument("bundle_or_manifest_path")
    parser.add_argument("--packet-json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_bundle(
        Path(args.bundle_or_manifest_path),
        Path(args.packet_json) if args.packet_json else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Browser stage evidence bundle validation passed.")
    else:
        print("Browser stage evidence bundle validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
