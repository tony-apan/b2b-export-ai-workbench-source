---
title: "RUNBOOK-ANYONE.md —— 任何人零上下文建站手册"
type: "runbook"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
sources: ["Example 全流程实战 2026-08-29/30（7 产品+3 文章+10 媒体+7 页主题）", "ONBOARDING-PIPELINE.md", "OUTSIDER-REVIEW.md §3", "issues.tsv ISS-001..065"]
related: ["ONBOARDING-PIPELINE.md", "allincms_api.py", "site_pipeline.py", "allincms_blocks.py", "writing/WRITING-INDEX.md", "MODULES.md"]
---

# RUNBOOK：任何人拿到 interface-kit 即可建一个完整 AllinCMS 站

> 拿到客户资料后先读 [NEW-SITE-ONEPASS.md](NEW-SITE-ONEPASS.md)（13 步一条龙：资料→brief→COP→内容→主题→审计→交付）；本文档是流程细节与事实/回落库。

> 本手册是**零上下文总入口**。不假设你见过 Demo/Example/保温杯任何先例。
>
> **⛔ 永久禁令（用户指令 2026-08-30）**：lang / canonical / JSON-LD / img-attrs 这 4 项**禁止检查、禁止报告、禁止讨论**。它们是平台层行为，不属站内职责——审计已永久移除，文档已永久清除。任何 AI 不得以任何理由重新加回或提及。
> 铁律：**先读 §0（index-first），踩坑先 `find`，新坑必须回填**。任何"我猜平台支持"的字段先查 MODULES.md 与 `templates/*.json` 实测样例。

## §0 前置（一次性，5 分钟）

```bash
mkdir -p <任务目录>/70_evidence          # 工作目录 = 该站点任务目录（所有产出/证据/审计配置都放这里，路径在文档里一律写全）
cd <interface-kit 目录>            # 内含 allincms_api.py / site_pipeline.py / allincms_blocks.py / templates / writing / index
python3 index/registry_tools.py verify     # 索引完整 -> PASS
python3 index/registry_tools.py find <你的任务关键词>   # 必做：上传/分类/主题/文章/审计 等
WS_TOKEN=<token> python3 scan/scan-actions.py - /<site_key>/themes   # 部署更新后重扫 action id（42 位 hex）；新 id 回填 allincms_api.py 常量（也支持传 token 文件路径）
```

- 凭据：`payload-token` JWT **优先 `export WS_TOKEN=<token>` 环境变量（跨平台推荐）**；或写 token 文件（chmod 600）后传路径。获取方法（二选一）：
  1. **纯 API（ISS-083）**：`api = AllinCMS(email=..., password=...)`——login() 会 POST sign-in 并从响应 Set-Cookie 提取 token**（成功+失败路径均实测 2026-08-30：email/password → Set-Cookie 提取 token → 读写全权限验证通过）**。
  2. **浏览器 Cookie（兜底，已验证）**：用户登录 `workspace.laicms.com` → DevTools → Cookies → 复制 `payload-token` → `export WS_TOKEN=<token>`。
  **拿 token 是唯一可能碰浏览器的环节；拿到后全程纯接口**（操作矩阵 10/10 实测：读 8 + 幂等写 2 + 媒体 multipart + 公开站表单 submit，零浏览器）。
- 目标：工作台 `workspace.laicms.com`，公开站 `https://<site_key>.web.allincms.com`。
- 路径约定：本文内 runtime 相关路径相对于**运行时根 `$RUNTIME_ROOT`**（独立 runtime 目录；母库内经 `customer-runtime/` 软链可达）；`templates/...`、`writing/...`、`index/...` 相对于 interface-kit 目录。
- 零第三方依赖：Python3 stdlib 即可；全文 API 直连，**不要开浏览器自动化**（除登录拿 token）。

## §1 建站总流程（10 步）

