#!/usr/bin/env python3
"""Summarize pre-browser source review objective coverage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_package_review_packet import load_json as load_review_json
from validate_source_package_review_packet import validate_review_packet


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: {label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [item for item in as_list(value) if isinstance(item, str) and item.strip()]


def path_exists(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and Path(value).expanduser().exists()


def packet_counts(packet: dict[str, Any]) -> dict[str, int]:
    counts = packet.get("counts") if isinstance(packet.get("counts"), dict) else {}
    out: dict[str, int] = {}
    for key in (
        "pages",
        "products",
        "posts",
        "forms",
        "media",
        "siteInfoFields",
        "navigationItems",
    ):
        value = counts.get(key)
        out[key] = value if isinstance(value, int) and value >= 0 else 0
    return out


def package_source_counts(package: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(package, dict):
        return {"inputFiles": 0, "rawExtractionRefs": 0, "wikiRefs": 0}
    source_set = package.get("sourceSet") if isinstance(package.get("sourceSet"), dict) else {}
    return {
        "inputFiles": len(as_list(source_set.get("inputFiles"))),
        "rawExtractionRefs": len(as_list(source_set.get("rawExtractionRefs"))),
        "wikiRefs": len(as_list(source_set.get("wikiRefs"))),
    }


def add_item(
    items: list[dict[str, Any]],
    *,
    item_id: str,
    label: str,
    status: str,
    evidence: list[str] | None = None,
    blockers: list[str] | None = None,
    required_for_review: bool = True,
    required_for_final: bool = True,
) -> None:
    items.append(
        {
            "id": item_id,
            "label": label,
            "status": status,
            "requiredForReview": required_for_review,
            "requiredForFinal": required_for_final,
            "evidence": evidence or [],
            "blockers": blockers or [],
        }
    )


def policy_present(packet: dict[str, Any], key: str) -> bool:
    review = packet.get("siteInfoNavigationFormsMediaReview")
    if not isinstance(review, dict):
        return False
    value = review.get(key)
    return isinstance(value, dict) and value.get("present") is True


def build_coverage(
    packet: dict[str, Any],
    *,
    review_packet_path: str,
    package: dict[str, Any] | None = None,
    package_path: str = "",
    objective: str = "",
) -> dict[str, Any]:
    issues: list[str] = []
    if packet.get("kind") != "allincms_source_package_review_packet":
        issues.append("review packet kind must be allincms_source_package_review_packet")
    if package is None and isinstance(packet.get("sourcePackage"), str):
        package_path = packet["sourcePackage"]
        package_file = Path(package_path).expanduser()
        if package_file.exists():
            package = load_json(package_file, "source package")
    if package is not None:
        issues.extend(validate_review_packet(packet, package))
    else:
        issues.extend(validate_review_packet(packet, None))
        issues.append("source package was not loaded; package-bound review coverage is incomplete")

    counts = packet_counts(packet)
    source_counts = package_source_counts(package)
    quality = packet.get("contentQualityReview") if isinstance(packet.get("contentQualityReview"), dict) else {}
    goal = packet.get("contentGoalCoverage") if isinstance(packet.get("contentGoalCoverage"), dict) else {}
    wiki = packet.get("wikiReview") if isinstance(packet.get("wikiReview"), dict) else {}
    site_info_nav = (
        packet.get("siteInfoNavigationFormsMediaReview")
        if isinstance(packet.get("siteInfoNavigationFormsMediaReview"), dict)
        else {}
    )
    decision_matrix = as_list(packet.get("confirmationDecisionMatrix"))
    confirmation_fields = string_list(packet.get("confirmationFields"))
    covered_confirmation_fields = {
        item.get("field")
        for item in decision_matrix
        if isinstance(item, dict) and item.get("field") in confirmation_fields
    }
    missing_decisions = sorted(set(confirmation_fields) - covered_confirmation_fields)

    items: list[dict[str, Any]] = []
    add_item(
        items,
        item_id="source_files_ingested",
        label="Source files were inventoried and preserved in a package source set",
        status="proven" if source_counts["inputFiles"] > 0 else "missing",
        evidence=[package_path],
        blockers=[] if source_counts["inputFiles"] > 0 else ["sourceSet.inputFiles must contain at least one source file"],
    )
    wiki_ready = (
        isinstance(wiki.get("sourceWiki"), str)
        and bool(wiki["sourceWiki"].strip())
        and path_exists(wiki.get("sourceWikiMarkdownIndex"))
        and source_counts["wikiRefs"] > 0
    )
    add_item(
        items,
        item_id="source_wiki_ready",
        label="Source material is distilled into JSON plus readable Markdown wiki artifacts",
        status="proven" if wiki_ready else "missing",
        evidence=[str(wiki.get("sourceWiki", "")), str(wiki.get("sourceWikiMarkdownIndex", ""))],
        blockers=[] if wiki_ready else ["wikiReview and sourceSet.wikiRefs must point to readable wiki artifacts"],
    )
    publishable = (
        not issues
        and goal.get("complete") is True
        and quality.get("readyShape") is True
        and counts["pages"] > 0
        and counts["products"] > 0
        and counts["posts"] > 0
    )
    add_item(
        items,
        item_id="publishable_package_review_ready",
        label="Source package and review packet cover pages, products, posts, site info, navigation, taxonomy, forms, and media policies",
        status="proven" if publishable else "missing",
        evidence=[package_path, review_packet_path],
        blockers=issues
        or (
            []
            if publishable
            else ["contentGoalCoverage.complete, contentQualityReview.readyShape, and nonzero page/product/post counts are required"]
        ),
    )
    add_item(
        items,
        item_id="single_pages_ready",
        label="Single/static pages have paths, headings, body length, and source refs for user review",
        status="proven" if counts["pages"] > 0 and bool(as_list(packet.get("pagesReview"))) else "missing",
        evidence=[f"pages={counts['pages']}"],
        blockers=[] if counts["pages"] > 0 else ["review packet must include at least one page"],
    )
    add_item(
        items,
        item_id="products_ready",
        label="Products have slugs, descriptions, body blocks, categories/tags, media needs, and source refs for user review",
        status="proven" if counts["products"] > 0 and bool(as_list(packet.get("productsReview"))) else "missing",
        evidence=[f"products={counts['products']}"],
        blockers=[] if counts["products"] > 0 else ["review packet must include at least one product"],
    )
    add_item(
        items,
        item_id="posts_ready",
        label="Posts have slugs, excerpts, body blocks, categories/tags, media needs, and source refs for user review",
        status="proven" if counts["posts"] > 0 and bool(as_list(packet.get("postsReview"))) else "missing",
        evidence=[f"posts={counts['posts']}"],
        blockers=[] if counts["posts"] > 0 else ["review packet must include at least one post"],
    )
    policies_ready = (
        counts["siteInfoFields"] > 0
        and counts["navigationItems"] > 0
        and policy_present(packet, "taxonomyPlan")
        and policy_present(packet, "mediaPolicy")
        and policy_present(packet, "contactFormPolicy")
    )
    add_item(
        items,
        item_id="site_info_navigation_policies_ready",
        label="Site info, navigation, taxonomy, forms, media, contact, and deferral policies are visible before confirmation",
        status="proven" if policies_ready else "missing",
        evidence=[
            f"siteInfoFields={counts['siteInfoFields']}",
            f"navigationItems={counts['navigationItems']}",
            str(site_info_nav.get("taxonomyPlan", {})),
            str(site_info_nav.get("mediaPolicy", {})),
            str(site_info_nav.get("contactFormPolicy", {})),
        ],
        blockers=[] if policies_ready else ["site-info, navigation, taxonomy, media, and contact policy summaries are required"],
    )
    confirmation_ready = bool(confirmation_fields) and not missing_decisions and packet.get("needsUserConfirmation") is True
    add_item(
        items,
        item_id="user_confirmation_needed",
        label="Review packet exposes every confirmation field and blocks remote mutation until the user confirms content intent",
        status="pending_user_confirmation" if confirmation_ready else "missing",
        evidence=confirmation_fields,
        blockers=[] if confirmation_ready else ["confirmation fields must all be covered by the decision matrix"],
        required_for_review=False,
    )
    for item_id, label in (
        ("remote_site_creation_not_started", "Create/select site is still unproven and requires a later browser stage"),
        ("schema_capture_not_started", "Posts/products schema capture is still unproven and requires current-site save request proof"),
        ("sample_batch_upload_not_started", "Sample and batch upload/publish are still unproven and require later gated browser evidence"),
        ("final_launch_not_started", "Frontend launch, cleanup, and final closeout are still unproven"),
    ):
        add_item(
            items,
            item_id=item_id,
            label=label,
            status="not_started",
            required_for_review=False,
            required_for_final=True,
            blockers=["not required for local review readiness, but required before the full source-to-live-site objective is complete"],
        )

    missing_for_review = [
        item["id"]
        for item in items
        if item["requiredForReview"] and item["status"] != "proven"
    ]
    missing_for_final = [
        item["id"]
        for item in items
        if item["requiredForFinal"] and item["status"] != "proven"
    ]
    review_complete = not missing_for_review

    return {
        "kind": "allincms_source_review_objective_coverage",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "remoteMutationAllowed": False,
        "objective": objective,
        "reviewPacket": review_packet_path,
        "sourcePackage": package_path or packet.get("sourcePackage", ""),
        "reviewComplete": review_complete,
        "readyForBrowserStage": "waiting_for_user_content_confirmation" if review_complete else "needs_source_package_repair",
        "complete": False,
        "counts": {
            **counts,
            "sourceInputFiles": source_counts["inputFiles"],
            "rawExtractionRefs": source_counts["rawExtractionRefs"],
            "wikiRefs": source_counts["wikiRefs"],
        },
        "contentGoalCoverage": packet.get("contentGoalCoverage", {}),
        "contentQualityReview": packet.get("contentQualityReview", {}),
        "contentGoalOverages": packet.get("contentGoalOverages", {}),
        "confirmationFields": confirmation_fields,
        "suggestedAcceptedFields": string_list(packet.get("suggestedAcceptedFields")),
        "suggestedAcceptedDeferrals": [
            item for item in as_list(packet.get("suggestedAcceptedDeferrals")) if isinstance(item, dict)
        ],
        "coverage": items,
        "missingForReview": missing_for_review,
        "missingForFinal": missing_for_final,
        "reviewPacketValidationIssues": issues,
        "adversarialChecks": [
            "This report proves local review readiness only; it is not browser evidence and not user authorization.",
            "Do not create/select a site, save, publish, upload, replay JSON, or bind domains from this report.",
            "User content confirmation is still required before preparing any create/select-site browser boundary.",
            "The full objective remains incomplete until site creation/selection, schema capture, sample upload, batch upload, frontend launch, cleanup, adversarial checks, and sedimentation are proven.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize pre-browser objective coverage from a source review packet.")
    parser.add_argument("review_packet")
    parser.add_argument("--package", default="", help="Optional source-site package JSON. Defaults to reviewPacket.sourcePackage when readable.")
    parser.add_argument("--objective", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-if-not-review-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    ensure_output_outside_skill(output)
    packet = load_review_json(Path(args.review_packet).expanduser(), "review packet")
    package_path = args.package or (packet.get("sourcePackage") if isinstance(packet.get("sourcePackage"), str) else "")
    package = load_json(package_path, "source package") if package_path else None
    coverage = build_coverage(
        packet,
        review_packet_path=args.review_packet,
        package=package,
        package_path=package_path,
        objective=args.objective,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
    if args.fail_if_not_review_ready and not coverage.get("reviewComplete"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
