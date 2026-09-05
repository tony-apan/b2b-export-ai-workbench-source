#!/usr/bin/env python3
"""slug 同 namespace 预检（check-slug-namespace.py，ISS-084/124）—— 建站前/写产品前必跑。

背景：平台 slug 唯一域覆盖产品与 taxonomy——产品 slug 与分类/tag slug 同名时
create 能成功但 publish 报 validation.slug.duplicate（ISS-084）。本脚本在建站前
把三路来源拉平成同一个 namespace 提前检测：
  ① read_lists(<slug>, 'products') 的产品行 slug 列表；
  ② read_lists 'products' 与 'posts' 的 categoryOptions（label+value）；
  ③ 同两路的 tagOptions（label+value）。
taxonomy 行只暴露 label（=分类名）与 value（=id），slug 按 label slugify 推导
（平台建分类/tag 的惯例 slug=slugify(name)；若行带 slug 字段则优先用显式值）。

用法：python3 check-slug-namespace.py <site-slug> [--json]
  --json 输出机器可读结果；冲突清单非空时 exit 1（可接入建站前置 gate）。
依赖：同目录 allincms_api.py（stdlib only）+ WS_TOKEN 或平台临时目录 ws-token.txt。

范围注记：只检产品 slug × taxonomy slug（ISS-084 实测冲突域）；产品 slug 互相重复
一并报告（同样会阻断 publish）；文章 slug 不在本检测域（article 侧独立对账）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from allincms_api import AllinCMS, _read_token


def slugify(text):
    """label → 平台惯例 slug：小写、非字母数字折叠为 -、去首尾 -。

    非 ASCII 折叠局限：CJK（中日韩）整段折叠为 '-'（去首尾后可能为空串）；重音拉丁
    （é/ó/ñ 等）也折叠为 '-' 而非去重音（'cerámica'→'cer-mica'，é≠e）——非英语站
    （西语等）落库前先自行 NFD 去重音再生成 slug，写前实测一次（NEW-SITE-ONEPASS
    非英语站注意①）。"""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(text or "").lower())).strip("-")


def collect(api, site_slug):
    """拉平三路来源 → (product_slugs:[{slug,id,name}], taxonomy:[{slug,name,id,kind,domain}])。"""
    products = api.read_lists(site_slug, "products")
    posts = api.read_lists(site_slug, "posts")
    if products.get("status") != 200 or posts.get("status") != 200:
        raise RuntimeError(f"read_lists 状态异常：products={products.get('status')} posts={posts.get('status')}"
                           "（先核对 token 与 site_slug）")
    product_slugs = []
    for row in products.get("data") or []:
        if isinstance(row, dict) and row.get("slug"):
            product_slugs.append({"slug": str(row["slug"]).lower(), "id": row.get("id"), "name": row.get("name")})
    taxonomy = []
    for domain, listing in (("products", products), ("posts", posts)):
        for kind, key in (("category", "categoryOptions"), ("tag", "tagOptions")):
            for row in listing.get(key) or []:
                if not isinstance(row, dict):
                    continue
                label = row.get("label")
                if not label:
                    continue
                slug = str(row.get("slug") or slugify(label)).lower()
                taxonomy.append({"slug": slug, "name": label, "id": row.get("value"),
                                 "kind": kind, "domain": domain})
    return product_slugs, taxonomy


def find_conflicts(product_slugs, taxonomy):
    """同 namespace 重复检测 → 冲突清单（每条含重复双方与命中 slug）。
    判定规则：冲突必须涉及产品 slug（产品×taxonomy=ISS-084 publish 阻断；产品×产品重复
    同样阻断）。纯 taxonomy×taxonomy 同 slug 不判——demo 种子同名 tag（如 Buying Guide）
    在 posts/products 两域各有一条是合法常态（ISS-115 实测），判了必误报。"""
    by_slug = {}
    for item in product_slugs:
        by_slug.setdefault(item["slug"], []).append({"type": "product", **{k: item[k] for k in ("id", "name")}})
    for item in taxonomy:
        by_slug.setdefault(item["slug"], []).append(
            {"type": f"{item['kind']}({item['domain']})", "id": item["id"], "name": item["name"]})
    conflicts = []
    for slug in sorted(by_slug):
        entries = by_slug[slug]
        if len(entries) > 1 and any(e["type"] == "product" for e in entries):
            conflicts.append({"slug": slug, "entries": entries})
    return conflicts


def main():
    args = sys.argv[1:]
    use_json = "--json" in args
    args = [a for a in args if a != "--json"]
    if len(args) != 1:
        print(__doc__)
        return 2
    site_slug = args[0]
    token = _read_token()
    if not token:
        print("无 token：请 export WS_TOKEN=<payload-token> 或写平台临时目录 ws-token.txt")
        return 1
    api = AllinCMS(token=token)
    try:
        product_slugs, taxonomy = collect(api, site_slug)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    conflicts = find_conflicts(product_slugs, taxonomy)
    if use_json:
        print(json.dumps({"site_slug": site_slug, "products": len(product_slugs),
                          "taxonomy": len(taxonomy), "conflicts": conflicts},
                         ensure_ascii=False, indent=2))
    else:
        print(f"site={site_slug} products={len(product_slugs)} taxonomy={len(taxonomy)} "
              f"（categoryOptions/tagOptions 来自 products+posts 两域，slug=显式值或 slugify(label)）")
        if not conflicts:
            print("NAMESPACE OK：产品 slug 与分类/tag slug 无同 namespace 重复。")
        else:
            print(f"NAMESPACE CONFLICT x{len(conflicts)}（同 namespace 重复 → publish validation.slug.duplicate，ISS-084）：")
            for c in conflicts:
                parties = ", ".join(f"{e['type']}[{e['name']}](id={e['id']})" for e in c["entries"])
                print(f"  - slug='{c['slug']}' 冲突：{parties}")
            print("修复：给产品 slug 加后缀差异化（如 -series）或改 taxonomy slug 后重建。")
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
