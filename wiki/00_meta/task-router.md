---
title: "Task Router"
description: "把用户请求映射到应读取文件、可修改文件、必须更新记录和交付格式，帮助无记忆 agent 快速接手。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["Subagent adversarial review"]
related: ["current-focus.md", "ai-operating-manual.md", "source-taxonomy.md", "definition-of-done.md", "check-mechanism-map.md", "agent-handoff.md"]
---

# Task Router

无记忆 agent 接手时，先用这张表判断任务路线。

| 用户请求 | 先读 | 可更新 | 必须更新 | 交付格式 |
|---|---|---|---|---|
| 新建长期知识页 | `wiki/00_meta/document-id-standard.md`, 目标目录 `index.md`, 最窄模板 | 目标知识页、对应 index | `doc_id`, sources/related, 当日日志 | 文件名、description、适用边界、证据和验证状态 |
| 处理原始对话 | `raw/index.md`, `raw/10_conversations/index.md`, `raw/_templates/conversation-source.md`, `publishing-and-redaction.md` | 私有 raw 或公开去敏入口、source registry | 当日日志、`derived_to`, 必要时 open questions | Source ID、敏感级别、同意状态、原文与提炼边界 |
| 提炼课程模块 | `wiki/90_outputs/courses/index.md`, `wiki/_templates/course-module.md`, 相关 concept/playbook | course module、练习、验证记录 | 当日日志、source registry、writeback | 来源、目标、步骤、练习、验收、边界和写回 |
| 运行结构体检 | `wiki/index.md`, 相关目录 index, `document-id-standard.md`, release docs | 只修改明确授权范围 | 当日日志、对抗审查记录 | 结构事实、验证命令、BLOCK/WARN/PASS 和残余风险 |
| 吸收新资料 | `wiki/index.md`, `ai-operating-manual.md`, `source-taxonomy.md`, `raw/index.md`, 对应 raw 分类入口和指定 raw 文件 | 相关业务/渠道/playbook/source 页 | `source-registry.md`, 当日日志 `logs/YYYY/YYYY-MM/YYYY-MM-DD.md`, 相关 index, 必要时 `open-questions.md` | 吸收摘要、更新文件、未解问题 |
| 建站/改页面 | `wiki/40_business/business-overview.md`, `wiki/40_business/id-0013-icp.md`, `wiki/40_business/offers.md`, `wiki/40_business/messaging-house.md`, `wiki/40_business/proof-library.md`, `wiki/30_playbooks/website-build.md` | website channel、outputs、相关 playbook | 若产生复用稿，更新 `90_outputs/` | 页面结构、文案、风险、待验证 |
| LinkedIn 内容 | `wiki/40_business/id-0013-icp.md`, `wiki/40_business/id-0012-customer-pain-map.md`, `wiki/40_business/messaging-house.md`, `wiki/30_playbooks/linkedin-content.md`, LinkedIn channel | outputs、LinkedIn channel、messaging | 重要内容沉淀 `90_outputs/` | 内容策略或帖子草稿 |
| 开发信 | `wiki/40_business/id-0013-icp.md`, `wiki/40_business/offers.md`, `wiki/40_business/id-0014-objections.md`, `wiki/40_business/proof-library.md`, `wiki/30_playbooks/cold-email.md` | outputs、email channel、objections | 若有新回复/数据，更新 source 和 metrics | 邮件序列、个性化角度、风险 |
| SEO | `wiki/30_playbooks/id-0011-seo-content.md`, SEO channel, `wiki/20_concepts/id-0001-search-intent.md`, `wiki/80_metrics/index.md` | SEO channel、outputs、topic map | 若有关键词/表现数据，更新 metrics | 关键词地图、brief、优先级 |
| GEO | `wiki/30_playbooks/id-0010-geo-ai-search.md`, GEO channel, business overview, competitor pages | GEO channel、test log、outputs | 记录测试问题和结果 | AI 搜索测试、纠偏动作 |
| SEM/Ads | `sem-ads.md`, Ads channel, metrics, proof, landing pages | Ads channel、experiment record、outputs | 实验记录、指标口径、销售反馈 | 实验方案、止损规则、复盘 |
| 销售/谈客户 | `sales-call.md`, ICP, offers, objections, proof | client profile、sales notes、objections | 成交/丢单学习回流 business pages | 通话提纲、资格评分、下一步 |
| 坑点分析 | `pitfall-analysis.md`, 相关 playbook, metrics | pitfall 页面、decision log、quality checklist | 若影响策略，更新 decision log | 根因、影响、修复、预防 |
| 子库维护 / 课程改进 | `current-focus.md`, `sub-library-contract.md`, 子库 `README.md`, `COURSE-MAP.md`, `MANIFEST.md`, `wiki/90_outputs/courses/index.md` | 当前焦点子库、模板、adapter、QA | 导航、manifest、当日日志和必要的月度摘要 | 变更、验证、残余 BLOCK |
| 新增模块 | `current-focus.md`, `module-expansion-sop.md`, `module-registry.md` | 优先登记 candidate；获批后才建 index / playbook / template | current focus、registry、相关 index | 晋升理由、完成闸、后续待办 |
| 多人维护 | `collaboration-model.md`, `markdown-standard.md`, `agent-handoff.md` | owner/reviewer 字段、handoff、decision log | conversation log 或 decision log | 角色、分工、审核动作 |
| GitHub 发布/去敏 | `publishing-and-redaction.md`, source registry, 相关页面 | redacted copy 或 visibility 字段 | redaction checklist, decision log | 可公开/不可公开清单 |
| Wiki 体检 | `quality-checklist.md`, `markdown-standard.md`, index files | meta docs、索引、重复页 | 当日日志、月度摘要或 handoff | 问题清单、修复列表、残余风险 |

