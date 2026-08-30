#!/usr/bin/env python3
"""Prepare a local evidence bundle for pages/site-info browser execution."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


REQUIRED_PAGE_ACTIONS = (
    "create_theme_page",
    "save_design",
    "publish_design",
    "enable_theme_page",
    "bind_route",
)
ACTION_TO_TEMPLATE_FIELD = {
    "create_theme_page": "createThemePageVerified",
    "save_design": "designSaved",
    "publish_design": "designPublished",
    "enable_theme_page": "pageEnabled",
    "bind_route": "routeBound",
}

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


def expected_frontend_url(frontend_base: str, path: str) -> str:
    return frontend_base.rstrip("/") if path == "/" else frontend_base.rstrip("/") + path


def normalize_handoff_pages(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    pages = handoff.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("handoff.pages must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(pages):
        if not isinstance(item, dict):
            continue
        page = item.get("page")
        if not isinstance(page, dict):
            continue
        path = str(page.get("path", "")).strip()
        title = str(page.get("title", "") or f"Page {index + 1}").strip()
        if not path.startswith("/"):
            raise ValueError(f"handoff page path must be absolute: {path}")
        actions = item.get("actions")
        action_names: list[str] = []
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, dict) and isinstance(action.get("action"), str):
                    action_names.append(action["action"])
        if not action_names:
            raise ValueError(f"handoff page has no actions: {path}")
        normalized.append({"title": title, "path": path, "actions": action_names})
    if not normalized:
        raise ValueError("handoff.pages contains no usable page entries")
    return normalized


def action_template(actions: list[str]) -> dict[str, Any]:
    return {
        action: {"preMutationGate": "passed|required", "verified": False, "evidence": "redacted proof to fill"}
        for action in actions
    }


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
    site_key = str(handoff.get("siteKey", "")).strip()
    frontend_base = str(handoff.get("frontendBaseUrl", "")).strip().rstrip("/")
    if not site_key:
        raise ValueError("handoff.siteKey is required")
    if not frontend_base.startswith("https://"):
        raise ValueError("handoff.frontendBaseUrl must be an https URL")
    pages = normalize_handoff_pages(handoff)
    template = {
        "kind": "allincms_pages_site_info_execution_evidence",
        "sourceHandoff": handoff_path,
        "siteKey": site_key,
        "remoteMutationsPerformed": True,
        "preMutationGatesPassed": False,
        "stopConditionMet": False,
        "blockingIssues": ["replace this placeholder with real blockers or [] after every proof passes"],
        "siteInfo": {
            "status": "verified|required",
            "target": f"https://workspace.laicms.com/{site_key}/site-info",
            "saveStatus": "ok|required",
            "backendVerified": False,
            "persistedVerified": False,
            "requestCapture": {
                "method": "POST",
                "headers": ["accept", "content-type"],
                "payloadShape": {"name": "string", "description": "string"},
                "responseStatus": None,
            },
        },
        "pages": [
            {
                "path": page["path"],
                "routePath": page["path"],
                "backendUrl": f"https://workspace.laicms.com/{site_key}/themes/<themeId>/<pageId>/design",
                "frontendUrl": expected_frontend_url(frontend_base, page["path"]),
                "createThemePageVerified": False,
                "designSaved": False,
                "designPublished": False,
                "pageEnabled": False,
                "routeBound": False,
                "frontendVerified": False,
                "homepageVerified": False if page["path"] == "/" else "not_required",
                "renderAudit": {
                    "sourceContentVerified": False,
                    "starterTemplateAbsent": False,
                    "expectedSourceSignals": ["redacted source heading/body signal to fill"],
                    "unexpectedStarterSignals": ["remove after proving no starter-template terms remain"],
                    "proof": "redacted DOM proof to fill; nonblank frontend is not enough",
                },
                "actionEvidence": action_template(page["actions"]),
            }
            for page in pages
        ],
    }
    for item in template["pages"]:
        required_fields = {
            ACTION_TO_TEMPLATE_FIELD[action]
            for action in item["actionEvidence"]
            if action in ACTION_TO_TEMPLATE_FIELD
        }
        for key in ACTION_TO_TEMPLATE_FIELD.values():
            if key not in required_fields:
                item[key] = "not_required_existing_page_reuse"
    template.update(source_context(handoff))
    return template


def validation_command(filled_path: Path, handoff_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/validate_pages_site_info_execution_evidence.py "
        f"{filled_path} --handoff {handoff_path} --output {output_dir / 'pages-site-info-execution-validation.json'}"
    )


def apply_command(filled_path: Path, handoff_path: str, output_dir: Path) -> str:
    return (
        "python3 skills/allincms-bulk-content-upload/scripts/apply_pages_site_info_execution.py "
        f"--pages-site-info-handoff {handoff_path} "
        f"--pages-site-info-evidence {filled_path} "
        "--package <source-site-package.json> "
        "--confirmation <confirmation-record.json> "
        "--execution-plan <confirmed-site-execution-plan.json> "
        "--artifact-readiness <artifact-readiness.json> "
        "--created-site-binding <created-site-artifact-binding.json> "
        "--taxonomy-handoff <taxonomy-execution-handoff.json> "
        "--schema-capture-handoff <schema-capture-handoff.json> "
        f"--output-dir {output_dir / 'pages-site-info-applied'}"
    )


def build_notes(handoff: dict[str, Any]) -> str:
    page_count = len(normalize_handoff_pages(handoff))
    return "\n".join(
        [
            "# Pages/Site-Info Evidence Bundle",
            "",
            "This bundle is local scaffolding only. It does not authorize browser actions.",
            "",
            "Before filling `pages-site-info-evidence.filled.json`:",
            "- choose exactly one action at a time from the handoff",
            "- create the action-time authorization record",
            "- run the matching pre-mutation gate",
            "- replace any `<themeId>` or `<pageId>` placeholders with concrete current-browser IDs",
            "- capture backend request/state proof and frontend DOM proof for the action",
            "- stop before products/posts/media upload, taxonomy, domains, tracking, forms, batch upload, or cleanup",
            "",
            f"Expected page count: {page_count}",
            "",
            "The filled evidence is complete only when site-info is verified and every handoff page has proof for the actions listed in that page's handoff entry, plus frontend proof.",
        ]
    ) + "\n"


def build_bundle(*, handoff: dict[str, Any], handoff_path: str, output_dir: Path) -> dict[str, Any]:
    ensure_output_dir_outside_skill(output_dir)
    if handoff.get("kind") != "allincms_pages_site_info_browser_handoff":
        raise ValueError("handoff kind must be allincms_pages_site_info_browser_handoff")
    if handoff.get("remoteMutationsPerformed") is not False:
        raise ValueError("handoff must be local-only/no remote mutation")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "pages-site-info-evidence.template.json"
    filled_path = output_dir / "pages-site-info-evidence.filled.json"
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
        "kind": "allincms_pages_site_info_evidence_bundle",
        "generatedAt": now_iso(),
        "localOnly": True,
        "preparedOnly": True,
        "remoteMutationsPerformed": False,
        "isUserAuthorization": False,
        "handoff": handoff_path,
        "sourceCurrentStage": "pages_site_info_execution",
        "handoffReadyForBrowserStage": handoff.get("readyForBrowserStage", ""),
        "handoffPreflightIssues": handoff.get("preflightIssues", []),
        "siteKey": handoff.get("siteKey"),
        "frontendBaseUrl": handoff.get("frontendBaseUrl"),
        "pageCount": len(normalize_handoff_pages(handoff)),
        "evidenceTemplate": str(template_path),
        "filledEvidencePath": str(filled_path),
        "notes": str(notes_path),
        "validationCommand": str(validation_command_path),
        "applyCommand": str(apply_command_path),
        "browserStepsExecutable": False,
        "requiredBeforeUse": [
            "action-time authorization for each individual action",
            "matching pre-mutation gate pass",
            "concrete theme/page/route targets before browser mutation",
            "redacted backend and frontend proof for every page and site-info",
        ],
        "nextAction": "fill redacted evidence after browser actions, validate it, then run apply_pages_site_info_execution.py",
    }
    bundle.update(source_context(handoff))
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("kind") != "allincms_pages_site_info_evidence_bundle":
        issues.append("kind must be allincms_pages_site_info_evidence_bundle")
    for key in ("localOnly", "preparedOnly"):
        if bundle.get(key) is not True:
            issues.append(f"{key} must be true")
    for key in ("remoteMutationsPerformed", "isUserAuthorization", "browserStepsExecutable"):
        if bundle.get(key) is not False:
            issues.append(f"{key} must be false")
    for key in ("handoff", "siteKey", "frontendBaseUrl", "evidenceTemplate", "filledEvidencePath", "notes", "validationCommand", "applyCommand"):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            issues.append(f"{key} must be present")
    if not isinstance(bundle.get("pageCount"), int) or bundle["pageCount"] < 1:
        issues.append("pageCount must be a positive integer")
    preflight_issues = bundle.get("handoffPreflightIssues")
    if not isinstance(preflight_issues, list):
        issues.append("handoffPreflightIssues must be an array")
    required = bundle.get("requiredBeforeUse")
    if not isinstance(required, list) or "matching pre-mutation gate pass" not in required:
        issues.append("requiredBeforeUse must include matching pre-mutation gate pass")
    issues.extend(source_context_issues(bundle))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local pages/site-info evidence bundle.")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = Path(args.output_dir).expanduser().resolve()
        bundle = build_bundle(
            handoff=load_json(Path(args.handoff), "pages/site-info handoff"),
            handoff_path=args.handoff,
            output_dir=output_dir,
        )
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError("pages/site-info evidence bundle validation failed:\n- " + "\n- ".join(issues))
        write_json(output_dir / "evidence-bundle.json", bundle)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote pages/site-info evidence bundle: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
