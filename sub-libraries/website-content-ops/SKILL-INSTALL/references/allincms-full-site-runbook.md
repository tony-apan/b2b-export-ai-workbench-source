---
title: "AllinCMS 完整建站 runbook 路由（supplemental）"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（allincms-full-site-runbook.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# AllinCMS 完整建站 runbook 路由（supplemental）

> 分类：supplemental。本文件只做路由，不定义 payload/action/授权（权威仍在 canonical adapter 与本机 operational 工具包）。

## 何时读

要完成**当前 Registry 支持的站点范围**（新建站 → 媒体/分类/产品/文章 → 主题 7 页/表单 → 审计与交付），读本机 operational 工具包的零上下文总入口。全新文章必须先跑当前部署 ISS-111 资格五步，再 create draft + reviewed update/publish；资格失败且有部署证据时才移除 Posts 入口并降级：

```text
<本机 customer-runtime>/00_shared/interface-kit/RUNBOOK-ANYONE.md
```

（运行时副本位于宿主机 runtime 根的 `00_shared/interface-kit/RUNBOOK-ANYONE.md`；不存在时先向主机求该目录。）

## RUNBOOK 覆盖的、canonical adapter 尚未注册的域

| 域 | canonical adapter 状态 | RUNBOOK 工具 |
|---|---|---|
| 主题创建/激活/路由（createTheme/setThemeActive/applyThemeRouteMapping） | 未注册 capability_route | `allincms_api.py` create_theme/set_theme_active/apply_theme_routes |
| 7 页文档/globals 设计提交（save+publish） | 未注册 | `allincms_api.py` save_home + templates 页面样例 |
| 文章页 CTA 真链接（material-story-split actionTarget） | 未注册 | RUNBOOK §3（正文内联 link 平台不支持） |
| 分类/标签创建 | category/tag create 有路由但无独立 module | `allincms_api.py` create_category2/create_tag |
| 13 项对抗审计 + 每站基线（audit/gate/contact 门） | 无 | `site_pipeline.py` audit/gate/contact --config |
| 平台已知边界与回落（根路径 /、页面 meta description、zod 空字段默认回填） | 无 | RUNBOOK §9 |

## 使用边界

- mutation 授权/指纹/capability 门禁仍以 canonical `content-run-controller.mjs` + Adapter 为准；RUNBOOK 工具是 operational 执行层，不得绕过 canonical 计划授权。
- 每站数量/CTA/FAQ 基线必须落在该站 `*-audit-config.json`（audit 默认基线是内置 demo 基线，缺 config 会误判）。
- 新坑必须回填 interface-kit `index/issues.tsv` 并 `registry_tools.py verify`。
