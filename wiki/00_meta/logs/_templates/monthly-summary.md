---
title: "Monthly Log Summary Template"
description: "月度日志摘要模板，用 as_of 和 month-to-date/final 模式压缩每日事件，区分稳定结论、已关闭事项、真正未决风险和知识写回。"
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
when_to_read: "创建月中滚动摘要或月末最终摘要时。"
keywords: ["monthly summary", "month-to-date", "as_of", "closed", "open risk", "writeback"]
---
# Monthly Log Summary Template

文件名：`YYYY-MM-summary.md`。Front matter 必须包含：

```yaml
summary_mode: "month-to-date | final"
as_of: "YYYY-MM-DDTHH:MM:SS+08:00"
```

## 稳定结论

-

## 已关闭事项

| closed_id | 结论 | 证据 | 写回位置 |
|---|---|---|---|
|  |  |  |  |

## 未决风险与阻断

| question_id | 风险 | 证据 | owner | 下一步 | 状态 |
|---|---|---|---|---|---|
|  |  |  |  |  | open/blocked/deferred |

## 需要回写的知识

- concept/playbook：
- source registry：
- course module：
- open question：
