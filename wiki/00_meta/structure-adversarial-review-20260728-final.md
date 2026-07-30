---
title: "Final Structure and Independent Release Adversarial Review"
description: "母库与 website-content-ops 子库完成结构升级后的最终对抗审查、证据、阻断和残余风险。"
type: "adversarial-review"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["Local repository validation 2026-07-28", "Mother and sub-library release candidates 2026-07-28", "Five independent adversarial review tracks"]
related: ["../../MANIFEST.md", "../../RELEASE.md", "../../scripts/validate-mother-library.mjs", "../../scripts/build-mother-release.mjs", "../../sub-libraries/README.md", "../../sub-libraries/website-content-ops/MANIFEST.md", "../../sub-libraries/website-content-ops/RELEASE.md", "../../sub-libraries/website-content-ops/scripts/validate-sub-library.mjs", "../../sub-libraries/website-content-ops/scripts/build-release.mjs", "structure-adversarial-review-20260728.md", "decision-log.md"]
visibility: "public"
redaction_status: "safe-to-publish"
release_status: "BLOCK"
---
# Final Adversarial Review

## 结论先行

本轮已经把“目录结构正确”升级为两条可以分别生成、分别校验、分别保留状态的发布线，但**目前仍不能对外宣称母库或子库稳定发布**。

| Scope | 结构检查 | 候选包 | 清洁复制后校验 | 外部发布 | 当前阻断 |
|---|---|---|---|---|---|
| 母库 | `STRUCTURE_PASS` | `dist/mother/latest` 已生成 | `STRUCTURE_PASS` | `BLOCK` | 许可证、人工批准、干净 Git snapshot 尚未完成 |
| `website-content-ops` | `STRUCTURE_PASS` | `dist/latest` 已生成 | `STRUCTURE_PASS` | `BLOCK` | 许可证、跨环境/真实最小闭环、Skill 安装批准尚未完成 |

`STRUCTURE_PASS` 只代表当前源码或候选目录通过静态合同，不等于 `Ready`、`Published` 或产品级稳定。

## 本轮已完成的升级

### 1. 子库真正停止反向依赖母库本地路径

新增：

- `sub-libraries/website-content-ops/REFERENCES/README.md`
- `sub-libraries/website-content-ops/REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md`
- `sub-libraries/website-content-ops/REFERENCES/SRC-20260727-ALLINCMS-OFFICIAL.md`

已将子库 front matter 的来源路径改为子库内部引用，并修复 `fixtures/README.md` 的断链。子库 validator 现在检查 Markdown 正文链接、front matter `sources` / `related`、路径是否越出子库根目录和条件性 `skill_entrypoint`。

### 2. 母库与子库都有真实构建入口

母库：

```bash
node scripts/validate-mother-library.mjs
node scripts/build-mother-release.mjs
```

子库：

```bash
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
node sub-libraries/website-content-ops/scripts/build-release.mjs
```

两条构建线都会：

```text
源码校验 → latest-only 目录复制 → MANIFEST.json → SHA256SUMS → 候选目录再次校验
```

母库候选包为 `dist/mother/latest/`；子库候选包为 `sub-libraries/website-content-ops/dist/latest/`。`dist/` 已加入 `.gitignore`，不作为源码或发布状态的隐式来源。

### 3. 机器可读的包边界

两个 manifest 都有 `include` / `exclude` / `license_status` / `release_status`。构建脚本会对候选包文件逐项检查 include/exclude，不只依赖自然语言说明。

母库只从根入口、`wiki/`、`sub-libraries/`、`scripts/` 和公开 raw 占位复制；子库不携带母库 `wiki/`、`raw/` 或客户运行区。

### 4. 可复现依赖和安装入口

AllinCMS adapter 已生成并提交到源码范围的 `package-lock.json`，并完成：

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

结果：`115 passed, 0 failed`。这只证明当前本地 adapter 测试合同通过，不证明官方 API、跨部署或外部发布通过。

子库新增 `INSTALL.md`，说明复制、升级、回滚和卸载边界。

## 当前证据

### 母库

```text
node scripts/validate-mother-library.mjs
→ STRUCTURE_PASS

node scripts/build-mother-release.mjs
→ RELEASE_CANDIDATE: dist/mother/latest
→ 235 files
→ candidate validator STRUCTURE_PASS
→ SHA256SUMS 231 entries, bad=0
```

### 子库

```text
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ STRUCTURE_PASS

node sub-libraries/website-content-ops/scripts/build-release.mjs
→ RELEASE_CANDIDATE: sub-libraries/website-content-ops/dist/latest
→ 88 files
→ candidate validator STRUCTURE_PASS
→ SHA256SUMS 86 entries, bad=0
```

### 清洁目录复制

两份候选包已复制到临时目录，从复制后的母库 `README.md`、子库 `README.md` 和各自 validator 重新启动；两者均通过结构检查，且没有要求读取 Tony 的本机路径。

### 发布闸

以下命令仍应失败：

```bash
node scripts/validate-mother-library.mjs --release
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs --release
```

两者都因 `release_status: BLOCK` 阻断。保留这个阻断是正确结果。

## 仍然阻断发布的事项

1. **最终许可证未由 owner 决定**：当前两个 manifest 为 `license_status: pending`。去敏通过不等于获得复制、修改、商用或二次发布授权。
2. **当前工作树未形成干净、可追溯的 Git commit/tag**：本轮没有提交、推送或改变远程可见性，不能把本地候选包说成已经发布。
3. **真实独立运行证据仍有限**：AllinCMS 是登录限定、部署限定的 adapter 观察证据，不得泛化为官方通用 API 或跨部署稳定。
4. **Skill 仍是草案**：`SKILL.md` 已有宿主规则优先声明，但尚未完成跨宿主安装、升级、卸载、回滚和用户验收，因此不能称为稳定可安装 Skill。
5. **第三方素材授权仍需人工确认**：来源卡保留官方 URL 和边界，但不自动替代版权、商标、课程原文、图片和截图授权判断。
6. **同步防漂移目前是“有闸门但非全自动”**：validator 已检查当前子库版本、状态、wiki canonical entry 和关键入口；新增第二、第三个子库时仍需把注册表解析和每个子库 smoke test 纳入 CI。

