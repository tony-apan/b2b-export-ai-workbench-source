---
title: "NEW-SITE-ONEPASS.md —— 给一份客户资料，AI 一条龙建完一个站"
type: "runbook"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-09-05"
sources: ["RUNBOOK-ANYONE.md（10 步总流程/实测事实表/平台回落表/执行路径决策树）", "ONBOARDING-PIPELINE.md（细节 SOP）", "templates/client-input-checklist.md", "templates/site-content-checklist.md", "templates/CONTENT-MINIMUM.md", "templates/brief-schema.json", "templates/site-audit-config.template.json", "templates/post-payload-example.json", "templates/product-payload-example.json", "templates/delivery-manifest.md", "writing/WRITING-INDEX.md", "MODULES.md（37 块注册表）", "Example 全流程实战 2026-08-29/30", "2026-09-04 双机实战（macOS+Windows 10 field build）"]
related: ["RUNBOOK-ANYONE.md", "ONBOARDING-PIPELINE.md", "templates/new-site-customization-checklist.md", "MODULES.md", "writing/WRITING-INDEX.md"]
description: AllinCMS 建站工具包文档（NEW-SITE-ONEPASS.md）
visibility: "public"
redaction_status: "safe-to-publish"
---

# NEW-SITE-ONEPASS：给一份客户资料，AI 一条龙建完一个站

> **定位**：本手册是 [RUNBOOK-ANYONE.md](RUNBOOK-ANYONE.md) 的**「新站执行版」**。RUNBOOK 是 10 步总流程 + 实测事实表 + 平台回落表的**地图**，本手册不重复那些细节，只给**按客户资料的输入 → 输出链**：每一步明确「输入什么、调什么命令/方法、看到什么算过、产物落到哪个路径」。
> **阅读前提**：细节 SOP 以 [ONBOARDING-PIPELINE.md](ONBOARDING-PIPELINE.md) 为准；冲突时以 RUNBOOK §2 实测事实为准。零上下文先读 RUNBOOK。
> **路径约定（先做，防相对路径断裂）**：
> 1. `TASK=<客户任务目录绝对路径>`（如 `.../30_tasks/<task-slug>`）；`IFK=<interface-kit 绝对路径>`。建议 export 到 shell。
> 2. `mkdir -p "$TASK/70_evidence"`——**下文所有 `70_evidence/` 一律指 `$TASK/70_evidence/`**，命令里用绝对路径或先 `cd "$TASK"` 再执行；kit 脚本（site_pipeline/writing-module/delete-demo-content）则用 `$IFK/` 绝对路径调用。
> 3. `<client>` = client_id；进入客户数据前先锁定（无 client scope 不得扫客户目录）。

---

## §1 输入：客户有什么资料 → 每类怎么用

### 1.1 资料类型与用途表

| # | 资料类型 | 怎么用 | 去向 |
|---|---|---|---|
| 1 | 公司/产品介绍 **PDF / DOCX / PPT** | 宿主解析 → Markdown（保留页码/章节定位）→ 事实抽取，每条标 `confirmed/inferred/missing`。这是**唯一事实源**：文案、规格、认证、联系方式只从这里出 | brief.json 的 `products/posts/story/contact` |
| 2 | 客户**现有网站** | 提炼结构与语气（导航/品类/卖点/规格/真实图片 URL）；确认目标市场语言 | brief + 步骤 5 媒体清单 |
| 3 | 书面 **brief / 聊天口述** | 原文即事实源；客户原话 = 文章痛点/代入感素材（写作前置 5 项之首） | brief 的 `brand/contact` + 文章 facts 集 |
| 4 | **图片**（产品图/公司图/logo/封面） | 先分授权：客户自有 / CC 代找（记录 author+license）；每张定 title/alt/caption | 步骤 5 `upload_media` |
| 4b | **图片型 PDF（无文字层）的图源** | `pdftoppm -r 220` 渲染整页 → 按 130dpi 预览定位的**相对坐标裁剪**产品/公司图（短边压 1600px JPEG q85）→ 拼 contact sheet **逐张目检去标题字残留**（通常需 2-3 轮精修）→ alt/title/caption 清单；**Windows 无 poppler 时用 `pypdf page.images` 提取嵌入图作平替**（ISS-121）；宣传页整页裁剪图带字=素材质量上限，产品主图需求早提示客户给干净图 | 步骤 5 上传；图永远从原 PDF 裁，不外找占位图 |
| 5 | **已有 CMS 后台内容** | 仅续建/迁移用：先 `read_lists` 导出，避免重复 create 堆积草稿 | 步骤 3 选站 + 现状 diff |
| 6 | **没有 / 不足** | 按 §1.2 必问清单问；AI 先执行素材推进策略（先自动提炼 → 不够给方案 → 仅剩不可推断的才问用户） | 缺口清单（标注 demo/待用户提供） |

### 1.2 资料不足时的必问清单（≤5 问，缺项=阻塞）

> 模板：[templates/client-input-checklist.md](templates/client-input-checklist.md) 第一节。以下 5 问收齐才能开工；缺问 3 = 全部阻塞。

| 问 | 要什么 | 为什么阻塞 |
|---|---|---|
| Q1 | **公司/品牌名 + 目标市场语言**（含标语、品牌一句介绍） | 站名/slug/导航/SEO title 前缀全部依赖 |
| Q2 | **真实联系方式**：邮箱（**必须真实可收件**）+ 电话 + WhatsApp + 地址/营业时间 | 表单链路与联系页、全站 globals 浮钮 |
| Q3 | **产品/公司资料文件**（PDF/DOCX/网页/口述） | 唯一事实源；没有它只能全 demo，不可发布 |
| Q4 | **首批内容范围确认**：产品 ≥3（名+一句话+规格+图）、文章主题/本地草稿 ≥4（或接受 demo 占位；**不等于允许远程新建**） | 本地内容计划门：products<3 或 posts<4 时 validate INVALID；remote article.create 只走 canonical JS Controller（Python fail-closed），provider/门不齐则本次 create BLOCK |
| Q5 | **写作素材 + 图片授权**：客户原话/询盘片段 ≥3 条、每文章 2-3 个真实数据、图片自有或同意代找 CC | 缺 Q5 文章只能写通用介绍且必须标注 demo |

动工前用户确认点（client-input-checklist 第四节）：站点名/slug 偏好、demo 值是否可接受、图片授权方式、首批内容范围。

---

## §2 一条龙执行链（步骤 0–12，共 13 步）

> 每步四段式：**输入 → 动作（具体命令/方法名）→ 验收判据 → 产物落盘**，末尾附「坑」（引自 RUNBOOK §2 实测事实表）。

### 步骤 0 — 索引 find/verify（开工硬 gate，ISS-065）

- **输入**：客户资料已到达（拿到任务关键词）+ **凭据就绪**——token 三种取法，按推荐顺序（专题真源：[TOKEN-AUTH.md](../../ADAPTERS/cms/allincms/docs/TOKEN-AUTH.md)，向用户索要凭据前必读）：
  1. **纯 API 登录（推荐，零浏览器；2026-08-30 双路径实测）**：邮箱+密码（对话直发，或用户自写临时文件）→ `AllinCMS(email, password)` 登录一次提取 token；密码即弃，临时文件用完即删。
  2. **浏览器手动取 Cookie（兜底，已验证）**：用户登录 workspace.laicms.com → DevTools → Cookies → 复制 `payload-token`。
  3. **浏览器配置文件提取（方向指引，未实测）**：详见 TOKEN-AUTH.md 方式三；优先 1/2。
  取到后 **`export WS_TOKEN=<token>`（跨平台推荐）**；或 token 文件（chmod 600）传路径。无 token = 全链路不可用。
  - ⚠️ `AllinCMS(...)` 构造**必须关键字传参**：`AllinCMS(email='..', password='..')`——第一个位置参数是 `token`，位置传参会把邮箱当 token 静默失效（页面全部 307 回 /sign-in，2026-09-03 qualification run踩中，ISS-118 同族）。
- **动作**：
  ```bash
  cd <IFK>
  python3 install-deps.py --verify                           # 依赖复检（新环境先 --yes）
  python3 index/registry_tools.py verify                     # 索引完整 → PASS
  python3 index/registry_tools.py find 上传 ; find 分类 ; find 主题 ; find 文章 ; find 审计
  python3 index/registry_tools.py find <客户品类关键词>        # 历史坑：现象→根因→修复链
  python3 scan/scan-actions.py - /sites       # 部署更新后必扫 action id（42 位 hex；token 从 WS_TOKEN 读取，也支持文件路径）
  # ⚠️ 如果扫描发现 id 变了/新 action 出现 → 读 API-DISCOVERY.md（7 步摸索流程）
  python3 allincms_api.py <token> read-sites                  # 冒烟：站点列表 JSON
  python3 check-contract-freshness.py [--live]                # 合同新鲜度四方对照（Registry/canonical JS/host driver/Python helper；可选 --live 实扫部署；漂移先修再干活）
  ```
- **验收判据**：`verify` 输出 `VERIFY PASS`；`find` 相关坑已读；action id 与 `allincms_api.py` 常量一致；`check-contract-freshness.py` 必须 PASS；`20_work/onepass-read-receipt.json` 已用 `--write-receipt` 生成并立刻 `--verify-receipt` PASS。没有 receipt 或 receipt stale = 不得进入 Plan A/Plan B。
- **产物**：`70_evidence/00-preflight.txt`（verify/find/scan/freshness 输出快照）+ `20_work/onepass-read-receipt.json`（必读文件精确 SHA-256 回执；规则变动自动失效）。
- **坑**：跳过 find 直接动手 = 重复已回填的坑（ISS-001/002/003/018/024/059 均为重复踩坑）；action id 用错**静默返回 `{}`**，不报错。

### 步骤 1 — 资料 → brief.json

- **输入**：§1.1 各类客户资料 + §1.2 问答结果。
- **动作**：
  1. 解析 → Markdown（保留来源定位）→ 事实抽取（confirmed/inferred/missing）；
  2. 对照 [templates/site-content-checklist.md](templates/site-content-checklist.md) 的 A–I 九节逐项映射；
  3. 按 [templates/brief-schema.json](templates/brief-schema.json) 填 `site/brand/contact/categories_*/tags/products/posts/story/nav`。
- **验收判据**：`python3 site_pipeline.py validate 70_evidence/brief.json` → `VALID`（products<3 或本地文章计划 posts<4 → INVALID，回 §1.2 Q4；只证明本地成稿输入，不证明远程 article.create 能力）。
- **产物**：`70_evidence/brief.json` + `70_evidence/source-extraction.md`（来源定位 + 图片 author/license + confirmed/inferred/missing 标注）。
- **坑**：所有文案必须来自资料，AI 合成必须显式标 `synthetic demo`（不冒充案例/销量/认证）；brief 里 media 先写 ref 名，URL 在步骤 5 上传后回填。

### 步骤 2 — validate + COP（数量基线）

- **输入**：`brief.json`。
- **动作**：
  ```bash
  python3 site_pipeline.py validate 70_evidence/brief.json
  python3 site_pipeline.py generate 70_evidence/brief.json 70_evidence/generated/   # 生成 payload 集（可选加速）
  ```
  写 COP（内容计划）：**本地内容计划基线**（产品 ≥3、文章主题/草稿 ≥4；remote published posts 另按现有 exact IDs，[CONTENT-MINIMUM.md](templates/CONTENT-MINIMUM.md)）+ 文章主题 + 分类/标签清单 + faq_answers/cta/units 值。
- **验收判据**：`VALID`；COP 明确**每类实建数**（这个数 = 步骤 12 audit `count` 基线）。
- **产物**：`70_evidence/<slug>-cop.md`。
- **坑**：audit/gate/contact 不带 `--config` 会沿用 **Demo 基线误判新站**（ISS-063）——COP 就是该 config 的全部取值来源。

### 步骤 3 — Plan A：create_site（只建站，不填内容）

