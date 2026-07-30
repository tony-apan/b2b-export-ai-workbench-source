---
title: "Monthly Operations Summary 2026-07"
description: "截至 2026-07-30 的 7 月滚动摘要，加入人类 README、AI START-HERE 和无账号联系入口结论，并区分已闭合的结构机制与仍阻断的正式发布/课程证据。"
type: "log-summary"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-30"
summary_mode: "month-to-date"
as_of: "2026-07-30T12:53:34+08:00"
sources: ["2026-07-28.md", "2026-07-29.md", "2026-07-30.md", "../../../current-focus.md", "../../../open-questions.md"]
related: ["../../index.md", "../index.md", "../../../decision-log.md", "../../../../../README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要快速恢复 2026 年 7 月截至 7 月 30 日的人类/AI 入口、稳定结论、已关闭事项和真实阻断时。"
keywords: ["2026-07", "month-to-date", "structure governance", "raw to course", "release block", "review evidence", "legacy migration"]
---
# Monthly Operations Summary — 2026-07

> **month-to-date**，证据截止 `2026-07-30T12:53:34+08:00`；不是月末 final summary。

## 稳定结论

- 根目录是逻辑母库，`sub-libraries/` 下子库可独立构建和验证；两个发布闸分开。
- `index.md` 服务人和 AI，只索引当前目录直接入口，不递归复制孙级正文。
- `raw/` 保存事实输入，原始对话进入 `raw/10_conversations/`；提炼结果进入 `wiki/` 或课程模块。
- 日志按日追加；新事件使用 v2 时间、correction 和 digest 字段，旧 conversation/decision/ingestion 日志冻结为 non-canonical。
- 母库/子库 manifest、builder、validator 和本地治理机制已经建立；正式资格固定为 builder `--prepare` 冻结候选、artifact validator `--release` 读取包外 sidecar、再生成包外 attestation 的两阶段流程，但机制存在不等于服务端正式发布资格。
- `website-content-ops/README.md` 面向人并用通俗语言说明价值、最快开始和账号联系；`START-HERE.md` 面向 AI 执行。没有 AllinCMS 账号只阻断远程 CMS 步骤，本地资料整理和模拟小样可继续，但必须标记远程结果未执行。

## 已关闭事项

| closed_id | 结论 | 证据 | 边界 |
|---|---|---|---|
| `CQ-20260728-0001` | synthetic raw → source/concept/playbook/course/exercise/verification/writeback 结构链已跑通 | `EVT-20260728-0007` | 仅结构/虚拟 fixture，不是课程效果证据 |
| `CQ-20260729-0001` | manifest、builder、validator、候选包和敏感边界机制已经实现 | `current-focus.md`、根 `MANIFEST.md`、`scripts/` | 正式 release 仍 BLOCK |
| `CQ-20260729-0002` | 工作树已按 G1–G5 形成分层 review slice；最新预收口 v5 记录 273 个唯一当前路径 | `EVT-20260729-0007`、`EVT-20260729-0008`、`dist/working-tree-review/2026-07-29-v5/` | 本地 bundle 可覆盖，且 handoff/log 写回后会过时；不是不可变 release evidence |
| `CQ-20260729-0003` | 本地治理攻击 53/53、G2 29/29、G3 19/19、G5 43/43、website-content-ops release governance 10/10、Adapter 131/131 与 audit 0 均通过；母库和子库普通结构校验通过 | `EVT-20260729-0010`、`EVT-20260729-0011` | 母库/子库正式 release 与课程 release 仍按预期 BLOCK；本地 PASS 不证明真人批准或生产稳定 |
| `CQ-20260730-0001` | 人类 README、AI START-HERE、无账号微信入口和本地降级路线已对齐；层级 index 与治理回归恢复通过 | `EVT-20260730-0001` | 二维码可达和本地机械 PASS 不证明账号开通、跨部署稳定或正式发布 |

## 未决风险与阻断

- 母库和子库仍缺许可证、clean tracked source、人工批准和 GitHub 服务端 qualification。
- 课程仍缺真实学员提交、评分 reviewer 和完整效果验证。
- 历史五个 reviewer 名称只有 Producer 转述，独立性和原始 verdict 均为 `not_verified`；以 `REVIEW-RECORDS/` 为恢复入口。
- CMS 跨部署、postCreate、远程失败恢复、大于 11 篇长跑和主题 Alt/列表语义仍未闭合。
- 真正未决项只在 `open-questions.md` 维护；本摘要不复制已关闭历史正文。

## 下一步

1. 保持本地机制回归可重复；只有范围变化时才重新生成 content-bound snapshot 并复审，不把 AI 自检写成人工批准。
2. Tony 决定许可证、品牌、批准人和 GitHub 服务端保护后，才从 clean tracked snapshot 进入单 scope qualification。
3. 课程在真实提交、独立评分、exercise/review/verification/writeback 与效果证据完成前保持 release gate `BLOCK`。
