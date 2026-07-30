---
title: "Raw Conversation and Course Pipeline"
description: "规定原始对话如何按来源形态归档、用元数据建立可查询维度，再经过 source registry、事实提炼、概念/playbook、课程模块、练习和写回形成可验证的教学内容。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["source-taxonomy.md", "knowledge-compounding-system.md"]
related: ["../../raw/index.md", "../../raw/10_conversations/index.md", "../10_sources/source-registry.md", "../90_outputs/courses/index.md", "../_templates/course-module.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "接收聊天、会议、访谈、AI 对话或课程材料，并需要后续检索、提炼或教学化时。"
keywords: ["raw", "conversation", "对话", "source registry", "课程", "提炼", "writeback"]
---
# Raw Conversation and Course Pipeline

## 先分清三层

| 层 | 保存什么 | 不保存什么 |
|---|---|---|
| `raw/` | 原文、转写、采集上下文、来源、同意/敏感级别 | AI 总结、SOP、课程结论 |
| `wiki/10_sources/` | Source ID、事实、引用、冲突、证据状态和来源摘要 | 未登记的“听起来像事实”的判断 |
| `wiki/20_concepts/`、`30_playbooks/`、`90_outputs/courses/` | 稳定定义、可执行方法、课程模块、练习、验收和写回 | 未验证的一次性经验 |

公开母库当前只接受公开来源索引、模板和去敏材料。真实客户对话、账号导出、课程原文和经营数据必须进入私有运行区；“放进 raw 方便搜索”不能绕过发布边界。

## 原始对话怎么分类

### 1. 物理目录按来源形态，不按每个主题建目录

```text
raw/
├── 00_inbox/          # 刚收到、尚未判定
├── 10_conversations/  # 聊天、会议、访谈、销售通话、AI 对话
├── 20_web/            # 网页、SERP、站点快照、公开评论
├── 30_documents/      # PDF、DOCX、表格、邮件导出
├── 40_media/          # 音频、视频、图片及其转写/说明
├── 50_exports/        # CRM、CMS、分析工具导出
└── 90_archive/        # 已处理、撤回、过期或不再进入公开编译层的资料
```

不要同时按“客户/渠道/月份/主题”无限嵌套物理目录；那会制造重复归档和路径漂移。主题、客户、渠道、语言和敏感级别放进 front matter，靠索引和全文搜索查询。

### 2. 对话文件命名

```text
src-YYYYMMDD-####-conversation-slug.md
```

对话 front matter 必须显式包含可为空的 `subject_ref` 与 `client_ref`；需要关联时只使用去标识化 `SUBJ-...` / `CLIENT-...` 引用。主题、渠道、客户等继续用 facets 查询，不为每个主题无限增加目录层级。

同一天的 `####` 是采集序号，不是知识质量评分。文件中的 `source_id`、`conversation_type`、`channel`、`participants`、`topics`、`sensitivity`、`consent_status`、`ingestion_status`、`derived_to` 是后续查询和追踪的主要字段。

建议 `topics` 使用受控词，同时允许 `keywords` 补充自然语言：

```yaml
topics: [icp, customer-pain, website, seo]
keywords: ["买家为什么不回复", "产品页转化", "搜索意图"]
```

### 3. 生命周期

```text
inbox → classified → registered → extracted → linked → ingested → derived → verified → archived
```

这是受控枚举；validator 对任何未知值 fail-closed。`new`、`done`、`processed` 等自由文本不得作为 lifecycle 值：

- `inbox`：刚收到，尚未完成分类；
- `classified`：放入正确 raw 分类并补元数据；
- `registered`：在 `source-registry.md` 分配 Source ID；
- `extracted`：分开记录 facts、quotes、conflicts、questions；
- `linked`：把证据链接到概念、playbook 或业务页；
- `ingested`：source note 已与 raw 双向绑定，并已登记完整五角色派生路径；
- `derived`：五角色页面已经形成，课程仍可处于 Draft；
- `verified`：独立练习制品、人工 review、event/snapshot、verification 与 writeback 全部完成；
- `archived`：保留溯源，但不再作为当前建议依据。

`ingested`、`derived`、`verified`、`archived` 都必须有非空且唯一的 `derived_to`。生命周期升级不能只改字符串，必须先满足对应证据。

## 从对话提炼课程的固定流水线

```text
raw conversation
  → source registry
  → facts / quotes / conflicts / open questions
  → concept or playbook candidate
  → course module draft
  → exercise with a changed scenario
  → verification record
  → writeback to source/wiki/metrics/open questions
```

硬规则：

1. 原始对话可以提供证据，不能自动成为通用事实。
2. 一次对话最多形成 `Seed` 课程候选；要升为 `Working`，至少有明确来源、学习目标、步骤、练习、验收标准和边界。
3. 要宣称可迁移，至少用第二个客户、第二个场景或陌生工具做练习；只复述原对话不算验证。
4. Source note 的 `derived_pages` 必须恰好包含五个唯一角色：`concept`、`playbook`、`course-module`、`verification-record`、`writeback-record`；raw 的 `derived_to` 必须与这五个页面的稳定 ID 完全一致，每个派生页还必须通过 `sources` 反向绑定 Source ID。
5. 五角色采用全局双向唯一合同：同一 `role + stable ID` 只能对应一个路径，同一路径也只能对应一个 `role + stable ID`。同一页面可被多个 Source ID 合法引用，但不得借不同路径复用同一 role ID，也不得让同一路径冒充不同角色或 ID。
6. 课程消费路径必须逐 Source ID 精确回指该 Source ID 的唯一五角色路径：course 必须等于 `course-module`，课程声明的 verification/writeback 必须分别等于 `verification-record` / `writeback-record`；course、verification 和 writeback 的 `sources` 集必须完全一致，不能用包含关系或后代路径绕过。
7. `reviewer_type`、`reviewer_id` 或旧式 `verification_status` 字符串不能证明真人身份或效果。状态必须拆成 `structure_verification_status: pending|verified|failed`、`exercise_verification_status: pending|verified|failed`、`effectiveness_verification_status: unverified|real-world-effectiveness-verified|failed`；未知值 fail-closed。
8. synthetic-only 来源链可以在独立证据支持下把结构和练习标为 `verified`，但效果必须保持 `unverified` 或 `failed`，永远不得升级为 `real-world-effectiveness-verified`。真实效果必须另有真实、授权、可复现的非 synthetic 证据。
9. release 证据至少包含四个不同且存在的文件：独立 exercise evidence、review record、verification record、writeback record。review record 必须绑定练习制品路径和该制品的 SHA-256；review、verification、writeback 必须各自包含 event refs 与存在的 snapshot refs。
10. 正式 approval 使用仓库外签名 sidecar，并绑定 canonical knowledge-chain manifest。manifest 必须冻结 `source_commit`、由所有链路 artifact 计算的 `snapshot_digest`，以及 raw、source note、concept、playbook、course、exercise、review、verification、writeback 的规范路径和 SHA-256；当前文件、签名 manifest、manifest digest 或 source commit 任一不一致都必须 BLOCK。
11. approval sidecar 中的姓名、agent 名称或 `reviewer_type` 不等于已验证身份。正式 release 还需 trusted GPG signer 和外部验证的 reviewer identity；synthetic test signer / `not_verified` 只能做攻击测试，不能解除正式发布 BLOCK。
12. Front Matter 按严格 YAML 平面映射解析：重复 key、对象型值、数组/标量类型混淆、非 boolean 的 `synthetic` 都必须 fail-closed，不能采用 last-value-wins。
13. 一次课程结构 PASS 只说明路径和角色闭环；没有完整证据时必须保持 Draft/未验证，`--release` 必须 BLOCK。
14. 发现冲突时，保留不同版本和日期，写入 `open-questions.md`，不能静默覆盖原文。

## 公开 raw 的额外发布闸

公开仓库中的 raw 默认不进入发布包。即使路径同时出现在 MANIFEST 和 builder allowlist 中，release validator 仍必须逐文件确认：

- `synthetic: true`；
- `source_kind` 明确包含 synthetic、virtual 或 fixture 语义；
- `visibility: public`；
- `sensitivity: public`；
- `redaction_status: safe-to-publish`；
- `consent_status` 属于受控公开许可值，例如 `original-synthetic-fixture`、`synthetic-fixture-publication-approved`、`explicit-public-consent`、`licensed-for-publication` 或 `public-domain`。

路径 allowlist、checksum 或 `synthetic: true` 单独都不能证明内容安全。任何一项缺失或使用未知值，公开 release 必须 fail-closed。真实客户、课程、账号和经营资料即使去敏也默认留在私有运行区，不能通过改 metadata 进入公开包。

## 查询策略

- 找某次原话：按 `source_id`、日期和 `conversation_type` 搜索 `raw/10_conversations/`；
- 找某类问题：按 `topics`、`keywords` 和 source registry 的 `secondary_types` 搜索；
- 找可教学内容：先查 `wiki/90_outputs/courses/index.md`，再沿 `sources` 和 `related` 回到证据；
- 找未闭环内容：查 `ingestion_status`、`verification_status`、`derived_to` 为空的记录，以及 `open-questions.md`；
- 找一次变更的过程：查 `wiki/00_meta/logs/` 的事件 ID，不把日志当作知识正文。
