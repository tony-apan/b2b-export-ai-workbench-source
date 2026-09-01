#!/usr/bin/env python3
"""写作模块调用器（writing-module.py）—— 独立可调用，零依赖。
子命令：
  outline <article.json>   : 校验并输出六段式骨架（阶段标注/钩子提示/渐进层级），补足缺阶段提示
  check   <article.json>   : 渐进+格式检查（6 项：阶段/承上启下/术语/边界/CTA/h2 语义标题+Markdown/单位/emoji 禁用自检；缺S1/S4=⚠️软提示）
  skeleton <brief.json>    : brief → 六段式骨架（h2+空段+QUICK ANSWER/PHOTO CREDIT/EDITORIAL NOTE）
  block   <type> <text>    : 生成原生块（h2/h3/para/spacer/quote，带 id）
  migrate <article.json>   : 旧格式(paragraph+bold 标签)→原生 h2/blockquote；输出未识别标签报告
  输入格式：{"title":"...","content":[{"type":"h2|h3|p|blockquote","children":[{"text":"...","bold":true}|...]}]}
  类型词法（2026-08-30 与服务器存储形态统一）：原生 Slate 类型 = p|h2|h3|blockquote（服务器存的就是这些）；旧词法 paragraph/heading 仅作输入兼容，输出一律原生 p/h2/blockquote。
"""
import json, random, re, string, sys

# 更新优先：先查已发布 slug resolve create/update；独立审查最终全字段 payload 后走 mutate_reviewed_post（勿裸 create，否则产生 Untitled 草稿/绕过门）


STAGES = [
    ("S1 认识", ["saturday", "07:00", "borrowed hull", "borrowed narrow hull", "damp", "if that sounds", "you could not read",
                  "fourteen days of lakes", "one hull that still looks new", "two paddlers, one weekend",
                  "a borrowed", "one borrowed", "borrow what the lake"]),
    ("S2 理解", ["mistake", "not by itself", "but", "trade-off", "usually", "common", "because"]),
    ("S3 判断", ["first, the length", "second, the beam", "third, the load", "check", "calculation", "rating", "reference"]),
    ("S4 决定", ["which end is yours", "before you buy", "short version", "ready to", "recommendation", "our catalogue", "share", "trip plan", "message us", "then what", "next step", "get help", "ask a question", "start a conversation"]),
]
LINK_DOWN = ["so the first question", "the trade-off", "but", "the common mistake", "it is also where", "so the check is simple", "these three", "this guide", "that means", "that is why", "now", "then", "and that"]
LINK_UP = ["what is worse", "then", "which end", "now", "so", "not by itself", "why", "how to", "ready to", "before you buy", "to decide", "next"]
BOUNDARY = ["calm lakes", "gentle rivers", "not a substitute", "manufacturer", "local conditions", "reference", "not universal"]
CTA_MARK = ["ready to", "recommendation", "trip plan", "catalogue", "message us", "get a"]
JARGON = {"beam": "船宽", "tracking": "直线循迹", "rock": "摇摆", "hatch": "舱口", "load capacity": "载重", "rocker": "船底弧度", "skeg": "船尾鳍"}

def texts(content):
    out = []
    for b in content:
        if not isinstance(b, dict): continue
        t = "".join(ch.get("text", "") for ch in b.get("children", []) if isinstance(ch, dict))
        out.append((b.get("type", ""), t.lower().strip()))
    return out

def find_stage(blk, idx):
    txt = blk[1]
    for s, keys in STAGES:
        if any(k in txt for k in keys): return s
    return "?"

def semantic_blocks(content):
    """过滤空段/标签段（分隔空段、全大写标签、01/02/03 编号行），只留承载内容的语义段"""
    out = []
    for b in content:
        if not isinstance(b, dict): continue
        t = "".join(ch.get("text", "") for ch in b.get("children", []) if isinstance(ch, dict)).strip().lower()
        if not t: continue
        if re.fullmatch(r"[a-z][a-z '\-\.]+", t) and len(t) < 40 and t.upper() == t: continue
        if re.match(r"^(01|02|03|\\d+\\.)\s", t): continue
        if len(t) < 15: continue
        out.append((b.get("type", ""), t))
    return out

