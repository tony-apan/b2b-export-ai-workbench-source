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
        print("     在权威任务目录（含 70_evidence/river-trail/sub-libraries）跑 verify 可覆盖。")
    print("VERIFY PASS: 3 tables, refs present, ids unique, statuses valid" if ok else "VERIFY FAIL")
    return 0 if ok else 1

def gen():
    import datetime
    L = ["# AllinCMS 建站知识索引（自动生成，勿手改；数据源=同目录 *.tsv）",
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
    if cmd == "gen": gen(); return
    if cmd == "ls": ls(args[1] if len(args) > 1 else None); return
    if cmd == "find": find(args[1]); return
    if cmd == "wiki": wiki(args); return
    print(__doc__)

def wiki(args):
    """wiki <client-registry.tsv 路径> [关键词] —— 客户知识索引查询（任意 TSV 通用查询）。
    例：python3 registry_tools.py wiki ../../river-trail/20_wiki/client-registry.tsv 痛点"""
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
