#!/usr/bin/env python3
"""索引工具（index/registry_tools.py）—— 三张 TSV 主索引的维护与查询，零依赖跨平台。

原理：TSV 是唯一数据源（机器可 grep/join/脚本消费）；INDEX.md 是本工具自动生成的阅读页（勿手改）。

用法（在 interface-kit/index/ 内或任意位置执行，自动定位）：
  python3 registry_tools.py verify          # 校验：引用存在/id 唯一/枚举合法（上线或收尾必跑）
  python3 registry_tools.py gen             # 由 3 张 TSV 生成 INDEX.md
  python3 registry_tools.py ls [kind]       # 列出（doc/script/template/evidence/canonical/index...）
  python3 registry_tools.py find <关键词>    # 跨三表检索（id/name/description/tags/issues/modules）
  python3 registry_tools.py add <表>        # 交互式追加一行（自动补 id）
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "docs": ("doc-registry.tsv", ["id", "kind", "scope", "name", "path", "status", "scripts", "tags", "description", "when_to_read"]),
    "issues": ("issues.tsv", ["id", "status", "category", "issue", "root_cause", "fix", "avoidance", "doc_refs", "script_refs", "evidence_ref"]),
    "modules": ("modules.tsv", ["type", "group", "builder_fn", "doc_ref", "schema_note", "frontend_display", "status", "evidence_ref"]),
}
STATUS_OK = {"current", "boundary", "pending", "fixed", "verified", "evidence", "legacy"}

def _rows(table):
    fn, cols = FILES[table]
    path = os.path.join(HERE, fn)
    if not os.path.exists(path):
        print(f"MISSING {table} -> {path}"); return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def _resolve(ref):
    """path 统一相对 index/ 目录（../=interface-kit/，../../=任务根，../../../=仓库根）"""
    return os.path.normpath(os.path.join(HERE, ref))

def verify():
    ok = True
    remote_note = []
    for table, (fn, cols) in FILES.items():
        rows = _rows(table)
        ids = [r.get("id") or r.get("type") for r in rows]
        dup = [i for i in set(ids) if ids.count(i) > 1]
        if dup: print(f"FAIL {table}: duplicate ids {dup}"); ok = False
        for r in rows:
            rid = r.get("id") or r.get("type") or "?"
            for c in cols:
                if not (r.get(c) or "").strip(): print(f"FAIL {table} {rid}: empty column {c}"); ok = False
            st = r.get("status", "") or ""
            if st not in STATUS_OK: print(f"FAIL {table} {rid}: bad status {st!r}"); ok = False
            if table == "docs":
                p = (r.get("path") or "").strip()
                if not p: continue
                real = _resolve(p)
                depth = len(p.split("/")) - 1      # ../=1, ../../=2 ... 工具包内引用 ≤2 层必须存在
                if depth <= 2:
                    if not os.path.exists(real):
                        print(f"FAIL docs {rid}: missing file {p}"); ok = False
                elif not os.path.exists(real):
                    remote_note.append((rid, p))
    if remote_note:
        print(f"WARN docs {len(remote_note)} remote refs (client/repo 级引用) 不在本副本上下文：",
              " ".join(rid for rid, _ in remote_note[:6]))
        print("     在权威任务目录（含 70_evidence/<task>/sub-libraries）跑 verify 可覆盖。")
    # 覆盖检查：interface-kit 根 *.md 必须全部登记（防 find 失明；DOC 登记遗漏即 FAIL）
    import glob as _glob
    _registered = set()
    for _t, (_fn, _cols) in FILES.items():
        for _r in _rows(_t):
            _p = (_r.get("path") or "").strip()
            if _p and not _p.startswith("../../"):
                _registered.add(os.path.realpath(_resolve(_p)))  # 全路径比对，防同名 md 挡枪
    _unreg = sorted(os.path.basename(f) for f in _glob.glob(os.path.join(HERE, "..", "*.md"))
                    if os.path.realpath(f) not in _registered)
    if _unreg:
        print(f"FAIL coverage: interface-kit 根 {len(_unreg)} 个 *.md 未登记: {', '.join(_unreg)}"); ok = False
    # 客户标识机器闸（大小写不敏感+词根级；2026-08-30 双审教训：人工清单漏大小写/词根变形两次，grep=0 必须变 FAIL 闸）
    import re as _re
    _ban_src = os.path.join(HERE, "client-ids.local.txt")  # 标识清单不发布（.gitignore），门文件零泄漏
    _ids = [l.strip() for l in open(_ban_src, encoding="utf-8").read().splitlines() if l.strip() and not l.startswith("#")] if os.path.exists(_ban_src) else []
    _BAN = _re.compile("(?i)(" + "|".join(_ids) + ")") if _ids else None
    _scan = []
    for _pat in ["index/*.tsv", "index/INDEX.md", "*.md", "*.py", "templates/*.md", "templates/*.json", "writing/*.md", "scan/*.py"]:
        _scan += _glob.glob(os.path.join(HERE, "..", _pat))
    _hits = []
    for _f in sorted(set(_scan)):
        if os.path.abspath(_f) == os.path.abspath(__file__): continue  # 门自身定义文件豁免
        try: _txt = open(_f, encoding="utf-8", errors="ignore").read()
        except OSError: continue
        if _BAN:
            _m = _BAN.findall(_txt)
            if _m: _hits.append((os.path.relpath(_f, HERE), sorted({x.lower() for x in _m})))
    if _hits:
        for _rel, _ids in _hits: print(f"FAIL client-ids: {_rel} 含客户标识 {_ids}")
        ok = False
    print("VERIFY PASS: 3 tables, refs present, ids unique, statuses valid" if ok else "VERIFY FAIL")
    return 0 if ok else 1

def gen():
    import datetime
    managed = ["title", "type", "status", "owner", "last_updated"]
    # ISS-096：保留 INDEX.md 现存 frontmatter 中非托管字段（description/created/
    # visibility 等），gen 只重写托管键——此前固定 5 键重写会剥掉治理批补的字段。
    # 续行（缩进/列表项/空行）跟随其归属键：属托管键则连键带续行整体丢弃，
    # 属保留键则一并保留；不认识的顶层形态 fail-closed 拒绝再生（ISS-096 对抗审查 P2）。
    preserved = []
    _idx = os.path.join(HERE, "INDEX.md")
    if os.path.exists(_idx):
        with open(_idx, encoding="utf-8") as _f:
            _lines = _f.read().splitlines()
        if _lines and _lines[0].strip() == "---":
            try:
                _end = _lines[1:].index("---") + 1
                _cur_managed = False
                _seen_key = False
                for _ln in _lines[1:_end]:
                    _s = _ln.strip()
                    if not _s:
                        if _seen_key and not _cur_managed: preserved.append(_ln)
                        continue
                    if _s.startswith("#"):
                        preserved.append(_ln); continue
                    if _ln.startswith((" ", "\t")) or _s.startswith("- "):
                        if not _seen_key:
                            print(f"FAIL gen: INDEX.md frontmatter 顶层续行无归属键，拒绝再生：{_ln[:60]}")
                            return 1
                        if not _cur_managed: preserved.append(_ln)
                        continue
                    if ":" not in _ln:
                        print(f"FAIL gen: INDEX.md frontmatter 含不识别形态，拒绝再生（防静默丢字段）：{_ln[:60]}")
                        return 1
                    _k = _ln.split(":", 1)[0].strip()
                    _seen_key = True
                    _cur_managed = _k in managed
                    if not _cur_managed:
                        preserved.append(_ln)
            except ValueError:
                print("FAIL gen: INDEX.md frontmatter 有起始 --- 无闭合 ---，拒绝再生（防静默覆盖损坏文件）")
                return 1
    L = ["---",
         "title: \"AllinCMS 建站知识索引\"",
         "type: \"index\"",
         "status: \"Working\"",
         "owner: \"AI\"",
         "last_updated: \"" + datetime.date.today().isoformat() + "\"",
         *preserved,
         "---",
         "",
         "# AllinCMS 建站知识索引（自动生成，勿手改；数据源=同目录 *.tsv）",
         "",
         f"> 生成时间：{datetime.date.today().isoformat()}｜查询：`python3 registry_tools.py find <词>`｜更新后跑 `verify` + `gen`",
         "",
         "## 1. 文档 / 脚本 / 模板（doc-registry.tsv）", "",
         "| id | kind | name | path | status | 说明 |", "|---|---|---|---|---|---|"]
    for r in _rows("docs"):
        L.append(f"| {r['id']} | {r['kind']} | {r['name']} | `{r['path']}` | {r['status']} | {r['description']} |")
    L += ["", "## 2. 问题 / 教训（issues.tsv）", "",
          "| id | status | category | 问题 | 根因 | 修复 | 规避 | 文档 |", "|---|---|---|---|---|---|---|---|"]
    for r in _rows("issues"):
        L.append(f"| {r['id']} | {r['status']} | {r['category']} | {r['issue']} | {r['root_cause']} | {r['fix']} | {r['avoidance']} | {r['doc_refs']} |")
    L += ["", "## 3. 模块库（modules.tsv）", "",
          "| type | group | builder_fn | schema_note | 前端显示 | status |", "|---|---|---|---|---|---|"]
    for r in _rows("modules"):
        L.append(f"| {r['type']} | {r['group']} | `{r['builder_fn']}` | {r['schema_note']} | {r['frontend_display']} | {r['status']} |")
    L += ["", "## 4. 维护规则", "",
          "- 新增文档/脚本/模板 → 在 doc-registry.tsv 加行后 `verify` + `gen`（id 按 DOC-/SCRIPT-/TPL-/EV-/CAN-/IDX- 递增）",
          "- 新问题排除后 → issues.tsv 加行（状态 fixed/boundary/pending）",
          "- 新模块摸清后 → modules.tsv 加行",
          "- TSV 字段含 tab 的文本（如多行）先替换为空格；description 精炼一行"]
    out = os.path.join(HERE, "INDEX.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"generated {out} ({len(L)} lines)")

def ls(kind=None):
    for table in FILES:
        for r in _rows(table):
            k = r.get("kind") or "module"
            if kind and k != kind and table != "modules": continue
            print(f"{r.get('id') or r.get('type'):10s} [{k:8s}] {r.get('name') or r.get('issue', '')[:60]}")

def find(kw):
    kw = kw.lower(); hits = 0
    for table, (fn, cols) in FILES.items():
        for r in _rows(table):
            hay = " ".join((r.get(c) or "") for c in cols if c != "path").lower()
            if kw in hay:
                label = (r.get("name") or r.get("type") or r.get("category") or (r.get("issue") or "")[:40])
                desc = (r.get("description") or r.get("issue") or r.get("schema_note") or "")
                print(f"[{table}] {r.get('id') or r.get('type')} | {label} | {desc[:90]}")
                hits += 1
    print(f"find '{kw}': {hits} hit(s)" if hits else f"find '{kw}': 0 hits")

def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "help"
    if cmd == "verify": sys.exit(verify())
    if cmd == "gen": sys.exit(gen())  # ISS-096：fail-closed 退出码必须传给 CI/调用方
    if cmd == "ls": ls(args[1] if len(args) > 1 else None); return
    if cmd == "find": find(args[1]); return
    if cmd == "wiki": wiki(args); return
    print(__doc__)

def wiki(args):
    """wiki <client-registry.tsv 路径> [关键词] —— 客户知识索引查询（任意 TSV 通用查询）。
    例：python3 registry_tools.py wiki ../../<client-task>/20_wiki/client-registry.tsv 痛点"""
    path = args[1] if len(args) > 1 else ""
    if not path or not os.path.exists(path):
        print("用法：wiki <path>/client-registry.tsv [关键词]；文件需存在"); return
    kw = args[2].lower() if len(args) > 2 else ""
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().rstrip("\n").split("\n") if ln.strip()]
    if not lines: print("empty tsv"); return
    cols = lines[0].split("\t")
    for ln in lines[1:]:
        cells = ln.split("\t") + [""] * (len(cols) - len(ln.split("\t")))
        row = dict(zip(cols, cells))
        hay = " ".join(cells).lower()
        if not kw or kw in hay:
            print(f"[{row.get('id','?'):8s}] {row.get('page',''):24s} {row.get('path',''):22s} {row.get('status',''):8s} {row.get('description','')[:66]}")
    print(f"rows={len(lines)-1} filter='{kw}'")

if __name__ == "__main__":
    main()
