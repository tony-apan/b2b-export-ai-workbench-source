# AllinCMS 建站上线 SOP（0 → 1 纯接口流水线）

目标：拿到「公司/产品介绍文档」后，AI 按本文档直接执行，无需再摸索接口；一份资料 → 一个新站全量上线。
所有命令均可复制粘贴；所有验证点都有输出判据。

> **⛔ 永久禁令**：见 [RUNBOOK-ANYONE.md](RUNBOOK-ANYONE.md) 顶部横幅（2026-08-30 用户指令，四项平台层检查永不涉及）。
>
> **零上下文新人先读 [RUNBOOK-ANYONE.md](RUNBOOK-ANYONE.md)**（10 步总入口 + 实测事实表 + 平台 BLOCK 回落表 + k3 写/flash 审工作流）；本文档是细节 SOP，RUNBOOK 是地图。

---

## 0.0 索引优先（AI 的第一步，任何任务通用）
```bash
cd interface-kit/index && python3 registry_tools.py find <关键词>
# 例：find 回填 / find 表单 / find 分类 / find 模块名
```
- 找模块字段 → `modules.tsv`；找历史坑 → `issues.tsv`（现象→根因→修复一步到位）；找文档/脚本 → `doc-registry.tsv`
- 查不到或遇到新问题 → 解决后**回填**：issues.tsv 加行（fixed/boundary/pending）+ doc/modules 相应登记 + `verify` + `gen`
- **硬 gate（ISS-065）**：任何新站/新任务的第一动作必须是 `find <关键词>` + `verify`；跳过索引直接动手 = 重复已回填的坑（ISS-001/002/003/018/024/059 均为重复踩坑）。验收时 audit 的 count 项=该站实建数才算过（不是提示，是门）。

---

## 0.1 环境准备（任何机器，先装后用）
```bash
python3 install-deps.py --yes                 # 检测+安装缺失依赖（docs-parse 选装）
python3 install-deps.py --verify              # 复检 PASS 即就绪
python3 index/registry_tools.py verify        # 索引完整性
```
依赖全景与各平台命令见 [SETUP.md](SETUP.md)；核心工具零第三方依赖（Python stdlib only）。

## 0. 一次性准备（新机器/新部署才需要）

```bash
# 0.1 环境
#  - Python 3（mac/win/linux 均可），本目录 interface-kit 完整复制即用
#  - token：工作台登录后 Cookie payload-token（JWT），推荐存 WS_TOKEN 环境变量（跨平台）；或 chmod 600 文件

# 0.2 校验部署 id 与 action id（同一部署不重扫；换部署/升级必扫）
python3 scan/scan-actions.py <token> /sites            # 输出当前部署所有 action id
# 若与 allincms_api.py 顶部常量不一致 → 更新常量（用错 id 静默返回 {}！）

# 0.3 冒烟
python3 allincms_api.py <token> read-sites             # 预期：站点列表 JSON
```

## 1. 输入资料 → 提炼清单（AI 第一步）

**先向用户收集必要资料（缺项阻塞，模板：`templates/client-input-checklist.md`）：**
1. 公司/品牌名称；2. 用户昵称/职位；3. 联系方式（邮箱/电话/WhatsApp）；4. 地址；5. 产品/公司资料文件（PDF/DOCX/网页等）

解析流程：资料 → Markdown（宿主解析，保留来源定位）→ 事实抽取（confirmed/inferred/missing）→ 对照「建站必备内容清单」（`templates/site-content-checklist.md`，全站内容=品牌层/分类/产品/文章/公司页/联系页/首页模块/素材/替换清单）→ 缺口清单与用户对齐 → brief.json。

产出 `brief.json`（结构见 `templates/brief-schema.json`）：
- `site`: name / slug / description / display 域名
- `brand`: title / tagline / cta 文案 / 社媒账号（无则 []）
- `contact`: email / phone / address / hours / whatsapp / 地图坐标（无则缺省）
- `bottles→products`: 每产品 name / slug / description / specs[{key,value}] / priceLabel / media 图
- `posts`: title / slug / excerpt / content blocks（Slate: p|h2|h3|blockquote，服务器原生词法）/ coverImage
- `story`: intro / story / stats / values / team（公司介绍页用）
- `nav`: 主导航结构；`home_plan`: 用哪些首页模块（默认全 11 模块）

**提炼规则（防模板残留）**：所有文案必须来自资料（或合成示例但标注 demo）；不得复用模板词（自检词表见 MODULES.md 六）。
**验证规则**：`python3 site_pipeline.py validate brief.json` 必须 VALID 才继续。

