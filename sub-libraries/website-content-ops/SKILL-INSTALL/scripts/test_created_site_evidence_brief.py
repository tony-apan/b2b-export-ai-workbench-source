#!/usr/bin/env python3
"""Regression tests for post-create created-site evidence brief generation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from build_confirmed_create_site_handoff import build_handoff
from make_created_site_evidence_brief import build
from test_confirmed_create_site_handoff import prepare_inputs, write_json


def handoff_file(root: Path) -> Path:
    args = prepare_inputs(root)
    handoff = build_handoff(args)
    path = Path(args.output)
    write_json(path, handoff)
    return path


def test_created_site_evidence_brief_is_post_submit_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = handoff_file(root)
        brief_path = root / "created-site-evidence-brief.json"
        brief = build(
            argparse.Namespace(
                create_site_handoff=str(handoff_path),
                output=str(brief_path),
                created_site_evidence_output=str(root / "created-site-evidence.json"),
                json=False,
            )
        )
        assert brief["kind"] == "allincms_created_site_evidence_brief"
        assert brief["localOnly"] is True
        assert brief["remoteMutationsPerformed"] is False
        assert brief["isUserAuthorization"] is False
        assert brief["preflight"].endswith("create-preflight.json")
        assert brief["createdSiteEvidenceOutput"].endswith("created-site-evidence.json")
        assert "make_created_site_evidence.py" in brief["makeCreatedSiteEvidenceCommandTemplate"]
        assert "--submitted-values" in brief["makeCreatedSiteEvidenceCommandTemplate"]
        assert "prepare_created_site_schema_capture.py" in brief["nextCommandAfterCreatedEvidence"]
        assert "do not create products/posts/media probes" in brief["forbiddenActions"]
        assert "products" in brief["requiredEvidence"]["moduleRoutes"]
        assert brief["requiredEvidence"]["submittedValues"]["name"] == "Example Demo"
        assert brief["requiredEvidence"]["submittedValues"]["description"] == brief["siteProposal"]["siteDescription"]
        assert brief_path.exists()


if __name__ == "__main__":
    test_created_site_evidence_brief_is_post_submit_only()
    print("created-site evidence brief regression tests passed.")
