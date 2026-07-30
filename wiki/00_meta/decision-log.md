---
title: "Decision Log"
description: "冻结的旧版决策汇总和关闭事项迁移映射；历史正文只读保留，新决策进入对应 durable 治理页并由按日日志记录发生时间。"
type: "meta"
status: "Archived"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: []
related: ["logs/index.md", "open-questions.md", "current-focus-history-2026-07.md"]
---
# Decision Log

> **FROZEN / NON-CANONICAL（2026-07-29）**：本页旧决策正文只读保留，不再追加新决策。新决策必须写入对应 durable governance/business page，并在 daily log 记录证据。
>
> 迁移映射：当前状态 → `current-focus.md`；当前问题 → `open-questions.md`；发生过程 → `logs/`；发布规则 → `release-state-machine.md`、`publishing-and-redaction.md`；母库/子库结构 → `private-master-and-sub-library-model.md`。

## Closed Question Migration Map

| closed_id | 已关闭事项 | canonical 结论/证据 | 关闭状态 |
|---|---|---|---|
| `CQ-20260727-0001` | 母库、子库和虚拟演示边界 | `private-master-and-sub-library-model.md`；`sub-library-contract.md` | closed |
| `CQ-20260727-0002` | AllinCMS 当前部署分类、标签、文章和真实图片生命周期 | 本页历史记录；`ingestion-log.md` 对应 `VERIFY-20260727-*` 历史别名；子库 verification/QA 记录 | closed-current-deployment-only |
| `CQ-20260727-0003` | 复杂 Slate 列表与正文图片节点单部署合同 | `ingestion-log.md` 的复杂 Slate/正文图片历史验证；跨部署和主题表现仍在 `open-questions.md` | closed-current-deployment-only |
| `CQ-20260727-0004` | 11 篇文章串行 update/publish/验收 | `ingestion-log.md` 的 `ALLINCMS-ARTICLE-SERIAL-11` 历史记录 | closed-current-deployment-only |
| `CQ-20260728-0001` | synthetic raw → course 结构闭环 | `logs/2026/07/2026-07-28.md` 的 `EVT-20260728-0007` | closed-structure-only |
| `CQ-20260729-0001` | manifest、builder、validator 和敏感检查是否存在 | `current-focus.md`、根 `MANIFEST.md`、`scripts/`；正式 release 资格仍 blocked | closed-mechanism-only |
记录会影响长期策略的决策。普通想法不要放这里，只有“以后要按这个方向做”的内容才写入。

## 格式

```md
## [YYYY-MM-DD] 决策标题

- 背景：
- 决策：
- 原因：
- 影响范围：
- 复查时间：
- 来源：
```
## [2026-07-27] AllinCMS 图片默认使用零点击接口串行方案

- 背景：用户希望小白和任何后续 AI 不再先选择 PicGo / 图床，也不重新抓接口或模拟点击；上传过程应逐张可见，并能把本地图片、媒体记录和最终链接稳定对应。
- 决策：凡目标是 AllinCMS 媒体库，固定先打开并加载准确的 `/{site_key}/media`，运行 `checkAllinCmsMediaRuntime()`，再调用 `uploadAllinCmsMediaSerial()` 并把 `imageIndexPath` 放在客户私有运行区。`uploadAllinCmsMediaDirect()` 仅为内部原语；歧义时只读对账；UI 回退需用户明确批准；PicGo、R2、GitHub、COS、OSS 仅在目标是外部图床或用户明确指定时使用。
- 原因：统一入口能减少认知成本，逐张刷新让用户可监督，私有原子索引和源 SHA-256 主键避免改名后重复上传，`request_started` 与只读对账避免结果不明时盲目重传。
- 影响范围：Website Content Operations 子库入口、AllinCMS Adapter、机器合同、共享 `allincms-bulk-content-upload` Skill、课程工具路线和发布阻断口径。
- 验证边界：真实远程证据覆盖单张直传、10 张串行、一次受控刷新对账和一张获批虚拟媒体的字段写入；原子索引、锁、统一异常、断点恢复、预存标题冲突、自定义标题和元数据停批规则已扩展为 29 项本地故障测试。新恢复层跨部署稳定性仍未由后续自然上传证明。
- 复查时间：下一次获得一轮安全虚拟图片上传授权时，先复验新恢复层；若 AllinCMS 部署合同漂移，停止并用一张新虚拟图重新捕获，不自动改走 UI 或外部图床。
- 来源：Tony 当前对话，2026-07-27。

## [2026-07-27] AllinCMS 文章发布采用动态抓包、全字段 update 后 publish

- 背景：文章接口已经探索出保存/发布路由；用户要求真实图片、所有字段完整，并通过接口完成真实发布。
- 决策：文章执行固定为“读取当前站点与分类/标签 → 准备已验收媒体对象 → 生成 Slate → 用完整 payload `mode=update` 保存 → 后台刷新核对 → 用同一完整 payload `mode=publish` 发布 → 前台列表/详情/图片验收”。动作 ID、siteId、postId 和媒体对象细节均运行时动态捕获，不硬编码。
- 原因：单独发布可区分草稿持久化和公开可见性；完整 payload 能避免更新时覆盖字段；真实封面必须以当前部署媒体对象形状为准。
- 影响范围：AllinCMS 文章 adapter、内容运营子库、文章模板和后续批量发布 SOP。
- 验证边界：已有分类/标签绑定和单个 `source: "oss"` + `path` 封面样本已验证；分类创建、标签创建、跨部署合同、复杂 Slate、失败重试和回滚仍 BLOCK。
- 复查时间：下一次目标部署合同变化或需要新建分类/标签时，先只读抓包并重新建立最小证据，不自动重放旧 action。
- 来源：Tony 当前对话，2026-07-27。

## [2026-07-27] AllinCMS 先建 taxonomy，再做全字段文章多轮验证

- 背景：用户要求真实创建文章分类、标签，并确认接口文章发布不是偶然成功。
- 决策：文章流程固定为“读取当前 taxonomy → 缺失时一次创建并刷新对账 → 取得 ID → 动态捕获当前文章 update action → 完整 `mode: update` → 后台刷新 → 重复 update/修改字段复验 → 完整 `mode: publish` → 重复 publish → 前台列表/详情双次验收”。
- 原因：taxonomy 名称不能替代 ID；重复保存和重复发布能暴露覆盖、重复创建和幂等性问题；真实封面必须经过匿名 HTTP、MIME 和图片解码验收。
- 影响范围：AllinCMS article adapter、内容运营子库、批量发布 SOP、后续分类/标签导入。
- 验证边界：本轮闭合单篇 taxonomy + 全字段文章的稳定发布；不代表删除/回滚、跨部署 Slate 或大批量限流已完成。
- 复查时间：下一次部署变更或进入批量文章导入前，重新抓当前 taxonomy/create 和 post/update action，并先用一篇虚拟文章跑同一 A/B/C/D 矩阵。
- 来源：Tony 当前对话，2026-07-27。

## [2026-07-27] DEC-20260727-ALLINCMS-SERIAL-METADATA-DELETE-CONTRACT | AllinCMS 媒体操作最终口径

- **Decision**：AllinCMS 媒体上传永久严格串行，禁止并发、任务池、多标签和重叠请求；一次请求多图不作为默认路线或发布缺口。
- **Per-image transaction**：AI 读图与事实校验 → 单图上传 → 刷新验收 → 原子索引 → 获批后单次写 `title / alt / caption` → 0 / 750 / 2000 ms 最多三次只读复核 → 下一张。
- **Private metadata**：完整 `description`、notes、结构化 metadata、事实依据和不确定项存客户私有 `image-index.json`；AllinCMS 只写平台支持的三个字段。
- **Ambiguity**：上传成功与元数据成功分开记账；元数据不明确时停止本批，不重发、不重传、不通过删除修复。
- **Deletion**：只以精确媒体卡和精确 RSC 记录消失验收；不要求证明 OSS、对象存储、公开 URL 或 CDN 的物理删除。
- **Reason**：降低重复上传、错配、重复字段写入和因读后写延迟产生的破坏性重试，让其他 AI 可以按固定合同执行。
- **Status**：accepted / implemented / local tests 22 of 22；单张真实虚拟元数据样本已验证，跨部署稳定性仍只可在后续自然获批任务中复验。

