---
title: "Release Checklist"
description: "发布到 GitHub、公开网页、社媒或客户材料前使用的去敏、版权、事实、授权和下架检查清单。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Risk review"]
related: ["publishing-and-redaction.md", "sensitive-data-inventory.md", "../10_sources/license-and-consent-register.md"]
visibility: "internal"
redaction_status: "not-reviewed"
---

# Release Checklist

发布前必须逐项检查。

## Scope

- Release target：
- Files/folders：
- Channel：GitHub / website / LinkedIn / email / client deck / ads
- Reviewer：
- Approval date：

## Hard Blocks

- [ ] 包含 `raw/` 原始资料。
- [ ] 包含客户姓名、邮箱、电话、微信、LinkedIn URL。
- [ ] 包含未授权课程 PDF、截图、课件或大段原文。
- [ ] 包含广告账户、CRM、合同、报价或后台截图。
- [ ] 包含 API key、cookie、账号密码。
- [ ] 包含社媒账号 cookie、session、验证码、恢复码、自动化脚本或批量互动/私信流程。
- [ ] 计划用 Codex 内置浏览器或脚本直接操作社媒账号。

任何一项为真，不能发布。

## Social Account Safety

- [ ] 涉及社媒账号时，已检查 [social-account-safety.md](social-account-safety.md)。
- [ ] 发布、评论、点赞、关注、加好友、私信等最终动作由人执行。
- [ ] 如使用 Chrome 插件，仅作为用户侧辅助，且由用户确认最终动作。

## Redaction

- [ ] 客户名已匿名化。
- [ ] 联系方式已删除。
- [ ] 本地绝对路径已删除。
- [ ] 具体金额/预算/转化率已范围化或授权。
- [ ] 截图已打码。
- [ ] 课程内容已改写为原创提炼。

## Rights And Consent

- [ ] 每个 source 都在 [../10_sources/license-and-consent-register.md](../10_sources/license-and-consent-register.md) 登记。
- [ ] `Public Use Allowed` 不是 `no`。
- [ ] 客户案例有授权或已匿名化。
- [ ] 第三方材料没有超范围引用。

## Publication Record

```md
## [YYYY-MM-DD] Release

- Target：
- Files：
- Reviewer：
- Approved by：
- Redaction status：
- Takedown condition：
```
