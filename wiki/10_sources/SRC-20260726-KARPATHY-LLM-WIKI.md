---
title: "Source Note: Andrej Karpathy LLM Wiki"
description: "提炼 Karpathy 2026 年 LLM Wiki 原始方法，作为本库 raw、wiki、agent 协议和持续积累机制的官方来源。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"]
related: ["../00_meta/knowledge-compounding-system.md", "../00_meta/ai-operating-manual.md"]
confidence: "high"
review_after: "2026-10-26"
when_to_read: "核对本库 raw/wiki/agent 分层和持续积累方法的来源时读本页；只提炼公开 Gist，不代表其作者认可本仓库实现。"
keywords: ["Karpathy", "LLM Wiki", "raw", "wiki", "agent instructions", "知识积累"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Source Note: Andrej Karpathy LLM Wiki

## Summary

Karpathy 在 2026-04-04 发布的 LLM Wiki 原始说明，核心不是“把很多文件丢进 RAG”，而是让 LLM 持续维护一套位于原始资料与用户之间的 Markdown wiki。新来源和新问题都应更新已有页面、交叉链接、矛盾和综合判断，使知识只编译一次、持续变好，而不是每次提问重新拼接。

截至 2026-07-26，该原始 gist 仍只有一个 revision。本页只记录 Karpathy 原文能够直接支持的原则；本仓库新增的来源登记、去敏、状态、指标和回写规则属于针对外贸业务场景的本地增强。

## Original Pattern

- `raw/`：保存原始资料，不把它直接当成当前结论。
- `wiki/`：保存经过提炼、互相链接、持续修订的当前知识。
- schema / agent instructions：规定页面格式、来源、链接、更新、矛盾处理和 lint 规则；本仓库由 `AGENTS.md` 与 `wiki/00_meta/` 承担。
- ingest：加入新来源时，不只是索引，而是读取、提炼并整合到已有 wiki。
- query：回答问题时，优先复用 wiki；问题本身带来的新理解也应回写。
- lint：定期检查孤立页面、断链、重复内容、陈旧页面和结构漂移。

## What It Does Not Require

- 不要求一开始就安装向量数据库或复杂 RAG；小型知识库可以先靠索引、文件名、front matter 和链接定位。
- 不规定唯一目录结构；具体 schema、工具和输出格式应按领域共同设计。
- 不等于自动把所有 AI 输出当成事实；来源、矛盾和人的判断仍然需要保留。

## Local Adaptation

本仓库在原始三层结构上增加：

1. `wiki/10_sources/`：公开来源登记与来源摘要，保证可追溯。
2. `wiki/80_metrics/`：业务数据和实验反馈，负责验证知识是否有效。
3. `wiki/90_outputs/`：页面、内容、话术等产出，不把一次性产出直接冒充长期知识。
4. `wiki/00_meta/ingestion-log.md`：记录公开可见的吸收与结构变化。
5. 公开/私有边界：真实客户、课程、账号和经营数据留在私有 raw；公开仓库只保留去敏后的知识。

## Implication For This Repository

每个 Module 都必须服从同一个循环：

`问题 -> 原始来源 -> 来源登记 -> wiki 提炼 -> playbook/输出 -> 数据与反馈 -> 回写 wiki`

Module 是知识的应用场景，不应再建立互不相通的资料孤岛。
