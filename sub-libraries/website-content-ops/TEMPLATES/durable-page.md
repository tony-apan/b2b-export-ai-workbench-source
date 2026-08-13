---
title: "Website Content Operations Durable Page Template"
description: "为本子库创建带稳定文档 ID、明确读取条件、检索词和证据边界的长期知识页。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-31"
when_to_read: "需要在本子库 durable roots 中新增可被人和 AI 稳定发现、引用和校验的长期页面时。"
keywords: ["durable page", "stable document ID", "website content ops", "retrieval metadata", "create-document"]
template_usage: "creator-compatible"
template_target_kind: "durable"
template_target_type: "page"
sources: ["../AGENTS.md", "../MANIFEST.md"]
related: ["README.md", "../PLAYBOOKS/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Website Content Operations Durable Page Template

在母库工作区中优先使用根目录的 `scripts/create-document.mjs` 渲染下方 payload；独立子库使用者也必须先扫描当前 durable roots，再分配未占用 ID。不要复制示例编号或凭记忆猜下一个编号。

<!-- DOCUMENT_TEMPLATE_START -->
---
doc_id: "{{doc_id}}"
title: "{{title}}"
description: "{{description}}"
type: "{{type}}"
status: "Working"
owner: "AI"
created: "{{today}}"
last_updated: "{{today}}"
sources: {{sources}}
related: []
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "{{when_to_read}}"
keywords: {{keywords}}
---
# {{title}}

## 结论

- 待补。

## 证据与边界

- 已确认：待补。
- 推断：待补。
- 待验证：待补。

## 执行与验收

1. 待补。
<!-- DOCUMENT_TEMPLATE_END -->
