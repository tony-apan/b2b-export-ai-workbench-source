#!/usr/bin/env python3
"""Generation-time AUTHORING scaffold — build a content-format-standard body BEFORE writing prose.

The format/quality gates are validators: they catch a bad body AFTER it is written. This flips the
order. Given a product/post's structured source fields (name, description, specifications,
differentiators, applications), it emits a Slate body pre-structured into the information
architecture of references/content-format-standard.md — a hook paragraph with a bolded key fact,
H2 sections (key specs / why choose it / applications), bullet lists, and an explicit CTA — so the
AI FILLS real leaf text into a correct structure instead of free-writing a paragraph wall.

Correct-by-construction: a skeleton it emits is designed to PASS check_content_format (>=2 headings,
a list, bold, a CTA). test_build_content_skeleton.py cross-checks that with the real gate. It does
NOT invent business facts: sections whose source is missing are reported in `needs` and the item is
`ready=false` — the downstream check_content_quality still blocks thin/placeholder bodies. So this
guarantees STRUCTURE, never the QUALITY or truth of the prose the AI fills in — that stays an AI
self-review + human-review responsibility.

Usage:
  build_content_skeleton.py --package pkg.json                 # report skeleton + needs per item
  build_content_skeleton.py --package pkg.json --apply -o out  # write skeleton into items with a thin/missing body
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import load_json, write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_content_skeleton_report"

# A body already this long is treated as authored; --apply won't overwrite it. A shorter existing
# body IS overwritten by the skeleton — so don't --apply over hand-written intros under this length.
AUTHORED_MIN_CHARS = 200
# Generic, non-fabricated CTA — an action prompt, asserts no price/contact/inventory fact.
DEFAULT_CTA = "Request a quote or the full datasheet for your configuration."


def _as_list(v) -> list:
    return v if isinstance(v, list) else ([] if v is None else [v])


def _text(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _spec_pairs(product: dict) -> list[tuple[str, str]]:
    pairs = []
    for s in _as_list(product.get("specifications")):
        if isinstance(s, dict):
            k, val = _text(s.get("key")), _text(s.get("value"))
            if k and val:
                pairs.append((k, val))
    return pairs


def _para(children) -> dict:
    return {"type": "paragraph", "children": children}


def _h2(t: str) -> dict:
    return {"type": "h2", "children": [{"text": t}]}


def _ul(items: list[str]) -> dict:
    return {"type": "ul", "children": [{"type": "li", "children": [{"text": it}]} for it in items]}


def build_product_body(product: dict) -> dict:
    """Return {content, needs, ready}. content is a content-format-standard Slate body."""
    needs: list[str] = []
    name = _text(product.get("name")) or "This product"
    desc = _text(product.get("description"))
    specs = _spec_pairs(product)
    diffs = [_text(d) for d in _as_list(product.get("differentiators")) if _text(d)]
    apps = [_text(a) for a in _as_list(product.get("applications")) if _text(a)]

    if not desc:
        needs.append("description (one-sentence positioning: what it is / who it's for / headline spec)")
    if not specs:
        needs.append("specifications (>=1 structured key/value that drives selection)")
    if len(diffs) < 2:
        needs.append("differentiators (>=2, each bound to a number/mechanism)")
    if not apps:
        needs.append("applications (>=1 concrete use)")

    content: list[dict] = []

    # 1. Hook paragraph — positioning + a bolded key fact. Bold the top spec value, else the name.
    if specs:
        k0, v0 = specs[0]
        hook = [{"text": (desc + " " if desc else f"{name}. ")}, {"text": v0, "bold": True},
                {"text": f" {k0}."}]
    else:
        hook = [{"text": (desc + " " if desc else "")}, {"text": name, "bold": True}, {"text": "."}]
    content.append(_para(hook))

    # 2. Key specifications section (body references the structured spec table).
    content.append(_h2("Key specifications"))
    if specs:
        content.append(_ul([f"{k}: {v}" for k, v in specs[:6]]))
    else:
        content.append(_para([{"text": "[fill: list the selection-driving specs from the specifications field]"}]))

    # 3. Why choose it — differentiators as bullets.
    content.append(_h2("Why choose it"))
    if diffs:
        content.append(_ul(diffs))
    else:
        content.append(_ul(["[fill: differentiator #1 + a number/mechanism]",
                             "[fill: differentiator #2 + a number/mechanism]"]))

    # 4. Applications — as bullets.
    content.append(_h2("Typical applications"))
    if apps:
        content.append(_ul(apps))
    else:
        content.append(_ul(["[fill: a concrete application/use case]"]))

    # 5. CTA — always present, generic action (no fabricated contact/price).
    content.append(_h2("Get a quote"))
    cta = _text(product.get("cta")) or DEFAULT_CTA
    content.append(_para([{"text": cta}]))

    return {"content": content, "needs": needs, "ready": not needs}


def build_post_body(post: dict) -> dict:
    """Articles: hook problem -> mechanism -> maps to product -> CTA. Structure-first like products."""
    needs: list[str] = []
    excerpt = _text(post.get("excerpt"))
    mechanism = _text(post.get("mechanism")) or _text(post.get("summary"))
    takeaways = [_text(t) for t in _as_list(post.get("takeaways")) if _text(t)]

    if not excerpt:
        needs.append("excerpt (one sharp insight the article delivers)")
    if not mechanism:
        needs.append("mechanism/summary (the why / trade-off the reader learns)")
    if len(takeaways) < 2:
        needs.append("takeaways (>=2 usable judgement points)")

    content: list[dict] = []
    if excerpt:
        content.append(_para([{"text": excerpt + " "}, {"text": "Here is what matters.", "bold": True}]))
    else:
        content.append(_para([{"text": "[fill: hook — the reader's real question] "},
                              {"text": "Here is what matters.", "bold": True}]))
    content.append(_h2("Why this matters"))
    content.append(_para([{"text": mechanism or "[fill: the mechanism / trade-off the reader should weigh]"}]))
    content.append(_h2("What to weigh"))
    content.append(_ul(takeaways or ["[fill: usable judgement point #1]", "[fill: usable judgement point #2]"]))
    content.append(_h2("Next step"))
    content.append(_para([{"text": _text(post.get("cta")) or DEFAULT_CTA}]))
    return {"content": content, "needs": needs, "ready": not needs}


def _body_len(content) -> int:
    out = []

    def visit(n):
        if isinstance(n, dict):
            if isinstance(n.get("text"), str):
                out.append(n["text"])
            for k, v in n.items():
                if k != "text":
                    visit(v)
        elif isinstance(n, list):
            for x in n:
                visit(x)

    visit(content)
    return len(" ".join(out))


def process(package: dict, apply: bool) -> dict:
    cp = package.get("contentPlan") if isinstance(package, dict) else None
    cp = cp if isinstance(cp, dict) else {}
    products = cp.get("products") if isinstance(cp.get("products"), list) else []
    posts = cp.get("posts") if isinstance(cp.get("posts"), list) else []

    items: list[dict] = []
    applied = 0
    for scope, coll, builder in (("products", products, build_product_body), ("posts", posts, build_post_body)):
        for i, it in enumerate(coll):
            if not isinstance(it, dict):
                continue
            label = f"{scope}[{i}]({it.get('slug') or it.get('name') or it.get('title') or i})"
            existing_len = _body_len(it.get("content"))
            skel = builder(it)
            record = {"item": label, "needs": skel["needs"], "ready": skel["ready"],
                      "existingBodyChars": existing_len}
            if apply and existing_len < AUTHORED_MIN_CHARS:
                it["content"] = skel["content"]
                record["applied"] = True
                applied += 1
            else:
                record["applied"] = False
                record["skeleton"] = skel["content"]
            items.append(record)

    return {
        "kind": KIND, "generatedAt": now_iso(), "applied": apply, "appliedCount": applied,
        "items": items,
        "authoringChecklist": [
            "The skeleton fixes STRUCTURE only — you still fill real leaf text (specs, selling points).",
            "Replace every [fill: ...] marker with source-backed content; do not publish markers.",
            "Bold the genuinely key fact, not filler; keep bold to <=1-2 per paragraph.",
            "After filling, run check_content_format and check_content_quality; --strict for product/post bodies.",
            "needs!=[] means the source is missing fields — get them; do not fabricate to fill the gap.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generation-time content-format-standard authoring scaffold.")
    parser.add_argument("--package", required=True, help="Content package JSON with a contentPlan")
    parser.add_argument("--apply", action="store_true", help="Write skeletons into items whose body is thin/missing")
    parser.add_argument("--output", "-o", default="", help="Where to write (report, or the applied package with --apply)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    package = load_json(args.package, "content package")
    report = process(package, args.apply)

    if args.apply and args.output:
        write_json(ensure_output_outside_skill(Path(args.output).expanduser()), package)
        print(f"Applied {report['appliedCount']} skeleton(s); wrote package -> {args.output}")
    elif args.output:
        write_json(ensure_output_outside_skill(Path(args.output).expanduser()), report)
        print(f"Wrote skeleton report -> {args.output}")

    not_ready = [it for it in report["items"] if not it["ready"]]
    print(f"items={len(report['items'])} applied={report['appliedCount']} needsSource={len(not_ready)}")
    for it in report["items"]:
        flag = "APPLIED" if it["applied"] else ("ready" if it["ready"] else "needs-source")
        print(f"  [{flag}] {it['item']}" + (f" -> {', '.join(it['needs'])}" if it["needs"] else ""))
    if not_ready:
        print("Authoring checklist:")
        for c in report["authoringChecklist"]:
            print(f"  - {c}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
