#!/usr/bin/env python3
"""依赖安装器（install-deps.py）—— 跨平台（mac/win/linux），零依赖。

用途：新环境/新电脑拿到 interface-kit 后，先跑本脚本完成"检测 → 安装 → 复检"。
与 requirements.txt / SETUP.md / doc-capability-check.py 配套。

用法：
  python3 install-deps.py              # 检测并给出建议（不安装）
  python3 install-deps.py --yes        # 一键安装（pip install --user；装 requirements 全部 4 包，不只缺失项）
  python3 install-deps.py --verify     # 安装后复检（等价 doc-capability-check + registry verify）

检测口径（ISS-120，Windows field build 实测）：
  - pypdf 的 ok 判定 = 新开子进程 `python -c "import pypdf"` 实测——pdftotext 存在不再短路
    （有 pdftotext 而 pypdf 缺失时，docs-parse 解析路径仍会 import pypdf 失败）。
  - 安装后复检同样用新子进程实测：包进入 --user site-packages 后，当前进程 sys.path
    不会刷新，同进程 find_spec 会误报 missing（--yes 后"复检仍缺"误报即此根因）。
"""
import importlib.util as _iu, os, shutil, subprocess, sys, platform

DOC_MODULES = [("pypdf", "pypdf (docs-parse 直接 import pypdf；pdftotext 不替代判定)"), ("docx", "python-docx"), ("pptx", "python-pptx"), ("openpyxl", "openpyxl")]
PIP_NAMES = {"pypdf": "pypdf", "docx": "python-docx", "pptx": "python-pptx", "openpyxl": "openpyxl"}
NODE_NEEDED = "canonical 校验（validate-links/validate-sub-library）使用"

# 一次子进程探完全部模块（真实 import 环境 = 未来脚本运行的环境，含 --user site-packages）
_PROBE_CODE = ("import importlib.util as u;print(','.join("
               "'ok' if u.find_spec(m) is not None else 'missing' for m in %r))"
               % [mod for mod, _ in DOC_MODULES])

def probe_modules():
    """新开子进程实测各模块可导入性。返回 {模块名: True/False}；子进程异常时回退本进程 find_spec。"""
    try:
        r = subprocess.run([sys.executable, "-c", _PROBE_CODE],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            states = r.stdout.strip().split(",")
            if len(states) == len(DOC_MODULES):
                return {mod: st == "ok" for (mod, _), st in zip(DOC_MODULES, states)}
    except Exception:
        pass
    return {mod: _iu.find_spec(mod) is not None for mod, _ in DOC_MODULES}

def have(mod): return _iu.find_spec(mod) is not None

def MISSING_TO_PIP(missing):
    """缺失项（模块名）→ pip 包名；未收录的模块名原样返回（不会把整段展示文字交给 pip）。"""
    return [PIP_NAMES.get(m, m) for m in missing]

def check_all():
    sys_ = platform.system()
    out = {"runtime": ("ok", "stdlib 零依赖（面向建站/索引/监控/图片门）"), "docs_parse": [], "canonical": None}
    probed = probe_modules()   # ISS-120：统一子进程实测（pypdf 不再被 pdftotext 短路；复检同口径）
    for mod, display in DOC_MODULES:
        out["docs_parse"].append((mod, display, "ok" if probed.get(mod) else "missing"))
    out["canonical"] = ("ok", shutil.which("node") or "missing")
    return sys_, out

def main():
    args = sys.argv[1:]
    sys_, m = check_all()
    print(f"== 环境：{sys_} / Python {sys.version.split()[0]} ==")
    print(f"[runtime] {m['runtime'][1]}")
    print("[docs-parse]（解析用户 PDF/DOCX/PPTX/XLSX；不解析可不装）")
    missing = []
    for mod, display, st in m["docs_parse"]:
        print(f"   {'ok ' if st == 'ok' else 'MISSING':8s} {display:28s}")
        if st != "ok": missing.append(mod)
    node = m["canonical"]
    node_ver = None
    if node[1] != "missing":
        try:
            v = subprocess.run(["node", "-v"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=10).stdout.strip()
            node_ver = v.lstrip("v")
        except Exception:
            node_ver = None
    print(f"[canonical] {'ok  ' if node[1] != 'missing' else 'MISSING'} node（{NODE_NEEDED}；不跑子库校验可不装）")
    if node_ver:
        try:
            major, minor = (int(x) for x in node_ver.split(".")[:2])
            if major < 20 or (major == 20 and minor < 9):
                print("   当前 Node", node_ver, "低于 Adapter 要求 >=20.9.0；运行 Adapter 安装/测试前请先升级。")
        except Exception:
            pass
    elif node[1] == "missing":
        print("   安装 node >=20.9（mac: brew install node；ubuntu: apt install -y nodejs npm；windows: choco install nodejs-lts 或 https://nodejs.org）")
    if missing:
        print("\n缺失：", ", ".join(missing))
        if "--yes" in args:
            # ISS-120：--yes 直接安装 requirements 全部 4 包（不只检测缺失项）——
            # pip 依赖解析按 requirements 整组装更稳，也避免"pdftotext 在场漏装 pypdf"类误判复发。
            cmd = [sys.executable, "-m", "pip", "install", "--user"] + sorted(set(PIP_NAMES.values()))
            print("执行:", " ".join(cmd))
            r = subprocess.run(cmd)
            print("pip exit:", r.returncode)
            if r.returncode != 0:
                print("PIP_INSTALL_FAILED：请检查网络/pip 源后重试，或手动执行上面命令。", file=sys.stderr)
                return 1
            # 复检（ISS-120）：check_all 内部已改为新开子进程 import 实测——
            # 刚装进 --user site-packages 的包对当前进程 sys.path 不可见，同进程复检必误报。
            _, m2 = check_all()
            still_missing = [mod for mod, _disp, st in m2["docs_parse"] if st != "ok"]
            if still_missing:
                print("复检仍缺：", ", ".join(still_missing), file=sys.stderr)
                return 1
            print("[docs-parse] 安装完成，全部就绪。")
        else:
            print("安装：python3 install-deps.py --yes")
            return 1
    else:
        print("\n[docs-parse] 全部就绪")
    if "--verify" in args:
        print("\n== 复检 ==")
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "doc-capability-check.py")])
        if r.returncode != 0:
            return 1
    print("\n下一步：SETUP.md -> 校验 -> 冒烟（allincms_api.py read-sites）")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
