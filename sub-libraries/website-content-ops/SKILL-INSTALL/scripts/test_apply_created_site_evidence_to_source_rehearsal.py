#!/usr/bin/env python3
"""Regression tests for applying created-site evidence to source rehearsals."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_create_preflight_to_source_rehearsal import build as apply_create_preflight_to_source
from apply_created_site_evidence_to_source_rehearsal import build
from test_apply_create_preflight_to_source_rehearsal import make_preflight, new_site_rehearsal
from test_apply_created_site_evidence_bundle import filled_template
from test_bind_created_site_to_artifacts import SITE_KEY


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def create_preflight_source_apply(root: Path) -> dict:
    _, rehearsal_path = new_site_rehearsal(root)
    preflight_path = make_preflight(root)
    result = apply_create_preflight_to_source(
        argparse.Namespace(
            rehearsal_summary=str(rehearsal_path),
            create_preflight=str(preflight_path),
            output_dir=str(root / "create-preflight-source-apply"),
            output="",
            json=False,
        )
    )
    write_json(root / "create-preflight-source-apply" / "create-preflight-source-rehearsal-apply.json", result)
    return result


def test_apply_created_site_evidence_to_source_rehearsal_prepares_next_stage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_apply = create_preflight_source_apply(root)
        bundle_path = source_apply["artifacts"]["createdSiteEvidenceBundle"]
        bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
        expected_site_name = bundle["submittedValues"]["name"]
        filled_path = filled_template(root, bundle)
        summary = build(
            argparse.Namespace(
                source_apply_result=str(root / "create-preflight-source-apply" / "create-preflight-source-rehearsal-apply.json"),
                created_site_evidence_bundle="",
                filled_created_site_evidence_template=filled_path,
                output_dir=str(root / "post-create-source-apply"),
                authorization_dir="",
                theme_target="",
                json=False,
            )
        )
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["isRemoteMutationAuthorization"] is False
        assert summary["preparedOnly"] is True
        assert summary["status"] == "created_site_evidence_applied"
        assert summary["targetMode"] == "new_site"
        assert summary["readyForBrowserStage"] == "pages_site_info_execution"
        assert summary["createdSiteSchemaCapturePrepared"] is True
        assert summary["createdSiteKey"] == SITE_KEY
        assert summary["createdSiteSubmittedValues"]["name"] == expected_site_name
        assert Path(summary["createdSiteEvidence"]).exists()
        assert Path(summary["sourceExecutionStatus"]).exists()
        assert Path(summary["sourceNextStageHandoff"]).exists()

        for key in (
            "createdSiteEvidenceBundleApplySummary",
            "createdSiteEvidence",
            "createdSiteSchemaCaptureSummary",
            "createdSiteArtifactBinding",
            "boundArtifactReadiness",
            "productsBoundDraftManifest",
            "postsBoundDraftManifest",
            "schemaCaptureHandoff",
            "schemaCaptureProgress",
            "pagesSiteInfoHandoff",
            "pagesSiteInfoEvidenceBundle",
            "taxonomyHandoff",
            "taxonomyEvidenceBundle",
            "sourceExecutionStatus",
            "sourceNextStageHandoff",
        ):
            assert Path(summary["artifacts"][key]).exists(), key

        source_status = json.loads(Path(summary["sourceExecutionStatus"]).read_text(encoding="utf-8"))
        next_stage = json.loads(Path(summary["sourceNextStageHandoff"]).read_text(encoding="utf-8"))
        binding = json.loads(Path(summary["artifacts"]["createdSiteArtifactBinding"]).read_text(encoding="utf-8"))
        assert source_status["currentStage"] == "pages_site_info_execution"
        assert next_stage["currentStage"] == "pages_site_info_execution"
        assert binding["siteBindingMode"] == "created_site"
        assert binding["createdSiteSubmittedValues"]["name"] == expected_site_name
        assert any("does not submit" in item for item in summary["adversarialChecks"])


def test_apply_created_site_evidence_to_source_rehearsal_rejects_wrong_source_kind() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bad_source = root / "bad-source-apply.json"
        write_json(
            bad_source,
            {
                "kind": "allincms_created_site_evidence_bundle_apply_summary",
                "localOnly": True,
                "remoteMutationsPerformed": False,
                "isRemoteMutationAuthorization": False,
            },
        )
        try:
            build(
                argparse.Namespace(
                    source_apply_result=str(bad_source),
                    created_site_evidence_bundle="",
                    filled_created_site_evidence_template=str(root / "filled.json"),
                    output_dir=str(root / "post-create-source-apply"),
                    authorization_dir="",
                    theme_target="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "source apply result kind" in str(exc)
        else:
            raise AssertionError("wrong source apply kind should be rejected")


def test_apply_created_site_evidence_to_source_rehearsal_rejects_missing_filled_template() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source_apply = create_preflight_source_apply(root)
        try:
            build(
                argparse.Namespace(
                    source_apply_result=str(root / "create-preflight-source-apply" / "create-preflight-source-rehearsal-apply.json"),
                    created_site_evidence_bundle=source_apply["artifacts"]["createdSiteEvidenceBundle"],
                    filled_created_site_evidence_template=str(root / "missing-filled-template.json"),
                    output_dir=str(root / "post-create-source-apply"),
                    authorization_dir="",
                    theme_target="",
                    json=False,
                )
            )
        except SystemExit as exc:
            assert "filled created-site evidence template does not exist" in str(exc)
        else:
            raise AssertionError("missing filled template should be rejected")


if __name__ == "__main__":
    test_apply_created_site_evidence_to_source_rehearsal_prepares_next_stage()
    test_apply_created_site_evidence_to_source_rehearsal_rejects_wrong_source_kind()
    test_apply_created_site_evidence_to_source_rehearsal_rejects_missing_filled_template()
    print("created-site evidence source rehearsal apply regression tests passed.")
