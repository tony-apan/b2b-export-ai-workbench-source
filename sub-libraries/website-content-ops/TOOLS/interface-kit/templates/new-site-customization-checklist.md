---
title: "new-site-customization-checklist.md —— 新站点改造清单（模板 → 客户内容逐项替换）"
type: "template"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
sources: ["../RUNBOOK-ANYONE.md", "../MODULES.md", "同目录 templates/ 的 *.json 与 *.md（字段样例真源）", "example-site-full-build-20260829（HANDOFF.md / 70_evidence / 20_work / scripts-20260830 / 公网实测抓取）"]
related: ["../RUNBOOK-ANYONE.md", "../MODULES.md", "site-content-checklist.md", "client-input-checklist.md", "CONTENT-MINIMUM.md", "site-audit-config.template.json", "delivery-manifest.md"]
description: AllinCMS 建站工具包文档（new-site-customization-checklist.md）
visibility: "public"
redaction_status: "safe-to-publish"
template_usage: "manual-copy"
when_to_read: "New site field-by-field customization when building from NEW-SITE-ONEPASS"
keywords: ["new-site", "customization", "checklist", "166-fields", "demo-replacement"]
---

# 新站点改造清单（AllinCMS template → 客户内容）

> **用途**：任何 AI 给任何新客户建站时，拿着本清单**逐项照改**，即可把 default 主题模板的全部 demo 内容换成客户内容，无残留、可审计、可交付。
> **配套总流程**：先读 `RUNBOOK-ANYONE.md`（10 步总流程），本清单是其第 8 步"主题页/globals 改造"的逐字段展开版 + 全流程防漏清单。
> **前置**：`payload-token` 已就绪（**推荐 `export WS_TOKEN=<token>`**；或 chmod 600 文件）；站点已 `create_site`；`interface-kit` 目录可 `sys.path.insert` 导入 `allincms_api`。
>
> **怎么读本清单**：
> - 按 ①~⑪ 分层；每层一张或多张表，每行 = 一个字段。
> - 行格式：**字段路径（精确）→ demo 默认值 → Example 替换示例 → 不改的后果 → 来源（文件:行）**。
> - 路径前缀约定：全站块用 `globals.elements.<key>.props.<field>`，页面块用 `pageDoc.elements.<key>.props.<field>`（`read_page_document()` 返回的 `page.document` / `page.globals` 两个元素树，来源 MODULES.md:4-5、allincms_api.py:220-231）。
> - **拿不准的字段标注"待验证"**，绝不猜值；所有 demo 值均来自 `templates/*.json` 实测样例，所有 Example 替换值均来自其 70_evidence 或编写时公网实测抓取。
> - demo 品牌注意：seeded 模板实际品牌为 "Northstar"（DEMO-CLEANUP.md:5），模板样例文件里为 "Example Corp"（home-page-example.json:512）——两者都是 demo，全部替换。

## 三条铁律（每条都对应一次真实返工，先背下来）

1. **可显示字段全部显式传**：props 里任何未提供的字段都会被服务端用模板默认值回填（含模板文案/假链接）。详见"服务端回填规则"节（来源 MODULES.md:7）。
2. **globals 按页存储**：header/footer/弹窗/浮钮存在**每一页**的 `globals` 里，改完后同一份 `globals_doc` 要对**全部 7 页**逐页 `save+publish`（来源 RUNBOOK-ANYONE.md:92、MODULES.md:130）。
3. **置空 ≠ 删除**：空字符串会被 zod 默认值打回 demo 值（如 WhatsApp `wa.me/+44-7911-123456`）。要"没有这个元素"就**同时删除 `elements.<key>` 和 `page-root.children` 里的引用**（来源 RUNBOOK-ANYONE.md:58、fix-remove-wa.py:21-23）。

## 分层总览（每层对应的操作与序号）

| # | 层 | 做什么 | 关键入口 |
|---|---|---|---|
| ① | 站点记录 | create_site / read_sites 选目标；站点名=全站 title 前缀 | allincms_api.create_site L263 |
| ② | 全局 globals | header / footer / contact-dialog / social-floating 全字段替换（7 页重交） | home-page-example.json L506-690 |
| ③ | 7 页逐块 | 每页每块必改 props 字段替换 | MODULES.md L14-61 |
| ④ | 分类/标签 | create_category2（cover 显式 null）/ create_tag | allincms_api.py L273-283 |
| ⑤ | 媒体 | upload_media + update_media 回写 title/alt/caption | allincms_api.py L285-297 |
| ⑥ | 产品 | 独立审查 READY/digest → mutate_reviewed_product（create/update） | product-payload-example.json |
| ⑦ | 文章 | article create/update：k3 写 + distinct reviewer + strict record/capability；create 先 ISS-111 资格五步→draft→reviewed update；post-detail CTA 块 | post-payload-example.json、fix-post-cta.py |
| ⑧ | 每站审计配置 | 复制模板按 COP 实填，audit/gate/contact 三命令都带 --config | site-audit-config.template.json |
| ⑨ | set_home_page | 最后一步；顺序错误=根路径错误壳 | ROOT-PATH-ISSUE.md L48-70 |
| ⑩ | demo 种子清理 | createTheme(default) 会重种 3 产品+3 文章+6 分类+7 标签（taxonomy 同样种入），每次建主题后重跑 `delete-demo-content.py`（全链） | RUNBOOK-ANYONE.md:60；ISS-071/074 |
| ⑪ | 平台 BLOCK 记录 | 5 项 BLOCK 抄进交付清单"已知事项" | RUNBOOK-ANYONE.md L142-153 |

---

## ① 站点记录（site create）

| 项 | 字段/路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 站点名 | `create_site(name, description)` 的 `name` | —（无 demo；由你取名） | `Example Corp` | **站点名是全站页面 title 前缀**（"Home \| <站名>"），写错=每页标题错 | allincms_api.py:263；FRONTEND-STATUS.md:4-20 |
| 站点描述 | `create_site(name, description)` 的 `description` | — | 一句话站描述 | 后台/元信息显示 demo 描述 | allincms_api.py:263 |
| 主题初始化 | 账号非首站时 createSite 只给 **blank 主题（0 页）** | — | 手工 `create_theme(preset='default')`（总是生成 7 页） | 不建主题 = 无页面可改，根路径 `/` 必然错误壳 | allincms_api.py:345-352；ROOT-PATH-ISSUE.md:10-13 |
| 站点选取 | 站点已存在 → `read_sites()` 选目标，勿重复建站 | — | 取 `site_id` / `site_key`（Example: `<your-site-id>` / `<your-site-key>`） | 重复建站产生多个站点，数据落错地方 | RUNBOOK-ANYONE.md:39；HANDOFF.md:8-9 |

> 注意：`create_theme(preset='default')` 会**重种 demo 种子**（见 ⑩）；主题 id / 页面 id 每次重建都会变，一律 `read_themes` / `read_pages` 现取（RUNBOOK-ANYONE.md:62）。

---

## ② 全局 globals（`globals.elements`，站点级共享，7 页逐页重交）

来源基准：home-page-example.json L506-690（globals 元素树）；MODULES.md L101-107（globals 块字段表）；DEMO-CLEANUP.md L4-11（Example 实测替换）；编写时公网实测。

### 2.1 header-dropdown（元素 key `header-dropdown-1`）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 1 | `globals.elements.header-dropdown-1.props.siteTitle` | `Example Corp`（seed 实际为 `Northstar Supply`） | `Example Corp` | 顶栏品牌名全站错误 | home-page-example.json:512；DEMO-CLEANUP.md:5 |
| 2 | `...props.tagline` | `Vacuum insulated bottles` | `Precision components up to high-frequency specs`（公网实测） | 品牌标语显示 demo 品类 | home-page-example.json:513 |
| 3 | `...props.logoMedia` | `null` | 无 logo 图 → 保持 `null`；有 → 传 `{type:"image",value:{name,type:"image",source:"url",url}}`（URL 带扩展名） | 无图时传错结构会显示破图 | home-page-example.json:514；MODULES.md:98-99 |
| 4 | `...props.logoTarget.href` | `/` | `/`（set_home_page 修复前临时用 `/home`） | logo 点击回 demo 首页/错误壳 | home-page-example.json:518；fix-globals-wa.py:30 |
| 5 | `...props.navigation[].label`（全树） | `Home / Products / Guides / About / Contact` | `Home / Products / Guides / About Us / Contact Us`（公网实测） | 导航显示 demo 站名（如 "Bags"） | home-page-example.json:520-570 |
| 6 | `...props.navigation[1].target.href`（Products） | `/products` | `/products` | 指向错误列表页 | home-page-example.json:533 |
| 7 | `...props.navigation[1].children[].label` | `Insulated Bottles` | `RF Test Cables`（公网实测） | **children 若不显式传会被回填 demo "Bags"** | home-page-example.json:537；MODULES.md:7 |
| 8 | `...props.navigation[1].children[].target.href` | `/products?category=product-insulated-bottles` | `/products?category=rf-test-cable-assemblies`（另加 `microwave-adaptors` 子项） | 下拉点击 → 空分类/404 | home-page-example.json:540；DEMO-CLEANUP.md:6 |
| 9 | `...props.navigation[2].target.href`（Guides） | `/posts/how-to-choose-an-insulated-bottle` | `/posts`（children: `Measurement guides`→`/posts/example-guide-slug-assembly`、`Connector types`→`/posts/example-product-guide-slug`，公网实测） | 导航指向不存在的 demo 文章 | home-page-example.json:550 |
| 10 | `...props.ctaLabel` | `Get a Quote` | `Request a Quote`（公网实测） | 主 CTA 文案 demo | home-page-example.json:571 |
| 11 | `...props.ctaTarget` | `{type:"action", anchorId:"contact-form-dialog"}` | 保持不变（锚点开弹窗，公网实测 `#contact-form-dialog`） | 改了会断掉全站询价弹窗 | home-page-example.json:572-575 |

