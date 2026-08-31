---
title: "AI Start Here: AllinCMS API-first Content Operations"
description: "其他 AI 执行 AllinCMS 登录交接、站点发现、计划驱动内容操作、图片上传与文章操作时的唯一入口。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-13"
sources: ["media-operations-contract.redacted.json", "article-image-binding-contract.json", "direct-delete-verification.redacted.md", "Observed signed-in upload and draft-binding runs 2026-07-27", "Local fault tests 2026-07-27", "Tony default browser, login handoff, site discovery, and interface fallback decision 2026-07-30"]
related: ["../../../REFERENCES/ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json", "README.md", "content-run-controller.mjs", "live-run-evidence.schema.json", "INTERFACE-INDEX.md", "interface-registry.json", "interface-registry.schema.json", "media-metadata-and-ai-vision-sop.md", "article-operations.md", "upload-media-browser.mjs", "article-image-binding.mjs", "article-operations.mjs", "article-operations-contract.json", "upload-media-browser.test.mjs", "article-image-binding.test.mjs", "article-operations.test.mjs", "interface-registry.test.mjs", "media-operations-contract.redacted.json", "article-image-binding-contract.json", "../../image-upload-routing.md"]
confidence: "high-for-observed-upload-contract-medium-for-new-local-recovery-layer"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AI 唯一执行入口：AllinCMS API-first 网站与内容操作

> **教程查询路由：** 用户先问“后台怎么操作”时，运行 `node ../../../scripts/query-allincms-official-tutorial-index.mjs "用户问题"` 并打开命中的官方原页核验；用户问 API、字段、登录态或真实 mutation 时，教程不构成接口证据，继续按本页、[Interface Index](INTERFACE-INDEX.md) 和当前部署证据执行。

> **通用资料驱动前置门槛：** 若用户提供 PDF、DOCX、表格、网站、图片或 brief，并要求新建/更新网站、文章或产品，先执行 `<SUB_LIBRARY_ROOT>/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md`：按宿主能力生成并校验私有 `TEMPLATES/source-extraction.md`，再生成并验证 `TEMPLATES/content-operation-plan.md`。本 Adapter 只消费已冻结、source-backed 的 desired state 和精确 operation；不得从历史示例写死站点、语言、taxonomy、CTA、字段、组件、产品结构或 Action ID。`upsert` 必须先只读解析为 `create/update/noop`；`update` 必须绑定 exact ID/站点内唯一 natural key 和 expected-current fingerprint。远程 mutation 只接受当前 deployment 的未过期 `live_verified_current_deployment` capability。产品 create/update/publish 已注册 canonical 模块与路由，但仍受当前 deployment 的 `fresh_live_verified_current_deployment` 门禁，不能在缺少真实运行证据时宣称稳定创建、更新或发布。

> **授权与执行口径：** 用户批准的是一份 digest 固定、站点固定、operation 顺序固定的计划，不是每个接口各问一次，也不是永久授权。调用 `content-run-controller.mjs`（仅完整源码 checkout） 后，Controller 会在每个 operation 前和请求真正发出前机器复核授权、capability、deployment、目标站点与依赖 readback；请求可能已发出时只允许只读 reconcile，结果仍不明即 `ambiguous/BLOCK`，禁止盲重试。发布只有在获批计划已明确包含 `publish` operation 时才能执行；否则生成新计划并重新授权。

## 不要重新研究路线

跨对象计划默认路线：

```text
validateContentOperationPlan(approved immutable plan)
→ runAllinCmsContentPlan()
→ 每步 preflight + evidence checkpoint
→ execute once
→ ambiguous transport 只读 reconcile
→ authoritative readback
→ 下一 operation；任一终态失败立即停止
```

`content-run-controller.mjs` 当前属于完整子库源码入口，因为它依赖上游 plan/runtime-scope validator；不要从 npm adapter 的最小 `package.files` 推断该 Controller 已可脱离子库独立分发。接口 Registry 和独立分发状态在后续接口索引项中单独判断。

只要目标是 **AllinCMS 媒体库**，默认使用本目录 adapter：

