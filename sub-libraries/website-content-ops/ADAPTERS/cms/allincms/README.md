---
title: "AllinCMS Media and Article Image Operations Adapter"
description: "供其他 AI 从唯一入口执行 AllinCMS 严格串行图片上传、正文图片原位绑定、AI 元数据同步和媒体记录删除。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-30"
sources: ["../allincms-overview.md", "observed-contract.redacted.json", "direct-serial-10-verification.redacted.md", "direct-serial-11-article-verification.redacted.md", "image-index-e2e-verification.redacted.md", "direct-delete-verification.redacted.md", "Observed signed-in media upload and delete runs 2026-07-27"]
related: ["AI-START-HERE.md", "media-metadata-and-ai-vision-sop.md", "../allincms-overview.md", "article-operations.md", "article-operations.mjs", "article-operations-contract.json", "article-operations.test.mjs", "upload-media-browser.mjs", "verify-media.mjs", "media-operations-contract.redacted.json", "observed-contract.redacted.json", "direct-delete-verification.redacted.md"]
confidence: "high"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# AllinCMS 图片上传、文章原位绑定与媒体记录删除 Adapter

> **其他 AI 不要从本页重新研究。媒体与文章正文图片的唯一执行入口是 [AI-START-HERE.md](AI-START-HERE.md)。** 媒体使用 `upload-media-browser.mjs`；Markdown 正文图片使用 `article-image-binding.mjs`。文章发布仍需单独明确授权。

## 权威边界

本目录是当前 AllinCMS 部署实测 Adapter 和合同的权威来源。共享的 `allincms-bulk-content-upload` Skill（安装位置由宿主环境决定） 只提供调用编排、入口和 SOP；如果共享 Skill 的旧模板与本目录冲突，以本目录的 `article-operations.mjs`、`article-operations-contract.json`、`article-image-binding.mjs` 和对应验证证据为准。

文章生命周期从 [article-operations.mjs](article-operations.mjs) 进入；正文 Markdown 图片绑定从 [article-image-binding.mjs](article-image-binding.mjs) 进入。不要把图片 companion 的 draft-only 合同误当成完整文章发布合同。

## 给其他 AI 的最短入口

先读 [AI 唯一入口](AI-START-HERE.md)、[图片元数据与 AI 读图 SOP](media-metadata-and-ai-vision-sop.md) 和 [机器合同](media-operations-contract.redacted.json)，再导入 [操作模块](upload-media-browser.mjs)。**AllinCMS 图片上传的唯一默认入口是 `uploadAllinCmsMediaSerial()`**；它负责任意数量图片的逐张接口上传、自动刷新、延迟只读对账、确认缺失后的有限重试、原子索引和断点恢复；开启 `syncRemoteMetadata` 后，还会在当前图片上传完成后同步并复核 `title / alt / caption`，再进入下一张。`uploadAllinCmsMediaDirect()` 只是总控内部使用的单张原语，其他 AI 不得围绕它另写 `for` 循环。元数据单张原语为 `updateAllinCmsMediaMetadataDirect()`；删除单独使用 `deleteAllinCmsMediaDirect()`，两者都必须遵守当前批次或当前目标的明确授权。默认上传与直接删除都调用当前部署的 Next Server Action，**不点击按钮、不打开文件选择器或确认框，也不导出 cookie 或 token**。

固定路线如下，后续 AI 不得自行换序：

```text
P1  checkAllinCmsMediaRuntime() → uploadAllinCmsMediaSerial()
P2  uploadAllinCmsMediaDirect() 仅作为总控内部单张原语
P3  updateAllinCmsMediaMetadataDirect() 只发一次字段写入并有限只读复核
P4  reconcileAllinCmsMediaDirect() 仅做只读上传对账
P5  uploadAllinCmsMediaBatch() 仅在用户明确批准后做 1–5 张 UI 回退
P6  PicGo + R2 / GitHub / COS / OSS 仅在目标是外部图床或用户明确指定时使用
```

UI 与外部图床都不是接口失败后的自动降级。

```text
本地 PNG / JPG / WebP
→ Node 内存中规范化为 WebP
→ 动态读取当前 deployment、uploadMedia action 和 Next router tree
→ 当前登录页面同源 fetch
→ 刷新读取媒体记录
→ 返回 media_id + 最终 HTTPS URL
→ 匿名 GET、Content-Type、图片解码和持久化验证
```

