---
title: "Adapter: AllinCMS Observed Interfaces"
description: "定义 AllinCMS 当前账号网站发现、媒体上传、文章与分类操作、媒体记录删除的抓取、去敏、回放、验证、漂移和回退合同。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-11"
sources: ["../../SOURCES.md", "Tony requirement 2026-07-27", "Observed signed-in single upload 2026-07-27", "allincms/observed-contract.redacted.json"]
related: ["README.md", "allincms/README.md", "allincms/AI-START-HERE.md", "allincms/INTERFACE-INDEX.md", "allincms/interface-registry.json", "allincms/article-operations.md", "../README.md", "../_template.md", "../../TEMPLATES/tool-field-map.md", "../../TEMPLATES/failure-diagnosis.md", "../../QA-CHECKLIST.md"]
confidence: "high"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
---
# Adapter: AllinCMS Observed Interfaces

## TL;DR

方向正确，但不要把抓到的请求称为“AllinCMS 官方 API”。当前正确命名是：

```text
observed_internal_contract
```

实施原则：

```text
首次捕获：登录后的真实 UI 触发 + Network/CDP 抓完整协议
默认执行：先预检，再由 `uploadAllinCmsMediaSerial()` 串行总控；单张直传原语只在总控内部调用
接口漂移或验证失败：先查媒体库是否已落记录；不自动重试，必要时回到一张新虚拟图重新捕获
```

对小白只显示“选择网站”和“上传图片并取得链接”。站点列表、Server Action、预签名上传、对象存储和媒体登记全部封装在 adapter 内。文章、分类、标签和发布也必须以稳定业务对象呈现，不能把内部 action 当成公开 API。

文章与分类的字段、依赖顺序和当前验证边界见 [AllinCMS 文章与分类操作逻辑](allincms/article-operations.md)。接口身份与可调用层级统一从 [人类/AI 接口索引](allincms/INTERFACE-INDEX.md) 查询，机器真源是 [interface-registry.json](allincms/interface-registry.json)；不要从本页的历史说明推断当前接口已放行。

### AllinCMS 图片路线固定优先级

```text
P1  checkAllinCmsMediaRuntime() → uploadAllinCmsMediaSerial()
P2  uploadAllinCmsMediaDirect() 仅作为总控内部单张原语
P3  reconcileAllinCmsMediaDirect() 仅做只读对账
P4  uploadAllinCmsMediaBatch() 仅在用户明确批准后做 1–5 张 UI 回退
P5  PicGo + R2 / GitHub / COS / OSS 仅在目标是外部图床或用户明确指定时使用
```

P4、P5 都不是 P1 失败后的自动降级。目标是 AllinCMS 媒体库时，不应先配置 PicGo，也不应重新抓接口或模拟点击；完整选择规则见 [图片上传路由](../image-upload-routing.md)。

## 1. 三个业务能力抽象，不绑定具体 endpoint

```text
list_sites(current_session) -> SiteSummary[]
upload_media(current_session, site_key, local_file) -> MediaAsset
delete_media_record(current_session, exact_media_identity, explicit_authorization) -> DeleteResult
```

这三个名称是课程和上层 AI 理解业务目标的抽象，不是源码 export，也不自动等于当前可执行接口。实际入口、暴露层级和 BLOCK 以 Registry 为准：当前站点发现与串行上传有 canonical controller；媒体 direct 删除仍因 legacy 裸布尔授权保持 `blocked`。底层可能是 JSON API、Next.js Server Action、RSC、SSR、DOM 读取或多阶段对象存储上传，但不把当前实现泄漏给用户流程。

## 2. 接口选择优先级

| 级别 | 实际来源 | 默认判断 | 使用条件 |
|---|---|---|---|
| A | 官方公开 API | 最稳定 | 有官方文档、认证和兼容承诺 |
| B | 普通 JSON API | 较适合回放 | 登录态下抓到，结构稳定，能独立验证 |
| C | Server Action | 可用但易漂移 | 动作 ID 和构建指纹可重新捕获，不长期硬编码 |
| D | RSC / SSR 数据 | 只读可用，解析较脆 | 没有更稳定接口，且有 DOM 对照 |
| E | DOM 读取 | 站点发现的安全回退 | 只读、不模拟点击、字段足够 |
| F | UI 点击 / 文件选择器 | 只用于首次抓取或回退 | 需登录和动作时授权 |

**对抗结论（2026-08-11 更新）**：网站列表不需要硬编码 Server Action。当前 canonical 路径是在宿主浏览器 session 中只读请求 `/sites?_rsc`，同时得到登录状态、`user.id`、分页站点列表和 `canCreate`；DOM 只作为登录交接与合同漂移诊断。新增网站和图片上传仍是动态 Server Action，action ID 必须从当前部署重新发现。

## 3. Site Discovery Contract

### 目标

获取**当前登录身份在当前 workspace/account 下可见的网站集合**，供用户选择目标站点。不得默认取数组第一项，不得把缓存中的“上次站点”冒充当前账号完整列表。

### 去敏合同模板

```yaml
contract: allincms-account-site-list
contract_kind: observed_internal_contract
capture_status: capture_required
captured_at: null
workspace_origin: https://workspace.laicms.com
build_fingerprint:
  observed_build_id: null
  route_signature_sha256: null
request:
  url_pattern: null
  method: null
  request_type: json_api | server_action | rsc | ssr | ssr_with_embedded_rsc | dom_fallback
  required_header_names: []
  auth_mode: current_browser_session
  body_shape: null
response:
  status: null
  content_type: null
  list_path: null
site_fields:
  site_id: null
  site_key: null
  display_name: null
  status: null
  role: null
  frontend_domains: []
  created_at: null
  updated_at: null
pagination:
  type: none | page | cursor | unknown
  cursor_field: null
verification:
  auth_failure_not_empty_list: true
  compare_with_sites_page: true
  unique_site_key: true
  pagination_exhausted: true
  selected_site_reconfirmed_before_write: true
```

### 2026-07-27 已验证的只读合同

本次在已登录浏览器中硬刷新 `https://workspace.laicms.com/sites`，通过 CDP 对 document、fetch 和 RSC 请求做了只读观察。公开版只记录协议结构，不记录账号邮箱、站点名称、站点 ID、站点数量或原始响应。

```yaml
contract: allincms-account-site-list
contract_kind: observed_internal_contract
capture_status: captured_read_only
captured_at: 2026-07-27
workspace_origin: https://workspace.laicms.com
build_fingerprint:
  deployment_fingerprint: 83eddf696484d494d59ae961cb4ded1d61d14b56
  route_signature_sha256: 5df81ae6916e7e1e0b14fbc634328a07f920404a6d4a7775d3bf0674d972fbf8
request:
  url_pattern: /sites
  method: GET
  request_type: ssr_with_embedded_rsc
  required_header_names: []
  auth_mode: current_browser_session
  body_shape: null
response:
  status: 200
  content_type: text/html
  list_path: SitesClient.props.data
site_fields:
  site_id: id
  site_key: slug
  display_name: name
  description: description
  status: active
  role: not_observed
  frontend_domains: domains + displayDomain
  theme_count: themeCount
  created_at: createdAt
  updated_at: not_observed
pagination:
  type: unknown
  cursor_field: null
verification:
  login_redirect_checked: true
  document_contains_rendered_cards: true
  embedded_rsc_payload_checked: true
  separate_site_list_json_request_observed: false
  separate_site_list_server_action_observed: false
  compare_with_sites_page: true
  unique_site_key: true
  pagination_exhausted: not_proven
  selected_site_reconfirmed_before_write: required
```

**证据解释**：站点卡片与结构化列表都随 `/sites` 的 `200 text/html` document 返回；响应内含 Next.js App Router 的 `self.__next_f` Flight 数据，`SitesClient` 接收 `data` 数组。硬刷新时没有观察到单独承载站点列表的 JSON API 或 Server Action。页面还会预取其他导航路由的 `text/x-component`，这些预取不能误认成站点列表接口。

因此当前最稳的实现不是猜测 `/api/sites`，而是：

```text
当前浏览器 session GET /sites?_rsc
→ 401/403、最终 /sign-in 或登录内容：打开并前台展示 /sign-in
→ 已登录：读取 RSC user.id、sites、pagination、canCreate
→ 拉完全部分页并验证 unique sites == totalDocs
→ RSC 合同漂移时打开 /sites 做页面诊断，不把 DOM 冒充完整机器真源
→ 写动作前让用户确认目标站点指纹
```

当前字段映射已经可用于实现 `list_sites(current_session)`；但它仍是内部观察合同，不是官方公开 API。构建指纹、字段结构或响应类型变化时必须重新捕获。

### 捕获顺序

1. 取得宿主内置 Browser 的当前会话；
2. 在该 session 中请求 `GET /sites?_rsc={nonce}`，不导出 cookie；
3. 先判定 401/403、最终 `/sign-in` 和登录内容，再解析 RSC；
4. 读取 `user.id` 和站点 payload，按 `pagination.totalPages` 拉完全部页；
5. 规范化为 `SiteSummary[]`，按站点 ID 去重并验证数量等于 `totalDocs`；
6. 只有合同漂移或页面健康诊断时才打开 `/sites` 与可见卡片交叉核对；
7. 写动作前重新执行新鲜 API 检查并确认目标站点；
8. 保存去敏合同，不保存 token、cookie、真实用户 ID、完整 header 值或原始私有响应。

### 选择规则

- 0 个站点：先区分“真正为空”与 401、403、登录重定向、workspace 错误或解析失败；
- 1 个站点：AI 可以推荐，但执行上传或改内容前仍显示站点名称、key 和域名让用户确认；
- 多个站点：必须列出并让用户选择，不默认第一项；
- 站点选择写入客户私有运行记录，至少保存 `site_key + display_name + frontend_domain` 指纹；
- 每次写动作前重新确认所选站点仍在当前账号列表中；
- 修改 `site_key` 的越权探测不属于正常验证，禁止枚举其他账号站点。

## 4. Media Upload Contract

### 目标

上传一张本地图片，返回可被产品、文章或页面稳定引用的媒体资产。**公开 URL 只是输出之一**；如果 CMS 保存内容依赖 `media_id`、对象 key 或媒体记录，也必须保留。

### 去敏合同模板

```yaml
contract: allincms-media-upload
contract_kind: observed_internal_contract
capture_status: capture_required
site_key: null
captured_at: null
build_fingerprint:
  observed_build_id: null
  upload_flow_signature_sha256: null
input:
  local_fixture: fluxpedal-demo-image
  sha256: null
  filename: null
  mime_type: null
  bytes: null
  width: null
  height: null
  accepted_mime_types: []
  max_bytes: null
  filename_policy: deterministic-slug-plus-short-hash
  duplicate_policy: reuse-by-hash-if-verified
upload_flow:
  type: direct_multipart | presigned_upload | server_action | multi_step | unknown
  steps:
    - order: 1
      purpose: request_upload_authorization | upload_binary | register_media | fetch_media_record
      request_url_pattern: null
      method: null
      content_type: null
      required_header_names: []
      body_field_names: []
      response_field_names: []
output:
  media_id: null
  object_key: null
  canonical_url: null
  public_url: null
  width: null
  height: null
  bytes: null
  mime_type: null
  checksum: null
verification:
  response_success: true
  backend_media_row: true
  anonymous_https_get: true
  content_type_matches: true
  decoded_image_matches_dimensions: true
  hash_or_bytes_match_when_possible: true
  bind_to_draft_content: true
  backend_reload_persists: true
  frontend_render_after_save: true
rollback:
  media_record_delete_supported: true
  delete_contract_captured: true
  physical_asset_cleanup_scope: out_of_scope_for_media_record_completion
  orphan_object_cleanup_scope: out_of_scope_for_media_record_completion
```

### 必须抓完整链路

不能只抓“文件 PUT 成功”。真实流程可能是：

```text
AllinCMS 请求上传凭证
→ 浏览器把二进制上传到 R2 / S3 / CDN / 其他存储
→ AllinCMS 登记媒体记录
→ 媒体库返回 media_id 与可用 URL
```

如果漏掉登记步骤，就可能产生“对象已上传但媒体库没有记录”的孤儿文件；如果只保存预签名 URL，它过期后也不能作为公开图片链接。

### 2026-07-27 单图直传、十图串行直传与五图 UI 回退验证结果

本轮先通过真实 UI 捕获合同并验证一次五图小批量，随后用新的 FluxPedal WebP 在当前登录页面的原生上下文直接回放上传 Server Action，并完成 10 张“单图接口串行调用”验证。纯接口测试没有点击按钮、没有打开文件选择器，也没有导出 cookie、Clerk token 或 Authorization。公开知识库只保留路由模式、字段名、动作长度 / 散列、构建指纹和验证结论。