```text
0 index-first + verify
1 读源材料 -> 提炼 brief.json（site/brand/contact/products/posts/nav/story）
2 validate brief -> 定 COP（内容计划）：每站数量基线 + 文章主题 + 分类/标签
3 Plan A：create_site（拿到 site_id/site_key）——站点已存在则 read_sites 选目标
4 媒体：upload_media × N + update_media 回写 title/alt/caption
5 分类/标签：create_category2（cover 显式 null）/ create_tag
6 产品：create_product -> publish_product（全字段 payload，见 templates/product-payload-example.json）
7 文章：k3 子 agent 写（§7）-> flash 子 agent 审（§8）-> create_post -> publish_post
8 主题页：create_theme(default) -> 改 7 页 doc + globals -> 每页 save+publish -> set_theme_active -> apply_theme_routes
9 每站审计配置（templates/site-audit-config.template.json 复制改名）-> audit/gate/contact 三门
10 交付清单 DELIVERY-<slug>-<date>.md + HANDOFF.md + 回填 issues.tsv
```

## §2 关键事实（已实测，别重踩）

| 事实 | 结论 | 出处 |
|---|---|---|
| 账号非首站时 createSite 只给 blank 主题（0 页）；手工 `create_theme(preset='default')` 总是生成 7 页 | 必须手工 create_theme | allincms_api.create_theme docstring（与 createSite 行为区分） |
| **根路径 `/` 修复=set_home_page**：`api.set_home_page(slug, site_id, theme_id, home_page_id)`（action=setHomePageAction，URL 必须是 `/{slug}/themes/{themeId}`）。**顺序：先 setThemeActive 再 set_home_page**（激活会清 homePageId）。其余路径（/{slug}/themes）返回 200 但静默无效 | ✅ **可修（2026-08-30 实测上线）** | allincms_api.set_home_page + 任务证据 `70_evidence/ROOT-PATH-ISSUE.md` 终局节 |
| 正文内联 link 节点平铺渲染无 `<a>` | 文章 CTA 用**页面级块**（material-story-split actionTarget）做真链接 | MODULES.md link 行 |
| 空字符串字段会被 zod 打回默认值（如 WhatsApp url 默认 `wa.me/+44-7911-123456`） | 删 demo 按钮=**移除元素**（children+elements 同删），不是置空 | 2026-08-30 实测（ISS-068） |
| 文章发布=create 空壳草稿 → publish_post upsert；同 slug 重跑会堆积 Untitled 草稿 | 先 read_lists 查 slug 再 publish（勿重复 create） | ISS-059 |
| **createTheme(default) 会重新种入 3 demo 产品+3 demo 文章+6 demo 分类+7 demo 标签**（站点级，新记录 id 时间戳=创建时刻；taxonomy 同样种入且 0 引用也会公开出现在筛选下拉） | 每次重建主题后重跑全链清理（delete-demo-content.py）；audit count 项自动暴露 | ISS-071/074 |
| 正文原生 Slate 类型 = `p|h2|h3|blockquote`（服务器存储形态；'heading'/'paragraph' 旧词法禁用） | 格式见 templates/post-payload-example.json；生成器 writing-module.py block/skeleton | ISS-060 |
| 主题 id/页面 id 会变 | 一律 read_themes/read_pages/read_page_document 现取，勿猜 | allincms_api.read_themes |

## §3 主题页操作（第 8 步展开）

```python
import sys; sys.path.insert(0, '<interface-kit 绝对路径>')
from allincms_api import AllinCMS
import os; api = AllinCMS(token=os.environ["WS_TOKEN"])  # export WS_TOKEN=<token>（或 token 文件路径）
# 建 default 主题（preset='default' 总是生成 7 页：/home /about-us /contact-us /posts /posts/{post} /products /products/{product}）
api.create_theme(slug, site_id, 'My Default', 'Default theme', preset='default')
# theme_id 来源：create_theme 后按 name 取最新（或取 active 主题）
themes = api.read_themes(slug)['themes']
theme_id = [t['id'] for t in themes if t['name'] == 'My Default'][-1]
# 读页面与文档（read_page_document 返回 {status, initialPayload:{page:{document,globals,themeConfig}}）
r = api.read_pages(slug, theme_id)          # {'pages':[...], 'routes':[...]}
page_id = r['pages'][0]['id']               # 示例取第一页；按需换 path=='/home' 等
c = api.read_page_document(slug, theme_id, page_id)
page = c['initialPayload']['page']
doc, globals_doc, tc = page['document'], page['globals'], page['themeConfig']
# 改 doc/globals 后用 save_home 逐页 save+publish；intent 两种都要发
api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='save')
api.save_home(slug, theme_id, page_id, site_id, doc, globals_doc, tc, intent='publish')
# 绑路由 → 激活 → 设首页（set_home_page 必须最后：setThemeActive 是唯一会清空 homePageId 的操作——
# routes/activate 次序互换无害（实测路由不破坏绑定）；任何未来重新激活主题后都要重跑 set_home_page）
api.apply_theme_routes(slug, site_id, theme_id, [{'routePath': p['path'], 'pageId': p['id']} for p in r['pages']])
api.set_theme_active(slug, site_id, theme_id)
home_page_id = [p['id'] for p in r['pages'] if p['path'] == '/home'][0]
api.set_home_page(slug, site_id, theme_id, home_page_id)   # 根路径 / 开始渲染首页（对抗矩阵见 ISS-070 审查记录）
```

