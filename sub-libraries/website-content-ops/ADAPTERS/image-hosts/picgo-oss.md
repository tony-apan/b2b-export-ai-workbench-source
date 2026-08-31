---
title: "PicGo Adapter: Alibaba Cloud OSS"
description: "使用 PicGo 阿里云 OSS uploader 完成图片上传、公开 URL 和自定义域名验证的合同。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["../../REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md"]
related: ["README.md", "../../TEMPLATES/image-manifest.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# PicGo + 阿里云 OSS

## 适用

团队已有阿里云账号、OSS bucket、域名或中国侧运维能力。

## 接入前确认

- AccessKeyId、AccessKeySecret 只进入 PicGo 或受控凭据环境；
- bucket、endpoint、上传目录、访问权限和自定义域名；
- HTTPS、CDN、CORS、缓存、删除恢复；
- GUI 与 CLI 是否读取同一配置。

## 单图验收

上传虚拟图片，验证 OSS 对象、正式 HTTPS URL、未登录访问、Markdown 与 CMS 草稿显示，再决定是否批量。
