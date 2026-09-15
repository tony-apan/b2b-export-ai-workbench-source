#!/usr/bin/env python3
"""域名巡检（domain-check.py，ISS-147）—— 平台侧 + DNS 侧双向对账。

用法：
    python3 domain-check.py <site_slug>                 # 巡检该站全部域名
    python3 domain-check.py <site_slug> --domain 17ark.com   # 只查某个域名
    python3 domain-check.py <site_slug> --json          # 机器可读输出

巡检 4 项（对应 SOP 的域名自检清单）：
    ① 有没有添加域名？          读平台 domains[]
    ② @ 和 www 都添加了吗？     数组 + DNS 双向核对
    ③ NS 是哪家 DNS 服务商？    本地 dig NS（无需代理）
    ④ CNAME 配对了吗？          平台 cnameValue ↔ 本地 dig 实际解析

关键发现（决定了本工具的判断逻辑）：
    - Cloudflare **根域 CNAME 强制展平且无法关闭**（官方文档明示），
      因此 CF 用户无法用根域 CNAME 通过 EdgeOne 验证 → 必须走「www 为主 + 301」。
    - 阿里云/DNSPod 等根域 CNAME 保留原记录 → 可直接验证通过。
    - 巡检不需要代理：dig 走 UDP 53，用国内 DNS 同样能查到 Cloudflare 记录。

退出码：0 全部正常；1 有需要处理的问题；2 参数/环境错误。
"""
import argparse
import datetime
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

NS_PROVIDERS = [
    (r"\.ns\.cloudflare\.com$", "Cloudflare", "warn-flatten"),
    # 阿里云实测（2026-09-15 goods-suppliers.com）：根域 CNAME 可加且与 MX 共存，平台验证通过
    (r"\.alidns\.com$", "阿里云解析", "ok"),
    (r"\.hichina\.com$", "阿里云解析（万网）", "ok"),
    (r"\.dnspod\.(net|com)$", "腾讯 DNSPod", "ok"),
    (r"\.dnsv\d*\.com$", "腾讯 DNSPod", "ok"),
    (r"\.googledomains\.com$", "Google Domains", "ok"),
    (r"\.awsdns-\d+\.(net|org|com|co\.uk)$", "AWS Route 53", "ok"),
    (r"\.nsone\.net$", "NS1", "ok"),
    (r"\.qeodns\.com$", "QEODNS（平台自有）", "ok"),
]

# 平台侧 cnameStatus 取值 → 中文含义（从平台源码提取）
# cnameStatus 取值（平台源码 getCnameStatusLabel：case active→"已验证", moved→"等待生效", invalid→"无效"）
CNAME_STATUS_CN = {
    "active": "已验证",
    "moved": "等待生效（平台同步中，稍后刷新）",
    "invalid": "无效（指向不对，需改 DNS）",
}
# edgeOneAliasStatus 取值（与 cnameStatus 是不同的枚举，勿混用）
ALIAS_STATUS_CN = {
    "active": "已生效", "pending": "等待生效", "conflict": "冲突",
    "requested": "申请中", "stop": "已停止", "failed": "失败",
}
CERT_STATUS_CN = {
    "active": "正常", "requested": "申请中", "failed": "失败",
    "none": "未申请", "expired": "已过期",
}


class DnsUnavailable(Exception):
    """本机没有 dig（Windows 常见）。"""


class DnsTimeout(Exception):
    """单次查询超时（网络抖动，不代表解析错误）。"""


class DnsQueryError(Exception):
    """dig 非零退出码（如非法域名/服务端拒绝）——与「查询成功但无记录」必须区分。"""


