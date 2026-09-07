#!/usr/bin/env python3
"""main 分支同步检查（check-update.py）—— 开工前检测本地 HEAD 与远端 main 是否同步（ISS-140，ISS-141 升级）。

语义说明（2026-09-07 修正）：
- 本工具做的是「main 分支同步检查」，不是「版本是否最新」判断。`UP_TO_DATE` 只表示
  本地 HEAD == 远端 main HEAD；它不代表候选版本已发布、也不代表版本号最新。
- tag/namespace 诊断：读取子库 MANIFEST.md 的 current_candidate_version；若为 non-null，
  预期 canonical 远端存在 namespaced tag `sub-library/website-content-ops/v<version>`
  且其 target commit SHA 与远端 main HEAD 一致（ISS-141：一版三绑事故的机器闸）；
  tag 缺失或 target 不一致 -> VERSION_STATE_INVALID（--quiet 退出码 2）。
  current_candidate_version 为 null（候选未分配）时只做 main SHA 同步检查。
- 本地领先或分叉（远端没有本地缺少的提交）-> LOCAL_DIVERGED（退出码 2），
  不能与 UP_TO_DATE 混淆。

用法：
  python3 check-update.py                       # 交互式检查（列新提交 + 升级命令）
  python3 check-update.py --quiet               # 静默：UP_TO_DATE / UPDATE_AVAILABLE / LOCAL_DIVERGED / VERSION_STATE_INVALID / CHECK_FAILED
  python3 check-update.py --auto-upgrade        # 安全自动升级：仅 clean main + origin 正确 + 落后可 fast-forward 时 git pull --ff-only
  python3 check-update.py --max-age-hours 24    # 结果缓存窗口（默认 24；缓存只存检查时间+远端 SHA，不含凭据）
  python3 check-update.py --force               # 忽略缓存强制联网检查

退出码：0=main 同步（UP_TO_DATE）；1=远端有新提交（UPDATE_AVAILABLE）；
2=检查失败 / 本地领先或分叉（LOCAL_DIVERGED）/ tag namespace 诊断失败（VERSION_STATE_INVALID）。

安全边界：默认只读（ls-remote/fetch 只更新远端跟踪引用与 FETCH_HEAD，不动工作树与本地分支）。
--auto-upgrade 前置守卫：工作树 dirty、detached HEAD、非 main 分支、origin 非官方地址、
本地领先或分叉时一律拒绝升级；只有 clean main + origin 正确 + 严格落后时才执行
git pull --ff-only（不 stash/reset）。升级后的 runtime 漂移由
scripts/interface-kit-pipeline.py sync-runtime 的既有 fail-closed 守卫兜底。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REMOTE_URL = "https://github.com/tony-apan/b2b-export-ai-workbench-source.git"
BRANCH = "main"
TAG_NAMESPACE_PREFIX = "sub-library/website-content-ops/v"
KIT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = (KIT_DIR / ".." / ".." / "MANIFEST.md").resolve()
REPO_OVERRIDE = None   # 仅供 check-update-selftest.py 注入临时仓根；正常使用恒为 None
CACHE_NAME = "wco-update-check.json"   # 写在 <repo>/.git/ 下，永不 tracked，不含凭据
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
    """返回脚本所在 git 仓的 toplevel；不在 git 仓内（如脱离仓库的散装拷贝）返回 None。

    自测 seam：REPO_OVERRIDE 非 None 时直接返回该路径（check-update-selftest.py 注入临时仓）。
    """
    if REPO_OVERRIDE is not None:
        return Path(REPO_OVERRIDE)
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


def branch_name(repo_root):
    """当前分支名；detached HEAD 返回 "HEAD"（git 通用输出）；失败返回 None。"""
    proc = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, timeout=15)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def worktree_dirty(repo_root):
    """工作树是否有任何未提交/未合并改动（含未跟踪文件）；干净返回 False。"""
    proc = run(["git", "status", "--porcelain"], cwd=repo_root, timeout=30)
    if proc.returncode != 0:
        return True   # 状态不明按 dirty 处理（fail-closed）
    return bool(proc.stdout.strip())


def origin_url(repo_root):
    """origin remote 的 URL；无 origin 或查询失败返回 None。"""
    proc = run(["git", "remote", "get-url", "origin"], cwd=repo_root, timeout=15)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def normalize_git_url(url):
    """归一化比较：去空白/尾斜杠/.git 后缀；github ssh 形式折算为 https 形式。"""
    u = (url or "").strip().rstrip("/")
    if u.endswith(".git"):
        u = u[: -len(".git")]
    u = re.sub(r"^git@github\.com:", "https://github.com/", u)
    return u.lower()


def remote_head(remote_url=None):
    """ls-remote canonical 仓 main 的 HEAD SHA；网络失败返回 (None, 原因)。"""
    url = remote_url or REMOTE_URL
    try:
        proc = run(["git", "ls-remote", url, BRANCH], timeout=LS_REMOTE_TIMEOUT)
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
    """读子库 MANIFEST.md 的 current_candidate_version；文件缺失或值为 null/未声明返回 None。"""
    try:
        text = MANIFEST_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^current_candidate_version:\s*\"?([^\"\n]+?)\"?\s*$", text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if not value or value.lower() in ("null", "~"):
        return None   # 候选未分配（如 "unassigned" 状态）：只做 main 同步检查
    return value


def namespaced_tag_target(remote_url, version):
    """ls-remote 查询 namespaced tag 的 target commit SHA。

    返回 (target_sha, err)：
    - tag 存在：annotated tag 取 peeled `^{}` 的 commit SHA，lightweight tag 取 ref 本身 SHA；
    - tag 不存在：err="missing"；
    - 查询失败：err=原因。
    """
    tag_ref = TAG_NAMESPACE_PREFIX + version
    url = remote_url or REMOTE_URL
    try:
        proc = run(["git", "ls-remote", "--tags", url, tag_ref], timeout=LS_REMOTE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "ls-remote 超时（{}s）".format(LS_REMOTE_TIMEOUT)
    except OSError as exc:
        return None, "无法启动 git: {}".format(exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, "ls-remote --tags 失败: " + (detail[-1] if detail else "exit {}".format(proc.returncode))
    direct = None
    peeled = None
    for line in proc.stdout.splitlines():
        match = re.match(r"^([0-9a-f]{40,64})\s+(refs/tags/\S+)$", line.strip())
        if not match:
            continue
        sha, ref = match.group(1), match.group(2)
        if ref == "refs/tags/" + tag_ref:
            direct = sha
        elif ref == "refs/tags/" + tag_ref + "^{}":
            peeled = sha
    if direct is None and peeled is None:
        return None, "missing"
    return (peeled or direct), None


def check_namespaced_tag(remote_main_sha, remote_url=None):
    """ISS-141 机器闸：候选版本已分配时，namespaced tag 必须存在且指向远端 main HEAD。

    返回 (ok, detail)；ok=False 时上层输出 VERSION_STATE_INVALID。
    """
    version = manifest_version()
    if version is None:
        return True, None   # 候选未分配：只做 main 同步检查
    tag_ref = TAG_NAMESPACE_PREFIX + version
    target, err = namespaced_tag_target(remote_url, version)
    if err == "missing":
        return False, "MANIFEST 声明 current_candidate_version={0}，但远端不存在 namespaced tag `{1}`（wrong namespace 或未打 tag）".format(version, tag_ref)
    if target is None:
        return False, "namespaced tag `{0}` 查询失败：{1}".format(tag_ref, err)
    if target != remote_main_sha:
        return False, "namespaced tag `{0}` 指向 {1}，与远端 main HEAD {2} 不一致（一版多绑）".format(tag_ref, target[:12], remote_main_sha[:12])
    return True, tag_ref + " -> " + target[:12]


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


def ahead_behind(repo_root, remote_url=None):
    """fetch 远端 main 后计算 (ahead, behind)：ahead=FETCH_HEAD..HEAD 数，behind=HEAD..FETCH_HEAD 数。

    本地领先或分叉时 ahead>0。fetch/log 失败返回 None（无法分类）。
    """
    url = remote_url or REMOTE_URL
    try:
        fetch = run(["git", "fetch", url, BRANCH], cwd=repo_root, timeout=FETCH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    if fetch.returncode != 0:
        return None
    behind = run(["git", "rev-list", "--count", "HEAD..FETCH_HEAD"], cwd=repo_root, timeout=30)
    ahead = run(["git", "rev-list", "--count", "FETCH_HEAD..HEAD"], cwd=repo_root, timeout=30)
    if behind.returncode != 0 or ahead.returncode != 0:
        return None
    try:
        return int(ahead.stdout.strip()), int(behind.stdout.strip())
    except ValueError:
        return None


def cache_path(repo_root):
    return repo_root / ".git" / CACHE_NAME


def read_cache(repo_root, max_age_hours):
    """读取新鲜缓存；返回 {"checked_at":..., "remote_sha":...} 或 None（无缓存/过期/损坏/来源不符）。"""
    path = cache_path(repo_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        checked_at = float(data.get("checked_at", 0))
        remote_sha = data.get("remote_sha", "")
        cached_url = data.get("remote_url", "")
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(remote_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", remote_sha):
        return None
    if normalize_git_url(cached_url) != normalize_git_url(REMOTE_URL):
        return None
    if max_age_hours <= 0 or (time.time() - checked_at) > max_age_hours * 3600:
        return None
    return {"checked_at": checked_at, "remote_sha": remote_sha}


def write_cache(repo_root, remote_sha):
    """缓存只写检查时间 + 远端 SHA + 远端 URL（不含任何凭据/本地状态）。"""
    path = cache_path(repo_root)
    try:
        path.write_text(
            json.dumps({"checked_at": time.time(), "remote_sha": remote_sha, "remote_url": REMOTE_URL},
                       ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        pass   # 缓存写失败不影响检查结论


def runtime_root(repo_root):
    """runtime 目录（对齐 scripts/interface-kit-pipeline.py：IFK_RUNTIME_ROOT 优先，否则母库同级 701_runtime）。"""
    env = os.environ.get("IFK_RUNTIME_ROOT")
    if env:
        return Path(env)
    return repo_root.parent / "701_runtime" / "00_shared" / "interface-kit"


def auto_upgrade(repo_root, ahead):
    """安全自动升级：前置守卫全过后 git pull --ff-only origin main → 重建 dist → sync-runtime（runtime 存在时）。

    守卫（任一不满足即拒绝，不执行 pull）：
    1. 当前分支必须是 main 且非 detached HEAD；
    2. 工作树必须 clean（含未跟踪文件）；
    3. origin 必须存在且指向 canonical 官方地址（防野远端注入）；
    4. 本地不得领先/分叉（ahead==0，调用方已分类）。
    """
    branch = branch_name(repo_root)
    if branch == "HEAD":
        print("拒绝自动升级：detached HEAD（不在任何分支上）——请先 git checkout main")
        return False
    if branch != BRANCH:
        print("拒绝自动升级：当前分支是 `{0}`，不是 `{1}`".format(branch, BRANCH))
        return False
    if worktree_dirty(repo_root):
        print("拒绝自动升级：工作树有未提交/未跟踪改动（--auto-upgrade 不 stash/reset，请先人工处理）")
        return False
    origin = origin_url(repo_root)
    if origin is None:
        print("拒绝自动升级：未配置 origin remote")
        return False
    if normalize_git_url(origin) != normalize_git_url(REMOTE_URL):
        print("拒绝自动升级：origin 指向 {0}，不是官方地址 {1}".format(origin, REMOTE_URL))
        return False
    if ahead and ahead > 0:
        print("拒绝自动升级：本地领先/分叉（非 fast-forward 场景）——请人工 rebase/merge 决策")
        return False

    print("==> git pull --ff-only origin {}".format(BRANCH))
    try:
        pull = run(["git", "pull", "--ff-only", "origin", BRANCH], cwd=repo_root, timeout=PULL_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("ERROR: git pull 超时（{}s），未完成升级".format(PULL_TIMEOUT))
        return False
    if pull.returncode != 0:
        print("ERROR: git pull --ff-only 失败（不 stash/reset，请人工处理）：")
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
    parser = argparse.ArgumentParser(
        description="main 分支同步检查（ISS-140/ISS-141）：对比本地 HEAD 与远端 main；"
                    "UP_TO_DATE 只表示 main 分支同步，不是“版本已是最新”")
    parser.add_argument("--quiet", action="store_true",
                        help="静默模式：只输出 UP_TO_DATE / UPDATE_AVAILABLE / LOCAL_DIVERGED / "
                             "VERSION_STATE_INVALID / CHECK_FAILED（退出码 0/1/2/2/2）。"
                             "UP_TO_DATE 语义=本地 HEAD 与远端 main 同步")
    parser.add_argument("--auto-upgrade", action="store_true",
                        help="安全自动升级：仅 clean main + origin 正确 + 落后可 fast-forward 时执行 "
                             "git pull --ff-only；dirty/detached/非 main/origin 异常/本地领先分叉一律拒绝")
    parser.add_argument("--max-age-hours", type=float, default=24.0, metavar="H",
                        help="检查结果缓存窗口（小时，默认 24；缓存只存检查时间+远端 SHA，写在 .git/ 下不 tracked；"
                             "仅候选版本未分配时的 main 同步检查可命中缓存；<=0 等效总是过期")
    parser.add_argument("--force", action="store_true",
                        help="忽略缓存，强制联网检查")
    args = parser.parse_args(argv)

    def fail_check(reason):
        if args.quiet:
            print("CHECK_FAILED")
        else:
            print("CHECK_FAILED: " + reason)
        return EXIT_CHECK_FAILED

    def invalid_state(reason):
        if args.quiet:
            print("VERSION_STATE_INVALID")
        else:
            print("VERSION_STATE_INVALID: " + reason)
        return EXIT_CHECK_FAILED

    repo_root = git_repo_root()
    if repo_root is None:
        return fail_check("脚本不在 git 仓库内（{}）——散装拷贝请改用完整 clone 后再检查".format(KIT_DIR))
    head = local_head(repo_root)
    if not head:
        return fail_check("git rev-parse HEAD 失败（仓库损坏？）")

    version = manifest_version()
    version_text = "v" + version if version else "(候选版本未分配：BLOCK)"

    # 缓存短路：仅候选版本未分配时，命中新鲜缓存且本地 HEAD == 缓存远端 SHA -> UP_TO_DATE（不联网）
    if not args.force and version is None:
        cached = read_cache(repo_root, args.max_age_hours)
        if cached and cached["remote_sha"] == head:
            if args.quiet:
                print("UP_TO_DATE")
            else:
                print("== main 分支同步检查 ==")
                print("本地 {} == 缓存远端 {}/main {}（{} 内缓存命中，未联网；UP_TO_DATE 只表示 main 同步）"
                      .format(head[:12], REMOTE_URL.split("/")[-1], cached["remote_sha"][:12], args.max_age_hours))
            return EXIT_UP_TO_DATE

    remote, remote_err = remote_head()
    if remote is None:
        return fail_check(remote_err or "无法获取远端 HEAD")
    write_cache(repo_root, remote)

    # tag/namespace 诊断（ISS-141）：候选版本已分配时强校验 namespaced tag
    tag_ok, tag_detail = check_namespaced_tag(remote)
    if not tag_ok:
        return invalid_state(tag_detail)
    if tag_detail and not args.quiet:
        print("tag 诊断: {} 与远端 main 一致".format(tag_detail))

    if head == remote:
        if args.quiet:
            print("UP_TO_DATE")
        else:
            print("== main 分支同步检查 ==")
            print("本地 {} {} == 远端 {}/{}，main 分支同步（非版本号判断）".format(head[:12], version_text, REMOTE_URL.split("/")[-1], BRANCH))
        if args.auto_upgrade:
            print("已与远端 main 同步，无需升级")
        return EXIT_UP_TO_DATE

    # head != remote：先分类（本地领先/分叉 vs 严格落后）
    ab = ahead_behind(repo_root)
    if ab is None:
        # 无法 fetch 分类时保守按“远端可能有更新”处理（与旧行为兼容），auto-upgrade 自身守卫兜底
        ahead, behind = 0, -1
    else:
        ahead, behind = ab
    if ahead > 0:
        if args.quiet:
            print("LOCAL_DIVERGED")
        else:
            print("== main 分支同步检查 ==")
            print("本地 {} 领先远端 {}（本地有未推送提交或已分叉）——LOCAL_DIVERGED，不能自动升级".format(head[:12], remote[:12]))
        return EXIT_CHECK_FAILED

    if args.quiet:
        print("UPDATE_AVAILABLE")
        return EXIT_UPDATE_AVAILABLE

    print("== main 分支同步检查 ==")
    print("本地: {} {}".format(head[:12], version_text))
    print("远端: {} ({}/{})".format(remote[:12], REMOTE_URL.split("/")[-1], BRANCH))
    if behind == 0:
        # SHA 不同但双向计数均为 0（浅克隆/异常历史）——按分叉口径提示
        print("i 本地与远端 SHA 不同但无法归类为落后（浅克隆或历史异常），请人工核对")
        return EXIT_CHECK_FAILED
    commits, log_err = new_commits(repo_root)
    if commits is None:
        print("⚠ 远端 main 有新提交（{} ≠ {}）".format(head[:12], remote[:12]))
        print("    " + (log_err or ""))
    elif commits.strip():
        count = len(commits.splitlines())
        print("⚠ 远端 main 领先 {} 个提交".format(count))
        for line in commits.splitlines():
            print("    " + line)
    else:
        print("⚠ 远端 main 有新提交（{} ≠ {}）".format(head[:12], remote[:12]))

    if args.auto_upgrade:
        print()
        if not auto_upgrade(repo_root, ahead):
            return EXIT_CHECK_FAILED
        new_head = local_head(repo_root)
        if new_head == remote:
            print("升级完成：{} == 远端 main {}".format((new_head or "?")[:12], remote[:12]))
            return EXIT_UP_TO_DATE
        print("WARN: pull 后本地 {} 仍不等于远端 main {}".format((new_head or "?")[:12], remote[:12]))
        return EXIT_UPDATE_AVAILABLE

    print()
    print("升级命令: git pull --ff-only origin {}".format(BRANCH))
    print("或自动升级: python3 {} --auto-upgrade".format(Path(__file__).name))
    return EXIT_UPDATE_AVAILABLE


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("CHECK_FAILED: 用户中断")
        raise SystemExit(2)
