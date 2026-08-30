#!/usr/bin/env python3
"""Prepare execution artifacts after a user confirms a source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from make_source_package_confirmation import build_confirmation
from validate_source_package_confirmation import validate_confirmation_with_review_packet
from build_confirmed_site_execution_plan import build_plan, validate_plan
from export_confirmed_site_artifacts import build_artifacts, validate_readiness
from build_confirmed_create_site_handoff import build_handoff as build_create_site_handoff
from build_confirmed_create_site_handoff import validate_handoff as validate_create_site_handoff
from build_confirmed_create_site_handoff import build_validation_report as build_create_site_handoff_validation
from build_create_site_runbook import build_runbook as build_create_site_runbook
from build_create_site_runbook import validate_runbook as validate_create_site_runbook
from build_create_site_runbook import build_validation_report as build_create_site_runbook_validation
from make_created_site_evidence_brief import build as build_created_site_evidence_brief
from make_create_site_preflight_brief import build as build_create_site_preflight_brief
from make_create_site_preflight_brief import build_validation_report as build_create_site_preflight_brief_validation
from prepare_created_site_evidence_bundle import build_bundle as build_created_site_evidence_bundle
from prepare_created_site_evidence_bundle import validate_bundle as validate_created_site_evidence_bundle
from prepare_created_site_evidence_bundle import build_validation_report as build_created_site_evidence_bundle_validation
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_execution_status
from validate_source_package_review_packet import load_json as load_review_json
from validate_source_site_package import load_json as load_package_json


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
        "confirmation": output_dir / "confirmation-record.json",
        "execution_plan": output_dir / "confirmed-site-execution-plan.json",
        "artifacts_dir": output_dir / "confirmed-artifacts",
        "artifact_readiness": output_dir / "confirmed-artifacts" / "artifact-readiness.json",
        "create_site_preflight_brief": output_dir / "create-site-preflight-brief.json",
        "create_site_preflight_brief_validation": output_dir / "create-site-preflight-brief-validation.json",
        "create_site_preflight": output_dir / "create-site-preflight.json",
        "create_site_handoff": output_dir / "confirmed-create-site-handoff.json",
        "create_site_handoff_validation": output_dir / "confirmed-create-site-handoff-validation.json",
        "create_site_runbook": output_dir / "create-site-browser-runbook.json",
        "create_site_runbook_validation": output_dir / "create-site-browser-runbook-validation.json",
        "created_site_evidence_brief": output_dir / "created-site-evidence-brief.json",
        "created_site_evidence": output_dir / "created-site-evidence.json",
        "created_site_evidence_bundle_dir": output_dir / "created-site-evidence-bundle",
        "created_site_evidence_bundle": output_dir / "created-site-evidence-bundle" / "evidence-bundle.json",
        "created_site_evidence_bundle_validation": output_dir
        / "created-site-evidence-bundle"
        / "evidence-bundle-validation.json",
        "execution_status": output_dir / "source-execution-status.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.json",
        "summary": output_dir / "confirmed-site-execution-preparation-summary.json",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    package = load_package_json(Path(args.package))
    review_packet = load_review_json(Path(args.review_packet), "review packet")
    confirmation = build_confirmation(
        SimpleNamespace(
            package=args.package,
            review_packet=args.review_packet,
            source_review_objective_coverage=getattr(args, "source_review_objective_coverage", "") or "",
            user_confirmation_text=args.user_confirmation_text,
            accepted_fields=args.accepted_fields,
            accepted_deferral=args.accepted_deferral,
            notes=args.notes,
            output=str(paths["confirmation"]),
            json=False,
        )
    )
    confirmation_issues = validate_confirmation_with_review_packet(confirmation, package, review_packet)
    if confirmation_issues:
        raise SystemExit("ERROR: generated confirmation is invalid:\n- " + "\n- ".join(confirmation_issues))
    write_json(paths["confirmation"], confirmation)

    plan = build_plan(
        SimpleNamespace(
            package=args.package,
            confirmation=str(paths["confirmation"]),
            target_mode=args.target_mode,
            site_key=args.site_key,
            output=str(paths["execution_plan"]),
            json=False,
        )
    )
    plan_issues = validate_plan(plan)
    if plan_issues:
        raise SystemExit("ERROR: generated execution plan is invalid:\n- " + "\n- ".join(plan_issues))
    write_json(paths["execution_plan"], plan)

    readiness = build_artifacts(
        SimpleNamespace(
            package=args.package,
            confirmation=str(paths["confirmation"]),
            execution_plan=str(paths["execution_plan"]),
            site_key=args.site_key,
            frontend_base_url=args.frontend_base_url,
            output_dir=str(paths["artifacts_dir"]),
            json=False,
        )
    )
    readiness_issues = validate_readiness(readiness)
    if readiness_issues:
        raise SystemExit("ERROR: generated artifact readiness is invalid:\n- " + "\n- ".join(readiness_issues))

    create_handoff: dict[str, Any] | None = None
    create_handoff_issues: list[str] = []
    create_handoff_validation: dict[str, Any] | None = None
    create_runbook: dict[str, Any] | None = None
    create_runbook_issues: list[str] = []
    create_runbook_validation: dict[str, Any] | None = None
    created_site_evidence_bundle: dict[str, Any] | None = None
    created_site_evidence_bundle_issues: list[str] = []
    created_site_evidence_bundle_validation: dict[str, Any] | None = None
    preflight_brief: dict[str, Any] | None = None
    preflight_brief_validation: dict[str, Any] | None = None
    created_site_evidence_brief: dict[str, Any] | None = None
    if args.target_mode == "new_site" and args.create_preflight:
        create_handoff = build_create_site_handoff(
            SimpleNamespace(
                package=args.package,
                review_packet=args.review_packet,
                confirmation=str(paths["confirmation"]),
                execution_plan=str(paths["execution_plan"]),
                preflight=args.create_preflight,
                authorization_output=args.create_authorization_output,
                output=str(paths["create_site_handoff"]),
                json=False,
            )
        )
        create_handoff_issues = validate_create_site_handoff(create_handoff)
        create_handoff_validation = build_create_site_handoff_validation(
            create_handoff,
            str(paths["create_site_handoff"]),
        )
        write_json(paths["create_site_handoff_validation"], create_handoff_validation)
        if not create_handoff_issues:
            write_json(paths["create_site_handoff"], create_handoff)
            create_runbook = build_create_site_runbook(
                handoff=create_handoff,
                handoff_path=str(paths["create_site_handoff"]),
                authorization_record=args.create_authorization_output,
            )
            create_runbook_issues = validate_create_site_runbook(create_runbook)
            create_runbook_validation = build_create_site_runbook_validation(
                create_runbook,
                str(paths["create_site_runbook"]),
            )
            write_json(paths["create_site_runbook_validation"], create_runbook_validation)
            if not create_runbook_issues:
                write_json(paths["create_site_runbook"], create_runbook)
            created_site_evidence_brief = build_created_site_evidence_brief(
                SimpleNamespace(
                    create_site_handoff=str(paths["create_site_handoff"]),
                    output=str(paths["created_site_evidence_brief"]),
                    created_site_evidence_output=str(paths["created_site_evidence"]),
                    json=False,
                )
            )
            if create_runbook and not create_runbook_issues:
                created_site_evidence_bundle = build_created_site_evidence_bundle(
                    runbook=create_runbook,
                    runbook_path=str(paths["create_site_runbook"]),
                    brief=created_site_evidence_brief,
                    brief_path=str(paths["created_site_evidence_brief"]),
                    output_dir=paths["created_site_evidence_bundle_dir"],
                )
                created_site_evidence_bundle_issues = validate_created_site_evidence_bundle(created_site_evidence_bundle)
                created_site_evidence_bundle_validation = build_created_site_evidence_bundle_validation(
                    created_site_evidence_bundle,
                    str(paths["created_site_evidence_bundle"]),
                )
                write_json(paths["created_site_evidence_bundle_validation"], created_site_evidence_bundle_validation)
                if not created_site_evidence_bundle_issues:
                    write_json(paths["created_site_evidence_bundle"], created_site_evidence_bundle)
    elif args.target_mode == "new_site":
        preflight_brief = build_create_site_preflight_brief(
            SimpleNamespace(
                package=args.package,
                review_packet=args.review_packet,
                confirmation=str(paths["confirmation"]),
                execution_plan=str(paths["execution_plan"]),
                output=str(paths["create_site_preflight_brief"]),
                preflight_output=str(paths["create_site_preflight"]),
                create_authorization_output=args.create_authorization_output,
                json=False,
            )
        )
        preflight_brief_validation = build_create_site_preflight_brief_validation(
            preflight_brief,
            str(paths["create_site_preflight_brief"]),
        )
        write_json(paths["create_site_preflight_brief_validation"], preflight_brief_validation)

    status_args = SimpleNamespace(
        package=args.package,
        review_packet=args.review_packet,
        confirmation=str(paths["confirmation"]),
        execution_plan=str(paths["execution_plan"]),
        artifact_readiness=str(paths["artifact_readiness"]),
        create_site_handoff=str(paths["create_site_handoff"]) if create_handoff and not create_handoff_issues else "",
        created_site_binding="",
        pages_site_info_handoff="",
        pages_site_info_evidence="",
        pages_site_info_validation="",
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff="",
        upload_readiness="",
        sample_evidence=[],
        batch_evidence="",
        batch_validation="",
        forms_media_settings="",
        launch_acceptance="",
    )
    execution_status = summarize_execution_status(status_args)
    write_json(paths["execution_status"], execution_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["execution_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
    )

    ready_for_browser_stage = "create_site_handoff_ready" if create_handoff and not create_handoff_issues else "needs_create_site_preflight"
    if args.target_mode == "existing_site":
        ready_for_browser_stage = "ready_for_existing_site_readonly_refresh"
    summary = {
        "kind": "allincms_confirmed_site_execution_preparation",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "targetMode": args.target_mode,
        "readyForBrowserStage": ready_for_browser_stage,
        "contentGoalOverages": confirmation.get("contentGoalOverages", {}),
        "wikiReview": confirmation.get("wikiReview", {}),
        **(
            {"sourceReviewObjectiveCoverage": confirmation["sourceReviewObjectiveCoverage"]}
            if isinstance(confirmation.get("sourceReviewObjectiveCoverage"), dict)
            else {}
        ),
        "artifacts": {
            "confirmation": str(paths["confirmation"]),
            "executionPlan": str(paths["execution_plan"]),
            "artifactReadiness": str(paths["artifact_readiness"]),
            "productsDraftManifest": readiness.get("artifacts", {}).get("productsManifest", ""),
            "postsDraftManifest": readiness.get("artifacts", {}).get("postsManifest", ""),
            "createSitePreflightBrief": str(paths["create_site_preflight_brief"]) if preflight_brief else "",
            "createSitePreflightBriefValidation": str(paths["create_site_preflight_brief_validation"])
            if preflight_brief_validation
            else "",
            "createSitePreflightTarget": str(paths["create_site_preflight"]) if preflight_brief else "",
            "createSiteHandoff": str(paths["create_site_handoff"]) if create_handoff and not create_handoff_issues else "",
            "createSiteHandoffValidation": str(paths["create_site_handoff_validation"])
            if create_handoff_validation
            else "",
            "createSiteRunbook": str(paths["create_site_runbook"]) if create_runbook and not create_runbook_issues else "",
            "createSiteRunbookValidation": str(paths["create_site_runbook_validation"])
            if create_runbook_validation
            else "",
            "createdSiteEvidenceBrief": str(paths["created_site_evidence_brief"])
            if created_site_evidence_brief
            else "",
            "createdSiteEvidenceBundle": str(paths["created_site_evidence_bundle"])
            if created_site_evidence_bundle and not created_site_evidence_bundle_issues
            else "",
            "createdSiteEvidenceBundleValidation": str(paths["created_site_evidence_bundle_validation"])
            if created_site_evidence_bundle_validation
            else "",
            "createdSiteEvidenceTarget": str(paths["created_site_evidence"]) if created_site_evidence_brief else "",
            "sourceExecutionStatus": str(paths["execution_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
            "summary": str(paths["summary"]),
        },
        "validation": {
            "confirmationIssues": confirmation_issues,
            "executionPlanIssues": plan_issues,
            "artifactReadinessIssues": readiness_issues,
            "createSiteHandoffIssues": create_handoff_issues,
            "createSiteHandoffValidationIssues": create_handoff_validation.get("issues", [])
            if create_handoff_validation
            else [],
            "createSiteRunbookIssues": create_runbook_issues,
            "createSiteRunbookValidationIssues": create_runbook_validation.get("issues", [])
            if create_runbook_validation
            else [],
            "createdSiteEvidenceBundleIssues": created_site_evidence_bundle_issues,
            "createdSiteEvidenceBundleValidationIssues": created_site_evidence_bundle_validation.get("issues", [])
            if created_site_evidence_bundle_validation
            else [],
            "createSitePreflightBriefPrepared": bool(preflight_brief),
            "createSitePreflightBriefIssues": preflight_brief_validation.get("issues", [])
            if preflight_brief_validation
            else [],
            "createSiteRunbookPrepared": bool(create_runbook and not create_runbook_issues),
            "createdSiteEvidenceBriefPrepared": bool(created_site_evidence_brief),
            "createdSiteEvidenceBundlePrepared": bool(created_site_evidence_bundle and not created_site_evidence_bundle_issues),
        },
        "adversarialChecks": [
            "User confirmation is content-intent proof only, not remote mutation authorization.",
            "Exported draft manifests remain schemaVerified=false and must not be uploaded directly.",
            "Create-site handoff is generated only when a fresh create-site preflight is provided.",
            "When create-site preflight is missing, create-site-preflight-brief.json defines the workspace API session evidence to collect before asking for authorization; it does not authorize visible /sites navigation.",
            "When create-site handoff is ready, create-site-browser-runbook.json defines the one-submit browser checklist and remains browserStepsExecutable=false until authorization and gate pass.",
            "When create-site handoff is ready, created-site-evidence-brief.json defines the post-submit evidence required before artifact binding.",
            "When create-site handoff is ready, created-site-evidence-bundle/evidence-bundle.json provides the fillable redacted evidence scaffold and follow-up commands.",
            "Source next-stage handoff is generated from the refreshed status; follow it instead of hand-copying the next command.",
            "After site creation, created-site artifact binding, schema capture, sample upload, batch upload, and launch acceptance remain separate gates.",
        ],
        "nextAction": (
            "use create-site-browser-runbook.json for the gated one-submit create-site browser stage"
            if ready_for_browser_stage == "create_site_handoff_ready"
            else "use create-site-preflight-brief.json to collect workspace API session preflight via background CDP fetch before asking for create-site authorization"
            if ready_for_browser_stage == "needs_create_site_preflight"
            else "perform existing-site read-only refresh and bind artifacts to that site"
        ),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
            "apiSessionPreflightRequired": next_stage_handoff.get("apiSessionPreflightRequired"),
            "apiSessionPreflight": next_stage_handoff.get("apiSessionPreflight", {}),
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare confirmed AllinCMS site execution artifacts.")
    parser.add_argument("--package", required=True)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument(
        "--source-review-objective-coverage",
        default="",
        help="Optional make_source_review_objective_coverage.py output to carry through the confirmed execution chain",
    )
    parser.add_argument("--user-confirmation-text", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-mode", choices=["new_site", "existing_site"], default="new_site")
    parser.add_argument("--site-key", default="", help="Required for existing_site mode")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--accepted-fields", default="")
    parser.add_argument("--accepted-deferral", action="append", default=[], help="field|decision|reason; repeatable")
    parser.add_argument("--notes", default="")
    parser.add_argument("--create-preflight", default="", help="Fresh create-site preflight evidence for new_site handoff")
    parser.add_argument(
        "--create-authorization-output",
        "--create-action-gate-output",
        dest="create_authorization_output",
        default="~/allincms-projects/allincms-authorization-create-site.json",
    )
    parser.add_argument("--fail-if-no-create-handoff", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.target_mode == "existing_site" and not args.site_key:
        raise SystemExit("ERROR: --site-key is required for existing_site mode")
    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote confirmed execution preparation summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"readyForBrowserStage={summary['readyForBrowserStage']} nextAction={summary['nextAction']}")
    if args.fail_if_no_create_handoff and summary["readyForBrowserStage"] != "create_site_handoff_ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
