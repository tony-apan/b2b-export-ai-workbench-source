---
title: "Failure Diagnosis Template"
description: "用证据区分输入、权限、映射、接口、平台、网络、验证和业务结果问题，避免盲目重试。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["../40_outputs/index.md", "../30_tasks/index.md"]
related: ["tool-field-map.md", "publish-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "执行失败或验证不一致时，用于分层定位输入、权限、映射、接口和业务结果问题。"
keywords: ["failure diagnosis", "permissions", "field mapping", "retry boundary", "evidence"]
generated_from: "../../TEMPLATES/failure-diagnosis.md"
generated_source_sha256: "cdf639a3126fc1117377c2e3a0fad8a19bb3ef4e9f225746ea0336ff38d15574"
generated_by: "scripts/sync-workspace-template.mjs"
---
<!-- Generated runtime copy from TEMPLATES/failure-diagnosis.md; do not hand-edit this copy in the source package. -->
# Failure Diagnosis

- Incident ID:
- Task ID:
- Tool / adapter version:
- Time:
- Intended action:
- Observed result:
- Exact error or evidence:
- Affected items:
- Credentials removed from record: yes / no

## Diagnose In Order

| Layer | Question | Evidence checked | Finding | Next action |
|---|---|---|---|---|
| Input | 输入文件、格式、必填字段是否完整？ |  |  |  |
| Knowledge | 业务事实是否确认，是否把推断当事实？ |  |  |  |
| Mapping | 稳定字段是否正确映射到平台字段？ |  |  |  |
| Permission | 当前账号是否允许该动作？ |  |  |  |
| Interface | GUI / API / CSV / CLI 的请求是否成立？ |  |  |  |
| Platform | 配额、状态、版本或平台限制是否触发？ |  |  |  |
| Network | URL、DNS、TLS 或连接是否正常？ |  |  |  |
| Verification | 是否只是返回成功，但真实结果不存在？ |  |  |  |
| Business | 技术成功是否仍未满足内容或客户目标？ |  |  |  |

## Recovery

- Root cause confidence:
- Safe to retry:
- Retry change:
- Rollback completed:
- Items requiring manual repair:
- Adapter or template improvement candidate:
- Human decision needed:
