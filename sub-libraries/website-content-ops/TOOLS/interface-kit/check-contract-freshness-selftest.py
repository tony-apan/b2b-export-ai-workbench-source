#!/usr/bin/env python3
"""Offline adversarial self-test for check-contract-freshness.py.

Uses an isolated temporary checkout projection; never touches network or customer data.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUB = HERE.parent.parent
FRESHNESS_REL = Path("TOOLS/interface-kit/check-contract-freshness.py")


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(root / FRESHNESS_REL), *args],
        cwd=root, capture_output=True, text=True, check=False,
    )


def project_tree(tmp):
    root = Path(tmp) / "website-content-ops"
    files = [
        "TOOLS/interface-kit/check-contract-freshness.py",
        "TOOLS/interface-kit/templates/onepass-read-contract.json",
        "TOOLS/interface-kit/allincms_api.py",
        "SKILL-INSTALL/SKILL.md",
        "PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md",
        "ADAPTERS/cms/allincms/AI-START-HERE.md",
        "ADAPTERS/cms/allincms/interface-registry.json",
        "ADAPTERS/cms/allincms/article-operations.mjs",
        "ADAPTERS/cms/allincms/product-operations.mjs",
        "ADAPTERS/cms/allincms/content-plan-host-driver.mjs",
        "TOOLS/interface-kit/NEW-SITE-ONEPASS.md",
    ]
    for rel in files:
        src = SUB / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = project_tree(tmp)
        baseline = run(root)
        if baseline.returncode != 0:
            print("BASELINE_NOT_READY:")
            print(baseline.stdout)
            raise SystemExit(1)

        # Canonical article create must not regress to a hard block.
        article = root / "ADAPTERS/cms/allincms/article-operations.mjs"
        text = article.read_text()
        needle = "export async function createPostDraft"
        pos = text.index(needle)
        brace = text.index("{", pos)
        text = text[:brace + 1] + "\n  throw new Error('ARTICLE_CREATE_BLOCKED_BY_CANONICAL_REGISTRY');\n" + text[brace + 1:]
        article.write_text(text)
        blocked = run(root)
        assert blocked.returncode == 1
        assert ("canonical export createPostDraft still hard-BLOCKs" in blocked.stdout
                or "canonical export createPostDraft missing" in blocked.stdout)
        shutil.copy2(SUB / "ADAPTERS/cms/allincms/article-operations.mjs", article)

        # P0-3.1: deleting or weakening any Python canonical-controller-required guard
        # for article create must be caught as CONTRACT_FRESHNESS_DRIFT.
        helper = root / "TOOLS/interface-kit/allincms_api.py"
        original_helper = helper.read_text()
        guard_raise = 'raise RuntimeError("ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED")'

        def tampered_after(marker, replacement):
            pos = original_helper.index(marker)
            return original_helper[:pos] + original_helper[pos:].replace(guard_raise, replacement, 1)

        # 1) Delete the _create_post_transport guard (transport becomes silent).
        helper.write_text(tampered_after("def _create_post_transport", "pass"))
        deleted = run(root)
        assert deleted.returncode == 1
        assert "Python _create_post_transport lacks canonical-controller-required guard" in deleted.stdout

        # 2) Weaken the _send_content_transport CREATE_POST refusal condition.
        pos = original_helper.index("def _send_content_transport")
        weakened = original_helper[:pos] + original_helper[pos:].replace("if action == CREATE_POST:", "if action == 'removed-guard':", 1)
        helper.write_text(weakened)
        disabled = run(root)
        assert disabled.returncode == 1
        assert "Python _send_content_transport lacks canonical-controller-required guard" in disabled.stdout

        # 3) Delete the mutate_reviewed_post(target_id=None) guard (review/capability path
        #    would run first again).
        helper.write_text(tampered_after("def mutate_reviewed_post", "pass"))
        bypassed = run(root)
        assert bypassed.returncode == 1
        assert "Python mutate_reviewed_post lacks canonical-controller-required guard" in bypassed.stdout

        helper.write_text(original_helper)
        assert run(root).returncode == 0

        # Canonical host handler removal must be detected.
        driver = root / "ADAPTERS/cms/allincms/content-plan-host-driver.mjs"
        text = driver.read_text()
        text = text.replace("'article:create': {", "'article:create-disabled': {", 1)
        driver.write_text(text)
        missing_handler = run(root)
        assert missing_handler.returncode == 1
        assert "canonical host driver handler article:create missing" in missing_handler.stdout
        shutil.copy2(SUB / "ADAPTERS/cms/allincms/content-plan-host-driver.mjs", driver)

        # Exact-byte read receipt must reject tampering.
        receipt = root / "receipt.json"
        wrote = run(root, "--write-receipt", str(receipt))
        assert wrote.returncode == 0 and receipt.is_file()
        data = json.loads(receipt.read_text())
        data["documents"][0]["digest"] = "sha256:" + "0" * 64
        receipt.write_text(json.dumps(data))
        tampered = run(root, "--verify-receipt", str(receipt))
        assert tampered.returncode == 1
        assert "read receipt document digests are stale or incomplete" in tampered.stdout

    print("CONTRACT_FRESHNESS_SELFTEST_PASS")


if __name__ == "__main__":
    main()
