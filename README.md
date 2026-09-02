<!--
Repository metadata:
title: "B2B Export AI Workbench"
description: "面向人和 AI 的外贸增长知识母库入口，说明母库、独立子库、知识层与发布状态应从哪里读取。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-08-30"
sources: ["AGENTS.md", "wiki/00_meta/private-master-and-sub-library-model.md"]
related: ["CONTEXT.md", "wiki/index.md", "AGENTS.md", "CLAUDE.md", "wiki/00_meta/current-focus.md", "wiki/00_meta/in-repository-agency-runtime-model.md", "sub-libraries/README.md", "sub-libraries/agency-operations/README.md"]
visibility: "private"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
-->
# B2B Export AI Workbench

外贸增长 AI 工作台：本仓库是私有、持续演进的逻辑**母库**，`sub-libraries/` 保存可独立交付和独立判定发布状态的**子库**。本页只帮助人和 AI 找到正确入口，不复制治理 SOP。

## 仓库分层

| 层 | 用途 | 入口 |
|---|---|---|
| `raw/` | 来源接入与原始上下文；公开包默认只含入口、模板和被精确 allowlist 的安全 synthetic fixture | [raw/index.md](raw/index.md) |
| `wiki/` | 提炼后的知识、业务模型、playbook、治理与输出 | [wiki/index.md](wiki/index.md) |
| `wiki/90_outputs/courses/` | 从来源与知识链提炼的课程模块、练习、验收和写回 | [课程入口](wiki/90_outputs/courses/index.md) |
| `wiki/00_meta/logs/` | 按日事件与证据指针、按月摘要；不是第二知识库 | [日志入口](wiki/00_meta/logs/index.md) |
| `sub-libraries/` | 可独立发布的能力模块；每个 scope 使用自己的 manifest、运行合同和发布证据 | [子库入口](sub-libraries/README.md) |
| `customer-runtime/` | 根目录下 Git 隔离的真实客户私有运行区；由 agency-operations 初始化，母库更新不得覆盖 | [运行模型](wiki/00_meta/in-repository-agency-runtime-model.md) / 初始化后本地 `customer-runtime/README.md` |

`wiki/` 的目录 canonical 入口使用 `index.md`；允许 README-only 的非 wiki 目录必须显式声明 `canonical_entry: "README.md"`。父级入口只索引直接文件和直接子目录入口，不递归铺平全库。

---

## 我要建站 / 使用本仓库能力

> **状态口径**：`website-content-ops` 当前是源码候选（Working），历史 `v0.3.2-preview.1` 可继续按其范围试用；当前源码候选发布状态 `BLOCK`，不代表 Stable 或 production-ready。本仓库可让“人 + AI”在干净账号上从资料建站并自测，但真实客户资料、账号、凭据只进独立客户私有运行区，不进公开提交。

### 快速上手：用资料直接建站

把下面这段整体复制发给一个能读写本地文件、能跑 Python/Node、有浏览器能力的 AI：

```text
使用本仓库的 Website Content Operations 能力建站。
1. 先读 sub-libraries/website-content-ops/README.md、AGENTS.md、MANIFEST.md、
   TOOLS/interface-kit/NEW-SITE-ONEPASS.md 与 RUNBOOK-ANYONE.md，不要扫描无关目录。
2. 检查环境并安装依赖：运行 sub-libraries/website-content-ops/SKILL-INSTALL/install.py
   （Windows 用 install.cmd）；它会自动 npm ci 并跑完整自测，缺失 Node/Python 时给出可复制安装命令。
3. 我提供客户资料（PDF/DOCX/表格/网站/图片均可）与 site-key 偏好。
4. 先只读核对账号/目标站点与当前能力；列出建站与发布计划，等我批准后再严格串行执行。
5. 删除类操作（站点/产品/文章/分类/标签/媒体/主题，含 delete-demo-content 与 --force/--confirm）
   永远逐条列目标等我确认。token 只放环境变量，不落盘、不入日志。
6. 完成后用 audit / acceptance-v2 逐项验收并报告证据，不把 HTTP 200 当成功。
```

