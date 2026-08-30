#!/usr/bin/env python3
"""Regression tests for pages/site-info execution evidence validation."""

from __future__ import annotations

from validate_pages_site_info_execution_evidence import site_info_field_count, validate_evidence


def handoff() -> dict:
    return {
        "kind": "allincms_pages_site_info_browser_handoff",
        "siteKey": "demo123",
        "frontendBaseUrl": "https://demo123.web.allincms.com",
        "siteInfo": {"browserStepsExecutable": False},
        "pages": [
            {
                "page": {"title": "Home", "path": "/", "sourceRefs": ["src-001"]},
                "browserStepsExecutable": False,
                "actions": [{"action": "create_theme_page"}],
            },
            {
                "page": {"title": "About", "path": "/about", "sourceRefs": ["src-001"]},
                "browserStepsExecutable": False,
                "actions": [{"action": "create_theme_page"}],
            },
        ],
    }


def reuse_handoff() -> dict:
    data = handoff()
    data["defaultTemplateState"] = {
        "reuseExistingPagesFirst": True,
        "existingRoutePaths": ["/", "/about"],
    }
    for item in data["pages"]:
        item["executionStrategy"] = "reuse_existing_theme_page_first"
        item["actions"] = [
            {"action": "save_design", "existingPageReuse": True},
            {"action": "publish_design", "existingPageReuse": True},
            {"action": "enable_theme_page", "existingPageReuse": True},
            {"action": "bind_route", "existingPageReuse": True},
        ]
    return data


def action_proof() -> dict:
    return {"preMutationGate": "passed", "verified": True, "evidence": "redacted proof"}


def page(path: str, frontend_url: str, *, homepage: bool = False) -> dict:
    data = {
        "path": path,
        "routePath": path,
        "backendUrl": "https://workspace.laicms.com/demo123/themes/theme-redacted/page-redacted/design",
        "frontendUrl": frontend_url,
        "createThemePageVerified": True,
        "designSaved": True,
        "designPublished": True,
        "pageEnabled": True,
        "routeBound": True,
        "frontendVerified": True,
        "renderAudit": {
            "sourceContentVerified": True,
            "starterTemplateAbsent": True,
            "expectedSourceSignals": ["source-confirmed heading rendered", "source-confirmed body rendered"],
            "unexpectedStarterSignals": [],
            "proof": "redacted DOM rendered expected source copy and no unrelated old copy",
        },
        "actionEvidence": {
            "create_theme_page": action_proof(),
            "save_design": action_proof(),
            "publish_design": action_proof(),
            "enable_theme_page": action_proof(),
            "bind_route": action_proof(),
        },
    }
    if homepage:
        data["homepageVerified"] = True
    return data


def valid_evidence() -> dict:
    return {
        "kind": "allincms_pages_site_info_execution_evidence",
        "siteKey": "demo123",
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": True,
        "stopConditionMet": True,
        "blockingIssues": [],
        "siteInfo": {
            "status": "verified",
            "target": "https://workspace.laicms.com/demo123/site-info",
            "saveStatus": "ok",
            "backendVerified": True,
            "persistedVerified": True,
            "requestCapture": {
                "method": "POST",
                "headers": ["accept", "content-type"],
                "payloadShape": {"name": "string", "description": "string"},
                "responseStatus": 200,
            },
        },
        "pages": [
            page("/", "https://demo123.web.allincms.com", homepage=True),
            page("/about", "https://demo123.web.allincms.com/about"),
        ],
    }


def test_accepts_complete_evidence() -> None:
    issues = validate_evidence(valid_evidence(), handoff())
    assert not issues, issues
    assert site_info_field_count(valid_evidence()["siteInfo"]) == 6


def test_accepts_existing_page_reuse_without_create_theme_page_proof() -> None:
    evidence = valid_evidence()
    for item in evidence["pages"]:
        item["createThemePageVerified"] = False
        item["actionEvidence"].pop("create_theme_page")
    issues = validate_evidence(evidence, reuse_handoff())
    assert not issues, issues


def test_existing_page_reuse_still_requires_design_and_route_proof() -> None:
    evidence = valid_evidence()
    for item in evidence["pages"]:
        item["createThemePageVerified"] = False
        item["actionEvidence"].pop("create_theme_page")
    evidence["pages"][1]["designSaved"] = False
    issues = validate_evidence(evidence, reuse_handoff())
    assert any("designSaved" in issue for issue in issues), issues


def test_rejects_missing_page_path_from_handoff() -> None:
    evidence = valid_evidence()
    evidence["pages"] = [evidence["pages"][0]]
    issues = validate_evidence(evidence, handoff())
    assert any("missing handoff paths" in issue for issue in issues), issues


def test_rejects_placeholder_backend_url() -> None:
    evidence = valid_evidence()
    evidence["pages"][1]["backendUrl"] = "https://workspace.laicms.com/demo123/themes/{themeId}/{pageId}/design"
    issues = validate_evidence(evidence, handoff())
    assert any("placeholder" in issue for issue in issues), issues


def test_rejects_string_render_audit() -> None:
    evidence = valid_evidence()
    evidence["pages"][0]["renderAudit"] = "frontend is nonblank"
    issues = validate_evidence(evidence, handoff())
    assert any("renderAudit must be an object" in issue for issue in issues), issues


def test_rejects_starter_template_frontend_proof() -> None:
    evidence = valid_evidence()
    evidence["pages"][0]["renderAudit"]["starterTemplateAbsent"] = False
    evidence["pages"][0]["renderAudit"]["unexpectedStarterSignals"] = ["template product copy"]
    evidence["pages"][0]["renderAudit"]["proof"] = "template product copy still visible"
    issues = validate_evidence(evidence, handoff())
    assert any("starterTemplateAbsent" in issue for issue in issues), issues
    assert any("unexpectedStarterSignals" in issue for issue in issues), issues
    assert any("starter-template terms" in issue for issue in issues), issues


def test_rejects_raw_header_values() -> None:
    evidence = valid_evidence()
    evidence["siteInfo"]["requestCapture"]["headers"] = ["cookie: secret"]
    issues = validate_evidence(evidence, handoff())
    assert any("header names only" in issue or "forbidden" in issue for issue in issues), issues


if __name__ == "__main__":
    test_accepts_complete_evidence()
    test_accepts_existing_page_reuse_without_create_theme_page_proof()
    test_existing_page_reuse_still_requires_design_and_route_proof()
    test_rejects_missing_page_path_from_handoff()
    test_rejects_placeholder_backend_url()
    test_rejects_string_render_audit()
    test_rejects_starter_template_frontend_proof()
    test_rejects_raw_header_values()
    print("pages/site-info execution evidence validation regression tests passed.")
