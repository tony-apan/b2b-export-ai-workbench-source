---
title: "域名绑定实战指南（Domain Setup）"
description: "规定给客户绑定自定义域名的完整流程与原理：CNAME 机制、Cloudflare 与阿里云分步实战、代理状态互斥陷阱（www 灰云 / 根域橙云）、根域在 CF 被强制展平的实测证据与 301 解法、接口自动化、巡检排查、域名数量上限与邮箱冲突等边界，以及给客户的话术。"
type: "doc"
status: "Working"
owner: "AI"
created: "2026-09-15"
last_updated: "2026-09-15"
sources: ["2026-09-15 17ark.com 生产域名真实配置实测（Cloudflare+EdgeOne，含橙云实验与还原）", "https://developers.cloudflare.com/dns/cname-flattening/set-up-cname-flattening/", "https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/", "laifaxin.com 阿里云解析实测对照"]
related: ["RUNBOOK-ANYONE.md", "NEW-SITE-ONEPASS.md", "templates/client-input-checklist.md", "../../ADAPTERS/cms/allincms/article-operations.md"]
visibility: "public"
redaction_status: "safe-to-publish"
doc_id: "DOC-DOMAIN-SETUP-001"
when_to_read: "给客户绑定自定义域名时；客户反馈域名打不开时；排查 DNS/证书问题时；需要判断 DNS 服务商差异时。"
keywords: ["域名", "domain", "CNAME", "DNS", "Cloudflare", "阿里云", "EdgeOne", "SSL", "301", "根域名", "apex", "代理状态"]
---

# 域名绑定实战指南

> 本文全部结论来自 **2026-09-15 在真实生产域名上的操作与实测**（含一次橙云实验并已还原），不是文档推测。
> **给客户看的话术照抄 [client-input-checklist.md](templates/client-input-checklist.md) 〇-c**；本文是技术侧完整参考。

## 一、原理（先理解这 4 件事）

```
客户浏览器 → DNS 解析 → 平台 CDN（腾讯 EdgeOne）→ 网站
              ↑                    ↑
        客户域名服务商        平台分配的目标域名
```

1. **客户要做两件事**：在域名服务商加 CNAME 记录 → 在平台上「添加域名」。
2. **平台要做两件事**：验证 CNAME 是否指向目标 → 通过后自动签发免费 SSL 证书。
3. **验证是看 CNAME 记录本身**（不是看解析结果）。这是后面所有坑的根源。
4. **CNAME 目标取哪个值**：用 `read_domains()` 返回的 `runtime_site_domain`（形如 `0gn3iso4o6.web.allincms.com`）——就是 UI 上显示给客户的那个。
   ⚠️ **不要**用接口里的 `cnameValue: "*.web.allincms.com"`（通配符，平台内部实现，给客户会配错）。

---

## 二、实战演示 A：Cloudflare（真实案例，含故障修复）

> 案例域名 `17ark.com`（生产域名，47 条 DNS 记录）。2026-09-15 实测。

### 2.1 初始状态：网站打不开

**症状**：`17ark.com` 和 `www.17ark.com` 都无法访问（HTTPS 报错）。
> 注：本章记录**修复过程**（历史状态）；当前终态见 §4.3-b。

**诊断过程**：

```bash
# ① 看平台侧状态
read_domains("0gn3iso4o6")
#  → 17ark.com:  cnameStatus=moved,  certificateStatus=failed
#                certificateError="自动验证无法通过，请检查域名 CNAME 配置"
#  → domains 列表里只有 17ark.com（没绑 www）

# ② 看 DNS 实际指向
dig +short CNAME www.17ark.com
#  → dwqfi7cupxmr.cloudfront.net   ← 指向 CloudFront（平台迁移前的旧地址！）

# ③ 验证旧地址是否还有效
dig +short dwqfi7cupxmr.cloudfront.net
#  → （空，该地址已失效）
```

**根因**：域名还指着平台**迁移前**的旧 CDN 地址（CloudFront），该地址已停用。

<!-- 要点：显示 17ark.com 与 www.17ark.com 两条 CNAME 都指向 dwqfi7cupxmr.cloudfront.net，代理状态列显示「仅 DNS」 -->

### 2.2 修复步骤

