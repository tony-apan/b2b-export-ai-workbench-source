---
title: "Customer Runtime Agent Rules"
description: "复制到私有运行区的局部规则，要求显式客户 scope、任务续接、secret reference 和外部动作批准。"
type: "agent-protocol"
status: "Canonical"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["README.md", "00_control/ACTIVE-CONTEXT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Customer Runtime AGENTS.md

- 无有效 `client_id` 不读取、搜索或写入客户目录。
- 当前状态读 JSON，续接读 HANDOFF；聊天和日志只作历史证据。
- 不保存 secret value，只保存 opaque reference。
- 不跨客户复用私有事实和证据。
- 外部发送、发布、私信、删除、覆盖、批量动作和账号切换必须取得精确批准并回读验证。
- 运行区不得提交母库 Git。
- 客户、任务和 active context 只通过受控脚本创建或切换；不要手工拼接跨文件绑定。
- `00_control/.runtime-write.lock` 存在时停止读写并检查恢复状态，不得直接抢锁。
- 依赖搜索前先保证 generated index/catalog 已同步并通过 validator。
