#!/usr/bin/env python3
"""Regression tests for the Slate content-shape gate."""
from __future__ import annotations

from validate_slate_content_shape import (
    validate_slate_content,
    validate_manifest_content_shapes,
    build_report,
)


def test_valid_slate_passes() -> None:
    content = [
        {"type": "p", "children": [{"text": "First paragraph."}], "id": "a1"},
        {"type": "p", "children": [{"text": "Second paragraph."}]},
    ]
    assert validate_slate_content(content) == [], "clean Slate node array must pass"


def test_string_body_rejected() -> None:
    issues = validate_slate_content("## Heading\n\nSome **markdown** body")
    assert issues, "a markdown string body must be rejected"
    assert any("string" in i for i in issues)


def test_html_string_rejected() -> None:
    issues = validate_slate_content("<p>hello</p>")
    assert issues, "an HTML string body must be rejected"


def test_empty_list_rejected() -> None:
    assert validate_slate_content([]), "empty content list must be rejected"


def test_missing_children_and_text_rejected() -> None:
    issues = validate_slate_content([{"type": "p"}])
    assert any("children" in i for i in issues), "node without children/text must be flagged"


def test_bad_leaf_rejected() -> None:
    issues = validate_slate_content([{"type": "p", "children": ["not-a-leaf"]}])
    assert any("leaf" in i for i in issues), "non-object leaf must be flagged"


def test_html_tag_in_leaf_flagged() -> None:
    issues = validate_slate_content([{"type": "p", "children": [{"text": "hello <b>world</b>"}]}])
    assert any("HTML tag" in i for i in issues), "an HTML tag in leaf text must be flagged"


def test_code_fence_in_leaf_flagged() -> None:
    issues = validate_slate_content([{"type": "p", "children": [{"text": "```json\n{}\n```"}]}])
    assert any("code fence" in i for i in issues), "a code fence in leaf text must be flagged"


def test_technical_copy_not_false_flagged() -> None:
    # Legit RF copy starting with '<' or '#' must NOT be flagged as residue.
    content = [
        {"type": "p", "children": [{"text": "<10 GHz insertion loss with #1-rated stability"}]},
        {"type": "p", "children": [{"text": "VSWR < 1.35:1 at 50 GHz"}]},
    ]
    assert validate_slate_content(content) == [], "technical copy with '<'/'#' must pass"


def test_manifest_items_validated() -> None:
    manifest = {
        "items": [
            {"slug": "good", "content": [{"type": "p", "children": [{"text": "ok"}]}]},
            {"slug": "bad", "content": "markdown string"},
            {"slug": "no-body"},  # no content field -> skipped, not an error
        ]
    }
    issues = validate_manifest_content_shapes(manifest)
    assert len(issues) == 1, "only the string-body item should fail"
    assert "bad.content" in issues[0]


def test_nested_manifest_items() -> None:
    manifest = {"manifest": {"items": [{"slug": "x", "content": "bad"}]}}
    issues = validate_manifest_content_shapes(manifest)
    assert issues, "items nested under manifest.items must still be validated"


def test_report_shape() -> None:
    report = build_report({"items": [{"slug": "x", "content": "bad"}]})
    assert report["kind"] == "allincms_slate_content_shape_validation"
    assert report["valid"] is False and report["issues"]


if __name__ == "__main__":
    test_valid_slate_passes()
    test_string_body_rejected()
    test_html_string_rejected()
    test_empty_list_rejected()
    test_missing_children_and_text_rejected()
    test_bad_leaf_rejected()
    test_html_tag_in_leaf_flagged()
    test_code_fence_in_leaf_flagged()
    test_technical_copy_not_false_flagged()
    test_manifest_items_validated()
    test_nested_manifest_items()
    test_report_shape()
    print("validate_slate_content_shape regression tests passed")
