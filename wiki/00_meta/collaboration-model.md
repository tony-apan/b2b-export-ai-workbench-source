---
title: "Collaboration Model"
description: "定义多人共同维护知识库时的角色、权限、改动流程、冲突处理和审核规则。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request"]
related: ["markdown-standard.md", "agent-handoff.md", "publishing-and-redaction.md"]
---

# Collaboration Model

多人一起维护时，核心原则是：事实来源可追溯，敏感信息不外泄，结构由少数人把关，日常沉淀可以多人参与。

## Roles

| Role | Can Do | Should Not Do |
|---|---|---|
| Owner | 决定结构、发布策略、敏感信息规则 | 跳过审核直接公开敏感资料 |
| Maintainer | 更新 wiki、合并页面、维护索引和 SOP | 改写 raw 原始资料 |
| Contributor | 提交资料、补充案例、写草稿 | 直接修改核心规则 |
| Reviewer | 审核事实、去敏、版权和业务风险 | 只看文字不看来源 |
| AI Agent | 提炼、链接、归类、生成草稿和检查清单 | 编造事实、删除历史来源、公开 raw |

## Change Workflow

1. Contributor 把资料放入 `raw/00_inbox/` 或指定 raw 目录。
2. Maintainer/AI 按 [source-taxonomy.md](source-taxonomy.md) 判断资料类型。
3. Maintainer/AI 更新 source registry、相关 wiki 页和索引。
4. Reviewer 检查敏感信息、版权、事实来源和对外风险。
5. Owner 决定是否可发布到 GitHub 或对外使用。

## Ownership Fields

每个重要页面建议补充：

```yaml
owner: "AI"
maintainers: []
reviewers: []
visibility: "public | internal | private"
```

## Conflict Rules

- 同一事实冲突：保留两版来源，写明冲突，不直接覆盖。
- 结构冲突：以 `module-registry.md` 和 `markdown-standard.md` 为准。
- 发布冲突：以 [publishing-and-redaction.md](publishing-and-redaction.md) 为准，默认不公开。

## Review Checklist

- 是否有来源？
- 是否有敏感信息？
- 是否有版权风险？
- 是否更新索引？
- 是否更新创建/更新时间？
- 是否会误导新人或 AI？

