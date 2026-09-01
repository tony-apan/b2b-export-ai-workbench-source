---
title: "模板资产使用说明"
type: "index"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-09-02"
canonical_entry: "README.md"
description: AllinCMS 建站工具包文档（README.md）
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# 模板资产说明（templates/）

这些文件是**已上线站的真实读回产物**（纯接口 RSC 读出），作为新站的字段参照与"骨架即用"模板：
换电脑时整个 interface-kit/ 复制走即可，不需要重新摸索接口或字段。

| 文件 | 内容 | 用途 |
|---|---|---|
| `product-payload-example.json` | 产品编辑态 defaultValues 全字段 | 新站产品 payload 参照（name/slug/description/order/media/mediaList/categories/tags/specifications/content） |
| `post-payload-example.json` | 文章编辑态 defaultValues 全字段 | 新站文章 payload 参照（title/slug/excerpt/order/coverImage/categories/tags/content Slate） |
| `home-page-example.json` | 首页三件套 `{pageDoc, globals, themeConfig}` | 首页骨架：11 模块真实结构 + 全站 globals + 主题配置 |
| `about-page-example.json` | 公司页三件套 | 公司介绍页骨架（story/stats/values/team 模块真实结构） |
| `about-page-example.json` 备注 | 同 above | - |
| `site-acceptance-v2.md` | 建站交付全量验收清单 v2：7 层 61 项 + 四轮对抗流程 + F1-F9 模块/表单摸索计划（TPL-023） | 步骤 12 三门通过后、DELIVERY 签发前逐项执行；巡检复用子集 |
| `content-review-record.template.json` | 产品 create/update、文章 exact-ID update 的严格 digest-bound READY 机器记录（TPL-024） | 独立 reviewer 审查最终全字段 business payload 后填写；site/target/operation/source/checks 全绑定 |
| `product-content-review-prompt.md` | 产品最终 payload 独立事实/规格/完整性审查 prompt（TPL-025） | 产品 create/update 前派与作者不同的 reviewer；与 content-review-gate / reviewed wrapper 配合 |
| `live-capability-context.template.json` | 当前 deployment/site/operation/expiry 能力上下文（TPL-026） | 远程产品 create/update 或文章 update 前只读发现并落私有证据；过期/跨站/缺 operation fail |

## 用法（对新站）
1. 新站建好后，产品/文章 payload 以 example 为字段骨架，替换文本/ID（分类 id 用新站建分类返回的 id）。
2. 首页三件套以 home-page-example.json 为底：用 `allincms_blocks.py` 重建（推荐），或直接改 example 的文案/媒体 URL（少字段时小心服务端回填——见 MODULES.md 第一节）。
3. 公司页/联系页以 about/contact example 为底重建。

## 骨架推荐工作流（零摸索）
```python
# 1) 从资料提炼 brief.json（字段见 site_pipeline.validate 输出）
python3 site_pipeline.py validate brief.json      # 必过
# 2) 生成 payload 集
python3 site_pipeline.py generate brief.json out/
# 3) 执行（allincms_api.py 按 ONBOARDING-PIPELINE.md 2.5-2.8）
# 4) 自检与验收
python3 site_pipeline.py check <public-html-dir>  # 模板词必须 CLEAN
```
