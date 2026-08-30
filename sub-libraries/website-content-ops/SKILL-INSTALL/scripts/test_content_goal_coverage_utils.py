#!/usr/bin/env python3
"""Regression tests for source-context utility helpers."""

from __future__ import annotations

from content_goal_coverage_utils import (
    matching_confirmation_decision_matrix,
    matching_content_counts,
    matching_created_site_submitted_values,
)


def full_counts() -> dict:
    return {
        "pages": 2,
        "products": 3,
        "posts": 1,
        "forms": 1,
        "media": 2,
        "navigationItems": 5,
        "siteInfoFields": 4,
    }


def test_matching_content_counts_accepts_full_scope() -> None:
    counts, issues = matching_content_counts(
        [
            ("artifact readiness", {"contentCounts": full_counts()}),
            ("created-site binding", {"contentCounts": full_counts()}),
        ]
    )
    assert not issues
    assert counts == full_counts()


def test_matching_content_counts_rejects_missing_extended_scope_key() -> None:
    stale = dict(full_counts())
    stale.pop("navigationItems")
    counts, issues = matching_content_counts(
        [
            ("artifact readiness", {"contentCounts": full_counts()}),
            ("created-site binding", {"contentCounts": stale}),
        ]
    )
    assert counts == full_counts()
    assert "created-site binding: contentCounts.navigationItems must be a non-negative integer" in issues
    assert "contentCounts mismatch between artifact readiness and created-site binding" in issues


def test_matching_content_counts_keeps_legacy_three_count_artifacts_valid() -> None:
    legacy = {"pages": 1, "products": 1, "posts": 1}
    counts, issues = matching_content_counts(
        [
            ("run evidence", {"contentCounts": legacy}),
            ("manifest", {"contentCounts": dict(legacy)}),
        ]
    )
    assert not issues
    assert counts == legacy


def test_matching_content_counts_can_require_downstream_labels() -> None:
    counts, issues = matching_content_counts(
        [
            ("source", {"contentCounts": full_counts()}),
            ("downstream evidence", {}),
        ],
        require_labels={"downstream evidence"},
    )
    assert counts == full_counts()
    assert "downstream evidence: contentCounts is required when source contentCounts are present" in issues


def confirmation_row(source: str = "acceptedFields", **overrides: object) -> dict:
    row = {
        "field": "contentPlan.mediaPolicy",
        "source": source,
        "decision": "accept",
        "deferDecision": None,
        "reason": "source material covers this field",
        "blocksRemoteMutation": False,
    }
    row.update(overrides)
    return row


def test_matching_confirmation_decision_matrix_ignores_source_label_transition() -> None:
    matrix, issues = matching_confirmation_decision_matrix(
        [
            ("review packet", {"confirmationDecisionMatrix": [confirmation_row("suggestedAcceptedFields")]}),
            ("confirmation", {"confirmationDecisionMatrix": [confirmation_row("acceptedFields")]}),
        ]
    )
    assert not issues
    assert matrix == [confirmation_row("suggestedAcceptedFields")]


def test_matching_confirmation_decision_matrix_accepts_defer_source_label_transition() -> None:
    review_row = confirmation_row(
        "suggestedAcceptedDeferrals",
        field="domains.customDomain",
        decision="defer",
        deferDecision="Use platform subdomain until a production domain is supplied.",
        reason="custom domain requires user-owned DNS",
    )
    confirmed_row = dict(review_row)
    confirmed_row["source"] = "acceptedDeferrals"
    matrix, issues = matching_confirmation_decision_matrix(
        [
            ("review packet", {"confirmationDecisionMatrix": [review_row]}),
            ("confirmation", {"confirmationDecisionMatrix": [confirmed_row]}),
        ]
    )
    assert not issues
    assert matrix == [review_row]


def test_matching_confirmation_decision_matrix_rejects_real_decision_drift() -> None:
    matrix, issues = matching_confirmation_decision_matrix(
        [
            ("review packet", {"confirmationDecisionMatrix": [confirmation_row("suggestedAcceptedFields")]}),
            ("confirmation", {"confirmationDecisionMatrix": [confirmation_row("acceptedFields", decision="defer", deferDecision="Later")]}),
        ]
    )
    assert matrix == [confirmation_row("suggestedAcceptedFields")]
    assert "confirmationDecisionMatrix mismatch between review packet and confirmation" in issues


def test_matching_confirmation_decision_matrix_rejects_defer_text_drift() -> None:
    review_row = confirmation_row(
        "suggestedAcceptedDeferrals",
        field="tracking.analytics",
        decision="defer",
        deferDecision="Skip analytics until tracking ID is supplied.",
        reason="tracking requires user confirmation",
    )
    confirmed_row = dict(review_row)
    confirmed_row["source"] = "acceptedDeferrals"
    confirmed_row["deferDecision"] = "Enable analytics immediately."
    _, issues = matching_confirmation_decision_matrix(
        [
            ("review packet", {"confirmationDecisionMatrix": [review_row]}),
            ("confirmation", {"confirmationDecisionMatrix": [confirmed_row]}),
        ]
    )
    assert "confirmationDecisionMatrix mismatch between review packet and confirmation" in issues


def submitted_values() -> dict:
    return {
        "name": "Example Demo",
        "description": "Example demo site for source-backed publishing.",
    }


def test_matching_created_site_submitted_values_accepts_full_chain() -> None:
    values, issues = matching_created_site_submitted_values(
        [
            ("created-site binding", {"createdSiteSubmittedValues": submitted_values()}),
            ("sample runbook", {"createdSiteSubmittedValues": dict(submitted_values())}),
        ]
    )
    assert not issues
    assert values == submitted_values()


def test_matching_created_site_submitted_values_rejects_missing_downstream() -> None:
    _, issues = matching_created_site_submitted_values(
        [
            ("created-site binding", {"createdSiteSubmittedValues": submitted_values()}),
            ("batch runbook", {}),
        ]
    )
    assert "batch runbook: createdSiteSubmittedValues is required when present in source context" in issues


def test_matching_created_site_submitted_values_rejects_drift() -> None:
    drifted = dict(submitted_values())
    drifted["description"] = "Different submitted description."
    _, issues = matching_created_site_submitted_values(
        [
            ("manifest", {"createdSiteSubmittedValues": submitted_values()}),
            ("sample evidence", {"createdSiteSubmittedValues": drifted}),
        ]
    )
    assert "createdSiteSubmittedValues mismatch between manifest and sample evidence" in issues


if __name__ == "__main__":
    test_matching_content_counts_accepts_full_scope()
    test_matching_content_counts_rejects_missing_extended_scope_key()
    test_matching_content_counts_keeps_legacy_three_count_artifacts_valid()
    test_matching_content_counts_can_require_downstream_labels()
    test_matching_confirmation_decision_matrix_ignores_source_label_transition()
    test_matching_confirmation_decision_matrix_accepts_defer_source_label_transition()
    test_matching_confirmation_decision_matrix_rejects_real_decision_drift()
    test_matching_confirmation_decision_matrix_rejects_defer_text_drift()
    test_matching_created_site_submitted_values_accepts_full_chain()
    test_matching_created_site_submitted_values_rejects_missing_downstream()
    test_matching_created_site_submitted_values_rejects_drift()
    print("content goal coverage utility regression tests passed.")
