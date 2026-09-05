---
title: "RUNBOOK-ANYONE.md —— 任何人零上下文建站手册"
type: "runbook"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-09-05"
sources: ["Example 全流程实战 2026-08-29/30（7 产品+3 文章+10 媒体+7 页主题）", "ONBOARDING-PIPELINE.md", "OUTSIDER-REVIEW.md §3", "issues.tsv ISS-001..133", "2026-09-04 双机实战（macOS+Windows 10 field build）", "2026-09-05 跨账号实证（Apply Theme UI 崩溃对照 + 读侧解析陷阱 + SEO 边界清单）"]
related: ["ONBOARDING-PIPELINE.md", "writing/WRITING-INDEX.md", "MODULES.md"]
description: AllinCMS 建站工具包文档（RUNBOOK-ANYONE.md）
visibility: "public"
redaction_status: "safe-to-publish"
---

# RUNBOOK：任何人拿到 interface-kit 即可建一个完整 AllinCMS 站

> 拿到客户资料后先读 [NEW-SITE-ONEPASS.md](NEW-SITE-ONEPASS.md)（13 步一条龙：资料→brief→COP→内容→主题→审计→交付）；本文档是流程细节与事实/回落库。

> 本手册是**零上下文总入口**。不假设你见过 Demo/Example/保温杯任何先例。
>
> **平台前端审计项（lang / canonical / JSON-LD / img-attrs）——收窄令（用户指令 2026-09-01"可"，取代 2026-08-30 永久禁令）**：这 4 项**允许检查并登记**（结果记 BOUNDARY/验收清单项，出证据），但**平台修复前不阻断交付**；它们是平台层行为，不属站内修复职责。检查判据与登记口径以 [templates/site-acceptance-v2.md](templates/site-acceptance-v2.md) 为准；对应平台缺陷走 BOUNDARY 三要件（OQ-TOOL-0004 渠道）。不得写成 FAIL 拦截交付，也不得重新当作站内待修项。
> 铁律：**先读 §0（index-first），踩坑先 `find`，新坑必须回填**。任何"我猜平台支持"的字段先查 MODULES.md 与 `templates/*.json` 实测样例。

## §0 前置（一次性，5 分钟）

```bash
mkdir -p <任务目录>/70_evidence          # 工作目录 = 该站点任务目录（所有产出/证据/审计配置都放这里，路径在文档里一律写全）
cd <interface-kit 目录>            # 内含 allincms_api.py / site_pipeline.py / allincms_blocks.py / templates / writing / index
python3 index/registry_tools.py verify     # 索引完整 -> PASS
python3 index/registry_tools.py find <你的任务关键词>   # 必做：上传/分类/主题/文章/审计 等
WS_TOKEN=<token> python3 scan/scan-actions.py - /<site_key>/themes   # 部署更新后重扫 action id（42 位 hex）；新 id 回填 allincms_api.py 常量（也支持传 token 文件路径）
python3 ../../scripts/interface-kit-pipeline.py check   # 真源管线 stale/drift 守卫（id-0073；WARN/FAIL 先处理）
```

- 凭据：`payload-token` JWT **优先 `export WS_TOKEN=<token>` 环境变量（跨平台推荐）**；或写 token 文件（chmod 600）后传路径。获取方法（三种，专题真源 [TOKEN-AUTH.md](../../ADAPTERS/cms/allincms/docs/TOKEN-AUTH.md)；③ 为方向指引未实测）：
  1. **纯 API（ISS-083，推荐）**：`api = AllinCMS(email=..., password=...)`——login() 会 POST sign-in 并从响应 Set-Cookie 提取 token**（成功+失败路径均实测 2026-08-30：email/password → Set-Cookie 提取 token → 读写全权限验证通过）**。
  2. **浏览器 Cookie（兜底，已验证）**：用户登录 `workspace.laicms.com` → DevTools → Cookies → 复制 `payload-token` → `export WS_TOKEN=<token>`。
  3. **浏览器配置文件提取（方向指引，未实测）**：AI 从用户已登录浏览器的 Cookie 存储自动提取；详见 TOKEN-AUTH.md 方式三，优先 1/2。
  **拿 token 是唯一可能碰浏览器的环节；拿到后全程纯接口**（操作矩阵 10/10 实测：读 8 + 幂等写 2 + 媒体 multipart + 公开站表单 submit，零浏览器）。
  **最快连通验证**：README.md 安装节第 4 条的 5 分钟冒烟一行命令（email+password 环境变量直连，打印站点列表即全通）。
