#!/usr/bin/env python3
"""Tests for run-mode resolution — the safety-critical part is that incremental (residue gate OFF)
is NEVER a silent default; an existing site defaults to conversion (gate ON) until the user says so."""
from __future__ import annotations

from resolve_run_mode import resolve_run_mode


def test_new_site_is_from_scratch_no_prompt() -> None:
    d = resolve_run_mode(site_creation_status="created_verified")
    assert d["mode"] == "from_scratch"
    assert d["needsUserConfirmation"] is False           # a new site always has demo residue — auto
    assert d["gates"]["template_residue"] == "required"


def test_existing_site_defaults_to_conversion_and_asks() -> None:
    d = resolve_run_mode(site_creation_status="existing_site_selected")
    assert d["mode"] == "template_conversion"            # SAFE DEFAULT, not incremental
    assert d["needsUserConfirmation"] is True            # must ask conversion vs daily
    assert d["gates"]["template_residue"] == "required"  # gate ON until told otherwise
    assert d["confirmationPrompt"]


def test_incremental_is_never_a_silent_default() -> None:
    # The whole point: without an explicit declaration, an existing site NEVER resolves to incremental
    # (which would skip the residue scan). This is the failure this feature prevents.
    d = resolve_run_mode(site_creation_status="existing_site_selected")
    assert d["mode"] != "incremental_update"
    assert d["gates"]["template_residue"] == "required"


def test_declared_incremental_skips_residue() -> None:
    d = resolve_run_mode(site_creation_status="existing_site_selected", declared_mode="incremental_update")
    assert d["mode"] == "incremental_update"
    assert d["needsUserConfirmation"] is False           # user answered
    assert d["gates"]["template_residue"] == "skipped"
    assert d["gates"]["content_quality"] == "required"   # new/changed items still quality-checked


def test_declared_conversion_keeps_residue() -> None:
    d = resolve_run_mode(site_creation_status="existing_site_selected", declared_mode="template_conversion")
    assert d["mode"] == "template_conversion"
    assert d["needsUserConfirmation"] is False
    assert d["gates"]["template_residue"] == "required"


def test_demo_signals_on_existing_suggest_conversion_still_asks() -> None:
    d = resolve_run_mode(site_creation_status="existing_site_selected", demo_signal_count=7)
    assert d["mode"] == "template_conversion"
    assert d["needsUserConfirmation"] is True
    assert "7" in " ".join(d["rationale"])


def test_declared_mode_overrides_new_site() -> None:
    d = resolve_run_mode(site_creation_status="created_verified", declared_mode="incremental_update")
    assert d["mode"] == "incremental_update"             # explicit user declaration wins


def test_unknown_status_defaults_to_conversion_and_asks() -> None:
    d = resolve_run_mode(site_creation_status="")
    assert d["mode"] == "template_conversion"
    assert d["needsUserConfirmation"] is True
    assert d["gates"]["template_residue"] == "required"


def test_content_quality_always_required() -> None:
    for status, declared in (("created_verified", ""), ("existing_site_selected", ""),
                             ("existing_site_selected", "incremental_update")):
        d = resolve_run_mode(site_creation_status=status, declared_mode=declared)
        assert d["gates"]["content_quality"] == "required"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("run-mode resolution tests passed")
