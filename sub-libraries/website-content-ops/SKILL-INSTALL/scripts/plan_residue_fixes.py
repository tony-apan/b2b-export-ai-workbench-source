#!/usr/bin/env python3
"""Turn a residue report into a per-type FIX WORK-ORDER — the missing link between "the residue gate
found leftovers on many pages" and "fix each one, by type, to zero".

check_template_residue.py finds WHERE old content survives (route + term + label). But leftovers on a
converted site are spread across content TYPES — product detail pages, post detail pages, standalone
theme pages, taxonomy chips, global blocks (footer/nav/contact modal), homepage modules — and EACH
type is fixed a different way (product/post save, backend category tab, theme page design, global-block
designer layer). That how-to-fix knowledge already lives in references/batch-verification.md as prose an
AI must remember. This tool routes every hit to its fix target so the AI works through them by type,
misses none, and doesn't edit the wrong layer.

Input: a check_template_residue report (its residueHits). Output: hits grouped by fixType, each with the
fix method and the re-verify step. It does NOT mutate anything — it plans the fixes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import load_json, write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_residue_fix_plan"

# label values come from the residue blacklist; route prefixes from the live site.
FIX_METHODS = {
    "taxonomy_chip": {
        "method": "Fix in the BACKEND category/tag tab (rename the term or fix the content association) — "
                  "NOT by editing the page designer. Chip residue is separate from page-copy residue.",
        "verify": "Re-check the chip on BOTH list pages (/products, /posts) and the item detail pages.",
    },
    "product_detail": {
        "method": "Capture the product's current save schema, then JSON-replace the residual fields "
                  "(name/description/content body/spec rows/category ids). Spec rows especially: replace "
                  "off-domain default spec rows (material/zipper/care...).",
        "verify": "Re-open the product detail route and confirm the term is gone from visible text.",
    },
    "post_detail": {
        "method": "JSON-replace the post's residual fields (title/excerpt/content body) via the captured "
                  "post save schema.",
        "verify": "Re-open the post detail route and confirm the term is gone.",
    },
    "theme_page": {
        "method": "Edit this standalone page's residual block in the theme page designer and publish; "
                  "verify at the public page level, not just in the designer chat/action log.",
        "verify": "Reload the public page route and confirm the term is gone.",
    },
    "global_block": {
        "method": "Contact/brand residue often lives in a GLOBAL block (header/footer/nav/contact "
                  "modal/newsletter/floating button). Select the exact designer layer that OWNS the "
                  "residue (a global modal shell may not own a nearby page-level address), edit, publish.",
        "verify": "Reload MULTIPLE routes (global blocks appear site-wide); confirm gone on each.",
    },
    "homepage_module": {
        "method": "Edit the owning homepage module (Hero/Banner/Category/Featured/News/Contact block) "
                  "and publish.",
        "verify": "Reload the homepage and confirm the term is gone from that module.",
    },
}

TAXONOMY_LABELS = ("old_category", "old_tag")
HARD_CONTACT_LABELS = ("old_email", "old_phone", "old_address")   # near-certainly a site-wide global block
SOFT_CONTACT_LABELS = ("old_brand", "old_cta", "old_domain")      # can also sit in product/post body copy


def classify(route: str, label: str) -> str:
    route = (route or "").strip()
    label = (label or "").strip()
    if label in TAXONOMY_LABELS:
        return "taxonomy_chip"                      # a chip is fixed in the backend tab wherever it shows
    if label in HARD_CONTACT_LABELS:
        return "global_block"                       # email/phone/address live in a global block — label wins over route
    if route.startswith("/products/"):
        return "product_detail"
    if route.startswith("/posts/"):
        return "post_detail"
    if label in SOFT_CONTACT_LABELS:
        return "global_block"                       # brand/domain/CTA outside a product/post route → a global block
    if route in ("/", "/home", ""):
        return "homepage_module"
    return "theme_page"                             # a named standalone page (/about, /contact, ...)


def plan(report: dict) -> dict:
    raw = report.get("residueHits") if isinstance(report, dict) else None
    raw = raw if isinstance(raw, list) else []
    hits = [h for h in raw if isinstance(h, dict)]
    skipped = len(raw) - len(hits)               # malformed non-dict entries dropped, counted, not silent
    groups: dict[str, list[dict]] = {}
    for hit in hits:
        fix_type = classify(str(hit.get("route", "")), str(hit.get("label", "")))
        groups.setdefault(fix_type, []).append({
            "route": hit.get("route"), "term": hit.get("term"), "label": hit.get("label"),
        })

    fix_groups = []
    for fix_type, group_hits in sorted(groups.items()):
        meta = FIX_METHODS[fix_type]
        fix_groups.append({
            "fixType": fix_type,
            "hitCount": len(group_hits),
            "method": meta["method"],
            "verifyAfter": meta["verify"],
            "hits": group_hits,
        })

    return {
        "kind": KIND,
        "generatedAt": now_iso(),
        "totalHits": len(hits),
        "skippedMalformed": skipped,
        "fixGroups": fix_groups,
        "note": ("Work through the groups by type; each is a distinct fix action, not page-designer poking. "
                 "After fixing a group, re-verify its routes are clean, then re-run check_template_residue "
                 "over the WHOLE site — launch only when it reports zero residue."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan per-type fixes for a residue report.")
    parser.add_argument("--report", required=True, help="A check_template_residue report JSON (with residueHits)")
    parser.add_argument("--output", default="", help="Optional path to write the fix plan JSON (outside the skill)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = load_json(args.report, "residue report")
    result = plan(report)

    if args.output:
        output = ensure_output_outside_skill(Path(args.output).expanduser())
        write_json(output, result)
        print(f"Wrote residue fix plan: {output}")

    print(f"total residue hits: {result['totalHits']} across {len(result['fixGroups'])} fix type(s)")
    for g in result["fixGroups"]:
        print(f"\n[{g['fixType']}] {g['hitCount']} hit(s)")
        print(f"  fix: {g['method']}")
        print(f"  verify: {g['verifyAfter']}")
        for h in g["hits"]:
            print(f"    - {h['route']} :: '{h['term']}' ({h['label']})")
    if result["fixGroups"]:
        print(f"\n{result['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
