---
title: "Live AllinCMS Operation Adversarial Review"
description: "针对真实 AllinCMS 站点、媒体、文章、产品、主题、路由和首页操作的对抗审查合同：证据轴、能力闸、不可变计划、双审门槛和可分享 Skill 硬性条件。"
type: "playbook"
status: "Draft"
owner: "AI"
created: "2026-08-26"
last_updated: "2026-08-26"
sources: ["SOL dual review 2026-08-26", "TERRA dual review 2026-08-26", "AllinCMS live operations on FluxPedal Motors", "interface-registry.json capability routes"]
related: ["../README.md", "../SKILL.md", "../START-HERE.md", "../QA-CHECKLIST.md", "id-0005-source-driven-cms-operation-sop.md"]
doc_id: "ID-0006"
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "执行或审查 AllinCMS 真实建站、媒体上传、文章/产品发布、主题页/路由/首页配置，或准备把活运行操作沉淀为可分享 Skill 时。"
keywords: ["live operation", "adversarial review", "dual review", "AllinCMS", "capability gate", "Plan A", "Plan B", "shareable skill"]
---
# Live AllinCMS Operation Adversarial Review

> 本页是双审（SOL + TERRA）升级后的对抗审查合同。它不替代 [ID-0005 Source-Driven CMS Operation SOP](id-0005-source-driven-cms-operation-sop.md)，而是定义“真实操作是否达到可审计、可复用、可分享”的硬性证据轴。

## 1. 为什么需要升级

之前一次 FluxPedal Motors 真实验证跑通了：

- 创建站点；
- 上传真实图片；
- 发布完整文章；
- 发布产品；
- 创建并发布主题页、绑定路由、设置首页；
- 前台 HTTP 200、无 `__next_error__`。

双审结论均为 **BLOCK**。原因不是页面不可访问，而是：

> **操作真实存在，但缺少 canonical capability、不可变计划、授权证据、完整回读和可分享证据链。**

因此本页把“后台/前台能打开”升级为“可审计、可复用、可分享”。

## 2. Capability Gate（先查能不能跑）

任何真实 mutation 前，必须从当前 deployment 的机器注册表确认：

| 操作 | 最低能力 | 当前/历史状态 |
|---|---|---|
| `site.discover` | `canonical` | 可读 |
| `site.create` | `live_verified_current_deployment` | 当前为 blocked/未达 |
| `media.create` | `canonical` | 可用 |
| `media.update` / `media.delete` | 需结构化授权 | 当前为 blocked |
| `article.create` | 需合同确认 | 当前 blocked/未达 |
| `article.update` / `article.publish` | `canonical` | 可用 |
| `product.*` | `live_verified_current_deployment` | 当前为 exploration_only |
| `theme/page/route/home mutation` | 需 canonical controller + 证据 | 当前未达 |
| delete / unpublish | 独立授权 | 当前为 blocked |

规则：

```text
capability 为 exploration_only、blocked 或未达到 live_verified_current_deployment
→ 不得作为可复用 Skill 路径
→ 只能作为私有探索证据
→ 不得宣称 qualified / stable / production-ready
```

## 3. 不可变两阶段计划

新建站必须严格分离：

### Plan A：account-scope site bootstrap

- target 是当前 RSC 回读的 `user.id`；
- `site_key/site_id = null`；
- 只含一个 `site:create`；
- 必须记录创建前完整站点 ID 集合；
- 创建后必须用完整站点列表 before/after 唯一差集证明只新增 1 个站点；
- 回读真实 `site_id`、`site_key`、`displayDomain`、owner、`setupError`；
- 未通过前不得进入 Plan B。

### Plan B：site-scope operation

- 引用 Plan A digest 和私有 readback；
- 重新发现 capability、current state、action ID、router tree、deployment；
- 只允许真实 `site_id/site_key` 下的分类、标签、媒体、文章、产品、主题、路由、首页；
- 每个 mutation 必须有精确 identity、expected-current fingerprint、create/update/noop 解析、authorizationContext、serial 顺序、readback。

禁止：

```text
一个计划里同时 create site + populate
用 <planned-site> 占位
跨站 fallback
模糊匹配后 update
```

## 4. 每次 mutation 必须有的证据

| 证据轴 | 最低要求 |
|---|---|
| 来源 | Source Extraction，含原始 digest、locator、提取器/version、置信度、warning |
| 授权 | 结构化 `authorizationContext`，绑定 site、operation、目标 digest、具名 human-asserted actor、approved_at、<=30min expires_at |
| 计划 | 不可变 operation plan digest；upsert 已解析为 create/update/noop |
| 请求 | 动态 action ID、router tree、x-deployment-id；禁止硬编码 |
| 响应 | HTTP 状态、Content-Type、RSC data/error 原文（私有） |
| 后台回读 | 精确 ID、slug、字段、状态、同站点绑定 |
| 编辑器重开 | 草稿/已发布状态、字段回显、组件可用 |
| 前台 | 匿名 GET、精确 URL、无 `__next_error__`、标题/正文/图片/规格 |
| 媒体 | 源 SHA-256、上传后 remote SHA-256、匿名 fetch、MIME、尺寸、decode |
| 图片/样式 | 封面、内联图片、alt、caption、可见性 |
| 路由/主题 | 页面已发布、首页设置、主题 active、route mapping |
| 失败 | 歧义只读对账记录；不盲重试 |

## 5. 对抗审查触发条件

出现以下任一项，必须升级为对抗审查：

- 从“后台成功”跨到“前台可见”；
- 从“单站点验证”跨到“可分享 Skill”；
- 使用 blocked / exploration_only capability；
- 涉及新站点、产品、主题、路由、首页；
- 图片、文章、产品、媒体元数据有真实外部副作用。

## 6. 双审门槛

准备分享 Skill 前，必须完成 SOL 与 TERRA 双审，且各自满足：

- 输出明确 `PASS / CONDITIONAL / BLOCK`；
- 列出 P0 / P1 / P2；
- 指出未验证的 SEO、排名、询盘、转化、真实效果；
- 指出是否需要 redact token、cookie、opaque action ID、raw RSC/Flight、客户标识；
- 给出“可分享 Skill 硬门槛”清单。

只有双审均不再出现 P0，且 P1 有可执行修复，才能进入候选分享。

## 7. 完成标准

一个真实 AllinCMS 操作只有满足以下才算完成：

```text
capability 允许
+ 来源与事实绑定
+ 不可变 Plan A/B 或 site-scope operation plan
+ 精确授权
+ 严格串行执行
+ 后台回读
+ 编辑器重开
+ 匿名前台精确 URL 验证
+ 无 __next_error__
+ 桌面/移动检查（有真实 renderer evidence）
+ 图片 fetch/decode/hash
+ 路由/主题/首页确认
+ 去敏化与私有边界
+ 达到 live_verified_current_deployment 或明确标记 BLOCK
```

## 8. 分享 Skill 前的禁止项

- 不得把 `exploration_only` 或 `blocked` capability 包装成通用能力；
- 不得把单站点成功外推为跨部署稳定；
- 不得在公开 Skill 中放 token、cookie、真实客户标识、opaque action ID、原始 Flight/RSC；
- 不得把 HTTP 200 当成发布成功；
- 不得把“已验证一次”写成“生产可用”；
- 不得在双审未通过时声称 shareable / stable / production-ready。
