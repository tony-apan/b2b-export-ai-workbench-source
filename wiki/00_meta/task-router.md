---
title: "Task Router"
description: "把用户请求映射到应读取文件、可修改文件、必须更新记录和交付格式，帮助无记忆 agent 快速接手。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Subagent adversarial review"]
related: ["ai-operating-manual.md", "source-taxonomy.md", "definition-of-done.md"]
---

# Task Router

无记忆 agent 接手时，先用这张表判断任务路线。

| 用户请求 | 先读 | 可更新 | 必须更新 | 交付格式 |
|---|---|---|---|---|
| 吸收新资料 | `wiki/index.md`, `ai-operating-manual.md`, `source-taxonomy.md`, 指定 `raw/` | 相关业务/渠道/playbook/source 页 | `source-registry.md`, `ingestion-log.md`, 相关 index, 必要时 `open-questions.md` | 吸收摘要、更新文件、未解问题 |
| 建站/改页面 | `business-overview.md`, `icp.md`, `offers.md`, `messaging-house.md`, `proof-library.md`, `website-build.md` | website channel、outputs、相关 playbook | 若产生复用稿，更新 `90_outputs/` | 页面结构、文案、风险、待验证 |
| LinkedIn 内容 | `icp.md`, `customer-pain-map.md`, `messaging-house.md`, `linkedin-content.md`, LinkedIn channel | outputs、LinkedIn channel、messaging | 重要内容沉淀 `90_outputs/` | 内容策略或帖子草稿 |
| 开发信 | `icp.md`, `offers.md`, `objections.md`, `proof-library.md`, `cold-email.md` | outputs、email channel、objections | 若有新回复/数据，更新 source 和 metrics | 邮件序列、个性化角度、风险 |
| SEO | `seo-content.md`, SEO channel, `search-intent.md`, `metrics/index.md` | SEO channel、outputs、topic map | 若有关键词/表现数据，更新 metrics | 关键词地图、brief、优先级 |
| GEO | `geo-ai-search.md`, GEO channel, business overview, competitor pages | GEO channel、test log、outputs | 记录测试问题和结果 | AI 搜索测试、纠偏动作 |
| SEM/Ads | `sem-ads.md`, Ads channel, metrics, proof, landing pages | Ads channel、experiment record、outputs | 实验记录、指标口径、销售反馈 | 实验方案、止损规则、复盘 |
| 销售/谈客户 | `sales-call.md`, ICP, offers, objections, proof | client profile、sales notes、objections | 成交/丢单学习回流 business pages | 通话提纲、资格评分、下一步 |
| 坑点分析 | `pitfall-analysis.md`, 相关 playbook, metrics | pitfall 页面、decision log、quality checklist | 若影响策略，更新 decision log | 根因、影响、修复、预防 |
| 新增模块 | `module-expansion-sop.md`, `module-registry.md`, `markdown-standard.md` | raw folder、module index、playbook、template、registry | 总索引、模块索引、source taxonomy（如需要） | 新模块最小文件集和后续待办 |
| 多人维护 | `collaboration-model.md`, `markdown-standard.md`, `agent-handoff.md` | owner/reviewer 字段、handoff、decision log | conversation log 或 decision log | 角色、分工、审核动作 |
| GitHub 发布/去敏 | `publishing-and-redaction.md`, source registry, 相关页面 | redacted copy 或 visibility 字段 | redaction checklist, decision log | 可公开/不可公开清单 |
| Wiki 体检 | `quality-checklist.md`, `markdown-standard.md`, index files | meta docs、索引、重复页 | `ingestion-log.md` 或 handoff | 问题清单、修复列表、残余风险 |

## 读多少才够

| 任务大小 | 读取范围 |
|---|---|
| 小任务 | 总索引 + 1 个相关 playbook/channel |
| 中任务 | 总索引 + 业务底座 + 相关 playbook/channel + sources |
| 大任务 | 总索引 + 业务底座 + 多渠道 + metrics + outputs + raw sources |

## 缺信息时怎么办

- 如果缺少核心业务事实，可以输出“假设版”，但必须标注 `假设` 和 `待验证`。
- 如果缺少证据，不能写确定性结果。
- 如果缺少指标口径，不能比较渠道优劣。
- 如果用户明确要继续，先给可执行草案，再把缺口写入 [open-questions.md](open-questions.md)。
