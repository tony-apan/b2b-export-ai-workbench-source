#!/usr/bin/env python3
"""Regression tests for source objective coverage summaries."""

from __future__ import annotations

import tempfile
from pathlib import Path

from make_source_objective_coverage import build_coverage
from test_validate_source_run_acceptance import (
    add_taxonomy_validation_to_status,
    complete_handoff,
    complete_status,
    validate_acceptance,
)


def acceptance_report(root: Path, *, omit_batch: bool = False) -> dict:
    status_path, paths = complete_status(root)
    status_path = add_taxonomy_validation_to_status(root, status_path)
    handoff_path = complete_handoff(root, status_path)
    batch_paths = [] if omit_batch else [paths["products_batch_validation"], paths["posts_batch_validation"]]
    return validate_acceptance(
        status_path=status_path,
        next_stage_handoff_path=handoff_path,
        package_path=paths["package"],
        review_packet_path=paths["review_packet"],
        confirmation_path=paths["confirmation"],
        launch_acceptance_path=paths["launch_acceptance"],
        created_site_binding_path=paths["created_site_binding"],
        upload_readiness_path=paths["upload_readiness"],
        sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
        batch_validation_paths=batch_paths,
        forms_media_settings_path=paths["forms_media_settings"],
        final_frontend_audit_path=paths["final_frontend_audit"],
        cleanup_evidence_path=paths["cleanup_evidence"],
        round_closeout_path=paths["round_closeout"],
        source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
        objective="用户给文件后生成 wiki、单页、产品、文章，确认后新建站点并上传验证",
    )


def test_objective_coverage_complete_when_acceptance_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = acceptance_report(Path(tmp))
        coverage = build_coverage(report, acceptance_report_path="/tmp/acceptance.json")
        assert report["accepted"] is True
        assert coverage["complete"] is True
        assert coverage["acceptedByFinalGate"] is True
        assert coverage["missingRequiredIds"] == []
        statuses = {item["id"]: item["status"] for item in coverage["coverage"]}
        assert statuses["source_wiki_ready"] == "proven"
        assert statuses["publishable_package_ready"] == "proven"
        assert statuses["new_site_created_and_bound"] == "proven"
        assert statuses["products_posts_uploaded"] == "proven"
        assert statuses["final_frontend_launch_verified"] == "proven"


def test_objective_coverage_blocks_when_batch_validation_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = acceptance_report(Path(tmp), omit_batch=True)
        coverage = build_coverage(report, acceptance_report_path="/tmp/acceptance.json")
        assert report["accepted"] is False
        assert coverage["complete"] is False
        assert "products_posts_uploaded" in coverage["missingRequiredIds"]
        statuses = {item["id"]: item["status"] for item in coverage["coverage"]}
        assert statuses["products_posts_uploaded"] == "missing"
        blockers = {
            item["id"]: " ".join(item["blockers"])
            for item in coverage["coverage"]
        }
        assert "batch" in blockers["products_posts_uploaded"].lower()


def test_objective_coverage_blocks_when_adversarial_checks_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = acceptance_report(Path(tmp))
        report["adversarialChecks"] = []
        coverage = build_coverage(report, acceptance_report_path="/tmp/acceptance.json")
        assert report["accepted"] is True
        assert coverage["complete"] is False
        assert "adversarial_checks_completed" in coverage["missingRequiredIds"]
        item = next(item for item in coverage["coverage"] if item["id"] == "adversarial_checks_completed")
        assert item["status"] == "missing"
        assert any("adversarialChecks" in blocker for blocker in item["blockers"])


if __name__ == "__main__":
    test_objective_coverage_complete_when_acceptance_passes()
    test_objective_coverage_blocks_when_batch_validation_missing()
    test_objective_coverage_blocks_when_adversarial_checks_missing()
    print("source objective coverage tests passed.")
