---
title: "SEO Channel"
description: "记录 SEO 目标关键词、官方基线、Search Console 数据、索引状态、内容缺口、竞品页面和转化页面。"
type: "channel"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["../../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md", "Internal SEO course source excluded from public version"]
related: ["../index.md", "../../30_playbooks/index.md", "../../40_business/index.md", "../../30_playbooks/seo-content.md", "../geo-ai-search/index.md"]
---
# SEO Channel

## 目标

通过搜索意图、内容集群、技术 SEO 和可转化页面获取长期自然流量和线索。

## Operating System

当前 SEO 模块按“官方基线 -> 市场/竞品 -> 关键词/意图 -> 内容差距 -> 技术抓取 -> 页面优化 -> 外链/PR/品牌 -> Search Console 复盘 -> 刷新”的闭环维护。

## Official Baseline

- Rule source：[Google Search Official Source](../../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md)
- Tool layer：SEMrush / Search Console / Analytics 等工具可用于研究和验证；公开版不包含任何私有课程来源。
- Main playbook：[SEO Playbook](../../30_playbooks/seo-content.md)

## Required Data

| Data | Status | Notes |
|---|---|---|
| Website URL | 待补 | 官网或目标站点 |
| Sitemap | 待补 | XML sitemap URL |
| Search Console access | 待补 | Performance、Indexing、URL Inspection |
| Analytics access | 待补 | GA4 or other analytics |
| Target market/language | 待补 | 外贸市场和语言版本 |
| Product/service pages | 待补 | 核心转化页面 |
| Competitor domains | 待补 | 独立站竞品 |
| Existing content list | 待补 | 已发布页面和表现 |

## Backlogs

| Backlog | Purpose | Source |
|---|---|---|
| Keyword backlog | 待评估关键词 | GSC、SEMrush、客户语言、销售反馈 |
| Content gap backlog | 和竞品相比缺失的页面/主题 | 竞品页面和关键词差距 |
| Technical SEO backlog | 抓取、索引、重定向、薄内容、schema、hreflang 等问题 | GSC、crawl、页面检查 |
| Refresh backlog | 需要更新的旧内容 | GSC impression/click/position、业务变化 |
| Authority backlog | PR、真实第三方证据、合作、目录和案例机会 | proof library、PR、伙伴资料 |
| Conversion backlog | 有流量但不转化的页面 | Analytics、CRM、销售反馈 |

## Search Console Fields

| Field | Use |
|---|---|
| Query | 判断真实搜索需求和语言 |
| Page | 判断哪个页面承接需求 |
| Impressions | 判断展示机会 |
| Clicks | 判断流量获取 |
| CTR | 判断标题/摘要/意图匹配 |
| Average position | 判断排名趋势，不单独作为成功指标 |
| Indexing reason | 判断未收录或异常原因 |

## Related

- [SEO Playbook](../../30_playbooks/seo-content.md)
- [Search Intent](../../20_concepts/search-intent.md)
- [GEO Channel](../geo-ai-search/index.md)
- [Google Search Official Source](../../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md)
