---
title: "License And Consent Register"
description: "登记公开版来源资料的版权、授权、是否可公开使用、是否允许 raw 上传和审批状态。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["Risk review"]
related: ["source-registry.md", "../00_meta/publishing-and-redaction.md", "../00_meta/sensitive-data-inventory.md"]
when_to_read: "准备吸收、引用或公开发布一份来源资料前，用本页核对版权、同意、raw 保存和审批状态。"
keywords: ["版权登记", "授权状态", "公开发布", "raw consent", "许可证", "来源审批"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# License And Consent Register

公开版只登记公开官方资料和原创提炼。私有课程、客户资料、账号数据、截图、CRM、合同和原始 raw 不包含在本仓库。

| Source ID | Source | Copyright Status | Public Use Allowed | Raw Upload Allowed | Redaction Required | Approval Owner | Evidence / Consent Ref | Decision Date | Review Before |
|---|---|---|---|---|---|---|---|---|---|
| SRC-20260628-GOOGLE-SEARCH-OFFICIAL | Google Search Central / Search Console official public pages | public official docs | yes | source-card only | no | pending | official public URL set in source card | pending | 2026-09-28 |
| SRC-20260628-GOOGLE-ADS-MEASUREMENT | Google Ads / GA4 / GTM official public help pages | public official docs | yes | source-card only | no | pending | official public URL set in source card | pending | 2026-09-28 |
| SRC-20260628-AI-SEARCH-OFFICIAL | Google / Bing / OpenAI / schema.org / Perplexity official or primary public pages | public official docs / primary docs | yes | source-card only | no | pending | official public URL set in source card | pending | 2026-09-28 |
| SRC-20260628-SOCIAL-OPS-OFFICIAL | LinkedIn / Meta / YouTube / TikTok official public pages | public official docs | yes | source-card only | no | pending | official public URL set in source card | pending | 2026-09-28 |
| SRC-20260727-ALLINCMS-OFFICIAL | AllinCMS official public docs and sitemap | public official docs | yes | source-card only | no | pending | official public URL set in source card | pending | 2026-10-27 |
| SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL | PicGo / Cloudflare R2 / GitHub / Tencent COS / Alibaba OSS official public docs | public official docs; verify trademarks and provider terms | needs-approval | source-card only | yes | pending | official public URL set in source card; provider terms to review | pending | 2026-10-27 |
| SRC-20260726-KARPATHY-LLM-WIKI | Andrej Karpathy official public GitHub Gist | public source; derivative summary requires attribution and scope review | needs-approval | source-card only | yes | pending | source URL plus attribution note in source card | pending | 2026-10-26 |
| SRC-20260728-0001 | Original synthetic training fixture authored for repository closure testing | original synthetic fixture | yes, public-safe fixture only | yes, this fixture only | no | AI + human reviewer | raw fixture front matter: `synthetic: true`, `redaction_status: safe-to-publish` | pending / review required | 2026-10-28 |

## Public Use Rule

可以公开链接和原创摘要，不复制官方网页全文，不上传第三方课程、客户资料、账号导出或后台截图。`needs-approval`、`pending` 或没有 Approval Owner / Evidence / Decision Date 的记录都不是授权通过；母库和子库在审批完成前继续保持 `BLOCK`。