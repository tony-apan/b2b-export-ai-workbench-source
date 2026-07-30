---
title: "Writeback: Synthetic Raw-to-Course Closure"
description: "记录 synthetic fixture 从 raw 到课程闭环后的知识写回、证据边界和下一步动作，确保索引概念、提炼 playbook、课程练习和发布闸不会只停留在一次性输出。"
type: "writeback-record"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["SRC-20260728-0001"]
related: ["../id-0004-structure-to-course-closure.md", "../verification/VER-20260728-raw-course-closure.md", "../../../00_meta/open-questions.md"]
writeback_id: "WB-20260728-raw-course-closure"
course_doc_id: "ID-0004"
writeback_status: "pending"
verification_record: "../verification/VER-20260728-raw-course-closure.md"
review_record: ""
change_summary: "仅记录 synthetic 结构说明与待办边界；没有真实练习提交、人工 review、效果证据或 release 批准。"
writeback_targets: ["../id-0004-structure-to-course-closure.md", "../verification/VER-20260728-raw-course-closure.md"]
snapshot_refs: []
visibility: "public"
redaction_status: "safe-to-publish"
event_refs: ["EVT-20260728-0007", "EVT-20260728-0009"]
snapshot_status: "working-tree-dirty; structural evidence only; no release digest"
---
# Writeback: Synthetic Raw-to-Course Closure

## Event

- **Writeback ID**：`WB-20260728-raw-course-closure`
- **Date / time window**：2026-07-28
- **Module / channel**：Knowledge-base governance / course pipeline
- **Related task**：完成一个去敏 raw → course 闭环样本
- **Data scope**：public / virtual

## Observed Evidence

- What happened：建立 synthetic raw fixture、Source Registry 条目、ID-0002 concept、ID-0003 playbook、ID-0004 course、verification record 和 writeback record。
- Source path / evidence path：`raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md` 及验证记录。
- Volume / sample size：1 个虚拟来源、3 个派生 durable page、1 个课程题目、0 个练习提交、0 条人工 review、1 条待完成验证说明、1 条待完成写回说明。
- Direct quote or exact signal：虚拟样本明确提出 index 分层、Raw 不直接成为课程和日志只记录事件指针三个问题。
- Data quality limitation：只有 synthetic fixture，未提供真实用户、市场或学习效果证据。

## Interpretation

- Confirmed fact：当前工作树的页面可以表达 raw → source → concept/playbook → course → verification/writeback 的结构关系；exercise 提交、人工 review 和效果证据仍不存在。
- Inference：为每个目录提供人话 description、读取时机和检索词，理论上更利于人和 AI 做入口筛选；本轮没有测量检索性能。
- Hypothesis：真实课程若加入第二场景和人工评分，能比只复述原文更好地区分“记住内容”和“掌握方法”；待真实教学样本验证。
- Contradiction：无。
- Confidence：medium（仅限结构和流程表达）。

## Knowledge Changes

| Knowledge area | Page / registry | Change | Status before → after | Evidence |
|---|---|---|---|---|
| source | `wiki/10_sources/source-registry.md` | 增加 synthetic Source ID 及派生页面 | 未登记 → ingested | Source note + raw path |
| concept | `wiki/20_concepts/id-0002-index-discovery-contract.md` | 提炼 index 的职责、字段和验收问题 | 无样本 → Working | synthetic fixture |
| playbook | `wiki/30_playbooks/id-0003-raw-to-course-closure.md` | 固化 raw 到课程的步骤和质量检查 | 只有治理规则 → Working | pipeline rule + fixture |
| course | `wiki/90_outputs/courses/id-0004-structure-to-course-closure.md` | 增加课程目标、第二场景练习和边界 | 空目录 → Draft | course module |
| verification | `VER-20260728-raw-course-closure` | 记录三层状态和非声明 | 无记录 → pending | verification note；无 snapshot/人工 review |

## Action

- Keep：保留当前分层 index、source registry、课程练习和范围化验证格式。
- Revise：真实课程样本到来后，补充人工评分、失败样本和课程版本变更记录。
- Stop：不把 synthetic fixture 当作真实客户或市场证据，不因此解除发布 BLOCK。
- Next experiment or content update：在私有运行区使用一个已授权真实样本，重复相同链路并单独记录脱敏结果。
- Owner：AI；Human reviewer 待指定且尚未批准
- Review date：2026-08-28

## Safety And Publication

- PII / client data removed：yes / not applicable（本样本为虚拟内容）
- Copyright / license checked：yes（原创 synthetic fixture；外部正式课程仍需单独确认）
- Public release impact：review required；不解除母库或子库 `release_status: BLOCK`
- Human approval：pending
