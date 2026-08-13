---
title: "Website Content Operations Templates Index"
description: "说明本子库模板的用途、实例化方式、证据要求和客户数据边界。"
type: "index"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-08-12"
sources: ["../README.md", "../MANIFEST.md", "../QA-CHECKLIST.md"]
related: ["../START-HERE.md", "../WORKSPACE-TEMPLATE/README.md", "../WRITEBACK.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# 模板目录

这里是 `website-content-ops` 的结构化模板入口。模板用于把输入、字段、证据、失败和写回记录成可复核文件；它们不是客户运行数据，也不是自动发布指令。

## 使用规则

1. 先从 [START-HERE.md](../START-HERE.md) 判断当前任务阶段。
2. 只复制当前阶段需要的模板，不要一次读取或填写全部模板。
3. 新文件中的公司、客户、联系、价格、指标和发布结果必须有来源或状态。
4. 客户真实数据只能进入客户私有运行区，不得回写本公开母库。
5. 模板本身不能代替 [QA-CHECKLIST.md](../QA-CHECKLIST.md) 的真实验收。

## 模板分类

- 业务对象：公司、产品、客户语言、[文章 brief](article-brief.md)。
- 文章草稿：使用 [Article Draft](article-draft.md) 分离页面标题/H1、Markdown 正文和 CMS 持久化格式。
- 文章质量：草稿完成后使用 [Article Quality Review](article-quality-review.md)，总分不能覆盖一票否决。
- 媒体与发布：图片清单、发布记录；正式文章还必须绑定前端 SEO 与编辑器重开证据。
- 工具迁移：字段映射、迁移练习、失败诊断。
- 资料驱动 CMS 变更：先用 [Source Extraction](source-extraction.md) 按宿主能力把每份 PDF、DOCX、表格、网页、图片或 brief 变成只存在于客户私有运行区的 locator/digest/warning 证据，再用 [Content Operation Plan](content-operation-plan.md) 把 source snapshot、claim ledger、两阶段 site scope、desired state、当前能力、精确 diff、串行 operations、授权摘要、对账和验收绑定到同一计划；正式流程读 [ID-0005](../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md)。提取 artifact 只是 claim-candidate input，本地 PASS 不证明事实已确认或允许公开。
- 来源与写回：来源登记和可复用经验记录。
- 长期知识页：需要进入 `MANIFEST.md` 声明的 durable roots 时，使用 [durable page 模板](durable-page.md)，并补齐 `doc_id`、读取时机和检索词。

## Current B2B buyer / conversion canonical contract

### 冻结候选与模板状态

冻结审查规则：失败候选永久作废，其 PASS、Reviewer、签字、digest 和局部绿灯都不得复用。修复后必须生成下一不可变候选，并由未参与上一候选审查或本轮修复的全新 Reviewer 对同一冻结副本重新审查。四件套始终是 working-tree contract inputs；在同一候选完成字段一致性验证与全新审查前，不得宣称 template contract ready 或 production-ready。

正式文章四件套为 `Article Brief → Article Draft → Article Quality Review → Publish Record`，必须共享 package/brief identity，并 exact projection 同一份 query、阶段、主 CTA、decision/conversion maps、deferred blocks 和 fatal verdict 状态。字段缺失、alias、值漂移或下游未消费均为 BLOCK。


### B2B article fail-closed contract 投影与模板边界

四件套的后续模板修订必须消费 `RUNTIME-CONTRACT.json#b2b_article_fail_closed_projection` 的全部 required gates，并由 [QA Checklist](../QA-CHECKLIST.md#b2b-article-fail-closed-contract-qa) 验证；字段与正文语义继续以 ID-0001/ID-0003 为 canonical，不在本索引复制第二套定义。当前只完成模板入口路由，不表示具体模板、示例或 scripts 已实现这些 gate；fixtures 也不构成真实 production proof。`html-lang / canonical / article-json-ld` 继续 deferred/not PASS。

### Primary SERP 到 Draft/Review/Publish 的闭环

- Primary query 必须独立结构化记录 `serp_primary_query_sample_size`、result-type counts、`serp_primary_query_dominant_result_type`、`serp_primary_query_dominant_result_count` 和观察前冻结且 `>0.50` 的 `serp_primary_query_dominance_threshold`；supporting query 只能旁证，不得 pooled 或替代 primary。
- dominant result type 必须投影为 Brief/Draft `expected_content_type`，并在 Draft 中形成可观察 shape；Review/Publish 再 exact projection `expected_content_type_snapshot`、primary SERP snapshot 和 `serp_content_type_parity_verdict`。checklist、comparison/matrix、calculator、diagnostic、guide/how-to、case study、product/category/landing 不得偷换成 generic guide。
- `serp_primary_query_dominance_verdict` 或 `serp_content_type_parity_verdict` 为 `block` 时，必须同时得到 fatal/overall/production-readiness BLOCK。

### Buyer、阶段与正文形态

- Closed vocabularies：`stage: learn|troubleshoot|compare|validate|buy`、`intent_class: informational|troubleshooting|commercial-investigation|mixed-commercial|transactional`、`commercial_commitment: none|soft|commercial`、`cta_interaction_type: inline-no-input|local-tool|input-collecting|human-handoff|commercial`；`dominant_task_contract` 最后一槽必须使用同一 commitment enum。
- `pain_chain_contract` 固定为 `actor|operating-event|evidence-gap|rework-mechanism|program-consequence|bounded-decision`；Direct Answer 必须显式保存 action、object、required inputs/evidence、condition/boundary、expected output/route 与 evidence boundary。
- 正文 canonical 顺序固定为 `Hook → Diagnose → Decide → De-risk → Act`，转化面固定为 `primary|soft|fallback`。四件套必须 exact projection `article_decision_sequence_map`、`article_decision_sequence_verdict`、`conversion_surface_map` 与 `conversion_surface_map_verdict`；调序、漏段或只记录最终 CTA 均为 BLOCK。
- H1 是 page-shell metadata；唯一 publishable body 禁止 H1，并从 H2 开始。内部 control record、status code、validator note、placeholder 或 release note 不得进入 buyer-visible body。

### CTA inventory、route 与 owner

- CTA inventory 不依赖 H2、标题或 `CTA` 标签。首个 H2 前、普通段落、列表、表格、粗体标签、链接、按钮，以及 send/email/share/submit/upload/contact/request/book/download/use-form/route-packet 等直接或同义 buyer-visible 指令均在 scope。末尾安全 CTA 不能覆盖更早的 unsafe CTA。
- 每条 CTA 都必须绑定稳定 surface ID、位置、destination、`cta_owner`、interaction、route status、endpoint-specific evidence 与 fallback；跨角色时 `cta_receiving_owner` 是买方侧接收 owner，不能冒充供应商侧 `cta_owner`。
- verified CTA/fallback 的 structured evidence 至少包含 `evidence_kind/check_id/task/owner/process/observed_result/capability_acceptance/evidence_ref`，并与该 exact endpoint 绑定；重复 endpoint 文本、存在同名页面或本地 reference parity 不能证明 route 可达或能力被接受。
- unverified route 全文不得出现可点击 endpoint，也不得指示 use/send/email/share/submit/contact 到该 route；只能明确 **do not send、save locally、request a verified route through the buyer organization’s existing approved supplier-contact process**，三轴保持 `not-run + missing + block`。
- 主 CTA 在四件套中 exact projection：`cta_destination`、`cta_owner`、reference/reachability/capability 的 execution status、evidence result、gate verdict、evidence refs、`cta_fallback_route_contract`。`frontend_deferred_blocks` exact set 只能是 `[html-lang, canonical, article-json-ld]`。

### Qualification、mobile 与 fatal consumption

- `first_round_inquiry_inputs` 与 `second_round_inquiry_inputs` 是 canonical、互斥输入组。缺输入只能进入 `needs-follow-up`；只有 evidenced incompatibility、out-of-envelope 或 unsupported scope 才能 `disqualified`。技术 qualification 与 sales acceptance 使用独立 gates、独立 named owner 和独立 evidence，不得自动升级。
- 内容层先采用两列、key-value stack、分组卡片、definition list 或其他 320px 可纵向阅读形态。没有真实 renderer/readability structured evidence 时，`mobile_visual_check_execution_status`、`mobile_visual_evidence_result`、`mobile_visual_gate_verdict` 只能保持 `not-run`、`missing`、`block`；唯一 evidence schema 为 `evidence_kind=mobile-readability`、`check_id=mobile-readability`、`target_task`、`accountable_owner`、`viewport_width_px=320`、`render_target`、`method`、`observed_result`、`acceptance_criteria`、`capability_acceptance`、`screenshot_or_trace_ref`，禁止 `mobile-visual` 与 `viewport_width` alias；结构 scope 可以审查，但 production readiness 必须 BLOCK。真正 ready 才允许 evidence-backed PASS。
- 所有 verdict 只允许 `pass|block|not-applicable`。ID-0001 §14 的 closed fatal verdict（包括两个 map verdict、`hierarchy_scan_verdict` 与 `semantic_emphasis_verdict`）中任一 applicable verdict 为 `block`，必须同时强制 `fatal_gate_verdict: block`、`overall_verdict: block`、`production_readiness: block`。评分、局部 PASS 或作者自报不能覆盖。
- `html-lang`、canonical、Article JSON-LD 本轮可保持 deferred/not PASS，且不阻断“内容合同 scope”；source/license、final DOM image alt、CMS mutation/readback/editor-reopen/frontend acceptance、release，以及排名/询盘/转化仍是独立 BLOCK 或未验证，不能被结构 PASS 覆盖。

## 不要把模板当成完成证据

模板填写完成只代表资料结构存在。正式文章使用 `Article Brief → Article Draft → Article Quality Review → Publish Record` 四件套；Brief 必须分开记录 buyer task、search demand 和 SERP format，Review 必须由不同 Reviewer 用逐项 evidence matrix 复核，不能用 blanket PASS 或布尔值自证；新写文章按 [B2B SEO 标准](../PLAYBOOKS/id-0001-b2b-seo-article-standard.md)，优化现有文章先按 [B2B Article Optimization SOP](../PLAYBOOKS/id-0003-b2b-article-optimization-sop.md) 串行诊断，并继续接受 ID-0001 的全部质量闸；页面发布再按 [前端 SEO 合同](../PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md) 验收。只有完成真实动作、后台回读、编辑器重开、前台/SEO 检查、失败记录和写回，任务才可能通过验收。
