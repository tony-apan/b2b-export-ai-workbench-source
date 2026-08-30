#!/usr/bin/env python3
"""Build the immutable Website Content Operations runtime snapshot.

The builder reads exact bytes from a committed Git revision, never from dirty
working-tree files. It copies only the explicit runtime allowlist, writes a
per-file SHA-256 manifest, and replaces the destination atomically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

PACKAGE_ID = "website-content-ops"
BUNDLE_FORMAT_VERSION = 1
DEFAULT_DESTINATION = Path(__file__).resolve().parents[1] / "vendor" / "website-content-ops-runtime"

BUNDLE_FILES = (
    "LICENSE",
    "NOTICE",
    "THIRD-PARTY-NOTICES.md",
    "RUNTIME-CONTRACT.json",
    "PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md",
    "TEMPLATES/source-extraction.md",
    "SCHEMAS/source-extraction.schema.json",
    "scripts/validate-source-extraction.mjs",
    "TEMPLATES/content-operation-plan.md",
    "SCHEMAS/content-operation-plan.schema.json",
    "scripts/validate-content-operation-plan.mjs",
    "scripts/runtime-scope.mjs",
    "scripts/json-schema-lite.mjs",
    "ADAPTERS/cms/allincms/AI-START-HERE.md",
    "ADAPTERS/cms/allincms/INTERFACE-INDEX.md",
    "ADAPTERS/cms/allincms/README.md",
    "ADAPTERS/cms/allincms/article-content-formats.mjs",
    "ADAPTERS/cms/allincms/article-content-formats.test.mjs",
    "ADAPTERS/cms/allincms/article-format-verification.redacted.md",
    "ADAPTERS/cms/allincms/article-image-binding-adversarial-review.redacted.md",
    "ADAPTERS/cms/allincms/article-image-binding-contract.json",
    "ADAPTERS/cms/allincms/article-image-binding.mjs",
    "ADAPTERS/cms/allincms/article-image-binding.test.mjs",
    "ADAPTERS/cms/allincms/article-operations-contract.json",
    "ADAPTERS/cms/allincms/article-operations.md",
    "ADAPTERS/cms/allincms/article-operations.mjs",
    "ADAPTERS/cms/allincms/article-operations.test.mjs",
    "ADAPTERS/cms/allincms/content-run-controller.mjs",
    "ADAPTERS/cms/allincms/content-run-controller.test.mjs",
    "ADAPTERS/cms/allincms/direct-delete-verification.redacted.md",
    "ADAPTERS/cms/allincms/direct-serial-10-verification.redacted.md",
    "ADAPTERS/cms/allincms/direct-serial-11-article-verification.redacted.md",
    "ADAPTERS/cms/allincms/image-index-e2e-verification.redacted.md",
    "ADAPTERS/cms/allincms/interface-registry.json",
    "ADAPTERS/cms/allincms/interface-registry.schema.json",
    "ADAPTERS/cms/allincms/interface-registry.test.mjs",
    "ADAPTERS/cms/allincms/live-run-evidence.schema.json",
    "ADAPTERS/cms/allincms/media-metadata-and-ai-vision-sop.md",
    "ADAPTERS/cms/allincms/media-operations-contract.redacted.json",
    "ADAPTERS/cms/allincms/mutation-authorization.mjs",
    "ADAPTERS/cms/allincms/observed-contract.redacted.json",
    "ADAPTERS/cms/allincms/package-lock.json",
    "ADAPTERS/cms/allincms/package.json",
    "ADAPTERS/cms/allincms/scripts/build-interface-index.mjs",
    "ADAPTERS/cms/allincms/scripts/validate-interface-registry.mjs",
    "ADAPTERS/cms/allincms/upload-media-browser.mjs",
    "ADAPTERS/cms/allincms/upload-media-browser.test.mjs",
    "ADAPTERS/cms/allincms/verification-evidence-contract.json",
    "ADAPTERS/cms/allincms/verify-media.mjs",
    "ADAPTERS/cms/allincms/workspace-preflight-contract.json",
    "ADAPTERS/cms/allincms/workspace-preflight.md",
    "ADAPTERS/cms/allincms/workspace-preflight.mjs",
    "ADAPTERS/cms/allincms/workspace-preflight.test.mjs",
)


def run_git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=text)


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def stable_manifest_digest(manifest: dict[str, object]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return digest(encoded)


def repository_context(source_root: Path, revision: str) -> tuple[Path, str, str]:
    repo = Path(str(run_git(source_root, "rev-parse", "--show-toplevel")).strip()).resolve()
    commit = str(run_git(repo, "rev-parse", f"{revision}^{{commit}}")).strip()
    prefix = source_root.resolve().relative_to(repo).as_posix()
    return repo, commit, prefix


def committed_bytes(repo: Path, commit: str, prefix: str, rel: str) -> bytes:
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe allowlist path: {rel}")
    git_path = f"{prefix}/{rel}" if prefix != "." else rel
    try:
        return bytes(run_git(repo, "show", f"{commit}:{git_path}", text=False))
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"allowlisted file missing at {commit}: {git_path}") from exc


def build(source_root: Path, destination: Path, revision: str) -> dict[str, object]:
    source_root = source_root.expanduser().resolve()
    destination = destination.expanduser().resolve()
    repo, commit, prefix = repository_context(source_root, revision)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_parent = Path(tempfile.mkdtemp(prefix="website-content-ops-runtime.", dir=destination.parent))
    temp_root = temp_parent / destination.name
    temp_root.mkdir()
    entries: list[dict[str, object]] = []
    try:
        for rel in BUNDLE_FILES:
            data = committed_bytes(repo, commit, prefix, rel)
            output = temp_root / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            entries.append({"path": rel, "bytes": len(data), "sha256": digest(data)})

        manifest: dict[str, object] = {
            "formatVersion": BUNDLE_FORMAT_VERSION,
            "packageId": PACKAGE_ID,
            "bundleKind": "verified-runtime-snapshot",
            "sourceCommit": commit,
            "sourceSubtree": prefix,
            "generationMode": "git-committed-bytes-allowlist",
            "files": entries,
            "includedSupportClasses": [
                "locked-node-runtime-dependencies",
                "adapter-interface-registry-validators",
                "local-contract-tests",
                "redacted-test-and-verification-evidence",
            ],
            "excludedClasses": [
                "source-cards-and-unredacted-source-material",
                "customer-runtime-and-unredacted-live-evidence",
                "credentials-and-browser-profiles",
                "node_modules-and-dist",
                "binary-fixtures",
            ],
            "evidenceBoundary": (
                "This digest proves local bundle self-consistency. sourceCommit records the Git revision from "
                "which this builder read the allowlisted bytes, but independent source authenticity and release "
                "eligibility still require separate Git and release verification. It does not prove remote CMS "
                "login, authorization, capability, publication, SEO, inquiry, conversion, Stable, or production "
                "readiness."
            ),
        }
        manifest["bundleDigest"] = stable_manifest_digest(manifest)
        (temp_root / "BUNDLE-MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        backup = destination.with_name(destination.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            destination.rename(backup)
        temp_root.rename(destination)
        if backup.exists():
            shutil.rmtree(backup)
        return manifest
    finally:
        if temp_parent.exists():
            shutil.rmtree(temp_parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, help="Canonical website-content-ops source root")
    parser.add_argument("--revision", default="HEAD", help="Committed Git revision to snapshot (default: HEAD)")
    parser.add_argument("--destination", default=str(DEFAULT_DESTINATION), help="Bundle output directory")
    args = parser.parse_args()
    manifest = build(Path(args.source_root), Path(args.destination), args.revision)
    print(json.dumps({
        "status": "built",
        "destination": str(Path(args.destination).expanduser().resolve()),
        "sourceCommit": manifest["sourceCommit"],
        "bundleDigest": manifest["bundleDigest"],
        "fileCount": len(manifest["files"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