### 2.2 footer-columns（元素 key `footer-columns-1`）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 12 | `...props.brand` | `Example Corp` | `Example Corp`（DEMO-CLEANUP.md:7） | 页脚品牌名 demo | home-page-example.json:583 |
| 13 | `...props.kicker` | `Vacuum insulated bottles` | `Precision components`（公网实测） | 页脚标语 demo 品类 | home-page-example.json:584 |
| 14 | `...props.description` | `Double-wall vacuum insulated stainless steel bottles for commute, travel, and family use.` | `precision test cable assemblies and adaptors up to high-frequency for production, metrology and R&D.`（公网实测） | 页脚公司简介整段 demo | home-page-example.json:585 |
| 15 | `...props.columns[0].title` + `links[].label` | `Shop` / `Products` / `How to choose` | `Products` / `RF test cables` / `Microwave adaptors`（公网实测） | 页脚第一列 demo 文案 | home-page-example.json:587-604 |
| 16 | `...props.columns[0].links[].target.href` | `/products`、`/posts/how-to-choose-an-insulated-bottle` | `/products`、`/products`（或分类页 `?category=`） | 页脚链接指向 demo 文章 | home-page-example.json:591-602 |
| 17 | `...props.columns[1].title` + `links[].label` | `Company` / `About us` / `Contact us` | `Company` / `About us` / `Contact us`（公网实测，语义同构可保留） | 文案不对位 | home-page-example.json:606-623 |
| 18 | `...props.columns[2].title` + `links[].label` | `Content` / `Journal` / `Buying guide` | `Guides` / `Measurement guides` / `Connector types`（公网实测） | 页脚第三列 demo 文案 | home-page-example.json:625-642 |
| 19 | `...props.columns[2].links[].target.href` | `/posts`、`/posts/how-to-choose-an-insulated-bottle` | `/posts`、`/posts/example-product-guide-slug`（公网实测） | 页脚链接 404 | home-page-example.json:630-639 |
| 20 | footer `...props.socialLinks` | 样例为 `[]`；footer 此字段**空则留白不回填**（MODULES:105）——**会回填 Instagram/LinkedIn 的是 contact 页 contact-info-1.props.socialLinks**（见 ⑩ 回填规则表） | 无社媒 → footer 显式 `[]`、contact-info 显式 `[]`（Example 实测两处都清空，DEMO-CLEANUP.md:8） | 页脚出现 Instagram/LinkedIn 假链接（模板词审计 FAIL） | home-page-example.json:645；MODULES.md:7、46、105 |
| 21 | `...props.copyright` | `© 2026 Example Corp. Demo site for qualification run.` | `© 2026 Example Corp Co., Ltd. All rights reserved.`（公网实测） | 版权行 demo 公司名 + "Demo site" 字样 | home-page-example.json:646；DEMO-CLEANUP.md:7 |
| 22 | `...props.systemNote` | `Bottles built for long days, not short seasons.`（seed 版本含 `San Francisco`） | `Shenzhen, Guangdong, China.`（公网实测；DEMO-CLEANUP.md:7 San Francisco→Shenzhen） | 页脚细则 demo 城市 | home-page-example.json:647 |

### 2.3 contact-form-dialog（元素 key `contact-form-dialog`）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 23 | `...props.title` | `Ask about sizes, materials, or wholesale.` | `Request a quote`（公网实测弹窗标题） | 全站询价弹窗标题 demo | home-page-example.json:655 |
| 24 | `...props.description` | `Send a question about insulation, capacity, wholesale programs...` | `Tell us about your measurement. Frequency range, connector interface, cable length and application.`（公网实测弹窗文案） | 弹窗描述 demo 品类 | home-page-example.json:656 |
| 25 | `...props.eyebrow` | `Product support` | Example 弹窗 eyebrow 实值待验证（公网渲染为 `Sales & engineering` 一带，不确证） | 弹窗眉题 demo | home-page-example.json:657 |
| 26 | `...props.formSlug` | `contact-inquiry` | 保持 `contact-inquiry`（平台表单库键，改了表单不渲染） | 弹窗表单断裂 | home-page-example.json:659；site-content-checklist.md F 节 |
| 26b | 元素级 `anchorId` | `contact-form-dialog`（与 header `cta_anchor` 一致） | **必须显式设置**：null 时公开站渲染器静默丢弃整个弹窗（点击只改 hash、零报错，ISS-094）；builder 默认已带，手拼 elements 时勿漏 | 全站 CTA 弹窗静默失效 | MODULES.md globals 表；issues.tsv ISS-094 |
| 27 | `...props.closeLabel` | `Close contact dialog` | 保持（无障碍文案，无客户内容） | —（不改无害） | home-page-example.json:658 |

### 2.4 social-floating-button（元素 key `social-floating-button-1`）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 28 | `globals.elements.social-floating-button-1`（整元素） | `brand:"whatsapp", url:"https://wa.me/8613800000000"`（seed 版本 `wa.me/+44-7911-123456`） | **客户源材料无社媒 → 整体删除元素**：同时删 `elements.social-floating-button-1` 与 `globals.elements.page-root.children[]` 中的 `"social-floating-button-1"`（Example 实测，fix-remove-wa.py:21-23） | 右下角假 WhatsApp 浮钮；置空 `url` 会被 zod 回填 demo 号码（ISS-068） | home-page-example.json:664-675；RUNBOOK-ANYONE.md:58 |
| 29 | `...props.url`（**仅客户有真实 WhatsApp 时**） | demo 号 | `https://wa.me/<真实国家码+号码>` | 浮钮指向他人号码 | home-page-example.json:668；MODULES.md:107 |
| 30 | `...props.label` / `...props.showLabel` / `...props.position` | `WhatsApp` / `false` / `bottom-right` | 按需（客户要求显示标签时 showLabel=true） | 显示 demo 标签 | home-page-example.json:669-671 |

### 2.5 globals 根节点（`globals.elements.page-root`）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 31 | `globals.elements.page-root.children` | `["header-dropdown-1","footer-columns-1","contact-form-dialog","social-floating-button-1"]` | 删除浮钮后为 `["header-dropdown-1","footer-columns-1","contact-form-dialog"]`（fix-remove-wa.py:22） | 只删 elements 不删 children = 引用悬空/按钮复活 | home-page-example.json:681-687 |

> **globals 交付动作**：对 7 页（/home /about-us /contact-us /posts /posts/{post} /products /products/{product}）逐页 `read_page_document` → 替换该页 `globals` → `save_home(..., intent='save')` + `save_home(..., intent='publish')`。只改 1 页 = 其余 6 页仍是 demo header/footer（RUNBOOK-ANYONE.md:92）。

---

## ③ 7 页逐块（`pageDoc.elements`）

> 块字段全集见 MODULES.md L14-61（20 种页面块）；嵌套子结构 schema 见 MODULES.md L63-99。每块 props 里**所有可显示字段都要显式传**（防回填，见"服务端回填规则"节）。
> 元素 key 名以每页 `read_page_document` 实读为准（下文 key 名来自实测样例与 Example 脚本）。

### 3.1 /home 首页（11 块，children 见 home-page-example.json:10-22）

**块 1：carousel-campaign-1（轮播）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 32 | `...props.slides[0..n].eyebrow` | `12h hot, 24h cold` 等 | `precision components up to high-frequency specs` 等（公网实测 slide 1） | 轮播眉题 demo | home-page-example.json:30 |
| 33 | `...props.slides[].title` | `Keep it hot all day...` | `From cost-effective to high-spec`（公网实测） | 轮播大标题 demo | home-page-example.json:31 |
| 34 | `...props.slides[].description` | `The ThermoSteel 500ml is a double-wall...` | `Example Corp designs and manufactures precision test cable assemblies and adaptors up to high-frequency for measurement teams that need repeatable results.`（公网实测） | 轮播正文 demo | home-page-example.json:32 |
| 35 | `...props.slides[].media.value.url` | `https://assets.laicms.com/<demo-site-key>/a1vn3g.jpg`（demo 保温杯图） | 客户产品/场景图（Example: `https://assets.laicms.com/<your-site-key>/gk8y0l.webp`，fix-post-cta.py:41） | 首页主视觉是别人家保温杯 | home-page-example.json:39 |
| 36 | `...props.slides[].price` / `...product` | `From $29` / `ThermoSteel 500ml Vacuum Insulated Bottle` | `EX-SERIES high-precision cable` 等真实系列名 | 价格/品名 demo | home-page-example.json:44-45 |
| 37 | `...props.slides[].primaryLabel` + `...primaryTarget.href` | `Shop the bottle` / `/products/thermosteel-500ml-vacuum-insulated-bottle` | `Explore the range` / `/products`（公网实测） | CTA 指向 demo 产品详情 | home-page-example.json:46-50 |
| 38 | `...props.slides[].secondaryLabel` + `...secondaryTarget.href` | `How to choose` / `/posts/how-to-choose-an-insulated-bottle` | `Why phase stability matters` / `/posts/why-phase-stability-matters-rf-test-cables`（公网实测） | 次 CTA 指向 demo 文章 | home-page-example.json:51-55 |
| 39 | `...props.serviceItems[].icon/title/description` | `truck` / `Export shipments` / `Consolidated container loads...` | `Ships in 1-2 days` / `Fast fulfillment with tracking on every order.` + `30 day returns` 条（公网实测，icon 值 待验证） | 轮播下服务条 demo 文案 | home-page-example.json:114-125；MODULES.md:66-67 |

