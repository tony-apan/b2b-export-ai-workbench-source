---
title: "AllinCMS Adapter Fixtures"
description: "说明 AllinCMS adapter 的去敏机器样本、合同 fixture 和测试数据边界。"
type: "example-index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["../README.md", "../../../../QA-CHECKLIST.md"]
related: ["../observed-contract.redacted.json", "../media-operations-contract.redacted.json", "../article-operations-contract.json", "../../../../TEMPLATES/image-manifest.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# AllinCMS Fixtures

本目录只放用于本地测试、合同解析和去敏演示的 fixture。它们不是当前账号的真实站点数据，也不是生产凭据。

## 使用边界

- 只能使用明确标记的虚拟站点、虚拟文章、虚拟媒体和去敏响应。
- 不得把真实 cookie、token、session、站点 ID、客户资料或生产配置写入本目录。
- fixture 通过不代表当前远程部署通过；真实结果仍需按对应验证记录复核。
- 修改机器合同后必须同步更新相关测试和验证边界，不得只改样本而不改说明。

## 权威入口

- 执行入口：[AI-START-HERE.md](../AI-START-HERE.md)
- 当前 adapter：[README.md](../README.md)
- 文章合同：[article-operations-contract.json](../article-operations-contract.json)
- 媒体合同：[media-operations-contract.redacted.json](../media-operations-contract.redacted.json)
