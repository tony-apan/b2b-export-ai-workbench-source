---
title: "Website Content Operations Playbooks"
description: "本子库长期可复用执行标准的 canonical 入口，区分新文章质量合同、现有文章优化 SOP 与文章页前端 SEO 合同。"
type: "index"
status: "Working"
owner: "AI"
created: "2026-07-31"
last_updated: "2026-08-12"
sources: ["../README.md", "../PLAYBOOK.md", "../MANIFEST.md"]
related: ["../START-HERE.md", "../TEMPLATES/README.md", "../QA-CHECKLIST.md", "../ADAPTERS/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
when_to_read: "需要执行正式网站内容方法，而不是只做工具接入或格式实验时。"
keywords: ["playbooks", "B2B SEO", "article standard", "frontend SEO", "content quality"]
---
# 执行标准

这里存放 `website-content-ops` 的长期 canonical 方法。根目录 `PLAYBOOK.md` 负责全流程路由；本目录页面负责某一类内容的详细标准，模板和 Adapter 只能引用它们，不能复制出第二套规则。

## 当前入口

1. [B2B SEO Article Standard](id-0001-b2b-seo-article-standard.md)：新写或重写正式文章时使用的唯一内容质量合同，定义买家意图、证据、结构、决策工具、CTA、评分与一票否决。
2. [B2B Article Optimization SOP](id-0003-b2b-article-optimization-sop.md)：优化现有文章时使用的串行执行 SOP；引用第 1 项，不复制第二套评分或事实规则。
3. [B2B Article Stage Patterns](id-0004-b2b-article-stage-patterns.md)：为 Learn、Troubleshoot、Compare、Validate、Buy 提供最小可复用模式，防止 AI 把所有文章写成同一套技术收资流程。
4. [Article Page Frontend SEO Contract](id-0002-article-page-frontend-seo-contract.md)：定义文章页可索引、结构化数据、语义 HTML、图片、移动端和发布后验收合同。
5. [Source-Driven CMS Create and Update SOP](id-0005-source-driven-cms-operation-sop.md)：用户提供 PDF、DOCX、表格、网站、图片或 brief 后，先按宿主能力生成私有 Source Extraction（原始 digest、locator、提取 digest、warning），再形成事实账本和 desired state，动态发现 CMS、做精确 create/update/upsert diff、两阶段新建站、计划摘要授权、严格串行接口执行和真实回读；不能把示例站、字段、CTA、产品模型或 Action ID 写死。
6. [Live AllinCMS Operation Adversarial Review](id-0006-live-allincms-adversarial-review.md)：针对真实站点、媒体、文章、产品、主题、路由、首页操作的双审升级合同，定义 capability gate、不可变 Plan A/B、证据轴、SOL + TERRA 双审门槛和可分享 Skill 硬性条件。
7. [Site Launch Acceptance](id-0007-site-launch-acceptance.md)：AllinCMS 站点上线前验收合同（内容/数据层、前端表现层、平台边界层），含 Runtime Forms 提交链路（load/submit action id、payload 形状、500 观察）、模板残留自检与 demo 值替换清单；上线前必查。

## 执行链

```text
Article Brief
→ Draft
→ Article Quality Review
→ Frontend SEO Contract
→ CMS Adapter
→ Publish Record
→ backend/editor/frontend acceptance
```

- 从空白新写：先读第 1 项，再依次复制 `TEMPLATES/article-brief.md` 与 `TEMPLATES/article-draft.md`。
- 优化已有文章：先读第 2 项和第 3 项，按 inventory → intent → pain → product map → links → CTA → review 严格串行，并继续接受第 1 项全部 fatal checks。
- 要判断页面能否正式索引或发布：再读第 4 项和 `TEMPLATES/article-quality-review.md`。
- 用户资料驱动的任意 create/update：先读第 5 项，并复制 `TEMPLATES/source-extraction.md` 与 `TEMPLATES/content-operation-plan.md`；新建站必须先 account-scope Plan A，再用真实 readback 建 site-scope Plan B。
- 目标 CMS 是 AllinCMS：最后读取 `ADAPTERS/cms/allincms/README.md`；格式、字段、产品和 create-site 能力以本次 deployment 的 Adapter capability 为准。
- API 成功、后台 toast 或单一总分都不能覆盖任何一票否决项。
