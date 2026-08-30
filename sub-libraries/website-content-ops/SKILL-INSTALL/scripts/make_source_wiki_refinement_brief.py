#!/usr/bin/env python3
"""Build a safe AI/operator brief for refining an AllinCMS source wiki."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_wiki import load_json
from validate_source_site_package import (
    TAXONOMY_STATUS_ALLOWED,
    MEDIA_STATUS_ALLOWED,
    CONTACT_STATUS_ALLOWED,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output path must be outside the skill package")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def read_optional_text(path: str, max_chars: int) -> str:
    if not path:
        return ""
    try:
        value = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    return value[:max_chars]


def compact_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in as_list(plan.get("items")):
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "sourceWikiTarget": text(item.get("sourceWikiTarget")) or "source_wiki",
                "classification": text(item.get("classification")) or "needs_refinement",
                "issue": text(item.get("issue")),
                "suggestedAction": text(item.get("suggestedAction")),
            }
        )
    return items


def source_refs(wiki: dict[str, Any]) -> list[str]:
    source_set = wiki.get("sourceSet")
    if not isinstance(source_set, dict):
        return []
    refs: list[str] = []
    for item in as_list(source_set.get("inputFiles")):
        if isinstance(item, dict) and text(item.get("sourceRef")):
            refs.append(text(item.get("sourceRef")))
    return refs


def count_items(wiki: dict[str, Any]) -> dict[str, int]:
    return {
        "pages": len(as_list(wiki.get("pages"))),
        "products": len(as_list(wiki.get("products"))),
        "posts": len(as_list(wiki.get("posts"))),
        "openQuestions": len(as_list(wiki.get("openQuestions"))),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    wiki = load_json(Path(args.source_wiki), "source wiki")
    plan = load_json(Path(args.refinement_plan), "refinement plan")
    if wiki.get("kind") != "allincms_source_wiki":
        raise SystemExit("ERROR: source wiki kind must be allincms_source_wiki")
    if plan.get("kind") != "allincms_source_wiki_refinement_plan":
        raise SystemExit("ERROR: refinement plan kind must be allincms_source_wiki_refinement_plan")

    output_refined = args.output_refined_source_wiki or str(output.with_name("source-wiki.refined.json"))
    markdown_context: dict[str, str] = {}
    for label, path in (
        ("site", args.site_markdown),
        ("pages", args.pages_markdown),
        ("products", args.products_markdown),
        ("posts", args.posts_markdown),
    ):
        value = read_optional_text(path, args.max_markdown_chars)
        if value:
            markdown_context[label] = value

    brief = {
        "kind": "allincms_source_wiki_refinement_brief",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "sourceWiki": args.source_wiki,
        "refinementPlan": args.refinement_plan,
        "outputRefinedSourceWiki": output_refined,
        "site": wiki.get("site") if isinstance(wiki.get("site"), dict) else {},
        "sourceRefs": source_refs(wiki),
        "counts": count_items(wiki),
        "blockerCount": len(compact_items(plan)),
        "classificationCounts": plan.get("classificationCounts") if isinstance(plan.get("classificationCounts"), dict) else {},
        "requiredEdits": compact_items(plan),
        "markdownContext": markdown_context,
        "outputContract": {
            "kind": "allincms_source_wiki",
            "writePath": output_refined,
            "mustKeep": [
                "localOnly=true",
                "remoteMutationsPerformed=false",
                "sourceSet.inputFiles and source refs",
                "pages/products/posts arrays with sourceRefs",
            ],
            "mustRemove": [
                "Draft Product / Draft Article placeholders",
                "requires review / requires source extraction / TODO wording",
                "unsupported claims not present in source refs",
                "cookies, headers, server-action IDs, account labels, private emails, raw object IDs",
            ],
            "mustDecideOrDefer": [
                "siteInfo public contact and legal identity",
                "navigation coverage for /, /products, /posts when planned",
                "media policy for source images, URL images, or no-image demo scope",
                "contact/form policy and notification destination handling",
                "taxonomy labels that still need current-site mapping",
            ],
            "policyStatusOptions": {
                "_note": "when the policy has any items/terms/gaps, its status must be one of these exact values (else publication-ready validation fails); values imported from validate_source_site_package to stay in sync",
                "contentPlan.taxonomyPlan.status": sorted(TAXONOMY_STATUS_ALLOWED),
                "contentPlan.mediaPolicy.status": sorted(MEDIA_STATUS_ALLOWED),
                "contentPlan.contactFormPolicy.status": sorted(CONTACT_STATUS_ALLOWED),
            },
            "contentFloors": {
                "_note": "editorial floors each item must meet to pass publication-ready (see references/site-content-and-aesthetics-spec.md Professional Copy Standard)",
                "product": "name + slug + description>=40 chars + content as >=3 Slate paragraphs (what / how-built / applications) + specs list + >=1 category",
                "post": "title + slug + excerpt>=40 chars + content as >=3 Slate paragraphs, genuinely useful (not a restated product ad)",
                "page": "each section a meaningful heading + a scannable paragraph; homepage leads with value prop + CTA",
                "taxonomy": "2-3 product categories, each with >=2 products",
            },
            "policyRequiredFields": {
                "_note": "when hand-editing (not using --auto-draft-refined-source-wiki), each policy object below needs its FULL required set, else publication-ready validation rejects field-by-field. status values are in policyStatusOptions above.",
                "contentPlan.taxonomyPlan": {
                    "status": "one of policyStatusOptions when categories/tags exist",
                    "userConfirmationRequired": "true",
                    "requiresCategorySchemaCapture / requiresTagSchemaCapture / requiresCreationOrMappingPlan": "all true",
                    "count fields (non-negative ints)": ["productCategoryCount", "postCategoryCount", "productTagCount", "postTagCount"],
                },
                "contentPlan.mediaPolicy": {
                    "status": "one of policyStatusOptions when any media need/candidate exists",
                    "requiresFrontendImageProof": "true",
                    "acceptedNoImage": "true only when no source media candidates/needs remain",
                    "count fields (ints)": ["sourceCandidateCount", "pageMediaNeedCount", "productMediaNeedCount", "postMediaNeedCount", "missingImageFieldCount"],
                },
                "contentPlan.contactFormPolicy": {
                    "status": "one of policyStatusOptions when forms/contact gaps exist",
                    "requiresSubmissionProofOrDeferral": "true",
                    "notificationDestinationPolicy / ctaDestinationPolicy": "explicit value (not empty, not 'implicit')",
                    "count fields (ints)": ["formCount", "contactGapCount"],
                },
                "contentPlan.siteInfo": {
                    "draftSeoTitle": "required", "draftSeoDescription": ">=40 chars", "userConfirmationRequired": "true",
                },
                "contentPlan.navigation": {
                    "items": "must include / and (/products, /posts when those are planned)", "userConfirmationRequired": "true",
                },
            },
        },
        "validationCommands": [
            (
                "python3 skills/allincms-bulk-content-upload/scripts/apply_refined_source_wiki.py "
                f"--source-wiki {output_refined} "
                f"--output-dir {Path(output_refined).with_name('refined-source-apply')}"
            )
        ],
        "authoringNorms": {
            "_note": "author each product/article to serve the visitor's decision, not as a catalog dump",
            "readFirst": "references/source-material-norms.md (visitor-first per-product/article norms + acceptance checklists)",
            "product": "P1 identity+one-line positioning / P2 structured specs (the parameters a buyer filters on) / P3 >=2 differentiators each tied to a number / P4 traceable trust claims / P5 config+inquiry path; one clean product image; >=1 category",
            "article": "title = the visitor's real question; body teaches mechanism/tradeoffs before it sells, maps to the product series by name, every number traceable; not a restated product ad",
            "inputHygiene": "one product per record (do not merge into a Draft blob), extract specs into structured key/value, strip unverifiable marketing, bind sourceRefs, flag gaps as needs-user-input, never fabricate specs/certs/prices/contacts",
        },
        "adversarialChecks": [
            "Do not ask for user confirmation until apply_refined_source_wiki.py reports reviewReady=true.",
            "Do not create sites, save content, upload media, publish, or replay JSON from this brief.",
            "Do not copy raw source text into the skill package; keep refined wiki and review artifacts in the run folder.",
            "Every generated claim should either reference sourceRefs or be marked as a user-confirmed/deferral decision.",
            "Author to references/source-material-norms.md: each product must let a visitor judge relevance/fit/differentiation/trust/action; each article must answer a real question and teach before it sells.",
        ],
        "nextAction": "write the refined allincms_source_wiki JSON, then run apply_refined_source_wiki.py",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AI/operator brief for source-wiki refinement.")
    parser.add_argument("--source-wiki", required=True)
    parser.add_argument("--refinement-plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-refined-source-wiki", default="")
    parser.add_argument("--site-markdown", default="")
    parser.add_argument("--pages-markdown", default="")
    parser.add_argument("--products-markdown", default="")
    parser.add_argument("--posts-markdown", default="")
    parser.add_argument("--max-markdown-chars", type=int, default=2000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    brief = build(args)
    print(f"Wrote source wiki refinement brief: {args.output}")
    print(f"blockers={brief['blockerCount']} outputRefinedSourceWiki={brief['outputRefinedSourceWiki']}")
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