- **输入**：`brief.site`（name/description）。
- **动作**：
  ```python
  api.create_site(name, description)        # 只建站；绝不与内容填充合一步；description ≤200 字符（超长被 zod 拒，P1/ISS-120 族）
  site = api.read_sites()["sites"][0]       # 校验唯一新站；slug 从响应或 read_sites 取
  ```
  站点已存在（续建/迁移）→ `read_sites` 选目标站，跳过 create。
  **slug namespace 建站前预检（ISS-124）**：拿到 slug 后、批量写内容前跑
  `python3 "$IFK/check-slug-namespace.py" <slug>`——产品 slug 与分类/tag slug 同名会在
  publish 才报 `validation.slug.duplicate`（ISS-084）；新站的 demo taxonomy 与续建站的
  既有 taxonomy 都在检测范围内，冲突清单非空（exit 1）先改命名计划再动工。
- **验收判据**：拿到**真实** `site_id`/`site_key`；`read_sites` 可见唯一新站；slug 预检 exit 0。
- **产物**：`70_evidence/<slug>-plan-a-readback.json`（site_id/site_key/账号 owner 读回证据）。
- **坑**：账号非首站时 createSite 只给 blank 主题（0 页）——不要指望自动 7 页，步骤 9 必须手工 `create_theme`；`create_site` description ≤200 字符。

### 步骤 4 — 填「新站改造清单」（customization checklist）

- **输入**：`brief.json` + COP + [templates/new-site-customization-checklist.md](templates/new-site-customization-checklist.md)。
- **动作**：拿客户资料把 checklist **每个字段填成该客户的值** → 落成 `<slug>-customization.md`；步骤 5–9 严格按它执行。
- **验收判据**：checklist 每个字段都有「该客户的值」或显式 `待用户提供/demo` 标记；与 site-content-checklist.md A–I 九节无缺口。
- **产物**：`70_evidence/<slug>-customization.md`。
- **坑**：服务端回填默认——**未显式字段会被模板默认值填充**（模板文案/假链接），checklist 上「可显示字段全部显式传」必须逐条落实；header 导航 children 必须递归 dict。
- **引用与回落**：与 checklist 的接口约定见 §5。该文件已存在（/166 字段，2026-08-30）；若缺失则按 MODULES.md 37 块字段全集 + §5 接口节执行，不阻塞主链。

### 步骤 5 — 媒体上传 + alt 回写

- **输入**：素材文件（客户图/CC 图）+ customization 的 media 节。
- **动作**（推荐一步两段式封装，ISS-122）：
  ```python
  r = api.upload_media_with_meta(slug, site_id, file_path, title, alt, caption)  # 上传→媒体库按 name 对账→update_media 回写
  # r = {id, url, path, title, alt}；内部已处理 media_urls 累积陷阱与最新记录匹配
  api.read_media_library(slug)                                           # 抽查核对（键为 {status, media}）
  ```
  手工两步等价写法：`upload_media(...)` → `update_media(slug, media_id, site_id, title, alt, caption)`（upload 的 title/alt 位置参数不生效）。
- **验收判据**：`read_media_library` 核对 10 字段（name/alt/url/path/size/mimeType…）；**URL 带扩展名**；license 记入证据。
- **产物**：`70_evidence/media-manifest.md`（文件名 → URL/alt/license）；URL 回填 brief.json 的 media ref。
- **坑**：**`upload_media` 的 title/alt/caption 位置参数不生效**（multipart 只传文件+siteId）——上传后记录是文件名 stem，**必须回写** SEO 元数据（`upload_media_with_meta` 已内置）并复核（2026-09-03 qualification run：22 张 alt 全为 stem，回写后 22/22 生效）；**`media_urls` 是历史累积全量勿当本次结果**（ISS-019/122）；URL 不带扩展名 → 运行时 404；同页不重复用同一张图（分类卡/hero 错开）；批量上传后以 read_media_library 为真源建 ref→{url,media_id} 映射表，产品 payload 的 media 用 `{source:"url", url:<CDN>}`（新站 ISS-105）；串行快传可能出现记录错位/缺失（ISS-109）——逐张对账后再进下一张。

### 步骤 6 — 分类 / 标签

- **输入**：customization 的 taxonomy 节。
- **动作**（推荐 safe 封装：内置对账 + transaction 竞态退避重试，ISS-123）：
  ```python
  from allincms_api import create_taxonomy_safe
  r = create_taxonomy_safe(api, slug, site_id, "category", name, cslug, content_type='products'|'posts')  # cover 显式 None
  r = create_taxonomy_safe(api, slug, site_id, "tag", name, cslug, content_type='products'|'posts')
  # r = {kind, name, slug, content_type, id, already_exists, attempts, flight}；id 来自回读
  ```
  手工等价：`api.create_category2(slug, site_id, name, slug, content_type=..., cover=None)` / `api.create_tag(...)`，但需自带对账与重试。
- **验收判据**：产品分类与文章分类**分开建**；cover=None 未 500；记录全部 id（后续 payload 用 **id 字符串数组**）；建完重跑 `check-slug-namespace.py` 确认与产品 slug 计划无冲突。
- **产物**：`70_evidence/taxonomy-ids.json`（name → id 映射）。
- **坑**：cover 缺省报 validation error；payload 传 id 数组（读回是对象数组）；**transaction number mismatch 竞态是间歇性的**（qualification run 中多次）——`create_taxonomy_safe` 已内置"每轮先 read_lists 对账确认不存在 → create → 回读取 id；失败含 transaction number 时 sleep 5→8→13s 重试"；手工路径配方：等 6-8s → read_lists 只读对账（确认远端不存在）→ 重试**同一**请求，勿换参数；对账形状：categoryOptions/tagOptions 行是 `{label,value(id)}`（label=分类名，映射表按 name 存，组装 payload 时 slug→name→id 三段转换，ISS-118）。

### 步骤 7 — 产品 create/publish（每个产品一遍）

