---
title: "Source Extraction Template"
description: "把一份原始 PDF、DOCX、表格、网页、图片、brief 或聊天快照绑定到宿主提取能力、精确 locator、提取 digest、置信度和警告。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-08-12"
last_updated: "2026-08-12"
sources: ["../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md", "../SCHEMAS/source-extraction.schema.json"]
related: ["source-register.md", "content-operation-plan.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "用户给出文件、网页或图片，需要先提取可追溯事实候选，再生成 CMS desired state 时。"
keywords: ["source extraction", "locator", "OCR warning", "claim candidate", "source digest"]
---
# Source Extraction

> 复制到当前客户私有运行区并保存为 `source-extraction.json`。本模板只定义输出合同，不内置第二套 PDF、DOCX、表格、浏览器或视觉解析器；按宿主实际可用能力路由。

## 客户运行区绑定（先做）

使用 schema `1.1`，先运行 `node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>` 生成 `runtime_scope`。原始来源必须先复制或快照到该任务的 `task_root/` 内再登记；不能把用户电脑绝对路径、URL、另一客户目录或 `private-runtime/...` 伪前缀写成可消费证据。

## 运行原则

1. 先计算原始文件或网页快照 SHA-256，再提取；不要只对摘要计算 digest。
2. 每次只绑定一个 `source_id`；PDF 页、表格单元格、DOM selector 和图片区域分别成为 units。
3. OCR、视觉识别、动态网页和合并单元格不得假装无损；用 `confidence` 与 `warnings` 暴露不确定性。
4. 在机器 artifact 内绑定 owner、rights、method-use clearance、publication clearance、source date、review-after 和 `client/company/task` scope；不能只在另一个 Markdown 表里登记。
5. `complete/partial` 至少有一个 unit；`blocked` 不得输出可消费 unit。
6. 本文件含客户原文，只能进入 `customer-runtime/`，不得提交或发布。
7. 通过本地结构校验后，AI 仍只能生成 claim candidates；是否 `confirmed` 由来源权威性、冲突、时效和业务门禁决定。

## 最小骨架

```json
{
  "schema_version": "1.1",
  "extraction_id": "SX-<source>-<revision>",
  "client_id": "<required>",
  "company_id": "<required>",
  "task_id": "<required>",
  "runtime_scope": {
    "root": "customer-runtime",
    "client_root": "customer-runtime/10_clients/<client_id>",
    "task_root": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>",
    "scope_digest": "sha256:<validator-compatible scope digest>"
  },
  "source_id": "SRC-<stable-id>",
  "source_kind": "pdf",
  "source_location": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/10_sources/<file>",
  "source_digest": "sha256:<original-bytes>",
  "source_owner": "<named owner>",
  "rights_status": "owned",
  "method_use_clearance": "approved",
  "publication_clearance": "approved",
  "source_date": "<UTC timestamp or null>",
  "review_after": null,
  "source_scope": "<client_id>/<company_id>/<task_id>",
  "captured_at": "<UTC timestamp>",
  "extractor": {
    "capability": "pdf-read",
    "implementation": "<host-runtime>",
    "version": "<observed-version>",
    "mode": "native_text"
  },
  "status": "complete",
  "units": [{
    "unit_id": "UNIT-001",
    "locator": "page=2;paragraph=3",
    "content_kind": "text",
    "value": "<private extracted value>",
    "extraction_digest": "sha256:<canonical-unit-value>",
    "confidence": "high",
    "warnings": []
  }],
  "warnings": [],
  "visibility": "private-runtime"
}
```

## 校验

```bash
node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>
node scripts/validate-source-extraction.mjs customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/20_work/source-extraction.json
```

`SOURCE_EXTRACTION_STRUCTURE_PASS` 只证明本地合同；不证明原文正确、OCR 无误、事实已确认或允许公开。
