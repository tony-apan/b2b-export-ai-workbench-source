---
title: "Agency Operations Agent Rules"
description: "agency-operations 子库及其生成运行区的最高局部协议，强调客户 scope、私密数据、人工批准和 fail-closed。"
type: "agent-protocol"
status: "Canonical"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["README.md", "RUNTIME-CONTRACT.json", "PLAYBOOK.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# AGENTS.md

## 优先级

用户当前明确要求 → 母库根 `AGENTS.md` → 本文件 → `RUNTIME-CONTRACT.json` → 任务与渠道 playbook。

## 强制规则

- 所有客户读取、搜索、写入和执行必须显式绑定已注册 `client_id`。
- 涉及执行时同时绑定 `task_id`；涉及外部账号时继续绑定 `company_id`、`channel_id`、`account_id` 和精确目标。
- 不跨客户复制原始资料、线索、价格、联系人、账号、cookie、token、证据或聊天。
- 凭据只保存 opaque secret reference，不保存 secret value。
- 运行区是用户持续可写 scope；本子库模板和母库 core 对普通运行任务只读。
- 未获得对象级批准，不得发送邮件、来发信消息、社媒互动、CMS 发布、删除或批量覆盖。
- 写回母库前必须去标识化并人工审核。
- 任一 Registry、目录、catalog 或 realpath 不一致均 BLOCK。
- 客户、任务和 active context 只通过受控脚本创建或切换；任务中的产品、渠道和账号必须显式绑定且不跨公司。
- `00_control/.runtime-write.lock` 存在时停止读写；不得绕过锁或在未检查恢复状态时删除 stale lock。
- 搜索在按 `client_id` 筛选前必须验证全部 catalog，catalog stale、超大文本或结果过宽均 BLOCK。
