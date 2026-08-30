#!/usr/bin/env python3
"""Tests for run-scoped authorization: coverage, carve-outs, and derived per-action auth validity."""
from __future__ import annotations

from run_authorization import (
    RUN_AUTH_KIND,
    COVERED_ACTIONS,
    validate_run_authorization,
    run_authorization_covers,
    derive_action_authorization,
)
from make_authorization_record import validate_record as validate_action_auth


def grant(site_key: str = "abc123xyz", covered: list | None = None,
          expires_at: str = "2099-01-01T00:00:00+00:00") -> dict:
    return {
        "kind": RUN_AUTH_KIND,
        "workspace": "https://workspace.laicms.com",
        "generatedAt": "2026-07-05T10:00:00+00:00",
        "expiresAt": expires_at,
        "mode": "run_scoped_auto",
        "siteKey": site_key,
        "packageHash": "sha256:deadbeefcafe1234",
        "confirmedItemCount": 6,
        "coveredActions": covered if covered is not None else sorted(COVERED_ACTIONS),
        "authorization": {
            "userAuthorized": True,
            "grantScope": "auto-build this confirmed package on site abc123xyz without re-prompting",
            "verificationPlan": "backend re-read + frontend verify per action; stop on carve-out/gate failure",
        },
    }


def test_valid_grant_passes() -> None:
    assert validate_run_authorization(grant()) == []


def test_covered_content_action_is_covered() -> None:
    ok, _ = run_authorization_covers(grant(), "save_product", "abc123xyz")
    assert ok is True
    ok2, _ = run_authorization_covers(grant(), "batch_upload", "abc123xyz")
    assert ok2 is True


def test_create_site_is_carve_out() -> None:
    ok, reason = run_authorization_covers(grant(), "create_site", "abc123xyz")
    assert ok is False and "carve-out" in reason


def test_delete_and_outward_settings_are_carve_outs() -> None:
    for action in ("delete_or_cleanup", "unpublish", "add_domain", "add_tracking_tag", "create_form", "save_site_settings"):
        ok, reason = run_authorization_covers(grant(), action, "abc123xyz")
        assert ok is False, f"{action} must be a carve-out"
        assert "carve-out" in reason


def test_unknown_action_defaults_to_carve_out() -> None:
    ok, _ = run_authorization_covers(grant(), "some_future_action", "abc123xyz")
    assert ok is False, "unknown actions must default to needing explicit auth (allowlist)"


def test_wrong_site_is_carve_out() -> None:
    ok, reason = run_authorization_covers(grant(site_key="abc123xyz"), "save_product", "othersite99")
    assert ok is False and "not the authorized" in reason


def test_action_not_in_granted_covered_list() -> None:
    g = grant(covered=["save_product", "publish_product"])
    ok, _ = run_authorization_covers(g, "batch_upload", "abc123xyz")
    assert ok is False, "an action outside this grant's coveredActions is not covered"


def test_covered_actions_reject_non_allowlisted_in_record() -> None:
    g = grant(covered=["save_product", "create_site"])
    errors = validate_run_authorization(g)
    assert any("allowlisted" in e for e in errors), "a grant cannot list create_site in coveredActions"


def test_derive_emits_valid_per_action_authorization() -> None:
    target = "https://workspace.laicms.com/abc123xyz/products/xxx/update"
    derived = derive_action_authorization(grant(), "save_product", target)
    # The point: the derived record must satisfy the EXISTING per-action gate validator unchanged.
    assert validate_action_auth(derived) == [], f"derived auth must pass validate_record: {validate_action_auth(derived)}"
    assert derived["authorization"]["authorizationSource"].startswith("run_scoped_authorization:")
    assert target in derived["authorization"]["authorizationSource"]


def test_derive_refuses_carve_out() -> None:
    for action in ("delete_or_cleanup", "create_site", "add_domain"):
        try:
            derive_action_authorization(grant(), action, "https://workspace.laicms.com/abc123xyz")
        except ValueError as exc:
            assert "carve-out" in str(exc)
        else:
            raise AssertionError(f"deriving auth for carve-out {action} must raise")


def test_derive_covers_batch_and_taxonomy() -> None:
    for action in ("batch_upload", "create_or_map_products_category", "publish_product", "save_design"):
        target = f"https://workspace.laicms.com/abc123xyz/{action}"
        d = derive_action_authorization(grant(), action, target)
        assert validate_action_auth(d) == [], f"{action}: {validate_action_auth(d)}"


def test_run_scoped_source_rejected_for_carve_out_action() -> None:
    # A hand-crafted run-scoped source must NOT bypass the strict human checks for a carve-out.
    from make_authorization_record import validate_authorization_source
    target = "https://workspace.laicms.com/sites"
    src = f"run_scoped_authorization: package sha256:x action create_site at {target}"
    try:
        validate_authorization_source("create_site", src, target)
    except ValueError as exc:
        assert "carve-out" in str(exc) or "allowlisted" in str(exc)
    else:
        raise AssertionError("run-scoped source for create_site must be rejected")
    # but valid for a covered action
    ct = "https://workspace.laicms.com/abc123xyz/products/x/update"
    assert validate_authorization_source(
        "save_product", f"run_scoped_authorization: package sha256:x action save_product at {ct}", ct
    )


def test_expired_grant_is_not_covered() -> None:
    # A grant past its TTL must stop auto-covering, even for an in-scope action on the right site.
    # generatedAt/expiresAt both in the past and correctly ordered, so it's structurally valid but stale.
    g = grant(expires_at="2026-06-01T18:00:00+00:00")
    g["generatedAt"] = "2026-06-01T10:00:00+00:00"
    assert validate_run_authorization(g) == [], "the stale grant must be structurally valid"
    ok, reason = run_authorization_covers(g, "save_product", "abc123xyz")
    assert ok is False and "expired" in reason


def test_grant_requires_expiry() -> None:
    g = grant()
    del g["expiresAt"]
    assert any("expiresAt is required" in e for e in validate_run_authorization(g))


def test_expiry_must_be_after_generated() -> None:
    g = grant(expires_at="2020-01-01T00:00:00+00:00")  # before generatedAt 2026
    assert any("after generatedAt" in e for e in validate_run_authorization(g))


def test_grant_rejects_secret_value() -> None:
    g = grant()
    g["authorization"]["grantScope"] = "auto-build; token=ab12cd34ef56gh"  # a pasted secret must be rejected
    assert any("PII" in e or "token" in e for e in validate_run_authorization(g))


if __name__ == "__main__":
    test_valid_grant_passes()
    test_covered_content_action_is_covered()
    test_create_site_is_carve_out()
    test_delete_and_outward_settings_are_carve_outs()
    test_unknown_action_defaults_to_carve_out()
    test_wrong_site_is_carve_out()
    test_action_not_in_granted_covered_list()
    test_covered_actions_reject_non_allowlisted_in_record()
    test_derive_emits_valid_per_action_authorization()
    test_derive_refuses_carve_out()
    test_derive_covers_batch_and_taxonomy()
    test_run_scoped_source_rejected_for_carve_out_action()
    test_expired_grant_is_not_covered()
    test_grant_requires_expiry()
    test_expiry_must_be_after_generated()
    test_grant_rejects_secret_value()
    print("run_authorization regression tests passed")
