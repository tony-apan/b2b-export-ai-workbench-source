#!/usr/bin/env python3
"""Regression tests for source-file rehearsal summary validation."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from run_source_file_rehearsal import build
from test_run_source_file_rehearsal import (
    base_args,
    make_preflight,
    refined_target,
    wiki_for_rehearsal_inventory,
    write_json,
)
from validate_source_file_rehearsal import validate_summary


def review_ready_summary(root: Path) -> dict:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    return build(args)


def confirmed_summary(root: Path) -> dict:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
    args.create_preflight = str(make_preflight(root))
    return build(args)


def confirmed_summary_needing_create_preflight(root: Path) -> dict:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    args.user_confirmation_text = "User confirms the reviewed package for a temporary AllinCMS demo site."
    return build(args)


def test_validate_review_ready_rehearsal_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        assert not validate_summary(summary, summary_path)


def test_validate_confirmed_rehearsal_summary_with_create_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = confirmed_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        assert summary["readyForBrowserStage"] == "create_site_handoff_ready"
        assert not validate_summary(summary, summary_path)

        drifted = copy.deepcopy(summary)
        drifted["artifacts"]["confirmedCreateSiteHandoffValidation"] = ""
        issues = validate_summary(drifted, summary_path)
        assert "artifacts.confirmedCreateSiteHandoffValidation is required" in issues

        drifted = copy.deepcopy(summary)
        validation_path = Path(drifted["artifacts"]["confirmedCreateSiteRunbookValidation"])
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        validation["runbook"] = str(root / "wrong-runbook.json")
        validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        issues = validate_summary(drifted, summary_path)
        assert any("runbook validation must bind" in issue for issue in issues)


def test_validate_confirmed_rehearsal_summary_needing_create_preflight() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = confirmed_summary_needing_create_preflight(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        assert summary["readyForBrowserStage"] == "needs_create_site_preflight"
        assert not validate_summary(summary, summary_path)

        drifted = copy.deepcopy(summary)
        drifted["artifacts"]["confirmedCreateSitePreflightBriefValidation"] = ""
        issues = validate_summary(drifted, summary_path)
        assert "artifacts.confirmedCreateSitePreflightBriefValidation is required" in issues


def test_validator_rejects_review_packet_and_objective_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"

        drifted = copy.deepcopy(summary)
        drifted["confirmationReview"]["reviewPacket"] = str(root / "wrong-review-packet.json")
        issues = validate_summary(drifted, summary_path)
        assert "confirmationReview.reviewPacket must match artifacts.reviewPacket" in issues

        drifted = copy.deepcopy(summary)
        drifted["objectiveAudit"]["nextBlockingRequirement"] = "batch upload/publish and launch QA complete"
        issues = validate_summary(drifted, summary_path)
        assert "objectiveAudit.nextBlockingRequirement must match the first incomplete objective check" in issues


def test_validator_rejects_stale_current_next_stage_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"

        drifted = copy.deepcopy(summary)
        drifted["artifacts"]["sourceNextStageHandoff"] = drifted["artifacts"]["initialSourceNextStageHandoff"]
        issues = validate_summary(drifted, summary_path)
        assert "artifacts.sourceNextStageHandoff must point to current stage confirmation" in issues
        assert "artifacts.sourceNextStageHandoff must use refinedSourceNextStageHandoff after refinement" in issues


def test_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        review_ready_summary(root)
        summary_path = root / "rehearsal" / "source-file-rehearsal-summary.json"
        output_path = root / "validation.json"
        script = Path(__file__).resolve().parent / "validate_source_file_rehearsal.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(summary_path),
                "--output",
                str(output_path),
                "--fail-on-invalid",
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_source_file_rehearsal_validation"
        assert parsed["ok"] is True
        assert parsed["summary"] == str(summary_path.resolve())
        assert output_path.exists()
        assert json.loads(output_path.read_text(encoding="utf-8"))["ok"] is True


if __name__ == "__main__":
    test_validate_review_ready_rehearsal_summary()
    test_validate_confirmed_rehearsal_summary_with_create_handoff()
    test_validate_confirmed_rehearsal_summary_needing_create_preflight()
    test_validator_rejects_review_packet_and_objective_drift()
    test_validator_rejects_stale_current_next_stage_handoff()
    test_cli_json_stdout_is_parseable()
    print("source-file rehearsal validation regression tests passed.")
