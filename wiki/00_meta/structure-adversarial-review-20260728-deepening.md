---
title: "Structure Adversarial Review 20260728 Deepening"
description: "母库/子库状态机、运行合同、registry 防漂移和候选包完整性升级后的独立复审记录。"
type: "audit"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["../../AGENTS.md", "../../MANIFEST.md", "../../sub-libraries/registry.json", "release-state-machine.md", "adversarial-review protocol"]
related: ["structure-adversarial-review-20260728-final.md", "../../scripts/validate-mother-library.mjs", "../../sub-libraries/website-content-ops/scripts/validate-sub-library.mjs", "../../sub-libraries/website-content-ops/RUNTIME-CONTRACT.json", "../../.github/workflows/validate-library.yml"]
visibility: "public"
redaction_status: "safe-to-publish"
release_status: "BLOCK"
---
# 深化对抗复审

## 顶层结论

**BLOCK：结构和候选包闸通过，但母库和子库仍不能正式对外发布，也不能把当前 `SKILL.md` 宣称为稳定可安装 Skill。**

这里的 `BLOCK` 是正式发布闸结果，不否定本轮结构升级已经通过的局部检查。审查区分：结构正确、候选包完整、运行证据、许可证和正式批准。

## 本轮修复后通过项

| 项目 | 证据 | 结论 |
|---|---|---|
| visibility 矛盾 | `wiki/00_meta/private-master-and-sub-library-model.md` 与母库 manifest 均声明 `public` | PASS |
| registry 真源 | `sub-libraries/registry.json` 为 schema 2；`sub-libraries/README.md` 明确是人类入口，不单独维护机器状态 | PASS |
| 状态分层 | 两个 manifest 和 registry 都有 `maturity_status`、`verification_status`、`release_status`、`license_status` | PASS |
| registry 防漂移 | 母库与子库 validator 逐字段比对版本、状态、scope、运行合同、交付形态、入口和母库包含关系 | PASS |
| 运行边界 | `sub-libraries/website-content-ops/RUNTIME-CONTRACT.json` 覆盖输入、输出、权限、副作用、人工审批、回滚和写回 | PASS |
| 候选包边界 | 母库 239 个文件 / 238 条 checksum；子库 89 个文件 / 88 条 checksum；artifact validator 均通过 | PASS |
| 可复现性 | `SOURCE_DATE_EPOCH=0` 连续构建母库和子库，逐文件 `diff -qr` 无差异 | PASS |
| 独立目录复现 | 从 latest 包复制到无母库父目录的临时目录，内嵌 validator 和 artifact validator 均通过 | PASS |
| Adapter 本地证据 | AllinCMS adapter `npm test`：115 passed, 0 failed；`npm audit --omit=dev`：0 vulnerabilities | PASS（仅限当前本地合同） |
| CI 入口 | `.github/workflows/validate-library.yml` 已加入结构、registry、候选包和 adapter 测试流程 | WARN：尚未由远程 CI 实际运行 |

## 仍然阻断正式发布的 finding

### BLOCK-1：许可证和第三方再分发授权仍未闭环

- **Evidence**：母库 `MANIFEST.md` 与子库 `MANIFEST.md` 的 `license_status` 仍为 `pending`；`README.md` 也明确没有最终许可证。
- **Risk**：结构安全不等于获得复制、修改、商业使用、课程素材、图片、截图和第三方来源的再分发权。
- **Recommendation**：由 owner 明确许可证策略，逐项关闭 `wiki/10_sources/license-and-consent-register.md`，清理或替换未授权内容；批准前保持 `BLOCK`。
- **Severity**：S0；**blocks release**：是。

### BLOCK-2：尚无不可变的正式发布链路

- **Evidence**：当前工作树存在未提交变更；没有本轮 source commit → artifact hash → review record → release tag 的不可变链路，也没有执行 push 或正式发布。
- **Risk**：无法证明外部拿到的包就是本次复审的源码快照，后续更新可能出现“文档说的是 A、制品是 B”。
- **Recommendation**：owner 批准后，在干净 checkout 上提交、打 tag、生成并保存 hash、关联复审记录，再发布；当前不要改成 `Ready` 或 `Published`。
- **Severity**：S0；**blocks release**：是。

### BLOCK-3：稳定运行证据仍然不够宽

- **Evidence**：115 项测试是本地 adapter 合同测试；当前 AllinCMS 证据仍限定于特定部署/会话/已观察路线。尚未完成第二环境完整安装、升级、回滚、任意大批量长跑、跨部署和更广泛真实前台主题验证。
- **Risk**：容易把单部署、单会话、单样本或模拟合同外推成跨环境稳定能力，造成错误交付或数据写入风险。
- **Recommendation**：增加独立第二环境、安装/升级/回滚记录，明确部署矩阵和未支持范围；在证据完成前保持 `verification_status: evidence-partial` 与 `release_status: BLOCK`。
- **Severity**：S1；**blocks release**：是。

### BLOCK-4：Skill 仍为草案适配器

- **Evidence**：`sub-libraries/website-content-ops/SKILL.md` 声明 `skill_status: draft-adapter-not-installable`；registry 的 `delivery_modes` 也明确是 `ai-skill-draft`。
- **Risk**：使用者可能只看到 `SKILL.md` 就误以为拿到可安装、跨 AI 稳定 Skill，而忽略宿主规则、权限、人工审批和运行合同。
- **Recommendation**：将 Skill 作为子库的条件性平台适配层；只有独立安装、权限边界、升级/回滚和跨环境证据完成后，才单独把该交付形态改为稳定。
- **Severity**：S1；**blocks stable Skill claim**：是。

## WARN

### WARN-1：CI 尚未得到远程运行证据

工作流已经加入源码包，但当前只有本地验证；未证明 GitHub runner 的 Node 版本、依赖安装和事件触发行为与本地一致。首次 PR/push 仍需观察并记录 run URL / commit SHA。

### WARN-2：README、CLAUDE、AGENTS 是薄入口，不应发展成第二真源

本轮已同步入口和路由，但后续任何状态字段、依赖或发布边界仍应先改 manifest、registry、runtime contract 和 wiki 合同，再更新三份薄入口。validator 目前防 registry 漂移，不防所有自然语言重复描述的语义漂移。

## 复审命令

```bash
node scripts/validate-mother-library.mjs
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
node scripts/build-mother-release.mjs
node sub-libraries/website-content-ops/scripts/build-release.mjs
node scripts/validate-artifact.mjs dist/mother/latest
node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
npm --prefix sub-libraries/website-content-ops/ADAPTERS/cms/allincms test
npm --prefix sub-libraries/website-content-ops/ADAPTERS/cms/allincms audit --omit=dev
```

## 不可误读的状态

```text
STRUCTURE_PASS ≠ release approval
ARTIFACT_PASS ≠ license clearance
115 local tests pass ≠ cross-deployment stability
SKILL.md exists ≠ installable Skill
```

## 2026-07-28 Final Continuation Addendum

本次继续推进不是把 `BLOCK` 改成 `PASS`，而是把发现的结构性漏检补成可失败的闸门，并重新执行正向与负向验证。

### 本轮新增修复

1. **母库/子库边界双向比较**：`scripts/build-mother-release.mjs` 现在对每个注册子库的每个源文件同时计算 child selection 和 mother selection；子库包含而母库排除、或子库排除而母库包含，都会直接失败。此前只在母库已选中文件时比较，存在漏检窗口。
2. **许可证状态显式化**：新增根 `LICENSE.md` 与 `sub-libraries/website-content-ops/LICENSE.md`。两者明确说明当前不是最终许可证，`license_status: pending` 仍然阻断再分发；它们不是“补一个文件就算授权”。
3. **来源审批字段补齐**：`wiki/10_sources/license-and-consent-register.md` 增加 `Approval Owner`、`Evidence / Consent Ref`、`Decision Date`。`needs-approval`、`pending` 或缺审批证据仍不得进入 `Ready/Published`。
4. **CI 可扩展化**：`.github/workflows/validate-library.yml` 的候选包构建和 tag release gate 改为读取 `sub-libraries/registry.json`，不再把 `website-content-ops` 写死为唯一子库；tag 触发时分别执行母库与每个注册子库的 `--release` gate。

### 当前重新验证证据

```text
node scripts/validate-mother-library.mjs
→ STRUCTURE_PASS

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ STRUCTURE_PASS

SOURCE_DATE_EPOCH=0 node scripts/build-mother-release.mjs
→ Version 0.1.1-draft
→ MANIFEST.json files: 239
→ SHA256SUMS entries: 240

SOURCE_DATE_EPOCH=0 node sub-libraries/website-content-ops/scripts/build-release.mjs
→ Version 0.3.2-draft
→ MANIFEST.json files: 87
→ SHA256SUMS entries: 88

node scripts/validate-artifact.mjs dist/mother/latest
→ ARTIFACT_PASS

node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
→ ARTIFACT_PASS

SOURCE_DATE_EPOCH=0 连续构建两次
→ 四个 MANIFEST/SHA256SUMS 文件 hash 无差异

clean artifact copy in a parent-independent temporary directory
→ mother and child structure/artifact validators both PASS

npm test
→ 115 passed, 0 failed

npm audit --omit=dev
→ 0 vulnerabilities
```

### 新增负向证据

```text
临时让母库排除 child 已包含的 START-HERE.md
→ mother build exit 1
→ mother/child release boundary mismatch: child=true mother=false

临时让 child 排除母库仍包含的 START-HERE.md
→ mother build exit 1
→ mother/child release boundary mismatch: child=false mother=true
```

这两项证明边界检查不是只比较两个 manifest 的文本相等，而是会对双向选择结果做语义级失败判断。

### 本轮对抗后仍然 BLOCK 的事项

- 母库和子库的 `license_status` 仍为 `pending`，来源表中的审批 owner、证据引用和决定日期仍未关闭；
- 当前工作树仍是 dirty snapshot，没有 source commit → artifact hash → 独立 review record → release tag 的不可变发布链；
- 仍没有第二环境的真实安装、升级、故障注入、回滚和回滚后复验记录；
- `SKILL.md` 仍为 `draft-adapter-not-installable`，不能叫稳定 Skill；
- GitHub Actions 配置已经加入 tag release gate，但本地没有远程 CI run 证据，不能把 YAML 存在写成 CI 已通过。

**本轮结论：结构防漂移与候选包防漏检继续 PASS；母库正式发布、子库正式发布、稳定 Skill 发布继续 BLOCK。**

### Provenance hardening after continuation review

候选包的 `MANIFEST.json` 现在额外写入并由 artifact validator 验证：

- `source_commit`：生成时的 Git HEAD SHA；
- `source_dirty`：生成时是否存在未提交或未跟踪变更；
- `content_digest`：按排序文件名和逐文件 SHA-256 计算的内容摘要。

当前本地候选包证据为 `source_commit=e54b9f8297bbf9d042543cedc84731111dd3bca6`、`source_dirty=true`。这正是应该保持的结果：候选包可以继续审查，但 dirty snapshot 不得被冒充为正式 release snapshot。固定 `SOURCE_DATE_EPOCH=0` 连续构建时，四份 `MANIFEST.json` / `SHA256SUMS` hash 无差异；这证明构建可复现，不证明当前 snapshot 已获批准。
