#!/usr/bin/env python3
"""Regression tests for pre-browser source review objective coverage."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from make_source_package_review_packet import build_review_packet
from make_source_review_objective_coverage import build_coverage
from test_source_confirmation_execution_plan import make_package, write_json


def build_packet(root: Path) -> tuple[Path, Path, dict]:
    package_path = make_package(root)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    review_path = root / "source-package-review-packet.json"
    packet = build_review_packet(
        package,
        str(package_path),
        generated_at="2026-07-01T00:00:00+00:00",
        review_packet_path=str(review_path),
    )
    write_json(review_path, packet)
    return package_path, review_path, packet


def test_review_objective_coverage_is_review_ready_but_not_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path, packet = build_packet(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        coverage = build_coverage(
            packet,
            review_packet_path=str(review_path),
            package=package,
            package_path=str(package_path),
            objective="source files to confirmed AllinCMS site with pages, products, posts, and launch proof",
        )
        assert coverage["kind"] == "allincms_source_review_objective_coverage"
        assert coverage["reviewComplete"] is True
        assert coverage["complete"] is False
        assert coverage["remoteMutationAllowed"] is False
        assert coverage["readyForBrowserStage"] == "waiting_for_user_content_confirmation"
        assert coverage["missingForReview"] == []
        assert "remote_site_creation_not_started" in coverage["missingForFinal"]
        statuses = {item["id"]: item["status"] for item in coverage["coverage"]}
        assert statuses["source_wiki_ready"] == "proven"
        assert statuses["publishable_package_review_ready"] == "proven"
        assert statuses["user_confirmation_needed"] == "pending_user_confirmation"
        assert statuses["sample_batch_upload_not_started"] == "not_started"
        assert coverage["counts"]["pages"] == 1
        assert coverage["counts"]["products"] == 1
        assert coverage["counts"]["posts"] == 1
        assert coverage["counts"]["sourceInputFiles"] == 1
        assert any("not user authorization" in item for item in coverage["adversarialChecks"])


def test_review_objective_coverage_blocks_on_packet_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path, review_path, packet = build_packet(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packet["contentGoalCoverage"]["checks"]["posts"] = False
        packet["contentGoalCoverage"]["missing"] = ["posts"]
        coverage = build_coverage(
            packet,
            review_packet_path=str(review_path),
            package=package,
            package_path=str(package_path),
        )
        assert coverage["reviewComplete"] is False
        assert coverage["readyForBrowserStage"] == "needs_source_package_repair"
        assert "publishable_package_review_ready" in coverage["missingForReview"]
        assert any("contentGoalCoverage" in issue for issue in coverage["reviewPacketValidationIssues"])


def test_review_objective_coverage_allows_visible_overage_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = make_package(root)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["declaredContentGoals"] = {
            **package.get("declaredContentGoals", {}),
            "posts": 0,
        }
        review_path = root / "source-package-review-packet.json"
        packet = build_review_packet(
            package,
            str(package_path),
            generated_at="2026-07-01T00:00:00+00:00",
            review_packet_path=str(review_path),
        )
        write_json(review_path, packet)
        coverage = build_coverage(
            packet,
            review_packet_path=str(review_path),
            package=package,
            package_path=str(package_path),
        )
        assert coverage["reviewComplete"] is True
        assert coverage["contentGoalOverages"]["present"] is True
        assert coverage["contentGoalOverages"]["details"]["posts"]["extraCount"] == 1
        assert "exceeds_declared_content_goal:posts" in coverage["contentQualityReview"]["warnings"]
        assert coverage["reviewPacketValidationIssues"] == []


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("source review objective coverage tests passed.")
