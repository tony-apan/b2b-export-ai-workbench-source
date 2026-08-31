---
title: "SEO 检查清单（每页发布前快速过）"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（seo-check.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# SEO 检查清单（每页发布前快速过）

> 平台边界见 ID-0007 C 表（og 缺失等平台行为，不误报）。本清单检查**内容侧可控项**。

## 每页
- [ ] title 存在且 ≤60 字符；`<页面名> | <品牌>` 格式；无重复 title
- [ ] meta description 150-160 字符（任务 + 证据 + 下一步）
- [ ] 唯一 H1（CMS 生成；详情页 1 个；首页多 H1 为平台架构—记录不阻塞）
- [ ] H2/H3 层级正确（详情页正文从 H2 开始）；无跳级
- [ ] viewport 正确；slug 短可读（- 分隔，无时间戳/无中文）
- [ ] 图片均有 alt（内容+场景描述）；外链为本站目标；无死链
- [ ] 模板词（过滤 style/script）= 0；空态文案 = 0

## 页面级
- [ ] 产品/文章详情页：og:title/og:description/og:image（平台自动注入，验证存在且 og:image 200）
- [ ] sitemap：新页是否出现在 sitemap（平台自动生成；核对 URL 在列）
- [ ] robots.txt 正常（Allow / + Disallow /api/ /_next/）

## 发布后
- [ ] 公网 200；readback diff 无害；residue gate pass；截图复核
- [ ] content-status.tsv 已登记（published + URL + date）

## 注意（平台边界，不阻塞）
- 首页/列表页无 og（平台行为）
