---
title: "Social Account Safety Red Lines"
description: "定义 AI、Claude、Codex、浏览器插件和自动化工具处理 LinkedIn、Meta、TikTok、YouTube 等社媒账号时的账号安全红线。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User instruction"]
related: ["ai-operating-manual.md", "quality-checklist.md", "../30_playbooks/linkedin-content.md", "../50_channels/linkedin/index.md"]
visibility: "internal"
redaction_status: "not-reviewed"
---
# Social Account Safety Red Lines

这页是社媒账号安全红线。任何 Claude、Codex、skill、browser automation、脚本或外部工具，只要涉及 LinkedIn、Meta、Facebook、Instagram、TikTok、YouTube、X/Twitter 等社媒账号，都必须先遵守这里。

## Hard Red Line

禁止让 AI 直接操作社媒账号。自动化登录、发帖、评论、点赞、关注、加好友、私信、批量浏览、批量抓取联系人、批量邀请、批量互动，都可能触发平台风控甚至封号。

## 禁止行为

- 禁止使用 Codex 内置浏览器或浏览器自动化直接登录社媒账号。
- 禁止用 Codex 浏览器自动发布 LinkedIn、Meta、TikTok、YouTube 等内容。
- 禁止自动点赞、评论、关注、加好友、发私信、撤回、删除或修改社媒内容。
- 禁止批量访问个人主页、批量采集联系人、批量导出私信或联系人资料。
- 禁止模拟真人互动、绕过平台限制、规避风控或验证码。
- 禁止把 cookie、session、账号密码、验证码、恢复码写入 raw/wiki。
- 禁止把“可自动化执行”写进社媒 skill、SOP 或工作流。

## 允许行为

- 可以让 AI 生成内容草稿、评论草稿、私信草稿、内容日历、选题、复盘和检查清单。
- 可以让 AI 分析用户提供的已导出数据、截图、帖子链接和手动整理的表现数据。
- 可以让 AI 设计手动操作 SOP，例如发布前检查、评论回复标准、私信分层规则。
- 可以在用户明确授权和人工监督下，辅助使用用户已安装的 Chrome 浏览器插件。
- 可以用 Chrome 插件做合规的辅助检查、复制草稿、格式校验或页面观察，最终发布、互动、私信必须由人确认和执行。

## Chrome 插件边界

Chrome 浏览器插件可以作为用户侧辅助工具，但必须满足：

- 用户明确要求使用该插件。
- 用户自己掌控登录态和最终动作。
- AI 不保存、不读取、不传播账号凭据、cookie 或 session。
- AI 不绕过平台风控、验证码或速率限制。
- 任何发帖、评论、点赞、加好友、私信等账号动作，都需要人类最后确认。

## Codex 浏览器边界

Codex 内置浏览器适合查资料、打开公开页面、检查本地网站和验证 UI。不允许用它登录或自动化操作社媒账号。

## Skill / Automation Rule

所有社媒相关 skill 只能做“准备”和“分析”，不能做“执行账号动作”。

允许：

- 生成 LinkedIn 帖子草稿。
- 生成评论/私信候选文案。
- 分析已导出的表现数据。
- 生成发布 checklist。

禁止：

- 自动发布。
- 自动评论。
- 自动私信。
- 自动加好友。
- 自动批量浏览或采集。

## 发现冲突时

如果用户、SOP、skill 或工具说明要求直接操作社媒账号，按本页红线处理：

1. 停止自动化账号动作。
2. 改为输出草稿、步骤和人工检查清单。
3. 提醒用户该动作存在封号风险。
4. 如需使用 Chrome 插件，只能在用户明确要求和人工确认下做辅助。
