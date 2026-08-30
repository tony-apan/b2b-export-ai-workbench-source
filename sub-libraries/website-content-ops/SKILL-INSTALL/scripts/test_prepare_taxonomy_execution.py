#!/usr/bin/env python3
"""Regression tests for taxonomy execution preparation and validation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from export_confirmed_site_artifacts import build_artifacts
from prepare_taxonomy_execution import build as build_taxonomy_handoff
from test_export_confirmed_site_artifacts import prepare_confirmed_plan
from test_validate_run_evidence import created_site_evidence
from validate_taxonomy_execution_evidence import validate_evidence


def write_json(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def prepare_handoff(root: Path) -> tuple[dict, dict]:
    package_path, confirmation_path, plan_path = prepare_confirmed_plan(root)
    readiness = build_artifacts(
        argparse.Namespace(
            package=str(package_path),
            confirmation=str(confirmation_path),
            execution_plan=str(plan_path),
            site_key="codex-test-site",
            frontend_base_url="https://codex-test-site.web.allincms.com",
            output_dir=str(root / "artifacts"),
            json=False,
        )
    )
    preflight = created_site_evidence()
    preflight["siteIdentity"]["siteKey"] = "codex-test-site"
    preflight["siteIdentity"]["frontendBaseUrl"] = "https://codex-test-site.web.allincms.com"
    preflight["siteIdentity"]["moduleRoutes"] = [
        "/codex-test-site/dashboard",
        "/codex-test-site/site-info",
        "/codex-test-site/products",
        "/codex-test-site/posts",
        "/codex-test-site/media",
        "/codex-test-site/themes",
        "/codex-test-site/routes",
        "/codex-test-site/forms",
        "/codex-test-site/domains",
        "/codex-test-site/tracking",
    ]
    preflight.setdefault("setupPages", {})
    preflight["setupPages"]["products"] = ["products list and taxonomy tabs inspected read-only"]
    preflight["setupPages"]["posts"] = ["posts list and taxonomy tabs inspected read-only"]
    preflight_path = write_json(root / "created-site-evidence.json", preflight)
    summary = build_taxonomy_handoff(
        argparse.Namespace(
            taxonomy_plan=readiness["artifacts"]["taxonomyPlan"],
            preflight=preflight_path,
            output_dir=str(root / "taxonomy"),
            json=False,
        )
    )
    handoff = json.loads(Path(summary["artifacts"]["handoff"]).read_text(encoding="utf-8"))
    return summary, handoff


def test_prepare_taxonomy_execution_outputs_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        summary, handoff = prepare_handoff(root)
        assert summary["localOnly"] is True
        assert summary["remoteMutationsPerformed"] is False
        assert summary["preparedOnly"] is True
        assert summary["readyForBrowserStage"] == "ready_to_prepare_action_specific_taxonomy_authorization"
        assert summary["actionCount"] == 4
        assert handoff["kind"] == "allincms_taxonomy_execution_handoff"
        assert handoff["browserStepsExecutable"] is False
        assert handoff["actions"][0]["browserStepsExecutable"] is False
        assert handoff["actions"][0]["requiresSchemaCapture"] is True
        assert "create_or_map_products_category" in handoff["actions"][0]["preMutationGateCommand"]
        assert "<paste current user authorization text here>" in handoff["actions"][0]["authorizationRecordCommand"]


def test_validate_taxonomy_execution_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, handoff = prepare_handoff(root)
        mappings = []
        for action in handoff["actions"]:
            term = action["term"]
            mappings.append(
                {
                    "targetIdentifier": action["targetIdentifier"],
                    "contentType": action["contentType"],
                    "termKind": action["termKind"],
                    "slug": term["slug"],
                    "label": term["label"],
                    "status": "created",
                    "preMutationGate": "passed",
                    "backendVerified": True,
                    "mappingVerified": True,
                    "backendUrl": action["target"],
                    "requestCapture": {
                        "method": "POST",
                        "responseStatus": 200,
                        "payloadShape": {"label": "string", "slug": "string"},
                    },
                }
            )
        evidence = {
            "kind": "allincms_taxonomy_execution_evidence",
            "siteKey": "codex-test-site",
            "remoteMutationsPerformed": True,
            "preMutationGatesPassed": True,
            "taxonomyMappings": mappings,
            "blockingIssues": [],
            "stopConditionMet": True,
        }
        assert not validate_evidence(evidence, handoff)
        bad = dict(evidence)
        bad["taxonomyMappings"] = mappings[:-1]
        issues = validate_evidence(bad, handoff)
        assert any("missing handoff terms" in issue for issue in issues), issues


def test_validate_taxonomy_execution_evidence_rejects_blocked_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, handoff = prepare_handoff(root)
        handoff["readyForBrowserStage"] = "blocked_taxonomy_preflight"
        handoff["preflightIssues"] = ["preflight.setupPages.products"]
        mappings = []
        for action in handoff["actions"]:
            term = action["term"]
            mappings.append(
                {
                    "targetIdentifier": action["targetIdentifier"],
                    "contentType": action["contentType"],
                    "termKind": action["termKind"],
                    "slug": term["slug"],
                    "label": term["label"],
                    "status": "created",
                    "preMutationGate": "passed",
                    "backendVerified": True,
                    "mappingVerified": True,
                    "backendUrl": action["target"],
                    "requestCapture": {
                        "method": "POST",
                        "responseStatus": 200,
                        "payloadShape": {"label": "string", "slug": "string"},
                    },
                }
            )
        evidence = {
            "kind": "allincms_taxonomy_execution_evidence",
            "siteKey": "codex-test-site",
            "remoteMutationsPerformed": True,
            "preMutationGatesPassed": True,
            "taxonomyMappings": mappings,
            "blockingIssues": [],
            "stopConditionMet": True,
        }
        issues = validate_evidence(evidence, handoff)
        assert any("handoff.readyForBrowserStage" in issue for issue in issues), issues
        assert any("handoff.preflightIssues must be empty" in issue for issue in issues), issues


if __name__ == "__main__":
    test_prepare_taxonomy_execution_outputs_handoff()
    test_validate_taxonomy_execution_evidence()
    test_validate_taxonomy_execution_evidence_rejects_blocked_handoff()
    print("taxonomy execution preparation regression tests passed.")
