---
title: "AllinCMS 单页模块规范（Blocks Library）—— 设计师用内容区块全集"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（MODULES.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["README.md"]
---

# AllinCMS 单页模块规范（Blocks Library）—— 设计师用内容区块全集

来源：设计器 document.elements（实测抓取）+ 对抗验证（blocks 重建 == 线上 doc，结构同构） + 编辑器 chunk 注册表 + 多站模板文档并集 + **公网渲染截图核实（前端显示映射）**。
每个模块 = document.elements 里一个 key（如 `hero-commerce-1`），value 必有 `type` + `props` + `children` + `anchorId`。
页面发布 = commitEditorSessionAction({pageDocument:{root,elements},globals,themeConfig})。

> **服务端回填规则（重大坑，2026-08-29 实测）**：props 中**未提供的字段**会被服务端用该模块的**模板默认值**回填（含模板文案/假链接，如 hero 的 campaignPills、contact-info 的 socialLinks Instagram/LinkedIn、header 导航 children 丢弃后回填 "Bags"）。对抗原则：**可显示字段全部显式传**（可传空数组/空串）；提交后必 readback 深度 diff，只允许 columnCount=N 这类无害回填；**formSlug="" 在表单块=整个 <form> 不渲染（ISS-076/077 实测），必须绑站点真实表单 slug**。

> **网格列数=条目数规则（ISS-107，2026-09-02 实测）**：所有带 `columnCount` 的网格模块（category-showcase-grid/feature-grid-proof/social-proof-quotes/company-stats-grid/company-values-grid/company-team-grid 等）按 columnCount **固定生成 N 列，条目不足不折叠不报错** → 末列/右侧渲染纯空白卡或半幅空白（实测 3 列填 2 行=空白第三卡、4 列填 2 卡=右半幅 540px 空白）。提交前必须 `columnCount == len(items/proofRows/reviews/stats/values)`，要么改列数要么补齐条目。**大标题规则**：hero-commerce 等大字号标题固定 72px 不随列宽缩放，长标题会在 ~426px 窄列堆 6 行，且连字符首词（如 "Wall-mounted"）被断成孤儿行 "Wall-"——标题避免连字符词开头、控制在 ~42 字符内。**模板固有行为（登记不硬改）**：hero 左列 content-between 中段空隙、产品卡 line-clamp 描述截断、奇数卡末行空位、吸顶导航 bg-background/95 半透明（滚动截图时底下内容 5% 透出=鬼影，勿误判重叠 bug）。

> **客户端块注册表全集（37 种，2026-08-30 从 workspace 设计器 bundle 提取，权威）**：
> `header-card, header-dropdown, carousel-campaign, page-header-card, contact-header-summary, category-showcase-grid, breadcrumb-inline, hero-commerce, about-intro-media, company-story-media, company-team-grid, company-stats-grid, company-values-grid, contact-info-grid, location-map-interactive, logo-cloud, image-gallery, video-section, faq-accordion, feature-grid-proof, social-floating-button, contact-dialog-form-modal, contact-form-split, featured-product-list-showcase, recommended-product-list-grid, full-product-list-filtered, material-story-split, social-proof-quotes, newsletter-inline, product-detail-gallery, product-related-grid, featured-news-list-editorial, recommended-news-list-grid, full-news-list-filtered, post-detail-article, post-related-grid, footer-columns`

## 一、页面区块（page-root 的 children 可用，20 种 = 13 主模块 + 3 公司页 + 4 联系页/辅助）

