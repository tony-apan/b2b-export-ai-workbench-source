---
title: "CMS Adapters"
description: "CMS adapter 入口，封装站点发现、媒体、内容、草稿、发布、验证和接口漂移。"
type: "adapter-index"
status: "Draft"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["../README.md", "allincms/article-operations.md"]
related: ["allincms-overview.md", "allincms/article-operations.md", "../_template.md", "../../TOOLS.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# CMS Adapters

## 当前参考实现

- [AllinCMS](allincms-overview.md)：当前首个 CMS 和默认图片目标。已捕获合同后不再要求每个 AI 重新抓接口。
- [AllinCMS 媒体操作唯一入口](allincms/AI-START-HERE.md)：默认调用 `uploadAllinCmsMediaSerial()`；单张原语、只读对账、图片索引和断点恢复由 adapter 管理。1–5 图语义化 UI 仅在接口漂移且用户明确批准时回退。
- [AllinCMS 文章与分类操作逻辑](allincms/article-operations.md)：已完成文章字段、分类依赖和 Server Action 形状梳理；单篇文章 update/publish 与前台列表/详情文字闭环已去敏实测通过，分类创建、标签、封面和复杂正文仍未闭合。
- [图片上传统一路由](../image-upload-routing.md)：明确 AllinCMS 与 PicGo / 外部图床的边界。

## 对用户保持简单

用户不需要理解底层请求。统一只暴露这些能力：

```text
列出我能访问的网站
上传图片并返回可用于内容的媒体资产
读取文章与分类 schema，准备一条文章草稿
删除一条经过精确核对和单独授权的媒体记录
```

adapter 内部再处理 JSON API、Server Action、RSC、SSR、对象存储、媒体登记、验证和回退。
