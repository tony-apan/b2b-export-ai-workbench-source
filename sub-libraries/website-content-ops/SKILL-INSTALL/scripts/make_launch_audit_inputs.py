#!/usr/bin/env python3
"""Generate URL and expected-status input files for an AllinCMS launch audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse


def parse_paths(raw: str, label: str) -> list[str]:
    paths = [item.strip() for item in raw.split(",") if item.strip()]
    if not paths:
        raise ValueError(f"{label} must contain at least one path")
    for path in paths:
        if not path.startswith("/"):
            raise ValueError(f"{label} path must start with /: {path}")
        if " " in path:
            raise ValueError(f"{label} path must not contain spaces: {path}")
    return paths


def normalize_base_url(raw: str) -> str:
    raw = raw.strip()
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("frontend base URL must be an https URL")
    return raw.rstrip("/") + "/"


def build_url(base_url: str, path: str) -> str:
    return urljoin(base_url, path.lstrip("/"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate launch audit URL and expected-status files.")
    parser.add_argument("--frontend-base-url", required=True, help="Frontend origin, for example https://example.web.allincms.com")
    parser.add_argument("--static-paths", required=True, help="Comma-separated paths expected to return 200")
    parser.add_argument("--detail-probe-paths", default="", help="Comma-separated redacted/probe paths expected to return 404")
    parser.add_argument("--urls-output", required=True, help="Output text file containing one URL per line")
    parser.add_argument("--statuses-output", required=True, help="Output JSON file mapping URL to expected HTTP status")
    args = parser.parse_args()

    try:
        base_url = normalize_base_url(args.frontend_base_url)
        static_paths = parse_paths(args.static_paths, "static paths")
        detail_paths = parse_paths(args.detail_probe_paths, "detail probe paths") if args.detail_probe_paths else []
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    statuses: dict[str, int] = {}
    for path in static_paths:
        statuses[build_url(base_url, path)] = 200
    for path in detail_paths:
        statuses[build_url(base_url, path)] = 404

    urls_output = Path(args.urls_output)
    statuses_output = Path(args.statuses_output)
    urls_output.write_text("\n".join(statuses.keys()) + "\n", encoding="utf-8")
    statuses_output.write_text(json.dumps(statuses, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {urls_output}")
    print(f"Wrote {statuses_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
