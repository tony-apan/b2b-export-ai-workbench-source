---
title: "Website Content Operations Source Policy"
description: "规定公司事实、公开网页、聊天、课程和第三方资料的来源与版权边界。"
type: "source-policy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-13"
sources: ["AGENTS.md"]
related: ["INTAKE.md", "QA-CHECKLIST.md", "REFERENCES/README.md", "ADAPTERS/cms/allincms-overview.md", "ADAPTERS/image-hosts/README.md"]
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

## B2B SEO 与内容方法来源

- 母库先登记 Source ID、许可、访问日期和派生页面；子库 `REFERENCES/` 只保留 standalone artifact 需要的 public-safe 摘要。
- [B2B SEO Content Research](REFERENCES/SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md) 只支持搜索意图、客户语言、信息增益、内容层级、内链和 CTA 的方法假设。
- Google 官方原则优先；Animalz、Ahrefs、CXL 等第三方公开文章只作为编辑和客户研究方法参考。
- 不复制网页正文，不把第三方案例数字写成本站承诺，也不把方法完整度外推为排名、询盘或转化已提升。

## 官方工具来源

- [AllinCMS 官方教程发现索引](REFERENCES/ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json)：按问题意图定位当前 36 个官方教程页，命中后仍需打开原页实时核验；
- [AllinCMS 文档入口](https://www.allincms.com/docs)
- [AllinCMS 新建站点](https://www.allincms.com/docs/quickstart/create-site)
- [AllinCMS 图片规范与媒体库](https://www.allincms.com/docs/content/image-guidelines)
- [AllinCMS 用 Codex 自动上传网站内容](https://www.allincms.com/docs/launch/codex-auto-content-upload)
- [PicGo、R2、GitHub、COS、OSS 来源边界](ADAPTERS/image-hosts/README.md)

官方 AllinCMS 页面证明产品支持相应 UI / Codex 工作流，不自动证明存在公开、稳定的开发者 API。教程索引也只是发现层，不能覆盖 canonical Adapter、Interface Registry、当前部署 capability、授权和回读要求。登录后抓到的请求必须标记为观察型内部合同，并经过回放和真实结果验证。

## 虚拟示例

所有虚拟公司、产品、聊天、指标和案例必须写明：

> 本示例为虚构演示，仅用于说明流程，不构成真实公司事实、客户案例或效果承诺。