**块 2：categories-1（category-showcase-grid 分类卡）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 40 | `...props.sectionLabel` / `headline` / `supportingCopy` | `Shop by category` / `Pick your bottle.` / `Start with the size and use case...` | `Product families` / `Cables and adaptors for every bench` / `Four test cable series and three precision adaptor families cover sub-6 GHz to high-frequency.`（公网实测） | 分类区标题 demo | home-page-example.json:133-135 |
| 41 | `...props.items[].name` / `description` | `Insulated Bottles` / `Buying Guide` / `Wholesale & OEM` | `RF Test Cables` / `Microwave Adaptors` / `Measurement Guides`（公网实测） | 分类卡 demo 品类 | home-page-example.json:138-189 |
| 42 | `...props.items[].target.href` | `/products?category=product-insulated-bottles` 等 | `/products`、`/products`、`/posts`（公网实测） | 卡点击 → 空分类/404 | home-page-example.json:152 |
| 43 | `...props.items[].media.value.url` | demo 图（且 3 卡同图） | 每卡不同真实图（**同页勿重复同一张**） | 分类卡显示 demo 图 | home-page-example.json:141-187；site-content-checklist.md H 节 |

**块 3：hero-commerce-1（商品 Hero）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 44 | `...props.eyebrow` / `title` / `description` | `Example Corp flagship` / `Insulated bottles for the whole day.` / demo 保温杯文案 | `Example Corp` / `Precision components solutions up to high-frequency` / `Precision test components and adaptors for production, metrology and R&D.`（公网实测） | Hero 主区整段 demo | home-page-example.json:200-202 |
| 45 | `...props.secondaryNote` | `Export quotations in 1-2 business days...` | `Around 20 years of RF experience, Shenzhen China`（公网实测） | 副注 demo | home-page-example.json:203 |
| 46 | `...props.mediaCaption` / `mediaKicker` / `mediaMeta` | demo 图注/`Example Corp`/`Vacuum insulated / 500ml` | 真实图注与品名（如 EX-SERIES 系列名） | 图下规格面板 demo | home-page-example.json:214-216 |
| 47 | `...props.productName` / `productDescription` / `productPriceLabel` | `ThermoSteel 500ml Vacuum Insulated Bottle` / `(Synthetic demo product for the qualification run.)` / `From $29` | 真实旗舰品名/描述/价签（无价可不传） | 规格面板 demo 产品 | home-page-example.json:217-219 |
| 48 | `...props.actions[].label` + `actions[].target.href` | `Shop the bottle`→`/products/thermosteel-...`、`Read the buying guide`→`/posts/how-to-choose-...` | `Explore products`→`/products`、`Request a quote`→`/contact-us`（公网实测） | Hero CTA 指向 demo | home-page-example.json:220-237 |
| 49 | `...props.serviceItems[].label/value` | `Volume pricing`/`Wholesale · OEM` 等 3 组 | `Engineered repeatability`/`Designs tuned to your application`、`Modular ordering`、`Fast quoting`（公网实测） | 服务列表 demo | home-page-example.json:238-251 |
| 50 | `...props.campaignPills[]` | `12h hot · 24h cold` 等 3 粒（**缺省会被回填 demo 药丸**） | `Up to high-frequency`/`EX-SERIES high-precision low loss cable`、`high-frequency support`、`Low PIM`/`Below -125 dBm`、`Phase and flexure stable`（公网实测） | 药丸区 demo 复活 | home-page-example.json:252-265；MODULES.md:7 |

**块 4：features-1（feature-grid-proof 特性网格）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 51 | `...props.eyebrow` / `heading` / `description` | `Why it is the daily pick` / `Insulation you can measure, not just claim.` / demo | `Why Example` / `Built for repeatable measurements` / `Construction, phase stability and durability engineered for the test floor.`（公网实测） | 特性区标题 demo | home-page-example.json:273-275 |
| 52 | `...props.proofRows[].label/title/description/meta` | `01 / Insulation` / `12h hot, 24h cold` / demo | `1`/`Z-TEST`/`Cost-effective durable`/`BeCu connector, PEI insulator, tri-shielding for high-cycle production test.`/`26.5 GHz`（公网实测第 1 行） | 特性卡 demo 数据 | home-page-example.json:277-309；MODULES.md:70-71 |
| 53 | `...props.proofRows[].actionLabel` + `target.href` | `Shop bottles`→`/products` | `View product`→`/products/z-test-durable-rf-test-cable-assembly`（公网实测） | 卡内 CTA 指错 | home-page-example.json:282-286 |

**块 5：products-1（featured-product-list-showcase 精选产品）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 54 | `...props.sectionLabel` / `headline` / `supportingCopy` / `merchandisingNote` | `Shop the edit` / `Best sellers and new arrivals` / demo / demo | `Featured products` / `Test cable assemblies and adaptors` / `Seven products across the Example range, from cost-effective production cables to high-frequency mmWave adaptors.`（公网实测） | 产品区标题 demo | home-page-example.json:319-322 |
| 55 | `...props.ctaLabel` + `ctaTarget.href` | `View all products` → `/products` | `Browse all products` → `/products`（公网实测） | CTA 文案 demo | home-page-example.json:323-327 |
| 56 | `...props.productActionLabel` / `featuredProductActionLabel` | `View product` / `View featured product` | `View product` / `View featured product`（公网实测，语义同构） | 按钮文案 demo | home-page-example.json:328-329 |
| 57 | `...props.associatedListPage.href` / `associatedDetailPage.href` / `categorySlug` / `sortOrder` | `/products` / `/products/{product}` / `""` / `newest` | 保持同构；categorySlug 可设产品分类 slug 过滤（Example 用 `""` 全量） | 列表跳转错误；**该块自动拉全部站点产品，demo 产品不删会混入**（DEMO-CLEANUP.md:30） | home-page-example.json:331-340 |

**块 6：materials-1（material-story-split 材质故事）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 58 | `...props.sectionLabel` / `headline` / `supportingCopy` | `Materials and care` / `Built to survive years of daily washes.` / demo | 客户工艺/材质主题文案（Example 首页该块实测文案以公网为准，本行 demo 必须替换） | 材质故事整段 demo | home-page-example.json:348-350 |
| 59 | `...props.notes[].title/description` | `304 stainless inner` 等 3 条 | 客户材质/工艺要点（Example: 屏蔽/铠甲/相位稳定类要点，具体值 待验证） | 要点卡 demo | home-page-example.json:361-374；MODULES.md:72-73 |
| 60 | `...props.actionLabel` + `actionTarget.href` | `Read the material guide` → `/about-us` | 指向真实内容页（如 `/posts/<guide>` 或 `/contact-us`） | 块内 CTA 指错 | home-page-example.json:375-379 |

**块 7：proof-1（social-proof-quotes 用户评价）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 61 | `...props.sectionLabel` / `headline` / `ratingLabel` | `Paddler notes` / `Proof from bottles that stay in use.` / `4.9 average...` | 真实评价区文案；**无真实客户评价 → 整块删除（children+elements 同删）**，不得编造 | 假评价/假评分上线（合规风险） | home-page-example.json:387-389 |
| 62 | `...props.reviews[].quote/name/detail` | `Coffee is still hot at 3pm...` / `Lin W.` / `Verified customer` | 真实引用；无真实客户证言 → 用角色化档位（Example 实测保留块，用 "Production engineer"/"Metrology lab" 等角色证言，不虚构人名）（Example 首页是否保留该块：公网首页未渲染评价区，判定为已删，具体以 readback 为准） | 假客户证言 | home-page-example.json:391-405；MODULES.md:74-75 |

**块 8：news-1（featured-news-list-editorial 精选文章）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 63 | `...props.sectionLabel` / `headline` / `supportingCopy` | `Stories and guides` / `Field notes, buying guides, and updates` / demo | 客户指南区文案（公网 Example: 文章区标题实测值以 readback 为准，demo 必须替换） | 文章区标题 demo | home-page-example.json:415-417 |
| 64 | `...props.digestLabel` / `featureLabel` / `postActionLabel` / `featureActionLabel` | `Latest stories` / `Featured story` / `Read` / `Read story` | `Read` / `Read story` 类真实文案（公网实测 `Read`、`Read story` 同构） | 标签文案 demo | home-page-example.json:418-437 |
| 65 | `...props.ctaLabel` + `ctaTarget.href` | `View all stories` → `/posts` | `Browse all guides` → `/posts`（公网实测） | CTA demo | home-page-example.json:420-424 |
| 66 | `...props.associatedListPage/associatedDetailPage/categorySlug/sortOrder/fit` | `/posts`、`/posts/{post}`、`""`、`newest`、`cover` | 保持同构 | 跳转错误；**该块自动拉全部站点文章，demo 文章不删会混入**（DEMO-CLEANUP.md:30） | home-page-example.json:425-437 |

