#!/usr/bin/env python3
"""Audit this AllinCMS skill package for domain leakage and sensitive residue."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
}

DOMAIN_TERMS = [
    "lai" + "faxin",
    "lai" + "fa",
    "\u6765\u53d1\u4fe1",
    "\u641c\u5ba2",
    "\u5ba2\u6237\u5f00\u53d1",
    "\u8054\u7cfb\u4eba",
    "\u90ae\u4ef6\u8425\u9500",
    "\u4e3b\u52a8\u5f00\u53d1",
    "\u7cbe\u51c6\u90ae\u7bb1",
    "\u6f5c\u5ba2",
    "C" + "RM",
    "\u5916\u8d38",
    "web." + "lai" + "faxin.com",
    "lai" + "faxin.com",
    "lai" + "fa.xin",
    "tracking" + "-logs",
    "search" + "-save-records",
    "tag" + "-management",
    "sync" + "-management",
    "i" + "forte",
    "North" + "star",
    "Moving " + "Light",
]

WORKFLOW_TERMS = [
    "lead search",
    "contact export",
    "contact exports",
    "email sending",
    "outreach",
    "prospect",
    "private contact",
    "sales playbook",
]

BLOCKLIST_PATTERNS = {
    "business_domain_leakage": re.compile("|".join(re.escape(term) for term in DOMAIN_TERMS), re.IGNORECASE),
    "non_cms_workflow_leakage": re.compile("|".join(re.escape(term) for term in WORKFLOW_TERMS), re.IGNORECASE),
    "temporary_business_copy": re.compile(r"\b(?:LED(?:\s+Lighting)?|lighting)\b", re.IGNORECASE),
    "email_address": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "mongo_like_content_id": re.compile(r"\b[a-f0-9]{24}\b"),
}

REQUIRED_ROUTER_MARKERS = {
    "SKILL.md": [
        "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED",
        "User-provided sources override examples",
        "Never invent a future site key",
        "never satisfies the canonical Adapter",
        "A customer value must be dynamic",
        "Only if the API itself reports `login_required`",
        "`http_error`, `contract_drift`, or `pagination_incomplete`",
    ],
    "README.md": [
        "verified bundled runtime snapshot",
        "普通用户只 clone / 安装这个 Skill 即可解析运行时",
        "runtimeBundleValidated",
        "customer-runtime/",
    ],
    "AGENTS.md": [
        "verified runtime snapshot",
        "second source of truth",
        "Bundle PASS proves local byte integrity only",
    ],
    "references/README.md": [
        "second CMS execution contract",
        "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED",
    ],
    "scripts/README.md": [
        "Runtime routing entry",
        "resolve_website_content_ops_root.py",
        "build_bundled_runtime.py",
        "non-authoritative",
    ],
    "references/canonical-adapter-routing.md": [
        "Only `login_required`",
        "`authenticated`",
        "`http_error`",
        "`contract_drift`",
        "`pagination_incomplete`",
    ],
    "agents/openai.yaml": [
        "API-first portable router",
        "bundled runtime snapshot",
        "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED",
        "login_required",
        "strictly serially",
    ],
    "install.sh": [
        "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED",
        "verified bundled runtime resolved",
        "verified runtime ready",
        "resolve_website_content_ops_root.py",
    ],
}

ACTIVE_ENTRYPOINT_FILES = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "NEXT-SESSION.md",
    "agents/openai.yaml",
    "install.sh",
    "references/README.md",
    "references/canonical-adapter-routing.md",
    "scripts/README.md",
)

ALLOWED_LOCAL_SCRIPT_COMMANDS = {
    "resolve_website_content_ops_root.py",
    "build_bundled_runtime.py",
    "test_resolve_website_content_ops_root.py",
    "audit_skill_hygiene.py",
    "audit_test_entrypoints.py",
}

LOCAL_SCRIPT_COMMAND_RE = re.compile(
    r"(?:^|[;&|`\n])\s*(?:python(?:3(?:\.\d+)?)?|node|bash|sh)\s+(?:\./)?scripts/([A-Za-z0-9_.-]+)",
    re.MULTILINE,
)
DIRECT_LOCAL_SCRIPT_RE = re.compile(r"(?:^|[;&|`\n])\s*\./scripts/([A-Za-z0-9_.-]+)", re.MULTILINE)

RETIRED_SKILL_HEADINGS = (
    "## Operating Rule",
    "## Required Reading",
    "## Workflow",
    "## Browser Paths",
    "## Probe Rules",
    "## Payload Rules",
)

def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[:2] == ("vendor", "website-content-ops-runtime"):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def scan_file(path: Path, root: Path) -> list[str]:
    issues: list[str] = []
    if path.resolve() == Path(__file__).resolve():
        return issues
    if path.name == "test_validate_run_evidence.py":
        return issues
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(f"{path.relative_to(root)}: cannot decode as UTF-8")
        return issues

    for lineno, line in enumerate(text.splitlines(), start=1):
        for code, pattern in BLOCKLIST_PATTERNS.items():
            match = pattern.search(line)
            if match:
                snippet = line.strip()[:180]
                issues.append(f"{path.relative_to(root)}:{lineno}: {code}: {snippet}")
    return issues


def check_router_contract(root: Path) -> list[str]:
    issues: list[str] = []
    for rel_path, markers in REQUIRED_ROUTER_MARKERS.items():
        path = root / rel_path
        if not path.exists():
            issues.append(f"{rel_path}: missing required router file")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                issues.append(f"{rel_path}: missing router marker: {marker}")

    skill_path = root / "SKILL.md"
    if skill_path.exists():
        skill_text = skill_path.read_text(encoding="utf-8")
        for heading in RETIRED_SKILL_HEADINGS:
            if heading in skill_text:
                issues.append(f"SKILL.md: retired second-source heading present: {heading}")
    return issues


def check_active_entrypoint_commands(root: Path) -> list[str]:
    """Prevent active docs/installers from re-enabling historical executors."""
    issues: list[str] = []
    for rel_path in ACTIVE_ENTRYPOINT_FILES:
        path = root / rel_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        commands = {
            *LOCAL_SCRIPT_COMMAND_RE.findall(text),
            *DIRECT_LOCAL_SCRIPT_RE.findall(text),
        }
        for script_name in sorted(commands - ALLOWED_LOCAL_SCRIPT_COMMANDS):
            issues.append(f"{rel_path}: invokes non-authoritative local script: scripts/{script_name}")
    return issues


def check_resolver_isolation(root: Path) -> list[str]:
    """The resolver may inspect canonical paths but must not import local legacy code."""
    resolver = root / "scripts/resolve_website_content_ops_root.py"
    if not resolver.is_file():
        return ["scripts/resolve_website_content_ops_root.py: missing active resolver"]
    try:
        tree = ast.parse(resolver.read_text(encoding="utf-8"), filename=str(resolver))
    except (OSError, SyntaxError) as exc:
        return [f"scripts/resolve_website_content_ops_root.py: unreadable or invalid: {exc}"]

    local_modules = {
        path.stem
        for path in (root / "scripts").glob("*.py")
        if path.name not in {
            "resolve_website_content_ops_root.py",
            "test_resolve_website_content_ops_root.py",
            "audit_skill_hygiene.py",
            "audit_test_entrypoints.py",
        }
    }
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                issues.append("scripts/resolve_website_content_ops_root.py: relative import is not allowed")
                continue
            names = {(node.module or "").split(".")[0]}
        else:
            continue
        for name in sorted(names & local_modules):
            issues.append(
                "scripts/resolve_website_content_ops_root.py: imports non-authoritative local module: " + name
            )
    return issues


def check_bundled_runtime(root: Path) -> list[str]:
    """Validate the generated bundle and reject private/runtime residue classes."""
    issues: list[str] = []
    bundle = root / "vendor" / "website-content-ops-runtime"
    resolver = root / "scripts" / "resolve_website_content_ops_root.py"
    if not bundle.is_dir():
        return ["vendor/website-content-ops-runtime: missing bundled runtime"]

    result = subprocess.run(
        [sys.executable, str(resolver), "--start", "/tmp", "--bundle-root", str(bundle), "--json"],
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in __import__("os").environ.items() if key != "WEBSITE_CONTENT_OPS_ROOT"},
    )
    if result.returncode != 0:
        issues.append("bundled runtime resolver validation failed: " + (result.stdout + result.stderr).strip())
        return issues
    try:
        payload = __import__("json").loads(result.stdout)
    except ValueError as exc:
        return [f"bundled runtime resolver returned invalid JSON: {exc}"]
    if payload.get("source") != "bundled-runtime" or payload.get("runtimeBundleValidated") is not True:
        issues.append("bundled runtime resolver did not report a validated bundled-runtime source")

    tracked_runtime_dependencies = subprocess.run(
        ["git", "-C", str(root), "ls-files", "vendor/website-content-ops-runtime/**/node_modules/**"],
        text=True,
        capture_output=True,
        check=False,
    )
    if tracked_runtime_dependencies.returncode == 0 and tracked_runtime_dependencies.stdout.strip():
        issues.append("node_modules runtime dependencies must never be tracked in the Skill repository")

    forbidden_parts = {".git", "node_modules", "dist", "customer-runtime", "credentials", "secrets", "browser-profiles"}
    forbidden_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".db", ".sqlite"}
    residue_patterns = {
        "tony_absolute_path": re.compile(rb"/Users/tony(?:/|\b)"),
        "known_real_site_key": re.compile(rb"rt4brzq2pb", re.IGNORECASE),
        "raw_bearer_value": re.compile(rb"Bearer\s+[A-Za-z0-9._~-]{24,}"),
    }
    for path in sorted(bundle.rglob("*")):
        rel = path.relative_to(bundle)
        if "node_modules" in rel.parts:
            continue
        if path.is_symlink():
            issues.append(f"{rel}: symlink forbidden inside immutable bundle")
            continue
        if not path.is_file():
            continue
        if any(part in forbidden_parts for part in rel.parts):
            issues.append(f"{rel}: forbidden bundle path class")
        if path.suffix.lower() in forbidden_suffixes:
            issues.append(f"{rel}: forbidden binary/runtime residue")
        data = path.read_bytes()
        for code, pattern in residue_patterns.items():
            if pattern.search(data):
                issues.append(f"{rel}: {code}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit skill package hygiene.")
    parser.add_argument("root", nargs="?", default=str(DEFAULT_ROOT), help="Skill root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2

    issues: list[str] = []
    for path in iter_text_files(root):
        issues.extend(scan_file(path, root))
    issues.extend(check_router_contract(root))
    issues.extend(check_active_entrypoint_commands(root))
    issues.extend(check_resolver_isolation(root))
    issues.extend(check_bundled_runtime(root))
    entrypoint_audit = root / "scripts" / "audit_test_entrypoints.py"
    if entrypoint_audit.exists():
        result = subprocess.run(
            [sys.executable, str(entrypoint_audit), str(root / "scripts")],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()
            issues.append("test entrypoint audit failed" + (f": {output}" if output else ""))

    if issues:
        print("Skill hygiene audit failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Skill hygiene audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
