#!/usr/bin/env python3
"""Pre-publish CONTENT QUALITY gate — catches junk that STRUCTURAL validators miss.

Structural completeness (fields present, slugs valid, source-refs resolve) stays in
validate_source_site_package.py. This gate asks a different question: is the CONTENT real,
on-topic, and decision-grade — or is it the kind of page that shipped an RF cable with a
tech-pouch's YKK-zipper specs and Unsplash stock photos?

BLOCKERS (pass=false): stock/placeholder images (in coverImage / media object-or-array /
gallery / top-level contentPlan.media / content), missing alt on a MAIN product image,
unreplaced placeholder/template markers. WARNINGS (need human/AI judgment): off-category or
leftover-demo terms, a spec table too thin for a technical buyer, near-duplicate copy, a
gallery image without alt (may be decorative), example.com references. Plus an aiReviewChecklist
for judgments that can't be automated (hallucinated specs, unbacked differentiators, fabricated
trust claims). --strict promotes warnings to blockers.

Aligned with references/source-material-norms.md (P1-P5 product / A1-A5 article) and the media
field contract (references/field-contract.md: coverImage/media/gallery, alt).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from _common import load_json, write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_content_quality_report"

# Public stock/placeholder image hosts — a B2B product page must show real product images.
STOCK_IMAGE_HOSTS = (
    "unsplash.com", "images.unsplash.com", "source.unsplash.com", "pexels.com", "pixabay.com",
    "placeholder.com", "via.placeholder.com", "placehold.co", "placehold.it", "lorempixel.com",
    "picsum.photos", "dummyimage.com", "loremflickr.com", "placekitten.com", "fakeimg.pl",
)

# Unmistakable placeholder / unfilled-template markers — must never reach a live page (BLOCK).
HARD_PLACEHOLDERS = (
    re.compile(r"\{\{"), re.compile(r"\}\}"), re.compile(r"\$\{"),
    re.compile(r"\blorem ipsum\b", re.IGNORECASE), re.compile(r"\bTODO\b"),
    re.compile(r"\[placeholder\]", re.IGNORECASE), re.compile(r"<placeholder>", re.IGNORECASE),
    re.compile(r"\bXYZ Corp\b", re.IGNORECASE),
    # build_content_skeleton.py leaves "[fill: ...]" markers where source is missing — an unfilled
    # skeleton must never publish, so its markers are hard placeholders too.
    re.compile(r"\[fill:", re.IGNORECASE),
)
# "TBD" only as a standalone token — so a real model number like TBD-500 is NOT hard-blocked (BLOCK).
TBD_STANDALONE = re.compile(r"(?<![\w-])TBD(?![\w-])")
# Softer signals — plausible in legit illustrative copy, so WARN rather than auto-reject.
SOFT_PLACEHOLDERS = (re.compile(r"\bexample\.com\b", re.IGNORECASE),)

# Leftover-demo / off-category fingerprints. The skill's demo template was a tech pouch, so its
# residue (zipper/ripstop/pouch...) landing in a cable's copy is the tell. WARN (not block): a
# vendor genuinely selling these would trip it, so an AI/human confirms. NOTE: this is a
# fingerprint of one known demo, not a general off-category detector — see aiReviewChecklist.
SUSPECT_CATEGORY_TERMS = (
    "pouch", "ykk", "ripstop", "zipper", "mesh pocket", "elastic keeper", "chargers and pens",
    "收纳", "拉链", "背包", "钱包", "the pouch opens flat",
)

MIN_SPECS = 3
MIN_DESCRIPTION_CHARS = 40
DUP_JACCARD = 0.85
DUP_MIN_CHARS = 60


def slate_text(node: Any) -> str:
    """Concatenate Slate `text` leaves only (ignores url/src attributes)."""
    out: list[str] = []

    def visit(n: Any) -> None:
        if isinstance(n, dict):
            if isinstance(n.get("text"), str):
                out.append(n["text"])
            for key, value in n.items():
                if key != "text":
                    visit(value)
        elif isinstance(n, list):
            for item in n:
                visit(item)

    visit(node)
    return " ".join(t for t in out if t)


def collect_image_urls(node: Any, urls: list[str]) -> None:
    """Find image-ish urls nested anywhere in a Slate content tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("url", "src", "href") and isinstance(value, str):
                urls.append(value)
            else:
                collect_image_urls(value, urls)
    elif isinstance(node, list):
        for item in node:
            collect_image_urls(item, urls)


