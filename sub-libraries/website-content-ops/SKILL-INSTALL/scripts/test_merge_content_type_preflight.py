#!/usr/bin/env python3
"""Regression tests for content-type preflight merge."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from merge_content_type_preflight import merge_content_preflight, validate_merge_result
from test_validate_run_evidence import created_site_evidence, existing_site_selected_evidence


def retarget_refresh_to_created_site(refresh: dict, created: dict) -> None:
    site_key = created["siteIdentity"]["siteKey"]
    refresh["siteIdentity"]["siteKey"] = site_key
    refresh["siteIdentity"]["backendDashboardUrl"] = created["siteIdentity"]["backendDashboardUrl"]
    refresh["siteIdentity"]["frontendBaseUrl"] = created["siteIdentity"]["frontendBaseUrl"]
    refresh["siteIdentity"]["moduleRoutes"] = list(created["siteIdentity"]["moduleRoutes"])
    refresh["siteCreation"]["existingSiteKeysBeforeCreate"] = [site_key]
    refresh["siteCreation"]["siteKeyEvidence"] = {
        site_key: f"backend route href observed for site key {site_key}"
    }
    refresh["siteCreation"]["selectedSiteEvidence"] = (
        f"backend dashboard route verified for selected site key {site_key}: "
        f"https://workspace.laicms.com/{site_key}/dashboard"
    )


def test_merge_posts_preflight_into_created_site() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created = created_site_evidence()
        refresh = existing_site_selected_evidence()
        retarget_refresh_to_created_site(refresh, created)
        refresh["contentInspection"] = {
            "contentType": "posts",
            "listColumns": ["标题", "Slug", "摘要", "状态"],
            "editFields": ["标题", "Slug", "摘要", "正文编辑器", "更新", "发布"],
        }
        refresh_path = root / "posts-readonly-refresh.json"
        refresh_path.write_text(json.dumps(refresh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        merged = merge_content_preflight(
            created,
            refresh,
            refresh_path=refresh_path,
            content_type="posts",
            output_path=root / "created-site-posts-preflight.json",
        )
        assert not validate_merge_result(merged, "posts")
        assert merged["siteCreation"]["status"] == "created_verified"
        assert merged["contentInspection"]["contentType"] == "posts"
        assert merged["contentTypePreflights"]["posts"]["readyForCreateProbeGate"] is True
        assert merged["contentTypePreflights"]["posts"]["sourceReadOnlyEvidence"] == str(refresh_path)
        assert merged["contentTypePreflights"]["posts"]["mergedEvidence"].endswith("created-site-posts-preflight.json")
        assert merged["localChecks"]["contentTypePreflightContentType"] == "posts"


def test_merge_rejects_wrong_content_type() -> None:
    created = created_site_evidence()
    refresh = existing_site_selected_evidence()
    retarget_refresh_to_created_site(refresh, created)
    refresh["contentInspection"]["contentType"] = "products"
    try:
        merge_content_preflight(
            created,
            refresh,
            refresh_path=Path("/tmp/products-refresh.json"),
            content_type="posts",
        )
    except ValueError as exc:
        assert "contentInspection.contentType must be posts" in str(exc)
    else:
        raise AssertionError("merge accepted wrong content type")


def test_merge_rejects_mutated_created_evidence() -> None:
    created = copy.deepcopy(created_site_evidence())
    created["siteCreation"]["status"] = "existing_site_selected"
    refresh = existing_site_selected_evidence()
    try:
        merge_content_preflight(
            created,
            refresh,
            refresh_path=Path("/tmp/refresh.json"),
            content_type="products",
        )
    except ValueError as exc:
        assert "created evidence" in str(exc)
    else:
        raise AssertionError("merge accepted non-created evidence")


if __name__ == "__main__":
    test_merge_posts_preflight_into_created_site()
    test_merge_rejects_wrong_content_type()
    test_merge_rejects_mutated_created_evidence()
    print("content-type preflight merge regression tests passed.")