## 对抗复审后的再次加固（2026-07-28）

三条独立复审均返回 `BLOCK` 后，继续完成以下修复：

1. 构建器现在真正执行 manifest `include` / `exclude`，跳过 `.git`、`.obsidian`、`node_modules`、`dist` 和敏感目录；使用 staging 目录，只有候选包验证、artifact validator 和 checksum 全通过后才原子替换 `latest`。
2. 新增母库与子库各自的 `scripts/validate-artifact.mjs`，检查 `MANIFEST.json`、文件集合、`SHA256SUMS`、嵌套 `dist` 和候选包内嵌结构 validator；母库 validator 自动发现 `sub-libraries/` 下的每个一级子库并检查注册表入口。
3. 修复子库中的母库布局路径文字和 standalone 占位路径；来源注册表与授权登记表已覆盖当前来源 ID，未确认来源明确标记为 `needs-approval`。
4. 如实声明 AllinCMS adapter 的 Node.js / npm / `sharp` 依赖；`sharp` 升级至 `0.35.3`，115 项本地测试通过，当前 `npm audit --omit=dev` 为 0 个漏洞。

加固后的最新证据：

```text
母库：236 个文件总数，235 条 checksum（MANIFEST.json 不计入 checksum），artifact validator PASS
子库：88 个文件总数，87 条 checksum（MANIFEST.json 不计入 checksum），artifact validator PASS
源目录与候选包逐文件 SHA256 差异：0
临时清洁目录复制后：母库和子库 artifact validator 均 PASS
```

本节的 `PASS` 仍只代表结构、打包完整性和本地静态证据；许可证、人工批准、真实独立运行和发布状态仍保持 `BLOCK`。

## 最终发布规则

- 母库 `Ready` 不代表任何子库 `Ready`。
- 子库 `Ready` 不代表母库 `Ready`。
- `Draft` / `BLOCK` 可以作为源码候选继续维护，不能当稳定产品发布。
- 只有在许可证、干净 checkout、候选包、清洁目录复现、目标用户最小流程、失败/回滚和人工批准均有证据后，才能把对应 scope 的 `release_status` 改为 `Ready`。
- 任何真实客户运行数据、账号、Cookie、Token、生产配置、私有 raw 和未授权素材都不得进入母库或公开子库。

## 最终判定

```text
结构方向：PASS
母库源码候选：PASS
子库源码候选：PASS
母库独立候选包：PASS（仍为 BLOCK 状态）
子库独立候选包：PASS（仍为 BLOCK 状态）
母库外部稳定发布：BLOCK
子库外部稳定发布：BLOCK
```

## 2026-07-28 Final Addendum：第三轮 agent 后续复核

本节覆盖三轮独立对抗审查后的本地复核结果；它比上文早期候选包统计更近。旧统计保留作为历史证据，不作为当前文件数真源。

### 本次复核命令与结果

```text
node scripts/validate-mother-library.mjs
→ STRUCTURE_PASS

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ STRUCTURE_PASS

node scripts/build-mother-release.mjs
→ RELEASE_CANDIDATE: dist/mother/latest
→ 236 files total
→ SHA256SUMS: 235 entries, bad=0
→ candidate artifact validator PASS

node sub-libraries/website-content-ops/scripts/build-release.mjs
→ RELEASE_CANDIDATE: sub-libraries/website-content-ops/dist/latest
→ 88 files total
→ SHA256SUMS: 87 entries, bad=0
→ candidate artifact validator PASS

node scripts/validate-artifact.mjs dist/mother/latest
→ ARTIFACT_PASS

node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
→ ARTIFACT_PASS

cd sub-libraries/website-content-ops/ADAPTERS/cms/allincms && npm test
→ 115 passed, 0 failed

npm audit --omit=dev
→ 0 vulnerabilities
```

### 可复现构建复核

使用 `SOURCE_DATE_EPOCH=0` 连续构建两次：

- 母库 `MANIFEST.json` SHA-256：`65b6b7a5c53ba1b49ab303e61c08b0fe64713df2f6122822453ddcc1e7f03ff3`，两次一致；
- `website-content-ops` `MANIFEST.json` SHA-256：`84abf7ec280c98fe90fe14355b8e844d3678545bd4bf9837b157a19d56cfad9b`，两次一致；
- 两个候选包的逐文件 SHA-256 清单两次一致；
- 构建完成后未遗留 `.staging-*` 或 `.previous-*` 目录。

这证明当前构建脚本在固定时间输入下具有可复现性；不等于源目录已经形成经批准的 Git release snapshot。

### 发布闸复核

```text
node scripts/validate-mother-library.mjs --release
→ exit 1，因 release_status 仍为 BLOCK

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs --release
→ exit 1，因 release_status 仍为 BLOCK
```

这是预期的安全失败，不是结构回归。

### 三轮 agent 的最终交叉结论

1. **母库轨**：可脱离父目录构建和校验；当前为 `source-index`，可以发布源码索引候选，但不能把 BLOCK 子库包装成稳定组件。
2. **子库轨**：`website-content-ops` 可脱离母库目录复制、安装和运行本地 adapter 测试；跨部署、真实失败恢复、完整回滚和稳定 Skill 安装仍无充分证据。
3. **治理轨**：`sub-libraries/registry.json` 已成为机器可读唯一注册表，版本、状态、许可证字段已做一致性校验；但新增子库的 CI 自动注册、自动同步、唯一来源授权闭环仍未完成。

### 本轮不改变的阻断

- 未选择最终许可证；
- 第三方来源、图片、课程/截图等授权仍需 owner 或权利人确认；
- 未创建 commit、tag、push 或正式 release snapshot；
- 未完成第二环境/第二部署的完整安装、升级、回滚和用户验收；
- `SKILL.md` 仍是 `draft-adapter-not-installable`，不得称为稳定可安装 Skill；
- 当前公开远程条件下，真实客户运行区、账号、Cookie、Token、私有 raw 和生产配置仍不得进入母库或子库。

因此最终状态保持：

```text
结构升级：PASS
母库候选包：PASS
子库候选包：PASS
可复现构建：PASS
本地 AllinCMS adapter：PASS
母库正式外部发布：BLOCK
website-content-ops 正式外部发布：BLOCK
稳定 Skill 发布：BLOCK
```

### 当前清洁目录复现补充

本次重新复制到全新临时目录后执行母库和子库 validator，均返回 `STRUCTURE_PASS`；对两份复制包扫描常见用户目录、临时目录和运行目录的本机路径模式，结果为 `LEAK_SCAN_PASS`。临时目录本身不属于发布包，也未被写回仓库。

## 2026-07-28 Continuation Verdict Addendum

本次继续推进后的当前快照，以本节证据覆盖前文较早的候选包数量；前文数字保留为历史复核记录，不再作为当前数量真源。

### 当前数量与验证

| Scope | Version | Current artifact evidence | Result |
|---|---:|---|---|
| Mother | `0.1.1-draft` | `MANIFEST.json` 239 files；`SHA256SUMS` 240 entries；连续固定时间构建 hash 一致 | `STRUCTURE_PASS` + `ARTIFACT_PASS` |
| `website-content-ops` | `0.3.2-draft` | `MANIFEST.json` 87 files；`SHA256SUMS` 88 entries；连续固定时间构建 hash 一致 | `STRUCTURE_PASS` + `ARTIFACT_PASS` |

### 继续对抗后新增的阻断说明

- 母库 builder 现在对 child manifest 的 include/exclude 进行双向语义比较；两组人为制造的不一致均以 exit 1 阻断。
- 根库与子库都提供了显式的 `LICENSE.md` 状态声明，但声明本身不是授权；两个 manifest 仍为 `license_status: pending`。
- 来源登记表增加审批 owner、证据引用和决定日期字段，当前未填审批事实，因此不能把 `needs-approval` 解释成 cleared。
- CI 已从单一硬编码子库改为读取 registry 构建所有注册子库，并在 tag 上执行母库和所有子库的 release gate；尚未有远程 CI 执行记录。

### 最终 verdict

```text
母库结构：PASS
子库结构：PASS
registry 防漂移：PASS
母库/子库发布边界：PASS（含双向负向测试）
候选包完整性：PASS
固定时间可复现构建：PASS
独立临时目录校验：PASS
当前 AllinCMS adapter 本地测试：PASS（115/115，限定当前本地合同）
母库正式外部发布：BLOCK
website-content-ops 正式外部发布：BLOCK
稳定 Skill 发布：BLOCK
```

当前最短安全路径仍是：**先关闭许可证与来源授权 → 在 clean checkout 生成不可变 artifact → 补第二环境安装/升级/故障/回滚证据 → 独立 reviewer 留档 → owner 批准 → 只对对应 scope 创建 tag 和发布。** 不得因为结构闸通过而提前修改 `release_status`。

### Provenance gate addendum

两个候选包的 `MANIFEST.json` 已纳入 `source_commit`、`source_dirty` 和 `content_digest`，并由对应 artifact validator 校验。当前均记录 `source_dirty: true`，因此本轮仍不能形成不可变正式发布快照；这把“当前包来自哪个 commit、内容是否发生变化、是否在 dirty worktree 生成”从口头说明提升为制品字段，但没有替代 clean checkout、独立 review record、tag 和 owner approval。


## Final recheck addendum — 2026-07-28 closure continuation

本次逐项对抗后，以下结果覆盖旧的计数和旧候选包数字：

- **Document ID**：`DOCUMENT_ID_PASS`；当前 `markdown=264`、`numbered=4`、`legacy=41`。`ID-0001` 迁移样本、`ID-0002` concept、`ID-0003` playbook、`ID-0004` course 已被识别；`VER-` / `WB-` / `redirect` 记录不计入 durable legacy。
- **Index / link**：`INDEX_VALIDATION_PASS`；修复课程 verification/writeback 记录中的 7 条错误相对路径，所有生成索引通过 stale 检查。
- **Knowledge chain**：`KNOWLEDGE_CHAIN_PASS`；raw 已移除提炼性 `Extraction Boundary`，补齐来源/采集/敏感/同意/派生/验证字段；source note 的 `derived_pages` 已覆盖 concept、playbook、course、verification、writeback。
- **Raw release boundary**：候选包默认排除 raw source，仅显式 allowlist 的 synthetic fixture 同时在 `.gitignore`、`MANIFEST.md`、`build-mother-release.mjs` 放行；母库候选包实际包含 294 个文件、293 条 checksum，artifact 校验通过。
- **Mother / sub-library**：母库和 `website-content-ops` 均 `STRUCTURE_PASS`；子库候选包为 100 个文件、99 条 checksum，artifact 校验通过。
- **Remaining BLOCK**：课程第二场景为 `assigned-not-submitted`，尚无学员提交与人工评分；许可证仍为 pending，clean Git snapshot / 独立环境复现、人工批准、真实运行与外部发布证据未完成；母库和子库 `release_status` 必须继续保持 `BLOCK`。

