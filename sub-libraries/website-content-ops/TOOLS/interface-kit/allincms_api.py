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
    create_taxonomy_safe(api, site_slug, site_id, "category"|"tag", name, slug, "posts"|"products")  # 对账+transaction 竞态重试（ISS-123）
    api.upload_media_with_meta(site_slug, site_id, "photo.jpg", title, alt)   # 两段式：上传→媒体库对账→update_media 回写（ISS-122）
    cap = api.refresh_product_capability(site_slug, site_id, task_root, client_id, task_id)  # 每批产品 mutation 前重建（30 分钟过期，ISS-125）
    api.upload_media(site_slug, site_id, "photo.jpg", title="...", alt="...")
    api.mutate_reviewed_product(site_slug, site_id, final_payload, review_json, capability_context, target_id=None_or_exact_id)
    api.mutate_reviewed_post(site_slug, site_id, final_payload, review_json, capability_context, target_id=exact_id)  # 仅 exact-ID update；article.create canonical 于 full-source JS Controller，Python fail-closed（P0-3.1）
    # 裸 create_*/publish_* 为 fail-closed 兼容壳；低层 _*transport 仅内部调用（ISS-102）
    api.save_home(site_slug, theme_id, page_id, site_id, doc, globals, cfg, intent="save"|"publish")
    api.create_theme(site_slug, site_id, name, preset="default"); api.set_theme_active(...); api.apply_theme_routes(...)