- 目标：工作台 `workspace.laicms.com`，公开站 `https://<site_key>.web.allincms.com`。
- 路径约定：本文内 runtime 相关路径相对于**运行时根 `$RUNTIME_ROOT`**（独立 runtime 目录；母库内经 `customer-runtime/` 软链可达）；`templates/...`、`writing/...`、`index/...` 相对于 interface-kit 目录。
- 零第三方依赖：Python3 stdlib 即可；全文 API 直连，**不要开浏览器自动化**（除登录拿 token）。

## §1 建站总流程（10 步）

```text
0 index-first + verify
1 读源材料 -> 提炼 brief.json（site/brand/contact/products/posts/nav/story）
2 validate brief -> 定 COP（内容计划）：每站数量基线 + 文章主题 + 分类/标签
3 Plan A：create_site（拿到 site_id/site_key）——站点已存在则 read_sites 选目标
4 媒体：upload_media × N + update_media 回写 title/alt/caption
5 分类/标签：create_category2（cover 显式 null）/ create_tag
6 产品：最终 payload + 独立审查 READY/digest → mutate_reviewed_product（见 product prompt/record/gate）
7 文章：k3 写 → distinct reviewer → strict record + fresh capability；新文章先 ISS-111 资格五步→create draft→mutate_reviewed_post，已有文章直接 exact-ID update
8 主题页：create_theme(default) -> 改 7 页 doc + globals -> 每页 save+publish -> set_theme_active -> apply_theme_routes
9 每站审计配置（templates/site-audit-config.template.json 复制改名）-> audit/gate/contact 三门
10 交付清单 DELIVERY-<slug>-<date>.md + HANDOFF.md + 回填 issues.tsv
```

> **步骤号映射（本文 ↔ ONEPASS 13 步）**：本文 6=ONEPASS 步骤 7（产品）、7=8（文章）、8=9/10/11（主题页/激活路由/demo 清理）、9=12（审计交付）；其余同号。跨文档引用步骤号时写明出处（如 "ONEPASS 步骤 10"），防歧义。

## §2 关键事实（已实测，别重踩）

