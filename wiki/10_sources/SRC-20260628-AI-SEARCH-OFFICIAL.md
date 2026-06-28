---
title: "Source Note: AI Search Official Guidance"
description: "提炼 Google AI features、OpenAI crawlers、Bing Webmaster、schema.org 等官方资料，明确 GEO/AI 搜索的可执行边界。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["https://developers.google.com/search/docs/appearance/ai-features", "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide", "https://developers.openai.com/api/docs/bots", "https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a", "https://schema.org/"]
related: ["../30_playbooks/geo-ai-search.md", "../50_channels/geo-ai-search/index.md", "../20_concepts/geo-ai-search.md", "../30_playbooks/seo-content.md"]
confidence: "medium"
review_after: "2026-09-28"
---
# Source Note: AI Search Official Guidance

## Summary

GEO / AI Search 是 emerging 模块。当前可确认的规则是：先做好可抓取、可索引、可引用、证据清楚的 SEO 基础，再分平台检查 Google、Bing、OpenAI、Perplexity 等 crawler、引用和 referral 表现。不要承诺“保证被 AI 引用/推荐”。

## Key Facts

- Google 官方把 AI features 的优化放在 SEO 基础之内；没有专门保证 AI 引用的特殊文件、特殊 schema 或捷径。
- Google AI features 的可见性与 Search Console、snippet 控制、robots/noindex/nosnippet 等搜索控制有关。
- 结构化数据有助于机器理解和 rich result 资格，但不是 AI 搜索出现或排名保证。
- OpenAI crawlers 需要区分 OAI-SearchBot、GPTBot、ChatGPT-User 等不同角色；robots、WAF/CDN 和 server log 都要分开检查。
- Bing Webmaster Guidelines 和 Bing AI Performance 可用于 Bing/Copilot 侧的可见性和引用观察。
- schema.org 是通用词汇表；是否被 Google 或其他平台用于展示，要看各平台官方支持。
- Perplexity 等平台有独立 crawler 规则，不能把 Google 规则直接套到所有 AI 平台。

## How To Use

- GEO playbook 必须写清：SEO 基础优先、平台差异、无保证、反 hack、实验记录。
- 每次 AI 搜索测试记录日期、平台、地区/账号状态、prompt、回答摘要、引用、错误和纠偏动作。
- 核心页面要维护 entity facts：公司/品牌是谁、服务谁、产品/服务、地区、证据、案例、FAQ、联系方式。
- 技术检查要包括 robots、noindex、nosnippet、WAF/CDN、crawler access、schema、server logs、UTM/referral。
- 第三方证据必须真实、可验证、与业务相关；不要买虚假 mentions 或批量生成低质引用。

## Emerging / 待验证

- `llms.txt`、AI visibility tools、prompt 排名监控、引用率到收入归因，均应作为实验项，不写成必做规则。
- 单次 ChatGPT/Perplexity/Gemini/AI Overviews 回答不能代表趋势。
- Gemini 与 Google Search AI features 的关系需分别查证，不应直接外推。

## Open Questions

- 目标品牌、官网 URL、核心页面和第三方证据待补。
- 是否已在 Bing Webmaster Tools、Search Console 中验证站点待确认。
- 是否能查看 server logs、CDN/WAF、referral/UTM 待确认。