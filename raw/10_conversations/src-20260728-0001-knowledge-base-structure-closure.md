---
source_id: "SRC-20260728-0001"
title: "Synthetic Conversation Fixture: Knowledge-Base Structure Closure"
description: "明确标记为 synthetic fixture 的训练对话，演示如何讨论分层 index、Raw 分类、课程提炼、验证和写回；不代表真实客户、市场或生产运行证据。"
type: "conversation-source"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
source_kind: "virtual-fixture"
synthetic: true
fixture_id: "FIX-KB-STRUCTURE-CLOSURE-0001"
fixture_provenance: "authored-for-governance-testing"
sources: ["Original synthetic training fixture authored for repository closure testing"]
related: ["../../wiki/10_sources/SRC-20260728-0001.md", "../../wiki/00_meta/raw-conversation-and-course-pipeline.md"]
raw_kind: "conversation"
conversation_type: "codex-chat"
source_date: "2026-07-28"
captured_at: "2026-07-28T00:00:00+08:00"
ingested_at: "2026-07-28T00:00:00+08:00"
channel: "internal-governance"
subject_ref: ""
client_ref: ""
participants: ["AI maintainer", "AI course designer"]
topics: ["knowledge-base-structure", "course-pipeline", "logging"]
keywords: ["index", "raw", "source registry", "course", "verification", "writeback"]
language: "zh-CN"
sensitivity: "public"
consent_status: "original-synthetic-fixture"
ingestion_status: "ingested"
derived_to: ["ID-0002", "ID-0003", "ID-0004", "VER-20260728-raw-course-closure", "WB-20260728-raw-course-closure"]
verification_status: "structure-pass"
visibility: "public"
redaction_status: "safe-to-publish"
---
# Synthetic Conversation Fixture: Knowledge-Base Structure Closure

> **Fixture notice**：以下内容是为验证知识库闭环而编写的虚拟训练样本，不是 Tony 的原始私密对话，不包含真实客户、账号、课程原文、经营数据或外部事实。

## Context

一个虚拟知识库不断增加 wiki、Raw、课程和日志文件。维护者希望人和 AI 都能从索引理解文档用途，同时又不希望把所有孙级文件全文复制到一个根 index 中。

## Exchange

### User（虚拟）

如果每个文件夹都只有一个很长的 index，文件多了以后 AI 读取成本会很高。上级目录应该只负责指向下级入口，当前目录的 index 才负责解释当前目录里的直接文件，对吗？

### Maintainer（虚拟）

对。上级 index 负责路由，当前 index 负责当前层的直接入口。每一行不能只写文件名，还要说明文档解决什么问题、什么时候读、适用边界和检索词；正文不复制到 index。

### User（虚拟）

原始对话应该放在 raw 中吗？如果以后要提炼课程，怎样避免把一次对话误当成通用结论？

### Maintainer（虚拟）

原始对话进入按来源形态分类的 raw/10_conversations，并使用 Source ID 登记。提炼时要分开事实、代表性表达、推断、冲突和待验证问题；只有经过概念或 playbook 提炼、练习和验收的内容才能进入课程模块。

### User（虚拟）

日志要不要每天追加？会不会变成另一个知识孤岛？

### Maintainer（虚拟）

默认每天一个追加日志，记录事件、证据指针、结果、风险和下一步，不复制原始对话。月末或阶段结束再提炼摘要，把稳定结论写回 wiki，把未决项写回 open questions。
