---
title: "Module Expansion SOP"
description: "定义候选需求如何通过当前焦点、最小证据和验收闸晋升为新模块，防止一次铺开大量空目录。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-26"
sources: ["User request", "Adversarial structure review 2026-07-26"]
related: ["current-focus.md", "module-registry.md", "markdown-standard.md", "task-router.md"]
---
# Module Expansion SOP

## Step 0：先过焦点闸

新增模块前先读 [current-focus.md](current-focus.md)。当前 Active 模块未 `Validated` 时，新需求默认按以下顺序处理：

1. 能否作为当前模块的知识依赖；
2. 能否作为当前模块的 adapter；
3. 能否作为当前模块的第二工具或相邻任务迁移练习；
4. 以上都不适用，才登记到 registry 的 `Backlog Candidates`。

未经人工切换焦点，不创建新的平级课程、子库、品牌或大型目录。

## Step 1：判断知识类型

| 类型 | 放哪里 | 例子 |
|---|---|---|
| Channel | `wiki/50_channels/{module}/index.md` | LinkedIn、Ads |
| Playbook | `wiki/30_playbooks/{module}.md` | 视频制作、客户访谈 |
| Business System | `wiki/40_business/{module}.md` | 产品内容、offer 系统 |
| Concept | `wiki/20_concepts/{module}.md` | buyer intent、social proof |
| Template | `wiki/_templates/{module}.md` | brief、记录表 |
| Adapter | 当前子库的 `ADAPTERS/{tool}.md` | CMS、图床、平台字段差异 |
| Sub-library | `sub-libraries/{module}/` | 能独立交付的完整任务闭环 |

先补已有页面，不因一个新名词自动新建 Module。

## Step 2：晋升条件

候选需求只有同时满足以下条件，才从 `Backlog` 晋升：

- 有重复出现的真实任务或明确用户决定；
- 当前模块无法合理承载；
- 能定义独立业务结果、输入、输出、指标和完成闸；
- 有至少一个来源或真实样本；
- 明确 owner 和停止条件；
- 人工确认新的 Active / Blocked / Dormant 状态。

## Step 3：最小文件集

正式模块至少需要：module index、主 playbook、必要模板、来源入口、registry 记录和总索引链接。若做可分发子库，还必须遵守 [sub-library-contract.md](sub-library-contract.md)。

当前公开仓库只创建 raw 占位说明，不创建或提交真实 `raw/{module}/` 数据。真实来源进入私有母库或客户运行区。

## Step 4：模块 SOP 必答

- 解决什么业务结果？
- 输入来源和权限是什么？
- 稳定对象、字段和状态是什么？
- 输出和真实成功证据是什么？
- 哪些动作必须人工审批？
- 失败如何诊断和回滚？
- 指标和写回位置是什么？
- 什么时候 `BLOCK`，什么时候 `Validated`？

## Step 5：何时做 Skill

先沉淀 playbook，并在真实任务中重复运行 3–5 次。只有输入输出稳定、权限边界清楚、失败模式可复现时，才考虑抽象为 skill。skill 不能用来掩盖尚未跑通的业务流程。
