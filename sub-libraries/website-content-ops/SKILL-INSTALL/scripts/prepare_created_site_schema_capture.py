#!/usr/bin/env python3
"""Prepare schema-capture handoff after a created site is verified."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from bind_created_site_to_artifacts import build_binding, validate_binding
from build_schema_capture_handoff import build_handoff as build_schema_handoff
from build_schema_capture_handoff import validate_handoff as validate_schema_handoff
from prepare_pages_site_info_evidence_bundle import build_bundle as build_pages_site_info_evidence_bundle
from prepare_pages_site_info_evidence_bundle import validate_bundle as validate_pages_site_info_evidence_bundle
from prepare_pages_site_info_execution import build as build_pages_site_info_handoff
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from prepare_taxonomy_evidence_bundle import build_bundle as build_taxonomy_evidence_bundle
from prepare_taxonomy_evidence_bundle import validate_bundle as validate_taxonomy_evidence_bundle
from prepare_taxonomy_execution import build as build_taxonomy_handoff
from summarize_schema_capture_progress import summarize as summarize_schema_progress
from summarize_source_execution_status import summarize as summarize_source_execution


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "bound_dir": output_dir / "created-site-bound-artifacts",
        "binding": output_dir / "created-site-artifact-binding.json",
        "schema_dir": output_dir / "schema-capture",
        "schema_handoff": output_dir / "schema-capture-handoff.json",
        "pages_site_info_dir": output_dir / "pages-site-info",
        "pages_site_info_handoff": output_dir / "pages-site-info" / "pages-site-info-browser-handoff.json",
        "pages_site_info_summary": output_dir / "pages-site-info" / "pages-site-info-preparation-summary.json",
        "pages_site_info_evidence_bundle_dir": output_dir / "pages-site-info" / "pages-site-info-evidence-bundle",
        "pages_site_info_evidence_bundle": output_dir / "pages-site-info" / "pages-site-info-evidence-bundle" / "evidence-bundle.json",
        "taxonomy_dir": output_dir / "taxonomy",
        "taxonomy_handoff": output_dir / "taxonomy" / "taxonomy-execution-handoff.json",
        "taxonomy_summary": output_dir / "taxonomy" / "taxonomy-execution-preparation-summary.json",
        "taxonomy_evidence_bundle_dir": output_dir / "taxonomy" / "taxonomy-evidence-bundle",
        "taxonomy_evidence_bundle": output_dir / "taxonomy" / "taxonomy-evidence-bundle" / "evidence-bundle.json",
        "schema_progress": output_dir / "schema-capture-progress.json",
        "source_status": output_dir / "source-execution-status.after-created-site.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-created-site.json",
        "summary": output_dir / "created-site-schema-capture-preparation-summary.json",
    }


def first_schema_next_action(progress: dict[str, Any]) -> str:
    results = progress.get("results")
    if not isinstance(results, list):
        return "inspect schema-capture progress output"
    for item in results:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        content_type = item.get("contentType", "content")
        if status == "ready_for_create_probe":
            return f"request action-time create-probe authorization for {content_type}"
        if status == "blocked_readonly_preflight":
            return f"refresh {content_type} read-only list/edit preflight, merge it, then rebuild schema-capture handoff"
    return str(progress.get("nextAction") or "continue schema-capture queue")


def source_or_schema_next_action(source_status: dict[str, Any], schema_progress: dict[str, Any]) -> str:
    current = source_status.get("currentStage")
    next_action = source_status.get("nextAction")
    if isinstance(current, str) and current not in {"schema_capture_handoff", "schema_manifests", "complete"}:
        return str(next_action or f"complete source execution stage {current}")
    return first_schema_next_action(schema_progress)


SOURCE_CONTEXT_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
    "createdSiteSubmittedValues",
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "wikiReview",
    "confirmationDecisionMatrix",
)


def source_context_from_binding(binding: dict[str, Any]) -> dict[str, Any]:
    return {key: binding.get(key) for key in SOURCE_CONTEXT_KEYS if key in binding}


def content_counts_from_binding(binding: dict[str, Any]) -> dict[str, int]:
    counts = binding.get("contentCounts")
    if not isinstance(counts, dict):
        raise SystemExit("ERROR: created-site binding missing contentCounts")
    result: dict[str, int] = {}
    for key in ("pages", "products", "posts", "forms", "media", "navigationItems", "siteInfoFields"):
        value = counts.get(key)
        if not isinstance(value, int) or value < 0:
            raise SystemExit(f"ERROR: created-site binding contentCounts.{key} must be a non-negative integer")
        result[key] = value
    return result


def load_json_file(path: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def review_packet_from_confirmation(confirmation_path: str) -> str:
    if not confirmation_path:
        return ""
    confirmation = load_json_file(confirmation_path, "confirmation")
    value = confirmation.get("sourceReviewPacket")
    return value if isinstance(value, str) else ""


def confirmed_plan_paths(artifact_readiness_path: str) -> tuple[str, str, str, str]:
    readiness = load_json_file(artifact_readiness_path, "artifact readiness")
    artifacts = readiness.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("ERROR: artifact readiness missing artifacts")
    pages_plan = artifacts.get("pagesPlan")
    site_info_plan = artifacts.get("siteInfoPlan")
    navigation_plan = artifacts.get("navigationPlan")
    taxonomy_plan = artifacts.get("taxonomyPlan")
    if not isinstance(pages_plan, str) or not pages_plan.strip():
        raise SystemExit("ERROR: artifact readiness missing artifacts.pagesPlan")
    if not isinstance(site_info_plan, str) or not site_info_plan.strip():
        raise SystemExit("ERROR: artifact readiness missing artifacts.siteInfoPlan")
    if not isinstance(navigation_plan, str) or not navigation_plan.strip():
        raise SystemExit("ERROR: artifact readiness missing artifacts.navigationPlan")
    if not isinstance(taxonomy_plan, str) or not taxonomy_plan.strip():
        raise SystemExit("ERROR: artifact readiness missing artifacts.taxonomyPlan")
    return pages_plan, site_info_plan, navigation_plan, taxonomy_plan


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    binding = build_binding(
        SimpleNamespace(
            artifact_readiness=args.artifact_readiness,
            created_site_evidence=args.created_site_evidence,
            output_dir=str(paths["bound_dir"]),
            output=str(paths["binding"]),
            json=False,
        )
    )
    binding_issues = validate_binding(binding)
    if binding_issues:
        raise SystemExit("ERROR: generated created-site binding is invalid:\n- " + "\n- ".join(binding_issues))
    write_json(paths["binding"], binding)
    content_counts = content_counts_from_binding(binding)

    schema_handoff = build_schema_handoff(
        SimpleNamespace(
            created_site_binding=str(paths["binding"]),
            created_site_evidence=args.created_site_evidence,
            output_dir=str(paths["schema_dir"]),
            authorization_dir=args.authorization_dir,
            output=str(paths["schema_handoff"]),
            json=False,
        )
    )
    schema_handoff_issues = validate_schema_handoff(schema_handoff)
    if schema_handoff_issues:
        raise SystemExit("ERROR: generated schema-capture handoff is invalid:\n- " + "\n- ".join(schema_handoff_issues))
    write_json(paths["schema_handoff"], schema_handoff)

    pages_plan, site_info_plan, navigation_plan, taxonomy_plan = confirmed_plan_paths(args.artifact_readiness)
    pages_site_info_summary = build_pages_site_info_handoff(
        SimpleNamespace(
            pages_plan=pages_plan,
            site_info_plan=site_info_plan,
            navigation_plan=navigation_plan,
            preflight=args.created_site_evidence,
            output_dir=str(paths["pages_site_info_dir"]),
            theme_target=args.theme_target,
            json=False,
        )
    )
    pages_site_info_handoff = load_json_file(str(paths["pages_site_info_handoff"]), "pages/site-info handoff")
    pages_site_info_handoff.update(source_context_from_binding(binding))
    write_json(paths["pages_site_info_handoff"], pages_site_info_handoff)
    pages_site_info_evidence_bundle = build_pages_site_info_evidence_bundle(
        handoff=pages_site_info_handoff,
        handoff_path=str(paths["pages_site_info_handoff"]),
        output_dir=paths["pages_site_info_evidence_bundle_dir"],
    )
    pages_site_info_evidence_bundle_issues = validate_pages_site_info_evidence_bundle(pages_site_info_evidence_bundle)
    if pages_site_info_evidence_bundle_issues:
        raise SystemExit(
            "ERROR: generated pages/site-info evidence bundle is invalid:\n- "
            + "\n- ".join(pages_site_info_evidence_bundle_issues)
        )
    write_json(paths["pages_site_info_evidence_bundle"], pages_site_info_evidence_bundle)
    taxonomy_summary = build_taxonomy_handoff(
        SimpleNamespace(
            taxonomy_plan=taxonomy_plan,
            preflight=args.created_site_evidence,
            output_dir=str(paths["taxonomy_dir"]),
            json=False,
        )
    )
    taxonomy_handoff = load_json_file(str(paths["taxonomy_handoff"]), "taxonomy handoff")
    taxonomy_handoff.update(source_context_from_binding(binding))
    write_json(paths["taxonomy_handoff"], taxonomy_handoff)
    taxonomy_evidence_bundle = build_taxonomy_evidence_bundle(
        handoff=taxonomy_handoff,
        handoff_path=str(paths["taxonomy_handoff"]),
        output_dir=paths["taxonomy_evidence_bundle_dir"],
    )
    taxonomy_evidence_bundle_issues = validate_taxonomy_evidence_bundle(taxonomy_evidence_bundle)
    if taxonomy_evidence_bundle_issues:
        raise SystemExit(
            "ERROR: generated taxonomy evidence bundle is invalid:\n- "
            + "\n- ".join(taxonomy_evidence_bundle_issues)
        )
    write_json(paths["taxonomy_evidence_bundle"], taxonomy_evidence_bundle)

    schema_progress = summarize_schema_progress(
        SimpleNamespace(
            schema_capture_handoff=str(paths["schema_handoff"]),
            create_evidence=[],
            save_handoff=[],
            save_runbook=[],
            save_capture=[],
            base_run_evidence=[],
            schema_manifest=[],
            output=str(paths["schema_progress"]),
            fail_on_incomplete=False,
            json=False,
        )
    )
    write_json(paths["schema_progress"], schema_progress)

    source_status = summarize_source_execution(
        SimpleNamespace(
            package=args.package,
            review_packet=args.review_packet or review_packet_from_confirmation(args.confirmation),
            confirmation=args.confirmation,
            execution_plan=args.execution_plan,
            artifact_readiness=args.artifact_readiness,
            create_site_handoff="",
            created_site_binding=str(paths["binding"]),
            pages_site_info_handoff=str(paths["pages_site_info_handoff"]),
            pages_site_info_evidence="",
            pages_site_info_validation="",
            taxonomy_handoff=str(paths["taxonomy_handoff"]),
            taxonomy_evidence="",
            taxonomy_validation="",
            schema_capture_handoff=str(paths["schema_handoff"]),
            upload_readiness="",
            sample_evidence=[],
            batch_evidence="",
            batch_validation="",
            launch_acceptance="",
        )
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
        created_site_evidence=args.created_site_evidence,
        authorization_dir=args.authorization_dir,
        theme_target=args.theme_target,
    )

    ready_count = int(schema_handoff.get("readyForCreateProbeAuthorizationCount", 0))
    blocked_count = int(schema_handoff.get("blockedByReadonlyPreflightCount", 0))
    summary = {
        "kind": "allincms_created_site_schema_capture_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": binding.get("siteKey"),
        "frontendBaseUrl": binding.get("frontendBaseUrl"),
        "contentGoalCoverage": binding.get("contentGoalCoverage"),
        "contentCounts": content_counts,
        "contentQualityReview": binding.get("contentQualityReview"),
        "wikiReview": binding.get("wikiReview"),
        "confirmationDecisionMatrix": binding.get("confirmationDecisionMatrix", []),
        "sourcePackageSha256": binding.get("sourcePackageSha256"),
        "sourceReviewPacketSha256": binding.get("sourceReviewPacketSha256"),
        "schemaCaptureStatus": schema_handoff.get("overallStatus"),
        "readyForCreateProbeAuthorizationCount": ready_count,
        "blockedByReadonlyPreflightCount": blocked_count,
        "artifacts": {
            "createdSiteArtifactBinding": str(paths["binding"]),
            "boundArtifactReadiness": binding.get("boundArtifacts", {}).get("artifactReadiness", ""),
            "productsBoundDraftManifest": binding.get("boundArtifacts", {}).get("productsManifest", ""),
            "postsBoundDraftManifest": binding.get("boundArtifacts", {}).get("postsManifest", ""),
            "schemaCaptureHandoff": str(paths["schema_handoff"]),
            "pagesSiteInfoHandoff": str(paths["pages_site_info_handoff"]),
            "pagesSiteInfoSummary": str(paths["pages_site_info_summary"]),
            "pagesSiteInfoEvidenceBundle": str(paths["pages_site_info_evidence_bundle"]),
            "taxonomyHandoff": str(paths["taxonomy_handoff"]),
            "taxonomySummary": str(paths["taxonomy_summary"]),
            "taxonomyEvidenceBundle": str(paths["taxonomy_evidence_bundle"]),
            "schemaCaptureProgress": str(paths["schema_progress"]),
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {
            "bindingIssues": binding_issues,
            "schemaHandoffIssues": schema_handoff_issues,
            "pagesSiteInfoEvidenceBundleIssues": pages_site_info_evidence_bundle_issues,
            "taxonomyEvidenceBundleIssues": taxonomy_evidence_bundle_issues,
        },
        "adversarialChecks": [
            "This step binds created-site identity and prepares schema-capture only; it does not create probes.",
            "Pages/site-info handoff is prepared-only; it does not save settings, create pages, save design, publish, enable, bind routes, or verify frontend.",
            "Pages/site-info evidence bundle is scaffolding only; it does not authorize or prove page/site-info browser mutations.",
            "Taxonomy handoff is prepared-only; it does not create or map categories/tags and must be validated before taxonomy-dependent products/posts upload.",
            "Taxonomy evidence bundle is scaffolding only; it does not authorize or prove category/tag create-or-map actions.",
            "Bound products/posts manifests remain schemaVerified=false.",
            "Products and posts keep separate preflight/schema-capture states.",
            "A ready create-probe command still requires current user action-time authorization and pre-mutation gate.",
            "A blocked content type needs same-site read-only list/edit preflight merged before create-probe authorization.",
            "Source next-stage handoff is generated from refreshed source status and must be followed before later browser or helper stages.",
        ],
        "taxonomyStatus": taxonomy_summary.get("readyForBrowserStage"),
        "nextAction": source_or_schema_next_action(source_status, schema_progress),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
    }
    submitted_values = binding.get("createdSiteSubmittedValues")
    if isinstance(submitted_values, dict):
        summary["createdSiteSubmittedValues"] = submitted_values
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare created-site schema-capture artifacts.")
    parser.add_argument("--artifact-readiness", required=True)
    parser.add_argument("--created-site-evidence", required=True)
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--authorization-dir", default="")
    parser.add_argument("--theme-target", default="", help="Optional concrete or templated theme page-list URL for pages/site-info handoff")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote created-site schema-capture preparation summary: {summary['artifacts']['schemaCaptureProgress']}")
        print(
            f"schemaCaptureStatus={summary['schemaCaptureStatus']} "
            f"ready={summary['readyForCreateProbeAuthorizationCount']} "
            f"blocked={summary['blockedByReadonlyPreflightCount']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
