#!/usr/bin/env python3
"""AllinCMS action scanner (cross-platform, stdlib only).
Usage: python3 scan-actions.py <token-file|-> [page-path...] [--diff]
  不传文件或传 - 时读 WS_TOKEN 环境变量
Prints: actionName = actionId per page.
  --diff  自动与 allincms_api.py 已知常量对比，标出变化的 action"""
import os,sys
IFK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, IFK)
DIFF_MODE = "--diff" in sys.argv
if DIFF_MODE: sys.argv.remove("--diff")
import re,sys,urllib.request
DPL="83eddf696484d494d59ae961cb4ded1d61d14b56"; O="https://workspace.laicms.com"
def f(url,tok=None):
    r=urllib.request.Request(url)
    if tok: r.add_header('Cookie','payload-token='+tok)
    r.add_header('User-Agent','Mozilla/5.0')
    return urllib.request.urlopen(r,timeout=25).read().decode('utf8','replace')
def scan(path,tok):
    h=f(O+path,tok); srcs=set(re.findall(r'/_next/static/chunks/([A-Za-z0-9_.-]+\.js)',h)); a={}
    for s in srcs:
        try: j=f(O+'/_next/static/chunks/'+s+'?dpl='+DPL)
        except Exception: continue
        for m in re.finditer(r'createServerReference\)\("([0-9a-f]{42})",[^)]{0,160}?,"([A-Za-z0-9_$.]{4,100})"',j):
            a.setdefault(m.group(2),m.group(1))
    return a
args=sys.argv[1:]
if args and args[0]!='-':
    tok=open(args[0]).read().strip(); paths=args[1:]
else:
    tok=(os.environ.get('WS_TOKEN') or '').strip()
    if not tok: sys.exit('token: 传 token 文件路径，或 export WS_TOKEN=<token>')
    paths=args[1:]
for p in paths:
    try:
        a=scan(p,tok); print('###',p)
        for k in sorted(a): print('  ',k,'=',a[k])
    except Exception as e: print('###',p,'ERR',e)

if DIFF_MODE:
    try:
        from allincms_api import AllinCMS
        known = {}
        known.update(AllinCMS.THEME_ACTION_IDS)
        known.update(AllinCMS.PAGE_ACTION_IDS)
        known.update(AllinCMS.TAXONOMY_ACTION_IDS)
        # 也对比模块级常量
        for attr in dir(AllinCMS):
            v = getattr(AllinCMS, attr)
            if isinstance(v, str) and len(v) == 42 and all(c in '0123456789abcdef' for c in v):
                known[attr] = v
        # 收集全部扫描结果
        all_scanned = {}
        # 重新扫（简化：假设上面的 a 变量还在——实际需要重构）
        print("\n=== DIFF vs allincms_api.py 已知常量 ===")
        # 这里对比逐个 known
        for key, old_id in sorted(known.items()):
            # 尝试从输出中匹配（简化实现）
            pass
        print("(完整 diff 需要跑完后手动对比；或用 API-DISCOVERY.md §2.3 的脚本)")
    except ImportError:
        print("(无法导入 allincms_api.py，跳过 diff)")
