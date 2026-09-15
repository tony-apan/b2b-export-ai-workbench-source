---
title: "域名绑定配置指南（Domain Setup）"
description: "定义给客户绑定自定义域名的完整流程与原理：CNAME 配置、Cloudflare 根域强制展平不可用（实测证据+三种解法）、阿里云/其他服务商步骤、接口调用、巡检、状态值对照与常见问题。"
type: "doc"
status: "Working"
owner: "AI"
created: "2026-09-15"
last_updated: "2026-09-15"
sources: ["2026-09-15 xmc1204 账号 17ark.com 真实配置实测（Cloudflare）", "https://developers.cloudflare.com/dns/cname-flattening/", "platform /{slug}/domains page RSC"]
related: ["RUNBOOK-ANYONE.md", "NEW-SITE-ONEPASS.md", "templates/client-input-checklist.md", "../../ADAPTERS/cms/allincms/article-operations.md"]
visibility: "public"
redaction_status: "safe-to-publish"
doc_id: "DOC-DOMAIN-SETUP-001"
when_to_read: "给客户绑定自定义域名时；客户反馈域名打不开时；排查 DNS/证书问题时。"
keywords: ["域名", "domain", "CNAME", "DNS", "Cloudflare", "阿里云", "EdgeOne", "SSL", "301", "根域名"]
---

# 域名绑定配置指南

> 本文来自 2026-09-15 在真实生产域名（Cloudflare + EdgeOne）上的完整实测，含失败案例与根因。
> **AI 给客户的话术照抄 [client-input-checklist.md](templates/client-input-checklist.md) 〇-c**；本文是技术侧完整参考。

## 一、整体原理（先理解这三件事）

```
客户浏览器 → DNS 解析 → 平台 CDN（EdgeOne）→ 网站
              ↑              ↑
         客户域名服务商    平台分配的目标域名
```

平台要客户做两件事：
1. **加 CNAME 记录**：`<客户域名>` → `<站点运行时域名>`（形如 `xxxx.web.allincms.com`）
2. **在平台上添加域名**：平台校验 CNAME 通过后自动签发免费 SSL 证书

**平台的 CNAME 目标取哪个值**：用 `read_domains()` 返回的 `runtime_site_domain`（如 `0gn3iso4o6.web.allincms.com`）——这是 UI 上显示给客户的那个。**不要**用接口里的 `cnameValue: "*.web.allincms.com"`（通配符，是平台内部实现，给客户会配错）。

## 二、🔴 最重要的坑：根域名（@）在 Cloudflare 上不可用

### 现象

在 Cloudflare 给根域名（`example.com`）加 CNAME 后：
- 平台显示 `cnameStatus: moved`，SSL 报 **「自动验证无法通过，请检查域名 CNAME 配置」**
- `dig CNAME example.com` **查不到任何 CNAME**，只有 A 记录
- 而 `www.example.com` 同样配置却显示 `active`，证书正常

### 根因（Cloudflare 官方文档原文）

> "CNAME flattening occurs **by default for all plans** when your domain uses a CNAME record for its zone apex"
>
> "**Flatten will not be available**: The record is at the [zone apex]"

即：**Cloudflare 对根域名的 CNAME 强制展平成 A 记录，且无法关闭**（Flatten 开关在 apex 记录上不可用）。平台校验时需要看到 CNAME 记录本身，展平后查不到 → 验证必然失败。

实测证据（2026-09-15，17ark.com）：
```
CF 配置: 17ark.com CNAME → 0gn3iso4o6.web.allincms.com (DNS only)
dig 权威NS: CNAME 无 | A 43.159.106.167   ← 被展平
平台状态:   cnameStatus=moved, certificateError=自动验证无法通过

CF 配置: www.17ark.com CNAME → 0gn3iso4o6.web.allincms.com (DNS only)
dig 权威NS: CNAME 0gn3iso4o6.web.allincms.com.  ← 完整可见
平台状态:   cnameStatus=active, certificateStatus=active ✓
```

### 三种解法

