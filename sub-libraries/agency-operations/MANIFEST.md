---
title: "Agency Operations Manifest"
description: "agency-operations 子库的机器可投影发布边界、交付形态、依赖、版本、许可和未验证声明唯一合同。"
type: "manifest"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["README.md", "VERSION.md", "RELEASE.md", "RUNTIME-CONTRACT.json"]
visibility: "public"
redaction_status: "safe-to-publish"
keywords: ["manifest", "Draft", "BLOCK", "runtime contract"]
package_id: "agency-operations"
version: "0.1.0-draft.1"
maturity_status: "draft"
verification_status: "structure-pass"
preparation_status: "complete"
preparation_scope: "local-structure-and-synthetic"
release_status: "BLOCK"
license_status: "pending"
approval_required: "true"
approval_status: "pending"
tag_namespace: "sub-library/agency-operations"
tag_prefix: "sub-library/agency-operations/v"
release_scope: "standalone-sub-library"
runtime_contract: "RUNTIME-CONTRACT.json"
dependency_mode: "self-contained"
source_package_only: "true"
package_kind: "standalone-sub-library"
delivery_modes: ["human-playbook", "toolkit", "template-pack"]
skill_entrypoint: null
canonical_entry: "README.md"
included_in_mother: "source-only"
durable_roots: ["KNOWLEDGE", "PLAYBOOKS", "COURSES", "OUTPUTS"]
---
# Manifest

## Included source

- 人类 playbook、模板、工具源码和 synthetic tests；
- 空的 `WORKSPACE-TEMPLATE/`；
- 无真实客户、账号、凭据、聊天、日志或证据。

## Excluded

- `customer-runtime/**`、`credentials/**`、`secrets/**`、`browser-profiles/**`；
- 真实客户材料和任何 secret value；
- 自动应用远程母库更新的能力；
- `SKILL.md` 和任何 installable Skill 声明。

## Preparation verdict

`preparation_status: complete` 只表示本地源码、模板、工具、Git 边界、权限 fail-closed、索引合同和双客户 synthetic 对抗已准备完毕。本轮没有创建根目录真实 `customer-runtime/`，可以在未来收到明确客户 scope 后再初始化。

## Post-preparation blocking facts

许可、品牌、支持、真实运行、多人权限、ACL/外部副本、备份恢复、远程升级 apply 和外部动作闭环均未完成。这些不阻断本地准备完成，但继续阻断 release、Published、Stable、生产可用和真实客户隔离声明。
