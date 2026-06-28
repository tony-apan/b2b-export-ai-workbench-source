---
title: "Skill Library"
description: "记录哪些 SOP 可以继续保留为 playbook，哪些稳定流程可以升级为 Codex/Claude skill。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request"]
related: ["module-expansion-sop.md", "../_templates/skill-spec.md"]
visibility: "internal"
---

# Skill Library

Skill 不等于普通知识页。只有当一个 SOP 反复执行、输入输出稳定、工具调用明确、风险边界清楚时，才考虑升级成 skill。

## Social Account Safety Rule

任何社媒相关 skill 都必须先遵守 [social-account-safety.md](social-account-safety.md)。Skill 可以生成草稿、策略、检查清单和复盘，但不能自动登录、发帖、评论、点赞、关注、加好友、私信、批量浏览或批量采集社媒账号。用户明确要求时，可以辅助 Chrome 浏览器插件，但最终账号动作必须由人确认和执行。

## Candidate Skills

| Skill | Source Playbook | Status | Why Candidate | Risk |
|---|---|---|---|---|
| LinkedIn Post Generator | `linkedin-content.md` | idea | 可根据 brief 生成帖子草稿 | 只能生成草稿，禁止自动发布或互动 |
| SEO Brief Builder | `seo-content.md` | idea | 输入关键词生成 brief | 需要搜索和竞品验证 |
| Cold Email Sequence Builder | `cold-email.md` | idea | 输入 ICP 和观察生成邮件序列 | 需要去敏和反垃圾规则 |
| Video Script Builder | `video-production.md` | idea | 输入产品/场景生成脚本 | 需要版权和素材边界 |
| Image Brief Builder | `visual-design.md` | idea | 输入渠道和信息生成作图 brief | 需要品牌规范 |

## Promotion Flow

1. 先写 playbook。
2. 用真实任务跑 3-5 次。
3. 把稳定输入输出写进 [../_templates/skill-spec.md](../_templates/skill-spec.md)。
4. 评估工具依赖和安全边界。
5. 再考虑创建正式 skill。