### A. 首页/商城主模块（13 种）
| type | 用途 | 关键字段 | 前端显示（实测截图） |
|---|---|---|---|
| carousel-campaign | 轮播主视觉 | slides[]（见下）, serviceItems[] | 顶通栏大图轮播；下方 2-3 项服务条（icon+标题+描述） |
| category-showcase-grid | 分类卡片网格 | sectionLabel, headline, supportingCopy, items[], columnCount | 标题+副标右侧；N 列图卡（图+名称+描述+箭头） |
| hero-commerce | 商品 Hero | eyebrow, title, description, secondaryNote, media, fit, mediaCaption, mediaKicker, mediaMeta, productName, productDescription, productPriceLabel, **actions[], serviceItems[], campaignPills[]** | 左文案+右图；图下规格面板（name/desc/price 卡）；左下 3 项服务列表；右信息药丸 pills（label+value） |
| feature-grid-proof | 特性网格 | eyebrow, heading, description, proofRows[], columnCount | N 列卡（label 编号/标题/描述/meta + 左下 action 链接） |
| featured-product-list-showcase | 精选产品列表 | sectionLabel, headline, supportingCopy, merchandisingNote, ctaLabel, ctaTarget, productActionLabel, featuredProductActionLabel, fit, associatedListPage, associatedDetailPage, **categorySlug（空串=显示全部产品；只接受分类 slug——误填产品 slug 会整区空态，2026-09-04 双机实战）**, sortOrder | 标题区+CTA 按钮；特色产品大卡（图+标签+名称+价格+按钮） |
| full-product-list-filtered | 全产品筛选列表 | associatedDetailPage, pageSize, showToolbar, sortOrder, columnCount, productActionLabel, fit | 筛选工具栏+产品网格 |
| material-story-split | 材质故事分栏 | sectionLabel, headline, supportingCopy, media, fit, notes[], actionLabel, actionTarget | 左图右文（或交替）；notes 列表项；底部 action 链接 |
| social-proof-quotes | 用户评价 | sectionLabel, headline, ratingLabel, reviews[], columnCount | 评分星标+平均分；N 列评价卡（quote+name+detail） |
| featured-news-list-editorial | 精选文章 | sectionLabel, headline, supportingCopy, digestLabel, featureLabel, ctaLabel, ctaTarget, associatedListPage, associatedDetailPage, categorySlug, sortOrder, fit, postActionLabel, featureActionLabel | 特色文章大卡+列表卡 |
| faq-accordion | FAQ 手风琴 | sectionLabel, headline, supportingCopy, supportNote, items[] | 问答手风琴 |
| newsletter-inline | 订阅条 | sectionLabel, headline, supportingCopy, emailPlaceholder, submitLabel, finePrint | 订阅行（输入+按钮+细则） |
| contact-form-split | 联系表单分栏 | eyebrow, title, description, responseTitle, responseDescription, emailLabel, emailValue, phoneLabel, phoneValue, addressLabel, addressValue, hoursLabel, hoursValue, formCardEyebrow, formCardTitle, formCardDescription, **formSlug（必填真实 slug，缺失=公网只渲染表单卡外壳 0 个 <form>，ISS-110；builder contact_split 已带默认 contact-inquiry）** | 左联系卡（email/phone/office/hours）+右表单卡 |
| product-comparison（chunk 注册） | 产品对比表 | -（对比表格） |
| header-card（chunk 注册） | 页头卡 | -（辅助区块） |

### B. 公司页模块（3 种，About 页标准组件）
| type | 用途 | 关键字段 | 前端显示 |
|---|---|---|---|
| about-intro-media | 公司简介 | eyebrow, title, description, body, media, fit:"cover", caption | 左文右图；图下 caption 小字说明 |
| company-story-media | 公司故事 | sectionLabel, headline, lead, body, media, fit, **note, noteLabel** | 左图右文；底部 note 引述块（noteLabel 为标签） |
| company-stats-grid | 数据指标 | sectionLabel, headline, description, stats[{value,label,description}], columnCount | 数字大标题+label+描述（N 列） |
| company-values-grid | 价值观 | sectionLabel, headline, description, values[{title,description}], columnCount | 标题卡网格（N 列） |
| company-team-grid | 团队 | sectionLabel, headline, description, members[{name,role,bio,photo}], columnCount, photoFit | 成员卡（头像占位/initials+姓名+角色+简介） |

### C. 联系页模块（4 种，Contact 页标准组件）
| type | 用途 | 关键字段 | 前端显示 |
|---|---|---|---|
| breadcrumb-inline | 面包屑 | {}（空 props） | "Home / 当前页" 顶部导航 |
| contact-header-summary | 联系页头 | eyebrow, title, description, items[{label,value}] | 左标题右 2-3 项 key-value |
| contact-info-grid | 联系信息 | sectionLabel, headline, description, items[{type:email\|phone\|address, label, value, detail}], columnCount, **socialLinks[{label,href}]（必须显式传，默认空！）** | 3 卡（Email/Phone/Office 卡片带图标） |
| location-map-interactive | 地图 | sectionLabel, headline, address, description, latitude, longitude, zoom, mapMode("m"), url, details[{label,value}] | 地图区（tile 加载依赖外部地图服务，可能显示占位灰块）+地址/细节列表 |
| contact-form-split | 联系表单 | 同 A 组 contact-form-split | 分栏表单 |

