---
title: "Quality Checklist"
description: "用于资料吸收、页面维护、业务输出和实验复盘的质量验收清单。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: []
related: []
---
# Quality Checklist

用于做 wiki 体检和任务验收。详细完成标准见 [definition-of-done.md](definition-of-done.md)。

## Markdown 基础验收

- 是否有 front matter？
- `description` 是否说明页面职责？
- `type/status/owner/created/last_updated/sources/related` 是否存在？
- 页面状态是否符合 [markdown-standard.md](markdown-standard.md)？

## 页面质量

- 页面是否有清晰标题和一句话结论？
- 关键事实是否能追溯到 `raw/`？
- 没有来源的判断是否标注为“推断”或“待验证”？
- 是否链接到相关页面？
- 是否有过时内容需要标记？

## 资料吸收验收

- 是否查重，避免重复吸收同一 source？
- 是否分配 Source ID？
- 是否登记 source registry？
- 是否更新相关页面、索引、日志？
- 是否记录 open questions？

## 结构质量

- `wiki/index.md` 是否能带人快速找到信息？
- 新增页面是否出现在对应 index？
- 是否存在重复主题页面？
- 是否存在孤立页面？
- 是否有重要概念反复出现却没有独立页面？

## 业务质量

- ICP、offer、痛点、异议是否一致？
- 网站、LinkedIn、开发信、SEO、Ads 是否共享同一套核心定位？
- 每个渠道是否有明确目标、受众、指标和下一步实验？
- 是否有“听起来很对但无法验证”的结论？

## 社媒账号安全验收

- 涉及 LinkedIn、Meta、TikTok、YouTube 等社媒账号时，是否已检查 [social-account-safety.md](social-account-safety.md)？
- 是否避免让 Codex 内置浏览器或脚本直接登录、发帖、评论、点赞、关注、加好友、私信或批量浏览社媒账号？
- 是否把 AI 的角色限制在草稿、策略、检查清单、数据分析和人工操作辅助？
- 如使用 Chrome 浏览器插件，是否明确由用户掌控登录态和最终动作？
- 是否避免记录 cookie、session、验证码、账号密码和任何规避风控方法？

## 实验质量

- 是否有 baseline？
- 是否有 primary metric 和 guardrail metric？
- 是否有样本/预算/时间上限？
- 是否有暂停、继续、放大规则？
- 是否把学习回流到 wiki？

## 发布去敏验收

- 是否检查 [publishing-and-redaction.md](publishing-and-redaction.md)？
- 是否确认 `raw/` 不公开上传？
- 是否确认公开仓库根 `README.md` 在 GitHub 首页不会显示 YAML front matter？
- 是否删除客户、联系人、电话、邮箱、账号、价格、广告数据？
- 是否删除或改写版权课程原文和截图？
- 是否删除本地绝对路径？
- 是否给页面标注 visibility 和 redaction_status？
