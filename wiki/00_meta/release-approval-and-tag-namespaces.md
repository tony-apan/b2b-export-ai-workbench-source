---
title: "Release Approval and Tag Namespaces"
description: "定义母库和子库 release approval event 的最小证据字段、source/candidate digest 单向绑定和互不冲突的 Git tag 命名空间。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["release-state-machine.md", "release-checklist.md", "structure-adversarial-review-20260728-final.md"]
related: ["release-state-machine.md", "release-checklist.md", "publishing-and-redaction.md", "sub-library-contract.md", "../../MANIFEST.md", "../../sub-libraries/registry.json"]
visibility: "public"
redaction_status: "safe-to-publish"
confidence: "high"
when_to_read: "需要批准母库或独立子库发布、生成 Git tag，或核对 source commit 与候选包是否同一不可变发布对象时。"
keywords: ["release approval", "approval event", "content digest", "source commit", "Git tag", "tag namespace", "mother library", "sub-library"]
---
# Release Approval and Tag Namespaces

## 目的与边界

本页规定**一次正式 release approval**如何绑定到一个母库或一个子库的不可变候选包，以及该批准如何落到不冲突的 Git tag 上。

- 母库和子库是两个独立 scope：母库的批准不自动批准任何子库；子库的批准也不提升母库状态。
- 本页是治理合同，不修改 `MANIFEST.md` 的状态、不替代 release validator，也不把 `STRUCTURE_PASS` 解释为发布批准。
- 只有 clean source、候选包 release 校验通过、许可和人工批准均已满足时，才可以创建 `approved` event 和正式 tag。

术语：

| 术语 | 定义 |
|---|---|
| source | 生成候选包的 Git source snapshot，由不可变 `source_commit` 标识。 |
| candidate | 已生成、具有 `MANIFEST.json`、`SHA256SUMS` 和 `content_digest` 的独立候选包。 |
| approval event | 对一个精确 source + candidate + 校验证据组合的人工决定记录；它不是 manifest 状态字段。 |
| tag | 指向被批准 source commit 的 annotated Git tag；tag 本身不是候选包内容。 |

## Approval Event 最小字段

每次决定都应保留一个不可变记录。`decision: approved` 才允许创建正式 tag；`rejected` 也应留档，但不得创建正式 tag。

```json
{
  "schema": "release-approval/v1",
  "approval_id": "APR-YYYYMMDD-####",
  "decision": "approved",
  "scope": {
    "kind": "mother-library | sub-library",
    "id": "<candidate MANIFEST.json package_id>",
    "package_kind": "mother-library-release-candidate | sub-library-release-candidate"
  },
  "source": {
    "commit": "<40-character lowercase Git SHA>",
    "dirty": false
  },
  "candidate": {
    "content_digest": "<64-character lowercase SHA-256>",
    "manifest_sha256": "<64-character lowercase SHA-256>",
    "sha256sums_sha256": "<64-character lowercase SHA-256>",
    "immutable_locator": "<release-asset ID or non-local immutable URI>"
  },
  "validation": {
    "profile": "mother-release-v1 | sub-library-release-v1",
    "evidence_digest": "<64-character lowercase SHA-256>",
    "completed_at": "YYYY-MM-DDTHH:MM:SSZ"
  },
  "approval": {
    "approved_by": "<human identity or accountable role>",
    "approved_at": "YYYY-MM-DDTHH:MM:SSZ",
    "basis_ref": "<review, ticket, or signed decision reference>"
  },
  "tag": {
    "name": "<namespace-conformant annotated tag>",
    "target_commit": "<same SHA as source.commit>",
    "object_sha": "<actual annotated tag object SHA>",
    "signer_fingerprint": "<git verify-tag VALIDSIG fingerprint>",
    "annotation_schema": "release-tag-annotation/v1",
    "annotation_sha256": "<canonical annotation bytes SHA-256>",
    "approval_binding_digest_algorithm": "sha256-canonical-approval-binding-v1",
    "approval_binding_sha256": "<stable approval intent projection SHA-256>"
  }
}
```

`validate-release-approval.mjs` 成功时输出 `APPROVAL_RECORD_PASS`：它只证明记录字段与候选包、scope 和 tag 声明一致。`approved_by` 含 AI/system 身份 token 会被阻断，但名称字符串不能证明批准者确为真人；可信身份、签名或独立批准渠道仍是正式发布责任人的外部证据。

以下字段缺失、格式不一致或互相不匹配时，event 不具备批准效力：

