#!/usr/bin/env python3
"""
AllinCMS / LAICMS 纯接口客户端（跨平台：macOS / Windows / Linux，Python stdlib，零第三方依赖）
=================================================================================================
用途：用 HTTP 接口操作 AllinCMS 工作台（站点/页面/文章/产品/分类/标签/媒体/首页设计器），
     不依赖浏览器、AppleScript、Playwright。**读写全部纯接口**：
     写 = server action（next-action header）；读 = RSC 流（RSC: 1 header + ?_rsc query），
     RSC 流中组件 props 即完整业务 JSON（列表数据、分类/标签选项、页面 document 等）。

用法示例（真实签名，2026-08-30 核对）：
    from allincms_api import AllinCMS
    api = AllinCMS(email="...", password="...")  # 推荐（方式一）：纯 API 登录，token 自动提取（ISS-083 双路径实测）
    # 无账号密码时兜底（方式二）：浏览器登录后取 Cookie payload-token → AllinCMS(token=...)；三法详见 ADAPTERS/cms/allincms/docs/TOKEN-AUTH.md
    api.create_category2(site_slug, site_id, name, slug, "posts")      # 分类（cover 显式传 None）
    api.create_category2(site_slug, site_id, name, slug, "products")
    api.upload_media(site_slug, site_id, "photo.jpg", title="...", alt="...")
    api.create_product(site_slug, site_id, {...}); api.publish_product(site_slug, site_id, product_id, {...})
    api.create_post(site_slug, site_id, {...});    api.publish_post(site_slug, site_id, post_id, {...})
    api.save_home(site_slug, theme_id, page_id, site_id, doc, globals, cfg, intent="save"|"publish")
    api.create_theme(site_slug, site_id, name, preset="default"); api.set_theme_active(...); api.apply_theme_routes(...)
零上下文建站总入口见 interface-kit/RUNBOOK-ANYONE.md。
"""
import json, os, re, ssl, sys, urllib.parse, urllib.request, urllib.error


# ---------- 跨平台 token 路径（Windows 兼容） ----------
def _token_file():
    """返回当前平台的 token 文件路径（兼容搜索：/tmp → %TEMP%）"""
    import tempfile
    return os.path.join(tempfile.gettempdir(), "ws-token.txt")

def _read_token():
    """优先 WS_TOKEN 环境变量，回退 token 文件（POSIX 先查 /tmp 再查 %TEMP%；Windows 只查 %TEMP%）。"""
    env = os.environ.get("WS_TOKEN")
    if env: return env
    candidates = [_token_file()]
    for p in candidates:
        if os.path.exists(p):
            try: return open(p).read().strip()
            except Exception: pass
    return ""


ORIGIN   = "https://workspace.laicms.com"
DEPLOY   = "83eddf696484d494d59ae961cb4ded1d61d14b56"
SIGNIN_A = "7f04a5d5c7ef3131a5a72bb56a236ef60fe8498749"   # sign-in action (登录)
CREATE_SITE_A   = "7fedc609bd55e0752bd42dcceb274aaf659064eb1b"
DELETE_SITE_A   = "7f2dd4d43672e0169e117f803d0e1422d880af3bf1"
CREATE_CATEGORY = "7f6253b19d9facfe55ee722dee48a3e834b665b6a6"
CREATE_TAG      = "7fe79a7564f05c77c813a34b52949a44f98704ef8d"
UPLOAD_MEDIA    = "604a958f15a77faf716031fbc33c1f0def20461e3b"
UPDATE_MEDIA    = "7fa3dd69986bb5118a3f57f689958a669350829319"
CREATE_PRODUCT  = "7f63f8f470b449afbd792e0403802ceb33b964f4db"
DELETE_PRODUCT  = "7ff4cdbd4b0334295d3cc7aba4767889363b4bcb45"
UPSERT_PRODUCT  = "7f0d6abcdcec492a7e8587539e8d3f12e96a3d19ca"
CREATE_POST     = "7fdfe82861882e4f6ac3cfbf022bac07e0520fdae1"
DELETE_POST     = "7f0be1853412ed6d5493ae2e4c1988bd78b88ca81e"
UPSERT_POST     = "7f205ad61951b1b4703378159b95d930e7e3f00b42"
COMMIT_DESIGN   = "7ff107025e28118dfb6d8f0da06b3ae64fb0ed74b3"

# ---------- RSC 流解析（读：GET path?_rsc + RSC:1 header） ----------
RECORD_RE = re.compile(r'^((?:[A-Za-z0-9_]+)|(?:o[0-9a-fA-F]+,[A-Za-z0-9_]+)):(.*)$', re.M)

def rsc_records(text):
    """把 RSC 流拆成 (key, decoded_json) 列表；只保留能 json.loads 的记录行。
    RSC 行格式（Next.js App Router 分段流）：
        <key>:<json>           例如 22:["$","$L2b",null,{"data":[...]}]
        o<len>,<id>:<json>     例如 o1000,20:I[...]（带长度前缀的引用行）
    特殊值行（I[...]/$S.../T.../X/C/R）不含业务 JSON，自动跳过。"""
    out = []
    for m in RECORD_RE.finditer(text):
        key, val = m.group(1), m.group(2).rstrip("\r\n")
        if not val:
            continue
        try:
            out.append((key, json.loads(val)))
        except Exception:
            pass
    return out

def _search(obj, needles):
    """深度优先找第一个包含全部 needles 键的 dict。"""
    if isinstance(obj, dict):
        if all(k in obj for k in needles):
            return obj
        for v in obj.values():
            r = _search(v, needles)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _search(v, needles)
            if r is not None:
                return r
    return None


def _walk_dicts(obj):
    """深度优先产出所有 dict 节点（供批量提取记录）。"""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_dicts(v)

def find_json(records, *needles):
    for _, v in records:
        r = _search(v, needles)
        if r is not None:
            return r
    return None

def find_json_all(records, *needles):
    found = []
    for _, v in records:
        r = _search(v, needles)
        if r is not None and r not in found:
            found.append(r)
    return found