**块 9：faq-accordion-1（FAQ）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 67 | `...props.sectionLabel` / `headline` / `supportingCopy` / `supportNote` | `Buyer questions` / `Questions buyers ask before they order` / demo / demo | 客户 FAQ 标题区（Example 公网实测 FAQ 区标题以 readback 为准） | FAQ 标题 demo | home-page-example.json:445-448 |
| 68 | `...props.items[].question/answer` | `How fast will my order ship?` 等 3 组 | `Which cable series should I choose?` / `What connector interfaces do you support?` / `How do I order?`（公网实测 3 问） | FAQ 内容整段 demo | home-page-example.json:449-462；MODULES.md:76-77 |

**块 10：newsletter-inline-1（订阅条）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 69 | `...props.sectionLabel` / `headline` / `supportingCopy` | `New drops and care notes` / `Get the next bottle drop before it sells through.` / demo | `Stay in the loop` / `RF measurement tips and product updates` / `Occasional practical content for test and measurement teams.`（公网实测） | 订阅条 demo 文案 | home-page-example.json:470-472 |
| 70 | `...props.emailPlaceholder` / `submitLabel` / `finePrint` | `Email address` / `Subscribe` / `Product news only. Unsubscribe anytime.` | 按客户订阅策略改（Example 实测 `Subscribe`；其余以 readback 为准） | 订阅文案 demo | home-page-example.json:473-475 |

**块 11：contact-1（contact-form-split 联系表单分栏）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 71 | `...props.eyebrow` / `title` / `description` | `Contact` / `Tell us what you are looking for` / demo | `Contact Example RF` / `Talk to our RF specialists` / `Tell us your frequency range, connector interface, length and application for a recommendation and quotation.`（公网实测） | 首页联系区标题 demo | home-page-example.json:483-485 |
| 72 | `...props.responseTitle` / `responseDescription` | `What happens after submission` / demo | 客户响应承诺文案（公网实测值以 readback 为准） | 响应区 demo | home-page-example.json:486-487 |
| 73 | `...props.emailValue` | `sales@example.example` | `sales@examplerf.com`（BRIEF.md:8、公网实测） | **表单通知/展示 demo 邮箱（demo-contact 审计 FAIL）** | home-page-example.json:489 |
| 74 | `...props.phoneValue` | `+86 (0) 755 0000 0000` | 无真实电话 → 文案替代：`Inquiry via email/site form`（公网实测；源材料无电话号） | demo 电话泄漏；源无电话就不得编号 | home-page-example.json:491 |
| 75 | `...props.addressValue` | `Example Corp Export Dept.\nShenzhen, China` | `Example Industrial Park, Shenzhen`（source-extraction.json + 公网实测） | demo 地址 | home-page-example.json:493 |
| 76 | `...props.hoursValue` | `Mon-Fri, 9:00-18:00 (GMT+8)` | 真实营业时间（Example 同 demo 值，公网实测；确认后沿用） | 营业时间 demo | home-page-example.json:495 |
| 77 | `...props.formCardEyebrow` / `formCardTitle` / `formCardDescription` | `Inquiry intake` / `Send the details` / demo | `Inquiry intake` / `Send the details` / `Share your measurement requirements and we will reply with a recommendation.`（公网实测） | 表单卡文案 demo | home-page-example.json:496-498 |
| 78 | **所有表单块** `formSlug`（contact-us 的 contact-split-1、**首页的 contact-1**、7 页 globals 的 contact-form-dialog——逐页逐块核） | `""`（**空=表单不渲染！ISS-076/077 实测：联系页与首页各有一个空 slug 块漏网**） | **每处都填站点真实表单 slug**（如 `contact-inquiry`，从 readback initialForms 取键名） | 空 slug → 该处整个 <form> 不渲染；填不存在的 slug 同样断 | ISS-076/077；MODULES.md:7 |

### 3.2 /about-us 公司页（6 块，children 见 about-page-example.json:151-158）

**块 1：about-intro-1（about-intro-media）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 79 | `...props.eyebrow` / `title` / `description` | `About us` / `Bottles designed for long days, not short seasons.` / demo | `About Example` / `Precision components for repeatable measurements` / `Example Corp Co., Ltd. designs and manufactures precision components solutions from Shenzhen, China.`（公网实测） | 公司简介头段 demo | about-page-example.json:14-16 |
| 80 | `...props.body` | demo 保温杯公司介绍 | 客户公司介绍正文（只用源材料事实：20 年 行业经验、67GHz、低 PIM 等，BRIEF.md:5-9） | 公司简介正文 demo | about-page-example.json:17 |
| 81 | `...props.media.value.url` / `caption` | demo 图 / demo 图注 | 客户公司/产线图；caption 显式传（**缺省会回填 demo 图注**） | 公司图 + 图注 demo | about-page-example.json:18-28 |

**块 2：company-story-1（company-story-media）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 82 | `...props.sectionLabel` / `headline` / `lead` | `Our story` / `One leaky bag, one 500ml bottle...` / demo | `Our story` / `From component specialist to precision interconnect partner` / `Example Technology specializes in design, development and manufacturing of precision components solutions.`（公网实测） | 公司故事 demo 起源 | about-page-example.json:36-38 |
| 83 | `...props.body` | demo 故事正文 | 客户发展史正文（源材料事实） | 故事正文 demo | about-page-example.json:39 |
| 84 | `...props.note` / `noteLabel` | `If a claim cannot be measured...` / `What guides us` | 客户理念引述（Example 公网实测 `Technology innovation and professional service`，noteLabel 以 readback 为准） | 引述块 demo | about-page-example.json:50-51 |

**块 3：company-stats-1（company-stats-grid）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 85 | `...props.sectionLabel` / `headline` / `description` | `By the numbers` / `A short spec sheet...` / demo | `By the numbers` / `Engineering capability` / `A compact team with deep RF experience and the equipment to prove performance.`（公网实测） | 数据区标题 demo | about-page-example.json:59-61 |
| 86 | `...props.stats[].value/label/description` | `12h`/`Hot retention`、`24h`、`304`、`100%` | `high-frequency`/`Frequency support`、`20+ yrs`/`RF experience`、`< -125 dBm`/`Low PIM design`、`100,000+`/`Fatigue life`（公网实测 4 组） | **数字是 demo 保温杯数据（严重失实）** | about-page-example.json:62-83；MODULES.md:78-79 |

**块 4：company-values-1（company-values-grid）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 87 | `...props.sectionLabel` / `headline` / `description` | `How we choose` / `Three rules...` / demo | `What we stand for` / `Precision, repeatability, responsiveness` / 客户理念描述（公网实测） | 价值观区 demo | about-page-example.json:92-94 |
| 88 | `...props.values[].title/description` | `Daily-use first` 等 3 组 | `Precision` / `Repeatability` / `Responsiveness`（公网实测 01/02/03） | 价值观卡 demo | about-page-example.json:95-108 |

**块 5：company-team-1（company-team-grid）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 89 | `...props.members[].name/role/bio` | `Sam Rivera` / `Founder / Sourcing` / demo | 真实团队成员（客户授权）或角色化档；**无成员信息 → 整块删除**（Example 公网 About 页无团队区 = 已删，判定依据公网抓取） | 假团队成员上线 | about-page-example.json:120-139 |

**块 6：breadcrumb-inline-1**：props 为 `{}`，无客户内容，不改（about-page-example.json:5-10）。

### 3.3 /contact-us 联系页（5 块，children 见 contact-page-example.json:118-125）

**块 1：contact-header-1（contact-header-summary）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 90 | `...props.eyebrow` / `title` / `description` | `Contact us` / `Questions, samples, or a leak-test story?` / demo | `Contact Example RF` / `Talk to our RF specialists` / `Tell us your frequency range, connector interface, length and application for a recommendation and quotation.`（公网实测） | 联系页头 demo | contact-page-example.json:14-16 |
| 91 | `...props.items[].label/value` | `Response time`/`Within one business day`、`Best for`/`Orders, wholesale, product support` | `Response time`/`Within one business day`、`Best for`/`Quotes, samples, custom assemblies`（公网实测） | key-value 卡 demo | contact-page-example.json:17-26；MODULES.md:84-85 |

**块 2：contact-info-1（contact-info-grid）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 92 | `...props.sectionLabel` / `headline` / `description` | `Reach us` / `Use the channel that fits your question.` / demo | `Contact details` / `Talk to our RF specialists` / `Send an inquiry through the site form for a recommendation and quotation.`（公网实测） | 联系卡区标题 demo | contact-page-example.json:34-36 |
| 93 | `...props.items[0]`（type=email）`value`/`detail` | `hello@example-demo.com` / demo | `sales@examplerf.com` / `For quotes, product questions and custom assemblies.`（公网实测） | **demo 邮箱公开（demo-contact 审计 FAIL + 询盘流失）** | contact-page-example.json:39-43 |
| 94 | `...props.items[1]`（type=phone）`value`/`detail` | `+86 138 0000 0000` / demo | 无真实电话 → `Inquiry via email or site form` / `Sales and engineering support.`（公网实测，不编号码） | demo 电话公开 | contact-page-example.json:44-49 |
| 95 | `...props.items[2]`（type=address）`value`/`detail` | `Building 3, No. 28 Xingang Road, Hangzhou, China` / demo | `Example Industrial Park, Shenzhen` / 到访说明（公网实测） | demo 城市地址 | contact-page-example.json:50-55 |
| 96 | `...props.socialLinks` | 样例 `[]`；**缺省回填 Instagram/LinkedIn** | 无社媒 → 显式 `[]` | 假社媒链接复活（MODULES.md:46） | contact-page-example.json:57 |

