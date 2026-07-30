---
title: "Markdown Standard"
description: "定义本知识库所有 Markdown 页的元信息、页面结构、引用、状态、命名和更新 SOP。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["User request", "Subagent adversarial review"]
related: ["definition-of-done.md", "quality-checklist.md", "agent-handoff.md"]
---

# Markdown Standard

每个 Markdown 都必须有**机器可读、面向人话的元描述**。元描述用来让 Claude、Codex、新人和索引脚本在不阅读全文时判断页面负责什么、何时读取、证据边界在哪里。默认格式是页面顶部的 YAML front matter。

公开 GitHub 仓库根目录的 `README.md` 是首页展示页，不能让 YAML front matter 出现在 GitHub 正文中；因此它使用同字段的 HTML 注释元数据块。这个块仍是正式元数据，不是免检例外；校验器会把它和 YAML front matter 一样检查。其他 Markdown（包括 wiki、raw、AGENTS.md、CLAUDE.md 和子库页面）使用 YAML front matter。

## 必填 Front Matter

```yaml
---
title: "页面标题"
description: "一句话说明这个页面负责什么，什么时候应该读它。"
type: "adapter-index | adversarial-review | agent-protocol | audit | brand | business | changelog | channel | checklist | client | competitor | concept | contact | conversation-source | course-module | evidence | example-index | governance | guide | index | installation-guide | intake | legal-notice | log | log-summary | manifest | meta | metric | output | page | playbook | raw-guide | redirect | references-index | release-guide | review-record | skill | source | source-note | source-policy | sub-library | template | tooling | tooling-index | tooling-reference | verification-record | version | writeback | writeback-record"
status: "Seed | Draft | Working | Verified | Canonical | Stale | Archived"
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
when_to_read: "什么时候应该读取本页"
keywords: ["检索词 1", "检索词 2"]
tags: []
```

## 字段解释

| Field | 必填 | 说明 |
|---|---|---|
| `title` | 是 | 页面标题，和 H1 可以一致。 |
| `description` | 是 | 用人话概括页面解决的问题、适用场景和关键边界；不能只复述文件名。 |
| `type` | 是 | 页面类型，用于任务路由；新增类型必须先登记在上方枚举。`validate-indexes.mjs` 直接读取该枚举并对未知值 fail-closed。 |
| `status` | 是 | 页面成熟度。 |
| `owner` | 是 | 默认 `AI`，重要业务决策可改为 `Human`。 |
| `created` | 是 | 页面创建日期。历史页面补建时，用首次进入知识库的日期。 |
| `last_updated` | 是 | 每次实质更新必须改。 |
| `sources` | 是 | 直接来源列表。必须写成 inline、唯一、非空的带引号字符串数组；无来源写 `[]`，正文标注待验证。 |
| `related` | 是 | 相关页面路径。必须写成 inline、唯一、非空的带引号字符串数组；每个仓库内相对路径都必须可解析，不能用不存在的“未来路径”占位。 |
| `confidence` | 推荐 | 对当前内容可信度的判断。 |
| `review_after` | 推荐 | 需要复查的日期。 |
| `when_to_read` | 条件必填 | 编号 durable page、canonical 入口和模板必须写具体任务触发条件；其他页面推荐填写。 |
| `keywords` | 条件必填 | 编号 durable page、canonical 入口和模板必须有 3—8 个稳定检索词；其他页面推荐 2—8 个。不要写“关键词 1”之类占位词。 |

## 模板和原始对话附加合同

- `type: template` 必须声明 `template_usage: "creator-compatible"` 或 `"manual-copy"`。creator-compatible 模板还必须声明 `template_target_kind` 与 `template_target_type`，并提供 `DOCUMENT_TEMPLATE_START/END` payload；manual-copy 模板不得声明生成器目标字段。
- 模板的 `description`、`when_to_read` 和 3–8 个 `keywords` 必须是具体、可检索的人话；`TODO`、`待填写`、`页面说明`、`关键词 1` 等语义占位会被阻断。
- `type: conversation-source` 必须显式声明 `subject_ref` 与 `client_ref`。未知或不适用时写空字符串；需要关联时只使用去标识化的 `SUBJ-...` / `CLIENT-...` 引用，不写真实姓名、账号或客户标识。
- 新建 durable page 优先运行 `node scripts/create-document.mjs`，显式传入 `--when-to-read`、3–8 个 `--keywords` 和权威 `--date`；生成器只消费 creator-compatible 模板，先 `--dry-run`，再落盘。

## 状态升级标准

| Status | 含义 | 升级/降级条件 |
|---|---|---|
| Seed | 只有骨架或问题 | 有至少一个来源后可升 Draft |
| Draft | 有初步内容但证据不足 | 多来源一致或可执行后可升 Working |
| Working | 可用于业务输出 | 经数据/成交/多轮验证后可升 Canonical |
| Verified | 在声明的范围内完成证据验证；不等于跨环境、可发布或业务整体通过 | 证据失效或边界扩大时降为 Working/Stale |
| Canonical | 当前主要依据 | 出现反证、过时或策略变化时降为 Working/Stale |
| Stale | 可能过时 | 复查后更新、归档或恢复 |
| Archived | 历史证据或迁移后只读记录 | 保留溯源，不再承担当前规则或任务路由 |

## Description 写作规则

`description` 不是标题的同义改写，也不是“页面说明”“资料索引”这类占位词。优先用一句到两句完整的人话回答：

1. **对象**：本页处理什么主题、资产或任务；
2. **用途**：它解决什么问题，读者能用它做什么；
3. **时机**：什么时候应该打开；
4. **边界**：哪些事实、环境、权限或发布结论不在本页承诺范围内。

推荐句式：

```yaml
description: "规定如何从搜索意图、关键词证据和业务定位生成可验证的 SEO 内容，并明确来源、发布、指标和后续写回边界。"
when_to_read: "准备制定或复盘 SEO 内容任务时。"
keywords: ["SEO", "搜索意图", "内容 brief", "Search Console"]
```

避免以下写法：

- `description: "SEO 页面。"`
- `description: "文档说明。"`
- 只把文件名改成中文再重复一次；
- 把未经来源支持的结论写进元描述；
- 把版本、状态、许可证等机器状态塞进 description（这些应由 manifest、registry 或 status 字段表达）。

建议长度为 30—120 个汉字或 15—35 个英文词。短页面可以更短，但必须让陌生 AI 不打开正文也能判断“为什么读、什么时候读、不能据此做什么”。

## Index 与目录导航规则

### Canonical 入口

- 知识目录优先使用 `index.md`；可独立交付的子库、工具包和示例优先使用 `README.md`。
- 同一目录只能有一个 canonical 总入口；不要并列维护 `README.md` 和 `index.md` 两套总入口。
- `scripts/`、纯实现目录、依赖目录、缓存、构建产物和私有运行区不要求新增 index。
- 如果一个目录需要被 AI 或新人导航，却没有 `index.md` / `README.md`，先补入口，再补内容。

### 只索引当前目录

`index.md` 只列当前目录的直接 Markdown 文件和直接子目录的 canonical 入口，不递归展开孙级内容：

```text
wiki/index.md
→ wiki/50_channels/index.md

wiki/50_channels/index.md
→ wiki/50_channels/seo/index.md

wiki/50_channels/seo/index.md
→ ../../30_playbooks/id-0011-seo-content.md
→ ../../20_concepts/id-0001-search-intent.md
```

每个 index 的“当前目录直接入口”表由 `scripts/sync-indexes.mjs` 生成，表格至少包含：

- 可点击的相对路径；
- 目标页面的 `description`；
- `type`；
- 什么时候读。

不要把正文复制进 index，也不要在 index 里维护第二套版本、发布状态或 Skill 状态。机器状态以 `MANIFEST.md`、`VERSION.md`、`RUNTIME-CONTRACT.json`、`sub-libraries/registry.json` 为准。

“只索引当前目录”同时约束生成区和人工区：不能绕开自动表，在任务路线、推荐阅读或说明段落中重新列出孙级 Markdown 页面；上级只能指向下一级 canonical 入口。`sync-indexes.mjs` 会用直接入口中最大的合法 `last_updated` 确定性同步当前 index 日期；index 的 `last_updated` 不得早于它收录的最新直接入口，也不能用每次运行的系统时间制造无内容变更的噪声。

### AI 渐进读取

AI 默认按“母库入口 → 目标目录 index → 具体页面 → 页面 sources / related”渐进读取；只有任务确实需要时才继续深入。索引 description 是路由信号，不等于证据本身，关键结论仍必须回到正文和来源。

### 索引同步与验收

修改、增加、删除或重命名 Markdown 后，在当前母库根目录运行：

```bash
node scripts/sync-indexes.mjs
node scripts/validate-indexes.mjs
```

CI 使用 `validate-indexes.mjs --check` 检查工作树中是否有过期索引。手工维护生成区会在下一次同步时被覆盖；人工说明、阅读顺序和职责边界放在生成区之外。

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

## Stable IDs and filename policy

长期知识页（concept、playbook、业务页、渠道页、指标页和可复用输出）新建时默认命名为 `id-####-slug.md`，并在 front matter 写 `doc_id: "ID-####"`。完整规则见 [document-id-standard.md](document-id-standard.md)。

不强制编号的文件包括目录单例（`index.md`、`README.md`、`AGENTS.md`、`CLAUDE.md`、发布合同）、模板、日期日志和 raw source。raw source 使用 `src-YYYYMMDD-####-slug.md`，日志使用日期文件名和 `EVT-YYYYMMDD-####` 事件 ID。现有未编号页面是 legacy，不因规则升级一次性重命名。

## Index as a human-and-AI reading interface

`index.md` 不是把所有后代正文复制进来的目录。它只列当前目录直接 Markdown 文件和直接子目录 canonical 入口，但每行必须让读者知道：目标文档讲什么、当前状态/可见性、稳定 ID（若有）和什么时候应该读。详细描述放在目标页 front matter 的 `description`，不要在 index 里维护第二份容易漂移的摘要。运行 `node scripts/sync-indexes.mjs` 生成表格，人工阅读顺序和边界说明放在生成区外。

## Raw and course separation

raw 页面只能保留原文、转写、采集上下文和来源指针；AI 总结、判断、SOP、课程目标和练习不得写进 raw。原始资料先登记到 [source-registry.md](../10_sources/source-registry.md)，再提炼到 concept/playbook，最后进入 [课程模块入口](../90_outputs/courses/index.md)。

## Logs and traceability

运行日志写入 [logs/index.md](logs/index.md)。默认每天追加一份日期日志、每月生成摘要；日志事件只保存短事实卡和证据路径，不复制 raw 内容。长期稳定结论必须回写知识页，不能要求未来 AI 阅读所有日志才能知道当前规则。
