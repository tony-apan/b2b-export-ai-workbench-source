#!/usr/bin/env python3
"""Tests for the canonical shared helpers in _common.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from _common import now_iso, skill_root, load_json, write_json, ensure_output_outside_skill


def test_now_iso_shape() -> None:
    ts = now_iso()
    assert ts.endswith("+00:00") and "T" in ts and ts.count(":") == 3


def test_skill_root_has_scripts() -> None:
    root = skill_root()
    assert (root / "scripts").is_dir() and (root / "SKILL.md").exists()


def test_write_then_load_roundtrips() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "sub" / "x.json"
        write_json(p, {"a": 1, "b": ["c"]})
        assert p.read_text(encoding="utf-8").endswith("\n")
        assert load_json(p, "x") == {"a": 1, "b": ["c"]}


def test_load_json_missing_raises_systemexit() -> None:
    try:
        load_json("/no/such/file.json", "thing")
    except SystemExit as exc:
        assert "thing" in str(exc) and "not found" in str(exc)
    else:
        raise AssertionError("missing file must raise SystemExit")


def test_load_json_bad_json_raises_systemexit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        try:
            load_json(p, "cfg")
        except SystemExit as exc:
            assert "valid JSON" in str(exc)
        else:
            raise AssertionError("bad JSON must raise SystemExit")


def test_ensure_output_outside_skill_rejects_inside() -> None:
    inside = skill_root() / "scripts" / "out.json"
    try:
        ensure_output_outside_skill(inside)
    except SystemExit:
        pass
    else:
        raise AssertionError("output inside the skill package must be rejected")


def test_ensure_output_outside_skill_allows_outside() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = ensure_output_outside_skill(Path(tmp) / "ok.json")
        assert isinstance(p, Path)


if __name__ == "__main__":
    test_now_iso_shape()
    test_skill_root_has_scripts()
    test_write_then_load_roundtrips()
    test_load_json_missing_raises_systemexit()
    test_load_json_bad_json_raises_systemexit()
    test_ensure_output_outside_skill_rejects_inside()
    test_ensure_output_outside_skill_allows_outside()
    print("_common regression tests passed")
