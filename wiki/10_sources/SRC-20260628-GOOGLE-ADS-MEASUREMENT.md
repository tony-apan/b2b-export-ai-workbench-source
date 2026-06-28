---
title: "Source Note: Google Ads And Measurement Official Guidance"
description: "提炼 Google Ads、GA4 和 GTM 官方资料，作为 SEM/Ads 投放、追踪、预算和复盘 SOP 的规则层。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["https://support.google.com/google-ads/answer/1722022", "https://support.google.com/google-ads/answer/7478529", "https://support.google.com/google-ads/answer/2453972", "https://support.google.com/analytics/answer/9322688", "https://support.google.com/tagmanager/answer/6105160"]
related: ["../30_playbooks/sem-ads.md", "../50_channels/sem-ads/index.md", "../80_metrics/index.md"]
confidence: "high"
review_after: "2026-09-28"
---
# Source Note: Google Ads And Measurement Official Guidance

## Summary

SEM/Ads 的规则层应先来自平台官方：转化追踪、关键词匹配、否词、搜索词报告、预算/竞价、落地页体验和政策合规。没有追踪、预算边界和 CRM 回流，就不能判断投放是否有效。

## Key Facts

- Google Ads 需要先定义 conversion goals 和 conversion measurement，再让 campaign 优化到正确目标。
- GA4 events/key events、Google Ads conversions、GTM tag 和 URL tagging 是不同层级，不能只用 UTM 代替转化追踪。
- 关键词匹配和否词共同控制搜索流量质量；search terms report 用于复查真实搜索词。
- Smart Bidding 依赖转化数据和学习期，不能用样本不足的短周期波动直接判断成败。
- Average daily budget 不是硬性日花费上限，预算复盘要看平台规则和统计周期。
- Responsive search ads、Ad Strength、landing page experience 和 Google Ads policies 都会影响广告可投放性和质量。
- SEM 不应只看 CTR；必须同时看转化、线索质量、销售反馈和护栏指标。

## How To Use

- 投放前先做 tracking QA：转化事件、GTM/GA4/Google Ads、UTM、CRM、表单、电话/WhatsApp 等路径。
- 搜索广告先建立 keyword + negative keyword + search terms review 的闭环。
- 预算要设置 budget cap、stop-loss rule 和 review cadence，并注明是否处于学习期。
- 落地页要和广告 claim 一致，且通过政策和合规检查。
- LinkedIn Ads、Microsoft Ads、再营销和 Performance Max 要分平台建 SOP，不混用搜索关键词逻辑。

## Implications

- For SEM/Ads：先追踪，后放量；先验证线索质量，再扩预算。
- For SEO：付费 search terms 可以反哺关键词和内容缺口，但不能直接等同自然搜索机会。
- For sales：销售反馈必须回流，避免“表单数量上升、SQL 比例下降”。

## Open Questions

- 当前是否已有 Google Ads、GA4、GTM 和 CRM 权限待确认。
- 当前转化事件、预算、campaign 和落地页待补。
- 是否需要 Microsoft Ads 或 LinkedIn Ads 的独立 source note 待确认。