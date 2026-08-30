#!/usr/bin/env python3
"""Build a staged browser queue from summarize_run_status nextActionDetails.

Use this when a real run summary already emits the next supported action, but a
full next-browser-action handoff/readiness artifact has not been generated yet.
This is local planning only; it does not authorize or mutate LAICMS.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from make_browser_stage_queue import build_queue, validate_queue


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def select_next_action(summary: dict[str, Any], action: str) -> dict[str, Any]:
    if summary.get("valid") is not True:
        raise ValueError("summary must be valid before queue generation")
    details = summary.get("nextActionDetails")
    if not isinstance(details, list) or not details:
        raise ValueError("summary.nextActionDetails must contain at least one item")
    matches = [item for item in details if isinstance(item, dict) and (not action or item.get("action") == action)]
    if not matches:
        raise ValueError(f"no next action detail found for action: {action}")
    if len(matches) > 1:
        raise ValueError("multiple next action details matched; pass --action")
    detail = matches[0]
    required = ("action", "target", "authorizationText")
    missing = [key for key in required if not isinstance(detail.get(key), str) or not detail[key].strip()]
    if missing:
        raise ValueError("next action detail missing fields: " + ", ".join(missing))
    return detail


def build_readiness_from_summary(summary: dict[str, Any], detail: dict[str, Any], summary_path: str) -> dict[str, Any]:
    target = str(detail["target"])
    action = str(detail["action"])
    if action != "create_product_probe":
        raise ValueError("summary queue bridge currently supports create_product_probe only")
    freshness = summary.get("evidenceFreshness") if isinstance(summary.get("evidenceFreshness"), dict) else {}
    fresh = freshness.get("freshForMutation") is True
    status = "ready_to_request_authorization" if fresh else "blocked_refresh_readonly_evidence"
    blockers = [] if fresh else ["preflight_not_fresh_for_mutation"]
    return {
        "kind": "allincms_next_browser_action_handoff_readiness",
        "generatedAt": now_iso(),
        "remoteMutationsPerformed": False,
        "handoff": "",
        "preflight": "",
        "target": target,
        "action": {
            "authorizationAction": action,
            "source": "summarize_run_status.nextActionDetails",
            "summary": summary_path,
        },
        "stopAfter": "probe draft or dialog state is verified; do not save or publish in the same authorization",
        "preparedOnly": True,
        "isUserAuthorization": False,
        "validation": {
            "ok": True,
            "issues": [],
            "source": "summary_next_action_detail",
        },
        "evidenceFreshness": freshness,
        "status": status,
        "blockers": blockers,
        "nextAction": (
            "ask the user for exact action-time authorization; do not run commands until they provide it"
            if fresh
            else "refresh read-only evidence and rebuild next action details before asking for authorization"
        ),
        "authorizationTextFromSummary": str(detail["authorizationText"]),
    }


def build_queue_from_summary(
    summary: dict[str, Any],
    upload_readiness: dict[str, Any],
    *,
    summary_path: str,
    upload_readiness_path: str,
    action: str = "create_product_probe",
    gap_audit: dict[str, Any] | None = None,
    gap_audit_path: str = "",
    products_manifest: str = "",
    posts_manifest: str = "",
) -> dict[str, Any]:
    detail = select_next_action(summary, action)
    readiness = build_readiness_from_summary(summary, detail, summary_path)
    queue = build_queue(
        readiness,
        upload_readiness,
        readiness_path=summary_path,
        upload_readiness_path=upload_readiness_path,
        gap_audit=gap_audit,
        gap_audit_path=gap_audit_path,
        products_manifest=products_manifest,
        posts_manifest=posts_manifest,
    )
    if queue["queue"] and queue["queue"][0].get("status") == "ready_to_request_authorization":
        authorization_text = str(detail["authorizationText"])
        if "do not save or publish" not in authorization_text:
            authorization_text = authorization_text.rstrip("。") + "；stop condition: do not save or publish in the same authorization。"
        queue["queue"][0]["authorizationText"] = authorization_text
    queue["sourceArtifacts"]["runSummary"] = summary_path
    queue["sourceArtifacts"]["summaryNextActionDetail"] = action
    queue["rule"] += " This queue was bridged from a valid run summary; still require action-time authorization."
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AllinCMS browser stage queue from run summary.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--upload-readiness", required=True)
    parser.add_argument("--gap-audit", default="")
    parser.add_argument("--action", default="create_product_probe")
    parser.add_argument("--products-manifest", default="")
    parser.add_argument("--posts-manifest", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        gap = load_json(Path(args.gap_audit), "gap audit") if args.gap_audit else None
        queue = build_queue_from_summary(
            load_json(Path(args.summary), "run summary"),
            load_json(Path(args.upload_readiness), "upload readiness"),
            summary_path=args.summary,
            upload_readiness_path=args.upload_readiness,
            action=args.action,
            gap_audit=gap,
            gap_audit_path=args.gap_audit,
            products_manifest=args.products_manifest,
            posts_manifest=args.posts_manifest,
        )
        errors = validate_queue(queue)
        if errors:
            raise ValueError("queue validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = [item["id"] for item in queue["queue"] if item["status"] == "ready_to_request_authorization"]
    print(f"Wrote {output}")
    print(f"queueStages={len(queue['queue'])} ready={','.join(ready) if ready else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