## [2026-07-27] DEC-20260727-ALLINCMS-UNBOUNDED-STRICT-SERIAL-RETRY

- **Decision**：AllinCMS 图片串行总控取消文件数量上限；永久保持一张完整闭环后才开始下一张。
- **Error policy**：上传报错后必须“延迟 → 精确只读对账 → 已存在则补齐 / 明确不存在才有限重试当前图片”。对账不明确不得盲目重传。
- **Default parameters**：`maxAttemptsPerImage: 3`，`retryDelaysMs: [2000, 5000]`；可配置，但必须是有限正整数尝试次数和非负延迟。
- **Unchanged boundaries**：元数据写请求每图最多一次；删除歧义不重发；并发上传永久禁止；索引写失败或锁冲突立即停止。
- **Evidence**：29/29 本地测试通过；12 张输入最大同时上传数为 1；源码无 `Promise.all` / `Promise.allSettled`。真实远程任意大批次长跑未验证。

## [2026-07-27] AllinCMS 前 4 项默认走动态抓包后的接口回放

- **背景**：用户要求通过接口完成真实分类、标签和文章生命周期操作，并在结束后检查稳定性和清理结果。
- **决策**：默认流程为“当前页面动态捕获 → 单次接口回放 → 等待响应 → 后台刷新重读 → 前台/列表验收”；分类、标签创建严格一次一个，文章先完整 `update` 再按需 `publish`，取消发布使用 `unpublish`，删除只发送一次已确认合同的请求。
- **原因**：Server Action ID、部署、站点和对象 ID 会漂移；HTTP 200 不是持久化或前台成功的充分证据；删除和创建都需要避免状态不明时重复发送。
- **影响范围**：AllinCMS 文章 adapter、taxonomy 操作、批量内容发布 SOP、测试清理和后续 AI 执行入口。
- **验证边界**：当前部署前 4 项已完成；跨部署合同、复杂 Slate、503/回滚和大批量仍待验证。
- **复查时间**：下一次部署/站点变化或进入批量发布前，先重新抓当前 action 和 schema，并用一篇虚拟文章跑最小闭环。
- **来源**：Tony 当前对话，2026-07-27。


## [2026-07-27] AllinCMS 复杂 Slate 验收必须分离数据层与主题表现层

- **Decision**：文章接口通过不能替代前台语义/无障碍验收；复杂 Slate 固定分为 CMS 数据层和主题表现层两层检查。
- **Evidence**：当前部署真实 UI 合同确认 `ul`/`ol`/`li`、`listStyleType`、`listStart` 和正文图片 `url/alt/children`；后台数据和视觉内容存在，但主题前台无序列表输出为嵌套 `div`，图片 `alt` 为空。
- **Implication**：接口批量发布可以复用已捕获的 Slate 节点形状，但若发布标准要求语义 `<ul>` 或图片无障碍属性，必须把主题修复/降级说明纳入发布门槛，不能通过重复 API 请求解决。
- **Cleanup rule**：删除前必须精确匹配目标行和确认文案；确认一次后只发送一次删除请求，刷新后台并以前台 404 完成验收；任何非目标确认在发送前取消。
- **Source**：Tony 当前对话，2026-07-27。

## 2026-07-27：AllinCMS 文章正文图片采用资产 / occurrence 双层合同

- **Decision**：Markdown 正文图片唯一入口为 `article-image-binding.mjs`；禁止全局字符串替换、文件名模糊匹配和手写 Slate 图片节点。
- **Asset rule**：源 SHA-256 是资产主键；同字节图片复用同一媒体 ID / URL。
- **Occurrence rule**：每个文章位置独立保存字符区间、块位置、前后锚点、页面语境、Alt 和 Caption；A/B/A 是 2 个资产、3 个 occurrence。
- **Caption rule**：AllinCMS 正文 Caption 必须为 Plate/Slate 文本节点数组，字符串 Caption 在请求前阻断。
- **Completion rule**：草稿保存必须同时通过单次 `mode=update` 请求、HTTP 200、后台完整回读、顺序/位置/URL/Alt/Caption 对账、编辑页非 500、图片解码、Caption 可见和仍为草稿；HTTP 200 不能单独判成功。
- **Retry rule**：文章保存请求一旦可能发出，禁止自动重发；只读回读后由人决定是否进行新的修正草稿更新。
- **Alt rule**：后台数据、编辑器 DOM、公开主题三层分开报告。当前只通过后台持久化；编辑器 DOM 3/3 缺失 Alt；本轮未发布。
- **Lock rule**：文章清单单写者锁冲突默认停止；陈旧锁只允许经句柄、进程、临时文件和目标清单检查后人工恢复并留私有证据。

