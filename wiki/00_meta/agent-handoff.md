---
title: "Agent Handoff"
description: "定义跨 agent 或跨轮次交接的结构化 verdict、证据、未验证边界和升级路径，让无记忆接手者知道能否继续、该退回谁以及哪些决定必须交给 Tony。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-30"
sources: ["Subagent adversarial review", "Adversarial review protocol 2026-07-29", "Tony human README and AI START-HERE decision 2026-07-30"]
related: ["task-router.md", "definition-of-done.md", "markdown-standard.md", "check-mechanism-map.md", "../../REVIEW-RECORDS/README.md"]
---
# Agent Handoff

阶段性工作、跨 agent 复审或暂停任务时，交接必须回答三个问题：**做了什么、真实证据是什么、下一步是否被阻断。** Producer 的总结不是 Reviewer 的证明。

## Canonical machine-readable handoff

用于 qualification、发布门禁或“已验证 PASS”声明的 handoff 必须是独立 JSON sidecar，并符合 `scripts/schemas/handoff.schema.json`。Markdown/YAML 只供人阅读，不能替代 canonical record。

```bash
node scripts/validate-handoff.mjs --file path/to/handoff.json
node scripts/validate-handoff.mjs --file path/to/handoff.json --release
```

CLI 只接受干净的 repository-relative `--file` 路径。schema 文件字节摘要固定在 validator 中；schema 漂移会 fail-closed，必须连同 validator 与测试一起接受治理审查。

Canonical JSON 顶层字段：

```json
{
  "schema_version": 1,
  "handoff_id": "HND-YYYYMMDD-NAME-0001",
  "scope": "mother-library | sub-library:<id> | file-set:<id>",
  "producer": {"name": "...", "agent_id": "... or null"},
  "reviewer": {"name": "...", "agent_id": "... or null"},
  "reviewer_provenance": "producer-reported | reviewer-authored | externally-attested",
  "identity_status": "verified | not_verified",
  "independence_status": "verified | not_verified",
  "scope_binding": {
    "scope_manifest": {"kind": "repository-relative", "locator": "...", "sha256": "sha256:..."},
    "source_commit": "40-lowercase-hex or null",
    "source_commit_binding": "content-bound | context-only | not-recorded",
    "content_digest": "sha256:... or null"
  },
  "original_verdict": {"available": false, "immutable": false, "ref": null, "binding": null},
  "attestations": {"identity": null, "independence": null, "reviewer_authorship": null},
  "verdict": "pass | warn | block | needs_tony",
  "blocks_next_step": true,
  "evidence_refs": [{"kind": "repository-relative", "locator": "...", "sha256": "sha256:..."}],
  "evidence_bundle_digest": "sha256:...",
  "not_verified": ["explicit boundary"],
  "return_to": "producer or owner",
  "approval_required": "Tony or named approver"
}
```

完整字段和 `additionalProperties: false` 约束以 schema 为准。所有 `scope_manifest`、`original_verdict.ref` 和 attestation refs 必须同时进入同一个 canonical `evidence_refs` bundle；不能通过旁路字段绕开 bundle digest。repository-relative ref 会拒绝 symlink 路径并核对当前仓库内真实文件 bytes；immutable HTTPS ref 必须满足公开、无凭据/query/fragment、无 IPv4/IPv6 私网或本地地址、无 mutable segment 且 path 含精确 SHA-256 的 locator 合同。

### 交叉约束

- `block`、`needs_tony` 必须 `blocks_next_step=true`；`pass`、`warn` 必须为 `false`。
- `--release` 只接受 `verdict=pass`；其他 verdict 即使结构有效也 fail-closed。
- `pass` 不接受 `producer-reported`，必须绑定不同的 producer/reviewer、40-hex content-bound source commit、content digest、scope manifest、可用且不可变的外部 original verdict，以及 identity、independence、reviewer_authorship 三类外部 immutable HTTPS attestation。
- 当 `source_commit_binding=content-bound` 时，`scope_manifest.locator` 必须是 repository-relative JSON；该 JSON 的 `source_commit` 或 `head` 必须精确等于 handoff 的 `source_commit`，handoff 的 `content_digest` 必须精确等于该 manifest 文件真实 bytes 的 SHA-256。只让 `evidence_refs` 中的文件摘要自洽、但不绑定 manifest 内 commit 或 manifest bytes digest，仍然 fail closed。
- 每个 attestation 和 original verdict 都带同一 `handoff_id`、`scope`、`reviewer_agent_id`、`source_commit`、`content_digest`、`verdict` 的精确 binding；其 ref SHA-256 还必须等于对应 canonical statement JSON 的真实摘要，使外部 locator digest 与这组 scope claims 绑定，任一字段漂移即失败。
- `identity_status=verified`、`independence_status=verified` 或 `reviewer-authored` 不能由显示名称、Agent 名称/ID、自报 YAML 或 producer 总结单独成立，必须有对应外部 attestation。
- 本地 validator 不下载远程对象、不验证真人或组织关系，固定输出 `human_identity=not_verified_locally`、`independence=not_verified_locally` 和 `HANDOFF_FACTUAL_VERDICT: not_verified`。因此 `HANDOFF_RECORD_STRUCTURE_PASS` 只是声明结构/绑定通过，不是人工 approval，也不是正式发布完成。

