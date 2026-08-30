---
title: "Source Note: AllinCMS Official Docs"
description: "登记 AllinCMS 当前 36 个公开教程页的发现快照，并界定公开 UI 教程与内部接口抓取证据的边界。"
type: "source-note"
source_id: "SRC-20260727-ALLINCMS-OFFICIAL"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-08-13"
sources: ["https://www.allincms.com/docs", "https://www.allincms.com/docs/quickstart/create-site", "https://www.allincms.com/docs/content/image-guidelines", "https://www.allincms.com/docs/launch/codex-auto-content-upload", "https://www.allincms.com/sitemap.xml"]
related: ["ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json", "../ADAPTERS/cms/allincms-overview.md", "../ADAPTERS/cms/allincms/article-operations.md", "../ADAPTERS/cms/allincms/INTERFACE-INDEX.md", "../TOOLS.md"]
confidence: "high"
review_after: "2026-11-13"
visibility: "public"
redaction_status: "safe-to-publish"
publication_review_status: "pending"
publication_status: "BLOCK"
license_status: "pending"
---
# Source Note: AllinCMS Official Docs

## 当前结论

2026-08-13 从官方 `sitemap.xml` 发现 38 个同域 URL；排除官网首页和搜索页后，36 个 `/docs` 页面均通过低速串行 HTTP 读取返回 200。机器可查清单见 [AllinCMS Official Tutorial Discovery Index](ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json)。该索引只保存 URL、页面标题/H1、原创摘要、问题意图和核验边界，不复制官方正文或图片。

AllinCMS 官方公开文档已经确认以下用户路径：

- 从工作台创建或进入网站，并完成主题、Home 页面与基础设置；
- 建站后准备图片，创建或编辑产品、产品分类、文章和页面；
- 配置导航、联系入口、页面模块、域名、统计、搜索收录和上线检查；
- Codex 可以读取资料、操作后台、先做单条样例、再批量，并在前台验收；
- 页面、产品或文章改错后，可以从对应编辑器检查并恢复历史版本。

官方公开文档目前提供的是后台操作与内容工作流说明，不足以证明存在稳定、公开、受支持的开发者 API。课程和 adapter 因此必须区分：

1. **官方公开能力**：AllinCMS 支持网站、媒体、产品、文章和前台验收工作流；
2. **实际环境观察**：登录后通过浏览器 Network / CDP 观察站点列表和图片上传的真实请求；
3. **内部接口合同**：只有完成抓取、去敏、回放和验证后，才能标记为 `observed_internal_contract`；
4. **公开 API**：没有官方开发者文档或平台确认前，不得标记为 `public_api`。

## 对课程的约束

- 不向小白展示 cookie、Server Action ID、预签名 URL 或对象存储细节；
- 用户看到的仍是“选择网站 → 上传图片 → 得到可用链接 → 插入内容 → 验证”；
- 技术复杂度封装在 AllinCMS adapter 中；
- 只有 canonical Adapter 报告合同缺失或漂移、且用户明确批准只读发现或 UI 回退时，才允许用 UI 辅助观察；正常执行保持 API-first，不静默回退；
- 先做一张测试图和一个草稿，不能直接批量或发布。

## 尚未由官方文档证明

本次 36 页公开教程盘点没有发现明确的开发者 API 总览、认证或版本文档，也没有发现以下合同：

- `user.id` 获取 API；
- 当前账号完整网站列表 API、分页和字段合同；
- 新建网站 API 的 payload、返回字段和支持承诺；
- 产品分类、文章分类、标签、媒体、文章或产品的公开 API 字段与 mutation 合同；
- 图片上传是单请求、预签名多阶段还是 Server Action；
- 返回值是否包含永久公开 URL、媒体 ID、对象 key 和图片元数据；
- 内部接口的兼容承诺、限流、幂等和版本策略。

这些字段只能由登录后的真实请求和响应补证，不能从路由名称猜测。
