---
title: "Agency Operations Mental Model"
description: "解释母库核心、初始化模板、私有运行区、机器真源、生成索引和升级锁的稳定模型。"
type: "concept"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["README.md", "PLAYBOOK.md", "WORKSPACE-TEMPLATE/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 心智模型

```text
Tracked Core      可更新的方法、规则、脚本、子库源码
Tracked Template  仅用于首次初始化的 synthetic 空结构
Ignored Runtime   用户持续写入的客户事实、任务、日志、输出和证据
```

模板变化只影响未来新建运行区。已有运行区通过 `runtime_schema_version`、迁移器、备份和回滚升级，不通过重新复制。

## 状态与历史分离

- `ACTIVE-CONTEXT.json`、`CLIENT.json`、`TASK.json` 是当前机器状态；
- `HANDOFF.md` 是人和 AI 的当前续接摘要；
- 对话与每日事件是历史证据；
- `index.md` 和 `search-catalog.jsonl` 是可重建视图。

## 三重 scope 校验

一次客户搜索至少同时核对 Registry、canonical 目录和 realpath；catalog 只是加速器，不是权限边界。
