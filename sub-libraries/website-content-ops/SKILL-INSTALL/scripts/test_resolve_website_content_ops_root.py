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

import resolve_website_content_ops_root as resolver_module  # noqa: E402
from resolve_website_content_ops_root import (  # noqa: E402
    BLOCK_CODE,
    BUNDLED_RUNTIME_REQUIRED_PATHS,
    BUNDLE_FORMAT_VERSION,
    BUNDLE_MANIFEST_NAME,
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
SOURCE_ROOT = SKILL_ROOT.parent
INSTALLER = SKILL_ROOT / "install.py"
PYTHON_310 = shutil.which("python3.11") or shutil.which("python3.10")


def make_package(root: Path) -> Path:
    for rel in FULL_SOURCE_REQUIRED_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    adapter = root / "ADAPTERS/cms/allincms"
    (adapter / "package.json").write_text(
        json.dumps(
            {
                "name": "fixture-adapter",
                "dependencies": {"acorn": "8.15.0", "ajv": "8.20.0", "sharp": "0.35.3"},
            }
        ),
        encoding="utf-8",
    )
    (root / "MANIFEST.md").write_text('---\npackage_id: "website-content-ops"\n---\n', encoding="utf-8")
    (root / "RUNTIME-CONTRACT.json").write_text(
        json.dumps({"package_id": "website-content-ops"}), encoding="utf-8"
    )
    return root


def install_fixture_dependencies(root: Path, *, sharp_version: str = "0.35.3") -> None:
    versions = {"acorn": "8.15.0", "ajv": "8.20.0", "sharp": sharp_version}
    adapter = root / "ADAPTERS/cms/allincms"
    for name, version in versions.items():
        package = adapter / "node_modules" / name / "package.json"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text(json.dumps({"name": name, "version": version}), encoding="utf-8")


def make_bundle(root: Path) -> Path:
    entries: list[dict[str, object]] = []
    for rel in BUNDLED_RUNTIME_REQUIRED_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = b"fixture\n"
        if rel == Path("RUNTIME-CONTRACT.json"):
            data = json.dumps({"package_id": "website-content-ops"}).encode("utf-8")
        elif rel == Path("ADAPTERS/cms/allincms/package.json"):
            data = json.dumps(
                {
                    "name": "fixture-adapter",
                    "dependencies": {"acorn": "8.15.0", "ajv": "8.20.0", "sharp": "0.35.3"},
                }
            ).encode("utf-8")
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


class ResolverTests(unittest.TestCase):
    def test_current_full_source_validates_and_builds_machine_result(self) -> None:
        root = validate_root(SOURCE_ROOT)
        result = build_result(root, "explicit")
        self.assertEqual(result["runtimeKind"], "full-source-checkout")
        self.assertTrue(result["sourceCheckoutValidated"])
        self.assertFalse(result["runtimeBundleValidated"])
        self.assertEqual(result["controllerExecutable"], result["runtimeDependenciesInstalled"])

    def test_full_source_without_node_modules_is_not_controller_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_package(Path(tmp) / "website-content-ops")
            result = build_result(root, "explicit")
            self.assertFalse(result["runtimeDependenciesInstalled"])
            self.assertFalse(result["controllerExecutable"])
            self.assertIn("missing_or_invalid_dependency:sharp@0.35.3", result["runtimeDependencyProblems"])

    def test_full_source_exact_dependency_versions_are_controller_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_package(Path(tmp) / "website-content-ops")
            install_fixture_dependencies(root)
            result = build_result(root, "explicit")
            self.assertTrue(result["runtimeDependenciesInstalled"])
            self.assertTrue(result["controllerExecutable"])

    def test_full_source_dependency_version_drift_is_not_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_package(Path(tmp) / "website-content-ops")
            install_fixture_dependencies(root, sharp_version="0.35.2")
            result = build_result(root, "explicit")
            self.assertFalse(result["controllerExecutable"])
            self.assertIn(
                "dependency_version_mismatch:sharp:expected=0.35.3:actual='0.35.2'",
                result["runtimeDependencyProblems"],
            )

    def test_explicit_root_precedes_environment_and_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            explicit = make_package(Path(tmp) / "explicit/website-content-ops")
            env_root = make_package(Path(tmp) / "env/website-content-ops")
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(env_root)}):
                resolved, source = resolve_root(explicit_root=str(explicit), start=tmp)
            self.assertEqual((resolved, source), (explicit.resolve(), "explicit"))

    def test_environment_root_precedes_full_source_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_root = make_package(Path(tmp) / "env/website-content-ops")
            discovered = make_package(Path(tmp) / "repo/sub-libraries/website-content-ops")
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(env_root)}):
                resolved, source = resolve_root(start=discovered / "ADAPTERS")
            self.assertEqual((resolved, source), (env_root.resolve(), "environment"))

    def test_upward_and_sibling_full_source_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            isolated_skill = Path(tmp) / "isolated-skill/SKILL-INSTALL"
            isolated_skill.mkdir(parents=True)
            root = make_package(Path(tmp) / "repo/sub-libraries/website-content-ops")
            deep = Path(tmp) / "repo/wiki/00_meta"
            deep.mkdir(parents=True)
            with patch.dict(os.environ, {}, clear=True), patch.object(resolver_module, "SKILL_ROOT", isolated_skill):
                self.assertEqual(resolve_root(start=deep), (root.resolve(), "upward-discovery"))
            sibling = Path(tmp) / "sibling/allincms-bulk-content-upload"
            sibling.mkdir(parents=True)
            canonical = make_package(Path(tmp) / "sibling/website-content-ops")
            with patch.dict(os.environ, {}, clear=True), patch.object(resolver_module, "SKILL_ROOT", isolated_skill):
                self.assertEqual(resolve_root(start=sibling), (canonical.resolve(), "upward-discovery"))

    def test_no_full_source_and_no_explicit_bundle_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), patch.object(
            resolver_module, "SKILL_ROOT", Path(tmp) / "isolated-skill/SKILL-INSTALL"
        ):
            with self.assertRaisesRegex(ResolutionError, rf"^{BLOCK_CODE}:.*vendor bundle is retired"):
                resolve_root(start=tmp)

    def test_invalid_explicit_or_environment_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "missing"
            with self.assertRaisesRegex(ResolutionError, "candidate_not_directory"):
                resolve_root(explicit_root=str(invalid), start=tmp)
            with patch.dict(os.environ, {"WEBSITE_CONTENT_OPS_ROOT": str(invalid)}):
                with self.assertRaisesRegex(ResolutionError, "candidate_not_directory"):
                    resolve_root(start=tmp)

    def test_dist_and_incomplete_source_candidates_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist = make_package(Path(tmp) / "dist/latest/website-content-ops")
            with self.assertRaisesRegex(ResolutionError, "candidate_is_build_artifact"):
                validate_root(dist)
            incomplete = make_package(Path(tmp) / "incomplete/website-content-ops")
            (incomplete / "scripts/runtime-scope.mjs").unlink()
            with self.assertRaisesRegex(ResolutionError, "candidate_missing_source_checkout_files"):
                validate_root(incomplete)

    def test_explicit_bundle_root_remains_available_for_test_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), patch.object(
            resolver_module, "SKILL_ROOT", Path(tmp) / "isolated-skill/SKILL-INSTALL"
        ):
            bundle = make_bundle(Path(tmp) / "bundle")
            resolved, source = resolve_root(start=Path(tmp) / "none", bundle_root=bundle)
            self.assertEqual((resolved, source), (bundle.resolve(), "bundled-runtime"))
            self.assertTrue(build_result(resolved, source)["runtimeBundleValidated"])

    def test_explicit_bundle_missing_tampered_or_extra_file_fails_closed(self) -> None:
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

    def test_explicit_bundle_rejects_internal_symlinks(self) -> None:
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

    def test_cli_full_source_success_and_structured_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_package(Path(tmp) / "website-content-ops")
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(json.loads(completed.stdout)["source"], "explicit")
        with tempfile.TemporaryDirectory() as blocked_tmp:
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            isolated_script = Path(blocked_tmp) / "isolated/SKILL-INSTALL/scripts/resolve_website_content_ops_root.py"
            isolated_script.parent.mkdir(parents=True)
            shutil.copy2(SCRIPT, isolated_script)
            blocked_start = Path(blocked_tmp) / "unrelated-project"
            blocked_start.mkdir(parents=True)
            blocked = subprocess.run(
                [sys.executable, str(isolated_script), "--start", str(blocked_start), "--json"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(json.loads(blocked.stdout)["code"], BLOCK_CODE)

    @unittest.skipUnless(PYTHON_310, "Python 3.10+ interpreter required for installer test")
    def test_install_py_from_isolated_full_source_copy_resolves_from_unrelated_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied_source = Path(tmp) / "arbitrary-clone-name"
            shutil.copytree(
                SOURCE_ROOT,
                copied_source,
                ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "__pycache__"),
            )
            copied_skill = copied_source / "SKILL-INSTALL"
            install_root = Path(tmp) / "skills"
            unrelated_project = Path(tmp) / "ordinary-project"
            unrelated_project.mkdir()
            env = os.environ.copy()
            env.pop("WEBSITE_CONTENT_OPS_ROOT", None)
            completed = subprocess.run(
                [PYTHON_310, str(copied_skill / "install.py"), f"--dir={install_root}", "--skip-self-test"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            link = install_root / "allincms-bulk-content-upload"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), copied_skill.resolve())
            self.assertIn("Skipping npm ci and runtime self-tests", completed.stdout)
            resolved = subprocess.run(
                [sys.executable, str(link / "scripts/resolve_website_content_ops_root.py"), "--start", str(unrelated_project), "--json"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
                cwd=unrelated_project,
            )
            payload = json.loads(resolved.stdout)
            self.assertEqual(payload["source"], "skill-relative-source")
            self.assertEqual(Path(payload["subLibraryRoot"]), copied_source.resolve())
            self.assertTrue(payload["sourceCheckoutValidated"])
            self.assertFalse(payload["runtimeDependenciesInstalled"])
            self.assertFalse(payload["controllerExecutable"])

    def test_active_docs_describe_source_only_install_and_fail_closed_handoff(self) -> None:
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        install = INSTALLER.read_text(encoding="utf-8")
        for text in (readme, skill):
            self.assertIn("source-only", text)
            self.assertIn("vendor", text)
            self.assertIn("retired", text)
            self.assertIn(BLOCK_CODE, text)
        self.assertIn("install.py", readme)
        self.assertIn("install.cmd", readme)
        self.assertNotIn("普通用户只 clone / 安装这个 Skill 即可解析运行时", readme)
        self.assertNotIn("For a bundled runtime", skill)
        self.assertIn("npm", install)
        self.assertIn("--skip-self-test", install)
        self.assertIn("--docs-parse", install)
        self.assertIn("ADAPTER_AUTHORIZATION_CONTEXT_REQUIRED", skill)
        self.assertIn("Only if the API itself reports `login_required`", skill)


if __name__ == "__main__":
    unittest.main(verbosity=2)
