---
title: "Mother Library Private Source Manifest"
description: "私有母库源码仓的范围、数据边界、同步状态，以及与公开子库独立发布之间的关系。"
type: "manifest"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-30"
sources: ["Mother-library and sub-library release architecture decision 2026-07-28", "Publishing and redaction policy"]
related: ["README.md", "CONTEXT.md", "AGENTS.md", "CLAUDE.md", "RELEASE.md", "VERSION.md", "CHANGELOG.md", "sub-libraries/README.md", "sub-libraries/registry.json", "scripts/README.md", "scripts/build-mother-release.mjs", "wiki/00_meta/publishing-and-redaction.md", "wiki/00_meta/release-state-machine.md"]
visibility: "private"
redaction_status: "private-source-reviewed"
repository_status: "private-source"
repository_sync_status: "Ready"
release_status: "BLOCK"
maturity_status: "draft"
verification_status: "evidence-partial"
release_scope: "standalone-mother-library"
package_id: "b2b-export-ai-workbench-mother-library"
package_kind: "private-master-source"
license_status: "restricted"
approval_required: true
approval_status: "pending"
approval_record: "RELEASE-APPROVAL.json (external sidecar)"
tag_namespace: "mother"
tag_prefix: "mother/v"
runtime_applicability: "none"
runtime_contract: null
include: [".gitignore", ".github/**", "README.md", "CONTEXT.md", "AGENTS.md", "CLAUDE.md", "MANIFEST.md", "RELEASE.md", "VERSION.md", "CHANGELOG.md", "LICENSE.md", "REVIEW-RECORDS/**", "wiki/**", "sub-libraries/**", "scripts/**", "raw/index.md", "raw/00_inbox/index.md", "raw/10_conversations/index.md", "raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md", "raw/20_web/index.md", "raw/30_documents/index.md", "raw/40_media/index.md", "raw/50_exports/index.md", "raw/90_archive/index.md", "raw/_templates/index.md", "raw/_templates/conversation-source.md"]
exclude: [".git/**", ".obsidian/**", "node_modules/**", "dist/**", "customer-runtime/**", "credentials/**", "raw/**", ".env*", "*.secret", "*.credentials", "*.sqlite*", "*.db", "*.p12", "*.pfx", "*.crt", "*.token", "*.cookie", "*.key", "*.pem", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.mp4", "*.mov", "*.mp3", "*.wav"]
raw_fixture_digests: ["raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md=3adeb6144f626ea99eb5a8bcf74518016dd4000464806f11438029fea4331180"]
---
# Mother Library Manifest

## 当前交付判断

本仓库是私有 canonical monorepo 母库源码，不是客户运行区，也不是把所有子库自动批准后的产品包。母库可以携带注册表中标记为 `source-only` 的公开子库源码快照，但这只表示源码分发，不授予任何子库独立发布资格；真实客户资料、账号、凭据、运行日志和私有 raw 必须在仓库外维护。

`repository_sync_status: Ready` 只允许把当前源码同步到私有 canonical 仓。`release_status: BLOCK` 继续阻止把整个母库当作公开或稳定发行物；结构完整也不代表子库已稳定。

## 母库包包含

- 根入口、协作规则、AI 路由和发布治理；
- `wiki/` 中的公开方法、来源索引、概念、playbook、业务模型、渠道模块、指标和输出模板；
- `sub-libraries/` 中明确标记为 `source-only` 的公开子库源码快照及其注册信息；这些源码随母库分发，但不继承母库的 approval 或 release qualification；
- 明确标注的虚拟示例、去敏验证结论和可复用模板；
- 仅经 manifest 路径 allowlist、builder allowlist 和 `raw_fixture_digests` 内容摘要三重绑定的公开安全 synthetic fixture；
- 母库版本、变更记录、manifest、release guide 和静态检查脚本。

## 母库包排除

- `raw/` 中任何真实客户、账号、课程原文、经营资料或未授权原始资料；公开发布包默认只包含 raw 的分类 index、模板和边界说明；只有 manifest 与构建脚本同时显式 allowlist 的公开安全 synthetic fixture 才可包含。
- 客户私有运行区、Cookie、Token、密码、API key、完整配置和后台导出；
- `.git/`、`.obsidian/`、本机工作区状态和本地绝对路径；
- 未授权第三方课程、截图、图片、录音、PDF、表格和大段原文；
- 任何未标明为虚拟或已去敏的客户案例与指标；
- 只属于某个子库 release 的内部证据、临时日志和私有 adapter 状态。

## 与子库的关系

- 母库发布不等于所有子库均可发布；
- 子库发布不需要把母库一起打包；
- `sub-libraries/registry.json` 是机器可读唯一注册表；`sub-libraries/README.md` 是人类入口和展示页；每个子库的 `MANIFEST.md` 是自己的发布合同；
- 母库候选包可复制 registry 标记为 `source-only` 的子库公开源码及其执行合同快照，但该副本只用于 monorepo 源码分发；母库的 Ready/Published/approval 不得替代子库自己的 qualification；
- 子库如果依赖母库规则，必须在自己的 manifest 中声明依赖，且不能依赖母库私有路径。

## 对外发行阻断

1. 私有同步不授予母库公开再分发许可；正式 public export 仍需单独许可证和第三方来源闭环；
2. 正式 Stable qualification 尚无完整真人 approval、signed tag、受保护 workflow 和远端证据；
3. `website-content-ops` 仅为 Preview，不能被母库入口包装成 Stable；
4. 任何正式候选必须来自 clean tagged commit；
5. 即使远程为 Private，也必须继续禁止凭据、真实客户运行数据和未授权原文进入 Git。

## 检查入口

```bash
node scripts/validate-mother-library.mjs
node scripts/validate-mother-library.mjs --release
```

普通检查验证结构和发布边界；`--release` 只有在本 manifest 已明确为 `Ready` 或 `Published` 时才允许通过。
