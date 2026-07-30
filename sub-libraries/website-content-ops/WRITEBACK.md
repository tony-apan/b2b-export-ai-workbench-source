---
title: "Website Content Operations Writeback"
description: "规定建站任务完成后事实、结果、失败和通用改进分别写到哪里。"
type: "writeback"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-26"
sources: ["PLAYBOOK.md"]
related: ["AGENTS.md", "QA-CHECKLIST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 写回规则

## 写回客户运行区

以下内容默认只留在客户自己的 `workspace/`：

- 公司、产品、客户、联系人、价格和经营事实；
- 网站抓取、聊天、询盘、图片和 CMS 数据；
- 当前内容草稿、发布 URL、指标和失败记录；
- 客户自己的决策、禁用词和审批意见。

## 可申请写回私有母库

以下内容去除客户特有事实、经过人工审核后，可以进入 Tony 私有母库：

- 新的通用步骤或质量闸；
- 模板字段缺失；
- PicGo、CMS 或浏览器 adapter 的兼容经验；
- 可复现的失败模式和修复方法；
- 已获授权的案例方法。

## 不得自动回传

- 原始客户文件和聊天；
- 账号、凭据和配置；
- 未授权案例、截图和指标；
- 客户专属策略、价格和名单。

## 每次任务的学习记录

```md
## YYYY-MM-DD | task-id
- Goal:
- Sources used:
- Facts added or changed:
- Actions executed:
- Verification:
- Failures and rollback:
- Customer workspace updates:
- Generic improvement candidate:
- Human approval needed:
```
