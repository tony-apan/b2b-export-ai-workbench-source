#!/usr/bin/env python3
"""Resolve the RUN MODE and decide which quality gates apply — so the whole-site template-residue
gate is enforced when it matters (new/converted sites carry demo residue) and skipped when it
doesn't (daily incremental updates to a site that's already yours and clean).

Three modes:
  from_scratch        — a NEW site was created. It always ships AllinCMS default-template demo
                        content, so residue MUST be cleared. Auto-resolved, no user prompt.
  template_conversion — an EXISTING generic/old-brand site is being converted. Demo/old residue is
                        scattered across it, so the residue gate is required.
  incremental_update  — a DAILY update to a site that is already yours and already clean. No
                        whole-site residue risk, so the residue gate is skipped (new/changed items
                        are still content-quality checked).

Key safety rule: for an EXISTING site the skill cannot tell conversion from daily update, so it MUST
ask the user, and until answered it defaults to conversion (residue gate ON). incremental_update is
NEVER a silent default — only an explicit user declaration (or a confirmed answer) selects it. That
biases every ambiguous case toward scanning, never toward silently shipping leftover template content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _common import write_json, ensure_output_outside_skill, now_iso

KIND = "allincms_run_mode_decision"
MODES = ("from_scratch", "template_conversion", "incremental_update")

CONFIRMATION_PROMPT = (
    "ASK THE USER before treating an existing site as clean — in THEIR OWN language, in plain everyday "
    "words, no jargon (do not say 'residue'/'gate'/'conversion'/'incremental'). Use the ready-made "
    "wording below, and make sure they can tell the two cases apart AND understand what happens if they "
    "pick wrong.\n\n"
    "【中文·请照这个问】你选的是一个【已经存在的网站】。先确认一件事,免得弄错——它现在是下面哪种?\n"
    "  ① 它现在还是个「演示模板」或「别人的旧网站」,你要把它改造成你自己的品牌。\n"
    "     (页面上还留着一堆不是你的东西:别的公司名、别的产品、别的联系方式、样例文章…)\n"
    "     → 我会把整个网站从头到尾扫一遍,只要还有一处旧内容没清干净,就拦住不让上线。\n"
    "  ② 它已经是【你自己的】网站,内容都是对的、干净的,你这次只是来加一点或改一点。\n"
    "     (比如上一个新产品、改一篇文章)\n"
    "     → 我就不做全站大扫除了,只检查你这次新加或改动的内容。\n"
    "  选 ① 还是 ②?  ⚠ 说错的后果:本该是①(改造)你却选了②,那些旧公司名、旧产品、旧联系方式\n"
    "  会悄悄留在你上线的网站上、没人发现;本该是②你选了①,最多我白扫一遍、没坏处。\n"
    "  所以——拿不准就选 ①。你不回答的话,我默认按 ①(全站扫),宁可多扫,也绝不漏掉旧内容。\n\n"
    "【EN·same question】Your existing site — which is it? (1) still a demo template / someone else's old "
    "site you're rebranding (pages still show names, products, contacts, sample articles that aren't "
    "yours) → I sweep the WHOLE site and block launch if ANY old content is left; or (2) already YOUR "
    "own clean site, you're just adding/editing a little → I skip the sweep and only check new/changed "
    "items. If it's really (1) but you say (2), old names/products/contacts silently stay on your live "
    "site; if (2) but you say (1), worst case I sweep once for nothing. When unsure, pick (1). No answer "
    "= I default to (1), full sweep ON."
)


def resolve_run_mode(site_creation_status: str = "", declared_mode: str = "",
                     demo_signal_count: int = 0) -> dict[str, Any]:
    status = (site_creation_status or "").strip()
    declared = (declared_mode or "").strip()
    reasons: list[str] = []
    needs_confirmation = False

    if declared in MODES:
        mode = declared
        reasons.append(f"user-declared mode: {declared}")
    elif status == "created_verified":
        mode = "from_scratch"
        reasons.append("a newly created site always ships AllinCMS default-template demo content; residue must be cleared")
    elif status == "existing_site_selected":
        needs_confirmation = True
        mode = "template_conversion"  # SAFE DEFAULT: unknown existing site treated as conversion until user says daily
        if demo_signal_count > 0:
            reasons.append(f"existing site shows {demo_signal_count} demo/template fingerprint(s) — likely a conversion; CONFIRM with user")
        else:
            reasons.append("existing site: cannot tell conversion from daily update — CONFIRM with user; "
                           "defaulting to conversion (residue gate ON) until told it is incremental")
    else:
        mode = "template_conversion"
        needs_confirmation = True
        reasons.append(f"unknown site-creation status {status!r}; defaulting to conversion (residue gate ON), confirm with user")

    residue_required = mode in ("from_scratch", "template_conversion")
    return {
        "kind": KIND,
        "generatedAt": now_iso(),
        "mode": mode,
        "needsUserConfirmation": needs_confirmation,
        "gates": {
            "template_residue": "required" if residue_required else "skipped",
            "content_quality": "required",  # new or changed content is always quality-checked
        },
        "confirmationPrompt": CONFIRMATION_PROMPT if needs_confirmation else "",
        "rationale": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve the AllinCMS run mode and applicable quality gates.")
    parser.add_argument("--site-creation-status", default="",
                        help="created_verified (new site) | existing_site_selected (selected existing site)")
    parser.add_argument("--declared-mode", default="",
                        help=f"Explicit user-declared mode, overrides inference: one of {MODES}")
    parser.add_argument("--demo-signal-count", type=int, default=0,
                        help="How many demo/template fingerprints were detected on a selected existing site")
    parser.add_argument("--output", default="", help="Optional path to write the decision JSON (outside the skill)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    decision = resolve_run_mode(args.site_creation_status, args.declared_mode, args.demo_signal_count)

    if args.output:
        output = ensure_output_outside_skill(Path(args.output).expanduser())
        write_json(output, decision)
        print(f"Wrote run-mode decision: {output}")

    print(f"mode={decision['mode']} needsUserConfirmation={str(decision['needsUserConfirmation']).lower()} "
          f"template_residue={decision['gates']['template_residue']} content_quality={decision['gates']['content_quality']}")
    for reason in decision["rationale"]:
        print(f"  - {reason}")
    if decision["needsUserConfirmation"]:
        print(f"ASK THE USER: {decision['confirmationPrompt']}")
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
