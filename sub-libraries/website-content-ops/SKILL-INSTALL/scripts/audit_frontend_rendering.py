#!/usr/bin/env python3
"""Audit published AllinCMS frontend pages for rendering regressions."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import re
import signal
import sys
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MARKDOWN_PATTERNS = {
    "literal_bold": re.compile(r"\*\*[^*\n][\s\S]{0,120}?\*\*"),
    "literal_inline_code": re.compile(r"`[^`\n]{1,160}`"),
    "literal_markdown_image": re.compile(r"!\[[^\]]*]\([^)]+\)"),
    "literal_markdown_link": re.compile(r"(?<!!)\[[^\]]+]\([^)]+\)"),
    "literal_pipe_table": re.compile(r"(^|\n)\s*\|[^|\n]+\|[^|\n]*\n\s*\|[-: |]+\|", re.MULTILINE),
    "jsx_style_object": re.compile(r"style=\{\{[^}]+}}"),
    "html_tag_text": re.compile(r"</?(?:u|span|div|table|tr|td|strong|code|br)\b[^>]*>"),
}


def html_double_star_count(html: str) -> int:
    return html.count("**")


@contextmanager
def alarm_timeout(seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(signum, frame):  # type: ignore[no-untyped-def]
        raise TimeoutError(f"operation exceeded {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def route_pattern(url: str) -> str:
    path = urlsplit(url).path or "/"
    match = re.fullmatch(r"/(posts|products)(?:/([^/]+))?/?", path)
    if not match:
        return path
    content_type = match.group(1)
    if match.group(2):
        return f"/{content_type}/{{slug}}"
    return f"/{content_type}"


def route_instance_key(pattern: str, occurrence: int) -> str:
    match = re.fullmatch(r"/(posts|products)/\{slug}", pattern)
    if match:
        return f"{match.group(1)}-detail-{occurrence}"
    label = re.sub(r"[^a-z0-9]+", "-", pattern.strip("/").lower()).strip("-") or "home"
    return f"route-{label}-{occurrence}"


def url_fingerprint(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def redact_reports(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    pattern_counts: dict[str, int] = {}
    for report in reports:
        item = dict(report)
        original_url = str(item.get("url", ""))
        pattern = route_pattern(original_url)
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        item["url"] = pattern
        if original_url.strip():
            item["urlFingerprint"] = url_fingerprint(original_url.strip())
        item["routeInstance"] = route_instance_key(pattern, pattern_counts[pattern])
        if "headings" in item and isinstance(item["headings"], dict):
            item["headings"] = {
                key: [f"redacted-{key}-{index + 1}" for index, _ in enumerate(value)]
                for key, value in item["headings"].items()
                if isinstance(value, list)
            }
        redacted_issues = []
        for issue in item.get("issues", []):
            if isinstance(issue, dict):
                redacted_issue = dict(issue)
                if redacted_issue.get("message"):
                    redacted_issue["message"] = "redacted"
                redacted_issues.append(redacted_issue)
        item["issues"] = redacted_issues
        redacted.append(item)
    return redacted


class FrontendParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.tags: dict[str, int] = {}
        self.images: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self._current_link: dict[str, str] | None = None
        self._skip_depth = 0
        self._current_heading: str | None = None
        self._heading_parts: list[str] = []
        self.headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if tag in {"head", "script", "style", "template", "svg"}:
            self._skip_depth += 1
            return
        attr_map = {k: v or "" for k, v in attrs}
        if tag == "img":
            self.images.append({"src": attr_map.get("src", ""), "alt": attr_map.get("alt", "")})
        if tag == "a":
            self._current_link = {"href": attr_map.get("href", ""), "text": ""}
            self.links.append(self._current_link)
        if tag in self.headings:
            self._current_heading = tag
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "script", "style", "template", "svg"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "a":
            self._current_link = None
        if tag == self._current_heading:
            heading_text = " ".join(part.strip() for part in self._heading_parts if part.strip())
            if heading_text:
                self.headings[tag].append(heading_text)
            self._current_heading = None
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if data:
            self.text_parts.append(data)
            if self._current_link is not None:
                self._current_link["text"] += data
            if self._current_heading is not None:
                self._heading_parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(part.strip() for part in self.text_parts if part.strip())


def fetch(url: str, timeout: int, max_bytes: int = 0) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": "allincms-render-audit/1.0"})
    try:
        with alarm_timeout(timeout):
            with urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                content_type = response.headers.get("content-type", "")
                body_bytes = response.read(max_bytes) if max_bytes > 0 else response.read()
                body = body_bytes.decode("utf-8", errors="replace")
                return status, content_type, body
    except HTTPError as exc:
        body_bytes = exc.read(max_bytes) if max_bytes > 0 else exc.read()
        body = body_bytes.decode("utf-8", errors="replace")
        return int(exc.code), exc.headers.get("content-type", ""), body
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def audit_html(url: str, html: str, status: int, content_type: str, expected_status: int) -> dict[str, Any]:
    parser = FrontendParser()
    parser.feed(html)
    text = parser.text
    issues: list[dict[str, str]] = []

    if status != expected_status:
        issues.append({"severity": "error", "code": "http_status", "message": f"HTTP status is {status}, expected {expected_status}"})

    if status == expected_status and expected_status != 200:
        html_star_count = html_double_star_count(html)
        visible_star_count = text.count("**")
        return {
            "url": url,
            "status": status,
            "expectedStatus": expected_status,
            "contentType": content_type,
            "tagCounts": {key: parser.tags.get(key, 0) for key in ("h1", "h2", "h3", "strong", "b", "code", "pre", "table", "ul", "ol", "li", "img", "a")},
            "headings": {key: parser.headings[key] for key in ("h1", "h2", "h3")},
            "imageCount": len(parser.images),
            "linkCount": len(parser.links),
            "diagnostics": {
                "htmlDoubleStarCount": html_star_count,
                "visibleTextDoubleStarCount": visible_star_count,
            },
            "issues": issues,
        }

    if "text/html" not in content_type.lower():
        issues.append({"severity": "warn", "code": "content_type", "message": f"Unexpected content-type: {content_type}"})

    html_star_count = html_double_star_count(html)
    visible_star_count = text.count("**")

    for code, pattern in MARKDOWN_PATTERNS.items():
        match = pattern.search(text)
        if match:
            issues.append({"severity": "error", "code": code, "message": match.group(0)[:180]})

    if parser.tags.get("h1", 0) == 0:
        issues.append({"severity": "warn", "code": "missing_h1", "message": "No <h1> found"})
    if parser.tags.get("h1", 0) > 1:
        unique_h1 = list(dict.fromkeys(parser.headings["h1"]))
        issues.append({"severity": "warn", "code": "multiple_h1", "message": " | ".join(unique_h1[:4])})
    if len(parser.headings["h1"]) != len(set(parser.headings["h1"])):
        issues.append({"severity": "warn", "code": "duplicate_h1_text", "message": "Duplicate H1 text found"})

    for index, image in enumerate(parser.images):
        if not image["src"]:
            issues.append({"severity": "error", "code": "image_missing_src", "message": f"image[{index}] has no src"})
        if not image["alt"]:
            issues.append({"severity": "warn", "code": "image_missing_alt", "message": f"image[{index}] has no alt"})

    return {
        "url": url,
        "status": status,
        "expectedStatus": expected_status,
        "contentType": content_type,
        "tagCounts": {key: parser.tags.get(key, 0) for key in ("h1", "h2", "h3", "strong", "b", "code", "pre", "table", "ul", "ol", "li", "img", "a")},
        "headings": {key: parser.headings[key] for key in ("h1", "h2", "h3")},
        "imageCount": len(parser.images),
        "linkCount": len(parser.links),
        "diagnostics": {
            "htmlDoubleStarCount": html_star_count,
            "visibleTextDoubleStarCount": visible_star_count,
        },
        "issues": issues,
    }


def read_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.url:
        urls.extend(args.url)
    if args.urls_file:
        with open(args.urls_file, "r", encoding="utf-8") as handle:
            urls.extend(line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#"))
    return urls


def read_expect_statuses(path: str | None) -> dict[str, int]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("--expect-statuses-file must contain a JSON object")

    statuses: dict[str, int] = {}
    for url, status in data.items():
        if not isinstance(url, str) or not url.strip():
            raise ValueError("--expect-statuses-file keys must be non-empty URL strings")
        if not isinstance(status, int) or isinstance(status, bool):
            raise ValueError(f"expected status for {url} must be an integer")
        statuses[url] = status
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit published AllinCMS frontend pages for rendering issues.")
    parser.add_argument("url", nargs="*", help="Frontend URLs to audit")
    parser.add_argument("--urls-file", help="File containing one URL per line")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--redact", action="store_true", help="Redact concrete URLs, headings, and issue snippets")
    parser.add_argument("--fail-on-warn", action="store_true", help="Exit non-zero when warnings are present")
    parser.add_argument("--expect-status", type=int, default=200, help="Expected HTTP status for every supplied URL")
    parser.add_argument("--expect-statuses-file", help="JSON object mapping URL to expected HTTP status; overrides --expect-status per URL")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds")
    parser.add_argument("--max-bytes", type=int, default=0, help="Maximum response bytes to read per URL; 0 reads the full body")
    args = parser.parse_args()

    urls = read_urls(args)
    if not urls:
        print("ERROR: provide at least one URL or --urls-file", file=sys.stderr)
        return 2

    try:
        expected_statuses = read_expect_statuses(args.expect_statuses_file)
    except Exception as exc:  # noqa: BLE001 - command-line validation.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    reports: list[dict[str, Any]] = []
    for url in urls:
        expected_status = expected_statuses.get(url, args.expect_status)
        try:
            status, content_type, html = fetch(url, args.timeout, args.max_bytes)
            reports.append(audit_html(url, html, status, content_type, expected_status))
        except Exception as exc:  # noqa: BLE001 - report per-URL failures instead of aborting early.
            reports.append({"url": url, "status": None, "expectedStatus": expected_status, "contentType": "", "tagCounts": {}, "imageCount": 0, "linkCount": 0, "issues": [{"severity": "error", "code": "fetch_failed", "message": str(exc)}]})

    output_reports = redact_reports(reports) if args.redact else reports

    if args.json:
        print(json.dumps(output_reports, ensure_ascii=False, indent=2))
    else:
        for report in output_reports:
            print(f"{report['url']} status={report['status']} issues={len(report['issues'])}")
            for issue in report["issues"]:
                print(f"  [{issue['severity']}] {issue['code']}: {issue['message']}")

    severities = [issue["severity"] for report in reports for issue in report["issues"]]
    if "error" in severities:
        return 1
    if args.fail_on_warn and "warn" in severities:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
