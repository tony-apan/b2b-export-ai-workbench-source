---
doc_id: "ID-0004"
title: "B2B Article Stage Patterns"
description: "为 Learn、Troubleshoot、Compare、Validate、Buy 五个搜索与决策阶段提供可供 AI 直接复用的最小文章模式，防止所有文章被误写成两轮技术资格流程；不证明真实搜索需求或转化效果。"
type: "page"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-11"
sources: ["id-0001-b2b-seo-article-standard.md", "id-0003-b2b-article-optimization-sop.md", "../REFERENCES/SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md"]
related: ["README.md", "id-0001-b2b-seo-article-standard.md", "id-0003-b2b-article-optimization-sop.md", "../TEMPLATES/article-brief.md", "../TEMPLATES/article-draft.md", "../TEMPLATES/article-quality-review.md"]
visibility: "public"
redaction_status: "safe-to-publish"
when_to_read: "需要为一篇英文海外 B2B 文章选择搜索阶段、痛点结构、产品内链证据等级和 CTA 交互，而不能默认套用 Validate 技术收资模式时。"
keywords: ["B2B SEO", "search stage", "Learn", "Troubleshoot", "Compare", "Validate", "Buy", "CTA pattern"]
---
# B2B Article Stage Patterns

## 目的和使用顺序

本页是 [B2B SEO Article Standard](id-0001-b2b-seo-article-standard.md) 的阶段化执行补充，不创建第二套字段、评分或事实规则。AI 在起草文章前必须：

1. 从真实 buyer language、buyer-task evidence 和 query evidence 中识别一个 dominant task；
2. 只选择一个 primary stage；
3. 复制该 stage 的最小模式，再按产品、市场与证据改写；
4. 若搜索词、正文、产品链接或 CTA 指向另一个 stage，先拆页或重分类，不得混写；
5. 未验证真实搜索需求、产品能力或 CTA 服务能力时保持对应 production gate 为 BLOCK。

所有例句只是 synthetic pattern，不是市场事实、产品承诺或已验证转化话术。

冻结审查边界：失败候选永久作废，不得复用其 PASS、Reviewer 或 digest。本页只描述可复用的阶段模式；只有下一不可变候选经未参与上一候选审查或修复的全新 Reviewer 对同一冻结副本一致通过，才可能形成该候选的内容合同结论。

## 五阶段总览

| Stage | 买家正在完成的任务 | 推荐页面产物 | 默认 intake | 默认产品链接 | 默认 CTA |
|---|---|---|---|---|---|
| Learn | 建立概念、边界或术语理解 | explanation、concept map、self-check | `none` | `none`；必要时 hub/educational | 无收资的下一阅读或自检 |
| Troubleshoot | 定位症状、根因分支或恢复路径 | diagnostic tree、recovery checklist | `none`；真实支持交接才 `troubleshoot-support` | 支持文档、诊断工具；不得先推 SKU | 本地诊断；必要时最小 support packet |
| Compare | 用同一组维度形成 shortlist/stop | comparison matrix、decision table | 默认 `none`；有证据的商业桥才 `compare-handoff` | `none` 或 `family-level` | 保存/使用矩阵；必要时最小 handoff |
| Validate | 判断首轮输入是否齐全并定义下一轮补证路径 | readiness worksheet、packet completeness、missing-evidence list、next review step；candidate-or-stop 仅为双门后后续决策 | `validate-technical` | `family-level`；只有 condition-to-spec 证据充分才 `sku-level` | 首轮最小工程 packet；完整二轮 + named technical-owner review 后才可 candidate-or-stop |
| Buy | 提交可被商业 owner 处理的 RFQ/采购请求 | RFQ/commercial packet | `buy-commercial` | 有证据的 family 或 SKU | 明确商业提交，不继承技术资格状态 |

## Canonical stage-intake 字段条件

以下条件只解释 ID-0001 已定义的 canonical 字段，不新增字段、评分或第二套 lifecycle。未选择 `validate-technical` 时，不得填入 Validate 两轮技术资格数据。

