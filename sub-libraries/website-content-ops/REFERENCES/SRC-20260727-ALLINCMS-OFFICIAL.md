---
title: "Source Note: AllinCMS Official Docs"
description: "登记 AllinCMS 建站、图片、Codex 内容上传公开文档，并界定公开 UI 教程与内部接口抓取证据的边界。"
type: "source-note"
source_id: "SRC-20260727-ALLINCMS-OFFICIAL"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-01"
sources: ["https://www.allincms.com/docs", "https://www.allincms.com/docs/quickstart/create-site", "https://www.allincms.com/docs/content/image-guidelines", "https://www.allincms.com/docs/launch/codex-auto-content-upload", "https://www.allincms.com/sitemap.xml"]
related: ["../ADAPTERS/cms/allincms-overview.md", "../ADAPTERS/cms/allincms/article-operations.md", "../TOOLS.md"]
confidence: "high"
review_after: "2026-10-27"
visibility: "public"
redaction_status: "safe-to-publish"
publication_review_status: "pending"
publication_status: "BLOCK"
license_status: "pending"
---
# Source Note: AllinCMS Official Docs

## 当前结论

AllinCMS 官方公开文档已经确认以下用户路径：

- 从工作台的网站列表创建或进入网站；
- 建站后在媒体库上传图片，再用于产品、文章和页面；
- Codex 可以读取资料、操作后台、先做单条样例、再批量，并在前台验收。

官方公开文档目前提供的是后台操作与内容工作流说明，不足以证明存在稳定、公开、受支持的开发者 API。课程和 adapter 因此必须区分：

1. **官方公开能力**：AllinCMS 支持网站、媒体、产品、文章和前台验收工作流；
2. **实际环境观察**：登录后通过浏览器 Network / CDP 观察站点列表和图片上传的真实请求；
3. **内部接口合同**：只有完成抓取、去敏、回放和验证后，才能标记为 `observed_internal_contract`；
4. **公开 API**：没有官方开发者文档或平台确认前，不得标记为 `public_api`。

## 对课程的约束

- 不向小白展示 cookie、Server Action ID、预签名 URL 或对象存储细节；
- 用户看到的仍是“选择网站 → 上传图片 → 得到可用链接 → 插入内容 → 验证”；
- 技术复杂度封装在 AllinCMS adapter 中；
- 第一次允许用 UI 触发真实动作并抓取协议，后续优先接口回放；
- 先做一张测试图和一个草稿，不能直接批量或发布。

## 尚未由官方文档证明

- 当前账号网站列表的独立 JSON API URL；
- 图片上传是单请求、预签名多阶段还是 Server Action；
- 返回值是否包含永久公开 URL、媒体 ID、对象 key 和图片元数据；
- 内部接口的兼容承诺、限流、幂等和版本策略。

这些字段只能由登录后的真实请求和响应补证，不能从路由名称猜测。
