---
title: "Distributable Sub-libraries"
description: "可独立交付子库的人类 canonical 入口；机器状态只读 registry.json，选定子库后进入其 README.md、MANIFEST.md 和 START-HERE.md。Draft/BLOCK 不代表稳定发布。"
type: "index"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-01"
sources: ["Tony conversation 2026-07-26", "Tony structure upgrade decision 2026-07-28"]
related: ["../wiki/00_meta/sub-library-contract.md", "../wiki/00_meta/publishing-and-redaction.md", "../wiki/00_meta/module-expansion-sop.md", "registry.json", "website-content-ops/README.md", "website-content-ops/MANIFEST.md", "agency-operations/README.md", "agency-operations/MANIFEST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
keywords: ["子库注册表", "独立发布", "发布合同", "Skill 边界", "latest-only", "子库入口"]
---
# 可发布子库注册表

这里放可以独立交付的任务型能力模块源码。它不是母库 `wiki/` 的复制品，也不是一个自动安装的 Skill 仓库。机器可读唯一注册表是 [`registry.json`](registry.json)；本页是人类导航，不得单独维护机器状态。新增或改名子库时，必须同时更新 registry、子库 MANIFEST、版本和入口索引。

## 规范层级

```text
sub-libraries/registry.json
  → 机器可读唯一注册表
sub-libraries/README.md
  → 人类入口和展示页；不单独维护机器状态
sub-libraries/<library>/README.md
  → 某个子库的人和 AI 入口
sub-libraries/<library>/MANIFEST.md
  → 发布边界、依赖、版本和阻断合同
sub-libraries/<library>/SKILL.md
  → 仅在适合 AI 执行时存在的条件性适配器
```

同一级不要再并列创建 `INDEX.md`、`index.md` 或第二个总注册表。每个子库只保留一个 canonical `README.md` 入口。

## 当前子库

| 子库 | 用途 | 交付形态 | 状态 | Historical / current identity | 入口 | 安装/自测 | 发布判断 |
|---|---|---|---|---|---|---|---|
| [Website Content Operations](website-content-ops/README.md) | 从公司/产品/客户语言到内容、图片、CMS 草稿、验证和写回 | `human-playbook` + `ai-skill-draft` + `toolkit` | Validated | historical `0.3.2-preview.1`; current `unassigned` / version `null` | [README](website-content-ops/README.md) | 一键安装+自测：`python3 website-content-ops/SKILL-INSTALL/install.py`（Windows 用 `install.cmd`）；自动 `npm ci` 并跑完整 11 文件自测套件 | 既有 Preview 可按已发布版本试用；当前源码候选 `BLOCK`、许可 pending、非 Stable；见 [MANIFEST](website-content-ops/MANIFEST.md) |
| [Agency Operations](agency-operations/README.md) | 同一母库根目录内的多客户私有运行区、AI 续接、作用域搜索和安全更新检查 | `human-playbook` + `toolkit` + `template-pack` | Draft / Preparation Complete | current `0.1.0-draft.1` / dirty working tree | [README](agency-operations/README.md) | 本地结构与 synthetic 准备 | 本地结构与 synthetic 准备 `complete`；真实运行、许可、审批、发布和 production 仍 `BLOCK`；见 [MANIFEST](agency-operations/MANIFEST.md) |

Agency Operations 当前是已完成本地准备的 Draft/BLOCK 子库，不是正式发布，也没有创建真实客户运行区。继续新增子库前，先通过 [Module Expansion SOP](../wiki/00_meta/module-expansion-sop.md) 的当前焦点、最小证据和停止条件。

## 子库最低合同

每个正式子库至少需要：

- `README.md`：唯一用户入口和完整导航；
- `MANIFEST.md`：包含、排除、依赖、版本、去敏和 release 状态；
- `AGENTS.md`：子库运行协议；
- `INSTALL.md`：复制、升级、回滚和卸载；
- `REFERENCES/`：独立发布所需的公开来源摘要副本；
- `START-HERE.md`、学习或执行流程、QA 和写回入口；
- 虚拟示例与可复制的空运行区模板；
- 适用时才增加 `SKILL.md`、安装说明、脚本或平台 adapter。

`SKILL.md` 是交付适配器，不是子库本体。没有稳定输入、输出、权限边界和可复核验收的模块，不得仅靠一份 Skill 文案对外宣称可用。

## 发布规则

- 所有子库必须遵守 [子库统一合同](../wiki/00_meta/sub-library-contract.md)。
- `Draft` / `BLOCK` 源码可以继续审查，但不得当作稳定外部发布包。
- 对外发布时只交付一个经过验收的 `latest` 包，不把旧版本和内部母库一起打包。
- 发布包不得含真实客户运行区、凭据、Cookie、Token、本地绝对路径或未授权素材。
- 子库之间尽量不互相引用；独立发布所需的来源摘要放进各自 `REFERENCES/`，不得使用越出子库根目录的母库 `wiki/` 或 `raw/` 本地依赖。
- 发布前必须通过链接、敏感信息、依赖边界、最小运行案例和人工批准检查。

## 更新顺序

```text
子库内容
→ 子库 README / MANIFEST / SKILL / CHANGELOG
→ 本注册表
→ wiki/index.md（只有形成通用知识时）
→ 根 README（只有公开说明变化时）
→ AGENTS / CLAUDE（只有治理或路由变化时）
```
