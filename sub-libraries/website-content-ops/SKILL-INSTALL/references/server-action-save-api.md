---
doc_id: allincms-bulk-server-action-save-api
title: AllinCMS Server Action 保存契约
description: LAICMS / AllinCMS 产品/文章/分类/发布/删除的 Next.js Server Action 请求形状、字段契约、发布语义与重试规则(中性模板,不含任何站点专属值)
layer: ops
status: "Working"
created: 2026-07-03
updated: 2026-07-30
page_type: reference
sources: ["self"]
confidence: medium
last_updated: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
related: ["../README.md"]
owner: "AI"
type: "doc"
---

# Server Action Save API 契约(中性模板)

本文件把 AllinCMS 后台"保存/发布/删除"背后的 Next.js Server Action 请求形状固化成**可复用的契约模板**,让后续 AI 优先走 JSON 批量而不是逐条点 UI。

> 安全边界:本文件**只留结构与字段契约**。真实 `siteId` / `next-action` ID / `deploymentId` / 业务文案 / CDN 私有路径**一律不写进 skill**,只留在每轮运行文件夹的本地 `*-save-contract.json` + `site-registry.json` 里。占位用 `{siteId}`、`{categoryId}`、`{productId}`、`{postId}`、`{nextActionId}`、`{cdnUrl}`。
>
> **权威关系（必须先读）**：这是中性/历史模板，不是任何宿主母库的当前文章合同。当前文章、分类、标签、创建、更新、发布、取消发布、删除、恢复和串行批量行为，以 `<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/` 下的 Adapter、机器合同、测试和当前部署证据为准；冲突时不得按本文件旧假设回放。已登录后台可作为执行前提，但不能替代当前 Action/部署捕获和回读验收；本文件不把“敏感”作为额外阻断理由，也不允许把 `postCreate`、远程失败恢复、跨部署或任意大批量能力在缺证据时标成已验证。

## 1. 请求形状(所有变更同构)

AllinCMS 后台是 Next.js App Router + Server Actions。每个"保存/创建/发布/删除"都是对**当前内容页 URL**发一个 POST:

```
POST https://workspace.laicms.com/<当前后台路由>
Headers:
  next-action: {nextActionId}          # 每个动作一个 ID,随部署变
  content-type: text/plain;charset=UTF-8
Body: JSON 数组 = Server Action 的入参列表,例如 [ { ...payload } ]
```

关键点:

- **body 是一个 JSON 数组**(Server Action 的参数列表),不是裸对象。单参动作就是 `[payload]`。
- `next-action` 头决定调用哪个动作;**同一个 ID 在一次部署内稳定,换部署就变**(见 §5)。响应头 `Content-Type: text/x-component`。
- 响应是 Next.js Server Action 的 **flight 流**:多行 `N:` 引用(`0:` / `1:` / `2:` …,不只 `0:`),需按引用树解析才能取回返回实体。**不要假设新建实体的 `_id` 在固定行**;稳妥做法是回放后按 `slug`/`siteId` 重新查该实体确认,而不是硬解 flight 首行。

## 2. 动作清单(按实体×动作,ID 本地记)

| 实体 | 动作 | 语义 | 本地记录键 |
|---|---|---|---|
| 分类 | create | 建分类,返回 `{categoryId}` | `actions.categoryCreate` |
| 产品 | create | 建产品(草稿),返回 `{productId}` | `actions.productCreate` |
| 产品 | update | 存草稿(`mode:'update'`) | `actions.productUpdate` |
| 产品 | publish | 发布上线(`mode:'publish'`,**同 update 的 action ID**) | 同 `productUpdate` |
| 产品 | delete | 删产品 | `deleteActions.product_delete` |
| 文章 | create | 建文章(草稿) | `postActions.create` |
| 文章 | update | 存草稿(`mode:'update'`) | `postActions.update`(实测与 publish 复用同一 ID) |
| 文章 | publish | 发布上线(`mode:'publish'` + 全字段,复用 update 的 ID) | 同 `postActions.update` |

> 记录时按此表把每个 `{nextActionId}` 落进本轮 `*-save-contract.json` 的 `actions` / `postActions` / `deleteActions`,并写清各字段。
> **历史模板说明**：本文件只保留中性/历史请求模板。当前母库文章分类、标签和文章生命周期以知识库 Adapter `sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.mjs`、`article-operations-contract.json` 和对应实测证据为准；该 Adapter 已覆盖 taxonomy CRUD、文章 update/publish/unpublish/delete 与状态不明恢复。`postCreate` 虽有受控实现，但除非当前部署重新捕获完整 create 合同并用精确新 `postId` 回读确认，否则仍是 BLOCK。若冲突，不得按本文件旧假设 replay。

## 3. 字段契约

### 产品 payload

