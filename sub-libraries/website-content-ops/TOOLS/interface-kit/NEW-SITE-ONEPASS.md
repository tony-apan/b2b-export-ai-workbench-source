---
title: "NEW-SITE-ONEPASS.md —— 给一份客户资料，AI 一条龙建完一个站"
type: "runbook"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
sources: ["RUNBOOK-ANYONE.md（10 步总流程/实测事实表/平台回落表）", "ONBOARDING-PIPELINE.md（细节 SOP）", "templates/client-input-checklist.md", "templates/site-content-checklist.md", "templates/CONTENT-MINIMUM.md", "templates/brief-schema.json", "templates/site-audit-config.template.json", "templates/post-payload-example.json", "templates/product-payload-example.json", "templates/delivery-manifest.md", "writing/WRITING-INDEX.md", "index/registry_tools.py", "MODULES.md（37 块注册表）", "Example 全流程实战 2026-08-29/30"]
related: ["RUNBOOK-ANYONE.md", "ONBOARDING-PIPELINE.md", "templates/new-site-customization-checklist.md", "MODULES.md", "writing/WRITING-INDEX.md"]
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
| 5 | **已有 CMS 后台内容** | 仅续建/迁移用：先 `read_lists` 导出，避免重复 create 堆积草稿 | 步骤 3 选站 + 现状 diff |
| 6 | **没有 / 不足** | 按 §1.2 必问清单问；AI 先执行素材推进策略（先自动提炼 → 不够给方案 → 仅剩不可推断的才问用户） | 缺口清单（标注 demo/待用户提供） |

### 1.2 资料不足时的必问清单（≤5 问，缺项=阻塞）

> 模板：[templates/client-input-checklist.md](templates/client-input-checklist.md) 第一节。以下 5 问收齐才能开工；缺问 3 = 全部阻塞。

| 问 | 要什么 | 为什么阻塞 |
|---|---|---|
| Q1 | **公司/品牌名 + 目标市场语言**（含标语、品牌一句介绍） | 站名/slug/导航/SEO title 前缀全部依赖 |
| Q2 | **真实联系方式**：邮箱（**必须真实可收件**）+ 电话 + WhatsApp + 地址/营业时间 | 表单链路与联系页、全站 globals 浮钮 |
| Q3 | **产品/公司资料文件**（PDF/DOCX/网页/口述） | 唯一事实源；没有它只能全 demo，不可发布 |
| Q4 | **首批内容范围确认**：产品 ≥3（名+一句话+规格+图）、文章主题 ≥4（或接受 demo 占位） | 数量门：products<3 或 posts<4 时 validate 直接 INVALID |
| Q5 | **写作素材 + 图片授权**：客户原话/询盘片段 ≥3 条、每文章 2-3 个真实数据、图片自有或同意代找 CC | 缺 Q5 文章只能写通用介绍且必须标注 demo |

动工前用户确认点（client-input-checklist 第四节）：站点名/slug 偏好、demo 值是否可接受、图片授权方式、首批内容范围。

---

## §2 一条龙执行链（步骤 0–12，共 13 步）

> 每步四段式：**输入 → 动作（具体命令/方法名）→ 验收判据 → 产物落盘**，末尾附「坑」（引自 RUNBOOK §2 实测事实表）。

### 步骤 0 — 索引 find/verify（开工硬 gate，ISS-065）

