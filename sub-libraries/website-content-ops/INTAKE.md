---
title: "Website Content Operations Intake"
description: "AI 从网站和资料自动盘点公司、产品、客户、内容、图片、CMS 和权限缺口。"
type: "intake"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-12"
sources: ["AGENTS.md"]
related: ["TEMPLATES/company-profile.md", "TEMPLATES/product-record.md", "PLAYBOOK.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Intake：先查，再问

## 资料提取 artifact 门禁

用户提供 PDF、DOCX、XLSX/CSV、网页、图片、brief 或聊天时，不要直接从一次阅读结果拼 CMS payload：

1. 原始资料进入锁定的 `client_id/company_id/task_id` 私有 scope，并登记原文件或网页快照 SHA-256；
2. 按宿主真实能力复制 [Source Extraction](TEMPLATES/source-extraction.md)，使用对应 Schema/validator 保存 locator、extraction digest、提取器/version、置信度和 warning；
3. `complete/partial` 的 units 只作为 claim candidates；OCR、动态网页、合并单元格或来源冲突不得静默提升为 confirmed；
4. 宿主缺少解析能力时标记 `blocked`，依赖该来源的字段停止，不得用示例值或通用默认值补齐；
5. extraction artifact 含客户原文，只能进入 `customer-runtime/`，不得提交到母库或公开 artifact。

## 资料驱动的新建 / 更新补充

用户提供文件或 URL 后，先形成 source snapshot 和 Source Extraction，而不是直接生成 CMS payload：

- 每份 PDF、DOCX、表格、网页、图片、brief 和聊天都有 `source_id`、原始字节/快照 SHA-256、日期、位置指针、所有权与 publication clearance；
- 提取结果保留页码、sheet/单元格、段落、图片或 DOM selector；OCR 和 AI 摘要是 derived，不替代原始来源；
- 逐字段标记 `confirmed / inferred / missing / conflicting / expired`；认证、规格、价格、MOQ、交期、联系人、案例和效果默认不能靠推断进入 mutation；
- 区分用户要 `create`、`update` 还是 `upsert`。更新时必须收集精确对象 ID 或站点内唯一 slug/external key，并明确哪些字段保持、变更或显式清空；
- 目标 CMS 的字段、枚举、站点 ID、Action ID 和部署 fingerprint 由运行时只读探索，不从 intake 模板预填。

资料和目标稳定后，进入 [Source-Driven CMS Create and Update SOP](PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md)，生成 [Content Operation Plan](TEMPLATES/content-operation-plan.md)。`confirmed/inferred` claim 必须绑定 Source Extraction 的精确 locator/digest，mutation 字段必须绑定 `claim_refs/derivation`。新建站必须先生成 account-scope Plan A，仅创建站点；回读真实 site identity 后再生成 site-scope Plan B，不得在一个计划中 create site + populate。


## AI 自行检查

在询问用户前，优先检查用户已提供的：

- 官网首页、关于、产品、应用、案例、FAQ、联系和政策页；
- sitemap、导航、页面标题、结构化数据和站内搜索；
- 产品目录、报价表、规格书、证书和图片文件夹；
- CMS 字段、已有分类、标签、URL 规则和发布状态；
- 客户聊天、询盘、FAQ、销售异议和搜索数据；
- 当前图床和 PicGo 是否已安装、已配置、可做单图测试。

## 建立事实表

每条信息使用以下格式。对会随时间变化的认证、规格、MOQ、交期、价格、联系人、能力和政策，必须记录 `review_after` 或 `expires_at`；超过期限而未重新确认时，状态改为 `expired`，不得继续沿用 `confirmed`：

| Fact | Value | Status | Source | Source date | Conflict / note |
|---|---|---|---|---|---|
| Company name |  | confirmed / inferred / missing / conflicting / expired | URL or file |  |  |

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
