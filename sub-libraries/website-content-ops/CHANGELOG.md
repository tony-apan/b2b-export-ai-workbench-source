---
title: "Website Content Operations Changelog"
description: "记录该子库的结构、入口、适配器和发布合同变更。"
type: "changelog"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-01"
sources: ["Repository structure adversarial upgrade 2026-07-28"]
related: ["README.md", "MANIFEST.md", "VERSION.md", "RELEASE.md", "SKILL.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Changelog

## Unreleased — 2026-08-30

### 四项平台层审计禁令全仓清扫 + id-0002 退役 + 工具包治理（每批 flash+TERRA 双审）

改动对比（旧 → 新 → 原因）：

| 旧 | 新 | 原因 |
|---|---|---|
| id-0002 文章页前端合同整页 + WT 镜像 + 20 处引用 | 删除；页面验收并入 ID-0007 B/C 层与 QA-CHECKLIST | 2026-08-30 用户永久禁令：四项平台层审计项不检查、不报告、不讨论 |
| frontend_deferred_blocks 三元组枚举（17 处模板/示例/规格句） | 空集 []，平台边界项不枚举 | 同上；字段与防漂移闸保留（exact-match 等强） |
| RUNTIME-CONTRACT 与 schema const 三元组 | []（schema 形成单向闸：加回即 INVALID） | 同上 |
| validate-article-package deferredExpected 三元组 + 负回归漂移算子 | [] + 漂移算子修复（测试 986/986 全绿） | 同上；防倒退闸保持等强 |
| audit 口径 17/15/14 项（ONEPASS/FORMAT-SPEC/ONBOARDING/id-0007） | 统一 13 项 = site_pipeline.py 代码真源 | 消除断言漂移 |
| issues.tsv ISS-012/043/053/058 平台审计事实行 | ⛔ 横幅式泛化（行结构与证据指针保留） | 禁令；原始文本在 git 历史可考证（禁 squash/改写） |
| KIT 8 文档 + site_pipeline.py 代码内四词残留（含死变量/死过滤/孤儿注释） | 清零（⛔ 横幅豁免除外） | 禁令 |
| 客户标识（品牌名/站点 key/任务路径）30+ 处（含 3 个 page-example JSON 模板与 registry 行） | Example/占位符 | 公开子库去敏 |
| /tmp 明文 token 教习（SETUP/API-DISCOVERY/RUNBOOK/根 README） | WS_TOKEN 环境变量优先；scan-actions.py 已支持 env | 凭据治理（明文 token 文件已删） |
| RUNBOOK/ONEPASS/API-DISCOVERY 未登记 registry | DOC-035/036 + verify 未登记覆盖检查（FAIL 闸）；DOC-037 与既有 DOC-034 去重 | 防 find 失明 |
| skill 独立仓（thin router + vendor 33MB） | 合并进母库 SKILL-INSTALL/（6.6MB，vendor 退役待 dist 管线）；独立仓 GitHub 封存 archived | 2026-08-30 用户决策：母库为唯一真源 |

- validate-sub-library 存量失败为基线既有（394→390，随修复推进下降；剩余 archived_at schema 等存量问题另行立项）。WORKSPACE-TEMPLATE 镜像含源模板 archived_at 追赶 hunk（sync 机制自愈，随本批入库）。
- 待用户定性（OQ-BAN-0001）：三状态字段名（12 文件+验证器+测试）与历史日志 4 处原句的豁免/清除；vendor bundle 需在 Skill 化前重建。

## 0.3.2-preview.1 — 2026-07-30

### Public Preview

- 以独立公开仓发布首个 Preview；README 面向新人，`START-HERE.md` 面向 AI agent。
- 许可证确定为 Apache-2.0，并增加 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`。
- 本地结构、链接、拆包、AllinCMS Adapter 131 项测试和依赖审计通过后允许单样本试用。
- Preview 不等于 Stable 或 production-ready；跨部署、真实新手冷启动、正式真人 approval、受保护发布 workflow 和 signed tag 仍未完成。

## Unreleased — 2026-08-01

### Current dirty candidate governance boundary

- 当前 dirty working-tree candidate 没有分配发布身份：`release_status: BLOCK`、`preview_publication_status: BLOCK`、`license_status: pending`、`approval_status: pending`。历史 `v0.3.2-preview.1` 的 Preview / Published / cleared 状态只属于其 2026-07-30 冻结 artifact，不属于、也不得继承给当前候选。
- 本次 Worker B write set 只修复 B2B 内容规范/操作文档与 runtime unsupported-claims，不操作 CMS、不改 `dist/`，不 commit、push、tag 或 release；不得把该局部范围外推为整个 dirty candidate 已完成。Tony 已明确 deferred `html lang`、canonical 与 Article JSON-LD；deferred 不等于 PASS。final DOM 正文图片空 alt 与 B2B research publication clearance pending 继续作为两个独立 BLOCK。

### B2B article contract adversarial hardening

- 统一 canonical template 枚举：query fact status 只允许 `missing|inferred|confirmed`；Troubleshoot/Compare intake 明确默认 `none`，仅在真实 destination、named owner、accepted receiving task 与阶段证据成立时升级。
- 将买方接收任务的 `cta_receiving_owner` 与外部 CTA route 的 `cta_owner` 分离；Buy commercial handoff 不再复用 engineering-only endpoint，也不能把买方 Procurement owner 与供应商 Commercial Account owner 混为同一责任。
- input-collecting、human-handoff 与 commercial CTA 的 copyable fallback 必须出现在买家可见 CTA 区，并分为 verified route 与 unverified/unconfigured route 两条 fail-closed 分支；只有 `executed + confirmed + pass` 才能宣称备用入口已验证，否则必须要求买家不要发送、保存本地并经既有 approved supplier-contact process 请求 verified route。
- 增加对应 template vocabulary、commercial route、owner separation 与 visible fallback 回归测试；这些结构门禁不证明排名、询盘或转化提升。
- 修复完整回归暴露的两个假阴性边界：所有 collecting CTA 正例必须在实际 CTA 区显示唯一 copyable fallback；buyer-visible capability proof 不再因少量散落通用词误判为已落正文。2026-08-01 本轮 article-package 回归为 406/406，后续计数仍以实际 TAP 输出为准。
- 固化 immutable review 规则：失败候选永久作废，不得复用其 PASS、Reviewer、签字、digest 或局部绿灯；修复后生成下一不可变候选，并由未参与上一候选审查或修复的全新 Reviewer 对同一冻结副本重新审查。候选即时状态只进入 freeze/review evidence。
- 修复目标把 primary SERP 的 sample size、dominant result type/count、预先冻结 threshold 与 supporting-query 边界结构化，并建立 result type → `expected_content_type` → Draft observable shape → Review/Publish fatal verdict 的 exact projection。
- 全部 buyer-visible CTA 均进入 inventory，不依赖 H2；verified route 要求 endpoint-specific structured evidence，unverified route 全文不得链接或指示使用/发送，只允许 do-not-send、save-locally、approved supplier-contact process 恢复路径。四件套还必须 exact projection 主 CTA 三轴、fallback contract、`Hook → Diagnose → Decide → De-risk → Act`、`primary|soft|fallback` 与 deferred exact set。
- 内容层新增 320px 小屏设计边界；没有真实 renderer/readability structured evidence 时只能 `not-run + missing + block`，结构 scope 可单独审查但 production readiness 必须 BLOCK。H1 明确属于 page-shell metadata，publishable body 禁止 H1。source/license、final DOM alt、CMS、release 和真实排名/询盘/转化继续独立 BLOCK/未验证；三个 deferred frontend SEO 项保持 not PASS，但不阻断本轮内容合同 scope。

### AllinCMS media startup and fallback routing

- 把 AllinCMS 图片上传冷启动固化为“宿主内置 Browser → 登录即时前台交接 → `/sites` 的 0 / 1 / 多站点发现 → 精确媒体页 → 接口串行上传”；接口异常时先判断请求是否可能已发出，再只读对账或页面诊断，UI 仅在另行明确批准后用于 1–5 张回退。
- 增加登录、无站点、多站点、无目标站点权限、页面 403/404/500/空白/Loading、浏览器控制面和本机依赖的统一提醒与 BLOCK 规则；修复 AI 唯一入口的媒体示例，显式创建并传入必需的 `authorizationContext`。

### AllinCMS article format profile

- 在冻结计划授权下严格串行创建 1 篇草稿、测试 13 个正文格式候选并只发布 1 次；复用既有 taxonomy 和真实媒体，没有删除、清理、跨站或修改已有文章。
- 形成 12 verified / 1 unsupported-current-shape / 0 not-tested 矩阵；H3、五种 inline mark、链接、两类列表、引用、分隔线和表格通过后台回读、编辑器重开与前台验收。
- `code-block` 在该阶段的测试形状虽可 API 保存并精确回读，但编辑器重开失败；已恢复 last-known-good 后再发布，合同明确禁止发布该形状。
- 新增 `article-content-formats.mjs`，把 Slate canonical 示例和 Markdown → Slate 保守转换固定为代码；直接 HTML/Markdown 不进入文章 `content`，代码围栏、正文 H1、raw HTML、不安全链接和畸形表格请求前 fail closed。
- 当前未发布工作树的 Adapter 回归为 158/158：媒体 45、正文图片 52、正文格式 13、文章生命周期/taxonomy 48；正式 trusted runtime profile 同步为四文件 158 全通过。

### AllinCMS article and taxonomy verification

- 在冻结计划授权下，同站点严格串行完成 2 个分类、2 个标签、3 张真实图片和 2 篇全字段文章的接口创建与发布；未删除、未清理、未跨站，随后逐篇单请求重复 publish，ID、slug、数量和 published 状态保持不变。
- 修复浏览器/CDP 跨 realm prototype 导致的 JSON 假阴性；taxonomy 精确 `/posts` route 回读允许省略 `contentType`，但显式冲突继续 fail closed。
- 封面回读改为比较后端实际持久化的 `name / alt / type / source / path / size / mimeType` canonical 字段；任何非空封面 payload 在请求前必须完整自有这 7 个字段，URL-only 或提交与回读同时缺字段也会 fail closed；扩展字段被省略不再误报，canonical 字段缺失/变化仍失败。
- 历史阶段 Adapter 计数依次为 136/136、加入正文格式 profile 后 145/145、将独立正文格式回归文件纳入 trusted profile 后 156/156；这些均为 historical snapshot，不是当前 trusted profile。当前固定四文件为 158/158（媒体 45、正文图片 52、正文格式 13、文章生命周期/taxonomy 48）。媒体 caption 在该次自然运行中仍为 `null`，主题未稳定透传正文图片 alt、分类与全部标签，因此顶层结论保持 WARN，不能宣称跨部署、Stable 或 production-ready。

### Human onboarding and AI execution entry

- 重写子库 README：第一屏改为面向业务人员和新手的通俗说明，明确“人说目标并批准关键动作，AI 按执行手册完成检查、制作和验证”。
- 明确 `START-HERE.md` 主要给可读写文件、使用浏览器或脚本的 AI agent 执行；保留四步执行链，并补充能力声明、无账号分支、本地小样降级路线和 fail-closed 停止条件。
- 增加真实微信支持二维码；没有 AllinCMS 账号、未开通网站或站点不明确时，引导用户联系 Tony，不让 AI 猜测站点、代注册或绕过登录。
- 将 README 中底层授权实现细节下沉到 AllinCMS adapter 文档；人类入口保留可理解的安全边界和发布状态，不再要求新手先理解 digest、Buffer 或 TOCTOU。
- 历史 `v0.3.2-preview.1` 冻结 artifact 的 `MANIFEST.md` 曾为 `release_status: Preview`、`license_status: cleared`、`preview_publication_status: Published`；这些字段只描述 2026-07-30 的 historical Public Preview，不属于当前 dirty candidate，也不构成 Stable、production-ready 或真人批准。

### Security / governance hardening

- AllinCMS direct、serial、batch、single 四个媒体上传入口现在都要求显式 `authorizationContext`，精确绑定 site、operation、有序文件列表 digest、approval actor/time 与限时 expiry；底层 direct 原语自行 fail closed，`beforeRequest` 仅用于 journaling。
- 历史安全快照阶段在原有授权回归上新增 11 项 TOCTOU / mutation-edge 负向测试：覆盖同路径换字节、symlink retarget、批次中途替换、chooser payload 篡改、29:59.999 / 30:00.000 / 30:00.001、future timestamp 和 callback 延迟过期；该 historical snapshot 的媒体测试为 45/45、adapter 全量为 131/131，后续文章与封面回读补测又将当时工作树提升到 136/136。这些不是当前 trusted profile，且该阶段未访问 CMS。
- 历史 `sub-library-release-v1` trusted runtime profile 曾与当时机器合同同步为媒体 45、正文图片 52、文章与 taxonomy 39，共 136 项；该 historical profile 的治理负向测试明确拒绝更旧的 `120/120`、`131/131`、135/137、少通过、失败、跳过和 test plan 重排。此记录不代表当前 158/158 profile。
- 子库 approval/artifact validator 新增 workflow 注入的实际 tag object SHA、signer fingerprint、canonical tag annotation 与 approval-binding digest 精确比对，并明确 PASS 不证明真人身份、远程保护或正式发布。
- 该历史 `v0.3.2-preview.1` 安全加固阶段的冻结 `MANIFEST.md` 曾为 `release_status: Preview`、`approval_status: pending`；这是 historical snapshot，不能覆盖当前 candidate 的 `BLOCK / pending`，Preview 与 Stable qualification 继续分闸。

## 0.3.2-draft — 2026-07-28

### Added / hardened

- 将 release candidate 的 `package_kind` 固定为 `sub-library-release-candidate`，并让 approval sidecar 的 `scope.id`、`scope.package_kind`、tag namespace 和候选包 manifest 使用同一子库身份。
- 增加缺失 sidecar、dirty source、错误 scope/tag/digest、AI reviewer、未知扩展名和缺失 annotated tag 的 fail-closed 对抗测试；该阶段 release 仍为 `BLOCK`。
- 修复子库 scripts README 的 release builder 示例代码块边界，避免人和 AI 复制命令时产生错误嵌套。

### Verification boundary

- 该冻结版本候选包可通过结构、索引/链接和 checksum 校验，但不构成真实人工批准、许可证清除、跨部署 CMS 稳定性或 Skill 可安装承诺。

## 0.3.1-draft — 2026-07-28

### Added

- 增加 `SKILL.md` 草案，明确渐进读取、审批闸、AllinCMS 路由和 BLOCK 边界。
- 增加 `TEMPLATES/README.md`、`ADAPTERS/cms/allincms/fixtures/README.md` 和 `scripts/README.md`，补齐有独立语义目录的索引。
- 增加 `RELEASE.md` 与无依赖静态检查脚本，形成源码包到 release candidate 的可复核入口。
- 增加独立 artifact validator，构建器改为 manifest 驱动 allowlist / denylist、可恢复的 latest 切换，并记录文件清单与 checksum。
- 增加机器注册表一致性校验、扩展敏感文件保护和嵌套目录碰撞检查；生成的 `MANIFEST.json` 现在包含依赖、许可证、Skill 入口和交付模式。
- 补齐 AllinCMS adapter 的 Node.js / npm / sharp 依赖声明；按 `sharp@0.35.3` 实际要求将 Node.js 下限统一为 `>=20.9.0`，115 项测试通过，`npm audit --omit=dev` 为 0 个漏洞。

### Changed

- 将 AllinCMS 总览文件重命名为 `ADAPTERS/cms/allincms-overview.md`，消除文件与目录同名歧义，并同步活动文档引用。
- 将子库、MANIFEST、VERSION 和注册表版本同步为 `0.3.1-draft`。

### Verification boundary

- 本版本仍是源码包，`release_status` 继续为 `BLOCK`。
- 检查脚本验证结构、链接、路径和敏感模式；不替代真实 CMS、跨部署、安装或外部发布验收。
