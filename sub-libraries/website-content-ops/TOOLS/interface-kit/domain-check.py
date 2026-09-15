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
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

NS_PROVIDERS = [
    (r"\.ns\.cloudflare\.com$", "Cloudflare", "warn-flatten"),
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
        return []
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


def norm_host(v):
    """主机名规范化：trim + lower + 去尾点（对齐平台 ed() 的比对口径）。"""
    return (v or "").strip().lower().rstrip(".")


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
    out["resolved"] = bool(out["cname"] or out["a"])
    return out


def check_site(api, site_slug, only_domain=None, quiet=False):
    """巡检一个站点。quiet=True 时不打印人读文本（供 --json 使用）。"""
    result = {"site_slug": site_slug, "findings": [], "domains": [], "ok": True}

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
        add("error", "本机没有 dig，无法做 DNS 侧核验（Windows 请装 BIND tools 或改用 nslookup）；"
                     "本次只输出平台侧状态")
    except DnsTimeout:
        pass  # 单次超时不代表不可用

    # MAJOR-9：按注册域分组（apex 判定基于"最后两段"，非仅去 www 前缀）
    def registrable(host):
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host

    groups = {}
    for d in domains:
        dom = norm_host(d.get("domain"))
        reg = registrable(dom)
        # apex = 域名本身等于注册域；www.x 和 x 归到同一 base
        is_apex = dom == reg
        base = reg if is_apex or dom.startswith("www." + reg) else dom
        groups.setdefault(base, {})["@" if is_apex else "www"] = d

    for base, pair in groups.items():
        entry = {"domain": base, "hosts": {}, "provider": None, "issues": []}
        emit(f"—— 域名：{base} ——")

        has_at, has_www = "@" in pair, "www" in pair

        # 先探测 apex 是否走 CF 301 方案（决定后续告警口径）
        apex_cf_scheme = False
        if dig_ok:
            try:
                probe = dns_state(base, None)  # 根域常被展平，用本地/默认查询即可
                apex_cf_scheme = any(is_cf_proxy_ip(x) for x in probe.get("a", []))
            except (DnsTimeout, DnsUnavailable):
                pass

        emit(f"② 平台已绑定：{'@ ' if has_at else ''}{'www ' if has_www else ''}".rstrip())
        if not has_at:
            if apex_cf_scheme:
                add("info", f"{base}：根域未绑到平台——**符合 301 方案**（根域由 Cloudflare 全权处理，"
                            f"平台无需验证它）")
            else:
                entry["issues"].append("平台未绑定根域名（@）")
                add("warn", f"{base}：平台未绑定根域名（@）")
        if not has_www:
            entry["issues"].append("平台未绑定 www 子域")
            add("warn", f"{base}：平台未绑定 www（多数客户习惯输 www）")

        # ③ NS 服务商（只查注册域，不查子域）；顺带拿到权威 NS 用于绕缓存
        provider, risk, ns_list, auth_ns = "未知", "unknown", [], None
        if dig_ok:
            try:
                ns_list = run_dig(["NS", base])
            except DnsTimeout:
                add("warn", f"{base}：NS 查询超时，未能判定 DNS 服务商")
                ns_list = []
            if ns_list:
                auth_ns = ns_list[0]  # 直接问权威，避开本地递归缓存
            if ns_list:
                provider, risk = identify_provider(ns_list)
                emit(f"③ DNS 服务商：{provider}（NS: {', '.join(ns_list[:3])}）")
                entry["provider"] = provider
                if risk == "warn-flatten" and apex_cf_scheme:
                    add("info", f"{base}：DNS 在 Cloudflare——根域已按 301 方案处理"
                                f"（指向 CF 代理 IP，流量在边缘跳转到 www），符合预期")
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
            else:
                emit("③ DNS 服务商：❓ 查不到 NS 记录（域名可能未注册或 DNS 未接入）")
                add("warn", f"{base}：查不到 NS 记录，请确认域名已注册且 DNS 已接入")

        # ④ CNAME 是否配对（先解析目标允许的 A 集合，供展平场景比对）
        tgt_ips = set()
        if dig_ok and cname_target:
            try:
                tgt_ips = set(run_dig(["A", cname_target]))
            except (DnsTimeout, DnsUnavailable):
                tgt_ips = set()

        for host_key, label in (("@", base), ("www", f"www.{base}")):
            rec = pair.get(host_key)
            if not dig_ok:
                entry["hosts"][host_key] = {"platform": rec, "dns": None}
                continue
            try:
                state = dns_state(label, auth_ns)
            except (DnsTimeout, DnsUnavailable) as e:
                state = {"cname": [], "a": [], "resolved": False, "error": str(e)}

            if state.get("error"):
                msg = ("DNS 查询超时，未能判定（网络抖动，非解析错误）"
                       if str(state["error"]).startswith("timeout") else str(state["error"]))
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
            else:
                # BLOCKER-3：规范化后"精确相等"，不再用子串匹配（防 evil-<target> 误判为通过）
                hit = any(norm_host(x) == cname_target for x in state["cname"])
                # MAJOR-10：展平场景——A 记录与目标的 A 集合求交
                if not hit and tgt_ips:
                    hit = bool(tgt_ips & {norm_host(x) for x in state["a"]})
                # apex 301 方案：根域指向 CF 代理 IP 属**合法终态**（流量在 CF 边缘 301 到 www，
                # 根本不到 EdgeOne，所以平台不需要验证根域）。识别后不再报"指向错误"。
                apex_via_cf = (host_key == "@"
                               and any(is_cf_proxy_ip(x) for x in state["a"]))
                if apex_via_cf:
                    entry["hosts"].setdefault(host_key, {})["apex_via_cf"] = True
                    add("info", f"{label}：根域走 Cloudflare 代理（301 跳转到 www 方案）——"
                                f"平台无需验证根域，属预期终态")
                elif not hit:
                    entry["issues"].append(f"{label} 指向不是 {cname_target}")
                    add("error", f"{label}：当前指向 {actual}，应指向 {cname_target}")

            if apex_via_cf:
                # 301 方案下平台不该绑根域；若仍绑着会残留 moved/failed 告警 → 建议解绑
                if rec:
                    add("info", f"{label}：该根域仍绑在平台上——301 方案下建议解绑"
                                f"（api.delete_domain），否则平台会一直显示验证失败告警")
            elif rec and rec.get("cnameStatus") and rec["cnameStatus"] != "active":
                st = rec["cnameStatus"]
                if st == "moved":
                    add("warn", f"{label}：平台状态 moved（等待生效）——平台仍在同步，"
                                f"先 refresh_domain 稍后复查，不要立刻让客户改 DNS")
                else:
                    add("error" if st == "invalid" else "warn",
                        f"{label}：平台状态 {st}（{CNAME_STATUS_CN.get(st, st)}）")
            if rec and rec.get("certificateStatus") == "failed" and not apex_via_cf:
                # MAJOR-8：平台无证书申请 action（actions 只有 add/refresh/setPrimary/setEnabled/delete），
                # 证书由平台在 DNS 校验通过后自动签发——不要引导用户/客户去找不存在的"申请接口"。
                add("warn", f"{label}：SSL 证书未签发——修正 DNS 后用 refresh_domain 同步；"
                            f"证书由平台在校验通过后自动签发（AI 无直接申请接口）")

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

    api = AllinCMS(token=token) if token else AllinCMS(email=email, password=password)
    quiet = bool(args.json or args.out)
    try:
        res = check_site(api, args.site_slug, args.domain, quiet=quiet)
    except RuntimeError as e:          # M1：站点不存在等业务错误 → 退出 2
        print(f"BLOCK: {e}")
        return 2

    if args.json or args.out:
        payload = json.dumps(res, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(payload + "\n")
            print(f"已写入 {args.out}")   # 这条走 stdout，但--json 已不混入
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

    # MAJOR-4：退出码只按 error 判定（无域名属合法中间态 → 0）
    return 1 if any(f["level"] == "error" for f in res["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
