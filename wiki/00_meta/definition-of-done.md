---
title: "Definition of Done"
description: "定义资料吸收、业务输出、实验记录、页面合并、wiki 体检等任务怎样才算完成。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["Subagent adversarial review", "Repository routing synchronization 2026-07-29"]
related: ["task-router.md", "quality-checklist.md", "check-mechanism-map.md", "release-checklist.md", "agent-handoff.md"]
---
# Definition of Done

“完成”必须同时满足任务产物、发现入口、验证证据和未验证边界；机器 PASS 不自动升级为业务、课程或发布完成。

## 所有文档任务

- 已确认目标 scope 是母库、某个子库或客户私有运行区，没有跨 scope 写入。
- description 用人话说明对象、问题、读取时机和边界；需要时填写 `when_to_read` 与 3–8 个 keywords。
- 新 durable page 符合 ID 规则；redirect 只保留兼容，不再被活动文档、front matter 或 registry 当 canonical 引用。
- 已更新文件元数据和必要入口，并运行 index sync；没有手改 index 生成区。
- 已运行与改动相关的 index、link、document ID 或专用校验，并记录未验证项。

## 资料吸收与知识写回

- 已从 [raw/index.md](../../raw/index.md) 进入并确认来源类型、Source ID、版权/许可和敏感性。
- 原始对话保存在 `raw/10_conversations/`；没有把 raw 原文复制进日志或直接包装成课程结论。
- 已更新 [source-registry.md](../10_sources/source-registry.md) 和相关 concept/business/channel/playbook 页面；事实、推断和待验证已区分。
- 可复用结论已写回稳定 wiki；缺口已进入 [open-questions.md](open-questions.md)。
- 当日日志只追加事件与证据指针；旧 [ingestion-log.md](ingestion-log.md) 只作历史汇总。
- 课程、客户、账号或第三方资料已同步许可登记和敏感数据检查。

## 课程模块

- 课程内容可追溯到 source 与提炼知识，并包含学习目标、练习、验收标准和 writeback。
- 结构校验通过只记为 `KNOWLEDGE_CHAIN_STRUCTURE_PASS`。
- 宣称真实效果前，已有真实学员提交、独立 reviewer、唯一 event/snapshot、artifact digest、verification record 和 writeback；作者自评不算独立验收。

## 业务输出

- 已读取业务底座和相关 playbook，标明对象、场景、依据、假设、风险和适用边界。
- 没有把占位页、无来源判断或 synthetic fixture 写成真实客户事实或效果承诺。
- 值得复用的版本进入 `wiki/90_outputs/` 或相关 playbook；暴露的缺口进入 open questions。
- 涉及对外发送、发布、账号操作或 CMS 写入时，已获得明确授权并完成目标系统回读；toast/HTTP 200 不等于完成。

## 新模块或子库

- 已按 [module-expansion-sop.md](module-expansion-sop.md) 判断应进入 channel、playbook、business、concept、template 或独立子库，而不是默认新建平级目录。
- 已建立 canonical 入口、必要来源/模板、registry 或 module registry 记录，并让父级入口可发现。
- 如为子库，manifest 明确 durable roots、delivery modes、dependency mode、runtime contract 与独立 release 状态。
- 只有 manifest 声明 `skill_entrypoint` 时才交付子库内 `SKILL.md`；未建立根级 `skills/` 第二真源。

## 日志与阶段闭环

- 每日事件 ID、actor、scope、action、evidence、result、risk 和 next 完整且可验证。
- 阶段/月度结束时生成摘要：稳定结论回写 wiki，未决项回写 open questions，原始日志保留溯源。
- 日志 validator PASS 只证明结构，不证明事件真的发生或证据内容正确。

## 候选与正式发布

### 候选准备完成

- 已明确单一 scope、version、source commit 与 content digest；母库和子库结果未串用。
- 当前 scope 的 manifest、license、approval 和 verification 状态被原样保留，没有把 `BLOCK` 改写成 Ready。
- 默认不发布真实 `raw/`；公开 synthetic fixture 同时满足路径、metadata、内容、许可和精确 digest allowlist。
- 已通过当前 scope 要求的结构、严格 index/link/log、知识链、制品和 runtime 检查；每个 PASS 的证明范围按 [check-mechanism-map.md](check-mechanism-map.md) 记录。

### Qualification 完成

- 候选外 approval/evidence 与同一 candidate 精确绑定；`APPROVAL_RECORD_PASS` 未被写成真人身份验证。
- 外部 workflow 已注入并比对实际 tag object SHA、target commit、signer fingerprint、canonical annotation 与 approval digest。
- 可信 workflow/governance、远端保护、runtime profile、archive/checksum 与 attestation 有真实服务端证据；缺失项保持 BLOCK。
- 输出最多记为 `qualified-not-published`，不自动改写 manifest 或创建 Published 事实。

### Published 完成

- 有权批准者已针对精确 scope/version/digest 和目标渠道作出明确发布决定，身份与授权由外部证据支持，而不是名称字符串。
- 目标平台已实际产生可回读的发布 URL/ID、时间、actor、checksum/digest、发布记录和下架入口。
- 发布后验收、失败处理与回滚/下架条件已记录；Published 不外推到其他 scope 或未来稳定性。

## 最终交付报告

- 列出改动文件、执行命令、PASS/WARN/BLOCK、证据位置和残余风险。
- 明确哪些事实只在本地、指定部署或指定时间窗口成立。
- 未经授权不执行 `git add`、commit、tag、push、remote 修改或发布。