这次闭环只证明本地结构、候选包边界、synthetic 文件链和静态验证结果；不把它外推为真实客户、真实教学效果、生产能力或许可证批准。


## 2026-07-28 Final Addendum 2：第四轮逐项对抗与制品边界加固

本节是当前状态的真源；上文早期候选包文件数只保留为历史记录，不覆盖本节的现场复核结果。

### 本轮实际完成的修复

1. **README-only canonical 规则落地**：知识目录继续使用 `index.md`；子库、脚本、adapter、模板、运行区和发布目录使用 `README.md` 时，必须在元数据中写 `canonical_entry: "README.md"`。不再允许同级出现第二个 `INDEX.md`、`index.md` 或平行注册表。
2. **编号页闸门收紧**：母库与子库 durable root 内的 `id-####-slug.md` 必须有匹配的 `doc_id: "ID-####"`；缺失、格式错误或重复会直接 `BLOCK`。母库与子库编号 scope 隔离，legacy 页面只报告迁移债务，不批量重命名。
3. **子库独立发布进一步解耦**：`website-content-ops` 的 `durable_roots`、内部模板、独立 ID 校验器和候选包 validator 均在子库内；候选包不依赖母库脚本路径，来源摘要放在子库自己的 `REFERENCES/`。
4. **制品级安全复验加固**：母库和子库 `validate-artifact.mjs` 在 checksum 之外再次检查本地绝对路径、明显凭据赋值模式和禁止的二进制扩展；CI 在构建母库和每个子库后执行 artifact boundary validator，而不是只校验源码。
5. **负向测试已验证**：人为创建缺少 `doc_id`、缺少 `when_to_read`、关键词数量不足的 durable page 时，子库 validator 正确阻断；测试文件已删除，未污染工作树内容。

### 当前现场证据（2026-07-28）

```text
node scripts/sync-indexes.mjs
→ INDEXES_SYNCED: 49

node scripts/validate-document-ids.mjs
→ DOCUMENT_ID_PASS: mother numbered=4, legacy=41

node scripts/validate-document-ids.mjs --scope sub-library:website-content-ops
→ DOCUMENT_ID_PASS: sub-library numbered=0, legacy=0

node scripts/validate-indexes.mjs --check
→ INDEX_VALIDATION_PASS: markdown=265

node scripts/validate-knowledge-chain.mjs
→ KNOWLEDGE_CHAIN_PASS

node scripts/validate-mother-library.mjs
→ STRUCTURE_PASS（并明确警告 release_status=BLOCK、license=pending）

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ STRUCTURE_PASS（并明确警告 release_status=BLOCK、license=pending）

node scripts/build-mother-release.mjs
→ ARTIFACT_PASS；FILES=296；SHA256SUMS=295 entries；bad=0；STATUS=BLOCK

node sub-libraries/website-content-ops/scripts/build-release.mjs
→ ARTIFACT_PASS；FILES=101；SHA256SUMS=100 entries；bad=0；STATUS=BLOCK

node scripts/validate-artifact.mjs dist/mother/latest
→ ARTIFACT_PASS

node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
→ ARTIFACT_PASS

git diff --check
→ PASS
```

候选包 `MANIFEST.json` 当前都记录 `source_dirty: true`，且两个 scope 的 `release_status: BLOCK`、`license_status: pending`；因此 `--release` 的安全失败仍是预期结果：

```text
node scripts/validate-mother-library.mjs --release
→ exit 1：clean Git worktree 与 Ready/Published 状态缺失

node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs --release
→ exit 1：clean Git worktree 与 Ready/Published 状态缺失
```

候选包边界扫描结果：

- 母库与子库候选包均未发现实际用户目录、系统临时目录或其它本机绝对路径；
- 未发现凭据赋值、私钥头或真实账号值；
- 候选包不含 PNG/JPG/PDF 等禁止二进制；源码中仍保留一张明确标记 `Not for publication` 的虚拟 PNG fixture，builder 会排除它，不能把源码 checkout 当发布包；
- 母库 raw 候选内容仍限于公开入口、模板和明确标记的 synthetic fixture，真实客户 raw、客户运行区和凭据不在候选包内。

### 四条独立对抗轨的统一判定

| 对抗轨 | 判定 | 结论 |
|---|---|---|
| 母库索引与治理 | `PASS`（发布前范围） | canonical、description、when_to_read、keywords、ID scope 和生成区可验证；legacy 迁移债务仍为 WARN。 |
| 子库独立性 | `PASS`（发布前范围） | 可从自身 README、MANIFEST、AGENTS、START-HERE 和内部 validator 启动；不等于跨环境稳定运行。 |
| 候选包安全边界 | `BLOCK`（发布范围） | 普通结构与 checksum PASS，但 dirty source、license pending、release BLOCK 直接阻断外部发布。 |
| raw→course→verification→writeback | `PASS`（静态范围） | 链路可追溯；synthetic fixture 和 assigned-not-submitted 不能证明真实教学效果。 |

### 不得被误读的最终状态

```text
结构校验：PASS
索引与 ID：PASS（legacy migration debt = WARN）
知识链静态一致性：PASS
候选包完整性与 checksum：PASS
候选包去敏扫描：PASS（当前扫描范围）
母库外部发布：BLOCK
website-content-ops 外部发布：BLOCK
真实跨环境运行：未证实 / BLOCK
课程真实迁移效果：未验证 / BLOCK
许可证与人工发布批准：待 owner 决定 / BLOCK
```

### 下一闭环（按 scope 分开，不跨 scope 借证据）