```yaml
contract: allincms-media-upload
contract_kind: observed_internal_contract
capture_status: captured_direct_single_and_semantic_five_file_fallback
captured_at: 2026-07-27
request:
  route_pattern: /{site_key}/media
  method: POST
  request_type: next_server_action_multipart
  content_type: multipart/form-data
  independent_presigned_put_observed: false
  body_parts:
    - name: _1_files
      kind: binary_file
    - name: "0"
      kind: server_action_arguments
      shape: ["<site_id>", "$K1"]
  required_dynamic_headers:
    - next-action
    - next-router-state-tree
    - x-deployment-id
direct_single:
  ui_clicks: 0
  file_chooser_events: 0
  target_server_action_requests: 1
  media_records_created: 1
  response_status: 200
  response_type: text/x-component
  backend_reload_persists: true
  media_id_present: true
  anonymous_https_get: true
  content_type_matches: true
  image_decodes: true
direct_serial_ten:
  strategy: ten_serial_single_file_server_actions
  ui_clicks: 0
  file_chooser_events: 0
  target_server_action_requests_verified: 10/10
  media_records_created: 10/10
  backend_reload_persists: 10/10
  anonymous_https_get: 10/10
  image_decodes: 10/10
  one_multipart_request_with_ten_files: not_verified
  parallel_requests: not_verified
semantic_five_file_fallback:
  file_chooser_events: 1
  target_server_action_requests: 1
  media_records_created: 5
  media_ids_present: 5/5
  anonymous_https_get: 5/5
status:
  direct_server_action_replay_single: verified
  direct_single_requests_serial_batch_10: verified
  direct_server_action_replay_batch: not_verified_one_request_batch
  parallel_direct_batch: not_verified
  semantic_browser_batch_upload_5: verified
  content_binding: verified_remote_draft_A_B_A_2026_07_27
  article_binding_entry: cms/allincms/article-image-binding.mjs
  article_editor_health_gate: editor_present_exact_image_count_decode_caption_and_draft_status
  article_editor_dom_alt: missing_observed_3_of_3
  published_theme_alt_current_run: not_run_not_authorized
  media_record_delete_direct: verified
  physical_asset_cleanup_after_delete: out_of_scope
```

关键结论：

- 单图不需要再模拟点击。adapter 可在 Node 内存中把 PNG / JPG / WebP 规范化为 WebP，再把字节传入当前页面主世界，用页面登录态同源 `fetch`；
- `uploadMedia` action、内部 `site_id`、router tree 和 deployment 每次动态发现，不长期硬编码，也不写入公开文件；
- HTTP `200` 仍只是中间证据。必须继续验证刷新后的媒体记录、媒体 ID、最终 URL、匿名访问、Content-Type 和实际图片解码；
- 接口结果未知时先按唯一标题查询媒体库，禁止自动重发；
- 五图语义化 UI 流程可作为 2–5 张临时回退，但不能把它冒充纯接口；
- 已证明纯接口单图和 10 张单图接口串行调用；这不等于一次请求上传 10 张。源 SHA-256 复用、原子索引、单写者锁、请求阶段记录、跨重启只读恢复、AI `title / alt / caption` 同步，以及上传报错后的延迟对账与有限重试规则已实现并通过 47 项媒体本地测试；正文图片 adapter 已升级为 schema 2、逐 occurrence 双重复核、`bindingProof`、文章 operation lock 和整篇单次保存，并通过 52 项本地测试；当前 trusted runtime profile 为四文件 160/160，历史 158/158 已陈旧并必须拒绝，完整 Adapter 11 文件 dev suite 回归为 267/267；一张获授权虚拟媒体的字段写入最终三字段持久化，但观察到读后写延迟。当前部署的 A/B/A 正文草稿绑定已验证；任意大批次真实远程长跑、跨部署正文绑定、一次请求多图和覆盖仍未验证。并发上传永久禁止，不作为后续优化目标；媒体记录删除只按卡片与 RSC 记录消失验收。


### 2026-07-27 图片元数据实查与单样本写入

- 上传弹窗没有 title、alt、说明输入框；
- 上传后编辑弹窗有 `title`（标题）、`alt`（替代文本）、`caption`（说明）；
- 当前 adapter 可保存 AI 生成的 `title / description / alt / caption / metadata` 到客户私有索引；
- `updateMediaAction` 已捕获；一张获授权虚拟媒体只发一次字段写请求，稍后新鲜刷新确认 `title / alt / caption` 全部持久化且 media ID / URL 未变；
- `uploadAllinCmsMediaSerial()` 可用 `syncRemoteMetadata: true` 逐张同步；每张写后只做有限只读刷新，未完全确认时停止本批，不重发、不重传；
- 删除完成只看媒体卡和 RSC 媒体记录消失，底层对象/CDN 状态退出完成口径。

### URL 取值规则

1. 优先采用 AllinCMS 最终媒体记录返回的 `public_url` 或 `canonical_url`；
2. 不保存短期预签名 URL；
3. 不擅自删除平台返回 URL 的查询参数；
4. 在无登录浏览器中验证 HTTPS、Content-Type 和实际解码；
5. 内容草稿若要求 `media_id`，不得只写 URL；
6. 保存源文件 SHA-256、上传输入 SHA-256、最终远端 SHA-256、media ID 和 URL；平台可能重编码图片，不能假设本地与远端哈希相同。MD5 仅作兼容字段，不作为唯一主键。

### 重名与幂等

- 同 hash、已有媒体记录且公开 URL 仍有效：默认复用，不重复上传；
- 同文件名、不同 hash：生成 `slug-shortHash.ext`，禁止静默覆盖；
- 接口超时但结果未知：先查询媒体库或按 hash 查重，再决定是否重试；
- 已验证 10 张采用单图接口串行调用；每张独立全链验收，任一结果不明立即停止后续调用，先按唯一标题对账；
- 语义化 UI 回退仍只允许一次选择 1–5 张；每张记录独立结果，失败后先对账，不自动重传整批；
- 删除、覆盖、替换 URL 和清理孤儿对象属于独立高风险动作，不和上传授权合并。

## 5. 首次抓取与后续执行

### 第一次，仅一张虚拟测试图

```text
确认已登录并确认目标站点
→ 准备一张唯一命名的虚拟图片
→ 用户批准该站点和该文件的上传
→ UI 触发一次并用 CDP 捕获协议
→ 验证媒体记录、媒体 ID、最终 URL、匿名访问和刷新持久化
→ 只保存去敏合同与构建 / 动作指纹
```

### 后续默认：预检 + 串行总控

前置硬条件：先在受控浏览器中打开并加载目标网站的 AllinCMS **后台媒体页** `https://workspace.laicms.com/{site_key}/media`。它可以是后台标签页，不要求屏幕前台显示，但不能只打开目标网站前台首页，也不能在没有该已登录页面上下文时直接发请求。`imageIndexPath` 必须是客户私有运行区中的绝对路径。

```text
读取 AI-START-HERE.md 和机器合同
→ 打开并加载目标后台媒体页
→ 运行 checkAllinCmsMediaRuntime()
→ 调用 uploadAllinCmsMediaSerial()，一次处理本轮全部图片
→ 每张先写 prepared，再在请求发出前写 request_started
→ 总控内部动态发现合同并调用一次 uploadAllinCmsMediaDirect()
→ 自动刷新并验证媒体卡、media ID、最终 URL、匿名访问和图片解码
→ 原子写入源 / 规范化上传 / 远端三组哈希与 URL 映射
→ 当前图片 verified 或 reconciled_existing 后才进入下一张
→ 失败或结果不明先只读对账，不自动重传
```

2026-07-27 的真实远程证据来自最多 10 次单张接口串行调用；当前业务入口已经收束为 `uploadAllinCmsMediaSerial()`，其他 AI 不得重新围绕 `uploadAllinCmsMediaDirect()` 手写循环。`prepared` 表示请求尚未开始：若恢复时发现同标题远端记录，必须按“预存标题冲突”停止，不能把它认领为本轮上传。`request_started` 恢复成功时必须保留已记录的规范化上传 SHA-256 / MD5。

这不等于一次 multipart 多文件请求。控制器不设图片数量上限，但永久严格串行：逐张请求、逐张刷新、逐张验收；平台真实远程证据目前到 10 张，本地控制器已覆盖 12 张。

### 2–5 张临时 UI 回退

用户明确接受文件选择器时，可使用一次文件选择、一次提交的语义化 UI adapter；不得称为接口上传。

