#!/usr/bin/env python3
"""Tests for the content-format (readability/structure) gate."""
from __future__ import annotations

from check_content_format import check


def pkg(products=None, posts=None) -> dict:
    return {"contentPlan": {"products": products or [], "posts": posts or []}}


def prod(content, slug="p") -> dict:
    return {"slug": slug, "name": "P-TEST", "content": content}


def wall_body():
    # A long, flat, structureless body — the "correct but a paragraph wall" failure.
    return [{"type": "p", "children": [{"text": "P-TEST is a phase-stable test cable. " * 20}]}]


def good_body():
    return [
        {"type": "p", "children": [{"text": "Phase-stable 26.5GHz cable, "}, {"text": "250 PPM drift", "bold": True}, {"text": "."}]},
        {"type": "h2", "children": [{"text": "Why choose it"}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "phase stable"}]},
                                     {"type": "li", "children": [{"text": "durable"}]}]},
        {"type": "h2", "children": [{"text": "Get a quote"}]},
        {"type": "p", "children": [{"text": "Request a quote or ask for the datasheet."}]},
    ]


def test_paragraph_wall_blocks() -> None:
    r = check(pkg([prod(wall_body())]))
    assert r["pass"] is False
    assert any("WALL" in b for b in r["blockers"])


def test_well_formatted_passes() -> None:
    r = check(pkg([prod(good_body())]))
    assert r["pass"] is True, r["blockers"] + r["warnings"]


def test_missing_cta_warns() -> None:
    body = [
        {"type": "p", "children": [{"text": "Intro with "}, {"text": "bold", "bold": True}]},
        {"type": "h2", "children": [{"text": "Specs"}]},
        {"type": "h2", "children": [{"text": "Applications"}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "lab test"}]}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("no CTA" in w for w in r["warnings"])


def test_missing_headings_warns() -> None:
    body = [
        {"type": "p", "children": [{"text": "Intro "}, {"text": "b", "bold": True}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "request a quote"}]}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("section heading" in w for w in r["warnings"])


def test_missing_list_warns() -> None:
    body = [
        {"type": "p", "children": [{"text": "Intro "}, {"text": "b", "bold": True}]},
        {"type": "h2", "children": [{"text": "Why"}]},
        {"type": "h2", "children": [{"text": "Get a quote"}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("no bullet" in w for w in r["warnings"])


def test_no_bold_warns() -> None:
    body = [
        {"type": "p", "children": [{"text": "Intro"}]},
        {"type": "h2", "children": [{"text": "Why"}]},
        {"type": "h2", "children": [{"text": "Quote"}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "request a quote"}]}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("no bold" in w for w in r["warnings"])


def test_short_unstructured_not_a_wall() -> None:
    # A short body with no structure is not a "wall" block (only warnings), so a one-liner product isn't hard-blocked.
    r = check(pkg([prod([{"type": "p", "children": [{"text": "Short line."}]}])]))
    assert not any("WALL" in b for b in r["blockers"])


def test_long_paragraph_warns() -> None:
    body = [
        {"type": "h2", "children": [{"text": "A"}]},
        {"type": "h2", "children": [{"text": "B"}]},
        {"type": "p", "children": [{"text": "x " * 400, "bold": True}]},  # >600 chars, structured elsewhere
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "request a quote"}]}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("over-long paragraph" in w for w in r["warnings"])


def test_spec_terms_not_mistaken_for_cta() -> None:
    # "contact resistance" / "ordering code" are spec terms, not a CTA — must not suppress the no-CTA warning.
    body = [
        {"type": "p", "children": [{"text": "Intro "}, {"text": "b", "bold": True}]},
        {"type": "h2", "children": [{"text": "Specs"}]},
        {"type": "h2", "children": [{"text": "Why"}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "contact resistance 5 milliohms; ordering code PT-26"}]}]},
    ]
    r = check(pkg([prod(body)]))
    assert any("no CTA" in w for w in r["warnings"])


def test_strict_promotes_warnings() -> None:
    body = [
        {"type": "p", "children": [{"text": "Intro "}, {"text": "b", "bold": True}]},
        {"type": "h2", "children": [{"text": "Why"}]},
        {"type": "h2", "children": [{"text": "Quote"}]},
        {"type": "ul", "children": [{"type": "li", "children": [{"text": "request a quote"}]}]},
    ]  # passes non-strict but... actually this is well-formed; use a clearly-warned body:
    warned = [{"type": "p", "children": [{"text": "Intro "}, {"text": "b", "bold": True}]},
              {"type": "h2", "children": [{"text": "Only one heading, no list, no cta"}]}]
    assert check(pkg([prod(warned)]))["pass"] is True
    assert check(pkg([prod(warned)]), strict=True)["pass"] is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("content-format gate tests passed")
