#!/usr/bin/env python3
"""Summarize redacted AllinCMS module scan JSON into interface evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
import sys
from pathlib import Path
from urllib.parse import urlparse
import re


SENSITIVE_MARKERS = (
    "@qq.com",
    "@gmail.com",
    "cookie",
    "authorization",
    "bearer ",
    "next-action",
    "next-router-state-tree",
)
SAFE_SITE_KEY_RE = re.compile(r"^[a-z0-9]{6,16}$")
SAFE_SITE_KEY_PLACEHOLDERS = {"{siteKey}", "{realSiteKey}"}
KNOWN_MUTATION_KEYWORDS = {
    "create": ("create", "创建", "添加", "add", "new"),
    "save": ("save", "保存", "update"),
    "publish": ("publish", "发布", "上线"),
    "enable": ("enable", "启用", "enabled"),
    "delete_or_cleanup": ("delete", "删除", "cleanup", "清理", "unpublish", "取消发布"),
    "upload": ("upload", "上传", "multipart"),
    "bind": ("bind", "绑定", "route"),
}


def module_items_from_object(data: dict[str, object]) -> list[dict]:
    modules = data.get("modules")
    if not isinstance(modules, dict):
        raise ValueError("scan JSON object must contain a modules object")
    items: list[dict] = []
    for module_name, raw_item in modules.items():
        if not isinstance(raw_item, dict):
            continue
        url = raw_item.get("url")
        requests: list[dict] = []
        if isinstance(url, str) and url.strip():
            parsed = urlparse(url)
            path = parsed.path if parsed.scheme else url
            requests.append(
                {
                    "method": "GET",
                    "path": path,
                    "type": "Document",
                    "mime": "text/html",
                }
            )
        raw_network = raw_item.get("network")
        if isinstance(raw_network, dict):
            if raw_network.get("documentGetObserved") is True and isinstance(url, str) and url.strip():
                parsed = urlparse(url)
                path = parsed.path if parsed.scheme else url
                if not any(request.get("path") == path and request.get("type") == "Document" for request in requests):
                    requests.append({"method": "GET", "path": path, "type": "Document", "mime": "text/html"})
            rsc_count = raw_network.get("rscGetCount")
            if isinstance(rsc_count, int) and rsc_count > 0 and isinstance(url, str) and url.strip():
                parsed = urlparse(url)
                path = parsed.path if parsed.scheme else url
                requests.append({"method": "GET", "path": f"{path}?_rsc={{token}}", "type": "Fetch", "mime": "text/x-component"})
            post_samples = raw_network.get("postSamples")
            if isinstance(post_samples, list):
                for sample in post_samples:
                    if not isinstance(sample, dict):
                        continue
                    sample_url = sample.get("url") or url
                    if not isinstance(sample_url, str) or not sample_url.strip():
                        continue
                    parsed = urlparse(sample_url)
                    path = parsed.path if parsed.scheme else sample_url
                    requests.append(
                        {
                            "method": "POST",
                            "path": path,
                            "type": "Fetch",
                            "payloadShape": sample.get("payloadShape", "missing_payload_shape"),
                        }
                    )
        items.append(
            {
                "module": module_name,
                "url": url or "",
                "requests": requests,
                "dom": {
                    "tableHeaders": raw_item.get("tableHeaders", raw_item.get("tableHeads", [])),
                    "inputs": raw_item.get("inputs", []),
                    "buttons": raw_item.get("buttons", []),
                    "headings": raw_item.get("headings", []),
                },
            }
        )
    return items


def load_scan(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if isinstance(data, dict):
        return module_items_from_object(data)
    if not isinstance(data, list):
        raise ValueError("scan JSON must be a list or an object with modules")
    return data


def validate_redaction(scan: list[dict]) -> list[str]:
    errors: list[str] = []
    raw = json.dumps(scan, ensure_ascii=False)
    lowered = raw.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        errors.append("scan contains sensitive or volatile account/header data")
    for item in scan:
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url")
        if isinstance(raw_url, str) and raw_url.startswith("https://workspace.laicms.com/"):
            parsed = urlparse(raw_url)
            parts = [part for part in parsed.path.split("/") if part]
            if not parts:
                continue
            site_key = parts[0]
            if site_key not in SAFE_SITE_KEY_PLACEHOLDERS and not SAFE_SITE_KEY_RE.match(site_key):
                errors.append(f"scan contains unsafe workspace site key in url: {raw_url}")
        raw_requests = item.get("requests")
        if isinstance(raw_requests, list):
            for request in raw_requests:
                if not isinstance(request, dict):
                    continue
                path = request.get("path")
                if not isinstance(path, str):
                    continue
                parsed = urlparse(path)
                path_part = parsed.path if parsed.scheme else path
                parts = [part for part in path_part.split("/") if part]
                if parts and parts[0] not in SAFE_SITE_KEY_PLACEHOLDERS and not SAFE_SITE_KEY_RE.match(parts[0]):
                    errors.append(f"scan contains unsafe site key in request path: {path}")
    return errors


def canonical_path(path: str) -> str:
    parsed = urlparse(path)
    if parsed.scheme and parsed.netloc:
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"
    return path


def classify_request(request: dict) -> tuple[str, str]:
    method = request.get("method")
    path = request.get("path")
    req_type = request.get("type")
    mime = request.get("mime")
    if not isinstance(path, str):
        return ("unknown", "")
    path = canonical_path(path)
    if method == "GET" and req_type == "Document":
        return ("document", path)
    if method == "GET" and req_type == "Fetch" and (mime in {None, "text/x-component"} or "_rsc=" in path):
        return ("rsc_fetch", path)
    if method == "POST":
        return ("post", path)
    if method in {"PUT", "PATCH", "DELETE"}:
        return ("mutation_method", path)
    return ("other", path)


def infer_actions(module: str, post_paths: list[str], buttons: list[object], inputs: list[object]) -> list[dict]:
    text = " ".join(str(value) for value in [module, *post_paths, *buttons, *inputs]).lower()
    actions: list[dict] = []
    for action, terms in KNOWN_MUTATION_KEYWORDS.items():
        if any(term.lower() in text for term in terms):
            actions.append(
                {
                    "action": action,
                    "status": "captured_post_requires_review" if post_paths else "visible_control_only",
                    "jsonSuitability": "conditional" if post_paths else "unknown",
                    "requiredProof": [
                        "action-specific user authorization",
                        "fresh request capture for this exact module/action",
                        "redacted payload shape and required id fields",
                        "backend state verification",
                        "frontend render verification when public",
                    ],
                }
            )
    return actions


def payload_shape_summary(requests: list[dict]) -> dict[str, int]:
    shapes: Counter[str] = Counter()
    for request in requests:
        if not isinstance(request, dict) or request.get("method") != "POST":
            continue
        shape = request.get("payloadShape") or request.get("bodyShape") or request.get("payload")
        if isinstance(shape, str) and shape.strip():
            shapes[shape.strip()] += 1
        elif "payloadKeys" in request:
            shapes["payloadKeys:" + ",".join(str(key) for key in request.get("payloadKeys", []))] += 1
        else:
            shapes["missing_payload_shape"] += 1
    return dict(shapes)


def summarize(scan: list[dict]) -> dict:
    modules: list[dict] = []
    for item in scan:
        if not isinstance(item, dict):
            continue
        requests = item.get("requests") if isinstance(item.get("requests"), list) else []
        document_paths: list[str] = []
        rsc_prefetch_paths: list[str] = []
        post_paths: list[str] = []
        for request in requests:
            if not isinstance(request, dict):
                continue
            kind, path = classify_request(request)
            if not path:
                continue
            if kind == "document":
                document_paths.append(path)
            elif kind == "rsc_fetch":
                rsc_prefetch_paths.append(path)
            elif kind in {"post", "mutation_method"}:
                post_paths.append(path)
        dom = item.get("dom") if isinstance(item.get("dom"), dict) else {}
        buttons = dom.get("buttons", [])
        inputs = dom.get("inputs", [])
        inferred_actions = infer_actions(str(item.get("module", "")), post_paths, buttons, inputs)
        if post_paths:
            json_suitability = "captured_post_requires_review"
        elif rsc_prefetch_paths and not post_paths:
            json_suitability = "read_only_prefetch_only"
        else:
            json_suitability = "read_only_only"
        modules.append(
            {
                "module": item.get("module", ""),
                "url": item.get("url", ""),
                "documentPaths": sorted(set(document_paths)),
                "rscFetchPaths": sorted(set(rsc_prefetch_paths)),
                "postPaths": sorted(set(post_paths)),
                "payloadShapes": payload_shape_summary(requests),
                "tableHeaders": dom.get("tableHeaders", []),
                "inputs": inputs,
                "buttons": buttons[:12] if isinstance(buttons, list) else [],
                "inferredActions": inferred_actions,
                "jsonSuitability": json_suitability,
                "jsonAccelerationRule": (
                    "Do not replay until each inferred action has authorization, payload shape, id fields, "
                    "and backend/frontend persistence proof."
                    if post_paths
                    else "No mutation request captured; use UI or capture the exact action first."
                ),
            }
        )
    blocked_replay_actions: list[dict] = []
    capture_next_actions: list[dict] = []
    for module in modules:
        module_name = module.get("module", "")
        for action in module.get("inferredActions", []):
            if not isinstance(action, dict):
                continue
            entry = {
                "module": module_name,
                "action": action.get("action", ""),
                "status": action.get("status", ""),
                "requiredProof": action.get("requiredProof", []),
            }
            if action.get("status") == "visible_control_only":
                capture_next_actions.append(entry)
            blocked_replay_actions.append(entry)
    return {
        "kind": "allincms_module_scan_summary",
        "redacted": True,
        "warning": "GET _rsc fetches can be sibling-route prefetches. POST presence still requires action-specific payload review and persistence proof before JSON replay.",
        "jsonReplayReady": False,
        "jsonReplayRule": (
            "JSON/Server Action replay is ready only when an action-specific POST has redacted payload shape, "
            "current id fields, explicit authorization, backend persistence proof, and frontend proof when public."
        ),
        "blockedReplayActions": blocked_replay_actions,
        "captureNextActions": capture_next_actions,
        "modules": modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize redacted AllinCMS read-only module scan JSON.")
    parser.add_argument("scan_json")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        scan = load_scan(Path(args.scan_json))
        errors = validate_redaction(scan)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        summary = summarize(scan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
