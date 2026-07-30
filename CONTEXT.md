---
title: "Repository Context"
description: "用极薄入口解释母库、子库、知识层、canonical 入口、Skill 与发布状态术语，并路由到权威规则和当前状态。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-29"
last_updated: "2026-07-29"
sources: ["AGENTS.md", "wiki/00_meta/current-focus.md"]
related: ["README.md", "AGENTS.md", "CLAUDE.md", "wiki/index.md", "sub-libraries/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Repository Context

- **身份**：根目录是逻辑母库；`sub-libraries/` 是独立发布子库；真实运行数据只进客户私有运行区。
- **知识链**：`raw/` 保存来源上下文，`wiki/` 保存提炼知识，`wiki/90_outputs/courses/` 保存课程表达，`wiki/00_meta/logs/` 保存事件证据指针。
- **Canonical 入口**：`wiki/` 目录使用 `index.md`；README-only 目录必须显式声明 `canonical_entry: "README.md"`；父入口只列直接下级，不递归铺平。
- **Skill**：子库不自动等于 Skill；仅 manifest 声明 `skill_entrypoint` 时交付子库内 `SKILL.md`，根目录不建第二真源。
- **发布**：母库和每个子库分别判断 `maturity_status`、`verification_status`、`release_status`、`license_status` 与 approval；彼此 PASS 不可串用。
- **证据边界**：记录结构、候选 digest、tag 字段、测试或 archive PASS 不证明真人身份、远端保护、真实效果或 Published。
- **最高规则**：[AGENTS.md](AGENTS.md)；Claude 入口：[CLAUDE.md](CLAUDE.md)；人类概览：[README.md](README.md)。
- **导航**：[wiki/index.md](wiki/index.md)；当前状态：[current-focus.md](wiki/00_meta/current-focus.md)；任务归宿：[task-router.md](wiki/00_meta/task-router.md)；子库入口：[sub-libraries/README.md](sub-libraries/README.md)。

本页只做术语和入口路由，不复制 SOP。