> **坑（DEMO-CLEANUP.md:28-30）**：此块必须用 `items[]`（type:email|phone|address）schema；误用 `emailLabel` 等自定义字段会被服务端忽略并回填 San Francisco demo 联系方式。

**块 3：location-map-1（location-map-interactive）**

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 97 | `...props.sectionLabel` / `headline` / `address` / `description` | `Visit us` / `Our studio is in Hangzhou.` / demo / `Building 3, No. 28 Xingang Road, Hangzhou, China` | `Find us` / `Shenzhen, Guangdong, China` / `Example Industrial Park, Shenzhen` / 同左（公网实测） | 地图区文案 + 地址 demo | contact-page-example.json:66-69 |
| 98 | `...props.latitude` / `longitude` | `30.25` / `120.15`（杭州） | 客户真实坐标（Example 深圳光明区坐标；具体数值 待验证，源材料未给 lat/lng） | 地图钉在 demo 城市 | contact-page-example.json:70-71 |
| 99 | `...props.description`（主要）；`...props.details[]` 为可选空数组（Example 实测线上为 []，勿把地址塞进 details） | 模板 details 示例 `Transit`/`Near Xingang Road Metro Station` | 地址/到访信息写 description（Example 实测 `Guangming District high-tech industrial park`） | 到访细节 demo | contact-page-example.json:75-84 |

**块 4：contact-form-1（contact-form-split）**：字段路径与首页 contact-1 完全一致（见 #71-78）；**emailValue/phoneValue/addressValue 必须与 contact-info-1 的 items 值一致**（site-content-checklist.md F 节）。Example 公网实测：Email `sales@examplerf.com`、Phone `Inquiry via email/site form`、Office `Example Industrial Park, Shenzhen`、Hours `Mon-Fri, 9:00-18:00 (GMT+8)`。

**块 5：breadcrumb-inline-1**：props `{}`，不改。

### 3.4 /products 产品列表页

> 元素 key 名以 `read_page_document` 实读为准（Example posts 页实测 key：`page-header-1`、`recommendations-1`，fix-posts-page.py:21-32；products 页同构）。

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 100 | `...page-header-1.props.eyebrow/title/description/kicker` | 模板默认列表页头文案 | 客户产品页头文案（如 `RF Test Cables & Adaptors` / 系列说明；Example products 页实值以 readback 为准） | 列表页头 demo 文案 | MODULES.md:57；fix-posts-page.py:21-31（posts 页同构样例） |
| 101 | `...（full-product-list-filtered 块）.props.pageSize/showToolbar/sortOrder/columnCount/productActionLabel/associatedDetailPage.href` | 模板默认 | 同构；产品少时 `showToolbar=false` 防空筛选；`associatedDetailPage.href="/products/{product}"` | 筛选/分页异常；数据自动拉取，demo 产品不删会混入 | MODULES.md:22、59；CONTENT-MINIMUM.md:37-39 |
| 102 | `...recommendations-1.props.sectionLabel/headline/supportingCopy/postActionLabel`（注意：products 页该块是 recommended-news-list-grid 推文章，动作字段是 postActionLabel；posts 页镜像块才是 productActionLabel） | 模板默认推荐文案 | `Recommended articles` / `Guides for RF engineersand adaptors to pair with your reading`（posts 页实测值，fix-posts-page.py:32-38；products 页同构） | 推荐区 demo 文案 | MODULES.md:60 |

### 3.5 /products/{product} 产品详情页

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 103 | `...（product-detail-gallery 块）.props.specificationsHeading/fit` | 模板默认 | 客户规格标题（如 `Specifications`） | 规格区标题 demo | MODULES.md:53 |
| 104 | `...（product-related-grid 块）.props.sectionLabel/headline/supportingCopy/pageSize/columnCount` | 模板默认（demo 文案） | 客户相关推荐文案；**目录只有一个产品时显示空态 `No content is available yet.` → 删该模块或补产品** | 相关区 demo 文案或空态 | MODULES.md:55；site-content-checklist.md J 节 |
| 105 | 产品详情页正文区 | 渲染记录 `content`（空则无正文区） | 产品 payload 的 `content` 用 Slate `p|h2|h3|blockquote`（无则留空，不留空态） | 正文区 demo | MODULES.md:53；site-content-checklist.md C 节 |

### 3.6 /posts 文章列表页

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 106 | `...page-header-1.props.eyebrow/title/description/kicker` | 模板默认列表页头文案（首轮漏网点） | `RF Testing Guides` / `Measurement and selection guides` / `Practical RF engineering guides on test cable selection, phase stability, and connector types.` / `Guides written for RF and microwave engineers.`（fix-posts-page.py:22-27 实测） | 文章列表页头 demo 文案（audit template 项曾 FAIL） | MODULES.md:57；AUDIT-FACT-MATRIX-20260829.md:20 |
| 107 | `...page-header-1.props.stats[].label/value` | 模板默认统计 | `Guides`/`3 published articles`、`Topics`/`RF test cables, phase stability, connectors`（fix-posts-page.py:27-30） | 页头统计 demo | fix-posts-page.py:27-30 |
| 108 | `...（full-news-list-filtered 块）.props.pageSize/showToolbar/sortOrder/columnCount/postActionLabel/associatedDetailPage.href` | 模板默认 | 同构；`associatedDetailPage.href="/posts/{post}"` | 列表行为异常 | MODULES.md:58 |
| 109 | `...recommendations-1.props.sectionLabel/headline/supportingCopy/productActionLabel` | 模板默认推荐文案（首轮漏网点） | `Recommended products` / `Test cables and adaptors to pair with your reading` / `Example RF test cable assemblies and microwave adaptors referenced across these guides.` / `View product`（fix-posts-page.py:32-38 实测） | 推荐区 demo 文案（audit template 项曾 FAIL） | MODULES.md:61；AUDIT-FACT-MATRIX-20260829.md:20 |

### 3.7 /posts/{post} 文章详情页（含 CTA 块 + related 文案，必做）

| # | 字段路径 | demo 默认值 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 110 | `...（post-detail-article 块）.props.fit` | 模板默认 | 同构（正文渲染 Slate content，原生 p/h2/blockquote） | 正文样式异常 | MODULES.md:54、109-124 |
| 111 | `...related-1.props.sectionLabel/headline/supportingCopy/postActionLabel` | `More from the journal` 等 demo（首轮漏网点） | `Read next` / `More RF engineering guides` / `Practical guides on RF test cable selection, phase stability, and connector types for your measurement setup.` / `Read article`（fix-post-cta.py:22-29 实测） | 详情页 related 区 demo 文案（ISS-068 漏网点） | fix-post-cta.py:22-29；AUDIT-FACT-MATRIX-20260829.md:20 |
| 112 | **新增** `pageDoc.elements.cta-1`（type=`material-story-split`）+ `page-root.children` 追加 `"cta-1"` | 不存在（demo 模板无真 CTA） | props：`sectionLabel:"Work with Example RF"`、`headline:"Need an RF test cable assembly or adaptor for your setup?"`、`supportingCopy` 询价引导、`notes[]` 3 条（high-frequency / phase-stable / adaptors）、`actionLabel:"Request a Quote"`、`actionTarget:{type:"custom",href:"/contact-us?source=example-article"}`（fix-post-cta.py:31-54 完整样例） | **文章页无询价转化路径**（正文内联 link 平铺无 `<a>`，平台不支持；audit cta 项 FAIL） | RUNBOOK-ANYONE.md:93；MODULES.md:57、120；fix-post-cta.py:31-54 |
| 113 | `...related-1` 文章 <2 篇时的空态 | `No content is available yet.` | 补文章到 ≥3 或删 related 模块 | 详情页空态文案（用户可见） | MODULES.md:56；CONTENT-MINIMUM.md:21 |

---

## ④ 分类/标签

| # | 项 | 规则/demo 注意点 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 114 | `create_category2(site_slug, site_id, name, slug, content_type='products'|'posts', description='', order=0, cover=None)` | **cover 必须显式传 None**，否则 500 | 产品分类 2：`RF Test Cable Assemblies`/`rf-test-cable-assemblies`、`Microwave Adaptors`/`microwave-adaptors`；文章分类 1：`RF Testing Guides`/`rf-testing-guides` | 无分类：产品不进列表筛选、导航下拉空、详情页无分类标签 | allincms_api.py:273-278；RUNBOOK-ANYONE.md:103；HANDOFF.md:24-25 |
| 115 | `create_tag(site_slug, site_id, name, slug, description='')` | contentType 固定 `posts` | 标签 6+3：`production-testing, durable-test-cables, phase-stable, low-loss, mmwave, precision-adaptor` 等（BLOCK-media-upload.md:21；文章标签 3 个） | 列表页标签筛选空 | allincms_api.py:279-283；BLOCK-media-upload.md:21 |
| 116 | slug 命名 | 产品分类建议 `product-` 前缀；**先 read_lists 查 categoryOptions 防与模板已有分类 slug 撞车** | — | slug 撞车 → 创建失败或覆盖 | site-content-checklist.md B 节 |
| 117 | 归属 | 产品挂**产品分类** id，文章挂**文章分类** id，不可交叉 | — | 交叉挂接 → 列表页不显示 | site-content-checklist.md C 节；delivery-manifest.md:47 |

