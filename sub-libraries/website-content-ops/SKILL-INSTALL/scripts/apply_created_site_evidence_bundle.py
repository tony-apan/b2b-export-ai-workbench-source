#!/usr/bin/env python3
"""Apply a filled created-site evidence bundle into run evidence and next prep."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from make_created_site_evidence import upgrade_evidence
from prepare_created_site_evidence_bundle import validate_bundle
from prepare_created_site_schema_capture import build as prepare_schema_capture


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


def as_list_of_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SystemExit(f"ERROR: filled evidence {label} must be a non-empty string array")
    return [item.strip() for item in value]


def require_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or value.startswith("<"):
        raise SystemExit(f"ERROR: filled evidence {key} must be a concrete non-placeholder string")
    return value.strip()


def require_bool_true(data: dict[str, Any], key: str) -> None:
    if data.get(key) is not True:
        raise SystemExit(f"ERROR: filled evidence {key} must be true")


def concrete_setup_evidence(data: dict[str, Any], key: str) -> str:
    setup = data.get("setupPageEvidence")
    if not isinstance(setup, dict):
        raise SystemExit("ERROR: filled evidence setupPageEvidence must be an object")
    value = setup.get(key)
    if not isinstance(value, str) or not value.strip() or value.startswith("<"):
        raise SystemExit(f"ERROR: filled evidence setupPageEvidence.{key} must be concrete")
    return value.strip()


def validate_filled_template(data: dict[str, Any], bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != "allincms_created_site_browser_evidence_fill_template":
        issues.append("filled template kind must be allincms_created_site_browser_evidence_fill_template")
    if data.get("action") != "create_site":
        issues.append("filled template action must be create_site")
    if data.get("preflight") != bundle.get("preflight"):
        issues.append("filled template preflight must match bundle preflight")
    if data.get("createSiteHandoff") != bundle.get("createSiteHandoff"):
        issues.append("filled template createSiteHandoff must match bundle createSiteHandoff")
    if data.get("createdSiteEvidenceOutput") != bundle.get("createdSiteEvidenceOutput"):
        issues.append("filled template createdSiteEvidenceOutput must match bundle output")
    if data.get("authorizationRecord") != bundle.get("authorizationRecord"):
        issues.append("filled template authorizationRecord must match bundle authorizationRecord")
    auth_record = data.get("authorizationRecord")
    if not isinstance(auth_record, str) or not auth_record.strip() or auth_record.startswith("<"):
        issues.append("filled template authorizationRecord must be concrete")
    elif not Path(auth_record).exists():
        issues.append("filled template authorizationRecord must point to an existing authorization record")
    if data.get("preMutationGateStatus") != "passed":
        issues.append("filled template preMutationGateStatus must be passed")
    if data.get("gateReadyForBrowserSubmit") is not True:
        issues.append("filled template gateReadyForBrowserSubmit must be true")
    for key in ("createdSiteKey", "siteCardEvidence", "backendEvidence", "frontendEvidence", "authorizationSource"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or value.startswith("<"):
            issues.append(f"filled template {key} must be concrete")
    submitted_values = data.get("submittedValues")
    if not isinstance(submitted_values, dict):
        issues.append("filled template submittedValues must be an object")
    else:
        bundle_values = bundle.get("submittedValues")
        if not isinstance(bundle_values, dict):
            bundle_values = {}
        for key in ("name", "description"):
            value = submitted_values.get(key)
            if not isinstance(value, str) or not value.strip() or value.startswith("<"):
                issues.append(f"filled template submittedValues.{key} must be concrete")
            elif bundle_values.get(key) and value != bundle_values[key]:
                issues.append(f"filled template submittedValues.{key} must match the confirmed siteProposal")
    for legacy_key, value_key in (("submittedSiteName", "name"), ("submittedSiteDescription", "description")):
        value = data.get(legacy_key)
        expected = submitted_values.get(value_key) if isinstance(submitted_values, dict) else None
        if value is not None and value != expected:
            issues.append(f"filled template {legacy_key} must match submittedValues.{value_key}")
    for key in ("listColumns", "editFields", "moduleRoutes", "submittedFields"):
        value = data.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() and not item.strip().startswith("<") for item in value):
            issues.append(f"filled template {key} must contain concrete strings")
    setup = data.get("setupPageEvidence")
    if not isinstance(setup, dict):
        issues.append("filled template setupPageEvidence must be an object")
    else:
        for key in ("siteInfo", "domains", "media", "themes", "routes", "forms", "tracking"):
            value = setup.get(key)
            if not isinstance(value, str) or not value.strip() or value.startswith("<"):
                issues.append(f"filled template setupPageEvidence.{key} must be concrete")
    for key in ("forbiddenNeighborActionsVerified", "stopConditionMet"):
        if data.get(key) is not True:
            issues.append(f"filled template {key} must be true")
    for key in ("contentGoalCoverage", "contentCounts", "contentQualityReview", "wikiReview", "confirmationDecisionMatrix"):
        if data.get(key) != bundle.get(key):
            issues.append(f"filled template {key} must match bundle source context")
    return issues


def build_created_site_evidence(filled: dict[str, Any]) -> dict[str, Any]:
    preflight = load_json(Path(require_text(filled, "preflight")), "preflight")
    setup = filled.get("setupPageEvidence")
    if not isinstance(setup, dict):
        raise SystemExit("ERROR: setupPageEvidence must be an object")
    require_bool_true(filled, "forbiddenNeighborActionsVerified")
    require_bool_true(filled, "stopConditionMet")
    return upgrade_evidence(
        preflight,
        created_site_key=require_text(filled, "createdSiteKey"),
        content_type=require_text(filled, "contentTypeForInitialInspection"),
        list_columns=as_list_of_strings(filled.get("listColumns"), "listColumns"),
        edit_fields=as_list_of_strings(filled.get("editFields"), "editFields"),
        site_card_evidence=require_text(filled, "siteCardEvidence"),
        backend_evidence=require_text(filled, "backendEvidence"),
        frontend_evidence=require_text(filled, "frontendEvidence"),
        site_info_evidence=concrete_setup_evidence(filled, "siteInfo"),
        domains_evidence=concrete_setup_evidence(filled, "domains"),
        media_evidence=concrete_setup_evidence(filled, "media"),
        themes_evidence=concrete_setup_evidence(filled, "themes"),
        routes_evidence=concrete_setup_evidence(filled, "routes"),
        forms_evidence=concrete_setup_evidence(filled, "forms"),
        tracking_evidence=concrete_setup_evidence(filled, "tracking"),
        module_routes=as_list_of_strings(filled.get("moduleRoutes"), "moduleRoutes"),
        submitted_fields=as_list_of_strings(filled.get("submittedFields"), "submittedFields"),
        authorization_source=require_text(filled, "authorizationSource"),
        repo_check_passed=True,
        repo_check_note=None,
        submitted_values=filled.get("submittedValues") if isinstance(filled.get("submittedValues"), dict) else None,
    )


def schema_summary_artifacts(schema_summary: dict[str, Any] | None) -> dict[str, str]:
    if not schema_summary:
        return {
            "createdSiteArtifactBinding": "",
            "boundArtifactReadiness": "",
            "productsBoundDraftManifest": "",
            "postsBoundDraftManifest": "",
            "schemaCaptureHandoff": "",
            "schemaCaptureProgress": "",
            "pagesSiteInfoHandoff": "",
            "pagesSiteInfoEvidenceBundle": "",
            "taxonomyHandoff": "",
            "taxonomyEvidenceBundle": "",
            "sourceExecutionStatus": "",
            "sourceNextStageHandoff": "",
        }
    artifacts = schema_summary.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("ERROR: created-site schema-capture summary missing artifacts")
    keys = (
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
    copied: dict[str, str] = {}
    missing: list[str] = []
    for key in keys:
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
        else:
            copied[key] = value
    if missing:
        raise SystemExit("ERROR: created-site schema-capture summary missing artifacts: " + ", ".join(missing))
    return copied


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_json(Path(args.bundle), "created-site evidence bundle")
    bundle_issues = validate_bundle(bundle)
    if bundle_issues:
        raise SystemExit("ERROR: created-site evidence bundle invalid:\n- " + "\n- ".join(bundle_issues))
    filled = load_json(Path(args.filled_template), "filled created-site evidence template")
    filled_issues = validate_filled_template(filled, bundle)
    if filled_issues:
        raise SystemExit("ERROR: filled created-site evidence template invalid:\n- " + "\n- ".join(filled_issues))
    try:
        created_site_evidence = build_created_site_evidence(filled)
    except ValueError as exc:
        raise SystemExit(f"ERROR: filled created-site evidence is invalid: {exc}") from None
    created_site_evidence_path = Path(args.created_site_evidence_output or bundle["createdSiteEvidenceOutput"]).expanduser().resolve()
    if args.require_output_under_output_dir and output_dir not in created_site_evidence_path.parents:
        raise SystemExit("ERROR: created-site evidence output must be under --output-dir")
    write_json(created_site_evidence_path, created_site_evidence)

    schema_summary: dict[str, Any] | None = None
    schema_output_dir = output_dir / "created-site-schema-capture"
    if args.prepare_created_site_schema_capture:
        required = {
            "--artifact-readiness": args.artifact_readiness,
            "--package": args.package,
            "--confirmation": args.confirmation,
            "--execution-plan": args.execution_plan,
        }
        missing = [flag for flag, value in required.items() if not value]
        if missing:
            raise SystemExit(
                "ERROR: --prepare-created-site-schema-capture requires " + ", ".join(missing)
            )
        schema_summary = prepare_schema_capture(
            SimpleNamespace(
                artifact_readiness=args.artifact_readiness,
                created_site_evidence=str(created_site_evidence_path),
                package=args.package,
                review_packet=args.review_packet,
                confirmation=args.confirmation,
                execution_plan=args.execution_plan,
                authorization_dir=args.authorization_dir,
                theme_target=args.theme_target,
                output_dir=str(schema_output_dir),
                json=False,
            )
        )

    downstream_artifacts = schema_summary_artifacts(schema_summary)
    summary = {
        "kind": "allincms_created_site_evidence_bundle_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "sourceBundle": args.bundle,
        "filledTemplate": args.filled_template,
        "createdSiteEvidence": str(created_site_evidence_path),
        "createdSiteKey": created_site_evidence.get("siteIdentity", {}).get("siteKey", ""),
        "frontendBaseUrl": created_site_evidence.get("siteIdentity", {}).get("frontendBaseUrl", ""),
        "createdSiteSubmittedValues": created_site_evidence.get("siteCreation", {}).get("submittedValues", {}),
        "contentGoalCoverage": bundle.get("contentGoalCoverage", {}),
        "contentCounts": bundle.get("contentCounts", {}),
        "contentQualityReview": bundle.get("contentQualityReview", {}),
        "wikiReview": bundle.get("wikiReview", {}),
        "confirmationDecisionMatrix": bundle.get("confirmationDecisionMatrix", []),
        "validation": {
            "bundleIssues": bundle_issues,
            "filledTemplateIssues": filled_issues,
        },
        "artifacts": {
            "createdSiteEvidence": str(created_site_evidence_path),
            "createdSiteSchemaCaptureSummary": str(schema_output_dir / "created-site-schema-capture-preparation-summary.json")
            if schema_summary
            else "",
            **downstream_artifacts,
        },
        "createdSiteSchemaCapturePrepared": schema_summary is not None,
        "nextAction": (
            schema_summary.get("nextAction")
            if schema_summary
            else "run prepare_created_site_schema_capture.py with the created-site evidence and confirmed artifact context"
        ),
        "adversarialChecks": [
            "This helper applies redacted browser proof only; it does not submit create-site, save content, upload, publish, or bind domains.",
            "The filled template must match the evidence bundle source context before created-site evidence is written.",
            "Created-site schema capture preparation, when requested, remains local-only and does not create probes or upload content.",
        ],
    }
    write_json(output_dir / "created-site-evidence-bundle-apply-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a filled AllinCMS created-site evidence bundle.")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--filled-template", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--created-site-evidence-output", default="")
    parser.add_argument("--require-output-under-output-dir", action="store_true")
    parser.add_argument("--prepare-created-site-schema-capture", action="store_true")
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote created-site evidence: {summary['createdSiteEvidence']}")
        print(f"createdSiteSchemaCapturePrepared={summary['createdSiteSchemaCapturePrepared']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