| `stage_intake_contract` | `first_round_inquiry_inputs` | `second_round_inquiry_inputs` / `second_round_input_relationships` | Technical qualification |
|---|---|---|---|
| `none` | `[]` | `[]` / `[]` | 不适用；technical gates 与 `qualification_reason_codes` 保持空数组 |
| `troubleshoot-support` | 单轮 support packet | `[]` / `[]` | 不使用 Validate lifecycle；只完成支持交接 |
| `compare-handoff` | 单轮 minimal handoff | `[]` / `[]` | 不使用 technical qualification；只完成有证据的比较交接 |
| `validate-technical` | 4–6 个首轮最小输入 | 二轮输入及逐项 `second_round_input_relationships` | 唯一允许使用两轮技术资格的合同 |
| `buy-commercial` | 独立 commercial packet | `[]` / `[]` | 使用 commercial owner/state，不继承技术资格状态 |

## 所有阶段共用的买家可见合同

无论选择哪一阶段，都必须同时满足：

- 标题、page-shell H1 metadata、slug、primary query、dominant task 和 stage 语义一致；page shell 只渲染一个 H1，publishable body 禁止 H1 并从 H2 开始；
- primary query 必须独立结构化记录 `serp_primary_query_sample_size`、result-type counts、`serp_primary_query_dominant_result_type`、`serp_primary_query_dominant_result_count` 与观察前冻结且 `>0.50` 的 `serp_primary_query_dominance_threshold`；supporting query 只作旁证，不能 pooled 或替代 primary；result type 必须继续投影到 `expected_content_type`、可观察 Draft shape、Review/Publish snapshot、`serp_primary_query_dominance_verdict` 与 `serp_content_type_parity_verdict`；
- 首个 H2 前以约 120–140 个英文词完成六槽 Direct Answer，并同时让买家看到适用的 fictional disclosure、窄 ICP fit、明确 exclusion、self-identification、first-round output 与 commitment boundary；
- 痛点按 actor → operating event → evidence gap → rework mechanism → program consequence → bounded decision 展开；
- 正文使用买家语言，不泄漏 `needs-follow-up`、`technical-qualified`、`Soft CTA`、`Final CTA` 等内部控制术语；
- `product_link_evidence_level` 决定只能无产品链接、链接 solution family，或链接具体 SKU；
- CTA 可见说明 value exchange、响应边界、提交方式、资料边界、承诺边界和负责角色；
- 收资 CTA 逐项显示输入用途、单位/格式、示例、必填/条件项和保密边界，并在 CTA 附近展示与承诺同等级的任务能力证明；
- input-collecting、human-handoff 与 commercial CTA 在买家可见 CTA 区提供可复制 fallback packet，并与 evidence axis 对齐：已验证 route 必须给出具体 buyer-visible endpoint，且该 endpoint 自己的 structured evidence 至少含 `evidence_kind/check_id/task/owner/process/observed_result/capability_acceptance/evidence_ref`，reachability/capability 为 `executed + confirmed + pass`；未验证 route 全文不得链接或指示使用，必须明确“不要发送、保存本地、经既有 approved supplier-contact process 请求 verified route”，并保持 `not-run + missing + block`；两种分支都要保留 route owner、完整首轮输入与 commitment boundary；
- 跨角色 CTA 区分买方侧 `cta_receiving_owner` 与外部 route 的 `cta_owner`；Buy commercial destination 不得伪装成 engineering/technical-only review endpoint；
- 全部 buyer-visible CTA 都在 scope，包括首个 H2 前、普通段落、列表、表格、粗体标签、链接、按钮和所有 submit/send/share/upload/contact/book/download/email/forward/transfer 等直接或同义动作；末尾安全 CTA 不得覆盖早期 unsafe CTA；
- 每篇文章保存并按序消费 `Hook → Diagnose → Decide → De-risk → Act` 的 `article_decision_sequence_map`，以及 `primary|soft|fallback` 的 `conversion_surface_map`；Review/Publish 必须 exact projection 并以对应 verdict fail closed；
- 至少提供一个帮助买家决策的视觉资产，或用九槽 `not-applicable` row 解释为什么不需要；决策表先采用两列、key-value stack、分组卡片、definition list 或其他 320px 可纵向阅读结构；没有真实 renderer/readability structured evidence 时只能 `not-run + missing + block`，结构 scope 可继续审查但 production readiness 必须 BLOCK；唯一 evidence schema 为 `evidence_kind=mobile-readability`、`check_id=mobile-readability`、`target_task`、`accountable_owner`、`viewport_width_px=320`、`render_target`、`method`、`observed_result`、`acceptance_criteria`、`capability_acceptance`、`screenshot_or_trace_ref`，禁止 `mobile-visual` 与 `viewport_width` alias；
- Brief/Draft/Review/Publish exact projection 主 CTA destination、owner、reference/reachability/capability 三轴 status/result/verdict/evidence refs、17 段 fallback contract，以及 `frontend_deferred_blocks=[html-lang, canonical, article-json-ld]`；
- 所有 verdict 只允许 `pass|block|not-applicable`。ID-0001 §14 closed list（包括 `article_decision_sequence_verdict`、`conversion_surface_map_verdict`、`hierarchy_scan_verdict`、`semantic_emphasis_verdict`）中任一 applicable fatal verdict 为 `block`，都必须传播为 `fatal_gate_verdict: block`、`overall_verdict: block`、`production_readiness: block`；任何阶段模式、评分或末尾安全 CTA 都不能覆盖；
- 不保证排名、询盘、销售接受、收入或转化提升；source/license、final DOM alt、CMS、release 与真实业务结果继续独立 BLOCK/未验证。

