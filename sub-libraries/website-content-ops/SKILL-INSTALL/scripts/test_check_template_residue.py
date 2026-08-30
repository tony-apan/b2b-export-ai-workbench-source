#!/usr/bin/env python3
"""Tests for the whole-site template-residue gate."""
from __future__ import annotations

from check_template_residue import check


def blacklist() -> dict:
    return {"terms": [
        {"value": "Wanderlust Outfitters", "label": "old_brand"},
        {"value": "Weekender Tote", "label": "old_product"},
        {"value": "Travel Essentials", "label": "old_category"},
        {"value": "buildnbuzz.com", "label": "old_email"},
    ]}


def fe(routes) -> dict:
    return {"routes": routes}


def test_clean_site_passes() -> None:
    frontend = fe([
        {"route": "/", "text": "EXAMPLE RF Technology — DC-67GHz test cables from Shenzhen."},
        {"route": "/products/f-test", "text": "F-TEST Super Flexible Test Cable. Category: RF Cables. contact via the site form"},
    ])
    r = check(blacklist(), frontend)
    assert r["pass"] is True, r["residueHits"]
    assert r["residueHits"] == []


def test_category_chip_residue_blocks() -> None:
    # The exact screenshot failure: an RF cable still carrying the old "Travel Essentials" category chip.
    frontend = fe([{"route": "/products/f-test", "text": "F-TEST Test Cable — Category: Travel Essentials"}])
    r = check(blacklist(), frontend)
    assert r["pass"] is False
    hit = r["residueHits"][0]
    assert hit["term"] == "Travel Essentials" and hit["route"] == "/products/f-test" and hit["label"] == "old_category"


def test_contact_residue_in_footer_blocks() -> None:
    frontend = fe([{"route": "/", "text": "Home hero copy is fine. Footer: contact buildnbuzz.com"}])
    r = check(blacklist(), frontend)
    assert r["pass"] is False
    assert any(h["term"] == "buildnbuzz.com" for h in r["residueHits"])


def test_case_insensitive() -> None:
    frontend = fe([{"route": "/about", "text": "we are wanderlust OUTFITTERS, a retailer"}])
    r = check(blacklist(), frontend)
    assert any(h["term"] == "Wanderlust Outfitters" for h in r["residueHits"])


def test_multiple_routes_multiple_hits() -> None:
    frontend = fe([
        {"route": "/", "text": "Weekender Tote featured"},
        {"route": "/about", "text": "Wanderlust Outfitters team"},
        {"route": "/products/x", "text": "clean RF copy"},
    ])
    r = check(blacklist(), frontend)
    assert r["pass"] is False
    routes_hit = {h["route"] for h in r["residueHits"]}
    assert routes_hit == {"/", "/about"}


def test_empty_blacklist_errors() -> None:
    r = check({"terms": []}, fe([{"route": "/", "text": "x"}]))
    assert r["pass"] is False and any("blacklist has no terms" in e for e in r["errors"])


def test_empty_frontend_errors() -> None:
    r = check(blacklist(), {"routes": []})
    assert r["pass"] is False and any("no routes" in e for e in r["errors"])


def test_short_term_warns() -> None:
    r = check({"terms": ["RF", "Wanderlust Outfitters"]}, fe([{"route": "/", "text": "clean"}]))
    assert any("collision-prone" in w for w in r["warnings"])


def test_plain_string_terms_accepted() -> None:
    r = check({"terms": ["Weekender Tote"]}, fe([{"route": "/", "text": "the Weekender Tote is here"}]))
    assert r["pass"] is False and r["residueHits"][0]["term"] == "Weekender Tote"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("template-residue gate tests passed")
