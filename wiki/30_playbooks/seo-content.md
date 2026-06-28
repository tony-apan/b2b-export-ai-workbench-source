---
title: "Playbook: SEO Content"
description: "指导关键词研究、内容集群、技术 SEO、Search Console 复盘、SEO brief 和内容质量门槛的执行 playbook。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md", "Internal SEO course source excluded from public version"]
related: ["index.md", "../40_business/index.md", "../80_metrics/index.md", "../50_channels/seo/index.md", "geo-ai-search.md"]
---
# Playbook: SEO Content

用于做关键词研究、内容集群、技术 SEO、页面 brief、内容更新和 Search Console 复盘。

## TL;DR

SEO 先按 Google 官方规则确保页面可抓取、可索引、可理解、对用户有价值，再用 SEMrush 等工具做市场、关键词、竞品和内容缺口研究。不要把工具指标当成 SEO 真相，也不要承诺“保证收录/排名/AI 引用”。

## Source Hierarchy

1. Rule layer：Google Search Central、Search Console、结构化数据和 spam policies，见 [Google Search Official Source](../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md)。
2. Tool layer：SEMrush、Search Console、Analytics、爬虫工具和排名工具，用于发现机会和验证变化。
3. Business layer：ICP、offer、proof、sales feedback 决定哪些关键词和页面值得做。

## Official SEO Baseline

- 页面必须能被发现、抓取、渲染、索引和理解。
- 内容必须服务明确用户和搜索意图，而不是只服务关键词。
- Sitemap、robots.txt、canonical、noindex、schema 各自解决不同问题，不能互相替代。
- 结构化数据要和页面可见内容一致；Google rich result 行为以 Google 官方文档为准。
- 外链、PR 和第三方引用必须真实相关，不能做垃圾链接或批量低质内容。
- 多语言/多市场外贸站必须单独检查语言版本、hreflang、地区 URL、产品页和库存/价格信息。

## SOP Flow

1. 明确业务目标：流量、线索、品牌、教育市场、产品页转化。
2. 读取业务底座：ICP、offer、messaging、proof、目标市场和产品资料。
3. 建官方基线检查：抓取、索引、robots/noindex、canonical、sitemap、移动端、页面体验、schema。
4. 按 ICP 和购买阶段拆关键词。
5. 区分信息型、商业型、交易型、导航型意图。
6. 用竞品和工具做 content gap，不只看搜索量。
7. 建内容集群：pillar page + supporting pages + product/application pages。
8. 每篇内容绑定下一步 CTA 和证据资产。
9. 发布后用 Search Console / Analytics / CRM 复盘。
10. 定期刷新过时内容，记录 refresh date 和指标变化。

## SEMrush-Style Workflow

1. Market scan：先确认市场、竞品和搜索需求是否值得做。
2. Competitor discovery：找到独立站竞品，不只看你已经知道的品牌。
3. Keyword metrics：评估 volume、difficulty、intent、SERP features、traffic potential、business value。
4. Content gap：比较自己和竞品覆盖了哪些主题、缺哪些页面。
5. Technical crawl：检查抓取、索引、重定向、薄内容、重复内容、页面健康度。
6. Page optimization：优化标题、结构、内容深度、内部链接、CTA 和 schema。
7. Topic cluster：用 pillar page + supporting pages 建主题权威。
8. Backlink / PR：分析真实外链、Digital PR 和第三方证据机会，不追求垃圾数量。
9. Refresh loop：定期更新旧内容，观察排名、点击和转化变化。

## SEO Diagnostic Categories

| Category | Questions | Output |
|---|---|---|
| Market | 这个市场有搜索需求和商业价值吗？ | 市场/竞品清单 |
| Keywords | 哪些词值得优先做？ | Keyword priority list |
| Intent | 用户搜索时真正想解决什么？ | Search intent map |
| Content Gap | 竞品覆盖了什么，我们缺什么？ | Content backlog |
| Technical | 页面能否被抓取、索引、渲染、理解？ | Technical issue list |
| On-page | 页面是否满足意图并推动转化？ | Optimization brief |
| Authority | 是否有真实第三方证据、PR、合作和引用？ | Authority opportunities |
| Refresh | 哪些旧内容值得更新？ | Refresh backlog |

## Technical SEO Checklist

- Sitemap 是否提交且覆盖核心 URL。
- robots.txt 是否误挡核心页面或资源。
- noindex / robots meta 是否误用。
- canonical 是否指向正确版本。
- 404、重定向链、重复内容、薄内容是否存在。
- 移动端是否可用，核心内容是否能渲染。
- Core Web Vitals 是否有明显问题。
- Organization、Product、Breadcrumb、FAQ 等 schema 是否适用且可验证。
- 多语言站是否有正确 hreflang 和自引用。
- Search Console 是否有 page indexing、crawl、manual action 或 security 问题。

## Content Quality Gate

- 是否服务明确 ICP 和搜索意图。
- 是否有原创经验、案例、数据或可验证证据。
- 是否解释 Who / How / Why：谁写的、怎么产生的、为什么写。
- 是否避免泛泛科普、拼凑内容和关键词堆叠。
- 是否有清晰结构、内部链接和下一步 CTA。
- 是否引用可信来源或内部 proof asset。
- 是否有作者/公司/联系方式/产品事实等信任线索。
- 是否设置 refresh date。

## Brief 模板

- 目标关键词：
- 搜索意图：
- 目标读者：
- 购买阶段：
- 读者已知：
- 读者未知：
- 页面目标：
- 必须覆盖的问题：
- 证据/案例：
- 内部链接：
- Schema：
- CTA：
- 复盘指标：

## Keyword Priority Score

| Factor | Score 1 | Score 3 | Score 5 |
|---|---|---|---|
| ICP relevance | 弱相关 | 部分相关 | 强相关 |
| Business value | 只带流量 | 可能带线索 | 明确商业意图 |
| Ranking feasibility | 很难 | 中等 | 可竞争 |
| Proof availability | 无证据 | 有部分证据 | 有强案例/数据 |
| Conversion path | 无 CTA | 弱 CTA | 明确下一步 |

优先做总分高、且能连接 offer 的页面。

## Search Console Review

| Signal | Meaning | Action |
|---|---|---|
| Impressions 上升，CTR 低 | 页面被展示但标题/摘要/意图匹配不足 | 优化 title、description、结构和 SERP intent |
| Clicks 上升，线索低 | 流量可能不符合 ICP 或 CTA 不清 | 检查页面承诺、CTA、offer fit |
| Position 下降 | 竞品、意图或内容质量变化 | 查 SERP、刷新内容、补证据 |
| Not indexed | 页面未进入索引 | 查 indexing reason、canonical、noindex、内容质量 |
| Query 偏离业务 | 流量不够精准 | 调整页面定位或内部链接 |

## Old Content Refresh Checklist

- 这个页面是否还有排名或 impression。
- 搜索意图是否变化。
- 竞品是否新增更好的内容。
- 页面是否内容单薄、过时、缺 FAQ 或缺证据。
- 内部链接是否足够。
- CTA 是否仍然匹配 offer。
- schema、产品参数、价格、认证、案例是否过时。
- 更新后是否记录 refresh date 和指标变化。

## Pillar Page Checklist

- 是否对应一个高价值主题。
- 是否能链接到多个 supporting pages。
- 是否覆盖定义、场景、问题、解决方案、证据和下一步。
- 是否有清晰内部链接结构。
- 是否能服务 SEO、GEO、销售和开发信复用。

## 产出前读取

- [../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md](../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md)
- [../20_concepts/search-intent.md](../20_concepts/search-intent.md)
- [../50_channels/seo/index.md](../50_channels/seo/index.md)
- [../40_business/messaging-house.md](../40_business/messaging-house.md)
- [../40_business/offers.md](../40_business/offers.md)