| 事实 | 结论 | 出处 |
|---|---|---|
| 账号非首站时 createSite 只给 blank 主题（0 页）；手工 `create_theme(preset='default')` 总是生成 7 页 | 必须手工 create_theme | allincms_api.create_theme docstring（与 createSite 行为区分） |
| **根路径 `/` 修复=set_home_page**：`api.set_home_page(slug, site_id, theme_id, home_page_id)`（action=setHomePageAction，URL 必须是 `/{slug}/themes/{themeId}`）。**顺序：先 setThemeActive 再 set_home_page**（激活会清 homePageId）。其余路径（/{slug}/themes）返回 200 但静默无效 | ✅ **可修（2026-08-30 实测上线）** | allincms_api.set_home_page + 任务证据 `70_evidence/ROOT-PATH-ISSUE.md` 终局节 |
| 正文内联 link 节点平铺渲染无 `<a>` | 文章 CTA 用**页面级块**（material-story-split actionTarget）做真链接 | MODULES.md link 行 |
| 空字符串字段会被 zod 打回默认值（如 WhatsApp url 默认 `wa.me/+44-7911-123456`） | 删 demo 按钮=**移除元素**（children+elements 同删），不是置空 | 2026-08-30 实测（ISS-068） |
| 旧流程 article create 空壳草稿后 publish；重复 create 曾堆积 Untitled Post | article create/update 均 canonical：create 先当前部署资格五步+唯一差集，拿 exact ID 后 strict review/capability→mutate_reviewed_post；不得重复 create | ISS-059/102 |
| **createTheme(default) 会重新种入 3 demo 产品+3 demo 文章+6 demo 分类+7 demo 标签**（站点级，新记录 id 时间戳=创建时刻；taxonomy 同样种入且 0 引用也会公开出现在筛选下拉） | 每次重建主题后重跑全链清理（delete-demo-content.py）；audit count 项自动暴露 | ISS-071/074 |
| 正文原生 Slate 类型 = `p|h2|h3|blockquote`（服务器存储形态；'heading'/'paragraph' 旧词法禁用） | 格式见 templates/post-payload-example.json；生成器 writing-module.py block/skeleton | ISS-060 |
| 主题 id/页面 id 会变 | 一律 read_themes/read_pages/read_page_document 现取，勿猜 | allincms_api.read_themes |
| **跨站: 部分新站产品 media 只接受 `source:"url"`**（oss+path 被静默拒，产品保持 Untitled）；且 `specifications.value` ≤200 字符 | 产品 media 用 `{source:url, url:<CDN url>}`；specs 短 value；先 scan 有无 createProductAction（无则走 update/upsert） | ISS-105（2026-09-02 新建站实测） |
| **globals 改动读原值改单字段回传**（自建 globals 结构会被服务端回退旧值）；导航 CTA 弹窗 = `header-dropdown.ctaTarget={type:action,anchorId:contact-form-dialog}` | read_page_document 取原 globals → 只改目标字段 → save_home(save)→readback→save_home(publish)；站点级可见改动用后台设计器站点级 Publish 刷 CDN | ISS-106（2026-09-02 实测） |
| **网格模块 columnCount 必须等于条目数**：columnCount=N 固定 N 列，条目不足渲染空白卡/半幅空白（3列填2=空白第三卡；4列填2=右半空白） | 提交前校验 `columnCount == len(items/proofRows/...)`，改列数或补条目二选一；hero 级大标题 72px 固定，连字符首词断孤儿行（"Wall-"），标题避免连字符词开头、≤42 字符 | ISS-107（2026-09-02 实测，MODULES.md 网格规则块） |
| **截图报障先排"导航穿透"**：吸顶导航 bg-background/95 半透明，滚动截图必有 5% 内容透出的鬼影；视觉模型会误读字符（6800→9600）和乱排区块序 | 定性前用浏览器 evaluate 量 section getBoundingClientRect + computed gridTemplateColumns，grep 公开 HTML 核对内容；模板固有行为（content-between 空隙/line-clamp 截断/奇数末行空位）登记不硬改 | 2026-09-02 三截图诊断实测（ISS-107） |
| **产品改名/字段级 update 全自动可行**：payload=GET `/{slug}/products/{id}/update` 的 defaultValues 归一化后只改目标字段；配 per-product 审查记录 + 新鲜 capability（≤30min，evidence digest 绑定）走 mutate_reviewed_product(target_id) | 实测 14/14 零 reconcile、全量 canonical readback 匹配；readback 证据键名是 `business_exact_match`（不是 exact_match） | 2026-09-02 批量改名实测（rename-results.json） |
| **激活/生效状态键名（ISS-108，勿猜勿用 isActive）**：theme 行 `active`(bool，**`isActive` 不存在，恒 None**)、`homePageId`、`homePagePublished`(bool)；page 行 `enabled`(bool)/`isHome`/`_status`；route 行 `status=='bound'`；product 行 `_status=='published'`（create-only 草稿不可见=ISS-105 另一面） | 判断是否生效只准用实测键名；**theme.homePagePublished 可免 curl 直接判根路径发布状态**；`active:True` 的主题仍要核对 homePageId 非空 | 2026-09-02 read_themes/read_pages/read_lists 实测键名 |
| **create_site 的 description ≤200 字符**（P1，超长被 zod 拒） | 站点描述写一句定位语，长文案留给 about 页/SEO description | 2026-09-04 双机实战（macOS+Windows 10 field build） |
| **Git Bash（MSYS）会把 `-` 开头参数转成路径**（E4/ISS-120）：`python x.py -c ...`、带 `-xxx` 的参数被展开成 `C:/Program Files/Git/...` | 命令前加 `MSYS_NO_PATHCONV=1`，或改用 cmd/PowerShell 跑同一条命令 | 2026-09-04 a Windows 10 field build |
| **capability 每批重建（P9/G2，ISS-117/125）**：live capability ≤30 分钟过期且字段双层严格相等，手拼模板易错 | 每批产品 mutation 前调 `api.refresh_product_capability(site_slug, site_id, task_root, client_id, task_id)`（内部观察 action id→写 70_evidence/→返回自检过的 context；create/update 操作集分开刷） | 2026-09-04 双机实战 |
| **CDN 滞后先分清后端/边缘（V8）**：公开站没变 ≠ 写失败——先 readback 后端（read_page_document/read_lists）：后端已新=边缘 CDN 缓存（等待/重取即可），后端也旧=写入没落地（回 §2.1 诊断树） | 验收顺序固定：后端 readback → 边缘 curl/抓取；不要只盯公网连续硬刷 | 2026-09-04 双机实战 |
| **registry capability_routes 声明 blocked ≠ 代理层实际不可用（ISS-129）**：某实战案例 delete_site 被标 blocked，直连实测成功 | 重要动作以真实请求小步验证为准（先读对账再执行）；破坏性动作无论声明如何都须用户明确授权 | 2026-09-04 双机实战（delete_site 实测成功） |
| **工作台 Apply Theme UI 崩溃 ≠ 服务端故障（ISS-130）**：点 Apply Theme 报 NotFoundError: insertBefore（React DOM 渲染崩溃），Theme 无法 Active、Routes Unbound，易被误判"平台故障等修复" | 主题绑定固定走 API 三步 `apply_theme_routes` → `set_theme_active` → `set_home_page`（§3 顺序）；同部署另一新站一次成功（active=True/homePagePublished/全路由 200）——UI 层崩溃不影响 Server Action 通道 | 2026-09-05 跨账号实证（某 coffee 实战站） |
| **SEO 可控/边界分层（ISS-133）**：可控★=description/excerpt（meta description 实测一致）/alt/slug/发布态；平台⛔=title 后缀（站点名+品牌句平台拼接，改产品名不可达≤60）/html lang 平台默认/canonical 全站缺失/JSON-LD 全站 0/分类查询页 title、desc 与列表页重复/首页多 H1 | SEO 诊断输出分"可控★/平台⛔/误报⚠"三层并给 ACTIONS 优先列；平台⛔项登记 BOUNDARY 照抄已知事项，不当站内待修项 | 2026-09-05 某 SEO 实战站实测 |

