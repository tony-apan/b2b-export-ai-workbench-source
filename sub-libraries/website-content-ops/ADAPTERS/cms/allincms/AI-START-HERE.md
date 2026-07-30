---
title: "AI Start Here: AllinCMS Media and Article Image Operations"
description: "其他 AI 执行 AllinCMS 图片串行上传、AI 元数据同步、文章正文图片原位绑定与媒体记录删除时的唯一入口。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-30"
sources: ["media-operations-contract.redacted.json", "article-image-binding-contract.json", "direct-delete-verification.redacted.md", "Observed signed-in upload and draft-binding runs 2026-07-27", "Local fault tests 2026-07-27"]
related: ["README.md", "media-metadata-and-ai-vision-sop.md", "article-operations.md", "upload-media-browser.mjs", "article-image-binding.mjs", "article-operations.mjs", "article-operations-contract.json", "upload-media-browser.test.mjs", "article-image-binding.test.mjs", "article-operations.test.mjs", "media-operations-contract.redacted.json", "article-image-binding-contract.json", "../../image-upload-routing.md"]
confidence: "high-for-observed-upload-contract-medium-for-new-local-recovery-layer"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AI 唯一执行入口：AllinCMS 图片上传、文章原位绑定与媒体记录删除

## 不要重新研究路线

只要目标是 **AllinCMS 媒体库**，默认使用本目录 adapter：

```text
checkAllinCmsMediaRuntime()
→ AI 逐张读图并生成候选
→ uploadAllinCmsMediaSerial()
→ 每张上传、刷新、验收并原子写索引
→ 若获授权则接口写 title / alt / caption，并做有限只读复核
→ 当前图片完整结束后才进入下一张
```

不要先配置 PicGo、R2、GitHub、COS 或 OSS。它们只在用户明确需要外部图床时使用，见 [图片上传统一路由](../../image-upload-routing.md)。

## 本库与共享 Skill 的权威关系

当前知识库中的 `ADAPTERS/cms/allincms/`（从子库根目录看） 是 **AllinCMS 当前部署实测 Adapter、文章字段合同、taxonomy 合同、状态机和验证证据的权威来源**。

共享的 `allincms-bulk-content-upload` Skill（安装位置由宿主环境决定） 是共享的入口、编排和 SOP 层：它负责把源资料、manifest、批次和验证串起来，但不得自行复制、重写或覆盖本库当前实测合同。两者冲突时，以本库的 Adapter/合同为准；共享 Skill 应引用本库，而不是保留旧假设。

文章生命周期与正文图片是两个 companion：

- 文章、分类、标签、创建/保存/发布/取消发布/删除、失败恢复和串行批次：`article-operations.mjs`；
- Markdown 正文图片原位绑定、Slate 图片节点和编辑器健康闸：`article-image-binding.mjs`；
- 共享机器字段和动作模板：`article-operations-contract.json`。

## 强制规则

1. 不重新抓上传、正文保存或删除接口，不复制本文件中的循环另写脚本。
2. 不模拟点击上传、不打开文件选择器、不用坐标点击。
3. 用户必须先登录，并打开准确页面：`https://workspace.laicms.com/{site_key}/media`。
4. `site_key` 未经用户确认、页面不准确、登录失效：停止，不做写操作。
5. 默认批次入口是 `uploadAllinCmsMediaSerial()`；`uploadAllinCmsMediaDirect()` 是其单张原语。
6. 上传出现错误时，当前图片先等待，再做精确只读对账；远端已存在则补齐索引，只有明确返回 `not_found_stop` 时才允许重试当前图片。对账不明确时禁止盲目重传。
7. 本地索引写入成功前，不进入下一张；索引锁冲突或写入失败立即停止。
8. `prepared` 阶段恢复时若远端已有同标题记录，按预存标题冲突停止，不得自动认领；`request_started` 对账成功时保留规范化上传哈希。
9. 删除必须获得当前这一次、这一条媒体的明确授权，并精确匹配 `siteKey + mediaId + title + URL`。
10. 删除成功只按 AllinCMS 媒体卡和 RSC 媒体记录消失判断；底层对象或 CDN 是否物理删除不属于当前完成口径。
11. 永久禁止并发上传：不使用 `Promise.all`、任务池、多标签或重叠请求；一张 verified / reconciled 并写索引后才开始下一张。
12. AI 先读图并生成候选；`description` 只写私有索引，`title / alt / caption` 可在本批明确授权后由接口同步。元数据失败不得删除或重传图片。
13. 元数据写请求最多一次；写后只允许有限次数刷新重读，不得因短暂读延迟自动重发。
14. UI 回退只有在 adapter 报告合同漂移且用户明确批准后才可使用；不得自动切换。
15. Markdown 文章正文图片只能通过 `article-image-binding.mjs` 处理；禁止全局字符串替换、按文件名模糊替换、手写 Slate 图片节点或重新抓正文保存接口。
16. 含图片正文的唯一远程入口是 `bindAndSaveAllinCmsArticleDraftDirect()`；其他 AI 不得直接调用 `saveAllinCmsArticleDraftDirect()` 保存图片正文，不得伪造 `bindingProof`，也不得绕过文章 operation lock。
17. 上传阶段打开精确媒体页；保存文章前再打开精确文章更新页 `/{site_key}/posts/{post_id}/update`。页面不精确或登录失效时停止。
18. 一个图片资产可以在正文出现多次；manifest 必须为 schema 2：`asset` 负责字节和远端映射，`occurrence` 独立负责绝对源路径、SHA-256、MD5、位置、Alt、Caption、上下文和锚点，禁止合并两层。
19. 正文 Caption 必须是 Plate/Slate 文本节点数组 `[{"text":"..."}]`，不能是字符串；字符串必须在请求前阻断。
20. 草稿保存后即使 HTTP 200 和后台回读一致，也必须继续通过编辑页非 500、图片解码和 Caption 可见闸；任一失败不得报告成功。
21. 正文图片绑定仍然只允许 `mode: "update"`；完整文章生命周期由 `article-operations.mjs` 单独执行。`publish` / `unpublish` / `delete` / taxonomy 写入必须单独明确授权，并遵守“请求后刷新、重读、状态不明不盲重发”的恢复规则。
22. AllinCMS 当前已验证的是 Alt 后台字段持久化；文章编辑器 DOM 的 `<img>` 仍未输出 Alt。不得宣称公开主题 SEO Alt 已生效。
23. 文章 `postCreate` 不是默认放行的远程动作：只有重新捕获当前部署的完整 create 合同、能从回读中取得精确新 `postId`，并显式传入 `createContractConfirmed: true` 时才允许调用；否则保持阻断。
24. 分类 / 标签创建必须带当前站点 taxonomy snapshot，用同站点 slug 做请求前重复检查；snapshot 缺失、`contentType` 不是 `posts` 或读回无法确认唯一对象时停止。
25. runtime 如果提供 `actions` 映射，缺少具体 action 必须 fail-closed；文章回读缺少状态或包含冲突状态时，不能把 HTTP 200 当成功。
26. 本地控制测试通过不等于新的远程部署通过；每次部署或站点变化都要重新捕获运行时合同，并把远程证据与本地证据分开报告。

## 1. 导入唯一模块

```js
const adapter = await import(
  "<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/upload-media-browser.mjs"
);
```

知识库移动后只替换绝对 `file://` URL，不复制 adapter 源码。不要导出 Cookie、Token、Authorization 或完整 Server Action 值。

## 2. 先做只读环境预检

```js
const readiness = await adapter.checkAllinCmsMediaRuntime({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  localFiles: [
    "/absolute/private-runtime/images/01.webp",
    "/absolute/private-runtime/images/02.png",
  ],
});
```

只有 `readiness.status === "ready"` 才进入上传。

- 小于等于 1 MB 的 WebP 不依赖 `sharp`；
- PNG、JPG 和较大的 WebP 需要本目录 `package.json` 声明的 `sharp`；
- `sharp` 缺失时明确阻断相关文件，不得偷偷切换 UI；
- 安装依赖属于机器状态变更，须先得到用户批准；批准后可在本目录执行 `npm install`。

## 3. 默认上传任意数量并写本地索引

`imageIndexPath` 必须位于客户自己的私有运行区，不能写进公开母库：

```js
const result = await adapter.uploadAllinCmsMediaSerial({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  imageIndexPath: "/absolute/private-runtime/media/image-index.json",
  progressMode: "visible",
  maxAttemptsPerImage: 3,
  retryDelaysMs: [2000, 5000],
  syncRemoteMetadata: true,
  metadataAuthorizationConfirmed: true,
  localFiles: [
    {
      localFile: "/absolute/private-runtime/images/01.webp",
      title: "rear-hub-motor-side-view",
      description: "产品侧面图",
      alt: "Rear e-bike hub motor showing the axle and cable lead",
      caption: "Rear hub motor side view for an electric bicycle application.",
      metadata: {
        asset_type: "product_side_view",
        visible_features: ["motor shell", "axle", "cable lead"],
        page_context: "product_detail",
        language: "en",
        confidence: 0.92,
        human_review_required: false,
        fact_basis: ["image_observation", "product_knowledge_base"],
        uncertain_claims: [],
      },
      notes: "产品详情页候选",
    },
    "/absolute/private-runtime/images/02.webp",
  ],
  onProgress: ({ stage, position, total, filename }) => {
    console.log(`[${position}/${total}] ${stage}: ${filename}`);
  },
});
```

内部固定执行：

```text
写 prepared
→ 写 request_started
→ 单张零点击接口请求
→ 若报错：等待 → 只读刷新对账 → 已存在则补齐；确认不存在才重试当前图片
→ 自动刷新媒体页
→ 验证唯一卡片、RSC media ID、URL、匿名 GET 和图片解码
→ 原子写 verified / reconciled_existing 上传映射
→ 若本项提供 title / alt / caption：只发 1 次 updateMediaAction
→ 按有限延迟只读刷新，验证 title / alt / caption 与 media ID / URL
→ 写 metadata_verified
→ 才进入下一张
```

刷新是 adapter 导航，不是模拟点击。媒体页在前台时，用户会看到卡片逐张增加；adapter 不承诺强制抢焦点或保持滚动位置。

### 成功状态

- `result.status === "completed"`：本批次已全部上传、对账或复用；
- item 为 `uploaded_and_indexed`：本轮上传并写索引；
- item 为 `reconciled_and_indexed` / `reconciled_existing`：没有重传，通过只读对账补齐；
- item 为 `reused_verified_mapping`：源 SHA-256 已有 verified 映射，即使文件改名也复用。
- `result.cleanup.imageIndexLockReleased === true`：本轮索引锁已正常释放；若为 `false`，保留远端与索引结果，但下一轮前必须人工检查私有锁文件。

### 必须停止的状态

- `stopped_ambiguous`：远端状态或对账仍不明确，禁止盲目重传；
- `stopped_retry_exhausted`：每次都已等待并确认远端不存在，但当前图片达到最大尝试次数；停止本批；
- `stopped_index_write_failed`：远端已验证但索引未落盘，停止下一张；下次从 `request_started` 状态只读对账恢复；
- `stopped_index_or_runtime_error`：索引、锁或运行环境错误；
- `stopped_metadata_before_request`：图片已上传，元数据请求未发出；保留图片并停止下一张；
- `stopped_metadata_ambiguous`：图片已上传，元数据请求可能已成功但有限刷新未完全一致；禁止重发元数据、禁止重传图片、停止下一张。

## 4. 只读对账，不发上传请求

当上次结果不明确或任务中断时：

```js
const reconciled = await adapter.reconcileAllinCmsMediaDirect({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  expectedTitle: "唯一文件名 stem",
  controlledReload: true,
});
```

固定状态：

- `reconciled_existing`：唯一媒体记录和全链验证成立；
- `not_found_stop`：精确确认未找到；只允许串行总控在当前图片、当前授权和剩余尝试次数内重试；
- `ambiguous_multiple_matches`：同标题多条，禁止自动处理；
- `verification_failed`：记录或公开资产验证不完整。

这个函数的 `requestSent` 恒为 `false`。只有 `uploadAllinCmsMediaSerial()` 可以把 `not_found_stop` 转换为当前图片的有限重试；其他 AI 不得在函数外另写“找不到就上传”的循环。

## 5. 图片索引合同

索引以 `source_sha256` 为主键，分别保存：

- `source_sha256`、`source_md5`；
- `normalized_upload_sha256`、`normalized_upload_md5`；
- `media_id`、`title`、`url`、`mime_type`；
- `remote_sha256`、`remote_md5`；
- `description`、`alt`、`caption`、`notes`、`ai_metadata`；
- 状态、时间和最多 20 条阶段历史。

平台可能重编码图片，源哈希、上传哈希和远端哈希不得互相代填。索引采用临时文件 + rename 原子写入，并以 `${imageIndexPath}.lock` 实现同一索引单写者。已 verified 的同源图片可以只更新本地 AI 元数据，不会重新上传。字段含义、事实闸和 AllinCMS 同步边界见 [图片元数据与 AI 读图 SOP](media-metadata-and-ai-vision-sop.md)。

## 6. Markdown 文章正文图片原位绑定

文章正文图片的**唯一入口**是：

```js
const articleImages = await import(
  "<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/article-image-binding.mjs"
);
```

禁止把 Markdown 全局替换成 URL，也禁止让另一个 AI 猜 Slate 结构。固定流程：

```text
读取原始 Markdown 和本地图片
→ createArticleImageBindingManifest() 创建 schema 2 清单：资产层可复用远端记录，每个 occurrence 独立保存绝对源路径、SHA-256、MD5、原文位置和语境
→ 逐资产复用或调用 uploadAllinCmsMediaSerial() 严格串行上传
→ 在精确媒体页 verifyArticleMediaMappings() 重新复核媒体记录、HTTPS、MIME、签名和浏览器解码；映射必须同时携带完整 verification 证据、与 asset 完全一致的源 SHA-256、已知 media ID 和 URL，不能只写 status: verified 或只按标题认领
→ replaceMarkdownImageOccurrences() 仅生成可审阅的 bound Markdown，不做远程保存
→ 打开精确文章更新页并确认 site key、post ID、登录状态和本次草稿保存授权
→ 只调用 `bindAndSaveAllinCmsArticleDraftDirect()`：
  → 按 occurrence 严格串行重读每个本地路径并校验 SHA-256/MD5
  → 按原位置逐 occurrence 绑定媒体 URL、Alt、Caption，并通过 `onProgress` 展示进度
  → 执行全量 audit 并生成不可手写的 bindingProof
  → 保存边界再次按 occurrence 串行复核本地源图和 proof
  → 整篇草稿只发 1 次 mode=update 请求，不逐图远程保存
  → 后台完整回读 + 编辑页非 500 + 图片解码 + Caption 可见
→ operation lock 持续到文章图片清单原子写入完成
```

含图片正文最终只允许下面这个调用形态；`tab` 必须是已经打开精确文章 update 页、仍保持登录状态的 Browser 标签页，`mappings` 必须来自前一步媒体复核，`manifestPath` 必须位于客户私有运行区且为绝对路径：

```js
const result = await articleImages.bindAndSaveAllinCmsArticleDraftDirect({
  tab,
  expectedSiteKey: "用户已确认的-site-key",
  expectedPostId: "用户已确认的-post-id",
  sourceMarkdown,
  manifest,
  mappings,
  manifestPath: "/absolute/private-run/article-image-binding.json",
  authorizationConfirmed: true,
  onProgress: async (event) => {
    // 只展示逐 occurrence 校验 / 绑定进度；这里不得触发上传或文章保存。
    console.log(`${event.stage}: ${event.current}/${event.total}`, event.sourceFile || "");
  },
});
```

禁止把内部步骤拆成 `buildAllinCmsSlateContent() → saveAllinCmsArticleDraftDirect()` 两段业务调用。拆开后无法证明同一把文章锁覆盖构建、保存、回读和清单落盘，也容易让第二个 AI 在两步之间改正文、换映射或重复保存。

### 两层对象，不能混

```yaml
manifest_schema: 2
asset:
  identity: source_sha256
  owns: [source_files, source_sha256, source_md5, media_id, public_url]
occurrence:
  identity: occurrence_id
  owns: [source_reference, absolute_source_file, source_sha256, source_md5, source_position, before_anchor, after_anchor, role, article_context, alt, caption]
```

同一资产可形成 `A → B → A` 三个 occurrence。第一处和第三处可以复用同一 `media_id / URL`，但必须分别保留自己的本地源路径、哈希、位置证据、Alt、Caption 和文章语境。即使两个路径创建清单时字节相同，保存前也必须分别重读；schema 1 或缺少 occurrence 源身份的旧清单一律停止并重建。

### Caption 的唯一正确结构

```json
{
  "type": "img",
  "url": "https://assets.example.invalid/{site_key}/image.webp",
  "alt": "页面语境中的替代文本",
  "caption": [
    {
      "text": "页面中可见的图片说明"
    }
  ],
  "children": [
    {
      "text": ""
    }
  ],
  "id": "unique-node-id"
}
```

`caption: "文字"` 虽可能被后端保存，但已在 2026-07-27 的虚拟草稿验证中导致文章编辑页 500。adapter 会在请求发出前阻断该结构。

