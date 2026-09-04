---
title: "交付清单模板（delivery-manifest.md）"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（delivery-manifest.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# 交付清单模板（delivery-manifest.md）

> 用途：新建站全部核验通过后，按本节生成交付清单（链接+说明+核验表）。AI 交付时必须产出此文件（ID-0007 D 判定 + 本模板）。
> 替换：`{{SITE_NAME}}` `{{SLUG}}` `{{DOMAIN}}` `{{SITE_ID}}` `{{THEME_ID}}` `{{DATE}}` 及全部内容行。

# {{SITE_NAME}} 交付清单（{{DATE}}）

- 站点：{{SITE_NAME}}（演示/正式 B2B 出口站）
- 账号清空：删除前 N 站（证据 `70_evidence/sites-before-delete-*.json`）→ 删除后 0 站
- 新站标识：siteId `{{SITE_ID}}` / slug `{{SLUG}}` / themeId `{{THEME_ID}}`
- 构建方式：纯接口（server action 写 + RSC 读），无浏览器模拟

## 一、公开链接（全部已核验 200）

| # | 链接 | 说明 | 核验 |
|---|---|---|---|
| 1 | https://{{DOMAIN}}/ | 首页（N 模块设计器组装） | 200 + gate 0 残留 |
| 2 | https://{{DOMAIN}}/products | 产品列表页 | 200 |
| 3 | https://{{DOMAIN}}/products/{{PRODUCT_SLUG}} | 产品详情：{{PRODUCT_NAME}} | 200 |
| 4 | https://{{DOMAIN}}/posts | 文章列表页 | 200 |
| 5 | https://{{DOMAIN}}/posts/{{POST1_SLUG}} | 文章：{{POST1_TITLE}} | 200 |
| 6 | https://{{DOMAIN}}/posts/{{POST2_SLUG}}（可选）| 文章：{{POST2_TITLE}} | 200 |
| 7 | https://{{DOMAIN}}/about-us | 公司介绍页 | 200 |
| 8 | https://{{DOMAIN}}/contact-us | 联系页 | 200 |
| 9 | https://{{DOMAIN}}/sitemap.xml | sitemap | 200 |
| 10 | https://assets.laicms.com/{{SLUG}}/{{IMG1}} | 图片：{{IMG1_NOTE}}（{{LICENSE}}） | 200 |

## 二、内容清单

| 类别 | 名称 | slug | 状态 |
|---|---|---|---|
| 产品分类 | ... | ... | 挂接到产品 |
| 文章分类 | ... | ... | - |
| 产品 | ... | ... | published（规格 N 项：...） |
| 文章 N | ... | ... | published（Slate 块数） |
| 模板清理 | 模板产品/文章清单 | - | 已删除，列表计数 0 |

## 三、核验记录

| 核验项 | 方法 | 结果 |
|---|---|---|
| 公开链接 | curl 页面+资源 | 全部 200 |
| sitemap | 解析 URL | 全覆盖 |
| 内链/资源 | fetch 全部 href/img | 0 bad |
| 模板残留 | skill check_template_residue.py（N 路由/N 术语） | pass=true 0 命中 |
| readback 对抗 | 每页提交后 RSC 深 diff | 仅无害回填 |
| 产品/文章归属 | RSC 读回 | 产品=产品分类；文章=文章分类 |
| 截图 | chrome headless | 截图路径（若有） |

## 四、已知事项（如实记录）

1. **表单提交链路**：是否实测提交（ID-0007 D-7）；demo 邮箱上线前必须替换并浏览器实提
2. **demo 值**：邮箱/电话/地址/社媒 URL 是否 demo；footer 标注
3. **平台边界**（ID-0007 C 表）：soft-404/og 缺失/多 H1/表单无 SSR
4. 后台不可删的分类/标签残留（若有）

## 五、如何复用

- 工具链：`interface-kit/`（索引 find → api/构建器/流水线）
- 本清单即交付产物；流程见 `interface-kit/ONBOARDING-PIPELINE.md` 2.10

## 内容完备性自检（DELIVERY 签发前必答，对抗"交付降级而不自知"）

- [ ] COP 承诺的每一类内容（产品/文章/页面）是否全部上线？未上线的每一项必须同时给出：① BLOCK 的部署实测证据（不是文档结论）② 解锁尝试记录（如 ISS-111 资格验证五步的执行结果）。两者缺一 = 不得签发，回到对应步骤继续。
- [ ] 导航/页脚是否仍有指向空内容区的入口（空文章列表、空分类）？
- [ ] brief/COP 与 DELIVERY 的数量基线是否逐项相等？