- 页面文档结构：`{"root":"page-root","elements":{...}}`；块类型白名单与 props 见 `templates/home-page-example.json`、allincms_blocks.py 与 MODULES.md（37 块注册表全集在 MODULES.md 开头）。
- globals（header/footer/contact dialog/social button）**按页存储**：改 globals 后用同一份 globals_doc 对**全部 7 页**逐页 save+publish（Example 实测可靠做法；只 commit 一页不可保证全站一致）。
- **文章页 CTA 真链接**（已实测）：post-detail 页 `page-root.children` 追加 `cta-1` 元素（type `material-story-split`，actionTarget `{"type":"custom","href":"/contact-us?source=<site>-article"}`），同时把 related-1 的 demo 文案（"More from the journal"）换掉。参考脚本：`<task_dir>/70_evidence/scripts-*/fix-post-cta.py`（参照你任务的同类脚本）。

## §4 产品（第 6 步展开）

- payload 见 `templates/product-payload-example.json`：media 扁平 `{name,alt,type:'image',source:'oss',path:'<siteKey>/<file>.webp',size,mimeType}`；categories/tags 传 id 字符串数组；specifications `[{key,value}]`。
- 流程：`create_product`（返回空壳 id）→ `publish_product`（同 payload 带 slug 再发，一次成功）。
- 数量/字段以 COP 为准；完成后 `read_lists(slug,'products')` 与 COP 逐条 diff。

## §5 分类/标签（第 5 步展开）

- `create_category2(slug, site_id, name, slug, content_type='products'|'posts', description='', order=0, cover=None)` —— cover 显式传 None，否则 500。
- `create_tag(slug, site_id, name, slug, description='')`。
- 坑：直接 POST create 时若报 transaction number mismatch → 先在浏览器打开对应 tab 拿新 router tree（ISS 记录）。

## §6 媒体（第 4 步展开）

- `upload_media(slug, site_id, file_path, title, alt, caption)`：multipart `_1_files` 传输（interface-kit 已封装），返回后立即 `update_media` 回写 title/alt/caption。
- 上传完 `read_media_library` 核对 10 字段（name/alt/url/path/size/mimeType）。

## §7 文章写作（第 7 步：子 agent k3 写）

```text
1) 主 AI 从源 PDF 提炼 facts（只允许用源内事实：频率/结构/参数/保固；禁止编价格/MOQ/认证/客户案例）
2) 派【写作子 agent，模型=k3】：给 BRIEF.md（facts+主题+Slate 格式规范）+ templates/article-writing-logic.md
   产出 <slug>.json：字段全集见 templates/post-payload-example.json（title/slug/excerpt/order/coverImage/content/categories/tags）
   content 原生 Slate 类型 = p|h2|h3|blockquote（服务器存的就是这些；'heading'/'paragraph' 是旧词法已禁用，用 writing-module.py 生成器保证）
3) 机器检查：python3 writing/writing-module.py check <slug>.json
4) 派【评审子 agent，模型=GLM flash（flash）】：复制 templates/ghostwriter-review-prompt.md 填文派空白子 agent
   -> 5 维评分+最弱3处+钩子检查+READY/NEEDS_REWRITE
5) NEEDS_REWRITE -> 回改表达（不动事实）重审；READY -> 下一步
6) create_post -> publish_post（先 read_lists 查 slug 防重）-> 上线后抓取验证 SSR
```

模型命名以宿主实际可用模型 id 为准：写作=K3 系（长文质量），评审=flash 系（快+挑剔）。

## §8 每站审计配置（第 9 步，必做）

