---
title: "In-Repository Agency Runtime Model"
description: "规定用户下载母库后，如何在同一物理根目录内安全维护多客户、多公司、多产品、多网站、社媒、来发信与邮件运行数据，并让上游母库持续更新而不覆盖本地日志、任务和证据。"
type: "governance"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01", "private-master-and-sub-library-model.md", "index-and-discovery-standard.md", "logging-standard.md"]
related: ["../../AGENTS.md", "task-router.md", "private-master-and-sub-library-model.md", "index-and-discovery-standard.md", "logging-standard.md", "../../sub-libraries/agency-operations/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "初始化、升级、搜索或审计同一母库根目录内的多客户私有运行区，或需要判断母库更新能否安全应用时。"
keywords: ["agency runtime", "customer-runtime", "multi-client", "scoped search", "core update", "handoff", "private logs"]
---
# 仓库内多客户代运营运行模型

## 决策

`/customer-runtime/` 可以物理位于母库根目录内，方便用户下载整个仓库后让 AI 从根目录启动；但它必须是根 Git 的保留私有命名空间，不能继承母库、子库或发布制品的可见性和 PASS。

```text
同一物理根目录
├── tracked upstream core       # 母库 wiki、规则、脚本、子库源码；普通用户只读
├── tracked empty templates     # 只包含 synthetic 空模板
└── ignored private runtime     # 真实客户数据、日志、证据和本地状态；持续可写
```

母库不是客户工作模板。母库是可版本化更新的上游核心；模板只是用于初始化运行区的冻结资产；复制后的运行区拥有独立生命周期，升级不得重新复制模板覆盖它。

## 不可突破的边界

1. 进入客户数据前必须先锁定 `client_id`；没有明确客户 scope 时，搜索和执行 fail-closed。
2. 同一任务必须绑定 `client_id`、`company_id`、`task_id`；涉及产品或渠道时继续绑定 `product_id`、`channel_id`、`account_id`。
3. 不得用无 scope 的递归搜索扫描整个 `customer-runtime/`，不得跨客户复用原始对话、名单、价格、账号或运行证据。
4. 密码、token、cookie、私钥和 session 不进入 Markdown、JSON、日志或根 Git；运行区只保存 Secret Manager 或本机凭据项的 opaque reference。
5. 外部发送、发布、互动、删除、批量覆盖、账号切换和权限改变必须按运行合同获得明确人工批准，并在动作后独立回读验证。
6. 客户事实与运行证据只留在客户 scope；通用改进只能先进入 `90_writeback/`，经去标识化和人工审核后再写回母库。
7. 根 Git、母库 artifact、子库 artifact 与客户运行区分别验收，一个 scope 的 PASS 不能替代另一个。

## Canonical 发现模型

### 人类导航

人或 AI 需要进入并判断下一步的语义目录，必须恰有一个 `README.md` 或 `index.md` canonical 入口。纯附件、截图、导出、缓存和证据 bundle 不为形式完整创建空索引，由上级入口或机器清单声明用途。

### 机器真源

- `RUNTIME.json`：运行区 schema、更新通道和安全策略；
- `00_control/ACTIVE-CONTEXT.json`：当前获授权客户和任务；
- `00_control/CORE-LOCK.json`：母库 commit、知识 revision、runtime schema 与模块版本；
- `00_control/clients-registry.json`：客户唯一注册表；
- `00_control/task-registry.jsonl`：任务状态事件或任务投影的机器入口；
- 每个客户的 `CLIENT.json`：客户边界和默认公司；
- 每个任务的 `TASK.json`：当前任务状态；
- `HANDOFF.md`：下一个人或 AI 的人类可读续接页。

Registry、JSON 合同和任务状态是机器真源；README/index 是生成或同步的展示视图，不能分别手工维护相互竞争的状态。

### 作用域搜索

搜索工具必须要求 `--client <client_id>`。目录、Registry、catalog 和最终结果路径都必须再次校验属于 `10_clients/<client_id>/`；仅在存在单独的跨客户分析授权时，才允许使用不同的显式命令。

全文或向量索引只是可重建缓存，不是权限边界或事实真源。每条索引记录必须携带 `client_id`，搜索必须在筛选目标客户前校验全部 catalog 行；删除或归档客户后必须可验证清理。为避免内存和输出失控，索引器必须对单文件大小、查询长度和结果数量设置显式上限，超过时 BLOCK 并要求拆分或收窄，不得静默漏索引。

运行区写入采用单写者 lock。lock 存在时其他写入、搜索和验证均停止；异常退出后的 stale lock 不能直接删除，必须先核对 Registry、目录、active context 和派生视图是否一致。

## 对话、日志、状态和证据分层

| 对象 | 作用 | 推荐位置 |
|---|---|---|
| 原始 AI/客户对话 | 保留当时说了什么和来源边界 | `10_sources/conversations/` |
| 当前任务状态 | 告诉 AI 现在做到哪里 | `30_tasks/<task_id>/TASK.json` |
| 续接摘要 | 告诉下一个 AI 下一步、阻断和禁止动作 | `30_tasks/<task_id>/HANDOFF.md` |
| 每日事件 | append-only 记录发生了什么 | `80_activity/YYYY/MM/YYYY-MM-DD.md` |
| 输出 | 草稿、页面、序列和报告 | `50_outputs/` |
| 指标 | 已定义口径的观察结果 | `60_metrics/` |
| 证据 | 截图、导出、响应和验收记录 | `70_evidence/` |
| 写回候选 | 去客户化后的通用改进 | `90_writeback/` |

日志不是当前状态，聊天也不是当前状态。新会话默认读取顺序是：根规则 → 运行区规则 → ACTIVE-CONTEXT → 客户合同 → TASK → HANDOFF → 最近事件 → 精确引用的来源和证据；不得为了续接先扫描所有历史聊天。

## 上游母库更新

普通用户不直接修改 tracked core。个性化规则进入运行区本地 policy，客户经验进入客户 scope，可贡献改进进入 writeback candidate。

更新必须分开记录：

- `core_release`：规则、脚本和执行合同；
- `knowledge_revision`：向后兼容的知识内容更新；
- `runtime_schema_version`：Registry、任务和目录合同变化。

受控更新顺序：

1. 检查 tracked core 是否 clean；存在本地修改时 BLOCK，不自动 stash；
2. 记录当前 commit 和 runtime schema，校验备份可用；
3. 只 fetch 候选，不立即覆盖；
4. 核对来源、版本、manifest、checksum、兼容性和迁移要求；
5. 在副本上 dry-run 迁移；破坏性迁移必须再次人工批准；
6. 仅允许 fast-forward 或可回滚的原子切换；
7. 不重新复制模板覆盖现有运行区；
8. 更新后重建派生索引，验证客户 scope、任务、链接和 Git 边界；
9. 更新 `CORE-LOCK.json` 和 append-only update history；
10. 任一关键检查失败时恢复旧 core 与迁移前快照。

安全收紧立即生效；业务字段或流程语义变化必须通过版本化迁移。进行中的任务保留创建时的 `core_commit`、`runtime_schema_version` 和模块版本，但不能借旧版本绕过新的安全限制。

## 保留路径与 Git 闸门

`.gitignore` 只是第一道防线。上游 CI 和本地 validator 还必须保证根 Git 从未追踪：

```text
customer-runtime/**
credentials/**
secrets/**
browser-profiles/**
```

即使母库为 Private，也不允许把真实客户运行数据和凭据提交。模板目录只能包含 synthetic fixture 和公开安全元数据。

## 最小验收

在宣称多客户运行可用前，至少完成：

1. clean clone 初始化运行区；
2. 创建两个拥有同名产品和相同渠道类型的 synthetic 客户；
3. 有 `client_id` 的搜索只返回目标客户；无 scope 搜索失败；
4. 错客户、错账号、路径穿越和 symlink 逃逸被阻断；
5. 根 Git 不追踪运行区，母库/子库 artifact 不包含运行区；runtime 目录权限固定为 `0700`、文件为 `0600`，POSIX owner uid 必须与当前用户一致，mode/owner 漂移即 BLOCK；macOS ACL、同步盘/备份副本和真实多用户边界需另行验证；
6. 母库更新不覆盖客户文件，模板变化只影响新初始化；
7. schema 不兼容时无迁移器则 BLOCK；
8. 人可在 2–4 层入口内找到客户、活动任务和最近日志；
9. AI 可从 TASK/HANDOFF 续接而不通读全部历史；
10. Registry 与 README/index 不形成两个可编辑真源；
11. 备份、恢复、客户归档和索引重建可验证；
12. 外部动作的批准、执行对象和回读证据精确绑定。
13. 创建客户或任务中途失败不会留下未注册目录、Registry 事件或错误 active context；并发写锁会阻断其他读写。
14. ACTIVE-CONTEXT 与 TASK 的客户、公司和实体关系可机器验证；账号 scope 不能隐式扩大到未声明渠道。

结构或 synthetic 测试通过只能证明对应局部 scope；真实客户隔离、多运营人员权限、远程更新可信度和生产稳定性在取得相应证据前继续 `BLOCK`。
