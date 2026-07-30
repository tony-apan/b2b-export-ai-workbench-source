---
title: "Image Manifest Template"
description: "图片语义、AI 读图、源文件指纹、平台目标映射、Alt、Caption、版权和验证记录模板。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["Tony decision 2026-07-27", "../ADAPTERS/cms/allincms/media-metadata-and-ai-vision-sop.md"]
related: ["../ADAPTERS/README.md", "../ADAPTERS/cms/allincms/media-metadata-and-ai-vision-sop.md", "../ADAPTERS/cms/allincms/article-image-binding-contract.json", "../ADAPTERS/cms/allincms/image-index-e2e-verification.redacted.md", "publish-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要登记网站图片来源、用途、尺寸、权利状态和发布绑定关系时。"
keywords: ["image manifest", "image rights", "alt text", "asset binding", "dimensions"]
---
# Image Manifest

## 资产身份与语义

| Asset ID | Source file | Source SHA-256 | Source MD5 | Product / article | Role | Rights | Description | Alt zh | Alt en | Caption | Size / format |
|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  | hero / gallery / detail / diagram / social | owned / licensed / virtual / unknown |  |  |  |  |  |

`source_sha256` 是源资产主键。MD5 只作兼容字段，不作为唯一身份。

## AI 读图记录

```yaml
asset_type:
product_ref:
product_model:
visible_features: []
visible_text: []
intended_use: []
page_context:
seo_topic:
language:
confidence:
human_review_required: true
fact_basis:
  - image_observation
uncertain_claims: []
notes:
```

规则：

- `visible_text` 是 OCR / 肉眼可见文字，不自动等于已确认产品事实；
- 参数、认证、型号、材料和性能必须与产品知识库或来源核对；
- 看不清或知识冲突时，写入 `uncertain_claims` 并把 `human_review_required` 设为 `true`；
- 装饰图在具体页面中的 Alt 可以为空；
- `description` 是私有索引语义说明，不等于 CMS 一定存在同名字段。

## 上传目标映射

一张源资产可以有多个目标记录，不要把某个 URL 当成图片本身。

| Asset ID | Destination | Site alias | Target filename | Media ID | Public URL | Normalized upload SHA-256 | Remote SHA-256 | Remote MD5 | Server transformed | Upload status | Metadata sync status | Verified at | Event / note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  | AllinCMS / R2 / GitHub / COS / OSS |  |  |  |  |  |  |  | yes / no / unknown | prepared / uploaded / verified / failed / skipped | not_applicable / pending / verified / failed |  |  |

源哈希、上传输入哈希和远端哈希必须分列。平台重编码时三者可能不同，但仍通过 `Asset ID + destination` 保持可追溯映射。

## AllinCMS 字段映射

| 语义 | 私有索引字段 | AllinCMS 媒体字段 | 当前同步状态 |
|---|---|---|---|
| 后台标题 | `title` / filename stem | `title` | 上传时来自文件名；编辑字段已观察 |
| 替代文本 | `alt` | `alt` | 媒体记录直接更新已验证；文章 occurrence 另存页面级 Alt |
| 可见说明 | `caption` | `caption`（UI 文案“说明”） | 媒体记录直接更新已验证；正文节点必须转换为 Slate 数组 |
| 完整语义说明 | `description` | 无已观察同名字段 | 仅私有索引 |
| AI 结构化结果 | `ai_metadata` | 无已观察对应字段 | 仅私有索引 |
| 内部备注 | `notes` | 无已观察对应字段 | 仅私有索引 |

上传和元数据同步是两个独立状态。元数据失败不得删除或重新上传已验证媒体。

## 文章 occurrence 绑定

资产记录回答“这是什么图片、远端映射是什么”；occurrence 记录回答“图片在这篇文章的这个位置承担什么作用”。同一 Asset ID 可以出现多次，每次都单独登记：

| Occurrence ID | Article ID | Asset ID | Source start / end | Block path / index | Before anchor SHA-256 | After anchor SHA-256 | Role | Article context | Alt | Caption | Media ID | Public URL | Binding status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  | hero / inline-detail / diagram / decorative |  |  |  |  |  | pending / verified / stale / failed |

要求：

- `Occurrence ID` 必须唯一；同一资产在 A/B/A 中的两处 A 不能共用 occurrence ID；
- `source_start / source_end + block + anchors` 共同证明原位，不得只凭图片路径或 Alt 匹配；
- 源 Markdown SHA-256 变化、token 位置变化或 anchors 变化时，清单标记 `stale` 并重建；
- `role=decorative` 时 Alt 可以为空，其他角色必须有非空 Alt；
- `caption` 在清单中保存普通文本，但写入 AllinCMS 正文时必须转换为 `[{"text":"..."}]`；
- 禁止全局字符串替换；必须按 occurrence 的字符区间从后向前替换；
- 媒体映射和 occurrence 绑定都验证后，才允许保存文章草稿。

## 文章草稿绑定验收

```yaml
source_content_sha256:
unique_assets:
image_occurrences:
unresolved_image_placeholders: 0
local_file_paths: 0
missing_asset_mappings: 0
missing_occurrence_bindings: 0
unexpected_extra_images: 0
image_order_mismatches: 0
image_position_mismatches: 0
stale_article_manifest: 0
broken_public_urls: 0
image_decode_failures: 0
missing_required_alt_in_backend_data: 0
editor_dom_alt_missing:
unreviewed_uncertain_claims: 0
backend_readback: passed / failed / not_run
editor_reload_and_render: passed / failed / not_run
editor_caption_visibility: passed / failed / not_run
published_frontend: not_run_not_authorized / passed / failed
published_theme_alt: not_run_not_authorized / present / empty / missing
```

`editor_dom_alt_missing` 是当前 AllinCMS 产品层观察项，不得偷偷改写成 0；它不否定后台 Alt 已持久化，但必须阻止“公开 SEO Alt 已生效”的结论。

## 清单单写者锁

图片资产索引与文章 occurrence 清单都必须原子写入并使用单写者锁。锁冲突默认停止。只允许确认无活动写者、无打开句柄、无待提交临时文件并在私有运行区留下证据后，人工恢复陈旧锁；禁止自动绕锁或遇到空锁直接删除。

## Single-image Test

- Test image:
- CMS / image-host adapter:
- Test time:
- Media ID:
- Result URL:
- Source SHA-256:
- Normalized upload SHA-256:
- Remote SHA-256:
- Server transformed:
- URL reachable:
- Image decodes:
- Media record persists after refresh:
- Local index written:
- AI metadata reviewed:
- CMS title / alt / caption sync status:
- Renders in Markdown / CMS:
- Backend Alt persisted:
- Editor DOM Alt present / missing / not checked:
- Caption visible in editor:
- Published theme Alt status:
- Approved for serial batch:
