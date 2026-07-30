---
title: "Verification: Synthetic Raw-to-Course Closure"
description: "验证 synthetic fixture 是否已经形成 raw、source registry、concept、playbook、course、第二场景练习、验证和写回的可追溯文件链；结论只适用于本地公开安全样本。"
type: "verification-record"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["SRC-20260728-0001"]
related: ["../id-0004-structure-to-course-closure.md", "../../../00_meta/raw-conversation-and-course-pipeline.md", "../writeback/WB-20260728-raw-course-closure.md"]
verification_id: "VER-20260728-raw-course-closure"
course_doc_id: "ID-0004"
structure_verification_status: "pending"
exercise_verification_status: "pending"
effectiveness_verification_status: "unverified"
exercise_artifact: ""
review_record: ""
sample_size: 0
observed_result: "当前仅观察到 synthetic 文件链可表达并可由普通结构校验解析；未保存不可变结构快照，练习未提交且未人工评分。"
allowed_claim: "当前工作树中的 synthetic 文件链可用于演示三层状态和结构校验边界。"
non_claim: "不证明真实练习完成、真人复核、真实学习或业务效果、外部批准或 release eligibility。"
snapshot_refs: []
visibility: "public"
redaction_status: "safe-to-publish"
event_refs: ["EVT-20260728-0007", "EVT-20260728-0009"]
snapshot_status: "working-tree-dirty; structural evidence only; no release digest"
---
# Verification: Synthetic Raw-to-Course Closure

## Scope

- **Verification ID**：`VER-20260728-raw-course-closure`
- **Target**：`SRC-20260728-0001` 及其派生页面
- **Environment**：当前知识库工作区（不写入机器绝对路径）
- **Version / commit**：未提交工作树；以 2026-07-28 文件状态为准
- **Operator**：Codex
- **Reviewer**：未提供；AI 记录不等于真人复核
- **Date**：2026-07-28

## Claim Being Tested

- **Claim**：一个公开安全的 synthetic fixture 能否按规则形成可追溯的 raw → source → concept/playbook → course → exercise → verification → writeback 闭环。
- **Allowed interpretation**：当前工作树中的本地文件链、索引入口和 Source ID 可被普通结构校验解析；该结果不升级 exercise 或 effectiveness 状态。
- **Explicit non-claim**：不证明真实客户需求、真实学员学习效果、生产运行能力、许可证已批准或母库/子库可发布。

## Preconditions

- 输入：明确标记 `synthetic: true` 的虚拟对话；
- 权限：只写本地公开安全知识库；
- Fixtures：没有真实客户、账号、Cookie、Token、课程原文或经营数据；
- 人工审批点：课程公开范围、第二场景人工评分和许可证确认仍需人工复核。

## Steps And Evidence

| Step | Action | Expected | Observed | Evidence path / URL | Result |
|---|---|---|---|---|---|
| 1 | 读取 synthetic raw fixture | 明确虚拟、公开安全和来源 ID | `synthetic: true`，Source ID 一致 | `raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md` | pass |
| 2 | 登记 Source ID | registry、raw path 和派生页一致 | 已登记 `SRC-20260728-0001` | `wiki/10_sources/source-registry.md`、`wiki/10_sources/SRC-20260728-0001.md` | pass |
| 3 | 提炼 concept/playbook | 不把样本扩写成市场事实 | 两页均注明证据边界 | `wiki/20_concepts/id-0002-index-discovery-contract.md`、`wiki/30_playbooks/id-0003-raw-to-course-closure.md` | pass |
| 4 | 建立课程和第二场景题目 | 有学习目标、题目、验收门槛和人工审批点 | `ID-0004` 包含迁移题目，但没有提交 artifact 或人工评分 | `wiki/90_outputs/courses/id-0004-structure-to-course-closure.md` | pending |
| 5 | 记录结构检查边界 | 入口可被当前工作树解析且不冒充效果 | 本记录只保存结构观察说明，没有不可变 snapshot/commit 证据 | `wiki/90_outputs/courses/index.md`、`verification/index.md`、`writeback/index.md` | pending |
| 6 | 准备写回说明 | 记录观察、未证明事项和下一步 | WB 页面存在，但 `writeback_status` 保持 `pending`，没有 snapshot 或人工批准 | `wiki/90_outputs/courses/writeback/WB-20260728-raw-course-closure.md` | pending |

## Result And Boundary

- **Structure status**：`pending`。普通 `node scripts/validate-knowledge-chain.mjs` 可以报告结构级结果，但该命令不生成不可变 snapshot，也不证明 release eligibility。
- **Exercise status**：`pending`。第二场景未提交，`exercise_artifact` 和 `review_record` 为空。
- **Effectiveness status**：`unverified`。没有真实教学、客户、市场或生产效果样本。
- **Allowed result**：仅可说当前 synthetic 页面演示了可解析的来源链和三层状态合同。
- **Release boundary**：`--release` 必须继续因缺真实提交、人工 review、snapshot/commit 绑定和外部签名 sidecar 而 BLOCK。

## Risks And Follow-up

- Residual risk：人工尚未对第二场景练习评分；synthetic fixture 可能让流程看起来比真实资料简单。
- Next verification：使用一个经过授权的真实或私有运行区样本，重复同一流水线，不把原文写入公开母库。
- Rollback / takedown condition：若发现样本含真实个人信息、未授权课程内容或错误来源声明，立即移入私有运行区并从公开候选包排除。

## Writeback

- Updated page / registry / log：Source Registry、ID-0002、ID-0003、ID-0004、课程索引、写回记录和 2026-07-28 日志。
- Evidence retained：本地文件路径和校验命令输出；未保留真实账号或外部凭据。
- Open question created：yes；人工评分阈值和 synthetic fixture 统一字段仍待确定。
