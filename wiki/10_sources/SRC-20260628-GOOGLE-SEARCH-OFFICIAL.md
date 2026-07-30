---
title: "Source Note: Google Search Official SEO Guidance"
description: "提炼 Google Search Central 和 Search Console 官方 SEO 资料，作为 SEO 模块的规则层和新人入门基线。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["https://developers.google.com/search/docs/essentials", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content", "https://support.google.com/webmasters/answer/7576553", "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide", "https://developers.google.com/search/docs/monitor-debug/search-console-insights"]
related: ["../30_playbooks/id-0011-seo-content.md", "../50_channels/seo/index.md", "../20_concepts/id-0001-search-intent.md"]
confidence: "high"
review_after: "2026-10-26"
when_to_read: "核对 SEO、Search Console、抓取、索引或 AI Search 建议前，先读本来源页；不把官方指南解释成排名保证。"
keywords: ["Google Search", "Search Console", "SEO 官方指南", "抓取索引", "people-first", "AI Search"]
---
# Source Note: Google Search Official SEO Guidance

## Summary

Google 官方资料是 SEO 的规则层：先确保页面可抓取、可索引、可理解、服务用户，再用工具做关键词、竞品和内容执行。SEMrush 等工具可以辅助研究，但不能替代 Google Search Essentials、Search Console 和结构化数据官方边界。

## Key Facts

- Search Essentials 是 SEO 的最低准入层，覆盖技术要求、垃圾政策和核心最佳实践。
- SEO Starter Guide 适合新人理解：SEO 的目标是帮助搜索引擎理解内容，并帮助用户找到内容，不是操纵排名。
- Helpful content 指南强调 people-first、原创价值、清晰来源、Who/How/Why 和用户满意度。
- Search Console 的 Performance、Page indexing、URL Inspection 等报告用于诊断，不等于排名保证。
- Sitemap、robots.txt、canonical、noindex、结构化数据分别解决不同问题：发现、抓取控制、规范化、索引控制、内容理解/富结果资格。
- schema.org 是词汇表；Google rich result 行为应以 Google Search Central 的具体类型文档为准。
- 多语言、hreflang、电商产品页和 Core Web Vitals 对外贸独立站尤其重要，但都不是单独的排名保证。
- 2026 AI 搜索指南强调 AI Overviews / AI Mode 仍建立在基础 SEO 之上，并建议提供独特、非同质化内容；Google 也明确表示无需为 AI Search 额外制造关键词变体、特殊 chunk 或其不使用的 `llms.txt` 文件。
- Search Console Insights 可用于查看增长中的 query、page、top/trending 内容和流量变化；这些信号适合进入知识库，但必须结合询盘和销售反馈判断商业价值。

## How To Use

- SEO playbook 开头先引用 Google 官方基线，再进入 SEMrush-style workflow。
- 内容质量检查必须加入 people-first、原创经验、证据透明、作者/来源、搜索意图和 CTA。
- 技术 SEO 检查必须区分 crawl、index、canonical、render、schema、hreflang 和 page experience。
- 外链/authority 相关建议必须受 Google spam policies 约束，避免把外链数量当成目标。
- 发布和刷新内容后，用 Search Console 观察 query、page、impression、click、CTR、position 和 indexing reason。
- 把 query、页面表现、询盘和销售反馈回写到搜索意图、ICP、FAQ、messaging、proof 和内容 backlog，而不是只做排名报表。

## Implications

- For SEO：官方规则层优先，工具层次之。
- For GEO：Google generative AI features 仍要求先做好 SEO 基础，不存在保证被 AI 引用的特殊捷径。
- For website：每个核心页面都应有索引状态、内部链接、结构化内容、清晰 CTA 和 evidence。
- For content：不要为了关键词堆内容；先满足搜索意图和用户决策。

## Open Questions

- 目标网站 URL、Search Console、Analytics 和 sitemap 待补。
- 目标市场语言和 hreflang 需求待确认。
- 产品页是否需要 Product structured data 和 Merchant Center 数据待确认。