#!/usr/bin/env python3
"""AllinCMS 建站流水线工具（零依赖跨平台）：brief 校验 / payload 生成 / 模板词自检 / readback 深度比对。
配合 ONBOARDING-PIPELINE.md 使用：AI 从「公司/产品介绍文档」提炼 brief.json → validate → generate →
用 allincms_api.py 执行 → check 自检 → 验收。

用法：
  python site_pipeline.py validate brief.json          # 校验 brief 字段完整性
  python site_pipeline.py generate brief.json outdir/  # 生成 payload 集（分类/标签/产品/文章/页面素材）
  python site_pipeline.py check file-or-dir...         # 模板词自检（过滤 <style>/<script>）
  python site_pipeline.py diff a.json b.json           # 深度 diff（readback 对抗比对）
  python site_pipeline.py gate <slug> --config <cfg>           # 上线门（数量/200/空态/模板词）
  python site_pipeline.py contact <slug> --config <cfg> --real "..."  # demo 联系方式门
  python site_pipeline.py audit <slug> --config <cfg> --out r.json  # 13 项对抗审计（必带每站 --config）
"""
import json, os, re, sys


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


# 会话级 scratch 根（ISS-079）：SCRATCH_DIR 环境变量优先，否则 /tmp；产物按功能分目录，便于按目录清理
SCRATCH = os.environ.get("SCRATCH_DIR") or "/tmp"

TEMPLATE_WORDS = [
    "northstar", "buildnbuzz", "555-0142", "mission street", "san francisco",
    "instagram.com", "linkedin.com", "weekender", "premium steel", "family size",
    "maya", "new season arrivals", "carry, home", "packing pouch", "desk tray",
    # 2026-08-30 对抗补充：default 主题页面/全局块的 demo 默认值（曾漏网）
    "more from the journal", "keep readers moving", "commerce editorial system",
    "materials and care", "built to age into the routine", "waxed canvas",
    "brushed steel", "recycled fiber", "shop new arrivals",
    "tell us what you are choosing for", "ask about sizing, materials",
    "field notes", "read the material guide",
    # 2026-08-30 二轮补充：products 页新闻块等再漏网 demo 默认值
    "guides for choosing", "buying guides, material", "material notes",
    "stories and guides", "explore by topic", "featured in our journal",
    "popular pieces", "routines, repairs", "products to pair", "follow us",
    "product care and ideas", "twitter.com", "x.com",
]

# ---------- 模板词自检 ----------
def strip_style_script(text):
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text)
    return t

def check_template_words(texts, ignore_style=True):
    """texts: [raw_text,...]；返回 [(word, count)]；忽略 CSS/JS 里的 canvas/img 类词。"""
    hits = {}
    for raw in texts:
        t = strip_style_script(raw) if ignore_style else raw
        low = t.lower()
        for w in TEMPLATE_WORDS:
            n = low.count(w)
            if n: hits[w] = hits.get(w, 0) + n
    return hits

# ---------- deep diff（readback 对抗） ----------
def deep_diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append(f"+ {path}/{k}={json.dumps(b[k], ensure_ascii=False)[:60]}")
            elif k not in b: out.append(f"- {path}/{k}={json.dumps(a[k], ensure_ascii=False)[:60]}")
            else: out += deep_diff(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append(f"len {path}: {len(a)}->{len(b)}")
        for i, (x, y) in enumerate(zip(a, b)): out += deep_diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"~ {path}: {str(a)[:45]} -> {str(b)[:45]}")
    return out

# ---------- brief schema 校验 ----------
BRIEF_SCHEMA = {
    "site": {"name": str, "slug": str, "description": str},
    "brand": {"title": str, "tagline": str, "cta": str},
    "contact": {"email": str, "phone": str, "address": str, "hours": str, "whatsapp": str},
    "categories_posts": list, "categories_products": list,
    "tags": list, "products": list, "posts": list,
    "story": dict, "nav": list,
}
OPTIONAL = {"contact": ["whatsapp"], "story": ["intro", "story", "stats", "values", "team"]}

def validate_brief(brief, strict=False):
    """返回问题列表 []；strict=False 时仅检查 site/brand/contact/products/posts 必填。"""
    problems = []
    for key in ("site", "brand", "contact", "products", "posts"):
        if key not in brief:
            problems.append(f"missing: {key}")
            continue
    site = brief.get("site", {})
    for f in ("name", "slug", "description"):
        if not site.get(f): problems.append(f"site.{f} missing")
    for f in ("title", "tagline", "cta"):
        if not brief.get("brand", {}).get(f): problems.append(f"brand.{f} missing")
    for f in ("email", "phone", "address", "hours"):
        if not brief.get("contact", {}).get(f): problems.append(f"contact.{f} missing")
    for i, p in enumerate(brief.get("products", [])):
        for f in ("name", "slug", "description", "specifications", "category"):
            if not p.get(f): problems.append(f"products[{i}].{f} missing")
        if not isinstance(p.get("specifications"), list):
            problems.append(f"products[{i}].specifications must be list of {{key,value}}")
    for i, p in enumerate(brief.get("posts", [])):
        for f in ("title", "slug", "excerpt", "content"):
            if not p.get(f): problems.append(f"posts[{i}].{f} missing")
        if not isinstance(p.get("content"), list):
            problems.append(f"posts[{i}].content must be Slate block list")
    # 数量门（美观基线，见 templates/CONTENT-MINIMUM.md）
    n_prod = len(brief.get("products", []))
    n_post = len(brief.get("posts", []))
    if n_prod < 3: problems.append(f"products 数量不足: {n_prod} < 3（美观基线；要求用户补充，或用 demo 占位并标注）")
    if n_post < 4: problems.append(f"posts 数量不足: {n_post} < 4（美观基线；要求用户补充，或用 demo 占位并标注）")
    return problems

# ---------- payload 生成 ----------
def build_payloads(brief, media_urls=None):
    """brief -> {categories, tags, products, posts, home_blocks_hints}（供 allincms_api 执行/组装）。
    media_urls: {ref_name: url} 或 callable(name)；brief 中 media 用 ref 名。"""
    resolve = (lambda name: (media_urls or {}).get(name)) if isinstance(media_urls, dict) else media_urls
    out = {
        "categories_posts": [{"name": c["name"], "slug": c["slug"], "contentType": "posts"} for c in brief.get("categories_posts", [])],
        "categories_products": [{"name": c["name"], "slug": c["slug"], "contentType": "products"} for c in brief.get("categories_products", [])],
        "tags": [{"name": t["name"], "slug": t["slug"]} for t in brief.get("tags", [])],
        "products": [p for p in brief.get("products", [])],
        "posts": [p for p in brief.get("posts", [])],
        "story": brief.get("story", {}),
        "nav": brief.get("nav", []),
        "contact": brief.get("contact", {}),
        "brand": brief.get("brand", {}),
    }
    return out

