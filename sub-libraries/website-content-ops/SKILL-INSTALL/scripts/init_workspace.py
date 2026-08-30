#!/usr/bin/env python3
"""Scaffold a PRIVATE multi-client / multi-site workspace for AllinCMS site builds.

Why this is separate from the skill package: the skill (this repo) is PUBLIC and read-only; the
workspace holds a client's raw materials, contact details, and real site keys — PII that must NEVER
land in the public skill repo. So the workspace lives OUTSIDE the skill, and this scaffolder refuses
to create it inside the skill package.

Layout (Karpathy: raw is append-only, wiki is the distilled evolving layer):
  <workspace>/
    README.md                              index: clients, their sites, live siteKey/URL/status
    clients/<client>/
      brief.md                             client overview
      raw/                                 original materials, append-only (never edited)
      wiki/  company.md brand.md contact.md products/   distilled CLIENT-level knowledge (shared across the client's sites)
      sites/<site>/
        brief.md                           this site's scope/positioning
        source-wiki/                        this site's source wiki (subset of client wiki + site-specific)
        package/                            confirmed content package
        run/                                build run state (resume) — a persistent run folder for this site
        residue-blacklist.json              old-content fingerprints for the residue gate (conversion sites)
        live.md                             launch record: siteKey, URL, date, acceptance

Safety: NEVER overwrites an existing client/site directory (your materials stay put); refuses to
scaffold inside the skill package; slugs are validated kebab-case.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _common import skill_root, now_iso

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

README_HEADER = """# AllinCMS 建站工作区(私有)

> ⚠️ **私有数据,切勿推送到公开的 skill 仓!** 这里放客户原始资料、联系方式、真实站点 key,
> 都是敏感信息。请把本工作区放在**独立的私有仓**或加进 `.gitignore`,绝不能进公开的
> `allincms-bulk-content-upload` skill 仓(那会把客户 PII 泄漏到公网)。

本工作区按「一客户一文件夹、客户下多站各自子文件夹」组织;raw 原始资料只增不改,
wiki 是提炼的客户级知识(跨该客户所有站复用),每个网站的独立数据在 `sites/<site>/`。

## 索引:客户 / 网站 / 线上状态

| 客户 | 网站 | 本地路径 | 线上 siteKey | URL | 状态 |
|---|---|---|---|---|---|
"""

CLIENT_BRIEF = """# {client} · 客户总览

- 公司 / 品牌:(填)
- 目标市场 / 买家:(填)
- 联系方式:见 `wiki/contact.md`(真实联系方式只放这里,不要散到各处)
- 这个客户有几个网站、各自定位:见下方 `sites/`

> 提炼规则:发来的原始资料先原样存进 `raw/`(只增不改),再提炼进 `wiki/`;
> 每条提炼出的知识标注来自哪份 raw(sourceRef),缺的标 gap,绝不编造。
"""

WIKI_FILES = {
    "company.md": "# 公司介绍(客户级 · 所有站的 About 共用)\n\n(从 raw/ 提炼;每条标 sourceRef)\n",
    "brand.md": "# 品牌调性 / 禁用词(客户级)\n\n- 调性:\n- 禁用说法:\n",
    "contact.md": "# 真实联系方式(客户级 · 敏感)\n\n> 只放这一处,产品/文章里引用它,不要各处重录。\n\n- 邮箱:\n- 电话:\n- 地址:\n",
}

SITE_BRIEF = """# {client} / {site} · 本站定位

- 这个站服务哪个细分 / 市场 / 语言:(填)
- 上哪些产品(从客户 wiki 取子集):(填)
- 目标 URL / 关键 SEO 词:(填)
- 建站模式:新建站=from_scratch;改造已有模板站=template_conversion;
  日常更新已有干净站=incremental_update(用 resolve_run_mode.py 定,已有站要问用户)
"""

SITE_LIVE = """# {client} / {site} · 上线记录

