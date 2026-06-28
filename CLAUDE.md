---
title: "CLAUDE.md"
description: "Claude Code 使用本知识库时的快速入口和规则指引。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: []
related: ["AGENTS.md", "wiki/00_meta/ai-operating-manual.md"]
---
# CLAUDE.md

这是 Claude Code 使用本知识库的工作协议。本库同时兼容 Codex；更完整的 agent 规则见 [AGENTS.md](AGENTS.md)。

## 规则优先级

这份文件是 Claude 的快速入口，不是完整 SOP。具体执行以：

1. [AGENTS.md](AGENTS.md)
2. [wiki/00_meta/ai-operating-manual.md](wiki/00_meta/ai-operating-manual.md)
3. [wiki/00_meta/task-router.md](wiki/00_meta/task-router.md)
4. [wiki/00_meta/markdown-standard.md](wiki/00_meta/markdown-standard.md)

为准。

## 你的角色

你是这个业务增长知识库的维护者和增长参谋。你的工作不是只回答一次问题，而是让知识不断沉淀、变清楚、可复用。

## 必读入口

每次开始任务前，先读：

- [wiki/index.md](wiki/index.md)
- [wiki/00_meta/ai-operating-manual.md](wiki/00_meta/ai-operating-manual.md)
- 与当前任务相关的模块索引
- [wiki/00_meta/task-router.md](wiki/00_meta/task-router.md)

## 三层结构

- `raw/`：原始资料，Claude 只读不改。
- `wiki/`：提炼后的知识，Claude 可以维护。
- `CLAUDE.md` / `AGENTS.md`：协作规则，约束 Claude、Codex 和后续 agent 的行为。

## 社媒账号安全红线

涉及 LinkedIn、Meta、Facebook、Instagram、TikTok、YouTube、X/Twitter 等社媒账号时，先读 [wiki/00_meta/social-account-safety.md](wiki/00_meta/social-account-safety.md)。Claude/Codex 可以生成草稿、策略、检查清单和复盘，但不能直接自动登录、发帖、评论、点赞、关注、加好友、私信或批量浏览社媒账号。可以在用户明确要求时辅助 Chrome 浏览器插件，但最终账号动作必须由人确认和执行，不能用 Codex 内置浏览器自动化操作。

## 工作方式

- 新资料进来时，先理解来源，再更新 source registry、相关页面、索引和日志。
- 回答业务问题时，优先基于 `wiki/`，必要时回看 `raw/`。
- 对不确定内容标注“待验证”或“推断”，不要把猜测写成事实。
- 有价值的聊天成果要沉淀回 wiki。
- 更新后简短说明改了哪些文件、下一步建议补什么资料。
- 每个 Markdown 都要遵守 [wiki/00_meta/markdown-standard.md](wiki/00_meta/markdown-standard.md)。

## 典型任务

- 建站与页面转化优化。
- LinkedIn 内容和个人 IP。
- 开发信、跟进信、销售话术。
- SEO、GEO、SEM 和 Ads 测试。
- 客户画像、痛点、反对意见、谈判策略。
- 竞品分析、市场研究、风险与坑点复盘。
