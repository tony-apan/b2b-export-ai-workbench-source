---
title: "Current Focus"
description: "给人和 AI 提供一到两屏的当前唯一焦点、已证实状态、现存阻断、下一动作与证据入口；历史过程已移入月度历史页。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-11"
sources: ["Tony conversation 2026-07-26", "Tony decisions 2026-07-27", "Local repository evidence 2026-07-29", "Tony publication authorization 2026-07-30", "GitHub remote verification 2026-07-30", "Local B2B SEO adversarial evidence 2026-07-31", "Authorized redacted existing-article optimization and publish acceptance 2026-07-31", "Tony preparation-only acceptance 2026-08-01", "F23 local immutable review and four-reviewer closure 2026-08-11"]
related: ["current-focus-history-2026-07.md", "check-mechanism-map.md", "open-questions.md", "in-repository-agency-runtime-model.md", "../../MANIFEST.md", "../../sub-libraries/agency-operations/README.md", "../../sub-libraries/website-content-ops/README.md", "logs/2026/07/2026-07-30.md", "logs/2026/07/2026-07-31.md", "logs/2026/08/2026-08-01.md", "logs/2026/08/2026-08-11.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 当前焦点

## Current Focus

**Agency Operations 本地准备阶段已经收口完成**：用户可把完整母库放在一个根目录内，未来再把多客户、多公司、多产品、多网站、社媒、来发信和邮件运行数据放入 Git 隔离的 `customer-runtime/`。当前已建立上游 Core / 初始化 Template / 私有 Runtime 三层合同、显式 `client_id` 搜索边界、TASK/HANDOFF 续接模型和 Draft/BLOCK 子库；本轮没有创建真实运行区，自动母库更新第一版只允许 `--check`，不允许 fetch/pull/apply。后续真实客户、备份、远程 apply 或发布只有另行立项和授权后才进入 Current。

当前入口：[运行模型](in-repository-agency-runtime-model.md) → [Agency Operations README](../../sub-libraries/agency-operations/README.md) → [START-HERE](../../sub-libraries/agency-operations/START-HERE.md)。Website Content Operations 的历史 Preview 和当前 release BLOCK 继续保留，但本阶段不再作为唯一 Current。

## Current State

**母库历史私有同步：`Synced / remote CI PASS`；子库历史 `v0.3.2-preview.1`：`Published with WARN`；当前未发布源码候选 publication/release：`BLOCK`；母库公开/Stable、子库 Stable 与真实效果：`BLOCK`。** 独立 reviewer 先发现 Node.js 20 文档 ID 兼容和母库 artifact 扩展名 allowlist 两个真实 BLOCK；修复后 GitHub Actions Run `30520244121` 在提交 `f0550f28f3cf968554852999d8848ea5509c4c74` 完整通过。已发布 Public Preview 快照的可见性、tag、prerelease、内容、许可、隐私和当时的 131 项测试均通过；当前未发布工作树已扩展为 145/145，尚未 commit、push、tag 或重新发布；仍保留“普通 clone 根目录不是纯 artifact”和“私有 upstream commit 不能由公开用户解析”两个非阻断 WARN。远端验收只证明当前私有同步和公开 Preview，不把任何 scope 升格为 Stable 或 production-ready。

## Agency Operations 当前状态

**本地准备：`complete`（scope=`local-structure-and-synthetic`）；结构与双客户 synthetic 隔离：`structure-pass`；子库发布与生产资格：`BLOCK`。** `agency-operations` 当前版本为 `0.1.0-draft.1`，本轮没有创建真实 `customer-runtime/`，未创建 `SKILL.md`，许可和人工批准均 pending。真实客户、ACL/外部副本、多人权限、备份恢复、远程更新 apply 和生产稳定是 post-preparation scope，不再作为本轮准备完成的 blocker。

## 已验证事实

- 私有母库仓为 `tony-apan/b2b-export-ai-workbench-source`，默认分支 `main`，GitHub 可见性为 `PRIVATE`；[母库 manifest](../../MANIFEST.md) 保持 `repository_sync_status: Synced`、`release_status: BLOCK`、`license_status: restricted`。
- 公开子库仓为 `tony-apan/website-content-ops`，默认分支 `main`，GitHub 可见性为 `PUBLIC`；`v0.3.2-preview.1` 指向发布提交并以非 Draft 的 prerelease 公开。
- 历史 `v0.3.2-preview.1` 的冻结 manifest 曾为 `release_status: Preview`、`preview_publication_status: Published`、`license_status: cleared`；当前工作树 manifest 为 `release_status: BLOCK`、`preview_publication_status: BLOCK`、`license_status: pending`、`approval_status: pending`，不得借用历史 Preview 状态放行当前候选。
- 从远端 clean clone 与 GitHub Node.js 20 CI 复验：母库文档 ID、治理攻击 53/53、母库/子库构建与 artifact、知识链和 Adapter workflow 全部通过；子库独立 archive 校验通过，已发布 Public Preview 的 AllinCMS Adapter 为 131/131，`npm audit --omit=dev` 为 0 vulnerabilities。
- 当前未发布工作树的 AllinCMS Adapter 为 145/145（媒体 45、正文图片 52、文章/正文格式/taxonomy 48）；在冻结计划授权下，同站点严格串行完成 2 分类、2 标签、3 张真实图片和 2 篇全字段文章的接口创建/发布，并逐篇完成单请求幂等 publish 复测。对象数量与 ID 稳定，无删除、清理或跨站。媒体 caption 与分类/标签展示仍为 WARN；正文图片虽在 Slate/CMS payload 中具有非空 alt，但最终 DOM 输出空 alt，属于 renderer SEO/无障碍独立 BLOCK。
- 另一次冻结格式实验严格串行创建 1 篇草稿、测试 13 个格式候选并调用 publish API 1 次；结果为 12 verified、1 unsupported-current-shape、0 not-tested。当前部署原生持久化正文为 Slate JSON `node[]`；Markdown 适合作为创作源并确定性转换为 Slate，HTML 未被证明可作为原生直传格式。`code-block` 测试形状虽通过 API 持久化与精确回读，但编辑器重开失败，已恢复 last-known-good 且未携带该形状发布；桌面、390×844 移动端、fresh navigation、精确 inline DOM 与真实图片匿名访问/解码通过。全程无删除、清理、跨站或修改现有文章。
- 2026-07-31 又在冻结计划下对 1 篇既存英文 B2B 技术文章执行了单次 update 和单次 publish，复用现有 taxonomy 与媒体，无创建、上传、删除、清理、跨站或自动重试。最终 59 个 Slate 顶层节点、7 个 H2、8 个 H3、1 个表格、1 个引用、2 张正文图和 2 个内链通过后台精确回读、编辑器重开及桌面/390×844 前台验收。update 的客户端 CDP 等待超时后未重发，而是只读 reconciliation 证明 draft 已持久化再发布。该单样本证明真实图片与已验证富文本能在一篇文章中共存，但不等于两条 Adapter 路径已形成通用组合入口。
- 同页内容与响应式渲染通过。页面级平台前端边界项（⛔ 禁令范围，不展开）已由 Tony 明确 deferred，不纳入本轮 B2B 内容方法验收；两张正文图在 Slate/CMS payload 中有非空 alt、最终 DOM 却输出空 alt，仍是前端 renderer/template 层的独立 SEO/无障碍 BLOCK。长页 CDP 截图中的 sticky header 重复经普通 viewport 截图和 DOM 几何确认是拼接伪影，不是页面重复内容。
- 当前未发布工作树已建立 [ID-0001 B2B SEO Article Standard](../../sub-libraries/website-content-ops/PLAYBOOKS/id-0001-b2b-seo-article-standard.md)、[ID-0003 Existing-Article Optimization SOP](../../sub-libraries/website-content-ops/PLAYBOOKS/id-0003-b2b-article-optimization-sop.md) 和 brief/draft/review/publish 四件套。新写文章以 ID-0001 为质量真源，优化既有文章按 ID-0003 串行执行并接受 ID-0001 全部质量闸。2026-08-11 的 F23 新不可变候选已补齐 F22 唯一 P1（冻结漏收前端边界 CTA measurement evidence），锁定 151 个文件与 manifest SHA-256 `3ced8c408d85d330d6c102009d12f3143e2d2571564fda3eab78033d615574d4`；冻结副本 full article-package 986/986、review-freeze 61/61、Workspace generated projection 16 项同步和结构/链接检查均通过，4 名全新只读 Reviewer 从 SEO/search intent、B2B buyer/CTA、validator/fixture honesty、docs/templates/SOP/AI reuse 四个角度给出 4/4 PASS、P0=0、P1=0。F20、F21、F22 继续永久保持 BLOCK；F23 只证明本地不可变候选的结构、合同与 synthetic fixture 闭环，canonical package 仍为 `decision=blocked`、`factual_evidence=not_verified`，不证明真实产品事实、query/SERP、排名、询盘或转化提升。 F23 终审后的母库收口又修复了示例 metadata/type/前端边界、测试源码 machine-local literal、related 路径和上层生成索引等机械治理问题；最终 mother-library 与 website-content-ops 静态结构 validator 均 PASS。该 post-freeze delta 未另建 F24，也未再次绑定四方 Reviewer，因此不能把 mutable working tree 冒充新的独立批准候选。
- 2026-08-01 本轮仅做 governance repair：不操作 CMS、不改 `dist/`，不 commit、push、tag 或 release。当前 candidate identity 为 `unassigned / dirty-working-tree`，继续保持 `release_status: BLOCK`、`preview_publication_status: BLOCK`、`license_status: pending`、`approval_status: pending`，不得继承 historical `v0.3.2-preview.1` 的 Published/Public Preview 身份。Tony 已明确 deferred 平台前端边界项（⛔ 禁令范围，不展开），但 deferred 不得写成 PASS；final DOM 正文图片空 alt 与 B2B research publication clearance pending 继续作为独立 BLOCK。
- 直接对普通 Git clone 根目录运行 artifact validator 会因 `.git/` 不是发布 allowlist 内容而失败；正确对象是 builder 产物或 `git archive` 导出的纯发布树。该失败证明 validator 没有静默忽略额外文件，不是公开仓内容泄漏；公开 clone 验收说明仍可在后续 Preview 改善。
- 子库 artifact 的逐文件 SHA-256 和公开 release commit 可验证，但 `source_commit` 指向私有母库，公开用户不能解析该 upstream Git object；当前作为 Preview provenance WARN 记录，不冒充公开可重建的完整来源链。
- 当前 `origin` 指向新的私有 canonical 母库；旧公开仓和旧私有仓分别保留为 `legacy-public`、`legacy-private`，发布后 `main` HEAD 仍为发布前基线。公开子库来自独立 artifact 和独立 Git 历史，不是把母库根目录推到公开仓。
- 母库与子库分别使用独立 manifest、builder、validator、approval/evidence 与 tag namespace；一个 scope 的结论不可替代另一个 scope。
- `raw/`、课程和日志已有独立入口与验证规则；真实客户、凭据和经营数据不得进入公开子库，也不得把 private Git 仓误当客户运行区。
- 子库不自动等于 Skill；当前 `SKILL.md` 是 Preview 条件入口，不是一键安装或跨平台稳定 Skill。

## Current BLOCK

- 母库对外发行许可证仍为 restricted；子库 Preview 已采用 Apache-2.0，但 Stable 所需的候选包外批准、真实批准者身份、可信 signer、远端 Protected Environment/ruleset 和正式服务端 run 尚未形成完整外部证据链。
- `APPROVAL_RECORD_PASS` 只能证明记录结构与候选绑定，不能单靠名称字段证明真人身份。
- 课程仍缺真实学员提交与独立 reviewer 的效果证据，不能宣称稳定课程交付。
- AllinCMS 的限定本地/当前部署证据不得外推到任意站点、任意批次、远程恢复或未来稳定性；媒体 caption 与 taxonomy 主题展示继续作为 WARN。正文图片 alt 已确认是当前 renderer 的正式 SEO / 无障碍 BLOCK：CMS payload 有值而最终 DOM 为空。
- B2B SEO 文章规范与优化 SOP 已通过 F23 本地不可变候选四方独立终审（4/4 PASS，P0=0，P1=0），因此原“尚未通过第二轮冻结复审”结构阻断已关闭；但真实产品/性能事实、真实 query/SERP、排名、询盘、询盘质量和转化仍未证明，当前部署的真实 CMS/前台文章仍只是单样本，Markdown 富文本转换与正文图片绑定仍是两条独立实现，不能外推为通用组合入口或生产稳定。按本轮边界，平台前端边界项（⛔ 禁令范围，不展开）延后处理；正文图片 alt renderer 仍是另一个正式 SEO / 无障碍 BLOCK；source publication/license clearance 与子库正式 release 继续 BLOCK。

## Next Action

1. Public Preview 后续更新只允许从新的 clean 子库候选生成新版本与新 tag；不得移动或覆盖 `v0.3.2-preview.1`。下一 Preview 应补充 clone→archive 验证命令，并区分私有 upstream commit、公开 release commit 与公开可解析性。
2. 母库后续只同步到新的私有 canonical 仓；旧公开/私有仓继续作为只读历史边界，不 force push、不覆盖。
3. 收集真实新手冷启动、跨部署和失败恢复证据；涉及远程 CMS mutation 时继续逐次获得明确授权。
4. 外部固定 workflow SHA、Protected Environment/ruleset、可信签名 annotated tag、包外 approval/evidence、课程真实提交和跨部署证据未齐备前，母库公开/Stable、子库 Stable 和课程 release 继续 `BLOCK`。
- 2026-08-30 晚：allincms-bulk-content-upload skill 独立仓已封存（archived），安装壳与运维参考合并进母库 `sub-libraries/website-content-ops/SKILL-INSTALL/`（唯一真源）；vendor 快照退役待 id-0073 dist 管线。
