---
title: "Website Content Operations Release Guide"
description: "把子库源码包变成可审查 release candidate 的最小发布流程和阻断条件。"
type: "release-guide"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-01"
sources: ["Sub-library contract", "Publishing and redaction policy", "Repository structure adversarial upgrade 2026-07-28"]
related: ["README.md", "MANIFEST.md", "VERSION.md", "CHANGELOG.md", "QA-CHECKLIST.md", "scripts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
state_source: "MANIFEST.md"
state_projection: ["release_status", "preview_publication_status"]
release_status: "BLOCK"
preview_publication_status: "BLOCK"
---
# Release Guide

## 当前边界

既有 `v0.3.2-preview.1` 已以 **Public Preview** 独立发布；当前目录的新增源码候选因 publication clearance pending，`preview_publication_status` 与 `release_status` 均为 `BLOCK`。既有公开仓事实不等于当前候选获准重新发布，也不等于跨环境稳定、生产可用或正式 qualification。

## Preview 发布流程

1. 使用 manifest allowlist 构建独立 artifact；
2. 对 artifact 重新运行结构、链接、敏感信息和当前 trusted profile 固定四文件的 158 项 Adapter 测试；
3. 确认 `LICENSE`、`NOTICE` 和 `THIRD-PARTY-NOTICES.md` 已包含；
4. 从独立 clean Git 历史推送到公开仓；
5. 保留 `VERSION.md` 的 legacy `Version` 与 `historical_published_version` / `historical_published_tag`，它们只描述 immutable historical published identity；为新的 future prerelease 仅分配新的 `current_candidate_identity`、非 dirty 的 `current_candidate_snapshot` 和非空 `current_candidate_version`。tag、approval、evidence 与 prepared candidate path 全部绑定新的 `current_candidate_version`，不得把 legacy `Version` 当作 current candidate version；新版本不得与历史 version/tag 碰撞。不得复用、移动、覆盖或重指向任何历史 tag（包括 `v0.3.2-preview.1`）；目标 tag 已存在但不精确绑定本次候选时立即 `BLOCK`；
6. 从 GitHub 重新 clone 验收；
7. README 始终保留 Preview、先单样本和生产动作需批准的说明。

Preview 不使用 Stable 的 `Ready / Published` 口径，也不伪造正式 approval 或 signed-tag qualification。

## 推荐流程

1. 在子库根目录运行 `node scripts/validate-sub-library.mjs`，确认结构健康。
2. 读取 `MANIFEST.md`、`QA-CHECKLIST.md` 和本文件，确认本次 release 的范围、版本和去敏边界；所有 `REFERENCES/SRC-*.md` 无条件视为 source card，必须保留 `type: source-note`，并显式填写合法的 `publication_review_status`、`publication_status`、`license_status`；prepare / approval / qualification 只有在三项分别为 `approved`、`PASS`、`cleared` 时才放行。改名为非 `SRC-*.md`、移出 `REFERENCES/`、改变 type、删除 marker/字段或只把包级 `license_status` 改为 `cleared` 均须 fail closed。
3. 普通检查只从子库目录构建 latest-only working-tree 候选包，不把母库 `wiki/`、`raw/`、客户私有运行区和 `.obsidian/` 带入。
4. 对候选包重新运行同一检查，并人工检查品牌、许可、联系方式、虚拟示例和第三方素材。
5. 正式 qualification 必须从 clean tagged commit 运行 `build-release.mjs --prepare`，冻结 `dist/prepared/v<current_candidate_version>/<content_digest>/` 下的 `prepared-unapproved` 候选；builder 不接收 approval/evidence。prepare validator 会直接读取 source-level frontmatter，存在未 clearance 的参与来源即 fail closed。随后对同一目录运行 `validate-artifact.mjs --release`，approval validator 必须再次直接读取 frozen candidate 内的来源 frontmatter，不得只信任 `MANIFEST.json.license_status`；从候选包外提供目标子库自己的 `RELEASE-EVIDENCE.json` 与 `RELEASE-APPROVAL.json`，并由外部受保护 workflow 注入实际 annotated tag object SHA、已验证 signer fingerprint、canonical annotation 原始字节及其 SHA-256、canonical approval-binding SHA-256，逐文件绑定 repository-relative commit provenance；母库 evidence 或 approval 不得复用。`runtime-tests` 必须绑定固定四文件 test plan（媒体 45、正文图片 52、正文格式 13、文章生命周期与 taxonomy 48）与精确 `158 passed / 0 failed / 0 skipped`；旧 `120/120`、`131/131`、`136/136`、`145/145`、已过时的 `156/156`，以及 `157/157`、`159/159`、partial、fail、skip、reordered plan 或任意其他计数/计划漂移都不具备 qualification 资格。
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
