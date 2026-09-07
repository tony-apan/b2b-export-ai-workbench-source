---
title: "Website Content Operations License"
description: "说明 website-content-ops 历史公开 Preview 的 Apache-2.0 范围，以及三张 source card 逐卡 clearance 后的许可边界（license_status: cleared，候选仍 BLOCK）。"
type: "legal-notice"
status: "Working"
owner: "Human"
created: "2026-07-28"
last_updated: "2026-09-07"
sources: ["LICENSE", "NOTICE", "THIRD-PARTY-NOTICES.md", "MANIFEST.md"]
related: ["MANIFEST.md", "RELEASE.md", "REFERENCES/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
state_source: "MANIFEST.md"
state_projection: ["release_status", "license_status"]
release_status: "Preview"
license_status: "cleared"
---
# License

既有 `v0.3.2-preview.1` 独立发布 artifact 中已获许可的原创代码、Markdown 文档、模板、配置和 synthetic fixtures 采用 **Apache License 2.0**。AllinCMS official、PicGo image-host official 与 B2B research reference 三张 source card 已于 2026-09-03 逐卡 clearance，包级 `license_status: cleared`（B2B research reference 的 `method_use` 仍为 internal-research-only）；这只闭合来源许可，不构成发布资格——当前源码候选仍是 `release_status: BLOCK`、`preview_publication_status: BLOCK`（2026-09-07 ISS-141 事故回退），母库裸 tag `v0.4.0-preview.1` 为非规范历史引用，不改变许可结论。这不追溯改变既有 artifact 的许可。完整法律文本见 [LICENSE](LICENSE)。

许可证不自动覆盖：

- AllinCMS、PicGo、Cloudflare、GitHub、腾讯云、阿里云等第三方名称、商标、产品或官方网页内容；
- 通过外链加载的 Tony 微信二维码图片；
- 用户自己的客户资料、账号、凭据、网站内容、图片与客户私有运行区；
- 未被 `MANIFEST.md` include allowlist 纳入独立 artifact 的母库文件。

第三方来源和归属说明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) 与 [NOTICE](NOTICE)。本项目按“现状”提供；Preview 状态不构成稳定性、生产适用性或专业法律意见承诺。
