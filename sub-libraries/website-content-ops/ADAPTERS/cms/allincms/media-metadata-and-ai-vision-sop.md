---
title: "AllinCMS Media Metadata and AI Vision SOP"
description: "AI 逐张读图、生成图片语义、串行上传、写入私有索引，并在不重复上传的前提下同步 AllinCMS title、alt、caption 的操作规范。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-11"
sources: ["Live AllinCMS upload and media edit dialogs inspected 2026-07-27", "One authorized direct metadata write and later fresh-page verification 2026-07-27", "Current AllinCMS client bundle inspected 2026-07-27", "media-operations-contract.redacted.json", "Tony decision 2026-07-27"]
related: ["AI-START-HERE.md", "README.md", "INTERFACE-INDEX.md", "interface-registry.json", "upload-media-browser.mjs", "upload-media-browser.test.mjs", "../../image-upload-routing.md", "../../../TEMPLATES/image-manifest.md"]
confidence: "high-for-observed-fields-and-one-authorized-metadata-write-medium-for-cross-deployment-stability"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 图片元数据与 AI 读图 SOP

## 给执行 AI 的一句话结论

**先由 AI 读图生成候选，再逐张串行执行“上传 → 刷新验收 → 写索引 → 元数据更新 → 只读刷新复核”；当前图片没有完整结束前，永久禁止开始下一张。**

不要并发，不要用 `Promise.all`，不要开多个标签，不要因为元数据结果不明确而重新上传图片或自动重发元数据请求。

## 真实页面结论

2026-07-27 已在登录后的真实 AllinCMS 媒体页检查并刷新复核：

1. **上传弹窗不能填写图片信息**，只有文件选择；当前提示支持 PNG、JPG、GIF、WebP，单文件最大 5 MB。
2. 图片形成媒体记录后，编辑弹窗提供三个字段：
   - `title`：标题，当前客户端校验上限 100 字符；
   - `alt`：替代文本，当前客户端校验上限 200 字符；
   - `caption`：说明，当前客户端校验上限 500 字符。
3. AllinCMS 媒体记录**没有独立 `description` 字段**。完整描述进入客户私有 `image-index.json`；只有适合公开展示的短说明才改写为 `caption`。
4. 当前客户端存在 `updateMediaAction`，提交对象为 `id + siteId + title + alt + caption`。完整 Server Action ID、site ID、media ID、真实 URL 和凭据不得写入公开母库。
5. 一次获授权的虚拟图片真实接口测试中，只发送了**一次**元数据写请求；第一次紧接写入后的读取看到 `alt` 已更新而 `caption` 暂未出现，稍后重新打开媒体页并再次刷新后，`title`、`alt`、`caption` 均持久化且 media ID / URL 未变。
6. 上述现象说明当前部署可能存在**读后写延迟**。正确修复是做有限次数的只读刷新复核，不是重发写请求。

## AI 能自动做什么

AI 可以自动完成以下本地工作：

- 识别主体、角度、颜色、结构和可见部件；
- OCR 可见文字，并标记不清晰内容；
- 结合已确认的公司、产品和页面知识生成候选；
- 生成英文稳定文件名、`title`、`alt`、`caption`；
- 生成更完整的私有 `description` 和结构化 `metadata`；
- 检查长度、关键词堆砌、臆测、隐私、商标和版权风险；
- 将候选写入私有图片索引；
- 在用户已明确授权本批元数据写入时，通过接口逐张同步 AllinCMS 字段。

AI **不能仅凭图片自行断言**型号、功率、扭矩、电压、材料、认证、兼容性、性能和客户承诺。此类事实只能来自已确认且可追溯的产品知识。

## 字段模型

