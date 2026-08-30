#!/usr/bin/env python3
"""Apply selected existing-site evidence to a source-file rehearsal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from prepare_created_site_schema_capture import build as prepare_created_site_schema_capture
from validate_run_evidence import validate as validate_run_evidence


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def artifact_path(summary: dict[str, Any], key: str) -> str:
    value = as_dict(summary.get("artifacts")).get(key)
    return value if isinstance(value, str) else ""


def require_artifact(summary: dict[str, Any], key: str) -> str:
    value = artifact_path(summary, key)
    if not value:
        raise SystemExit(f"ERROR: source rehearsal summary missing artifacts.{key}")
    if not Path(value).exists():
        raise SystemExit(f"ERROR: source rehearsal artifacts.{key} does not exist: {value}")
    return value


def require_existing_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"ERROR: {label} is required")
    if not Path(value).exists():
        raise SystemExit(f"ERROR: {label} does not exist: {value}")
    return value


def confirmed_artifact_path(summary: dict[str, Any], key: str) -> str:
    direct_key = {
        "confirmation": "confirmedConfirmation",
        "executionPlan": "confirmedExecutionPlan",
        "artifactReadiness": "confirmedArtifactReadiness",
    }[key]
    direct = artifact_path(summary, direct_key)
    if direct:
        return require_existing_path(direct, f"source rehearsal artifacts.{direct_key}")
    confirmed_summary_path = require_artifact(summary, "confirmedExecutionSummary")
    confirmed_summary = load_json(Path(confirmed_summary_path), "confirmed execution summary")
    confirmed_artifacts = as_dict(confirmed_summary.get("artifacts"))
    return require_existing_path(
        confirmed_artifacts.get(key),
        f"confirmed execution summary artifacts.{key}",
    )


def validate_selected_site_evidence(evidence: dict[str, Any]) -> list[str]:
    issues = validate_run_evidence(evidence)
    site_creation = evidence.get("siteCreation")
    if not isinstance(site_creation, dict):
        issues.append("siteCreation must be an object")
    elif site_creation.get("status") != "existing_site_selected":
        issues.append("siteCreation.status must be existing_site_selected")
    if evidence.get("completionClaimed") is not False:
        issues.append("completionClaimed must be false for selected-site read-only evidence")
    return issues


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = Path(args.rehearsal_summary).expanduser().resolve()
    evidence_path = Path(args.selected_site_evidence).expanduser().resolve()
    summary = load_json(summary_path, "source-file rehearsal summary")
    evidence = load_json(evidence_path, "selected existing-site evidence")
    evidence_issues = validate_selected_site_evidence(evidence)
    if evidence_issues:
        raise SystemExit("ERROR: invalid selected existing-site evidence:\n- " + "\n- ".join(evidence_issues))
    if summary.get("kind") != "allincms_source_file_rehearsal_summary":
        raise SystemExit("ERROR: rehearsal summary kind must be allincms_source_file_rehearsal_summary")
    if summary.get("confirmationPrepared") is not True:
        raise SystemExit("ERROR: source rehearsal must have confirmationPrepared=true")
    if summary.get("readyForBrowserStage") != "ready_for_existing_site_readonly_refresh":
        raise SystemExit("ERROR: source rehearsal must be at ready_for_existing_site_readonly_refresh")
    confirmed = as_dict(summary.get("confirmedExecution"))
    if confirmed.get("targetMode") != "existing_site":
        raise SystemExit("ERROR: confirmedExecution.targetMode must be existing_site")

    schema_summary = prepare_created_site_schema_capture(
        SimpleNamespace(
            artifact_readiness=confirmed_artifact_path(summary, "artifactReadiness"),
            created_site_evidence=str(evidence_path),
            package=require_artifact(summary, "sourceSitePackage"),
            review_packet=artifact_path(summary, "reviewPacket"),
            confirmation=confirmed_artifact_path(summary, "confirmation"),
            execution_plan=confirmed_artifact_path(summary, "executionPlan"),
            authorization_dir=args.authorization_dir,
            theme_target=args.theme_target,
            output_dir=str(output_dir / "selected-site-schema-capture"),
            json=False,
        )
    )
    artifacts = as_dict(schema_summary.get("artifacts"))
    result = {
        "kind": "allincms_selected_site_source_rehearsal_apply",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourceRehearsalSummary": str(summary_path),
        "selectedSiteEvidence": str(evidence_path),
        "status": "selected_site_bound_schema_capture_prepared",
        "readyForBrowserStage": schema_summary.get("sourceNextStage", {}).get("currentStage"),
        "siteKey": schema_summary.get("siteKey"),
        "frontendBaseUrl": schema_summary.get("frontendBaseUrl"),
        "targetMode": "existing_site",
        "schemaCaptureSummary": artifacts.get("summary", "") or str(output_dir / "selected-site-schema-capture" / "created-site-schema-capture-preparation-summary.json"),
        "sourceExecutionStatus": artifacts.get("sourceExecutionStatus", ""),
        "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
        "artifacts": {
            "schemaCaptureSummary": str(output_dir / "selected-site-schema-capture" / "created-site-schema-capture-preparation-summary.json"),
            "createdSiteArtifactBinding": artifacts.get("createdSiteArtifactBinding", ""),
            "boundArtifactReadiness": artifacts.get("boundArtifactReadiness", ""),
            "productsBoundDraftManifest": artifacts.get("productsBoundDraftManifest", ""),
            "postsBoundDraftManifest": artifacts.get("postsBoundDraftManifest", ""),
            "schemaCaptureHandoff": artifacts.get("schemaCaptureHandoff", ""),
            "schemaCaptureProgress": artifacts.get("schemaCaptureProgress", ""),
            "pagesSiteInfoHandoff": artifacts.get("pagesSiteInfoHandoff", ""),
            "pagesSiteInfoEvidenceBundle": artifacts.get("pagesSiteInfoEvidenceBundle", ""),
            "taxonomyHandoff": artifacts.get("taxonomyHandoff", ""),
            "taxonomyEvidenceBundle": artifacts.get("taxonomyEvidenceBundle", ""),
            "sourceExecutionStatus": artifacts.get("sourceExecutionStatus", ""),
            "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
        },
        "nextAction": schema_summary.get("nextAction", ""),
        "adversarialChecks": [
            "This helper applies read-only selected-site evidence to local source artifacts only.",
            "It does not prove a new site was created and does not authorize browser mutation.",
            "Existing-site binding may omit createdSiteSubmittedValues; do not use it for new-site objectives.",
            "Follow sourceNextStageHandoff before pages/site-info, taxonomy, schema, sample, or batch work.",
        ],
    }
    issues = validate_apply_result(result)
    if issues:
        raise SystemExit("ERROR: invalid selected-site source rehearsal apply result:\n- " + "\n- ".join(issues))
    write_json(Path(result["artifacts"]["schemaCaptureSummary"]), schema_summary)
    return result


def validate_apply_result(result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("kind") != "allincms_selected_site_source_rehearsal_apply":
        issues.append("kind must be allincms_selected_site_source_rehearsal_apply")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if result.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    if result.get("status") != "selected_site_bound_schema_capture_prepared":
        issues.append("status must be selected_site_bound_schema_capture_prepared")
    if result.get("targetMode") != "existing_site":
        issues.append("targetMode must be existing_site")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        return issues
    for key in (
        "schemaCaptureSummary",
        "createdSiteArtifactBinding",
        "boundArtifactReadiness",
        "productsBoundDraftManifest",
        "postsBoundDraftManifest",
        "schemaCaptureHandoff",
        "schemaCaptureProgress",
        "pagesSiteInfoHandoff",
        "pagesSiteInfoEvidenceBundle",
        "taxonomyHandoff",
        "taxonomyEvidenceBundle",
        "sourceExecutionStatus",
        "sourceNextStageHandoff",
    ):
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"artifacts.{key} is required")
        elif key != "schemaCaptureSummary" and not Path(value).exists():
            issues.append(f"artifacts.{key} must exist")
    if result.get("sourceExecutionStatus") != artifacts.get("sourceExecutionStatus"):
        issues.append("sourceExecutionStatus must mirror artifacts.sourceExecutionStatus")
    if result.get("sourceNextStageHandoff") != artifacts.get("sourceNextStageHandoff"):
        issues.append("sourceNextStageHandoff must mirror artifacts.sourceNextStageHandoff")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply selected existing-site evidence to source-file rehearsal artifacts.")
    parser.add_argument("--rehearsal-summary", required=True)
    parser.add_argument("--selected-site-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(args)
    output = Path(args.output).expanduser().resolve() if args.output else Path(args.output_dir).expanduser().resolve() / "selected-site-source-rehearsal-apply.json"
    write_json(output, result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote selected-site source rehearsal apply result: {output}")
        print(f"readyForBrowserStage={result['readyForBrowserStage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