零上下文建站总入口见 interface-kit/RUNBOOK-ANYONE.md。
"""
import hashlib, json, os, re, ssl, sys, time, urllib.parse, urllib.request, urllib.error


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
    def _req(self, path, action=None, payload=None, method="POST", form=None, timeout=40, raw_data=None):
        url = ORIGIN + path
        headers = {"Accept": "text/x-component", "User-Agent": "Mozilla/5.0"}
        if self.token: headers["Cookie"] = "payload-token=" + self.token
        if action:
            headers["next-action"] = action
            headers["x-deployment-id"] = DEPLOY
            headers["Origin"] = ORIGIN
            headers["Referer"] = ORIGIN + path
        data = None
        if raw_data is not None:
            if payload is not None or form is not None:
                raise ValueError("raw_data cannot be combined with payload/form")
            headers["Content-Type"] = "text/plain;charset=UTF-8"
            data = raw_data
        elif form is not None:
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
        """读主题页面列表（/themes/{themeId} 页 RSC）：pages + routes + 主题信息。
        pages 行状态键（ISS-108 实测）：enabled(bool)/isHome/_status；routes 行 status=='bound' 判已绑路由。"""
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
    def upload_media_with_meta(self, site_slug, site_id, file_path, title, alt, caption=""):
        """上传+回写 SEO 元数据一步完成（两段式封装，ISS-122）：
        upload_media → read_media_library 按 name 匹配最新项 → update_media 回写 title/alt/caption
        → 返回 {id, url, path, title, alt}。
        ⚠️ upload_media 返回的 media_urls 是**历史累积全量**（每次含所有历史 URL），勿当本次结果
        （ISS-019/109）；本方法以 read_media_library 的记录为唯一真源（键为 {status, media}，
        行在 media 里）。upload_media 的 title/alt/caption 位置参数本身不生效（multipart 只传
        文件+siteId），所以上传后必须 update_media 回写——即"上传=两段式"。
        同名多记录取 createdAt/updatedAt 最新一条；找不到匹配记录时抛 RuntimeError
        （串行快传可能出现记录错位/缺失，按 ISS-109 逐张对账后再重试）。"""
        fname = os.path.basename(file_path)
        stem = os.path.splitext(fname)[0]
        self.upload_media(site_slug, site_id, file_path)   # 第一段：传文件（title/alt 经 update 回写）
        lib = self.read_media_library(site_slug)           # 第二段：媒体库对账（真源）
        exact = [r for r in (lib.get("media") or []) if isinstance(r, dict) and r.get("name") == fname]
        loose = [r for r in (lib.get("media") or []) if isinstance(r, dict) and r.get("name") == stem and r not in exact]
        rows = exact or loose   # 精确文件名优先；stem 仅在无精确匹配时兜底（防 photo.png 顶掉 photo.jpg）
        if not rows:
            raise RuntimeError(
                f"upload_media_with_meta: read_media_library 未发现 name={fname!r} 的记录——"
                "media_urls 是历史累积全量不可当本次结果；若疑似串扰/缺失按 ISS-109 逐张对账后重试")
        def _ts(row):
            # 解析为绝对时刻再比较（字典序会误判 +08:00 与 Z 形式），无法解析的行排最后
            from datetime import datetime
            for key in ("createdAt", "updatedAt", "created", "updated"):
                value = row.get(key)
                if not (isinstance(value, str) and value):
                    continue
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    continue
            return datetime.min.replace(tzinfo=datetime.timezone.utc)
        row = max(rows, key=_ts)   # 同名取解析后最新一条
        media_id = row.get("id")
        if not media_id:
            raise RuntimeError(f"upload_media_with_meta: 匹配记录缺 id 字段：{ {k: row.get(k) for k in ('name', 'url', 'path')} }")
        self.update_media(site_slug, media_id, site_id, title, alt, caption)
        return {"id": media_id, "url": row.get("url"), "path": row.get("path"),
                "title": title, "alt": alt}
    def _normalize_content_readback(self, record, object_type):
        import content_review_gate as _review
        allowed = _review.BUSINESS_KEYS[object_type]
        out = {key: record.get(key) for key in allowed if key in record}
        for key in ("categories", "tags"):
            out[key] = [str(x.get("id") or x.get("value")) if isinstance(x, dict) else str(x)
                        for x in (out.get(key) or [])]
        if out.get("order") is None: out["order"] = 0
        if object_type == "product" and out.get("mediaList") is None: out["mediaList"] = []
        if out.get("tags") is None: out["tags"] = []
        return out
    def _authoritative_content_readback(self, site_slug, target_id, business_payload, object_type):
        resource = "products" if object_type == "product" else "posts"
        import content_review_gate as _review
        evidence = {"target_id": target_id, "resource": resource}
        try:
            status, raw = self.get_page(f"/{site_slug}/{resource}/{target_id}/update")
            evidence["detail_http_status"] = status
            evidence["detail_raw_digest"] = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
            records = rsc_records(raw)
            box = find_json(records, "defaultValues")
            if not isinstance(box, dict) or not isinstance(box.get("defaultValues"), dict):
                raise ValueError("defaultValues not found in authoritative detail readback")
            normalized = self._normalize_content_readback(box["defaultValues"], object_type)
            listing = self.read_lists(site_slug, resource)
            evidence["list_http_status"] = listing.get("status")
            rows = listing.get("data", [])
            if not isinstance(rows, list):
                raise ValueError("authoritative list readback data is not a list")
            exact_rows = [row for row in rows if isinstance(row, dict) and row.get("id") == target_id]
            list_status = (exact_rows[0].get("status") or exact_rows[0].get("_status")) if len(exact_rows) == 1 else None
            exact_match = _review.canonical_bytes(normalized) == _review.canonical_bytes(business_payload)
            normalized_digest = _review.payload_digest(normalized)
        except Exception as exc:
            exact_match = False
            normalized_digest = None
            exact_rows = []
            list_status = None
            evidence["readback_error"] = f"{type(exc).__name__}: {exc}"
        evidence.update({"normalized_business_digest": normalized_digest, "business_exact_match": exact_match,
                         "list_exact_id_count": len(exact_rows), "list_status": list_status})
        evidence["readback_evidence_digest"] = _review.payload_digest(evidence)
        return (evidence.get("detail_http_status") == 200 and evidence.get("list_http_status") == 200
                and exact_match and len(exact_rows) == 1 and list_status == "published"), evidence

    @staticmethod
    def _safe_route_segment(value, label):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
            raise ValueError(f"{label} must be a non-empty safe route segment")
        return value

    @staticmethod
    def _content_transport_confirmed(result, request_evidence, *, require_id=False):
        status = request_evidence.get("response_status") if isinstance(request_evidence, dict) else None
        if not isinstance(result, dict):
            return False
        data = result.get("data")
        if not isinstance(status, int) or not 200 <= status < 300 or not isinstance(data, dict):
            return False
        if require_id:
            target_id = data.get("id")
            return isinstance(target_id, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", target_id))
        return data.get("status") == "published"
    # ---------- 产品（受支持内容 mutation 只允许 reviewed + fresh capability 入口） ----------
    def _send_content_transport(self, path, action, envelope):
        """Freeze one HTTP body, digest it, then send the exact same bytes.
        Article create is refused here too：该 transport 被产品 create/update 与文章 update
        共用，CREATE_POST 动作本身 canonical-controller-only（P0-3.1），请求前 fail-closed。"""
        if action == CREATE_POST:
            raise RuntimeError("ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED")
        import content_review_gate as _review
        body = json.dumps([envelope], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        pre = _review.request_evidence(path, action, body)
        try:
            status, text = self._req(path, action, raw_data=body)
        except Exception as exc:
            evidence = dict(pre)
            evidence.update({"response_status": None, "transport_error": f"{type(exc).__name__}: {exc}",
                             "request_may_have_succeeded": True})
            evidence["request_evidence_digest"] = _review.payload_digest(evidence)
            return None, evidence
        evidence = _review.request_evidence(path, action, body, status=status, response_text=text)
        if evidence["request_body_digest"] != pre["request_body_digest"]:
            raise RuntimeError("REQUEST_BODY_DIGEST_DRIFT")
        return self._flight(text), evidence
    def _create_product_transport(self, site_slug, site_id, product_payload):
        import content_review_gate as _review
        payload = _review.project_wire_payload(product_payload, object_type="product", site_id=site_id,
                                               target_id=None, wire_phase="create_draft")
        return self._send_content_transport(f"/{site_slug}/products", CREATE_PRODUCT, payload)
    def _publish_product_transport(self, site_slug, site_id, product_id, product_payload):
        import content_review_gate as _review
        payload = _review.project_wire_payload(product_payload, object_type="product", site_id=site_id,
                                               target_id=product_id, wire_phase="publish_update")
        return self._send_content_transport(f"/{site_slug}/products/{product_id}/update", UPSERT_PRODUCT, payload)
    def create_product(self, *args, **kwargs):
        raise RuntimeError("CONTENT_REVIEW_CONTEXT_REQUIRED: use mutate_reviewed_product")
    def publish_product(self, *args, **kwargs):
        raise RuntimeError("CONTENT_REVIEW_CONTEXT_REQUIRED: use mutate_reviewed_product")
    def mutate_reviewed_product(self, site_slug, site_id, business_payload, review_record_path,
                                capability_context, target_id=None):
        """受支持产品 create/update 入口；合作式流程门，不是对恶意 token 持有者的安全沙箱。"""
        import content_review_gate as _review
        self._safe_route_segment(site_slug, "site_slug")
        if target_id is not None:
            self._safe_route_segment(target_id, "target_id")
        operation = "update" if target_id else "create"
        required_ops = ({"allincms.product.update", "allincms.product.publish"} if target_id else
                        {"allincms.product.create", "allincms.product.publish"})
        rc, ctx = _review.verify_payload_record(
            business_payload, review_record_path, expected_object_type="product",
            expected_operation=operation, expected_site_key=site_slug, expected_site_id=site_id,
            expected_target_id=target_id)
        if rc: raise RuntimeError("CONTENT_REVIEW_REQUIRED_OR_STALE")
        cap_rc, cap_problems = _review.verify_live_capability(
            capability_context, deployment_id=DEPLOY, site_key=site_slug, site_id=site_id,
            required_operations=required_ops, expected_runtime_scope_root=ctx["runtime_scope_root"],
            expected_action_ids={"allincms.product.create": CREATE_PRODUCT,
                                 "allincms.product.update": UPSERT_PRODUCT,
                                 "allincms.product.publish": UPSERT_PRODUCT},
            expected_client_id=ctx["client_id"], expected_task_id=ctx["task_id"])
        if cap_rc: raise RuntimeError("FRESH_LIVE_CAPABILITY_REQUIRED: " + "; ".join(cap_problems))
        evidence = {"review_context": ctx, "capability_context": capability_context,
                    "wire_projection_version": _review.PROJECTION_VERSION, "automatic_retry": False}
        if not target_id:
            created, create_request = self._create_product_transport(site_slug, site_id, business_payload)
            evidence["create_request"] = create_request
            created_data = created.get("data") if isinstance(created, dict) else None
            new_id = created_data.get("id") if isinstance(created_data, dict) else None
            if not self._content_transport_confirmed(created, create_request, require_id=True):
                return {"result": created, "evidence": evidence, "request_may_have_succeeded": True,
                        "reconcile_required": True, "reconcile": {"resource":"products", "site_key":site_slug,
                        "natural_key":{"slug":business_payload.get("slug")}, "before_after_unique_id_delta":True}}
            evidence["target_id"] = new_id
            published, publish_request = self._publish_product_transport(site_slug, site_id, new_id, business_payload)
            evidence["publish_request"] = publish_request
            if not self._content_transport_confirmed(published, publish_request):
                return {"result": published, "evidence": evidence, "request_may_have_succeeded": True,
                        "reconcile_required": True, "reconcile": {"resource":"products", "site_key":site_slug,
                        "target_id":new_id, "expected_slug":business_payload.get("slug"), "readback_required":True}}
            readback_ok, readback_evidence = self._authoritative_content_readback(
                site_slug, new_id, business_payload, "product")
            evidence["authoritative_readback"] = readback_evidence
            if not readback_ok:
                return {"result": published, "evidence": evidence, "reconcile_required": True,
                        "reconcile": {"resource":"products", "site_key":site_slug, "target_id":new_id,
                                      "expected_slug":business_payload.get("slug"), "readback_required":True}}
            return {"result": published, "evidence": evidence, "reconcile_required": False}
        published, request_evidence = self._publish_product_transport(site_slug, site_id, target_id, business_payload)
        evidence.update({"target_id": target_id, "publish_request": request_evidence})
        if not self._content_transport_confirmed(published, request_evidence):
            return {"result": published, "evidence": evidence, "request_may_have_succeeded": True,
                    "reconcile_required": True, "reconcile": {"resource":"products", "site_key":site_slug,
                    "target_id":target_id, "expected_slug":business_payload.get("slug"), "readback_required":True}}
        readback_ok, readback_evidence = self._authoritative_content_readback(
            site_slug, target_id, business_payload, "product")
        evidence["authoritative_readback"] = readback_evidence
        if not readback_ok:
            return {"result": published, "evidence": evidence, "reconcile_required": True,
                    "reconcile": {"resource":"products", "site_key":site_slug, "target_id":target_id,
                                  "expected_slug":business_payload.get("slug"), "readback_required":True}}
        return {"result": published, "evidence": evidence, "reconcile_required": False}
    def delete_product(self, site_slug, site_id, product_id):
        """⚠️ 破坏性/不可逆：删除产品记录。先 read_product/read_lists 核对目标；必须取得用户明确授权后再调。"""
        s, t = self._req(f"/{site_slug}/products", DELETE_PRODUCT, [{"id": product_id, "siteId": site_id}])
        return self._flight(t)
    def refresh_product_capability(self, site_slug, site_id, task_root, client_id, task_id,
                                   ttl_minutes=25, operation="create"):
        """重建产品 mutation 的 live capability context（ISS-117/125，两机实战沉淀）。
        **每批 mutation 前必须重建**——capability 30 分钟过期（gate 上限 30，默认 ttl 25），
        禁止复用上一批的 context；批量中途超窗即整批刷新。

        内部动作：① GET /{slug}/products 列表页 RSC 观察当前部署是否仍携带 CREATE_PRODUCT
        action id（operation='create' 时必须命中；未命中≈新站无 createProductAction，按 ISS-105
        改走 update/upsert 路径）；② 取首个产品 GET /{slug}/products/{id}/update 编辑页观察
        UPSERT_PRODUCT action id。然后把 evidence 写入 <task_root>/70_evidence/ 并返回
        verify_live_capability 可直接接受的 capability context dict（含 evidence_digest）。

        operation='create' → operations={allincms.product.create, allincms.product.publish}；
        operation='update' → {allincms.product.update, allincms.product.publish}（两者都必须
        与 mutate_reviewed_product 的 required_operations 精确一致，不能合并成三操作集）。
        站内无产品时返回 None 并提示（UPSERT_PRODUCT 只在产品编辑页可观察——需先有产品）。
        task_root 即 runtime_scope_root：review record 与 evidence 都必须落在其下。"""
        import content_review_gate as _review
        import datetime as _dt
        if operation not in ("create", "update"):
            raise ValueError("operation must be 'create' or 'update'")
        if not 1 <= ttl_minutes <= 30:
            raise ValueError("ttl_minutes must be within (0, 30] —— capability 窗口上限 30 分钟")
        ops = sorted({"create": ("allincms.product.create", "allincms.product.publish"),
                      "update": ("allincms.product.update", "allincms.product.publish")}[operation])
        actions = {"allincms.product.create": CREATE_PRODUCT,
                   "allincms.product.update": UPSERT_PRODUCT,
                   "allincms.product.publish": UPSERT_PRODUCT}
        s1, t1 = self.get_page(f"/{site_slug}/products")
        if s1 != 200:
            raise RuntimeError(f"refresh_product_capability: /{site_slug}/products HTTP {s1}（token/站点状态先排查）")
        has_create_action = CREATE_PRODUCT in t1
        if operation == "create" and not has_create_action:
            raise RuntimeError(
                "refresh_product_capability: 当前列表页 RSC 未观察到 createProductAction —— "
                "该站可能只有 upsertProductAction（ISS-105），改走 update/upsert：先 create 得 draft id，"
                "再 mutate_reviewed_product(target_id=draft_id) + operation='update'")
        listing = self.read_lists(site_slug, "products")
        rows = [r for r in (listing.get("data") or []) if isinstance(r, dict) and r.get("id")]
        if not rows:
            print("refresh_product_capability: 站内无产品——UPSERT_PRODUCT 只能在产品编辑页观察，"
                  "需先有至少 1 个产品（draft 也行）再刷新 capability；返回 None。")
            return None
        s2, t2 = self.get_page(f"/{site_slug}/products/{rows[0]['id']}/update")
        if s2 != 200 or UPSERT_PRODUCT not in t2:
            raise RuntimeError(
                f"refresh_product_capability: 首个产品编辑页未观察到 upsertProductAction"
                f"（HTTP {s2}）——部署可能已更新，重扫 action id（scan/scan-actions.py）后再试")
        root = os.path.abspath(task_root)
        ev_dir = os.path.join(root, "70_evidence")
        os.makedirs(ev_dir, exist_ok=True)
        now = _dt.datetime.now(_dt.timezone.utc)
        stamp = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        ev_name = f"capability-product-{operation}-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
        ev_path = os.path.join(ev_dir, ev_name)
        evidence = {"deployment_id": DEPLOY, "site_key": site_slug, "site_id": site_id,
                    "verified_operations": ops,
                    "action_ids": {op: actions[op] for op in ops},
                    "observed_at": stamp}
        with open(ev_path, "w", encoding="utf-8") as fh:
            json.dump(evidence, fh, indent=1, sort_keys=True)
            fh.write("\n")
        with open(ev_path, "rb") as fh:
            digest = "sha256:" + hashlib.sha256(fh.read()).hexdigest()
        context = {"status": "live_verified_current_deployment", "deployment_id": DEPLOY,
                   "site_key": site_slug, "site_id": site_id, "operations": ops,
                   "evidence_ref": f"70_evidence/{ev_name}", "observed_at": stamp,
                   "expires_at": (now + _dt.timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                   "runtime_scope_root": root, "evidence_digest": digest,
                   "client_id": client_id, "task_id": task_id}
        rc, problems = _review.verify_live_capability(
            context, deployment_id=DEPLOY, site_key=site_slug, site_id=site_id,
            required_operations=set(ops), expected_action_ids={op: actions[op] for op in ops},
            expected_runtime_scope_root=root, expected_client_id=client_id, expected_task_id=task_id)
        if rc:
            raise RuntimeError("CAPABILITY_SELF_CHECK_FAILED: " + "; ".join(problems))
        print(f"refresh_product_capability: {operation} ops={ops} evidence={ev_path} "
              f"expires_at={context['expires_at']}（每批 mutation 前重建，30 分钟过期）")
        return context
    # ---------- 文章（article.create canonical 于 full-source JS Controller；Python 仅 exact-ID update，P0-3.1） ----------
    def _create_post_transport(self, site_slug, site_id, post_payload):
        """Python 不得发出文章 create 请求（第二执行面禁令，P0-3.1）。
        canonical 执行面 = ADAPTERS/cms/allincms 的 content-run-controller.mjs +
        content-plan-host-driver.mjs 'article:create' handler + article-operations.mjs
        #createPostDraft，宿主注入三个真实 provider（articleBeforePostIdsProvider /
        articleCreateReadbackProvider / articleEditorReopenProvider）；缺 provider 时本次
        create BLOCK，不得降级到 Python。不做 payload projection、不发网络请求。"""
        raise RuntimeError("ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED")
    def _publish_post_transport(self, site_slug, site_id, post_id, post_payload):
        import content_review_gate as _review
        payload = _review.project_wire_payload(post_payload, object_type="article", site_id=site_id,
                                               target_id=post_id, wire_phase="publish_update")
        return self._send_content_transport(f"/{site_slug}/posts/{post_id}/update", UPSERT_POST, payload)
    def create_post(self, *args, **kwargs):
        raise RuntimeError("CONTENT_REVIEW_CONTEXT_REQUIRED: use mutate_reviewed_post")
    def publish_post(self, *args, **kwargs):
        raise RuntimeError("CONTENT_REVIEW_CONTEXT_REQUIRED: use mutate_reviewed_post")
    def mutate_reviewed_post(self, site_slug, site_id, business_payload, review_record_path,
                             capability_context, target_id=None):
        """受支持文章 exact-ID update 入口。target_id=None（create）不再由 Python 执行：
        article.create canonical 于 full-source JS Controller（content-run-controller.mjs +
        content-plan-host-driver.mjs 'article:create' handler + article-operations.mjs
        #createPostDraft + 三个真实 provider）；Python 是第二执行面禁令对象，任何
        review/capability/network/readback 之前先 fail-closed（P0-3.1）。"""
        if target_id is None:
            raise RuntimeError("ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED")
        import content_review_gate as _review
        self._safe_route_segment(site_slug, "site_slug")
        self._safe_route_segment(target_id, "target_id")
        operation = "update"
        required_ops = {"allincms.article.update", "allincms.article.publish"}
        rc, ctx = _review.verify_payload_record(
            business_payload, review_record_path, expected_object_type="article",
            expected_operation=operation, expected_site_key=site_slug, expected_site_id=site_id,
            expected_target_id=target_id)
        if rc: raise RuntimeError("CONTENT_REVIEW_REQUIRED_OR_STALE")
        cap_rc, cap_problems = _review.verify_live_capability(
            capability_context, deployment_id=DEPLOY, site_key=site_slug, site_id=site_id,
            required_operations=required_ops,
            expected_action_ids={"allincms.article.update": UPSERT_POST,
                                 "allincms.article.publish": UPSERT_POST},
            expected_runtime_scope_root=ctx["runtime_scope_root"], expected_client_id=ctx["client_id"],
            expected_task_id=ctx["task_id"])
        if cap_rc: raise RuntimeError("FRESH_LIVE_CAPABILITY_REQUIRED: " + "; ".join(cap_problems))
        evidence = {"review_context": ctx, "capability_context": capability_context,
                    "wire_projection_version": _review.PROJECTION_VERSION, "automatic_retry": False,
                    "target_id": target_id}
        published, request_evidence = self._publish_post_transport(site_slug, site_id, target_id, business_payload)
        evidence["publish_request"] = request_evidence
        if not self._content_transport_confirmed(published, request_evidence):
            return {"result": published, "evidence": evidence, "request_may_have_succeeded": True,
                    "reconcile_required": True, "reconcile": {"resource":"posts", "site_key":site_slug,
                    "target_id":target_id, "expected_slug":business_payload.get("slug"), "readback_required":True}}
        readback_ok, readback_evidence = self._authoritative_content_readback(
            site_slug, target_id, business_payload, "article")
        evidence["authoritative_readback"] = readback_evidence
        if not readback_ok:
            return {"result": published, "evidence": evidence, "reconcile_required": True,
                    "reconcile": {"resource":"posts", "site_key":site_slug, "target_id":target_id,
                                  "expected_slug":business_payload.get("slug"), "readback_required":True}}
        return {"result": published, "evidence": evidence, "reconcile_required": False}
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
        """页面启用/停用（setPageEnabledAction）：enabled=False 时路由仍 bound 但公开 404（ISS-108 诊断树第 4 步）。"""
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


def create_taxonomy_safe(api, slug, site_id, kind, name, cslug, content_type="posts", retries=3):
    """taxonomy（分类/标签）安全创建：写前/重试前 read_lists 对账 + transaction 竞态退避重试
    （模块级便捷函数，ISS-024/086/123 两机实战沉淀）。

    已知症状：create_category2/create_tag 偶发 "Given transaction number X does not match
    active transaction number Y"（Mongo 事务错位，间歇性），且 create 响应常为 {} 无 id，
    易误判成败。本函数固化实测配方：
      每次尝试前 read_lists 对账（label=分类名/value=id，确认远端确实不存在，已存在直接复用）
      → create → readback 按 label 找 id（ISS-086：id 只能从回读拿）
      → 未确认且错误文本含 "transaction number" → sleep 5→8→13s 重试（retries=3 默认）
      → 其他错误/重试耗尽 → RuntimeError（带最后一次响应，供人工判断）。

    kind: 'category'（create_category2，cover 显式 None）| 'tag'（create_tag）；
    content_type: 'posts' | 'products'（产品域 taxonomy 必须传 'products'，标签按域隔离）。
    对账按 label（=name）匹配——categoryOptions/tagOptions 行不含 slug（ISS-118），
    所以 name 撞名即视为已存在；slug 查重在调用方 brief 阶段做（check-slug-namespace.py）。
    返回 {kind, name, slug, content_type, id, already_exists, attempts, flight}。"""
    if kind not in ("category", "tag"):
        raise ValueError("kind must be 'category' or 'tag'")
    if content_type not in ("posts", "products"):
        raise ValueError("content_type must be 'posts' or 'products'")
    resource = "posts" if content_type == "posts" else "products"
    options_key = "categoryOptions" if kind == "category" else "tagOptions"
    delays = (5, 8, 13)

    def _find_existing():
        listing = api.read_lists(slug, resource)
        for row in (listing.get(options_key) or []):
            if isinstance(row, dict) and row.get("label") == name and row.get("value"):
                return row.get("value")
        return None

    last_flight, last_error = None, ""
    for attempt in range(int(retries) + 1):
        existing = _find_existing()
        if existing:
            return {"kind": kind, "name": name, "slug": cslug, "content_type": content_type,
                    "id": existing, "already_exists": True, "attempts": attempt, "flight": last_flight}
        try:
            if kind == "category":
                last_flight = api.create_category2(slug, site_id, name, cslug,
                                                   content_type=content_type, cover=None)
            else:
                last_flight = api.create_tag(slug, site_id, name, cslug, content_type=content_type)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_flight = None
        found = _find_existing()
        if found:
            return {"kind": kind, "name": name, "slug": cslug, "content_type": content_type,
                    "id": found, "already_exists": False, "attempts": attempt + 1, "flight": last_flight}
        err_text = last_error or (json.dumps(last_flight, ensure_ascii=False, default=str)
                                  if last_flight is not None else "")
        retryable = "transaction number" in err_text.lower()
        if attempt < int(retries) and retryable:
            delay = delays[min(attempt, len(delays) - 1)]
            print(f"create_taxonomy_safe[{kind}/{name}]: transaction mismatch（attempt {attempt + 1}），"
                  f"sleep {delay}s 后对账重试：{err_text[:160]}")
            time.sleep(delay)
            continue
        if attempt < int(retries) and not retryable and not err_text:
            # 无错误文本也未回读到（列表刷新滞后）：短等一次再进下一轮（对账会再查）
            time.sleep(2)
            continue
        raise RuntimeError(
            f"create_taxonomy_safe[{kind}/{name}] 未能确认创建（attempts={attempt + 1}）："
            f"last_flight={json.dumps(last_flight, ensure_ascii=False, default=str) if last_flight is not None else None} "
            f"error={last_error or '(无错误文本，回读未命中 label)'}——若疑似竞态可手动重跑本函数；"
            "勿盲目重复 create（先 read_lists 对账）")
    raise RuntimeError("create_taxonomy_safe: unreachable retries exhaustion")

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