```text
checkAllinCmsMediaRuntime()
→ AI 逐张读图并生成候选
→ uploadAllinCmsMediaSerial()
→ 每张上传、刷新、验收并原子写索引
→ 若获授权则接口写 title / alt / caption，并做有限只读复核
→ 当前图片完整结束后才进入下一张
```

不要先配置 PicGo、R2、GitHub、COS 或 OSS。它们只在用户明确需要外部图床时使用，见完整子库源码中的 `../../image-upload-routing.md`；该上层路由不随独立 npm adapter 包分发。

查询接口时先看 [INTERFACE-INDEX.md](INTERFACE-INDEX.md)，机器检索以 [interface-registry.json](interface-registry.json) 为真源。按 export 名、`interface_id`、domain、exposure 或 lifecycle 检索；`internal`、`compatibility`、`blocked` 只能用于维护、兼容或审查，不能绕过 canonical controller。索引必须通过 `npm run interfaces:index:check`，不得手工维护第二份接口清单。

## 接口和能力路由查询

先读取 [interface-registry.json](interface-registry.json) 的 22 条 `capability_routes` allowlist，按 `entity_type + action` 查当前默认接口、执行门禁、执行面、串行 Controller 和验收要求；人类视图见生成的 [INTERFACE-INDEX.md](INTERFACE-INDEX.md)。`canonical` 只表示 Adapter 默认路径，不表示当前登录态、deployment capability 或 mutation 授权已成立；`exploration_only` 只允许只读探索，`blocked` 不得执行。当前 `site:create` 与 `product:create/update/publish` 已注册 canonical 路由，但都受 `fresh_live_verified_current_deployment` 门禁；`product.discover/delete`、文章创建和媒体元数据更新仍不是通用 canonical 执行路由；所有 delete 与 article unpublish 在通用 immutable plan / 薄 Skill 中同样 fail closed。底层 export 被 Registry 登记只解决“可查询”，绝不等于该动作已进入通用执行路由。

`content-run-controller.mjs` 是完整子库源码 checkout 的 canonical 串行 Controller，但未进入最小 npm adapter 包，因为它依赖子库上层 plan、runtime scope 和 schema helper。共享薄 Skill 必须先 resolver 到完整 canonical 子库；只有最小 npm 包时，不得声称跨对象 plan Controller 可执行。

## 0. 默认启动、登录交接与回落路由

任何电脑、任何 AI 收到 AllinCMS 站点发现、建站、媒体或文章任务后，先执行这一节。**登录状态、当前用户和网站列表默认由接口判断；页面 DOM 只用于登录交接和异常诊断。** 机器合同、代码和字段说明见 [Workspace API-first 前置检查](workspace-preflight.md)、[workspace-preflight.mjs](workspace-preflight.mjs) 与 [workspace-preflight-contract.json](workspace-preflight-contract.json)。

### 0.1 API-first Workspace 前置检查

1. 先取得宿主**内置 Browser**的可控会话，在该浏览器登录上下文中执行 `GET https://workspace.laicms.com/sites?_rsc={nonce}`，请求头为 `Accept: text/x-component`、`RSC: 1`，并使用 `credentials: include`。不得读取、导出或复制 Cookie、Token、密码和密钥。
2. 以 `2xx + 最终 URL 非 /sign-in + RSC 同时含 user 和 sites payload` 作为已登录证据。HTTP 200、旧页面 DOM、旧标签页标题或“之前登录过”都不能单独证明当前登录。
3. **取得浏览器会话不等于打开 `/sites` 给用户看。** 优先复用现有 `workspace.laicms.com` 同源标签页，在后台用 CDP `Runtime.evaluate` 执行 credentialed `fetch`；正常已登录检查禁止 `goto()`、禁止切前台、禁止点击。只有完全没有同源执行上下文时，才允许创建一个不前台展示的后台 session transport 标签页；仍必须用新鲜 RSC 响应判断登录和站点列表，不能改用页面卡片作为机器真源。
4. 内置 Browser 无法提供可控会话时，先报告浏览器控制问题并尝试恢复；仍不可控才可回落到 Chrome 或其他宿主浏览器。所有浏览器都不可控时标记 `BLOCK`，不得改成导出 Cookie 或独立 Node 凭据绕过。

