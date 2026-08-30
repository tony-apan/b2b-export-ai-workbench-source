#!/usr/bin/env python3
"""Run a local-only staged AllinCMS content probe lifecycle simulation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from check_pre_mutation_gate import (
    validate_cleanup_probe_gate,
    validate_probe_gate,
    validate_publish_probe_gate,
    validate_save_probe_gate,
)
from check_round_closeout import validate_closeout
from make_authorization_record import build_record, validate_record as validate_authorization_record
from merge_probe_evidence import merge as merge_probe_evidence
from summarize_run_status import summarize as summarize_run_status
from validate_run_evidence import validate as validate_run_evidence


CONTENT_META = {
    "products": {
        "createAction": "create_product_probe",
        "module": "products",
        "targetType": "products",
        "zh": "产品",
        "english": "product",
        "createFields": "name,slug,description,content,media",
    },
    "posts": {
        "createAction": "create_post_probe",
        "module": "posts",
        "targetType": "posts",
        "zh": "文章",
        "english": "post",
        "createFields": "title,slug,excerpt,content,coverImage",
    },
    "forms": {
        "createAction": "create_form_probe",
        "module": "forms",
        "targetType": "forms",
        "zh": "表单",
        "english": "form",
        "createFields": "name,slug,description,fields",
    },
}


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raise_if_errors(label: str, errors: list[str]) -> None:
    if errors:
        raise ValueError(f"{label} failed:\n" + "\n".join(f"- {error}" for error in errors))


def site_key(data: dict) -> str:
    value = data.get("siteIdentity", {}).get("siteKey") if isinstance(data.get("siteIdentity"), dict) else ""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("base evidence must contain siteIdentity.siteKey")
    return value.strip()


def content_type(data: dict) -> str:
    value = data.get("contentInspection", {}).get("contentType") if isinstance(data.get("contentInspection"), dict) else ""
    if value not in CONTENT_META:
        raise ValueError(f"base evidence content type must be one of {sorted(CONTENT_META)}")
    return value


def module_url(site: str, module: str) -> str:
    return f"https://workspace.laicms.com/{site}/{module}"


def edit_url(site: str, module: str, content_id: str) -> str:
    return f"{module_url(site, module)}/{content_id}/update"


def frontend_url(site: str, module: str, slug: str) -> str:
    return f"https://{site}.web.allincms.com/{module}/{slug}"


def build_authorization(
    *,
    action: str,
    site: str,
    target: str,
    target_type: str,
    target_identifier: str,
    fields_or_files: str,
    expected_result: str,
    verification_plan: str,
    cleanup_plan: str,
    authorization_source: str,
    generated_at: str,
) -> dict:
    record = build_record(
        SimpleNamespace(
            action=action,
            site_key=site,
            target=target,
            target_type=target_type,
            target_identifier=target_identifier,
            fields_or_files=fields_or_files,
            expected_result=expected_result,
            verification_plan=verification_plan,
            cleanup_plan=cleanup_plan,
            authorization_source=authorization_source,
        )
    )
    record["generatedAt"] = generated_at
    raise_if_errors(f"{action} authorization validation", validate_authorization_record(record))
    return record


def merge_request_capture(base: dict, request_url: str) -> dict:
    return merge_probe_evidence(
        base,
        SimpleNamespace(
            request_capture=True,
            url=request_url,
            method="POST",
            headers="Accept, Content-Type, next-action",
            payloadShape="redacted server action payload",
            contentBlockShape="structured rich text blocks",
            idFields="siteId, contentId",
            mode="update",
            publishBehavior="publish separate",
            sample_verification=False,
            backendUrl=None,
            frontendUrl=None,
            status=None,
            renderAudit=None,
            cleanup_completed=False,
            cleaned_candidates="",
            cleanup_backend_evidence="",
            cleanup_frontend_evidence="",
        ),
    )


def merge_sample(base: dict, backend_url: str, public_url: str) -> dict:
    return merge_probe_evidence(
        base,
        SimpleNamespace(
            request_capture=False,
            url=None,
            method=None,
            headers=None,
            payloadShape=None,
            contentBlockShape=None,
            idFields=None,
            mode=None,
            publishBehavior=None,
            sample_verification=True,
            backendUrl=backend_url,
            frontendUrl=public_url,
            status="published",
            renderAudit="simulated frontend detail check: status 200, structured rich text, media, and no Markdown residue verified",
            cleanup_completed=False,
            cleaned_candidates="",
            cleanup_backend_evidence="",
            cleanup_frontend_evidence="",
        ),
    )


def merge_cleanup(base: dict, content_type_value: str, backend_url: str) -> dict:
    return merge_probe_evidence(
        base,
        SimpleNamespace(
            request_capture=False,
            url=None,
            method=None,
            headers=None,
            payloadShape=None,
            contentBlockShape=None,
            idFields=None,
            mode=None,
            publishBehavior=None,
            sample_verification=False,
            backendUrl=None,
            frontendUrl=None,
            status=None,
            renderAudit=None,
            cleanup_completed=True,
            cleaned_candidates=f"{content_type_value}|Codex Probe - Delete Me|{backend_url}|simulated probe cleanup",
            cleanup_backend_evidence="simulated backend list no longer shows Codex Probe - Delete Me",
            cleanup_frontend_evidence="simulated frontend probe detail returns 404 after cleanup",
        ),
    )


def mark_local_simulation(data: dict) -> dict:
    data["localOnly"] = True
    data["simulationOnly"] = True
    data["remoteMutationsPerformed"] = False
    return data


def run_simulation(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = Path(args.output_dir)
    base = load_json(Path(args.base))
    raise_if_errors("base evidence validation", validate_run_evidence(base))

    current_site = site_key(base)
    current_type = content_type(base)
    meta = CONTENT_META[current_type]
    module = meta["module"]
    target_type = meta["targetType"]
    content_id = args.simulated_content_id
    slug = args.simulated_slug
    list_url = module_url(current_site, module)
    probe_edit_url = edit_url(current_site, module, content_id)
    public_url = frontend_url(current_site, module, slug)
    target_identifier = f"Codex Probe - Delete Me {meta['english']} draft"

    create_generated_at = datetime.now(timezone.utc).isoformat()
    create_auth = build_authorization(
        action=meta["createAction"],
        site=current_site,
        target=list_url,
        target_type=target_type,
        target_identifier=target_identifier,
        fields_or_files=meta["createFields"],
        expected_result="temporary probe draft opens for request capture",
        verification_plan="verify backend probe draft before any save or publish",
        cleanup_plan="no automatic cleanup; request separate cleanup authorization",
        authorization_source=(
            f"current user explicitly authorizes create {meta['zh']} product probe draft at {list_url}"
            if current_type == "products"
            else f"current user explicitly authorizes create {meta['english']} probe draft at {list_url}"
        ),
        generated_at=create_generated_at,
    )
    raise_if_errors(
        "create probe gate",
        validate_probe_gate(base, create_auth, str(meta["createAction"]), max_age_minutes=args.max_age_minutes),
    )
    probe_created = mark_local_simulation(dict(base))
    probe_created["mode"] = "mutating_probe"
    probe_created["generatedAt"] = datetime.now(timezone.utc).isoformat()
    probe_created["authorization"] = {
        "userAuthorized": True,
        "authorizedAction": meta["createAction"],
        "target": list_url,
        "authorizationSource": create_auth["authorization"]["authorizationSource"],
        "verificationPlan": "simulated probe draft creation verified locally",
    }
    raise_if_errors("probe-created evidence validation", validate_run_evidence(probe_created))

    save_generated_at = datetime.now(timezone.utc).isoformat()
    save_auth = build_authorization(
        action="save_probe",
        site=current_site,
        target=probe_edit_url,
        target_type=target_type,
        target_identifier=target_identifier,
        fields_or_files="requestCapture,payloadShape,persistedVerified",
        expected_result="probe save request captured and backend persistence verified",
        verification_plan="save probe, capture request, and verify backend persistence",
        cleanup_plan="no automatic cleanup; request separate cleanup authorization",
        authorization_source=f"current user explicitly authorizes save {meta['zh']} probe draft and capture request at {probe_edit_url}",
        generated_at=save_generated_at,
    )
    raise_if_errors("save probe gate", validate_save_probe_gate(probe_created, save_auth, args.max_age_minutes))
    request_captured = mark_local_simulation(merge_request_capture(probe_created, probe_edit_url))

    publish_generated_at = datetime.now(timezone.utc).isoformat()
    publish_auth = build_authorization(
        action="publish_probe",
        site=current_site,
        target=probe_edit_url,
        target_type=target_type,
        target_identifier=target_identifier,
        fields_or_files="publishStatus,frontendVerified",
        expected_result="probe published and frontend detail verified",
        verification_plan="publish probe, verify backend status and frontend detail",
        cleanup_plan="request separate cleanup authorization after verification",
        authorization_source=f"current user explicitly authorizes publish {meta['zh']} probe draft at {probe_edit_url}",
        generated_at=publish_generated_at,
    )
    raise_if_errors("publish probe gate", validate_publish_probe_gate(request_captured, publish_auth, args.max_age_minutes))
    sample_verified = mark_local_simulation(merge_sample(request_captured, probe_edit_url, public_url))

    cleanup_generated_at = datetime.now(timezone.utc).isoformat()
    cleanup_auth = build_authorization(
        action="cleanup_probe",
        site=current_site,
        target=probe_edit_url,
        target_type=target_type,
        target_identifier=target_identifier,
        fields_or_files="cleanedCandidates,backendVerified,frontendVerified",
        expected_result="probe cleaned and frontend no longer renders probe",
        verification_plan="delete or unpublish probe, verify backend absence and frontend 404",
        cleanup_plan="cleanup is the requested action",
        authorization_source=f"current user explicitly authorizes cleanup {meta['zh']} probe draft at {probe_edit_url}",
        generated_at=cleanup_generated_at,
    )
    raise_if_errors("cleanup probe gate", validate_cleanup_probe_gate(sample_verified, cleanup_auth, args.max_age_minutes))
    cleanup_completed = mark_local_simulation(merge_cleanup(sample_verified, current_type, probe_edit_url))
    cleanup_completed["completionClaimed"] = False
    raise_if_errors("cleanup-completed evidence validation", validate_run_evidence(cleanup_completed))

    paths = {
        "createAuthorization": output_dir / "01-create-probe-authorization.json",
        "probeCreated": output_dir / "02-probe-created-evidence.json",
        "saveAuthorization": output_dir / "03-save-probe-authorization.json",
        "requestCaptured": output_dir / "04-request-captured-evidence.json",
        "publishAuthorization": output_dir / "05-publish-probe-authorization.json",
        "sampleVerified": output_dir / "06-sample-verified-evidence.json",
        "cleanupAuthorization": output_dir / "07-cleanup-probe-authorization.json",
        "cleanupCompleted": output_dir / "08-cleanup-completed-evidence.json",
        "summary": output_dir / "run-summary.json",
        "closeout": output_dir / "round-closeout.json",
    }
    summary = summarize_run_status(
        cleanup_completed,
        str(paths["cleanupCompleted"]),
        require_created_site=args.require_created_site,
    )
    round_issues = getattr(
        args,
        "round_issue",
        ["Checked local probe lifecycle simulation and found no reusable skill update needed."],
    )
    closeout = validate_closeout(
        summary,
        args.sedimentation,
        args.closeout_note,
        [item.strip() for item in args.changed_files.split(",") if item.strip()],
        Path(__file__).resolve().parents[1],
        round_issues,
    )
    if not closeout["ok"]:
        raise_if_errors("round closeout", closeout["issues"])

    for key, data in (
        ("createAuthorization", create_auth),
        ("probeCreated", probe_created),
        ("saveAuthorization", save_auth),
        ("requestCaptured", request_captured),
        ("publishAuthorization", publish_auth),
        ("sampleVerified", sample_verified),
        ("cleanupAuthorization", cleanup_auth),
        ("cleanupCompleted", cleanup_completed),
        ("summary", summary),
        ("closeout", closeout),
    ):
        write_json(paths[key], data)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate staged AllinCMS probe lifecycle locally.")
    parser.add_argument("--base", required=True, help="Created/read-only run evidence JSON")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--simulated-content-id", default="codex-probe-id")
    parser.add_argument("--simulated-slug", default="codex-probe-delete-me")
    parser.add_argument("--require-created-site", action="store_true")
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument("--sedimentation", choices=["updated", "none"], default="none")
    parser.add_argument("--closeout-note", default="no reusable skill update needed after checking")
    parser.add_argument("--changed-files", default="")
    parser.add_argument(
        "--round-issue",
        action="append",
        default=["Checked local probe lifecycle simulation and found no reusable skill update needed."],
    )
    args = parser.parse_args()

    try:
        paths = run_simulation(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for label, path in paths.items():
        print(f"{label}: {path}")
    print("Local probe lifecycle simulation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
