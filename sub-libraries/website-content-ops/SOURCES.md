---
title: "Website Content Operations Source Policy"
description: "规定公司事实、公开网页、聊天、课程和第三方资料的来源与版权边界。"
type: "source-policy"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-27"
sources: ["AGENTS.md"]
related: ["INTAKE.md", "QA-CHECKLIST.md", "ADAPTERS/cms/allincms-overview.md", "ADAPTERS/image-hosts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 来源规则

## 来源优先级

1. 使用者人工确认和正式文件；
2. 当前有效的证书、规格书、产品表和 CMS 数据；
3. 公司官网当前页面；
4. 客户聊天、询盘、销售记录和客服 FAQ；
5. 第三方平台和公开网页；
6. AI 推断。

低优先级来源与高优先级来源冲突时，必须显式列出，不能静默覆盖。

## 课程和公开知识

- 可以吸收公开知识和用户合法提供的课程，蒸馏为原创、可执行的知识点；
- 不复制完整课件结构、大段原文、付费 PDF、未授权截图和受限素材；
- 每条蒸馏知识保留来源、日期、许可状态和“如何用于业务”；
- 工具规则优先查官方文档；容易变化的按钮、限制和价格必须注明核验日期。

## 官方工具来源

- [AllinCMS 文档入口](https://www.allincms.com/docs)
- [AllinCMS 新建站点](https://www.allincms.com/docs/quickstart/create-site)
- [AllinCMS 图片规范与媒体库](https://www.allincms.com/docs/content/image-guidelines)
- [AllinCMS 用 Codex 自动上传网站内容](https://www.allincms.com/docs/launch/codex-auto-content-upload)
- [PicGo、R2、GitHub、COS、OSS 来源边界](ADAPTERS/image-hosts/README.md)

官方 AllinCMS 页面证明产品支持相应 UI / Codex 工作流，不自动证明存在公开、稳定的开发者 API。登录后抓到的请求必须标记为观察型内部合同，并经过回放和真实结果验证。

## 虚拟示例

所有虚拟公司、产品、聊天、指标和案例必须写明：

> 本示例为虚构演示，仅用于说明流程，不构成真实公司事实、客户案例或效果承诺。
