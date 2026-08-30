#!/usr/bin/env python3
"""Tests for the site build-pipeline progress helper."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from site_build_status import site_build_status


def _site() -> Path:
    root = Path(tempfile.mkdtemp(prefix="allincms-site-"))
    for sub in ("run", "source-wiki", "package"):
        (root / sub).mkdir()
    return root


def _fill(d: Path, name: str = "x.json") -> None:
    (d / name).write_text("{}", encoding="utf-8")


def _run(site: Path, name: str, obj: dict) -> None:
    (site / "run" / name).write_text(json.dumps(obj), encoding="utf-8")


def test_empty_site_next_is_source_wiki() -> None:
    s = _site()
    try:
        st = site_build_status(str(s))
        assert st["nextStage"] == "build_source_wiki" and st["done"] == []
    finally:
        shutil.rmtree(s)


def test_source_wiki_then_package() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki")
        assert site_build_status(str(s))["nextStage"] == "build_package"
    finally:
        shutil.rmtree(s)


def test_package_then_content_quality() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        assert site_build_status(str(s))["nextStage"] == "content_quality_gate"
    finally:
        shutil.rmtree(s)


def test_content_quality_fail_stays_at_gate() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": False})
        assert site_build_status(str(s))["nextStage"] == "content_quality_gate"  # not advanced
    finally:
        shutil.rmtree(s)


def test_content_quality_pass_then_run_mode() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        assert site_build_status(str(s))["nextStage"] == "resolve_run_mode"
    finally:
        shutil.rmtree(s)


def test_run_mode_then_build_live() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "from_scratch"})
        assert site_build_status(str(s))["nextStage"] == "build_site_live"
    finally:
        shutil.rmtree(s)


def test_from_scratch_after_live_needs_residue() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "from_scratch"})
        _run(s, "site-live.json", {"siteKey": "abc123xyz"})
        st = site_build_status(str(s))
        assert st["nextStage"] == "residue_gate"
        assert "residue_gate" in st["gatesPending"]
    finally:
        shutil.rmtree(s)


def test_incremental_skips_residue_after_live() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "incremental_update"})
        _run(s, "site-live.json", {"siteKey": "abc123xyz"})
        st = site_build_status(str(s))
        assert "residue_gate" in st["done"]           # skipped, counted done
        assert st["nextStage"] == "launch_acceptance"
    finally:
        shutil.rmtree(s)


def test_residue_pass_then_launch() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "template_conversion"})
        _run(s, "site-live.json", {"siteKey": "abc123xyz"})
        _run(s, "residue-report.json", {"pass": True})
        assert site_build_status(str(s))["nextStage"] == "launch_acceptance"
    finally:
        shutil.rmtree(s)


def test_all_done_launched() -> None:
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "template_conversion"})
        _run(s, "site-live.json", {"siteKey": "abc123xyz"})
        _run(s, "residue-report.json", {"pass": True})
        _run(s, "launch-acceptance.json", {"pass": True})
        st = site_build_status(str(s))
        assert st["launched"] is True and st["nextStage"] is None
    finally:
        shutil.rmtree(s)


def test_unknown_mode_does_not_skip_residue() -> None:
    # A corrupt/unknown mode must NOT silently skip the residue gate — only explicit incremental does.
    s = _site()
    try:
        _fill(s / "source-wiki"); _fill(s / "package")
        _run(s, "content-quality-report.json", {"pass": True})
        _run(s, "run-mode.json", {"mode": "daily_typo"})   # not a valid mode
        _run(s, "site-live.json", {"siteKey": "abc123xyz"})
        st = site_build_status(str(s))
        assert "residue_gate" not in st["done"]
        assert st["nextStage"] == "residue_gate"
    finally:
        shutil.rmtree(s)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("site build-status tests passed")
