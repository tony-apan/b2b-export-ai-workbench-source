---
title: "Website Content Operations Course Map"
description: "把原有十一课收束为工具、知识、小样、验证写回四个可执行阶段。"
type: "index"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-27"
sources: ["MENTAL-MODEL.md", "PLAYBOOK.md", "QA-CHECKLIST.md", "Tony decision 2026-07-27"]
related: ["START-HERE.md", "EXAMPLES/fluxpedal-motors/README.md", "ADAPTERS/image-upload-routing.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 四阶段课程地图

用户只按四个阶段执行；完整模型、模板和 QA 留给 AI 在需要时调用。

| 阶段 | 用户要完成什么 | AI 只读什么 | 必交付 | 通过闸 |
|---|---|---|---|---|
| 1. 工具 | 打开 Markdown；目标为 AllinCMS 时先做 API-first 登录/用户/完整站点检查，再确认精确媒体页、运行环境和私有索引路径 | `START-HERE.md`、图片上传路由、AllinCMS adapter | 工具检查记录 | 不泄露凭据；不擅自安装或改配置；目标和默认路线已说明 |
| 2. 知识 | 建公司、产品、ICP、客户语言四张卡 | 当前演示或客户来源、相关模板 | 四张知识卡 | 事实、推断、冲突、缺失分开；关键内容可追溯 |
| 3. 小样 | 做一篇 brief、一张图、AllinCMS 媒体映射和一条 CMS 草稿 | 当前 playbook 阶段、AllinCMS adapter | 单样本与图片索引 | media ID / URL / 哈希一一对应；失败只读对账；未经批准不发布 |
| 4. 验证写回 | 检查前台、记录指标和失败，再迁移第二工具 | QA、writeback、迁移记录 | 验收和写回 | 客户数据不回流公开包；第二工具独立小样通过 |

## 学习终点

学习者能解释并执行：

`来源 → 知识 → 客户任务 → 内容 / 图片 → 工具映射 → 单样本 → 验证 → 指标 → 写回`

学会的标准不是记住按钮，而是换到另一图床、CMS、开发信或社媒任务时，仍能重新调查字段、权限、接口和验收方法。

## 当前参考实现

- 虚拟公司：[FluxPedal Motors](EXAMPLES/fluxpedal-motors/README.md)；
- 产品：电动自行车轮毂电机；
- 内容链：虚拟聊天 → 搜索意图假设 → SEO/GEO article brief；
- CMS：AllinCMS 已确定为首个参考实现；图片默认走零点击接口逐张串行上传；
- 外部图床：R2、GitHub、COS、OSS 仅在需要独立公开 URL、跨系统复用或迁移练习时选择；
- 当前状态：虚拟知识、AllinCMS 媒体上传与 Markdown 正文图片原位绑定 adapter 已建立，A/B/A 草稿已真实验证；公开主题 Alt、跨部署复杂正文、完整草稿前台闭环和第二工具迁移仍为 `BLOCK`。
