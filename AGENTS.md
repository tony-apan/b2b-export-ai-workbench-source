---
title: "AGENTS.md"
description: "Codex 和其他 agent 维护本母库及独立子库时必须遵守的最高项目规则与权威文档路由。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-30"
sources: ["Tony structure upgrade decision 2026-07-28"]
related: ["CONTEXT.md", "wiki/00_meta/current-focus.md", "wiki/00_meta/ai-operating-manual.md", "wiki/00_meta/task-router.md", "wiki/00_meta/check-mechanism-map.md", "sub-libraries/README.md"]
---
# AGENTS.md

你是这个持续进化的外贸增长知识库的维护者。本文件定义不可突破的项目规则和权威入口；详细 SOP 留在对应 wiki、manifest 和子库合同中，避免根文件分叉。

## 规则优先级

1. 用户当前明确要求。
2. 本文件。
3. [AI Operating Manual](wiki/00_meta/ai-operating-manual.md)。
4. 与任务 scope 对应的 wiki 标准、母库/子库 manifest、runtime contract 和 release guide。
5. `README.md`、`CONTEXT.md`、`CLAUDE.md` 仅作路由，不得覆盖以上规则。

## 仓库身份与数据边界

- 根目录是逻辑母库；`sub-libraries/` 下每个注册目录是可独立交付、独立验证和独立发布的子库。
- `raw/` 是私有母库来源接口；任何公开子库或公开 artifact 只允许包含被其 manifest、builder、metadata、内容与 digest 共同 allowlist 的安全 synthetic fixture。
- 真实客户、账号、凭据、课程原文、经营数据和私有运行证据只进入客户私有运行区；即使母库为私有 Git 仓，也不得把凭据和客户运行数据直接提交。
- 母库、子库和客户运行区不得共享发布 PASS。母库私有源码同步、子库 Public Preview 与 Stable Release 是三个独立状态；改变 remote、可见性、提交、tag、push 或发布必须得到用户明确授权。

权威结构见 [母库/子库模型](wiki/00_meta/private-master-and-sub-library-model.md)、[子库合同](wiki/00_meta/sub-library-contract.md) 和 [发布去敏规则](wiki/00_meta/publishing-and-redaction.md)。

## 入口与 canonical 规则

- 新任务先读 [CONTEXT.md](CONTEXT.md)、[wiki/index.md](wiki/index.md)、[current-focus.md](wiki/00_meta/current-focus.md) 和目标目录入口；不要为小任务扫描全库。
- `wiki/` 目录使用 `index.md` 作为 canonical 入口。允许 README-only 的非 wiki 目录必须声明 `canonical_entry: "README.md"`。
- index 同时服务人和 AI，只索引当前目录直接文件与直接子目录 canonical 入口；description、`when_to_read` 和 keywords 必须可帮助检索，不递归铺平全库。
- index 生成区由脚本维护，不手工编辑。规则和命令见 [index-and-discovery-standard.md](wiki/00_meta/index-and-discovery-standard.md) 与 [scripts/README.md](scripts/README.md)。
- 新 durable page 默认用 `id-####-slug.md` 和匹配的 `doc_id`；编号范围与豁免见 [document-id-standard.md](wiki/00_meta/document-id-standard.md)。

## 内容归宿

| 内容 | 归宿 / 权威入口 |
|---|---|
| 原始对话与来源上下文 | [raw/index.md](raw/index.md)；对话进入 `raw/10_conversations/` |
| 提炼知识、方法、业务模型 | [wiki/index.md](wiki/index.md) 与目标模块 index |
| 课程、练习、验收、写回 | [wiki/90_outputs/courses/index.md](wiki/90_outputs/courses/index.md) |
| 每日事件和月度摘要 | [wiki/00_meta/logs/index.md](wiki/00_meta/logs/index.md) |
| 可独立交付能力 | [sub-libraries/README.md](sub-libraries/README.md) 与 registry 指向的子库 README |

原始对话不能直接包装成课程结论；日志只保存事件与证据指针，不复制 raw，也不替代稳定知识页。分别遵守 [raw-to-course 流水线](wiki/00_meta/raw-conversation-and-course-pipeline.md) 和 [日志标准](wiki/00_meta/logging-standard.md)。

## 子库与 Skill

- 子库是完整能力模块，不自动等于 Skill。
- 只有子库 manifest 声明 `skill_entrypoint` 时，子库内的 `SKILL.md` 才是条件性交付入口；根目录不建立并行的 `skills/` 第二真源。
- 进入子库后，先读其 `README.md`、`MANIFEST.md`、`AGENTS.md` 和 `RUNTIME-CONTRACT.json`；Skill 不能覆盖系统、用户、宿主项目或本文件的更高优先级规则。
- 未达到对应 scope 的 `Ready` 或 `Published` 前，不得对外宣称稳定可用。

## 发布与证据边界

- 母库和每个子库分别拥有 manifest、builder、validator、approval/evidence 和 tag namespace；一个 scope 的结果不能替代另一个 scope。
- builder 只冻结候选；正式资格由候选外的 approval/evidence 与同一候选绑定。具体状态与流程以 [release-state-machine.md](wiki/00_meta/release-state-machine.md)、[release-approval-and-tag-namespaces.md](wiki/00_meta/release-approval-and-tag-namespaces.md) 和目标 scope 的 release guide 为准。
- `APPROVAL_RECORD_PASS` 只证明记录结构和候选绑定，不证明 `approved_by` 是真人。实际 tag object SHA、signer fingerprint、canonical tag annotation 和 approval digest 必须由外部 workflow 注入并精确比对。
- 本地 workflow shape、测试、archive、checksum、attestation 或 `qualified-not-published` 都不能单独证明远端保护、真人批准、生产稳定、课程效果或 Published。
- 所有 verdict 必须按 [check-mechanism-map.md](wiki/00_meta/check-mechanism-map.md) 说明 scope、对象、证据和未验证边界；发布前按 [release-checklist.md](wiki/00_meta/release-checklist.md) 检查。

## 工作与完成

- 先查真实文件和当前状态；区分事实、推断、缺口与冲突。没有来源的内容标注“推断”或“待验证”。
- 新来源先登记，再提炼；可复用结果写回 wiki，未决项写入 [open-questions.md](wiki/00_meta/open-questions.md)，事件追加到当日日志。
- 业务任务先读 `wiki/40_business/` 和相关 playbook；缺业务底座时只能输出假设版。
- 涉及社媒账号时必须遵守 [social-account-safety.md](wiki/00_meta/social-account-safety.md)，AI 不直接登录或自动化发布、互动、私信。
- 按 [definition-of-done.md](wiki/00_meta/definition-of-done.md) 验收；完成后报告改动、验证、残余风险和下一步，不得隐藏 BLOCK。
