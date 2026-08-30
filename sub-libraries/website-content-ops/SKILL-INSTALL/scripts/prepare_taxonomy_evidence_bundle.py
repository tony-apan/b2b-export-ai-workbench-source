#!/usr/bin/env python3
"""Prepare a local evidence bundle for taxonomy create/map browser execution."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


SOURCE_CONTEXT_KEYS = (
    "sourcePackageSha256",
    "sourceReviewPacketSha256",
    "createdSiteSubmittedValues",
    "contentGoalCoverage",
    "contentCounts",
    "contentQualityReview",
    "wikiReview",
    "confirmationDecisionMatrix",
)

REQUIRED_CONTENT_COUNT_KEYS = ("pages", "products", "posts")
EXTENDED_CONTENT_COUNT_KEYS = ("forms", "media", "navigationItems", "siteInfoFields")


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


def normalized_actions(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    actions = handoff.get("actions")
    if not isinstance(actions, list):
        raise ValueError("handoff.actions must be an array")
    out: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        term = action.get("term")
        if not isinstance(term, dict):
            continue
        target_identifier = str(action.get("targetIdentifier") or "").strip()
        content_type = str(action.get("contentType") or "").strip()
        term_kind = str(action.get("termKind") or "").strip()
        slug = str(term.get("slug") or "").strip()
        label = str(term.get("label") or "").strip()
        if not target_identifier or not content_type or not term_kind or not slug or not label:
            raise ValueError(f"handoff.actions[{index}] is missing targetIdentifier/contentType/termKind/term fields")
        out.append(
            {
                "targetIdentifier": target_identifier,
                "contentType": content_type,
                "termKind": term_kind,
                "slug": slug,
                "label": label,
                "backendUrl": str(action.get("target") or "").strip(),
                "authorizationOutput": str(action.get("authorizationOutput") or "").strip(),
                "preMutationGateCommand": str(action.get("preMutationGateCommand") or "").strip(),
            }
        )
    return out


def source_context(handoff: dict[str, Any]) -> dict[str, Any]:
    return {key: handoff.get(key) for key in SOURCE_CONTEXT_KEYS if key in handoff}


def source_context_issues(data: dict[str, Any]) -> list[str]:
    if not any(key in data for key in SOURCE_CONTEXT_KEYS):
        return []
    issues: list[str] = []
    if any(key in data for key in ("sourcePackageSha256", "sourceReviewPacketSha256")):
        for key in ("sourcePackageSha256", "sourceReviewPacketSha256"):
            value = data.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                issues.append(f"{key} must be a lowercase 64-character sha256 when source identity is present")
    submitted = data.get("createdSiteSubmittedValues")
    if submitted is not None:
        if not isinstance(submitted, dict):
            issues.append("createdSiteSubmittedValues must be an object when present")
        else:
            for key in ("name", "description"):
                value = submitted.get(key)
                if not isinstance(value, str) or not value.strip():
                    issues.append(f"createdSiteSubmittedValues.{key} must be a non-empty string when present")
    coverage = data.get("contentGoalCoverage")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True:
        issues.append("contentGoalCoverage.complete must be true when source context is present")
    quality = data.get("contentQualityReview")
    if not isinstance(quality, dict) or "warnings" not in quality:
        issues.append("contentQualityReview with warnings is required when source context is present")
    wiki = data.get("wikiReview")
    if not isinstance(wiki, dict) or not wiki.get("sourceWikiMarkdownIndex"):
        issues.append("wikiReview.sourceWikiMarkdownIndex is required when source context is present")
    matrix = data.get("confirmationDecisionMatrix")
    if not isinstance(matrix, list) or not matrix:
        issues.append("confirmationDecisionMatrix is required when source context is present")
    counts = data.get("contentCounts")
    if not isinstance(counts, dict):
        issues.append("contentCounts is required when source context is present")
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


def evidence_template(handoff: dict[str, Any], handoff_path: str) -> dict[str, Any]:
    site_key = str(handoff.get("siteKey") or "").strip()
    if not site_key:
        raise ValueError("handoff.siteKey is required")
    actions = normalized_actions(handoff)
    template = {
        "kind": "allincms_taxonomy_execution_evidence",
        "sourceHandoff": handoff_path,
        "siteKey": site_key,
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": False,
        "stopConditionMet": False,
        "blockingIssues": ["replace this placeholder with real blockers or [] after every taxonomy proof passes"],
        "taxonomyMappings": [
            {
                "targetIdentifier": action["targetIdentifier"],
                "contentType": action["contentType"],
                "termKind": action["termKind"],
                "slug": action["slug"],
                "label": action["label"],
                "status": "created|mapped_existing",
                "preMutationGate": "passed|required",
                "backendUrl": action["backendUrl"],
                "backendVerified": False,
                "mappingVerified": False,
                "requestCapture": {
                    "method": "POST",
                    "headers": ["accept", "content-type"],
                    "payloadShape": {"term": "redacted shape to fill"},
                    "responseStatus": None,
                },
                "evidence": "redacted backend row, selector option, or request proof to fill",
            }
            for action in actions
        ],
    }
    template.update(source_context(handoff))
    return template


def validation_command(filled_path: Path, handoff_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_taxonomy_execution_evidence.py "
        f"{filled_path} --handoff {handoff_path} --output {output_dir / 'taxonomy-execution-validation.json'}"
    )


def apply_command(filled_path: Path, handoff_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_taxonomy_execution.py "
        f"--taxonomy-handoff {handoff_path} "
        f"--taxonomy-evidence {filled_path} "
        "--package <source-site-package.json> "
        "--confirmation <confirmation-record.json> "
        "--execution-plan <confirmed-site-execution-plan.json> "
        "--artifact-readiness <artifact-readiness.json> "
        "--created-site-binding <created-site-artifact-binding.json> "
        "--pages-site-info-handoff <pages-site-info-browser-handoff.json> "
        "--pages-site-info-validation <pages-site-info-execution-validation.json> "
        "--schema-capture-handoff <schema-capture-handoff.json> "
        f"--output-dir {output_dir / 'taxonomy-applied'}"
    )


def build_notes(handoff: dict[str, Any]) -> str:
    actions = normalized_actions(handoff)
    return "\n".join(
        [
            "# Taxonomy Evidence Bundle",
            "",
            "This bundle is local scaffolding only. It does not authorize browser actions.",
            "",
            "Before filling `taxonomy-execution-evidence.filled.json`:",
            "- choose exactly one taxonomy action at a time from the handoff",
            "- inspect the current products/posts category or tag UI/request shape",
            "- create the action-time authorization record",
            "- run the matching pre-mutation gate",
            "- create or map the term, then stop before product/post upload",
            "- record redacted backend row or selector-option proof for that term",
            "- do not store raw cookies, authorization headers, server-action IDs, router state, account emails, or business copy",
            "",
            f"Expected taxonomy action count: {len(actions)}",
            "",
            "The filled evidence is complete only when every handoff taxonomy action has a created or mapped_existing row with backendVerified and mappingVerified true.",
        ]
    ) + "\n"


def build_bundle(*, handoff: dict[str, Any], handoff_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if handoff.get("kind") != "allincms_taxonomy_execution_handoff":
        raise ValueError("handoff kind must be allincms_taxonomy_execution_handoff")
    if handoff.get("remoteMutationsPerformed") is not False:
        raise ValueError("handoff must be local-only/no remote mutation")
    actions = normalized_actions(handoff)
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "taxonomy-execution-evidence.template.json"
    filled_path = output_dir / "taxonomy-execution-evidence.filled.json"
    notes_path = output_dir / "notes.md"
    validation_command_path = output_dir / "validation-command.txt"
    apply_command_path = output_dir / "apply-command.txt"
    template = evidence_template(handoff, handoff_path)
    write_json(template_path, template)
    write_json(filled_path, template)
    notes_path.write_text(build_notes(handoff), encoding="utf-8")
    validation_command_path.write_text(validation_command(filled_path, handoff_path, output_dir) + "\n", encoding="utf-8")
    apply_command_path.write_text(apply_command(filled_path, handoff_path, output_dir) + "\n", encoding="utf-8")
    bundle = {
        "kind": "allincms_taxonomy_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "handoff": handoff_path,
        "siteKey": handoff.get("siteKey"),
        "handoffReadyForBrowserStage": handoff.get("readyForBrowserStage", ""),
        "handoffPreflightIssues": handoff.get("preflightIssues", []),
        "actionCount": len(actions),
        "termCounts": handoff.get("termCounts", {}),
        "evidenceTemplate": str(template_path),
        "filledEvidencePath": str(filled_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "current products/posts taxonomy UI or request-shape inspection",
            "action-time authorization for each individual taxonomy action",
            "matching pre-mutation gate pass",
            "redacted backend row or selector-option proof for every term",
        ],
        "nextAction": "resolve taxonomy handoff preflight blockers before browser actions"
        if handoff.get("preflightIssues")
        else "fill redacted taxonomy evidence after browser actions, validate it, then run apply_taxonomy_execution.py",
    }
    bundle.update(source_context(handoff))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_taxonomy_evidence_bundle":
        issues.append("kind must be allincms_taxonomy_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in ("handoff", "siteKey", "evidenceTemplate", "filledEvidencePath", "notes", "validationCommand", "applyCommand"):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    if not isinstance(bundle.get("actionCount"), int):
        issues.append("actionCount must be an integer")
    preflight_issues = bundle.get("handoffPreflightIssues")
    if not isinstance(preflight_issues, list):
        issues.append("handoffPreflightIssues must be an array")
    ready_stage = bundle.get("handoffReadyForBrowserStage")
    if ready_stage and ready_stage != "ready_to_prepare_action_specific_taxonomy_authorization":
        if not preflight_issues:
            issues.append("blocked handoffReadyForBrowserStage must include handoffPreflightIssues")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "matching pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include matching pre-mutation gate pass")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local taxonomy evidence bundle.")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            handoff=load_json(Path(args.handoff), "taxonomy handoff"),
            handoff_path=args.handoff,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("taxonomy evidence bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "evidence-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote taxonomy evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
