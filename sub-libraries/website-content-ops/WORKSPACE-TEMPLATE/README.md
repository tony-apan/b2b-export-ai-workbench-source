---
title: "Customer Workspace Template"
description: "交付给单个使用者后复制使用的私有运行区模板，承载来源、知识、任务、输出、指标和写回。"
type: "template"
template_usage: "manual-copy"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["TEMPLATES/README.md"]
related: ["00_intake/index.md", "90_writeback/index.md", "TEMPLATES/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
when_to_read: "需要从子库复制一个隔离客户工作区并理解目录、隐私和写回边界时。"
keywords: ["workspace template", "client runtime", "privacy boundary", "writeback", "content operations"]
---
# 客户运行区模板

本目录是**空模板**，可以公开分发；复制并填入真实公司、产品、聊天、账号环境和结果后，副本默认是客户私有运行区，不应提交回公开子库。

## 初始化

1. 把整个 `WORKSPACE-TEMPLATE/` 复制到客户自己的受控目录，并改名为 `workspace/`；
2. 用 Obsidian 把 `workspace/` 作为一个 vault 打开，或作为现有 vault 的子目录；
3. 先完成 [00_intake/index.md](00_intake/index.md) 和 [10_sources/index.md](10_sources/index.md)；需要填写结构化记录时，从 [TEMPLATES/README.md](TEMPLATES/README.md) 选择最窄模板。
4. 再让 AI 读取 [20_knowledge/index.md](20_knowledge/index.md) 生成知识卡；
5. 所有执行任务进入 [30_tasks/index.md](30_tasks/index.md)，结果进入 [40_outputs/index.md](40_outputs/index.md)；
6. 指标进入 [50_metrics/index.md](50_metrics/index.md)，学习进入 [90_writeback/index.md](90_writeback/index.md)。

## 运行目录

```text
workspace/
├── 00_intake/      # 范围、权限、目标、工具和阻断
├── 10_sources/     # 网站、资料、聊天、导出和来源登记
├── 20_knowledge/   # 公司、产品、客户需求、内容意图和证据
├── 30_tasks/       # 待执行任务、字段映射、审批和运行记录
├── 40_outputs/     # 文章、产品页、图片清单、CMS 草稿和 URL
├── 50_metrics/     # 抓取、索引、点击、询盘、引用和转化反馈
└── 90_writeback/   # 客户专属学习与可申请回母库的通用改进
```

## 安全边界

- 可以记录凭据是否存在、权限是否足够，但不要把密码、token、cookie 或 Secret 写进 Markdown；
- 原始聊天、客户名单、价格和经营数据默认只留在客户运行区；
- AI 可读不等于可公开；发布前另走脱敏和授权检查；
- 子库升级时更新方法和模板，不覆盖客户已填写的运行数据。