1. `scope.id` 必须逐字等于候选包 `MANIFEST.json.package_id`；母库也不能写 `mother-library` 别名，子库不能写目录别名或产品昵称。
2. `source.commit` 与 `tag.target_commit` 必须完全相同，且 `source.dirty` 必须为 `false`。
3. `candidate.content_digest` 必须等于该候选包 `MANIFEST.json` 的 `content_digest`；`manifest_sha256` 和 `sha256sums_sha256` 必须由同一份候选包文件计算。
4. `validation.evidence_digest` 必须指向本次相同 source/candidate 的 release-mode 输出或等价不可变证据，不能复用另一版本的 PASS 日志。
5. `immutable_locator` 只允许 HTTPS；不得包含 URL credentials、query、fragment、反斜杠、localhost/私网/link-local、内部或单标签主机、dot segment、重复编码、`latest/tmp` 或 credential 类 token，且 URL path 必须以完整 segment 同时包含 candidate version 与 `content_digest`。release-mode 最终闸门还会要求 sidecar 路径，并在 clean Git checkout 中验证可信签名 annotated tag 实际存在且解析到 `source.commit`。

## 单向 Digest 绑定：避免循环

候选包必须先冻结，再批准。当前 artifact 合同中：

1. `content_digest` 按 `MANIFEST.json` 的排序 `files` 列表及各文件 SHA-256 计算；它不把 `MANIFEST.json` 或 `SHA256SUMS` 本身作为输入。
2. `SHA256SUMS` 覆盖每个 listed file 和 `MANIFEST.json`；它不覆盖自身。
3. 候选包冻结并完成 pre-tag 检查后，人工 reviewer 先形成批准意图；正式 tag 尚不存在时不能伪造 tag object、annotation digest 或 post-tag evidence。
4. `sha256-canonical-approval-binding-v1` 对稳定批准投影做 canonical JSON 摘要：保留 schema、`approval_id`、decision、scope、source、candidate、validation profile、人工批准字段以及 tag name/target/signer；排除 tag 创建后才产生的 object SHA、annotation digest、approval binding 回填字段和完整 evidence digest，避免自引用循环。
5. signed annotated tag 指向 `source.commit`，message 必须是 `release-tag-annotation/v1` 单行 canonical JSON，精确记录 approval binding digest、`approval_id`、scope、version 与 `candidate.content_digest`。tag 创建后再将实际 object SHA、signer fingerprint、annotation digest 和 tag-signature evidence 写入候选包外的完成记录；它们不得反向成为 candidate 的输入。

因此依赖方向只能是：

```text
clean source commit
  -> prepared-unapproved frozen candidate
  -> pre-tag checks + human approval intent
  -> canonical approval binding digest
  -> signed canonical annotated tag
  -> post-tag evidence + completed approval sidecar
  -> formal qualification
  -> deterministic archive + unpack/revalidate/tree-equivalence attestation
```

不得反向写入：若把 approval event 放进 candidate 的 `files`，该 event 又要写入候选包 digest，就会形成“event 需要 digest、digest 又需要 event”的循环。若任何一个绑定值变化（source commit、任一 candidate digest、验证证据 digest 或 scope），旧 event 失效，必须重新生成 candidate、重新验证并重新批准。

## 独立 Tag Namespace

正式 tag 一律使用 annotated tag，且只能使用以下两个 namespace：

| Scope | 正式 tag 格式 | 示例 |
|---|---|---|
| 母库 | `mother/v<version>` | `mother/v0.1.1` |
| 子库 | `sub-library/<package_id>/v<version>` | `sub-library/website-content-ops/v0.3.2` |

规则：

1. `<package_id>` 必须与子库 `MANIFEST.md` 的 `package_id` 完全一致；不得用显示名称、目录别名或客户名称替代。
2. 一个 tag 名只能指向一个不可变 commit，禁止 force-update、删除后复用或把 `latest` 当正式 tag。
3. 母库 tag 只能引用母库 approval event；子库 tag 只能引用该 `package_id` 的 approval event。即使两者恰好指向同一 source commit，也必须各有自己的 candidate digest、验证证据和批准。
4. tag 的 version 必须与对应 scope 的 version 合同一致；不能用母库版本冒充子库版本，也不能用子库版本代表整个母库。
5. 尚未批准的草稿或候选包不得创建上述正式 namespace 的 tag。需要内部定位时，使用不属于正式 release namespace 的短期引用，并明确标为 non-release。

### 反例与正确做法

| 反例 | 为什么不合规 | 正确做法 |
|---|---|---|
| `v0.3.2` | 不说明母库还是哪个子库，多个 scope 会冲突。 | `sub-library/website-content-ops/v0.3.2`。 |
| `website-content-ops/v0.3.2` | 缺少保留的 `sub-library/` 前缀，无法和未来其他 namespace 一致解析。 | 使用完整子库 namespace。 |
| 用 `mother/v0.1.1` 表示所有子库均可发布 | 母库 approval 不能替代独立子库的 runtime、安装和回滚证据。 | 仅批准母库；需要时为每个通过的子库单独批准和打 tag。 |
| approval event 写入 candidate，再重算 `content_digest` | 会产生循环，并让已批准对象在批准后发生变化。 | event 作为 candidate 外部 sidecar；冻结 candidate 后只做单向引用。 |
| tag 指向批准前后的另一个 commit | source、candidate 与 tag 不再是一条可审计链。 | tag target 必须等于 event 的 `source.commit`。 |
| 在 dirty worktree 生成 candidate 后人工补一个 tag | 不能从 tag 重建同一 source tree，候选包不具备不可变性。 | 从 clean checkout 重建、release 校验、批准后再 tag。 |

