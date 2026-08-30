#!/usr/bin/env python3
"""Tests for make_resolved_source_input_gaps.py."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_resolved_source_input_gaps
import record_source_input_gap
from make_source_input_requirements import build_report as build_requirements_report


def write_gap_ledger(path: Path) -> None:
    Args = type("Args", (), {})
    Args.action = "append"
    Args.output = str(path)
    Args.site_key = "mysite01"
    Args.content_type = "posts"
    Args.field = "post-detail-route"
    Args.target = "themes/pages.posts-detail,routes.posts-dynamic"
    Args.classification = "blocked-until-schema-captured,user-confirmed"
    Args.source_hint = "Post detail route must render every linked article slug."
    Args.generation_rule = "Verify linked detail route before claiming post upload complete."
    Args.current_evidence = "ui-only"
    Args.decision_needed = "needs-schema-capture"
    Args.evidence_pointer = "/tmp/redacted-post-route-evidence.json"
    Args.operator_note = "Initial public detail route returned 404."
    ledger = record_source_input_gap.apply_action(Args())
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_make_resolved_gap_filters_requirement_gap() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger_path = root / "source-input-gaps.json"
        resolved_path = root / "resolved-gaps.json"
        req_path = root / "requirements.json"
        write_gap_ledger(ledger_path)

        Args = type("Args", (), {})
        Args.site_key = "mysite01"
        Args.gap_ledger = str(ledger_path)
        Args.output = str(resolved_path)
        Args.json = False
        Args.resolved_gap = [
            "fieldLabel=posts.post-detail-route|proof=/tmp/redacted-post-detail-recheck.json|note=Bounded frontend recheck rendered the new detail route, so this route blocker is superseded."
        ]
        report = make_resolved_source_input_gaps.build_report(Args())
        assert report["kind"] == "allincms_resolved_source_input_gaps"
        assert report["summary"]["resolvedFields"] == ["posts.post-detail-route"]
        resolved_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        ReqArgs = type("ReqArgs", (), {})
        ReqArgs.site_key = "mysite01"
        ReqArgs.content_types = "posts"
        ReqArgs.source_types = "pdf_catalog,plain_brief"
        ReqArgs.manifest = []
        ReqArgs.save_capture_evidence = []
        ReqArgs.media_evidence = None
        ReqArgs.readiness_evidence = None
        ReqArgs.gap_ledger = [str(ledger_path)]
        ReqArgs.resolved_gap_evidence = [str(resolved_path)]
        ReqArgs.output = str(req_path)
        ReqArgs.json = False
        requirements = build_requirements_report(ReqArgs)

    assert requirements["operationGaps"]["entryCount"] == 0
    assert requirements["operationGaps"]["resolvedEntryCount"] == 1
    assert requirements["operationGaps"]["resolvedFields"] == ["posts.post-detail-route"]
    assert "posts.post-detail-route" not in requirements["operationGaps"]["blockedFields"]


def test_make_resolved_gap_rejects_unknown_gap_label() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "source-input-gaps.json"
        write_gap_ledger(ledger_path)

        Args = type("Args", (), {})
        Args.site_key = "mysite01"
        Args.gap_ledger = str(ledger_path)
        Args.resolved_gap = [
            "fieldLabel=posts.post-body|proof=/tmp/redacted-post-body.json|note=This field is not in the supplied ledger."
        ]

        try:
            make_resolved_source_input_gaps.build_report(Args())
        except SystemExit as exc:
            assert "not present in gap ledger" in str(exc)
        else:
            raise AssertionError("expected unknown fieldLabel to be rejected")


def test_make_resolved_gap_rejects_sensitive_proof_path() -> None:
    Args = type("Args", (), {})
    Args.site_key = "mysite01"
    Args.gap_ledger = ""
    Args.resolved_gap = [
        "fieldLabel=posts.post-detail-route|proof=/tmp/authorization-post-route.json|note=Later public proof superseded this route issue."
    ]

    try:
        make_resolved_source_input_gaps.build_report(Args())
    except SystemExit as exc:
        assert "sensitive" in str(exc)
    else:
        raise AssertionError("expected sensitive proof path to be rejected")


def test_requirements_rejects_sensitive_handwritten_resolved_gap() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        resolved_path = Path(tmp) / "resolved-gaps.json"
        resolved_path.write_text(
            json.dumps(
                {
                    "kind": "allincms_resolved_source_input_gaps",
                    "siteKey": "mysite01",
                    "resolvedGaps": [
                        {
                            "fieldLabel": "posts.post-detail-route",
                            "proof": "/tmp/authorization-post-route.json",
                            "note": "Later public proof superseded this route issue.",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        ReqArgs = type("ReqArgs", (), {})
        ReqArgs.site_key = "mysite01"
        ReqArgs.content_types = "posts"
        ReqArgs.source_types = "pdf_catalog,plain_brief"
        ReqArgs.manifest = []
        ReqArgs.save_capture_evidence = []
        ReqArgs.media_evidence = None
        ReqArgs.readiness_evidence = None
        ReqArgs.gap_ledger = []
        ReqArgs.resolved_gap_evidence = [str(resolved_path)]

        try:
            build_requirements_report(ReqArgs)
        except SystemExit as exc:
            assert "sensitive" in str(exc)
        else:
            raise AssertionError("expected handwritten sensitive resolved evidence to be rejected")


def main() -> None:
    test_make_resolved_gap_filters_requirement_gap()
    test_make_resolved_gap_rejects_unknown_gap_label()
    test_make_resolved_gap_rejects_sensitive_proof_path()
    test_requirements_rejects_sensitive_handwritten_resolved_gap()
    print("resolved source-input gap tests passed.")


if __name__ == "__main__":
    main()
