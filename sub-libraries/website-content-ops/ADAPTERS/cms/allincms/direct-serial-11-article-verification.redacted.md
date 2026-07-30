---
title: "AllinCMS Article Direct Serial 11 Verification"
description: "11 篇虚拟文章使用完整字段通过单篇接口串行保存、发布、后台刷新与前台详情验收的去敏证据。"
type: "evidence"
status: "Verified"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["Live signed-in AllinCMS article verification 2026-07-27", "article-operations.md"]
related: ["article-operations.md", "AI-START-HERE.md", "observed-contract.redacted.json"]
confidence: "high"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 11 篇文章纯接口串行验证

## 结论

2026-07-27，在当前已登录的 AllinCMS 部署和授权虚拟测试范围内，连续创建 11 篇临时文章草稿。每篇均使用完整文章 payload，通过单篇 `update` 接口保存后再用同一文章的 `publish` 动作发布，并完成后台刷新与前台详情验收。

```yaml
article_direct_serial_batch_11: verified
articles: 11
full_payload_per_article: 11/11
mode_update: 11/11
mode_publish: 11/11
backend_reload_status_published: 11/11
frontend_detail_title: 11/11
frontend_detail_body: 11/11
frontend_detail_list_text: 11/11
frontend_images_loaded_and_decoded: 55/55
cover_image_webp_1200x800: 11/11
cleanup_backend_rows_removed: 11/11
cleanup_frontend_details_404: 11/11
parallel_article_writes: not_used
one_multipart_article_batch: not_verified
cross_deployment_contract: not_verified
large_batch_beyond_this_11_run: not_verified
```

## 每篇文章的完整字段

本轮每篇文章都携带以下字段，不使用只填标题的最小 payload：

```text
title
slug
excerpt
order
coverImage
categories
tags
content
siteId
postId
mode
```

正文包含结构化 Slate 内容、真实 WebP 封面，并包含真实正文图片节点；每篇最终按 `update → publish` 顺序串行执行。动作、部署、站点和对象值均为运行时动态捕获，未写入本公开证据。

## 验收顺序

```text
创建一篇临时草稿
→ 完整 update
→ 等待响应
→ 后台刷新并确认文章行
→ 完整 publish
→ 等待响应
→ 后台刷新并确认“已发布”
→ 打开前台详情
→ 检查标题、正文、列表文本、5 张图片、封面 MIME / 尺寸 / 解码
→ 下一篇
```

一次批量 CDP 调用曾出现客户端超时。由于请求状态可能已经落地，本轮没有自动重发；先回读后台并确认 11 篇均已发布，再继续做只读前台验收。这次处理明确固化为：

```text
远程动作状态不明
→ 不自动重试
→ 后台回读
→ 只在确认缺口后由人决定下一步
```

## 清理

11 篇临时文章均已清理。第 1、2 篇先精确筛选并确认删除文案后删除；第 3—11 篇使用同一已捕获的删除 Server Action 串行删除。后台刷新后 11 个标题全部消失；误打开的一次非目标删除确认已取消，没有删除既有的“勿发布”虚拟草稿。

## 可复用边界

本轮证明的是当前部署、当前登录站点、动态捕获 action、完整字段、逐篇串行 `update → publish` 的 11 篇稳定性。它不证明：

- 503 或 transaction state mismatch 下的文章失败恢复、回滚和跨请求幂等；
- 跨部署的 action、封面对象、taxonomy 或 Slate 合同兼容性；
- 更大规模远程长跑的限流、中断恢复和全量对账；
- 当前主题已修复无序列表语义 `<ul>` 或正文图片 `<img alt>` 透传问题。
