#!/usr/bin/env python3
"""Regression tests for default-theme bootstrap preparation and validation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from prepare_default_theme_bootstrap import build as build_runbook
from test_validate_run_evidence import created_site_evidence
from validate_default_theme_bootstrap_evidence import validate_evidence


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def valid_evidence(site_key: str = "codex-test-site") -> dict:
    base = f"https://{site_key}.web.allincms.com"
    return {
        "kind": "allincms_default_theme_bootstrap_evidence",
        "siteKey": site_key,
        "target": f"https://workspace.laicms.com/{site_key}/themes",
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": True,
        "stopConditionMet": True,
        "createdDefaultTheme": True,
        "preset": "默认",
        "themeName": "Default Launch Theme",
        "themeId": "theme-redacted",
        "pageCount": 7,
        "createTheme": {
            "action": "create_theme",
            "preMutationGate": "passed",
            "backendVerified": True,
            "requestCapture": {
                "method": "POST",
                "url": f"https://workspace.laicms.com/{site_key}/themes",
                "headers": ["accept", "content-type"],
                "payloadShape": {"name": "string", "preset": "default", "description": "string"},
                "responseStatus": 200,
            },
        },
        "activateTheme": {
            "action": "activate_theme",
            "preMutationGate": "passed",
            "routeMappingReviewed": True,
            "themeEnabled": True,
            "backendVerified": True,
        },
        "routes": {
            "routesBound": True,
            "backendVerified": True,
            "checkedRoutes": ["/home", "/products", "/products/{product}", "/posts", "/posts/{post}", "/about-us", "/contact-us"],
        },
        "frontend": {
            "baseUrl": base,
            "checkedPaths": [
                {"path": "/", "url": base, "statusOk": True, "domNonEmpty": True},
                {"path": "/home", "url": base + "/home", "statusOk": True, "domNonEmpty": True},
                {"path": "/products", "url": base + "/products", "statusOk": True, "domNonEmpty": True},
                {"path": "/posts", "url": base + "/posts", "statusOk": True, "domNonEmpty": True},
                {"path": "/about-us", "url": base + "/about-us", "statusOk": True, "domNonEmpty": True},
                {"path": "/contact-us", "url": base + "/contact-us", "statusOk": True, "domNonEmpty": True},
            ],
            "genericTemplateContentRemaining": True,
            "businessContentComplete": False,
        },
        "blockingIssues": [],
    }


def test_prepare_default_theme_bootstrap_outputs_runbook() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        preflight_path = write_json(root / "created-site-evidence.json", created_site_evidence())
        summary = build_runbook(
            argparse.Namespace(
                preflight=preflight_path,
                output=str(root / "default-theme-runbook.json"),
                theme_name="Default Launch Theme",
                json=False,
            )
        )
        assert summary["readyForBrowserStage"] == "ready_to_prepare_action_specific_authorization", summary
        runbook = json.loads(Path(summary["runbook"]).read_text(encoding="utf-8"))
        assert runbook["kind"] == "allincms_default_theme_bootstrap_runbook"
        assert runbook["theme"]["preset"] == "默认"
        assert [action["action"] for action in runbook["actions"]] == ["create_theme", "activate_theme"]
        assert "<paste current user authorization text here>" in runbook["actions"][0]["authorizationRecordCommand"]
        assert "check_pre_mutation_gate.py --action activate_theme" in runbook["actions"][1]["preMutationGateCommand"]
        assert runbook["evidenceTemplate"]["frontend"]["businessContentComplete"] is False


def test_validate_default_theme_bootstrap_accepts_complete_evidence() -> None:
    issues = validate_evidence(valid_evidence())
    assert not issues, issues


def test_validate_default_theme_bootstrap_rejects_blank_or_incomplete_theme() -> None:
    evidence = valid_evidence()
    evidence["preset"] = "blank"
    evidence["pageCount"] = 0
    evidence["frontend"]["checkedPaths"] = []
    issues = validate_evidence(evidence)
    assert any("preset" in issue for issue in issues), issues
    assert any("pageCount" in issue for issue in issues), issues
    assert any("checkedPaths" in issue for issue in issues), issues


def test_validate_default_theme_bootstrap_rejects_raw_header_values() -> None:
    evidence = valid_evidence()
    evidence["createTheme"]["requestCapture"]["headers"] = ["cookie: secret"]
    issues = validate_evidence(evidence)
    assert any("header names only" in issue or "forbidden" in issue for issue in issues), issues


if __name__ == "__main__":
    test_prepare_default_theme_bootstrap_outputs_runbook()
    test_validate_default_theme_bootstrap_accepts_complete_evidence()
    test_validate_default_theme_bootstrap_rejects_blank_or_incomplete_theme()
    test_validate_default_theme_bootstrap_rejects_raw_header_values()
    print("default-theme bootstrap regression tests passed.")