```yaml
source_sha256: "..."
source_md5: "..."
filename: "rear-hub-motor-side-view-a1b2c3.webp"
title: "rear-hub-motor-side-view-a1b2c3"
alt: "Rear e-bike hub motor showing the axle and cable lead"
caption: "Rear hub motor side view for an electric bicycle application."
description: >-
  Synthetic product-side image showing a circular rear hub motor shell,
  axle and cable lead on a plain background.
metadata:
  asset_type: product_side_view
  product_ref: FP-HM750
  visible_features:
    - motor shell
    - axle
    - cable lead
  visible_text: []
  intended_use:
    - product_detail
    - product_comparison
  page_context: product_detail
  seo_topic: rear e-bike hub motor
  language: en
  confidence: 0.92
  human_review_required: false
  fact_basis:
    - image_observation
    - product_knowledge_base
  uncertain_claims: []
notes: "Virtual demo asset; verify model before public use."
```

| 字段 | 保存位置 | 规则 |
|---|---|---|
| `filename` | 本地文件 + 索引 | 小写英文、连字符、短哈希；稳定且可去重 |
| `title` | AllinCMS + 索引 | 后台管理名；不堆关键词；≤100 |
| `alt` | AllinCMS + 索引 | 与页面任务相关的可见内容；≤200；装饰图可为空 |
| `caption` | AllinCMS + 索引 | 可能公开展示的简短说明；≤500；无展示价值可为空 |
| `description` | 仅私有索引 | 完整资产说明，可比 caption 更详细 |
| `metadata` | 仅私有索引 | 产品、用途、可见事实、语言、置信度、依据和不确定项 |

## 自动填写闸

只有同时满足以下条件，AI 候选才允许自动进入远程字段同步：

1. 图片属于用户确认的公司、产品或页面任务；
2. `uncertain_claims` 为空；
3. 不含仅凭图片无法证明的产品事实；
4. `title / alt / caption` 通过长度、语言、禁词和重复检查；
5. 当前页精确为 `https://workspace.laicms.com/{site_key}/media`，且登录有效；
6. 目标精确匹配 `siteKey + mediaId + URL + currentTitle`；
7. 当前部署动态发现到唯一 `updateMediaAction` 合同；
8. 用户已明确授权本批图片上传和元数据写入。

以下情况必须人工确认：

- 铭牌、型号或 OCR 不清楚；
- 文案涉及功率、扭矩、电压、认证、材料、兼容性或性能；
- 图片含第三方商标、客户信息、人物、地址或版权风险；
- 页面用途不明确；
- AI 读图与文件名、产品知识冲突；
- 生成结果需要营销主张而非纯视觉说明。

## 默认串行调用

如果只需要上传和索引，不写远程元数据：

```js
const authorizationContext = await adapter.createAllinCmsMediaUploadAuthorizationContext({
  localFiles,
  expectedSiteKey,
  entrypoint: "serial",
  approvalActor: "当前明确批准这批精确文件的人类用户",
});

await adapter.uploadAllinCmsMediaSerial({
  tab,
  expectedSiteKey,
  imageIndexPath,
  localFiles,
  authorizationContext,
});
```

如果每张图片都要把 AI 候选写入 AllinCMS：

```js
const localFiles = [
  {
    localFile: "/absolute/private-runtime/images/01.webp",
    title: "rear-hub-motor-side-view",
    description: "私有完整图片说明",
    alt: "Rear e-bike hub motor showing the axle and cable lead",
    caption: "Rear hub motor side view for an electric bicycle application.",
    metadata: {
      asset_type: "product_side_view",
      visible_features: ["motor shell", "axle", "cable lead"],
      confidence: 0.92,
      human_review_required: false,
      fact_basis: ["image_observation", "product_knowledge_base"],
      uncertain_claims: [],
    },
  }];

const authorizationContext = await adapter.createAllinCmsMediaUploadAuthorizationContext({
  localFiles,
  expectedSiteKey,
  entrypoint: "serial",
  approvalActor: "当前明确批准这批精确文件的人类用户",
});

await adapter.uploadAllinCmsMediaSerial({
  tab,
  expectedSiteKey,
  imageIndexPath,
  localFiles,
  authorizationContext,
  syncRemoteMetadata: true,
  metadataAuthorizationConfirmed: true,
});
```