### §2.1 「改动不生效」诊断树（未激活/未发布/未启用，按序查）

```text
改了后台/接口，公开站没变？按序查（全部用上表实测键名）：
1) theme.active==True？            → 否：set_theme_active（激活后必须重跑 set_home_page！ISS-070）
2) theme.homePageId 指向预期首页？  → 否：set_home_page
3) theme.homePagePublished==True？ → 否：save_home(intent='publish') 后重查
4) page.enabled==True 且 _status 正常？ → 否：set_page_enabled(true)
5) route.status=='bound'？          → 否：apply_theme_routes
6) read_page_document readback 与预期一致？ → 否：save_home(intent='save')→readback→(intent='publish')（ISS-106 只改单字段）
7) 页面 publish 后公网仍未变且改动在 header/footer/站点级 → 后台主题设计器站点级 Publish 刷 CDN（ISS-106）
8) 产品在公开列表缺失 → read_lists 行 _status=='published'？否=create-only 草稿，走 update/publish（ISS-105）
9) 以上全对仍旧内容 → CDN 缓存：sleep 后重取 curl，勿连续硬刷
audit 机器闸目前不覆盖 1)-8) 的状态字段——这九步必须人工/脚本各跑一遍（扩展项已列计划）。
```

## §3 主题页操作（第 8 步展开）

```python
import sys; sys.path.insert(0, '<interface-kit 绝对路径>')
from allincms_api import AllinCMS
import os; api = AllinCMS(token=os.environ["WS_TOKEN"])  # export WS_TOKEN=<token>（或 token 文件路径）
# 建 default 主题（preset='default' 总是生成 7 页：/home /about-us /contact-us /posts /posts/{post} /products /products/{product}）
api.create_theme(slug, site_id, 'My Default', 'Default theme', preset='default')
# theme_id 来源：create_theme 后按 name 取最新（或取 active 主题）
# ⚠️ 激活键名是 t['active']（bool），isActive 不存在（恒 None，ISS-108）；active 主题仍须核对 homePageId 非空
themes = api.read_themes(slug)['themes']
theme_id = [t['id'] for t in themes if t['name'] == 'My Default'][-1]
act = [t for t in themes if t.get('active')]
assert act and act[0]['homePageId'], 'active 主题缺 homePageId → 根路径是 Runtime 壳，跑 §2.1 诊断树'
# 读页面与文档（read_page_document 返回 {status, initialPayload:{page:{document,globals,themeConfig}}）
r = api.read_pages(slug, theme_id)          # {'pages':[...], 'routes':[...]}
page_id = r['pages'][0]['id']               # 示例取第一页；按需换 path=='/home' 等
c = api.read_page_document(slug, theme_id, page_id)
page = c['initialPayload']['page']
doc, globals_doc, tc = page['document'], page['globals'], page['themeConfig']
# 改 doc/globals 后用 save_home 逐页 save+publish；intent 两种都要发
api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='save')
api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='publish')
# 绑路由 → 激活 → 设首页（set_home_page 必须最后：setThemeActive 是唯一会清空 homePageId 的操作——
# routes/activate 次序互换无害（实测路由不破坏绑定）；任何未来重新激活主题后都要重跑 set_home_page）
api.apply_theme_routes(slug, site_id, theme_id, [{'routePath': p['path'], 'pageId': p['id']} for p in r['pages']])
api.set_theme_active(slug, site_id, theme_id)
home_page_id = [p['id'] for p in r['pages'] if p['path'] == '/home'][0]
api.set_home_page(slug, site_id, theme_id, home_page_id)   # 根路径 / 开始渲染首页（对抗矩阵见 ISS-070 审查记录）
```

- 页面文档结构：`{"root":"page-root","elements":{...}}`；块类型白名单与 props 见 `templates/home-page-example.json`、allincms_blocks.py 与 MODULES.md（37 块注册表全集在 MODULES.md 开头）。
- globals（header/footer/contact dialog/social button）**按页存储**：改 globals 后用同一份 globals_doc 对**全部 7 页**逐页 save+publish（Example 实测可靠做法；只 commit 一页不可保证全站一致）。
- **globals 改动只改单字段回传（ISS-106）**：`read_page_document` 取 `page['globals']` → 改目标字段（如 `globals_doc['elements']['header-dropdown-1']['props']['ctaTarget']`、`footer-columns-1.props.brand`）→ 其余原样 `save_home(intent=save)` → `readback` 确认 → `save_home(intent=publish)`。**不要自建整个 globals 结构**（缺 children/anchorId 会被服务端回退用存储值，改动不生效）。**导航 CTA 弹窗** = `header-dropdown.props.ctaTarget = {type:"action", anchorId:"contact-form-dialog"}`（公网 `#contact-form-dialog`）；`{type:"custom",href:"/contact-us"}` 是跳页非弹窗。站点级/头部/品牌/菜单可见改动，若页面级 publish 后公网未刷新，用后台主题设计器顶部的**站点级 Publish**（而非仅 save_home）触发 CDN。
- **文章页 CTA 真链接（仅已有 exact-ID 文章 update 分支）**：post-detail 页 `page-root.children` 追加 `cta-1` 元素（type `material-story-split`，actionTarget `{"type":"custom","href":"/contact-us?source=<site>-article"}`），同时替换 related-1 demo 文案。干净账号先跑 ISS-111 资格五步；通过则 create+reviewed update 并保留 Posts 导航/news，失败且留有部署证据时才移除空文章入口。参考脚本仅作历史结构证据：`<task_dir>/70_evidence/scripts-*/fix-post-cta.py`。

