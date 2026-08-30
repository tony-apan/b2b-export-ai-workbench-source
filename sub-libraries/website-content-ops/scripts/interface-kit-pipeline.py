#!/usr/bin/env python3
"""interface-kit 真源管线（id-0073）：runtime(权威) ⇄ tracked(SHA 锚) ⇄ dist(分发)。

真源方向（2026-08-30 三轮对抗审查修正版）：
    runtime 编辑 → pull-to-tracked(回流, fail-closed) → git commit(SHA 锚)
    → build-dist(从 git committed 字节构建) → sync-runtime(消费, 前置守卫防覆盖)

用法：
  python3 interface-kit-pipeline.py status                 # 三层状态与漂移
  python3 interface-kit-pipeline.py pull-to-tracked [--confirm]   # 回流（有漂移须 --confirm）
  python3 interface-kit-pipeline.py anchor                 # 记录当前 HEAD 为同步锚
  python3 interface-kit-pipeline.py build-dist             # 从 committed 字节构建 dist
  python3 interface-kit-pipeline.py sync-runtime [--confirm]      # runtime 消费 dist
  python3 interface-kit-pipeline.py check                  # stale 守卫（阈值告警）
  python3 interface-kit-pipeline.py selftest               # 临时目录三场景自测

铁律：
  - build-dist 只读 git committed 字节（绝不读脏工作树）；
  - sync-runtime 前置守卫：runtime 存在未回流改动即中止（无 git 保护的权威副本不可被覆盖）；
  - 本地专用文件（client-ids.local.txt/__pycache__/*.pyc/.DS_Store）永不入 manifest、永不同步。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WCO_ROOT = os.path.dirname(HERE)
MOTHER = os.path.dirname(os.path.dirname(WCO_ROOT))
TRACKED = os.path.join(WCO_ROOT, "TOOLS", "interface-kit")
DIST = os.path.join(WCO_ROOT, "dist", "latest", "interface-kit")
RUNTIME_DEFAULT = os.path.join(
    os.path.dirname(MOTHER), "701_runtime", "00_shared", "interface-kit")
RUNTIME = os.environ.get("IFK_RUNTIME_ROOT", RUNTIME_DEFAULT)
SYNC_MANIFEST = os.path.join(RUNTIME, ".sync-manifest.json")
DIST_MANIFEST = os.path.join(DIST, "PIPELINE-MANIFEST.json")
TRACKED_REL = "sub-libraries/website-content-ops/TOOLS/interface-kit"

EXCLUDE_NAMES = {"__pycache__", ".DS_Store", "client-ids.local.txt",
                 ".sync-manifest.json", "PIPELINE-MANIFEST.json"}
EXCLUDE_SUFFIX = (".pyc", ".pyo")

STALE_DAYS_WARN = 7
STALE_COMMITS_WARN = 10


def _excluded(name):
    return name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIX)


def tree_hashes(root):
    """返回 {相对路径: sha256}；空目录不入表；排除本地专用文件。"""
    out = {}
    if not os.path.isdir(root):
        return out
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _excluded(d)]
        for f in files:
            if _excluded(f):
                continue
            p = os.path.join(base, f)
            rel = os.path.relpath(p, root)
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            out[rel] = h.hexdigest()
    return out


def git(*args, cwd=MOTHER, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} 失败: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def load_json(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)


def drift(base, cur):
    """返回 (新增, 修改, 删除) 三个相对路径列表。"""
    add = sorted(k for k in cur if k not in base)
    mod = sorted(k for k in cur if k in base and cur[k] != base[k])
    dele = sorted(k for k in base if k not in cur)
    return add, mod, dele


def anchor_commit():
    """tracked 子树最新 commit（无改动时等于 HEAD 对该子树的锚）。"""
    return git("log", "-1", "--format=%H", "--", TRACKED_REL)


def _require_runtime():
    if not os.path.isdir(RUNTIME):
        print(f"FAIL: runtime 根不存在: {RUNTIME}（检查 IFK_RUNTIME_ROOT / 软链）——拒绝执行，防误判全树删除")
        return False
    return True


def cmd_status(args):
    if not _require_runtime(): return 1

    rt, tr = tree_hashes(RUNTIME), tree_hashes(TRACKED)
    m = load_json(SYNC_MANIFEST)
    dm = load_json(DIST_MANIFEST)
    print(f"runtime: {len(rt)} 文件  tracked: {len(tr)} 文件")
    a, b, c = drift(tr, rt)
    same_runtime_tracked = not (a or b or c)
    print(f"runtime vs tracked: {'一致 ✓' if same_runtime_tracked else f'漂移 +{len(a)} ~{len(b)} -{len(c)}'}")
    if a[:5]: print("  runtime 新增:", *a[:5], sep="\n    ")
    if b[:5]: print("  runtime 修改:", *b[:5], sep="\n    ")
    if c[:5]: print("  runtime 删除:", *c[:5], sep="\n    ")
    if m:
        print(f"sync-manifest: anchor={m.get('anchor_commit','?')[:12]} at {m.get('anchored_at','?')}")
    else:
        print("sync-manifest: 无（首次运行 pull-to-tracked 建基线）")
    if dm:
        behind = commits_behind(dm.get("source_commit", ""))
        print(f"dist: source={dm.get('source_commit','?')[:12]} built={dm.get('built_at','?')} 落后 HEAD {behind} commit")
    else:
        print("dist: 无 PIPELINE-MANIFEST（未构建）")
    return 0


def commits_behind(sha):
    if not sha:
        return -1
    r = git("rev-list", "--count", f"{sha}..HEAD", "--", TRACKED_REL, check=False)
    try:
        return int(r)
    except ValueError:
        return -1


def cmd_pull(args):
    if not _require_runtime(): return 1
    rt, tr = tree_hashes(RUNTIME), tree_hashes(TRACKED)
    m = load_json(SYNC_MANIFEST)
    add, mod, dele = drift(tr, rt)
    if not (add or mod or dele):
        print("runtime 与 tracked 一致，无需回流")
        if not m:
            _write_manifest(rt, note="首次基线（双向一致）")
        return 0
    print(f"回流差异: 新增 {len(add)} / 修改 {len(mod)} / 删除 {len(dele)}")
    for k in (add + mod + dele)[:20]:
        print("   ", k)
    if len(add + mod + dele) > 20:
        print(f"    ... 共 {len(add + mod + dele)} 个")
    m = load_json(SYNC_MANIFEST)
    base = (m or {}).get("files")
    if base:
        tracked_side = [k for k in set(add) | set(mod) | set(dele)
                        if tr.get(k) != base.get(k)]
        if tracked_side:
            print(f"FAIL(方向守卫): {len(tracked_side)} 个差异源于 tracked 侧相对基线的改动，回流会覆盖丢失它们；")
            print("      先在 tracked 侧 git checkout（弃）或 commit（保）处理：")
            for k in tracked_side[:15]:
                print("        ", k)
            return 1
    # 回流内容级去敏闸：与 verify client-ids 同源（client-ids.local.txt 不发布）
    _ids_path = os.path.join(WCO_ROOT, "TOOLS", "interface-kit", "index", "client-ids.local.txt")
    _ids = [l.strip() for l in open(_ids_path, encoding="utf-8").read().splitlines()
            if l.strip() and not l.startswith("#")] if os.path.exists(_ids_path) else []
    if _ids:
        import re as _re
        _ban = _re.compile("(?i)(" + "|".join(_ids) + ")")
        _dirty = []
        for k in add + mod:
            try:
                _txt = open(os.path.join(RUNTIME, k), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if _ban.findall(_txt):
                _dirty.append(k)
        if _dirty:
            print(f"FAIL(回流去敏闸): 以下文件含客户标识，禁止写入 tracked（先去敏再回流）：")
            for k in _dirty[:15]:
                print("        ", k)
            return 1
    if not args.confirm:
        print("FAIL(fail-closed): 上述 runtime 改动尚未回流。确认后加 --confirm 执行；")
        print("      回流后必须 git commit tracked 子树，再运行 anchor 记录 SHA 锚。")
        return 1
    for k in add + mod:
        src, dst = os.path.join(RUNTIME, k), os.path.join(TRACKED, k)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    for k in dele:
        p = os.path.join(TRACKED, k)
        if os.path.exists(p):
            os.remove(p)
    _write_manifest(tree_hashes(RUNTIME), note="回流后待 commit+anchor")
    print(f"已回流 {len(add)+len(mod)} 个改动、{len(dele)} 个删除 → tracked")
    print("下一步: git commit 该子树 → python3 interface-kit-pipeline.py anchor")
    return 0


def _write_manifest(rt_hashes, note=""):
    save_json(SYNC_MANIFEST, {
        "anchor_commit": anchor_commit(),
        "anchored_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "file_count": len(rt_hashes),
        "files": rt_hashes,
        "tree_digest": hashlib.sha256(
            json.dumps(rt_hashes, sort_keys=True).encode()).hexdigest(),
        "note": note,
    })


def cmd_anchor(args):
    dirty = git("status", "--porcelain", "--", TRACKED_REL)
    if dirty:
        print("FAIL: tracked 子树有未提交改动，先 commit 再 anchor：")
        print(dirty[:500])
        return 1
    rt = tree_hashes(RUNTIME)
    a, b, c = drift(tree_hashes(TRACKED), rt)
    if a or b or c:
        print(f"FAIL: runtime ≠ tracked（+{len(a)} ~{len(b)} -{len(c)}）——漂移状态禁止 anchor，")
        print("      先 pull-to-tracked 回流并 commit，或处理 runtime 侧差异。")
        return 1
    _write_manifest(rt, note="anchor（tracked 已 commit，runtime==tracked）")
    print(f"锚已记录: {anchor_commit()[:12]} @ {time.strftime('%Y-%m-%d %H:%M')}")
    return 0


def cmd_build_dist(args):
    head = git("rev-parse", "HEAD")
    tmp = tempfile.mkdtemp(prefix="ifk-dist-")
    try:
        archive = os.path.join(tmp, "src.tar")
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", f"HEAD:{TRACKED_REL}"],
                           cwd=MOTHER, stdout=f, check=True)
        out = os.path.join(tmp, "out")
        os.makedirs(out)
        subprocess.run(["tar", "-xf", archive, "-C", out], check=True)
        hashes = {}
        for base, dirs, files in os.walk(out):
            dirs[:] = [d for d in dirs if not _excluded(d)]
            for fn in files:
                if _excluded(fn):
                    continue
                p = os.path.join(base, fn)
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                hashes[os.path.relpath(p, out)] = h
        manifest = {
            "source_commit": head,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "file_count": len(hashes),
            "files": hashes,
        }
        manifest["bundle_digest"] = hashlib.sha256(
            json.dumps(manifest["files"], sort_keys=True).encode()).hexdigest()
        # 替换 dist（rmtree+move 非原子；构建失败可重跑；依赖外部 tar，裸 Windows 无 tar 时失败）
        if os.path.isdir(DIST):
            shutil.rmtree(DIST)
        os.makedirs(os.path.dirname(DIST), exist_ok=True)
        shutil.move(out, DIST)
        save_json(os.path.join(DIST, "PIPELINE-MANIFEST.json"), manifest)
        print(f"dist 已构建: {len(hashes)} 文件, source={head[:12]}, digest={manifest['bundle_digest'][:16]}…")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_sync_runtime(args):
    dm = load_json(DIST_MANIFEST)
    if not dm:
        print("FAIL: 无 dist PIPELINE-MANIFEST，先 build-dist")
        return 1
    m = load_json(SYNC_MANIFEST)
    if m is None:
        print("FAIL(fail-closed): 无 sync-manifest（基线缺失或被删）——守卫拒绝在无基线下同步，")
        print("      防止绕过未回流改动检查。先运行 pull-to-tracked（runtime==tracked 时自动重建基线），")
        print("      若 runtime 有改动则先回流并 commit，再 sync-runtime。")
        return 1
    rt = tree_hashes(RUNTIME)
    add, mod, dele = drift(m.get("files", {}), rt)
    if add or mod or dele:
        print("FAIL(fail-closed): runtime 存在未回流改动（相对 sync-manifest 基线），")
        print(f"      新增 {len(add)} / 修改 {len(mod)} / 删除 {len(dele)}；先 pull-to-tracked 回流并 commit：")
        for k in (add + mod + dele)[:10]:
            print("        ", k)
        return 1
    dist_hashes = dm.get("files", {})
    add, mod, dele = drift(rt, dist_hashes)
    if not (add or mod or dele):
        print(f"runtime 已等于 dist(source={dm['source_commit'][:12]}) ✓")
        return 0
    print(f"将同步 dist→runtime: +{len(add)} ~{len(mod)} -{len(dele)}")
    if not args.confirm:
        print("确认后加 --confirm")
        return 1
    for k in add + mod:
        src, dst = os.path.join(DIST, k), os.path.join(RUNTIME, k)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    for k in dele:
        p = os.path.join(RUNTIME, k)
        if os.path.exists(p):
            os.remove(p)
    _write_manifest(tree_hashes(RUNTIME), note=f"消费 dist {dm['source_commit'][:12]}")
    print(f"runtime 已更新到 dist(source={dm['source_commit'][:12]})")
    return 0


def cmd_install(args):
    """把 dist 安装到目标目录（自用轻量安装；不做公开可安装宣称——source-only 边界）。"""
    dm = load_json(DIST_MANIFEST)
    if not dm:
        print("FAIL: 无 dist PIPELINE-MANIFEST，先 build-dist")
        return 1
    target = os.path.abspath(os.path.expanduser(args.target))
    if os.path.isdir(target) and os.listdir(target) and not args.force:
        print(f"FAIL: 目标目录非空: {target}（清空后重试，或 --force 覆盖安装）")
        return 1
    os.makedirs(target, exist_ok=True)
    files = dm.get("files", {})
    # 路径键防护：manifest 是 dist 内自证文件——拒绝越界键（../、绝对路径），防污染 manifest 越目标写
    bad_keys = [k for k in files if k.startswith("/") or ".." in k.split(os.sep) or ".." in k.split("/")]
    if bad_keys:
        print(f"FAIL: PIPELINE-MANIFEST 含越界路径键（dist 可能被污染）: {bad_keys[:5]}")
        return 1
    for rel, want in files.items():
        src = os.path.join(DIST, rel)
        dst = os.path.join(target, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except shutil.SameFileError:
            print(f"FAIL: 目标即 dist 自身（{target}），拒绝自毁式安装")
            return 1
        got = hashlib.sha256(open(dst, "rb").read()).hexdigest()
        if got != want:
            print(f"FAIL: 安装校验失败 {rel}（sha256 不匹配）")
            return 1
    print(f"安装完成: {len(files)} 文件 -> {target}")
    print(f"来源: dist source={dm['source_commit'][:12]} digest={dm['bundle_digest'][:16]}...（逐文件 sha256 已校验）")
    print("入口: README.md -> NEW-SITE-ONEPASS.md（13 步建站）；凭据用 export WS_TOKEN=<token>")
    print("边界: 本安装为自用轻量分发（source-only），不构成 Public Preview/Release 宣称；升级=重跑 install --force")
    if os.path.isdir(target):
        import glob as _g
        _known = set(files)
        _stale = [f for f in _g.glob(os.path.join(target, "**", "*"), recursive=True)
                  if os.path.isfile(f) and os.path.relpath(f, target) not in _known
                  and not any(x in f for x in ("__pycache__", ".DS_Store"))]
        if _stale:
            print(f"提示: 目标存在 {len(_stale)} 个 manifest 外旧文件（升级残留，未删除）：", *[os.path.relpath(f, target) for f in _stale[:5]])
    return 0


def cmd_check(args):
    dm = load_json(DIST_MANIFEST)
    problems = []
    if not dm:
        print("FAIL: dist 未构建（无 PIPELINE-MANIFEST）——id-0073 DoD② 未满足")
        problems.append("no-dist")
    else:
        behind = commits_behind(dm.get("source_commit", ""))
        age_days = (time.time() - time.mktime(time.strptime(
            dm.get("built_at", "1970-01-01T00:00:00"), "%Y-%m-%dT%H:%M:%S"))) / 86400
        print(f"dist: 落后 HEAD {behind} commit, 构建 {age_days:.1f} 天前")
        if behind > STALE_COMMITS_WARN or age_days > STALE_DAYS_WARN:
            print(f"WARN(stale): 超阈值（>{STALE_COMMITS_WARN} commit 或 >{STALE_DAYS_WARN} 天）→ 建议 build-dist")
            problems.append("stale")
    rt, tr = tree_hashes(RUNTIME), tree_hashes(TRACKED)
    a, b, c = drift(tr, rt)
    if a or b or c:
        print(f"WARN(drift): runtime 相对 tracked +{len(a)} ~{len(b)} -{len(c)} 未回流")
        problems.append("drift")
    else:
        print("runtime == tracked ✓")
    verdict = "PASS" if not problems else ("FAIL " if "no-dist" in problems else "WARN ") + ",".join(problems)
    print("CHECK:", verdict)
    return 0 if not problems else 2


def cmd_selftest(args):
    """临时目录模拟三层：场景=干净 no-op / 漂移 fail-closed / dist 消费守卫。"""
    global RUNTIME, TRACKED, DIST, SYNC_MANIFEST, DIST_MANIFEST
    tmp = tempfile.mkdtemp(prefix="ifk-selftest-")
    o_r, o_t, o_d, o_sm, o_dm = RUNTIME, TRACKED, DIST, SYNC_MANIFEST, DIST_MANIFEST
    try:
        RUNTIME, TRACKED, DIST = (os.path.join(tmp, "rt"), os.path.join(tmp, "tr"), os.path.join(tmp, "dist"))
        SYNC_MANIFEST, DIST_MANIFEST = os.path.join(RUNTIME, ".sync-manifest.json"), os.path.join(DIST, "PIPELINE-MANIFEST.json")
        for d in (RUNTIME, TRACKED):
            os.makedirs(os.path.join(d, "sub"), exist_ok=True)
            open(os.path.join(d, "a.py"), "w").write("print(1)\n")
            open(os.path.join(d, "sub", "b.md"), "w").write("# b\n")
        ok = []
        # 场景1: 一致 → pull 无需回流并建基线
        ok.append(("baseline", cmd_pull(argparse.Namespace(confirm=False)) == 0))
        # 场景2: runtime 漂移 → 无 --confirm 必须 FAIL
        open(os.path.join(RUNTIME, "a.py"), "w").write("print(2)\n")
        ok.append(("drift-blocked", cmd_pull(argparse.Namespace(confirm=False)) == 1))
        # 场景3: --confirm 回流成功且 tracked 更新
        ok.append(("drift-confirm", cmd_pull(argparse.Namespace(confirm=True)) == 0
                   and open(os.path.join(TRACKED, "a.py")).read() == "print(2)\n"))
        # 场景4: dist 消费——runtime 再漂移后 sync 必须中止
        save_json(DIST_MANIFEST, {"source_commit": "x" * 40, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                  "files": {"a.py": "deadbeef", "sub/b.md": "deadbeef"}, "file_count": 2})
        open(os.path.join(RUNTIME, "a.py"), "w").write("print(3)\n")  # 未回流改动
        ok.append(("sync-guard", cmd_sync_runtime(argparse.Namespace(confirm=False)) == 1))
        allok = all(x[1] for x in ok)
        for name, passed in ok:
            print(f"  {'✔' if passed else '✘'} {name}")
        print("SELFTEST:", "PASS" if allok else "FAIL")
        return 0 if allok else 1
    finally:
        RUNTIME, TRACKED, DIST, SYNC_MANIFEST, DIST_MANIFEST = o_r, o_t, o_d, o_sm, o_dm
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in [("status", cmd_status), ("pull-to-tracked", cmd_pull),
                     ("anchor", cmd_anchor), ("build-dist", cmd_build_dist),
                     ("sync-runtime", cmd_sync_runtime), ("check", cmd_check),
                     ("install", cmd_install), ("selftest", cmd_selftest)]:
        p = sub.add_parser(name)
        if name in ("pull-to-tracked", "sync-runtime"):
            p.add_argument("--confirm", action="store_true")
        if name == "install":
            p.add_argument("target")
            p.add_argument("--force", action="store_true")
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
