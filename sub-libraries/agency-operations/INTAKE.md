---
title: "Agency Operations Intake"
description: "创建客户、公司、产品、渠道、账号和首个任务前必须收集的最小字段与敏感信息边界。"
type: "intake"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["PLAYBOOK.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Intake

## 必需字段

- 客户显示名与唯一 `client_id`；
- 默认 `company_id`；
- 产品列表及稳定 `product_id`；
- 渠道与账号的非敏感标识；
- 当前目标、成功口径、时间范围和禁止动作；
- 数据授权来源、可用范围和保留策略；
- 外部动作由谁批准、批准有效期和验证方式。

密码、cookie、token、私钥和 session 只登记 secret reference。信息不足时可以建立 Draft 客户，但不得开始外部执行。
