#!/usr/bin/env python3
"""Prepare a local evidence bundle for one create-site browser run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import sys
from typing import Any

from build_create_site_runbook import validate_runbook
from make_created_site_evidence_brief import REQUIRED_MODULES
from validate_source_package_confirmation import validate_content_goal_overages, validate_content_goal_overages_for_warnings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("output directory must be outside the skill package")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{label} JSON not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def validate_brief(brief: dict[str, Any], runbook: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if brief.get("kind") != "allincms_created_site_evidence_brief":
        issues.append("brief kind must be allincms_created_site_evidence_brief")
    if brief.get("isUserAuthorization") is not False:
        issues.append("brief must not be user authorization")
    if brief.get("remoteMutationsPerformed") is not False:
        issues.append("brief must be local-only/no remote mutation")
    handoff = str(brief.get("createSiteHandoff", ""))
    if not handoff or handoff != str(runbook.get("sourceCreateSiteHandoff", "")):
        issues.append("brief createSiteHandoff must match runbook sourceCreateSiteHandoff")
    if str(brief.get("preflight", "")) != str(runbook.get("preflight", "")):
        issues.append("brief preflight must match runbook preflight")
    if not isinstance(brief.get("createdSiteEvidenceOutput"), str) or not brief["createdSiteEvidenceOutput"]:
        issues.append("brief.createdSiteEvidenceOutput is required")
    return issues


SOURCE_CONTEXT_KEYS = (
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "contentGoalOverages",
    "wikiReview",
    "confirmationDecisionMatrix",
)

REQUIRED_CONTENT_COUNT_KEYS = ("pages", "products", "posts")
EXTENDED_CONTENT_COUNT_KEYS = ("forms", "media", "navigationItems", "siteInfoFields")


def source_context(runbook: dict[str, Any]) -> dict[str, Any]:
    return {key: runbook.get(key) for key in SOURCE_CONTEXT_KEYS}


def source_context_issues(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true")
    quality = data.get("contentQualityReview")
    if not isinstance(quality, dict) or "warnings" not in quality:
        issues.append("contentQualityReview with warnings is required")
    overages = data.get("contentGoalOverages")
    validate_content_goal_overages(overages, issues)
    validate_content_goal_overages_for_warnings(overages, quality, issues)
    wiki = data.get("wikiReview")
    if not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex"):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required")
    matrix = data.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix is required")
    counts = data.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts is required")
    else:
        for key in REQUIRED_CONTENT_COUNT_KEYS:
            value = counts.get(key)
            if not isinstance(value, int) or value < 0:
                issues.append(f"contentCounts.{key} must be a non-negative integer")
        for key in EXTENDED_CONTENT_COUNT_KEYS:
            if key in counts:
                value = counts.get(key)
                if not isinstance(value, int) or value < 0:
                    issues.append(f"contentCounts.{key} must be a non-negative integer")
    return issues


def evidence_template(runbook: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    site_name = str(runbook.get("siteProposal", {}).get("siteName", ""))
    site_description = str(runbook.get("siteProposal", {}).get("siteDescription", ""))
    template = {
        "kind": "allincms_created_site_browser_evidence_fill_template",
        "sourceRunbook": "",
        "sourceCreatedSiteEvidenceBrief": "",
        "createSiteHandoff": runbook.get("sourceCreateSiteHandoff", ""),
        "authorizationRecord": runbook.get("authorizationRecord", ""),
        "preMutationGateStatus": "passed|required_before_submit",
        "gateReadyForBrowserSubmit": False,
        "preflight": runbook.get("preflight", ""),
        "action": "create_site",
        "target": "https://workspace.laicms.com/sites",
        "submittedSiteName": site_name,
        "submittedSiteDescription": site_description,
        "submittedValues": {
            "name": site_name,
            "description": site_description,
        },
        "createdSiteKey": "<created-site-key>",
        "contentTypeForInitialInspection": "products",
        "listColumns": ["<products list column>", "<another column>"],
        "editFields": ["<products edit field>", "<another field>"],
        "siteCardEvidence": "site card route/href contains <created-site-key>",
        "backendEvidence": "backend URL https://workspace.laicms.com/<created-site-key>/dashboard loaded",
        "frontendEvidence": "frontend URL https://<created-site-key>.web.allincms.com loaded",
        "setupPageEvidence": {
            "siteInfo": "site-info controls visible",
            "domains": "domains controls visible",
            "media": "media controls visible",
            "themes": "themes controls visible",
            "routes": "routes controls visible",
            "forms": "forms controls visible",
            "tracking": "tracking controls visible",
        },
        "moduleRoutes": [f"/<created-site-key>/{module}" for module in REQUIRED_MODULES],
        "submittedFields": ["name", "description"],
        "authorizationSource": "<current user create_site authorization text>",
        "forbiddenNeighborActionsVerified": False,
        "stopConditionMet": False,
        "createdSiteEvidenceOutput": brief.get("createdSiteEvidenceOutput", ""),
    }
    template.update(source_context(runbook))
    return template


def make_created_site_command(template_path: Path, output_path: str) -> str:
    return " ".join(
        shlex.quote(part)
        for part in [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/make_created_site_evidence.py",
            "--preflight",
            "<copy from template.preflight>",
            "--created-site-key",
            "<copy from template.createdSiteKey>",
            "--content-type",
            "<copy from template.contentTypeForInitialInspection>",
            "--list-columns",
            "<comma-separated template.listColumns>",
            "--edit-fields",
            "<comma-separated template.editFields>",
            "--site-card-evidence",
            "<copy from template.siteCardEvidence>",
            "--backend-evidence",
            "<copy from template.backendEvidence>",
            "--frontend-evidence",
            "<copy from template.frontendEvidence>",
            "--site-info-evidence",
            "<copy from template.setupPageEvidence.siteInfo>",
            "--domains-evidence",
            "<copy from template.setupPageEvidence.domains>",
            "--media-evidence",
            "<copy from template.setupPageEvidence.media>",
            "--themes-evidence",
            "<copy from template.setupPageEvidence.themes>",
            "--routes-evidence",
            "<copy from template.setupPageEvidence.routes>",
            "--forms-evidence",
            "<copy from template.setupPageEvidence.forms>",
            "--tracking-evidence",
            "<copy from template.setupPageEvidence.tracking>",
            "--module-routes",
            "<comma-separated template.moduleRoutes with real site key>",
            "--submitted-fields",
            "name,description",
            "--submitted-values",
            "<JSON copy from template.submittedValues>",
            "--authorization-source",
            "<copy from template.authorizationSource>",
            "--output",
            output_path,
        ]
    )


def prepare_created_site_schema_command(brief: dict[str, Any], output_dir: Path) -> str:
    created_site_output = str(brief.get("createdSiteEvidenceOutput", ""))
    return " ".join(
        shlex.quote(part)
        for part in [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/prepare_created_site_schema_capture.py",
            "--artifact-readiness",
            "<artifact-readiness.json>",
            "--created-site-evidence",
            created_site_output or "<created-site-evidence.json>",
            "--package",
            "<source-site-package.json>",
            "--confirmation",
            "<confirmation-record.json>",
            "--execution-plan",
            "<confirmed-site-execution-plan.json>",
            "--output-dir",
            str(output_dir / "created-site-schema-capture"),
        ]
    )


def apply_bundle_command(bundle_path: Path, filled_template_path: Path, output_dir: Path, created_site_output: str) -> str:
    return " ".join(
        shlex.quote(part)
        for part in [
            "python3",
            "skills/allincms-bulk-content-upload/scripts/apply_created_site_evidence_bundle.py",
            "--bundle",
            str(bundle_path),
            "--filled-template",
            str(filled_template_path),
            "--output-dir",
            str(output_dir / "applied"),
            "--created-site-evidence-output",
            created_site_output,
        ]
    )


def build_notes(runbook: dict[str, Any], brief: dict[str, Any]) -> str:
    lines = [
        "# Created Site Evidence Bundle",
        "",
        "This bundle is local scaffolding only. It does not authorize browser actions.",
        "",
        "Before filling `created-site-evidence.filled-template.json`:",
        "- create the action-time create_site authorization record",
        "- run the create_site pre-mutation gate",
        "- re-open `/sites` and confirm the create dialog still has the expected fields",
        "- submit the create-site form exactly once",
        "- stop before products/posts/media probes, content save, publish, theme edit, route bind, domains, tracking, or cleanup",
        "",
        "After the browser run, fill only redacted, neutral evidence:",
        "- new created site key",
        "- backend dashboard URL and public frontend URL proof",
        "- module route list for dashboard/products/posts/media/themes/routes/forms/site-info/tracking/domains",
        "- setup-page controls proof for site-info/domains/media/themes/routes/forms/tracking",
        "- one read-only content list/edit inspection, preferably products",
        "- proof forbidden neighboring actions did not happen",
        "",
        "Preferred apply path:",
        "- fill `created-site-evidence.filled-template.json`",
        "- run `apply-created-site-evidence-bundle-command.txt`",
        "- add `--prepare-created-site-schema-capture` plus confirmed package/artifact paths when you want the helper to immediately prepare the next local stage",
        "",
        f"Runbook: `{runbook.get('sourceCreateSiteHandoff', '')}`",
        f"Created-site evidence target: `{brief.get('createdSiteEvidenceOutput', '')}`",
    ]
    return "\n".join(lines) + "\n"


def build_bundle(
    *,
    runbook: dict[str, Any],
    runbook_path: str,
    brief: dict[str, Any],
    brief_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    runbook_issues = validate_runbook(runbook)
    if runbook_issues:
        raise ValueError("create-site runbook validation failed:\n- " + "\n- ".join(runbook_issues))
    brief_issues = validate_brief(brief, runbook)
    if brief_issues:
        raise ValueError("created-site evidence brief validation failed:\n- " + "\n- ".join(brief_issues))
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "created-site-evidence.template.json"
    filled_template_path = output_dir / "created-site-evidence.filled-template.json"
    notes_path = output_dir / "notes.md"
    bundle_path = output_dir / "evidence-bundle.json"
    apply_command_path = output_dir / "apply-created-site-evidence-bundle-command.txt"
    make_command_path = output_dir / "make-created-site-evidence-command.txt"
    next_command_path = output_dir / "prepare-created-site-schema-capture-command.txt"
    template = evidence_template(runbook, brief)
    template["sourceRunbook"] = runbook_path
    template["sourceCreatedSiteEvidenceBrief"] = brief_path
    write_json(template_path, template)
    write_json(filled_template_path, template)
    notes_path.write_text(build_notes(runbook, brief), encoding="utf-8")
    created_site_output = str(brief["createdSiteEvidenceOutput"])
    apply_command_path.write_text(
        apply_bundle_command(bundle_path, filled_template_path, output_dir, created_site_output) + "\n",
        encoding="utf-8",
    )
    make_command_path.write_text(make_created_site_command(filled_template_path, created_site_output) + "\n", encoding="utf-8")
    next_command_path.write_text(prepare_created_site_schema_command(brief, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_created_site_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "runbook": runbook_path,
        "createdSiteEvidenceBrief": brief_path,
        "createSiteHandoff": runbook.get("sourceCreateSiteHandoff", ""),
        "preflight": runbook.get("preflight", ""),
        "authorizationRecord": runbook.get("authorizationRecord", ""),
        "createdSiteEvidenceOutput": created_site_output,
        "submittedValues": template["submittedValues"],
        "evidenceTemplate": str(template_path),
        "filledEvidenceTemplate": str(filled_template_path),
        "notes": str(notes_path),
        "applyCreatedSiteEvidenceBundleCommand": str(apply_command_path),
        "makeCreatedSiteEvidenceCommand": str(make_command_path),
        "prepareCreatedSiteSchemaCaptureCommand": str(next_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "action-time create_site authorization",
            "pre-mutation gate pass",
            "create-site dialog fields rechecked",
            "browser submit exactly once",
            "forbidden neighboring actions verified absent",
        ],
        "nextAction": "fill redacted evidence after the gated browser run, run apply_created_site_evidence_bundle.py, then run or auto-run prepare_created_site_schema_capture.py",
    }
    bundle.update(source_context(runbook))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_created_site_evidence_bundle":
        issues.append("kind must be allincms_created_site_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in (
        "runbook",
        "createdSiteEvidenceBrief",
        "createSiteHandoff",
        "preflight",
        "authorizationRecord",
        "createdSiteEvidenceOutput",
        "evidenceTemplate",
        "filledEvidenceTemplate",
        "notes",
        "applyCreatedSiteEvidenceBundleCommand",
        "makeCreatedSiteEvidenceCommand",
        "prepareCreatedSiteSchemaCaptureCommand",
    ):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include pre-mutation gate pass")
    submitted_values = bundle.get("submittedValues")
    if not isinstance(submitted_values, dict):
        issues.append("submittedValues must be an object")
    else:
        for key in ("name", "description"):
            value = submitted_values.get(key)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"submittedValues.{key} must be a non-empty string")
    issues.extend(source_context_issues(bundle))
    return issues


def build_validation_report(bundle: dict[str, Any], bundle_path: str = "") -> dict[str, Any]:
    issues = validate_bundle(bundle)
    return {
        "kind": "allincms_created_site_evidence_bundle_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "bundle": bundle_path,
        "preparedOnly": bundle.get("preparedOnly"),
        "browserStepsExecutable": bundle.get("browserStepsExecutable"),
        "remoteMutationsPerformed": bundle.get("remoteMutationsPerformed"),
        "isUserAuthorization": bundle.get("isUserAuthorization"),
        "createdSiteEvidenceOutput": bundle.get("createdSiteEvidenceOutput"),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local created-site evidence bundle.")
    parser.add_argument("--runbook", required=True)
    parser.add_argument("--created-site-evidence-brief", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            runbook=load_json(Path(args.runbook), "create-site runbook"),
            runbook_path=args.runbook,
            brief=load_json(Path(args.created_site_evidence_brief), "created-site evidence brief"),
            brief_path=args.created_site_evidence_brief,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("created-site evidence bundle validation failed:\n- " + "\n- ".join(issues))
        manifest_path = output_dir / "evidence-bundle.json"
        write_json(manifest_path, bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote created-site evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