- **输入**：customization products 节 + `taxonomy-ids.json` + 媒体 URL + **每产品正文 facts/应用场景/选型要点**。
- **动作**（每产品）：
  ```python
  p  = 最终完整 business payload   # 骨架 = templates/product-payload-example.json；
                                   # media=oss+path；categories/tags=id 字符串数组；
                                   # specifications=[{key,value}]；content=非空 Slate
  # create/update 均先 resolve target：不存在 → operation=create,target_id=null；存在 → update,exact id
  # ① content-review-gate.py digest p
  # ② 独立 reviewer 按 product-content-review-prompt.md 审查最终全字段 p + facts + update diff
  # ③ 产 <slug>-review.json：site/target/operation/phase/producer/reviewer/checks/findings + exact digest
  # ④ 唯一受支持 mutation 入口（review + fresh capability 内部强制；裸方法 fail-closed）：
  result = api.mutate_reviewed_product(slug, site_id, p, review_path, capability_context,
                                       target_id=None_or_pid)
  # create 时 wrapper 在审查后内部执行 create_draft → publish_update；update 直接 publish_update
  ```
  > **capability context 刷新（ISS-117/125，每批 mutation 前执行，禁止复用上一批）**：
  > ```python
  > # 推荐封装（2026-09-04 起）：观察 action id → 写 70_evidence/ 证据 → 返回自检过的 context
  > capability_context = api.refresh_product_capability(slug, site_id, TASK_ROOT, client, task,
  >                                                    operation='create'|'update')  # 站内无产品返回 None
  > ```
  > 手写模板（等价底层，字段缺一不可）：
  > ```python
  > now = datetime.datetime.now(datetime.timezone.utc)
  > stamp = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
  > ev = {"deployment_id": <DEPLOY>, "site_key": S, "site_id": SID,
  >       "verified_operations": sorted(required_ops),          # 与路由 gate 要求精确一致
  >       "action_ids": {op: <对应 42hex 常量> for op in required_ops},
  >       "observed_at": stamp}
  > json.dump(ev, open(evp, "w"), indent=1)                     # 先写 evidence
  > cap = {"status": "live_verified_current_deployment", "deployment_id": <DEPLOY>,
  >        "site_key": S, "site_id": SID, "operations": sorted(required_ops),
  >        "evidence_ref": "70_evidence/<capability-evidence>.json", "observed_at": stamp,
  >        "expires_at": (now+timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
  >        "runtime_scope_root": <TASK_ROOT 绝对路径>,
  >        "evidence_digest": "sha256:" + hashlib.sha256(open(evp,'rb').read()).hexdigest(),
  >        "client_id": client, "task_id": task}
  > ```
  > evidence 与 context 的 observed_at 必须同值；evidence 文件改动后 digest 必须重算；一批超 25 分钟即整批刷新。
- **验收判据**：`api.read_lists(slug,'products')` 与 COP 逐条 diff（数量/名称/slug/规格）；状态字段 `_status=='published'`（键名是 `_status`，ISS-108；create-only 草稿 `_status` 非 published 且**公网不可见**=ISS-105 另一面）；`read_product` 的 content **非空**；公网每个产品详情页 `<article>` 内至少 1 个实质 H2 + 正文事实短语 SSR，且相关产品模块真链接可点、无空态。
- **产物**：`70_evidence/products/<slug>.json` + `<slug>-review.json`（最终 payload + 独立 reviewer READY 记录，digest 精确绑定；含 business_operation=create|update、site/target binding）。
- **坑**：`content: []` 只会建出有图/规格、无正文的空心详情页（ISS-097）；create 后 draft slug 会变时间戳，publish 时 payload 必须带正确 slug；publish/update 额外契约=siteId + media `source:"oss"/path` + taxonomy id 字符串数组（ISS-098，readback 对象数组不可原样回传）；全量 update 必须从 current readback + brief 真源合并，**不得复用可能过期的存证 payload**，尤其 specifications/content/media（空数组会真清空后台，ISS-101）；合并后必须再归一化为**写接口形状**：media 从读回包裹/url 形状转 `source:"oss"+path`，categories/tags 从对象数组转 id 字符串数组，specifications/content 以 brief/COP 真源覆盖（不得把 read_product/read_lists 读形状原样回传）；同 slug 重跑会堆积 Untitled 草稿（ISS-059）→ 先 `read_lists` 查 slug；正文内联 link 节点前台平铺无 `<a>`，产品/文章内链必须用页面模块 target（feature-grid/product showcase），不可伪造正文链接。
  > **blockquote 两门矛盾（ISS-112，2026-09-03 qualification run）**：content_review_gate 要求 blockquote.children 嵌套 {type:p} 块，site_pipeline product-content 门空块判定只认 children[].text 平铺——同一 payload 无法同时过两门。**产品正文禁用 blockquote**，选型建议用 p 段（"Buyer tip: " 前缀）。
  > **跨站差异（ISS-105，2026-09-02 新建站实测）**：不是所有站都接受 `source:"oss"`。新建站产品 upsert 若 media=oss+path 会**静默拒绝整个 payload**（产品保持 Untitled）；`specifications.value` 有 200 字符上限（`validation.specifications.valueMax200`）。**写产品前先扫该站是否有 `createProductAction`**（若无只能走 update/upsert，即 `mutate_reviewed_product(target_id=draft id)`）；media 用 `{source:url, url:<CDN url>}`；长型号清单放 `content` 正文、specifications 只留短 value（≤200）；publish 后查 response 的 `validationErrors` 是否为空。API 读回媒体库能拿每张图的真实 `url`。

### 步骤 8 — 文章 k3 写 + flash 审 + reviewed update（create canonical 于 full-source JS Controller）