### 草稿保存完成口径

必须同时满足：

1. 本轮只有一个文章保存请求，且 `mode: "update"`；
2. HTTP 200；
3. 后台刷新后完整 payload 回读一致；
4. 图片数量、A/B/A 顺序、Slate 节点位置和 URL 一致；
5. 非装饰图片的 Alt 在后台数据中存在且一致；
6. Caption 按 Slate 文本语义回读一致；
7. 编辑页重载后不是 500；
8. 所有正文图片 `complete=true` 且 `naturalWidth>0`；
9. Caption 在编辑器中可见；
10. 页面仍为草稿，未执行发布。

若第 1 次保存后出现编辑页 500 或其他渲染异常，返回 `article_editor_render_failed`，并标记 `requestMayHaveSucceeded: true`、`automaticRetryAllowed: false`。只允许修正本地 payload 后，由人确认是否进行新的草稿更新；禁止把失败当作“没保存”自动重发。

### Alt 三层状态

| 层 | 当前结论 |
|---|---|
| 后台数据 | 已验证 Alt 字段持久化和回读 |
| AllinCMS 编辑器 DOM | 2026-07-27 只读复验中，3 张正文图的 `<img alt>` 均缺失 |
| 公开主题 | 本轮未发布、未授权验证；不得外推 |

因此当前可宣称“Alt 已写入后台数据”，不能宣称“编辑器或公开主题已完成 SEO Alt 输出”。Caption 是当前已验证能在编辑器中可见的图片说明。

### 两层锁与单次保存

含图片正文使用文章级 operation lock：默认路径为 `${manifestPath}.${siteKey}.${postId}.operation.lock`。它覆盖精确页面预检、逐 occurrence 源图复核、原位绑定、audit、`bindingProof`、保存前再次逐图复核、整篇一次保存、后台回读、编辑器健康检查和最终清单写入。第二个任务遇到锁时必须在构建和请求前停止。

清单原子写入仍使用 `${manifestPath}.lock`。两种锁都不得自动删除或绕过；只有同时确认锁已陈旧、无打开句柄、无活动写进程、无待提交临时文件，并在私有运行区留下恢复证据后，才允许人工恢复。

`onProgress` 的逐图事件只表示“逐 occurrence 校验和内存绑定”，不表示每张图片都远程保存一次。无论正文有几张图，远程文章保存始终整篇只发一次。若远程保存与回读完成后本地 manifest 写入失败，返回 `article_manifest_write_failed_after_save`，并保持 `requestMayHaveSucceeded: true`、`automaticRetryAllowed: false`；不得自动重发文章。

机器合同见 [article-image-binding-contract.json](article-image-binding-contract.json)，实现与测试见 [article-image-binding.mjs](article-image-binding.mjs) 和 [article-image-binding.test.mjs](article-image-binding.test.mjs)，当前对抗复核证据见 [article-image-binding-adversarial-review.redacted.md](article-image-binding-adversarial-review.redacted.md)。

## 7. 删除媒体记录

```js
const deleted = await adapter.deleteAllinCmsMediaDirect({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  mediaId: "精确 24 位 media ID",
  expectedTitle: "精确标题",
  expectedUrl: "精确 https://assets.laicms.com/{site_key}/... URL",
  authorizationConfirmed: true,
});
```

不要批量猜 ID，不要把一次授权扩展到其他记录，不要自动重发歧义删除。成功状态为 `media_record_deleted_and_verified`：只证明精确媒体卡和 RSC 媒体记录已消失。默认不再探测底层对象或 CDN 是否物理删除。

## 8. 漂移和回退

出现登录重定向、401 / 403、action / deployment / site ID / router tree 不唯一、请求计数异常、响应类型漂移、媒体记录或公开 URL 验证失败时：

```text
停止写入
→ 调用 reconcileAllinCmsMediaDirect() 只读对账
→ 保存失败阶段和证据
→ 不重传、不自动 UI、不自动改走 PicGo
→ 用户批准后，才用一张新的虚拟图片重新捕获合同或使用语义化 UI 回退
```

## 9. 本地验证命令

```bash
node --check upload-media-browser.mjs
node --check article-image-binding.mjs
npm test
python3 -m json.tool media-operations-contract.redacted.json
python3 -m json.tool article-image-binding-contract.json
```

