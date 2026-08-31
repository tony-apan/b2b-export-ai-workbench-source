---
title: "AllinCMS 建站知识索引"
type: "index"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
---

# AllinCMS 建站知识索引（自动生成，勿手改；数据源=同目录 *.tsv）

> 生成时间：2026-08-31｜查询：`python3 registry_tools.py find <词>`｜更新后跑 `verify` + `gen`

## 1. 文档 / 脚本 / 模板（doc-registry.tsv）

| id | kind | name | path | status | 说明 |
|---|---|---|---|---|---|
| DOC-001 | doc | 工具包总览（读写方案+换机指南） | `../README.md` | current | 零依赖纯接口工具包：写=server action，读=RSC 流；端点矩阵；CLI；换电脑(mac/win)指南；Runtime Forms 章节 |
| DOC-002 | doc | 0→1 建站上线 SOP | `../ONBOARDING-PIPELINE.md` | current | 资料→brief→validate→generate→执行→globals 全站→验收三步；参考 ID；坑清单；换机快速开始 |
| DOC-003 | doc | 单页模块规范（Blocks Library） | `../MODULES.md` | current | 20 种页面模块+4 全局模块 schema/嵌套结构/前端显示映射/服务端回填坑/模板词自检表 |
| DOC-004 | doc | 模板资产使用说明 | `../templates/README.md` | current | 真实读回产物作字段参照：产品/文章 payload example、页面三件套、brief-schema |
| DOC-005 | doc | 索引体系说明（本目录） | `INDEX.md` | current | 三张 TSV 主索引+自动生成的阅读页；查询/更新规则见文内 |
| SCRIPT-001 | script | AllinCMS 纯接口客户端 | `../allincms_api.py` | current | 零依赖客户端：写(站点/分类/标签/媒体/产品/文章/设计器)+读(RSC 9 路+CLI 8 命令)；action id 常量表 |
| SCRIPT-002 | script | 模块构建器 | `../allincms_blocks.py` | current | hero/carousel/category/feature/product/material/proof/news/faq/newsletter/contact+公司页/联系页 builder+page_document 组装 |
| SCRIPT-003 | script | 建站流水线工具 | `../site_pipeline.py` | current | validate(含 3/4 数量门)/generate/check(模板词)/diff(readback)/gate(一键门)/contact(demo 联系方式门)/audit(13 项一体对抗审计+JSON 报告：http/count/root-home/form-render/空态/模板词/demo联系方式/FAQ答案SSR/真实CTA/单位/绝对化/Markdown/h2语义) |
| SCRIPT-004 | script | action id 扫描器 | `../scan/scan-actions.py` | current | 从页面/工作台 chunk 扫 createServerReference 得当前部署 action id |
| SCRIPT-005 | script | 索引工具（registry） | `registry_tools.py` | current | verify(引用存在/id 唯一/枚举合法)/gen(生成 INDEX.md)/ls/find(关键词查询)/add(安全追加) |
| TPL-001 | template | 产品 payload 参照 | `../templates/product-payload-example.json` | current | defaultValues 全字段(name/slug/description/order/media/mediaList/categories/tags/specifications/content) |
| TPL-002 | template | 文章 payload 参照 | `../templates/post-payload-example.json` | current | defaultValues 全字段(title/slug/excerpt/order/coverImage/categories/tags/content Slate) |
| TPL-003 | template | 首页三件套参照 | `../templates/home-page-example.json` | current | pageDoc+globals+themeConfig 完整示例（11 模块真实结构） |
| TPL-004 | template | 公司页三件套参照 | `../templates/about-page-example.json` | current | about-intro/story/stats/values/team 真实结构 |
| TPL-005 | template | 联系页三件套参照 | `../templates/contact-page-example.json` | current | header/info/map/form 真实结构 |
| TPL-006 | template | brief 字段骨架 | `../templates/brief-schema.json` | current | 公司/产品资料→brief.json 的字段结构与说明 |
| EV-001 | evidence | 接口要点全集+踩坑集 | `../../70_evidence/THERMOS-INTERFACE-REPORT.md` | current | 全 action 端点/payload/返回/错误模式；RSC 端点矩阵；对抗要点 |
| EV-002 | evidence | 工具包验证报告（对抗记录） | `../../70_evidence/KIT-VERIFICATION.md` | current | 交付物+实测验证表+RSC 攻破+回填规则+观察项 |
| EV-003 | evidence | 站点上线审计报告 | `../../70_evidence/SITE-LAUNCH-AUDIT-20260829.md` | current | 全站审计：已解决/平台边界/表单链路待验证+证据指针 |
| EV-004 | evidence | template-residue gate 报告 | `../../70_evidence/template-residue-gate.json` | current | skill 自带 gate 输出：7 路由/19 术语/0 命中 pass=true |
| EV-005 | evidence | 首页 document RSC 快照 | `../../70_evidence/rsc-home-doc-rsc-read.json` | current | 设计器接口读回的首页三件套原始快照 |
| EV-006 | evidence | 清空前站点证据 | `../../70_evidence/sites-before-delete.json` | current | 7 站删除前记录（totalDocs 7→0 依据） |
| CAN-001 | doc | 上线验收合同（ID-0007） | `../../../../../../../sub-libraries/website-content-ops/PLAYBOOKS/id-0007-site-launch-acceptance.md` | current | 三层验收(A 内容/B 前端/C 平台边界)+Runtime Forms 链路+判定门槛 |
| CAN-002 | doc | 实站操作对抗审查（ID-0006） | `../../../../../../../sub-libraries/website-content-ops/PLAYBOOKS/id-0006-live-allincms-adversarial-review.md` | current | capability gate/Plan A-B/双审门槛/可分享 Skill 硬条件 |
| CAN-003 | doc | 来源驱动建站 SOP（ID-0005） | `../../../../../../../sub-libraries/website-content-ops/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md` | current | Source Extraction→事实账本→desired state→动态发现→精确 diff→授权→串行执行 |
| IDX-001 | index | 索引阅读页（自动生成） | `INDEX.md` | current | 由registry_tools.py gen 生成；勿手改 |
| IDX-002 | index | 文档/脚本/模板 registry | `doc-registry.tsv` | current | 主索引（本表）：每行一个可复用资产+状态+脚本+用途 |
| IDX-003 | index | 问题/教训 registry | `issues.tsv` | current | 问题库：现象/根因/修复/规避/文档/脚本/证据+状态(fixed/boundary/pending) |
| IDX-004 | index | 模块 registry | `modules.tsv` | current | 模块库：type/分组/构建函数/文档/前端显示/状态 |
| TPL-007 | template | 交付清单模板（delivery-manifest） | `../templates/delivery-manifest.md` | current | 建站验收后生成交付清单（链接+说明+核验表）的模板；含公开链接表/内容清单/核验记录/已知事项 |
| EV-007 | evidence | 皮筏艇站交付清单 | `../../70_evidence/DELIVERY-KAYAK-20260829.md` | current | Demo 站全量交付清单范例（13 链接+核验表+gates） |
| EV-008 | evidence | 皮筏艇站清理前证据 | `../../70_evidence/sites-before-delete-kayak.json` | current | 清空前站点记录（1 站）+ 删除后 0 站 |
| TPL-008 | template | 前置资料收集清单 | `../templates/client-input-checklist.md` | current | 建站前向用户收集 5 项必填（品牌名/昵称职位/邮箱电话WA/地址/资料文件）+ 解析提炼流程 + 版权合规 + 确认点 |
| TPL-009 | template | 建站必备内容清单 | `../templates/site-content-checklist.md` | current | 全站内容=字段级映射（品牌/分类/产品/文章/公司/联系/首页/素材/替换清单/勿漏检），AI 规划与核验对照用 |
| EV-009 | evidence | 改进清单（对抗分析） | `../../70_evidence/IMPROVEMENT-PLAN-20260829.md` | current | 本批修复+模块库补全+后续标准动作+新问题+待办+验收判据建议 |
| TPL-010 | template | 文章对抗审查清单 | `../templates/article-adversarial-checklist.md` | current | 发布前逐问：目标客群/痛点来源/证据边界/反空洞/SEO/自动化门；非空答才可发 |
| TPL-011 | template | 产品/单页对抗审查清单 | `../templates/page-adversarial-checklist.md` | current | 逐区块前向审查（客户喜欢吗/痛在哪/为什么喜欢/能否更强）：首屏3秒/利益化/痛点/差异化/视觉层级/心理 |
| TPL-012 | template | 图片对抗审查清单 | `../templates/image-adversarial-checklist.md` | current | 硬性门(分辨率/大小/许可/alt)+审美(主体/构图/一致性/裁切)+心理(场景/证据/情绪匹配) |
| TPL-013 | template | SEO 检查清单 | `../templates/seo-check.md` | current | 每页 title/desc/H1层级/slug/alt/模板词/空态/og/发布后登记；平台边界标注不误报 |
| SCRIPT-006 | script | 图片硬性门检查 | `../image-check.py` | current | 分辨率/文件大小/格式/alt/同尺寸重复检测（零依赖 jpg/png 头部解析） |
| SCRIPT-007 | script | 友商监控工具 | `../../../../../client-task/40_competitors/competitor-watch.py` | current | 每友商一目录：add(初始化 sitemap.tsv+snapshots)/scan(对比输出 new/updated/removed)/watch(批量)/report；TSV 主表+md profile |
| SCRIPT-008 | script | 文档解析能力检查 | `../doc-capability-check.py` | current | 环境门：检查 pypdf/python-docx/python-pptx/openpyxl/pdftotext + 安装建议 + self-test；分享 skill 前必跑 |
| DOC-006 | doc | 友商自动发现流程 | `../../../../../client-task/40_competitors/COMPETITOR-DISCOVERY.md` | current | daily 搜索语法+domains.tsv 去重表+探 sitemap+promote/scan 闭环；发现用 web_search 脚本登记 |
| TPL-016 | template | 站点登记表（多公司多网站） | `../../../../../client-task/site-registry.tsv` | current | company→sites 映射：每品牌一 AllinCMS 站；sites/<slug>/ 目录层约定 |
| EV-010 | evidence | 双审记录（SOL+TERRA） | `../../../../../client-task/70_evidence/DUAL-REVIEW-20260829.md` | current | 双审机制+本轮执行状态+客观门结果（路径/编译/列一致/凭据0/超时/上手）+调优 |
| SCRIPT-009 | script | 依赖安装器 | `../install-deps.py` | current | 检测 runtime/docs-parse/canonical 三层依赖 → --yes 一键 pip 安装 → --verify 复检；跨平台 |
| DOC-007 | doc | 安装与依赖指南 | `../SETUP.md` | current | 依赖全景表（runtime 零依赖/docs-parse 选装 4 包/canonical 选装 Node/截图 Chrome）+ 安装步骤 + mac/win/linux 命令 + 常见问题 + 干活前顺序 |
| TPL-017 | template | 依赖清单 requirements | `../requirements.txt` | current | 分层 requirements（runtime=空，docs-parse 4 包标注，canonical Node 标注）；提示阅读 SETUP.md |
| DOC-008 | doc | 旁观审查机制 | `../OUTSIDER-REVIEW.md` | current | 无上下文独立 AI 审查回落质量（接手性/完整性/自证/追溯/矛盾/闭环/可执行）7 维 + 触发时机 + 输出回填 |
| TPL-018 | template | 会话回落模板 | `../templates/conversation-writeback.md` | current | 即时回落（新坑→issues）+ 收尾回落（HANDOFF 段格式）+ 回落质量自检 |
| TPL-019 | template | 内容数量标准 | `../templates/CONTENT-MINIMUM.md` | current | 美观基线（产品≥3/文章≥4）+ 命中依据 + 用户话术 + 降级策略；validate 与 gate 已内置 |
| TPL-020 | template | 文章创作逻辑（软文逻辑总结） | `../templates/article-writing-logic.md` | current | 六段式骨架(H2起)/7 钩子库/代入感三件套/防空洞自检/子agent完善流程；与 ID-0001/checklist 分工表 |
| TPL-021 | template | 空白子 agent 审稿 prompt | `../templates/ghostwriter-review-prompt.md` | current | 可直接复制给空白 subagent 的评审 prompt（4 维评分/最弱3处/钩子检查/禁加事实） |
| TPL-022 | template | 品牌视觉规则 | `../templates/visual-design-rules.md` | current | 视觉方向/可落地规则表(Quick Answer·参数锚点·callout 标签·真链接 CTA·图片来源·边界声明)/平台边界列表/CTA 文案原则/品牌红线 |
| DOC-009 | doc | 写作模块入口（WRITING-INDEX） | `../writing/WRITING-INDEX.md` | current | 写文章统一入口：五步调用链（素材→骨架→成稿→评审→发布）+全仓写作资产路由表；写文章先读此文件 |
| DOC-010 | doc | 文章循序渐进规范（PROGRESSION） | `../writing/PROGRESSION.md` | current | 四阶段递进模型（S1认识→S2理解→S3判断→S4决定）+每阶段检查（承上/启下/密度/术语/无跳级/边界一致/CTA时机）+递进词库+反模式+5问自检 |
| SCRIPT-010 | script | 写作模块调用器 | `../writing/writing-module.py` | current | outline(brief→六段式骨架+阶段标注+钩子提示)/check(渐进机器检查三档：缺S1/S4=❌,波动/衔接/术语/边界/CTA=⚠️) |
| DOC-011 | doc | 接口模块入口（API-INDEX） | `../api/API-INDEX.md` | current | 接口独立模块入口：模块图（写=server action/读=RSC）/端点矩阵/action id 表/快速调用 copy-paste/常见错误速查(ISS 引用)；调接口先读本页 |
| TPL-014 | template | 接口快查表（api-ref tsv） | `../api/api-ref.tsv` | current | 机器可读快查：21 项操作=method/endpoint/action_id/payload 摘要/返回/坑引用/示例——grep 即用；换部署更新 action 列 |
| DOC-012 | doc | 正文格式规范（FORMAT-SPEC） | `../writing/FORMAT-SPEC.md` | current | 正文格式单一真源：块清单(原生h2/h3/blockquote包裹/leaf)/id规则/范文章节/禁用清单/工具链；凡未列=先 format-lab 再用 |
| TPL-015 | template | 正文格式快查（format-ref tsv） | `../writing/format-ref.tsv` | current | 机器可读块表：format|valid|render_semantic|render_style|json_shape|usage|pitfall 19 行——grep 即用 |
| DOC-031 | doc | 新站改造清单（166 字段逐项改什么） | `../templates/new-site-customization-checklist.md` | current | 新站建站时逐字段把模板换成客户内容；每条含 demo 值+替换示例+后果 |
| DOC-032 | doc | 新站一条龙总入口（13 步 0→上线） | `../NEW-SITE-ONEPASS.md` | current | 拿到客户资料后从 0 到上线的一条龙执行链 |
| DOC-033 | script | demo 种子清理脚本 | `../delete-demo-content.py` | current | createTheme(default) 重种的 3+3 demo 内容清理 |
| DOC-034 | doc | API 摸索流程（平台更新后 7 步重发现） | `../API-DISCOVERY.md` | current | 部署升级导致 action id/schema/模板变化时，AI 按此流程系统性重新摸索 |
| DOC-035 | doc | RUNBOOK：任何人零上下文建站手册 | `../RUNBOOK-ANYONE.md` | current | 实测事实与回落库；⛔ 禁令横幅；13 项审计口径；新坑回填流程 |
| DOC-036 | doc | NEW-SITE-ONEPASS 13 步一条龙 | `../NEW-SITE-ONEPASS.md` | current | 资料→brief→COP→建站→内容→主题→审计→交付 13 步全流程 |

