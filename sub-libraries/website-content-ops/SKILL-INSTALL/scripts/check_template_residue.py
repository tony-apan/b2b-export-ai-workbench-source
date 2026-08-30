#!/usr/bin/env python3
"""Whole-site TEMPLATE-RESIDUE gate — makes the "no default-template residue" launch rule ENFORCED.

The skill already knows residue is a launch blocker and lists where it hides (batch-verification.md:
static pages, header, footer, CTAs, category/tag chips, recommended blocks, contact details in
global modals/footers/newsletter, product spec rows). But that was prose an AI could skip — so a
site converted from a retail template shipped with the old brand, old products, old category chips,
and old contact info still scattered across dozens of spots, reported as "minor residue".

This gate turns "should scan" into "must scan". Feed it:
  --blacklist  the site's OLD default-template fingerprints captured BEFORE conversion
               (old brand, product names, category/tag names, emails, phones, addresses, domains,
               authors, CTA copy) — the strings that must appear NOWHERE after conversion.
  --frontend   the visible text of EVERY live route (home + each product + each post + each page +
               header/footer/nav/meta), captured live after publish.
It scans every route for every blacklist term. Any hit = BLOCK, with the exact route + term.
Zero hits across all routes is the launch condition — not the AI's own "looks done".

Complements check_content_quality.py: that gate asks "is the NEW content good"; this one asks
"is the OLD template content fully gone".
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _common import load_json, write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_template_residue_report"
MIN_TERM_LEN = 4  # shorter blacklist terms are collision-prone (e.g. a generic word) -> warn


def _terms(blacklist: Any) -> list[dict[str, str]]:
    """Normalize blacklist into [{value, label}]. Accepts {'terms':[...]} of strings or {value,label}."""
    raw = blacklist.get("terms") if isinstance(blacklist, dict) else blacklist
    out: list[dict[str, str]] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str) and item.strip():
            out.append({"value": item.strip(), "label": "old_content"})
        elif isinstance(item, dict) and str(item.get("value", "")).strip():
            out.append({"value": str(item["value"]).strip(), "label": str(item.get("label") or "old_content")})
    return out


def _routes(frontend: Any) -> list[dict[str, str]]:
    raw = frontend.get("routes") if isinstance(frontend, dict) else frontend
    out: list[dict[str, str]] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            out.append({"route": str(item.get("route") or item.get("url") or "?"),
                        "text": str(item.get("text") or item.get("visibleText") or "")})
    return out


def check(blacklist: Any, frontend: Any) -> dict[str, Any]:
    terms = _terms(blacklist)
    routes = _routes(frontend)
    errors: list[str] = []
    warnings: list[str] = []
    if not terms:
        errors.append("blacklist has no terms — capture the OLD template fingerprints before conversion")
    if not routes:
        errors.append("frontend has no routes — capture visible text of every live route after publish")

    short = sorted({t["value"] for t in terms if len(t["value"]) < MIN_TERM_LEN})
    if short:
        warnings.append(f"blacklist terms shorter than {MIN_TERM_LEN} chars are collision-prone (may false-hit "
                        f"legitimate copy) — prefer exact old identifiers: {short}")

    residue_hits: list[dict[str, Any]] = []
    for route in routes:
        haystack = route["text"].casefold()
        if not haystack.strip():
            warnings.append(f"route {route['route']} has empty visible text — was it actually captured?")
            continue
        for term in terms:
            needle = term["value"].casefold()
            count = haystack.count(needle)
            if count:
                residue_hits.append({"route": route["route"], "term": term["value"],
                                     "label": term["label"], "count": count})

    passed = not errors and not residue_hits
    return {
        "kind": KIND,
        "generatedAt": now_iso(),
        "pass": passed,
        "routesScanned": len(routes),
        "blacklistTerms": len(terms),
        "residueHits": residue_hits,
        "errors": errors,
        "warnings": warnings,
        "coverageNote": (f"Zero residue covers ONLY the {len(routes)} route(s) submitted here; it does not prove "
                         "the whole site was inspected. Route COMPLETENESS (every product/post/page captured) is a "
                         "separate gate — the final frontend audit reconciles route counts/URLs against the "
                         "confirmed package before launch acceptance."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Whole-site template-residue gate for a converted AllinCMS site.")
    parser.add_argument("--blacklist", required=True, help="Old default-template fingerprints JSON (terms to eradicate)")
    parser.add_argument("--frontend", required=True, help="Visible text of every live route JSON")
    parser.add_argument("--output", default="", help="Optional path to write the residue report JSON (outside the skill)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    blacklist = load_json(args.blacklist, "residue blacklist")
    frontend = load_json(args.frontend, "frontend routes")
    report = check(blacklist, frontend)

    if args.output:
        output = ensure_output_outside_skill(Path(args.output).expanduser())
        write_json(output, report)
        print(f"Wrote template-residue report: {output}")

    print(f"pass={str(report['pass']).lower()} routes={report['routesScanned']} terms={report['blacklistTerms']} "
          f"residueHits={len(report['residueHits'])}")
    for err in report["errors"]:
        print(f"  ERROR {err}")
    for hit in report["residueHits"]:
        print(f"  RESIDUE {hit['route']} still shows old {hit['label']}: '{hit['term']}' (x{hit['count']})")
    for warn in report["warnings"]:
        print(f"  warn  {warn}")
    if report["residueHits"]:
        print("Fix: edit or DELETE the source of each hit (old category/tag in backend tabs, footer/header/"
              "modal global blocks, product spec rows), republish, recapture the route text, and re-run to zero.")
    print(f"  scope: {report['coverageNote']}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
