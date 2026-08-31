---
title: "Tool Field Map Template"
description: "强制把稳定业务对象映射到具体平台对象、字段、接口、权限、限制、验证和回滚。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["../20_knowledge/index.md", "../30_tasks/index.md"]
related: ["failure-diagnosis.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "接入新的 CMS 或工具时，用于映射稳定业务对象、平台字段、权限和验收方法。"
keywords: ["tool field map", "CMS adapter", "object mapping", "permissions", "validation"]
generated_from: "../../TEMPLATES/tool-field-map.md"
generated_source_sha256: "91c90e55d0a7421185352f4363aa74f64798e7de03f93dce51f2445fd662d0e4"
generated_by: "scripts/sync-workspace-template.mjs"
---
<!-- Generated runtime copy from TEMPLATES/tool-field-map.md; do not hand-edit this copy in the source package. -->
# Tool Field Map

## Investigation

- Business problem:
- Tool / service:
- Version or observed date:
- Official documentation reviewed:
- Available interfaces: GUI / API / CSV / CLI / MCP / browser
- Chosen interface and reason:
- Authentication type:
- Required permissions:
- Read / draft / publish / update / delete boundaries:
- Rate, size, batch or quota limits:
- Unknowns requiring a test:

## Object And Field Mapping

| Stable object | Stable field / state | Platform object | Platform field / action | Required | Transform / default | Validation | Risk |
|---|---|---|---|---|---|---|---|
|  |  |  |  | yes / no |  |  |  |

## Single-sample Contract

- Input fixture:
- Expected platform state:
- Expected public result:
- Dry-run available:
- Idempotency key or duplicate rule:
- Verification evidence:
- Rollback action:
- Human approval required:

## Batch Contract

- Maximum first batch:
- Retry rule:
- Skip rule:
- Update / overwrite rule:
- Failure log location:
- Stop condition:
