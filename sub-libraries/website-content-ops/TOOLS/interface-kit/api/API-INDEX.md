# 接口模块（API-INDEX.md）—— AllinCMS 纯接口 · 独立入口 · 快速调用

> 模块组成：`allincms_api.py`（客户端本体，interface-kit 根，零依赖）+ 本目录：
> - `API-INDEX.md`（入口：模块图/端点矩阵/action id 表/快速调用/常见错误）
> - `api-ref.tsv`（机器可读快查表：操作|method|endpoint|action_id|payload 摘要|返回|坑|示例——grep 即用）
> 任何"调接口"任务先读本文件；换部署后 `python3 scan/scan-actions.py` 重扫并更新 api-ref.tsv。

## 一、模块图
```text
AllinCMS(token=JWT)
├── 写（POST + next-action header；Cookie payload-token / Origin+Referer workspace / x-deployment-id）
│   ├── 站点 create_site/delete_site │ 分类 create_category2 │ 标签 create_tag
│   ├── 媒体 upload_media/update_media │ 产品 create→publish │ 文章 create→publish
│   └── 设计器 save_home(slug, theme_id, page_id, sid, doc, globals, cfg, intent)
├── 读（GET path?_rsc + RSC:1 → 组件 props 即数据）
│   read_sites / read_lists / read_pages / read_page_document / read_product / read_post / read_media_library / read_site_info
└── CLI：allincms_api.py read-* �；site_pipeline.py validate|generate|check|diff|gate|contact|audit
```

## 二、端点矩阵（速查；写接口明细见 api-ref.tsv）
| 数据 | 路径 | 方法 |
|---|---|---|
| 站点列表 | GET /sites?_rsc | read_sites |
| 文章/产品列表+分类选项 | GET /{slug}/posts\|products?_rsc | read_lists |
| 主题页面+routes | GET /{slug}/themes/{themeId}?_rsc | read_pages |
| 设计器三件套 | GET /{slug}/themes/{themeId}/{pageId}/design?_rsc | read_page_document |
| 产品/文章编辑态 | GET /{slug}/products\|posts/{id}/update?_rsc | read_product/read_post |
| 媒体库/站点信息 | GET /{slug}/media·site-info?_rsc | read_media_library/read_site_info |

## 三、action id 表（完整见 api-ref.tsv）
SIGNIN 7f04a5d5… ｜ CREATE_SITE 7fedc609… ｜ DELETE_SITE 7f2dd4d4… ｜ CREATE_CATEGORY 7f6253b1…
CREATE_TAG 7fe79a75… ｜ UPLOAD_MEDIA 604a958f… ｜ UPDATE_MEDIA 7fa3dd69… ｜ CREATE_PRODUCT 7f63f8f4…
DELETE_PRODUCT 7ff4cdbd… ｜ UPSERT_PRODUCT 7f0d6abc… ｜ CREATE_POST 7fdfe828… ｜ DELETE_POST 7f0be185…
UPSERT_POST 7f205ad6… ｜ COMMIT_DESIGN 7ff10702…

## 四、快速调用（copy-paste）
```python
from allincms_api import AllinCMS
api = AllinCMS(token=open("/tmp/ws-token.txt").read().strip())
sites = api.read_sites()["sites"]                      # ① 冒烟
api.create_category2("<demo-site-key>", SID, "Guide", "guide", content_type="posts", cover=None)
api.upload_media("<demo-site-key>", SID, "photo.jpg", title="t")   # media_urls 是全量累积→取差值
api.create_product(...) → api.publish_product(slug, sid, pid, {...})   # payload 必带 siteId；media 扁平
api.create_post(...) → api.publish_post(...)
api.save_home(slug, theme_id, page_id, sid, doc, globals, cfg, intent="publish")
# 读回：read_page_document → initialPayload.page.{document,globals,themeConfig}
```

## 五、常见错误速查（→ ISS 编号）
| 现象 | 根因/解法 |
|---|---|
| 返回 {} | action id 部署失效→重扫（ISS-006） |
| validationErrors.siteId | payload 缺 siteId（ISS-020） |
| media.source 校验错 | 写入扁平 {name,alt,type,source,url}（ISS-021） |
| draft slug 时间戳 | publish 带正确 slug+id（ISS-022） |
| 分类事务号不匹配 | 原样重试一次（ISS-024） |
| 媒体 URL 404 | 带扩展名（ISS-004） |
| upload 返回全量 URL | 差值取最新（ISS-019） |