推荐入口：

```text
runAllinCmsWorkspacePreflight({ fetchPage, openLoginPage, targetSite })
```

`fetchPage(request)` 必须由宿主绑定到当前浏览器 session；该 Adapter 不持有账号凭据。

### 0.2 未登录时必须立即打开登录页并交接

接口返回 401 / 403、最终 URL 为 `/sign-in`，或响应是登录内容而不是 Workspace RSC 合同时，AI 必须立即：

1. 用宿主内置 Browser 打开 `https://workspace.laicms.com/sign-in`；
2. 保持登录页可见并切到前台；
3. 明确提醒：`AllinCMS 后台尚未登录。我已打开登录页，请完成登录；完成后告诉我“已登录”，我会重新通过接口检查当前用户和网站列表。`；
4. 若出现验证码、MFA、账号错误、循环跳转或登录页异常，报告屏幕上实际问题和用户下一步；
5. 用户说“已登录”后，重新请求 `/sites?_rsc`；不能复用登录前响应、旧 user、旧 sites 或旧站点选择。

如果宿主没有传入 `openLoginPage()`，Adapter 只会返回 `hostActionRequired: open_login_in_in_app_browser`，不会假装登录页已经打开。`openLoginPage()` 只允许在 API 已分类为 `login_required` 后调用；`authenticated`、`http_error`、`contract_drift` 和分页异常都不得触发可见导航。

### 0.3 当前用户 ID、完整网站列表与精确选站

当前 AllinCMS 用户 ID 的唯一认可来源是 Workspace RSC 的 `user.id`；同时可读 `user.name / user.email / user.role / user.tenant`。不得从邮箱推导用户 ID，也不得拿外部认证平台 ID 替代。真实用户 ID、邮箱、tenant、Cookie 和 Token 不得进入公开母库、fixture 或日志。

站点列表读取字段：

```text
data[].id / name / description / slug / domains / displayDomain
data[].active / themeCount / createdAt
pagination.* / canCreate
```

当 `pagination.totalPages > 1` 时必须逐页读取、按站点 `id` 去重，并验证唯一站点数等于 `totalDocs`；否则返回 `pagination_incomplete`，不能宣称列表完整。Tony 已删除的历史站点不再出现在当前列表属于正常状态，不得继续沿用旧站点 scope。

| 观察结果 | AI 动作 | 是否可进入写入 |
|---|---|---|
| 0 个站点 | 报告 `zero_sites`；可说明账号当前无站点，并询问是否要按获批名称创建，不得自动创建临时站点 | `BLOCK` |
| 1 个站点 | 回显精确 `name + id/slug/displayDomain`；只读可继续，写入前仍需绑定精确目标 | 用户确认后才可 |
| 多个站点 | 列出完整网站列表，让用户按精确 `id / slug / displayDomain` 选择；不得按排序、最近活动或旧会话猜选 | 用户选择后才可 |
| 用户指定站点不可见 | 返回 `target_not_visible`，核对账号、邀请和权限 | `BLOCK` |
| 分页、用户身份或合同在读取中变化 | 返回 `pagination_incomplete` 或 `contract_drift`，重新做一次新鲜只读检查 | `BLOCK` |

### 0.4 新增网站 API 和字段边界

当前部署的新增网站不是公开 JSON REST，而是 `/sites` 页面动态发现的 Next.js Server Action `createSiteAction`。客户端业务字段只有：

| 字段 | 必填 | 当前约束 |
|---|---:|---|
| `name` | 是 | string，2–50 字符 |
| `description` | 否 | string，最多 200 字符；UI 默认空字符串 |

`user.id / tenant / role` 由服务端 session 注入，不进入客户端 payload；站点 `id / slug / 默认域名 / 默认 setup` 由服务端生成。`Next-Action` 是 opaque runtime value，当前实测长度为 42 位，但实现只接受动态发现的 40–64 位十六进制值，绝不能永久硬编码。实际创建前还必须重新取得当前 `Next-Router-State-Tree` 和可选 `x-deployment-id`。