def image_entries(value: Any, label: str) -> list[dict[str, Any]]:
    """Normalize a coverImage / media (object OR array) / gallery / top-level media field into
    a flat list of {url, alt, label}. Handles the documented shapes in field-contract.md."""
    items = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    entries: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict) and (item.get("url") or item.get("type") == "image"):
            entries.append({"url": str(item.get("url") or "").strip(), "alt": item.get("alt"), "label": label})
    return entries


def is_stock_image(url: str) -> bool:
    """Match stock hosts against the URL's netloc only (not a substring of the whole URL)."""
    netloc = urlparse(url.strip()).netloc.lower()
    if not netloc:
        return False
    return any(netloc == host or netloc.endswith("." + host) for host in STOCK_IMAGE_HOSTS)


def has_alt(entry: dict[str, Any]) -> bool:
    return isinstance(entry.get("alt"), str) and entry["alt"].strip() != ""


def product_texts(product: dict) -> list[str]:
    texts = [str(product.get("name") or ""), str(product.get("description") or "")]
    for spec in product.get("specifications") or []:
        if isinstance(spec, dict):
            texts.append(str(spec.get("key", "")))
            texts.append(str(spec.get("value", "")))
    texts.append(slate_text(product.get("content")))
    return texts


def placeholder_issues(texts: list[str], label: str, blockers: list[str], warnings: list[str]) -> None:
    hard = False
    soft = False
    for text in texts:
        if not hard and (any(rx.search(text) for rx in HARD_PLACEHOLDERS) or TBD_STANDALONE.search(text)):
            blockers.append(f"{label}: unreplaced placeholder/template text near '{text.strip()[:60]}'")
            hard = True
        if not soft and any(rx.search(text) for rx in SOFT_PLACEHOLDERS):
            warnings.append(f"{label}: references example.com — likely placeholder/illustrative, confirm it's intentional")
            soft = True


def image_issues(entries: list[dict[str, Any]], label: str, blockers: list[str], warnings: list[str],
                 *, alt_required: bool) -> None:
    for entry in entries:
        url = entry["url"]
        if url and is_stock_image(url):
            blockers.append(f"{label}: stock/placeholder image ({entry['label']}) not allowed on a real page: {url}")
        if url and not has_alt(entry):
            if alt_required:
                blockers.append(f"{label}: main image ({entry['label']}) is missing alt text (SEO + accessibility)")
            else:
                warnings.append(f"{label}: gallery image ({entry['label']}) has no alt (ok only if decorative)")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def duplicate_pairs(bodies: list[tuple[str, str]]) -> list[tuple[str, str]]:
    normed = [(label, _norm(text)) for label, text in bodies if len(_norm(text)) >= DUP_MIN_CHARS]
    pairs: list[tuple[str, str]] = []
    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            if jaccard(normed[i][1], normed[j][1]) > DUP_JACCARD:
                pairs.append((normed[i][0], normed[j][0]))
    return pairs


