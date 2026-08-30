#!/usr/bin/env python3
"""Regression tests for applying launch acceptance evidence."""

from __future__ import annotations

import sys

import argparse
import json
import tempfile
from pathlib import Path

from apply_launch_acceptance import build
from test_apply_batch_upload_publish import batch_evidence
from test_summarize_source_execution_status import (
    confirmation,
    confirmation_decision_matrix,
    content_goal_coverage,
    content_quality_review,
    created_site_binding,
    execution_plan,
    package,
    pages_site_info_handoff,
    pages_site_info_validation,
    review_packet,
    schema_capture_handoff,
    wiki_review,
)
from test_validate_source_run_acceptance import (
    cleanup_evidence,
    content_counts,
    counted_batch_validation,
    counted_pages_site_info_validation,
    final_frontend_audit,
    frontend_audit_inputs_summary,
    frontend_audit_report,
    frontend_expected_statuses,
    full_batch_evidence,
    full_sample_evidence,
    manifest,
    maintenance_round_closeout,
    round_closeout as final_round_closeout,
    source_wiki,
    upload_readiness_with_manifest_paths,
)
from make_final_frontend_audit_stage_result import url_fingerprint
from test_manifest_sample_upload import content_goal_overages, created_site_submitted_values, overage_quality
from test_validate_run_evidence import (
    launch_cleanup_evidence,
    launch_final_frontend_audit_result,
    launch_forms_media_settings_out_of_scope,
    launch_module_coverage,
    launch_ready_run_evidence,
)