`canCreate` 只表示当前列表响应声明的客户端可创建能力，不是 mutation 授权，也不是远程执行成熟度。新建站必须先生成 `site_bootstrap` Plan A：target 为当前 RSC 回读的 `user.id`，`site_key/site_id=null`，只含一个 `site:create`，`publication_effect=non_public_resource`。当前源码已注册 `site-operations.mjs` 和 canonical `site:create` 路由；但仍必须以当前 deployment 的新鲜 `live_verified_current_deployment` capability 为准，不得因模块存在或历史运行就放宽门槛。

未来 capability 经本次 deployment 的真实单样本升级后，Plan A 才可在精确 `name + description` 授权下严格调用一次。验收必须用完整网站列表 before/after 唯一 ID 差集证明只新增 1 个站点，并回读 `site_id / site_key(slug) / account owner / displayDomain / setupError`；HTTP 200 或 toast 不足以判定成功。然后停止 Plan A，以该私有 readback 和 Plan A digest 生成全新的 `site_operation` Plan B，重新发现 capability/current state 后才处理分类、标签、媒体、文章、产品或主题页。Adapter 不接受一个同时 create site + populate 的计划。

### 0.5 精确媒体页与页面健康检查

站点确认后，打开 `https://workspace.laicms.com/{site_key}/media`，并同时确认：

- origin、URL 路径和 `site_key` 精确一致；
- 登录仍有效，目标站点身份没有跳转或串站；
- 媒体列表能完成加载，不是 404 / 500 / 空白 / 持续 Loading；
- 页面存在媒体列表和上传入口；必要时只读打开上传弹窗，检查格式、大小提示和按钮状态，但**不选文件、不点击最终上传**；
- Console 没有阻断性错误；如果需要检查 Network，只做诊断或已授权请求的证据读取，不重新捕获凭据。

只有 Workspace API 前置检查、精确站点身份和媒体页面健康都成立后，才运行 `checkAllinCmsMediaRuntime()`。

### 0.6 接口优先，页面诊断和 UI 回退分开

```text
默认：Workspace API 前置检查
→ checkAllinCmsMediaRuntime()
→ 展示精确 site_key、操作和有序文件列表
→ 用户批准
→ 创建精确 authorizationContext
→ uploadAllinCmsMediaSerial() 接口串行上传

接口异常
→ 先判断请求是否可能已经发出
  ├─ 可能已发出：延迟 + reconcileAllinCmsMediaDirect() 只读对账，禁止重传
  └─ 确认未发出：打开/保持精确媒体页做登录、站点、权限、页面和部署诊断
→ 页面正常但接口合同漂移：报告漂移证据和下一步，不自动改走 UI
→ 用户另行明确批准 UI 回退：仅 1–5 张调用 uploadAllinCmsMediaBatch()
→ 页面也异常或没有可控浏览器：BLOCK
```

页面诊断至少覆盖：新鲜 Workspace API 登录状态、完整站点列表与目标站点权限、精确媒体 URL、页面 404/500/空白/Loading、上传入口及格式/大小提示、Console 错误、401/403、Server Action/deployment/action ID 漂移、同标题媒体是否已存在、请求状态是否不明确、Browser/CDP/Playwright 能力，以及本机 Node、`sharp`、绝对路径、格式、大小、symlink 和文件 digest。

每次遇到问题都用下面四行即时告诉用户，不能等到流程末尾才补报：

```text
当前问题：<登录 / 站点 / 权限 / 页面 / 接口 / 本机依赖的具体问题>
已确认：<当前 URL、可见状态和只读证据>
需要你做：<登录、选择站点、授权、补权限或无需用户动作>
我接下来：<重新 API 检查 / 只读对账 / 页面诊断 / 停止>
```

## 本库与共享 Skill 的权威关系

当前知识库中的 `ADAPTERS/cms/allincms/`（从子库根目录看） 是 **AllinCMS 当前部署实测 Adapter、文章字段合同、taxonomy 合同、状态机和验证证据的权威来源**。

共享的 `allincms-bulk-content-upload` Skill（安装位置由宿主环境决定） 是共享的入口、编排和 SOP 层：它负责把源资料、manifest、批次和验证串起来，但不得自行复制、重写或覆盖本库当前实测合同。两者冲突时，以本库的 Adapter/合同为准；共享 Skill 应引用本库，而不是保留旧假设。

