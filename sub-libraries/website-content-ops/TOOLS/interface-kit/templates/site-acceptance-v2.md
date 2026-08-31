---
title: "建站交付全量验收清单 v2（逐项检查 + 对抗完善流程）"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-09-01"
description: AllinCMS 建站工具包文档（site-acceptance-v2.md）
created: "2026-09-01"
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["交付站巡检发现 13 项审计盲区四类漏网问题 2026-09-01（lang 标错/模板 meta description/弹窗不挂载/浮钮缺失）", "site_pipeline.py audit 13 项现状与 ISS-073/ID-0007 C2 已证平台边界", "Tony 指令：穷尽检查项+对抗验收+模块表单摸索 2026-09-01", "对抗审查（独立 reviewer NO-GO→修订）2026-09-01：P0×5/P1×10/P2 补充 30 项全采纳"]
related: ["../NEW-SITE-ONEPASS.md", "../RUNBOOK-ANYONE.md", "../MODULES.md", "site-audit-config.template.json", "delivery-manifest.md", "../../../PLAYBOOKS/id-0007-site-launch-acceptance.md"]
---

# 建站交付全量验收清单 v2

> **为什么有 v2**：13 项机器审计全 PASS 的交付站，交付后巡检仍发现四类漏网问题——`lang` 标错（英文站 zh-CN）、5 个顶层页面模板默认 meta description、Get a Quote 弹窗点击无反应、WhatsApp 浮钮缺失——全部在旧审计盲区。v2 把"检查什么"穷尽到 7 层 61 项，把"怎么验"升级为四轮对抗流程。**判据从"审计 PASS"改为"陌生买家能不能用这个网站完成询盘"。**
>
> **两档强度**：新站交付 = 全量 61 项四轮；巡检/维护 = L1+L2.8+L3.3+L4.1 子集（结果按日期分节追加到 acceptance-v2.md，不新开文件）。
>
> **前置确认（已生效）**：RUNBOOK 顶部横幅的四项平台前端审计项（lang/canonical/JSON-LD/img-attrs）原为 2026-08-30 永久禁令；按 Tony 2026-09-01"可"的确认，已收窄为**可检查+登记、平台修复前不阻断交付**（横幅已同步）。原标 ⛔ 的条目全部解锁为 BOUNDARY 语义（检查→登记证据→不写 FAIL 拦截交付），平台缺陷走 L7 三要件（OQ-TOOL-0004）。
>
> **与既有验收体系的关系**：轮1 机器审计 13 项是**底座**（v2 不替代它，坐在它上面）；本清单与 ID-0007（CAN-001，上线判定合同）的关系 = **取代其 B 表验收清单部分，边界事实（C 表）继续有效**，ID-0007 待下批同步修订声明。冲突时以本清单为准（更新）。

## 第〇部分：底座映射（audit 13 项 → v2 归属，旧项一个不丢）

| audit 项 | v2 归属 | 说明 |
|---|---|---|
| http | L1.1 | 升级：并入"非 Runtime 错误壳"判据（ISS-070） |
| count | L2.4 | 升级：==COP 实建数（非 ≥ 门，ISS-071 demo 重种信号） |
| root-home | L1.1 | 错误壳探针并入，不单列 |
| form-render | L3.3 | 升级为四表单面逐字段 |
| empty | L2.2 | 保留 |
| template | L2.3+L1.3 | 升级为正文+meta 双处 |
| demo-contact | L4.4 | 升级为三态表+硬门 |
| faq-answer | L2.1 | 显式保留：FAQ 实质短语 SSR 断言 |
| cta | L4.1 | 升级为真浏览器点击实证 |
| unit / absolute | L2.12 | 显式保留：单位一致+绝对化合规词 |
| markdown / h2-semantic | L2.5 | 升级为全块矩阵 |

## 第一部分：全量检查项（7 层 61 项）

### L1 逐页基础（15 项，每 URL 一行 × 全站 URL）

