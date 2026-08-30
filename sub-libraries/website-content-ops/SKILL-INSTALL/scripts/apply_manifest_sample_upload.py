#!/usr/bin/env python3
"""Validate one manifest sample upload and refresh source execution status."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from content_goal_coverage_utils import (
    load_matching_coverage,
    load_matching_confirmation_decision_matrix,
    load_matching_quality_review,
    load_matching_wiki_review,
    matching_content_counts,
    matching_created_site_submitted_values,
    matching_quality_review,
    matching_wiki_review,
)
from prepare_source_next_stage import build_default_handoff as build_source_next_handoff
from summarize_source_execution_status import summarize as summarize_source_status
from validate_manifest import load_manifest
from validate_manifest_sample_upload_evidence import (
    load_json as load_sample_json,
    progress_entry,
    validate_sample_evidence,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def load_json(path: str, label: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def review_packet_from_confirmation(confirmation_path: str) -> str:
    if not confirmation_path:
        return ""
    confirmation = load_json(confirmation_path, "confirmation")
    value = confirmation.get("sourceReviewPacket")
    return value if isinstance(value, str) else ""


def artifact_paths(output_dir: Path, content_type: str) -> dict[str, Path]:
    return {
        "validation": output_dir / f"{content_type}-manifest-sample-upload-validation.json",
        "progress_entry": output_dir / f"{content_type}-manifest-sample-progress-entry.json",
        "source_status": output_dir / "source-execution-status.after-manifest-sample.json",
        "next_stage_handoff": output_dir / "source-next-stage-handoff.after-manifest-sample.json",
        "summary": output_dir / f"{content_type}-manifest-sample-upload-apply-summary.json",
    }


def sample_paths(existing: list[str], current: str) -> list[str]:
    paths = [item for item in existing if item and item != current]
    paths.append(current)
    return paths


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    content_type = str(manifest.get("contentType", "")).strip() or "content"
    paths = artifact_paths(output_dir, content_type)
    source_coverage, source_coverage_issues = load_matching_coverage(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    if source_coverage_issues:
        raise SystemExit("ERROR: source content goal coverage invalid:\n- " + "\n- ".join(source_coverage_issues))
    source_quality, source_quality_issues = load_matching_quality_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    manifest_quality, manifest_quality_issues = matching_quality_review(
        [
            ("source context", {"contentQualityReview": source_quality} if source_quality else None),
            ("manifest", manifest),
        ],
        require_when_present=False,
    )
    quality_issues = [*source_quality_issues, *manifest_quality_issues]
    if quality_issues:
        raise SystemExit("ERROR: source content quality review invalid:\n- " + "\n- ".join(quality_issues))
    source_wiki_review, source_wiki_review_issues = load_matching_wiki_review(
        [
            ("source package", args.package),
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ]
    )
    manifest_wiki_review, manifest_wiki_review_issues = matching_wiki_review(
        [
            ("source context", {"wikiReview": source_wiki_review} if source_wiki_review else None),
            ("manifest", manifest),
        ],
        require_when_present=False,
    )
    wiki_review_issues = [*source_wiki_review_issues, *manifest_wiki_review_issues]
    if wiki_review_issues:
        raise SystemExit("ERROR: source wiki review invalid:\n- " + "\n- ".join(wiki_review_issues))
    decision_matrix, decision_matrix_issues = load_matching_confirmation_decision_matrix(
        [
            ("review packet", args.review_packet or review_packet_from_confirmation(args.confirmation)),
            ("confirmation", args.confirmation),
            ("execution plan", args.execution_plan),
            ("artifact readiness", args.artifact_readiness),
            ("created-site binding", args.created_site_binding),
        ],
        require_when_any_source=True,
    )
    if decision_matrix_issues:
        raise SystemExit("ERROR: source confirmation decision matrix invalid:\n- " + "\n- ".join(decision_matrix_issues))

    evidence = load_sample_json(Path(args.sample_evidence), "manifest sample evidence")
    source_counts, source_counts_issues = matching_content_counts(
        [
            ("source package", load_json(args.package, "source package") if args.package else None),
            (
                "review packet",
                load_json(args.review_packet or review_packet_from_confirmation(args.confirmation), "review packet")
                if args.review_packet or review_packet_from_confirmation(args.confirmation)
                else None,
            ),
            ("confirmation", load_json(args.confirmation, "confirmation") if args.confirmation else None),
            ("execution plan", load_json(args.execution_plan, "execution plan") if args.execution_plan else None),
            ("artifact readiness", load_json(args.artifact_readiness, "artifact readiness") if args.artifact_readiness else None),
            ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
            ("manifest", manifest),
            ("sample evidence", evidence),
        ]
    )
    if source_counts_issues:
        raise SystemExit("ERROR: source content counts invalid:\n- " + "\n- ".join(source_counts_issues))
    submitted_values, submitted_values_issues = matching_created_site_submitted_values(
        [
            ("created-site binding", load_json(args.created_site_binding, "created-site binding") if args.created_site_binding else None),
            ("manifest", manifest),
            ("sample evidence", evidence),
        ],
        require_when_present=False,
    )
    if submitted_values_issues:
        raise SystemExit("ERROR: created-site submitted values invalid:\n- " + "\n- ".join(submitted_values_issues))
    issues = validate_sample_evidence(evidence, manifest)
    validation = {
        "kind": "allincms_manifest_sample_upload_evidence_validation",
        "generatedAt": now_iso(),
        "valid": not issues,
        "evidence": args.sample_evidence,
        "manifest": args.manifest,
        "siteKey": evidence.get("siteKey"),
        "contentType": evidence.get("contentType"),
        "sampleSlug": evidence.get("sampleSlug"),
        "issues": issues,
        "batchPrerequisiteSatisfied": not issues,
    }
    write_json(paths["validation"], validation)

    progress_path = ""
    if not issues:
        progress_path = write_json(paths["progress_entry"], progress_entry(evidence))
    elif args.fail_on_invalid:
        raise SystemExit("ERROR: manifest sample upload evidence invalid:\n- " + "\n- ".join(issues))
    merged_sample_paths = sample_paths(args.existing_sample_evidence, args.sample_evidence) if not issues else args.existing_sample_evidence

    source_status = summarize_source_status(
        SimpleNamespace(
            package=args.package,
            review_packet=args.review_packet or review_packet_from_confirmation(args.confirmation),
            confirmation=args.confirmation,
            execution_plan=args.execution_plan,
            artifact_readiness=args.artifact_readiness,
            create_site_handoff=getattr(args, "create_site_handoff", ""),
            created_site_binding=args.created_site_binding,
            pages_site_info_handoff=args.pages_site_info_handoff,
            pages_site_info_evidence=args.pages_site_info_evidence,
            pages_site_info_validation=args.pages_site_info_validation,
            taxonomy_handoff=args.taxonomy_handoff,
            taxonomy_evidence=args.taxonomy_evidence,
            taxonomy_validation=args.taxonomy_validation,
            schema_capture_handoff=args.schema_capture_handoff,
            upload_readiness=args.upload_readiness,
            sample_evidence=merged_sample_paths,
            batch_evidence=args.batch_evidence,
            batch_validation=args.batch_validation,
            forms_media_settings=getattr(args, "forms_media_settings", ""),
            launch_acceptance=args.launch_acceptance,
        )
    )
    write_json(paths["source_status"], source_status)
    next_stage_handoff = build_source_next_handoff(
        status_path=str(paths["source_status"]),
        output_path=str(paths["next_stage_handoff"]),
        output_dir=str(output_dir / "next-stage"),
        manifest=args.manifest,
        sample_evidence=args.sample_evidence,
    )

    ready_for_next = "blocked_manifest_sample_evidence" if issues else str(source_status.get("currentStage"))
    summary = {
        "kind": "allincms_manifest_sample_upload_apply_summary",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "siteKey": evidence.get("siteKey"),
        "contentType": evidence.get("contentType"),
        "sampleSlug": evidence.get("sampleSlug"),
        "contentGoalCoverage": source_coverage or {},
        "contentCounts": source_counts or {},
        "contentQualityReview": manifest_quality or source_quality or {},
        "wikiReview": manifest_wiki_review or source_wiki_review or {},
        "confirmationDecisionMatrix": decision_matrix or [],
        **({"createdSiteSubmittedValues": submitted_values} if submitted_values else {}),
        "validationValid": not issues,
        "readyForNextStage": ready_for_next,
        "artifacts": {
            "sampleValidation": str(paths["validation"]),
            "sampleProgressEntry": progress_path,
            "existingSampleEvidence": args.existing_sample_evidence,
            "mergedSampleEvidence": merged_sample_paths,
            "sourceExecutionStatus": str(paths["source_status"]),
            "sourceNextStageHandoff": str(paths["next_stage_handoff"]),
        },
        "validation": {"manifestSampleIssues": issues},
        "adversarialChecks": [
            "This helper validates redacted sample evidence and refreshes local status only; it does not mutate AllinCMS.",
            "A valid manifest sample proves one source-generated slug only; it does not upload the remaining manifest items.",
            "Batch upload remains locked until sourceExecutionStatus.currentStage is batch_upload and the batch authorization/gate passes.",
            "Keep products and posts sample evidence separate; one content type's sample does not validate the other.",
            "Source next-stage handoff is generated from refreshed status and must be followed before batch preparation or browser work.",
        ],
        "nextAction": str(source_status.get("nextAction") or "inspect refreshed source execution status"),
        "sourceNextStage": {
            "currentStage": next_stage_handoff.get("currentStage"),
            "mode": next_stage_handoff.get("mode"),
            "browserWorkRequired": next_stage_handoff.get("browserWorkRequired"),
        },
    }
    write_json(paths["summary"], summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply manifest sample upload evidence to source execution status.")
    parser.add_argument("--manifest", required=True, help="Schema-verified posts/products manifest JSON")
    parser.add_argument("--sample-evidence", required=True, help="allincms_manifest_sample_upload_evidence JSON")
    parser.add_argument("--package", default="")
    parser.add_argument("--review-packet", default="")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--execution-plan", default="")
    parser.add_argument("--artifact-readiness", default="")
    parser.add_argument("--create-site-handoff", default="")
    parser.add_argument("--created-site-binding", default="")
    parser.add_argument("--pages-site-info-handoff", default="")
    parser.add_argument("--pages-site-info-evidence", default="")
    parser.add_argument("--pages-site-info-validation", default="")
    parser.add_argument("--taxonomy-handoff", default="")
    parser.add_argument("--taxonomy-evidence", default="")
    parser.add_argument("--taxonomy-validation", default="")
    parser.add_argument("--schema-capture-handoff", default="")
    parser.add_argument("--upload-readiness", action="append", default=[])
    parser.add_argument("--existing-sample-evidence", action="append", default=[])
    parser.add_argument("--batch-evidence", default="")
    parser.add_argument("--batch-validation", default="")
    parser.add_argument("--forms-media-settings", default="")
    parser.add_argument("--launch-acceptance", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = build(args)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote manifest sample upload apply summary: {summary['artifacts']['sourceExecutionStatus']}")
        print(f"validationValid={str(summary['validationValid']).lower()} nextAction={summary['nextAction']}")
    if args.fail_on_invalid and not summary["validationValid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
