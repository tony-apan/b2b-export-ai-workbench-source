#!/usr/bin/env python3
"""Prepare a local evidence bundle directory for one AllinCMS browser stage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from build_browser_stage_packet import validate_browser_stage_packet


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"packet JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid packet JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("packet JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_result_template(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "allincms_browser_stage_result",
        "generatedAt": "",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "stageId": packet["stageId"],
        "status": "partial",
        "redactedEvidencePointers": [],
        "proofRecorded": [],
        "blockingIssues": ["replace this placeholder with missing proof or blockers before applying"],
        "browserStageMutatedRemote": False,
        "operatorNote": "",
    }


def build_manifest(packet: dict[str, Any], packet_path: Path, output_dir: Path) -> dict[str, Any]:
    stage_id = str(packet.get("stageId", ""))
    required_proof = [item for item in packet.get("requiredProof", []) if isinstance(item, str)]
    return {
        "kind": "allincms_browser_stage_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "stageId": stage_id,
        "recovery": packet.get("recovery") is True,
        "mode": packet.get("mode", ""),
        "authorizationRequired": packet.get("authorizationRequired") is True,
        "remoteMutationExpectation": packet.get("remoteMutationExpectation", ""),
        "targetTemplate": packet.get("targetTemplate", ""),
        "sourcePacket": str(packet_path),
        "outputDir": str(output_dir),
        "requiredProof": required_proof,
        "expectedEvidenceFiles": [
            "redacted-browser-scan.json",
            "redacted-network-summary.json",
            "redacted-frontend-audit.json",
            "backend-state-proof.json",
            "stage-result.json",
        ],
        "stageResultTemplate": str(output_dir / "stage-result-template.json"),
        "notesPath": str(output_dir / "notes.md"),
        "applyCommandTemplate": (
            "python3 skills/allincms-bulk-content-upload/scripts/make_browser_stage_result.py "
            f"--packet-json {packet_path} "
            "--status completed "
            f"--evidence-pointers {output_dir}/redacted-browser-scan.json "
            f"--output {output_dir}/stage-result.json"
        ),
        "warning": (
            "This bundle is local scaffolding only. It does not authorize browser actions, "
            "does not prove remote persistence, and must be filled with redacted evidence before ledger apply."
        ),
    }


def build_notes(packet: dict[str, Any]) -> str:
    lines = [
        "# AllinCMS Browser Stage Evidence Notes",
        "",
        f"- stageId: `{packet.get('stageId', '')}`",
        f"- targetTemplate: `{packet.get('targetTemplate', '')}`",
        f"- authorizationRequired: `{packet.get('authorizationRequired') is True}`",
        f"- remoteMutationExpectation: `{packet.get('remoteMutationExpectation', '')}`",
        "",
        "## Required Proof",
        "",
    ]
    for proof in packet.get("requiredProof", []):
        if isinstance(proof, str) and proof.strip():
            lines.append(f"- [ ] {proof}")
    lines.extend(
        [
            "",
            "## Evidence Rules",
            "",
            "- Store only redacted local evidence pointers in `stage-result.json`.",
            "- Do not store cookies, tokens, account text, raw IDs, private copy, or concrete site-scoped workspace URLs.",
            "- For authorization-required stages, this bundle is not user approval; obtain action-time authorization first.",
            "- After the stage, create `stage-result.json`, validate it against the packet, then apply it to the ledger.",
            "",
        ]
    )
    return "\n".join(lines)


def prepare_bundle(packet_path: Path, output_dir: Path, force: bool = False) -> dict[str, Any]:
    packet = load_json(packet_path)
    validation = validate_browser_stage_packet(packet)
    if not validation["ok"]:
        raise ValueError("packet validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise ValueError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(packet, packet_path, output_dir)
    write_json(output_dir / "evidence-manifest.json", manifest)
    write_json(output_dir / "stage-result-template.json", stage_result_template(packet))
    (output_dir / "notes.md").write_text(build_notes(packet), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local evidence bundle for one AllinCMS browser stage packet.")
    parser.add_argument("--packet-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true", help="Allow writing into a non-empty output directory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        manifest = prepare_bundle(Path(args.packet_json), Path(args.output_dir), args.force)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote evidence bundle: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
