---
title: "Website Content Operations Scripts"
description: "子库源码包的无依赖结构、发布内容安全、Runtime Contract schema 和发布前静态检查入口。"
type: "tooling-index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-31"
sources: ["Repository structure adversarial upgrade 2026-07-28"]
related: ["../README.md", "../MANIFEST.md", "../RUNTIME-CONTRACT.json", "../SCHEMAS/runtime-contract.schema.json", "../RELEASE.md", "../INSTALL.md", "validate-sub-library.mjs", "validate-article-package.mjs", "article-package.test.mjs", "sync-workspace-template.test.mjs", "validate-artifact.mjs", "validate-links.mjs", "release-governance.test.mjs", "query-allincms-official-tutorial-index.mjs", "query-allincms-official-tutorial-index.test.mjs", "build-release.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Scripts

## Source-only Skill 安装

完整 `website-content-ops` clean clone 是唯一 canonical 安装来源；`vendor/` bundle 已退役且不随仓分发。在 `SKILL-INSTALL/` 运行 `python3 install.py`，Windows 运行 `install.cmd`。安装器自动完成 adapter 的 `npm ci`、接口 Registry/索引检查、`runtime-test-plan.json` 驱动的全自测、原生依赖加载检查和 Skill 链接创建；`install.sh` 仅为 POSIX 薄包装。详见 [INSTALL.md](../INSTALL.md) 与 [SKILL-INSTALL/README.md](../SKILL-INSTALL/README.md)。

## interface-kit 真源管线（id-0073）

```bash
python3 scripts/interface-kit-pipeline.py status            # runtime/tracked/dist 三层状态
python3 scripts/interface-kit-pipeline.py pull-to-tracked --confirm   # runtime 改动回流 tracked（fail-closed）
python3 scripts/interface-kit-pipeline.py anchor            # commit 后记录 SHA 锚
python3 scripts/interface-kit-pipeline.py build-dist        # 从 git committed 字节构建 dist（本地产物）
python3 scripts/interface-kit-pipeline.py sync-runtime --confirm      # runtime 消费 dist（前置守卫防覆盖）
python3 scripts/interface-kit-pipeline.py check             # stale 守卫（落后 >10 commit 或 >7 天告警）
python3 scripts/interface-kit-pipeline.py selftest          # 四场景自测
python3 scripts/interface-kit-pipeline.py install <目录> [--force]  # 自用轻量安装（逐文件 sha256 校验；source-only 边界）
```

真源方向：runtime 编辑 → 回流 tracked → git commit（SHA 锚）→ build-dist（只读 committed 字节）→ runtime 消费。interface-kit 的 dist 为**本地消费产物**，不入 build-release.mjs 的子库候选；子库 release 重建 `dist/latest/` 后需重跑本管线 `build-dist`。`sync-runtime` 存在未回流改动即中止；`client-ids.local.txt`/`__pycache__` 等本地文件永不同步。

## AllinCMS 官方教程查询

```bash
node scripts/query-allincms-official-tutorial-index.mjs "怎么新建文章并发布"
node scripts/query-allincms-official-tutorial-index.mjs --json "如何创建产品分类"
node --test scripts/query-allincms-official-tutorial-index.test.mjs
```

查询器只读取 [官方教程发现索引](../REFERENCES/ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json)，不联网、不登录、不执行 CMS mutation。命中后必须打开 `official_url` 实时核验；用户实际询问 API、字段或真实写入时，继续读取 AllinCMS canonical Adapter 和 Interface Registry。

## Content Operation Plan 校验

```bash
node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>
node scripts/validate-source-extraction.mjs path/to/source-extraction.json
node scripts/validate-content-operation-plan.mjs path/to/content-operation-plan.json
node --test scripts/content-operation-plan.test.mjs
node --test ADAPTERS/cms/allincms/content-run-controller.test.mjs
```

运行区 helper 生成绑定 `client_id + company_id + task_id` 的 canonical task root 与 digest；两个验证器共同阻断跨客户/跨任务路径、绝对路径、URL、路径逃逸和伪 runtime 前缀。Content Operation Plan 验证器继续检查来源引用、事实状态、精确 identity、update fingerprint、能力成熟度、严格串行依赖、动态接口/凭据禁入、只读歧义对账、后台/编辑器/前台验收和计划摘要授权。它只输出本地结构结论，不证明真实 CMS 写入或发布。Controller 专项测试继续覆盖整份计划一次授权、每请求前复核、严格串行、expected-current fingerprint、evidence checkpoint、unknown transport 只读 reconcile、禁止盲重试、跨客户阻断、动态接口/凭据字段阻断和 authoritative readback。

## 结构检查

在子库根目录运行：

```bash
node scripts/validate-sub-library.mjs
```

它检查必需入口、Markdown front matter、正文与 YAML 的活动相对链接、是否越过子库根、旧路径、文件/目录同名冲突、Manifest 显式 allowlist、跨平台本地路径、明显凭据与常见 PII，并使用 [Runtime Contract Schema](../SCHEMAS/runtime-contract.schema.json) 检查输入、输出、权限、副作用、审批、回滚和写回边界。

`MANIFEST.md` 是本独立子库当前发布状态的唯一真源。required contract 固定为：`README.md` 投影 `release_status, preview_publication_status, license_status`；`INSTALL.md` / `RELEASE.md` / `VERSION.md` 投影 `release_status, preview_publication_status`；`SKILL.md` 再增加 `skill_status`；`LICENSE.md` 投影 `release_status, license_status`。这些 required 文档同时删除两个声明或缩窄字段集合也不能退出检查。其他活动 Markdown 只要声明了 `state_source` 或 `state_projection` 中任一项，就必须同时声明两项。validator 只接受精确解析到 standalone scope 根目录的 `MANIFEST.md` 并逐字段比较；来源缺失/越根/不是 manifest、投影为空或重复、字段缺失和值漂移全部 fail closed。历史审查和归档记录不声明投影，因此不会被今天的状态覆盖。

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
node --test scripts/sync-workspace-template.test.mjs
```

子库结构校验会自动执行 `--check`。同步器对全部 generated projection 逐一核对 bytes、`generated_from`、`generated_source_sha256` 和 `generated_by`；额外的 `*.runtime.md`、canonical `TEMPLATES/` 中伪装成 `.md` 的目录或 symlink、伪装成 runtime 文件的目录、metadata 篡改或任何第二真源都会在 check 与 write 两种模式 fail closed。如果源码模板更新但没有重新生成运行时副本，校验必须阻断，而不是让独立包带着隐性断链继续发布。

## B2B SEO 文章包校验

正式买家文章使用同一 `package_id` / `brief_id` 绑定 Article Brief、Article Draft、Article Quality Review 和 Publish Record。先运行负向回归，再校验目标四件套：

```bash
node --test scripts/article-package.test.mjs
node scripts/validate-article-package.mjs \
  --brief EXAMPLES/fluxpedal-motors/b2b-seo-article-brief.md \
  --draft EXAMPLES/fluxpedal-motors/b2b-seo-article-draft.md \
  --review EXAMPLES/fluxpedal-motors/b2b-seo-article-review.md \
  --publish EXAMPLES/fluxpedal-motors/b2b-seo-publish-record.md
```

负向回归总数不在治理文档中写死，必须以执行 `node --test scripts/article-package.test.mjs` 时的当前 TAP 输出为准；主线程可在最终冻结证据中记录该次真实计数。四件套成功输出为 `ARTICLE_PACKAGE_STRUCTURE_PASS`，并显式保留 `factual_evidence=not_verified`。它只证明当前实现覆盖的 package 绑定、字段、正文语义和格式检查；不证明引用内容真实、搜索判断正确、Reviewer 真人身份或独立性、授权真实性、CTA 目的地网络可达、浏览器结果、排名、询盘、转化或真实发布。

Canonical v4 已在 validator、synthetic fixture 和负向回归中同步：固定 18 个 fatal IDs，并包含 `qualified-inquiry-contract`、`cta-destination-reachability` 与 `anti-stuffing`。Review 正文必须逐项给出 18 行 canonical 可见证据矩阵，且每行包含 PASS/BLOCK、check-specific evidence 和 limitation；缺行、重复行、状态漂移、blanket PASS 或复用一组宽泛证据都会 fail closed。`cta_destination_reachability_check_pass` 只表示 Reviewer 正确核对 reachability gate，不表示目标 URL 可达；当状态为 `missing / conflicting / expired` 时 production 继续 BLOCK，旧字段 `cta_destination_reachability_pass` 被明确拒绝。

当前 validator 还会阻断：无证据的排名、询盘或转化结果承诺；把 direct answer 藏到全文末尾；只写“提高效率、降低成本、沟通挑战”等泛化痛点；在一个 dominant task 中打包 learn / compare / validate / buy 多个任务族；用同一任务伪装 cannibalization 边界；以及 Brief/Review reachability 状态不一致。`conflict_candidates`、`intent_separation`、`product_decision_map`、`internal_link_buyer_task_contracts`、progressive profiling 与 qualified-inquiry / sales-acceptance / measurement snapshot 均使用 canonical grammar 并跨 Brief、Draft、Review、Publish Record 对齐。

F22 对抗路径还要求：buyer-visible pain chain 使用六条编号自然语言且不泄漏 audit labels；`conversion_surface_map` 使用 `surface-id|role|outcome|location-or-locator|interaction|route-id` 六槽并与 CTA inventory 一一绑定；`cta_measurement_map` 再绑定相同 surface/role/owner、stage-specific qualification/commercial events 及本地 evidence refs；measurement evidence 必须包含当前每一行唯一的 `measurement_row_sha256`。主入口测试与 mutation-kill 会分别证明 transmission inventory 和 published lifecycle 的 active call 不可删除。Production-shaped fixture 中的 `pass/published` 只覆盖 validator 分支，绝不证明真实 CMS、前端 SEO、analytics、排名、询盘、转化或收入。

索引文章的 dominant intent、客户语言、痛点、content inventory 与 information gain 必须为 `confirmed` 且绑定非占位 refs，cannibalization 必须 resolved。正文第一个 heading 必须是 H2，`format_features` 必须与实际转换结果完全一致；converter 会阻断正文 H1、H4-H6、Setext heading、code block、raw HTML/HTML comment、Markdown 图片、reference-style link、不安全链接和不匹配表格。`dry-run` 不能声明 API 写入成功，`draft` 不能在 API 未运行时声明 ready；`published` 还要求至少三个不同的 evidence refs。富文本 converter 与 `article-image-binding.mjs` 仍是两条未合并路径，无图文章包 PASS 不得外推为“真实图片 + 富文本”一体化稳定。

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

该脚本校验 `MANIFEST.json`、`SHA256SUMS`、文件集合和嵌套构建产物，并在打包后重复扫描 macOS、Linux、Windows 和文件 URI 形式的本地路径，以及明显凭据、非示例邮箱、电话与客户标识。它还逐文件核对 `git-file-provenance/v1` receipt：provenance 路径集合必须与 `MANIFEST.json.files` 精确一一对应，每条 SHA-256 必须等于候选包实际 bytes，commit-bound 记录还必须与其 `commit_sha256` 一致；因此只重算 `content_digest` 和 `SHA256SUMS` 不能掩盖陈旧 provenance。扫描仍是补充控制；候选文件只允许 `.md`、`.json`、`.mjs`、`.yml`、`.yaml`，以及显式的 `.gitignore`，其他扩展名一律阻断。

普通 artifact PASS 只证明候选包内的 manifest、checksums、文件 bytes 与 provenance receipt **内部自洽**；它不能独立证明 Git commit object 真实存在、记录的 blob 确实属于该 commit、远端 tag 受保护、signer 可信或批准者是真人。正式 qualification 仍必须由候选包外的可信 workflow 在 clean/tagged checkout 上验证 commit、tag、signer、approval/evidence 并注入实际绑定值。

## 发布治理攻击回归

```bash
node --test scripts/release-governance.test.mjs
```

测试只在系统临时目录创建隔离副本，覆盖状态投影漂移、当前候选 machine state 与 public entry/release prose 的矛盾、根 basename glob、未登记 `clients/`、未登记 private-notes、跨平台路径与常见 PII、以及语义空 Runtime Contract。当前候选处于 `BLOCK`、identity/version 未分配、许可 pending 或批准 pending 时，公共入口不得肯定宣称当前候选为 Stable、Published、production-ready、approved、deployed 或已通过 live SEO；明确否定、具名历史 artifact 和 future prerequisite 不受影响。它不连接真实 CMS，不构造真实客户资料，也不改变 Preview/Stable 边界。

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



## 对抗审查冻结证据包

`build-review-freeze.mjs` 只向仓库外的显式绝对路径写入，递归冻结 `--roots-file` 中代码根的本地 ESM 依赖，并把 `--resources-file` / 重复 `--resource-file` 指定的非代码运行时资源纳入同一 exact set。static import、export-from 由 Node `vm.SourceTextModule` 语法解析；literal dynamic import 由 token-aware scanner 补充。missing、ambiguous extension、scope escape、symlink、non-regular、unsupported local type 和 non-literal dynamic import 全部 BLOCK。未扫描的 `.cjs` 等 executable resource、`eval` / `Function` / string timer loader、Worker / SharedWorker / ServiceWorker runtime dependency、任意 `dist/` 路径，以及完整 code dependency closure 与 resources 的分类重叠也全部 fail closed；不得用 resource classification 绕过代码依赖扫描。脚本复制后重新验证 exact file set、bytes 与 SHA-256；已有输出一律拒绝覆盖。

控制清单是 UTF-8 文本，每行一个 canonical repo-relative POSIX path；允许空行和以 `#` 开头的注释。`roots.txt` 只列 `.mjs` / `.js` 代码入口；母库级 harness 可以显式列入，但其 canonical scope 外依赖也必须逐个显式列为 root。`resources.txt` 逐项列 regular、non-symlink、非 executable、非 `dist/` 的运行时文件；代码不能伪装成 resource，且任何已出现在 root 或 transitive code closure 的路径都不得再次列为 resource。

先由调用方提供仓库外的绝对审查目录，或在当前 shell 中创建一个临时目录；`roots_file` 与 `resources_file` 是输入控制文件，不是 builder 生成物：

```bash
review_dir="${REVIEW_DIR:-$(mktemp -d)}"
roots_file="$review_dir/wco-<candidate>-roots.txt"
resources_file="$review_dir/wco-<candidate>-resources.txt"
```

`roots_file` 内容示例：

```text
sub-libraries/website-content-ops/scripts/build-review-freeze.mjs
sub-libraries/website-content-ops/scripts/build-review-freeze.test.mjs
sub-libraries/website-content-ops/scripts/release-governance.test.mjs
sub-libraries/website-content-ops/scripts/article-package.test.mjs
sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-content-formats.test.mjs
sub-libraries/website-content-ops/scripts/sync-workspace-template.test.mjs
```

`resources_file` 内容示例：

```text
sub-libraries/README.md
sub-libraries/registry.json
sub-libraries/website-content-ops/.gitignore
sub-libraries/website-content-ops/INSTALL.md
sub-libraries/website-content-ops/VERSION.md
sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations-contract.json
# 继续逐项列出冻结测试真实读取的其余 Markdown、JSON、template 和 fixture 文件。
```

生成前确保以下四个 generated output paths 不存在；不要把 manifest、file list、SHA sidecar 或 freeze root 指向仓库内：

```bash
manifest_file="$review_dir/website-content-ops-b2b-article-freeze-<candidate>.json"
freeze_root="$review_dir/website-content-ops-b2b-article-freeze-<candidate>-root"
file_list="$review_dir/wco-b2b-freeze-files-<candidate>.txt"
sha_file="$review_dir/website-content-ops-b2b-article-freeze-<candidate>.sha256"

node scripts/build-review-freeze.mjs \
  --freeze-id WCO-B2B-ARTICLE-<VERSION>-<YYYYMMDD>-<CANDIDATE> \
  --manifest "$manifest_file" \
  --freeze-root "$freeze_root" \
  --file-list "$file_list" \
  --sha-file "$sha_file" \
  --roots-file "$roots_file" \
  --resources-file "$resources_file"
```

`--resource-file sub-libraries/website-content-ops/PATH` 可重复使用，适合临时追加一两个 repo-relative 资源；可维护的完整 release-governance runtime closure 应固定在审查专用 resources 清单中，不应硬编码进 builder。

生成完成后，controller 必须在 builder 进程之外独立计算 manifest bytes 的 SHA-256，并把该值直接传给 `verify-review-freeze.mjs`。不得从同目录 sidecar 读取 expected SHA 来自证。Verifier 调用必须同时带入两份 input controls：

```bash
expected_manifest_sha256="$(shasum -a 256 "$manifest_file" | awk '{print $1}')"

node scripts/verify-review-freeze.mjs \
  --freeze-root "$freeze_root" \
  --manifest "$manifest_file" \
  --file-list "$file_list" \
  --sha-file "$sha_file" \
  --roots-file "$roots_file" \
  --resources-file "$resources_file" \
  --expected-manifest-sha256 "$expected_manifest_sha256"
```

verifier 会重算 manifest digest，严格校验 manifest schema、canonical path、exact file set、file-list 顺序、每个文件的 bytes/SHA-256，并拒绝 symlink、non-regular、路径穿越、额外文件及 sidecar mismatch。它只验证 freeze tree、manifest、file list、roots file、resources file 和显式 `--sha-file` 已经处于规定的本地只读模式，不负责设置权限；审查结束后 controller 应再用同一外部保存的 expected SHA 复验一次。即使攻击者同步改写 manifest 与 sidecar，只要 controller expected SHA 未变也必须 BLOCK。

### 只读冻结候选上的 mutation suite 唯一流程

冻结候选本体始终保持只读。需要运行会改写 fixture 的 mutation suite 时，controller 只能按以下顺序执行，不能直接对 freeze tree `chmod`，也不能跳过任一步：

1. 使用 controller 外部保存的 expected manifest SHA-256 调用 `verify-review-freeze.mjs`，验证冻结候选 exact bytes。
2. 把已验证候选复制到新的仓库外临时目录；复制必须 byte-identical，且不得复用旧临时副本。
3. 在任何权限变更前，再次逐文件验证临时副本的 exact file set、bytes 与 SHA-256 均与候选 manifest 一致。
4. 只对临时副本递归增加 owner write/execute 权限；不得改变 freeze tree、manifest、file list、SHA sidecar 或 controller SHA 文件的权限和 bytes。
5. 仅在该 writable temporary copy 上运行 mutation suites；测试 fixture 自身仍须 fail closed，且不得把临时副本结果解释为冻结候选已被修改。
6. 把测试命令、TAP 结果、temporary-copy pre-chmod byte verification 和 candidate controller SHA-256 绑定到同一 review evidence record；审查结束后再次验证原冻结候选。

`sync-workspace-template.test.mjs` 遵守同一边界：`cpSync` 完成后只将测试临时副本设为 owner-writable，以便 mutation fixture 写入；不会放宽源候选或 review freeze 的权限。

此机制的信任范围严格限定为 **local review immutability**：它不是数字签名，不证明 reviewer 身份或独立性，不是 release trust、Stable、Published、production-ready、真实 SEO 排名、询盘或转化效果证据。

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

正式 `sub-library-release-v1` trusted runtime profile 只接受固定 test plan：`upload-media-browser.test.mjs`、`article-image-binding.test.mjs`、`article-content-formats.test.mjs`、`article-operations.test.mjs`，并要求精确 `160 passed / 0 failed / 0 skipped`；历史 profile `120/120`、`131/131`、`136/136`、`145/145`、`156/156`、`158/158`，以及异常结果 159/161、任意少跑/多报、失败、跳过或重排 test plan 都必须 fail closed。合同分项为媒体 47、正文图片 52、正文格式 13、文章生命周期/taxonomy 48。

`APPROVAL_RECORD_PASS` 只表示记录结构以及候选、evidence、canonical tag 和 workflow 注入值精确绑定；`ARTIFACT_QUALIFICATION_RECORD_PASS` 只再证明 frozen candidate 完整性及同一绑定。二者都不证明 approver 真人身份、reviewer 独立性、远程 signer allowlist、Protected Environment、workflow 来源、已经发布或 `Published` 状态。当前子库本地治理测试数量由 `node scripts/release-governance.test.mjs --list` 的注册计划动态确定，evidence 必须绑定该精确计划数量且全部通过，禁止继续写死陈旧的 11/11；adapter trusted runtime profile 当前固定为四文件 160/160（47 + 52 + 13 + 48），历史 158/158 必须拒绝。真实 GitHub formal workflow 未在本地运行。

历史 `v0.3.2-preview.1` 已按其冻结范围公开；当前未发布源码候选为 `approval_status: pending`、`release_status: BLOCK`、`preview_publication_status: BLOCK`、`license_status: pending`。本地测试或 artifact 通过不得把当前候选升级成 Preview、Stable、Ready、Published 或 production-ready。
