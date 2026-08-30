---
title: "Agency Operations Sub-library"
description: "多客户代运营私有运行区的人类和 AI 入口；本地结构与 synthetic 准备已完成，发布和生产资格仍为 BLOCK。"
type: "sub-library"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["START-HERE.md", "AGENTS.md", "PLAYBOOK.md", "TOOLS.md", "QA-CHECKLIST.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "WORKSPACE-TEMPLATE/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
keywords: ["代运营", "多客户", "customer-runtime", "作用域搜索", "AI handoff", "母库更新"]
canonical_entry: "README.md"
state_source: "MANIFEST.md"
state_projection: ["preparation_status", "verification_status", "release_status", "license_status"]
preparation_status: "complete"
verification_status: "structure-pass"
release_status: "BLOCK"
license_status: "pending"
---
# 多客户代运营运行底座

本子库让用户把整个母库放在一个目录里，同时把真实客户工作放进根目录下 Git 隔离的 `customer-runtime/`。母库可继续更新，客户事实、聊天、日志、任务和证据不会被模板更新覆盖。

> 当前状态：**Preparation Complete / Draft / structure-pass / release BLOCK / license pending**。本地源码、模板、工具、Git 边界、权限检查、索引和 synthetic 对抗已准备完成；本轮没有创建根目录真实 `customer-runtime/`。真实客户隔离、多人并发、ACL/外部副本、云端升级 apply、备份恢复和生产稳定性属于后续独立 scope。

## 解决什么问题

- 多客户、多公司、多产品、多网站、社媒、来发信和邮件账号分 scope 管理；
- 新 AI 先读当前客户、任务和 handoff，不通读所有聊天；
- 搜索强制 `--client`，无客户 scope 直接失败；
- 上游母库和本地运行区分离，模板只初始化一次；
- 初始化强制目录 `0700`、文件 `0600`，并要求 POSIX owner uid 与当前用户一致；mode 或 owner 漂移后，写入、搜索和边界验证均 fail closed；这不等于已验证 macOS ACL、同步盘副本或真实多用户隔离；
- 客户经验先写入私有 writeback candidate，脱敏审批后再进入母库。

## Preparation Complete 意味着

- 用户拿到整个库后，AI 已有统一入口、客户/任务机器真源、handoff、日志、索引与 fail-closed 工具合同；
- 未来可在明确 `client_id` 和授权后初始化本地私有运行区，不需要再改 tracked 母库结构；
- 母库更新不会通过模板复制覆盖既有运行区，v1 更新工具只做 `--check`；
- 它不等于已发布、生产可用或真实客户验证通过。

## 未来首次初始化

以下命令仅在用户决定开始实际本地运行时执行；本轮未在仓库根创建真实运行区。

```bash
node sub-libraries/agency-operations/scripts/init-customer-runtime.mjs
node sub-libraries/agency-operations/scripts/create-client.mjs --client cli-acme --name "Acme Synthetic"
node sub-libraries/agency-operations/scripts/register-entity.mjs --client cli-acme --type product --id prd-main --name "Main Product" --company co-acme
node sub-libraries/agency-operations/scripts/create-task.mjs --client cli-acme --task tsk-first-task --title "First task" --products prd-main --activate
node sub-libraries/agency-operations/scripts/sync-runtime-indexes.mjs
node sub-libraries/agency-operations/scripts/validate-runtime-indexes.mjs
node sub-libraries/agency-operations/scripts/validate-runtime-boundary.mjs
```

切换已有任务时使用 `activate-task.mjs --client ... --task ...`，不要手工拼接客户、公司和任务绑定。执行前依次读取 [START-HERE.md](START-HERE.md)、[AGENTS.md](AGENTS.md)、[PLAYBOOK.md](PLAYBOOK.md) 和 [RUNTIME-CONTRACT.json](RUNTIME-CONTRACT.json)。

## Canonical 导航

- [START-HERE.md](START-HERE.md)：AI 启动顺序；
- [MENTAL-MODEL.md](MENTAL-MODEL.md)：Core、Template、Runtime 三层模型；
- [PLAYBOOK.md](PLAYBOOK.md)：初始化、建客户、建任务、续接、升级；
- [TOOLS.md](TOOLS.md)：命令和 fail-closed 行为；
- [QA-CHECKLIST.md](QA-CHECKLIST.md)：验收与未验证边界；
- [MANIFEST.md](MANIFEST.md)：唯一发布状态合同；
- [WORKSPACE-TEMPLATE/README.md](WORKSPACE-TEMPLATE/README.md)：运行区模板说明。

不创建 `SKILL.md`。只有真实运行多次、权限边界和验收稳定后，才讨论 AI Skill 适配器。