文章生命周期与正文图片是两个 companion：

- 文章、分类、标签、创建/保存/发布/取消发布/删除、失败恢复和串行批次：`article-operations.mjs`；
- 文章格式矩阵、12 个 canonical Slate 示例和 Markdown → Slate 保守转换：`article-content-formats.mjs`（由 `article-operations.mjs` 统一 re-export）；
- Markdown 正文图片原位绑定、Slate 图片节点和编辑器健康闸：`article-image-binding.mjs`；
- 共享机器字段和动作模板：`article-operations-contract.json`。

## 强制规则

1. 不重新抓上传、正文保存或删除接口，不复制本文件中的循环另写脚本。
2. 默认接口路径不模拟点击上传、不打开文件选择器、不用坐标点击；只有用户另行明确批准 1–5 张 UI 回退后，才允许 adapter 使用语义化控件和文件选择器。
3. AI 必须先按第 0 节通过当前浏览器 session 做 Workspace API 前置检查；只有未登录才打开并前台展示登录页。目标站点确认后再打开准确页面 `https://workspace.laicms.com/{site_key}/media`；不得把登录判断、完整站点列表或找页面的责任丢给用户。
4. `site_key` 未经用户确认、页面不准确、登录失效、无站点或目标站点不可见：停止，不做写操作。
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
23. 文章 `postCreate` 不是默认放行的远程动作：只有重新捕获当前部署的完整 create 合同，同时提供创建前后的完整文章 ID snapshot，证明差集恰好只有一个新 `postId`，且该 ID 与同站点创建记录精确一致，并显式传入 `createContractConfirmed: true` 时才允许调用；仅证明“某个 ID 以前不存在”不够，否则保持阻断。
24. 分类 / 标签创建必须带当前站点 taxonomy snapshot，用同站点 slug 做请求前重复检查；snapshot 中每条记录都必须显式携带已证明的 `siteId`。若当前 RSC 记录省略 `siteId`，controller 必须先从精确站点页面上下文验证站点，再为每条记录补入该 `siteId`；不得把路由作用域当作隐式租户证明直接传给 adapter。任何记录缺失 `siteId` 时必须在请求前停止。写后回读必须同时证明非空唯一 ID、精确 `siteId`，以及本次提交的 `name / slug / description / cover / parent / order` 等全部适用字段。精确文章 taxonomy route 的回读可省略 `contentType`，此时只按 route-scoped `posts` 处理；若显式返回非 `posts` 值则停止。snapshot 缺失、字段丢失或无法确认唯一对象时停止。
25. runtime 如果提供 `actions` 映射，缺少具体 action 必须 fail-closed；文章回读缺少状态或包含冲突状态时，不能把 HTTP 200 当成功。
26. 本地控制测试通过不等于新的远程部署通过；每次部署或站点变化都要重新捕获运行时合同，并把远程证据与本地证据分开报告。

## 0.6 canonical mutation 与只读 operation 的验收证据（不可降级）

机器真源是 [verification-evidence-contract.json](verification-evidence-contract.json)，接口路由是 [interface-registry.json](interface-registry.json)。两套验收 profile 必须分开匹配：

- mutation profile 绑定 `capability_routes`；对 `category/tag create|update`、`media:create`、`article:update|publish`，plan 的 `readback_requirements`、Registry route 和 verification profile 必须**精确相等**；
- `read_only_profiles` 绑定 `noop/explore` intent；`noop` 不发送远程请求，只做 authoritative same-site readback；`explore` 最多发送当前批准的一次只读请求，再做 authoritative same-site readback；
- 两套 profile 互不替代。只读 PASS 不能证明 mutation capability，也不能删减 mutation required checks；任何 profile 缺项、增项或漂移都必须在请求前 BLOCK；
- `noop/explore` 失败都不得进入 write/mutation reconciliation，不能盲目重试或改走写接口。

```text
HTTP 200 / toast / 后台状态字符串 / 单一截图 ≠ PASS
```

每个 check 必须同时满足：

