---
title: "Durable Page Template"
description: "通用长期页面模板，用于创建带稳定文档 ID、完整元描述和最小可检索结构的知识页；优先使用更窄的 concept、playbook 或 course 模板。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
when_to_read: "没有更窄的 concept、playbook 或 course 模板可用，但确需创建长期可检索知识页时。"
keywords: ["长期知识页", "稳定文档 ID", "元描述", "检索入口", "通用页面"]
template_usage: "creator-compatible"
sources: []
related: ["../00_meta/markdown-standard.md", "../00_meta/document-id-standard.md"]
template_target_kind: "durable"
template_target_type: "page"
---
# Durable Page Template

`create-document.mjs` 只渲染下方显式 payload，不会读取正文示例或代码块中的同名字段。

<!-- DOCUMENT_TEMPLATE_START -->
---
doc_id: "{{doc_id}}"
title: "{{title}}"
description: "{{description}}"
type: "{{type}}"
status: "Seed"
owner: "AI"
created: "{{today}}"
last_updated: "{{today}}"
when_to_read: "{{when_to_read}}"
keywords: {{keywords}}
sources: {{sources}}
related: []
---
# {{title}}

## 结论

- 待补。

## 证据与边界

- 已确认：待补。
- 推断：待补。
- 待验证：待补。

## 下一步

1. 待补。
<!-- DOCUMENT_TEMPLATE_END -->
