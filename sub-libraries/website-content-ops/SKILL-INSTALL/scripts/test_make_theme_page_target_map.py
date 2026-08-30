#!/usr/bin/env python3
"""Regression tests for theme/page target-map generation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from make_theme_page_target_map import build


def handoff() -> dict:
    return {
        "kind": "allincms_pages_site_info_browser_handoff",
        "siteKey": "demo123",
        "frontendBaseUrl": "https://demo123.web.allincms.com",
        "pages": [
            {
                "page": {"title": "Home", "path": "/"},
                "actions": [
                    {
                        "action": "save_design",
                        "target": "https://workspace.laicms.com/demo123/themes/{themeId}/{pageId}/design",
                        "authorizationRecordCommand": "make --target https://workspace.laicms.com/demo123/themes/{themeId}/{pageId}/design",
                        "requiresConcreteTargetBeforeAuthorization": True,
                    },
                    {
                        "action": "publish_design",
                        "target": "https://workspace.laicms.com/demo123/themes/{themeId}/{pageId}/design",
                        "requiresConcreteTargetBeforeAuthorization": True,
                    },
                    {
                        "action": "bind_route",
                        "target": "https://workspace.laicms.com/demo123/routes",
                        "requiresConcreteTargetBeforeAuthorization": False,
                    },
                ],
            },
            {
                "page": {"title": "Applications", "path": "/applications"},
                "actions": [
                    {
                        "action": "create_theme_page",
                        "target": "https://workspace.laicms.com/demo123/themes/{themeId}",
                        "requiresConcreteTargetBeforeAuthorization": False,
                    }
                ],
            },
        ],
    }


def observation() -> dict:
    return {
        "siteKey": "demo123",
        "themeUrl": "https://workspace.laicms.com/demo123/themes/theme-main",
        "pageRows": [
            {
                "title": "Home",
                "path": "/home",
                "status": "published",
                "designUrl": "https://workspace.laicms.com/demo123/themes/theme-main/page-home/design",
            },
            {
                "title": "About Us",
                "path": "/about-us",
                "status": "published",
                "designUrl": "https://workspace.laicms.com/demo123/themes/theme-main/page-about/design",
            },
        ],
    }


def test_maps_home_root_to_existing_home_design_url() -> None:
    result = build(handoff(), observation(), "/tmp/handoff.json")
    home = result["mappedPages"][0]
    assert home["sourcePath"] == "/"
    assert home["matchStatus"] == "existing_page_mapped"
    assert home["homepageRootUsesHomeRoute"] is True
    assert home["actions"][0]["target"] == "https://workspace.laicms.com/demo123/themes/theme-main/page-home/design"
    assert "{pageId}" not in home["actions"][0]["authorizationRecordCommand"]
    assert home["actions"][0]["commandsConcrete"] is True
    assert home["actions"][0]["requiresConcreteTargetBeforeAuthorization"] is False
    assert result["missingSourcePaths"] == ["/applications"]
    assert result["readyForExistingPageAuthorization"] is True


def test_rejects_cross_site_design_url() -> None:
    obs = observation()
    obs["pageRows"][0]["designUrl"] = "https://workspace.laicms.com/other123/themes/theme-main/page-home/design"
    try:
        build(handoff(), obs, "/tmp/handoff.json")
    except SystemExit as exc:
        assert "site key does not match" in str(exc)
    else:
        raise AssertionError("cross-site design URL should be rejected")


def test_writes_outside_skill_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "target-map.json"
        result = build(handoff(), observation(), "/tmp/handoff.json")
        out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        assert json.loads(out.read_text(encoding="utf-8"))["themeId"] == "theme-main"


if __name__ == "__main__":
    test_maps_home_root_to_existing_home_design_url()
    test_rejects_cross_site_design_url()
    test_writes_outside_skill_contract()
    print("theme page target-map regression tests passed.")
