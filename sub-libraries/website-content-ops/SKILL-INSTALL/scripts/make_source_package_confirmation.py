#!/usr/bin/env python3
"""Create a local user-confirmation record for an AllinCMS source-site package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_source_package_confirmation import (
    package_required_accepted_fields,
    package_counts,
    same_resolved_path,
    validate_confirmation,
    validate_source_review_objective_coverage,
)
from validate_source_package_review_packet import load_json as load_review_packet_json
from validate_source_package_review_packet import validate_review_packet
from validate_source_site_package import load_json as load_package_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_deferrals(values: list[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for raw in values:
        parts = [part.strip() for part in raw.split("|")]
        if len(parts) < 3:
            raise SystemExit("ERROR: --accepted-deferral must use field|decision|reason")
        result.append({"field": parts[0], "decision": parts[1], "reason": "|".join(parts[2:]).strip()})
    return result


def suggested_accepted_fields(review_packet: dict[str, Any]) -> list[str]:
    fields = review_packet.get("suggestedAcceptedFields")
    if not isinstance(fields, list):
        return []
    return sorted({item.strip() for item in fields if isinstance(item, str) and item.strip()})


def suggested_accepted_deferrals(review_packet: dict[str, Any]) -> list[dict[str, str]]:
    deferrals = review_packet.get("suggestedAcceptedDeferrals")
    if not isinstance(deferrals, list):
        return []
    result: list[dict[str, str]] = []
    for item in deferrals:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", "")).strip()
        decision = str(item.get("decision", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if field and decision and reason:
            result.append({"field": field, "decision": decision, "reason": reason})
    return result


def file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def confirmation_decision_matrix(
    review_packet: dict[str, Any],
    accepted_fields: list[str],
    accepted_deferrals: list[dict[str, str]],
) -> list[dict[str, Any]]:
    fields = [
        item
        for item in review_packet.get("confirmationFields", [])
        if isinstance(item, str) and item.strip()
    ]
    if not fields:
        fields = sorted(
            {item for item in accepted_fields if isinstance(item, str) and item.strip()}
            | {
                item.get("field")
                for item in accepted_deferrals
                if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
            }
        )
    accepted = {field for field in accepted_fields if isinstance(field, str) and field.strip()}
    deferrals = {
        item.get("field"): item
        for item in accepted_deferrals
        if isinstance(item, dict) and isinstance(item.get("field"), str) and item.get("field")
    }
    matrix: list[dict[str, Any]] = []
    for field in fields:
        if field in deferrals:
            deferral = deferrals[field]
            matrix.append(
                {
                    "field": field,
                    "decision": "defer",
                    "source": "acceptedDeferrals",
                    "deferDecision": deferral.get("decision", ""),
                    "reason": deferral.get("reason", ""),
                    "blocksRemoteMutation": False,
                }
            )
        elif field in accepted:
            matrix.append(
                {
                    "field": field,
                    "decision": "accept",
                    "source": "acceptedFields",
                    "deferDecision": "",
                    "reason": "",
                    "blocksRemoteMutation": False,
                }
            )
        else:
            matrix.append(
                {
                    "field": field,
                    "decision": "missing_decision",
                    "source": "",
                    "deferDecision": "",
                    "reason": "",
                    "blocksRemoteMutation": True,
                }
            )
    return matrix


def load_review_objective_coverage(
    path: str,
    *,
    package_path: str,
    review_packet_path: str,
) -> dict[str, Any]:
    coverage = load_review_packet_json(Path(path), "source review objective coverage")
    issues: list[str] = []
    validate_source_review_objective_coverage(coverage, issues)
    if not same_resolved_path(coverage.get("reviewPacket"), review_packet_path):
        issues.append("sourceReviewObjectiveCoverage.reviewPacket must match --review-packet")
    if not same_resolved_path(coverage.get("sourcePackage"), package_path):
        issues.append("sourceReviewObjectiveCoverage.sourcePackage must match --package")
    if issues:
        raise SystemExit("ERROR: invalid source review objective coverage:\n- " + "\n- ".join(issues))
    return coverage


def build_confirmation(args: argparse.Namespace) -> dict[str, Any]:
    package = load_package_json(Path(args.package))
    review_packet = load_review_packet_json(Path(args.review_packet), "review packet")
    review_issues = validate_review_packet(review_packet, package)
    if review_issues:
        raise SystemExit("ERROR: invalid review packet:\n- " + "\n- ".join(review_issues))
    review_objective_coverage_path = getattr(args, "source_review_objective_coverage", "") or ""
    review_objective_coverage = (
        load_review_objective_coverage(
            review_objective_coverage_path,
            package_path=args.package,
            review_packet_path=args.review_packet,
        )
        if review_objective_coverage_path
        else None
    )
    explicit_fields = parse_csv(args.accepted_fields)
    accepted_fields = sorted(
        package_required_accepted_fields(package)
        | set(explicit_fields or suggested_accepted_fields(review_packet))
    )
    accepted_deferrals = (
        parse_deferrals(args.accepted_deferral)
        if args.accepted_deferral
        else suggested_accepted_deferrals(review_packet)
    )
    gate = package.get("confirmationGate") if isinstance(package.get("confirmationGate"), dict) else {}
    package_blocked_actions = gate.get("blockedRemoteActions")
    if not isinstance(package_blocked_actions, list):
        package_blocked_actions = []
    confirmation = {
        "kind": "allincms_source_site_package_confirmation",
        "confirmedAt": now_iso(),
        "confirmedBy": "user",
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "isRemoteMutationAuthorization": False,
        "sourcePackage": args.package,
        "sourcePackageSha256": file_sha256(args.package),
        "sourceReviewPacket": args.review_packet,
        "sourceReviewPacketSha256": file_sha256(args.review_packet),
        "userConfirmationText": args.user_confirmation_text,
        "acceptedFields": accepted_fields,
        "acceptedDeferrals": accepted_deferrals,
        "confirmationDecisionMatrix": confirmation_decision_matrix(
            review_packet,
            accepted_fields,
            accepted_deferrals,
        ),
        "confirmedCounts": package_counts(package),
        "contentGoalCoverage": review_packet.get("contentGoalCoverage"),
        "contentQualityReview": review_packet.get("contentQualityReview"),
        "contentGoalOverages": review_packet.get("contentGoalOverages", {}),
        "wikiReview": review_packet.get("wikiReview", {}),
        "blockedRemoteActionsStillRequireActionAuthorization": sorted(
            {item for item in package_blocked_actions if isinstance(item, str)}
        ),
        "notes": args.notes,
        **(
            {"sourceReviewObjectiveCoverage": review_objective_coverage}
            if review_objective_coverage is not None
            else {}
        ),
        "nextActions": [
            "Create or select the AllinCMS site only after action-specific authorization.",
            "Capture current-site schemas for products/posts/pages/forms before upload or JSON replay.",
            "Use this confirmation as content intent proof, not as mutation permission.",
        ],
    }
    issues = validate_confirmation(confirmation, package)
    if issues:
        raise SystemExit("ERROR: invalid confirmation:\n- " + "\n- ".join(issues))
    return confirmation


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an AllinCMS source-site package confirmation JSON.")
    parser.add_argument("--package", required=True, help="Validated source-site package JSON")
    parser.add_argument("--review-packet", required=True, help="Validated source-package review packet JSON")
    parser.add_argument(
        "--source-review-objective-coverage",
        default="",
        help="Optional make_source_review_objective_coverage.py output to carry into the confirmation",
    )
    parser.add_argument("--user-confirmation-text", required=True, help="Current user text confirming the package")
    parser.add_argument("--accepted-fields", default="", help="Extra accepted fields, comma-separated")
    parser.add_argument("--accepted-deferral", action="append", default=[], help="field|decision|reason; repeatable")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    confirmation = build_confirmation(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(confirmation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source package confirmation: {output}")
    print("remoteMutationAuthorization=false")
    if args.json:
        print(json.dumps(confirmation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