## DEC-20260727-ALLINCMS-ARTICLE-EDITOR-COMPLETE-GATE | 后台回读后必须通过完整编辑器健康闸

- **Status**：Accepted
- **Decision**：AllinCMS 正文图片保存不能以 HTTP 200、Server Action 捕获或后台字段回读作为最终成功。必须继续确认 Slate 编辑器存在、正文图片数量与保存内容一致、全部图片解码、可见 Caption 顺序一致、Draft/草稿状态仍存在。
- **Caption rule**：`caption` 必须是非空 Slate 文本节点数组，数组中每一项都必须是含字符串 `text` 的对象；字符串和混合数组请求前阻断。
- **Alt boundary**：后台 Alt 持久化、编辑器 DOM Alt、公开主题 Alt 分层报告；当前草稿仅证明后台持久化，编辑器 DOM 仍缺 3/3，公开主题本轮未授权。
- **Retry boundary**：请求可能发出后，任何回读或渲染异常都禁止自动重发，只允许只读重载与对账。
- **Evidence**：新版默认健康闸在当前虚拟 A/B/A 草稿只读运行通过；文章图片 31/31 与媒体 29/29 合计 60/60。


## [2026-07-27] DEC-20260727-ALLINCMS-ARTICLE-SERIAL-11 | 当前部署文章批量上限证据与状态不明处理

- **Decision**：当前部署的文章接口默认保持“逐篇完整 payload → `update` → 刷新对账 → `publish` → 前台验收”的严格串行路径；11 篇真实运行已验证，不把它解释为任意大批量能力。
- **Evidence**：11/11 后台已发布，前台标题/正文/列表文本 11/11 通过，55/55 图片解码，11/11 真实 WebP 封面通过；清理后 11 个临时文章行消失。
- **Ambiguity rule**：批量 CDP 调用超时后禁止自动重发；先只读回读后台确认远端状态，再决定是否继续。
- **Boundary**：更大批次、限流、中断恢复、503/transaction state mismatch、文章级回滚、跨部署合同和主题语义/Alt 缺口仍保持 BLOCK。
- **Impact**：AllinCMS 文章 adapter、批量发布 SOP、测试清理和知识库验收口径。
- **Source**：`direct-serial-11-article-verification.redacted.md` 与用户当前对话，2026-07-27。


## [2026-07-27] DEC-20260727-ALLINCMS-ARTICLE-IMAGE-IDENTITY-AND-READBACK-GATES

- **Decision**：AllinCMS 正文图片绑定只有在“源资产身份、当前本地字节、远端媒体身份、后台 Slate 结构、编辑器健康”五层同时通过时才可判定草稿绑定成功。
- **Identity gate**：`mapping_source_sha256` 和 `candidate_source_sha256` 必须等于 occurrence 的 `asset_id`；候选必须有已知 `candidate_media_id` 与 `candidate_url`；标题唯一也不能替代源哈希身份。
- **Freshness gate**：`buildAllinCmsSlateContent()` 必须被 `await`；构建前严格串行重读每个本地图片文件，并复核 SHA-256 与 MD5，字节变化立即停止并要求重建清单。
- **Structure gate**：Caption 只接受 Plate/Slate 文本节点数组；保存后既比较文本，也复验后台实际节点结构，字符串或混合数组一律失败。
- **Recovery gate**：锁文件记录 PID、取得时间和目标清单；禁止自动删锁、绕锁、并发执行，状态不明时只读对账，不盲目重发。
- **Evidence**：媒体 29/29、文章图片 36/36，合计 65/65 本地测试通过；已有真实 A/B/A 草稿证据继续有效。
- **Boundary**：此 PASS 只覆盖当前草稿正文图片绑定；公开主题 Alt、跨部署、更多复杂 Plate 节点、发布与失败回滚仍不在通过范围。