- **输入**：写作前置素材（client-input-checklist 第六节）+ COP 文章主题 + customization posts 节。
- **article.create 执行路由（P0-3.1 后唯一口径）**：Registry 合同仍是 `availability=canonical + fresh_live_verified_current_deployment`，但**唯一执行面是 full-source JS Controller**——用 `ADAPTERS/cms/allincms/content-run-controller.mjs` 跑 content plan，经 `content-plan-host-driver.mjs` 的 `article:create` handler 调 `article-operations.mjs#createPostDraft`，且宿主必须注入**三个真实 provider**：`articleBeforePostIdsProvider`（真实同站 before post-ID 快照，禁止伪造空快照）、`articleCreateReadbackProvider`（权威 backend 完整回读 + afterPostIds）、`articleEditorReopenProvider`（真实编辑器重开 200/authenticated/healthy）。**缺任一 provider 时本次 create BLOCK**（canonical 合同仍在，执行门不齐），不得降级到 Python。资格验证五步（合同扫描零漂移 / before-after 快照差集恰 1 / 完整回读 / 编辑器重开）即由这三道 provider 在 Controller 内落实；证据样例见 private qualification task `70_evidence/article-create-qualification.json`（ISS-111，2026-09-03 qualification site 实测）。
- **Python fail-closed 边界（防第二执行面）**：`TOOLS/interface-kit/allincms_api.py` 不再提供文章 create——`_create_post_transport`、`_send_content_transport(..., CREATE_POST, ...)`、`mutate_reviewed_post(target_id=None)` 三处一律抛 `ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED`（任何 review/capability/network/readback 之前）；Python 只保留 **exact-ID reviewed update**（`mutate_reviewed_post(target_id=<exact_pid>)`）。create 后 draft slug 变时间戳，由 reviewed update 带正式 slug 覆盖。
- **provider 不齐时的分支**：4 篇仍完成本地成稿+独立评审+review records，但**不远程创建**；主题构建时移除 Posts 导航、news/post-related 模块，并从 audit pages/count/FAQ article 断言中移除远程文章项，DELIVERY 首行记录 `article.create=BLOCK / local drafts ready`（注明缺哪个 provider）。不得保留空文章列表入口，也不得改用 Python 创建。
- **动作**（五步链，入口 [writing/WRITING-INDEX.md](writing/WRITING-INDEX.md)）：
  ```bash
  python3 writing/writing-module.py outline 70_evidence/brief.json     # 六段式骨架（可选）
  # ① 主 AI 从源 PDF 提炼 facts（只用源内事实；禁止编价格/MOQ/认证/客户案例）
  # ② 派【写作子 agent】（子代理连续 Provider 失败≥2 次即主线程兜底直写，勿耗在重试）：
  #    BRIEF.md（facts+主题+Slate 规范）+ article-writing-logic.md + PROGRESSION.md
  #    产出 70_evidence/posts/<slug>.json（字段全集 = templates/post-payload-example.json）
  # ③ 机器检查：python3 writing/writing-module.py check 70_evidence/posts/<slug>.json
  # ④ 派【评审子 agent，模型=flash】：templates/ghostwriter-review-prompt.md（5 维评分+最弱 3 处+钩子）→ READY / NEEDS_REWRITE
  # ⑤ NEEDS_REWRITE → 回改表达（不动事实）重审；READY 后对最终完整 post business payload（含
  #    title/slug/excerpt/order/coverImage/content/categories/tags）做 digest，产严格 review JSON；
  # ⑥ create：full-source JS Controller（content-run-controller + article:create handler +
  #    articleBeforePostIdsProvider/articleCreateReadbackProvider/articleEditorReopenProvider，
  #    缺 provider 本次 create BLOCK；Python 不得代发）；
  # ⑥' create 拿到 exact post ID 后的 reviewed update（Python 唯一文章 mutation 入口）：
  api.mutate_reviewed_post(slug, site_id, post_payload, review_path, capability_context, target_id=exact_pid)
  # 先 read_lists 查 exact slug；无 exact ID 且 JS Controller provider 不齐则本次 create BLOCK，
  # 不得创建（ISS-059/102/111，P0-3.1）
  ```
- **验收判据**：`check` PASS + 评审 READY + 发布后抓取验证 **SSR**（FAQ 实质短语出现在公网 HTML）。
- **产物**：`70_evidence/posts/<slug>.json` + `70_evidence/posts/<slug>-review.md`（人读评审报告）+ `70_evidence/posts/<slug>-review.json`（机器严格 context）。
- **文章上线收尾链（发布≠完成，缺这步导航没有文章入口）**：① 全站 7 页 globals 的 header navigation 加回 `Articles`（含分类下拉）+ footer 加文章链接列（逐页 save+publish）；② home 恢复 `featured-news-list-editorial` 模块（children 插在 materials-1 后，结构照 MODULES.md）；③ audit config 更新：pages 加 `posts/{slug}`、count.posts=实数、faq_answers 改为文章页 FAQ 实测渲染短语；④ 公网逐篇 200+H2 SSR 验证后重跑完整 audit。文章 blockquote 用嵌套 p（ISS-112）；批量 capability context 每批刷新（ISS-117）。
- **坑**：正文原生 Slate 类型 = `p|h2|h3|blockquote`（`heading`/`paragraph` 旧词法已禁用，ISS-060）；**blockquote.children 必须嵌套 `{type:"p",id,children}` 块**（ISS-112：平铺 text 被 content_review_gate 拒；writing-module 兼容嵌套）；正文内联 link 节点平铺渲染**无 `<a>`**——文章 CTA 放步骤 9 的页面级块；文章挂**文章分类** id，勿用产品分类 id；coverImage 是 media 对象（source:url+CDN url，新站见 ISS-105）。

### 步骤 9 — 主题 createTheme(default) + 7 页内容写入（save+publish）+ globals

- **输入**：customization 的 7页/home 节 + 全部内容（产品/文章/媒体 URL）。
- **动作**：
  ```python
  api.create_theme(slug, site_id, 'My Default', 'Default theme', preset='default')   # preset='default' 总是 7 页
  themes  = api.read_themes(slug)['themes']
  theme_id = [t['id'] for t in themes if t['name'] == 'My Default'][-1]              # id 会变，现取勿猜
  r = api.read_pages(slug, theme_id)
  page_id = r['pages'][0]['id']                                  # 逐页循环时换成当前页 id
  c = api.read_page_document(slug, theme_id, page_id)
  doc, globals_doc, tc = c['initialPayload']['page']['document'], c['initialPayload']['page']['globals'], c['initialPayload']['page']['themeConfig']
  # 逐页改 doc（allincms_blocks.py 重建 + MODULES.md 37 块白名单），每页：
  api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='save')
  #   read_page_document 深度 diff（只允许 columnCount 无害回填；formSlug="" 在表单块=断裂必修，本步必须绑真实 slug）→
  api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='publish')
  # globals 按页存储：同一份 globals_doc 对全部 7 页逐页 save+publish（只交一页≠全站一致）
  ```
  文章详情页 CTA 真链接：post-detail 页 `page-root.children` 追加 `cta-1`（type `material-story-split`，`actionTarget={"type":"custom","href":"/contact-us?source=<site>-article"}`），并替换 related-1 demo 文案。
