---
title: "Markdown Standard"
description: "定义本知识库所有 Markdown 页的元信息、页面结构、引用、状态、命名和更新 SOP。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request", "Subagent adversarial review"]
related: ["definition-of-done.md", "quality-checklist.md", "agent-handoff.md"]
---

# Markdown Standard

每个 Markdown 都必须有元描述。这里的元描述默认指页面顶部的 YAML front matter，用来让 Claude、Codex、新人快速判断页面职责、可信度和维护方式。

例外：公开 GitHub 仓库根目录的 `README.md` 是首页展示页。GitHub 会把 YAML front matter 直接渲染成正文，因此根 `README.md` 不使用可见 YAML front matter；如需保留元信息，写在 HTML 注释里。其他 wiki 页面、raw Markdown、AGENTS.md、CLAUDE.md 仍然使用 YAML front matter。

## 必填 Front Matter

```yaml
---
title: "页面标题"
description: "一句话说明这个页面负责什么，什么时候应该读它。"
type: "meta | index | concept | playbook | business | channel | source | client | competitor | metric | output | template | raw-guide"
status: "Seed | Draft | Working | Canonical | Stale"
owner: "AI | Human | Team"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
sources: []
related: []
---
```

## 推荐 Front Matter

```yaml
confidence: "low | medium | high"
audience: ["Claude", "Codex", "新人"]
review_after: "YYYY-MM-DD"
tags: []
```

## 字段解释

| Field | 必填 | 说明 |
|---|---|---|
| `title` | 是 | 页面标题，和 H1 可以一致。 |
| `description` | 是 | 元描述。说明页面用途，不写营销口号。 |
| `type` | 是 | 页面类型，用于任务路由。 |
| `status` | 是 | 页面成熟度。 |
| `owner` | 是 | 默认 `AI`，重要业务决策可改为 `Human`。 |
| `created` | 是 | 页面创建日期。历史页面补建时，用首次进入知识库的日期。 |
| `last_updated` | 是 | 每次实质更新必须改。 |
| `sources` | 是 | 直接来源列表。无来源写 `[]`，正文标注待验证。 |
| `related` | 是 | 相关页面路径。 |
| `confidence` | 推荐 | 对当前内容可信度的判断。 |
| `review_after` | 推荐 | 需要复查的日期。 |

## 状态升级标准

| Status | 含义 | 升级/降级条件 |
|---|---|---|
| Seed | 只有骨架或问题 | 有至少一个来源后可升 Draft |
| Draft | 有初步内容但证据不足 | 多来源一致或可执行后可升 Working |
| Working | 可用于业务输出 | 经数据/成交/多轮验证后可升 Canonical |
| Canonical | 当前主要依据 | 出现反证、过时或策略变化时降为 Working/Stale |
| Stale | 可能过时 | 复查后更新、归档或恢复 |

## 页面正文 SOP

标准页面建议结构：

1. H1：页面标题。
2. TL;DR：当前结论或页面作用。
3. Current Understanding：当前理解。
4. Evidence / Sources：证据和来源路径。
5. How To Use：如何用于业务输出。
6. Open Questions：待验证问题。
7. Related：相关页面。

模板页可以不完全遵守正文结构，但必须有 front matter。

## 引用规范

- 来源路径写相对路径，例如 `../../raw/clients/example.md`。
- 客户原话用引号，并保留来源。
- 推断必须写成 `推断：...`。
- 无来源强结论必须降级为 `待验证：...`。
- 数字、价格、转化率、结果必须有来源或标注待验证。

## Raw Markdown Source Rules

`raw/` 里的 Markdown 也必须有来源，但它的来源指“原始文件、采集渠道或转写来源”，不是 wiki 里的二次引用。

Raw Markdown 推荐字段：

```yaml
source_id: "SRC-YYYYMMDD-topic"
raw_kind: "original | extracted | transcript | export | screenshot-note"
original_path: ""
extraction_method: ""
source_date: "YYYY-MM-DD"
ingested_at: "YYYY-MM-DD"
```

- `raw` Markdown 只能做转写、清洁排版、页码标记和必要的去乱码。
- 不在 `raw` Markdown 里写 AI 总结、建议、分类或 SOP。
- 提炼、归类、判断、方法论必须写入 `wiki/`。
- `raw` Markdown 和 `wiki` Markdown 都必须能追溯到 source registry。

## 更新 SOP

1. 判断任务类型，查看 [task-router.md](task-router.md)。
2. 读取相关页面和来源。
3. 更新正文。
4. 更新 front matter 的 `last_updated`、`sources`、`related`；新页面必须写 `created`。
5. 更新相关 index。
6. 更新日志或交接记录。
7. 按 [quality-checklist.md](quality-checklist.md) 验收。

## Visibility And Publishing Fields

涉及客户、课程、账号、报价、商业策略、内部数据的页面，建议加：

```yaml
visibility: "public | internal | private"
redaction_status: "not-reviewed | redacted | safe-to-publish"
maintainers: []
reviewers: []
```

发布到 GitHub 前必须检查 [publishing-and-redaction.md](publishing-and-redaction.md)。
