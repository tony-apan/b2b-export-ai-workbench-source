---
title: "Sensitive Data Inventory"
description: "登记知识库可能包含的敏感数据类型、所在位置、风险等级、处理规则和发布限制。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Risk review"]
related: ["publishing-and-redaction.md", "../10_sources/license-and-consent-register.md", "collaboration-model.md"]
visibility: "internal"
redaction_status: "not-reviewed"
---

# Sensitive Data Inventory

默认假设 `raw/` 含敏感资料，不公开上传。

| Data Type | Examples | Likely Location | Sensitivity | Public Rule |
|---|---|---|---|---|
| PII | 姓名、电话、邮箱、微信、LinkedIn URL | `raw/clients/`, `raw/sales-calls/`, `raw/linkedin/` | restricted | 删除或匿名化 |
| Client Data | 客户访谈、聊天记录、需求、合同、报价 | `raw/clients/`, `wiki/60_clients/` | restricted | 默认不公开 |
| Account Data | 广告账户、CRM、后台截图、Search Console | `raw/sem-ads/`, `raw/seo/` | confidential | 默认不公开 |
| Social Account Session | 社媒账号 cookie、session、验证码、恢复码、登录状态、插件导出 | `raw/linkedin/`, `raw/short-video/`, browser/plugin exports | restricted | 不得入库，不得公开，不得自动化使用 |
| Course Material | 付费课程 PDF、课件、讲师资料、截图 | `raw/`, external folders | restricted | 不公开 raw，只公开原创提炼 |
| Pricing / Margin | 报价、利润、预算、CPA、成交金额 | `raw/`, `wiki/40_business/`, `wiki/80_metrics/` | confidential | 聚合或范围化 |
| Trade Secrets | 供应链、工艺、渠道、客户名单 | `raw/products-offers/`, `wiki/40_business/` | restricted | 不公开 |
| Credentials | API key、cookie、登录信息 | any | restricted | 不得入库 |

## Handling Rules

- 任何含 PII 的资料进入 wiki 前先标记 sensitivity。
- 对外版本中客户名改为 `Client A`，联系人改为角色。
- 具体数值可以改为范围，如 `$10k-$50k`。
- 账号截图默认不公开，除非完全打码并审批。
- 课程资料只保留原创总结，不复制大段原文。
- 社媒账号 cookie、session、验证码、恢复码和自动化脚本不得进入 raw 或 wiki。
- 涉及社媒账号动作时，必须遵守 [social-account-safety.md](social-account-safety.md)。
