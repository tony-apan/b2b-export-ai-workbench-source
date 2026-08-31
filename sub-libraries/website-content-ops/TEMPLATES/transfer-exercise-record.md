---
title: "Transfer Exercise Record Template"
description: "验证学习者能否把稳定模型迁移到第二个陌生工具或相邻业务任务，而不是复制旧按钮教程。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["../COURSE-MAP.md", "../QA-CHECKLIST.md"]
related: ["tool-field-map.md", "failure-diagnosis.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要验证学习者能否脱离示例迁移方法并记录提交、评分和反馈时。"
keywords: ["transfer exercise", "learner submission", "review score", "feedback", "course evidence"]
---
# Transfer Exercise Record

## Target

- Reference tool / task:
- New tool / adjacent task:
- Why this transfer matters:
- Stable objects reused:
- Tool-specific assumptions discarded:

## Independent Investigation

- Official sources reviewed:
- New objects, fields and states:
- Interfaces and permissions:
- Limits and risks:
- New mapping file:

## Single Sample

- Input:
- Expected result:
- Approval:
- Action performed:
- Actual result:
- Verification evidence:
- Failure / diagnosis:
- Rollback:

## Transfer Verdict

- [ ] 未复用旧工具按钮步骤作为新工具事实。
- [ ] 来源、事实状态、人工审批、执行记录和验证均保留。
- [ ] 平台差异只进入 adapter，没有污染稳定模型。
- [ ] 失败时能指出证据和诊断顺序。
- [ ] 已把结果写回客户运行区。

Verdict: `PASS / WARN / BLOCK`

- Reason:
- Next gap:
