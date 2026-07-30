---
title: "2026-07-28 结构对抗审查：元描述、分层索引与独立工作区"
description: "记录本轮对 Markdown 人话描述、当前目录索引、模板选择和子库独立工作区边界的对抗审查、修复证据、残余风险与发布阻断。"
type: "review-record"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["../../scripts/sync-indexes.mjs", "../../scripts/validate-indexes.mjs", "../../sub-libraries/website-content-ops/scripts/sync-workspace-template.mjs", "../../sub-libraries/website-content-ops/scripts/validate-sub-library.mjs"]
related: ["markdown-standard.md", "sub-library-contract.md", "publishing-and-redaction.md", "structure-adversarial-review-20260728-final.md"]
visibility: "public"
redaction_status: "safe-to-publish"
review_verdict: "BLOCK"
---
# 结构对抗审查记录

## 审查目标

本轮不是把结构检查通过包装成发布通过，而是攻击以下假设：

1. 每个 Markdown 的 `description` 是否真的能帮助人和 AI 判断“这页解决什么问题、什么时候读、边界是什么”；
2. 每个 `index.md` 是否只索引当前目录，并且把目标文件的 `description` 带出来，而不是把全库递归展开成高消耗目录；
3. 新建页面是否有最窄可复用模板，避免 AI 随意创造字段和元数据；
4. 子库中的 `WORKSPACE-TEMPLATE/` 被单独复制后，是否仍依赖子库上层的 `TEMPLATES/`、`ADAPTERS/` 或母库路径；
5. 母库和子库的结构 PASS 是否被误读为外部发布批准。

## 已完成修复

- 母库 `scripts/sync-indexes.mjs` 统一生成分层索引：只列当前目录的直接 Markdown 文件和直接子目录 canonical 入口，并展示 `title`、`description`、`type` 和读取时机。
- 母库 `scripts/validate-indexes.mjs` 检查 front matter、description、断链、本机绝对路径、canonical 入口和索引是否过期。
- `wiki/00_meta/markdown-standard.md` 已明确人话 description、推荐字段、当前目录索引、渐进读取和模板选择规则。
- `wiki/_templates/` 已提供普通知识页、验证记录、写回记录等最窄模板；根目录治理文件不作为普通模板复制。
- `website-content-ops/WORKSPACE-TEMPLATE/` 已增加运行区内的 `TEMPLATES/`，其中模板由子库根目录 `TEMPLATES/` 生成，避免独立复制后链接越界。
- 新增 `sub-libraries/website-content-ops/scripts/sync-workspace-template.mjs`；子库校验自动以 `--check` 验证运行时副本未过期。
- `WORKSPACE-TEMPLATE` 的跨层链接已改为工作区内闭环路径；运行时模板不再引用母库、子库上层 `ADAPTERS/` 或不存在的课程文件。
- 母库和子库路由继续保持分层：母库只引导到子库 canonical 入口，子库内部再读取自己的协议、合同、模板和 adapter。

## 当前验证证据

已运行并通过结构检查：

```text
node sub-libraries/website-content-ops/scripts/sync-workspace-template.mjs --check
WORKSPACE_TEMPLATE_SYNC_PASS: 10 generated files are current

node scripts/sync-indexes.mjs
INDEXES_SYNCED: 34

node scripts/validate-indexes.mjs --check
INDEX_VALIDATION_PASS: markdown=228

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
STRUCTURE_PASS: static sub-library checks passed; this is not release approval.

node scripts/validate-mother-library.mjs
STRUCTURE_PASS: static mother-library checks passed; this is not release approval.

git diff --check
# no output
```

## 独立复制验证

从 `dist/latest/` 复制到临时目录后，未带入母库 `wiki/`、`raw/` 或母库 registry，运行：

```text
node <copy>/scripts/validate-sub-library.mjs
STRUCTURE_PASS: static sub-library checks passed; this is not release approval.

node <copy>/scripts/validate-artifact.mjs <copy>
ARTIFACT_PASS

WORKSPACE_COPY_LINK_CHECK_PASS
```

运行区内部模板和索引均能在 `WORKSPACE-TEMPLATE/` 内闭环；子库上层 `ADAPTERS/` 和母库路径不再是工作区运行依赖。该证据证明的是“当前候选源码包的静态独立性”，不是客户真实运行、许可证批准或稳定发布。

## 仍然 BLOCK 的原因

- 母库 `MANIFEST.md` 仍为 `release_status: BLOCK`，且 `license_status` 尚未 cleared；母库不能对外宣称已发布。
- `website-content-ops/MANIFEST.md` 仍为 `release_status: BLOCK`、draft / evidence-partial，且许可证未清；子库不能对外宣称是稳定 Skill 或稳定产品。
- 本记录中的静态检查不等于真实独立安装、客户运行区运行、跨部署执行、CMS 长跑、失败恢复或授权验收。
- 独立候选包复制验证需要在 latest-only 构建后再次确认，不能只凭源码目录校验。

## 后续闭环

1. 修改子库根目录 `TEMPLATES/` 后，先运行 `node scripts/sync-workspace-template.mjs`，再运行 `--check`。
2. 运行母库和目标子库各自的校验；任何一个 scope 未有证据，不能替代另一个 scope 的 Ready。
3. 构建 `dist/latest/` 后，从复制目录运行子库内置 validator 和 artifact validator，确认包不依赖母库路径。
4. 新建客户运行区时只复制 `WORKSPACE-TEMPLATE/`，先读其 `README.md`、各层 canonical 入口和 `TEMPLATES/README.md`，不要把模板当成完成证据。
5. 客户事实、账号、凭据、聊天、指标和发布结果只写入客户私有运行区；通用方法改进必须脱敏并人工批准后才可回母库。
