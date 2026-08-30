#!/usr/bin/env python3
"""Regression tests for applying filled created-site evidence bundles."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_created_site_evidence_bundle import build
from export_confirmed_site_artifacts import build_artifacts
from test_bind_created_site_to_artifacts import SITE_KEY, module_routes
from test_confirmed_create_site_handoff import prepare_inputs as prepare_create_site_inputs
from test_prepare_created_site_evidence_bundle import prepared_inputs


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def prepared_bundle(root: Path) -> dict:
    runbook, runbook_path, brief, brief_path = prepared_inputs(root)
    from prepare_created_site_evidence_bundle import build_bundle

    bundle = build_bundle(
        runbook=runbook,
        runbook_path=runbook_path,
        brief=brief,
        brief_path=brief_path,
        output_dir=root / "created-site-evidence-bundle",
    )
    write_json(root / "created-site-evidence-bundle" / "evidence-bundle.json", bundle)
    return bundle


def filled_template(root: Path, bundle: dict) -> str:
    template = json.loads(Path(bundle["evidenceTemplate"]).read_text(encoding="utf-8"))
    authorization_record = Path(bundle["authorizationRecord"])
    authorization_record.parent.mkdir(parents=True, exist_ok=True)
    authorization_record.write_text(
        json.dumps(
            {
                "action": "create_site",
                "target": "https://workspace.laicms.com/sites",
                "targetIdentifier": "Example Demo",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    template.update(
        {
            "createdSiteKey": SITE_KEY,
            "preMutationGateStatus": "passed",
            "gateReadyForBrowserSubmit": True,
            "contentTypeForInitialInspection": "products",
            "listColumns": ["名称", "Slug", "状态"],
            "editFields": ["名称", "Slug", "描述", "更新"],
            "siteCardEvidence": f"site card href https://workspace.laicms.com/{SITE_KEY}/dashboard",
            "backendEvidence": f"backend URL https://workspace.laicms.com/{SITE_KEY}/dashboard loaded",
            "frontendEvidence": f"frontend URL https://{SITE_KEY}.web.allincms.com loaded",
            "setupPageEvidence": {
                "siteInfo": "site-info settings page controls visible",
                "domains": "domains page controls visible",
                "media": "media page controls visible",
                "themes": "themes page controls visible",
                "routes": "routes page controls visible",
                "forms": "forms page controls visible",
                "tracking": "tracking page controls visible",
            },
            "moduleRoutes": module_routes(SITE_KEY),
            "submittedFields": ["name", "description"],
            "authorizationSource": "授权 Codex 在 https://workspace.laicms.com/sites 创建站点，站点名称为 Example Demo。",
            "forbiddenNeighborActionsVerified": True,
            "stopConditionMet": True,
        }
    )
    return write_json(root / "created-site-evidence-bundle" / "created-site-evidence.filled-template.json", template)


def confirmed_artifacts(root: Path) -> tuple[str, str, str, str]:
    create_site_args = prepare_create_site_inputs(root)
    package_path = Path(create_site_args.package)
    confirmation_path = Path(create_site_args.confirmation)
    plan_path = Path(create_site_args.execution_plan)
    readiness = build_artifacts(
        argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            execution_plan=str(plan_path),
            site_key="",
            frontend_base_url="",
            output_dir=str(root / "artifacts"),
            json=False,
        )
    )
    readiness_path = root / "artifacts" / "artifact-readiness.json"
    write_json(readiness_path, readiness)
    return str(package_path), str(confirmation_path), str(plan_path), str(readiness_path)


def base_args(root: Path, bundle: dict, filled_path: str) -> argparse.Namespace:
    return argparse.Namespace(
        bundle=str(root / "created-site-evidence-bundle" / "evidence-bundle.json"),
        filled_template=filled_path,
        output_dir=str(root / "applied"),
        created_site_evidence_output=str(root / "applied" / "created-site-evidence.json"),
        require_output_under_output_dir=True,
        prepare_created_site_schema_capture=False,
        artifact_readiness="",
        package="",
        review_packet="",
        confirmation="",
        execution_plan="",
        authorization_dir="",
        theme_target="",
        json=False,
    )


def test_apply_created_site_evidence_bundle_writes_created_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        summary = build(base_args(root, bundle, filled_path))
        assert summary["remoteMutationsPerformed"] is False
        assert summary["createdSiteKey"] == SITE_KEY
        assert summary["createdSiteSubmittedValues"]["name"] == "Example Demo"
        assert summary["createdSiteSubmittedValues"]["description"] == bundle["submittedValues"]["description"]
        assert summary["createdSiteSchemaCapturePrepared"] is False
        evidence = json.loads(Path(summary["createdSiteEvidence"]).read_text(encoding="utf-8"))
        assert evidence["siteCreation"]["status"] == "created_verified"
        assert evidence["siteIdentity"]["siteKey"] == SITE_KEY
        assert evidence["siteIdentity"]["frontendBaseUrl"] == f"https://{SITE_KEY}.web.allincms.com"
        assert evidence["siteCreation"]["submittedValues"]["name"] == "Example Demo"
        assert evidence["siteCreation"]["submittedValues"]["description"] == bundle["submittedValues"]["description"]
        assert evidence["setupPages"]["media"] == ["media page controls visible"]
        assert evidence["authorization"]["userAuthorized"] is True


def test_apply_created_site_evidence_bundle_can_prepare_schema_capture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        package_path, confirmation_path, plan_path, readiness_path = confirmed_artifacts(root)
        args = base_args(root, bundle, filled_path)
        args.prepare_created_site_schema_capture = True
        args.package = package_path
        args.confirmation = confirmation_path
        args.execution_plan = plan_path
        args.artifact_readiness = readiness_path
        summary = build(args)
        assert summary["createdSiteSchemaCapturePrepared"] is True
        assert summary["createdSiteSubmittedValues"]["name"] == "Example Demo"
        assert Path(summary["artifacts"]["createdSiteSchemaCaptureSummary"]).exists()
        assert Path(summary["artifacts"]["createdSiteArtifactBinding"]).exists()
        assert Path(summary["artifacts"]["boundArtifactReadiness"]).exists()
        assert Path(summary["artifacts"]["productsBoundDraftManifest"]).exists()
        assert Path(summary["artifacts"]["postsBoundDraftManifest"]).exists()
        assert Path(summary["artifacts"]["schemaCaptureHandoff"]).exists()
        assert Path(summary["artifacts"]["schemaCaptureProgress"]).exists()
        assert Path(summary["artifacts"]["pagesSiteInfoHandoff"]).exists()
        assert Path(summary["artifacts"]["pagesSiteInfoEvidenceBundle"]).exists()
        assert Path(summary["artifacts"]["taxonomyHandoff"]).exists()
        assert Path(summary["artifacts"]["taxonomyEvidenceBundle"]).exists()
        assert Path(summary["artifacts"]["sourceExecutionStatus"]).exists()
        assert Path(summary["artifacts"]["sourceNextStageHandoff"]).exists()
        schema_summary = json.loads(Path(summary["artifacts"]["createdSiteSchemaCaptureSummary"]).read_text(encoding="utf-8"))
        assert schema_summary["siteKey"] == SITE_KEY
        assert schema_summary["remoteMutationsPerformed"] is False
        assert schema_summary["sourceNextStage"]["currentStage"] == "pages_site_info_execution"


def test_apply_created_site_evidence_bundle_rejects_source_context_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        filled = json.loads(Path(filled_path).read_text(encoding="utf-8"))
        filled["contentCounts"]["pages"] += 1
        write_json(Path(filled_path), filled)
        try:
            build(base_args(root, bundle, filled_path))
        except SystemExit as exc:
            assert "contentCounts must match bundle" in str(exc)
        else:
            raise AssertionError("source-context drift should block bundle apply")


def test_apply_created_site_evidence_bundle_rejects_submitted_value_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        filled = json.loads(Path(filled_path).read_text(encoding="utf-8"))
        filled["submittedValues"]["name"] = "Different Demo"
        filled["submittedSiteName"] = "Different Demo"
        write_json(Path(filled_path), filled)
        try:
            build(base_args(root, bundle, filled_path))
        except SystemExit as exc:
            assert "submittedValues.name must match the confirmed siteProposal" in str(exc)
        else:
            raise AssertionError("submitted site name drift should block bundle apply")


def test_apply_created_site_evidence_bundle_reports_missing_module_route() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        filled = json.loads(Path(filled_path).read_text(encoding="utf-8"))
        filled["moduleRoutes"] = [route for route in filled["moduleRoutes"] if "/media" not in route]
        write_json(Path(filled_path), filled)
        try:
            build(base_args(root, bundle, filled_path))
        except SystemExit as exc:
            assert "filled created-site evidence is invalid" in str(exc)
            assert "module routes missing required modules: media" in str(exc)
        else:
            raise AssertionError("missing media module route should block bundle apply")


def test_apply_created_site_evidence_bundle_rejects_missing_media_setup_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        filled = json.loads(Path(filled_path).read_text(encoding="utf-8"))
        filled["setupPageEvidence"].pop("media")
        write_json(Path(filled_path), filled)
        try:
            build(base_args(root, bundle, filled_path))
        except SystemExit as exc:
            assert "setupPageEvidence.media must be concrete" in str(exc)
        else:
            raise AssertionError("missing media setup evidence should block bundle apply")


def test_apply_created_site_evidence_bundle_rejects_missing_gate_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bundle = prepared_bundle(root)
        filled_path = filled_template(root, bundle)
        filled = json.loads(Path(filled_path).read_text(encoding="utf-8"))
        filled["preMutationGateStatus"] = "pending"
        filled["gateReadyForBrowserSubmit"] = False
        write_json(Path(filled_path), filled)
        try:
            build(base_args(root, bundle, filled_path))
        except SystemExit as exc:
            assert "preMutationGateStatus must be passed" in str(exc)
            assert "gateReadyForBrowserSubmit must be true" in str(exc)
        else:
            raise AssertionError("missing gate pass should block bundle apply")


if __name__ == "__main__":
    test_apply_created_site_evidence_bundle_writes_created_evidence()
    test_apply_created_site_evidence_bundle_can_prepare_schema_capture()
    test_apply_created_site_evidence_bundle_rejects_source_context_drift()
    test_apply_created_site_evidence_bundle_rejects_submitted_value_drift()
    test_apply_created_site_evidence_bundle_reports_missing_module_route()
    test_apply_created_site_evidence_bundle_rejects_missing_media_setup_evidence()
    test_apply_created_site_evidence_bundle_rejects_missing_gate_pass()
    print("apply created-site evidence bundle regression tests passed.")