def check(content):
    issues = []
    blocks = semantic_blocks(content)
    if not blocks: return ["无语义段（空/标签）/无法检查"]
    stages_seen = [find_stage(b, i) for i, b in enumerate(blocks)]
    order = {"S1 认识": 1, "S2 理解": 2, "S3 判断": 3, "S4 决定": 4}
    seen = [order.get(s, 0) for s in stages_seen if s in order]
    out = []
    # S1/S4 缺失为软提示（Quick Answer 前置允许场景后置；机器只提示，硬判定走 ghostwriter+human）
    if 1 not in seen: out.append("⚠️ 未识别到 S1 场景段（若是'先答案后故事'结构可接受；否则建议补代入场景）")
    if 4 not in seen: out.append("⚠️ 未识别到 S4 行动/CTA 段（确认结尾有下一步行动）")
    if seen != sorted(seen) and len(set(seen)) > 1:
        out.append(f"⚠️ 阶段顺序检测有波动 {stages_seen}（Quick Answer 前置属正常；确认其余顺序渐进）")
    misses = 0
    ANY_LINK = ("these", "so", "but", "this", "that", "now", "then", "which", "it is", "they", "such", "the result")
    for i, (typ, txt) in enumerate(blocks):
        if not any(k in txt for k in ANY_LINK): misses += 1
    if misses > max(2, len(blocks)//3):
        out.append(f"⚠️ 承上启下偏弱（{misses}/{len(blocks)} 段未显式衔接）：建议每段首/末句加指示承接（these/so/but/this 等）")
    for j, k in JARGON.items():
        idxs = [i for i, (t, x) in enumerate(blocks) if j in x]
        if idxs and idxs[0] == 0: out.append(f"⚠️ 术语 '{j}' 首段即用，建议先解释（{k}）")
    for i, (typ, txt) in enumerate(blocks):
        if "open water" in txt and "not a substitute" not in txt:
            out.append(f"⚠️ 段{i} open water 建议未带边界声明"); break
    first_cta = next((i for i, (t, x) in enumerate(blocks) if any(k in x for k in CTA_MARK)), None)
    if first_cta is not None and first_cta < 3: out.append(f"⚠️ CTA 时机偏早（段{first_cta}）")
    # 禁用项自检：Markdown/单位/emoji
    for i, (typ, x) in enumerate(blocks):
        if "]( " in x or "**" in x or x.strip().startswith("# "): out.append(f"⚠️ 段{i} 疑似 Markdown 残留"); break
        if re.search(r"\b(5\.2m|68cm|220kg|80kg)\b", x): out.append(f"⚠️ 段{i} 单位未加空格"); break
        if re.search(r"[\U0001F300-\U0001FAFF]", x): out.append(f"⚠️ 段{i} 含 emoji（禁用）"); break
    # h2 语义标题（h3-only 提示）
    h2s = [b for b in content if isinstance(b, dict) and b.get("type") == "h2"]
    h3only = [b for b in content if isinstance(b, dict) and b.get("type") == "h3"]
    if not h2s and not h3only: out.append("⚠️ 正文无语义标题（h2/h3）——建议用原生 h2 类型（NOT heading）标记章节")
    elif not h2s and h3only: out.append("⚠️ 只有 h3 无 h2——建议章节主标题用 h2（h3 作子分节）")
    return out or [f"✓ 渐进检查通过（{len(blocks)} 语义段；阶段/衔接/术语/边界/CTA 均达标）"]

def outline(post):
    blocks = texts(post.get("content", []))
    lines = [f"# {post.get('title','')}"]
    for i, (typ, txt) in enumerate(blocks):
        if not txt: lines.append("  — 空段(分隔) —"); continue
        stage = find_stage((typ, txt), i)
        lines.append(f"[{stage}] {typ}: {txt[:70]}")
    lines.append("")
    lines.append("渐进提示：确认四阶段顺序 S1→S2→S3→S4；每段首句承上、末句启下；CTA 放 S4。")
    return "\n".join(lines)


# ---------- 格式构建器（FORMAT-SPEC.md 单一真源；生成带 id 的原生块） ----------
def bid():
    return "".join(random.choices(string.ascii_letters + string.digits, k=10))
def h2(text):   return {"type": "h2", "children": [{"text": text}], "id": bid()}
def h3(text):   return {"type": "h3", "children": [{"text": text}], "id": bid()}
def para(text): return {"type": "p", "children": [{"text": text}], "id": bid()}
def leaf(text, bold=False, italic=False, underline=False):
    m = {"text": text}
    if bold: m["bold"] = True
    if italic: m["italic"] = True
    if underline: m["underline"] = True
    return m
def para_parts(parts):  # parts:[(text,bold,italic,underline)...]
    return {"type": "p", "children": [leaf(*pp) if isinstance(pp, tuple) else pp for pp in parts], "id": bid()}
def spacer(): return {"type": "p", "children": [{"text": ""}], "id": bid()}
def blockquote(text):
    return {"children": [{"type": "p", "children": [{"text": text}], "id": bid()}], "type": "blockquote", "id": bid()}
def sep(blocks):
    out = []
    for b in blocks: out.append(b); out.append(spacer())
    return out
# ---------- 迁移：旧格式(paragraph+bold 标签) -> 原生 h2；扁平 blockquote 补包裹 ----------
MIGRATE_LABELS = ["QUICK ANSWER", "01 LENGTH", "02 BEAM", "03 LOAD", "FIELD NOTE", "WHICH END IS YOURS?",
                  "BEFORE YOU BUY", "THE SHORT VERSION", "PHOTO CREDIT", "EDITORIAL NOTE", "01 HULL",
                  "02 HATCH", "03 STORAGE", "WHY IT MATTERS", "THE THREE QUESTIONS", "WHY STABLE FIRST",
                  "THE TRADE-OFF", "CHOOSE BY WATER", "WHY A LONGER TANDEM HULL", "STABILITY VERSUS SPEED",
                  "CALCULATE THE TOTAL", "THE CHECK PEOPLE FORGET", "HOW TO STORE BETWEEN TRIPS",
                  "THE FIRST-TRIP METRIC", "WHAT A WIDER BEAM COSTS", "THEN WHAT?"]
def _is_label(text):
    t = re.sub(r"\s+", " ", text.strip().upper())
    for l in MIGRATE_LABELS:
        l_n = re.sub(r"\s+", " ", l.upper())
        if t == l_n or (t.startswith(l_n) and len(t) - len(l_n) < 30): return True
    return False
def migrate(content):
    out = []
    for b in content:
        if not isinstance(b, dict): continue
        children = b.get("children", [])
        full = "".join(ch.get("text", "") for ch in children if isinstance(ch, dict))
        typ = b.get("type", "")
        is_p = typ in ("paragraph", "p")
        if is_p and _is_label(full):
            out.append(h2(full.strip())); continue
        if is_p and children and isinstance(children[0], dict) and children[0].get("bold"):
            first = children[0].get("text", "").strip()
            rest = [c for c in children[1:] if isinstance(c, dict) and c.get("text", "").strip()]
            if _is_label(first):
                out.append(h2(first))
                for ch in rest: out.append(para(ch["text"]))
                continue
        if typ == "blockquote" and children and children[0].get("type") not in ("paragraph", "p"):
            out.append(blockquote(full)); continue
        b.setdefault("id", bid()); out.append(b)
    return out

def migrate_report(content):
    """返回【migrate 未能转换】的 bold 标签段（_is_label 未命中），防静默漏转"""
    leftovers = []
    for b in content:
        if not isinstance(b, dict) or b.get("type") not in ("paragraph", "p"): continue
        ch = b.get("children", [])
        first = ch[0] if ch else {}
        if isinstance(first, dict) and first.get("bold") and not _is_label(first.get("text", "")):
            leftovers.append(first.get("text", "")[:40])
    return leftovers


def skeleton(brief):
    """brief → 六段式骨架 content（h2 章节 + 空段 + quote 可用位 + credit/editorial 尾巴）。
    brief 可选键：qa(Quick Answer 3 行), stages[{title,points[]}], credit, editorial"""
    blocks = []
    def add(b): blocks.append(b); blocks.append(spacer())
    if brief.get("qa"): add(h2("QUICK ANSWER")); add(para_parts([(brief["qa"], True)]))
    for st in brief.get("stages", []):
        add(h2(st.get("title", "")))
        for pt in st.get("points", []):
            add(para_parts([(pt, True)])) if st.get("lead") and pt == st["points"][0] else add(para(pt))
    add(h2("THE SHORT VERSION"))
    add(para_parts([(brief.get("summary", "Choose by where you paddle, what you carry, and how often both paddlers go. This product is a reference, not a universal answer."), True)]))
    if brief.get("credit"): add(h2("PHOTO CREDIT")); add(para(brief["credit"]))
    add(h2("EDITORIAL NOTE"))
    add(para(brief.get("editorial", "Written by Demo Product Team. Reviewed against the product specification sheet. Last updated: 2026-08-29.")))
    return blocks

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("help", "-h", "--help") or len(args) < 2:
        print(__doc__); return
    cmd, path = args[0], args[1]
    if cmd == "block":
        bt = args[1] if len(args) > 1 else "h2"
        txt = args[2] if len(args) > 2 else ""
        fn = {"h2": h2, "h3": h3, "para": para, "spacer": spacer, "quote": blockquote}.get(bt)
        if fn is None: print("unknown block:", bt, "| 支持 h2/h3/para/spacer/quote"); return
        print(json.dumps(fn(txt) if bt != "spacer" else fn(), ensure_ascii=False, indent=1))
        return
    data = json.load(open(path, encoding="utf-8"))
    if cmd == "outline":
        print(outline(data))
    elif cmd == "check":
        issues = check(data.get("content", []))
        for issue in issues:
            print(issue)
        # 有 ❌ 硬失败 → 退出码 1；仅 ⚠️ 提示 → 退出码 0（提示级）
        if any(i.startswith("\u274c") for i in issues): sys.exit(1)
    elif cmd == "migrate":
        # python3 writing-module.py migrate <article.json>  -> 输出迁移后的 content 到 stdout(或另存)
        content = data.get("content", [])
        mc = migrate(content)
        print(json.dumps(mc, ensure_ascii=False, indent=1))
        print(f"# 迁移完成 {sum(1 for x in mc if x.get('type')=='h2')} 个 h2", file=sys.stderr)
        lv = migrate_report(content)
        if lv: print(f"# ⚠️ 未识别 bold 标签段 {len(lv)} 个（需人工核对）: {lv[:3]}", file=sys.stderr)
    elif cmd == "skeleton":
        # python3 writing-module.py skeleton <brief.json>  -> 六段式骨架（h2+空段+quote/credit/editorial）
        print(json.dumps(skeleton(data), ensure_ascii=False, indent=1))
    else:
        print("unknown:", cmd, "| 支持 outline / check")

if __name__ == "__main__":
    main()
