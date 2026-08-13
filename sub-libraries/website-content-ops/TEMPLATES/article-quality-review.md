---
title: "Article Quality Review Template"
description: "用 fatal gate、结构评分与生产证据评分分离审查 English-only B2B SEO 文章的搜索意图、买家任务、阶段合同、决策证据、CTA、内链和发布边界。"
type: "template"
template_usage: "manual-copy"
status: "Working"
owner: "AI"
author_id: "replace-with-stable-person-id"
producer_id: "replace-with-stable-person-id"
independent_reviewer_id: "replace-with-different-stable-person-id"
remediation_participant_ids: []
identity_provenance_evidence_refs: []
identity_provenance_observed_at: "replace-with-ISO-8601-or-not-applicable"
identity_provenance_reviewed_at: "replace-with-ISO-8601-or-not-applicable"
identity_provenance_review_ceiling: "replace-with-ISO-8601-or-not-applicable"
reviewer_separation_verdict: "block"
created: "2026-07-31"
last_updated: "2026-08-11"
sources: ["../PLAYBOOKS/id-0001-b2b-seo-article-standard.md", "../PLAYBOOKS/id-0003-b2b-article-optimization-sop.md"]
related: ["article-brief.md", "article-draft.md", "publish-record.md", "../PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要独立审查文章是否完成一个真实英文买家任务，并把结构质量、生产证据、fatal gate 和 deferred 前端问题明确分开时。"
keywords: ["quality review", "fatal gate", "structure score", "production evidence", "search intent", "buyer task", "stage CTA", "B2B SEO"]
record_type: "article-quality-review"
package_id: "replace-with-shared-package-id"
brief_id: "replace-with-brief-id"
draft_id: "replace-with-draft-id"
review_id: "replace-with-review-id"
reviewer_identity: "replace-with-independent-reviewer"
reviewed_at: "replace-with-iso-datetime"
evidence_scope: "replace-with-synthetic-fixture-or-production"
evidence_origin: "replace-with-synthetic-fixture-test-fixture-or-live-production"
fixture_identity: "replace-with-concrete-fixture-id-or-not-applicable"
production_proof_eligible: false
content_action: "replace-with-create-update-merge-redirect-or-do-not-write"
icp_evidence_status_snapshot: "replace-with-confirmed-inferred-missing-conflicting-or-expired"
icp_evidence_refs_snapshot: []
icp_fit_contract_snapshot: "replace-with-company-fit-application-context-buying-condition-and-required-capability-to-act"
icp_exclusion_contract_snapshot: "replace-with-adjacent-audiences-applications-or-buying-conditions-this-article-must-not-attract"
seo_title_snapshot: "replace-with-exact-draft-article-title"
supported_content_languages: ["en"]
target_content_language: "en"
target_market: "replace-with-market"
language_gate_verdict: "block"
page_h1: "replace-with-exact-page-shell-h1"
primary_query: "replace-with-reviewed-primary-query"
supporting_query_variants: ["replace-with-reviewed-same-task-variant"]
secondary_intent_contracts: ["replace-with-supporting-query|replace-with-buyer-task|replace-with-exact-canonical-stage|replace-with-exact-canonical-commercial-commitment|replace-with-owner-page-or-this-article|replace-with-supports-or-delegated"]
excluded_query_modifiers: ["replace-with-reviewed-excluded-modifier"]
query_evidence_status: "missing"
query_evidence_refs: ["replace-with-query-task-and-query-boundary-evidence"]
buyer_task_evidence_status: "missing"
buyer_task_evidence_refs: []
customer_language_status: "missing"
customer_language_refs: []
customer_language_gate_verdict: "block"
pain_evidence_status: "missing"
pain_evidence_refs: []
pain_evidence_gate_verdict: "block"
search_demand_evidence_status: "missing"
search_demand_evidence_refs: []
search_demand_observation_start_at: "replace-with-ISO-8601-or-not-applicable"
search_demand_observation_end_at: "replace-with-ISO-8601-or-not-applicable"
buyer_language_seeds: ["replace-with-buyer-phrasing-seed"]
query_language_transformation_reason: "replace-with-preservation-or-normalization-reason"
intent_class: "replace-with-informational-troubleshooting-commercial-investigation-mixed-commercial-or-transactional"
stage: "replace-with-learn-troubleshoot-compare-validate-or-buy"
stage_intake_contract: "replace-with-none-troubleshoot-support-compare-handoff-validate-technical-or-buy-commercial"
dominant_search_intent: "replace-with-one-specific-intent"
dominant_task_contract: "replace-with-action|replace-with-object|replace-with-observable-output|replace-with-stage|replace-with-none-soft-or-commercial"
terminal_action_contract: "{{ action|decision-object|observable-output|stage|commercial-commitment }}"
first_round_expected_output: "packet completeness, missing-evidence list, and next review step"
candidate_decision_required_gates: ["{{ complete-second-round-package|not-applicable }}", "{{ named-technical-owner-review|not-applicable }}"]
first_round_output_candidate_gate_verdict: "block"
expected_content_type_snapshot: "replace-with-exact-brief-draft-expected-content-type"
content_family_matches: []
content_family_singleton_verdict: "block"
in_scope_questions: ["replace-with-question-this-page-must-answer"]
out_of_scope_questions: ["replace-with-question-owned-elsewhere"]
intent_completion_test: "replace-with-observable-reader-completion-test"
faq_applicability: "replace-with-applicable-or-not-applicable"
faq_trigger_type: "replace-with-dated-serp-pattern-documented-buyer-objection-documented-buyer-uncertainty-or-none"
faq_trigger_evidence_refs: []
faq_absence_reason: "replace-with-specific-reason-when-not-applicable"
faq_items: []
faq_decision_verdict: "block"
serp_content_type_parity_verdict: "pass|block|not-applicable"
body_content_family_implementation_verdict: "block"
cta_interaction_type: "replace-with-inline-no-input-local-tool-input-collecting-human-handoff-or-commercial"
cta_from_role: "replace-with-originating-role-or-not-applicable"
cta_to_role: "replace-with-receiving-role-or-not-applicable"
cta_receiving_task: "replace-with-receiving-task-or-not-applicable"
cta_receiving_owner: "replace-with-named-buyer-side-receiving-owner-or-not-applicable"
cta_destination: "replace-with-real-stage-appropriate-destination-or-not-applicable"
cta_owner: "replace-with-accountable-output-owner-or-not-applicable"
cta_value_exchange: "replace-with-buyer-visible-output"
cta_response_expectation: "replace-with-verified-timing-or-explicit-unknown-boundary"
cta_submission_method: "replace-with-form-email-approved-portal-or-existing-channel"
cta_confidentiality_or_data_boundary: "replace-with-what-not-to-submit-and-secure-channel-boundary"
cta_data_purpose: "replace-with-the-single-buyer-visible-purpose-for-collected-inputs-or-not-applicable"
cta_data_retention_period: "replace-with-a-bounded-retention-period-or-not-applicable"
cta_data_deletion_path: "replace-with-a-buyer-visible-deletion-or-withdrawal-path-or-not-applicable"
cta_data_retention_owner: "replace-with-accountable-role-or-not-applicable"
cta_data_policy_contract_id: "replace-with-stable-policy-contract-id-or-not-applicable"
cta_data_policy_status: "missing"
cta_data_policy_effective_at: "replace-with-YYYY-MM-DD-or-not-applicable"
cta_data_policy_checked_at: "replace-with-YYYY-MM-DD-or-not-applicable"
cta_data_policy_version: "replace-with-policy-version-or-not-applicable"
cta_data_policy_digest: "replace-with-sha256-or-not-applicable"
cta_data_policy_observed_at: "replace-with-ISO-8601-or-not-applicable"
cta_data_policy_reviewed_at: "replace-with-ISO-8601-or-not-applicable"
cta_data_policy_review_ceiling: "replace-with-ISO-8601-or-not-applicable"
cta_data_policy_owner_acceptance: "pending"
cta_data_policy_evidence_refs: []
cta_data_deletion_capability_evidence_refs: []
cta_collection_route_policy_contracts: ["replace-with-route-id|replace-with-endpoint|replace-with-required-inputs-mode|replace-with-data-purpose|replace-with-retention-period|replace-with-deletion-path|replace-with-retention-owner|replace-with-policy-contract-id|replace-with-policy-version|replace-with-policy-digest|replace-with-policy-checked-at|replace-with-policy-observed-at|replace-with-policy-reviewed-at|replace-with-policy-review-ceiling|replace-with-policy-status|replace-with-policy-owner-acceptance|replace-with-policy-evidence-refs|replace-with-deletion-capability-evidence-refs"]
local_preparation_purpose: "replace-with-buyer-local-preparation-purpose"
supplier_side_collection_purpose: "not-applicable-until-route-and-policy-gates-pass"
cta_collection_send_gate_verdict: "block"
cta_commitment_boundary: "replace-with-what-this-action-does-and-does-not-commit"
cta_fallback_route_contract: "replace-with-route-status|endpoint|owner|required-inputs-mode|commitment-boundary|reference-execution|reference-result|reference-verdict|reference-refs|reachability-execution|reachability-result|reachability-verdict|reachability-refs|capability-execution|capability-result|capability-verdict|capability-refs"
cta_buyer_visible_owner: "replace-with-buyer-facing-team-or-role"
cta_input_collection_applicability: "replace-with-applicable-or-not-applicable"
cta_input_collection_not_applicable_reason: "required-when-not-applicable-otherwise-use-not-applicable"
stage_link_requirement_status: "replace-with-applicable-or-not-applicable"
stage_link_not_applicable_reason: "required-when-not-applicable-otherwise-use-not-applicable"
pain_chain_contract: "actor|operating-event|evidence-gap|rework-mechanism|program-consequence|bounded-decision"
visible_pain_chain: ["Actor|replace-with-primary-actor", "Trigger|replace-with-operating-trigger", "Evidence gap|replace-with-missing-or-incomparable-evidence", "Rework|replace-with-repeat-work-caused-by-the-gap", "Consequence|replace-with-bounded-program-consequence", "Decision|replace-with-bounded-buyer-decision"]
visible_pain_chain_sequence_verdict: "block"
pain_trigger_snapshot: "replace-with-approved-trigger-event"
surface_problem_snapshot: "replace-with-approved-surface-problem"
operational_friction_snapshot: "replace-with-approved-operational-friction"
business_consequence_snapshot: "replace-with-approved-business-consequence"
desired_decision_snapshot: "replace-with-approved-bounded-decision"
product_decision_map_snapshot: []
internal_link_targets_snapshot: []
internal_link_plan_status: "missing"
buyer_visible_internal_link_count: 0
buyer_visible_internal_links_status: "replace-with-present-absent-until-gates-pass-or-missing"
buyer_visible_internal_links_absence_reason: "replace-with-specific-reason-when-links-are-withheld"
buyer_visible_internal_links_verdict: "pass|block|not-applicable"
cta_required_inputs_snapshot: []
direct_answer_action: "replace-with-reader-action"
direct_answer_object: "replace-with-decision-object"
direct_answer_condition_or_boundary: "replace-with-applicability-condition-or-boundary"
direct_answer_evidence_boundary: "replace-with-evidence-boundary-including-what-is-not-proven"
direct_answer_required_inputs_or_evidence: ["replace-with-minimum-input-or-evidence"]
direct_answer_expected_output_or_route: "replace-with-bounded-output-or-next-route"
first_round_inquiry_inputs: []
first_round_input_specifications: []
cta_buyer_visible_capability_proofs: []
second_round_inquiry_inputs: []
second_round_input_relationships: []
technical_qualification_requirement: "not-applicable"
technical_qualification_contract_status: "not-applicable"
technical_qualification_gates: []
technical_qualification_definition: "not-applicable"
technical_qualification_owner: "not-applicable"
technical_qualification_next_step: "not-applicable"
sales_acceptance_requirement: "not-applicable-without-explicit-commercial-intent"
sales_acceptance_contract_status: "conditional-on-explicit-commercial-intent"
sales_acceptance_gates: ["explicit-commercial-intent", "commercial-qualification-required", "commercial-inputs-complete", "named-commercial-owner-reviewed-and-accepted"]
sales_acceptance_definition: "sales-accepted requires explicit-commercial-intent, commercial-qualification-required, commercial-inputs-complete, and named-commercial-owner-reviewed-and-accepted"
sales_commercial_intent_required: "explicit price, quote, RFQ, purchasing timeline, order, supplier-selection, or supplier-award intent"
sales_acceptance_owner: "replace-with-stable-commercial-owner-id-or-person-name-comma-role"
sales_acceptance_next_step: "perform commercial qualification or RFQ review without treating technical readiness as sales acceptance"
disqualifiers: ["evidenced incompatibility|record evidence and stop or redirect the technical path","evidenced out-of-envelope result|record evidence and stop or redirect the technical path","explicitly unsupported scope|record evidence and stop or redirect to supported scope"]
qualification_reason_codes: []
commercial_commitment: "replace-with-none-soft-or-commercial"
serp_evidence_ref: "replace-with-dated-query-market-language-device-result-type-evidence"
serp_primary_query: "replace-with-exact-primary-query"
serp_primary_query_sample_size: "not-run"
serp_primary_query_result_type_counts: []
serp_primary_query_dominant_result_type: "not-run"
serp_primary_query_dominant_result_count: "not-run"
serp_primary_query_dominance_threshold: "not-run"
serp_primary_query_dominance_verdict: "block"
serp_supporting_query_result_type_rows: []
article_decision_sequence_map: ["hook|replace-with-complete-buyer-visible-trigger-or-direct-answer|replace-with-opening-location","diagnose|replace-with-cause-evidence-gap-and-consequence|replace-with-diagnosis-location","decide|replace-with-bounded-candidate-stop-or-next-decision|replace-with-decision-location","de-risk|replace-with-assumptions-no-fit-proof-and-validation-boundary|replace-with-risk-location","act|replace-with-one-bounded-next-action-and-observable-output|replace-with-final-action-location"]
article_decision_sequence_verdict: "block"
conversion_surface_map: ["{{ primary-surface-id }}|primary|replace-with-main-stage-outcome|replace-with-location-or-locator|replace-with-interaction|replace-with-route-id-or-not-applicable","{{ soft-surface-id }}|soft|replace-with-lower-friction-preparation-or-self-check|replace-with-location-or-locator|replace-with-interaction|replace-with-route-id-or-not-applicable","{{ fallback-surface-id }}|fallback|replace-with-safe-no-send-route-recovery|replace-with-location-or-locator|replace-with-interaction|replace-with-route-id-or-not-applicable"]
cta_measurement_map: ["{{ primary-surface-id }}|primary|{{ page-version }}|{{ primary-cta-version }}|{{ primary-start-event }}|{{ primary-submit-event }}|{{ primary-success-event }}|{{ primary-failure-event }}|{{ primary-abandonment-definition }}|{{ primary-qualification-event-or-not-applicable }}|{{ primary-commercial-acceptance-event-or-not-applicable }}|{{ analytics-data-source }}|{{ baseline-window }}|{{ observation-window }}|{{ accountable-owner }}|{{ evidence-ref }}", "{{ soft-surface-id }}|soft|{{ page-version }}|{{ soft-cta-version }}|{{ soft-start-event }}|{{ soft-submit-event }}|{{ soft-success-event }}|{{ soft-failure-event }}|{{ soft-abandonment-definition }}|not-applicable|not-applicable|{{ analytics-data-source }}|{{ baseline-window }}|{{ observation-window }}|{{ accountable-owner }}|{{ evidence-ref }}", "{{ fallback-surface-id }}|fallback|{{ page-version }}|{{ fallback-cta-version }}|{{ fallback-start-event }}|{{ fallback-submit-event }}|{{ fallback-success-event }}|{{ fallback-failure-event }}|{{ fallback-abandonment-definition }}|not-applicable|not-applicable|{{ analytics-data-source }}|{{ baseline-window }}|{{ observation-window }}|{{ accountable-owner }}|{{ evidence-ref }}"]
conversion_measurement_plan_status: "planned"
measurement_window: "replace-with-observation-window"
cta_abandonment_measurement_status: "planned"
cta_abandonment_measurement_refs: ["replace-with-local-measurement-plan-ref"]
cta_measurement_plan_verdict: "block"
buyer_visible_cta_inventory: ["primary-replace-with-stable-id|replace-with-location-kind|replace-with-unique-visible-locator|replace-with-one-exact-buyer-visible-instruction|replace-with-https-destination-or-not-applicable|replace-with-stable-owner|replace-with-interaction-type|replace-with-verified-unverified-unavailable-or-not-applicable|replace-with-evidence-bundle-ref-or-not-applicable|replace-with-cta_fallback_route_contract-or-not-applicable", "soft-replace-with-stable-id|replace-with-location-kind|replace-with-unique-visible-locator|replace-with-one-exact-buyer-visible-instruction|replace-with-https-destination-or-not-applicable|replace-with-stable-owner|replace-with-interaction-type|replace-with-verified-unverified-unavailable-or-not-applicable|replace-with-evidence-bundle-ref-or-not-applicable|replace-with-cta_fallback_route_contract-or-not-applicable", "fallback-replace-with-stable-id|replace-with-location-kind|replace-with-unique-visible-locator|replace-with-one-exact-buyer-visible-instruction|replace-with-https-destination-or-not-applicable|replace-with-stable-owner|replace-with-interaction-type|replace-with-verified-unverified-unavailable-or-not-applicable|replace-with-evidence-bundle-ref-or-not-applicable|replace-with-cta_fallback_route_contract-or-not-applicable"]
cta_transmission_action_inventory: []
conversion_surface_map_verdict: "block"
serp_format_evidence_status: "missing"
serp_format_evidence_refs: []
production_search_evidence_gate_verdict: "block"
query_contract_verdict: "block"
dominant_task_verdict: "block"
stage_contract_verdict: "block"
title_primary_query_parity_verdict: "block"
title_dominant_task_parity_verdict: "block"
title_stage_parity_verdict: "block"
h1_title_task_parity_verdict: "block"
title_slug_stage_parity_verdict: "block"
publishable_body_boundary_verdict: "block"
stage_intake_contract_verdict: "block"
buyer_visible_editorial_language_verdict: "block"
internal_control_term_leakage_verdict: "block"
cta_value_exchange_verdict: "block"
soft_path_route_safety_verdict: "block"
all_buyer_visible_cta_sections_evidence_parity_verdict: "block"
cross_cta_instruction_consistency_verdict: "block"
product_link_claim_parity_verdict: "block"
visual_decision_assets_verdict: "block"
direct_answer_six_slot_verdict: "block"
six_node_causal_chain_verdict: "block"
buyer_role_scope_verdict: "block"
primary_buyer_role: "replace-with-reviewed-primary-role"
secondary_buyer_roles: []
secondary_buyer_role_contracts: []
cross_role_delegation_verdict: "not-applicable"
cannibalization_verdict: "block"
inventory_zero_result_evidence_refs: []
role_handoff_contracts: []
information_gain_artifact_status: "missing"
information_gain_artifact_refs: []
market_information_gain_status: "missing"
information_gain_market_refs: []
information_gain_artifact_verdict: "block"
information_gain_market_verdict: "block"
product_decision_map_verdict: "block"
product_link_evidence_level: "replace-with-none-family-level-or-sku-level"
visual_decision_assets: ["replace-with-asset_type|buyer_task_supported|claim_supported|evidence_ref|placement_after_section|caption|alt_intent|mobile_readability_requirement|required-optional-or-not-applicable"]
mobile_visual_check_execution_status: "not-run"
mobile_visual_evidence_result: "missing"
mobile_visual_gate_verdict: "block"
mobile_visual_evidence_refs: []
hierarchy_scan_verdict: "block"
semantic_emphasis_verdict: "block"
section_information_gain_verdict: "block"
normalized_field_set_redundancy_verdict: "block"
internal_link_stage_contract_verdict: "block"
cta_stage_contract_verdict: "block"
technical_qualification_verdict: "not-applicable"
sales_acceptance_verdict: "not-applicable"
unsupported_outcome_claims_verdict: "block"
internal_link_reference_check_execution_status: "not-run"
internal_link_reference_evidence_result: "missing"
internal_link_reference_gate_verdict: "block"
internal_link_reachability_check_execution_status: "not-run"
internal_link_reachability_evidence_result: "missing"
internal_link_reachability_gate_verdict: "block"
internal_link_capability_check_execution_status: "not-run"
internal_link_capability_evidence_result: "missing"
internal_link_capability_gate_verdict: "block"
cta_reference_check_execution_status: "not-run"
cta_reference_evidence_result: "missing"
cta_reference_gate_verdict: "block"
cta_reference_evidence_refs: []
cta_reachability_check_execution_status: "not-run"
cta_reachability_evidence_result: "missing"
cta_reachability_gate_verdict: "block"
cta_reachability_evidence_refs: []
cta_capability_check_execution_status: "not-run"
cta_capability_evidence_result: "missing"
cta_capability_gate_verdict: "block"
cta_capability_evidence_refs: []
structure_score: 0
structure_score_max: 100
production_evidence_score: "not-applicable"
production_evidence_score_max: 100
fatal_gate_verdict: "block"
structure_review_verdict: "block"
production_evidence_review_verdict: "block"
production_readiness: "block"
production_readiness_scope: "cms-draft-content-contract"
release_decision: "blocked"
operation_mode: "not-run"
overall_verdict: "block"
cta_route_transmission_verdict: "block"
frontend_deferred_blocks: ["html-lang", "canonical", "article-json-ld"]
html_lang_status: "deferred-block"
canonical_status: "deferred-block"
article_json_ld_status: "deferred-block"
final_dom_image_alt_renderer_status: "block"
actual_ranking_status: "unverified"
actual_inquiry_status: "unverified"
actual_sales_acceptance_status: "unverified"
actual_conversion_status: "unverified"
actual_outcome_observation_window: "not-applicable"
actual_outcome_metric_or_event_definition: "replace-with-metric-or-event-definition-when-status-is-not-unverified-otherwise-not-applicable"
actual_outcome_observed_result: "replace-with-observed-result-when-status-is-not-unverified-otherwise-not-applicable"
actual_outcome_evidence_refs: []
actual_outcome_accountable_reviewer: "not-applicable"
actual_sales_acceptance_evidence_refs: []
---
# Article Quality Review

> Canonical projection contract: `content_action`、`page_h1`、`dominant_search_intent`、`content_family_matches`、`content_family_singleton_verdict`、customer-language/pain status+refs+gate、`evidence_origin`、`fixture_identity`、`production_proof_eligible`、`cta_transmission_action_inventory`、`cta_collection_route_policy_contracts`、`section_information_gain_verdict` 与 `normalized_field_set_redundancy_verdict` 必须与其余三记录逐字符一致，不得使用 snapshot alias 或省略。Production 只允许 `live-production + fixture_identity=not-applicable + production_proof_eligible=true`，并要求 customer language 与 pain evidence 都是 `confirmed + 非空 refs + gate pass`；synthetic/test fixture 必须 `production_proof_eligible=false`，不能成为 production proof。

> `secondary_intent_contracts` 每行严格六槽：stage 等于 canonical `stage`，commitment 从 `none|soft|commercial` 取值且等于 canonical `commercial_commitment`；`supports` 必须由 `this-article` 承接，`delegated` 必须指向不同的非 `this-article` owner page。supporting query/task 只能支持 dominant task，不得污染 dominant intent；非 Buy 不得扩张为 terminal commercial action。FAQ trigger 只允许 `dated-serp-pattern|documented-buyer-objection|documented-buyer-uncertainty|none`；applicable row 只允许 `question|buyer_job|objection_or_uncertainty|evidence_ref_or_explicit_inferred_boundary|article_owned_answer`。

> Internal-link fail-closed: `stage_link_requirement_status=applicable` 且正文 link 被 withheld/数量为 0 时，`buyer_visible_internal_links_verdict` 必须为 `block`，不得用 `not-applicable` 掩盖。Positive fixture 必须有真实 buyer-visible Markdown link 与完整 reference/reachability/capability/target-acceptance gate；synthetic placeholder 永远不是 Production proof。

> CTA collection policy uses one 18-slot row per actually collecting verified endpoint: `route-id|endpoint|required-inputs-mode|data-purpose|retention-period|deletion-path|retention-owner|policy-contract-id|policy-version|policy-digest|policy-checked-at|policy-observed-at|policy-reviewed-at|policy-review-ceiling|policy-status|policy-owner-acceptance|policy-evidence-refs|deletion-capability-evidence-refs`. Primary/fallback 各自绑定，`required-inputs-mode=none` 不触发。旧 `cta_data_*` 仅可作为 primary collecting row 的 exact projection，不是第二真源。Local preparation 与 supplier-side collection 必须分开；destination/reference/reachability/capability/policy/retention/deletion/owner 未全部确认前，只能本地准备并请求 verified route plus data-policy details，不得发送。

> Body anti-repetition: 完整 first-round field set、units、formats 与 examples 只能存在于唯一 worksheet；仅当无 worksheet 时才允许唯一 copyable fallback，二者不得同时列全集。Decision artifact 使用纵向 H3/definition-like blocks、key-value stack 或最多两列；opening、preparation、final CTA 与 fallback 只引用 worksheet。六个 pain-chain label 必须按固定编号、加粗、唯一且有序地出现在正文，并进入 `semantic_emphasis_plan`；自然行业化表达写在 label 之后。

> Canonical schema parity: `stage_required_link_roles` emits only `hub|product|solution|educational|comparison|diagnostic|support|technical-review|conversion|commercial`. `secondary_buyer_role_contracts` uses `role|evidence_ref|concrete_objection|article_owned_answer`, with exactly one row per secondary role; `buyer_role_matrix` is retired/forbidden. A cross-role `human-handoff` or `commercial` CTA must match exactly one `role_handoff_contracts` row on from/to/url/receiving task/buyer-side receiving owner; otherwise all four CTA role fields use `not-applicable`. Production SERP-format evidence lives in an independent fragment with flat query-set/market/language/device/date/result-type fields; this record only binds it through `serp_format_evidence_refs` and never embeds a nested frontmatter object.

> Four-record exact projection: Brief, Draft, Review and Publish Record must carry byte-for-byte identical `page_h1`, `terminal_action_contract`, `first_round_expected_output`, `candidate_decision_required_gates`, and `first_round_output_candidate_gate_verdict`. `validate-technical` uses only the exact scalar `packet completeness, missing-evidence list, and next review step`; every other branch uses only `not-applicable`. Any drift, missing field, or non-`block` first-round candidate verdict is fatal. `terminal_action_contract` is the bounded end-state action and must not be replaced by the fallback request for a verified route.


## Stage-intake field conditions

Populate intake and qualification fields only after selecting `stage_intake_contract`; unused arrays remain `[]` and unused scalar qualification fields remain `not-applicable`.

| `stage_intake_contract` | `first_round_inquiry_inputs` / `cta_required_inputs` | `second_round_inquiry_inputs` + relationships | Qualification boundary |
|---|---|---|---|
| `none` | `[]` | `[]` | No intake and no qualification rows. |
| `troubleshoot-support` | One minimal diagnostic/support packet; both arrays match exactly | `[]` | Conditional only when a real support team accepts the diagnostic handoff; otherwise Troubleshoot uses `none`. Never the Validate technical lifecycle. |
| `compare-handoff` | One evidence-backed minimal handoff packet; both arrays match exactly | `[]` | Conditional only with dated `mixed-commercial` evidence and a real receiving task; otherwise Compare uses `none`. No technical qualification. |
| `validate-technical` | 4–6 minimum engineering inputs; both arrays match exactly | Populate both arrays and one exact relationship row per second-round item | This is the only branch that may populate two-round technical gates and `technical_qualification_*`. |
| `buy-commercial` | One independent RFQ/commercial packet; both arrays match exactly | `[]` | Use commercial owner and commercial states; do not inherit `technical-qualified`. |

`qualification_reason_codes` contains only states legal for the selected branch. Never copy the full Validate lifecycle into Learn, Troubleshoot, Compare, or Buy.

For every applicable input-collecting CTA, `first_round_input_specifications` (or the Publish snapshot) must contain exactly one row per first-round input using:

```text
input | why-needed | accepted-unit-or-format | example | required-or-conditional | confidentiality-boundary
```

The buyer-facing CTA must show these units/formats and an example in a scan-friendly list or table. `cta_buyer_visible_capability_proofs` (or the Publish snapshot) uses `proof-type|buyer-task-supported|claim-or-boundary|evidence-ref|buyer-visible-copy|required-or-not-applicable`. Input-collecting, human-handoff, and commercial CTAs require at least one task-specific proof such as a review method, redacted sample output, test capability, sourced case/certification, or explicit capability boundary. A generic brand slogan is not proof.

## 1. Review identity and evidence boundary

- Package / Brief / Draft:
- Reviewer and independence statement:
- Review timestamp:
- Evidence scope: synthetic fixture / production
- Target content language: `en`
- Target market:
- Evidence refs reviewed:

If the target article is not English, stop and route it to human language review. A market field does not satisfy the language gate.

A synthetic fixture may receive a structure verdict, but `production_evidence_score` must be `not-applicable` and its production evidence verdict must remain BLOCK. Do not convert fixture shape, reserved URLs, author assertions, HTTP 200 or CMS success messages into production evidence PASS.

## 2. Top-level verdict

- Fatal gate verdict: pass / block
- Structure score: /100
- Production evidence score: /100 / not-applicable
- Overall verdict: pass / block
- Release recommendation: do-not-write / revise / ready-for-draft / ready-for-production-verification / ready-for-approved-publish

**Fatal gate precedence:** any applicable fatal gate at BLOCK forces `overall_verdict: block`, regardless of either score.

## 3. Fatal gates

Missing buyer-visible ICP fit/exclusion before the first H2, failure of buyer self-identification, an omitted buyer-visible transfer/control action, a complete input set repeated outside the single preferred worksheet, both a worksheet and fallback listing the complete set, a complete fallback used when a worksheet exists, or either `section_information_gain_verdict` / `normalized_field_set_redundancy_verdict` being `block` is fatal. A single complete fallback is allowed only when no worksheet exists. Force `fatal_gate_verdict=block`, `overall_verdict=block`, and `production_readiness=block`; no status string overrides these findings.


| Gate | PASS condition | Result | Evidence / finding |
|---|---|---|---|
| English-only language | `target_content_language=en`; non-English is routed to human review |  |  |
| Query/task parity | Primary query, same-task variants, intent class, stage and SERP format describe one task |  |  |
| Dominant buyer task | Exactly one `action / object / observable output / stage / commercial commitment`; commitment is exactly one of `none|soft|commercial`, while technical review stays in CTA/action/output |  |  |
| Stage contract | Reader outcome, CTA, links and qualification match `learn|troubleshoot|compare|validate|buy` |  |  |
| Six-slot opening answer | Before the first H2, an approximately 120–140-word opening answer preserves applicable fictional/synthetic disclosure, buyer task, narrow ICP fit, exclusion, self-identification, first-round output and commitment boundary while completing action, object, required inputs/evidence, condition/boundary, expected output/route and evidence boundary; no fixed visible label is required |  |  |
| Six-slot causal chain | Actor → operating event → evidence gap → rework mechanism → program consequence → bounded decision is specific and evidenced |  |  |
| Cannibalization | `clear` has dated snapshot plus zero-result evidence, or `resolved` has one-to-one candidate separation |  |  |
| Product decision | Nine-part map is visible; non-stop candidate has a real product/solution/hub target |  |  |
| Stage intake and CTA contract | `stage_intake_contract` matches the stage; applicable intake surfaces align; `second_round_input_relationships` declares each new or summary-to-detail refinement without requesting the same value twice |  |  |
| Four-record exact projection | `page_h1`, `terminal_action_contract`, `first_round_expected_output`, `candidate_decision_required_gates`, and `first_round_output_candidate_gate_verdict` are byte-for-byte identical across all four records; Validate uses the exact three-part output scalar, non-Validate uses `not-applicable`, and verdict remains `block` for first-round candidate output |  |  |
| Validate candidate gate | First round returns only packet completeness, missing-evidence list and next review step; `candidate-or-stop` appears only after a complete second-round package and named technical-owner review |  |  |
| CTA route/policy safety | Fallback route request is separate from terminal action; any route or policy BLOCK forbids submit/send/email/upload/share/transmit instructions and permits only local save plus a request for a verified route |  |  |
| Evidence axes | Every production-applicable axis is `executed + confirmed + pass` |  |  |
| Qualification separation | Technical-qualified is not treated as sales-accepted; sales acceptance has commercial intent, owner and next step |  |  |
| Unsupported outcomes | No promise of ranking, inquiry, sales acceptance, revenue or conversion lift |  |  |

## 4. Query and search-intent attack

### Query contract

Attack `query_evidence_status` and every `query_evidence_ref`; an inferred or synthetic query contract cannot become production acceptance.

- Primary query:
- Supporting variants:
- Excluded modifiers and their owner pages:
- Intent class:
- Decision stage:
- Expected content type:
- Dated SERP evidence ref:

Adversarial questions:

- Does each supporting variant complete the same action, object and observable output?
- Did a price, MOQ, definition, troubleshooting, validation or RFQ modifier silently introduce a different stage?
- Does the direct answer solve the search task rather than merely repeat query words?
- Is the SERP evidence bound to market, language, device, date and result type?
- Is low-confidence semantic matching routed to a human rather than passed by token overlap?

### Conditional FAQ attack

- FAQ applicability: applicable / not-applicable
- Trigger type: SERP/query pattern / buyer objection / not-applicable
- Trigger evidence refs or absence reason:
- If absent with no eligible trigger, confirm absence is valid and apply no score penalty: pass / block

If FAQ is present, review every row as:

```text
question | buyer_job | objection_or_uncertainty | evidence_ref_or_explicit_inferred_boundary | article_owned_answer | reviewer_result
```

Adversarial checks:

- Does each buyer job match the dominant buyer task or an evidenced secondary buyer task, without introducing another stage or commercial commitment?
- Is each objection/uncertainty specific, and is the answer genuinely owned by this article rather than another owner page or CTA destination?
- Does each production factual answer bind evidence; where the row is inferred, does it explicitly state the basis and non-generalization boundary without claiming confirmation?
- Does any question merely restate the body, repeat a synonymous keyword variant, or exist only because FAQ is treated as an SEO best practice?
- Do multiple questions stack keywords while producing the same buyer output? If yes, treat this as keyword stuffing and merge or remove them.

A present FAQ cannot pass this review when buyer-job parity, evidence/inferred boundary, article ownership, or keyword-stuffing checks fail. A missing FAQ with no eligible trigger is `not-applicable`, not a defect.

Verdict and repair:

## 5. Dominant buyer task and intent completion

```text
action | object | observable output | stage | commercial commitment
```

- In-scope questions all support the dominant task: pass / block
- Out-of-scope questions are delegated to owner pages: pass / block
- Completion test is observable: pass / block
- The page avoids two competing primary stages: pass / block

Verdict and repair:

## 6. Six-slot causal-chain review

| Node | Specific actor/object/condition | Evidence | Causal link to next node | pass/block |
|---|---|---|---|---|
| Actor |  |  |  |  |
| Operating event |  |  |  |  |
| Evidence gap |  |  |  |  |
| Rework mechanism |  |  |  |  |
| Program consequence |  |  |  |  |
| Bounded decision |  |  |  |  |

BLOCK generic claims such as “improve efficiency,” “reduce cost” or “ensure quality” unless the article names the operating condition, bounded mechanism and evidence. Confirm that one dedicated buyer-visible pain H2 contains exactly six consecutive, case-sensitive Markdown lines using `1. **Actor:**` through `6. **Decision:**`, with no missing bold markers, label drift, alternate numbering, duplication, reordering or projection drift. Do not require fabricated loss numbers to make the pain appear concrete.

## 7. Direct answer, hierarchy and scanning

| Check | Expected | Result | Repair |
|---|---|---|---|
| Six-slot coherence | Action + object + required inputs/evidence + condition/boundary + expected output/route + evidence boundary are connected as one answer |  |  |
| Opening self-identification | Before the first H2, about 120–140 English words naturally include disclosure when applicable, buyer task, narrow ICP fit, explicit exclusion, first-round output and commitment boundary |  |  |
| Buyer exit path | The target buyer can self-identify immediately and excluded audiences or buying conditions can exit without reading the body |  |  |
| Placement | The full six-slot direct answer remains inside the pre-H2 opening |  |  |
| Visible label | No fixed `Direct answer:` label is required; buyer-readable prose is preferred |  |  |
| Page-shell H1 | One CMS/page-shell H1 matching the completed task; no H1 inside the bounded publishable body |  |  |
| H2 | Decision-led, mutually useful path |  |  |
| H3 | Supports its parent H2 |  |  |
| Lists/tables | Used when they reduce decision effort |  |  |
| Semantic strong | Complete judgment bound to a decision-scanning role |  |  |
| Exclusions | No decorative keyword bolding or whole-paragraph bolding |  |  |

Semantic emphasis grammar:

```text
condition|risk|evidence|no-fit|boundary|action|decision | complete judgment | placement
```

## 8. Buyer-role lenses and delegation

### Primary buyer contract

- Required primary role:
- Concrete objection:
- Article-owned answer:
- Evidence:

### Evidence-based secondary roles

Secondary roles are optional. For each included role, verify:

```text
role | evidence_ref | concrete objection | article-owned answer
```

### Reviewer lenses

Use these to attack omissions; do not force all four into the article:

- Engineer lens: feasibility, conditions, measurements and failure modes.
- Quality lens: evidence, repeatability, acceptance and traceability.
- Procurement lens: comparability, supplier inputs and commercial readiness.
- Management lens: bounded consequence, risk ownership and decision path.

### Cross-role delegation

Every delegation must bind:

```text
from_role | to_role | url | retained_task | receiving_task | owner | acceptance_evidence_ref
```

Verdict and repair:

## 9. Inventory and cannibalization

- Owner page:
- Inventory snapshot / checked at:
- Status: clear / resolved / unresolved

For `clear`:

- Zero candidates are allowed.
- Inventory snapshot and explicit zero-result evidence are mandatory.

For `resolved`:

- Every candidate must have one matching separation row.
- Each row must state owner task, candidate task and non-overlap boundary.

For `unresolved`: overall verdict remains BLOCK.

## 10. Information gain and product decision

### Information gain

| Dimension | Status | Evidence | pass/block |
|---|---|---|---|
| Artifact exists and is usable | `missing` / `inferred` / `confirmed` / `confirmed-for-fixture-structure` |  |  |
| Market difference is evidenced | `missing` / `inferred` / `confirmed` / `not-applicable` |  |  |

A synthetic checklist, calculator, matrix or diagram can pass artifact structure but cannot prove market difference.

### Nine-part product decision map

| Condition | Variable | Evidence | No-fit | Remaining inputs | Candidate or stop | Candidate target | Next-validation target | Placement | pass/block |
|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |

For `validate-technical`, first-round output is limited to packet completeness, missing-evidence list and next review step. Do not emit `candidate-or-stop` from the first round. A non-stop candidate is legal only after both `complete-second-round-package` and `named-technical-owner-review` are evidenced; then confirm the target is a real product, solution or task-accepting hub and appears visibly where declared. Missing inputs must appear under `remaining inputs` and route to `needs-follow-up`; no-fit may contain only evidenced incompatibility, out-of-envelope results or unsupported scope.

## 11. Stage-specific article, CTA and link review

First confirm `stage_link_requirement_status`. If it is `not-applicable`, require a specific in-page-completion reason and reject links added only to meet a quota. If it is `applicable`, check the Standard's `required_when_applicable` role separately from merely `allowed` roles.

Then review the branch selected by `stage_intake_contract`:

| Branch | Required review |
|---|---|
| `none` | All intake, second-round, destination and qualification arrays are empty; the CTA closes locally without pretending a human response. |
| `troubleshoot-support` | One minimal diagnostic packet, real support destination/owner, no second round and no technical qualification lifecycle. |
| `compare-handoff` | Evidence-backed minimal handoff only; no technical-qualified language or Validate-stage packet. |
| `validate-technical` | 4–6 first-round inputs, exact CTA parity, complete second-round relationships, named technical owner and bounded technical output. |
| `buy-commercial` | Independent RFQ/commercial packet, named commercial owner, no inherited technical-qualified state. |

For every applicable CTA, verify that the actual CTA section—not scattered prose—shows `cta_value_exchange`, `cta_response_expectation`, `cta_submission_method`, `cta_confidentiality_or_data_boundary`, `cta_commitment_boundary`, and `cta_buyer_visible_owner`. Unknown timing or confidentiality capability must be stated as a boundary, not invented. `terminal_action_contract` remains the bounded end-state action; a fallback request for a verified route is a separate recovery action. If route or collection-policy evidence is BLOCK, buyer-visible copy must not instruct submit, send, email, upload, share, transmit or equivalent delivery; it may only instruct local save and requesting a verified route through the approved supplier-contact process.

Verify inferred or synthetic pain uses only bounded `may`, `can`, or `risks` wording; unsupported `must` or `will` causal claims are fatal. Verify `product_link_evidence_level`: `none` rejects product/solution claims; `family-level` permits only a solution family/category and unresolved narrowing conditions; `sku-level` requires condition-to-spec evidence and target-page claim parity. Verify each required `visual_decision_assets` row supports the dominant task, points to evidence and a real placement, and is usable on mobile.

## 12. Qualification and commercial routing

`qualification_reason_codes` must contain only states legal for the selected branch and use `state|cause-category|evidence-rule|owner|next-step`. Only `validate-technical` may use the two-round technical lifecycle. Only `buy-commercial` or an explicitly evidenced commercial route may use commercial qualification/acceptance, and sales acceptance requires the named commercial owner's review. Internal states must remain outside the publishable body.

## 13. Three-axis evidence review

| Object / axis | Check execution status | Evidence result | Gate verdict | Evidence refs | Reviewer result |
|---|---|---|---|---|---|
| Internal link / reference parity |  |  |  |  |  |
| Internal link / reachability |  |  |  |  |  |
| Internal link / capability / task acceptance |  |  |  |  |  |
| CTA / reference parity |  |  |  |  |  |
| CTA / reachability |  |  |  |  |  |
| CTA / capability |  |  |  |  |  |

Allowed state model:

```text
check_execution_status: not-run | executed | not-applicable
evidence_result: missing | synthetic-only | confirmed | failed | not-applicable
gate_verdict: pass | block | not-applicable
```

A production-applicable `pass` requires `executed + confirmed + pass`. Missing/not-run is never `pass`. A complex table cannot receive mobile usability PASS without real 320px renderer/readability evidence. Mobile evidence uses only `evidence_kind=mobile-readability`, `check_id=mobile-readability`, `target_task`, `accountable_owner`, `viewport_width_px=320`, `render_target`, `method`, `observed_result`, `acceptance_criteria`, `capability_acceptance`, and `screenshot_or_trace_ref`; `mobile-visual` and `viewport_width` are forbidden aliases.

## 14. Scoring

### Structure score — 100 points

| Dimension | Weight | Score | Notes |
|---|---:|---:|---|
| Query, dominant task and stage parity | 25 |  |  |
| Direct answer and six-slot causal contract | 20 |  |  |
| Hierarchy, scanning and semantic emphasis | 15 |  |  |
| Buyer scope, delegation and cannibalization | 15 |  |  |
| Product map, stage CTA and stage links | 25 |  |  |

### Production evidence score — 100 points or not-applicable

| Dimension | Weight | Score | Notes |
|---|---:|---:|---|
| Dated SERP, demand and inventory evidence | 25 |  |  |
| Customer/pain and first-party proof | 20 |  |  |
| Information-gain market evidence | 15 |  |  |
| Product/link/CTA reference and reachability | 20 |  |  |
| Capability, ownership and publication evidence | 20 |  |  |

Do not average structure and production evidence into a `pass` when a fatal gate is `block`. All verdicts are closed to `pass|block|not-applicable`; the two map verdicts, `hierarchy_scan_verdict`, and `semantic_emphasis_verdict` are fatal, and any applicable `block` forces fatal/overall/production readiness to `block`. For synthetic fixtures, use `production_evidence_score: not-applicable`.

## 15. Findings

### P0 / fatal

- Finding:
- Exact path/section:
- Risk:
- Executable repair:

### P1

- Finding:
- Exact path/section:
- Risk:
- Executable repair:

### P2

- Finding:
- Exact path/section:
- Risk:
- Executable repair:

### P3

- Finding:
- Exact path/section:
- Risk:
- Executable repair:

## 16. Non-claims and deferred blocks

This review does not verify or promise actual ranking, organic traffic, inquiries, sales acceptance, revenue or conversion lift. The canonical status enums are closed:

```text
actual_ranking_status: unverified | not-applicable | observed-no-improvement | observed-improvement
actual_inquiry_status: unverified | not-applicable | observed-no-improvement | observed-improvement
actual_conversion_status: unverified | not-applicable | observed-no-improvement | observed-improvement
actual_sales_acceptance_status: unverified | not-applicable | not-accepted | sales-accepted
```

Any `observed-no-improvement`, `observed-improvement`, `not-accepted`, or `sales-accepted` result requires a dated `actual_outcome_observation_window`, a concrete `actual_outcome_metric_or_event_definition`, a factual `actual_outcome_observed_result`, non-empty `actual_outcome_evidence_refs`, and an identifiable `actual_outcome_accountable_reviewer`. `actual_sales_acceptance_status: sales-accepted` additionally requires non-empty `actual_sales_acceptance_evidence_refs`, affirmative evidence for every canonical sales-acceptance gate, complete commercial inputs, and evidence that the named canonical commercial owner reviewed and accepted the opportunity. Otherwise fail closed and make no outcome claim.

Do not treat content review as closure for these independent blocks:

- HTML `lang` — deferred frontend SEO BLOCK;
- canonical — deferred frontend SEO BLOCK;
- Article JSON-LD — deferred frontend SEO BLOCK;
- final DOM image alt — independent renderer BLOCK.

## 17. Final decision

- `six_node_causal_chain_verdict`: pass / block and must be consumed by the final decision.
- `hierarchy_scan_verdict`: pass / block and must be consumed by the final decision.
- `first_round_output_candidate_gate_verdict`: must remain `block` unless the complete second-round package and named technical-owner review gates are both evidenced; any first-round candidate output is fatal.
- Four-record exact-projection verdict: pass / block and must consume all four exact fields.
- CTA route/policy transmission verdict: pass / block and must remain block while route or policy evidence is blocked.

- Fatal gate verdict:
- Structure score:
- Production evidence score:
- Overall verdict:
- Required repairs:
- Unverified boundaries:
- Next authorized step:
