---
doc_id: allincms-bulk-live-verification-mysite01
title: AllinCMS 现场核验记录 mysite01
description: 2026-06-29 对 mysite01 站点的 LAICMS / AllinCMS 字段、路由和渲染行为脱敏核验记录
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-04
page_type: reference
sources: []
confidence: medium
---

# Live Verification: mysite01

Observed through the in-app browser on 2026-06-29 and refreshed read-only on 2026-06-29. This is a verified LAICMS / AllinCMS platform-behavior example for orientation only. Re-check every new site, content type, and backend version before upload.

Business content from this site is intentionally redacted. This reference must not become a knowledge base for the site's topic, industry, private operating process, or any other non-CMS business domain.

## Verified Site

```json
{
  "workspaceUrl": "https://workspace.laicms.com/dashboard",
  "siteKey": "mysite01",
  "frontendBaseUrl": "https://mysite01.web.allincms.com",
  "loginState": "logged in",
  "visibleAccount": "redacted"
}
```

## Dashboard

Dashboard showed real edit links for both content types:

```text
https://workspace.laicms.com/mysite01/posts/{postId}/update
https://workspace.laicms.com/mysite01/products/{productId}/update
```

Refreshed module routes observed read-only:

```text
/mysite01/dashboard
/mysite01/products
/mysite01/posts
/mysite01/media
/mysite01/themes
/mysite01/routes
/mysite01/forms
/mysite01/site-info
/mysite01/tracking
/mysite01/domains
```

The refresh also observed existing `Untitled ...` draft patterns for posts, products, and forms. Treat them as cleanup candidates that require explicit cleanup authorization. Do not mark cleanup as completed or not needed while such candidates remain visible.

## Site Creation Preflight

Create-site dialog was opened read-only and closed without submitting.

Observed fields and controls:

```text
button: 创建站点
dialog title: 创建站点
input name: name, placeholder: 站点名称
textarea name: description, placeholder: 站点简介
submit button: 创建
close button: Close
dialogClosedVerified: true
```

## Posts

Backend list:

```text
https://workspace.laicms.com/mysite01/posts
```

Verified list columns:

```text
标题
Slug
摘要
排序
状态
分类
标签
创建时间
```

Verified edit page:

```text
https://workspace.laicms.com/mysite01/posts/{postId}/update
```

Visible edit controls:

```text
正文编辑器
标题
Slug
分类
标签
摘要
排序
封面图
更新
取消发布
历史
```

Observed input details:

```json
{
  "titleFieldName": "title",
  "slugPlaceholder": "post-slug",
  "excerptPlaceholder": "简短摘要...",
  "statusControl": "发布 or 取消发布 depending on current item state",
  "saveControl": "更新"
}
```

Frontend routes verified:

```text
https://mysite01.web.allincms.com/posts
https://mysite01.web.allincms.com/posts/{post-slug}
```

## Products

Backend list:

```text
https://workspace.laicms.com/mysite01/products
```

Verified list columns:

```text
媒体
名称
Slug
描述
排序
状态
分类
标签
创建时间
```

Verified tabs:

```text
列表
分类
标签
规格
```

Verified edit page:

```text
https://workspace.laicms.com/mysite01/products/{productId}/update
```

Visible edit controls:

```text
正文编辑器
名称
Slug
分类
标签
描述
规格
排序
主图/视频
图片/视频列表
更新
取消发布
历史
```

Observed input details:

```json
{
  "nameFieldName": "name",
  "slugPlaceholder": "product-slug",
  "descriptionPlaceholder": "产品描述...",
  "specsVisible": true,
  "specsState": "尚未配置规格",
  "mediaControls": ["主图/视频", "图片/视频列表"],
  "statusControl": "发布 or 取消发布 depending on current item state",
  "saveControl": "更新"
}
```

Frontend routes verified:

```text
https://mysite01.web.allincms.com/products
https://mysite01.web.allincms.com/products/{product-slug}
```

## Media, Themes, Routes, Pages

Verified backend routes:

```text
https://workspace.laicms.com/mysite01/media
https://workspace.laicms.com/mysite01/themes
https://workspace.laicms.com/mysite01/routes
```

Media state:

```text
媒体 page exists.
Current state: no media found.
Upload control exists.
```

Themes state:

```text
主题 page exists.
Default theme is enabled.
Theme shows 7 pages.
Controls include 页面, 设计, 预览.
```

Routes state:

```text
路由 page exists.
Columns: 路径, 绑定页面, 绑定状态, 备注, 更新时间.
Verified detail routes: /posts/{post}, /products/{product}.
```

Forms state:

```text
表单 page exists.
Columns: 名称, Slug, 描述, 字段, 状态, 更新时间.
Create control exists and must be treated as potentially mutating until re-checked.
```

Pages route:

```text
https://workspace.laicms.com/mysite01/pages returned 404.
Do not assume backend /pages exists.
```

## Not Verified Without Authorization

These steps require explicit user authorization because they create, edit, publish, delete, or upload remote content:

```text
create probe item
save through UI
capture real save request
replay save request
upload one sample item
publish sample
delete or unpublish probe
batch upload
batch publish
```

Do not mark them verified unless the user authorizes the side effect and the browser proof is collected in the same run.

The refreshed evidence artifact for the read-only existing-site inspection was written outside the skill package:

```text
~/allincms-projects/allincms-existing-site-readonly-2026-06-29-mysite01-refresh.json
```

It validates with:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py ~/allincms-projects/allincms-existing-site-readonly-2026-06-29-mysite01-refresh.json
```

The refreshed evidence includes a redacted `frontendRendering` block. Concrete slugs, headings, product names, article names, and issue snippets must stay out of the evidence.

## Markdown / rich-text rendering (superseded — pointer only)

The 2026-06-29 markdown-residue findings from this run (literal `**`/backticks rendering on the
frontend when a body is stored as plain Slate text; the fix = convert source markdown into the
editor's structured Slate content-block schema before saving, then audit the frontend DOM) are now
固化 as reusable rules elsewhere and should be read there, not here:
`references/field-contract.md`, `references/batch-verification.md`, Invariant INV-4 in
`references/operational-findings.md`, and the gate `scripts/validate_slate_content_shape.py`;
the frontend audit command lives in `references/batch-verification.md`
(`scripts/audit_frontend_rendering.py --json --redact`). This file keeps only the site snapshot
above (module columns, edit controls, `/pages` 404 evidence), which is not duplicated elsewhere.
