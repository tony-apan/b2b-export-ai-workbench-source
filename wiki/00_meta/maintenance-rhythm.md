---
title: "Maintenance Rhythm"
description: "定义知识库每次、每周、每月维护节奏和例行检查动作。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: []
related: []
---
# Maintenance Rhythm

## 每次新增资料

- 登记来源。
- 更新相关页面。
- 更新对应 index。
- 追加 ingestion log。
- 记录开放问题。
- 检查是否需要更新 decision log。
- 检查是否需要写 agent handoff。

## 每周

- 做一次轻量 health check。
- 合并重复页面。
- 标记过时页面。
- 把有价值的聊天输出沉淀到 `90_outputs/`。
- 检查 source registry 是否有 `new` 或 `needs-review`。
- 检查强结论是否缺来源。
- 检查 open questions 是否有阻塞项。

## 每月

- 复查 ICP、offer、messaging。
- 复查渠道指标。
- 复查客户异议和成交原因。
- 生成一份“本月学到了什么”的增长复盘。

## Weekly Health Check SOP

1. 读取 [quality-checklist.md](quality-checklist.md)。
2. 检查所有 Markdown 是否有 front matter。
3. 检查断链。
4. 检查 `source-registry.md` 中未吸收或待复查来源。
5. 检查 `open-questions.md` 中阻塞业务输出的问题。
6. 检查 `90_outputs/` 中是否有应回流到 playbook 的学习。
7. 输出本周修复项、未修复风险和下周优先级。

## Archive Protocol

- 过时页面移入 `wiki/99_archive/`。
- 如果旧路径仍可能被引用，保留一个短页面说明迁移去向。
- 更新所有 index。
- 在 ingestion log 记录归档原因。
- 不删除有来源的历史信息，除非用户明确要求。

## Output Location

- 体检结果：`wiki/00_meta/ingestion-log.md` 或新的 dated note。
- 策略变化：`wiki/00_meta/decision-log.md`。
- 实验结果：`wiki/80_metrics/index.md` 或 `wiki/90_outputs/` 中对应输出。
- 多 agent 交接：按 [agent-handoff.md](agent-handoff.md) 格式写入最终回复或相关日志。