```bash
cp templates/site-audit-config.template.json 70_evidence/<slug>-audit-config.json
# 按该站 COP 填：pages（含全部产品/文章 slug）、count（实建数）、faq_answers（文章必 SSR 的实质短语）、cta（真链接+source）
python3 site_pipeline.py audit <slug> --config <cfg> --out 70_evidence/audit-report.json
python3 site_pipeline.py gate <slug> --config <cfg>
python3 site_pipeline.py contact <slug> --config <cfg> --real "<真实电话|邮箱|地址>"
```

- 13 项机检：count/200/空态/模板词/demo 联系方式/FAQ SSR/真 CTA/单位/绝对化/Markdown/h2 语义/根路径首页(root-home)/表单渲染(form-render)。
- 平台 BLOCK（已永久移除，用户指令禁止涉及）；**根路径 / 是可修项**（set_home_page），audit root-home 项判 FAIL 说明首页没设好。
- **createTheme(default) 会重种 3+3 demo（ISS-071/074）**：审计前先跑 `python3 delete-demo-content.py <slug> [--dry-run]`（全链：产品+文章+分类+标签；带引用护栏）。
- **⚠️ 删除授权门（TERRA）**：一切删除类操作（delete_site/product/post/theme/category/tag/delete-demo-content.py 非 dry-run）**执行前必须取得用户/客户明确授权**；先 --dry-run 列清单确认，再授权执行。
- verdict FAIL 且问题非 BLOCK → 先修再交付；**没有 --config 的 audit 会用 Demo 基线误判新站（ISS-063）**。

## §9 已知平台 BLOCK 与回落（交付时照抄到"已知事项"）

| BLOCK | 现象 | 回落 |
|---|---|---|
| 根路径 `/` | 200 但错误壳（Allin CMS Runtime） | **可修**：`set_home_page`（先激活主题再设首页）；审计含 root-home 项防回归 |
| 正文内联链接 | `{"type":"link"}` 平铺无 `<a>` | 用页面级块 actionTarget（§3） |
| 页面 SEO description（meta） | 静态页可经 `api.update_page(..., description=...)` 改（配方=updatePage→等10s→commit publish 带 description→curl 验证）；**动态路由页**（/posts/{post}、/products/{product}）回退模板值=平台限制（ISS-073） | 静态页改、动态页记录；audit 已排除 meta 层判定 |
| 空字段 zod 默认回填 | 置空字符串会被 schema default 顶回 demo 值（如 WhatsApp wa.me/+44-7911-123456） | 删元素（children+elements 同删）而非置空（ISS-068） |
| 表单提交 | **链路已实测可用**（ISS-076/077）：公开站 submitRuntimeFormAction(siteId,{formSlug,values}) → success:true + fieldErrors 服务端校验；**所有表单块 formSlug 必须绑真实 slug**（空=整个 <form> 不渲染——含首页内联块 contact-1 与 7 页 globals 弹窗，逐页核）；工作台暂无提交收件箱 UI（平台待补） | **回落三层**：①联系页/首页展示真实邮箱（sales@…）直达 ②全局弹窗表单（Request a Quote 按钮）同 slug 可用 ③向平台确认提交数据导出/邮件通知；audit form-render 项防回归 |

## §10 交付与回填（第 10 步）

```bash
# 交付清单：templates/delivery-manifest.md -> 70_evidence/DELIVERY-<slug>-<date>.md
#   必须含：公开链接表（每行核验 200）+ 内容清单 + 核验记录（方法+结果）+ 已知事项（§9 照抄）
# HANDOFF.md：状态/事实矩阵/下一步
# 回填：新坑 -> issues.tsv 加行（fixed/boundary/pending）-> registry_tools.py verify
```

## §11 卡住时（顺序执行）

1. `python3 index/registry_tools.py find <关键词>`（历史坑有现象→根因→修复链）
2. `python3 site_pipeline.py audit <slug> --config <cfg>`（拿事实矩阵再判断）
3. **接口不工作/平台更新了？** → 读 [API-DISCOVERY.md](API-DISCOVERY.md)（7 步摸索流程：重扫→反编译→对比→发现→适配→验证）
4. 看 `templates/*.json` 实测 payload 样例 + `MODULES.md` 白名单
5. 新发现 → 修完立即回填 issues.tsv（否则下篇重蹈——这正是"为什么没按规则做"的根因：不 find 不回填）
