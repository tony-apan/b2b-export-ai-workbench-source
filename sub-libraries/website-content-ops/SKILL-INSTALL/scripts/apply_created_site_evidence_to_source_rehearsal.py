#!/usr/bin/env python3
"""Apply filled created-site evidence to a source-file rehearsal chain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from apply_created_site_evidence_bundle import build as apply_created_site_bundle


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


def require_artifact(result: dict[str, Any], key: str) -> str:
    value = as_dict(result.get("artifacts")).get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"ERROR: source apply result missing artifacts.{key}")
    if not Path(value).exists():
        raise SystemExit(f"ERROR: source apply result artifacts.{key} does not exist: {value}")
    return value


def optional_artifact(result: dict[str, Any], key: str) -> str:
    value = as_dict(result.get("artifacts")).get(key)
    return value if isinstance(value, str) else ""


def confirmed_source_paths(confirmation_path: str) -> tuple[str, str]:
    confirmation = load_json(Path(confirmation_path), "source package confirmation")
    package = confirmation.get("sourcePackage")
    review_packet = confirmation.get("sourceReviewPacket")
    if not isinstance(package, str) or not package.strip() or not Path(package).exists():
        raise SystemExit("ERROR: confirmation.sourcePackage must point to an existing artifact")
    if not isinstance(review_packet, str) or not review_packet.strip() or not Path(review_packet).exists():
        raise SystemExit("ERROR: confirmation.sourceReviewPacket must point to an existing artifact")
    return package, review_packet


def require_source_apply_result(result: dict[str, Any]) -> None:
    if result.get("kind") != "allincms_create_preflight_source_rehearsal_apply":
        raise SystemExit("ERROR: source apply result kind must be allincms_create_preflight_source_rehearsal_apply")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
    ):
        if result.get(key) is not expected:
            raise SystemExit(f"ERROR: source apply result {key} must be {str(expected).lower()}")
    if result.get("status") != "create_site_handoff_prepared":
        raise SystemExit("ERROR: source apply result status must be create_site_handoff_prepared")
    if result.get("readyForBrowserStage") != "create_site_handoff_ready":
        raise SystemExit("ERROR: source apply result readyForBrowserStage must be create_site_handoff_ready")
    if result.get("targetMode") != "new_site":
        raise SystemExit("ERROR: source apply result targetMode must be new_site")


def validate_apply_summary(summary: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if summary.get("kind") != "allincms_created_site_evidence_source_rehearsal_apply":
        issues.append("kind must be allincms_created_site_evidence_source_rehearsal_apply")
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("isRemoteMutationAuthorization", False),
        ("preparedOnly", True),
    ):
        if summary.get(key) is not expected:
            issues.append(f"{key} must be {str(expected).lower()}")
    if summary.get("status") != "created_site_evidence_applied":
        issues.append("status must be created_site_evidence_applied")
    if not isinstance(summary.get("readyForBrowserStage"), str) or not summary["readyForBrowserStage"].strip():
        issues.append("readyForBrowserStage must be a non-empty string")
    if summary.get("createdSiteSchemaCapturePrepared") is not True:
        issues.append("createdSiteSchemaCapturePrepared must be true")
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
        return issues
    required_existing = (
        "createdSiteEvidenceBundleApplySummary",
        "createdSiteEvidence",
        "createdSiteSchemaCaptureSummary",
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
    )
    for key in required_existing:
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"artifacts.{key} is required")
        elif not Path(value).exists():
            issues.append(f"artifacts.{key} must point to an existing artifact")
    if summary.get("createdSiteEvidence") != artifacts.get("createdSiteEvidence"):
        issues.append("createdSiteEvidence must mirror artifacts.createdSiteEvidence")
    if summary.get("sourceExecutionStatus") != artifacts.get("sourceExecutionStatus"):
        issues.append("sourceExecutionStatus must mirror artifacts.sourceExecutionStatus")
    if summary.get("sourceNextStageHandoff") != artifacts.get("sourceNextStageHandoff"):
        issues.append("sourceNextStageHandoff must mirror artifacts.sourceNextStageHandoff")
    source_status_path = artifacts.get("sourceExecutionStatus")
    if isinstance(source_status_path, str) and source_status_path.strip() and Path(source_status_path).exists():
        try:
            source_status = load_json(Path(source_status_path), "source execution status")
        except SystemExit as exc:
            issues.append(str(exc))
        else:
            if summary.get("readyForBrowserStage") != source_status.get("currentStage"):
                issues.append("readyForBrowserStage must match sourceExecutionStatus.currentStage")
    checks = summary.get("adversarialChecks")
    if not isinstance(checks, list) or not checks:
        issues.append("adversarialChecks must be a non-empty array")
    elif not any("does not" in item.lower() and "submit" in item.lower() for item in checks if isinstance(item, str)):
        issues.append("adversarialChecks must state the helper does not submit browser actions")
    return issues


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_apply_path = Path(args.source_apply_result).expanduser().resolve()
    source_apply = load_json(source_apply_path, "create-preflight source rehearsal apply result")
    require_source_apply_result(source_apply)

    bundle_path = Path(args.created_site_evidence_bundle or require_artifact(source_apply, "createdSiteEvidenceBundle")).expanduser().resolve()
    filled_template_path = Path(args.filled_created_site_evidence_template).expanduser().resolve()
    if not filled_template_path.exists():
        raise SystemExit(f"ERROR: filled created-site evidence template does not exist: {filled_template_path}")
    confirmation_path = require_artifact(source_apply, "confirmation")
    package_path, review_packet_path = confirmed_source_paths(confirmation_path)

    apply_output_dir = output_dir / "created-site-evidence-apply"
    created_site_evidence_output = output_dir / "created-site-evidence.json"
    bundle_summary = apply_created_site_bundle(
        argparse.Namespace(
            bundle=str(bundle_path),
            filled_template=str(filled_template_path),
            output_dir=str(apply_output_dir),
            created_site_evidence_output=str(created_site_evidence_output),
            require_output_under_output_dir=False,
            prepare_created_site_schema_capture=True,
            artifact_readiness=require_artifact(source_apply, "artifactReadiness"),
            package=package_path,
            review_packet=review_packet_path,
            confirmation=confirmation_path,
            execution_plan=require_artifact(source_apply, "executionPlan"),
            authorization_dir=args.authorization_dir,
            theme_target=args.theme_target,
            json=False,
        )
    )

    artifacts = as_dict(bundle_summary.get("artifacts"))
    source_execution_status_path = artifacts.get("sourceExecutionStatus", "")
    next_stage = ""
    if isinstance(source_execution_status_path, str) and source_execution_status_path.strip():
        source_execution_status = load_json(Path(source_execution_status_path), "source execution status")
        current_stage = source_execution_status.get("currentStage")
        if isinstance(current_stage, str):
            next_stage = current_stage
    summary = {
        "kind": "allincms_created_site_evidence_source_rehearsal_apply",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "preparedOnly": True,
        "sourceApplyResult": str(source_apply_path),
        "createdSiteEvidenceBundle": str(bundle_path),
        "filledCreatedSiteEvidenceTemplate": str(filled_template_path),
        "status": "created_site_evidence_applied",
        "targetMode": "new_site",
        "readyForBrowserStage": next_stage,
        "createdSiteKey": bundle_summary.get("createdSiteKey", ""),
        "frontendBaseUrl": bundle_summary.get("frontendBaseUrl", ""),
        "createdSiteSubmittedValues": bundle_summary.get("createdSiteSubmittedValues", {}),
        "createdSiteEvidence": artifacts.get("createdSiteEvidence", ""),
        "createdSiteSchemaCapturePrepared": bundle_summary.get("createdSiteSchemaCapturePrepared") is True,
        "sourceExecutionStatus": artifacts.get("sourceExecutionStatus", ""),
        "sourceNextStageHandoff": artifacts.get("sourceNextStageHandoff", ""),
        "artifacts": {
            "createdSiteEvidenceBundleApplySummary": str(apply_output_dir / "created-site-evidence-bundle-apply-summary.json"),
            "createdSiteEvidence": artifacts.get("createdSiteEvidence", ""),
            "createdSiteSchemaCaptureSummary": artifacts.get("createdSiteSchemaCaptureSummary", ""),
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
            "upstreamCreatePreflightSourceApply": str(source_apply_path),
            "upstreamCreateSiteHandoff": optional_artifact(source_apply, "createSiteHandoff"),
            "upstreamCreateSiteRunbook": optional_artifact(source_apply, "createSiteRunbook"),
        },
        "nextAction": bundle_summary.get("nextAction", ""),
        "adversarialChecks": [
            "This helper applies already-filled, redacted post-create browser evidence only.",
            "It does not submit the create-site form, save content, upload media, publish, delete, bind domains, or authorize browser mutation.",
            "It reuses the created-site evidence bundle validator so the filled proof must match the source context, gate proof, submitted site values, and required module routes.",
            "It immediately prepares created-site schema/pages/site-info/taxonomy artifacts so operators do not hand-stitch package, confirmation, execution-plan, and artifact-readiness paths after browser submit.",
        ],
    }
    issues = validate_apply_summary(summary)
    if issues:
        raise SystemExit("ERROR: invalid created-site evidence source rehearsal apply summary:\n- " + "\n- ".join(issues))
    write_json(output_dir / "created-site-evidence-source-rehearsal-apply.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply filled created-site evidence to a source-file rehearsal chain.")
    parser.add_argument("--source-apply-result", required=True)
    parser.add_argument("--filled-created-site-evidence-template", required=True)
    parser.add_argument("--created-site-evidence-bundle", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote created-site source rehearsal apply summary: {Path(args.output_dir).resolve() / 'created-site-evidence-source-rehearsal-apply.json'}")
        print(f"readyForBrowserStage={summary['readyForBrowserStage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