- **验收判据**：7 页 readback diff≈0；globals 7 页一致；公网无空态文案（`No content is available yet` 等——单品/单文时删详情页 related 模块）。
- **产物**：`70_evidence/pages/<page>.json`（每页最终三件套存证，共 7 份）。
- **坑**：**createTheme(default) 会重新种入 3 demo 产品 + 3 demo 文章**（站点级，ISS-071，步骤 11 清）；空字符串字段会被 zod 打回默认值（如 WhatsApp `wa.me/+44-7911-123456`）→ 删 demo 按钮=**移除元素**（children+elements 同删），不是置空（ISS-068）；主题 id/页面 id 会变，一律 `read_themes/read_pages/read_page_document` 现取；**全局弹窗元素必须带 anchorId=header cta 锚点名，null 时公开站静默丢弃整树（ISS-094，builder 默认已带）**。
  > **hero/carousel 隐藏商城槽位（ISS-113，2026-09-03 qualification run）**：hero-commerce 除显性字段外还有 productName/productDescription/productPriceLabel/campaignPills[].value/mediaMeta/actions[].label 六处；carousel slides 每项还有 price/product/primaryLabel/secondaryLabel 四处——不显式覆盖（可空串）服务端回填 demo 值（Weekender Tote/From $96/Materials and care 系），audit template 多轮才清完。serviceItems 结构为 icon+title+description；materials-1 的 actionLabel/actionTarget 也是隐藏槽（demo 值 "Read the material guide" 会被 audit template 抓）。落库前对照 ISS-113 清单**逐页逐模块**枚举 demo 词（`re.search` 打分脚本扫 doc JSON）一次性清零，不要等 audit 一轮轮揭露。
  > **globals 写入（ISS-106，2026-09-02 新建站实测）**：`save_home` 传**自建的 globals 结构**不会覆盖页面级 globals（readback 仍是旧值，因缺 children/anchorId 等被服务端回退用存储值）。正确做法：`read_page_document` 取 `ip['globals']`，**只改目标字段**（如 `header-dropdown-1.props.ctaTarget`、`footer-columns-1.props.brand`），其余原样回传 `save_home(intent=save)` → `readback` 确认 → `save_home(intent=publish)`。**导航 CTA 弹窗** = `ctaTarget: {type:"action", anchorId:"contact-form-dialog"}`（公网 `#contact-form-dialog`，参照弹窗站已验证）。涉及站点级/头部/footer 的可见改动，若页面级 publish 后公网未刷新，用后台主题设计器的 **Publish**（站点级）触发 CDN。
  > **网格列数=条目数 + 大标题规则（ISS-107，2026-09-02 实测）**：带 `columnCount` 的网格模块按列数**固定生成 N 列、条目不足不折叠**——3 列只填 2 条 proofRows → 公开站第三列只剩边框空白卡；4 列只填 2 个分类卡 → 右半幅约 540px 空白。提交前逐模块校验 `columnCount == len(items/proofRows/reviews/stats/values)`，改列数或补条目二选一。hero-commerce 大标题固定 72px 不随列宽缩放：长标题在窄列堆 6 行、连字符首词断孤儿行（"Wall-mounted"→"Wall-"独行），标题**避免连字符词开头、≤42 字符**。**模板固有行为登记不硬改**：hero 左列 content-between 中段空隙、产品卡 line-clamp 截断、奇数卡末行空位、吸顶导航 bg-background/95 半透明（滚动截图时底下内容 5% 透出，勿误判为重叠 bug）。**内联表单卡 formSlug 必填（ISS-110，2026-09-03 physolar 首页实测）**：contact-form-split 缺 formSlug 时公网只渲染表单卡外壳、同页 0 个 `<form>`；builder `contact_split()` 已带默认 `contact-inquiry`，audit form-render 已扩展为扫描所有含该模块的页面（不再只查 /contact-us）。

### 步骤 10 — 激活 + 路由 + set_home_page（顺序规则）

- **输入**：theme_id + `read_pages` 的 routes 快照。
- **动作**（**顺序固定**）：
  ```python
  api.apply_theme_routes(slug, site_id, theme_id, [{'routePath': p['path'], 'pageId': p['id']} for p in r['pages']])
  api.set_theme_active(slug, site_id, theme_id)
  home_page_id = [p['id'] for p in r['pages'] if p['path'] == '/home'][0]
  api.set_home_page(slug, site_id, theme_id, home_page_id)   # 必须最后（action=setHomePageAction，URL=/{slug}/themes/{themeId}）
  ```
- **验收判据**：根路径 `/` 返回 200 且渲染首页（**非** "Allin CMS Runtime" 错误壳）；`/about-us` `/contact-us` `/posts` `/products` 均 200。
- **状态自检（先 API 后 curl，ISS-108）**：
  ```python
  th = [t for t in api.read_themes(slug)['themes'] if t.get('active')][0]  # ⚠️ 键名是 active，isActive 不存在（恒 None）
  assert th['id'] == theme_id and th.get('homePageId') == home_page_id and th.get('homePagePublished') is True
  # homePagePublished=False 或 homePageId 为空 → 根路径必然是 Runtime 壳，回到上方动作重跑（勿等 curl 才发现）
  rp = api.read_pages(slug, theme_id)
  assert all(p.get('enabled') for p in rp['pages']) and all(rt.get('status')=='bound' for rt in rp['routes'])
  ```
- **产物**：`70_evidence/routes-final.json`（routePath → pageId 快照）。
- **坑**：`setThemeActive` 是**唯一会清空 homePageId** 的操作 → set_home_page 必须最后（routes/activate 次序互换无害，实测路由不破坏绑定）；**任何未来重新激活主题后都要重跑 set_home_page**；其余路径（`/{slug}/themes`）返回 200 但**静默无效**；激活键名是 `active` 不是 `isActive`，判断生效状态一律用 §2.1 诊断树的实测键名。

### 步骤 11 — demo 种子清理（createTheme 重种 3 产品+3 文章+6 分类+7 标签，全链）