**Step 1 — 先在平台补绑缺失的 www**（API 操作，AI 可做）：

```python
api.add_domain(slug, site_id, "www.17ark.com", authorization_confirmed=True)
```

**Step 2 — 改 DNS 指向**（在 Cloudflare 控制台操作）：

| # | 类型 | 名称 | 内容 | 代理状态 |
|---|---|---|---|---|
| 1 | CNAME | `www` | `0gn3iso4o6.web.allincms.com` | 🌫️ **仅 DNS（灰云）** |
| 2 | CNAME | `@`（根域） | `0gn3iso4o6.web.allincms.com` | 🌫️ 仅 DNS（**根域需额外处理，见第四节**） |

<!-- 📸 截图位 2：Cloudflare「添加记录」表单 -->
<!-- 要点：类型=CNAME / 名称=www / 目标=<站点运行时域名> / 代理状态=仅 DNS -->

**Step 3 — 刷新平台状态**：

```python
api.refresh_domain(slug, site_id, "www.17ark.com")
```

### 2.3 结果

```
www.17ark.com  → cnameStatus=active  certificateStatus=active  HTTPS 200 ✅
17ark.com      → cnameStatus=moved   certificateStatus=failed  ❌（见第四节）
```

![平台域名列表：www 三项全绿](https://cos.files.maozhishi.com/data/web/web-files/img/domain-setup-04-platform-www-green.png)

> 平台「域名」页：仅 `www.17ark.com`，Alias / DNS / SSL 三项均为绿色，CNAME 目标显示为站点专属域名。
<!-- 📸 截图位 4：浏览器访问 https://www.17ark.com 正常显示网站 + 地址栏锁标志 -->

---

## 三、实战演示 B：阿里云

> 阿里云（含万网）**没有根域名展平问题**——根域 CNAME 会原样保留，`@` 和 `www` 都能通过平台验证。
> 实证对照（`laifaxin.com`，NS=`vip1.alidns.com`）：

```
根域 @ : CNAME → laifaxin.com.eo.dnse2.com.     ✅ 保留可见
www   : CNAME → www.laifaxin.com.eo.dnse2.com.  ✅
HTTPS : 根域 302 跳转 / www 200
```

### 操作步骤

```
1. 阿里云控制台 → 云解析 DNS → 找到域名 → 点「解析设置」
2. 点「添加记录」，逐条添加：

   记录 1（www）:
     记录类型 = CNAME
     主机记录 = www
     记录值   = <站点运行时域名>
     TTL      = 10 分钟（默认）

   记录 2（根域）:
     记录类型 = CNAME
     主机记录 = @
     记录值   = <站点运行时域名>

3. 保存 → 回平台点刷新
```

<!-- 📸 截图位 5：阿里云「解析设置」页面（两条 CNAME 记录明细） -->

### ⚠️ 阿里云根域 CNAME 的前置检查（重要）

**根域加 CNAME 会与邮箱记录冲突**（DNS 协议：同一主机名上 CNAME 不能与其他记录共存）。

加之前必须确认该域名**没有在使用根域邮箱**：

```bash
dig +short MX 17ark.com     # 有输出 = 根域邮箱在用
dig +short TXT 17ark.com    # 有 SPF/DKIM 也说明在用
```

- **没有邮箱** → 直接加根域 CNAME ✅
- **有邮箱** → 不要用 **CNAME** 方案动根域（CNAME 与 MX 冲突）；改用子域名收发，**或走第四节的 301 方案**（A 记录 + 橙云代理 **不影响 MX**——MX 记录不经 CF 代理）

---

## 四、🔴 核心坑：Cloudflare 根域名不可用（实测证据）

### 4.1 Cloudflare 会强制展平根域 CNAME

**官方文档原文**（`developers.cloudflare.com/dns/cname-flattening/set-up-cname-flattening/`）：

> "CNAME flattening occurs **by default for all plans** when your domain uses a CNAME record for its zone apex"
>
> "**Flatten will not be available**: The record is at the zone apex"

即：**根域名（@）的 CNAME 会被 Cloudflare 自动展平成 A 记录，且无法关闭**（Flatten 开关在 apex 记录上不可用）。

**实测证据**（`17ark.com`，同样配置，结果相反）：

| | `www.17ark.com` | `17ark.com`（根域） |
|---|---|---|
| CF 配置 | CNAME → 站点域名 | CNAME → 站点域名 |
| **权威 NS 查 CNAME** | `0gn3iso4o6.web.allincms.com.` ✅ | **空**（被展平） |
| **权威 NS 查 A** | — | `43.159.106.167`（EdgeOne IP，**301 方案实施前的中间态**） |
| 平台 `cnameStatus` | **active** ✅ | **moved** ❌ |
| 平台证书 | **active** ✅ | failed（"自动验证无法通过"） |
| HTTPS 访问 | **200** ✅ | **000**（无证书） |

**为什么平台验证失败**：平台要看到 CNAME 记录**本身**来判断指向；展平后只剩 A 记录，平台查不到 CNAME → 验证永不通过 → 证书签不出来。

> ⚠️ **一次观测，非稳定结论**：apex 仍绑在平台上时，用 `--resolve` 强制指向 EdgeOne IP 曾观测到 301/302；根域解绑后同一手法返回 **418**（与乱码域名相同）。故「EdgeOne 认这个 Host」**依赖平台侧绑定状态**，不构成可复现的机制结论——不要据此判断路由层无问题。

### 4.2 🔴 代理状态陷阱：两条记录要求**恰好相反**

这是最容易配错的一点，**实测确认**：

| 记录 | 代理状态 | 原因 |
|---|---|---|
| `www` | 🌫️ **仅 DNS（灰云）** | 平台必须看到 CNAME 记录本身才能验证 + 签证书；开橙云会让 CF 拦截，平台看不到原始 CNAME |
| 根域 `@` | ☁️ **代理（橙云）** | CF 官方：*"Single Redirects **require** that the incoming traffic ... is **proxied** by Cloudflare"*；灰云时 301 规则**完全不生效** |

**实验证据**（2026-09-15 实测，已还原）：

```
① 根域保持灰云（原状）：HTTPS → 000（EdgeOne 没有该域名证书）
② 根域开橙云（实验）  ：HTTPS → 000，响应头 server: cloudflare
                         + location: https://17ark.com/   ← EdgeOne 返回的 HTTP→HTTPS 跳转
                         CF 原样转发 → 浏览器再请求 https://17ark.com/ → 又回到 CF → 循环
```

**结论**：橙云**单独开不能解决问题**——必须配合重定向规则（让根域流量在 CF 边缘就 301 到 www，根本不下发到 EdgeOne）。

### 4.2-b 代理状态对照（真实截图）

| 根域：A 记录 + ☁️ **已代理（橙云）** | www：CNAME + 🌫️ **仅 DNS（灰云）** |
|---|---|
| ![根域 A 记录 192.0.2.1 已开橙云](https://cos.files.maozhishi.com/data/web/web-files/img/domain-setup-01-cf-apex-orange-cloud.png) | ![www CNAME 指向平台目标且为仅 DNS](https://cos.files.maozhishi.com/data/web/web-files/img/domain-setup-02-cf-www-cname-grey.png) |

> 这两张对照就是本节的核心：**同一个域名下，两条记录的代理状态必须相反**——根域橙云（301 规则生效前提），www 灰云（平台能验证 CNAME）。

### 4.3 根域正确配置（301 方案，推荐）

```
Step 1  根域记录：把云朵点亮成 ☁️ 橙色（代理）
        （更干净：类型改成 A 记录，内容填 192.0.2.1 —— RFC 5737 保留测试地址，
          永不真实访问；目的是避免 CF 回源到 EdgeOne）

Step 2  Rules → Redirect Rules → Create rule
        When：Hostname equals 17ark.com
        Then：Dynamic redirect → 301
              Expression: concat("https://www.17ark.com", http.request.uri.path)
        （免费版若用 Page Rules：Forwarding URL + 301 + https://www.17ark.com/$1 —— ⚠️ CF 已将 Page Rules 标为 **deprecated**，优先用 Single Redirects）

Step 3  验证：curl -sI http://17ark.com
        应返回 301 + Location: https://www.17ark.com/
```

![Cloudflare 重定向规则（301 至 www）](https://cos.files.maozhishi.com/data/web/web-files/img/domain-setup-03-cf-redirect-rule.png)

> 上图：Rules → 重定向规则，1 个活跃规则，匹配「主机名等于 17ark.com」，动作「301 重定向到 concat("https://www.17ark.com", http.request.uri.path)」——路径与参数会被完整保留。

**平台侧配套**（避免告警困惑）：
- 把 `www` 设为**主域名**：`api.set_primary_domain(slug, sid, "www.17ark.com", authorization_confirmed=True)`
  - ✅ **本案例已核查**：`read_domains()` 返回 `www.17ark.com` 的 `isPrimary=True`、`enabled=True`、`cnameStatus=active`、`certificateStatus=active`（2026-09-15 实测）
- 根域可从平台**解绑**（已由 CF 全权处理）——否则平台会一直显示根域验证失败

### 4.3-b 实测完成记录（2026-09-15，方案 A 全流程跑通）

**操作**（用带 `Single Redirect: 编辑` 权限的 API Token 直接完成）：

```
① 创建 Single Redirect 规则（apex → www，301）
   PUT /zones/{zone_id}/rulesets/phases/http_request_dynamic_redirect/entrypoint
   {
     "rules": [{
       "action": "redirect",
       "action_parameters": {"from_value": {
         "status_code": 301,
         "target_url": {"expression": "concat(\"https://www.17ark.com\", http.request.uri.path)"},
         "preserve_query_string": true}},
       "expression": "(http.host eq \"17ark.com\")",
       "description": "Apex to www (301)"
     }]
   }

② 根域记录改 A 192.0.2.1 + 橙云（proxied=true）
   PATCH /zones/{zone_id}/dns_records/{record_id}

③ 平台侧配套
   set_primary_domain(slug, sid, "www.17ark.com", authorization_confirmed=True)
   delete_domain(slug, sid, "17ark.com", authorization_confirmed=True, confirm_token="17ark.com")
```

**验证结果**（全部实测）：

| 测试 | 结果 |
|---|---|
| `curl -L http://17ark.com` | 最终 **200**，跳转 1 次，落点 `https://www.17ark.com/` ✅ |
| `curl -I https://17ark.com` | **301** + `location: https://www.17ark.com/` + `server: cloudflare` ✅ |
| 带路径参数 `http://17ark.com/about?x=1` | → `https://www.17ark.com/about?x=1`（路径与参数完整保留）✅ |
| `https://www.17ark.com` | **200**，证书有效，页面正常 ✅ |
| 平台域名列表 | 只剩 `www.17ark.com`：`primary=true` `cname=active` `ssl=active` ✅ |
| `domain-check.py` | **0 须修 / 0 提醒**（全绿）✅ |

**最终架构**：

```
客户输入 17ark.com ──→ Cloudflare 边缘 301 ──→ https://www.17ark.com
                       （橙云 A 192.0.2.1）              │
                                                         ↓
                                              灰云 CNAME → EdgeOne（平台验证 + 证书）
```

**根域流量根本不到 EdgeOne**，所以平台不需要（也不应该）验证根域——这就是方案 A 能成立的根本原因。

**工具增强**：`domain-check.py` 已内置 Cloudflare 官方 IP 段识别——当根域指向 CF 代理 IP 时，判定为「301 方案预期终态」而非"指向错误"，并把相关告警降级为提示（避免误报）。

### 4.4 三种解法对比

| 方案 | 操作 | 优点 | 代价 |
|---|---|---|---|
| **A. www 为主 + 根域 301**（推荐） | 见 4.3 | 客户无感（输根域自动跳 www）；不动 DNS 服务商 | 需在 CF 手动配一次规则 |
| B. 只保证 www | 平台只绑 www | 最简单 | 客户输不带 www 的域名打不开 |
| C. DNS 迁到阿里云 | 改 NS | 根域 www 都能验证 | 需迁移全部记录（含邮箱！）风险高 |

---

## 五、用接口操作（AI 自动化）

```python
from allincms_api import AllinCMS
api = AllinCMS(email="...", password="...")   # 或 token="..."

# 读站点域名现状（含平台要求的 CNAME 目标、是否还能加域名）
info = api.read_domains("site_slug")
info["runtime_site_domain"]   # → 客户要填的 CNAME 目标（给客户的就是它）
info["can_add_domain"]        # → 是否还能加域名
info["domains"]               # → 已绑列表（含 cnameStatus / certificateStatus / isPrimary）

# 绑定（需用户明确授权）
api.add_domain(slug, site_id, "www.example.com", authorization_confirmed=True)

# 客户改完 DNS 后刷新平台状态
api.refresh_domain(slug, site_id, "www.example.com")

# 设为主域名 / 启停用 / 删除
api.set_primary_domain(slug, site_id, "www.example.com", authorization_confirmed=True)
api.set_domain_enabled(slug, site_id, "x.example.com", False, authorization_confirmed=True)
api.delete_domain(slug, site_id, "x.example.com",
                  authorization_confirmed=True, confirm_token="x.example.com")
```

**域名规范化**（`normalize_domain`，与平台 zod 规则逐字一致）：去空格 → 转小写 → 去 `https://` → 去路径。
**约束**：单站最多 **3 个**域名；`delete_domain` 需 `confirm_token` 逐字等于域名（防误删）。

> ### 🔐 AI 操作客户 DNS 的边界（硬规则，三处文档统一口径）
>
> **默认：AI 不接触客户的 DNS 后台**（不登录、不改记录），只给指引 + 用 `dig` 复验。
>
> **例外（用户显式提供 scoped API Token 时）**——必须同时满足：
> 1. **逐条展示 diff 并取得用户授权**后才执行（不得静默批量改）；
> 2. 权限**限定到该域名**（Zone Resources = Include → Specific zone）；
> 3. **只允许新增/修改本方案涉及的 A / CNAME 记录**；
> 4. **禁止触碰 MX / TXT（SPF/DMARC/DKIM）/ NS / CAA**——这些是邮件与委派记录，改错会直接中断服务；
> 5. 改完把变更记录写入任务证据（不写 token 本身）。
>
> **所需权限**（2026-09-15 实测）：
> | 用途 | 权限 |
> |---|---|
> | 改 DNS 记录 | `DNS: 编辑` |
> | 创建根域 301 | `单一重定向: 编辑`（`Single Redirect Edit`） |
> | 备用 | `页面规则: 编辑`（Page Rules 已被 CF 标为 deprecated，优先用 Single Redirects） |
> | 辅助读取 | `Config Rules: 编辑` + `Zone Custom Assets: 读取` |
>
> 未提供 token 时，把本节第 4.3 的步骤发给客户自行操作，AI 用 `dig` / `curl` 复验。

---

## 六、巡检与排查

```bash
# 巡检（不需要代理：dig 走 UDP 53）
WS_EMAIL=... WS_PASSWORD=... python3 domain-check.py <site_slug>

# 留档（产物直接落盘）
WS_EMAIL=... WS_PASSWORD=... python3 domain-check.py <site_slug> \
  --json --out 70_evidence/domain-report.json
```

巡检四项：① 已添加域名 ② `@` 与 `www` 是否都绑定 ③ NS 服务商（含根域展平风险预警） ④ CNAME 实际解析 == 平台要求目标。

**工具行为**：
- 用**权威 NS** 查询（`dig @<ns>`），避免本地递归缓存滞后误报（实测踩过）
- `dig` 超时/缺失会显式区分，不编造成"解析错误"
- 退出码：`0` 无问题 / `1` 有须修项 / `2` 环境或参数错误

### 常见问题速查

| 现象 | 原因 | 处理 |
|---|---|---|
| 域名打不开（超时） | CNAME 指向已失效的旧地址 | `dig CNAME <域名>` 看指向；改成 `runtime_site_domain` |
| 平台长期 `moved` | ① DNS 未生效 ② 根域被展平 | 权威 NS 复核；根域 → 走第四节方案 |
| SSL failed + "自动验证无法通过" | CNAME 未通过验证 | 先修 DNS，再 `refresh_domain` |
| 网站能开但样式错乱/字体异常 | 推断：加了代理层（CF 橙云）会改写/拦截资源（**本项目未实测到此因果**） | www 记录改回**仅 DNS** |
| 客户说"加了还是不行" | 本地缓存 / 加错主机名（@ vs www） | 用巡检工具（权威 NS 查询）核对 |
| 改了 DNS 但巡检说没配 | 本地 DNS 缓存滞后 | 已修复：工具改用权威 NS |

---

## 七、其他需要知道的（边界与限制）

| 项 | 说明 |
|---|---|
| **域名数量上限** | 单站最多 **3 个**（平台常量 `MAX_SITE_DOMAINS`）。够用：`@` + `www` + 1 个子域 |
| **主域名含义** | `isPrimary` 决定 **sitemap 落点与默认跳转**（实测 sitemap 用主域名）；⚠️ 未观测到 `<link rel="canonical">`（全站 0 命中），**不要对客户宣称 canonical 已生效**。换主域名属业务决策，需用户确认 |
| **证书签发** | 平台在 **CNAME 验证通过后自动签发**，AI **没有**申请接口；未签好前**不得**对客户宣称"证书已生效" |
| **证书续期** | 平台自动处理，无需客户操作 |
| **邮箱冲突** | 根域加 CNAME 会与 MX/SPF 冲突（见 3.1 前置检查）——有邮箱的域名不要动根域 |
| **换域名** | 原语齐备（`add` 新 + `set_primary` + `delete` 旧），但**没有现成 SOP**：需考虑旧域名 301 保留 SEO、canonical 更新、证书重签顺序 |
| **子域名需求** | 如 `blog.example.com`：直接加为独立域名（占 1 个名额）；CF 展平问题适用于任何 apex |
| **域名过期** | 工具暂不检查到期时间；建议交付时提醒客户留意续费 |
| **⚠️ 301 规则的失效模式** | 规则被误删/配额超限时，根域会回源到占位地址 `192.0.2.1`（不可达）→ **522**。巡检已内置实测断言（`domain-check.py` 会 curl apex 验证 301 落点）；发现失败即报 error |
| **DNS 传播时间** | 通常 1–10 分钟；工具用权威 NS 可立即看到真实值（绕过本地缓存） |
| **国内访问** | 做外贸无需备案；`1.1.1.1`/DoH 在国内不可达但 `dig` 正常；操作 CF 后台建议开代理 |

---

## 八、给客户的沟通要点

- **时机**：网站做好、客户满意**之后**再谈域名（先交付价值，别在开工时就谈配置）
- **话术**：照抄 [client-input-checklist.md](templates/client-input-checklist.md) 〇-c——购买引导 / 绑定确认 / 按 NS 商给 DNS 步骤 / 三档证书状态反馈
- **安全边界**：默认 AI **不接触客户 DNS 后台**；只有用户显式提供 scoped token 时才可代改（且严格按 §5 的硬规则：逐条 diff 授权、限 A/CNAME、禁碰 MX/TXT/NS）。无论如何，AI 都要用 `dig` / `curl` **独立复验**结果（比让客户截图更可靠）
- **诚实红线**：证书没签好就说"平台在等 DNS 校验通过"，**不得**说"已生效"
- **不替客户决策**：选哪个注册商、要不要迁 DNS、换不换域名 —— 都给建议 + 让客户拍板

---

## 附：截图清单（待补充）

本文截图位需外部图床托管（仓库 MANIFEST **排除所有图片格式**，截图不能进 Git）。

| # | 截图内容 | 状态 | 位置 |
|---|---|---|---|
| 1 | CF 根域 A 记录 + 橙云 | ✅ 已嵌入 | §4.2-b |
| 2 | CF www CNAME + 灰云 | ✅ 已嵌入 | §4.2-b |
| 3 | CF Redirect Rules 配置界面 | ✅ 已嵌入 | §4.3 |
| 4 | 平台域名列表（www 三项全绿） | ✅ 已嵌入 | §2.3 |
| 5 | CF「添加记录」表单 | ⏳ 待补充 | §2.2 Step 2 |
| 6 | 浏览器访问 www 成功 + 锁标志 | ⏳ 待补充 | §2.3 |
| 7 | 阿里云解析设置 | ⏳ 待补充 | §3 |

**上传约定**：截图 → 外部图床（如 `cos.files.maozhishi.com`）→ 把 URL 填进对应截图位的图片行。
**去敏要求**：公开文档中的截图需遮蔽账号名等敏感信息（或确认域名本身可公开）。
