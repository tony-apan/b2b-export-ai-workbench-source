---
title: "Website Content Operations Agent Protocol"
description: "AI 在建站内容运营子库中的渐进读取、来源、权限、执行、验证和写回规则。"
type: "agent-protocol"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-30"
sources: ["README.md", "COURSE-MAP.md", "MENTAL-MODEL.md", "PLAYBOOK.md", "Tony decisions 2026-07-27 and 2026-07-30"]
related: ["START-HERE.md", "COURSE-MAP.md", "INTAKE.md", "QA-CHECKLIST.md", "WRITEBACK.md", "MANIFEST.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# AI 工作协议

## 宿主规则优先

本协议只在宿主系统规则、用户明确要求、宿主项目 `AGENTS.md` / `CLAUDE.md` 和平台安全规则允许的范围内生效。不得覆盖宿主规则、用户项目规则、系统权限或平台安全限制。优先级为：宿主系统与平台安全规则 > 用户当前要求 > 宿主项目规则 > 本子库 `AGENTS.md` > 本子库 `SKILL.md` > 普通说明文档。

## 机器可读运行合同

先读 [RUNTIME-CONTRACT.json](RUNTIME-CONTRACT.json)。它定义输入、输出、权限、外部副作用、人工审批点、回滚和写回边界；本文件和母库规则优先级更高。

## 第一目标

把使用者现有网站和资料转成可追溯、可执行、可持续更新的公司、产品与客户知识，再用它完成一个真实可验证的内容任务。不要一上来读全库、批量生成或上传。

## 渐进读取，禁止一次读完

第一次只读：

1. [START-HERE.md](START-HERE.md)
2. 当前演示或客户运行区入口
3. 当前步骤明确指定的一个模板或 adapter

只有遇到对应问题时再读：

- 不理解对象关系：读 [MENTAL-MODEL.md](MENTAL-MODEL.md)；
- 需要完整执行：读 [PLAYBOOK.md](PLAYBOOK.md) 当前阶段；
- 需要收集资料：读 [INTAKE.md](INTAKE.md)；
- 需要图床或 CMS：读 [ADAPTERS/](ADAPTERS/README.md) 对应文件；
- 需要验收或写回：读 [QA-CHECKLIST.md](QA-CHECKLIST.md) 或 [WRITEBACK.md](WRITEBACK.md)。

不得要求初学者先理解全部目录，也不得为了“保险”每次读取所有模板。

## 四步运行

1. **工具**：检查本地文件读写、浏览器、Node.js 和目标 CMS；Obsidian 只在用户使用时检查，PicGo 只在用户明确需要外部图床时检查；不擅自安装或改配置；
2. **知识**：建立公司、产品、ICP、客户语言四张最小卡；
3. **小样**：只做一篇内容、一张图片和一条 CMS 草稿；
4. **验证写回**：检查真实 URL / 状态、记录失败和指标，再迁移到第二工具。

## 事实规则

- 状态只允许：`confirmed`、`inferred`、`missing`、`conflicting`、`expired`；
- 公司、产品、认证、交期、MOQ、能力和结果必须有来源或状态；
- 网站说法不是自动真理；冲突必须列出；
- 不得把虚拟示例当成真实公司或案例；
- 不得编造联系方式、认证、客户、销量、排名和效果数据。

## 执行与权限

- 先建库，再生产；先一条小样，再批量；
- 图片先做来源、用途、版权、命名和 alt 清单；
- PicGo 必须先单图验证，GUI 与 CLI 配置不一致时停止；
- CMS 默认草稿；安装、发布、覆盖、删除、批量和全局设置必须由人确认；
- 不索取或记录明文凭据、完整配置、cookie 或 session；
- 发布后检查真实页面，不把命令成功或后台成功当成唯一证据。

## README-only 与 durable page 规则

本子库根入口和实现目录使用 `README.md`，元数据必须声明 `canonical_entry: "README.md"`；不要为了形式统一额外创建 `index.md`。长期可复用知识页只允许放在 `MANIFEST.md` 的 `durable_roots`（`KNOWLEDGE/`、`PLAYBOOKS/`、`COURSES/`、`OUTPUTS/`）内，并使用 `id-####-slug.md`、匹配的 `doc_id`、人话 description、when_to_read 和 3-8 个 keywords。创建前优先使用本子库 `TEMPLATES/durable-page.md`，完成后运行母库 scope ID 校验和本子库校验。

## 每一步返回

- 这一步用了哪些来源；
- 生成或修改了哪个文件；
- 哪些是事实、推断和缺口；
- 是否需要人工批准；
- 如何验证；
- 结果写回哪里。

单次任务只有在外部动作获批、真实结果验证、错误可追溯并完成写回时才算完成。课程只有在第二图床或 CMS 迁移也通过时才算学会。

## AllinCMS 内容 mutation 授权

文章、分类、标签和正文图片草稿写入不得接受裸布尔授权。调用子库 adapter 时必须提供与准确站点、操作、目标摘要、具名 `human-asserted` actor、批准时间和最长 30 分钟有效期绑定的 `authorizationContext`；每次请求前必须重新校验。`approval_identity_status` 保持 `not_verified`，该上下文不是正式批准或身份凭证。发布、删除、批量或全局修改继续要求独立明确人工批准和可验证回读。

## AllinCMS canonical run discipline (2026-08-27 lessons; hard rules)

- Freeze-and-archive: 任何远程 mutation 前，计划的 `authorization_scope.approved_at/expires_at/plan_sha256` 与 `capability_snapshot` 时间必须与 file write 同一步骤落盘（`content-operation-plan.json` 保存即证据）。请求时的手工/运行期校验不替代归档窗口。
- Transport: 页内桥一律 `new TextDecoder().decode(Uint8Array.from(atob(...)))`；`eval(atob(...))` 为 Latin-1，禁止用于含 UTF-8/CJK 载荷。
- Success pattern: 本部署 update/publish/metadata 返回整页 flight 属成功重渲染；任何 PASS 必须来自权威回读原文 +（公开变更）匿名公网验证。HTTP 200 / flight / 本地测试 ≠ PASS。
- Authorization stratification: product/taxonomy/article/site 走 `deriveAllinCmsMutationBinding` 结构化上下文；media 写入无 binding 分支 → 一律标注「request-scoped/empirical」，不得宣称结构化授权覆盖；删除/清理/发布需单条显式批准。
- Contexts: 动作 ID 用 5th-arg 字面捕获（`ADAPTERS/cms/allincms/scripts/scan-server-action-ids.mjs`）；旧 name-adjacent 正则作废。
