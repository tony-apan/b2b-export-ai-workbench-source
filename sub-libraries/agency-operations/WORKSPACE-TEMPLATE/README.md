---
title: "Customer Runtime Template"
description: "初始化脚本复制或生成私有 customer-runtime 的空结构说明；机器状态来自 JSON，index 为可重建视图。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["AGENTS.md", "RUNTIME.json", "00_control/index.md", "10_clients/index.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
when_to_read: "首次初始化同一母库根目录下的私有多客户运行区，并确认模板不会覆盖已有客户数据时。"
keywords: ["customer runtime", "multi-client template", "private workspace", "core lock", "scoped search"]
---
# Customer Runtime Template

这是空的 tracked 模板，不是实际运行区。`init-customer-runtime.mjs` 会复制基础合同并写入当前 core lock。已有运行区不得用本目录覆盖。

运行区 canonical 入口：`README.md` → `00_control/ACTIVE-CONTEXT.json` → 已注册客户 `CLIENT.json` → 活动任务 `TASK.json` / `HANDOFF.md`。

客户、任务和 active context 由子库脚本维护；`index.md` 与 `search-catalog.jsonl` 是可重建视图。`00_control/.runtime-write.lock` 存在时停止运行并先检查恢复状态。
