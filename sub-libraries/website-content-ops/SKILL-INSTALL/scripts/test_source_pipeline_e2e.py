#!/usr/bin/env python3
"""End-to-end regression for the local source-file rehearsal pipeline.

Runs the real `run_source_file_rehearsal.py` spine on a synthetic catalog through both
stages (source-prepare -> AI-content-pass patch -> confirmed execution) and asserts the
pipeline reaches the browser boundary WITHOUT authorizing any remote mutation, that the
review/publication gates pass, and that a placeholder body is still blocked. This locks in
the manually-verified 2026-07-04 end-to-end run so a future change to the pipeline that
breaks the source->confirmation flow, or that leaks mutation authorization, fails here.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REHEARSAL = SCRIPTS / "run_source_file_rehearsal.py"

CATALOG = """# Acme RF Connectors — Product Catalog

Acme RF makes precision coaxial connectors and adapters for test and measurement labs.

## SMA Precision Connector (ACME-SMA-01)
- Frequency: DC to 26.5 GHz
- Impedance: 50 Ohm
Cost-effective everyday SMA connector for repeatable microwave measurement up to 26.5 GHz.

## 2.92mm Precision Adapter (ACME-292-01)
- Frequency: DC to 40 GHz
- Impedance: 50 Ohm
Precision 2.92mm microwave adapter for measurement into the tens of GHz.
"""

BASE_ARGS = [
    "--site-name", "Acme RF Connectors",
    "--site-description", "Precision coaxial connectors and adapters for RF and microwave test and measurement labs.",
    "--language", "en", "--industry", "RF test and measurement", "--json",
]


def _run(run_dir: Path, catalog: Path, *extra: str) -> dict:
    cmd = [sys.executable, str(REHEARSAL), str(catalog), "--output-dir", str(run_dir), *BASE_ARGS, *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPTS))
    assert proc.stdout.strip(), f"rehearsal produced no JSON: {proc.stderr[-500:]}"
    return json.loads(proc.stdout)


def _real_products() -> list[dict]:
    def para(t: str) -> dict:
        return {"type": "paragraph", "text": t}

    return [
        {
            "name": "ACME-SMA-01 Precision SMA Connector",
            "slug": "acme-sma-01-precision-sma-connector",
            "description": "Cost-effective precision SMA connector for repeatable RF and microwave measurement from DC to 26.5 GHz on a 50-ohm platform.",
            "content": [
                para("The ACME-SMA-01 is a precision SMA connector for RF and microwave test benches that need repeatable, low-uncertainty measurement from DC to 26.5 GHz. It targets VNA calibration, bench characterisation and production test."),
                para("Each unit pairs a stainless-steel body with a gold-plated centre contact on a controlled 50-ohm interface, so return loss and insertion loss stay predictable across the band and through repeated mating cycles."),
                para("Typical applications include VNA calibration, bench and R&D test, and OEM port test. Order by interface and quantity; pair with the ACME-292-01 adapter to reach higher microwave bands."),
            ],
            "sourceRefs": ["src-001"],
            "specs": [{"key": "Frequency", "value": "DC to 26.5 GHz"}, {"key": "Impedance", "value": "50 Ohm"}],
            "categories": ["Coaxial Connectors"],
        },
        {
            "name": "ACME-292-01 Precision 2.92mm Adapter",
            "slug": "acme-292-01-precision-2-92mm-adapter",
            "description": "Precision 2.92mm microwave adapter for measurement into the tens of GHz, in male-male and male-female configurations with low VSWR.",
            "content": [
                para("The ACME-292-01 is a precision 2.92mm microwave adapter for engineers extending a test setup into the tens of gigahertz on a 50-ohm platform, up to 40 GHz."),
                para("Machined from passivated stainless steel, the adapter holds low VSWR and stable return loss across its band and inter-operates cleanly with common 2.92mm and SMA-class hardware."),
                para("Use it to protect instrument ports, adapt between microwave standards, or complete a calibrated path alongside the ACME-SMA-01 connector."),
            ],
            "sourceRefs": ["src-001"],
            "specs": [{"key": "Frequency", "value": "DC to 40 GHz"}, {"key": "Impedance", "value": "50 Ohm"}],
            "categories": ["Precision Adapters"],
        },
    ]


def _author_refined(bound_path: Path) -> None:
    """Do the AI content pass: replace auto-draft placeholders with real products."""
    wiki = json.loads(bound_path.read_text(encoding="utf-8"))
    wiki["products"] = _real_products()
    wiki["taxonomyPlan"] = {
        "status": "source_taxonomy_pending_schema_capture",
        "userConfirmationRequired": True,
        "categories": [{"name": "Coaxial Connectors"}, {"name": "Precision Adapters"}],
    }
    # Scrub the auto-draft placeholder name from any remaining field (e.g. openQuestions).
    oq = wiki.get("openQuestions")
    if isinstance(oq, list):
        wiki["openQuestions"] = [q for q in oq if "Draft Product" not in json.dumps(q, ensure_ascii=False)]
    dumped = json.dumps(wiki, ensure_ascii=False)
    assert "Draft Product" not in dumped, "authored wiki must not keep placeholder product"
    bound_path.write_text(json.dumps(wiki, ensure_ascii=False, indent=1), encoding="utf-8")


def test_pipeline_reaches_browser_boundary_without_mutation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        catalog = tmp_path / "catalog.md"
        catalog.write_text(CATALOG, encoding="utf-8")
        run_dir = tmp_path / "run"

        # Stage 1: prepare + auto-draft so a full refined-wiki exists at the bound path.
        first = _run(run_dir, catalog, "--auto-draft-refined-source-wiki")
        assert first["sourceFileRehearsalValidation"]["ok"] is True, first["sourceFileRehearsalValidation"]
        # Auto-draft alone is NOT review-ready (placeholder product) -> gate correctly blocks.
        assert first["refinedSource"]["reviewReady"] is False, "auto-draft with a placeholder must not be review-ready"

        brief = json.loads((run_dir / "01-source-prepare" / "source-wiki-refinement-brief.json").read_text(encoding="utf-8"))
        bound = Path(brief["outputRefinedSourceWiki"])
        assert bound.exists(), f"bound refined wiki should exist at {bound}"

        # AI content pass, then Stage 2: refined wiki + user confirmation.
        _author_refined(bound)
        second = _run(
            run_dir, catalog,
            "--refined-source-wiki", str(bound),
            "--user-confirmation-text", "确认建站:2 产品 2 分类,new_site,接受当前范围。",
        )

        assert second["refinedSource"]["reviewReady"] is True, second.get("nextAction")
        ce = second["confirmedExecution"]
        assert ce["prepared"] is True, "confirmed execution must be prepared after confirmation"
        assert ce["targetMode"] == "new_site"
        assert ce["readyForBrowserStage"] == "needs_create_site_preflight", ce
        assert second["confirmationBrief"]["isRemoteMutationAuthorization"] is False, "pipeline must not authorize a remote mutation"
        assert second["sourceFileRehearsalValidation"]["ok"] is True
        assert second["sourceFileRehearsalValidation"]["issues"] == []


if __name__ == "__main__":
    test_pipeline_reaches_browser_boundary_without_mutation()
    print("source pipeline end-to-end regression passed")
