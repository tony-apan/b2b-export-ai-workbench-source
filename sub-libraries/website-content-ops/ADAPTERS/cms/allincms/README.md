---
title: "AllinCMS Workspace, Media and Article Operations Adapter"
description: "供其他 AI 从唯一入口执行 AllinCMS API-first 登录/用户/站点发现、计划驱动的严格串行内容操作、图片上传和文章操作。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-12"
sources: ["../allincms-overview.md", "observed-contract.redacted.json", "direct-serial-10-verification.redacted.md", "direct-serial-11-article-verification.redacted.md", "image-index-e2e-verification.redacted.md", "direct-delete-verification.redacted.md", "Observed signed-in media upload and delete runs 2026-07-27"]
related: ["AI-START-HERE.md", "content-run-controller.mjs", "live-run-evidence.schema.json", "INTERFACE-INDEX.md", "interface-registry.json", "interface-registry.schema.json", "workspace-preflight.md", "workspace-preflight.mjs", "workspace-preflight-contract.json", "media-metadata-and-ai-vision-sop.md", "../allincms-overview.md", "article-operations.md", "article-operations.mjs", "article-operations-contract.json", "article-operations.test.mjs", "upload-media-browser.mjs", "verify-media.mjs", "media-operations-contract.redacted.json", "observed-contract.redacted.json", "direct-delete-verification.redacted.md"]
confidence: "high"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# AllinCMS Workspace、图片与文章操作 Adapter

> 用户资料驱动的新建/更新流程以 `<SUB_LIBRARY_ROOT>/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md`、`SCHEMAS/source-extraction.schema.json` 和 `SCHEMAS/content-operation-plan.schema.json` 为上游业务合同；本目录是当前 AllinCMS 运行时适配真源。它动态发现登录用户、网站、字段、枚举、Action/部署合同并严格执行已规划操作，不拥有客户事实，也不允许把测试站、一次部署 Action ID 或历史产品字段固化为跨部署保证。`confirmed/inferred` claim 必须绑定精确 locator/extraction digest，mutation 字段必须绑定 `claim_refs/derivation`；公开写入只消费 `approved/not-applicable` 来源。
> **当前能力边界：** 任何远程 mutation 只接受未过期的 `live_verified_current_deployment` capability。新站必须拆成 account-scope Plan A 和真实 readback 后的 site-scope Plan B，不能 create site + populate 混在一个计划。当前 create-site 仅有 `local_tested` 请求构造器、产品仍为 `exploration_only`；二者都不能被文档或历史 payload 升级为稳定远程创建/更新/发布能力。


> **其他 AI 不要从本页重新研究。统一启动入口是 [AI-START-HERE.md](AI-START-HERE.md)。** 已批准的跨对象内容计划由 `content-run-controller.mjs` 严格串行调度；媒体使用 `upload-media-browser.mjs`；Markdown 正文图片使用 `article-image-binding.mjs`。发布必须作为精确 operation 明列在获批计划内；原计划未包含发布时，必须生成新的计划并重新授权，不能在执行中临时加操作。

## 权威边界

本目录是当前 AllinCMS 部署实测 Adapter 和合同的权威来源。共享的 `allincms-bulk-content-upload` Skill（安装位置由宿主环境决定）只提供调用编排、入口和 SOP；如果共享 Skill 的旧模板与本目录冲突，以本目录的 Workspace、文章、媒体实现、机器合同和当前验证证据为准。