### 漂移时

出现以下任一情况，立即停止写入并重新捕获：

- 401 / 403 / 登录重定向；
- 404 / 405 / 422 或响应类型变化；
- Server Action ID、字段结构、请求步骤或 CDN 域名变化；
- 返回 2xx 但媒体库无记录；
- URL 需要登录、已过期、Content-Type 错误或前台不显示；
- 站点列表与 `/sites` 页面不一致；
- 无法确定写入的是哪个站点。

## 6. 对抗审查

| 风险 | 容易出现的假成功 | 防线 |
|---|---|---|
| 把内部接口当官方 API | 页面升级后突然失效 | 标记 `observed_internal_contract`，保存观察日期和构建指纹 |
| 只抓上传到存储的一步 | 对象存在但媒体库无记录 | 捕获授权、上传、登记、读取媒体记录全链路 |
| 把预签名 URL 当图片外链 | 几分钟或几小时后失效 | 只接受最终媒体记录中的可公开 URL |
| 返回 2xx 就判成功 | 图片未入库、未绑定或前台不显示 | 后台记录、匿名访问、草稿绑定、刷新持久化和前台五层验收 |
| 默认第一个站点 | 多站点账号写错站 | 标准化列表并在写动作前确认目标指纹 |
| 空数组被当成无站点 | 实际是登录过期或解析失败 | 显式区分 empty、unauthorized、redirected、parse_error |
| 导出 cookie 做脚本 | 凭据泄露、长期失控 | 在同源浏览器会话内调用，不把 cookie/token 写文件 |
| 硬编码 Next Action ID | 部署后请求漂移 | 每次从当前页面 chunk 动态发现 action，并保存长度 / 散列而不是完整值 |
| 重试造成重复图片 | 超时或 CDP 报错后再次上传 | 接口发出后先刷新媒体库按唯一标题对账，adapter 不自动重传 |
| 批量 RSC 记录串行错配 | 相邻对象的 ID、标题和 URL 被混在一起 | 按目标 URL 定位完整 JSON 对象，并再次校验对象内 URL 和标题 |
| 固定等待导致选站假失败 | 500 ms 后 URL 尚未切换 | 等待目标 `/{site_key}/...` URL，超时才停止 |
| 受控环境缺少 `new Image()` | 上传成功但验证器自身报错 | 读取媒体卡已有 `<img>` 的 complete 与 naturalWidth/naturalHeight |
| 只记录 URL | 内容模型实际要求 media_id | 返回完整 `MediaAsset`，同时保存 ID、URL 和元数据 |
| 只看 DOM 卡片判断登录或完整列表 | 旧页面、分页和渲染失败会误判 | API-first 解析当前 RSC；DOM 只做登录交接与合同漂移诊断 |

## 7. 权限与动作闸

| 动作 | 默认许可 | 是否需要动作时确认 |
|---|---|---|
| 当前浏览器 session 请求 `/sites?_rsc`，读取登录、用户和完整站点列表 | read-only | 未登录才打开 `/sign-in`；不导出凭据 |
| 选择目标站点 | read-only decision | 用户确认站点指纹 |
| 上传一张指定虚拟图片 | mutation | 是，只授权该站点和该文件 |
| 在同一已授权批次内串行上传后续图片 | batch mutation | 可继续，但必须逐张验收并在首个不明结果处停止 |
| 一次上传 1–5 张 | batch mutation | 已验证到 5 张；每次仍需确认目标站点和具体文件 |
| 6–10 张单图接口串行调用 | batch mutation | 已验证到 10 张；不允许并发，结果不明先停并对账 |
| 任意数量 | batch mutation | 控制器不设数量上限；仍逐张执行。真实远程证据到 10 张，本地测试覆盖 12 张 |
| 一次请求多图 | batch mutation | 未验证，不得假设与逐张接口等价 |
| 并发上传 | prohibited | 明确禁止，不使用任务池、多标签或重叠请求 |
| 删除测试图、清理孤儿对象 | destructive | 单独批准 |
| 发布产品、文章或页面 | publish | 与媒体上传分开批准 |

## 8. 当前状态