## 2. 执行顺序（依赖图）

```
1 建站        2 分类          3 标签          4 媒体        5 产品          6 文章
create_site  → category×N    → tag×N        → upload_media → create+publish  → create+publish
7 设计器组装（首页/公司/联系页 document+globals）→ 8 全站 globals 统一 → 9 验收
```

### 2.1 建站
```python
api.create_site(name, description)   # 返回 {data:{id,...}}；slug 从响应或 read_sites 取
site = api.read_sites()["sites"][0]  # 校验唯一新站
```

### 2.2 分类（posts 与 products **分开建**，contentType 必填）
```python
api.create_category2(slug, site_id, "文章分类 A", "a-slug", content_type="posts", cover=None)
api.create_category2(slug, site_id, "产品分类 A", "product-a", content_type="products", cover=None)
# cover 必须显式传（None 合法；缺省报 validation error）
# 产品分类 slug 约定 product- 前缀，写入产品 categories 用 id 字符串数组
```

### 2.3 标签
```python
api.create_tag(slug, site_id, "标签名", "tag-slug")
```

### 2.4 媒体（先上传，URL 用于产品/文章/首页）
```python
r = api.upload_media(slug, site_id, "photo.jpg", title="...", alt="...")
# r["media_urls"] 为 assets URL；注意：URL 必须带扩展名（.jpg/.webp），否则运行时 404！
# 图片素材：Wikimedia/Unsplash 等可商用来源；记录 license 到证据
```

### 2.5 产品（每个产品：create → publish）
```python
p = {"name":..., "slug":..., "description":..., "order":0,
     "media": {"type":"image","value":{"name":...,"alt":...,"type":"image","source":"url","url":URL}},
     "mediaList":[同 media]，"categories":[产品分类id]，"tags":[],
     "specifications":[{"key":"Capacity","value":"500 ml"}, ...],
     "content":[]（可选 Slate 块）}
r1 = api.create_product(slug, site_id, p)          # 得 productId
r2 = api.publish_product(slug, site_id, pid, p)    # 得 status published
```

"### 2.5b 文章创作流程（先要→逻辑→子 agent→验收）
1. **先要**（client-input-checklist 六）：客户原话≥3/真实数据/案例/图/客群描述——缺则先索要（或书面确认 demo）
2. **出稿**：按 templates/article-writing-logic.md 六段式骨架（H2 开始/钩子/代入感）
3. **空白子 agent 完善**：templates/ghostwriter-review-prompt.md 派空白 agent（评分 4 维+最弱 3 处改写+钩子检查）→ 合并建议（不改事实）
4. **验收**：article-adversarial-checklist + `writing/writing-module.py check <article.json>` + gate + 模板词

### 2.6 文章（Slate content：`{"type":"p"|"h2"|"h3"|"blockquote","children":[{"text":"..."}]}`——服务器原生词法；heading/paragraph 旧词法禁用，见 FORMAT-SPEC）
```python
p = {"title":..., "slug":..., "excerpt":..., "order":0, "coverImage":media,
     "categories":[文章分类id]，"tags":[]， "content":[Slate blocks]}
api.create_post(...) → api.publish_post(...)
```

### 2.7 页面组装（首页/公司页/联系页）
```python
from allincms_blocks import *
doc = page_document([
    ("carousel-campaign-1", carousel([slide(...), slide(...)], [service_item("truck","Export shipments","...")])),
    ("categories-1", category_grid(...)), ("hero-commerce-1", hero(...actions/service_items/campaign_pills 全传)),
    ("features-1", feature_grid(...)), ("products-1", product_showcase(...)),
    ("materials-1", material_split(...)), ("proof-1", proof_quotes(...)),
    ("news-1", news_list(...)), ("faq-accordion-1", faq(...)),
    ("newsletter-inline-1", newsletter(...)), ("contact-1", contact_split(...)),
])
# 公司页：breadcrumb/about_intro/company_story/company_stats/company_values/company_team
# 联系页：breadcrumb/contact_header/contact_info(social_links=[]!)/location_map/contact_split
# 关键：所有可显示字段显式传（见 MODULES.md 服务端回填坑）
```

### 2.8 提交（每页 save → readback 零 diff → publish）
```python
api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, theme_cfg, intent="save")
rb = api.read_page_document(slug, theme_id, page_id)   # 深度 diff，只允许 columnCount 无害回填；formSlug="" 在表单块=断裂必修（ISS-076，绑真实 slug）
api.save_home(..., intent="publish")
```
**globals 按页存储**：new site 时从任一页 readback 取 globals/themeConfig 为底，**对全部页面列表重交**：
```python
for p in api.read_pages(slug, theme_id)["pages"]:
    doc = api.read_page_document(slug, theme_id, p["id"])["initialPayload"]["page"]["document"]
    api.save_home(slug, theme_id, p["id"], site_id, doc, globals_doc, theme_cfg, intent="save")
    api.save_home(slug, theme_id, p["id"], site_id, doc, globals_doc, theme_cfg, intent="publish")
```

