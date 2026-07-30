---
title: "Course Module Template"
description: "课程模块模板，用于把已登记来源提炼成可学习、可练习、可人工复核、可验证和可写回的教学单元；front matter 字符串不能替代独立证据。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
when_to_read: "把已登记来源和方法整理为可学习、可练习、可验收并可写回的课程模块时。"
keywords: ["课程模块", "练习", "人工复核", "验证", "知识写回"]
template_usage: "creator-compatible"
sources: ["../00_meta/knowledge-compounding-system.md", "../00_meta/definition-of-done.md"]
related: ["../90_outputs/courses/index.md", "playbook.md", "verification-record.md", "writeback-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
template_target_kind: "durable"
template_target_type: "course-module"
---
# Course Module Template

课程状态必须分三层记录：`structure_verification_status` 只表示文件链和字段结构，`exercise_verification_status` 只表示真实练习提交及其人工复核，`effectiveness_verification_status` 只表示真实世界效果。模板默认 `pending / pending / unverified`；普通结构校验不能把后两层升级为通过。进入 release 资格校验前，还必须把 `exercise_artifact`、`review_record`、`verification_record` 和 `writeback_record` 指向四个不同且存在的文件，review record 绑定 exercise artifact 的 SHA-256，并由外部签名 sidecar 证明审批边界。

<!-- DOCUMENT_TEMPLATE_START -->
---
doc_id: "{{doc_id}}"
title: "{{title}}"
description: "{{description}}"
type: "{{type}}"
status: "Seed"
owner: "AI"
created: "{{today}}"
last_updated: "{{today}}"
when_to_read: "{{when_to_read}}"
keywords: {{keywords}}
sources: {{sources}}
related: []
visibility: "public"
redaction_status: "not-reviewed"
course_id: "COURSE-{{today}}-待分配"
module_order: 1
level: "beginner"
learning_outcomes: []
structure_verification_status: "pending"
exercise_verification_status: "pending"
effectiveness_verification_status: "unverified"
exercise_artifact: ""
review_record: ""
verification_record: ""
writeback_record: ""
---
# {{title}}

## 1. 适用对象与前置条件

- 适用对象：待补。
- 前置知识：待补。
- 不适用场景：待补。

## 2. 学习目标

- 待补一个可观察、可验收的学习结果。

## 3. 来源与证据

| Source ID / 页面 | 支持的事实或方法 | 证据状态 | 边界 |
|---|---|---|---|
| 待补 | 待补 | confirmed / inferred / pending | 待补 |

## 4. 可执行步骤

1. 待补。

## 5. 变化场景练习

- 输入：待补。
- 变化条件：第二客户、第二场景或陌生工具。
- 输出：待补。

## 6. 验收与人工复核

- [ ] 独立 exercise evidence artifact 已保存。
- [ ] 人工 review record 已绑定 artifact SHA-256。
- [ ] verification 与 writeback 均有存在的 event/snapshot 证据。

## 7. 已验证结果与边界

- 当前只允许写结构或练习草案结论；没有完整证据链时不得宣称真实效果 PASS。
<!-- DOCUMENT_TEMPLATE_END -->
