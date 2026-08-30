---
doc_id: "ID-0007"
title: "Site Launch Acceptance (AllinCMS)"
description: "AllinCMS 站点上线前验收合同：内容/数据层、前端表现层、平台边界层的可执行检查项与已知平台行为，含 Runtime Forms 提交链路、模板残留自检、demo 值替换清单。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-08-29"
last_updated: "2026-08-29"
sources: ["Example 客户站 launch audit 2026-08-29", "id-0006-live-allincms-adversarial-review.md", "interface-kit audit scripts"]
related: ["README.md", "../QA-CHECKLIST.md", "id-0006-live-allincms-adversarial-review.md", "../ADAPTERS/cms/allincms/interface-registry.json"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "AllinCMS 站点内容全部写入并发布后、对外宣称上线/交付前；或复盘已上线站点的质量问题时。"
keywords: ["launch acceptance", "AllinCMS", "site audit", "Runtime Forms", "soft 404", "template residue", "demo values"]
---
# Site Launch Acceptance (AllinCMS)

> 本页定义“内容已发布≠可交付”的验收动作。执行顺序：**A 内容与数据 → B 前端表现 → C 平台边界认知**。
> A/B 是可修项（修到通过）；C 是平台实测边界（修不了，但必须记录、不得误报为内容问题，也不得作为失败项）。

## A. 内容与数据层

### A1. readback 对抗（每页）
- 每页提交后必须 RSC readback 深度 diff（`site_pipeline.py diff` / `deep_diff`），只允许无害回填：`formSlug=""`、`columnCount=N`（服务端按项数推断）。
- 其余任何 `+ /path/key=值` 均为**服务端模板默认回填**：必须显式传值（可空数组/空串）后重交。已知回填字段：
  hero `campaignPills/actions/serviceItems`；contact-info `socialLinks`（默认 Instagram/LinkedIn 裸域名假链接）；header 导航 `children`（转 dict 失败则丢弃回填模板 "Bags"）；company-story `note/noteLabel`；about-intro `caption/fit`。

### A2. 模板词自检（内容层）
抓公网 HTML，过滤 `<style>/<script>` 后扫描词表：
`northstar|buildnbuzz|555-0142|mission street|san francisco|instagram.com|linkedin.com|weekender|premium steel|family size|maya|new season arrivals|carry, home|packing pouch|desk tray`
（`canvas` 会命中 CSS reset，必须先过滤 style/script 再判定。）
工具：`site_pipeline.py check <html-dir>` / skill `scripts/check_template_residue.py`。

### A3. demo 值替换清单（上线前必须核对，**联系方式必须由用户提供**）
- 联系方式（邮箱/电话/WhatsApp）是**用户提供项**：缺失即索要，不得用 demo 值交付；站上出现 demo 联系方式 = 不开上线
- 自动门：`python3 site_pipeline.py contact <slug> --real "<user@example.com>|<+86 17x xxxx xxxx>|<wa.me/86xxxxxxxxx>"` → 公网 demo 联系方式 0 才 PASS
- 扫描范围覆盖全站 globals（WhatsApp 浮钮/联系弹窗）与每页 contact 模块（信息卡+表单双份字段）
- 联系方式三件套：邮箱 / 电话+国际区号格式 / 地址（contact info、contact 表单卡、footer description 内嵌信息）；
- WhatsApp/社媒浮钮 URL 是否真实可聊；
- footer copyright / systemNote 是否还带 "Demo site for qualification run" 之类；
- 产品/文章正文中的 "(Synthetic demo product...)" 标注；
- 地图坐标（location-map-interactive 的 lat/lng/address）。
**注意**：不可收件邮箱（如 `@xxx-demo.com`）可能直接导致 Runtime Forms 提交服务端 500（见 C4），必须在真机实测前替换。

### A4. 数据一致性
- 产品分类 ≠ 文章分类（contentType:'products' vs 'posts'）；页面引用分类用 `?category=<产品分类slug>`。
- 产品/文章 slug 唯一；导航下拉不指向不存在的分类（如模板 500ml-travel/premium-steel）。

## B. 前端表现层

### B1. 全站链接/资源检查
- sitemap 每 URL 200；页面内所有内链与 img src（assets.laicms.com）200；
- 工具：零依赖抓取脚本（urllib 遍历 href/src，见 interface-kit 审计脚本）。

### B2. 截图人工复查（桌面 1440 + 移动 390）
- 导航可点、下拉正确；轮播服务条非模板文案；分类卡非模板卡；footer 无空白异常（socialLinks=[] 时社交区留白为正常）；
- 表单区域渲染（SSR 为客户端组件，无 JS 时为空——平台行为）；
- 地图 tile 依赖外部服务，加载失败时灰块属正常（数据仍在）。

### B4. 全站空态扫描（2026-08-29 追加）
- 所有公开路由 grep（过滤 style/script 后）`No content is available yet|No items yet|No results|coming soon|This form has no fields` = **0**
- 已知触发：详情页 related 推荐区（product/post-related-grid）在目录单品/单篇时无推荐项即空态；正文区 content 为空则不渲染（无空态）
- 修复：删除详情模板页 related 模块（document 可编辑）或保持目录 ≥2 项

### B7. 对抗审计门（2026-08-29 追加）
- 命令：`python3 site_pipeline.py audit <slug> --out 70_evidence/audit-report.json`（13 项一体机检）
- 判定：count/200/empty/template/demo-contact/faq-answer/cta/unit/absolute/markdown 全 PASS 为站内判据
- 机器可读报告入 evidence（audit-report.json）——后续旁观审查/双审可直接引用，避免"文档说完成但前端没落地"

### B6. 内容数量门（2026-08-29 追加）
- 美观基线：**产品 ≥3、文章 ≥4**（依据：列表网格/首页模块/related 区渲染行为，详见 interface-kit/templates/CONTENT-MINIMUM.md）
- 防空态底线：产品 ≥2、文章 ≥3（不足时必须删相关模块或关筛选栏——已实现为降级策略）
- 命令：`python3 site_pipeline.py gate <slug>`（数量/公网200/空态/模板词 一键门；任一不过 = 不开上线，向用户索要内容）
- brief validate 已内置数量检查（不足=INVALID+缺项提示）

### B5. 模板页纳入检查（2026-08-29 追加）
- Post/Product 详情页与 Posts/Products 列表页（theme pages 中 path 含 {post}/{product} 的页）document 一并纳入 A1 readback 检查；其模板文案（page-header 等）务必替换为品牌内容
- 相关模板页模块见 MODULES.md D 区（product-detail-gallery/post-detail-article/related-grid/page-header-card 等 8 种）

### B3. 元数据快照（记录，不绝对阻塞）
- title 规范：`<页面名> | <品牌>`；meta description 存在；
- 产品/文章详情页有 og:title/og:description/og:image/twitter:*（平台自动注入，源自记录）；
- **首页/列表页无 og:***、无 favicon/link icon——平台模板行为（见 C）。

## C. 平台边界（实测 2026-08-29，示例客户站）

| # | 现象 | 实测 | 处理 |
|---|---|---|---|
| C1 | soft-404 | 不存在路径返回 **HTTP 200**，body 为 "Allin CMS Runtime" shell（`/favicon.ico` 也返回 200 text/html） | 平台行为，工作台无配置入口；搜索引擎可能收垃圾索引——若客户有 SEO 要求需向平台反馈或接受 |
| C2 | 首页多 H1 | carousel slide 与 hero 模块固定输出 `<h1>`（首页 4 个 H1；template 架构） | 平台行为（模块渲染固定 tag）；内容上让首屏主标题承担主要语义，勿大字排布次要标题 |
| C3 | og 缺失（站级页面） | 首页与列表页无 og:*；详情页有 og:image（引联资产 URL，200） | 平台模板行为；产品/文章页 og 已由平台按记录注入，站级页面无入口 |
| C4 | Runtime Forms | `loadRuntimeFormAction` 公开站无鉴权可调（payload `[siteId, formSlug]`，返回完整 schema：字段/校验/submit 文案）；`submitRuntimeFormAction`（`[{formSlug, values}]`）接口级实测 **HTTP 500**（digest 753112626），疑似 demo 邮箱不可收件/需浏览器会话 | 已在 interface-kit 记录 action id 与 payload；**任何站上线前必须替换真实邮箱后用浏览器实提一次**，通过才算表单链路 OK |
| C5 | 表单为客户端组件 | contact 页 SSR HTML 无 `<form>`（JS hydration 后渲染） | 平台行为；无 JS 场景表单不可用 |
| C6 | 首屏体量 | 公开页 HTML ~900KB（RSC 内联） | 平台架构；记录，不阻塞 |
| C8 | 正文排版（写文章前必读） | Slate 正文 **无标题语义/无段落间距 CSS**（heading 不渲染 h2；slate-editor 块无 margin；CSS 为编译产物不可注入） | 平台固定；**方案**：视觉标题=段首加粗句、段落分隔=段间空段落（paragraph text=""）、内链=恢复 related 模块（数据≥3 时不再空态）；正文禁用 Markdown 语法 |
| C7 | globals 按页存储 | 单页 commit 只更新该页；全站统一需对全部页面重交（readback 各页 document 原样回传 + 新 globals） | 已写入 ID-0006/模块文档；上线前全局改动必须 7 页重交 |

## D. 上线判定

不满足以下任一条 → 不开（或仅作为 preview 交付）：
1. A1：所有页面 readback diff 仅含无害回填；
1b. A3：contact 门 PASS（公网无 demo 联系方式，用户真实值已验证）；
2. A2：公网 HTML 过滤后模板词 = 0；
3. A3：demo 值清单无残留（或客户书面确认接受 demo 值）；
4. A4：产品/文章分类归属验证 passes（产品=产品，文章=文章）；
5. B1：8 页 URL + 全部资源 200；
6. B2：桌面/移动截图人工复核无模板残留与明显版面缺陷；
7. B4：全站空态扫描 = 0（related 区/正文区/列表区无 "No content is available yet" 等空态文案）；
8. B5：详情/列表模板页 document 纳入 readback，模板文案已替换；
9. C4：真实邮箱替换后表单实提成功（或记录为已知缺陷并客户确认）。

## E. 参考命令（零依赖，接口级）

```bash
# 模板词自检
python3 site_pipeline.py check <public-html-dir>
# readback 对抗
python3 site_pipeline.py diff submitted.json readback.json
# 表单 schema 读取（公开站，无鉴权）
curl -X POST https://<site>.web.allincms.com/contact-us \
  -H "next-action: <loadRuntimeFormAction id>" -H "content-type: text/plain;charset=UTF-8" \
  -H "Accept: text/x-component" -H "Origin: https://<site>.web.allincms.com" \
  -H "Referer: https://<site>.web.allincms.com/contact-us" \
  --data '["<siteId>","<formSlug>"]'
```