当前验证边界：

- 纯接口直传：已验证单张，也已验证 10 张采用“单图接口串行调用、逐张全链验收、结果不明先停并对账”；
- 语义化 UI 回退：已验证一次 1–5 张；
- 媒体记录删除：已验证一条精确目标的零点击直接删除；完成口径只看媒体卡和 RSC 记录消失，不再检查底层对象或 CDN；
- 媒体元数据：已验证一张虚拟图片只发一次更新请求；稍后新鲜刷新后 title、alt、caption 全部持久化，media ID / URL 未变；
- 一次 multipart 传 10 张、覆盖和内容绑定：未验证；上传及元数据写入都禁止并发和自动重发，不作为后续提速方向。

## 文章正文图片 companion

文章正文图片已经有唯一可执行 adapter，不再只是一页参考逻辑：

- 实现：[article-image-binding.mjs](article-image-binding.mjs)；
- 机器合同：[article-image-binding-contract.json](article-image-binding-contract.json)；
- 本地测试：[article-image-binding.test.mjs](article-image-binding.test.mjs)；
- 对抗复核证据：[article-image-binding-adversarial-review.redacted.md](article-image-binding-adversarial-review.redacted.md)；
- 文章对象、分类、标签、封面和发布边界：[article-operations.md](article-operations.md)；可执行生命周期：[article-operations.mjs](article-operations.mjs)。

固定模型必须拆成：

```text
asset = 源 SHA-256 / MD5 + media ID + public URL
occurrence = 原文位置 + 前后锚点 + 页面语境 + Alt + Caption
```

同一远端资产可以在正文按 `A → B → A` 复用，但三处 occurrence 不能合并。manifest 必须使用 schema 2；每个 occurrence 独立保存绝对源路径、SHA-256、MD5、位置和语境。相同字节来自不同路径时可复用远端资产，但每个路径仍必须在构建前和保存前分别串行重读。禁止全局字符串替换、文件名模糊替换、手写 Slate 图片节点和伪造 `bindingProof`。

含图片正文的唯一远程入口是 `bindAndSaveAllinCmsArticleDraftDirect()`。它在文章级 operation lock 内逐 occurrence 校验和原位绑定，生成并复核 `bindingProof`，然后把完整草稿只保存一次，再做后台回读、编辑器健康检查和 manifest 原子写入。`onProgress` 可以让用户看到图片逐张被处理，但不得把它实现为“每张图远程保存一次”。其他 AI 不得直接用 `saveAllinCmsArticleDraftDirect()` 保存图片正文，也不得重新抓接口或绕过锁。

正文 Caption 必须是 Plate/Slate 文本节点数组：

```json
"caption": [{"text": "可见图片说明"}]
```

字符串 Caption 已在 2026-07-27 的虚拟草稿验证中导致文章编辑页 500。adapter 会在请求前阻断错误结构，并在后台回读后继续检查编辑页非 500、图片解码和 Caption 可见。HTTP 200 不能单独判成功。

当前 A/B/A 草稿验证：2 个唯一资产形成 3 个正文位置，顺序、位置、URL、后台 Alt、后台 Caption、编辑器渲染和图片解码均通过，页面保持草稿且未发布。编辑器 DOM 的 3 张正文图均没有 `alt` 属性，因此当前只能宣称“后台 Alt 已持久化”；本轮没有授权验证公开主题 Alt。

含图片正文有两层锁：`${manifestPath}.${siteKey}.${postId}.operation.lock` 覆盖构建、一次远程保存、回读、编辑器健康检查和 manifest 落盘；`${manifestPath}.lock` 只保护 manifest 的原子 temp-rename。任一锁冲突都必须停止；只允许在私有运行区确认无活动写者、无打开句柄、无待提交临时文件并留下证据后人工恢复陈旧锁，禁止自动绕过。若文章已保存但 manifest 写失败，报告 `article_manifest_write_failed_after_save`，禁止自动重发。

## 为什么必须先打开对应媒体页

当前 adapter 不是脱离浏览器运行的公开 API 客户端。打开目标后台媒体页有四个作用：

1. 取得当前有效的登录会话，但不导出 Cookie 或 Token；
2. 用 URL 中的 `site_key` 锁定写入目标，避免多站点账号写错网站；
3. 动态发现当前 deployment、`uploadMedia` / `deleteMediaAction`、内部 `site_id` 和 router tree；
4. 上传前检查媒体库中是否已经存在同标题记录，上传后刷新对账。

因此，当前安全合同是：

```text
打开并加载目标后台媒体页
→ 确认登录状态与 site_key
→ 才允许接口上传或经单独授权的媒体记录删除
```

**技术上不要求页面始终处于前台**：标签页加载完成后放到后台仍可零点击、零文件选择器上传。但面向小白、课程演示和用户监督时，默认保持媒体页可见，并采用“上传一张 → adapter 自动刷新 → 用户看到新增卡片 → 完成验收与索引 → 再上传下一张”。这里的刷新由 adapter 导航完成，不是模拟点击。若完全不打开该页面，理论上只能改成导出登录凭据、硬编码内部动作值，或者等待 AllinCMS 提供稳定公开 API；这三种都不属于当前已验证方案。

## 为什么不硬编码接口

AllinCMS 当前没有已确认的公开开发者 API。抓到的是部署相关的 Next.js Server Action：动作 ID 和构建指纹可能变化。因此 adapter 每次从当前页面和已加载 JS chunk 动态发现：

- 当前内部 `site_id`；
- `uploadMedia` 或 `deleteMediaAction` Server Action ID；
- `next-router-state-tree`；
- `x-deployment-id`。

这些运行值只保留在内存中。公开文件只记录字段结构、长度、散列和验证结论。

## Codex Browser 用法

前提：AI 必须先在受控浏览器中打开并加载完成**目标网站的 AllinCMS 后台媒体页** `https://workspace.laicms.com/{site_key}/media`，确认仍处于登录状态且 URL 中的 `site_key` 与用户选择的网站一致；然后才能开始接口上传。这里不是目标网站前台首页。技术上媒体页可以放在后台，但面向小白、课程演示和用户监督时默认保持可见：adapter 每上传一张就自动刷新一次，用户会看到媒体库逐张增加。该标签页不能关闭；文件名 stem 还必须在媒体库中唯一。

```js
const adapter = await import(
  "<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/upload-media-browser.mjs"
);
```

### 默认：预检后串行上传任意数量

不要自己循环调用单张原语。先做只读预检，再把同一批文件交给串行总控：

```js
const localFiles = [
  {
    localFile: "/absolute/private-runtime/source/01.png",
    description: "电动自行车轮毂电机产品图",
    alt: "Rear hub motor for commuter e-bike",
    notes: "用于产品页和后续 SEO 内容",
  },
  "/absolute/private-runtime/source/02.webp",
];

const readiness = await adapter.checkAllinCmsMediaRuntime({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  localFiles,
});
if (readiness.status !== "ready") {
  throw new Error(readiness.errors.join("; "));
}

const authorizationContext = await adapter.createAllinCmsMediaUploadAuthorizationContext({
  localFiles,
  expectedSiteKey: "用户确认的 site_key",
  entrypoint: "serial",
  approvalActor: "当前明确批准这批精确文件的人类用户",
});

const result = await adapter.uploadAllinCmsMediaSerial({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  imageIndexPath: "/absolute/private-runtime/media/image-index.json",
  localFiles,
  authorizationContext,
  progressMode: "visible",
  onProgress(event) {
    console.log(`[${event.position}/${event.total}] ${event.stage}: ${event.filename}`);
  },
});
```

`authorizationContext` 必须由调用者显式提供，不能省略，也不能用 `beforeRequest` 代替。它精确绑定 `site_key`、操作 `allincms.media.upload`、入口、按顺序排列的文件名/字节数/SHA-256 digest、`approval_actor`、`approved_at` 和最长 30 分钟的 `expires_at`。`approved_at` 晚于当前时间一律拒绝；授权在 `now >= expires_at` 时失效，因此 29:59.999 可执行，30:00.000 起必须重新批准。

四个入口先拒绝最终路径为 symlink 的输入，再通过文件描述符只读一次并冻结源字节快照。direct 只从该快照规范化并生成请求；serial 给每次单图 mutation edge 传同一快照；batch/single 给文件选择器传内存 Buffer payload，而不是再次交出原始路径。原路径在快照形成前换字节会因 digest 不一致而 fail closed；快照形成后原路径再变化不会改变本次实际发送字节。`beforeRequest` 返回后、direct 的 `sendReplay` 前，以及 batch/single 的确认点击前，adapter 都会重新校验完整授权、当前时间、逐文件快照和实际 chooser payload digest。actor 仅为 `human-asserted` 声明，身份状态固定 `not_verified`。

`imageIndexPath` 必须是客户私有运行区中的绝对路径，不得放入或提交到公开母库。默认流程固定为：

```text
prepared
→ request_started
→ 一次单图直接接口请求
→ adapter 自动刷新媒体页
→ 验证唯一卡片、RSC media ID、最终 URL、匿名 GET 和图片解码
→ 原子写入源 / 上传 / 远端指纹及说明
→ 当前图片 verified 或 reconciled 后才处理下一张
```

报告批次成功前至少检查：

```js
result.status === "completed";
result.completed === localFiles.length;
result.cleanup.imageIndexLockReleased === true;
result.items.every((item) => [
  "uploaded_and_indexed",
  "reconciled_and_indexed",
  "reconciled_existing",
  "reused_verified_mapping",
].includes(item.status));
```

同一源文件以 SHA-256 为主键；即使改名，只要私有索引已有 verified 映射，默认复用而不重复上传。索引分别保存源 MD5 / SHA-256、规范化上传 MD5 / SHA-256、media ID、URL、远端 MD5 / SHA-256、说明、alt 和用途备注。平台可能重编码图片，三组哈希不得互相代填。

### 依赖与停止规则

- 小于等于 1 MB 的 WebP 可不依赖 `sharp`；PNG、JPG 和较大 WebP 需要本目录 [package.json](package.json) 声明的 `sharp`。
- 缺依赖时由 `checkAllinCmsMediaRuntime()` 阻断受影响文件；不得偷偷改用 UI。安装依赖属于机器状态变更，须先获得用户批准。
- `upload_result_ambiguous`、`request_started` 中断、请求后刷新失败或 RSC 读取失败，都必须先调用只读 `reconcileAllinCmsMediaDirect()`；不得自动重传。
- `stopped_index_write_failed` 表示远端可能已经成功但本地映射没安全落盘；立即停止下一张，修复索引后从只读对账恢复。
- `stopped_retry_exhausted` 表示当前图片每次报错后都已延迟并确认远端不存在，但已达到最大尝试次数；停止本批。
- `stopped_preexisting_title_collision` 表示索引仍在 `prepared` 阶段、请求尚未开始，但远端已有同标题记录；不得把该记录自动认领为当前源图，必须改唯一标题或人工核对。
- `request_started` 恢复并对账成功时，索引必须保留请求前已经记录的规范化上传 SHA-256 / MD5，不得被空值覆盖。
- `${imageIndexPath}.lock` 已存在时，第二个 AI / 进程必须停止，不得删除锁后抢写。若结束时 `cleanup.imageIndexLockReleased !== true`，上传结果仍保留，但必须人工检查私有运行区中的锁文件，下一轮不得直接开始。

2026-07-27 的真实远程证据覆盖单张直传、10 张单图严格串行、一次 5 张中的受控刷新对账、一张获批虚拟媒体的 `title / alt / caption` 最终持久化，以及 A/B/A 正文原位绑定草稿。2026-07-29 本地回归为媒体上传 45/45、adapter 全量 131/131；负向用例覆盖四入口缺失授权、site/operation/entrypoint/actor/digest 篡改、同路径换字节、symlink retarget、批次中途替换、chooser payload 篡改、29:59.999 / 30:00.000 / 30:00.001 边界、future timestamp，以及 callback 延迟跨过 expiry，且均未访问真实 CMS。正文绑定前另会复核本地图片字节未变化、远端映射源 SHA-256 与资产一致、候选携带已知 media ID/URL，并对后台 Caption 结构再次验形；标题相同不构成资产归属证据。**本地 PASS 只证明隔离控制器合同；新快照/时效逻辑、恢复层、自定义标题和跨部署元数据稳定性仍待下一次自然、获批的真实操作顺带复验**，不得为测试重复写入。

### 单张原语：仅供 adapter 维护者

`uploadAllinCmsMediaDirect()` 是 `uploadAllinCmsMediaSerial()` 的内部上传原语，不是其他 AI 的默认入口。只有维护 adapter、做合同漂移诊断或编写隔离测试时才直接调用；业务调用不得复制手写循环绕过私有索引、锁和恢复状态机。 即使由上层串行总控调用，direct 原语也必须收到与当前单文件绑定的授权上下文并自行验证；可选 `beforeRequest` 只负责 journaling，不能放宽或替代授权。

### 已验证：零点击删除一条媒体记录

删除属于独立高风险动作，必须取得用户对本次具体媒体的明确授权，并同时提供 `siteKey + mediaId + title + URL`：

```js
const deleted = await adapter.deleteAllinCmsMediaDirect({
  tab,
  expectedSiteKey: "用户确认的 site_key",
  mediaId: result.media.mediaId,
  expectedTitle: result.media.title,
  expectedUrl: result.media.url,
  authorizationConfirmed: true, // 仅在用户已明确授权本次具体删除后填写
});
```

只有 `serverAction200`、`mediaCardRemoved`、`mediaRecordRemoved` 和 `contractVerified` 全部为 `true`，才能报告“媒体记录已删除”。本次真实验证中，删除后的公开图片 URL 仍返回 `200 image/webp`，因此不得报告“图片对象已清理”或“URL 已失效”。完整规则见 [零点击删除验证](direct-delete-verification.redacted.md)。

### 回退：1–5 张语义化 UI 上传

仅在单图直接回放因部署漂移失败、或用户明确需要一次 2–5 张且接受浏览器选择文件时使用：

```js
const localFiles = [
  "/absolute/path/to/01.png",
  "/absolute/path/to/02.png",
];
const authorizationContext = await adapter.createAllinCmsMediaUploadAuthorizationContext({
  localFiles,
  expectedSiteKey: "用户确认的 site_key",
  entrypoint: "batch",
  approvalActor: "当前明确批准该精确文件列表的人类用户",
});
const result = await adapter.uploadAllinCmsMediaBatch({
  tab,
  localFiles,
  expectedSiteKey: "用户确认的 site_key",
  authorizationContext,
});
```

这个回退会打开一次文件选择器并提交一次 Server Action。失败后禁止自动重传整批，先按 `result.items[]` 对账。

## 已验证事实

2026-07-27 的真实验证包括：

1. 单张 WebP 通过页面原生 `fetch` 直接 POST 到 `/{site_key}/media`；
2. 直传过程 `ui_clicks=0`、`filechooser_events=0`、目标接口请求数为 1；
3. 请求为 Next Server Action multipart，文件字段为 `_1_files`，参数字段为 `0`，参数形状为 `[site_id, "$K1"]`；
4. 必要动态头包括 `next-action`、`next-router-state-tree` 和 `x-deployment-id`，`Content-Type` 边界由 `FormData` 自动生成；
5. 响应为 HTTP 200、`text/x-component`；
6. 刷新后媒体记录仍存在，并包含媒体 ID、最终 URL、类型、大小和对象路径；
7. 匿名下载返回远端内容 SHA-256 / MD5；平台可能重编码图片，因此远端哈希不得由本地哈希代填；
8. 最终 URL 可匿名 HTTPS GET，Content-Type 为图片，ETag 存在且图片可实际解码；
9. 五图 UI 回退仍是一次文件选择、一次提交、一个 Server Action、五条媒体记录；
10. 十张 WebP 通过 10 次单图接口串行调用完成：UI 点击 0、文件选择器 0、接口请求验收 10/10、HTTP 200 10/10、刷新持久化 10/10、匿名 HTTPS 与图片解码 10/10；
11. 第九张首次出现客户端 evaluate 超时，系统先停、查媒体库确认同标题记录不存在，再受控继续；没有盲目重传；
12. 另一轮 5 张测试同样采用 5 次单图接口串行调用，最终图片、媒体 ID 与链接映射均为 5/5，UI 点击和文件选择器均为 0；
13. 该 5 张测试的第 5 张接口已返回 200、图片卡与公开 URL 已成立，但首次刷新未及时读到 RSC media ID；流程没有重新上传，而是停止后按唯一标题做一次受控刷新对账，随后补齐唯一媒体记录与映射；
14. 本次没有观察到独立预签名 PUT；
15. 一张唯一虚拟媒体通过直接删除 Server Action 完成：UI 点击 0、确认框 0、请求 1 次、HTTP 200，刷新后媒体卡和 RSC 记录均消失；
16. 历史测试曾观察到删除媒体记录后原公开 URL 仍可访问；该事实保留在历史证据中，但底层对象或 CDN 是否物理删除已退出当前完成口径，不再阻断媒体记录删除成功。

