---
title: "Agency Operations QA Checklist"
description: "明确本地 Preparation Complete 的已通过项目，以及不属于本轮验收的真实客户、发布与生产后续闸门。"
type: "checklist"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "Tony preparation-only acceptance 2026-08-01"]
related: ["PLAYBOOK.md", "MANIFEST.md", "RELEASE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# QA Checklist

## Preparation acceptance — complete

- [x] 根 `.gitignore` 排除 `customer-runtime/**`、`credentials/**`、`secrets/**` 和 `browser-profiles/**`，当前 Git 索引未追踪这些路径；
- [x] 本轮没有在仓库根创建真实 `customer-runtime/`；synthetic 运行区只在系统临时目录生成；
- [x] runtime 目录为 `0700`、文件为 `0600`、POSIX owner uid 为当前用户，mode/owner 漂移时写入、搜索和 validator 均 BLOCK；
- [x] 初始化拒绝覆盖现有目录；
- [x] client/task ID 格式、Registry 和目录一致；
- [x] 客户和任务创建中途失败后目录、Registry 与 active context 回滚；
- [x] 并发写锁存在时，写入、搜索和 validator fail-closed；
- [x] ACTIVE-CONTEXT 的 client/company/task 与真实 TASK.json 精确绑定；
- [x] task 的 product/channel/account 均存在且不跨 company；
- [x] 无 scope 搜索失败；
- [x] path traversal、绝对路径和 symlink 逃逸失败；
- [x] catalog 每项位于声明客户目录；
- [x] 搜索前验证全部客户 catalog 行，而不是先筛选目标客户；
- [x] stale catalog、重复路径、超大文本和过宽查询被拒绝；
- [x] secret shape 不进入 tracked source 或 runtime 可索引文本；
- [x] index 可从 Registry、TASK.json 等机器真源重建。

## 双客户 synthetic — complete

- [x] 两客户有同名产品与同渠道；
- [x] Acme 搜索不返回 Beta marker；
- [x] Beta 搜索不返回 Acme marker；
- [x] 错客户 catalog 被 validator 拒绝；
- [x] 重复客户、重复任务和已有运行区被拒绝；
- [x] 每客户 `30_tasks/index.md` 可从任务真源重建；
- [x] 权限改为 `0644` 后 writer、search、boundary/index validator 与 sync check 均 BLOCK，恢复 `0600` 后重新 PASS。

## Post-preparation gates — deferred, not part of this acceptance

- [ ] 3–5 次真实客户运行；
- [ ] macOS ACL、同步盘/备份副本和真实多用户读取边界；
- [ ] 多运营人员授权隔离；
- [ ] 真实备份、破坏、恢复、归档与保留演练；
- [ ] 可信远程更新、schema migration、rollback 和 apply；
- [ ] 外部渠道对象级批准、执行与回读；
- [ ] 人工许可、品牌、支持与发布批准。

前两组通过即允许 `preparation_status: complete`。最后一组不阻断本地准备完成，但任何一项未完成时，真实客户 readiness、Published、Stable、release 和 production-ready 声明继续 BLOCK。
