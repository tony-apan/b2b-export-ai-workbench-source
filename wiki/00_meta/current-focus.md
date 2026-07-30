---
title: "Current Focus"
description: "给人和 AI 提供一到两屏的当前唯一焦点、已证实状态、现存阻断、下一动作与证据入口；历史过程已移入月度历史页。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-30"
sources: ["Tony conversation 2026-07-26", "Tony decisions 2026-07-27", "Local repository evidence 2026-07-29", "Tony publication authorization 2026-07-30", "GitHub remote verification 2026-07-30"]
related: ["current-focus-history-2026-07.md", "check-mechanism-map.md", "open-questions.md", "../../MANIFEST.md", "../../sub-libraries/website-content-ops/README.md", "logs/2026/07/2026-07-30.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 当前焦点

## Current Focus

**Website Content Operations** 已完成入口、独立仓与 Public Preview 发布闭环：`README.md` 给业务人员和新手看，`START-HERE.md` 给具备文件、浏览器或脚本能力的 AI agent 执行。新的私有母库 `b2b-export-ai-workbench-source` 与公开子库 `website-content-ops` 均采用新仓非覆盖发布；旧公开仓和旧私有仓只保留历史，未 force push、未改写原有 `main`。

子库入口：[README](../../sub-libraries/website-content-ops/README.md) → [START-HERE](../../sub-libraries/website-content-ops/START-HERE.md)。

## Current State

**母库私有同步：`Synced / remote CI PASS`；子库 Public Preview：`Published with WARN`；母库公开/Stable、子库 Stable 与真实效果：`BLOCK`。** 独立 reviewer 先发现 Node.js 20 文档 ID 兼容和母库 artifact 扩展名 allowlist 两个真实 BLOCK；修复后 GitHub Actions Run `30520244121` 在提交 `f0550f28f3cf968554852999d8848ea5509c4c74` 完整通过。公开子库的可见性、tag、prerelease、内容、许可、隐私、131 项测试均通过；仍保留“普通 clone 根目录不是纯 artifact”和“私有 upstream commit 不能由公开用户解析”两个非阻断 WARN。远端验收只证明当前私有同步和公开 Preview，不把任何 scope 升格为 Stable 或 production-ready。

## 已验证事实

- 私有母库仓为 `tony-apan/b2b-export-ai-workbench-source`，默认分支 `main`，GitHub 可见性为 `PRIVATE`；[母库 manifest](../../MANIFEST.md) 保持 `repository_sync_status: Synced`、`release_status: BLOCK`、`license_status: restricted`。
- 公开子库仓为 `tony-apan/website-content-ops`，默认分支 `main`，GitHub 可见性为 `PUBLIC`；`v0.3.2-preview.1` 指向发布提交并以非 Draft 的 prerelease 公开。
- 子库 manifest 为 `release_status: Preview`、`preview_publication_status: Published`、`license_status: cleared`、`approval_status: pending`；只表示 Public Preview 已公开，不放行 Stable。
- 从远端 clean clone 与 GitHub Node.js 20 CI 复验：母库文档 ID、治理攻击 53/53、母库/子库构建与 artifact、知识链和 Adapter workflow 全部通过；子库独立 archive 校验通过，AllinCMS Adapter 131/131，`npm audit --omit=dev` 为 0 vulnerabilities。
- 直接对普通 Git clone 根目录运行 artifact validator 会因 `.git/` 不是发布 allowlist 内容而失败；正确对象是 builder 产物或 `git archive` 导出的纯发布树。该失败证明 validator 没有静默忽略额外文件，不是公开仓内容泄漏；公开 clone 验收说明仍可在后续 Preview 改善。
- 子库 artifact 的逐文件 SHA-256 和公开 release commit 可验证，但 `source_commit` 指向私有母库，公开用户不能解析该 upstream Git object；当前作为 Preview provenance WARN 记录，不冒充公开可重建的完整来源链。
- 当前 `origin` 指向新的私有 canonical 母库；旧公开仓和旧私有仓分别保留为 `legacy-public`、`legacy-private`，发布后 `main` HEAD 仍为发布前基线。公开子库来自独立 artifact 和独立 Git 历史，不是把母库根目录推到公开仓。
- 母库与子库分别使用独立 manifest、builder、validator、approval/evidence 与 tag namespace；一个 scope 的结论不可替代另一个 scope。
- `raw/`、课程和日志已有独立入口与验证规则；真实客户、凭据和经营数据不得进入公开子库，也不得把 private Git 仓误当客户运行区。
- 子库不自动等于 Skill；当前 `SKILL.md` 是 Preview 条件入口，不是一键安装或跨平台稳定 Skill。

## Current BLOCK

- 母库对外发行许可证仍为 restricted；子库 Preview 已采用 Apache-2.0，但 Stable 所需的候选包外批准、真实批准者身份、可信 signer、远端 Protected Environment/ruleset 和正式服务端 run 尚未形成完整外部证据链。
- `APPROVAL_RECORD_PASS` 只能证明记录结构与候选绑定，不能单靠名称字段证明真人身份。
- 课程仍缺真实学员提交与独立 reviewer 的效果证据，不能宣称稳定课程交付。
- AllinCMS 的限定本地/当前部署证据不得外推到任意站点、任意批次、远程恢复或未来稳定性。

## Next Action

1. Public Preview 后续更新只允许从新的 clean 子库候选生成新版本与新 tag；不得移动或覆盖 `v0.3.2-preview.1`。下一 Preview 应补充 clone→archive 验证命令，并区分私有 upstream commit、公开 release commit 与公开可解析性。
2. 母库后续只同步到新的私有 canonical 仓；旧公开/私有仓继续作为只读历史边界，不 force push、不覆盖。
3. 收集真实新手冷启动、跨部署和失败恢复证据；涉及远程 CMS mutation 时继续逐次获得明确授权。
4. 外部固定 workflow SHA、Protected Environment/ruleset、可信签名 annotated tag、包外 approval/evidence、课程真实提交和跨部署证据未齐备前，母库公开/Stable、子库 Stable 和课程 release 继续 `BLOCK`。