## §4 产品（第 6 步展开）

> **跨站差异（ISS-105，2026-09-02 新建站实测，先看再动）**：不是所有站都接受 `source:"oss"`。部分新建站产品 upsert 若 media=oss+path 会**静默拒绝整个 payload**（产品保持 Untitled）。**写产品前先 scan 该站有无 `createProductAction`**（新站常只有 `upsertProductAction`，无 create → 必须走 update/upsert，即 `mutate_reviewed_product(target_id=已有 draft id)`，先 create 得 draft id 再 update 填字段）。
- payload 见 `templates/product-payload-example.json`，但 **media 用 `{name,alt,type:'image',source:'url',url:<CDN url>}`**（url 从 `read_media_library` 读回拿，如 `https://assets.laicms.com/<siteKey>/<file>.jpg`），不要 oss+path；categories/tags 传 id 字符串数组；specifications `[{key,value}]` 且 **每个 value ≤200 字符**（`valueMax200`），长型号/参数清单放 `content` 正文（Slate p/h2/h3）。
- 流程：`mutate_reviewed_product` 是唯一公开入口；review context PASS 后内部完成 create_draft→publish_update（create）或 publish_update（update）。
- publish 后检查 response 的 `validationErrors` 是否为空（非空即被拒，回退 Untitled）；完成用 `read_lists(slug,'products')` 与 COP 逐条 diff，并 `read_product` 确认 content 非空。

## §5 分类/标签（第 5 步展开）

- `create_category2(slug, site_id, name, slug, content_type='products'|'posts', description='', order=0, cover=None)` —— cover 显式传 None，否则 500。
- `create_tag(slug, site_id, name, slug, description='')`。
- 坑：直接 POST create 时若报 transaction number mismatch → 先在浏览器打开对应 tab 拿新 router tree（ISS 记录）。

## §6 媒体（第 4 步展开）

- `upload_media(slug, site_id, file_path, title, alt, caption)`：multipart `_1_files` 传输（interface-kit 已封装），返回后立即 `update_media` 回写 title/alt/caption。
- 上传完 `read_media_library` 核对 10 字段（name/alt/url/path/size/mimeType）。

## §7 文章写作（第 7 步：子 agent k3 写）

```text
1) 主 AI 从源 PDF 提炼 facts（只允许用源内事实：频率/结构/参数/保固；禁止编价格/MOQ/认证/客户案例）
2) 派【写作子 agent，模型=k3】：给 BRIEF.md（facts+主题+Slate 格式规范）+ templates/article-writing-logic.md
   产出 <slug>.json：字段全集见 templates/post-payload-example.json（title/slug/excerpt/order/coverImage/content/categories/tags）
   content 原生 Slate 类型 = p|h2|h3|blockquote（服务器存的就是这些；'heading'/'paragraph' 是旧词法已禁用，用 writing-module.py 生成器保证）
3) 机器检查：python3 writing/writing-module.py check <slug>.json
4) 派【评审子 agent，模型=GLM flash（flash）】：复制 templates/ghostwriter-review-prompt.md 填文派空白子 agent
   -> 5 维评分+最弱3处+钩子检查+READY/NEEDS_REWRITE
5) NEEDS_REWRITE -> 回改表达（不动事实）重审；READY -> 下一步
6) 先 read_lists resolve exact existing ID → 独立 review READY + fresh capability → mutate_reviewed_post update → 上线后 SSR；不存在则先跑 ISS-111 资格五步后 create draft+reviewed update；资格失败才 BLOCK
```

模型命名以宿主实际可用模型 id 为准：写作=K3 系（长文质量），评审=flash 系（快+挑剔）。

## §8 每站审计配置（第 9 步，必做）

