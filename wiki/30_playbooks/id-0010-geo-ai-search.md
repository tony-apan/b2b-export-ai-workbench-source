---
title: "Playbook: GEO / AI Search"
doc_id: "ID-0010"
description: "指导 AI 搜索可见性测试、crawler 检查、实体事实和引用纠偏；不承诺平台收录、引用、推荐或排名。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md", "../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md"]
related: ["index.md", "../40_business/index.md", "../80_metrics/index.md", "../50_channels/geo-ai-search/index.md", "id-0011-seo-content.md"]
when_to_read: "准备检查 AI 搜索可见性、crawler、引用准确性或实体一致性时，按本 playbook 执行；不承诺平台收录或排名。"
keywords: ["GEO", "AI 搜索", "crawler", "引用准确性", "实体一致性", "可见性测试"]
---
# Playbook: GEO / AI Search

用于提升品牌在 ChatGPT、Perplexity、Gemini、Google AI Overviews、Bing/Copilot 等 AI 答案中的准确性、可引用性和可见性。

## TL;DR

GEO 是 emerging 模块。当前可靠做法不是找 AI 搜索捷径，而是先做好 SEO 基础、品牌实体、可验证证据、结构清晰页面和平台 crawler 可访问性，再分平台记录测试结果。不要承诺保证被 AI 引用、推荐或带来收入。

内容是 SEO 与 GEO 的共同载体，但真正的上游是客户问题、产品事实和可验证证据。客户聊天可以生成问题库和答案结构；独立站把这些知识发布为稳定页面；搜索与 AI 平台是否抓取、索引、引用或推荐仍需分别观察。

## Customer Voice To Cite-Ready Knowledge

`客户聊天（真实资料留私有层；虚拟演示明确标注） -> 问题 -> 搜索/决策意图 -> 直接答案 -> 产品事实与限制 -> 案例/证据 -> 独立站页面 -> 分平台测试`

适合从客户聊天提炼的 cite-ready 单元：

- 明确定义：产品/服务是什么，不是什么。
- Who / When：适合谁，在什么场景使用。
- How：如何工作、步骤和前提条件。
- Compare：与替代方案的真实差异。
- Limits：不能解决什么、风险和限制。
- Proof：案例、数据、认证、流程和第三方证据。
- FAQ：客户反复提出的问题和直接答案。

这些单元应服务真实用户决策，而不是为了让 AI 截取而机械切块。完整转换使用 [Customer Voice To Search Intent Template](../_templates/customer-voice-to-search-intent.md)。

## Boundaries

- Google 官方将 generative AI features 的优化放在 SEO 基础之内。
- schema、llms.txt、AI visibility tools 都不能写成“保证被 AI 引用”。
- 单次 AI 回答不能代表趋势；必须按平台、日期、地区、账号状态和 prompt 记录。
- 第三方信号必须真实、可验证、与业务相关，不做虚假 mentions 或垃圾外链。

## Core Tasks

- Brand entity：你是谁、服务谁、解决什么、在哪些市场、有什么证据。
- Crawlability：Googlebot、Bingbot、OAI-SearchBot、GPTBot、ChatGPT-User、PerplexityBot 是否能访问应访问页面。
- Cite-ready pages：事实结构清楚，FAQ、案例、产品、对比、证据和来源明确。
- Third-party proof：目录、媒体、合作、客户案例、评价、行业资料等真实证据。
- Error correction：发现错误回答后，更新页面、schema、FAQ、关于页、案例页或第三方资料。
- Measurement：用 Search Console、Bing Webmaster、server logs、UTM/referral、人工测试和截图共同观察。

## Platform Checklist

| Platform | Check | Evidence |
|---|---|---|
| Google AI features | 页面是否可索引、snippet 控制是否合理、内容是否满足 SEO 基础 | Search Console、页面检查、SERP 观察 |
| Bing / Copilot | 站点是否验证、Bingbot 是否能抓取、AI Performance 是否有引用/grounding query | Bing Webmaster Tools |
| ChatGPT Search | OpenAI crawler 是否被 robots/WAF/CDN 放行，referral/UTM 是否可看 | robots、server logs、analytics |
| Perplexity | Perplexity crawler 是否可访问，回答引用是否正确 | robots、server logs、人工测试 |
| Gemini | 不直接外推 Google Search AI features；单独记录测试 | 平台测试记录 |

## AI Search Test Questions

- `[业务类别] 推荐哪些公司/服务商？`
- `[目标客户] 如何解决 [痛点]？`
- `[你的品牌] 是做什么的？`
- `[你的品牌] 和 [竞品] 有什么区别？`
- `谁适合使用 [你的服务类型]？`
- `[产品/服务] 选型时应该注意什么？`
- `[地区/行业] 的 [产品/服务] 供应商有哪些？`

## Test Protocol

- 每个测试记录日期、平台、账号/地区、prompt、答案摘要。
- 记录是否提到品牌、是否引用、引用是否正确。
- 用 1-5 分记录准确性，标准见 [../_templates/geo-test-log.md](../_templates/geo-test-log.md)。
- 截图或复制摘要放入 `raw/geo-ai-search/`。
- 错误回答要写明纠偏动作：更新页面、补结构化事实、补第三方证据、修正品牌实体。
- 同一主题至少跨平台和跨时间复测，不用单次结果下结论。

## Cite-Ready Page Checklist

- 页面开头是否直接说明对象、场景和结论。
- 是否有清晰实体信息：品牌、公司、产品、地区、服务对象、联系方式。
- 是否有 FAQ、对比、使用场景、限制条件和下一步。
- 是否有可验证证据：案例、认证、数据、客户评价、第三方引用。
- 是否有清晰内部链接到关于页、产品页、案例页、FAQ 和联系页。
- 是否有合适 schema，且和可见内容一致。

## Anti-Hack List

- 不承诺“保证被 AI 引用/推荐”。
- 不批量生成低质 AI 页面。
- 不买虚假 mentions 或垃圾外链。
- 不把 schema 写成排名或 AI 引用保证。
- 不把 llms.txt、prompt 排名工具或 AI visibility 分数当成官方标准。
- 不把 ChatGPT、Perplexity、Gemini、Google、Bing 混成同一套算法。

## Quality Controls

- 单次回答不能代表趋势。
- 不同平台要分开记录。
- 登录状态、地区、时间会影响结果，记录上下文。
- GEO 结果不能直接等同收入贡献。
- 所有强结论必须引用 source note 或标注推断/待验证。

## 产出前读取

- [../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md](../10_sources/SRC-20260628-AI-SEARCH-OFFICIAL.md)
- [../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md](../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md)
- [../20_concepts/geo-ai-search.md](../20_concepts/geo-ai-search.md)
- [../50_channels/geo-ai-search/index.md](../50_channels/geo-ai-search/index.md)
- [../40_business/business-overview.md](../40_business/business-overview.md)
- [../70_competitors/index.md](../70_competitors/index.md)
- [../_templates/geo-test-log.md](../_templates/geo-test-log.md)