def run_dig(args, timeout=12):
    """执行 dig。返回结果列表；dig 缺失抛 DnsUnavailable，超时抛 DnsTimeout。
    （把超时/缺失与"查询到空结果"区分开——后者才是真的没配置解析。）"""
    try:
        r = subprocess.run(["dig", "+short"] + args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise DnsUnavailable("dig 不可用")
    except subprocess.TimeoutExpired:
        raise DnsTimeout(f"dig {' '.join(args)} 超时")
    if r.returncode != 0:
        # M8：非零退出码 ≠ 无记录（NXDOMAIN 的 dig 退出码是 0 + 空输出）。
        raise DnsQueryError((r.stderr or r.stdout or f"dig exit {r.returncode}").strip()[:160])
    return [x.strip().rstrip(".").lower() for x in (r.stdout or "").splitlines() if x.strip()]


def dig_ns(domain):
    out = run_dig(["NS", domain])
    if out is None:
        return None, "dig 不可用（Windows 请装 BIND tools 或用 nslookup 替代）"
    return out, ""


def identify_provider(ns_list):
    for ns in ns_list or []:
        low = ns.lower()
        for pattern, name, risk in NS_PROVIDERS:
            if re.search(pattern, low):
                return name, risk
    return ("未知服务商", "unknown")


# Cloudflare 代理 IP 段（官方 https://www.cloudflare.com/ips-v4，2026-09-15 抓取）
# 用途：apex 走「301 跳转到 www」方案时，根域会指向 CF 代理 IP —— 这是**合法终态**，不是"指向错误"。
CF_PROXY_CIDRS = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]


def _ip_to_int(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return None
    try:
        return sum(int(p) << (8 * (3 - i)) for i, p in enumerate(parts))
    except ValueError:
        return None


def is_cf_proxy_ip(ip):
    """判断 IP 是否属于 Cloudflare 代理段（apex 301 方案下的合法终态）。"""
    n = _ip_to_int((ip or "").strip())
    if n is None:
        return False
    for cidr in CF_PROXY_CIDRS:
        base, bits = cidr.split("/")
        b = _ip_to_int(base)
        if b is None:
            continue
        mask = (0xFFFFFFFF << (32 - int(bits))) & 0xFFFFFFFF
        if (n & mask) == (b & mask):
            return True
    return False


def probe_http(host, timeout=20, attempts=2):
    """线上可达性检测：公网访问该主机，跟随跳转后的最终状态码与落点。

    与 probe_tls 互补——TLS 只证明"握手/证书"，本函数证明"网站真的能打开"。
    内置重试（attempts）：单次网络抖动不应被报成错误——实测遇到过 5 次连测全过、
    但偶发 1 次失败的情况，故失败后重试一次。
    返回 {ok, status, final_url, redirects, error, attempts}
    """
    last = None
    for n in range(max(1, attempts)):
        last = _probe_http_once(host, timeout)
        last["attempts"] = n + 1
        # 只有真正成功才提前返回；失败（含 4xx/5xx/连接失败）一律重试——
        # 实测遇过偶发 000，也见过状态码瞬时异常，单次结果不足以判定。
        if last["ok"]:
            return last
        if n + 1 < max(1, attempts):
            time.sleep(2)
    return last


def _probe_http_once(host, timeout=20):
    out = {"ok": False, "status": None, "final_url": "", "redirects": None, "error": ""}
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-L", "--max-time", str(timeout),
             "-w", "%{http_code}|%{url_effective}|%{num_redirects}",
             f"https://{host}/"],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except FileNotFoundError:
        out["error"] = "curl 不可用"
        return out
    except subprocess.TimeoutExpired:
        out["error"] = "请求超时"
        return out
    parts = (r.stdout or "").strip().split("|")
    if len(parts) != 3:
        out["error"] = "响应异常"
        return out
    try:
        out["status"] = int(parts[0])
    except ValueError:
        out["error"] = f"状态码异常：{parts[0][:20]}"
        return out
    out["final_url"] = parts[1]
    try:
        out["redirects"] = int(parts[2])
    except ValueError:
        pass
    out["ok"] = out["status"] == 200
    if not out["ok"]:
        out["error"] = f"HTTP {out['status']}"
    return out