```json
{
  "name": "<string>",
  "slug": "<kebab>",
  "description": "<string, 列表/SEO 短描述>",
  "order": 0,
  "media": { "name": "<file.png>", "alt": null, "type": "image", "source": "url", "url": "{cdnUrl}" },
  "mediaList": [],
  "categories": ["{categoryId}"],
  "tags": [],
  "specifications": [ { "key": "<name>", "value": "<value>" } ],
  "content": [ { "type": "p", "children": [ { "text": "<段落>" } ], "id": "<rand>" } ],
  "siteId": "{siteId}",
  "productId": "{productId}",
  "mode": "update"
}
```

### 文章 payload

- `title` / `excerpt` / `coverImage`(同 `media` 的对象形状)/ `content`(Slate 节点数组)/ `categories` / `tags` / `postId` / `mode`。
- `excerpt` 实测遇到过 maxlength 约束(约 200 字),但**该数字未逐部署确认**——当作"保持简短、可能被截"处理,别把 200 写死成契约。

> **字段命名以本表为准(实测)**:产品用 `name` + `specifications`,文章用 `title` + `excerpt`。若 `request-capture.md` 里旧的假设 payload 用了 `title`/`specs` 之类,以本文实测为权威,不要按旧假设 replay(会挂字段)。

### 删除 payload

- `POST /products`(或对应实体路由)body `[{ "id": "{productId}", "siteId": "{siteId}" }]`。

### 字段硬规则

- **`content` 必须是 Slate 节点数组**:`[{type:'p', children:[{text:'...'}], id:'<rand>'}]`。不是 markdown、不是 HTML。
- `categories` / `tags` = **ID 字符串数组**(不是名字)。分类要先建、拿到 `{categoryId}` 再引用(taxonomy-first)。
- `specifications` = `[{key,value}]` 数组。
- `media` / `coverImage` = 对象 `{name,alt,type:'image',source:'url',url}`;`source:'url'` + CDN 直链即可直接设封面,无需走上传弹窗。本地图先传公共 CDN 再引用(见 `field-contract.md` 的 coverImage 契约)。
- `siteId` 是**内部 ID**,`≠` URL 里的 `siteKey`;两者都要本地记(见 `site-registry.json`)。

## 4. 发布语义(易错)

- **发布 = 用 update 的同一个 action ID**,body 里把 `mode` 从 `'update'` 换成 `'publish'`,且**带全字段**(不是只发 `{productId}`)。
- 在 update body 里塞 `isDraft:false` **无效**;必须走 `mode:'publish'` 路径。
- `mode:'update'` = 存草稿(`isDraft` 保持),`mode:'publish'` = 上线。

## 5. next-action ID 随部署漂移(必须每轮重抓)

- `next-action` ID 由构建产物决定,**换一次部署就变**。不能把上一轮的 ID 直接复用。
- 每次批量前:在 UI 里真实触发一次该动作的保存(建一个探针,或改一个已存在实体),用注入的 `window.fetch` 拦截器抓下**当前** `next-action` 头 + router-tree,写进本轮 contract,再开始批量。
- 捕获方法见 `request-capture.md`(注入 `window.__cap` 拦截器);判"该不该走 JSON"见 `interface-inventory.md` 与 `official-docs-alignment.md`。

## 6. 重试(后端间歇失败)

> 本节是历史/中性模板；当前母库文章 Adapter 的恢复合同优先。

- 后端偶发 **503** + MongoDB **"transaction number does not match"** 事务冲突。
- 当前 Adapter 不允许因为 `readback === null` 就自动重发已有文章或 taxonomy mutation；只有创建动作在显式 `retryOnExactAbsence: true` 且 `confirmExactAbsence()` 新鲜确认“精确不存在”时，才允许一次受控重试。
- 对策:**串行**提交 + 指数退避重试(本地 `window.__post2` 助手:遇 503/事务冲突先只读对账,不并发)。请求可能已成功但状态不明时停止人工介入，不能把旧模板的“遇错即重试”当成当前合同。

## 7. 主题(Theme)编辑:两个作用域,分清"能不能 JSON"

主题相关有**两类不同的保存**,别混为一谈(这是本 skill 里最容易自相矛盾的点):

**A. 主题页设计保存(design save)= 是 Server Action,可 JSON 回放。** `request-capture.md` 有 **2026-06-29 CDP 实测**记录:保存一页设计就是
```
POST /{siteKey}/themes/{themeId}/{pageId}/design
next-action: {nextActionId}
body: [ { siteId, themeId, pageId, intent:"save",
          pageDocument:{ root:"page-root", elements:{ "<blockId>":{ type:"<blockType>", props:{...} } } } } ]
```
整页的 `pageDocument`(所有块的 type + props,含文案/`media`/URL)都在这一个 body 里。**改整页 = 抓一次 design save → 在 `pageDocument` 里改块 props → 回放** → 主题也能 JSON 批量,不必逐块点。

**B. 为什么本轮没走 A、退回了 UI 半自动:捕获方式用错了。** 主题 design save 走的 `fetch` 引用在 bundle 初始化时被 Next 捕获,**晚注入的 `window.fetch` 拦截器抓不到它**(内容页 save 能抓、主题 save 抓不到);Jotai 默认 store(`__JOTAI_DEFAULT_STORE__`)也为空(设计器用作用域 store)。所以本轮改主题走了下面的 React-setter 半自动 UI。

**结论(消除矛盾)**:主题 design save **不是不可能 JSON**,而是**必须换捕获方式**——用 **CDP Network 监听**(06-29 就是这么抓到的)、或在 bundle 初始化前 hook `fetch`、或从作用域 Jotai 读 doc atom;抓到 `pageDocument` 契约后即可整页回放。捕获前用不了 JSON 时,**下面的 React-setter + Save/Publish 是可靠降级**(逐块改,已实测跑通全站)。切勿在 skill 任何地方写"主题不能 JSON"——正确说法是"主题 design save 可 JSON,但要 CDP 抓不能晚注入 fetch 抓"。

> 另有**主题页结构操作**(create theme / create page / enable-activate / bind route)——见 `create-flows.md`、`request-capture.md`,它们各是独立 action,已分别抓到过,和上面的 design save 是不同端点、不同 payload,别用一个当另一个的证据。

### 7.5 React-setter 半自动法(未抓到 design save 时的降级)

**切页与选块**:JS 点 `[aria-label="Page context"]` 开页面下拉 → 点目标页名(Home/Products/Product/About Us/Contact Us/Posts/Post 等,**SPA 软导航,不 hard reload**;navigate/hard-reload 会冲掉 Clerk 登录态)。选块:先确保左侧 **Layers 标签激活**(否则点到 Blocks 调色板,选不中),再点 Layers 里的块行,或直接点画布上的图/文选中。切页/切块后右侧 Inspector 可能跳到 Theme 标签,**写值前必须先点回 Props 标签**。块名以 Layers 的 `Hide <name>` aria-label 为准(详情页相关块叫 `Post Related`/`Product Related`,不是 Recommended Articles)。

**批量写文案**:用 `HTMLInputElement`/`HTMLTextAreaElement` 的 prototype `value` setter + 派发 `input`+`change` 事件,按 input/textarea 的 `name` 批量写。一次 JS 填整块所有字段(sectionLabel/headline/supportingCopy/items.N.xxx),再点 Save → 等 → Publish(一般无二次确认框)。

**换图(媒体选择器 URL 标签)**:Inspector 无图片 URL 输入框。点块 Media 区「替换图片」按钮 → 弹「选择图片」模态(媒体库/上传/URL 三标签,媒体库常空)→ 点 **URL** 标签 → React-set 那个占位 `example.com/image.jpg` 的 input 为公共 CDN 直链 → **轮询等「确认」enable**(预览加载完才可点,最多 ~6s)→ 点「确认」。图必须公共 http(s) 直链(同 §3 media 契约)。

### 7.6 把主题也 JSON 化(下一轮的正解)

按 §7 结论,主题 design save 是可回放的 Server Action,只是要**换捕获方式**。三条路任选:
1. **CDP Network 监听**(推荐,06-29 已验证):在设计器里真存一次 → 从 CDP 拿到 `POST .../design` 的 `next-action` + `pageDocument` body → 改块 props → 回放整页。
2. bundle 初始化前 hook `window.fetch`(在页面脚本执行前注入)。
3. 从作用域 Jotai store 读 doc atom(需先定位设计器用的那个 store 实例,非 `__JOTAI_DEFAULT_STORE__`)。
抓到后即可像内容一样"改 pageDocument → 回放",彻底摆脱逐块 UI。**在此之前用 7.5 半自动法**。

**2026-07-04 live 复核(确认端点 + 定位工具卡点)**:在设计器里真存一次,`read_network_requests` 确认 **`POST /{siteKey}/themes/{themeId}/{pageId}/design` 会 live 触发**(200/503,与 §7 契约一致,且 per-page)。但当前 Claude-in-Chrome 的 `read_network_requests` **只回 url/method/status,不含 `next-action` 头,也不含 postData body**;晚注入 `window.fetch` 拦截器仍抓不到(bundle-init 捕获)。=> **整页回放缺的只有 `next-action` id 那一项**:body(`pageDocument`)本身可从页面块状态构造,并已有 `validate_theme_page_document.py` 门禁校验;唯独 action id 需要一个**能返回 request postData/headers 的 CDP 会话**(06-29 那次就是),不是当前 MCP 桥能给的。结论:主题 JSON 回放**工具就绪、契约就绪、body 可构造+可校验,只差一个能读 postData 的 CDP 抓取**——这是外部工具限制,不是 skill 逻辑缺口。

## 8. 与其它 reference 的关系

- 判"要不要 JSON":`interface-inventory.md` + `official-docs-alignment.md`(replay 的 action 必须属于当前官方步骤,不能只是抓到的邻近 API)。
- 抓请求:`request-capture.md`。变更授权/记录:`mutation-safety.md`。字段风险:`field-contract.md`。批量验收:`batch-verification.md`。
