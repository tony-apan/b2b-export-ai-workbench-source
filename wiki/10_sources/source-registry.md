---
title: "Source Registry"
description: "面向来源维护者登记 Source ID、类型、状态、复查日期和派生页面，支持从知识页反向追溯证据；不收录私有 raw 或本地路径。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: []
related: ["license-and-consent-register.md"]
when_to_read: "新增来源、复查来源日期或反向追踪某个知识页由哪些 Source ID 派生时，先查本登记表。"
keywords: ["Source ID", "来源登记", "Pages Updated", "反向追踪", "Last Reviewed", "证据链"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Source Registry

> 原始资料先按 [raw/index.md](../../raw/index.md) 分类，再在这里登记稳定 Source ID。原始对话不直接写成课程结论；`derived_to`、相关页面和验证状态用于追踪从来源到 wiki/课程的提炼链。


这里登记公开版知识库使用的来源。公开版不包含私有 raw、客户资料、课程 PDF、账号数据或本地文件路径。

| Source ID | Date Added | Source Path | Primary Type | Secondary Types | Ingestion Status | Source Note | Confidence | Pages Updated | Last Reviewed |
|---|---|---|---|---|---|---|---|---|---|
| SRC-20260628-GOOGLE-SEARCH-OFFICIAL | 2026-06-28 | Official Google Search Central / Search Console pages | seo | official-docs, search-console, structured-data, content-quality | ingested | [SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md](SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md) | high | `wiki/30_playbooks/id-0011-seo-content.md`, `wiki/50_channels/seo/index.md`, `wiki/20_concepts/geo-ai-search.md`, `wiki/20_concepts/id-0001-search-intent.md` | 2026-07-29 |
| SRC-20260628-GOOGLE-ADS-MEASUREMENT | 2026-06-28 | Official Google Ads / GA4 / GTM help pages | sem-ads | official-docs, google-ads, ga4, gtm, tracking | ingested | [SRC-20260628-GOOGLE-ADS-MEASUREMENT.md](SRC-20260628-GOOGLE-ADS-MEASUREMENT.md) | high | `wiki/30_playbooks/sem-ads.md`, `wiki/50_channels/sem-ads/index.md` | 2026-06-28 |
| SRC-20260628-AI-SEARCH-OFFICIAL | 2026-06-28 | Official or primary Google / Bing / OpenAI / schema.org / Perplexity pages | geo-ai-search | official-docs, google-ai-features, openai-crawlers, bing, schema, perplexity | ingested | [SRC-20260628-AI-SEARCH-OFFICIAL.md](SRC-20260628-AI-SEARCH-OFFICIAL.md) | medium | `wiki/30_playbooks/id-0010-geo-ai-search.md`, `wiki/50_channels/geo-ai-search/index.md`, `wiki/20_concepts/geo-ai-search.md` | 2026-07-26 |
| SRC-20260628-SOCIAL-OPS-OFFICIAL | 2026-06-28 | Official LinkedIn / Meta / YouTube / TikTok public pages | linkedin | official-docs, social-media, short-video, linkedin-ads, meta, youtube, tiktok | ingested | [SRC-20260628-SOCIAL-OPS-OFFICIAL.md](SRC-20260628-SOCIAL-OPS-OFFICIAL.md) | medium | `wiki/30_playbooks/linkedin-content.md`, `wiki/30_playbooks/short-video-ops.md`, `wiki/50_channels/linkedin/index.md`, `wiki/50_channels/short-video/index.md` | 2026-06-28 |
| SRC-20260727-ALLINCMS-OFFICIAL | 2026-07-27 | Official AllinCMS docs and sitemap | tooling | official-docs, cms, allincms, media, article, codex | ingested | [SRC-20260727-ALLINCMS-OFFICIAL.md](SRC-20260727-ALLINCMS-OFFICIAL.md) | high | `sub-libraries/website-content-ops/TOOLS.md`, `sub-libraries/website-content-ops/ADAPTERS/cms/`, `sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md` | 2026-07-27 |
| SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL | 2026-07-27 | Official PicGo / Cloudflare R2 / GitHub / Tencent COS / Alibaba OSS docs | tooling | official-docs, picgo, image-host, r2, github, cos, oss | ingested | [SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md](SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md) | high | `sub-libraries/website-content-ops/TOOLS.md`, `sub-libraries/website-content-ops/ADAPTERS/image-hosts/` | 2026-07-27 |
| SRC-20260728-0001 | 2026-07-28 | `raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md` | knowledge-base | virtual-fixture, course-pipeline, governance | ingested | [SRC-20260728-0001.md](SRC-20260728-0001.md) | medium | `ID-0002`, `ID-0003`, `ID-0004`, `VER-20260728-raw-course-closure`, `WB-20260728-raw-course-closure` | 2026-07-28 |
| SRC-20260726-KARPATHY-LLM-WIKI | 2026-07-26 | Andrej Karpathy official GitHub Gist | knowledge-base | official-primary, llm-wiki, raw, wiki, agent-instructions | ingested | [SRC-20260726-KARPATHY-LLM-WIKI.md](SRC-20260726-KARPATHY-LLM-WIKI.md) | high | `wiki/00_meta/knowledge-compounding-system.md`, `wiki/00_meta/ai-operating-manual.md`, `wiki/50_channels/seo/index.md` | 2026-07-26 |

## Type Reference

- `official-docs`
- `seo`
- `geo-ai-search`
- `sem-ads`
- `linkedin`
- `social-media`
- `strategy`
- `analytics`
- `knowledge-base`
- `tooling`
- `image-host`
- `cms`