#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("resolve_website_content_ops_root.py")
SCRIPTS_DIR = SCRIPT.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from resolve_website_content_ops_root import (  # noqa: E402
    BLOCK_CODE,
    BUNDLED_RUNTIME_REQUIRED_PATHS,
    BUNDLE_FORMAT_VERSION,
    BUNDLE_MANIFEST_NAME,
    BUNDLED_RUNTIME_ROOT,
    FULL_SOURCE_REQUIRED_PATHS,
    ResolutionError,
    _sha256_bytes,
    _stable_manifest_digest,
    build_result,
    resolve_root,
    validate_root,
    validate_runtime_bundle,
)

SKILL_ROOT = SCRIPT.parents[1]
ROUTED_DOCS = (
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "README.md",
    SKILL_ROOT / "AGENTS.md",
    SKILL_ROOT / "CLAUDE.md",
    SKILL_ROOT / "NEXT-SESSION.md",
    SKILL_ROOT / "agents/openai.yaml",
    SKILL_ROOT / "references/canonical-adapter-routing.md",
    SKILL_ROOT / "references/README.md",
    SKILL_ROOT / "scripts/README.md",
)


def make_package(root: Path) -> Path:
    for rel in FULL_SOURCE_REQUIRED_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    (root / "MANIFEST.md").write_text('---\npackage_id: "website-content-ops"\n---\n', encoding="utf-8")
    (root / "RUNTIME-CONTRACT.json").write_text(
        json.dumps({"package_id": "website-content-ops"}), encoding="utf-8"
    )
    return root


