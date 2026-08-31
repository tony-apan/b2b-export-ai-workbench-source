---
title: "写作模块（WRITING-INDEX.md）—— 独立可调用，入口在此"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（WRITING-INDEX.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# 写作模块（WRITING-INDEX.md）—— 独立可调用，入口在此

> 写文章 = 调用本模块。资产按"五步调用链"组织，每一步都有规范 + 检查 + 工具。**不要再散找规范。**

## 五步调用链（从素材到上线）

```text
① 素材     client-input-checklist.md 第六节（写作前置素材 5 项——先要）
② 骨架     writing-module.py outline <brief.json>   → 自动生成六段式骨架+渐进层级+钩子提示
③ 成稿     派【写作子 agent：k3 模型】给 BRIEF.md（facts+主题+Slate 规范）+ article-writing-logic.md
           （六段式）+ PROGRESSION.md（四阶段递进）+ visual-design-rules.md + MODULES 三·五
④ 评审     派【评审子 agent：GLM flash 模型】ghostwriter-review-prompt.md（空白视角 5 维评分+最弱 3 处+钩子检查）
           writing-module.py check <article.json> → 机器渐进检查（6 项）
⑤ 发布     article-adversarial-checklist.md（发布前审查）→ publish → site_pipeline.py audit <slug>
```

## 资产表（本模块=入口；原件位置不变，全部经此路由）

| 角色 | 资产 | 位置 |
|---|---|---|
| 素材 | client-input-checklist 第六节 | templates/ |
| 骨架生成器 | writing-module.py（outline/check 子命令） | writing/ |
| 递进规范 | **PROGRESSION.md**（本目录，四阶段模型） | writing/ |
| 创作逻辑 | article-writing-logic.md（六段式/钩子库/五·四决策页增强） | templates/ |
| 评审 prompt | ghostwriter-review-prompt.md（5 维） | templates/ |
| 发布前审 | article-adversarial-checklist.md（A-F 六节） | templates/ |
| 页面/图片/SEO/视觉 | page-/image-adversarial-checklist.md · seo-check.md · visual-design-rules.md | templates/ |
| 内容质量合同 | canonical PLAYBOOKS ID-0001（六槽 pain chain/证据/禁声明） | sub-libraries/… |
| 内容质量合同 | ID-0001（质量合同）· ID-0003（优化 SOP）· ID-0004（stage patterns） | sub-libraries/… |
| 模板 | article-brief/draft/quality-review · customer-voice-to-content | canonical TEMPLATES/ |
| 机器检查 | check_content_quality.py · validate_slate_content_shape.py | skill scripts/ |
| 平台门 | MODULES 三·五（Slate 白名单：heading/link 平铺 ❌；callout ⚠️ emoji 弃用） | MODULES.md |

## 其他写作相关规范（本仓库完整清单，防遗漏）

- 数量基线：CONTENT-MINIMUM.md（产品≥3/文章≥4）
- 内容字段：site-content-checklist.md（品牌/分类/产品/文章/公司/联系/首页逐字段）
- 客户声音→痛点：customer-voice-to-content.md（canonical）
- 反对抗评审协议：OUTSIDER-REVIEW.md §3（评审回应前先 audit）

## 调用示例

```bash
# 骨架生成（从 brief 提取产品/文章字段 → 输出 JSON 骨架 + 渐进提示）
python3 writing/writing-module.py outline <tmp>/kayak-article.json
# 渐进机器检查（阶段顺序/承上启下/术语/边界/CTA 时机）
python3 writing/writing-module.py check <tmp>/kayak-article.json
# 空白 agent 评审（5 维）
#   复制 templates/ghostwriter-review-prompt.md 填入文章，派 subagent
# 发布前综合门
python3 site_pipeline.py audit <demo-site-key>
```
