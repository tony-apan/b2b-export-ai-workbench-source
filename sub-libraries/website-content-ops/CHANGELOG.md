---
title: "Website Content Operations Changelog"
description: "记录该子库的结构、入口、适配器和发布合同变更。"
type: "changelog"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-30"
sources: ["Repository structure adversarial upgrade 2026-07-28"]
related: ["README.md", "MANIFEST.md", "VERSION.md", "RELEASE.md", "SKILL.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Changelog

## 0.3.2-preview.1 — 2026-07-30

### Public Preview

- 以独立公开仓发布首个 Preview；README 面向新人，`START-HERE.md` 面向 AI agent。
- 许可证确定为 Apache-2.0，并增加 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`。
- 本地结构、链接、拆包、AllinCMS Adapter 131 项测试和依赖审计通过后允许单样本试用。
- Preview 不等于 Stable 或 production-ready；跨部署、真实新手冷启动、正式真人 approval、受保护发布 workflow 和 signed tag 仍未完成。

## Unreleased — 2026-07-30

### Human onboarding and AI execution entry

- 重写子库 README：第一屏改为面向业务人员和新手的通俗说明，明确“人说目标并批准关键动作，AI 按执行手册完成检查、制作和验证”。
- 明确 `START-HERE.md` 主要给可读写文件、使用浏览器或脚本的 AI agent 执行；保留四步执行链，并补充能力声明、无账号分支、本地小样降级路线和 fail-closed 停止条件。
- 增加真实微信支持二维码；没有 AllinCMS 账号、未开通网站或站点不明确时，引导用户联系 Tony，不让 AI 猜测站点、代注册或绕过登录。
- 将 README 中底层授权实现细节下沉到 AllinCMS adapter 文档；人类入口保留可理解的安全边界和发布状态，不再要求新手先理解 digest、Buffer 或 TOCTOU。
- `MANIFEST.md` 已进入 `release_status: Preview`、`license_status: cleared`、`preview_publication_status: Published`；这只表示 Public Preview 已独立公开，不构成 Stable、production-ready 或真人批准。

### Security / governance hardening

- AllinCMS direct、serial、batch、single 四个媒体上传入口现在都要求显式 `authorizationContext`，精确绑定 site、operation、有序文件列表 digest、approval actor/time 与限时 expiry；底层 direct 原语自行 fail closed，`beforeRequest` 仅用于 journaling。
- 在原有授权回归上新增 11 项 TOCTOU / mutation-edge 负向与安全快照测试：覆盖同路径换字节、symlink retarget、批次中途替换、chooser payload 篡改、29:59.999 / 30:00.000 / 30:00.001、future timestamp 和 callback 延迟过期；当前媒体测试 45/45、adapter 全量 131/131。未访问 CMS，远程行为未复验。
- 将正式 `sub-library-release-v1` trusted runtime profile 与机器合同同步为媒体 45、正文图片 50、文章与 taxonomy 36，共 131 项；治理负向测试明确拒绝旧 `120/120`、130/132、少通过、失败、跳过和 test plan 重排。
- 子库 approval/artifact validator 新增 workflow 注入的实际 tag object SHA、signer fingerprint、canonical tag annotation 与 approval-binding digest 精确比对，并明确 PASS 不证明真人身份、远程保护或正式发布。
- `MANIFEST.md` 当前为 `release_status: Preview`、`approval_status: pending`；Preview 与 Stable qualification 分闸。

## 0.3.2-draft — 2026-07-28

### Added / hardened

- 将 release candidate 的 `package_kind` 固定为 `sub-library-release-candidate`，并让 approval sidecar 的 `scope.id`、`scope.package_kind`、tag namespace 和候选包 manifest 使用同一子库身份。
- 增加缺失 sidecar、dirty source、错误 scope/tag/digest、AI reviewer、未知扩展名和缺失 annotated tag 的 fail-closed 对抗测试；当前 release 仍为 `BLOCK`。
- 修复子库 scripts README 的 release builder 示例代码块边界，避免人和 AI 复制命令时产生错误嵌套。

### Verification boundary

- 当前候选包可通过结构、索引/链接和 checksum 校验，但不构成真实人工批准、许可证清除、跨部署 CMS 稳定性或 Skill 可安装承诺。

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