| # | 检查项 | 判据 | 旧审计 |
|---|---|---|---|
| 1.1 | HTTP + 错误壳探针 | 全 200 **且非 Runtime 错误壳页**（ISS-070：200 也可能是错误页） | ✅http+root-home |
| 1.2 | `<title>` | 每页定制、非裸词模板、**跨页唯一**、≤60 字符 | ✅template 升级 |
| 1.3 | meta description | **静态页（home/about/contact/posts/products 列表）：定制非模板默认（黑名单比对），FAIL-able；动态详情页：服务端回退模板值=已证平台边界（ISS-073），登记 BOUNDARY，最后一次 publish 后复测防重置** | ❌v2 新增 |
| 1.4 | `<html lang>` | 与站点目标语言一致；不一致登记 BOUNDARY（平台修复前不阻断交付）——修复旋钮未知（平台 shell 本身 lang=zh-CN，站点级 locale 待摸索 F7）；旋钮确认前带工单证据登记 | ❌v2 新增 |
| 1.5 | 语言纯净度 | 目标语言页无混杂语言残留/demo 词/拼音占位 | 部分覆盖 |
| 1.6 | 标题层级 | **边界感知**：首页多 H1（carousel/hero 平台行为，ID-0007 C2 已证）=登记制；**非首页 H1 缺失/跳级 = FAIL** | ❌v2 新增 |
| 1.7 | 图片 alt | 非空（机械 slug 值可接受但登记）；描述性深度检查结果登记（img-attrs 属平台 renderer 职责，登记不阻断） | ❌v2 新增 |
| 1.8 | 图片可解码+体积 | 匿名 fetch 200+可解码；>500KB 登记优化建议 | 部分覆盖 |
| 1.9 | console 零未捕获异常 | 逐页浏览器加载，零 uncaught error（"零报错但功能死"本身是诊断信号） | ❌v2 新增 |
| 1.10 | robots.txt 理智 | 可达、无误 noindex、无误 Disallow 全站；meta robots 无 noindex | ❌v2 新增 |
| 1.11 | 混合内容 | 零 http:// 资源引用 | ❌v2 新增 |
| 1.12 | 分页第 2 页 | 内容数 > pageSize 时列表第 2 页可渲染（平台分页行为未知→F8 摸索） | ❌v2 新增 |
| 1.13 | slug 一致性 | 小写连字符、无产品/taxonomy slug 冲突（ISS-084 域） | ❌v2 新增 |
| 1.14 | 404 行为 | 不存在路径行为记录（soft-404=平台边界登记） | ❌v2 新增 |
| 1.15 | 全站链接全量抓取 | 每页提取**全部** `a href`（含正文模块内 tag/breadcrumb/related 卡等非 CTA 链接）逐个验证可达——header/footer/CTA 面（2.6/2.7/4.1）之外的兜底，防漏网死链 | ❌v2 新增（二轮复审 P1-5） |

### L2 逐模块渲染（12 项，20 页面模块+4 全局模块，实建页面逐 type 核对）

| # | 检查项 | 判据 |
|---|---|---|
| 2.1 | 模块 SSR 内容一致 | 每个已用模块 headline/eyebrow/description/media/notes 与 brief/COP 一致；**FAQ 实质短语 SSR 断言显式保留**（faq-answer 映射） |
| 2.2 | 空态模块清零 | related/推荐位无 "No content is available yet." |
| 2.3 | 模板默认文案清零 | 正文+meta 双处黑名单扫描（含 page-header stats 回填，ISS-089） |
| 2.4 | 计数 == COP 实建数 | products/posts 数与 COP 严格相等（不齐=demo 重种信号 ISS-071） |
| 2.5 | 富文本块矩阵 | 正文仅 p/h2/h3/blockquote/加粗；无平铺 link/列表/Markdown 残留 |
| 2.6 | header-dropdown | 导航项逐个可达；CTA label/target 正确 |
| 2.7 | footer-columns | 列链接逐个可达；copyright/brand 正确；socialLinks 空缺=显式决策 |
| 2.8 | **contact-dialog-form-modal** | **点击实证**：真浏览器点击 CTA → dialog 元素出现在 DOM → 表单可见可填可关；仅 href/RSC 引用不算过（2026-09-01 教训：href 有效但组件不挂载） |
| 2.9 | social-floating-button | 已配置：链接/位置/标签正确；未配置：登记决策（B2B 站默认应配，需客户号码） |
| 2.10 | 产品价格显示策略 | B2B 无价站 priceLabel 显示询盘引导文案而非 0/货币占位 |
| 2.11 | 媒体库终态对账 | read_media_library 计数 == media-manifest；demo 种子媒体零残留（delete-demo 不覆盖媒体——F9 摸索清理路径） |
| 2.12 | 单位一致+绝对化词 | units 黑名单零违规；绝对化表述（best/第一/guarantee 类）合规扫描（unit/absolute 映射） |

