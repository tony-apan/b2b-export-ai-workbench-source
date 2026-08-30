---
source_doc_id: "ID-0005"
title: "Source-Driven CMS Create and Update SOP"
description: "把用户提供的文档、网站、表格、图片和 brief 转成可追溯 desired state，经动态 CMS 能力发现、精确 diff、授权、串行接口执行和真实回读后，新建或更新网站、文章与产品。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-08-12"
last_updated: "2026-08-12"
sources: ["../README.md", "../00_intake/index.md", "../20_knowledge/index.md", "index.md"]
related: ["index.md", "../TEMPLATES/content-operation-plan.md", "source-driven-cms-operation-sop.runtime.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "用户提供资料并要求新建或更新网站、文章、产品、分类、标签或媒体，且需要通过 CMS 接口执行时。"
keywords: ["source driven", "CMS operation plan", "create update upsert", "desired state", "API first", "reconciliation"]
generated_from: "../../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md"
generated_source_sha256: "441ca83133b0ce3e0544945074db8894de892b1583bf0b0208d5a8944d491929"
generated_by: "scripts/sync-workspace-template.mjs"
---
<!-- Generated runtime projection from PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md; canonical edits belong in the core package. -->
# 资料驱动的 CMS 新建与更新 SOP

## 1. 目标和边界

本 SOP 的核心不是“把一份固定 payload 发给 AllinCMS”，而是把**用户本次给出的资料和目标**转成可审查、可追溯、可重复执行的站点变更：

```text
用户资料
→ 宿主格式能力路由与来源快照
→ claim ledger 与平台无关 desired state
→ 当前 CMS 能力和现状快照
→ 精确 diff 和 digest-bound plan
→ 严格串行接口执行与歧义对账
→ 后台 / 编辑器 / 前台验收
→ 私有运行区写回
```

它适用于 `site`、`article`、`product`、`category`、`tag`、`media` 和 `theme_page`。但“对象在合同里出现”不等于当前 CMS Adapter 已支持：每次运行都必须读取 capability snapshot；`exploration_only` 或 `unsupported` 不得伪装成正式发布能力。

## 2. 不允许写死的内容

以下值必须来自用户资料、当前客户运行区、CMS 实时只读发现或本次明确决策，不能从示例站复制：

- 公司名、品牌、域名、站点名、语言、时区、市场、联系人和 CTA；
- 产品、型号、规格、价格、MOQ、交期、认证、案例、指标和效果；
- 分类、标签、slug、SEO title、description、正文、图片、alt 和内链；
- `user_id`、`site_id`、`site_key`、内容 ID、媒体 ID、组件 ID、部署 fingerprint；
- CMS 字段、枚举、路由树、Server Action ID、deployment/build ID 和内部接口参数。

动态发现值只可存在于内存或客户私有运行证据。Cookie、Authorization、session、token、浏览器 profile 和完整请求头不得进入 operation plan、公开子库或 Git。

## 3. 资料优先级与事实状态

### 3.1 先登记再提取

1. 先运行 `node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>` 生成机器绑定；原文件原样复制或快照到 `customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/` 私有 scope；
2. 为每个 PDF、DOCX、表格、网页、图片、聊天或 brief 分配 `source_id`；
3. 记录原始字节 SHA-256、来源位置、所有权、日期、授权、敏感性和 publication clearance；
4. 提取文本、表格、图片和 URL 时保存页码、sheet、单元格、段落或 DOM selector 等定位指针；
5. 不把 OCR、摘要或 AI 重写当成新的第一手事实源。

### 3.2 资料摄取是宿主能力路由，不是写死解析器

本子库定义统一的来源和 claim 合同，但不复制 PDF、Word、表格、浏览器或图像工具的实现。运行时按资料类型调用宿主已有能力：

| 输入 | 首选宿主能力 | 必须保留的定位 |
|---|---|---|
| PDF | PDF 读取/OCR runtime | 页码、表格区域、图片区域 |
| DOCX | documents runtime | 标题层级、段落、表格/单元格 |
| XLSX/CSV | spreadsheets runtime | sheet、行列、单元格范围 |
| website | 浏览器或只读 HTTP/API | URL、抓取时间、DOM selector/JSON path |
| image | 视觉读取/OCR | 文件 digest、像素区域/对象区域 |
| brief/chat | 原始文本快照 | 消息或段落定位 |

摄取结果写入同一 task root 的 `source-extraction.json`；schema `1.1` 必须携带和三元身份一致的 `runtime_scope`，`source_location` 只能指向该 task root 内的规范化相对 POSIX 路径。绝对路径、URL、反斜线、`..`、query/fragment、percent-encoded path bytes、伪 `private-runtime/` 前缀或另一客户/任务路径全部 BLOCK。artifact 至少包含 `source_id`、owner/rights、method-use 与 publication clearance、source date/review-after、客户 scope、原始字节/快照 digest、提取器及版本、`captured_at`、精确 locator、提取片段 digest 和提取警告。Source Register 仍是人可读入口，但机器计划不能只靠另一个 Markdown 表的声明；这些来源边界必须进入被校验的 JSON。AI 从中生成的是 **claim candidate**，不是自动确认事实；OCR 低置信度、表格合并、网页动态内容、图片文字和跨来源冲突必须保留 warning，不能静默“修正”。如果宿主缺少对应能力，就把该来源标为未提取并 BLOCK 依赖它的字段，不得用通用默认值补齐。

### 3.3 事实只允许五种状态

- `confirmed`：来源直接支持，且仍在适用期；
- `inferred`：从来源推导，必须保留推导说明，不能冒充确认事实；
- `missing`：资料没有提供；
- `conflicting`：来源之间冲突；
- `expired`：曾有来源，但超出适用期或已被更新。

`confirmed` 和 `inferred` 必须同时有 `source_refs`、精确 `evidence_refs`，且 evidence 必须把 `source_digest + extraction_id + unit_id + locator + extraction_digest` 绑定到 source snapshot 中声明的已校验 Source Extraction unit。只写一个相似 locator 或复制 digest 不能形成证据链。字段还必须通过 `claim_refs` 引用 claim；直接复制用 `derivation.mode=direct`，规范化或多条事实组合用 `normalized/composed` 并写明推导。`missing`、`conflicting`、`expired` 可留在缺口账本，但不得进入 mutation。认证、性能、规格、MOQ、价格、交期、客户案例、联系方式等高风险事实默认只接受 `confirmed`；不能用“行业惯例”“模板默认值”或搜索片段补齐。


### 3.4 更新现有内容时，当前 CMS 也必须成为来源

更新不是只读用户文件后覆盖 CMS。应先把目标站点中**当前记录、taxonomy、媒体关系、SEO 字段和编辑器内容**做只读快照，作为 `source_kind=cms_snapshot` 的私有 Source Extraction：绑定精确站点/record ID、读取时间、deployment fingerprint、字段 JSON path/DOM locator 与 snapshot digest。然后按以下优先级解冲突：

1. 用户当前明确指令；
2. 用户提供且仍有效、权利与用途已放行的资料；
3. 当前 CMS 中用户未要求更改的现有值；
4. 明确标注为 `inferred` 的编辑推导。

因此“用户没提及”必须解释为保留当前值，而不是使用空字符串、模板默认值或历史 fixture；用户资料与当前 CMS 冲突时进入 `conflicting`，除非用户已明确指定覆盖方向。更新 diff 只允许包含本次 desired state 明确消费的字段，不能顺便规范化全记录。

## 4. 从资料生成 desired state，而不是直接写 CMS

先建立公司、产品、ICP、买家语言和内容目标，再生成平台无关的 desired state。每个对象至少包含：

```json
{
  "entity_ref": "article:buyer-guide",
  "entity_type": "article",
  "intent": "upsert",
  "identity": {
    "id": null,
    "natural_key": {
      "site_key": "resolved-at-runtime",
      "slug": "buyer-guide"
    },
    "match_strategy": "exact_natural_key"
  },
  "fields": {
    "title": {
      "value": "Example title",
      "fact_status": "confirmed",
      "source_refs": ["SRC-001"],
      "claim_refs": ["CLAIM-ARTICLE-TITLE"],
      "derivation": {"mode": "direct", "notes": ""},
      "clear_existing": false
    }
  }
}
```

规则：

- `upsert` 只表达业务意图，执行前必须经当前状态 snapshot 解析为 `create`、`update` 或 `noop`；不能把未解析的 upsert 直接发给 CMS。
- 不能只按标题、产品名或分类名模糊匹配。更新必须绑定站点内精确 ID，或 `site_key + slug/external_key` 等唯一 natural key。
- 用户只要求更新文章时，不得顺手重建站点、覆盖主题、改产品或清理媒体。
- 用户资料缺失的字段默认保持当前值；“空白”不等于“允许清空”。清空必须是显式 desired state，并单独进入 diff。
- 已有页面的人工编辑、未知字段和平台扩展字段默认保留，不能由模板默认值覆盖。

## 5. 新建网站必须两阶段，禁止虚构未来 site key

创建网站和向新网站填充内容是两个独立的授权与证据 scope：

```text
Plan A: site_bootstrap（account scope）
→ 只读确认登录用户、完整网站列表、可建站权限和当前 create-site capability
→ desired_state 只包含 1 个 site:create
→ site_key/site_id 必须为 null，只允许 source-backed site_key_candidate
→ account-scoped digest + authorization
→ 严格执行一次 create-site
→ 回读真实 site_id/site_key/account owner，并写入私有 bootstrap evidence

Plan B: site_operation（site scope）
→ 引用 Plan A digest + bootstrap readback evidence
→ 使用真实 site_key 重新发现 capability/current state
→ 新摘要与新授权
→ 分类、标签、媒体、文章、产品、主题页和站点配置严格串行执行
```

禁止把 `<planned-site>`、测试站 key 或候选 slug 冒充真实 `site_key`；禁止在 Plan A 中混入分类、标签、媒体、文章或产品。若 CMS 返回的新站身份不唯一、回读失败或 deployment fingerprint 漂移，Plan B 不得生成。更新现有网站直接走 `site_operation`，但仍需精确站点选择和 current-state fingerprint。

## 6. 每次运行动态发现 CMS

在 mutation 前生成 `capability_snapshot`，而不是相信历史文档仍然有效：

1. 用当前已登录 session 做只读认证检查；未登录才打开宿主内置浏览器的登录页，引导用户登录，然后重新检查；
2. 只读取得当前 `user_id`、完整网站列表、创建站点能力和目标站点精确身份；
3. 读取目标内容类型、字段、枚举、生命周期、taxonomy、媒体和主题页面合同；
4. 动态捕获本部署所需的 Action ID、router tree、build/deployment ID；不得提交到母库或写入公开计划；
5. 为每项能力记录成熟度：
   - `live_verified_current_deployment`
   - `local_tested`
   - `exploration_only`
   - `unsupported`
6. 版本 fingerprint 漂移、字段歧义或多个候选匹配时，切换 `audit` 并停止 mutation。

能力放行原则：

- `publish` 必须是当前部署 `live_verified_current_deployment`；
- `local_tested` 只能支持其明确覆盖的草稿或受限 mutation，不得外推为当前部署正式发布；
- `exploration_only` 只允许只读探索或获批的小样草稿验证，不能正式发布；
- `unsupported` 直接 BLOCK。

当前 AllinCMS 产品能力仍以 Adapter 的实时 capability snapshot 为准；历史产品文档或模拟测试不能替代当前部署的 create → readback → update → publish → frontend 验证。

## 7. current state、diff 与并发保护

对每个目标对象做站点内精确回读并保存 canonical fingerprint：

- `create`：确认唯一 key 当前不存在；若存在则停止，不自动认领；
- `update`：保存 `expected_current_fingerprint`，mutation 前再次回读；不同则说明有人或系统已修改，停止并重新规划；
- `noop`：字段规范化后无差异，不发送远程请求；但仍须完成 authoritative same-site readback，证明当前对象无需变更后才能形成成功 evidence；
- `explore`：只允许计划和 capability 明确批准的只读请求；完成后须 authoritative same-site readback，失败不得进入 mutation reconciliation；
- `delete`、清理、跨站复制不属于默认能力，必须独立计划和授权。

Diff 必须逐字段说明 `before`、`after`、来源、是否清空、依赖和验证方法。operation plan 中不能隐藏 UI 动作、隐式 fallback 或计划外副作用。

## 8. operation plan、摘要与授权

使用 [Content Operation Plan 模板](../TEMPLATES/content-operation-plan.md) 生成 JSON，并运行：

```bash
node scripts/validate-content-operation-plan.mjs path/to/content-operation-plan.json
```

计划至少绑定：

- `client_id`、`company_id`、`task_id` 以及机器生成的 `runtime_scope`；所有 source/artifact/capability/evidence/writeback ref 必须留在同一 task root；
- `plan_phase`；Plan A 绑定 account target，Plan B 绑定回读后的精确 `site_key` 和 CMS adapter；
- source snapshot、带精确 locator/digest 的 claim ledger、带有效期的 capability snapshot；
- desired state、current-state fingerprint、diff；
- 有序 operations、依赖、对账和验收；
- writeback targets；
- 对 canonical plan projection 计算的 SHA-256；摘要排除 `plan_digest`、`plan_sha256` 和授权 actor/时间，只绑定不可变业务计划与精确站点/operation scope，避免自引用循环。

用户授权必须绑定**同一计划摘要、同一 target scope/key 和同一 operation ID 列表**。授权必须在**同一文件写入步骤**连同 `archived_at`(=approved_at) 落盘（冻结即归档）；验证器对 approved 计划强制归档字段，缺档 BLOCK。Plan A 绑定账号，Plan B 绑定真实站点；二者不能共用摘要或授权。计划、资料字节、目标站点、操作顺序、字段或图片发生变化后，旧授权失效。计划结构 PASS 只证明本地合同；`authorization_scope.status=pending` 时不得执行。

## 9. 接口优先与严格串行执行

默认执行顺序按依赖解析，例如：

```text
认证与网站只读检查
→ Plan A 创建站点并回读真实身份（仅新站）
→ Plan B 重新发现并锁定真实站点
→ 分类
→ 标签
→ 媒体（逐张）
→ 文章或产品草稿
→ 编辑器重开回读
→ 单独发布
→ 前台验收
```

要求：

- 默认 API / 当前部署 Server Action；UI 只用于登录、动态合同探索或人工验收，不是静默降级通道；
- mutation 严格串行；后一个操作只在前一个操作完成且 readback 确定后开始；
- 每个 operation 使用确定性 idempotency / identity 规则；
- 网络超时发生在请求可能已发送之后时，结果标为 `ambiguous`，只读对账，禁止盲目重发；
- 每个 operation 显式声明 `publication_effect`：`private_draft`、`public_immediate`、`publish_transition` 或 `none`；任何公开 mutation 使用的来源必须为 `approved/not-applicable`；
- 发布是独立 operation，不能因为草稿保存成功自动发布；
- 不跨站 fallback，不自动创建计划外分类、标签、媒体或站点。

## 10. 新建与更新的验收矩阵

| 对象 | 后台 / API 回读 | 编辑器重开 | 前台验收 |
|---|---|---|---|
| site | 精确 site ID/key、设置和状态 | 适用时 | 首页、导航、语言、移动端 |
| category/tag | ID、slug、站点归属 | 选择器仍绑定 | 主题支持时检查展示/链接 |
| media | media ID、URL、metadata、哈希映射 | 资源选择器可见 | URL 200、content-type、尺寸/alt |
| article | 全字段、taxonomy、媒体、生命周期 | 必须重开并持久化 | URL、H1/层级、图片、CTA、内链、DOM |
| product | 全字段、taxonomy、媒体、生命周期 | 必须重开并持久化 | 产品 URL、规格、图片、CTA、结构化数据 |
| theme_page | 页面配置、组件和发布状态 | 适用时 | desktop/mobile DOM 与交互 |

`fast` 用于合同未漂移、能力已在当前部署实测、单对象低风险变更；`audit` 用于首次接入、字段/版本漂移、产品、主题、批量或高风险事实。两种模式都必须做接口回读；`fast` 不能省略歧义对账和前台验收。

## 11. 写回和可移植 Skill 边界

客户事实、原资料、凭据外的 session 证据、operation plan、请求结果和验收截图只进入客户私有运行区。母库只回写：

- 去敏后的稳定字段合同；
- capability 成熟度和适用部署范围；
- 可复现的失败卡、对账规则、测试 fixture 与验证器；
- 不包含客户数据和动态 Action ID 的通用 SOP。

可安装的 `allincms-bulk-content-upload` 只是发现与路由薄入口：定位 `<SUB_LIBRARY_ROOT>`，读取本 SOP、Schema 和 canonical AllinCMS Adapter。它不得复制接口实现或将某次部署、站点和产品字段固化为第二真源。

## 12. 对抗停止条件

出现任一情况立即 BLOCK：

- 未锁定 `client_id/company_id/task_id`；site_operation 未锁定真实 `site_key`，或 site_bootstrap 虚构未来 `site_key`；
- 来源缺失、claim 没有精确 locator/digest、字段没有 `claim_refs/derivation`、事实冲突或过期，或 publication clearance 不满足公开动作；
- 仅凭名称模糊匹配更新对象；
- update 缺 expected-current fingerprint，或 fingerprint 已漂移；
- 计划含 Cookie、token、Action ID、测试站 ID 或跨站 fallback；
- 远程 mutation 的 capability 不是 `live_verified_current_deployment`，或 capability snapshot 已过期；
- 操作依赖不是单链，或运行中并行 mutation；
- 请求结果歧义却准备重发；
- 授权摘要、target scope/key、操作列表或有效期不匹配；
- 只有 API 200/toast，没有后台回读、编辑器重开或前台验收；
- 把本地结构 PASS 宣称为真实发布、SEO、询盘或转化 PASS。
