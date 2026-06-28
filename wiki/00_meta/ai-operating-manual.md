---
title: "AI Operating Manual"
description: "AI 维护知识库的主操作手册，定义资料吸收、查询输出、冲突处理和归档流程。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: []
related: []
---
# AI Operating Manual

这个知识库采用 Karpathy LLM Wiki 的三层模式：原始资料、提炼 wiki、agent 协议。核心思想是：不要每次问问题都从原始资料重新推理，而是让 AI 把资料逐步编译成可链接、可维护、可复用的 Markdown wiki。

## 公开版边界

本仓库是公开去敏版，不是完整私有知识库。这里的 `raw/` 只保留占位说明和公开索引，不包含真实原始资料、客户档案、课程提炼、账号导出、广告截图或未发布草稿。

当任务需要真实来源时：

1. 在本公开仓库中先读 `raw/README.md`、`raw/index.md` 和 `wiki/10_sources/source-registry.md`，确认公开来源边界。
2. 如果问题依赖私有 raw、客户细节、课程资料或账号数据，标注“需要私有完整库验证”，不要在公开版补造事实。
3. 不要把私有 raw 上传到本仓库；公开版只能沉淀去敏后的 SOP、模板、方法论和公开来源摘要。

参考来源：

- Andrej Karpathy, LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## 角色分工

- 人负责：收集资料、提出问题、判断方向、确认重要决策。
- AI 负责：摘要、归档、链接、改写、发现矛盾、维护索引、沉淀输出。
- `raw/` 负责：在私有完整库中保存不可变事实；在本公开版中仅保留占位说明。
- `wiki/` 负责：保存当前最好理解。

## Raw Markdown 与 Wiki Markdown

- Raw Markdown：在私有完整库中放在 `raw/`，是原始资料的转写、OCR、网页提取、字幕或会议转写。它必须有来源，但不做总结和判断。公开版 `raw/` 不存真实 raw，只保留占位和公开来源说明。
- Wiki Markdown：放在 `wiki/`，是提炼后的知识、SOP、索引、方法论、输出草稿。它必须引用 raw 或 source registry。
- 两者都要能追溯到 [../10_sources/source-registry.md](../10_sources/source-registry.md)。

## 必读 SOP

- 术语统一：[glossary.md](glossary.md)
- 方法论总纲：[methodology.md](methodology.md)
- Markdown 元描述规范：[markdown-standard.md](markdown-standard.md)
- 任务路由：[task-router.md](task-router.md)
- 社媒账号安全红线：[social-account-safety.md](social-account-safety.md)
- 资料类型判定：[source-taxonomy.md](source-taxonomy.md)
- 完成定义：[definition-of-done.md](definition-of-done.md)
- 多 agent 交接：[agent-handoff.md](agent-handoff.md)
- 对话记录：[conversation-log.md](conversation-log.md)
- 模块登记：[module-registry.md](module-registry.md)
- 模块扩展：[module-expansion-sop.md](module-expansion-sop.md)
- 多人维护：[collaboration-model.md](collaboration-model.md)
- 发布去敏：[publishing-and-redaction.md](publishing-and-redaction.md)

## 页面生命周期

1. Seed：骨架页，等待资料。
2. Draft：已有初步内容，但来源不足。
3. Working：可用于业务输出，但仍需继续更新。
4. Canonical：已被多次验证，可作为主要依据。
5. Stale：可能过时，需要复查。

所有 Markdown 必须在页面顶部使用 front matter，详见 [markdown-standard.md](markdown-standard.md)。基础格式：

```yaml
status: Seed
last_updated: 2026-06-28
owner: AI
created: "2026-06-28"
sources: []
```

升级/降级条件以 [markdown-standard.md](markdown-standard.md) 为准。

## Source ID 规则

每个被吸收的来源必须有稳定 Source ID，格式：

`SRC-YYYYMMDD-短主题`

例子：

