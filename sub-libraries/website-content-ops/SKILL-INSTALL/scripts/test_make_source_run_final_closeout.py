#!/usr/bin/env python3
"""Regression tests for final source-run closeout generation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from make_source_run_final_closeout import build_summary
from test_validate_source_run_acceptance import (
    complete_handoff,
    complete_status,
    confirmation_decision_matrix,
    content_counts,
    content_goal_coverage,
    content_quality_review,
    write_json,
)
from test_manifest_sample_upload import content_goal_overages, created_site_submitted_values
from validate_source_run_acceptance import validate_acceptance


class Args:
    pass


def build_args(root: Path) -> tuple[Args, str, dict[str, str]]:
    status_path, paths = complete_status(root)
    handoff_path = complete_handoff(root, status_path)
    args = Args()
    args.source_status = status_path
    args.source_next_stage_handoff = handoff_path
    args.package = paths["package"]
    args.review_packet = paths["review_packet"]
    args.confirmation = paths["confirmation"]
    args.created_site_binding = paths["created_site_binding"]
    args.upload_readiness = [paths["upload_readiness"]]
    args.sample_evidence = [paths["products_sample"], paths["posts_sample"]]
    args.batch_validation = [paths["products_batch_validation"], paths["posts_batch_validation"]]
    args.forms_media_settings = paths["forms_media_settings"]
    args.final_frontend_audit = paths["final_frontend_audit"]
    args.cleanup_evidence = paths["cleanup_evidence"]
    args.launch_acceptance = paths["launch_acceptance"]
    args.objective = "source files to launched AllinCMS site"
    args.sedimentation = "updated"
    args.sedimentation_note = "Recorded final run proof."
    return args, handoff_path, paths


def test_builds_final_closeout_accepted_by_source_run_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, handoff_path, paths = build_args(root)
        closeout = build_summary(args)
        assert closeout["kind"] == "allincms_source_run_final_closeout"
        assert closeout["valid"] is True
        assert closeout["complete"] is True
        assert closeout["completionGaps"] == []
        assert closeout["contentGoalCoverage"] == content_goal_coverage()
        assert closeout["contentCounts"] == content_counts()
        assert closeout["contentGoalOverages"] == content_goal_overages()
        assert closeout["confirmationDecisionMatrix"] == confirmation_decision_matrix()
        assert closeout["createdSiteSubmittedValues"] == created_site_submitted_values()
        assert closeout["wikiReview"]["sourceWiki"] == paths["source_wiki"]
        closeout_path = root / "generated-final-closeout.json"
        closeout_path.write_text(json.dumps(closeout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        report = validate_acceptance(
            status_path=args.source_status,
            next_stage_handoff_path=handoff_path,
            package_path=paths["package"],
            review_packet_path=paths["review_packet"],
            confirmation_path=paths["confirmation"],
            launch_acceptance_path=paths["launch_acceptance"],
            created_site_binding_path=paths["created_site_binding"],
            upload_readiness_path=paths["upload_readiness"],
            sample_evidence_paths=[paths["products_sample"], paths["posts_sample"]],
            batch_validation_paths=[paths["products_batch_validation"], paths["posts_batch_validation"]],
            forms_media_settings_path=paths["forms_media_settings"],
            final_frontend_audit_path=paths["final_frontend_audit"],
            cleanup_evidence_path=paths["cleanup_evidence"],
            round_closeout_path=str(closeout_path),
            source_wiki_markdown_index_path=paths["source_wiki_markdown_index"],
            objective="source files to launched AllinCMS site",
        )
        assert report["accepted"] is True, report


def test_blocks_incomplete_status() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, _paths = build_args(root)
        status = json.loads(Path(args.source_status).read_text(encoding="utf-8"))
        status["complete"] = False
        status["currentStage"] = "batch_upload"
        status_path = root / "incomplete-status.json"
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.source_status = str(status_path)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("source status currentStage must be complete" in item for item in closeout["completionGaps"])


def test_blocks_source_context_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        launch = json.loads(Path(paths["launch_acceptance"]).read_text(encoding="utf-8"))
        launch["contentCounts"] = {"pages": 1, "products": 2, "posts": 1}
        args.launch_acceptance = write_json(root / "launch-acceptance-count-drift.json", launch)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("contentCounts mismatch" in item for item in closeout["completionGaps"])


def test_blocks_content_goal_overage_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        launch = json.loads(Path(paths["launch_acceptance"]).read_text(encoding="utf-8"))
        launch["contentGoalOverages"]["details"].pop("posts")
        args.launch_acceptance = write_json(root / "launch-acceptance-overage-drift.json", launch)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("contentGoalOverages" in item for item in closeout["completionGaps"])


def test_blocks_source_identity_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        audit = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit["sourcePackageSha256"] = "c" * 64
        args.final_frontend_audit = write_json(root / "final-frontend-audit-identity-drift.json", audit)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("sourcePackageSha256/sourceReviewPacketSha256 mismatch" in item for item in closeout["completionGaps"])


def test_blocks_created_site_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        audit = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit["createdSiteSubmittedValues"] = {
            **created_site_submitted_values(),
            "description": "Different description.",
        }
        args.final_frontend_audit = write_json(root / "final-frontend-audit-submitted-value-drift.json", audit)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("createdSiteSubmittedValues mismatch" in item for item in closeout["completionGaps"])


def test_blocks_missing_created_site_submitted_values_for_new_site_objective() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        args.objective = "用户确认后 AI 新建站点并上传内容"

        package = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package["targetMode"] = "new_site"
        args.package = write_json(root / "package-new-site-without-submitted-values.json", package)

        for key in (
            "source_status",
            "created_site_binding",
            "launch_acceptance",
            "forms_media_settings",
            "final_frontend_audit",
        ):
            data = json.loads(Path(getattr(args, key)).read_text(encoding="utf-8"))
            data.pop("createdSiteSubmittedValues", None)
            setattr(args, key, write_json(root / f"{key}-without-submitted-values.json", data))

        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert "createdSiteSubmittedValues" not in closeout
        assert any("createdSiteSubmittedValues" in item for item in closeout["completionGaps"])


def test_blocks_missing_posts_sample_direct_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, _paths = build_args(root)
        args.sample_evidence = [args.sample_evidence[0]]
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("sample evidence for posts is required" in item for item in closeout["completionGaps"])


def test_blocks_invalid_batch_evidence_direct_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        validation = json.loads(Path(paths["posts_batch_validation"]).read_text(encoding="utf-8"))
        evidence = json.loads(Path(paths["posts_batch_evidence"]).read_text(encoding="utf-8"))
        evidence["progressLog"][0]["bodyVerified"] = False
        bad_evidence_path = write_json(root / "posts-batch-evidence-bad-body.json", evidence)
        validation["evidence"] = bad_evidence_path
        args.batch_validation = [
            args.batch_validation[0],
            write_json(root / "posts-batch-validation-bad-body.json", validation),
        ]
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("bodyVerified must be true" in item for item in closeout["completionGaps"])


def test_blocks_final_frontend_audit_report_issue() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        reports = json.loads(Path(paths["final_frontend_audit_report"]).read_text(encoding="utf-8"))
        reports[1]["issues"] = [{"code": "literal_bold", "severity": "error"}]
        bad_report = root / "final-frontend-audit-report-with-issue.json"
        bad_report.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit = json.loads(Path(paths["final_frontend_audit"]).read_text(encoding="utf-8"))
        audit["auditReport"] = str(bad_report)
        audit["redactedEvidencePointers"] = [str(bad_report)]
        args.final_frontend_audit = write_json(root / "final-frontend-audit-with-issue.json", audit)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("literal_bold" in item for item in closeout["completionGaps"])


def test_blocks_forms_media_settings_direct_validation_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        forms = json.loads(Path(paths["forms_media_settings"]).read_text(encoding="utf-8"))
        forms["mediaVerified"] = False
        forms["deferrals"] = [
            item for item in forms.get("deferrals", []) if item.get("module") != "media"
        ]
        args.forms_media_settings = write_json(root / "forms-media-settings-missing-media.json", forms)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("mediaVerified must be true" in item for item in closeout["completionGaps"])


def test_blocks_existing_site_binding_for_new_site_closeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        package = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package["targetMode"] = "new_site"
        args.package = write_json(root / "package-new-site.json", package)
        binding = json.loads(Path(paths["created_site_binding"]).read_text(encoding="utf-8"))
        binding["siteBindingMode"] = "existing_site"
        binding["siteCreationStatus"] = "existing_site_selected"
        args.created_site_binding = write_json(root / "existing-site-binding.json", binding)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("new-site objective requires siteBindingMode=created_site" in item for item in closeout["completionGaps"])


def test_blocks_next_stage_handoff_status_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, _paths = build_args(root)
        other_status_path = root / "other-source-execution-status.json"
        other_status_path.write_text(Path(args.source_status).read_text(encoding="utf-8"), encoding="utf-8")
        args.source_next_stage_handoff = write_json(
            root / "source-next-stage-handoff-stale.json",
            {
                "kind": "allincms_source_next_stage_handoff",
                "localOnly": True,
                "remoteMutationsPerformed": False,
                "preparedOnly": True,
                "isUserAuthorization": False,
                "sourceExecutionStatus": str(other_status_path),
                "currentStage": "complete",
                "supported": False,
                "mode": "complete",
            },
        )
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("sourceExecutionStatus must point to this source status file" in item for item in closeout["completionGaps"])


def test_blocks_missing_source_wiki_layer_direct_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        package = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package.pop("sourceWiki", None)
        args.package = write_json(root / "package-without-source-wiki.json", package)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("source package must include sourceWiki" in item for item in closeout["completionGaps"])


def test_blocks_json_wikiref_without_readable_markdown_direct_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        wiki = json.loads(Path(paths["source_wiki"]).read_text(encoding="utf-8"))
        json_ref = write_json(root / "wiki-json-ref.json", wiki)
        wiki["sourceSet"]["wikiRefs"] = [json_ref]
        source_wiki_path = write_json(root / "source-wiki-json-ref-only.json", wiki)
        package = json.loads(Path(paths["package"]).read_text(encoding="utf-8"))
        package["sourceWiki"] = source_wiki_path
        package["wikiReview"] = {
            **package["wikiReview"],
            "sourceWiki": source_wiki_path,
            "sourceWikiMarkdown": "",
            "sourceWikiMarkdownIndex": "",
        }
        args.package = write_json(root / "package-json-ref-only.json", package)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("readable source wiki Markdown index" in item for item in closeout["completionGaps"])


def test_blocks_wiki_review_markdown_drift_direct_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, paths = build_args(root)
        other_index = root / "other-wiki-index.md"
        other_index.write_text("# Other Wiki\n\nReadable but not the verified source wiki index.\n", encoding="utf-8")
        launch = json.loads(Path(paths["launch_acceptance"]).read_text(encoding="utf-8"))
        launch["wikiReview"] = {
            **launch["wikiReview"],
            "sourceWikiMarkdown": str(other_index),
            "sourceWikiMarkdownIndex": str(other_index),
        }
        args.launch_acceptance = write_json(root / "launch-with-wiki-review-drift.json", launch)
        closeout = build_summary(args)
        assert closeout["valid"] is False
        assert closeout["complete"] is False
        assert any("wikiReview" in item and "mismatch" in item for item in closeout["completionGaps"])


def test_allows_pre_final_closeout_launch_handoff_when_only_launch_stage_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args, _handoff_path, _paths = build_args(root)
        status = json.loads(Path(args.source_status).read_text(encoding="utf-8"))
        status["complete"] = False
        status["currentStage"] = "launch_acceptance"
        status["stages"]["launch_acceptance"] = {
            "status": "blocked",
            "evidence": "",
            "blockers": ["launch acceptance validation missing"],
            "nextAction": "run launch acceptance after batch/forms/final audit/cleanup",
        }
        status["passedCount"] = status["stageCount"] - 1
        args.source_status = write_json(root / "source-execution-status.pre-final-closeout.json", status)
        args.source_next_stage_handoff = write_json(
            root / "source-next-stage-handoff.pre-final-closeout.json",
            {
                "kind": "allincms_source_next_stage_handoff",
                "localOnly": True,
                "remoteMutationsPerformed": False,
                "preparedOnly": True,
                "isUserAuthorization": False,
                "sourceExecutionStatus": args.source_status,
                "currentStage": "launch_acceptance",
                "supported": True,
                "mode": "local_helper_prepares_or_applies_stage",
            },
        )
        closeout = build_summary(args)
        assert closeout["valid"] is True, closeout["completionGaps"]
        assert closeout["complete"] is True


if __name__ == "__main__":
    test_builds_final_closeout_accepted_by_source_run_acceptance()
    test_blocks_incomplete_status()
    test_blocks_source_context_drift()
    test_blocks_content_goal_overage_drift()
    test_blocks_source_identity_drift()
    test_blocks_created_site_submitted_value_drift()
    test_blocks_missing_created_site_submitted_values_for_new_site_objective()
    test_blocks_missing_posts_sample_direct_validation()
    test_blocks_invalid_batch_evidence_direct_validation()
    test_blocks_final_frontend_audit_report_issue()
    test_blocks_forms_media_settings_direct_validation_failure()
    test_blocks_existing_site_binding_for_new_site_closeout()
    test_blocks_next_stage_handoff_status_mismatch()
    test_blocks_missing_source_wiki_layer_direct_validation()
    test_blocks_json_wikiref_without_readable_markdown_direct_validation()
    test_blocks_wiki_review_markdown_drift_direct_validation()
    test_allows_pre_final_closeout_launch_handoff_when_only_launch_stage_blocked()
    print("source run final closeout regression tests passed.")
