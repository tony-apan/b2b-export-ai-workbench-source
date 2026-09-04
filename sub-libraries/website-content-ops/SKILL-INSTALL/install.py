#!/usr/bin/env python3
"""Install the AllinCMS Skill from a complete Website Content Operations checkout."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

BLOCK_CODE = "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED"
MIN_PYTHON = (3, 9)
MIN_NODE = (20, 9, 0)
SKILL_NAME_FALLBACK = "allincms-bulk-content-upload"
TOOL_DIRS = {
    "codex": Path(".codex/skills"),
    "claude": Path(".claude/skills"),
    "workbuddy": Path(".workbuddy/skills"),
}


class InstallError(RuntimeError):
    """An expected installation failure with an actionable message."""


def step(message: str) -> None:
    print(f"==> {message}", flush=True)


def fail(message: str, *, code: int = 1) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def install_commands() -> str:
    system = platform.system()
    if system == "Darwin":
        return "brew install node@20"
    if system == "Linux":
        return "sudo apt update && sudo apt install -y nodejs npm"
    if system == "Windows":
        return (
            "winget install OpenJS.NodeJS.LTS\n"
            "  or: choco install nodejs-lts\n"
            "  or download the LTS installer from https://nodejs.org/"
        )
    return "Install Node.js >=20.9.0 and npm from https://nodejs.org/"


def validate_skill_metadata(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    name_match = re.search(r"^name:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", text, re.MULTILINE)
    description_match = re.search(r"^description:\s*(\"(?:[^\"\\]|\\.)*\")\s*$", text, re.MULTILINE)
    if not name_match or not description_match:
        raise InstallError("SKILL_METADATA_INVALID: name must be kebab-case and description must be one double-quoted line")
    name = name_match.group(1)
    if len(name) > 64:
        raise InstallError("SKILL_METADATA_INVALID: name exceeds 64 characters")
    try:
        description = json.loads(description_match.group(1))
    except json.JSONDecodeError as exc:
        raise InstallError(f"SKILL_METADATA_INVALID: description is not valid JSON/YAML quoted text: {exc}") from exc
    if not description or len(description) > 1024 or len(description.encode("utf-8")) > 1024:
        raise InstallError("SKILL_METADATA_INVALID: description is empty or exceeds the 1024-character/UTF-8-byte host limit")
    prefix = description[:250]
    for label, pattern in (
        ("CMS brand", r"AllinCMS|LAICMS"),
        ("Chinese site task", r"建站|更新网站"),
        ("product/taxonomy", r"产品|categor|tag"),
        ("article", r"文章|article"),
        ("image/media", r"图片|image|media"),
        ("bulk/import", r"批量|bulk|import"),
    ):
        if not re.search(pattern, prefix, re.IGNORECASE):
            raise InstallError(f"SKILL_METADATA_INVALID: first 250 description characters miss {label} trigger")
    return name


def canonical_paths() -> tuple[Path, Path, Path]:
    skill_root = Path(__file__).resolve().parent
    source_root = skill_root.parent
    adapter = source_root / "ADAPTERS/cms/allincms"
    required = (
        skill_root / "SKILL.md",
        adapter / "package.json",
        adapter / "runtime-test-plan.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InstallError(f"{BLOCK_CODE}: missing {', '.join(missing)}")
    validate_skill_metadata(skill_root / "SKILL.md")
    return skill_root, source_root, adapter


def skill_name(skill_file: Path) -> str:
    return validate_skill_metadata(skill_file)


def parse_node_version(output: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", output.strip())
    return tuple(map(int, match.groups())) if match else None


def require_runtimes() -> tuple[str, str, str]:
    if sys.version_info < MIN_PYTHON:
        raise InstallError(
            f"Python 3.9+ is required; found {platform.python_version()}. "
        )
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        raise InstallError(
            "Node.js >=20.9.0 and npm are required. Run:\n  "
            + install_commands().replace("\n", "\n  ")
        )
    probe = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    version_text = (probe.stdout or probe.stderr).strip()
    version = parse_node_version(version_text)
    if probe.returncode != 0 or version is None or version < MIN_NODE:
        raise InstallError(
            f"Node.js >=20.9.0 is required; found {version_text or 'unknown'}. Run:\n  "
            + install_commands().replace("\n", "\n  ")
        )
    return node, npm, version_text


def command_text(command: Sequence[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def run_checked(command: Sequence[str], *, cwd: Path, label: str) -> None:
    step(label)
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        print(f"    PASS: {command_text(command)}")
        return
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part).splitlines()
    tail = "\n".join(combined[-30:]) or "(command produced no output)"
    raise InstallError(
        f"command failed ({completed.returncode}): {command_text(command)}\n"
        f"TAP/output tail:\n{tail}"
    )


def source_digest(source_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", value) else "full-source"


def write_ready_marker(adapter: Path, digest: str, node_version: str) -> None:
    marker = adapter / "node_modules/.allincms-runtime-ready.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {"status": "verified", "digest": digest, "nodeVersion": node_version},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"    ready marker: {marker}")


def target_roots(args: argparse.Namespace) -> list[Path]:
    roots = [Path(value).expanduser().resolve() for value in args.directories]
    roots.extend((Path.home() / TOOL_DIRS[name]).resolve() for name in args.tools)
    if roots:
        return list(dict.fromkeys(roots))
    for rel in TOOL_DIRS.values():
        candidate = Path.home() / rel
        if candidate.parent.is_dir():
            roots.append(candidate.resolve())
    if not roots:
        raise InstallError(
            "No known tool detected (~/.codex, ~/.claude, ~/.workbuddy). "
            "Use --dir=<path> to target a skills directory."
        )
    return list(dict.fromkeys(roots))


def is_windows_reparse_directory(path: Path) -> bool:
    if platform.system() != "Windows" or not path.exists():
        return False
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    reparse = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_dir() and bool(attributes & reparse)


def points_to(path: Path, expected: Path) -> bool:
    try:
        return path.resolve(strict=True) == expected.resolve(strict=True)
    except OSError:
        return False


def remove_link_only(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if is_windows_reparse_directory(path):
        os.rmdir(path)
        return
    raise InstallError(f"refusing to remove real file or directory: {path}")


def create_link(link: Path, source: Path) -> None:
    if platform.system() == "Windows":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip()
            raise InstallError(
                f"directory junction creation failed: {link} -> {source}: {detail}. "
                "Resolve the existing path or permissions and retry with --force."
            )
    else:
        link.symlink_to(source, target_is_directory=True)


def install_link(root: Path, name: str, source: Path, *, force: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    link = root / name
    if link.is_symlink() or is_windows_reparse_directory(link):
        if points_to(link, source):
            print(f"    = {link} already points to this source")
        elif not force:
            raise InstallError(f"{link} is an existing link; retry with --force to repoint it")
        else:
            remove_link_only(link)
            create_link(link, source)
            print(f"    ~ repointed {link} -> {source}")
    elif link.exists():
        raise InstallError(f"{link} is a real file or directory; refusing to touch it")
    else:
        create_link(link, source)
        print(f"    + {link} -> {source}")
    skill = link / "SKILL.md"
    try:
        with skill.open("r", encoding="utf-8") as handle:
            handle.read(1)
    except OSError as exc:
        raise InstallError(f"installed Skill is not readable at {skill}: {exc}") from exc
    print(f"    PASS: {skill} is readable")
    return link


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Install the source-only AllinCMS Skill and prepare its canonical runtime.",
    )
    result.add_argument("tools", nargs="*", metavar="TOOL", help="codex, claude, or workbuddy")
    result.add_argument("--dir", dest="directories", action="append", default=[], metavar="PATH")
    result.add_argument("--force", action="store_true", help="repoint an existing link; never remove real data")
    result.add_argument(
        "--skip-self-test",
        action="store_true",
        help="only create links; skip npm ci, self-tests, and ready marker",
    )
    result.add_argument(
        "--docs-parse",
        action="store_true",
        help="install optional PDF/DOCX parsing dependencies",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        unknown_tools = [name for name in args.tools if name not in TOOL_DIRS]
        if unknown_tools:
            return fail(
                f"unknown tool argument(s): {', '.join(unknown_tools)}; "
                "use codex, claude, workbuddy, or --dir=<path>",
                code=2,
            )
        if any(not value.strip() for value in args.directories):
            return fail("--dir requires a non-empty path", code=2)
        skill_root, source_root, adapter = canonical_paths()
        step(f"Canonical source checkout: {source_root}")
        node, npm, node_version = require_runtimes()
        print(f"    Python {platform.python_version()}; Node.js {node_version}; npm {npm}")
        roots = target_roots(args)

        if args.skip_self_test:
            step("Skipping npm ci and runtime self-tests (--skip-self-test)")
        else:
            run_checked([npm, "ci", "--no-audit", "--no-fund"], cwd=adapter, label="Installing locked Node dependencies")
            commands = (
                ([npm, "run", "interfaces:validate"], "Validating interface Registry"),
                ([npm, "run", "interfaces:index:check"], "Checking generated interface index"),
                ([npm, "test"], "Running runtime-test-plan suite"),
                (
                    [node, "--input-type=module", "-e", "await Promise.all([import('acorn'),import('ajv'),import('sharp')])"],
                    "Loading runtime dependencies",
                ),
            )
            for command, label in commands:
                run_checked(command, cwd=adapter, label=label)
            write_ready_marker(adapter, source_digest(source_root), node_version)

        if args.docs_parse:
            run_checked(
                [sys.executable, str(source_root / "TOOLS/interface-kit/install-deps.py"), "--yes"],
                cwd=source_root,
                label="Installing optional PDF/DOCX parsing dependencies",
            )
        else:
            print("Optional PDF/DOCX parsing dependencies were not installed; use --docs-parse when needed.")

        name = skill_name(skill_root / "SKILL.md")
        step(f"Installing Skill '{name}' from {skill_root}")
        for root in roots:
            install_link(root, name, skill_root, force=args.force)
        print("Skill installation complete. Restart tools that discover Skills only at startup.")
        return 0
    except InstallError as exc:
        return fail(str(exc))
    except KeyboardInterrupt:
        return fail("installation interrupted")
    except Exception as exc:  # Keep failures actionable instead of emitting a traceback to end users.
        return fail(f"unexpected installation failure: {exc}. Re-run the printed command after correcting the issue.")


if __name__ == "__main__":
    raise SystemExit(main())
