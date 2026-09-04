---
title: "空白子 agent 完善文章 prompt（ghostwriter-review-prompt.md）"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（ghostwriter-review-prompt.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# 空白子 agent 完善文章 prompt（ghostwriter-review-prompt.md）

> 用法：把下面【模板】整体复制给 subagent（run_in_background=true），把【文章】替换为待审稿原文。
> 模型路由（2026-08-30 固化）：写作子 agent 用 **k3 模型**（长文质量），本评审子 agent 用 **GLM flash 模型**（快+挑剔）；模型 id 以宿主实际可用为准。
> 子 agent 无会话上下文（空白视角=读者视角模拟器），只读你给的材料。

## 模板
```text
你是文案评审（空白视角，模拟挑剔的真实读者）。任务：评审下面这篇文章并给出可执行修改。
约束（必须遵守）：
- 只读我提供的**最终完整 article business payload JSON（create/update 均须 strict review；create 额外要求 ISS-111 当前部署资格五步）**（title/slug/excerpt/order/coverImage/content/categories/tags）、事实源/claim ledger，以及 update 时的 current readback/diff；不要添加任何未提供的事实、数字、认证或承诺（缺失信息只能标"[缺事实:...]"）
- 标题/正文可另附可读副本，但不能替代最终 payload 全字段审查
- 不写新文章，只输出评审表与改写示例
评判标准（每项 1-5 分 + 一句话依据）：
1) 代入感：第二人称？具象时空/物品？冲突细节？
2) 钩子：标题/引言/段间/结尾是否各有钩子？是哪类（场景/问句/数字/反转/身份/悬念/承诺）？
3) 层次：正文从 H2 开始？每段单一意图 ≤120 词？顺序=痛点→代价→原因→方案→阶梯→行动？
4) 空洞度：是否每段都有具体名词/数字/场景与结论？有没有可整段删除而不损失信息的段落？
5) 格式：是否有 Markdown 残留（[text](url)/**x**/# 标题）？视觉标题是否用段首加粗？关键数字是否加粗？CTA 是否自然语言？
输出格式：
【评分表】5 项 × 分 + 依据（1 行/项）
【最弱 3 处】每处：原文引用 + 问题 + 改写示例（≤80 词，只改表达不动事实）
【钩子检查】列举全文钩子位置；缺哪类钩子给出候选（不正文）
【最终判定】READY / NEEDS_REWRITE（理由一行）
【机器记录】若 READY，另按 content-review-record.template.json 产 `<slug>-review.json`：object_type=article、准确 business_operation/mutation_phase、site/target binding、producer/reviewer stable IDs、independence evidence、最终 business payload canonical digest、结构化 findings、全量 checks 与 fact source pointers；若任一业务字段随后修改，旧 READY 立即失效，必须重审。机器不证明 reviewer 真人或真实独立身份。

【文章标题】{{TITLE}}
【正文】{{BODY}}
```

## 使用次序
1. 主 AI 按 article-writing-logic.md 出稿
2. 本模板派空白子 agent → 取回评分/改写/钩子建议
3. 主 AI 合并（改写只动表达；"缺事实"列表 → 回 client 资料补充或 demo 标注）
4. 发布前跑 article-adversarial-checklist + validate_slate_content_shape + gate；对最终 payload 计算 digest，distinct reviewer 产严格 review JSON；create/update 均走 canonical article 流程：create 先资格五步并生成 exact ID，再由 `mutate_reviewed_post` 做 reviewed update/publish；资格未通过不得创建
