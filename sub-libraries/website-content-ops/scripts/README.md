---
title: "Website Content Operations Scripts"
description: "子库源码包的无依赖结构、发布内容安全、Runtime Contract schema 和发布前静态检查入口。"
type: "tooling-index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["Repository structure adversarial upgrade 2026-07-28"]
related: ["../README.md", "../MANIFEST.md", "../RUNTIME-CONTRACT.json", "../SCHEMAS/runtime-contract.schema.json", "../RELEASE.md", "../INSTALL.md", "validate-sub-library.mjs", "validate-artifact.mjs", "validate-links.mjs", "release-governance.test.mjs", "build-release.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Scripts

## 结构检查

在子库根目录运行：

```bash
node scripts/validate-sub-library.mjs
```

它检查必需入口、Markdown front matter、正文与 YAML 的活动相对链接、是否越过子库根、旧路径、文件/目录同名冲突、Manifest 显式 allowlist、跨平台本地路径、明显凭据与常见 PII，并使用 [Runtime Contract Schema](../SCHEMAS/runtime-contract.schema.json) 检查输入、输出、权限、副作用、审批、回滚和写回边界。

Manifest allowlist 和人工发布复核是主边界；内容扫描只是纵深防御，不能因为扫描无命中就认定文件适合公开发布。

可发布前强制检查：

```bash
node scripts/validate-sub-library.mjs --release
```

`--release` 只有在 `MANIFEST.md` 已明确标记为 `Ready` 或 `Published` 时才通过；当前源码包预期会被阻断。

脚本是静态检查，不代表真实 CMS、浏览器、安装、跨部署或外部发布验收。

## 工作区模板独立性

`WORKSPACE-TEMPLATE/` 可能被单独复制给客户，因此其中的运行模板不能依赖子库上层的 `TEMPLATES/`、`ADAPTERS/` 或母库路径。子库根目录的 `TEMPLATES/` 是唯一源码；运行时副本由以下命令同步：

```bash
node scripts/sync-workspace-template.mjs
node scripts/sync-workspace-template.mjs --check
```

子库结构校验会自动执行 `--check`。如果源码模板更新但没有重新生成运行时副本，校验必须阻断，而不是让独立包带着隐性断链继续发布。

## latest-only 候选包

从子库根目录运行：

```bash
node scripts/build-release.mjs
```

普通模式输出到 `dist/latest/`，生成 `MANIFEST.json` 和 `SHA256SUMS`，并把 `qualification_state` 标记为 `working-candidate`；它只用于当前 working tree 的机械检查。正式资格先运行 `SOURCE_DATE_EPOCH=0 node scripts/build-release.mjs --prepare`，输出到 `dist/prepared/v<version>/<content_digest>/`，候选状态固定为 `Ready`、`pending`、`prepared-unapproved`。builder 的单阶段 `--release` 已退役，`--prepare` 也拒绝 approval/evidence。

## 独立候选包校验

```bash
node scripts/validate-artifact.mjs dist/latest
node scripts/validate-artifact.mjs --prepare dist/prepared/v<version>/<content-digest>
```

`--release` 只用于后续 qualification，且只接受 frozen `prepared-unapproved` 候选；不得把 `dist/latest` 传入正式资格闸。

该脚本校验 `MANIFEST.json`、`SHA256SUMS`、文件集合和嵌套构建产物，并在打包后重复扫描 macOS、Linux、Windows 和文件 URI 形式的本地路径，以及明显凭据、非示例邮箱、电话与客户标识。扫描仍是补充控制；候选文件只允许 `.md`、`.json`、`.mjs`、`.yml`、`.yaml`，以及显式的 `.gitignore`，其他扩展名一律阻断。

## 发布治理攻击回归

```bash
node --test scripts/release-governance.test.mjs
```

测试只在系统临时目录创建隔离副本，覆盖根 basename glob、未登记 `clients/`、未登记 private-notes、跨平台路径与常见 PII、以及语义空 Runtime Contract。它不连接真实 CMS，不构造真实客户资料，也不改变 Draft/BLOCK 状态。

`--prepare` 与正式 `--release` 都只运行 standalone 子库候选包内实际提供的校验器：`validate-links.mjs --release`、`sync-workspace-template.mjs --check` 和 `validate-sub-library.mjs --prepare`；不会假定母库的索引、日志或知识链脚本存在。正式 `--release` 额外验证外部 approval/evidence、tag 和 commit provenance。任一内嵌校验器缺失、失败或修改 frozen candidate 字节都会阻断。

## 最小负向回归（扩展名白名单）

除上述治理攻击回归外，下面的只读候选包副本命令继续覆盖“已登记但扩展名未知”的反例：它会重算内容摘要和校验和，因此预期失败必须来自扩展名白名单，而不是完整性失配。

```bash
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -R dist/latest "$tmp/latest"
node --input-type=module - "$tmp/latest" <<'NODE'
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const root = process.argv[2];
const hash = (file) => createHash('sha256').update(readFileSync(join(root, file))).digest('hex');
const manifestPath = join(root, 'MANIFEST.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
writeFileSync(join(root, 'unexpected.txt'), 'negative fixture\n');
manifest.files = [...manifest.files, 'unexpected.txt'].sort();
const digest = createHash('sha256');
for (const file of manifest.files) digest.update(`${file}\0${hash(file)}\n`);
manifest.content_digest = digest.digest('hex');
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
writeFileSync(join(root, 'SHA256SUMS'), [...manifest.files, 'MANIFEST.json']
  .map((file) => `${hash(file)}  ${file}`).join('\n') + '\n');
NODE
if node scripts/validate-artifact.mjs "$tmp/latest" >"$tmp/output" 2>&1; then
  echo 'expected extension allowlist rejection, but validator passed' >&2; exit 1
fi
grep -F 'FAIL: unsupported artifact file extension: unexpected.txt' "$tmp/output"
```


## 本地链接校验

```bash
node scripts/validate-links.mjs
node scripts/validate-links.mjs --release
```

该脚本只检查子库 scope 内的 Markdown 相对链接，不访问外部 URL；复制成 standalone artifact 后仍可独立运行。

## 发布候选激活的 fail-closed 规则

`build-release.mjs` 普通模式只在 staging 的 checksum、结构和 artifact 校验全部通过后才激活 `dist/latest/`；`--prepare` 只在 clean commit、`Ready/pending` 和 commit provenance 全部满足时，原子激活精确内容寻址的 prepared 目录。失败时删除 staging，保留既有候选。builder 不接收批准材料，也不写入 qualified/approved 状态；这证明的是冻结候选的机械边界，不是最终人工批准。

## 人工批准与独立 tag namespace

子库候选包的批准声明必须同时使用旁路 `RELEASE-APPROVAL.json` 与 scope-bound `RELEASE-EVIDENCE.json`，不能把批准或验证证据塞入参与 `content_digest` 的源码，避免摘要循环。记录必须绑定 `source_commit`、`content_digest`、`MANIFEST.json` SHA-256、`SHA256SUMS` SHA-256、evidence 的 `sha256-canonical-json-v1` 摘要、精确 annotated tag object SHA、signer fingerprint 与 canonical tag annotation/approval-binding digest。候选 manifest 还必须逐文件证明 package path、repository-relative path、candidate SHA-256 与 commit blob 一致；working-tree snapshot 只能用于普通候选检查。记录中的 approver/reviewer 是待外部信任系统确认的声明，validator 不验证真人身份或独立性。

本子库固定使用 `sub-library/website-content-ops/v<version>`；母库的 `mother/v<version>` 不能代替子库 tag。验证命令：

```bash
node scripts/validate-release-approval.mjs \
  dist/latest \
  /path/to/RELEASE-APPROVAL.json \
  /path/to/RELEASE-EVIDENCE.json
```

正式两阶段 qualification：

```bash
SOURCE_DATE_EPOCH=0 node scripts/build-release.mjs --prepare

RELEASE_APPROVAL_PATH=/external/RELEASE-APPROVAL.json \
RELEASE_EVIDENCE_PATH=/external/RELEASE-EVIDENCE.json \
RELEASE_SOURCE_ROOT=/clean/tagged/checkout \
RELEASE_REQUIRE_GIT_TAG=1 \
RELEASE_TRIGGER_TAG=sub-library/website-content-ops/vX.Y.Z \
RELEASE_ACTUAL_TAG_OBJECT_SHA=<workflow-resolved-annotated-tag-object-sha> \
RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT=<workflow-verified-primary-fingerprint> \
RELEASE_ACTUAL_TAG_ANNOTATION_SHA256=<sha256-of-canonical-annotation-bytes> \
RELEASE_ACTUAL_TAG_ANNOTATION_BASE64=<base64-of-exact-canonical-annotation-bytes> \
RELEASE_ACTUAL_APPROVAL_BINDING_SHA256=<sha256-of-canonical-approval-binding> \
node scripts/validate-artifact.mjs \
  --release \
  dist/prepared/vX.Y.Z/<content-digest>
```

artifact gate 对同一个 frozen candidate 验证 approval/evidence、canonical annotation bytes、workflow 注入的实际 tag object SHA、signer fingerprint、annotation digest、approval-binding digest、`source.commit`、逐文件 repository-relative commit provenance 和 qualification 前后 tree digest。五个 `RELEASE_ACTUAL_*` 值必须由候选包外、固定且受保护的 workflow 在验证真实 tag 后注入；候选自身不得推导并自证这些值。批准与资格状态保存在候选包外的 sidecar/attestation 中；候选包本身保持 `pending`、`prepared-unapproved`。

正式 `sub-library-release-v1` trusted runtime profile 只接受固定 test plan：`upload-media-browser.test.mjs`、`article-image-binding.test.mjs`、`article-operations.test.mjs`，并要求精确 `131 passed / 0 failed / 0 skipped`；旧 `120/120`、任意少跑/多报、失败、跳过或重排 test plan 都必须 fail closed。合同分项为媒体 45、正文图片 50、文章与 taxonomy 36。

`APPROVAL_RECORD_PASS` 只表示记录结构以及候选、evidence、canonical tag 和 workflow 注入值精确绑定；`ARTIFACT_QUALIFICATION_RECORD_PASS` 只再证明 frozen candidate 完整性及同一绑定。二者都不证明 approver 真人身份、reviewer 独立性、远程 signer allowlist、Protected Environment、workflow 来源、已经发布或 `Published` 状态。当前子库本地治理测试为 10/10；adapter 当前为 131/131。真实 GitHub formal workflow 未在本地运行。

当前 `approval_status: pending` 与 `release_status: Preview` 表示只放行公开试用；本地测试或 artifact 通过不得把它升级成 Stable、Ready 或 Published。
