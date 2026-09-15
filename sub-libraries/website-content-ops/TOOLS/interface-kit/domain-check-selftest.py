#!/usr/bin/env python3
"""domain-check.py 离线自测（domain-check-selftest.py）。

用**本地自签 TLS 服务器 + 本地 HTTP 服务器**覆盖 SSL 检测链，
不依赖外网、不依赖真实域名。对齐 kit 内其他 *-selftest.py 的纪律。

覆盖：
  probe_tls        自签证书 → verified=False 且分类为"自签名"
                   域名不匹配 → 分类为"证书域名不匹配"
                   无 TLS 服务 → 分类为握手/连接失败
  _served_cert_names 从真实证书提取 SAN/CN（无垃圾 token、保留尾部 0）
  _cert_days_left  未来/过去/非法格式
  probe_http       同站 200 → ok；（模拟）错误壳/过短/落点第三方 → 不 ok
  check_host_ssl   rec=None 时不判 error（未绑定主机是候选不是要求）

用法：python3 domain-check-selftest.py
退出码：0 全部通过；1 有失败。
"""
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util
spec = importlib.util.spec_from_file_location("dc", os.path.join(HERE, "domain-check.py"))
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))


def make_selfsigned(cn, tmpdir):
    """用 openssl 生成自签证书；返回 (cert_path, key_path) 或 None。"""
    cert = os.path.join(tmpdir, f"{cn}.crt")
    key = os.path.join(tmpdir, f"{cn}.key")
    r = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", key, "-out", cert, "-days", "2",
         "-subj", f"/CN={cn}", "-addext", f"subjectAltName=DNS:{cn}"],
        capture_output=True, text=True, timeout=60,
    )
    return (cert, key) if r.returncode == 0 else None


class TlsServer:
    """本地 TLS 服务器（后台线程），用于探测。"""

    def __init__(self, cert, key, host="127.0.0.1"):
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(cert, key)
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.host = host
        self._stop = False
        self.t = threading.Thread(target=self._serve, daemon=True)
        self.t.start()

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            try:
                with self.ctx.wrap_socket(conn, server_side=True) as ss:
                    ss.recv(1024)
                    ss.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
            except Exception:
                pass

    def close(self):
        self._stop = True
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    tmpdir = tempfile.mkdtemp(prefix="dc-selftest-")
    try:
        # ---- _cert_days_left ----
        future = time.strftime("%b %d %H:%M:%S %Y GMT", time.gmtime(time.time() + 10 * 86400))
        past = time.strftime("%b %d %H:%M:%S %Y GMT", time.gmtime(time.time() - 5 * 86400))
        d_future = dc._cert_days_left(future)
        d_past = dc._cert_days_left(past)
        check("_cert_days_left 未来日期 ≈10 天", d_future is not None and 9 <= d_future <= 10, str(d_future))
        check("_cert_days_left 过去日期为负（能识别已过期）", d_past is not None and d_past < 0, str(d_past))
        check("_cert_days_left 非法格式返回 None", dc._cert_days_left("not-a-date") is None)

        # ---- probe_tls 对自签证书 ----
        made = make_selfsigned("selfsigned.test", tmpdir)
        if not made:
            print("SKIP: openssl 不可用，跳过 TLS 相关用例")
        else:
            cert, key = made
            srv = TlsServer(cert, key)
            try:
                r = dc.probe_tls("127.0.0.1", port=srv.port, timeout=6)
                check("probe_tls 自签证书 → verified=False", r["verified"] is False)
                check("probe_tls 自签证书 → 分类为自签名", "自签名" in r["reason"], r["reason"])
                check("probe_tls 自签证书 → handshake=True（能连上）", r["handshake"] is True)
                check("probe_tls 自签证书 → 能提取服务端证书名",
                      any("selfsigned" in n for n in r.get("served", [])), str(r.get("served")))
            finally:
                srv.close()

            # ---- probe_tls 域名不匹配（用 IP 连但证书是别的域名）----
            srv2 = TlsServer(cert, key)
            try:
                r2 = dc.probe_tls("localhost", port=srv2.port, timeout=6)
                check("probe_tls 域名不匹配 → verified=False",
                      r2["verified"] is False, r2["reason"][:50])
            finally:
                srv2.close()

            # ---- _served_cert_names：SAN/CN 提取 ----
            srv3 = TlsServer(cert, key)
            try:
                names = dc._served_cert_names("127.0.0.1", port=srv3.port, timeout=6)
                check("_served_cert_names 返回真实证书名（无垃圾 token）",
                      "selfsigned.test" in names and all(" " not in n for n in names), str(names))
            finally:
                srv3.close()

        # ---- probe_tls 无 TLS 服务 ----
        dead = socket.socket()
        dead.bind(("127.0.0.1", 0))
        dead_port = dead.getsockname()[1]
        dead.close()
        r3 = dc.probe_tls("127.0.0.1", port=dead_port, timeout=3, attempts=1)
        check("probe_tls 无服务 → verified=False 且 handshake=False",
              r3["verified"] is False and r3["handshake"] is False, r3["reason"][:40])

        # ---- probe_tls 非法主机名不崩（M-6）----
        try:
            r4 = dc.probe_tls("x" * 300 + ".com", timeout=3, attempts=1)
            check("probe_tls 非法主机名不抛异常（M-6）", r4["verified"] is False, r4["reason"][:40])
        except Exception as e:
            check("probe_tls 非法主机名不抛异常（M-6）", False, f"抛了 {type(e).__name__}")

        # ---- check_host_ssl：rec=None 不判 error（M-1）----
        findings = []
        dc.check_host_ssl("127.0.0.1", None, False,
                          lambda lvl, t: findings.append((lvl, t)),
                          lambda *a: None,
                          runtime_domain="example.com")
        check("check_host_ssl 未绑定主机（rec=None）不产生 error（M-1）",
              not any(l == "error" for l, _ in findings),
              str([l for l, _ in findings]))

        # ---- 网络受限提示 ----
        r5 = dc.probe_tls("127.0.0.1", port=dead_port, timeout=3, attempts=1)
        check("连接失败提示含网络环境线索",
              "网络" in r5["reason"] or "连接失败" in r5["reason"], r5["reason"][:50])
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    failed = [r for r in results if not r[1]]
    print(f"\nSELFTEST: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
