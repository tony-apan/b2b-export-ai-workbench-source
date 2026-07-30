---
title: "2026-07-28 Adversarial Review: Raw, Course, ID and Log Layers"
description: "独立攻击本轮 raw 分类、原始对话归档、课程提炼、文档 ID、索引可读性和日志分层方案，记录当前通过项、legacy 债务、公开边界和仍然阻断发布的证据。"
type: "review-record"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["../../scripts/validate-document-ids.mjs", "../../scripts/validate-indexes.mjs", "../../scripts/validate-mother-library.mjs", "../../AGENTS.md"]
related: ["document-id-standard.md", "logs/index.md", "../90_outputs/courses/index.md", "../../raw/index.md", "structure-adversarial-review-20260728-index-navigation.md"]
visibility: "public"
redaction_status: "safe-to-publish"
review_verdict: "BLOCK"
---
# 2026-07-28 Adversarial Review: Raw, Course, ID and Log Layers

## 审查范围

本轮检查的不是“目录看起来完整”，而是攻击以下失败路径：

1. 人和 AI 看到 index 仍不知道目标页何时读、解决什么问题、是否可公开。
2. 编号制度迫使仓库一次性重命名，造成断链和外部引用失效。
3. 原始对话被误当成 wiki 结论或课程事实，丢失来源、同意状态和证据边界。
4. 日志变成第二知识库：单文件无限膨胀，或一事件一文件导致检索碎片化。
5. 根级 `skills/` 与子库源码形成第二真源，发布后发生版本漂移。

## 已落地并有当前文件证据的改进

- 每个分层 index 的生成表显示 ID（若有）、入口、description、类型、状态/可见性和什么时候读；脚本只索引当前目录直接入口。
- `raw/` 已分成 inbox、conversations、web、documents、media、exports、archive，并提供 `raw/_templates/conversation-source.md`。
- 原始对话使用 `src-YYYYMMDD-####-slug.md` 预留命名；公开母库不放真实客户/账号/课程原文。
- `wiki/90_outputs/courses/` 和 `wiki/_templates/course-module.md` 固定“来源 → 概念/playbook → 练习 → 验收 → writeback”闭环。
- `wiki/00_meta/logs/` 采用每日追加、月度摘要和事件 ID；旧的三个单文件日志保留为历史兼容入口。
- 根级不新增 `skills/`；Skill 仍是子库 manifest 条件性适配器，生成包不回写成第二源码。
- `scripts/validate-document-ids.mjs` 默认只阻断重复/非法 ID，报告 primary knowledge/output layers 的 legacy，不要求危险的批量重命名。

## 当前验证证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 索引同步 | PASS | `node scripts/sync-indexes.mjs`；当前 47 个 index 入口表同步 |
| 索引和 Markdown | PASS | `node scripts/validate-indexes.mjs`；当前 markdown=249 |
| 文档 ID | PASS with legacy warning | `node scripts/validate-document-ids.mjs`；无重复/非法 ID，现有知识页仍有 legacy |
| 母库结构 | PASS with release warning | `node scripts/validate-mother-library.mjs`；静态结构通过 |
| 子库结构 | 待本轮最终重跑 | 需同时运行当前子库 validator，不能用母库结果替代 |
| 发布状态 | BLOCK | 母库/子库 release 状态、许可证和发布批准证据仍未满足 |

## 对抗结论

### PASS（本轮设计层面）

- 分层 index 的职责正确：父级指向下一级入口，不把全部孙级内容堆到主 index；description 是导航信号，正文和 source 才是证据。
- 原始对话放在 raw 是正确的，但必须按来源形态、敏感级别和 ingestion 状态分类；课程只能消费经过登记和提炼的内容。
- 日志按日追加、按月压缩是比单文件或一事件一文件更稳的折中；超过阈值再按 scope 拆分。

### WARN（可继续推进但要有 owner）

- 现有 durable pages 尚未批量编号。owner：母库维护者；触发器：下一次稳定引用/大规模迁移前；动作：按 scope 建 ID registry，先迁移 1 个 concept 和 1 个 playbook 做样本。
- 课程模块目前只有模板和入口，没有已验证课程实例。owner：课程维护者；触发器：第一批真实/虚拟练习完成后；动作：创建 `id-####-course-module-...`，附 verification 和 writeback。
- 每月摘要需要在月末人工提炼，不能假设脚本能判断“什么是稳定结论”。

### BLOCK（不能宣称外部发布）

- 当前结构 PASS 不等于母库或子库 Published；公开远程仍要求真实 raw、客户数据、凭据、课程原文留在私有运行区。
- 许可证、清洁目录复现、真实安装/运行、人工批准和发布包证据仍需分别满足母库和每个子库的 release gate。

## 下一次闭环验收

1. 添加第一批真正需要稳定引用的 `id-####-slug.md`，验证链接、index、scope 唯一性和发布包复制。
2. 用一个去敏对话做完整演练：raw → source registry → concept/playbook → course module → exercise → verification → writeback。
3. 月末检查日志是否超过拆分阈值；若没有，保持每日文件，不额外拆分。
4. 分别重跑母库和每个子库 validator/build/artifact 检查，任何一个 scope 仍 BLOCK 就保持 BLOCK。

## Recheck addendum — 2026-07-28

- 修复了母库候选包对 raw 分类入口的发布边界：公开包现在包含 `raw/` 的分类 index/模板；真实、私有和未授权 raw source 仍排除，仅显式 allowlist 的安全 synthetic fixture 可例外。
- `node scripts/build-mother-release.mjs`：通过，生成 279 个文件、278 条 checksum；候选包自校验和 artifact 校验通过。
- `node sub-libraries/website-content-ops/scripts/build-release.mjs`：通过，生成 100 个文件、99 条 checksum；子库候选包自校验和 artifact 校验通过。
- `node scripts/validate-mother-library.mjs` 与子库 validator：均 `STRUCTURE_PASS`，但母库和子库 release 状态仍为 `BLOCK`。

这次失败不是被隐藏，而是由候选包复制验证暴露并修复：若 raw 新增分类入口，发布 manifest 和候选包复制逻辑必须同时更新；只改源码目录会造成发布包中的 index 断链。


## Recheck addendum — 2026-07-28 synthetic fixture allowlist

- 为使本轮 raw → course 闭环可以在候选包中复现，新增一个 `synthetic: true` 且 `safe-to-publish` 的虚拟 fixture。
- `MANIFEST.md`、`scripts/build-mother-release.mjs` 和 `.gitignore` 三处同时显式放行同一个文件；其他 raw source 仍由 `raw/**` 默认排除。
- 母库候选包现已重新构建并通过自校验，包含 294 个文件、293 条 checksum；状态仍为 `BLOCK`，不代表许可证或人工发布批准。