## 已实查的图片信息字段

2026-07-27 在当前已登录媒体页先完成字段检查，随后对一张用户明确授权的虚拟图片执行了一次元数据接口写入，并在新鲜页面刷新后复核：

- 上传弹窗只有文件选择、格式与 5 MB 限制，没有 title、alt 或说明字段；
- 上传后编辑弹窗有 `title`（标题）、`alt`（替代文本）、`caption`（说明）；
- adapter 已提供 `updateAllinCmsMediaMetadataDirect()`；`uploadAllinCmsMediaSerial()` 开启 `syncRemoteMetadata: true` 后，可在每张图片上传并入库后同步 `title / alt / caption`；
- AI 可先读图，把候选 `title / alt / caption` 与完整 `description / metadata` 写入客户私有索引；AllinCMS 没有独立 `description` 字段；
- 一次真实虚拟样本只发送 1 次字段写请求。第一次紧接读取时只看到部分字段，稍后新鲜页面刷新后三字段均持久化，media ID / URL 未变；该现象按读后写延迟处理；
- 每张元数据写请求最多 1 次，随后仅按 0 / 750 / 2000 ms 做有限只读复核；仍不明确时保留已上传媒体并停止本批，不重发字段请求、不重传图片；
- 自定义 `title` 在写入前先检查目标标题不存在；撞名时在请求前停止。

详见 [图片元数据与 AI 读图 SOP](media-metadata-and-ai-vision-sop.md)。

## Adapter 的防错设计

- 站点名称与 `site_key` 双重确认，不默认第一个站点；
- 纯接口上传前要求已经位于确认后的媒体页；
- 拒绝重复路径、重复 filename stem 和媒体库已有同标题；
- PNG/JPG 在 Node 内存中转换为 WebP，不产生凭据文件；
- GIF 的直接规范化尚未验证，直接模式会停止而不是静默破坏动画；
- 每次动态发现 action 和 deployment，不长期硬编码；
- 上传报错后先等待并刷新媒体库做精确只读对账；已存在则补齐，只有确认不存在且当前图片仍有尝试次数时才重试；
- 只接受一个目标 Server Action；
- 刷新后把媒体卡 URL 与 RSC 媒体对象、标题和媒体 ID 一一核对；
- 最终链接再用不带登录态的 Node HTTPS GET 验证；
- 删除前要求 `siteKey + mediaId + title + URL` 四项精确一致且只匹配一条；删除结果不明时绝不自动重发；默认只验媒体卡和 RSC 记录消失，不探测物理资产；
- 永久禁止并发上传；不使用 `Promise.all`、任务池、多标签或重叠请求；
- AI 元数据先写私有索引；元数据更新失败或不明确时保留上传成功事实并停止本批，不得继续下一张、重发字段请求或重新上传图片；
- 真实 `site_key`、媒体 ID、对象 key、完整动作值和最终 URL不写入公开知识库。

## 漂移与失败处理

出现以下任一情况立即停止，不要改用坐标点击蒙混过去：

- 401 / 403 / 登录重定向；
- 找不到唯一 `uploadMedia` 或 `deleteMediaAction`；
- 找不到当前 `site_id`、router tree 或 deployment；
- Server Action 不是一次、响应不是 200 或类型不再是 `text/x-component`；
- 200 后刷新看不到对应媒体记录；
- 最终 URL 不能匿名访问或图片不能解码。

处理顺序：

```text
先查媒体库是否已经生成同标题记录
→ 已生成：返回并标注验证缺口，不重传
→ 未生成：记录漂移阶段
→ 回到一张新虚拟图重新捕获合同
→ 只有用户明确同意时才使用 UI 回退
```

## 当前状态

