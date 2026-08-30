#!/usr/bin/env python3
"""Merge probe request/sample/cleanup proof into AllinCMS run evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from validate_run_evidence import validate
from validate_probe_save_capture_evidence import to_merge_args, validate_capture_evidence
from validate_probe_publish_sample_evidence import (
    to_merge_args as publish_sample_to_merge_args,
)
from validate_probe_publish_sample_evidence import validate_publish_sample_evidence
from validate_probe_cleanup_evidence import to_merge_args as cleanup_to_merge_args
from validate_probe_cleanup_evidence import validate_cleanup_evidence


REQUEST_CAPTURE_FIELDS = (
    "url",
    "method",
    "headers",
    "payloadShape",
    "contentBlockShape",
    "idFields",
    "mode",
    "publishBehavior",
)
SAMPLE_FIELDS = (
    "backendUrl",
    "frontendUrl",
    "status",
    "renderAudit",
)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("evidence root must be an object")
    return data


def require_text(value: str | None, label: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def site_key(data: dict) -> str:
    site_identity = data.get("siteIdentity")
    if not isinstance(site_identity, dict):
        raise ValueError("base evidence must contain siteIdentity")
    value = site_identity.get("siteKey")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("base evidence must contain siteIdentity.siteKey")
    return value.strip()


def content_type(data: dict) -> str:
    content = data.get("contentInspection")
    if not isinstance(content, dict):
        raise ValueError("base evidence must contain contentInspection")
    value = content.get("contentType")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("base evidence must contain contentInspection.contentType")
    return value.strip()


def ensure_backend_url(url: str, current_site_key: str, label: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
        raise ValueError(f"{label} must be an https workspace.laicms.com URL")
    if not parsed.path.startswith(f"/{current_site_key}/"):
        raise ValueError(f"{label} must belong to siteKey {current_site_key}")
    return url


def ensure_frontend_url(url: str, current_site_key: str, label: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != f"{current_site_key}.web.allincms.com":
        raise ValueError(f"{label} must belong to frontend host {current_site_key}.web.allincms.com")
    return url


def base_authorization(data: dict, target: str) -> dict:
    return {
        "userAuthorized": True,
        "authorizedAction": "save probe sample upload evidence after staged authorization",
        "target": target,
        "authorizationSource": "current staged probe authorization recorded outside this merge helper",
        "verificationPlan": "capture request, verify backend persistence, frontend render, and cleanup state",
    }


def append_authorization_history(data: dict, authorization: dict) -> None:
    history = data.get("authorizationHistory")
    if not isinstance(history, list):
        history = []
    key = (
        authorization.get("authorizedAction"),
        authorization.get("target"),
        authorization.get("authorizationSource"),
    )
    for existing in history:
        if not isinstance(existing, dict):
            continue
        existing_key = (
            existing.get("authorizedAction"),
            existing.get("target"),
            existing.get("authorizationSource"),
        )
        if existing_key == key:
            data["authorizationHistory"] = history
            return
    history.append(dict(authorization))
    data["authorizationHistory"] = history


def parse_cleanup_candidates(raw: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for index, item in enumerate(part.strip() for part in raw.split(",") if part.strip()):
        parts = [part.strip() for part in item.split("|", 3)]
        if len(parts) != 4:
            raise ValueError(
                f"cleanup candidate {index} must use contentType|titlePattern|backendUrl|reason"
            )
        candidates.append(
            {
                "contentType": require_text(parts[0], f"cleanup candidate {index} contentType"),
                "titlePattern": require_text(parts[1], f"cleanup candidate {index} titlePattern"),
                "backendUrl": require_text(parts[2], f"cleanup candidate {index} backendUrl"),
                "reason": require_text(parts[3], f"cleanup candidate {index} reason"),
            }
        )
    if not candidates:
        raise ValueError("cleanup candidates are required when merging cleanup proof")
    return candidates


def cleanup_candidates_from_evidence(cleanup_evidence: dict) -> list[dict[str, str]]:
    raw_candidates = cleanup_evidence.get("cleanedCandidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("cleanup evidence cleanedCandidates must be a non-empty list")
    candidates: list[dict[str, str]] = []
    for index, candidate in enumerate(raw_candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"cleanup evidence cleanedCandidates[{index}] must be an object")
        candidates.append(
            {
                "contentType": require_text(candidate.get("contentType"), f"cleanup candidate {index} contentType"),
                "titlePattern": require_text(candidate.get("titlePattern"), f"cleanup candidate {index} titlePattern"),
                "backendUrl": require_text(candidate.get("backendUrl"), f"cleanup candidate {index} backendUrl"),
                "reason": require_text(candidate.get("reason"), f"cleanup candidate {index} reason"),
            }
        )
    return candidates


def merge_request_capture(data: dict, args: argparse.Namespace, current_site_key: str) -> None:
    request_capture = {
        field: require_text(getattr(args, field), f"request {field}")
        for field in REQUEST_CAPTURE_FIELDS
    }
    request_capture["url"] = ensure_backend_url(request_capture["url"], current_site_key, "request url")
    request_capture["method"] = request_capture["method"].upper()
    if request_capture["method"] not in {"POST", "PUT", "PATCH"}:
        raise ValueError("request method must be POST, PUT, or PATCH")
    request_capture["persistedVerified"] = True
    data["requestCapture"] = request_capture
    data["uploadInScope"] = True
    data["mode"] = "mutating_probe"


def merge_sample(data: dict, args: argparse.Namespace, current_site_key: str) -> None:
    sample = {
        field: require_text(getattr(args, field), f"sample {field}")
        for field in SAMPLE_FIELDS
    }
    sample["backendUrl"] = ensure_backend_url(sample["backendUrl"], current_site_key, "sample backendUrl")
    sample["frontendUrl"] = ensure_frontend_url(sample["frontendUrl"], current_site_key, "sample frontendUrl")
    sample["backendVerified"] = True
    sample["frontendVerified"] = True
    sample["titleOrNameVerified"] = True
    sample["coverOrMediaVerified"] = True
    sample["bodyVerified"] = True
    data["sampleVerification"] = sample
    data["uploadInScope"] = True
    data["mode"] = "mutating_probe"


def merge_cleanup(data: dict, args: argparse.Namespace, current_site_key: str) -> None:
    candidates = getattr(args, "cleaned_candidates_structured", None)
    if candidates is None:
        candidates = parse_cleanup_candidates(args.cleaned_candidates)
    for candidate in candidates:
        candidate["backendUrl"] = ensure_backend_url(candidate["backendUrl"], current_site_key, "cleanup backendUrl")
    data["cleanup"] = {
        "status": "completed",
        "cleanedCount": len(candidates),
        "cleanedCandidates": candidates,
        "backendVerified": True,
        "frontendVerified": True,
        "backendEvidence": require_text(args.cleanup_backend_evidence, "cleanup backend evidence"),
        "frontendEvidence": require_text(args.cleanup_frontend_evidence, "cleanup frontend evidence"),
    }
    append_authorization_history(
        data,
        {
            "userAuthorized": True,
            "authorizedAction": "cleanup delete unpublish probe evidence after staged authorization",
            "target": f"https://workspace.laicms.com/{current_site_key}/{content_type(data)}",
            "authorizationSource": "current staged cleanup authorization recorded outside this merge helper",
            "verificationPlan": "delete or unpublish only the probe candidate and verify backend absence plus frontend non-public state",
        },
    )


def merge(data: dict, args: argparse.Namespace) -> dict:
    current_site_key = site_key(data)
    current_content_type = content_type(data)
    merged = dict(data)
    merged["generatedAt"] = datetime.now(timezone.utc).isoformat()

    target = f"https://workspace.laicms.com/{current_site_key}/{current_content_type}"
    stage_authorization = base_authorization(merged, target)
    if not isinstance(merged.get("authorization"), dict):
        merged["authorization"] = stage_authorization
    append_authorization_history(merged, stage_authorization)

    if args.request_capture:
        merge_request_capture(merged, args, current_site_key)
    if args.sample_verification:
        merge_sample(merged, args, current_site_key)
    if args.cleanup_completed:
        merge_cleanup(merged, args, current_site_key)

    errors = validate(merged)
    if errors:
        allowed_prefixes: tuple[str, ...] = ()
        if args.request_capture and not args.sample_verification and not isinstance(merged.get("sampleVerification"), dict):
            allowed_prefixes += ("sampleVerification:",)
        if (args.request_capture or args.sample_verification) and not args.cleanup_completed:
            allowed_prefixes += ("cleanup.candidates:",)
        unexpected = [
            error
            for error in errors
            if not any(error.startswith(prefix) for prefix in allowed_prefixes)
        ]
        if unexpected:
            raise ValueError("merged evidence failed validation: " + "; ".join(unexpected))
    return merged


def merge_from_save_capture_evidence(data: dict, save_capture: dict) -> dict:
    issues = validate_capture_evidence(save_capture, data)
    if issues:
        raise ValueError("save capture evidence failed validation: " + "; ".join(issues))
    merge_values = to_merge_args(save_capture)

    class Args:
        request_capture = True
        sample_verification = False
        cleanup_completed = False
        backendUrl = None
        frontendUrl = None
        status = None
        renderAudit = None
        cleaned_candidates = ""
        cleanup_backend_evidence = ""
        cleanup_frontend_evidence = ""

    for key, value in merge_values.items():
        setattr(Args, key, value)
    return merge(data, Args())


def merge_from_publish_sample_evidence(data: dict, publish_sample: dict) -> dict:
    issues = validate_publish_sample_evidence(publish_sample, data)
    if issues:
        raise ValueError("publish sample evidence failed validation: " + "; ".join(issues))
    merge_values = publish_sample_to_merge_args(publish_sample)

    class Args:
        request_capture = False
        sample_verification = True
        cleanup_completed = False
        url = None
        method = None
        headers = None
        payloadShape = None
        contentBlockShape = None
        idFields = None
        mode = None
        publishBehavior = None
        cleaned_candidates = ""
        cleanup_backend_evidence = ""
        cleanup_frontend_evidence = ""

    for key, value in merge_values.items():
        setattr(Args, key, value)
    return merge(data, Args())


def merge_from_cleanup_evidence(data: dict, cleanup_evidence: dict) -> dict:
    issues = validate_cleanup_evidence(cleanup_evidence, data)
    if issues:
        raise ValueError("cleanup evidence failed validation: " + "; ".join(issues))
    merge_values = cleanup_to_merge_args(cleanup_evidence)
    structured_candidates = cleanup_candidates_from_evidence(cleanup_evidence)

    class Args:
        request_capture = False
        sample_verification = False
        cleanup_completed = True
        url = None
        method = None
        headers = None
        payloadShape = None
        contentBlockShape = None
        idFields = None
        mode = None
        publishBehavior = None
        backendUrl = None
        frontendUrl = None
        status = None
        renderAudit = None
        cleaned_candidates_structured = structured_candidates

    for key, value in merge_values.items():
        setattr(Args, key, value)
    return merge(data, Args())


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge staged probe proof into AllinCMS run evidence.")
    parser.add_argument("--base", required=True, help="Existing run evidence JSON")
    parser.add_argument("--output", required=True)

    parser.add_argument("--request-capture", action="store_true", help="Merge requestCapture proof")
    parser.add_argument("--url")
    parser.add_argument("--method")
    parser.add_argument("--headers")
    parser.add_argument("--payloadShape")
    parser.add_argument("--contentBlockShape")
    parser.add_argument("--idFields")
    parser.add_argument("--mode")
    parser.add_argument("--publishBehavior")

    parser.add_argument("--sample-verification", action="store_true", help="Merge sampleVerification proof")
    parser.add_argument("--backendUrl")
    parser.add_argument("--frontendUrl")
    parser.add_argument("--status")
    parser.add_argument("--renderAudit")

    parser.add_argument("--cleanup-completed", action="store_true", help="Merge completed cleanup proof")
    parser.add_argument(
        "--cleaned-candidates",
        default="",
        help="Comma-separated contentType|titlePattern|backendUrl|reason entries",
    )
    parser.add_argument("--cleanup-backend-evidence", default="")
    parser.add_argument("--cleanup-frontend-evidence", default="")
    parser.add_argument(
        "--save-capture-evidence",
        help="Validated allincms_probe_save_capture_evidence JSON to merge as requestCapture proof",
    )
    parser.add_argument(
        "--publish-sample-evidence",
        help="Validated allincms_probe_publish_sample_evidence JSON to merge as sampleVerification proof",
    )
    parser.add_argument(
        "--cleanup-evidence",
        help="Validated allincms_probe_cleanup_evidence JSON to merge as cleanup proof",
    )
    args = parser.parse_args()

    if args.save_capture_evidence:
        args.request_capture = True
    if args.publish_sample_evidence:
        args.sample_verification = True
    if args.cleanup_evidence:
        args.cleanup_completed = True
    if not any((args.request_capture, args.sample_verification, args.cleanup_completed)):
        print("ERROR: choose at least one merge stage", file=sys.stderr)
        return 2

    try:
        base = load_json(Path(args.base))
        structured_inputs = [
            bool(args.save_capture_evidence),
            bool(args.publish_sample_evidence),
            bool(args.cleanup_evidence),
        ]
        if sum(structured_inputs) > 1:
            raise ValueError("merge save, publish, and cleanup structured evidence in separate steps")
        if args.save_capture_evidence:
            evidence = merge_from_save_capture_evidence(base, load_json(Path(args.save_capture_evidence)))
        elif args.publish_sample_evidence:
            evidence = merge_from_publish_sample_evidence(base, load_json(Path(args.publish_sample_evidence)))
        elif args.cleanup_evidence:
            evidence = merge_from_cleanup_evidence(base, load_json(Path(args.cleanup_evidence)))
        else:
            evidence = merge(base, args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
