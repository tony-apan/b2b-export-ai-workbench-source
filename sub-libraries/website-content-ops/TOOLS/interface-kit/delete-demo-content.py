#!/usr/bin/env python3
"""删除 createTheme(default) 重种的 demo 内容（ISS-071/074，产品+文章+分类+标签全链清理）。
用法：python3 delete-demo-content.py <site-slug> [--dry-run]（--dry-run 只列将删项不执行；执行前须取得用户明确授权）
说明：createTheme(preset='default') 会在站点级重新种入 3 个 demo 产品 + 3 个 demo 文章，
      以及 demo 分类/标签（分类名随 preset 固定，id 每站不同——按名字删）。
      audit 的 count 项（基线=该站实建数）会直接暴露；上线前必跑本脚本。
依赖：同目录 allincms_api.py + 平台临时目录的 ws-token.txt（或 WS_TOKEN 环境变量）。
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from allincms_api import AllinCMS


# ---------- 跨平台 token 路径（Windows 兼容） ----------
def _token_file():
    """返回当前平台的 token 文件路径（兼容搜索：/tmp → %TEMP%）"""
    import tempfile
    return os.path.join(tempfile.gettempdir(), "ws-token.txt")

def _read_token():
    """优先 WS_TOKEN 环境变量，回退 token 文件（POSIX 先查 /tmp 再查 %TEMP%；Windows 只查 %TEMP%）。"""
    env = os.environ.get("WS_TOKEN")
    if env: return env
    candidates = ["tempfile.gettempdir() + "/ws-token.txt", _token_file()] if os.name != "nt" else [_token_file()]
    for p in candidates:
        if os.path.exists(p):
            try: return open(p).read().strip()
            except Exception: pass
    return ""


DEMO_PRODUCT_SLUGS = ["modular-packing-pouch", "stackable-desk-tray-set", "waxed-canvas-weekender"]
DEMO_POST_SLUGS = ["small-entryway-system", "material-care-buying-decision", "choose-a-weekender-bag"]
DEMO_POST_CATEGORY_NAMES = ["Buying Guides", "Material Notes", "Home Routines"]
DEMO_PRODUCT_CATEGORY_NAMES = ["Daily Carry", "Home Goods", "Travel Essentials"]
DEMO_POST_TAG_NAMES = ["Buying Guide", "How To", "Material Focus"]
DEMO_PRODUCT_TAG_NAMES = ["Buying Guide", "Gift Pick", "Material Focus", "New Arrival"]


def find_site_id(api, slug):
    sites = api.read_sites()
    data = sites.get("data") or sites.get("sites") or [] if isinstance(sites, dict) else sites or []
    for s in data:
        if s.get("slug") == slug:
            return s["id"]
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    slug = sys.argv[1]
    token = _read_token()
    if not token:
        print("无 token：请把 payload-token 写平台临时目录 ws-token.txt 或设 WS_TOKEN"); sys.exit(1)
    api = AllinCMS(token=token)
    site_id = find_site_id(api, slug)
    if not site_id:
        print(f"未找到 slug={slug} 的站点"); sys.exit(1)
    deleted = 0

    # ① demo 产品/文章（按 slug）
    dry_run = "--dry-run" in sys.argv
    for kind, slugs, del_fn in [("products", DEMO_PRODUCT_SLUGS, api.delete_product),
                                ("posts", DEMO_POST_SLUGS, api.delete_post)]:
        for x in api.read_lists(slug, kind)["data"]:
            if x.get("slug") in slugs:
                if dry_run:
                    print(f"[dry-run] would delete {kind[:-1]} {x['slug']} (id={x['id']})")
                    continue
                del_fn(slug, site_id, x["id"])
                print(f"deleted {kind[:-1]} {x['slug']}")
                deleted += 1
                time.sleep(1.0)

    # ② demo 分类/标签（按名字；id 每站不同）。TERRA P1 护栏：名字是通用词（"Buying Guide" 等），
    # 先校验这些 taxonomy 的引用集 ⊆ demo slug 集才删——若被非 demo 内容引用则跳过并 WARN（防误删客户真实同名 taxonomy）。
    dry_run = "--dry-run" in sys.argv
    demo_content_slugs = set(DEMO_PRODUCT_SLUGS + DEMO_POST_SLUGS)
    for kind, cat_names, tag_names in [("posts", DEMO_POST_CATEGORY_NAMES, DEMO_POST_TAG_NAMES),
                                        ("products", DEMO_PRODUCT_CATEGORY_NAMES, DEMO_PRODUCT_TAG_NAMES)]:
        d = api.read_lists(slug, kind)
        items = api.read_lists(slug, kind)["data"]
        item_slugs = {x.get("slug") for x in items}
        # 引用集 = 现存内容 slug 是否含非 demo（说明有真实内容在用这些 taxonomy）
        non_demo_items = item_slugs - demo_content_slugs
        for c in d.get("categoryOptions") or []:
            if c.get("label") in cat_names:
                if non_demo_items:
                    print(f"SKIP {kind} category {c['label']}：存在非 demo 内容 {sorted(non_demo_items)[:5]}（人工确认后再删）")
                    continue
                if dry_run:
                    print(f"[dry-run] would delete {kind} category {c['label']} (id={c['value']})")
                    continue
                api.delete_category(slug, site_id, c["value"], kind)
                print(f"deleted {kind} category {c['label']}")
                deleted += 1
                time.sleep(1.0)
        for t in d.get("tagOptions") or []:
            if t.get("label") in tag_names:
                if non_demo_items:
                    print(f"SKIP {kind} tag {t['label']}：存在非 demo 内容 {sorted(non_demo_items)[:5]}（人工确认后再删）")
                    continue
                if dry_run:
                    print(f"[dry-run] would delete {kind} tag {t['label']} (id={t['value']})")
                    continue
                api.delete_tag(slug, site_id, t["value"], kind)
                print(f"deleted {kind} tag {t['label']}")
                deleted += 1
                time.sleep(1.0)

    # ③ 终态复核
    n_p = len(api.read_lists(slug, "products")["data"])
    n_o = len(api.read_lists(slug, "posts")["data"])
    fin_cats = [c["label"] for k in ("posts", "products") for c in (api.read_lists(slug, k).get("categoryOptions") or [])]
    fin_tags = [t["label"] for k in ("posts", "products") for t in (api.read_lists(slug, k).get("tagOptions") or [])]
    demo_left = [n for n in fin_cats + fin_tags if n in (DEMO_POST_CATEGORY_NAMES + DEMO_PRODUCT_CATEGORY_NAMES + DEMO_POST_TAG_NAMES + DEMO_PRODUCT_TAG_NAMES)]
    print(f"DONE: removed {deleted} demo items | products={n_p} posts={n_o}")
    print(f"taxonomy remaining: cats={fin_cats} tags={fin_tags}")
    if demo_left:
        print(f"WARN: demo taxonomy 仍残留 {demo_left}（可能被内容引用，人工处理）")
        sys.exit(1)

if __name__ == "__main__":
    main()
