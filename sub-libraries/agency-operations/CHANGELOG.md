---
title: "Agency Operations Changelog"
description: "记录 agency-operations 源码合同、工具和验证范围变更。"
type: "changelog"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["VERSION.md", "MANIFEST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Changelog

## 0.1.0-draft.1 — 2026-08-01

- 建立 Core / Template / Runtime 三层模型；
- 建立多客户 Registry、任务、handoff、日志和索引合同；
- 增加初始化、客户/任务创建、scope search、边界校验和 update check 工具；
- 增加原子 staging/回滚、单写者锁、已有任务安全激活、任务实体关系验证和每客户任务索引；
- 搜索改为筛选前校验全部 catalog，并限制单文件 2 MiB、查询长度和结果数量；
- runtime 初始化强制目录 `0700`、文件 `0600`、POSIX owner uid 匹配当前用户，mode/owner 漂移时写入、搜索和 validator fail closed；macOS ACL 与外部副本安全仍未验证；
- 增加独立 `preparation_status: complete` / `preparation_scope: local-structure-and-synthetic`，明确本地准备完成；
- 真实客户、ACL/外部副本、多人授权、备份恢复、远程 apply、许可和发布改列 post-preparation gate，不阻断准备完成但继续阻断 release/production；
- 本轮未创建根目录真实 `customer-runtime/`，状态保持 Draft/BLOCK，未创建 Skill。
