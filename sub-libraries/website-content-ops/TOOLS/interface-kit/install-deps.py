#!/usr/bin/env python3
"""依赖安装器（install-deps.py）—— 跨平台（mac/win/linux），零依赖。

用途：新环境/新电脑拿到 interface-kit 后，先跑本脚本完成"检测 → 安装 → 复检"。
与 requirements.txt / SETUP.md / doc-capability-check.py 配套。

用法：
  python3 install-deps.py              # 检测并给出建议（不安装）
  python3 install-deps.py --yes        # 一键安装缺失项（pip install --user；仅 docs-parse 层）
  python3 install-deps.py --verify     # 安装后复检（等价 doc-capability-check + registry verify）
"""
import importlib.util as _iu, os, shutil, subprocess, sys, platform

DOC_PKGS = ["pypdf", "docx", "pptx", "openpyxl"]   # docx=python-docx / pptx=python-pptx 的导入名
PIP_NAMES = {"pypdf": "pypdf", "docx": "python-docx", "pptx": "python-pptx", "openpyxl": "openpyxl"}
NODE_NEEDED = "canonical 校验（validate-links/validate-sub-library）使用"

def have(mod): return _iu.find_spec(mod) is not None

def MISSING_TO_PIP(missing):
    """missing 项名（显示名）→ pip 包名；pypdf 显示名直接即包名"""
    return [PIP_NAMES.get(m, m) for m in missing]

def check_all():
    sys_ = platform.system()
    out = {"runtime": ("ok", "stdlib 零依赖（面向建站/索引/监控/图片门）"), "docs_parse": [], "canonical": None}
    pdf_ok = have("pypdf") or have("PyPDF2") or shutil.which("pdftotext") is not None
    out["docs_parse"].append(("pypdf (或 PyPDF2 / poppler pdftotext)", "ok" if pdf_ok else "missing"))
    for m in ("docx", "pptx", "openpyxl"):
        out["docs_parse"].append((m, "ok" if have(m) else "missing"))
    out["canonical"] = ("ok", shutil.which("node") or "missing")
    return sys_, out

def main():
    args = sys.argv[1:]
    sys_, m = check_all()
    print(f"== 环境：{sys_} / Python {sys.version.split()[0]} ==")
    print(f"[runtime] {m['runtime'][1]}")
    print("[docs-parse]（解析用户 PDF/DOCX/PPTX/XLSX；不解析可不装）")
    missing = []
    for name, st in m["docs_parse"]:
        print(f"   {'ok ' if st == 'ok' else 'MISSING':8s} {name:28s}")
        if st != "ok": missing.append(name)
    node = m["canonical"]
    print(f"[canonical] {'ok  ' if node[1] != 'missing' else 'MISSING'} node（{NODE_NEEDED}；不跑子库校验可不装）")
    if "node" in (node[1] or ""): print("   apt/brew 安装 node >=18 即可（mac: brew install node）")
    if missing:
        print("\n缺失：", ", ".join(missing))
        if "--yes" in args:
            cmd = [sys.executable, "-m", "pip", "install", "--user"] + MISSING_TO_PIP(missing)
            print("执行:", " ".join(cmd))
            r = subprocess.run(cmd)
            print("pip exit:", r.returncode)
        else:
            print("安装：python3 install-deps.py --yes")
    else:
        print("\n[docs-parse] 全部就绪")
    if "--verify" in args:
        print("\n== 复检 ==")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "doc-capability-check.py")])
    print("\n下一步：SETUP.md -> 校验 -> 冒烟（allincms_api.py read-sites）")

if __name__ == "__main__":
    main()
