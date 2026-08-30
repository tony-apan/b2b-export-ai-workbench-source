#!/usr/bin/env python3
"""Apply a refined source wiki and refresh package/review/status artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from build_source_site_package import build_package
from export_source_wiki_markdown import build as export_source_wiki_markdown
from make_source_wiki_refinement_plan import build as build_refinement_plan
from make_source_package_review_packet import build_review_packet
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_execution_status
from validate_refined_source_wiki_contract import build_report as build_refined_contract_report
from validate_refined_source_wiki_contract import hydrate_source_fingerprints
from validate_source_package_review_packet import validate_review_packet
from validate_source_site_package import validate_package
from validate_source_wiki import load_json, validate_source_wiki


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
        "source_package": output_dir / "source-site-package.refined.json",
        "wiki_dir": output_dir / "wiki",
        "wiki_markdown_manifest": output_dir / "wiki" / "manifest.json",
        "refined_contract_validation": output_dir / "refined-source-wiki-contract-validation.json",
        "refinement_plan": output_dir / "source-wiki-refinement-plan.json",
        "validation": output_dir / "source-site-package.refined-validation.json",
        "review_packet": output_dir / "source-package-review-packet.refined.json",
        "execution_status": output_dir / "source-execution-status.after-refined-wiki.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-refined-wiki.json",
        "summary": output_dir / "refined-source-wiki-apply-summary.json",
    }


def package_validation_report(package_path: str, issues: list[str]) -> dict[str, Any]:
    return {
        "kind": "allincms_source_site_package_validation",
        "generatedAt": now_iso(),
        "package": package_path,
        "valid": not issues,
        "requireCompletePackage": True,
        "requirePublicationReady": True,
        "issues": issues,
    }


def source_status_args(args: argparse.Namespace, paths: dict[str, Path], review_packet_path: str) -> SimpleNamespace:
    return SimpleNamespace(
        package=str(paths["source_package"]),
        review_packet=review_packet_path,
        confirmation=args.confirmation,
        execution_plan=args.execution_plan,
        artifact_readiness=args.artifact_readiness,
        create_site_handoff=getattr(args, "create_site_handoff", ""),
        created_site_binding=args.created_site_binding,
        pages_site_info_handoff=args.pages_site_info_handoff,
        pages_site_info_evidence=args.pages_site_info_evidence,
        pages_site_info_validation=args.pages_site_info_validation,
        taxonomy_handoff=args.taxonomy_handoff,
        taxonomy_evidence=args.taxonomy_evidence,
        taxonomy_validation=args.taxonomy_validation,
        schema_capture_handoff=args.schema_capture_handoff,
        upload_readiness=args.upload_readiness,
        sample_evidence=args.sample_evidence,
        batch_evidence=args.batch_evidence,
        batch_validation=args.batch_validation,
        forms_media_settings=getattr(args, "forms_media_settings", ""),
        launch_acceptance=args.launch_acceptance,
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    original_refined_wiki = load_json(Path(args.source_wiki), "refined source wiki")
    inventory = load_json(Path(args.inventory), "source inventory") if args.inventory else None
    refined_wiki, fingerprints_hydrated = hydrate_source_fingerprints(original_refined_wiki, inventory)
    source_wiki_for_outputs = args.source_wiki
    hydrated_source_wiki = ""
    if fingerprints_hydrated:
        hydrated_source_wiki = write_json(output_dir / "source-wiki.refined.hydrated.json", refined_wiki)
        source_wiki_for_outputs = hydrated_source_wiki
    contract_issues: list[str] = []
    contract_report_path = ""
    if getattr(args, "refinement_brief", ""):
        contract_report = build_refined_contract_report(
            SimpleNamespace(
                refined_source_wiki=args.source_wiki,
                refinement_brief=args.refinement_brief,
                inventory="" if hydrated_source_wiki else args.inventory,
                output=str(paths["refined_contract_validation"]),
                json=False,
            )
        )
        contract_issues = contract_report.get("issues", []) if isinstance(contract_report.get("issues"), list) else []
        contract_report_path = write_json(paths["refined_contract_validation"], contract_report)
        if contract_issues and args.fail_on_invalid:
            raise SystemExit("ERROR: refined source wiki contract validation failed:\n- " + "\n- ".join(contract_issues))
    wiki_issues = validate_source_wiki(refined_wiki, inventory)
    if wiki_issues and args.fail_on_invalid:
        raise SystemExit("ERROR: refined source wiki is invalid:\n- " + "\n- ".join(wiki_issues))
    wiki_markdown = export_source_wiki_markdown(
        SimpleNamespace(
            source_wiki=source_wiki_for_outputs,
            inventory=args.inventory,
            output_dir=str(paths["wiki_dir"]),
            fail_on_invalid=False,
            json=False,
        )
    )

    package: dict[str, Any] = {}
    package_issues: list[str] = []
    review_packet: dict[str, Any] | None = None
    review_issues: list[str] = []
    review_packet_path = ""

    if not wiki_issues and not contract_issues:
        package = build_package(
            SimpleNamespace(
                source_wiki=source_wiki_for_outputs,
                requirements=args.requirements,
                site_key=args.site_key,
                frontend_base_url=args.frontend_base_url,
                output=str(paths["source_package"]),
                json=False,
            )
        )
        write_json(paths["source_package"], package)
        package_issues = validate_package(package, require_complete=True, require_publication_ready=True)
        write_json(paths["validation"], package_validation_report(str(paths["source_package"]), package_issues))
        if not package_issues:
            try:
                review_packet = build_review_packet(
                    package,
                    str(paths["source_package"]),
                    review_packet_path=str(paths["review_packet"]),
                    wiki_review_override={
                        "sourceWiki": source_wiki_for_outputs,
                        "sourceWikiMarkdown": str(paths["wiki_markdown_manifest"]),
                        "sourceWikiMarkdownIndex": str(wiki_markdown.get("files", {}).get("index", "")),
                    },
                )
                review_issues = validate_review_packet(review_packet, package)
                if not review_issues:
                    review_packet_path = write_json(paths["review_packet"], review_packet)
            except ValueError as exc:
                review_issues = [str(exc)]
    else:
        write_json(paths["validation"], package_validation_report(str(paths["source_package"]), wiki_issues))

    source_status = summarize_execution_status(source_status_args(args, paths, review_packet_path))
    write_json(paths["execution_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["execution_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
    )
    refinement_plan = build_refinement_plan(
        SimpleNamespace(
                source_wiki=source_wiki_for_outputs,
            package=str(paths["source_package"]) if package else "",
            source_wiki_issue=wiki_issues,
            package_issue=package_issues,
            review_packet_issue=review_issues,
            output=str(paths["refinement_plan"]),
            json=False,
        )
    )

    review_ready = bool(review_packet_path) and not wiki_issues and not package_issues and not review_issues
    summary = {
        "kind": "allincms_refined_source_wiki_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "reviewReady": review_ready,
        "readyForNextStage": "review_packet" if review_ready else "source_wiki_refinement",
        "artifacts": {
            "sourceWiki": args.source_wiki,
            "hydratedSourceWiki": hydrated_source_wiki,
            "sourceWikiMarkdown": str(paths["wiki_markdown_manifest"]),
            "sourceWikiMarkdownIndex": wiki_markdown.get("files", {}).get("index", ""),
            "refinedSourceWikiContractValidation": contract_report_path,
            "sourceSitePackage": str(paths["source_package"]) if package else "",
            "packageValidation": str(paths["validation"]),
            "sourceWikiRefinementPlan": str(paths["refinement_plan"]),
            "reviewPacket": review_packet_path,
            "sourceExecutionStatus": str(paths["execution_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {
            "sourceWikiIssues": wiki_issues,
            "refinedSourceWikiContractIssues": contract_issues,
            "packagePublicationIssues": package_issues,
            "reviewPacketIssues": review_issues,
            "refinementPlanItemCount": refinement_plan.get("itemCount", 0),
        },
        "adversarialChecks": [
            "This helper applies a refined local source wiki only; it does not create, save, upload, publish, or authorize AllinCMS mutations.",
            "Review packet generation is allowed only after source wiki validation and publication-ready package validation pass.",
            "Package confirmation remains content-intent proof only and must not be treated as remote mutation authorization.",
            "Products/posts manifests remain schemaVerified=false until current-site save capture and sample verification.",
            "Markdown wiki files are review artifacts generated from the refined source wiki; they are not upload payloads.",
            "When review is blocked, source-wiki-refinement-plan.json translates validation issues into field-level repair actions.",
        ],
        "nextAction": (
            "show review packet and ask user for content-intent confirmation"
            if review_ready
            else "refine source wiki until source/package/review validation passes"
        ),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
    }
    write_json(paths["summary"], summary)
    if args.fail_on_invalid and not review_ready:
        blockers = wiki_issues + contract_issues + package_issues + review_issues
        raise SystemExit("ERROR: refined source wiki is not review-ready:\n- " + "\n- ".join(blockers or ["unknown validation failure"]))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a refined source wiki to source package/review/status artifacts.")
    parser.add_argument("--source-wiki", required=True, help="AI/user-refined allincms_source_wiki JSON")
    parser.add_argument("--refinement-brief", default="", help="Optional allincms_source_wiki_refinement_brief JSON to bind the refined wiki contract")
    parser.add_argument("--inventory", default="", help="Optional source inventory used to validate source refs")
    parser.add_argument("--requirements", default="", help="Optional allincms_source_input_requirements JSON")
    parser.add_argument("--site-key", default="")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--create-site-handoff", default="")
    parser.add_argument("--created-site-binding", default="")
    parser.add_argument("--pages-site-info-handoff", default="")
    parser.add_argument("--pages-site-info-evidence", default="")
    parser.add_argument("--pages-site-info-validation", default="")
    parser.add_argument("--taxonomy-handoff", default="")
    parser.add_argument("--taxonomy-evidence", default="")
    parser.add_argument("--taxonomy-validation", default="")
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", default="")
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote refined source wiki apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"reviewReady={str(summary['reviewReady']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["reviewReady"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
