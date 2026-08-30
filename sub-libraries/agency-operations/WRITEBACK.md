---
title: "Agency Operations Writeback"
description: "规定客户事实、运行证据和通用改进候选的分流、去标识化和人工审核规则。"
type: "writeback"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["PLAYBOOK.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Writeback

- 客户事实、聊天、名单、价格、账号、输出、指标和证据永远留在客户 scope；
- 通用方法改进先写入客户 `90_writeback/` candidate；
- candidate 必须删除客户名、域名、联系人、内部 ID、价格、账号和可逆指纹；
- 人工确认来源授权与通用性后，才允许写入母库；
- 母库接收后记录来源类型和日期，不复制客户原文。
