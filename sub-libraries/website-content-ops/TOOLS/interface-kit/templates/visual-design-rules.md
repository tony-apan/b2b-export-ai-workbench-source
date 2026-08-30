---
title: "品牌视觉规则（visual-design-rules.md）—— 网站审美执行准则"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
---

# 品牌视觉规则（visual-design-rules.md）—— 网站审美执行准则

> 来源：第三方专业评审（2026-08-29）+ 平台能力边界适配。**平台 CSS 层不可注入**（className 固定），以下规则为目标态，能落地的落地（内容/结构/图片选择/CTA 模块），不能落地的记录为平台边界。

## 1. 视觉方向（每站开工前定）
- 默认建议：克制、安静、可靠（**engineering editorial**：信息优先，不做装饰堆砌）
- 元规则：**视觉组件服务于信息理解**；禁止用于掩盖内容不足

## 2. 可以落地的结构化规则（AllinCMS 平台内）
| 规则 | 实现方式 |
|---|---|
| 首屏 5 秒给答案 | **Quick Answer / 三数字总览**：正文第 1-2 个 callout 用 QUICK ANSWER 标签（三数字+边界声明） |
| 参数视觉锚点 | 关键数字加粗+统一格式（5.2 m / 68 cm / 220 kg） |
| 单位统一 | **全站统一空格**模式：5.2 m / 68 cm / 220 kg / 80 kg；写 “5 m or more”（禁 5m-plus / 5.2m 混用） |
| 章节节奏 | 段首加粗句=章节标题（01 LENGTH / 02 BEAM / 03 LOAD），短段落 1-3 句 |
| 专业提示 | callout 用 FIELD NOTE / CHECK BEFORE YOU BUY 标签（每篇 2-4 个，不用 emoji） |
| 可扫描 | 每 3-4 段一个视觉锚点；每逻辑段后空段（段落间隔） |
| 真链接 CTA | **详情页模板 document 加产品推荐模块/contact 模块**（渲染真 <a>）；不依赖正文文本 |
| 图片来源可见 | 文末 callout 放 Photo credit（作者+许可）——不只在 alt |
| 数字边界 | 每个参数带"参考值/该产品规格/以厂家为准"声明（不绝对化） |
| 移动端 | 参数纵向排列（callout 文本自动换行）、CTA 不低于 44px（模块按钮）、无横向溢出 |

## 3. 记录为平台边界（勿浪费工时）
- 字号/颜色/间距 CSS——平台固定
- 正文 H2/H3 语义、正文内联链接、正文图片——渲染器不支持
- FAQ 模块只有加在模板页有语义

## 4. CTA 文案原则（来自评审）
- 不用 Learn more / Get a Quote 裸词；用收益句："Compare the Demo Product specifications" / "Get help choosing your tandem kayak"
- CTA 模块置于"解释完之后"（先给判断方法再给产品）
- 主/次按钮：主=产品规格，次=咨询/推荐

## 5. 品牌感红线
- 正式站：**删除所有 demo/synthetic/qualification 公开文案**（footer/产品描述/产品页）；演示站：noindex 处理+不对外
- 图片：产品主体清晰、少人物遮挡、移动端裁切不丢主体；同站摄影风格统一