---

## ⑤ 媒体

| # | 项 | 规则/demo 注意点 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 118 | `upload_media(site_slug, site_id, file_path, title, alt, caption)` | multipart `_1_files`；返回 media_urls 后**立即 `update_media` 回写 title/alt/caption** | 10 张：产品图 7 + 公司/场景图 3（HANDOFF.md:23） | 媒体库 alt/title 缺失 → audit img/可访问性差 | allincms_api.py:285-297；RUNBOOK-ANYONE.md:109 |
| 119 | 媒体格式（产品/文章 payload 内引用） | 扁平 `{name,alt,type:'image',source:'oss',path:'<siteKey>/<file>.webp',size,mimeType}` 或 `{name,alt,type:'image',source:'url',url:完整URL}`；**URL 必须带扩展名** | Example 图：`https://assets.laicms.com/<your-site-key>/gk8y0l.webp`（fix-post-cta.py:41） | 无扩展名 URL 部分前端不渲染 | post-payload-example.json:7-15；product-payload-example.json:6-21；site-content-checklist.md H 节 |
| 120 | 上传通道可靠性 | 直接调 uploadMedia Server Action 有 500 记录；**验证过的路径是对话框驱动**，页面不水合时先重启浏览器 | 上传后 `read_media_library` 核对 10 字段（name/alt/url/path/size/mimeType） | 上传静默失败却继续建内容 → 全站破图 | BLOCK-media-upload.md:3-4；RUNBOOK-ANYONE.md:110 |
| 121 | 图片规范 | alt 必填；**同页不重复用同一张图**；CC 素材记录 author+license | — | 分类卡/hero 同图（走查扣分项） | site-content-checklist.md H 节 |

---

## ⑥ 产品

| # | 项 | 规则/demo 注意点 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 122 | 流程 | `mutate_reviewed_product`（review PASS 后内部 create_draft→publish_update 或 update） | 7 产品全 publish | 只 create 不 publish = 前台无产品 | RUNBOOK-ANYONE.md:98；allincms_api.py:299-306 |
| 123 | `payload.name` | 型号+品类 | `Z-TEST Cost-Effective Durable RF Test Cable Assembly` 等 7 个（audit-config pages 清单） | 品名 demo | product-payload-example.json:2；example-audit-config.json:10-16 |
| 124 | `payload.slug` | **create 后 draft slug 会变时间戳，publish 时 payload 必须带正确 slug** | `z-test-durable-rf-test-cable-assembly` 等 | 详情页 URL 变时间戳 slug（FRONTEND 表全部失效） | site-content-checklist.md C 节：27 |
| 125 | `payload.description` | 1-2 句卖点 + 素材来源声明 | 源材料事实（Z/P/F/A 系列规格，BRIEF.md:12-41） | demo 描述 + synthetic 声明残留 | product-payload-example.json:4 |
| 126 | `payload.specifications[{key,value}]` | 5-8 项：Capacity/Insulation/Material/Structure/Dimensions/Weight | 频率/相位/屏蔽/弯曲半径/插拔寿命/连接器等真实规格 | 规格表是 demo 保温杯参数 | product-payload-example.json:27-52 |
| 127 | `payload.media` / `mediaList` | 扁平媒体格式（见 ⑤） | 每产品 1-2 张真实图 | demo 保温杯图 | product-payload-example.json:6-21 |
| 128 | `payload.categories` / `tags` | **id 字符串数组**；categories 必须产品分类 id | 产品分类 id 数组；tags 可空 | 分类错挂 → 列表/筛选不显示 | product-payload-example.json:23-26 |
| 129 | `payload.content` | Slate，可空（空则无正文区） | 按需；只用 `p|h2|h3|blockquote` | 正文区 demo 或非法块整篇不渲染 | product-payload-example.json:22；MODULES.md:53、109-124 |
| 130 | 数量 | 美观基线 **产品 ≥3**（硬底 ≥2） | 7 | 少于 3 → 列表稀疏、related 空态（gate BLOCK） | CONTENT-MINIMUM.md:8-18 |
| 131 | 完成后核验 | `read_lists(slug,'products')` 与 COP 逐条 diff | count=7/7 | 数量不符 → audit count FAIL | RUNBOOK-ANYONE.md:99 |

---

## ⑦ 文章（含 post-detail CTA 块 + related 文案）

| # | 项 | 规则/demo 注意点 | Example 替换 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 132 | 写作管线 | 主 AI 提炼 facts → k3 系子 agent 写（BRIEF.md + article-writing-logic.md）→ 机器检查 `writing-module.py check` → flash 系子 agent 5 维评审 → READY 才发布 | 3 篇 90/90/94 分 | 事实编造/格式非法 | RUNBOOK-ANYONE.md:114-126；HANDOFF.md:22 |
| 133 | `payload.title` | buyer-intent 标题，60 字符内 | `How to Choose an RF Test Cable Assembly` 等 3 篇（BRIEF.md:43-50） | 标题无采购意图 | post-payload-example.json:3 |
| 134 | `payload.excerpt` | 1 句摘要 ≤120 字符 | 各篇摘要 | 列表卡摘要 demo | post-payload-example.json:5 |
| 135 | `payload.coverImage` | 扁平媒体格式（见 ⑤） | 每篇封面图 | demo 封面 | post-payload-example.json:7-15 |
| 136 | `payload.content`（Slate） | **原生类型只允许 `p|h2|h3|blockquote`**；每非根元素必须带 `id` + `children:[{text}]`；`heading`/`paragraph` 旧词法禁用；**禁内联 link/列表/Markdown** | 每篇 700-1100 词，h2 编号章节 ≥3（Example 主文章 h2=7） | 非法块 → 整篇正文不渲染；内联 link 平铺无 `<a>` | post-payload-example.json:16-47；MODULES.md:109-124 |
| 137 | 流程防重 | **先 `read_lists(slug,'posts')` 查 exact slug**：存在→strict review/capability→mutate_reviewed_post update；不存在→先 ISS-111 资格五步，唯一 create draft 后 reviewed update（禁止重复 create 堆积 Untitled 草稿） | — | 草稿堆积（ISS-059） | RUNBOOK-ANYONE.md:59 |
| 138 | `payload.categories/tags` | 文章分类/标签 id 数组 | `rf-testing-guides` + 文章标签 | 文章不显示在分类 | post-payload-example.json:48-49 |
| 139 | post-detail CTA 块 | 见 ③.3.7 表 #112（`cta-1` material-story-split，actionTarget `/contact-us?source=<site>-article`） | `source=example-article`，SSR 验证 1 命中/文章页 | audit cta 项 FAIL；文章无询价出口 | fix-post-cta.py:31-54；AUDIT-FACT-MATRIX-20260829.md:23 |
| 140 | post-detail related 文案 | 见 ③.3.7 表 #111（`related-1` demo "More from the journal"） | `Read next` / `More RF engineering guides` | demo 文案残留（曾漏网） | fix-post-cta.py:22-29 |
| 141 | 数量 | 美观基线 **文章 ≥4**（硬底 ≥3，related 需其它文章 ≥3） | 3（Example 3 篇 + 删 related 兜底或接受底限） | related 空态 + 列表稀疏（gate BLOCK） | CONTENT-MINIMUM.md:8-21 |

---

## ⑧ 每站审计配置（第 9 步，必做）

```bash
cp templates/site-audit-config.template.json 70_evidence/<slug>-audit-config.json
# 按该站 COP 填 pages / count / faq_answers / cta / units / required_h2
python3 site_pipeline.py audit <slug> --config <cfg> --out 70_evidence/audit-report.json
python3 site_pipeline.py gate <slug> --config <cfg>
python3 site_pipeline.py contact <slug> --config <cfg> --real "<真实电话|邮箱|地址>"
```

| # | 配置字段 | 填什么 | Example 实样 | 不改的后果 | 来源 |
|---|---|---|---|---|---|
| 142 | `pages` | 导航页 + sitemap + **全部产品 slug；所有资格通过并 published 的文章加入文章 slug** | `""`、`about-us`、`contact-us`、`products`、`sitemap.xml`、全部 `products/<slug>`；有 existing remote posts 时再加 `posts`/`posts/<slug>` | 页面漏检，或资格失败时仍误配空文章入口 | site-audit-config.template.json；ISS-102 |
| 143 | `count` | 该站实建数（**不是模板数**） | `{"products":7,"posts":3}` | 用默认 Demo 基线 3/4 → 假 FAIL（ISS-063） | site-audit-config.template.json:13；RUNBOOK-ANYONE.md:140 |
| 144 | `fallback_article` / `primary_article` | 主文章 slug | `example-guide-slug-assembly` | h2 语义检查抓错页 | site-audit-config.template.json:14-15 |
| 145 | `faq_answers` | 文章**必须 SSR 的实质事实短语**（非 FAQ 模块问题） | `["phase stability","67 ghz","vswr","request a quote"]` | 用默认皮筏艇短语 → 4/4 假 FAIL | site-audit-config.template.json:16-21；AUDIT-FACT-MATRIX-20260829.md:22 |
| 146 | `cta.product_link` / `cta.consult_source` | 真链接 + source 归因 | `/contact-us?source=example-article` / `source=example-article` | cta 项按默认站判定 → 假 FAIL | site-audit-config.template.json:22-25；example-audit-config.json:22-25 |
| 147 | `units` | 该站计量单位清单；**没有就显式 `[]` 跳过**（三态 bug 已修） | `[]`（GHz/mm 非米制基线） | 空 units 曾因 `\b()\b` 正则假 FAIL（ISS-064） | site-audit-config.template.json:26；HANDOFF.md:41 |
| 148 | `template_words_extra` / `demo_contacts_extra` | 追加客户特有 demo 词 | `{}` | 新增 demo 词漏检 | site-audit-config.template.json:27-28 |
| 149 | `required_h2` | 主文章最少原生 h2 数 | `3`（Example 实测 7） | h2 语义检查基线错 | site-audit-config.template.json:29 |

