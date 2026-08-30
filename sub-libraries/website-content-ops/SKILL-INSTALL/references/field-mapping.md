---
doc_id: allincms-bulk-field-mapping
title: AllinCMS 字段映射核实
description: LAICMS / AllinCMS 批量上传前的列表页和编辑页字段映射核实流程
layer: ops
status: draft
created: 2026-06-29
updated: 2026-06-29
page_type: reference
sources: []
confidence: medium
---

# Field Mapping

Use this reference when inspecting a content type for the first time on a site or after a backend version change.

After mapping visible fields, read `field-contract.md` to document field meanings, risks, and verification evidence before creating a payload template.

## Target Type

Confirm one of:

```text
posts    = articles
products = products
media    = media library
themes   = theme/page management, if page-like content is under themes
routes   = frontend route bindings
```

Do not assume `pages` is a backend path. On at least one verified site, `/pages` returned 404 and page-like management lived under `themes` and `routes`.

Record:

```json
{
  "siteKey": "",
  "backendListUrl": "",
  "frontendBaseUrl": "",
  "contentType": "posts",
  "inspectedAt": "YYYY-MM-DD",
  "notes": []
}
```

## List Page Inspection

Read visible columns only. Do not edit rows. Do not copy row values, titles, descriptions, slugs, content IDs, account menu text, or business copy into the skill or run evidence. For evidence, record table headers, search placeholders, filter/control labels, and route shape only.

For posts, check:

```text
title
slug
excerpt
order
status
category
tags
created time
updated time
```

For products, check:

```text
media or cover
name or title
slug
description
order
status
category
tags
created time
updated time
specs, price, SKU, gallery, variants, inventory, if visible
```

If columns differ materially, pause and inspect the model before upload.

## Edit Page Inspection

Open one existing item and map actual controls without saving.

Do not click a list-page `创建` button just to inspect fields unless the user authorizes remote draft creation. On the verified site, clicking `创建` on posts/products immediately created an `Untitled ...` draft and navigated to its update page.

For posts, map:

```text
body editor
title
slug
category
tags
excerpt
order
cover image
update button
publish or unpublish control
```

For products, map:

```text
body editor
name or title
slug
category
tags
description
order
cover image or media
specs
price
SKU
gallery
update button
publish or unpublish control
```

## Mapping Record

Keep a compact mapping in the run notes. Use the per-type field names from the authoritative
contract in `server-action-save-api.md` §3 — **products use `name` + `specifications` + `media`;
posts use `title` + `excerpt` + `coverImage`**. Do NOT carry `title`/`specs` into a product
payload; those are the old assumption that `server-action-save-api.md` §3 calls out as breaking
fields (会挂字段). A products example:

```json
{
  "contentType": "products",
  "nameField": "name",
  "descriptionField": "description",
  "mediaField": "media",
  "bodyField": "content",
  "idField": "productId",
  "publishControl": "Publish",
  "statusValues": ["draft", "published"],
  "extraRequiredFields": ["specifications"]
}
```

For posts the record is `titleField: "title"`, `excerptField: "excerpt"`, `coverField: "coverImage"`.
Do not convert this record into a reusable payload until request capture confirms the same keys
in the real save request; `server-action-save-api.md` §3 is the authority when they disagree.

## Create-Flow Inspection

Create buttons are not uniformly read-only:

```text
posts/products:
  clicking 创建 can immediately create an Untitled draft and open an update page.
  treat the click itself as a remote write.

routes/themes:
  clicking 创建 opened a dialog in the verified run.
  final submit buttons still create remote records and require explicit authorization.

media:
  上传 starts the upload flow and may open a file picker or transmit files.
  do not click or select files without explicit upload authorization.
```

If an accidental draft is created during exploration, stop and report the exact observed draft pattern. Do not delete it without explicit deletion authorization.
