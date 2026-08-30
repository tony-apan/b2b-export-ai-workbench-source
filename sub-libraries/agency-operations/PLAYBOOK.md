---
title: "Agency Operations Playbook"
description: "多客户运行区初始化、客户与任务创建、日常续接、日志写回、归档和安全升级的执行流程。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["START-HERE.md", "TOOLS.md", "QA-CHECKLIST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 执行手册

## 1. 初始化

运行 `init-customer-runtime.mjs`。脚本先在同级 staging 目录完整生成，强制所有目录为 `0700`、文件为 `0600`，并要求 POSIX owner uid 与当前用户一致，再原子切换为正式运行区；目标已存在时默认拒绝覆盖，不得用模板刷新已有运行区。外部工具若把任何 runtime 路径放宽为 group/other 可读写或改变 owner，写入、搜索和 validator 都会 BLOCK，先恢复私有权限再继续。`0700/0600 + owner` 仍不验证 macOS ACL、云盘/备份副本或真实多用户授权。

## 2. 创建客户

运行 `create-client.mjs --client cli-... --name ...`。脚本在独占写锁内生成 Registry、`CLIENT.json`、任务/来源/渠道/输出/指标/证据/日志/写回目录和 canonical 入口；中途失败必须回滚新目录和 Registry。

## 3. 注册公司、产品、渠道和账号

使用 `register-entity.mjs`。公司、产品、渠道、账号都有稳定 ID；账号只允许保存 `keychain://`、`1password://`、`secret-manager://`、`env-ref://` 或 `manual-login://` 形式的 opaque reference。产品和渠道绑定公司，账号同时绑定公司和渠道；不一致即 BLOCK。

## 4. 创建任务

运行 `create-task.mjs --client ... --task tsk-... --title ...`。可用 `--products prd-a,prd-b`、`--channels chn-a` 和 `--accounts acct-a` 显式绑定实体；产品、渠道和账号必须属于任务公司，账号对应渠道还必须显式列入 `--channels`。任务记录绑定创建时 core commit、runtime schema 和客户 scope；创建时激活使用 `--activate`，切换已有任务使用 `activate-task.mjs`，清空当前 scope 使用 `activate-task.mjs --clear`。

## 5. 日常续接

按 START-HERE 顺序读取。完成一个动作后：

1. 更新 `TASK.json` 当前状态；
2. 重写 `HANDOFF.md` 当前摘要；
3. append-only 记录当日事件；
4. 保存证据 pointer，不复制 secret；
5. 重建索引和 catalog；
6. 运行 boundary validator。

## 6. 搜索

只使用 `runtime-search.mjs --client <id> --query <text>`。搜索在筛选目标客户前先验证**全部** catalog 行、Registry、目录、realpath、文件大小和当前性；无 `--client`、catalog 任一客户越界、catalog stale、symlink、超大文本或结果过宽均失败。单个可索引文本当前上限为 2 MiB，超过时应拆分原始对话或日志，不得静默漏索引。

所有写工具使用 `00_control/.runtime-write.lock` 单写者锁；锁存在时写入、搜索和验证均停止。异常退出遗留锁时先检查运行区是否存在半完成状态，不得直接删除锁后继续。

## 7. 母库更新

第一版 `update-core.mjs` 只支持 `--check`。它检查 tracked core、运行区 Git 边界、当前 commit 和 schema lock；`--apply` 固定 BLOCK。正式自动更新需另有 fetch 来源验证、迁移副本、备份恢复和人工批准证据。

## 8. 归档与写回

归档前关闭活动任务、冻结 handoff、验证 catalog 清理和保留策略。通用经验只进入 `90_writeback/`，去标识化人工批准后才能提交母库。