### Canonical decision and conversion maps

```yaml
article_decision_sequence_map:
  - "hook|buyer-visible failure or trigger|opening"
  - "diagnose|cause/evidence gap and why it matters|diagnosis section"
  - "decide|candidate-or-stop or next decision|decision section"
  - "de-risk|assumptions, no-fit, proof and validation boundary|risk section"
  - "act|one bounded next action and expected output|final action section"
article_decision_sequence_verdict: "pass|block"
conversion_surface_map:
  - "primary-stable-surface-id|primary|main stage outcome|location-or-locator|interaction|route-id-or-not-applicable"
  - "soft-stable-surface-id|soft|lower-friction preparation or self-check|location-or-locator|interaction|route-id-or-not-applicable"
  - "fallback-stable-surface-id|fallback|safe no-send route recovery|location-or-locator|interaction|route-id-or-not-applicable"
conversion_surface_map_verdict: "pass|block"
```

---

## Pattern 1：Learn

### 适用搜索意图

买家想先理解术语、工作原理、输入之间的关系或适用边界，尚未要求诊断、选型验证、报价或供应商动作。

```yaml
stage: "learn"
intent_class: "informational"
stage_intake_contract: "none"
commercial_commitment: "none"
product_link_evidence_level: "none"
```

### Synthetic minimum pattern

- Query example: `how regenerative braking works in industrial drives`
- Dominant task: `understand|regenerative braking operating conditions and limits|a bounded concept map and self-check|learn|none`
- Pain chain: new engineer → braking requirement appears → operating limits are unclear → terminology is interpreted as universal capability → concept selection may need rework → reader needs a bounded applicability map.
- Direct Answer six slots:
  - action: explain;
  - object: operating conditions and limits;
  - inputs/evidence: system topology, operating mode, energy path;
  - boundary: concept explanation, not application approval;
  - output: concept map and self-check;
  - evidence boundary: product-specific capability remains unverified.
- CTA interaction: `inline-no-input`；例如“Use the three-condition self-check before opening the application guide.”
- Visual asset: annotated concept diagram or semantic decision table.

### Forbidden carry-over

- 不收项目参数；
- 不出现两轮 technical intake；
- 不产生 qualification state；
- 不把 “Learn more” 当 CTA；应明确读者下一步会获得什么；
- 不以产品页代替概念答案。

---

## Pattern 2：Troubleshoot

### 适用搜索意图

买家已有故障、异常、失败或性能偏差，目标是缩小根因范围并获得恢复或支持路径。

```yaml
stage: "troubleshoot"
intent_class: "troubleshooting"
stage_intake_contract: "none|troubleshoot-support"
commercial_commitment: "none"
product_link_evidence_level: "none"
```

### Synthetic minimum pattern

- Query example: `why industrial encoder feedback drops under load`
- Dominant task: `diagnose|encoder feedback loss under loaded operation|a root-cause branch and safe next check|troubleshoot|none`
- Pain chain: maintenance engineer → dropout appears under load → signal/power/mechanical evidence is incomplete → teams swap parts without isolating the branch → downtime and repeat failures can continue → buyer needs the next safe discriminating check.
- Direct Answer: start with the safest branch order, required observations, stop condition, expected diagnostic output and the limit that remote content cannot confirm the root cause.
- CTA interaction:
  - local closure: `local-tool` or `inline-no-input` diagnostic checklist;
  - support handoff: only collect symptom, environment, reproduction steps, observed codes/logs and safety boundary.
- Product link: prefer diagnostic/support content; do not recommend a replacement SKU before evidence isolates a product-level cause.
- Visual asset: decision tree with “check / result / next branch / stop” nodes.

### Forbidden carry-over

- 不把缺少日志写成产品 no-fit；
- 不使用 Validate 的二轮 engineering packet；
- 不因 buyer 提到停机成本就改写为 Buy；
- 不把 support request 自动判为 technical-qualified 或 sales-accepted。

---

## Pattern 3：Compare

### 适用搜索意图

买家要在多个方案、架构或供应类别之间建立共同维度，并形成 shortlist、条件化选择或 stop。

```yaml
stage: "compare"
intent_class: "commercial-investigation|mixed-commercial"
stage_intake_contract: "none|compare-handoff"
commercial_commitment: "none|soft"
product_link_evidence_level: "none|family-level"
```

### Synthetic minimum pattern

- Query example: `servo motor vs stepper motor for low-speed positioning`
- Dominant task: `compare|servo and stepper architectures under low-speed positioning constraints|a condition-based shortlist and stop rule|compare|none`
- Pain chain: design engineer → two architectures appear viable → load, accuracy and duty assumptions are mixed → teams compare headline specs instead of common conditions → shortlist churn risks delaying design freeze → buyer needs a common-basis decision matrix.
- Direct Answer: state the selection boundary, required comparison inputs, which condition favors each option, the expected shortlist and what still requires validation.
- CTA interaction: use/save the matrix; only use `compare-handoff` when evidence supports a real mixed-commercial bridge and collect the minimum fields needed for that bridge.
- Product link:
  - no evidence: educational/hub only;
  - category evidence: solution family;
  - do not link a SKU merely because it appears in the catalogue.
- Visual asset: comparison matrix with identical units, conditions, evidence and “not enough data” state.

### Forbidden carry-over

- 不把 Compare 写成“所有产品都适用”；
- 不默认收取完整工程 packet；
- 不产生 technical-qualified；
- 不用 price/MOQ/RFQ 词吸引非 Buy 查询；
- 不让推荐结果早于共同维度和 no-fit 规则。

---

## Pattern 4：Validate

### 适用搜索意图

买家已有候选方向，目标是先判断首轮输入是否齐全、缺什么证据、下一轮由谁补什么；candidate-or-stop 只属于完整二轮包经 named technical-owner review 后的后续决策。

```yaml
stage: "validate"
intent_class: "commercial-investigation"
stage_intake_contract: "validate-technical"
commercial_commitment: "none"
product_link_evidence_level: "family-level|sku-level"
```

### Synthetic minimum pattern

- Query example: `cargo hub motor engineering readiness checklist`
- Dominant task: `assemble|cargo hub-motor engineering-readiness inputs|packet completeness, missing-evidence list, and next review step|validate|none`
- Pain chain: application engineer → candidate request arrives → load/route/controller/interface evidence is incomplete → wattage-first matching creates repeated clarification → sample and schedule risk may grow → buyer needs a bounded readiness decision.
- Direct Answer: list the first-round evidence, packet-completeness rule, missing-evidence output, next review step and the boundary that readiness does not prove performance, compliance, availability or commercial acceptance.
- CTA interaction:
  - first request: 4–6 minimum engineering inputs;
  - second round: only after first review, with exact `second_round_input_relationships`;
  - first-round value exchange: packet completeness, missing-evidence list and next review step;
  - later candidate-or-stop: allowed only after the complete second-round package plus named technical-owner review;
  - buyer-visible language must describe this result without exposing internal lifecycle labels.