接口身份、源码 binding、暴露层级、生命周期与关系导航以 [interface-registry.json](interface-registry.json) 为机器真源；[INTERFACE-INDEX.md](INTERFACE-INDEX.md) 是由 Registry 确定性生成的人类/AI 查询视图，[interface-registry.schema.json](interface-registry.schema.json) 定义结构约束。`capability_routes` 以 22 条 allowlist 路由进一步固定“实体 × 动作 → 当前默认接口 / 串行 Controller / 执行门禁 / 执行面 / 验收要求”，供人和 AI 先判定 `canonical / exploration_only / blocked`，再读取专项合同；它不是当前 deployment capability snapshot，更不能绕过 `live_verified_current_deployment` 门禁。Registry **不复制** payload、transport、错误、授权或部署证据的专项真源；这些仍以各专项合同、测试和去敏证据为准。`internal`、`compatibility` 和 `blocked` 记录被登记只是为了防止漏查，绝不等于默认可调用或稳定公开。Registry v2 的每个文件引用都必须声明 `availability`：`packaged` 表示最小 npm 包必须携带，`source_only` 表示只在源码 checkout 中提供且不得伪装为包内文件；`source_only_modules` 当前只登记依赖子库上层 scripts 的 `content-run-controller.mjs`，因此最小 npm 包只保留它的查询记录和边界，不伪装成可执行携带。所有 delete 与 article unpublish 在通用 immutable plan / 薄 Skill 中 fail closed；即使底层 export 已登记，也不得绕过能力路由直接执行。

```bash
npm run interfaces:validate
npm run interfaces:index:check
```

`interfaces:validate` 会自动区分源码与最小包引用范围：源码 checkout 中要求全部 `source_only` provenance 存在；独立 npm 包中只允许缺少明确标记为 `source_only` 的测试/证据文件，所有 `packaged` 合同和运行时模块仍须完整。`acorn`、`ajv` 与 `sharp` 都是实际运行依赖，必须保留在 `dependencies`，不能只放进 `devDependencies`；否则安装 tarball 后 Registry CLI 会在启动前失败。

Workspace 前置检查从 [workspace-preflight.mjs](workspace-preflight.mjs) 进入：默认复用内置浏览器现有同源 session，在后台请求 `/sites?_rsc` 判断登录、读取 `user.id`、拉取完整网站列表和动态发现 `createSiteAction`；正常分支不导航 `/sites`、不切前台、不点击，只有接口确认 `login_required` 时才打开并前台展示 `/sign-in`。字段与状态机见 [workspace-preflight.md](workspace-preflight.md) 和 [workspace-preflight-contract.json](workspace-preflight-contract.json)。

### 已批准计划的严格串行 Controller

跨分类、标签、媒体、产品、文章和发布的统一计划从源码 checkout 中的 `content-run-controller.mjs`（仅完整源码 checkout） 进入，运行证据按 `live-run-evidence.schema.json`（仅完整源码 checkout） 校验。它只消费通过 `validateContentOperationPlan()` 的不可变 `approved` plan，不接受调用方临时追加 operation，也不保存 Action ID、deployment ID、Cookie、Token 或授权材料。

固定语义：

```text
整份精确 plan 由用户授权一次
→ Controller 在每个 operation 前复核 plan digest、目标站点、当前 deployment、capability TTL 和授权 TTL
→ update 在请求前回读 expected-current fingerprint
→ 先确认本地运行证据已落盘
→ 请求真正发出前最后一次复核授权和 capability 是否仍有效
→ execute 一次
→ 请求状态不明时只读 reconcile，禁止盲目 retry
→ authoritative readback 满足全部 requirement 后才进入下一步
→ 任一步 BLOCK / failed / ambiguous，后续 operation 全部停止
```

这解决的是“一个计划内不要每个接口重复向用户索权”，不是永久授权：站点、operation 顺序、字段摘要、发布动作或 plan digest 改变，授权到期，capability/deployment 漂移，或新计划增加了发布/删除，都必须重新获得精确授权。Controller 的本地测试只证明本机排序、阻断和注入 readback 合同，不证明远程请求、登录、持久化、前台、SEO、询盘或转化。

只读 operation 也必须形成可验证闭环，但不得借此放宽 mutation 验收：