当前 131 项本地测试包括 45 项媒体测试、50 项文章图片测试和 36 项文章生命周期与 taxonomy 测试，覆盖严格串行、授权时效与 TOCTOU 边界、延迟对账、禁止盲目重传、原子索引、单写者锁、断点恢复、A/B/A 复用、源文哈希和锚点防漂移、Caption 全数组结构预检、后台回读，以及 Slate 编辑器、图片数量、解码、Caption 和草稿状态健康闸。本地测试不替代真实部署证据。

## 当前边界

```yaml
default_allincms_upload: uploadAllinCmsMediaSerial
direct_server_action_replay_single: verified_remote_2026_07_27
direct_single_requests_serial_batch_10: verified_remote_2026_07_27
read_only_reconciliation: implemented_and_local_tested
atomic_image_index_and_lock: implemented_and_local_tested
cross_restart_recovery: implemented_and_local_tested
prepared_title_collision_guard: implemented_and_local_tested
request_started_normalized_hash_recovery: implemented_and_local_tested
remote_recovery_e2e: not_verified
one_multipart_request_with_10_files: not_verified
parallel_upload_allowed: false
content_binding: verified_remote_draft_A_B_A_2026_07_27
article_binding_entry: article-image-binding.mjs
article_binding_local_tests: 50_passed
article_draft_backend_readback: verified_remote_2026_07_27
article_editor_render_after_reload: verified_remote_2026_07_27
article_editor_caption_visible: verified_remote_2026_07_27
article_editor_dom_alt: missing_observed_3_of_3_2026_07_27
published_theme_alt_for_current_A_B_A_run: not_run_not_authorized
media_record_delete_direct: verified_remote_2026_07_27
media_editor_fields_title_alt_caption: observed_2026_07_27
direct_metadata_update_contract: discovered_and_one_authorized_remote_write_verified_2026_07_27
ai_metadata_to_private_index: implemented_local_tested
ai_metadata_to_allincms_title_alt_caption: one_authorized_remote_sample_verified_with_delayed_read_visibility
physical_asset_cleanup_after_delete: out_of_scope
publication_status: PASS_DRAFT_BINDING_WITH_DOCUMENTED_ALT_PRODUCT_GAP__BLOCK_PUBLISHING_AND_CROSS_DEPLOYMENT
```

## 本目录

| 文件 | 用途 |
|---|---|
| `AI-START-HERE.md` | 其他 AI 必须先读的唯一执行入口 |
| `media-operations-contract.redacted.json` | 机器可读的默认路由、函数、索引、元数据和停止规则 |
| `media-metadata-and-ai-vision-sop.md` | AI 读图、元数据职责、串行上传与不重传规则 |
| `upload-media-browser.mjs` | 预检、任意数量严格串行总控、延迟对账与有限重试、单张上传、元数据更新、有限只读复核、索引、删除和 UI 回退 |
| `upload-media-browser.test.mjs` | 不触碰远端的媒体本地故障测试 |
| `article-image-binding-contract.json` | 正文图片资产、occurrence、Slate、保存和渲染闸机器合同 |
| `article-image-binding.mjs` | Markdown 原位解析、清单、映射复核、Slate 构建、草稿保存和编辑器健康闸 |
| `article-image-binding.test.mjs` | 50 项不触碰远端的文章图片测试 |
| `package.json` | 测试命令和 PNG / JPG 规范化依赖声明 |
| `observed-contract.redacted.json` | 去敏后的观察型内部接口形状和漂移合同 |
| `direct-serial-10-verification.redacted.md` | 10 张串行真实验证的去敏证据与边界 |
| `direct-delete-verification.redacted.md` | 零点击媒体记录删除的历史去敏证据；物理资产状态已退出当前完成口径 |
| `verify-media.mjs` | 无登录态公开 URL 验证器 |
| `fixtures/` | 只放无敏感信息的虚拟测试图片 |

## 内容变更授权入口

文章、分类、标签及正文图片草稿 mutation 只接受结构化 `authorizationContext`，不接受 `true`/`false`。使用 `mutation-authorization.mjs` 创建与准确 `site_key`、operation 和目标摘要绑定的上下文；actor 为 `human-asserted`、身份状态为 `not_verified`，有效期最长 30 分钟。adapter 会在每次远程请求前重验；任一字段、目标或时间不匹配即停止。该上下文不替代 publish/delete 的独立人工批准，也不证明正式发布资格。
