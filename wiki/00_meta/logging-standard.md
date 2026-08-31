---
title: "Logging Standard"
description: "规定运行日志的 v2 事件、独立 legacy digest baseline、真实证据引用、correction closure 与 fail-closed 校验；同时明确机械结构通过不证明事实、身份或正式批准。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-31"
sources: ["Tony structure upgrade decision 2026-07-28", "G5 adversarial remediation 2026-07-29"]
related: ["logs/index.md", "logs/_templates/daily-log.md", "logs/_templates/monthly-summary.md", "agent-handoff.md", "definition-of-done.md", "open-questions.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要记录变更、验证、失败、审批、更正、回滚，或判断某条日志能否作为 release/handoff 资格证据时。"
keywords: ["日志", "legacy digest baseline", "evidence refs", "correction closure", "event digest", "release evidence", "daily log"]
---
# Logging Standard

## 目录与 canonical 边界

```text
wiki/00_meta/logs/
├── index.md
├── YYYY/YYYY-MM/YYYY-MM-DD.md
├── YYYY/YYYY-MM/YYYY-MM-summary.md
└── _templates/

scripts/log-legacy-digest-baseline.json
```

默认一天一个文件并持续追加。`conversation-log.md`、`decision-log.md`、`ingestion-log.md` 是 historical/non-canonical 兼容入口：新原始对话进入 `raw/10_conversations/`，新事件进入 daily log，稳定结论进入 durable wiki page。

## Append-only 与事实边界

- 已存在事件正文不得静默改写；发现错误时追加新的 correction event。
- correction event 使用新 event ID，`correction_of` 只能指向已经出现且时间不晚于当前 correction 的事件。自环、forward reference、互环、任意长度环都会阻断。
- 同一事件不能同时出现两个直接 correction；第二次更正必须指向上一条 correction，形成唯一链，避免产生两个互相竞争的“当前事实”。
- Git 未跟踪文件无法证明历史 append-only。v2 `event_digest` 只能证明当前事件卡和其摘要一致；legacy baseline 只能冻结已登记旧卡的当前 canonical bytes。
- `LOG_VALIDATION_PASS` 只代表结构和完整性检查通过。validator 固定输出 `LOG_FACTUAL_VERDICT: not_verified`；它不证明自然语言事实、Reviewer 身份、组织独立性、远程证据存在或人工批准。

## v2 事件合同

新事件使用 `EVT-YYYYMMDD-####`，日期与 daily-log 路径一致，并显式包含：

```markdown
### EVT-YYYYMMDD-#### — 一句话标题

- **occurred_at**：2026-07-29T21:40:00+08:00
- **recorded_at**：2026-07-29T21:41:00+08:00
- **actor**：
- **scope**：mother-library | sub-library:<id> | private-runtime:<id>
- **action**：
- **evidence**：给人看的证据摘要，不等于资格证据 bundle
- **evidence_summary_digest**：sha256:<evidence 字段 UTF-8 trim 值的 SHA-256>
- **evidence_role**：summary-only | qualification
- **evidence_refs**：<qualification 时为单行 JSON 数组；summary-only 时省略>
- **evidence_bundle_digest**：<qualification 时必填；summary-only 时省略>
- **commands**：
- **files changed**：
- **result**：
- **risk / blocker**：
- **next**：
- **writeback**：
- **correction_of**：none | EVT-YYYYMMDD-####
- **event_digest**：sha256:<canonical event payload 的 SHA-256>
```

时间必须为带显式时区的 ISO 8601。`occurred_at` 不得晚于 validator 当前时间超过五分钟，`recorded_at` 不得早于 `occurred_at`。自然语言 `时间` 只供冻结 legacy 事件读取，新事件不得使用。

### 摘要证据与资格证据必须分层

`evidence_summary_digest` 只绑定 `evidence` 的一句自然语言摘要，不能替代文件、artifact、审查记录或外部 attestation。

- `evidence_role: summary-only`：不得携带 `evidence_refs` 或 `evidence_bundle_digest`，避免把摘要伪装成 qualification evidence。
- `evidence_role: qualification`：`evidence_refs` 至少一项，每项必须恰好包含 `kind`、`locator`、`sha256`；`evidence_bundle_digest` 必须绑定排序规范化后的完整 refs 数组。
- `repository-relative` locator 必须是无 query/fragment、无绝对路径、无反斜杠、无空段和 `.`/`..` 的仓库相对文件；任一路径组件不得是 symlink，validator 读取仓库内真实文件字节并核对 SHA-256。
- `immutable-https` locator 必须是公开 HTTPS，不含凭据、query、fragment、私网/本地主机、dot segment 或 `latest/current/staging`，URL path 必须包含该 ref 的精确 SHA-256。IPv4 私网/loopback/link-local，以及 IPv6 loopback、ULA、link-local、site-local、multicast、documentation range 均 fail closed；validator 会规范化 WHATWG URL 返回的 IPv6 方括号形式后再判断。日志 validator 不下载远程内容，因此只验证 locator/digest 声明形状，不证明远程对象真实存在。

Canonical evidence bundle：每项仅保留 `{kind, locator, sha256}`，按三字段连接后的代码点顺序排序，再对 `JSON.stringify(array)` 的 UTF-8 bytes 计算 SHA-256。不得使用 locale-dependent 排序。

`event_digest` 的 canonical payload 按 validator 固定字段顺序构造。为冻结 `EVT-20260729-0009/0010`，canonical JSON 内摘要属性名暂时保留历史键 `evidence_digest`，其值来自 Markdown 字段 `evidence_summary_digest`；新 Markdown 事件仍必须使用新字段名。摘要不包含 `event_digest` 自身。

## 空日志

Daily log 不能只是模板或空壳。`no_events` 的语义锚定是"本页没有 `EVT-` 事件卡"，而非"当天没有发生任何事"：确实没有事件卡时，front matter 必须同时声明：

```yaml
no_events: true
no_events_reason: "当天仅做只读观察，未发生需要记录的仓库或外部状态变化。"
```

出现 `EVT-` 事件卡的日志不得声明 `no_events: true`，也不得保留孤立的 `no_events_reason`。`none`、`n/a`、`todo`、`tbd` 不是有效理由。记录了实际治理工作但不使用事件卡的日志，适用下方"叙述式治理日志"豁免。

## 叙述式治理日志（2026-08-31 起）

治理批按日日志允许以叙述小节（`##` 标题 + bullet）记录当批执行与证据指针，并声明 `no_events: true` + `no_events_reason: "治理批叙述性日志"`，前提是：

- 全文不得出现 `EVT-` 事件卡标题；一旦需要 digest 级防伪证据，必须转正式 v2 事件卡并移除 `no_events` 声明。
- 叙述小节只承载执行留痕与 durable 指针（commit、run、OQ/CQ ID）；叙述行不受 `event_digest` 防伪保护、不构成资格证据，canonical 状态变更仍必须落 OQ/CQ/CHANGELOG/current-focus。
- front matter 必须通过 7 步校验与模板泄漏闸（未求值生成占位符 FAIL）。

该豁免不降低事件卡合同：凡涉及发布资格、凭据或跨客户边界的证据，仍必须使用 v2 事件卡。

## 字段唯一性与 alias

每张事件卡中一个 canonical 字段只能出现一次。`risk`/`risk / blocker`、`commands`/`command`、`files changed`/`files_changed`、`occurred_at`/`time`/`时间`、`writeback`/`写回` 等 alias 同时出现也会被拒绝。

`evidence_digest` 已冻结为历史 alias，只允许以下两张既有 v2 卡继续使用，避免修改当日日志正文及其 event digest：

- `wiki/00_meta/logs/2026/07/2026-07-29.md#EVT-20260729-0009`
- `wiki/00_meta/logs/2026/07/2026-07-29.md#EVT-20260729-0010`

其他新事件使用 `evidence_digest` 必须失败。

## Legacy 逐事件冻结 baseline

2026-07-29 引入 v2 前的事件正文不为补字段而改写。精确 cutoff 为：

- `2026-07-28.md`：截至 `EVT-20260728-0017`；
- `2026-07-29.md`：截至 `EVT-20260729-0008`。

每张 legacy 卡的 canonical bytes 为：heading 加完整卡正文、换行统一 LF、移除每行尾部空白、移除卡尾空行。其逐事件 SHA-256 存在独立文件 `scripts/log-legacy-digest-baseline.json`，不写回日志正文。

治理约束有三层：

1. daily log front matter 的 `legacy_event_cutoff` 必须与 validator allowlist 精确一致；
2. baseline 内 `cutoffs`、每个 `{path,event_id,sha256}`、唯一性和 `entries_digest` 必须通过校验；
3. baseline 文件自身 SHA-256 固定在 `scripts/validate-logs.mjs`。baseline 任意字节变化都会先失败，除非治理代码同步显式更新 pin 并重新接受对抗审查。

`--release` 下，baseline 事件缺失、旧卡 digest 改变、未登记 legacy 事件、baseline 缺项/重复/自摘要不符均 fail-closed。普通模式只把日志与已验证 baseline 的历史不一致降为 warning；baseline 文件或 schema 本身损坏始终失败。

## Correction closure

```bash
node scripts/validate-logs.mjs --release --closure-json
```

该命令额外输出一行 `CORRECTION_CLOSURE_JSON:<json>`：

- `effective[]`：当前未被更正的事件及其完整 `supersedes` 列表；
- `superseded[]`：每个旧事件到最终 `effective_event_id` 的解析结果。

这只是机器可用的结构视图。原事件写 `PASS`、后续 correction 写 `BLOCK` 时，closure 会把最终事件标为 effective，但 validator 不理解自然语言 verdict 的真实性，也不会把结构 PASS 升格为事实 PASS。

## Validator 模式

```bash
node scripts/validate-logs.mjs
node scripts/validate-logs.mjs --release
node scripts/validate-logs.mjs --release --closure-json
```

两种模式都会拒绝空日志无理由、canonical 字段重复、未来时间、重复 event ID、correction 图错误、v2 缺字段、摘要不匹配、无效证据 ref 或 bundle digest 不匹配。`--release` 还会把 warning 和 legacy baseline 漂移作为阻断。

validator 扫描 `wiki/00_meta/logs/YYYY/MM/YYYY-MM-DD.md` 以及合法的 `YYYY-MM-DD--<scope>.md` scope shard；shard 文件名必须符合约定，事件 `scope` 必须与文件名绑定。形似 shard 但命名错误的文件会阻断。validator 不扫描月摘要、index、模板或冻结 legacy 汇总页。

## 月摘要、拆分与保留

月度未结束时声明 `summary_mode: "month-to-date"` 和带时区的 `as_of`；月末冻结时改为 `summary_mode: "final"`。稳定结论写回 durable pages，真正未决项写回 `open-questions.md`。

| 情况 | 做法 |
|---|---|
| 当天少于约 200 条事件 | 一个日文件持续追加 |
| 超过约 200 条或多个 scope 高并发 | 使用 `YYYY-MM-DD--<scope>.md` 按 scope 拆分；文件名 scope 与卡片 `scope` 精确一致，并保留全局唯一 event ID |
| 月末或阶段完成 | 生成摘要，提炼稳定结论、关闭事项和未决风险 |
| 涉及私有数据 | 只写脱敏证据指针，不复制客户原话、账号或凭据 |

## 验收

```bash
node --check scripts/validate-logs.mjs
node scripts/tests/validate-logs-g5.mjs
node scripts/validate-logs.mjs
node scripts/validate-logs.mjs --release
node scripts/validate-logs.mjs --release --closure-json
```
