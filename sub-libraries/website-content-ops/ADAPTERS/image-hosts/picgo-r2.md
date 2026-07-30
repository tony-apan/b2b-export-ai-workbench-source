---
title: "PicGo Adapter: Cloudflare R2"
description: "使用 PicGo 的 S3 兼容接入方式把虚拟演示图片上传到 Cloudflare R2 的调查和验收合同。"
type: "tooling"
status: "Draft"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["../../REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md"]
related: ["README.md", "../../TEMPLATES/image-manifest.md", "../../TEMPLATES/tool-field-map.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# PicGo + Cloudflare R2

## 适用

面向全球公开网站，希望把图片放入对象存储并通过正式公开域名访问。

## 接入前确认

- R2 bucket 与区域 / jurisdiction；
- 使用自定义域名还是仅测试公开访问；
- PicGo 通过哪个已审核的 S3 兼容插件、Skill 或 adapter 接入；
- endpoint、bucket、路径前缀和公开 URL 生成规则；
- CORS、缓存、删除恢复和生命周期策略。

## 单图验收

上传一张虚拟产品图，验证对象 key、最终 HTTPS URL、未登录访问、Markdown 显示、CMS 草稿显示和删除 / 替换策略。没有完成这些检查前，不允许批量。

## 关键边界

R2 提供 S3 兼容 API不等于当前 PicGo 安装已具备可用 R2 uploader。必须先确认插件来源、版本、配置读取位置和实际上传结果。