def gate(site_slug, base_url=None, html_dir=None, config=None):
    """上线一键门：数量(read_lists)/公网 200/空态/模板词。任一不过 -> 退出码 1 并输出清单。
    用法：python3 site_pipeline.py gate <site-slug> [--config site-config.json] [--base https://dom] [--html-dir /path/to/html]
    说明：数量基线与页面清单走每站 --config（ISS-063）。"""
    import urllib.request, ssl
    cfg = load_audit_config(config)
    base_url = base_url or f"https://{site_slug}.web.allincms.com"
    problems = []
    passed = True
    # ① 数量门（需要 token：从 allincms_api 读；无 token 则跳过仅提示）
    try:
        import sys as _s
        here = os.path.dirname(os.path.abspath(__file__))
        _s.path.insert(0, here)
        from allincms_api import AllinCMS
        token = _read_token()
        if token:
            api = AllinCMS(token=token)
            n_prod = len(api.read_lists(site_slug, "products")["data"])
            n_post = len(api.read_lists(site_slug, "posts")["data"])
            if n_prod < cfg["count"]["products"]: problems.append(f"产品数量 {n_prod} < {cfg['count']['products']}"); passed = False
            if n_post < cfg["count"]["posts"]: problems.append(f"文章数量 {n_post} < {cfg['count']['posts']}"); passed = False
            print(f"[num] products={n_prod} posts={n_post} (基线 {cfg['count']['products']}/{cfg['count']['posts']})")
        else:
            print("[num] 无 token -> 跳过数量门（人工核对）")
    except Exception as e:
        print(f"[num] skip ({type(e).__name__})")
    # ② 公网 200 + 空态 + 模板词
    pages = cfg["pages"]
    if html_dir and os.path.isdir(html_dir):
        htmls = [os.path.join(html_dir, f) for f in sorted(os.listdir(html_dir)) if f.endswith(".html")]
    else:
        htmls = []
        for p in pages:
            fn = os.path.join(html_dir or os.path.join(SCRATCH, "gate-html"), (p.replace("/", "_") or "home") + ".html")
            os.makedirs(os.path.dirname(fn) or ".", exist_ok=True)
            try:
                with urllib.request.urlopen(urllib.request.Request(base_url + "/" + p, headers={"User-Agent": "Mozilla/5.0"}), timeout=25,
                                             context=ssl.create_default_context()) as r:
                    open(fn, "w", encoding="utf-8").write(r.read().decode("utf-8", "replace"))
                    if r.status != 200: problems.append(f"http {r.status} {p}")
            except urllib.error.HTTPError as e:
                problems.append(f"http {e.code} {p}"); passed = False
            except Exception as e:
                problems.append(f"fetch {p}: {type(e).__name__}"); passed = False
            htmls.append(fn)
    empty = 0; tmpl = 0
    for h in htmls:
        try: t = open(h, encoding="utf-8", errors="replace").read()
        except Exception: continue
        body = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", t)
        body = re.sub(r"<[^>]+>", " ", body)
        for w in ("No content is available yet", "No items yet", "No results", "coming soon"):
            if w.lower() in body.lower(): empty += 1; problems.append(f"空态 {h}: {w}")
        low = body.lower()
        for w in TEMPLATE_WORDS:
            if w in low: tmpl += 1; problems.append(f"模板词 {h}: {w}")
    if empty or tmpl: passed = False
    print(f"[http/empty/template] pages={len(htmls)} empty={empty} template={tmpl}")
    if problems:
        print("GATE FAIL:"); [print("   -", p) for p in problems]
    else:
        print("GATE PASS: 数量/200/空态/模板词 全部通过")
    return 0 if passed else 1

DEMO_CONTACTS = {
    "8613800000000": "demo WhatsApp",
    "138 0000 0000": "demo phone",
    "hello@demo-demo.com": "demo email",
    "hello@example-demo.com": "demo email",
    "wa.me/8613": "demo whatsapp",
    "buildnbuzz.com": "template email",
    "555-0142": "template phone",
    "mission street": "template address",
    # 2026-08-30 对抗补充：default 主题 social-floating-button 默认值（曾漏网）
    "wa.me/+44-7911-123456": "template whatsapp (fake)",
}

# ---------- audit 站点基线（对抗升级：单站硬编码 → 每站可配）----------
# 默认基线 = Demo（向后兼容）；新站建站时必须提供 --config 覆盖，
# 否则 count/faq-answer/cta/unit 会按 Demo 事实误判（ISS-063）。
AUDIT_CONFIG_DEFAULTS = {
    "pages": ["", "about-us", "contact-us", "posts", "products", "sitemap.xml"],
    "count": {"products": 3, "posts": 4},
    "fallback_article": "how-to-choose-a-touring-kayak-for-two",
    "primary_article": None,            # 指定 faq/cta/h2 检查用主文章 slug；缺省用 arts[0]
    "faq_answers": ["not by itself", "add both paddlers", "typically heavier", "this guide is for calm lakes"],
    "cta": {"product_link": "/products/demo-product-slug",
            "consult_source": "source=tandem-kayak-guide"},
    "units": ["5.2m", "68cm", "220kg", "80kg", "65kg", "25kg", "170kg", "4.2m"],
    "template_words_extra": [],
    "demo_contacts_extra": {},
    "required_h2": 3,
}


