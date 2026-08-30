#!/usr/bin/env python3
"""Canonical shared helpers for allincms-bulk-content-upload scripts (go-forward standard).

Why this exists: an audit found `load_json` copy-defined in 117 scripts, `write_json` in 96,
`now_iso` in 93, `skill_root` in 49, `ensure_output_*` in ~50. NEW scripts should import from
here instead of re-defining, so the duplication stops growing.

Why the existing copies were NOT force-migrated: the copies are not clean duplicates. `load_json`
alone has **47 distinct implementations** across those 117 files (different exception types —
`SystemExit` vs `ValueError` — different messages, `str` vs `Path` signatures, optional labels);
`write_json` has 11 variants, `ensure_output_*` several. Blanket-unifying them would change the
error/return behaviour of ~90 scripts, roughly half of which have no direct test, for a
maintainability-only gain that is invisible to how the skill executes. That trade is not worth the
regression risk (see references/operational-findings.md, 2026-07-04 dedup finding). Use these
canonical versions in new code; leave the working divergent copies in place.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """UTC timestamp to seconds — the dominant existing variant."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    """The skill package root (this file lives in <root>/scripts/)."""
    return Path(__file__).resolve().parents[1]


def load_json(path: str | Path, label: str = "input") -> Any:
    """Load a JSON file, raising SystemExit with a clean CLI message on failure.

    Canonical for new scripts. Existing scripts keep their own load_json (47 divergent variants,
    see module docstring) — do not swap them out wholesale.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: {label} is not valid JSON ({path}): {exc}")


def write_json(path: str | Path, data: Any) -> None:
    """Write JSON with the dominant existing convention (utf-8, indent 2, trailing newline)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_output_outside_skill(output: str | Path) -> Path:
    """Reject an output path that lands inside the skill package; return the resolved path."""
    resolved = Path(output).expanduser().resolve()
    root = skill_root()
    if resolved == root or root in resolved.parents:
        raise SystemExit(f"ERROR: output must be written outside the skill package, got {resolved}")
    return resolved


def default_run_root() -> Path:
    """Cross-platform, PERSISTENT default run-folder root for the artifacts a build must
    keep across sessions (source wiki, content package, confirmation, run state — needed to
    resume/reuse/audit). Unlike /tmp it survives reboots and resolves on Windows too.
    Override with $ALLINCMS_RUN_HOME; otherwise ~/allincms-projects. One-off throwaway
    evidence may still use a temp dir, but long-lived run state belongs here."""
    env = os.environ.get("ALLINCMS_RUN_HOME", "").strip()
    return Path(env).expanduser() if env else Path.home() / "allincms-projects"