- 线上 siteKey:(建站后填)
- 前台 URL:
- 上线日期:
- launch 验收:(过 launch-acceptance + 残留闸后填)
"""


def _write_if_absent(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _resolve_workspace(root: str) -> Path:
    resolved = Path(root).expanduser().resolve()
    sk = skill_root()
    if resolved == sk or sk in resolved.parents or sk == resolved.parent:
        raise SystemExit(f"ERROR: workspace must be OUTSIDE the skill package (got {resolved}); "
                         "keep client data out of the public skill repo")
    return resolved


def _validate_slug(slug: str, kind: str) -> str:
    if not SLUG_RE.match(slug or ""):
        raise SystemExit(f"ERROR: {kind} slug must be lowercase kebab-case (a-z, 0-9, -), got {slug!r}")
    return slug


def _index_append(root: Path, client: str, site: str, local_path: Path) -> None:
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(README_HEADER, encoding="utf-8")
    rel = local_path.relative_to(root)
    row = f"| {client} | {site} | `{rel}` | (建站后填) | | 未开始 |\n"
    text = readme.read_text(encoding="utf-8")
    if f"`{rel}`" in text:  # exact backtick-wrapped path, so a prefix sibling (eu-store vs eu-store-2) isn't dropped
        return
    readme.write_text(text + row, encoding="utf-8")


def cmd_init_workspace(root: str) -> int:
    ws = _resolve_workspace(root)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "clients").mkdir(exist_ok=True)
    created = _write_if_absent(ws / "README.md", README_HEADER)
    print(f"workspace ready at {ws}" + ("" if created else " (README already present, left as is)"))
    print("  reminder: keep this workspace PRIVATE — never push it to the public skill repo.")
    return 0


def cmd_new_client(root: str, client: str) -> int:
    ws = _resolve_workspace(root)
    client = _validate_slug(client, "client")
    cdir = ws / "clients" / client
    if cdir.exists():
        raise SystemExit(f"ERROR: client {client!r} already exists at {cdir} — refusing to overwrite existing materials")
    (cdir / "raw").mkdir(parents=True)
    (cdir / "wiki" / "products").mkdir(parents=True)
    (cdir / "sites").mkdir()
    _write_if_absent(cdir / "brief.md", CLIENT_BRIEF.format(client=client))
    for name, content in WIKI_FILES.items():
        _write_if_absent(cdir / "wiki" / name, content)
    print(f"created client {client} at {cdir}")
    print("  next: drop original materials into raw/ (append-only), distill into wiki/, then add a site.")
    return 0


def cmd_new_site(root: str, client: str, site: str) -> int:
    ws = _resolve_workspace(root)
    client = _validate_slug(client, "client")
    site = _validate_slug(site, "site")
    cdir = ws / "clients" / client
    if not cdir.exists():
        raise SystemExit(f"ERROR: client {client!r} not found — run --action new-client first")
    sdir = cdir / "sites" / site
    if sdir.exists():
        raise SystemExit(f"ERROR: site {site!r} already exists at {sdir} — refusing to overwrite existing materials")
    (sdir / "source-wiki").mkdir(parents=True)
    (sdir / "package").mkdir()
    (sdir / "run").mkdir()
    _write_if_absent(sdir / "brief.md", SITE_BRIEF.format(client=client, site=site))
    _write_if_absent(sdir / "live.md", SITE_LIVE.format(client=client, site=site))
    _write_if_absent(sdir / "residue-blacklist.json",
                     json.dumps({"kind": "allincms_template_residue_blacklist", "generatedAt": now_iso(),
                                 "note": "fill with the OLD site's fingerprints before a template conversion; leave empty for a from-scratch or clean incremental site",
                                 "terms": []}, ensure_ascii=False, indent=2) + "\n")
    _index_append(ws, client, site, sdir)
    print(f"created site {site} for client {client} at {sdir}")
    print(f"  this site's run folder: {sdir / 'run'} (pass it as --output-dir, or set ALLINCMS_RUN_HOME to it)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a private multi-client/multi-site AllinCMS workspace.")
    parser.add_argument("--action", required=True, choices=("init-workspace", "new-client", "new-site"))
    parser.add_argument("--root", required=True, help="Workspace root path (OUTSIDE the skill package, keep private)")
    parser.add_argument("--client", default="", help="Client slug (kebab-case) for new-client / new-site")
    parser.add_argument("--site", default="", help="Site slug (kebab-case) for new-site")
    args = parser.parse_args()

    if args.action == "init-workspace":
        return cmd_init_workspace(args.root)
    if args.action == "new-client":
        if not args.client:
            raise SystemExit("ERROR: --client is required for new-client")
        return cmd_new_client(args.root, args.client)
    if args.action == "new-site":
        if not (args.client and args.site):
            raise SystemExit("ERROR: --client and --site are required for new-site")
        return cmd_new_site(args.root, args.client, args.site)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
