#!/usr/bin/env python3
"""Regression tests for PicGo media upload + content link rewriting."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from upload_media_via_picgo import (
    build,
    collect_local_image_paths,
    rewrite_links,
    validate_upload_map,
)

# Minimal valid 1x1 PNG bytes.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000154a24f0d0000000049454e44ae426082"
)


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def make_image(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_BYTES)
    return str(path)


def make_wiki(root: Path) -> tuple[Path, str]:
    cover = make_image(root / "images" / "titancut-cover.png")
    wiki = {
        "kind": "allincms_source_wiki",
        "media": [{"path": cover, "name": "titancut-cover.png", "requiresUserApprovalBeforeUpload": True}],
        "products": [
            {
                "slug": "titancut-x200",
                "content": [
                    {"type": "paragraph", "text": f"Rugged plasma cutter. ![cover]({cover}) Clean 50mm cuts."}
                ],
                "mediaNeeds": [{"target": "product.cover", "kind": "cover", "sourceHint": cover}],
            }
        ],
        "posts": [],
        "pages": [],
    }
    return write_json(root / "source-wiki.json", wiki), cover


def base_args(root: Path, wiki_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=str(wiki_path),
        image=[],
        endpoint="http://127.0.0.1:36677/upload",
        output=str(root / "media-upload-map.json"),
        rewrite_wiki_output="",
        dry_run=False,
        confirm_upload=False,
        json=False,
    )


def fake_uploader(paths, endpoint):
    assert endpoint == "http://127.0.0.1:36677/upload"
    return [f"https://cdn.example.com/{Path(p).name}" for p in paths]


def test_collect_finds_media_and_markdown_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path, cover = make_wiki(root)
        wiki = json.loads(wiki_path.read_text(encoding="utf-8"))
        found = collect_local_image_paths(wiki, [])
        # The same cover is referenced in media[], product body markdown, and mediaNeeds;
        # it must be de-duplicated to a single distinct local path.
        assert found == [cover], found


def test_collect_finds_site_and_siteinfo_images() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hero = make_image(root / "images" / "hero.png")
        logo = make_image(root / "images" / "logo.png")
        wiki = {
            "kind": "allincms_source_wiki",
            "site": {"siteName": "X", "heroImage": hero},
            "siteInfo": {"logo": logo},
            "media": [], "products": [], "posts": [], "pages": [],
        }
        found = collect_local_image_paths(wiki, [])
        # Logo and hero live in site/siteInfo, not media/pages/products/posts; both must be collected.
        assert set(found) == {hero, logo}, found


def test_dry_run_plans_without_upload_or_rewrite() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path, _cover = make_wiki(root)
        args = base_args(root, wiki_path)
        args.dry_run = True
        args.rewrite_wiki_output = str(root / "wiki.rewritten.json")
        result = build(args, uploader=fake_uploader)
        upload_map = json.loads(Path(result["uploadMap"]).read_text(encoding="utf-8"))
        assert upload_map["dryRun"] is True
        assert upload_map["imageHostUploadPerformed"] is False
        assert upload_map["imageCount"] == 1
        assert upload_map["images"][0]["uploaded"] is False
        assert upload_map["images"][0]["hostedUrl"] == ""
        assert not validate_upload_map(upload_map)
        # No rewrite is produced in dry-run.
        assert result["rewrittenWiki"] == ""
        assert not (root / "wiki.rewritten.json").exists()


def test_real_upload_rewrites_links_and_records_map() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path, cover = make_wiki(root)
        args = base_args(root, wiki_path)
        args.confirm_upload = True
        args.rewrite_wiki_output = str(root / "wiki.rewritten.json")
        result = build(args, uploader=fake_uploader)
        upload_map = json.loads(Path(result["uploadMap"]).read_text(encoding="utf-8"))
        assert upload_map["dryRun"] is False
        assert upload_map["imageHostUploadPerformed"] is True
        assert upload_map["allincmsRemoteMutationsPerformed"] is False
        img = upload_map["images"][0]
        assert img["hostedUrl"] == "https://cdn.example.com/titancut-cover.png"
        assert img["uploaded"] is True
        assert len(img["sha256"]) == 64
        assert not validate_upload_map(upload_map)
        # Rewritten wiki: local paths replaced by hosted URL everywhere.
        rewritten = json.loads(Path(result["rewrittenWiki"]).read_text(encoding="utf-8"))
        media0 = rewritten["media"][0]
        assert media0["path"] == "https://cdn.example.com/titancut-cover.png"
        assert media0["hostedUrl"] == "https://cdn.example.com/titancut-cover.png"
        assert media0["localSourcePath"] == cover
        assert media0["uploaded"] is True
        body = rewritten["products"][0]["content"][0]["text"]
        assert "https://cdn.example.com/titancut-cover.png" in body
        assert cover not in body  # local link replaced
        assert rewritten["products"][0]["mediaNeeds"][0]["sourceHint"] == "https://cdn.example.com/titancut-cover.png"


def test_real_upload_requires_confirm_flag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path, _cover = make_wiki(root)
        args = base_args(root, wiki_path)  # confirm_upload=False, dry_run=False
        raised = ""
        try:
            build(args, uploader=fake_uploader)
        except SystemExit as exc:
            raised = str(exc)
        assert "--confirm-upload" in raised, raised


def test_real_upload_rejects_missing_local_image() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki = {
            "kind": "allincms_source_wiki",
            "media": [{"path": str(root / "images" / "does-not-exist.png"), "name": "x.png"}],
            "products": [],
            "posts": [],
            "pages": [],
        }
        wiki_path = write_json(root / "source-wiki.json", wiki)
        args = base_args(root, wiki_path)
        args.confirm_upload = True
        raised = ""
        try:
            build(args, uploader=fake_uploader)
        except SystemExit as exc:
            raised = str(exc)
        assert "missing local images" in raised, raised


def test_validate_rejects_unhosted_after_real_upload() -> None:
    bad = {
        "kind": "allincms_media_upload_map",
        "dryRun": False,
        "imageHostIsExternal": True,
        "allincmsRemoteMutationsPerformed": False,
        "images": [{"localPath": "/tmp/a.png", "hostedUrl": "/tmp/a.png", "uploaded": True, "sha256": "0" * 64}],
    }
    issues = validate_upload_map(bad)
    assert any("hostedUrl must be an http(s) URL" in i for i in issues), issues


def test_output_must_be_outside_skill() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_path, _cover = make_wiki(root)
        args = base_args(root, wiki_path)
        args.dry_run = True
        skill_scripts = Path(__file__).resolve().parent
        args.output = str(skill_scripts / "should-not-write.json")
        raised = ""
        try:
            build(args, uploader=fake_uploader)
        except SystemExit as exc:
            raised = str(exc)
        assert "outside the skill package" in raised, raised
        assert not (skill_scripts / "should-not-write.json").exists()


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    for name in sorted(dir(current_module)):
        if name.startswith("test_"):
            getattr(current_module, name)()
    print("media picgo upload regression tests passed.")
