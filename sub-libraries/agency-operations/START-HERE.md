---
title: "Agency Operations Start Here"
description: "AI 在准备完成后初始化或续接本地客户代运营任务时的最短读取和阻断顺序。"
type: "guide"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["README.md", "AGENTS.md", "PLAYBOOK.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# AI 启动入口

> 本地准备已完成，但模板不等于已创建客户运行区。本轮没有根目录真实 `customer-runtime/`；只有用户明确开始实际运行后才执行初始化。

1. 读取母库根 `AGENTS.md`、`CONTEXT.md` 和本文件。
2. 确认 `customer-runtime/RUNTIME.json` 存在；不存在只可运行初始化，不得猜客户目录。
3. 确认不存在未解释的 `00_control/.runtime-write.lock`，再读取 `customer-runtime/AGENTS.md` 与 `00_control/ACTIVE-CONTEXT.json`。
4. `client_id` 为空、客户未注册或目录不一致时停止；不要扫描整个运行区寻找“可能的客户”。
5. 读取目标客户 `CLIENT.json`。
6. 若有活动任务，读取对应 `TASK.json` 和 `HANDOFF.md`，再读最近日志与精确证据指针。
7. 外部发送、发布、私信、删除、覆盖、批量变更或账号切换必须取得本次对象级明确批准。
8. 工作后更新任务状态、handoff、append-only 日志和必要索引。

切换已有任务使用 `activate-task.mjs`；依赖索引或搜索前先运行 `sync-runtime-indexes.mjs` 与 `validate-runtime-indexes.mjs`。不要手工修改 active context 后跳过绑定校验。

## 禁止的捷径

- `rg ... customer-runtime/`；
- 根据目录名猜客户或账号；
- 把聊天记录当当前状态；
- 把客户事实写回 tracked 母库；
- 用旧批准覆盖新对象或新批次；
- 因 structural PASS 宣称生产可用。
