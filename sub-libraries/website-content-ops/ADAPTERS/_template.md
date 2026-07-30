---
title: "Adapter Template"
description: "为具体图床、CMS 或平台建立可复查、可测试、可回滚和可迁移的 adapter 强制结构。"
type: "template"
template_usage: "manual-copy"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["README.md", "../MENTAL-MODEL.md"]
related: ["../TEMPLATES/tool-field-map.md", "../TEMPLATES/failure-diagnosis.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要为新的 CMS、图床或平台建立可测试、可回滚的 adapter 合同时。"
keywords: ["adapter contract", "field mapping", "permissions", "rollback", "single sample"]
---
# Adapter: {{tool-name}}

> 源码模板可以保留占位符；创建具体 adapter 时必须替换。未完成映射、单样本和验证前，adapter 状态只能是 `Draft`，发布结论必须是 `BLOCK`。

## 1. Scope

- Business problem:
- Tool / service:
- Version or observed date:
- Review after:
- Official sources:
- Supported scope:
- Explicit exclusions:

## 2. Objects And States

| Stable object | Platform object | Stable state | Platform state | Notes |
|---|---|---|---|---|
|  |  |  |  |  |

## 3. Interfaces And Permissions

| Interface | Available | Chosen | Authentication | Minimum permission | Limits | Risk |
|---|---|---|---|---|---|---|
| GUI / API / CSV / CLI / MCP / browser |  |  |  |  |  |  |

不得保存密码、token、cookie、SecretId、SecretKey 或完整凭据配置。

## 4. Field Mapping

填写 [tool-field-map.md](../TEMPLATES/tool-field-map.md)，并在这里链接实际记录：

- Mapping record:
- Transform rules:
- Required defaults:
- Duplicate / idempotency rule:

## 5. Reference Sample

- Input fixture:
- Precondition check:
- Dry-run or draft action:
- Expected result:
- Actual result:
- Verification evidence:
- Human approval:
- Rollback tested:

## 6. Batch And Audit

- First batch limit:
- Retry / backoff:
- Skip rule:
- Update / overwrite rule:
- Stop condition:
- Audit log:
- Failure record:

## 7. Failure Diagnosis

- Known failure signatures:
- Diagnosis order:
- Recovery:
- Escalation boundary:
- Linked diagnosis records:

## 8. Transfer Comparison

- Compared tool:
- Stable model retained:
- Platform differences:
- Migration single sample:
- Transfer verdict:

## 9. Current Verdict

`BLOCK / WARN / PASS`

- Evidence:
- Missing:
- Reviewer:
- Review date:
