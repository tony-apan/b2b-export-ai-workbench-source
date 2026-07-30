---
title: "Adversarial Review: Discovery, Raw, Course and Logging v2"
description: "对索引可读性、文档编号、raw 对话分类、课程提炼、Skill 边界和日志规模做第二轮对抗审查，记录已修复问题、仍然存在的迁移债务和发布阻断。"
type: "evidence"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["Current repository inspection 2026-07-28", "index-and-discovery-standard.md", "raw-conversation-and-course-pipeline.md", "logging-standard.md"]
related: ["structure-adversarial-review-20260728-raw-course-log.md", "document-id-standard.md", "sub-library-contract.md", "../../scripts/validate-mother-library.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "准备继续扩目录、接入原始对话、建立课程或判断结构是否已经可以发布时。"
keywords: ["adversarial review", "对抗审查", "index", "raw", "course", "logging", "skill", "release gate"]
---
# Adversarial Review — v2

## 审查问题

本轮不问“目录看起来是否整齐”，而问：

1. 文件数量增长后，人和 AI 是否仍能定位正确内容？
2. 编号、路径和外部引用变化时，是否会静默断链？
3. 原始对话是否会被误当成事实、课程或公开资料？
4. 日志是否会变成新的知识孤岛或文件爆炸？
5. Skill 是否会偷偷成为第二真源并覆盖宿主规则？
6. 母库与子库是否仍能分别独立发布和拒绝不完整制品？

## 结果

### PASS — 已建立的结构控制

- 每级 index 只列当前直接入口和直接子目录 canonical 入口，不递归堆叠孙级内容。
- 生成表包含 ID、入口、description、type、状态/可见性、阅读时机和检索词；description 要说明对象、问题、结果和边界。
- 新 durable page 可用 `scripts/create-document.mjs` 取得当前 scope 的下一个 `ID-####`，先 dry-run 再写入；不会重命名旧文件。
- raw 按来源形态分层；主题、客户、渠道和关键词放入 front matter facets，避免同时按多个维度无限建目录。
- raw → source registry → facts/quotes/conflicts → concept/playbook → course module → exercise → verification → writeback 的闭环已经写成规则和模板。
- 日志按日追加、按月摘要，只有超过约 200 条事件或多 scope 并行才按 scope 拆分；不复制 raw 原文。
- 没有建立根级 `skills/` 第二真源；Skill 仍是子库的条件性适配器，并受 manifest 和宿主规则约束。
- 母库和 `website-content-ops` 子库分别完成结构检查、候选包构建和 checksum 制品验收。
- 对抗发现 `.gitignore` 原先只放行 `raw/index.md`，会让 raw 分类索引和对话模板在 Git 发布边界上消失；现已逐一放行安全分类入口与模板，实际 raw source 仍默认忽略。
- 对抗发现 `create-document.mjs` 原先把母库根目录作为全量取号范围，未来可能读取子库 ID；现已限制母库 durable roots、子库独立 scope，并拒绝治理/raw/日志/模板目录。
- 继续对抗发现普通 durable ID 不应覆盖 `wiki/10_sources/`：来源页已有 `SRC-YYYYMMDD-####` 体系；生成器现已拒绝该目录，避免同一来源被两套 ID 语义标记。

### 本轮继续推进的证据

- `ID-0001` 迁移样本已完成：旧路径保留 `type: redirect` 兼容页，内部引用已更新；编号报告从 42 个 legacy 降为 41 个。
- synthetic raw → source → concept → playbook → course → exercise → verification → writeback 样本已完成；`VER-` 与 `WB-` 记录不属于 durable page。raw 已恢复为只保存 fixture 对话和上下文，提炼边界移入 source note；新增 `scripts/validate-knowledge-chain.mjs` 检查必填字段、Source ID、derived_to 和 verification/writeback 指针。
- 验证器已显式豁免 `redirect`、`verification-record`、`writeback-record`，避免记录型证据污染长期文档迁移统计；后续仍需为这些豁免类型补独立完整性检查；课程第二场景仍为 assigned-not-submitted，未宣称人工评分通过。

### WARN — 仍需渐进治理

- 当前 42 个长期知识页仍是 legacy 文件名，`validate-document-ids.mjs` 报告为迁移债务；本轮不批量重命名，避免外部引用和 Git 历史大面积抖动。
- 现有老页面尚未全部填写 `when_to_read` 和 `keywords`，索引会使用 type fallback 或显示 `—`；新页面必须按模板填写，旧页面按实际修改逐步补齐。
- raw 分类入口已从 Git 忽略规则中放行，但仍需在真实提交/清洁 clone 中确认目录入口不会因空目录或未跟踪模板再次消失。
- 课程目录已有模板和入口，但还没有足够多经过练习、第二场景和人工验收的正式课程实例。
- 日志按日文件设计已通过结构审查，但真实高频运行时仍需按月观察事件数，再决定是否拆 scope。

### BLOCK — 当前不得宣称 Published

- 母库和子库 `release_status` 仍为 `BLOCK`。
- 许可证状态仍为 pending/未清除。
- 尚未在清洁目录中完成母库和子库的独立复现、安装、运行、失败恢复和人工批准证据。
- 真实客户 raw、账号数据、课程原文和经营数据仍不得放入公开母库。

## 证据命令

```bash
node scripts/sync-indexes.mjs
node scripts/validate-document-ids.mjs
node scripts/validate-indexes.mjs --check
node scripts/validate-mother-library.mjs
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
node scripts/build-mother-release.mjs
node sub-libraries/website-content-ops/scripts/build-release.mjs
node scripts/validate-artifact.mjs dist/mother/latest
node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
git diff --check
```

本轮证据结论：结构和候选制品检查通过；编号迁移、许可证、独立复现和人工发布闸仍保持原样 BLOCK/WARN，未被“脚本绿灯”掩盖。
