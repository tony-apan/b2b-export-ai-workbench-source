---
title: "Agent Handoff"
description: "定义 Claude、Codex、多 agent 或多轮对话之间的交接格式，保证无记忆接手也能继续推进。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Subagent adversarial review"]
related: ["task-router.md", "definition-of-done.md", "markdown-standard.md"]
---

# Agent Handoff

当一个 agent 完成阶段性工作，或者需要另一个 agent 接手时，使用这个格式。

## Handoff Template

```md
## Handoff: YYYY-MM-DD 任务名

### Task

- 用户要什么：
- 本轮目标：

### Read

- 已读文件：
- 已读来源：

### Changed

- 已改文件：
- 新增文件：

### Decisions

- 做出的判断：
- 证据等级：

### Open Questions

- 待确认：
- 阻塞哪些输出：

### Risks

- 可能误导的地方：
- 需要人类确认的地方：

### Next

- 下一位 agent 应先读：
- 下一步建议：
```

## 什么时候必须写交接

- 多 agent 对抗分析后。
- 大范围改 wiki 结构后。
- 未完成但需要暂停时。
- 发现关键业务冲突或数据缺口时。
- 做了会影响后续策略的判断时。

