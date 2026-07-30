---
title: "Website Content Operations Intake"
description: "AI 从网站和资料自动盘点公司、产品、客户、内容、图片、CMS 和权限缺口。"
type: "intake"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-26"
sources: ["AGENTS.md"]
related: ["TEMPLATES/company-profile.md", "TEMPLATES/product-record.md", "PLAYBOOK.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Intake：先查，再问

## AI 自行检查

在询问用户前，优先检查用户已提供的：

- 官网首页、关于、产品、应用、案例、FAQ、联系和政策页；
- sitemap、导航、页面标题、结构化数据和站内搜索；
- 产品目录、报价表、规格书、证书和图片文件夹；
- CMS 字段、已有分类、标签、URL 规则和发布状态；
- 客户聊天、询盘、FAQ、销售异议和搜索数据；
- 当前图床和 PicGo 是否已安装、已配置、可做单图测试。

## 建立事实表

每条信息使用以下格式：

| Fact | Value | Status | Source | Source date | Conflict / note |
|---|---|---|---|---|---|
| Company name |  | confirmed / inferred / missing / conflicting | URL or file |  |  |

至少覆盖：

- 公司名称、品牌、地区、联系方式；
- 核心产品、分类、型号和别名；
- 材料、规格、用途、行业和买家角色；
- 定制能力、MOQ、样品、交期、包装和贸易条款；
- 认证、测试、工厂、案例和可用证明；
- 目标市场、客户痛点、购买触发、异议和搜索意图；
- 禁止宣传或尚未证实的说法；
- CMS、图床、域名和分析工具现状。

## 只追问阻塞项

问题按优先级分三类：

- `P0`：不回答就可能发布错误事实、覆盖数据或无法上传；
- `P1`：不回答会明显降低内容质量或转化；
- `P2`：可以先保留占位，后续补充。

AI 第一次最多问 7 个问题，优先问 P0。网站和资料已经能回答的问题不得重复问。

## Intake 完成输出

- 来源清单；
- 公司事实草稿；
- 产品记录草稿；
- 冲突清单；
- P0/P1/P2 缺口；
- 建议的小样对象；
- 所需工具和权限，但不包含凭据。
