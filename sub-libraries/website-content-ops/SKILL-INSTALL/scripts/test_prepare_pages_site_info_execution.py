#!/usr/bin/env python3
"""Regression tests for pages/site-info execution preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from export_confirmed_site_artifacts import build_artifacts
from prepare_pages_site_info_execution import build
from test_export_confirmed_site_artifacts import prepare_confirmed_plan
from test_validate_run_evidence import created_site_evidence


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def test_prepare_pages_site_info_execution_outputs_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="codex-test-site",
                frontend_base_url="https://codex-test-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        preflight_path = Path(write_json(root / "created-site-evidence.json", created_site_evidence()))
        summary = build(
            argparse.Namespace(
                pages_plan=readiness["artifacts"]["pagesPlan"],
                site_info_plan=readiness["artifacts"]["siteInfoPlan"],
                navigation_plan=readiness["artifacts"]["navigationPlan"],
                preflight=str(preflight_path),
                output_dir=str(root / "pages-site-info"),
                theme_target="",
                json=False,
            )
        )

        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["pageCount"] == 1
        handoff = json.loads(Path(summary["artifacts"]["handoff"]).read_text(encoding="utf-8"))
        assert handoff["kind"] == "allincms_pages_site_info_browser_handoff"
        assert handoff["siteInfo"]["browserStepsExecutable"] is False
        assert handoff["navigation"]["browserStepsExecutable"] is False
        assert handoff["navigation"]["items"]
        assert not handoff["navigation"]["issues"], handoff["navigation"]["issues"]
        assert summary["navigationItemCount"] >= 3
        assert "save_site_settings" in handoff["siteInfo"]["preMutationGateCommand"]
        assert handoff["pages"][0]["browserStepsExecutable"] is False
        assert any(action["action"] == "save_design" for action in handoff["pages"][0]["actions"])
        assert any(action["requiresConcreteTargetBeforeAuthorization"] is True for action in handoff["pages"][0]["actions"])
        assert "<paste current user authorization text here>" in handoff["pages"][0]["actions"][0]["authorizationRecordCommand"]


def test_prepare_pages_site_info_execution_reuses_default_theme_pages_first() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="codex-test-site",
                frontend_base_url="https://codex-test-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        preflight = created_site_evidence()
        preflight["setupPages"]["themes"] = [
            "themes page shows Default active starter theme, create theme control, pages/design/preview controls, and 7 pages"
        ]
        preflight["setupPages"]["routes"] = [
            "routes page shows default routes /home /about-us /contact-us /posts /products, bound page, status, notes, updated time"
        ]
        preflight_path = Path(write_json(root / "created-site-evidence.json", preflight))
        summary = build(
            argparse.Namespace(
                pages_plan=readiness["artifacts"]["pagesPlan"],
                site_info_plan=readiness["artifacts"]["siteInfoPlan"],
                navigation_plan=readiness["artifacts"]["navigationPlan"],
                preflight=str(preflight_path),
                output_dir=str(root / "pages-site-info"),
                theme_target="",
                json=False,
            )
        )
        handoff = json.loads(Path(summary["artifacts"]["handoff"]).read_text(encoding="utf-8"))
        assert handoff["defaultTemplateState"]["reuseExistingPagesFirst"] is True
        assert handoff["defaultTemplateState"]["defaultTemplateDetected"] is True
        assert handoff["pages"][0]["executionStrategy"] == "reuse_existing_theme_page_first"
        action_names = [action["action"] for action in handoff["pages"][0]["actions"]]
        assert "create_theme_page" not in action_names
        assert "save_design" in action_names
        assert all(action["existingPageReuse"] is True for action in handoff["pages"][0]["actions"])


def test_prepare_pages_site_info_execution_blocks_missing_navigation_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
        readiness = build_artifacts(
            argparse.Namespace(
                package=str(package_path),
                confirmation=str(confirmation_path),
                execution_plan=str(plan_path),
                site_key="codex-test-site",
                frontend_base_url="https://codex-test-site.web.allincms.com",
                output_dir=str(root / "artifacts"),
                json=False,
            )
        )
        preflight_path = Path(write_json(root / "created-site-evidence.json", created_site_evidence()))
        summary = build(
            argparse.Namespace(
                pages_plan=readiness["artifacts"]["pagesPlan"],
                site_info_plan=readiness["artifacts"]["siteInfoPlan"],
                navigation_plan="",
                preflight=str(preflight_path),
                output_dir=str(root / "pages-site-info"),
                theme_target="",
                json=False,
            )
        )
        handoff = json.loads(Path(summary["artifacts"]["handoff"]).read_text(encoding="utf-8"))
        assert summary["readyForBrowserStage"] == "blocked_navigation_plan"
        assert handoff["navigation"]["issues"]


if __name__ == "__main__":
    test_prepare_pages_site_info_execution_outputs_handoff()
    test_prepare_pages_site_info_execution_reuses_default_theme_pages_first()
    test_prepare_pages_site_info_execution_blocks_missing_navigation_plan()
    print("pages/site-info execution preparation regression tests passed.")
