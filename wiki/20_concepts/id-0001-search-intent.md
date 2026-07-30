---
doc_id: "ID-0001"
title: "Search Intent"
description: "面向把客户语言和搜索证据转成页面任务的人与 AI，说明意图识别、页面映射和验证指标；不把单次聊天或 query 假设当作市场事实。"
type: "concept"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md", "User direction on 2026-07-26"]
related: ["index.md", "../40_business/id-0012-customer-pain-map.md", "../30_playbooks/id-0011-seo-content.md", "../30_playbooks/id-0010-geo-ai-search.md", "../50_channels/seo/index.md", "../50_channels/geo-ai-search/index.md", "../_templates/customer-voice-to-search-intent.md"]
confidence: "high"
review_after: "2026-10-26"
when_to_read: "当需要把客户语言、搜索查询或市场证据转换为页面主题、内容 brief 和验证指标时，先读本页；不要把单次聊天直接当作市场事实。"
keywords: ["search intent", "搜索意图", "客户语言", "query hypothesis", "页面映射", "SEO"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Search Intent

## 核心判断

搜索意图不是一个关键词标签，而是用户在特定情境下想完成的任务：他遇到了什么问题、为什么现在要解决、已经知道什么、下一步想做什么、需要什么证据才会继续。

客户聊天、询盘、销售电话和客服问题是识别搜索意图的重要一方信号，因为客户会用自己的语言描述触发事件、痛点、替代方案、疑虑和期待结果。但聊天内容不等于真实搜索词：销售对话中的长句、上下文和产品提示，通常需要转换成用户独自面对搜索框时会输入的问题。

```text
客户原话
→ 情境与触发事件
→ 表面问题与深层痛点
→ 想完成的任务
→ 购买/决策阶段
→ 可能搜索的问题
→ 需要的页面与证据
→ 发布验证
```

## 五层意图

| 层 | 要回答的问题 | 示例输出 |
|---|---|---|
| Situation | 客户在什么情况下提出问题？ | 新市场开发、回复率下降、供应商比较 |
| Pain | 什么让他损失时间、金钱、机会或信心？ | 名单不准、无法判断采购意向、缺少可信证据 |
| Job | 他真正想完成什么任务？ | 找到符合条件的潜在客户并获得回复 |
| Stage | 他处于问题、方案、比较还是行动阶段？ | problem-aware / solution-aware / comparison / action |
| Evidence | 什么信息能帮助他继续决策？ | 方法、清单、案例、数据、对比、产品事实 |

## 常见搜索意图与页面映射

| 意图 | 常见客户语言 | 可能的搜索表达 | 优先页面 |
|---|---|---|---|
| 认识问题 | “为什么一直没人回复？” | why cold emails get no replies | 诊断文章、问题指南 |
| 学习方法 | “应该怎么找采购负责人？” | how to find purchasing managers | 教程、步骤页、工具页 |
| 比较方案 | “这个和数据库有什么区别？” | solution A vs solution B | 对比页、替代方案页 |
| 判断适用性 | “适不适合我们这个行业？” | best solution for [industry/use case] | 行业页、应用场景页 |
| 降低风险 | “数据准不准？会不会封号？” | accuracy / compliance / risk questions | FAQ、方法说明、合规页 |
| 准备行动 | “价格多少？怎么开始？” | pricing / demo / supplier / service | 产品页、落地页、联系页 |
| 验证供应商 | “你们有没有类似案例？” | brand reviews / case study / company credibility | 案例页、关于页、证据页 |

## 从聊天到搜索词不能直接跳

真实客户原话先保存在私有 raw 或客户运行区；公开知识层只保留处理后的表达。虚拟演示可以保留完整表达，但必须标注虚构。转换时至少补齐：

1. **对象**：谁遇到这个问题？
2. **场景**：什么时候发生？
3. **任务**：他想完成什么？
4. **阻碍**：为什么当前方案不行？
5. **结果**：他希望得到什么？
6. **阶段**：是在学习、比较还是准备行动？
7. **证据**：页面需要什么事实、案例或限制条件？

然后再形成多种 query hypothesis：短词、问题句、场景词、比较词、风险词和行动词。不要把每个假设都当作真实需求。

## 证据梯度

| Evidence | 说明 | 可支持的结论 |
|---|---|---|
| 单次聊天 | 一个客户在特定上下文中的表达 | 生成待验证假设 |
| 多次独立聊天重复 | 多个客户重复相似问题 | 提升痛点优先级 |
| 聊天 + Search Console query | 客户语言与真实搜索数据相互印证 | 建立或刷新页面 |
| 聊天 + SERP/竞品/社区 | 市场存在同类公开问题 | 判断页面类型与内容差距 |
| 页面表现 + 有效询盘 | 搜索需求与业务价值同时成立 | 沉淀为较高置信度知识 |

不使用单条客户聊天直接推出“市场都这么想”。

## 验证方法

发布前验证：

- SERP 中主流页面是否回答同一个任务，而不只包含同一个词。
- 页面类型是否匹配：教程、产品页、对比页、案例页或 FAQ。
- 公司是否有足够产品事实和证据回答，而不是靠 AI 补全。
- 内容是否能自然连接到下一步 CTA。

发布后验证：

- Search Console 的 query、impression、click、CTR 和 landing page。
- 进入页面的用户是否符合 ICP。
- 询盘、聊天和销售反馈是否再次出现同类问题。
- 内容有没有吸引错误需求或产生新的异议。
- 成功和失败结论是否回写客户痛点、搜索意图、messaging、offer 和 playbook。

## Related

- [Customer Pain Map](../40_business/id-0012-customer-pain-map.md)
- [SEO Playbook](../30_playbooks/id-0011-seo-content.md)
- [GEO Playbook](../30_playbooks/id-0010-geo-ai-search.md)
- [Customer Voice To Search Intent Template](../_templates/customer-voice-to-search-intent.md)