1. 先由 owner 处理母库和子库各自的许可证、第三方来源和素材授权。
2. 在不改动当前 `BLOCK` 的前提下保存本轮源码变更；经批准后形成 clean commit/tag，再重新构建两个候选包，确认 `source_dirty: false`。
3. 分别在干净目录复制母库包和子库包，从各自 `README.md` 开始完成最小阅读、安装、失败停止、恢复/回滚和写回验收。
4. 若要交付 `SKILL.md`，额外完成宿主安装、升级、卸载、回滚和用户验收；子库本体与 Skill 状态分开记录。
5. 人工批准后才把对应 scope 的 `release_status` 改为 `Ready` 或 `Published`；本轮不做该变更，不 commit、不 push、不发布。

## Final Addendum 3 — 2026-07-28 strict state-machine and traceability hardening

### Scope

本轮由三个独立对抗轨复核并落地：索引检索质量、日志事件 schema、raw → course 证据状态机。没有修改许可证、没有把 `BLOCK` 改为 `Ready`/`Published`，没有 commit、push 或外部发布。

### New machine gates

1. `scripts/validate-indexes.mjs --strict`：canonical / registry 入口至少有 3 个检索词；durable page 的 `doc_id`、`description`、`when_to_read` 和 3–8 个关键词仍是硬闸；raw/index、模板、日志、verification/writeback 记录按类型豁免关键词数量。
2. `scripts/validate-logs.mjs`：日日志事件 ID、日期/路径一致性、重复 ID 和 `actor/scope/action/evidence/result/risk/next/commands/files changed/writeback` 字段可机器复核。当前 2026-07-28 日志 9 个事件、0 warnings。
3. `scripts/validate-knowledge-chain.mjs`：扫描 conversations、web、documents、media、exports 五类 raw 入口；校验 synthetic/consent/source_kind 组合；verification/writeback 必须有事件引用和 snapshot 指针；普通模式只输出结构通过，`--release` 对练习提交、reviewer、真实效果和证据缺口 fail-closed。
4. 根 `AGENTS.md`、`CLAUDE.md`、`README.md` 和 tag release CI 已同步这些命令；生成索引仍由 `sync-indexes.mjs` 统一维护。

### Current evidence

```text
node scripts/validate-logs.mjs
→ LOG_VALIDATION_PASS: daily_logs=1 events=9 warnings=0 failures=0

node scripts/validate-indexes.mjs --strict
→ INDEX_VALIDATION_PASS: markdown=265

node scripts/validate-knowledge-chain.mjs
→ KNOWLEDGE_CHAIN_STRUCTURE_PASS: 3 warnings for human exercise/reviewer/real-world effectiveness

node scripts/validate-knowledge-chain.mjs --release
→ BLOCK: release evidence incomplete (expected while exercise, reviewer and real-world verification are incomplete)
```

### Final judgment

- **PASS**：索引可发现性、日志 schema、raw 分类扫描、synthetic 边界、事件/快照指针、母库/子库静态结构和普通候选包完整性。
- **WARN**：41 个 legacy durable page 仍未完成渐进编号；课程 synthetic fixture 仍未完成真人练习提交、人工 reviewer 和真实效果验证。
- **BLOCK**：母库与 `website-content-ops` 外部发布、稳定 Skill 交付、许可证、clean Git provenance、跨环境复制运行、失败恢复/回滚和人工批准。

本轮把“文件存在”提升为“字段、状态和反向证据可复核”，但没有把结构 PASS 误写成教学、运行或发布 PASS。


## Final Addendum 4 — 2026-07-28 local-link and scope-boundary hardening

### 独立攻击面

此前索引、文件元数据和候选包 checksum 已通过，但仍存在一个容易被“文件存在”掩盖的风险：文档可能链接到已被 manifest 排除的路径，或子库文档越过自身根目录引用母库路径。仅靠索引同步和 checksum 不能证明复制后的 standalone 包仍可导航。

### 已落地修复

- 新增 `scripts/validate-links.mjs`，母库和子库各自携带一份，不依赖母库私有路径。
- 普通模式报告 warning；`--release` 对断链和 scope 外本地路径 fail-closed。
- 母库/子库结构 validator 在源码和候选包复制后都会调用链接闸门。
- tag release CI 先运行母库链接 release gate；子库链接检查由各自 validator 继承执行。

### 当前证据

```text
node scripts/validate-links.mjs --release
→ LINK_VALIDATION_PASS: markdown=265 links=969

node sub-libraries/website-content-ops/scripts/validate-links.mjs --release sub-libraries/website-content-ops
→ LINK_VALIDATION_PASS: markdown=81 links=194

母库 dist/mother/latest：LINK_VALIDATION_PASS，265 Markdown / 969 links
子库 dist/latest：LINK_VALIDATION_PASS，81 Markdown / 194 links
隔离注入 missing.md：退出码 1，准确报告 1 个 BLOCK
```

### 对抗结论

- **PASS**：当前源码和两个 latest-only 候选包不存在已发现的本地断链或 scope 外本地路径。
- **WARN**：外部 URL、标题锚点、许可证、真实工具运行和人工阅读仍不由该脚本证明。
- **BLOCK**：母库与 `website-content-ops` 外部发布仍受 `release_status: BLOCK`、许可证 pending、工作树 dirty、人工批准和独立运行/回滚证据阻断。

### Final Addendum 4 follow-up — release mode propagation

对抗复核又发现一个闸门语义风险：如果父级 `validate-mother-library.mjs --release` 或子库 `validate-sub-library.mjs --release` 调用链接检查时仍使用普通模式，断链可能只成为 warning。现已按父命令模式传递 `--release`，因此直接 release gate 与独立 `validate-links.mjs --release` 的严格程度一致。当前两套 release gate 仍按预期因 clean worktree 和 `release_status: BLOCK` 阻断。

## Final Addendum 5 — 2026-07-28 standalone install and rollback rehearsal

### 独立运行证据

在不依赖母库路径的临时目录中复制 `sub-libraries/website-content-ops/dist/latest` 后，候选包自身的 artifact 和本地链接校验均通过。随后在同一份隔离候选包内执行：

