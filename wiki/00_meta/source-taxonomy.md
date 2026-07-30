---
title: "Source Taxonomy"
description: "定义原始资料类型、判定规则、应更新页面和边界情况，避免多 agent 归档口径不一致。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["Subagent adversarial review"]
related: ["../10_sources/source-registry.md", "task-router.md", "markdown-standard.md"]
---

# Source Taxonomy

一份资料可以有一个主类型和多个副类型。主类型决定优先更新哪里，副类型决定还要同步哪些页面。

| Primary Type | 典型资料 | 必须更新 | 常见副类型 |
|---|---|---|---|
| `client` | 客户访谈、聊天、需求文档 | client profile, pain map, objections | sales-call, product-offer |
| `sales-call` | 销售通话转写、会议纪要 | sales notes, objections, ICP, offers | client |
| `competitor` | 竞品页面、广告、报价 | competitor profile, competitor index | SEO, Ads |
| `market-research` | 行业报告、趋势、采购流程 | business overview, concepts | SEO, GEO |
| `product-offer` | 产品说明、报价、交付流程 | offers, proof library, objections | website |
| `website` | 网站页面、截图、站点地图 | website channel, messaging, outputs | SEO, Ads |
| `linkedin` | 帖子、评论、私信、资料页 | LinkedIn channel, outputs, pain map | client |
| `email-outreach` | 邮件、回复、序列、退信 | email channel, objections, outputs | client |
| `seo` | 关键词、SERP、Search Console | SEO channel, metrics, outputs | competitor |
| `geo-ai-search` | AI 答案、引用、品牌回答 | GEO channel, GEO test log | competitor |
| `sem-ads` | 广告账户、素材、搜索词 | Ads channel, experiment record, metrics | website |
| `analytics` | GA、CRM、广告数据、报表 | metrics, experiment record | 任意 |
| `strategy` | 战略讨论、决策、复盘 | decision log, growth system | 任意 |
| `conversation` | AI 对话、内部讨论、团队会议、聊天记录 | conversation log, relevant wiki pages | client, strategy |
| `course-material` | 课程 PDF、付费资料、培训文档 | source note, license register | linkedin, strategy |

## 判定规则

- 如果资料来自真实客户，优先 `client` 或 `sales-call`。
- 如果资料主要提供可量化表现，优先 `analytics`。
- 如果资料会改变业务方向，副类型加 `strategy` 并考虑更新 decision log。
- 如果一个资料能支持 proof，必须同步 [../40_business/proof-library.md](../40_business/proof-library.md)。
- 如果资料包含客户原话，必须保留原话和来源路径。
- 如果资料来自对话，原文先使用 [../../raw/_templates/conversation-source.md](../../raw/_templates/conversation-source.md) 归档到 `raw/10_conversations/`；随后用 [../_templates/source-note.md](../_templates/source-note.md) 建立正式 Source ID。只有在需要辅助拆分 facts、quotes、inferences 和 conflicts 时才使用 [../_templates/conversation-note.md](../_templates/conversation-note.md)，它不是 raw 或 source note 的替代品。
- 如果资料来自课程、PDF 或付费材料，必须登记 [../10_sources/license-and-consent-register.md](../10_sources/license-and-consent-register.md)。

## Source ID 规则

格式：`SRC-YYYYMMDD-短主题`

例子：

- `SRC-20260628-ACME-CALL`
- `SRC-20260628-GOOGLE-ADS-Q2`
- `SRC-20260628-COMPETITOR-HOMEPAGE`
