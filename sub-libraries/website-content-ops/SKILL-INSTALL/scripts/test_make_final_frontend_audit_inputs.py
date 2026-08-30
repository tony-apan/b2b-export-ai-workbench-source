#!/usr/bin/env python3
"""Regression tests for make_final_frontend_audit_inputs.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from make_final_frontend_audit_inputs import (
    build_inputs,
    build_inputs_for_manifests,
    load_manifest,
    validate_progress_for_manifests,
)


BASE = "https://example.web.allincms.com"


def manifest(content_type: str, slugs: list[str]) -> dict:
    return {
        "siteKey": "example",
        "frontendBaseUrl": BASE,
        "contentType": content_type,
        "schemaVerified": True,
        "fieldMapping": {"title": "title", "slug": "slug"},
        "payloadTemplate": {"siteId": "{siteId}", "mode": "update", "content": "{contentBlocks}"},
        "items": [
            {
                "operation": "create",
                **({"name": slug.replace("-", " ").title()} if content_type == "products" else {"title": slug.replace("-", " ").title()}),
                "slug": slug,
                **(
                    {"description": f"Description for {slug}."}
                    if content_type == "products"
                    else {"excerpt": f"Excerpt for {slug}."}
                ),
                "coverImage": {"url": "https://example.com/image.jpg", "alt": slug},
                "content": [{"type": "paragraph", "children": [{"text": f"Body for {slug}."}]}],
            }
            for slug in slugs
        ],
    }


def progress(content_type: str, slugs: list[str]) -> list[dict]:
    return [
        {
            "slug": slug,
            "contentType": content_type,
            "saveStatus": "ok",
            "publishStatus": "ok",
            "backendVerified": True,
            "frontendVerified": True,
            "coverOrMediaVerified": True,
            "errors": [],
        }
        for slug in slugs
    ]


def test_single_manifest_compatibility() -> None:
    products = manifest("products", ["sample-product-one"])
    urls, statuses, summary = build_inputs(products, BASE, ["/", "/products"])
    assert urls == [
        f"{BASE}/",
        f"{BASE}/products",
        f"{BASE}/products/sample-product-one",
    ]
    assert statuses[f"{BASE}/products/sample-product-one"] == 200
    assert summary["contentType"] == "products"
    assert summary["contentTypes"] == ["products"]
    assert summary["detailRouteCountByContentType"] == {"products": 1}


def test_mixed_products_posts_generate_one_final_audit_set() -> None:
    products = manifest("products", ["sample-product-one", "sample-product-two"])
    posts = manifest("posts", ["sample-post-one"])
    urls, statuses, summary = build_inputs_for_manifests([products, posts], BASE, ["/", "/products", "/posts"])
    assert f"{BASE}/products/sample-product-one" in urls
    assert f"{BASE}/products/sample-product-two" in urls
    assert f"{BASE}/posts/sample-post-one" in urls
    assert set(statuses.values()) == {200}
    assert summary["contentType"] == "mixed"
    assert summary["contentTypes"] == ["products", "posts"]
    assert summary["detailRouteCount"] == 3
    assert summary["detailRouteCountByContentType"] == {"products": 2, "posts": 1}
    assert "/products/{slug}" in summary["routePatterns"]
    assert "/posts/{slug}" in summary["routePatterns"]


def test_mixed_progress_accepts_one_combined_log() -> None:
    products = manifest("products", ["sample-product-one"])
    posts = manifest("posts", ["sample-post-one"])
    with tempfile.TemporaryDirectory() as tmp:
        progress_path = Path(tmp) / "progress.json"
        progress_path.write_text(
            json.dumps({"progressLog": progress("products", ["sample-product-one"]) + progress("posts", ["sample-post-one"])}) + "\n",
            encoding="utf-8",
        )
        assert validate_progress_for_manifests([products, posts], [progress_path]) == []


def test_mixed_progress_rejects_same_type_extra_slug_in_combined_log() -> None:
    products = manifest("products", ["sample-product-one"])
    posts = manifest("posts", ["sample-post-one"])
    with tempfile.TemporaryDirectory() as tmp:
        progress_path = Path(tmp) / "progress.json"
        progress_path.write_text(
            json.dumps(
                {
                    "progressLog": progress("products", ["sample-product-one", "extra-product"])
                    + progress("posts", ["sample-post-one"])
                }
            )
            + "\n",
            encoding="utf-8",
        )
        errors = validate_progress_for_manifests([products, posts], [progress_path])
        assert any("extra-product is not present in manifest" in error for error in errors), errors


def test_repeated_progress_logs_must_match_manifest_count() -> None:
    products = manifest("products", ["sample-product-one"])
    posts = manifest("posts", ["sample-post-one"])
    with tempfile.TemporaryDirectory() as tmp:
        one = Path(tmp) / "one.json"
        two = Path(tmp) / "two.json"
        three = Path(tmp) / "three.json"
        for path in (one, two, three):
            path.write_text(json.dumps({"progressLog": []}) + "\n", encoding="utf-8")
        errors = validate_progress_for_manifests([products, posts], [one, two, three])
        assert any("count must be 1 or match --manifest count" in error for error in errors), errors


def test_cli_accepts_repeated_manifest_flags() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        products_path = root / "products.json"
        posts_path = root / "posts.json"
        urls_path = root / "urls.txt"
        statuses_path = root / "statuses.json"
        summary_path = root / "summary.json"
        products_path.write_text(json.dumps(manifest("products", ["sample-product-one"])) + "\n", encoding="utf-8")
        posts_path.write_text(json.dumps(manifest("posts", ["sample-post-one"])) + "\n", encoding="utf-8")
        assert load_manifest(products_path, True)["contentType"] == "products"
        from make_final_frontend_audit_inputs import main

        import sys

        old_argv = sys.argv
        try:
            sys.argv = [
                "make_final_frontend_audit_inputs.py",
                "--manifest",
                str(products_path),
                "--manifest",
                str(posts_path),
                "--require-schema-verified",
                "--static-paths",
                "/,/products,/posts",
                "--urls-output",
                str(urls_path),
                "--statuses-output",
                str(statuses_path),
                "--summary-output",
                str(summary_path),
            ]
            assert main() == 0
        finally:
            sys.argv = old_argv
        assert f"{BASE}/products/sample-product-one" in urls_path.read_text(encoding="utf-8")
        assert f"{BASE}/posts/sample-post-one" in urls_path.read_text(encoding="utf-8")
        assert json.loads(summary_path.read_text(encoding="utf-8"))["contentType"] == "mixed"


if __name__ == "__main__":
    test_single_manifest_compatibility()
    test_mixed_products_posts_generate_one_final_audit_set()
    test_mixed_progress_accepts_one_combined_log()
    test_mixed_progress_rejects_same_type_extra_slug_in_combined_log()
    test_repeated_progress_logs_must_match_manifest_count()
    test_cli_accepts_repeated_manifest_flags()
    print("final frontend audit input regression tests passed.")
