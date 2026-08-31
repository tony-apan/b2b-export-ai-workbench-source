---
title: "Customer Workspace Template"
description: "复制到已激活 agency-operations task scope 中的 synthetic 内容模板和只读规范投影；不是独立 runtime，也不维护 machine state。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-02"
sources: ["TEMPLATES/README.md"]
related: ["00_intake/index.md", "90_writeback/index.md", "TEMPLATES/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
when_to_read: "已在 agency-operations 激活准确 task scope，准备复制 synthetic 内容结构或读取只读规范投影，并确认 machine state 仍由外部 runtime 维护时。"
keywords: ["workspace template", "client runtime", "privacy boundary", "writeback", "content operations"]
---
# 客户内容能力投影模板

本目录只包含可复制到**已激活 agency-operations 客户任务 scope** 的 synthetic 内容结构和只读规范投影。它不是独立 runtime，也不能改名为 `workspace/` 使用。

## 前置机器合同

复制任何内容前，宿主必须已通过 `agency-operations` 建立并验证：

- `customer-runtime/RUNTIME.json`；
- `00_control/ACTIVE-CONTEXT.json`；
- `clients-registry.json` 与 `task-registry.jsonl`；
- 当前客户 `CLIENT.json`；
- 当前任务 `TASK.json` 与 `HANDOFF.md`；
- 精确一致的 `client_id + company_id + task_id`。

缺少 scope、ACTIVE-CONTEXT/TASK 不一致、跨客户路径、symlink、路径穿越、写锁或 Registry 冲突时必须停止。禁止无 scope 搜索整个 `customer-runtime/`。

## 加载内容能力

1. 先在外部 runtime 中激活准确客户与任务；
2. 只选择当前任务需要的 `00_intake/`、`10_sources/`、`20_knowledge/`、`40_outputs/`、`50_metrics/`、`90_writeback/` 和 `TEMPLATES/` 内容结构；
3. `30_tasks/*.runtime.md` 是由 core playbook 生成并带 SHA-256 的只读规则投影；
4. 任务状态、owner、approval、blocker 和完成度只写 `TASK.json`，续接写 `HANDOFF.md`，事件写 runtime 日志；
5. [30_tasks/index.md](30_tasks/index.md) 只导航能力投影，不能维护并行任务表；
6. 升级 core 时重新核验 projection digest，但不得覆盖客户的 Registry、ACTIVE-CONTEXT、CLIENT、TASK、HANDOFF、日志、证据或输出。

## 内容目录

```text
content-capability-projection/
├── 00_intake/      # 当前任务需要的范围、授权和阻断材料
├── 10_sources/     # 当前客户 scope 内的来源登记
├── 20_knowledge/   # 当前客户 scope 内的公司、产品、ICP 和证据
├── 30_tasks/       # 只读规范投影和能力导航；不是状态真源
├── 40_outputs/     # 当前任务草稿、清单和交付物
├── 50_metrics/     # 当前任务可验证指标
├── 90_writeback/   # 去标识化前的客户私有学习候选
└── TEMPLATES/      # 内容记录模板
```

客户事实不得复制回 tracked core。可复用方法必须先去标识化并经人工审核，再按 [WRITEBACK.md](../WRITEBACK.md) 回落。