def _cert_days_left(not_after):
    """把证书 notAfter 字符串换算为剩余天数（容错，失败返回 None）。"""
    ts = None
    try:
        ts = ssl.cert_time_to_seconds(not_after)
    except Exception:
        try:
            ts = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=datetime.timezone.utc).timestamp()
        except Exception:
            return None
    return int((ts - time.time()) // 86400)


def _served_cert_names(host, port=443, timeout=8):
    """取服务端**实际提供**的证书里的域名字串（诊断用）。

    验证失败时（如 CDN/平台默认证书、域名不匹配）用它回答「对方到底给了我哪张证书」——
    实测价值很高：能直接看出是云商默认证书还是漏签发。
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                der = ss.getpeercert(binary_form=True)
    except Exception:
        return []
    names, seen = [], set()
    for raw in re.findall(rb"[ -~]{4,}", der or b""):
        text = raw.decode("ascii", "ignore").rstrip("0")
        if ("." in text and " " not in text and "/" not in text
                and 4 <= len(text) <= 80 and not text.startswith("http")):
            if text not in seen:
                seen.add(text)
                names.append(text)
    return names[:4]


def probe_tls(host, port=443, timeout=12, attempts=2):
    """本地 TLS/SSL 检测（stdlib socket+ssl，零依赖、跨平台）。

    返回值：
      handshake  是否完成 TLS 握手（False=443 无 TLS）
      verified   证书是否通过校验（CA 可信 + 域名匹配 + 未过期）
      reason     失败原因分类（中文，面向诊断）
      cn/sans/issuer/not_after/days_left/protocol  验证通过时的证书信息
      served     服务端实际提供的证书域名（失败时用于诊断）
    """
    out = {"host": host, "handshake": False, "verified": False, "reason": "",
           "cn": None, "sans": [], "issuer": None, "not_after": None,
           "days_left": None, "protocol": None, "served": []}
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                out["handshake"] = True
                out["verified"] = True
                out["protocol"] = ss.version()
                subj = dict(x[0] for x in cert.get("subject", []) if x)
                out["cn"] = subj.get("commonName")
                out["sans"] = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
                iss = dict(x[0] for x in cert.get("issuer", []) if x)
                out["issuer"] = iss.get("organizationName") or iss.get("commonName")
                out["not_after"] = cert.get("notAfter")
                if cert.get("notAfter"):
                    out["days_left"] = _cert_days_left(cert["notAfter"])
    except ssl.SSLCertVerificationError as e:
        out["handshake"] = True            # 握手已到证书校验阶段 → 证书存在但不合规
        msg = str(e)
        if "Hostname mismatch" in msg or "not valid for" in msg:
            out["reason"] = "证书域名不匹配（服务端证书不含该域名，多为未签发或指向了别处）"
        elif "expired" in msg:
            out["reason"] = "证书已过期"
        elif "self-signed" in msg or "self signed" in msg:
            out["reason"] = "自签名证书（浏览器会报警告）"
        elif "unable to get local issuer" in msg or "unable to get issuer" in msg:
            out["reason"] = "证书链不完整（缺中间证书）"
        else:
            out["reason"] = "证书校验失败：" + msg.split(":")[-1].strip()[:70]
    except ssl.SSLError as e:
        out["reason"] = "TLS 握手失败：" + str(e)[:70]
    except (socket.timeout, TimeoutError):
        out["reason"] = "连接超时（443 无响应）"
    except (ConnectionRefusedError, OSError) as e:
        out["reason"] = "连接失败：" + type(e).__name__
    if not out["verified"]:
        # 连接类失败重试一次（网络抖动不应被报成证书问题）
        if out["reason"].startswith(("连接超时", "连接失败")) and attempts > 1:
            time.sleep(1)
            return probe_tls(host, port, timeout, attempts - 1)
        out["served"] = _served_cert_names(host, port)
    return out


def norm_host(v):
    """主机名规范化：trim + lower + 去尾点（对齐平台 ed() 的比对口径）。"""
    return (v or "").strip().lower().rstrip(".")


def probe_apex_redirect(apex, expected_www, timeout=15):
    """B2：实测 apex 是否真的 301/308 跳到 expected_www。

    不能只看「apex 指向 CF 代理 IP」就认定 301 方案已生效——那只是必要条件。
    返回 (ok, detail)；ok=True 表示实测确认跳转存在且目标正确。
    """
    raw = None
    for attempt in range(2):                 # 网络抖动重试：apex 判定依赖它，必须稳
        try:
            raw = subprocess.run(
                ["curl", "-sI", "-o", "/dev/null", "-D", "-", "--max-time", str(timeout),
                 f"http://{apex}/"],
                capture_output=True, text=True, timeout=timeout + 5,
            )
            break
        except FileNotFoundError:
            return None, "curl 不可用，无法验证 301（跳过判定）"
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(2)
                continue
            return None, "curl 超时，无法验证 301（跳过判定）"
    r = raw
    headers = (r.stdout or "") + (r.stderr or "")
    status = None
    location = ""
    for line in headers.splitlines():
        low = line.strip().lower()
        if low.startswith("http/"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    status = int(parts[1])
                except ValueError:
                    pass
        elif low.startswith("location:"):
            location = line.split(":", 1)[1].strip()
    if status not in (301, 308):
        return False, f"实测 apex HTTP 返回 {status}，未跳转（期望 301/308）"
    if not location:
        return False, "返回 301 但缺少 Location 头"
    loc_host = ""
    m = re.match(r"^https?://([^/:]+)", location)
    if m:
        loc_host = norm_host(m.group(1))
    if loc_host != norm_host(expected_www):
        return False, f"跳转目标 {loc_host or location!r} 不是已绑定的 {expected_www}"
    return True, f"实测 {status} → {location}"


def authoritative_ns(base):
    """查注册域的权威 NS（用于避开本地递归缓存——改了 DNS 后本地缓存可能滞后数分钟）。"""
    try:
        return run_dig(["NS", base])
    except (DnsUnavailable, DnsTimeout):
        return []


def dns_state(domain, auth_ns=None):
    """查询主机名的 CNAME 与 A 记录。auth_ns 给定时直接问权威 NS（绕过本地缓存）。

    超时/不可用通过 error 字段区分，不编造"无记录"。
    """
    out = {"cname": [], "a": [], "resolved": False, "error": None, "via": "auth" if auth_ns else "local"}
    target = [f"@{auth_ns}"] if auth_ns else []
    try:
        out["cname"] = run_dig(["CNAME", domain] + target)
        out["a"] = run_dig(["A", domain] + target)
    except DnsUnavailable as e:
        out["error"] = f"dig-unavailable: {e}"
        return out
    except DnsTimeout as e:
        out["error"] = f"timeout: {e}"
        return out
    except DnsQueryError as e:
        out["error"] = f"query-error: {e}"
        return out
    out["resolved"] = bool(out["cname"] or out["a"])
    return out


def check_site(api, site_slug, only_domain=None, quiet=False):
    """巡检一个站点。quiet=True 时不打印人读文本（供 --json 使用）。"""
    result = {"site_slug": site_slug, "findings": [], "domains": [], "ok": True, "env_error": False}

    def emit(*a):
        if not quiet:
            print(*a)

    def add(level, text):
        result["findings"].append({"level": level, "text": text})
        if level == "error":
            result["ok"] = False

    info = api.read_domains(site_slug)
    runtime_domain = norm_host(info.get("runtime_site_domain") or "")
    cname_target = runtime_domain  # 平台要求的 CNAME 目标 = 站点运行时域名（UI 显示的就是它）
    all_domains = info.get("domains") or []
    result["runtime_site_domain"] = runtime_domain

    emit(f"站点：{site_slug}（运行时域名 {runtime_domain}）")
    emit(f"平台要求的 CNAME 目标：{cname_target}")
    emit()

    # ① 有没有添加域名
    if not all_domains:
        add("info", "平台侧还没有绑定自定义域名——建站后提醒客户配置（属合法中间态，非错误）")
        emit("① 已添加域名：⏳ 无（建站后待配置）")
        return result
    emit(f"① 已添加域名：✅ {len(all_domains)} 个")

    # BLOCKER-2：--domain 指定的域名必须真实存在于平台，否则报错而非静默 PASS
    if only_domain:
        only = api.normalize_domain(only_domain)
        filtered = [d for d in all_domains if norm_host(d.get("domain")) == only]
        if not filtered:
            got = [d.get("domain") for d in all_domains]
            add("error", f"--domain 指定的 {only} 不在该站已绑定域名中（当前：{got}）")
            emit(f"❌ {only} 未绑定到该站点（当前已绑：{got}）")
            return result
        domains = filtered
    else:
        domains = all_domains

    # MAJOR-3：dig 可用性全局探测（不可用则跳过 DNS 判定，不编造"未配置"）
    dig_ok = True
    try:
        run_dig(["NS", "example.com"], timeout=8)
    except DnsUnavailable:
        dig_ok = False
        result["env_error"] = True     # M7：环境缺失 → 退出 2，不与"有须修项"同码
        add("warn", "本机没有 dig，无法做 DNS 侧核验（Windows 请装 BIND tools 或改用 nslookup）；"
                    "本次只输出平台侧状态（属环境限制，非域名问题）")
    except DnsTimeout:
        pass  # 单次超时不代表不可用

    # B3：注册域切分需支持多段公共后缀（.co.uk/.com.cn/.com.au…）。
    # 精简 PSL：覆盖外贸常见地区后缀；未命中时回退"最后两段"。
    MULTI_SUFFIX = {
        "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk", "ac.uk", "gov.uk",
        "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
        "com.au", "net.au", "org.au", "edu.au", "gov.au",
        "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp",
        "co.nz", "net.nz", "org.nz",
        "com.br", "com.tw", "com.hk", "com.sg", "com.my", "com.mx",
        "com.ar", "com.tr", "com.vn", "com.ph", "com.pk", "com.sa",
        "co.za", "co.in", "co.kr", "co.id", "co.th", "co.il",
        "com.ua", "com.pl", "com.ru", "com.es", "com.it",
    }

    def registrable(host):
        parts = host.split(".")
        if len(parts) < 2:
            return host
        last2 = ".".join(parts[-2:])
        if last2 in MULTI_SUFFIX and len(parts) >= 3:
            return ".".join(parts[-3:])
        return last2

    # 分组：同注册域的 @ 与 www 成一组（both 都要检查）；
    # 其他子域（blog.x.com）单独成组，只检查它自己，不再合成 www.<子域>。
    groups = {}
    for d in domains:
        dom = norm_host(d.get("domain"))
        reg = registrable(dom)
        if dom == reg or dom == "www." + reg:
            groups.setdefault(reg, {})["@" if dom == reg else "www"] = d
        else:
            groups.setdefault(dom, {})["self"] = d

    for base, pair in groups.items():
        entry = {"domain": base, "hosts": {}, "provider": None, "issues": [], "issues_list": []}
        emit(f"—— 域名：{base} ——")

        is_subdomain_group = "self" in pair and "@" not in pair and "www" not in pair
        has_at, has_www = "@" in pair, "www" in pair
        if is_subdomain_group:
            emit(f"② 平台已绑定：{base}（子域名，按独立主机校验）")

        # 先探测 apex 是否走 CF 301 方案。
        # B2：仅"指向 CF 代理 IP"是必要条件，**必须再实测 301 跳转**才认定方案生效，
        # 否则任何 apex 挂在 CF 后面的站点都会被误判为"预期终态"，从而漏报真实故障。
        apex_cf_hint = False
        apex_via_cf = False
        apex_redirect_detail = ""
        # 注意：apex 已在平台解绑时（301 方案的标准终态）has_at=False，但仍需探测——
        # 判定依据应是 **DNS 实际状态**，不是平台绑定状态。所以只要不是子域组就探测。
        if dig_ok and not is_subdomain_group:
            try:
                probe = dns_state(base, None)
                apex_cf_hint = any(is_cf_proxy_ip(x) for x in probe.get("a", []))
            except (DnsTimeout, DnsUnavailable, DnsQueryError):
                pass
            if apex_cf_hint:
                ok, detail = probe_apex_redirect(base, "www." + base)
                apex_via_cf = bool(ok)
                apex_redirect_detail = detail
                if ok is None:
                    add("warn", f"{base}：根域指向 Cloudflare 代理，但{detail}"
                                f"——无法确认 301 方案是否生效，请人工核对")
                elif not ok:
                    # 实测未通过：可能是规则缺失，也可能是瞬时抖动 → warn 而非 error，
                    # 避免网络抖动被报成"指向错误"（下面 apex 分支会给出准确提示）
                    add("warn", f"{base}：根域指向 Cloudflare 代理，但{detail}"
                                f"——若是新配的规则，稍后复查确认")

        if not is_subdomain_group:
            emit(f"② 平台已绑定：{'@ ' if has_at else ''}{'www ' if has_www else ''}".rstrip())
        if not is_subdomain_group and not has_at:
            if apex_via_cf:
                add("info", f"{base}：根域未绑到平台——**符合 301 方案**（根域由 Cloudflare 全权处理，"
                            f"平台无需验证它）")
            else:
                entry["issues"].append("平台未绑定根域名（@）")
                add("warn", f"{base}：平台未绑定根域名（@）")
        if not is_subdomain_group and not has_www:
            entry["issues"].append("平台未绑定 www 子域")
            add("warn", f"{base}：平台未绑定 www（多数客户习惯输 www）")

        # ③ NS 服务商（只查注册域，不查子域）；顺带拿到权威 NS 用于绕缓存
        provider, risk, ns_list, auth_ns = "未知", "unknown", [], None
        if dig_ok:
            try:
                ns_list = run_dig(["NS", base])
            except (DnsTimeout, DnsQueryError) as e:
                add("warn", f"{base}：NS 查询失败（{str(e)[:40]}），未能判定 DNS 服务商")
                ns_list = []
            if ns_list:
                auth_ns = ns_list[0]  # 直接问权威，避开本地递归缓存
            if ns_list:
                provider, risk = identify_provider(ns_list)
                emit(f"③ DNS 服务商：{provider}（NS: {', '.join(ns_list[:3])}）")
                entry["provider"] = provider
                if risk == "warn-flatten" and apex_via_cf:
                    add("info", f"{base}：DNS 在 Cloudflare——根域已按 301 方案处理"
                                f"（实测确认：{apex_redirect_detail}），符合预期")
                elif risk == "warn-flatten":
                    add("warn", f"{base}：DNS 在 Cloudflare——**根域（@）CNAME 会被自动展平**"
                                f"（官方文档：apex 记录默认展平且 Flatten 开关不可用），"
                                f"EdgeOne 无法验证根域。建议：① www 为主域名 + 根域 301 跳转到 www"
                                f"（注意：CF 的 301 规则**要求根域走橙云代理**，而 www 必须保持**灰云**"
                                f"才能通过平台验证——两条记录代理状态相反）；"
                                f"或 ② 把 DNS 迁到阿里云（根域 CNAME 可保留原记录）")
                elif risk == "unknown":
                    add("warn", f"{base}：未识别的 DNS 服务商（{ns_list[0]}），"
                                f"全部 NS：{', '.join(ns_list)}——请人工确认是否支持根域 CNAME")
                elif provider.startswith("阿里云"):
                    # 阿里云支持带域名的直达链接（实测：未登录先跳登录，登录后回到该域名解析页）
                    add("info", f"{base}：阿里云解析——给用户的直达链接："
                                f"https://dnsnext.console.aliyun.com/authoritative/domains/{base}"
                                f"（打开即进解析设置；@ 与 www 都可加 CNAME，实测与 MX 共存无冲突）")
            else:
                emit("③ DNS 服务商：❓ 查不到 NS 记录（域名可能未注册或 DNS 未接入）")
                add("warn", f"{base}：查不到 NS 记录，请确认域名已注册且 DNS 已接入")

        # ④ CNAME 是否配对（先解析目标允许的 A 集合，供展平场景比对）
        tgt_ips = set()
        if dig_ok and cname_target:
            try:
                tgt_ips = set(run_dig(["A", cname_target]))
            except (DnsTimeout, DnsUnavailable, DnsQueryError):
                tgt_ips = set()

        # B3：子域组只校验它自己，不合成 www.<subdomain>
        if is_subdomain_group:
            host_iter = (("self", base),)
        else:
            host_iter = (("@", base), ("www", f"www.{base}"))
        for host_key, label in host_iter:
            rec = pair.get(host_key)
            per_host_apex_cf = False          # B1：每轮显式初始化，防"无记录分支"未赋值即被引用
            if not dig_ok:
                entry["hosts"][host_key] = {"platform": rec, "dns": None}
                continue
            try:
                state = dns_state(label, auth_ns)
            except (DnsTimeout, DnsUnavailable, DnsQueryError) as e:
                state = {"cname": [], "a": [], "resolved": False, "error": str(e)}

            if state.get("error"):
                err = str(state["error"])
                if err.startswith("timeout"):
                    msg = "DNS 查询超时，未能判定（网络抖动，非解析错误）"
                elif err.startswith("query-error"):
                    msg = f"DNS 查询失败（{err.split(':',1)[1].strip()[:60]}）——非『未配置』"
                elif err.startswith("dig-unavailable"):
                    msg = "本机无 dig，无法核验"
                else:
                    msg = err
                emit(f"④ {label}：⚠️  {msg}")
                add("warn", f"{label}：{msg}")
                entry["hosts"][host_key] = {"platform": rec, "dns": state}
                continue

            actual = (state["cname"] or state["a"] or ["<无记录>"])[0]
            src = "权威NS" if state.get("via") == "auth" else "本地缓存"
            line = f"④ {label}：{src}解析 → {actual}"
            if rec:
                p_cname = rec.get("cnameStatus")
                line += f"｜平台 cname={p_cname}（{CNAME_STATUS_CN.get(p_cname, p_cname)}）"
                if rec.get("certificateStatus"):
                    cs = rec["certificateStatus"]
                    line += f"｜SSL={cs}（{CERT_STATUS_CN.get(cs, cs)}）"
            emit(line)
            entry["hosts"][host_key] = {"platform": rec, "dns": state}

            if not state["resolved"]:
                entry["issues"].append(f"{label} 本地无解析记录")
                add("error", f"{label}：本地查不到任何解析记录（DNS 未配置）")
                continue                       # B1：本主机判定结束，后续逻辑不再适用
            else:
                # BLOCKER-3：规范化后"精确相等"，不再用子串匹配（防 evil-<target> 误判为通过）
                hit = any(norm_host(x) == cname_target for x in state["cname"])
                # M9：A 记录交集回退**仅用于 apex**（展平机制）；www 必须命中 CNAME 本身，
                # 否则平台看不到 CNAME 无法验证（DOMAIN-SETUP「验证是看 CNAME 记录本身」）。
                if not hit and tgt_ips and host_key == "@":
                    hit = bool(tgt_ips & {norm_host(x) for x in state["a"]})
                if not hit and host_key == "www" and state["a"] and not state["cname"]:
                    add("warn", f"{label}：该主机只有 A 记录（无 CNAME）——平台按 CNAME 验证，"
                                f"可能无法通过；建议改回 CNAME 指向 {cname_target}")
                # apex 301 方案（B2：外层已**实测**确认 301 跳转存在，非仅靠 IP 启发式）。
                # 仅当 host_key=="@" 且外层实测通过时，才把"指向 CF 代理 IP"视为合法终态。
                per_host_apex_cf = (host_key == "@" and apex_via_cf)
                if per_host_apex_cf:
                    entry["hosts"].setdefault(host_key, {})["apex_via_cf"] = True
                    add("info", f"{label}：根域走 Cloudflare 代理且**实测确认** 301 跳转到 www"
                                f"——平台无需验证根域，属预期终态")
                elif not hit:
                    entry["issues"].append(f"{label} 指向不是 {cname_target}")
                    add("error", f"{label}：当前指向 {actual}，应指向 {cname_target}")

            if per_host_apex_cf:
                # B2：不再直接建议 delete_domain（破坏性动作需人工授权）；只提示现状与选项
                if rec:
                    add("info", f"{label}：该根域仍绑在平台上——301 方案下平台无法验证它，"
                                f"会持续显示失败告警。是否解绑由人工决定（解绑属破坏性操作，"
                                f"需按 RUNBOOK 授权流程执行）")
            elif rec and rec.get("cnameStatus") and rec["cnameStatus"] != "active":
                st = rec["cnameStatus"]
                if st == "moved":
                    add("warn", f"{label}：平台状态 moved（等待生效）——平台仍在同步，"
                                f"先 refresh_domain 稍后复查，不要立刻让客户改 DNS")
                else:
                    add("error" if st == "invalid" else "warn",
                        f"{label}：平台状态 {st}（{CNAME_STATUS_CN.get(st, st)}）")
            # ⑤ SSL/TLS 双层检测：**先本地实测握手与证书**，再与平台侧状态交叉校验。
            # 本地是唯一真相来源——平台显示 active 也可能实际握手失败（证书吊销/域名改指）。
            tls = probe_tls(label)
            entry["hosts"][host_key]["tls"] = tls
            p_cert = (rec or {}).get("certificateStatus")
            if tls["verified"]:
                dl = tls.get("days_left")
                # 线上可达性（TLS 只证明握手，这里证明网站真的能打开）
                http = probe_http(label)
                entry["hosts"][host_key]["http"] = http
                mark = "✅" if http["ok"] else ("❌" if http["status"] else "⚠️")
                hop = f"（{http['redirects']} 次跳转 → {http['final_url']}）" if http.get("redirects") else ""
                emit(f"⑤ {label}：SSL/CERT ✅ | 线上访问 {mark} HTTP {http['status'] or '-'}{hop}"
                     f"｜CN={tls.get('cn')}｜剩余 {dl} 天")
                if dl is not None and dl <= 30:
                    add("warn", f"{label}：SSL 证书仅剩 {dl} 天（到期 {tls.get('not_after')}）"
                                f"——平台通常自动续期，临近时复查")
                if not http["ok"]:
                    add("error", f"{label}：证书正常但**线上访问失败**（{http.get('error')}）"
                                 f"——落点 {http.get('final_url') or '未知'}")
                if p_cert in ("none", "requested", "failed"):
                    add("warn", f"{label}：本地 SSL 已正常，但平台证书状态仍为 {p_cert}"
                                f"——平台状态可能滞后，refresh_domain 后复查")
            else:
                reason = tls.get("reason") or "未知原因"
                served = tls.get("served") or []
                extra = f"；服务端实际提供：{', '.join(served)}" if served else ""
                http = probe_http(label)
                entry["hosts"][host_key]["http"] = http
                if tls["handshake"]:
                    emit(f"⑤ {label}：SSL ❌ {reason}{extra}｜线上访问 HTTP {http['status'] or '失败'}")
                else:
                    emit(f"⑤ {label}：SSL ❌ {reason}；线上访问 HTTP {http['status'] or '失败'}")
                if p_cert in ("none", "requested"):
                    # 平台正在签发 → 属过渡态，不是需要客户动手的问题
                    add("warn", f"{label}：SSL 尚未就绪（{reason}）——平台证书状态 {p_cert}，"
                                f"签发完成后复查{extra}")
                else:
                    add("error", f"{label}：SSL 不可用——{reason}{extra}")
                    if p_cert == "active":
                        add("error", f"{label}：**平台显示证书 active 但本地握手失败**——两侧矛盾，"
                                    f"需排查（证书被吊销 / 域名指向了别的服务）")

        result["domains"].append(entry)
        emit()
    return result


def main():
    ap = argparse.ArgumentParser(description="域名巡检（平台 + DNS 双向对账）")
    ap.add_argument("site_slug", help="站点 slug")
    ap.add_argument("--domain", help="只检查指定域名（必须已绑定）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON（可直接落盘为 domain-report.json）")
    ap.add_argument("--out", help="把 JSON 写入指定文件")
    args = ap.parse_args()

    email = os.environ.get("WS_EMAIL")
    password = os.environ.get("WS_PASSWORD")
    token = os.environ.get("WS_TOKEN")
    if not token and not (email and password):
        print("BLOCK: 需要 WS_TOKEN 或 WS_EMAIL+WS_PASSWORD 环境变量")
        return 2
    try:
        from allincms_api import AllinCMS
    except ImportError:
        print("BLOCK: 找不到 allincms_api.py（本脚本需与它同目录）")
        return 2

    quiet = bool(args.json or args.out)
    try:
        api = AllinCMS(token=token) if token else AllinCMS(email=email, password=password)
        res = check_site(api, args.site_slug, args.domain, quiet=quiet)
    except RuntimeError as e:          # 站点不存在等业务错误 → 退出 2
        print(f"BLOCK: {e}")
        return 2
    except Exception as e:             # M7：网络异常/未预期崩溃 → 退出 2（不与"有须修项"同码）
        print(f"BLOCK: 巡检执行异常（{type(e).__name__}: {e}）")
        return 2

    if args.json or args.out:
        payload = json.dumps(res, ensure_ascii=False, indent=2)
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(payload + "\n")
            except OSError as e:                    # M7：写盘失败归环境错误（2）
                print(f"BLOCK: 无法写入 {args.out}: {e}", file=sys.stderr)
                return 2
            print(f"已写入 {args.out}", file=sys.stderr)   # M10：提示走 stderr，保持 stdout 纯净
        if args.json:
            print(payload)
    else:
        print("=" * 56)
        errs = [f for f in res["findings"] if f["level"] == "error"]
        warns = [f for f in res["findings"] if f["level"] == "warn"]
        infos = [f for f in res["findings"] if f["level"] == "info"]
        if not errs and not warns:
            print("✅ 巡检通过：域名配置无问题")
        for f in errs:
            print(f"❌ {f['text']}")
        for f in warns:
            print(f"⚠️  {f['text']}")
        for f in infos:
            print(f"ℹ️  {f['text']}")
        print(f"\n小结：{len(errs)} 个须修 / {len(warns)} 个提醒")

    # 退出码：2=环境缺失（无 dig）/ 1=有须修项 / 0=正常（无域名属合法中间态）
    if res.get("env_error"):
        return 2
    return 1 if any(f["level"] == "error" for f in res["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