```yaml
reference_cms: AllinCMS
official_ui_workflow: confirmed
public_developer_api: not_confirmed
site_list_contract: captured_read_only
media_upload_contract: captured_direct_single_serial_ten_and_semantic_five_file_fallback
direct_server_action_replay_single: verified
direct_single_requests_serial_batch_10: verified
direct_server_action_replay_batch: not_verified_one_request_batch
parallel_direct_batch: permanently_disallowed_not_a_delivery_target
ui_clicks_required_for_direct_single: false
filechooser_required_for_direct_single: false
semantic_browser_single_upload: verified
semantic_browser_batch_upload_5: verified
source_sha256_reuse_and_atomic_index: implemented_local_tested
cross_restart_read_only_recovery: implemented_local_tested
prepared_title_collision_guard: implemented_local_tested
request_started_normalized_hash_recovery: implemented_local_tested
remote_recovery_e2e: not_verified
batch_idempotency_remote_e2e: not_verified
batch_failure_retry_remote_e2e: not_verified
content_schema_read_only: captured
category_create_contract: verified_single_observed_deployment
post_create_ui_draft: observed_single_virtual_record
post_create_api: blocked_requires_current_contract_and_exact_new_id
post_update_publish: verified_current_deployment
content_binding: verified_remote_draft_A_B_A_2026_07_27
article_binding_entry: cms/allincms/article-image-binding.mjs
article_operations_local_tests: 36_passed
article_image_binding_local_tests: 50_passed
all_adapter_local_tests: 131_passed_2026_07_30
article_editor_health_gate: editor_present_exact_image_count_decode_caption_and_draft_status
article_editor_dom_alt: missing_observed_3_of_3
published_theme_alt_current_run: not_run_not_authorized
media_record_delete_direct: verified
physical_asset_cleanup_after_delete: out_of_scope
publication_status: PASS_DRAFT_BINDING_WITH_DOCUMENTED_ALT_PRODUCT_GAP__BLOCK_PUBLISHING_CROSS_DEPLOYMENT_RECOVERY_AND_ROLLBACK
```

## 9. 其他 AI 的下一次最小闭环

默认不要再点上传按钮：

1. 先读取 [AI 唯一执行入口](allincms/AI-START-HERE.md)，不得重新抓接口或模拟点击；
2. 在受控浏览器中打开并加载目标网站的后台媒体页 `/{site_key}/media`，检查登录、站点名称和 `site_key`；页面可在后台标签页，但不能关闭；
3. 确认本轮全部文件与私有绝对 `imageIndexPath`，确保每个 filename stem 唯一；
4. 运行 `checkAllinCmsMediaRuntime()`；只有 `ready` 才调用 `uploadAllinCmsMediaSerial()`；
5. 让总控负责逐张直传、自动刷新、验收、原子索引和断点恢复，不得手写单张循环；
6. 同时保存媒体 ID、最终 URL和源 / 规范化上传 / 远端三组哈希；
7. `prepared` 恢复时若发现远端同标题记录，按预存标题冲突停止，不得自动认领；上传报错后先延迟并只读对账，只有确认远端不存在才允许总控有限重试当前图片；
8. 只有直传合同漂移，且用户明确接受文件选择器时，才调用 `uploadAllinCmsMediaBatch()`；
9. 一次请求多图、内容绑定或发布仍需独立验证和授权；控制器不设文件数上限，但并发上传永久禁止。媒体记录删除每次仍需单独授权，完成口径只看媒体记录消失。
10. AI 读图候选字段先写私有索引；当前已观察到编辑字段 `title / alt / caption`，但直接元数据更新接口尚未捕获，详见 [图片元数据与 AI 读图 SOP](allincms/media-metadata-and-ai-vision-sop.md)。

## 10. Open Questions

- `/sites` 是否存在分页、多个 workspace、归档、禁用或邀请中站点？本次响应未证明分页已穷尽。
- AllinCMS 产品 / 文章字段最终引用 URL、`media_id` 还是完整媒体对象？
- 本地已用源 SHA-256 做 verified 映射复用；真实远程复验后，是否还需要平台侧可查询的稳定资产指纹，避免仅依赖标题完成跨系统对账？
- 当前已捕获并单样本验证 `title / alt / caption` 直接更新合同；后续仅需在自然获批运行中观察跨部署稳定性。
- 是否支持按最终资产查询、删除、替换和孤儿对象清理？
- 内部接口变化时，能否通过稳定的应用版本或构建 ID 自动触发重新捕获？
