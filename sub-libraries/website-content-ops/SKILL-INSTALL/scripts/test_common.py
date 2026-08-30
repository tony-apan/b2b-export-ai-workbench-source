#!/usr/bin/env python3
"""Tests for _common.default_run_root (cross-platform persistent run root) and the
review_run_paths fallback that depends on it."""
from __future__ import annotations

import os
from pathlib import Path

from _common import default_run_root
from make_source_package_review_packet import review_run_paths


def _clear_env() -> None:
    os.environ.pop("ALLINCMS_RUN_HOME", None)


def test_default_is_persistent_home_dir() -> None:
    _clear_env()
    root = default_run_root()
    assert root == Path.home() / "allincms-projects"
    assert "/tmp" not in str(root)  # persistent, not the reboot-cleared temp dir


def test_env_override_is_expanduser_ed() -> None:
    os.environ["ALLINCMS_RUN_HOME"] = "~/custom-run"
    try:
        assert default_run_root() == Path.home() / "custom-run"  # ~ expanded, no literal ~
    finally:
        _clear_env()


def test_blank_env_falls_through_to_default() -> None:
    os.environ["ALLINCMS_RUN_HOME"] = "   "
    try:
        assert default_run_root() == Path.home() / "allincms-projects"
    finally:
        _clear_env()


def test_review_run_paths_fallback_lands_in_persistent_root() -> None:
    # The None fallback (real callers usually pass an explicit path) must land under the
    # persistent run root, never /tmp — this is the branch Phase 1 introduced.
    _clear_env()
    paths = review_run_paths(None)
    assert "allincms-projects" in paths["reviewPacket"]
    assert "/tmp" not in paths["reviewPacket"]


if __name__ == "__main__":
    test_default_is_persistent_home_dir()
    test_env_override_is_expanduser_ed()
    test_blank_env_falls_through_to_default()
    test_review_run_paths_fallback_lands_in_persistent_root()
    print("common/default_run_root tests passed")