- **输入**：`api.read_lists(slug,'products'|'posts')` 现状 + customization 的 ⑩ 清理节。
- **动作**：
  ```bash
  python3 "$IFK/delete-demo-content.py" <slug> --dry-run   # ① 先 dry-run 列将删项（DOC-033 全链：3 产品+3 文章+6 分类+7 标签，带引用护栏）
  # ② 把 dry-run 清单给用户确认（删除类操作必须取得明确授权；不可恢复）
  python3 "$IFK/delete-demo-content.py" <slug>             # ③ 授权后执行真删
  ```
  脚本退出码非 0 = taxonomy 仍有残留（可能被内容引用）→ 按 WARN 名单人工处理。页面内 demo 元素（whatsapp 假号、假社媒、footer demo 标注）**删元素**后对应页 save+publish 重交。
- **验收判据**：脚本输出 `DONE` + taxonomy remaining 无 demo 名；`read_lists` 计数 == COP 实建数；audit `count` 项自动通过。
- **产物**：`70_evidence/cleanup-log.md`（脚本输出贴存：删除前后计数 + taxonomy 终态）。
- **坑**：**每次重建主题都会重新种入 demo（含 taxonomy）** → 重跑步骤 9 后必须重跑本步；demo 分类/标签 0 引用也会公开出现在列表页筛选下拉（ISS-074）；置空会被 zod 顶回 demo 默认值 → 删元素而非置空（ISS-068）。

### 步骤 12 — 每站 audit-config + audit/gate/contact 三门 + DELIVERY

- **输入**：COP + 步骤 1–11 全部产物。
- **动作**：
  ```bash
  cp templates/site-audit-config.template.json 70_evidence/<slug>-audit-config.json
  #   按 COP 填：pages（全部产品 slug；仅 existing reviewed-update 文章加文章 slug）、count（远程实建数）、faq_answers（仅有远程文章时加）、cta（真链接+source）、units
  python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json --out 70_evidence/audit-report.json
  python3 site_pipeline.py gate <slug> --config 70_evidence/<slug>-audit-config.json
  python3 site_pipeline.py contact <slug> --config 70_evidence/<slug>-audit-config.json --real "<真实电话|邮箱|地址>"
  python3 site_pipeline.py product-content <slug> --config 70_evidence/<slug>-audit-config.json  # 独立扩展闸；audit 历史口径仍为 13 项
  # DELIVERY：templates/delivery-manifest.md → 70_evidence/DELIVERY-<slug>-<date>.md（链接表每行核验 200 + 已知事项照抄 RUNBOOK §9）
  python3 onepass-completion-gate.py "$TASK"  # receipt/Plan A+B/回读/媒体/taxonomy/产品文章评审/路由/audit/DELIVERY 装配闸
  # 收尾：70_evidence/HANDOFF.md + 新坑回填 issues.tsv（fixed/boundary/pending）+ registry_tools.py verify + gen
  ```
- **验收判据**：audit 13 项站内检查全 PASS（历史口径不变）+ product-content 独立扩展闸 PASS；gate PASS；contact PASS；DELIVERY 链接表**每行核验列非空且为 200**；`onepass-completion-gate.py "$TASK"` 输出 `ONEPASS_COMPLETION_STRUCTURE_PASS`。三门通过后、DELIVERY 签发前，另按 [templates/site-acceptance-v2.md](templates/site-acceptance-v2.md)（TPL-023，7 层 61 项 + 四轮对抗流程）逐项验收——判据="陌生买家能否完成询盘"，证据落盘 `70_evidence/acceptance-v2.md`。
- **产物**：`<slug>-audit-config.json`、`audit-report.json`、`acceptance-v2.md`、`DELIVERY-<slug>-<date>.md`、`HANDOFF.md`（详见 §4）。
- **坑**：没有 `--config` 的 audit 会用 Demo 基线误判新站（ISS-063）；**faq_answers 断言短语必须逐字取自公网 FAQ 卡渲染文本**（校准方向=断言对齐现实，不是改内容迎合断言）；posts=0 时 faq-answer/cta/h2-semantic 三项文章断言无法通过（config 无开关）——DELIVERY 已知事项注记 N/A 及原因；`product_content` 是 **dict**（slug→{required_h2:int, fact_phrases:[]}）；公网 CDN 缓存 publish 后 5–10s 生效，验收以列表页数据源 + counter 为准；audit 连续 FAIL 时逐词 grep 公网 HTML 定位残留模块（template 词是渐进揭露的，一轮全清完再跑）。

---

## §3 验收汇总

### 3.1 16 URL 校验表（模板，交付前逐行核验）

> `https://<site_key>.web.allincms.com` 记为 `<DOMAIN>`；核验方法：`curl` + `site_pipeline.py gate` + 公网抓取 SSR + 截图复查。

| # | URL | 说明 | 核验判据 |
|---|---|---|---|
| 1 | `<DOMAIN>/` | 根路径 = 首页 | 200 + **非 Runtime 错误壳**（root-home 回归项）+ gate 0 残留 |
| 2 | `<DOMAIN>/products` | 产品列表页 | 200 + 网格满卡（≥3 产品，无空态文案） |
| 3 | `<DOMAIN>/products/<product-1>` | 产品详情 1 | 200 + 规格面板 + 主图 alt |
| 4 | `<DOMAIN>/products/<product-2>` | 产品详情 2 | 200 |
| 5 | `<DOMAIN>/products/<product-3>` | 产品详情 3 | 200 |
| 6 | `<DOMAIN>/posts` | 文章列表页 | 200 |
| 7 | `<DOMAIN>/posts/<post-1>` | 文章 1 | 200 + FAQ 实质短语 SSR + CTA 块在页 |
| 8 | `<DOMAIN>/posts/<post-2>` | 文章 2 | 200 |
| 9 | `<DOMAIN>/posts/<post-3>` | 文章 3 | 200 |
| 10 | `<DOMAIN>/posts/<post-4>` | 文章 4 | 200 |
| 11 | `<DOMAIN>/about-us` | 公司页 | 200 + 6 模块（intro/story/stats/values/team） |
| 12 | `<DOMAIN>/contact-us` | 联系页 | 200 + 真实联系方式（无 demo 电话/假社媒） |
| 13 | `<DOMAIN>/sitemap.xml` | sitemap | 200 + URL 覆盖上述全部页面 |
| 14 | 产品主图 assets URL | 图片资源 | 200 + 扩展名 + alt 正确 |
| 15 | 文章封面 assets URL | 图片资源 | 200 + license 已记录 |
| 16 | `<DOMAIN>/contact-us?source=<site>-article` | 文章 CTA 真链接落点 | 200 + `source` 参数保留 |

