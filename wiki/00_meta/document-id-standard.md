---
title: "Document ID Standard"
description: "规定长期知识页、来源页、原始资料、日志和发布合同分别如何命名与编号，避免重命名造成断链，同时让人和 AI 能用稳定 ID 引用文档。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["Tony structure upgrade decision 2026-07-28"]
related: ["markdown-standard.md", "../10_sources/source-registry.md", "../_templates/index.md", "../../scripts/create-document.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Document ID Standard

## 结论

从 **2026 年 7 月 28 日** 起，新建的长期知识页默认使用：

```text
id-0001-slug.md
```

front matter 同步写：

```yaml
doc_id: "ID-0001"
```

ID 的作用是稳定引用和检索，不代表知识质量，也不代表发布日期。编号按发布 scope 独立管理：母库一套、每个可独立发布子库各一套；跨 scope 不能假设 ID 唯一。母库 durable roots 是 `wiki/20_concepts/` 至 `wiki/90_outputs/` 的知识层；子库只在自身 `MANIFEST.md` 的 `durable_roots` 内编号，固定入口、合同、adapter、模板、来源和验证/写回记录保留语义路径。

## 哪些文件要编号

| 文件类型 | 命名 | 是否使用普通文档 ID | 原因 |
|---|---|---:|---|
| 长期 Concept、Playbook、业务页、渠道页、指标页、可复用输出 | `id-####-slug.md` | 是 | 需要稳定引用、迁移和追踪生命周期 |
| 原始对话、网页快照、文档转写、导出 | `src-YYYYMMDD-####-slug.md` | 否 | Source ID 已包含日期和采集序号，避免与提炼页混淆 |
| 每日日志 | `YYYY-MM-DD.md` | 否 | 日期本身是检索主键，事件使用 `EVT-YYYYMMDD-####` |
| 月度摘要 | `YYYY-MM-summary.md` | 否 | 月份是归档主键 |
| `index.md`、`README.md`、`AGENTS.md`、`CLAUDE.md`、发布合同 | 固定文件名 | 否 | 它们是目录/协议单例，重命名会破坏工具入口；README-only 目录必须声明 `canonical_entry: "README.md"` |
| 验证记录 | `VER-YYYYMMDD-slug.md` | 否 | 记录一次有边界的验收，不是 durable knowledge page |
| 写回记录 | `WB-YYYYMMDD-slug.md` | 否 | 记录一次知识回写，不与长期页面抢 ID |
| 兼容重定向页 | 原 legacy 路径 + `type: redirect` | 否 | 保留旧链接，直到外部引用完成迁移 |
| `_templates/` 模板 | 语义文件名 | 否 | 模板是创建器，不是知识实体 |

## 迁移策略

不要一次性重命名现有 229 个 Markdown。当前已有页面保留原路径并标记为 legacy，避免大量断链、外部引用失效和 Git 历史噪声。以后修改 legacy 页面时，按以下顺序渐进迁移：

1. 先确认它不是公共入口、合同、模板、日志或 raw 文件。
2. 为页面选择下一个可用 ID，并补 `doc_id`。
3. 若确实需要改文件名，先用链接搜索更新母库、子库、README、索引和发布脚本。
4. 在旧位置保留迁移说明或兼容重定向文件，直到外部引用确认失效。
5. 运行 `node scripts/validate-document-ids.mjs`、必要时再按 scope 运行 `node scripts/validate-document-ids.mjs --scope sub-library:<id>`，然后做索引和链接校验。

验证器按 **frozen allowlist + fail-closed** 工作：`scripts/document-id-legacy-allowlist.json` 精确绑定既有 legacy 的路径和 `type`；allowlist 外新出现的未编号 durable page、路径漂移或类型漂移都阻断。`type: verification-record` 与 `type: writeback-record` 不是普通 durable page，但必须落在各自约定目录，文件名 ID 必须与 `verification_id` / `writeback_id` 一致。`type: redirect` 也必须在 frozen allowlist 中，并且只能使用同一发布 scope 内的单跳相对路径，最终目标必须是存在的、非 redirect、已编号 canonical page；绝对路径、跨 scope、self-loop、cycle、multihop 和未编号目标全部阻断。

`node scripts/create-document.mjs` 是受限生成器：它只接受 durable page 目录，并按发布 scope 取号。母库扫描 durable wiki 层但排除 `sub-libraries/`、raw、日志、模板和生成产物；子库扫描当前 `sub-libraries/<id>/` 但排除 `dist/`、运行时、凭据、日志和模板目录。生成器只接受 `template_usage: "creator-compatible"` 且声明 `template_target_kind` / `template_target_type` 的模板；durable page 还必须显式传入具体 `--when-to-read`、3–8 个 `--keywords` 和权威 `--date YYYY-MM-DD`。先用 `--dry-run` 验证，再正式写入。这样即使母库和子库都从 `ID-0001` 开始，也不会互相抢号或因为生成包污染下一次取号。

## 人和 AI 的引用规则

- 文档引用优先写相对路径，同时可写 `ID-####`。
- ID 不能替代路径：同一个 ID 可能在不同子库 scope 内重复。
- 发现标题、路径和 ID 不一致时，以当前文件 front matter、当前 scope 注册表和验证结果为准，不凭记忆修复。
- `index.md` 应显示 ID、标题、description、状态/可见性和“什么时候读”；description 不能只写文件名。
