---
title: "Website Content Operations Release Guide"
description: "把子库源码包变成可审查 release candidate 的最小发布流程和阻断条件。"
type: "release-guide"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["Sub-library contract", "Publishing and redaction policy", "Repository structure adversarial upgrade 2026-07-28"]
related: ["README.md", "MANIFEST.md", "VERSION.md", "CHANGELOG.md", "QA-CHECKLIST.md", "scripts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
release_status: "Preview"
---
# Release Guide

## 当前边界

当前目录已经以 **Public Preview** 独立发布，`preview_publication_status: Published` 只表示公开 Preview 仓和对应版本已可获取。`release_status: Preview` 不等于 Stable；不要把本地检查、公开仓或 prerelease 写成跨环境稳定、生产可用或正式 qualification。

## Preview 发布流程

1. 使用 manifest allowlist 构建独立 artifact；
2. 对 artifact 重新运行结构、链接、敏感信息和 131 项 Adapter 测试；
3. 确认 `LICENSE`、`NOTICE` 和 `THIRD-PARTY-NOTICES.md` 已包含；
4. 从独立 clean Git 历史推送到公开仓；
5. 创建 `v0.3.2-preview.1` prerelease；
6. 从 GitHub 重新 clone 验收；
7. README 始终保留 Preview、先单样本和生产动作需批准的说明。

Preview 不使用 Stable 的 `Ready / Published` 口径，也不伪造正式 approval 或 signed-tag qualification。

## 推荐流程

1. 在子库根目录运行 `node scripts/validate-sub-library.mjs`，确认结构健康。
2. 读取 `MANIFEST.md`、`QA-CHECKLIST.md` 和本文件，确认本次 release 的范围、版本和去敏边界。
3. 普通检查只从子库目录构建 latest-only working-tree 候选包，不把母库 `wiki/`、`raw/`、客户私有运行区和 `.obsidian/` 带入。
4. 对候选包重新运行同一检查，并人工检查品牌、许可、联系方式、虚拟示例和第三方素材。
5. 正式 qualification 必须从 clean tagged commit 运行 `build-release.mjs --prepare`，冻结 `dist/prepared/v<version>/<content_digest>/` 下的 `prepared-unapproved` 候选；builder 不接收 approval/evidence。随后对同一目录运行 `validate-artifact.mjs --release`，从候选包外提供目标子库自己的 `RELEASE-EVIDENCE.json` 与 `RELEASE-APPROVAL.json`，并由外部受保护 workflow 注入实际 annotated tag object SHA、已验证 signer fingerprint、canonical annotation 原始字节及其 SHA-256、canonical approval-binding SHA-256，逐文件绑定 repository-relative commit provenance；母库 evidence 或 approval 不得复用。`runtime-tests` 必须绑定固定三文件 test plan 与精确 `131 passed / 0 failed / 0 skipped`，旧 `120/120` 或任意计数/计划漂移都不具备 qualification 资格。
6. Preview 仓发布后回写 `preview_publication_status: Published`；只有真实单样本、迁移练习、安装/读取、失败恢复、真实人工批准和远程保护均闭合后，才可进入 Stable 的 `Ready` 或 `Published` qualification。

## Qualification 成功语义

正式 `--release` 必须显式注入以下由候选包外 workflow 取得的值：

- `RELEASE_ACTUAL_TAG_OBJECT_SHA`；
- `RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT`；
- `RELEASE_ACTUAL_TAG_ANNOTATION_SHA256`；
- `RELEASE_ACTUAL_TAG_ANNOTATION_BASE64`；
- `RELEASE_ACTUAL_APPROVAL_BINDING_SHA256`。

validator 会把这些值与 approval/evidence、精确候选、Git annotated tag object、`git verify-tag --raw` 的 `VALIDSIG` fingerprint 和单行 canonical annotation bytes 逐项精确比对。`APPROVAL_RECORD_PASS` 仅证明记录结构与候选/tag/workflow 注入绑定；`ARTIFACT_QUALIFICATION_RECORD_PASS` 仅再证明 frozen candidate 在 qualification 前后未改变。两者均不证明 approver 是真人、reviewer 独立、signer 属于远程 trusted allowlist、Protected Environment/ruleset 已生效、workflow 来源可信、已发布或达到 `Published`。这些信任必须由母库外部固定 workflow 与远程保护另行建立。

## 当前明确不支持的声明

- 不声明跨 AI、跨操作系统、跨 AllinCMS 部署稳定；
- 不声明当前观察型内部接口是官方公开 API；
- 不声明仅有 `SKILL.md` 就可以自动安装；
- 不把草稿、日志或本地验证文件当作客户运行数据模板中的真实证据。

## Release candidate 最小证据

- 结构检查通过；
- 所有活动链接和入口可解析；
- 无真实凭据、本地绝对路径和未授权数据；
- 人类文档包、AI 适配器和工具包的交付形态已分别标注；
- 至少一个完整单样本闭环和一个第二工具/相邻任务迁移闭环；
- 安装或复制后，另一位使用者能从 `README.md` 找到入口并复现最小流程；
- 失败、回滚、写回和下架条件已经记录；
- 正式候选另有 scope-bound evidence bundle、真实人工 approval sidecar、clean commit provenance、可信签名 tag、候选归档 checksum，以及候选包外的 `qualified-not-published` qualification attestation；远程 workflow 证据仍须实际产生和保存。

Preview 发布清单未满足时保持 `preview_publication_status: Ready` 或回退为 `BLOCK`；Stable 证据未满足时始终保持 Stable `BLOCK`，不要用版本号或测试数量掩盖证据缺口。
