#!/usr/bin/env python3
"""版本检查（check-update.py）—— 开工前检测线上 GitHub 是否有新版本（ISS-140）。
对比本地 git HEAD 与远端 main（b2b-export-ai-workbench-source，公开仓免 token），
同时读 MANIFEST.md 的 current_candidate_version 作语义版本号显示。零依赖跨平台（stdlib only）。

用法：
  python3 check-update.py                    # 交互式检查（列新提交 + 升级命令）
  python3 check-update.py --quiet            # 静默模式：只输出 UP_TO_DATE / UPDATE_AVAILABLE / CHECK_FAILED
  python3 check-update.py --auto-upgrade     # 自动升级：git pull origin main + 重建 dist + sync-runtime（runtime 存在时）

退出码（供脚本判断）：0=已是最新；1=有新版本；2=检查失败（无网络/不在 git 仓内等）。
安全边界：默认只读（ls-remote/fetch 只更新远端跟踪引用，不动工作树与本地分支）；
--auto-upgrade 才执行 pull；pull 前不 stash/reset，工作树有未提交改动导致冲突时原样报错交人工处理。
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REMOTE_URL = "https://github.com/tony-apan/b2b-export-ai-workbench-source.git"
BRANCH = "main"
KIT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = (KIT_DIR / ".." / ".." / "MANIFEST.md").resolve()
LS_REMOTE_TIMEOUT = 30   # 秒；网络差时快速失败而不是挂死
FETCH_TIMEOUT = 120
PULL_TIMEOUT = 600

EXIT_UP_TO_DATE = 0
EXIT_UPDATE_AVAILABLE = 1
EXIT_CHECK_FAILED = 2


def run(cmd, cwd=None, timeout=120):
    """跨平台子进程：list 参数不经 shell；utf-8+replace 解码防 GBK 等本地编码崩溃（对齐 install.py ISS-120 口径）。"""
    return subprocess.run(
        [str(part) for part in cmd],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )


def git_repo_root():
    """返回脚本所在 git 仓的 toplevel；不在 git 仓内（如脱离仓库的散装拷贝）返回 None。"""
    try:
        proc = run(["git", "rev-parse", "--show-toplevel"], cwd=KIT_DIR, timeout=15)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    return Path(root) if root else None


def local_head(repo_root):
    proc = run(["git", "rev-parse", "HEAD"], cwd=repo_root, timeout=15)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def remote_head():
    """ls-remote 公开仓 main 的 HEAD SHA；网络失败返回 None。"""
    try:
        proc = run(["git", "ls-remote", REMOTE_URL, BRANCH], timeout=LS_REMOTE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "ls-remote 超时（{}s）".format(LS_REMOTE_TIMEOUT)
    except OSError as exc:
        return None, "无法启动 git: {}".format(exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, "ls-remote 失败: " + (detail[-1] if detail else "exit {}".format(proc.returncode))
    for line in proc.stdout.splitlines():
        # 形如 "<40位sha>\trefs/heads/main"
        match = re.match(r"^([0-9a-f]{40,64})\s+refs/heads/" + re.escape(BRANCH) + r"$", line.strip())
        if match:
            return match.group(1), None
    return None, "ls-remote 输出中未找到 refs/heads/" + BRANCH


def manifest_version():
    """读子库 MANIFEST.md 的 current_candidate_version；文件缺失（散装拷贝/dist 部署）返回 None。"""
    try:
        text = MANIFEST_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^current_candidate_version:\s*\"?([^\"\n]+?)\"?\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def new_commits(repo_root, count_only=False):
    """fetch 远端 main 后列 HEAD..FETCH_HEAD 新提交（fetch 只写远端跟踪引用/FETCH_HEAD，不动工作树）。"""
    try:
        fetch = run(["git", "fetch", REMOTE_URL, BRANCH], cwd=repo_root, timeout=FETCH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "fetch 超时，跳过新提交列表"
    if fetch.returncode != 0:
        return None, "fetch 失败，跳过新提交列表"
    proc = run(
        ["git", "log", "HEAD..FETCH_HEAD", "--oneline"] + (["-1"] if count_only else []),
        cwd=repo_root, timeout=30,
    )
    if proc.returncode != 0:
        return None, "git log 失败，跳过新提交列表"
    return proc.stdout.strip(), None


def runtime_root(repo_root):
    """runtime 目录（对齐 scripts/interface-kit-pipeline.py：IFK_RUNTIME_ROOT 优先，否则母库同级 701_runtime）。"""
    env = os.environ.get("IFK_RUNTIME_ROOT")
    if env:
        return Path(env)
    return repo_root.parent / "701_runtime" / "00_shared" / "interface-kit"


def auto_upgrade(repo_root):
    """git pull origin main（无 origin remote 时直接 pull URL）→ 重建 dist → sync-runtime（runtime 存在时）。"""
    remotes = run(["git", "remote"], cwd=repo_root, timeout=15)
    pull_source = "origin" if remotes.returncode == 0 and "origin" in remotes.stdout.split() else REMOTE_URL
    print("==> git pull {} {}".format(pull_source, BRANCH))
    try:
        pull = run(["git", "pull", pull_source, BRANCH], cwd=repo_root, timeout=PULL_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("ERROR: git pull 超时（{}s），未完成升级".format(PULL_TIMEOUT))
        return False
    if pull.returncode != 0:
        print("ERROR: git pull 失败（不 stash/reset，请人工处理）：")
        for line in (pull.stdout or "").splitlines() + (pull.stderr or "").splitlines():
            if line.strip():
                print("    " + line.strip())
        return False
    for line in (pull.stdout or "").splitlines():
        if line.strip():
            print("    " + line.strip())

    pipeline = (KIT_DIR / ".." / ".." / "scripts" / "interface-kit-pipeline.py").resolve()
    runtime = runtime_root(repo_root)
    if not runtime.is_dir():
        print("==> runtime 不存在（{}），跳过 sync-runtime".format(runtime))
        return True
    if not pipeline.is_file():
        print("==> 未找到 {}，跳过 dist 重建与 sync-runtime".format(pipeline))
        return True
    for label, args in (
        ("重建 dist（build-dist，只读 committed 字节）", ["build-dist"]),
        ("同步 runtime（sync-runtime --confirm，有未回流改动会 fail-closed 中止）", ["sync-runtime", "--confirm"]),
    ):
        print("==> " + label)
        proc = run([sys.executable, str(pipeline)] + args, cwd=pipeline.parent, timeout=300)
        output = (proc.stdout or "") + (proc.stderr or "")
        for line in output.splitlines():
            if line.strip():
                print("    " + line.strip())
        if proc.returncode != 0:
            print("ERROR: {} 失败（exit {}），升级未完全收尾".format(args[0], proc.returncode))
            return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="检测线上 GitHub 是否有新版本（ISS-140，公开仓免 token）")
    parser.add_argument("--quiet", action="store_true",
                        help="静默模式：只输出 UP_TO_DATE / UPDATE_AVAILABLE / CHECK_FAILED（退出码 0/1/2）")
    parser.add_argument("--auto-upgrade", action="store_true",
                        help="自动升级：git pull origin main + 重建 dist + sync-runtime（runtime 存在时）")
    args = parser.parse_args(argv)

    def fail_check(reason):
        if args.quiet:
            print("CHECK_FAILED")
        else:
            print("CHECK_FAILED: " + reason)
        return EXIT_CHECK_FAILED

    repo_root = git_repo_root()
    if repo_root is None:
        return fail_check("脚本不在 git 仓库内（{}）——散装拷贝请改用完整 clone 后再检查".format(KIT_DIR))
    head = local_head(repo_root)
    if not head:
        return fail_check("git rev-parse HEAD 失败（仓库损坏？）")
    remote, remote_err = remote_head()
    if remote is None:
        return fail_check(remote_err or "无法获取远端 HEAD")

    version = manifest_version()
    version_text = "v" + version if version else "(MANIFEST 版本未知)"

    if head == remote:
        if args.quiet:
            print("UP_TO_DATE")
        else:
            print("== 版本检查 ==")
            print("本地 {} {} == 远端 {}/{}，已是最新".format(head[:12], version_text, REMOTE_URL.split("/")[-1], BRANCH))
        return EXIT_UP_TO_DATE

    if args.quiet:
        print("UPDATE_AVAILABLE")
        return EXIT_UPDATE_AVAILABLE

    print("== 版本检查 ==")
    print("本地: {} {}".format(head[:12], version_text))
    print("远端: {} ({}/{})".format(remote[:12], REMOTE_URL.split("/")[-1], BRANCH))
    commits, log_err = new_commits(repo_root)
    if commits is None:
        print("⚠ 有新版本（{} ≠ {}）".format(head[:12], remote[:12]))
        print("    " + (log_err or ""))
    elif commits.strip():
        count = len(commits.splitlines())
        print("⚠ 有新版本：远端领先 {} 个提交".format(count))
        for line in commits.splitlines():
            print("    " + line)
    else:
        # SHA 不同但 HEAD..FETCH_HEAD 为空 = 本地领先/分叉（如本地有未推送提交）
        print("i 本地与远端不同但无远端新增提交（本地领先或已分叉），无需从远端升级")
        return EXIT_UP_TO_DATE

    if args.auto_upgrade:
        print()
        if not auto_upgrade(repo_root):
            return EXIT_CHECK_FAILED
        new_head = local_head(repo_root)
        if new_head == remote:
            print("升级完成：{} == 远端 {}".format(new_head[:12], remote[:12]))
            return EXIT_UP_TO_DATE
        print("WARN: pull 后本地 {} 仍不等于远端 {}".format((new_head or "?")[:12], remote[:12]))
        return EXIT_UPDATE_AVAILABLE

    print()
    print("升级命令: git pull origin {}".format(BRANCH))
    print("或自动升级: python3 {} --auto-upgrade".format(Path(__file__).name))
    return EXIT_UPDATE_AVAILABLE


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("CHECK_FAILED: 用户中断")
        raise SystemExit(2)