### 2.9 验收（三步全过才算上线）

> **根路径首页（2026-08-30 新增，ISS-070）**：主题激活会清空 homePageId，验收前必须补一步（顺序：先激活后设首页）：
> ```python
> home_page_id = [p['id'] for p in api.read_pages(slug, theme_id)['pages'] if p['path'] == '/home'][0]
> api.set_home_page(slug, site_id, theme_id, home_page_id)   # 之后 curl 根路径应 __next_error__=0
> ```
> **createTheme(default) 会重种 3+3 demo（ISS-071）**：审计前先跑 `python3 delete-demo-content.py <slug>`。
```bash
# A. readback 对抗：每页 diff≈0（见 2.8）
# B. 对抗审计（推荐首位，替代手工清单部分）——**必带每站 --config**（ISS-063）：
python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json --out 70_evidence/audit-report.json
#    13 项自动化：数量/200/空态/模板词/demo 联系方式/FAQ 答案 SSR/真实 CTA/单位/绝对化/Markdown 残留/h2 语义/根路径首页(root-home)/表单渲染(form-render)——全 PASS 才上线
#    每站 --config 基线（pages/count/faq_answers/cta/units）从内容计划(COP)取实建数，不得沿用他站（旧口径 14/15/16 项已作废；root-home=根路径真实首页、form-render=表单真实渲染）
# C. 截图人工复查（chrome headless），检查：导航链接、轮播、分类卡、规格面板、footer 无假社交链接
python3 allincms_api.py <token> read-sites / read-posts / read-products / read-pages / read-doc / read-media
python3 site_pipeline.py contact <slug> --real "<真实联系方式|分隔>"
```

### 2.10 产出交付清单（**必做**，用户最终交付物）
```bash
python3 templates/delivery-manifest.md 模板 → 填为 70_evidence/DELIVERY-<SLUG>-<DATE>.md
```
清单必须含：**公开链接表**（带说明与核验列）、**内容清单表**、**核验记录表**、**已知事项**（表单链路/demo 值/平台边界）。
范例：保温杯站 `70_evidence/DELIVERY-KAYAK-20260829.md`（皮筏艇站完整交付清单）。
判定：链接表每行核验列非空且为 200；核验记录每项有方法+结果；已知事项如实列出（不得隐藏形式 500/demo 值）。

## 3. 关键 ID 恒等式（<demo-site-key> 参考，新站替换）
- siteId=6a91e2fa8333e0ece4a6852e / themeId=6a91e2fa8333e0ece4a68580 / homePageId=6a91e2fa8333e0ece4a68762
- 页面：About 6a91e2fb8333e0ece4a687ad / Contact 6a91e2fb8333e0ece4a687bc / Posts 6a91e2fb8333e0ece4a6878f / Product 详情 6a91e2fb8333e0ece4a68780（新站用 read_pages 拿，勿猜）

## 4. 边界与坑（务必读）
1. **服务端回填默认**：未显式字段会被模板默认值填充（文案/假链接！）→ 全显式 + readback diff
2. **header 导航 children 必须递归 dict**，否则丢弃回填模板 "Bags"
3. **globals 按页存储** → 全站统一要重交 7 页
4. **action id 部署相关** → scan-actions.py 重扫；用错静默 {}
5. **media URL 带扩展名**；**分类/标签写入 id 数组**（读回是对象数组）
6. **Slate content 验证过的块**：p/h2/h3/blockquote（服务器 read_post 实测存储词法；link/image/list 平铺禁用，见 MODULES 三·五）
7. **地图 tile 依赖外部服务**，公网可能显示灰块（数据正常）
8. **公网 CDN 缓存**：publish 后 5-10s 生效，验收以列表页数据源+counter 为准；删除类操作以列表计数为权威
9. 登录成功分支（Set-Cookie 提取）未实测——token 由浏览器 Cookie 提供；不要尝试暴力登录

## 5. 换机快速开始（mac/win 通用）
1. 复制 `interface-kit/` 整目录到新机器（含 templates/）
2. `pip` 不需要；python3 直接跑
3. token 从浏览器 Cookies 获取（工作台登录后）
4. `python3 allincms_api.py <token> read-sites` 冒烟 → 按本文档执行