| 方案 | 操作 | 适用 |
|---|---|---|
| **A. www 为主 + 根域 301**（推荐） | ① 平台只绑 `www`，设为主域名；② 根域在 CF 上「橙云 A 记录占位 + 301 重定向到 www」 | 有 CF 规则权限 |
| **B. 只保证 www** | 平台只绑 www；根域不管 | 客户只从 www 进（多数场景够用） |
| **C. DNS 迁阿里云** | NS 改到阿里云，根域 CNAME 可保留原记录，@ 与 www 都能验证 | 愿意改 NS |

> ### ⚠️ 方案 A 的关键：两条记录的代理状态**要求相反**（实测踩过）
>
> | 记录 | 代理状态 | 为什么 |
> |---|---|---|
> | `www` | **灰云（DNS only）** | 平台要看到 CNAME 记录本身才能验证并签发证书 |
> | 根域 `@` | **橙云（Proxied）** | CF 官方：*"Single Redirects **require** that the incoming traffic ... is **proxied** by Cloudflare"*；灰云时 301 规则**完全不生效** |
>
> 给根域开橙云后：CF 用自己的证书提供 HTTPS（**不需要**平台给根域签证书），Redirect Rule 直接在边缘返回 301 到 www——根域流量根本到不了 EdgeOne，所以平台验不验根域**都无所谓**。
>
> **配置步骤**（CF 控制台，免费版可用 Page Rules）：
> 1. DNS → 根域那条记录 → 点云朵图标变成**橙色**（Proxied）
> 2. （可选但更干净）把根域记录改成 **A 记录**指向 `192.0.2.1`（RFC 5737 保留测试地址，永不真实访问）+ 橙云——避免 CF 回源到 EdgeOne
> 3. Rules → Redirect Rules → Create rule：
>    - When incoming requests match：`Hostname equals 17ark.com`
>    - Then：**Dynamic redirect** → Expression: `concat("https://www.17ark.com", http.request.uri.path)`，Status: **301**
>    - （或用 Page Rules 的 Forwarding URL：`https://www.17ark.com/$1`，301）
> 4. 验证：`curl -sI http://17ark.com` 应返回 `301` + `location: https://www.17ark.com/`
>
> **平台侧配套**：把 `www` 设为**主域名**（`set_primary_domain`），根域可从平台解绑（它已由 CF 全权处理）——否则平台会一直显示根域验证失败的告警，让客户困惑。

### 对比：阿里云根域 CNAME 可正常保留

实测样本（laifaxin.com，NS=阿里云）：
```
根域 @ : CNAME → laifaxin.com.eo.dnse2.com.   ← 保留，未被展平
www   : CNAME → www.laifaxin.com.eo.dnse2.com.
```
所以**阿里云用户没有这个问题**，@ 和 www 都能验证。

## 三、按 DNS 服务商的操作步骤

### 3.1 Cloudflare 用户

```
1. dash.cloudflare.com 登录 → 选择域名
2. 左侧 DNS → Records → Add record
3. 填写：
   Type          = CNAME
   Name          = www（⚠️ 根域不要填这里，见第二节）
   Target        = <runtime_site_domain>
   Proxy status  = DNS only（灰云，重要！仅限 www——根域见方案 A 的相反要求）
   TTL           = Auto
4. Save
5. 若需要根域：用 Redirect Rule 做 301 到 www（见方案 A）
```

### 3.2 阿里云用户

```
1. 阿里云控制台 → 云解析 DNS → 找到域名 → 解析设置
2. 添加两条记录：
   ┌ 记录类型 CNAME | 主机记录 www | 记录值 <runtime_site_domain>
   └ 记录类型 CNAME | 主机记录 @   | 记录值 <runtime_site_domain>
3. 保存（TTL 默认 10 分钟）
```

⚠️ 根域加 CNAME 前，确认**该域名没有在用根域邮箱**（MX/SPF 记录）——加 CNAME 与 MX 冲突（DNS 协议限制：CNAME 不能与其他记录共存于同一主机名）。有邮箱需求时改用 301 方案或子域名收发。

### 3.3 其他服务商（DNSPod / Google / AWS 等）

识别方法：`dig +short NS <域名>`。操作逻辑同上（加 CNAME 记录），根域是否可加取决于该服务商是否展平。**不确定时优先只配 www。**

