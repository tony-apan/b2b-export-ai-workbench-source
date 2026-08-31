---
title: "Mother Library Changelog"
description: "记录母库版本范围内已经发生的结构与发布合同变化；未发布工作只进入 Unreleased，不把校验结果写成发布事实。"
type: "changelog"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-31"
sources: ["Mother-library and sub-library release architecture decision 2026-07-28", "Repository routing synchronization 2026-07-29"]
related: ["README.md", "MANIFEST.md", "RELEASE.md", "VERSION.md", "wiki/00_meta/current-focus.md"]
visibility: "private"
redaction_status: "private-source-reviewed"
---
# Mother Library Changelog

## 0.3.3-working — 2026-08-31

### 治理批收口 + skill 合并 + 真源管线（每批 flash+TERRA 双审）

| 项 | 0.3.2-working | 0.3.3-working |
|---|---|---|
| skill 仓 | 独立仓（public→private 冻结） | 封存 archived；311 文件合并进母库 SKILL-INSTALL/（唯一真源，source-only 身份） |
| interface-kit 真源 | 手工 cp 双副本 | id-0073 管线：四子命令+四守卫+stale 守卫（Adopted，期限前达成） |
| 客户标识防线 | 人工清单式清扫（三次变形漏网） | 大小写不敏感机器闸（verify FAIL）+ 回流内容级去敏闸 |
| 提交纪律 | 工作树长期 dirty | C1-C6 分批 commit+push（禁 squash 保持） |

- 详细逐项对比见子库 CHANGELOG 2026-08-30 三列表与本文 0.3.2-working 治理批小节。
- 治理收尾批次（2026-08-31）：validate-sub-library 存量 390 失败修复至 STRUCTURE_PASS（`1e976bd`）；interface-kit install 轻量安装（`192da25`）；governance tests 8→0（`a867865`）——截至 `289e974` 远端 CI run `33396415381` 与本地 pre-push-check 7/7 全绿，OQ-MOTHER-0001 关闭。
- 已知边界（2026-08-31 对抗修正批更新）：license 3 卡 BLOCK（按需通关）、公开 git 历史既有标识维持接受现状。（原"validate-sub-library 存量失败修复立项中"已由上条收口。）

## 0.3.2-working — 2026-08-30

### 建站工具包治理批（四项平台审计禁令清扫 + skill 仓风控 + 凭据治理）

- 根 README 拆除 Quick Start 建站段（根页只做总导航）；建站入口 + mermaid 流程图移入 WCO README"建站一条龙"。
- WCO 子库完成禁令全仓清扫（id-0002 退役、frontend_deferred_blocks 空集化、schema/验证器/负回归测试同步、去敏 30+ 处），逐项对比表见子库 CHANGELOG 2026-08-30。
- skill 仓 allincms-bulk-content-upload 已转 private；3 个脏文件去敏后本地 commit 598b970（未 push，待授权）。
- <tmp>/ws-token.txt 明文 token 删除；文档与 scan-actions.py 全面改 WS_TOKEN 环境变量优先。
- KIT registry 登记 DOC-035/036/037 + verify 未登记覆盖检查；id-0072 待办区两处履约勾选。
- 待用户：CMS 密码轮换（OQ-AUTH-0001）、维持 private 确认（OQ-AUTH-0002）、5-commit 切分提交授权（OQ-COMMIT-0001）。
- skill 仓合并（2026-08-30 用户决策"合并进母库"）：独立仓 tony-apan/allincms-bulk-content-upload 封存（archived，保留历史）；tracked 树（除 vendor 33MB 与 _archive）导入 `sub-libraries/website-content-ops/SKILL-INSTALL/`（6.6MB）；合并前清理母库实名×2 与客户名大小写变形×2（skill 仓 00da9e0/31191ea）；~/.agents|claude|codex 三软链重指母库目录。OQ-AUTH-0002（维持 private 确认）由此**作废**。
- 提交切分方案（OQ-COMMIT-0001 授权对象；禁 squash、禁历史改写，以 git status 实数对账）：C1 禁令清扫+id-0002 退役+空集化（WCO 主体：PLAYBOOKS/PLAYBOOK/QA/START-HERE/SKILL/TEMPLATES/EXAMPLES/RUNTIME-CONTRACT/schema/scripts/ADAPTERS/WORKSPACE-TEMPLATE）；C2 interface-kit 工具面（KIT 全部 + ADAPTERS docs/TOKEN-AUTH）；C3 入口治理（根 README + WCO README）；C4 治理留痕（CHANGELOG×2 / current-focus / id-0072 / open-questions）；C5 skill 合并（SKILL-INSTALL/ 全目录 + wiki/00_meta/logs/2026/08/2026-08-30.md 当日日志）。


### 第三轮对抗审查修复（flash×2 + TERRA，14 处）

**PII/凭据清零**：
- 真实账号邮箱 → `reviewer@example.com`（issues.tsv/INDEX.md；原值见私有会话记录，不入公开文档）
- 真实格式中国手机号 → `138-0000-0000`（原值同上，去敏记录本身不得携带被去敏值——2026-08-31 终检修正）
- `wa.me/447762109411` → `wa.me/+44-7911-123456`（5 个文档全清）

