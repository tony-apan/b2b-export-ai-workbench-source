---
title: "Bundled Public References"
description: "随 website-content-ops 独立发布的公开来源摘要；不依赖母库 wiki 路径。"
type: "references-index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-01"
sources: ["Bundled reference cards and official URLs 2026-07-28"]
related: ["../README.md", "../MANIFEST.md", "SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md", "SRC-20260727-ALLINCMS-OFFICIAL.md", "SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Bundled Public References

这里保留子库独立运行所需的公开来源摘要。它们是母库来源卡的发布副本，不是客户资料，也不替代官方文档。

| Source ID | 来源卡 | 用途 | 公开/授权状态 | 边界 |
|---|---|---|---|---|
| `SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL` | [PicGo And Image Hosts](SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md) | PicGo、R2、GitHub、COS、OSS 的公开能力和验证边界 | `content/redaction safe: links-and-original-summary`；`publication/license: pending/BLOCK` | 不包含账号、密钥、真实 bucket 或临时签名 |
| `SRC-20260727-ALLINCMS-OFFICIAL` | [AllinCMS Official Docs](SRC-20260727-ALLINCMS-OFFICIAL.md) | AllinCMS 公开文档与内部观察证据的分层 | `content/redaction safe: links-and-original-summary`；`publication/license: pending/BLOCK`；不等同 API 授权 | 不把观察到的内部请求宣称为公开 API |
| `SRC-20260731-B2B-SEO-CONTENT-RESEARCH` | [B2B SEO Content Research](SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md) | 搜索意图、客户语言、三层痛点、信息增益、层级、内链与 CTA 方法 | `method_use=internal-research-only-links-and-original-summary; publication_review=pending`；不复制网页正文 | 不证明排名、询盘或转化提升；正式使用需本站证据验证 |

## 同步规则

- 母库来源卡是源头；子库发布副本必须保留来源日期和官方 URL。
- 子库只引用本目录，不引用母库 `wiki/` 或 `raw/` 路径。
- 母库来源卡有实质变化时，更新子库副本、Source ID 授权登记、版本、变更记录并重新运行双重校验。
- 当前 bundled references 只包含官方链接和本项目原创摘要；B2B research reference 的 `method_use=internal-research-only` 只允许在内部方法研究与 Working artifact 中使用这些链接和原创总结，不等于 publication clearance。`publication_review=pending` 的来源在批准前继续阻断当前源码候选的 Public Preview publication 和 release；这不撤销既有结构测试，但不得外推为 Stable、Published 或 production-ready。外部网页正文、商标和第三方素材不包含在本项目许可证中。
