---
title: "Website Content Operations Templates Index"
description: "说明本子库模板的用途、实例化方式、证据要求和客户数据边界。"
type: "index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["../README.md", "../MANIFEST.md", "../QA-CHECKLIST.md"]
related: ["../START-HERE.md", "../WORKSPACE-TEMPLATE/README.md", "../WRITEBACK.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# 模板目录

这里是 `website-content-ops` 的结构化模板入口。模板用于把输入、字段、证据、失败和写回记录成可复核文件；它们不是客户运行数据，也不是自动发布指令。

## 使用规则

1. 先从 [START-HERE.md](../START-HERE.md) 判断当前任务阶段。
2. 只复制当前阶段需要的模板，不要一次读取或填写全部模板。
3. 新文件中的公司、客户、联系、价格、指标和发布结果必须有来源或状态。
4. 客户真实数据只能进入客户私有运行区，不得回写本公开母库。
5. 模板本身不能代替 [QA-CHECKLIST.md](../QA-CHECKLIST.md) 的真实验收。

## 模板分类

- 业务对象：公司、产品、客户语言、文章 brief。
- 媒体与发布：图片清单、发布记录。
- 工具迁移：字段映射、迁移练习、失败诊断。
- 来源与写回：来源登记和可复用经验记录。
- 长期知识页：需要进入 `MANIFEST.md` 声明的 durable roots 时，使用 [durable page 模板](durable-page.md)，并补齐 `doc_id`、读取时机和检索词。

## 不要把模板当成完成证据

模板填写完成只代表资料结构存在。只有完成真实动作、后台或前台回读、失败记录和写回，任务才可能通过验收。