`metadataAuthorizationConfirmed: true` 是 legacy/partial 批次批准，只表示当前用户口头/上下文同意本次元数据写入；它**没有**把最终 `title / alt / caption` payload、具名 actor 和 TTL 完整绑定进摘要。`updateAllinCmsMediaMetadataDirect()` 因此在接口 Registry 中保持 `blocked`；上例只记录现有串行兼容路径，不得外推成结构化字段授权已经完成。

如果 `title` 与上传时由文件名生成的当前标题不同，adapter 会在写请求前确认目标标题尚未被其他媒体卡使用；发现撞名时停止当前批次，且不会发出元数据写请求。

## 单张固定顺序

```text
AI 读图和 OCR
→ 生成并校验 description / title / alt / caption / metadata
→ 写 prepared
→ 写 request_started
→ 发出当前尝试的 1 次上传请求
→ 若报错：等待 → 只读刷新对账；已存在则补齐，明确不存在且未耗尽才重试当前图片
→ 刷新并验证媒体卡、RSC 记录、media ID、URL 和图片解码
→ 原子写入已验证上传映射
→ 发出 1 次元数据更新请求
→ 按 0ms / 750ms / 2000ms 延迟做最多 3 次只读刷新复核
→ title / alt / caption 全部一致且 media ID / URL 不变
→ 写 metadata_verified
→ 才开始下一张
```

这三个延迟是当前 adapter 的默认有限复核窗口，不是平台 SLA。若窗口内仍未完全一致，状态必须保持不明确并停止本批；不得自动发第二次元数据请求。

## 状态机

```text
prepared
→ request_started
→ verified | reconciled_existing
→ metadata_candidate_ready
→ metadata_request_started
→ metadata_verified
```

异常分支：

- `prepared_title_collision`：请求尚未发出但远端已有同标题；停止，不能认领。
- `upload_error_pending_reconciliation`：上传报错后先等待并只读对账。
- `upload_retry_scheduled`：已精确确认远端不存在，且当前图片仍有剩余尝试次数。
- `upload_result_ambiguous`：对账仍不明确；停止本批，不能盲目重传。
- `stopped_retry_exhausted`：已多次确认远端不存在，但当前图片达到最大尝试次数。
- `metadata_update_failed_before_request`：上传已成功，字段请求未发出；保留媒体记录并停止本批。
- `metadata_update_ambiguous`：字段请求可能已成功但有限复核未完全一致；保留媒体记录，只读复核，不能重发字段请求。
- `stopped_metadata_ambiguous`：当前图片已上传，但元数据未闭环；下一张不得开始。

**上传重试和元数据写入是两套独立合同。** 上传只允许“报错后延迟 + 精确只读对账 + 确认不存在后有限重试”；元数据请求可能已成功时仍禁止自动重发。

**上传成功和元数据成功是两个独立事实。** 元数据失败不能把上传改写成失败，更不能通过删除或重传图片“修复”。

## 成功口径

### 上传成功

必须同时满足：

- 当前图片只有一个上传接口请求；
- 刷新后唯一媒体卡存在；
- RSC 中存在唯一 media ID、title 和 URL；
- URL 可匿名 HTTPS 访问且内容可解码；
- 私有索引已原子写入 verified / reconciled 映射。

### 元数据成功

必须逐图片、逐运行满足；历史样本不能替代当前回读。必须同时满足：

- 当前图片只有一个元数据更新请求；
- 响应成功；
- 有限次数的只读刷新后，RSC 或刷新后的编辑表单中 `title / alt / caption` 与候选完全一致；
- media ID 和 URL 未变化；
- 私有索引写入 `metadata_sync_status: metadata_verified`、时间和字段快照。

### 删除成功

只要求：

- 精确媒体卡消失；
- 精确 RSC 媒体记录消失。

不检查、不讨论、不阻断于 OSS、对象存储或 CDN 是否物理删除。

## 去重与复用