## Verdict 规则

| verdict | 何时使用 | 能否继续 |
|---|---|---|
| `pass` | 当前精确 scope 无阻断，且满足上述外部 attestation 与内容绑定合同 | 可以进入已声明的下一机械步骤；仍不替代人工发布批准 |
| `warn` | 有真实风险但不在下一步关键路径，已有 owner、追踪入口和接受理由 | 可以；必须保留 `not_verified` 和风险 |
| `block` | 正确性、安全、发布、数据、证据或合同缺口会污染下一步 | 不可以；必须 `return_to` |
| `needs_tony` | 涉及许可、公开发布、不可逆动作、范围取舍或只有 Tony 能做的判断 | 不可以；AI 不得代拍或降级 |

Producer 不得给自己的高风险交付做最终批准。母库 PASS 不得替代子库，结构 PASS 不得替代 artifact、真实运行、课程效果、Reviewer 身份或发布批准。

## Human-readable Handoff Template

```md
## Handoff: YYYY-MM-DD 任务名

<粘贴 Machine-readable Verdict>

### Task
- 用户要什么：
- 本轮目标与 scope：

### Read And Changed
- 已读权威文件：
- 已改 / 新增文件：
- 未触碰的共享状态：

### Decisions
- 已验证事实：
- 推断或待验证：
- 为什么是当前 verdict：

### Evidence
- 运行命令与关键输出：
- 文件 / 日志 / artifact / 截图指针：
- 证据与 source commit / digest 的绑定：

### Risks And Next
- 阻断或警告：
- 下一位 agent 先读：
- 退回对象、下一动作与人工审批点：
```

## 什么时候必须写交接

- 多 agent 生产与独立对抗审查后。
- 大范围修改 wiki 结构、validator、release builder 或 CI 后。
- 未完成但需要暂停，或 verdict 为 `warn`、`block`、`needs_tony` 时。
- 发现关键业务冲突、数据缺口、隐私/授权风险或 scope 串线时。
- 做了会影响后续策略、正式发布或不可逆外部动作的判断时。

## Current narrative handoff：2026-07-29 本地对抗收口与正式发布边界

> 下面是供人恢复上下文的 Markdown/YAML 叙事，不符合 canonical handoff v1 schema，不得送入 `validate-handoff.mjs`，也不得作为 qualification、identity verification 或正式 PASS。当前 dirty working tree 没有 content-bound successor snapshot；正式交接必须另存 JSON sidecar 并绑定 clean tracked scope。

```yaml
scope: current dirty working tree; mother-library + sub-library:website-content-ops local governance only
producer: Codex
reviewer: AI adversarial review only; no human or organizational identity attestation
review_id: local-2026-07-29-final-closure
reviewer_agent_id: not-a-release-identity
reviewer_provenance: producer-reported
independence_status: not_verified
scope_manifest: unavailable for the final writeback delta; historical v5 snapshot is stale
source_commit: e54b9f8297bbf9d042543cedc84731111dd3bca6 context-only; dirty working tree is not content-bound to HEAD
content_digest: null
original_verdict_locator: unavailable
verdict: block
blocks_next_step: true
evidence:
  - governance attacks passed 53/53 with known_gaps=0 and SOURCE_WORKTREE_UNCHANGED
  - focused regressions passed: G2 29/29, G3 19/19, G5 43/43
  - website-content-ops release governance passed 10/10; ordinary structure validation passed while formal release remained BLOCK
  - AllinCMS Adapter passed 131/131, npm audit --omit=dev reported 0 vulnerabilities, and npm pack dry-run excluded tests, fixtures, node_modules, coverage and private evidence
  - index, link, log and document-ID validators passed in the current local workspace; mother ordinary structure passed
not_verified:
  - reviewer names or agent IDs do not prove human identity or organizational independence
  - no clean tracked content-bound source snapshot, trusted signed tag, remote Protected Environment qualification or human approval exists
  - course real submissions, independent scoring, exercise artifacts and effectiveness evidence remain incomplete
  - AllinCMS cross-deployment, cross-site and long-run production stability is not proven
return_to: Tony for license/approval/remote decisions; otherwise keep formal release gates blocked
approval_required: Tony before git add, commit, tag, push, remote configuration or publication
```

