#!/usr/bin/env python3
"""Regression tests for applying selected-site evidence to source rehearsals."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_selected_site_to_source_rehearsal import build
from test_bind_created_site_to_artifacts import created_site_evidence, existing_site_evidence
from test_run_source_file_rehearsal import base_args, refined_target, wiki_for_rehearsal_inventory, write_json
from run_source_file_rehearsal import build as build_rehearsal


def existing_site_rehearsal(root: Path) -> tuple[dict, Path]:
    source = root / "brief.txt"
    source.write_text("Brief source text for a product website with product and article ideas.", encoding="utf-8")
    args = base_args(root, source)
    args.refined_source_wiki = write_json(refined_target(root), wiki_for_rehearsal_inventory())
    args.user_confirmation_text = "User confirms the reviewed package for updating an existing AllinCMS demo site."
    args.target_mode = "existing_site"
    args.site_key = "newsite123"
    args.frontend_base_url = "https://newsite123.web.allincms.com"
    summary = build_rehearsal(args)
    summary_path = Path(args.output_dir) / "source-file-rehearsal-summary.json"
    return summary, summary_path


def test_apply_selected_site_to_source_rehearsal_prepares_schema_capture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rehearsal, rehearsal_path = existing_site_rehearsal(root)
        evidence_path = existing_site_evidence(root)
        result = build(
            argparse.Namespace(
                rehearsal_summary=str(rehearsal_path),
                selected_site_evidence=str(evidence_path),
                output_dir=str(root / "selected-site-apply"),
                authorization_dir="",
                theme_target="",
                output="",
                json=False,
            )
        )
        assert result["localOnly"] is True
        assert result["remoteMutationsPerformed"] is False
        assert result["targetMode"] == "existing_site"
        assert result["status"] == "selected_site_bound_schema_capture_prepared"
        assert result["siteKey"] == "newsite123"
        assert result["frontendBaseUrl"] == "https://newsite123.web.allincms.com"
        assert result["readyForBrowserStage"] == "pages_site_info_execution"
        assert Path(result["schemaCaptureSummary"]).exists()
        assert Path(result["artifacts"]["schemaCaptureSummary"]).exists()
        assert Path(result["artifacts"]["createdSiteArtifactBinding"]).exists()
        assert Path(result["artifacts"]["boundArtifactReadiness"]).exists()
        assert Path(result["artifacts"]["schemaCaptureHandoff"]).exists()
        assert Path(result["artifacts"]["pagesSiteInfoHandoff"]).exists()
        assert Path(result["artifacts"]["pagesSiteInfoEvidenceBundle"]).exists()
        assert Path(result["artifacts"]["taxonomyHandoff"]).exists()
        assert Path(result["artifacts"]["taxonomyEvidenceBundle"]).exists()
        assert Path(result["artifacts"]["sourceExecutionStatus"]).exists()
        assert Path(result["artifacts"]["sourceNextStageHandoff"]).exists()

        schema_summary = json.loads(Path(result["schemaCaptureSummary"]).read_text(encoding="utf-8"))
        binding = json.loads(Path(result["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        source_status = json.loads(Path(result["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        schema_handoff = json.loads(Path(result["artifacts"]["schemaCaptureHandoff"]).read_text(encoding="utf-8"))
        assert schema_summary["sourceNextStage"]["currentStage"] == "pages_site_info_execution"
        assert binding["siteBindingMode"] == "existing_site"
        assert binding["siteCreationStatus"] == "existing_site_selected"
        assert schema_handoff["siteBindingMode"] == "existing_site"
        assert source_status["targetMode"] == "existing_site"
        assert "createdSiteSubmittedValues" not in schema_summary
        assert "createdSiteSubmittedValues" not in binding
        assert "createdSiteSubmittedValues" not in source_status
        assert result["sourceExecutionStatus"] == result["artifacts"]["sourceExecutionStatus"]
        assert result["sourceNextStageHandoff"] == result["artifacts"]["sourceNextStageHandoff"]
        for key in ("confirmedConfirmation", "confirmedExecutionPlan", "confirmedArtifactReadiness"):
            assert Path(rehearsal["artifacts"][key]).exists()


def test_apply_selected_site_rejects_created_site_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, rehearsal_path = existing_site_rehearsal(root)
        evidence_path = created_site_evidence(root)
        try:
            build(
                argparse.Namespace(
                    rehearsal_summary=str(rehearsal_path),
                    selected_site_evidence=str(evidence_path),
                    output_dir=str(root / "selected-site-apply"),
                    authorization_dir="",
                    theme_target="",
                    output="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "siteCreation.status must be existing_site_selected" in str(exc)
        else:
            raise AssertionError("created-site evidence must not satisfy selected-site apply helper")


if __name__ == "__main__":
    test_apply_selected_site_to_source_rehearsal_prepares_schema_capture()
    test_apply_selected_site_rejects_created_site_evidence()
    print("selected-site source rehearsal apply regression tests passed.")