```text
npm ci --ignore-scripts --no-audit --no-fund
→ added 9 packages

npm test
→ tests 115
→ pass 115
→ fail 0
```

这把之前仅有源码工作树的 AllinCMS 本地测试，推进为“从 latest-only 候选包重新安装依赖后测试”的独立目录证据。

### 回滚攻击

在临时目录保留一份上一份已验收目录，模拟升级包被篡改：向当前候选包的 `README.md` 追加内容后，`validate-artifact.mjs` 以退出码 `1` 阻断；随后切换回上一份目录，artifact 校验重新通过。

结论：

- **PASS（机械边界）**：候选包复制、依赖安装、115 项本地 adapter 测试、checksum 发现篡改、恢复上一份已验收目录。
- **WARN（运行证据）**：尚未证明跨部署 CMS、客户 workspace 数据迁移、版本升级兼容性和真实凭据审批。
- **BLOCK（外部发布）**：母库和 `website-content-ops` 仍是 `release_status: BLOCK`；许可证仍 `pending`；工作树仍 dirty；课程 release 仍缺人工练习、reviewer 和真实效果证据。

本 addendum 不改变任何发布状态，也不把本地 adapter 测试误写成真实远程或跨环境稳定性证明。

## Final Addendum 6 — 2026-07-28 release fail-closed and artifact allowlist hardening

### 攻击面

上一轮已经证明普通候选包可构建、checksum 可校验、独立目录可安装，但仍有三个代码级风险：

1. `build-*-release.mjs --release` 在构建前只跑普通结构校验，可能把 release 失败推迟到 staging 之后；
2. artifact 校验没有在候选包根目录独立执行完整 release 集合；
3. 仅阻断已知二进制扩展名，未知文件类型可能被遗漏。

### 已落地修复

- 母库和 `website-content-ops` 的 release 构建在源码阶段、staging 结构阶段和 staging artifact 阶段都传递 `--release`。
- 只有 staging 所有闸门通过后才执行 `latest` 替换；失败时清理 staging，旧 `latest` 保持不变。
- 母库 artifact 在 `--release` 下独立运行 `validate-indexes --strict`、`validate-links --release`、`validate-logs --release`、`validate-knowledge-chain --release` 和 `validate-mother-library --release`。
- 子库 artifact 只运行自身实际携带的 `validate-links --release`、`sync-workspace-template --check` 和 `validate-sub-library --release`，避免把母库脚本假定为 standalone 依赖。
- 两份 artifact validator 采用扩展名白名单：`.md`、`.json`、`.mjs`、`.yml`、`.yaml`，另显式允许 `.gitignore`；未知扩展名默认 BLOCK。

### 当前证据

```text
node --check scripts/build-mother-release.mjs
node --check sub-libraries/website-content-ops/scripts/build-release.mjs
node --check scripts/validate-artifact.mjs
node --check sub-libraries/website-content-ops/scripts/validate-artifact.mjs
→ SYNTAX_PASS

node scripts/build-mother-release.mjs
→ RELEASE_CANDIDATE: dist/mother/latest
→ 299 files, 298 SHA256SUMS, STATUS: BLOCK

node sub-libraries/website-content-ops/scripts/build-release.mjs
→ RELEASE_CANDIDATE: sub-libraries/website-content-ops/dist/latest
→ 102 files, 101 SHA256SUMS, STATUS: BLOCK

node scripts/validate-artifact.mjs dist/mother/latest
node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
→ 两者均 ARTIFACT_PASS

临时副本将已登记的 probe.docx / unexpected.txt 加入 manifest 并重算 content_digest 与 SHA256SUMS
→ 母库与子库均 exit 1，准确命中 unsupported artifact file extension

node scripts/build-mother-release.mjs --release
node sub-libraries/website-content-ops/scripts/build-release.mjs --release
→ 两者均 exit 1；原因是当前 dirty worktree 与 manifest BLOCK；旧 latest digest 不变；无残留 staging

node scripts/validate-artifact.mjs --release dist/mother/latest
→ 完整 release 集合已执行；knowledge-chain、clean provenance 和 BLOCK 状态仍阻断

node sub-libraries/website-content-ops/scripts/validate-artifact.mjs --release sub-libraries/website-content-ops/dist/latest
→ standalone 可用 release 集合已执行；clean provenance 和 BLOCK 状态仍阻断
```

### 对抗结论

- **PASS（机械闸门）**：release 构建提前失败、staging 不污染 `latest`、普通候选包完整性、未知扩展名 fail-closed、母库/子库 artifact release 集合独立执行。
- **WARN**：外部 URL 和标题锚点未由本地链接脚本抓取验证；41 个 legacy durable page 尚未渐进编号；未来扩展二进制制品需要逐文件授权与扫描；母库/子库 tag namespace 和 approval event/digest 绑定仍是治理增强项。
- **BLOCK（不能发布）**：母库和 `website-content-ops` 的 `release_status` 仍为 `BLOCK`，许可证仍 `pending`，工作树仍 dirty；课程 release 证据不完整；真实 CMS 跨部署、失败恢复、客户 workspace 升级兼容和最终人工批准未闭合。

本 addendum 只证明本轮代码级发布闸门已加固，不改变任何 manifest 状态，也不把普通结构 PASS、候选包 PASS 或本地 115 项 adapter 测试升级成正式发布批准。

## Final Addendum 7 — 2026-07-28 approval event binding and tag namespace isolation

### 新攻击面

前一轮已把结构、artifact、checksum、独立安装和 fail-closed 构建闸门补齐，但仍存在两类容易被“绿灯”掩盖的风险：

1. `STRUCTURE_PASS` / `ARTIFACT_PASS` 可能被误读为人工发布批准；
2. 母库和子库如果共用裸 `v<version>` tag，或把一个 scope 的批准记录复用于另一个 scope，可能发生错误发布和溯源串线。

