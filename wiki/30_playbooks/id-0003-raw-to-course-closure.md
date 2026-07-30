---
doc_id: "ID-0003"
title: "Raw to Course Closure"
description: "面向需要把去敏原始对话提炼成可复用课程的人和 AI，提供来源登记、事实分层、概念与 playbook 提炼、练习、验证和写回步骤，帮助形成可追溯闭环；不把单次对话升级为市场事实。"
type: "playbook"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
sources: ["SRC-20260728-0001"]
related: ["../00_meta/raw-conversation-and-course-pipeline.md", "../00_meta/knowledge-compounding-system.md", "../20_concepts/id-0002-index-discovery-contract.md", "../90_outputs/courses/id-0004-structure-to-course-closure.md"]
when_to_read: "当需要把一份原始对话或访谈变成课程、练习或可复用方法时，先读本 playbook；如果资料含真实客户或账号数据，先切换到私有运行区。"
keywords: ["raw", "source registry", "course pipeline", "facts", "exercise", "verification", "writeback"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Raw to Course Closure

## Use When

适用于把一份已去敏、已确认可处理的原始对话或虚拟训练样本，转换为可追溯的课程模块。它不适用于把真实客户原文直接公开，也不允许仅凭单次对话下结论。

## Inputs

- 一个 `raw/10_conversations/` 中的原始对话或明确标记的 synthetic fixture；
- 来源 ID、采集时间、来源类型、敏感级别和同意/公开状态；
- 当前相关 concept、playbook、课程模板和验证模板；
- 明确的输出范围和人工审批点。

## Steps

1. **确认边界**：判断资料是否真实、虚拟、公开安全或只能进入私有运行区；不把真实凭据、客户数据和未授权课程材料写入公开母库。
2. **归档原始资料**：使用 `src-YYYYMMDD-####-slug.md`，保留原文/转写和上下文，不在 raw 中写最终结论。
3. **登记来源**：在 `wiki/10_sources/source-registry.md` 建立 Source ID，记录来源路径、类型、吸收状态、置信度和派生页面。
4. **提取分层信息**：分别写出 confirmed facts、representative quotes、inferences、conflicts 和 open questions；synthetic fixture 的内容不能伪装成真实客户证据。
5. **提炼稳定知识**：只有能复用且边界清楚的部分才进入 `wiki/20_concepts/` 或 `wiki/30_playbooks/`，并保留来源指针。
6. **建立课程模块**：课程页必须有学习对象、学习目标、来源表、操作步骤、第二场景练习、验收标准、失败模式和人工审批点。
7. **验证练习**：用与样本不同的第二场景检查学员是否掌握方法，而不是复述原文或记忆按钮路径。
8. **写回结果**：创建 verification record 和 writeback record，更新 source registry、相关知识页、open questions、索引和当日日志。
9. **发布判断**：局部闭环通过不等于母库或子库 Published；许可证、清洁目录复现、安装、运行、失败恢复和人工批准仍按各自合同执行。

## Output Format

```text
raw source
  -> source registry
  -> facts / quotes / conflicts / questions
  -> concept or playbook
  -> course module
  -> second-scenario exercise
  -> verification record
  -> writeback record
  -> index + daily log
```

## Quality Check

- [ ] raw 文件明确标注真实/虚拟、敏感级别和公开边界。
- [ ] source registry 的 Source ID 与 raw 文件一致。
- [ ] 事实、推断、冲突和待验证项没有混写。
- [ ] 概念或 playbook 没有超出来源证据范围。
- [ ] 课程包含第二场景练习和可操作验收标准。
- [ ] verification record 写清楚证明了什么、没有证明什么。
- [ ] writeback record 已更新来源、知识页、开放问题和日志。
- [ ] 没有因为该样本通过而解除母库或子库发布 BLOCK。
