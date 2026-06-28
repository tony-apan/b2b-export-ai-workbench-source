---
title: "AGENTS.md"
description: "Codex 和其他 agent 维护知识库时必须遵守的最高优先级工作协议。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: []
related: ["wiki/00_meta/ai-operating-manual.md", "wiki/00_meta/task-router.md", "wiki/00_meta/markdown-standard.md"]
---
# AGENTS.md

你是这个知识库的维护者。请把它当成一个会持续进化的业务增长 wiki，而不是一次性文档整理任务。

## 规则优先级

如果规则之间出现冲突，按以下顺序执行：

1. 用户当前明确要求。
2. 本文件 `AGENTS.md`。
3. [wiki/00_meta/ai-operating-manual.md](wiki/00_meta/ai-operating-manual.md)。
4. [wiki/00_meta/markdown-standard.md](wiki/00_meta/markdown-standard.md)、[wiki/00_meta/task-router.md](wiki/00_meta/task-router.md)、[wiki/00_meta/definition-of-done.md](wiki/00_meta/definition-of-done.md)。
5. [wiki/00_meta/publishing-and-redaction.md](wiki/00_meta/publishing-and-redaction.md)（涉及公开发布、版权、客户或账号数据时优先执行）。
6. `README.md` 和 `CLAUDE.md`。

`README.md` 和 `CLAUDE.md` 只是快速入口，不是完整 SOP。

## 核心结构

- `raw/` 是原始资料层：只读、不可变、事实来源。
- `wiki/` 是提炼知识层：你可以创建、更新、合并、链接、归档。
- `wiki/index.md` 是导航入口：每次新增重要页面或模块后必须更新。
- `wiki/00_meta/` 是工作规则、日志、开放问题、质量检查。

## 社媒账号安全红线

涉及 LinkedIn、Meta、Facebook、Instagram、TikTok、YouTube、X/Twitter 等社媒账号时，必须先读 [wiki/00_meta/social-account-safety.md](wiki/00_meta/social-account-safety.md)。

- 禁止使用 Codex 内置浏览器或脚本直接登录、发帖、评论、点赞、关注、加好友、私信或批量浏览社媒账号。
- 禁止把社媒账号自动化写进 skill、SOP 或自动化流程；这类操作有封号风险。
- 可以生成草稿、策略、检查清单和复盘；最终发布、互动、私信必须由人确认和执行。
- 用户明确要求时，可以辅助使用用户侧 Chrome 浏览器插件，但不能用 Codex 浏览器直接自动化社媒账号动作。

## 每次开始前

先读：

1. `wiki/index.md`
2. `wiki/00_meta/ai-operating-manual.md`
3. `wiki/00_meta/task-router.md`
4. 与任务相关的模块索引，例如 `wiki/30_playbooks/index.md`、`wiki/40_business/index.md`、`wiki/50_channels/.../index.md`

不要为了小任务读取全库。先用索引定位，再读相关页面和源文件。

## 资料吸收规则

当用户要求吸收新资料时：

1. 读取指定的 `raw/` 文件。
2. 判断资料类型：客户、竞品、产品、网站、LinkedIn、开发信、SEO、GEO、SEM/Ads、销售通话、市场研究。
3. 在 `wiki/10_sources/source-registry.md` 记录来源。
4. 更新或创建相关 wiki 页面。
5. 更新 `wiki/index.md` 和对应模块索引。
6. 在 `wiki/00_meta/ingestion-log.md` 追加记录。
7. 若发现矛盾、缺口或待确认事实，写入 `wiki/00_meta/open-questions.md`。
8. 按 `wiki/00_meta/definition-of-done.md` 验收。

## 写作与引用规则

- 不要编造事实。没有来源的内容必须标注为“推断”或“待验证”。
- 关键结论尽量指向来源文件路径，例如 `raw/clients/...`。
- 保留具体日期、客户名、渠道、金额、转化率等上下文。
- 页面要可被新人快速读懂：先结论，后证据，再行动建议。
- 使用普通 Markdown 链接，保持 Claude、Codex、Obsidian 都能读。
- 每个 Markdown 必须符合 `wiki/00_meta/markdown-standard.md`，包含 front matter 元描述。
- 涉及 GitHub 发布、课程资料、客户资料、账号数据时，先读 `wiki/00_meta/publishing-and-redaction.md`。

## 业务输出规则

当用户要你帮忙建站、写 LinkedIn、开发信、SEO/GEO/SEM、谈客户或分析 Ads：

1. 先读 `wiki/40_business/` 中的业务背景、ICP、offer、定位、反对意见。
2. 再读对应渠道页和 playbook。
3. 输出前明确适用对象、目标、核心信息、假设和风险。
4. 如果产出值得复用，把版本沉淀到 `wiki/90_outputs/` 或更新相关 playbook。
5. 如果业务底座缺字段，只能输出“假设版/待验证版”，不能写强结论。

## 体检与维护规则

定期检查：

- 是否有孤立页面。
- 是否有过时结论。
- 是否有多个页面讲同一件事。
- 是否有断链。
- 是否有强结论缺来源。
- 是否有已经多次出现、但还没有独立页面的重要概念。

如果合并页面，保留更好的标题和链接，并在旧页说明迁移去向。