1. task/site/site ID/entity ref/entity ID 与批准 operation 精确绑定；exact-ID update/publish 必须等于批准 ID；
2. `subject_digest` 绑定 Controller 从不可变 operation + desired entity 派生的 subject；
3. `observed_at` 位于该 operation 的开始与完成窗口内；
4. primary proof 是当前客户任务目录内的 `application/json` artifact；
5. `readEvidenceArtifact()` 读取实际字节后重算 SHA-256，且 parsed JSON envelope 与 structured check 精确一致；截图只能作为 JSON 内补充引用；
6. taxonomy 要 precise ID、全部提交字段、exact same-site binding 和 create duplicate exclusion；
7. media 要 backend ID、persisted HTTPS URL、anonymous GET、actual decode、metadata readback，三处 URL 一致；
8. article update 要 expected-current fingerprint、全部字段、editor reopen、taxonomy/media binding；
9. publish 要 backend published state、editor reopen、exact public URL、anonymous exact detail、visible content；适用图片必须实际 decode，三项 public URL 一致；
10. noop/explore 要使用 intent 对应的 `read_only_profiles`，证明 authoritative same-site readback 与精确站点绑定；noop 的 transport 必须保持未启动，二者的 reconciliation 必须保持未执行。

`validateAllinCmsLiveRunEvidence()` 是离线结构/绑定 validator，不读 artifact bytes、不访问远程 CMS；primary artifact 字节与 envelope 验证只在源码 checkout 的 `runAllinCmsContentPlan()` live path 执行。本地 PASS 不证明当前登录、远程写入、匿名前台、SEO、询盘/转化、Stable、Published 或 production-ready。

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
    "/absolute/private-runtime/images/02.png"],
});
```

只有 `readiness.status === "ready"` 才进入上传。

- 小于等于 1 MB 的 WebP 不依赖 `sharp`；
- PNG、JPG 和较大的 WebP 需要本目录 `package.json` 声明的 `sharp`；
- `sharp` 缺失时明确阻断相关文件，不得偷偷切换 UI；
- 安装依赖属于机器状态变更，须先得到用户批准；批准后可在本目录执行 `npm install`。

## 3. 默认上传任意数量并写本地索引

`imageIndexPath` 必须位于客户自己的私有运行区，不能写进公开母库。下面的授权与上传代码只能在用户已经看到精确 `site_key`、操作和有序文件列表并明确批准后运行：

```js
const localFiles = [
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
  "/absolute/private-runtime/images/02.webp"];

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
  authorizationContext,
  progressMode: "visible",
  maxAttemptsPerImage: 3,
  retryDelaysMs: [2000, 5000],
  syncRemoteMetadata: true,
  metadataAuthorizationConfirmed: true,
  localFiles,
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
const { createAllinCmsArticleImageAuthorizationContext } = await import(
  "<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/mutation-authorization.mjs"
);

const expectedSiteKey = "用户已确认的-site-key";
const expectedPostId = "用户已确认的-post-id";
const authorizationContext = createAllinCmsArticleImageAuthorizationContext({
  siteKey: expectedSiteKey,
  postId: expectedPostId,
  approvalActor: "当前用户声明的具名 actor",
  // approvedAt / expiresAt 默认使用当前 UTC 时间和最长 30 分钟有效期；
  // 如显式传入，必须是规范 UTC ISO 时间且不得超过 30 分钟。
});

const result = await articleImages.bindAndSaveAllinCmsArticleDraftDirect({
  tab,
  expectedSiteKey,
  expectedPostId,
  sourceMarkdown,
  manifest,
  mappings,
  manifestPath: "/absolute/private-run/article-image-binding.json",
  authorizationContext,
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

机器合同见 [article-image-binding-contract.json](article-image-binding-contract.json)，实现见 [article-image-binding.mjs](article-image-binding.mjs)；源码 checkout 中的 `article-image-binding.test.mjs` 与 `article-image-binding-adversarial-review.redacted.md` 分别保存本地故障测试和去敏对抗复核证据，不随独立 npm adapter 包分发。

## 7. 删除媒体记录

> **当前执行入口 BLOCK。** `deleteAllinCmsMediaDirect()` 的实现和媒体机器合同仍使用旧的裸布尔 `authorizationConfirmed`，尚未迁移到与准确 `site_key`、删除 operation、目标摘要、具名 actor 和有效期绑定的结构化 `authorizationContext`。因此本入口不再提供可复制的删除调用示例；即使用户口头同意，也不得由 AI 调用该旧接口。先完成实现、合同和测试的结构化授权迁移，再恢复远程删除。

历史证据只能证明 2026-07-27 在当时部署中完成过一次精确媒体记录删除，不证明当前授权边界合格，也不能作为新的删除授权。迁移后仍必须精确绑定 media ID、标题和 URL；不要批量猜 ID，不要把一次授权扩展到其他记录，不要自动重发歧义删除。成功状态 `media_record_deleted_and_verified` 也只证明精确媒体卡和 RSC 媒体记录已消失，不证明底层对象或 CDN 已物理删除。

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

当前正式冻结的文章/媒体 runtime qualification profile 固定为四文件 158 项：45 项媒体测试、52 项文章图片测试、13 项正文格式测试、48 项文章生命周期与 taxonomy 测试。完整源码工作树的 `npm test` 另含 21 项 Workspace 登录/用户/站点/建站合同测试、58 项严格串行 Controller 测试和 11 项接口 Registry 测试，七文件当前全量为 251/251；正式 158 项 profile 与完整 251 项开发回归不得互相替代。全量共同覆盖严格串行、授权时效与 TOCTOU 边界、延迟对账、禁止盲目重传、原子索引、单写者锁、断点恢复、A/B/A 复用、源文哈希和锚点防漂移、Caption 全数组结构预检、taxonomy route-scoped `contentType`、跨 realm JSON 语义比较、封面 canonical 持久化字段与非空封面 payload 请求前完整性、后台回读，以及 Slate 编辑器、图片数量、解码、Caption 和草稿状态健康闸。本地测试不替代真实部署证据。

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
article_binding_local_tests: 52_passed
article_draft_backend_readback: verified_remote_2026_07_27
article_editor_render_after_reload: verified_remote_2026_07_27
article_editor_caption_visible: verified_remote_2026_07_27
article_editor_dom_alt: missing_observed_3_of_3_2026_07_27
published_theme_alt_for_current_A_B_A_run: not_run_not_authorized
media_record_delete_direct: verified_remote_2026_07_27
media_editor_fields_title_alt_caption: observed_2026_07_27
direct_metadata_update_contract: discovered_and_one_authorized_remote_write_verified_2026_07_27
ai_metadata_to_private_index: implemented_local_tested
ai_metadata_to_allincms_title_alt_caption: historical_one_sample_verified__current_2026_07_30_caption_null_warn
physical_asset_cleanup_after_delete: out_of_scope
publication_status: WARN_CURRENT_DEPLOYMENT_ARTICLE_PUBLISH_COMPLETE__MEDIA_CAPTION_AND_THEME_PRESENTATION_GAPS__BLOCK_CROSS_DEPLOYMENT
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
| `article-image-binding.test.mjs` | 52 项不触碰远端的文章图片测试 |
| `package.json` | 测试命令和 PNG / JPG 规范化依赖声明 |
| `observed-contract.redacted.json` | 去敏后的观察型内部接口形状和漂移合同 |
| `direct-serial-10-verification.redacted.md` | 10 张串行真实验证的去敏证据与边界 |
| `direct-delete-verification.redacted.md` | 零点击媒体记录删除的历史去敏证据；物理资产状态已退出当前完成口径 |
| `verify-media.mjs` | 无登录态公开 URL 验证器 |
| `fixtures/` | 只放无敏感信息的虚拟测试图片 |

## 内容变更授权入口

文章、分类、标签及正文图片草稿 mutation 只接受结构化 `authorizationContext`，不接受 `true`/`false`。使用 `mutation-authorization.mjs` 创建与准确 `site_key`、operation 和目标摘要绑定的上下文；actor 为 `human-asserted`、身份状态为 `not_verified`，有效期最长 30 分钟。adapter 会在每次远程请求前重验；任一字段、目标或时间不匹配即停止。该上下文不替代 publish/delete 的独立人工批准，也不证明正式发布资格。
