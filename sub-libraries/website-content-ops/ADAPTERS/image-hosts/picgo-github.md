---
title: "PicGo Adapter: GitHub"
description: "使用 PicGo GitHub uploader 完成无敏感、小规模图片演示的配置字段和使用边界。"
type: "tooling"
status: "Draft"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["../../REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md"]
related: ["README.md", "../../TEMPLATES/image-manifest.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# PicGo + GitHub

## 适用

无敏感、小规模、可公开的课程演示或迁移练习。

## 接入前确认

- 使用独立演示 repository，不与源码母库混放；
- repository、branch、图片路径和公开 URL 规则；
- token 只保存在受控凭据环境，不写入 Markdown；
- 文件大小、仓库增长、GitHub Pages 使用限制和删除后的历史残留。

## 单图验收

验证 commit / object 已产生、公开 URL 可访问、Markdown 可显示、重名策略明确，并记录如何撤销本次演示。

## 关键边界

GitHub 是代码与协作平台，不默认等于生产图片 CDN。真实网站长期图片应优先评估对象存储或 CMS 媒体库。
