#!/usr/bin/env python3
"""Regression tests for create-site preflight evidence generation."""

from __future__ import annotations

from make_create_preflight_evidence import build_evidence, parse_observed_fields, parse_site_key_evidence
from validate_run_evidence import validate


def valid_observed_fields_text() -> str:
    return (
        "create site entry button visible on /sites;"
        "dialog opened for create site;"
        "input name: name placeholder Site Name;"
        "textarea name: description placeholder Site Description;"
        "submit button Create;"
        "close dialog button"
    )


def test_parse_observed_fields_requires_downstream_create_terms() -> None:
    try:
        parse_observed_fields(
            "input name: name placeholder Site Name;"
            "textarea name: description placeholder Site Description;"
            "submit button Create;"
            "close dialog button"
        )
    except ValueError as exc:
        assert "observed create site entry" in str(exc)
    else:
        raise AssertionError("missing create-site-entry should block preflight generation")


def test_generated_preflight_passes_run_evidence_validation() -> None:
    fields = parse_observed_fields(valid_observed_fields_text())
    evidence = build_evidence(
        ["existingdemo"],
        fields,
        dialog_closed_verified=True,
        repo_check_passed=True,
        repo_check_note=None,
        site_key_evidence={
            "existingdemo": "existingdemo backend URL href https://workspace.laicms.com/existingdemo/dashboard"
        },
    )
    assert not validate(evidence)


def test_site_card_frontend_domain_is_strong_site_key_evidence() -> None:
    parsed = parse_site_key_evidence(
        "existingdemo shown as /sites card frontend domain existingdemo.web.allincms.com",
        ["existingdemo"],
    )
    assert parsed["existingdemo"] == "existingdemo shown as /sites card frontend domain existingdemo.web.allincms.com"


if __name__ == "__main__":
    test_parse_observed_fields_requires_downstream_create_terms()
    test_generated_preflight_passes_run_evidence_validation()
    test_site_card_frontend_domain_is_strong_site_key_evidence()
    print("create-site preflight evidence regression tests passed.")