- **`noop`：** 不调用远程 `execute()`，`transport` 必须保持 `request_started=false/status=not_started`；仍须完成 authoritative same-site readback，证明批准对象规范化后的当前状态无需变更并精确绑定站点。
- **`explore`：** 只允许执行计划和当前 capability 已批准的一次只读请求；随后必须 authoritative same-site readback，证明发现结果与批准对象和站点精确绑定。
- 两者都使用 [verification-evidence-contract.json](verification-evidence-contract.json) 的 `read_only_profiles`，失败时不得进入 write/mutation reconciliation，也不得把只读结果外推为写能力或发布能力。

#### 权威验收证据合同

机器验收真源是 [verification-evidence-contract.json](verification-evidence-contract.json)：mutation profile 由 Registry validator 强制与 `capability_routes[].verification_requirements` 精确一致；`noop/explore` 则必须与 `read_only_profiles` 中对应 intent 的 required checks 精确一致。两类 profile 互不替代，不能用只读 PASS 削弱 mutation 的 required checks。**HTTP 200、toast、后台状态字符串或单一截图都不能单独构成 PASS。** 每个 required check 必须提供结构化 check 和同一客户任务目录内的 primary JSON artifact；Controller 会读取 `artifact_ref` 的实际字节、重算 SHA-256，并要求 JSON envelope 与 check 的站点、实体、operation subject、观察时间和观察结果精确一致。截图只能作为该 JSON artifact 内的补充引用，不能取代 primary proof。

对象级最低验收如下：

- **分类 / 标签：** authoritative backend 的非空精确 ID；精确 slug 与全部提交字段；精确同站点绑定；创建时还须排除同站点重复 slug。update 额外要求请求前 expected-current fingerprint 精确匹配。
- **媒体：** authoritative backend 的精确 media ID、持久化 HTTPS URL 和全部提交元数据；同一个 URL 必须匿名 GET 200 且实际完成图片解码，不能只相信 MIME header；persisted、anonymous-fetch 与 decode 三处 URL 必须一致。
- **文章 update：** 只作用于批准的 exact existing article ID；请求前 expected-current fingerprint 精确匹配；回读全部提交字段、生命周期状态、分类/标签/封面/正文媒体绑定，并重开精确编辑器确认健康与持久化内容一致。
- **文章 publish：** 回读 exact article ID 的 published 后台状态；重开精确编辑器；解析唯一 HTTPS public URL；匿名加载精确文章详情而不是登录页、fallback 或 generic 200 shell；核对买家可见正文，且所有适用图片必须实际解码。三项前台 check 的 URL 必须一致。

`validateAllinCmsLiveRunEvidence()` 只校验 evidence 的 schema、profile、task/site/entity/subject/time/URL 等结构与绑定，**不会读取 artifact bytes，也不会访问远程 CMS**。只有 `runAllinCmsContentPlan()` live path 通过强制注入的 `readEvidenceArtifact()` 才重算 primary artifact 字节摘要和 envelope。即使两者本地测试全部通过，也只能称 `PASS（local verification-contract and fail-closed controller scope）`，不能外推为当前已登录、远程 mutation 成功、远程 CMS truth、匿名前台真实可用、SEO、询盘/转化、Stable、Published 或 production-ready。

文章生命周期从 [article-operations.mjs](article-operations.mjs) 进入；正文 Markdown 图片绑定从 [article-image-binding.mjs](article-image-binding.mjs) 进入。不要把图片 companion 的 draft-only 合同误当成完整文章发布合同。

## 给其他 AI 的最短入口

先读 [AI 唯一入口](AI-START-HERE.md)、[图片元数据与 AI 读图 SOP](media-metadata-and-ai-vision-sop.md) 和 [机器合同](media-operations-contract.redacted.json)，再导入 [操作模块](upload-media-browser.mjs)。**AllinCMS 图片上传的唯一默认入口是 `uploadAllinCmsMediaSerial()`**；它负责任意数量图片的逐张接口上传、自动刷新、延迟只读对账、确认缺失后的有限重试、原子索引和断点恢复；开启 `syncRemoteMetadata` 后，还会在当前图片上传完成后同步并复核 `title / alt / caption`，再进入下一张。`uploadAllinCmsMediaDirect()` 只是总控内部使用的单张原语，其他 AI 不得围绕它另写 `for` 循环。元数据单张原语 `updateAllinCmsMediaMetadataDirect()` 与删除原语 `deleteAllinCmsMediaDirect()` 当前仍使用 legacy 裸布尔授权，已在 Registry 标记为 `blocked`；在迁移到结构化目标/字段摘要授权前，不得作为默认入口调用。默认上传调用当前部署的 Next Server Action，**不点击按钮、不打开文件选择器，也不导出 cookie 或 token**；历史直接删除证据只证明限定目标的既有运行，不放行当前 BLOCK 原语。