### L3 表单端到端（9 项——"能用的网站"的核心，旧流程最大盲区）

| # | 检查项 | 判据 | 前置降级 |
|---|---|---|---|
| 3.1 | 表单实体存在 | CMS 侧确认 formSlug 实体存在 | **F1 完成前降级**：以 loadRuntimeFormAction schema 读回 + 真实邮箱可达 + 提交回执 success 为准（ID-0007 C4 路径） |
| 3.2 | 四表单面清单化 | contact 页 / home 内联（ISS-077 同型第二处）/ globals 弹窗 / newsletter（若实建）——逐面绑 slug 核对 | — |
| 3.3 | 渲染逐字段 | label/placeholder/required/topic 选项内容正确（每面一行） | — |
| 3.4 | **提交端到端** | 测试提交（**TEST- 前缀标识**）→ 收件可见（submissions/邮箱，F3 确认路径）→ **通知到达**（或确认平台无邮件通知能力并显式登记）→ 清理（逐条批准） | **授权边界**：客户正式站写入测试询盘需客户知情授权；能测试站（内部测试站）先行的项目以测试站结论为 local_tested，正式站复验后才 live_verified |
| 3.5 | 校验行为 | 空提交/坏邮箱被拒，报错可读 | — |
| 3.6 | 反垃圾 | 平台能力记录（有=验证；无=登记边界） | — |
| 3.7 | 成功反馈可见性 | 提交后成功文案/回执对用户可见 | — |
| 3.8 | 弹窗表单复测 | 弹窗修复后对弹窗面重复 3.1–3.7 | — |
| 3.9 | 通知收件人配置 | 收件地址粒度（站点级/表单级）确认（F6） | — |

### L4 转化路径（8 项，陌生买家视角）

| # | 检查项 | 判据 |
|---|---|---|
| 4.1 | **CTA 点击面枚举实证** | header CTA、hero actions、列表卡按钮、**详情页 CTA 块**（product-detail/material-story-split）、页尾 CTA——逐个真浏览器点击，落到预期页/弹窗（href 值有效 ≠ 可达） |
| 4.2 | 询盘路径完整性 | 首页→产品→CTA→联系方式 ≥3 条路径走通，断一条=FAIL |
| 4.3 | email/tel/WhatsApp 链接 | 格式正确、值真实（非 demo） |
| 4.4 | 真值三态表+硬门 | 电话/WhatsApp/营业时间逐项：真值/demo/缺失 + **确认人+日期**列；**硬门：≥1 条入站渠道实测可用**（真邮箱可达或表单端到端到客户可见收件），否则不许 DELIVERY |
| 4.5 | 404 迷路恢复 | 错误路径能回到导航/首页 |
| 4.6 | 查询参数保留 | CTA 带 `?source=` 等参数落点不剥参 |
| 4.7 | 法律页决策 | Privacy/Terms 平台能力+客户合规要求决策行（GDPR 面；能力未知→F8） |
| 4.8 | rebuild 流量承接 | 重建任务：旧 URL 重定向/流量承接决策行（不做=显式登记） |

### L5 视口与性能（6 项）