- **输入**：客户资料已到达（拿到任务关键词）+ **凭据就绪**：用户登录 workspace.laicms.com 后取 Cookie `payload-token` → **`export WS_TOKEN=<token>`（跨平台推荐）**；或 token 文件（chmod 600）传路径。无 token = 全链路不可用。
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
  ```
- **验收判据**：`verify` 输出 `VERIFY PASS`；`find` 相关坑已读；action id 与 `allincms_api.py` 常量一致。
- **产物**：`70_evidence/00-preflight.txt`（verify/find/scan 输出快照）。
- **坑**：跳过 find 直接动手 = 重复已回填的坑（ISS-001/002/003/018/024/059 均为重复踩坑）；action id 用错**静默返回 `{}`**，不报错。

### 步骤 1 — 资料 → brief.json

- **输入**：§1.1 各类客户资料 + §1.2 问答结果。
- **动作**：
  1. 解析 → Markdown（保留来源定位）→ 事实抽取（confirmed/inferred/missing）；
  2. 对照 [templates/site-content-checklist.md](templates/site-content-checklist.md) 的 A–I 九节逐项映射；
  3. 按 [templates/brief-schema.json](templates/brief-schema.json) 填 `site/brand/contact/categories_*/tags/products/posts/story/nav`。
- **验收判据**：`python3 site_pipeline.py validate 70_evidence/brief.json` → `VALID`（products<3 或 posts<4 → INVALID，回 §1.2 Q4）。
- **产物**：`70_evidence/brief.json` + `70_evidence/source-extraction.md`（来源定位 + 图片 author/license + confirmed/inferred/missing 标注）。
- **坑**：所有文案必须来自资料，AI 合成必须显式标 `synthetic demo`（不冒充案例/销量/认证）；brief 里 media 先写 ref 名，URL 在步骤 5 上传后回填。

### 步骤 2 — validate + COP（数量基线）

- **输入**：`brief.json`。
- **动作**：
  ```bash
  python3 site_pipeline.py validate 70_evidence/brief.json
  python3 site_pipeline.py generate 70_evidence/brief.json 70_evidence/generated/   # 生成 payload 集（可选加速）
  ```
  写 COP（内容计划）：**每站数量基线**（产品 ≥3、文章 ≥4，[CONTENT-MINIMUM.md](templates/CONTENT-MINIMUM.md)）+ 文章主题 + 分类/标签清单 + faq_answers/cta/units 值。
- **验收判据**：`VALID`；COP 明确**每类实建数**（这个数 = 步骤 12 audit `count` 基线）。
- **产物**：`70_evidence/<slug>-cop.md`。
- **坑**：audit/gate/contact 不带 `--config` 会沿用 **Demo 基线误判新站**（ISS-063）——COP 就是该 config 的全部取值来源。

### 步骤 3 — Plan A：create_site（只建站，不填内容）

- **输入**：`brief.site`（name/description）。
- **动作**：
  ```python
  api.create_site(name, description)        # 只建站；绝不与内容填充合一步
  site = api.read_sites()["sites"][0]       # 校验唯一新站；slug 从响应或 read_sites 取
  ```
  站点已存在（续建/迁移）→ `read_sites` 选目标站，跳过 create。
- **验收判据**：拿到**真实** `site_id`/`site_key`；`read_sites` 可见唯一新站。
- **产物**：`70_evidence/<slug>-plan-a-readback.json`（site_id/site_key/账号 owner 读回证据）。
- **坑**：账号非首站时 createSite 只给 blank 主题（0 页）——不要指望自动 7 页，步骤 9 必须手工 `create_theme`。

### 步骤 4 — 填「新站改造清单」（customization checklist）

- **输入**：`brief.json` + COP + [templates/new-site-customization-checklist.md](templates/new-site-customization-checklist.md)。
- **动作**：拿客户资料把 checklist **每个字段填成该客户的值** → 落成 `<slug>-customization.md`；步骤 5–9 严格按它执行。
- **验收判据**：checklist 每个字段都有「该客户的值」或显式 `待用户提供/demo` 标记；与 site-content-checklist.md A–I 九节无缺口。
- **产物**：`70_evidence/<slug>-customization.md`。
- **坑**：服务端回填默认——**未显式字段会被模板默认值填充**（模板文案/假链接），checklist 上「可显示字段全部显式传」必须逐条落实；header 导航 children 必须递归 dict。
- **引用与回落**：与 checklist 的接口约定见 §5。该文件已存在（/166 字段，2026-08-30）；若缺失则按 MODULES.md 37 块字段全集 + §5 接口节执行，不阻塞主链。

### 步骤 5 — 媒体上传 + alt 回写

- **输入**：素材文件（客户图/CC 图）+ customization 的 media 节。
- **动作**：
  ```python
  r  = api.upload_media(slug, site_id, file_path, title, alt, caption)   # multipart _1_files
  api.update_media(slug, media_id, site_id, title, alt, caption)         # 上传后立即回写
  api.read_media_library(slug)                                           # 核对
  ```
- **验收判据**：`read_media_library` 核对 10 字段（name/alt/url/path/size/mimeType…）；**URL 带扩展名**；license 记入证据。
- **产物**：`70_evidence/media-manifest.md`（文件名 → URL/alt/license）；URL 回填 brief.json 的 media ref。
- **坑**：URL 不带扩展名 → 运行时 404；同页不重复用同一张图（分类卡/hero 错开）。

### 步骤 6 — 分类 / 标签

- **输入**：customization 的 taxonomy 节。
- **动作**：
  ```python
  api.create_category2(slug, site_id, name, slug, content_type='products'|'posts', description='', order=0, cover=None)  # cover 显式 None
  api.create_tag(slug, site_id, name, slug, description='')
  ```
- **验收判据**：产品分类与文章分类**分开建**；cover=None 未 500；记录全部 id（后续 payload 用 **id 字符串数组**）。
- **产物**：`70_evidence/taxonomy-ids.json`（name → id 映射）。
- **坑**：cover 缺省报 validation error；payload 传 id 数组（读回是对象数组）；POST 报 transaction number mismatch → 浏览器打开对应 tab 拿新 router tree 再试。

### 步骤 7 — 产品 create/publish（每个产品一遍）

- **输入**：customization products 节 + `taxonomy-ids.json` + 媒体 URL。
- **动作**（每产品）：
  ```python
  p  = 全字段 payload   # 骨架 = templates/product-payload-example.json；media 扁平 {name,alt,type,source,path/url}；
                        # categories = 产品分类 id 数组（不可用文章分类）；specifications=[{key,value}]
  r1 = api.create_product(slug, site_id, p)        # 空壳 id
  r2 = api.publish_product(slug, site_id, pid, p)  # 同 payload 带正确 slug 再发，一次成功
  ```
- **验收判据**：`api.read_lists(slug,'products')` 与 COP 逐条 diff（数量/名称/slug/规格）；状态 published。
- **产物**：`70_evidence/products/<slug>.json`（每产品最终 payload 存证）。
- **坑**：create 后 draft slug 会变时间戳，publish 时 payload 必须带正确 slug；同 slug 重跑会堆积 Untitled 草稿（ISS-059）→ 先 `read_lists` 查 slug。

### 步骤 8 — 文章 k3 写 + flash 审 + create/publish

- **输入**：写作前置素材（client-input-checklist 第六节：客户原话 ≥3 / 真实数据 / 案例 / 图 / 客群描述）+ COP 文章主题 + customization posts 节。
- **动作**（五步链，入口 [writing/WRITING-INDEX.md](writing/WRITING-INDEX.md)）：
  ```bash
  python3 writing/writing-module.py outline 70_evidence/brief.json     # 六段式骨架（可选）
  # ① 主 AI 从源 PDF 提炼 facts（只用源内事实；禁止编价格/MOQ/认证/客户案例）
  # ② 派【写作子 agent，模型=k3】：BRIEF.md（facts+主题+Slate 规范）+ article-writing-logic.md + PROGRESSION.md
  #    产出 70_evidence/posts/<slug>.json（字段全集 = templates/post-payload-example.json）
  # ③ 机器检查：python3 writing/writing-module.py check 70_evidence/posts/<slug>.json
  # ④ 派【评审子 agent，模型=flash】：templates/ghostwriter-review-prompt.md（5 维评分+最弱 3 处+钩子）→ READY / NEEDS_REWRITE
  # ⑤ NEEDS_REWRITE → 回改表达（不动事实）重审；READY →：
  api.create_post(...)  →  api.publish_post(...)   # 先 read_lists 查 slug 防重（ISS-059）
  ```
- **验收判据**：`check` PASS + 评审 READY + 发布后抓取验证 **SSR**（FAQ 实质短语出现在公网 HTML）。
- **产物**：`70_evidence/posts/<slug>.json` + `70_evidence/posts/<slug>-review.md`。
- **坑**：正文原生 Slate 类型 = `p|h2|h3|blockquote`（`heading`/`paragraph` 旧词法已禁用，ISS-060，用 writing-module.py 生成器保证）；正文内联 link 节点平铺渲染**无 `<a>`**——文章 CTA 放步骤 9 的页面级块；文章挂**文章分类** id，勿用产品分类 id。

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
- **坑**：**createTheme(default) 会重新种入 3 demo 产品 + 3 demo 文章**（站点级，ISS-071，步骤 11 清）；空字符串字段会被 zod 打回默认值（如 WhatsApp `wa.me/+44-7911-123456`）→ 删 demo 按钮=**移除元素**（children+elements 同删），不是置空（ISS-068）；主题 id/页面 id 会变，一律 `read_themes/read_pages/read_page_document` 现取。

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
- **产物**：`70_evidence/routes-final.json`（routePath → pageId 快照）。
- **坑**：`setThemeActive` 是**唯一会清空 homePageId** 的操作 → set_home_page 必须最后（routes/activate 次序互换无害，实测路由不破坏绑定）；**任何未来重新激活主题后都要重跑 set_home_page**；其余路径（`/{slug}/themes`）返回 200 但**静默无效**。

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
  #   按 COP 填：pages（全部产品/文章 slug）、count（实建数）、faq_answers（文章必 SSR 的实质短语）、cta（真链接+source）、units
  python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json --out 70_evidence/audit-report.json
  python3 site_pipeline.py gate <slug> --config 70_evidence/<slug>-audit-config.json
  python3 site_pipeline.py contact <slug> --config 70_evidence/<slug>-audit-config.json --real "<真实电话|邮箱|地址>"
  # DELIVERY：templates/delivery-manifest.md → 70_evidence/DELIVERY-<slug>-<date>.md（链接表每行核验 200 + 已知事项照抄 RUNBOOK §9）
  # 收尾：70_evidence/HANDOFF.md + 新坑回填 issues.tsv（fixed/boundary/pending）+ registry_tools.py verify + gen
  ```
- **验收判据**：audit 13 项站内检查全 PASS（范围以 site_pipeline.py 为真源）；gate PASS；contact PASS；DELIVERY 链接表**每行核验列非空且为 200**。
- **产物**：`<slug>-audit-config.json`、`audit-report.json`、`DELIVERY-<slug>-<date>.md`、`HANDOFF.md`（详见 §4）。
- **坑**：没有 `--config` 的 audit 会用 Demo 基线误判新站（ISS-063）；公网 CDN 缓存 publish 后 5–10s 生效，验收以列表页数据源 + counter 为准。

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
| `products/<slug>.json` ×N | 7 | 每产品最终 publish payload |
| `posts/<slug>.json` + `<slug>-review.md` ×N | 8 | k3 成稿 + flash 评审记录 |
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