---

## ⑨ set_home_page（根路径 `/` 的唯一天花板开关）

| # | 项 | 规则 | 不改的后果 | 来源 |
|---|---|---|---|---|
| 150 | 调用 | `api.set_home_page(slug, site_id, theme_id, home_page_id)`；**URL 必须是 `/{slug}/themes/{themeId}`**（`/{slug}/themes` 返回 200 但静默无效） | 根路径 200 但 `Allin CMS Runtime` 错误壳（__next_error__ + noindex） | allincms_api.py:390-397；ROOT-PATH-ISSUE.md:61-62 |
| 151 | **顺序** | `createTheme(default) → 写 7 页内容(save+publish) → apply_theme_routes → setThemeActive → set_home_page（必须最后）`；**setThemeActive 是唯一清空 homePageId 的操作**，任何未来重新激活主题后都要重跑 set_home_page | 顺序反了 → 激活清掉 homePageId → 根路径回到错误壳 | OUTSIDER-REVIEW-20260830-SETHOME-ADVERSARIAL.md:29-32；ROOT-PATH-ISSUE.md:63 |
| 152 | 验证 | 状态 readback 三字段 `theme.homePageId + homePagePublished + page.isHome` 齐备 + `curl /` 无 `__next_error__`（对抗矩阵实测：改首页内容/重绑路由/启停页面都不破坏绑定） | 只看 200 会被静默无效骗过 | OUTSIDER-REVIEW-20260830-SETHOME-ADVERSARIAL.md:18-25、45 |
| 153 | action id 漂移 | 42 位 action id 绑定部署；平台升级后跑 `WS_TOKEN=$WS_TOKEN python3 scan/scan-actions.py - /<site_key>/themes/<themeId>` 重扫 | 旧 id 失效 → 静默失败 | RUNBOOK-ANYONE.md:24；OUTSIDER-REVIEW-20260830-SETHOME-ADVERSARIAL.md:38 |

---

## ⑩ demo 种子清理（createTheme 会重种，每次重建主题后必跑）

| # | 项 | 规则 | 不改的后果 | 来源 |
|---|---|---|---|---|
| 154 | 触发条件 | **`createTheme(preset='default')` 每次都会重新种入 3 demo 产品 + 3 demo 文章**（站点级新记录，id 时间戳=创建时刻） | 产品/文章列表与首页自动拉取块混入 demo 条目（DEMO-CLEANUP.md:30） | RUNBOOK-ANYONE.md:60（ISS-071） |
| 155 | 产品 slug 清单（3） | `modular-packing-pouch`、`stackable-desk-tray-set`、`waxed-canvas-weekender`（对应名：Modular Packing Pouch / Stackable Desk Tray Set / Waxed Canvas Weekender） | 用 `read_lists(slug,'products')` 按 slug 取 id → `delete_product`；**产品 slug 以 read_lists 实读为准（seed 版本可能有变体）** | demo 产品在首页 showcase/列表页可见 | DEMO-CLEANUP.md:18-20 |
| 156 | 文章 slug 清单（3） | `small-entryway-system`、`material-care-buying-decision`、`choose-a-weekender-bag`（对应名：A Small Entryway System / Why Material Care Belongs / How to Choose a Weekender Bag） | 同上 → `delete_post` | demo 文章在首页 news 块/列表页可见 | DEMO-CLEANUP.md:19 |
| 157 | 清理时机 | 每次 create_theme 后重跑 + audit count 项（基线=实建数）自动暴露残留 | 删后 `read_lists` 再核 0 残留 | 重建主题反复复活 demo | RUNBOOK-ANYONE.md:60 |
| 158 | 第二波漏网点（不止删记录） | ① post-detail `related-1` 文案 ② posts 页 `page-header-1`/`recommendations-1` 文案 ③ 浮动 WhatsApp 按钮（ISS-068 实测 4 处漏网） | 全部替换/删除（见 ③ 表 #111/#106/#109/#28） | 记录删了文案还在 → audit template 项 FAIL | HANDOFF.md:27；AUDIT-FACT-MATRIX-20260829.md:20 |
| 158a | **demo taxonomy 清理（6 分类+7 标签，ISS-074）** | demo 分类（posts：Buying Guides/Material Notes/Home Routines；products：Daily Carry/Home Goods/Travel Essentials）与 demo 标签（posts：Buying Guide/How To/Material Focus；products：Buying Guide/Gift Pick/Material Focus/New Arrival）**同样由 createTheme 种入且 0 引用** | 按名字删：`api.delete_category(slug,sid,id,'posts'/'products')` / `api.delete_tag(...)`（id 从 read_lists 的 categoryOptions/tagOptions 按名字取）；`python3 delete-demo-content.py <slug>` 已内置全链（产品+文章+分类+标签） | 列表页筛选下拉出现可点出 0 结果的 demo 分类（ISS-074 实测公开可见） | issues.tsv ISS-074；DEMO-CLEANUP.md 四轮节 |

---

## ⑪ 平台 BLOCK 记录（交付清单"已知事项"照抄，不判站内 FAIL）

| # | BLOCK | 现象 | 回落 | 来源 |
|---|---|---|---|---|
| 159 | — | 已按 ⛔ 禁令移除（平台层项不再设字段） | — | — |
| 160 | — | 已按 ⛔ 禁令移除（平台层项不再设字段） | — | — |
| 161 | — | 已按 ⛔ 禁令移除（平台层项不再设字段） | — | — |
| 162 | 页面 SEO description（meta） | 模板句（如 "A journal listing page..."）；**静态页可改**：api.update_page(description=)→等10s→commit publish 带 description 字段→curl 验证（ISS-073）；动态路由页（/posts/{post}、/products/{product}）回退模板值=平台限制 | 静态页逐页换品牌文案；动态页记录；audit 已排除 meta 层判定（ISS-066） | RUNBOOK-ANYONE.md:151 |
| 163 | 正文内联链接 | `{"type":"link"}` 平铺无 `<a>` | 用页面级块 actionTarget（③.3.7 #112） | RUNBOOK-ANYONE.md:150；MODULES.md:120 |
| 164 | 空字段 zod 默认回填 | 置空字符串被 schema default 顶回 demo 值（如 WhatsApp wa.me/+44-7911-123456） | 删元素而非置空（ISS-068） | RUNBOOK-ANYONE.md:152 |
| 165 | 表单提交 | 平台表单链路（未实测端到端） | 交付清单如实写，demo 邮箱上线前必须换真并浏览器实提 | RUNBOOK-ANYONE.md:153；delivery-manifest.md:52 |
| 166 | 根路径 `/`（历史 BLOCK，**已可修**） | 200 但错误壳 | `set_home_page`（⑨）；audit 含 root-home 项防回归 | RUNBOOK-ANYONE.md:146；ROOT-PATH-ISSUE.md:48-70 |

---

# 服务端回填规则（单独成节，提交前必背）

> 结论（MODULES.md:7 原文）：props 中**未提供的字段**会被服务端用该模块的**模板默认值**回填（含模板文案/假链接）。对抗原则：**可显示字段全部显式传**（可传空数组/空串）；提交后必 readback 深度 diff，只允许 `columnCount=N` 这类无害回填；`formSlug=""` 出现在带表单的块=表单断裂（ISS-076），必须补真实 slug。

| 场景 | 缺省/置空时的服务端行为 | 实测出处 |
|---|---|---|
| props 字段整体省略 | 用该模块模板默认值回填（含模板文案/假链接） | MODULES.md:7 |
| `hero-commerce.campaignPills` 不传 | demo 药丸（`12h hot · 24h cold` 等）复活 | MODULES.md:7、19 |
| `contact-info-grid.socialLinks` 不传 | 回填 Instagram/LinkedIn 假链接（**注意：footer `socialLinks` 空 `[]` 是安全的留白**） | MODULES.md:7、46、105 |
| header `navigation[].children` 丢弃 | 回填 demo "Bags" 子菜单 | MODULES.md:7 |
| `social-floating-button.url` 置空串 | zod 默认值顶回 `wa.me/+44-7911-123456`（demo 英国号） | RUNBOOK-ANYONE.md:58；MODULES.md:107 |
| `contact-info-grid` / `location-map-interactive` 用错字段名（如 `emailLabel` 等自定义字段） | 服务端忽略并回填 San Francisco demo 联系方式（"demo 复活"） | DEMO-CLEANUP.md:28-30 |
| `contact-form-split.formSlug` 缺省 | 回填 `""`——**会致表单不渲染，必须显式填真实 slug**（ISS-076 修正旧"无害"结论） | ISS-076；MODULES.md:7、28 |
| `columnCount` / `fit` 等布局字段缺省 | 回填模板默认布局值（无害白名单） | MODULES.md:7 |
| `updateThemeAction` 额外字段 | zod 剥离（homePageId 等传不进去） | allincms_api.py:367 |
| `apply_theme_routes` 传 `"/"` 路由 | server 拒绝 `Route "/" does not exist` | allincms_api.py:361 |

