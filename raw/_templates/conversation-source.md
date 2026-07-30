---
title: "Conversation Source Template"
description: "原始对话归档模板，用于保存聊天、会议、访谈或 AI 对话的原文与采集上下文；默认 private、未授权公开且不加入总结或策略判断。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
when_to_read: "归档一段聊天、会议、访谈或 AI 对话原文，并在提炼前登记采集与去敏边界时。"
keywords: ["原始对话", "conversation source", "Source ID", "去敏归档", "采集上下文"]
template_usage: "creator-compatible"
sources: ["../index.md", "../../wiki/00_meta/source-taxonomy.md"]
related: ["../../wiki/_templates/conversation-note.md", "../../wiki/10_sources/source-registry.md"]
visibility: "public"
redaction_status: "safe-to-publish"
template_target_kind: "raw-source"
template_target_type: "conversation-source"
---
# Conversation Source Template

本模板生成的是 raw 原文记录，不是 wiki conversation note。默认值必须留在私有运行边界；只有 synthetic/virtual、public visibility/sensitivity、safe-to-publish redaction 和明确公开 consent 同时成立时，release validator 才允许它进入公开候选包。

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
sources: []
related: []
source_kind: "conversation"
synthetic: false
raw_kind: "conversation"
conversation_type: "meeting"
source_date: "{{today}}"
captured_at: "{{captured_at}}"
ingested_at: "{{captured_at}}"
channel: ""
subject_ref: ""
client_ref: ""
participants: []
topics: []
keywords: []
language: "zh-CN"
sensitivity: "private"
visibility: "private"
consent_status: "unknown"
ingestion_status: "inbox"
derived_to: []
verification_status: "unverified"
redaction_status: "not-reviewed"
---
# {{title}}

## 原文

按时间顺序保存原话、说话人和必要上下文。不要在 raw 页加入 Summary、Recommendations、Analysis 或课程结论。

## 采集说明

- 原始位置：待补。
- 提取方式：待补。
- 去敏范围：待补。
- 版权/同意备注：待补。
<!-- DOCUMENT_TEMPLATE_END -->
