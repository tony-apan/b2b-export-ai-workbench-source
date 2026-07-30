---
title: "Wiki Map"
description: "知识库目录地图，说明每个顶层目录和模块的职责。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-27"
sources: []
related: []
---
# Wiki Map

## Root / 母库

当前根目录是逻辑母库；GitHub 远程为公开时只保存公开安全知识和虚拟演示。

- `README.md`：给人看的总说明。
- `AGENTS.md`：Codex 等 agent 的工作协议。
- `CLAUDE.md`：Claude Code 的工作协议。

## sub-libraries

可独立交付、品牌化和发布的任务型子库源码。可以包含空的客户运行区模板，但不包含填入真实数据的客户运行时资料。

- `sub-libraries/README.md`：子库入口与发布规则。
- `sub-libraries/website-content-ops/`：首个建站内容运营子库；包含课程地图、客户运行区空模板、执行模板和 adapter 合同，当前 release 为 BLOCK。

## raw

当前公开远程条件下，母库的 `raw/` 只保留占位说明：

- `raw/index.md`：公开版 raw 边界和索引占位说明。

客户或项目私有运行区才可以包含真实 `raw/00_inbox/`、`raw/clients/`、`raw/competitors/`、`raw/market-research/`、`raw/products-offers/`、`raw/website/`、`raw/linkedin/`、`raw/email-outreach/`、`raw/seo/`、`raw/geo-ai-search/`、`raw/sem-ads/`、`raw/sales-calls/`、`raw/screenshots/` 和 `raw/archive/`。

## wiki

- `wiki/00_meta/`：规则、日志、开放问题、质量检查。
- `wiki/00_meta/glossary.md`：统一术语。
- `wiki/00_meta/methodology.md`：增长方法论总纲。
- `wiki/00_meta/knowledge-compounding-system.md`：所有 Module 共用的知识积累、执行、验证和回写闭环。
- `wiki/00_meta/private-master-and-sub-library-model.md`：根目录母库、可发布子库和客户运行区边界。
- `wiki/00_meta/sub-library-contract.md`：每个可独立交付子库必须实现的统一接口。
- `wiki/00_meta/markdown-standard.md`：Markdown 元描述和页面 SOP。
- `wiki/00_meta/task-router.md`：任务路由。
- `wiki/00_meta/source-taxonomy.md`：资料类型判定。
- `wiki/00_meta/definition-of-done.md`：完成定义。
- `wiki/00_meta/agent-handoff.md`：多 agent 交接格式。
- `wiki/00_meta/conversation-log.md`：重要对话和提炼记录。
- `wiki/00_meta/current-focus.md`：当前唯一 Active 模块、阻断和验收闸。
- `wiki/00_meta/structure-adversarial-review-20260726.md`：本轮结构审查、已修复项和残余 BLOCK。
- `wiki/00_meta/module-registry.md`：模块内容成熟度与执行状态登记。
- `wiki/00_meta/module-expansion-sop.md`：新增模块流程。
- `wiki/00_meta/collaboration-model.md`：多人维护规则。
- `wiki/00_meta/publishing-and-redaction.md`：GitHub 发布和去敏规则。
- `wiki/00_meta/b2b-export-module-map.md`：外贸 B2B 模块地图。
- `wiki/10_sources/`：来源登记与来源摘要。
- `wiki/20_concepts/`：长期概念库。
- `wiki/30_playbooks/`：可执行方法论。
- `wiki/40_business/`：业务底座。
- `wiki/50_channels/`：渠道打法。
- `wiki/60_clients/`：客户档案。
- `wiki/70_competitors/`：竞品档案。
- `wiki/80_metrics/`：指标、实验、看板口径。
- `wiki/90_outputs/`：草稿、成稿、可复用产出。
- `wiki/99_archive/`：过时 wiki 页归档。
- `wiki/_templates/`：页面模板。