class AllinCMS:
    def __init__(self, token=None, email=None, password=None):
        self.token = token
        if email and password:
            self.token = self.login(email, password)
        if not self.token:
            raise ValueError("需要 token（payload-token JWT）或 email+password")
    # ---------- 基础 ----------
    def _req(self, path, action=None, payload=None, method="POST", form=None, timeout=40):
        url = ORIGIN + path
        headers = {"Accept": "text/x-component", "User-Agent": "Mozilla/5.0"}
        if self.token: headers["Cookie"] = "payload-token=" + self.token
        if action:
            headers["next-action"] = action
            headers["x-deployment-id"] = DEPLOY
            headers["Origin"] = ORIGIN
            headers["Referer"] = ORIGIN + path
        data = None
        if form is not None:
            # multipart/form-data（媒体上传）: form[name] = (fname, bytes, ctype)；fname 为 None → 普通字段
            boundary = "----AllinCMSBoundary" + os.urandom(8).hex()
            body = b""
            for name, (fname, content, ctype) in form.items():
                if fname is None:
                    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n" % (boundary, name)).encode() + content + b"\r\n"
                else:
                    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (boundary, name, fname, ctype)).encode() + content + b"\r\n"
            body += ("--%s--\r\n" % boundary).encode()
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
            data = body
        else:
            if payload is not None:
                headers["Content-Type"] = "text/plain;charset=UTF-8"
                data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        self._last_set_cookies = []
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                try:
                    self._last_set_cookies = r.headers.get_all("Set-Cookie") or []
                except Exception:
                    self._last_set_cookies = []
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            try:
                self._last_set_cookies = e.headers.get_all("Set-Cookie") or []
            except Exception:
                self._last_set_cookies = []
            return e.code, e.read().decode("utf-8", "replace")
    def _flight(self, text):
        try:
            for line in text.splitlines():
                if line.startswith("1:{"):
                    return json.loads(line[2:])
        except Exception: pass
        return None
    # ---------- auth ----------
    def login(self, email, password, remember=True):
        """纯 API 账号密码登录（无浏览器）：POST sign-in action → 从响应 Set-Cookie 提取 payload-token（Payload 标准）。
        成功：self.token 生效并返回 token；失败：抛 RuntimeError。
        注意（ISS-083）：成功路径按 Payload 标准实现（Set-Cookie: payload-token=...），但无真实凭据未实测成功分支；
        错误凭据路径已实测（干净报错）。token 仍可走浏览器 Cookie 手动路径（写入平台临时目录的 ws-token.txt）作为兜底。"""
        s, t = self._req("/sign-in", SIGNIN_A, [{"email": email, "password": password, "rememberMe": remember}])
        res = self._flight(t)
        if res and isinstance(res, dict) and "serverError" in res:
            raise RuntimeError("login failed: " + res["serverError"])
        tok = None
        for ck in (self._last_set_cookies or []):
            m = re.search(r"payload-token=([A-Za-z0-9._-]+)", ck)
            if m:
                tok = m.group(1)
                break
        if not tok:
            m2 = re.search(r'"(?:token|payload-token)"\s*:\s*"([A-Za-z0-9._-]+)"', t)
            if m2:
                tok = m2.group(1)
        if tok:
            self.token = tok
            return tok
        raise RuntimeError("login: 响应无 payload-token（Set-Cookie 与响应体均无）——改用浏览器 Cookie 手动路径：登录 workspace.laicms.com → DevTools→Cookies→payload-token → 写入平台临时目录的 ws-token.txt")

    # ---------- RSC 读（纯接口：GET path?_rsc + RSC:1 header，无需浏览器） ----------
    def get_page(self, path, referer=None, timeout=60):
        """GET {path}?_rsc（RSC: 1）→ (status, 原始 RSC 文本)。
        path 例："/sites"、"/{slug}/posts"、"/{slug}/themes/{themeId}/{pageId}/design"。
        服务端对无 _rsc 的请求 307 到 ?_rsc；本方法直接带 ?_rsc 发起。"""
        sep = "&" if "?" in path else "?"
        url = ORIGIN + path.split("?")[0] + sep + "_rsc"
        headers = {"Accept": "text/x-component", "User-Agent": "Mozilla/5.0",
                   "RSC": "1", "Origin": ORIGIN,
                   "Referer": referer or (ORIGIN + path.split("?")[0])}
        if self.token:
            headers["Cookie"] = "payload-token=" + self.token
        for _ in range(4):  # 处理 307/308 重定向
            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.status, r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                loc = (e.headers.get("location") or "").strip()
                if e.code in (307, 308) and loc:
                    url = urllib.parse.urljoin(ORIGIN + path, loc)
                    continue
                return e.code, e.read().decode("utf-8", "replace")
        return None, ""
    def read_sites(self):
        """读站点列表（工作台 /sites 页 RSC）。返回 {status, sites, pagination}。"""
        s, t = self.get_page("/sites")
        rec = rsc_records(t)
        box = find_json(rec, "data", "pagination")
        return {"status": s, "sites": (box or {}).get("data", []),
                "pagination": (box or {}).get("pagination", {})}
    def read_lists(self, site_slug, resource="posts"):
        """读列表页 props：{data, categoryOptions, tagOptions, pagination}。
        resource: 'posts' | 'products'；页面路径 /{slug}/{resource}。"""
        s, t = self.get_page(f"/{site_slug}/{resource}")
        rec = rsc_records(t)
        box = find_json(rec, "data", "pagination", "categoryOptions", "tagOptions") or find_json(rec, "data", "pagination")
        if not box:
            return {"status": s, "data": [], "categoryOptions": [], "tagOptions": [], "pagination": {}}
        return {"status": s, "data": box.get("data", []),
                "categoryOptions": box.get("categoryOptions", []),
                "tagOptions": box.get("tagOptions", []),
                "pagination": box.get("pagination", {})}
    def read_pages(self, site_slug, theme_id):
        """读主题页面列表（/themes/{themeId} 页 RSC）：pages + routes + 主题信息。"""
        s, t = self.get_page(f"/{site_slug}/themes/{theme_id}")
        rec = rsc_records(t)
        box = find_json(rec, "pages", "routes")
        return {"status": s, "themeId": theme_id,
                "pages": (box or {}).get("pages", []),
                "routes": (box or {}).get("routes", [])}
    def read_page_document(self, site_slug, theme_id, page_id):
        """读设计器页面（GET /{slug}/themes/{themeId}/{pageId}/design?_rsc）。
        返回 {status, initialPayload}，initialPayload 含：
          site/theme/page；page 内 document{root,elements} + globals + themeConfig
          （设计器三件套一次读全）；另有 mediaLibraryItems/pageSwitchOptions 等。"""
        s, t = self.get_page(f"/{site_slug}/themes/{theme_id}/{page_id}/design")
        rec = rsc_records(t)
        box = find_json(rec, "initialPayload")
        if box is None:
            return {"status": s, "error": "initialPayload not found in RSC payload"}
        ip = box.get("initialPayload") or box
        return {"status": s, "initialPayload": ip}
    def read_product(self, site_slug, product_id):
        """读产品编辑态（GET /{slug}/products/{id}/update?_rsc）：
        defaultValues = {name, slug, description, order, media, mediaList, content[], categories, tags, specifications}"""
        s, t = self.get_page(f"/{site_slug}/products/{product_id}/update")
        rec = rsc_records(t)
        box = find_json(rec, "defaultValues")
        return {"status": s, "product": (box or {}).get("defaultValues", {})}
    def read_post(self, site_slug, post_id):
        """读文章编辑态（GET /{slug}/posts/{id}/update?_rsc）：
        defaultValues = {title, slug, excerpt, order, coverImage, content[], categories, tags}"""
        s, t = self.get_page(f"/{site_slug}/posts/{post_id}/update")
        rec = rsc_records(t)
        box = find_json(rec, "defaultValues")
        return {"status": s, "post": (box or {}).get("defaultValues", {})}
    def read_media_library(self, site_slug):
        """读媒体库列表（/{slug}/media 页 RSC）：mediaLibraryItems。"""
        s, t = self.get_page(f"/{site_slug}/media")
        rec = rsc_records(t)
        ml = find_json(rec, "mediaLibraryItems")
        return {"status": s, "media": (ml or {}).get("mediaLibraryItems", [])}
    def read_site_info(self, site_slug):
        """读站点信息页（/{slug}/site-info RSC）：site/user/tenant/sites 等。"""
        s, t = self.get_page(f"/{site_slug}/site-info")
        rec = rsc_records(t)
        box = find_json(rec, "site", "user") or find_json(rec, "site")
        return {"status": s, "info": box or {}}
    # ---------- 站点 ----------
    def list_sites(self):
        """读取站点列表（需 RSC 或 delete 动作响应；此处用删除接口的空 id 探测返回）
        返回：站点列表；可靠取得方式见 README：读 /sites 页面 RSC 需浏览器一次性导出。"""
        raise NotImplementedError("站点列表读取需 RSC（见 README read_access）；写操作不依赖。")
    def create_site(self, name, description):
        s, t = self._req("/sites", CREATE_SITE_A, [{"name": name, "description": description}])
        res = self._flight(t)
        return res
    def delete_site(self, site_id):
        """⚠️ 破坏性/不可逆：删除整个站点（含全部内容）。先 read_sites 核对目标 id；必须取得用户明确授权后再调。"""
        s, t = self._req("/sites", DELETE_SITE_A, [{"id": site_id}])
        return self._flight(t)
    # ---------- 分类 / 标签 ----------
    def create_category(self, site_id, name, slug, content_type="posts", description="", order=0, cover=None):
        raise NotImplementedError("create_category 需要 site slug；使用 create_category2(site_slug, ...)")
    def create_category2(self, site_slug, site_id, name, slug, content_type="posts", description="", order=0, cover=None):
        payload = {"siteId": site_id, "contentType": content_type, "name": name, "slug": slug, "order": order}
        if description: payload["description"] = description
        payload["cover"] = cover  # cover 必须显式提供（null 合法；缺省报 validation cover expected object）
        s, t = self._req(f"/{site_slug}/posts?tab=categories", CREATE_CATEGORY, [payload])
        return self._flight(t)
    def create_tag(self, site_slug, site_id, name, slug, description="", content_type="posts"):
        """content_type: 'posts' | 'products'（标签按域隔离，产品标签必须传 'products'）"""
        payload = {"siteId": site_id, "contentType": content_type, "name": name, "slug": slug}
        if description: payload["description"] = description
        tab_path = f"/{site_slug}/{'posts' if content_type == 'posts' else 'products'}?tab=tags"
        s, t = self._req(tab_path, CREATE_TAG, [payload])
        return self._flight(t)
    # ---------- 媒体 ----------
    def upload_media(self, site_slug, site_id, file_path, title=None, alt=None, caption=None):
        with open(file_path, "rb") as fh: content = fh.read()
        import mimetypes
        ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        fname = os.path.basename(file_path)
        form = {"_1_files": (fname, content, ctype), "0": (None, json.dumps([site_id, "$K1"]).encode(), "text/plain")}
        # multipart '0' 字段非文件：特殊处理（正文里放 JSON 字符串）
        s, t = self._req(f"/{site_slug}/media", UPLOAD_MEDIA, form=form)
        urls = sorted(set(re.findall(r'https://assets\.laicms\.com/[a-z0-9/._-]+', t)))
        return {"status": s, "media_urls": urls, "flight": self._flight(t)}
    def update_media(self, site_slug, media_id, site_id, title, alt="", caption=""):
        s, t = self._req(f"/{site_slug}/media", UPDATE_MEDIA, [{"id": media_id, "siteId": site_id, "title": title, "alt": alt, "caption": caption}])
        return self._flight(t)
    # ---------- 产品 ----------
    def create_product(self, site_slug, site_id, product_payload):
        """product_payload 含 name,slug,description,order,media,mediaList,categories:[idStr],tags:[],specifications,productId,mode='update'
        siteId 注入内部副本（action 校验必填），不污染调用方待存证 payload。"""
        payload = dict(product_payload)
        payload.setdefault("siteId", site_id)
        s, t = self._req(f"/{site_slug}/products", CREATE_PRODUCT, [payload])
        return self._flight(t)
    def publish_product(self, site_slug, site_id, product_id, product_payload):
        """发布/更新产品：siteId 自动注入；media update schema 只接受 oss+path；
        categories/tags 必须是 id 字符串数组（readback 对象数组不可原样回传）；content 应为非空 Slate 块。
        见 ISS-097/098。"""
        payload = dict(product_payload)
        payload["siteId"] = site_id
        payload["productId"] = product_id; payload["mode"] = "publish"
        s, t = self._req(f"/{site_slug}/products/{product_id}/update", UPSERT_PRODUCT, [payload])
        return self._flight(t)
    def delete_product(self, site_slug, site_id, product_id):
        """⚠️ 破坏性/不可逆：删除产品记录。先 read_product/read_lists 核对目标；必须取得用户明确授权后再调。"""
        s, t = self._req(f"/{site_slug}/products", DELETE_PRODUCT, [{"id": product_id, "siteId": site_id}])
        return self._flight(t)
    # ---------- 文章 ----------
    def create_post(self, site_slug, site_id, post_payload):
        post_payload.setdefault("siteId", site_id)
        s, t = self._req(f"/{site_slug}/posts", CREATE_POST, [post_payload])
        return self._flight(t)
    def publish_post(self, site_slug, site_id, post_id, post_payload):
        post_payload["postId"] = post_id; post_payload["mode"] = "publish"
        s, t = self._req(f"/{site_slug}/posts/{post_id}/update", UPSERT_POST, [post_payload])
        return self._flight(t)
    def delete_post(self, site_slug, site_id, post_id):
        """⚠️ 破坏性/不可逆：删除文章记录。先 read_post/read_lists 核对目标；必须取得用户明确授权后再调。"""
        s, t = self._req(f"/{site_slug}/posts", DELETE_POST, [{"id": post_id, "siteId": site_id}])
        return self._flight(t)
    # ---------- 主题（2026-08-30 从 workspace 客户端 bundle 提取 42 位 action id）----------
    def read_themes(self, site_slug):
        """GET /{slug}/themes → 主题记录列表（id/name/preset/active/homePageId/homePagePublished/pageCount/designPageId）。
        用于：create_theme 后按 name 取最新 themeId；核对 active 主题。"""
        s, t = self.get_page(f"/{site_slug}/themes")
        out, seen = [], set()
        for k, v in rsc_records(t):
            for rec in _walk_dicts(v):
                if isinstance(rec, dict) and "id" in rec and "name" in rec and "preset" in rec:
                    rid = rec.get("id")
                    if rid and rid not in seen:
                        seen.add(rid); out.append(rec)
        return {"status": s, "themes": out}


    THEME_ACTION_IDS = {
        "createTheme":  "7f3203f59ef09aa7673d34d997f19e374db21d3922",
        "updateTheme":  "7fe46f6230d01d085ac2c269ab2c591d3749927a0b",
        "deleteTheme":  "7fee07b6135885e809eec398cfe6e8af0daa3fd705",
        "setActive":    "7f7f3eda0e33ad8932f12027dd4af21d4ad6643f2f",
        "applyRoutes":  "7f1d7009b7d91ad4e1f140784cef274b8076a1f05f",
        "routeState":   "609c71b72e7ba177588a1e056d6626aaf142173c90",
    }

    def create_theme(self, site_slug, site_id, name, description="", preset="default"):
        """createThemeAction {siteId,name,description,preset:'blank'|'default'}。
        preset='default' 总是生成 7 页模板（/home /about-us /contact-us /posts /posts/{post} /products /products/{product}）。
        注意区分：createSite 时 server 给账号首站建 default 主题、非首站建 blank(0页) 主题——那是 createSite 行为；
        本方法手工建 default 主题即可拿到 7 页。homePageId 可经 set_home_page() 设置（先 setThemeActive 再 set_home_page；顺序不能反，见 set_home_page docstring 与 RUNBOOK §2）。"""
        payload = {"siteId": site_id, "name": name, "description": description, "preset": preset}
        s, t = self._req(f"/{site_slug}/themes", self.THEME_ACTION_IDS["createTheme"], [payload])
        return self._flight(t)

    def set_theme_active(self, site_slug, site_id, theme_id):
        payload = {"siteId": site_id, "id": theme_id}
        s, t = self._req(f"/{site_slug}/themes", self.THEME_ACTION_IDS["setActive"], [payload])
        return self._flight(t)

    def apply_theme_routes(self, site_slug, site_id, theme_id, mappings):
        """mappings: [{'routePath': '/about-us', 'pageId': '<page-id>'}, ...]。
        平台不接受 path '/'（server 报 Route "/" does not exist），根路径只能走 homePageId。"""
        payload = {"id": theme_id, "siteId": site_id, "mappings": mappings}
        s, t = self._req(f"/{site_slug}/themes", self.THEME_ACTION_IDS["applyRoutes"], [payload])
        return self._flight(t)

    def update_theme(self, site_slug, site_id, theme_id, name=None, description=None, cover=None):
        """updateThemeAction schema 仅 {id,siteId,name,description,cover}（zod 会剥离 homePageId 等额外字段）。"""
        payload = {"id": theme_id, "siteId": site_id}
        if name is not None: payload["name"] = name
        if description is not None: payload["description"] = description
        if cover is not None: payload["cover"] = cover
        s, t = self._req(f"/{site_slug}/themes", self.THEME_ACTION_IDS["updateTheme"], [payload])
        return self._flight(t)

    def delete_theme(self, site_slug, site_id, theme_id):
        """⚠️ 破坏性/不可逆：删除主题（其下 7 页设计随之删除）。先 read_themes 核对非 active 再删（删 active 站点全坏）；
        必须取得用户明确授权；产品/文章/媒体为站点级不受影响。"""
        payload = {"siteId": site_id, "id": theme_id}
        s, t = self._req(f"/{site_slug}/themes", self.THEME_ACTION_IDS["deleteTheme"], [payload])
        return self._flight(t)

    # ---------- 页面管理（2026-08-30 从主题概览页 chunk 提取；路径必须是 /{slug}/themes/{themeId}）----------
    PAGE_ACTION_IDS = {
        "createPage":    "7fc39d53972334169c628abed43f7b2d158845f0f2",
        "updatePage":    "7f75d7522d0cf2660d1be50c8d2b0da26e3c0dcd92",
        "deletePage":    "7f423eaf832c83717fe3ee4bbeb3603a843058deea",
        "duplicatePage": "7fae37e87c404869862e3f28fdb88e684e1d2b17ae",
        "setHomePage":   "7f94c780f5f262f8263c08958aa5fb1d1b546f068a",
        "setPageEnabled":"7f35aa21ed412796f83b87a818f776ad2b42044366",
    }

    def set_home_page(self, site_slug, site_id, theme_id, page_id):
        """setHomePageAction {id:pageId, siteId, themeId}——**根路径 / 的唯一天花板开关**。
        必须 POST 到 /{slug}/themes/{themeId}（主题概览页路径），/{slug}/themes 会 200 静默无效果。
        效果：theme.homePageId=pageId + homePagePublished=true + page.isHome=true → 根路径 / 开始渲染该页。
        注意：setThemeActive 会清掉 homePageId，激活主题后要重跑本方法。"""
        payload = [{"id": page_id, "siteId": site_id, "themeId": theme_id}]
        s, t = self._req(f"/{site_slug}/themes/{theme_id}", self.PAGE_ACTION_IDS["setHomePage"], payload)
        return self._flight(t)

    def set_page_enabled(self, site_slug, site_id, theme_id, page_id, enabled):
        payload = [{"id": page_id, "siteId": site_id, "themeId": theme_id, "enabled": enabled}]
        s, t = self._req(f"/{site_slug}/themes/{theme_id}", self.PAGE_ACTION_IDS["setPageEnabled"], payload)
        return self._flight(t)

    def update_page(self, site_slug, site_id, theme_id, page_id, name=None, path=None, query=None, description=None):
        """updatePageAction {id,siteId,themeId,name,path,query,description}——页面记录级字段（含 SEO description）。
        注意（ISS-073 实测）：①静态页 description 可改；动态路由页（/posts/{post}、/products/{product}）description
        会被服务端回退为路由模板值（平台限制）。②页面 publish（commit）可能把 description 重置回模板——description
        更新要在最后一次页面发布之后做；公网 meta 是否刷新以 curl <meta name=description> 为准。"""
        payload = {"id": page_id, "siteId": site_id, "themeId": theme_id}
        if name is not None: payload["name"] = name
        if path is not None: payload["path"] = path
        if query is not None: payload["query"] = query
        if description is not None: payload["description"] = description
        s, t = self._req(f"/{site_slug}/themes/{theme_id}", self.PAGE_ACTION_IDS["updatePage"], [payload])
        return self._flight(t)

    # ---------- 分类/标签管理（2026-08-30 从 posts/products tab chunk 35taj5359am8z 提取）----------
    TAXONOMY_ACTION_IDS = {
        "updateCategory": "7f65d4f36cd601c6bd6fc5ba0348927b58fc4f4c00",
        "deleteCategory": "7fce75b59e7bd261011ad752380c86ad09dd32403b",
        "updateTag":      "7f682f8304deb5f278ee2a65b3f8a4b601eb62cbb0",
        "deleteTag":      "7fbc466fa72b6a1d5d448a3809a88169638208927a",
        "reorderCategories": "7ff678e47cee5a8c6167b251e4acd0c015e3951a31",
        "toggleCategoryVisibility": "7f7889d5c636feb58ec546a085eb12bd58f8b7a1cc",
    }

    def delete_category(self, site_slug, site_id, category_id, content_type="posts"):
        """deleteCategoryAction {id, siteId, contentType}。URL 带 ?tab=categories（与 create 一致）。
        ⚠️ 不可逆：删除分类记录（内容引用会被摘掉）。先 read_lists 核对引用为 0 或符合预期再删；须用户授权。"""
        payload = [{"id": category_id, "siteId": site_id, "contentType": content_type}]
        s, t = self._req(f"/{site_slug}/{'posts' if content_type == 'posts' else 'products'}?tab=categories",
                         self.TAXONOMY_ACTION_IDS["deleteCategory"], payload)
        return self._flight(t)

    def delete_tag(self, site_slug, site_id, tag_id, content_type="posts"):
        """deleteTagAction {id, siteId, contentType}。URL 带 ?tab=tags。
        ⚠️ 不可逆：删除标签记录（内容引用会被摘掉）。先 read_lists 核对引用为 0 或符合预期再删；须用户授权。"""
        payload = [{"id": tag_id, "siteId": site_id, "contentType": content_type}]
        s, t = self._req(f"/{site_slug}/{'posts' if content_type == 'posts' else 'products'}?tab=tags",
                         self.TAXONOMY_ACTION_IDS["deleteTag"], payload)
        return self._flight(t)

    # ---------- 首页设计器 ----------
    def save_home(self, site_slug, theme_id, page_id, site_id, document, globals_doc, theme_config, intent="save"):
        payload = {"siteId": site_id, "themeId": theme_id, "pageId": page_id, "intent": intent,
                   "pageDocument": document, "globals": globals_doc, "themeConfig": theme_config}
        s, t = self._req(f"/{site_slug}/themes/{theme_id}/{page_id}/design", COMMIT_DESIGN, [payload])
        return self._flight(t)

def site_slug(site_id):
    raise NotImplementedError("callers must pass site_slug explicitly")

def _cli():
    """跨平台命令行入口（Windows: python allincms_api.py ...；示例见 README.md）。"""
    args = sys.argv[1:]
    if len(args) < 2 or args[1] in ("help", "-h", "--help"):
        print(__doc__)
        print("用法:")
        print("  python allincms_api.py <token> read-sites")
        print("  python allincms_api.py <token> read-posts <site-slug>")
        print("  python allincms_api.py <token> read-products <site-slug>")
        print("  python allincms_api.py <token> read-pages <site-slug> <themeId>")
        print("  python allincms_api.py <token> read-doc <site-slug> <themeId> <pageId>")
        print("  python allincms_api.py <token> read-product <site-slug> <productId>")
        print("  python allincms_api.py <token> read-post <site-slug> <postId>")
        print("  python allincms_api.py <token> read-media <site-slug>")
        print("  python allincms_api.py <token> read-info <site-slug>")
        print("  示例详见 README.md；token 为工作台登录后的 payload-token JWT。")
        return
    token, cmd = args[0], args[1]
    api = AllinCMS(token=token)
    out = None
    if cmd == "read-sites":
        out = api.read_sites()
    elif cmd == "read-posts":
        out = api.read_lists(args[2], "posts")
    elif cmd == "read-products":
        out = api.read_lists(args[2], "products")
    elif cmd == "read-pages":
        out = api.read_pages(args[2], args[3])
    elif cmd == "read-doc":
        out = api.read_page_document(args[2], args[3], args[4])
    elif cmd == "read-product":
        out = api.read_product(args[2], args[3])
    elif cmd == "read-post":
        out = api.read_post(args[2], args[3])
    elif cmd == "read-media":
        out = api.read_media_library(args[2])
    elif cmd == "read-info":
        out = api.read_site_info(args[2])
    else:
        print("未知命令:", cmd); return
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:20000])

if __name__ == "__main__":
    _cli()
