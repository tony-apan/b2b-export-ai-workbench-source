---
source_doc_id: "ID-0002"
title: "Article Page Frontend SEO Contract"
description: "定义正式文章页从语言、canonical、结构化数据到移动端、图片和发布后源码验收的前端 SEO 合同。"
type: "page"
status: "Working"
owner: "AI"
created: "2026-07-31"
last_updated: "2026-08-02"
sources: ["b2b-seo-article-standard.runtime.md", "../40_outputs/index.md", "index.md"]
related: ["index.md", "b2b-seo-article-standard.runtime.md", "../TEMPLATES/article-quality-review.md", "../TEMPLATES/publish-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要实现、审查或验收正式文章详情页的技术 SEO、语义 HTML、图片、移动体验和索引资格时。"
keywords: ["frontend SEO", "article page", "canonical", "structured data", "semantic HTML"]
generated_from: "../../PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md"
generated_source_sha256: "c706b0ee8eba8983d2ee5181080c171b79a42e919f9d1bf51a39ea36d0f3cbc1"
generated_by: "scripts/sync-workspace-template.mjs"
---
<!-- Generated runtime projection from PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md; canonical edits belong in the core package. -->
# Article Page Frontend SEO Contract

## 结论

正式文章是否“内容写得好”与页面是否“能正确索引、理解和使用”是两套独立合同。CMS API 返回成功不能证明 HTML、canonical、schema、图片、移动端或 sitemap 正确。

本合同是平台无关的目标状态。具体 CMS/主题是否支持、如何配置和有哪些限制，必须由对应 Adapter 和当前部署实测决定。

## 1. 索引资格矩阵

| 页面目的 | robots | sitemap | 推荐/相关文章 | 要求 |
|---|---|---|---|---|
| 正式买家文章 | `index,follow` 或未阻止 | 应进入 | 可以 | 内容与本合同全部通过 |
| 草稿/预览 | `noindex,nofollow` 或不可公开 | 不进入 | 不进入 | 仅供内部验收 |
| QA / Format Lab | `noindex,nofollow` | 不进入 | 不进入 | 不得污染买家内容路径 |
| 重复/替代页 | 按迁移策略 | 通常不进入 | 不进入 | canonical/redirect 指向唯一页面 |

`noindex` 不是隐藏敏感内容的安全措施；私有内容必须使用权限隔离。

## 2. Document 与语言

必须检查：

- `<html lang>` 与正文主语言和目标 locale 一致；
- 页面字符集和 viewport 正确；
- title、meta description 与页面实际任务一致；
- 页面只有一个清晰 H1；
- 正文 H2/H3 不跳级制造视觉层级；
- 日期使用机器可读 `<time datetime="YYYY-MM-DD">`；
- 作者、技术审阅者和更新日期在适用时可见。

多语言站点不得只翻译正文而保留错误 lang、canonical 或 hreflang。

## 3. Canonical、robots 与 URL

正式索引页至少满足：

- 一个绝对 canonical URL；
- canonical 与最终可访问 URL 的协议、主机、路径和首选尾斜杠策略一致；
- canonical 目标返回成功且自身可索引；
- 不同时存在互相冲突的 robots meta、HTTP header 或 CMS 设置；
- slug 稳定、可读，不依赖临时测试时间戳；
- URL 迁移有 redirect 和内链更新计划。

发布记录必须保存最终 canonical，而不是只保存后台编辑 URL。

## 4. 结构化数据

推荐最小集合：

- `Article` 或更准确的文章子类型；
- `BreadcrumbList`；
- 站点级 `Organization` / `WebSite` 由全站模板维护，避免每篇重复冲突。

Article JSON-LD 应与页面可见内容一致，包括：

- `headline`；
- `description`；
- `image`；
- `datePublished`；
- `dateModified`；
- `author`；
- `publisher`（有真实组织资料时）；
- `mainEntityOfPage`。

FAQ 只有在页面真实展示 FAQ 且内容适合时才使用相应 schema；不要为了富结果制造问题。文章层 FAQ 也是条件性组件：只有 query、SERP 或 buyer evidence 显示存在尚未被正文直接回答的决策问题时才添加。每个问题必须绑定一个 buyer task 或 objection，答案必须保持事实与承诺边界，不得重复 H2 正文、引入 competing intent、编造政策/性能，或把 CTA 改写成问答。没有这类证据时明确省略 FAQ。

## 5. Open Graph 与分享

至少核对：

- `og:title`；
- `og:description`；
- `og:image` 与可匿名访问的绝对 URL；
- `og:url`；
- `og:type=article`；
- 适用时的 `og:site_name` 和 Twitter Card。

分享图应有稳定比例、清晰主题和安全裁切区；不得用无法公开读取的后台媒体地址。

## 6. 语义 HTML 与文章层级

内容输入可能是 Markdown、HTML 或 Slate，但前台输出必须可读、可搜索、可访问：

- 页面标题输出为唯一真实 `h1`；若 CMS 由独立 title 字段生成 H1，正文从 `h2` 开始且不得重复 H1；
- 列表输出为 `ul/ol/li`；
- 引用使用 `blockquote`；
- 表格使用 `table/thead/tbody/th/td`，需要时提供 caption；
- 链接文字描述目标，不滥用 “click here”；
- 外链安全属性按站点策略处理；
- 代码、公式或复杂嵌套只有在 Adapter 和编辑器重开均验证时使用。

正式文章的视觉样式建议由独立 typography/article-content CSS 组件维护，不把大量内联 style 写进正文数据。

## 7. 图片合同

每张图片记录：用途、来源、许可、原始文件、衍生尺寸、alt、caption（如需）、上传 ID/URL 和验证状态。

前台至少检查：

- cover 和正文图有明确 `width`/`height` 或稳定 aspect-ratio，减少布局跳动；
- 使用响应式 `srcset/sizes` 或平台等效能力；
- 首屏主图不要无条件 lazy-load；非首屏图片可以 lazy-load；
- 格式、压缩和尺寸适合实际显示宽度；
- alt 传达信息，装饰图使用空 alt；必须同时比较 CMS/源数据中的 alt 与最终 DOM 的 `img[alt]`，不能用后台字段存在替代前端透传验收；
- 图片链接可匿名 fetch、decode，并与目标内容一致；
- 相同图片的重复出现有明确理由。

## 8. 移动端、可访问性与美观

至少在约 390px 宽的真实页面检查：

- 无横向溢出；
- 正文行长、字号、行高和段间距适合长文；
- 表格在窄屏可滚动或重排，不截断关键内容；
- 长 URL、代码和数字不会撑破容器；
- 导航、CTA 和表单触控目标足够大；
- focus 可见，键盘可操作；
- 颜色对比和提示框不只依赖颜色传递状态；
- 目录/锚点不会被 sticky header 遮挡。

美观的目标是降低认知负担：稳定 H2/H3、短段落、适量留白、少量高价值提示框、表格与图表服务决策。不要把文章页做成营销组件堆栈。

## 9. 性能与稳定性

正式验收至少观察：

- 首屏图片和字体是否阻塞；
- 页面是否因图片或第三方脚本明显跳动；
- 主内容是否在无客户端脚本或 hydration 延迟时仍存在；
- 页面缓存/更新后 canonical、schema 和日期是否同步；
- 相关文章、推荐模块和表单是否造成明显布局或交互问题。

具体 Core Web Vitals 阈值应按当前官方标准和真实监控验证；本合同不冻结容易过期的数值。

## 10. Sitemap 与更新

正式索引页：

- 只出现一个最终 URL；
- `lastmod` 反映有意义的内容更新，不因每次部署伪更新；
- noindex、redirect、404 和 QA 页面不进入；
- 删除/合并页面时同步处理 sitemap、内链和 redirect；
- 发布记录保存 sitemap 回读时间与结果。

## 11. 发布验收顺序

```text
CMS mutation response
→ backend refresh/readback
→ editor reopen
→ anonymous frontend detail
→ desktop and mobile layout
→ rendered DOM and source metadata
→ image fetch/decode
→ sitemap/robots/canonical reconciliation
```

任何一步失败，不能用前一步成功覆盖。

### 必须记录的证据

- 最终 URL 与 canonical；
- robots/indexing intent；
- lang、title、description；
- Article/Breadcrumb schema 状态；
- 后台精确字段回读；
- 编辑器重开；
- 匿名桌面与移动页面；
- 图片加载与 alt；
- sitemap/lastmod；
- rollback plan。

## 12. 前端一票否决

以下任一项存在，正式 index/publish 必须 `BLOCK`：

1. 目标语言和 `html lang` 冲突；
2. canonical 缺失、错误或指向不可索引页面；
3. QA/Format Lab 被索引、进入 sitemap 或推荐模块；
4. 正文主内容在渲染后缺失或层级严重损坏；
5. Article schema 与可见内容冲突或包含编造字段；
6. 关键图片无法匿名访问/解码；
7. 移动端存在阻断阅读或提交的溢出/交互问题；
8. API 成功但后台、编辑器或前台未通过；
9. noindex 页面被标记为正式发布完成；
10. Adapter 不支持的正文形状仍被发送或发布；
11. CMS/Slate 中信息型图片已有非空 alt，但前端 renderer 丢失、改写为空或绑定到错误图片。

## 13. CMS Adapter 边界

- Adapter 负责把 canonical 内容映射到当前 CMS 字段和正文结构；
- Adapter 的支持矩阵只能证明已测试的部署/格式；
- HTML/Markdown 是作者输入格式，不自动等于 CMS 的持久化格式；
- 当前 AllinCMS 的保守富文本 converter 与正文图片 binding 尚未形成单一集成入口；两条路径各自 PASS 不能自动组合成图片富文本文章 PASS；
- AllinCMS 当前已记录的 canonical 持久化格式为 Slate node array；Markdown 只能经受约束的转换器进入；
- 某一格式“API 保存成功”但“编辑器重开失败”仍是不支持；
- 不得用前端 CSS 掩盖编辑器或数据结构损坏。

## 证据与边界

- **已确认**：本子库把后台刷新、编辑器重开、匿名前台、桌面/移动和图片 decode 作为不同证据层。
- **当前部署观察**：曾发现语言、canonical、schema、推荐内容和图片语义等前端问题；其中一次实测确认 Slate 正文图片在 CMS payload 中有非空 alt，但最终 DOM 输出 `alt=""`。这只能说明该次部署的 renderer 需要修复，不能外推为平台普遍缺陷，也不能通过重复文章 mutation 修复。
- **截图证据边界**：超长页面的自动拼接截图可能重复 sticky header；必须用普通 viewport 截图、DOM 数量/几何和 overflow 检查交叉验证，不能让单张拼接图独自决定 PASS/BLOCK。
- **推断**：本文给出的组件和检查顺序是可迁移工程标准，不是某个搜索引擎的官方排名保证。
- **待验证**：具体主题、插件、部署、缓存、sitemap 生成器和表单行为必须逐站实测。