### 3.2 audit 机检项（13 项，含 root-home 根路径回归项 + form-render 表单渲染项）

> 命令：`python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json`。**13 项站内检查全部 PASS 才上线**；审计范围以 site_pipeline.py 代码为唯一真源。

| # | 机检项 | 判据 / 失败动作 |
|---|---|---|
| 1 | count | == COP 实建数（产品 N / 文章 M）；多出即 demo 种子残留 → 回步骤 11 |
| 2 | 200 | 配置内全部页面返回 200 |
| 3 | 空态 | 无 `No content is available yet / No items yet / No results / coming soon` |
| 4 | 模板词 | 模板词表 0 命中（自检词表见 MODULES.md 六） |
| 5 | demo 联系方式 | 无 `wa.me/+44-7911-123456` 等 demo 电话/邮箱/WhatsApp |
| 6 | FAQ SSR | faq_answers 实质短语出现在公网 HTML（非客户端渲染） |
| 7 | 真 CTA | 真实链接 + source 参数（`/contact-us?source=<site>-article`） |
| 8 | 单位 | 规格/正文单位规范（metric/imperial 一致） |
| 9 | 绝对化 | 无绝对化违规声明（best/guaranteed 等） |
| 10 | Markdown 残留 | 无 `**`/`#` 等 Markdown 符号泄漏到页面 |
| 11 | h2 语义 | 正文 h2 结构符合 required_h2 基线 |
| 12 | root-home | 根路径 `/` 渲染首页而非 Runtime 壳（防 set_home_page 回归；任何重新激活主题后重跑步骤 10 末尾验证） |
| form-render | contact-us 渲染真实 `<form>`+submit | 表单块 formSlug 空=断裂（ISS-076） |

---

## §4 交付物清单（必须留档，全部在 `70_evidence/`）

| 文件 | 来源步骤 | 内容要求 |
|---|---|---|
| `00-preflight.txt` | 0 | verify/find/scan 输出快照 |
| `brief.json` | 1 | 客户资料提炼结果（validate VALID） |
| `source-extraction.md` | 1 | 来源定位 + confirmed/inferred/missing + 图片 author/license |
| `<slug>-cop.md` | 2 | 内容计划：数量基线/主题/分类/faq/cta/units |
| `<slug>-plan-a-readback.json` | 3 | Plan A 读回：真实 site_id/site_key/账号 owner |
| `<slug>-customization.md` | 4 | 逐字段填值的改造清单（该客户专属值） |
| `media-manifest.md` | 5 | 文件名 → URL/alt/license |
| `taxonomy-ids.json` | 6 | 分类/标签 name → id 映射 |
| `products/<slug>.json` + `<slug>-review.json` ×N | 7 | 每产品最终 publish payload + digest-bound 独立审查 READY（create/update） |
| `posts/<slug>.json` + `<slug>-review.md` + `<slug>-review.json` ×N | 8 | k3 成稿 + flash 内容评审 + digest-bound READY 记录（create/update） |
| `pages/<page>.json` ×7 | 9 | 每页最终三件套（document/globals/themeConfig） |
| `routes-final.json` | 10 | routePath → pageId 快照 |
| `cleanup-log.md` | 11 | demo 删除前后计数 |
| `<slug>-audit-config.json` + `audit-report.json` | 12 | 每站审计基线 + 机检结果 |
| `DELIVERY-<slug>-<date>.md` | 12 | 交付清单：16 URL 表（每行 200）+ 内容清单 + 核验记录 + 已知事项 |
| `HANDOFF.md` | 12 | 状态/事实矩阵/下一步 |
| `issues.tsv` 回填（新增坑时） | 12 | 现象→根因→修复，`verify` + `gen` 通过 |

---

## §5 与 templates/new-site-customization-checklist.md 的接口

> [templates/new-site-customization-checklist.md](templates/new-site-customization-checklist.md) 由另一文档维护（逐字段改造清单）。本手册第 4 步 = **拿客户资料把该 checklist 的每个字段填成该客户的值**，产出 `70_evidence/<slug>-customization.md`，后续步骤 5–9 只消费这份填值清单。
> 该文件已存在（templates/new-site-customization-checklist.md，166 字段逐条含 demo 值+替换示例）；**若缺失**：不阻塞主链——按 MODULES.md 37 块字段全集 + 下方接口节执行（本接口节即两文档的契约，避免内容重复）。

```text
接口节（NEW-SITE-ONEPASS 第 4 步 ↔ new-site-customization-checklist 填写器约定）
site      ← brief.json: site(name/slug/description)+brand+contact              → 步骤 3 create_site 参数、步骤 9 globals 文案
globals   ← brand(title/tagline/cta)+contact(email/phone/whatsapp/address)+社媒[] → 7 页统一 globals_doc（浮钮/弹窗/footer）
7页/home  ← site-content-checklist E/F/G + 首页 11 模块启用裁剪表             → 每页 document 增删改点（含文章详情页 CTA 块）
taxonomy  ← categories_posts/categories_products/tags（name+slug）            → 步骤 6 create_category2/create_tag 参数
media     ← 素材文件 → title/alt/caption/license                              → 步骤 5 upload_media/update_media 清单
products  ← 每产品 name/slug/description/specs/priceLabel/media/categories    → 步骤 7 product-payload-example 骨架填值
posts     ← 每文章主题/facts 集/标题/slug/excerpt/分类                        → 步骤 8 k3 写作输入 + post-payload-example 填值
audit+home+清理 ← COP 数量基线 + 首页模块裁剪 + demo 元素/3+3 种子删除清单     → 步骤 12 audit-config 值、步骤 9/11 动作
```

---

## 卡住时（顺序执行，同 RUNBOOK §11）

1. `python3 index/registry_tools.py find <关键词>`（历史坑有现象→根因→修复链）；
2. `python3 site_pipeline.py audit <slug> --config <cfg>`（拿事实矩阵再判断）；
3. 看 `templates/*.json` 实测 payload 样例 + `MODULES.md` 37 块白名单；
4. 新发现 → 修完立即回填 `issues.tsv`（fixed/boundary/pending）+ `verify`。
