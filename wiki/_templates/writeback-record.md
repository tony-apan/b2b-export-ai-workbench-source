---
title: "Knowledge Writeback Record Template"
description: "知识写回记录模板，用于把经过 review 和 verification 的范围化结果绑定到来源、课程、事件、快照及具体知识目标；默认 pending，不能用一句‘已写回’替代变更摘要和目标证据。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
when_to_read: "经过 review 和 verification 后，需要记录范围化结果计划写回哪些知识目标及其证据时。"
keywords: ["知识写回", "writeback", "验证结果", "变更目标", "证据绑定"]
template_usage: "manual-copy"
sources: []
related: ["course-module.md", "verification-record.md", "../00_meta/open-questions.md"]
visibility: "public"
redaction_status: "not-reviewed"
---
# Knowledge Writeback Record Template

文件名建议：`WB-YYYYMMDD-topic.md`。以下字段与 `scripts/validate-knowledge-chain.mjs` 的机器合同一致；新记录默认不表示写回已完成：

```yaml
---
title: ""
description: "说明哪些范围化执行结果计划写回哪些知识页、指标或开放问题，以及哪些仍未确认。"
type: "writeback-record"
status: "Working"
owner: "AI | Human | Team"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
sources: ["SRC-YYYYMMDD-####"]
related: []
writeback_id: "WB-YYYYMMDD-topic"
course_doc_id: "ID-####"
writeback_status: "pending"
verification_record: "../verification/VER-YYYYMMDD-topic.md"
review_record: "../reviews/REV-YYYYMMDD-topic.md"
change_summary: "pending; no knowledge change has been applied"
writeback_targets: []
event_refs: []
snapshot_refs: []
visibility: "public | private"
redaction_status: "safe-to-publish | not-reviewed"
---
```

只有目标文件真实存在、变更已经完成且事件与快照证据可复现时，才能把 `writeback_status` 改为 `completed`。写回不得扩大 verification 的 `allowed_claim`，也不得把 synthetic 练习写成真实效果。

## Observed Evidence

- What happened：
- Evidence path：
- Sample size：
- Data quality limitation：

## Knowledge Changes

| Knowledge area | Page / registry | Change | Evidence |
|---|---|---|---|
| source / concept / playbook / course / metric / open question |  |  |  |

## Safety And Publication

- PII / client data removed：
- Copyright / license checked：
- Public release impact：
- Human approval：not verified by this record
