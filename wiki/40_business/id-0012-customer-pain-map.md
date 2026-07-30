---
title: "Customer Pain Map"
doc_id: "ID-0012"
description: "记录客户痛点、触发事件、当前替代方案、不行动成本、期待结果、证据强度和可服务的搜索/营销场景；真实资料与虚拟演示分开处理。"
type: "business"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["User direction on 2026-07-26"]
related: ["index.md", "id-0013-icp.md", "messaging-house.md", "../20_concepts/id-0001-search-intent.md", "../30_playbooks/id-0011-seo-content.md", "../_templates/customer-voice-to-search-intent.md"]
confidence: "medium"
review_after: "2026-10-26"
when_to_read: "需要整理客户触发事件、痛点、替代方案和证据强度，或把客户语言连接到营销任务时读本页；真实资料不得混入虚拟演示。"
keywords: ["客户痛点", "触发事件", "替代方案", "证据强度", "客户语言", "虚拟演示"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Customer Pain Map

## 作用

客户痛点地图不是文案灵感清单，而是连接客户原话、搜索意图、产品能力、内容页面和市场验证的中间层。

真实客户原话默认保存在私有 raw 或客户运行区；公开页面只保存处理后、归一化并可追溯的结论。虚拟演示可以保留完整原话，但必须标注虚构。没有来源或只有单次对话时，状态必须是 `Signal` 或 `Hypothesis`，不能写成市场事实。

## Pain Map

| Pain ID | Segment / Role | Trigger | Surface Problem | Deeper Pain / Job | Current Alternative | Cost of Inaction | Desired Outcome | Evidence Count | Confidence | Source Refs | Search / Page Opportunities |
|---|---|---|---|---|---|---|---|---:|---|---|---|
| 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 0 | Hypothesis | 待补 | 待补 |

## 客户语言卡

每条值得沉淀的客户语言至少记录：

- `customer_words_private_ref`：私有原话位置，不在公开库复制 PII。
- `normalized_language`：可复用的客户表达；真实资料需移除 PII，虚拟演示需标注虚构。
- `segment_and_role`：什么类型的客户、什么角色。
- `situation_and_trigger`：什么情境触发了问题。
- `pain_or_job`：真正想解决的问题或完成的任务。
- `current_alternative`：现在怎么解决，为什么不满意。
- `desired_outcome`：理想结果。
- `objection_or_risk`：担心什么。
- `evidence_level`：单次 signal、多次重复、搜索印证或实验验证。
- `possible_use`：SEO/GEO、产品、销售、主动营销、FAQ 或 onboarding。

## 从痛点到内容的约束

- 痛点必须连接到明确 ICP 和使用场景，不能只写宽泛焦虑。
- 页面只能承诺公司能够用事实和证据支持的结果。
- 同一个痛点可能需要不同页面：诊断、方法、对比、产品、案例、FAQ。
- 搜索量低不代表没有商业价值；高搜索量也不代表适合目标客户。
- 聊天中的问题可以生成搜索假设，但必须用 Search Console、SERP、其他聊天或页面实验继续验证。
- 有效和无效结果都要回写；无效页面同样能否定错误的痛点或意图假设。

## Related

- [ICP](id-0013-icp.md)
- [Search Intent](../20_concepts/id-0001-search-intent.md)
- [SEO Playbook](../30_playbooks/id-0011-seo-content.md)
- [Sales Call Playbook](../30_playbooks/sales-call.md)