- `SRC-20260628-ACME-CALL`
- `SRC-20260628-GOOGLE-ADS-Q2`
- `SRC-20260628-COMPETITOR-HOMEPAGE`

吸收前先查 [../10_sources/source-registry.md](../10_sources/source-registry.md)，避免重复登记。

## 资料吸收流程

适用于用户说“吸收资料”“更新知识库”“把这个放进 wiki”。

1. 私有完整库：读取指定 `raw/` 文件。公开版：只读取公开占位索引和 source registry；如果需要真实 raw，停止并标注“需要私有完整库验证”。
2. 提取：事实、结论、客户原话、数字、对象、场景、风险、可行动建议。
3. 写入或更新：
   - `wiki/10_sources/source-registry.md`
   - 相关业务页
   - 相关渠道页
   - 相关 playbook
   - `wiki/index.md`
   - `wiki/00_meta/ingestion-log.md`
4. 如果新资料挑战旧结论，在相关页面新增“冲突/变化”段落。
5. 如果资料不足，在 `wiki/00_meta/open-questions.md` 追加问题。
6. 按 [definition-of-done.md](definition-of-done.md) 验收。

## 冲突处理流程

当新资料和旧结论冲突时：

1. 保留旧结论，不直接删除。
2. 新增“Conflict / Change”段落，说明冲突内容、来源、日期。
3. 标注当前采用哪一版，以及为什么。
4. 把待确认问题写入 [open-questions.md](open-questions.md)。
5. 如果影响策略，写入 [decision-log.md](decision-log.md)。

## 归档与迁移流程

- 过时但仍有历史价值的页面移动到 `wiki/99_archive/`。
- 原页面位置保留短说明时，必须写清迁移去向。
- 更新所有 index 和入链。
- 不删除有来源的历史结论，除非用户明确要求。

## 查询与输出流程

适用于用户要建站、写开发信、写 LinkedIn、做 SEO/GEO/SEM、谈客户、分析 Ads。

1. 先读 `wiki/index.md`。
2. 读业务底座：ICP、offer、messaging、pain map、objections。
3. 读对应渠道或 playbook。
4. 必要时回看来源文件。
5. 输出时注明：
   - 目标对象
   - 使用场景
   - 依据
   - 假设
   - 下一步需要验证什么
6. 若输出值得复用，沉淀到 `wiki/90_outputs/` 或更新 playbook。

涉及 LinkedIn、Meta、TikTok、YouTube 等社媒账号动作时，必须先读 [social-account-safety.md](social-account-safety.md)。AI 只能准备草稿、策略、检查清单和复盘；不得用 Codex 浏览器或脚本直接登录、发布、互动、私信或批量浏览账号。

## 质量标准

好的 wiki 页面应该：

- 标题清楚。
- 第一段直接讲结论。
- 有来源路径或明确的“待验证”标记。
- 链到相关页面。
- 能指导下一步行动。
- 不把聊天里的临时想法伪装成事实。

输出前还要检查 [quality-checklist.md](quality-checklist.md)。

## 链接规则

- 使用相对 Markdown 链接，例如 `[ICP](../40_business/icp.md)`。
- 新建页面后更新对应 index。
- 页面末尾可以加“Related”段落列出相关页面。

## 命名规则

- 文件夹和文件名用英文小写、短横线。
- 页面标题可以用中文。
- 客户、竞品、活动名称尽量保持一致。
- 日期统一用 `YYYY-MM-DD`。

## 维护节奏

- 每次吸收资料：更新 source registry、相关页、索引和日志。
- 每周或资料明显增多后：做一次 wiki health check。
- 每次形成可复用输出：归档到 `90_outputs/`。
- 每次发现策略变化：记录到 `00_meta/decision-log.md`。
- 每次形成长期需求或关键对话：记录到 `00_meta/conversation-log.md`。
- 每次新增模块：按 `00_meta/module-expansion-sop.md` 更新 raw、wiki、playbook、模板和索引。
