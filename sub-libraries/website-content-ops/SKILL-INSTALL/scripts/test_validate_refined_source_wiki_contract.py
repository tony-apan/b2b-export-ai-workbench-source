#!/usr/bin/env python3
"""Regression tests for refined source wiki contract validation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from make_source_wiki_refinement_brief import build as build_refinement_brief
from test_apply_refined_source_wiki import inventory, refined_wiki, write_json
from validate_refined_source_wiki_contract import build_report, validate_contract


def refinement_plan() -> dict:
    return {
        "kind": "allincms_source_wiki_refinement_plan",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "reviewReadyBlocked": True,
        "classificationCounts": {"needs_source_backed_rewrite": 1},
        "items": [
            {
                "sourceWikiTarget": "products[0].name",
                "classification": "needs_source_backed_rewrite",
                "issue": "products[0].name contains placeholder copy",
                "suggestedAction": "Replace placeholder product with source-backed publishable product copy.",
            }
        ],
    }


def make_brief(root: Path, output_refined: Path) -> str:
    original_wiki = refined_wiki()
    original_wiki["products"][0]["name"] = "Draft Product"
    source_wiki_path = write_json(root / "source-wiki.json", original_wiki)
    plan_path = write_json(root / "source-wiki-refinement-plan.json", refinement_plan())
    return write_json(
        root / "source-wiki-refinement-brief.json",
        build_refinement_brief(
            argparse.Namespace(
                source_wiki=source_wiki_path,
                refinement_plan=plan_path,
                output=str(root / "source-wiki-refinement-brief.json"),
                output_refined_source_wiki=str(output_refined),
                site_markdown="",
                pages_markdown="",
                products_markdown="",
                posts_markdown="",
                max_markdown_chars=2000,
                json=False,
            )
        ),
    )


def test_contract_accepts_refined_wiki_matching_brief() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, refined_path)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        refined = refined_wiki()
        issues = validate_contract(
            refined_wiki=refined,
            brief=json.loads(Path(brief_path).read_text(encoding="utf-8")),
            refined_wiki_path=str(refined_path),
            inventory=json.loads(Path(inventory_path).read_text(encoding="utf-8")),
        )
        assert issues == []
        write_json(refined_path, refined)
        report = build_report(
            argparse.Namespace(
                refined_source_wiki=str(refined_path),
                refinement_brief=brief_path,
                inventory=inventory_path,
                output="",
                json=False,
            )
        )
        assert report["ok"] is True
        assert report["sourceFingerprintsHydrated"] is True


def test_contract_rejects_wrong_path_placeholder_and_authorization_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refined_path = root / "source-wiki.refined.json"
        brief = json.loads(Path(make_brief(root, refined_path)).read_text(encoding="utf-8"))
        inventory_data = inventory(root)
        refined = refined_wiki()
        refined["products"][0]["name"] = "Draft Product"
        refined["remoteMutationsPerformed"] = True
        issues = validate_contract(
            refined_wiki=refined,
            brief=brief,
            refined_wiki_path=str(root / "other.json"),
            inventory=inventory_data,
        )
        assert "refined source wiki path must match brief.outputRefinedSourceWiki" in issues
        assert "refined wiki remoteMutationsPerformed must be false" in issues
        assert any("placeholder/review term" in issue for issue in issues)


def test_cli_json_stdout_is_parseable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refined_path = root / "source-wiki.refined.json"
        brief_path = make_brief(root, refined_path)
        inventory_path = write_json(root / "source-index.json", inventory(root))
        write_json(refined_path, refined_wiki())
        output = root / "contract-validation.json"
        script = Path(__file__).resolve().parent / "validate_refined_source_wiki_contract.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--refined-source-wiki",
                str(refined_path),
                "--refinement-brief",
                str(brief_path),
                "--inventory",
                str(inventory_path),
                "--output",
                str(output),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        parsed = json.loads(result.stdout)
        assert parsed["kind"] == "allincms_refined_source_wiki_contract_validation"
        assert parsed["ok"] is True
        assert parsed["sourceFingerprintsHydrated"] is True
        assert output.exists()
        assert "validation passed" not in result.stdout.lower()


if __name__ == "__main__":
    test_contract_accepts_refined_wiki_matching_brief()
    test_contract_rejects_wrong_path_placeholder_and_authorization_drift()
    test_cli_json_stdout_is_parseable()
    print("refined source wiki contract validation regression tests passed.")