### D. 模板页/详情页/列表页模块（8 种，页面 path 自动渲染，document 可编辑）
| type | 用途 | 关键字段 | 注意（对抗经验） |
|---|---|---|---|
| product-detail-gallery | 产品详情 | specificationsHeading, fit | 正文区渲染记录 content（空则无正文区） |
| post-detail-article | 文章详情 | fit | 正文渲染 Slate content（原生 p/h2/blockquote 已验证） |
| product-related-grid | 产品详情相关区 | sectionLabel, headline, supportingCopy, pageSize, columnCount | **目录只有一个产品时显示空态 "No content is available yet."——删该模块或补产品** |
| post-related-grid | 文章详情相关区 | 同上 | 同上（文章 <2 时空态） |
| page-header-card | 列表页头 | eyebrow, title, description, kicker | 模板默认文案需替换 |
| full-news-list-filtered | 文章列表 | pageSize, showToolbar, sortOrder, columnCount, postActionLabel, associatedDetailPage | 列表数据自动 |
| full-product-list-filtered | 产品列表 | 同上（productActionLabel） | 列表数据自动 |
| recommended-product-list-grid | 列表页底推荐产品 | sectionLabel, headline, supportingCopy, associatedDetailPage | 产品不足时也可能空态 |
| recommended-news-list-grid | 列表页底推荐文章 | 同上 | 同上 |

## 二、嵌套子结构
### slides[]（carousel-campaign）
`{eyebrow, title, description, media:{type:"image",value:{name,type:"image",source:"url",url}}, fit:"cover", showMask:bool, price, product, primaryLabel, primaryTarget:{type:"custom",href}, secondaryLabel, secondaryTarget:{type:"custom",href}}`
### serviceItems[]（carousel-campaign）
`{icon:"truck"|"shield", title, description}`
### items[]（category-showcase-grid）
`{name, description, media:{...}, fit, target:{type:"custom",href}}`
### proofRows[]（feature-grid-proof）
`{label, title, description, meta, actionLabel, target:{type:"custom",href}}`
### notes[]（material-story-split）
`{title, description}`
### reviews[]（social-proof-quotes）
`{quote, name, detail}`
### items[]（faq-accordion）
`{question, answer}`
### stats[]（company-stats-grid）
`{value, label, description}`
### values[]（company-values-grid）
`{title, description}`
### members[]（company-team-grid）
`{name, role, bio, photo:null|media}`
### contact header items[]（contact-header-summary）
`{label, value}`
### contact info items[]（contact-info-grid）
`{type:"email"|"phone"|"address", label, value, detail}`
### map details[]（location-map-interactive）
`{label, value}`
### hero actions[]（hero-commerce）
`{label, target:{type:"custom",href}, variant:"solid"|"outline"}`
### hero serviceItems[]（hero-commerce）
`{label, value}`
### hero campaignPills[]（hero-commerce）
`{label, value}`
### 通用 target
`{type:"custom", href:"/products"}` 或 `{type:"action", anchorId:"contact-form-dialog"}`
### 通用 media
`{type:"image", value:{name, type:"image", source:"url", url:需要扩展名}}`

## 三、全局区块（globals.elements，站点级共享——**按页存储**，改一次需对全部 7 页重交）
| type | 用途 | 关键字段 | 前端显示 |
|---|---|---|---|
| header-dropdown | 站点头部导航 | siteTitle, tagline, logoMedia, logoFit, logoTarget, navigation[{label,target,children[]}], ctaLabel, ctaTarget | 顶栏：品牌+导航（可下拉）+CTA 按钮 |
| footer-columns | 页脚 | brand, kicker, description, columns[{title,links[{label,target}]}], socialLinks[{label,target}], copyright, systemNote | 品牌区+N 列链接+版权细则；socialLinks 空则社交区留白 |
| contact-dialog-form-modal | 联系弹窗 | title, description, eyebrow, closeLabel, formSlug:"contact-inquiry", **anchorId（必须设置且与 header 的 cta_anchor 一致，null 时公开站静默丢弃整树——ISS-094）** | 全站 CTA 弹出表单 |
| social-floating-button | 社交悬浮钮 | brand:"whatsapp", url, label, showLabel, position:"bottom-right" | 右下角绿色浮钮 |

## 三·五、正文富文本支持矩阵（Slate，2026-08-29 终版 —— article 区精确检测法；2026-08-30 词法统一）

