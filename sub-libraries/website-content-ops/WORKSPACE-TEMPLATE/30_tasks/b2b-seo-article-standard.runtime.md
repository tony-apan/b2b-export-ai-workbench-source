---
source_doc_id: "ID-0001"
title: "B2B SEO Article Standard"
description: "定义 English-only B2B SEO 文章的单一搜索任务、六节点因果链、阶段化内容/CTA/内链、证据状态、产品决策与独立质量门禁；不证明排名、询盘或转化提升。"
type: "page"
status: "Working"
owner: "AI"
created: "2026-07-31"
last_updated: "2026-08-11"
sources: ["../10_sources/index.md", "../20_knowledge/index.md", "index.md"]
related: ["index.md", "b2b-article-optimization-sop.runtime.md", "b2b-article-stage-patterns.runtime.md", "../TEMPLATES/article-brief.md", "../TEMPLATES/article-draft.md", "../TEMPLATES/article-quality-review.md", "../TEMPLATES/publish-record.md", "../40_outputs/index.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要策划、撰写、优化或审查正式英文 B2B SEO 文章，并判断其是否真正完成一个买家搜索任务时。"
keywords: ["B2B SEO", "English-only", "search intent", "buyer task", "six-node pain chain", "stage contract", "information gain", "CTA"]
generated_from: "../../PLAYBOOKS/id-0001-b2b-seo-article-standard.md"
generated_source_sha256: "be36127407b72e5e3363e1195cd3d5eb434f00183644322c874c04e9350066a1"
generated_by: "scripts/sync-workspace-template.mjs"
---
<!-- Generated runtime projection from PLAYBOOKS/id-0001-b2b-seo-article-standard.md; canonical edits belong in the core package. -->
# B2B SEO Article Standard

## 结论与版本边界

优质 B2B SEO 文章不是“关键词加长文”，而是帮助一个专业买家完成**一个主要任务**的决策页面。正式 `buyer-article + index` 必须先通过 fatal gates，再分别记录结构质量和生产证据质量；高分不能覆盖任何 BLOCK。

本版本明确为 **English-only**：

```yaml
supported_content_languages: ["en"]
target_content_language: "en"
target_market: "replace-with-market"
```

- `target_market` 与语言独立，不得再使用混合字段 `target_market_language`。
- `target_content_language != en` 时 fail closed，转人工语言审查；不得套用英文 regex、英文词数或英文 CTA 标签后声称 PASS。
- 本标准只提高任务匹配、扫读和转化路径清晰度的可能性，**不承诺实际排名、询盘量、询盘质量或转化率提升**。这些结果只能由发布后的真实数据验证。

### 当前冻结审查状态

冻结审查规则：任何候选只要任一路出现 P0/P1 或 `VERDICT=FAIL`，该候选即永久作废；不得复用其 PASS、签字、Reviewer 身份、manifest digest 或局部绿灯。修复后必须生成下一不可变候选，并由未参与上一候选审查、也未参与本轮修复的全新 Reviewer 只读审查同一冻结副本。候选状态只记录在 freeze/review evidence 中；本文只定义可复用内容合同，不证明当前候选已生成或已 PASS。

本文、SOP、四份 canonical template、配套示例与 validator 必须投影同一组 canonical 字段；不得发射同义 alias、旧枚举或 snapshot 分叉。核心枚举与证据轴为：

```yaml
stage: "learn|troubleshoot|compare|validate|buy"
intent_class: "informational|troubleshooting|commercial-investigation|mixed-commercial|transactional"
commercial_commitment: "none|soft|commercial"
dominant_search_intent: "one specific buyer search intent; exact projection across Brief/Draft/Review/Publish"
page_h1: "buyer-visible page-shell H1; exact projection across Brief/Draft/Review/Publish"
content_action: "create|update|merge|redirect|do-not-write"
content_family_matches: []
content_family_singleton_verdict: "pass|block"
secondary_intent_contracts: ["supporting-query | buyer-task | exact canonical stage | exact canonical commercial commitment | owner page or this-article | supports or delegated"]
evidence_origin: "synthetic-fixture|test-fixture|live-production"
fixture_identity: "concrete fixture ID or not-applicable"
production_proof_eligible: false
customer_language_status: "missing|inferred|confirmed"
customer_language_refs: []
customer_language_gate_verdict: "pass|block"
pain_evidence_status: "missing|inferred|confirmed"
pain_evidence_refs: []
pain_evidence_gate_verdict: "pass|block"
dominant_task_contract: "action | object | observable output | stage | commercial commitment"
terminal_action_contract: "action|object|observable-output|stage|commercial-commitment"
first_round_expected_output: "packet completeness, missing-evidence list, and next review step"
candidate_decision_required_gates: ["complete-second-round-package|not-applicable", "named-technical-owner-review|not-applicable"]
first_round_output_candidate_gate_verdict: "pass|block|not-applicable"
pain_chain_contract: "actor | operating-event | evidence-gap | rework-mechanism | program-consequence | bounded-decision"
direct_answer_action: "..."
direct_answer_object: "..."
direct_answer_required_inputs_or_evidence: "..."
direct_answer_condition_or_boundary: "..."
direct_answer_expected_output_or_route: "..."
direct_answer_evidence_boundary: "..."
cta_interaction_type: "inline-no-input|local-tool|input-collecting|human-handoff|commercial"
stage_intake_contract: "none|troubleshoot-support|compare-handoff|validate-technical|buy-commercial"
cta_from_role: "originating role or not-applicable"
cta_to_role: "receiving role or not-applicable"
cta_receiving_task: "receiving task or not-applicable"
cta_receiving_owner: "named buyer-side receiving owner or not-applicable"
cta_input_collection_applicability: "applicable|not-applicable"
cta_input_collection_not_applicable_reason: "required when not-applicable"
stage_link_requirement_status: "applicable|not-applicable"
stage_link_not_applicable_reason: "required when not-applicable"
first_round_inquiry_inputs: []
second_round_inquiry_inputs: []
second_round_input_relationships: []
cta_required_inputs: []
first_round_input_specifications: []
cta_buyer_visible_capability_proofs: []
qualification_reason_codes: ["state | cause-category | evidence-rule | owner | next-step"]
buyer_task_evidence_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
buyer_task_evidence_refs: []
buyer_task_evidence_gate_verdict: "pass|block"
query_evidence_status: "missing|inferred|confirmed"
query_evidence_refs: []
query_evidence_gate_verdict: "pass|block"
buyer_language_seeds: []
query_language_transformation_reason: "why buyer wording is preserved or normalized into the target query"
search_demand_evidence_status: "missing|inferred|confirmed"
search_demand_evidence_refs: []
search_demand_evidence_gate_verdict: "pass|block"
search_demand_evidence_schema: "exact query set | source/platform | market | language | device | observation_start_at | observation_end_at | metric type | observed value per query | brand/non-brand boundary | zero/low-demand decision | seasonality/trend note | analyst conclusion | independent reviewer | snapshot ref | digest"
serp_format_evidence_status: "missing|inferred|confirmed"
serp_format_evidence_refs: []
serp_format_evidence_gate_verdict: "pass|block"
serp_primary_query: "exact primary_query"
serp_primary_query_sample_size: 0
serp_primary_query_result_type_counts: ["result-type|count"]
serp_primary_query_dominant_result_type: "replace-with-supported-content-family"
serp_primary_query_dominant_result_count: 0
serp_primary_query_dominance_threshold: "predeclared ratio greater than 0.50"
serp_primary_query_dominance_verdict: "pass|block"
serp_supporting_query_result_type_rows: []
market_information_gain_status: "missing|inferred|confirmed|not-applicable"
information_gain_market_refs: []
information_gain_artifact_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
information_gain_artifact_refs: []
secondary_buyer_role_contracts: []
role_handoff_contracts: []
internal_link_role: "hub|product|solution|educational|comparison|diagnostic|support|technical-review|conversion|commercial"
product_link_evidence_level: "none|family-level|sku-level"
cta_value_exchange: "what the buyer receives"
cta_response_expectation: "verified timing or an explicit unknown boundary"
cta_submission_method: "accepted channel or file method"
cta_confidentiality_or_data_boundary: "what not to submit and approved secure-channel boundary"
cta_commitment_boundary: "what the action does and does not commit the buyer to"
cta_buyer_visible_owner: "buyer-facing responsible team or role"
buyer_visible_cta_inventory: ["surface-id | location-kind | locator | instruction | destination | owner | interaction-type | route-status | evidence-bundle-ref | fallback-contract-ref"]
cta_route_evidence_bundles: ["route-id | endpoint | evidence_kind | check_id | task | owner | process | observed_result | capability_acceptance | reference-status | reachability-status | capability-status | evidence_ref"]
cta_collection_route_policy_contracts: ["route-id | endpoint | required-inputs-mode | data-purpose | retention-period | deletion-path | retention-owner | policy-contract-id | policy-status | policy-owner-acceptance | policy-evidence-refs | deletion-capability-evidence-refs"]
local_preparation_purpose: "buyer-local preparation purpose"
supplier_side_collection_purpose: "not-applicable until every route and policy gate passes"
cta_collection_send_gate_verdict: "pass|block|not-applicable"
section_information_gain_verdict: "pass|block"
normalized_field_set_redundancy_verdict: "pass|block"
article_decision_sequence_map: ["hook | diagnose | decide | de-risk | act"]
article_decision_sequence_verdict: "pass|block"
conversion_surface_map: ["primary | soft | fallback"]
conversion_surface_map_verdict: "pass|block"
visual_decision_assets: ["asset_type | buyer_task_supported | claim_supported | evidence_ref | placement_after_section | caption | alt_intent | mobile_readability_requirement | status"]
mobile_visual_check_execution_status: "not-run|executed|not-applicable"
mobile_visual_evidence_result: "missing|confirmed|failed|not-applicable"
mobile_visual_gate_verdict: "pass|block|not-applicable"
mobile_visual_evidence_refs: []
production_readiness_scope: "cms-draft-content-contract"
frontend_deferred_blocks: []
inventory_zero_result_evidence_refs: []
```

Applicable first-round input row grammar:

```text
input | why-needed | accepted-unit-or-format | example | required-or-conditional | confidentiality-boundary
```

Buyer-visible CTA proof row grammar:

```text
proof-type | buyer-task-supported | claim-or-boundary | evidence-ref | buyer-visible-copy | required-or-not-applicable
```

For `input-collecting|human-handoff|commercial`, at least one task-specific buyer-visible proof is required and must be visible near the CTA. Acceptable proof types include review method, redacted sample output, test capability, sourced case/certification, or an explicit capability boundary. Generic brand language cannot satisfy this contract.

Canonical template、example、validator 与 workspace projection 必须逐字符使用以上枚举，不得用展示文案替代机器值。以下均为兼容性 BLOCK：

- `commercial_commitment: none-or-commercial`；
- `cta_interaction_type: self-serve-or-human-handoff`；
- 任何遗漏 `mixed-commercial` 的 intent vocabulary；
- 把 `technical-review`、`sample-request`、`rfq`、`supplier-selection`、`purchase-order`、`contract-award` 等 action、CTA、output、link role 或 workflow state 写进 `commercial_commitment`；
- 使用 retired aliases `qualification_rows`、`cta_first_round_inputs`、`cta_complete_technical_inputs`、`cta_second_round_rows` 或 `second_round_rows`；
- 在任何 verdict 中使用 `PASS|BLOCK|WARN|pass-for-fixture-structure|block-for-production` 等 alias。所有 verdict 只允许 closed enum `pass|block|not-applicable`；其中 `not-applicable` 仅用于标准明确允许且有非空理由的字段。fixture/production readiness 必须由独立 `evidence_scope`、evidence result、fatal gate、`production_readiness` 和 release 字段表达，不得在 verdict 发明第四状态。

不得通过 alias mapping、默认值或 validator 宽容分支把旧值静默转换成 canonical PASS。

三层真源不得混写：

1. 本页：正文、买家决策、证据与编辑质量；
2. 目标 CMS Adapter：字段、持久化格式、发布生命周期和已验证组件。

## 1. Query 与 dominant buyer task 合同

### 1.1 必填 query contract

Brief 必须记录：

```yaml
primary_query: "one real search trigger"
supporting_query_variants: ["same-task close variant"]
excluded_query_modifiers: ["buy", "price", "quote", "supplier", "MOQ", "lead time", "purchase", "RFQ"]
intent_class: "informational|troubleshooting|commercial-investigation|mixed-commercial|transactional"
stage: "learn|troubleshoot|compare|validate|buy"
expected_content_type: "serp-aligned page type"
buyer_task_evidence_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
buyer_task_evidence_refs: []
query_evidence_status: "missing|inferred|confirmed"
query_evidence_refs: []
search_demand_evidence_status: "missing|inferred|confirmed"
search_demand_evidence_refs: []
serp_format_evidence_status: "missing|inferred|confirmed"
serp_format_evidence_refs: []
```

`buyer_task_evidence_*` 与 `query_evidence_*` 是两条独立轴：

- buyer-task evidence 证明某类买家确有该 operating decision/task，可来自 dated CRM、访谈、support、sales 或产品研究；
- query evidence 证明某个真实搜索触发词对应该 task，不得由客户聊天、AI 推断、persona 或 token overlap 替代；
- search-demand evidence 证明该 query 在目标 market/language 范围内有可复核需求信号；
- SERP-format evidence 证明当前结果页的主导 intent 与适合的页面形式。

Production SERP-format evidence 必须使用一个**独立、fragment-bound 的结构化 evidence fragment**。四个 canonical record 的 frontmatter 只保留 flat scalar/array 字段，并通过 `serp_format_evidence_refs` 指向该 fragment；当前 frontmatter parser 不支持 nested mapping，禁止在 Brief、Draft、Review、Publish Record 或 evidence card frontmatter 中嵌入对象。独立 fragment 的正文 schema 固定为：

```yaml
query_set: ["exact primary query", "every exact supporting variant"]
primary_query: "exact primary query; supporting query cannot occupy this field"
market: "exact target_market"
language: "exact target_content_language"
device: "the one shared device used by every query row"
checked_at: "actual YYYY-MM-DD review date"
primary_query_sample_size: 0
primary_query_result_type_counts: ["supported-family|count"]
primary_query_dominant_result_type: "checklist|comparison|calculator|diagnostic|guide|case-study|product-landing"
primary_query_dominant_result_count: 0
primary_query_dominance_threshold: "predeclared ratio greater than 0.50"
primary_query_dominance_verdict: "pass|block"
supporting_query_result_type_rows: ["exact-query|sample-size|dominant-result-type|dominant-result-count|threshold|verdict|fragment-bound-evidence-ref"]
```

`query_set` 必须与 `[primary_query, ...supporting_query_variants]` 集合完全相等，不得缺失、重复或额外加入 query；`market`、`language` 必须逐字符等于文章目标字段，`device` 必须等于全部 query rows 的唯一 shared device。`checked_at` 必须为实际检查日期。Production 的 primary query 样本必须至少包含 5 个 eligible organic results；`primary_query_dominance_threshold` 必须在观察前冻结、严格大于 0.50，`primary_query_dominant_result_count` 必须等于该 result type family 的实际计数并达到 `ceil(sample_size × threshold)`。并列第一、样本不足、计数和 sample size 对不上、阈值事后调整或 `primary_query_dominance_verdict=block` 均为 fatal BLOCK。supporting query 只记录旁证和边界，不能通过 pooled result types、多数 supporting queries 或任意一个 supporting query 替代 primary query 的 dominant result type。`serp_format_evidence_refs` 必须 fragment-bound；generic SERP paragraph、query-family 总结、不同 market/language/device 的拼接证据或 synthetic fragment 均不能确认 Production SERP-format evidence。

四记录必须把独立 fragment exact projection 为 `serp_primary_query`、`serp_primary_query_sample_size`、`serp_primary_query_result_type_counts`、`serp_primary_query_dominant_result_type`、`serp_primary_query_dominant_result_count`、`serp_primary_query_dominance_threshold`、`serp_primary_query_dominance_verdict` 与 `serp_supporting_query_result_type_rows`；`serp_primary_query` 必须逐字符等于 `primary_query`。每个 supporting query 必须恰有一行和一个 fragment-bound evidence ref；对应 fragment 必须保存 exact query、market、language、shared device、checked_at、raw `result_types`、sample size、dominant family/count、预冻结 threshold 与 verdict。每个 supporting sample 至少 5 条，threshold 必须严格大于 0.50，dominant count 必须由 raw result types 重算并达到 strict majority；缺行、重复、额外 query、scope 漂移、伪造 dominant family/count、`block` verdict 或四记录投影漂移均为 fatal BLOCK。`serp_primary_query_result_type_counts` 是 `result-type|count` 数组，所有 count 必须为非负整数且总和等于 sample size；validator 必须由该数组独立重算 dominant type 与 dominant count，不能信任自报 dominant 字段。未执行或 synthetic fixture 四记录统一使用 `[] + not-run`，且 production search evidence gate 保持 `block`。此时 `serp_content_type_parity_verdict` 必须为 `not-applicable`，不得用自报 content family 冒充真实 SERP parity；只有 Production 且 dated primary-query SERP evidence 完整时才允许 `pass`。正文是否实现声明形态使用独立 `body_content_family_implementation_verdict: pass|block`，由 Review/Publish exact projection 并从 publishable body 重算。字段缺失、alias（例如 `dominant_family`）、值漂移、不能重算或未消费均为 fatal BLOCK。

### 1.2 SERP result type 到正文形态的 fatal 闭环

`expected_content_type` 不是描述性标签，必须形成以下可审计链路：

```text
Primary-query sample size + dominant result type/count/predeclared threshold/verdict
→ Brief/Draft exact SERP projection + expected_content_type exact parity
→ Draft observable content shape
→ Review expected_content_type_snapshot + serp_content_type_parity_verdict
→ Publish expected_content_type_snapshot + exact dominant-result projection + verdict
```

Production 必须从 `serp_format_evidence_refs` 的 `result_types` 推导页面形态；不得把 comparison、calculator、diagnostic、checklist 或 case study 的主导结果页统一改写成 generic long-form guide。Draft 必须出现相应可观察结构，例如 checklist 的可操作清单/表格、comparison 的共同维度矩阵、calculator 的输入/公式/输出、diagnostic 的症状/分支/stop、how-to 的有序步骤、case study 的问题/做法/有来源结果。无法映射、Brief/Draft 漂移、正文没有实现声明形态、Review/Publish snapshot 漂移或 `serp_content_type_parity_verdict=block` 均为 fatal BLOCK。

Synthetic fixture 只能证明“声明形态已在正文实现”，不能把该结构 PASS 冒充真实 SERP observation；其 production SERP-format evidence gate 继续 BLOCK。

`expected_content_type` 必须只命中一个 supported content family：`checklist|comparison|calculator|diagnostic|guide|case-study|product-landing`。判定时必须收集**全部** family matches，而不是按 pattern 顺序返回第一个结果；`0` 个或 `>1` 个 match 都是 fatal BLOCK，并在问题中列出全部命中的 family。`checklist plus product landing page`、`comparison guide and calculator` 等混合声明不能靠四记录逐字一致获得 PASS。Production 的 primary-query dominant family、Brief/Draft 声明 family、正文 observable family、Review/Publish snapshot 必须分别为 exact singleton 且完全相等。

Production query evidence 必须按**精确 query 一行**记录；canonical row header 与字段顺序只能是：

```text
query|action|object|observable-output|stage|commercial-commitment|market|language|device|checked_at|evidence_ref
```

集合、计数与绑定合同：

1. row 的 query 集合必须与 `{primary_query} ∪ supporting_query_variants` 完全相等；`row_count = 1 + supporting_query_variants.length`，每个 exact query 恰好一行，不得缺失、合并或重复；
2. primary query 和每个 supporting variant 都必须有自己的 dated row；generic query-family paragraph、一个“代表性 query”或一个泛化 SERP 链接不能覆盖其他 variants；
3. 所有 row 必须使用相同 target `market`、`language`、`device`，`checked_at` 必须为实际检查日期；
4. 每行 `action`、`object`、`observable-output` 必须逐槽绑定 `dominant_task_contract` 的前三槽，`stage` 与 `commercial-commitment` 必须分别等于文章 canonical 字段和 dominant-task 后两槽；
5. 每行 `evidence_ref` 必须非空并精确指向包含该 exact query row 的 dated evidence fragment；`query_evidence_refs` 必须覆盖这些 row fragments；
6. Buyer-task evidence confirmed 不能令 query evidence 自动 confirmed，query evidence 也不能替代真实 buyer-task evidence。

不再使用松散的 `primary_query_cluster`。每个 supporting variant 还必须与 `intent_class` 和 expected content type 一致，不含由其他 owner page 承担的 excluded modifier。低置信语义匹配必须转人工 Reviewer，不得用 token overlap 冒充真实意图理解。

以下是明确的**不接受**反例，任一出现即 Production query evidence BLOCK：

- row 缺 `action`、`object` 或 `observable-output` 任一槽；
- `supporting_query_variants` 中任一 exact variant 没有独立 dated row；
- variant 的 `stage` 或 `commercial-commitment` 与 primary query、canonical article fields 或 `dominant_task_contract` 漂移；
- 只因关键词/token overlap 就声称同一搜索意图，没有 query-to-task 语义证据与人工复核。

以下 transactional modifiers 是强商业触发词：`buy / price / quote / supplier / MOQ / lead time / purchase / RFQ`。Primary query 或 supporting variant 出现任一触发词时，默认进入 `transactional` 或 `mixed-commercial` route，并由 Buy owner page 承接商业任务；不得把它包装成纯 Validate 查询。若仍列入 `excluded_query_modifiers`，必须逐项记录：

```text
modifier | exclusion reason | dated SERP or first-party evidence ref | owner page | owner task | checked_at
```

只有可复核证据表明该 modifier 在当前 market/language/device 下不是 dominant intent，且另一 owner page 已明确承接其商业任务时，才允许排除。缺证据、缺 owner page、目标页未接受任务或语义混合无法拆分时 fail closed。

### 1.3 dominant buyer task 固定 grammar

```yaml
dominant_task_contract: "action | object | observable output | stage | commercial commitment"
```

其中：

- `action`：买家读完后执行的单一动作；
- `object`：动作作用的具体对象；
- `observable output`：可检查的完成结果；
- `stage`：只允许 `learn / troubleshoot / compare / validate / buy`，且必须等于 front matter 的 `stage`；
- `commercial commitment`：只允许 `none / soft / commercial`，且必须等于 front matter 的 `commercial_commitment`。

`dominant_search_intent` 是 primary query 背后的单一买家意图陈述，不是关键词列表、SERP family 或 supporting-query 汇总。Brief、Draft、Review、Publish Record 必须逐字符 exact projection；它必须与 `primary_query`、`dominant_task_contract`、`stage`、`commercial_commitment` 和终点 action 同时一致。字段缺失、snapshot alias、supporting intent 覆盖 dominant intent 或任一记录漂移都立即 BLOCK。

一页不得同时拥有两个以上主任务。Secondary question 只能支持主任务；相邻任务通过明确内链或 delegation 交给 owner page。

正文最后一个 buyer-visible action 还必须投影独立的 terminal-action contract：

```yaml
terminal_action_contract: "action|object|observable-output|stage|commercial-commitment"
```

它必须在 Brief、Draft、Review、Publish Record 中逐字符 exact projection，并与 `dominant_task_contract`、`article_decision_sequence_map` 的 `act` row、最终 buyer-visible 本地动作和 `stage`/`commercial_commitment` 同时一致。`terminal_action_contract` 只描述文章在当前页面可完成的终点，不得混入“请求 verified route”之类 fallback/delegated route recovery；fallback 必须单独进入 `cta_fallback_route_contract`、CTA inventory 和 route/policy gates。所有非商业 stage（Learn、Troubleshoot、Compare、Validate）都必须保持非商业 terminal action：不得以 `nominate / appoint / award / select a manufacturing partner / choose a preferred source / request a quote / RFQ / order` 或标点、零宽字符拆分后的同义表达作为终点。出现商业终点时必须重分类为 Buy、交给明确 owner page，或 BLOCK；不得仅靠 `commercial_commitment: none` 自报消除矛盾。四记录任一缺字段、字面漂移、Act row 混入 fallback request，或 fallback request 反向改写 terminal action，均为 fatal BLOCK。

CTA measurement 也是文章合同，不是发布后的可选补记。Brief、Draft、Review、Publish Record 必须逐字符 exact projection `cta_measurement_map`、`conversion_measurement_plan_status`、`measurement_window`、`cta_abandonment_measurement_status`、`cta_abandonment_measurement_refs` 与 `cta_measurement_plan_verdict`。`cta_measurement_map` 固定三行 `primary / soft / fallback`，每行使用：

```text
surface-id|surface-role|page-version|cta-version|start-event|submit-event|success-event|failure-event|abandonment-definition|qualification-event|commercial-acceptance-event|data-source|baseline-window|observation-window|accountable-owner|evidence-refs
```

存在适用 conversion surface 时，measurement plan 只能是 `planned|active`，不得写 `not-applicable`；surface ID、CTA version 和全部生命周期 event 必须稳定且不得跨 surface/slot 复用。`conversion_surface_map` 固定六槽 `surface-id|role|outcome|location-or-locator|interaction|route-id-or-not-applicable`，并与 `buyer_visible_cta_inventory` 的 surface ID、locator、interaction 一一绑定；`cta_measurement_map` 再与同一 surface ID、role 和 inventory owner 一一绑定。只有 Validate + `validate-technical` 的 primary row 可声明 technical-qualified event；只有 Buy + `buy-commercial` 且商业输入、acceptance requirement 和 named commercial owner 均成立时，primary row 才可声明 sales-accepted event；其他 row 必须 `not-applicable`。page version、baseline、观察窗口、数据源、owner 与本地 evidence refs 均必填。measurement-plan evidence 必须逐行记录当前 row bytes 的 `measurement_row_sha256`，且 exact set 不得 stale、missing、duplicate 或 ghost。Synthetic fixture 可以保留 `planned` 与 `not-run-no-production-baseline`，但结构 PASS 只证明合同路径，不代表真实 analytics、排名、询盘、转化或收入结果。

### 1.4 Intent completion

Brief、Draft、Review、Publish Record 必须逐字符 exact projection：

```yaml
secondary_intent_contracts: ["supporting-query|buyer-task|stage|commercial-commitment|owner-page-or-this-article|supports-or-delegated"]
in_scope_questions: []
out_of_scope_questions: []
intent_completion_test: "observable completion test"
```

`secondary_intent_contracts` 必须与 `supporting_query_variants` 一一对应且无多余 row，并逐行执行六槽语义合同：第三槽必须逐字符等于本包 canonical `stage`；第四槽只能取 `none|soft|commercial` 且必须逐字符等于本包 `commercial_commitment`；第六槽为 `supports` 时第五槽必须是 `this-article`，第六槽为 `delegated` 时第五槽必须是非 `this-article`、且不同于当前 owner 的明确 owner page。supporting query 与 buyer task 必须在 action/object/output 上支持 `dominant_search_intent` 与 `dominant_task_contract`，不能替换、汇总、扩大或污染 dominant intent。非 Buy 记录不得借 secondary row 扩张为 quote、RFQ、order、supplier award 等 terminal commercial action。in/out scope 不只检查字符串完全相同，还必须检查规范化文本、同义任务、同阶段替代表达和隐含商业承诺；同一问题不得同时进入 in/out scope。Brief、Draft、Review、Publish 必须 exact projection 并消费这些语义；无法证明边界时先 BLOCK，不继续写作。

### 1.4A First-round output 与 candidate decision gate

Brief、Draft、Review、Publish Record 必须逐字符 exact projection：

```yaml
first_round_expected_output: "packet completeness, missing-evidence list, and next review step"
candidate_decision_required_gates: ["complete-second-round-package|not-applicable", "named-technical-owner-review|not-applicable"]
first_round_output_candidate_gate_verdict: "pass|block|not-applicable"
```

规则：

1. `stage_intake_contract: validate-technical` 时，首轮唯一合法输出是 **packet completeness + missing-evidence list + next review step**。它只能说明现有输入是否齐全、缺什么证据、下一轮由谁补什么；不得输出、暗示或命名 `candidate-or-stop`、candidate approval、technical-qualified、supplier selection 或任何等价终态。
2. Validate 的 `candidate_decision_required_gates` 必须逐字符为 `complete-second-round-package` 与 `named-technical-owner-review`。只有第二轮字段全集完成、relationship rows 闭合，并由 front matter 中可识别的 named technical owner 实际复核后，才允许输出 `candidate-or-stop`；两门任一未满足都只能保持 follow-up/BLOCK。
3. 非 `validate-technical` 分支把 `first_round_expected_output` 与两个 gate item 明确投影为 `not-applicable`，不得借此复用 Validate 两轮 lifecycle；其 stage-specific output 仍由 dominant/terminal action 合同约束。
4. `first_round_output_candidate_gate_verdict` 是 fatal verdict：字段缺失、四记录字面漂移、首轮提前给 candidate、第二轮不完整、named owner 缺失/未复核或用岗位名冒充人员身份，均必须为 `block`，并联动 `fatal_gate_verdict`、`overall_verdict` 与 `production_readiness` 为 BLOCK。

### 1.5 Title / H1 / hierarchy 语义门禁

Title 与 H1 必须帮助同一个买家完成同一个 dominant task，而不是只包含 primary query token。H1 使用独立 page-shell 机器真值，不得把 `working_article_title`、`article_title` 或 `published_article_title` 同时冒充 H1。Brief、Draft、Review、Publish Record 必须逐字符 exact projection：

```yaml
page_h1: "buyer-visible page-shell H1"
```

Draft 的 publishable body 不重复内嵌 H1；页面壳只从 `page_h1` 渲染一个 H1。Publish Record 正文的 `Proposed search fields` 表必须把 `SEO title / Meta description / H1 / Excerpt` 分别与 frontmatter 的 `published_article_title / published_meta_description / page_h1 / published_excerpt` 逐字符对齐；任一字段出现第二套值或漂移即 BLOCK。Production review 至少记录并消费：

```yaml
title_primary_query_parity_verdict: "pass|block"
title_dominant_task_parity_verdict: "pass|block"
title_stage_parity_verdict: "pass|block"
h1_title_task_parity_verdict: "pass|block"
hierarchy_scan_verdict: "pass|block"
```

要求：

1. Title 与 H1 都必须与 `primary_query` 的真实主题/对象语义一致；只有 token overlap、同义词堆叠或 keyword word salad 不构成 PASS；
2. Title 与 H1 必须表达或清楚承接 `dominant_task_contract` 的 action、object 与 observable output，不得把 Learn 写成选择供应商、把 Validate 写成报价页，或把 Buy 写成纯教育页；
3. Title、H1、intent class、stage 与 commercial commitment 必须互相一致；任何 competing stage 都必须 BLOCK；
4. `stage != buy` 时，Title/H1 禁止 `buy / price / quote / supplier / MOQ / lead time / purchase / RFQ` 等 transactional modifier，除非先按证据重分类为 Buy 或建立明确 owner-page delegation，不能靠 excluded list 静默放行；
5. `H1` 合同指 **page-shell title metadata**，不是 publishable body 内的 Markdown H1；page shell 必须且只能渲染一次 H1，Brief/Draft/Review 只审它与 title/query/task/stage 的 metadata parity。publishable body 一律禁止 `# H1`，正文从 H2 开始；
6. `hierarchy_scan_verdict: block` 必须进入 fatal gate，并令 `fatal_gate_verdict: block` 与 overall verdict 为 `block`；validator 不得只生成该 verdict 而不消费它。

以上语义门禁必须人工复核；token overlap、字符相似度或标题长度只能做辅助信号。

## 2. Stage-specific article / CTA / link / sales contract

每篇文章还必须保存两张 canonical map，并由 Review/Publish exact projection：

```yaml
article_decision_sequence_map:
  - "hook|buyer-visible failure or trigger|opening"
  - "diagnose|cause/evidence gap and why it matters|diagnosis section"
  - "decide|bounded decision permitted by the current evidence gates|decision section"
  - "de-risk|assumptions, no-fit, proof and validation boundary|risk section"
  - "act|one bounded next action and expected output|final action section"
article_decision_sequence_verdict: "pass|block"
conversion_surface_map:
  - "primary|main stage outcome|location|interaction|route-id-or-not-applicable"
  - "soft|lower-friction preparation or self-check|location|interaction|route-id-or-not-applicable"
  - "fallback|safe no-send route recovery|location|interaction|route-id-or-not-applicable"
conversion_surface_map_verdict: "pass|block"
```

五段必须按 `Hook → Diagnose → Decide → De-risk → Act` 顺序出现并完成同一个 dominant buyer task；可以合并相邻 section，但不得调序、漏段或把 Act 提前成无证据销售动作。三类 conversion surface 必须显式列出；不适用时写 `not-applicable` 与阶段理由，不能静默缺失。两项 verdict 都是 fatal verdict。

Canonical CTA/link/intake fields：

```yaml
cta_interaction_type: "inline-no-input|local-tool|input-collecting|human-handoff|commercial"
stage_intake_contract: "none|troubleshoot-support|compare-handoff|validate-technical|buy-commercial"
cta_input_collection_applicability: "applicable|not-applicable"
cta_input_collection_not_applicable_reason: "required only when not-applicable"
stage_link_requirement_status: "applicable|not-applicable"
stage_link_not_applicable_reason: "required only when not-applicable"
```

| Stage | Intent class | Dominant task/output | Default CTA | `stage_intake_contract` | Intake / qualification boundary | Commercial commitment |
|---|---|---|---|---|---|---|
| Learn | `informational` | 理解边界并完成 self-check/education output | `inline-no-input` | `none` | 默认不收资、不 qualification；阅读、下载或完成 self-check 不能被算作 lead qualification | `none` |
| Troubleshoot | `troubleshooting` | 完成诊断分支并得到 recovery/support-ready output | `local-tool`；需要人工支持时 `human-handoff` | 本地闭环为 `none`；真实 support handoff 才为 `troubleshoot-support` | 只收复现、环境、症状、已尝试步骤和安全边界等当前诊断必需输入；不得继承 Validate 的两轮技术 qualification，也不等于 sales acceptance | `none` |
| Compare | `commercial-investigation`；有证据的商业桥才 `mixed-commercial` | 用共同维度形成 comparison/shortlist/stop | `local-tool` 或 `inline-no-input` | 默认 `none`；只有证据化 `mixed-commercial` handoff 才为 `compare-handoff` | 默认不收资；handoff 只收完成该比较/商业桥所需的最小字段，不启动 technical-qualified lifecycle | 默认 `none`；证据化 mixed-commercial bridge 才可 `soft` |
| Validate | `commercial-investigation` | 首轮形成 packet completeness、missing-evidence list 与 next review step；仅在完整第二轮 + named technical-owner review 后形成 candidate-or-stop | `human-handoff` 或 `input-collecting` | `validate-technical` | **只有该合同**使用两轮 technical progressive profiling；首轮不得输出 candidate-or-stop，且 named technical owner 接受只形成技术决策，不产生 sales acceptance/RFQ/order/supplier-award | `none` |
| Buy | `transactional` 或证据化 `mixed-commercial` | 形成 RFQ/报价/样品/采购 qualification packet | `commercial` | `buy-commercial` | 使用独立 RFQ/commercial packet：显式商业意图、数量/MOQ、目标市场、时间窗口、交付/贸易条件和必要技术输入；由 named commercial owner 判断，不继承 `validate-technical`、两轮技术 intake 或 `technical-qualified` lifecycle | `commercial`；低承诺商业入口可 `soft` |

Stage/intake 映射规则：

- `stage_intake_contract: none` 必须对应 `cta_input_collection_applicability: not-applicable`，理由必填，且不得发射 intake packet、qualification rows 或占位表单；
- 无论 stage，任何 buyer-visible `submit / send / email / upload / share / transmit / proceed` 或同义传递动作，都必须同时绑定已通过 reference、reachability、capability、data-policy、retention、deletion 与 owner acceptance 的同一 endpoint。任一 route/policy gate 为 BLOCK 时，只能让买家把 packet 保存在本地并单独请求 verified route 与 policy details；不得显示可点击 endpoint，不得把 fallback request 混入 `terminal_action_contract`；
- `troubleshoot-support` 只允许 Troubleshoot + 真实 support destination；`compare-handoff` 只允许有 dated query/SERP/first-party evidence 的 Compare + `mixed-commercial`；`validate-technical` 只允许 Validate，且首轮输出固定为 packet completeness、missing evidence 与 next review step；`buy-commercial` 只允许 Buy；
- `cta_input_collection_applicability: applicable` 不再自动等于 progressive profiling、technical owner、technical-qualified 或 sales gate；具体字段、owner、route 与状态完全由 `stage_intake_contract` 决定；Validate 首轮完成也只能生成 completeness/missing-evidence/next-step，不得提前生成 candidate-or-stop；
- Troubleshoot 和 Compare intake 不得重复索取与当前诊断/比较无关的完整 RFQ 或技术验证字段；Buy 可收必要技术输入，但必须作为 commercial packet 的明确组成，不得借此推导 technical-qualified；
- `stage_link_requirement_status` 只控制 stage-link 的 role、target URL、owner 与 reachability/capability/acceptance evidence；`not-applicable` 时理由必填，不得为了数量配额添加无用链接；
- `role_handoff_contracts` 独立于 intake：CTA 或 stage link 形成真实跨角色 delegation 时必须有 handoff row；无跨角色 target 时必须为空；
- CTA 跨角色时，`cta_from_role`、`cta_to_role`、`cta_receiving_task`、`cta_receiving_owner` 与唯一 handoff row 必须逐字符一致；`cta_receiving_owner` 表示买方接收任务的 owner，`cta_owner` 表示外部 CTA route 的 accountable output owner，Buy commercial route 不得把两者混成同一字段或同一责任；不跨角色时四者必须为精确 sentinel `not-applicable`；
- `cta_interaction_type` 描述交互，不等于 commercial commitment。Learn/Troubleshoot 不得改写成 RFQ 页面；Compare 不能因 shortlist 自动进入 sales qualification；Validate 不能偷渡商业状态；Buy 不能复用 technical-qualified 作为 sales acceptance；
- Stage、intent、CTA、intake、link、qualification、delegation、owner 与 commitment 任一冲突均 fail closed。

## 3. 六节点 Buyer Pain-to-Decision 因果链

Canonical 可机械投影字段为：

```yaml
pain_chain_contract: "actor | operating-event | evidence-gap | rework-mechanism | program-consequence | bounded-decision"
```

这是固定的**六槽位因果链**；`actor` 是第一槽并参与链路判断，不得再称为“五节点”或从 verdict 中排除。六槽位依次为 `actor → operating-event → evidence-gap → rework-mechanism → program-consequence → bounded-decision`，每个槽位必须具体且能与前后节点形成因果关系：

1. `actor`：承担判断、返工或后果的具体 buyer/operating role；
2. `operating-event`：触发判断的真实工作事件与对象；
3. `evidence-gap`：阻止判断的缺失证据，而非泛称“信息不足”；
4. `rework-mechanism`：缺口如何导致复测、追问、返工、升级或等待；
5. `program-consequence`：有边界的项目/采购/验证后果；
6. `bounded-decision`：读者可在本文范围内完成的决定或 stop condition。

当 pain、原因或后果仅为 `inferred` 或 `synthetic` 时，买家可见正文只能使用 `may / can / risks` 等有边界措辞；`creates / causes / will / suppliers do` 等无来源确定性陈述必须降级或删除。不得编造停线成本、返工比例、ROI、供应商行为或客户原话。以下直接 BLOCK：槽位只是同义改写、actor 与后果不匹配、rework mechanism 不可观察、program consequence 写成无证据确定性损失，或 bounded decision 超出 dominant task。

控制记录必须另有一组**机器可读、标签稳定、顺序固定**的六行投影，用于把自然 buyer-facing prose 映射回 canonical chain；推荐 row grammar：

```yaml
visible_pain_chain:
  - "Actor|specific buyer or operating role"
  - "Trigger|specific operating event and object"
  - "Evidence gap|missing decision evidence"
  - "Rework|observable clarification, retest, rebuild or wait mechanism"
  - "Consequence|bounded program, procurement or validation consequence"
  - "Decision|bounded decision or stop condition owned by this article"
visible_pain_chain_sequence_verdict: "pass|block"
```

六个机器槽位必须各有一个非空值，并在四记录的 `visible_pain_chain` 中保留稳定标签与固定顺序；这些标签是 audit/control projection，**不得原样泄漏到 buyer-visible 正文**。正文应在一个专用 H2 下使用恰好六条连续编号自然语言，依次表达 actor、trigger、evidence gap、rework、consequence、decision，但不显示 `Actor:`、`Trigger:` 等内部标签。每条自然语言必须唯一映射到一个 canonical slot，并与相邻节点构成因果；缺项、重复、倒序、循环解释、token bag 或无法唯一映射都 BLOCK。可使用加粗突出真正的买家判断、证据缺口、stop condition 或下一动作，但不得把六条写成审计表单。

## 4. Direct Answer 与首屏

Canonical direct-answer 槽位：

```yaml
direct_answer_action: "..."
direct_answer_object: "..."
direct_answer_required_inputs_or_evidence: "what the reader must know, provide, inspect, or verify before acting"
direct_answer_condition_or_boundary: "when the action applies, stops, or changes route"
direct_answer_expected_output_or_route: "the observable output or explicitly delegated next route"
direct_answer_evidence_boundary: "what is proven, missing, synthetic, deferred, or requires the next validation"
```

以上六个字段共同构成唯一 Direct Answer 合同：`action / object / required inputs or evidence / condition or boundary / expected output or route / evidence boundary`。不要求 front matter 与正文逐字复制，也**不要求买家看到固定 `Direct answer:` 标签**；可以用自然首段、短 lead 或 callout 呈现。首个 H2 前的完整 opening 以 **120–140 个英文词作为编辑目标，不是 fatal 字数门槛**；真正的 fatal gate 是完整 opening 是否在首个 H2 前自然交付 task、narrow ICP fit、explicit exclusion、buyer self-identification、first-round output、commitment boundary 与六槽 direct-answer 语义。synthetic/fictional fixture 还必须在此处披露。required inputs/evidence 与 evidence boundary 必须同屏可扫读，不得埋到文末或扩成完整 worksheet。

Exact parity 要求：

1. `direct_answer_action` 必须与 `dominant_task_contract.action` 同义且不扩大任务；
2. `direct_answer_object` 必须与 `dominant_task_contract.object` 指向同一对象；
3. `direct_answer_required_inputs_or_evidence` 必须列出完成该动作前真正需要的 inputs/evidence，不得把后续商业收资偷渡进非商业 stage；
4. `direct_answer_condition_or_boundary` 必须说明适用条件、stop/no-fit 条件或 route-change 边界；
5. `direct_answer_expected_output_or_route` 必须与 dominant task 的 observable output 一致，或精确指向已接受任务的 next route；
6. `direct_answer_evidence_boundary` 必须区分已证明、缺失、synthetic、deferred 与待验证内容，不得改写成收益保证。

Brief、Draft、Review 与可见首屏必须在上述六项上语义一致；任一槽位缺失、对象/输出漂移、stage/commitment 冲突、route 无真实 owner/acceptance，或正文仅靠关键词重合，均不得 PASS。要求仍包括：直接回答 dominant buyer task；不以公司介绍、行业大词或 SEO 前言开场。首个 H2 前必须让目标买家完成自我识别：一句说明“适合谁/处于什么触发场景”，一句说明“不适合谁/何时停止”，且 fit/exclusion 与 `icp_fit_contract`、`icp_exclusion_contract` 语义一致。机械检查只能验证字段和候选位置，最终 parity 必须人工审查。

## 5. 搜索证据、ICP、SERP gap 与 information gain

每篇文章必须显式记录可投影的 ICP 合同，而不是只写 buyer role：`icp_evidence_status/refs`、`icp_fit_contract` 与 `icp_exclusion_contract`。Fit 至少说明目标企业类型、应用场景、购买阶段或触发条件，以及买方具备哪些条件才可执行下一步；exclusion 必须排除相邻但不适用的行业、应用、消费型流量、price-only 流量或证据不足项目。Production ICP evidence 未 `confirmed`、refs 为空、状态已 `expired`，或 Brief/Draft/Review/Publish 四记录 projection 漂移时必须 BLOCK。

Production 搜索证据必须按四轴独立记录并 fail closed：

```yaml
buyer_task_evidence_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
buyer_task_evidence_refs: []
buyer_task_evidence_gate_verdict: "pass|block"
query_evidence_status: "missing|inferred|confirmed"
query_evidence_refs: []
query_evidence_gate_verdict: "pass|block"
search_demand_evidence_status: "missing|inferred|confirmed"
search_demand_evidence_refs: []
search_demand_evidence_gate_verdict: "pass|block"
serp_format_evidence_status: "missing|inferred|confirmed"
serp_format_evidence_refs: []
serp_format_evidence_gate_verdict: "pass|block"
production_search_evidence_gate_verdict: "pass|block"
```

Buyer-task evidence 与 query evidence 不得相互替代。Production query evidence 必须 dated，并逐 query 绑定 `query → action → object → observable output → stage → commercial commitment`，另记录 market/language/device/checked_at 和 immutable evidence ref。Production query evidence 与 SERP-format evidence 的 `checked_at` 最长有效期均为 395 天；超过时限或无法证明实际观察日期时，status 只能写 `missing|inferred|expired`，对应 gate 必须 `BLOCK`。

Search-demand 是独立 production evidence object，不得由 buyer opinion、销售判断、SERP 截图、文章结构或 query presence 代替。每个 `search_demand_evidence_refs` 必须精确指向包含以下 schema 的 dated fragment：

```text
exact query set | source/platform | market | language | device | observation_start_at | observation_end_at | metric type | observed value per query | brand/non-brand boundary | zero/low-demand decision | seasonality/trend note | analyst conclusion | independent reviewer | immutable snapshot ref | digest
```

- exact query set 必须等于 `{primary_query} ∪ supporting_query_variants`，每个 query 都有同一 metric definition 下的 observed value；aggregate 不能掩盖漏 query；
- source/platform、market、language、device、`observation_start_at`、`observation_end_at` 与 metric type 必须明确；不得把不同口径数值拼成同一 demand conclusion。`observation_end_at` 不得晚于其 evidence `observed_at`、immutable snapshot `captured_at` 或当前 record `reviewed_at`；任一时间缺失、倒置或越过 review ceiling 都 BLOCK；
- brand/non-brand boundary 必须说明品牌词如何分离；zero/low-demand decision 必须说明继续、改写、合并、noindex 或 do-not-write 的依据；
- seasonality/trend note 不得省略；若观察窗无法判断季节性或趋势，必须明确写 `unknown` 及其限制，不能留空；
- analyst conclusion 必须由 observed values 支持，并由独立 reviewer 复核。没有 metric/value、wrong market、wrong query、stale/未界定 window、opinion-only 或 zero/low demand 被主观改写为“有需求”时，status 只能 `missing|inferred`，gate 必须 `BLOCK`。

Production query/search-demand/SERP-format 任一未 `confirmed`，总 gate 必须 `BLOCK`。SERP-format evidence 还必须记录 result types、snapshot 和 digest，并由人工确认 supporting variants 的真实意图 parity。

Information gain 拆成两条轴：

```yaml
information_gain_artifact_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
information_gain_artifact_refs: []
market_information_gain_status: "missing|inferred|confirmed|not-applicable"
information_gain_market_refs: []
```

Production 声称两轴 `confirmed` 时必须满足：

1. artifact refs 非空，精确指向真实 decision artifact fragment；
2. market refs 非空，精确指向 dated market/SERP comparison fragment；
3. 两组 refs 指向**不同 fragment**，不得复用同一泛化段落；
4. dated comparison 至少记录 market、language、query set、checked_at、comparison corpus/snapshot、差异维度与 reviewer；
5. 任一 fragment 缺失、错锚、未 dated 或只证明“文章有结构”时 fail closed。

Synthetic fixture 可以证明 artifact shape，但 query/search-demand/SERP-format 与 `market_information_gain_status` 必须保持 `missing`，对应 production gate 为 BLOCK；`production_evidence_score` 只写 `not-applicable`。不得用结构完整度冒充真实查询、真实需求、SERP 形式或市场差异。

### 5.1 Production evidence identity、provenance、snapshot 与 freshness

Production evidence 不接受 display name 自证。所有 evidence record 和 snapshot 必须使用 stable identity fields：

```yaml
author_id: "stable-person-id"
producer_id: "stable-person-id"
independent_reviewer_id: "different-stable-person-id"
remediation_participant_ids: []
identity_provenance_evidence_refs: []
identity_provenance_observed_at: "ISO-8601-or-not-applicable"
identity_provenance_reviewed_at: "ISO-8601-or-not-applicable"
identity_provenance_review_ceiling: "ISO-8601-or-not-applicable"
reviewer_separation_verdict: "pass|block"
```

`independent_reviewer_id` 不得等于 author、producer、任何 remediation participant，或该 scope 明确禁止兼任的 accountable owner。显示名、岗位后缀或角色变化不能改变同一个 stable person ID；稳定 ID 只是去重键，不等于真人身份已验证，Production 还必须有独立 provenance ref。`identity_provenance_observed_at` 必须不晚于 `identity_provenance_reviewed_at`，后者不得晚于 `identity_provenance_review_ceiling`；review ceiling 由当前审查预先声明，过期、缺时区或 provenance artifact 无 digest 时 Production identity gate BLOCK。AI/self-review、fixture identity 或包内自签名不能满足 Production independence。

凡 evidence record 声明 `artifact_digest` 或 snapshot digest，必须同时有 package-root-relative、可解析、不可逃逸的 artifact/snapshot ref，并按原始 bytes 重算 SHA-256；只有 64 位十六进制而无真实 artifact 的记录一律 BLOCK。Production snapshot 使用 closed common envelope：

```json
{
  "schema_version": "website-content-ops.snapshot.v1",
  "artifact_kind": "search-demand|serp-format|market-comparison|content-inventory",
  "evidence_scope": "production",
  "captured_at": "ISO-8601 timestamp",
  "subject_id": "stable subject/page/query-set id",
  "scope_id": "stable client/site/package scope id",
  "capture_method": "reproducible method",
  "producer_id": "stable person id",
  "independent_reviewer_id": "different stable person id",
  "payload": {}
}
```

Common envelope 之外，每个 `artifact_kind` 的 `payload` 必须非空并使用 closed kind-specific schema：

- `search-demand`：exact query set、source/platform、market、language、device、`observation_start_at`、`observation_end_at`、metric type、每 query observed-value rows、brand/non-brand boundary；
- `serp-format`：exact query set、market、language、device、checked_at、eligible result rows、result-type counts、primary-query dominance inputs；
- `market-comparison`：exact query set、market、language、device、checked_at、comparison corpus IDs/rows、difference dimensions、accepted information gain 与 boundary。Corpus row 固定使用 `stable-id|https-url|content-family|existing-topic-or-decision-artifact`；ID 与 rows 必须 exact-set 一致，difference dimensions 非空且具体，accepted information gain 与 boundary 必须逐字段投影到 fragment，禁止用泛化 `comparison` 文本或自报 PASS 代替；
- `content-inventory`：site/scope、retrieval dimensions、checked_at、candidate rows、owner task、overlap basis、candidate action 与 zero-result basis。

只有 schema envelope、空 `payload`、空 rows、泛化说明或无法绑定 query/market/page/scope 的 snapshot 都是 fatal BLOCK。`captured_at` 必须不晚于 Review/Publish checked date，并满足声明的 kind-specific max age；默认上限不得宽于 395 天，kind 可收紧。过期 artifact 只能显式标为 historical，必须记录 historical-use reason，且不能满足 current Production readiness。ICP Production evidence同样必须有 affirmative provenance snapshot、source kind、capture method、subject/scope IDs、producer/reviewer IDs 和 digest-bound observation；`synthetic/虚构` denylist 只能作为 defense-in-depth，不能充当真实性边界。

任何 synthetic fixture、示例 person ID、`example.test` URL、placeholder snapshot 或测试生成的 digest，只能验证字段和 validator branch，不得称为 production baseline、production proof、真实市场观察或外部独立审核。

四记录必须 exact projection：

```yaml
evidence_origin: "synthetic-fixture|test-fixture|live-production"
fixture_identity: "concrete-id|not-applicable"
production_proof_eligible: true
customer_language_status: "missing|inferred|confirmed"
customer_language_refs: []
customer_language_gate_verdict: "pass|block"
pain_evidence_status: "missing|inferred|confirmed"
pain_evidence_refs: []
pain_evidence_gate_verdict: "pass|block"
```

Production 内容合同只有在 `evidence_origin=live-production`、`fixture_identity=not-applicable`、`production_proof_eligible=true`，且 customer language 与 pain evidence 都是 `confirmed + 非空 fragment-bound refs + gate pass` 时才允许进入 production readiness 判断。`synthetic-fixture` 与 `test-fixture` 必须有具体 `fixture_identity`、`production_proof_eligible=false`；其 inferred/fixture evidence 可以验证结构，但 customer/pain gate 必须保持 `block`，不得升级为 production proof。

### 5.2 FAQ conditional contract

FAQ 是搜索意图与买家异议的**条件性支持组件**，不是每篇文章的固定模块、字数配额或关键词容器。只有下列任一触发成立时才允许规划 FAQ：

1. dated、可复核的真实 SERP/query pattern 显示，同一 dominant buyer task 下存在正文决策路径尚未自然承接的具体追问；
2. buyer-task、CRM、访谈、support、sales 或产品研究证据记录了具体 buyer objection / uncertainty，且文章应自行回答而不是委派给另一 owner page。

Brief、Draft、Review、Publish Record 必须 exact projection 同一 FAQ decision record：

```yaml
faq_applicability: "applicable|not-applicable"
faq_trigger_type: "dated-serp-pattern|documented-buyer-objection|documented-buyer-uncertainty|none"
faq_trigger_evidence_refs: []
faq_absence_reason: "required when not-applicable; explain why no eligible trigger exists"
faq_items: []
faq_decision_verdict: "pass|block"
```

FAQ trigger 的唯一 closed enum 是 `dated-serp-pattern|documented-buyer-objection|documented-buyer-uncertainty|none`；任何旧 trigger、同义 alias 或“SEO best practice”占位值都 BLOCK。`not-applicable` 时 trigger 必须为 `none`、refs/items 必须为空且 absence reason 具体；`applicable` 时 trigger、fragment-bound refs 与非空 items 缺一不可。

当 `faq_applicability=applicable` 时，每一题使用以下 exact row grammar：

```text
question | buyer_job | objection_or_uncertainty | evidence_ref_or_explicit_inferred_boundary | article_owned_answer
```

- `buyer_job` 必须与 dominant buyer task 或已有证据支持的 secondary buyer role/task 一致；FAQ 不得另起一个 stage、commercial commitment 或新的 owner page；
- `objection_or_uncertainty` 必须具体到买家无法继续判断或执行的缺口，不能只写关键词变体；
- production 可证实事实使用 fragment-bound evidence ref。若某一问只能基于推断，第四槽必须明确写 `inferred`、推断依据和不可外推边界；该标记不能把 production evidence 升级为 `confirmed`；
- `article_owned_answer` 必须给出本页可完成的有边界答案；若答案实际属于产品页、支持页、比较页或商业接收方，应按 owner-page / internal-link / CTA 合同委派，而不是在 FAQ 中伪装完成；
- 不得复述正文凑字数，不得用同义关键词问题堆叠，不得仅以“SEO 最佳实践”为由强加 FAQ，也不得把 FAQ 数量或关键词覆盖率当成质量门槛。

没有符合条件的触发证据时，`faq_applicability=not-applicable`、refs 为 `[]` 且填写具体 `faq_absence_reason` 即为合法；FAQ absence 不得导致扣分或 BLOCK。若添加 FAQ，则 Review 必须逐题检查 buyer-job parity、objection/uncertainty、evidence 或明确 inferred boundary、article-owned answer 与 keyword stuffing；任一失败时，相关 query/task、hierarchy 或 evidence verdict 不得 PASS。

## 6. Content inventory 与 cannibalization

Brief 必须记录，并由 Draft、Review、Publish Record exact projection：

```yaml
owner_page: "..."
content_inventory_status: "missing|inferred|confirmed|confirmed-for-fixture-structure"
inventory_snapshot_ref: "..."
inventory_checked_at: "YYYY-MM-DD"
cannibalization_status: "clear|resolved|unresolved"
conflict_candidates: []
intent_separation: []
inventory_zero_result_evidence_refs: ["path.md#exact-zero-result-evidence-fragment"]
content_action: "create|update|merge|redirect|do-not-write"
```

`content_action` 只表达页面级处理动作，不表达 fixture 身份；Brief、Draft、Review、Publish Record 必须逐字符 exact projection 同一 closed-enum 值。Synthetic fixture 新建示例固定使用 `create`，fixture 身份由 `evidence_origin`、`fixture_identity` 与 `production_proof_eligible` 共同表达，不得借 `content_action` 或记录类型推断。

四记录还必须 exact projection `dominant_search_intent`、`content_family_matches` 与 `content_family_singleton_verdict`。`content_family_matches` 必须从 marker 内正文结构独立重算；恰好一个 family 才允许 singleton verdict=`pass`，零个或多个都 BLOCK。不得只在 Publish 登记、只复制 expected type，或用 `body_content_family_implementation_verdict` 替代 exact singleton 记录。

状态分支：

- `clear`：允许 `conflict_candidates=[]` 和 `intent_separation=[]`，但必须有独立 inventory snapshot 与 zero-result evidence；
- `resolved`：至少一个 candidate，且 candidate 与 intent separation 按 URL 一一对应；
- `unresolved`：发布 BLOCK。

`clear` 的 zero-result evidence 必须独立于 information-gain、SERP-gap 或文章内容段落，并至少记录：

```yaml
inventory_zero_result_evidence:
  scope: "site/locale/content-types/statuses/date boundary"
  checked_at: "YYYY-MM-DD"
  retrieval_dimensions: ["URL/slug", "title", "primary query", "supporting variants", "task/action/object", "taxonomy"]
  candidate_count: 0
  snapshot_ref: "immutable inventory snapshot"
  snapshot_digest: "sha256:..."
  evidence_scope: "production|synthetic-fixture"
```

Production `clear` 必须有真实 inventory snapshot 与可复核 digest；placeholder、reserved URL 或 synthetic fixture 只能通过结构审查，不能证明真实站点 cannibalization clear。每个 `inventory_zero_result_evidence_refs` 必须精确绑定包含该 canonical record 的目标 fragment；只验证“同文件有关键词”、指向 information-gain 段落、空锚或错锚均 BLOCK。人工 Reviewer必须复核 scope、日期、检索维度、唯一 `candidate_count: 0`、空 conflict candidates、无匹配 owner/candidate 的 observed result，以及 snapshot/digest 是否指向同一 inventory。

Candidate grammar：

```text
conflict_candidates:
candidate_url | overlap_basis | candidate_action

intent_separation:
candidate_url | owner_task | candidate_task | non_overlap_boundary
```

不得为了通过 validator 编造候选 URL、把 owner page 当 candidate，或用“意图不同”替代真实任务分工。

## 7. Buyer roles 与跨角色 delegation

### 7.1 角色合同

- `primary_buyer_role` 必填，并直接控制文章叙事、首屏和主要异议；
- `secondary_buyer_roles` 可选，只能在有 buyer/customer/product/operational evidence 时加入；
- Engineer、Quality、Procurement、Management 是 Reviewer lenses，不再强制每篇文章各出现一次；
- 无证据的 secondary role 不得为“B2B 完整性”硬塞进正文。

Secondary role grammar：

```text
role | evidence_ref | concrete objection | article-owned answer
```

`secondary_buyer_role_contracts` 是唯一机器字段，逐字符 grammar 为 `role|evidence_ref|concrete_objection|article_owned_answer`；`buyer_role_matrix` 已 retired/forbidden，不得读取、发射、兼容映射或作为第二真源。每个 `secondary_buyer_roles` 必须恰好对应一行 contract，不重、不漏、不多；roles 为空时 contracts 必须为空。Production 的 `evidence_ref` 必须 dated、fragment-bound、non-synthetic，并在 fragment 内证明该角色的具体异议与本文负责回答的边界；synthetic row 只能证明结构，Production 仍 BLOCK。

### 7.2 跨角色 delegation

任何跨角色委派必须使用七段合同：

```text
from_role | to_role | url | retained_task | receiving_task | owner | acceptance_evidence_ref
```

- `retained_task` 写明本文仍负责什么；
- `receiving_task` 写明目标页接收什么；
- owner 必须是 canonical named owner：稳定 owner ID，或“person name + role”；部门、团队、岗位名、`AI`、`TBD` 或多个候选 owner 不能代替 named owner；
- acceptance evidence 必须证明目标页及该 named owner 接受该任务；
- handoff 的触发条件是**实际跨角色 delegation**，不取决于 CTA 是否收资；CTA 与 stage link 任一把任务交给另一角色就必须记录，二者都没有跨角色 target 时 `role_handoff_contracts` 必须为空；
- 主题相关不等于可跨角色委派，虚构目标页、owner 或 acceptance evidence 均 BLOCK。

## 8. Product decision map

Brief 与 Draft 必须使用相同九段 grammar，并在可见正文按相同顺序呈现：

```yaml
product_decision_map:
  - "condition | variable | evidence | no-fit | remaining inputs | candidate-or-stop | candidate target | next-validation target | placement"
```

规则：

- Candidate 只能在 condition、evidence、no-fit 和 remaining inputs 之后出现；
- `candidate-or-stop` 非 stop 时，`candidate target` 必须是可访问的真实 product、solution 或适当 hub link；
- hub 只有在它真实承接候选方向时可作为 target，不能用导航页名称冒充产品证据；
- stop 时 candidate target 可为 `N/A`，但 next-validation target 必须说明收集输入、测试、支持或停止路径；
- brochure、产品名和空 A/B 表不能证明性能、寿命、认证或适用性。

## 9. 层级、扫读与 semantic emphasis

Title/H1 先通过 1.4 的 query/task/stage parity，再检查正文层级。H2 应形成买家决策路径，H3 只服务其父级变量、方法、证据或失败模式。不得为了关键词数量创建平行 H2。`hierarchy_scan_verdict` 必须由 Review 与 validator 作为 fatal input 消费；生成了 `BLOCK` 却仍给 overall PASS 属于合同失败。

每个 `strong` 必须绑定一个 decision-scanning role：

```text
condition | risk | evidence | no-fit | boundary | action | decision
```

Semantic emphasis plan grammar：

```text
decision-scanning-role | complete judgment | placement
```

必须扫描唯一 publishable body 内的**全部** `strong` 并建立一对一追溯：每个 strong 都必须逐字符对应 `semantic_emphasis_plan` 中的一条完整 buyer decision judgment，plan 中要求 strong 的 judgment 也必须真实出现。Pain-chain 正文若使用自然行业化小标题或 strong，同样按其 decision-scanning role 登记；机器合同保留六槽，但不再为英文 schema label 设置 buyer-facing 免登记例外。泛粗体、产品名、人物名、岗位、`Subject:`、`Route status:`、`What to send:`、栏目标签、关键词、半句或 whole-paragraph bold 都不能构成 semantic emphasis PASS；“一个合法 strong + 多个未计划 decorative strong”同样 BLOCK。任一未计划 strong、缺失 planned strong 或非完整判断都令 `semantic_emphasis_verdict: block` 并进入 fatal gate。仍不规定固定粗体数、H2 数、链接数、表格数或 CTA 密度，避免组件堆叠。

作者判断不得用 blockquote 伪装引用；blockquote 只允许有来源引文或明确标记的 copyable message。相同完整句、相同 strong 判断和无新增 condition/evidence/action/boundary 的重复段落应删除。Synthetic fixture 必须在 marker 内、首屏和首个 H2 前明确披露公司、人物、产品、URL 与 workflow 为 fictional；marker 外披露不算 buyer-visible disclosure。首个 H2 前目标约 120–140 个英文词，并同时完成 buyer task、narrow ICP fit、explicit exclusion、buyer self-identification、first-round output 与 commitment boundary；不得重复完整输入清单。

完整 first-round field set、units、formats 与 examples 在整篇买家正文中只能有一个机器可识别的 source surface：优先放在唯一 **worksheet**；只有文章明确没有 worksheet 时，才允许放在唯一 copyable fallback，二者不得同时承载全集。Opening 只讲痛点、直接答案与边界；decision artifact 必须采用移动端更稳的纵向 H3/definition-like blocks、key-value stack 或最多两列结构，只解释变量如何改变判断；preparation 只说明如何使用 worksheet；final CTA 和 fallback 均只引用该 worksheet，不重新枚举五字段。Reviewer 必须按 section 做 normalized field-set 比对，表格、列表、同义改写、词序变化和 label 变化都计入重复面。`section_information_gain_verdict` 与 `normalized_field_set_redundancy_verdict` 必须由 Brief/Draft/Review/Publish exact projection并进入 fatal gate；任一 section 没有新增 decision value，或近完整 field set 在两个以上 surface 重复，都 BLOCK。结构更稳不等于 mobile PASS；没有真实 320px renderer/readability evidence 时仍必须保持 mobile production BLOCK。

### 9.1 Draft control record 与唯一可发布正文

Draft 必须把内部控制记录和买家可见正文物理分离：

```html
<!-- PUBLISHABLE_BODY_START -->
<!-- only buyer-visible article body; starts with H2 when page shell owns H1 -->
<!-- PUBLISHABLE_BODY_END -->
```

- 每份 Draft 必须且只能有一对 marker，顺序正确且边界不重叠；缺失、重复、倒置或空 body 均 BLOCK；
- marker 外是 control record，可保存 front matter、evidence register、review verdict、schema parity、renderer/release notes 与内部 workflow 状态，**禁止直接发布或交给 CMS converter**；
- marker 内不得出现 `# Article Draft`、内部状态码/字段名、validator 说明、evidence gate、schema parity、placeholder、release/renderer note、`replace-with-*`、`[H2: ...]` 或其他编辑指令；这些内容泄漏到买家正文即 BLOCK；
- 买家正文必须使用面向其任务的人话表达；`confirmed / inferred / missing / BLOCK / technical-qualified / sales-accepted` 等内部控制词只有在它们本身是读者必须理解的业务术语时才可出现，否则留在 marker 外；
- 发布、转换或复制正文时只能提取唯一 marker 内的 bounded body。手工选择全文、marker 外内容被转换、CMS 已有 title 时 body 再发射 H1，均不得发布。

## 10. Stage-specific internal links

允许的 link roles：

```text
hub / product / solution / educational / comparison / diagnostic / support / technical-review / conversion / commercial
```

简洁 target：

```text
role | url | descriptive_anchor
```

Buyer-task contract：

```text
role | url | descriptive_anchor | buyer_need | target_buyer_role | placement | target_status | owner | acceptance_evidence_ref
```

要求：

- link roles 必须满足当前 stage 的下一任务，不按统一数量配额；
- anchor 自身必须明确表达买家要完成的 task、decision、缺失 evidence 或 expected output，并与同 row 的 `buyer_need`、target task 和 owner acceptance 一致；禁止 `click here / learn more / view details / explore solutions / discover products / browse options / see products` 等只表达浏览或供应商推广的 anchor。有限 denylist 只作 defense-in-depth；即使不命中禁词，anchor 不能回答“买家到目标页完成什么”也必须 BLOCK；
- product/solution link 只在条件和证据已明确后出现；
- conversion link 只在 stage contract 允许时出现；
- target owner 与 acceptance evidence 必须真实，不能用 AI/TBD。
- 唯一 canonical role 枚举是 `hub|product|solution|educational|comparison|diagnostic|support|technical-review|conversion|commercial`；旧 alias `diagnosis` 禁止出现在机器字段、模板值或示例记录中。

五阶段 link-role 矩阵先受 `stage_link_requirement_status` 控制。`not-applicable` 时下表不产生数量要求，也不得为了“凑内链”添加离题目标；`applicable` 时再区分 `required_when_applicable` 与 `allowed`。若 `stage_link_requirement_status=applicable` 但 buyer-visible link 被 withheld 或数量为 0，`buyer_visible_internal_links_verdict` 必须为 `block`，不得用 `not-applicable` 掩盖。withheld-link negative fixture 必须明确标记 fixture identity 并保留该 BLOCK。Positive fixture 只有在 marker 内存在真实 buyer-visible Markdown link，且 reference、reachability、capability、target-task acceptance 与 owner evidence 全部通过时才可得到结构 scope PASS；synthetic placeholder URL 即使演示 gate shape，`production_proof_eligible` 仍必须为 `false`，不能冒充 Production link proof：

| Stage | `required_when_applicable` | `allowed`（仅在正文任务和证据支持时） |
|---|---|---|
| Learn | 至少一个 `educational` 或 `hub` | 另一个 `educational|hub` |
| Troubleshoot | 至少一个 `diagnostic` 或 `support` | 诊断结果确需进一步处理时才允许 `technical-review|product` |
| Compare | `comparison` | 只有证据化候选存在时才允许 `product|solution|hub` |
| Validate | `technical-review` | candidate 非 stop 时才允许真实 `product|solution` 或承接候选的 `hub` |
| Buy | 至少一个 `product` 或 `solution`，并至少一个真实下一步 `conversion` 或 `commercial` | 另一个有证据的 `product|solution|conversion|commercial` |

## 11. Stage-specific CTA intake 与 progressive refinement

每篇文章先记录 intake contract，不得先假定需要表单或技术 qualification：

```yaml
cta_interaction_type: "inline-no-input|local-tool|input-collecting|human-handoff|commercial"
stage_intake_contract: "none|troubleshoot-support|compare-handoff|validate-technical|buy-commercial"
cta_input_collection_applicability: "applicable|not-applicable"
cta_input_collection_not_applicable_reason: "required when not-applicable"
```

所有 applicable route 都必须说明 trigger、minimum inputs、expected output/route、boundary、真实 destination、named owner、capability evidence、soft path 与 copyable fallback；但**只有 `validate-technical`**启用两轮 technical progressive profiling。

所有 buyer-visible surface 还必须投影 transmission grammar：

```yaml
cta_transmission_action_inventory:
  - "surface-id|normalized-action|object|instruction-mode|route-id-or-not-applicable|route-status|evidence-bundle-ref-or-not-applicable"
cta_route_transmission_verdict: "pass|block|not-applicable"
```

`normalized-action` 是 open-class inventory：至少覆盖 `save|request|send|submit|upload|share|email|contact|use|paste|attach|fill|enter|import|drag|drop|copy into|forward|post|transmit|hand off control`，以及任何在语义上把 packet、数据、文件、消息或控制权转给另一主体/系统的同义、被动、条件、recommendation 或标点拆分形式。四记录的 `cta_transmission_action_inventory` 必须逐字符 exact projection，并覆盖全部 buyer-visible transfer/control actions；漏一处即 fatal BLOCK。`instruction-mode` 只允许 `local-only|prohibited-until-verified|conditional-after-verification|immediate`。未验证/不可用 route 只能出现本地保存、明确禁止传递，或“验证后再传递”的条件句；不得出现立即 paste/attach/fill/upload/submit 等指令、直接 endpoint 链接或肯定性可用声明。任何传递动作都必须绑定该 exact route 的 reference、reachability 与 capability evidence，而不是借用另一 endpoint 的证据。

### Validate 两轮 progressive refinement

```yaml
cta_input_collection_mode: "progressive-profiling"
first_round_inquiry_inputs: ["4-6 minimum decision inputs by default"]
second_round_inquiry_inputs: ["bounded second-round technical inputs"]
cta_required_inputs: ["exact copy of first_round_inquiry_inputs"]
second_round_input_relationships:
  - "second_round_item|new-or-refines|first_round_item-or-not-applicable|additional_decision_purpose"
cta_destination: "real technical-review destination"
cta_owner: "named technical owner"
```

Rules：

- `new-or-refines` 只允许 `new` 或 `refines`；每个 second-round item 恰好一行；
- `new` 必须把第三槽写 `not-applicable`；`refines` 必须精确引用一个 first-round item，并说明从 summary 到 detail 的新增 decision purpose；
- 可以 summary → detail，例如首轮 `duty summary`、二轮 `duty cycle by operating segment`；这不是重复，但必须说明为何详细值改变技术判断；
- 不得再次索取已经提交的同一个值、只换单位/措辞制造“新字段”，或让二轮与首轮语义重复而没有 additional decision purpose；
- `second_round_input_relationships` 必须覆盖所有实际二轮请求且不得多发；每行严格使用 `second_round_item|new-or-refines|first_round_item-or-not-applicable|additional_decision_purpose`，不得带额外槽位；缺失、重复、孤立 refinement 或目的不改变判断均 BLOCK；
- `qualification_rows`、`cta_first_round_inputs`、`cta_complete_technical_inputs`、`cta_second_round_rows`、`second_round_rows` 等别名均 retired/forbidden；不得 alias mapping 到 canonical 字段制造 PASS；
- `technical-qualified` 只能由 complete technical evidence + named technical owner acceptance 产生，不能由表单提交自动产生。

其他 intake contracts：

- `none`：不收资、不发 intake fields、不 qualification；
- `troubleshoot-support`：只收完成当前诊断/support 所需 packet；允许缺输入时 `needs-follow-up`，不使用两轮 technical progressive profiling，不产生 technical-qualified 或 sales-accepted；
- `compare-handoff`：只收证据化 mixed-commercial handoff 的最小字段；默认无 qualification，不使用 technical-qualified lifecycle；
- `buy-commercial`：使用独立 RFQ/commercial packet 和 named commercial owner；可含必要技术字段，但不使用上述 `second_round_input_relationships`，也不从 technical-qualified 继承 acceptance。`sales-accepted` 仍需 explicit commercial intent、完整商业输入、owner review 和明确 commercial next step。

`cta_input_collection_applicability: not-applicable` 必须给出 non-empty reason；此时 intake packet、destination、qualification rows、soft path 与 fallback 不作为门禁，且不得用占位表单伪造 applicable。

### 11.1 全部 buyer-visible CTA 与 fallback route 闭环

Reviewer 和 validator 必须枚举唯一可发布正文中的**全部 buyer-visible CTA instructions**，不能依赖 H2、最后一个 CTA、固定标题或 `CTA` 标签。scope 包含首个 H2 之前的导语、普通段落、列表、表格、粗体标签、链接文本/URL、按钮文案，以及任何 `submit / send / share / upload / contact / book / download / email / forward / transfer / request / use the form / route the packet` 等直接或同义动作。每条指令必须进入 `buyer_visible_cta_inventory`，绑定稳定 `surface-id`、精确位置、destination、owner、interaction type、route status、evidence bundle 与 fallback contract。任一早期、中段、软路径或最终 CTA 的 endpoint、发送指令、owner、inputs、commitment boundary 或证据强度与其他 CTA 冲突，整篇立即 BLOCK；后置安全 CTA 不能覆盖前置不安全 CTA，未被枚举的 CTA 也直接 BLOCK。以下三个 Review/Publish verdict 必须由 fatal gate 消费：

```yaml
soft_path_route_safety_verdict: "pass|block"
all_buyer_visible_cta_sections_evidence_parity_verdict: "pass|block"
cross_cta_instruction_consistency_verdict: "pass|block"
```

`buyer_visible_cta_inventory` 使用唯一十槽 row：

```text
surface-id|location-kind|locator|instruction|destination|owner|interaction-type|route-status|evidence-bundle-ref|fallback-contract-ref
```

`location-kind` 至少支持 `pre-h2|paragraph|list|table|strong-label|link|button|heading`。inventory 必须覆盖全文所有动作指令；同一指令只能有一个 route binding，不能靠标题形式或位置逃逸。

Brief、Draft、Review 与 Publish Record 必须逐字符保持同一 `cta_fallback_route_contract`。它是唯一 17 段 pipe row：

```text
route-status
| endpoint
| owner
| required-inputs-mode
| commitment-boundary
| reference-execution
| reference-result
| reference-verdict
| reference-refs
| reachability-execution
| reachability-result
| reachability-verdict
| reachability-refs
| capability-execution
| capability-result
| capability-verdict
| capability-refs
```

`route-status` 只允许 `verified|unverified-unavailable|not-applicable`。三个 evidence axis 只能使用 canonical closed enum：execution=`not-run|executed|not-applicable`；result=`missing|synthetic-only|confirmed|failed|not-applicable`；verdict=`pass|block|not-applicable`。任何 `done-locally`、`observed` 或近义 alias 均 BLOCK。

- `verified`：必须提供 concrete endpoint、canonical named owner、完整 inputs mode 与 commitment boundary；reference、reachability、capability 三轴都必须是 endpoint-specific `executed|confirmed|pass`，且各自 refs 非空。每个 verified primary CTA 或 fallback route 还必须绑定自己的 structured evidence bundle，至少包含 `evidence_kind`、`check_id`、`task`、`owner`、实际执行 `process`、事实 `observed_result`、`capability_acceptance` 与 fragment-bound `evidence_ref`；只重复 endpoint 文本、Markdown 链接、HTTP 200、toast、作者自述，或借用主 CTA/其他 URL 的证据均不能确认 route。
- `unverified-unavailable`：`endpoint=not-applicable`，三轴必须分别为 `not-run|missing|block|not-applicable`；**全文不得直接链接、展示为可点击目标、指示 use/send/email/share/submit/contact 到该 primary 或 fallback route**。全部 buyer-visible CTA 只能明确 **do not send / save locally / request a verified route through the buyer organization's existing approved supplier-contact process**。任何肯定存在 verified/approved/secure/existing route 的句式，或“仅当表单失败时才不要发送”的条件式写法，都立即 BLOCK。
- `not-applicable`：仅在 intake 与 fallback 确实不适用且有非空理由时使用；不能用它绕过 collecting、handoff 或 commercial CTA 的 route safety。

每个实际收资的 verified primary 或 fallback endpoint 必须由单一 canonical 数组逐 endpoint 绑定：

```text
cta_collection_route_policy_contracts:
route-id|endpoint|required-inputs-mode|data-purpose|retention-period|deletion-path|retention-owner|policy-contract-id|policy-version|policy-digest|policy-checked-at|policy-observed-at|policy-reviewed-at|policy-review-ceiling|policy-status|policy-owner-acceptance|policy-evidence-refs|deletion-capability-evidence-refs
```

每个 `required-inputs-mode != none` 的 verified collecting endpoint 必须恰好一行，`route-id` 与 `endpoint` 均逐字符匹配该 primary/fallback route；不得让 fallback 借用 primary policy、删除能力或 owner evidence。`required-inputs-mode=none` 不触发 collection-policy row，也不得被 validator 误要求。Collecting route 必须绑定 policy contract ID、version、SHA-256 digest、`policy-checked-at`、`policy-observed-at`、`policy-reviewed-at` 与预先声明的 `policy-review-ceiling`；checked/observed 不得晚于 reviewed，reviewed 不得晚于 ceiling，digest 必须绑定被审 policy bytes。过期、缺时区或任一值缺失即 policy gate BLOCK。若保留 `cta_data_*` scalars，它们只能是 primary collecting route row 的 exact projection，不能成为第二真源；无 primary collecting route 时必须为 `not-applicable`/空 refs。

买家可见 endpoint gate 只呈现用途、不得提交的数据边界、route availability 与负责响应方；retention owner、review ceiling 等完整治理核验留在后台 Review/SOP，不得要求买家自行调查。Local preparation 可以指导买家在本地整理 worksheet/packet；在 destination、reference parity、reachability、capability、policy contract、retention period、deletion path 与 named retention owner 全部 endpoint-specific confirmed 之前，`Supplier-side collection purpose` 必须为 `not applicable`，`cta_collection_send_gate_verdict=block`，正文只能请求 verified route/policy details，不得指示发送 packet。

`owner`、`cta_receiving_owner`、`cta_owner` 以及 `role_handoff_contracts` 的 receiving owner 共用同一 named-owner parser：只接受稳定 owner ID，或 `person name + role`；纯岗位名、部门、团队、AI、TBD、多候选均不合格。

`qualification_reason_codes` 的 canonical row grammar 为：

```text
state | cause-category | evidence-rule | owner | next-step
```

必须 cause-first：先由证据判定 cause category，再映射当前 stage/intake 允许的 state；不得先选理想状态再补理由。

## 12. Technical-qualified 与 sales-accepted 分离

Qualification state semantics：

| State | Required cause/evidence | Allowed owner | Required next step |
|---|---|---|---|
| `needs-follow-up` | 缺少完成当前 gate 所需输入，尚无 no-fit 证据 | technical 或 commercial follow-up owner，按缺口类型决定 | 只请求缺失输入，不得升级 acceptance |
| `disqualified` | 有明确 technical no-fit 或 commercial no-fit evidence rule 命中 | 对应 technical/commercial accountable owner | 记录原因、证据与 stop/alternate route |
| `technical-qualified` | 技术输入完整、evidence rule 通过、technical owner 明确接受 bounded technical next step | technical reviewer/deliverable owner；Applications Engineering 可承担 | 技术判断、测试或 next-validation；不产生 sales acceptance |
| `sales-accepted` | explicit commercial intent + required commercial inputs + sales/commercial owner acceptance | 只能 commercial/sales accountable owner | 明确 commercial next step |

Applications Engineering 只能是 technical reviewer、technical deliverable owner 或 technical follow-up owner，不能作为 sales acceptance owner。Sales-accepted 不得由下载、support 请求、技术 review、worksheet 完成或 technical-qualified 自动推导。

Stage semantics：Learn 默认无 qualification；Troubleshoot 可 `needs-follow-up`/technical route；Compare 默认无 sales qualification；Validate 始终 `commercial_commitment: none`，最多形成 technical-qualified，且无 sales acceptance、RFQ、order 或 supplier-award commitment；Buy 或有证据的 mixed-commercial route 才启用 sales acceptance。若 Validate 出现显式商业意图，必须先重分类/路由，不能在原 stage 偷渡商业状态。

### 12.1 Actual outcome evidence 与 named-owner 合同

实际结果字段使用 Buyer 细粒度 canonical closed enum，不得写自由文本、`observed` 总称或其他近义 alias：

```yaml
actual_ranking_status: "unverified|not-applicable|observed-no-improvement|observed-improvement"
actual_inquiry_status: "unverified|not-applicable|observed-no-improvement|observed-improvement"
actual_sales_acceptance_status: "unverified|not-applicable|not-accepted|sales-accepted"
actual_conversion_status: "unverified|not-applicable|observed-no-improvement|observed-improvement"
actual_outcome_observation_window: "dated-window|not-applicable"
actual_outcome_metric_or_event_definition: "metric-or-event-definition|not-applicable"
actual_outcome_observed_result: "bounded-observed-result|not-applicable"
actual_outcome_evidence_refs: []
actual_outcome_accountable_reviewer: "stable-reviewer-id-or-person-name-plus-role|not-applicable"
actual_sales_acceptance_evidence_refs: []
```

Shared outcome evidence contract：

- `unverified` 表示没有足够真实结果证据；`not-applicable` 只用于 stage/measurement plan 明确不适用的 outcome。两种状态都必须令 `actual_outcome_observation_window`、`actual_outcome_metric_or_event_definition`、`actual_outcome_observed_result`、`actual_outcome_accountable_reviewer` 为 `not-applicable`，并令两组 evidence refs 为 `[]`；不得据此暗示改善。
- Ranking、inquiry 或 conversion 写 `observed-no-improvement` 或 `observed-improvement` 时，五个 shared evidence fields 必须完整：dated observation window、metric/event definition、bounded observed result、非空 evidence refs、accountable reviewer。状态必须由 observed result 支持，不得把“有数据”自动写成 improvement。
- Sales acceptance 写 `not-accepted` 时，同样必须有完整 shared outcome evidence，且 observed result 必须记录未接受的 gate/原因，不得把 missing evidence 冒充 not-accepted。
- `actual_sales_acceptance_status: sales-accepted` 除完整 shared evidence 外，`actual_sales_acceptance_evidence_refs` 必须非空，并逐项证明 `explicit-commercial-intent`、`commercial-qualification-required`、`commercial-inputs-complete`、`named-commercial-owner-reviewed-and-accepted`，以及 named commercial owner 与 commercial next step。Technical-qualified、技术 review、下载或 CTA submit 都不能代替 sales acceptance。
- 同一记录有多个非 unverified outcomes 时，shared evidence 内容和 refs 必须按 outcome 明确分段或逐项绑定，不能用一个模糊结果同时覆盖 ranking、inquiry、sales acceptance 与 conversion。

Canonical named owner 只接受：稳定 owner ID，或 `person name + role`。部门、团队、角色名本身、`AI`、`TBD`、`Applications Engineering`、`Sales` 等均不合格。每条 qualification reason row 的 `owner` 必须与该 state/route 的 canonical owner **精确绑定**：技术状态绑定 `technical_qualification_owner` 或该状态声明的 named technical owner；商业状态绑定 `sales_acceptance_owner`。不得写“团队或某人”、多个备选 owner，或仅凭岗位语义近似通过。

Cause-first reason row 继续使用唯一 grammar：

```text
state|cause-category|evidence-rule|owner|next-step
```

## 13. Reference / reachability / capability 三轴

每个适用对象分别记录三字段：

```text
*_check_execution_status: not-run | executed | not-applicable
*_evidence_result: missing | synthetic-only | confirmed | failed | not-applicable
*_gate_verdict: pass | block | not-applicable
```

分别应用于 CTA 和 internal-link 的：

- reference parity；
- reachability；
- capability / target-task acceptance。

Production applicable gate 只有在 `executed + confirmed + pass` 时通过。每个 CTA route 的三轴必须由该 endpoint 自己的 structured evidence bundle 支撑，bundle 至少含 `evidence_kind/check_id/task/owner/process/observed_result/capability_acceptance/evidence_ref`，并能证明目标确实接受声明的 buyer task；`missing`、未执行、只重复 endpoint、HTTP 200、toast、作者自述或 reserved URL 不能写成 PASS。

Synthetic fixture 可以：

- `structure_gate_verdict: pass`；
- evidence result 写 `synthetic-only`；
- production evidence 写 `not-applicable` 或 gate `block`。

Synthetic fixture 不得升级为 production evidence PASS。

## 13.1 Buyer-visible editorial language gate

Publishable body 必须使用买家自然语言，不得把内部工作流字段、枚举或审查标签暴露给买家。以下仅能保留在 marker 外 control record：`needs-follow-up`、`first-round-complete`、`engineering-review-ready`、`technical-qualified`、`commercial-qualification-required`、`sales-accepted`、`canonical`、`synthetic`、`Soft CTA`、`Final CTA`。正文应翻译为买家可理解的结果，例如“we need more information before recommending a candidate”“the packet is ready for engineering review”“the next step is sample validation”。

Review 必须给出：

```yaml
buyer_visible_editorial_language_verdict: "pass|block"
internal_control_term_leakage_verdict: "pass|block"
```

## 13.2 CTA value exchange and friction boundary

CTA 不是“Contact us”。每个适用 CTA 必须让买家在点击前知道：提交什么、得到什么、通过何种渠道、由谁回应、时效是否已验证、资料边界、以及此动作不构成什么商业承诺。收资、人工 handoff 或 commercial CTA 还必须在买家可见 CTA 区展示可复制 fallback packet，并严格二选一：

1. **已验证 fallback route**：买家可见区给出具体 email、portal、form 或 endpoint、外部 route owner、完整 first-round inputs 与同一 commitment boundary；对应 reachability 与 capability 必须都是 `executed + confirmed + pass`，才允许写 `verified`、`approved` 或同义确定性说法。
2. **未验证或未配置 fallback route**：明确写“当前没有 verified fallback route”，要求买家不要发送 packet、先保存在本地，再通过其既有且已批准的 supplier-contact process 请求 verified route；对应 reachability/capability 保持 `not-run + missing + block`。不得用 `verified channel`、`approved route` 或 `secure endpoint` 自证一个不存在的备用入口。

只把 fallback 藏在 frontmatter/control record，或让文案中的确定性强于 evidence axis，一律 BLOCK。

```yaml
cta_value_exchange: "buyer-visible output"
cta_response_expectation: "verified response time or explicitly unknown"
cta_submission_method: "form|email|approved portal|existing engineering channel"
cta_confidentiality_or_data_boundary: "non-confidential packet or approved secure-channel boundary"
cta_data_purpose: "single buyer-visible purpose for collected inputs or not-applicable"
cta_data_retention_period: "bounded retention period or not-applicable"
cta_data_deletion_path: "buyer-visible deletion or withdrawal path or not-applicable"
cta_data_retention_owner: "accountable named role or not-applicable"
cta_commitment_boundary: "technical review only|comparison handoff only|commercial request"
cta_buyer_visible_owner: "named team or role"
cta_value_exchange_verdict: "pass|block"
```

不得编造响应时效、保密承诺或 owner。未知时必须直接写 unknown boundary，而不是删除该字段。凡 CTA 收集输入，买家可见区还必须明确展示唯一 data purpose、有限 retention period、可执行 deletion/withdrawal path 与 accountable retention owner；缺任一项、仅藏在 frontmatter、无限期保留或 owner 为 AI/TBD 时均 BLOCK。不收集输入时四字段必须一致写 `not-applicable`，并与 intake contract 相符。

## 13.3 Product-link evidence ladder

```yaml
product_link_evidence_level: "none|family-level|sku-level"
product_link_claim_parity_verdict: "pass|block"
product_claim_ledger_applicability: "applicable|not-applicable"
product_claim_ledger_not_applicable_reason: "non-empty only when not-applicable"
product_claim_ledger:
  - "claim-id|buyer-visible-claim|claim-type|evidence-ref|applicability-boundary|target-url-or-not-applicable|target-page-parity-status|production-use-status"
product_claim_ledger_verdict: "pass|block|not-applicable"
```

- `none`：只允许 decision tool、educational hub 或 owner page，不得暗示具体产品 fit；
- `family-level`：可链接 solution family/category，并明确还需哪些条件才能缩小候选；
- `sku-level`：只有 condition-to-spec 证据、适用边界和目标页 claim parity 均已证实时才链接具体 SKU。

Synthetic fixture 可以演示结构，但不得因虚构产品卡而升级成 production `sku-level`。

正文中 certification/compliance、universal fit、兼容性、额定/连续性能数值、耐久/寿命、生产能力、交期/库存或具体 SKU suitability 等 buyer-visible 产品事实，必须逐条进入 ledger；每条都要有稳定 claim ID、可解析 evidence ref、适用条件/排除条件、目标页 URL（如有）和 target-page claim parity。证据只支持 family 时不得写 SKU；证据只支持特定条件时不得改写成“fits every / always / guaranteed”。ledger 未适用仅允许在正文没有任何产品/规格/认证/fit/performance claim 时使用，并填写非空理由。Synthetic product card、fixture claim 或目标页自述不能单独满足 Production evidence。

## 13.4 Visual decision asset contract

视觉资产必须减少决策成本，而不是装饰。每项使用九槽合同：

```yaml
visual_decision_assets:
  - "decision-table | compare the five readiness inputs | input-to-decision relationship | evidence-ref | after readiness section | descriptive caption | not-applicable-for-semantic-table | readable without horizontal clipping at 320px | required"
visual_decision_assets_verdict: "pass|block|not-applicable"
```

允许且只允许 `diagram|decision-tree|decision-table|worksheet|annotated-product|process-flow`；`decision-list` 等未登记别名一律 BLOCK。声明 `decision-table|required` 时，对应 H2 内必须出现真实 Markdown table，表头和行必须支持声明 buyer task，并给出 320px stack/label fallback；Review 不得从 frontmatter 自报推断 table visible。若阶段确实不需要资产，必须记录 `not-applicable` 与理由。若 asset type 为图片类且 status 为 `required`，Draft 的声明 H2 内必须出现真实 Markdown image handoff：非空且任务相关的 alt，以及非 placeholder 的 source URL 或 asset locator；caption、alt、buyer task 与声明资产必须能唯一绑定。只有正文出现相似关键词、frontmatter 提到 URL，或存在未绑定媒体记录都不算完成。该 handoff 只证明内容对象已指向媒体，不替代 CMS media ID/readback、图片 fetch/decode 或 final DOM alt renderer 验收；图片类资产仍不能替代 final DOM alt renderer 的独立 BLOCK。

内容层必须先采用小屏友好设计：关键决策表优先改为两列、key-value stack、分组卡片、definition list 或可纵向阅读的重复表头结构；不得把 4–6 列长文本表格直接视为 mobile-ready。`readable at 320px` 只是 requirement，不是证据。没有真实 renderer/readability structured evidence 时，canonical 状态只能是：

```yaml
mobile_visual_check_execution_status: "not-run"
mobile_visual_evidence_result: "missing"
mobile_visual_gate_verdict: "block"
mobile_visual_evidence_refs: []
```

真实 content-contract production-ready 需要 endpoint/page-version-specific structured evidence，唯一 canonical schema 为 `evidence_kind=mobile-readability`、`check_id=mobile-readability`、`target_task`、`accountable_owner`、`viewport_width_px=320`、`render_target`、`method`、`observed_result`、`acceptance_criteria`、`capability_acceptance`、截图或 trace ref。禁止 `mobile-visual` evidence kind、`viewport_width` alias、desktop 截图、作者声明或普通文本“320px/mobile ready”冒充证据。缺该证据时，文章结构 scope 可以独立 PASS，但 `fatal_gate_verdict`、`overall_verdict` 和 `production_readiness` 必须保持 `block`。

## 14. Review、评分与 fatal gates

Review 必须拆分并消费关键语义 verdict：

```yaml
structure_score: 0
production_evidence_score: "0-100|not-applicable"
language_gate_verdict: "pass|block"
query_contract_verdict: "pass|block"
dominant_task_verdict: "pass|block"
stage_contract_verdict: "pass|block"
title_primary_query_parity_verdict: "pass|block"
title_dominant_task_parity_verdict: "pass|block"
title_stage_parity_verdict: "pass|block"
h1_title_task_parity_verdict: "pass|block"
title_slug_stage_parity_verdict: "pass|block"
publishable_body_boundary_verdict: "pass|block"
stage_intake_contract_verdict: "pass|block"
serp_primary_query_dominance_verdict: "pass|block"
serp_content_type_parity_verdict: "pass|block|not-applicable"
body_content_family_implementation_verdict: "pass|block"
article_decision_sequence_verdict: "pass|block"
conversion_surface_map_verdict: "pass|block"
buyer_visible_editorial_language_verdict: "pass|block"
internal_control_term_leakage_verdict: "pass|block"
cta_value_exchange_verdict: "pass|block"
soft_path_route_safety_verdict: "pass|block"
all_buyer_visible_cta_sections_evidence_parity_verdict: "pass|block"
cross_cta_instruction_consistency_verdict: "pass|block"
product_link_claim_parity_verdict: "pass|block"
visual_decision_assets_verdict: "pass|block|not-applicable"
mobile_visual_gate_verdict: "pass|block|not-applicable"
direct_answer_six_slot_verdict: "pass|block"
six_node_causal_chain_verdict: "pass|block"
buyer_role_scope_verdict: "pass|block"
cross_role_delegation_verdict: "pass|block|not-applicable"
cannibalization_verdict: "pass|block"
information_gain_artifact_verdict: "pass|block"
information_gain_market_verdict: "pass|block|not-applicable"
product_decision_map_verdict: "pass|block"
hierarchy_scan_verdict: "pass|block"
semantic_emphasis_verdict: "pass|block"
internal_link_stage_contract_verdict: "pass|block|not-applicable"
cta_stage_contract_verdict: "pass|block|not-applicable"
technical_qualification_verdict: "pass|block|not-applicable"
sales_acceptance_verdict: "pass|block|not-applicable"
unsupported_outcome_claims_verdict: "pass|block"
first_round_output_candidate_gate_verdict: "pass|block|not-applicable"
production_search_evidence_gate_verdict: "pass|block"
internal_link_reference_gate_verdict: "pass|block|not-applicable"
internal_link_reachability_gate_verdict: "pass|block|not-applicable"
internal_link_capability_gate_verdict: "pass|block|not-applicable"
cta_reference_gate_verdict: "pass|block|not-applicable"
cta_reachability_gate_verdict: "pass|block|not-applicable"
cta_capability_gate_verdict: "pass|block|not-applicable"
fatal_gate_verdict: "pass|block"
structure_review_verdict: "pass|block"
production_evidence_review_verdict: "pass|block|not-applicable"
overall_verdict: "pass|block"
production_readiness: "ready|block"
production_readiness_scope: "cms-draft-content-contract"
```

- 上述列表是 fatal verdict 的 closed list；`article_decision_sequence_verdict`、`conversion_surface_map_verdict`、`hierarchy_scan_verdict`、`semantic_emphasis_verdict` 与 `first_round_output_candidate_gate_verdict` 均在 fatal 集内。canonical record 中任何 applicable verdict 为 `block`，或任一 applicable evidence gate 为 `block`，必须同时强制 `overall_verdict: block`、`fatal_gate_verdict: block`、`production_readiness: block`。任何非 `pass|block|not-applicable` 值先按合同错误 fail closed；不得把 `pass-for-fixture-structure`、`confirmed`、`true`、`approved` 或 `warning` 当 verdict。`structure_review_verdict`、`production_evidence_review_verdict`、`overall_verdict` 本身也必须被消费，禁止出现 reviewer 明确 `block` 但 Publish Record 自报 ready；
- `production_readiness_scope` 四记录必须 exact projection 为 `cms-draft-content-contract`。即使 `production_readiness: ready`，也只表示内容合同可进入 CMS draft verification，不表示 formal production SEO ready；三个 deferred frontend SEO、CMS、renderer、source/license 和发布证据继续独立判定；
- `not-applicable` 只允许标准明确声明 applicability 的字段，并必须有非空理由；不得用 `not-applicable` 绕过 CTA、mobile、link、qualification 或 evidence gate；
- Brief、Draft、Review 与 Publish 必须 exact projection 下列主 CTA 与 deferred 字段；不得只复制 destination/owner 而丢失执行状态、观察结果、verdict 或 refs：

```text
cta_destination
cta_owner
cta_reference_check_execution_status
cta_reference_evidence_result
cta_reference_gate_verdict
cta_reference_evidence_refs
cta_reachability_check_execution_status
cta_reachability_evidence_result
cta_reachability_gate_verdict
cta_reachability_evidence_refs
cta_capability_check_execution_status
cta_capability_evidence_result
cta_capability_gate_verdict
cta_capability_evidence_refs
cta_fallback_route_contract
terminal_action_contract
first_round_expected_output
candidate_decision_required_gates
first_round_output_candidate_gate_verdict
frontend_deferred_blocks = []
```

任一 destination、owner、三轴 status/result/verdict、evidence refs、fallback contract、terminal action、首轮输出、candidate gates、首轮 gate verdict 或 deferred exact set 漂移均为 fatal BLOCK；Validate 首轮出现 candidate-or-stop，或 route/policy BLOCK 时仍出现 submit/send 类动作，同样 fatal BLOCK；
- `structure_score`：query/task parity、阶段合同、层级、扫读、字段完整性；
- `production_evidence_score`：真实 SERP、inventory、产品事实、链接、CTA 能力和发布证据；
- synthetic fixture 的 production score 为 `not-applicable`，不得用结构分代替；
- 上述结构/编辑 verdict 任一为 `block`，或任一 production-applicable evidence gate 为 `block` 时，validator 与 overall review 必须消费它并令 `fatal_gate_verdict: block`、overall verdict `block`，无论分数多高；`visual_decision_assets_verdict` 仅在显式 `not-applicable` 且有阶段理由时可不阻断。生成但不消费 verdict 属于 fail-open；
- `five_node_causal_chain_verdict` 是 retired/forbidden legacy field；出现即兼容性 BLOCK，不得 alias 到 `six_node_causal_chain_verdict`。

Reviewer 至少使用 SEO/Search Intent、Primary Buyer、Secondary-role lenses、Content Design、Evidence/Governance 五个角度。四类典型角色只作为 lenses，不能反向强制正文出现。

以下项目必须由人工 Reviewer 做语义和证据审查，机械字段存在、token overlap、数量阈值或格式 regex 不能单独给 PASS：

1. **六槽位因果链**：actor 加五个后续槽位是否具体、因果相连、非同义改写，program consequence 是否有边界；inferred/synthetic pain 是否只用 `may/can/risks`；任何描述该 pain、rework、delay、cost 或 consequence 的 buyer-visible 句子都不得使用确定性 `must/will`，除非同一具体事实已升级为 `confirmed` 并绑定可复核 refs；
2. **Direct Answer 六槽**：正文是否完整呈现 `action + object + required inputs/evidence + condition/boundary + expected output/route + evidence boundary`；首个 H2 前是否以约 120–140 English words 同时完成适用的 fictional disclosure、buyer task、窄 ICP fit、explicit exclusion、buyer self-identification、first-round output 与 commitment boundary，且不重复完整 worksheet；
3. **Product decision map**：九段 `condition → variable → evidence → no-fit → remaining inputs → candidate-or-stop → candidate target → next-validation target → placement` 是否顺序可见；非 stop candidate 是否有真实 target；
4. **Role handoff**：七段 `from/to/url/retained task/receiving task/owner/acceptance evidence` 是否完整，目标页和 owner 是否真实接受任务；
5. **Technical vs sales**：technical-qualified 是否只基于技术输入，sales-accepted 是否同时满足商业意图、商业输入、sales owner 和商业下一步；
6. **搜索意图与扫读**：Title/H1 是否与 primary query、dominant action/object/output 和 stage 语义一致；non-Buy 是否排除 transactional modifier；H2/首屏/加粗是否帮助完成同一 buyer task；`hierarchy_scan_verdict` 是否被 fatal gate 消费，而不是机械堆叠关键词或粗体；
7. **SERP 形态与正文实现双闭环**：Production primary query 的 sample size、family counts、predeclared threshold、dominant family/count/verdict 是否独立成立；supporting query 是否只作旁证；该 dominant family、Brief/Draft `expected_content_type`、Review/Publish snapshot 与 `serp_content_type_parity_verdict` 是否逐层一致。Synthetic 或缺 dated primary-query SERP evidence 时 parity 必须为 `not-applicable`；无论 parity 是否适用，都要由独立 `body_content_family_implementation_verdict` 检查 marker 内真实正文是否实现声明的 checklist、comparison、calculator、diagnostic、case study 或 landing-page shape；不得 pooled 汇总或把任一 content family 偷换成 generic guide；
8. **CTA 全文一致性**：首个 H2 前、段落、列表、表格、strong、链接、按钮与全部动作词是否都进入 inventory，并与同一 17 段 fallback contract、各自 endpoint structured evidence、named owner、输入与 commitment boundary 一致；不得用最后一个 CTA 覆盖早期 unsafe route，也不得在 unverified route 中保留直接链接或 use/send 指令；
9. **决策与转化顺序**：`Hook → Diagnose → Decide → De-risk → Act` 与 primary/soft/fallback 三类 conversion surface 是否完整、按序、exact projection；
10. **移动可读性**：320px 决策表是否先采用可纵向阅读设计；没有真实 renderer/readability structured evidence 时是否保持 `not-run/missing/block` 与 production readiness BLOCK；
11. **可发布正文边界**：page-shell H1 metadata 与正文边界是否分开，是否只发布唯一 markers 内的 buyer-visible body，内部状态码、control record、placeholder、validator/release/renderer note 或正文 H1 是否泄漏。

### 14.1 Published lifecycle evidence binding

`publication_status: Published`、后台状态字符串、HTTP 200、toast 或单一截图均不能自证发布完成。Publish Record 必须逐轴记录 `publication_lifecycle_evidence_rows` 并由 `publication_lifecycle_evidence_verdict` 消费，八轴缺一即 BLOCK：`authorization`、`cms-mutation`、`backend-readback`、`editor-reopen`、`anonymous-frontend`、`desktop`、`mobile`、`image-fetch-decode`。

```text
axis|status|artifact-ref|sha256|site-id|record-id|url-or-image-url-or-not-applicable|producer-id|independent-reviewer-id|observed-at|reviewed-at|review-ceiling
```

Artifact digest 必须绑定真实 bytes；site/record/URL 必须锁定同一对象；producer/reviewer 必须是分离的 stable IDs；`observed-at <= reviewed-at <= review-ceiling`。任一轴 `not-run|missing|failed`、对象漂移、时间越界、digest 不匹配或 reviewer 不独立，都令 lifecycle verdict BLOCK。

## 15. 不承诺结果与独立前端 BLOCK

以下结果始终保持未验证，直到有真实站点数据：

- 排名与自然流量；
- 询盘量、询盘质量和 sales acceptance；
- 转化率、收入和成交周期。

禁止在 Title、meta description、excerpt、正文、CTA、Review 或 Publish Record 中声称或暗示结构优化会 `fill the sales pipeline`、带来 `ready-to-buy prospects`、把访客变成 `paying customers`、保证 customer acquisition、提升排名/流量/询盘/询盘质量/转化/收入，或使用任何等价结果保证。允许的表达只能是：帮助买家完成某个可观察任务、减少信息缺口、提高 packet 的可审查性，或“计划测量/可能影响”；实际效果保持 `unverified`，直到真实 observation window、metric definition、observed result、evidence refs 和 accountable reviewer 全部存在。

平台层前端边界项按 ⛔ 禁令不检查、不报告、不展开（见 RUNBOOK-ANYONE.md 顶部横幅）；不得由内容结构 PASS 代替，也不阻断本轮“B2B 内容合同 scope”完成。

正文图片的 **final DOM 空 alt** 仍是独立 renderer BLOCK。Markdown/Slate 中写了 alt 或媒体元数据，不等于 final DOM 已解决。

Source publication clearance 与 license status、候选冻结、CMS write/readback/editor-reopen/frontend acceptance、release approval、tag/push/publish 与 Stable/Published 状态也各自保持独立 BLOCK；文章结构或 synthetic fixture PASS 不得替代这些证据。

## 16. 当前兼容性边界

Standard、SOP、canonical templates、examples、validator、tests 与 workspace projection 必须在**同一候选、同次验证**中证明字段名、枚举值、阶段行为和 fatal-gate 语义一致。本页不宣称这些对象当前已经同步。

- 任一对象仍读取旧字段、把 `technical-review` 当商业承诺、统一强制 sales CTA/三类内链，或把 evidence status 与 gate verdict 混用，均为兼容性 BLOCK；
- validator PASS 只有在它覆盖本标准当前合同且同次 fixture/negative tests 通过时才有意义；
- 不得恢复旧 alias 或放宽 evidence gate 来制造兼容 PASS；
- production 发布必须等待同次合同一致性验证与真实 production evidence gate 对齐。
