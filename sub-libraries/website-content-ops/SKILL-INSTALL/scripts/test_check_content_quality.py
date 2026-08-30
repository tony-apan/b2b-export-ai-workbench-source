#!/usr/bin/env python3
"""Tests for the pre-publish content-quality gate (incl. real field-contract image shapes)."""
from __future__ import annotations

from check_content_quality import check, is_stock_image


def clean_product(**overrides) -> dict:
    p = {
        "name": "Z-TEST RF Test Cable DC-26.5GHz",
        "slug": "z-test-rf-cable",
        "description": "Low-loss 50-ohm RF test cable assembly for 26.5 GHz production and lab test.",
        "specifications": [
            {"key": "Frequency", "value": "DC-26.5 GHz"},
            {"key": "Impedance", "value": "50 ohm"},
            {"key": "Connector", "value": "SMA male / SMA male"},
        ],
        "content": [{"type": "paragraph", "children": [{"text": "Phase-stable assembly with 0.03 dB insertion-loss repeatability."}]}],
        "coverImage": {"source": "url", "type": "image", "url": "https://cdn.example-host.net/z-test-cable.jpg",
                       "name": "z", "alt": "26.5GHz RF test cable with SMA connectors"},
    }
    p.update(overrides)
    return p


def pkg(products=None, posts=None, media=None) -> dict:
    cp = {"products": products or [], "posts": posts or []}
    if media is not None:
        cp["media"] = media
    return {"contentPlan": cp}


def test_clean_product_passes() -> None:
    r = check(pkg([clean_product()]))
    assert r["pass"] is True, r["blockers"] + r["warnings"]
    assert r["blockers"] == []


# --- Finding 1: real field-contract image shapes must be scanned for stock + alt ---

def test_coverimage_stock_blocks() -> None:
    p = clean_product(coverImage={"type": "image", "url": "https://images.unsplash.com/p", "alt": "x"})
    r = check(pkg([p]))
    assert r["pass"] is False and any("stock" in b for b in r["blockers"])


def test_media_object_stock_blocks() -> None:
    p = clean_product(media={"type": "image", "url": "https://www.pexels.com/x.jpg", "alt": "x"})
    r = check(pkg([p]))
    assert r["pass"] is False and any("stock" in b for b in r["blockers"])


def test_media_array_stock_blocks() -> None:
    # media as an ARRAY (field-contract line 189) — the dict-only version missed this.
    p = clean_product(media=[{"type": "image", "url": "https://images.unsplash.com/a", "alt": "a"}])
    r = check(pkg([p]))
    assert r["pass"] is False and any("stock" in b for b in r["blockers"])


def test_gallery_stock_blocks() -> None:
    p = clean_product(gallery=[{"type": "image", "url": "https://pixabay.com/g.jpg", "alt": "g"}])
    r = check(pkg([p]))
    assert r["pass"] is False and any("stock" in b for b in r["blockers"])


def test_toplevel_media_stock_blocks() -> None:
    r = check(pkg([clean_product()], media=[{"type": "image", "url": "https://images.unsplash.com/top"}]))
    assert r["pass"] is False and any("stock" in b for b in r["blockers"])


def test_main_image_missing_alt_blocks() -> None:
    p = clean_product(coverImage={"type": "image", "url": "https://cdn.example-host.net/x.jpg", "alt": ""})
    r = check(pkg([p]))
    assert r["pass"] is False and any("alt text" in b for b in r["blockers"])


def test_gallery_missing_alt_warns_not_blocks() -> None:
    # A gallery image may be decorative — missing alt is a warning, not a hard block (field-contract line 191).
    p = clean_product(gallery=[{"type": "image", "url": "https://cdn.example-host.net/g.jpg", "alt": ""}])
    r = check(pkg([p]))
    assert r["pass"] is True
    assert any("gallery image" in w and "no alt" in w for w in r["warnings"])


# --- Finding 2 & 3: placeholder false positives ---

def test_tbd_model_number_not_blocked() -> None:
    p = clean_product(name="TBD-500 Thermal Barrier Diode", slug="tbd-500")
    r = check(pkg([p]))
    assert not any("placeholder" in b for b in r["blockers"])  # TBD-500 is a real model, not a placeholder


def test_standalone_tbd_blocks() -> None:
    p = clean_product(specifications=[{"key": "Price", "value": "TBD"},
                                      {"key": "Frequency", "value": "DC-26.5 GHz"},
                                      {"key": "Impedance", "value": "50 ohm"}])
    r = check(pkg([p]))
    assert r["pass"] is False and any("placeholder" in b for b in r["blockers"])


def test_example_com_warns_not_blocks() -> None:
    p = clean_product(description="A full 40+ char description; configure your part at example.com/configurator online.")
    r = check(pkg([p]))
    assert r["pass"] is True  # not a hard block
    assert any("example.com" in w for w in r["warnings"])


# --- Finding 4: stock host must match netloc, not a substring of the whole URL ---

def test_stock_host_in_path_not_blocked() -> None:
    assert is_stock_image("https://cdn.acme.net/blog/goodbye-unsplash.com-forever.jpg") is False
    assert is_stock_image("https://images.unsplash.com/photo-1") is True
    assert is_stock_image("https://sub.pexels.com/x.jpg") is True


# --- Other detectors (unchanged behavior) ---

def test_wrong_category_specs_warn_not_block() -> None:
    p = clean_product(specifications=[
        {"key": "Material", "value": "Recycled nylon ripstop"},
        {"key": "Closure", "value": "YKK coil zipper"},
        {"key": "Use", "value": "Tech, travel, and small repair kits"},
    ])
    r = check(pkg([p]))
    assert any("off-category" in w for w in r["warnings"])
    assert not any("off-category" in b for b in r["blockers"])


def test_thin_specs_warn() -> None:
    p = clean_product(specifications=[{"key": "Frequency", "value": "DC-26.5 GHz"}])
    r = check(pkg([p]))
    assert any("decision-grade spec" in w for w in r["warnings"])


def test_duplicate_copy_warns() -> None:
    body = [{"type": "paragraph", "children": [{"text": "Identical marketing paragraph reused across two different products verbatim here."}]}]
    r = check(pkg([clean_product(slug="a", content=body), clean_product(slug="b", content=body)]))
    assert any("duplicate" in w for w in r["warnings"])


def test_strict_promotes_warnings_to_failure() -> None:
    p = clean_product(specifications=[{"key": "Frequency", "value": "DC-26.5 GHz"}])  # thin -> warning
    assert check(pkg([p]))["pass"] is True
    assert check(pkg([p]), strict=True)["pass"] is False


def test_post_placeholder_and_stock() -> None:
    post = {"slug": "guide", "title": "How to choose", "excerpt": "A real excerpt about choosing cables for lab use.",
            "content": [{"type": "image", "url": "https://unsplash.com/x"}, {"type": "paragraph", "children": [{"text": "TODO write this"}]}]}
    r = check(pkg(posts=[post]))
    assert r["pass"] is False
    assert any("stock" in b for b in r["blockers"]) and any("placeholder" in b for b in r["blockers"])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("content-quality gate tests passed")