这里的 `block` 只阻断“把当前脏工作树视为已经独立批准、正式 qualification、稳定生产能力或 Published”。本地工程和治理机制可以判为机械 `PASS`，但不能把这些结果改写为真人批准或外部发布资格。

## 历史五个 reviewer 声明的恢复边界

机器可读迁移记录位于 [REVIEW-RECORDS](../../REVIEW-RECORDS/README.md)：

| 名称 | 历史声称 | 当前 provenance | independence | 原始 verdict |
|---|---|---|---|---|
| Heisenberg | 治理测试/CI 子任务，reviewer verdict 不明确 | producer-reported | not_verified | unavailable |
| Noether | 首轮 reviewer / BLOCK | producer-reported | not_verified | unavailable |
| Linnaeus | 首轮 reviewer / BLOCK | producer-reported | not_verified | unavailable |
| Confucius | 对抗 reviewer / BLOCK | producer-reported | not_verified | unavailable |
| McClintock | final reviewer / WARN | producer-reported | not_verified | unavailable |

这些记录只保存仓库中已有的 Producer 声称，不补写不存在的 agent ID、task/thread ID、scope manifest digest、原始报告或外部不可变定位。旧 handoff 中的 McClintock `WARN` 因此只能称为**历史自报 verdict**，不能再作为已证明独立的当前 verdict。

## PASS/BLOCK 分层

| scope | 当前状态 | 说明 |
|---|---|---|
| 根治理与定向攻击测试 | `pass`（本地机械范围） | governance 53/53、known_gaps=0；G2 29/29、G3 19/19、G5 43/43 |
| 索引、日志、链接与文档 ID | `pass`（本地机械范围） | 当前 validator 已通过；最终精确计数以本日日志 EVT-20260729-0011 和命令输出为准 |
| `website-content-ops` 本地治理与 Adapter | `pass`（本地机械范围） | 子库普通结构 PASS；release governance 10/10；Adapter 131/131；npm audit 0；正式 release 仍 BLOCK |
| AI 对抗复审身份与独立性 | `not_verified` | AI 只读复审可发现本地问题，但无外部 identity/independence attestation，不能构成人工 approval |
| 母库正式发布 | `block` | release/license/approval/clean source/remote qualification 未闭环 |
| `sub-library:website-content-ops` 正式发布 | `block` | license/approval/clean source/remote qualification 与跨部署证据未闭环 |
| course evidence chain | `block` | 缺真实提交、独立评分和完整效果证据 |
| GitHub 服务端资格链 | `needs_tony` | Protected Environment、ruleset、可信 signer 和正式 qualification 未建立 |

## Actionlint 证据口径

历史日志和旧 handoff 曾记录“actionlint v1.7.12 PASS”。本轮没有可用二进制、CI run ID、工具 digest 或保存的完整输出，因此当前只能写为：**历史 Producer 自报 PASS，本轮未复验**。它不得支持本轮 G5 PASS，也不得冒充 GitHub 服务端 qualification。

## 下一位 Reviewer 恢复顺序

1. 先确认任务是继续本地维护，还是要进入正式 qualification；二者证据和权限不同。
2. 本地维护先读 current focus、本日日志和相关 scope validator；只有范围变化时才生成新的 content-bound snapshot，旧 v5 只作历史证据。
3. 每个 finding 必须写 evidence、risk、recommendation、blocking，并给出 `PASS/WARN/BLOCK`；AI Reviewer 不能把本地测试包装为人工 approval。
4. 如需正式 qualification，必须从 clean tracked commit 开始，并补齐许可证、包外 sidecar、可信 signed annotated tag、固定 workflow SHA、Protected Environment/ruleset 和服务端 run。
5. Tony 明确授权前不得 `git add`、commit、tag、push、远程配置或 Release。
