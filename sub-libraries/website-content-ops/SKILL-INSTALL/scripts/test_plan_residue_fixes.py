#!/usr/bin/env python3
"""Tests for the residue fix-plan router (residue hits -> per-type fix work-order)."""
from __future__ import annotations

from plan_residue_fixes import classify, plan


def rep(hits) -> dict:
    return {"residueHits": hits}


def h(route, term, label) -> dict:
    return {"route": route, "term": term, "label": label}


def _type_of(hits) -> str:
    groups = plan(rep(hits))["fixGroups"]
    assert len(groups) == 1
    return groups[0]["fixType"]


def test_product_route_to_product_detail() -> None:
    assert _type_of([h("/products/f-test", "Weekender Tote", "old_product")]) == "product_detail"


def test_post_route_to_post_detail() -> None:
    assert _type_of([h("/posts/how-to", "Old Author", "old_author")]) == "post_detail"


def test_category_label_to_taxonomy_chip_any_route() -> None:
    # The screenshot failure: an RF cable card still showing "Travel Essentials" — fix in the backend tab.
    assert classify("/products/f-test", "old_category") == "taxonomy_chip"
    assert classify("/", "old_category") == "taxonomy_chip"
    assert classify("/posts/x", "old_tag") == "taxonomy_chip"


def test_standalone_page_to_theme_page() -> None:
    assert _type_of([h("/about", "Wanderlust Outfitters", "old_brand_page_copy")]) == "theme_page"


def test_contact_label_to_global_block() -> None:
    # Old email/phone/address in the footer -> global block, not a page edit.
    assert classify("/", "old_email") == "global_block"
    assert classify("/contact", "old_phone") == "global_block"


def test_homepage_generic_to_homepage_module() -> None:
    assert classify("/", "old_content") == "homepage_module"


def test_groups_multiple_types() -> None:
    r = plan(rep([
        h("/products/f-test", "Travel Essentials", "old_category"),   # taxonomy_chip
        h("/products/g-test", "Weekender Tote", "old_product"),       # product_detail
        h("/posts/guide", "buildnbuzz.com", "old_domain"),           # post_detail (route wins over contact label)
        h("/", "buildnbuzz.com", "old_email"),                       # global_block
        h("/about", "Wanderlust Outfitters", "old_brand"),           # global_block (brand is a contact label) OR page
    ]))
    types = {g["fixType"] for g in r["fixGroups"]}
    assert "taxonomy_chip" in types and "product_detail" in types and "post_detail" in types and "global_block" in types
    assert r["totalHits"] == 5


def test_every_group_has_method_and_verify() -> None:
    r = plan(rep([h("/products/x", "t", "old_product"), h("/", "t", "old_email")]))
    for g in r["fixGroups"]:
        assert g["method"].strip() and g["verifyAfter"].strip()


def test_hard_contact_wins_over_route() -> None:
    # An email/phone/address on a product/post route is still a global block (footer), not the item schema.
    assert classify("/products/x", "old_email") == "global_block"
    assert classify("/posts/y", "old_phone") == "global_block"
    assert classify("/products/x", "old_address") == "global_block"


def test_soft_contact_on_product_route_stays_product() -> None:
    # Brand in product body copy → fix in the product save; route wins for soft-contact labels.
    assert classify("/products/x", "old_brand") == "product_detail"
    assert classify("/posts/y", "old_domain") == "post_detail"
    assert classify("/about", "old_brand") == "global_block"   # but off a product/post route → global block


def test_malformed_hits_counted_not_silent() -> None:
    r = plan(rep(["not-a-dict", 123, {"route": "/products/x", "term": "t", "label": "old_product"}]))
    assert r["totalHits"] == 1 and r["skippedMalformed"] == 2
    assert sum(g["hitCount"] for g in r["fixGroups"]) == r["totalHits"]   # invariant holds


def test_empty_report() -> None:
    r = plan(rep([]))
    assert r["totalHits"] == 0 and r["fixGroups"] == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("residue fix-plan tests passed")