- Product link:
  - `family-level` until category evidence supports a solution family;
  - `sku-level` only when condition-to-spec evidence supports that exact SKU and visible claims match the evidence.
- Visual asset: readiness worksheet、interface diagram、candidate/stop flow，或纵向 H3/definition-like blocks、key-value stack、最多两列的决策工具。只有确有比较必要时才使用 Markdown `decision-table`；若 required，必须在声明 H2 内渲染并提供 320px 逐行 label stack fallback。结构更稳不等于 mobile PASS；无真实 renderer/readability evidence 时 mobile production 仍 BLOCK。

### Forbidden carry-over

- 不把首轮提交写成技术通过；
- 不把 technical review 写成 RFQ/order/supplier award；
- 不在首轮 CTA 提前索取二轮细节；
- 不让 Applications Engineering 成为 sales acceptance owner；
- 不向买家展示内部 state code；
- synthetic/no-SERP-evidence 不得把正文 checklist shape 写成 SERP parity PASS，必须使用 `serp_content_type_parity_verdict=not-applicable` 与独立 `body_content_family_implementation_verdict`；
- 二轮正文的每项 Relationship 与 First-round source 必须逐字等于 `second_round_input_relationships`，relationship 只允许 `new|refines`。

---

## Pattern 5：Buy

### 适用搜索意图

买家明确要求价格、报价、MOQ、交期、样品、订单或供应商商业评估，页面需要把请求变成 commercial owner 可处理的 packet。

```yaml
stage: "buy"
intent_class: "transactional|mixed-commercial"
stage_intake_contract: "buy-commercial"
commercial_commitment: "commercial"
product_link_evidence_level: "family-level|sku-level"
```

### Synthetic minimum pattern

- Query example: `request industrial gearbox quote for food packaging line`
- Dominant task: `request|a commercially reviewable gearbox supply proposal|an RFQ packet and named commercial next step|buy|commercial`
- Pain chain: procurement lead → sourcing window opens → technical and commercial inputs are split across emails → supplier responses are incomparable → quote cycles may require another review and award timing can drift → buyer needs one reviewable RFQ packet.
- Direct Answer: state the minimum commercial and technical inputs, quotation boundary, expected response route and the fact that submission is not automatic supplier acceptance.
- CTA interaction: `commercial`; collect explicit commercial intent, quantity/MOQ context, market, timing, delivery/trade conditions and required technical inputs; expose submission method, owner, data boundary and response expectation.
- Product link: link only the family or SKU actually supported by evidence; do not use a generic product link to hide an incomplete RFQ route.
- Visual asset: RFQ readiness checklist or proposal-comparison table.

### Forbidden carry-over

- 不继承 Validate 的 technical-qualified state；
- 不把下载 datasheet 当商业意图；
- 不在没有 named commercial owner 和可验证 destination 时宣称可报价；
- 不承诺价格、交期、产能或 sales acceptance；
- 不把询盘提交等同成交或供应商 award。

---

## Stage terminal-action and article-shape contract

每个 pattern 在 Brief、Draft、Review、Publish Record 中 exact projection `secondary_intent_contracts`、`in_scope_questions`、`out_of_scope_questions`、`intent_completion_test`、六个 FAQ conditional fields，以及：

```text
terminal_action_contract = action|object|observable-output|stage|commercial-commitment
visible_pain_chain = Actor → Trigger → Evidence gap → Rework → Consequence → Decision
```

- **Learn** terminal action 只能是 explain、self-check、understand、identify next learning input；不得 nominate/appoint/select supplier、quote、RFQ、order。
- **Troubleshoot** terminal action 只能是 isolate cause、complete diagnostic output、identify next check/stop；不得报价、推荐购买或供应商 award。
- **Compare** terminal action 只能是 build a bounded comparison/matrix/shortlist-for-further-validation；不得 appoint、award、nominate manufacturing partner 或完成 supplier selection。
- **Validate** 首轮 terminal action 只能是 prepare/validate an evidence packet，并返回 packet completeness、missing-evidence list 与 next review step；`candidate-or-stop` 只在 complete second-round package + named technical-owner review 两门均通过后才可作为后续 action。不得 supplier/manufacturing-partner nomination、quote、RFQ、order。
- **Buy** 才可进入 quote/RFQ/commercial next step，但提交不等于 supplier acceptance、award、order acceptance、成交或收入结果。

