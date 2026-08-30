#!/usr/bin/env python3
"""Regression tests for create-site authorization preparation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from apply_create_preflight_to_confirmed_execution import build as apply_preflight
from test_apply_create_preflight_to_confirmed_execution import make_apply_result, make_preflight
from prepare_create_site_authorization import build, validate_preparation


def make_create_site_apply(root: Path) -> Path:
    result = apply_preflight(
        argparse.Namespace(
            apply_result=str(make_apply_result(root)),
            create_preflight=str(make_preflight(root)),
            output_dir=str(root / "with-preflight"),
            output=str(root / "with-preflight" / "apply-result.json"),
            json=False,
        )
    )
    path = root / "with-preflight" / "apply-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def base_args(root: Path, apply_result: Path, authorization_text: str = "") -> argparse.Namespace:
    return argparse.Namespace(
        apply_result=str(apply_result),
        runbook="",
        user_authorization_text=authorization_text,
        authorization_output=str(root / "authorization-create-site.json"),
        output_dir=str(root / "authorization-prep"),
        output=str(root / "authorization-prep" / "authorization-prep.json"),
        max_age_minutes=60 * 24 * 365,
        json=False,
    )


def test_prepares_pending_authorization_package_without_user_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_create_site_apply(root)
        result = build(base_args(root, apply_result))
        assert result["status"] == "awaiting_user_authorization"
        assert result["remoteMutationsPerformed"] is False
        assert result["isRemoteMutationAuthorization"] is False
        assert result["gateReadyForBrowserSubmit"] is False
        assert "authorize Codex to create the site" in result["suggestedAuthorizationText"]
        assert "<paste current user authorization text here>" in result["authorizationRecordCommandTemplate"]
        assert not Path(result["authorizationRecordTarget"]).exists()
        assert result["artifacts"]["runbook"] == result["runbook"]
        assert result["artifacts"]["preflight"] == result["preflight"]
        assert result["artifacts"]["authorizationRecordTarget"] == result["authorizationRecordTarget"]
        assert result["artifacts"]["authorizationRecord"] == ""
        assert result["artifacts"]["createdSiteEvidenceBundle"].endswith("evidence-bundle.json")
        assert result["artifacts"]["createdSiteEvidenceTarget"].endswith("created-site-evidence.json")
        assert not validate_preparation(result)


def test_writes_authorization_record_and_passes_gate_with_exact_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_create_site_apply(root)
        prep = build(base_args(root, apply_result))
        result = build(base_args(root, apply_result, prep["suggestedAuthorizationText"]))
        assert result["status"] == "pre_mutation_gate_passed"
        assert result["gateReadyForBrowserSubmit"] is True
        assert Path(result["authorizationRecord"]).exists()
        auth = json.loads(Path(result["authorizationRecord"]).read_text(encoding="utf-8"))
        assert auth["action"] == "create_site"
        assert auth["target"] == "https://workspace.laicms.com/sites"
        assert auth["targetIdentifier"] == result["targetIdentifier"]
        assert {"name", "description"}.issubset(set(auth["fieldsOrFiles"]))
        assert result["artifacts"]["authorizationRecord"] == result["authorizationRecord"]
        assert Path(result["artifacts"]["authorizationRecord"]).exists()
        assert result["validation"]["authorizationRecordIssues"] == []
        assert result["validation"]["preMutationGateIssues"] == []
        assert not validate_preparation(result)


def test_direct_runbook_input_preserves_created_site_evidence_target() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_create_site_apply(root)
        apply_data = json.loads(apply_result.read_text(encoding="utf-8"))
        runbook = Path(apply_data["artifacts"]["createSiteRunbook"])
        result = build(
            argparse.Namespace(
                apply_result="",
                runbook=str(runbook),
                user_authorization_text="",
                authorization_output=str(root / "authorization-create-site.json"),
                output_dir=str(root / "authorization-prep-from-runbook"),
                output=str(root / "authorization-prep-from-runbook" / "authorization-prep.json"),
                max_age_minutes=60 * 24 * 365,
                json=False,
            )
        )
        assert result["status"] == "awaiting_user_authorization"
        assert result["artifacts"]["createdSiteEvidenceBundle"] == ""
        assert result["artifacts"]["createdSiteEvidenceTarget"].endswith("created-site-evidence.json")
        assert not validate_preparation(result)


def test_generic_authorization_text_does_not_pass_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply_result = make_create_site_apply(root)
        result = build(base_args(root, apply_result, "ok"))
        assert result["status"] == "authorization_record_invalid"
        assert result["gateReadyForBrowserSubmit"] is False
        assert result["authorizationRecord"] == ""
        assert result["validation"]["authorizationRecordIssues"]
        assert not validate_preparation(result)


if __name__ == "__main__":
    test_prepares_pending_authorization_package_without_user_text()
    test_writes_authorization_record_and_passes_gate_with_exact_text()
    test_direct_runbook_input_preserves_created_site_evidence_target()
    test_generic_authorization_text_does_not_pass_gate()
    print("create-site authorization preparation regression tests passed.")
