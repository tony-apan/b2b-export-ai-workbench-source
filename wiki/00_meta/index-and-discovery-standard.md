---
title: "Index and Discovery Standard"
description: "规定每级 index.md 如何同时服务人和 AI：只索引当前层、用人话描述文档、提供读取时机和检索词，并通过分层入口避免把全文递归堆进上级目录。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["Tony structure upgrade decision 2026-07-28"]
related: ["markdown-standard.md", "document-id-standard.md", "../_templates/page.md", "../../scripts/sync-indexes.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "新增、重命名、拆分目录或发现 AI 找不到文档时，先确认索引粒度和描述规则。"
keywords: ["index", "索引", "目录", "检索", "description", "导航", "AI retrieval"]
---
# Index and Discovery Standard

## 核心结论

`index.md` 不是文件清单，而是当前目录的**导航和检索决策页**。它要让新人、Claude、Codex 在不打开全部正文的情况下知道：

- 这个目录负责什么；
- 当前条目解决什么问题；
- 什么时候应该读它；
- 它处于什么状态、能否公开使用；
- 下一步应进入哪一个子目录或文档。

## 分层规则

1. `wiki/` 知识目录必须使用一个 `index.md` 作为 canonical 入口；子库、脚本、adapter、模板、运行区和发布目录可以使用 `README.md`，但不能同时保留两个 canonical 入口。
2. README-only 目录的 `README.md` 必须在元数据中声明 `canonical_entry: "README.md"`；该根下每个可导航子目录也必须恰有一个 `README.md` 或 `index.md` canonical 入口，新增无入口子目录或同目录双入口都 fail-closed。
3. `scripts/sync-indexes.mjs` 会把当前目录的直接 Markdown 和直接子目录 canonical 入口都纳入上级 `index.md`；README-only 目录不需要被强行改成 `index.md`。
4. 当前目录的 index 只列：
   - 当前目录的直接 Markdown 文件；
   - 直接子目录的 canonical `index.md` 或 `README.md`。
5. 上级 index 不复制孙级文件，不把整个 wiki 展平成一张巨表。需要深入时，沿着下一级入口继续读。
6. `scripts/sync-indexes.mjs` 生成“当前目录直接入口”表；生成区不能手工修改。
7. 反递归规则覆盖整个 index，而不只是生成区：任务路线、推荐阅读、附录或人工说明不能重新手列孙级 Markdown；上级只能链接下一级 canonical 入口。
8. index 的 `last_updated` 必须不早于当前直接入口中最新的合法 `last_updated`；同步脚本按入口日期确定性更新，不使用当前系统时间制造无关 diff。
9. 目录有子目录但缺 canonical 入口时，必须补入口或明确把它标记为实现/运行目录，不能让 AI 猜路径。
10. `type: redirect` 只用于旧 URL 兼容，不进入“当前目录直接入口”主生成表；如确需展示兼容关系，只能放入降级的独立兼容区，不能与 ID canonical 同权排列。
11. 活动文档、模板、`sources` / `related` 和 source registry 的页面路径必须直接指向 ID canonical；除 redirect 本身、已归档历史页和日志外，不得把 redirect 当作内部导航入口。
12. 模板必须声明 `template_usage: "creator-compatible"` 或 `"manual-copy"`：前者供受控生成器使用并声明目标 kind/type，后者只供人工复制且不得冒充生成器模板。模板的 description、when_to_read 和 3–8 个 keywords 必须是可检索的具体语义，通用占位词在严格模式下阻断。

## 每个条目的最小信息

生成索引至少展示：

| 字段 | 写法 | 目的 |
|---|---|---|
| ID | `ID-0001` 或 `—` | 稳定引用；不把 ID 当作跨 scope 全局唯一键 |
| 入口 | 标题 + 相对链接 | 人可以点击，AI 可以继续路由 |
| description | 一句话说明对象、问题、产出和边界 | 防止只看文件名仍不知道内容 |
| type | `concept`、`playbook`、`source`、`template` 等 | 让 AI 先判断页面角色 |
| state | `status / visibility` | 避免把 Seed、Draft、BLOCK 当成稳定结论 |
| 什么时候读 | 明确任务触发条件 | 减少无目的全文读取 |
| 检索词 | 3-8 个自然关键词 | 支持人类扫描和关键词检索 |

新建或已编号的 durable page 必须提供 3-8 个检索词；旧 legacy 页面先报告缺口，不因为历史债务一次性阻断全库。

## 索引质量分层与闸门

索引入口按责任分层，不把固定入口、长期知识页和一次性记录混用：

| 层级 | 适用对象 | 关键词规则 | 普通模式 | `--strict` / `--release` |
|---|---|---|---|---|
| Durable page | `id-####-slug.md`，以及文档 ID 规则定义的长期知识页 | 必须有 `doc_id`、`description`、`when_to_read`，并有 3-8 个关键词 | BLOCK | BLOCK |
| Canonical / registry entry | 校验器动态发现的所有 wiki 目录 canonical 入口（通常为 `index.md`，显式 README-only 时为 `README.md`）、`sub-libraries/README.md`，以及 `sub-libraries/registry.json` 用 `path` + `canonical_entry` 声明的入口 | 所有入口提供 3-8 个检索词；wiki canonical 还必须提供具体 `when_to_read`，子库入口的读取时机由各子库合同继续约束；缺失字段或 `—` 都按 0 个计 | WARN | BLOCK |
| Fixed or record entry | `raw/**`、`wiki/00_meta/logs/**`、子库 `TEMPLATES/`，以及 `type: template`、`type: verification-record` 或 `type: writeback-record` 的记录 | 豁免 canonical 关键词闸；按各自 raw、模板、日志或记录规则处理；`wiki/_templates/index.md` 作为模板目录导航入口不豁免 | 不因关键词 `—` 阻断 | 不因关键词 `—` 阻断 |

`description` 缺失仍按 Markdown 元数据规则 BLOCK；上述豁免只针对 canonical 入口的关键词数量，不豁免链接、路径、front matter 或其他适用校验。`--check` 继续只检查生成索引是否过期并保留普通模式行为；`--strict` 是索引质量闸的严格模式，`--release` 与其等价。

## description 写作公式

推荐格式：

> 面向【对象/任务】，解释或提供【核心内容】，帮助完成【结果】，不覆盖【边界/未验证事项】。

反例：

- `页面说明`
- `资料索引`
- `关于 SEO 的文档`

合格示例：

> 面向需要设计 B2B SEO 内容的 AI 和新人，说明搜索意图、页面 brief、证据核对和发布前检查，帮助产出可验收的内容任务；不替代真实 Search Console 数据。

## 控制索引规模

索引不会因为文件数量增加而无限复制正文：

- 目录级 index 只保留直接入口；
- 描述控制在一到两句，正文放在目标页；
- 一个目录直接条目超过约 80 个时，按稳定主题拆子目录；
- 一个 index 超过约 120 行时，优先拆分目录或增加中间导航页，不靠压缩字体或删除 description；
- 只有真正需要独立发布、独立权限或独立生命周期的内容才升为子库；
- 人工区也不得复制孙级清单；需要跨层任务路线时，只指向下一层 canonical 入口，并让下一级 index 继续展开。

## 验收

每次结构变化后运行：

```bash
node scripts/sync-indexes.mjs
node scripts/validate-indexes.mjs --check
node scripts/validate-indexes.mjs --strict
node scripts/validate-document-ids.mjs
node scripts/validate-document-ids.mjs --scope sub-library:website-content-ops
```

人工抽查至少一个上级 index、一个下级 index 和一个具体文档：能否从上级入口一路判断“这是什么、何时读、读完做什么”。
