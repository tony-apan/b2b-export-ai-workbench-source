#!/usr/bin/env python3
"""Build a final_frontend_audit browser-stage result from a redacted audit report."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from apply_browser_stage_result import build_stage_result, validate_browser_stage_result
from build_browser_stage_packet import validate_browser_stage_packet
from content_goal_coverage_utils import (
    load_matching_confirmation_decision_matrix,
    load_matching_coverage,
    load_matching_created_site_submitted_values,
    load_matching_quality_review,
    load_matching_wiki_review,
    matching_content_counts,
)


PROOF_HTTP = "HTTP status report"
PROOF_DOM = "DOM/rich-text report"
PROOF_IMAGE = "image report"
PROOF_EMPTY_BROKEN = "broken-entry list empty"

DOM_ISSUE_CODES = {
    "literal_bold",
    "literal_inline_code",
    "literal_markdown_image",
    "literal_markdown_link",
    "literal_pipe_table",
    "jsx_style_object",
    "html_tag_text",
    "missing_h1",
    "multiple_h1",
    "duplicate_h1_text",
    "content_type",
}
IMAGE_ISSUE_CODES = {"image_missing_src", "image_missing_alt"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_packet(path: Path) -> dict[str, Any]:
    packet = load_json(path)
    if not isinstance(packet, dict):
        raise ValueError("packet JSON root must be an object")
    validation = validate_browser_stage_packet(packet)
    if not validation["ok"]:
        raise ValueError("packet validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    if packet.get("stageId") != "final_frontend_audit":
        raise ValueError("packet stageId must be final_frontend_audit")
    if packet.get("authorizationRequired") is not False:
        raise ValueError("final_frontend_audit packet must not require mutation authorization")
    return packet


def load_reports(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("audit report must be a JSON array")
    reports: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"audit report item {index} must be an object")
        reports.append(item)
    if not reports:
        raise ValueError("audit report must contain at least one route report")
    return reports


def issue_code(issue: Any) -> str:
    if not isinstance(issue, dict):
        return "unknown"
    code = issue.get("code")
    return str(code).strip() or "unknown"


def route_label(report: dict[str, Any], index: int) -> str:
    url = report.get("url")
    return str(url).strip() if isinstance(url, str) and url.strip() else f"report[{index}]"


def route_pattern_from_url(value: str) -> str:
    path = urlsplit(value).path or "/"
    if not path.startswith("/"):
        path = "/" + path
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) == 2 and parts[0] in {"posts", "products"}:
        return f"/{parts[0]}/{{slug}}"
    return path


def url_fingerprint(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def report_route_key(report: dict[str, Any], index: int) -> str:
    value = report.get("url")
    if not isinstance(value, str) or not value.strip():
        return f"report[{index}]"
    return route_pattern_from_url(value.strip())


def report_route_instance(report: dict[str, Any], index: int) -> str:
    value = report.get("routeInstance")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return report_route_key(report, index)


def has_detail_instance_identity(reports: list[dict[str, Any]]) -> bool:
    detail_reports = [
        report
        for index, report in enumerate(reports)
        if report_route_key(report, index) in {"/posts/{slug}", "/products/{slug}"}
    ]
    if len(detail_reports) <= 1:
        return True
    instances = [report.get("routeInstance") for report in detail_reports]
    return all(isinstance(instance, str) and instance.strip() for instance in instances) and len(set(instances)) == len(instances)


def validate_expected_coverage(
    reports: list[dict[str, Any]],
    audit_inputs_summary: dict[str, Any] | None,
    expected_statuses: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    report_count = len(reports)
    report_routes = {report_route_key(report, index) for index, report in enumerate(reports)}

    if audit_inputs_summary is not None:
        expected_static_count = audit_inputs_summary.get("staticRouteCount")
        expected_detail_count = audit_inputs_summary.get("detailRouteCount")
        if not isinstance(expected_static_count, int) or isinstance(expected_static_count, bool):
            blockers.append("audit inputs summary missing staticRouteCount")
        if not isinstance(expected_detail_count, int) or isinstance(expected_detail_count, bool):
            blockers.append("audit inputs summary missing detailRouteCount")
        if (
            isinstance(expected_static_count, int)
            and not isinstance(expected_static_count, bool)
            and isinstance(expected_detail_count, int)
            and not isinstance(expected_detail_count, bool)
        ):
            expected_total = expected_static_count + expected_detail_count
            if report_count != expected_total:
                blockers.append(f"audit report route count {report_count} != expected {expected_total}")
            if expected_detail_count > 1 and not has_detail_instance_identity(reports):
                blockers.append("audit report detail routes missing unique redacted routeInstance values")

        route_patterns = audit_inputs_summary.get("routePatterns")
        if isinstance(route_patterns, list):
            for pattern in route_patterns:
                if isinstance(pattern, str) and pattern and pattern not in report_routes:
                    blockers.append(f"audit report missing expected route pattern {pattern}")
        detail_route_instances = audit_inputs_summary.get("detailRouteInstances")
        if isinstance(detail_route_instances, list):
            expected_instances = [
                instance
                for instance in detail_route_instances
                if isinstance(instance, str) and instance.strip()
            ]
            if len(expected_instances) != len(detail_route_instances):
                blockers.append("audit inputs summary detailRouteInstances must contain non-empty strings")
            report_instances = {
                report_route_instance(report, index)
                for index, report in enumerate(reports)
                if report_route_key(report, index) in {"/posts/{slug}", "/products/{slug}"}
            }
            for instance in expected_instances:
                if instance not in report_instances:
                    blockers.append(f"audit report missing expected route instance {instance}")

    if expected_statuses is not None:
        expected_urls = [url for url in expected_statuses if isinstance(url, str) and url.strip()]
        if len(expected_urls) != len(expected_statuses):
            blockers.append("expected statuses must use non-empty URL string keys")
        expected_routes = {route_pattern_from_url(url) for url in expected_urls}
        for route in sorted(expected_routes):
            if route not in report_routes:
                blockers.append(f"audit report missing expected status route {route}")
        if report_count != len(expected_urls):
            blockers.append(f"audit report route count {report_count} != expected statuses count {len(expected_urls)}")
        expected_detail_count = sum(1 for url in expected_urls if route_pattern_from_url(url) in {"/posts/{slug}", "/products/{slug}"})
        report_detail_instances = {
            report_route_instance(report, index)
            for index, report in enumerate(reports)
            if report_route_key(report, index) in {"/posts/{slug}", "/products/{slug}"}
        }
        if expected_detail_count > 1 and len(report_detail_instances) != expected_detail_count:
            blockers.append(
                f"audit report detail route instance count {len(report_detail_instances)} != expected {expected_detail_count}"
            )
        expected_fingerprints = {url_fingerprint(url) for url in expected_urls}
        report_fingerprints = {
            value
            for report in reports
            for value in [report.get("urlFingerprint")]
            if isinstance(value, str) and value.strip()
        }
        if report_fingerprints:
            missing_fingerprints = expected_fingerprints - report_fingerprints
            extra_fingerprints = report_fingerprints - expected_fingerprints
            if missing_fingerprints:
                blockers.append(
                    f"audit report missing {len(missing_fingerprints)} expected concrete URL fingerprints"
                )
            if extra_fingerprints:
                blockers.append(
                    f"audit report has {len(extra_fingerprints)} unexpected concrete URL fingerprints"
                )
        elif any(route_pattern_from_url(url) in {"/posts/{slug}", "/products/{slug}"} for url in expected_urls):
            blockers.append("redacted audit report must include urlFingerprint for concrete detail URL coverage")
    return blockers


def summarize_reports(reports: list[dict[str, Any]], fail_on_warn: bool) -> tuple[list[str], list[str]]:
    proof = {PROOF_HTTP, PROOF_DOM, PROOF_IMAGE}
    blockers: list[str] = []
    for index, report in enumerate(reports):
        label = route_label(report, index)
        status = report.get("status")
        expected = report.get("expectedStatus")
        if not isinstance(expected, int) or isinstance(expected, bool):
            blockers.append(f"{label}: missing expectedStatus")
        if status != expected:
            blockers.append(f"{label}: HTTP status {status} != expected {expected}")

        tag_counts = report.get("tagCounts")
        headings = report.get("headings")
        if not isinstance(tag_counts, dict) or not isinstance(headings, dict):
            blockers.append(f"{label}: missing DOM/rich-text structural report")

        if not isinstance(report.get("imageCount"), int) or isinstance(report.get("imageCount"), bool):
            blockers.append(f"{label}: missing image report")

        issues = report.get("issues", [])
        if not isinstance(issues, list):
            blockers.append(f"{label}: issues must be an array")
            continue
        for issue in issues:
            code = issue_code(issue)
            severity = str(issue.get("severity", "error")) if isinstance(issue, dict) else "error"
            if severity == "warn" and not fail_on_warn:
                continue
            if code in IMAGE_ISSUE_CODES:
                blockers.append(f"{label}: image issue {code}")
            elif code in DOM_ISSUE_CODES:
                blockers.append(f"{label}: DOM/rich-text issue {code}")
            else:
                blockers.append(f"{label}: frontend issue {code}")

    if not blockers:
        proof.add(PROOF_EMPTY_BROKEN)
    return sorted(proof), blockers


def build_result(
    packet: dict[str, Any],
    audit_report: Path,
    evidence_pointers: list[str],
    fail_on_warn: bool,
    audit_inputs_summary: dict[str, Any] | None = None,
    expected_statuses: dict[str, Any] | None = None,
    source_context_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    if packet.get("stageId") != "final_frontend_audit":
        raise ValueError("packet stageId must be final_frontend_audit")
    reports = load_reports(audit_report)
    proof, blockers = summarize_reports(reports, fail_on_warn)
    blockers.extend(validate_expected_coverage(reports, audit_inputs_summary, expected_statuses))
    if blockers and PROOF_EMPTY_BROKEN in proof:
        proof.remove(PROOF_EMPTY_BROKEN)
    status = "completed" if not blockers else "partial"
    if not evidence_pointers:
        evidence_pointers = [str(audit_report)]
    result = build_stage_result(
        "final_frontend_audit",
        status,
        evidence_pointers,
        proof,
        blockers,
        browser_stage_mutated_remote=False,
    )
    result["operatorNote"] = (
        "final frontend audit passed with no blocking issues"
        if status == "completed"
        else "final frontend audit has blocking issues; keep cleanup locked"
    )
    if isinstance(audit_inputs_summary, dict):
        navigation_count = audit_inputs_summary.get("navigationItemCount")
        if isinstance(navigation_count, int) and not isinstance(navigation_count, bool) and navigation_count >= 0:
            result["navigationItemCount"] = navigation_count
    source_context_artifacts = source_context_artifacts or []
    if source_context_artifacts:
        sources = [(f"source context {index + 1}", path) for index, path in enumerate(source_context_artifacts)]
        loaded_sources = [(label, load_json(Path(path))) for label, path in sources]
        coverage, coverage_issues = load_matching_coverage(sources, require_when_any_source=True)
        quality, quality_issues = load_matching_quality_review(sources, require_when_any_source=True)
        wiki_review, wiki_review_issues = load_matching_wiki_review(sources, require_when_any_source=True)
        matrix, matrix_issues = load_matching_confirmation_decision_matrix(sources, require_when_any_source=True)
        submitted_values, submitted_value_issues = load_matching_created_site_submitted_values(
            sources,
            require_when_any_source=False,
        )
        content_counts, content_counts_issues = matching_content_counts(loaded_sources)
        source_context_issues = (
            coverage_issues
            + quality_issues
            + wiki_review_issues
            + matrix_issues
            + submitted_value_issues
            + content_counts_issues
        )
        if source_context_issues:
            raise ValueError("source context validation failed:\n" + "\n".join(f"- {issue}" for issue in source_context_issues))
        result["contentGoalCoverage"] = coverage or {}
        result["contentCounts"] = content_counts or {}
        result["contentQualityReview"] = quality or {}
        result["wikiReview"] = wiki_review or {}
        result["confirmationDecisionMatrix"] = matrix or []
        if submitted_values:
            result["createdSiteSubmittedValues"] = submitted_values
    validation = validate_browser_stage_result(result, packet)
    if not validation["ok"]:
        raise ValueError("stage result validation failed:\n" + "\n".join(f"- {issue}" for issue in validation["issues"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final_frontend_audit stage result from redacted frontend audit JSON.")
    parser.add_argument("--packet-json", required=True)
    parser.add_argument("--audit-report-json", required=True)
    parser.add_argument("--audit-inputs-summary-json", default="", help="Optional summary from make_final_frontend_audit_inputs.py")
    parser.add_argument("--expected-statuses-json", default="", help="Optional expected statuses JSON from make_final_frontend_audit_inputs.py")
    parser.add_argument(
        "--source-context-artifact",
        action="append",
        default=[],
        help="Optional source-context artifact to bind into the final audit result; repeat for package/confirmation/binding.",
    )
    parser.add_argument("--evidence-pointers", default="", help="Comma-separated redacted evidence pointers; defaults to audit report path")
    parser.add_argument("--fail-on-warn", action="store_true", help="Treat warning issues as blockers")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        packet = load_packet(Path(args.packet_json))
        evidence_pointers = [item.strip() for item in args.evidence_pointers.split(",") if item.strip()]
        audit_inputs_summary = None
        if args.audit_inputs_summary_json:
            loaded_summary = load_json(Path(args.audit_inputs_summary_json))
            if not isinstance(loaded_summary, dict):
                raise ValueError("--audit-inputs-summary-json must contain a JSON object")
            audit_inputs_summary = loaded_summary
        expected_statuses = None
        if args.expected_statuses_json:
            loaded_statuses = load_json(Path(args.expected_statuses_json))
            if not isinstance(loaded_statuses, dict):
                raise ValueError("--expected-statuses-json must contain a JSON object")
            expected_statuses = loaded_statuses
        result = build_result(
            packet,
            Path(args.audit_report_json),
            evidence_pointers,
            args.fail_on_warn,
            audit_inputs_summary,
            expected_statuses,
            args.source_context_artifact,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_json(Path(args.output), result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
