---
title: "内容数量标准（CONTENT-MINIMUM.md）—— 界面美观与用户提供基线"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（CONTENT-MINIMUM.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# 内容数量标准（CONTENT-MINIMUM.md）—— 界面美观与用户提供基线

> 依据：AllinCMS 模板模块渲染行为实测（皮筏艇站走查 + 空态/推荐区观察，2026-08-29）。
> 原则：**数量门是"美观与不空态"的门，质量门另走三份对抗 checklist**（数量达标但内容空洞 = 不合格）。

## 一、最低数量（要求用户提供）

| 内容 | 美观基线 | 推荐区间 | 依据（模块行为） |
|---|---|---|---|
| **产品** | **≥3** | 4-6 | 列表页 full-product-list-filtered 3 列网格：1-2 个显稀疏；首页 products 模块卡不满；related 推荐区（若启用）需其他产品 ≥2 |
| **文章** | **≥4** | 5-8 | 列表页 2 列 ×2 行；首页 news featured+digest 卡满；post-related-grid 3 卡需其他文章 ≥3 |
| 产品分类 | ≥1 | 1-2 | 详情页分类标签/筛选 |
| 文章分类 | ≥1 | 1-2 | 同上 |
| 标签 | ≥2 | 2-4 | 列表页标签筛选/文章卡片 |
| 图片 | 每产品 1-2 张 + 公司页 1-2 张 | 同上 | hero/分类卡/详情图库；**同页不重复同一张**（image checklist） |

**硬性防空态底线**（无内容会渲染 "No content is available yet."）：产品 ≥2、文章 ≥3；
**当前皮筏艇站**：1 产品/2 文章 = 不出空态（已删 related+关 showToolbar 保底），但不达美观线 → 下批补到 3/4。

## 二、为什么是这些数字（对抗证据）
1. **related 空态**（ISS-025）：product-related-grid 需 ≥2 个"其它"产品；post-related-grid 需 ≥3 其它文章——数量不足即显示空态文案（用户可见）
2. **列表页稀疏感**：3 列网格 1-2 件 → 大片留白；2 列杂志格 1-2 篇 → 同样问题（截图复核结论）
3. **推荐区/关联内容**：首页 featured-product-list-showcase（featured 大卡 + 列表）、news 模块（featured 1 + digest 3）需要 3-4 个实体才能显示"满卡"效果
4. **转化路径**：买家进入列表页是想"选"，≥3 才有比较对象；单件页没有可比性（buyer decision 需要对比）

## 三、用户沟通话术（要求提供时）
> "为了保证首页/列表页/关联推荐区显示美观（不留白、不出'暂无内容'），请至少提供 **3 个产品（每个一句话说明+规格+图片）** 和 **4 篇文章主题/本地草稿（选题参考：选购指南/材质保养/使用技巧/公司动态）**；如果暂时没有，我可以用演示内容占位（会标注 demo），或按你现有资料先做骨架"
> 图片：每产品 1 张主图（无图请告知，我按 CC 素材代找并记录许可）

## 四、流程挂载位置
- 前置收集（client-input-checklist.md）：必填项第五条"资料文件"注明 **最低 3 产品/4 文章**
- brief validate（site_pipeline.py）：products<3 或本地文章计划 posts<4 → INVALID + 缺项提示；此门不授权远程 article.create；create 仍需当前部署 ISS-111 资格五步 + strict review + fresh capability
- 验收（ONBOARDING 2.9 / ID-0007 B6）：`python3 site_pipeline.py gate <slug>` 数量门 + 空态 + 模板词 + 200 一键检查，任一不过 = 不开上线
- 交付清单（delivery-manifest）：生成时先过 gate；不过则清单标记 "BLOCK: 数量不足（产品 N/文章 M）"

## 五、数量不足时的降级策略（保底不空态，可接受但标记）
1. 详情页删除 related 模块（document 可编辑）
2. 列表页 showToolbar=false（隐藏模板分类筛选）
3. 首页推荐/分类卡改成站内入口指向（指南/批发/联系）
4. 交付清单"已知事项"记降级原因（数量 ← 用户提供不足，未阻塞）
