#!/usr/bin/env python3
"""Validate a full local-only AllinCMS E2E simulation output directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from summarize_run_status import summarize as summarize_run_status
from validate_manifest_rehearsal import validate_rehearsal as validate_manifest_rehearsal
from validate_run_evidence import validate as validate_run_evidence


REQUIRED_FILES = {
    "fullSummary": "full-e2e-summary.json",
    "siteEvidence": "01-site-creation/created-site-evidence.json",
    "siteSummary": "01-site-creation/run-summary.json",
    "probeEvidence": "02-probe-lifecycle/08-cleanup-completed-evidence.json",
    "probeSummary": "02-probe-lifecycle/run-summary.json",
    "moduleScan": "03-module-interface-plan/module-scan.redacted.json",
    "moduleScanSummary": "03-module-interface-plan/module-scan-summary.json",
    "moduleCapturePlan": "03-module-interface-plan/module-capture-plan.json",
    "draftManifest": "04-manifest-rehearsal/draft-manifest.json",
    "sourceInputRequirements": "04-manifest-rehearsal/source-input-requirements.json",
    "manifestSummary": "04-manifest-rehearsal/manifest-rehearsal-summary.json",
}


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def require(condition: bool, issues: list[str], message: str) -> None:
    if not condition:
        issues.append(message)


def same_path(recorded: object, expected: Path) -> bool:
    if not isinstance(recorded, str) or not recorded.strip():
        return False
    return Path(recorded).resolve() == expected.resolve()


def validate_directory(root: Path) -> dict:
    issues: list[str] = []
    paths = {key: root / rel for key, rel in REQUIRED_FILES.items()}
    loaded: dict[str, dict] = {}
    for key, path in paths.items():
        try:
            loaded[key] = load_json(path)
        except ValueError as exc:
            issues.append(str(exc))
    if issues:
        return {"ok": False, "root": str(root), "issues": issues, "paths": {k: str(v) for k, v in paths.items()}}

    full = loaded["fullSummary"]
    site_evidence = loaded["siteEvidence"]
    probe_evidence = loaded["probeEvidence"]
    module_scan = loaded["moduleScan"]
    module_summary = loaded["moduleScanSummary"]
    capture_plan = loaded["moduleCapturePlan"]
    manifest_summary = loaded["manifestSummary"]

    require(full.get("localOnly") is True, issues, "full summary must be localOnly")
    require(full.get("remoteMutationsPerformed") is False, issues, "full summary must record no remote mutations")
    require(same_path(full.get("siteCreationDir"), root / "01-site-creation"), issues, "siteCreationDir does not match output root")
    require(same_path(full.get("probeLifecycleDir"), root / "02-probe-lifecycle"), issues, "probeLifecycleDir does not match output root")
    require(same_path(full.get("moduleInterfaceDir"), root / "03-module-interface-plan"), issues, "moduleInterfaceDir does not match output root")
    require(same_path(full.get("manifestRehearsalDir"), root / "04-manifest-rehearsal"), issues, "manifestRehearsalDir does not match output root")

    site_errors = validate_run_evidence(site_evidence)
    probe_errors = validate_run_evidence(probe_evidence)
    issues.extend(f"site evidence: {error}" for error in site_errors)
    issues.extend(f"probe evidence: {error}" for error in probe_errors)

    site_summary = summarize_run_status(site_evidence, str(paths["siteEvidence"]), require_created_site=True)
    probe_summary = summarize_run_status(probe_evidence, str(paths["probeEvidence"]), require_created_site=True)
    require(site_summary.get("valid") is True, issues, "site summary must be valid")
    require(probe_summary.get("valid") is True, issues, "probe summary must be valid")
    require(probe_summary.get("localOnly") is True, issues, "probe lifecycle summary must be localOnly")
    require(probe_summary.get("simulationOnly") is True, issues, "probe lifecycle summary must be simulationOnly")
    require(probe_summary.get("remoteMutationsPerformed") is False, issues, "probe lifecycle summary must record no remote mutations")
    require(probe_summary.get("complete") is False, issues, "probe lifecycle summary must not claim real completion")
    require(probe_summary.get("completionGaps") == [], issues, "probe lifecycle simulation should have no modeled completion gaps")
    require(full.get("siteSummary", {}).get("valid") == site_summary.get("valid"), issues, "full siteSummary.valid mismatch")
    require(full.get("probeSummary", {}).get("complete") == probe_summary.get("complete"), issues, "full probeSummary.complete mismatch")

    require(module_scan.get("siteKey") == capture_plan.get("siteKey"), issues, "module scan and capture plan siteKey mismatch")
    require(module_summary.get("kind") == "allincms_module_scan_summary", issues, "module scan summary kind mismatch")
    require(capture_plan.get("kind") == "allincms_module_capture_plan", issues, "capture plan kind mismatch")
    require(module_summary.get("jsonReplayReady") is False, issues, "module summary must not be replay-ready")
    require(capture_plan.get("jsonReplayReady") is False, issues, "capture plan must not be replay-ready")
    stages = capture_plan.get("stages")
    require(isinstance(stages, list) and bool(stages), issues, "capture plan must contain stages")
    if isinstance(stages, list):
        require(
            full.get("moduleInterface", {}).get("captureStageCount") == len(stages),
            issues,
            "full moduleInterface.captureStageCount mismatch",
        )
        groups = sorted({stage.get("group", "") for stage in stages if isinstance(stage, dict)})
        require(full.get("moduleInterface", {}).get("captureGroups") == groups, issues, "full captureGroups mismatch")
        require(
            all(stage.get("jsonReplayReady") is False for stage in stages if isinstance(stage, dict)),
            issues,
            "every capture stage must remain jsonReplayReady false",
        )

    manifest_validation = validate_manifest_rehearsal(paths["manifestSummary"])
    issues.extend(f"manifest rehearsal: {error}" for error in manifest_validation.get("issues", []))
    require(manifest_validation.get("ok") is True, issues, "manifest rehearsal validation must pass")
    require(
        full.get("manifestRehearsal", {}).get("sourceInputRequirementsStatus") == "blocked",
        issues,
        "full manifestRehearsal.sourceInputRequirementsStatus must be blocked",
    )
    require(
        full.get("manifestRehearsal", {}).get("sourceInputRequirementsBlockedUntilCount")
        == loaded["manifestSummary"].get("sourceInputRequirements", {}).get("blockedUntilCount"),
        issues,
        "full manifestRehearsal.sourceInputRequirementsBlockedUntilCount mismatch",
    )
    source_requirements = loaded.get("sourceInputRequirements", {})
    operation_gaps = source_requirements.get("operationGaps") if isinstance(source_requirements, dict) else {}
    require(
        isinstance(operation_gaps, dict) and operation_gaps.get("entryCount", 0) > 0,
        issues,
        "sourceInputRequirements.operationGaps.entryCount must be positive",
    )
    require(
        loaded["manifestSummary"].get("sourceInputRequirements", {}).get("operationGapCount")
        == operation_gaps.get("entryCount"),
        issues,
        "manifest summary operationGapCount mismatch",
    )
    require(
        full.get("manifestRehearsal", {}).get("contentType") == manifest_summary.get("contentType"),
        issues,
        "full manifestRehearsal.contentType mismatch",
    )
    require(
        full.get("manifestRehearsal", {}).get("draftValidationPassed") is True,
        issues,
        "full manifestRehearsal.draftValidationPassed must be true",
    )
    require(
        full.get("manifestRehearsal", {}).get("schemaGateExpectedFailure") is True,
        issues,
        "full manifestRehearsal.schemaGateExpectedFailure must be true",
    )
    require(
        full.get("manifestRehearsal", {}).get("schemaGateErrorCount") == manifest_summary.get("schemaGate", {}).get("errorCount"),
        issues,
        "full manifestRehearsal.schemaGateErrorCount mismatch",
    )

    return {
        "ok": not issues,
        "root": str(root),
        "localOnly": full.get("localOnly"),
        "remoteMutationsPerformed": full.get("remoteMutationsPerformed"),
        "siteKey": capture_plan.get("siteKey"),
        "captureStageCount": len(stages) if isinstance(stages, list) else 0,
        "manifestDraftValidationPassed": manifest_validation.get("draftValidationPassed"),
        "manifestSchemaGateExpectedFailure": manifest_validation.get("schemaGateExpectedFailure"),
        "sourceInputRequirementsGenerated": True,
        "sourceInputRequirementsBlocked": manifest_validation.get("sourceInputRequirementsBlocked"),
        "sourceInputRequirementsBlockedUntilCount": loaded["manifestSummary"].get("sourceInputRequirements", {}).get("blockedUntilCount"),
        "sourceInputOperationGapCount": operation_gaps.get("entryCount") if isinstance(operation_gaps, dict) else 0,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate full local-only AllinCMS E2E simulation output.")
    parser.add_argument("output_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_directory(Path(args.output_dir).resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("Full E2E simulation output validation passed.")
    else:
        print("Full E2E simulation output validation failed:")
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
