---
title: "Agency Operations Scripts"
description: "本子库初始化、客户和任务创建、索引、搜索、边界校验、更新检查及测试命令入口。"
type: "tooling-index"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["../README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Scripts

```bash
node scripts/validate-sub-library.mjs
node --test scripts/runtime-boundary.test.mjs
node scripts/init-customer-runtime.mjs
node scripts/create-client.mjs --client cli-acme --name "Acme"
node scripts/register-entity.mjs --client cli-acme --type channel --id chn-laifaxin --name "Laifaxin" --company co-acme --channel-type laifaxin
node scripts/create-task.mjs --client cli-acme --task tsk-first-outreach --title "First outreach" --channels chn-laifaxin --activate
node scripts/activate-task.mjs --client cli-acme --task tsk-first-outreach
node scripts/sync-runtime-indexes.mjs
node scripts/validate-runtime-indexes.mjs
node scripts/runtime-search.mjs --client cli-acme --query motor
node scripts/validate-runtime-boundary.mjs
node scripts/update-core.mjs --check
```

写命令通过 `00_control/.runtime-write.lock` 串行化。初始化把目录固定为 `0700`、文件固定为 `0600`，并要求 POSIX owner uid 与当前用户一致；任何 mode 或 owner 漂移都会阻断写入、搜索和 validator。该检查不证明 macOS ACL 或外部副本安全。创建或切换状态后先同步索引；catalog stale、任一客户路径错配或单个文本超过 2 MiB 时，搜索固定 BLOCK。
