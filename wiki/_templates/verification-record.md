---
title: "Verification Record Template"
description: "验证记录模板，用于分别记录知识链结构、课程练习和真实效果的验证状态，并把课程、独立练习、review、事件、快照与范围化结论绑定；默认不宣称真人身份或真实世界效果。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-29"
when_to_read: "课程或知识链需要分别记录结构、练习与真实效果验证，并限制可声明结论时。"
keywords: ["验证记录", "结构验证", "练习验证", "效果验证", "允许声明"]
template_usage: "manual-copy"
sources: []
related: ["course-module.md", "writeback-record.md", "../00_meta/definition-of-done.md"]
visibility: "public"
redaction_status: "not-reviewed"
---
# Verification Record Template

文件名建议：`VER-YYYYMMDD-topic.md`。以下字段与 `scripts/validate-knowledge-chain.mjs` 的机器合同一致；新记录默认保持 `pending` / `unverified`，只能由真实证据推动升级：

```yaml
---
title: ""
description: "说明验证对象、结构与练习证据、允许得出的范围化结论，以及明确不能推出的效果结论。"
type: "verification-record"
status: "Working"
owner: "AI | Human | Team"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
sources: ["SRC-YYYYMMDD-####"]
related: []
verification_id: "VER-YYYYMMDD-topic"
course_doc_id: "ID-####"
structure_verification_status: "pending"
exercise_verification_status: "pending"
effectiveness_verification_status: "unverified"
exercise_artifact: "../evidence/EX-YYYYMMDD-topic.md"
review_record: "../reviews/REV-YYYYMMDD-topic.md"
sample_size: 0
observed_result: "pending; no observation recorded"
allowed_claim: "pending; no positive claim is allowed"
non_claim: "No real-world effectiveness, customer outcome, production readiness, or reviewer identity is verified."
event_refs: []
snapshot_refs: []
visibility: "public | private"
redaction_status: "safe-to-publish | not-reviewed"
---
```

状态枚举：

- `structure_verification_status`: `pending | verified | failed`
- `exercise_verification_status`: `pending | verified | failed`
- `effectiveness_verification_status`: `unverified | real-world-effectiveness-verified | failed`

`synthetic: true` 的来源链最多验证结构和练习，不得把效果状态升级为 `real-world-effectiveness-verified`。

## Claim Being Tested

- Claim：
- Allowed interpretation：
- Explicit non-claim：

## Steps And Evidence

| Step | Action | Expected | Observed | Evidence | Result |
|---|---|---|---|---|---|
| 1 |  |  |  |  | pass / fail / blocked |

## Result And Boundary

- Scope-limited result：PASS / PARTIAL / BLOCK
- What is proven：
- What is not proven：
- Reproduction notes：