固定路线如下，后续 AI 不得自行换序：

```text
P1  checkAllinCmsMediaRuntime() → uploadAllinCmsMediaSerial()
P2  uploadAllinCmsMediaDirect() 仅作为总控内部单张原语
P3  updateAllinCmsMediaMetadataDirect() 当前 BLOCK；迁移结构化字段授权后才可恢复
P4  reconcileAllinCmsMediaDirect() 仅做只读上传对账
P5  uploadAllinCmsMediaBatch() 仅在用户明确批准后做 1–5 张 UI 回退
P6  PicGo + R2 / GitHub / COS / OSS 仅在目标是外部图床或用户明确指定时使用
```

UI 与外部图床都不是接口失败后的自动降级。API-first 登录判断、`user.id`、完整网站列表、0/1/多站点处理、未登录浏览器交接、新增网站字段、精确媒体页检查和接口失败后的页面诊断，统一执行 [AI-START-HERE.md 的第 0 节](AI-START-HERE.md#0-默认启动登录交接与回落路由)，不要在其他文件复制第二套状态机。

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
- 媒体记录删除：历史上已验证一条精确目标的零点击直接删除；但当前 direct 原语仍是 legacy 裸布尔授权，Registry 保持 `blocked`，不得把历史证据当作当前默认放行；
- 媒体元数据：历史上已验证一张虚拟图片只发一次更新请求；稍后新鲜刷新后三字段持久化且 media ID / URL 未变；但 direct 元数据原语和串行同步中的元数据批准仍是 legacy/partial 授权，字段 payload 未被完整摘要绑定；
- 一次 multipart 传 10 张、覆盖和内容绑定：未验证；上传及元数据写入都禁止并发和自动重发，不作为后续提速方向。

## 文章正文格式 companion

AllinCMS 文章正文不是直接保存 HTML 或 Markdown，而是保存 Slate JSON `node[]`。Markdown 只适合作为创作源，必须先通过当前 Adapter 的确定性转换器：

```js
import {
  ALLINCMS_ARTICLE_FORMAT_SUPPORT,
  createCanonicalAllinCmsSlateExamples,
  markdownToAllinCmsSlate,
} from './article-operations.mjs';

const slate = markdownToAllinCmsSlate(markdownSource, { idPrefix: 'article-body' });
```

当前真实接口实验结论为 **12 verified / 1 unsupported-current-shape / 0 not-tested**。已验证：H3、粗体、斜体、下划线、删除线、行内代码、链接、无序列表、有序列表、引用、分隔线和表格。代码块本次测试形状虽然能 API 保存并精确回读，但编辑器重开失败，因此必须恢复 last-known-good，**不得发布**。完整矩阵、Markdown 规则和证据边界见 [article-operations.md](article-operations.md#810-文章格式接口实验slate-是持久化格式markdown-只作创作源) ；源码 checkout 中的 `article-format-verification.redacted.md` 保存去敏验证证据，不随独立 npm adapter 包分发。

## 文章正文图片 companion

文章正文图片已经有唯一可执行 adapter，不再只是一页参考逻辑：

- 实现：[article-image-binding.mjs](article-image-binding.mjs)；
- 机器合同：[article-image-binding-contract.json](article-image-binding-contract.json)；
- 本地测试：源码 checkout 中的 `article-image-binding.test.mjs`（不随独立 npm adapter 包分发）；
- 对抗复核证据：源码 checkout 中的 `article-image-binding-adversarial-review.redacted.md`（不随独立 npm adapter 包分发）；
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

2026-07-27 的真实远程证据覆盖单张直传、10 张单图严格串行、一次 5 张中的受控刷新对账、一张获批虚拟媒体的 `title / alt / caption` 最终持久化，以及 A/B/A 正文原位绑定草稿。2026-07-30 的历史本地回归快照曾为媒体上传 45/45、正文图片 52/52、文章、正文格式与 taxonomy 48/48，adapter 全量 145/145；2026-08-01 的历史 trusted-profile 快照为 156/156，随后补齐 2 项格式负向回归，当前正式冻结的文章/媒体四文件 qualification profile 为媒体 45/45、正文图片 52/52、正文格式 13/13、文章生命周期与 taxonomy 48/48，合计 158/158；完整源码工作树另含 Workspace 前置检查 21/21、严格串行 Controller 58/58 与接口 Registry 11/11，`npm test` 七文件当前全量为 248/248；两种口径不得互相替代；负向用例覆盖四入口缺失授权、site/operation/entrypoint/actor/digest 篡改、同路径换字节、symlink retarget、批次中途替换、chooser payload 篡改、29:59.999 / 30:00.000 / 30:00.001 边界、future timestamp，以及 callback 延迟跨过 expiry，且均未访问真实 CMS。正文绑定前另会复核本地图片字节未变化、远端映射源 SHA-256 与资产一致、候选携带已知 media ID/URL，并对后台 Caption 结构再次验形；标题相同不构成资产归属证据。**本地 PASS 只证明隔离控制器合同；新快照/时效逻辑、恢复层、自定义标题和跨部署元数据稳定性仍待下一次自然、获批的真实操作顺带复验**，不得为测试重复写入。

### 单张原语：仅供 adapter 维护者

`uploadAllinCmsMediaDirect()` 是 `uploadAllinCmsMediaSerial()` 的内部上传原语，不是其他 AI 的默认入口。只有维护 adapter、做合同漂移诊断或编写隔离测试时才直接调用；业务调用不得复制手写循环绕过私有索引、锁和恢复状态机。 即使由上层串行总控调用，direct 原语也必须收到与当前单文件绑定的授权上下文并自行验证；可选 `beforeRequest` 只负责 journaling，不能放宽或替代授权。

### 历史已验证、当前 AI 执行 BLOCK：零点击删除一条媒体记录

删除属于独立高风险动作。2026-07-27 的历史证据证明当时部署中可以用 `siteKey + mediaId + title + URL` 精确删除一条媒体记录；但当前 `deleteAllinCmsMediaDirect()` 实现和机器合同仍接受旧的裸布尔 `authorizationConfirmed`，没有绑定 operation、目标摘要、具名 actor 和授权有效期。因此本入口当前不提供可复制调用示例，AI 不得执行；必须先迁移到结构化 `authorizationContext` 并补齐负向测试。

迁移后仍只有 `serverAction200`、`mediaCardRemoved`、`mediaRecordRemoved` 和 `contractVerified` 全部为 `true`，才能报告“媒体记录已删除”。历史真实验证中，删除后的公开图片 URL 仍返回 `200 image/webp`，因此不得报告“图片对象已清理”或“URL 已失效”。完整历史证据保存在源码 checkout 的 `direct-delete-verification.redacted.md`，不随独立 npm adapter 包分发。

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
- 历史一次虚拟样本只发送 1 次字段写请求，稍后刷新后三字段均持久化；但 2026-07-30 的自然真实批次中 title/alt 已持久化而 caption 刷新后仍为 `null`。因此元数据字段必须逐次回读，不能把历史单样本外推为跨部署稳定；
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
article_binding_tests: 52_passed
article_content_formats_tests: 13_passed
article_operations_tests: 48_passed
article_adapter_local_tests: 182_passed_current_2026_08_11
article_editor_render_gate: verified_remote_2026_07_27
article_editor_dom_alt: missing_observed_3_of_3_2026_07_27
published_theme_alt_current_run: partial_empty_observed_warn_2026_07_30
article_update_publish_remote_current_deployment: verified_scoped_11_serial_2026_07_27_and_2_full_create_publish_idempotent_2026_07_30
article_post_create_api: verified_scoped_current_deployment_2_serial_2026_07_30
article_remote_failure_injection_recovery: blocked_not_verified
media_record_delete_direct: verified
media_editor_fields_title_alt_caption: observed
direct_metadata_update_contract: captured_and_one_authorized_remote_write_verified
ai_metadata_to_private_index: implemented_local_tested
ai_title_alt_caption_to_allincms: historical_one_sample_verified__current_batch_caption_null_warn
physical_asset_cleanup_after_delete: out_of_scope
publication_status: WARN_CURRENT_DEPLOYMENT_CREATE_PUBLISH_COMPLETE__MEDIA_CAPTION_AND_THEME_PRESENTATION_GAPS__BLOCK_CROSS_DEPLOYMENT
```

## 本目录

| 文件 | 用途 |
|---|---|
| `AI-START-HERE.md` | 其他 AI 必须先读的唯一执行入口 |
| `media-operations-contract.redacted.json` | AI 可机读的上传 / 删除 / 元数据函数、前置条件和停止规则 |
| `media-metadata-and-ai-vision-sop.md` | AI 读图、title / alt / caption 职责、事实闸和不重传规则 |
| `observed-contract.redacted.json` | 去敏后的接口形状、验证和漂移合同 |
| `direct-serial-10-verification.redacted.md`（仅源码 checkout） | 10 张单图接口串行调用的去敏证据与边界 |
| `direct-serial-11-article-verification.redacted.md` | 11 篇文章完整字段 `update → publish` 串行验证的去敏证据与边界 |
| `image-index-e2e-verification.redacted.md`（仅源码 checkout） | 私有图片索引、断点恢复与去重闭环的去敏证据及适用边界 |
| `direct-delete-verification.redacted.md` | 零点击媒体记录删除的历史去敏证据；当前完成口径只看卡片与 RSC 记录 |
| `upload-media-browser.mjs` | 运行预检 + 任意数量永久串行总控 + 报错延迟对账与有限重试 + 单图接口原语 + AI title/alt/caption 同步 + 原子私有索引 + 零点击媒体记录删除 + 1–5 图 UI 回退 |
| `upload-media-browser.test.mjs` | 45 项媒体本地故障与授权边界测试；不等同于所有部署的真实远程生产验证 |
| `article-image-binding-contract.json` | 正文图片的资产、occurrence、Slate、保存、渲染和 Alt 分层合同 |
| `article-image-binding.mjs` | Markdown 原位解析、映射复核、Slate 构建、草稿保存与编辑器健康闸 |
| `article-image-binding.test.mjs` | 52 项文章图片本地测试；包含 A/B/A、锚点防漂移、Caption 全数组预检、非空封面 canonical 字段请求前完整性与持久化回读，以及编辑器、图片解码、Caption 和草稿状态健康闸 |
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

文章、分类、标签和正文图片草稿写入统一要求结构化 `authorizationContext`；裸布尔值不会授权任何请求。`mutation-authorization.mjs` 将授权精确绑定到当前 `site_key`、operation、目标 SHA-256 摘要、具名 `human-asserted` actor、批准时间和最长 30 分钟有效期，并在每次远程请求前重验。actor 身份状态固定为 `not_verified`，不能据此宣称真人批准。当前摘要主要证明 operation + 对象/slug/文件列表级 target binding：文章 update/publish/unpublish、taxonomy 与正文图片并未把完整 mutation payload 全部绑定进授权摘要；媒体元数据字段和 direct 删除仍是 legacy 裸布尔授权。publish/delete 仍需独立明确人工批准；本地完整 Adapter 的 248 项源码工作树测试和 npm 包检查不证明真实 CMS、跨部署稳定或正式发布资格。
