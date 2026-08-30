#!/usr/bin/env python3
"""Regression tests for the theme design-save (pageDocument) replay validator."""
from __future__ import annotations

from validate_theme_page_document import validate_theme_replay, _iter_prop_strings


def _payload(**overrides) -> list:
    obj = {
        "siteId": "site-internal-id",
        "themeId": "theme-id",
        "pageId": "page-id",
        "intent": "save",
        "pageDocument": {
            "root": "page-root",
            "elements": {
                "hero-1": {
                    "type": "hero-commerce",
                    "props": {
                        "title": "Precision RF interconnect",
                        "media": {"type": "image", "value": {"url": "https://cdn.example/img/a.png"}},
                    },
                }
            },
        },
    }
    obj.update(overrides)
    return [obj]


def test_valid_payload_passes() -> None:
    r = validate_theme_replay(_payload())
    assert r["valid"] is True, r["issues"]
    assert r["elementCount"] == 1


def test_not_one_element_array_rejected() -> None:
    assert validate_theme_replay({"siteId": "x"})["valid"] is False
    assert validate_theme_replay([])["valid"] is False
    assert validate_theme_replay(_payload() + _payload())["valid"] is False


def test_missing_ids_rejected() -> None:
    r = validate_theme_replay(_payload(siteId=""))
    assert r["valid"] is False and any("siteId" in i for i in r["issues"])


def test_wrong_intent_rejected() -> None:
    r = validate_theme_replay(_payload(intent="publish"))
    assert r["valid"] is False and any("intent" in i for i in r["issues"])


def test_missing_root_and_elements_rejected() -> None:
    p = _payload()
    p[0]["pageDocument"] = {"root": "", "elements": {}}
    r = validate_theme_replay(p)
    assert r["valid"] is False
    assert any("root" in i for i in r["issues"]) or any("elements" in i for i in r["issues"])


def test_element_without_type_rejected() -> None:
    p = _payload()
    p[0]["pageDocument"]["elements"]["hero-1"].pop("type")
    r = validate_theme_replay(p)
    assert r["valid"] is False and any("type" in i for i in r["issues"])


def test_local_image_path_rejected() -> None:
    p = _payload()
    p[0]["pageDocument"]["elements"]["hero-1"]["props"]["media"]["value"]["url"] = "/Users/me/img/a.png"
    r = validate_theme_replay(p)
    assert r["valid"] is False and any("local/relative path" in i for i in r["issues"])


def test_placeholder_flagged_only_when_publication_ready() -> None:
    p = _payload()
    p[0]["pageDocument"]["elements"]["hero-1"]["props"]["title"] = "Draft Product placeholder"
    assert validate_theme_replay(p, require_publication_ready=False)["valid"] is True
    r = validate_theme_replay(p, require_publication_ready=True)
    assert r["valid"] is False and any("placeholder" in i for i in r["issues"])


def test_legit_your_copy_not_flagged() -> None:
    # "your" is common professional copy and must not trip the placeholder gate.
    p = _payload()
    p[0]["pageDocument"]["elements"]["hero-1"]["props"]["title"] = "Send us your instrument ports and test conditions"
    r = validate_theme_replay(p, require_publication_ready=True)
    assert r["valid"] is True, r["issues"]


def test_iter_prop_strings_nested() -> None:
    pairs = dict(_iter_prop_strings({"a": {"b": "x"}, "c": ["y"]}))
    assert pairs["a.b"] == "x" and pairs["c[0]"] == "y"


if __name__ == "__main__":
    test_valid_payload_passes()
    test_not_one_element_array_rejected()
    test_missing_ids_rejected()
    test_wrong_intent_rejected()
    test_missing_root_and_elements_rejected()
    test_element_without_type_rejected()
    test_local_image_path_rejected()
    test_placeholder_flagged_only_when_publication_ready()
    test_legit_your_copy_not_flagged()
    test_iter_prop_strings_nested()
    print("validate_theme_page_document regression tests passed")