| # | 检查项 | 判据 |
|---|---|---|
| 5.1 | 390×844 逐页 | 无横向溢出、hero/表格/卡片不破版 |
| 5.2 | **桌面 1440 逐页**（1920 抽一） | B2B 买家主力视口不破版（ID-0007 B2 双视口保留） |
| 5.3 | 移动菜单 | 汉堡开合正常、菜单项可达 |
| 5.4 | 触控+键盘 smoke | Tab 序合理；弹窗 Esc 可关+焦点回收（弹窗修复后必测） |
| 5.5 | 图片体积格式 | WebP 优先；首屏图 >500KB 登记优化建议 |
| 5.6 | 首屏粗测 | LCP 量级+RSC payload 体积登记制（不设硬门） |

### L6 SEO 与可发现性（7 项）

| # | 检查项 | 判据 |
|---|---|---|
| 6.1 | canonical | 每页存在且自指；平台缺失=BOUNDARY+工单证据（不阻断交付） |
| 6.2 | og: 标签+og:image | og:title/description/image 存在且 image URL 200（详情页平台已注入 og——ID-0007 C3）；缺失=BOUNDARY |
| 6.3 | sitemap 双向比对 | sitemap URL 集 == 实建 URL 集（多或漏均 FAIL；期望集写进 audit-config expectations） |
| 6.4 | favicon/品牌 | favicon 加载、品牌名/logo 全站一致 |
| 6.5 | 内链密度 | 每详情页 ≥2 内链（related/导航卡） |
| 6.6 | 域名与统计决策 | 自定义域名绑定决策行（hash 子域长期可用性）；analytics/访问统计能力登记（客户必问，能力未知→F8） |
| 6.7 | 结构化数据 JSON-LD | Product/Article/Breadcrumb schema 存在性登记（平台注入能力未知→F8）；缺失=BOUNDARY 不阻断 |

### L7 平台边界项（4 项——CMS 不可控，如实分桶，不许静默）

| # | 检查项 | 处置三要件 |
|---|---|---|
| 7.1 | 弹窗组件不挂载 | ①证据包（点击探针输出+RSC 对照+console 状态）②临时补偿（CTA 直链或浮钮）③**渠道动作**：平台工单渠道当前未建立——显式登记"渠道未建立"并知会 Tony（母库 OQ-TOOL-0004），修复后 L2.8/L3.8 复测；跨时间跟踪落 HANDOFF 下一步，不只写一次性 DELIVERY |
| 7.2 | soft-404 / og / canonical 缺失 | 同上三要件；soft-404 附 SEO 收录风险口径 |
| 7.3 | 正文图片 alt renderer / CDN 缓存延迟 | 沿用 RUNBOOK 既有登记；复测时序：修复后等 CDN 5-10s 再验 |
| 7.4 | 平台能力探索缺口 | 多语言 hreflang / analytics / 法律页 / 分页 / 自定义域——F8 统一摸索，结论回填本表 |

**原 ⛔ 条目（L1.4 lang / L1.7 alt / L6.1 canonical / L6.2 og / L6.7 JSON-LD）已按 Tony 2026-09-01"可"解锁为 BOUNDARY 语义**：检查→登记证据→不写 FAIL 拦截交付；平台缺陷走 L7 三要件。

## 第二部分：对抗完善验收流程（四轮，FAIL 即修，修复必回归）

