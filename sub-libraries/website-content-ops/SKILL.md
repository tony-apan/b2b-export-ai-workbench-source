---
title: "Website Content Operations AI Skill Adapter"
description: "把建站内容运营子库的渐进读取、审批、单样本、验证和写回流程适配给可读取本地文件的 AI agent。"
type: "skill"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["README.md", "AGENTS.md", "START-HERE.md", "PLAYBOOK.md", "QA-CHECKLIST.md"]
related: ["README.md", "AGENTS.md", "START-HERE.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "ADAPTERS/cms/allincms/README.md", "QA-CHECKLIST.md", "VERSION.md"]
audience: ["Claude", "Codex", "可读取本地文件的 AI agent"]
release_status: "Preview"
skill_status: "preview-adapter-not-installable"
visibility: "public"
redaction_status: "safe-to-publish"
---
# Website Content Operations AI Skill

> **当前状态：Public Preview 已发布 / 非 Stable。** 本文件是子库内的 AI 适配器，不是一键安装或跨平台稳定的 Skill；实时状态以 `MANIFEST.md` 的 `preview_publication_status` 为准。宿主系统、用户项目和平台安全规则始终高于本文件。

## 什么时候使用

当用户希望 AI 帮助完成以下闭环时使用：

- 从网站、资料或客户语言建立有来源的公司、产品和 ICP 知识；
- 生成一篇内容、一张图片或一个 CMS 草稿；
- 调查陌生图床、CMS 或相邻营销工具；
- 复核真实结果，并把事实、失败和通用改进分层写回。

不要把本 Skill 用于：

- 没有来源的事实编造；
- 绕过账号权限或导出凭据；
- 未经批准的发布、删除、批量覆盖或社媒账号动作；
- 把当前 AllinCMS 部署证据外推成官方 API 或跨部署保证。

## 渐进读取

第一次只读：

1. [START-HERE.md](START-HERE.md)；
2. 用户明确提供的当前运行区入口；
3. 当前步骤需要的一个模板或 adapter。

按需读取：

- 底层对象和迁移： [MENTAL-MODEL.md](MENTAL-MODEL.md)；
- 完整执行： [PLAYBOOK.md](PLAYBOOK.md)；
- 工具调查： [TOOLS.md](TOOLS.md) 和对应 [ADAPTERS/README.md](ADAPTERS/README.md)；
- 验收： [QA-CHECKLIST.md](QA-CHECKLIST.md)；
- 写回： [WRITEBACK.md](WRITEBACK.md)。

禁止为了“保险”一次性读取整个子库。

## 默认执行协议

```text
检查来源和权限
→ 建立最小知识卡
→ 只做一个小样本
→ 获取后台 / 前台 / 文件回读证据
→ 记录失败、停止或回滚
→ 获批后再扩大范围
→ 分层写回
```

外部动作默认停在草稿或待批准状态。安装、发布、覆盖、删除、批量和全局修改都必须得到明确授权。

## 输入要求

开始前至少确认：

- 业务目标；
- 当前来源和来源状态；
- 目标工具、站点和权限边界；
- 用户希望得到的输出；
- 是否允许真实外部动作。

缺失事实必须标记为 `missing` 或 `待验证`，不能用推断填空。

## 输出要求

每一步返回：

- 使用了哪些来源；
- 修改或生成了哪些文件；
- 哪些是事实、推断和缺口；
- 是否需要人工批准；
- 如何验证真实结果；
- 失败或回滚记录写到哪里。

## 当前 AllinCMS 路由

目标是 AllinCMS 媒体库时，先读 [AllinCMS AI 唯一入口](ADAPTERS/cms/allincms/AI-START-HERE.md)，不要绕过当前 adapter 自行重抓或重写上传循环。当前路线仍受本子库 `MANIFEST.md` 的 Preview 限制与 Stable BLOCK 边界约束。

### 上传前必须取得精确授权

对 direct、serial、batch、single 四个媒体上传入口，`authorizationContext` 是不可省略的必需输入，不是可选 callback。执行 agent 必须：

1. 向当前用户展示并确认精确 AllinCMS `site_key`、操作 `allincms.media.upload` 和精确有序文件列表；
2. 记录用户声明的 approval actor 与批准时间；
3. 使用 `createAllinCmsMediaUploadAuthorizationContext()` 对文件名、字节数和 SHA-256 形成 file-list digest；
4. 把返回对象显式传给对应上传入口；
5. 任何文件内容/顺序、site、operation、entrypoint 变化，任何 `approved_at > now`，或最长 30 分钟授权在 `now >= expires_at` 时过期后，停止并重新批准；最终路径为 symlink 时不得开始。

底层 `uploadAllinCmsMediaDirect()` 自身也会 fail closed，不能依赖 `beforeRequest`、UI 状态或上层“已经问过用户”的口头假设。direct/serial 必须沿用首次通过 digest 校验的源 Buffer；batch/single 必须使用安全 Buffer payload，不得在确认前把原始路径重新交给浏览器。`beforeRequest` 返回后或确认点击前必须重新校验完整授权、逐文件 digest 和当前时间。授权记录的 actor 是 `human-asserted` 声明，身份状态固定为 `not_verified`；本 Skill 不验证或证明批准者真人身份。当前本地 adapter 回归为 131/131，媒体上传子集为 45/45；这仍不证明真实 CMS、跨部署或发布资格。

## 适配范围

本 Skill 只定义业务流程和读取路由；工具按钮、接口、字段和当前部署证据留在 `ADAPTERS/`。如果宿主平台没有本地文件读取、浏览器、脚本或相应权限，必须明确报告不可执行，不得假装完成。

## 发布闸

在 `MANIFEST.md` 的 `release_status` 不是 `Ready` 或 `Published` 前，不得把本文件当作稳定外部 Skill 推荐给用户。发布前还必须通过品牌、联系、许可、去敏、参考实现、迁移和打包验收。

### 文章、分类、标签与正文图片变更授权

所有 AllinCMS 文章、分类、标签和正文图片草稿 mutation 必须传入结构化 `authorizationContext`；裸布尔值或“上层已经确认”的口头状态无效。该对象必须精确绑定 `site_key`、operation、目标摘要、具名 `human-asserted` actor、`approved_at` 与不超过 30 分钟的 `expires_at`，并在每次远程请求前重验。actor 身份固定为 `not_verified`；本地对象不证明真人批准。发布、删除仍需独立明确人工批准；子库当前仅为 Preview，远程副作用授权和 Stable qualification 仍独立 BLOCK。
