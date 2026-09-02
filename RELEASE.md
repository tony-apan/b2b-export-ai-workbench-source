---
title: "Mother Library Release Guide"
description: "说明母库源码的公开可用边界、子库独立 Preview/Stable Release，以及不同通道之间的证据要求；避免把 Git 同步、公开试用与稳定发布混成同一个闸。"
type: "release-guide"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-09-02"
sources: ["Mother Library Manifest", "Sub-library contract", "Publishing and redaction policy", "Tony public MIT decision 2026-09-02"]
related: ["README.md", "MANIFEST.md", "VERSION.md", "CHANGELOG.md", "AGENTS.md", "scripts/README.md", "sub-libraries/README.md", "wiki/00_meta/release-state-machine.md", "wiki/00_meta/release-checklist.md"]
visibility: "public"
redaction_status: "safe-to-publish"
state_source: "MANIFEST.md"
state_projection: ["repository_sync_status", "release_status"]
repository_sync_status: "Synced"
release_status: "BLOCK"
---
# Mother Library Release Guide

## 不同通道，不能互相冒充

| 通道 | 对象 | 当前允许状态 | 核心要求 | 不证明什么 |
|---|---|---|---|---|
| Source Sync | canonical 母库（公开 Git） | `repository_sync_status: Ready / Synced` | clean commit、基础验证、安全扫描、目标仓确认 | 不代表 Stable / production-ready |
| Public Preview | 独立公开子库或公开预览制品 | `release_status: Preview` | 许可证 cleared、allowlist 拆包、去敏、链接/安装/测试通过、README 显著标注 Preview | 不证明跨部署稳定、生产效果或正式 qualification |
| Stable Release | 母库公开制品或独立子库稳定版 | `Ready / Published` | 完整 approval/evidence、signed annotated tag、受保护 workflow、远端验收 | 不能由本地自评或普通 Git push 替代 |

## Source Sync（当前母库采用）

母库 canonical 仓库是 `tony-apan/b2b-export-ai-workbench-source`（MIT 许可、默认分支 `main`）。仓库可见性以 GitHub 实际设置为准；旧历史仓保留原样，不 force push、不覆盖。

同步前：

1. 读取 `MANIFEST.md` 和当前 Git 状态；
2. 运行索引、链接、日志、文档 ID、治理和安全检查；
3. 确认没有凭据、客户运行数据、机器本地路径或未授权大段原文；
4. 把目标变化形成 clean commit；
5. 只推送到 canonical remote；
6. 从远端重新 clone 并复跑基础验证。

## 母库 release（正式公开导出，当前 BLOCK）

母库内容以 MIT 授权可直接使用；`release_status: BLOCK` 只表示尚未经过正式 Stable qualification（approval/evidence、signed tag、Protected Environment、远端验收），不代表不可读或不可用。

普通构建：

```bash
node scripts/build-mother-release.mjs
node scripts/validate-artifact.mjs dist/mother/latest
```

它只生成 `working-candidate`，用于回归公开边界；不是批准、tag 或发布事实。正式 qualification 仍按 [发布状态机](wiki/00_meta/release-state-machine.md)、[批准与 tag namespace](wiki/00_meta/release-approval-and-tag-namespaces.md) 和 [发布检查清单](wiki/00_meta/release-checklist.md) 执行。

## 子库 release（独立判定）

子库必须使用自己的 `README.md`、`MANIFEST.md`、`RELEASE.md`、builder、validator 和独立仓库。母库 release 或同步都不会替子库完成：

- 许可证与第三方来源审查；
- allowlist 独立拆包；
- Skill/Adapter 本地测试；
- 新手冷启动和真实单样本；
- 正式 approval、tag、Protected Environment、ruleset 和 GitHub Release。

当前 `website-content-ops` 允许以 Public Preview 发布；Stable 仍独立 BLOCK。

## 不得混淆的证据

- clean commit 只证明 Git 快照可追踪；
- GitHub Public 只证明仓库可见性，不证明内容质量；
- checksum、archive 和本地测试只证明候选一致性与局部行为；
- `Preview` 只允许公开试用和单样本；
- `Ready / Published` 必须满足对应 scope 的完整资格，且母库与子库不能共享 PASS。