## 2. 问题 / 教训（issues.tsv）

| id | status | category | 问题 | 根因 | 修复 | 规避 | 文档 |
|---|---|---|---|---|---|---|---|
| ISS-001 | fixed | server-backfill | props 未提供的字段被服务端用模板默认值回填（含模板文案与假链接：hero campaignPills/actions/serviceItems、contact-info socialLinks=Instagram/LinkedIn、company-story note/noteLabel、about-intro caption/fit） | 设计器 commit 对缺失字段应用模块模板默认 | 所有可显示字段显式传（可空数组/空串）；提交后 readback 深度 diff | 只允许 formSlug 空串与 columnCount=N 这类无害回填 | DOC-003 |
| ISS-002 | fixed | server-backfill | header 导航 children 传元组列表被服务端丢弃并回填模板 Bags | 构建器未递归转换 children | _naav_entry 递归转 dict 后重交并 readback 验证 | children 必须 dict 数组 | DOC-003 |
| ISS-003 | fixed | designer | globals 按页存储：单页 commit 只更新该页，其他页仍显示旧 footer/导航 | 平台数据模型 globals 随 page 存储 | read_pages 全页→每页 readback document 原样回传+新 globals 重交 save+publish | 全站全局变更必须全页重交 | DOC-002 |
| ISS-004 | fixed | media | 媒体 URL 不带扩展名导致运行时 404 | 资产 URL 后缀必须保留 | URL 必须带 .jpg/.webp；上传后从响应取完整 URL | 写任何 media 字段前检查扩展名 | DOC-001 |
| ISS-005 | fixed | taxonomy | categories/tags 写入与读回不对称：写 id 字符串数组，读回 {id,name} 对象数组 | API 映射不一致 | 写用 id 数组；读回按对象数组解析 | 页面引用分类用 slug query 不用 id | DOC-001 |
| ISS-006 | fixed | action-id | action id 随部署变化；用错 id 静默返回 {} 不报错 | 每部署 chunk 内 createServerReference 生成新 id | scan-actions.py 重扫并核对响应非空 | 换部署/升级必重扫 action id | DOC-001 |
| ISS-007 | fixed | taxonomy | 产品误挂文章分类导致产品页分类错乱 | posts/products 分类体系独立 contentType 不同 | 产品分类 contentType products；产品 categories 用产品分类 id；页面 target 用产品分类 slug | 产品是产品 文章是文章 | DOC-002 |
| ISS-008 | fixed | taxonomy | create_category2 缺省 cover 报 validation error | cover 字段 schema 必填 null 合法 | payload 显式 cover=None 或完整对象 | 建分类永远显式传 cover | DOC-001 |
| ISS-009 | fixed | media | upload_media multipart 普通字段当文件拼导致 TypeError | str bytes 类型冲突 | 支持 fname=None 普通字段（0 字段放 JSON 文本） | 表单字段区分文件/普通 | DOC-001 |
| ISS-010 | fixed | rsc | 设计器 RSC 的 initialPayload 双层包裹 | RSC 组件 props 结构 | 取 ip[initialPayload] 再解 page.document/globals/themeConfig | 解析器统一 unwrap | DOC-001 |
| ISS-011 | boundary | platform | soft-404：不存在路径返回 HTTP 200（Allin CMS Runtime shell；favicon.ico 亦 200 text/html） | 平台 fallback 行为，工作台无配置入口 | 记录不接受误报；有 SEO 要求向平台反馈 | 不在本站点内容侧浪费工时 | DOC-003 |
| ISS-012 | boundary | platform | 首页/列表页无 og；其余前端边界项属 ⛔ 禁令范围（不展开） | 平台模板行为（详情页由平台按记录注入 og） | 接受；详情页 og 可用；不阻塞交付 | 不当作内容 bug | DOC-003 |
| ISS-013 | boundary | platform | 首页多 H1（carousel slide 与 hero 均输出 h1） | 模块渲染固定 tag | 内容策略：首屏主标题承担主语义 | 不误报为 SEO 失败 | DOC-003 |
| ISS-014 | boundary | platform | contact 表单 SSR 无 form 元素（客户端组件 hydration 后渲染） | 平台渲染架构 | 接受；无 JS 场景不可用 | 记录即可 | DOC-001 |
| ISS-015 | boundary | platform | contact 页 map tile 加载失败显示灰块 | 地图依赖外部 tile 服务 | 接受；数据正常 | 记录即可 | DOC-003 |
| ISS-016 | pending | forms | submitRuntimeFormAction 接口级实测 HTTP 500（digest 753112626）；payload [{formSlug,values}] 与浏览器一致 | 假设 demo 邮箱不可收件/需浏览器同源会话；未闭环 | 上线前换真实邮箱并浏览器实提一次 | 通过前不得宣称表单链路 OK | DOC-001 |
| ISS-017 | fixed | copy | About 页图注 800ml 与产品 500ml 矛盾 | 文案与产品数据未交叉核对 | 发布前全站数字一致性自检（容量/参数/年份） | 跨模块数字必须一致 | DOC-003 |
| ISS-018 | fixed | copy | demo 联系方式进入公网（demo 邮箱/电话/地址/wa 号码与 synthetic 标注） | 占位值未被替换清单拦截 | 上线前 demo 值替换清单核对 A3 | 正式站必换真实可收件邮箱 | DOC-002 |
| ISS-019 | fixed | media | upload_media 的 media_urls 返回累积全量（每次含历史所有 URL），非本次新增 | 解析器取响应 assets 列表全量 | 按差值取本次新增 URL（本次集 - 上次集），或直接取列表最后一个/去重比对 | 上传后不要直接用全量列表作为本次资产 URL | DOC-001 |
| ISS-020 | fixed | payload | 产品/文章 create 缺 siteId 报 validationErrors.siteId expected string | create 动作需要 payload 内显式 siteId（并非由路径推断） | create/update/publish payload 一律显式带 siteId | 写 payload 前检查 siteId 在场 | DOC-001 |
| ISS-021 | fixed | payload | media 写入格式为扁平 {name,alt,type,source,url}；readback 才是包裹 {type,value:{...}} | 写读格式不对称（与 categories 相同教训） | publish/create 用扁平；解析读回用 value 包裹 | 写扁平、读解包 | DOC-001 |
| ISS-022 | fixed | payload | create 后 draft slug 被替换为时间戳数字（1787...），publish 时带正确 slug 会纠正 | 草稿动作自动生成 slug | publish/update payload 必须带正确的 slug 与 productId/postId | 不要用 create 返回的 slug 当作最终 slug | DOC-001 |
| ISS-023 | fixed | media | Wikimedia 图片下载 403：自定义 UA 被 CDN 拒（API 成功但 upload.wikimedia.org 拒绝） | Wikimedia 需浏览器 UA | 下载用 Mozilla/Chrome UA；upload 侧同理 | 爬素材必须带浏览器 UA | DOC-001 |
| ISS-024 | fixed | misc | create_category2 偶发事务号不匹配（Given transaction number N does not match active M） | 服务端事务错位（并发/时序） | 原样重试一次即成功 | 重试而非换参数 | DOC-001 |
| ISS-025 | fixed | frontend | 详情页出现 No content is available yet. 空态 | related 推荐区（product/post-related-grid）在目录单品/单篇时无推荐项即空态 | 删除详情模板页 related 模块（document 可编辑）或保持目录≥2 项 | 新增站时详情模板页纳入检查；空态扫描必跑 | DOC-003 |
| ISS-026 | fixed | launch | 详情/列表模板页（Post/Product 页 document）未纳入上线检查 | 验收范围只覆盖 3 个内容页 | 全站 7 页（含模板页）readback+公网空态扫描 | 模板页 document 改动后也要 readback | DOC-003 |
| ISS-027 | fixed | process | 前置资料未收集就开工导致 demo 值进公网 | 流程缺前置检查 | client-input-checklist 固化（品牌/昵称职位/邮箱电话WA/地址/资料文件）缺项阻塞 | 任何新站先发资料收集清单 | DOC-002 |
| ISS-028 | fixed | double-review | TERRA P0: competitor-watch add/scan 裸调 fetch（HTTPError 未捕获）→ daily 整批崩溃；promote 对 add 失败仍置 monitored=y | urlopen 对 4xx 抛异常使 status!=200 死分支；promote 未看 add 返回值 | fetch 统一 catch 返回 (code,'')+4MB cap；add 返回 bool；promote 成功才标记 y（失败置 add-failed） | 异常路径每日运行必测 | DOC-006 |
| ISS-029 | fixed | double-review | TERRA P0(上手): 查询命令路径不存在（00_shared 无 interface-kit 分发）；任务目录为空（无 TASK/HANDOFF） | 权威副本未分发；任务真源只留在 client-task 任务目录 | interface-kit 复制到 customer-runtime/00_shared/；client-task/30_tasks/<task>/ 补 TASK.json+HANDOFF.md；README 指针修正 | 新客户先分发 00_shared 再写 README | DOC-002 |
| ISS-030 | fixed | double-review | TERRA P1: site-registry.tsv 伪 TSV（#注释/| 行混入）；scan 从 profile.md 抠 URL；parse_sitemap 不支持 sitemapindex | 表约定不严；真源未统一 | TSV 纯化（注释移 site-registry.notes.md）；scan 真源=domains.tsv.sitemap_url；parse 兼容命名空间+index（子 sitemap 由 promote 二次收集） | 表结构用真实 tab 头；多来源优先级写死 | TPL-016 |
| ISS-031 | fixed | outsider-review | 旁观审发现：HANDOFF/README 计数过期（49→51、18→27、25→33）与快速入口路径错误（interface-kit/PLAYBOOKS 不存在） | 回填后未刷新计数；路径写错层级 | 计数改“以 verify/ls 为准”；验收合同补全仓根路径 sub-libraries/website-content-ops/PLAYBOOKS/id-0007；wiki 命令注明仅 client-task 可用 | 任何文档写具体数字/路径前核对其来源 | HANDOFF.md |
| ISS-032 | fixed | outsider-review | 旁观审发现：TASK.json status=COMPLETE 与未决项矛盾 | 状态语义过粗 | status 改 content_complete_launch_pending_real_email + open_items_summary | 机器真源字段须与未决一致 | TASK.json |
| ISS-033 | boundary | platform | 表单提交 submitRuntimeFormAction 服务端 500（digest 753112626）——平台缺陷确认 | 已用真实邮箱(reviewer@example.com)+浏览器同源 fetch+精确 payload 三盲测仍 500；排除 API 用法/邮箱因素 | 向平台支持反馈；等待修复或使用替代询盘通道 | 任何站的表单均可能受影响——上线前实提一次（ID-0007 D-7），失败则记录平台缺陷 | CAN-001 |
| ISS-034 | fixed | content | Slate 支持矩阵已完成（3 轮实证）：白名单 heading/paragraph/bold/italic/numbered-list/blockquote | 渲染器仅实现极简块（link/image/无序列表不渲染或丢失语义） | 按矩阵白名单使用；禁用 ❌ 块；文档 MODULES 三·五 | 写正文前查矩阵（MODULES 三·五） | DOC-003 |
| ISS-035 | fixed | contact | 联系方式必须以用户提供为准并全站替换（138-0000-0000 示例：电话+WhatsApp） | demo 值散布 contact 页/首页/全站 globals 浮钮 | 用户提供→替换→contact 门扫描验证（contact-scan）→未提供项列入交付清单 | 联系方式必填收集；替换后 contact 门必跑 | TPL-009 |
| ISS-036 | fixed | copywriting | meta/流程备注泄漏进读者正文（(Guide is synthetic...)）；footer demo 标注在正式站亦伤信任 | 创作与审核未区分内部备注与读者可见文本 | 正文删除内部备注（移入交付/元数据）；正式站 footer copyright/systemNote 的 Demo/qualification 声明必须替换为真实版权 | 写作六段式不放 meta 备注；正式站发布前扫 footer 声明 | TPL-020 |
| ISS-037 | fixed | copywriting | 文章缺层次/钩子/CTA（子 agent 评审 2/2/2/3 分 NEEDS_REWRITE） | 未按六段式逻辑写作 | 按 article-writing-logic 六段式重写（标题钩+场景引言+痛点代价+阶梯+CTA）并发布 | 出稿必按六段式；发布前跑 ghostwriter 评审 | TPL-020 |
| ISS-038 | fixed | format | Slate heading 实际不渲染 h2（此前矩阵误判：页面唯一 h2 是 footer 品牌区） | 矩阵验证用全局 tag 计数，未做正文区定位 | format-lab 逐 marker 精查；MODULES 矩阵改正（heading❌）；改用加粗段首做视觉标题；格式判定改动前必须重测 | 正文视觉层=加粗段首+数字加粗；任何矩阵结论改动先 format-lab | TPL-020 |
| ISS-039 | fixed | format | CTA 用 Markdown [text]\(url\) 语法渲染成纯文本（用户截图暴露） | 文案层误用 Markdown 而 Slate 不支持 | 正文禁 Markdown（方括号圆括号/#/** 语法）；CTA 自然语言；链接只进模块字段；写作逻辑加格式规则节 | 出稿自检无 Markdown 残留；ghostwriter 3 项新检查之一 | TPL-020 |
| ISS-040 | fixed | frontend | 正文排版难受（段落无间距/无标题/内链丢失） | Slate 正文无间距 CSS 且 heading 不渲染；related 模块曾被删（防空态） | 空段落分隔+段首加粗+恢复 related（数据足后）+禁 Markdown；CSS 层平台边界记录（ID-0007 C8） | 写文章按五·五格式规则；数据 ≥3 时保留 related | TPL-020 |
| ISS-042 | fixed | seo-copy | 第三方评审55分：CTA非真链接/正文缺语义层/数据绝对化/Quick Answer缺失/标题意图不稳 | 正文 CTA 只有文字；参数绝对化；未用 callout 做决策模块 | 详情页模板加产品推荐模块(真链接)；Quick Answer+承重公式+边界声明+图片来源callout；标题SEO化；五·四规则固化 | 专业决策页五件套：Quick Answer/公式/边界/来源/真链接CTA | TPL-020 |
| ISS-043 | boundary | platform | 文档语言层平台边界（⛔ 禁令范围，不展开） | 平台行为（第三方评审 2026-08-29 P0 实锤） | ⛔ 禁令：不检查、不报告 | 不参与站内可修判定 | ID-0007 A6 |
| ISS-044 | fixed | seo-copy | 评审2轮：callout 组件自带 emoji、产品模块混列3品、咨询CTA无归因、almost always 绝对化、单位不统一、缺 SHORT VERSION | 组件默认图标不可控；模块选型不当（showcase 全列表）；CTA 未带 source | 弃 callout 改纯文本标签段；产品推荐改单主品+咨询归因双卡(source=slug)；语言进一步边界化；单位全站统一空格；加 THE SHORT VERSION 决策闭环 | 规则与线上一致：纯标签/单主品/归因 CTA/单位模板 | TPL-020/TPL-022 |
| ISS-045 | fixed | visual-brand | 评审4轮：主图含第三方品牌标识(Aqua Bound桨)+构图杂+无产品证明力；标题与正文预期差；缺边界声明/FAQ/作者信息 | 选图未按品牌规则(无logo/主体清晰)；内容未含场景边界 | 换 Hoover PD 素材(双人皮艇主体清晰无logo/Andrew Cattoir PD)；加 calm-water 边界声明段；详情页加 FAQ 模块(4问有边界答案)；作者=Product Team(平台字段缺失已记) | 选图规则入库：无商业 logo/主体清晰/移动端裁切不丢主体；写作规则：场景边界声明必带 | TPL-022 |
| ISS-046 | boundary | platform | Demo 站 noindex 无法实现（工作台无 robots/noindex/seo 配置字段） | 平台未提供 SEO/索引开关 | 记录 BLOCK+平台反馈；演示站保留 demo 声明（合规）；正式站需平台支持或清理文案 | 站长决策：demo vs 正式 | ID-0007 |
| ISS-047 | fixed | verification | FAQ 答案初始 HTML 可见性——事实复核：**PASS**（4 答案首句全部 SSR；评审猜测不成立） | 未做事实级验证即交付 | 事实级复核法（HTML 搜索答案首句+aria 检查）纳入验收 | 任何模块'完成'声明前必跑事实复核 | MODULES |
| ISS-048 | fixed | verification | FAQ 可爬取性——PASS（SSR 全答案）；aria-controls=0 为组件实现（记录） | 同上 | 以初始 HTML 内容为准判定可爬取；控件语义待平台 | 验收以初始 HTML 为准 | MODULES |
| ISS-050 | fixed | visual-brand | 主图 alt 塞版权信息且与多船场景不符 | alt 承载版权+描述不准 | alt 纯画面描述（Kayakers paddling on a calm reservoir below Hoover Dam）；版权单独 PHOTO CREDIT | alt 规则：描述画面，不承载版权 | image-checklist B·五 |
| ISS-054 | fixed | copywriting | open water 建议与 calm-water 边界冲突 | 边界声明与后续建议不一致 | 删除 open water 选型建议句，改为独立安全边界句（hull design/flotation/weather/waves/local guidance） | 边界声明后不得出现冲突建议 | TPL-020 |
| ISS-049 | boundary | visual-brand | 主图为公共场景图，非 Demo Product 产品证明图（产品证明力不足） | 无真实产品素材（demo 站） | 记录 BLOCK；正式站需真实产品图（侧面全船/尺寸图） | 产品卡/封面区分：封面=场景图，产品卡=产品图（真实素材到齐前不假冒） | TPL-022 |
| ISS-053 | boundary | platform | 图片输出属性策略层平台边界（⛔ 禁令范围，不展开） | 平台行为 | ⛔ 禁令：不检查、不报告；首图已有 preload | 不参与站内可修判定 | ID-0007 C8 |
| ISS-055 | fixed | process | 评审引用旧快照导致误判（FAQ无答案/alt未修），若盲从会错误返工 | 多轮评审存在缓存/版本滞后 | 对抗评审协议：先建最新事实矩阵+标注评审版本+证据回应，采纳真实点/平台BLOCK记录/旧快照点证据闭环 | 收到外部复核先抓现网，不盲从不傲慢 | OUTSIDER-REVIEW §3 |
| ISS-056 | fixed | copywriting | 标题与内容承诺未对齐（3 Specs vs 更多内容）；技术措辞仍偏绝对（tends to track/default） | 标题未含边界词；技术句未带影响因素 | 标题加边界词（for Calm Water）+首段归类 fit checks；技术措辞模型（can/tend to+影响因素）；故事后置（先答案） | 标题/措辞/顺序三条规则入库 | TPL-020 |
| ISS-057 | fixed | trust | 作者/审核/日期信息缺失（EA-T） | 平台无作者字段 | 正文增加真实主体段（Product Team/Reviewed against spec/Last updated）；不虚构专家 | 真实主体+可追溯日期 | TPL-020 |
| ISS-058 | fixed | verification | 审计仅人工/靠文档提醒，可重复出现'文档说完成但前端未落地' | 缺自动化机检门；人工清单靠自觉 | site_pipeline.py audit 门（早期 14 项含平台层项，现为 13 项站内项+机器可读 JSON 报告）接入 ONBOARDING 2.9/ID-0007 B7/OUTSIDER §3.0 | 任何上线前必跑 audit；评审回应前先 audit 拿事实 | DOC-002 |
| ISS-059 | fixed | process | 升级文章时 create_post 每次都新建草稿，同 slug 已发布版未复用→3 篇 Untitled Post 残留 | create 与 update 混用：更新前未查已存在 slug | 更新优先规则：先 read_lists 找已发布 slug → 存在则 publish_post 更新（不 create）；audit 全站 posts 数=预期数才算过 | 任何文章升级：先查 slug 再发布；上线前 audit 的 count 项核对 posts=预期 | WRITING-INDEX |
| ISS-060 | fixed | format | 正文标题语义：我们一直用 type:'heading'（无标题样式），编辑器原生是 type:'h2'/'h3'（渲染 slate-h2 text-2xl）——此前矩阵判 heading 无效是'用错类型'而非'平台不支持'；blockquote 需包裹结构 | 从未从编辑器真实 payload（update 表单）提取块类型，而是自测猜测 | 从编辑器默认值 payload 批量提取块类型（h1-h6/bulleted/numbered/blockquote 包裹/带 id）；实测 h2/h3/blockquote(包裹) 生效，列表仍平铺 | 任何块类型判断前：先看编辑器/更新 payload 的正规格式；迁移文章用原生 h2 替换 bold 标签 | MODULES 三·五 |
| ISS-061 | fixed | double-review | 对抗审查 FAIL：callout 三源矛盾/迁移空格漏转/文档-代码脱节(skeleton/签名)/format-ref 计数/check 无禁用自检 | 多文档各自为政未单一真源；MIGRATE_LABELS 空格与范文不一致；实现先于文档 | 以 FORMAT-SPEC 为真源统一 MODULES/WRITING-INDEX；migrate 空格归一化+漏转报告；补 skeleton 实现;format-ref 补3行(image→false);check 加禁用自检+h3-only 提示;docstring 同步;计数修正(api-ref 23) | 任何文档-代码对不上=评审必查；标签间距以范文为准归一化 | FORMAT-SPEC |
| ISS-062 | fixed | double-review | 续接代码块对抗审查 PASS_WITH_FIXES：5×P1（cd 缺失/模块数口径矛盾/check 占位不可释且无 exit 码/§3 旧 14 项口径/证据目录未提）+6×P2（33vs34/token 未明示/HANDOFF 过期计数/无上下文未点破/ghostwriter 两套协议混用） | 续接块早于审查生成、数字沿用旧口径、token/证据目录依赖隐性前提 | 重写最终版：cd 开头+token 明示+证据目录+14→15 旧口径标注+BLOCK 分账(机检4/总7)+H2 已绕过+check live JSON 导出+ghostwriter 两套协议区分+无上下文点破；OUTSIDER §3 14→15；FORMAT-SPEC migrate 签名修正；check 加 sys.exit | 跨会话指引必须：路径基准唯一+数字实时核+可选前提显式化；更新后再自审一遍 | OUTSIDER-REVIEW.md |
| ISS-063 | fixed | process | audit 门硬编码 Demo 事实（页面/数量 3+4/FAQ 短语/CTA 深链/单位），对任何新站产生假 FAIL——Example 被误报 count/faq-answer/cta 三项 | site_pipeline.py audit 把单站基线写死在函数体，未做 per-site 配置 | audit 增加 --config <json> 站点基线（pages/count/faq_answers/cta/units/primary_article/required_h2），AUDIT_CONFIG_DEFAULTS 保留 Demo 向后兼容；Example 建 example-audit-config.json 后 4/4 通过 | 任何新站上线前 audit 必须带该站 --config；基线从内容计划(COP)取实建数，不得沿用他站 | OUTSIDER-REVIEW §3; ONBOARDING 2.9 |
| ISS-064 | fixed | process | audit add() 三态丢失：bool(None)=False 把'skip'坍缩成'失败'且 if not ok 把 skip 记进 problems；空 units 列表使正则 \b()\b 匹配空串 | add() 用 bool(ok) 存值丢失 None；units 空表未短路 | add() 改为保留三态(ok is None→⏭️)且仅 ok is False 记 problem；units 空表显式 add('unit', None, 跳过) | 写机检门时 None=跳过/False=失败/True=通过三态分离；列表驱动的正则先判空 | OUTSIDER-REVIEW §3 |
| ISS-065 | boundary | process | 新站建站未先 index-first（registry_tools.py find），重复已知坑 ISS-001/002/003/018/024/059；'没按规则做'的核心原因=入口规则无强制 gate | 0.0 索引优先是纯文档提醒，靠自觉；无 fail-closed 拦截 | 0.0 前置硬 gate：新任务第一动作必须 find + verify；audit 化后 count 项=实建数才过（ISS-059 已回填）；本次补齐 audit 每站 --config | 任何新站/新任务：先 find 关键词再动手；audit 带 per-site config；找不到或踩新坑→回填 issues.tsv | ONBOARDING 0.0/2.9 |
| ISS-066 | boundary | platform | 页面级 SEO description 为主题生成元数据（如 Posts 页 'A journal listing page...'），页面记录有 description 字段但全客户端 bundle 无任何 updatePage/seo action，无法经 API 改——与 homePageId/isHome 同类平台 BLOCK | default 主题模板自带页面 description；updateTheme 只覆盖主题名/描述，不覆盖页面元数据 | audit 模板词扫描排除 meta/link 标签（script/style 之后）；页面元数据归平台 BLOCK 记入交付清单；可见文本残留仍判 FAIL | 模板词检查只对可见文本判定；meta 层归平台 | RUNBOOK-ANYONE §9; OUTSIDER §3 |
| ISS-067 | fixed | process | 主题 domain 只有 /tmp 散脚本（createTheme/setThemeActive/applyRoutes/updateTheme/deleteTheme 42 位 action id），新 AI 无法复用；文章 CTA 真链接无配方；RUNBOOK 缺零上下文总入口 | 主题操作未沉淀进 allincms_api.py；会话内脚本失散 | allincms_api.py 新增 create_theme/set_theme_active/apply_theme_routes/update_theme/delete_theme + THEME_ACTION_IDS（从 workspace 客户端 bundle 提取验证 42 位 id）；新建 RUNBOOK-ANYONE.md 零上下文 10 步手册 + §2 实测事实表 + §9 平台 BLOCK 回落表 + §7/§8 k3 写 flash 审工作流 | 任何新操作一旦实测成功必须沉淀为 api 方法+runbook 步骤；散脚本只留证据不承担复用 | RUNBOOK-ANYONE.md; WRITING-INDEX.md |
| ISS-068 | fixed | seo-copy | Example 残留 demo 内容 4 处（对抗补充扫描发现）：post-detail 页 related 块 'More from the journal'；posts 页 page-header 'Journal/Product care and ideas' 与 recommendations 'featured in our journal'；social-floating-button WhatsApp 空号按钮（zod 空串回默认 wa.me/+44-7911-123456） | 早期 demo 清理只扫了 TEMPLATE_WORDS 旧词表 + 首页/关于/联系页，未覆盖文章详情页/posts 页块 props 与全局浮动按钮；zod default 回填机制未识破 | post-detail 加 material-story-split CTA 真链接(/contact-us?source=example-article) + related 文案换 Example；posts 页两块文案全换；浮动按钮整体移除（children+elements 同删，置空无效）；TEMPLATE_WORDS/DEMO_CONTACTS 补 13 个漏网 demo 词与 wa.me/+44-7911-123456 | demo 清理必须覆盖全部 7 页 + 全局块（header/footer/dialog/floating）+ 详情页块 props；'置空'对 zod default 字段无效，移除=删元素；模板词表每遇漏网立即扩充 | RUNBOOK-ANYONE §2/§9; MODULES |
| ISS-069 | fixed | double-review | 零上下文 subagent 对抗审查 RUNBOOK：NEEDS_FIXES，3 个新手必撞断点——①块类型三套词汇打架（§2 h2/§7 'p'/样例 'heading'）②§3 主题页断链（theme_id 无来源/read_page_document 返回结构注释错误/create_theme docstring 与 createSite 行为混淆/globals 一致性说法矛盾）③目录与凭据假设悬空（70_evidence 未定义、audit --out 不建目录、/tmp 脚本悬空、scan-actions 用法错误、allincms_api 顶部 docstring 全是旧签名、login 静默 no-op） | 多轮修修补补导致词汇/签名/出处三处分叉，无零上下文复核 | 统一类型词法 p|h2|h3|blockquote（服务器存储形态实测）：post-payload-example.json 重写、writing-module 输出 p 输入兼容 paragraph、FORMAT-SPEC/MODULES 同步；allincms_api 新增 read_themes()；audit --out makedirs；login() 非静默；docstring 换真实签名；RUNBOOK §0 工作目录/token 双路径/路径约定/scan-actions 真实用法、§3 theme_id 获取链+返回结构+globals 按页存储；复核 subagent 二次判定 READY_TO_HAND_OFF | 任何'任何人可用'类文档交付前必须派零上下文 subagent 实测复核（OUTSIDER-REVIEW §执行方式）；类型词法以服务器 readback 存储形态为唯一真源 | RUNBOOK-ANYONE.md; FORMAT-SPEC.md; MODULES.md |
| ISS-070 | fixed | platform | 根路径 / 修复：setHomePageAction（页面管理域，chunk 12rhvrcyv9te_ 懒加载于主题概览页 /{slug}/themes/{themeId}）。此前'无 setHome action'定论是错的——页面管理域不在已抓的 9 个主题域 action 里 | 只搜了主题面板+设计器 chunk；页面管理 UI chunk 未加载；POST 到 /{slug}/themes 返回 200 空 flight 静默无效果，误导为'平台 BLOCK' | allincms_api 新增 set_home_page/set_page_enabled + PAGE_ACTION_IDS(6)；修复顺序=激活主题→set_home_page；Example 根路径 / 已上线验证(err=0, Home | Example Corp)；audit 加 root-home 项(__next_error__ 检查) | '不存在'类结论必须注明'在已检查的 N 个 bundle/路径中'；同一 action 换 URL 路径重试（server action 路由绑定在页面路径上）；setThemeActive 会清 homePageId——先激活后设首页 | RUNBOOK-ANYONE §2/§3/§9; ROOT-PATH-ISSUE.md |
| ISS-071 | fixed | boundary | createTheme(preset='default') 会在站点级重新种入 3 个 demo 产品+3 个 demo 文章（本轮 5 次 createTheme 后 read_lists 变 10/6，新记录 id 时间戳=创建时刻）——demo 清理不是一次性，重建主题后必须重跑 | default 主题 preset 含站点示例内容种子；之前 demo 删除后以为一劳永逸 | 重建主题后立即重跑 demo 清理（delete_product/delete_post 按 demo slug 清单）；audit count 项自动暴露（products=7 posts=3 基线） | 任何 createTheme 之后：audit count 核对 = 预期实建数；RUNBOOK §8 审计前先删 demo 种子 | RUNBOOK-ANYONE §2 |
| ISS-072 | fixed | double-review | 多代理对抗复核（4 代理并行：demo 终审/新站清单/一条龙手册/零上下文复核）NEEDS_FIXES：RUNBOOK §3 page_id 未定义(NameError)；ONBOARDING 2.6 仍教 heading/paragraph 旧词法（3 处）+ article-writing-logic 旧教义 + format-ref.tsv 3 行；audit 项数口径全线滞后（代码 16，RUNBOOK/ONBOARDING/OUTSIDER/FORMAT-SPEC/INDEX 写 15 甚至 14）；ISS-071 回填半途（delete-demo-content.py 不存在、demo slug 清单未入 kit、ONBOARDING 零提及）；create_theme docstring 与 set_home_page 自相矛盾；TEMPLATE_WORDS 漏 product care and ideas 与 twitter/x.com；MODULES 六词表旧 15 词 | 多项修复各自为政，文档-代码-证据三处未同步；无并发修改协调 | 全部修复：RUNBOOK §3 补 page_id；ONBOARDING 三处词法统一 p|h2|h3|blockquote + 2.9 加 set_home_page 与 demo 清理步骤；项数口径全改 16；新建 delete-demo-content.py（含 6 demo slug）+ 注册 doc-registry；create_theme docstring 指向 set_home_page；TEMPLATE_WORDS 补 3 词；MODULES 六词表改指代码真源；FORMAT-SPEC/article-writing-logic/format-ref 统一 | 多代理并行修改同一仓库时必须指定单一写者或事后全量 grep 口径核对；'旧词法'迁移必须 grep 全仓一处不留 | RUNBOOK-ANYONE.md; ONBOARDING-PIPELINE.md; NEW-SITE-ONEPASS.md; templates/new-site-customization-checklist.md |
| ISS-073 | fixed | platform | 页面 meta description：①静态页（home/about/contact/posts/products）可经 updatePageAction 改（旧结论'无写路径'作废一半）；②动态路由页（/posts/{post}、/products/{product}）description 被服务端回退模板值（平台限制）；③页面 publish 可能重置 description→更新必须在最后一次发布后，公网以 curl meta 为准 | 页面管理域 updatePageAction 未发现；commit publish 会重生成页面记录 | allincms_api 新增 update_page()；实测配方=updatePageAction→等 10s→commit publish 带 description 字段→curl 验证；5 静态页全部上线 Example meta | meta description 更新放最后；动态路由页 meta 归平台 BLOCK 记录 | RUNBOOK-ANYONE §9 |
| ISS-074 | fixed | content | 多代理 demo 终审 FOUND_13：about 页两处公开模板文案（about-intro/company-story body）、products page-header demo 文案、产品详情 related 文案、6 个孤儿 demo 分类（Buying Guides/Daily Carry/Home Goods/Travel Essentials/Material Notes/Home Routines）、7 个孤儿 demo 标签 | 早期清理只删了 demo 产品/文章，未删 taxonomy；about/products 页部分块未替换 | 全部修复：4 处文案换 Example；allincms_api 新增 delete_category/delete_tag（chunk 35taj5359am8z 提取 6 个 taxonomy action id）；13 个孤儿记录删除；read_lists 验证只剩 Example 分类/标签 | demo 清理必须含 taxonomy 层（分类/标签同样由 createTheme 种入）；新站清单加 taxonomy 清理节 | templates/new-site-customization-checklist.md |
| ISS-075 | fixed | double-review | 第 2 轮全量对抗审查（4 零上下文代理并行）：站点复验 CLEAN（13 处清零+16URL 200+内容完整）；但工具链抓出 12 处缺口——①site_pipeline docstring 15项+audit 内部'无写路径'过期注释 ②两条新文档：taxonomy 清理全链缺失/清单#162 meta 结论过时/#20 footer socialLinks 失实/#102 字段名错(postActionLabel)/#99 details 归属错/#62 proof-1 判定错/ONEPASS 路径基准断裂/步骤11 未用权威脚本/行数写死 ③README login 措辞张力 | 首轮修复后无第二轮独立复核；清单由单代理编写未经实测比对 | 全部修复：delete-demo-content.py 升级全链（产品+文章+分类+标签按名字删+自动复核，实测通过）；清单 5 处修正+⑩ 表补 158a taxonomy 行；ONEPASS 路径约定(TASK/IFK 变量+mkdir)+步骤11 权威脚本；site_pipeline 16项+注释更新；README login 措辞；行数引用去写死 | 任何新文档交付前必须过两关：零上下文审查代理 + 字段实测比对代理（与线上真源逐路径核对）；'已删/不存在'类判定必须以 readback 为准 | NEW-SITE-ONEPASS.md; templates/new-site-customization-checklist.md |
| ISS-076 | fixed | frontend | 联系页表单整个不渲染：contact-form-split 块 formSlug 为空串（旧文档误标'无害回填'）——空 slug 时 RuntimeFormsProvider 找不到表单定义，<form>/<input> 全部不输出；此前'MODULES.md:7 把 formSlug="" 列入无害白名单'的结论错误 | formSlug 是表单块的绑定键，空值≠无害，是断裂 | contact-split-1.props.formSlug='contact-inquiry'（站点 initialForms 里的真实 slug）+save+publish；公网验证 <form>/<input>/<textarea>/Send message 全渲染；实测提交链路：POST 公开站 /contact-us + next-action=submitRuntimeFormAction(siteId 绑定) body=[siteId,{formSlug,values}] → {success:true}；注意 action 在公开站部署，workspace 域 404 | 表单块 formSlug 必须显式绑真实 slug；提交测试必须打公开站域；工作台无提交收件箱 UI（平台限制）→ 联系页必须保留邮箱兜底 | RUNBOOK-ANYONE §9; templates/new-site-customization-checklist.md #78/回填表 |
| ISS-077 | fixed | verification | ISS-076 修复后对抗复验又抓出一处：首页内联表单块 contact-1（非 contact-split-1）formSlug 也是空——同型断裂第二处；且 audit 此前无表单渲染检查项（表单断了 audit 仍 PASS） | 只修了用户报告的那一处，未全站扫同型块；审计盲区 | 首页 contact-1 绑 contact-inquiry（公网验证 form=2：内联+弹窗）；7 页 globals 弹窗 formSlug 逐页核验全 ✓；服务端校验实测（缺必填→fieldErrors 逐字段）；audit 新增 form-render 项（contact-us 必须有 <form>+submit），17 项口径全文档同步；回落三层写入 RUNBOOK §9 | 修任何'某块断裂'类问题必须全站扫同型块（按 block type 扫 7 页+globals）；关键交互（表单/CTA/导航）要有对应机检项，不能只靠用户报障 | RUNBOOK-ANYONE §9; site_pipeline.py form-render |
| ISS-078 | fixed | double-review | TERRA 双审（2 代理：凭据/风险/合规 + 矛盾/上手断层）两路 PASS_WITH_FIXES：①凭据 0 泄漏、事实与 BRIEF 合规（90/90/94 属实）②6 个 delete_* 无破坏性警告 ③demo 清理按名删 taxonomy 无引用护栏（误删客户真实同名风险）④删除无授权门 ⑤状态文档 3 处矛盾（HANDOFF frontmatter/TASK.json audit 引用算术/platform_blocks 含已修复 root）⑥文章 VSWR 配对事实错（2 条 low 旗标悬置）⑦formSlug 旧口径残留在真源 MODULES.md:7+3 处 ⑧ONEPASS §3.2 漏 form-render 行+doc-registry/FORMAT-SPEC 16 项残留 ⑨RUNBOOK demo 重种未回填 taxonomy ⑩routes/activate 顺序三文档分叉 ⑪ONEPASS page_id 缺赋值+步骤 0 无 token 前置+2 悬空脚本 ⑫DELIVERY 从未产出 ⑬入口链到不了 ONEPASS | 多轮修复各自为政+无 TERRA 角色化终审；破坏性方法从未加护栏 | 全部修复：6 delete_* 加破坏性 docstring；delete-demo-content.py --dry-run+引用护栏（非 demo 引用即 SKIP）；删除授权门写入 RUNBOOK §8/ONEPASS 步骤 11；TASK.json/HANDOFF 状态修正+测试提交披露；文章 VSWR 改两系列<1.15（产品规格表证据）publish 上线；MODULES/ONBOARDING/ONEPASS/checklist 4 处 formSlug 旧口径归零；17 项口径补 doc-registry/FORMAT-SPEC/ONEPASS §3.2；RUNBOOK 重种回填 taxonomy；顺序统一 routes→activate→set_home；ONEPASS page_id/token 前置/悬空脚本；新建 DELIVERY-<site-key>-20260830.md；README/RUNBOOK 补 ONEPASS 第一入口链 | 大任务收尾必须过 TERRA 双审（凭据面+矛盾面）+DELIVERY 才算完；破坏性方法从第一天就要护栏 | DELIVERY-<site-key>-20260830.md; DUAL-REVIEW 记录 |
| ISS-079 | boundary | structure | 结构性混层：母库根混 tracked 知识/customer-runtime/tmp 运行残留；64 tracked 修改跨客户活；/tmp 217 个跨会话散落（chunk/HTML/探测脚本）无分区无 TTL；工具 CWD 残留（contact-scan/audit-html 写相对路径）；skill 仓 dirty 3 文件 | 四层（可发布知识/工具代码/客户数据/会话 scratch）无物理分层，靠 .gitignore 兜底挡不住清理负担 | 结构约定写入 wiki/00_meta/id-0072-runtime-folder-structure-v2.md（四层分离 + 迁移方案 symlink 兼容）；site_pipeline.py 加 SCRATCH_DIR 环境变量（contact-scan/audit-html/gate-html 全部走它）；本会话 /tmp 垃圾清零（备份 real-theme-backup.json 先保进任务 70_evidence） | 新工具产物一律 SCRATCH_DIR，禁 CWD 依赖；会话垃圾落 20_scratch/<日期>；迁移需用户授权 | wiki/00_meta/id-0072-runtime-folder-structure-v2.md |
| ISS-080 | fixed | structure | TERRA 结构迁移审查（71d23959）先修后迁六条件：①.gitignore 尾斜杠模式不匹配软链（抛弃仓实证：软链会被 git add -A 误提交为 symlink blob）②00_shared 软链变体会断运行区（内部绝对引用指向 10_clients）③相对软链以链接所在目录为锚（cwd 无关、整树搬迁有效，绝对链会断）④tracked 区绝对路径引用=0、运行区内部绝对引用经整目录软链全兼容 ⑤64 tracked 修改 8 文件抽查全部=知识升级（我的 41/23 总账成立，严格口径 43 工具配置+21 文档）⑥skill 仓 3 文件合规可 commit；id-0072 可入库但需补 visibility/redaction_status | 迁移方案未实证 git 软链行为；00_shared 变体隐患未发现 | 已修：.gitignore 加无斜杠行（复刻实证通过：link-dir 被忽略）；id-0072 迁移节重写为 TERRA 六条件版+回滚一句话+软链运行必需警告；frontmatter 补 visibility/redaction_status；flash-2 核验本会话改动无损 | 任何 git ignore 规则涉及软链前必须实证 check-ignore 行为；迁移类方案先抛弃仓复刻验证再执行 | wiki/00_meta/id-0072-runtime-folder-structure-v2.md |
| ISS-081 | fixed | structure | flash-1 结构方案审查（2d5a5ecf）需补漏后执行：①根因未隔离——64 tracked 修改主体在 sub-libraries/ADAPTERS（tracked 且客户活必改），mv customer-runtime 不解决'母库被改脏'复发 ②事实虚构——'母库 dist 同步 interface-kit'无源（母库 tracked 0 命中、dist 无），真实权威副本在 runtime ③TTL 会删证据（fluxpedal HANDOFF 引 8/12 artifacts 14+ 天基线 + 5 客户状态文件引 chunk//tmp 路径）④残留误判——REVIEW-RECORDS 实为 tracked、tmp/fluxpedal-site 无去向、.DS_Store 未 ignore、26 untracked 未分拣 ⑤flash-1 误报 1 处：'skill 无 git 仓'——.git 目录实证存在、TERRA 已核 3 脏文件合规 | 方案只迁移不动因；TTL 一刀切；部分残留分类未实测 | id-0072 全部修订：REVIEW-RECORDS 归 tracked 不迁；'dist 同步'改'runtime 权威（现状）+dist 管线待建'置顶待办①；TTL 加 promote-to-70_evidence 豁免闸门+引用检查；规则区加 adapter 脏源承认（当日 release 快速通道/runtime-override）；迁移节补 fluxpedal-site 归客户区+legacy shim 标注；待办补 .DS_Store ignore 与 RUNTIME_ROOT 约定；flash-1 误报核销 | 结构方案每个'事实性主张'（同步源存在/某目录是残留/某仓不存在）必须实测核验再写；TTL 必须有引用豁免 | wiki/00_meta/id-0072-runtime-folder-structure-v2.md |
| ISS-082 | fixed | structure | 第 2 轮结构对抗（flash 8a53f97a 复核修订 + TERRA ff467d52 干跑演练）：flash 判 6/6 修订落地达标可执行（建议执行序显式化+ln 前置闸门——已补 7 步执行序含闸门 A1/A2/B）；TERRA 判先修 3 条：X1 realpath 相对路径 cwd 依赖（实测错误 cwd 输出'看似成功'的错值）X2 缺显式 mv 步骤+无 mkdir+先 ln 会静默嵌套软链（10_clients 其实随树搬不存在缺失问题——用户前提不成立但顺序风险真实）X3 整树搬迁断 11 文件绝对引用+待办①应与迁移绑定授权；另 df 同卷断言+redaction_status 纯枚举化 | 第 1 轮修订后文档仍无显式执行序；验证命令相对路径；警告只覆盖删链漏了搬家 | 全部修复：7 步显式执行序（闸门 A1 目标不存在+A2 df 同卷断言+B ln 前置原目录不存在）一次复制可跑；realpath 绝对路径+断言期望值；警告 2 整树搬迁断 11 处绝对引用（列代表文件）+迁后改 $RUNTIME_ROOT 批次；绑定条款=授权迁移同时立项 interface-kit 真源；redaction_status 拆纯枚举+redaction_note | 迁移类方案的验证命令必须绝对路径+断言期望值（防'看似成功'）；执行序必须显式编号含全部前置闸门；'删链'与'搬家'两种断链场景都要警告 | wiki/00_meta/id-0072-runtime-folder-structure-v2.md |
| ISS-083 | fixed | boundary | 对抗审查'能否完全不依赖浏览器纯 cookie 接口操作'：操作矩阵 10/10 全通（读 8+幂等写 2，全 API 无浏览器）；唯一浏览器依赖=首次取 token（login() 曾丢弃 Set-Cookie 响应头，机制上不可能拿 token） | _req 只返回 (status, body)，响应头全丢；Payload 标准 sign-in 会回 Set-Cookie: payload-token | login() 升级纯 API：_req 捕获 Set-Cookie 列表 → login 从中提取 payload-token（成功+失败双路径实测通过：错误凭据干净报错；真实凭据（用户提供）→ Set-Cookie 提取 357 字符 JWT → read_sites 返回 2 站 + set_home_page 写权限验证通过——浏览器依赖归零，全链路纯 API） | 声明'不支持'前先查客户端是否丢弃了关键响应头；登录类能力分级=错误路径实测✓/成功路径标准实现未实测 | RUNBOOK-ANYONE §0 |

