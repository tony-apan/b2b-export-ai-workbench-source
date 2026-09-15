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

> 案例域名 `17ark.com`（生产域名，47 条 DNS 记录，含邮箱 MX/SPF/DKIM）。2026-09-15 实测。

### 2.1 初始状态：网站打不开

**症状**：`17ark.com` 和 `www.17ark.com` 都无法访问（HTTPS 报错）。

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

<!-- 📸 截图位 1：Cloudflare DNS 记录列表（修复前） -->
<!-- 要点：显示 17ark.com 与 www.17ark.com 两条 CNAME 都指向 dwqfi7cupxmr.cloudfront.net，代理状态列显示「仅 DNS」 -->
<!-- 补充后替换本行为：![修复前的 DNS 记录](https://<图床>/domain/cf-dns-before.png) -->

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

<!-- 📸 截图位 3：平台域名列表（修复后）—— www 的 DNS/别名/SSL 三项全绿 -->
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
- **有邮箱** → 不要动根域（会断邮件），改用子域名收发，或走第四节的 301 方案

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
| **权威 NS 查 A** | — | `43.159.106.167`（EdgeOne IP） |
| 平台 `cnameStatus` | **active** ✅ | **moved** ❌ |
| 平台证书 | **active** ✅ | failed（"自动验证无法通过"） |
| HTTPS 访问 | **200** ✅ | **000**（无证书） |

**为什么平台验证失败**：平台要看到 CNAME 记录**本身**来判断指向；展平后只剩 A 记录，平台查不到 CNAME → 验证永不通过 → 证书签不出来。

> 补充实测：EdgeOne **认这个 Host**（用 `--resolve` 强制指向 EdgeOne IP 时，`17ark.com` 返回 301/302，而乱码域名返回 418）——说明**路由层没问题，卡住的只是证书签发**。

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

<!-- 📸 截图位 6：Cloudflare 记录列表，重点圈出两条记录代理状态不同（www 灰云 / 根域橙云） -->

### 4.3 根域正确配置（301 方案，推荐）

```
Step 1  根域记录：把云朵点亮成 ☁️ 橙色（代理）
        （更干净：类型改成 A 记录，内容填 192.0.2.1 —— RFC 5737 保留测试地址，
          永不真实访问；目的是避免 CF 回源到 EdgeOne）

Step 2  Rules → Redirect Rules → Create rule
        When：Hostname equals 17ark.com
        Then：Dynamic redirect → 301
              Expression: concat("https://www.17ark.com", http.request.uri.path)
        （免费版也可用 Page Rules：Forwarding URL + 301 + https://www.17ark.com/$1）

Step 3  验证：curl -sI http://17ark.com
        应返回 301 + Location: https://www.17ark.com/
```

<!-- 📸 截图位 7：Cloudflare Redirect Rules 配置界面 -->

**平台侧配套**（避免告警困惑）：
- 把 `www` 设为**主域名**：`api.set_primary_domain(slug, sid, "www.17ark.com", authorization_confirmed=True)`
- 根域可从平台**解绑**（已由 CF 全权处理）——否则平台会一直显示根域验证失败

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

> 💡 如果用户提供 Cloudflare API Token，AI 可**直接操作 DNS**（不必让用户手动点）：
> 需要 `Zone → DNS → Edit` 权限（限定到具体域名）。**但 Redirect Rules / Page Rules 需要额外权限**
> （本次实测的 token 两者都返回未授权），所以 301 那步通常仍需用户手动配或补授权。

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
| 网站能开但样式错乱/字体异常 | 加了代理层（CF 橙云） | www 记录改回**仅 DNS** |
| 客户说"加了还是不行" | 本地缓存 / 加错主机名（@ vs www） | 用巡检工具（权威 NS 查询）核对 |
| 改了 DNS 但巡检说没配 | 本地 DNS 缓存滞后 | 已修复：工具改用权威 NS |

---

## 七、其他需要知道的（边界与限制）

| 项 | 说明 |
|---|---|
| **域名数量上限** | 单站最多 **3 个**（平台常量 `MAX_SITE_DOMAINS`）。够用：`@` + `www` + 1 个子域 |
| **主域名含义** | `isPrimary` 的那个决定 canonical 与默认跳转；换主域名属业务决策，需用户确认 |
| **证书签发** | 平台在 **CNAME 验证通过后自动签发**，AI **没有**申请接口；未签好前**不得**对客户宣称"证书已生效" |
| **证书续期** | 平台自动处理，无需客户操作 |
| **邮箱冲突** | 根域加 CNAME 会与 MX/SPF 冲突（见 3.1 前置检查）——有邮箱的域名不要动根域 |
| **换域名** | 原语齐备（`add` 新 + `set_primary` + `delete` 旧），但**没有现成 SOP**：需考虑旧域名 301 保留 SEO、canonical 更新、证书重签顺序 |
| **子域名需求** | 如 `blog.example.com`：直接加为独立域名（占 1 个名额）；CF 展平问题适用于任何 apex |
| **域名过期** | 工具暂不检查到期时间；建议交付时提醒客户留意续费 |
| **DNS 传播时间** | 通常 1–10 分钟；工具用权威 NS 可立即看到真实值（绕过本地缓存） |
| **国内访问** | 做外贸无需备案；`1.1.1.1`/DoH 在国内不可达但 `dig` 正常；操作 CF 后台建议开代理 |

---

## 八、给客户的沟通要点

- **时机**：网站做好、客户满意**之后**再谈域名（先交付价值，别在开工时就谈配置）
- **话术**：照抄 [client-input-checklist.md](templates/client-input-checklist.md) 〇-c——购买引导 / 绑定确认 / 按 NS 商给 DNS 步骤 / 三档证书状态反馈
- **安全边界**：AI **不登录客户的 DNS 后台**。只做两件事：① 给逐步指引（客户能照着点）② 用 `dig` 复验结果（比让客户截图更可靠、更快）
- **诚实红线**：证书没签好就说"平台在等 DNS 校验通过"，**不得**说"已生效"
- **不替客户决策**：选哪个注册商、要不要迁 DNS、换不换域名 —— 都给建议 + 让客户拍板

---

## 附：截图清单（待补充）

本文截图位需外部图床托管（仓库 MANIFEST **排除所有图片格式**，截图不能进 Git）。

| # | 截图内容 | 状态 |
|---|---|---|
| 1 | CF DNS 记录列表（修复前，指向旧地址） | ⏳ 待补充 |
| 2 | CF「添加记录」表单（CNAME / www / 仅 DNS） | ⏳ 待补充 |
| 3 | 平台域名列表（修复后，www 三项全绿） | ⏳ 待补充 |
| 4 | 浏览器访问 www 成功 + 锁标志 | ⏳ 待补充 |
| 5 | 阿里云解析设置（两条 CNAME） | ⏳ 待补充 |
| 6 | CF 记录列表（两条代理状态不同：www 灰云 / 根域橙云） | ⏳ 待补充 |
| 7 | CF Redirect Rules 配置界面 | ⏳ 待补充 |

**上传约定**：截图 → 外部图床（如 `cos.files.maozhishi.com`）→ 把 URL 填进对应截图位的图片行。
**去敏要求**：公开文档中的截图需遮蔽账号名等敏感信息（或确认域名本身可公开）。