```bash
cp templates/site-audit-config.template.json 70_evidence/<slug>-audit-config.json
# 按该站 COP 填：pages（全部产品 slug；仅 existing reviewed-update 文章才加文章 slug）、count（远程实建数）、faq_answers（仅有远程文章时加文章 SSR 断言）、cta（真链接+source）
python3 site_pipeline.py audit <slug> --config <cfg> --out 70_evidence/audit-report.json
python3 site_pipeline.py gate <slug> --config <cfg>
python3 site_pipeline.py contact <slug> --config <cfg> --real "<真实电话|邮箱|地址>"
```

- 13 项机检：count/200/空态/模板词/demo 联系方式/FAQ SSR/真 CTA/单位/绝对化/Markdown/h2 语义/根路径首页(root-home)/表单渲染(form-render)。
- 平台 BLOCK（已永久移除，用户指令禁止涉及）；**根路径 / 是可修项**（set_home_page），audit root-home 项判 FAIL 说明首页没设好。
- **createTheme(default) 会重种 3+3 demo（ISS-071/074）**：审计前先跑 `python3 delete-demo-content.py <slug> [--dry-run]`（全链：产品+文章+分类+标签；带引用护栏）。
- **⚠️ 删除授权门（TERRA）**：一切删除类操作（delete_site/product/post/theme/category/tag/delete-demo-content.py 非 dry-run）**执行前必须取得用户/客户明确授权**；先 --dry-run 列清单确认，再授权执行。
- verdict FAIL 且问题非 BLOCK → 先修再交付；**没有 --config 的 audit 会用 Demo 基线误判新站（ISS-063）**。

### §8.1 执行路径决策树（按操作类型选执行面；两机实战 2026-09-04，ISS-127）

```text
要做的操作是哪类？按序对号入座，不要跨面降级：

1) article.create（远程新建文章）
   → 唯一执行面 = canonical JS Controller（content-run-controller.mjs + article:create
     handler + 三真实 provider：beforePostIds/readback/editorReopen）。
   → 当前 transport 示例仅 macOS+Chrome 可用；Windows 等无 transport 的宿主 =
     BLOCK（三 provider 不可伪造，设计如此）。BLOCK 分支：本地成稿+独立评审+
     review records 照做，不远程创建，DELIVERY 首行记录 article.create=BLOCK。
   → 禁止降级：Python 直发（第二执行面禁令）与伪造 provider 快照都不可。
2) 产品 create/update/publish（interface-kit reviewed 入口）
   → 全可用、跨平台（macOS/Windows/Linux 均纯 HTTP）：strict review record +
     fresh capability → mutate_reviewed_product；capability 用
     refresh_product_capability 每批重建（≤30 分钟窗）。
   → 跨站差异先 scan：无 createProductAction 的新站走 update/upsert 路径（ISS-105）。
3) 删站 / 删 taxonomy（delete_site / delete_category / delete_tag）
   → allincms_api 直连实测可用（ISS-129：registry 标 blocked 不代表不可用，
     以真实请求小步验证为准）。
   → ⚠️ 破坏性/不可逆：先 read_sites/read_lists 对账目标，必须取得用户明确授权。
4) taxonomy 创建（分类/标签）
   → create_taxonomy_safe（对账+transaction 竞态重试，ISS-123）；
     或手动配方：read_lists 对账 → create → 回读 label/value 取 id。
5) 媒体上传
   → upload_media_with_meta（两段式：上传→媒体库对账→SEO 元数据回写，ISS-122）；
     勿信响应 media_urls（历史累积全量）。
```

决策树口径：执行面由操作类型决定，不由"哪台机器在手"决定——机器只决定 article.create
是否 BLOCK（transport 可用性），产品/删除/taxonomy/媒体在任何平台都走 interface-kit 直连。

### §8.2 品牌化 demo 残留扫描词库（ISS-128；新站落库前对 doc JSON 全文 re.search 一次清零）

> 除 MODULES/site_pipeline 的 TEMPLATE_WORDS/DEMO_CONTACTS 词表外，品牌化模板还有一层
> "看起来不像 demo 的 demo"（公司名/栏目名/人名/城市），audit 模板词项抓不全，落库前手工/脚本扫一遍：

