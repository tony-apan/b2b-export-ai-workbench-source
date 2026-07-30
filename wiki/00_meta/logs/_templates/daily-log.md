---
title: "Daily Log Template"
description: "v2 每日日志模板：分开记录人类可读证据摘要与可核验 qualification refs，绑定 event digest，并通过 correction_of 生成可解析的 effective/superseded 视图。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["../../logging-standard.md"]
related: ["../../logging-standard.md", "../index.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "创建 daily log、追加 v2 事件或为 release/handoff 记录规范证据 refs 时。"
keywords: ["daily log template", "evidence summary", "evidence refs", "event digest", "correction closure"]
---
# Daily Log Template

文件名：`YYYY/MM/YYYY-MM-DD.md`。

## 默认：summary-only 事件

```markdown
### EVT-YYYYMMDD-#### — 一句话事件标题

- **occurred_at**：YYYY-MM-DDTHH:MM:SS+08:00
- **recorded_at**：YYYY-MM-DDTHH:MM:SS+08:00
- **actor**：
- **scope**：mother-library | sub-library:<id> | private-runtime:<id>
- **action**：
- **evidence**：给人看的证据摘要；不要在这里声称它是正式资格证据
- **evidence_summary_digest**：sha256:<evidence 字段摘要>
- **evidence_role**：summary-only
- **commands**：
- **files changed**：
- **result**：
- **risk / blocker**：
- **next**：
- **writeback**：
- **correction_of**：none
- **event_digest**：sha256:<canonical event payload>
```

`summary-only` 不得添加 `evidence_refs` 或 `evidence_bundle_digest`。

## 仅资格事件：qualification evidence

```markdown
- **evidence**：候选包和独立审查记录已绑定；这里只是摘要
- **evidence_summary_digest**：sha256:<evidence 字段摘要>
- **evidence_role**：qualification
- **evidence_refs**：[{"kind":"repository-relative","locator":"path/to/evidence.json","sha256":"sha256:<真实文件字节摘要>"},{"kind":"immutable-https","locator":"https://public.example/objects/<相同sha256-hex>/record.json","sha256":"sha256:<摘要>"}]
- **evidence_bundle_digest**：sha256:<规范化 evidence_refs 数组摘要>
```

完整 locator 约束和 bundle canonicalization 见 [Logging Standard](../../logging-standard.md)。远程 locator 形状通过不代表远程对象已被本地下载或身份已验证。

无事件时不要创建空卡；在 daily log front matter 写：

```yaml
no_events: true
no_events_reason: "具体说明为什么当天没有需要记录的事件。"
```

不要粘贴 raw 原文。更正旧事件时追加新事件并指向上一条有效链节点；不要并行更正同一 target。结构校验 PASS 不等于事实 PASS。
