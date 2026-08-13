---
title: "Agency Runtime Integration"
description: "规定 website-content-ops 如何只在 agency-operations 提供的 customer-runtime 客户任务作用域内运行，并在缺少 client_id、company_id、task_id 或机器真源不一致时 fail-closed。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-08-02"
last_updated: "2026-08-02"
sources: ["RUNTIME-CONTRACT.json", "Tony multi-client runtime decision 2026-08-01"]
related: ["README.md", "START-HERE.md", "INSTALL.md", "WORKSPACE-TEMPLATE/README.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "初始化客户内容任务、升级本包、搜索客户资料或准备把 WORKSPACE-TEMPLATE 内容投影放入客户任务时。"
keywords: ["agency-operations", "customer-runtime", "client scope", "task binding", "fail-closed", "runtime dependency"]
---
# Agency Runtime Integration

`website-content-ops` 是内容能力包，不再自行定义并行的客户工作区控制面。它声明对 `agency-operations` runtime contract 的必需外部依赖。

## 进入任务前的机器闸

开始任何客户资料读取、写入、搜索、CMS 准备或证据记录前，宿主必须通过 `agency-operations` 的受支持命令建立并验证：

1. `customer-runtime/RUNTIME.json`；
2. `00_control/ACTIVE-CONTEXT.json`；
3. `00_control/clients-registry.json` 与 `task-registry.jsonl`；
4. 对应客户的 `CLIENT.json`；
5. 对应任务的 `TASK.json` 与 `HANDOFF.md`；
6. 同一活动 scope 精确绑定 `client_id + company_id + task_id`。

缺少任一项、Registry 与目录不一致、ACTIVE-CONTEXT 与 TASK 不一致、路径逃逸、symlink、跨客户结果、写锁存在或 scope 为空时，必须停止。不得退回无 scope 的 `rg customer-runtime`、手工 Markdown 状态表或旧 `workspace/` 目录。

## 内容投影如何放置

`WORKSPACE-TEMPLATE/` 只是一组 synthetic 内容目录和只读规范投影，不是独立 runtime。完成 agency runtime 初始化和任务激活后，才可把所需内容模板放入该任务的受控输出/工作目录；`TASK.json` 仍是状态机器真源，`HANDOFF.md` 是人类续接页，`30_tasks/index.md` 只说明内容能力和生成投影，不能记录任务状态。

## 升级规则

- 更新本包只替换 tracked core；
- 不得重新复制 `WORKSPACE-TEMPLATE/` 覆盖已有 `customer-runtime/`；
- 不得改写 Registry、ACTIVE-CONTEXT、CLIENT、TASK、HANDOFF、日志、证据或客户输出；
- schema 不兼容时先备份、迁移、验证和准备回滚；本包自身不提供 runtime migration；
- `agency-operations` 未安装、版本/合同不满足或 validator 未通过时，本包只能用于 public synthetic 示例，不得承载真实客户运行。

## 写回

客户事实、搜索证据、文章草稿、CMS 记录、指标和询盘结果只进入当前客户任务 scope。可复用方法先进入该客户的 `90_writeback/`，去标识化并人工审核后，才可回到本包的 canonical playbook；不能把客户运行数据复制进公开源码或 release artifact。
