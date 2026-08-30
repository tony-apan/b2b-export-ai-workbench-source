#!/usr/bin/env python3
"""Pre-publish CONTENT-FORMAT gate — is the body readable/scannable, or a flat paragraph wall?

check_content_quality.py asks "is the content correct" (no placeholders/stock images/hallucinated
specs). This gate asks a different question: is the body FORMATTED like a professional page —
section headings, bold on key facts, bullet lists for differentiators/applications, an explicit
CTA — or is it undifferentiated prose a scan-reader bounces off (the "correct but a paragraph wall"
page)? Reads the Slate content nodes of each product/post and flags structure gaps.

Rules (references/content-format-standard.md): >=2 section headings; some bold; a list for the
differentiators/applications; an end-of-body CTA; no over-long paragraph walls. A long body with
ZERO structure (no heading, no list, no bold) is a BLOCK; single missing pieces are WARNINGS.
--strict promotes warnings to blockers.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _common import load_json, write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_content_format_report"

MIN_HEADINGS = 2
WALL_TEXT_MIN = 300        # a body this long with zero structure (no heading/list/bold) is a paragraph wall
MAX_PARAGRAPH_CHARS = 600  # a single paragraph longer than this should be split or listed

# CTA terms are matched as phrases, not bare words, so spec terminology doesn't read as a CTA
# (e.g. "contact resistance" / "ordering code" are NOT a call-to-action).
CTA_TERMS = ("quote", "datasheet", "data sheet", "contact us", "contact our", "contact sales",
             "get in touch", "request a", "request the", "place an order", "order now", "inquiry",
             "enquire", "配置报价", "报价", "询价", "咨询", "联系我们", "索取", "下一步", "订购")


# Node-type matchers are best-effort: they cover standard SlateJS conventions + content-format-standard's
# authoring spec. No real AllinCMS heading/list/bold save payload is captured in the repo yet; when one is,
# freeze it into a test fixture and extend these. A WALL block needs headings==0 AND lists==0 AND not bold
# all at once, so a matcher miss degrades to at most a spurious WARN, never a false block.
def _is_heading(t: str) -> bool:
    t = t.lower()
    return t in ("h1", "h2", "h3", "h4", "heading", "heading-one", "heading-two", "heading-three") or "head" in t


def _is_list(t: str) -> bool:
    t = t.lower()
    return t in ("ul", "ol", "bulleted-list", "numbered-list", "list") or t.endswith("-list") or t == "list-item"


def _para_text(node: dict) -> str:
    out = []

    def leaf(n):
        if isinstance(n, dict):
            if isinstance(n.get("text"), str):
                out.append(n["text"])
            for k, v in n.items():
                if k != "text":
                    leaf(v)
        elif isinstance(n, list):
            for x in n:
                leaf(x)

    leaf(node)
    return " ".join(out)


def analyze_body(content) -> dict:
    headings = lists = 0
    has_bold = False
    longest_para = 0
    all_text = []

    def visit(node):
        nonlocal headings, lists, has_bold, longest_para
        if isinstance(node, dict):
            t = str(node.get("type", ""))
            if _is_heading(t):
                headings += 1
            if _is_list(t):
                lists += 1
            if t in ("p", "paragraph", ""):
                # a leaf-bearing block: measure its text length
                pt = _para_text(node)
                if pt:
                    longest_para = max(longest_para, len(pt))
            if node.get("bold") is True or node.get("strong") is True:
                has_bold = True
            if isinstance(node.get("text"), str):
                all_text.append(node["text"])
            for k, v in node.items():
                if k != "text":
                    visit(v)
        elif isinstance(node, list):
            for x in node:
                visit(x)

    visit(content)
    text = " ".join(all_text)
    return {
        "headings": headings, "lists": lists, "hasBold": has_bold,
        "longestParagraph": longest_para, "textLen": len(text),
        "hasCta": any(term in text.lower() for term in CTA_TERMS),
    }


def _issues_for(label: str, content, blockers: list, warnings: list) -> None:
    a = analyze_body(content)
    if a["textLen"] == 0:
        return
    # A long body with zero structure at all = a paragraph wall.
    if a["textLen"] >= WALL_TEXT_MIN and a["headings"] == 0 and a["lists"] == 0 and not a["hasBold"]:
        blockers.append(f"{label}: body is a paragraph WALL ({a['textLen']} chars, no headings, no lists, no bold) "
                        "— structure it per content-format-standard (H2 sections, bold key facts, bullet lists)")
        return
    if a["headings"] < MIN_HEADINGS:
        warnings.append(f"{label}: only {a['headings']} section heading(s) (<{MIN_HEADINGS}) — add H2 sections "
                        "(key specs / why choose it / applications / trust / CTA)")
    if not a["hasBold"]:
        warnings.append(f"{label}: no bold anywhere — emphasize key specs / selling points / the CTA action")
    if a["lists"] == 0:
        warnings.append(f"{label}: no bullet/numbered list — put differentiators and applications in lists, not prose")
    if not a["hasCta"]:
        warnings.append(f"{label}: no CTA / next step in the body — end with an explicit ask (request a quote / datasheet)")
    if a["longestParagraph"] > MAX_PARAGRAPH_CHARS:
        warnings.append(f"{label}: an over-long paragraph ({a['longestParagraph']} chars) — split it or turn it into a list")


def check(package, strict: bool = False) -> dict:
    blockers: list = []
    warnings: list = []
    cp = package.get("contentPlan") if isinstance(package, dict) else None
    cp = cp if isinstance(cp, dict) else {}
    products = cp.get("products") if isinstance(cp.get("products"), list) else []
    posts = cp.get("posts") if isinstance(cp.get("posts"), list) else []

    for i, p in enumerate(products):
        if isinstance(p, dict):
            _issues_for(f"products[{i}]({p.get('slug') or p.get('name') or i})", p.get("content"), blockers, warnings)
    for i, p in enumerate(posts):
        if isinstance(p, dict):
            _issues_for(f"posts[{i}]({p.get('slug') or p.get('title') or i})", p.get("content"), blockers, warnings)

    passed = not blockers and (not strict or not warnings)
    return {
        "kind": KIND, "generatedAt": now_iso(), "pass": passed, "strict": strict,
        "productsChecked": len(products), "postsChecked": len(posts),
        "blockers": blockers, "warnings": warnings,
        "formatChecklist": [
            "Body reads as scannable sections (H2), not one prose block (content-format-standard)",
            "Key specs / selling points / CTA are bolded — sparingly, not everywhere",
            "Differentiators (>=2, each with a number/mechanism) and applications are in lists",
            "Body ends with an explicit next step / CTA (request a quote, get the datasheet)",
            "Product image sits after the title / beside its section, not before with no context",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-publish content-format (readability/structure) gate.")
    parser.add_argument("--package", required=True, help="Content package JSON with a contentPlan")
    parser.add_argument("--output", default="", help="Optional path to write the report JSON (outside the skill)")
    parser.add_argument("--strict", action="store_true", help="Promote format warnings to blockers")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = check(load_json(args.package, "content package"), strict=args.strict)
    if args.output:
        write_json(ensure_output_outside_skill(Path(args.output).expanduser()), report)
        print(f"Wrote content-format report: {report['pass']}")
    print(f"pass={str(report['pass']).lower()} products={report['productsChecked']} posts={report['postsChecked']} "
          f"blockers={len(report['blockers'])} warnings={len(report['warnings'])}")
    for b in report["blockers"]:
        print(f"  BLOCK {b}")
    for w in report["warnings"]:
        print(f"  warn  {w}")
    if report["blockers"] or report["warnings"]:
        print("Format self-review (content-format-standard.md):")
        for item in report["formatChecklist"]:
            print(f"  - {item}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
