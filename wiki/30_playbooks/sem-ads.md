---
title: "Playbook: SEM / Ads"
description: "指导 SEM、Google Ads、LinkedIn Ads、转化追踪、预算止损、搜索词复盘、落地页和广告实验的执行 playbook。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md"]
related: ["index.md", "../40_business/index.md", "../80_metrics/index.md", "../50_channels/sem-ads/index.md"]
when_to_read: "准备启动或调整 SEM、Google Ads、LinkedIn Ads、预算和转化追踪时读本页；没有账号授权、基线和止损线不得执行投放。"
keywords: ["SEM","Google Ads","LinkedIn Ads","转化追踪","预算止损","搜索词复盘"]
---
# Playbook: SEM / Ads

用于 Google Ads、LinkedIn Ads、搜索广告、再营销和落地页实验。

## TL;DR

SEM/Ads 不是先花钱买点击，而是先把转化追踪、落地页、预算边界、政策合规和销售反馈打通，再用小预算验证受众、关键词、痛点、承诺和素材。没有追踪和 CRM 回流，不启动。

## Source Hierarchy

1. Platform rules：Google Ads、GA4、GTM、LinkedIn Ads、Microsoft Ads 等官方规则。
2. Account data：搜索词、转化、成本、线索质量、销售反馈。
3. Experiment learning：每次投放只验证一个主要假设，结果回流到 wiki。

## Platform Split

| Platform / Type | Logic | Do Not Mix Up |
|---|---|---|
| Google Search Ads | 关键词和搜索意图驱动 | 不用 LinkedIn 人群逻辑替代关键词质量 |
| Performance Max | 目标、素材、feed 和转化信号驱动 | 不适合作为无追踪冷启动黑箱 |
| LinkedIn Ads | 职位、公司、行业和人群驱动 | 不用 search terms 逻辑判断内容 |
| Microsoft Ads | 搜索意图 + Bing 生态 | 需单独检查 UET 和导入设置 |
| Retargeting | 已访问/互动人群再触达 | 不适合替代新客获客策略 |

## Pre-Launch QA

- Conversion goals 是否定义清楚。
- Google Ads conversion、GA4 key event、GTM tag 是否触发。
- 表单、预约、电话、WhatsApp 或下载是否进入 CRM。
- UTM 是否包含 source、medium、campaign、content、term。
- GCLID / auto-tagging 或平台点击参数是否保留。
- Landing page 的 claim、CTA、表单和隐私/合规信息是否一致。
- Ads policy 是否有明显风险。
- Budget cap、stop-loss rule 和 review cadence 是否写入实验记录。
- 是否能区分不同受众、关键词、素材或落地页。

## Experiment Framework

- Hypothesis：我们认为哪个受众/痛点/承诺会更有效。
- Audience：给谁看。
- Message：说什么。
- Creative：用什么形式表达。
- Landing Page：承接页面是什么。
- Metric：用什么指标判断。
- Decision Rule：达到什么条件继续、暂停或放大。
- Baseline：当前表现是什么。
- Budget Cap：最多花多少钱验证。
- Guardrail：不能牺牲什么质量指标。
- Feedback Loop：销售和 CRM 结果如何回写。

## Search Ads SOP

1. 选择业务强相关关键词，不从宽泛大词开始。
2. 按购买意图分组：问题词、方案词、品类词、品牌词、竞品词。
3. 为每组写匹配的广告和落地页。
4. 设置否词种子：免费、招聘、教程、二手、无关国家/行业等。
5. 启动后定期看 search terms report。
6. 把高意图词加入精细分组，把低意图词加入否词。
7. 把高转化 search terms 回流到 SEO、LinkedIn 和开发信。

## Budget And Bidding Guardrails

- Average daily budget 不是硬性日花费上限，预算复盘要看统计周期。
- Smart Bidding 需要足够转化数据和学习期；样本不足时不要频繁改动。
- 冷启动先用可解释结构验证关键词、落地页和转化路径。
- 放量前先确认 SQL 或销售反馈没有变差。
- 如果线索量上升但质量下降，优先修流量和 offer，不急着加预算。

## Stop-Loss Rules

- 没有转化追踪，不启动。
- 搜索词明显偏离 ICP，先加否词再继续。
- Landing page 与 claim 不一致，先修页面。
- Ads policy 或合规风险未处理，暂停上线。
- 线索数量上升但 SQL 比例下降，暂停放大。
- 预算花完但无有效学习，记录失败假设并停止重复投放。

## Review Cadence

| Item | Cadence | Notes |
|---|---|---|
| Tracking QA | 启动前和每次改页面/表单后 | 先验证再花钱 |
| Search terms | 每周或达到样本量后 | 样本不足不强判 |
| Negative keywords | 跟随 search terms 更新 | 记录新增原因 |
| Creative / ad assets | 达到预算或样本量后 | 不只看 CTR |
| Landing page | 每轮实验后 | 看转化和线索质量 |
| Lead quality | 每次销售反馈后 | 回写 campaign 和关键词 |

## 常见坑

- 关键词太宽，预算被低意图流量吃掉。
- 广告承诺和落地页不一致。
- 只看 CTR，不看线索质量。
- 没有否词和搜索词复盘。
- 没有把销售反馈回流到广告判断。
- 把平均日预算当成绝对日限额。
- 在 Smart Bidding 学习期频繁改动。
- 自然内容、搜索广告、人群广告混用同一套判断标准。

## 产出前读取

- [../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md](../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md)
- [Creative Testing](../20_concepts/id-0006-creative-testing.md)
- [../50_channels/sem-ads/index.md](../50_channels/sem-ads/index.md)
- [../80_metrics/index.md](../80_metrics/index.md)
- [../_templates/experiment-record.md](../_templates/experiment-record.md)