**操作守则**：
1. 写之前先 `read_page_document` 拿真实 doc/globals，**在原结构上改，不要凭空重建**（blocks 重建 == 线上 doc 才安全，MODULES.md:3）。
2. 每个可显示字段显式给值：文案给客户文案、无内容的数组给 `[]`、无社媒给 `[]`。
3. 想"去掉某元素"= **删 `elements.<key>` + 删 `page-root.children` 引用**（fix-remove-wa.py:21-23），不是置空。
4. 每次 `save+publish` 后 `read_page_document` readback **深 diff**：只允许 `columnCount=N` 无害回填；`formSlug=""` 在表单块=断裂必修（ISS-076）；出现任何 demo 文案/假链接 = 按上表修。

---

# 【新站开工 20 分钟自检表】（建完站后逐项打勾）

> 前置：`export WS_TOKEN=<token>`（推荐）；`SLUG=<site_key>`；`BASE=https://<slug>.web.allincms.com`；`CFG=70_evidence/<slug>-audit-config.json`；`cd <interface-kit>`。

| ☐ | 检查项 | 命令 | 期望结果 |
|---|---|---|---|
| ☐ | 1. 站点+主题收敛 | `python3 -c "import sys;sys.path.insert(0,'.');from allincms_api import AllinCMS;import os;a=AllinCMS(token=os.environ['WS_TOKEN']);print(a.read_themes('$SLUG'))"` | 仅 1 个 active 主题；`homePageId` 非空、`homePagePublished=True` |
| ☐ | 2. 根路径渲染 | `curl -s $BASE/ \| grep -c "__next_error__"` | 输出 `0`；且 `curl -s $BASE/ \| grep -o "<title>[^<]*</title>"` 含站名 |
| ☐ | 3. 全路径 200 | `for p in "" about-us contact-us posts products sitemap.xml; do echo -n "/$p "; curl -s -o /dev/null -w "%{http_code}\n" $BASE/$p; done`（产品/文章详情逐条同查） | 全部 `200`，错误壳 0 |
| ☐ | 4. demo 种子清理 | `python3 -c "...;print([x.get('slug') for x in a.read_lists('$SLUG','products')['data']]);print([x.get('slug') for x in a.read_lists('$SLUG','posts')['data']])"` | 无 `modular-packing-pouch`/`stackable-desk-tray-set`/`waxed-canvas-weekender`/`small-entryway-system`/`material-care-buying-decision`/`choose-a-weekender-bag` |
| ☐ | 5. 模板词+空态扫描 | `python3 site_pipeline.py gate $SLUG --config $CFG` | gate 全 PASS；`northstar\|weekender\|555-0142\|mission street\|wa.me\|instagram.com` 0 命中（MODULES.md:142-143） |
| ☐ | 6. 联系方式门 | `python3 site_pipeline.py contact $SLUG --config $CFG --real "<真实邮箱|电话|地址>"` | `[contact] PASS`（无 demo 联系方式残留） |
| ☐ | 7. 完整审计 | `python3 site_pipeline.py audit $SLUG --config $CFG --out 70_evidence/audit-report.json` | `"verdict": "PASS"`，problems 为空（13 项站内检查全过） |
| ☐ | 8. globals 7 页一致 | 对 7 页循环 `read_page_document`，比对 `page['globals']` 的 header/footer JSON | 7 页 globals 完全相同（demo 文案 0） |
| ☐ | 9. readback 深 diff | 每页 `save+publish` 后重读 document 与提交版 diff | 仅 `columnCount=N` 无害回填；`formSlug=""` 在表单块=断裂必修（ISS-076） |
| ☐ | 10. 文章 CTA SSR（create/update published 文章） | `curl -s $BASE/posts/<primary_article> \| grep -c "source=<site>-article"` | ≥1 命中；仅当前部署资格验证失败并留证时本项 N/A 且 Posts 模块/入口移除 |
| ☐ | 11. sitemap 覆盖 | `curl -s $BASE/sitemap.xml` | 含全部远程实建产品；仅 existing reviewed-update 文章才含文章 slug；含根路径 `/` 条目 |
| ☐ | 12. 交付清单 | 复制 `templates/delivery-manifest.md` → `70_evidence/DELIVERY-<slug>-<date>.md`，公开链接表逐行核 200 + 已知事项抄 ⑪ | 每行核验=200；BLOCK 如实记录 |

---

# 最容易漏的 5 项（历史返工实证）

1. **globals 只改了 1 页**：globals 按页存储，只 commit 首页 = 其余 6 页 header/footer 还是 demo（RUNBOOK-ANYONE.md:92）。Example 靠"同一份 globals_doc 对 7 页逐页 save+publish"才清干净。
2. **置空当删除**：把 WhatsApp `url` 置 `""` 会被 zod 回填 `wa.me/+44-7911-123456`（ISS-068）。必须删元素（children+elements 同删，fix-remove-wa.py）。
3. **set_home_page 顺序**：`setThemeActive` 会清空 homePageId；必须先激活再设首页，且未来每次重新激活后重跑（OUTSIDER-REVIEW-20260830-SETHOME-ADVERSARIAL.md:24）。
4. **createTheme 重种 demo**：每次 `create_theme(default)` 都重种 3 产品+3 文章；重建主题后不重跑清理 → 首页自动拉取块混入 demo（RUNBOOK-ANYONE.md:60）。
5. **audit 不带 --config**：默认 Demo 基线会对新站 count/faq/cta 产生假 FAIL，诱使返工已对的项（ISS-063）。

---

# 来源索引（文件:行号）

| 文件 | 用到的关键行 |
|---|---|
| ../RUNBOOK-ANYONE.md | L37-49（10 步）、L51-62（关键事实）、L64-93（§3 主题页）、L101-110（§5/§6）、L128-140（§8 审计）、L142-153（§9 BLOCK）、L155-161（§10 交付） |
| ../MODULES.md | L4-7（element 结构 + 回填规则）、L9-10（37 块注册表）、L14-61（页面块字段）、L63-99（嵌套子结构）、L101-107（globals 块）、L109-124（Slate 矩阵）、L126-132（发布接口）、L141-143（模板词） |
| interface-kit/templates/home-page-example.json | L10-22（children）、L25-504（11 块 props）、L506-690（globals） |
| interface-kit/templates/about-page-example.json | L11-145（5 块 props） |
| interface-kit/templates/contact-page-example.json | L11-112（4 块 props） |
| interface-kit/templates/product-payload-example.json | L1-53（全字段） |
| interface-kit/templates/post-payload-example.json | L1-50（全字段 + Slate 规范） |
| interface-kit/templates/site-audit-config.template.json | L1-30（每站基线） |
| interface-kit/templates/delivery-manifest.md | L13-55（交付结构） |
| interface-kit/templates/site-content-checklist.md | A-J 节（内容映射/防漏） |
| interface-kit/templates/CONTENT-MINIMUM.md | L8-21（数量基线）、L37-39（降级） |
| interface-kit/templates/client-input-checklist.md | L7-17（必填资料） |
| interface-kit/allincms_api.py | L263（create_site）、L273-283（分类/标签）、L285-297（媒体）、L299-320（产品/文章）、L322-333（read_themes）、L345-364（主题操作）、L390-397（set_home_page）、L405-409（save_home） |
| <task_dir>/HANDOFF.md | L18-29（完成清单）、L30-35（前端状态）、L37-42（审计结论）、L44-53（ISS 修复） |
| <task_dir>/70_evidence/DEMO-CLEANUP.md | L4-30（globals/doc/demo 清理 + 平台行为） |
| <task_dir>/70_evidence/AUDIT-FACT-MATRIX-20260829.md | L15-37（15 项分级） |
| <task_dir>/70_evidence/ROOT-PATH-ISSUE.md | L48-70（setHomePageAction 终局） |
| <task_dir>/70_evidence/OUTSIDER-REVIEW-20260830-SETHOME-ADVERSARIAL.md | L18-32（对抗矩阵+顺序）、L45（验证判据） |
| <task_dir>/70_evidence/FRONTEND-STATUS.md | L4-20（全路径 title 表） |
| <task_dir>/70_evidence/BLOCK-media-upload.md | L3-4（上传通道结论）、L21（分类/标签实样） |
| <task_dir>/70_evidence/example-audit-config.json | L3-29（每站配置实样） |
| <task_dir>/70_evidence/scripts-*/fix-post-cta.py | L22-54（related 文案 + CTA 块完整样例） |
| <task_dir>/70_evidence/scripts-20260830/fix-remove-wa.py | L21-23（删元素正确姿势） |
| <task_dir>/70_evidence/scripts-20260830/fix-posts-page.py | L21-38（posts 页块替换） |
| <task_dir>/70_evidence/scripts-20260830/fix-globals-wa.py | L21-33（置空方案 → 被删元素方案取代） |
| example/20_work/articles/BRIEF.md | L5-9（公司事实）、L12-41（产品规格）、L43-50（文章主题） |
| 公网实测（编写时抓取） | https://<your-site-key>.web.allincms.com/、/about-us、/contact-us（header/footer/首页各块/联系页/关于页实值） |

> 版本：2026-08-30。新坑回填路径：interface-kit/issues.tsv + `index/registry_tools.py verify`（RUNBOOK-ANYONE.md:161）。
