#!/usr/bin/env python3
"""Summarize source-file-to-site objective coverage from acceptance evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def load_json(path: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: {label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def load_optional_json(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def issue_keys(report: dict[str, Any]) -> set[str]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return set()
    return {item.get("key") for item in issues if isinstance(item, dict) and isinstance(item.get("key"), str)}


def issue_messages(report: dict[str, Any], keys: set[str]) -> list[str]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return []
    messages: list[str] = []
    for item in issues:
        if not isinstance(item, dict) or item.get("key") not in keys:
            continue
        message = item.get("message")
        evidence = item.get("evidence")
        text = str(message) if message else str(item.get("key"))
        if evidence:
            text = f"{text} [{evidence}]"
        messages.append(text)
    return messages


def path_exists(path: str) -> bool:
    return bool(path) and Path(path).expanduser().exists()


def nested(report: dict[str, Any], *keys: str) -> Any:
    value: Any = report
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def artifact_path(report: dict[str, Any], key: str) -> str:
    value = nested(report, "artifacts", key)
    return value if isinstance(value, str) else ""


def artifact_paths(report: dict[str, Any], key: str) -> list[str]:
    value = nested(report, "artifacts", key)
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def count_value(report: dict[str, Any], key: str) -> int:
    counts = nested(report, "contentGoalCoverage", "counts")
    if isinstance(counts, dict):
        value = counts.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    counts = report.get("contentCounts")
    if isinstance(counts, dict):
        value = counts.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return 0


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def adversarial_check_blockers(report: dict[str, Any], round_closeout: dict[str, Any] | None) -> list[str]:
    checks = string_list(report.get("adversarialChecks"))
    blockers: list[str] = []
    if not checks:
        blockers.append("final acceptance report must carry adversarialChecks")
    check_text = " ".join(checks).lower()
    required_terms = {
        "source": "source/wiki/package scope",
        "contentgoalcoverage": "content goal coverage",
        "contentqualityreview": "content quality review",
        "wiki": "source wiki layer",
        "confirmationdecisionmatrix": "user confirmation decision matrix",
        "site": "created/selected site binding",
        "sample": "sample upload proof",
        "batch": "batch upload/publish proof",
        "frontend": "frontend launch verification",
        "round closeout": "final closeout proof",
    }
    for term, label in required_terms.items():
        if term not in check_text:
            blockers.append(f"adversarialChecks must mention {label}")
    sedimentation = round_closeout.get("sedimentation") if isinstance(round_closeout, dict) else None
    sedimentation_status = sedimentation.get("status") if isinstance(sedimentation, dict) else sedimentation
    if sedimentation_status not in {"updated", "none", "read-only-deferred"}:
        blockers.append("final round closeout must carry accepted sedimentation status")
    proof = round_closeout.get("proof") if isinstance(round_closeout, dict) else None
    if not isinstance(proof, list) or not proof:
        blockers.append("final round closeout must carry proof entries for the completed run")
    return blockers


def package_source_counts(package: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(package, dict):
        return {}
    source_set = package.get("sourceSet")
    if not isinstance(source_set, dict):
        return {}
    return {
        "inputFiles": len(source_set.get("inputFiles") or []) if isinstance(source_set.get("inputFiles"), list) else 0,
        "rawExtractionRefs": len(source_set.get("rawExtractionRefs") or [])
        if isinstance(source_set.get("rawExtractionRefs"), list)
        else 0,
        "wikiRefs": len(source_set.get("wikiRefs") or []) if isinstance(source_set.get("wikiRefs"), list) else 0,
    }


def status_for(
    report: dict[str, Any],
    *,
    required_paths: list[str] | None = None,
    blocking_keys: set[str] | None = None,
    extra_ok: bool = True,
    accepted_required: bool = False,
) -> str:
    blocking_keys = blocking_keys or set()
    keys = issue_keys(report)
    if keys & blocking_keys:
        return "missing"
    if required_paths and any(not path_exists(path) for path in required_paths):
        return "missing"
    if not extra_ok:
        return "missing"
    if accepted_required and report.get("accepted") is not True:
        return "incomplete"
    return "proven"


def add_item(
    items: list[dict[str, Any]],
    *,
    item_id: str,
    label: str,
    status: str,
    evidence: list[str] | None = None,
    blockers: list[str] | None = None,
    required_for_completion: bool = True,
) -> None:
    items.append(
        {
            "id": item_id,
            "label": label,
            "status": status,
            "requiredForCompletion": required_for_completion,
            "evidence": evidence or [],
            "blockers": blockers or [],
        }
    )


def build_coverage(report: dict[str, Any], *, objective: str = "", acceptance_report_path: str = "") -> dict[str, Any]:
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    package_path = artifact_path(report, "sourcePackage")
    package = load_optional_json(package_path)
    source_counts = package_source_counts(package)
    keys = issue_keys(report)
    accepted = report.get("accepted") is True and report.get("complete") is True
    round_closeout_path = artifact_path(report, "roundCloseout")
    round_closeout = load_optional_json(round_closeout_path)

    items: list[dict[str, Any]] = []

    source_blockers = {"package_missing", "package_kind", "source_status_load_failed"}
    add_item(
        items,
        item_id="source_files_ingested",
        label="User files are inventoried/extracted into a source set outside the skill package",
        status=status_for(
            report,
            required_paths=[package_path],
            blocking_keys=source_blockers,
            extra_ok=accepted or source_counts.get("inputFiles", 0) > 0,
        ),
        evidence=[package_path],
        blockers=issue_messages(report, source_blockers)
        or (
            []
            if accepted or source_counts.get("inputFiles", 0) > 0
            else ["source package must preserve sourceSet.inputFiles or the final acceptance report must be accepted"]
        ),
    )

    wiki_blockers = {
        "source_wiki_missing",
        "source_wiki_invalid",
        "source_wiki_markdown_missing",
        "wiki_review_invalid",
        "wiki_review_binding_mismatch",
    }
    add_item(
        items,
        item_id="source_wiki_ready",
        label="Source material is distilled into JSON plus readable Markdown wiki",
        status=status_for(
            report,
            required_paths=[artifact_path(report, "sourceWiki"), artifact_path(report, "sourceWikiMarkdownIndex")],
            blocking_keys=wiki_blockers,
        ),
        evidence=[artifact_path(report, "sourceWiki"), artifact_path(report, "sourceWikiMarkdownIndex")],
        blockers=issue_messages(report, wiki_blockers),
    )

    package_blockers = {
        "review_packet_missing",
        "review_packet_kind",
        "content_goal_coverage_invalid",
        "content_quality_review_invalid",
        "content_counts_invalid",
    }
    add_item(
        items,
        item_id="publishable_package_ready",
        label="Publishable site package and user review packet cover site info, pages, products, posts, forms/media policies, navigation, and taxonomy",
        status=status_for(
            report,
            required_paths=[package_path, artifact_path(report, "reviewPacket")],
            blocking_keys=package_blockers,
            extra_ok=count_value(report, "pages") > 0 and count_value(report, "products") > 0 and count_value(report, "posts") > 0,
        ),
        evidence=[package_path, artifact_path(report, "reviewPacket")],
        blockers=issue_messages(report, package_blockers)
        or (
            []
            if count_value(report, "pages") > 0 and count_value(report, "products") > 0 and count_value(report, "posts") > 0
            else ["contentGoalCoverage/counts must include at least one page, product, and post"]
        ),
    )

    confirmation_blockers = {
        "confirmation_missing",
        "confirmation_kind",
        "confirmation_authorization_confusion",
        "confirmation_decision_matrix_invalid",
    }
    add_item(
        items,
        item_id="user_confirmation_recorded",
        label="User confirmed the review packet, with accepted fields and deferrals bound to package hashes",
        status=status_for(report, required_paths=[artifact_path(report, "confirmation")], blocking_keys=confirmation_blockers),
        evidence=[artifact_path(report, "confirmation")],
        blockers=issue_messages(report, confirmation_blockers),
    )

    created_site_blockers = {
        "created_site_binding_missing",
        "created_site_binding_invalid",
        "created_site_required",
        "created_site_submitted_values_invalid",
        "site_identity_mismatch",
    }
    add_item(
        items,
        item_id="new_site_created_and_bound",
        label="AI-created AllinCMS site is verified and bound back to the confirmed source package",
        status=status_for(report, required_paths=[artifact_path(report, "createdSiteBinding")], blocking_keys=created_site_blockers),
        evidence=[artifact_path(report, "createdSiteBinding")],
        blockers=issue_messages(report, created_site_blockers),
    )

    pages_blockers = {"final_content_count_mismatch", "final_structure_count_mismatch", "launch_acceptance_incomplete"}
    add_item(
        items,
        item_id="pages_and_site_info_published",
        label="Single/static pages, navigation, routes, and necessary site-info fields are saved, published, and frontend-verified",
        status=status_for(report, blocking_keys=pages_blockers, accepted_required=True),
        evidence=[
            str(nested(report, "artifacts", "finalContentCounts") or ""),
            str(nested(report, "artifacts", "finalStructureCounts") or ""),
            artifact_path(report, "launchAcceptance"),
        ],
        blockers=issue_messages(report, pages_blockers),
    )

    upload_blockers = {
        "upload_readiness_missing",
        "upload_readiness_invalid",
        "sample_evidence_missing",
        "sample_evidence_invalid",
        "sample_direct_validation_failed",
        "batch_validation_missing",
        "batch_validation_invalid",
        "batch_direct_validation_failed",
        "final_content_count_mismatch",
    }
    add_item(
        items,
        item_id="products_posts_uploaded",
        label="Products and posts have schema-verified manifests, sample proof, batch upload/publish proof, and frontend detail verification",
        status=status_for(
            report,
            required_paths=artifact_paths(report, "uploadReadiness")
            + artifact_paths(report, "sampleEvidence")
            + artifact_paths(report, "batchValidation"),
            blocking_keys=upload_blockers,
        ),
        evidence=artifact_paths(report, "uploadReadiness")
        + artifact_paths(report, "sampleEvidence")
        + artifact_paths(report, "batchValidation"),
        blockers=issue_messages(report, upload_blockers),
    )

    settings_blockers = {
        "forms_media_settings_missing",
        "forms_media_settings_invalid",
        "forms_media_settings_direct_validation_failed",
        "final_structure_count_mismatch",
    }
    add_item(
        items,
        item_id="forms_media_settings_handled",
        label="Forms, media, domains, tracking, contact/legal/site-info decisions are verified or explicitly deferred",
        status=status_for(report, required_paths=[artifact_path(report, "formsMediaSettings")], blocking_keys=settings_blockers),
        evidence=[artifact_path(report, "formsMediaSettings")],
        blockers=issue_messages(report, settings_blockers),
    )

    frontend_blockers = {
        "final_frontend_audit_missing",
        "final_frontend_audit_invalid",
        "final_frontend_audit_direct_validation_failed",
        "launch_acceptance_missing",
        "launch_acceptance_incomplete",
        "final_structure_count_mismatch",
    }
    add_item(
        items,
        item_id="final_frontend_launch_verified",
        label="Final frontend launch QA passes for public routes, detail pages, rich text, images, navigation, and broken-entry checks",
        status=status_for(
            report,
            required_paths=[artifact_path(report, "finalFrontendAudit"), artifact_path(report, "launchAcceptance")],
            blocking_keys=frontend_blockers,
        ),
        evidence=[artifact_path(report, "finalFrontendAudit"), artifact_path(report, "launchAcceptance")],
        blockers=issue_messages(report, frontend_blockers),
    )

    closeout_blockers = {
        "cleanup_evidence_missing",
        "cleanup_evidence_invalid",
        "cleanup_evidence_direct_validation_failed",
        "round_closeout_missing",
        "round_closeout_invalid",
    }
    add_item(
        items,
        item_id="cleanup_and_sedimentation_closed",
        label="Probe/test cleanup is verified and the skill sedimentation/final closeout is recorded",
        status=status_for(
            report,
            required_paths=[artifact_path(report, "cleanupEvidence"), artifact_path(report, "roundCloseout")],
            blocking_keys=closeout_blockers,
        ),
        evidence=[artifact_path(report, "cleanupEvidence"), artifact_path(report, "roundCloseout")],
        blockers=issue_messages(report, closeout_blockers),
    )

    adversarial_blockers = adversarial_check_blockers(report, round_closeout)
    add_item(
        items,
        item_id="adversarial_checks_completed",
        label="Each major step is guarded by adversarial checks, and reusable findings are sedimented into the skill closeout",
        status="proven" if not adversarial_blockers else "missing",
        evidence=[acceptance_report_path or artifacts.get("acceptanceReport", ""), round_closeout_path],
        blockers=adversarial_blockers,
    )

    missing = [item for item in items if item["requiredForCompletion"] and item["status"] != "proven"]
    return {
        "kind": "allincms_source_objective_coverage",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "objective": objective or report.get("objective", ""),
        "acceptanceReport": acceptance_report_path or artifacts.get("acceptanceReport", ""),
        "acceptedByFinalGate": accepted,
        "complete": accepted and not missing,
        "counts": {
            "pages": count_value(report, "pages"),
            "products": count_value(report, "products"),
            "posts": count_value(report, "posts"),
            "forms": count_value(report, "forms"),
            "media": count_value(report, "media"),
            "siteInfoFields": count_value(report, "siteInfoFields"),
            "sourceInputFiles": source_counts.get("inputFiles", 0),
            "rawExtractionRefs": source_counts.get("rawExtractionRefs", 0),
            "wikiRefs": source_counts.get("wikiRefs", 0),
        },
        "coverage": items,
        "missingRequiredIds": [item["id"] for item in missing],
        "issuesFromAcceptance": report.get("issues") if isinstance(report.get("issues"), list) else [],
        "adversarialChecks": [
            "Do not treat this objective coverage report as browser proof; it summarizes the final acceptance report.",
            "Do not mark the user objective complete unless complete=true and validate_source_run_acceptance.py also accepted the same artifacts.",
            "Do not use manual UI proof for one product/post as batch upload proof unless schema-verified manifests, sample evidence, batch validation, and final frontend audit are present.",
            "Do not use user content confirmation as remote mutation authorization.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize objective coverage from a source-run acceptance report.")
    parser.add_argument("acceptance_report")
    parser.add_argument("--objective", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    ensure_output_outside_skill(output)
    report = load_json(args.acceptance_report, "acceptance report")
    if report.get("kind") != "allincms_source_run_acceptance_validation":
        raise SystemExit("ERROR: acceptance report kind must be allincms_source_run_acceptance_validation")
    coverage = build_coverage(report, objective=args.objective, acceptance_report_path=args.acceptance_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
    if args.fail_on_incomplete and not coverage.get("complete"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
