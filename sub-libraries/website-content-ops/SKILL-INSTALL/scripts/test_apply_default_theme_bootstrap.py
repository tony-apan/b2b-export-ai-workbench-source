#!/usr/bin/env python3
"""Regression tests for applying default-theme bootstrap evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_default_theme_bootstrap import build as apply_bootstrap
from prepare_default_theme_bootstrap import build as build_runbook
from test_prepare_created_site_schema_capture import prepare_artifacts
from test_default_theme_bootstrap import valid_evidence
from test_validate_run_evidence import created_site_evidence
from validate_run_evidence import validate as validate_run_evidence


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def build_valid_run(root: Path) -> tuple[str, str, str]:
    created = created_site_evidence()
    site_key = created["siteIdentity"]["siteKey"]
    created_path = write_json(root / "created-site-evidence.json", created)
    runbook_summary = build_runbook(
        argparse.Namespace(
            preflight=created_path,
            output=str(root / "default-theme-runbook.json"),
            theme_name="Default Launch Theme",
            json=False,
        )
    )
    evidence_path = write_json(root / "default-theme-evidence.json", valid_evidence(site_key))
    return created_path, runbook_summary["runbook"], evidence_path


def test_apply_default_theme_bootstrap_writes_refreshed_created_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created_path, runbook_path, evidence_path = build_valid_run(root)
        summary = apply_bootstrap(
            argparse.Namespace(
                created_site_evidence=created_path,
                runbook=runbook_path,
                bootstrap_evidence=evidence_path,
                output_dir=str(root / "applied"),
                prepare_created_site_schema_capture=False,
                artifact_readiness="",
                package="",
                review_packet="",
                confirmation="",
                execution_plan="",
                authorization_dir="",
                theme_target="",
                fail_on_invalid=True,
                json=False,
            )
        )
        assert summary["validationValid"] is True, summary
        refreshed_path = Path(summary["artifacts"]["createdSiteEvidenceAfterDefaultThemeBootstrap"])
        refreshed = json.loads(refreshed_path.read_text(encoding="utf-8"))
        assert not validate_run_evidence(refreshed)
        assert refreshed["defaultThemeBootstrap"]["businessContentComplete"] is False
        assert "frontendRendering" in refreshed
        assert "launchReadiness" in refreshed
        assert "default-theme bootstrap validated" in " ".join(refreshed["setupPages"]["themes"])
        assert "default-theme bootstrap routes bound" in " ".join(refreshed["setupPages"]["routes"])
        assert summary["downstreamPreparation"]["requested"] is False
        assert summary["downstreamPreparation"]["ran"] is False


def test_apply_default_theme_bootstrap_can_prepare_created_site_schema_capture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created_path, runbook_path, evidence_path = build_valid_run(root)
        package_path, confirmation_path, plan_path, readiness_path = prepare_artifacts(root)
        summary = apply_bootstrap(
            argparse.Namespace(
                created_site_evidence=created_path,
                runbook=runbook_path,
                bootstrap_evidence=evidence_path,
                output_dir=str(root / "applied"),
                prepare_created_site_schema_capture=True,
                artifact_readiness=str(readiness_path),
                package=str(package_path),
                review_packet="",
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                authorization_dir="",
                theme_target="",
                fail_on_invalid=True,
                json=False,
            )
        )
        assert summary["validationValid"] is True, summary
        assert summary["downstreamPreparation"]["requested"] is True
        assert summary["downstreamPreparation"]["ran"] is True
        assert Path(summary["artifacts"]["createdSiteSchemaCapturePreparation"]).exists()
        assert Path(summary["artifacts"]["sourceExecutionStatus"]).exists()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        refreshed = json.loads(Path(summary["artifacts"]["createdSiteEvidenceAfterDefaultThemeBootstrap"]).read_text(encoding="utf-8"))
        schema_summary = json.loads(Path(summary["artifacts"]["createdSiteSchemaCapturePreparation"]).read_text(encoding="utf-8"))
        assert schema_summary["artifacts"]["sourceExecutionStatus"] == summary["artifacts"]["sourceExecutionStatus"]
        binding = json.loads(Path(schema_summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        assert binding["siteKey"] == refreshed["siteIdentity"]["siteKey"]


def test_apply_default_theme_bootstrap_rejects_wrong_site_key() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created_path, runbook_path, _ = build_valid_run(root)
        bad = valid_evidence("other-site-key")
        evidence_path = write_json(root / "bad-default-theme-evidence.json", bad)
        summary = apply_bootstrap(
            argparse.Namespace(
                created_site_evidence=created_path,
                runbook=runbook_path,
                bootstrap_evidence=evidence_path,
                output_dir=str(root / "applied"),
                prepare_created_site_schema_capture=False,
                artifact_readiness="",
                package="",
                review_packet="",
                confirmation="",
                execution_plan="",
                authorization_dir="",
                theme_target="",
                fail_on_invalid=False,
                json=False,
            )
        )
        assert summary["validationValid"] is False, summary
        assert summary["artifacts"]["createdSiteEvidenceAfterDefaultThemeBootstrap"] == ""
        assert any("siteKey" in issue for issue in summary["validation"]["issues"]), summary


def test_apply_default_theme_bootstrap_rejects_incomplete_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created_path, runbook_path, evidence_path = build_valid_run(root)
        evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        evidence["pageCount"] = 0
        incomplete_path = write_json(root / "incomplete-evidence.json", evidence)
        summary = apply_bootstrap(
            argparse.Namespace(
                created_site_evidence=created_path,
                runbook=runbook_path,
                bootstrap_evidence=incomplete_path,
                output_dir=str(root / "applied"),
                prepare_created_site_schema_capture=False,
                artifact_readiness="",
                package="",
                review_packet="",
                confirmation="",
                execution_plan="",
                authorization_dir="",
                theme_target="",
                fail_on_invalid=False,
                json=False,
            )
        )
        assert summary["validationValid"] is False, summary
        assert any("pageCount" in issue for issue in summary["validation"]["issues"]), summary


if __name__ == "__main__":
    test_apply_default_theme_bootstrap_writes_refreshed_created_evidence()
    test_apply_default_theme_bootstrap_can_prepare_created_site_schema_capture()
    test_apply_default_theme_bootstrap_rejects_wrong_site_key()
    test_apply_default_theme_bootstrap_rejects_incomplete_evidence()
    print("apply default-theme bootstrap regression tests passed.")
