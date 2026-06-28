---
title: "Definition of Done"
description: "定义资料吸收、业务输出、实验记录、页面合并、wiki 体检等任务怎样才算完成。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Subagent adversarial review"]
related: ["task-router.md", "quality-checklist.md", "agent-handoff.md"]
---

# Definition of Done

这里定义“完成”的最低标准，防止 agent 只做表面整理。

## 资料吸收完成

- 已读取指定 `raw/`。
- 已判断 source type 和 source ID。
- 已更新 [../10_sources/source-registry.md](../10_sources/source-registry.md)。
- 已更新相关 business/channel/playbook/concept/client/competitor 页。
- 已更新对应 index。
- 已更新 [ingestion-log.md](ingestion-log.md)。
- 缺口已写入 [open-questions.md](open-questions.md)。
- 新结论的来源、推断、待验证已区分。
- 如果资料来自对话，已更新 conversation log 或 conversation note。
- 如果资料涉及课程/版权/客户/账号数据，已更新 license-and-consent register 或 sensitive data inventory。

## 业务输出完成

- 已读取业务底座和相关 playbook。
- 输出标明目标对象、使用场景、依据、假设、风险。
- 没有把无来源内容写成事实。
- 如果值得复用，已沉淀到 `wiki/90_outputs/`。
- 如果暴露业务缺口，已更新 open questions。
- 如果要发布，已通过 release checklist。

## 新模块完成

- 已按 [module-expansion-sop.md](module-expansion-sop.md) 创建 raw folder、模块索引、playbook 和必要模板。
- 已更新 [module-registry.md](module-registry.md)。
- 已更新总索引、playbook index、channel index。
- 已定义 owner、created、last_updated、visibility。

## 发布完成

- 已检查 [publishing-and-redaction.md](publishing-and-redaction.md)。
- 已检查 [release-checklist.md](release-checklist.md)。
- 已确认不发布 `raw/`。
- 已去敏客户、账号、课程、价格、路径和截图。
- 已记录审批人和下架条件。

## 实验记录完成

- 已记录 hypothesis、baseline、segment、variant。
- 已定义 primary metric 和 guardrail metric。
- 已定义预算/时间/样本上限。
- 已定义 continue/pause/scale decision rule。
- 已记录 result、learning、next action。
- 学习已回流到相关 playbook、channel 或 business 页面。

## Wiki 体检完成

- 已检查 front matter 覆盖率。
- 已检查断链。
- 已检查重复页、孤立页、过时页。
- 已检查强结论是否有来源。
- 已列出已修复项和残余风险。

## 页面合并完成

- 已确认两个页面职责重复。
- 已保留更清晰的页面名。
- 已迁移有价值内容。
- 已更新所有入链和 index。
- 旧页已说明迁移去向或归档到 `99_archive/`。
