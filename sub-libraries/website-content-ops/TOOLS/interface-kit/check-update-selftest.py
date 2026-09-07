#!/usr/bin/env python3
"""check-update.py 自测（check-update-selftest.py）—— stdlib 临时 git 仓覆盖核心场景（ISS-140/ISS-141）。

覆盖场景（>=8）：
 1. up_to_date               本地 == 远端 main -> UP_TO_DATE (exit 0)
 2. behind                   远端领先 -> UPDATE_AVAILABLE (exit 1)
 3. local_ahead              本地领先 -> LOCAL_DIVERGED (exit 2)
 4. diverged                 双方各有新提交 -> LOCAL_DIVERGED (exit 2)
 5. auto_refuse_dirty        --auto-upgrade 工作树 dirty -> 拒绝且 HEAD 不变
 6. auto_refuse_detached     --auto-upgrade detached HEAD -> 拒绝
 7. auto_refuse_wrong_origin --auto-upgrade origin 指向非官方地址 -> 拒绝
 8. cache_hit                新鲜缓存命中时不联网（远端被移走仍 UP_TO_DATE）；--force 后 CHECK_FAILED
 9. tag_namespace_invalid    current_candidate_version non-null 且远端无 namespaced tag -> VERSION_STATE_INVALID (exit 2)
10. tag_target_mismatch      namespaced tag 指向旧提交（≠远端 main HEAD）-> VERSION_STATE_INVALID (exit 2)
11. tag_namespace_ok         namespaced tag 存在且指向远端 main HEAD -> 不触发 VERSION_STATE_INVALID
12. auto_upgrade_success     clean main + origin 正确 + 严格落后 -> --ff-only 拉平

运行：python3 check-update-selftest.py   （只用 stdlib：tempfile/subprocess/importlib；不访问网络）
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK_UPDATE = HERE / "check-update.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_update_under_test", CHECK_UPDATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args, check=True):
    proc = subprocess.run(
        ["git", "-c", "user.email=selftest@example.com", "-c", "user.name=selftest",
         "-c", "commit.gpgsign=false", *args],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError("git {} 失败: {}".format(" ".join(args), proc.stderr.strip()[:300]))
    return proc


def make_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-b", "main")
    (path / "README.md").write_text("# t\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-m", "init")
    return path


def commit(path, name):
    (path / name).write_text(name + "\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-m", name)


def run_check(cu, argv):
    """以指定参数调用被测 main()，捕获 stdout，返回 (exit_code, output)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cu.main(argv)
    return code, buf.getvalue()


def fresh_case(cu, tmp, manifest_value="null", name=None):
    """建 origin + clone + 临时 MANIFEST；返回 (origin, clone, manifest)。每个场景用独立 name。"""
    tag = name or os.urandom(4).hex()
    origin = make_repo(Path(tmp) / ("origin-" + tag))
    clone = Path(tmp) / ("clone-" + tag)
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True,
                   capture_output=True, text=True)
    manifest = Path(tmp) / ("manifest-" + tag + ".md")
    manifest.write_text(
        "---\ncurrent_candidate_version: {}\n---\n".format(manifest_value), encoding="utf-8")
    cu.MANIFEST_PATH = manifest
    cu.REMOTE_URL = str(origin)
    cu.REPO_OVERRIDE = str(clone)   # 让 git_repo_root() 指向测试 clone（自测 seam）
    return origin, clone, manifest


