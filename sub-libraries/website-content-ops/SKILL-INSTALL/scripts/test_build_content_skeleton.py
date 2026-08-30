#!/usr/bin/env python3
"""Tests for the generation-time authoring scaffold.

The key contract: a skeleton it emits is correct-by-construction — it PASSES check_content_format.
That is cross-checked here against the real gate, so the generator and the validator can't drift.
"""
from __future__ import annotations

from build_content_skeleton import build_product_body, build_post_body, process
from check_content_format import check as format_check
from check_content_quality import check as quality_check


def full_product() -> dict:
    return {
        "slug": "p-test", "name": "PT-26 Phase-Stable Cable",
        "description": "A phase-stable 26.5GHz test cable for lab and production RF measurement.",
        "specifications": [{"key": "Frequency", "value": "DC-26.5 GHz"},
                           {"key": "Phase drift", "value": "250 PPM"},
                           {"key": "Impedance", "value": "50 Ohm"}],
        "differentiators": ["Phase drift held to 250 PPM over the full band",
                            "Rated for 20,000 flex cycles"],
        "applications": ["VNA calibration", "Production RF test benches"],
    }


def _pkg(products=None, posts=None) -> dict:
    return {"contentPlan": {"products": products or [], "posts": posts or []}}


def test_full_product_skeleton_passes_format_gate() -> None:
    skel = build_product_body(full_product())
    assert skel["ready"] is True, skel["needs"]
    r = format_check(_pkg([{"slug": "p", "content": skel["content"]}]))
    assert r["pass"] is True, r["blockers"] + r["warnings"]


def test_full_product_skeleton_has_all_structure() -> None:
    from check_content_format import analyze_body
    a = analyze_body(build_product_body(full_product())["content"])
    assert a["headings"] >= 2
    assert a["lists"] >= 1
    assert a["hasBold"] is True
    assert a["hasCta"] is True


def test_thin_product_still_passes_format_but_flags_needs() -> None:
    # Missing specs/diffs/apps: structure is still correct (gate passes), but needs is non-empty and ready=False.
    skel = build_product_body({"slug": "x", "name": "Bare", "description": "A bare item."})
    assert skel["ready"] is False
    assert any("specifications" in n for n in skel["needs"])
    assert any("differentiators" in n for n in skel["needs"])
    r = format_check(_pkg([{"slug": "x", "content": skel["content"]}]))
    assert r["pass"] is True, r["blockers"] + r["warnings"]  # structure present even when source is thin


def test_post_skeleton_passes_format_gate() -> None:
    post = {"slug": "guide", "title": "How to choose a phase-stable cable",
            "excerpt": "Phase drift, not loss, is what breaks calibration budgets.",
            "mechanism": "Drift accumulates with temperature and flexing, so the spec that matters is PPM over the band.",
            "takeaways": ["Compare PPM over the full band, not a single point",
                          "Flex-cycle rating predicts bench lifetime"]}
    skel = build_post_body(post)
    assert skel["ready"] is True, skel["needs"]
    r = format_check(_pkg(posts=[{"slug": "g", "content": skel["content"]}]))
    assert r["pass"] is True, r["blockers"] + r["warnings"]


def test_apply_writes_body_only_when_thin() -> None:
    thick_body = [{"type": "p", "children": [{"text": "x " * 200}]}]  # already authored
    pkg = _pkg([full_product(), {"slug": "keep", "name": "Keep", "content": thick_body}])
    report = process(pkg, apply=True)
    # first product had no content -> applied; second had a long body -> preserved
    assert report["appliedCount"] == 1
    assert pkg["contentPlan"]["products"][1]["content"] is thick_body


def test_apply_result_passes_format_gate() -> None:
    pkg = _pkg([full_product()])
    process(pkg, apply=True)
    r = format_check(pkg)
    assert r["pass"] is True, r["blockers"] + r["warnings"]


def test_fill_markers_present_when_source_missing() -> None:
    skel = build_product_body({"slug": "x", "name": "Bare"})
    text = str(skel["content"])
    assert "[fill:" in text  # thin source surfaces explicit fill markers, not fabricated content


def test_unfilled_skeleton_is_blocked_by_quality_gate() -> None:
    # The real safety loop: a skeleton whose [fill:] markers were never replaced must NOT publish.
    # The format gate passes on structure, but the quality gate must hard-block the leftover markers.
    skel = build_product_body({"slug": "x", "name": "Bare"})  # thin source -> [fill:] markers remain
    pkg = {"contentPlan": {"products": [{"slug": "x", "name": "Bare", "content": skel["content"]}]}}
    assert format_check(pkg)["pass"] is True                 # structure is correct-by-construction
    q = quality_check(pkg)
    assert q["pass"] is False, "unfilled [fill:] markers must be a quality blocker"
    assert any("fill" in b.lower() or "placeholder" in b.lower() for b in q["blockers"])


def test_filled_skeleton_passes_both_gates() -> None:
    # Once real leaf text replaces the markers, both gates pass — the intended happy path.
    pkg = {"contentPlan": {"products": [{"slug": "p", "name": "PT-26",
                                         "content": build_product_body(full_product())["content"]}]}}
    assert format_check(pkg)["pass"] is True
    assert quality_check(pkg)["pass"] is True, quality_check(pkg)["blockers"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("content-skeleton tests passed")
