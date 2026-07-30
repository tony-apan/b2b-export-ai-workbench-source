---
title: "Open Questions"
description: "只保存当前真正 open、blocked 或 deferred 的问题，并为每项提供稳定 ID、owner、阻断 scope、证据与下一步；已关闭事项迁移到冻结决策映射或历史日志，不在本页重复。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["current-focus.md", "decision-log.md", "logs/2026/07/2026-07-summary.md"]
related: ["current-focus.md", "decision-log.md", "logs/index.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要判断当前还有哪些业务、课程、CMS 或正式发布问题未闭合，以及某项是否真正阻断下一步时。"
keywords: ["open questions", "blocked", "deferred", "owner", "evidence", "next action", "closed migration"]
---
# Open Questions

本页是**当前未决事项的唯一清单**。只允许 `open`、`blocked`、`deferred`；已关闭问题不得继续留在正文，应迁入 [冻结决策与关闭事项映射](decision-log.md#closed-question-migration-map) 或按日日志。

## 业务底座

| question_id | 状态 | 问题 | owner | 阻断 scope | 证据 | 下一步 |
|---|---|---|---|---|---|---|
| `OQ-BIZ-0001` | open | 核心业务一句话、服务对象、问题和结果是什么？ | Tony | 对外定位 | `wiki/40_business/` 当前仍含假设/seed 内容 | 提供真实业务简述并区分公开与私有证据。 |
| `OQ-BIZ-0002` | open | 目标 ICP、排除型客户、地区、规模、职位和预算是什么？ | Tony | 精准获客输出 | `wiki/40_business/id-0013-icp.md` | 用真实成交/丢单样本校准。 |
| `OQ-BIZ-0003` | open | 可公开案例、结果、客户评价和授权证明有哪些？ | Tony | proof 与课程效果声明 | `wiki/40_business/`、发布去敏规则 | 先完成授权和脱敏登记。 |
| `OQ-OFFER-0001` | open | 产品包、价格、周期、交付物和售后边界是什么？ | Tony | offer、销售和课程落地 | `wiki/40_business/` | 提供当前商业版本，未确认前只输出假设版。 |
| `OQ-CHANNEL-0001` | deferred | 网站、SEO、GEO、开发信、Ads 和销售漏斗的真实基线数据是什么？ | Tony | 效果验证 | 当前公开库没有真实经营数据 | 在客户私有运行区接入后再评估。 |

## Website Content Operations

| question_id | 状态 | 问题 | owner | 阻断 scope | 证据 | 下一步 |
|---|---|---|---|---|---|---|
| `OQ-CMS-0001` | blocked | `postCreate` 的当前部署完整合同和精确新 `postId` 回读尚未验证。 | Adapter owner | create 能力放行 | `current-focus.md` Current BLOCK | 获批后先捕获当前部署真实 UI 请求，再做单样本和回读。 |
| `OQ-CMS-0002` | blocked | taxonomy、Slate、封面对象和 Server Action 能否跨部署/跨站点稳定？ | Adapter owner | 稳定子库声明 | `current-focus.md`；历史验证只绑定当前部署 | 每次部署动态发现；至少补第二部署/站点证据。 |
| `OQ-CMS-0003` | blocked | 503、transaction state mismatch、请求可能成功后的恢复和回滚缺少文章级远程证据。 | Adapter owner | 远程失败恢复 | 当前只有本地故障控制 | 自然失败时只读对账，保存精确证据，不为测试制造生产数据。 |
| `OQ-CMS-0004` | deferred | 大于 11 篇的限流、长跑、中断恢复和全量对账是否稳定？ | Adapter owner | 大批量稳定声明 | 当前证据上限为 11 篇 | 仅在明确授权或自然业务批次中验证。 |
| `OQ-CMS-0005` | open | `/sites` 是否存在分页、多 workspace、归档、禁用或邀请中状态？ | Adapter owner | 多站点发现 | 当前只验证 SSR/RSC 当前样本 | 在出现对应账号条件时只读捕获。 |
| `OQ-THEME-0001` | blocked | 当前主题无序列表语义和正文图片 Alt 透传应由编辑器、主题还是两者修复？ | Product/theme owner | 无障碍和前台语义 | 当前主题观察到嵌套 `div` 与空 Alt | 先定位渲染层，再做主题级修复与验收。 |
| `OQ-CMS-0006` | deferred | 表格、嵌套列表、图库、图片链接和更多 Plate 节点合同尚未验证。 | Adapter owner | 复杂内容覆盖 | 当前只闭合部分 Slate 节点 | 先捕获目标部署真实 UI 节点，禁止猜 payload。 |

## 工具与演示环境

| question_id | 状态 | 问题 | owner | 阻断 scope | 证据 | 下一步 |
|---|---|---|---|---|---|---|
| `OQ-TOOL-0001` | deferred | 课程 R2 使用新建 bucket、现有空演示 bucket、自定义域名还是开发 URL？ | Tony | R2 演示 | 尚无批准 | Tony 选择无真实业务数据的演示资源。 |
| `OQ-TOOL-0002` | deferred | 是否批准 Wrangler v4、PicGo R2/S3 adapter，以及 GUI/CLI 统一配置？ | Tony | PicGo/R2 执行 | 尚无批准 | 明确工具与配置保存边界后再安装。 |
| `OQ-TOOL-0003` | open | 哪个真实但可安全操作的网站用于最终端到端验收？ | Tony | 真实验收 | 当前只有限定站点证据 | 指定站点、权限、可写范围和回滚责任人。 |

## 正式发布与审查证据

| question_id | 状态 | 问题 | owner | 阻断 scope | 证据 | 下一步 |
|---|---|---|---|---|---|---|
| `OQ-REL-0001` | blocked | Stable 阶段的最终品牌、Logo、官网、邮箱和更新入口未确定。 | Tony | Stable/正式营销发布 | 当前 FluxPedal 仅为明确标注的虚拟案例；Preview 使用仓库名和 Tony 公开联系入口 | Preview 保持虚拟示例声明；Stable 前确认品牌资产与授权。 |
| `OQ-REL-0002` | blocked | 母库对外发行和子库 Stable 的最终商业/法律边界仍未批准。 | Tony | 母库公开/Stable + 子库 Stable | 子库 Public Preview 已采用 Apache-2.0 并补齐 LICENSE/NOTICE；母库为 restricted private source | Preview 按 Apache-2.0；母库公开或子库 Stable 前另行完成法律/商业审查。 |
| `OQ-REL-0003` | blocked | GitHub Protected Environment、required reviewers、ruleset、可信 signer 和正式 qualification 尚未建立。 | Tony | 母库公开/Stable + 子库 Stable qualification | Public Preview prerelease 已发布并从远端重克隆验收；本地 prepare→qualify、archive/checksum/attestation 合同与 53/53 攻击测试已闭合，但仍无 Stable 服务端 run | Preview 不冒充正式 qualification；Stable 前在服务端逐 scope 配置并演练，保存 exact archive、checksum、attestation 和 run identity。 |
| `OQ-REV-0001` | blocked | 五个历史 reviewer 声明没有 agent ID、scope digest 或不可变原始 verdict。 | Repository owner | 将历史审查视为独立证据 | `REVIEW-RECORDS/` 均为 producer-reported / not_verified | 后续审查使用 reviewer record schema，从任务创建时绑定证据。 |
| `OQ-REL-0004` | deferred | Public Preview 的普通 clone 验收命令和私有 upstream / 公开 release provenance 字段是否需要进一步拆分？ | Release owner | 新手自验证与公开来源可解释性 | `v0.3.2-preview.1` 的纯 `git archive` artifact、逐文件 SHA-256 和公开 release commit 可验证；clone 根目录含 `.git/` 会被 artifact validator 拒绝，私有母库 source commit 不能由公开用户解析 | 下一 Preview 在 README/INSTALL 补 clone→archive 标准命令，并分字段声明 private upstream、public release commit/tag 和 public resolvability；不移动现有 tag。 |

## 课程证据

| question_id | 状态 | 问题 | owner | 阻断 scope | 证据 | 下一步 |
|---|---|---|---|---|---|---|
| `OQ-COURSE-0001` | blocked | 第二场景由谁评分、最低通过线和独立评分次数是多少？ | Tony/course owner | 课程 release | 知识链 release gate 仍 BLOCK | 定义 rubric、reviewer 和通过阈值。 |
| `OQ-COURSE-0002` | open | 哪些失败模式触发复训、改 playbook 或暂停发布？ | Course owner | 课程运营 | 尚无真实学员样本 | 首批私有教学后按失败模式回写。 |
| `OQ-COURSE-0003` | deferred | 是否统一公开 fixture_id，并绑定 raw/source/verification/writeback？ | Governance owner | fixture 检索一致性 | 当前 synthetic 链已结构闭合 | 在新增第二 fixture 前决定，避免批量迁移。 |
| `OQ-COURSE-0004` | blocked | 真实私有样本如何只公开来源类型、脱敏摘要和证据摘要而不泄露原文？ | Tony/privacy owner | 真实课程证据公开 | 发布去敏规则 | 先在私有运行区定义脱敏与授权记录。 |
| `OQ-COURSE-0005` | open | `VER-`、`WB-`、redirect 等豁免记录是否需要独立完整性 validator？ | Governance owner | 记录完整性 | 当前仅从 durable ID 统计豁免 | 先统计实际缺口，再决定是否新增 validator。 |
