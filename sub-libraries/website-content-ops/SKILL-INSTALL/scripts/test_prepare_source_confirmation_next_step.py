#!/usr/bin/env python3
"""Regression tests for source confirmation next-step handoff preparation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_source_confirmation_next_step import build_handoff, validate_handoff
from run_source_file_rehearsal import build as run_rehearsal
from test_run_source_file_rehearsal import base_args, make_preflight, refined_target, wiki_for_rehearsal_inventory, write_json


def make_summary(root: Path, *, confirmed: bool = False, preflight: bool = False) -> dict:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    if confirmed:
        args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
    if preflight:
        args.create_preflight = str(make_preflight(root))
    return run_rehearsal(args)


def handoff_args(root: Path, summary: dict, **overrides: str) -> argparse.Namespace:
    values = {
        "brief": summary["confirmationBrief"]["json"],
        "summary": str(root / "rehearsal" / "source-file-rehearsal-summary.json"),
        "user_confirmation_text": "",
        "output": str(root / "next-step-handoff.json"),
        "json": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_waiting_confirmation_handoff_without_text_is_non_executable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root)
        handoff = build_handoff(handoff_args(root, summary))
        assert handoff["mode"] == "await_user_confirmation_text"
        assert handoff["localCommandReady"] is False
        assert handoff["localCommand"] == ""
        assert handoff["browserBoundary"]["required"] is False
        assert "capture explicit content-intent confirmation" in handoff["nextAction"]
        assert not validate_handoff(handoff)


def test_waiting_confirmation_handoff_with_text_prepares_local_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root)
        handoff = build_handoff(
            handoff_args(
                root,
                summary,
                user_confirmation_text="User confirms package for temporary site execution.",
            )
        )
        assert handoff["mode"] == "await_user_confirmation_text"
        assert handoff["localCommandReady"] is True
        assert "prepare_confirmed_site_execution.py" in handoff["localCommand"]
        assert "<paste current user confirmation text here>" not in handoff["localCommand"]
        assert "User confirms package for temporary site execution." in handoff["localCommand"]
        assert handoff["browserBoundary"]["required"] is False
        assert not validate_handoff(handoff)


def test_confirmed_handoff_collects_create_preflight_boundary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root, confirmed=True)
        handoff = build_handoff(handoff_args(root, summary))
        assert handoff["mode"] == "collect_create_preflight"
        assert handoff["localCommandReady"] is False
        assert handoff["browserBoundary"]["required"] is True
        assert handoff["browserBoundary"]["readOnly"] is True
        assert handoff["browserBoundary"]["action"] == "collect_create_site_preflight"
        assert handoff["browserBoundary"]["targetEvidence"] == summary["artifacts"]["confirmedCreateSitePreflightTarget"]
        assert not validate_handoff(handoff)


def test_confirmed_with_preflight_handoff_points_to_gated_create_site_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root, confirmed=True, preflight=True)
        handoff = build_handoff(handoff_args(root, summary))
        assert handoff["mode"] == "run_gated_create_site"
        assert handoff["localCommandReady"] is False
        assert handoff["browserBoundary"]["required"] is True
        assert handoff["browserBoundary"]["readOnly"] is False
        assert handoff["browserBoundary"]["requiresActionAuthorization"] is True
        assert handoff["browserBoundary"]["browserStepsExecutable"] is False
        assert handoff["browserBoundary"]["runbook"] == summary["artifacts"]["confirmedCreateSiteRunbook"]
        assert handoff["browserBoundary"]["evidenceBundle"] == summary["artifacts"]["confirmedCreatedSiteEvidenceBundle"]
        assert not validate_handoff(handoff)


def test_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root)
        output = root / "next-step-handoff.json"
        script = Path(__file__).resolve().parent / "prepare_source_confirmation_next_step.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                summary["confirmationBrief"]["json"],
                "--summary",
                str(root / "rehearsal" / "source-file-rehearsal-summary.json"),
                "--user-confirmation-text",
                "User confirms package for temporary site execution.",
                "--output",
                str(output),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_source_confirmation_next_step_handoff"
        assert parsed["localCommandReady"] is True
        assert output.exists()
        assert "Wrote source confirmation next-step handoff" not in result.stdout


if __name__ == "__main__":
    test_waiting_confirmation_handoff_without_text_is_non_executable()
    test_waiting_confirmation_handoff_with_text_prepares_local_command()
    test_confirmed_handoff_collects_create_preflight_boundary()
    test_confirmed_with_preflight_handoff_points_to_gated_create_site_runbook()
    test_cli_json_stdout_is_parseable()
    print("source confirmation next-step handoff regression tests passed.")
