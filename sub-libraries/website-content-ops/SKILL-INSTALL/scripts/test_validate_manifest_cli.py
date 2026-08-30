#!/usr/bin/env python3
"""Regression tests for validate_manifest.py CLI output modes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def draft_manifest() -> dict:
    return {
        "kind": "allincms_bulk_content_manifest",
        "contentType": "products",
        "items": [
            {
                "name": "Example Product",
                "slug": "example-product",
                "description": "A practical example product for validation.",
                "content": [{"type": "paragraph", "text": "Example body."}],
            }
        ],
    }


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def script_path() -> Path:
    return Path(__file__).resolve().parent / "validate_manifest.py"


def test_validate_manifest_json_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = write_json(Path(tmp) / "manifest.json", draft_manifest())
        result = subprocess.run(
            [sys.executable, str(script_path()), "--json", str(manifest)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_manifest_validation"
        assert parsed["valid"] is True
        assert parsed["requireSchemaVerified"] is False
        assert parsed["issues"] == []
        assert "Manifest validation passed" not in result.stdout


def test_validate_manifest_json_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = write_json(Path(tmp) / "manifest.json", draft_manifest())
        result = subprocess.run(
            [sys.executable, str(script_path()), "--json", "--require-schema-verified", str(manifest)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert result.returncode == 1
        parsed = json.loads(result.stdout)
        assert parsed["valid"] is False
        assert parsed["requireSchemaVerified"] is True
        assert any("schemaVerified" in issue for issue in parsed["issues"])


def test_validate_manifest_help() -> None:
    result = subprocess.run(
        [sys.executable, str(script_path()), "--help"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert "Validate an AllinCMS posts/products manifest" in result.stdout
    assert "--require-schema-verified" in result.stdout
    assert "--json" in result.stdout
    assert result.stderr == ""


if __name__ == "__main__":
    test_validate_manifest_json_success()
    test_validate_manifest_json_failure()
    test_validate_manifest_help()
    print("validate manifest CLI regression tests passed.")
