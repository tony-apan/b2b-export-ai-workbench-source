---
doc_id: "ID-0002"
title: "Index as Retrieval Contract"
description: "面向维护母库或子库的人和 AI，规定每个 index 如何描述当前目录的直接入口、读取时机和检索词，帮助在文件增长后仍能准确定位文档；不替代目标文档正文或发布合同。"
type: "concept"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["SRC-20260728-0001"]
related: ["../00_meta/index-and-discovery-standard.md", "../00_meta/raw-conversation-and-course-pipeline.md", "../30_playbooks/id-0003-raw-to-course-closure.md", "../90_outputs/courses/id-0004-structure-to-course-closure.md"]
confidence: "medium"
when_to_read: "当新增文件夹、文档或子库，或者 AI 开始把全文递归塞进一个大 index 时，先读本页确认索引粒度和描述字段。"
keywords: ["index", "索引", "retrieval contract", "description", "when to read", "keywords", "直接入口"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Index as Retrieval Contract

## 定义

`index.md` 不是把所有正文复制一遍的目录，而是当前文件夹的**检索合同**：它告诉人和 AI 当前层负责什么、每个直接入口解决什么问题、什么时候应该打开它，以及下一步沿哪条路径继续读取。

## 为什么重要

当文件数量增长时，AI 的成本和误召回风险通常不是因为没有文件，而是因为入口缺少语义。只有文件名的目录会迫使 AI 逐个打开正文；把所有后代内容堆到根 index 又会制造巨大上下文和重复事实。

## 当前稳定规则

1. 每个正式目录保留一个 canonical `index.md`，实现目录也要明确是否提供入口。
2. 当前 index 只列当前目录的直接 Markdown 文件和直接子目录的 canonical 入口。
3. 每行至少包含 ID、入口、description、type、状态/可见性、什么时候读和检索词。
4. description 用人话说明对象、问题、结果和边界，不使用“页面说明”一类空描述。
5. 上级 index 负责路由，下级 index 负责当前层的完整入口；正文只保留在目标文档。
6. 生成区由脚本同步，人工只维护页面元数据和正文中的导航说明。

## 证据和边界

本页来源是一个明确标记为 synthetic fixture 的结构治理样本，并与现有索引标准相互印证。它证明了如何设计和验收索引合同，不证明任何外部搜索数据、客户行为或生产检索性能。

## 验收问题

- 新人只读上级 index，能否判断下一步应该进入哪个目录？
- AI 不打开全部正文，能否根据 description 和 keywords 选出正确入口？
- 当前 index 是否只包含直接入口，而不是复制孙级内容？
- 页面状态是否明确区分 Seed、Draft、Working、BLOCK 和 Published？
- description 是否说明了适用边界，而不是把推断写成事实？

## Open Questions

- 当单个目录直接入口超过约 80 个时，具体拆分主题的阈值是否需要按业务复杂度动态调整？
- 是否需要在未来增加机器可读的 alias 或 deprecated path 字段来支持更长时间的旧链接迁移？
