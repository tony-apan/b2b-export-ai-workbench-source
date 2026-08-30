#!/usr/bin/env python3
"""Regression tests for applying create preflight evidence to source rehearsals."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_create_preflight_to_source_rehearsal import build
from make_create_preflight_evidence import build_evidence, parse_observed_fields
from test_run_source_file_rehearsal import base_args, refined_target, wiki_for_rehearsal_inventory, write_json
from run_source_file_rehearsal import build as build_rehearsal


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
    return Path(write_json(root / "create-site-preflight.json", preflight))


def new_site_rehearsal(root: Path) -> tuple[dict, Path]:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    args.user_confirmation_text = "User confirms the reviewed package for creating a temporary AllinCMS demo site."
    summary = build_rehearsal(args)
    summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
    return summary, summary_path


def existing_site_rehearsal(root: Path) -> tuple[dict, Path]:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    args.user_confirmation_text = "User confirms the reviewed package for updating an existing AllinCMS demo site."
    args.target_mode = "existing_site"
    args.site_key = "existing-demo-site"
    args.frontend_base_url = "https://existing-demo-site.web.allincms.com"
    summary = build_rehearsal(args)
    summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
    return summary, summary_path


def test_apply_create_preflight_to_source_rehearsal_prepares_create_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rehearsal, rehearsal_path = new_site_rehearsal(root)
        preflight_path = make_preflight(root)
        result = build(
            argparse.Namespace(
                rehearsal_summary=str(rehearsal_path),
                create_preflight=str(preflight_path),
                output_dir=str(root / "create-preflight-apply"),
                output="",
                json=False,
            )
        )
        assert result["localOnly"] is True
        assert result["remoteMutationsPerformed"] is False
        assert result["isRemoteMutationAuthorization"] is False
        assert result["targetMode"] == "new_site"
        assert result["status"] == "create_site_handoff_prepared"
        assert result["readyForBrowserStage"] == "create_site_handoff_ready"
        assert Path(result["artifacts"]["createPreflightConfirmedExecutionApply"]).exists()
        assert Path(result["artifacts"]["confirmedExecutionSummary"]).exists()
        assert Path(result["artifacts"]["sourceExecutionStatus"]).exists()
        assert Path(result["artifacts"]["sourceNextStageHandoff"]).exists()
        assert Path(result["artifacts"]["createSiteHandoff"]).exists()
        assert Path(result["artifacts"]["createSiteHandoffValidation"]).exists()
        assert Path(result["artifacts"]["createSiteRunbook"]).exists()
        assert Path(result["artifacts"]["createSiteRunbookValidation"]).exists()
        assert Path(result["artifacts"]["createdSiteEvidenceBrief"]).exists()
        assert Path(result["artifacts"]["createdSiteEvidenceBundle"]).exists()
        assert Path(result["artifacts"]["createdSiteEvidenceBundleValidation"]).exists()
        assert result["artifacts"]["createdSiteEvidenceTarget"].endswith("created-site-evidence.json")

        runbook = json.loads(Path(result["artifacts"]["createSiteRunbook"]).read_text(encoding="utf-8"))
        handoff = json.loads(Path(result["artifacts"]["createSiteHandoff"]).read_text(encoding="utf-8"))
        source_status = json.loads(Path(result["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(result["artifacts"]["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        assert runbook["browserStepsExecutable"] is False
        assert runbook["remoteMutationsPerformed"] is False
        assert "<paste current user authorization text here>" in handoff["authorizationRecordCommand"]
        assert source_status["currentStage"] == "created_site_binding"
        assert next_stage["currentStage"] == "created_site_binding"
        assert next_stage["browserWorkRequired"] is True
        assert rehearsal["artifacts"]["confirmedSourceNextStageHandoff"]


def test_apply_create_preflight_rejects_existing_site_rehearsal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, rehearsal_path = existing_site_rehearsal(root)
        preflight_path = make_preflight(root)
        try:
            build(
                argparse.Namespace(
                    rehearsal_summary=str(rehearsal_path),
                    create_preflight=str(preflight_path),
                    output_dir=str(root / "create-preflight-apply"),
                    output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "needs_create_site_preflight" in str(exc)
        else:
            raise AssertionError("existing-site rehearsal must not accept create preflight apply")


def test_apply_create_preflight_rejects_unconfirmed_rehearsal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "brief.txt"
        source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
        args = base_args(root, source)
        args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
        summary = build_rehearsal(args)
        summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
        preflight_path = make_preflight(root)
        try:
            build(
                argparse.Namespace(
                    rehearsal_summary=str(summary_path),
                    create_preflight=str(preflight_path),
                    output_dir=str(root / "create-preflight-apply"),
                    output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "confirmationPrepared=true" in str(exc)
        else:
            raise AssertionError("unconfirmed source rehearsal must not accept create preflight apply")
        assert summary["readyForBrowserStage"] == "waiting_for_user_content_confirmation"


if __name__ == "__main__":
    test_apply_create_preflight_to_source_rehearsal_prepares_create_handoff()
    test_apply_create_preflight_rejects_existing_site_rehearsal()
    test_apply_create_preflight_rejects_unconfirmed_rehearsal()
    print("create-preflight source rehearsal apply regression tests passed.")
