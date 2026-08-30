#!/usr/bin/env python3
"""Build an actionable refinement plan from source wiki/package validation issues."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from validate_source_site_package import load_json as load_package_json
from validate_source_wiki import load_json as load_wiki_json


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


def load_json_optional(path: str, label: str) -> dict[str, Any]:
    if not path:
        return {}
    if label == "source wiki":
        return load_wiki_json(Path(path), label)
    return load_package_json(Path(path))


def issue_target(issue: str) -> str:
    match = re.search(r"((?:siteProposal|contentPlan|openQuestions|pages|products|posts|siteInfo|navigation|taxonomyPlan|mediaPolicy|contactFormPolicy)[A-Za-z0-9_.\\[\\]-]*)", issue)
    return match.group(1) if match else "source_wiki"


def source_wiki_target(package_target: str) -> str:
    target = package_target
    target = target.replace("siteProposal.", "site.")
    target = target.replace("contentPlan.", "")
    target = target.replace("siteInfo.", "siteInfo.")
    return target


def classification(issue: str) -> str:
    lowered = issue.lower()
    if "declaredcontentgoals" in lowered and any(token in lowered for token in ("categor", "taxonomy", "tag")):
        return "needs_taxonomy_confirmation"
    if any(token in lowered for token in ("placeholder", "draft product", "draft article", "review-required", "requires source extraction", "too short", "non-empty publication-ready copy")):
        return "needs_source_backed_rewrite"
    if any(token in lowered for token in ("media", "image", "cover", "logo")):
        return "needs_media_policy_or_user_deferral"
    if any(token in lowered for token in ("contact", "form", "notification", "cta", "legal")):
        return "needs_contact_or_form_confirmation"
    if any(token in lowered for token in ("taxonomy", "categor", "tag")):
        return "needs_taxonomy_confirmation"
    if any(token in lowered for token in ("navigation", "/products", "/posts", "homepage path")):
        return "needs_navigation_confirmation"
    if "sourceRefs" in issue or "source refs" in lowered:
        return "needs_source_reference_repair"
    return "needs_structural_or_copy_refinement"


def suggested_action(issue: str, target: str, kind: str) -> str:
    if kind == "needs_source_backed_rewrite":
        return f"Rewrite `{target}` with concise publishable copy derived from raw extraction/source refs; remove draft/review wording."
    if kind == "needs_media_policy_or_user_deferral":
        return f"Update `{target}` with source media candidates, public URL policy, or an explicit no-image/media deferral."
    if kind == "needs_contact_or_form_confirmation":
        return f"Update `{target}` with user-confirmed contact/form policy or explicit demo-scope deferral."
    if kind == "needs_taxonomy_confirmation":
        return f"Update `{target}` with source-backed category/tag labels and mark taxonomy as needing user confirmation/schema mapping."
    if kind == "needs_navigation_confirmation":
        return f"Update `{target}` so navigation includes required public paths and labels for planned pages/products/posts."
    if kind == "needs_source_reference_repair":
        return f"Attach valid sourceRefs from source-index.json to `{target}`."
    return f"Repair `{target}` in source-wiki JSON and rerun apply_refined_source_wiki.py."


def build_items(source: str, issues: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, str) or not issue.strip():
            continue
        target = issue_target(issue)
        wiki_target = source_wiki_target(target)
        kind = classification(issue)
        items.append(
            {
                "source": source,
                "issue": issue,
                "packageTarget": target,
                "sourceWikiTarget": wiki_target,
                "classification": kind,
                "blockingReview": True,
                "suggestedAction": suggested_action(issue, wiki_target, kind),
            }
        )
    return items


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    wiki = load_json_optional(args.source_wiki, "source wiki") if args.source_wiki else {}
    package = load_json_optional(args.package, "package") if args.package else {}
    wiki_issues = as_list(args.source_wiki_issue)
    package_issues = as_list(args.package_issue)
    review_issues = as_list(args.review_packet_issue)
    items = (
        build_items("source_wiki_validation", wiki_issues)
        + build_items("package_publication_validation", package_issues)
        + build_items("review_packet_validation", review_issues)
    )
    grouped: dict[str, int] = {}
    for item in items:
        grouped[item["classification"]] = grouped.get(item["classification"], 0) + 1
    plan = {
        "kind": "allincms_source_wiki_refinement_plan",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceWiki": args.source_wiki,
        "package": args.package,
        "reviewReadyBlocked": bool(items),
        "itemCount": len(items),
        "classificationCounts": grouped,
        "items": items,
        "context": {
            "siteName": wiki.get("site", {}).get("siteName") if isinstance(wiki.get("site"), dict) else "",
            "packageKind": package.get("kind") if isinstance(package, dict) else "",
        },
        "nextAction": "refine source-wiki JSON and rerun apply_refined_source_wiki.py" if items else "no refinement blockers recorded",
        "rule": "This plan is local-only. It guides source-wiki refinement and does not authorize AllinCMS remote mutation.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an actionable source-wiki refinement plan from validation issues.")
    parser.add_argument("--source-wiki", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--source-wiki-issue", action="append", default=[])
    parser.add_argument("--package-issue", action="append", default=[])
    parser.add_argument("--review-packet-issue", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan = build(args)
    print(f"Wrote source wiki refinement plan: {args.output}")
    print(f"reviewReadyBlocked={str(plan['reviewReadyBlocked']).lower()} items={plan['itemCount']}")
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