```text
轮1 机器审计（底座 = site_pipeline.py audit 13 项不删只保）
     计划扩展（约 7 项，独立代码批落地+自测）：lang（BOUNDARY 登记）、meta 黑名单、
     img alt 非空、sitemap 双向比对、404 探针、console 探针（浏览器侧归轮2）、混合内容
     → audit-config 模板补 expectations 字段（lang、meta 黑名单、期望 sitemap 集、期望计数）
轮2 AI 逐项复核（本清单 61 项逐行四态：PASS/FAIL/BOUNDARY/PENDING-CLIENT）
     证据落盘 70_evidence/acceptance-v2.md（每项证据指针：截图/DOM 输出/链接表）
     浏览器实证在本轮做（audit 纯 HTTP 层做不了点击/console）
     FAIL 项当日修复后该项复测
轮3 独立对抗审查（新开主会话的独立 reviewer，与建站执行者不同身份；
     引用 OUTSIDER-REVIEW.md DOC-008 机制）
     攻击 A：扮演陌生买家，落地→询盘全路径找断点（浏览器实证可用）
     攻击 B：攻击清单本身——本轮漏检维度
     攻击 C：内容事实核对（规格/联系方式/品牌表述 vs 事实源）
轮4 修复复审（回归是硬要求——已证回归链：ISS-070 主题重激活断 root-home、
     ISS-071 重建重种 demo、ISS-073 publish 后 description 重置、ISS-003 globals 单页提交 7 页漂移）
     ①任何修复后重跑轮1 全量机器 audit（近零成本）
     ②受影响层关联项抽测 + 与被改模块同页的其他模块
     ③顺序铁律：描述类字段更新必须发生在最后一次 publish 之后并复测（ISS-073）
     ④CDN 缓存 5-10s 后再验
     全项 PASS 或 BOUNDARY/PENDING 显式登记 → DELIVERY 首行列 PENDING-CLIENT 清单 → Tony 签收
```

**铁律**：①任何 FAIL 不许降级 WARN 带病交付；②BOUNDARY 必须带三要件（证据包+临时补偿+渠道动作或"渠道未建立"登记并知会 Tony），不许裸露；③PENDING-CLIENT 必须 DELIVERY 首行显式列出且不突破 4.4 硬门；④轮3 reviewer 与建站执行者不得同一身份。

## 第三部分：模块与表单摸索计划（F1–F9）

| # | 摸索问题 | 方法 | 产出 |
|---|---|---|---|
| F1 | 表单实体集合是否存在（forms collection/API）；formSlug（如 contact-inquiry）平台内置 vs 站点可建 | 测试站后台只读探查+read_lists 试探+表单管理页 RSC | FORMS.md 合同页 |
| F2 | 能否自建表单/自定义字段/topic 选项 | 测试站最小实例 | 同上 |
| F3 | 提交链路：server action → 存储（submissions 收件箱？平台待补——RUNBOOK §9 已记）→ 通知机制与收件地址 | 测试站提交 1 条全程追踪（TEST- 前缀） | 同上+issues 回填 |
| F4 | 提交数据导出/清理路径 | 测试站探查 | 同上 |
| F5 | 弹窗表单与页面表单是否同 slug 同收件 | 测试站双端各提交 1 条比对 | 同上 |
| F6 | 通知收件人配置粒度（站点级/表单级） | 测试站配置面探查 | 同上 |
| F7 | `<html lang>` 控制旋钮（站点 locale/主题/平台层？） | 后台设置面+创建参数回读 | FORMS.md 附节或 issues |
| F8 | 平台能力面：自定义域/analytics/法律页/列表分页/多语言 | 测试站逐项探查 | L7.4 回填 |
| F9 | 媒体库 demo 种子清理路径（delete-demo 不覆盖媒体） | 测试站受控验证 | issues 回填 |

### 模块行为矩阵补全

以 MODULES.md 注册表（37 种）为**全量清单**逐 type 对账：本站未实建模块 → 测试站最小实例实测前端行为，回填 MODULES.md"前端显示"列与坑位。优先级：交付中高频使用的 carousel-campaign / newsletter-inline（提交链路并入 L3.2）/ social-proof-quotes / product-comparison / location-map-interactive（外部地图依赖）/ faq-accordion（开合交互）/ recommended-* 空态阈值 / 全局 4 模块"按页存储改一次 7 页重交"边界实测。

### 新坑回填纪律

摸索中发现的平台行为/缺陷全部回填 `index/issues.tsv`（fixed/boundary/pending + 客户标识去敏），保持 registry verify+gen PASS；四类漏网问题已回填 ISS-092..095。

---
*本清单自身接受对抗：使用中发现新盲区 → 回填并 bump 版本，教训写入 sources。条目计数改动必须同步标题/§一/轮2 三处口径（防项数漂移反模式）。*