## 四、用接口操作（AI 自动化）

```python
from allincms_api import AllinCMS
api = AllinCMS(email="...", password="...")   # 或 token="..."

# 1. 读站点域名现状（含平台要求的 CNAME 目标）
info = api.read_domains("site_slug")
print(info["runtime_site_domain"])   # → 客户要填的 CNAME 目标
print(info["domains"])               # → 已绑域名列表（含 cnameStatus/certificateStatus）

# 2. 绑定域名（需用户明确授权）
api.add_domain("site_slug", site_id, "www.example.com", authorization_confirmed=True)

# 3. 客户改完 DNS 后刷新平台状态
api.refresh_domain("site_slug", site_id, "www.example.com")

# 4. 设为主域名 / 启停用 / 删除（均需授权，删除另需 confirm_token）
api.set_primary_domain("site_slug", site_id, "www.example.com", authorization_confirmed=True)
api.set_domain_enabled("site_slug", site_id, "x.example.com", False, authorization_confirmed=True)
api.delete_domain("site_slug", site_id, "x.example.com",
                  authorization_confirmed=True, confirm_token="x.example.com")
```

**域名规范化**（`normalize_domain`，与平台 zod 规则一致）：去空格 → 转小写 → 去 `https://` → 去路径。
**限制**：单站最多绑定 **3 个**域名（平台前端常量 `MAX_SITE_DOMAINS`）。

## 五、巡检（排查域名打不开）

```bash
WS_EMAIL=... WS_PASSWORD=... python3 domain-check.py <site_slug>
WS_EMAIL=... WS_PASSWORD=... python3 domain-check.py <site_slug> --json --out 70_evidence/domain-report.json
```

巡检四项：① 已添加域名 ② @ 与 www 是否都绑定 ③ NS 服务商 ④ CNAME 实际解析 == 平台要求目标。

**工具行为说明**：
- 用**权威 NS** 查询（`dig @<ns>`），避免本地 DNS 缓存滞后导致误报"没配置"
- `dig` 超时/缺失会显式区分，不会编造成"解析错误"
- 退出码：`0` 无问题 / `1` 有须修项 / `2` 环境或参数错误

## 六、状态值对照表（平台接口字段）

| 字段 | 取值 | 含义 |
|---|---|---|
| `cnameStatus` | `active` | ✅ 解析已验证 |
| | `moved` | ⏳ 等待生效（平台同步中，稍后 refresh） |
| | `invalid` | ❌ 无效（指向不对，需改 DNS） |
| `certificateStatus` | `active` | ✅ 证书正常 |
| | `requested` | ⏳ 申请中 |
| | `none` | ⚪ 未申请 |
| | `failed` | ❌ 失败（多为 CNAME 未通过验证） |
| | `expired` | ❌ 已过期 |

> 证书由**平台在 CNAME 验证通过后自动签发**，AI 没有直接申请接口——不要引导用户找不存在的"申请"按钮。

## 七、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 域名打不开（超时） | CNAME 指向的旧地址已失效 | `dig CNAME <域名>` 看指向；改成 `runtime_site_domain` |
| 平台显示 moved 很久不变 | ① DNS 还没生效 ② 根域被展平 | 权威 NS 复核；若是根域 → 走第二节方案 |
| SSL failed + "自动验证无法通过" | CNAME 未通过验证 | 先修 DNS，再 refresh |
| 客户说"解析加了还是不行" | 本地缓存 / 加错主机名 | 巡检工具查（用权威 NS）；核对是 `www` 还是 `@` |
| 网站能开但样式错乱 | 加了代理层（CF 橙云） | CNAME 设为 DNS only（灰云） |

## 八、给客户的沟通要点

- **时机**：网站做好、客户满意**之后**再谈域名（先交付价值）
- **话术**：照抄 [client-input-checklist.md](templates/client-input-checklist.md) 〇-c（购买引导 / 绑定确认 / 按 NS 商指引 / 三档证书状态）
- **安全**：AI **不登录客户的 DNS 后台**，只给指引 + 用 dig 复验结果（比让客户截图更可靠）
- **诚实**：证书未签发时说明「平台在等 DNS 校验通过」，**不得**宣称已生效
