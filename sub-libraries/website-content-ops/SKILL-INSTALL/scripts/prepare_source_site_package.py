#!/usr/bin/env python3
"""Prepare local source-to-site artifacts from user files without remote mutation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from build_source_inventory import build_inventory, validate_inventory
from extract_source_materials import build_extraction
from build_source_wiki import build_source_wiki
from export_source_wiki_markdown import build as export_source_wiki_markdown
from validate_source_wiki import validate_source_wiki
from make_source_input_requirements import build_report as build_requirements
from build_source_site_package import build_package
from validate_source_site_package import validate_package
from make_source_wiki_refinement_plan import build as build_refinement_plan
from make_source_wiki_refinement_brief import build as build_refinement_brief
from make_source_package_review_packet import build_review_packet
from validate_source_package_review_packet import validate_review_packet
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_execution_status


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_run_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: run directory must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def default_run_label(sources: list[str]) -> str:
    if not sources:
        return "allincms-source-run"
    first = Path(sources[0]).expanduser()
    name = first.name or first.parent.name
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    return safe[:48] or "allincms-source-run"


def artifact_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "inventory": run_dir / "source-index.json",
        "raw_dir": run_dir / "raw-extraction",
        "raw_summary": run_dir / "raw-extraction" / "summary.json",
        "source_wiki": run_dir / "source-wiki.json",
        "wiki_dir": run_dir / "wiki",
        "wiki_markdown_manifest": run_dir / "wiki" / "manifest.json",
        "requirements": run_dir / "source-input-requirements.json",
        "source_package": run_dir / "source-site-package.json",
        "refinement_plan": run_dir / "source-wiki-refinement-plan.json",
        "refinement_brief": run_dir / "source-wiki-refinement-brief.json",
        "refined_source_wiki": run_dir / "source-wiki.refined.json",
        "review_packet": run_dir / "source-package-review-packet.json",
        "execution_status": run_dir / "source-execution-status.json",
        "next_stage_handoff": run_dir / "source-next-stage-handoff.json",
        "summary": run_dir / "prepare-source-site-package-summary.json",
    }


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_len(value: Any) -> int:
    if isinstance(value, str):
        return len(value.strip())
    if isinstance(value, dict):
        return sum(text_len(item) for item in value.values())
    if isinstance(value, list):
        return sum(text_len(item) for item in value)
    return 0


def content_quality_summary(
    inventory: dict[str, Any],
    extraction_summary: dict[str, Any],
    source_package: dict[str, Any],
) -> dict[str, Any]:
    entries = as_list(inventory.get("entries"))
    extraction_stats = extraction_summary.get("extractionStats") if isinstance(extraction_summary.get("extractionStats"), dict) else {}
    plan = source_package.get("contentPlan") if isinstance(source_package.get("contentPlan"), dict) else {}
    pages = [item for item in as_list(plan.get("pages")) if isinstance(item, dict)]
    products = [item for item in as_list(plan.get("products")) if isinstance(item, dict)]
    posts = [item for item in as_list(plan.get("posts")) if isinstance(item, dict)]
    navigation = plan.get("navigation") if isinstance(plan.get("navigation"), dict) else {}
    nav_items = [item for item in as_list(navigation.get("items")) if isinstance(item, dict)]
    nav_paths = [item.get("path") for item in nav_items if isinstance(item.get("path"), str)]
    taxonomy = plan.get("taxonomyPlan") if isinstance(plan.get("taxonomyPlan"), dict) else {}
    page_lengths = [text_len(page.get("sections")) for page in pages]
    product_body_lengths = [text_len(product.get("content")) for product in products]
    post_body_lengths = [text_len(post.get("content")) for post in posts]
    warnings: list[str] = []
    if len(nav_paths) != len(set(nav_paths)):
        warnings.append("navigation_paths_not_unique")
    if products and not taxonomy.get("productCategoryCount"):
        warnings.append("products_present_without_product_categories")
    if posts and not taxonomy.get("postCategoryCount"):
        warnings.append("posts_present_without_post_categories")
    if pages and min(page_lengths or [0]) < 120:
        warnings.append("short_page_copy")
    if products and min(product_body_lengths or [0]) < 100:
        warnings.append("short_product_copy")
    if posts and min(post_body_lengths or [0]) < 140:
        warnings.append("short_post_copy")
    extracted_count = extraction_stats.get("extractedCount", 0)
    failed_count = extraction_stats.get("failedCount", 0)
    unsupported_count = extraction_stats.get("unsupportedCount", 0)
    return {
        "inputFileCount": len(entries),
        "extractedCount": extracted_count,
        "failedCount": failed_count,
        "unsupportedCount": unsupported_count,
        "contentCounts": {
            "pages": len(pages),
            "products": len(products),
            "posts": len(posts),
            "forms": len(as_list(plan.get("forms"))),
            "media": len(as_list(plan.get("media"))),
        },
        "navigationPathCount": len(nav_paths),
        "navigationPathsUnique": len(nav_paths) == len(set(nav_paths)),
        "taxonomyCounts": {
            "productCategories": taxonomy.get("productCategoryCount", 0),
            "postCategories": taxonomy.get("postCategoryCount", 0),
            "productTags": taxonomy.get("productTagCount", 0),
            "postTags": taxonomy.get("postTagCount", 0),
        },
        "minimumCopyLengths": {
            "page": min(page_lengths) if page_lengths else 0,
            "product": min(product_body_lengths) if product_body_lengths else 0,
            "post": min(post_body_lengths) if post_body_lengths else 0,
        },
        "warnings": warnings,
        "readyShape": not warnings and bool(pages and products and posts),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.output_dir).expanduser().resolve()
    ensure_run_dir_outside_skill(run_dir)
    paths = artifact_paths(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    run_label = args.run_label or default_run_label(args.sources)
    site_key = args.site_key or "{siteKey-after-creation}"

    inventory_args = SimpleNamespace(
        sources=args.sources,
        recursive=args.recursive,
        run_label=run_label,
        output=str(paths["inventory"]),
    )
    inventory = build_inventory(inventory_args)
    inventory_issues = validate_inventory(inventory)
    if inventory_issues:
        raise SystemExit("ERROR: invalid generated source inventory:\n- " + "\n- ".join(inventory_issues))
    write_json(paths["inventory"], inventory)

    extraction_args = SimpleNamespace(
        inventory=str(paths["inventory"]),
        output_dir=str(paths["raw_dir"]),
        site_name=args.site_name,
        site_description=args.site_description,
        language=args.language,
        industry=args.industry,
        max_text_chars=args.max_text_chars,
        max_table_rows=args.max_table_rows,
    )
    extraction_summary = build_extraction(extraction_args)

    wiki_args = SimpleNamespace(
        inventory=str(paths["inventory"]),
        extraction_summary=str(paths["raw_summary"]),
        site_name=args.site_name,
        site_description=args.site_description,
        language=args.language,
        industry=args.industry,
        wiki_ref=[],
        output=str(paths["source_wiki"]),
    )
    source_wiki = build_source_wiki(wiki_args)
    wiki_issues = validate_source_wiki(source_wiki, inventory)
    if wiki_issues:
        raise SystemExit("ERROR: invalid generated source wiki:\n- " + "\n- ".join(wiki_issues))
    write_json(paths["source_wiki"], source_wiki)
    wiki_markdown = export_source_wiki_markdown(
        SimpleNamespace(
            source_wiki=str(paths["source_wiki"]),
            inventory=str(paths["inventory"]),
            output_dir=str(paths["wiki_dir"]),
            fail_on_invalid=False,
            json=False,
        )
    )

    requirements_args = SimpleNamespace(
        site_key=site_key,
        content_types=args.content_types,
        source_types=args.source_types,
        manifest=[],
        save_capture_evidence=[],
        media_evidence=None,
        readiness_evidence=None,
        gap_ledger=args.gap_ledger,
        resolved_gap_evidence=args.resolved_gap_evidence,
    )
    requirements = build_requirements(requirements_args)
    write_json(paths["requirements"], requirements)

    package_args = SimpleNamespace(
        source_wiki=str(paths["source_wiki"]),
        requirements=str(paths["requirements"]),
        site_key=args.site_key,
        frontend_base_url=args.frontend_base_url,
        output=str(paths["source_package"]),
    )
    source_package = build_package(package_args)
    write_json(paths["source_package"], source_package)

    structural_issues = validate_package(source_package, require_complete=True, require_publication_ready=False)
    publication_issues = validate_package(source_package, require_complete=True, require_publication_ready=True)

    review_packet: dict[str, Any] | None = None
    review_issues: list[str] = []
    if not publication_issues:
        try:
            review_packet = build_review_packet(
                source_package,
                str(paths["source_package"]),
                review_packet_path=str(paths["review_packet"]),
                wiki_review_override={
                    "sourceWiki": str(paths["source_wiki"]),
                    "sourceWikiMarkdown": str(paths["wiki_markdown_manifest"]),
                    "sourceWikiMarkdownIndex": str(wiki_markdown.get("files", {}).get("index", "")),
                },
            )
            review_issues = validate_review_packet(review_packet, source_package)
            if not review_issues:
                write_json(paths["review_packet"], review_packet)
        except ValueError as exc:
            review_issues = [str(exc)]
    refinement_plan = build_refinement_plan(
        SimpleNamespace(
            source_wiki=str(paths["source_wiki"]),
            package=str(paths["source_package"]),
            source_wiki_issue=wiki_issues,
            package_issue=publication_issues,
            review_packet_issue=review_issues,
            output=str(paths["refinement_plan"]),
            json=False,
        )
    )
    wiki_files = wiki_markdown.get("files") if isinstance(wiki_markdown.get("files"), dict) else {}
    refinement_brief = build_refinement_brief(
        SimpleNamespace(
            source_wiki=str(paths["source_wiki"]),
            refinement_plan=str(paths["refinement_plan"]),
            output=str(paths["refinement_brief"]),
            output_refined_source_wiki=str(paths["refined_source_wiki"]),
            site_markdown=str(wiki_files.get("site", "")),
            pages_markdown=str(wiki_files.get("pages", "")),
            products_markdown=str(wiki_files.get("products", "")),
            posts_markdown=str(wiki_files.get("posts", "")),
            max_markdown_chars=2000,
            json=False,
        )
    )

    status_args = SimpleNamespace(
        package=str(paths["source_package"]),
        review_packet=str(paths["review_packet"]) if review_packet and not review_issues else "",
        confirmation="",
        execution_plan="",
        artifact_readiness="",
        create_site_handoff="",
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
        output_dir=str(run_dir / "next-stage"),
    )

    package_status = "review_ready" if review_packet and not review_issues else "needs_source_wiki_refinement"
    if structural_issues:
        package_status = "blocked_structural_package"
    quality = content_quality_summary(inventory, extraction_summary, source_package)
    summary = {
        "kind": "allincms_prepared_source_site_package",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "packageStatus": package_status,
        "runDirectory": str(run_dir),
        "siteKeyMode": "existing_site" if args.site_key else "new_site_placeholder",
        "counts": {
            "sourceFiles": inventory.get("summary", {}).get("fileCount", 0),
            "pages": len(source_package.get("contentPlan", {}).get("pages", [])),
            "products": len(source_package.get("contentPlan", {}).get("products", [])),
            "posts": len(source_package.get("contentPlan", {}).get("posts", [])),
        },
        "contentQuality": quality,
        "artifacts": {
            "inventory": str(paths["inventory"]),
            "rawExtractionSummary": str(paths["raw_summary"]),
            "sourceWiki": str(paths["source_wiki"]),
            "sourceWikiMarkdown": str(paths["wiki_markdown_manifest"]),
            "sourceWikiMarkdownIndex": wiki_markdown.get("files", {}).get("index", ""),
            "sourceInputRequirements": str(paths["requirements"]),
            "sourceSitePackage": str(paths["source_package"]),
            "sourceWikiRefinementPlan": str(paths["refinement_plan"]),
            "sourceWikiRefinementBrief": str(paths["refinement_brief"]),
            "refinedSourceWikiTarget": str(paths["refined_source_wiki"]),
            "reviewPacket": str(paths["review_packet"]) if review_packet and not review_issues else "",
            "sourceExecutionStatus": str(paths["execution_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {
            "inventoryIssues": inventory_issues,
            "sourceWikiIssues": wiki_issues,
            "packageStructuralIssues": structural_issues,
            "packagePublicationIssues": publication_issues,
            "reviewPacketIssues": review_issues,
            "refinementPlanItemCount": refinement_plan.get("itemCount", 0),
            "refinementBriefBlockerCount": refinement_brief.get("blockerCount", 0),
        },
        "adversarialChecks": [
            "All artifacts are local-only and outside the skill package.",
            "Review packet is generated only after publication-ready package validation passes.",
            "Package confirmation remains separate from remote create/save/upload/publish authorization.",
            "Products and posts stay schemaVerified=false until current-site save capture and sample verification.",
            "Markdown wiki files are human-review artifacts generated from the source wiki; they are not upload payloads.",
            "When review is blocked, source-wiki-refinement-plan.json translates validation issues into field-level repair actions.",
            "source-wiki-refinement-brief.json is a safe AI/operator task contract for writing source-wiki.refined.json; it is not user confirmation or remote authorization.",
            "contentQuality.readyShape is a shape signal only; it does not replace package validation, user confirmation, schema capture, sample proof, or batch gates.",
        ],
        "nextAction": (
            "show review packet and ask user to confirm content intent"
            if package_status == "review_ready"
            else "refine source wiki using source-wiki-refinement-brief.json, then run apply_refined_source_wiki.py"
        ),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local AllinCMS source-site package artifacts from user files.")
    parser.add_argument("sources", nargs="+", help="Source files or directories")
    parser.add_argument("--output-dir", required=True, help="Run directory outside the skill package")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--run-label", default="")
    parser.add_argument("--site-name", default="")
    parser.add_argument("--site-description", default="")
    parser.add_argument("--language", default="en")
    parser.add_argument("--industry", default="unspecified")
    parser.add_argument("--site-key", default="", help="Existing site key; omit for new-site package planning")
    parser.add_argument("--frontend-base-url", default="")
    parser.add_argument("--content-types", default="products,posts,themes/pages,site-info,forms,media,navigation")
    parser.add_argument("--source-types", default="pdf_catalog,product_datasheet,company_profile,website_copy,image_urls,spreadsheet,sitemap_or_navigation_brief,plain_brief")
    parser.add_argument("--gap-ledger", action="append", default=[])
    parser.add_argument("--resolved-gap-evidence", action="append", default=[])
    parser.add_argument("--max-text-chars", type=int, default=12000)
    parser.add_argument("--max-table-rows", type=int, default=40)
    parser.add_argument("--fail-if-not-review-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote source-site package preparation summary: {summary['artifacts']['sourceSitePackage']}")
        print(f"packageStatus={summary['packageStatus']} nextAction={summary['nextAction']}")
        print(f"summary={Path(args.output_dir).expanduser().resolve() / 'prepare-source-site-package-summary.json'}")
    if args.fail_if_not_review_ready and summary["packageStatus"] != "review_ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
