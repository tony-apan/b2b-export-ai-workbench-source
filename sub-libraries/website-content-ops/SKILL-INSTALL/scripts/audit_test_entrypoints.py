#!/usr/bin/env python3
"""Audit script-style regression tests for skipped local test functions."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys


DEFAULT_SCRIPTS_DIR = Path(__file__).resolve().parent


def no_arg_test_functions(tree: ast.Module) -> list[str]:
    tests: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        required_positional = [
            arg
            for arg in node.args.args
            if arg.arg not in {"self", "cls"}
        ]
        if not required_positional and not node.args.kwonlyargs:
            tests.append(node.name)
    return tests


def has_main_guard(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
            continue
        for comparator in test.comparators:
            if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                return True
    return False


def uses_test_discovery(text: str) -> bool:
    return 'startswith("test_")' in text or "startswith('test_')" in text


def directly_called_tests(tree: ast.Module) -> set[str]:
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id.startswith("test_"):
            called.add(node.func.id)
    return called


def audit_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: syntax error: {exc}"]
    tests = no_arg_test_functions(tree)
    if not tests:
        return []
    if not has_main_guard(tree):
        return [f"{path}: missing __main__ test runner for {len(tests)} test functions"]
    if uses_test_discovery(text):
        return []
    missing = sorted(set(tests) - directly_called_tests(tree))
    if missing:
        preview = ", ".join(missing[:10])
        if len(missing) > 10:
            preview += ", ..."
        return [f"{path}: __main__ does not run {len(missing)} test functions: {preview}"]
    return []


def audit(scripts_dir: Path) -> list[str]:
    issues: list[str] = []
    for path in sorted(scripts_dir.glob("test_*.py")):
        issues.extend(audit_file(path))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit AllinCMS test script entrypoints.")
    parser.add_argument("scripts_dir", nargs="?", default=str(DEFAULT_SCRIPTS_DIR))
    args = parser.parse_args()
    issues = audit(Path(args.scripts_dir))
    if issues:
        print("Test entrypoint audit failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Test entrypoint audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
