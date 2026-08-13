---
title: "Website Content Operations QA Checklist"
description: "分别检查源码包、客户任务、发布制品和迁移能力，避免用文件齐全冒充可执行通过。"
type: "checklist"
status: "Draft"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-08-03"
sources: ["MENTAL-MODEL.md", "PLAYBOOK.md", "AGENTS.md", "MANIFEST.md"]
related: ["WRITEBACK.md", "MANIFEST.md", "PLAYBOOKS/id-0001-b2b-seo-article-standard.md", "PLAYBOOKS/id-0002-article-page-frontend-seo-contract.md", "PLAYBOOKS/id-0004-b2b-article-stage-patterns.md", "TEMPLATES/article-draft.md", "TEMPLATES/article-quality-review.md", "TEMPLATES/publish-record.md", "TEMPLATES/transfer-exercise-record.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# QA Checklist

## 当前冻结候选边界

- [ ] 任一失败候选已永久作废；没有复用其 PASS、Reviewer、签字、digest 或局部绿灯。
- [ ] 修复后生成下一不可变候选；Reviewer 均未参与上一候选审查或本轮修复，并且只读审查同一冻结副本。任一路 FAIL/P0/P1 都令该候选作废，不得自报 ready。


## B2B article fail-closed contract QA

本节把长期 fail-closed 规则投影到运行合同和 QA 路由；canonical 内容规则仍由 [ID-0001](PLAYBOOKS/id-0001-b2b-seo-article-standard.md) 与 [ID-0003](PLAYBOOKS/id-0003-b2b-article-optimization-sop.md) 定义，机器入口为 `RUNTIME-CONTRACT.json#b2b_article_fail_closed_projection`。本节不证明具体模板或 scripts 已完成对应强制校验；只有可执行实现、匹配目标分支的测试与独立审查同时闭合，相关 verdict 才可能由 `block` 改变。

- [ ] `content-family-exact-singleton`：primary SERP、声明 family 与可见正文只能得到同一个 family；零匹配、混合匹配或 first-match 吞掉第二 family 均为 `block`。
- [ ] `ordered-six-slot-pain-chain`：可见痛点链按 ID-0001 的六槽顺序表达 Actor → Trigger → Evidence gap → Rework → Consequence → Decision，并验证槽位唯一与相邻因果；token 齐全但倒序、循环或无因果仍为 `block`。
- [ ] `buyer-task-internal-link-anchor`：anchor 自身说明买家要完成的任务、决策、证据或预期输出，并与 buyer-task contract/target parity 对齐；只表达浏览、探索或产品推广的 supplier-centric anchor 为 `block`。
- [ ] `cta-transmission-route-safety`：CTA inventory 消费开放类传递/填写动作及其变形、同义和混淆写法，而不是依赖有限动词表；任何指向未验证 route 的粘贴、附加、填写、导入、拖放、上传、发送或等价指令/链接均为 `block`。
- [ ] `product-claim-evidence-binding`：所有 buyer-visible 产品认证、通用适配、数值性能、连续能力或其他决策性事实进入 product claim ledger，并绑定 claim ID、证据引用、适用边界和 target-page parity；缺任一项或用 synthetic product card 代替真实 SKU 证据均为 `block`。
- [ ] `stable-actor-identity-separation`：production evidence 使用稳定 `producer_id` 与 `independent_reviewer_id`，并按 ID 验证职责分离；同一人更换角色后缀、显示名或头衔不能通过。
- [ ] `artifact-digest-byte-binding`：出现 artifact digest 时必须同时存在可解析 artifact ref，且 digest 与被引用文件字节一致；无 ref 的任意 hex、只靠文本声明或自签名均为 `block`。
- [ ] `production-snapshot-kind-freshness-provenance`：每种 production snapshot 使用 kind-specific closed schema、非空 payload、当前证据窗口以及 query/market/page/scope/subject/capture provenance，并绑定稳定 producer/reviewer IDs；空 envelope、过期快照或仅改写 synthetic 标签均为 `block`。
- [ ] 四记录 exact projection：`secondary_intent_contracts` 与 supporting queries 一一对应；`in_scope_questions`、`out_of_scope_questions`、`intent_completion_test`、`terminal_action_contract`、`first_round_expected_output`、`candidate_decision_required_gates`、`first_round_output_candidate_gate_verdict` 逐字符一致且无同义重叠、跨 stage/commitment/owner 漂移。任一缺失/漂移，或首轮 candidate verdict 不是 `block`，均为 fatal BLOCK。
- [ ] `validate-technical` 首轮只能返回 packet completeness、missing-evidence list、next review step；只有 complete second-round package 与 named technical-owner review 同时有证据后才允许 `candidate-or-stop`。
- [ ] `terminal_action_contract` 与 fallback verified-route request 分离；fallback 不得覆盖或冒充终点动作。route 或 collection-policy 为 BLOCK 时，正文及任何 CTA 不得出现 submit/send/email/upload/share/transmit 或等价传递指令，只能本地保存并通过 approved supplier-contact process 请求 verified route。
- [ ] FAQ conditional contract：FAQ 不是每篇强制。只有 dated 的真实 SERP/query pattern 或具体 buyer objection/uncertainty 触发时才标为 `applicable`；无符合条件的触发证据时，`not-applicable + 空 refs + 具体 absence reason` 合法且不扣分。若添加 FAQ，每题均绑定 `buyer job / objection-or-uncertainty / evidence ref 或明确 inferred boundary / article-owned answer`，且 Review 已检查 buyer-job parity、evidence 边界、正文重复、同义关键词堆叠与 keyword stuffing；仅因“SEO 最佳实践”、字数或关键词覆盖而添加则不通过。
- [ ] `unsupported-outcome-semantic-detection`：标题、meta、excerpt、正文和 CTA 均检查排名、pipeline、ready-to-buy、paying-customer、询盘、转化、获客或收入结果的同义、改写及标点/不可见字符混淆；结构 PASS 不得暗示这些实际结果。
- [ ] `fixture-production-proof-boundary`：所有 synthetic、fixture 或 production-shaped test data 明示仅用于合同/validator 测试，不得满足真实 production evidence、human identity、市场效果或发布资格。
- [ ] 三个前端 SEO 项继续保持 exact deferred set：`html-lang / canonical / article-json-ld`。它们不阻断本轮“内容合同与 QA 路由”落档，但不是 PASS，仍阻断正式 production SEO PASS。

## A. 源码包结构 QA

适用于仍在维护的 `Draft` 源码包。源码模板可以保留明确的双花括号占位符，但必须被 [MANIFEST.md](MANIFEST.md) 列为未完成项，且发布状态保持 `BLOCK`。

- [ ] README 和 COURSE-MAP 可点击到所有必读协议、模板、adapter、QA、写回、品牌、联系、版本和 manifest。
- [ ] 提供可复制的 `WORKSPACE-TEMPLATE/`，但不包含真实客户运行数据。
- [ ] 提供工具字段映射、迁移练习和失败诊断模板。
- [ ] adapter 模板强制版本、来源、权限、单样本、验证、回滚和复查日期。
- [ ] 所有故意占位符已在 manifest 列出；没有未声明占位符。
- [ ] 没有密码、token、cookie、完整配置或本地绝对路径。

## B. 单次客户任务 QA

### 底层理解

- [ ] 学习者能解释业务目标，不只复述按钮步骤。
- [ ] 能说清公司、产品、客户语言、内容、图片、发布记录和反馈之间的关系。
- [ ] 能区分稳定模型与工具特有字段、按钮和限制。
- [ ] 知道为什么先单样本再批量，并能说明成功证据和回滚。

### 事实与业务

- [ ] 公司、产品、认证、MOQ、交期和案例有来源或明确状态。
- [ ] 推断没有写成确认事实；虚拟示例没有进入真实页面。
- [ ] 内容回答具体买家、痛点、决策阶段和下一步，而不是只堆关键词。
- [ ] `buyer_language_seeds` 至少保留两个具体买家表达，并用 `query_language_transformation_reason` 解释为何原话被保留或规范为目标 query；buyer task、search demand 与 SERP format 分开记录并分别验证，synthetic evidence 没有冒充真实市场证据。
- [ ] Primary SERP 已结构化记录 exact query、`serp_primary_query_sample_size`、`serp_primary_query_result_type_counts`（`result-type|count` 数组，counts 总和等于 sample size，并可独立重算 dominant type/count）、`serp_primary_query_dominant_result_type`、`serp_primary_query_dominant_result_count` 和观察前冻结且 `>0.50` 的 threshold；样本至少 5 个 eligible organic results，dominant count 达到 `ceil(sample_size × threshold)`。supporting query 独立成行且只作旁证，未 pooled、未替代 primary。
- [ ] Primary dominant result type → Brief/Draft exact SERP projection与 `expected_content_type` parity → Draft 可观察结构 → Review/Publish `expected_content_type_snapshot`、dominant-result snapshot 与 `serp_content_type_parity_verdict` 已形成 fatal 闭环；synthetic/no dated primary-query SERP evidence 必须为 `not-applicable`，正文形态另由 `body_content_family_implementation_verdict` 从 marker 内真实结构判定；checklist、comparison/matrix、calculator、diagnostic、guide/how-to、case study、product/category/landing 没有被偷换为 generic guide。
- [ ] 主要声明有证明，不能证明的已降级或删除。
- [ ] 正式文章已绑定 Brief、Draft、Quality Review 和 Publish Record，四者 package/brief ID 一致。
- [ ] 只有一个 dominant search intent、dominant buyer task 和 primary decision stage；secondary questions 只支持主任务。
- [ ] 客户语言和三层痛点有可追溯来源；trigger、surface problem、operational/confidence friction、business consequence 与 desired decision 具体但不夸大。
- [ ] 已完成站内 content inventory 与 cannibalization 决策；`conflict_candidates` 按 `candidate_url|overlap_basis|candidate_action` 且不含 owner，`intent_separation` 按 `candidate_url|owner_task|candidate_task|non_overlap_boundary` 一一对应；`merge / redirect / do-not-write` 没有被包装成继续新写。
- [ ] SERP gap、first-party proof 和 information gain 分开记录；新增价值不是“字数更多”。
- [ ] Product decision map 与可见正文都按 condition/variable → evidence → no-fit → remaining inputs → candidate/stop decision 展开，最后再给 target 与 placement；正文没有退化成 brochure 或空白 A/B。
- [ ] `content_purpose` 只使用 `buyer-article / qa-format-lab`；事实状态只使用统一词表，正式生产索引文章的 buyer task、search demand、SERP format 和一方证据均为 `confirmed`，且 source/proof refs 存在、不越界、不是占位符。
- [ ] Primary buyer 明确；secondary roles 只在有证据的具体异议会影响主任务时进入合同或正文。Engineer、Quality、Procurement、Management 只作为 reviewer lenses，不强制四角色全部出现在文章中。
- [ ] `<strong>` 只突出完整判断、风险条件或动作，不与链接嵌套；blockquote 只用于有来源引用或明确 copyable message，作者判断的 callout 不伪装成引用。Synthetic disclosure 位于 marker 内首屏；首个 H2 前约 100–140 英文词。
- [ ] Direct Answer 六槽 `action/object/required inputs or evidence/condition or boundary/expected output or route/evidence boundary` 在 Brief、Draft、Review 与正文语义一致；核心 action/object/output/boundary 位于首段或前 80–120 个英文词，不强制买家看到固定 `Direct answer:` 标签。
- [ ] 没有规范化后重复句、重复/近义 strong 判断、重复 anchor/主张或没有新增 condition/evidence/action/boundary 的低信息段落；semantic emphasis 不是粗体配额。
- [ ] 先判断 `stage_link_requirement_status`；`not-applicable` 时不得因数量要求加链接，`applicable` 时分别检查 `required_when_applicable` 与 `allowed`。内链只完成当前 stage 必需的下一任务；`product_link_evidence_level=none` 不链 product/solution，`family-level` 只链 solution/category，`sku-level` 才允许具体 product。`internal_link_targets` 与九槽 `internal_link_buyer_task_contracts` 一一对应，anchor、placement、owner 和 buyer task 明确，并分别验证 parity、可达性和 target acceptance。
- [ ] Title/H1 与 primary query、dominant task 的 action/object/output、stage/intent/commitment 语义一致；non-Buy 无 transactional modifier；`hierarchy_scan_verdict` 和 title parity verdict 均被 fatal gate/validator 消费。
- [ ] `stage_intake_contract` 只使用 `none|troubleshoot-support|compare-handoff|validate-technical|buy-commercial`：Learn 默认 none；Troubleshoot 只收诊断/support 必需输入；Compare 默认 none、仅 mixed-commercial 才最小 handoff；Validate 才使用两轮 technical profiling；Buy 使用独立 RFQ/commercial packet，不继承 technical-qualified lifecycle。
- [ ] `content_action` 使用 closed enum `create|update|merge|redirect|do-not-write`，Brief、Draft、Review、Publish Record exact；synthetic fixture 使用 `create`，由 `evidence_scope=synthetic-fixture` 表达 fixture 身份。
- [ ] Validate 二轮唯一 canonical 字段为 `second_round_input_relationships`，数组每行严格使用 `second_round_item|new-or-refines|first_round_item-or-not-applicable|additional_decision_purpose`；允许 summary→detail，但不重复索取同一个值，二轮请求与数组集合一致，旧字段或 alias 均 BLOCK。
- [ ] Applicable CTA 有真实 destination，并在买家可见正文写清 value exchange、response expectation、submission method、资料/保密边界、commitment boundary、buyer-visible owner，以及 trigger、最低输入、output/route 和 fallback；qualification state 与当前 stage/intake 匹配，不把 support、compare 或 Buy 强制写成 Applications Engineering 技术预审。
- [ ] `visual_decision_assets` 每行恰好九槽，资产帮助买家完成当前 stage 的决策、支持具体 claim、有 evidence/placement/caption/alt intent，并声明 320px/mobile 阅读要求；装饰图不能替代决策资产。
- [ ] 买家可见正文不出现 `needs-follow-up`、`technical-qualified`、`Soft CTA`、`Final CTA` 或其他内部控制术语；内部 state 只保留在 publishable markers 之外的控制记录。
- [ ] `article_decision_sequence_map` 按 `Hook → Diagnose → Decide → De-risk → Act` 完整、同任务、未调序；`conversion_surface_map` 明确列出 `primary|soft|fallback`，不适用项有理由；Review/Publish exact projection，`article_decision_sequence_verdict` 与 `conversion_surface_map_verdict` 均被 fatal gate 消费。
- [ ] Author 与 Reviewer 不同；[ID-0001 §14](PLAYBOOKS/id-0001-b2b-seo-article-standard.md) 列出的全部 fatal verdict 和 production evidence gates 均被逐项消费，没有只生成不消费的 verdict。任一 applicable `block` 必须同时强制 `fatal_gate_verdict=block`、`overall_verdict=block`、`production_readiness=block`；分数、局部 PASS 或 Publish Record 不得覆盖。所有 verdict 只允许 `pass|block|not-applicable`；Legacy field、blanket PASS、缺 verdict 或未消费 block 均 fail closed。
- [ ] Search-demand production evidence 独立记录 exact query set、platform、market、language、device、window、metric/value per query、brand boundary、zero/low decision、seasonality/trend、analyst、independent reviewer、snapshot/digest；opinion、SERP presence 或错误市场/查询不能写 confirmed。
- [ ] Inferred/synthetic pain 只用 `may/can/risks` 等边界措辞，未经事实证据不得使用 `must/will`；Draft 仅发布唯一 `PUBLISHABLE_BODY_START/END` 内正文，marker 外 control record、内部状态码、placeholder、validator/release/renderer note 和重复 H1 不得泄漏。
- [ ] 总分未覆盖 fabricated claim、unsupported performance claim、缺搜索意图来源、cannibalization unresolved、盘点自引用、缺 information gain、缺 CTA capability proof/destination 或 QA/synthetic 页面误当 production readiness 等一票否决。
- [ ] Stage-conditional intake 已逐分支验收：Learn=`none` 且不收资；Troubleshoot 默认 `none`，只有真实 support receiving task 才使用 `troubleshoot-support`；Compare 默认 `none`，只有 dated `mixed-commercial` evidence + real receiving task 才使用 `compare-handoff`；Validate 才允许两轮 technical qualification；Buy 使用独立 commercial/RFQ packet，不继承 technical-qualified lifecycle。
- [ ] 仅在当前 stage 合法时填写 `fit_signals`、`disqualifiers`、`qualification_reason_codes`、technical/sales acceptance 与 measurement fields；不再使用已禁止的 `qualified_inquiry_contract_status`。结构完整不能冒充询盘、销售接受或转化提升。
- [ ] 任何 input-collecting / human-handoff / commercial CTA 均有 buyer-visible、claim-parity 的任务能力证明，且正文 CTA 附近明确展示 review method、脱敏样例输出、测试能力、有来源案例/认证或能力边界；品牌口号不算证明。
- [ ] 跨角色 CTA 的 `cta_receiving_owner` 是买方接收任务的 named owner，`cta_owner` 是外部 route 的 accountable owner；Buy commercial 两者责任分离，destination 不得复用 technical/engineering-only path。
- [ ] input-collecting / human-handoff / commercial CTA 在买家可见 CTA 区展示与 control record 精确一致的 copyable fallback：已验证 route 给出具体 endpoint 且 reachability/capability 为 `executed + confirmed + pass`；未验证 route 明确“不要发送、保存本地、经既有 approved supplier-contact process 请求 verified route”且保持 `not-run + missing + block`；两者都说明 route owner、完整首轮输入及不构成 quote/order/award/delivery/sales acceptance 的边界。
- [ ] 已枚举全部 buyer-visible CTA instructions，扫描不依赖 H2：首个 H2 前、普通段落、列表、表格、粗体标签、链接/URL、按钮、heading，以及所有 send/email/share/submit/upload/contact/request/book/download/use/route 同义动作都进入 inventory；早期/中段/最终 CTA 的 endpoint、发送指令、owner、inputs、commitment boundary 与证据强度互不冲突，末尾安全 CTA 未覆盖早期 unsafe CTA，且三个 verdict `soft_path_route_safety_verdict`、`all_buyer_visible_cta_sections_evidence_parity_verdict`、`cross_cta_instruction_consistency_verdict` 均被 fatal gate 消费。
- [ ] `html-lang`、`canonical`、`article-json-ld` 在四记录中均明确保持 `deferred-block`；内容合同 scope 可单独验收，但不得据此宣称页面正式 SEO PASS。
- [ ] 四记录的主 CTA `cta_destination`、`cta_owner`、reference/reachability/capability 三轴 `check_execution_status/evidence_result/gate_verdict/evidence_refs` 与 `cta_fallback_route_contract` 逐字符 exact projection；`frontend_deferred_blocks` exact set 仅为 `[html-lang, canonical, article-json-ld]` 且四记录 parity。
- [ ] 四记录的 `cta_fallback_route_contract` 为 exact 17 段同值；verified primary/fallback route 的 endpoint-specific structured evidence 至少包含 `evidence_kind/check_id/task/owner/process/observed_result/capability_acceptance/evidence_ref`，三轴各自绑定该 endpoint，不能只重复 endpoint 文本或借用其他 route 证据；unverified 分支全文无直接链接/use/send 指令，明确 do not send + save locally + request a verified route through the approved supplier-contact process；route、CTA receiving 与 role-handoff receiving owner 均为稳定 ID 或 person name + role，纯岗位/部门/团队不通过。
- [ ] 正文 gate matrix 的 execution/result/verdict 每格只使用 closed enum：`not-run|executed|not-applicable`、`missing|synthetic-only|confirmed|failed|not-applicable`、`pass|block|not-applicable`；任何 alias 都 BLOCK。
- [ ] `first_round_input_specifications` 与首轮字段一一对应，逐项给出 why-needed、单位/格式、示例、required/conditional 和 confidentiality boundary；正文 CTA 附近以可扫读表格或清单呈现，避免二次追问。

### 数据、工具和权限

- [ ] 已识别工具的问题、对象、字段和状态。
- [ ] 已记录 GUI、API、CSV、CLI、MCP 或浏览器接口及选择理由。
- [ ] 已完成稳定对象 / 字段到平台对象 / 字段 / 操作的映射。
- [ ] 已记录认证类型、最小权限、批量限制、幂等、回滚和验证。
- [ ] 图片身份、用途、alt、版权和 URL 有记录；CMS/Slate alt 与最终 DOM `img[alt]` 已逐图比对，不能只看后台字段。
- [ ] 没有凭据、测试文字、未处理占位符或本地绝对路径。
- [ ] 安装、批量、发布、覆盖、删除或全局修改已单独获批。

### 执行与发布后

- [ ] 图片先通过单图测试；CMS 先通过单条草稿测试。
- [ ] 没有把命令、API 或按钮返回成功直接当成业务成功。
- [ ] 真实 URL 可访问，后台刷新、编辑器重开与前台一致。
- [ ] 正式索引文章的 lang、canonical、robots、Article/Breadcrumb schema、time、Open Graph、语义层级和 sitemap 已验证。内容规范单独落档时，只允许把 exact set `html-lang / canonical / article-json-ld` 记录为独立 deferred BLOCK；这不阻断“内容合同 scope”审查，但 deferred 不是 PASS，仍阻断“页面正式 SEO PASS”。
- [ ] Source publication clearance/license、final DOM alt、CMS 写入与回读、release/Published/Stable、排名、询盘、sales acceptance 和转化均保持独立证据轴；任一未验证不能由内容结构 PASS、synthetic fixture、HTTP 200 或历史 release 状态覆盖。
- [ ] QA / Format Lab / 预览页为 noindex，未进入 sitemap、推荐模块或正式内容内链。
- [ ] 内容层先把决策表设计为 320px 可纵向阅读的两列、key-value stack、分组卡片、definition list 或重复表头结构；没有真实 renderer/readability structured evidence 时只能记录 `not-run + missing + block`；唯一 evidence schema 是 `evidence_kind=mobile-readability`、`check_id=mobile-readability`、`target_task`、`accountable_owner`、`viewport_width_px=320`、`render_target`、`method`、`observed_result`、`acceptance_criteria`、`capability_acceptance`、`screenshot_or_trace_ref`，禁止 `mobile-visual` 与 `viewport_width` alias；结构 scope 可独立审查，但 `fatal_gate_verdict`、`overall_verdict` 与 `production_readiness` 继续 BLOCK。真正 ready 时，evidence 必须绑定 endpoint/page version、320px viewport、check_id、target_task、accountable_owner、method、observed result、acceptance criteria、capability acceptance 与截图/trace ref。
- [ ] Visual asset type 只允许 `diagram|decision-tree|decision-table|worksheet|annotated-product|process-flow`；`decision-table|required` 时 marker 内对应 H2 存在真实 Markdown table，并有 320px label-stack fallback；Review 从正文计数，不信任自报 visible。
- [ ] Planned internal-link targets 与 buyer-visible links 分开记录；reachability/capability/target acceptance 未 PASS 时 buyer-visible link count 为 0，不得假报 links visible PASS。
- [ ] Page-shell H1 metadata 与 publishable body 分离：页面 shell 最终只渲染一个 H1，正文禁止 H1、从 H2 开始；桌面和移动端图片、CTA、表格、FAQ 和链接正常；超长拼接截图若出现 sticky header 重复，已用普通 viewport 截图和 DOM 几何排除截图伪影。
- [ ] 未意外覆盖旧内容，失败、跳过、回滚和写回均有记录。
- [ ] 已先运行 `node --test scripts/article-package.test.mjs`，再运行 `node scripts/validate-article-package.mjs`；回归数量不在清单中写死，必须以当前 TAP 输出和同一 freeze 的验证证据为准。`ARTICLE_PACKAGE_STRUCTURE_PASS` 只证明四件套绑定、fatal checks、计分自洽、当前 AllinCMS 正文转换预检和发布记录结构，不替代事实、浏览器、专家、授权或真实发布验收。
- [ ] 四件套是 package root 内普通文件，realpath 不越界；极短空壳、低熵重复、占位字段、泛 anchor、目录或 symlink 伪装均 fail closed。
- [ ] AllinCMS 正文首个 heading 为 H2，`format_features` 与实际转换结果一致；富文本与正文图片仍按两条未集成路径分别验证，不把无图 PASS 外推为图片文章 PASS。

## C. 迁移能力 QA

- [ ] 学习者能让 AI 调查陌生图床、CMS 或相邻平台。
- [ ] 已建立新工具的对象、字段、接口、权限和限制映射。
- [ ] 已在新工具上完成独立样本并验证真实结果。
- [ ] 能根据证据诊断失败，而不是盲目重试。
- [ ] 平台特有知识只写入新 adapter，稳定模型没有被工具绑架。
- [ ] 来源、审批、执行记录和分层写回在迁移后仍然保留。
- [ ] 能把公司、产品和客户知识重映射到一个相邻业务任务，而不是原样复制网站内容。

## D. 品牌化发布制品 QA

适用于真正交付给外部用户的 ZIP、仓库、Skill、插件或普通文件夹。此层**不允许任何占位符**。

- [ ] 品牌名、Logo / 标识、使用说明、联系和支持入口已填充。
- [ ] 许可证、署名、修改、转售和更新边界已确定。
- [ ] release manifest 与实际文件一致。
- [ ] 所有双花括号占位符均已替换，没有测试数据和本地路径。
- [ ] 至少一个参考实现和一个第二工具迁移有可复查证据。
- [ ] 包内链接不逃逸到私有母库或本机目录。

## 结论规则

- 任一权限、事实、数据完整性、真实结果或发布制品项失败：`BLOCK`；
- 参考实现成功但第二工具迁移未验证：教学结论仍为 `BLOCK`；
- 仅有非阻断优化且关键证据完整：`WARN`；
- 所有适用项通过且证据可复查：`PASS`。
