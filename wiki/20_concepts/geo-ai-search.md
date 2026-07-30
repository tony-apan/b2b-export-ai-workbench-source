---
title: "GEO / AI Search Visibility"
description: "定义 GEO / AI 搜索可见性的核心问题、适用边界、证据要求和评估方向。"
type: "concept"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md", "../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md"]
related: ["index.md", "../40_business/index.md", "../30_playbooks/id-0010-geo-ai-search.md", "../50_channels/geo-ai-search/index.md"]
when_to_read: "需要区分 AI crawler 访问、索引、提及、引用和推荐，或设计 GEO 可见性验证口径时读本页；不得据此承诺稳定收录或收入。"
keywords: ["GEO","AI 搜索","crawler","引用可见性","实体一致性","验证边界"]
---
# GEO / AI Search Visibility

GEO 是本知识库对 AI 搜索可见性工作的内部简称，指面向 ChatGPT Search、Perplexity、Google AI features、Bing/Copilot 等答案引擎，提升品牌被正确理解、引用和呈现的概率。

## Current Understanding

GEO 不是传统 SEO 的改名，也不是 AI 搜索捷径。当前可验证的基础动作仍然是：让网站可抓取、可索引、事实清楚、证据可信、实体一致，并按平台检查 crawler、引用和 referral。任何“保证被 AI 推荐”的说法都应视为高风险。

## 关键问题

- AI 是否知道你是谁。
- AI 是否能准确描述你的服务。
- AI 是否在相关问题中提到你。
- AI 提到你时是否引用正确页面。
- 你的内容是否有清晰实体、结构化事实和第三方证据。
- 你的 robots、WAF、CDN 是否误挡相关 crawler。

## Evidence Levels

| Level | Evidence | Use |
|---|---|---|
| L0 | 单次 AI 回答 | 只能记录现象 |
| L1 | 多次同平台同问题一致 | 可作为趋势线索 |
| L2 | 多平台一致且引用正确 | 可作为优化方向 |
| L3 | referral / server log / Bing AI Performance 等数据支持 | 可进入渠道复盘 |
| L4 | AI 可见性带来可追踪 SQL 或成交 | 可作为业务决策依据 |

## Related

- [GEO Playbook](../30_playbooks/id-0010-geo-ai-search.md)
- [GEO Channel](../50_channels/geo-ai-search/index.md)
- [AI Search Official Source](../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md)