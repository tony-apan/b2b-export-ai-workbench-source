#!/usr/bin/env python3
"""Tests for the workspace scaffolder — the safety-critical parts are: never overwrite existing
client/site materials, and never scaffold inside the public skill package."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from init_workspace import cmd_init_workspace, cmd_new_client, cmd_new_site
from _common import skill_root


def _ws() -> Path:
    return Path(tempfile.mkdtemp(prefix="allincms-ws-"))


def test_init_creates_root_and_readme() -> None:
    ws = _ws()
    try:
        cmd_init_workspace(str(ws))
        assert (ws / "README.md").exists()
        assert (ws / "clients").is_dir()
        assert "私有" in (ws / "README.md").read_text(encoding="utf-8")  # the never-push warning
    finally:
        shutil.rmtree(ws)


def test_new_client_scaffolds_karpathy_layers() -> None:
    ws = _ws()
    try:
        cmd_new_client(str(ws), "acme-rf")
        c = ws / "clients" / "acme-rf"
        assert (c / "raw").is_dir()                      # append-only raw layer
        assert (c / "wiki" / "products").is_dir()        # distilled wiki layer
        assert (c / "sites").is_dir()
        for name in ("company.md", "brand.md", "contact.md"):
            assert (c / "wiki" / name).exists()
        assert (c / "brief.md").exists()
    finally:
        shutil.rmtree(ws)


def test_prefix_slug_sibling_both_indexed() -> None:
    # A new site whose slug is a PREFIX of an existing sibling must still get its own index row —
    # dedup must match the exact backtick-wrapped path, not a bare substring.
    ws = _ws()
    try:
        cmd_new_client(str(ws), "acme-rf")
        cmd_new_site(str(ws), "acme-rf", "eu-store-2")
        cmd_new_site(str(ws), "acme-rf", "eu-store")
        readme = (ws / "README.md").read_text(encoding="utf-8")
        assert "`clients/acme-rf/sites/eu-store`" in readme      # the prefix site is indexed
        assert "`clients/acme-rf/sites/eu-store-2`" in readme    # the sibling is still there
    finally:
        shutil.rmtree(ws)


def test_new_site_scaffolds_and_indexes() -> None:
    ws = _ws()
    try:
        cmd_new_client(str(ws), "acme-rf")
        cmd_new_site(str(ws), "acme-rf", "eu-store")
        s = ws / "clients" / "acme-rf" / "sites" / "eu-store"
        assert (s / "source-wiki").is_dir() and (s / "package").is_dir() and (s / "run").is_dir()
        assert (s / "brief.md").exists() and (s / "live.md").exists()
        bl = json.loads((s / "residue-blacklist.json").read_text(encoding="utf-8"))
        assert bl["kind"] == "allincms_template_residue_blacklist" and bl["terms"] == []
        assert "eu-store" in (ws / "README.md").read_text(encoding="utf-8")   # indexed
    finally:
        shutil.rmtree(ws)


def test_refuses_to_overwrite_existing_client() -> None:
    ws = _ws()
    try:
        cmd_new_client(str(ws), "acme-rf")
        (ws / "clients" / "acme-rf" / "raw" / "important.pdf").write_text("user data", encoding="utf-8")
        try:
            cmd_new_client(str(ws), "acme-rf")
        except SystemExit as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("must refuse to overwrite an existing client")
        assert (ws / "clients" / "acme-rf" / "raw" / "important.pdf").read_text(encoding="utf-8") == "user data"
    finally:
        shutil.rmtree(ws)


def test_refuses_to_overwrite_existing_site() -> None:
    ws = _ws()
    try:
        cmd_new_client(str(ws), "acme-rf")
        cmd_new_site(str(ws), "acme-rf", "eu-store")
        (ws / "clients" / "acme-rf" / "sites" / "eu-store" / "source-wiki" / "wip.json").write_text("{}", encoding="utf-8")
        try:
            cmd_new_site(str(ws), "acme-rf", "eu-store")
        except SystemExit as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("must refuse to overwrite an existing site")
    finally:
        shutil.rmtree(ws)


def test_new_site_requires_existing_client() -> None:
    ws = _ws()
    try:
        try:
            cmd_new_site(str(ws), "no-such", "eu-store")
        except SystemExit as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("new-site must require the client to exist first")
    finally:
        shutil.rmtree(ws)


def test_rejects_bad_slug() -> None:
    ws = _ws()
    try:
        for bad in ("Acme RF", "acme_rf", "-acme", "ACME"):
            try:
                cmd_new_client(str(ws), bad)
            except SystemExit as exc:
                assert "kebab-case" in str(exc)
            else:
                raise AssertionError(f"bad slug {bad!r} must be rejected")
    finally:
        shutil.rmtree(ws)


def test_rejects_workspace_inside_skill_package() -> None:
    inside = skill_root() / "should-not-be-created-here"
    try:
        cmd_init_workspace(str(inside))
    except SystemExit as exc:
        assert "OUTSIDE the skill package" in str(exc)
    else:
        raise AssertionError("must refuse to scaffold a workspace inside the public skill package")
    assert not inside.exists()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("workspace scaffolder tests passed")