def check(package: Any, strict: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    content_plan = package.get("contentPlan") if isinstance(package, dict) else None
    content_plan = content_plan if isinstance(content_plan, dict) else {}
    products = content_plan.get("products") if isinstance(content_plan.get("products"), list) else []
    posts = content_plan.get("posts") if isinstance(content_plan.get("posts"), list) else []

    # Top-level site media
    image_issues(image_entries(content_plan.get("media"), "contentPlan.media"),
                 "contentPlan.media", blockers, warnings, alt_required=False)

    for index, product in enumerate(products):
        if not isinstance(product, dict):
            continue
        label = f"products[{index}]({product.get('slug') or product.get('name') or index})"
        texts = product_texts(product)
        placeholder_issues(texts, label, blockers, warnings)

        # Main product images: coverImage + media (object or array) — alt required.
        image_issues(image_entries(product.get("coverImage"), "coverImage")
                     + image_entries(product.get("media"), "media"),
                     label, blockers, warnings, alt_required=True)
        # Gallery — stock still blocks; missing alt only warns (may be decorative).
        image_issues(image_entries(product.get("gallery"), "gallery"),
                     label, blockers, warnings, alt_required=False)
        # Images embedded in the Slate content body (stock only; body images have no alt contract here).
        content_urls: list[str] = []
        collect_image_urls(product.get("content"), content_urls)
        for url in content_urls:
            if is_stock_image(url):
                blockers.append(f"{label}: stock/placeholder image in content body: {url}")

        concrete_specs = [s for s in (product.get("specifications") or [])
                          if isinstance(s, dict) and str(s.get("value", "")).strip()]
        if len(concrete_specs) < MIN_SPECS:
            warnings.append(f"{label}: only {len(concrete_specs)} concrete spec(s) — a technical buyer needs a "
                            f"decision-grade spec table (>= {MIN_SPECS}, norms P2)")

        desc = str(product.get("description") or "")
        if desc.strip() and len(desc.strip()) < MIN_DESCRIPTION_CHARS:
            warnings.append(f"{label}: description under {MIN_DESCRIPTION_CHARS} chars — too thin to establish "
                            "relevance (norms P1)")

        joined = " ".join(texts).lower()
        hits = sorted({term for term in SUSPECT_CATEGORY_TERMS if term in joined})
        if hits:
            warnings.append(f"{label}: off-category / leftover-demo terms {hits} — AI must confirm these belong to "
                            "this product's category and are not leftover template/demo copy")

    for index, post in enumerate(posts):
        if not isinstance(post, dict):
            continue
        label = f"posts[{index}]({post.get('slug') or post.get('title') or index})"
        placeholder_issues([str(post.get("title") or ""), str(post.get("excerpt") or ""),
                            slate_text(post.get("content"))], label, blockers, warnings)
        image_issues(image_entries(post.get("coverImage"), "coverImage")
                     + image_entries(post.get("media"), "media"),
                     label, blockers, warnings, alt_required=True)
        content_urls = []
        collect_image_urls(post.get("content"), content_urls)
        for url in content_urls:
            if is_stock_image(url):
                blockers.append(f"{label}: stock/placeholder image in content body: {url}")

    bodies = [(f"products[{i}]", slate_text(p.get("content"))) for i, p in enumerate(products) if isinstance(p, dict)]
    bodies += [(f"posts[{i}]", slate_text(p.get("content"))) for i, p in enumerate(posts) if isinstance(p, dict)]
    for a, b in duplicate_pairs(bodies):
        warnings.append(f"near-duplicate body copy between {a} and {b} — SEO duplicate-content risk; each item needs unique copy")

    checklist = [
        "Specs actually belong to THIS product's category — no hallucinated or borrowed parameters (norms P2)",
        "Each differentiator is backed by a concrete number or mechanism, not adjectives (norms P3)",
        "Trust claims (certs, benchmarks, warranty, stock, price) are user-supplied, never fabricated (norms P4)",
        "Copy is unique to this item, not a reworded template or a competitor-generic paragraph",
        "Product images are real product photos (not stock), each main image with descriptive alt text",
        "Leftover-demo prose with none of the known fingerprint terms is NOT auto-caught — read the body once for off-topic copy",
    ]

    passed = not blockers and (not strict or not warnings)
    return {
        "kind": KIND,
        "generatedAt": now_iso(),
        "pass": passed,
        "strict": strict,
        "productsChecked": len(products),
        "postsChecked": len(posts),
        "blockers": blockers,
        "warnings": warnings,
        "aiReviewChecklist": checklist,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-publish content-quality gate for an AllinCMS content package.")
    parser.add_argument("--package", required=True, help="Content package / source wiki JSON with a contentPlan")
    parser.add_argument("--output", default="", help="Optional path to write the quality report JSON (outside the skill)")
    parser.add_argument("--strict", action="store_true", help="Promote warnings to blockers (fail on any warning too)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    package = load_json(args.package, "content package")
    report = check(package, strict=args.strict)

    if args.output:
        output = ensure_output_outside_skill(Path(args.output).expanduser())
        write_json(output, report)
        print(f"Wrote content-quality report: {output}")

    print(f"pass={str(report['pass']).lower()} products={report['productsChecked']} posts={report['postsChecked']} "
          f"blockers={len(report['blockers'])} warnings={len(report['warnings'])}")
    for issue in report["blockers"]:
        print(f"  BLOCK {issue}")
    for issue in report["warnings"]:
        print(f"  warn  {issue}")
    if report["blockers"] or report["warnings"]:
        print("AI self-review before publishing:")
        for item in report["aiReviewChecklist"]:
            print(f"  - {item}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
