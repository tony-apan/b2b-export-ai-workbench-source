#!/usr/bin/env python3
"""Tests for the PicGo reachability probe + two-paths setup guidance."""
from __future__ import annotations

import argparse
import os
import tempfile

from upload_media_via_picgo import probe_picgo, picgo_setup_guidance, build


def test_probe_unreachable_port_fails_fast() -> None:
    # Port 9 is not a PicGo server; probe must return False quickly, not hang for 60s.
    ok, detail = probe_picgo("http://127.0.0.1:9/upload", timeout=1.0)
    assert ok is False
    assert "not reachable" in detail


def test_guidance_offers_both_paths_cross_platform() -> None:
    g = picgo_setup_guidance("http://127.0.0.1:36677/upload")
    assert "36677" in g
    assert "PicGo" in g and "Media module" in g   # both routes (install PicGo OR backend media)
    assert "brew" in g and "winget" in g          # macOS + Windows install


def test_build_stops_with_guidance_when_picgo_unreachable() -> None:
    # confirm-upload but PicGo down: build must raise guidance and NEVER call the uploader.
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        fh.write(b"\x89PNG\r\n")
        img = fh.name
    calls: list = []
    try:
        args = argparse.Namespace(
            wiki="", image=[img], endpoint="http://127.0.0.1:9/upload", output="unused",
            rewrite_wiki_output="", dry_run=False, confirm_upload=True,
        )
        build(args, uploader=lambda p, e: calls.append(p) or ["http://x"],
              prober=lambda e: (False, "down"))
    except SystemExit as exc:
        assert "PicGo" in str(exc) and "Media module" in str(exc)
        assert calls == []  # uploader never reached
    else:
        raise AssertionError("unreachable PicGo must stop the upload")
    finally:
        os.unlink(img)


def test_build_reachable_proceeds_to_upload() -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        fh.write(b"\x89PNG\r\n")
        img = fh.name
    out = img + ".map.json"
    try:
        args = argparse.Namespace(
            wiki="", image=[img], endpoint="http://127.0.0.1:36677/upload", output=out,
            rewrite_wiki_output="", dry_run=False, confirm_upload=True,
        )
        result = build(args, uploader=lambda p, e: ["https://host/img.png"],
                       prober=lambda e: (True, "up"))
        assert result["imageHostUploadPerformed"] is True
    finally:
        os.unlink(img)
        if os.path.exists(out):
            os.unlink(out)


if __name__ == "__main__":
    test_probe_unreachable_port_fails_fast()
    test_guidance_offers_both_paths_cross_platform()
    test_build_stops_with_guidance_when_picgo_unreachable()
    test_build_reachable_proceeds_to_upload()
    print("upload_media_via_picgo probe/guidance tests passed")