> **类型词法**：服务器原生存储 = `p|h2|h3|blockquote`（read_post 实测）；`paragraph` 为旧词法（输入兼容、writing-module 归一化为 p），`heading` 禁用。
> **检测方法必须用 `<article>` 正文区**（全局计数会被 footer/RSC 干扰——曾误判 heading）；**单块隔离测试**（混合非法块会让整篇正文不渲染，fmt5 实证）。
| 块/标记 | 写法 | 前端渲染 | 可用 |
|---|---|---|---|
| p（段落） | {"type":"p","children":[{"text":"…"}]} | 文本流（div.slate-p） | ✅ |
| 加粗 | {text,bold:true} | `<strong>` | ✅ |
| 斜体/下划线 | {text,italic/underline:true} | `<em>/<u>` | ✅ |
| ~~callout~~ | {"type":"callout","children":[{"text":"…"}]} | 组件自带 💡 图标不可控 | ❌ **已弃用**（纯文本标签段替代；见 FORMAT-SPEC 四） |
| **h2/h3（原生类型）** | {"type":"h2"\|"h3","children":[{"text":"…"}],"id":"..."} | **slate-h2/slate-h3 样式class生效**（text-2xl font-semibold tracking-tight） | ✅ 用原生 h2 做标题（勿用 heading） |
| link | {"type":"link","url":...} | **无 `<a>`**（平铺） | ❌ 正文禁内联链接 |
| **blockquote（包裹结构）** | {"children":[{"type":"p","children":[{"text":"…"}]}],"type":"blockquote","id":"..."} | **slate-blockquote border-l-2 pl-6 italic 生效** | ✅ 原生包裹结构 |
| bulleted-list / numbered-list / quote / divider / table / code / checklist / todo / embed / video / toc | 同上 | 列表/其余仍平铺或异常 | ❌ 禁用 |

**美学排版工具（平台内）**：空段落=段落间距 · **原生 h2=章节标题**（勿用 heading）· callout 已弃用（标签段替代）· 数字加粗=强调 · **内链=卡组件**（related 推荐/导航/模块 target）——正文不得使用 Markdown、不得期待标题/链接语义。

## 四、发布/更新接口（单页模块使用入口）
- 读写：POST `/{slug}/themes/{themeId}/{pageId}/design`，next-action=commitEditorSessionAction `7ff107025e28118dfb6d8f0da06b3ae64fb0ed74b3`
- payload `{siteId,themeId,pageId,intent:"save"|"publish",pageDocument,globals,themeConfig}`
- 实测：curl 直调可行（无需浏览器）！save→{data:{intent:"save"}}, publish→完整 flight
- **globals 按页存储**：页面 commit 只更新该页 globals 引用；要全站统一需对每页重交（readpages 列 7 页；用 readback 拿各页 document 原样回传 + 新 globals）
- themeId/pageId 获取（纯接口）：`GET /{slug}/themes/{themeId}?_rsc` → `pages[]`（含 id/path/isHome）；或用 `allincms_api.py read_pages()`
- 读回 document/globals/themeConfig（纯接口）：`GET /{slug}/themes/{themeId}/{pageId}/design?_rsc` → `initialPayload.page.{document,globals,themeConfig}`（`allincms_api.py read_page_document()`）；写后用同路径读回即对抗验证

## 五、模块库分类（Blocks 面板）
Navigation → header/footer/breadcrumb；Heroes → hero-commerce；Campaigns → carousel-campaign；
Catalog → category-showcase-grid/full-product-list-filtered；Products → featured-product-list-showcase；
Articles → featured-news-list-editorial；Media → 媒体展示；Story → material-story-split/company-story-media；
Company → about-intro-media/company-stats-grid/company-values-grid/company-team-grid；
Proof → feature-grid-proof/social-proof-quotes；Forms → contact-form-split/contact-header-summary/contact-info-grid/location-map-interactive/newsletter-inline/faq-accordion

## 六、文案模板词自检（上线前必跑）
- 词表（真源=site_pipeline.py TEMPLATE_WORDS，38 词 + DEMO_CONTACTS 9 项，以代码为准勿手抄）：northstar / buildnbuzz / 555-0142 / mission street / weekender / maya / packing pouch / desk tray / more from the journal / keep readers moving / commerce editorial / materials and care / built to age / waxed canvas / brushed steel / recycled fiber / shop new arrivals / guides for choosing / buying guides, material / material notes / stories and guides / explore by topic / featured in our journal / popular pieces / routines, repairs / products to pair / follow us / field notes 等；联系方式另有 wa.me/+44-7911-123456、hello@demo-demo.com 等。扫描须过滤 style/script/meta 标签后判定
- 站点级 globals 也必须扫描（footer socialLinks 易残留模板假链接）
