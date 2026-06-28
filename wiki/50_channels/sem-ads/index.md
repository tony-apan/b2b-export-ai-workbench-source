---
title: "SEM / Ads Channel"
description: "记录 SEM/Ads 投放平台、转化追踪、预算、campaign、素材、搜索词、落地页、CRM 回流和实验。"
type: "channel"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["../../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md"]
related: ["../index.md", "../../30_playbooks/index.md", "../../40_business/index.md", "../../30_playbooks/sem-ads.md"]
---
# SEM / Ads Channel

## 目标

通过付费流量测试受众、痛点、承诺、素材和落地页，并把学习反馈到整体增长系统。

## Official Baseline

- Rule source：[Google Ads And Measurement Source](../../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md)
- Main playbook：[SEM Ads Playbook](../../30_playbooks/sem-ads.md)

## Required Data

| Data | Status | Notes |
|---|---|---|
| Platforms | 待补 | Google Ads、LinkedIn Ads、Microsoft Ads、Meta 等 |
| Current budget | 待补 | 日预算/月预算/测试预算 |
| Current campaigns | 待补 | campaign name、type、status |
| Conversion goals | 待补 | 表单、预约、电话、WhatsApp、下载等 |
| Tracking setup | 待补 | Google Ads conversion、GA4 key event、GTM、UTM、CRM |
| Landing pages | 待补 | URL、claim、CTA、表单 |
| Search terms report | 待补 | 搜索广告必需 |
| Negative keywords | 待补 | 否词清单和原因 |
| Lead quality feedback | 待补 | SQL、成交、无效线索原因 |

## Experiment Table

| Experiment | Platform | Hypothesis | Budget Cap | Primary Metric | Guardrail | Status | Learnings |
|---|---|---|---|---|---|---|---|
| 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |

## Tracking QA Fields

| Field | Required | Notes |
|---|---|---|
| Conversion event fires | yes | 提交表单/预约/电话等是否触发 |
| CRM receives lead | yes | 是否能看到来源和 campaign |
| UTM present | yes | source、medium、campaign、content、term |
| Click id preserved | recommended | GCLID 或平台点击参数 |
| Landing page claim match | yes | 广告承诺和页面一致 |
| Policy check | yes | 避免广告拒登和高风险承诺 |

## Related

- [SEM Ads Playbook](../../30_playbooks/sem-ads.md)
- [Creative Testing](../../20_concepts/creative-testing.md)
- [Google Ads And Measurement Source](../../10_sources/SRC-20260628-GOOGLE-ADS-MEASUREMENT.md)