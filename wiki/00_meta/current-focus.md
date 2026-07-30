---
title: "Current Focus"
description: "给人和 AI 提供一到两屏的当前唯一焦点、已证实状态、现存阻断、下一动作与证据入口；历史过程已移入月度历史页。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-30"
sources: ["Tony conversation 2026-07-26", "Tony decisions 2026-07-27", "Local repository evidence 2026-07-29", "Tony human README and AI START-HERE decision 2026-07-30"]
related: ["current-focus-history-2026-07.md", "check-mechanism-map.md", "open-questions.md", "../../MANIFEST.md", "../../sub-libraries/website-content-ops/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 当前焦点

## Current Focus

**Website Content Operations** 已明确入口分工：`README.md` 给业务人员和新手看，`START-HERE.md` 给具备文件、浏览器或脚本能力的 AI agent 执行。新的私有母库 `b2b-export-ai-workbench-source` 与公开子库 `website-content-ops` 已完成非覆盖建仓和首次推送；当前只剩把最终 Published 状态同步到公开子库、创建 `v0.3.2-preview.1` prerelease，并从两个远端重克隆验收。旧公开仓和旧私有仓只保留历史，不覆盖、不 force push。

子库入口：[README](../../sub-libraries/website-content-ops/README.md) → [START-HERE](../../sub-libraries/website-content-ops/START-HERE.md)。

## Current State

**母库私有同步：`Synced`；子库 Public Preview：`Published`；Stable 与真实效果：`BLOCK`。** 母库结构、分层索引、日志、文档 ID、模板、raw 对话、课程结构链、子库合同、发布治理和 AllinCMS Adapter 已通过当前本地机械验证；两个新远端已创建并完成非覆盖首次推送。最终 prerelease 与远端重克隆仍是本次发布任务的验收动作，不会把 Preview 升格为 Stable。

## 已验证的本地事实

- [母库 manifest](../../MANIFEST.md) 为 `visibility: private`、`repository_sync_status: Synced`、`release_status: BLOCK`、`license_status: restricted`；私有 canonical 源码已经同步，不放行母库公开/Stable 发行。
- 子库 manifest 为 `release_status: Preview`、`preview_publication_status: Published`、`license_status: cleared`、`approval_status: pending`；只表示 Public Preview 已公开，不放行 Stable。
- 母库治理攻击当前为 53/53；子库 release governance 为 10/10；独立 artifact 为 116 files / 115 checksum entries；AllinCMS Adapter 为 131/131，`npm audit --omit=dev` 为 0 vulnerabilities。
- 母库与子库分别使用独立 manifest、builder、validator、approval/evidence 与 tag namespace；一个 scope 的结论不可替代另一个 scope。
- 分层 index 只收录当前目录直接文件与直接子目录 canonical 入口；redirect legacy 页不与 ID canonical 同权。
- `raw/`、课程和日志已有独立入口与验证规则；真实客户、凭据和经营数据不得进入公开子库，也不得把 private Git 仓误当客户运行区。
- 子库不自动等于 Skill；当前 `SKILL.md` 只是 `preview-adapter-not-installable` 条件入口，不是一键安装或跨平台稳定 Skill。
- 当前 `origin` 指向新的私有 canonical 母库；旧公开仓和旧私有仓已分别保留为 `legacy-public`、`legacy-private`，发布前后 HEAD 均未变化。公开子库来自独立 artifact 和独立 Git 历史，不是把母库根目录推到公开仓。

## Current BLOCK

- 母库对外发行许可证仍为 restricted；子库 Preview 已采用 Apache-2.0，但 Stable 所需的候选包外批准、真实批准者身份、可信 signer、远端 Protected Environment/ruleset 和正式服务端 run 尚未形成完整外部证据链。
- `APPROVAL_RECORD_PASS` 只能证明记录结构与候选绑定，不能单靠名称字段证明真人身份。
- 课程仍缺真实学员提交与独立 reviewer 的效果证据，不能宣称稳定课程交付。
- AllinCMS 的限定本地/当前部署证据不得外推到任意站点、任意批次、远程恢复或未来稳定性。

## Next Action

1. 从当前 clean source commit 重建最终子库 artifact，把 `Published` 状态 fast-forward 同步到公开子库。
2. 创建 `v0.3.2-preview.1` GitHub prerelease；如果同名 tag 已存在则停止并升级 preview 序号，绝不覆盖。
3. 从私有母库和公开子库远端重新 clone，核对可见性、commit、tag、prerelease、artifact、131 项 Adapter 测试和依赖审计，并把 exact evidence 写入当日日志。
4. 外部固定 workflow SHA、Protected Environment/ruleset、可信签名 annotated tag、包外 approval/evidence、课程真实提交和跨部署证据未齐备前，母库公开/Stable、子库 Stable 和课程 release 继续 `BLOCK`。
