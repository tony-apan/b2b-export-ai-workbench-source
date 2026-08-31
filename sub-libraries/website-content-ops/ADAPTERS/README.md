---
title: "Adapters"
description: "把稳定业务对象映射到具体图床、CMS 或平台的统一 adapter 合同、模板和发布闸。"
type: "adapter-index"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-12"
sources: ["../MENTAL-MODEL.md", "../PLAYBOOK.md"]
related: ["_template.md", "image-upload-routing.md", "image-hosts/README.md", "cms/README.md", "cms/allincms/article-operations.md", "../TOOLS-INDEX.md", "../TEMPLATES/tool-field-map.md", "../QA-CHECKLIST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# Adapters

## 资料驱动的 Adapter 边界

Adapter 只把稳定业务 desired state 映射到当前平台，不决定客户事实和内容。用户资料先按 [ID-0005](../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md) 生成私有 [Source Extraction](../TEMPLATES/source-extraction.md)、来源/claim 账本和 operation plan；Adapter 在运行时发现站点、内容类型、字段、枚举、生命周期和当前部署内部接口，并返回有时效的 capability snapshot。测试站值、Action ID、router tree、deployment/build ID、Cookie 和 Token 不得成为通用合同。

每项能力必须标为 `live_verified_current_deployment / local_tested / exploration_only / unsupported`。任何远程 mutation 只接受当前 deployment 的未过期 `live_verified_current_deployment`；未知或漂移字段先探索，不允许 UI 静默降级。新建站必须拆为 account-scope `site_bootstrap` Plan A 和回读真实身份后的 site-scope `site_operation` Plan B；Adapter 不得消费一个同时 create site + populate 的未解析计划。

## 为什么分离

稳定知识记录“要完成什么、对象和字段是什么、如何验收”，adapter 只记录“某个工具当前如何承载它”。按钮、API 和平台变化时，只更新 adapter。

adapter 不是独立按钮教程，必须先引用 [MENTAL-MODEL.md](../MENTAL-MODEL.md)，再说明平台差异。

## 已建立的适配器

- 图片统一决策：[AllinCMS 优先与外部图床回退路由](image-upload-routing.md)
- CMS：[AllinCMS 观察型内部接口 adapter](cms/allincms-overview.md)；文章与分类只读逻辑见 [article-operations.md](cms/allincms/article-operations.md)
- 外部图床备选：[R2 / GitHub / 腾讯云 COS / 阿里云 OSS](image-hosts/README.md)

## 创建流程

1. 复制 [_template.md](_template.md) 并按工具命名；
2. 使用 [tool-field-map.md](../TEMPLATES/tool-field-map.md) 完成对象和字段映射；
3. 只引用官方资料或实际环境证据，不凭记忆编写当前按钮、版本和限制；
4. 不保存凭据，只记录认证类型和最小权限；
5. 跑单样本并保存真实验证证据；
6. 用 [failure-diagnosis.md](../TEMPLATES/failure-diagnosis.md) 记录失败；
7. 用 [transfer-exercise-record.md](../TEMPLATES/transfer-exercise-record.md) 比较第二工具。

## 每个具体 adapter 必须包含

1. 工具解决的问题、适用边界、版本或观察日期和复查日期；
2. 核心对象、字段和状态；
3. 支持的 GUI、API、CSV、CLI、MCP 或浏览器接口；
4. “稳定对象 / 字段 → 平台对象 / 字段 / 操作”映射；
5. 认证方式和最小权限，但不保存凭据；
6. 单样本输入、预期输出、真实验证和回滚；
7. 批量限制、幂等、重试、跳过和审计；
8. 常见失败的证据、诊断顺序和恢复方法；
9. 平台特有操作步骤及其来源；
10. 一次迁移练习或与另一工具的差异说明。

## 图片上传默认合同

- 目标是 AllinCMS 媒体库：先按 [AllinCMS AI 唯一入口第 0 节](cms/allincms/AI-START-HERE.md#0-默认启动登录交接与回落路由) 用宿主内置 Browser 处理登录、站点发现和精确媒体页，再默认调用 `uploadAllinCmsMediaSerial()`，不先走 PicGo；
- 单张接口原语由串行总控调用，其他 AI 不自行复制循环；
- 每张必须完成 AI 候选校验、单图上传、自动刷新、媒体记录、media ID、URL、匿名访问、解码、原子索引，以及获批后的单次 `title / alt / caption` 写入和有限只读复核；
- 永久严格串行：当前图片完整闭环后才开始下一张，禁止 `Promise.all`、任务池、多标签和重叠媒体请求；
- 上传报错先延迟并只读对账；确认已存在则补齐，只有精确确认不存在才有限重试当前图片。对账不明确或元数据结果不明确时停止本批，不盲目重传、不重发字段请求、不改走 UI；
- PicGo 与外部图床仅用于 CMS 解耦 URL、跨系统复用、迁移练习或用户明确指定。

## PicGo adapter 的额外要求

- 区分 PicGo 客户端 / CLI 与实际图床服务；
- 记录图片资产如何映射到 uploader、存储位置、URL 和引用；
- 检查安装、当前 uploader 和配置存在性，但不输出密钥；
- 先单图测试并验证 URL 可访问、内容正确、可在 Markdown / CMS 显示；
- 记录批量输入、输出、失败、重试、跳过、替换和失效恢复；
- 图床未确定、单图未验证时结论必须为 `BLOCK`。

## CMS adapter 的额外要求

- 记录 CMS 名称、版本或观察日期；
- 覆盖产品、文章、媒体、分类和发布状态对象；AllinCMS 当前已补齐文章 / 分类 schema 的只读参考页，但写入合同仍须单条草稿实跑后才可升级；
- 区分草稿、更新、发布、覆盖、删除和全局设置权限；
- 单条草稿通过后才能申请批量；
- 发布后获取真实 URL，并在浏览器验证；
- 首个 CMS 未指定前，不得伪造“可运行 adapter”。

## 当前状态

AllinCMS 是当前默认图片实现；站点发现、单图零点击接口直传、10 张严格串行直传、1–5 图语义化浏览器回退、零点击媒体记录删除，以及一张获批虚拟媒体的 `title / alt / caption` 最终持久化已有真实证据。媒体 adapter 已补齐只读对账、原子图片索引、断点恢复、单写者锁、AI 元数据单次写入和停批规则，并通过 45 项媒体测试。当前部署的 Markdown A/B/A 正文草稿已完成 2 个资产、3 个 occurrence 的原位绑定、后台回读、编辑器重载、3/3 解码和 Caption 可见验证；文章图片 adapter 通过 50 项测试，并强制 schema 2、逐 occurrence 双重复核、`bindingProof`、文章 operation lock 与整篇单次保存，保存后必须继续验证 Slate 编辑器存在、图片数量精确、全部解码、Caption 顺序一致和草稿标识。其他 AI 必须从 [AI 唯一执行入口](cms/allincms/AI-START-HERE.md) 开始。完整 `description`、notes 和结构化 metadata 只进入客户私有图片索引。PicGo 四种图床保留为外部备选。完整课程仍因任意大批次真实远程长跑、跨部署复杂正文、表格、公开主题 Alt、迁移和回滚证据不足而 `BLOCK`；媒体并发、一次请求多图和物理资产清理不再列为目标或阻断。