**代码/配置修复**：
- `AUDIT_CONFIG_DEFAULTS` 默认 pages 去掉站点专属产品 URL；`<demo-product-slug>` → `demo-product-slug`（纯词，默认审计不再必 FAIL）
- `FORMAT-SPEC.md` migrate 签名 `<slug> <postId>` → `<article.json>`（与模块实际一致）
- `doc-registry` SCRIPT-003 audit 描述去掉已移除的 4 个 BLOCK 项（13 项口径统一）

**文档链修复**：
- RUNBOOK:98 example 客户路径 → `<task_dir>` 风格（不再悬空）
- RUNBOOK:36 本机仓库根 → 通用化
- RUNBOOK:60 ROOT-PATH-ISSUE → 任务证据相对引用
- RUNBOOK §1 vs §8 审计配置文件名统一为 `site-audit-config.template.json`
- checklist:503 formSlug 旧"无害"口径 → 断裂必修（ISS-076）
- checklist example/ 引用 8 处 → `<task_dir>` 通用描述
- README:27 THERMOS 死链 → 改指 MODULES.md / api/API-INDEX.md

**安全硬化**：
- <tmp>/ws-token.txt 补 `chmod 600` 建议（或 WS_TOKEN 环境变量优先）
- MANIFEST 增 kit 级 Apache-2.0 license 记录（3 张 source card 未闭合，状态保持 pending/BLOCK）
- 分发文件 chmod 644（防打包带 600）

### 修改对比
| 对象 | 旧 | 新 |
|---|---|---|
| 默认审计 pages | 含站点专属产品 URL（必 404） | 6 个通用导航页 |
| cta 默认占位 | `<demo-product-slug>` | `demo-product-slug` |
| PII 联系方式 | 3 处真实格式 | 假值 |
| token 指引 | 无权限硬化 | chmod 600 / WS_TOKEN |


## 0.3.1-working — 2026-08-30

### 分发就绪（flash+TERRA 对抗审查后）

- **interface-kit（50 文件 / 612KB）首次进 tracked**：`sub-libraries/website-content-ops/TOOLS/interface-kit/`
- **Apache-2.0 LICENSE + 非官方第三方客户端声明**（AllinCMS 逆向接口，不担保平台行为）
- **去敏完成**：21 文件客户标识 → 合成占位符（`<your-site-key>` / `Example Corp` / `<demo-site-key>`），9 种敏感 key 清零
- **根 README 加 Quick Start**：clone → token → verify → 建站，5 分钟上手路径
- **文档矛盾修复**：README login() 描述统一为实测结论（纯 API 可获取 token）

### 修改
| 对象 | 旧 | 新 |
|---|---|---|
| interface-kit 位置 | 仅 runtime（gitignored） | tracked `sub-libraries/wco/TOOLS/interface-kit/` |
| License | 无 | Apache-2.0 + 非官方声明 |
| README | 无建站指引 | Quick Start（5 分钟 clone→建站） |
| 客户标识 | 真实 site_key/site_id/URL | `<your-site-key>` 占位符 |


## 0.3.0-working — 2026-08-30

### 新增（+18,923 行 / 140 文件，commits `bf8d62d` + `0551b80`）

**AllinCMS 建站完整管线（从客户生产实战沉淀（已去敏））：**
- `TOKEN-AUTH.md`：3 种 token 获取方式（纯 API 登录 / 浏览器 Cookie / 半自动提取），成功+失败双路径实测
- `API-DISCOVERY.md`：平台更新后 AI 摸索接口的 7 步标准流程（重扫→反编译→对比→发现→适配→验证）
- product/site operations 模块 + contracts + 测试（`product-operations.mjs` / `site-operations.mjs`）
- `scan-server-action-ids.mjs`：42 位 hex action id 自动扫描（5th-arg 字面捕获）
- content-plan host driver + host-run template（计划驱动内容操作）
- 对审查合同 `id-0006`（adversarial review）+ 上线验收 `id-0007`（site launch acceptance）
- AllinCMS 官方教程索引 + 查询脚本

**审计管线（13 项，4 项平台 BLOCK 永久移除）：**
- `root-home` 检查项：根路径 `/` 渲染真实首页（防 `set_home_page` 回归）
- `form-render` 检查项：联系页 `<form>` 真实渲染（防 `formSlug` 空绑定断裂）
- `set_home_page()` / `update_page()` / `delete_category()` / `delete_tag()` — 从客户端 bundle 逆向发现的 4 个关键 API
- `delete-demo-content.py`：全链清理（产品+文章+分类+标签）+ `--dry-run` + 引用护栏
- `create_tag` 支持 `content_type` 参数（产品域 vs 文章域隔离）
- `create_product` / `create_post` 自动注入 `siteId`（平台校验必填）
- 跨平台 token 路径（POSIX `/tmp` + Windows `%TEMP%` 双路径搜索）
- `SCRATCH_DIR` 环境变量（会话级产物统一管理，不再 CWD 依赖）

