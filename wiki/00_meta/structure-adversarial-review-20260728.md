---
title: "Knowledge Base Structure Adversarial Review 2026-07-28"
description: "针对母库、独立子库、AI Skill 适配器、发布边界和更新同步机制的升级前后对抗审查。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["Repository structure inspected 2026-07-28", "Adversarial review protocol", "Sub-library contract", "Publishing and redaction policy"]
related: ["current-focus.md", "sub-library-contract.md", "publishing-and-redaction.md", "../../sub-libraries/README.md", "../../sub-libraries/website-content-ops/RELEASE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
release_status: "BLOCK"
---
# 知识库结构升级对抗审查

## 最终结论

- **结构治理：PASS（在本次静态审查范围内）**
- **稳定外部发布：BLOCK**

这不是把子库“做成一个目录”就结束，而是把母库、子库、Skill、工具 adapter、运行区和 release candidate 的边界写成了可检查合同。结构检查通过不等于当前子库可以安装、跨环境运行或对外承诺稳定。

## 审查范围

### 已审查

- 根入口：`AGENTS.md`、`CLAUDE.md`、`README.md`、`wiki/index.md`；
- 子库注册与合同：`sub-libraries/README.md`、`website-content-ops/README.md`、`MANIFEST.md`、`VERSION.md`；
- AI 适配器：`website-content-ops/SKILL.md`；
- 发布和静态检查：`website-content-ops/RELEASE.md`、`scripts/validate-sub-library.mjs`；
- 活动 AllinCMS adapter、索引、模板、fixture 目录；
- 全库 Markdown front matter、相对链接、路径冲突、旧路径、机器绝对路径和明显凭据模式。

### 未审查

- 真实 CMS、浏览器、外部账号、安装器或跨操作系统运行；
- GitHub 发布、远程可见性、发布制品上传或第三方版权批准；
- 真实客户私有运行区；
- 跨部署 AllinCMS 合同、第二图床 / CMS 迁移和长时间批量运行。

## 升级前攻击结果

| 级别 | 证据 | 风险 |
|---|---|---|
| BLOCK | 子库虽已存在，但没有明确的 Skill 条件性适配器、源码包 / 人类包 / 工具包分层规则和发布 candidate 检查入口。 | 后续 agent 可能把“有一个 `SKILL.md`”误判为可安装产品，或把母库一起打包。 |
| BLOCK | `website-content-ops` 仍为 `0.3.0-draft`，本轮结构新增内容没有变更记录。 | 版本、入口和审计记录容易漂移。 |
| WARN | 活动文档仍引用旧的 `ADAPTERS/cms/allincms.md`，且存在 `allincms.md` 文件与 `allincms/` 目录同名歧义。 | 新人或 AI 可能打开错误入口，或者产生断链。 |
| WARN | `.obsidian/` 是本地工作区状态，且不应进入公开 release；原 `.gitignore` 未明确排除它。 | 可能泄露本机 workspace 状态和过期路径。 |
| WARN | 公共日志和 adapter 文档存在机器绝对路径。 | 发布包可暴露本机目录结构，且不可迁移。 |

## 升级动作

1. 保持 `wiki/` 与 `sub-libraries/` 并列，不建立第二套平行 `skills/` 真源。
2. 为子库明确唯一入口链：
   `sub-libraries/README.md → <library>/README.md → MANIFEST.md → AGENTS.md → 可选 SKILL.md`。
3. 将 `allincms.md` 重命名为 `allincms-overview.md`，保留 `allincms/` 作为实现目录。
4. 将子库版本同步为 `0.3.1-draft`，新增 `CHANGELOG.md`。
5. 新增 `RELEASE.md`，明确 latest-only、去敏、复制 / 安装、迁移、回滚和 `BLOCK` 条件。
6. 新增 `scripts/README.md` 与无依赖 `validate-sub-library.mjs`，使结构检查可以在另一台机器复跑。
7. 修正活动链接、source back-reference 和验证命令，去掉公开文档中的机器绝对路径。
8. 将 `.obsidian/` 加入 `.gitignore`，把本地查看器状态排除在公开发布边界外。

## 升级后证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 子库静态结构检查 | PASS | `node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs`；必需入口、front matter、活动链接、版本、旧路径、冲突和路径模式均通过。 |
| AllinCMS adapter 本地测试 | PASS | `npm test`；115 tests passed, 0 failed。 |
| 全库 Markdown front matter | PASS | 201 个 Markdown 文件抽查 / 脚本化检查，无缺失。 |
| 全库相对链接 | PASS | 脚本化检查无断链。 |
| 文件 / 目录同名 | PASS | 脚本化检查无冲突。 |
| 公开机器路径与明显凭据模式 | PASS | 排除 `.git`、`.obsidian` 后无命中；历史私有运行区改写为“仓库外的私有运行区”。 |
| release gate | BLOCK（预期） | `node sub-libraries/website-content-ops/scripts/validate-sub-library.mjs --release` 因 `MANIFEST.md: release_status: BLOCK` 阻断。 |
| 工作树 | WARN | 当前工作树本来就有大量既有修改和未跟踪资料；本轮未提交、未推送、未改变远程。 |

## 必须保留的阻断

1. 还没有可复现的 latest-only 压缩 / 打包制品和安装后验收证据；
2. `SKILL.md` 仍为 Draft / BLOCK，不能作为稳定 Skill 推荐或自动安装；
3. 没有第二图床 / CMS 的独立迁移闭环；
4. 没有跨部署、跨环境和失败恢复的完整实证；
5. 当前公开远程边界仍不允许真实客户、账号、凭据、课程原文和经营数据进入母库。

## 放行顺序

```text
结构静态 PASS
→ 生成 latest-only release candidate
→ 去敏 / 版权 / 许可人工审查
→ 另一环境从 README 复制并完成最小流程
→ 第二工具迁移闭环
→ 真实单样本与失败恢复复验
→ 才能讨论 Ready / Published
```

在上述证据完成前，任何 agent 都必须保留 `release_status: BLOCK`，不能用测试数量、版本号或“可读取”替代真实发布证据。