```yaml
direct_server_action_replay_single: verified
direct_single_requests_serial_batch_10: verified
one_multipart_request_with_10_files: not_verified
parallel_upload_allowed: false
ui_clicks_required_for_direct_single: false
filechooser_required_for_direct_single: false
semantic_browser_single_upload: verified
semantic_browser_batch_upload_5: verified
source_sha256_reuse_and_atomic_index: implemented_local_tested
cross_restart_read_only_recovery: implemented_local_tested
prepared_title_collision_guard: implemented_local_tested
request_started_normalized_hash_recovery: implemented_local_tested
remote_recovery_e2e: not_verified
content_binding: verified_remote_draft_A_B_A_2026_07_27
article_binding_entry: article-image-binding.mjs
article_binding_tests: 50_passed
article_operations_tests: 36_passed
article_adapter_local_tests: 131_passed_2026_07_30
article_editor_render_gate: verified_remote_2026_07_27
article_editor_dom_alt: missing_observed_3_of_3_2026_07_27
published_theme_alt_current_run: not_run_not_authorized
article_update_publish_remote_current_deployment: verified_scoped_11_serial_2026_07_27
article_post_create_api: blocked_live_contract_not_reverified
article_remote_failure_injection_recovery: blocked_not_verified
media_record_delete_direct: verified
media_editor_fields_title_alt_caption: observed
direct_metadata_update_contract: captured_and_one_authorized_remote_write_verified
ai_metadata_to_private_index: implemented_local_tested
ai_title_alt_caption_to_allincms: implemented_local_tested_and_one_remote_sample_verified
physical_asset_cleanup_after_delete: out_of_scope
publication_status: PASS_DRAFT_BINDING_WITH_DOCUMENTED_ALT_PRODUCT_GAP__BLOCK_PUBLISHING_AND_CROSS_DEPLOYMENT
```

## 本目录

| 文件 | 用途 |
|---|---|
| `AI-START-HERE.md` | 其他 AI 必须先读的唯一执行入口 |
| `media-operations-contract.redacted.json` | AI 可机读的上传 / 删除 / 元数据函数、前置条件和停止规则 |
| `media-metadata-and-ai-vision-sop.md` | AI 读图、title / alt / caption 职责、事实闸和不重传规则 |
| `observed-contract.redacted.json` | 去敏后的接口形状、验证和漂移合同 |
| [direct-serial-10-verification.redacted.md](direct-serial-10-verification.redacted.md) | 10 张单图接口串行调用的去敏证据与边界 |
| `direct-serial-11-article-verification.redacted.md` | 11 篇文章完整字段 `update → publish` 串行验证的去敏证据与边界 |
| [image-index-e2e-verification.redacted.md](image-index-e2e-verification.redacted.md) | 私有图片索引、断点恢复与去重闭环的去敏证据及适用边界 |
| `direct-delete-verification.redacted.md` | 零点击媒体记录删除的历史去敏证据；当前完成口径只看卡片与 RSC 记录 |
| `upload-media-browser.mjs` | 运行预检 + 任意数量永久串行总控 + 报错延迟对账与有限重试 + 单图接口原语 + AI title/alt/caption 同步 + 原子私有索引 + 零点击媒体记录删除 + 1–5 图 UI 回退 |
| `upload-media-browser.test.mjs` | 45 项媒体本地故障与授权边界测试；不等同于所有部署的真实远程生产验证 |
| `article-image-binding-contract.json` | 正文图片的资产、occurrence、Slate、保存、渲染和 Alt 分层合同 |
| `article-image-binding.mjs` | Markdown 原位解析、映射复核、Slate 构建、草稿保存与编辑器健康闸 |
| `article-image-binding.test.mjs` | 50 项文章图片本地测试；包含 A/B/A、锚点防漂移、Caption 全数组预检，以及编辑器、图片解码、Caption 和草稿状态健康闸 |
| `package.json` | adapter 的本地测试命令与 `sharp` 规范化依赖声明 |
| `verify-media.mjs` | 无登录态公开 URL 验证器 |
| `fixtures/` | 只放无敏感信息的虚拟测试图片 |

## 依赖安装

该 adapter 的 Node 依赖由 `package.json` 和 `package-lock.json` 固定。需要执行本地工具测试时，在本目录运行：

```bash
npm ci
npm test
```

这只验证本地 adapter 合同和测试，不等于 AllinCMS 官方 API、跨部署或外部发布通过。

## 结构化内容 mutation 授权

文章、分类、标签和正文图片草稿写入统一要求结构化 `authorizationContext`；裸布尔值不会授权任何请求。`mutation-authorization.mjs` 将授权精确绑定到当前 `site_key`、operation、目标 SHA-256 摘要、具名 `human-asserted` actor、批准时间和最长 30 分钟有效期，并在每次远程请求前重验。actor 身份状态固定为 `not_verified`，不能据此宣称真人批准。publish/delete 仍需独立明确人工批准；本地 131 项测试和 npm 包检查不证明真实 CMS、跨部署稳定或正式发布资格。
