---
title: "Glossary"
description: "统一知识库、增长、渠道、销售、实验、SEO/SEM/GEO 和 AI 协作中的核心术语，避免 Claude、Codex、新人对同一词理解不一致。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["User request", "../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md", "../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md", "../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md", "../10_sources/SRC-20260628-SOCIAL-OPS-OFFICIAL.md"]
related: ["methodology.md", "markdown-standard.md", "task-router.md"]
---
# Glossary

术语表是知识库的共同语言。任何反复出现、影响业务判断、容易被不同人解释成不同意思的词，都应该进入这里。

## 使用规则

- 新增术语时，用中文名、英文名、定义、不要误解、常用页面五列记录。
- 如果术语涉及指标，必须连接到 [../80_metrics/index.md](../80_metrics/index.md)。
- 如果术语涉及渠道打法，必须连接到对应 playbook 或 channel 页面。
- 不确定定义时，标注 `待验证`，不要写成定论。

## Wiki / AI 协作术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 原始资料 | Raw source | 未经改写的事实来源，放在 `raw/`。 | 不是草稿区，AI 不应改写。 | [Source Registry](../10_sources/source-registry.md) |
| 来源卡 | Source card | raw 层对网页、官方文档或外部资料的来源元信息记录。 | 不是网页全文复制，也不是策略摘要。 | [Raw Index](../../raw/index.md) |
| 提炼知识 | Wiki knowledge | 从原始资料中整理出的当前最佳理解，放在 `wiki/`。 | 不是不可变真相，随资料更新。 | [AI Manual](ai-operating-manual.md) |
| 来源登记 | Source registry | 已吸收资料的登记表。 | 不是全文摘要，只记录可追溯信息。 | [Source Registry](../10_sources/source-registry.md) |
| 资料吸收 | Ingestion | 把 `raw/` 资料转成 wiki 结构化知识的过程。 | 不是简单摘要，必须更新相关页面和日志。 | [Task Router](task-router.md) |
| 规则层 | Rule layer | 来自官方文档、平台规则、合规要求的底层边界。 | 不是经验技巧，优先级高于工具建议。 | [Methodology](methodology.md) |
| 工具层 | Tool layer | SEMrush、GSC、GA4、Ads、爬虫工具等帮助执行和观察的工具。 | 工具指标不等于事实真相。 | [Methodology](methodology.md) |
| 元描述 | Metadata description | Markdown 页 front matter 中的 `description` 字段。 | 不是 SEO meta description，而是给人和 AI 快速理解页面职责。 | [Markdown Standard](markdown-standard.md) |
| 交接记录 | Agent handoff | 多 agent 或多轮对话之间的接力格式。 | 不是长篇复盘，只记录下一位继续工作所需信息。 | [Agent Handoff](agent-handoff.md) |
| 待验证 | To verify | 当前没有足够来源支撑的说法。 | 不能当事实使用。 | [Quality Checklist](quality-checklist.md) |
| 推断 | Inference | 基于已有资料做出的合理判断。 | 必须与事实区分。 | [AI Manual](ai-operating-manual.md) |

## 业务与定位术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 理想客户画像 | ICP | 最适合购买、成功率最高、利润和协作质量最好的客户类型。 | 不是所有潜在客户。 | [ICP](../40_business/id-0013-icp.md) |
| 触发事件 | Trigger event | 让客户从“知道问题”变成“现在要解决”的事件。 | 不是普通痛点。 | [Customer Pain Map](../40_business/id-0012-customer-pain-map.md) |
| Offer | Offer | 客户愿意付钱换取的结果、交付物、确定性和风险降低。 | 不是服务列表。 | [Offers](../40_business/offers.md) |
| 定位 | Positioning | 客户心中你属于哪个选择、为谁解决什么、为什么优于替代方案。 | 不是 slogan。 | [Positioning](../20_concepts/id-0009-positioning.md) |
| 核心信息屋 | Messaging house | 统一 claim、证据、使用渠道和禁用表达的 messaging 系统。 | 不是广告语集合。 | [Messaging House](../40_business/messaging-house.md) |
| 证据资产 | Proof asset | 案例、数据、截图、推荐语、第三方引用等能支撑 claim 的材料。 | 没授权的证据不能随便公开使用。 | [Proof Library](../40_business/proof-library.md) |
| 反对意见 | Objection | 客户购买前表达出的阻力。 | 不一定是真实原因，需要判断潜台词。 | [Objections](../40_business/id-0014-objections.md) |

## 渠道术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 建站 | Website build | 用网页表达定位、offer、证据和 CTA，使目标客户能理解并转化。 | 不只是视觉设计。 | [Website Playbook](../30_playbooks/website-build.md) |
| LinkedIn 内容 | LinkedIn content | 用持续内容、互动和私信建立信任与销售机会。 | 不只看点赞，要看目标客户互动质量。 | [LinkedIn Playbook](../30_playbooks/linkedin-content.md) |
| 开发信 | Cold email | 面向陌生目标客户的精准邮件触达。 | 不是群发广告。 | [Cold Email](../30_playbooks/cold-email.md) |
| SEO | Search Engine Optimization | 面向传统搜索引擎的自然流量和转化优化。 | 不等于只写文章，也不等于工具分数。 | [SEO Playbook](../30_playbooks/id-0011-seo-content.md) |
| GEO | Generative Engine Optimization | 本知识库对 AI 搜索可见性工作的内部简称。 | 是 emerging 领域，不代表官方保证或特殊捷径。 | [GEO Playbook](../30_playbooks/id-0010-geo-ai-search.md) |
| SEM / Ads | Paid search and ads | 用付费流量测试和获取目标线索。 | 不是只追求点击率。 | [SEM Ads](../30_playbooks/sem-ads.md) |
| 落地页 | Landing page | 承接某个流量、受众、offer 或实验的转化页面。 | 不一定等同首页。 | [Website Channel](../50_channels/website/index.md) |
| 短视频运营 | Short video ops | 用短视频表达产品、场景、证据和客户问题。 | 不是单纯追热点或搬运素材。 | [Short Video Playbook](../30_playbooks/short-video-ops.md) |

## SEO / GEO 术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 抓取 | Crawling | 搜索引擎或 crawler 访问 URL 和资源。 | 被抓取不等于被索引或排名。 | [SEO Playbook](../30_playbooks/id-0011-seo-content.md) |
| 索引 | Indexing | 页面进入搜索引擎索引库，可能参与展示。 | 被索引不等于有排名或流量。 | [SEO Channel](../50_channels/seo/index.md) |
| 规范化 | Canonicalization | 告诉搜索引擎多个相似 URL 中哪个是首选版本。 | canonical 是信号，不是绝对命令。 | [SEO Playbook](../30_playbooks/id-0011-seo-content.md) |
| 结构化数据 | Structured data | 用机器可读格式帮助理解页面实体和属性。 | 不是排名或 AI 引用保证。 | [SEO Playbook](../30_playbooks/id-0011-seo-content.md) |
| schema.org | schema.org vocabulary | 通用结构化数据词汇表。 | Google rich result 行为以 Google 官方支持类型为准。 | [AI Search Source](../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md) |
| 可引用页面 | Cite-ready page | 事实结构清楚、证据明确、适合被 AI 或人引用的页面。 | 不能保证被引用。 | [GEO Playbook](../30_playbooks/id-0010-geo-ai-search.md) |
| AI 搜索测试 | AI search test | 按平台、日期、地区、账号和 prompt 记录 AI 回答。 | 单次回答不能代表趋势。 | [GEO Channel](../50_channels/geo-ai-search/index.md) |

## SEM / Ads 术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 转化追踪 | Conversion tracking | 记录广告或渠道带来的表单、预约、电话、下载等关键动作。 | UTM 不是完整转化追踪。 | [SEM Ads](../30_playbooks/sem-ads.md) |
| 搜索词报告 | Search terms report | 展示用户真实触发广告的搜索词。 | 不等于关键词列表本身。 | [SEM Channel](../50_channels/sem-ads/index.md) |
| 否词 | Negative keyword | 排除不想触发广告的搜索词或意图。 | 不是越多越好，要记录原因。 | [SEM Ads](../30_playbooks/sem-ads.md) |
| 智能出价 | Smart Bidding | 平台基于转化目标和信号自动优化出价。 | 样本不足或追踪错误时不要盲信。 | [SEM Ads](../30_playbooks/sem-ads.md) |
| 平均日预算 | Average daily budget | 平台按平均日预算控制投放消耗。 | 不等于硬性单日上限。 | [SEM Ads](../30_playbooks/sem-ads.md) |

## 数据与实验术语

| 中文 | English | 定义 | 不要误解 | 常用页面 |
|---|---|---|---|---|
| 北极星指标 | North star metric | 当前阶段最能代表增长质量的核心指标。 | 不是所有团队永久唯一指标。 | [Metrics](../80_metrics/index.md) |
| 基线 | Baseline | 实验前的当前表现，用于判断变化。 | 没有基线就不要夸大实验结果。 | [Experiment Template](../_templates/experiment-record.md) |
| 护栏指标 | Guardrail metric | 防止局部优化伤害整体质量的指标。 | 例如 CTR 上升但线索质量下降。 | [Metrics](../80_metrics/index.md) |
| 决策规则 | Decision rule | 实验开始前定义的继续、暂停、放大条件。 | 不应结果出来后再临时解释。 | [Experiment Template](../_templates/experiment-record.md) |
| 线索质量 | Lead quality | 线索是否符合 ICP、是否有真实需求和推进可能。 | 不是表单数量。 | [Sales Call](../30_playbooks/sales-call.md) |
| 复盘 | Retrospective | 判断假设是否成立、学到了什么、更新哪些页面。 | 不是只记录结果好坏。 | [Pitfall Analysis](../30_playbooks/pitfall-analysis.md) |