### 已落地修复

- 新增母库和子库各自携带的 `scripts/validate-release-approval.mjs`，最终批准使用旁路 `RELEASE-APPROVAL.json`，不参与候选包 `content_digest`，从根源上避免批准记录自摘要循环。
- 批准校验器要求：候选包 `Ready/Published`、`license_status: cleared`、`verification_status: e2e-pass`、`source_dirty: false`、40 位 commit、真实人工 reviewer、UTC 时间、scope/package/version 一致，以及四项摘要绑定：`source_commit`、`content_digest`、`MANIFEST.json` SHA-256、`SHA256SUMS` SHA-256。
- 固化并在 manifest、registry、构建产物和文档中同步 tag 规则：母库 `mother/v<version>`；子库 `sub-library/<package_id>/v<version>`。
- `approval_status` 当前为 `pending`，因此新增机制不会绕过既有 BLOCK。

### 对抗证据

```text
node scripts/validate-mother-library.mjs
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ 两者 STRUCTURE_PASS；仅输出 approval pending WARN

node scripts/build-mother-release.mjs
node sub-libraries/website-content-ops/scripts/build-release.mjs
→ 两者普通候选包和 artifact 校验通过；制品 MANIFEST.json 已携带 approval/tag 字段

node scripts/validate-release-approval.mjs dist/mother/latest /missing/RELEASE-APPROVAL.json
→ exit 1，缺失 approval record 被 BLOCK

临时 synthetic candidate：显式设置 Ready / cleared / e2e-pass / source_dirty=false，绑定四项摘要并使用人工 reviewer 测试身份
→ APPROVAL_PASS；仅证明校验器逻辑，绝不构成真实人工批准
```

### 最终判断

- **PASS（治理机械层）**：批准事件与精确候选包摘要绑定；母库/子库 scope、package、version 和 tag namespace 不能串线；dirty source、AI/system 假 reviewer、缺失或错误摘要会阻断。
- **WARN**：真实人工 reviewer、许可证清除、clean commit/tag、跨环境运行、CMS 失败恢复、客户 workspace 升级和课程真人效果仍未提供证据；外部 URL/锚点也仍未由本地脚本抓取验证；41 个 legacy durable page 继续按修改渐进迁移。
- **BLOCK（当前不能发布）**：两个 manifest 仍为 `release_status: BLOCK`、`license_status: pending`、`approval_status: pending`；工作树 dirty；课程 release、真实跨部署 CMS、失败恢复和最终人工批准仍未闭合。

本 addendum 只证明批准治理的机器闸门已经落地，不把 synthetic approval、普通候选包通过或本地测试通过写成正式发布批准。

## Final Addendum 8 — 2026-07-28 approval locator false-positive repair and full recheck

### 新发现

对上一轮批准校验器的 synthetic pass 进行真实复跑时发现：`immutable_locator` 的拒绝正则把任意包含 `s:/` 的 URL 协议片段误判为 Windows 本地路径。结果是合法的不可变 HTTPS locator 也无法通过，导致批准机制存在“过度阻断”而不是可用的发布闸门。

### 已落地修复

- 母库与 `website-content-ops` 子库的 `validate-release-approval.mjs` 已统一把本地路径匹配收紧为字符串开头：Unix `/...`、Windows `C:\...` 和 UNC `\\...`；不再把 `https://...` 误判为本地路径。
- `release-state-machine.md` 的批准示例已改为与实际 `release-approval/v1` nested schema 完全一致，删除旧的 `schema_version` / `approval_basis` flat schema。
- `CHANGELOG.md` 中子库 tag 示例已修正为真实合同 `sub-library/<package_id>/v<version>`。
- 两个 scope 的最新候选包已重新构建，旧 `latest` 仅在新候选包全部校验通过后切换。

### 当前验证证据

```text
node --check scripts/validate-release-approval.mjs
node --check sub-libraries/website-content-ops/scripts/validate-release-approval.mjs
→ 两个 validator 均通过语法检查

node scripts/build-mother-release.mjs
→ mother latest：302 files / 301 SHA256SUMS entries；artifact PASS；status BLOCK

node sub-libraries/website-content-ops/scripts/build-release.mjs
→ website-content-ops latest：103 files / 102 SHA256SUMS entries；artifact PASS；status BLOCK

node scripts/sync-indexes.mjs
node scripts/validate-indexes.mjs --check
node scripts/validate-indexes.mjs --strict
node scripts/validate-links.mjs --release
node scripts/validate-logs.mjs --release
→ indexes 266 markdown PASS；links 266 markdown / 971 links PASS；logs 1 daily log / 15 events PASS

node scripts/validate-document-ids.mjs
→ 4 个已编号 durable page；41 个 legacy page 仅为迁移 WARN，无重复或格式错误

node scripts/validate-knowledge-chain.mjs --release
→ 按预期 BLOCK 3 项：课程练习尚未提交、reviewer 缺失、真实课程效果未验证

approval validator matrix（母库 + 子库）
→ 缺失 sidecar 各 1 项 BLOCK；URL immutable locator 下 synthetic pass 各 1 项；dirty source、错误 scope、错误 tag、错误 digest、AI reviewer 各 5 项/每个 scope 均 BLOCK；总计 2 个逻辑 pass + 12 个负向阻断

artifact adversarial test
→ 在母库/子库候选包分别加入 probe.docx；两个 artifact validator 均 exit 1，准确命中 unlisted/unsupported artifact
```

### 结论