**运行时结构 v2（四层物理分离）：**
- `id-0072`：母库（纯 tracked 知识）/ 客户运行区（独立物理根 `701_runtime/`）/ 结构化 scratch / 软链兼容
- `id-0073`：interface-kit 真源管线任务卡（迁移绑定条款）
- `.gitignore`：`customer-runtime` 无斜杠行（软链防追踪）+ `.DS_Store`

**agency-operations 子库（全新 22 文件）：**
- scripts（create-client / create-task / activate-task / runtime-search / validate）
- WORKSPACE-TEMPLATE + RUNTIME-CONTRACT.json
- canonical 注册进 `sub-libraries/registry.json`

**母库治理：**
- release evidence contract + runtime test profile 更新
- governance tests + validate-artifact + validate-mother-library 更新
- `in-repository-agency-runtime-model.md`（运行区模型）
- wiki 日志（2026-07-31 / 08-01 / 08-11）+ 来源 SRC-20260731

### 修改（vs 0.2.0）

| 对象 | 旧 | 新 | 原因 |
|---|---|---|---|
| audit 检查项数 | 14→15→16→17 项 | **13 项** | lang/canonical/jsonld/img-attrs 永久移除（用户指令） |
| 正文类型词法 | heading/paragraph | **p/h2/h3/blockquote** | 服务器存储形态统一（ISS-060/069） |
| token 获取 | 仅浏览器手动 | **纯 API 登录（首选）** | login() 从 Set-Cookie 提取（ISS-083） |
| 审计基线 | 客户站点硬编码 | **每站 `--config`** | ISS-063 假 FAIL 修复 |
| 文章页 CTA | 纯文本 | **material-story-split 块真链接** | ISS-076/077 formSlug/CTA 修复 |
| demo 清理范围 | 3 产品+3 文章 | **3+3+6 分类+7 标签全链** | ISS-071/074 taxonomy 种入发现 |
| 客户数据位置 | `customer-runtime/`（库内） | **`701_runtime/`（独立物理根+软链）** | ISS-079 四层分离 |
| interface-kit 位置 | `customer-runtime/00_shared/` | 同上（权威副本，dist 管线待建 id-0073） | flash-1 事实修正 |

### 已知边界

- `interface-kit` 真源管线（母库 tracked + dist 同步）→ 任务卡 `id-0073`（期限 2026-09-06）
- 动态路由页 meta description 平台回退 → ISS-073 记录
- 表单提交收件箱 UI 平台未提供 → ISS-076 记录
- `lang/canonical/jsonld/img-attrs` 已永久移除（用户指令 2026-08-30：禁止检查、报告、讨论）


## 0.2.0-working — 2026-07-30

- 母库身份改为私有 canonical source；私有仓库同步与公开 Stable release 分开判定。
- canonical 仓库命名为 `b2b-export-ai-workbench-source`，不含 `-private`，也不覆盖既有公开仓或旧私有仓历史。
- `website-content-ops` 升级为 `0.3.2-preview.1` Public Preview，采用 Apache-2.0，保留非 Stable 和单样本边界。


## Unreleased — 2026-07-29

- 将根 `README.md`、`AGENTS.md`、`CLAUDE.md` 和 `CONTEXT.md` 收敛为一致的入口与边界路由，详细 SOP 继续由 wiki、manifest、release guide 和子库合同维护。
- 同步母库/子库独立发布、index canonical、raw→wiki→course、日志、Skill 条件性交付和外部证据边界。
- 明确 `APPROVAL_RECORD_PASS` 只证明记录结构与候选绑定，不能证明批准者真人身份；实际 tag object SHA、signer fingerprint、canonical annotation 与 approval digest 需要外部 workflow 真实值精确比对。
- 修正远端表述：本地 `origin` 于 2026-07-29 指向 `https://github.com/suxuemi/b2b-export-ai-workbench.git`；未修改 remote，也不把本地 URL 当作远端所有权、可见性或保护配置证明。
- 母库与已注册子库仍为 `release_status: BLOCK`、`license_status: pending`、`approval_status: pending`；本节不表示已经发布。

## 0.1.1-draft — 2026-07-28

- 增加候选包外批准记录、母库与子库独立 tag namespace，以及两阶段 prepare→qualify 合同。
- approval validator 校验 sidecar 结构、scope、commit、content digest、manifest/checksum 摘要、locator 与 tag 声明绑定；名称字段过滤不构成真人身份验证。
- 强化 registry/manifest 同步、source completeness、artifact 文件集合与 checksum 校验，并保持 dirty source、许可或批准未闭环时 fail closed。

## 0.1.0-draft — 2026-07-28

- 增加母库 manifest、release guide、版本、changelog、构建器和制品校验入口。
- 明确母库与子库是独立发布 scope；母库携带子库源码不授予子库发布资格。
- 构建范围改为 manifest 驱动 allowlist/denylist，并增加 registry 机器真源和敏感路径保护。
- 初始版本保持 `BLOCK`，未宣称许可证、人工批准、独立复现或正式发布完成。