def main():
    if shutil.which("git") is None:
        print("SELFTEST: FAIL（环境缺 git）")
        return 1
    results = []

    def record(name, passed, detail=""):
        results.append((name, bool(passed), detail))
        print("  {0} {1}{2}".format("✔" if passed else "✘", name, (" — " + detail) if detail and not passed else ""))

    tmp = tempfile.mkdtemp(prefix="wco-check-update-selftest-")
    try:
        # 1. up_to_date
        cu = load_module()
        origin, clone, _ = fresh_case(cu, tmp)
        code, out = run_check(cu, ["--quiet"])
        record("up_to_date", code == cu.EXIT_UP_TO_DATE and "UP_TO_DATE" in out,
               "exit={} out={!r}".format(code, out.strip()))
        # 缓存文件应已写入 clone/.git/
        record("cache_written", (clone / ".git" / cu.CACHE_NAME).is_file())

        # 2. behind（--force 绕开上一步写入的新鲜缓存）
        commit(origin, "remote-change")
        code, out = run_check(cu, ["--quiet", "--force"])
        record("behind", code == cu.EXIT_UPDATE_AVAILABLE and "UPDATE_AVAILABLE" in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 3. local_ahead
        cu2 = load_module()
        origin2, clone2, _ = fresh_case(cu2, tmp)
        commit(clone2, "local-only")
        code, out = run_check(cu2, ["--quiet"])
        record("local_ahead", code == cu2.EXIT_CHECK_FAILED and "LOCAL_DIVERGED" in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 4. diverged
        commit(origin2, "remote-only")
        code, out = run_check(cu2, ["--quiet"])
        record("diverged", code == cu2.EXIT_CHECK_FAILED and "LOCAL_DIVERGED" in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 5. auto_refuse_dirty
        cu3 = load_module()
        origin3, clone3, _ = fresh_case(cu3, tmp)
        commit(origin3, "remote-new")
        (clone3 / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        head_before = git(clone3, "rev-parse", "HEAD").stdout.strip()
        code, out = run_check(cu3, ["--auto-upgrade"])
        head_after = git(clone3, "rev-parse", "HEAD").stdout.strip()
        record("auto_refuse_dirty",
               code == cu3.EXIT_CHECK_FAILED and "拒绝自动升级" in out and head_before == head_after,
               "exit={} out={!r} head_moved={}".format(code, out.strip()[:120], head_before != head_after))

        # 6. auto_refuse_detached
        cu4 = load_module()
        origin4, clone4, _ = fresh_case(cu4, tmp)
        commit(origin4, "remote-new-2")
        git(clone4, "checkout", "-q", "--detach", "HEAD")
        head_before = git(clone4, "rev-parse", "HEAD").stdout.strip()
        code, out = run_check(cu4, ["--auto-upgrade"])
        head_after = git(clone4, "rev-parse", "HEAD").stdout.strip()
        record("auto_refuse_detached",
               code == cu4.EXIT_CHECK_FAILED and "detached" in out and head_before == head_after,
               "exit={} out={!r}".format(code, out.strip()[:120]))

        # 7. auto_refuse_wrong_origin
        cu5 = load_module()
        origin5, clone5, _ = fresh_case(cu5, tmp)
        commit(origin5, "remote-new-3")
        other = make_repo(Path(tmp) / "other-remote")
        git(clone5, "remote", "set-url", "origin", str(other))
        code, out = run_check(cu5, ["--auto-upgrade"])
        record("auto_refuse_wrong_origin",
               code == cu5.EXIT_CHECK_FAILED and "不是官方地址" in out,
               "exit={} out={!r}".format(code, out.strip()[:120]))

        # 8. cache_hit：命中新鲜缓存时不联网（远端目录移走仍 UP_TO_DATE）；--force 联网即失败
        cu6 = load_module()
        origin6, clone6, _ = fresh_case(cu6, tmp)
        code, out = run_check(cu6, ["--quiet"])
        assert code == cu6.EXIT_UP_TO_DATE, out
        moved = Path(tmp) / "origin6-moved-away"
        shutil.move(str(origin6), str(moved))
        code, out = run_check(cu6, ["--quiet"])
        cached_ok = code == cu6.EXIT_UP_TO_DATE and "UP_TO_DATE" in out
        code2, out2 = run_check(cu6, ["--quiet", "--force"])
        record("cache_hit",
               cached_ok and code2 == cu6.EXIT_CHECK_FAILED and "CHECK_FAILED" in out2,
               "cached(exit={} out={!r}) forced(exit={} out={!r})".format(code, out.strip(), code2, out2.strip()))

        # 9. tag_namespace_invalid：声明候选版本但远端无 namespaced tag
        cu7 = load_module()
        origin7, clone7, _ = fresh_case(cu7, tmp, manifest_value="9.9.9-preview.9")
        code, out = run_check(cu7, ["--quiet"])
        record("tag_namespace_invalid",
               code == cu7.EXIT_CHECK_FAILED and "VERSION_STATE_INVALID" in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 10. tag_target_mismatch：tag 存在但指向旧提交（≠ 远端 main HEAD）
        commit(origin7, "one-more")   # origin7 现在至少 2 个提交
        git(origin7, "tag", "sub-library/website-content-ops/v9.9.9-preview.9", "HEAD~1")
        code, out = run_check(cu7, ["--quiet", "--force"])
        record("tag_target_mismatch",
               code == cu7.EXIT_CHECK_FAILED and "VERSION_STATE_INVALID" in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 11. tag_namespace_ok：tag 指向远端 main HEAD -> 无 VERSION_STATE_INVALID
        git(origin7, "tag", "-d", "sub-library/website-content-ops/v9.9.9-preview.9")
        git(origin7, "tag", "sub-library/website-content-ops/v9.9.9-preview.9", "HEAD")
        code, out = run_check(cu7, ["--quiet", "--force"])
        record("tag_namespace_ok",
               code == cu7.EXIT_UPDATE_AVAILABLE and "VERSION_STATE_INVALID" not in out,
               "exit={} out={!r}".format(code, out.strip()))

        # 12. auto_upgrade_success：clean main + origin 正确 + 严格落后 -> --ff-only 拉平
        cu8 = load_module()
        origin8, clone8, _ = fresh_case(cu8, tmp)
        commit(origin8, "remote-ff")
        code, out = run_check(cu8, ["--auto-upgrade"])
        head8 = git(clone8, "rev-parse", "HEAD").stdout.strip()
        remote8 = git(origin8, "rev-parse", "HEAD").stdout.strip()
        record("auto_upgrade_success",
               "升级完成" in out and head8 == remote8,
               "exit={} out={!r} head_eq_remote={}".format(code, out.strip()[:160], head8 == remote8))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [name for name, ok, _ in results if not ok]
    print("SELFTEST:", "PASS ({}/{} scenarios)".format(len(results) - len(failed), len(results))
          if not failed else "FAIL: " + ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