def make_bundle(root: Path) -> Path:
    entries: list[dict[str, object]] = []
    for rel in BUNDLED_RUNTIME_REQUIRED_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = b"fixture\n"
        if rel == Path("RUNTIME-CONTRACT.json"):
            data = json.dumps({"package_id": "website-content-ops"}).encode("utf-8")
        elif rel == Path("ADAPTERS/cms/allincms/package.json"):
            data = json.dumps({
                "name": "fixture-adapter",
                "version": "1.0.0",
                "dependencies": {"acorn": "8.15.0", "ajv": "8.20.0", "sharp": "0.35.3"},
            }).encode("utf-8")
        path.write_bytes(data)
        entries.append({"path": rel.as_posix(), "bytes": len(data), "sha256": _sha256_bytes(data)})
    manifest: dict[str, object] = {
        "formatVersion": BUNDLE_FORMAT_VERSION,
        "packageId": "website-content-ops",
        "bundleKind": "verified-runtime-snapshot",
        "sourceCommit": "a" * 40,
        "sourceSubtree": "sub-libraries/website-content-ops",
        "generationMode": "test-fixture",
        "files": entries,
        "excludedClasses": [],
        "evidenceBoundary": "fixture",
    }
    manifest["bundleDigest"] = _stable_manifest_digest(manifest)
    (root / BUNDLE_MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return root


def mark_bundle_ready(root: Path) -> None:
    manifest = json.loads((root / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    adapter = root / "ADAPTERS/cms/allincms"
    for name, version in {"acorn": "8.15.0", "ajv": "8.20.0", "sharp": "0.35.3"}.items():
        package = adapter / "node_modules" / name / "package.json"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text(json.dumps({"name": name, "version": version}), encoding="utf-8")
    (adapter / "node_modules/.allincms-runtime-ready.json").write_text(
        json.dumps({"status": "verified", "bundleDigest": manifest["bundleDigest"]}),
        encoding="utf-8",
    )


class ResolverTests(unittest.TestCase):
    def test_checked_in_bundle_validates_and_builds_machine_result(self) -> None:
        root, manifest = validate_runtime_bundle(BUNDLED_RUNTIME_ROOT)
        self.assertEqual(root, BUNDLED_RUNTIME_ROOT.resolve())
        self.assertEqual(manifest["bundleKind"], "verified-runtime-snapshot")
        result = build_result(root, "bundled-runtime")
        self.assertFalse(result["sourceCheckoutValidated"])
        self.assertTrue(result["runtimeBundleValidated"])
        self.assertFalse(result["runtimeDependenciesInstalled"])
        self.assertFalse(result["controllerExecutable"])
        self.assertIn("runtime_ready_marker_missing_or_invalid", result["runtimeDependencyProblems"])
        self.assertEqual(result["sourceRevision"], manifest["sourceCommit"])
        self.assertEqual(result["bundleDigest"], manifest["bundleDigest"])

    def test_runtime_created_node_modules_are_ignored_but_ready_state_is_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(Path(tmp) / "bundle")
            mark_bundle_ready(bundle)
            root, _manifest = validate_runtime_bundle(bundle)
            result = build_result(root, "bundled-runtime")
            self.assertTrue(result["runtimeDependenciesInstalled"])
            self.assertTrue(result["controllerExecutable"])

            marker = Path(result["runtimeReadyMarker"])
            payload = json.loads(marker.read_text(encoding="utf-8"))
            payload["bundleDigest"] = "sha256:" + "0" * 64
            marker.write_text(json.dumps(payload), encoding="utf-8")
            drifted = build_result(root, "bundled-runtime")
            self.assertFalse(drifted["controllerExecutable"])
            self.assertIn("runtime_ready_marker_bundle_digest_mismatch", drifted["runtimeDependencyProblems"])

    def test_explicit_root_precedes_environment_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            explicit = make_package(Path(tmp) / "explicit/website-content-ops")
            env_root = make_package(Path(tmp) / "env/website-content-ops")
            bundle = make_bundle(Path(tmp) / "bundle")
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(env_root)}):
                resolved, source = resolve_root(
                    explicit_root=str(explicit), start=Path(tmp) / "unused", bundle_root=bundle
                )
            self.assertEqual(resolved, explicit.resolve())
            self.assertEqual(source, "explicit")
            result = build_result(resolved, source)
            self.assertTrue(result["sourceCheckoutValidated"])
            self.assertFalse(result["runtimeBundleValidated"])

    def test_environment_root_precedes_discovery_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_root = make_package(Path(tmp) / "env/website-content-ops")
            discovered = make_package(Path(tmp) / "repo/sub-libraries/website-content-ops")
            bundle = make_bundle(Path(tmp) / "bundle")
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(env_root)}):
                resolved, source = resolve_root(start=discovered / "ADAPTERS", bundle_root=bundle)
            self.assertEqual(resolved, env_root.resolve())
            self.assertEqual(source, "environment")

    def test_upward_and_sibling_discovery_precede_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(Path(tmp) / "bundle")
            root = make_package(Path(tmp) / "repo/sub-libraries/website-content-ops")
            deep = Path(tmp) / "repo/wiki/00_meta"
            deep.mkdir(parents=True)
            with patch.dict(os.environ, {}, clear=True):
                resolved, source = resolve_root(start=deep, bundle_root=bundle)
            self.assertEqual((resolved, source), (root.resolve(), "upward-discovery"))

            sibling_base = Path(tmp) / "sibling"
            skill_checkout = sibling_base / "allincms-bulk-content-upload"
            skill_checkout.mkdir(parents=True)
            canonical = make_package(sibling_base / "website-content-ops")
            with patch.dict(os.environ, {}, clear=True):
                resolved, source = resolve_root(start=skill_checkout, bundle_root=bundle)
            self.assertEqual((resolved, source), (canonical.resolve(), "upward-discovery"))

    def test_bundle_is_fallback_from_arbitrary_working_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            starts = [SKILL_ROOT, Path(tmp), Path(tmp) / "new-project/deep"]
            starts[2].mkdir(parents=True)
            for start in starts:
                resolved, source = resolve_root(start=start)
                self.assertEqual(resolved, BUNDLED_RUNTIME_ROOT.resolve())
                self.assertEqual(source, "bundled-runtime")

    def test_invalid_explicit_or_environment_root_fails_closed_without_bundle_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(Path(tmp) / "bundle")
            invalid = Path(tmp) / "missing"
            with self.assertRaisesRegex(ResolutionError, rf"{BLOCK_CODE}.*candidate_not_directory"):
                resolve_root(explicit_root=str(invalid), start=tmp, bundle_root=bundle)
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(invalid)}):
                with self.assertRaisesRegex(ResolutionError, rf"{BLOCK_CODE}.*candidate_not_directory"):
                    resolve_root(start=tmp, bundle_root=bundle)

    def test_dist_and_incomplete_source_candidates_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_package(Path(tmp) / "dist/latest/website-content-ops")
            with self.assertRaisesRegex(ResolutionError, "candidate_is_build_artifact"):
                validate_root(root)
            root = make_package(Path(tmp) / "incomplete/website-content-ops")
            (root / "scripts/runtime-scope.mjs").unlink()
            with self.assertRaisesRegex(ResolutionError, "candidate_missing_source_checkout_files"):
                validate_root(root)

    def test_bundle_missing_tampered_or_extra_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = make_bundle(Path(tmp) / "source")
            for mode in ("missing", "tampered", "extra"):
                candidate = Path(tmp) / mode
                shutil.copytree(source, candidate)
                target = candidate / BUNDLED_RUNTIME_REQUIRED_PATHS[-1]
                if mode == "missing":
                    target.unlink()
                elif mode == "tampered":
                    target.write_text("tampered\n", encoding="utf-8")
                else:
                    (candidate / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
                with self.assertRaisesRegex(ResolutionError, "bundled_runtime_"):
                    validate_runtime_bundle(candidate)

    def test_bundle_rejects_internal_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(Path(tmp) / "bundle")
            target = bundle / BUNDLED_RUNTIME_REQUIRED_PATHS[-1]
            original = target.read_bytes()
            target.unlink()
            outside = Path(tmp) / "outside.txt"
            outside.write_bytes(original)
            target.symlink_to(outside)
            with self.assertRaisesRegex(ResolutionError, "symlink_forbidden"):
                validate_runtime_bundle(bundle)

    def test_no_runtime_returns_stable_block_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ResolutionError, rf"^{BLOCK_CODE}:"):
                resolve_root(start=tmp, bundle_root=Path(tmp) / "missing-bundle")

    def test_cli_json_bundle_success_and_structured_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--start", tmp, "--json"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["source"], "bundled-runtime")
            self.assertTrue(result["runtimeBundleValidated"])

            blocked = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(Path(tmp) / "missing"), "--json"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(blocked.returncode, 2)
            payload = json.loads(blocked.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["code"], BLOCK_CODE)

    def test_installer_from_isolated_copy_reports_verified_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied_skill = Path(tmp) / "checkout"
            shutil.copytree(SKILL_ROOT, copied_skill, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            install_root = Path(tmp) / "skills"
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            completed = subprocess.run(
                ["bash", str(copied_skill / "install.sh"), f"--dir={install_root}"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            combined = completed.stdout + completed.stderr
            link = install_root / "allincms-bulk-content-upload"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), copied_skill.resolve())
            self.assertIn("verified bundled runtime resolved", combined)
            self.assertIn("bundled runtime dependencies and self-tests verified", combined)
            self.assertIn("verified runtime ready", combined)
            self.assertNotIn("Thin router installed only", combined)
            self.assertNotIn("CMS operations remain BLOCK", combined)
            resolved = subprocess.run(
                [sys.executable, str(copied_skill / "scripts/resolve_website_content_ops_root.py"), "--start", str(copied_skill), "--json"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(resolved.stdout)
            self.assertTrue(payload["runtimeDependenciesInstalled"])
            self.assertTrue(payload["controllerExecutable"])

    def test_installer_does_not_create_link_when_bundle_is_tampered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied_skill = Path(tmp) / "checkout"
            shutil.copytree(
                SKILL_ROOT,
                copied_skill,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"),
            )
            target = copied_skill / "vendor/website-content-ops-runtime/RUNTIME-CONTRACT.json"
            target.write_text("tampered\n", encoding="utf-8")
            install_root = Path(tmp) / "skills"
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            completed = subprocess.run(
                ["bash", str(copied_skill / "install.sh"), f"--dir={install_root}"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((install_root / "allincms-bulk-content-upload").exists())
            self.assertIn("bundled_runtime_file_integrity_mismatch", completed.stdout + completed.stderr)

    def test_installer_recognizes_explicit_full_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = make_package(Path(tmp) / "website-content-ops")
            install_root = Path(tmp) / "skills"
            env = os.environ.copy()
            env["WEBSITE_CONTENT_OPS_ROOT"] = str(canonical)
            completed = subprocess.run(
                ["bash", str(SKILL_ROOT / "install.sh"), f"--dir={install_root}"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            combined = completed.stdout + completed.stderr
            self.assertIn("canonical source checkout resolved", combined)
            self.assertIn("verified runtime ready", combined)
            self.assertNotIn("verified bundled runtime resolved", combined)

    def test_active_docs_describe_portable_bundle_and_fail_closed_login_handoff(self) -> None:
        forbidden = "/Users/example/private-workspace"
        for path in ROUTED_DOCS:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text, path)

        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.splitlines()), 200)
        for stable_token in (
            "<SUB_LIBRARY_ROOT>",
            BLOCK_CODE,
            "BUNDLE-MANIFEST.json",
            "ADAPTER_AUTHORIZATION_CONTEXT_REQUIRED",
            "never satisfies the canonical Adapter",
            "no more than 30 minutes",
            "id-0005-source-driven-cms-operation-sop.md",
            "site_bootstrap",
            "site_operation",
            "Never invent a future site key",
            "live_verified_current_deployment",
            "product at `exploration_only`",
            "User-provided sources override examples",
            "A customer value must be dynamic",
            "Only if the API itself reports `login_required`",
            "`http_error`, `contract_drift`, or `pagination_incomplete`",
            "repeat the API preflight",
        ):
            self.assertIn(stable_token, skill)
        for retired_heading in (
            "## Operating Rule", "## Required Reading", "## Workflow",
            "## Browser Paths", "## Probe Rules", "## Payload Rules",
        ):
            self.assertNotIn(retired_heading, skill)

        routing = (SKILL_ROOT / "references/canonical-adapter-routing.md").read_text(encoding="utf-8")
        for token in (
            "digest-verified bundled runtime",
            "revalidates the same context immediately before every request",
            "not a requirement to interrupt the user before every API call",
            "Only `login_required`", "`authenticated`", "`http_error`",
            "`contract_drift`", "`pagination_incomplete`",
        ):
            self.assertIn(token, routing)

        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("普通用户只 clone / 安装这个 Skill 即可解析运行时", readme)
        self.assertIn("runtimeBundleValidated", readme)
        self.assertIn("runtimeDependenciesInstalled", readme)
        self.assertIn("全部通过后才创建 Skill 链接", readme)
        installer = (SKILL_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn(BLOCK_CODE, installer)
        self.assertIn("verified bundled runtime resolved", installer)
        self.assertIn("npm ci --omit=dev --no-audit --no-fund", installer)
        self.assertIn("Installation stopped before creating Skill links", installer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
