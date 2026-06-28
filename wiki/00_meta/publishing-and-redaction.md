---
title: "Publishing and Redaction"
description: "定义发布到 GitHub 或对外分享前的去敏、版权、raw 上传、wiki 派生内容和审核策略。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request"]
related: ["collaboration-model.md", "markdown-standard.md", "../10_sources/source-registry.md"]
---

# Publishing and Redaction

默认策略：`raw/` 不上传公开 GitHub，`wiki/` 也必须去敏后才能公开。

发布前必须同时检查：

- [sensitive-data-inventory.md](sensitive-data-inventory.md)
- [release-checklist.md](release-checklist.md)
- [../10_sources/license-and-consent-register.md](../10_sources/license-and-consent-register.md)
- [social-account-safety.md](social-account-safety.md)（涉及社媒账号、发帖、互动、私信或浏览器插件时）

## Publish Policy

| Folder / File | Public GitHub? | Reason |
|---|---|---|
| `raw/` | No by default | 可能包含版权课程、客户资料、聊天记录、账号数据、合同、价格、截图 |
| `wiki/10_sources/` | Redacted only | source note 可能暴露原始来源、客户、课程名称或文件路径 |
| `wiki/40_business/` | Redacted or private | 可能包含商业策略、offer、价格、客户画像 |
| `wiki/60_clients/` | No by default | 客户隐私和商业敏感信息 |
| `wiki/70_competitors/` | Usually internal | 可公开部分方法，不公开未授权截图或内部判断 |
| `wiki/90_outputs/` | Case by case | 已发布内容可公开，草稿和客户提案默认不公开 |
| `wiki/00_meta/` | Usually yes after review | 规则、SOP、模板可以公开，但删除私人路径和来源细节 |
| `wiki/30_playbooks/` | Usually yes after review | 方法论可公开，但不要复制课程原文 |

## Copyright Rules

- 版权课程、PDF、付费资料、培训材料不要上传到公开仓库。
- Wiki 可以写“自己的提炼和应用框架”，不能大段复制原文。
- 引用原文只保留短句，且标注来源和内部使用。
- 对外发布时删除课程作者联系方式、未授权截图、完整课件结构。
- 如果不确定是否可公开，标为 `visibility: private`。

## Redaction Checklist

发布前检查：

- 客户名、联系人、邮箱、电话、微信、LinkedIn URL。
- 公司内部数据、价格、利润、转化率、广告预算。
- 合同、报价、付款、交付细节。
- 课程资料、PDF 原文、截图、讲师联系方式。
- 本地绝对路径，如 `D:/work/...`。
- API key、cookie、账号、后台截图。
- 未授权客户评价、案例、Logo。
- 社媒账号 cookie、session、验证码、恢复码、自动化脚本和批量操作记录。

## Social Account Automation Red Line

- 禁止用 Codex 内置浏览器或脚本直接登录、发帖、评论、点赞、关注、加好友、私信或批量浏览社媒账号。
- 可以准备草稿、检查清单和人工操作步骤。
- 用户明确要求时，可以辅助 Chrome 浏览器插件，但最终账号动作必须由人确认和执行。
- 不要公开或入库任何社媒账号凭据、cookie、session、验证码或自动化规避方法。

## Recommended `.gitignore`

```gitignore
raw/
wiki/60_clients/
wiki/90_outputs/drafts/
*.pdf
*.docx
*.xlsx
*.csv
*.png
*.jpg
*.jpeg
*.webp
*.mp4
*.mov
.env
```

## Redacted Wiki Pattern

对外版本建议：

- 保留 SOP、模板、方法论。
- 删除客户和课程原始来源。
- 把具体客户改成 `Client A`、`Industry X`。
- 把本地文件路径改成 `internal source`。
- 把具体数字改成范围，除非已获授权。

## Visibility Field

重要页面建议加入：

```yaml
visibility: "public | internal | private"
redaction_status: "not-reviewed | redacted | safe-to-publish"
sensitivity: "public | internal | confidential | restricted"
copyright_status: "owned | licensed | public | unknown | restricted"
public_use: "yes | no | needs-approval"
approval_required: true
approved_by: ""
```
