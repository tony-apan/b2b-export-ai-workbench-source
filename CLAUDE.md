---
title: "CLAUDE.md"
description: "Claude Code 进入本仓库时使用的薄路由，指向项目规则、当前状态、知识导航、子库合同和验证入口。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["AGENTS.md"]
related: ["CONTEXT.md", "AGENTS.md", "README.md", "wiki/index.md", "wiki/00_meta/current-focus.md", "sub-libraries/README.md", "scripts/README.md"]
---
# CLAUDE.md

这是 Claude Code 的**薄入口**，不复制第二套 SOP。

## 启动顺序

1. 读 [CONTEXT.md](CONTEXT.md) 对齐术语。
2. 读 [AGENTS.md](AGENTS.md) 获取最高项目规则。
3. 读 [current-focus.md](wiki/00_meta/current-focus.md) 获取当前状态和阻断。
4. 从 [wiki/index.md](wiki/index.md) 或 [sub-libraries/README.md](sub-libraries/README.md) 进入目标 scope；不要先扫描全库。

## 按任务路由

- 母库知识、业务和输出：读目标目录的 `index.md`、[task-router.md](wiki/00_meta/task-router.md) 与相关页面。
- 原始资料：从 [raw/index.md](raw/index.md) 进入，再按 [raw-to-course 流水线](wiki/00_meta/raw-conversation-and-course-pipeline.md) 提炼。
- 课程：从 [课程入口](wiki/90_outputs/courses/index.md) 进入；结构完整不等于真实课程效果。
- 日志：按 [logging-standard.md](wiki/00_meta/logging-standard.md) 写入每日事件和月度摘要，不复制 raw 原文。
- 子库：先读其 `README.md`、`MANIFEST.md`、`AGENTS.md` 和 `RUNTIME-CONTRACT.json`；仅在 manifest 声明时再读 `SKILL.md`。
- 真实客户代运营：先读 [仓库内运行模型](wiki/00_meta/in-repository-agency-runtime-model.md)，再进入本地 `customer-runtime/README.md`、`AGENTS.md` 和 `00_control/ACTIVE-CONTEXT.json`；没有明确 `client_id` 时不得扫描客户目录。
- 索引与 Markdown：遵守 [index-and-discovery-standard.md](wiki/00_meta/index-and-discovery-standard.md)；不要手改 index 生成区，命令从 [scripts/README.md](scripts/README.md) 读取。
- 发布或去敏：读当前 scope 的 manifest、[RELEASE.md](RELEASE.md)、[release-checklist.md](wiki/00_meta/release-checklist.md) 和 [check-mechanism-map.md](wiki/00_meta/check-mechanism-map.md)。

## 不可越过的边界

- 母库与子库独立判定；结构、制品、运行、课程效果、人工批准和 Published 互不替代。
- `APPROVAL_RECORD_PASS` 不能证明批准者真人身份；tag object SHA、signer fingerprint、canonical annotation 与 approval digest 必须由外部 workflow 的真实值精确绑定，远端保护和最终发布仍需外部证据。
- 真实客户、账号、凭据、经营数据和未授权原文不得直接提交到母库；公开子库只能包含经过 allowlist 与去敏审查的内容。
- 发布、登录、发送、删除、批量覆盖、修改 remote 或其他外部副作用必须得到明确授权；命令成功不等于业务验收成功。
- 涉及社媒账号时遵守 [social-account-safety.md](wiki/00_meta/social-account-safety.md)，AI 不直接自动化账号动作。

完成后报告：改动文件、运行的验证、未验证边界和下一步；不得把 `BLOCK` 美化为 PASS。