- **PASS（机械治理层）**：nested approval schema、scope 隔离、tag namespace、摘要绑定、合法 HTTPS immutable locator、非法本地路径和错误批准身份均按预期工作；母库与子库制品携带相同的最新批准校验器。
- **WARN**：以上 synthetic approval 只证明校验器逻辑，不是 Tony 的人工批准；41 个 legacy durable page 仍按渐进编号迁移；外部 URL 内容、跨部署 CMS、失败恢复、客户 workspace 升级和课程真人效果仍未完成验证。
- **BLOCK（真实发布层）**：母库与 `website-content-ops` 仍为 `release_status: BLOCK`、`license_status: pending`、`approval_status: pending`；构建时 `source_dirty: true`；未创建正式 tag、未 commit、未 push、未发布。

本 addendum 记录的是一次“先发现过度阻断、再修复并复验”的对抗闭环，不能被解读为正式发布批准。

## Final Addendum 9 — 2026-07-28 final approval-gate recheck

### 本轮目标

本轮不是重新证明“目录看起来完整”，而是逐个攻击最终批准链：候选包身份、旁路 approval、摘要绑定、人工身份、tag namespace、clean source 和未知扩展名。审查只接受当前工作区命令输出，不把前一轮摘要当证据。

### 当前候选包事实

| Scope | Candidate | package_kind | Version | Files | SHA256SUMS | release | license | approval | source_dirty |
|---|---|---|---|---:|---:|---|---|---|---|
| 母库 | `dist/mother/latest` | `mother-library-release-candidate` | `0.1.1-draft` | 300 | 301 | `BLOCK` | `pending` | `pending` | `true` |
| `website-content-ops` | `sub-libraries/website-content-ops/dist/latest` | `sub-library-release-candidate` | `0.3.2-draft` | 101 | 102 | `BLOCK` | `pending` | `pending` | `true` |

目录文件总数分别为 302 和 103，因为还包括 `MANIFEST.json` 与 `SHA256SUMS`。

### 当前命令证据

```text
node scripts/sync-indexes.mjs
→ INDEXES_SYNCED: 49

node scripts/validate-indexes.mjs --check
node scripts/validate-indexes.mjs --strict
→ INDEX_VALIDATION_PASS: markdown=266

node scripts/validate-links.mjs --release
→ LINK_VALIDATION_PASS: markdown=266 links=971

node scripts/validate-logs.mjs --release
→ LOG_VALIDATION_PASS; daily_logs=1 events=16 warnings=0 failures=0

node scripts/validate-mother-library.mjs
node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs
→ 两个 scope 均 STRUCTURE_PASS，但各自明确报告 release_status BLOCK、license pending、approval pending

node scripts/validate-artifact.mjs dist/mother/latest
node sub-libraries/website-content-ops/scripts/validate-artifact.mjs sub-libraries/website-content-ops/dist/latest
→ 两个候选包均 ARTIFACT_PASS；这只是完整性和静态边界通过

node scripts/validate-knowledge-chain.mjs --release
→ 按预期 BLOCK 3 项：课程练习未提交、reviewer 缺失、真实课程效果未验证
```

### approval matrix 与 fail-closed 攻击

在临时副本中将候选包显式改成 `Ready` / `cleared` / `approved` / `e2e-pass`，绑定当前 `source.commit`、`content_digest`、`MANIFEST.json` 和 `SHA256SUMS` 摘要，再使用合法 HTTPS immutable locator 与人工 reviewer 做 synthetic pass：

- 母库 synthetic approval：`PASS`；子库 synthetic approval：`PASS`。
- 每个 scope 的 `scope.id`、`scope.package_kind`、content digest、local immutable locator、AI reviewer、tag name、dirty source 共 7 个负向变体：全部 `BLOCK`，合计 14 项。
- 每个 scope 的 strict tag 检查：没有真实 annotated tag 时 `BLOCK`。
- 每个 scope 的 artifact gate：缺失 sidecar 时 `BLOCK`；带 synthetic sidecar 但没有真实 annotated tag 时仍 `BLOCK`。
- 向两个临时 artifact 注入已登记并重算摘要的 `probe.docx`：均准确 `BLOCK: unsupported artifact file extension`。

这证明的是校验器的负向行为，不是 Tony 已经批准发布，也不是许可证、跨部署运行或课程效果证据。

### 代码与文档加固

- 母库和子库 approval validator 的 `expectedPackageKind` 现在依据 `release_scope` 推导，而不是依赖 package id 的偶然值；`scope.id` 仍必须逐字等于候选包 `MANIFEST.json.package_id`。
- tag namespace 现在严格依据 `standalone-mother-library` / `standalone-sub-library` 推导；非法 release scope 会直接阻断。
- 修复 `sub-libraries/website-content-ops/scripts/README.md` 的嵌套 Markdown fence；新增子库 `CHANGELOG` 的 `0.3.2-draft` 入口，消除 VERSION 与 CHANGELOG 的版本入口漂移。
- 已重新构建 latest-only 候选包，最新包中已包含上述 validator 和文档。

### 最终 verdict

- 结构与索引：`PASS`（静态范围内）。
- 母库独立候选包：`PASS`（artifact 完整性），发布状态仍为 `BLOCK`。
- `website-content-ops` 独立候选包：`PASS`（artifact 完整性），发布状态仍为 `BLOCK`。
- approval / tag fail-closed：`PASS`（synthetic 正向 + 负向攻击均符合预期）。
- 课程知识链 release evidence：`BLOCK`。
- 母库正式外部发布：`BLOCK`。
- `website-content-ops` 正式外部发布：`BLOCK`。

### 不能被本轮 PASS 覆盖的事实

当前工作树仍 dirty，没有创建正式 annotated tag，没有真实人工 `RELEASE-APPROVAL.json`，许可证仍 pending；真实 CMS 跨部署、升级/回滚、第二工具迁移、客户运行区和课程实际效果仍未闭合。不得 commit、push、创建正式 tag、把 manifest 改为 Ready/Published 或对外宣称稳定可安装。
