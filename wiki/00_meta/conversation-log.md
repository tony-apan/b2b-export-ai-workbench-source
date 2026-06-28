---
title: "Conversation Log"
description: "公开版对话记录模板，用于记录重要决策、AI 提炼动作和后续待办。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request"]
related: ["ingestion-log.md", "agent-handoff.md", "decision-log.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Conversation Log

这里记录“值得沉淀”的对话，不是逐字聊天备份。公开版只保留模板和去敏后的结构，不包含私有文件名、客户资料、课程资料或本地路径。

## When To Record

- 用户提出新的长期要求。
- 对话中形成可复用方法、SOP、模板、策略。
- 用户做了业务决策。
- 用户给了产品、渠道、市场、团队、发布风险等重要信息。
- 多 agent 对抗分析产生了结构性建议。

## Do Not Record

- 纯寒暄。
- 临时命令输出。
- 没有复用价值的中间推理。
- 涉敏原文、客户隐私、版权课程大段内容。

## Log Template

```md
## [YYYY-MM-DD] 主题

- Trigger：
- User intent：
- Key facts：
- Decisions：
- Wiki pages updated：
- Follow-up：
- Sensitivity：public/internal/private
```