Noncommercial stage 检查须归一化大小写、标点、连字符与零宽字符后识别商业同义终点；dominant task、`Act` row、terminal action、stage 与 commitment 必须同义一致。

所有阶段还必须满足：

1. 六槽 pain contract 各有唯一值且顺序固定；`visible_pain_chain` 在控制记录中保留 `Actor|...` 到 `Decision|...` 的稳定投影，但 buyer-facing prose 必须用六条连续编号自然语言依次表达六槽，不公开 `Actor:`、`Trigger:` 等 audit labels，并逐条验证可唯一映射及相邻因果。
2. 产品链接 anchor 本身表达 buyer task、decision、evidence gap 或 expected output；`explore solutions / discover products / browse options / see products` 不是合格 anchor。
3. CTA 对 `send|submit|upload|share|email|contact|use|paste|attach|fill|enter|import|drag|drop|copy into|forward|post` 建立 transmission inventory；未验证 route 只能本地保存、明确禁止，或验证后再传递。
4. CTA measurement 对 `primary / soft / fallback` 分别绑定稳定 surface ID、page/CTA version、start/submit/success/failure、abandonment、technical-qualified、sales-accepted、数据源、baseline、观察窗口、owner 与 evidence refs；四记录 exact projection，适用 surface 不得 `not-applicable`。
5. Buyer-visible 产品事实进入 claim ledger，并绑定 evidence、applicability boundary、target URL 与 target-page parity；synthetic card 不证明 Production SKU。
6. 禁止结构优化会带来 pipeline、ready-to-buy prospects、paying customers、customer acquisition、排名、流量、询盘、转化或收入的承诺；只描述 buyer task 与 evidence packet。
7. Fixture、placeholder、`example.test` 与 synthetic reviewer 只证明结构，不证明 Production evidence 或独立真人审核。

## AI 起草前的阶段对抗问题

若任一题答“是”，先停下并重分类、拆页或修合同：

1. 标题是 Learn，但 CTA 要报价吗？
2. 查询是 Troubleshoot，但文章在证据出现前推荐 SKU 吗？
3. Compare 是否在共同维度之前宣布 winner？
4. Validate 是否把首轮表单提交写成通过、报价或 supplier acceptance？
5. Buy 是否复用了技术资格流程，却没有独立商业 packet 和 commercial owner？
6. 产品链接是否超过 `product_link_evidence_level`？
7. CTA 是否只写“Contact us / Learn more”，没有说明买家获得什么、如何提交和承诺边界？
8. 收资/人工/commercial CTA 的 fallback 是否只藏在 control record，或缺主 route 不可用时的动作、完整首轮输入、备用 channel/owner？
9. Buy 是否把买方 Procurement receiving owner、外部 commercial route owner 和 engineering endpoint 混成一个 handoff？
10. 图片是否只是装饰，不能帮助买家完成该 stage 的任务？
11. 买家可见正文是否出现内部 gate、state、review label 或作者控制词？
12. 是否把 structural PASS、表单提交或 CMS 成功误写成排名、询盘或转化提升？
13. `expected_content_type` 是否同时命中多个 family，或只靠 first-match 逃过冲突？
14. noncommercial terminal action 是否用 nominate、appoint、partner、award 等同义词隐藏商业终点？
15. 六槽 pain contract 是否缺失、重复、乱序、无法从自然正文映射，或相邻因果不成立？
16. 产品链接 anchor 是否只是软广，而不是 buyer-task anchor？
17. 未验证 CTA route 是否仍出现立即 send/use/copy/upload 等传递指令？
18. 产品事实是否缺 claim ledger、applicability boundary 或 target-page parity？
19. reviewer stable ID 是否与 producer/remediation participant 实为同一人，或只靠 display suffix 伪装分离？
20. Production snapshot 是否 payload 为空、超过 395 天、provenance 不明或 digest 未绑定真实 bytes？

全部通过后，才进入 Draft 和独立 Quality Review。