def write_json(path: Path, data: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def artifact_readiness() -> dict:
    return {
        "kind": "allincms_confirmed_site_artifact_readiness",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "contentGoalCoverage": content_goal_coverage(),
        "contentCounts": content_counts(),
        "contentQualityReview": overage_quality(),
        "contentGoalOverages": content_goal_overages(),
        "draftManifestStatus": {
            "products": {"itemCount": 2, "schemaVerified": False},
            "posts": {"itemCount": 0, "schemaVerified": False},
        },
    }


def round_closeout() -> dict:
    return final_round_closeout()


def base_args(root: Path, *, missing_final_audit: bool = False) -> argparse.Namespace:
    source_wiki_path, _source_wiki_index = source_wiki(root)
    review = {
        "sourceWiki": source_wiki_path,
        "sourceWikiMarkdown": _source_wiki_index,
        "sourceWikiMarkdownIndex": _source_wiki_index,
    }
    package_data = package()
    package_data["sourceWiki"] = source_wiki_path
    package_data["wikiReview"] = review
    package_data["contentQualityReview"] = overage_quality()
    package_data["contentGoalOverages"] = content_goal_overages()
    package_path = write_json(root / "package.json", package_data)
    review_packet_data = review_packet(package_path)
    review_packet_data["wikiReview"] = review
    review_packet_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    review_packet_data["contentCounts"] = content_counts()
    review_packet_data["contentQualityReview"] = overage_quality()
    review_packet_data["contentGoalOverages"] = content_goal_overages()
    review_path = write_json(root / "review-packet.json", review_packet_data)
    confirmation_data = confirmation()
    confirmation_data["sourceReviewPacket"] = review_path
    confirmation_data["wikiReview"] = review
    confirmation_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    confirmation_data["contentCounts"] = content_counts()
    confirmation_data["contentQualityReview"] = overage_quality()
    confirmation_data["contentGoalOverages"] = content_goal_overages()
    execution_plan_data = execution_plan()
    execution_plan_data["wikiReview"] = review
    execution_plan_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    execution_plan_data["contentCounts"] = content_counts()
    execution_plan_data["contentQualityReview"] = overage_quality()
    execution_plan_data["contentGoalOverages"] = content_goal_overages()
    artifact_readiness_data = artifact_readiness()
    artifact_readiness_data["wikiReview"] = review
    artifact_readiness_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    created_site_binding_data = created_site_binding()
    created_site_binding_data["wikiReview"] = review
    created_site_binding_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    created_site_binding_data["contentCounts"] = content_counts()
    created_site_binding_data["contentQualityReview"] = overage_quality()
    created_site_binding_data["contentGoalOverages"] = content_goal_overages()
    created_site_binding_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    schema_capture_handoff_data = schema_capture_handoff()
    schema_capture_handoff_data["wikiReview"] = review
    schema_capture_handoff_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    schema_capture_handoff_data["contentQualityReview"] = overage_quality()
    schema_capture_handoff_data["contentGoalOverages"] = content_goal_overages()
    forms_media_settings_data = launch_forms_media_settings_out_of_scope()
    forms_media_settings_data["wikiReview"] = review
    forms_media_settings_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    forms_media_settings_data["contentCounts"] = content_counts()
    forms_media_settings_data["contentQualityReview"] = overage_quality()
    forms_media_settings_data["contentGoalOverages"] = content_goal_overages()
    forms_media_settings_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    forms_media_settings_data["deferrals"].append(
        {"module": "media", "reason": "media upload proof is explicitly deferred for this temporary launch"}
    )
    forms_media_settings_data["deferrals"].append(
        {"module": "site-info", "reason": "site information field proof is explicitly deferred for this temporary launch"}
    )
    products_manifest = write_json(root / "products-manifest.json", manifest("products"))
    posts_manifest = write_json(root / "posts-manifest.json", manifest("posts"))
    products_batch_evidence = write_json(root / "products-batch-evidence.json", full_batch_evidence("products"))
    posts_batch_evidence = write_json(root / "posts-batch-evidence.json", full_batch_evidence("posts"))
    frontend_audit_report_path = root / "final-frontend-audit-report.json"
    frontend_audit_report_path.write_text(json.dumps(frontend_audit_report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frontend_audit_inputs_summary_path = write_json(root / "final-frontend-audit-inputs-summary.json", frontend_audit_inputs_summary())
    frontend_expected_statuses_path = write_json(root / "final-frontend-expected-statuses.json", frontend_expected_statuses())
    final_frontend_audit_data = final_frontend_audit()
    final_frontend_audit_data["proof"] = list(final_frontend_audit_data["proofRecorded"])
    final_frontend_audit_data["redactedEvidencePointers"] = [str(frontend_audit_report_path)]
    final_frontend_audit_data["auditReport"] = str(frontend_audit_report_path)
    final_frontend_audit_data["auditInputsSummary"] = frontend_audit_inputs_summary_path
    final_frontend_audit_data["expectedStatuses"] = frontend_expected_statuses_path
    final_frontend_audit_data["contentGoalCoverage"] = content_goal_coverage()
    final_frontend_audit_data["contentCounts"] = content_counts()
    final_frontend_audit_data["contentQualityReview"] = overage_quality()
    final_frontend_audit_data["contentGoalOverages"] = content_goal_overages()
    final_frontend_audit_data["wikiReview"] = review
    final_frontend_audit_data["confirmationDecisionMatrix"] = confirmation_decision_matrix()
    final_frontend_audit_data["createdSiteSubmittedValues"] = created_site_submitted_values()
    return argparse.Namespace(
        run_evidence=write_json(root / "run-evidence.json", launch_ready_run_evidence()),
        module_coverage=write_json(root / "module-coverage.json", launch_module_coverage()),
        stage_coverage="",
        upload_readiness=write_json(root / "upload-readiness.json", upload_readiness_with_manifest_paths(products_manifest, posts_manifest)),
        batch_evidence=write_json(root / "batch-evidence.json", batch_evidence()),
        batch_validation=[
            write_json(root / "products-batch-validation.json", counted_batch_validation("products", evidence=products_batch_evidence, manifest_path=products_manifest)),
            write_json(root / "posts-batch-validation.json", counted_batch_validation("posts", evidence=posts_batch_evidence, manifest_path=posts_manifest)),
        ],
        forms_media_settings=write_json(root / "forms-media-settings.json", forms_media_settings_data),
        final_frontend_audit=""
        if missing_final_audit
        else write_json(root / "final-frontend-audit.json", final_frontend_audit_data),
        cleanup_evidence=write_json(root / "cleanup-evidence.json", cleanup_evidence()),
        round_closeout="",
        auto_final_closeout=True,
        final_closeout_output="",
        final_closeout_sedimentation="updated",
        final_closeout_sedimentation_note="Recorded final launch proof.",
        require_created_site=True,
        package=package_path,
        review_packet="",
        confirmation=write_json(root / "confirmation.json", confirmation_data),
        execution_plan=write_json(root / "execution-plan.json", execution_plan_data),
        artifact_readiness=write_json(root / "artifact-readiness.json", artifact_readiness_data),
        created_site_binding=write_json(root / "created-site-binding.json", created_site_binding_data),
        pages_site_info_handoff=write_json(root / "pages-site-info-handoff.json", pages_site_info_handoff()),
        pages_site_info_evidence="",
        pages_site_info_validation=write_json(root / "pages-site-info-validation.json", counted_pages_site_info_validation()),
        taxonomy_handoff="",
        taxonomy_evidence="",
        taxonomy_validation="",
        schema_capture_handoff=write_json(root / "schema-capture-handoff.json", schema_capture_handoff_data),
        sample_evidence=[
            write_json(root / "products-sample-evidence.json", full_sample_evidence("products", products_manifest)),
            write_json(root / "posts-sample-evidence.json", full_sample_evidence("posts", posts_manifest)),
        ],
        output_dir=str(root / "apply-launch"),
        fail_on_invalid=False,
        json=False,
    )


def test_apply_launch_acceptance_advances_source_status_to_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root))
        assert summary["validationValid"] is True
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        assert Path(summary["artifacts"]["sourceRunAcceptance"]).exists()
        assert summary["sourceNextStage"]["currentStage"] == "complete"
        assert summary["contentGoalCoverage"]["complete"] is True
        assert summary["contentCounts"] == content_counts()
        assert summary["contentQualityReview"] == overage_quality()
        assert summary["contentGoalOverages"] == content_goal_overages()
        assert summary["wikiReview"]["sourceWikiMarkdownIndex"].endswith("/wiki/index.md")
        assert summary["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert summary["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert summary["sourceRunAcceptance"]["accepted"] is True
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["complete"] is True, status
        assert status["currentStage"] == "complete", status
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        assert validation["valid"] is True
        assert validation["complete"] is True
        assert validation["sampleEvidenceCount"] == 2
        assert validation["batchValidationCount"] == 2
        assert validation["contentGoalCoverage"]["complete"] is True
        assert validation["contentCounts"] == content_counts()
        assert validation["contentQualityReview"] == overage_quality()
        assert validation["contentGoalOverages"] == content_goal_overages()
        assert validation["wikiReview"] == summary["wikiReview"]
        assert validation["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert validation["createdSiteSubmittedValues"] == created_site_submitted_values()
        acceptance = json.loads(Path(summary["artifacts"]["sourceRunAcceptance"]).read_text(encoding="utf-8"))
        assert acceptance["accepted"] is True
        assert acceptance["contentGoalCoverage"]["complete"] is True
        assert acceptance["contentCounts"] == content_counts()
        assert acceptance["contentQualityReview"] == overage_quality()
        assert acceptance["contentGoalOverages"] == content_goal_overages()
        assert acceptance["wikiReview"] == summary["wikiReview"]
        assert acceptance["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert acceptance["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert acceptance["stageSummary"]["currentStage"] == "complete"


def test_apply_launch_acceptance_can_generate_final_closeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        summary = build(args)
        assert summary["validationValid"] is True
        closeout_path = summary["artifacts"]["sourceRunFinalCloseout"]
        assert closeout_path.endswith("source-run-final-closeout.json")
        closeout = json.loads(Path(closeout_path).read_text(encoding="utf-8"))
        assert closeout["kind"] == "allincms_source_run_final_closeout"
        assert closeout["valid"] is True
        assert closeout["complete"] is True
        assert summary["sourceRunAcceptance"]["accepted"] is True


def test_apply_launch_acceptance_blocks_wiki_review_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        launch_data = json.loads(Path(args.created_site_binding).read_text(encoding="utf-8"))
        launch_data["wikiReview"] = {**launch_data["wikiReview"], "sourceWikiMarkdown": str(root / "other-manifest.json")}
        Path(args.created_site_binding).write_text(json.dumps(launch_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            build(args)
        except SystemExit as exc:
            assert "wiki review" in str(exc)
        else:
            raise AssertionError("wikiReview drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_decision_matrix_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        confirmation_data = json.loads(Path(args.confirmation).read_text(encoding="utf-8"))
        confirmation_data["confirmationDecisionMatrix"] = [
            {**confirmation_decision_matrix()[0], "decision": "defer", "deferDecision": "changed"}
        ]
        args.confirmation = write_json(root / "confirmation-bad-matrix.json", confirmation_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "decision matrix" in str(exc)
        else:
            raise AssertionError("confirmationDecisionMatrix drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_content_counts_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        forms_data = json.loads(Path(args.forms_media_settings).read_text(encoding="utf-8"))
        forms_data["contentCounts"] = {**content_counts(), "products": 3}
        args.forms_media_settings = write_json(root / "forms-media-settings-bad-counts.json", forms_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "content counts" in str(exc)
        else:
            raise AssertionError("contentCounts drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_source_identity_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        audit_data["sourceReviewPacketSha256"] = "c" * 64
        args.final_frontend_audit = write_json(root / "final-frontend-audit-identity-drift.json", audit_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "source identity hashes" in str(exc)
        else:
            raise AssertionError("source identity hash drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        audit_data["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "name": "Different Demo",
        }
        args.final_frontend_audit = write_json(root / "final-frontend-audit-submitted-value-drift.json", audit_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "created-site submitted values" in str(exc)
        else:
            raise AssertionError("createdSiteSubmittedValues drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_content_goal_overage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        audit_data["contentGoalOverages"]["details"].pop("posts")
        args.final_frontend_audit = write_json(root / "final-frontend-audit-overage-drift.json", audit_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "content goal overages" in str(exc)
        else:
            raise AssertionError("contentGoalOverages drift should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_missing_final_audit_content_counts_when_source_has_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        audit_data.pop("contentCounts", None)
        args.final_frontend_audit = write_json(root / "final-frontend-audit-no-counts.json", audit_data)
        try:
            build(args)
        except SystemExit as exc:
            assert "content counts" in str(exc)
        else:
            raise AssertionError("missing final frontend audit contentCounts should block launch acceptance apply")


def test_apply_launch_acceptance_blocks_final_audit_report_issue() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        reports = frontend_audit_report()
        reports[1]["issues"] = [{"severity": "error", "code": "literal_bold", "message": "redacted"}]
        bad_report_path = write_json(root / "bad-final-frontend-audit-report.json", reports)
        audit_data["auditReport"] = bad_report_path
        audit_data["redactedEvidencePointers"] = [bad_report_path]
        args.final_frontend_audit = write_json(root / "bad-final-frontend-audit.json", audit_data)
        summary = build(args)
        assert summary["validationValid"] is False
        assert "final_frontend_audit_passed" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "final_frontend_audit_passed"
            for blocker in item["blockers"]
        )
        assert "literal_bold" in blockers


def test_apply_launch_acceptance_blocks_second_batch_validation_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        invalid_posts = json.loads(Path(args.batch_validation[1]).read_text(encoding="utf-8"))
        invalid_posts["valid"] = False
        invalid_posts["issues"] = ["posts batch validation deliberately invalid"]
        args.batch_validation[1] = write_json(root / "posts-batch-validation-invalid.json", invalid_posts)
        summary = build(args)
        assert summary["validationValid"] is False
        assert "batch_upload_publish_verified" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        assert validation["batchValidationCount"] == 2
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "batch_upload_publish_verified"
            for blocker in item["blockers"]
        )
        assert "batch validation 2 report must be valid" in blockers


def test_apply_launch_acceptance_blocks_missing_batch_content_type_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        first = json.loads(Path(args.batch_validation[0]).read_text(encoding="utf-8"))
        duplicate_evidence = write_json(root / "products-batch-evidence-duplicate.json", full_batch_evidence("products"))
        args.batch_validation[1] = write_json(
            root / "products-batch-validation-duplicate.json",
            counted_batch_validation("products", evidence=duplicate_evidence, manifest_path=first["manifest"]),
        )
        summary = build(args)
        assert summary["validationValid"] is False
        assert "batch_upload_publish_verified" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        assert validation["batchValidationCount"] == 2
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "batch_upload_publish_verified"
            for blocker in item["blockers"]
        )
        assert "batch validation missing required content types from upload readiness: posts" in blockers


def test_apply_launch_acceptance_blocks_second_sample_evidence_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        invalid_posts = json.loads(Path(args.sample_evidence[1]).read_text(encoding="utf-8"))
        invalid_posts["frontendVerified"] = False
        args.sample_evidence[1] = write_json(root / "posts-sample-evidence-invalid.json", invalid_posts)
        summary = build(args)
        assert summary["validationValid"] is False
        assert "sample_backend_frontend_verified" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        assert validation["sampleEvidenceCount"] == 2
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "sample_backend_frontend_verified"
            for blocker in item["blockers"]
        )
        assert "sample evidence 2.frontendVerified must be true" in blockers


def test_apply_launch_acceptance_blocks_missing_sample_content_type_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        first = json.loads(Path(args.sample_evidence[0]).read_text(encoding="utf-8"))
        duplicate_products = full_sample_evidence("products", first["manifestPath"])
        args.sample_evidence[1] = write_json(root / "products-sample-evidence-duplicate.json", duplicate_products)
        summary = build(args)
        assert summary["validationValid"] is False
        assert "sample_backend_frontend_verified" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        assert validation["sampleEvidenceCount"] == 2
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "sample_backend_frontend_verified"
            for blocker in item["blockers"]
        )
        assert "sample evidence missing required content types from upload readiness: posts" in blockers


def test_apply_launch_acceptance_blocks_final_audit_wrong_detail_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        audit_data = json.loads(Path(args.final_frontend_audit).read_text(encoding="utf-8"))
        reports = frontend_audit_report()
        reports[1]["urlFingerprint"] = url_fingerprint("https://demo123.web.allincms.com/products/wrong-product")
        bad_report_path = write_json(root / "wrong-detail-final-frontend-audit-report.json", reports)
        audit_data["auditReport"] = bad_report_path
        audit_data["redactedEvidencePointers"] = [bad_report_path]
        args.final_frontend_audit = write_json(root / "wrong-detail-final-frontend-audit.json", audit_data)
        summary = build(args)
        assert summary["validationValid"] is False
        assert "final_frontend_audit_passed" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "final_frontend_audit_passed"
            for blocker in item["blockers"]
        )
        assert "fingerprint" in blockers


def test_apply_launch_acceptance_keeps_invalid_launch_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary = build(base_args(root, missing_final_audit=True))
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_launch_acceptance"
        assert summary["sourceRunAcceptance"]["accepted"] is False
        assert "final_frontend_audit_passed" in summary["validation"]["blockedKeys"]
        status = json.loads(Path(summary["artifacts"]["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        assert status["complete"] is False, status
        assert status["currentStage"] == "launch_acceptance", status
        acceptance = json.loads(Path(summary["artifacts"]["sourceRunAcceptance"]).read_text(encoding="utf-8"))
        issue_keys = {issue["key"] for issue in acceptance["issues"]}
        assert "source_status_incomplete" in issue_keys
        assert "launch_acceptance_incomplete" in issue_keys


def test_apply_launch_acceptance_rejects_maintenance_closeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = base_args(root)
        args.auto_final_closeout = False
        args.final_closeout_sedimentation = ""
        args.final_closeout_sedimentation_note = ""
        args.round_closeout = write_json(root / "maintenance-round-closeout.json", maintenance_round_closeout())
        summary = build(args)
        assert summary["validationValid"] is False
        assert summary["readyForNextStage"] == "blocked_launch_acceptance"
        assert summary["sourceRunAcceptance"]["accepted"] is False
        assert "skill_sedimentation_completed_or_readonly_exception_recorded" in summary["validation"]["blockedKeys"]
        validation = json.loads(Path(summary["artifacts"]["launchAcceptanceValidation"]).read_text(encoding="utf-8"))
        blockers = "\n".join(
            blocker
            for item in validation["blocked"]
            if item["key"] == "skill_sedimentation_completed_or_readonly_exception_recorded"
            for blocker in item["blockers"]
        )
        assert "maintenance closeout cannot prove launch completion" in blockers
        assert "launch closeout must have complete=true" in blockers
if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("apply launch acceptance regression tests passed.")