def _deep_merge(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def load_audit_config(path):
    cfg = json.loads(json.dumps(AUDIT_CONFIG_DEFAULTS))
    if path and os.path.isfile(path):
        _deep_merge(cfg, json.load(open(path, encoding="utf-8")))
    return cfg


def contact_gate(base_url, check_values="", config=None):
    """联系方式门：抓公网页面，扫描 demo/占位联系方式；--real 传用户提供的真实值清单（| 分隔）。
    任一 demo 值命中且不在 real 清单 -> FAIL（要求用户提供真实值）。
    页面清单走每站 --config（ISS-063）。"""
    import urllib.request, ssl
    cfg = load_audit_config(config)
    real = (check_values or "").lower()
    found = {}
    os.makedirs(os.path.join(SCRATCH, "contact-scan"), exist_ok=True)
    pages = cfg["pages"]
    for p in pages:
        fn = os.path.join(SCRATCH, "contact-scan", (p.replace("/", "_") or "home") + ".html")
        try:
            with urllib.request.urlopen(urllib.request.Request(base_url + "/" + p, headers={"User-Agent": "Mozilla/5.0"}),
                                        timeout=25, context=ssl.create_default_context()) as r:
                open(fn, "w", encoding="utf-8").write(r.read().decode("utf-8", "replace"))
        except Exception:
            continue
        t = open(fn, encoding="utf-8", errors="replace").read().lower()
        for demo, label in DEMO_CONTACTS.items():
            if demo in t and demo not in real:
                found.setdefault(demo, []).append(os.path.basename(fn))
    if found:
        print("[contact] FAIL 未替换 demo 联系方式（需用户提供真实值）:")
        for d, fs in found.items(): print("    -", d, "in", fs[:3])
        return 1
    print("[contact] PASS: 公网无未替换 demo 联系方式" + ("；--real 已核对" if real else "；提示：建议 --real 传用户真实值以确认来源"))
    return 0


def audit(site_slug, base_url=None, html_dir=None, out=None, config=None):
    """综合对抗审计（优于 gate）：内容/前端/SEO 一体检查，输出 PASS/FAIL 与机器可读 JSON。
    覆盖：数量、200、空态、模板词、demo 联系方式、FAQ 答案 SSR、真实 CTA、
          单位统一、绝对化词、Markdown 残留(](与#)、正文 h2 语义、根路径 home 回归、表单渲染。
    用法：python3 site_pipeline.py audit <slug> [--config site-audit-config.json] [--out audit-report.json]
    说明：--config 必带每站基线（ISS-063）；缺省= Demo 基线，新站会误判。"""
    import urllib.request, ssl
    cfg = load_audit_config(config)
    base_url = base_url or f"https://{site_slug}.web.allincms.com"
    report = {"slug": site_slug, "base": base_url, "checks": {}, "problems": []}
    def add(kind, ok, detail):
        report["checks"][kind] = {"ok": (ok if ok is None else bool(ok)), "detail": detail}
        if ok is False:
            report["problems"].append(f"{kind}: {detail}")
    def fetch(url):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25,
                                         context=ssl.create_default_context()) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception as e:
            return 0, type(e).__name__
    pages = cfg["pages"]
    htmls = {}
    if html_dir and os.path.isdir(html_dir):
        for f in sorted(os.listdir(html_dir)):
            if f.endswith(".html"): htmls[f] = open(os.path.join(html_dir, f), encoding="utf-8", errors="replace").read()
    else:
        os.makedirs(os.path.join(SCRATCH, "audit-html"), exist_ok=True)
        for p in pages:
            st, txt = fetch(base_url + "/" + p)
            fn = (p.replace("/", "_") or "home") + ".html"
            if txt: open(os.path.join(SCRATCH, "audit-html", fn), "w", encoding="utf-8").write(txt)
            if st != 200: add("http", False, f"{p} -> {st}")
            htmls[fn] = txt
    add("http", not any(k.startswith("http") for k in report["checks"]), "抓取页面")
    # 数量门
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from allincms_api import AllinCMS
        token = _read_token()
        if token:
            api = AllinCMS(token=token)
            np_, npo = len(api.read_lists(site_slug, "products")["data"]), len(api.read_lists(site_slug, "posts")["data"])
            add("count", np_ >= cfg["count"]["products"] and npo >= cfg["count"]["posts"],
                f"products={np_} posts={npo} (基线 {cfg['count']['products']}/{cfg['count']['posts']})")
        else:
            add("count", None, "无 token 跳过（人工核对）")
    except Exception as e:
        add("count", None, f"skip {type(e).__name__}")
    # 根路径首页（ISS-070）：/ 必须渲染真实首页而非 Allin CMS Runtime 错误壳
    home_raw = htmls.get("home.html", "")
    add("root-home", "__next_error__" not in home_raw and len(home_raw) > 10000,
        "根路径 / 渲染真实首页" if "__next_error__" not in home_raw else "根路径 / 是错误壳（用 set_home_page 修复，见 RUNBOOK §2）")
    # 表单渲染（ISS-076）：contact-us 必须有真实 <form>（formSlug 空=整个表单不渲染）；home 至少 1 个表单（内联或全局弹窗）
    contact_raw = htmls.get("contact-us.html", "")
    has_form = "<form" in contact_raw and ('type="submit"' in contact_raw or "Send message" in contact_raw)
    add("form-render", has_form,
        "contact-us 渲染真实表单" if has_form else "contact-us 无 <form>（表单块 formSlug 空=断裂，绑 readback initialForms 里的真实 slug，ISS-076）")
    # 全页正文聚合（去 script/style/meta/标签）。meta 排除理由：模板词扫描只对可见文本判定；
    # 页面 description 是主题生成元数据——静态页可经 api.update_page(description=) 改（ISS-073），
    # 动态路由页回退模板值（平台限制）；审计以可见文本为准，meta 单独人工核对。
    bodies = {fn: re.sub(r"<[^>]+>", " ",
                         re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<meta[\s\S]*?>|<link[\s\S]*?>", " ", t)).lower()
              for fn, t in htmls.items()}
    # 空态 / 模板词
    empty_hits = [(fn, w) for fn, b in bodies.items() for w in
                  ("no content is available yet", "no items yet", "no results", "coming soon") if w in b]
    add("empty", not empty_hits, f"{empty_hits[:3]}")
    tmpl_words = TEMPLATE_WORDS + list(cfg.get("template_words_extra", []))
    tmpl_hits = [(fn, w) for fn, b in bodies.items() for w in tmpl_words if w in b]
    add("template", not tmpl_hits, f"{tmpl_hits[:3]}")
    # demo 联系方式
    demo_contacts = dict(DEMO_CONTACTS); demo_contacts.update(cfg.get("demo_contacts_extra", {}))
    demo_hits = [(fn, w) for fn, b in bodies.items() for w in demo_contacts if w in b]
    add("demo-contact", not demo_hits, f"{demo_hits[:3]}")
    # 全站文章内容检查（拉取全部文章 slug；不再锁单篇）
    arts = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from allincms_api import AllinCMS
        token = _read_token()
        if token:
            api = AllinCMS(token=token)
            for x in api.read_lists(site_slug, "posts")["data"]:
                arts.append(x["slug"])
    except Exception:
        arts = [cfg["fallback_article"]]
    if not arts: arts = [cfg["fallback_article"]]
    for a in arts:
        fn = f"posts_{a}.html"
        if fn not in htmls:
            st, txt = fetch(base_url + "/posts/" + a)
            htmls[fn] = txt
            if txt: open(os.path.join(SCRATCH, "audit-html", fn), "w", encoding="utf-8").write(txt)
    # FAQ/内容答案 SSR（问题标志+答案首句都在初始 HTML；兼容 SSR 转义 \"/&#x27; 形式）
    primary = cfg.get("primary_article") or (arts[0] if arts else cfg["fallback_article"])
    raw_art = htmls.get("posts_" + primary + ".html", "")
    raw_art_norm = raw_art.replace("&#x27;", "'").replace("\\\"", '"').replace("\\n", " ").lower()
    faq_answers = tuple(cfg["faq_answers"])
    add("faq-answer", all(a.lower() in raw_art_norm for a in faq_answers),
        f"answers_present={sum(1 for a in faq_answers if a.lower() in raw_art_norm)}/{len(faq_answers)}")
    # 真实 CTA（产品深链 + 带 source 的咨询链）
    prod_cta = cfg["cta"]["product_link"] in raw_art
    consult_cta = cfg["cta"]["consult_source"] in raw_art
    add("cta", prod_cta and consult_cta, f"product={prod_cta} consult={consult_cta}")
    # 单位统一（无空格残留，站点可配；units 为空则跳过）
    if cfg["units"]:
        unit_bad = re.findall(r"\b(" + "|".join(re.escape(u) for u in cfg["units"]) + r")\b", raw_art_norm)
        add("unit", not unit_bad, f"bad_units={sorted(set(unit_bad))[:5]}")
    else:
        add("unit", None, "站点未配置单位基线，跳过")
    # 绝对化词（排除合法边界短语 always confirm/follow、问句 always ...?、RSC 转义重复）
    abs_hits = []
    for m in re.finditer(r"(always|usually|is faster|is more stable|comfortable default|best|never fails)", raw_art_norm):
        ctx = raw_art_norm[max(0, m.start()-60):m.end()+60]
        # 排除合法边界语境：场景限定(calm water/lakes/rivers/many/around/tends/can/most)、
        # 指令(confirm/follow)、问句(?/!)、RSC 转义(channel/value)、软词(usually/for many/for calm)
        if any(w in ctx for w in ("confirm", "follow", "more stable?", "?", "!", "channel", "value",
                                  "calm water", "calm lake", "gentle river", "many first", "around 68",
                                  "can feel", "tends", "may", "for calm", "usually")):
            continue
        abs_hits.append(m.group(1))
    add("absolute", not abs_hits, f"abs_words={sorted(set(abs_hits))[:5]}")
    # Markdown 残留（限定正文可见文本：去标签后；排除 CSS 类名与转义序列）
    visible = re.sub(r"<[^>]+>", " ", raw_art).replace("\\\"", "").replace("**", "")
    md_hits = re.findall(r"\]\(|(?:^|[\s(])\*\*|\*\*(?:[\s).,])|^#\s", visible)
    add("markdown", not md_hits, f"md_hits={sorted(set(md_hits))[:5]}")
    # 正文语义标题（原生 h2）
    import re as _re
    n_h2 = raw_art.count('data-slate-type="h2"')
    add("h2-semantic", n_h2 >= cfg["required_h2"], f"正文 h2 数 = {n_h2}（原生 h2 语义标题；≥{cfg['required_h2']} 达标）")

    # 汇总
    fail = list(report["problems"])
    report["verdict"] = "PASS" if not fail else "FAIL"
    report["counts"] = {"checks": len(report["checks"]), "problems": len(report["problems"])}
    if out:
        d = os.path.dirname(os.path.abspath(out))
        os.makedirs(d, exist_ok=True)
        json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[audit] 报告已写 {out}")
    for k, v in report["checks"].items():
        mark = "✅" if v["ok"] else ("⏭️" if v["ok"] is None else "❌")
        print(f"  {mark} {k}: {v['detail']}")
    print(f"VERDICT: {report['verdict']} | checks={report['counts']['checks']} problems={report['counts']['problems']}")
    return 0 if report["verdict"] == "PASS" else 1


def _cli():
    args = sys.argv[1:]
    if not args or args[0] in ("help", "-h", "--help"):
        print(__doc__); return
    cmd = args[0]
    if cmd == "validate":
        brief = json.load(open(args[1], encoding="utf-8"))
        probs = validate_brief(brief)
        if probs:
            print("INVALID:"); [print(" ", p) for p in probs]; sys.exit(1)
        print("VALID: brief 完整（site/brand/contact/products/posts 就绪）")
    elif cmd == "generate":
        brief = json.load(open(args[1], encoding="utf-8"))
        outdir = args[2] if len(args) > 2 else "generated"
        os.makedirs(outdir, exist_ok=True)
        payloads = build_payloads(brief)
        for k, v in payloads.items():
            json.dump(v, open(os.path.join(outdir, f"{k}.json"), "w"), ensure_ascii=False, indent=1)
        print("generated:", sorted(os.listdir(outdir)))
        print("下一步：见 ONBOARDING-PIPELINE.md 2.5-2.8（用 allincms_api.py 执行）")
    elif cmd == "check":
        hits = {}
        for f in args[1:]:
            if os.path.isdir(f):
                for root, _, files in os.walk(f):
                    for fn in files:
                        if fn.endswith((".html", ".txt", ".json", ".md")):
                            h = check_template_words([open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()])
                            for w, n in h.items(): hits[f"{os.path.join(root, fn)}:{w}"] = n
            else:
                h = check_template_words([open(f, encoding="utf-8", errors="replace").read()])
                for w, n in h.items(): hits[f"{f}:{w}"] = n
        if hits:
            print("TEMPLATE-WORD HITS:"); [print(f"  {k}: {v}") for k, v in hits.items()]; sys.exit(1)
        print("CLEAN: 无模板词残留")
    elif cmd == "contact":
        base_url = f"https://{args[1]}.web.allincms.com"
        for a in args[2:]:
            if a.startswith("--base="): base_url = a.split("=", 1)[1]
        real = ""
        config = None
        for i, a in enumerate(args):
            if a == "--real" and i + 1 < len(args): real = args[i + 1]
            if a == "--config" and i + 1 < len(args): config = args[i + 1]
        sys.exit(contact_gate(base_url, check_values=real, config=config))
    elif cmd == "audit":
        base_url = f"https://{args[1]}.web.allincms.com"
        for a in args[2:]:
            if a.startswith("--base="): base_url = a.split("=", 1)[1]
        out = None
        config = None
        for i, a in enumerate(args):
            if a == "--out" and i + 1 < len(args): out = args[i + 1]
            if a == "--config" and i + 1 < len(args): config = args[i + 1]
        sys.exit(audit(args[1], base_url=base_url, out=out, config=config))
    elif cmd == "gate":
        import argparse
        args_extra = [a for a in args[2:] if not a.startswith("--")]
        def _val(flag):
            for i, a in enumerate(args):
                if a.startswith(flag + "="): return a.split("=", 1)[1]
                if a == flag and i + 1 < len(args): return args[i + 1]
            return None
        html_dir = _val("--html-dir")
        base_url = _val("--base")
        config = _val("--config")
        sys.exit(gate(args[1], base_url=base_url, html_dir=html_dir, config=config))
    elif cmd == "diff":
        a, b = json.load(open(args[1], encoding="utf-8")), json.load(open(args[2], encoding="utf-8"))
        d = deep_diff(a, b)
        if d:
            print(f"DIFF ({len(d)}):"); [print("  ", x) for x in d[:30]]; sys.exit(1)
        print("IDENTICAL")
    else:
        print("unknown command:", cmd); print(__doc__)

if __name__ == "__main__":
    _cli()