## 3. 模块库（modules.tsv）

| type | group | builder_fn | schema_note | 前端显示 | status |
|---|---|---|---|---|---|
| carousel-campaign | Campaigns | `carousel(); slide(); service_item()` | slides[]+serviceItems[]（icon/desc） | 顶通大图轮播+2-3 服务条 | verified |
| category-showcase-grid | Catalog | `category_grid(); category_item()` | items[]（name/desc/media/target） | N 列图卡（图+名+描述+箭头） | verified |
| hero-commerce | Heroes | `hero()` | actions[]/serviceItems[]/campaignPills[] 必须显式（回填坑） | 左文右图+规格面板+服务3项+信息药丸 | verified |
| feature-grid-proof | Proof | `feature_grid(); feature_row()` | proofRows[]（label/title/desc/meta/action） | N 列卡（编号+字+meta+action 链接） | verified |
| featured-product-list-showcase | Products | `product_showcase()` | associatedListPage/DetailPage/categorySlug/sortOrder | 标题区+CTA+特色产品大卡 | verified |
| full-product-list-filtered | Products | `product_list()` | pageSize/showToolbar/sortOrder/columnCount | 筛选工具栏+产品网格 | verified |
| material-story-split | Story | `material_split(); material_note()` | notes[]（title/desc） | 左图右文+notes 列表+action | verified |
| social-proof-quotes | Proof | `proof_quotes(); review()` | reviews[]（quote/name/detail）+ratingLabel | 评分星标+N 列评价卡 | verified |
| featured-news-list-editorial | Articles | `news_list()` | associatedListPage/DetailPage/categorySlug/sortOrder | 特色文章大卡+列表卡 | verified |
| faq-accordion | Forms | `faq(); faq_item()` | items[]（question/answer）+supportNote | 问答手风琴 | verified |
| newsletter-inline | Forms | `newsletter()` | emailPlaceholder/submitLabel/finePrint | 订阅行（输入+按钮+细则） | verified |
| contact-form-split | Forms | `contact_split()` | email/phone/address/hours + formCard* | 左联系卡+右表单卡（客户端渲染） | verified |
| about-intro-media | Company | `about_intro()` | eyebrow/title/description/body/media/fit/caption（caption 显式传避免回填） | 左文右图+图下 caption 小字 | verified |
| company-story-media | Company | `company_story()` | sectionLabel/headline/lead/body/media/fit/note/noteLabel | 左图右文+note 引述块 | verified |
| company-stats-grid | Company | `company_stats(); stat()` | stats[]（value/label/description）+columnCount | 数字大标题+N 列 | verified |
| company-values-grid | Company | `company_values(); value_item()` | values[]（title/description）+columnCount | 标题卡网格 | verified |
| company-team-grid | Company | `company_team(); team_member()` | members[]（name/role/bio/photo）+photoFit+columnCount | 成员卡（initials 头像+角色+简介） | verified |
| breadcrumb-inline | Navigation | `breadcrumb()` | props 空对象 | Home / 当前页 面包屑 | verified |
| contact-header-summary | Forms | `contact_header(); info_item()` | items[]（label/value） | 左标题右 key-value 项 | verified |
| contact-info-grid | Forms | `contact_info(); contact_info_item()` | items[]（type=email|phone|address/label/value/detail）+socialLinks 必须显式（回填坑） | 3 卡（图标+值+细节） | verified |
| location-map-interactive | Forms | `location_map(); map_detail()` | lat/lng/zoom/mapMode/details[]；tile 依赖外部服务 | 地图区+地址/细节列表（tile 失败灰块正常） | verified |
| header-dropdown | Global | `header()` | navigation[] children 必须递归 dict（回填坑） | 顶栏品牌+导航(可下拉)+CTA | verified |
| footer-columns | Global | `footer()` | columns[].links[]+socialLinks 显式（默认空）+copyright/systemNote | 品牌区+N 列链接+版权细则 | verified |
| contact-dialog-form-modal | Global | `contact_dialog()` | formSlug 关联 Runtime Form | 全站 CTA 弹出表单 | verified |
| social-floating-button | Global | `social_float()` | brand/url/label/showLabel/position | 右下角浮钮 | verified |
| product-detail-gallery | Detail | `-` | specificationsHeading/fit；正文区渲染记录 content（空则无正文区） | 面包屑+图库+规格+正文 | verified |
| product-related-grid | Detail | `-` | sectionLabel/headline/supportingCopy/pageSize/columnCount；无其它产品时显示"No content is available yet."（空态！） | 相关产品卡网格 | verified |
| post-detail-article | Detail | `-` | fit；正文渲染记录 content（Slate 已被验证渲染，注意 RSC 与 HTML 一致性） | 面包屑+文章头+正文 | verified |
| post-related-grid | Detail | `-` | 同 product-related-grid；其它文章不足也空态 | 相关文章卡网格 | verified |
| page-header-card | Detail | `-` | eyebrow/title/description/kicker | 列表页头（标准标题区） | verified |
| full-news-list-filtered | Detail | `-` | pageSize/showToolbar/sortOrder/columnCount/postActionLabel/associatedDetailPage | 文章列表（筛选工具栏+网格） | verified |
| recommended-product-list-grid | Detail | `-` | sectionLabel/headline/supportingCopy/postActionLabel/associatedDetailPage | 文章列表页底部推荐产品卡 | verified |
| recommended-news-list-grid | Detail | `-` | 同上（推荐文章） | 产品列表页底部推荐文章卡 | verified |

## 4. 维护规则

- 新增文档/脚本/模板 → 在 doc-registry.tsv 加行后 `verify` + `gen`（id 按 DOC-/SCRIPT-/TPL-/EV-/CAN-/IDX- 递增）
- 新问题排除后 → issues.tsv 加行（状态 fixed/boundary/pending）
- 新模块摸清后 → modules.tsv 加行
- TSV 字段含 tab 的文本（如多行）先替换为空格；description 精炼一行