- 私有索引以源 SHA-256 为主键，MD5 仅用于人工排查和跨工具兼容；
- 同一源 SHA-256 已有 verified 映射时，即使改名也默认复用 media ID / URL；
- 同一图片用于不同页面时，可以生成页面级 alt/caption 方案，但不重复上传；
- 只更新私有 description/metadata 时，不触发远程上传；
- 修改远程字段必须精确锁定现有 media ID / URL，不能靠标题模糊匹配；
- title 改名后要保留历史名称，避免后续误判缺图。

## 已验证边界

### 已验证

- 上传弹窗无元数据字段；
- 编辑弹窗存在 title、alt、caption；
- 当前客户端校验上限为 100 / 200 / 500；
- `updateMediaAction` 的 payload 字段形状已观察；
- 一次虚拟图片直接元数据写入只发一个请求；
- 历史单样本在稍后新鲜页面刷新后 title、alt、caption 全部持久化，media ID / URL 未变；
- 2026-07-30 的自然真实批次中，3 张图片的 title/alt 已持久化，但 caption 刷新后仍为 `null`；该结果是部署/运行差异 WARN，不能用历史单样本覆盖；
- adapter 已加入有限只读复核，不会因短暂读延迟自动重发写请求；
- 串行上传、索引、元数据停止规则已通过本地故障测试。

### 仍需谨慎

- Server Action、deployment、router tree 和字段校验可能随部署漂移，必须每次动态发现；
- 一张虚拟图片的真实验证不等于所有账号、站点和未来部署永远一致；
- 产品、文章和主题是否自动继承媒体库 alt/caption，需要按内容类型分别验证；
- AI 读图模型可替换，但事实闸、私有索引和禁止重传规则不可省略。

## 文章正文中的图片描述：资产层与 occurrence 层

媒体库字段与文章正文字段不是同一个对象：

| 层 | 适合保存什么 | 是否随文章位置变化 |
|---|---|---|
| 私有资产索引 | 完整 `description`、版权、可见特征、OCR、产品引用、不确定项 | 通常不变 |
| AllinCMS 媒体记录 | 后台管理 `title`，以及可作为默认候选的 `alt / caption` | 不应频繁改写 |
| 文章 occurrence | 当前段落语境下的 `role / article_context / alt / caption / anchors` | 每个位置独立 |

同一资产在两篇文章或同一文章的两个位置，搜索意图与上下文可能不同，因此 occurrence Alt / Caption 不能强制继承媒体库默认值，也不能通过修改媒体库字段覆盖所有文章。

AI 生成正文图片说明时按以下顺序：

1. 读取图片本身和私有资产说明；
2. 读取产品知识库中的已确认事实；
3. 读取图片前后段落、文章搜索意图和该图角色；
4. 只描述对当前页面任务有帮助的可见事实；
5. 参数、认证、性能、材料和兼容性继续受事实闸约束；
6. 将完整判断写入私有 occurrence 记录；
7. 将简洁 Alt 写入正文图片后台字段；
8. 将需要被读者看到的说明写成 Caption；无展示价值时 Caption 可为空。

正文图片节点的 Caption 不是字符串，必须转换为 Plate/Slate 文本节点数组：

```json
"caption": [{"text": "虚拟演示图：轮毂电机结构细节"}]
```

字符串 Caption 会在请求前被 [article-image-binding.mjs](article-image-binding.mjs) 阻断，因为 2026-07-27 的虚拟草稿实测表明：后端可以持久化字符串，但文章编辑器可能在重载时 500。

正文 Alt 的完成状态必须分层记录：

```yaml
backend_alt_field: persisted | missing | not_checked
editor_dom_img_alt: present | missing | not_checked
published_theme_alt: present | empty | missing | not_run_not_authorized
```

当前 A/B/A 虚拟草稿只确认 `backend_alt_field: persisted`；编辑器 DOM 观察为 `missing`；本轮未发布，因此公开主题状态必须保持 `not_run_not_authorized`。不得把后台字段持久化写成“SEO Alt 已在公开页面生效”。
