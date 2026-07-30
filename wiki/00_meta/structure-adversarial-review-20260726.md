---
title: "Knowledge Base Structure Adversarial Review 2026-07-26"
description: "对当前公开知识库是否支持新人学习、AI 执行、知识复利、子库分发和陌生工具迁移的证据化审查。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-26"
sources: ["Repository structure inspected 2026-07-26", "Tony conversation 2026-07-26"]
related: ["current-focus.md", "module-registry.md", "sub-library-contract.md", "../../sub-libraries/website-content-ops/MANIFEST.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 知识库结构对抗审查

## 总结论

`BLOCK`。本轮已把“文件集合”推进为“可逐课执行的源码包骨架”，但当前仓库仍是公开版，私有母库未确定；首个子库也没有真实参考实现和迁移证据，不能声称课程已可交付。

## 审查问题

1. 新手不知道文件名时，能否按顺序完成？
2. AI 能否知道输入、输出、权限、停止条件和写回位置？
3. 换工具后能否保留稳定模型，而不是重写按钮教程？
4. 客户事实、公开方法、发布包和运行数据是否分层？
5. 失败、指标和聊天信号能否让知识持续复利？
6. 模块状态是否反映真实成熟度，而不是“有页面就 Working”？

## 本轮已修复

| 原问题 | 修复 | 当前状态 |
|---|---|---|
| 子库缺少用户逐课路线 | 新增 `COURSE-MAP.md`，每课有必读、必交付、通过闸 | PASS for structure |
| playbook 要求创建 workspace，但没有可复制模板 | 新增 `WORKSPACE-TEMPLATE/` 七层运行区 | PASS for template |
| 工具接入仍靠 prose | 新增字段映射、adapter、迁移和失败诊断强制模板 | PASS for contract |
| 大量文件没有人类可点击入口 | README 建立完整导航，课程地图串起学习顺序 | PASS for navigation |
| `Working` 同时表示“有内容”和“已在执行” | registry 拆成 Lifecycle 与 Execution | PASS for governance |
| 多模块同时看似在推进 | 新增 `current-focus.md`，只允许一个 Active | PASS for focus |
| 源码占位符与发布 QA 冲突 | 区分 Draft 源码包与品牌化 release artifact | PASS for semantics |
| ICP / objections 在概念层和业务层职责模糊 | 明确定义归概念、当前答案归业务并互相回链 | PASS for ownership |

## 仍然阻断

### BLOCK-1：没有真实私有母库

当前仓库规则明确把它作为公开去敏版。真实公司、产品、客户、课程、聊天、经营数据和长期 raw 不能进入这里。没有私有母库位置，就没有完整的长期 source of truth。

### BLOCK-2：没有参考实现证据

Obsidian、PicGo 和 CMS 目前只有方法、模板和验收要求。尚未确认实际版本、图床、CMS、权限、单样本 URL、批量结果、回滚和失败记录。

### BLOCK-3：没有迁移能力证据

尚未在第二图床或 CMS 上独立调查、映射并验证单样本，也没有把同一知识迁移到相邻业务任务的记录。

### BLOCK-4：没有可发布品牌制品

品牌、联系、许可证、版本、更新地址和第一种交付格式未确定。源码模板允许占位符，但任何占位符存在时 release 必须保持 `BLOCK`。

### BLOCK-5：没有虚拟端到端业务样本

尚未选择虚拟公司、产品、市场、客户聊天和目标网站，无法演示“网站 / 聊天 → 知识 → SEO/GEO brief → 图片 → CMS → 指标 → 写回”。

## 下一验收顺序

```text
拍板私有母库与交付边界
→ 选择虚拟公司 / 产品 / 市场
→ 确定 Obsidian / PicGo 图床 / 首个 CMS
→ 跑一个端到端小样并保存证据
→ 跑第二工具迁移
→ 跑一个相邻业务任务迁移
→ 注入品牌 / 联系 / 许可
→ 生成 release artifact 并全量检查
```

在上述证据完成前，不得把 `Draft` 改为 `Working`、把 `Active` 改为 `Validated`，也不得把 release 结论改为 `PASS`。
