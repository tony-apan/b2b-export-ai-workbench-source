---
title: "Ingestion Log"
description: "冻结的旧版资料吸收与验证摘要兼容入口；历史 INGEST/VERIFY 别名保留，新来源登记、原始资料和运行事件分别进入 source registry、raw 与按日日志。"
type: "meta"
status: "Archived"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: []
related: ["logs/index.md", "../10_sources/source-registry.md", "../../raw/index.md", "open-questions.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Ingestion Log

> **FROZEN / NON-CANONICAL（2026-07-29）**：本页正文是旧版 ingest/verify 汇总，只读保留，不再追加。
>
> 迁移映射：来源身份与许可 → `wiki/10_sources/source-registry.md`；原始资料 → `raw/`；发生事件 → `logs/YYYY/MM/YYYY-MM-DD.md`；稳定提炼 → 对应 concept/playbook/course page；未决项 → `open-questions.md`。旧 `INGEST-*` / `VERIFY-*` 仅是历史 alias，重复 alias 不得被解释为多个独立证据。
按时间记录知识库发生了什么。公开版不记录私有文件名、本地路径、客户资料、账号数据或版权课程来源。

## [2026-07-26] CONV-20260726-PRIVATE-MASTER-SUBLIBRARY | 私有母库与首个可发布子库

- Source：Tony 当前对话；当前仓库和 GitHub visibility 实测。
- Type：governance / sub-library / website-content-operations。
- Files read：AGENTS、AI operating manual、wiki map、module registry、publishing/release rules、knowledge compounding system、website channel/playbook。
- Pages created：私有母库与子库模型、子库统一合同、发布清单模板、可发布子库入口、Website Content Operations 子库及模板。
- Pages updated：AGENTS、wiki index、wiki map、module registry、template index、publishing/release rules、open questions、conversation log。
- Decisions：完整知识库目标为私有母库；当前公开仓库在人工决定前继续按 public 处理；公开交付物通过 manifest 生成；客户事实只写客户运行区；首个模块先跑建站内容、图片、CMS 上传、验证和写回。
- Open questions：私有母库位置、当前仓库命运、品牌与许可、交付形态、首个 CMS、PicGo 图床和演示业务。
- Confidence：high for architecture and current repository visibility；end-to-end business execution remains unverified。
- Next：Tony 拍板仓库策略并提供最小品牌与工具信息，然后用虚拟公司跑一条真实工具链演示。

## [2026-07-26] SRC-20260726-KARPATHY-LLM-WIKI | 建立统一知识复利底座

- Source：Tony 当前方向、Karpathy 2026-04-04 LLM Wiki 原始 gist、Google 2026 AI 搜索与 Search Console 官方指南。
- Type：knowledge-base / seo / operating-system。
- Files read：本仓库 AGENTS、AI operating manual、来源系统、SEO channel/playbook；本地既有 Karpathy 风格知识库运行原则。
- Pages created：Karpathy 官方来源摘要、`knowledge-compounding-system.md`。
- Pages updated：AGENTS、AI operating manual、wiki map、总索引、来源登记、Google SEO 官方来源、SEO channel 和 SEO playbook。
- Decisions：全项目只用一个知识底座；Module 先读库再执行，执行后回写；SEO 先作为知识发现与验证 Module，而不是批量内容生产线。
- Open questions：真实私有 raw 的工具与存储位置仍需在工具层确定；本公开仓库继续只保留去敏编译层。
- Confidence：high；Karpathy 原始方法和 Google 官方边界已核验，业务效果仍需真实 SEO 数据验证。
- Next：停止扩课程大纲，下一步只梳理 SEO Module 的输入、输出、工具和第一轮真实数据闭环。

## [2026-07-26] CONV-20260726-CUSTOMER-VOICE-SEO-GEO | 客户聊天到搜索意图与内容

- Source：Tony 当前对话；Google Search Central AI features、people-first content 与 Search Console Performance 官方说明；OpenAI crawler 官方说明。
- Type：conversation / customer-voice / seo / geo-ai-search。
- Files read：search intent、customer pain map、SEO/GEO channel、SEO/GEO playbook、官方来源卡、模板和对话日志。
- Pages created：`wiki/_templates/customer-voice-to-search-intent.md`。
- Pages updated：search intent、customer pain map、SEO/GEO channel、SEO/GEO playbook、template index、conversation log。
- Decisions：内容是 SEO/GEO 共同载体；客户聊天是搜索意图和痛点的一方信号；真实聊天留私有层并按发布边界处理，演示统一使用标注清楚的虚拟聊天；聊天仍需转换和交叉验证；抓取不等于索引、排名、引用、推荐或转化。
- Open questions：待创建一份可公开演示的虚拟聊天；真实网站、Search Console、Analytics、询盘和 AI 搜索测试数据仍待接入。
- Confidence：high for workflow and official platform boundaries；business results remain unverified。
- Next：用模板完成第一份 chat-to-SEO/GEO end-to-end demo。

## [2026-06-28] PUBLIC-TEMPLATE-SETUP | 初始化公开版外贸增长 AI 工作台

- Type：setup / public-template / ai-workbench。
- Pages included：公开 SOP、模板、方法论、官方来源摘要、发布去敏规则、社媒账号安全红线。
- Pages excluded：真实 raw、客户资料、课程 PDF、账号数据、草稿输出、本地路径。
- Decisions：公开版只保留可复用框架和官方来源摘要；私有资料留在受控环境。
- Confidence：high。
- Next：使用者应在私有环境补充自己的 ICP、offer、proof、客户反馈、渠道数据和实验记录。


## [2026-07-26] CONV-20260726-TRANSFERABLE-CAPABILITY | 从工具教学升级为底层模型与迁移能力

- Source：Tony 当前对话中的稳定教学原则。
- Type：governance / pedagogy / transfer / website-content-operations。
- Files read：子库合同、知识复利系统、Website Content Operations 入口、playbook、tools、adapters、QA、manifest 和 version。
- Pages created：`sub-libraries/website-content-ops/MENTAL-MODEL.md`。
- Pages updated：子库合同、知识复利系统、Website Content Operations README、START-HERE、AGENTS、PLAYBOOK、TOOLS、ADAPTERS、QA、MANIFEST、VERSION 和 conversation log。
- Decisions：不教按钮，先教业务与数据模型；Obsidian、PicGo 和 CMS 作为参考实现；每个子库增加 Why / Model / Reference implementation / Transfer exercise；只有完成陌生工具映射、单样本、验证、诊断和写回，教学才通过。
- Open questions：首个 CMS、PicGo 图床、第二迁移工具、品牌、许可和演示业务仍待指定。
- Confidence：high for architecture and pedagogy；end-to-end transfer outcome remains unverified。
- Next：用虚拟公司完成首个参考实现，再换第二图床或 CMS 做迁移能力验收。


## [2026-07-27] CONV-20260727-MASTER-SUBLIB-FLUXPEDAL | 确认单仓母库、虚拟电机公司与四图床方案

- Source：Tony 当前对话的四项明确决定，以及 PicGo / R2 / GitHub / COS / OSS 官方资料。
- Type：governance / virtual-demo / tooling / website-content-operations。
- Files read：母库规则、当前焦点、模块登记、子库入口、课程、工具、adapter、manifest、品牌与联系。
- Pages created：PicGo 四图床官方来源页；R2、GitHub、COS、OSS adapter；FluxPedal Motors 公司、产品、ICP、虚拟聊天和首条闭环。
- Pages updated：AGENTS、母库模型、当前焦点、模块登记、Markdown schema、来源登记、子库入口、课程、工具、品牌、联系、版本、manifest、索引和开放问题。
- Decisions：当前根目录为逻辑母库，`sub-libraries/` 为子库；公开远程继续只放公开安全和虚拟内容；虚拟演示采用电动自行车电机出口商；PicGo 覆盖四种图床；用户入口收束为四阶段。
- Open questions：首个 CMS、首个真实图床环境、PicGo 唯一配置、正式品牌 / 许可、真实上传与迁移证据。
- Confidence：high for confirmed architecture and synthetic demo；external execution remains unverified。
- Next：经 Tony 确认首个 CMS 与首个图床后，执行 Obsidian → Codex 入库 → PicGo 单图 → CMS 草稿的真实小样。

## Log Template

```md
## [YYYY-MM-DD] source_id | task

- Source：
- Type：
- Files read：
- Pages created：
- Pages updated：
- Decisions：
- Open questions：
- Confidence：
- Next：
```
## [2026-07-26] REVIEW-20260726-KB-STRUCTURE | 知识库结构对抗审查与整改

- Source：Tony 当前要求；本仓库结构、权威规则、索引、module registry、子库合同和 Website Content Operations 全包。
- Type：adversarial-review / information-architecture / pedagogy / execution-contract。
- Files read：仓库 AGENTS、wiki index、AI manual、task router、module registry、module SOP、母库 / 子库治理、开放问题和 Website Content Operations 全部入口、模板、adapter、QA 与 manifest。
- Pages created：`current-focus.md`、结构对抗审查、COURSE-MAP、WORKSPACE-TEMPLATE、来源登记、工具字段映射、迁移练习、失败诊断和 adapter 强制模板。
- Pages updated：root / wiki / sub-library 导航、module registry、module expansion SOP、sub-library contract、task router、concept/business ownership、playbook、tools、QA、manifest、AGENTS 和日志。
- Decisions：当前只推进一个 Active 模块；文件存在不等于可执行；源码包、客户任务、迁移能力和品牌 release 分层验收；真实结果和第二工具迁移缺失时必须保持 BLOCK。
- Validation：170 Markdown；648 个本地 Markdown 链接；metadata 0 error；broken links 0；package link escape 0；本地绝对路径 0；credential-like hit 0；包内孤立 Markdown 0；`git diff --check` PASS。
- Open questions：私有母库、品牌 / 联系 / 许可 / 交付格式、虚拟演示业务、PicGo 图床、首个 CMS、第二迁移工具和真实验收网站。
- Confidence：high for structure and static validation；real tool execution and business outcomes remain unverified。
- Next：不扩其他 Module；先拍板 P0 并完成第一条端到端参考实现。

## [2026-07-27] ENV-20260727-ALLINCMS-R2 | AllinCMS + R2 参考实现只读环境证据

- Source：Tony 当前决定；本机命令和浏览器可见状态。
- Source type：conversation / local-environment / browser-observation。
- Registered facts：参考实现为 AllinCMS + R2；Obsidian / Codex 小闭环已通过；Wrangler 缺失；PicGo 无 R2 adapter 且 GUI / CLI 配置分叉；两个外部控制台均需登录。
- Derived decision：登录、安装、创建 bucket、上传和 CMS 写入继续保持动作时确认；当前不得把参考实现标记为已跑通。
- Files updated：`wiki/00_meta/current-focus.md`、`wiki/00_meta/open-questions.md`、`sub-libraries/website-content-ops/START-HERE.md`、`sub-libraries/website-content-ops/MANIFEST.md`。
- Sensitive data：未读取、记录或写入账号、邮箱、token、Access Key、Secret、cookie 或完整 PicGo 配置。
- Validation status：local / UI evidence confirmed；external write path BLOCK。

## [2026-07-27] INGEST-20260727-ALLINCMS-INTERFACE-CONTRACT

- Source：AllinCMS 官方公开文档、官方 sitemap 与 Tony 的接口化要求。
- Source type：official-docs / tooling decision / observed-interface design。
- Ingested into：`wiki/10_sources/SRC-20260727-ALLINCMS-OFFICIAL.md`、`sub-libraries/website-content-ops/ADAPTERS/cms/`、工具页、manifest、当前焦点和开放问题。
- Stable knowledge：官方文档确认建站、媒体库和 Codex 内容上传 UI 工作流；当前未确认公开开发者 API。站点发现和媒体上传应通过稳定 adapter 合同承载，内部 endpoint 必须登录后抓取、去敏、回放和验证。
- Hypotheses kept open：`/sites` 的真实数据来源、媒体上传步骤、最终内容字段对 URL / media ID 的要求、接口版本和限流。
- External actions：none；未登录、未上传、未创建或发布。
- Public safety：只保存官方链接、原创合同、占位符和验证规则，不保存凭据、真实账号或站点数据。

## [2026-07-27] VERIFY-20260727-ALLINCMS-SITE-DISCOVERY

- Source：已登录 AllinCMS 浏览器会话中的 `/sites` 页面、CDP 网络事件和 document 响应；仅保留去敏结构。
- Source type：authenticated-browser-observation / read-only-network-verification。
- Verified facts：`GET /sites` 返回 `200 text/html`；站点卡片随 SSR document 返回；响应内嵌 Next.js RSC Flight，`SitesClient.props.data` 提供 `id`、`name`、`description`、`slug`、`domains`、`displayDomain`、`active`、`themeCount`、`createdAt`；硬刷新未观察到单独的站点列表 JSON API 或 Server Action；页面控制台无 warning / error。
- Derived contract：`list_sites(current_session)` 优先解析 document 内的 `SitesClient.props.data`，与 DOM 卡片交叉核对，解析漂移时回退 DOM；写动作前仍必须确认 `site_key + display_name + frontend_domain`。
- Files updated：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms.md`、`wiki/00_meta/current-focus.md`、`wiki/00_meta/open-questions.md`。
- Sensitive data：未写入账号邮箱、站点名称、站点 ID、站点数量、cookie、token、header 值、完整响应或截图。
- Remaining block：目标 FluxPedal 测试站点未确认；媒体上传仍未触发，完整上传链继续为 `capture_required`。

## [2026-07-27] AllinCMS single media upload contract capture

- Event：`AllinCMS single media upload contract capture`。
- Source：Tony 动作授权 + 已登录浏览器中的真实单图观察。
- Result：`verified_single_upload`。
- Captured：浏览器侧 PNG → WebP 规范化、`/{site_key}/media` Next Server Action multipart POST、RSC 媒体记录、最终公开图片 URL。
- Verified：后台媒体记录、media ID、匿名 HTTPS `200`、图片 Content-Type、实际解码和后台刷新持久化。
- Public data：只写去敏合同、路由模式、字段名和散列指纹。
- Private runtime values written to repo：`false`。
- At that time not verified：纯 Server Action 第二次回放、产品 / 文章绑定、前台内容渲染、批量、删除和孤儿对象清理；后续单图零点击直传已在同日独立验证。
- Files：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/` 执行包、主 adapter、CMS index、当前焦点和开放问题。

## [2026-07-27] CONV-20260727-ALLINCMS-FIVE-MEDIA-BATCH | AllinCMS 五图批量协议验证与 adapter 修正

- Source：Tony 要求“尝试批量传 5 张试试”；真实登录 AllinCMS 浏览器会话；五张 FluxPedal 虚拟 PNG。
- Type：tooling / cms-adapter / live-batch-mutation / protocol-capture / verification。
- Files read：AllinCMS adapter 合同、语义化浏览器模块、匿名验证器、Website Content Operations manifest、当前焦点和开放问题。
- Pages updated：AllinCMS 去敏合同、执行 README、主 adapter 文档、子库 README / manifest、current focus、open questions 和 conversation log。
- Code updated：`upload-media-browser.mjs` 新增 1–5 图批量函数，并修正 RSC 对象错配、导航竞态和浏览器图片验证兼容性。
- Verified result：一次文件选择器选择 5 张、一次“上传 (5)”、一个目标 Server Action、五条媒体记录；媒体卡、刷新持久化、RSC 记录、媒体 ID、匿名 HTTPS、Content-Type 和解码均为 5/5。
- Decisions：当前只宣称受控 1–5 图语义化浏览器批量；点击确认后不自动重传；任何失败返回逐张结果供对账；大批量、幂等、限流、失败恢复、删除和内容绑定继续 BLOCK。
- Public safety：真实账号、站点 key、媒体 ID、对象 key、最终 URL 和完整 Server Action 值未写入仓库。
- Confidence：high for the observed five-file browser batch；production-scale retry and idempotency remain unverified。
- Next：用已上传媒体中的一张验证产品或文章草稿字段绑定与前台渲染；纯接口批量和超过 5 张的调度另立验证任务。

## [2026-07-27] VERIFY-20260727-ALLINCMS-DIRECT-MEDIA-UPLOAD

- Source：Tony 明确要求停止模拟点击；已登录 AllinCMS 媒体页中的真实同源 Server Action 请求与刷新后媒体状态；仅保留去敏结构。
- Source type：authenticated-browser-observation / live-mutation / direct-interface-verification。
- Authorized scope：一张新的无敏感 FluxPedal 虚拟图片；没有删除、发布或批量重传。
- Verified facts：UI 点击 0、文件选择器事件 0、直接接口请求 1；请求返回 `200 text/x-component`；刷新后新增一条媒体记录且媒体 ID 存在；匿名 HTTPS、`image/webp`、ETag 和 1200×800 图片解码均通过。
- Derived contract：单图默认使用部署相关的 Next Server Action 直传；每次动态发现 action、deployment、site ID 和 router tree；不读取或导出 cookie / token；结果不明时先查媒体库；该历史规则后续升级为“报错先延迟对账、确认缺失后有限重试当前图片”。
- Files updated：AllinCMS adapter、执行 README、去敏合同、母库当前状态和共享 AllinCMS skill。
- Sensitive data：未写入真实账号、内部 site ID、媒体 ID、对象 key、最终测试 URL 或完整 action 值。
- Remaining block：纯接口批量、幂等、部分失败恢复、产品 / 文章媒体绑定、删除和发布仍未验证。
## [2026-07-27] VERIFY-20260727-ALLINCMS-DIRECT-SERIAL-10

- Source：用户授权“接口传 10 张测试”后的真实登录媒体库验证。
- Type：live interface verification / CMS media / redacted evidence。
- Result：10 张虚拟 WebP 采用 10 次单图 Server Action 串行调用；UI 点击 0、文件选择器 0、上传与全链验收 10/10。
- Failure handling：第九张首次客户端 evaluate 超时后立即停止；媒体库按唯一标题确认未生成，才在原授权范围内受控继续；未盲目重传。
- Distilled to：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/README.md`、`observed-contract.redacted.json`、`direct-serial-10-verification.redacted.md`、AllinCMS 方法页和当前焦点。
- Boundary（当时）：一次 multipart 10 图、并发、跨轮幂等、自动失败恢复、内容绑定、删除和发布未验证。后续已补本地索引与恢复层；一次 multipart、多图并发、真实远程恢复 E2E、内容绑定和发布仍未验证。
- Safety：真实账号、站点 key、内部 ID、对象 key、动作值和最终 URL 未写入公开库。
## [2026-07-27] VERIFY-20260727-ALLINCMS-IMAGE-INDEX-E2E

- Source：用户授权的一张虚拟图片真实接口上传，以及仓库外私有索引事件。
- Type：live interface verification / image asset index / redacted evidence。
- Result：零 UI 点击、零文件选择器、一个直接接口请求；media ID、最终 URL、刷新持久化、匿名 HTTPS、图片解码和源资产到目标映射通过。
- Important correction：AllinCMS 返回的远端 WebP 与本地上传字节哈希不同；模板和 adapter 已改为分别记录源、上传输入和远端内容指纹。
- Duplicate boundary（当时）：第二次同标题调用在请求前停止；当时跨轮 SHA-256 幂等、并发和崩溃恢复未验证。后续已实现源 SHA-256 复用与本地断点恢复；并发及新增恢复层真实远程 E2E 仍未验证。
- Distilled to：`sub-libraries/website-content-ops/TEMPLATES/image-manifest.md`、AllinCMS adapter README / 方法页、`image-index-e2e-verification.redacted.md`、current focus 和 open questions。
- Safety：真实 site key、media ID、URL 与私有运行目录未进入公开证据。

## [2026-07-27] VERIFY-20260727-ALLINCMS-DIRECT-MEDIA-RECORD-DELETE

- Source：用户明确授权的一张唯一虚拟图片上传后直接删除；真实登录 AllinCMS 媒体页；仓库外私有运行事件。
- Source type：authenticated-browser-observation / destructive-live-mutation / redacted-evidence。
- Result：直接上传后取得唯一 media ID / 标题 / URL；直接删除请求 1 次、UI 点击 0、确认框 0、HTTP 200；刷新后媒体卡和 RSC 媒体记录消失。
- Asset boundary：删除后原公开 URL 立即与稍后 cache-bust 复查均为 `200 image/webp`，因此状态定义为 `media_record_deleted_asset_cleanup_unverified`。
- Distilled to：AllinCMS `AI-START-HERE.md`、机器合同、去敏删除证据、observed contract、adapter README / 方法页、current focus、open questions、manifest 和独立 skill。
- Private writeback：两轮测试事件均使用临时文件后原子 rename 更新；真实目标标识只保存在仓库外运行区。
- Safety：公开库不含真实 site key、site ID、media ID、最终 URL、完整 action ID 或私有运行目录。
## [2026-07-27] DECISION-20260727-ALLINCMS-DEFAULT-IMAGE-ROUTE

- Source：Tony 当前对话中的长期工具路由决定。
- Type：decision / tooling-route / CMS-media / cross-AI-handoff。
- Distilled rule：目标为 AllinCMS 媒体库时，默认使用预检 + 任意数量零点击接口串行总控 + 私有图片索引；单张原语不对业务调用开放；报错先延迟并只读对账，确认缺失后才有限重试当前图片；UI 与外部图床仅为非自动备选。
- Pages updated：Website Content Operations 的入口、课程图、工具页、adapter 导航、AllinCMS AI 唯一入口、执行 README、机器合同、母库 decision/current-focus/open-questions/index 和共享 Skill。
- Implementation（初版快照）：新增统一请求后歧义封装、只读对账、运行预检、源 SHA-256 图片索引、原子写入、单写者锁、断点恢复、串行总控和锁清理结果；补上 `prepared` 预存标题冲突防误认领与 `request_started` 恢复时规范化哈希保留。后续又加入 AI 元数据、自定义标题和停批规则，当前测试集为 29 项。
- Evidence boundary：没有新增真实远程写入；历史真实上传证据不等于新恢复层远程复验。
- Public safety：真实 site key、media ID、URL、账号凭据和客户私有 `imageIndexPath` 均未写入公开母库。

## [2026-07-27] EXPLORE-20260727-ALLINCMS-ARTICLE-OPERATIONS

- Source：已登录 AllinCMS 工作区的文章列表、已有文章草稿编辑页、文章分类页只读观察；结合已登记的官方来源和历史保存 action 参考。
- Source type：authenticated-browser-observation / read-only-schema-exploration / observed-internal-contract-reference。
- Scope：只核对文章列表字段、文章编辑字段、分类树根/子分类入口、分类弹窗字段、文章 payload 形状和保存/发布语义；没有点击文章创建、分类创建、保存、发布、删除或图片上传。
- Distilled facts：文章列表包含 `title`、`slug`、`excerpt`、`order`、`status`、`category`、`tags`、创建时间；编辑页出现 Slate 正文、`title`、`slug`、标签、`excerpt`、`order`、`coverImage`、更新、发布、历史；历史 payload 使用 `categories` / `tags` ID 数组，`content` 为 Slate 节点数组，`mode=update` 与 `mode=publish` 分开。
- Category rule：文章分类位于文章模块独立分类 tab；顶部 `+` 创建根分类，行级 `+` 创建子分类；创建弹窗当前只显示名称和 Slug，编辑面板另有描述和封面。必须先读树、判断父子关系、创建后刷新并取得 ID，不能默认复用产品分类 ID。
- Distilled to：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md`、AllinCMS adapter 索引、CMS/子库导航、`wiki/00_meta/current-focus.md`、`wiki/00_meta/open-questions.md`。
- Boundary：本轮结论是 `article_schema_read_only: captured`，不是 `article_write_verified`；当前部署的 create/update/publish action、分类创建 payload、标签创建合同、真实草稿到前台详情闭环仍待单样本授权实跑。
- Safety：没有产生远程写入或发布；真实账号、site key、site ID、post ID、category ID、media ID、最终 URL 和完整 action 值未写入公开库。

## [2026-07-27] VERIFY-20260727-ALLINCMS-ARTICLE-API-PUBLISH | 单篇文章接口保存、发布与前台闭环

- Source：Tony 明确要求“先探索接口，再用接口发文章”；已登录 AllinCMS 工作区和当前测试站点的真实文章页。
- Type：authenticated-browser-observation / live content mutation / Server Action replay / frontend verification / redacted writeback。
- Authorized scope：创建并发布一篇无敏感、无封面、空分类/标签的虚拟验证文章；未创建新分类、未上传图片、未删除或修改其他文章。
- Captured contract：文章更新路由为 `POST /{site_key}/posts/{post_id}/update`；请求体为 `[payload]`；字段为 `title`、`slug`、`excerpt`、`order`、`coverImage`、`categories`、`tags`、`content`、`siteId`、`postId`、`mode`；`next-action`、deployment、内部 ID 只保留运行时，不写公开库。
- Verified result：`mode=update` 返回 HTTP 200 / `text/x-component`，后台刷新后正文可见且为草稿；同一完整 payload 改为 `mode=publish` 后返回 HTTP 200 / `text/x-component`，后台刷新显示“已发布”。
- Frontend result：`/posts` 列表出现标题、摘要和详情链接；`/posts/{slug}` 返回 HTTP 200，标题、摘要和两段 Slate 正文均出现在 DOM。
- Tooling finding：Playwright 隔离 evaluate 环境没有 `fetch`；本轮用同一登录页面的 CDP 主世界 `Runtime.evaluate` 发同源请求，没有导出 cookie、token 或凭据。
- Distilled to：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md`、AllinCMS CMS adapter 入口、`wiki/00_meta/current-focus.md`、`wiki/00_meta/open-questions.md`。
- Boundary（历史快照，已被后续加固记录细化）：文章 schema、UI 创建远程草稿、update/publish 和前台列表/详情曾在单样本观察中通过；`postCreate` API 当时未独立验证，后续当前口径仍为 `BLOCK`。分类 create、标签、封面、复杂 Slate、删除/取消发布、失败重试和回滚在该快照时仍待单独验证。
- Safety：真实站点 key、site ID、post ID、category ID、media ID、最终测试 URL、完整 action 值和账号信息未写入公开库。

## [2026-07-27] VERIFY-20260727-ALLINCMS-FIELD-COMPLETE-ARTICLE-COVER | 全字段文章真实封面发布闭环

- Source：Tony 要求“模拟真实发文章，所有字段都有，有真实的图片”；沿用同一已登录 AllinCMS 会话完成接口保存、发布和前台验证。
- Type：authenticated-browser-observation / live content mutation / Server Action replay / frontend verification / redacted writeback。
- Authorized scope：复用已有文章分类、四个已有标签和一张媒体库真实图片，创建/更新并发布一篇虚拟英文文章；未创建新分类、未创建新标签、未上传新媒体、未删除其他对象。
- Full-field result：`title`、`slug`、`excerpt`、`order`、`coverImage`、`categories`、`tags`、16 个 Slate `content` 节点、运行时 `siteId` / `postId`、`mode` 均进入同一完整 payload；先 `update` 后 `publish`。
- Cover result：当前部署实测 `coverImage` 为 `source: "oss"` + `path`，另带 `name`、`alt`、`type`、`size`、`mimeType`；后台刷新后封面保留，前台列表和详情真实渲染封面 HTTPS 图片。旧的 `source: "url"` + `url` 仅保留为历史/其他部署可能形状。
- Taxonomy result：已有分类 `Catalog & Content` 和四个已有标签绑定成功；分类创建和标签创建没有被本轮宣称验证。
- Frontend result：前台 `/posts` 列表出现标题、摘要、分类和封面；文章详情出现标题、摘要、正文首节、四个标签和封面。
- Fresh recheck：本轮再次匿名请求前台列表和详情均返回 HTTP 200；标题、摘要、分类、四个标签、封面资源均在 HTML 中出现，封面响应为 `image/webp`、1200×800。
- Safety：真实 site key、site ID、post ID、category ID、tag ID、media ID、最终测试 URL、完整 action 值、cookie/token、账号信息和真实运行目录未写入公开知识库。
- Distilled to：`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md`、`wiki/00_meta/current-focus.md`、`wiki/00_meta/open-questions.md`、`wiki/00_meta/decision-log.md`。

## [2026-07-27] INGEST-20260727-ALLINCMS-TAXONOMY-ARTICLE-STABILITY

- Source：Tony 当前对话，要求真实创建文章分类、文章标签，并用接口进行多轮稳定性测试。
- Type：authenticated-browser-observation / live taxonomy mutation / Server Action replay / frontend verification / redacted writeback。
- Scope：当前登录测试站点；创建一个虚拟文章根分类、一个虚拟文章标签和一篇专用测试文章。未删除内容，未修改既有业务文章。
- Captured：分类 create 使用文章 `categories` tab 当前页面 POST，payload 含 `siteId`、`contentType`、`name`、`slug`、`description`、`cover`、`parent`、`order`；标签 create 使用 `tags` tab 当前页面 POST，payload 含 `siteId`、`contentType`、`name`、`slug`、`description`。
- Verified：分类/标签创建均 `200 text/x-component`；刷新后唯一存在；文章全字段 `update`、重复 `update`、变更后 `update` + `publish`、重复 `publish` 全部 `200 text/x-component`；后台字段和前台列表/详情双次验证通过。
- Media：最终封面来自真实媒体库 WebP；匿名 HTTPS、MIME、解码和尺寸验证通过。曾发现一个仅凭名称推断的路径实际 404，已按媒体记录重取完整对象并修正，作为负例写入 adapter 边界。
- Redaction：未写入真实站点 key、siteId、postId、categoryId、tagId、mediaId、真实 URL、完整 `next-action`、router state、cookie、token、账号信息。

## [2026-07-27] AllinCMS 严格串行图片元数据与删除口径固化

- 输入：Tony 对媒体删除完成口径、禁止并发、图片信息字段和 AI 自动读图填写的明确要求，以及 2026-07-27 已登录 AllinCMS 媒体页的真实只读检查与一次获批虚拟元数据写入证据。
- 提炼：上传弹窗无元数据字段；编辑记录支持 `title / alt / caption`；完整 description 与结构化 metadata 留在客户私有图片索引。
- 实现：串行总控支持 AI 候选、自定义标题写前撞名检查、每图单次元数据请求、有限只读刷新复核、歧义停批和 verified 映射只同步元数据。
- 决策：永久禁止媒体并发；删除成功只看精确媒体卡和 RSC 记录消失；物理资产状态退出当前验收和阻断。
- 验证：一张获批虚拟媒体三字段最终持久化，观察到读后写延迟；本地 22/22 tests passed；源文件无 `Promise.all` / `Promise.allSettled`。
- 写回：更新 AllinCMS adapter、AI 入口、机器合同、元数据 SOP、当前焦点、开放问题、manifest、索引和独立 skill。
- 边界：未新增远程写入；一张样本不证明所有账号、站点和未来部署稳定。

## [2026-07-27] INGEST-20260727-ALLINCMS-UNBOUNDED-SERIAL-RETRY

- Input：Tony 对 AllinCMS 图片批量口径的最新覆盖决定。
- Distilled rule：取消 10 张控制器上限，但不取消严格串行；错误后先延迟和只读对账，确认远端缺失后才重试当前图片。
- Implementation：更新 `uploadAllinCmsMediaSerial()`、29 项测试、AI 唯一入口、元数据 SOP、机器合同、课程状态页和独立 AllinCMS skill。
- Safety：不并发；不在对账不明确时重传；不把上传重试扩展到元数据或删除重发；不写入真实站点 key、媒体 ID、URL、cookie、token 或完整 action。
- Verification scope：本地 12 张严格串行与故障注入通过；本轮无真实远程写入。

## [2026-07-27] VERIFY-20260727-ALLINCMS-FIRST-FOUR-LIFECYCLE

- **Source**：Tony 当前对话；当前登录 AllinCMS 站点的真实接口回放、后台刷新、前台访问和测试清理结果。
- **Type**：cms / article-operations / taxonomy / lifecycle-verification。
- **Observed**：分类编辑、隐藏/恢复、排序、根/子分类 `parent`、删除；标签编辑、删除、重复 slug 前置校验；文章全字段 `update`、重复 `update`、`publish`、重复 `publish`、`unpublish`、恢复发布、删除。
- **Contract**：文章更新路由为 `POST /{site_key}/posts/{postId}/update`；文章删除为 `POST /{site_key}/posts?tab=list` 数组；分类和标签删除分别为 `posts?tab=categories` / `posts?tab=tags` 数组。Server Action ID、站点 ID、对象 ID 和媒体对象必须动态捕获。
- **Evidence**：所有动作均按“UI 捕获（必要时）→ 接口实际回放 → 后台刷新重读 → 前台验收”区分；文章使用全字段和真实 WebP 封面；删除后后台行消失、前台详情 404；临时文章、标签、子分类清理完成。
- **Boundary**：分类/标签创建曾出现 transaction state mismatch，后续需单次创建后等待、刷新和重读；跨部署、大批量、复杂 Slate、503/回滚仍开放。
- **Writeback**：已更新 `sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md`、`current-focus.md`、`open-questions.md`、`conversation-log.md`、`decision-log.md`。


## [2026-07-27] INGEST-20260727-ALLINCMS-COMPLEX-SLATE-CLEANUP

- **Input**：继续执行 AllinCMS 文章真实接口逐项测试，补齐复杂 Slate 列表/正文图片字段，并清理临时文章。
- **Observed**：UI 保存请求给出无序/有序列表真实节点；完整文章接口恢复并发布后，后台刷新和前台内容层验证通过；真实 WebP 为匿名 HTTPS、`image/webp` 且可解码。
- **Gap**：当前主题将无序列表输出为嵌套 `div`，正文图片 `alt` 未透传；这是主题表现层与无障碍缺口，不是当前保存接口的字段缺失证据。
- **Cleanup**：目标文章删除请求一次；后台目标行消失，前台详情 404；非目标删除确认在确认前取消。
- **Writeback**：更新 AllinCMS article adapter、current focus、open questions、conversation log、decision log。
- **Boundary**：不写入运行时 ID/URL/action/认证信息；跨部署、复杂表格/嵌套列表、失败恢复、回滚和大批量仍开放。

## 2026-07-27 — AllinCMS Markdown 正文图片 A/B/A 草稿验证与稳定化

- Source type：用户要求 + 已登录真实 AllinCMS 虚拟草稿验证 + 当前部署客户端合同 + 本地故障测试。
- Scope：文章图片资产/occurrence 映射、Markdown 原位绑定、Plate Caption、草稿保存回读、编辑器渲染健康、Alt 分层与清单锁恢复。
- Confirmed：2 个资产 / 3 occurrence 的 A/B/A 草稿绑定通过；字符串 Caption 会导致编辑器 500；数组 Caption 修复后后台回读、编辑器重载、3/3 图片解码和 Caption 可见通过；草稿未发布。
- Product gap：后台 Alt 已持久化，但编辑器 DOM 3/3 未输出 `<img alt>`；当前公开主题未验证。
- Public redaction：未写入真实 site key、site/post/media ID、Action ID、deployment、账号或资产 URL；完整证据保留在仓库外的私有运行区，不进入公开母库。
- Outputs：更新 AllinCMS adapter 文档、`article-image-binding-contract.json`、图片清单模板、共享 Skill、知识库导航与状态日志。
- Verification：文章 30 项 + 媒体 29 项本地测试；语法、JSON、链接/敏感检查在本轮收口执行。

## [2026-07-27] ING-20260727-ALLINCMS-ARTICLE-IMAGE-STABILITY-CLOSEOUT

- Source：Tony “干，确保稳定！”；当前授权虚拟 A/B/A 草稿的只读浏览器状态；本地 adapter 与机器合同。
- Type：authenticated-browser-readonly-verification / adapter hardening / machine-contract update / cross-AI SOP sedimentation。
- Distilled to：`article-image-binding.mjs`、`article-image-binding.test.mjs`、`article-image-binding-contract.json`、`observed-contract.redacted.json`、AllinCMS AI 入口、adapter 索引、子库状态、共享 AllinCMS Skill 和当前焦点。
- Verified result：新版编辑器健康闸只读通过；3 张正文图片数量精确、3/3 解码、Caption 顺序一致、Draft/草稿 badge 存在、无 500；编辑器 DOM Alt 缺失 3/3 继续作为产品缺口。
- Local result：文章图片 31/31、媒体 29/29，合计 60/60。
- Safety：未发布、未重新上传、未重发文章保存、未提交、未推送；公开母库未记录真实 siteKey、postId、mediaId、Action ID、Deployment ID 或资产 URL。


## 2026-07-27 | AllinCMS article direct serial 11 verification
- Goal: 在已完成单篇文章接口闭环后，验证当前部署连续 11 篇完整字段文章的接口串行稳定性，并清理临时数据。
- Sources used: 用户当前对话中的真实接口运行结果；`sub-libraries/website-content-ops/ADAPTERS/cms/allincms/article-operations.md`；去敏证据 `direct-serial-11-article-verification.redacted.md`。
- Facts added or changed: 11/11 完整 `update → publish`；后台 11/11 已发布；前台标题、正文、列表文本 11/11 通过；55/55 图片加载解码；11/11 封面为 1200×800 WebP；临时文章 11/11 已清理。
- Actions executed: 每篇严格串行；每个动作后等待、后台刷新、重读，再进入下一步；一次批量 CDP 调用超时后没有重发，改为后台只读回读。
- Verification: 后台状态和前台详情均完成核对；清理后后台目标行消失；一次非目标删除确认已取消。
- Failures and rollback: 记录了一次客户端超时；因远端状态可能不明，禁止自动重试，先回读后继续；本轮未执行 503 或文章级回滚测试。
- Customer workspace updates: 无；仅回写公开母库的去敏合同和边界，不写入 siteId、postId、媒体 path、Cookie、Token 或完整 action ID。
- Generic improvement candidate: 将文章动作固定为“动态捕获 → 单篇完整 update → 刷新对账 → publish → 前台验收”，并把状态不明统一处理为“只读回读、不自动重发”。
- Human approval needed: 更大文章批次、失败恢复/回滚、跨部署和主题渲染修复仍需单独授权与证据。


## [2026-07-27] INGEST-20260727-ALLINCMS-ARTICLE-IMAGE-HARDENING-65-CLOSEOUT

- **Input**：Tony “干，确保稳定！”；现有 AllinCMS A/B/A 草稿证据；正文图片 adapter、机器合同与共享 Skill。
- **Type**：adapter hardening / machine-contract update / cross-AI SOP sedimentation / local adversarial verification。
- **New hardening**：映射源 SHA-256 必须等于资产 ID；候选必须携带已知 media ID 和 URL；禁止标题式认领；Slate 构建前重读本地图片字节；后台 Caption 结构二次复验；文章清单锁记录 PID、时间和目标。
- **Verification**：文章图片 36/36、媒体 29/29，合计 65/65；本轮没有远程变更。
- **Distilled to**：AllinCMS 正文图片实现、测试、schema 1.4 合同、AI 唯一入口、adapter 文档、子库状态、共享 Skill 与当前焦点。
- **Known gap**：`backend_alt: persisted_and_read_back`；`editor_dom_alt: missing_observed_3_of_3`；`published_theme_alt: not_run_not_authorized`。
- **Safety**：不记录真实 siteKey、postId、mediaId、Action ID、Deployment ID、账号、认证数据或资产 URL；草稿未发布。


## [2026-07-27] AllinCMS 文章 Adapter 对抗审查加固收口

- **输入/范围**：复核共享 `allincms-bulk-content-upload` 与 `701_kecheng` 当前 Adapter 的权威关系，检查文章/分类/标签动作、恢复、批量和主题表现层的放行口径。
- **已写回**：共享 `SKILL.md`、`README.md`、`references/server-action-save-api.md` 增加“当前 Adapter 优先、共享模板为中性/历史、已登录不是合同证据、敏感不作为额外阻断”的明确规则；知识库 Adapter 与文章文档保留当前运行时合同。
- **代码/测试状态**：`article-operations.mjs` 的 ID/slug 规范化、状态规范化、精确不存在确认、创建前 `beforePostIds` 快照和状态不明人工介入规则已落地；当前 Adapter 测试总计 `115/115` 通过。
- **仍未放行**：当前部署 `postCreate` 远程合同未重新捕获并回放；文章级远程 503/transaction mismatch/请求可能成功恢复未注入验证；跨部署/跨站点与大于 11 篇长跑未证明；当前主题无序列表语义和正文图片 `alt` 透传缺口未修复。
- **结论**：敏感性不是本轮阻断原因；整体仍为 `BLOCK`，原因是证据、恢复合同和表现层缺口。不得把本地 115/115 或当前部署限定闭环外推为任意部署/任意批量 PASS。
- **来源**：当前工作区 Adapter、合同、测试和共享 skill 文件；Tony 当前对话，2026-07-27。


## [2026-07-28] INGEST-20260728-RAW-COURSE-CLOSURE | Synthetic raw-to-course closure fixture

- Input：`raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md`。
- Classification：公开安全的 `virtual-fixture`，不是真实客户、课程原文、账号数据或市场证据。
- Source ID：`SRC-20260728-RAW-COURSE-CLOSURE`，已登记到 `wiki/10_sources/source-registry.md`。
- Derived：`ID-0002` index discovery concept、`ID-0003` raw-to-course playbook、`ID-0004` course module，以及 `VER-20260728-raw-course-closure`、`WB-20260728-raw-course-closure`。
- Verification：通过本地文件链和字段一致性检查；第二场景人工评分、真实教学效果、许可证最终批准仍未完成。
- Safety：没有真实客户资料、账号、Cookie、Token、经营数据或第三方课程内容；母库和子库 `release_status` 继续为 `BLOCK`。
- Next：将人工评分阈值、fixture 标识规范和私有真实样本脱敏记录方式写入开放问题，运行完整结构与候选包验证。