| 类别 | 词（小写、子串匹配） | 说明 |
|---|---|---|
| 模板公司名 | northstar、commerce editorial | 品牌/刊名占位（公司名张力处按客户指示替换） |
| 地址/发货地 | ships from san francisco | 模板默认发货地文案 |
| 栏目/导航名 | journal、guides、new arrivals、collections | 文章/指南/上新/合集类栏目默认名 |
| 社媒外链 | instagram、wa.me 4477、wa.me/44 | 默认社媒与 WhatsApp 占位号段 |
| demo 人名 | maya c. | 评价/作者位占位人名 |
| 占位邮箱（2026-09-05 补） | you@example.com | 表单/页脚联系位占位邮箱（demo 联系方式层；命中即替换为用户真实邮箱，勿留在联系位） |
| 商城槽位（ISS-113） | weekender、waxed canvas、from $96、materials and care、new season | hero/carousel 隐藏商城字段回填 |

扫描口径：对每页 document+globals JSON 序列化后逐词 `re.search`（大小写不敏感）；命中即
显式传值（多数可空串）或删元素（zod default 项置空无效，ISS-068）；不可 props 化的模板
编译文案（面包屑/工具栏/表单字段标签）登记边界不硬改。

## §9 已知平台 BLOCK 与回落（交付时照抄到"已知事项"）

| BLOCK | 现象 | 回落 |
|---|---|---|
| 根路径 `/` | 200 但错误壳（Allin CMS Runtime） | **可修**：`set_home_page`（先激活主题再设首页）；审计含 root-home 项防回归 |
| 正文内联链接 | `{"type":"link"}` 平铺无 `<a>` | 用页面级块 actionTarget（§3） |
| 页面 SEO description（meta） | 静态页可经 `api.update_page(..., description=...)` 改（配方=updatePage→等10s→commit publish 带 description→curl 验证）；**动态路由页**（/posts/{post}、/products/{product}）回退模板值=平台限制（ISS-073） | 静态页改、动态页记录；audit 已排除 meta 层判定 |
| 空字段 zod 默认回填 | 置空字符串会被 schema default 顶回 demo 值（如 WhatsApp wa.me/+44-7911-123456） | 删元素（children+elements 同删）而非置空（ISS-068） |
| 表单提交 | **链路已实测可用**（ISS-076/077）：公开站 submitRuntimeFormAction(siteId,{formSlug,values}) → success:true + fieldErrors 服务端校验；**所有表单块 formSlug 必须绑真实 slug**（空=整个 <form> 不渲染——含首页内联块 contact-1 与 7 页 globals 弹窗，逐页核）；工作台暂无提交收件箱 UI（平台待补） | **回落三层**：①联系页/首页展示真实邮箱（sales@…）直达 ②全局弹窗表单（Request a Quote 按钮）同 slug 可用 ③向平台确认提交数据导出/邮件通知；audit form-render 项防回归 |

## §10 交付与回填（第 10 步）

```bash
# 交付清单：templates/delivery-manifest.md -> 70_evidence/DELIVERY-<slug>-<date>.md
#   必须含：公开链接表（每行核验 200）+ 内容清单 + 核验记录（方法+结果）+ 已知事项（§9 照抄）
# HANDOFF.md：状态/事实矩阵/下一步
# 回填：新坑 -> issues.tsv 加行（fixed/boundary/pending）-> registry_tools.py verify
```

## §11 卡住时（顺序执行）

1. `python3 index/registry_tools.py find <关键词>`（历史坑有现象→根因→修复链）
2. `python3 site_pipeline.py audit <slug> --config <cfg>`（拿事实矩阵再判断）
3. **接口不工作/平台更新了？** → 读 [API-DISCOVERY.md](API-DISCOVERY.md)（7 步摸索流程：重扫→反编译→对比→发现→适配→验证）
4. 看 `templates/*.json` 实测 payload 样例 + `MODULES.md` 白名单
5. 新发现 → 修完立即回填 issues.tsv（否则下篇重蹈——这正是"为什么没按规则做"的根因：不 find 不回填）