### 本仓库能做什么（按目标找入口）

| 我的目标 | 入口 |
|---|---|
| 用资料从零建 AllinCMS 网站 | [Website Content Operations（建站一条龙）](sub-libraries/website-content-ops/README.md) |
| 更新现有网站的产品/文章 | [WCO 内容更新与 review 门](sub-libraries/website-content-ops/README.md) |
| 新建客户私有代运营运行区 | [Agency Operations](sub-libraries/agency-operations/README.md) |
| 给 AI 注册成可调用 Skill | [WCO SKILL-INSTALL 安装说明](sub-libraries/website-content-ops/SKILL-INSTALL/README.md) |
| 只查外贸/建站知识 | [wiki 导航](wiki/index.md) |
| 查看所有可独立交付模块 | [子库注册表](sub-libraries/README.md) |

安装与自测命令（在 clone 根执行）：

```bash
# 1) 基础自检（应 VERIFY PASS；remote-refs WARN 属正常）
cd sub-libraries/website-content-ops/TOOLS/interface-kit && python3 index/registry_tools.py verify && cd ../../..

# 2) 一键安装 Node 依赖 + 全量自测 + 注册 Skill（Windows 用 install.cmd）
python3 sub-libraries/website-content-ops/SKILL-INSTALL/install.py          # 加 --dir=<skills目录> 指定目标

# 3) 可选：PDF/DOCX/PPTX/XLSX 解析能力
python3 sub-libraries/website-content-ops/TOOLS/interface-kit/install-deps.py --yes
```

---

## 从这里开始

- 新 agent 术语路由：[CONTEXT.md](CONTEXT.md)
- 最高项目规则：[AGENTS.md](AGENTS.md)
- Claude 薄入口：[CLAUDE.md](CLAUDE.md)
- 当前状态与阻断：[current-focus.md](wiki/00_meta/current-focus.md)
- 人和 AI 的知识导航：[wiki/index.md](wiki/index.md)
- 子库机器注册表：[sub-libraries/registry.json](sub-libraries/registry.json)
- 多客户代运营运行区：[Agency Operations](sub-libraries/agency-operations/README.md)；初始化前先读 [仓库内运行模型](wiki/00_meta/in-repository-agency-runtime-model.md)
- 检查结果能证明什么：[check-mechanism-map.md](wiki/00_meta/check-mechanism-map.md)
- 任务完成标准：[definition-of-done.md](wiki/00_meta/definition-of-done.md)

## 安全与发布边界

- 即使母库为私有仓库，真实客户、账号、凭据、课程原文和经营数据仍不得直接提交；它们进入独立客户私有运行区。
- 子库不自动等于 Skill。只有 manifest 声明 `skill_entrypoint` 时，子库内的 `SKILL.md` 才是条件性交付入口；根目录不建立第二真源 `skills/`。
- 母库与每个子库分别判定。一个 scope 的结构、制品或测试 PASS 不得替代另一个 scope 的证据。
- `APPROVAL_RECORD_PASS` 只证明记录结构和候选绑定；本地校验、候选 archive、checksum、签名字段或 attestation 均不能单独证明真人身份、远端保护或已经 Published。
- 母库的私有源码同步与子库的公开发布分开判定：母库可同步到私有 canonical 仓；`website-content-ops` 仅以 Preview 公开，不代表 Stable 或 production-ready。

发布前从 [母库合同](MANIFEST.md)、[发布指南](RELEASE.md)、[发布状态机](wiki/00_meta/release-state-machine.md) 和 [发布检查清单](wiki/00_meta/release-checklist.md) 进入。所有命令以 [scripts/README.md](scripts/README.md) 和目标子库自己的合同为准，避免在根入口复制易漂移命令。

## 许可

母库是私有内部源码，不授予公开再分发许可，见 [LICENSE.md](LICENSE.md)。公开子库使用自己的许可证和发布状态；母库私有同步不等于公开授权，Preview 也不等于稳定发布。
