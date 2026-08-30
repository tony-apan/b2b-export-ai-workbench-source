#!/usr/bin/env python3
"""Regression tests for applying create-site preflight to confirmed execution."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_create_preflight_to_confirmed_execution import build, validate_apply_result
from apply_source_confirmation_next_step import apply_handoff as apply_source_confirmation
from make_create_preflight_evidence import build_evidence, parse_observed_fields
from prepare_source_confirmation_next_step import build_handoff as build_next_step_handoff
from test_prepare_source_confirmation_next_step import handoff_args, make_summary


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def make_preflight(root: Path) -> Path:
    preflight = build_evidence(
        ["abc123demo"],
        parse_observed_fields(
            "observed create site entry button 创建站点;observed dialog title 创建站点;"
            "name input;description textarea;submit 创建;close Close"
        ),
        dialog_closed_verified=True,
        repo_check_passed=True,
        repo_check_note=None,
        generated_at="2026-07-02T00:00:00+00:00",
        site_key_evidence={"abc123demo": "backend URL https://workspace.laicms.com/abc123demo/dashboard"},
    )
    return write_json(root / "create-site-preflight.json", preflight)


def make_empty_site_list_preflight(root: Path) -> Path:
    preflight = build_evidence(
        [],
        parse_observed_fields(
            "observed create site entry button 创建站点;observed dialog title 创建站点;"
            "name input;description textarea;submit 创建;close Close"
        ),
        dialog_closed_verified=True,
        repo_check_passed=True,
        repo_check_note=None,
        generated_at="2026-07-02T00:00:00+00:00",
        empty_site_list_evidence="verified empty /sites list from safe DOM route inspection",
    )
    return write_json(root / "create-site-preflight-empty.json", preflight)


def make_apply_result(root: Path) -> Path:
    summary = make_summary(root)
    next_step = build_next_step_handoff(
        handoff_args(
            root,
            summary,
            user_confirmation_text="User confirms package for temporary site execution.",
        )
    )
    next_step_path = write_json(root / "next-step-handoff.json", next_step)
    apply_result = apply_source_confirmation(
        argparse.Namespace(
            handoff=str(next_step_path),
            output_dir=str(root / "apply"),
            output=str(root / "apply" / "apply-result.json"),
            json=False,
        )
    )
    return write_json(root / "apply" / "apply-result.json", apply_result)


def test_apply_preflight_prepares_create_site_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_apply_result(root)
        preflight = make_preflight(root)
        result = build(
            argparse.Namespace(
                apply_result=str(apply_result),
                create_preflight=str(preflight),
                output_dir=str(root / "with-preflight"),
                output=str(root / "with-preflight" / "apply-result.json"),
                json=False,
            )
        )
        assert result["localOnly"] is True
        assert result["remoteMutationsPerformed"] is False
        assert result["isRemoteMutationAuthorization"] is False
        assert result["status"] == "create_site_handoff_prepared"
        assert result["readyForBrowserStage"] == "create_site_handoff_ready"
        assert Path(result["artifacts"]["createSiteHandoff"]).exists()
        assert Path(result["artifacts"]["createSiteRunbook"]).exists()
        assert Path(result["artifacts"]["createdSiteEvidenceBundle"]).exists()
        assert Path(result["artifacts"]["sourceNextStageHandoff"]).exists()
        assert "<paste current user authorization text here>" in Path(
            result["artifacts"]["createSiteHandoff"]
        ).read_text(encoding="utf-8")
        runbook = json.loads(Path(result["artifacts"]["createSiteRunbook"]).read_text(encoding="utf-8"))
        assert runbook["browserStepsExecutable"] is False
        assert not validate_apply_result(result)


def test_apply_preflight_accepts_verified_empty_site_list() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_apply_result(root)
        preflight = make_empty_site_list_preflight(root)
        result = build(
            argparse.Namespace(
                apply_result=str(apply_result),
                create_preflight=str(preflight),
                output_dir=str(root / "with-empty-preflight"),
                output=str(root / "with-empty-preflight" / "apply-result.json"),
                json=False,
            )
        )
        assert result["readyForBrowserStage"] == "create_site_handoff_ready"
        assert Path(result["artifacts"]["createSiteHandoff"]).exists()
        assert not validate_apply_result(result)


def test_apply_preflight_accepts_source_next_stage_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_apply_result(root)
        apply_data = json.loads(apply_result.read_text(encoding="utf-8"))
        handoff_path = Path(apply_data["artifacts"]["sourceNextStageHandoff"])
        preflight = make_preflight(root)
        result = build(
            argparse.Namespace(
                apply_result=str(handoff_path),
                create_preflight=str(preflight),
                output_dir=str(root / "with-handoff-input"),
                output=str(root / "with-handoff-input" / "apply-result.json"),
                json=False,
            )
        )
        assert result["readyForBrowserStage"] == "create_site_handoff_ready"
        assert Path(result["artifacts"]["createSiteHandoff"]).exists()
        assert Path(result["artifacts"]["createSiteRunbook"]).exists()
        assert Path(result["artifacts"]["createdSiteEvidenceBundle"]).exists()
        assert not validate_apply_result(result)


def test_rejects_non_preflight_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_apply_result(root)
        bad_preflight = write_json(
            root / "bad-preflight.json",
            {
                "completionClaimed": False,
                "mode": "read_only_simulation",
                "siteCreation": {"status": "created_verified"},
            },
        )
        try:
            build(
                argparse.Namespace(
                    apply_result=str(apply_result),
                    create_preflight=str(bad_preflight),
                    output_dir=str(root / "with-preflight"),
                    output=str(root / "with-preflight" / "apply-result.json"),
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "create_preflight_verified" in str(exc)
        else:
            raise AssertionError("non-preflight evidence was accepted")


if __name__ == "__main__":
    test_apply_preflight_prepares_create_site_handoff()
    test_apply_preflight_accepts_verified_empty_site_list()
    test_apply_preflight_accepts_source_next_stage_handoff()
    test_rejects_non_preflight_evidence()
    print("create preflight apply regression tests passed.")
