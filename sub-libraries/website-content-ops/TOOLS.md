---
title: "Website Content Operations Tools"
description: "建站内容运营的工具中立选择逻辑、参考实现、安装边界和陌生工具接入方法。"
type: "tooling"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-27"
sources: ["MENTAL-MODEL.md", "PLAYBOOK.md", "REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md", "REFERENCES/SRC-20260727-ALLINCMS-OFFICIAL.md", "Tony decision 2026-07-27"]
related: ["ADAPTERS/README.md", "ADAPTERS/image-hosts/README.md", "ADAPTERS/cms/allincms-overview.md", "ADAPTERS/_template.md", "TEMPLATES/tool-field-map.md", "START-HERE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 工具选择

## 先选能力，不先选品牌

选择前先写清：业务问题、输入输出、稳定对象、所需接口、权限、批量、幂等、回滚、审计和单样本成功证据。

| 任务 | 稳定能力 | 参考实现 | 可替换方案 |
|---|---|---|---|
| 查看和维护知识 | 本地文件、链接、搜索、可迁移 | Obsidian | VS Code、Typora 等 |
| AI 协作 | 读写文件、检查环境、执行、验证、受权限约束 | Codex | 其他文件型 agent |
| 网站检查 | URL、时间、页面证据、差异 | 浏览器 + 可审计抓取 | sitemap、导出、CMS API |
| 图片进入 AllinCMS | media ID、公开 URL、批量记录、只读对账、失败恢复 | AllinCMS 零点击接口串行 adapter | 经批准的语义化 UI 回退 |
| 外部图片存储 | 与 CMS 解耦的公开 URL、跨系统复用 | PicGo + R2 / GitHub / COS / OSS | 对象存储 CLI/API |
| 内容发布 | 对象/字段映射、草稿、更新、发布、回滚 | AllinCMS adapter | CSV、API、GUI、浏览器操作 |
| 结果验证 | 检查真实用户可见结果 | 浏览器 | 监测与分析工具 |

## 确定顺序

```text
业务目标 → 稳定对象 / 字段 → 接口需求 → 检查现有环境
→ 选择最少工具 → 建立映射 → 单样本验证 → 人工确认 → 批量
```

## 安装与环境检查边界

- 先检查是否已经安装、是否存在多版本、配置是否可用，再提议安装；
- 安装软件或扩展属于机器状态变更，必须得到用户确认；
- 版本、下载地址和安装方式应在演示当天以官方来源为准，不把易过时命令写成永久真理；
- 可记录“配置存在 / uploader 名称 / 权限是否足够”，不得展示或复制密钥；
- 安装完成必须重新打开、执行一个最小操作并验证结果。

## 三个参考演示

### Obsidian

检查环境 → 经批准安装或打开 → 把子库 / 客户运行区作为 Vault → 搜索和链接 → 让 Codex 修改一个 Markdown → 在 Obsidian 中看到变更。

### AllinCMS 图片

目标是 AllinCMS 媒体库时，默认读取 [图片上传统一路由](ADAPTERS/image-upload-routing.md) 和 [AI 唯一入口](ADAPTERS/cms/allincms/AI-START-HERE.md)：准确媒体页 → 运行环境预检 → 零点击接口逐张串行 → 每张自动刷新验收 → 原子图片索引 → 下一张。无需 PicGo。

### PicGo 与外部图床

只在需要与 CMS 解耦的 URL、跨系统复用、迁移练习或用户明确指定时，检查安装与当前 uploader → 复制 adapter 模板 → 填写字段映射 → 单图上传 → 验证 URL、协议、图片内容和引用 → 经批准批量。

课程覆盖 R2、GitHub、腾讯云 COS 和阿里云 OSS。进入该路线后再从 [图床选择入口](ADAPTERS/image-hosts/README.md) 选择环境；不得把 PicGo 本身等同于存储服务，也不得伪造可运行配置。

- 国际公开站优先评估 R2；
- 已有腾讯云或阿里云资产时优先复用 COS / OSS；
- GitHub 仅用于无敏感、小规模课程演示和迁移练习；
- R2 需要验证当前 PicGo 的 S3 兼容插件、Skill 或 adapter，不能假设原生可用；
- GUI 与 CLI uploader 不一致时先停止，明确使用哪份配置后再上传。

### CMS

首个参考实现采用 [AllinCMS adapter](ADAPTERS/cms/allincms-overview.md)。当前媒体合同已经捕获并固化；其他 AI 不再从 UI 重新抓接口，直接调用唯一入口。只有 adapter 明确报告合同漂移，且用户批准使用一张新的虚拟资产重新捕获时，才进入协议更新流程。内部请求仍只能标记为 `observed_internal_contract`，不能冒充官方公开 API。

用户侧仍保持简单：选择网站 → 上传一张图片并取得媒体资产 → 建一个产品或文章草稿 → 检查后台与前台 → 经批准批量 → 记录回滚和发布结果。

## 陌生工具接入提示词

```text
请先识别这个工具解决什么业务问题、核心对象、字段和状态，
并检查它支持 GUI、API、CSV、CLI、MCP、浏览器操作中的哪些接口。
使用 TEMPLATES/tool-field-map.md 把稳定数据模型映射到它，
标出认证、权限、批量限制、幂等、回滚和验证方法。
先做一个样本，验证输入、输出、权限和回滚；确认后再批量。
不要先让我照着按钮教程操作。
```

## 迁移时什么该变

- 只在 `ADAPTERS/` 更新按钮、API、字段名、限制、版本和复查日期；
- 不因工具变化重写公司、产品、客户、内容、图片和发布记录的语义；
- 新工具不能满足关键质量闸时，换工具或降低自动化范围，不降低验收标准。
