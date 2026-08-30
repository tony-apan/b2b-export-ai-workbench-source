#!/usr/bin/env python3
"""Resolve a complete Website Content Operations runtime.

Resolution order is fail-closed and deterministic:
1. ``--root`` (exact caller-provided full canonical source checkout)
2. ``$WEBSITE_CONTENT_OPS_ROOT`` (full canonical source checkout)
3. validated sibling/upward full-source discovery from ``--start`` or cwd
4. this Skill's immutable, digest-verified bundled runtime snapshot

An invalid explicit/environment root never falls through to another source. The
bundled snapshot is a generated runtime subset, not a second mutable canonical
implementation and not evidence of remote login, authorization, or capability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable

ENV_NAME = "WEBSITE_CONTENT_OPS_ROOT"
PACKAGE_ID = "website-content-ops"
BLOCK_CODE = "CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED"
ALLINCMS_REL = Path("ADAPTERS/cms/allincms")
SKILL_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_RUNTIME_ROOT = SKILL_ROOT / "vendor" / "website-content-ops-runtime"
BUNDLE_MANIFEST_NAME = "BUNDLE-MANIFEST.json"
BUNDLE_READY_MARKER_NAME = ".allincms-runtime-ready.json"
BUNDLE_FORMAT_VERSION = 1
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")

# These files distinguish a complete canonical source checkout from both this
# Skill and intentionally smaller Adapter packages.
FULL_SOURCE_REQUIRED_PATHS = (
    Path("README.md"),
    Path("MANIFEST.md"),
    Path("AGENTS.md"),
    Path("RUNTIME-CONTRACT.json"),
    Path("SKILL.md"),
    Path("PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md"),
    Path("TEMPLATES/source-extraction.md"),
    Path("SCHEMAS/source-extraction.schema.json"),
    Path("scripts/validate-source-extraction.mjs"),
    Path("TEMPLATES/content-operation-plan.md"),
    Path("SCHEMAS/content-operation-plan.schema.json"),
    Path("scripts/validate-content-operation-plan.mjs"),
    Path("scripts/runtime-scope.mjs"),
    Path("scripts/json-schema-lite.mjs"),
    ALLINCMS_REL / "README.md",
    ALLINCMS_REL / "AI-START-HERE.md",
    ALLINCMS_REL / "interface-registry.json",
    ALLINCMS_REL / "interface-registry.schema.json",
    ALLINCMS_REL / "scripts/validate-interface-registry.mjs",
    ALLINCMS_REL / "workspace-preflight.mjs",
    ALLINCMS_REL / "workspace-preflight-contract.json",
    ALLINCMS_REL / "article-content-formats.mjs",
    ALLINCMS_REL / "mutation-authorization.mjs",
    ALLINCMS_REL / "article-operations.mjs",
    ALLINCMS_REL / "article-operations-contract.json",
    ALLINCMS_REL / "article-image-binding.mjs",
    ALLINCMS_REL / "article-image-binding-contract.json",
    ALLINCMS_REL / "upload-media-browser.mjs",
    ALLINCMS_REL / "verification-evidence-contract.json",
    ALLINCMS_REL / "content-run-controller.mjs",
    ALLINCMS_REL / "content-run-controller.test.mjs",
    ALLINCMS_REL / "live-run-evidence.schema.json",
)
# Backward-compatible import name used by existing tests/integrations.
REQUIRED_RELATIVE_PATHS = FULL_SOURCE_REQUIRED_PATHS

# A bundle does not pretend to be the full source checkout, but it must contain
# every execution-critical contract and dependency imported by the Controller.
BUNDLED_RUNTIME_REQUIRED_PATHS = (
    Path("LICENSE"),
    Path("RUNTIME-CONTRACT.json"),
    Path("PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md"),
    Path("TEMPLATES/source-extraction.md"),
    Path("SCHEMAS/source-extraction.schema.json"),
    Path("scripts/validate-source-extraction.mjs"),
    Path("TEMPLATES/content-operation-plan.md"),
    Path("SCHEMAS/content-operation-plan.schema.json"),
    Path("scripts/validate-content-operation-plan.mjs"),
    Path("scripts/runtime-scope.mjs"),
    Path("scripts/json-schema-lite.mjs"),
    ALLINCMS_REL / "README.md",
    ALLINCMS_REL / "AI-START-HERE.md",
    ALLINCMS_REL / "package.json",
    ALLINCMS_REL / "package-lock.json",
    ALLINCMS_REL / "interface-registry.json",
    ALLINCMS_REL / "interface-registry.schema.json",
    ALLINCMS_REL / "scripts/validate-interface-registry.mjs",
    ALLINCMS_REL / "scripts/build-interface-index.mjs",
    ALLINCMS_REL / "workspace-preflight.mjs",
    ALLINCMS_REL / "workspace-preflight-contract.json",
    ALLINCMS_REL / "workspace-preflight.test.mjs",
    ALLINCMS_REL / "article-content-formats.mjs",
    ALLINCMS_REL / "article-content-formats.test.mjs",
    ALLINCMS_REL / "mutation-authorization.mjs",
    ALLINCMS_REL / "article-operations.mjs",
    ALLINCMS_REL / "article-operations-contract.json",
    ALLINCMS_REL / "article-operations.test.mjs",
    ALLINCMS_REL / "article-image-binding.mjs",
    ALLINCMS_REL / "article-image-binding-contract.json",
    ALLINCMS_REL / "article-image-binding.test.mjs",
    ALLINCMS_REL / "upload-media-browser.mjs",
    ALLINCMS_REL / "upload-media-browser.test.mjs",
    ALLINCMS_REL / "verification-evidence-contract.json",
    ALLINCMS_REL / "content-run-controller.mjs",
    ALLINCMS_REL / "content-run-controller.test.mjs",
    ALLINCMS_REL / "interface-registry.test.mjs",
    ALLINCMS_REL / "live-run-evidence.schema.json",
)

FORBIDDEN_BUNDLE_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "customer-runtime",
    "credentials",
    "secrets",
    "browser-profiles",
}


class ResolutionError(ValueError):
    """Raised when no safe canonical source/runtime root can be proven."""


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _blocked(detail: str) -> ResolutionError:
    return ResolutionError(f"{BLOCK_CODE}: {detail}")


def _load_runtime_contract(root: Path) -> dict[str, object]:
    try:
        runtime = json.loads((root / "RUNTIME-CONTRACT.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _blocked(f"runtime_contract_unreadable_or_invalid: {root}: {exc}") from exc
    if runtime.get("package_id") != PACKAGE_ID:
        raise _blocked(
            f"runtime_contract_package_mismatch: expected={PACKAGE_ID} "
            f"actual={runtime.get('package_id')!r}: {root}"
        )
    return runtime


def validate_source_root(path: str | Path) -> Path:
    root = _resolved(path)
    if "dist" in root.parts:
        raise _blocked(f"candidate_is_build_artifact: {root}")
    if not root.is_dir():
        raise _blocked(f"candidate_not_directory: {root}")

    missing = [str(rel) for rel in FULL_SOURCE_REQUIRED_PATHS if not (root / rel).is_file()]
    if missing:
        raise _blocked(f"candidate_missing_source_checkout_files: {root}: {', '.join(missing)}")

    _load_runtime_contract(root)
    try:
        manifest = (root / "MANIFEST.md").read_text(encoding="utf-8")
    except OSError as exc:
        raise _blocked(f"manifest_unreadable: {root}: {exc}") from exc
    if f'package_id: "{PACKAGE_ID}"' not in manifest and f"package_id: {PACKAGE_ID}" not in manifest:
        raise _blocked(f"manifest_package_id_missing: {root}")
    return root


# Backward-compatible function name.
def validate_root(path: str | Path) -> Path:
    return validate_source_root(path)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _stable_manifest_digest(manifest: dict[str, object]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "bundleDigest"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(encoded)


def _safe_bundle_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise _blocked(f"bundled_runtime_manifest_invalid_path: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise _blocked(f"bundled_runtime_manifest_unsafe_path: {value}")
    if any(part in FORBIDDEN_BUNDLE_PARTS for part in pure.parts):
        raise _blocked(f"bundled_runtime_manifest_forbidden_path: {value}")
    return Path(*pure.parts)


def validate_runtime_bundle(path: str | Path) -> tuple[Path, dict[str, object]]:
    root = _resolved(path)
    if not root.is_dir():
        raise _blocked(f"bundled_runtime_not_directory: {root}")
    manifest_path = root / BUNDLE_MANIFEST_NAME
    if manifest_path.is_symlink():
        raise _blocked(f"bundled_runtime_manifest_symlink_forbidden: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _blocked(f"bundled_runtime_manifest_unreadable_or_invalid: {root}: {exc}") from exc

    if manifest.get("formatVersion") != BUNDLE_FORMAT_VERSION:
        raise _blocked(f"bundled_runtime_format_mismatch: {root}")
    if manifest.get("packageId") != PACKAGE_ID:
        raise _blocked(f"bundled_runtime_package_mismatch: {root}")
    if manifest.get("bundleKind") != "verified-runtime-snapshot":
        raise _blocked(f"bundled_runtime_kind_mismatch: {root}")
    source_commit = manifest.get("sourceCommit")
    if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
        raise _blocked(f"bundled_runtime_source_commit_invalid: {root}")
    bundle_digest = manifest.get("bundleDigest")
    if not isinstance(bundle_digest, str) or not SHA256_RE.fullmatch(bundle_digest):
        raise _blocked(f"bundled_runtime_digest_invalid: {root}")
    if bundle_digest != _stable_manifest_digest(manifest):
        raise _blocked(f"bundled_runtime_manifest_digest_mismatch: {root}")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise _blocked(f"bundled_runtime_files_missing: {root}")

    declared: dict[Path, tuple[str, int]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise _blocked(f"bundled_runtime_file_entry_invalid: {root}")
        rel = _safe_bundle_relative_path(entry.get("path"))
        digest = entry.get("sha256")
        size = entry.get("bytes")
        if rel in declared:
            raise _blocked(f"bundled_runtime_duplicate_path: {rel}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise _blocked(f"bundled_runtime_file_digest_invalid: {rel}")
        if not isinstance(size, int) or size < 0:
            raise _blocked(f"bundled_runtime_file_size_invalid: {rel}")
        declared[rel] = (digest, size)

    missing_required = [str(rel) for rel in BUNDLED_RUNTIME_REQUIRED_PATHS if rel not in declared]
    if missing_required:
        raise _blocked(f"bundled_runtime_missing_required_files: {root}: {', '.join(missing_required)}")

    actual_files: set[Path] = set()
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if "node_modules" in rel.parts:
            continue
        if path.is_symlink():
            raise _blocked(f"bundled_runtime_symlink_forbidden: {rel}")
        if path.is_file() and path.name != BUNDLE_MANIFEST_NAME:
            actual_files.add(rel)
    if actual_files != set(declared):
        missing = sorted(str(path) for path in set(declared) - actual_files)
        unexpected = sorted(str(path) for path in actual_files - set(declared))
        raise _blocked(
            f"bundled_runtime_file_set_mismatch: {root}: "
            f"missing={missing or 'none'} unexpected={unexpected or 'none'}"
        )

    for rel, (expected_digest, expected_size) in declared.items():
        path = root / rel
        if path.is_symlink():
            raise _blocked(f"bundled_runtime_declared_file_symlink_forbidden: {rel}")
        data = path.read_bytes()
        if len(data) != expected_size or _sha256_bytes(data) != expected_digest:
            raise _blocked(f"bundled_runtime_file_integrity_mismatch: {rel}")

    _load_runtime_contract(root)
    return root, manifest


def _bundle_runtime_state(root: Path, manifest: dict[str, object]) -> tuple[bool, list[str], Path]:
    """Return installer-produced runtime dependency readiness without trusting it as bundle evidence."""
    adapter = root / ALLINCMS_REL
    marker = adapter / "node_modules" / BUNDLE_READY_MARKER_NAME
    problems: list[str] = []
    try:
        package = json.loads((adapter / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"package_json_unreadable_or_invalid: {exc}"], marker

    dependencies = package.get("dependencies")
    if not isinstance(dependencies, dict) or not dependencies:
        return False, ["package_json_dependencies_missing"], marker
    for name, expected_version in sorted(dependencies.items()):
        package_path = adapter / "node_modules" / str(name) / "package.json"
        try:
            installed = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            problems.append(f"missing_or_invalid_dependency:{name}@{expected_version}")
            continue
        if installed.get("version") != expected_version:
            problems.append(
                f"dependency_version_mismatch:{name}:expected={expected_version}:actual={installed.get('version')!r}"
            )

    try:
        ready = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        problems.append("runtime_ready_marker_missing_or_invalid")
    else:
        if ready.get("bundleDigest") != manifest.get("bundleDigest"):
            problems.append("runtime_ready_marker_bundle_digest_mismatch")
        if ready.get("status") != "verified":
            problems.append("runtime_ready_marker_status_invalid")
    return not problems, problems, marker


def discovery_candidates(start: str | Path) -> Iterable[Path]:
    cursor = _resolved(start)
    if cursor.is_file():
        cursor = cursor.parent
    for base in (cursor, *cursor.parents):
        if base.name == PACKAGE_ID:
            yield base
        yield base / PACKAGE_ID
        yield base / "sub-libraries" / PACKAGE_ID


def resolve_root(
    *,
    explicit_root: str | None = None,
    start: str | Path | None = None,
    bundle_root: str | Path | None = None,
) -> tuple[Path, str]:
    # An invalid higher-precedence input must never silently fall through.
    if explicit_root:
        return validate_source_root(explicit_root), "explicit"

    env_root = os.environ.get(ENV_NAME, "").strip()
    if env_root:
        return validate_source_root(env_root), "environment"

    errors: list[str] = []
    seen: set[Path] = set()
    for candidate in discovery_candidates(start or Path.cwd()):
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            return validate_source_root(resolved), "upward-discovery"
        except ResolutionError as exc:
            errors.append(str(exc))

    candidate_bundle = bundle_root if bundle_root is not None else BUNDLED_RUNTIME_ROOT
    try:
        root, _manifest = validate_runtime_bundle(candidate_bundle)
        return root, "bundled-runtime"
    except ResolutionError as exc:
        errors.append(str(exc))

    detail = "; ".join(errors[-4:]) if errors else "no candidates"
    raise _blocked(
        "complete_runtime_not_found: pass --root, set "
        f"{ENV_NAME}, run from a repository containing sub-libraries/{PACKAGE_ID}, "
        f"or reinstall a Skill containing a valid {BUNDLE_MANIFEST_NAME}; {detail}"
    )


def build_result(root: Path, source: str) -> dict[str, object]:
    adapter = root / ALLINCMS_REL
    bundled = source == "bundled-runtime"
    source_revision: str | None = None
    bundle_manifest_path: str | None = None
    bundle_digest: str | None = None
    runtime_dependencies_installed: bool | None = None
    runtime_dependency_problems: list[str] = []
    runtime_ready_marker: str | None = None
    if bundled:
        _validated, manifest = validate_runtime_bundle(root)
        source_revision = str(manifest["sourceCommit"])
        bundle_digest = str(manifest["bundleDigest"])
        bundle_manifest_path = str(root / BUNDLE_MANIFEST_NAME)
        runtime_dependencies_installed, runtime_dependency_problems, marker = _bundle_runtime_state(root, manifest)
        runtime_ready_marker = str(marker)
    return {
        "status": "resolved",
        "packageId": PACKAGE_ID,
        "source": source,
        "runtimeKind": "bundled-runtime-snapshot" if bundled else "full-source-checkout",
        "subLibraryRoot": str(root),
        "allinCmsRoot": str(adapter),
        "sourceDrivenSop": str(root / "PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md"),
        "sourceExtractionTemplate": str(root / "TEMPLATES/source-extraction.md"),
        "sourceExtractionSchema": str(root / "SCHEMAS/source-extraction.schema.json"),
        "sourceExtractionValidator": str(root / "scripts/validate-source-extraction.mjs"),
        "contentOperationPlanTemplate": str(root / "TEMPLATES/content-operation-plan.md"),
        "contentOperationPlanSchema": str(root / "SCHEMAS/content-operation-plan.schema.json"),
        "contentOperationPlanValidator": str(root / "scripts/validate-content-operation-plan.mjs"),
        "allinCmsEntry": str(adapter / "AI-START-HERE.md"),
        "interfaceRegistry": str(adapter / "interface-registry.json"),
        "workspacePreflight": str(adapter / "workspace-preflight.mjs"),
        "contentRunController": str(adapter / "content-run-controller.mjs"),
        "verificationEvidenceContract": str(adapter / "verification-evidence-contract.json"),
        "runtimeContract": str(root / "RUNTIME-CONTRACT.json"),
        "bundleManifest": bundle_manifest_path,
        "bundleDigest": bundle_digest,
        "sourceRevision": source_revision,
        "sourceCheckoutValidated": not bundled,
        "runtimeBundleValidated": bundled,
        "runtimeDependenciesInstalled": runtime_dependencies_installed,
        "runtimeDependencyProblems": runtime_dependency_problems,
        "runtimeReadyMarker": runtime_ready_marker,
        "controllerExecutable": runtime_dependencies_installed if bundled else True,
        "minimalAdapterPackageOnly": False,
        # Compatibility for callers of the first resolver draft.
        "isSourceArtifact": not bundled,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Exact Website Content Operations full source root")
    parser.add_argument("--start", default=str(Path.cwd()), help="Start path for upward discovery")
    parser.add_argument("--bundle-root", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable result")
    args = parser.parse_args()

    try:
        root, source = resolve_root(
            explicit_root=args.root,
            start=args.start,
            bundle_root=args.bundle_root,
        )
    except ResolutionError as exc:
        if args.json:
            print(json.dumps({"status": "blocked", "code": BLOCK_CODE, "detail": str(exc)}, ensure_ascii=False))
        else:
            print(str(exc), file=sys.stderr)
        return 2

    result = build_result(root, source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["subLibraryRoot"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
