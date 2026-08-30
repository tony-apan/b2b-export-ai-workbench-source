---
title: "模板资产使用说明"
type: "index"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
canonical_entry: "README.md"
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
