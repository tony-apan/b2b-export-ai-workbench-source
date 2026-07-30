---
title: "Reviewer Evidence Records"
description: "保存跨 agent 审查的机器可读身份、scope、源码和原始 verdict 证据字段；缺少任务 ID、内容摘要或不可变原始报告时明确标记 producer-reported 与 not_verified，防止作者自报被误当成独立批准。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-29"
last_updated: "2026-07-29"
sources: ["../wiki/00_meta/agent-handoff.md", "../wiki/00_meta/logs/2026/07/2026-07-29.md"]
related: ["../wiki/00_meta/agent-handoff.md", "../wiki/00_meta/current-focus.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
when_to_read: "需要判断 reviewer 是否真实独立、审查对象是否绑定到精确快照，或需要让下一位 agent 恢复原始 verdict 证据时。"
keywords: ["review record", "reviewer independence", "agent id", "scope manifest", "content digest", "original verdict", "producer-reported"]
---
# Reviewer Evidence Records

本目录是审查证据登记层，不是批准系统。JSON 字段只能记录现有证据，不能通过填写名称自行证明 reviewer 独立、真人身份或正式批准。

## 使用规则

1. 新审查先生成稳定 `review_id`，再记录 `agent_id` 或可信账号/任务标识。
2. `scope_manifest` 必须绑定被读文件清单；`source_commit` 与 `content_digest` 必须说明是内容绑定还是仅上下文。
3. 原始 verdict 应指向 reviewer 自己产生的记录；只有 Producer 总结时，必须保持 `provenance_status: producer-reported`。
4. `identity_status` 或 `independence_status` 只有存在可信任务/账号/审查渠道证据时才能改为 `verified`。
5. 本地可覆盖文件不得写成 `immutable: true`；没有原始报告时必须使用 `available: false` 和空 locator/digest。
6. 这些记录不能替代 Tony 的 approval、Protected Environment、正式 tag 或 qualification artifact。

Schema：[reviewer-record.schema.json](reviewer-record.schema.json)。

## 当前历史声明迁移

| review_id | 名称 | Producer 声称的角色/verdict | 当前证据等级 | 独立性 | 原始 verdict |
|---|---|---|---|---|---|
| `REV-20260729-HEISENBERG-0001` | Heisenberg | 治理测试/CI 子任务；reviewer verdict 未记录 | producer-reported | not_verified | unavailable |
| `REV-20260729-NOETHER-0001` | Noether | 首轮 reviewer / block | producer-reported | not_verified | unavailable |
| `REV-20260729-LINNAEUS-0001` | Linnaeus | 首轮 reviewer / block | producer-reported | not_verified | unavailable |
| `REV-20260729-CONFUCIUS-0001` | Confucius | 对抗 reviewer / block | producer-reported | not_verified | unavailable |
| `REV-20260729-MCCLINTOCK-0001` | McClintock | final reviewer / warn | producer-reported | not_verified | unavailable |

以上五条只恢复“仓库曾如何声称”，**不恢复或伪造不存在的 agent ID、scope manifest digest、原始 verdict 和外部不可变证明**。
