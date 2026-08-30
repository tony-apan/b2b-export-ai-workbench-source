#!/usr/bin/env python3
"""Upload local source images through a PicGo local server and rewrite content links.

This helper takes a distilled `allincms_source_wiki` (or an explicit image list),
uploads the referenced LOCAL image files through PicGo's local HTTP server
(default POST http://127.0.0.1:36677/upload), and rewrites every occurrence of
each local path across the wiki (root `media[]`, per-item `mediaNeeds`, and body
`content`/`sections` text, including Markdown `![alt](path)` refs) to the hosted
online URL PicGo returns. It emits:

  - an `allincms_media_upload_map` evidence artifact (local path -> hosted URL, sha256),
  - optionally a rewritten wiki JSON with local links replaced by hosted URLs.

Safety model:
  - This is NOT an AllinCMS mutation; `allincmsRemoteMutationsPerformed` is always false.
  - It DOES perform a real external upload (images become publicly reachable URLs),
    so a real upload requires the explicit `--confirm-upload` flag. The default is a
    local `--dry-run` plan that uploads nothing and rewrites nothing.
  - The source wiki `mediaPolicy` sets `requiresUserApprovalBeforeUpload=True`; run
    the real upload only after the user has approved the media in content confirmation.
  - Never store image bytes, credentials, PicGo config, or tokens in the skill package.
    Write all artifacts outside the skill package.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable
import socket
import urllib.request
from urllib.parse import urlparse

DEFAULT_ENDPOINT = "http://127.0.0.1:36677/upload"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif", ".tiff"}
UPLOAD_MAP_KIND = "allincms_media_upload_map"
CREDENTIAL_PATTERN = re.compile(r"\b(?:cookie|bearer|authorization|token|api[_-]?key|password|secret)\b", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output must be outside the skill package")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: {label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def looks_like_local_image(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    if text.startswith(("http://", "https://", "//", "data:")):
        return False
    if Path(text).suffix.lower() not in IMAGE_SUFFIXES:
        return False
    # A bare filename (e.g. a media item's "name" field) is not a path reference.
    # Treat it as a local image only if it carries a path separator or actually exists.
    return ("/" in text) or ("\\" in text) or Path(text).expanduser().exists()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_local_image_paths(wiki: dict[str, Any], extra_images: list[str]) -> list[str]:
    """Find every distinct local image path referenced by the wiki plus explicit images.

    Order is deterministic (first-seen order) so the uploaded URL list maps back
    positionally and the resulting map is stable across runs.
    """
    seen: dict[str, None] = {}

    def visit(node: Any) -> None:
        if isinstance(node, str):
            if looks_like_local_image(node):
                seen.setdefault(node.strip(), None)
            else:
                # Also catch Markdown image refs embedded in longer body text.
                for match in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", node):
                    if looks_like_local_image(match):
                        seen.setdefault(match.strip(), None)
        elif isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            for value in node.values():
                visit(value)

    # site/siteInfo carry logo and hero image refs; media/pages/products/posts carry the rest.
    visit(wiki.get("site"))
    visit(wiki.get("siteInfo"))
    visit(wiki.get("media"))
    visit(wiki.get("pages"))
    visit(wiki.get("products"))
    visit(wiki.get("posts"))
    for image in extra_images:
        if isinstance(image, str) and image.strip():
            seen.setdefault(image.strip(), None)
    return list(seen.keys())


def probe_picgo(endpoint: str, timeout: float = 3.0) -> tuple[bool, str]:
    """Fast TCP probe of the PicGo local server, so a missing/stopped PicGo fails in seconds
    with actionable guidance instead of a 60s urlopen hang / raw traceback."""
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 36677
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"PicGo server reachable at {host}:{port}"
    except OSError as exc:
        return False, f"PicGo server not reachable at {host}:{port} ({exc.__class__.__name__})"


def picgo_setup_guidance(endpoint: str) -> str:
    """Cross-platform two-paths guidance shown when PicGo is not reachable."""
    return (
        f"PicGo local server is not reachable at {endpoint}.\n"
        "Local images in your content can't be auto-uploaded until it's running. Two ways forward:\n\n"
        "A) Set up PicGo (best when you have many images to batch-upload):\n"
        "   1. Install — macOS: `brew install --cask picgo` (or download from https://molunerfinn.com/PicGo/).\n"
        "      Windows: `winget install Molunerfinn.PicGo` (or download from https://molunerfinn.com/PicGo/).\n"
        "   2. Open PicGo -> Settings -> turn ON the Server (default port 36677).\n"
        "   3. Configure an image host in PicGo (Aliyun OSS / Tencent COS / GitHub / SM.MS ...) so uploads return a public URL.\n"
        "   4. Re-run this command (it probes the server first).\n\n"
        "B) Skip PicGo, use the AllinCMS backend Media module (best for just a few images):\n"
        "   Upload images by hand in the site's Media module (the UI-only media path), then reference the\n"
        "   returned hosted URLs in your content. No PicGo needed.\n"
    )


def picgo_upload(paths: list[str], endpoint: str) -> list[str]:
    """POST absolute image paths to a PicGo local server and return hosted URLs.

    PicGo server contract: POST {"list": [abs_path, ...]} -> {"success": true, "result": [url, ...]}.
    """
    payload = json.dumps({"list": [str(Path(p).expanduser().resolve()) for p in paths]}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - localhost PicGo server
        body = response.read().decode("utf-8")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: PicGo response was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or parsed.get("success") is not True:
        raise SystemExit(f"ERROR: PicGo upload did not succeed: {body[:400]}")
    result = parsed.get("result")
    if not isinstance(result, list) or len(result) != len(paths) or not all(isinstance(u, str) and u.startswith(("http://", "https://")) for u in result):
        raise SystemExit("ERROR: PicGo result must be a URL list matching the uploaded image count")
    return result


def rewrite_links(node: Any, path_to_url: dict[str, str]) -> Any:
    """Deep-copy a structure replacing every local image path with its hosted URL.

    Handles bare path values, Markdown image refs `![alt](path)`, and marks media
    dicts (`{"path": <local>}`) with `hostedUrl`/`uploaded` while preserving the
    original path under `localSourcePath` for audit.
    """
    if isinstance(node, str):
        text = node
        for local, url in path_to_url.items():
            if local in text:
                text = text.replace(local, url)
        return text
    if isinstance(node, list):
        return [rewrite_links(item, path_to_url) for item in node]
    if isinstance(node, dict):
        result: dict[str, Any] = {}
        for key, value in node.items():
            result[key] = rewrite_links(value, path_to_url)
        original_path = node.get("path")
        if isinstance(original_path, str) and original_path.strip() in path_to_url:
            local = original_path.strip()
            result["localSourcePath"] = local
            result["hostedUrl"] = path_to_url[local]
            result["uploaded"] = True
        return result
    return node


def build_upload_map(
    wiki: dict[str, Any],
    *,
    local_paths: list[str],
    hosted_urls: list[str],
    endpoint: str,
    dry_run: bool,
    wiki_path: str,
) -> dict[str, Any]:
    images: list[dict[str, Any]] = []
    for index, local in enumerate(local_paths):
        resolved = Path(local).expanduser()
        exists = resolved.exists()
        entry: dict[str, Any] = {
            "localPath": local,
            "name": resolved.name,
            "exists": exists,
            "sha256": sha256_file(resolved) if exists else "",
            "hostedUrl": hosted_urls[index] if index < len(hosted_urls) else "",
            "uploaded": not dry_run and index < len(hosted_urls),
        }
        images.append(entry)
    return {
        "kind": UPLOAD_MAP_KIND,
        "generatedAt": now_iso(),
        "sourceWiki": wiki_path,
        "endpoint": endpoint,
        "dryRun": dry_run,
        "imageHostUploadPerformed": not dry_run and bool(hosted_urls),
        "imageHostIsExternal": True,
        "allincmsRemoteMutationsPerformed": False,
        "imageCount": len(local_paths),
        "images": images,
        "notes": (
            "Dry-run plan only: no image was uploaded and no link was rewritten."
            if dry_run
            else "Images were uploaded to an external host via PicGo and are now publicly reachable."
        ),
        "adversarialChecks": [
            "This step does not create/select/save/publish/upload anything in AllinCMS.",
            "Real upload requires --confirm-upload and prior media approval in content confirmation.",
            "Hosted URLs are public; do not upload images the user has not approved for publication.",
            "Do not store image bytes, PicGo config, tokens, or credentials in the skill package.",
        ],
    }


def validate_upload_map(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if data.get("kind") != UPLOAD_MAP_KIND:
        issues.append(f"kind must be {UPLOAD_MAP_KIND}")
    if data.get("allincmsRemoteMutationsPerformed") is not False:
        issues.append("allincmsRemoteMutationsPerformed must be false")
    if data.get("imageHostIsExternal") is not True:
        issues.append("imageHostIsExternal must be true")
    dry_run = data.get("dryRun")
    if not isinstance(dry_run, bool):
        issues.append("dryRun must be boolean")
    images = data.get("images")
    if not isinstance(images, list):
        issues.append("images must be an array")
        images = []
    for index, image in enumerate(images):
        if not isinstance(image, dict):
            issues.append(f"images[{index}] must be an object")
            continue
        if not isinstance(image.get("localPath"), str) or not image["localPath"].strip():
            issues.append(f"images[{index}].localPath is required")
        hosted = image.get("hostedUrl")
        if dry_run is False:
            if not isinstance(hosted, str) or not hosted.startswith(("http://", "https://")):
                issues.append(f"images[{index}].hostedUrl must be an http(s) URL after a real upload")
            if image.get("uploaded") is not True:
                issues.append(f"images[{index}].uploaded must be true after a real upload")
            if not isinstance(image.get("sha256"), str) or len(image.get("sha256", "")) != 64:
                issues.append(f"images[{index}].sha256 must be a 64-char digest of the uploaded file")
    blob = json.dumps(data, ensure_ascii=False)
    if CREDENTIAL_PATTERN.search(blob):
        issues.append("upload map must not contain credential/token/cookie material")
    return issues


def build(
    args: argparse.Namespace,
    *,
    uploader: Callable[[list[str], str], list[str]] = picgo_upload,
    prober: Callable[[str], tuple[bool, str]] = probe_picgo,
) -> dict[str, Any]:
    wiki = load_json(args.wiki, "source wiki") if args.wiki else {}
    extra_images = list(getattr(args, "image", []) or [])
    local_paths = collect_local_image_paths(wiki, extra_images)

    missing = [p for p in local_paths if not Path(p).expanduser().exists()]
    if missing and not args.dry_run:
        raise SystemExit("ERROR: cannot upload missing local images:\n- " + "\n- ".join(missing))

    hosted_urls: list[str] = []
    if not args.dry_run and local_paths:
        if not args.confirm_upload:
            raise SystemExit(
                "ERROR: a real PicGo upload requires --confirm-upload; default is --dry-run. "
                "Run only after the user approved the media in content confirmation."
            )
        reachable, detail = prober(args.endpoint)
        if not reachable:
            raise SystemExit(picgo_setup_guidance(args.endpoint) + f"\n[{detail}]")
        hosted_urls = uploader(local_paths, args.endpoint)

    upload_map = build_upload_map(
        wiki,
        local_paths=local_paths,
        hosted_urls=hosted_urls,
        endpoint=args.endpoint,
        dry_run=args.dry_run or not local_paths,
        wiki_path=args.wiki or "",
    )
    issues = validate_upload_map(upload_map)
    if issues:
        raise SystemExit("ERROR: invalid media upload map:\n- " + "\n- ".join(issues))

    output = Path(args.output).expanduser()
    ensure_output_outside_skill(output)
    write_json(output, upload_map)

    rewritten_wiki: dict[str, Any] | None = None
    if args.rewrite_wiki_output and hosted_urls and wiki:
        path_to_url = {img["localPath"]: img["hostedUrl"] for img in upload_map["images"] if img.get("hostedUrl")}
        rewritten_wiki = rewrite_links(wiki, path_to_url)
        rewrite_output = Path(args.rewrite_wiki_output).expanduser()
        ensure_output_outside_skill(rewrite_output)
        write_json(rewrite_output, rewritten_wiki)

    return {
        "uploadMap": str(output),
        "rewrittenWiki": str(Path(args.rewrite_wiki_output).expanduser()) if rewritten_wiki is not None else "",
        "imageCount": upload_map["imageCount"],
        "dryRun": upload_map["dryRun"],
        "imageHostUploadPerformed": upload_map["imageHostUploadPerformed"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload local source images via PicGo and rewrite content links.")
    parser.add_argument("--wiki", default="", help="allincms_source_wiki JSON to scan and (optionally) rewrite")
    parser.add_argument("--image", action="append", default=[], help="Extra local image path to upload; repeatable")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="PicGo local server upload endpoint")
    parser.add_argument("--output", default="", help="Where to write the media upload map JSON (outside the skill); required unless --check")
    parser.add_argument("--rewrite-wiki-output", default="", help="Optional path for the rewritten wiki (real upload only)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only: upload nothing, rewrite nothing (default behavior when set)")
    parser.add_argument("--confirm-upload", action="store_true", help="Required to perform a real external upload")
    parser.add_argument("--check", action="store_true", help="Only probe the PicGo server and print setup guidance; upload nothing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.check:
        reachable, detail = probe_picgo(args.endpoint)
        print(detail)
        if not reachable:
            print()
            print(picgo_setup_guidance(args.endpoint))
        return 0 if reachable else 1

    if not args.wiki and not args.image:
        raise SystemExit("ERROR: provide --wiki and/or at least one --image")
    if not args.output:
        raise SystemExit("ERROR: --output is required (unless --check)")

    result = build(args)
    print(f"Wrote media upload map: {result['uploadMap']}")
    print(
        f"imageCount={result['imageCount']} dryRun={str(result['dryRun']).lower()} "
        f"imageHostUploadPerformed={str(result['imageHostUploadPerformed']).lower()}"
    )
    if result["rewrittenWiki"]:
        print(f"Wrote rewritten wiki: {result['rewrittenWiki']}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
