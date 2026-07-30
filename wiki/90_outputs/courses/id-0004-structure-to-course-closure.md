---
doc_id: "ID-0004"
title: "Structure to Course Closure"
description: "面向知识库维护者和 AI，训练如何把一个去敏结构治理案例转换为来源、概念、playbook、课程练习、验收和写回记录，帮助复用完整闭环；不证明真实客户或生产发布能力。"
type: "course-module"
status: "Draft"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["SRC-20260728-0001"]
related: ["../../00_meta/raw-conversation-and-course-pipeline.md", "../../20_concepts/id-0002-index-discovery-contract.md", "../../30_playbooks/id-0003-raw-to-course-closure.md", "verification/VER-20260728-raw-course-closure.md", "writeback/WB-20260728-raw-course-closure.md"]
visibility: "public"
redaction_status: "safe-to-publish"
course_id: "COURSE-2026-0001"
module_order: 1
level: "beginner"
when_to_read: "当需要学习或演练一条完整的 raw 到课程知识闭环时，先读本页；如果要发布真实客户课程或外部产品能力，还必须另行完成授权和运行验证。"
keywords: ["course module", "raw to course", "index governance", "exercise", "verification", "writeback"]
learning_outcomes:
  - "能判断一份 raw 是否可以公开处理，并为其建立 Source ID。"
  - "能把事实、推断、冲突和待验证项分开。"
  - "能把稳定方法提炼为 concept/playbook，而不是复制原始对话。"
  - "能设计一个不同于原始样本的第二场景练习并按范围验收。"
structure_verification_status: "pending"
exercise_verification_status: "pending"
effectiveness_verification_status: "unverified"
exercise_artifact: ""
review_record: ""
verification_record: ""
writeback_record: ""
---
# Structure to Course Closure

## 1. 适用对象与前置条件

- **适用对象**：维护 Markdown 知识库的 AI、课程设计者和需要做知识写回的新人。
- **前置知识**：知道 `raw/`、`wiki/`、`index.md`、Source ID 和 Markdown front matter 的基本用途。
- **不适用场景**：真实客户资料、账号数据、未授权课程原文或需要正式发布的生产能力验证。

## 2. 学习目标

学员完成后必须能够：

- 识别 raw、source、concept、playbook、course、verification 和 writeback 的职责边界；
- 为一份去敏或虚拟样本建立可追溯的来源登记；
- 把原始表达转换为明确的事实、推断、冲突和开放问题；
- 设计第二场景练习，证明方法可以迁移而不是只会复述原样本；
- 在局部通过后仍正确保留母库和子库的发布 BLOCK。

## 3. 来源与证据

| Source ID / 页面 | 支持的事实或方法 | 证据状态 | 备注 |
|---|---|---|---|
| [SRC-20260728-0001](../../10_sources/SRC-20260728-0001.md) | 一个明确标记为 synthetic fixture 的结构治理对话，以及从 raw 到课程的提炼边界 | confirmed within fixture | 不代表真实客户或市场证据 |
| [Index as Retrieval Contract](../../20_concepts/id-0002-index-discovery-contract.md) | 当前层索引、description、读取时机和检索词的职责 | confirmed by repository rule | 需要结合索引校验脚本 |
| [Raw to Course Closure](../../30_playbooks/id-0003-raw-to-course-closure.md) | 来源登记、提取、课程、练习、验证和写回的步骤 | confirmed by repository rule | 不解除发布合同 |

## 4. 核心概念

- `raw/` 保留来源形态和上下文，不直接承载稳定结论；
- Source ID 是从原始材料到派生知识的溯源主键；
- `index.md` 是当前文件夹的检索合同，不是全文复制区；
- 课程必须加入第二场景练习和范围化验收；
- `PASS` 只适用于声明范围，不自动等于 `Ready` 或 `Published`。

## 5. 可执行步骤

1. 阅读 synthetic fixture，确认它没有真实客户、账号或未授权课程资料。
2. 在 source registry 中核对 Source ID、raw path、公开状态和派生页面。
3. 对原始表达做四栏提取：confirmed facts、inferences、conflicts、open questions。
4. 阅读 concept 和 playbook，确认哪些内容是可复用规则，哪些只是样本情境。
5. 完成第二场景练习：为一个“邮件开发 playbook 文件夹”设计分层 index，不能复制结构治理样本的原句。
6. 运行索引、ID、结构和制品检查，记录证据和边界。
7. 将结果写回 verification record、writeback record、source registry、相关 index 和 daily log。

## 6. 练习

### 第二场景：邮件开发 Playbook 目录设计

- **输入**：一个虚拟目录，包含 `cold-email.md`、`subject-lines.md`、`reply-handling.md`、`metrics/index.md` 和一个 `templates/` 子目录。
- **操作**：设计当前目录的 `index.md` 直接入口表；每个描述必须说明文档对象、解决的问题、读取时机和不覆盖的边界；不得把模板正文复制进 index。
- **输出**：一份 Markdown 索引草案，以及一段说明为什么模板目录需要自己的 canonical 入口。
- **约束**：不得声称这些页面已在真实客户或 Search Console 数据上验证；必须标注假设和待验证项。

## 7. 验收标准

> 当前第二场景仍是“已布置、未提交、未人工评分”；下面的标准是验收门槛，不是已完成声明。

- [ ] 能指出 raw、source registry、concept、playbook、course 和 verification 各自的职责。
- [ ] Source ID、raw path 和课程来源表完全一致。
- [ ] 对话中的事实、推断和开放问题分开记录。
- [ ] 第二场景 index 只索引当前层直接入口，并包含人话 description、读取时机和检索词。
- [ ] 验证记录没有把 synthetic fixture 写成真实客户证据。
- [ ] 写回后能从母库 index 进入课程，再进入来源和验证记录。
- [ ] 母库与子库 `release_status: BLOCK` 未被本课程样本解除。

## 8. 三层状态与边界

- **Structure = pending**：仓库中已存在 synthetic fixture、source registry、concept、playbook、course、verification 和 writeback 页面，但本课程尚未绑定不可变 snapshot/commit 证据；普通 validator 的结构通过只说明当前文件链可解析，不能升级本字段。
- **Exercise = pending**：第二场景只是题目，尚无真实提交 artifact，也没有绑定 artifact SHA-256 的人工 review record。
- **Effectiveness = unverified**：没有真实学员、真实客户、对照样本或外部效果数据，不得宣称学习迁移、业务结果或生产效果。
- **失败模式**：把原始对话直接包装成课程结论；把题目当提交；把 AI 或 front matter 自填当真人复核；把结构 PASS 当效果 PASS 或发布批准。
- **人工审批点**：公开课程素材授权、真实提交复核、真实客户/课程原文去敏确认、正式发布和外部使用范围。

## 9. 学习结果写回

- 练习/实验记录：[VER-20260728-raw-course-closure](verification/VER-20260728-raw-course-closure.md)
- 指标或结果：synthetic fixture 链路文件齐全；静态结构和索引检查通过；学习者人工评分尚未完成。
- 新发现应更新的 concept/playbook：[Index as Retrieval Contract](../../20_concepts/id-0002-index-discovery-contract.md)、[Raw to Course Closure](../../30_playbooks/id-0003-raw-to-course-closure.md)
- 需要补充的 source 或 open question：真实场景课程验收与许可证审批仍待单独处理。
