#!/usr/bin/env python3
"""Regression tests for the next-action freshness gate."""
from __future__ import annotations

from check_next_action_freshness import check_freshness, _collect_action_ids


def _contract(deployment: str = "dep-current-abc123") -> dict:
    return {
        "deploymentId": deployment,
        "actions": {
            "productCreate": "7f499304d7430b6f8bd58cce2420d98c47bbc6d142",
            "productUpdate": "7fadb04c60ce99518d25f7332f06121fa2d951b0c7",
            "categoryCreate": "7f602158e4577e9e37aaa362cef378a4a5cf0f43c0",
        },
        "postActions": {"create": "7f11951bae6c43d992a0274dead12e5aca45801748"},
        "deleteActions": {"product_delete": "7f79e6bd7d04119de1206ac91dbb04e621dd4bb13b"},
    }


def test_matching_deployment_is_fresh() -> None:
    r = check_freshness(_contract(), "dep-current-abc123")
    assert r["fresh"] is True, r["issues"]
    assert r["actionCount"] == 5


def test_stale_deployment_refused() -> None:
    r = check_freshness(_contract("dep-old-xyz"), "dep-current-abc123")
    assert r["fresh"] is False
    assert any("stale" in i for i in r["issues"])


def test_missing_deployment_marker_refused() -> None:
    c = _contract()
    del c["deploymentId"]
    r = check_freshness(c, "dep-current-abc123")
    assert r["fresh"] is False
    assert any("no deploymentId" in i for i in r["issues"])


def test_missing_current_id_refused() -> None:
    r = check_freshness(_contract(), "")
    assert r["fresh"] is False
    assert any("current deployment id is empty" in i for i in r["issues"])


def test_no_action_ids_refused() -> None:
    r = check_freshness({"deploymentId": "dep-current-abc123"}, "dep-current-abc123")
    assert r["fresh"] is False
    assert any("no next-action IDs" in i for i in r["issues"])


def test_short_action_id_refused() -> None:
    c = _contract()
    c["actions"]["productCreate"] = "abc"
    r = check_freshness(c, "dep-current-abc123")
    assert r["fresh"] is False
    assert any("plausible" in i for i in r["issues"])


def test_required_action_missing_refused() -> None:
    r = check_freshness(_contract(), "dep-current-abc123", required_actions=["actions.postPublish"])
    assert r["fresh"] is False
    assert any("required action" in i for i in r["issues"])


def test_captured_for_deployment_alias() -> None:
    c = _contract()
    del c["deploymentId"]
    c["capturedForDeployment"] = "dep-current-abc123"
    r = check_freshness(c, "dep-current-abc123")
    assert r["fresh"] is True, r["issues"]


def test_collect_action_ids() -> None:
    ids = _collect_action_ids(_contract())
    assert "actions.productCreate" in ids and "deleteActions.product_delete" in ids


if __name__ == "__main__":
    test_matching_deployment_is_fresh()
    test_stale_deployment_refused()
    test_missing_deployment_marker_refused()
    test_missing_current_id_refused()
    test_no_action_ids_refused()
    test_short_action_id_refused()
    test_required_action_missing_refused()
    test_captured_for_deployment_alias()
    test_collect_action_ids()
    print("check_next_action_freshness regression tests passed")
