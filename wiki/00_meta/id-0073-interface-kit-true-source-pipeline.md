---
title: "任务卡：interface-kit 真源管线（迁移绑定条款）"
description: "把 runtime 权威的 interface-kit 纳入母库 tracked + dist 同步管线，消除长期悬空。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-31"
doc_id: "ID-0073"
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["id-0072 迁移绑定条款（TERRA X3）", "迁移执行授权 2026-08-30"]
keywords: ["interface-kit", "pipeline", "dist", "digest", "sync", "stale-guard"]
when_to_read: "需要了解 runtime 迁移或 interface-kit 真源管线时"
related: ["id-0072-runtime-folder-structure-v2.md"]
---

# 任务卡：interface-kit 真源管线

## 背景（为什么立项）
- 迁移已执行（2026-08-30）：customer-runtime → 701_runtime（整目录 + 相对软链 shim）。
- 现状：interface-kit 权威副本在 `701_runtime/00_shared/interface-kit/`（母库 tracked 0 命中、dist 无同步源）——"母库 dist 同步"是虚构待建（flash-1 实锤）。
- 风险：不立项则真源悬空——runtime 侧持续演化（ISS-063..082 全在 runtime 改），母库永远落后；换机器/清 runtime 即丢工具链。

## 验收定义（DoD）
1. interface-kit 纳入母库 tracked（位置：`sub-libraries/website-content-ops/TOOLS/interface-kit/` 或独立子库，去敏后无客户数据/凭据）。
2. dist 同步管线：母库真源 → 构建 dist 分发副本（沿用 sub-library 合同：manifest/builder/digest）。
3. runtime 侧改为消费方：从 dist 同步，本机改动回流母库走 PR/复制流程。
4. 两轮对抗审查（SOL+TERRA）通过。

## 步骤
- [x] 去敏审计：四批治理完成（客户名/站点 key/业务指纹/路径全量 Example 化；双机器闸拦截复发）——2026-08-30/31
- [x] 选型：并入 website-content-ops 子库（TOOLS/interface-kit，C2 commit 73e3488 已推送）
- [x] 建管线：`scripts/interface-kit-pipeline.py`（四子命令+selftest；build-dist 只读 git committed 字节；dist 本地产物按仓设计不入库）——2026-08-31
- [x] runtime 切换为 dist 消费 + 回流约定：sync-runtime 前置守卫（未回流改动即中止，探针负测试实证）；anchor 记录 SHA 锚
- [x] 双审 + release：双审完成 2026-08-31（flash 前台终审条件GO 三防御洞修复复现 + TERRA 前台终审条件GO 三条件落地），C6=2617b3d 已推送；release 随子库既有 release 流程（3 卡 BLOCK 未变）

## 期限建议
2026-09-06 前完成验收（一周内；拖延即回流 id-0072 待办①警告的"无限期漂流"场景）。