## 正式 Workflow 的单 Scope 执行

正式 GitHub gate 使用 `.github/workflows/release-library.yml`，只允许手工 `workflow_dispatch` 输入一个精确 `release_tag` 和一个外部 approval sidecar。`scripts/resolve-release-scope.mjs` 必须先将 tag 严格解析为当前版本的母库或 registry 中唯一子库；母库分支与子库分支互斥，不能在同一次任务中遍历全部 scope。

workflow 先确认从默认分支启动，且 `github.workflow_sha` 与 Environment 级 `FORMAL_RELEASE_TRUSTED_WORKFLOW_SHA` 完全一致；随后分别 checkout trusted governance 和 `refs/tags/<release_tag>` candidate。resolver 只从 trusted checkout 执行，candidate 的母库 scripts、release workflow、sub-library registry 和目标子库 scripts 必须与 trusted governance 一致。

candidate tag 必须是指向当前 `HEAD` 的 signed annotated tag；`git verify-tag --raw` 的有效签名 fingerprint 必须位于 `FORMAL_RELEASE_TRUSTED_TAG_SIGNERS`。两个 job 都必须读取真实 tag object，解析并比较完全相同的 object SHA、signer fingerprint、canonical annotation bytes/digest 与 approval binding digest。sidecar 只在这些检查之后解码到 `$RUNNER_TEMP`，不打印正文；builder 只接收 `--prepare`，不接收 approval/evidence。trusted root approval validator 在 strict 模式下通过环境变量读取 sidecar/evidence 和实际 tag receipt，并确认 approval、evidence、workflow、Git object 与 attestation 是同一 identity。

`immutable_locator` 仅允许 HTTPS，拒绝 credentials、query/fragment、localhost/私网/link-local、dot segment、重复编码及 `latest/tmp` 等可变标记；URL path 必须以完整 segment 包含 candidate version 与 content digest。该静态闸不解析 DNS，下载器仍应配置可信 host allowlist 并校验实际连接地址。

母库没有声明 runtime contract，必须输出 machine-readable `runtime_not_applicable`、固定 reason、空 test plan、零计数和空 image digest，不得虚构母库 runtime tests。目标子库则必须命中 trusted runtime-test profile，并在隔离 runner job 中执行；profile 逐级拒绝 adapter/祖先 symlink，要求 package/lockfile/test 与祖先目录 npm/package-manager 控制文件和 trusted governance 一致，再把显式 allowlist 中的 candidate implementation 与 trusted tests 物化为临时 subject。依赖安装与测试使用 `FORMAL_RELEASE_NODE20_IMAGE_DIGEST` 外部固定的 Node 容器；测试容器只读挂载 subject、禁网、降权且看不到 sibling governance，不接受 candidate `npm test` lifecycle，并校验最终 test plan/pass/fail/skipped 计数；当前 `website-content-ops` trusted profile 精确要求 3 个测试文件与 131/131 全通过；120、130、132 或任意 failed/skipped 都必须 fail-closed。通过后按 content digest 冻结确定性 tar.gz 与严格单行 SHA-256 sidecar，解包后重跑校验；attestation 再次解包并以 `sha256-canonical-tree-v1` 证明三树等价。该 workflow 不创建 GitHub Release。

这套代码仍不能单靠 `approved_by` 字符串证明批准者真人身份。只有 GitHub 仓库侧 Protected Environment required reviewers、默认分支/正式 tag ruleset、外部 pinned SHA、可信签名者和真实服务端 run 共同存在时，身份与不可变性链才成立；`approval_sidecar_base64` 不是 secret。缺任一项时，发布资格继续 BLOCK。

## 执行前自审

创建正式 tag 前，负责人必须确认：

- [ ] approval event 的 scope、package kind、source commit 和 tag target 一致。
- [ ] `source.dirty: false`，候选包不是从未提交工作树构建。
- [ ] candidate 的 `content_digest`、manifest hash、checksum hash 与 event 完全一致。
- [ ] release-mode validator 证据属于这一个 candidate，而非历史或相邻 scope。
- [ ] `license_status`、来源授权和人工批准已经满足对应 scope 的发布条件。
- [ ] tag 名符合本页 namespace，且不存在同名 tag 的重用或 retarget。
- [ ] event 与 tag annotation 未被写回候选包内容，因而不存在 digest 循环。

满足以上条件只是形成可审计的 approval 链；真实发布后的安装、升级、卸载、回滚与外部渠道验收仍按对应 runtime contract 和 release checklist 另行记录。
