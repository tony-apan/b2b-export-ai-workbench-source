#!/usr/bin/env python3
"""Regression tests for applying source confirmation next-step handoffs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from apply_source_confirmation_next_step import apply_handoff, validate_apply_result
from prepare_source_confirmation_next_step import build_handoff as build_next_step_handoff
from test_prepare_source_confirmation_next_step import handoff_args, make_summary


def apply_args(root: Path, handoff_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        handoff=str(handoff_path),
        output_dir=str(root / "apply"),
        output=str(root / "apply" / "apply-result.json"),
        json=False,
    )


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_apply_prepares_confirmed_execution_from_next_step_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root)
        handoff = build_next_step_handoff(
            handoff_args(
                root,
                summary,
                user_confirmation_text="User confirms package for temporary site execution.",
            )
        )
        handoff_path = write_json(root / "next-step-handoff.json", handoff)
        result = apply_handoff(apply_args(root, handoff_path))
        assert result["status"] == "local_confirmed_execution_prepared"
        assert result["appliedConfirmedExecution"] is True
        assert result["remoteMutationsPerformed"] is False
        assert result["isRemoteMutationAuthorization"] is False
        assert Path(result["confirmedExecutionSummary"]).exists()
        assert Path(result["sourceExecutionStatus"]).exists()
        assert Path(result["sourceNextStageHandoff"]).exists()
        assert result["artifacts"]["confirmedExecutionSummary"] == result["confirmedExecutionSummary"]
        assert result["artifacts"]["sourceExecutionStatus"] == result["sourceExecutionStatus"]
        assert result["artifacts"]["sourceNextStageHandoff"] == result["sourceNextStageHandoff"]
        assert Path(result["artifacts"]["confirmation"]).exists()
        assert Path(result["artifacts"]["executionPlan"]).exists()
        assert Path(result["artifacts"]["artifactReadiness"]).exists()
        assert result["artifacts"]["createSitePreflightBrief"].endswith("create-site-preflight-brief.json")
        assert result["artifacts"]["createSitePreflightTarget"].endswith("create-site-preflight.json")
        confirmed = json.loads(Path(result["confirmedExecutionSummary"]).read_text(encoding="utf-8"))
        assert confirmed["readyForBrowserStage"] == "needs_create_site_preflight"
        assert confirmed["artifacts"]["confirmation"]
        assert confirmed["artifacts"]["createSitePreflightTarget"].endswith("create-site-preflight.json")
        assert not validate_apply_result(result)


def test_apply_does_not_execute_browser_boundary_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root, confirmed=True)
        handoff = build_next_step_handoff(handoff_args(root, summary))
        handoff_path = write_json(root / "next-step-handoff.json", handoff)
        result = apply_handoff(apply_args(root, handoff_path))
        assert result["status"] == "browser_boundary_not_applied"
        assert result["appliedConfirmedExecution"] is False
        assert result["browserBoundary"]["readOnly"] is True
        assert result["browserBoundary"]["targetEvidence"] == summary["artifacts"]["confirmedCreateSitePreflightTarget"]
        assert result["artifacts"]["handoff"] == str(handoff_path.resolve())
        assert result["artifacts"]["browserBoundaryTargetEvidence"] == summary["artifacts"]["confirmedCreateSitePreflightTarget"]
        assert result["artifacts"]["sourceExecutionStatus"] == ""
        assert not validate_apply_result(result)


def test_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = make_summary(root)
        handoff = build_next_step_handoff(
            handoff_args(
                root,
                summary,
                user_confirmation_text="User confirms package for temporary site execution.",
            )
        )
        handoff_path = write_json(root / "next-step-handoff.json", handoff)
        output = root / "apply" / "apply-result.json"
        script = Path(__file__).resolve().parent / "apply_source_confirmation_next_step.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(handoff_path),
                "--output-dir",
                str(root / "apply"),
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
        assert parsed["kind"] == "allincms_source_confirmation_next_step_apply"
        assert parsed["status"] == "local_confirmed_execution_prepared"
        assert output.exists()
        assert "Wrote source confirmation next-step apply result" not in result.stdout


if __name__ == "__main__":
    test_apply_prepares_confirmed_execution_from_next_step_handoff()
    test_apply_does_not_execute_browser_boundary_handoff()
    test_cli_json_stdout_is_parseable()
    print("source confirmation next-step apply regression tests passed.")
