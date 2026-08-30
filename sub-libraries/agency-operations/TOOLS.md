---
title: "Agency Operations Tools"
description: "运行区初始化、客户和任务创建、索引、搜索、边界验证和母库更新检查命令参考。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["PLAYBOOK.md", "scripts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 工具

| 命令 | 用途 | 默认安全行为 |
|---|---|---|
| `init-customer-runtime.mjs` | 初始化私有运行区 | 已存在即拒绝 |
| `create-client.mjs` | 创建客户 scope 和默认公司 | 重复 ID、非法 ID、symlink 即拒绝 |
| `register-entity.mjs` | 注册公司、产品、渠道和账号 | 关系错配或 raw secret value 即拒绝 |
| `create-task.mjs` | 创建任务和 handoff | 产品/渠道/账号必须显式且属于任务公司 |
| `activate-task.mjs` | 安全切换或清空 ACTIVE-CONTEXT | 校验客户、公司、任务和实体绑定，不授权外部动作 |
| `sync-runtime-indexes.mjs` | 重建 README/index 与 catalog | 只从 Registry 和目标目录生成 |
| `validate-runtime-indexes.mjs` | 校验 Registry、目录、索引与 catalog | 任何跨客户路径失败 |
| `runtime-search.mjs` | 客户内搜索 | `--client` 必填，筛选前全 catalog 校验 |
| `validate-runtime-boundary.mjs` | Git、symlink、secret shape 和 scope 审计 | 不自动修复 |
| `update-core.mjs --check` | 安全更新前检查 | 不 fetch、不 pull、不 apply |

所有工具支持 `--runtime <absolute-or-relative-path>` 以便 synthetic 测试；默认目标为仓库根 `customer-runtime/`。

写工具使用独占 lock；单个索引文本上限 2 MiB，搜索结果超过 500 条会要求缩小查询。index 与 catalog 是派生视图，创建客户、实体、任务或切换 active context 后必须运行 `sync-runtime-indexes.mjs`。