## 内容的唯一归宿

同一个事实只维护一个可编辑真相源，其他位置使用 Markdown 链接和必要的一句上下文，不复制整段正文。拿不准归宿时先记录到 `raw/00_inbox/` 或 `open-questions.md`，不得为了“方便”新建第二真源。

| 内容类型 | 唯一真相源 | 其他位置如何引用 | 禁止复制 / 冒充的位置 |
|---|---|---|---|
| 原始对话、网页抓取、文档转写、媒体或导出 | `raw/` 对应分类；真实敏感材料进入仓库外私有运行区 | `10_sources` 登记 Source ID、授权、摘要和 raw 指针 | 不把原文复制进 wiki、课程、日志或子库源码 |
| 来源身份、日期、授权、证据边界 | `wiki/10_sources/` | concept、playbook、course 通过 Source ID / 路径引用 | 不在多个业务页各维护一套来源事实 |
| 稳定定义、判断模型和跨场景原则 | `wiki/20_concepts/` | playbook、channel、course 链接该概念并补场景差异 | 不把工具按钮说明写成长期概念 |
| 可重复执行的方法、步骤、失败处理和验收 | `wiki/30_playbooks/` | channel、course、sub-library 只引用或声明自己的适配差异 | 不在课程和子库各复制一套通用 SOP |
| 当前公司、产品、ICP、offer、异议和证据事实 | `wiki/40_business/`；真实客户事实进私有运行区 | 渠道和输出页链接业务事实并注明快照日期 | 不把假设、synthetic fixture 或客户私密数据写成母库事实 |
| 教学顺序、练习、验收和学员 writeback | `wiki/90_outputs/courses/` | 引用 source、concept、playbook；只新增教学表达 | 不把 raw 原文或未经验证的框架包装成课程结论 |
| 可独立交付的完整能力模块 | `sub-libraries/<id>/` | 母库只保留 registry、canonical 入口和通用知识链接 | 不建平行根级 `skills/` 或复制整套母库知识 |
| 真实运行输入、凭据、客户对象、接口响应和私有证据 | 仓库外客户私有运行区 | 公开库只写去敏证据指针、边界和可复用结论 | 不提交到公开 `raw/`、wiki、日志、fixture 或 release artifact |
| 发布范围、版本、许可、状态、approval 和 tag | 当前 scope 的 `MANIFEST.md`、`RELEASE.md`、`VERSION.md` 与 sidecar | README/registry 展示同步后的摘要并链接合同 | 不用 README 文案、日志或另一个 scope 的 PASS 覆盖合同 |
| 当日事件与证据指针 | `wiki/00_meta/logs/YYYY/YYYY-MM/YYYY-MM-DD.md` | 月度摘要提炼稳定结论并回写上述真相源 | 不复制 raw 原文，不用日志替代长期知识页 |

### 放置决策顺序

1. 先问“这是来源、稳定知识、执行方法、业务事实、教学表达、独立交付、私有运行还是发布合同？”
2. 只在对应唯一真相源编辑正文；如果同时影响多个层，只更新各层独有的职责字段并互相链接。
3. 新增前搜索标题、`doc_id`、Source ID、关键词和 canonical 入口，优先更新已有页。
4. 变更完成后更新直接父目录索引、当日日志和必要的 handoff；用 [检查机制地图](check-mechanism-map.md) 声明本次 PASS 的边界。

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
