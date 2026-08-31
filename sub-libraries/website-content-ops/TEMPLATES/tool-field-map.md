---
title: "Tool Field Map Template"
description: "强制把稳定业务对象映射到具体平台对象、字段、接口、权限、限制、验证和回滚。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["../MENTAL-MODEL.md", "../ADAPTERS/README.md"]
related: ["transfer-exercise-record.md", "failure-diagnosis.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "接入新的 CMS 或工具时，用于映射稳定业务对象、平台字段、权限和验收方法。"
keywords: ["tool field map", "CMS adapter", "object mapping", "permissions", "validation"]
---
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
