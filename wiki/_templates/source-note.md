---
title: "Source Note Template"
description: "来源摘要模板，用于把一条 raw 资料登记为可追溯 Source ID，并分开事实、引用、推断、冲突、派生角色和验证写回入口。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
when_to_read: "完成 raw 分类后，需要登记 Source ID，并分开事实、引用、推断、冲突和派生链时。"
keywords: ["source note", "Source ID", "raw path", "事实与推断", "派生链"]
template_usage: "creator-compatible"
sources: []
related: ["../00_meta/raw-conversation-and-course-pipeline.md", "../10_sources/source-registry.md"]
template_target_kind: "source-note"
template_target_type: "source-note"
---
# Source Note Template

Source note 保存提炼和证据状态，不复制 raw 原文。创建时必须传入同一个 `--source-id` 和存在的 `--raw-path`。

<!-- DOCUMENT_TEMPLATE_START -->
---
source_id: "{{source_id}}"
title: "{{title}}"
description: "{{description}}"
type: "{{type}}"
status: "Seed"
owner: "AI"
created: "{{today}}"
last_updated: "{{today}}"
when_to_read: "当需要核对本来源支持了哪些事实、派生页面和验证记录时。"
keywords: ["source note", "raw", "事实", "派生链"]
sources: []
related: []
raw_path: "{{raw_path}}"
source_type: "conversation"
secondary_types: []
confidence: "low"
ingested_at: "{{today}}"
ingestion_status: "registered"
derived_pages: []
verification_record: ""
writeback_record: ""
---
# {{title}}

## Summary

待补：只总结来源负责什么，不把一次性判断升级为事实。

## Key Facts

- 待补，并标明证据位置。

## Useful Quotes

- 待补；公开发布前确认授权和去敏。

## Inferences And Conflicts

- 推断：待补。
- 冲突：待补。
- 待验证：待补。

## Pages Updated

- concept：待补。
- playbook：待补。
- course：待补。
- verification：待补。
- writeback：待补。
<!-- DOCUMENT_TEMPLATE_END -->