## [2026-07-27] AllinCMS 共享 Skill 与知识库 Adapter 的权威关系

- **Decision**：对 Tony 的 `701_kecheng` 任务，当前文章、分类、标签、创建、更新、发布、取消发布、删除、恢复和串行批量合同，以 `sub-libraries/website-content-ops/ADAPTERS/cms/allincms/` 的 Adapter、机器合同、测试和当前部署证据为准；共享 `allincms-bulk-content-upload` 只负责通用入口、源料编排、SOP、中性模板和验证报告。
- **Conflict rule**：共享 skill 或 `references/server-action-save-api.md` 与当前 Adapter 冲突时，不回放共享文档的旧假设；先更新引用说明，再按 Adapter 的 fail-closed 合同执行。
- **Review rule**：已登录后台是执行前提，不是 API 合同证明；本轮不把“敏感”作为阻断项，但凭据和真实运行标识仍只留在私有运行区。HTTP 200、UI 成功提示或历史成功不能覆盖当前 Adapter 的 `BLOCK`。
- **Current gates**：`postCreate`、文章级远程故障注入恢复、跨部署/跨站点外推、任意大于 11 篇远程批量和主题语义/图片 `alt` 表现层仍需分别满足证据门槛，不能合并宣称 PASS。
- **来源**：Tony 当前对话，2026-07-27；当前 Adapter 本地测试 115/115。

## [2026-07-28] DEC-20260728-SUBLIBRARY-STRUCTURE-ADVERSARIAL-UPGRADE | 子库结构与发布边界升级

- **Decision**：保持 `wiki/` 与 `sub-libraries/` 并列；子库内部以 `README.md → MANIFEST.md → AGENTS.md → 可选 SKILL.md` 为唯一入口链，不建立平行第二套 `skills/` 真源。
- **Delivery modes**：人类操作包、AI Skill 适配器和工具包分别声明成熟度；当前 `website-content-ops` 为 `0.3.1-draft`，`release_status: BLOCK`。
- **Hardening**：补齐 `CHANGELOG.md`、`RELEASE.md`、`scripts/README.md` 和无依赖静态检查；将 `allincms.md` 改为 `allincms-overview.md`，清理活动旧路径、机器绝对路径和本地 `.obsidian/` 发布风险。
- **Verification**：子库静态检查通过；全库 202 个 Markdown 文件 front matter / 活动链接 / 文件目录冲突 / 机器路径 / 明显凭据模式检查通过；AllinCMS adapter `npm test` 为 115/115。
- **Release boundary**：结构 PASS 不代表稳定发布 PASS。没有 latest-only release candidate、安装后验收、第二工具迁移、跨部署和完整失败恢复证据前，继续保持 `BLOCK`。
- **Source**：`wiki/00_meta/structure-adversarial-review-20260728.md`、`sub-libraries/website-content-ops/RELEASE.md`、本次工作区检查，2026-07-28。

## 2026-07-28：母库与子库双发布线升级后的最终判定

- **决定**：母库和每个子库各自拥有 manifest、validator、latest-only 构建器、候选包清单和 checksum；子库独立运行所需来源摘要进入自身 `REFERENCES/`。
- **证据**：母库 `dist/mother/latest` 与 `website-content-ops/dist/latest` 均生成并通过候选目录静态校验；AllinCMS `npm ci` + `npm test` 为 115/115。
- **保留阻断**：两个 scope 都保持 `release_status: BLOCK`，因为许可证、干净 Git snapshot、真实独立运行/Skill 安装和人工发布批准尚未完成。
- **边界**：母库通过不替代子库通过；子库通过不替代母库通过；不得把本地候选包、结构 PASS 或本地 adapter 测试写成外部稳定发布。
- **来源**：`wiki/00_meta/structure-adversarial-review-20260728-final.md`。
