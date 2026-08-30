---
title: "Content Operation Plan Template"
description: "把用户资料、事实状态、CMS 能力、两阶段站点 scope、desired state、精确 diff、串行操作、授权摘要、对账和验收写成机器可校验计划。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
created: "2026-08-12"
last_updated: "2026-08-12"
sources: ["../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md", "../SCHEMAS/content-operation-plan.schema.json", "../SCHEMAS/source-extraction.schema.json"]
related: ["source-register.md", "source-extraction.md", "tool-field-map.md", "publish-record.md", "failure-diagnosis.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "用户资料已登记并完成可追溯提取，准备通过 CMS 接口新建站点或在真实站点内新建、更新文章、产品、taxonomy、媒体或主题页面时。"
keywords: ["operation plan", "site bootstrap", "site operation", "desired state", "source refs", "CMS diff", "authorization digest"]
---
# Content Operation Plan

> 在客户私有运行区复制为 `content-operation-plan.json`。这里不保存客户事实、凭据、Cookie、Action ID、deployment/build ID 或测试站默认值。完整字段以 [Schema](../SCHEMAS/content-operation-plan.schema.json) 为准。

## 客户运行区绑定（先做）

计划和来源 artifact 都使用 schema `1.1`。先由机器生成 `runtime_scope`，不要手抄 digest：

```bash
node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>
```

`task_root` 固定为 `customer-runtime/10_clients/<client_id>/30_tasks/<task_id>`；`company_id` 不新增目录层，而是进入 `scope_digest` 和 `source_scope`。所有 source location、extraction artifact、capability/readback/frontend evidence、bootstrap readback 与 writeback path 都必须是该 `task_root/` 下的已规范化相对 POSIX 路径。绝对路径、URL、反斜线、`..`、query/fragment、percent-encoded path bytes 或另一客户/任务路径一律 BLOCK。

## 生成顺序

1. 用 [Source Register](source-register.md) 登记用户给出的 PDF、DOCX、表格、网站、图片和 brief，并计算每个原文件或网页快照的 SHA-256。
2. 按宿主能力生成并校验 [Source Extraction](source-extraction.md)；机器 artifact 同时绑定 owner、rights、method-use/publication clearance、source date、review-after、客户 scope、原始 digest、提取器/version、精确 locator、提取 digest、置信度和 warning。提取 unit 只是 claim candidate，不自动成为确认事实。
3. 把每个已校验 `source-extraction.json` 的 artifact ref、`extraction_id`、原始 `source_digest` 和可消费 units 投影进 source snapshot；再建立 claim ledger。`confirmed` 和 `inferred` 必须引用存在的 `source_id`，并用 `evidence_refs` 同时绑定 `source_digest + extraction_id + unit_id + locator + extraction_digest`；`missing/conflicting/expired` 可留在缺口账本，但不得进入 mutation。
4. 只读发现登录用户、网站列表、当前字段与 capability maturity；capability snapshot 必须有 `captured_at/expires_at` 和证据，过期即重新发现；动态 Action ID 只留在运行内存或客户私有证据。
5. 先选择计划阶段：
   - 已有真实站点：直接生成 `site_operation`；
   - 需要新建站点：先生成只含一次 `site:create` 的 `site_bootstrap`（Plan A），回读真实 `site_id/site_key/account owner` 后，再生成新的 `site_operation`（Plan B）。
6. 将用户目标写成平台无关 desired state，再和 current state 做精确 diff；upsert 必须解析成 create/update/noop。
7. 更新操作绑定 exact ID 或站点内唯一 natural key，并保存 expected-current fingerprint。未提及字段默认保持不变，清空必须显式声明。
8. operations 按真实依赖排成单链；每个 mutation 显式声明 `publication_effect`。任何公开 mutation 使用的来源都必须 `approved/not-applicable`。
9. 先生成 `authorization_scope.status=pending` 的计划，运行验证器并展示 target、操作顺序、publication effects 与摘要。
10. 用户按精确计划 SHA-256 授权后，填入 actor、时间、最长 30 分钟 expires 和同一 plan digest；**同一写入步骤必须同时落盘 `archived_at`（= `approved_at`）**——冻结即归档，验证器对 approved 计划强制 `AUTHORIZATION_ARCHIVE_REQUIRED`，缺档即 BLOCK。摘要只绑定不可变业务计划和精确 target/operation scope，不把 actor/授权时间自身纳入摘要循环；任何业务计划变化都重新授权。

## Plan B：已有或已回读真实站点的最小骨架

```json
{
  "schema_version": "1.1",
  "plan_id": "COP-<task>-<revision>",
  "plan_digest": "sha256:<validator-calculated>",
  "client_id": "<required>",
  "company_id": "<required>",
  "task_id": "<required>",
  "runtime_scope": {
    "root": "customer-runtime",
    "client_root": "customer-runtime/10_clients/<client_id>",
    "task_root": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>",
    "scope_digest": "sha256:<validator-compatible scope digest>"
  },
  "execution_mode": "audit",
  "plan_phase": "site_operation",
  "cms_adapter": {
    "id": "<runtime-selected>",
    "version": "<observed-contract-version>",
    "observed_at": "<UTC timestamp>",
    "deployment_fingerprint": "sha256:<64 hex>"
  },
  "site_selector": {
    "target_scope": "site",
    "site_key": "<exact real target>",
    "site_id": null,
    "account_user_id": null,
    "selection_source": "user-confirmed",
    "bootstrap_readback_ref": null,
    "bootstrap_plan_digest": null,
    "cross_site_fallback": false
  },
  "source_snapshot": {
    "captured_at": "<UTC timestamp>",
    "sources": [{
      "source_id": "SRC-<stable-id>",
      "kind": "docx",
      "location": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/10_sources/source.docx",
      "digest": "sha256:<original-bytes>",
      "authority": "primary",
      "owner": "<named owner>",
      "rights_status": "owned",
      "method_use_clearance": "approved",
      "source_date": null,
      "review_after": null,
      "source_scope": "<client_id>/<company_id>/<task_id>",
      "extractions": [{
        "extraction_id": "SX-<stable-id>",
        "artifact_ref": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/20_work/source-extraction.json",
        "source_digest": "sha256:<same original bytes>",
        "captured_at": "<UTC timestamp>",
        "status": "complete",
        "units": [{
          "unit_id": "UNIT-001",
          "locator": "<page/sheet/cell/paragraph/DOM/image region>",
          "extraction_digest": "sha256:<canonical extracted value>"
        }]
      }],
      "publication_clearance": "approved"
    }]
  },
  "claim_ledger": [
    {
      "claim_id": "CLAIM-<stable-id>",
      "status": "confirmed",
      "source_refs": ["SRC-<stable-id>"],
      "evidence_refs": [{
        "source_id": "SRC-<stable-id>",
        "source_digest": "sha256:<same original bytes>",
        "extraction_id": "SX-<stable-id>",
        "unit_id": "UNIT-001",
        "locator": "<source-extraction unit locator>",
        "extraction_digest": "sha256:<same extraction unit digest>"
      }],
      "value": "<source-backed value>",
      "notes": ""
    }
  ],
  "capability_snapshot": {
    "captured_at": "<UTC timestamp>",
    "expires_at": "<short-lived UTC timestamp>",
    "deployment_fingerprint": "sha256:<same deployment>",
    "capabilities": []
  },
  "desired_state": [{
    "entity_ref": "article:<stable-ref>",
    "entity_type": "article",
    "intent": "upsert",
    "identity": {
      "id": null,
      "natural_key": {
        "site_key": "<exact real target>",
        "slug": "<stable slug>"
      },
      "match_strategy": "exact_natural_key"
    },
    "fields": {
      "title": {
        "value": "<desired title>",
        "fact_status": "confirmed",
        "source_refs": ["SRC-<stable-id>"],
        "claim_refs": ["CLAIM-<stable-id>"],
        "derivation": {"mode": "direct", "notes": ""},
        "clear_existing": false
      }
    }
  }],
  "current_state_fingerprint": "sha256:<canonical current state>",
  "diff": [],
  "operations": [{
    "operation_id": "OP-001",
    "entity_ref": "article:<stable-ref>",
    "entity_type": "article",
    "intent": "create",
    "identity": {
      "id": null,
      "natural_key": {
        "site_key": "<exact real target>",
        "slug": "<stable slug>"
      },
      "match_strategy": "exact_natural_key"
    },
    "field_refs": ["title"],
    "capability_ref": "CAP-<runtime-verified>",
    "expected_current_fingerprint": null,
    "dependencies": [],
    "mutation": true,
    "publication_effect": "private_draft",
    "readback_requirements": ["record-id", "slug", "persisted-fields"]
  }],
  "authorization_scope": {
    "status": "pending",
    "actor": null,
    "identity_status": "not_verified",
    "target_scope": "site",
    "target_key": "<exact real target>",
    "operation_ids": [],
    "approved_at": null,
    "expires_at": null,
    "plan_sha256": null
  },
  "reconciliation_policy": {
    "ambiguous_write": "read-only-reconcile-before-any-retry",
    "automatic_retry_after_request_started": false,
    "identity_rule": "exact-id-or-site-scoped-natural-key"
  },
  "verification_plan": {
    "backend_readback": true,
    "editor_reopen": true,
    "frontend": true,
    "evidence_targets": []
  },
  "writeback_targets": []
}
```

### AllinCMS 只读 operation 示例

若目标 Adapter 是 AllinCMS，`noop/explore` 必须使用该 Adapter 的 `verification-evidence-contract.json#read_only_profiles`；其他 CMS 应替换成其自身机器合同，不能照抄为跨 CMS 保证。只读 operation 仍属于已批准计划，但 `mutation` 必须为 `false`、`publication_effect` 必须为 `none`、`field_refs` 必须为空：

```json
[
  {
    "operation_id": "OP-READ-001",
    "entity_ref": "article:<stable-ref>",
    "entity_type": "article",
    "intent": "noop",
    "identity": {
      "id": "<exact existing id>",
      "natural_key": {},
      "match_strategy": "exact_id"
    },
    "field_refs": [],
    "capability_ref": "CAP-<runtime-verified-read-capability>",
    "expected_current_fingerprint": null,
    "dependencies": [],
    "mutation": false,
    "publication_effect": "none",
    "readback_requirements": [
      "read_only.authoritative_noop_readback",
      "scope.exact_site_binding"
    ]
  },
  {
    "operation_id": "OP-READ-002",
    "entity_ref": "article:<discovery-ref>",
    "entity_type": "article",
    "intent": "explore",
    "identity": {
      "id": null,
      "natural_key": {
        "site_key": "<exact real target>",
        "slug": "<exact discovery key>"
      },
      "match_strategy": "exact_natural_key"
    },
    "field_refs": [],
    "capability_ref": "CAP-<runtime-verified-read-capability>",
    "expected_current_fingerprint": null,
    "dependencies": ["OP-READ-001"],
    "mutation": false,
    "publication_effect": "none",
    "readback_requirements": [
      "read_only.authoritative_exploration_readback",
      "scope.exact_site_binding"
    ]
  }
]
```

执行约束：`noop` 不调用远程 `execute()`；`explore` 最多执行当前批准的一次只读请求。两者都必须 authoritative same-site readback，且失败时不得进入 write/mutation reconciliation。只读 PASS 不证明写能力、发布能力或 mutation profile 通过。

若本真实站点来自 Plan A 回读，则把 `selection_source` 改为 `bootstrap-readback`，并同时填写：

```json
{
  "bootstrap_readback_ref": "customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/40_evidence/site-bootstrap-readback.json",
  "bootstrap_plan_digest": "sha256:<exact Plan A digest>"
}
```

## Plan A：新建站点的最小差异

Plan A 是 **account scope**，只能创建一个非公开 CMS site resource。`site_key/site_id` 必须为 `null`，未来站点身份只能先作为来源支持的 `site_key_candidate`，不得虚构真实 `site_key`。

```json
{
  "plan_phase": "site_bootstrap",
  "site_selector": {
    "target_scope": "account",
    "site_key": null,
    "site_id": null,
    "account_user_id": "<exact current signed-in user id>",
    "selection_source": "planned-create",
    "bootstrap_readback_ref": null,
    "bootstrap_plan_digest": null,
    "cross_site_fallback": false
  },
  "desired_state": [{
    "entity_ref": "site:<stable-ref>",
    "entity_type": "site",
    "intent": "create",
    "identity": {
      "id": null,
      "natural_key": {"site_key_candidate": "<source-backed candidate>"},
      "match_strategy": "exact_natural_key"
    },
    "fields": {}
  }],
  "operations": [{
    "operation_id": "OP-SITE-001",
    "entity_ref": "site:<stable-ref>",
    "entity_type": "site",
    "intent": "create",
    "identity": {
      "id": null,
      "natural_key": {"site_key_candidate": "<source-backed candidate>"},
      "match_strategy": "exact_natural_key"
    },
    "field_refs": [],
    "capability_ref": "CAP-site-create-current-deployment",
    "expected_current_fingerprint": null,
    "dependencies": [],
    "mutation": true,
    "publication_effect": "non_public_resource",
    "readback_requirements": ["site-id", "site-key", "account-owner"]
  }],
  "authorization_scope": {
    "status": "pending",
    "actor": null,
    "identity_status": "not_verified",
    "target_scope": "account",
    "target_key": "<exact current signed-in user id>",
    "operation_ids": ["OP-SITE-001"],
    "approved_at": null,
    "expires_at": null,
    "plan_sha256": null
  }
}
```

Plan A 还必须具有一一对应的单条 `diff`、当前 deployment 的未过期 capability snapshot 和私有回读目标。它不能混入分类、标签、媒体、文章、产品或主题页；回读真实站点身份后必须停止，再创建新的 Plan B、重新发现 capability/current state、计算新 digest 并获得站点 scope 授权。

## 校验

```bash
node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>
node scripts/validate-content-operation-plan.mjs customer-runtime/10_clients/<client_id>/30_tasks/<task_id>/content-operation-plan.json
```

可能输出：

- `CONTENT_OPERATION_PLAN_STRUCTURE_PASS_AUTHORIZATION_PENDING`：计划结构可审查，但不能执行；
- `CONTENT_OPERATION_PLAN_EXECUTION_READY`：本地结构和摘要授权一致，仍需在每次请求前检查授权时效、CMS session、capability expiry 和 expected-current fingerprint；
- `CONTENT_OPERATION_PLAN_BLOCK`：不得 mutation，按问题列表修复。

本地 PASS 不证明登录、远程写入、发布、前台、SEO、询盘或转化。
