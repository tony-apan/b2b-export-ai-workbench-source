---
title: "Website Content Operations AI Skill Adapter"
description: "把建站内容运营子库的渐进读取、审批、单样本、验证和写回流程适配给可读取本地文件的 AI agent。"
type: "skill"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-01"
sources: ["README.md", "AGENTS.md", "START-HERE.md", "PLAYBOOK.md", "QA-CHECKLIST.md"]
related: ["README.md", "AGENTS.md", "START-HERE.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "ADAPTERS/cms/allincms/README.md", "QA-CHECKLIST.md", "VERSION.md"]
audience: ["Claude", "Codex", "可读取本地文件的 AI agent"]
state_source: "MANIFEST.md"
state_projection: ["release_status", "preview_publication_status", "skill_status"]
release_status: "BLOCK"
preview_publication_status: "BLOCK"
skill_status: "preview-adapter-not-installable"
visibility: "public"
redaction_status: "safe-to-publish"
---
# Website Content Operations AI Skill

> **状态分离：历史 artifact `v0.3.2-preview.1` 已发布为 Public Preview；当前未发布源码候选为 `BLOCK` / 非 Stable。** 历史发布事实不能继承给当前候选；新增研究来源的 publication clearance 尚未完成。本文件仍只是子库内的预览级 AI 适配器，不是一键安装或跨平台稳定 Skill。实时状态以 `MANIFEST.md` 为准。

## 什么时候使用

当用户希望 AI 帮助完成以下闭环时使用：

- 从网站、PDF、DOCX、表格、图片、brief 或客户语言建立有来源的公司、产品和 ICP 知识；
- 根据用户资料新建或更新网站、文章、产品、分类、标签、媒体和主题页面；
- 生成一篇内容、一张图片或一个 CMS 草稿；
- 调查陌生图床、CMS 或相邻营销工具；
- 复核真实结果，并把事实、失败和通用改进分层写回。

不要把本 Skill 用于：

- 没有来源的事实编造；
- 绕过账号权限或导出凭据；
- 未经批准的发布、删除、批量覆盖或社媒账号动作；
- 把当前 AllinCMS 部署证据外推成官方 API 或跨部署保证。

## 渐进读取

第一次只读：

1. [START-HERE.md](START-HERE.md)；
2. 用户明确提供的当前运行区入口；
3. 当前步骤需要的一个模板或 adapter。

按需读取：

- 底层对象和迁移： [MENTAL-MODEL.md](MENTAL-MODEL.md)；
- 完整执行： [PLAYBOOK.md](PLAYBOOK.md)；
- 资料驱动的新建/更新 CMS 对象：先读 [Source-Driven CMS Create and Update SOP](PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md)，再用 [Content Operation Plan](TEMPLATES/content-operation-plan.md) 和机器验证器冻结本次 desired state、精确 diff 与授权摘要；
- 真实 AllinCMS 操作/可分享能力对抗审查：先读 [Live AllinCMS Operation Adversarial Review](PLAYBOOKS/id-0006-live-allincms-adversarial-review.md)，确认 capability gate、Plan A/B、证据轴和双审门槛；未经双审不得宣称可分享或 production-ready；
- 正式 B2B SEO 文章： [PLAYBOOKS/README.md](PLAYBOOKS/README.md)；新写走 [B2B SEO Article Standard](PLAYBOOKS/id-0001-b2b-seo-article-standard.md)，优化现有文章走 [B2B Article Optimization SOP](PLAYBOOKS/id-0003-b2b-article-optimization-sop.md)；
- 工具调查： [TOOLS-INDEX.md](TOOLS-INDEX.md) 和对应 [ADAPTERS/README.md](ADAPTERS/README.md)；
- 验收： [QA-CHECKLIST.md](QA-CHECKLIST.md)；
- 写回： [WRITEBACK.md](WRITEBACK.md)。

禁止为了“保险”一次性读取整个子库。

## 默认执行协议

```text
检查来源和权限
→ 建立最小知识卡
→ 只做一个小样本
→ 获取后台 / 前台 / 文件回读证据
→ 记录失败、停止或回滚
→ 获批后再扩大范围
→ 分层写回
```

外部动作默认停在草稿或待批准状态。安装、发布、覆盖、删除、批量和全局修改都必须得到明确授权。用户提供资料时不得跳过来源登记直接套固定 payload：先生成 source snapshot、claim ledger、desired state 和 current-state diff；站点、语言、taxonomy、slug、字段、媒体、CTA、Action ID 与 deployment fingerprint 均须来自本次资料或运行时发现。`upsert` 必须在执行前解析成精确 `create/update/noop`，更新绑定 exact ID 或站点内唯一 natural key 与 expected-current fingerprint。

## 输入要求

开始前至少确认：

- 业务目标；
- 当前来源和来源状态；
- 目标工具、站点和权限边界；
- 用户希望得到的输出；
- 是否允许真实外部动作。

缺失事实必须标记为 `missing` 或 `待验证`，不能用推断填空。

## 输出要求

每一步返回：

- 使用了哪些来源；
- 修改或生成了哪些文件；
- 哪些是事实、推断和缺口；
- 是否需要人工批准；
- 如何验证真实结果；
- 失败或回滚记录写到哪里。

## 通用 CMS operation plan 门槛

用户给出 PDF、DOCX、表格、网站、图片、brief 或既有 CMS 内容并要求新建或更新时，先读 [ID-0005](PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md)，不得直接套历史 payload：

1. 锁定 `client_id/company_id/task_id`，登记原始 bytes/snapshot digest；
2. 按宿主格式能力生成 [Source Extraction](TEMPLATES/source-extraction.md)，保留精确 locator、extraction digest、提取器/version、置信度与 warning；它只是 private claim-candidate input；
3. 建 claim ledger 和 field-level `claim_refs/derivation`，blocked/missing/conflicting/expired claim 不得进入 mutation；
4. 动态发现当前登录用户、完整网站列表、CMS 字段/枚举、deployment fingerprint 与有时效的 capability；站点、语言、taxonomy、CTA、产品字段、组件、Action ID 和 build ID 均不得写死；
5. 生成平台无关 desired state、精确 current fingerprint、diff 和严格串行 [Content Operation Plan](TEMPLATES/content-operation-plan.md)；远程 mutation 只接受当前 deployment 的 `live_verified_current_deployment` capability；
6. 新建站拆为 Plan A `site_bootstrap`（account scope，exactly one `site:create`，未来 `site_key/site_id=null`）和 Plan B `site_operation`（引用 Plan A digest/readback，绑定真实 site）；两份计划不得混合或共用授权；
7. 每个 mutation 声明 `publication_effect`，公开写入只消费 `approved/not-applicable` 来源；接口优先、严格串行、歧义只读对账，完成后台回读、编辑器重开、前台验收和私有运行区写回。

本地 Schema/validator PASS 只证明合同结构，不证明登录、远程执行、发布、SEO、询盘或转化。

## 正式文章执行门槛

正式买家文章必须使用同一 `package_id` / `brief_id` 绑定 `Article Brief → Article Draft → Article Quality Review → Publish Record`。先通过内容一票否决，再检查前端 SEO 合同，最后才读取目标 CMS Adapter。`total_score >= 80`、API 成功或后台 toast 都不能覆盖 fabricated claims、缺搜索意图来源、缺工程 CTA、QA 页面误 index、前端 blocker、Adapter 不支持格式或编辑器未重开。最低机械校验使用 `node scripts/validate-article-package.mjs --brief ... --draft ... --review ... --publish ...`；Review 必须由不同 reviewer 使用 canonical fatal-check evidence matrix 逐项绑定证据。输出 `ARTICLE_PACKAGE_STRUCTURE_PASS` 只证明结构、引用路径、自洽和当前 AllinCMS 保守格式预检，事实判断、Reviewer 真人身份、授权、浏览器与发布证据仍为 `not_verified`。

## 当前 AllinCMS 路由

目标是 AllinCMS 时，先读 [AllinCMS AI 唯一入口](ADAPTERS/cms/allincms/AI-START-HERE.md)，并从其第 0 节直接执行：默认用宿主内置 Browser session 请求 `/sites?_rsc`，读取登录状态、`user.id`、完整网站列表和 `canCreate`；只有未登录才打开并前台展示 `/sign-in`，登录后重新 API 检查，再做精确选站、媒体页检查、接口优先和页面诊断回落。不要让用户先自行找页面，不要绕过当前 adapter 自行重抓或重写上传循环，也不要把 UI 当自动降级。历史 artifact 的 Public Preview 不放行当前未发布源码候选；当前路线仍受 `MANIFEST.md` 的 `BLOCK` 状态与独立 Stable qualification 边界约束。

### 上传前必须取得精确授权

对 direct、serial、batch、single 四个媒体上传入口，`authorizationContext` 是不可省略的必需输入，不是可选 callback。执行 agent 必须：

1. 向当前用户展示并确认精确 AllinCMS `site_key`、操作 `allincms.media.upload` 和精确有序文件列表；
2. 记录用户声明的 approval actor 与批准时间；
3. 使用 `createAllinCmsMediaUploadAuthorizationContext()` 对文件名、字节数和 SHA-256 形成 file-list digest；
4. 把返回对象显式传给对应上传入口；
5. 任何文件内容/顺序、site、operation、entrypoint 变化，任何 `approved_at > now`，或最长 30 分钟授权在 `now >= expires_at` 时过期后，停止并重新批准；最终路径为 symlink 时不得开始。

底层 `uploadAllinCmsMediaDirect()` 自身也会 fail closed，不能依赖 `beforeRequest`、UI 状态或上层“已经问过用户”的口头假设。direct/serial 必须沿用首次通过 digest 校验的源 Buffer；batch/single 必须使用安全 Buffer payload，不得在确认前把原始路径重新交给浏览器。`beforeRequest` 返回后或确认点击前必须重新校验完整授权、逐文件 digest 和当前时间。授权记录的 actor 是 `human-asserted` 声明，身份状态固定为 `not_verified`；本 Skill 不验证或证明批准者真人身份。当前冻结的文章/媒体四文件专项 qualification profile 为 158/158（媒体 45、正文图片 52、正文格式 13、文章生命周期/taxonomy 48）；完整源码工作树另含 Workspace 前置检查 21/21、串行 Controller 58/58 与 Interface Registry 11/11，当前 `npm test` 七文件全量为 248/248。正式 qualification profile 与完整开发回归必须分层报告，不能用 248 取代冻结的 158，也不能用 158 冒充完整套件；这些本地结果仍不证明真实 CMS、跨部署或发布资格。

## 适配范围

本 Skill 只定义业务流程和读取路由；工具按钮、接口、字段和当前部署证据留在 `ADAPTERS/`。如果宿主平台没有本地文件读取、浏览器、脚本或相应权限，必须明确报告不可执行，不得假装完成。

## 发布闸

在 `MANIFEST.md` 的 `release_status` 不是 `Ready` 或 `Published` 前，不得把本文件当作稳定外部 Skill 推荐给用户。发布前还必须通过品牌、联系、许可、去敏、参考实现、迁移和打包验收。

### 文章、分类、标签与正文图片变更授权

所有 AllinCMS 文章、分类、标签和正文图片草稿 mutation 必须传入结构化 `authorizationContext`；裸布尔值或“上层已经确认”的口头状态无效。该对象必须精确绑定 `site_key`、operation、目标摘要、具名 `human-asserted` actor、`approved_at` 与不超过 30 分钟的 `expires_at`，并在每次远程请求前重验。actor 身份固定为 `not_verified`；本地对象不证明真人批准。发布、删除仍需独立明确人工批准；历史 artifact 仅已发布为 Public Preview，当前未发布源码候选、远程副作用授权和 Stable qualification 仍分别保持 `BLOCK`。
