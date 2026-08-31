---
title: "FluxPedal Motors First Closed Loop"
description: "把虚拟客户聊天转成 SEO/GEO 文章、图片、PicGo、CMS 草稿、验证和写回的首个跟做任务。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["company.md", "products.md", "icp.md", "customer-voice.md"]
related: ["../../START-HERE.md", "../../ADAPTERS/image-hosts/README.md", "../../TEMPLATES/article-brief.md", "../../TEMPLATES/image-manifest.md", "../../TEMPLATES/publish-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 第一条业务闭环

## 目标

用 `FP-HC60 Cargo Hub Motor` 的虚拟聊天完成一篇文章草稿和一张图片的小样，证明：

`客户语言 → 痛点 → 搜索意图假设 → 内容 → 图片 → 图床 → CMS 草稿 → 验证 → 写回`

## 四步跟做

### 1. 建知识

读取本目录的公司、产品、ICP 和客户聊天。把未知认证、MOQ、交期和性能结果保留为 `missing`，不得补写。

### 2. 做一个内容小样

使用 `TEMPLATES/article-brief.md` 生成一份 brief，主问题为：

> How to select a hub motor for a 20-inch cargo e-bike without relying on wattage alone?

正文必须区分解释、需要用户提供的数据、待工程验证内容和目标市场合规问题。

### 3. 做一张图片并上传

制作一张虚拟信息图：`8 inputs for cargo e-bike motor selection`。先填写 image manifest，再从 R2、COS、OSS 或 GitHub 中选择一个 adapter，完成单图上传和未登录 URL 验证。未经人工确认不批量。

### 4. 进入 CMS 草稿并写回

首个 CMS 尚未最终拍板。默认只准备工具中立字段：title、slug、summary、body、FAQ、image URL、alt、CTA、sources、status。选择 CMS 后建立字段映射，只创建草稿；验证后台和预览页后，把结果、失败和改进写回运行区。

## 通过证据

- 一份来源可追溯的 article brief；
- 一张图片的 manifest；
- 一个可在未登录浏览器打开的 HTTPS 图片 URL；
- 一条 CMS 草稿或可验证导入记录；
- 一份发布检查记录；
- 一条指标与复盘写回。

当前仅完成虚拟知识和任务设计；实际图片上传、CMS 草稿和真实页面验证仍为 `BLOCK`。
