---
title: "Mother Library Scripts"
description: "说明母库结构校验、治理负向回归、索引同步、候选包构建和制品验收脚本的运行方式、证据边界与已知缺口。"
type: "tooling-index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["Mother-library and sub-library release architecture decision 2026-07-28"]
related: ["../MANIFEST.md", "../RELEASE.md", "run-governance-tests.mjs", "tests/governance-cases.mjs", "verify-runtime-test-profile.mjs", "verify-tested-candidate-identity.mjs", "verify-node-test-summary.mjs", "resolve-release-scope.mjs", "validate-release-approval.mjs", "validate-mother-library.mjs", "validate-artifact.mjs", "validate-links.mjs", "build-mother-release.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Mother Library Scripts

## 稳定文档 ID

新建长期知识页默认使用 `id-####-slug.md` 并在 front matter 写 `doc_id: "ID-####"`。运行：

```bash
node scripts/validate-document-ids.mjs
```

默认模式只阻断重复/非法 ID，并报告未迁移的 legacy 页面；不要为了清零 legacy 而一次性重命名全库。`--scope mother` 只检查母库，`--scope sub-library:<id>` 只检查一个独立子库；`--strict` 只在单独迁移窗口使用。编号 durable page 缺少或错写 `doc_id` 会直接阻断，legacy 页面仍作为迁移债务报告。规则和豁免见 [../wiki/00_meta/document-id-standard.md](../wiki/00_meta/document-id-standard.md)。

记录型文件不使用普通 durable ID：来源页使用 `SRC-...`，验证记录使用 `VER-YYYYMMDD-slug.md`，写回记录使用 `WB-YYYYMMDD-slug.md`，兼容页使用 `type: redirect`。这些类型由验证器显式豁免，避免把一次性证据记录误报成长期知识页。

处理 raw 到课程的任务还要运行：

```bash
node scripts/validate-knowledge-chain.mjs
```

它检查 raw 必填字段、Source ID / registry、`derived_to`、source note 的 concept/playbook/course/verification/writeback 指针，以及 raw 不得混入提炼标题。若课程仍是 `assigned-not-submitted` 或 `partially_verified`，普通模式输出 `KNOWLEDGE_CHAIN_STRUCTURE_PASS`；`--release` 会将未完成的人工作业/真实验证转为 BLOCK。

## 本地 Markdown 链接校验

```bash
node scripts/validate-links.mjs
node scripts/validate-links.mjs --release
```

该校验器只验证当前 scope 内的 Markdown 相对链接是否存在，并拒绝指向 scope 外的本地路径；不会抓取外部 URL。普通模式输出 warning 后继续，`--release` 将断链或母库/子库边界泄漏升级为 BLOCK。母库和独立子库各自携带一份同名脚本，候选包会在复制后的目录再次运行。

## 日志闭环校验

```bash
node scripts/validate-logs.mjs
node scripts/validate-logs.mjs --release
```

校验器只扫描 `wiki/00_meta/logs/YYYY/MM/YYYY-MM-DD.md` 的 `EVT-YYYYMMDD-####` 事件卡，不读取旧 `wiki/00_meta/ingestion-log.md`。每条事件必须有非空的 `actor`、`scope`、`action`、`result`、`risk`、`next`，并显式写出 `evidence`、`commands`、`files changed`、`writeback`；后四项允许为空。普通模式把缺字段、重复 event ID 和非法或不一致日期报告为 `LOG_VALIDATION_WARNINGS`，不阻断；`--release` 会把同类问题输出为 `LOG_VALIDATION_FAILURES` 并以非零状态退出。完整字段别名和路径合同见 [../wiki/00_meta/logging-standard.md](../wiki/00_meta/logging-standard.md)。

## 新建长期文档

优先使用生成器取得当前 scope 的下一个 ID，避免人工抢号或漏写 front matter：

```bash
node scripts/create-document.mjs \
  --dir wiki/20_concepts \
  --template wiki/_templates/concept-page.md \
  --slug example-topic \
  --title "Example Topic" \
  --description "面向什么人，解决什么问题，读完可以完成什么任务；明确不覆盖的边界。" \
  --dry-run
```

确认内容后去掉 `--dry-run`。它只新建文件，不重命名、不覆盖已有文件；`index.md`、raw、日志、模板和协议单例不要用这个命令申请普通 ID。

生成器会拒绝治理目录、raw、日志、模板和仓库根目录作为 `--dir`。母库只在 `wiki/20_concepts`、`wiki/30_playbooks`、`wiki/40_business`、`wiki/50_channels`、`wiki/60_clients`、`wiki/70_competitors`、`wiki/80_metrics`、`wiki/90_outputs` 范围内取号；子库只在其 `MANIFEST.md` 声明的 `durable_roots`（默认 `KNOWLEDGE/`、`PLAYBOOKS/`、`COURSES/`、`OUTPUTS/`）内取号，且不会读取兄弟子库或母库 ID；子库 durable page 必须使用子库自己的模板。

## 索引同步与检查

Markdown 增删改后先同步各级 `index.md` 的直接入口表，再做只读校验：

```bash
node scripts/sync-indexes.mjs
node scripts/validate-indexes.mjs
```

CI 使用 `node scripts/validate-indexes.mjs --check`，只要索引生成区过期就阻断。脚本只索引当前目录的直接 Markdown 和直接子目录 canonical 入口，不会把孙级内容递归复制到上级。

## 结构检查

从母库根目录运行：

```bash
node scripts/validate-mother-library.mjs
```

发布闸检查：

```bash
node scripts/validate-mother-library.mjs --release
```

脚本检查入口文件、Markdown 元数据（根 README 使用 HTML 注释元数据块）、正文与 YAML 路径、分层索引、母库 / 子库边界、旧路径、机器绝对路径、明显凭据模式、版本注册和 manifest 状态。

脚本不替代版权、许可证、真实工具、安装、跨环境和人工发布验收。CI 入口见 [`.github/workflows/validate-library.yml`](../.github/workflows/validate-library.yml)；CI 通过也不自动解除 `release_status: BLOCK`。

## latest-only 候选包

从母库根目录运行：

```bash
node scripts/build-mother-release.mjs
```

普通模式输出到 `dist/mother/latest/`，同时生成 `MANIFEST.json` 和 `SHA256SUMS`，并将 `qualification_state` 标记为 `working-candidate`；它只用于当前 working tree 的机械检查。正式资格先运行 `SOURCE_DATE_EPOCH=0 node scripts/build-mother-release.mjs --prepare`，输出到 `dist/mother/prepared/v<version>/<content_digest>/`，候选状态固定为 `Ready`、`pending`、`prepared-unapproved`。builder 单阶段 `--release` 已退役，`--prepare` 也拒绝 approval/evidence。

## 独立候选包校验

```bash
node scripts/validate-artifact.mjs dist/mother/latest
node scripts/validate-artifact.mjs --prepare dist/mother/prepared/v<version>/<content-digest>
```

`--release` 只用于后续 qualification，且只接受 frozen `prepared-unapproved` 候选；不得把 `dist/mother/latest` 传入正式资格闸。正式流程还必须先用 trusted root 的 `validate-release-approval.mjs` 校验 approval/evidence、canonical tag annotation、实际 tag object/signer 和 commit provenance；artifact validator 的 PASS 不能替代该绑定。

该脚本校验 `MANIFEST.json`、`SHA256SUMS`、文件集合、嵌套构建产物和候选包内嵌 validator，并在打包后再次扫描本地绝对路径和明显凭据赋值。候选文件只允许 `.md`、`.json`、`.mjs`、`.yml`、`.yaml`，以及显式的 `.gitignore`；其他扩展名（包括默认未声明理由的 `.txt`、`.sh`）一律阻断。普通 inspect 不会因状态文案自动冒充正式资格；只有显式 `--release` 才读取外部 approval/evidence 并执行 tag/commit gate。prepared 候选路径、状态和 tree digest 任何不一致都会阻断。

`--prepare` 在候选包根目录依次运行 strict index、release link/log checks 和 `validate-mother-library.mjs --prepare`，但不要求真实课程效果资格；正式 `--release` 还运行 `validate-knowledge-chain.mjs --release` 并验证外部批准、tag 和 commit provenance。任何内嵌校验器缺失、失败或修改 frozen candidate 字节都会阻断。

## 治理 validator 负向回归

从母库根目录运行显式 allowlist 中的全部治理攻击：

```bash
node scripts/run-governance-tests.mjs
```

只运行一个用例或查看固定清单：

```bash
node scripts/run-governance-tests.mjs --list
node scripts/run-governance-tests.mjs --test artifact-unknown-extension
node scripts/run-governance-tests.mjs --timeout-ms 30000
```

runner 在系统临时目录为每个用例复制一份不含 `.git`、`node_modules` 和 `dist` 的仓库快照；每个测试由独立 Node 子进程执行并受超时限制，结束后删除临时目录。运行前后会比较真实仓库的 Git 状态；若状态变化，测试整体失败。测试 fixture 不得直接写入真实仓库。

每个预期阻断都同时断言**非零状态和目标诊断文本**，不能把语法错误、缺文件、checksum 失配或任意非零状态误当作攻击被正确阻断。完整 fixture 会在注入攻击后重算 `content_digest` 与 `SHA256SUMS`，使 artifact 测试尽量只命中目标闸门。

当前 53 项 allowlist 覆盖：Front Matter 缺字段、数组形状、重复 key、related 路径与未知 `type`；生成区和人工区越级 index、陈旧 description 与 index 日期；同 scope 重号与跨 scope 合法重号；synthetic 冒充真实验证；日志日期和重复事件；artifact 扩展名、绝对路径、manifest traversal 与 symlink 预读取；显式及装饰后的 AI/system reviewer；approval scope/tag/digest/触发 tag、canonical annotation 与 approval binding；母库和子库逐文件 commit provenance；dirty source、release 与普通模式下的 Ready/Published/approved sidecar gate；母库/子库 artifact PASS 隔离；正式 release router 与 workflow 单 scope 形状；runtime profile 的 adapter/祖先 symlink、根/父级 npm/workspace 控制文件、candidate 重新导出 sibling governance implementation、Node 测试提前退出/计数伪造，以及跨 job candidate/tag/signer/annotation identity；qualification archive/checksum/tree equivalence、runtime applicability 和 attestation 串线攻击。普通 CI 的 `structure-and-artifacts` job 会执行该 runner，但不会执行正式发布。

输出含义：

- `PASS`：攻击被目标 validator 准确阻断，或允许的 scope 边界被准确接受；
- `KNOWN_GAP`：现有 validator 尚未阻断，但该绕过已被显式命名、固定输入和预期行为；新增未知 gap、已实现测试未进入 allowlist、测试超时、目标诊断消失或真实工作树被污染都会使 CI 失败；
- `FAIL`：测试 harness、fixture 或目标 validator 出现非预期行为。

`KNOWN_GAP` 不是安全通过，也不能解除 `release_status: BLOCK`。关闭缺口后，应把对应 case 从 `known-gap` 改成 `reject` 并更新精确诊断；不能直接删除攻击或放宽断言。当前已知缺口以 runner 最终 `KNOWN_GAPS` 清单为准。


## 发布候选激活的 fail-closed 规则

`build-mother-release.mjs` 普通模式只在 staging 的 checksum、结构和 artifact 校验全部通过后才激活 `dist/mother/latest/`；`--prepare` 只在 clean commit、`Ready/pending` 和 commit provenance 全部满足时，原子激活精确内容寻址的 prepared 目录。失败时删除 staging，保留既有候选。builder 不接收批准材料，也不写入 qualified/approved 状态；这证明的是冻结候选的机械边界，不是最终人工批准。

## 人工批准与 tag namespace

候选包机械验证通过后，母库和目标子库都必须分别冻结 scope-bound 的 `release-evidence/v1` JSON bundle，并由真实人工 reviewer 产生一个不进入 `content_digest` 的 `RELEASE-APPROVAL.json` sidecar。每个 scope 的 sidecar 都必须绑定候选包的 `source_commit`、`content_digest`、`MANIFEST.json` SHA-256、`SHA256SUMS` SHA-256，以及对应 evidence bundle 的 `sha256-canonical-json-v1` 摘要；validator 会读取实际 bundle、规范化 JSON 后重算摘要，并核对 profile/scope/source/candidate/completed_at/checks。母库与子库 approval 都要求 `source_commit_rebuildable: true`、`source_snapshot_kind: source-commit`，逐文件核对 package path、repository-relative path、candidate SHA-256、commit blob 声明和空的 unbound/missing 清单；正式 Git tag 模式下再对 clean checkout 的 commit tree 与 blob 内容复核。validator 会拒绝包含 AI/system 身份 token 的 `approved_by`，并要求 `approved_at` 不得晚于 trusted evidence / validation 的 `completed_at`，避免逆序审批时间线；但字符串检查和本地 synthetic 测试本身不能证明远程 GitHub run 或真实人工判断，仍需独立批准渠道、Protected Environment 和可信身份记录。

母库只能使用 `mother/v<version>`，子库只能使用 `sub-library/<package_id>/v<version>`；禁止裸 `v<version>` 或跨 scope 复用 approval。验证命令：

```bash
node scripts/validate-release-approval.mjs \
  dist/mother/prepared/v<version>/<content-digest> \
  /path/to/RELEASE-APPROVAL.json \
  /path/to/RELEASE-EVIDENCE.json
```

该脚本输出 `APPROVAL_RECORD_PASS` 只表示所提供的批准记录与当前候选包完全绑定，不证明批准者身份真实性，也不代表许可证、真实跨部署运行或课程效果自动通过。当前 manifest 的 `approval_status` 仍为 `pending`，所以当前 release 继续 BLOCK。


## 正式 Release 路由与 Workflow 边界

```bash
node scripts/resolve-release-scope.mjs mother/v0.1.1-draft
node scripts/resolve-release-scope.mjs sub-library/website-content-ops/v0.3.2-preview.1
```

resolver 只接受当前 `VERSION.md` 与 registry 精确匹配的 `mother/v<version>` 或 `sub-library/<id>/v<version>`，并只输出一个 scope；裸 tag、未知/重复子库、错版本、registry 路径逃逸或 symlink 越根都必须 BLOCK。

`.github/workflows/validate-library.yml` 只做普通结构、working-tree 候选包和 adapter 验证，不承担正式 release。`.github/workflows/release-library.yml` 仅由 `workflow_dispatch` 启动，输入精确 `release_tag` 与外部 `approval_sidecar_base64`；dispatcher 只能提交尚未填充最终 evidence 字段的 approval intent，不能自行注入 evidence bundle。workflow checkout 对应 signed annotated tag，只运行 resolver 选中的一个 scope；builder 只执行 `--prepare` 并输出精确 frozen candidate path。随后由 pinned trusted governance job 根据本次实际检查输出生成 `RELEASE-EVIDENCE.json`，再用其 canonical digest finalize approval sidecar；trusted root `validate-release-approval.mjs` 把 approval/evidence 与实际 tag object、signer、canonical annotation、approval binding、commit tree 和 workflow/run 上下文精确绑定，归档后还会使用同一对 sidecar 重新验证提取树。该本地结构不能伪装成远程 evidence、Protected Environment 或真人批准证明；远程 run、Environment reviewer、tag signer 身份和 attestation 仍需 GitHub 侧实证。

`environment: formal-release` 只是代码中的环境名称。GitHub 仓库设置中尚需由 Tony 配置 required reviewers 与允许部署的引用；在服务端未运行、无真实 sidecar、无 annotated tag 时，不能把本地 workflow 形状 PASS 写成正式发布可用。Base64 只是编码，sidecar 不得包含密码、Token 或 Cookie。

## Formal qualification 的可信执行边界

正式 workflow 不直接执行 candidate 自带的 resolver 来决定 scope，而是用 `github.workflow_sha` 对应的 trusted governance checkout 执行 `resolve-release-scope.mjs`，并把 `RELEASE_SOURCE_ROOT` 指向独立 candidate checkout。进入 sidecar 和 builder 前还必须：

- 匹配环境级 `FORMAL_RELEASE_TRUSTED_WORKFLOW_SHA` 与启用 secret；
- 验证 signed annotated tag、candidate HEAD 和可信 GPG signing-key fingerprint；allowlist 登记 `VALIDSIG` 实际返回的 signing subkey fingerprint，并明确轮换/撤销；
- 比对母库 scripts、release workflow、`sub-libraries/registry.json` 与目标子库 scripts，阻止 candidate 自带弱化 validator；
- 在独立 runner job 对目标子库运行可信 runtime-test profile：`verify-runtime-test-profile.mjs` 逐级拒绝 adapter/祖先 symlink，要求 package/lock/test 与祖先目录 npm/package-manager 控制文件和 trusted governance 一致，并把显式 allowlist 中的 candidate implementation 与 trusted tests 复制到 `$RUNNER_TEMP/runtime-subject`。依赖安装与测试在 `FORMAL_RELEASE_NODE20_IMAGE_DIGEST` 固定的 Node 容器内运行；测试容器只读挂载 subject、禁网、降权、移除 capabilities，不能看到 sibling governance checkout 或 GitHub command files。pinned workflow 直接执行固定 `node --test --test-reporter=tap`，`verify-node-test-summary.mjs` 再要求精确的最终 test plan/pass/fail/skipped 计数；当前 `website-content-ops` trusted profile 固定为 3 个测试文件和 131/131 全通过，120、130、132 或任意 failed/skipped 都必须 fail-closed。runtime job 输出实际测试的 candidate commit 与 annotated tag object SHA，qualification job 的全新 checkout 通过 `verify-tested-candidate-identity.mjs` 精确比对后再构建，避免 candidate 重定向测试对象、污染后续 builder、替换 npm lifecycle、提前退出伪造空跑，或 tag 在两个 job 之间 retarget；未来新增子库若没有 profile，正式 qualification 必须 BLOCK；
- 对 builder 输出的精确 frozen candidate 执行 qualification，确认 validator 未修改 tree；随后生成以 `content_digest` 命名的确定性 tar.gz 和精确单行 SHA-256 sidecar，解包到独立目录并再次运行 approval/artifact 校验。候选原树、workflow 解包树和 attestation 脚本再次解包树必须用 `sha256-canonical-tree-v1` 得到相同 path/type/mode/size/content/symlink/empty-directory digest。候选包外的 `QUALIFICATION-ATTESTATION.json` 再绑定 candidate tree、archive、approval/evidence、workflow、tag、signer、runtime 状态和精确测试计数，三者一起上传，避免验证对象与下载对象发生 TOCTOU。

所有 `actions/*` 引用固定完整 commit SHA。此 workflow 只产生 qualification artifact，不创建 GitHub Release；Protected Environment、默认分支/正式 tag ruleset、真实 sidecar、可信 signer 和服务端成功 run 仍是仓库外部前置条件；同名 trust anchor 不得在 repository/org scope 作为后备值，首次演练需保存配置快照。

`immutable_locator` 由母库和子库同字节 validator 使用 WHATWG URL 解析：仅允许 HTTPS，拒绝 URL credentials、query/fragment、反斜杠、localhost、IPv4 私网/loopback/link-local、IPv6 loopback/ULA/link-local/site-local/multicast/documentation range、单标签或内部后缀、重复编码 dot segment、`latest/tmp` 与 credential 类 token，并要求路径完整 segment 同时包含 candidate version 和 `content_digest`。WHATWG `URL.hostname` 对 IPv6 可能保留方括号，因此共享网络策略会先规范化再判定；静态检查不解析 DNS，正式下载仍应限制可信 artifact host、解析后地址并校验实际连接地址。

## 最终批准闸门

普通 `working-candidate` 不需要 approval sidecar，并且只证明结构和制品边界。正式 qualification 必须先从 clean tagged commit 冻结候选，再对同一目录运行 artifact release gate：

```bash
SOURCE_DATE_EPOCH=0 node scripts/build-mother-release.mjs --prepare

export RELEASE_APPROVAL_PATH=/external/RELEASE-APPROVAL.json
export RELEASE_EVIDENCE_PATH=/external/RELEASE-EVIDENCE.json
export RELEASE_SOURCE_ROOT=/clean/tagged/checkout
export RELEASE_REQUIRE_GIT_TAG=1
export RELEASE_TRIGGER_TAG=mother/vX.Y.Z
export RELEASE_ACTUAL_TAG_OBJECT_SHA=<actual-tag-object-sha>
export RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT=<verified-full-fingerprint>
export RELEASE_ACTUAL_TAG_ANNOTATION_SHA256=<canonical-annotation-sha256>
export RELEASE_ACTUAL_TAG_ANNOTATION_BASE64=<canonical-annotation-base64>
export RELEASE_ACTUAL_APPROVAL_BINDING_SHA256=<canonical-approval-binding-sha256>

node scripts/validate-release-approval.mjs \
  dist/mother/prepared/vX.Y.Z/<content-digest> \
  "$RELEASE_APPROVAL_PATH" \
  "$RELEASE_EVIDENCE_PATH"

node scripts/validate-artifact.mjs \
  --release \
  dist/mother/prepared/vX.Y.Z/<content-digest>
```

builder 不读取 sidecar，也不修改候选为 approved/qualified；最终 gate 验证外部 sidecar、clean checkout、annotated tag、tag target、commit provenance 和候选 tree immutability。workflow 随后在候选包外生成 `qualified-not-published` attestation。缺任一证据均为 BLOCK；attestation 与本地 PASS 也不等于 GitHub Release 或 Published。
