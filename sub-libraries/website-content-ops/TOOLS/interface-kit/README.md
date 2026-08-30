# AllinCMS 纯接口工具包（跨平台：macOS / Windows / Linux）

> **零上下文新人第一入口链：[NEW-SITE-ONEPASS.md](NEW-SITE-ONEPASS.md)（给一份客户资料→13 步一条龙建站）→ [RUNBOOK-ANYONE.md](RUNBOOK-ANYONE.md)（10 步总流程 + 实测事实表 + 平台回落表）**。本文档是 API/工具参考。

## 0. 先查索引（任何任务的第 0 步）
```bash
cd index && python3 registry_tools.py find <关键词>   # 找文档/脚本/模板/问题/模块，一次检索三张表
```
- `index/doc-registry.tsv`：全部文档/脚本/模板/证据 + 路径 + 状态 + 用途
- `index/issues.tsv`：已踩问题索引（现象/根因/修复/规避，行数以 `ls issues` 为准；fixed/boundary/pending）
- `index/modules.tsv`：单页模块 + 构建函数 + 前端显示（行数以 `ls modules` 为准）
- `INDEX.md`：由 `registry_tools.py gen` 自动生成的阅读页（勿手改）
- 维护：新增资产/问题/模块后 `verify` + `gen`（详见 index/INDEX.md 维护规则）

## 安装与依赖（新环境第 0 步）
1. 依赖全景：**runtime = 零第三方依赖（Python stdlib）**；docs-parse（解析用户 PDF/DOCX/PPTX/XLSX）= 选装 4 包；canonical 校验 = 选装 Node ≥18；截图 = 本机 Chrome
2. 安装：`python3 install-deps.py --yes && python3 install-deps.py --verify`（检测+安装+复检）
3. 自检：`python3 index/registry_tools.py verify` → PASS；`python3 allincms_api.py <token> read-sites` 冒烟
4. 详见 [SETUP.md](SETUP.md)（依赖表/各平台命令/常见问题/每次干活前顺序）

## 组成
- `allincms_api.py` —— 零依赖 Python 客户端（stdlib only：json/os/re/urllib）
- `scan/scan-actions.py` —— 通用 action 扫描器（发现新部署的 action id）
- `MODULES.md` —— 单页模块（Blocks Library）schema 与嵌套规范
- `API-DISCOVERY.md` —— **平台更新后 AI 摸索接口的标准流程**（重扫/反编译/对比/发现/适配/验证）
- `allincms_blocks.py` —— 单页模块构建器（hero/carousel/catalog/faq/contact…）
- 接口要点全集见 `70_evidence/THERMOS-INTERFACE-REPORT.md`

## 快速开始
```python
from allincms_api import AllinCMS
api = AllinCMS(token="<payload-token JWT>")   # 方式1：手动提供（浏览器登录后取 Cookie payload-token）
# 或 api.login(email, password)  # 方式2：账号密码（注意：login 不读 Set-Cookie，拿不到 token 属预期——推荐一律用浏览器 Cookie 的 payload-token）

# ---- 写（全部纯 HTTP server action）----
api.create_category2("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", "Insulated Bottles", "insulated-bottles", content_type="posts")
api.create_tag("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", "Vacuum Insulated", "vacuum-insulated")
api.upload_media("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", "photo.jpg", title="demo")
api.create_product("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", {...})
api.publish_product("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", "6a91e5e28333e0ece4a691b8", {...})
api.create_post("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", {...})
api.publish_post("<demo-site-key>", "6a91e2fa8333e0ece4a6852e", "6a91e66f8333e0ece4a69342", {...})
api.save_home("<demo-site-key>", "6a91e2fa8333e0ece4a68580", "6a91e2fa8333e0ece4a68762", "6a91e2fa8333e0ece4a6852e", doc, globals, cfg, intent="publish")

# ---- 读（RSC 流纯接口：GET path?_rsc + RSC:1 header，无需浏览器）----
api.read_sites()                        # 站点列表
api.read_lists("<demo-site-key>", "posts")   # 文章列表 + 分类/标签选项 + 分页
api.read_lists("<demo-site-key>", "products")# 产品列表 + 分类/标签选项 + 分页
api.read_pages("<demo-site-key>", "6a91e2fa8333e0ece4a68580")          # 主题页面列表 + routes
api.read_page_document("<demo-site-key>", "6a91e2fa8333e0ece4a68580", "6a91e2fa8333e0ece4a68762")  # 设计器 page{document+globals+themeConfig}
api.read_product("<demo-site-key>", "6a91e5e28333e0ece4a691b8")        # 产品编辑态 defaultValues
api.read_post("<demo-site-key>", "6a91e66f8333e0ece4a69342")           # 文章编辑态 defaultValues
api.read_media_library("<demo-site-key>")    # 媒体库
api.read_site_info("<demo-site-key>")        # 站点信息 + user
```

### CLI（换机/脚本直接跑，Windows 同命令）
```bash
python allincms_api.py <token> read-sites
python allincms_api.py <token> read-posts <site-slug>
python allincms_api.py <token> read-products <site-slug>
python allincms_api.py <token> read-pages <site-slug> <themeId>
python allincms_api.py <token> read-doc <site-slug> <themeId> <pageId>
python allincms_api.py <token> read-product <site-slug> <productId>
python allincms_api.py <token> read-post <site-slug> <postId>
python allincms_api.py <token> read-media <site-slug>
python allincms_api.py <token> read-info <site-slug>
```

## Runtime Forms（全站表单：contact 页 + CTA 弹窗共用）

- 表单定义在平台 DB（`initialForms.contact-inquiry`，含字段/schema/submit 文案），设计器 initialPayload 可读取
- **公开站无鉴权可调**（POST 到任意公开页，不带 Cookie）：
  - `loadRuntimeFormAction` `6015323de61487eb20de18018cbe5d428f4ea9aabe`，body `[siteId, formSlug]` → 返回完整 schema（字段 type/name/label/placeholder/required/minLength/maxLength/options + submit.successMessage）
  - `submitRuntimeFormAction` `6084316ab295c23ef1032c6f19ad614dda9377f878`，body `[{formSlug, values:{name,email,topic,message}}]`（与浏览器调用一致）
- ✅ **submit 实测通过**（2026-08-30，Example 站）：POST 公开页 `/contact-us` + body `[siteId, {formSlug:'contact-inquiry', values:{name,email,topic,message}}]` → `{success:true, successMessage:"Thanks..."}`；缺必填/坏邮箱 → `{success:false, fieldErrors:{...}}` 逐字段校验（ISS-076/077）。
  - 注意两点：①body 第一参数是 siteId（submitRuntimeFormAction 被 bind(null, siteId)）；②**必须 POST 公开站域**（POST 工作台域会 404 "Server action not found"）。
  - 上线必查：表单块 `formSlug` 绑真实 slug（空串=整个 <form> 不渲染，ISS-076）；工作台暂无提交收件箱 UI（平台待补）→ 联系页保留真实邮箱兜底。
- action id 扫描来源：公开页 chunk `createServerReference)("42hex",...,"NAME")`（与工作台同 dpl）。

## RSC 读的原理（为什么会成功）- Next.js App Router 对 `RSC: 1` 请求返回 `text/x-component` RSC 分段流；**不带 `Next-Router-State-Tree` 也能直接拿到首屏组件 props**（服务端 fallback tree）
- 请求 `GET {path}?_rsc`（无 `_rsc` 的服务端会 307 到 `?_rsc`；带 query 时用 `&_rsc`）
- 业务 JSON = 组件 props：`<key>:<json>` 行内直接是解码 JSON（如 `22:["$","$L2b",null,{"data":[...]}]`）；`o<len>,<id>:` 前缀行是引用段，可 json.loads 的行全被 `rsc_records()` 收集
- 只用三个 headers：`Cookie: payload-token=<JWT>`、`RSC: 1`、`Accept: text/x-component`（Origin/Referer 带上更保险，与写一致）

## RSC 端点矩阵（已验证 200）
| 数据 | 路径（拼接 `?_rsc`） | 提取键 |
|---|---|---|
| 站点列表 | `/sites` | `{data, pagination}` |
| 文章列表/分类/标签 | `/{slug}/posts` | `{data, categoryOptions, tagOptions, pagination}` |
| 产品列表/分类/标签 | `/{slug}/products` | 同上 |
| 主题页面+routes | `/{slug}/themes/{themeId}` | `{pages, routes}` |
| 设计器页面三件套 | `/{slug}/themes/{themeId}/{pageId}/design` | `initialPayload.page.{document,globals,themeConfig}` |
| 产品编辑态 | `/{slug}/products/{productId}/update` | `defaultValues` |
| 文章编辑态 | `/{slug}/posts/{postId}/update` | `defaultValues` |
| 媒体库 | `/{slug}/media` | `mediaLibraryItems` |
| 站点信息/user | `/{slug}/site-info` | `{site,user,sites}` |
| 工作台首页壳 | `/{slug}/dashboard` | site/user/sidebar 状态 |

## 换电脑怎么用（mac/win 通用）
1. **token 获取**（一次性或定期）：
   - 方式 A：浏览器登录 `workspace.laicms.com` → DevTools → Application → Cookies → `payload-token` 值
   - 方式 B：脚本 `AllinCMS(email, password)` —— 调 sign-in action（`7f04a5d5...`），payload 已验证；成功分支从 **Set-Cookie** 提取 `payload-token`（标准 Payload 行为；因无真实密码未实测，标注待验证）
2. **写操作**：全部纯 HTTP server action（本工具包），无需浏览器/AppleScript/Playwright
3. **读操作**：全部 RSC 纯接口（本工具包），无需浏览器/AppleScript/Playwright —— **读写闭环，全平台仅需 Python 3 + 网络**
4. 新机器只需：复制本目录 → 安装 Python 3 → 填入 token 即可跑通全链路

## action id 部署相关（重要）
- action id **随部署变化**（本包记录的是 dpl `83eddf…` 的值）。换环境/升级后用 `scan/scan-actions.py <token> <page-path>` 重扫
- 用错 action id → 静默返回 `{}`（不报错）——**必须核对响应**
- RSC 读不受部署影响（无 action id），仅受部署路径变化影响

## 已验证 / 待验证
- ✅ 已验证（curl/Python 纯接口实测）：建站/删站、建分类（posts+products）/标签、上传媒体/改元数据、建/删/发布产品、建/删/发布文章、首页设计器 save/publish；RSC 读：站点/文章/产品/分类选项/标签选项/页面列表/routes/设计器 document+globals+themeConfig/产品编辑态/文章编辑态/媒体库/站点信息
- ✅ 对抗验证：RSC 读回首页 document 与发布保底(flask-home-doc-new.json)及构建器重建(blocks-rebuilt-home.json) 模块类型集合、root children 序列完全一致；产品分类/文章分类读回与已知 id 一致（产品=产品，文章=文章）
- ⚠️ 待验证：登录成功分支（无真实密码——用户确认跳过）；文章中分类 `parentId` 语义（读回为 `$undefined`，写入无 parent 需求）
- 📌 观察项：产品分类下拉含测试残留 "Test Product Cat"（`6a91facb8333e0ece4a6c104`），若需清理需删除分类接口（未提供/未探索）
