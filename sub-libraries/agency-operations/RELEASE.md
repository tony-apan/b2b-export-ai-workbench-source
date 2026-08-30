---
title: "Agency Operations Release"
description: "定义 Draft 源码、结构验证、真实运行证据和正式发布资格之间不可混用的状态边界。"
type: "release-guide"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["MANIFEST.md", "QA-CHECKLIST.md", "LICENSE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
state_source: "MANIFEST.md"
state_projection: ["preparation_status", "release_status"]
preparation_status: "complete"
release_status: "BLOCK"
---
# Release

- preparation_status：`complete`（仅 `local-structure-and-synthetic`）
- repository_sync_status：`Working`
- release_status：`BLOCK`
- license_status：`pending`
- approval_status：`pending`

当前本地准备已经完成：可作为母库中的 source-only Draft，在未来明确客户 scope 后初始化本地运行区。Preparation PASS 或双客户 synthetic 测试通过不等于真实客户隔离、生产稳定、远程更新可信或 Published；release validator 继续按设计返回 BLOCK。

正式候选至少需要：许可明确、品牌与支持明确、3–5 次真实运行、多人权限验证、备份恢复、迁移回滚、外部动作批准证据、独立 reviewer 和人工发布批准。
