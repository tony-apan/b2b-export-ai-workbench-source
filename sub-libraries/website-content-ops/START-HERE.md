---
title: "AI Execution Start"
description: "给可读取本地文件并在用户授权后调用浏览器或脚本的 AI agent 使用的执行入口；按工具检查、知识建卡、单样本和验证写回四步推进，并在无账号、权限不清或结果不明确时停止。"
type: "guide"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-12"
sources: ["COURSE-MAP.md", "Tony decisions 2026-07-27", "Tony AI execution entry decision 2026-07-30"]
related: ["README.md", "RUNTIME-INTEGRATION.md", "CONTACT.md", "COURSE-MAP.md", "AGENTS.md", "EXAMPLES/fluxpedal-motors/README.md", "ADAPTERS/image-upload-routing.md", "ADAPTERS/cms/allincms/AI-START-HERE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "AI 第一次接手本子库，需要确认自身工具能力、当前账号和权限，并开始第一个最小样本时。"
keywords: ["AI execution", "start here", "tool preflight", "AllinCMS", "single sample", "approval boundary"]
---
# AI 执行入口

> **本页主要给 AI agent 读取和执行。** 人类用户不需要逐条操作，只需要说明目标、提供必要资料、在自己的浏览器中完成登录，并对上传、覆盖、删除或发布分别确认。不要向 AI 发送密码、Cookie、Token 或 Secret。

## 开始前先声明能力

AI 必须先检查并用大白话告诉用户：

- 是否能读取和写入本地文件；
- 是否能使用浏览器、Node.js 和本目录脚本；
- 是否已经看到用户指定的准确站点和页面；
- 哪些步骤可以立即执行，哪些需要用户登录、补资料或批准；
- 如果当前宿主 AI 缺少工具，明确报告不可执行，不得假装完成。

没有 AllinCMS 账号、没有开通网站或无法确认站点时，不要代替用户注册、猜测站点或尝试绕过登录。停止远程 CMS 路线，并提醒用户查看 [README 的联系入口](README.md#没有-allincms-账号) 或 [CONTACT.md](CONTACT.md)；如果本地资料足够，可继续完成不产生远程副作用的小样，并把远程步骤标记为 `BLOCK / not executed`。

## 用户资料驱动路线

当用户提供 PDF、DOCX、表格、网站、图片或 brief，并要求新建或更新网站、文章或产品时，先读 [Source-Driven CMS Create and Update SOP](PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md)。不要把示例公司、站点、语言、分类、标签、产品字段、CTA、组件或 Action ID 当默认值。先登记原始来源和 bytes/snapshot digest，再按宿主格式能力生成并校验 [Source Extraction](TEMPLATES/source-extraction.md)；提取 unit 只是 claim candidate，必须保留 locator、extraction digest、提取器/version、置信度和 warning。之后建立事实/冲突账本与平台无关 desired state，只读发现当前 CMS 和目标对象，生成 [Content Operation Plan](TEMPLATES/content-operation-plan.md)；`upsert` 在 mutation 前必须解析为精确 `create/update/noop`。

> 资料证据门禁：`confirmed/inferred` claim 必须绑定 Source Extraction 的精确 locator 与提取 digest；mutation 字段必须绑定 `claim_refs` 和 `derivation`。远程 mutation 只接受未过期的 `live_verified_current_deployment` capability；公开写入由 `publication_effect` 显式标记，所用来源必须为 `approved/not-applicable`。

新建网站必须拆成两份不可混合的计划：Plan A=`site_bootstrap`，以当前登录账号为 target，只创建一个 site resource，且 `site_key/site_id=null`；回读真实 `site_id/site_key/account owner` 后停止。Plan B=`site_operation`，引用 Plan A digest 和私有 readback evidence，重新发现 capability/current state，再处理分类、标签、媒体、文章、产品或主题页。不得用 `<planned-site>` 或测试站 key 占位，也不得共用两阶段授权。

更新已有内容时，未在用户资料中出现的字段默认保持不变；仅按标题或名字模糊匹配、缺 expected-current fingerprint、跨站 fallback、能力仍为 `exploration_only` 却计划发布，都必须停止。接口优先，UI 只负责登录、合同探索或验收，不得静默降级。

## 按四步执行

```mermaid
flowchart LR
  A["1. 检查工具和权限"] --> B["2. 建四张知识卡"]
  B --> C["3. 跑一个内容小样"]
  C --> D["4. 验证并写回"]
  D --> E["经批准后再扩量或迁移"]
```

## 1. 检查工具和权限

AI 执行：

1. 读取 `AGENTS.md`、`MANIFEST.md`、[RUNTIME-INTEGRATION.md](RUNTIME-INTEGRATION.md) 和目标 adapter 入口，不扫描无关目录；
2. 验证 `agency-operations` 已初始化 `customer-runtime/`，并且 ACTIVE-CONTEXT、Registry、CLIENT、TASK 与 HANDOFF 对同一 `client_id + company_id + task_id` 一致；任何 scope 缺失或冲突都 fail-closed，禁止无 scope 搜索；
3. 检查本地 Markdown、Node.js 和所需脚本是否可用；
4. 如果用户使用 Obsidian，只需确认它能打开目标目录；Obsidian 不是强制依赖；
5. 若目标是 AllinCMS，先用宿主内置 Browser 的当前 session 接口请求 `/sites?_rsc`，获取登录状态、`user.id` 和完整网站列表；只有未登录时才打开并前台展示 `/sign-in`，登录后必须重新 API 检查，再处理 0 / 1 / 多站点和精确 `site_key`。完整状态机只读 [AllinCMS AI 唯一入口第 0 节](ADAPTERS/cms/allincms/AI-START-HERE.md#0-默认启动登录交接与回落路由)；
6. 运行 AllinCMS 只读环境预检，不读取或导出 Cookie、Token 和密钥；默认走接口，接口异常先判断请求是否可能已发出，再只读对账或打开页面诊断，不自动改走 UI；
7. 只有用户明确需要外部图床时，才检查 PicGo 以及 R2、GitHub、腾讯云 COS、阿里云 OSS；
8. 汇总可执行项、缺失项、风险和下一步，等待必要批准。

> **AllinCMS 媒体库默认直接上传。** 使用 [图片上传统一路由](ADAPTERS/image-upload-routing.md) 和 [AllinCMS AI 唯一入口](ADAPTERS/cms/allincms/AI-START-HERE.md)。不需要先配置 PicGo、R2 或 GitHub。外部图床只作为跨系统公开 URL、迁移练习或用户明确指定时的备选。

安装、升级、改配置、创建 bucket、上传和发布都必须先得到用户确认。已获得某次上传授权，不等于获得删除、覆盖或发布授权。

完成只读预检后，把本次 deployment fingerprint 和 `site_key` 写入私有 operation plan；动态 Action ID、Cookie、Token 和完整请求头不写入计划或公开母库。

## 2. 建四张知识卡

只建立：公司、产品、ICP、客户语言。每条信息标记 `confirmed / inferred / missing / conflicting / expired`，并保留来源指针。

资料不足时先列出真正阻断小样的问题，不进行无边界访谈。没有真实资料时，可从 [FluxPedal Motors 虚拟演示](EXAMPLES/fluxpedal-motors/README.md)开始，但必须明确标记为 synthetic，不得写成真实客户证据。

## 3. 跑一个内容小样

先完成一条最小闭环：

- 一份客户聊天到搜索意图的 article brief；若从空白新写正式买家文章，先读 [B2B SEO Article Standard](PLAYBOOKS/id-0001-b2b-seo-article-standard.md)；若优化现有文章，先读 [B2B Article Optimization SOP](PLAYBOOKS/id-0003-b2b-article-optimization-sop.md)，并继续接受 ID-0001 的全部质量闸；随后使用 `TEMPLATES/article-brief.md`；
- 一张图片和 image manifest；
- 若用户已明确批准并具备 AllinCMS 环境，通过 `uploadAllinCmsMediaSerial()` 上传一张图片；
- 获得一一对应的 media ID、公开 URL、源 / 上传 / 远端哈希和本地私有图片索引；
- 使用 `TEMPLATES/article-draft.md` 建立标题、正文和持久化格式合同；草稿完成后再使用 `TEMPLATES/article-quality-review.md` 做非作者对抗审查，并检查 [Article Page Frontend SEO Contract](PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md)；
- 只有内容、前端和目标 Adapter 均无 blocker，才建立一条 CMS 草稿；默认不直接发布；
- 真实写入后用 `TEMPLATES/publish-record.md` 记录后台刷新、编辑器重开、桌面/移动前台、SEO 源码和 sitemap。

如果没有账号或没有获得上传批准，仍可完成本地 brief、image manifest 和模拟 CMS 草稿，但必须把远程上传与真实页面验证标记为 `BLOCK / not executed`，不得伪造 media ID 或 URL。

每张真实图片必须按“接口上传 → 自动刷新 → 全链验证 → 原子写索引”完成后再进入下一张。结果不明确时只读对账，不自动重传。

## 4. 验证并写回

验证页面、图片、字段和状态；正式文章还要验证 lang、canonical、robots、Article/Breadcrumb schema、语义层级、移动端、图片和 sitemap；记录失败、指标和人工判断。客户事实与 `image-index.json` 留在客户私有运行区，通用模板和 adapter 改进审核后写回母库。

只有当前样本通过并获得用户对下一批精确对象的批准后，才能扩大批次或迁移到第二工具。不能把一次样本通过外推为跨站点、跨部署稳定。

## 第一条 AI 指令

```text
请读取 README.md、AGENTS.md、START-HERE.md、MANIFEST.md，
以及与当前任务最相关的 adapter 入口，不要扫描无关目录。

先声明你当前能否读取/写入文件、使用浏览器和运行 Node.js 脚本。
然后只执行第 1 步“检查工具和权限”，不要安装、升级、改配置、上传或发布。

如果目标是 AllinCMS：
1. 默认用宿主内置 Browser 的当前 session 请求 /sites?_rsc；只有接口确认未登录时才打开 /sign-in、保持前台并立即引导；
2. 登录后重新 API 检查 user.id、分页完整网站列表和 canCreate，再由用户确认准确 site_key；
3. 打开精确 /{site_key}/media，检查页面健康后运行 checkAllinCmsMediaRuntime()；
4. 告诉用户 WebP 是否可直接传，以及 PNG/JPG 是否缺 sharp；
5. 准备客户私有 image-index.json 路径，并向用户列出精确 site_key、操作和有序文件列表；
6. 用户批准后创建 authorizationContext，再默认调用 uploadAllinCmsMediaSerial()；接口异常先只读对账或页面诊断，不自动 UI 回退。

没有账号、站点不确定或权限不清时停止，提醒用户查看 README.md 的联系入口。
不要先让用户选择 PicGo 或外部图床；只有用户明确需要外部公开图床时，
再提供 R2、GitHub、COS、OSS 备选。
```

## 停止条件

出现以下任一情况时立即停止并标记 `BLOCK`：

- AI 无法读取必要文件、使用所需工具或验证真实结果；
- 没有账号、登录失效、站点 key 不确定或权限不清；
- 接口漂移、索引锁、索引写入失败或结果不明确；
- 来源冲突、未知版权、目标文件与授权文件不一致；
- 当前步骤需要上传、覆盖、删除或发布，但用户尚未批准；
- 操作无法验证或无法回滚。

不得自动改走 UI、PicGo、其他图床或另一个站点来绕过阻断。远程 CMS 步骤被阻断时，可以继续本地整理和模拟草稿，但必须清楚标记未执行范围，不能把局部 BLOCK 写成整个任务已经完成。
