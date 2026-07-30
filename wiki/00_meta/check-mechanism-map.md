---
title: "Check Mechanism Map"
description: "把母库和子库的机器检查、人工复核与真实运行证据分层，明确每个 PASS 能证明什么、不能证明什么、由谁负责及何时必须阻断。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-29"
last_updated: "2026-07-29"
sources: ["Adversarial review 2026-07-29", "Release governance validators"]
related: ["definition-of-done.md", "release-checklist.md", "release-state-machine.md", "release-approval-and-tag-namespaces.md", "../../scripts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
keywords: ["检查机制", "结构验证", "制品验证", "人工批准", "真实运行", "课程效果", "发布闸"]
---
# 检查机制地图

下游只能消费与自己 **scope、对象、commit、content digest、证据类型和时间窗口**一致的结论。任何 PASS 都必须同时说明未验证边界。

## 机制总表

| 检查 / 状态 | 类型 | 证明什么 | 不证明什么 | 主要阻断 | 命令 / 证据 |
|---|---|---|---|---|---|
| `INDEX_SYNC_CHECK_PASS` | 机器 | index 生成区与当前直接入口元数据一致，redirect 未进入 canonical 主表 | 页面内容真实、链接可达、生成结果已人工审阅 | 生成区陈旧、越级收录、redirect 与 canonical 同权 | `node scripts/sync-indexes.mjs --check` |
| `INDEX_VALIDATION_PASS` | 机器 | 元数据形状、canonical 入口、直接层级、反递归和生成区新鲜度符合当前规则 | 内容真实、课程有效、可发布 | 缺字段、入口漂移、陈旧 description/日期、活动引用命中 redirect | `node scripts/validate-indexes.mjs --check`；候选用 `--strict` |
| `LINK_VALIDATION_PASS` | 机器 | 当前 scope 的本地链接和发布路径边界可解析 | 远程 URL 内容真实、接口可用、页面质量 | 断链、越根、release 禁止路径、活动引用命中 redirect | `node scripts/validate-links.mjs`；候选用 `--release` |
| `DOCUMENT_ID_PASS` | 机器 | durable roots 内编号格式、唯一性和 scope 隔离符合合同 | legacy 已全部迁移、页面质量 | 重号、文件名与 `doc_id` 不一致、越界编号 | `node scripts/validate-document-ids.mjs [--scope ...]` |
| `LOG_VALIDATION_PASS` | 机器 | 日志路径、日期、事件 ID、字段和重复性符合规则 | 事件真实发生、证据内容正确、稳定结论已写回 | 日期/ID 不一致、重复 ID、缺 evidence 或 release 字段 | `node scripts/validate-logs.mjs [--release]` |
| `KNOWLEDGE_CHAIN_STRUCTURE_PASS` | 机器 | raw/source/derived/course/verification/writeback 声明链可解析 | 学员完成、reviewer 独立、课程产生效果 | 路径断裂、角色不匹配、release 证据缺失 | `node scripts/validate-knowledge-chain.mjs [--release]` |
| `STRUCTURE_PASS` | 机器 | 某一个母库或子库 scope 的静态合同自洽 | 另一个 scope、artifact、运行、批准或 Published | manifest/registry/合同或 scope validator 失败 | 母库或目标子库 validator |
| `ARTIFACT_PASS` | 机器 | 候选文件集合、manifest、checksum 与当前构建规则自洽 | clean source、真实 tag、批准者身份、安装运行或已发布 | 文件越界、未知扩展、本地路径、摘要或集合不一致 | artifact validator 与 `SHA256SUMS` |
| `RELEASE_SCOPE_PASS` | 机器 | 输入 tag 名只解析为当前版本的一个母库或注册子库 scope | tag object 实际存在、签名可信、sidecar 有效 | 裸 tag、未知 namespace/子库、错版本或重复路由 | `node scripts/resolve-release-scope.mjs <tag>` |
| `APPROVAL_RECORD_PASS` | 机器记录校验 | sidecar 字段、scope、commit、candidate digest、manifest/checksum 摘要、tag 声明与 locator 结构精确绑定 | `approved_by` 真人身份、实际 tag object、签名者授权、远端保护或发布决定 | 结构缺失、scope/commit/digest 串线、locator 不可接受、AI/system token | trusted `validate-release-approval.mjs` 对候选外记录的结果 |
| `TAG_RECEIPT_BINDING_PASS` | 外部 workflow + 机器比对 | workflow 读取的实际 tag object SHA、target commit、signer fingerprint、canonical annotation bytes/digest 和 approval binding 与同一 candidate 精确一致 | signer 是批准者本人、signer 获业务授权、Environment/ruleset 已正确配置 | 任一实际值缺失/漂移、签名无效、fingerprint 不在外部 allowlist、annotation 非 canonical | 服务端 job 的 `git verify-tag --raw`、tag receipt 与跨 job 输出 |
| `QUALIFICATION_ARTIFACT_PASS` | 外部 workflow + 机器 | 唯一 scope、trusted workflow/governance、approval/tag receipt、候选、runtime profile、archive 和 attestation 在一次 run 中绑定 | GitHub Release 已创建、真人身份已证实、业务效果或未来稳定 | 外部配置/可信 SHA/signer 缺失、候选可替换、runtime 控制面不可信、archive 不等价 | qualification run、archive、checksum、`QUALIFICATION-ATTESTATION.json` |
| `RUNTIME_VERIFICATION_PASS` | 人工主导 + 自动证据 | 指定部署、site、operation、对象/批次和时间窗口内完成并回读 | 跨部署、任意规模、未来稳定 | 缺 authorization context、对象定位、回读、失败/回滚或清理证据 | 私有运行记录、接口/后台/前台验收 |
| `COURSE_EFFECT_PASS` | 人工 | 指定学员提交由独立 reviewer 审核并形成 verification/writeback | 所有人稳定使用、正式发布已批准 | 未提交、作者自评、无 reviewer、无前后证据 | exercise、review record、verification、writeback |
| `PUBLISHED` | 外部事实 + 人工决策 | 精确 scope/version/digest 已在批准目标完成发布，并有可回读的发布记录 | 内容永久正确、未来稳定、其他 scope 已发布 | 无明确批准、目标不明、发布对象/digest 不一致、无法回读 | 发布平台 URL/ID、时间、actor 证明、发布摘要与下架入口 |

## 不可替代关系

```text
索引/链接 PASS ≠ 内容真实
结构 PASS ≠ 制品 PASS ≠ 运行 PASS
批准记录 PASS ≠ 真人身份 ≠ 实际签名 tag
qualification artifact ≠ Published
母库 PASS ≠ 子库 PASS
synthetic fixture PASS ≠ 真实客户或生产 PASS
作者完成 ≠ 独立 reviewer 通过
```

## 状态消费规则

1. verdict 必须带 scope、对象、commit/digest（适用时）、证据指针、时间窗口和未验证项。
2. `reviewer_identity`、`independence_status` 与 `reviewer_authorship` 必须显式记录；机器校验不能把 `not_verified` 自动升级为 verified。
3. `WARN` 只有在不阻断下一步且已有 owner、期限或追踪入口时才可继续；`BLOCK` 不得靠改措辞或换 scope 绕过。
4. `needs_tony` 表示 AI 无权决定，保持 BLOCK，等待 Tony 明确批准或拒绝。
5. CI 只证明实际执行的命令、代码和 fixture；未接入 CI 的检查不得写成自动闸。
6. workflow 文件中的 Environment 名称、secret 名称或 signer 字段不是远端配置证据；必须由目标远端的真实设置和服务端 run 证明。
